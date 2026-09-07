# First-Boot Configuration

This tool's "First-Boot Config" screen (and `--cli config`) reproduces the
real mechanism Raspberry Pi Imager itself uses for its own "OS
Customisation" dialog on a Raspberry Pi OS (Bookworm and later) image:

1. A `firstrun.sh` shell script is written onto the image's **boot**
   partition.
2. `cmdline.txt` gets ` systemd.run=/boot/firmware/firstrun.sh
   systemd.run_success_action=reboot
   systemd.unit=kernel-command-line.target` appended - a real, native
   systemd kernel-command-line directive that runs the script exactly once,
   before the normal boot targets start.
3. `firstrun.sh` itself only ever calls `raspi-config nonint <subcommand>`
   for hostname/locale/keyboard/timezone/SSH/Wi-Fi - the same stable,
   public, non-interactive interface `raspi-config` has offered for years,
   rather than hand-writing a `wpa_supplicant.conf` or a NetworkManager
   keyfile directly. Reproducing `raspi-config`'s own real behavior is more
   honest than a parallel implementation that could silently drift from
   what a real device actually does on boot.
4. The user account is handled the same way `userconf-pi` (Raspberry Pi
   Imager's own helper package, present on official images) does: the
   image's own pre-existing first user (uid 1000) is renamed and given a
   real `SHA-512-crypt` password hash (`chpasswd -e`, or `userconf-pi`'s own
   helper when present) - the plaintext password this tool asks for is
   never written anywhere; only its hash is.
5. The script deletes itself and cleans `cmdline.txt` back up before
   the real boot continues, so a normal reboot afterward never re-runs it.

## Why `raspi-config nonint`, not a hand-rolled config

An earlier, more common approach (still valid on Raspberry Pi OS Bullseye
and older) drops a raw `wpa_supplicant.conf` plus a `userconf.txt`
(`user:hashed-password`) onto the boot partition directly, read by an
older `firstboot` systemd service baked into that image. This tool targets
current (Bookworm+) Raspberry Pi OS, whose default network stack is
NetworkManager, not `wpa_supplicant` directly - `raspi-config nonint
do_wifi_ssid_passphrase` already knows how to configure whichever backend
the target image actually uses, so this tool never needs to special-case
that itself.

## Password hashing

`firstboot_config.hash_password()` uses
[`passlib`](https://passlib.readthedocs.io/)'s `sha512_crypt` (rounds=5000,
glibc's own default) to produce the exact `$6$...` format `chpasswd -e`
expects. This is deliberately **not** Python's stdlib `crypt` module:
`crypt` only ever wraps the *host's own* `libc` call, so it is Unix-only
(this tool also runs on Windows) and was removed outright in Python 3.13.
`passlib` produces the byte-identical real format on every platform this
tool runs on.

## What this tool does NOT do

- It never invents a Wi-Fi country code, timezone, or keyboard layout -
  every field is exactly what the operator typed, passed straight through.
- It never silently skips a validation failure - an invalid hostname,
  username, or missing password for a requested user raises a real,
  specific `FirstBootConfigError` instead of writing a broken script.
- SSH key injection (`--ssh-key`) only *adds* an `authorized_keys` entry;
  it never disables password authentication on its own.
