<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-OS-REBUILDER Banner" width="100%">
</p>

# 🏗️ HYDRA-UMC-OS-REBUILDER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | 🇩🇪 <b>Deutsch</b> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 📀 Ein flashbereites, vollständig aktuelles CM5-Image erstellen

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="PySide6 Qt Quick Desktop-GUI">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Windows und Linux">
</p>

> **Status: v0.1.7, Grundgerüst.** Die CLI, die Ökosystem-Erkennung, der
> Ersteinrichtungs-Generator und die GUI sind real und getestet. Der
> echte End-to-End-Image-Build (Download → Loop-Mount →
> Chroot-Installation → Unmount) ist implementiert, läuft aber nur auf
> einem echten Linux-Host mit Root-Rechten - siehe
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) für die genaue
> Plattformgrenze und warum sie existiert.

---

## 1. 🛠️ TECHNISCHER ÜBERBLICK

HYDRA-UMC-OS-REBUILDER ist ein Windows/Linux-Desktop-Tool - standardmäßig
mit Fenster-GUI, vollständige CLI mit `--cli` - das die Frage beantwortet,
die jede reale CM5-Bereitstellung irgendwann braucht: **"Baue mir ein
frisches SD-Karten-/eMMC-Image, mit der aktuellsten echten Version jedes
Ökosystem-Projekts bereits installiert, und lass mich WLAN/Benutzer/
Hostname/SSH einstellen, bevor ich es schreibe."**

Es tut drei echte Dinge:

1. **Prüft GitHub.** Jedes Repository im HYDRA-UMC/URTC-Ökosystem, dessen
   eigene `hydra-umc.project.json`
   `"deployment_target": "cm5"` deklariert, wird dynamisch entdeckt (nie
   eine feste Liste) und dessen aktuell veröffentlichte Version gelesen -
   indem es sich auf `hydra-umc-updater` als echte Bibliothek dafür
   verlässt, nicht auf eine zweite, unabhängig driftende
   Neuimplementierung des eigenen Erkennungscodes.
2. **Baut ein echtes Image.** Lädt ein fixiertes, checksummenverifiziertes
   Raspberry-Pi-OS-Basisimage herunter, mountet es per Loop-Device und
   installiert/aktualisiert jedes entdeckte Projekt, indem **das eigene
   `build.sh` dieses Projekts** innerhalb des Chroot des Images ausgeführt
   wird - niemals eine Neuimplementierung der eigenen Build-Schritte
   irgendeines Projekts.
3. **Schreibt echte Ersteinrichtungs-Konfiguration.** Hostname, ein neuer
   Benutzer mit einem echt mit `passlib` gehashten Passwort, WLAN,
   Zeitzone, Tastaturlayout und SSH - derselbe echte `firstrun.sh`-
   Mechanismus, den der eigene "OS Customisation"-Bildschirm von
   Raspberry Pi Imager auf einem Raspberry-Pi-OS-Image (Bookworm und
   neuer) verwendet, sodass sich die resultierende SD-Karte genau so
   verhält wie eine, die Raspberry Pi Imager selbst erzeugt hätte. Siehe
   [docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md).
4. **Prüft die eigene Ausgabe vor der Freigabe.** Bevor das erstellte
   Image an seinen endgültigen Pfad verschoben wird, wird das gemountete
   Root-Dateisystem auf ein echtes, in `wpa_supplicant.conf`/einem
   NetworkManager-Verbindungsprofil zurückgelassenes WLAN-Passwort, einen
   echten privaten SSH-Schlüssel, eine nicht leere Shell-Historie oder
   eine verirrte `.env`-Datei geprüft - jeder echte Fund blockiert die
   Freigabe vollständig, genau wie es ein Bereinigungsfehler bereits tut.
   Die Prüfsummenverifikation deckte nur den EINGANG (das Basis-Image)
   ab; dies ist die erste Prüfung dessen, was der Build-Vorgang selbst im
   AUSGANG hinterlässt.

```
$ hydra-umc-os-rebuilder --cli status
HYDRA-UMC-SERVER 0.4.8 (api/node)
HYDRA-UMC-VISION-STREAMER 0.0.3 (service/python)
HYDRA-UMC-GATEWAY-INDUSTRIAL 0.0.3 (api/node)
...
TOTAL=27

$ hydra-umc-os-rebuilder --cli config --out ./boot \
    --hostname hydra-umc-cm5 --username hydra-umc --password 'aendern' \
    --wifi-ssid MeinNetz --wifi-password 'wlan-pass' --wifi-country DE
CONFIG_WRITTEN out=boot firstrun=firstrun.sh
```

Ohne Argumente gestartet, öffnet es dieselben Informationen in einer Qt
Quick-Desktop-Oberfläche - unter Wiederverwendung derselben visuellen
Sprache wie HYDRA-UMC-UPDATER (gleiche dunkle Palette, Typografie und
Komponenten-Set) auf drei Tabs: Ökosystem-Status, Image erstellen und
Ersteinrichtung.

## 2. 🧱 ARCHITEKTUR UND DESIGN-ENTSCHEIDUNGEN

- **`ecosystem_plan.py` implementiert die GitHub-Erkennung niemals neu.**
  Es hängt von `hydra-umc-updater` als echtem Python-Paket ab
  (`hydra_umc_updater.github_client.discover_remote_projects()`) statt
  von einer zweiten Kopie seiner Manifest-Validierungs-/Retry-/Backoff-
  Logik - eine dort vorgenommene Korrektur oder Verbesserung kommt diesem
  Tool automatisch zugute.
- **`image_builder.py` implementiert den Build eines Projekts niemals
  neu.** Jedes Ökosystem-Projekt wird bei seiner eigenen echten fixierten
  Version geklont und durch Ausführen SEINES EIGENEN `build.sh`, im
  Chroot des Ziel-Rootfs, gebaut - dasselbe Prinzip "an das eigene
  Build-Skript jedes Projekts delegieren", das bereits das eigene
  `install.py` von `hydra-umc-updater` dokumentiert.
- **Die Linux/Root-Plattformgrenze wird immer zuerst geprüft.**
  `check_build_platform()` ist das Allererste, was `build_image()` tut -
  ein Build, der auf einem nicht unterstützten Host (Windows, ein
  Linux-Benutzer ohne Root, ein fehlendes `losetup`/`chroot`) still
  no-op'd, wäre schlimmer als einer, der mit einem klaren Grund die
  Ausführung verweigert.
- **`firstboot_config.py` ist ein reiner Generator ohne Nebeneffekte.** Es
  erzeugt nur reinen Textinhalt (einen `firstrun.sh`-String, einen
  `cmdline.txt`-Patch-String) - es berührt niemals ein echtes Image oder
  Dateisystem selbst, sodass es ohne Root oder ein echtes Image trivial
  testbar bleibt. Nur `image_builder.py` ist dafür verantwortlich, diesen
  Inhalt tatsächlich auf eine echte Boot-Partition zu schreiben.
- **Echtes SHA-512-Crypt-Passwort-Hashing, nicht das stdlib-Modul
  `crypt`.** `crypt` umschließt nur den eigenen libc-Aufruf des *Hosts*
  (nur Unix, und in Python 3.13 vollständig entfernt) - `passlib` erzeugt
  auf jeder Plattform, auf der dieses Tool läuft, einschließlich Windows,
  byte-identisch dasselbe echte `$6$...`-Format, das `chpasswd -e`
  erwartet.

## 📂 VERZEICHNISSTRUKTUR

```
HYDRA-UMC-OS-REBUILDER/
├── src/hydra_umc_os_rebuilder/
│   ├── ecosystem_plan.py    # Echter CM5-Projekt-/Versionsplan, aufgebaut auf der eigenen Erkennung von hydra_umc_updater
│   ├── firstboot_config.py  # Reiner firstrun.sh/cmdline.txt-Generator - kein Dateisystemzugriff
│   ├── image_builder.py     # Echte Download-/Loop-Mount-/Chroot-Installations-Pipeline, auf Linux/Root beschränkt
│   ├── i18n.py               # Echte, vollständige GUI-Übersetzungen (7 Sprachen)
│   ├── qt_gui.py             # Qt-Quick-Brücke über die echten CLI-seitigen Module oben
│   ├── qml/Main.qml          # Themenbasierte Desktop-Oberfläche: Ökosystem-Status / Image erstellen / Ersteinrichtung
│   └── main.py                # Dispatch: GUI standardmäßig, --cli für status/config/build-image
├── tests/                    # Echte Tests: firstboot_config, ecosystem_plan, i18n
├── docs/
│   ├── CLI_REFERENCE.md       # Befehlsreferenz
│   └── FIRST_BOOT_CONFIG.md   # Der echte firstrun.sh-Mechanismus, den dieses Tool nachbildet, und warum
├── images/                    # Medien, App-Icon und Banner
├── tools/
│   ├── build_test.py          # Nicht-versionierende Kompilierungsprüfung
│   └── ci_validate.py         # Manifest-/CHANGELOG-/Doku-Validierung, von der CI verwendet
├── build.sh / build.bat       # venv + editierbare Installation + Kompilierungsprüfung
├── run.sh / run.bat           # GUI standardmäßig / CLI-Einstiegspunkt
├── run-gui.vbs                # Windows-GUI-Launcher ohne Konsolenfenster
├── bump_version.py            # Ökosystemweiter Odometer-Bump (pyproject.toml + __init__.py)
└── bump_manifest_version.py   # Synchronisiert die Version von hydra-umc.project.json mit der nativen (--sync)
```

## ⚙️ BUILD- UND AUSFÜHRUNGSANLEITUNG

```bash
chmod +x build.sh   # einmalig
./build.sh          # erstellt .venv, pip install -e ".[dev,gui]", prüft Kompilierung, führt pytest aus
./run.sh                                # Fenster-GUI (Standard)
./run.sh --cli status                   # aktuellste echte GitHub-Version jedes Ökosystem-Projekts
./run.sh --cli config --out ./boot ...  # schreibt Ersteinrichtungs-Konfiguration (siehe docs/CLI_REFERENCE.md für jede Option)
./run.sh --cli build-image --out FILE   # baut ein flashbereites .img (nur Linux/Root)
```

Unter Windows: `build.bat`, dann `run.bat` (GUI) / `run.bat --cli status`
/ `run.bat --cli config ...`. `build-image` benötigt trotzdem einen
echten Linux-Host mit Root - siehe
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

**Fehlerbehebung**

- `--cli build-image` beendet sich mit `BUILD_BLOCKED reason=...`: den
  Grund lesen - er benennt das genau fehlende Element (nicht Linux, kein
  Root, oder ein bestimmtes fehlendes Tool im `PATH`) statt eines
  generischen Fehlers.
- `--cli config` wirft einen Validierungsfehler: der angegebene Hostname/
  Benutzername/WLAN-Ländercode entspricht nicht der echten, engen Form,
  die diese Felder erfordern - siehe die eigene Validierung von
  `firstboot_config.py`.
- Der Ökosystem-Status-Tab der GUI bleibt leer: Netzwerk prüfen - dieses
  Tool braucht eine echte Verbindung zu
  `github.com`/`raw.githubusercontent.com` für `status`/die Erkennung,
  genau wie `hydra-umc-updater` selbst.

## 🚀 ROADMAP

- Cloud-init-Unterstützung als alternativer Ersteinrichtungs-Mechanismus
  für ein Nicht-Pi-Basisimage, neben dem aktuellen `firstrun.sh`-Pfad.
- Inkrementelle Image-Updates (ein bestehendes `.img` patchen statt eines
  vollständigen Neubaus), sobald ein echter Bedarf über einen
  Von-Grund-auf-Build hinaus besteht.
- Ein `--json`-Ausgabemodus für `status`, zum Skripten dagegen.
- Eigenständige GUI-Executable (PyInstaller), nach derselben Konvention
  wie `build_exe.bat`/`.sh` von HYDRA-UMC-SUITE, für eine
  Doppelklick-Installation ohne `pip`/venv-Schritt.

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil des HYDRA-UMC-Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage tatsächlich eines dieser Projekte betreffen könnte statt dieses Repositorys.

**Direkt Verwandt**
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — die reproduzierbare Raspberry-Pi-OS-Produktschicht, von der dieses Tool tatsächlich ein Image baut: Nur-Lese-Agent, validierte Konfiguration/Profile, WLAN-Ersteinrichtungs-Provisioning.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — das Schwester-Tool für Ökosystem-Operationen, von dem dieses als echte Bibliothek für die GitHub-Erkennung abhängt - erkennt, installiert und aktualisiert manuell das gesamte Ökosystem auf einer bereits laufenden Maschine, während dieses Tool eine neue von Grund auf baut.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — Wartungsvorfall-Koordinator: eine Edge-Rolle mit niedrigem Privileg sammelt einen bereinigten Inventar-/Gesundheits-Snapshot, eine Control-Plane-Rolle rendert ihn schreibgeschützt und bittet einen KI-Anbieter um einen Diagnosevorschlag - wendet nie einen Patch an und stellt nie etwas bereit.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — reproduzierbarer Entwicklungshost (Raspberry Pi 5 / CM5), der den Quellcode des Ökosystems vorhält und begrenzte Build-/Test-Aufgaben über eine dauerhafte Warteschlange ausführt; eine dedizierte Entwicklerrolle, ausdrücklich kein operativer CM5.

**Ebenfalls Teil des Ökosystems**

*Hardware- und Plattform-Kern*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — der gemeinsame JSON-Schema-Vertrag und die Sicherheits-Gate-Grenze, gegen die jede Bridge ihre Befehle validiert.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — deklaratives Adapter-Manifest-Register und Validator für Konnektoren externer Maschinen; erweitert die eigene Vertragsidee des SDK auf externe Maschinen, ohne die Industrie-Gateway-Projekte zu ersetzen.

*Kern-Backend und Clients*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — die physische Hauptplatine des Roboterarms: CM5-Host + Dual-Core-STM32H745, der bis zu 8 Werkzeugarme über CAN-OTA/SPI-OTA koordiniert.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das echte kopflose Backend (REST/WebSocket), mit dem jeder Steuerungsclient tatsächlich spricht.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — Web-Steuerungs-Dashboard mit Echtzeit-3D-Visualisierung mehrerer Roboter.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Schwarm-Kommandozentrale (PySide6) für mehrere Server gleichzeitig.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischem Login und gekoppeltem Wear-OS-Begleiter.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisation.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-Oberfläche für den eingebauten 7"-DSI-Touchscreen direkt auf der CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Editor/-Ersteller, der fertige Modelle in den eigenen Katalog von STUDIO überträgt.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsgrenze für AGV-/AMR-Flotten über einen echten VDA-5050-MQTT-Publisher.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — hochrangiger CNC-Zellenkoordinator mit echtem GRBL-Status-/Steuerbyte-Zugriff.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsgrenze für beinige/humanoide Droiden, mit einem echten Boston-Dynamics-Spot-Befehlssender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Sicherheitskoordinator für Laserzellen, der 3 echte Schlüssel-/Gehäuse-/Verriegelungs-GPIO-Sicherungen liest.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer hochrangiger Board-Flow-Koordinator für OpenPnP-Pick-and-Place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsgrenze für Moonraker-/Klipper-3D-Drucker, mit real gesperrten Job-Befehlen.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Sicherheitskoordinator mit einem echten, verzögert importierten rclpy-ROS-2-Transport.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsgrenze für kameraausgestattete UAVs, mit einem echten MAVLink-Befehlssender.

*URTC-Werkzeugplattform*
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-GUI-Flash-Tool für URTC-Boards, CAN-OTA plus vollständiges SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Live-CAN-Bus-Diagnose-Tool für URTC-Boards, ein Panel pro Werkzeugprofil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, keine lokale Installation nötig.

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrations-Hub für die Hailo-8-Vision-Pipeline, mit einer echten Hardware-Bereitschaftsprüfung pro Stufe.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echtes Registry für kompilierte Modelle mit sicherer Hailo-Architektur-/Checksummenprüfung.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echter GStreamer-Pipeline- + MediaMTX-Konfigurationsgenerator mit echter HailoRT-Integrationsgrenze.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — echtes Position-Based-Visual-Servoing-Korrekturgesetz, sicherheitsgegated durch vorgelagerten Zonenstatus.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — echte Zonenverletzungsprüfung und Notaus-Anforderung, mit Durchsetzung der Kalibrierungsaktualität.

*Kognitiver KI-Knoten (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Integrations-Hub für die kognitive Hailo-10-Pipeline (LLM-/VLA-/Sprach-Orchestrierung).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — echte Aktions-Token-Codierung/-Decodierung und Trajektoriengenerierung für ein Vision-Language-Action-Modell.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — echtes Sprach-Frontend (VAD + Intent-Parser) mit einem begrenzten, bestätigungspflichtigen Watch-Relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — echte regelbasierte Aufgabenzerlegung und semantische Fehlerbehebung über MCU-Fehlercodes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — echte, nur-stdlib-basierte TF-IDF-Dokumentensuche über die eigene Markdown-Dokumentation dieses Ökosystems.

*Orchestrierung und Schwarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — Integrations-Hub mit einem echten gRPC-/Protobuf-Health-Report-Vertrag und Missions-Zustandsautomat.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — echte prioritätsbasierte Job-Queue mit Deduplizierung, über eine echte HTTP-API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — echter gRPC-basierter Flotten-Gesundheits-Watchdog mit Retry/Backoff und Identitätsabweichungserkennung.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — echter RRT-basierter 3D-Pfadplaner mit echter Hindernis-/Arbeitsraum-Kollisionsvalidierung.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — echte CRDT-LWW-Element-Map-Zustandssynchronisation, eigenschaftsgetestet für Multi-Zellen-Konvergenz.

*Digitaler Zwilling und Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — Integrations-Hub für die Digital-Twin-Engine, mit einem echten Versions-Kompatibilitäts-Synchronisationsvertrag.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — echte Hardware-in-the-Loop-Sicherheitsverriegelung, die Befehle zwischen Simulation und echter Hardware routet.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — echte Vorwärtskinematik und Gelenkgrenzenvalidierung über eine echte URDF-Teilmenge.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — echter prozeduraler 2D-Szenengenerator mit YOLO-/COCO-Annotationsexport.

*Daten und Analytik*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — echter sqlite3-gestützter Zeitreihenspeicher mit einer echten Ingest-/Query-HTTP-API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — echter FFT- + statistischer Baseline-Anomaliedetektor mit Drift-Überwachung.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — echte OEE-/Verfügbarkeitsberechnung über die DATALAKE-Historie, mit reproduzierbarem CSV-Export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — echte CAN-/WebSocket-Ingestion-Pipeline nach DATALAKE, mit Sequenz-Deduplizierung.

*Industrie-Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — Integrations-Hub, der zu Industrieprotokollen weiterleitet, mit einer echten Befehls-Allowlist-/Backpressure-Schicht.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — echter OPC-UA-Adressraum, verifiziert mit einer echten Client-Sitzung im Binärprotokoll.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — echter MQTT-Broker mit optionaler Client-Authentifizierung und Topic-ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — echte MTConnect-XML-Endpunkte `/probe` und `/current` mit Ausgabe im Degraded-Modus.

*Ergänzende Tools und Ökosystem-Operationen*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart-Summaries- und Anomaly-Highlighting-Panels über DATALAKE/ANOMALY-DETECTOR, mit einem ehrlichen statistischen Fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — Flotten-CLI mit einem echten, stabilen Exit-Code-Vertrag, ein echter Live-Client der eigenen API von HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleiter-App mit echten haptischen Alarmen und einem Sprach-Relay zum gekoppelten Telefon.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Board-Montage-Rack mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen thermischen/RGB-Inspektionswerkzeugkopf.

---

## 📚 Dokumentation und Community

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — jeder `--cli`-Unterbefehl, mit echter Beispielausgabe.
- **[docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md)** — der echte `firstrun.sh`-Mechanismus, den dieses Tool nachbildet, und warum.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Technologie-Stack und Coding-Richtlinien für einen Pull Request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — die in dieser Community erwarteten Verhaltensstandards.
- **[SECURITY.md](SECURITY.md)** — wie man eine Schwachstelle meldet, und die echten Sicherheitsschwerpunkte dieses Projekts.
- **[SUPPORT.md](SUPPORT.md)** — wo man Fragen stellt und Bugs meldet.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LIZENZ

GPL-3.0 (Software) / CC BY-SA 4.0 (Dokumentation) - siehe [LICENSE.md](LICENSE.md).
