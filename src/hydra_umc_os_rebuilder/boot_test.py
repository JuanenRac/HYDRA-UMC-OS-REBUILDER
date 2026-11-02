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

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any


class BootTestError(ValueError):
    """A boot test that cannot be planned."""


def qemu_command(image: Path, config: dict[str, Any], *, kernel: Path | None = None) -> list[str]:
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
    return command


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


def run_boot_test(image: Path, config: dict[str, Any], *, launch: Launcher = _launch, which: Callable[[str], str | None] = shutil.which) -> dict[str, Any]:
    """Boot the image in QEMU and read the serial log. Skipped (not passed) when switched off or QEMU is missing."""
    options = config["boot_test"]
    result: dict[str, Any] = {"command": qemu_command(image, config)}
    if not options["enabled"]:
        return {**result, "state": "skipped", "reason": "boot_test.enabled is off"}
    if which(str(options["qemu_binary"])) is None:
        return {**result, "state": "skipped", "reason": f"{options['qemu_binary']} is not installed"}
    if not image.is_file():
        return {**result, "state": "skipped", "reason": f"{image} does not exist"}
    log = launch(result["command"], float(options["timeout_seconds"]))
    return {**result, **read_boot_log(log, config)}
