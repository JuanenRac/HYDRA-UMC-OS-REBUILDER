# =============================================================================
# HYDRA-UMC-OS-REBUILDER - CLI commands of the build backends, cache, release channel and boot test: extra_commands.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# build-plan, cache-status, cache-prune, release-manifest, release-sign, release-verify, golden-register, golden-verify and boot-test. None of them writes
# an image, a device or a tag: they plan, check and report (see docs/CLI_REFERENCE.md).
# =============================================================================
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from . import artifact_cache, boot_test, build_backends, build_config, golden_image, release_channel
from .profile_signing import ProfileSigningError


def add_parsers(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    def with_config(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--config", help=f"options file (else {build_config.CONFIG_ENV}); everything is off without it")
        return parser

    plan = with_config(sub.add_parser("build-plan", help="show what the chosen build backend (chroot, nspawn, pi-gen) would do; runs nothing"))
    plan.add_argument("--project", action="append", default=[], metavar="NAME=COMMIT", help="a project and its commit (repeatable)")
    plan.add_argument("--write-pigen-stage", metavar="DIR", help="write the files of the pi-gen stage into this new folder")
    with_config(sub.add_parser("cache-status", help="show the artifact cache"))
    with_config(sub.add_parser("cache-prune", help="remove the least recently used cache entries beyond the size limit"))
    manifest = with_config(sub.add_parser("release-manifest", help="write release.json for a finished image"))
    manifest.add_argument("--image", required=True)
    manifest.add_argument("--version", required=True)
    manifest.add_argument("--commit", required=True, help="the full commit the image was built from")
    manifest.add_argument("--output", required=True)
    sign = with_config(sub.add_parser("release-sign", help="write release.json.sig with a private key file kept outside the repository"))
    sign.add_argument("--manifest", required=True)
    sign.add_argument("--key-file", required=True)
    verify = with_config(sub.add_parser("release-verify", help="check an image against its release.json, its signature and its signed tag"))
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--image", required=True)
    verify.add_argument("--trusted-key", default="")
    verify.add_argument("--repo", help="repository holding the signed tag")
    golden = with_config(sub.add_parser("golden-register", help="keep a known-good recovery image on this host, signed (the device never holds it)"))
    golden.add_argument("--image", required=True)
    golden.add_argument("--store", required=True, help="folder that holds the golden image, golden.json and its signature")
    golden.add_argument("--version", required=True)
    golden.add_argument("--commit", required=True, help="the full commit the image was built from")
    golden.add_argument("--key-file", required=True)
    golden.add_argument("--replace", action="store_true", help="replace an existing golden image with a newer version")
    golden_check = with_config(sub.add_parser("golden-verify", help="check the signature and the hash of the golden image before it is used for a recovery"))
    golden_check.add_argument("--store", required=True)
    golden_check.add_argument("--trusted-key", default="")
    golden_check.add_argument("--minimum-version", default="")
    boot = with_config(sub.add_parser("boot-test", help="boot the image in QEMU and read the serial log (skipped when off or QEMU is missing)"))
    boot.add_argument("--image", required=True)


def _projects(items: list[str]) -> dict[str, str]:
    projects: dict[str, str] = {}
    for item in items:
        name, _, commit = item.partition("=")
        projects[name] = commit
    return projects


def _cmd_build_plan(args: argparse.Namespace) -> int:
    config = build_config.load_config(args.config)
    projects = _projects(args.project)
    plan = build_backends.plan_backend(config, projects)
    if args.write_pigen_stage:
        plan["written"] = [str(p) for p in build_backends.write_pigen_stage(Path(args.write_pigen_stage), projects, config)]
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


def _cache(config: dict) -> "artifact_cache.ArtifactCache | None":
    return artifact_cache.ArtifactCache.from_config(config)


def _cmd_cache_status(args: argparse.Namespace) -> int:
    cache = _cache(build_config.load_config(args.config))
    print(json.dumps(cache.status() if cache else {"enabled": False}, indent=2, sort_keys=True))
    return 0


def _cmd_cache_prune(args: argparse.Namespace) -> int:
    cache = _cache(build_config.load_config(args.config))
    removed = cache.prune() if cache else []
    print(json.dumps({"removed": [f"{p}@{c}" for p, c in removed]}, indent=2))
    return 0


def _cmd_release_manifest(args: argparse.Namespace) -> int:
    config = build_config.load_config(args.config)
    target = release_channel.make_manifest(Path(args.image), args.version, args.commit, Path(args.output), config)
    print(f"RELEASE_MANIFEST_OK file={target}")
    print("TAG_COMMAND " + " ".join(release_channel.tag_command(args.version, args.commit, config)))
    return 0


def _cmd_release_sign(args: argparse.Namespace) -> int:
    print(f"RELEASE_SIGNED signature={release_channel.sign_release(Path(args.manifest), args.key_file)}")
    return 0


def _cmd_release_verify(args: argparse.Namespace) -> int:
    config = build_config.load_config(args.config)
    result = release_channel.verify_release(
        Path(args.manifest), Path(args.image), config, trusted_key=args.trusted_key, repo=Path(args.repo) if args.repo else None
    )
    print("RELEASE_VERIFIED " + json.dumps(result, sort_keys=True))
    return 0


def _cmd_golden_register(args: argparse.Namespace) -> int:
    record = golden_image.register(Path(args.image), Path(args.store), args.version, args.commit, args.key_file, replace=args.replace)
    print(f"GOLDEN_REGISTERED record={record}")
    return 0


def _cmd_golden_verify(args: argparse.Namespace) -> int:
    config = build_config.load_config(args.config)
    key = args.trusted_key or str(config["release_channel"]["trusted_key"])
    print("GOLDEN_VERIFIED " + json.dumps(golden_image.verify(Path(args.store), key, minimum_version=args.minimum_version), sort_keys=True))
    return 0


def _cmd_boot_test(args: argparse.Namespace) -> int:
    result = boot_test.run_boot_test(Path(args.image), build_config.load_config(args.config))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["state"] in ("failed", "no-result") else 0


HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "build-plan": _cmd_build_plan,
    "cache-status": _cmd_cache_status,
    "cache-prune": _cmd_cache_prune,
    "release-manifest": _cmd_release_manifest,
    "release-sign": _cmd_release_sign,
    "release-verify": _cmd_release_verify,
    "golden-register": _cmd_golden_register,
    "golden-verify": _cmd_golden_verify,
    "boot-test": _cmd_boot_test,
}


def run(args: argparse.Namespace) -> int:
    """Run one of the commands above; a refusal is printed as one line and returns 1."""
    try:
        return HANDLERS[args.command](args)
    except (
        build_config.BuildConfigError, build_backends.BackendError, artifact_cache.CacheError, release_channel.ReleaseError, golden_image.GoldenError,
        boot_test.BootTestError, ProfileSigningError, OSError,
    ) as error:
        print(f"{args.command.upper().replace('-', '_')}_FAILED error={error}", file=sys.stderr)
        return 1
