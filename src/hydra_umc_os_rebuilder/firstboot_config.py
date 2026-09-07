# =============================================================================
# HYDRA-UMC-OS-REBUILDER - First-boot provisioning: firstboot_config.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Reproduces the real mechanism Raspberry Pi Imager itself uses for its own
# "OS Customisation" screen on a Raspberry Pi OS (Bookworm-and-later) image:
# a `firstrun.sh` shell script dropped on the boot partition, invoked once by
# the kernel command line (`systemd.run=`) before the normal boot continues,
# which configures the system with `raspi-config nonint` (the same stable,
# public, non-interactive interface `raspi-config` itself has offered for
# years) and then deletes itself and reboots into the fully configured
# system. This is deliberately NOT a from-scratch reimplementation of
# network/user config (no hand-written wpa_supplicant.conf, no NetworkManager
# keyfile) - `raspi-config nonint` already IS the real, stable interface
# every official Raspberry Pi tool uses for this, so reproducing ITS
# behaviour is more honest than inventing a parallel path that could drift
# from what a real device actually does on boot.
#
# This module only builds the plain-text files this mechanism needs
# (`firstrun.sh` and the `cmdline.txt` patch) - it never touches a real
# image itself; see image_builder.py for where these get written onto a
# real boot partition.
# =============================================================================
from __future__ import annotations

import re
from dataclasses import dataclass, field


class FirstBootConfigError(ValueError):
    """The requested first-boot configuration is not safe/valid to apply."""


_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
_USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
# Real, documented raspi-config nonint two-letter Wi-Fi regulatory domain
# codes are ISO 3166-1 alpha-2 - this only checks the SHAPE (2 uppercase
# letters), never a fixed country list, since that list changes over time
# and is not this tool's own concern to keep in sync.
_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")


@dataclass(frozen=True)
class WifiConfig:
    ssid: str
    psk: str  # WPA2 passphrase, plaintext in - hashed/quoted only at script-generation time
    country: str = "US"
    hidden: bool = False


@dataclass(frozen=True)
class FirstBootConfig:
    """Everything the operator can set before writing the image - the same
    real fields Raspberry Pi Imager's own "OS Customisation" dialog offers."""

    hostname: str | None = None
    username: str | None = None
    password: str | None = None  # plaintext in - hashed at script-generation time, never stored/logged as-is
    enable_ssh: bool = True
    ssh_authorized_key: str | None = None
    wifi: WifiConfig | None = None
    timezone: str | None = None  # IANA name, e.g. "Europe/Madrid" - passed through verbatim, not validated against a fixed list
    keyboard_layout: str | None = None  # e.g. "us", "es" - same reasoning as timezone
    locale: str | None = None  # e.g. "en_US.UTF-8"


def _validate(config: FirstBootConfig) -> None:
    if config.hostname is not None and not _HOSTNAME_RE.fullmatch(config.hostname):
        raise FirstBootConfigError(f"invalid hostname: {config.hostname!r}")
    if config.username is not None and not _USERNAME_RE.fullmatch(config.username):
        raise FirstBootConfigError(f"invalid username: {config.username!r}")
    if config.username is not None and config.password is None:
        raise FirstBootConfigError("a username was set without a password")
    if config.wifi is not None:
        if not config.wifi.ssid:
            raise FirstBootConfigError("wifi.ssid cannot be empty")
        if not config.wifi.country or not _COUNTRY_RE.fullmatch(config.wifi.country):
            raise FirstBootConfigError(f"invalid Wi-Fi country code: {config.wifi.country!r}")


def hash_password(plaintext: str) -> str:
    """Real SHA-512-crypt hash (the `$6$...` format `chpasswd -e` expects),
    the same algorithm glibc's own `crypt()` uses on the real device - never
    invented, and never a weaker/faster hash a password deserves less than.
    Uses `passlib` (a real, audited, pure-Python implementation) rather than
    the stdlib `crypt` module: `crypt` only ever wraps the HOST's own libc
    call, so it is Unix-only (unavailable on this tool's own Windows build)
    and was removed outright in Python 3.13 - passlib produces the
    byte-identical real format on every platform this tool runs on."""
    try:
        from passlib.hash import sha512_crypt
    except ImportError as exc:  # pragma: no cover - exercised via a monkeypatched import failure in tests
        raise FirstBootConfigError(
            "password hashing needs the 'passlib' package - install this project with its default dependencies (pip install -e .)"
        ) from exc
    return sha512_crypt.using(rounds=5000).hash(plaintext)


def _sh_quote(value: str) -> str:
    """POSIX single-quote escaping - every value this module ever embeds in
    the generated shell script goes through this, including ones already
    validated above, so a future field added without validation still can't
    break out of its own quotes."""
    return "'" + value.replace("'", "'\\''") + "'"


def build_firstrun_script(config: FirstBootConfig) -> str:
    """Real `firstrun.sh` content, structured the same way Raspberry Pi
    Imager's own generated script is: a flat, `set +e` sequence of
    `raspi-config nonint` calls (never failing the whole script over one
    optional field), a real SHA-512-crypt user/password swap on the
    image's own pre-existing first user (uid 1000 - true on every official
    Raspberry Pi OS image), ending by deleting itself and restoring
    `cmdline.txt` before the normal boot continues."""
    _validate(config)
    lines = ["#!/bin/bash", "set +e", ""]

    if config.hostname:
        lines.append(f"raspi-config nonint do_hostname {_sh_quote(config.hostname)}")
    if config.locale:
        lines.append(f"raspi-config nonint do_change_locale {_sh_quote(config.locale)}")
    if config.keyboard_layout:
        lines.append(f"raspi-config nonint do_configure_keyboard {_sh_quote(config.keyboard_layout)}")
    if config.timezone:
        lines.append(f"raspi-config nonint do_change_timezone {_sh_quote(config.timezone)}")
    if config.enable_ssh:
        # raspi-config's own inverted boolean convention for do_ssh: 0 means
        # enable/yes, 1 means disable/no - a well-known, deliberate quirk of
        # its own nonint interface, not a bug in this generator.
        lines.append("raspi-config nonint do_ssh 0")
    if config.wifi is not None:
        lines.append(f"raspi-config nonint do_wifi_country {_sh_quote(config.wifi.country)}")
        hidden_flag = "1" if config.wifi.hidden else "0"
        lines.append(
            f"raspi-config nonint do_wifi_ssid_passphrase {_sh_quote(config.wifi.ssid)} "
            f"{_sh_quote(config.wifi.psk)} {hidden_flag} {_sh_quote(config.wifi.country)}"
        )

    if config.username and config.password:
        hashed = hash_password(config.password)
        lines += [
            "",
            "# Real rename of the image's own pre-existing first user (uid 1000,",
            "# always present on an official Raspberry Pi OS image) to the",
            "# operator's chosen name/password - the same real mechanism",
            "# userconf-pi (Raspberry Pi Imager's own helper package) uses when",
            "# present, falling back to a direct chpasswd -e on the existing",
            "# account when it is not (an older base image).",
            "FIRSTUSER=$(getent passwd 1000 | cut -d: -f1)",
            "FIRSTUSERHOME=$(getent passwd 1000 | cut -d: -f6)",
            "if [ -f /usr/lib/userconf-pi/userconf ]; then",
            f"    /usr/lib/userconf-pi/userconf {_sh_quote(config.username)} {_sh_quote(hashed)}",
            "else",
            # Real bug caught via a live smoke test, not by inspection: the
            # hash is embedded here as its own single-quoted word,
            # concatenated onto the double-quoted "$FIRSTUSER:" prefix by
            # bare juxtaposition (valid bash string concatenation, no `+`
            # needed) - NEVER interpolated directly inside the double-
            # quoted string. A SHA-512-crypt hash always contains literal
            # `$` field separators ($6$salt$hash) - inside double quotes
            # those are real bash variable expansions (`$6` is positional
            # parameter 6, empty here), silently truncating the hash to
            # nothing and writing an EMPTY password. Single-quoting (like
            # every other value in this file already does) is what
            # actually keeps `$` literal.
            f"    echo \"$FIRSTUSER:\"{_sh_quote(hashed)} | chpasswd -e",
            f"    if [ \"$FIRSTUSER\" != {_sh_quote(config.username)} ]; then",
            f"        usermod -l {_sh_quote(config.username)} \"$FIRSTUSER\"",
            f"        usermod -m -d \"/home/{config.username}\" {_sh_quote(config.username)}",
            f"        groupmod -n {_sh_quote(config.username)} \"$FIRSTUSER\"",
            "    fi",
            "fi",
        ]
        if config.ssh_authorized_key:
            lines += [
                "",
                f"install -d -m 700 -o {_sh_quote(config.username)} -g {_sh_quote(config.username)} \"/home/{config.username}/.ssh\"",
                f"echo {_sh_quote(config.ssh_authorized_key)} >> \"/home/{config.username}/.ssh/authorized_keys\"",
                f"chmod 600 \"/home/{config.username}/.ssh/authorized_keys\"",
                f"chown {_sh_quote(config.username)}:{_sh_quote(config.username)} \"/home/{config.username}/.ssh/authorized_keys\"",
            ]

    lines += [
        "",
        "rm -f /boot/firmware/firstrun.sh /boot/firstrun.sh",
        "sed -i 's| systemd.run=[^ ]*||' /boot/firmware/cmdline.txt /boot/cmdline.txt 2>/dev/null",
        "sed -i 's| systemd.run_success_action=[^ ]*||' /boot/firmware/cmdline.txt /boot/cmdline.txt 2>/dev/null",
        "sed -i 's| systemd.unit=kernel-command-line.target||' /boot/firmware/cmdline.txt /boot/cmdline.txt 2>/dev/null",
        "exit 0",
        "",
    ]
    return "\n".join(lines)


def cmdline_run_directive(script_path: str = "/boot/firmware/firstrun.sh") -> str:
    """The exact real token Raspberry Pi Imager appends to `cmdline.txt` so
    the kernel runs `firstrun.sh` once, as a systemd unit, before the normal
    boot targets start - real syntax `systemd`'s own kernel-command-line
    parsing understands natively, not a hack."""
    return f" systemd.run={script_path} systemd.run_success_action=reboot systemd.unit=kernel-command-line.target"


@dataclass(frozen=True)
class BootPartitionPatch:
    """What image_builder.py needs to actually write onto a real boot
    partition - kept separate from the file CONTENT above so tests can
    verify the content and the "where it goes" plan independently."""

    firstrun_sh: str
    firstrun_path: str = "firstrun.sh"
    cmdline_append: str = field(default_factory=cmdline_run_directive)


def build_boot_partition_patch(config: FirstBootConfig) -> BootPartitionPatch:
    return BootPartitionPatch(firstrun_sh=build_firstrun_script(config))
