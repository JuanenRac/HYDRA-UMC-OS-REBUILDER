# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_golden_image.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The golden image kept on the host: signed with a throw-away key made by each test, never with a key of the project."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("cryptography")

from hydra_umc_os_rebuilder import golden_image, profile_signing, release_channel  # noqa: E402
from hydra_umc_os_rebuilder.golden_image import GoldenError  # noqa: E402

COMMIT = "c" * 40


@pytest.fixture()
def setup(tmp_path: Path) -> tuple[Path, Path, str, Path]:
    private, public = tmp_path / "k", tmp_path / "k.pub"
    public_hex = profile_signing.generate_keypair(private, public)
    image = tmp_path / "golden-0.1.0.img"
    image.write_bytes(b"known good image")
    return private, tmp_path / "store", public_hex, image


def test_register_then_verify_gives_the_image_back(setup) -> None:
    private, store, public_hex, image = setup
    golden_image.register(image, store, "0.1.0", COMMIT, str(private))
    result = golden_image.verify(store, public_hex)
    assert result["version"] == "0.1.0" and Path(result["image"]).read_bytes() == b"known good image"
    assert golden_image.verify(store, public_hex, minimum_version="0.1.0")["commit"] == COMMIT


def test_a_changed_image_record_or_key_is_refused(setup, tmp_path: Path) -> None:
    private, store, public_hex, image = setup
    golden_image.register(image, store, "0.1.0", COMMIT, str(private))
    stored = store / image.name
    stored.write_bytes(b"tampered image!")
    with pytest.raises(GoldenError):
        golden_image.verify(store, public_hex)
    stored.write_bytes(b"known good image")
    other_public = profile_signing.generate_keypair(tmp_path / "o", tmp_path / "o.pub")
    with pytest.raises(GoldenError):
        golden_image.verify(store, other_public)
    with pytest.raises(GoldenError):  # no trusted key at all
        golden_image.verify(store, "")
    record = store / "golden.json"
    record.write_text(record.read_text(encoding="utf-8").replace("0.1.0", "9.9.9"), encoding="utf-8")
    with pytest.raises(GoldenError):  # record changed after signing
        golden_image.verify(store, public_hex)
    (store / "golden.json.sig").unlink()
    with pytest.raises(GoldenError):
        golden_image.verify(store, public_hex)


def test_a_release_signature_cannot_pass_as_a_golden_one(setup) -> None:
    private, store, public_hex, image = setup
    golden_image.register(image, store, "0.1.0", COMMIT, str(private))
    forged = release_channel.sign_release(store / "golden.json", str(private))  # same key, the release domain
    (store / "golden.json.sig").write_text(forged.read_text(encoding="utf-8"), encoding="utf-8")
    forged.unlink()
    with pytest.raises(GoldenError):
        golden_image.verify(store, public_hex)


def test_replacing_needs_a_newer_version_and_says_so(setup, tmp_path: Path) -> None:
    private, store, public_hex, image = setup
    golden_image.register(image, store, "0.1.0", COMMIT, str(private))
    with pytest.raises(GoldenError):  # silently replacing is refused
        golden_image.register(image, store, "0.2.0", COMMIT, str(private))
    newer = tmp_path / "golden-0.2.0.img"
    newer.write_bytes(b"newer good image")
    with pytest.raises(GoldenError):  # going back is refused
        golden_image.register(newer, store, "0.1.0", COMMIT, str(private), replace=True)
    golden_image.register(newer, store, "0.2.0", COMMIT, str(private), replace=True)
    assert golden_image.verify(store, public_hex)["version"] == "0.2.0"
    assert not (store / image.name).exists()
    with pytest.raises(GoldenError):
        golden_image.verify(store, public_hex, minimum_version="0.3.0")


def test_bad_inputs_are_refused_before_anything_is_written(setup, tmp_path: Path) -> None:
    private, store, _public_hex, image = setup
    for version, commit in (("v1", COMMIT), ("0.1.0", "abc")):
        with pytest.raises(GoldenError):
            golden_image.register(image, store, version, commit, str(private))
    with pytest.raises(GoldenError):
        golden_image.register(tmp_path / "missing.img", store, "0.1.0", COMMIT, str(private))
    assert not store.exists()
