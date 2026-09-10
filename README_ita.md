<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="Banner HYDRA-UMC-OS-REBUILDER" width="100%">
</p>

# 🏗️ HYDRA-UMC-OS-REBUILDER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | 🇮🇹 <b>Italiano</b> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 📀 Costruisci un'Immagine CM5 Pronta da Scrivere e Completamente Aggiornata

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="GUI desktop PySide6 Qt Quick">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Windows e Linux">
</p>

> **Stato: v0.1.7, scheletro.** La CLI, la scoperta dell'ecosistema, il
> generatore di configurazione del primo avvio e la GUI sono reali e
> testati. La costruzione reale dell'immagine end-to-end (download →
> montaggio loop → installazione in chroot → smontaggio) è implementata
> ma funziona solo su un vero host Linux con permessi root - vedi
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) per il limite esatto di
> piattaforma e il perché esiste.

---

## 1. 🛠️ PANORAMICA TECNICA

HYDRA-UMC-OS-REBUILDER è uno strumento desktop Windows/Linux - GUI in
finestra per impostazione predefinita, CLI completa con `--cli` - che
risponde alla domanda che ogni distribuzione reale su CM5 finisce per
porsi: **"costruiscimi un'immagine fresca di scheda SD/eMMC, con la
versione reale più recente di ogni progetto dell'ecosistema già
installata, e lasciami configurare Wi-Fi/utente/hostname/SSH prima di
scriverla."**

Fa tre cose reali:

1. **Interroga GitHub.** Ogni repository dell'ecosistema HYDRA-UMC/URTC il
   cui proprio `hydra-umc.project.json` dichiara
   `"deployment_target": "cm5"` viene scoperto dinamicamente (mai un
   elenco fisso) e ne viene letta la versione pubblicata attuale -
   dipendendo da `hydra-umc-updater` come vera libreria per questo, non
   una seconda implementazione che potrebbe divergere silenziosamente dal
   proprio codice di scoperta.
2. **Costruisce un'immagine reale.** Scarica un'immagine base Raspberry
   Pi OS fissata e verificata tramite checksum, la monta in loop, e
   installa/aggiorna ogni progetto scoperto eseguendo **il `build.sh`
   proprio di quel progetto** all'interno del chroot dell'immagine - mai
   una reimplementazione dei passi di build di alcun progetto.
3. **Scrive una configurazione reale di primo avvio.** Hostname, un nuovo
   utente con una password realmente sottoposta ad hash da `passlib`,
   Wi-Fi, fuso orario, layout di tastiera e SSH - lo stesso meccanismo
   reale `firstrun.sh` usato dalla schermata "OS Customisation" di
   Raspberry Pi Imager su un'immagine Raspberry Pi OS (Bookworm e
   successive), così la scheda SD risultante si comporta esattamente come
   una che avrebbe prodotto lo stesso Raspberry Pi Imager. Vedi
   [docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md).
4. **Analizza il proprio output prima di pubblicarlo.** Prima che
   l'immagine costruita venga spostata nel suo percorso finale, il
   rootfs montato viene controllato alla ricerca di una vera password
   Wi-Fi lasciata in `wpa_supplicant.conf`/un profilo di connessione
   NetworkManager, una vera chiave SSH privata, una cronologia della
   shell non vuota, o un file `.env` abbandonato - qualsiasi risultato
   reale blocca del tutto la pubblicazione, allo stesso modo di un
   fallimento della pulizia. La verifica del checksum copriva solo
   l'INGRESSO (l'immagine base); questo è il primo controllo su ciò che
   la stessa costruzione lascia nell'USCITA.

```
$ hydra-umc-os-rebuilder --cli status
HYDRA-UMC-SERVER 0.4.8 (api/node)
HYDRA-UMC-VISION-STREAMER 0.0.3 (service/python)
HYDRA-UMC-GATEWAY-INDUSTRIAL 0.0.3 (api/node)
...
TOTAL=27

$ hydra-umc-os-rebuilder --cli config --out ./boot \
    --hostname hydra-umc-cm5 --username hydra-umc --password 'da-cambiare' \
    --wifi-ssid LaMiaRete --wifi-password 'pass-wifi' --wifi-country IT
CONFIG_WRITTEN out=boot firstrun=firstrun.sh
```

Eseguito senza argomenti apre le stesse informazioni in una shell desktop
Qt Quick - riutilizzando lo stesso linguaggio visivo di
HYDRA-UMC-UPDATER (stessa palette scura, tipografia e set di componenti)
su tre schede: Stato dell'Ecosistema, Crea Immagine e Configurazione
Primo Avvio.

## 2. 🧱 ARCHITETTURA E DECISIONI DI PROGETTAZIONE

- **`ecosystem_plan.py` non reimplementa mai la scoperta di GitHub.**
  Dipende da `hydra-umc-updater` come vero pacchetto Python
  (`hydra_umc_updater.github_client.discover_remote_projects()`) invece
  di una seconda copia della sua logica di validazione manifesto/
  retry/backoff - una correzione o un miglioramento fatto lì beneficia
  automaticamente questo strumento.
- **`image_builder.py` non reimplementa mai la build di un progetto.**
  Ogni progetto dell'ecosistema viene clonato alla propria versione reale
  fissata e costruito eseguendo il SUO PROPRIO `build.sh`, in chroot
  dentro il rootfs di destinazione - lo stesso principio "delega allo
  script di build proprio di ogni progetto" già documentato dal proprio
  `install.py` di `hydra-umc-updater`.
- **Il limite di piattaforma Linux/root viene sempre controllato per
  primo.** `check_build_platform()` è la primissima cosa che fa
  `build_image()` - una build che fallisce silenziosamente su un host non
  supportato (Windows, un utente Linux senza root, un `losetup`/`chroot`
  mancante) sarebbe peggio di una che rifiuta di partire con un motivo
  chiaro.
- **`firstboot_config.py` è un generatore puro senza effetti
  collaterali.** Produce solo contenuto di file in testo semplice (una
  stringa `firstrun.sh`, una stringa di patch per `cmdline.txt`) - non
  tocca mai un'immagine o un filesystem reale, quindi resta banalmente
  testabile senza root né un'immagine reale. Solo `image_builder.py` è
  responsabile di scrivere davvero quel contenuto su una partizione boot
  reale.
- **Hashing password SHA-512-crypt reale, non il modulo `crypt` della
  stdlib.** `crypt` avvolge solo la chiamata libc propria dell'*host*
  (solo Unix, e rimosso del tutto in Python 3.13) - `passlib` produce lo
  stesso formato reale `$6$...` byte per byte che si aspetta
  `chpasswd -e`, su qualunque piattaforma su cui gira questo strumento,
  Windows incluso.

## 📂 STRUTTURA DELLE DIRECTORY

```
HYDRA-UMC-OS-REBUILDER/
├── src/hydra_umc_os_rebuilder/
│   ├── ecosystem_plan.py    # Piano reale progetti/versioni CM5, costruito sulla scoperta propria di hydra_umc_updater
│   ├── firstboot_config.py  # Generatore puro firstrun.sh/cmdline.txt - nessun accesso al filesystem
│   ├── image_builder.py     # Pipeline reale download/montaggio loop/installazione chroot, limitata a Linux/root
│   ├── i18n.py               # Traduzioni reali e complete della GUI (7 lingue)
│   ├── qt_gui.py             # Bridge Qt Quick sui moduli reali sopra, gli stessi usati dalla CLI
│   ├── qml/Main.qml          # Shell desktop a tema: Stato dell'Ecosistema / Crea Immagine / Configurazione Primo Avvio
│   └── main.py                # Dispatch: GUI predefinita, --cli per status/config/build-image
├── tests/                    # Test reali: firstboot_config, ecosystem_plan, i18n
├── docs/
│   ├── CLI_REFERENCE.md       # Riferimento comandi
│   └── FIRST_BOOT_CONFIG.md   # Il meccanismo reale firstrun.sh riprodotto da questo strumento, e perché
├── images/                    # Risorse, icona dell'app e banner
├── tools/
│   ├── build_test.py          # Verifica di compilazione senza versionamento
│   └── ci_validate.py         # Validazione manifesto/CHANGELOG/documentazione usata dalla CI
├── build.sh / build.bat       # venv + installazione editabile + verifica compilazione
├── run.sh / run.bat           # GUI predefinita / punto di ingresso CLI
├── run-gui.vbs                # Launcher grafico Windows senza finestra console
├── bump_version.py            # Incremento tipo odometro per tutto l'ecosistema (pyproject.toml + __init__.py)
└── bump_manifest_version.py   # Sincronizza la versione di hydra-umc.project.json con quella nativa (--sync)
```

## ⚙️ GUIDA A COMPILAZIONE ED ESECUZIONE

```bash
chmod +x build.sh   # una tantum
./build.sh          # crea .venv, pip install -e ".[dev,gui]", verifica compilazione, esegue pytest
./run.sh                                # GUI in finestra (predefinita)
./run.sh --cli status                   # versione reale GitHub più recente di ogni progetto dell'ecosistema
./run.sh --cli config --out ./boot ...  # scrive la configurazione di primo avvio (vedi docs/CLI_REFERENCE.md per ogni opzione)
./run.sh --cli build-image --out FILE   # costruisce un .img pronto da scrivere (solo Linux/root)
```

Su Windows: `build.bat`, poi `run.bat` (GUI) / `run.bat --cli status` /
`run.bat --cli config ...`. `build-image` richiede comunque un vero host
Linux con root - vedi [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

**Risoluzione dei problemi**

- `--cli build-image` termina con `BUILD_BLOCKED reason=...`: leggi il
  motivo - indica esattamente l'elemento mancante (non Linux, non root, o
  uno strumento specifico mancante nel `PATH`) invece di un fallimento
  generico.
- `--cli config` solleva un errore di validazione: l'hostname/username/
  codice paese Wi-Fi indicato non rispetta la forma reale e rigorosa
  richiesta da quei campi - vedi la validazione propria di
  `firstboot_config.py`.
- La scheda Stato dell'Ecosistema della GUI resta vuota: controlla la tua
  rete - questo strumento ha bisogno di una vera connessione a
  `github.com`/`raw.githubusercontent.com` per `status`/la scoperta,
  come lo stesso `hydra-umc-updater`.

## 🚀 ROADMAP

- Supporto cloud-init come meccanismo alternativo di primo avvio per
  un'immagine base non-Pi, accanto all'attuale percorso `firstrun.sh`.
- Aggiornamenti incrementali dell'immagine (applicare una patch a un
  `.img` esistente invece di una ricostruzione completa) quando ci sarà
  un reale bisogno oltre a una build da zero.
- Una modalità di output `--json` per `status`, per l'uso da script.
- Eseguibile GUI standalone (PyInstaller), seguendo la stessa convenzione
  di `build_exe.bat`/`.sh` di HYDRA-UMC-SUITE, per un'installazione con
  doppio clic senza alcun passaggio `pip`/venv.

## 🔗 Progetti Correlati

Questo progetto fa parte dell'ecosistema robotico HYDRA-UMC dello stesso autore (JuanenRac / Electro Hobby 3D). Utile da conoscere, poiché una richiesta potrebbe in realtà riguardare uno di questi invece di questo repository.

**Direttamente Correlati**
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — lo strato prodotto riproducibile di Raspberry Pi OS di cui questo strumento costruisce davvero un'immagine: agente in sola lettura, configurazione/profili validati, provisioning Wi-Fi al primo contatto.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — lo strumento gemello di operazioni dell'ecosistema da cui questo dipende come vera libreria per la scoperta GitHub - rileva, installa e aggiorna manualmente l'intero ecosistema su una macchina già in funzione, mentre questo strumento ne costruisce una nuova da zero.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinatore di incidenti di manutenzione: un ruolo edge a basso privilegio raccoglie uno snapshot di inventario/salute sanificato, un ruolo control-plane lo rende in sola lettura e chiede a un provider di IA di suggerire una diagnosi - non applica mai una patch né distribuisce nulla.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — host di sviluppo riproducibile (Raspberry Pi 5 / CM5) che conserva il codice sorgente dell'ecosistema ed esegue attività delimitate di build/test tramite una coda durevole; un ruolo di sviluppo dedicato, esplicitamente distinto da un CM5 operativo.

**Anche Parte dell'Ecosistema**

*Nucleo Hardware e Piattaforma*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — il contratto condiviso JSON-Schema e il limite del gate di sicurezza contro cui ogni bridge valida i propri comandi.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registro dichiarativo e validatore di manifesti adattatore per connettori di macchine esterne; estende la propria idea di contratto dell'SDK alle macchine esterne senza sostituire i progetti di gateway industriale.

*Backend e Client Principali*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la scheda madre fisica del braccio robotico: host CM5 + coprocessore STM32H745 dual-core, che coordina fino a 8 bracci-utensile via CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — il vero backend headless (REST/WebSocket) con cui parla davvero ogni client di controllo.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — cruscotto di controllo web con visualizzazione 3D multi-robot in tempo reale.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro di comando sciame desktop (PySide6) per più server contemporaneamente.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app di controllo Android nativa con login biometrico e compagno Wear OS abbinato.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app di controllo iOS/iPadOS (Flutter) con sincronizzazione WebSocket in tempo reale.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaccia touch nativa per il touchscreen DSI da 7" integrato sulla stessa CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creatore/editor grafico desktop di URDF che invia i modelli finiti nel catalogo proprio di STUDIO.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — confine di coordinamento per flotte AGV/AMR tramite un vero publisher MQTT VDA 5050.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinatore di cella CNC di alto livello con vero accesso a stato/byte di controllo GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — confine di coordinamento per droidi con zampe/umanoidi, con un vero invio di comandi Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinatore di sicurezza per cella laser che legge 3 vere protezioni GPIO chiave/recinzione/interlock.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinatore sicuro di alto livello del flusso schede per il pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — confine di coordinamento sicuro per stampanti 3D Moonraker/Klipper, con comandi di lavoro realmente controllati.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinatore di sicurezza con un vero trasporto rclpy ROS 2, importato in modo lazy.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — confine di coordinamento per UAV dotati di telecamera, con un vero invio di comandi MAVLink.

*Piattaforma Strumenti URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware per la scheda fisica Universal Robot Tool Controller, 25+ profili utensile su bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — strumento desktop con GUI per flashare schede URTC, CAN-OTA più SWD/JTAG a chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — strumento desktop di diagnostica bus CAN in tempo reale per schede URTC, un pannello per profilo utensile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa via browser a URTC-TESTER tramite la Web Serial API, senza installazione locale.

*Nodo Vision AI (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub di integrazione per la pipeline di visione Hailo-8, con un vero controllo di prontezza hardware per stadio.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro reale di modelli compilati con verifica sicura di architettura/checksum Hailo.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generatore reale di pipeline GStreamer + configurazione MediaMTX con un vero confine di integrazione HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — vera legge di correzione Position-Based Visual Servoing, con gate di sicurezza basato sullo stato di zona a monte.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — vero controllo di violazione zona e richiesta di arresto di emergenza, con obbligo di calibrazione aggiornata.

*Nodo Cognitivo AI (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub di integrazione per la pipeline cognitiva Hailo-10 (orchestrazione LLM/VLA/voce).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vera codifica/decodifica di token d'azione e generazione di traiettoria per un modello Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vero front-end vocale (VAD + parser di intenti) con un relay al Watch limitato e soggetto a conferma.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vera scomposizione di task basata su regole e recupero semantico degli errori sui codici di errore dell'MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vera ricerca documentale TF-IDF solo stdlib sulla documentazione Markdown propria di questo ecosistema.

*Orchestrazione e Sciame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub di integrazione con un vero contratto di health-report gRPC/Protobuf e macchina a stati di missione.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vera coda di lavori basata su priorità con deduplicazione, su una vera API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vero watchdog di salute flotta basato su gRPC con retry/backoff e rilevamento di identità non corrispondente.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vero pianificatore di percorso 3D basato su RRT con validazione reale di collisione ostacolo/spazio di lavoro.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vera sincronizzazione di stato CRDT LWW-Element-Map, testata a proprietà per la convergenza multi-cella.

*Gemello Digitale e Simulazione*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub di integrazione per il motore di gemello digitale, con un vero contratto di sincronizzazione di compatibilità versione.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — vero interlock di sicurezza hardware-in-the-loop, che instrada i comandi tra simulazione e hardware reale.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — vera cinematica diretta e validazione dei limiti di giunto su un vero sottoinsieme URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — vero generatore procedurale di scene 2D con esportazione di annotazioni YOLO/COCO.

*Dati e Analytics*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vero archivio di serie temporali su sqlite3 con una vera API HTTP di ingest/query.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vero rilevatore di anomalie con FFT + baseline statistica con monitoraggio della deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vero calcolo OEE/disponibilità sullo storico DATALAKE, con esportazione CSV riproducibile.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vera pipeline di ingest CAN/WebSocket verso DATALAKE, con deduplicazione per sequenza.

*Gateway Industriale*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub di integrazione che inoltra verso protocolli industriali, con un vero livello di allowlist comandi/backpressure.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vero address space OPC-UA, verificato con una vera sessione client di protocollo binario.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vero broker MQTT con autenticazione opzionale per client e ACL sui topic.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — veri endpoint XML `/probe` e `/current` MTConnect con output in modalità degradata.

*Strumenti Complementari e Operazioni dell'Ecosistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — pannelli Smart Summaries e Anomaly Highlighting su DATALAKE/ANOMALY-DETECTOR, con un fallback statistico onesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI di flotta con un vero contratto di exit-code stabile, un genuino client live della propria API di HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app compagna WearOS con vere notifiche aptiche e un relay vocale al telefono abbinato.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware per un rack di montaggio schede con vera decodifica ID utensile e logica di pre-riscaldamento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware più un vero compagno di visione Python per una testa di ispezione termica/RGB.

---

## 📚 Documentazione e Comunità

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — ogni sottocomando `--cli`, con output di esempio reale.
- **[docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md)** — il meccanismo reale `firstrun.sh` riprodotto da questo strumento, e perché.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnologico e linee guida di codice per una pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — gli standard di comportamento attesi in questa comunità.
- **[SECURITY.md](SECURITY.md)** — come segnalare una vulnerabilità, e le vere aree di sicurezza di questo progetto.
- **[SUPPORT.md](SUPPORT.md)** — dove porre domande e segnalare bug.

## 👤 AUTORE
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENZA

GPL-3.0 (software) / CC BY-SA 4.0 (documentazione) - vedi [LICENSE.md](LICENSE.md).
