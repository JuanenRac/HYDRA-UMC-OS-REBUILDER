# =============================================================================
# HYDRA-UMC-OS-REBUILDER - package init
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
# Real bug found and fixed here: this used to be a hardcoded literal string,
# a second copy of pyproject.toml's own real version field with nothing
# keeping them in sync - bump_manifest_version.py (this repo's single owner
# of pyproject.toml's version, see CHANGELOG.md's own "Versioning scheme")
# only ever touched pyproject.toml and hydra-umc.project.json, never this
# file, so main.py's `--version` and the GUI's own About dialog had been
# silently stuck reporting "0.0.1" for 2 real releases (confirmed live: a
# fresh `pip install` from this project's own real, current GitHub HEAD
# still reported 0.0.1 well after the real published version had moved to
# 0.0.3). Reading it back from the installed distribution's own metadata -
# populated by setuptools straight from pyproject.toml at install time -
# makes this structurally impossible to drift again, rather than adding a
# second sync step to remember.
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("hydra-umc-os-rebuilder")
except PackageNotFoundError:  # running from a bare checkout, never installed
    __version__ = "0.0.0+unknown"
