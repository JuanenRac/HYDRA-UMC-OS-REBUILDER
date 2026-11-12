# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_installer_check_and_boot_extract.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The installers run through the links of an image tree, the first boot that can run them, and the kernel and device tree taken out of the boot partition."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hydra_umc_os_rebuilder import boot_test, build_config, installer_check
from hydra_umc_os_rebuilder.firstboot_config import FirstBootConfig, FirstBootConfigError, build_firstrun_script
from hydra_umc_os_rebuilder.image_builder import link_checkout_for_installers

INSTALLER = """#!/usr/bin/env bash
set -euo pipefail
APPLY=0
for arg in "$@"; do if [[ "$arg" == "--apply" ]]; then APPLY=1; fi; done
[[ $APPLY -eq 1 ]] || { echo "Dry-run policy: rerun with --apply after review."; exit 0; }
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SOURCE="$ROOT/HYDRA-UMC-DEMO"
[[ -f "$SOURCE/hydra-umc.project.json" ]] || { echo "incomplete" >&2; exit 2; }
"""


def _os_checkout(root: Path, installers: list[str]) -> Path:
    os_dir = root / "os"
    (os_dir / "provisioning").mkdir(parents=True)
    for script in installers:
        (os_dir / "provisioning" / script).write_text(INSTALLER, encoding="utf-8", newline="\n")
    rows = [{"script": s, "source": "HYDRA-UMC-DEMO"} for s in installers]
    (os_dir / "provisioning" / "install_plan.json").write_text(json.dumps({"installers": rows}), encoding="utf-8")
    return os_dir


def _real_bash() -> str | None:
    bash = shutil.which("bash")
    if bash is None:
        return None
    try:
        probe = subprocess.run([bash, "-c", "echo ok"], capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return bash if probe.stdout.strip() == "ok" else None


def test_the_decision_lines_are_the_root_and_the_source_of_the_installer() -> None:
    assert installer_check.decision_lines(INSTALLER) == ['ROOT="$(cd "$(dirname "$0")/../.." && pwd)"', 'SOURCE="$ROOT/HYDRA-UMC-DEMO"']
    with pytest.raises(installer_check.InstallerCheckError):
        installer_check.decision_lines("echo nothing\n")


def test_a_tree_without_the_os_link_is_refused(tmp_path: Path) -> None:
    with pytest.raises(installer_check.InstallerCheckError):
        installer_check.installer_scripts(tmp_path)
    with pytest.raises(installer_check.InstallerCheckError):
        installer_check.check_tree(tmp_path, bash="no-such-bash", which=lambda name: None)


def test_a_dry_run_that_fails_or_stays_silent_is_not_a_pass(tmp_path: Path) -> None:
    script = tmp_path / "install_x.sh"
    script.write_text(INSTALLER, encoding="utf-8")
    silent = installer_check.check_installer(script, run=lambda c: subprocess.CompletedProcess(c, 0, "", ""))
    assert silent["dry_run_ok"] is False and "dry-run" in silent["problem"]
    failing = installer_check.check_installer(script, run=lambda c: subprocess.CompletedProcess(c, 3, "Dry-run policy", ""))
    assert failing["dry_run_ok"] is False


def test_a_source_that_does_not_exist_is_reported_with_its_path(tmp_path: Path) -> None:
    script = tmp_path / "install_x.sh"
    script.write_text(INSTALLER, encoding="utf-8")
    calls = iter([subprocess.CompletedProcess([], 0, "Dry-run policy: rerun", ""), subprocess.CompletedProcess([], 1, str(tmp_path / "missing"), "")])
    row = installer_check.check_installer(script, run=lambda c: next(calls))
    assert row["dry_run_ok"] is True and row["resolves"] is False and "does not resolve" in row["problem"]


def test_a_hand_written_installer_is_listed_as_skipped_and_never_run(tmp_path: Path) -> None:
    script = tmp_path / "install_hand.sh"
    script.write_text("#!/usr/bin/env bash\n[[ $EUID -eq 0 ]] || exit 2\nROOT=/x\n", encoding="utf-8")
    row = installer_check.check_installer(script, run=lambda c: pytest.fail("must not run"))
    assert row["skipped"] is True and row["resolves"] is False and "not run" in row["problem"]


def test_the_installers_resolve_their_project_through_the_links_of_the_tree(tmp_path: Path) -> None:
    bash = _real_bash()
    if bash is None:
        pytest.skip("no working bash on this host")
    os_dir = _os_checkout(tmp_path, ["install_demo.sh", "install_other.sh"])
    tree = tmp_path / "tree"
    try:
        names = installer_check.build_tree(tree, os_dir, link=link_checkout_for_installers)
    except OSError:
        pytest.skip("this host cannot make links")
    assert names == ["HYDRA-UMC-OS", "HYDRA-UMC-DEMO"]
    report = installer_check.check_tree(tree, bash=bash)
    assert report["installers"] == 2 and report["checked"] == 2 and report["skipped"] == 0 and report["ok"] is True
    assert all(row["resolves"] for row in report["rows"])


def test_a_missing_project_makes_the_whole_tree_fail(tmp_path: Path) -> None:
    bash = _real_bash()
    if bash is None:
        pytest.skip("no working bash on this host")
    os_dir = _os_checkout(tmp_path, ["install_demo.sh"])
    tree = tmp_path / "tree"
    try:
        installer_check.build_tree(tree, os_dir, link=link_checkout_for_installers)
    except OSError:
        pytest.skip("this host cannot make links")
    shutil.rmtree(tree / "opt" / "hydra-umc" / "hydra-umc-demo")
    report = installer_check.check_tree(tree, bash=bash)
    assert report["ok"] is False and report["rows"][0]["resolves"] is False


def test_the_first_boot_runs_no_installer_unless_asked() -> None:
    assert "install_" not in build_firstrun_script(FirstBootConfig())
    script = build_firstrun_script(FirstBootConfig(run_installers=("install_server.sh", "install_twin.sh")))
    lines = [line for line in script.splitlines() if "--apply" in line]
    assert lines == [
        '/opt/hydra-umc/src/HYDRA-UMC-OS/provisioning/install_server.sh --apply || echo "installer install_server.sh failed" >&2',
        '/opt/hydra-umc/src/HYDRA-UMC-OS/provisioning/install_twin.sh --apply || echo "installer install_twin.sh failed" >&2',
    ]
    assert script.index("install_server.sh") < script.index("rm -f /boot/firmware/firstrun.sh")


@pytest.mark.parametrize("name", ["../install_x.sh", "install_x.sh; reboot", "rm -rf", "Install_X.sh", "install_.sh", "install_x.py"])
def test_an_installer_name_that_could_run_something_else_is_refused(name: str) -> None:
    with pytest.raises(FirstBootConfigError):
        build_firstrun_script(FirstBootConfig(run_installers=(name,)))


SFDISK = json.dumps({"partitiontable": {"label": "dos", "sectorsize": 512, "partitions": [
    {"node": "x1", "start": 8192, "size": 524288, "type": "c"}, {"node": "x2", "start": 532480, "size": 99, "type": "83"}]}})


def test_the_boot_partition_offset_is_the_start_of_the_first_fat_partition_in_bytes() -> None:
    assert boot_test.boot_partition_offset(SFDISK) == 8192 * 512
    gpt = json.dumps({"partitiontable": {"sectorsize": 4096, "partitions": [{"start": 10, "type": "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7"}]}})
    assert boot_test.boot_partition_offset(gpt) == 40960


@pytest.mark.parametrize("text", ["not json", "{}", json.dumps({"partitiontable": {"partitions": [{"start": 1, "type": "83"}]}}), json.dumps({"partitiontable": {"partitions": []}})])
def test_a_table_without_a_boot_partition_or_unreadable_is_refused(text: str) -> None:
    with pytest.raises(boot_test.BootTestError):
        boot_test.boot_partition_offset(text)


def _config(**boot: object) -> dict:
    config = build_config.load_config()
    config["boot_test"].update(boot)
    return config


def test_the_kernel_and_the_device_tree_are_copied_with_mtools_from_the_offset(tmp_path: Path) -> None:
    seen: list[list[str]] = []

    def run(command: list[str]) -> str:
        seen.append(command)
        return SFDISK if command[0] == "sfdisk" else ""

    config = _config(extract_kernel=True, kernel_name="kernel8.img", dtb_name="bcm2712-rpi-5-b.dtb")
    files = boot_test.extract_boot_files(tmp_path / "x.img", tmp_path / "out", config, run=run, which=lambda n: "/bin/" + n)
    assert files["kernel"] == tmp_path / "out" / "kernel8.img" and files["dtb"] == tmp_path / "out" / "bcm2712-rpi-5-b.dtb"
    copies = [c for c in seen if c[0] == "mcopy"]
    assert [c[3] for c in copies] == [f"{tmp_path / 'x.img'}@@{8192 * 512}"] * 2
    assert [c[4] for c in copies] == ["::kernel8.img", "::bcm2712-rpi-5-b.dtb"]


@pytest.mark.parametrize("name", ["../kernel8.img", "a/b", ".hidden", "a\\b"])
def test_a_file_name_that_leaves_the_boot_partition_is_refused(tmp_path: Path, name: str) -> None:
    config = _config(extract_kernel=True, kernel_name=name)
    with pytest.raises(boot_test.BootTestError):
        boot_test.extract_boot_files(tmp_path / "x.img", tmp_path / "out", config, run=lambda c: SFDISK, which=lambda n: "/bin/" + n)


def test_the_tools_that_are_missing_are_named(tmp_path: Path) -> None:
    config = _config(extract_kernel=True)
    with pytest.raises(boot_test.BootTestError, match="mcopy"):
        boot_test.extract_boot_files(tmp_path / "x.img", tmp_path / "out", config, run=lambda c: SFDISK, which=lambda n: None if n == "mcopy" else "/bin/" + n)


def test_qemu_gets_the_kernel_and_the_dtb_only_together(tmp_path: Path) -> None:
    config = _config()
    plain = boot_test.qemu_command(tmp_path / "x.img", config)
    assert "-kernel" not in plain and "-dtb" not in plain
    with_both = boot_test.qemu_command(tmp_path / "x.img", config, kernel=tmp_path / "k", dtb=tmp_path / "d")
    assert with_both[with_both.index("-kernel") + 1] == str(tmp_path / "k") and with_both[with_both.index("-dtb") + 1] == str(tmp_path / "d")
    assert "-dtb" not in boot_test.qemu_command(tmp_path / "x.img", config, dtb=tmp_path / "d")


def test_the_boot_test_with_extraction_off_by_default_does_not_extract(tmp_path: Path) -> None:
    image = tmp_path / "x.img"
    image.write_bytes(b"\0")
    config = _config(enabled=True)
    assert config["boot_test"]["extract_kernel"] is False
    result = boot_test.run_boot_test(image, config, launch=lambda c, t: "login: ", which=lambda n: "/bin/" + n, run=lambda c: pytest.fail("must not extract"))
    assert result["state"] == "ready" and "-kernel" not in result["command"]


def test_the_boot_test_with_extraction_on_boots_with_the_kernel_and_skips_when_it_cannot_extract(tmp_path: Path) -> None:
    image = tmp_path / "x.img"
    image.write_bytes(b"\0")
    config = _config(enabled=True, extract_kernel=True, dtb_name="board.dtb")
    ran = boot_test.run_boot_test(image, config, launch=lambda c, t: "login: ", which=lambda n: "/bin/" + n,
                                  run=lambda c: SFDISK if c[0] == "sfdisk" else "")
    assert ran["state"] == "ready" and "-kernel" in ran["command"] and ran["command"][ran["command"].index("-dtb") + 1].endswith("board.dtb")

    def broken(command: list[str]) -> str:
        raise boot_test.BootTestError("mcopy failed: no such file")

    skipped = boot_test.run_boot_test(image, config, launch=lambda c, t: pytest.fail("must not launch"), which=lambda n: "/bin/" + n, run=broken)
    assert skipped["state"] == "skipped" and "mcopy failed" in skipped["reason"]
