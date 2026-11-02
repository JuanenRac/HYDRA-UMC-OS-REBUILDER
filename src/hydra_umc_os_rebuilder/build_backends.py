# =============================================================================
# HYDRA-UMC-OS-REBUILDER - Build backends (systemd-nspawn, pi-gen): build_backends.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The image build runs the installs of the projects inside the image. The default backend is the chroot of
# image_builder.py. This module PREPARES the two alternatives and runs nothing: it returns the command that
# systemd-nspawn would run (it handles the pseudo file systems and the network without hand-made mounts) and writes the
# files of a pi-gen custom stage (pi-gen is the official image builder of Raspberry Pi: the stage copies the checkouts
# the artifact cache holds). Choosing a backend is the option `build_backend.name` of the configuration file; "chroot"
# stays the default.
# =============================================================================
from __future__ import annotations

import shlex
import shutil
from pathlib import Path
from typing import Any

_SAFE_NAME = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_HEX = set("0123456789abcdef")


class BackendError(ValueError):
    """A backend that cannot be planned with these inputs."""


def _check_name(value: str, what: str) -> str:
    if not value or value.startswith(".") or any(ch not in _SAFE_NAME for ch in value):
        raise BackendError(f"{what} must be made of letters, digits, '.', '_' and '-': {value!r}")
    return value


def _check_timezone(value: str) -> str:
    if not value or any(ch not in _SAFE_NAME | {"/", "+"} for ch in value) or value.startswith(("/", ".")) or ".." in value:
        raise BackendError(f"pigen.timezone is not a zone name: {value!r}")
    return value


def nspawn_command(rootfs: Path, command: list[str], config: dict[str, Any], *, bind_ro: dict[str, str] | None = None) -> list[str]:
    """`systemd-nspawn` around `command` inside `rootfs`. `bind_ro` maps a host path to a path in the image (read-only)."""
    options = config["build_backend"]["nspawn"]
    if not command:
        raise BackendError("nothing to run inside the image")
    plan = [str(options["binary"]), "--quiet", "--directory", str(rootfs), "--resolv-conf=replace-host"]
    for host, inside in sorted((bind_ro or {}).items()):
        if ":" in host or ":" in inside:
            raise BackendError("a bind path cannot contain ':'")
        plan += ["--bind-ro", f"{host}:{inside}"]
    plan += [str(item) for item in options["extra_args"]]
    return plan + ["--", *command]


def pigen_config_text(config: dict[str, Any]) -> str:
    """The `config` file of pi-gen for an image that only adds the stage of this project to the lite stages."""
    options = config["build_backend"]["pigen"]
    stage = _check_name(str(options["stage_name"]), "pigen.stage_name")
    values = {
        "IMG_NAME": _check_name(str(options["image_name"]), "pigen.image_name"),
        "RELEASE": _check_name(str(options["release"]), "pigen.release"),
        "LOCALE_DEFAULT": _check_name(str(options["locale"]), "pigen.locale"),
        "TIMEZONE_DEFAULT": _check_timezone(str(options["timezone"])),
        "ENABLE_SSH": "0",
        "STAGE_LIST": f"stage0 stage1 stage2 {stage}",
    }
    return "".join(f"{key}={shlex.quote(value)}\n" for key, value in values.items())


def pigen_stage_files(projects: dict[str, str], config: dict[str, Any]) -> dict[str, str]:
    """Relative path -> text of the custom stage. `projects` maps a project name to its commit (the checkouts come from the cache).

    The stage starts nothing: it copies the checkouts below /opt/hydra-umc/src, like the chroot build.
    """
    stage = _check_name(str(config["build_backend"]["pigen"]["stage_name"]), "pigen.stage_name")
    lines = ["#!/bin/bash -e", 'install -d -m 0755 "${ROOTFS_DIR}/opt/hydra-umc/src"']
    for name, commit in sorted(projects.items()):
        _check_name(name, "project name")
        if len(commit) < 7 or any(ch not in _HEX for ch in commit):
            raise BackendError(f"{name}: {commit!r} is not a commit")
        lines.append(f'cp -a "files/{name}" "${{ROOTFS_DIR}}/opt/hydra-umc/src/{name}"  # {commit}')
    return {
        f"{stage}/prerun.sh": '#!/bin/bash -e\n[ -d "${ROOTFS_DIR}" ] || copy_previous\n',
        f"{stage}/00-checkouts/00-run.sh": "\n".join(lines) + "\n",
        f"{stage}/EXPORT_IMAGE": 'IMG_SUFFIX=""\n',
        "config": pigen_config_text(config),
    }


def write_pigen_stage(directory: Path, projects: dict[str, str], config: dict[str, Any]) -> list[Path]:
    """Write the files of `pigen_stage_files` below `directory` (never over an existing file)."""
    files = pigen_stage_files(projects, config)
    for relative in files:
        if (directory / relative).exists():
            raise BackendError(f"{directory / relative} already exists: not overwriting")
    written: list[Path] = []
    for relative, text in files.items():
        target = directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        written.append(target)
    return written


def plan_backend(config: dict[str, Any], projects: dict[str, str], *, rootfs: Path | None = None) -> dict[str, Any]:
    """What the chosen backend would do and what is missing on this host; nothing is run or written."""
    name = str(config["build_backend"]["name"])
    plan: dict[str, Any] = {"backend": name, "runs_anything": False, "missing_tools": []}
    if name == "nspawn":
        binary = str(config["build_backend"]["nspawn"]["binary"])
        plan["command"] = nspawn_command(rootfs or Path("<rootfs>"), ["/bin/true"], config)
        if shutil.which(binary) is None:
            plan["missing_tools"].append(binary)
    elif name == "pigen":
        plan["files"] = sorted(pigen_stage_files(projects, config))
        checkout = str(config["build_backend"]["pigen"]["checkout"])
        if not checkout or not (Path(checkout) / "build.sh").is_file():
            plan["missing_tools"].append("pi-gen checkout (build_backend.pigen.checkout)")
    else:
        plan["note"] = "the chroot of the image builder"
    return plan
