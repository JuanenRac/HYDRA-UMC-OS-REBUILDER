# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_main.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json

from hydra_umc_os_rebuilder import main as main_module
from hydra_umc_os_rebuilder.ecosystem_plan import EcosystemPlan, EcosystemPlanEntry
from hydra_umc_os_rebuilder.main import build_parser
from hydra_umc_os_rebuilder.profile_manifest import freeze_profile, load_profile_manifest, save_profile_manifest


def test_status_command_parses() -> None:
    args = build_parser().parse_args(["--cli", "status"])
    assert args.command == "status"
    assert args.owner == "JuanenRac"


def test_status_json_flag_parses() -> None:
    args = build_parser().parse_args(["--cli", "status", "--json"])
    assert args.json is True


def test_status_json_defaults_to_false() -> None:
    args = build_parser().parse_args(["--cli", "status"])
    assert args.json is False


def test_status_json_output_is_real_machine_readable_json(monkeypatch, capsys) -> None:
    """Real end-to-end of _cmd_status's own --json branch, against a fake
    (not network) plan - fetch_ecosystem_plan itself already has its own
    real coverage in test_ecosystem_plan.py; this test is about the CLI's
    own JSON shape, not discovery."""
    fake_plan = EcosystemPlan(
        entries=(
            EcosystemPlanEntry(name="HYDRA-UMC-SDK", version="0.0.3", role="library", stack="python", git_url="https://github.com/JuanenRac/HYDRA-UMC-SDK.git"),
        ),
        discovery_errors=("HYDRA-UMC-BROKEN: manifest not found",),
    )
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: fake_plan)

    exit_code = main_module.main(["--cli", "status", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total"] == 1
    assert payload["projects"] == [
        {"name": "HYDRA-UMC-SDK", "version": "0.0.3", "role": "library", "stack": "python", "git_url": "https://github.com/JuanenRac/HYDRA-UMC-SDK.git", "branch": "main"}
    ]
    assert payload["discovery_errors"] == ["HYDRA-UMC-BROKEN: manifest not found"]


def test_config_command_requires_out() -> None:
    parser = build_parser()
    args = parser.parse_args(["--cli", "config", "--out", "./boot", "--hostname", "cm5", "--wifi-country", "ES"])
    assert args.command == "config"
    assert args.out == "./boot"
    assert args.hostname == "cm5"
    assert args.no_ssh is False
    assert args.acknowledge_no_remote_access is False


def test_config_command_parses_the_recovery_acknowledgment_flag() -> None:
    args = build_parser().parse_args(["--cli", "config", "--out", "./boot", "--no-ssh", "--acknowledge-no-remote-access"])
    assert args.no_ssh is True
    assert args.acknowledge_no_remote_access is True


def test_build_image_command_parses_with_defaults() -> None:
    args = build_parser().parse_args(["--cli", "build-image", "--out", "x.img"])
    assert args.command == "build-image"
    assert args.work_dir == "work"


def test_custom_owner_is_threaded_through() -> None:
    args = build_parser().parse_args(["--owner", "SomeoneElse", "--cli", "status"])
    assert args.owner == "SomeoneElse"


# --- profile-freeze / profile-diff / profile-update ----------------


def _fake_plan(*names_and_shas: tuple[str, str]) -> EcosystemPlan:
    return EcosystemPlan(
        entries=tuple(
            EcosystemPlanEntry(name=n, version="0.1.0", role="service", stack="python", git_url=f"https://github.com/JuanenRac/{n}.git", commit_sha=sha)
            for n, sha in names_and_shas
        ),
        discovery_errors=(),
    )


def test_profile_freeze_writes_a_real_manifest_file(monkeypatch, tmp_path, capsys) -> None:
    plan = _fake_plan(("HYDRA-UMC-SERVER", "a" * 40))
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: plan)
    out_path = tmp_path / "cm5-production.json"

    exit_code = main_module.main(["--cli", "profile-freeze", "--name", "cm5-production", "--out", str(out_path)])

    assert exit_code == 0
    assert "PROFILE_FROZEN" in capsys.readouterr().out
    manifest = load_profile_manifest(out_path)
    assert manifest.profile_name == "cm5-production"
    assert manifest.entry("HYDRA-UMC-SERVER").commit_sha == "a" * 40


def test_profile_diff_reports_an_updated_project(monkeypatch, tmp_path, capsys) -> None:
    frozen = freeze_profile(_fake_plan(("A", "a" * 40)), profile_name="p")
    manifest_path = tmp_path / "p.json"
    save_profile_manifest(frozen, manifest_path)
    live = _fake_plan(("A", "b" * 40))
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: live)

    exit_code = main_module.main(["--cli", "profile-diff", "--manifest", str(manifest_path)])

    assert exit_code == 0
    assert "UPDATED A" in capsys.readouterr().out


def test_profile_diff_reports_no_changes_for_an_identical_profile(monkeypatch, tmp_path, capsys) -> None:
    plan = _fake_plan(("A", "a" * 40))
    frozen = freeze_profile(plan, profile_name="p")
    manifest_path = tmp_path / "p.json"
    save_profile_manifest(frozen, manifest_path)
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: plan)

    exit_code = main_module.main(["--cli", "profile-diff", "--manifest", str(manifest_path)])

    assert exit_code == 0
    assert "PROFILE_UNCHANGED" in capsys.readouterr().out


def test_profile_update_pins_unselected_projects_and_writes_to_out(monkeypatch, tmp_path, capsys) -> None:
    frozen = freeze_profile(_fake_plan(("A", "a" * 40), ("B", "b" * 40)), profile_name="p")
    manifest_path = tmp_path / "p.json"
    save_profile_manifest(frozen, manifest_path)
    live = _fake_plan(("A", "c" * 40), ("B", "d" * 40))
    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: live)
    out_path = tmp_path / "p-updated.json"

    exit_code = main_module.main(["--cli", "profile-update", "--manifest", str(manifest_path), "--project", "A", "--out", str(out_path)])

    assert exit_code == 0
    updated = load_profile_manifest(out_path)
    assert updated.entry("A").commit_sha == "c" * 40
    assert updated.entry("B").commit_sha == "b" * 40  # not selected - stays pinned


def test_profile_set_required_resources_writes_the_real_inventory(monkeypatch, tmp_path, capsys) -> None:
    frozen = freeze_profile(_fake_plan(("A", "a" * 40)), profile_name="p")
    manifest_path = tmp_path / "p.json"
    save_profile_manifest(frozen, manifest_path)

    exit_code = main_module.main([
        "--cli", "profile-set-required-resources", "--manifest", str(manifest_path),
        "--project", "A", "--resource", "dist/index.html", "--resource", "server/main.py",
    ])

    assert exit_code == 0
    assert "PROFILE_RESOURCES_SET" in capsys.readouterr().out
    updated = load_profile_manifest(manifest_path)
    assert updated.entry("A").required_resources == ("dist/index.html", "server/main.py")


def test_profile_set_required_resources_rejects_an_unfrozen_project(tmp_path, capsys) -> None:
    frozen = freeze_profile(_fake_plan(("A", "a" * 40)), profile_name="p")
    manifest_path = tmp_path / "p.json"
    save_profile_manifest(frozen, manifest_path)

    exit_code = main_module.main([
        "--cli", "profile-set-required-resources", "--manifest", str(manifest_path),
        "--project", "NOT-FROZEN", "--resource", "dist/index.html",
    ])

    assert exit_code == 1
    assert "PROFILE_RESOURCES_FAILED" in capsys.readouterr().err


def test_profile_build_command_parses_with_defaults() -> None:
    args = build_parser().parse_args(["--cli", "profile-build", "--manifest", "p.json", "--out", "x.img"])
    assert args.command == "profile-build"
    assert args.work_dir == "work"
