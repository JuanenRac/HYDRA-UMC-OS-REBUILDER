# Support Information 🛠️ (HYDRA-UMC-OS-REBUILDER)

Thank you for using HYDRA-UMC-OS-REBUILDER! Here is how you can get help:

## 📺 Video Tutorials & Demos

The best way to see how this tool builds a ready-to-flash CM5 image is
through our official YouTube channel:
[youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## ✉️ Direct Technical Inquiries

For questions about building your own image, a custom first-boot
configuration, or anything not covered by the README:
Email: `electrohobby3d@gmail.com`

## 🐛 Bug Reports

If `--cli status` reports the wrong version for a project, `--cli config`
produces a `firstrun.sh` that does not behave as documented in
`docs/FIRST_BOOT_CONFIG.md`, or `--cli build-image` fails on a real Linux
host that passes `check_build_platform()`, please open a **GitHub Issue**
in this repository - include the exact command you ran and its full
output.
*Please search existing issues before opening a new one.*

## ❌ What is NOT support?

- This tool does not build/install a project FOR you beyond running its
  own existing `build.sh` inside the image - a build failure inside a
  specific project's own `build.sh` is that project's own issue tracker,
  not this one's.
- This tool cannot build an image on Windows/macOS - that limitation is
  by design (see `docs/CLI_REFERENCE.md`), not a bug to report.
