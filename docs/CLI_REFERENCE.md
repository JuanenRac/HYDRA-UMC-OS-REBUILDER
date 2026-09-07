# CLI Reference

`hydra-umc-os-rebuilder --cli <command>` runs headless - no display, no Qt
runtime required (the `gui` extra can stay uninstalled entirely for a
CLI-only checkout). Every command prints plain, greppable `KEY=value`
summary lines; nothing here is translated (see `i18n.py`'s own header for
why).

## `status`

Prints the real, current GitHub version of every `deployment_target: "cm5"`
project in the HYDRA-UMC/URTC ecosystem - never a fixed list, discovered the
same way `hydra-umc-updater` itself discovers the whole ecosystem (a real
GitHub repository scan, keeping only repositories whose own
`hydra-umc.project.json` opts into `ecosystem: "HYDRA-UMC"`).

```
hydra-umc-os-rebuilder --cli status
hydra-umc-os-rebuilder --cli --owner SomeoneElse status
```

Output:

```
HYDRA-UMC-SERVER 0.4.8 (api/node)
HYDRA-UMC-VISION-STREAMER 0.0.3 (service/python)
...
TOTAL=27
```

## `config`

Writes a real `firstrun.sh` (and a `cmdline-append.txt` sidecar with the
exact token that needs appending to the image's own `cmdline.txt`) into
`--out` - the same real mechanism Raspberry Pi Imager's own "OS
Customisation" screen uses on a Raspberry Pi OS (Bookworm+) image. See
[FIRST_BOOT_CONFIG.md](FIRST_BOOT_CONFIG.md) for exactly what this script
does and why.

```
hydra-umc-os-rebuilder --cli config --out ./boot \
  --hostname hydra-umc-cm5 \
  --username hydra_umc --password 'change-me' \
  --wifi-ssid MyNetwork --wifi-password 'wifi-pass' --wifi-country ES \
  --timezone Europe/Madrid --keyboard es
```

Only `--out` is required; every other field is optional and independently
skipped when absent (no hostname change, no user created, no Wi-Fi
configured, SSH enabled by default unless `--no-ssh` is given).

## `build-image`

Builds a complete, ready-to-flash `.img`: downloads the pinned base
Raspberry Pi OS release, loop-mounts it, installs/updates every discovered
CM5 project by running **that project's own `build.sh`** inside the image's
own chroot, and writes the output file.

```
hydra-umc-os-rebuilder --cli build-image --out hydra-umc-cm5.img --work-dir ./work
```

**This command only runs on Linux, as root, with `losetup`/`mount`/
`chroot`/`xz` available** - loop-mounting a raw image and chrooting into it
cannot be meaningfully emulated on Windows. Run it from a real Linux
machine, or WSL2 configured for real loop-device access. On any other
platform this command exits with `BUILD_BLOCKED reason=...` explaining
exactly what is missing, rather than silently doing nothing.
