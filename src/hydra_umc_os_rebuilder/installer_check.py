# =============================================================================
# HYDRA-UMC-OS-REBUILDER - Run the installers of HYDRA-UMC-OS against the tree of an image: installer_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The image keeps its checkouts under `/opt/hydra-umc/<name>` and links `/opt/hydra-umc/src/<NAME>` to each, so that an installer of HYDRA-UMC-OS finds the project it
# installs next to its own checkout. Whether that is true cannot be seen by reading the link code: this module takes the tree that the build made (a mounted root file
# system, or any folder with the same layout), runs every installer script through the link with bash (first the dry-run the scripts promise, which changes nothing, then
# only the two lines of the script that decide where the project is) and reports, for each one, whether `$SOURCE/hydra-umc.project.json` resolves. It never runs an
# installer with `--apply` (that needs root and changes the system) and it never writes into the tree.
# =============================================================================
from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

OS_NAME = "HYDRA-UMC-OS"
_LINE = re.compile(r"^(ROOT|SOURCE)=(.+)$")


class InstallerCheckError(ValueError):
    """A tree that cannot be checked."""


def decision_lines(script_text: str) -> list[str]:
    """The `ROOT=` and `SOURCE=` assignments of an installer, in order (the only lines that decide where the project must be)."""
    lines = [line for line in script_text.splitlines() if _LINE.match(line)]
    if not any(line.startswith("ROOT=") for line in lines) or not any(line.startswith("SOURCE=") for line in lines):
        raise InstallerCheckError("the installer has no ROOT= and SOURCE= lines")
    return lines


Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


def _run(command: list[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(command, capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL, timeout=60)


def installer_scripts(rootfs: Path) -> list[Path]:
    """The installers `/opt/hydra-umc/src/HYDRA-UMC-OS/provisioning/install_*.sh` of the tree, reached through the link."""
    folder = rootfs / "opt" / "hydra-umc" / "src" / OS_NAME / "provisioning"
    if not folder.is_dir():
        raise InstallerCheckError(f"{folder} does not exist: HYDRA-UMC-OS is not linked in the image")
    return sorted(folder.glob("install_*.sh"))


def check_installer(script: Path, *, bash: str = "bash", run: Runner = _run) -> dict[str, Any]:
    """Run one installer through its link: the dry-run, then its ROOT and SOURCE lines. Returns what was found."""
    result: dict[str, Any] = {"script": script.name, "dry_run_ok": False, "source": None, "resolves": False, "problem": None}
    dry = run([bash, str(script)])
    result["dry_run_ok"] = dry.returncode == 0 and "Dry-run policy" in dry.stdout
    if not result["dry_run_ok"]:
        result["problem"] = f"the dry-run exited {dry.returncode} instead of 0 with its dry-run message"
        return result
    try:
        lines = decision_lines(script.read_text(encoding="utf-8"))
    except (InstallerCheckError, OSError) as error:
        result["problem"] = str(error)
        return result
    # The file test runs inside bash too, so the answer is the one the installer itself would get (and a path as bash sees it is not turned into a host path).
    probe = "\n".join(lines) + '\nprintf "%s" "$SOURCE"\n[ -f "$SOURCE/hydra-umc.project.json" ]\n'
    # `$0` must be the path through the link: that is how the installers are started in the image, and `cd ..` follows the link text.
    found = run([bash, "-c", probe, str(script)])
    result["source"] = found.stdout.strip() or None
    result["resolves"] = found.returncode == 0
    if not result["resolves"]:
        result["problem"] = f"{result['source'] or 'SOURCE'}/hydra-umc.project.json does not resolve"
    return result


def check_tree(rootfs: Path, *, bash: str = "bash", run: Runner = _run, which: Callable[[str], str | None] = shutil.which) -> dict[str, Any]:
    """Check every installer of the tree. `ok` is true only when there is at least one installer and each one resolves its project."""
    if which(bash) is None:
        raise InstallerCheckError(f"{bash} is not installed")
    scripts = installer_scripts(rootfs)
    rows = [check_installer(script, bash=bash, run=run) for script in scripts]
    return {"installers": len(rows), "ok": bool(rows) and all(r["dry_run_ok"] and r["resolves"] for r in rows), "rows": rows}


def build_tree(destination: Path, os_checkout: Path, *, link: Callable[[Path, str], Path]) -> list[str]:
    """Make a tree with the layout of an image from a checkout of HYDRA-UMC-OS: its own folder, one stub checkout per project named in its table of installers,
    and the capital-letter links. Used by the manual workflow; the stubs hold only a `hydra-umc.project.json`. Returns the project names."""
    table = json.loads((os_checkout / "provisioning" / "install_plan.json").read_text(encoding="utf-8"))
    base = destination / "opt" / "hydra-umc"
    shutil.copytree(os_checkout, base / OS_NAME.lower(), ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))
    names = [OS_NAME]
    link(destination, OS_NAME)
    for row in table.get("installers", []):
        name = str(row.get("source") or "")
        if not name or name in names:
            continue
        folder = base / name.lower()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "hydra-umc.project.json").write_text(json.dumps({"name": name}), encoding="utf-8")
        link(destination, name)
        names.append(name)
    return names
