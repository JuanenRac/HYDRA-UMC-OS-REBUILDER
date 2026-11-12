#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tools/installer_tree_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Run the installers of a HYDRA-UMC-OS checkout against a tree laid out like an image and check that each finds its project.

    python tools/installer_tree_check.py --os DIR [--tree DIR]

Builds the tree (the checkout under /opt/hydra-umc/hydra-umc-os, one stub project per installer, and the links /opt/hydra-umc/src/<NAME> made by the builder's own
`link_checkout_for_installers`), then runs every installer through its link with bash: the dry-run first, then the lines that decide where the project must be. Nothing
is installed (no `--apply`, no root). Prints one line per installer and exits 1 when one does not resolve. evidence=simulator (the tree is made, it is not an image).
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

from hydra_umc_os_rebuilder import installer_check  # noqa: E402
from hydra_umc_os_rebuilder.image_builder import link_checkout_for_installers  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--os", required=True, help="a checkout of HYDRA-UMC-OS")
    parser.add_argument("--tree", default="", help="folder to build the tree in (default: a temporary one)")
    args = parser.parse_args()
    holder = tempfile.TemporaryDirectory(prefix="hydra-tree-") if not args.tree else None
    tree = Path(holder.name if holder else args.tree).resolve()
    try:
        names = installer_check.build_tree(tree, Path(args.os).resolve(), link=link_checkout_for_installers)
        print(f"INFO  tree with {len(names)} projects at {tree}")
        report = installer_check.check_tree(tree)
        for row in report["rows"]:
            good = row["dry_run_ok"] and row["resolves"]
            print(("PASS  " if good else "FAIL  ") + f"{row['script']} -> {row['source']}" + ("" if good else f" ({row['problem']})"))
        print(f"{'PASS' if report['ok'] else 'FAIL'}  {report['installers']} installers run through their links")
        print("evidence=simulator (a tree with the layout of the image was made, nothing was installed)")
        return 0 if report["ok"] else 1
    finally:
        if holder:
            holder.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
