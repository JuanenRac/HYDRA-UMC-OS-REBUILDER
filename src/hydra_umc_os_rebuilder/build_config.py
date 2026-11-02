# =============================================================================
# HYDRA-UMC-OS-REBUILDER - Build options file: build_config.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The options of the build backend, the artifact cache, the release channel and the boot test live in one JSON file
# (config/rebuilder.example.json shows every key), never in the code. Everything is off or conservative by default: the
# chroot backend, no cache, no signature required, no boot test. The file is given with --config or
# HYDRA_UMC_OS_REBUILDER_CONFIG; a missing option means the default. Unknown keys are refused so that a typo cannot
# silently leave a protection off.
# =============================================================================
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

CONFIG_ENV = "HYDRA_UMC_OS_REBUILDER_CONFIG"
FORMAT = "hydra-rebuilder-config/1"
BACKENDS = ("chroot", "nspawn", "pigen")

DEFAULTS: dict[str, Any] = {
    "format": FORMAT,
    "build_backend": {
        "name": "chroot",
        "nspawn": {"binary": "systemd-nspawn", "extra_args": []},
        "pigen": {
            "checkout": "", "stage_name": "stage-hydra", "release": "trixie", "image_name": "hydra-umc",
            "locale": "en_GB.UTF-8", "timezone": "Europe/Madrid",
        },
    },
    "artifact_cache": {"enabled": False, "directory": "", "max_gb": 4},
    "release_channel": {
        "require_signed_tag": False, "require_signed_manifest": False, "trusted_key": "", "tag_prefix": "image-v",
    },
    "boot_test": {
        "enabled": False, "qemu_binary": "qemu-system-aarch64", "machine": "virt", "cpu": "cortex-a72", "memory_mb": 2048,
        "timeout_seconds": 300, "ssh_port": 2222, "ready_markers": ["login:"],
        "failure_markers": ["Kernel panic", "VFS: Unable to mount root"],
        "verify_over_ssh": False, "ssh_user": "", "verify_command": "provisioning/verify_cm5_runtime.sh --json",
    },
}


class BuildConfigError(ValueError):
    """A configuration file that cannot be used."""


def _same_kind(default: Any, value: Any) -> bool:
    if isinstance(default, bool) or isinstance(value, bool):
        return isinstance(default, bool) and isinstance(value, bool)
    if isinstance(default, (int, float)):
        return isinstance(value, (int, float))
    return isinstance(value, type(default))


def _merge(base: dict[str, Any], override: dict[str, Any], where: str) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key not in base:
            raise BuildConfigError(f"unknown key {where}{key}")
        if isinstance(base[key], dict):
            if not isinstance(value, dict):
                raise BuildConfigError(f"{where}{key} must be an object")
            merged[key] = _merge(base[key], value, f"{where}{key}.")
        else:
            if not _same_kind(base[key], value):
                raise BuildConfigError(f"{where}{key} must be of type {type(base[key]).__name__}")
            merged[key] = value
    return merged


def load_config(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """The options, with the defaults for whatever the file leaves out."""
    chosen = str(path) if path else os.environ.get(CONFIG_ENV, "")
    if not chosen:
        return copy.deepcopy(DEFAULTS)
    file = Path(chosen)
    if not file.is_file():
        raise BuildConfigError(f"configuration file not found: {file}")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BuildConfigError(f"cannot read {file}: {error}") from error
    if not isinstance(data, dict) or data.get("format", FORMAT) != FORMAT:
        raise BuildConfigError(f"{file} is not a {FORMAT} file")
    config = _merge(DEFAULTS, data, "")
    if config["build_backend"]["name"] not in BACKENDS:
        raise BuildConfigError(f"build_backend.name must be one of {', '.join(BACKENDS)}")
    return config
