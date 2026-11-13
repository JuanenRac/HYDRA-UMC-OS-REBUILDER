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
Customisation" screen uses on a Raspberry Pi OS (Trixie+) image. See
[FIRST_BOOT_CONFIG.md](FIRST_BOOT_CONFIG.md) for exactly what this script
does and why.

```
export HYDRA_UMC_FIRSTBOOT_PASSWORD='change-me'
export HYDRA_UMC_FIRSTBOOT_WIFI_PASSWORD='wifi-pass'
hydra-umc-os-rebuilder --cli config --out ./boot \
  --hostname hydra-umc-cm5 --username hydra_umc \
  --wifi-ssid MyNetwork --wifi-country ES \
  --timezone Europe/Madrid --keyboard es
```

The two passwords come from those variables or, with `--secrets-stdin`, from a JSON object on standard input. `--password` and `--wifi-password` on the command line are refused (a command line is visible to every user of the machine) unless the options file sets `secrets.allow_password_argument` to `true`.

Only `--out` is required; every other field is optional and independently
skipped when absent (no hostname change, no user created, no Wi-Fi
configured, SSH enabled by default unless `--no-ssh` is given).

**Recovery-procedure guard:** `--no-ssh` without `--username` is refused
(`FirstBootConfigError`) - on this tool's own official base images (no
default user on Trixie and later) that combination leaves the unit
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

"Versions and compatibility across the set": `status` above always
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

# Curate the real inventory of resources (relative paths inside a
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
a single yes/no answer - a version diff alone was never going to be an honest
compatibility signal by itself.

`profile-set-required-resources` ("Verificación del contenido
distribuido fuera del checkout") is deliberately per-profile, not a
global per-project list: a minimal headless profile and a full
UI-carrying one can require different resources from the same project.
Nothing here is invented from the project's own repository - a human
curates this list once per profile, and `profile-build` checks it for
real against the actual post-build tree, catching a UI asset or runtime
module a project's own `build.sh` silently stopped producing, before an
incomplete image is ever promoted.

## Files written next to a finished image

A successful `build-image` or `profile-build` writes two files beside the image, named after it:

- `<image>.sha256`, one line in the `sha256sum` format, so `sha256sum -c <image>.sha256` checks the image after a copy or a download.
- `<image>.manifest.json`: the image name, its SHA-256 and size, the base image it was built from (label, URL and pinned SHA-256), every installed project with its version and the content hash of what landed on disk, and the version of this tool.

If the two files cannot be written the build is reported as failed, although the image itself has been moved to its place.

## Signed profile manifests

A profile manifest decides which commit of which project goes into an image, so it can be signed:

```
hydra-umc-os-rebuilder --cli profile-keygen --private-out profile.key --public-out profile.pub
hydra-umc-os-rebuilder --cli profile-sign --manifest cm5.json --key-file profile.key
hydra-umc-os-rebuilder --cli profile-verify --manifest cm5.json --trusted-key profile.pub
hydra-umc-os-rebuilder --cli profile-build --manifest cm5.json --out cm5.img --require-signed --trusted-key profile.pub
```

`<manifest>.sig` holds an Ed25519 signature over the SHA-256 of the file's bytes. Keys are 64 hexadecimal characters in a file of their own (the private key is created readable by its owner only and is never overwritten; keep it out of any repository). `--trusted-key` takes the public key itself or a file holding it; `HYDRA_UMC_OS_REBUILDER_PROFILE_PUBKEY` is the fallback. `--require-signed` is off by default (a profile frozen on the same machine needs no signature); `HYDRA_UMC_OS_REBUILDER_REQUIRE_SIGNED=1` turns it on everywhere. A changed file, a signature by another key or a missing signature stops the build before the platform check. A signed manifest is not rewritten by the build: the hashes of what landed go to `<manifest>.built.json`. Needs `pip install 'hydra-umc-os-rebuilder[signing]'`.

## Compressed output

`build-image --compress` and `profile-build --compress` (off by default) compress the finished image with `xz -T0` into `<image>.xz` and write the checksum file and the manifest for that compressed file; the manifest adds `image_uncompressed_sha256`, the hash of the raw image inside. `xz` must be installed on the build host; the check before the download says so if it is not.

## Checks before the download

Before the base image is fetched the build refuses: a plan with no projects, a missing `git` (and `parted`, `e2fsck` and `resize2fs` when `--grow-mb` is used, or `xz` with `--compress`), and a work folder with less free space than the base image needs.

## Images meant to be distributed

`build-image --public-image` and `profile-build --public-image` (off by default) refuse a first-boot configuration and extend the secret scan to the boot partition and to the installed projects (`.env` files, generated `data` folders). A finding stops the image from being promoted. Leave the switch off for an image personalised for your own devices. The **Public image** box of the build window (off by default) does the same for a local build and adds the switch to a remote one.

## Making room in the image

The official image is made to fit a small card, and installing the projects (virtual environments, `node_modules`, build folders) can fill its root file system. `build-image --grow-mb N` and `profile-build --grow-mb N` make the image N MiB larger before it is mounted: the file is extended, partition 2 is grown to the end (`parted resizepart`), the file system is checked (`e2fsck -f`) and grown (`resize2fs`). The default is 0, the size of the base image. The step is covered by tests that check the commands and their order; it has not been run against a real image yet.

## Build backends, artifact cache, signed releases, golden image and boot test

All of these read one options file (`config/rebuilder.example.json` lists every key; give yours with `--config` or `HYDRA_UMC_OS_REBUILDER_CONFIG`). Everything is off by default and unknown keys are refused. None of the commands writes an image, a device or a tag.

- `build-plan [--project NAME=COMMIT ...] [--write-pigen-stage DIR]`: what `build_backend.name` (`chroot`, `nspawn` or `pigen`) would do and which tools the host lacks; `--write-pigen-stage` writes the pi-gen stage files into a new folder.
- `cache-status`, `cache-prune`: the artifact cache keyed by (project, full commit); needs `artifact_cache.enabled` and a directory; entries are checked against their SHA-256 and the least recently used are removed beyond `max_gb`.
- `release-manifest --image F --version V --commit SHA --output release.json`, `release-sign --manifest release.json --key-file KEY`, `release-verify --manifest release.json --image F [--trusted-key K] [--repo DIR]`: image, SHA-256, Ed25519 signature and (with `require_signed_tag`) the signed tag. The private key stays outside any repository.
- `golden-register --image F --store DIR --version V --commit SHA --key-file KEY [--replace]`, `golden-verify --store DIR [--trusted-key K] [--minimum-version V]`: the known-good recovery image lives on the host in a store folder (image, `golden.json`, `golden.json.sig`), signed with Ed25519 under a domain of its own; replacing it needs `--replace` and a newer version; verification checks the signature and the SHA-256 of the image. The device holds no copy.
- `delta-create --base OLD --target NEW --store DIR --key-file KEY [--block-size N]`, `delta-apply --base OLD --store DIR --output NEW [--trusted-key K]`: a signed delta between two images for an A/B update. The store holds `delta.json`, `delta.bin` (only the changed blocks) and `delta.json.sig` (Ed25519 under its own domain). Applying checks the signature, the base and the data, and writes the output only if the rebuilt image has the hash of the target.
- `boot-test --image F`: boots the image in QEMU with a throw-away overlay and reads the serial log; the result is `skipped` (with the reason) when `boot_test.enabled` is off or QEMU is not installed. With `boot_test.extract_kernel` on, the kernel (`kernel_name`) and the device tree (`dtb_name`, optional) are first copied out of the boot partition with `sfdisk` and `mcopy` and given to QEMU with `-kernel` and `-dtb`.
- `config`, `build-image` and `profile-build` take `--run-installer install_X.sh` (repeatable, off by default): the first boot then runs that installer of HYDRA-UMC-OS with `--apply` from `/opt/hydra-umc/src/HYDRA-UMC-OS/provisioning/`. Without it nothing is installed on the first boot.
- `tools/installer_tree_check.py --os DIR` runs every installer of a HYDRA-UMC-OS checkout through the links of a tree laid out like an image (dry-run and the `ROOT`/`SOURCE` lines, never `--apply`) and exits 1 when one does not find its project; the hand-written installers (no `SOURCE` project) are listed as skipped and not run.
