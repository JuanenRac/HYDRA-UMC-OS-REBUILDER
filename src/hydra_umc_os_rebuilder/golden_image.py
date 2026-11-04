# =============================================================================
# HYDRA-UMC-OS-REBUILDER - The golden (recovery) image kept on the host: golden_image.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The recovery image of a device is a known-good image that lives on the HOST (the CM5 or the PC that runs the updater), never on the
# device: there is no flash left there for a third slot. A store is one folder that holds the image, `golden.json` (its name, size,
# SHA-256, version and commit) and `golden.json.sig`, an Ed25519 signature over the SHA-256 of golden.json made with the same key
# format as the signed releases but with a domain of its own, so a release or a profile signature can never pass as a golden one.
# Registering refuses to replace the golden with an older or equal version unless the person says so, and verifying checks the
# hash of the image and the signature before the image may be used to recover a device. The private key is a file outside any
# repository and is never printed; this module reinstalls nothing.
# =============================================================================
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from .profile_signing import ProfileSigningError, _ed25519, _read_hex_key
from .release_channel import file_sha256

FORMAT = "hydra-image-golden/1"
RECORD = "golden.json"
_DOMAIN = b"hydra-umc-os-rebuilder-golden/1\n"
_HEX = set("0123456789abcdef")


class GoldenError(ValueError):
    """A golden image that cannot be registered or does not verify."""


def _message(record: Path) -> bytes:
    return _DOMAIN + hashlib.sha256(record.read_bytes()).hexdigest().encode("ascii")


def _version_key(version: str) -> tuple[int, ...]:
    parts = version.split(".")
    if not version or not all(part.isdigit() for part in parts):
        raise GoldenError(f"not a version: {version!r}")
    return tuple(int(part) for part in parts)


def _read_record(store: Path) -> dict[str, Any]:
    try:
        data = json.loads((store / RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise GoldenError(f"cannot read the golden record in {store}: {error}") from error
    if data.get("format") != FORMAT:
        raise GoldenError(f"{RECORD} is not a {FORMAT} file")
    return data


def register(image: Path, store: Path, version: str, commit: str, private_key: str, *, replace: bool = False) -> Path:
    """Copy `image` into `store`, write golden.json (the hash is read from the file) and sign it. Returns the record path."""
    if not image.is_file():
        raise GoldenError(f"{image} is not a file")
    new = _version_key(version)
    if len(commit) != 40 or any(ch not in _HEX for ch in commit):
        raise GoldenError("the golden image names the full 40-character commit it was built from")
    record = store / RECORD
    previous: dict[str, Any] | None = None
    if record.is_file():
        previous = _read_record(store)
        if not replace:
            raise GoldenError(f"{store} already holds a golden image (version {previous.get('version')}); pass replace to change it")
        if new <= _version_key(str(previous["version"])):
            raise GoldenError(f"the golden image does not go back: {version} is not newer than {previous['version']}")
    ed25519, _ = _ed25519()
    key = ed25519.Ed25519PrivateKey.from_private_bytes(_read_hex_key(private_key, "private key"))  # fails before anything is written
    store.mkdir(parents=True, exist_ok=True)
    target = store / image.name
    if image.resolve() != target.resolve():
        shutil.copyfile(image, target)
    data = {"format": FORMAT, "image": image.name, "size": target.stat().st_size, "sha256": file_sha256(target), "version": version, "commit": commit}
    record.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (store / (RECORD + ".sig")).write_text(key.sign(_message(record)).hex() + "\n", encoding="utf-8")
    if previous and previous.get("image") != image.name:
        old = store / Path(str(previous["image"])).name
        if old.is_file():
            old.unlink()
    return record


def verify(store: Path, trusted_public_key: str, *, minimum_version: str = "") -> dict[str, Any]:
    """The signature of the record and the hash of the image both hold; returns the record with the image path."""
    if not trusted_public_key:
        raise GoldenError("a trusted public key is required to use the golden image")
    data = _read_record(store)
    record = store / RECORD
    sig = store / (RECORD + ".sig")
    if not sig.is_file():
        raise GoldenError(f"{RECORD} has no signature file ({sig.name})")
    ed25519, invalid = _ed25519()
    try:
        signature = bytes.fromhex(sig.read_text(encoding="utf-8").strip())
        ed25519.Ed25519PublicKey.from_public_bytes(_read_hex_key(trusted_public_key, "trusted public key")).verify(signature, _message(record))
    except (ValueError, ProfileSigningError, invalid) as error:
        raise GoldenError(f"the signature of {RECORD} does not verify against the trusted key: {error}") from error
    name = str(data.get("image", ""))
    image = store / name
    if not name or Path(name).name != name or not image.is_file():
        raise GoldenError("the golden image file named in the record is missing")
    if image.stat().st_size != data.get("size") or file_sha256(image) != data.get("sha256"):
        raise GoldenError("the golden image does not match its record (size or SHA-256)")
    if minimum_version and _version_key(str(data["version"])) < _version_key(minimum_version):
        raise GoldenError(f"the golden image {data['version']} is older than the required {minimum_version}")
    return {"version": data["version"], "commit": data["commit"], "sha256": data["sha256"], "image": str(image)}
