# =============================================================================
# HYDRA-UMC-OS-REBUILDER - frozen per-profile version manifests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# D05 ("Versiones y compatibilidad del conjunto"): "Fijar una combinacion
# ensayada de componentes por candidato de perfil. Guardar manifest de
# instalacion, procedencia de paquetes, hashes y compatibilidades. No
# sustituir dependencias silenciosamente por 'latest' en mitad de un
# ensayo. Actualizar un cliente no obliga a actualizar todos los servicios
# si el contrato sigue siendo compatible; incompatibilidades deben
# detectarse antes de instalar."
#
# ecosystem_plan.py already answers "what is the most current real version
# of everything, right now" - a live, network-fetched, always-moving
# answer. This module is the other half D05 needs: freeze ONE such answer
# into a named, persisted profile (a real tested combination, not a
# hardcoded one), so a later build can be told to build from EXACTLY that
# frozen combination instead of re-resolving "latest" mid-trial, and so a
# later refresh can be compared against it to see precisely what would
# change before anything is installed.
#
# Deliberately does NOT invent a semantic "compatibility" score from
# version numbers: this ecosystem's own versioning is a base-10 odometer
# with no semantic-versioning meaning (see this repo's own CHANGELOG.md,
# "Versioning scheme") - a version diff alone can never honestly answer
# "is this still compatible". What IS real and checkable without any new,
# invented field is whether a project is still the same project (still
# discoverable, still declaring deployment_target=="cm5", same role/stack)
# - see diff_profile() below for exactly what that does and does not claim
# to detect.
# =============================================================================
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from .ecosystem_plan import EcosystemPlan, EcosystemPlanEntry


class ProfileManifestError(ValueError):
    """A profile manifest could not be frozen, loaded, or safely updated."""


@dataclass(frozen=True)
class ProfileManifestEntry:
    name: str
    version: str
    role: str
    stack: str
    git_url: str
    commit_sha: str
    # Real proof of what actually landed on disk, in the exact
    # "sha256:<hash>" shape image_builder.py's own BuildResult.installed
    # already produces (see record_build_result() below) - None until a
    # real build has actually happened. Never guessed or pre-filled.
    content_hash: str | None = None
    # relative paths a human has curated, for THIS profile, as
    # genuinely required for this entry to work once installed - see
    # set_required_resources() below and ecosystem_plan.EcosystemPlanEntry's
    # own docstring for how this reaches build_image(). Empty by default:
    # freeze_profile() below never invents this from live discovery alone.
    required_resources: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProfileManifest:
    profile_name: str
    entries: tuple[ProfileManifestEntry, ...]
    # The shared SDK checkout that projects declaring `hydra-umc-sdk` are
    # built against inside the image (None: an older manifest, or the
    # SDK commit could not be resolved when the profile was frozen).
    sdk_commit_sha: str | None = None

    def entry(self, name: str) -> ProfileManifestEntry | None:
        for e in self.entries:
            if e.name == name:
                return e
        return None

    def __len__(self) -> int:
        return len(self.entries)


def freeze_profile(plan: EcosystemPlan, *, profile_name: str) -> ProfileManifest:
    """Turns a live EcosystemPlan into a frozen ProfileManifest - the real
    'tested combination of components' D05 asks for. Refuses to freeze an
    entry whose commit SHA never resolved (already excludes those
    from `plan.entries`, but a caller could still hand this a hand-built
    plan) - freezing a mutable branch name instead of an immutable commit
    would defeat the entire point of a frozen profile."""
    if not profile_name:
        raise ProfileManifestError("profile_name cannot be empty")
    frozen: list[ProfileManifestEntry] = []
    for e in plan.entries:
        if not e.commit_sha:
            raise ProfileManifestError(f"{e.name}: cannot freeze a profile entry with no resolved commit SHA")
        frozen.append(
            ProfileManifestEntry(
                name=e.name, version=e.version, role=e.role, stack=e.stack, git_url=e.git_url, commit_sha=e.commit_sha
            )
        )
    return ProfileManifest(profile_name=profile_name, entries=tuple(frozen), sdk_commit_sha=plan.sdk_commit_sha)


def manifest_to_ecosystem_plan(manifest: ProfileManifest) -> EcosystemPlan:
    """The other direction: reconstructs a real EcosystemPlan straight
    from a frozen manifest, with every commit_sha already filled in - so
    build_image() (which only ever needs an EcosystemPlan, see main.py's
    _cmd_build_image) can build from EXACTLY a previously-frozen profile
    without a single new network call, and therefore without any chance
    of silently picking up a 'latest' that moved since the profile was
    frozen. `branch` is left at its default: _install_one_project() only
    ever clones by commit_sha, branch is dead weight here."""
    entries = tuple(
        EcosystemPlanEntry(
            name=e.name, version=e.version, role=e.role, stack=e.stack, git_url=e.git_url, commit_sha=e.commit_sha,
            required_resources=e.required_resources,
        )
        for e in manifest.entries
    )
    return EcosystemPlan(entries=entries, discovery_errors=(), sdk_commit_sha=manifest.sdk_commit_sha)


def to_json(manifest: ProfileManifest) -> dict:
    return {
        "profile_name": manifest.profile_name,
        "sdk_commit_sha": manifest.sdk_commit_sha,
        "entries": [
            {
                "name": e.name,
                "version": e.version,
                "role": e.role,
                "stack": e.stack,
                "git_url": e.git_url,
                "commit_sha": e.commit_sha,
                "content_hash": e.content_hash,
                "required_resources": list(e.required_resources),
            }
            for e in manifest.entries
        ],
    }


def from_json(data: dict) -> ProfileManifest:
    try:
        profile_name = data["profile_name"]
        raw_entries = data["entries"]
    except KeyError as exc:
        raise ProfileManifestError(f"malformed profile manifest: missing {exc}") from exc
    entries = []
    for raw in raw_entries:
        try:
            entries.append(
                ProfileManifestEntry(
                    name=raw["name"],
                    version=raw["version"],
                    role=raw["role"],
                    stack=raw["stack"],
                    git_url=raw["git_url"],
                    commit_sha=raw["commit_sha"],
                    content_hash=raw.get("content_hash"),
                    required_resources=tuple(raw.get("required_resources", ())),
                )
            )
        except KeyError as exc:
            raise ProfileManifestError(f"malformed profile manifest entry: missing {exc}") from exc
    return ProfileManifest(profile_name=profile_name, entries=tuple(entries), sdk_commit_sha=data.get("sdk_commit_sha"))


def save_profile_manifest(manifest: ProfileManifest, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_json(manifest), indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")


def load_profile_manifest(path: Path) -> ProfileManifest:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProfileManifestError(f"could not read profile manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileManifestError(f"malformed profile manifest {path}: top level must be an object")
    return from_json(data)


def record_build_result(manifest: ProfileManifest, installed: tuple[str, ...]) -> ProfileManifest:
    """Folds image_builder.BuildResult.installed's own real
    'name@version#sha256:<hash>' strings back onto the matching frozen
    entries - turns a pre-build ProfileManifest (a recipe only) into a
    post-build one (the recipe plus real proof of what actually landed on
    disk). An installed-line for a project this manifest never froze is
    ignored, never invented into a new entry - record_build_result() only
    ever annotates what freeze_profile() already decided belongs here."""
    hashes: dict[str, str] = {}
    for line in installed:
        try:
            name_version, hash_part = line.split("#", 1)
            name = name_version.split("@", 1)[0]
        except ValueError:
            continue
        hashes[name] = hash_part
    updated = tuple(
        replace(e, content_hash=hashes[e.name]) if e.name in hashes else e
        for e in manifest.entries
    )
    return ProfileManifest(profile_name=manifest.profile_name, entries=updated, sdk_commit_sha=manifest.sdk_commit_sha)


@dataclass(frozen=True)
class ProfileDiffEntry:
    name: str
    kind: str  # "added" | "removed" | "dropped_from_cm5" | "updated" | "role_changed" | "stack_changed"
    detail: str


@dataclass(frozen=True)
class ProfileDiff:
    entries: tuple[ProfileDiffEntry, ...]

    def __len__(self) -> int:
        return len(self.entries)

    def has_changes(self) -> bool:
        return len(self.entries) > 0


def diff_profile(frozen: ProfileManifest, live: EcosystemPlan) -> ProfileDiff:
    """D05's own 'incompatibilidades deben detectarse antes de instalar',
    made concrete: a real, per-project comparison between a previously
    frozen, tested profile and the CURRENT live ecosystem discovery.
    Never collapses to a single pass/fail boolean - every real difference
    is its own line, for a human (or refreeze_selected() below) to act on
    individually. `live` is expected to already be filtered to
    deployment_target=="cm5" (ecosystem_plan.build_plan() already does
    this) - a project missing from `live` therefore means either it no
    longer exists, or it no longer targets cm5 at all; both are reported
    as `dropped_from_cm5` since this function cannot tell those apart
    from `live` alone, and both mean the same thing for this profile: a
    refreeze today would silently lose that project."""
    live_by_name = {e.name: e for e in live.entries}
    frozen_names = {e.name for e in frozen.entries}
    findings: list[ProfileDiffEntry] = []

    for frozen_entry in frozen.entries:
        live_entry = live_by_name.get(frozen_entry.name)
        if live_entry is None:
            findings.append(
                ProfileDiffEntry(
                    frozen_entry.name,
                    "dropped_from_cm5",
                    f"{frozen_entry.name} is no longer discoverable as a cm5 project - refreezing today would drop it",
                )
            )
            continue
        if live_entry.commit_sha and live_entry.commit_sha != frozen_entry.commit_sha:
            findings.append(
                ProfileDiffEntry(
                    frozen_entry.name,
                    "updated",
                    f"{frozen_entry.name}: frozen at {frozen_entry.version} ({frozen_entry.commit_sha[:12]}), "
                    f"live is {live_entry.version} ({live_entry.commit_sha[:12]})",
                )
            )
        if live_entry.role != frozen_entry.role:
            findings.append(
                ProfileDiffEntry(
                    frozen_entry.name,
                    "role_changed",
                    f"{frozen_entry.name}: role changed from {frozen_entry.role!r} to {live_entry.role!r} - "
                    "a structural change version numbers alone would not reveal",
                )
            )
        if live_entry.stack != frozen_entry.stack:
            findings.append(
                ProfileDiffEntry(
                    frozen_entry.name,
                    "stack_changed",
                    f"{frozen_entry.name}: stack changed from {frozen_entry.stack!r} to {live_entry.stack!r}",
                )
            )

    for live_entry in live.entries:
        if live_entry.name not in frozen_names:
            findings.append(
                ProfileDiffEntry(live_entry.name, "added", f"{live_entry.name} now targets cm5 and is not part of this frozen profile")
            )

    findings.sort(key=lambda f: f.name.casefold())
    return ProfileDiff(entries=tuple(findings))


def refreeze_selected(frozen: ProfileManifest, live: EcosystemPlan, names: set[str]) -> ProfileManifest:
    """D05's own 'actualizar un cliente no obliga a actualizar todos los
    servicios si el contrato sigue siendo compatible': builds a NEW
    ProfileManifest starting from `frozen`, updating ONLY the entries
    named in `names` to their current `live` state - every other entry
    stays pinned to exactly what was frozen before (same version, same
    commit_sha, same content_hash if it had one). A name with no match in
    `live` raises rather than silently dropping a real project out of the
    profile; a name with no match in `frozen` is added fresh (the operator
    is deliberately widening the profile, not just refreshing it)."""
    if not names:
        raise ProfileManifestError("refreeze_selected() needs at least one project name to update")
    live_by_name = {e.name: e for e in live.entries}
    updated: list[ProfileManifestEntry] = []
    seen = set()
    for frozen_entry in frozen.entries:
        seen.add(frozen_entry.name)
        if frozen_entry.name in names:
            live_entry = live_by_name.get(frozen_entry.name)
            if live_entry is None or not live_entry.commit_sha:
                raise ProfileManifestError(f"{frozen_entry.name}: not found in the live ecosystem plan (or has no resolved commit SHA) - cannot update it")
            updated.append(
                ProfileManifestEntry(
                    name=live_entry.name, version=live_entry.version, role=live_entry.role,
                    stack=live_entry.stack, git_url=live_entry.git_url, commit_sha=live_entry.commit_sha,
                )
            )
        else:
            updated.append(frozen_entry)
    for extra_name in names - seen:
        live_entry = live_by_name.get(extra_name)
        if live_entry is None or not live_entry.commit_sha:
            raise ProfileManifestError(f"{extra_name}: not found in the live ecosystem plan (or has no resolved commit SHA) - cannot add it")
        updated.append(
            ProfileManifestEntry(
                name=live_entry.name, version=live_entry.version, role=live_entry.role,
                stack=live_entry.stack, git_url=live_entry.git_url, commit_sha=live_entry.commit_sha,
            )
        )
    updated.sort(key=lambda e: e.name.casefold())
    return ProfileManifest(profile_name=frozen.profile_name, entries=tuple(updated), sdk_commit_sha=frozen.sdk_commit_sha)


def set_required_resources(manifest: ProfileManifest, name: str, required_resources: tuple[str, ...]) -> ProfileManifest:
    """the one place a human actually curates 'the real inventory of
    resources this project needs, for this profile' - image_builder.py's
    own build_image() verifies every one of these actually exists on disk
    right after that entry's build.sh runs, before promoting the image
    (see verify_installed_resources()). Deliberately per-profile, not a
    global per-project list: what counts as a required resource for a
    minimal headless profile can differ from a full UI-carrying one.

    Raises rather than silently no-op'ing on a name this manifest never
    froze - curating requirements for a project that isn't actually part
    of this profile is a real mistake to catch immediately, not build a
    frozen manifest around."""
    if manifest.entry(name) is None:
        raise ProfileManifestError(f"{name}: not part of profile {manifest.profile_name!r} - freeze it first")
    updated = tuple(
        replace(e, required_resources=tuple(required_resources)) if e.name == name else e
        for e in manifest.entries
    )
    return ProfileManifest(profile_name=manifest.profile_name, entries=updated, sdk_commit_sha=manifest.sdk_commit_sha)
