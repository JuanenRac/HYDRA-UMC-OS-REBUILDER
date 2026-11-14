# =============================================================================
# HYDRA-UMC-OS-REBUILDER - package init
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
# The version is read from the installed distribution's own metadata,
# populated by setuptools straight from pyproject.toml at install time,
# and is not a hardcoded literal: a second copy of pyproject.toml's own
# version field would have nothing keeping them in sync, because
# bump_manifest_version.py (this repo's single owner of pyproject.toml's
# version, see CHANGELOG.md's own "Versioning scheme") only touches
# pyproject.toml and hydra-umc.project.json, so main.py's `--version` and
# the GUI's own About dialog would stay stuck on an old number. Reading the
# metadata makes drift structurally impossible, with no second sync step
# to remember.
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("hydra-umc-os-rebuilder")
except PackageNotFoundError:  # running from a bare checkout, never installed
    __version__ = "0.0.0+unknown"
