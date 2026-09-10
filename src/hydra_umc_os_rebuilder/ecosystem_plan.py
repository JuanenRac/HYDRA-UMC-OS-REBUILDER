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
import urllib.error
import urllib.request
from dataclasses import dataclass, replace

from hydra_umc_updater.github_client import RemoteDiscovery, RemoteStatus, discover_remote_projects

GITHUB_API_BASE = "https://api.github.com"


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
    ANY failure (network, 404, rate limit, a malformed response) rather
    than raising or fabricating one - `resolve_commit_shas()` treats that
    exactly like discovery already treats an unreadable manifest: the
    project is excluded from this build, never guessed at."""
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
    branch just because one lookup failed."""
    resolved: list[EcosystemPlanEntry] = []
    errors = list(plan.discovery_errors)
    for entry in plan.entries:
        sha = _fetch_commit_sha(owner, entry.name, entry.branch, token=token)
        if sha is None:
            errors.append(
                f"{entry.name}: could not resolve a real commit SHA for branch {entry.branch!r} - excluded from this build"
            )
            continue
        resolved.append(replace(entry, commit_sha=sha))
    return EcosystemPlan(entries=tuple(resolved), discovery_errors=tuple(errors))


def fetch_ecosystem_plan(*, owner: str = "JuanenRac", token: str | None = None) -> EcosystemPlan:
    """Real network entry point - a thin wrapper so main.py/qt_gui.py never
    need to import hydra_umc_updater's own discovery internals directly."""
    discovery = discover_remote_projects(owner=owner, token=token)
    plan = build_plan(discovery, owner=owner)
    return resolve_commit_shas(plan, owner=owner, token=token)


def plan_summary_lines(plan: EcosystemPlan) -> list[str]:
    """Plain-text lines for the CLI's own `status` output - one real
    project per line, never truncated or summarized away."""
    lines = [f"{entry.name} {entry.version} ({entry.role}/{entry.stack})" for entry in plan.entries]
    if plan.discovery_errors:
        lines.append(f"({len(plan.discovery_errors)} repositor{'y' if len(plan.discovery_errors) == 1 else 'ies'} could not be checked - see --verbose)")
    return lines
