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

**Recovery-procedure guard:** `--no-ssh` without `--username` is refused
(`FirstBootConfigError`) - on this tool's own official base images (no
default user on Bookworm and later) that combination leaves the unit
with no login path at all, remote or physical. Pass
`--acknowledge-no-remote-access` to opt in when another way in is
certain. A `--ssh-key` given without both `--username` and `--password`
is refused outright (no acknowledgment override) - it would otherwise be
silently dropped from the generated script, since `firstboot_config.py`
only ever installs a key for the account it is itself creating.

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

Accepts the same optional `--hostname`/`--username`/`--password`/
`--no-ssh`/`--acknowledge-no-remote-access`/`--ssh-key`/`--wifi-*`/
`--timezone`/`--keyboard`/`--locale` flags as `config` above, threaded
straight into the real build.

## `profile-freeze` / `profile-diff` / `profile-update` / `profile-set-required-resources` / `profile-build`

D05 ("versions and compatibility across the set"): `status` above always
answers "what is current on GitHub right now" - a live, moving target.
These five commands let a candidate combination be pinned, inspected,
curated and built from without ever silently picking up whatever
"latest" has become since it was frozen.

```
# Pin the current live ecosystem plan into a named, persisted manifest
hydra-umc-os-rebuilder --cli profile-freeze --name cm5-production --out profiles/cm5-production.json

# Compare a previously frozen profile against the current live ecosystem,
# per project - never a single pass/fail boolean
hydra-umc-os-rebuilder --cli profile-diff --manifest profiles/cm5-production.json

# Refreeze ONLY the named project(s) - every other one stays pinned
# exactly as it was tested before, even if it also changed upstream
hydra-umc-os-rebuilder --cli profile-update --manifest profiles/cm5-production.json --project HYDRA-UMC-SERVER

# I12: curate the real inventory of resources (relative paths inside a
# project's own installed tree) profile-build refuses to promote an
# image without - repeatable --resource, edits the manifest in place
hydra-umc-os-rebuilder --cli profile-set-required-resources --manifest profiles/cm5-production.json --project HYDRA-UMC-STUDIO --resource dist/index.html

# Build a real .img from EXACTLY the frozen manifest's own commit SHAs -
# never re-resolves "latest" mid-build. Same real Linux/root/tool
# requirements as build-image above; folds real post-build content
# hashes back into the manifest on disk once it succeeds. Refuses to
# install (and therefore never promotes the image) if any project with
# curated required_resources is missing one of them after its own
# build.sh ran.
hydra-umc-os-rebuilder --cli profile-build --manifest profiles/cm5-production.json --out hydra-umc-cm5.img
```

`profile-diff`'s findings are per-project and typed (`UPDATED`,
`ROLE_CHANGED`, `STACK_CHANGED`, `ADDED`, `DROPPED_FROM_CM5`) rather than
a single yes/no answer - this ecosystem's own version numbers are a
base-10 odometer with no semantic-versioning meaning (see this repo's
own `CHANGELOG.md`, "Versioning scheme"), so a version diff alone was
never going to be an honest compatibility signal by itself.

`profile-set-required-resources` (I12, "Verificación del contenido
distribuido fuera del checkout") is deliberately per-profile, not a
global per-project list: a minimal headless profile and a full
UI-carrying one can require different resources from the same project.
Nothing here is invented from the project's own repository - a human
curates this list once per profile, and `profile-build` checks it for
real against the actual post-build tree, catching a UI asset or runtime
module a project's own `build.sh` silently stopped producing, before an
incomplete image is ever promoted.
