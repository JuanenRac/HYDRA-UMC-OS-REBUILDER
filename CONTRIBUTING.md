# Contributing to HYDRA-UMC-OS-REBUILDER 🦾

We welcome contributions to the CM5 image-building tool of the HYDRA-UMC
platform.

## Technology Stack

- **Language**: Python 3.10+.
- **GitHub discovery**: depends on `hydra-umc-updater` as a real library
  (`ecosystem_plan.py`) rather than a second, parallel implementation of
  its own `github_client.py`/`project_manifest.py` - see that module's own
  header comment for why.
- **GUI**: PySide6 (Qt Quick/QML), optional (`pip install -e ".[gui]"`) -
  the CLI stays usable on a headless machine without it.
- **Password hashing**: `passlib` (`sha512_crypt`), never the stdlib
  `crypt` module - see `firstboot_config.py`'s own header comment.

## Guidelines

1. **`ecosystem_plan.py` never hardcodes a project list.** Every CM5
   project comes from a real GitHub scan, filtered by each repository's
   own `hydra-umc.project.json` declaring `deployment_target: "cm5"` -
   matching this ecosystem's own dynamic-discovery convention everywhere
   else.
2. **`image_builder.py` never reimplements a project's own build.** Each
   ecosystem project is installed into the image by running THAT
   project's own `build.sh`, chrooted - if a project's own build script is
   wrong, fix it there, not by working around it here.
3. **The Linux/root platform boundary is checked first, always.**
   `check_build_platform()` must remain the very first thing
   `build_image()` does - a build that silently no-ops on an unsupported
   host is worse than one that refuses to start.
4. **`firstboot_config.py` stays a pure generator.** It only ever produces
   plain-text file content (`firstrun.sh`, the `cmdline.txt` patch) - it
   never touches a real image or a real filesystem itself; that boundary
   belongs to `image_builder.py` alone, so the generator stays trivially
   testable without root or a real image.
