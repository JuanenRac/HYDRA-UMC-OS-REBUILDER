# =============================================================================
# HYDRA-UMC-OS-REBUILDER - The platform of the image: platforms.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Which base image, packages and units a kind of module needs (`cm5`, `jetson`, `rk3588`) and which build backends can build it. The table is the one of
# HYDRA-UMC-OS (config/platforms/*.json, format hydra-platform/1); a test compares both when the two repositories are side by side. The platform is the option
# `platform.name` of the configuration file; `cm5` is the default and adds nothing, so the images of today do not change. `rk3588` is a GENERIC profile: no module or
# carrier board is chosen. Nothing here builds, flashes or boots: it plans (evidence: simulator).
# =============================================================================
from __future__ import annotations

import copy
from typing import Any

FORMAT = "hydra-platform/1"
DEFAULT_PLATFORM = "cm5"

PLATFORMS: dict[str, dict[str, Any]] = {
    "cm5": {
        "format": "hydra-platform/1",
        "platform": "cm5",
        "label": "Raspberry Pi Compute Module 5",
        "arch": "arm64",
        "generic": False,
        "base_image": {
            "kind": "raspberry-pi-os",
            "variant": "lite",
            "release": "trixie",
            "source": "the official Raspberry Pi OS Lite image",
            "note": "what the images of this project are built on today"
        },
        "packages": [],
        "remove_packages": [],
        "units": [],
        "build_backends": [
            "chroot",
            "nspawn",
            "pigen"
        ],
        "status": "in use: the platform of the pilot bench",
        "evidence": "bench"
    },
    "jetson": {
        "format": "hydra-platform/1",
        "platform": "jetson",
        "label": "NVIDIA Jetson module (Orin NX class)",
        "arch": "arm64",
        "generic": False,
        "base_image": {
            "kind": "nvidia-l4t-rootfs",
            "variant": "jetpack",
            "release": "ubuntu-22.04",
            "source": "the root file system of the JetPack release the module runs; supplied by the person who builds",
            "note": "assumed release: confirm it against the JetPack in use before building"
        },
        "packages": [
            "nvidia-jetpack"
        ],
        "remove_packages": [],
        "units": [
            {
                "name": "nvpmodel.service",
                "enable": True
            }
        ],
        "build_backends": [
            "chroot",
            "nspawn"
        ],
        "status": "prepared in simulation: the package and unit names are those of JetPack as far as known and are confirmed on a module",
        "evidence": "simulator"
    },
    "rk3588": {
        "format": "hydra-platform/1",
        "platform": "rk3588",
        "label": "Generic RK3588 module (no board chosen)",
        "arch": "arm64",
        "generic": True,
        "base_image": {
            "kind": "generic-arm64-debian",
            "variant": "minimal",
            "release": "trixie",
            "source": "a Debian arm64 root file system plus the vendor kernel, device tree and boot loader of the board, supplied by the person who builds",
            "note": "no model is chosen: nothing here depends on a board"
        },
        "packages": [
            "u-boot-tools",
            "device-tree-compiler"
        ],
        "remove_packages": [],
        "units": [],
        "build_backends": [
            "chroot",
            "nspawn"
        ],
        "status": "generic profile: no module or carrier board has been chosen",
        "evidence": "simulator"
    }
}


class PlatformError(ValueError):
    """A platform that does not exist or cannot be built with the chosen backend."""


def names() -> list[str]:
    return sorted(PLATFORMS)


def get(name: str) -> dict[str, Any]:
    """The declaration of a platform (a copy); an unknown name is an error, never another platform."""
    if name not in PLATFORMS:
        raise PlatformError(f"{name!r} is not a platform; the platforms are {', '.join(names())}")
    return copy.deepcopy(PLATFORMS[name])


def selected(config: dict[str, Any]) -> dict[str, Any]:
    """The platform of the configuration with its extra packages and units added (the options `platform.extra_packages` and `platform.extra_units`)."""
    options = config["platform"]
    declaration = get(str(options["name"]))
    for package in options["extra_packages"]:
        if package not in declaration["packages"]:
            declaration["packages"].append(package)
    for unit in options["extra_units"]:
        if all(existing["name"] != unit for existing in declaration["units"]):
            declaration["units"].append({"name": unit, "enable": True})
    return declaration


def check_backend(declaration: dict[str, Any], backend: str) -> None:
    """Refuses a backend that cannot build the platform (pi-gen builds Raspberry Pi images only)."""
    if backend not in declaration["build_backends"]:
        raise PlatformError(f"the platform {declaration['platform']} cannot be built with {backend}; it can be built with {', '.join(declaration['build_backends'])}")


def platform_plan(config: dict[str, Any]) -> dict[str, Any]:
    """What the platform asks of the build; nothing is run."""
    declaration = selected(config)
    commands: list[list[str]] = []
    if declaration["packages"]:
        commands.append(["apt-get", "install", "-y", "--no-install-recommends", *declaration["packages"]])
    if declaration["remove_packages"]:
        commands.append(["apt-get", "remove", "-y", *declaration["remove_packages"]])
    for unit in declaration["units"]:
        commands.append(["systemctl", "enable" if unit["enable"] else "disable", unit["name"]])
    return {
        "platform": declaration["platform"], "label": declaration["label"], "arch": declaration["arch"], "generic": declaration["generic"],
        "base_image": declaration["base_image"], "packages": declaration["packages"], "units": declaration["units"], "commands": commands,
        "build_backends": declaration["build_backends"], "evidence": declaration["evidence"],
    }
