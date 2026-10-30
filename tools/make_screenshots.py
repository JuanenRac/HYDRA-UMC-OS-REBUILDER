# =============================================================================
# HYDRA-UMC-OS-REBUILDER - tools/make_screenshots.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Takes the screenshots of the README: the real Qt Quick window, without a window on the desktop (the offscreen Qt platform and the software
# renderer), with a made-up list of projects instead of the one the program fetches from GitHub. Nothing real is behind the pictures, and nothing
# is sent to any network.
#
#   python tools/make_screenshots.py              writes images/screenshots/<name>.png at 1920x1080
#   python tools/make_screenshots.py --out DIR    writes them in DIR instead, to look at them before they replace the ones in the repository
#
# It takes no mouse or keyboard of the desktop. Run it from the repository root, with the interpreter of the project (the one that has PySide6).
# =============================================================================
import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"))   # the offscreen platform finds no fonts by itself
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication, QWindow  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402,F401  (so that the window comes back as a Quick window, which can grab itself)

from hydra_umc_os_rebuilder import qt_gui  # noqa: E402
from hydra_umc_os_rebuilder.ecosystem_plan import EcosystemPlanEntry  # noqa: E402

PROJECTS = [
    ("HYDRA-UMC-SERVER", "0.8.0.3", "server", "stack-b"), ("HYDRA-UMC-STUDIO", "0.8.0.3", "web interface", "stack-b"), ("HYDRA-UMC-DATALAKE", "0.8.0.3", "time-series store", "stack-b"),
    ("HYDRA-UMC-MQTT-BROKER", "0.8.0.3", "message broker", "stack-b"), ("HYDRA-UMC-VOICE-UI", "0.8.0.3", "voice interface", "stack-b"), ("HYDRA-UMC-DASHBOARD-AI", "0.8.0.3", "dashboard", "stack-b"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(HERE / "images" / "screenshots"))
    out = Path(parser.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    bridge = qt_gui.RebuilderBridge(Path("rebuilder.log"))
    engine.rootContext().setContextProperty("backend", bridge)
    engine.load(QUrl.fromLocalFile(str(HERE / "src" / "hydra_umc_os_rebuilder" / "qml" / "Main.qml")))
    if not engine.rootObjects():
        print("SCREENSHOTS=FAIL the window did not load")
        return 1
    root = engine.rootObjects()[0]
    root.setVisibility(QWindow.Visibility.Windowed)   # the window opens maximized: here it gets the size of the pictures instead
    root.resize(1920, 1080)
    root.show()
    entries = [EcosystemPlanEntry(name=name, version=version, role=role, stack=stack, git_url=f"https://github.com/example/{name}.git") for name, version, role, stack in PROJECTS]
    bridge._planResult.emit(entries, [])
    root.setProperty("buildTarget", "local")   # the form of this computer: the one of the remote host starts with the address of the real CM5
    for _ in range(20):
        app.processEvents()
    path = out / "overview.png"
    image = root.grabWindow()
    image.save(str(path))
    print("wrote", path, image.width(), "x", image.height())
    return 0


if __name__ == "__main__":
    sys.exit(main())
