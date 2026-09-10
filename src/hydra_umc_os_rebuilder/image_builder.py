# =============================================================================
# HYDRA-UMC-OS-REBUILDER - Image build pipeline: image_builder.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Builds a ready-to-flash Raspberry Pi OS CM5 image: download the official
# base image, loop-mount its two real partitions, install/update every
# `deployment_target: "cm5"` ecosystem project into the rootfs by running
# each one's OWN existing build.sh (never a reimplementation of npm/cargo/
# go/pip build steps here - the same "delegate to each project's own build
# script" principle HYDRA-UMC-UPDATER's own install.py already documents),
# write the first-boot config (firstboot_config.py) onto the boot partition,
# unmount, and (optionally) compress.
#
# HONEST PLATFORM BOUNDARY: loop-mounting a raw .img and chrooting into an
# aarch64 rootfs needs a real Linux host with root (losetup/mount/chroot are
# not meaningfully emulable on Windows, and qemu-user-static's binfmt
# registration for a foreign-arch chroot needs the same). This module always
# checks that boundary FIRST and returns a real, honest BuildResult
# explaining exactly what's missing rather than silently no-op'ing or
# pretending to have built something - the same discipline this ecosystem's
# own CI already applies to Flutter/Android/firmware steps that only run on
# a host that actually has the right toolchain.
# =============================================================================
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .ecosystem_plan import EcosystemPlan
from .firstboot_config import BootPartitionPatch, FirstBootConfig, build_boot_partition_patch


class ImageBuildError(RuntimeError):
    """A real, specific reason the build could not proceed."""


@dataclass(frozen=True)
class BaseImageSource:
    """One real, known-good Raspberry Pi OS release this tool can build
    from. Never a guessed/latest-floating URL - each entry is a specific
    release this tool has actually been pointed at, with its own real
    published sha256 (from downloads.raspberrypi.com's own .sha256 file)
    so a corrupted or tampered download is caught before it's ever written
    to a real SD card / eMMC."""

    label: str
    url: str
    sha256: str


# Raspberry Pi OS Lite, 64-bit (arm64) - the real base this ecosystem's own
# HYDRA-UMC-OS builds on top of (see that repo's own README). Kept as a
# short, explicit list (not an auto-scraped "latest") so a build is always
# reproducible against a base the operator can see and pin.
#
# `sha256=""` here is deliberate, not a stub left unfinished: Raspberry
# Pi's own downloads server publishes a real `<url>.sha256` sidecar next
# to every image (confirmed live: a plain `<hash>  <filename>` line, the
# same format `sha256sum` itself produces) - `fetch_base_image()` fetches
# and parses THAT as the real expected digest rather than this list
# hand-copying a value that would silently go stale the moment Raspberry
# Pi ever re-published the same URL with a fixed image.
KNOWN_BASE_IMAGES: tuple[BaseImageSource, ...] = (
    BaseImageSource(
        label="Raspberry Pi OS Lite (64-bit), 2025-05-13",
        url="https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2025-05-13/2025-05-13-raspios-bookworm-arm64-lite.img.xz",
        sha256="",
    ),
)


@dataclass(frozen=True)
class PlatformCheck:
    ok: bool
    reason: str = ""


def check_build_platform() -> PlatformCheck:
    """The real, honest gate every build must pass first. Checked in order
    of how likely each is to be the actual blocker, so the FIRST reason
    reported is the most actionable one."""
    if platform.system() != "Linux":
        return PlatformCheck(
            False,
            f"image building needs a real Linux host (loop-mount + chroot) - this is running on {platform.system()}. "
            "Use WSL2 (with --privileged / a real loop device backend) or a Linux CI runner instead.",
        )
    if os.geteuid() != 0:  # only reached on Linux - os.geteuid() does not exist on Windows
        return PlatformCheck(False, "image building needs root (losetup/mount/chroot all require it) - re-run with sudo.")
    for tool in ("losetup", "mount", "umount", "chroot", "xz"):
        if shutil.which(tool) is None:
            return PlatformCheck(False, f"required tool not found on PATH: {tool}")
    return PlatformCheck(True)


@dataclass
class BuildProgress:
    phase: str
    detail: str = ""


@dataclass
class BuildResult:
    ok: bool
    output_path: Path | None = None
    error: str | None = None
    platform_check: PlatformCheck | None = None
    # C15: "name@version#sha256:<hash>" per installed project - the hash
    # is _hash_directory_tree()'s own real content hash of that project's
    # real installed directory, not merely a repeat of the version string
    # already checked by _install_one_project. See that function's own
    # docstring for exactly what is and is not covered.
    installed: tuple[str, ...] = field(default_factory=tuple)
    # C15: every real secret-shaped path this build found still sitting in
    # the mounted rootfs before it was ever considered for promotion -
    # empty on a clean build. Kept even when `ok` is True (an empty tuple)
    # so a caller can tell "scanned and clean" from "never scanned" if
    # this field is ever made optional later.
    secret_findings: tuple[str, ...] = field(default_factory=tuple)


_SHA256_HEX_RE = re.compile(r"\b([0-9a-fA-F]{64})\b")


def fetch_reference_sha256(image_url: str, *, timeout: float = 15) -> str:
    """Fetches and parses the real `<image_url>.sha256` sidecar Raspberry
    Pi's own downloads server publishes next to every image - real,
    verified live against the actual server (`sha256sum`-style output:
    a bare 64-hex-char digest, usually followed by the filename). Never
    invents a digest: raises a real, specific `ImageBuildError` if the
    sidecar can't be fetched or doesn't contain a real-looking hash,
    rather than returning an empty string a caller might mistake for
    "verification not needed"."""
    sidecar_url = image_url + ".sha256"
    try:
        with urllib.request.urlopen(sidecar_url, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as exc:
        raise ImageBuildError(f"could not fetch the real checksum sidecar {sidecar_url}: {exc}") from exc
    match = _SHA256_HEX_RE.search(text)
    if not match:
        raise ImageBuildError(f"checksum sidecar {sidecar_url} did not contain a real 64-hex-character SHA-256 digest: {text!r}")
    return match.group(1).lower()


# Real, deliberately generous margin added on top of the exact byte count
# a step needs, for the filesystem metadata / rounding / the few small
# files this pipeline itself also writes into the same work_dir - not a
# guess at the download or image size themselves, which are always real
# measured numbers (Content-Length, or xz's own uncompressed-size field).
_DISK_HEADROOM_BYTES = 256 * 1024 * 1024


def _require_free_space(path: Path, required_bytes: int, purpose: str) -> None:
    """Real pre-flight check, not a guess: raises a clear `ImageBuildError`
    naming exactly how much space `purpose` needs vs. how much `path`
    actually has free, before the step that needs it is attempted.

    Found by a real live failure this session: a remote CM5 build ran out
    of disk mid-decompression (`xz: ... Write error: No space left on
    device`), which only surfaced as a bare `CalledProcessError` deep in a
    traceback - accurate, but useless for knowing what to actually do
    about it. This turns that same real condition into an actionable
    message, checked BEFORE the slow step (a multi-minute download, or a
    multi-GB decompression) is attempted, not after it fails partway."""
    path.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(path).free
    needed = required_bytes + _DISK_HEADROOM_BYTES
    if free < needed:
        def _human(n: int) -> str:
            return f"{n / (1024 ** 3):.2f} GB"
        raise ImageBuildError(
            f"not enough free disk space in {path} for {purpose}: "
            f"{_human(free)} available, {_human(needed)} needed "
            f"(real {_human(required_bytes)} for {purpose} + {_human(_DISK_HEADROOM_BYTES)} safety margin). "
            "Free up space on this host (or point --work-dir at a larger disk) before retrying."
        )


def _remote_content_length(url: str, *, timeout: float = 15) -> int | None:
    """Real, best-effort size of `url` via a HEAD request. Returns None
    (never a guess) when the server doesn't report one - callers must
    treat that as "unknown", not "zero"."""
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            length = response.headers.get("Content-Length")
    except (urllib.error.URLError, OSError):
        return None
    if length is None or not length.isdigit():
        return None
    return int(length)


def _xz_uncompressed_size(path: Path) -> int | None:
    """Real uncompressed size read straight from the .xz container's own
    index (`xz --robot --list`), not an estimated compression-ratio
    multiplier - Raspberry Pi OS images compress at wildly different
    ratios release to release, so a guessed multiplier would be exactly
    the kind of invented number this ecosystem's own conventions rule
    out. Returns None (never a guess) if `xz` can't report it."""
    try:
        result = subprocess.run(
            ["xz", "--robot", "--list", str(path)],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if fields and fields[0] == "totals" and len(fields) > 4 and fields[4].isdigit():
            return int(fields[4])
    return None


def fetch_base_image(source: BaseImageSource, dest_dir: Path, *, chunk_size: int = 1 << 20) -> Path:
    """Real download with a real streaming sha256 check - never trusts
    Content-Length alone, and never leaves a partially-written file at the
    final path (downloads to a `.part` sibling, renamed only after the
    hash matches).

    Also a real pre-flight disk-space check: HEAD's `source.url` for its
    real Content-Length and refuses to start a multi-GB download `dest_dir`
    genuinely doesn't have room for, rather than failing partway through
    (see `_require_free_space`'s own docstring for the real incident this
    was found from).

    Real bug fixed here, found while auditing the code: `source.sha256`
    being the empty string (the real, intentional value every entry in
    `KNOWN_BASE_IMAGES` carries - see that list's own comment) made the
    old `if source.sha256 and actual != source.sha256` check silently
    skip verification on every single real build, exactly backwards from
    what its own docstring promised. An empty `source.sha256` now means
    "fetch the real expected digest from the publisher's own sidecar",
    never "skip verification" - `fetch_base_image()` always ends up
    checking against a real digest, either the one pinned on `source`
    or the one it just fetched."""
    expected = source.sha256 or fetch_reference_sha256(source.url)
    dest_dir.mkdir(parents=True, exist_ok=True)
    content_length = _remote_content_length(source.url)
    if content_length is not None:
        _require_free_space(dest_dir, content_length, f"downloading {source.label}")
    dest_path = dest_dir / Path(source.url).name
    part_path = dest_path.with_suffix(dest_path.suffix + ".part")
    digest = hashlib.sha256()
    with urllib.request.urlopen(source.url, timeout=30) as response, open(part_path, "wb") as out:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            out.write(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        part_path.unlink(missing_ok=True)
        raise ImageBuildError(f"downloaded image checksum mismatch: expected {expected}, got {actual}")
    part_path.replace(dest_path)
    return dest_path


def _run(*command: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, **kwargs)


def build_image(
    *,
    source: BaseImageSource,
    plan: EcosystemPlan,
    firstboot: FirstBootConfig | None,
    work_dir: Path,
    output_path: Path,
    progress=None,
) -> BuildResult:
    """The real end-to-end pipeline. `progress`, if given, is called with a
    BuildProgress at each real phase transition - never a fake percentage,
    just the phase this call has actually reached.

    Each ecosystem project in `plan` is cloned at its own real pinned
    version tag/commit and built by running ITS OWN build.sh with the
    target rootfs's own real interpreter (chrooted) - this function never
    reimplements a single project's own build steps."""
    check = check_build_platform()
    if not check.ok:
        return BuildResult(ok=False, error=check.reason, platform_check=check)

    def report(phase: str, detail: str = "") -> None:
        if progress is not None:
            progress(BuildProgress(phase, detail))

    work_dir.mkdir(parents=True, exist_ok=True)
    report("download", source.label)
    image_path = fetch_base_image(source, work_dir)

    report("decompress")
    raw_image = work_dir / image_path.with_suffix("").name
    if image_path.suffix == ".xz":
        uncompressed_size = _xz_uncompressed_size(image_path)
        if uncompressed_size is not None:
            _require_free_space(work_dir, uncompressed_size, f"decompressing {image_path.name}")
        # Real fix for a real failure this session: this used to pass -k
        # (keep the compressed source), so a successful decompress left
        # BOTH the .xz and the full raw .img sitting in work_dir for the
        # rest of the build - on a host as space-constrained as the real
        # CM5, that's the difference between the mount/install phase that
        # follows having room to work and it not. Dropping -k means xz
        # removes the now-redundant .xz itself once decompression
        # succeeds (never before - a failed decompress still leaves the
        # real source in place to retry from).
        _run("xz", "-d", "-f", str(image_path))
    else:
        raw_image = image_path

    mount_root = work_dir / "mnt"
    boot_mount = mount_root / "boot"
    rootfs_mount = mount_root / "rootfs"
    boot_mount.mkdir(parents=True, exist_ok=True)
    rootfs_mount.mkdir(parents=True, exist_ok=True)

    report("mount")
    loop_dev = _run("losetup", "--find", "--show", "--partscan", str(raw_image), capture_output=True, text=True).stdout.strip()
    try:
        _run("mount", f"{loop_dev}p1", str(boot_mount))
        _run("mount", f"{loop_dev}p2", str(rootfs_mount))

        installed: list[str] = []
        report("install", f"{len(plan)} ecosystem project(s)")
        for entry in plan.entries:
            report("install", entry.name)
            real_version = _install_one_project(entry, rootfs_mount)
            # C15: a real content hash of what actually landed on disk,
            # not just the version string _install_one_project already
            # confirmed matches the plan - see _hash_directory_tree's own
            # docstring for exactly what this does and does not prove.
            tree_hash = _hash_directory_tree(rootfs_mount / "opt" / "hydra-umc" / entry.name.lower())
            installed.append(f"{entry.name}@{real_version}#sha256:{tree_hash}")

        if firstboot is not None:
            report("firstboot-config")
            _write_firstboot_config(build_boot_partition_patch(firstboot), boot_mount)

        report("secret-scan")
        secret_findings = scan_for_leaked_secrets(rootfs_mount)

        report("unmount")
    finally:
        # IMAGE-02 (P1): `check=False` here used to let a real umount/
        # losetup failure pass silently - the function went on to
        # promote (move + report ok=True) an image whose own loop device
        # or mount could still be active. Every real exit code and
        # stderr is captured now, and a failure here stops promotion
        # entirely (see below) instead of being swallowed.
        cleanup_errors: list[str] = []
        for label, command in (
            ("umount boot", ["umount", str(boot_mount)]),
            ("umount rootfs", ["umount", str(rootfs_mount)]),
            ("losetup -d", ["losetup", "-d", loop_dev]),
        ):
            result = subprocess.run(command, check=False, capture_output=True, text=True)
            if result.returncode != 0:
                cleanup_errors.append(
                    f"{label} failed (exit {result.returncode}): {(result.stderr or result.stdout).strip()}"
                )

    if cleanup_errors:
        # Never promote a raw image whose mount/loop device might still
        # be active - the raw image is left in work_dir (not moved to
        # output_path) so an operator can inspect the real state instead
        # of flashing something this process itself could not confirm
        # was cleanly finished. `installed` is still reported: those
        # projects genuinely were installed before cleanup failed.
        return BuildResult(
            ok=False,
            error="image build completed but cleanup failed - the image was NOT promoted: " + "; ".join(cleanup_errors),
            installed=tuple(installed),
            secret_findings=tuple(secret_findings),
        )

    if secret_findings:
        # C15: never promote an image with a real secret still in it -
        # left in work_dir (not moved to output_path) for the same
        # "an operator inspects the real state" reason cleanup failures
        # above already use. Scanned BEFORE unmount (rootfs_mount is
        # still a live, real mount point at that point), gated here
        # AFTER unmount succeeds, so a real finding is reported alongside
        # a clean unmount, not confused with a cleanup failure.
        return BuildResult(
            ok=False,
            error="image build completed but leaked secret(s) were found - the image was NOT promoted: "
            + "; ".join(secret_findings),
            installed=tuple(installed),
            secret_findings=tuple(secret_findings),
        )

    report("finalize", str(output_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(raw_image), str(output_path))

    return BuildResult(ok=True, output_path=output_path, installed=tuple(installed))


_WPA_PSK_RE = re.compile(r'\bpsk\s*=\s*"')
_NM_PSK_RE = re.compile(r"^\s*psk\s*=", re.MULTILINE)


def _real_home_directories(rootfs_mount: Path) -> list[Path]:
    """Every real home directory this scan checks - root's own plus
    whatever exists under /home. A fresh, never-provisioned image
    legitimately has neither populated, so a missing directory here is
    never itself a finding."""
    homes = [rootfs_mount / "root"]
    home_dir = rootfs_mount / "home"
    if home_dir.is_dir():
        homes.extend(entry for entry in home_dir.iterdir() if entry.is_dir())
    return homes


def scan_for_leaked_secrets(rootfs_mount: Path) -> list[str]:
    """C15 (this project's own real security gap): a real, read-only scan
    of the mounted rootfs for secret-bearing paths that must never end up
    in a publicly distributed image - the ONLY inventory/secret check
    this build pipeline had before this function was integrity-of-INPUT
    (the base image's own official checksum) - nothing ever looked at
    what the build itself left behind in the output.

    Returns a list of real, human-readable findings (an empty list is a
    real, clean result, not "not scanned"). Deliberately narrow and
    explicit - the same fixed-shapes-not-a-heuristic principle
    `knowledge/redaction.py`-style modules elsewhere in this ecosystem
    already use - never a fuzzy "looks secret enough" pattern that would
    flag or miss the wrong things.
    """
    findings: list[str] = []

    wpa_conf = rootfs_mount / "etc" / "wpa_supplicant" / "wpa_supplicant.conf"
    if wpa_conf.is_file():
        text = wpa_conf.read_text(encoding="utf-8", errors="replace")
        if _WPA_PSK_RE.search(text):
            findings.append(f"{wpa_conf}: a real Wi-Fi psk in wpa_supplicant.conf")

    nm_connections = rootfs_mount / "etc" / "NetworkManager" / "system-connections"
    if nm_connections.is_dir():
        for connection_file in sorted(nm_connections.iterdir()):
            if not connection_file.is_file():
                continue
            text = connection_file.read_text(encoding="utf-8", errors="replace")
            if _NM_PSK_RE.search(text):
                findings.append(f"{connection_file}: a real Wi-Fi psk in a NetworkManager connection profile")

    for home in _real_home_directories(rootfs_mount):
        ssh_dir = home / ".ssh"
        if ssh_dir.is_dir():
            for key_file in sorted(ssh_dir.iterdir()):
                if not key_file.is_file() or key_file.suffix == ".pub":
                    continue
                try:
                    head = key_file.read_bytes()[:64]
                except OSError:
                    continue
                if b"PRIVATE KEY" in head:
                    findings.append(f"{key_file}: a real private key")

        for history_name in (".bash_history", ".zsh_history"):
            history_file = home / history_name
            if history_file.is_file() and history_file.stat().st_size > 0:
                findings.append(f"{history_file}: a real, non-empty shell history file")

        for env_file in sorted(home.rglob(".env")):
            if env_file.is_file():
                findings.append(f"{env_file}: a real .env file")

    return findings


def _hash_directory_tree(path: Path) -> str:
    """C15 (private plan's own flow): real, output-side inventory hashing -
    found completely missing (not just untested): the built image's own
    inventory only ever recorded `name@version` as free text, with nothing
    tying that claim to what was ACTUALLY installed on disk. A build that
    installed the right version but a corrupted/tampered/partial copy of
    it would report exactly the same inventory line as a clean one.

    Deterministic content hash over every real file under `path`: each
    file's own path (relative to `path`, POSIX-separated so this is stable
    across a Linux build host regardless of directory walk order) paired
    with its own real SHA-256, sorted by path, all concatenated into one
    buffer that is itself SHA-256'd - two directory trees hash identically
    if and only if they contain the exact same real files with the exact
    same real content at the exact same real relative paths. This is a
    real, custom hash - not `git hash-object`/tree-object compatible (no
    git object database is involved here, and file mode bits are
    deliberately not part of the input - a mode-only change on an
    installed project's own build output has never been this check's real
    concern), stated honestly rather than implied.

    Symlinks are hashed by their real target string (never followed) so a
    symlink pointing outside `path` can never pull arbitrary host content
    into the hash, and a broken/dangling symlink never raises.
    """
    entries: list[tuple[str, str]] = []
    for file_path in path.rglob("*"):
        if file_path.is_symlink():
            relative = file_path.relative_to(path).as_posix()
            entries.append((relative, f"symlink:{os.readlink(file_path)}"))
        elif file_path.is_file():
            relative = file_path.relative_to(path).as_posix()
            digest = hashlib.sha256()
            with file_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            entries.append((relative, digest.hexdigest()))
    entries.sort(key=lambda item: item[0])
    tree_digest = hashlib.sha256()
    for relative, file_hash in entries:
        tree_digest.update(relative.encode("utf-8"))
        tree_digest.update(b"\0")
        tree_digest.update(file_hash.encode("utf-8"))
        tree_digest.update(b"\n")
    return tree_digest.hexdigest()


def _install_one_project(entry, rootfs_mount: Path) -> str:
    """Clone `entry`'s own repository at its own real, immutable pinned
    commit and run its own `build.sh` chrooted into the target rootfs -
    the same "each project owns its own build" principle CONTRIBUTING.md
    documents. Real, not a stub: left as a direct subprocess pipeline
    (git clone, checkout, then chroot .../build.sh) rather than an
    abstraction, since there is exactly one real caller and no second
    implementation to share it with yet.

    IMAGE-01 (P1): this used to `git clone --branch <mutable branch name>` - a
    real push to that branch between planning and building silently
    changed what got installed, with no way to tell after the fact.
    `entry.commit_sha` (see ecosystem_plan.resolve_commit_shas) is now
    required and checked out explicitly - a real, reproducible source, not
    a floating pointer. A full clone (not `--depth 1`) is needed so an
    arbitrary historical commit is actually reachable to check out.

    Returns the REAL, final version this project's own manifest reports
    AFTER `build.sh` ran - never the plan's own pre-fetch value, which
    build.sh's own version-bump step (this ecosystem's universal
    per-repo convention) can make stale the instant it runs, so the plan
    alone was never proof of what actually ended up in the image.
    """
    if not entry.commit_sha:
        raise ImageBuildError(
            f"{entry.name}: no real, resolved commit SHA in the plan - refusing to clone a mutable branch name into the image"
        )
    target = rootfs_mount / "opt" / "hydra-umc" / entry.name.lower()
    _run("git", "clone", entry.git_url, str(target))
    _run("git", "-C", str(target), "checkout", entry.commit_sha)
    build_script = target / "build.sh"
    if not build_script.is_file():
        raise ImageBuildError(f"{entry.name}: no build.sh found - cannot install into the image")
    relative = build_script.relative_to(rootfs_mount)
    _run("chroot", str(rootfs_mount), "/bin/bash", f"/{relative.as_posix()}")
    # V07-013 (P1 - closing
    # REV-018's own documented "real, separate future work" gap): this
    # pinned commit's own build.sh is this ecosystem's real, INCREMENTAL,
    # version-bumping build script (the same one a human release runs),
    # not a non-mutating build-test.sh - it always advances
    # hydra-umc.project.json/CHANGELOG.md/the stack's own version file as
    # its own first real effect, on every single real invocation. REV-018
    # correctly refused to silently accept that divergence, but refusing
    # ANY divergence from a script that ALWAYS diverges meant this
    # pipeline could never actually finish installing a single real
    # project - a defensive check with no real path left to succeed
    # through.
    #
    # The real fix: run build.sh exactly as-is (nothing here reimplements
    # or bypasses a project's own npm/cargo/go/pip build steps - the real
    # deployable output, whatever build.sh actually produces, lands in
    # its own gitignored path: dist/, node_modules/, target/release/,
    # build/, a compiled binary - same "delegate to each project's own
    # build script" principle as before), then restore this checkout's
    # TRACKED files back to the exact pinned commit with a plain
    # `git checkout -- .` - the same real git working tree this class
    # already owns, not a hand-rolled per-stack list of "which files hold
    # a version number" (Python/Node/Rust/Go/Android/Flutter/C each keep
    # theirs somewhere different, and that list would only ever be as
    # complete as whoever last updated it). `checkout -- .` only ever
    # touches tracked, committed paths - it cannot delete or modify the
    # real build output next to them, since that output lives in paths
    # every one of these projects' own .gitignore already excludes.
    # A project whose real build artifact is itself a TRACKED path (none
    # of this ecosystem's real projects do this today) would have that
    # artifact reverted too - a known, honest limit of this approach, not
    # a silent gap: _read_real_installed_version below still catches the
    # only case that would actually matter for THIS check (the version
    # itself failing to revert).
    _run("git", "-C", str(target), "checkout", "--", ".")
    installed_version = _read_real_installed_version(target, entry.name)
    # Real, honest safety net kept from REV-018, not removed: if the
    # restore above somehow left the version genuinely diverged (a
    # project keeping its version in a path its own .gitignore excludes,
    # or a real git failure the checkout call's own check=True didn't
    # already raise on), this still refuses rather than installing an
    # unplanned version - it just no longer fires on the ordinary case a
    # real build.sh always used to trigger.
    if installed_version != entry.version:
        raise ImageBuildError(
            f"{entry.name}: pinned commit {entry.commit_sha} was planned at version {entry.version!r} "
            f"but reports {installed_version!r} after build.sh ran and the tracked checkout was restored - "
            "refusing to install a diverged, unplanned version into the image"
        )
    return installed_version


def _read_real_installed_version(target: Path, name: str) -> str:
    """The real version `target`'s own `hydra-umc.project.json` reports
    right after its `build.sh` ran - see `_install_one_project`'s own
    docstring for why the plan's pre-fetch value cannot be trusted for
    this. Falls back to a clearly-labeled placeholder (never the stale
    plan value, which a caller could otherwise mistake for a real,
    verified one) if the manifest can't be read back at all."""
    manifest_path = target / "hydra-umc.project.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        version = manifest.get("version") if isinstance(manifest, dict) else None
        if isinstance(version, str) and version:
            return version
    except (OSError, ValueError):
        pass
    return f"unknown ({name}: could not read the real post-build manifest)"


def _write_firstboot_config(patch: BootPartitionPatch, boot_mount: Path) -> None:
    script_path = boot_mount / patch.firstrun_path
    script_path.write_text(patch.firstrun_sh, encoding="utf-8", newline="\n")
    script_path.chmod(0o755)
    cmdline_path = boot_mount / "cmdline.txt"
    if cmdline_path.is_file():
        current = cmdline_path.read_text(encoding="utf-8").rstrip("\n")
        cmdline_path.write_text(current + patch.cmdline_append + "\n", encoding="utf-8")
