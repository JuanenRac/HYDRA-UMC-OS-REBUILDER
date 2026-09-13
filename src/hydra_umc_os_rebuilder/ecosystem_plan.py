# =============================================================================
# HYDRA-UMC-OS-REBUILDER - Ecosystem freshness plan: ecosystem_plan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Answers "what is the most current real version of every ecosystem project
# that belongs on the CM5, right now" - the input a real image build needs to
# actually be current. Deliberately does NOT reimplement GitHub discovery or
# manifest parsing: hydra_umc_updater.github_client.discover_remote_projects()
# already does exactly this (scan the real GitHub account, open every public
# repository's own hydra-umc.project.json, keep the ones that opt into this
# ecosystem) - duplicating ~600 lines of already-tested discovery/retry/
# manifest-validation logic here would only risk it silently drifting from
# the updater's own. This module's only real job is the one thing that IS
# new: filtering that real discovery down to `deployment_target: "cm5"`
# (the only projects a CM5 image actually needs to carry) and turning it
# into a plain, serializable plan image_builder.py can act on.
# =============================================================================
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, replace

from hydra_umc_updater.github_client import (
    RemoteDiscovery,
    RemoteStatus,
    describe_http_error,
    discover_remote_projects,
    is_primary_rate_limited,
)

GITHUB_API_BASE = "https://api.github.com"


class GitHubRateLimitedError(RuntimeError):
    """Real bug found from a live report: repeated GitHub refreshes
    silently listed fewer and fewer projects (42 -> 9 -> 0), staying at 0
    even after restarting the app. Root cause: `resolve_commit_shas()`
    below spends one `api.github.com` call PER PROJECT to resolve a real
    commit SHA, on an unauthenticated 60-requests-PER-HOUR budget shared
    with the repo-listing call - with ~50+ real ecosystem projects, a
    SINGLE refresh can exhaust the whole hourly budget, and every
    following click (before the real GitHub-side hour window resets, not
    an app-restartable state) has less and less of it left. `_fetch_commit_sha`
    used to catch this exactly like a 404 (silently return `None`,
    "excluded from this build") - this dedicated exception lets
    `resolve_commit_shas()` tell the two apart and stop immediately
    instead of burning the rest of an already-dead budget one doomed
    request at a time."""


@dataclass(frozen=True)
class EcosystemPlanEntry:
    name: str
    version: str
    role: str
    stack: str
    git_url: str
    branch: str = "main"
    # IMAGE-01 (P1): `branch` alone is a mutable pointer - a real push to `main`
    # between this plan being built and an image actually being built
    # from it silently changes what gets installed. `commit_sha` is the
    # real, immutable identity `_install_one_project` now clones and
    # checks out instead - see `resolve_commit_shas()` below for how it
    # gets filled in. `None` here means "not yet resolved" (the shape
    # `build_plan()` itself, a pure/offline function, produces).
    commit_sha: str | None = None
    # I12 ("Verificacion del contenido distribuido fuera del checkout"):
    # relative paths (POSIX-style, relative to this project's own
    # installed root) a human profile author has curated as genuinely
    # required for this project to actually work once installed - e.g. a
    # UI's compiled index.html, a service's real entry point. Empty by
    # default (live discovery alone has no way to know this); a frozen
    # ProfileManifestEntry is where a human actually declares it (see
    # profile_manifest.py's set_required_resources()), carried onto this
    # dataclass by manifest_to_ecosystem_plan() so build_image() can
    # verify it for real, in the one place that actually installs
    # anything. Never invented or guessed here.
    required_resources: tuple[str, ...] = ()


@dataclass(frozen=True)
class EcosystemPlan:
    """Every real `deployment_target: "cm5"` project discovered on GitHub,
    at the exact version its own manifest currently declares - never a
    fixed/hardcoded list, matching this ecosystem's own dynamic-discovery
    convention everywhere else (see [[project_manifest_dynamic_discovery]])."""

    entries: tuple[EcosystemPlanEntry, ...]
    discovery_errors: tuple[str, ...]

    def __len__(self) -> int:
        return len(self.entries)


def _git_url(owner: str, name: str) -> str:
    return f"https://github.com/{owner}/{name}.git"


def build_plan(discovery: RemoteDiscovery, *, owner: str = "JuanenRac") -> EcosystemPlan:
    """Pure function over an already-fetched RemoteDiscovery - kept
    separate from fetch_ecosystem_plan() below purely so tests can exercise
    the real filtering/sorting logic against a canned RemoteDiscovery,
    without ever making a real network call."""
    entries: list[EcosystemPlanEntry] = []
    for status in discovery.projects:
        manifest = status.manifest
        if manifest is None or status.version is None:
            continue
        if manifest.deployment_target != "cm5":
            continue
        entries.append(
            EcosystemPlanEntry(
                name=manifest.name,
                version=str(status.version),
                role=manifest.role,
                stack=manifest.stack,
                git_url=_git_url(owner, manifest.name),
            )
        )
    entries.sort(key=lambda entry: entry.name.casefold())
    return EcosystemPlan(entries=tuple(entries), discovery_errors=discovery.errors)


def _fetch_commit_sha(owner: str, name: str, branch: str, *, token: str | None, timeout: float = 15) -> str | None:
    """IMAGE-01: the real, immutable HEAD commit SHA for `owner/name`'s
    `branch`, via GitHub's own real REST API (never guessed, never
    derived from the raw-content fetch discovery already does - that
    endpoint doesn't expose a commit identity at all). Returns `None` on
    an ordinary failure (network, 404, a malformed response) rather than
    raising or fabricating one - `resolve_commit_shas()` treats that
    exactly like discovery already treats an unreadable manifest: the
    project is excluded from this build, never guessed at.

    Raises `GitHubRateLimitedError` instead of returning `None` when the
    failure is specifically GitHub's real PRIMARY rate limit - a
    genuinely different situation from "this one repo/branch has a
    problem": every remaining call in this same batch is doomed too, so
    the caller needs to know to stop, not keep excluding one project at
    a time until none are left.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{name}/commits/{branch}"
    headers = {
        "User-Agent": "hydra-umc-os-rebuilder",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if is_primary_rate_limited(exc):
            raise GitHubRateLimitedError(describe_http_error(exc)) from exc
        return None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    sha = payload.get("sha") if isinstance(payload, dict) else None
    return sha if isinstance(sha, str) and sha else None


def resolve_commit_shas(plan: EcosystemPlan, *, owner: str = "JuanenRac", token: str | None = None) -> EcosystemPlan:
    """IMAGE-01's own real second pass over an already-built
    `EcosystemPlan`: resolves each entry's real, immutable commit SHA so
    `image_builder._install_one_project` clones an exact, reproducible
    source instead of a mutable branch name that could have moved
    between planning and building. An entry whose SHA cannot be resolved
    is EXCLUDED from the returned plan (recorded in `discovery_errors`
    instead, the same channel a manifest failure already uses) - this
    real fix must never fall back to silently building from an unpinned
    branch just because one lookup failed.

    Real fix for a live report of repeated refreshes silently listing
    fewer and fewer projects (42 -> 9 -> 0, still 0 after restarting the
    app): once GitHub's real PRIMARY rate limit is hit, every remaining
    entry in this loop would fail the exact same way - this stops
    immediately instead of spending the rest of the loop finding that
    out one doomed request at a time, and reports ONE clear, real error
    naming how many entries were actually resolved before the wall, how
    many are excluded because of it, and (via `describe_http_error()`)
    exactly when GitHub's own limit resets.
    """
    resolved: list[EcosystemPlanEntry] = []
    errors = list(plan.discovery_errors)
    for index, entry in enumerate(plan.entries):
        try:
            sha = _fetch_commit_sha(owner, entry.name, entry.branch, token=token)
        except GitHubRateLimitedError as exc:
            # `index` itself is the entry that just hit the limit (a real
            # attempt, not a skipped one) - counted together with every
            # entry after it under "excluded", since neither ever made it
            # into `resolved` either way.
            excluded = len(plan.entries) - len(resolved)
            errors.append(
                f"GitHub commit-SHA resolution stopped after {len(resolved)} of {len(plan.entries)} project(s) resolved - "
                f"{exc} - {excluded} project(s) (including the one that hit the limit) are excluded from this build"
            )
            break
        if sha is None:
            errors.append(
                f"{entry.name}: could not resolve a real commit SHA for branch {entry.branch!r} - excluded from this build"
            )
            continue
        resolved.append(replace(entry, commit_sha=sha))
    return EcosystemPlan(entries=tuple(resolved), discovery_errors=tuple(errors))


def fetch_ecosystem_plan(*, owner: str = "JuanenRac", token: str | None = None) -> EcosystemPlan:
    """Real network entry point - a thin wrapper so main.py/qt_gui.py never
    need to import hydra_umc_updater's own discovery internals directly.

    Real fix for a token-fallback inconsistency found while diagnosing the
    rate-limit bug above: `discover_remote_projects()` already falls back
    to the real `GITHUB_TOKEN` environment variable when `token` is
    `None`, but `resolve_commit_shas()` never did the same - a user
    relying on that env var (rather than passing a token explicitly to
    THIS function) got an authenticated repo listing but a fully
    unauthenticated, 60/hour-capped commit-SHA resolution pass right
    after it, in the exact same call. The fallback is resolved once,
    here, and threaded through both calls identically.
    """
    resolved_token = token if token is not None else os.environ.get("GITHUB_TOKEN") or None
    discovery = discover_remote_projects(owner=owner, token=resolved_token)
    plan = build_plan(discovery, owner=owner)
    return resolve_commit_shas(plan, owner=owner, token=resolved_token)


def plan_summary_lines(plan: EcosystemPlan) -> list[str]:
    """Plain-text lines for the CLI's own `status` output - one real
    project per line, never truncated or summarized away."""
    lines = [f"{entry.name} {entry.version} ({entry.role}/{entry.stack})" for entry in plan.entries]
    if plan.discovery_errors:
        lines.append(f"({len(plan.discovery_errors)} repositor{'y' if len(plan.discovery_errors) == 1 else 'ies'} could not be checked - see --verbose)")
    return lines
