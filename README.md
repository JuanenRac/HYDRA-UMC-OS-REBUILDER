<!-- =============================================================================
HYDRA-UMC-OS-REBUILDER - Builds a ready-to-flash CM5 image
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-OS-REBUILDER banner" width="100%">
</p>

# 📀 HYDRA-UMC-OS-REBUILDER

<p align="center">🇺🇸 <b>English</b> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 📀 Build a Ready-to-Flash, Fully Current CM5 Image

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="Desktop">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Tests-183%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.3.3-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

> **Safety and security status:** this ecosystem is not a certified safety system. There is no hardware E-STOP path, no firmware-enforced limits or interlocks and no verified motion command yet; firmware images are checked with CRC-32 and an Ed25519 signature, and a release build refuses the published development keys (the tool heads and expansion boards behind the relay still run URTC bootloaders, which take a shared-key HMAC-SHA256 instead of a signature); TLS and mutual TLS are optional and off by default; no custom board has been populated or tested yet. Read the [security baseline](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) and the [threat model](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) before relying on any statement here for the safety of a person.

---

## 📋 At a glance

| | |
|---|---|
| Version | `0.3.3` |
| Maturity | Functional |
| Tests | 183 (`python -m pytest -q tests`) |
| Stack | Python 3.10+ / PySide6 / QML / Raspberry Pi OS / GitHub raw content |
| Target | The PC of the person using it |
| On real hardware | Not yet: no run on real hardware is recorded for this version |

**Jump to:** [Overview](#-overview) · [Architecture](#-architecture) · [Security & Safety](#-security--safety) · [Quick start](#-quick-start) · [Testing](#-testing) · [Repository Structure](#-repository-structure) · [Related Projects](#-related-projects)

## 🚦 Project status

Each line is one part of this repository and the light says how far it is today. It is written from what the repository can show (tests, builds, runs), not from what is planned.

🟢 Done and verified · 🟡 Works, with known limits · 🟠 Partly done or not verified yet · 🔴 Not done or not working

| Area | State | What it means here |
|---|---|---|
| Software | 🟡 | Works for its main purpose; the honesty check above lists what is still missing |
| Tests | 🟢 | 183 automated tests, run on every change |
| Real hardware | 🔴 | Not yet: no run on real hardware is recorded for this version |
| Documentation | 🟢 | README in eight languages, checked against the manifest on every change |

## 🎯 Overview

HYDRA-UMC-OS-REBUILDER is a Windows/Linux desktop tool - windowed GUI by
default, full CLI with `--cli` - that answers the question a real CM5
deployment always eventually needs answered: **"build me a fresh SD
card/eMMC image, with the most current real version of every ecosystem
project already on it, and let me set Wi-Fi/user/hostname/SSH before I
write it."**

**What the image contains:** the project checkouts under `/opt/hydra-umc/<name>` at the planned versions and whatever each project's own build produced there. It does not create service users or systemd units and does not set up `/etc/hydra-umc`, so no service starts by itself on first boot; the provisioning scripts of HYDRA-UMC-OS still have to be run on the board.

It does three real things:

1. **Checks GitHub.** Every repository in the HYDRA-UMC/URTC ecosystem
   whose own `hydra-umc.project.json` declares
   `"deployment_target": "cm5"` is discovered dynamically (never a fixed
   list) and its current published version read - by depending on
   `hydra-umc-updater` as a real library for this, not a second,
   independently-drifting reimplementation of its own discovery code.
2. **Builds a real image.** Downloads a pinned, checksum-verified
   Raspberry Pi OS base image, loop-mounts it, and installs/updates each
   discovered project by running **that project's own `build.sh`** inside
   the image's own chroot - never a reimplementation of any one project's
   own build steps.
3. **Writes real first-boot configuration.** Hostname, a new user with a
   real `passlib`-hashed password, Wi-Fi, timezone, keyboard layout and
   SSH - the exact same `firstrun.sh` mechanism Raspberry Pi Imager's own
   "OS Customisation" screen uses on a Raspberry Pi OS (Trixie+) image,
   so the resulting SD card behaves exactly like one Raspberry Pi Imager
   itself would have produced. See
   [docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md).
4. **Scans its own output before promoting it.** Before the built image is
   ever moved to its final path, the mounted rootfs is checked for a real
   Wi-Fi password left in `wpa_supplicant.conf`/a NetworkManager
   connection profile, a real private SSH key, a non-empty shell history,
   or a stray `.env` file - any real finding blocks promotion outright,
   the same way a cleanup failure already does. Checksum verification
   only ever covered the INPUT base image; this is the first check on
   what the build itself leaves behind in the OUTPUT.

```
$ hydra-umc-os-rebuilder --cli status
HYDRA-UMC-SERVER 0.4.8 (api/node)
HYDRA-UMC-VISION-STREAMER 0.0.3 (service/python)
HYDRA-UMC-GATEWAY-INDUSTRIAL 0.0.3 (api/node)
...
TOTAL=27

$ hydra-umc-os-rebuilder --cli config --out ./boot \
    --hostname hydra-umc-cm5 --username hydra-umc --password 'change-me' \
    --wifi-ssid MyNetwork --wifi-password 'wifi-pass' --wifi-country ES
CONFIG_WRITTEN out=boot firstrun=firstrun.sh
```

Running it with no arguments opens the same information in a Qt Quick
desktop shell - reusing HYDRA-UMC-UPDATER's own visual language (same
dark palette, typography and component set) across three tabs: Ecosystem
Status, Build Image, and First-Boot Config.

## 🧩 Role in HYDRA-UMC

**HYDRA-UMC-OS-REBUILDER** builds a fresh CM5 image with the current version of every ecosystem project already on it, and writes the first-boot settings (Wi-Fi, user, host name, SSH) before the image is flashed. The platform layer that image carries is described by `HYDRA-UMC-OS`.

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-OS-REBUILDER architecture" width="100%">
</p>

### ARCHITECTURE & DESIGN DECISIONS

- **SSH host key pinned on first use, and no default Wi-Fi country.** A remote build refuses a machine whose key it has not pinned and shows the key's SHA-256 fingerprint; enter that fingerprint (checked on the machine itself) and the key is pinned, after which only that key is accepted and a different one is refused as a changed key. The image's Wi-Fi country code has no default any more (`--wifi-country` / the country field is required with a Wi-Fi network), because it sets the radio rules of the country where the machine will be.
- **`ecosystem_plan.py` never reimplements GitHub discovery.** It depends
  on `hydra-umc-updater` as a real Python package
  (`hydra_umc_updater.github_client.discover_remote_projects()`) rather
  than a second copy of its manifest-validation/retry/backoff logic -
  a fix or improvement made there benefits this tool automatically.
- **`image_builder.py` never reimplements a project's own build.** Each
  ecosystem project is cloned and checked out at its own real, immutable
  commit SHA (resolved from GitHub at plan time, never a mutable branch
  name that could move between planning and building) and built by
  running ITS OWN `build.sh`, chrooted into the target rootfs - the same
  "delegate to each project's own build script" principle
  `hydra-umc-updater`'s own `install.py` already documents. The version
  reported for each installed project is read back from its own manifest
  AFTER `build.sh` ran, not the plan's own pre-fetch value - that build
  step bumps the version itself, this ecosystem's universal convention.
- **The Linux/root platform boundary is checked first, always.**
  `check_build_platform()` is the very first thing `build_image()` does -
  a build that silently no-ops on an unsupported host (Windows, a
  non-root Linux user, a missing `losetup`/`chroot`) would be worse than
  one that refuses to start with a clear reason.
- **`firstboot_config.py` is a pure generator with no side effects.** It
  only ever produces plain-text file content (a `firstrun.sh` string, a
  `cmdline.txt` patch string) - it never touches a real image or
  filesystem itself, so it stays trivially testable without root or a
  real image. `image_builder.py` alone is responsible for actually
  writing that content onto a real boot partition.
- **A firstboot config that would lock the operator out is refused, not
  built.** Disabling SSH while no account is being configured either
  leaves this tool's own official base images (no default user on
  Trixie and later) with no login path at all - refused unless
  `acknowledge_no_remote_access=True` explicitly opts in.
  `describe_recovery_procedure()` states the real recovery path for
  whatever the config does leave open.
- **A frozen profile is a real, persisted recipe, never re-fetched.**
  `profile_manifest.py`'s `freeze_profile()`/`profile-build` pin every
  project to the exact commit SHA it was tested at - a later build never
  silently substitutes whatever GitHub currently calls "latest".
  `diff_profile()` compares a frozen profile against the live ecosystem
  per project (not as a single boolean), since this ecosystem's own

  meaning and can never be an honest compatibility signal by themselves.
- **Real SHA-512-crypt password hashing, not the stdlib `crypt` module.**
  `crypt` only wraps the *host's own* libc call (Unix-only, and removed
  outright in Python 3.13) - `passlib` produces the byte-identical real
  `$6$...` format `chpasswd -e` expects, on every platform this tool
  itself runs on, including Windows. The hash uses 500000 rounds, not the glibc default of 5000 from the year 2000, so a copy of the image or of `/etc/shadow` costs far more to attack; the device's own preferred yescrypt (`$y$`) cannot be produced portably from Python on Windows.
- **The passwords never travel as arguments.** `--password` and `--wifi-password` still work, but a command line is visible to every user of the machine and `sudo` writes it to the authentication log, so the CLI also reads them from `HYDRA_UMC_FIRSTBOOT_PASSWORD` / `HYDRA_UMC_FIRSTBOOT_WIFI_PASSWORD` or, with `--secrets-stdin`, from one JSON object (`{"password": "...", "wifiPassword": "..."}`) on standard input. The remote (SSH) build of the GUI sends them that way and no longer puts them in the command it runs.
- **The chroot is complete and the remote build is pinned.** The build mounts `/proc`, `/sys`, `/dev` and `/dev/pts` in the image and gives it the host's name resolution while the projects build (the image's own `resolv.conf` is put back afterwards), so `pip`, `npm` and `go` can reach the network from the chroot. A remote build over SSH installs this tool from the release tag of the version that is running (`HYDRA_UMC_REBUILDER_REMOTE_REF` names another tag or commit) and builds from the frozen profile of the plan that was reviewed (`profile-build`) instead of discovering the ecosystem again on the remote host. None of this has run on a real Linux host with root yet.

## 🔒 Security & Safety

`--public-image` (on `build-image` and `profile-build`, and the **Public image** box of the build window; off by default) refuses any first-boot configuration and also scans the boot partition (`firstrun.sh`, `wpa_supplicant.conf`, `userconf*`, `custom.toml`, `user-data`, `network-config`) and `/opt/hydra-umc` (`.env` files and data folders with files) for credentials; any finding stops the image from being promoted. It has not been tried on a real image, because that needs Linux.

## 🚀 Quick start

Requires Python 3.10 or newer.

```bash
./build.sh             # Linux, macOS (build.bat on Windows)
./run.sh               # windowed GUI
./run.sh --cli status  # latest real version of every project
```

## 🧪 Testing

183 automated tests run with `python -m pytest -q tests`. They need no hardware and nothing outside this machine.

The CI runs `HYDRA_UMC_CI=1 python tools/ci_validate.py`, which checks the manifest, the documents, the eight READMEs and the pictures.

## 🏗️ Build & Release

```bash
chmod +x build.sh   # one-time
./build.sh          # creates .venv, pip install -e ".[dev,gui]", compile-checks everything, runs pytest
./run.sh                                # windowed GUI (default)
./run.sh --cli status                   # every ecosystem project's latest real GitHub version
./run.sh --cli config --out ./boot ...  # write first-boot config (see docs/CLI_REFERENCE.md for every flag)
./run.sh --cli build-image --out FILE   # build a ready-to-flash .img (Linux/root only)
./run.sh --cli profile-freeze --name cm5-production --out profiles/cm5-production.json  # pin a real tested combination
./run.sh --cli profile-diff --manifest profiles/cm5-production.json                     # what changed since it was frozen
./run.sh --cli profile-update --manifest profiles/cm5-production.json --project X       # refreeze only X, leave the rest pinned
./run.sh --cli profile-set-required-resources --manifest profiles/cm5-production.json --project X --resource dist/index.html  # curate what X must produce
./run.sh --cli profile-build --manifest profiles/cm5-production.json --out FILE         # build from EXACTLY that frozen profile
```

On Windows: `build.bat`, then `run.bat` (GUI) / `run.bat --cli status` /
`run.bat --cli config ...`. `build-image` still needs a real Linux host
with root either way - see [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

**Troubleshooting**

- `--cli build-image` exits with `BUILD_BLOCKED reason=...`: read the
  reason - it names the exact missing piece (not Linux, not root, or a
  specific missing tool on `PATH`) rather than a generic failure.
- `--cli config` raises a validation error: the hostname/username/Wi-Fi
  country code you gave does not match the real, narrow shape those
  fields require - see `firstboot_config.py`'s own validation.
- `--cli config`/`build-image` refuses with "no login path at all": SSH
  was disabled without configuring an account either - either configure
  one, or pass `acknowledge_no_remote_access=True` (GUI/API) if another
  way in is certain. See `describe_recovery_procedure()`.
- `profile-build` refuses a project with "no real, resolved commit SHA":
  the frozen manifest predates a repository being renamed or made
  private - refreeze the profile (`profile-freeze`) against the current
  live ecosystem instead.
- `profile-build` refuses with "missing N required resource(s)": a
  project curated with `profile-set-required-resources` had its own
  `build.sh` run, but a declared relative path still doesn't exist on
  disk afterward - a real, incomplete build, never rescued by a
  leftover file elsewhere; the image is not promoted.
- The GUI's Ecosystem Status tab stays empty: check your network - this
  tool needs a real connection to `github.com`/`raw.githubusercontent.com`
  for `status`/discovery, same as `hydra-umc-updater` itself.
- **The project count keeps shrinking on repeated refreshes (e.g. 42 ->
  9 -> 0), even after restarting the app** - a real, previously
  unreported bug: resolving each project's real commit SHA spends one
  `api.github.com` call PER PROJECT, on an *unauthenticated* budget of
  60 requests PER HOUR shared with everything else this tool (and
  `hydra-umc-updater`) does - with 50+ real ecosystem projects, a single
  refresh can exhaust it, and GitHub's own hourly window (not this app's
  own state) is what has to reset, not something a restart fixes. Fixed
  to report this honestly instead of silently listing fewer projects:
  the amber banner under the project list now names exactly how many
  projects were resolved before the wall and when GitHub's limit resets
  (see `ecosystem_plan.GitHubRateLimitedError`). Set a `GITHUB_TOKEN`
  environment variable (a plain GitHub personal access token, no scopes
  needed for public repos) before launching this tool to raise the
  budget to 5000/hour - both the repo listing and the per-project
  commit-SHA resolution now honor it consistently.

## 📂 Repository Structure

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-OS-REBUILDER" width="100%">
</p>

<details>
<summary>Text version of the tree</summary>

```text
HYDRA-UMC-OS-REBUILDER/
├── src/hydra_umc_os_rebuilder/   source code
│   ├── __init__.py               Package version
│   ├── ecosystem_plan.py         Real CM5 project/version plan, built on hydra_umc_updater's own discovery
│   ├── firstboot_config.py       Pure firstrun.sh/cmdline.txt generator - no filesystem access; recovery-procedure guard
│   ├── profile_manifest.py       Frozen per-profile version manifests: freeze/diff/selectively update, never "latest" mid-trial
│   ├── image_builder.py          Real download/loop-mount/chroot-install pipeline, Linux/root-gated
│   ├── i18n.py                   Real, complete GUI translations (8 languages)
│   ├── qt_gui.py                 Qt Quick bridge over the CLI modules
│   ├── qml/Main.qml              Themed desktop shell: Ecosystem Status / Build Image / First-Boot Config
│   ├── main.py                   Dispatch: GUI by default, --cli for status/config/build-image
│   ├── remote_install.py         What a remote build installs and builds from (pinned, not the tip of main)
│   └── ssh_hostkeys.py           Trust on first use of the SSH host key of a remote build machine, with a pinned fingerprint
├── tests/                        Real tests: firstboot_config, ecosystem_plan, profile_manifest, image_builder, i18n, main
├── docs/                         documents of the project
├── images/                       Media, app icon and banner
├── tools/                        project tools and CI checks
├── .github/                      CI workflow and issue templates
├── build.sh / build.bat          venv + editable install + compile-check
├── run.sh / run.bat              GUI default / CLI entry point
├── run-gui.vbs                   Windows graphical launcher with no console window
├── bump_version.py               explicit version bump
├── bump_manifest_version.py      Syncs hydra-umc.project.json's version to the native one (--sync)
├── CHANGELOG.md                  what changed in each version
├── build-test.sh                 non-mutating build check
├── hydra-umc.project.json        manifest: version, maturity, family
├── pyproject.toml                package metadata
└── test.sh                       runs the tests
```

</details>

## 🗺️ Roadmap & Known limits

**Known limits today**

- Cloud-init support as an alternative first-boot mechanism for a non-Pi
  base image, alongside the current `firstrun.sh` path.
- Incremental image updates (patch an existing `.img` in place instead of
  a full rebuild) once there is a real need for it beyond a from-scratch
  build.
- A `--json` output mode for `status`, for scripting against it.
- Packaged standalone GUI executable (PyInstaller), matching
  HYDRA-UMC-SUITE's own `build_exe.bat`/`.sh` convention, for a
  double-click install with no `pip`/venv step.
- A GUI checkbox for `acknowledge_no_remote_access` - today the GUI
  surfaces `FirstBootConfigError`'s real message honestly (no crash, no
  silent no-op) but has no dedicated control to opt in, only the CLI/API
  do.
- A GUI panel over `profile_manifest.py` (freeze/diff/update from the
  desktop shell, not just the CLI).

## 🌍 Languages

This README and the documents of the repository exist in eight languages: English, Spanish, German, French, Italian, Japanese, Chinese and Portuguese (Portugal). They are written together and checked in the CI so that the eight files have the same sections and the same links.

## 🔗 Related Projects

This project is part of the HYDRA-UMC robotics ecosystem by the same author (JuanenRac / Electro Hobby 3D). Worth knowing about, since a request might actually be about one of these rather than this repository.

**Directly Related**
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — the reproducible Raspberry Pi OS product layer this tool actually builds an image OF: read-only agent, validated config/profiles, WiFi first-contact provisioning.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — the sibling ecosystem-operations tool this one depends on as a real library for GitHub discovery - detects, installs and manually updates the whole ecosystem on an already-running machine, where this tool builds a fresh one from scratch.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — maintenance-incident coordinator: a low-privilege edge role collects a sanitized inventory/health snapshot, a control-plane role renders it read-only and asks an AI provider to suggest a diagnosis - never applies a patch or deploys anything.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — reproducible development host (Raspberry Pi 5 / CM5) that stores the ecosystem's source and runs bounded build/test tasks under a durable queue; a dedicated dev role, explicitly not an operational CM5.

**Also Part of the Ecosystem**

*Core Hardware & Platform*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — the shared JSON-Schema contract and software job-gate boundary every bridge validates its commands against (not a certified safety function).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — declarative adapter-manifest registry and validator for external-machine connectors; extends the SDK's own contract idea to external machines without replacing the industrial-gateway projects.

*Core Backend & Clients*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the robot-arm motherboard design: CM5 host + dual-core STM32H745, meant to orchestrate up to 8 tool arms over CAN-OTA/SPI-OTA (firmware at an early stage; no populated board yet).
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — the real headless backend (REST/WebSocket) every control client actually talks to.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — web control dashboard with real-time multi-robot 3D visualization.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — desktop (PySide6) swarm command center for multiple servers at once.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android control app with biometric login and a paired Wear OS companion.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS control app (Flutter) with real-time WebSocket sync.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native touch UI for the onboard 7" DSI touchscreen, embedded on the CM5 itself.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — desktop graphical URDF creator/editor that pushes finished models into STUDIO's own catalog.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — desktop STL model editor, transforming/replacing/removing/adding real parts in the same model catalog HYDRA-UMC-EDITOR-URDF also edits.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — coordination boundary for AGV/AMR fleets via a VDA 5050 MQTT publisher (tested against an emulated fleet only).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — high-level CNC-cell coordinator with GRBL status/control-byte access (tested against an emulator only).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — coordination boundary for legged/humanoid droids, with a Boston Dynamics Spot command sender (tested against an emulator only).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — laser-cell coordinator reading 3 key/enclosure/interlock GPIO signals (tested against a fake chip only; it cannot arm or fire a laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — safe high-level board-flow coordinator for OpenPnP pick-and-place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — safe coordination boundary for Moonraker/Klipper 3D printers, with real gated job commands.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinator with a lazily imported rclpy ROS 2 transport (not yet run against a ROS 2 installation).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — coordination boundary for camera-equipped UAVs, with a MAVLink command sender (tested against an emulator only).

*URTC Tool Platform*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware for the physical Universal Robot Tool Controller PCB, 25+ tool profiles over CAN bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — desktop GUI flashing tool for URTC boards, CAN-OTA plus full-chip SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — desktop live CAN-bus diagnostic tool for URTC boards, one panel per tool profile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to URTC-TESTER via the Web Serial API, no local install needed.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — gateway in front of the URTC CAN bus: an allowed list of identifiers, a rate limit and a session key; software tested on a computer, not yet on a real bus.

*Vision AI Node (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — integration hub for the Hailo-8 vision pipeline, with a real per-stage hardware-readiness check.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — real compiled-model registry with Hailo-architecture/checksum safe-load verification.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — real GStreamer pipeline + MediaMTX config generator with a real HailoRT integration boundary.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — Position-Based Visual Servoing correction law with authorisation gated on the zone state; no camera pose estimation yet.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — v0 zone-breach, calibration-freshness and E-STOP-request logic that takes object positions from a file; no detector feeds it and no physical E-STOP is wired to it yet.

*Cognitive AI Node (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — integration hub for the Hailo-10 cognitive pipeline (LLM/VLA/voice orchestration).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — real action-token encoding/decoding and trajectory generation for a Vision-Language-Action model.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — real voice front-end (VAD + intent parser) with a bounded, confirmation-gated Watch relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — real rule-based task decomposition and semantic error recovery over MCU error codes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — real stdlib-only TF-IDF document search over this ecosystem's own Markdown docs.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — local, policy-gated AI maintenance technician for the ecosystem itself - observes, diagnoses and proposes fixes; the two highest risk levels are deliberately not implemented yet.

*Orchestration & Swarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — integration hub with a real gRPC/Protobuf health-report contract and mission state machine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — real priority-based job queue with deduplication, over a real HTTP API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — real gRPC-based fleet health watchdog with retry/backoff and identity-mismatch detection.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — real RRT-based 3D path planner with real obstacle/workspace collision validation.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — real CRDT LWW-Element-Map state sync, property-tested for multi-cell convergence.

*Digital Twin & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — integration hub for the digital-twin engine, with a real version-compatibility sync contract.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — hardware-in-the-loop router with a software collision interlock between simulation and real hardware (tested without real hardware).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — real forward kinematics and joint-limit validation over a real URDF subset.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — real procedural 2D scene generator with YOLO/COCO annotation export.

*Data & Analytics*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — real sqlite3-backed time-series store with a real ingest/query HTTP API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — real FFT + statistical baseline anomaly detector with drift monitoring.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — real OEE/availability calculation over DATALAKE history, with reproducible CSV export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — real CAN/WebSocket ingestion pipeline into DATALAKE, with sequence deduplication.

*Industrial Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — integration hub relaying to industrial protocols, with a real command allowlist/backpressure layer.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — real OPC-UA address space, verified with a real binary-protocol client session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — real MQTT broker with optional per-client authentication and topic ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — real MTConnect `/probe` and `/current` XML endpoints with degraded-mode output.

*Complementary Tools & Ecosystem Operations*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart Summaries and Anomaly Highlighting panels over DATALAKE/ANOMALY-DETECTOR, with an honest statistical fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — fleet CLI with a real, stable exit-code contract, a genuine live client of HYDRA-UMC-SERVER's own API.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS companion app with haptic alert patterns and a paired-phone voice relay (not yet run on a physical watch).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware for a board-mounting rack with real tool-ID decoding and Smart Idle pre-heating logic.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus a real Python vision companion for a thermal/RGB inspection tool head.

## 📚 Documentation

Where to read more:

* **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — every `--cli` subcommand, real example output.
* **[docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md)** — the real `firstrun.sh` mechanism this tool reproduces, and why.
* [Security baseline of the ecosystem](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Threat model of the ecosystem](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Changelog of this repository](CHANGELOG.md)
* [License of this repository](LICENSE.md)

## 🤝 Contributing & Community

* Before a pull request run `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (or `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`): it must print `CI_VALIDATION=PASS`. Do not run `build.sh` or `build.bat` for this check; building is not a check.
* The eight READMEs are written from one source in HYDRA-UMC-DOCS; do not edit them by hand. Change the source and write them again with `tools/make_readmes.py`.
* Do not state in a README what has not run: say "simulated" or "not tried on hardware" where that is the truth.
* See [CONTRIBUTING.md](CONTRIBUTING.md), the [code of conduct](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) and [SUPPORT.md](SUPPORT.md).

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENSE

GPL-3.0-or-later - [LICENSE](LICENSE).
