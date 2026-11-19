# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_platforms.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The platform of the image (cm5, jetson, generic rk3588): the table, the option of the configuration, the pi-gen stage and the plan. Nothing is built; evidence: simulator."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydra_umc_os_rebuilder import build_backends, build_config, platforms
from hydra_umc_os_rebuilder import main as main_module

COMMIT = "a" * 40
ROOT = Path(__file__).resolve().parent.parent


def config_for(**platform: object) -> dict:
    config = build_config.load_config()
    config["platform"] = {**config["platform"], **platform}
    return config


def test_the_default_is_cm5_and_adds_nothing() -> None:
    config = build_config.load_config()
    assert config["platform"] == {"name": "cm5", "extra_packages": [], "extra_units": [], "partitions": {"boot": 1, "root": 2}}
    declaration = platforms.selected(config)
    assert declaration["packages"] == [] and declaration["units"] == []
    assert platforms.platform_plan(config)["commands"] == []


def test_the_pigen_stage_of_the_default_platform_is_what_it_was_before_the_platforms() -> None:
    files = build_backends.pigen_stage_files({"HYDRA-UMC-OS": COMMIT}, build_config.load_config())
    assert sorted(files) == ["config", "stage-hydra/00-checkouts/00-run.sh", "stage-hydra/EXPORT_IMAGE", "stage-hydra/prerun.sh"]


def test_the_table_names_three_platforms_and_the_generic_one_names_no_board() -> None:
    assert platforms.names() == ["cm5", "jetson", "rk3588"]
    text = json.dumps(platforms.PLATFORMS["rk3588"]).lower()
    assert platforms.PLATFORMS["rk3588"]["generic"] is True
    for model in ("orange", "rock", "radxa", "firefly", "khadas", "friendlyelec", "nanopi", "turing", "rk3588s", "cool pi"):
        assert model not in text
    for declaration in platforms.PLATFORMS.values():
        assert declaration["format"] == platforms.FORMAT and declaration["arch"] == "arm64"
    assert platforms.PLATFORMS["cm5"]["build_backends"] == ["chroot", "nspawn", "pigen"]
    assert all("pigen" not in platforms.PLATFORMS[name]["build_backends"] for name in ("jetson", "rk3588"))


def test_the_table_is_the_one_of_the_os_repository_when_it_is_next_to_this_one() -> None:
    folder = ROOT.parent / "HYDRA-UMC-OS" / "config" / "platforms"
    if not folder.is_dir():
        pytest.skip("HYDRA-UMC-OS is not next to this repository")
    for name in platforms.names():
        assert json.loads((folder / f"{name}.json").read_text(encoding="utf-8")) == platforms.PLATFORMS[name], name


def test_an_unknown_platform_is_an_error_and_a_copy_is_returned() -> None:
    with pytest.raises(platforms.PlatformError):
        platforms.get("orin")
    copy = platforms.get("jetson")
    copy["packages"].append("x")
    assert platforms.PLATFORMS["jetson"]["packages"] == ["nvidia-jetpack"]


def test_the_configuration_chooses_the_platform_and_adds_packages_and_units(tmp_path: Path) -> None:
    file = tmp_path / "c.json"
    file.write_text(json.dumps({"platform": {"name": "jetson", "extra_packages": ["htop", "nvidia-jetpack"], "extra_units": ["nvfancontrol.service", "nvpmodel.service"]}}), encoding="utf-8")
    declaration = platforms.selected(build_config.load_config(file))
    assert declaration["packages"] == ["nvidia-jetpack", "htop"]
    assert [u["name"] for u in declaration["units"]] == ["nvpmodel.service", "nvfancontrol.service"]


@pytest.mark.parametrize(
    "platform",
    [
        {"name": "orin"}, {"name": "jetson", "extra_packages": ["a b"]}, {"name": "jetson", "extra_packages": ["htop", "htop"]}, {"name": "jetson", "extra_packages": [3]},
        {"name": "jetson", "extra_units": ["nvpmodel"]}, {"name": "jetson", "extra_units": ["a.service", "a.service"]},
    ],
)
def test_a_bad_platform_option_is_refused(tmp_path: Path, platform: dict) -> None:
    file = tmp_path / "c.json"
    file.write_text(json.dumps({"platform": platform}), encoding="utf-8")
    with pytest.raises(build_config.BuildConfigError):
        build_config.load_config(file)


@pytest.mark.parametrize(
    "partitions",
    [{"boot": 2, "root": 2}, {"boot": 1, "root": 0}, {"boot": -1, "root": 2}, {"boot": 1, "root": True}, {"boot": 1.5, "root": 2}, {"boot": "1", "root": 2}],
)
def test_a_bad_partition_layout_is_refused(tmp_path: Path, partitions: dict) -> None:
    file = tmp_path / "c.json"
    file.write_text(json.dumps({"platform": {"name": "rk3588", "partitions": partitions}}), encoding="utf-8")
    with pytest.raises(build_config.BuildConfigError):
        build_config.load_config(file)


def test_the_partition_layout_of_the_configuration_reaches_the_build(tmp_path: Path) -> None:
    import argparse

    file = tmp_path / "c.json"
    file.write_text(json.dumps({"platform": {"name": "rk3588", "partitions": {"boot": 0, "root": 3}}}), encoding="utf-8")
    layout = main_module._partition_layout(argparse.Namespace(config=str(file)))
    assert (layout.boot, layout.root, layout.numbers()) == (0, 3, (3,))
    default = main_module._partition_layout(argparse.Namespace(config=None))
    assert (default.boot, default.root, default.numbers()) == (1, 2, (1, 2))


def test_pigen_builds_raspberry_pi_images_only(tmp_path: Path) -> None:
    file = tmp_path / "c.json"
    file.write_text(json.dumps({"platform": {"name": "rk3588"}, "build_backend": {"name": "pigen"}}), encoding="utf-8")
    with pytest.raises(build_config.BuildConfigError, match="cannot be built with pigen"):
        build_config.load_config(file)
    config = config_for(name="jetson")
    config["build_backend"]["name"] = "pigen"  # a configuration that skipped the loader
    with pytest.raises(build_backends.BackendError):
        build_backends.plan_backend(config, {})
    nspawn = tmp_path / "n.json"
    nspawn.write_text(json.dumps({"platform": {"name": "rk3588"}, "build_backend": {"name": "nspawn"}}), encoding="utf-8")
    assert build_backends.plan_backend(build_config.load_config(nspawn), {})["platform"]["platform"] == "rk3588"


def test_extra_packages_and_units_reach_the_pigen_stage_for_cm5() -> None:
    config = config_for(extra_packages=["htop", "tmux"], extra_units=["ssh.service"])
    files = build_backends.pigen_stage_files({"HYDRA-UMC-OS": COMMIT}, config)
    assert files["stage-hydra/01-platform/00-packages"] == "htop\ntmux\n"
    assert files["stage-hydra/02-platform-units/00-run.sh"] == "#!/bin/bash -e\non_chroot systemctl enable ssh.service\n"
    config = config_for(extra_units=["ssh.service"])
    config["platform"]["extra_units"] = ["ssh.service"]
    only_units = build_backends.pigen_stage_files({}, config)
    assert "stage-hydra/01-platform/00-packages" not in only_units and "stage-hydra/02-platform-units/00-run.sh" in only_units


def test_a_disabled_unit_is_written_as_disable(monkeypatch: pytest.MonkeyPatch) -> None:
    table = json.loads(json.dumps(platforms.PLATFORMS))
    table["cm5"]["units"] = [{"name": "ssh.service", "enable": False}]
    table["cm5"]["remove_packages"] = ["triggerhappy"]
    monkeypatch.setattr(platforms, "PLATFORMS", table)
    files = build_backends.pigen_stage_files({}, build_config.load_config())
    assert "systemctl disable ssh.service" in files["stage-hydra/02-platform-units/00-run.sh"]
    assert "stage-hydra/01-platform/00-packages" in files
    assert platforms.platform_plan(build_config.load_config())["commands"][0] == ["apt-get", "remove", "-y", "triggerhappy"]


def test_the_plan_of_each_platform_names_its_commands_and_runs_nothing() -> None:
    plan = build_backends.plan_backend(config_for(name="jetson"), {})
    assert plan["runs_anything"] is False and plan["platform"]["commands"] == [
        ["apt-get", "install", "-y", "--no-install-recommends", "nvidia-jetpack"], ["systemctl", "enable", "nvpmodel.service"],
    ]
    assert plan["platform"]["base_image"]["kind"] == "nvidia-l4t-rootfs"
    generic = build_backends.plan_backend(config_for(name="rk3588"), {})["platform"]
    assert generic["generic"] is True and generic["evidence"] == "simulator"


def test_the_command_plans_for_a_platform(capsys: pytest.CaptureFixture[str]) -> None:
    assert main_module.main(["--cli", "build-plan"]) == 0
    assert json.loads(capsys.readouterr().out)["platform"]["platform"] == "cm5"
    assert main_module.main(["--cli", "build-plan", "--platform", "jetson"]) == 0
    assert json.loads(capsys.readouterr().out)["platform"]["platform"] == "jetson"
    assert main_module.main(["--cli", "build-plan", "--platform", "rk3588"]) == 0
    assert json.loads(capsys.readouterr().out)["platform"]["generic"] is True


def test_the_command_refuses_a_platform_the_chosen_backend_cannot_build(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    file = tmp_path / "c.json"
    file.write_text(json.dumps({"build_backend": {"name": "pigen"}}), encoding="utf-8")
    assert main_module.main(["--cli", "build-plan", "--config", str(file), "--platform", "jetson"]) == 1
    assert "BUILD_PLAN_FAILED" in capsys.readouterr().err


# ---- build-image chooses the base image by platform ----------------------------------------------------------------------------------------------------

def _build(monkeypatch, capsys, *argv: str):
    from hydra_umc_os_rebuilder import image_builder

    calls: list[dict] = []

    def fake_build(**kwargs):
        calls.append(kwargs)
        return image_builder.BuildResult(ok=True, output_path=kwargs["output_path"], installed=())

    monkeypatch.setattr(image_builder, "check_build_platform", lambda: image_builder.PlatformCheck(True, ""))
    monkeypatch.setattr(image_builder, "build_image", fake_build)
    from hydra_umc_os_rebuilder.ecosystem_plan import EcosystemPlan

    monkeypatch.setattr(main_module, "fetch_ecosystem_plan", lambda owner: EcosystemPlan(entries=(), discovery_errors=()))
    code = main_module.main(["--cli", "build-image", "--out", "x.img", *argv])
    return code, calls, capsys.readouterr()


def test_build_image_for_cm5_keeps_the_known_raspberry_pi_image_and_adds_no_command(monkeypatch, capsys) -> None:
    from hydra_umc_os_rebuilder import image_builder

    code, calls, _ = _build(monkeypatch, capsys)
    assert code == 0 and calls[0]["source"] == image_builder.KNOWN_BASE_IMAGES[0] and calls[0]["platform_commands"] == ()


def test_build_image_for_another_platform_needs_the_base_image_and_its_checksum(monkeypatch, capsys) -> None:
    digest = "ab" * 32
    code, calls, out = _build(monkeypatch, capsys, "--platform", "jetson")
    assert code == 1 and not calls and "--base-image-url and --base-image-sha256" in out.err
    for bad in ("zz" * 32, "ab" * 31, digest.upper()):
        code, calls, out = _build(monkeypatch, capsys, "--platform", "jetson", "--base-image-url", "https://example.invalid/rootfs.img", "--base-image-sha256", bad)
        assert code == 1 and not calls
    code, calls, out = _build(monkeypatch, capsys, "--platform", "jetson", "--base-image-url", "https://example.invalid/rootfs.img", "--base-image-sha256", digest)
    assert code == 0
    source = calls[0]["source"]
    assert (source.url, source.sha256, source.label) == ("https://example.invalid/rootfs.img", digest, platforms.PLATFORMS["jetson"]["label"])
    assert calls[0]["platform_commands"] == (("apt-get", "install", "-y", "--no-install-recommends", "nvidia-jetpack"), ("systemctl", "enable", "nvpmodel.service"))


def test_build_image_uses_the_platform_of_the_configuration_and_refuses_an_impossible_one(monkeypatch, capsys, tmp_path: Path) -> None:
    file = tmp_path / "c.json"
    file.write_text(json.dumps({"platform": {"name": "rk3588"}}), encoding="utf-8")
    code, calls, _ = _build(monkeypatch, capsys, "--config", str(file), "--base-image-url", "https://example.invalid/d.img", "--base-image-sha256", "cd" * 32)
    assert code == 0 and calls[0]["platform_commands"][0][:3] == ("apt-get", "install", "-y")
    code, calls, out = _build(monkeypatch, capsys, "--config", str(tmp_path / "missing.json"))
    assert code == 1 and "BUILD_BLOCKED" in out.err


def test_the_cm5_platform_with_extra_packages_runs_them_on_the_known_image(monkeypatch, capsys, tmp_path: Path) -> None:
    from hydra_umc_os_rebuilder import image_builder

    file = tmp_path / "c.json"
    file.write_text(json.dumps({"platform": {"extra_packages": ["htop"]}}), encoding="utf-8")
    code, calls, _ = _build(monkeypatch, capsys, "--config", str(file))
    assert code == 0 and calls[0]["source"] == image_builder.KNOWN_BASE_IMAGES[0] and calls[0]["platform_commands"] == (("apt-get", "install", "-y", "--no-install-recommends", "htop"),)
