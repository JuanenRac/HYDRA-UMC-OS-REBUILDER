<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-OS-REBUILDER banner" width="100%">
</p>

# 🏗️ HYDRA-UMC-OS-REBUILDER

<p align="center">🇺🇸 <b>English</b> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 📀 Build a Ready-to-Flash, Fully Current CM5 Image

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="PySide6 Qt Quick desktop GUI">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Windows and Linux">
</p>

> **Status: v0.1.7, scaffolding.** The CLI, the ecosystem discovery, the
> first-boot config generator and the GUI shell are real and tested. The
> real end-to-end image build (download → loop-mount → chroot-install →
> unmount) is implemented but only runs on a real Linux host with root -
> see [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) for the exact
> platform boundary and why it exists.

**Honesty check - what actually runs today:** the CLI (`main.py`), the dynamic ecosystem discovery that reuses `hydra_umc_updater`'s own GitHub client instead of a second copy of it (`ecosystem_plan.py`), the pure `firstrun.sh`/`cmdline.txt` first-boot config generator with no filesystem access (`firstboot_config.py`), the 7-language GUI translations (`i18n.py`) and the Qt Quick desktop shell (`qt_gui.py`, `qml/Main.qml`) are real and tested (67 tests, `pytest`). `image_builder.py`'s download/checksum-verify/loop-mount/chroot-install/unmount pipeline, its per-project content-hashing of what actually landed on disk, and its pre-promotion scan for a leaked Wi-Fi password/private SSH key/shell history/`.env` file are real code, gated behind `check_build_platform()` - they only execute on a real Linux host with root and `losetup`/`chroot` on `PATH`, and have not been run end-to-end against a real CM5 SD card/eMMC write in this environment; on Windows or a non-root Linux user, `build-image` exits early with `BUILD_BLOCKED reason=...` rather than pretending to succeed. `status`/`config` have been exercised for real against live GitHub discovery. See `CHANGELOG.md` for exactly what has shipped so far, and the ROADMAP below for what remains open.

---

## 1. 🛠️ TECHNICAL OVERVIEW

HYDRA-UMC-OS-REBUILDER is a Windows/Linux desktop tool - windowed GUI by
default, full CLI with `--cli` - that answers the question a real CM5
deployment always eventually needs answered: **"build me a fresh SD
card/eMMC image, with the most current real version of every ecosystem
project already on it, and let me set Wi-Fi/user/hostname/SSH before I
write it."**

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
   "OS Customisation" screen uses on a Raspberry Pi OS (Bookworm+) image,
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

## 2. 🧱 ARCHITECTURE & DESIGN DECISIONS

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
- **Real SHA-512-crypt password hashing, not the stdlib `crypt` module.**
  `crypt` only wraps the *host's own* libc call (Unix-only, and removed
  outright in Python 3.13) - `passlib` produces the byte-identical real
  `$6$...` format `chpasswd -e` expects, on every platform this tool
  itself runs on, including Windows.

## 📂 DIRECTORY STRUCTURE

```
HYDRA-UMC-OS-REBUILDER/
├── src/hydra_umc_os_rebuilder/
│   ├── ecosystem_plan.py    # Real CM5 project/version plan, built on hydra_umc_updater's own discovery
│   ├── firstboot_config.py  # Pure firstrun.sh/cmdline.txt generator - no filesystem access
│   ├── image_builder.py     # Real download/loop-mount/chroot-install pipeline, Linux/root-gated
│   ├── i18n.py               # Real, complete GUI translations (7 languages)
│   ├── qt_gui.py             # Qt Quick bridge over the real CLI-facing modules above
│   ├── qml/Main.qml          # Themed desktop shell: Ecosystem Status / Build Image / First-Boot Config
│   └── main.py                # Dispatch: GUI by default, --cli for status/config/build-image
├── tests/                    # Real tests: firstboot_config, ecosystem_plan, image_builder, i18n, main
├── docs/
│   ├── CLI_REFERENCE.md       # Command reference
│   └── FIRST_BOOT_CONFIG.md   # The real firstrun.sh mechanism this tool reproduces, and why
├── images/                    # Media, app icon and banner
├── tools/
│   ├── build_test.py          # Non-versioning build/compile check
│   └── ci_validate.py         # Manifest/CHANGELOG/docs validation used by CI
├── build.sh / build.bat       # venv + editable install + compile-check
├── run.sh / run.bat           # GUI default / CLI entry point
├── run-gui.vbs                # Windows graphical launcher with no console window
├── bump_version.py            # Ecosystem-wide odometer bump (pyproject.toml + __init__.py)
└── bump_manifest_version.py   # Syncs hydra-umc.project.json's version to the native one (--sync)
```

## ⚙️ BUILD & RUN GUIDE

```bash
chmod +x build.sh   # one-time
./build.sh          # creates .venv, pip install -e ".[dev,gui]", compile-checks everything, runs pytest
./run.sh                                # windowed GUI (default)
./run.sh --cli status                   # every ecosystem project's latest real GitHub version
./run.sh --cli config --out ./boot ...  # write first-boot config (see docs/CLI_REFERENCE.md for every flag)
./run.sh --cli build-image --out FILE   # build a ready-to-flash .img (Linux/root only)
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
- The GUI's Ecosystem Status tab stays empty: check your network - this
  tool needs a real connection to `github.com`/`raw.githubusercontent.com`
  for `status`/discovery, same as `hydra-umc-updater` itself.

## 🚀 ROADMAP

- Cloud-init support as an alternative first-boot mechanism for a non-Pi
  base image, alongside the current `firstrun.sh` path.
- Incremental image updates (patch an existing `.img` in place instead of
  a full rebuild) once there is a real need for it beyond a from-scratch
  build.
- A `--json` output mode for `status`, for scripting against it.
- Packaged standalone GUI executable (PyInstaller), matching
  HYDRA-UMC-SUITE's own `build_exe.bat`/`.sh` convention, for a
  double-click install with no `pip`/venv step.

## 🔗 Related Projects

This project is part of the HYDRA-UMC robotics ecosystem by the same author (JuanenRac / Electro Hobby 3D). Worth knowing about, since a request might actually be about one of these rather than this repository.

**Directly Related**
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — the reproducible Raspberry Pi OS product layer this tool actually builds an image OF: read-only agent, validated config/profiles, WiFi first-contact provisioning.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — the sibling ecosystem-operations tool this one depends on as a real library for GitHub discovery - detects, installs and manually updates the whole ecosystem on an already-running machine, where this tool builds a fresh one from scratch.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — maintenance-incident coordinator: a low-privilege edge role collects a sanitized inventory/health snapshot, a control-plane role renders it read-only and asks an AI provider to suggest a diagnosis - never applies a patch or deploys anything.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — reproducible development host (Raspberry Pi 5 / CM5) that stores the ecosystem's source and runs bounded build/test tasks under a durable queue; a dedicated dev role, explicitly not an operational CM5.

**Also Part of the Ecosystem**

*Core Hardware & Platform*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — the shared JSON-Schema contract and safety-gate boundary every bridge validates its commands against.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — declarative adapter-manifest registry and validator for external-machine connectors; extends the SDK's own contract idea to external machines without replacing the industrial-gateway projects.

*Core Backend & Clients*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the physical robot-arm motherboard: CM5 host + dual-core STM32H745, orchestrating up to 8 tool arms over CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — the real headless backend (REST/WebSocket) every control client actually talks to.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — web control dashboard with real-time multi-robot 3D visualization.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — desktop (PySide6) swarm command center for multiple servers at once.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android control app with biometric login and a paired Wear OS companion.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS control app (Flutter) with real-time WebSocket sync.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native touch UI for the onboard 7" DSI touchscreen, embedded on the CM5 itself.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — desktop graphical URDF creator/editor that pushes finished models into STUDIO's own catalog.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — coordination boundary for AGV/AMR fleets via a real VDA 5050 MQTT publisher.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — high-level CNC-cell coordinator with real GRBL status/control-byte access.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — coordination boundary for legged/humanoid droids, with a real Boston Dynamics Spot command sender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — laser-cell safety coordinator reading 3 real key/enclosure/interlock GPIO safeguards.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — safe high-level board-flow coordinator for OpenPnP pick-and-place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — safe coordination boundary for Moonraker/Klipper 3D printers, with real gated job commands.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — safety coordinator with a real, lazily-imported rclpy ROS 2 transport.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — coordination boundary for camera-equipped UAVs, with a real MAVLink command sender.

*URTC Tool Platform*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware for the physical Universal Robot Tool Controller PCB, 25+ tool profiles over CAN bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — desktop GUI flashing tool for URTC boards, CAN-OTA plus full-chip SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — desktop live CAN-bus diagnostic tool for URTC boards, one panel per tool profile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to URTC-TESTER via the Web Serial API, no local install needed.

*Vision AI Node (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — integration hub for the Hailo-8 vision pipeline, with a real per-stage hardware-readiness check.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — real compiled-model registry with Hailo-architecture/checksum safe-load verification.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — real GStreamer pipeline + MediaMTX config generator with a real HailoRT integration boundary.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — real Position-Based Visual Servoing correction law, safety-gated on upstream zone state.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — real zone-breach checking and E-STOP requesting, with calibration-freshness enforcement.

*Cognitive AI Node (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — integration hub for the Hailo-10 cognitive pipeline (LLM/VLA/voice orchestration).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — real action-token encoding/decoding and trajectory generation for a Vision-Language-Action model.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — real voice front-end (VAD + intent parser) with a bounded, confirmation-gated Watch relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — real rule-based task decomposition and semantic error recovery over MCU error codes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — real stdlib-only TF-IDF document search over this ecosystem's own Markdown docs.

*Orchestration & Swarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — integration hub with a real gRPC/Protobuf health-report contract and mission state machine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — real priority-based job queue with deduplication, over a real HTTP API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — real gRPC-based fleet health watchdog with retry/backoff and identity-mismatch detection.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — real RRT-based 3D path planner with real obstacle/workspace collision validation.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — real CRDT LWW-Element-Map state sync, property-tested for multi-cell convergence.

*Digital Twin & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — integration hub for the digital-twin engine, with a real version-compatibility sync contract.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — real hardware-in-the-loop safety interlock routing commands between simulation and real hardware.
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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS companion app with real haptic alerts and a paired-phone voice relay.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware for a board-mounting rack with real tool-ID decoding and Smart Idle pre-heating logic.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus a real Python vision companion for a thermal/RGB inspection tool head.

---

## 📚 Documentation & Community

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — every `--cli` subcommand, real example output.
- **[docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md)** — the real `firstrun.sh` mechanism this tool reproduces, and why.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — tech stack and coding guidelines for a pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — the standards of behavior expected in this community.
- **[SECURITY.md](SECURITY.md)** — how to report a vulnerability, and this project's own real security focus areas.
- **[SUPPORT.md](SUPPORT.md)** — where to ask questions and report bugs.

## 👤 AUTHOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENSE

GPL-3.0 (software) / CC BY-SA 4.0 (documentation) - see [LICENSE.md](LICENSE.md).
