# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_ssh_hostkeys.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Trust on first use with a pinned fingerprint, and no default Wi-Fi country."""
import base64
import hashlib

import pytest

from hydra_umc_os_rebuilder.firstboot_config import FirstBootConfig, FirstBootConfigError, WifiConfig, _validate
from hydra_umc_os_rebuilder.ssh_hostkeys import (
    HostKeyError,
    HostKeyStore,
    decide,
    fingerprint_sha256,
    normalize_fingerprint,
)

KEY_A = b"\x00\x00\x00\x0bssh-ed25519" + b"A" * 36
KEY_B = b"\x00\x00\x00\x0bssh-ed25519" + b"B" * 36


def test_the_fingerprint_is_the_openssh_sha256_form():
    expected = "SHA256:" + base64.b64encode(hashlib.sha256(KEY_A).digest()).decode().rstrip("=")
    assert fingerprint_sha256(KEY_A) == expected
    assert "=" not in expected


def test_normalize_accepts_the_prefix_or_not_and_padding():
    fingerprint = fingerprint_sha256(KEY_A)
    assert normalize_fingerprint(fingerprint) == fingerprint
    assert normalize_fingerprint(fingerprint[len("SHA256:"):]) == fingerprint
    assert normalize_fingerprint(" " + fingerprint + "= ") == fingerprint
    assert normalize_fingerprint("  ") == ""


def test_an_unknown_host_is_refused_and_the_message_shows_the_fingerprint(tmp_path):
    store = HostKeyStore(tmp_path / "known.json")
    with pytest.raises(HostKeyError) as raised:
        decide(store, "cm5.local", 22, "ssh-ed25519", KEY_A)
    assert fingerprint_sha256(KEY_A) in str(raised.value)
    assert store.pinned("cm5.local", 22) is None  # nothing is pinned by a refusal


def test_the_entered_fingerprint_pins_the_key_on_first_use(tmp_path):
    store = HostKeyStore(tmp_path / "known.json")
    fingerprint = fingerprint_sha256(KEY_A)
    assert decide(store, "cm5.local", 22, "ssh-ed25519", KEY_A, fingerprint) == fingerprint
    assert store.pinned("cm5.local", 22) == fingerprint
    # once pinned, no fingerprint has to be entered again
    assert decide(store, "CM5.local", 22, "ssh-ed25519", KEY_A) == fingerprint


def test_a_wrong_entered_fingerprint_pins_nothing(tmp_path):
    store = HostKeyStore(tmp_path / "known.json")
    with pytest.raises(HostKeyError, match="not the"):
        decide(store, "cm5.local", 22, "ssh-ed25519", KEY_A, fingerprint_sha256(KEY_B))
    assert store.pinned("cm5.local", 22) is None


def test_a_changed_key_is_always_refused_even_with_its_new_fingerprint_entered(tmp_path):
    store = HostKeyStore(tmp_path / "known.json")
    decide(store, "cm5.local", 22, "ssh-ed25519", KEY_A, fingerprint_sha256(KEY_A))
    with pytest.raises(HostKeyError, match="CHANGED"):
        decide(store, "cm5.local", 22, "ssh-ed25519", KEY_B)
    with pytest.raises(HostKeyError, match="CHANGED"):
        decide(store, "cm5.local", 22, "ssh-ed25519", KEY_B, fingerprint_sha256(KEY_B))
    assert store.pinned("cm5.local", 22) == fingerprint_sha256(KEY_A)


def test_the_port_is_part_of_the_identity(tmp_path):
    store = HostKeyStore(tmp_path / "known.json")
    decide(store, "cm5.local", 22, "ssh-ed25519", KEY_A, fingerprint_sha256(KEY_A))
    with pytest.raises(HostKeyError, match="first connection"):
        decide(store, "cm5.local", 2222, "ssh-ed25519", KEY_A)


def test_a_damaged_store_trusts_nothing(tmp_path):
    path = tmp_path / "known.json"
    path.write_text("not json", encoding="utf-8")
    store = HostKeyStore(path)
    assert store.pinned("cm5.local", 22) is None
    path.write_text('["a list"]', encoding="utf-8")
    assert store.pinned("cm5.local", 22) is None


def test_there_is_no_default_wifi_country():
    assert WifiConfig(ssid="lab", psk="12345678").country == ""
    config = FirstBootConfig(wifi=WifiConfig(ssid="lab", psk="12345678"))
    with pytest.raises(FirstBootConfigError, match="required"):
        _validate(config)
    _validate(FirstBootConfig(wifi=WifiConfig(ssid="lab", psk="12345678", country="ES")))
    with pytest.raises(FirstBootConfigError, match="invalid"):
        _validate(FirstBootConfig(wifi=WifiConfig(ssid="lab", psk="12345678", country="spain")))
