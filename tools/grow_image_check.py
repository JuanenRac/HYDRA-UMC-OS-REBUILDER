#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tools/grow_image_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Grows a real (small, made-up) Raspberry Pi style image with the code of the builder, on a loop device, and checks the result.

Run as root on a Linux machine with losetup, parted, mkfs.vfat and mkfs.ext4 (the manual workflow "Grow the root partition of an image" does it on a
runner of GitHub). It builds an image with a FAT boot partition and an ext4 root partition holding a marker file each, then calls the same functions as the
builder (`extend_image_file`, `grow_root_partition`) and checks that:

  * the file is larger by exactly the growth asked for;
  * partition 2 now reaches the end of the file and the root file system filled it (and is clean for `e2fsck -fn`);
  * the files in both partitions are still there, byte for byte;
  * a growth of zero or less is refused and changes nothing.

It proves the sequence of parted, e2fsck and resize2fs on a real block device; the image of Raspberry Pi OS itself (and a card) is not involved.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from hydra_umc_os_rebuilder import image_builder  # noqa: E402

MB = 1024 * 1024
FAIL = 0


def ok(text: str) -> None:
    print(f"PASS  {text}", flush=True)


def bad(text: str) -> None:
    global FAIL
    FAIL = 1
    print(f"FAIL  {text}", flush=True)


def run(*command: str, capture: bool = False) -> str:
    done = subprocess.run(command, check=True, text=True, capture_output=capture, stdin=subprocess.DEVNULL)
    return done.stdout.strip() if capture else ""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if os.geteuid() != 0:
        print("FAIL  this check needs root (losetup, mount)")
        return 1
    work = Path(tempfile.mkdtemp(prefix="grow-check-"))
    raw = work / "test.img"
    boot_mount, root_mount = work / "boot", work / "root"
    boot_mount.mkdir()
    root_mount.mkdir()

    # a small image: 64 MiB FAT boot partition and a 192 MiB ext4 root partition
    with open(raw, "wb") as handle:
        handle.truncate(270 * MB)
    run("parted", "--script", str(raw), "mklabel", "msdos", "mkpart", "primary", "fat32", "4MiB", "68MiB", "mkpart", "primary", "ext4", "68MiB", "260MiB")
    loop = run("losetup", "--find", "--show", "--partscan", str(raw), capture=True)
    try:
        image_builder._wait_for_partitions(loop)
        run("mkfs.vfat", "-F", "32", f"{loop}p1")
        run("mkfs.ext4", "-q", "-F", f"{loop}p2")
        payloads = {}
        for part, mount, name in ((f"{loop}p1", boot_mount, "BOOTMARK.TXT"), (f"{loop}p2", root_mount, "rootmark.bin")):
            run("mount", part, str(mount))
            (mount / name).write_bytes(os.urandom(300_000))
            payloads[name] = sha(mount / name)
            run("umount", str(mount))
        before_fs = int(run("blockdev", "--getsize64", f"{loop}p2", capture=True))
    finally:
        subprocess.run(["losetup", "-d", loop], check=False)

    size_before = raw.stat().st_size
    grow_mb = 512
    image_builder.extend_image_file(raw, grow_mb)
    if raw.stat().st_size == size_before + grow_mb * MB:
        ok(f"the file grew by exactly {grow_mb} MiB")
    else:
        bad(f"the file is {raw.stat().st_size} bytes, expected {size_before + grow_mb * MB}")

    for wrong in (0, -5):
        try:
            image_builder.extend_image_file(raw, wrong)
            bad(f"a growth of {wrong} was not refused")
        except image_builder.ImageBuildError:
            if raw.stat().st_size == size_before + grow_mb * MB:
                ok(f"a growth of {wrong} is refused and changes nothing")
            else:
                bad(f"a growth of {wrong} changed the file")

    loop = run("losetup", "--find", "--show", "--partscan", str(raw), capture=True)
    try:
        image_builder._wait_for_partitions(loop)
        image_builder.grow_root_partition(loop)
        image_builder._wait_for_partitions(loop)
        after_fs = int(run("blockdev", "--getsize64", f"{loop}p2", capture=True))
        if after_fs >= before_fs + (grow_mb - 8) * MB:
            ok(f"partition 2 grew from {before_fs // MB} MiB to {after_fs // MB} MiB")
        else:
            bad(f"partition 2 is {after_fs // MB} MiB, expected about {before_fs // MB + grow_mb} MiB")
        table = run("parted", "--script", "-m", str(raw), "unit", "B", "print", capture=True)
        end = int([line for line in table.splitlines() if line.startswith("2:")][0].split(":")[2].rstrip("B"))
        if raw.stat().st_size - end <= 2 * MB:
            ok("partition 2 reaches the end of the file")
        else:
            bad(f"partition 2 ends at {end}, the file at {raw.stat().st_size}")
        check = subprocess.run(["e2fsck", "-fn", f"{loop}p2"], stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
        if check.returncode == 0:
            ok("e2fsck finds the grown file system clean")
        else:
            bad(f"e2fsck exit {check.returncode}: {check.stdout[-300:]}")
        run("mount", f"{loop}p2", str(root_mount))
        free = int(run("df", "--output=avail", "-B1", str(root_mount), capture=True).splitlines()[-1])
        if free > (grow_mb - 64) * MB:
            ok(f"the root file system has {free // MB} MiB free for the projects")
        else:
            bad(f"only {free // MB} MiB free in the grown file system")
        if sha(root_mount / "rootmark.bin") == payloads["rootmark.bin"]:
            ok("the file in the root partition is intact")
        else:
            bad("the file in the root partition changed")
        run("umount", str(root_mount))
        run("mount", f"{loop}p1", str(boot_mount))
        if sha(boot_mount / "BOOTMARK.TXT") == payloads["BOOTMARK.TXT"]:
            ok("the file in the boot partition is intact")
        else:
            bad("the file in the boot partition changed")
        run("umount", str(boot_mount))
    finally:
        subprocess.run(["umount", str(root_mount)], check=False, capture_output=True)
        subprocess.run(["umount", str(boot_mount)], check=False, capture_output=True)
        subprocess.run(["losetup", "-d", loop], check=False)
    print("evidence=simulator (made-up image on a loop device, no Raspberry Pi OS image, no card)")
    return FAIL


if __name__ == "__main__":
    raise SystemExit(main())
