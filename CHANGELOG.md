# Changelog

All notable work on **HYDRA-UMC-OS-REBUILDER** is summarized here, newest first.

## Versioning scheme

`pyproject.toml`'s `version` field bumps via
`bump_manifest_version.py` (bare invocation - this repo is a "single owner"
of its own version, no separate `--sync` step), run as the first step of
`build.bat`/`build.sh` before the real build itself, matching every other
Python tool in this ecosystem. Same base-10 "odometer" rule rather than
semantic-versioning judgment calls:

- `patch` +1 on every build
- when `patch` would exceed 9, it resets to 0 and `minor` +1 instead (e.g. `0.0.9` -> `0.1.0`, never `0.0.10`)
- the same carry cascades into `major` if `minor` would exceed 9

This file itself is *not* auto-generated per build (most builds are routine
verification runs with nothing changelog-worthy); it's updated by hand when
a change is actually worth summarizing for a human.

---

## [0.1.7] - C15: a real content hash of what actually landed in the image, not just its version string

The built image's own inventory (`BuildResult.installed`) only ever
recorded `name@version` as free text - a build that installed the right
VERSION but a corrupted/tampered/partial copy of it would report exactly
the same inventory line as a clean one, since nothing tied that claim to
what was actually on disk.

New `_hash_directory_tree()`: a real, deterministic SHA-256 over every
file's own real path and content under a project's installed directory
(sorted for determinism, so it never depends on filesystem walk order) -
now appended to every real installed-project line as
`name@version#sha256:<hash>`. A symlink is hashed by its own real target
string, never followed (never pulls arbitrary host content into the hash
and never raises on a dangling one). Not git-tree-compatible - a real,
custom hash, stated honestly rather than implied.

Verified: full pytest suite (67/67, 8 new - stability, content/path/
addition sensitivity, walk-order independence, empty-directory, real
symlink handling), `tools/ci_validate.py` PASS (incl. a 6-language
README version-string fix this surfaced).

## [0.1.6] - C15: scan the built image's own output for a leaked secret

Input integrity (the official base image's own checksum, commit-SHA
pinning for every installed project) was already real and tested - but
nothing ever looked at what the build itself leaves behind in the
OUTPUT. A real Wi-Fi password, an SSH private key, a shell history or a
stray `.env` file left in the mounted rootfs would have shipped straight
into a publicly distributable image.

- New `scan_for_leaked_secrets()` in `image_builder.py` - a real,
  read-only scan of the mounted rootfs (never a network image
  introspection tool, just plain file reads on an already-mounted
  filesystem) for: a real `psk=` in `wpa_supplicant.conf` or a
  NetworkManager connection profile, a real PEM-format private key under
  any home directory's `.ssh/` (never flagging the matching `.pub`), a
  real non-empty `.bash_history`/`.zsh_history`, and a real `.env` file
  anywhere under a home directory. A fixed, explicit list of real secret
  shapes - never a fuzzy heuristic.
- `build_image()` now runs this scan right before unmounting (while the
  rootfs is still a real, live mount point) and refuses to promote the
  image if anything real is found - the raw image is left in `work_dir`
  for inspection, the exact same "never promote what couldn't be
  confirmed clean" policy an unmount/cleanup failure already enforces.
- 9 new real tests in `tests/test_image_builder.py` - no real loop-mount
  needed, since the function only ever reads from a plain directory
  tree. 59/59 tests pass.
- README + all 6 translations - documents this as a 4th real pipeline
  step, alongside download/build/first-boot-config.

## [0.1.5] - V07-013: a normal incremental build.sh could never actually finish an install

REV-018 (an earlier independent revalidation audit) correctly found that
`_install_one_project()` ran a pinned commit's own real, INCREMENTAL,
version-bumping `build.sh` and then refused to install if the reported
version diverged from the plan - but every real `build.sh` in this
ecosystem always bumps its own version as its first real effect, on
every single invocation. That refusal-on-any-divergence check meant this
pipeline could never actually finish installing a single real project;
it only ever proved the divergence it was designed to catch.

Fixed: after `build.sh` runs (its real, un-reimplemented compile/package
steps still happen exactly as before - nothing here bypasses a
project's own npm/cargo/go/pip build), the checkout's own TRACKED files
are restored to the exact pinned commit with a plain `git checkout -- .`
- the real deployable output `build.sh` produced lands in that project's
own gitignored path (`dist/`, `node_modules/`, `target/release/`, a
compiled binary) and is completely untouched by that restore, while the
version/manifest/CHANGELOG bookkeeping the audit specifically objected
to mutating goes back to the exact pinned state. The original
divergence check is kept as a real safety net for the one case this
restore cannot fix (a version living in a path outside git's tracking)
rather than removed.

Scope note: this closes the specific P1 finding (a normal build can now
actually complete). It does not add systemd-unit installation/enablement
for a project's declared `service` - that remains real, separate future
work, not claimed done here.

2 new regression tests (50 total): the ordinary incremental-build case
now succeeds and reports the restored, planned version; the "restore
did not actually fix it" case still refuses, exactly like REV-018's own
original closure criterion.

## [0.1.4] - REV-018: real regression found by independent revalidation

An independent revalidation audit reproduced a real gap in `_install_one_project()`
(against a real fixture project whose own `build.sh` bumps its version,
no real image/mount involved):

- **REV-018 [P1]:** the pinned commit `_install_one_project()` clones and
  checks out (IMAGE-01's own real fix) is still built with that project's
  real `build.sh` - this ecosystem's real, INCREMENTAL, version-bumping
  build script (the same one a human release runs), not the non-mutating
  `build-test.sh` every project also carries. Running it here can change
  the very version the pinned commit reports, silently diverging the
  image's real installed identity from the plan that was supposed to
  describe it exactly - and this was previously reported back as if it
  were the correct, trustworthy result. Fixed: the real, post-build
  version is now compared against the plan's own recorded version for
  that entry, and the build is refused outright on any divergence,
  instead of silently accepting whichever version came out.
  **Honest limit, stated explicitly:** a real, fully non-incremental
  packaging path (so this divergence could never happen in the first
  place, rather than only being caught after the fact) is real, separate
  future work not attempted here.
- 1 new regression test; the existing test that asserted the old
  divergent-version behavior as correct was rewritten into two tests (one
  for the matching-version case, one proving the divergent case is now
  refused).

## [0.1.3] - IMAGE-01/02: pin to a real commit, never promote an image cleanup couldn't finish

- **IMAGE-01 (found in an ecosystem-wide software-improvements audit,
  P1):** `_install_one_project()` used to `git clone --branch <branch>` -
  a real push to that branch between planning and building silently
  changed what got installed, with no way to tell after the fact. New
  `ecosystem_plan.resolve_commit_shas()` resolves each entry's real,
  immutable HEAD commit SHA from GitHub's own REST API right after the
  plan is built; an entry whose SHA cannot be resolved is excluded from
  the build (recorded as a discovery error) rather than falling back to
  an unpinned branch. `_install_one_project()` now clones (full, not
  shallow - an arbitrary historical commit needs real reachable history)
  and explicitly checks out that real SHA, and reports the REAL final
  version read back from the rootfs's own `hydra-umc.project.json` AFTER
  `build.sh` ran, not the plan's own pre-fetch value - that build step
  bumps the version itself, this ecosystem's universal per-repo
  convention, so the plan alone was never proof of what actually ended
  up installed.
- **IMAGE-02 (found in the same audit, P1):** `build_image()`'s cleanup
  (`umount`/`losetup -d`) ran with `check=False`, so a real failure there
  passed silently - the function went on to promote (move + report
  `ok=True`) an image whose own loop device or mount could still be
  active. Every real exit code/stderr is now captured; a cleanup failure
  returns `ok=False` with a real diagnostic and leaves the raw image
  un-promoted (still in `work_dir`, not moved to `output_path`) instead
  of silently shipping a possibly-still-mounted image as done.
- 7 new regression tests (48 total): resolving a real SHA via a local
  fixture GitHub API server, excluding only the entry that actually
  failed to resolve, refusing an unpinned entry, and reading back the
  real post-build version instead of the plan's stale one. `pytest
  tests/ -q`: all passing.

## Unreleased

- **Real UI layout/sizing pass, per real user feedback**:
  - The Build Target buttons (This computer / Remote host via SSH) and
    the Remote Preset buttons (CM5 / Custom host) each now sit on one
    line inside their own visual frame, instead of stacked loose in the
    column.
  - The progress bar under Build Log is now double height, with its own
    phase-name/percentage labels doubled in size to match.
  - About, Copy and the About dialog's own Close button are now double
    width; First-Boot Config is 50% wider; Refresh from GitHub is 25%
    wider; the About dialog's Open on GitHub is 25% wider.
  - The build checkpoint list (Download/Decompress/.../Finalize) now
    shows real, descriptive, translated labels ("Download base image",
    "Write first-boot config", ...) instead of the raw, untranslated
    internal phase key (e.g. "firstboot-config") - new `checkpoint_*`
    keys added across all 7 languages in `i18n.py`.

## [0.1.2]

- **Real program icon**: the window/taskbar icon fell back to Qt's own
  generic default - `run_gui()` never called `setWindowIcon()` at all,
  even though this repo already ships the same real `images/
  HYDRA_UMC_ICON.ico`/`.svg` assets HYDRA-UMC-UPDATER's own
  `launch_qt_gui()` already uses. Wired up the same real pattern here
  (native `.ico` on Windows, SVG fallback for a fresh checkout).
  Verified with a real screenshot of the running window.
- **Column widths, real user feedback**: Ecosystem Status gave up 25%
  of its own real width (measured live at a real 1920px window: 1196px
  -> 896px) to Build Image and Build Log in equal halves (+150px each:
  340->490, 300->450) - both were feeling cramped next to how much room
  Ecosystem Status's own list was keeping. Verified with a real
  headless QML width measurement before and after, and a real
  screenshot of the running window.

## [0.1.1]

- **Fixed a real, deeper cause behind v0.1.0's own new disk-space check firing on the real CM5**: that check was correct (0.63 GB available, 2.82 GB needed), but the real reason there was no room is that the remote work directory (plain `mktemp -d`) resolves to `/tmp`, which on this real CM5 - and on a modern systemd host generally - is a **tmpfs capped at 2GB total**, smaller than a single base image's own real peak decompressed size regardless of how empty it is. Now measures real free space (`df --output=avail`) on both `/tmp` and `/var/tmp` (the POSIX-standard disk-backed counterpart) and picks whichever the actual host reports more room on, rather than assuming either.
- **Fixed the real leftover this caused**: 3 real orphaned work directories (1.3GB total) from previous remote-build attempts survived on the real CM5, because the client-side cleanup only runs if the GUI process reaches its own `finally` block - closing/crashing the whole process skips it. The remote work directory now uses a distinctive, safely-matchable name (`hydra-umc-os-rebuilder-build.*` instead of `mktemp`'s generic default) so a real sweep at the start of every remote build can safely remove only this tool's own stale leftovers (older than 2 hours) before starting, without risking any other real process's own unrelated temp files.

## [0.1.0]

- **Real pre-flight disk-space checks**, found from a real live remote-build failure against the CM5 (`xz: ... Write error: No space left on device`, surfaced only as a bare `CalledProcessError` deep in a traceback). `fetch_base_image()` now HEAD-checks the real download size before starting, and `build_image()` reads the real uncompressed size straight from the `.xz` container's own index (`xz --robot --list`, never a guessed compression-ratio multiplier) before decompressing - either check now fails fast with a clear, actionable message naming exactly how much space is available vs. needed, instead of a multi-minute download or multi-GB decompression dying partway through.
- Decompression also no longer keeps the now-redundant `.xz` around forever (dropped `-k` from the `xz` call) - a successful decompress frees that space back for the mount/install phase that follows, real headroom that matters most on a space-constrained host like the CM5 itself.
- **Real progress bar** below the Build Log, per real user feedback - one honest fraction per real build phase reached (the same 7-phase sequence the existing checkpoint list already tracks), never a smoothly-animated fake percentage.

## [0.0.9]

- **Draggable dividers between the 3 columns** (`SplitView` instead of a
  plain `RowLayout`) - real user feedback: "que se puedan mover de
  izquierda a derecha para yo elegir si el de build log lo quiero mas
  grande". A custom-styled handle (a thin cyan-on-hover bar) matches
  this window's own dark theme instead of Qt's plain default grey.
- **Fixed a real, serious hang, likely the exact "en windows me da
  fallo" report with no visible error at all.** `_start_remote_build`'s
  own worker thread did `import paramiko` and constructed its
  `SSHClient()` BEFORE the `try` block that was supposed to catch
  real failures - on a real machine where `pip install -e .[gui]` was
  run before this remote-build feature ever added `paramiko` as a
  dependency (never rerun since), the `ModuleNotFoundError` raised
  straight out of the thread with nothing catching it: no
  `_buildResult` ever fires, `buildBusy` stays `true` forever (the UI
  just looks permanently stuck), and a background thread's own
  uncaught exception does NOT go through `sys.excepthook` either -
  Python's own default `threading.excepthook` only ever prints it to a
  stderr this GUI has no console for when launched by double-click, so
  even the new v0.0.8 log file never saw it. Both are now inside the
  real `try`/`except`, and `_setup_file_logging()` also installs a real
  `threading.excepthook`, so this class of bug can never be silent
  again. Verified live: a real connection timeout now correctly
  surfaces through `_buildResult` and clears `buildBusy` instead of
  hanging (confirmed via a direct `RebuilderBridge.buildImage()` call
  against an unroutable address).

## [0.0.8]

- **Real user report: a build failed on Windows and there was no way to
  get the error text out of the window** ("no puedo seleccionar su log
  para copiar y pegartelo"). The Build Log was a `ListView` of plain
  `Text` items - not selectable, no copy, no scrollbar. Replaced with a
  `TextArea` inside a `ScrollView` (real text selection, Ctrl+C, a real
  scrollbar), plus a "Copy" button that selects and copies the whole log
  in one click. Every real build-log line (and every unhandled
  exception, including from a background thread, which Qt would
  otherwise only ever print to a console this GUI doesn't have when
  launched by double-click) now also lands in a real plain-text log
  file (`~/.hydra_umc_os_rebuilder/logs/gui_<timestamp>.log`), whose
  path is shown under the log panel - the same real file-logger
  convention this ecosystem's other desktop tools already use (e.g.
  URTC-TESTER's own `_file_logger`). Verified live: the file is created
  and receives real log lines on a real launch.

## [0.0.7]

- **Fixed a follow-up on v0.0.6's own `GameField` font change**: doubling
  the font also grew `implicitHeight` 38px -> 52px, which real user
  feedback said explicitly was NOT wanted ("no quiero que se haga más
  grande o más alto") - bigger text, same-size field. Reverted
  `implicitHeight` back to 38 while keeping the 24px font.

## [0.0.6]

- **3 real layout refinements, live user feedback on v0.0.4's own
  restructure**:
  - The window now opens maximized (`visibility: Window.Maximized`).
  - Build Target ("This computer" / "Remote host via SSH") is now a
    stacked column instead of a side-by-side row - "esta un poco fea".
  - Build Log moved into its own 3rd column, to the right of the Build
    Image controls, instead of sharing that panel - "aunque el panel
    Ecosystem Status se haga más pequeño, no hace falta una lista tan
    ancha" (Ecosystem Status is now the flexible column, willingly
    narrower to make room).
  - The build-phase checkpoint row is now a vertical list (one phase per
    row, a filled circle + label), matching HYDRA-UMC-UPDATER's own Safe
    Update panel style exactly (✓/›/blank inside the circle) - was a
    wrapped horizontal `Flow`.
  - `GameField`'s font (so both typed text and placeholder text, which
    share one font on a `TextField`) doubled from 12px/38px tall to
    24px/52px - the placeholder text specifically ("Host / IP",
    "Username", ...) read too small.
- `pyside6-qmllint`: no errors. Manually launched end-to-end again,
  confirmed via a real bounded screenshot of the running window: zero
  QML/Python runtime errors.

## [0.0.5]

- **New `--cli status --json`**, for scripting - the same real discovery
  as the human-readable table, as a real JSON object (`projects[]` with
  every `EcosystemPlanEntry` field, `discovery_errors[]`, `total`).
  New real test (`tests/test_main.py`) exercises the actual JSON shape
  against a monkeypatched plan. Verified live against the real ecosystem
  too.

## [0.0.4]

- **Layout: Build Image now sits beside the Ecosystem Status list, First-Boot
  Config is a dialog instead of a 3rd tab - real user feedback, "que lo
  podemos dejar muy similar a UPDATER".** The project list is now always
  visible (no longer hidden behind a tab); a new "First-Boot Config…"
  button next to Build Image opens the same real form in a `Dialog`
  (`saveFirstBootConfig()` unchanged) - matching UPDATER's own narrow
  right-side action panel next to its main list.
- **New: a real remote build over SSH, for the actual gap the same
  feedback named - "no me deja hacer build image en windows tampoco".**
  `check_build_platform()` correctly refuses to build on Windows (needs
  real loop-mount/chroot); there was previously no way to build FROM
  Windows at all. `RebuilderBridge._start_remote_build()` (new, paramiko)
  connects to a real Linux host over SSH, confirms it's actually Linux
  with real passwordless-sudo root (never assumed), creates a throwaway
  venv, installs this exact project fresh from its own public GitHub repo,
  runs `--cli build-image` with the same first-boot flags the local path
  uses (now threaded into a real build - see below), streams the real
  remote stdout back as a live checkpoint row + build log, and downloads
  the real resulting `.img` back over SFTP - the remote scratch dir is
  always removed after, success or failure. A "CM5 (production)" preset
  pre-fills the real host/username (never a password - authentication is
  always live user input, key or password, never hardcoded) with an
  honest warning that building there competes with the live services
  already running on it; "Custom host" is a free-form second target.
  Verified live against the real CM5: SSH connect (key auth - its sshd
  only allows publickey, confirmed live), `uname -s`, `sudo -n true`,
  venv creation, and a real `pip install` from this project's own GitHub
  HEAD all succeed. The full multi-minute build itself was deliberately
  NOT triggered against the live production CM5 in the same session that
  verified the pipeline - a real, ready action, not yet exercised
  end-to-end.
- **Fixed a real, separate bug found while verifying the above: this
  package's own `__version__` had been silently stuck reporting "0.0.1"
  since the very first release**, 2 real versions behind
  `pyproject.toml`. `bump_manifest_version.py` (this repo's declared
  single owner of its version) only ever touched `pyproject.toml` and
  `hydra-umc.project.json` - nothing kept `src/hydra_umc_os_rebuilder/
  __init__.py`'s own hardcoded literal in sync, unlike HYDRA-UMC-UPDATER's
  own `__init__.py` (mirrored by that project's separate `bump_version.py`
  step). Confirmed live: a fresh `pip install` from this project's own
  real GitHub HEAD (already at 0.0.3) still reported `--version` 0.0.1.
  `__version__` now reads back from the installed distribution's own
  metadata (`importlib.metadata.version(...)`, populated by setuptools
  straight from `pyproject.toml` at install time) instead of a second,
  hand-maintained copy - structurally impossible to drift again, rather
  than one more sync step to remember.
- **First-boot config now actually feeds into a real build, on both
  targets** - `main.py`'s `build-image` subcommand gained the same
  `--hostname`/`--wifi-ssid`/... flags `config` already had, and
  `buildImage()`'s local path now builds a real `FirstBootConfig` from
  the dialog's own fields instead of always passing `firstboot=None`.
  Previously the dialog could only ever write a standalone `firstrun.sh`
  to an arbitrary directory, disconnected from what a real build actually
  produced.
- `pytest`: 31/31 pass. `pyside6-qmllint`: no errors. Manually launched
  end-to-end twice more, including clicking through to the new First-Boot
  Config dialog: zero QML/Python runtime errors.

## [0.0.3]

- **Finished the real visual parity with HYDRA-UMC-UPDATER's own GUI that
  v0.0.1 only half-delivered.** v0.0.1's own changelog entry claimed "same
  palette, typography and component set" - true for the first two, not
  the third: `Main.qml` only ever reused the 3 shared color/font
  primitives and rendered every actual control (buttons, combos,
  checkboxes, the header, the tab bar) as bare default Qt Controls, real
  user feedback confirmed live against both windows side by side. Ported
  UPDATER's own styled component set for real - `GameButton`, `GameCombo`,
  `GameCheck`, `MetricCard`, `AboutInfoRow`, the animated header mark, the
  gradient background, a real About dialog - plus a new `GameField` (a
  styled `TextField`, which UPDATER's own form-free UI never needed but
  this repo's real hostname/Wi-Fi/output-path inputs do). Also closed a
  real, separate gap found in the same pass: the Build tab's own button
  had no `onClicked` handler at all - `RebuilderBridge.buildImage()` now
  runs the real `image_builder.build_image()` pipeline on a worker
  thread (same threading pattern as `refresh()`), rendering the real
  `download → decompress → mount → install → firstboot-config → unmount →
  finalize` phase sequence as a live checkpoint row and a real build log,
  instead of a button that did nothing. `platformOk`/`platformReason`
  (from `check_build_platform()`) now drive the tab's own status banner
  honestly instead of a single static translated string. New i18n keys
  added and verified complete in all 7 languages (`tests/test_i18n.py`).
  `pyside6-qmllint`: no errors (warning count in line with UPDATER's own
  baseline). Manually launched end-to-end 3 times: zero QML/Python
  runtime errors.

## [0.0.2]

- **Fixed a real bug found the same night by an ecosystem-wide bug audit:
  base-image checksum verification never actually ran.**
  `KNOWN_BASE_IMAGES`'s own `sha256=""` (deliberate - meant "fetch the
  real digest from the publisher's sidecar at download time") made the
  old check (`if source.sha256 and actual != source.sha256`) silently
  skip verification on every real build, the exact opposite of what
  `fetch_base_image()`'s own docstring promised. New
  `fetch_reference_sha256()` fetches and parses the real
  `<image-url>.sha256` sidecar Raspberry Pi's own downloads server
  publishes next to every image (verified live: `sha256sum`-style output,
  a bare 64-hex-char digest) - an empty `source.sha256` now always
  resolves to a real digest before the download's own hash is checked
  against anything, never to "skip". 5 new real tests (a real local HTTP
  fixture server, not mocked at the `urllib` layer) - including one that
  reproduces the exact old bug's blind spot (empty pinned hash) and
  confirms verification now actually happens.

## [0.0.1]

- **Initial scaffold.** Real CLI (`status`/`config`/`build-image`) and a
  Qt Quick GUI (reusing HYDRA-UMC-UPDATER's own visual language - same
  palette, typography and component set) built around three real pieces:
  - `ecosystem_plan.py` - discovers every real `deployment_target: "cm5"`
    ecosystem project and its current GitHub version by depending on
    `hydra-umc-updater` as a real library, rather than a second,
    independently-drifting implementation of the same discovery/manifest-
    validation logic that project already has real test coverage for.
  - `firstboot_config.py` - generates a real `firstrun.sh`, the same
    mechanism Raspberry Pi Imager's own "OS Customisation" screen uses on
    a Raspberry Pi OS (Bookworm+) image (`raspi-config nonint` calls, a
    real `userconf-pi`-compatible user/password swap using `passlib`'s
    SHA-512-crypt). See `docs/FIRST_BOOT_CONFIG.md`.
  - `image_builder.py` - the real download/loop-mount/chroot-install/
    unmount pipeline, gated behind an honest `check_build_platform()` that
    refuses to pretend to build on anything but a real Linux host with
    root, rather than silently no-op'ing.
