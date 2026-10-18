# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_pipeline_guards.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Guards around the image pipeline that do not need a loop device: what runs
before the first mount, what a subprocess may read, what a profile file may
hand to git."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from hydra_umc_os_rebuilder import image_builder as image_builder_module
from hydra_umc_os_rebuilder.ecosystem_plan import EcosystemPlan, EcosystemPlanEntry
from hydra_umc_os_rebuilder.firstboot_config import FirstBootConfig
from hydra_umc_os_rebuilder.image_builder import (
    BaseImageSource,
    ImageBuildError,
    PlatformCheck,
    _wait_for_partitions,
    build_image,
    check_build_platform,
)
from hydra_umc_os_rebuilder.profile_manifest import (
    ProfileManifestError,
    freeze_profile,
    from_json,
    refreeze_selected,
    set_required_resources,
    to_json,
)


def _plan_entry(name="HYDRA-UMC-SERVER", sha="a" * 40, version="0.1.0") -> EcosystemPlanEntry:
    return EcosystemPlanEntry(
        name=name, version=version, role="service", stack="python",
        git_url=f"https://github.com/JuanenRac/{name}.git", commit_sha=sha,
    )


def test_a_host_that_cannot_run_an_aarch64_image_is_refused_before_anything_is_downloaded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(image_builder_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(image_builder_module.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(image_builder_module.shutil, "which", lambda _tool: "/usr/bin/tool")
    monkeypatch.setattr(image_builder_module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(image_builder_module.Path, "exists", lambda self: False)
    check = check_build_platform()
    assert not check.ok
    assert "qemu-user-static" in check.reason

    monkeypatch.setattr(image_builder_module.platform, "machine", lambda: "aarch64")
    assert check_build_platform().ok


def test_the_pipeline_never_hands_a_terminal_to_a_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_run(command, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(image_builder_module.subprocess, "run", fake_run)
    image_builder_module._run("true")
    assert seen["stdin"] == subprocess.DEVNULL


def test_a_bad_first_boot_setting_fails_the_build_before_any_download(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(image_builder_module, "check_build_platform", lambda: PlatformCheck(True))
    downloads = []
    monkeypatch.setattr(image_builder_module, "fetch_base_image", lambda *a, **k: downloads.append(a) or tmp_path / "x.img")
    result = build_image(
        source=BaseImageSource(label="x", url="https://example.invalid/x.img.xz", sha256=""),
        plan=EcosystemPlan(entries=(), discovery_errors=()),
        firstboot=FirstBootConfig(hostname="not a valid host name!"),
        work_dir=tmp_path / "work",
        output_path=tmp_path / "out.img",
    )
    assert not result.ok
    assert "hostname" in result.error
    assert downloads == []


def test_a_failed_download_is_a_failed_build_not_an_exception(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(image_builder_module, "check_build_platform", lambda: PlatformCheck(True))

    def failing_download(*_a, **_k):
        (tmp_path / "work").mkdir(exist_ok=True)
        (tmp_path / "work" / "image.img.xz.part").write_bytes(b"half")
        raise ImageBuildError("the connection was reset")

    monkeypatch.setattr(image_builder_module, "fetch_base_image", failing_download)
    result = build_image(
        source=BaseImageSource(label="x", url="https://example.invalid/x.img.xz", sha256=""),
        plan=EcosystemPlan(entries=(), discovery_errors=()),
        firstboot=None,
        work_dir=tmp_path / "work",
        output_path=tmp_path / "out.img",
    )
    assert not result.ok and "connection was reset" in result.error
    assert list((tmp_path / "work").glob("*.part")) == []


def test_waiting_for_the_partition_devices_is_bounded() -> None:
    created = {"/dev/loop9p1", "/dev/loop9p2"}
    _wait_for_partitions("/dev/loop9", exists=lambda path: path in created, sleep=lambda _s: None)
    with pytest.raises(ImageBuildError, match="did not appear"):
        _wait_for_partitions("/dev/loop9", timeout_seconds=1.0, exists=lambda _path: False, sleep=lambda _s: None)


def test_updating_one_project_keeps_the_resources_curated_for_it() -> None:
    frozen = freeze_profile(EcosystemPlan(entries=(_plan_entry(),), discovery_errors=()), profile_name="p")
    frozen = set_required_resources(frozen, "HYDRA-UMC-SERVER", ("dist/index.html",))
    live = EcosystemPlan(entries=(_plan_entry(sha="b" * 40, version="0.2.0"),), discovery_errors=())
    refreshed = refreeze_selected(frozen, live, {"HYDRA-UMC-SERVER"})
    entry = refreshed.entry("HYDRA-UMC-SERVER")
    assert entry.commit_sha == "b" * 40
    assert entry.required_resources == ("dist/index.html",)


def test_a_profile_file_cannot_hand_git_an_option_or_a_foreign_url() -> None:
    good = to_json(freeze_profile(EcosystemPlan(entries=(_plan_entry(),), discovery_errors=()), profile_name="p"))
    from_json(good)

    option = {**good, "entries": [{**good["entries"][0], "commit_sha": "--upload-pack=evil"}]}
    with pytest.raises(ProfileManifestError, match="commit"):
        from_json(option)

    foreign = {**good, "entries": [{**good["entries"][0], "git_url": "https://evil.example/repo.git"}]}
    with pytest.raises(ProfileManifestError, match="git_url"):
        from_json(foreign)
