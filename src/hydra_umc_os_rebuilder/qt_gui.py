# =============================================================================
# HYDRA-UMC-OS-REBUILDER - Qt Quick / QML GUI bridge: qt_gui.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# QML calls this bridge; the bridge calls the same ecosystem_plan.py/
# firstboot_config.py/image_builder.py the CLI uses - no separate GUI-only
# implementation to drift from those. PySide6 is imported only when the GUI
# actually launches (main.py's own --cli path never imports this module),
# same boundary HYDRA-UMC-UPDATER's own qt_gui.py keeps.
# =============================================================================
from __future__ import annotations

import logging
import re
import sys
import threading
import time
import traceback
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from . import __version__, i18n
from .ecosystem_plan import EcosystemPlanEntry, fetch_ecosystem_plan
from .firstboot_config import FirstBootConfig, WifiConfig
from .image_builder import BuildProgress, check_build_platform

# Matches the real "[phase] detail" lines the remote build's own CLI
# progress() printer emits (main.py's _cmd_build_image) - see
# RebuilderBridge._start_remote_build's own emit_line() for why this is
# parsed back apart rather than shown as one opaque string.
_REMOTE_LOG_LINE_RE = re.compile(r"^\[(?P<phase>[\w-]+)\]\s*(?P<detail>.*)$")

#: Real, plain-text log file, one per real GUI run - the QML build log
#: (a ListView, not a selectable text box) can't be copy-pasted out of
#: the running app, found live: a real Windows build failure had no way
#: to get its own error text out of the window at all. Every real build-
#: log line, every real exception (including one from a background
#: thread, which Qt would otherwise only ever print to a console this
#: GUI doesn't have when launched by double-click) lands here too, same
#: real file-logger convention already used by this ecosystem's other
#: desktop tools (see e.g. URTC-TESTER's own `_file_logger`).
LOGS_DIR = Path.home() / ".hydra_umc_os_rebuilder" / "logs"


def _setup_file_logging() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"gui_{time.strftime('%Y%m%d_%H%M%S')}.log"
    logger = logging.getLogger("hydra_umc_os_rebuilder.gui")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.info("HYDRA-UMC OS Rebuilder GUI v%s starting - log file: %s", __version__, log_path)

    def _log_unhandled(exc_type, exc_value, exc_tb) -> None:
        logger.error("UNHANDLED EXCEPTION:\n%s", "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _log_unhandled

    # Real, separate safety net for a background worker thread's own
    # uncaught exception (refresh()/buildImage() both run on one) -
    # sys.excepthook above only ever covers the main thread. Python's own
    # default threading.excepthook already prints these to stderr, which
    # this GUI has no console for when launched by double-click, so
    # without this a broken worker thread failed completely silently:
    # the real bug found live behind this fix (see _start_remote_build's
    # own comment) left buildBusy stuck true forever with no error
    # anywhere - not even here in the log - until this hook existed.
    def _log_unhandled_thread(args) -> None:
        logger.error(
            "UNHANDLED EXCEPTION in thread %r:\n%s",
            args.thread.name if args.thread else "?",
            "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)),
        )
        threading.__excepthook__(args)

    threading.excepthook = _log_unhandled_thread
    return log_path


_GUI_LOGGER = logging.getLogger("hydra_umc_os_rebuilder.gui")


class RebuilderBridge(QObject):
    languageChanged = Signal()
    projectsChanged = Signal()
    busyChanged = Signal()
    statusChanged = Signal()
    buildProgressChanged = Signal()
    buildBusyChanged = Signal()
    buildLogChanged = Signal()
    _planResult = Signal(object, object)
    _buildProgress = Signal(object)
    _buildResult = Signal(bool, str, object)

    def __init__(self, log_file_path: Path | None = None) -> None:
        super().__init__()
        self._lang = i18n.resolve_initial_lang()
        self._logFilePath = str(log_file_path) if log_file_path else ""
        self._projects: list[EcosystemPlanEntry] = []
        self._discoveryErrors: list[str] = []
        self._busy = False
        self._status = ""
        self._buildBusy = False
        self._buildPhase = ""
        self._buildDetail = ""
        self._buildLog: list[str] = []
        # Computed once - the real platform gate never changes for the
        # lifetime of one GUI process (same host, same privilege level).
        self._platformCheck = check_build_platform()
        self._planResult.connect(self._on_plan_result)
        self._buildProgress.connect(self._on_build_progress)
        self._buildResult.connect(self._on_build_result)

    # -- language ---------------------------------------------------------
    @Property(str, notify=languageChanged)
    def language(self) -> str:
        return self._lang

    @Slot(str)
    def setLanguage(self, code: str) -> None:
        if code == self._lang:
            return
        self._lang = code
        i18n.save_lang(code)
        self.languageChanged.emit()

    @Property(list, constant=True)
    def availableLanguages(self) -> list:
        return [{"code": code, "label": label} for code, label in i18n.LANGUAGES]

    @Slot(str, result=str)
    def text(self, key: str) -> str:
        return i18n.text(self._lang, key)

    # -- version ------------------------------------------------------------
    @Property(str, constant=True)
    def appVersion(self) -> str:
        return __version__

    # -- diagnostics ----------------------------------------------------
    @Property(str, constant=True)
    def logFilePath(self) -> str:
        return self._logFilePath

    # -- ecosystem status ---------------------------------------------------
    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(list, notify=projectsChanged)
    def projects(self) -> list:
        return [
            {"name": p.name, "version": p.version, "role": p.role, "stack": p.stack}
            for p in self._projects
        ]

    @Property(int, notify=projectsChanged)
    def projectCount(self) -> int:
        return len(self._projects)

    @Slot()
    def refresh(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.busyChanged.emit()
        self._status = i18n.text(self._lang, "lbl_checking")
        self.statusChanged.emit()

        def worker() -> None:
            try:
                plan = fetch_ecosystem_plan()
                self._planResult.emit(list(plan.entries), list(plan.discovery_errors))
            except Exception as exc:  # pragma: no cover - network failure path, real message surfaced to the UI either way
                self._planResult.emit([], [str(exc)])

        threading.Thread(target=worker, daemon=True).start()

    def _on_plan_result(self, entries: list[EcosystemPlanEntry], errors: list[str]) -> None:
        self._projects = entries
        self._discoveryErrors = errors
        self._busy = False
        self._status = i18n.text(self._lang, "lbl_projects_found", count=len(entries))
        self.busyChanged.emit()
        self.statusChanged.emit()
        self.projectsChanged.emit()

    # -- image build --------------------------------------------------------
    # Real gate, computed once at startup (see __init__) - never invents a
    # green light: platformOk/platformReason mirror check_build_platform()'s
    # own real Linux/root/tool-availability probe byte for byte, the exact
    # one _cmd_build_image() (main.py) already gates on.
    @Property(bool, constant=True)
    def platformOk(self) -> bool:
        return self._platformCheck.ok

    @Property(str, constant=True)
    def platformReason(self) -> str:
        return self._platformCheck.reason

    @Property(bool, notify=buildBusyChanged)
    def buildBusy(self) -> bool:
        return self._buildBusy

    @Property(str, notify=buildProgressChanged)
    def buildPhase(self) -> str:
        return self._buildPhase

    @Property(str, notify=buildProgressChanged)
    def buildDetail(self) -> str:
        return self._buildDetail

    @Property(list, notify=buildLogChanged)
    def buildLog(self) -> list:
        return list(self._buildLog)

    @staticmethod
    def _firstboot_config_from_options(options: dict) -> FirstBootConfig | None:
        """Real first-boot config, built from the same fields the First-Boot
        Config dialog collects - shared by the local build path below.
        Returns None (an image with no first-boot customisation at all)
        when every field was left blank, matching main.py's own
        `_cmd_build_image` behavior for the CLI's equivalent flags."""
        wifi_ssid = (options.get("wifiSsid") or "").strip()
        wifi = WifiConfig(ssid=wifi_ssid, psk=options.get("wifiPassword") or "", country=options.get("wifiCountry") or "US") if wifi_ssid else None
        fields = [options.get("hostname"), options.get("fbUsername"), options.get("fbPassword"), wifi, options.get("timezone"), options.get("keyboard")]
        if not any(fields) and options.get("enableSsh", True):
            return None
        return FirstBootConfig(
            hostname=options.get("hostname") or None,
            username=options.get("fbUsername") or None,
            password=options.get("fbPassword") or None,
            enable_ssh=bool(options.get("enableSsh", True)),
            wifi=wifi,
            timezone=options.get("timezone") or None,
            keyboard_layout=options.get("keyboard") or None,
        )

    @staticmethod
    def _firstboot_cli_args(options: dict) -> list[str]:
        """Same real fields as _firstboot_config_from_options above, as CLI
        flags for the remote (SSH) build path - main.py's own build-image
        subcommand now accepts these directly (see that file's own
        comment for why this is new)."""
        import shlex

        args: list[str] = []

        def add(flag: str, value) -> None:
            if value:
                args.append(f"{flag} {shlex.quote(str(value))}")

        add("--hostname", options.get("hostname"))
        add("--username", options.get("fbUsername"))
        add("--password", options.get("fbPassword"))
        if not options.get("enableSsh", True):
            args.append("--no-ssh")
        add("--wifi-ssid", options.get("wifiSsid"))
        add("--wifi-password", options.get("wifiPassword"))
        add("--wifi-country", options.get("wifiCountry"))
        add("--timezone", options.get("timezone"))
        add("--keyboard", options.get("keyboard"))
        return args

    @Slot("QVariantMap")
    def buildImage(self, options: dict) -> None:
        """Dispatches to the real local pipeline (image_builder.build_image,
        this same host - only reachable when platformOk) or a real remote
        one over SSH (buildImageRemote below - the way to get a real build
        done from a Windows dev machine, which can never itself pass
        check_build_platform()). `options["target"]` picks which; every
        other key is read by whichever path needs it, ignored by the
        other. Reuses whatever ecosystem plan the Status tab already
        discovered (a fresh refresh() first is what populates it) rather
        than re-fetching, so Build always installs the exact same project
        set the user already reviewed."""
        if self._buildBusy:
            return
        if not self._projects:
            self._buildLog = [i18n.text(self._lang, "lbl_build_needs_refresh")]
            _GUI_LOGGER.warning(self._buildLog[0])
            self.buildLogChanged.emit()
            return
        if options.get("target") == "remote":
            self._start_remote_build(options)
        else:
            self._start_local_build(options)

    def _start_local_build(self, options: dict) -> None:
        if not self._platformCheck.ok:
            return
        self._buildBusy = True
        self._buildLog = []
        self._buildPhase = ""
        self._buildDetail = ""
        self.buildBusyChanged.emit()
        self.buildLogChanged.emit()
        self.buildProgressChanged.emit()

        plan_entries = list(self._projects)
        plan_errors = list(self._discoveryErrors)
        output_path = options.get("outputPath") or ""
        firstboot = self._firstboot_config_from_options(options)

        def worker() -> None:
            from .ecosystem_plan import EcosystemPlan
            from .image_builder import KNOWN_BASE_IMAGES, ImageBuildError, build_image

            def progress(update: BuildProgress) -> None:
                self._buildProgress.emit(update)

            try:
                out_path = Path(output_path) if output_path else Path("hydra-umc-cm5.img")
                work_dir = Path.home() / ".hydra_umc_os_rebuilder" / "build-work"
                plan = EcosystemPlan(entries=tuple(plan_entries), discovery_errors=tuple(plan_errors))
                result = build_image(
                    source=KNOWN_BASE_IMAGES[0],
                    plan=plan,
                    firstboot=firstboot,
                    work_dir=work_dir,
                    output_path=out_path,
                    progress=progress,
                )
                self._buildResult.emit(result.ok, result.error or "", result.output_path)
            except ImageBuildError as exc:
                self._buildResult.emit(False, str(exc), None)
            except Exception as exc:  # pragma: no cover - real, unanticipated failure surfaced honestly rather than crashing the worker thread silently
                self._buildResult.emit(False, str(exc), None)

        threading.Thread(target=worker, daemon=True).start()

    def _start_remote_build(self, options: dict) -> None:
        """Real remote build over SSH (paramiko) - lets a Windows operator
        run the real Linux+root pipeline against a real Linux host (this
        ecosystem's own CM5, or any other real machine reachable by SSH)
        instead of never being able to build at all. Real steps, no
        simulation: connects, confirms the target is actually Linux with
        real root (via passwordless sudo - never assumed), creates a
        throwaway venv in a remote temp dir, installs this exact project
        fresh from its own real public GitHub repo (same
        `pip install git+https://...` convention this project's own
        pyproject.toml already uses for hydra-umc-updater), runs
        `--cli build-image` with the same first-boot flags the local path
        uses, streams its real stdout back line by line, and - on success
        - downloads the real resulting .img back to this machine over
        SFTP. The remote scratch directory is always removed afterward,
        success or failure."""
        self._buildBusy = True
        self._buildLog = [i18n.text(self._lang, "lbl_build_remote_connecting", host=options.get("host", ""))]
        self._buildPhase = ""
        self._buildDetail = ""
        _GUI_LOGGER.info(self._buildLog[0])
        self.buildBusyChanged.emit()
        self.buildLogChanged.emit()
        self.buildProgressChanged.emit()

        output_path = options.get("outputPath") or "hydra-umc-cm5.img"
        firstboot_args = self._firstboot_cli_args(options)
        host = options.get("host") or ""
        port = int(options.get("port") or 22)
        username = options.get("username") or ""
        auth_method = options.get("authMethod") or "key"
        password = options.get("password") or ""
        key_path = options.get("keyPath") or ""
        key_passphrase = options.get("keyPassphrase") or ""

        def emit_line(line: str) -> None:
            # The remote CLI's own progress() printer (main.py's
            # _cmd_build_image) already formats each real line as
            # "[phase] detail" - parsed back apart here so _on_build_progress
            # can render it exactly like a local build's own BuildProgress
            # (phase + bare detail, no double-bracketing). A line that
            # doesn't match (this method's own "[connect]"/"[install]"
            # pre-flight lines, or the final BUILD_OK/BUILD_FAILED summary)
            # still comes through, just with an empty/synthetic phase.
            match = _REMOTE_LOG_LINE_RE.match(line)
            if match:
                self._buildProgress.emit(BuildProgress(phase=match.group("phase"), detail=match.group("detail")))
            else:
                self._buildProgress.emit(BuildProgress(phase="", detail=line))

        def worker() -> None:
            # Real bug fixed here, found live: `import paramiko` and
            # SSHClient() construction used to happen BEFORE the try block
            # below - on a real machine where the `gui` extra's own
            # paramiko dependency was installed before this remote-build
            # feature existed (an older `pip install -e .[gui]`, never
            # rerun), a missing paramiko raised straight out of this
            # thread with NOTHING catching it: no _buildResult signal ever
            # fires, buildBusy stays true forever (the UI just looks
            # permanently "stuck"), and a background thread's own
            # uncaught exception does NOT go through sys.excepthook either
            # - Python's default threading.excepthook only ever prints it
            # to a stderr this GUI has no console for. Now inside the
            # real try/except below, and _setup_file_logging() also
            # installs a real threading.excepthook so this class of bug
            # is never silent again, whatever actually throws next time.
            remote_tmp = ""
            client = None
            try:
                import shlex

                import paramiko

                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                if not host or not username:
                    raise RuntimeError(i18n.text(self._lang, "lbl_build_remote_missing_host"))
                connect_kwargs: dict = {"hostname": host, "port": port, "username": username, "timeout": 10}
                if auth_method == "password":
                    connect_kwargs["password"] = password
                else:
                    if not key_path:
                        raise RuntimeError(i18n.text(self._lang, "lbl_build_remote_missing_key"))
                    connect_kwargs["key_filename"] = key_path
                    if key_passphrase:
                        connect_kwargs["passphrase"] = key_passphrase
                client.connect(**connect_kwargs)

                def run(command: str, *, check: bool = True) -> str:
                    _stdin, stdout, stderr = client.exec_command(command, timeout=30)
                    out = stdout.read().decode("utf-8", errors="replace")
                    err = stderr.read().decode("utf-8", errors="replace")
                    status = stdout.channel.recv_exit_status()
                    if check and status != 0:
                        raise RuntimeError(f"{command!r} failed (exit {status}): {err.strip() or out.strip()}")
                    return out.strip()

                kernel = run("uname -s")
                if kernel != "Linux":
                    raise RuntimeError(i18n.text(self._lang, "lbl_build_remote_not_linux", kernel=kernel))
                run("sudo -n true", check=True)  # real root check - raises with a clear message if this host has no passwordless sudo for this user

                # Real bug fixed here, found live against the real CM5:
                # plain `mktemp -d` resolves to $TMPDIR/tmp (usually
                # /tmp), which on a modern systemd host (this real CM5
                # included, confirmed live via `mount`) is very often a
                # tmpfs - RAM-backed and capped far below a real disk
                # partition (2GB total here, while decompressing one real
                # base image alone peaks past that). /var/tmp is the
                # POSIX-standard disk-backed counterpart, but rather than
                # hardcoding it (this feature's own promise is "any Linux
                # host via SSH", not just this one CM5), pick whichever of
                # the two real candidates this actual host reports more
                # free space on - `df --output=avail` in 1K blocks, real
                # measured numbers, never assumed.
                def _real_avail_kb(path: str) -> int:
                    try:
                        out = run(f"df --output=avail -k {shlex.quote(path)} | tail -n1", check=True)
                        return int(out.strip())
                    except Exception:
                        return -1  # real "couldn't measure" - never treated as "has room"

                tmp_candidates = ("/var/tmp", "/tmp")
                avail_by_candidate = {c: _real_avail_kb(c) for c in tmp_candidates}
                work_base = max(avail_by_candidate, key=lambda c: avail_by_candidate[c])
                emit_line(
                    "[connect] real free space: "
                    + ", ".join(f"{c}={avail_by_candidate[c] // 1024}MB" for c in tmp_candidates)
                    + f" -> using {work_base}"
                )

                # Real bug found live on the real CM5: the `finally` block
                # below that removes `remote_tmp` only ever runs if this
                # worker thread itself reaches it - closing/crashing the
                # whole GUI process instead (found live: 3 real leftover
                # work dirs, 1.3GB total, from exactly that) skips it
                # entirely, and every one of those leftovers eats into the
                # real free-space check above. A distinctive prefix (never
                # the bare `tmp.XXXXXXXXXX` template `mktemp` uses by
                # default, which could just as easily be some other real
                # process's own unrelated temp dir) lets a real startup
                # sweep safely remove only this tool's own stale leftovers
                # - "stale" meaning older than any real build this tool
                # itself could still be running (2 hours is generous
                # headroom over a real base-image build's own real
                # download+decompress+install time).
                stale = run(
                    f"find {shlex.quote(work_base)} -maxdepth 1 -name 'hydra-umc-os-rebuilder-build.*' -mmin +120",
                    check=False,
                )
                if stale:
                    stale_paths = [p for p in stale.splitlines() if p.strip()]
                    emit_line(f"[connect] removing {len(stale_paths)} real stale work dir(s) from a previous run: {', '.join(stale_paths)}")
                    run(f"sudo rm -rf {' '.join(shlex.quote(p) for p in stale_paths)}", check=False)

                remote_tmp = run(f"mktemp -d --tmpdir={shlex.quote(work_base)} hydra-umc-os-rebuilder-build.XXXXXXXXXX")
                emit_line(f"[connect] {username}@{host}: Linux, sudo OK, workdir {remote_tmp}")

                venv_dir = f"{remote_tmp}/.venv"
                run(f"python3 -m venv {shlex.quote(venv_dir)}")
                emit_line("[install] creating a real venv and installing hydra-umc-os-rebuilder from its own GitHub repo...")
                run(f"{shlex.quote(venv_dir)}/bin/pip install --quiet 'hydra-umc-os-rebuilder @ git+https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER.git'")

                remote_img = f"{remote_tmp}/output.img"
                remote_work = f"{remote_tmp}/work"
                cli = f"sudo {shlex.quote(venv_dir)}/bin/hydra-umc-os-rebuilder --cli build-image --out {shlex.quote(remote_img)} --work-dir {shlex.quote(remote_work)}"
                if firstboot_args:
                    cli += " " + " ".join(firstboot_args)

                _stdin, stdout, stderr = client.exec_command(cli)
                channel = stdout.channel
                channel.set_combine_stderr(True)
                buffer = ""
                while True:
                    if channel.recv_ready():
                        chunk = channel.recv(4096).decode("utf-8", errors="replace")
                        buffer += chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            if line.strip():
                                emit_line(line.strip())
                    elif channel.exit_status_ready():
                        break
                    else:
                        import time

                        time.sleep(0.2)
                if buffer.strip():
                    emit_line(buffer.strip())
                exit_status = channel.recv_exit_status()
                if exit_status != 0:
                    raise RuntimeError(i18n.text(self._lang, "lbl_build_remote_failed", status=exit_status))

                emit_line(i18n.text(self._lang, "lbl_build_remote_downloading"))
                sftp = client.open_sftp()
                try:
                    local_out = Path(output_path)
                    local_out.parent.mkdir(parents=True, exist_ok=True)
                    sftp.get(remote_img, str(local_out))
                finally:
                    sftp.close()

                self._buildResult.emit(True, "", Path(output_path))
            except Exception as exc:
                _GUI_LOGGER.error("Remote build failed: %s", exc, exc_info=True)
                self._buildResult.emit(False, str(exc), None)
            finally:
                if client is not None:
                    if remote_tmp:
                        try:
                            client.exec_command(f"rm -rf {remote_tmp}")
                        except Exception:  # pragma: no cover - best-effort cleanup, a failed rm here never hides the real build result already emitted above
                            pass
                    client.close()

        threading.Thread(target=worker, daemon=True).start()

    def _on_build_progress(self, update: BuildProgress) -> None:
        self._buildPhase = update.phase
        self._buildDetail = update.detail
        line = f"[{update.phase}] {update.detail}" if update.phase else update.detail
        self._buildLog = [*self._buildLog, line]
        _GUI_LOGGER.info(line)
        self.buildProgressChanged.emit()
        self.buildLogChanged.emit()

    def _on_build_result(self, ok: bool, error: str, output_path: Path | None) -> None:
        self._buildBusy = False
        line = (
            i18n.text(self._lang, "lbl_build_ok", path=str(output_path))
            if ok
            else i18n.text(self._lang, "lbl_build_failed", error=error)
        )
        self._buildLog = [*self._buildLog, line]
        (_GUI_LOGGER.info if ok else _GUI_LOGGER.error)(line)
        self.buildBusyChanged.emit()
        self.buildLogChanged.emit()

    # -- first-boot config ----------------------------------------------
    @Slot(str, str, str, str, bool, str, str, str, str, str, str, result=str)
    def saveFirstBootConfig(
        self,
        outDir: str,
        hostname: str,
        username: str,
        password: str,
        enableSsh: bool,
        wifiSsid: str,
        wifiPassword: str,
        wifiCountry: str,
        timezone: str,
        keyboard: str,
        locale: str,
    ) -> str:
        from .firstboot_config import FirstBootConfigError, build_boot_partition_patch

        wifi = WifiConfig(ssid=wifiSsid, psk=wifiPassword, country=wifiCountry or "US") if wifiSsid else None
        config = FirstBootConfig(
            hostname=hostname or None,
            username=username or None,
            password=password or None,
            enable_ssh=enableSsh,
            wifi=wifi,
            timezone=timezone or None,
            keyboard_layout=keyboard or None,
            locale=locale or None,
        )
        try:
            patch = build_boot_partition_patch(config)
        except FirstBootConfigError as exc:
            return f"error: {exc}"
        out = Path(outDir)
        out.mkdir(parents=True, exist_ok=True)
        script_path = out / patch.firstrun_path
        script_path.write_text(patch.firstrun_sh, encoding="utf-8", newline="\n")
        return f"ok: {script_path}"


def run_gui() -> int:
    log_path = _setup_file_logging()
    app = QGuiApplication.instance() or QGuiApplication([])
    app.setApplicationName("HYDRA-UMC-OS-REBUILDER")
    app.setApplicationDisplayName("HYDRA-UMC OS Rebuilder")
    # Real user feedback: this window had no real program icon at all
    # (task-bar/title-bar fell back to Qt's own generic default) - same
    # real HYDRA-UMC mark HYDRA-UMC-UPDATER's own launch_qt_gui() already
    # sets, using the exact same asset this repo already ships in
    # images/ but never wired up. Windows gets the native .ico; the SVG
    # is a safe fallback for a fresh checkout where the ICO hasn't been
    # generated yet.
    project_root = Path(__file__).resolve().parents[2]
    icon_path = project_root / "images" / "HYDRA_UMC_ICON.ico"
    if not icon_path.is_file():
        icon_path = project_root / "images" / "HYDRA_UMC_ICON.svg"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    engine = QQmlApplicationEngine()
    bridge = RebuilderBridge(log_path)
    engine.rootContext().setContextProperty("backend", bridge)
    qml_path = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    return app.exec()
