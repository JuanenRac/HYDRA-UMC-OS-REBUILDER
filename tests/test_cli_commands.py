# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_cli_commands.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The commands of the command line, run through main(): the first-boot files, the image build (with the build itself replaced), the profile
# signing round trip, the release and golden-image commands, the cache and the boot test. Every refusal prints one line and returns 1.
# =============================================================================
from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

from hydra_umc_os_rebuilder import extra_commands, image_builder
from hydra_umc_os_rebuilder import main as main_module
from hydra_umc_os_rebuilder.ecosystem_plan import EcosystemPlan, EcosystemPlanEntry
from hydra_umc_os_rebuilder.profile_manifest import freeze_profile, load_profile_manifest, save_profile_manifest

pytest.importorskip("cryptography")

COMMIT = "a" * 40


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(main_module, "_fetch_commit_sha", lambda *a, **k: COMMIT)
    monkeypatch.delenv("HYDRA_UMC_OS_REBUILDER_CONFIG", raising=False)
    monkeypatch.delenv("HYDRA_UMC_FIRSTBOOT_PASSWORD", raising=False)
    monkeypatch.delenv("HYDRA_UMC_FIRSTBOOT_WIFI_PASSWORD", raising=False)
    monkeypatch.delenv("HYDRA_UMC_OS_REBUILDER_PROFILE_PUBKEY", raising=False)
    monkeypatch.delenv("HYDRA_UMC_OS_REBUILDER_REQUIRE_SIGNED", raising=False)


def _plan(*names: str) -> EcosystemPlan:
    return EcosystemPlan(
        entries=tuple(
            EcosystemPlanEntry(name=n, version="0.1.0", role="service", stack="python", git_url=f"https://github.com/JuanenRac/{n}.git", commit_sha=COMMIT)
            for n in names
        ),
        discovery_errors=(),
    )


def _write_config(tmp_path: Path, body: dict) -> Path:
    path = tmp_path / "options.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _run(capsys, *argv: str) -> tuple[int, str, str]:
    code = main_module.main(["--cli", *argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- status and no command --------------------------------------------------------------------------------------------------
def test_status_prints_the_summary_and_the_total(monkeypatch, capsys) -> None:
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: _plan("HYDRA-UMC-SDK", "HYDRA-UMC-SERVER"))
    code, out, _ = _run(capsys, "status")
    assert code == 0
    assert "HYDRA-UMC-SDK" in out
    assert out.strip().splitlines()[-1] == "TOTAL=2"


def test_no_command_in_cli_mode_prints_the_help_and_fails(capsys) -> None:
    code, out, _ = _run(capsys)
    assert code == 1
    assert "profile-freeze" in out


def test_a_password_on_the_command_line_is_refused_with_a_fixed_sentence(tmp_path, capsys) -> None:
    code, _, err = _run(capsys, "config", "--out", str(tmp_path), "--password", "hunter2")
    assert code == 2
    assert err.startswith("REFUSED: ")
    assert "hunter2" not in err


def test_a_broken_secrets_stdin_is_refused(monkeypatch, tmp_path, capsys) -> None:
    import io

    for payload in ("{not json", '["a"]', '{"password": 5}', '{"other": "x"}'):
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        code, _, err = _run(capsys, "config", "--out", str(tmp_path), "--secrets-stdin")
        assert code == 2, payload
        assert "REFUSED" in err


# --- the first-boot files ---------------------------------------------------------------------------------------------------------
def test_config_writes_the_first_boot_script_and_the_command_line_addition(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("HYDRA_UMC_FIRSTBOOT_PASSWORD", "from-the-environment")
    out_dir = tmp_path / "boot"
    code, out, _ = _run(
        capsys, "config", "--out", str(out_dir), "--hostname", "hydra-cm5", "--username", "operator", "--ssh-key", "ssh-ed25519 AAAAC3Nza test@host",
        "--timezone", "Europe/Madrid", "--keyboard", "es", "--locale", "es_ES.UTF-8",
    )
    assert code == 0
    assert out.startswith("CONFIG_WRITTEN out=")
    files = {p.name for p in out_dir.iterdir()}
    assert "cmdline-append.txt" in files
    script = next(out_dir / name for name in files if name != "cmdline-append.txt")
    text = script.read_text(encoding="utf-8")
    assert "hydra-cm5" in text
    assert "from-the-environment" not in text  # only a hash of the password may be written
    assert "\r" not in text
    if sys.platform != "win32":
        assert stat.S_IMODE(script.stat().st_mode) == 0o755


def test_config_with_wifi_carries_the_network_and_the_country(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("HYDRA_UMC_FIRSTBOOT_WIFI_PASSWORD", "wifi-secret-123")
    out_dir = tmp_path / "boot"
    code, _, _ = _run(capsys, "config", "--out", str(out_dir), "--hostname", "h", "--wifi-ssid", "Workshop", "--wifi-country", "ES", "--wifi-hidden")
    assert code == 0
    text = "\n".join(p.read_text(encoding="utf-8") for p in out_dir.iterdir())
    assert "Workshop" in text
    assert "ES" in text


def test_config_with_a_wifi_and_no_country_is_refused_in_one_line(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("HYDRA_UMC_FIRSTBOOT_WIFI_PASSWORD", "wifi-secret-123")
    with pytest.raises(ValueError):
        _run(capsys, "config", "--out", str(tmp_path / "boot"), "--wifi-ssid", "Workshop")


# --- the image build ---------------------------------------------------------------------------------------------------------------------
class _Recorder:
    def __init__(self, ok: bool = True) -> None:
        self.calls: list[dict] = []
        self.ok = ok

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        kwargs["progress"](image_builder.BuildProgress("download", "base image"))
        if not self.ok:
            return image_builder.BuildResult(ok=False, error="the loop device is busy")
        return image_builder.BuildResult(ok=True, output_path=kwargs["output_path"], installed=("HYDRA-UMC-SDK@0.1.0#sha256:abc",))


def _ready_platform(monkeypatch, ok: bool = True, reason: str = "") -> None:
    monkeypatch.setattr(image_builder, "check_build_platform", lambda: image_builder.PlatformCheck(ok, reason))


def test_build_image_is_blocked_with_the_reason_when_the_platform_is_not_right(monkeypatch, tmp_path, capsys) -> None:
    _ready_platform(monkeypatch, False, "needs root")
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: pytest.fail("must not look at the network when blocked"))
    code, out, err = _run(capsys, "build-image", "--out", str(tmp_path / "x.img"))
    assert code == 1
    assert "BUILD_BLOCKED reason=needs root" in err
    assert out == ""


def test_build_image_without_first_boot_flags_builds_with_no_customisation(monkeypatch, tmp_path, capsys) -> None:
    _ready_platform(monkeypatch)
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: _plan("HYDRA-UMC-SDK"))
    recorder = _Recorder()
    monkeypatch.setattr(image_builder, "build_image", recorder)
    code, out, _ = _run(capsys, "build-image", "--out", str(tmp_path / "x.img"))
    assert code == 0
    assert "[download] base image" in out
    assert "BUILD_OK output=" in out
    assert "HYDRA-UMC-SDK@0.1.0" in out
    call = recorder.calls[0]
    assert call["firstboot"] is None
    assert call["grow_mb"] == 0
    assert call["compress"] is False
    assert call["public_image"] is False


def test_build_image_hands_the_options_to_the_builder(monkeypatch, tmp_path, capsys) -> None:
    _ready_platform(monkeypatch)
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: _plan("HYDRA-UMC-SDK"))
    monkeypatch.setenv("HYDRA_UMC_FIRSTBOOT_PASSWORD", "from-the-environment")
    recorder = _Recorder()
    monkeypatch.setattr(image_builder, "build_image", recorder)
    code, _, _ = _run(
        capsys, "build-image", "--out", str(tmp_path / "x.img"), "--work-dir", str(tmp_path / "w"), "--hostname", "hydra", "--username", "op", "--no-ssh",
        "--acknowledge-no-remote-access", "--run-installer", "install_kiosk.sh", "--grow-mb", "512", "--compress", "--public-image",
        "--project-timeout-seconds", "0",
    )
    assert code == 0
    call = recorder.calls[0]
    boot = call["firstboot"]
    assert (boot.hostname, boot.username, boot.enable_ssh, boot.run_installers) == ("hydra", "op", False, ("install_kiosk.sh",))
    assert boot.password == "from-the-environment"
    assert (call["grow_mb"], call["compress"], call["public_image"]) == (512, True, True)
    assert call["project_timeout_seconds"] is None  # 0 means no limit
    assert call["work_dir"] == tmp_path / "w"


def test_build_image_failure_is_one_line_and_exit_one(monkeypatch, tmp_path, capsys) -> None:
    _ready_platform(monkeypatch)
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: _plan("HYDRA-UMC-SDK"))
    monkeypatch.setattr(image_builder, "build_image", _Recorder(ok=False))
    code, _, err = _run(capsys, "build-image", "--out", str(tmp_path / "x.img"))
    assert code == 1
    assert err.strip() == "BUILD_FAILED error=the loop device is busy"


# --- profiles ------------------------------------------------------------------------------------------------------------------------------
def test_profile_freeze_warns_when_the_sdk_commit_cannot_be_resolved(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: _plan("HYDRA-UMC-SERVER"))

    def refuse(*_a, **_k):
        raise OSError("rate limited")

    monkeypatch.setattr(main_module, "_fetch_commit_sha", refuse)
    out_file = tmp_path / "p.json"
    code, out, err = _run(capsys, "profile-freeze", "--name", "bench", "--out", str(out_file))
    assert code == 0
    assert "PROFILE_FROZEN name=bench" in out
    assert "could not resolve the SDK commit" in err
    assert out_file.is_file()


def test_profile_diff_reports_no_change_and_then_a_change(monkeypatch, tmp_path, capsys) -> None:
    plan = _plan("HYDRA-UMC-SERVER")
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(plan, profile_name="bench"), manifest)
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: plan)
    code, out, _ = _run(capsys, "profile-diff", "--manifest", str(manifest))
    assert (code, out.strip()) == (0, "PROFILE_UNCHANGED name=bench")
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: _plan("HYDRA-UMC-SERVER", "HYDRA-UMC-DSI"))
    code, out, _ = _run(capsys, "profile-diff", "--manifest", str(manifest))
    assert code == 0
    assert "HYDRA-UMC-DSI" in out
    assert "TOTAL_CHANGES=" in out


def test_profile_update_writes_to_a_new_file_and_leaves_the_original(monkeypatch, tmp_path, capsys) -> None:
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(_plan("HYDRA-UMC-SERVER"), profile_name="bench"), manifest)
    before = manifest.read_text(encoding="utf-8")
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: _plan("HYDRA-UMC-SERVER"))
    target = tmp_path / "next.json"
    code, out, _ = _run(capsys, "profile-update", "--manifest", str(manifest), "--project", "HYDRA-UMC-SERVER", "--out", str(target))
    assert code == 0
    assert "PROFILE_UPDATED name=bench" in out
    assert target.is_file()
    assert manifest.read_text(encoding="utf-8") == before


def test_required_resources_are_set_and_a_bad_project_is_refused(tmp_path, capsys) -> None:
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(_plan("HYDRA-UMC-SERVER"), profile_name="bench"), manifest)
    code, out, _ = _run(capsys, "profile-set-required-resources", "--manifest", str(manifest), "--project", "HYDRA-UMC-SERVER", "--resource", "run.sh", "--resource", "src/app.py")
    assert code == 0
    assert "resources=2" in out
    code, _, err = _run(capsys, "profile-set-required-resources", "--manifest", str(manifest), "--project", "NOT-THERE", "--resource", "x")
    assert code == 1
    assert err.startswith("PROFILE_RESOURCES_FAILED error=")


# --- signing a profile ----------------------------------------------------------------------------------------------------------------------
def _keys(tmp_path: Path, capsys) -> tuple[Path, str]:
    private, public = tmp_path / "private.key", tmp_path / "public.key"
    code, out, _ = _run(capsys, "profile-keygen", "--private-out", str(private), "--public-out", str(public))
    assert code == 0
    assert out.startswith("PROFILE_KEYGEN_OK public=")
    return private, public.read_text(encoding="utf-8").strip()


def test_sign_and_verify_round_trip_and_a_changed_manifest_is_refused(tmp_path, capsys) -> None:
    private, public = _keys(tmp_path, capsys)
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(_plan("HYDRA-UMC-SERVER"), profile_name="bench"), manifest)
    code, out, _ = _run(capsys, "profile-sign", "--manifest", str(manifest), "--key-file", str(private))
    assert code == 0 and out.startswith("PROFILE_SIGNED signature=")
    code, out, _ = _run(capsys, "profile-verify", "--manifest", str(manifest), "--trusted-key", public)
    assert (code, out.strip()) == (0, "PROFILE_VERIFIED")
    manifest.write_text(manifest.read_text(encoding="utf-8").replace("bench", "bench2"), encoding="utf-8")
    code, _, err = _run(capsys, "profile-verify", "--manifest", str(manifest), "--trusted-key", public)
    assert code == 1
    assert err.startswith("PROFILE_VERIFY_FAILED error=")


def test_verify_takes_the_trusted_key_from_the_environment(monkeypatch, tmp_path, capsys) -> None:
    private, public = _keys(tmp_path, capsys)
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(_plan("HYDRA-UMC-SERVER"), profile_name="bench"), manifest)
    _run(capsys, "profile-sign", "--manifest", str(manifest), "--key-file", str(private))
    monkeypatch.setenv("HYDRA_UMC_OS_REBUILDER_PROFILE_PUBKEY", public)
    code, out, _ = _run(capsys, "profile-verify", "--manifest", str(manifest))
    assert (code, out.strip()) == (0, "PROFILE_VERIFIED")


def test_verify_with_no_key_and_sign_with_a_missing_key_fail_in_one_line(tmp_path, capsys) -> None:
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(_plan("HYDRA-UMC-SERVER"), profile_name="bench"), manifest)
    code, _, err = _run(capsys, "profile-verify", "--manifest", str(manifest))
    assert code == 1 and err.startswith("PROFILE_VERIFY_FAILED")
    code, _, err = _run(capsys, "profile-sign", "--manifest", str(manifest), "--key-file", str(tmp_path / "absent.key"))
    assert code == 1 and err.startswith("PROFILE_SIGN_FAILED")


def test_keygen_into_a_folder_that_does_not_exist_fails_in_one_line(tmp_path, capsys) -> None:
    code, _, err = _run(capsys, "profile-keygen", "--private-out", str(tmp_path / "no" / "such" / "a.key"), "--public-out", str(tmp_path / "b.key"))
    assert code == 1
    assert err.startswith("PROFILE_KEYGEN_FAILED error=")


def test_profile_build_requires_a_trusted_key_when_a_signature_is_asked_for(tmp_path, capsys, monkeypatch) -> None:
    _ready_platform(monkeypatch)
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(_plan("HYDRA-UMC-SERVER"), profile_name="bench"), manifest)
    code, _, err = _run(capsys, "profile-build", "--manifest", str(manifest), "--out", str(tmp_path / "x.img"), "--require-signed")
    assert code == 1
    assert "BUILD_BLOCKED" in err
    assert "no trusted public key" in err


def test_profile_build_with_a_bad_signature_never_reaches_the_build(tmp_path, capsys, monkeypatch) -> None:
    _ready_platform(monkeypatch)
    _private, public = _keys(tmp_path, capsys)
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(_plan("HYDRA-UMC-SERVER"), profile_name="bench"), manifest)
    monkeypatch.setattr(image_builder, "build_image", lambda **_k: pytest.fail("the build must not start"))
    code, _, err = _run(capsys, "profile-build", "--manifest", str(manifest), "--out", str(tmp_path / "x.img"), "--require-signed", "--trusted-key", public)
    assert code == 1  # there is no signature file at all
    assert "BUILD_BLOCKED" in err


def test_profile_build_unsigned_records_the_hashes_in_the_manifest(tmp_path, capsys, monkeypatch) -> None:
    _ready_platform(monkeypatch)
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(_plan("HYDRA-UMC-SDK"), profile_name="bench"), manifest)
    recorder = _Recorder()
    monkeypatch.setattr(image_builder, "build_image", recorder)
    code, out, _ = _run(capsys, "profile-build", "--manifest", str(manifest), "--out", str(tmp_path / "x.img"), "--work-dir", str(tmp_path / "w"))
    assert code == 0
    assert "BUILD_OK" in out
    assert "PROFILE_BUILD_RECORDED" not in out
    assert "sha256:abc" in manifest.read_text(encoding="utf-8")
    assert recorder.calls[0]["firstboot"] is None


def test_profile_build_signed_leaves_the_signed_file_alone_and_records_next_to_it(tmp_path, capsys, monkeypatch) -> None:
    _ready_platform(monkeypatch)
    private, public = _keys(tmp_path, capsys)
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(_plan("HYDRA-UMC-SDK"), profile_name="bench"), manifest)
    _run(capsys, "profile-sign", "--manifest", str(manifest), "--key-file", str(private))
    signed_bytes = manifest.read_bytes()
    monkeypatch.setattr(image_builder, "build_image", _Recorder())
    code, out, _ = _run(capsys, "profile-build", "--manifest", str(manifest), "--out", str(tmp_path / "x.img"), "--require-signed", "--trusted-key", public)
    assert code == 0
    assert "PROFILE_BUILD_RECORDED path=" in out
    assert manifest.read_bytes() == signed_bytes
    recorded = tmp_path / "p.built.json"
    assert recorded.is_file()
    assert load_profile_manifest(recorded).profile_name == "bench"


def test_profile_build_failure_does_not_touch_the_manifest(tmp_path, capsys, monkeypatch) -> None:
    _ready_platform(monkeypatch)
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(_plan("HYDRA-UMC-SDK"), profile_name="bench"), manifest)
    before = manifest.read_bytes()
    monkeypatch.setattr(image_builder, "build_image", _Recorder(ok=False))
    code, _, err = _run(capsys, "profile-build", "--manifest", str(manifest), "--out", str(tmp_path / "x.img"))
    assert code == 1
    assert "BUILD_FAILED" in err
    assert manifest.read_bytes() == before


def test_profile_build_blocked_platform_is_reported_after_the_signature(tmp_path, capsys, monkeypatch) -> None:
    _ready_platform(monkeypatch, False, "needs root")
    manifest = tmp_path / "p.json"
    save_profile_manifest(freeze_profile(_plan("HYDRA-UMC-SDK"), profile_name="bench"), manifest)
    code, _, err = _run(capsys, "profile-build", "--manifest", str(manifest), "--out", str(tmp_path / "x.img"))
    assert code == 1
    assert "BUILD_BLOCKED reason=needs root" in err


# --- the commands of extra_commands --------------------------------------------------------------------------------------------------
def test_build_plan_prints_json_and_writes_a_pi_gen_stage(tmp_path, capsys) -> None:
    config = _write_config(tmp_path, {"build_backend": {"name": "pigen", "pigen": {"checkout": str(tmp_path / "pi-gen")}}})
    stage = tmp_path / "stage"
    code, out, _ = _run(capsys, "build-plan", "--config", str(config), "--project", "HYDRA-UMC-SDK=" + COMMIT, "--write-pigen-stage", str(stage))
    assert code == 0
    plan = json.loads(out)
    assert plan["written"]
    assert stage.is_dir()


def test_build_plan_with_the_default_backend_runs_nothing(tmp_path, capsys) -> None:
    code, out, _ = _run(capsys, "build-plan")
    assert code == 0
    assert "written" not in json.loads(out)


def test_an_unusable_options_file_is_one_line_and_exit_one(tmp_path, capsys) -> None:
    code, _, err = _run(capsys, "build-plan", "--config", str(tmp_path / "absent.json"))
    assert code == 1
    assert err.startswith("BUILD_PLAN_FAILED error=")
    bad = _write_config(tmp_path, {"unknown_key": 1})
    code, _, err = _run(capsys, "cache-status", "--config", str(bad))
    assert code == 1
    assert err.startswith("CACHE_STATUS_FAILED error=")


def test_the_cache_is_off_without_options_and_reports_when_on(tmp_path, capsys) -> None:
    code, out, _ = _run(capsys, "cache-status")
    assert (code, json.loads(out)) == (0, {"enabled": False})
    code, out, _ = _run(capsys, "cache-prune")
    assert (code, json.loads(out)) == (0, {"removed": []})
    config = _write_config(tmp_path, {"artifact_cache": {"enabled": True, "directory": str(tmp_path / "cache"), "max_gb": 1}})
    code, out, _ = _run(capsys, "cache-status", "--config", str(config))
    assert code == 0
    assert json.loads(out)["enabled"] is True
    code, out, _ = _run(capsys, "cache-prune", "--config", str(config))
    assert (code, json.loads(out)) == (0, {"removed": []})


def test_release_manifest_sign_and_verify_round_trip(tmp_path, capsys) -> None:
    private, public = _keys(tmp_path, capsys)
    image = tmp_path / "hydra.img"
    image.write_bytes(b"not a real image, but bytes")
    manifest = tmp_path / "release.json"
    code, out, _ = _run(capsys, "release-manifest", "--image", str(image), "--version", "0.1.0", "--commit", COMMIT, "--output", str(manifest))
    assert code == 0
    assert "RELEASE_MANIFEST_OK" in out
    assert "TAG_COMMAND git tag -s image-v0.1.0" in out
    assert json.loads(manifest.read_text(encoding="utf-8"))["version"] == "0.1.0"
    code, out, _ = _run(capsys, "release-sign", "--manifest", str(manifest), "--key-file", str(private))
    assert code == 0 and out.startswith("RELEASE_SIGNED signature=")
    code, out, _ = _run(capsys, "release-verify", "--manifest", str(manifest), "--image", str(image), "--trusted-key", public)
    assert code == 0 and out.startswith("RELEASE_VERIFIED ")
    image.write_bytes(b"a different image")
    code, _, err = _run(capsys, "release-verify", "--manifest", str(manifest), "--image", str(image), "--trusted-key", public)
    assert code == 1
    assert err.startswith("RELEASE_VERIFY_FAILED error=")


def test_release_manifest_refuses_a_short_commit_and_a_missing_image(tmp_path, capsys) -> None:
    image = tmp_path / "hydra.img"
    image.write_bytes(b"x")
    code, _, err = _run(capsys, "release-manifest", "--image", str(image), "--version", "0.1.0", "--commit", "abc123", "--output", str(tmp_path / "r.json"))
    assert code == 1 and err.startswith("RELEASE_MANIFEST_FAILED")
    code, _, err = _run(capsys, "release-manifest", "--image", str(tmp_path / "none.img"), "--version", "0.1.0", "--commit", COMMIT, "--output", str(tmp_path / "r.json"))
    assert code == 1 and err.startswith("RELEASE_MANIFEST_FAILED")


def test_golden_image_register_verify_and_the_minimum_version(tmp_path, capsys) -> None:
    private, public = _keys(tmp_path, capsys)
    image = tmp_path / "golden.img"
    image.write_bytes(b"known good bytes")
    store = tmp_path / "store"
    store.mkdir()
    code, out, _ = _run(capsys, "golden-register", "--image", str(image), "--store", str(store), "--version", "1.2.0", "--commit", COMMIT, "--key-file", str(private))
    assert code == 0 and out.startswith("GOLDEN_REGISTERED record=")
    code, out, _ = _run(capsys, "golden-verify", "--store", str(store), "--trusted-key", public)
    assert code == 0 and out.startswith("GOLDEN_VERIFIED ")
    code, _, err = _run(capsys, "golden-verify", "--store", str(store), "--trusted-key", public, "--minimum-version", "1.10.0")
    assert code == 1 and err.startswith("GOLDEN_VERIFY_FAILED")
    code, _, err = _run(capsys, "golden-register", "--image", str(image), "--store", str(store), "--version", "1.3.0", "--commit", COMMIT, "--key-file", str(private))
    assert code == 1 and err.startswith("GOLDEN_REGISTER_FAILED")  # an existing golden image is only replaced on request
    code, _, _ = _run(capsys, "golden-register", "--image", str(image), "--store", str(store), "--version", "1.3.0", "--commit", COMMIT, "--key-file", str(private), "--replace")
    assert code == 0
    image_hash_before = image.read_bytes()
    (store / next(p.name for p in store.iterdir() if p.suffix == ".img")).write_bytes(b"tampered")
    code, _, err = _run(capsys, "golden-verify", "--store", str(store), "--trusted-key", public)
    assert code == 1 and err.startswith("GOLDEN_VERIFY_FAILED")
    assert image.read_bytes() == image_hash_before


def test_golden_verify_without_any_trusted_key_is_refused(tmp_path, capsys) -> None:
    store = tmp_path / "store"
    store.mkdir()
    code, _, err = _run(capsys, "golden-verify", "--store", str(store))
    assert code == 1
    assert err.startswith("GOLDEN_VERIFY_FAILED")


def test_boot_test_is_skipped_when_it_is_off_and_fails_on_a_failed_state(monkeypatch, tmp_path, capsys) -> None:
    image = tmp_path / "x.img"
    image.write_bytes(b"x")
    code, out, _ = _run(capsys, "boot-test", "--image", str(image))
    assert code == 0
    assert json.loads(out)["state"] not in ("failed", "no-result")
    for state, expected in (("failed", 1), ("no-result", 1), ("ready", 0), ("skipped", 0)):
        monkeypatch.setattr(extra_commands.boot_test, "run_boot_test", lambda *_a, _s=state, **_k: {"state": _s})
        code, _, _ = _run(capsys, "boot-test", "--image", str(image))
        assert code == expected, state


def test_the_failure_line_is_named_after_the_command(monkeypatch, capsys) -> None:
    import argparse

    def explode(_args):
        raise OSError("disk gone")

    monkeypatch.setitem(extra_commands.HANDLERS, "cache-status", explode)
    code = extra_commands.run(argparse.Namespace(command="cache-status"))
    assert code == 1
    assert capsys.readouterr().err.strip() == "CACHE_STATUS_FAILED error=disk gone"
