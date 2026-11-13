# =============================================================================
# HYDRA-UMC-OS-REBUILDER - Signed documentation corpus in the image: corpus_delivery.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The documentation assistant (HYDRA-UMC-DOCS-QA) answers from an index that is built once per release in CI and signed on the maintainer's machine with
# the release key that also signs the packages and images: `corpus-<release>.json` with `corpus-<release>.json.sha256` and `corpus-<release>.json.sig`
# (the `sha256sum` line and the base64 Ed25519 signature of the exact bytes). An image may carry it. This module checks the three files against the
# public key the operator trusts BEFORE the image is mounted, refuses an unsigned, altered or foreign-signed corpus, and copies the verified files into
# /opt/hydra-umc/docs-qa/corpus/ together with a record and the public key, so the service on the device can check the very same signature again with
# `serve --bundle-public-key`. It holds no private key and never signs anything. Off unless a corpus is given: an image without one still builds, and the
# service then falls back to indexing local documents with a warning.
# Needs the `cryptography` package (the `signing` extra), like the signed profiles.
# =============================================================================
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .profile_signing import ProfileSigningError, _ed25519, _read_hex_key

CORPUS_PUBKEY_ENV = "HYDRA_UMC_OS_REBUILDER_CORPUS_PUBKEY"
CORPUS_DIR = Path("opt") / "hydra-umc" / "docs-qa" / "corpus"
RECORD_FORMAT = "hydra-umc-image-corpus/1"
BUNDLE_FORMAT = "hydra-umc-docs-qa-bundle/1"
MAX_CORPUS_BYTES = 256 * 1024 * 1024
_NAME = re.compile(r"^corpus-([0-9]+(?:\.[0-9]+){1,3})\.json$")


class CorpusDeliveryError(ValueError):
    """The corpus cannot go into the image: missing, unsigned, altered, signed by another key or not a corpus bundle."""


@dataclass(frozen=True)
class VerifiedCorpus:
    bundle: Path
    release: str
    sha256: str
    public_key_hex: str


def _read_exact(path: Path, what: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise CorpusDeliveryError(f"the {what} {path.name} is missing or unreadable") from error


def verify_signed_corpus(bundle: Path, trusted_public_key: str) -> VerifiedCorpus:
    """Checks `bundle`, its `.sha256` and its `.sig` against the trusted release public key (64 hex characters, or a file holding them)."""
    match = _NAME.match(bundle.name)
    if match is None:
        raise CorpusDeliveryError(f"{bundle.name} is not named corpus-<release>.json")
    try:
        if bundle.stat().st_size > MAX_CORPUS_BYTES:
            raise CorpusDeliveryError("the corpus is larger than the service loads")
    except OSError as error:
        raise CorpusDeliveryError(f"the corpus {bundle.name} is missing or unreadable") from error
    try:
        key_bytes = _read_hex_key(trusted_public_key, "corpus public key")
    except ProfileSigningError as error:
        raise CorpusDeliveryError(str(error)) from error
    data = _read_exact(bundle, "corpus")
    digest_text = _read_exact(bundle.with_name(bundle.name + ".sha256"), "digest file").decode("ascii", "replace").split()
    actual = hashlib.sha256(data).hexdigest()
    if not digest_text or not hmac.compare_digest(digest_text[0].lower(), actual):
        raise CorpusDeliveryError(f"{bundle.name} does not match its .sha256: it was changed after it was signed")
    sig_text = _read_exact(bundle.with_name(bundle.name + ".sig"), "signature file").decode("ascii", "replace").strip()
    try:
        signature = base64.b64decode(sig_text, validate=True)
    except (binascii.Error, ValueError) as error:
        raise CorpusDeliveryError(f"{bundle.name}.sig is not base64") from error
    if len(signature) != 64:
        raise CorpusDeliveryError(f"{bundle.name}.sig does not hold an Ed25519 signature")
    try:
        ed25519, invalid_signature = _ed25519()
    except ProfileSigningError as error:
        raise CorpusDeliveryError(str(error)) from error
    try:
        ed25519.Ed25519PublicKey.from_public_bytes(key_bytes).verify(signature, data)
    except invalid_signature as error:
        raise CorpusDeliveryError(f"the signature of {bundle.name} does not verify against the trusted key: it is unsigned for this key or was signed by someone else") from error
    try:
        header = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise CorpusDeliveryError(f"{bundle.name} is signed but is not JSON") from error
    if not isinstance(header, dict) or header.get("format") != BUNDLE_FORMAT:
        raise CorpusDeliveryError(f"{bundle.name} is signed but is not a corpus bundle of the format the service reads")
    if header.get("release") != match.group(1):
        raise CorpusDeliveryError(f"the file name says release {match.group(1)} and the corpus says {header.get('release')!r}")
    return VerifiedCorpus(bundle=bundle, release=match.group(1), sha256=actual, public_key_hex=key_bytes.hex())


def install_signed_corpus(rootfs_mount: Path, verified: VerifiedCorpus) -> Path:
    """Copies the verified files into the image and writes the record; returns the directory. The bytes are checked again after the copy."""
    target = rootfs_mount / CORPUS_DIR
    target.mkdir(parents=True, exist_ok=True)
    for suffix in ("", ".sha256", ".sig"):
        source = verified.bundle.with_name(verified.bundle.name + suffix)
        destination = target / source.name
        destination.write_bytes(source.read_bytes())
        destination.chmod(0o644)
    copied = target / verified.bundle.name
    if hashlib.sha256(copied.read_bytes()).hexdigest() != verified.sha256:
        raise CorpusDeliveryError("the corpus in the image differs from the verified file")
    (target / "release-public-key.hex").write_text(verified.public_key_hex + "\n", encoding="ascii", newline="\n")
    (target / "release-public-key.hex").chmod(0o644)
    record = {
        "format": RECORD_FORMAT, "release": verified.release, "bundle": verified.bundle.name, "sha256": verified.sha256,
        "signature": f"{verified.bundle.name}.sig", "public_key": "release-public-key.hex", "verified_at_build": True,
        "use": f"hydra-umc-docs-qa serve --bundle {verified.bundle.name} --bundle-public-key release-public-key.hex (from this directory)",
    }
    (target / "corpus-record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (target / "corpus-record.json").chmod(0o644)
    return target
