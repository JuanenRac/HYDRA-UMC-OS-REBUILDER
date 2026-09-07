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


def test_build_image_command_parses_with_defaults() -> None:
    args = build_parser().parse_args(["--cli", "build-image", "--out", "x.img"])
    assert args.command == "build-image"
    assert args.work_dir == "work"


def test_custom_owner_is_threaded_through() -> None:
    args = build_parser().parse_args(["--owner", "SomeoneElse", "--cli", "status"])
    assert args.owner == "SomeoneElse"
