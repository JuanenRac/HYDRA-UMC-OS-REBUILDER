#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tools/pigen_stage_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Put the custom stage of the pi-gen backend into a real pi-gen checkout and check that pi-gen would accept its shape.

    python tools/pigen_stage_check.py --pigen DIR --payload NAME=DIR [--payload NAME=DIR ...]

It writes the stage with `build_backends.write_pigen_stage` next to pi-gen's own stages, copies each payload folder to `<stage>/00-checkouts/files/NAME`, writes the
`config` file, marks the stages before it as not exporting an image, and then checks, the way pi-gen reads a stage: every run script is executable and parses with
`bash -n`, the stage has the files pi-gen looks for, the stage list of the config names stages that exist, and the folders of the payload are where the script copies them from.
It runs nothing of pi-gen. Prints one line per check and exits 1 when one fails. evidence=simulator (no image is built here).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

from hydra_umc_os_rebuilder import build_backends  # noqa: E402

failures = 0


def check(condition: bool, message: str) -> None:
    global failures
    print(("PASS  " if condition else "FAIL  ") + message)
    failures += 0 if condition else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pigen", required=True)
    parser.add_argument("--payload", action="append", default=[], help="NAME=DIR, a project folder copied into the stage")
    args = parser.parse_args()
    pigen = Path(args.pigen).resolve()
    check((pigen / "build.sh").is_file() and (pigen / "stage0").is_dir() and (pigen / "stage2").is_dir(), "the pi-gen checkout has build.sh and its stages")

    config = json.loads((HERE / "config" / "rebuilder.example.json").read_text(encoding="utf-8"))
    config["build_backend"]["name"] = "pigen"
    config["build_backend"]["pigen"]["checkout"] = str(pigen)
    payloads: dict[str, Path] = {}
    for item in args.payload:
        name, _, folder = item.partition("=")
        payloads[name] = Path(folder).resolve()
    projects = {name: "a" * 40 for name in payloads}

    plan = build_backends.plan_backend(config, projects)
    check(plan["missing_tools"] == [], f"the plan finds the pi-gen checkout (missing: {plan['missing_tools']})")

    stage = config["build_backend"]["pigen"]["stage_name"]
    written = build_backends.write_pigen_stage(pigen, projects, config)
    check(len(written) == 4, f"four files were written ({len(written)})")
    for name, folder in payloads.items():
        target = pigen / stage / "00-checkouts" / "files" / name
        shutil.copytree(folder, target, ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))
        check(target.is_dir(), f"the payload {name} is where 00-run.sh copies it from")

    run_script = pigen / stage / "00-checkouts" / "00-run.sh"
    prerun = pigen / stage / "prerun.sh"
    for script in (run_script, prerun):
        script.chmod(0o755)
        result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        check(result.returncode == 0, f"bash -n {script.relative_to(pigen)} {result.stderr.strip()}")
        check(os.access(script, os.X_OK), f"{script.relative_to(pigen)} is executable")
    text = run_script.read_text(encoding="utf-8")
    for name in payloads:
        check(f'cp -a "files/{name}" ' in text, f"00-run.sh copies {name}")
    check((pigen / stage / "EXPORT_IMAGE").is_file(), "the stage exports an image (EXPORT_IMAGE)")

    config_text = (pigen / "config").read_text(encoding="utf-8")
    settings = {}
    for line in config_text.splitlines():
        key, _, value = line.partition("=")
        settings[key] = value.strip("'")
    listed = settings.get("STAGE_LIST", "").split()
    check(bool(listed) and all((pigen / name).is_dir() for name in listed), f"every stage of STAGE_LIST exists: {listed}")
    check(bool(listed) and listed[-1] == stage, "the stage of this project comes last")
    for name in ("stage0", "stage1", "stage2"):
        (pigen / name / "SKIP_IMAGES").touch()
    check(all((pigen / n / "SKIP_IMAGES").is_file() for n in ("stage0", "stage1", "stage2")), "the earlier stages are marked not to export an image of their own")
    check("ENABLE_SSH=0" in config_text or "ENABLE_SSH='0'" in config_text, "ssh stays off in the image")
    print("evidence=simulator (the stage was checked, no image was built)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
