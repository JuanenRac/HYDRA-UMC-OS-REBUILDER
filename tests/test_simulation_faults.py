# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_simulation_faults.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Simulation bench, part two: a host twin that fails at every single step of the image build.

The twin (`FakeHost`) stands in for the Linux host that the real build needs (a loop device, mounts, `git`, `chroot`, `xz`): it keeps the list of loop devices and
of mounts, creates the checkout that `git clone` would create, and makes ONE chosen step fail, either with an exit status or with a time-out. The real pipeline
(`build_image`) runs over it unchanged, so the bench proves what the build does when any step fails: it returns a result and does not raise, it reports the
failure, it never puts a half-built image at the output path, it leaves no mount and no loop device behind (except the one whose release was the step that
failed, and then it says so), and a build started again from a fresh base image gives the same content hashes as one that never failed.
Nothing here needs root, a loop device or a network; what it cannot show is how a real kernel and a real `chroot` behave, which stays a test on a Linux host.
"""
from __future__ import annotations

import random
import subprocess
import urllib.error
from pathlib import Path

import pytest

from hydra_umc_os_rebuilder import image_builder as builder
from hydra_umc_os_rebuilder.ecosystem_plan import EcosystemPlan, EcosystemPlanEntry
from hydra_umc_os_rebuilder.image_builder import BaseImageSource, PlatformCheck, build_image

SEED = 20260101
PLATFORM_COMMAND = ("apt-get", "install", "-y", "nvidia-jetpack")


def _entry(name: str, **overrides) -> EcosystemPlanEntry:
    base = dict(
        name=name,
        version="1.0.0",
        role="api",
        stack="node",
        git_url=f"https://github.com/JuanenRac/{name}.git",
        commit_sha="c" * 40,
    )
    base.update(overrides)
    return EcosystemPlanEntry(**base)  # type: ignore[arg-type]


def _plan() -> EcosystemPlan:
    return EcosystemPlan(entries=(_entry("HYDRA-UMC-SERVER"), _entry("HYDRA-UMC-STUDIO")), discovery_errors=())


class FakeHost:
    """The Linux host of the build. `fail_at` is the number of the step (counting the download as step 0) that fails; `how` is `exit` or `timeout`."""

    def __init__(self, work_dir: Path, fail_at: int | None = None, how: str = "exit") -> None:
        self.work_dir = work_dir
        self.fail_at = fail_at
        self.how = how
        self.steps: list[str] = []
        self.failed_step: str | None = None
        self.mounted: list[str] = []
        self.loops: set[str] = set()

    # the download of the base image: a fresh image every time, as a new download is
    def fetch(self, source: BaseImageSource, dest_dir: Path, **_kwargs) -> Path:
        self._step("fetch", None, ("fetch", source.url))
        dest_dir.mkdir(parents=True, exist_ok=True)
        mount_root = dest_dir / "mnt"
        if mount_root.exists():
            import shutil

            shutil.rmtree(mount_root)
        image = dest_dir / Path(source.url).name
        image.write_bytes(b"fixture base image")
        return image

    def _step(self, kind: str, timeout: float | None, command: tuple[str, ...]) -> None:
        index = len(self.steps)
        self.steps.append(" ".join(command))
        if index != self.fail_at:
            return
        self.failed_step = " ".join(command)
        if kind == "fetch":
            part = self.work_dir / "base.img.part"
            part.write_bytes(b"half")
            raise urllib.error.URLError("simulated: the connection was cut")
        if self.how == "timeout" and timeout is not None:
            raise subprocess.TimeoutExpired(list(command), timeout)
        raise subprocess.CalledProcessError(1, list(command), stderr="simulated failure")

    def __call__(self, command, **kwargs):
        command = tuple(str(part) for part in command)
        check = bool(kwargs.get("check", False))
        try:
            self._step("run", kwargs.get("timeout"), command)
        except subprocess.CalledProcessError as exc:
            if check:
                raise
            return subprocess.CompletedProcess(command, 1, "", str(exc.stderr))
        return self._apply(command)

    def _apply(self, command: tuple[str, ...]) -> subprocess.CompletedProcess:
        done = subprocess.CompletedProcess(command, 0, "", "")
        if command[:2] == ("losetup", "--find"):
            self.loops.add("/dev/loop0")
            done.stdout = "/dev/loop0\n"
        elif command[:2] == ("losetup", "-d"):
            self.loops.discard(command[2])
        elif command[0] == "mount" and "--make-rslave" not in command:
            self.mounted.append(command[-1])
        elif command[0] == "umount":
            if command[1] in self.mounted:
                self.mounted.remove(command[1])
            else:
                return subprocess.CompletedProcess(command, 32, "", "not mounted")
        elif command[:2] == ("git", "clone"):
            target = Path(command[-1])
            if target.exists():
                return subprocess.CompletedProcess(command, 128, "", "destination path already exists")
            target.mkdir(parents=True)
            (target / "build.sh").write_text("#!/bin/bash\n", encoding="utf-8")
            (target / "hydra-umc.project.json").write_text('{"version": "1.0.0"}', encoding="utf-8")
        return done


@pytest.fixture(autouse=True)
def _host_dns_file(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    resolv = tmp_path_factory.mktemp("dns") / "resolv.conf"
    resolv.write_text("nameserver 192.0.2.53\n", encoding="utf-8")
    monkeypatch.setattr(builder.ChrootEnvironment, "HOST_RESOLV_CANDIDATES", (str(resolv),))


def _build(root: Path, monkeypatch: pytest.MonkeyPatch, fail_at: int | None = None, how: str = "exit", host: FakeHost | None = None):
    work_dir = root / "work"
    host = host or FakeHost(work_dir, fail_at, how)
    monkeypatch.setattr(builder, "check_build_platform", lambda: PlatformCheck(True))
    monkeypatch.setattr(builder, "check_build_preflight", lambda **_k: PlatformCheck(True))
    monkeypatch.setattr(builder, "_wait_for_partitions", lambda *_a, **_k: None)
    monkeypatch.setattr(builder, "fetch_base_image", host.fetch)
    monkeypatch.setattr(builder.subprocess, "run", host)
    output = root / "out" / "hydra-umc.img"
    result = build_image(
        source=BaseImageSource(label="fixture", url="http://example.invalid/base.img", sha256=""),
        plan=_plan(),
        firstboot=None,
        work_dir=work_dir,
        output_path=output,
        project_timeout_seconds=30,
        platform_commands=(PLATFORM_COMMAND,),
    )
    return result, host, output, work_dir


@pytest.fixture()
def baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    result, host, output, _work = _build(tmp_path / "baseline", monkeypatch)
    assert result.ok, result.error
    return result, host, output


def test_a_build_that_nothing_interrupts_finishes_and_leaves_the_host_clean(baseline) -> None:
    result, host, output = baseline
    assert output.is_file()
    assert output.with_name(output.name + ".sha256").is_file()
    assert output.with_name(output.name + ".manifest.json").is_file()
    assert len(result.installed) == 2
    assert host.mounted == []
    assert host.loops == set()
    # every project was cloned, built in the chroot and put back to its pinned commit, and the platform command ran in the chroot
    assert [step for step in host.steps if step.startswith("git clone")].__len__() == 2
    assert any(step.endswith(" ".join(PLATFORM_COMMAND)) and step.startswith("chroot") for step in host.steps)
    assert len(host.steps) > 20


@pytest.mark.parametrize("how", ["exit", "timeout"])
def test_every_single_step_can_fail_and_the_build_still_ends_cleanly(how: str, baseline, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _result, base_host, _output = baseline
    total = len(base_host.steps)
    for step_number in range(total):
        root = tmp_path / f"{how}-{step_number}"
        result, host, output, work_dir = _build(root, monkeypatch, fail_at=step_number, how=how)
        step = host.failed_step
        label = f"step {step_number} ({step}) failing with {how}"
        assert step is not None, f"{label}: the failure was never reached"
        assert result.ok is False, f"{label}: the build said it worked"
        assert result.error, f"{label}: no reason was given"
        assert not output.exists(), f"{label}: a half-built image reached the output path"
        assert list(work_dir.glob("*.part")) == [], f"{label}: a half-downloaded file was left behind"
        # nothing stays mounted and no loop device stays attached, except what the failing step itself was supposed to release
        allowed_mounts = [step.split()[-1]] if step.startswith("umount") else []
        allowed_loops = {step.split()[-1]} if step.startswith("losetup -d") else set()
        assert host.mounted == allowed_mounts or set(host.mounted) <= set(allowed_mounts), f"{label}: mounts left behind: {host.mounted}"
        assert host.loops == allowed_loops, f"{label}: loop devices left attached: {host.loops}"
        if allowed_mounts or allowed_loops:
            assert "cleanup" in result.error or "umount" in result.error or "chroot" in result.error, f"{label}: the release that failed was not reported: {result.error}"


def test_a_build_started_again_after_a_failure_gives_the_same_content_as_one_that_never_failed(baseline, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_result, base_host, _output = baseline
    rng = random.Random(SEED)
    steps = list(range(len(base_host.steps)))
    for attempt, step_number in enumerate(sorted(rng.sample(steps, 10))):
        root = tmp_path / f"retry-{attempt}"
        failed, host, _out, _work = _build(root, monkeypatch, fail_at=step_number, how=rng.choice(["exit", "timeout"]))
        assert failed.ok is False
        # the same folders again, the failure gone: a new download is a fresh image
        again, _host, output, _work = _build(root, monkeypatch, host=FakeHost(root / "work"))
        assert again.ok, f"the second build after a failure at {host.failed_step!r} failed: {again.error}"
        assert output.is_file()
        assert again.installed == base_result.installed, "the content hashes of a build after a failure differ from a build without one"


def test_a_failure_in_a_project_names_that_project_and_the_ones_before_it_stay_reported(baseline, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _result, base_host, _output = baseline
    second_clone = [i for i, step in enumerate(base_host.steps) if step.startswith("git clone")][1]
    result, host, output, _work = _build(tmp_path / "second", monkeypatch, fail_at=second_clone)
    assert result.ok is False
    assert "HYDRA-UMC-STUDIO" in result.error
    assert len(result.installed) == 1 and result.installed[0].startswith("HYDRA-UMC-SERVER@1.0.0#sha256:")
    assert not output.exists()
    assert host.mounted == [] and host.loops == set()
