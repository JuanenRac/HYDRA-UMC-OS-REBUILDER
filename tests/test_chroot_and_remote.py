# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_chroot_and_remote.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The chroot needs /proc, /sys, /dev and name resolution; a remote build installs a pinned
rebuilder. Nothing here mounts anything: the commands go to a recorder."""
import subprocess
from pathlib import Path

import pytest

from hydra_umc_os_rebuilder.image_builder import ChrootEnvironment, ImageBuildError
from hydra_umc_os_rebuilder.remote_install import RemoteInstallError, remote_install_requirement, remote_ref


def _env(tmp_path: Path, fail_on: str | None = None):
    rootfs = tmp_path / "rootfs"
    (rootfs / "etc").mkdir(parents=True)
    resolv = tmp_path / "host-resolv.conf"
    resolv.write_text("nameserver 192.0.2.53\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def run(*command: str, **_kwargs):
        calls.append(command)
        if fail_on and fail_on in command:
            raise subprocess.CalledProcessError(32, command)

    return ChrootEnvironment(rootfs, run=run, host_resolv=(str(resolv),)), rootfs, calls


def test_the_pseudo_file_systems_are_mounted_in_order_and_unmounted_in_reverse(tmp_path: Path) -> None:
    env, rootfs, calls = _env(tmp_path)
    env.mount()
    assert [c[:3] for c in calls] == [
        ("mount", "-t", "proc"), ("mount", "-t", "sysfs"),
        ("mount", "--bind", "/dev"), ("mount", "--make-rslave", str(rootfs / "dev")),
        ("mount", "--bind", "/dev/pts"), ("mount", "--make-rslave", str(rootfs / "dev" / "pts")),
    ]
    calls.clear()
    assert env.unmount() == []
    assert [Path(c[1]).name for c in calls] == ["pts", "dev", "sys", "proc"]
    assert env.unmount() == []  # nothing left to do the second time


def test_resolv_conf_is_the_hosts_while_building_and_the_original_afterwards(tmp_path: Path) -> None:
    env, rootfs, _ = _env(tmp_path)
    target = rootfs / "etc" / "resolv.conf"
    target.write_text("nameserver 10.0.0.1\n", encoding="utf-8")
    env.mount()
    assert "192.0.2.53" in target.read_text(encoding="utf-8")
    env.unmount()
    assert target.read_text(encoding="utf-8") == "nameserver 10.0.0.1\n"
    assert not (rootfs / "etc" / ("resolv.conf" + ChrootEnvironment.SAVED_SUFFIX)).exists()


def test_a_rootfs_without_resolv_conf_ends_without_one(tmp_path: Path) -> None:
    env, rootfs, _ = _env(tmp_path)
    env.mount()
    assert (rootfs / "etc" / "resolv.conf").is_file()
    env.unmount()
    assert not (rootfs / "etc" / "resolv.conf").exists()


def test_a_symlinked_resolv_conf_is_put_back_as_a_symlink(tmp_path: Path) -> None:
    env, rootfs, _ = _env(tmp_path)
    target = rootfs / "etc" / "resolv.conf"
    try:
        target.symlink_to("../run/systemd/resolve/stub-resolv.conf")
    except OSError:
        pytest.skip("symbolic links need a privilege this host does not give")
    env.mount()
    assert not target.is_symlink()
    env.unmount()
    assert target.is_symlink()


def test_a_failing_mount_undoes_what_was_done_and_says_so(tmp_path: Path) -> None:
    env, rootfs, calls = _env(tmp_path, fail_on="sysfs")
    with pytest.raises(ImageBuildError, match="could not be prepared"):
        env.mount()
    assert ("umount", str(rootfs / "proc")) in calls
    assert not (rootfs / "etc" / "resolv.conf").exists()


def test_a_failing_unmount_is_reported_not_raised(tmp_path: Path) -> None:
    env, rootfs, _ = _env(tmp_path)
    env.mount()
    env._run = lambda *command, **_k: (_ for _ in ()).throw(subprocess.CalledProcessError(32, command))  # type: ignore[attr-defined]
    problems = env.unmount()
    assert len(problems) == 4 and all("failed" in p for p in problems)


def test_a_host_without_resolv_conf_is_refused_before_anything_is_mounted(tmp_path: Path) -> None:
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    calls: list[tuple[str, ...]] = []
    env = ChrootEnvironment(rootfs, run=lambda *c, **_k: calls.append(c), host_resolv=(str(tmp_path / "nothing"),))
    with pytest.raises(ImageBuildError):
        env.mount()
    assert calls == []


def test_the_remote_install_is_pinned_to_the_release_tag_of_the_running_version() -> None:
    assert remote_ref("0.3.1", override="") == "v0.3.1"
    assert remote_install_requirement("0.3.1", override="").endswith("HYDRA-UMC-OS-REBUILDER.git@v0.3.1")
    assert remote_ref("0.3.1", override="0123abc") == "0123abc"
    assert remote_ref("0.3.1", override="release/1.x") == "release/1.x"


def test_a_development_copy_or_a_bad_reference_is_refused_not_replaced_by_main() -> None:
    with pytest.raises(RemoteInstallError):
        remote_ref("0.0.0+unknown", override="")
    for bad in ("main; rm -rf /", "../x", "a b", "-flag"):
        with pytest.raises(RemoteInstallError):
            remote_ref("0.3.1", override=bad)


def test_the_environment_can_name_the_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYDRA_UMC_REBUILDER_REMOTE_REF", "abc1234")
    assert remote_ref("0.0.0+unknown") == "abc1234"
