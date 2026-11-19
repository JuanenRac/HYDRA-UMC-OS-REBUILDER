# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_partition_layout.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The partitions of the base image (platform.partitions): the layout, the growth of the root partition, the wait for the nodes and the mounts. Fake commands only; evidence: simulator."""
from __future__ import annotations

from pathlib import Path

import pytest
import test_image_builder as helpers
from test_image_builder import _entry, _fake_subprocess_run, _install_pipeline_fake_run

from hydra_umc_os_rebuilder import image_builder as image_builder_module
from hydra_umc_os_rebuilder.ecosystem_plan import EcosystemPlan
from hydra_umc_os_rebuilder.image_builder import BaseImageSource, ImageBuildError, PlatformCheck, build_image

fixture_server = helpers.fixture_server  # the fixture of the image builder tests, under the same name


def test_the_partition_layout_names_the_nodes_the_growth_and_the_wait_use(monkeypatch: pytest.MonkeyPatch) -> None:
    from hydra_umc_os_rebuilder.image_builder import PartitionLayout

    real_wait = image_builder_module._wait_for_partitions
    assert PartitionLayout().numbers() == (1, 2)
    assert PartitionLayout(boot=0, root=1).numbers() == (1,)
    for boot, root in ((1, 1), (0, 0), (-1, 2)):
        with pytest.raises(ImageBuildError):
            PartitionLayout(boot=boot, root=root)
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(image_builder_module, "_run", lambda *command, **kwargs: calls.append(command))
    monkeypatch.setattr(image_builder_module, "_wait_for_partitions", lambda loop_dev, **kwargs: calls.append(("wait", loop_dev, str(kwargs["partitions"]))))

    class Done:
        returncode = 0

    monkeypatch.setattr(image_builder_module.subprocess, "run", lambda command, **kwargs: calls.append(tuple(command)) or Done())
    image_builder_module.grow_root_partition("/dev/loop7", PartitionLayout(boot=0, root=3))
    assert calls == [
        ("parted", "--script", "/dev/loop7", "resizepart", "3", "100%"),
        ("wait", "/dev/loop7", "(3,)"),
        ("e2fsck", "-f", "-y", "/dev/loop7p3"),
        ("resize2fs", "/dev/loop7p3"),
    ]
    waited: list[str] = []
    real_wait("/dev/loop7", partitions=(3,), timeout_seconds=0.0, sleep=lambda _s: None, exists=lambda path: waited.append(path) or True)
    assert waited == ["/dev/loop7p3"]


def test_an_image_without_a_boot_partition_refuses_a_first_boot_configuration(tmp_path: Path) -> None:
    from hydra_umc_os_rebuilder.firstboot_config import FirstBootConfig
    from hydra_umc_os_rebuilder.image_builder import PartitionLayout

    result = build_image(
        source=BaseImageSource(label="x", url="http://127.0.0.1:1/x.img", sha256=""),
        plan=EcosystemPlan(entries=(), discovery_errors=()),
        firstboot=FirstBootConfig(hostname="h"),
        work_dir=tmp_path / "w",
        output_path=tmp_path / "o.img",
        layout=PartitionLayout(boot=0, root=1),
    )
    assert result.ok is False and "no boot partition" in result.error


def test_build_image_mounts_the_partitions_of_the_layout(fixture_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from hydra_umc_os_rebuilder.image_builder import PartitionLayout

    monkeypatch.setattr(image_builder_module, "check_build_platform", lambda: PlatformCheck(True))
    monkeypatch.setattr(image_builder_module, "_wait_for_partitions", lambda *_a, **_k: None)
    succeeding_target = tmp_path / "work" / "mnt" / "rootfs" / "opt" / "hydra-umc" / "hydra-umc-server"
    fake_run, run_calls = _install_pipeline_fake_run(succeeding_target)
    monkeypatch.setattr(image_builder_module, "_run", fake_run)
    monkeypatch.setattr(image_builder_module.subprocess, "run", _fake_subprocess_run([]))
    build_image(
        source=BaseImageSource(label="fixture", url=f"{fixture_server}/image.img", sha256=""),
        plan=EcosystemPlan(entries=(_entry(name="HYDRA-UMC-SERVER", version="1.0.0", commit_sha="c" * 40),), discovery_errors=()),
        firstboot=None,
        work_dir=tmp_path / "work",
        output_path=tmp_path / "out" / "x.img",
        layout=PartitionLayout(boot=0, root=3),
    )
    mounts = [c for c in run_calls if c and c[0] == "mount" and str(c[1]).startswith("/dev/")]
    assert [m[1][-2:] for m in mounts] == ["p3"], "only the root partition is mounted when there is no boot partition"
