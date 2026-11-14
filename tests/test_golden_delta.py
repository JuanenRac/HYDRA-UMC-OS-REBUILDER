# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_golden_delta.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The signed delta between two images, made and read back with a throw-away key made by each test."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

pytest.importorskip("cryptography")

from hydra_umc_os_rebuilder import golden_delta, profile_signing  # noqa: E402
from hydra_umc_os_rebuilder.golden_delta import DeltaError  # noqa: E402

BLOCK = 512


def _images(tmp_path: Path, seed: int = 7) -> tuple[Path, Path]:
    rng = random.Random(seed)
    old = bytearray(rng.randbytes(BLOCK * 20 + 100))  # a short last block on purpose
    new = bytearray(old)
    new[BLOCK * 3 : BLOCK * 3 + 40] = b"\xaa" * 40  # one changed block
    new += rng.randbytes(BLOCK + 17)  # and a longer image
    base, target = tmp_path / "old.img", tmp_path / "new.img"
    base.write_bytes(bytes(old))
    target.write_bytes(bytes(new))
    return base, target


@pytest.fixture()
def keys(tmp_path: Path) -> tuple[Path, str]:
    private, public = tmp_path / "k", tmp_path / "k.pub"
    return private, profile_signing.generate_keypair(private, public)


def test_a_delta_rebuilds_the_target_and_carries_only_the_changed_blocks(tmp_path: Path, keys) -> None:
    private, public = keys
    base, target = _images(tmp_path)
    store = tmp_path / "delta"
    golden_delta.create(base, target, store, str(private), block_size=BLOCK)
    assert (store / "delta.bin").stat().st_size < target.stat().st_size // 3  # most blocks are copied from the base
    out = tmp_path / "rebuilt.img"
    result = golden_delta.apply(base, store, public, out)
    assert out.read_bytes() == target.read_bytes() and result["size"] == target.stat().st_size


def test_a_wrong_base_a_wrong_key_and_a_changed_record_are_refused(tmp_path: Path, keys) -> None:
    private, public = keys
    base, target = _images(tmp_path)
    store = tmp_path / "delta"
    golden_delta.create(base, target, store, str(private), block_size=BLOCK)
    other = tmp_path / "other.img"
    other.write_bytes(base.read_bytes()[:-1] + b"?")
    out = tmp_path / "rebuilt.img"
    with pytest.raises(DeltaError, match="base image"):
        golden_delta.apply(other, store, public, out)
    other_public = profile_signing.generate_keypair(tmp_path / "o", tmp_path / "o.pub")
    with pytest.raises(DeltaError, match="signature"):
        golden_delta.apply(base, store, other_public, out)
    with pytest.raises(DeltaError, match="trusted public key"):
        golden_delta.apply(base, store, "", out)
    record = store / "delta.json"
    record.write_text(record.read_text(encoding="utf-8").replace('"block_size": 512', '"block_size": 1024'), encoding="utf-8")
    with pytest.raises(DeltaError, match="signature"):
        golden_delta.apply(base, store, public, out)
    assert not out.exists()


def test_tampered_data_leaves_no_output_and_no_partial_file(tmp_path: Path, keys) -> None:
    private, public = keys
    base, target = _images(tmp_path)
    store = tmp_path / "delta"
    golden_delta.create(base, target, store, str(private), block_size=BLOCK)
    payload = store / "delta.bin"
    data = bytearray(payload.read_bytes())
    data[0] ^= 1
    payload.write_bytes(bytes(data))
    out = tmp_path / "rebuilt.img"
    with pytest.raises(DeltaError, match="delta.bin"):
        golden_delta.apply(base, store, public, out)
    assert not out.exists() and not (tmp_path / "rebuilt.img.partial").exists()


def test_bad_inputs_are_refused_before_anything_is_written(tmp_path: Path, keys) -> None:
    private, _ = keys
    base, target = _images(tmp_path)
    with pytest.raises(DeltaError, match="not a file"):
        golden_delta.create(tmp_path / "none", target, tmp_path / "d", str(private))
    with pytest.raises(DeltaError, match="block size"):
        golden_delta.create(base, target, tmp_path / "d", str(private), block_size=16)
    assert not (tmp_path / "d").exists()


def test_the_signature_of_a_golden_image_cannot_pass_as_a_delta_signature(tmp_path: Path, keys) -> None:
    private, public = keys
    base, target = _images(tmp_path)
    store = tmp_path / "delta"
    golden_delta.create(base, target, store, str(private), block_size=BLOCK)
    assert golden_delta._DOMAIN != b"hydra-umc-os-rebuilder-golden/1\n"
    (store / "delta.json.sig").write_text("00" * 64 + "\n", encoding="utf-8")
    with pytest.raises(DeltaError, match="signature"):
        golden_delta.apply(base, store, public, tmp_path / "x.img")
