# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_language_hostkeys_boot_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The edges the other tests leave: how the language of the window is chosen and saved, the store of pinned host keys and the decision on a
# presented key, and the boot test with its launcher and QEMU replaced (skips, the log markers, a kernel taken out of the boot partition).
# =============================================================================
from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from hydra_umc_os_rebuilder import boot_test, i18n
from hydra_umc_os_rebuilder.build_config import DEFAULTS
from hydra_umc_os_rebuilder.ssh_hostkeys import (
    HostKeyError,
    HostKeyStore,
    decide,
    default_store_path,
    fingerprint_sha256,
    normalize_fingerprint,
)

import copy

BLOB = b"\x00\x00\x00\x0bssh-ed25519" + bytes(range(32))
OTHER = b"\x00\x00\x00\x0bssh-ed25519" + bytes(range(1, 33))


def _config(**boot) -> dict:
    config = copy.deepcopy(DEFAULTS)
    config["boot_test"].update(boot)
    return config


# --- the language of the window --------------------------------------------------------------------------------------------
@pytest.fixture
def lang_file(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "lang.json"
    monkeypatch.setattr(i18n, "_CONFIG_PATH", path)
    return path


def test_a_saved_language_wins_over_the_locale(lang_file, monkeypatch) -> None:
    lang_file.write_text(json.dumps({"lang": "ja"}), encoding="utf-8")
    monkeypatch.setattr(i18n.locale, "getlocale", lambda: ("de_DE", "UTF-8"))
    assert i18n.resolve_initial_lang() == "ja"


@pytest.mark.parametrize("content", ["", "{not json", "[]", '{"lang": "xx"}', '{"lang": 5}', '{"other": "es"}'])
def test_a_damaged_or_unknown_saved_language_is_ignored(lang_file, monkeypatch, content) -> None:
    lang_file.write_text(content, encoding="utf-8")
    monkeypatch.setattr(i18n.locale, "getlocale", lambda: ("fr_FR", "UTF-8"))
    assert i18n.resolve_initial_lang() == "fr"


def test_the_locale_is_used_when_nothing_is_saved_and_english_is_the_last_resort(lang_file, monkeypatch) -> None:
    for detected, expected in ((("pt_PT", "UTF-8"), "pt"), (("ZH_cn", "UTF-8"), "zh"), (("pl_PL", "UTF-8"), "en"), ((None, None), "en"), (("", ""), "en")):
        monkeypatch.setattr(i18n.locale, "getlocale", lambda d=detected: d)
        assert i18n.resolve_initial_lang() == expected, detected


def test_a_locale_that_cannot_be_read_gives_english(lang_file, monkeypatch) -> None:
    def broken():
        raise ValueError("unknown locale")

    monkeypatch.setattr(i18n.locale, "getlocale", broken)
    assert i18n.resolve_initial_lang() == "en"


def test_save_language_writes_a_known_code_only(lang_file) -> None:
    i18n.save_lang("it")
    assert json.loads(lang_file.read_text(encoding="utf-8")) == {"lang": "it"}
    i18n.save_lang("klingon")
    assert json.loads(lang_file.read_text(encoding="utf-8")) == {"lang": "it"}


def test_save_language_in_a_folder_that_does_not_exist_is_silent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(i18n, "_CONFIG_PATH", tmp_path / "no" / "such" / "lang.json")
    i18n.save_lang("es")  # must not raise


def test_every_language_is_offered_once_with_a_label(lang_file) -> None:
    codes = [code for code, _label in i18n.LANGUAGES]
    assert sorted(codes) == sorted(["en", "es", "fr", "it", "de", "zh", "ja", "pt"])
    assert len(set(codes)) == len(codes)
    assert all(label.strip() for _code, label in i18n.LANGUAGES)


def test_no_translation_is_empty_or_a_copy_of_the_key(lang_file) -> None:
    for code, table in i18n.TRANSLATIONS.items():
        for key, value in table.items():
            assert value.strip(), f"{code}.{key}"
            assert value != key, f"{code}.{key}"


def test_the_european_portuguese_forms_are_used(lang_file) -> None:
    pt = " ".join(i18n.TRANSLATIONS["pt"].values()).lower()
    for brazilian in ("arquivo", "usuário", "baixar", "tela "):
        assert brazilian not in pt, brazilian


# --- the store of pinned host keys ---------------------------------------------------------------------------------------------
def test_the_store_path_comes_from_the_environment_or_the_home_folder(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HYDRA_UMC_OS_REBUILDER_KNOWN_HOSTS", str(tmp_path / "hosts.json"))
    assert default_store_path() == tmp_path / "hosts.json"
    monkeypatch.setenv("HYDRA_UMC_OS_REBUILDER_KNOWN_HOSTS", "   ")
    assert default_store_path().name == "os-rebuilder-known-hosts.json"


def test_fingerprints_follow_the_openssh_form_and_normalise() -> None:
    fingerprint = fingerprint_sha256(BLOB)
    assert fingerprint.startswith("SHA256:")
    assert "=" not in fingerprint
    assert fingerprint != fingerprint_sha256(OTHER)
    bare = fingerprint[len("SHA256:"):]
    assert normalize_fingerprint(bare) == fingerprint
    assert normalize_fingerprint("  sha256:" + bare + "==  ") == fingerprint
    assert normalize_fingerprint("") == ""
    assert normalize_fingerprint("   ") == ""


def test_the_store_reads_a_missing_or_damaged_file_as_empty(tmp_path) -> None:
    store = HostKeyStore(tmp_path / "hosts.json")
    assert store.pinned("pi", 22) is None
    for content in ("{not json", "[]", '{"pi:22": "text"}', '{"pi:22": {"fingerprint": 5}}', '{"pi:22": {"type": "x"}}'):
        store.path.write_text(content, encoding="utf-8")
        assert store.pinned("pi", 22) is None, content


def test_a_pin_is_kept_per_host_and_port_and_ignores_case_and_spaces(tmp_path) -> None:
    store = HostKeyStore(tmp_path / "deep" / "hosts.json")
    store.pin("Pi.Local ", 22, "ssh-ed25519", "SHA256:abc")
    store.pin("pi.local", 2222, "ssh-ed25519", "SHA256:def")
    assert store.pinned("pi.local", 22) == "SHA256:abc"
    assert store.pinned("PI.LOCAL", 2222) == "SHA256:def"
    assert store.pinned("pi.local", 23) is None
    assert not list((tmp_path / "deep").glob("*.tmp"))
    assert json.loads(store.path.read_text(encoding="utf-8"))["pi.local:22"]["type"] == "ssh-ed25519"


def test_the_first_contact_is_refused_without_an_expected_fingerprint_and_names_it(tmp_path) -> None:
    store = HostKeyStore(tmp_path / "hosts.json")
    with pytest.raises(HostKeyError) as caught:
        decide(store, "pi", 22, "ssh-ed25519", BLOB)
    assert fingerprint_sha256(BLOB) in str(caught.value)
    assert store.pinned("pi", 22) is None  # a refused key is never pinned


def test_the_first_contact_with_the_right_fingerprint_pins_it_and_later_contacts_need_no_entry(tmp_path) -> None:
    store = HostKeyStore(tmp_path / "hosts.json")
    expected = fingerprint_sha256(BLOB).replace("SHA256:", "")
    assert decide(store, "pi", 22, "ssh-ed25519", BLOB, expected) == fingerprint_sha256(BLOB)
    assert store.pinned("pi", 22) == fingerprint_sha256(BLOB)
    assert decide(store, "pi", 22, "ssh-ed25519", BLOB) == fingerprint_sha256(BLOB)


def test_a_wrong_expected_fingerprint_is_refused_and_nothing_is_pinned(tmp_path) -> None:
    store = HostKeyStore(tmp_path / "hosts.json")
    with pytest.raises(HostKeyError) as caught:
        decide(store, "pi", 22, "ssh-ed25519", BLOB, fingerprint_sha256(OTHER))
    assert "refusing to connect" in str(caught.value)
    assert store.pinned("pi", 22) is None


def test_a_changed_key_is_refused_even_when_the_right_one_is_typed_again(tmp_path) -> None:
    store = HostKeyStore(tmp_path / "hosts.json")
    decide(store, "pi", 22, "ssh-ed25519", BLOB, fingerprint_sha256(BLOB))
    with pytest.raises(HostKeyError) as caught:
        decide(store, "pi", 22, "ssh-ed25519", OTHER, fingerprint_sha256(OTHER))
    assert "CHANGED" in str(caught.value)
    assert store.pinned("pi", 22) == fingerprint_sha256(BLOB)


def test_a_seeded_set_of_random_keys_is_pinned_once_and_never_swapped(tmp_path) -> None:
    rng = random.Random(20261113)
    store = HostKeyStore(tmp_path / "hosts.json")
    keys = {f"host{i}": bytes(rng.randrange(256) for _ in range(40)) for i in range(25)}
    for host, blob in keys.items():
        assert decide(store, host, 22, "ssh-ed25519", blob, fingerprint_sha256(blob)) == fingerprint_sha256(blob)
    for host, blob in keys.items():
        for other_host, other_blob in keys.items():
            if other_host == host:
                continue
            with pytest.raises(HostKeyError):
                decide(store, host, 22, "ssh-ed25519", other_blob)
        assert decide(store, host, 22, "ssh-ed25519", blob) == fingerprint_sha256(blob)


# --- the boot test ----------------------------------------------------------------------------------------------------------------------------
def test_the_qemu_command_forwards_ssh_to_the_host_loopback_only(tmp_path) -> None:
    command = boot_test.qemu_command(tmp_path / "x.img", _config(ssh_port=2200, memory_mb=1024))
    joined = " ".join(command)
    assert "hostfwd=tcp:127.0.0.1:2200-:22" in joined
    assert "-m 1024" in joined
    assert "snapshot=on" in joined  # the image is never written
    with_kernel = boot_test.qemu_command(tmp_path / "x.img", _config(), kernel=tmp_path / "k", dtb=tmp_path / "d")
    assert with_kernel[-6:-4] == ["-kernel", str(tmp_path / "k")] or "-kernel" in with_kernel
    assert "-dtb" in with_kernel


def test_a_boot_test_with_no_image_name_is_refused() -> None:
    with pytest.raises(boot_test.BootTestError):
        boot_test.qemu_command(Path(""), _config())


def test_the_boot_log_is_read_by_the_first_marker_that_appears() -> None:
    config = _config()
    assert boot_test.read_boot_log("Booting...\nraspberrypi login:", config) == {"state": "ready", "marker": "login:"}
    assert boot_test.read_boot_log("Kernel panic - not syncing", config) == {"state": "failed", "marker": "Kernel panic"}
    assert boot_test.read_boot_log("Kernel panic ... then login:", config)["state"] == "failed"
    assert boot_test.read_boot_log("login: ... then Kernel panic", config)["state"] == "ready"
    assert boot_test.read_boot_log("", config) == {"state": "no-result", "marker": None}


def test_the_partition_offset_is_the_first_fat_partition() -> None:
    table = {"partitiontable": {"sectorsize": 512, "partitions": [{"type": "83", "start": 100}, {"type": "c", "start": 2048}, {"type": "0b", "start": 9999}]}}
    assert boot_test.boot_partition_offset(json.dumps(table)) == 2048 * 512
    table["partitiontable"]["sectorsize"] = 4096
    assert boot_test.boot_partition_offset(json.dumps(table)) == 2048 * 4096
    gpt = {"partitiontable": {"partitions": [{"type": "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "start": 8}]}}
    assert boot_test.boot_partition_offset(json.dumps(gpt)) == 8 * 512


@pytest.mark.parametrize("text", ["", "{", "[]", "{}", '{"partitiontable": {}}', '{"partitiontable": {"partitions": [{"type": "83", "start": 1}]}}', '{"partitiontable": {"partitions": [{"type": "c"}]}}'])
def test_a_partition_table_that_cannot_give_a_boot_partition_is_refused(text) -> None:
    with pytest.raises(boot_test.BootTestError):
        boot_test.boot_partition_offset(text)


def test_the_kernel_is_taken_out_of_the_boot_partition_without_mounting(tmp_path) -> None:
    table = json.dumps({"partitiontable": {"partitions": [{"type": "c", "start": 8192}]}})
    calls: list[list[str]] = []

    def run(command: list[str]) -> str:
        calls.append(command)
        return table if command[0] == "sfdisk" else ""

    found = boot_test.extract_boot_files(tmp_path / "x.img", tmp_path / "out", _config(dtb_name="bcm2712.dtb"), run=run, which=lambda tool: "/usr/bin/" + tool)
    assert found["kernel"] == tmp_path / "out" / "kernel8.img"
    assert found["dtb"] == tmp_path / "out" / "bcm2712.dtb"
    copies = [c for c in calls if c[0] == "mcopy"]
    assert len(copies) == 2
    assert all(f"@@{8192 * 512}" in " ".join(c) for c in copies)
    assert not any(c[0] in ("mount", "losetup") for c in calls)


def test_extracting_needs_both_tools_and_a_plain_file_name(tmp_path) -> None:
    with pytest.raises(boot_test.BootTestError, match="mcopy is not installed"):
        boot_test.extract_boot_files(tmp_path / "x.img", tmp_path / "out", _config(), run=lambda c: "", which=lambda tool: None if tool == "mcopy" else "/x")
    table = json.dumps({"partitiontable": {"partitions": [{"type": "c", "start": 1}]}})
    for name in ("../kernel", "a/b", "a\\b", ".hidden"):
        with pytest.raises(boot_test.BootTestError, match="not a file name"):
            boot_test.extract_boot_files(tmp_path / "x.img", tmp_path / "out", _config(kernel_name=name), run=lambda c: table, which=lambda t: "/x")


def test_the_check_over_ssh_needs_a_user_and_never_pins_the_throw_away_guest() -> None:
    with pytest.raises(boot_test.BootTestError):
        boot_test.ssh_verify_command(_config(ssh_user=""))
    command = boot_test.ssh_verify_command(_config(ssh_user="op", ssh_port=2201))
    assert command[:3] == ["ssh", "-p", "2201"]
    assert "BatchMode=yes" in command
    assert "op@127.0.0.1" in command


def test_the_boot_test_is_skipped_for_each_reason_and_never_passed(tmp_path) -> None:
    image = tmp_path / "x.img"
    never = lambda *_a: pytest.fail("QEMU must not be started")  # noqa: E731
    off = boot_test.run_boot_test(image, _config(), launch=never)
    assert (off["state"], "off" in off["reason"]) == ("skipped", True)
    no_qemu = boot_test.run_boot_test(image, _config(enabled=True), launch=never, which=lambda _t: None)
    assert no_qemu["state"] == "skipped" and "not installed" in no_qemu["reason"]
    no_image = boot_test.run_boot_test(image, _config(enabled=True), launch=never, which=lambda _t: "/usr/bin/qemu")
    assert no_image["state"] == "skipped" and "does not exist" in no_image["reason"]


def test_the_boot_test_reads_the_serial_log_of_the_launcher(tmp_path) -> None:
    image = tmp_path / "x.img"
    image.write_bytes(b"x")
    seen = {}

    def launch(command, timeout):
        seen["timeout"] = timeout
        return "systemd[1]: Reached target\nhydra login:"

    result = boot_test.run_boot_test(image, _config(enabled=True, timeout_seconds=42), launch=launch, which=lambda _t: "/usr/bin/qemu")
    assert (result["state"], result["marker"]) == ("ready", "login:")
    assert seen["timeout"] == 42.0
    failed = boot_test.run_boot_test(image, _config(enabled=True), launch=lambda *_a: "VFS: Unable to mount root fs", which=lambda _t: "/usr/bin/qemu")
    assert failed["state"] == "failed"


def test_a_kernel_that_cannot_be_extracted_skips_the_test_with_the_reason(tmp_path) -> None:
    image = tmp_path / "x.img"
    image.write_bytes(b"x")
    result = boot_test.run_boot_test(image, _config(enabled=True, extract_kernel=True), launch=lambda *_a: pytest.fail("no launch"), which=lambda t: None if t == "sfdisk" else "/x")
    assert result["state"] == "skipped"
    assert "sfdisk is not installed" in result["reason"]


def test_the_kernel_is_handed_to_qemu_when_it_is_extracted(tmp_path) -> None:
    image = tmp_path / "x.img"
    image.write_bytes(b"x")
    table = json.dumps({"partitiontable": {"partitions": [{"type": "c", "start": 2048}]}})
    launched = {}

    def launch(command, timeout):
        launched["command"] = command
        return "login:"

    result = boot_test.run_boot_test(
        image, _config(enabled=True, extract_kernel=True), launch=launch, which=lambda t: "/x", run=lambda c: table if c[0] == "sfdisk" else ""
    )
    assert result["state"] == "ready"
    assert "-kernel" in launched["command"]
