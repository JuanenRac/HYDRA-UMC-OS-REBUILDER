# =============================================================================
# HYDRA-UMC-OS-REBUILDER - A signed delta between two images: golden_delta.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# A delta carries only the blocks of a new image that differ from an older one, so an A/B update does not move the whole image. A delta is
# one folder: `delta.json` (the format, the size and SHA-256 of the base and of the target, the block size and the list of blocks),
# `delta.bin` (the bytes of the changed blocks) and `delta.json.sig`, an Ed25519 signature over the SHA-256 of delta.json made with the
# same key format as the signed releases and a domain of its own. Applying checks the signature, the hash of the base, and the hash of the
# result before the output path is touched. The private key is a file outside any repository and is never printed.
# =============================================================================
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .profile_signing import ProfileSigningError, _ed25519, _read_hex_key
from .release_channel import file_sha256

FORMAT = "hydra-image-delta/1"
RECORD = "delta.json"
DATA = "delta.bin"
DEFAULT_BLOCK = 65536
_DOMAIN = b"hydra-umc-os-rebuilder-delta/1\n"
MIN_BLOCK = 512
MAX_BLOCK = 16 * 1024 * 1024


class DeltaError(ValueError):
    """A delta that cannot be made, does not verify or does not apply."""


def _message(record: Path) -> bytes:
    return _DOMAIN + hashlib.sha256(record.read_bytes()).hexdigest().encode("ascii")


def _blocks(path: Path, block: int) -> Iterator[bytes]:
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(block)
            if not chunk:
                return
            yield chunk


def create(base: Path, target: Path, store: Path, private_key: str, *, block_size: int = DEFAULT_BLOCK) -> Path:
    """Write the delta that turns `base` into `target` in `store`. Returns the record path. Fails before writing when the key is bad."""
    for name, path in (("base", base), ("target", target)):
        if not path.is_file():
            raise DeltaError(f"the {name} image {path} is not a file")
    if not MIN_BLOCK <= block_size <= MAX_BLOCK:
        raise DeltaError(f"the block size must be between {MIN_BLOCK} and {MAX_BLOCK} bytes")
    ed25519, _ = _ed25519()
    key = ed25519.Ed25519PrivateKey.from_private_bytes(_read_hex_key(private_key, "private key"))
    base_index: dict[str, int] = {}
    for index, chunk in enumerate(_blocks(base, block_size)):
        base_index.setdefault(hashlib.sha256(chunk).hexdigest(), index)
    ops: list[list[Any]] = []
    literal = 0
    store.mkdir(parents=True, exist_ok=True)
    with (store / DATA).open("wb") as out:
        for chunk in _blocks(target, block_size):
            found = base_index.get(hashlib.sha256(chunk).hexdigest())
            # a copy is only valid when the base block has the same length as this one (the last block of a file can be short)
            if found is not None and _same_length(base, found, block_size, len(chunk)):
                ops.append(["c", found, len(chunk)])
            else:
                out.write(chunk)
                ops.append(["l", literal, len(chunk)])
                literal += len(chunk)
    data = {
        "format": FORMAT,
        "block_size": block_size,
        "base": {"size": base.stat().st_size, "sha256": file_sha256(base)},
        "target": {"size": target.stat().st_size, "sha256": file_sha256(target)},
        "data": {"size": literal, "sha256": file_sha256(store / DATA)},
        "blocks": ops,
    }
    record = store / RECORD
    record.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")
    (store / (RECORD + ".sig")).write_text(key.sign(_message(record)).hex() + "\n", encoding="utf-8")
    return record


def _same_length(base: Path, index: int, block: int, length: int) -> bool:
    return min(block, base.stat().st_size - index * block) == length


def _load(store: Path, trusted_public_key: str) -> dict[str, Any]:
    if not trusted_public_key:
        raise DeltaError("a trusted public key is required to apply a delta")
    record, sig = store / RECORD, store / (RECORD + ".sig")
    if not record.is_file() or not sig.is_file():
        raise DeltaError(f"{store} does not hold {RECORD} and its signature")
    ed25519, invalid = _ed25519()
    try:
        signature = bytes.fromhex(sig.read_text(encoding="utf-8").strip())
        ed25519.Ed25519PublicKey.from_public_bytes(_read_hex_key(trusted_public_key, "trusted public key")).verify(signature, _message(record))
    except (ValueError, ProfileSigningError, invalid) as error:
        raise DeltaError(f"the signature of {RECORD} does not verify against the trusted key: {error}") from error
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
    except ValueError as error:
        raise DeltaError(f"cannot read {RECORD}: {error}") from error
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise DeltaError(f"{RECORD} is not a {FORMAT} file")
    return data


def apply(base: Path, store: Path, trusted_public_key: str, output: Path) -> dict[str, Any]:
    """Rebuild the target image from `base` and the delta in `store`; `output` is replaced only if every hash holds."""
    data = _load(store, trusted_public_key)
    if not base.is_file():
        raise DeltaError(f"the base image {base} is not a file")
    if base.stat().st_size != data["base"]["size"] or file_sha256(base) != data["base"]["sha256"]:
        raise DeltaError("the base image is not the one this delta was made from (size or SHA-256)")
    payload = store / DATA
    if not payload.is_file() or payload.stat().st_size != data["data"]["size"] or file_sha256(payload) != data["data"]["sha256"]:
        raise DeltaError(f"{DATA} does not match its record (size or SHA-256)")
    block = int(data["block_size"])
    if not MIN_BLOCK <= block <= MAX_BLOCK:
        raise DeltaError("the block size in the record is out of range")
    literal = payload.read_bytes()
    base_size = int(data["base"]["size"])
    temp = output.with_name(output.name + ".partial")
    result = hashlib.sha256()
    written = 0
    try:
        with base.open("rb") as source, temp.open("wb") as out:
            for op, where, length in data["blocks"]:
                if length <= 0 or length > block:
                    raise DeltaError("a block of the delta has a length outside the block size")
                if op == "c":
                    start = where * block
                    if where < 0 or start >= base_size:
                        raise DeltaError("a block of the delta points outside the base image")
                    source.seek(start)
                    chunk = source.read(length)
                elif op == "l":
                    if where < 0 or where + length > len(literal):
                        raise DeltaError("a block of the delta points outside its data")
                    chunk = literal[where : where + length]
                else:
                    raise DeltaError(f"unknown block kind {op!r}")
                if len(chunk) != length:
                    raise DeltaError("a block of the delta is shorter than the record says")
                out.write(chunk)
                result.update(chunk)
                written += length
        if written != data["target"]["size"] or result.hexdigest() != data["target"]["sha256"]:
            raise DeltaError("the rebuilt image does not match the target hash of the delta")
        temp.replace(output)
    finally:
        if temp.exists():
            temp.unlink()
    return {"sha256": data["target"]["sha256"], "size": written, "image": str(output)}
