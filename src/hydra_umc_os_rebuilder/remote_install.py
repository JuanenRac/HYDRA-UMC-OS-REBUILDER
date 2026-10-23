# =============================================================================
# HYDRA-UMC-OS-REBUILDER - What a remote build installs and builds from: remote_install.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A remote build runs, as root, the rebuilder on another machine. Two things used to float:

  * the rebuilder itself was installed from the tip of `main`, so the remote ran a different
    version from the one the operator was using;
  * the remote discovered the ecosystem plan again instead of using the one the operator had
    reviewed, so "the exact same project set the user already reviewed" was not true there.

`remote_install_spec` pins the rebuilder to the release tag of the version that is running (or to
a reference the operator names), and the GUI sends the frozen profile to the remote and builds
from it (`profile-build`), so the remote installs exactly the commits that were reviewed.
"""
from __future__ import annotations

import os
import re

REPO_URL = "https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER.git"
REF_ENV = "HYDRA_UMC_REBUILDER_REMOTE_REF"
_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:\.\d+)?$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$")


class RemoteInstallError(ValueError):
    """The reference for the remote install is not usable."""


def remote_ref(version: str, override: str | None = None) -> str:
    """The git reference the remote installs: `override` (or the environment variable) when given,
    otherwise the tag `v<version>` of the running release. A development build with no real version
    has no tag to pin to and is refused rather than falling back to `main`."""
    wanted = (override if override is not None else os.environ.get(REF_ENV, "")).strip()
    if wanted:
        if not _REF.fullmatch(wanted) or ".." in wanted:
            raise RemoteInstallError(f"{wanted!r} is not a valid git reference")
        return wanted
    if not _VERSION.fullmatch(version):
        raise RemoteInstallError(
            f"this copy ({version}) has no release version to pin the remote install to; set {REF_ENV} to a tag or commit"
        )
    return f"v{version}"


def remote_install_requirement(version: str, override: str | None = None) -> str:
    """The pip requirement for the rebuilder on the remote host, pinned to a reference."""
    return f"hydra-umc-os-rebuilder @ git+{REPO_URL}@{remote_ref(version, override)}"
