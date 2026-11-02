# =============================================================================
# HYDRA-UMC-OS-REBUILDER - Signed image releases: release_channel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# A release of an image is three things that must agree: the image file, a `release.json` that names its SHA-256, its
# size, its version and the commit it was built from, and a signed git tag on that commit. `release.json.sig` is an
# Ed25519 signature over the SHA-256 of release.json (the same key format as the signed profiles, with a domain of its own
# so that a profile signature can never pass as a release signature). The private key is given as a file outside any
# repository and is never printed. Verification checks the hash of the image, the signature and, when asked, the
# signature of the tag with `git verify-tag`. This module creates no tag and publishes nothing: `tag_command` only returns
# the command the person who releases runs.
# =============================================================================
from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .profile_signing import ProfileSigningError, _ed25519, _read_hex_key

FORMAT = "hydra-image-release/1"
_DOMAIN = b"hydra-umc-os-rebuilder-release/1\n"
_HEX = set("0123456789abcdef")


class ReleaseError(ValueError):
    """A release that cannot be made or does not verify."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def signature_path(manifest: Path) -> Path:
    return manifest.with_name(manifest.name + ".sig")


def _message(manifest: Path) -> bytes:
    return _DOMAIN + hashlib.sha256(manifest.read_bytes()).hexdigest().encode("ascii")


def tag_name(version: str, config: dict[str, Any]) -> str:
    if not version or any(ch not in "0123456789." for ch in version):
        raise ReleaseError(f"not a version: {version!r}")
    return f"{config['release_channel']['tag_prefix']}{version}"


def tag_command(version: str, commit: str, config: dict[str, Any]) -> list[str]:
    """The command that makes the signed tag. It is returned, never run."""
    if len(commit) != 40 or any(ch not in _HEX for ch in commit):
        raise ReleaseError("the tag goes on a full 40-character commit")
    name = tag_name(version, config)
    return ["git", "tag", "-s", name, commit, "-m", f"Image release {version}"]


def make_manifest(image: Path, version: str, commit: str, output: Path, config: dict[str, Any]) -> Path:
    """Write release.json for `image` (the hash is read from the file, never taken from elsewhere)."""
    if not image.is_file():
        raise ReleaseError(f"{image} is not a file")
    tag_command(version, commit, config)  # validates version and commit
    data = {
        "format": FORMAT, "image": image.name, "size": image.stat().st_size, "sha256": file_sha256(image),
        "version": version, "commit": commit, "tag": tag_name(version, config),
    }
    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def sign_release(manifest: Path, private_key: str) -> Path:
    ed25519, _ = _ed25519()
    key = ed25519.Ed25519PrivateKey.from_private_bytes(_read_hex_key(private_key, "private key"))
    target = signature_path(manifest)
    target.write_text(key.sign(_message(manifest)).hex() + "\n", encoding="utf-8")
    return target


def verify_signature(manifest: Path, trusted_public_key: str) -> None:
    ed25519, invalid = _ed25519()
    sig = signature_path(manifest)
    if not sig.is_file():
        raise ReleaseError(f"{manifest.name} has no signature file ({sig.name})")
    try:
        signature = bytes.fromhex(sig.read_text(encoding="utf-8").strip())
        key = ed25519.Ed25519PublicKey.from_public_bytes(_read_hex_key(trusted_public_key, "trusted public key"))
        key.verify(signature, _message(manifest))
    except (ValueError, ProfileSigningError, invalid) as error:
        raise ReleaseError(f"the signature of {manifest.name} does not verify against the trusted key: {error}") from error


Runner = Callable[[list[str], Path], "subprocess.CompletedProcess[str]"]


def _run_git(command: list[str], cwd: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=60, check=False)


def verify_tag(repo: Path, tag: str, commit: str, run: Runner = _run_git) -> None:
    """The tag verifies (`git verify-tag`) and points at the commit of the manifest."""
    checked = run(["git", "verify-tag", tag], repo)
    if checked.returncode != 0:
        raise ReleaseError(f"the tag {tag} has no valid signature: {checked.stderr.strip() or checked.stdout.strip()}")
    pointed = run(["git", "rev-list", "-n", "1", tag], repo)
    if pointed.returncode != 0 or pointed.stdout.strip() != commit:
        raise ReleaseError(f"the tag {tag} does not point at the commit of the release")


def verify_release(manifest: Path, image: Path, config: dict[str, Any], *, trusted_key: str = "", repo: Path | None = None, run: Runner = _run_git) -> dict[str, Any]:
    """Check the release. The signature of the manifest and of the tag are checked when the options ask for them or when given."""
    options = config["release_channel"]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ReleaseError(f"cannot read {manifest}: {error}") from error
    if data.get("format") != FORMAT:
        raise ReleaseError(f"{manifest.name} is not a {FORMAT} file")
    if image.name != data.get("image") or image.stat().st_size != data.get("size") or file_sha256(image) != data.get("sha256"):
        raise ReleaseError("the image does not match its release manifest (name, size or SHA-256)")
    checked = ["sha256"]
    key = trusted_key or str(options["trusted_key"])
    if options["require_signed_manifest"] or key:
        if not key:
            raise ReleaseError("a signed release is required but no trusted public key is given")
        verify_signature(manifest, key)
        checked.append("signature")
    if options["require_signed_tag"]:
        if repo is None:
            raise ReleaseError("a signed tag is required but no repository is given to check it in")
        verify_tag(repo, str(data["tag"]), str(data["commit"]), run)
        checked.append("tag")
    return {"version": data["version"], "tag": data["tag"], "checked": checked}
