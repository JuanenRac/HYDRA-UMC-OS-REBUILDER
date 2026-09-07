# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tests/test_firstboot_config.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import pytest

from hydra_umc_os_rebuilder.firstboot_config import (
    FirstBootConfig,
    FirstBootConfigError,
    WifiConfig,
    build_firstrun_script,
    cmdline_run_directive,
    hash_password,
)


def test_empty_config_produces_a_minimal_valid_script() -> None:
    script = build_firstrun_script(FirstBootConfig())
    assert script.startswith("#!/bin/bash")
    assert "set +e" in script
    # SSH is enabled by default.
    assert "raspi-config nonint do_ssh 0" in script
    assert script.rstrip().endswith("exit 0")


def test_no_ssh_flag_omits_the_do_ssh_call() -> None:
    script = build_firstrun_script(FirstBootConfig(enable_ssh=False))
    assert "do_ssh" not in script


def test_hostname_is_passed_through_quoted() -> None:
    script = build_firstrun_script(FirstBootConfig(hostname="hydra-umc-cm5"))
    assert "raspi-config nonint do_hostname 'hydra-umc-cm5'" in script


def test_invalid_hostname_is_rejected() -> None:
    with pytest.raises(FirstBootConfigError):
        build_firstrun_script(FirstBootConfig(hostname="not a valid host!"))


def test_username_without_password_is_rejected() -> None:
    with pytest.raises(FirstBootConfigError):
        build_firstrun_script(FirstBootConfig(username="hydra_umc"))


def test_user_password_block_uses_a_real_sha512_crypt_hash() -> None:
    script = build_firstrun_script(FirstBootConfig(username="hydra_umc", password="correct horse battery staple"))
    assert "correct horse battery staple" not in script  # the plaintext must never appear
    assert "$6$" in script  # the real glibc SHA-512-crypt prefix
    assert "userconf-pi" in script
    assert "chpasswd -e" in script


def test_password_hash_is_never_embedded_inside_double_quotes() -> None:
    # Real bug caught via a live smoke test: a SHA-512-crypt hash always
    # contains literal `$6$salt$hash` - if that string is interpolated
    # directly inside a DOUBLE-quoted bash string, `$6` and the salt look
    # like real variable expansions (positional parameter 6, then unset
    # variables), silently truncating the hash to nothing and writing an
    # EMPTY password via `chpasswd -e`. The chpasswd fallback line must
    # carry the hash as its own single-quoted word.
    script = build_firstrun_script(FirstBootConfig(username="hydra-umc", password="x"))
    fallback_line = next(line for line in script.splitlines() if "| chpasswd -e" in line)
    assert '"$FIRSTUSER:"' in fallback_line, "the $FIRSTUSER prefix must stay in its own double-quoted word"
    # The hash itself must appear as a SEPARATE single-quoted word right
    # after that prefix, never inside the double-quoted part.
    assert '"$FIRSTUSER:$6$' not in fallback_line
    assert "'$6$" in fallback_line


def test_ssh_authorized_key_is_appended_when_username_and_password_given() -> None:
    script = build_firstrun_script(
        FirstBootConfig(username="hydra_umc", password="x", ssh_authorized_key="ssh-ed25519 AAAA... test@host")
    )
    assert "authorized_keys" in script
    assert "ssh-ed25519 AAAA... test@host" in script


def test_wifi_block_uses_raspi_config_nonint() -> None:
    script = build_firstrun_script(FirstBootConfig(wifi=WifiConfig(ssid="MyNet", psk="hunter22", country="ES")))
    assert "do_wifi_country 'ES'" in script
    assert "do_wifi_ssid_passphrase 'MyNet' 'hunter22' 0 'ES'" in script


def test_wifi_requires_a_valid_country_code() -> None:
    with pytest.raises(FirstBootConfigError):
        build_firstrun_script(FirstBootConfig(wifi=WifiConfig(ssid="MyNet", psk="x", country="ESP")))


def test_wifi_ssid_cannot_be_empty() -> None:
    with pytest.raises(FirstBootConfigError):
        build_firstrun_script(FirstBootConfig(wifi=WifiConfig(ssid="", psk="x")))


def test_shell_metacharacters_in_values_cannot_break_out_of_quotes() -> None:
    # A real, hostile SSID containing a single quote and a command
    # substitution attempt must stay inert - POSIX single-quote escaping
    # (_sh_quote) is the only thing standing between this and a real shell
    # injection in a script that runs as root on first boot.
    hostile_ssid = "x'; rm -rf / #"
    script = build_firstrun_script(FirstBootConfig(wifi=WifiConfig(ssid=hostile_ssid, psk="x", country="US")))
    # The hostile SSID must appear ONLY as a single properly-escaped shell
    # word (each embedded ' closed and reopened around a literal \') - a
    # real shell parses this whole run as one inert string argument, never
    # as a quote break-out followed by a second, executable command.
    assert "'x'\\''; rm -rf / #'" in script
    # And it must appear NOWHERE unescaped (a bare, unquoted "; rm -rf /"
    # would be the real injection this test exists to catch).
    assert "x'; rm -rf / #" not in script


def test_cmdline_run_directive_is_a_real_systemd_run_token() -> None:
    directive = cmdline_run_directive()
    assert directive.startswith(" systemd.run=")
    assert "systemd.run_success_action=reboot" in directive
    assert "systemd.unit=kernel-command-line.target" in directive


def test_hash_password_produces_a_real_verifiable_sha512_crypt_hash() -> None:
    passlib_hash = pytest.importorskip("passlib.hash")
    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith("$6$")
    assert passlib_hash.sha512_crypt.verify("correct horse battery staple", hashed)
    assert not passlib_hash.sha512_crypt.verify("wrong password", hashed)
