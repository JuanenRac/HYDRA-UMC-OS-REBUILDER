# =============================================================================
# HYDRA-UMC-OS-REBUILDER - CLI entry point: main.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# No arguments launches the windowed GUI (qt_gui.py, PySide6/QML) - the
# default way this tool runs, matching HYDRA-UMC-UPDATER's own run.bat/.sh
# convention. `--cli <command>` runs headless, safe over SSH with no
# display and no Qt runtime installed, for scripting or a first pass on a
# machine that never gets the `gui` extra installed at all.
# =============================================================================
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .ecosystem_plan import fetch_ecosystem_plan, plan_summary_lines
from .firstboot_config import FirstBootConfig, WifiConfig, build_boot_partition_patch
from .profile_manifest import (
    diff_profile,
    freeze_profile,
    load_profile_manifest,
    manifest_to_ecosystem_plan,
    record_build_result,
    refreeze_selected,
    save_profile_manifest,
)


def _cmd_status(args: argparse.Namespace) -> int:
    plan = fetch_ecosystem_plan(owner=args.owner)
    if args.json:
        # Real, scripting-friendly shape - every field EcosystemPlanEntry
        # actually carries, plus the same discovery_errors the human-
        # readable path only ever prints inline (plan_summary_lines()
        # folds a discovery error into its own output line, easy to miss
        # in a script; here it's its own real, always-present array,
        # empty when nothing went wrong).
        payload = {
            "projects": [
                {"name": e.name, "version": e.version, "role": e.role, "stack": e.stack, "git_url": e.git_url, "branch": e.branch}
                for e in plan.entries
            ],
            "discovery_errors": list(plan.discovery_errors),
            "total": len(plan),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    for line in plan_summary_lines(plan):
        print(line)
    print(f"TOTAL={len(plan)}")
    return 0


def _cmd_config(args: argparse.Namespace) -> int:
    wifi = None
    if args.wifi_ssid:
        wifi = WifiConfig(ssid=args.wifi_ssid, psk=args.wifi_password or "", country=args.wifi_country, hidden=args.wifi_hidden)
    config = FirstBootConfig(
        hostname=args.hostname,
        username=args.username,
        password=args.password,
        enable_ssh=not args.no_ssh,
        ssh_authorized_key=args.ssh_key,
        wifi=wifi,
        timezone=args.timezone,
        keyboard_layout=args.keyboard,
        locale=args.locale,
        acknowledge_no_remote_access=args.acknowledge_no_remote_access,
    )
    patch = build_boot_partition_patch(config)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    script_path = out_dir / patch.firstrun_path
    script_path.write_text(patch.firstrun_sh, encoding="utf-8", newline="\n")
    script_path.chmod(0o755)
    (out_dir / "cmdline-append.txt").write_text(patch.cmdline_append, encoding="utf-8")
    print(f"CONFIG_WRITTEN out={out_dir} firstrun={script_path.name}")
    return 0


def _cmd_build_image(args: argparse.Namespace) -> int:
    from .image_builder import KNOWN_BASE_IMAGES, build_image, check_build_platform

    check = check_build_platform()
    if not check.ok:
        print(f"BUILD_BLOCKED reason={check.reason}", file=sys.stderr)
        return 1

    plan = fetch_ecosystem_plan(owner=args.owner)
    source = KNOWN_BASE_IMAGES[0]

    # Real first-boot config, threaded into the actual build - same flags
    # as the standalone `config` subcommand above. Previously always
    # `firstboot=None` here: the `config` subcommand could only ever write
    # a firstrun.sh to a directory disconnected from the actual image
    # build, so a real build never carried the hostname/user/Wi-Fi the
    # operator configured. `--hostname`/`--username`/... are all optional
    # (matching `config`'s own behavior) - omit every one and this stays
    # `firstboot=None`, an image with no first-boot customisation at all.
    wifi = None
    if args.wifi_ssid:
        wifi = WifiConfig(ssid=args.wifi_ssid, psk=args.wifi_password or "", country=args.wifi_country, hidden=args.wifi_hidden)
    firstboot = None
    if any([args.hostname, args.username, args.password, wifi, args.timezone, args.keyboard, args.locale, args.no_ssh]):
        firstboot = FirstBootConfig(
            hostname=args.hostname,
            username=args.username,
            password=args.password,
            enable_ssh=not args.no_ssh,
            ssh_authorized_key=args.ssh_key,
            wifi=wifi,
            timezone=args.timezone,
            keyboard_layout=args.keyboard,
            locale=args.locale,
            acknowledge_no_remote_access=args.acknowledge_no_remote_access,
        )

    def progress(update) -> None:
        print(f"[{update.phase}] {update.detail}")

    result = build_image(
        source=source,
        plan=plan,
        firstboot=firstboot,
        work_dir=Path(args.work_dir),
        output_path=Path(args.out),
        progress=progress,
    )
    if not result.ok:
        print(f"BUILD_FAILED error={result.error}", file=sys.stderr)
        return 1
    print(f"BUILD_OK output={result.output_path} installed={','.join(result.installed)}")
    return 0


def _cmd_profile_freeze(args: argparse.Namespace) -> int:
    plan = fetch_ecosystem_plan(owner=args.owner)
    manifest = freeze_profile(plan, profile_name=args.name)
    save_profile_manifest(manifest, Path(args.out))
    print(f"PROFILE_FROZEN name={manifest.profile_name} out={args.out} projects={len(manifest)}")
    return 0


def _cmd_profile_diff(args: argparse.Namespace) -> int:
    manifest = load_profile_manifest(Path(args.manifest))
    live = fetch_ecosystem_plan(owner=args.owner)
    diff = diff_profile(manifest, live)
    if not diff.has_changes():
        print(f"PROFILE_UNCHANGED name={manifest.profile_name}")
        return 0
    for finding in diff.entries:
        print(f"{finding.kind.upper()} {finding.name}: {finding.detail}")
    print(f"TOTAL_CHANGES={len(diff)}")
    return 0


def _cmd_profile_update(args: argparse.Namespace) -> int:
    manifest = load_profile_manifest(Path(args.manifest))
    live = fetch_ecosystem_plan(owner=args.owner)
    refrozen = refreeze_selected(manifest, live, set(args.project))
    out_path = Path(args.out) if args.out else Path(args.manifest)
    save_profile_manifest(refrozen, out_path)
    print(f"PROFILE_UPDATED name={refrozen.profile_name} out={out_path} updated={','.join(args.project)}")
    return 0


def _cmd_profile_build(args: argparse.Namespace) -> int:
    from .image_builder import build_image, check_build_platform

    check = check_build_platform()
    if not check.ok:
        print(f"BUILD_BLOCKED reason={check.reason}", file=sys.stderr)
        return 1

    manifest_path = Path(args.manifest)
    manifest = load_profile_manifest(manifest_path)
    plan = manifest_to_ecosystem_plan(manifest)
    from .image_builder import KNOWN_BASE_IMAGES

    source = KNOWN_BASE_IMAGES[0]

    wifi = None
    if args.wifi_ssid:
        wifi = WifiConfig(ssid=args.wifi_ssid, psk=args.wifi_password or "", country=args.wifi_country, hidden=args.wifi_hidden)
    firstboot = None
    if any([args.hostname, args.username, args.password, wifi, args.timezone, args.keyboard, args.locale, args.no_ssh]):
        firstboot = FirstBootConfig(
            hostname=args.hostname,
            username=args.username,
            password=args.password,
            enable_ssh=not args.no_ssh,
            ssh_authorized_key=args.ssh_key,
            wifi=wifi,
            timezone=args.timezone,
            keyboard_layout=args.keyboard,
            locale=args.locale,
            acknowledge_no_remote_access=args.acknowledge_no_remote_access,
        )

    def progress(update) -> None:
        print(f"[{update.phase}] {update.detail}")

    result = build_image(
        source=source,
        plan=plan,
        firstboot=firstboot,
        work_dir=Path(args.work_dir),
        output_path=Path(args.out),
        progress=progress,
    )
    if not result.ok:
        print(f"BUILD_FAILED error={result.error}", file=sys.stderr)
        return 1
    # D05/D07: fold the real, post-build content hashes back into the
    # frozen manifest on disk - a rebuilt profile now carries real proof
    # of what actually landed, not just the recipe it was built from.
    built_manifest = record_build_result(manifest, result.installed)
    save_profile_manifest(built_manifest, manifest_path)
    print(f"BUILD_OK output={result.output_path} installed={','.join(result.installed)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hydra-umc-os-rebuilder", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--cli", action="store_true", help="run headless instead of launching the GUI")
    parser.add_argument("--owner", default="JuanenRac", help="GitHub account to discover ecosystem projects from")
    sub = parser.add_subparsers(dest="command")

    status_parser = sub.add_parser("status", help="print every real CM5 project's latest GitHub version")
    status_parser.add_argument("--json", action="store_true", help="machine-readable JSON instead of the human-readable summary")

    config_parser = sub.add_parser("config", help="write a real first-boot config (firstrun.sh) to a directory")
    config_parser.add_argument("--out", required=True, help="directory to write firstrun.sh into (the image's boot partition when used for real)")
    config_parser.add_argument("--hostname")
    config_parser.add_argument("--username")
    config_parser.add_argument("--password")
    config_parser.add_argument("--no-ssh", action="store_true", help="do not enable SSH (enabled by default)")
    config_parser.add_argument("--acknowledge-no-remote-access", action="store_true", help="opt into a config that disables SSH with no account configured either - see firstboot_config.py")
    config_parser.add_argument("--ssh-key", help="a public key to authorize for the new user")
    config_parser.add_argument("--wifi-ssid")
    config_parser.add_argument("--wifi-password")
    config_parser.add_argument("--wifi-country", default="US")
    config_parser.add_argument("--wifi-hidden", action="store_true")
    config_parser.add_argument("--timezone")
    config_parser.add_argument("--keyboard")
    config_parser.add_argument("--locale")

    build_parser_cmd = sub.add_parser("build-image", help="build a ready-to-flash .img (Linux/root only)")
    build_parser_cmd.add_argument("--out", required=True, help="output .img path")
    build_parser_cmd.add_argument("--work-dir", default="work", help="scratch directory for the download/mount/build steps")
    # Same real first-boot flags as the `config` subcommand above - all
    # optional, all threaded straight into the actual build (see
    # _cmd_build_image's own comment for why that's new).
    build_parser_cmd.add_argument("--hostname")
    build_parser_cmd.add_argument("--username")
    build_parser_cmd.add_argument("--password")
    build_parser_cmd.add_argument("--no-ssh", action="store_true", help="do not enable SSH (enabled by default)")
    build_parser_cmd.add_argument("--acknowledge-no-remote-access", action="store_true", help="opt into a config that disables SSH with no account configured either - see firstboot_config.py")
    build_parser_cmd.add_argument("--ssh-key", help="a public key to authorize for the new user")
    build_parser_cmd.add_argument("--wifi-ssid")
    build_parser_cmd.add_argument("--wifi-password")
    build_parser_cmd.add_argument("--wifi-country", default="US")
    build_parser_cmd.add_argument("--wifi-hidden", action="store_true")
    build_parser_cmd.add_argument("--timezone")
    build_parser_cmd.add_argument("--keyboard")
    build_parser_cmd.add_argument("--locale")

    # D05: freeze/diff/update/build a named, persisted, tested combination
    # of components - see profile_manifest.py's own module docstring.
    freeze_parser = sub.add_parser("profile-freeze", help="freeze the current live ecosystem plan into a named, persisted profile manifest")
    freeze_parser.add_argument("--name", required=True, help="profile name, e.g. 'cm5-production'")
    freeze_parser.add_argument("--out", required=True, help="path to write the profile manifest JSON to")

    diff_parser = sub.add_parser("profile-diff", help="compare a frozen profile manifest against the current live ecosystem")
    diff_parser.add_argument("--manifest", required=True, help="path to an existing profile manifest JSON")

    update_parser = sub.add_parser("profile-update", help="refreeze only the named projects in a profile, leaving the rest pinned exactly as before")
    update_parser.add_argument("--manifest", required=True, help="path to an existing profile manifest JSON")
    update_parser.add_argument("--project", required=True, action="append", help="project name to update to its current live version (repeatable)")
    update_parser.add_argument("--out", help="write the updated manifest here instead of overwriting --manifest in place")

    profile_build_parser = sub.add_parser("profile-build", help="build a real .img from EXACTLY a frozen profile manifest (Linux/root only)")
    profile_build_parser.add_argument("--manifest", required=True, help="path to an existing profile manifest JSON")
    profile_build_parser.add_argument("--out", required=True, help="output .img path")
    profile_build_parser.add_argument("--work-dir", default="work", help="scratch directory for the download/mount/build steps")
    profile_build_parser.add_argument("--hostname")
    profile_build_parser.add_argument("--username")
    profile_build_parser.add_argument("--password")
    profile_build_parser.add_argument("--no-ssh", action="store_true", help="do not enable SSH (enabled by default)")
    profile_build_parser.add_argument("--acknowledge-no-remote-access", action="store_true", help="opt into a config that disables SSH with no account configured either - see firstboot_config.py")
    profile_build_parser.add_argument("--ssh-key", help="a public key to authorize for the new user")
    profile_build_parser.add_argument("--wifi-ssid")
    profile_build_parser.add_argument("--wifi-password")
    profile_build_parser.add_argument("--wifi-country", default="US")
    profile_build_parser.add_argument("--wifi-hidden", action="store_true")
    profile_build_parser.add_argument("--timezone")
    profile_build_parser.add_argument("--keyboard")
    profile_build_parser.add_argument("--locale")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        if not args.cli:
            from .qt_gui import run_gui

            return run_gui()
        parser.print_help()
        return 1

    handlers = {
        "status": _cmd_status,
        "config": _cmd_config,
        "build-image": _cmd_build_image,
        "profile-freeze": _cmd_profile_freeze,
        "profile-diff": _cmd_profile_diff,
        "profile-update": _cmd_profile_update,
        "profile-build": _cmd_profile_build,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
