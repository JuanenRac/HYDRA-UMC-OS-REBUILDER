# =============================================================================
# HYDRA-UMC-OS-REBUILDER - Boot test of an image in QEMU: boot_test.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Before an image is promoted it can be booted in QEMU and, when the options say so, the read-only
# `verify_cm5_runtime.sh --json` of HYDRA-UMC-OS can be run in it over SSH. This module builds the QEMU command, reads
# the serial log for a ready or a failure marker and reports the result as data. It runs QEMU only when the option
# `boot_test.enabled` is on AND QEMU is installed; otherwise the result is "skipped" with the reason, so a host without
# QEMU is reported honestly instead of passing. The image is attached as a copy-on-write overlay (`snapshot=on`), so the
# file itself is never written. It never touches a device or the CM5.
# =============================================================================
from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any


class BootTestError(ValueError):
    """A boot test that cannot be planned."""


def qemu_command(image: Path, config: dict[str, Any], *, kernel: Path | None = None, dtb: Path | None = None) -> list[str]:
    """The QEMU command line for `image`. Serial goes to stdio; the SSH port of the guest is forwarded to the host's 127.0.0.1."""
    options = config["boot_test"]
    if not image.name:
        raise BootTestError("no image")
    command = [
        str(options["qemu_binary"]), "-M", str(options["machine"]), "-cpu", str(options["cpu"]),
        "-m", str(int(options["memory_mb"])), "-smp", "2", "-nographic",
        "-drive", f"file={image},format=raw,if=virtio,snapshot=on",
        "-netdev", f"user,id=n0,hostfwd=tcp:127.0.0.1:{int(options['ssh_port'])}-:22",
        "-device", "virtio-net-pci,netdev=n0",
    ]
    if kernel is not None:
        command += ["-kernel", str(kernel), "-append", "root=/dev/vda2 rootwait console=ttyAMA0"]
        if dtb is not None:
            command += ["-dtb", str(dtb)]
    return command


_FAT_TYPES = {"c", "b", "e", "0c", "0b", "0e", "ebd0a0a2-b9e5-4433-87c0-68b6b72699c7"}


def boot_partition_offset(sfdisk_json: str) -> int:
    """The byte offset of the first FAT partition (the boot partition) in the `sfdisk --json` listing of an image."""
    try:
        table = json.loads(sfdisk_json)["partitiontable"]
        sector = int(table.get("sectorsize", 512))
        for part in table["partitions"]:
            if str(part.get("type", "")).lower() in _FAT_TYPES:
                return int(part["start"]) * sector
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise BootTestError(f"the partition table of the image cannot be read: {error}") from error
    raise BootTestError("the image has no FAT boot partition")


Runner = Callable[[list[str]], str]


def _run(command: list[str]) -> str:
    done = subprocess.run(command, capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL)
    if done.returncode != 0:
        raise BootTestError(f"{command[0]} failed: {(done.stderr or done.stdout).strip()[:200]}")
    return done.stdout


def extract_boot_files(image: Path, destination: Path, config: dict[str, Any], *, run: Runner = _run,
                       which: Callable[[str], str | None] = shutil.which) -> dict[str, Path | None]:
    """Copy the kernel (and, when named, the device tree) out of the boot partition of `image` with mtools, without mounting anything.

    Needs `sfdisk` and `mcopy`; a name that is not on the partition stops the test with a clear message instead of a QEMU that cannot start.
    """
    options = config["boot_test"]
    for tool in ("sfdisk", "mcopy"):
        if which(tool) is None:
            raise BootTestError(f"{tool} is not installed")
    offset = boot_partition_offset(run(["sfdisk", "--json", str(image)]))
    destination.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path | None] = {"kernel": None, "dtb": None}
    for key, name in (("kernel", str(options["kernel_name"])), ("dtb", str(options["dtb_name"]))):
        if not name:
            continue
        if "/" in name or "\\" in name or name.startswith("."):
            raise BootTestError(f"{name!r} is not a file name of the boot partition")
        target = destination / name
        run(["mcopy", "-n", "-i", f"{image}@@{offset}", f"::{name}", str(target)])
        found[key] = target
    return found


def read_boot_log(text: str, config: dict[str, Any]) -> dict[str, Any]:
    """"ready" when a ready marker is seen before any failure marker, "failed" on a failure marker, else "no-result"."""
    options = config["boot_test"]
    best: tuple[int, str, str] | None = None
    for state, markers in (("ready", options["ready_markers"]), ("failed", options["failure_markers"])):
        for marker in markers:
            at = text.find(str(marker))
            if at >= 0 and (best is None or at < best[0]):
                best = (at, state, str(marker))
    if best is None:
        return {"state": "no-result", "marker": None}
    return {"state": best[1], "marker": best[2]}


def ssh_verify_command(config: dict[str, Any]) -> list[str]:
    """The SSH command that runs the runtime check in the guest (the host key of a throw-away guest is not pinned)."""
    options = config["boot_test"]
    if not options["ssh_user"]:
        raise BootTestError("boot_test.ssh_user is empty")
    return [
        "ssh", "-p", str(int(options["ssh_port"])), "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null", f"{options['ssh_user']}@127.0.0.1", str(options["verify_command"]),
    ]


Launcher = Callable[[list[str], float], str]


def _launch(command: list[str], timeout: float) -> str:
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False, stdin=subprocess.DEVNULL)
        return done.stdout
    except subprocess.TimeoutExpired as error:
        out = error.stdout
        return out.decode("utf-8", "replace") if isinstance(out, bytes) else (out or "")


def run_boot_test(image: Path, config: dict[str, Any], *, launch: Launcher = _launch, which: Callable[[str], str | None] = shutil.which,
                  run: Runner = _run) -> dict[str, Any]:
    """Boot the image in QEMU and read the serial log. Skipped (not passed) when switched off or QEMU is missing."""
    options = config["boot_test"]
    result: dict[str, Any] = {"command": qemu_command(image, config)}
    if not options["enabled"]:
        return {**result, "state": "skipped", "reason": "boot_test.enabled is off"}
    if which(str(options["qemu_binary"])) is None:
        return {**result, "state": "skipped", "reason": f"{options['qemu_binary']} is not installed"}
    if not image.is_file():
        return {**result, "state": "skipped", "reason": f"{image} does not exist"}
    if options.get("extract_kernel"):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="hydra-boot-") as scratch:
            try:
                files = extract_boot_files(image, Path(scratch), config, run=run, which=which)
            except BootTestError as error:
                return {**result, "state": "skipped", "reason": str(error)}
            result["command"] = qemu_command(image, config, kernel=files["kernel"], dtb=files["dtb"])
            log = launch(result["command"], float(options["timeout_seconds"]))
        return {**result, **read_boot_log(log, config)}
    log = launch(result["command"], float(options["timeout_seconds"]))
    return {**result, **read_boot_log(log, config)}
