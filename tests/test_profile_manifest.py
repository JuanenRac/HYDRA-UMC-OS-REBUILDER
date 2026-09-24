# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_profile_manifest.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

from pathlib import Path

import pytest

from hydra_umc_os_rebuilder.ecosystem_plan import EcosystemPlan, EcosystemPlanEntry
from hydra_umc_os_rebuilder.profile_manifest import (
    ProfileManifest,
    ProfileManifestError,
    diff_profile,
    freeze_profile,
    load_profile_manifest,
    manifest_to_ecosystem_plan,
    record_build_result,
    refreeze_selected,
    save_profile_manifest,
    set_required_resources,
)


def _entry(name: str, version="0.1.0", role="service", stack="python", sha="a" * 40) -> EcosystemPlanEntry:
    return EcosystemPlanEntry(name=name, version=version, role=role, stack=stack, git_url=f"https://github.com/JuanenRac/{name}.git", commit_sha=sha)


def _plan(*entries: EcosystemPlanEntry) -> EcosystemPlan:
    return EcosystemPlan(entries=tuple(entries), discovery_errors=())


def test_freeze_profile_copies_every_real_field() -> None:
    plan = _plan(_entry("HYDRA-UMC-SERVER", version="0.6.5", sha="c" * 40))
    manifest = freeze_profile(plan, profile_name="cm5-production")
    assert manifest.profile_name == "cm5-production"
    entry = manifest.entry("HYDRA-UMC-SERVER")
    assert entry is not None
    assert entry.version == "0.6.5"
    assert entry.commit_sha == "c" * 40
    assert entry.content_hash is None


def test_freeze_profile_rejects_an_unresolved_commit_sha() -> None:
    plan = _plan(EcosystemPlanEntry(name="X", version="0.1.0", role="service", stack="python", git_url="https://x", commit_sha=None))
    with pytest.raises(ProfileManifestError):
        freeze_profile(plan, profile_name="p")


def test_freeze_profile_rejects_an_empty_name() -> None:
    with pytest.raises(ProfileManifestError):
        freeze_profile(_plan(), profile_name="")


def test_manifest_round_trips_through_json_on_disk(tmp_path: Path) -> None:
    plan = _plan(_entry("HYDRA-UMC-SERVER"), _entry("HYDRA-UMC-STUDIO", role="client", stack="typescript"))
    manifest = freeze_profile(plan, profile_name="cm5-production")
    path = tmp_path / "cm5-production.json"
    save_profile_manifest(manifest, path)
    loaded = load_profile_manifest(path)
    assert loaded == manifest


def test_load_profile_manifest_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(ProfileManifestError):
        load_profile_manifest(path)


def test_load_profile_manifest_rejects_a_json_array(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ProfileManifestError):
        load_profile_manifest(path)


def test_manifest_to_ecosystem_plan_preserves_commit_shas_for_a_real_build() -> None:
    plan = _plan(_entry("A", sha="1" * 40), _entry("B", sha="2" * 40))
    manifest = freeze_profile(plan, profile_name="p")
    rebuilt = manifest_to_ecosystem_plan(manifest)
    assert {e.name: e.commit_sha for e in rebuilt.entries} == {"A": "1" * 40, "B": "2" * 40}
    assert rebuilt.discovery_errors == ()


def test_record_build_result_annotates_matching_entries_with_a_real_content_hash() -> None:
    manifest = freeze_profile(_plan(_entry("A", version="0.1.0")), profile_name="p")
    updated = record_build_result(manifest, installed=("A@0.1.0#sha256:deadbeef",))
    assert updated.entry("A").content_hash == "sha256:deadbeef"


def test_record_build_result_ignores_an_installed_line_for_an_unfrozen_project() -> None:
    manifest = freeze_profile(_plan(_entry("A")), profile_name="p")
    updated = record_build_result(manifest, installed=("SOMETHING-ELSE@1.0.0#sha256:xyz",))
    assert updated.entry("A").content_hash is None


def test_diff_profile_detects_a_project_dropped_from_cm5() -> None:
    manifest = freeze_profile(_plan(_entry("A"), _entry("B")), profile_name="p")
    live = _plan(_entry("A"))  # B no longer discoverable / no longer targets cm5
    diff = diff_profile(manifest, live)
    kinds = {(e.name, e.kind) for e in diff.entries}
    assert ("B", "dropped_from_cm5") in kinds


def test_diff_profile_detects_a_real_commit_update() -> None:
    manifest = freeze_profile(_plan(_entry("A", version="0.1.0", sha="a" * 40)), profile_name="p")
    live = _plan(_entry("A", version="0.2.0", sha="b" * 40))
    diff = diff_profile(manifest, live)
    assert any(e.name == "A" and e.kind == "updated" for e in diff.entries)


def test_diff_profile_detects_role_and_stack_changes_independent_of_version() -> None:
    manifest = freeze_profile(_plan(_entry("A", role="service", stack="python")), profile_name="p")
    live = _plan(_entry("A", role="client", stack="rust"))  # same version/commit, structural change only
    diff = diff_profile(manifest, live)
    kinds = {e.kind for e in diff.entries if e.name == "A"}
    assert "role_changed" in kinds
    assert "stack_changed" in kinds


def test_diff_profile_detects_a_newly_added_cm5_project() -> None:
    manifest = freeze_profile(_plan(_entry("A")), profile_name="p")
    live = _plan(_entry("A"), _entry("NEW-PROJECT"))
    diff = diff_profile(manifest, live)
    assert any(e.name == "NEW-PROJECT" and e.kind == "added" for e in diff.entries)


def test_diff_profile_of_an_unchanged_profile_has_no_findings() -> None:
    plan = _plan(_entry("A"), _entry("B"))
    manifest = freeze_profile(plan, profile_name="p")
    diff = diff_profile(manifest, plan)
    assert not diff.has_changes()
    assert len(diff) == 0


def test_refreeze_selected_updates_only_the_named_projects() -> None:
    manifest = freeze_profile(_plan(_entry("A", version="0.1.0", sha="a" * 40), _entry("B", version="0.1.0", sha="b" * 40)), profile_name="p")
    live = _plan(_entry("A", version="0.2.0", sha="c" * 40), _entry("B", version="0.9.0", sha="d" * 40))
    refrozen = refreeze_selected(manifest, live, {"A"})
    assert refrozen.entry("A").version == "0.2.0"
    assert refrozen.entry("A").commit_sha == "c" * 40
    # B was NOT in the update set - stays pinned exactly as frozen before,
    # even though `live` shows it changed too.
    assert refrozen.entry("B").version == "0.1.0"
    assert refrozen.entry("B").commit_sha == "b" * 40


def test_refreeze_selected_can_add_a_project_not_previously_frozen() -> None:
    manifest = freeze_profile(_plan(_entry("A")), profile_name="p")
    live = _plan(_entry("A"), _entry("NEW-PROJECT", sha="e" * 40))
    refrozen = refreeze_selected(manifest, live, {"NEW-PROJECT"})
    assert refrozen.entry("NEW-PROJECT") is not None
    assert refrozen.entry("NEW-PROJECT").commit_sha == "e" * 40


def test_refreeze_selected_rejects_a_name_missing_from_the_live_plan() -> None:
    manifest = freeze_profile(_plan(_entry("A")), profile_name="p")
    live = _plan(_entry("A"))
    with pytest.raises(ProfileManifestError):
        refreeze_selected(manifest, live, {"DOES-NOT-EXIST"})


def test_refreeze_selected_requires_at_least_one_name() -> None:
    manifest = freeze_profile(_plan(_entry("A")), profile_name="p")
    with pytest.raises(ProfileManifestError):
        refreeze_selected(manifest, _plan(_entry("A")), set())


# =============================================================================
# set_required_resources - the one real place a human curates
# "the real inventory of resources this project needs, for this profile".
# =============================================================================


def test_set_required_resources_updates_only_the_named_entry() -> None:
    manifest = freeze_profile(_plan(_entry("A"), _entry("B")), profile_name="p")
    updated = set_required_resources(manifest, "A", ("dist/index.html", "dist/bundle.js"))
    assert updated.entry("A").required_resources == ("dist/index.html", "dist/bundle.js")
    assert updated.entry("B").required_resources == ()


def test_set_required_resources_rejects_a_project_not_in_the_manifest() -> None:
    manifest = freeze_profile(_plan(_entry("A")), profile_name="p")
    with pytest.raises(ProfileManifestError):
        set_required_resources(manifest, "NOT-FROZEN", ("dist/index.html",))


def test_freeze_profile_never_invents_required_resources() -> None:
    manifest = freeze_profile(_plan(_entry("A")), profile_name="p")
    assert manifest.entry("A").required_resources == ()


def test_required_resources_round_trip_through_json_on_disk(tmp_path: Path) -> None:
    manifest = set_required_resources(freeze_profile(_plan(_entry("A")), profile_name="p"), "A", ("dist/index.html",))
    path = tmp_path / "profile.json"
    save_profile_manifest(manifest, path)
    reloaded = load_profile_manifest(path)
    assert reloaded.entry("A").required_resources == ("dist/index.html",)


def test_manifest_to_ecosystem_plan_carries_required_resources_through_to_build_image(tmp_path: Path) -> None:
    manifest = set_required_resources(freeze_profile(_plan(_entry("A")), profile_name="p"), "A", ("dist/index.html",))
    plan = manifest_to_ecosystem_plan(manifest)
    entry = next(e for e in plan.entries if e.name == "A")
    assert entry.required_resources == ("dist/index.html",)
