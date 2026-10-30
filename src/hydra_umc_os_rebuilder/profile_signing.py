# =============================================================================
# HYDRA-UMC-OS-REBUILDER - Signed profile manifests: profile_signing.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# A profile manifest decides exactly which commit of which project goes into an image. Anyone who can change the file
# changes the image, so a profile may be signed: `<manifest>.sig` holds an Ed25519 signature over the SHA-256 of the
# file's bytes, and `profile-build --require-signed` refuses a manifest whose signature does not verify against a public
# key the operator trusts. Off by default (a profile frozen on the same machine needs no signature); the switch is
# `--require-signed` or HYDRA_UMC_OS_REBUILDER_REQUIRE_SIGNED=1.
#
# Keys are raw 32-byte Ed25519 keys written as 64 hexadecimal characters in a file of their own. The private key never
# goes into a command line or a repository. Needs the `cryptography` package (installed with the `signing` extra).
# =============================================================================
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

REQUIRE_SIGNED_ENV = "HYDRA_UMC_OS_REBUILDER_REQUIRE_SIGNED"
TRUSTED_KEY_ENV = "HYDRA_UMC_OS_REBUILDER_PROFILE_PUBKEY"
_DOMAIN = b"hydra-umc-os-rebuilder-profile/1\n"
_HEX_KEY = re.compile(r"^[0-9a-fA-F]{64}$")


class ProfileSigningError(ValueError):
    """A key, a signature or a manifest that cannot be used."""


def _ed25519():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError as error:
        raise ProfileSigningError(
            "signing a profile needs the 'cryptography' package: pip install 'hydra-umc-os-rebuilder[signing]'"
        ) from error
    return ed25519, InvalidSignature


def signature_path(manifest_path: Path) -> Path:
    return manifest_path.with_name(manifest_path.name + ".sig")


def _message(manifest_path: Path) -> bytes:
    return _DOMAIN + hashlib.sha256(manifest_path.read_bytes()).hexdigest().encode("ascii")


def _read_hex_key(source: str, what: str) -> bytes:
    """A key given as 64 hex characters, or as the path of a file holding them."""
    text = source.strip()
    if not _HEX_KEY.match(text):
        path = Path(source)
        if not path.is_file():
            raise ProfileSigningError(f"the {what} is neither 64 hexadecimal characters nor an existing file: {source!r}")
        text = path.read_text(encoding="utf-8").strip()
    if not _HEX_KEY.match(text):
        raise ProfileSigningError(f"the {what} must be 64 hexadecimal characters (a raw 32-byte Ed25519 key)")
    return bytes.fromhex(text)


def generate_keypair(private_path: Path, public_path: Path) -> str:
    """Write a new key pair (hex, one file each; the private one readable by its owner only) and return the public key."""
    ed25519, _ = _ed25519()
    for path in (private_path, public_path):
        if path.exists():
            raise ProfileSigningError(f"{path} already exists: not overwriting a key")
    from cryptography.hazmat.primitives import serialization

    private = ed25519.Ed25519PrivateKey.generate()
    seed = private.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    ).hex()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    descriptor = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(seed + "\n")
    public_path.write_text(public + "\n", encoding="utf-8")
    return public


def sign_manifest(manifest_path: Path, private_key: str) -> Path:
    """Write `<manifest>.sig` for the manifest as it is now. `private_key` is the key file (or its 64 hex characters)."""
    ed25519, _ = _ed25519()
    key = ed25519.Ed25519PrivateKey.from_private_bytes(_read_hex_key(private_key, "private key"))
    target = signature_path(manifest_path)
    target.write_text(key.sign(_message(manifest_path)).hex() + "\n", encoding="utf-8")
    return target


def verify_manifest(manifest_path: Path, trusted_public_key: str) -> None:
    """Raise ProfileSigningError unless `<manifest>.sig` is a valid signature of this manifest by the trusted key."""
    ed25519, invalid_signature = _ed25519()
    sig_file = signature_path(manifest_path)
    if not sig_file.is_file():
        raise ProfileSigningError(f"{manifest_path.name} has no signature file ({sig_file.name})")
    try:
        signature = bytes.fromhex(sig_file.read_text(encoding="utf-8").strip())
    except ValueError as error:
        raise ProfileSigningError(f"{sig_file.name} is not a hexadecimal signature") from error
    key = ed25519.Ed25519PublicKey.from_public_bytes(_read_hex_key(trusted_public_key, "trusted public key"))
    try:
        key.verify(signature, _message(manifest_path))
    except invalid_signature as error:
        raise ProfileSigningError(
            f"the signature of {manifest_path.name} does not match its content and the trusted key: the profile was changed or signed by someone else"
        ) from error


def signature_required(flag: bool = False) -> bool:
    """True when the switch is given or the environment asks for it (1, true, yes, on)."""
    return flag or os.environ.get(REQUIRE_SIGNED_ENV, "").strip().lower() in ("1", "true", "yes", "on")
