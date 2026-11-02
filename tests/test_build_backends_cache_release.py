# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_build_backends_cache_release.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Build backends, the artifact cache, the signed release channel and the boot test: planned and checked with stand-ins, nothing is run."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from hydra_umc_os_rebuilder import artifact_cache, boot_test, build_backends, build_config, extra_commands, main as main_module, release_channel

COMMIT = "a" * 40


def _config(**sections: dict) -> dict:
    config = build_config.load_config()
    for key, value in sections.items():
        config[key].update(value)
    return config


def test_defaults_are_off_and_unknown_keys_refused(tmp_path: Path) -> None:
    config = build_config.load_config()
    assert config["build_backend"]["name"] == "chroot"
    assert config["artifact_cache"]["enabled"] is False and config["boot_test"]["enabled"] is False
    assert config["release_channel"]["require_signed_tag"] is False
    bad = tmp_path / "c.json"
    bad.write_text(json.dumps({"artifact_cache": {"enabeld": True}}), encoding="utf-8")
    with pytest.raises(build_config.BuildConfigError):
        build_config.load_config(bad)
    bad.write_text(json.dumps({"build_backend": {"name": "docker"}}), encoding="utf-8")
    with pytest.raises(build_config.BuildConfigError):
        build_config.load_config(bad)
    bad.write_text(json.dumps({"artifact_cache": {"enabled": "yes"}}), encoding="utf-8")
    with pytest.raises(build_config.BuildConfigError):
        build_config.load_config(bad)


def test_example_file_loads_and_equals_defaults() -> None:
    example = Path(__file__).resolve().parent.parent / "config" / "rebuilder.example.json"
    assert build_config.load_config(example) == build_config.load_config()


def test_nspawn_command_and_pigen_stage(tmp_path: Path) -> None:
    config = _config()
    command = build_backends.nspawn_command(tmp_path / "root", ["/bin/true"], config, bind_ro={"/srv/src": "/opt/src"})
    assert command[0] == "systemd-nspawn" and command[-2:] == ["--", "/bin/true"] and "/srv/src:/opt/src" in command
    with pytest.raises(build_backends.BackendError):
        build_backends.nspawn_command(tmp_path, ["x"], config, bind_ro={"a:b": "/c"})
    files = build_backends.pigen_stage_files({"HYDRA-UMC-OS": "b" * 40}, config)
    assert "stage-hydra/00-checkouts/00-run.sh" in files and "STAGE_LIST='stage0 stage1 stage2 stage-hydra'" in files["config"]
    with pytest.raises(build_backends.BackendError):
        build_backends.pigen_stage_files({"x; rm": COMMIT}, config)
    with pytest.raises(build_backends.BackendError):
        build_backends.pigen_stage_files({"ok": "main"}, config)
    written = build_backends.write_pigen_stage(tmp_path / "stage", {"A": COMMIT}, config)
    assert written and all(p.is_file() for p in written)
    with pytest.raises(build_backends.BackendError):
        build_backends.write_pigen_stage(tmp_path / "stage", {"A": COMMIT}, config)


def test_plan_reports_missing_tools_and_runs_nothing(tmp_path: Path) -> None:
    config = _config(build_backend={"name": "pigen"})
    plan = build_backends.plan_backend(config, {"A": COMMIT})
    assert plan["runs_anything"] is False and plan["missing_tools"]


def test_cache_hit_miss_tamper_and_prune(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "f.txt").write_text("one", encoding="utf-8")
    cache = artifact_cache.ArtifactCache(tmp_path / "cache", max_gb=1)
    assert cache.lookup("P", COMMIT) is None
    payload = cache.store("P", COMMIT, source)
    assert cache.lookup("P", COMMIT) == payload
    (payload / "f.txt").write_text("changed", encoding="utf-8")
    assert cache.lookup("P", COMMIT) is None and cache.status()["entries"] == 0
    with pytest.raises(artifact_cache.CacheError):
        cache.lookup("P", "main")
    with pytest.raises(artifact_cache.CacheError):
        cache.lookup("../x", COMMIT)
    small = artifact_cache.ArtifactCache(tmp_path / "small", max_gb=0)
    small.store("P", "1" * 40, source)
    small.store("P", "2" * 40, source)
    assert small.status()["entries"] == 1 and small.lookup("P", "2" * 40) is not None


def test_cache_off_by_default() -> None:
    assert artifact_cache.ArtifactCache.from_config(_config()) is None


class _Git:
    def __init__(self, ok: bool, commit: str) -> None:
        self.ok, self.commit = ok, commit

    def __call__(self, command: list[str], cwd: Path) -> "subprocess.CompletedProcess[str]":
        if command[1] == "verify-tag":
            return subprocess.CompletedProcess(command, 0 if self.ok else 1, "", "" if self.ok else "bad signature")
        return subprocess.CompletedProcess(command, 0, self.commit + "\n", "")


def test_release_roundtrip_and_refusals(tmp_path: Path) -> None:
    pytest.importorskip("cryptography")
    from hydra_umc_os_rebuilder import profile_signing

    private, public = tmp_path / "k", tmp_path / "k.pub"
    public_hex = profile_signing.generate_keypair(private, public)
    image = tmp_path / "hydra.img"
    image.write_bytes(b"image bytes")
    config = _config(release_channel={"require_signed_tag": True, "require_signed_manifest": True})
    manifest = release_channel.make_manifest(image, "0.4.0", COMMIT, tmp_path / "release.json", config)
    assert release_channel.tag_command("0.4.0", COMMIT, config)[:3] == ["git", "tag", "-s"]
    release_channel.sign_release(manifest, str(private))
    ok = release_channel.verify_release(manifest, image, config, trusted_key=public_hex, repo=tmp_path, run=_Git(True, COMMIT))
    assert ok["checked"] == ["sha256", "signature", "tag"]
    with pytest.raises(release_channel.ReleaseError):  # bad tag signature
        release_channel.verify_release(manifest, image, config, trusted_key=public_hex, repo=tmp_path, run=_Git(False, COMMIT))
    with pytest.raises(release_channel.ReleaseError):  # tag on another commit
        release_channel.verify_release(manifest, image, config, trusted_key=public_hex, repo=tmp_path, run=_Git(True, "b" * 40))
    with pytest.raises(release_channel.ReleaseError):  # no repository
        release_channel.verify_release(manifest, image, config, trusted_key=public_hex)
    with pytest.raises(release_channel.ReleaseError):  # no key
        release_channel.verify_release(manifest, image, config, repo=tmp_path, run=_Git(True, COMMIT))
    image.write_bytes(b"tampered")
    with pytest.raises(release_channel.ReleaseError):
        release_channel.verify_release(manifest, image, config, trusted_key=public_hex, repo=tmp_path, run=_Git(True, COMMIT))
    image.write_bytes(b"image bytes")
    manifest.write_text(manifest.read_text(encoding="utf-8").replace("0.4.0", "0.4.1"), encoding="utf-8")
    with pytest.raises(release_channel.ReleaseError):  # manifest changed after signing
        release_channel.verify_release(manifest, image, config, trusted_key=public_hex, repo=tmp_path, run=_Git(True, COMMIT))
    with pytest.raises(release_channel.ReleaseError):
        release_channel.tag_command("0.4.0; rm", COMMIT, config)


def test_boot_log_and_skips(tmp_path: Path) -> None:
    config = _config()
    assert boot_test.read_boot_log("x\nraspberrypi login: ", config)["state"] == "ready"
    assert boot_test.read_boot_log("Kernel panic - not syncing\nlogin:", config)["state"] == "failed"
    assert boot_test.read_boot_log("nothing", config)["state"] == "no-result"
    image = tmp_path / "i.img"
    image.write_bytes(b"x")
    off = boot_test.run_boot_test(image, config, launch=lambda c, t: pytest.fail("must not launch"))
    assert off["state"] == "skipped"
    on = _config(boot_test={"enabled": True})
    missing = boot_test.run_boot_test(image, on, launch=lambda c, t: pytest.fail("must not launch"), which=lambda n: None)
    assert missing["state"] == "skipped" and "not installed" in missing["reason"]
    seen: list[list[str]] = []
    ran = boot_test.run_boot_test(image, on, launch=lambda c, t: seen.append(c) or "login: ", which=lambda n: "/usr/bin/qemu")
    assert ran["state"] == "ready" and "snapshot=on" in " ".join(seen[0])
    with pytest.raises(boot_test.BootTestError):
        boot_test.ssh_verify_command(on)


def test_cli_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main_module.main(["--cli", "build-plan", "--project", f"A={COMMIT}"]) == 0
    assert json.loads(capsys.readouterr().out)["backend"] == "chroot"
    assert main_module.main(["--cli", "cache-status"]) == 0
    assert json.loads(capsys.readouterr().out) == {"enabled": False}
    assert main_module.main(["--cli", "boot-test", "--image", str(tmp_path / "none.img")]) == 0
    assert "skipped" in capsys.readouterr().out
    assert main_module.main(["--cli", "release-manifest", "--image", str(tmp_path / "none"), "--version", "1", "--commit", COMMIT, "--output", str(tmp_path / "r.json")]) == 1
    assert extra_commands.HANDLERS
