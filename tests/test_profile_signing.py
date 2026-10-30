# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_profile_signing.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A signed profile manifest: a changed file, a foreign key, a missing signature and a wrong key file are all refused.
Skipped where the `cryptography` package is not installed."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("cryptography")

from hydra_umc_os_rebuilder import main as main_module  # noqa: E402
from hydra_umc_os_rebuilder import profile_signing  # noqa: E402
from hydra_umc_os_rebuilder.profile_signing import ProfileSigningError  # noqa: E402


@pytest.fixture()
def keys(tmp_path: Path) -> tuple[Path, Path, str]:
    private, public = tmp_path / "profile.key", tmp_path / "profile.pub"
    public_hex = profile_signing.generate_keypair(private, public)
    return private, public, public_hex


@pytest.fixture()
def manifest(tmp_path: Path) -> Path:
    path = tmp_path / "profile.json"
    path.write_text('{"profile_name": "p", "entries": []}', encoding="utf-8")
    return path


def test_a_signed_manifest_verifies_with_the_key_given_as_a_file_or_as_hex(keys, manifest: Path) -> None:
    private, public, public_hex = keys
    signature = profile_signing.sign_manifest(manifest, str(private))
    assert signature == manifest.with_name("profile.json.sig")
    profile_signing.verify_manifest(manifest, str(public))
    profile_signing.verify_manifest(manifest, public_hex)


def test_a_manifest_changed_after_signing_is_refused(keys, manifest: Path) -> None:
    private, _public, public_hex = keys
    profile_signing.sign_manifest(manifest, str(private))
    manifest.write_text('{"profile_name": "p", "entries": [{"name": "evil"}]}', encoding="utf-8")
    with pytest.raises(ProfileSigningError, match="does not match"):
        profile_signing.verify_manifest(manifest, public_hex)


def test_a_signature_by_another_key_is_refused(keys, manifest: Path, tmp_path: Path) -> None:
    _private, _public, public_hex = keys
    other_private = tmp_path / "other.key"
    profile_signing.generate_keypair(other_private, tmp_path / "other.pub")
    profile_signing.sign_manifest(manifest, str(other_private))
    with pytest.raises(ProfileSigningError, match="does not match"):
        profile_signing.verify_manifest(manifest, public_hex)


def test_a_missing_or_garbled_signature_and_a_bad_key_are_refused(keys, manifest: Path) -> None:
    _private, _public, public_hex = keys
    with pytest.raises(ProfileSigningError, match="no signature"):
        profile_signing.verify_manifest(manifest, public_hex)
    manifest.with_name("profile.json.sig").write_text("not hex", encoding="utf-8")
    with pytest.raises(ProfileSigningError, match="not a hexadecimal"):
        profile_signing.verify_manifest(manifest, public_hex)
    manifest.with_name("profile.json.sig").write_text("ab" * 64, encoding="utf-8")
    with pytest.raises(ProfileSigningError, match="trusted public key"):
        profile_signing.verify_manifest(manifest, "short")


def test_a_key_is_never_overwritten(keys) -> None:
    private, public, _hex = keys
    with pytest.raises(ProfileSigningError, match="not overwriting"):
        profile_signing.generate_keypair(private, public)


def test_the_commands_sign_and_verify_and_the_build_switch_follows_the_environment(
    keys, manifest: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    private, public, _hex = keys
    assert main_module.main(["--cli", "profile-sign", "--manifest", str(manifest), "--key-file", str(private)]) == 0
    assert main_module.main(["--cli", "profile-verify", "--manifest", str(manifest), "--trusted-key", str(public)]) == 0
    manifest.write_text("{}", encoding="utf-8")
    assert main_module.main(["--cli", "profile-verify", "--manifest", str(manifest), "--trusted-key", str(public)]) == 1
    assert "PROFILE_VERIFY_FAILED" in capsys.readouterr().err

    monkeypatch.delenv(profile_signing.REQUIRE_SIGNED_ENV, raising=False)
    assert profile_signing.signature_required() is False
    monkeypatch.setenv(profile_signing.REQUIRE_SIGNED_ENV, "1")
    assert profile_signing.signature_required() is True


def test_a_build_that_requires_a_signature_stops_before_anything_else(
    keys, manifest: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _private, _public, public_hex = keys
    monkeypatch.delenv(profile_signing.TRUSTED_KEY_ENV, raising=False)
    base = ["--cli", "profile-build", "--manifest", str(manifest), "--out", str(manifest.parent / "x.img"), "--require-signed"]
    assert main_module.main(base) == 1
    assert "no trusted public key" in capsys.readouterr().err
    assert main_module.main([*base, "--trusted-key", public_hex]) == 1
    assert "no signature file" in capsys.readouterr().err
