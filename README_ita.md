<!-- =============================================================================
HYDRA-UMC-OS-REBUILDER - Builds a ready-to-flash CM5 image
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-OS-REBUILDER banner" width="100%">
</p>

# 📀 HYDRA-UMC-OS-REBUILDER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | 🇮🇹 <b>Italiano</b> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 📀 Costruisci un'Immagine CM5 Pronta da Scrivere e Completamente Aggiornata

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="Desktop">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Tests-187%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.3.3-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

> **Stato di sicurezza (safety e security):** questo ecosistema non è un sistema di sicurezza certificato. Non esiste ancora un percorso E-STOP hardware, né limiti o interblocchi imposti dal firmware, né un comando di movimento verificato; le immagini firmware sono controllate con CRC-32 e una firma Ed25519, e una compilazione di rilascio rifiuta le chiavi di sviluppo pubblicate (le teste utensile e le schede di espansione dietro il relè usano ancora i bootloader di URTC, che accettano un HMAC-SHA256 a chiave condivisa invece di una firma); TLS e TLS reciproco sono opzionali e disattivati per impostazione predefinita; nessuna scheda propria è stata ancora assemblata o provata. Leggi la [base di sicurezza](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e il [modello delle minacce](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) prima di fidarti di qualsiasi affermazione qui per la sicurezza di una persona.

---

## 📋 In breve

| | |
|---|---|
| Versione | `0.3.3` |
| Maturità | Funzionale |
| Test | 187 (`python -m pytest -q tests`) |
| Tecnologia | Python 3.10+ / PySide6 / QML / Raspberry Pi OS / GitHub raw content |
| Destinazione | Il PC di chi lo usa |
| Su hardware reale | Non ancora: per questa versione non risulta alcuna esecuzione su hardware reale |

**Vai a:** [Panoramica](#-panoramica) · [Architettura](#-architettura) · [Sicurezza e protezione](#-sicurezza-e-protezione) · [Avvio rapido](#-avvio-rapido) · [Test](#-test) · [Struttura del repository](#-struttura-del-repository) · [Progetti correlati](#-progetti-correlati)

## 🚦 Stato del progetto

Ogni riga è una parte di questo repository e il semaforo dice a che punto è oggi. È scritta in base a ciò che il repository può mostrare (test, compilazioni, esecuzioni), non a ciò che è previsto.

🟢 Fatto e verificato · 🟡 Funziona, con limiti noti · 🟠 Fatto a metà o non ancora verificato · 🔴 Non fatto o non funzionante

| Area | Stato | Cosa significa qui |
|---|---|---|
| Software | 🟡 | Funziona per il suo scopo principale; la verifica di onestà qui sopra elenca ciò che manca ancora |
| Test | 🟢 | 187 test automatici, eseguiti a ogni modifica |
| Hardware reale | 🔴 | Non ancora: per questa versione non risulta alcuna esecuzione su hardware reale |
| Documentazione | 🟢 | README in otto lingue, verificato rispetto al manifesto a ogni modifica |

## 🎯 Panoramica

HYDRA-UMC-OS-REBUILDER è uno strumento desktop Windows/Linux - GUI in
finestra per impostazione predefinita, CLI completa con `--cli` - che
risponde alla domanda che ogni distribuzione reale su CM5 finisce per
porsi: **"costruiscimi un'immagine fresca di scheda SD/eMMC, con la
versione reale più recente di ogni progetto dell'ecosistema già
installata, e lasciami configurare Wi-Fi/utente/hostname/SSH prima di
scriverla."**

**Cosa contiene l'immagine:** le copie dei progetti in `/opt/hydra-umc/<nome>` alle versioni previste e ciò che la compilazione di ciascun progetto vi ha prodotto. Non crea utenti di servizio né unità systemd e non prepara `/etc/hydra-umc`, quindi nessun servizio parte da solo al primo avvio; gli script di provisioning di HYDRA-UMC-OS vanno comunque eseguiti sulla scheda.

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
   Raspberry Pi Imager su un'immagine Raspberry Pi OS (Trixie e
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

## 🧩 Ruolo in HYDRA-UMC

**HYDRA-UMC-OS-REBUILDER** costruisce una nuova immagine della CM5 con la versione attuale di ogni progetto dell'ecosistema già inclusa, e scrive le impostazioni del primo avvio (Wi-Fi, utente, nome host, SSH) prima di scrivere l'immagine. Lo strato di piattaforma che l'immagine porta è descritto da `HYDRA-UMC-OS`.

## 🏛️ Architettura

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-OS-REBUILDER architecture" width="100%">
</p>

### ARCHITETTURA E DECISIONI DI PROGETTAZIONE

- **Chiave SSH della macchina fissata al primo uso e nessun paese Wi-Fi predefinito.** Una build remota rifiuta una macchina di cui non ha fissato la chiave e mostra l'impronta SHA-256 della chiave; inserisci quell'impronta (verificata sulla macchina stessa) e la chiave viene fissata: da allora si accetta solo quella chiave e una diversa viene rifiutata come chiave cambiata. Il codice paese Wi-Fi dell'immagine non ha più un valore predefinito (`--wifi-country` / il campo paese è obbligatorio con una rete Wi-Fi), perché fissa le regole radio del paese in cui sarà la macchina.
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
- **Una configurazione di primo avvio che chiuderebbe fuori l'operatore viene rifiutata, non costruita.** Disattivare SSH senza configurare alcun account lascerebbe le immagini di base ufficiali di questo stesso strumento (nessun utente predefinito da Trixie in poi) senza alcun modo di accesso - rifiutato a meno che `acknowledge_no_remote_access=True` non lo accetti esplicitamente. `describe_recovery_procedure()` indica il vero percorso di recupero per ciò che la configurazione lascia aperto.
- **Le password non viaggiano più come argomenti.** `--password` e `--wifi-password` funzionano ancora, ma una riga di comando è visibile a ogni utente della macchina e `sudo` la scrive nel registro di autenticazione; la CLI le legge quindi anche da `HYDRA_UMC_FIRSTBOOT_PASSWORD` / `HYDRA_UMC_FIRSTBOOT_WIFI_PASSWORD` o, con `--secrets-stdin`, da un oggetto JSON (`{"password": "...", "wifiPassword": "..."}`) sullo standard input. La build remota (SSH) della GUI le invia così e non le mette più nel comando eseguito.
- **Il chroot è completo e la compilazione remota è fissata.** La compilazione monta `/proc`, `/sys`, `/dev` e `/dev/pts` nell'immagine e le dà la risoluzione dei nomi dell'host mentre i progetti vengono compilati (il `resolv.conf` proprio dell'immagine viene rimesso dopo), così `pip`, `npm` e `go` raggiungono la rete dal chroot. Una compilazione remota via SSH installa questo strumento dal tag della versione in esecuzione (`HYDRA_UMC_REBUILDER_REMOTE_REF` indica un altro tag o commit) e compila dal profilo congelato del piano esaminato (`profile-build`) invece di riscoprire l'ecosistema sull'host remoto. Niente di tutto ciò è ancora stato eseguito su un host Linux reale con root.
- **Un profilo congelato è una vera ricetta persistente, mai riscaricata.** `freeze_profile()`/`profile-build` di `profile_manifest.py` fissano ogni progetto allo SHA esatto del commit con cui è stato provato - una build successiva non sostituisce mai in silenzio ciò che GitHub chiama oggi «latest». `diff_profile()` confronta un profilo congelato con l'ecosistema reale progetto per progetto (non come un singolo booleano), perché i numeri di versione di questo ecosistema sono un contachilometri in base 10 senza significato semantico e non possono mai essere, da soli, un segnale onesto di compatibilità.
- **Hashing password SHA-512-crypt reale, non il modulo `crypt` della
  stdlib.** `crypt` avvolge solo la chiamata libc propria dell'*host*
  (solo Unix, e rimosso del tutto in Python 3.13) - `passlib` produce lo
  stesso formato reale `$6$...` byte per byte che si aspetta
  `chpasswd -e`, su qualunque piattaforma su cui gira questo strumento,
  Windows incluso. L'hash usa 500000 round, non i 5000 predefiniti di glibc risalenti al 2000, così attaccare una copia dell'immagine o di `/etc/shadow` costa molto di più; lo yescrypt (`$y$`) preferito dal dispositivo stesso non può essere prodotto in modo portabile da Python su Windows.

## 🖼️ Schermate

Catturate a 1920×1080 su un banco di prova, con dati di esempio e senza alcuna installazione reale dietro.

<table>
<tr><td width="50%" valign="top"><img src="images/screenshots/overview.png" alt="La finestra: i progetti della CM5 trovati per l'immagine con versione, ruolo e stack, le opzioni di costruzione e il registro." width="100%"><br><sub>La finestra: i progetti della CM5 trovati per l'immagine con versione, ruolo e stack, le opzioni di costruzione e il registro.</sub></td></tr>
</table>

## 🔒 Sicurezza e protezione

`--public-image` (su `build-image` e `profile-build`, e la casella **Immagine pubblica** della finestra di costruzione; spenta per impostazione predefinita) rifiuta qualsiasi configurazione del primo avvio e cerca anche credenziali nella partizione di avvio (`firstrun.sh`, `wpa_supplicant.conf`, `userconf*`, `custom.toml`, `user-data`, `network-config`) e in `/opt/hydra-umc` (file `.env` e cartelle di dati con file); qualsiasi rilevamento impedisce di promuovere l'immagine. Non è stato provato su un'immagine reale, perché serve Linux.

## 🚀 Avvio rapido

Richiede Python 3.10 o successivo.

```bash
./build.sh             # Linux, macOS (build.bat on Windows)
./run.sh               # windowed GUI
./run.sh --cli status  # latest real version of every project
```

## 🧪 Test

187 test automatici si eseguono con `python -m pytest -q tests`. Non richiedono hardware né nulla al di fuori di questa macchina.

La CI esegue `HYDRA_UMC_CI=1 python tools/ci_validate.py`, che controlla il manifesto, i documenti, gli otto README e le immagini.

## 🏗️ Compilazione e rilascio

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
- `--cli config`/`build-image` rifiuta con «no login path at all»: SSH è stato disattivato senza configurare un account - configurarne uno, oppure passare `acknowledge_no_remote_access=True` (GUI/API) se un altro accesso è sicuro. Vedere `describe_recovery_procedure()`.
- `profile-build` rifiuta un progetto con «no real, resolved commit SHA»: il manifesto congelato precede il cambio di nome o la privatizzazione di un repository - ricongelare il profilo (`profile-freeze`) rispetto all'ecosistema reale attuale.
- `profile-build` rifiuta con «missing N required resource(s)»: un progetto curato con `profile-set-required-resources` ha eseguito il proprio `build.sh`, ma un percorso relativo dichiarato non esiste ancora sul disco dopo - una vera build incompleta, mai salvata da un file residuo altrove; l'immagine non viene promossa.
- La scheda Stato dell'Ecosistema della GUI resta vuota: controlla la tua
  rete - questo strumento ha bisogno di una vera connessione a
  `github.com`/`raw.githubusercontent.com` per `status`/la scoperta,
  come lo stesso `hydra-umc-updater`.
- **Il numero di progetti continua a diminuire a ogni aggiornamento (ad es. 42 -> 9 -> 0), anche dopo aver riavviato l'app** - un vero bug prima non segnalato: risolvere il vero SHA del commit di ogni progetto consuma una chiamata a `api.github.com` PER PROGETTO, su un budget *non autenticato* di 60 richieste ALL'ORA condiviso con tutto ciò che fa questo strumento (e `hydra-umc-updater`) - con oltre 50 veri progetti dell'ecosistema, un solo aggiornamento può esaurirlo, ed è la finestra oraria di GitHub (non lo stato di questa app) che deve ripartire, cosa che un riavvio non fa. Corretto per segnalarlo onestamente invece di elencare in silenzio meno progetti: il banner ambra sotto l'elenco dei progetti indica esattamente quanti progetti sono stati risolti prima del limite e quando il limite di GitHub si azzera (vedere `ecosystem_plan.GitHubRateLimitedError`). Impostare la variabile d'ambiente `GITHUB_TOKEN` (un semplice token di accesso personale GitHub, nessun permesso necessario per i repository pubblici) prima di avviare questo strumento per portare il budget a 5000/ora - sia l'elenco dei repository sia la risoluzione dello SHA per progetto lo rispettano ora in modo coerente.

## 📂 Struttura del repository

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-OS-REBUILDER" width="100%">
</p>

<details>
<summary>Versione testuale dell'albero</summary>

```text
HYDRA-UMC-OS-REBUILDER/
├── src/hydra_umc_os_rebuilder/   codice sorgente
│   ├── __init__.py               Versione del pacchetto
│   ├── ecosystem_plan.py         Piano reale progetti/versioni CM5, costruito sulla scoperta propria di hydra_umc_updater
│   ├── firstboot_config.py       Generatore puro firstrun.sh/cmdline.txt - nessun accesso al filesystem; protezione di recupero
│   ├── profile_manifest.py       Manifest di profilo di versione congelati: congelare/confrontare/aggiornare selettivamente, mai "l'ultima versione" a metà prova
│   ├── image_builder.py          Pipeline reale download/montaggio loop/installazione chroot, limitata a Linux/root
│   ├── i18n.py                   Traduzioni reali e complete della GUI (8 lingue)
│   ├── qt_gui.py                 ponte Qt Quick sui moduli della CLI
│   ├── qml/Main.qml              Shell desktop a tema: Stato dell'Ecosistema / Crea Immagine / Configurazione Primo Avvio
│   ├── main.py                   Dispatch: GUI predefinita, --cli per status/config/build-image
│   ├── remote_install.py         Da cosa installa e compila una build remota (revisione fissata, non la punta di main)
│   └── ssh_hostkeys.py           Fiducia al primo uso della chiave SSH della macchina di build remota, con impronta fissata
├── tests/                        Test reali: firstboot_config, ecosystem_plan, profile_manifest, image_builder, i18n, main
├── docs/                         documenti del progetto
├── images/                       Risorse, icona dell'app e banner
├── tools/                        strumenti del progetto e controlli della CI
├── .github/                      workflow di CI e modelli di segnalazione
├── build.sh / build.bat          venv + installazione editabile + verifica compilazione
├── run.sh / run.bat              GUI predefinita / punto di ingresso CLI
├── run-gui.vbs                   Launcher grafico Windows senza finestra console
├── bump_version.py               Incremento di versione stile contachilometri (eseguito solo dal comando `bump` esplicito)
├── bump_manifest_version.py      Sincronizza la versione di hydra-umc.project.json con quella nativa (--sync)
├── CHANGELOG.md                  cosa è cambiato in ogni versione
├── build-test.sh                 controllo di build senza modifiche
├── hydra-umc.project.json        manifesto: versione, maturità, famiglia
├── pyproject.toml                metadati del pacchetto
└── test.sh                       esegue i test
```

</details>

## 🗺️ Roadmap e limiti noti

**Limiti noti oggi**

- Supporto cloud-init come meccanismo alternativo di primo avvio per
  un'immagine base non-Pi, accanto all'attuale percorso `firstrun.sh`.
- Aggiornamenti incrementali dell'immagine (applicare una patch a un
  `.img` esistente invece di una ricostruzione completa) quando ci sarà
  un reale bisogno oltre a una build da zero.
- Una modalità di output `--json` per `status`, per l'uso da script.
- Eseguibile GUI standalone (PyInstaller), seguendo la stessa convenzione
  di `build_exe.bat`/`.sh` di HYDRA-UMC-SUITE, per un'installazione con
  doppio clic senza alcun passaggio `pip`/venv.
- Una casella nella GUI per `acknowledge_no_remote_access` - oggi la GUI mostra onestamente il vero messaggio di `FirstBootConfigError` (nessun crash, nessuna azione silenziosa) ma non ha un controllo dedicato per accettare, solo la CLI/API lo fanno.
- Un pannello GUI su `profile_manifest.py` (congelare/confrontare/aggiornare dalla shell desktop, non solo dalla CLI).

## 🌍 Lingue

Questo README e i documenti del repository esistono in otto lingue: inglese, spagnolo, tedesco, francese, italiano, giapponese, cinese e portoghese (Portogallo). Sono scritti insieme e la CI verifica che gli otto file abbiano le stesse sezioni e gli stessi link.

## 🔗 Progetti correlati

Questo progetto fa parte dell'ecosistema robotico HYDRA-UMC dello stesso autore (JuanenRac / Electro Hobby 3D). Utile da conoscere, poiché una richiesta potrebbe in realtà riguardare uno di questi invece di questo repository.

**Direttamente Correlati**
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — lo strato prodotto riproducibile di Raspberry Pi OS di cui questo strumento costruisce davvero un'immagine: agente in sola lettura, configurazione/profili validati, provisioning Wi-Fi al primo contatto.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — lo strumento gemello di operazioni dell'ecosistema da cui questo dipende come vera libreria per la scoperta GitHub - rileva, installa e aggiorna manualmente l'intero ecosistema su una macchina già in funzione, mentre questo strumento ne costruisce una nuova da zero.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinatore di incidenti di manutenzione: un ruolo edge a basso privilegio raccoglie uno snapshot di inventario/salute sanificato, un ruolo control-plane lo rende in sola lettura e chiede a un provider di IA di suggerire una diagnosi - non applica mai una patch né distribuisce nulla.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — host di sviluppo riproducibile (Raspberry Pi 5 / CM5) che conserva il codice sorgente dell'ecosistema ed esegue attività delimitate di build/test tramite una coda durevole; un ruolo di sviluppo dedicato, esplicitamente distinto da un CM5 operativo.

**Anche Parte dell'Ecosistema**

*Nucleo Hardware e Piattaforma*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — il contratto JSON-Schema condiviso e la barriera software di controllo dei job contro cui ogni bridge valida i propri comandi (non è una funzione di sicurezza certificata).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registro dichiarativo e validatore di manifesti adattatore per connettori di macchine esterne; estende la propria idea di contratto dell'SDK alle macchine esterne senza sostituire i progetti di gateway industriale.

*Backend e Client Principali*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — il progetto della scheda madre del braccio robotico: host CM5 + coprocessore STM32H745 dual-core, pensato per coordinare fino a 8 bracci utensile via CAN-OTA/SPI-OTA (firmware in fase iniziale; nessuna scheda assemblata per ora).
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — il vero backend headless (REST/WebSocket) con cui parla davvero ogni client di controllo.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — cruscotto di controllo web con visualizzazione 3D multi-robot in tempo reale.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro di comando sciame desktop (PySide6) per più server contemporaneamente.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app di controllo Android nativa con login biometrico e compagno Wear OS abbinato.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app di controllo iOS/iPadOS (Flutter) con sincronizzazione WebSocket in tempo reale.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaccia touch nativa per il touchscreen DSI da 7" integrato sulla stessa CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creatore/editor grafico desktop di URDF che invia i modelli finiti nel catalogo proprio di STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor desktop di modelli STL, che trasforma/sostituisce/rimuove/aggiunge veri pezzi nello stesso catalogo di modelli modificato anche da HYDRA-UMC-EDITOR-URDF.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — barriera di coordinamento per flotte AGV/AMR tramite un publisher MQTT VDA 5050 (testato solo contro una flotta emulata).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinatore ad alto livello per celle CNC con accesso a stato/byte di controllo GRBL (testato solo contro un emulatore).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — barriera di coordinamento per droidi con zampe/umanoidi, con un mittente di comandi per Boston Dynamics Spot (testato solo contro un emulatore).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinatore per celle laser che legge 3 segnali GPIO di chiave/involucro/interblocco (testato solo contro un chip simulato; non può armare né far partire un laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinatore sicuro di alto livello del flusso schede per il pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — confine di coordinamento sicuro per stampanti 3D Moonraker/Klipper, con comandi di lavoro realmente controllati.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinatore con un trasporto ROS 2 rclpy importato in modo lazy (non ancora eseguito contro un'installazione ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — barriera di coordinamento per UAV dotati di fotocamera, con un mittente di comandi MAVLink (testato solo contro un emulatore).

*Piattaforma Strumenti URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware per la scheda fisica Universal Robot Tool Controller, 25+ profili utensile su bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — strumento desktop con GUI per flashare schede URTC, CAN-OTA più SWD/JTAG a chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — strumento desktop di diagnostica bus CAN in tempo reale per schede URTC, un pannello per profilo utensile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa via browser a URTC-TESTER tramite la Web Serial API, senza installazione locale.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — gateway davanti al bus CAN di URTC: elenco di identificatori consentiti, limite di frequenza e chiave di sessione; software provato su computer, non ancora su un bus reale.

*Nodo Vision AI (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub di integrazione per la pipeline di visione Hailo-8, con un vero controllo di prontezza hardware per stadio.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro reale di modelli compilati con verifica sicura di architettura/checksum Hailo.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generatore reale di pipeline GStreamer + configurazione MediaMTX con un vero confine di integrazione HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — legge di correzione Position-Based Visual Servoing con autorizzazione condizionata allo stato di zona; ancora nessuna stima di posa da telecamera.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — vero controllo di violazione zona e richiesta di arresto di emergenza, con obbligo di calibrazione aggiornata.

*Nodo Cognitivo AI (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub di integrazione per la pipeline cognitiva Hailo-10 (orchestrazione LLM/VLA/voce).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vera codifica/decodifica di token d'azione e generazione di traiettoria per un modello Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vero front-end vocale (VAD + parser di intenti) con un relay al Watch limitato e soggetto a conferma.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vera scomposizione di task basata su regole e recupero semantico degli errori sui codici di errore dell'MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vera ricerca documentale TF-IDF solo stdlib sulla documentazione Markdown propria di questo ecosistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — tecnico di manutenzione IA locale e con cancelli di policy per l'ecosistema stesso - osserva, diagnostica e propone correzioni; i due livelli di rischio più alti non sono deliberatamente ancora implementati.

*Orchestrazione e Sciame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub di integrazione con un vero contratto di health-report gRPC/Protobuf e macchina a stati di missione.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vera coda di lavori basata su priorità con deduplicazione, su una vera API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vero watchdog di salute flotta basato su gRPC con retry/backoff e rilevamento di identità non corrispondente.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vero pianificatore di percorso 3D basato su RRT con validazione reale di collisione ostacolo/spazio di lavoro.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vera sincronizzazione di stato CRDT LWW-Element-Map, testata a proprietà per la convergenza multi-cella.

*Gemello Digitale e Simulazione*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub di integrazione per il motore di gemello digitale, con un vero contratto di sincronizzazione di compatibilità versione.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — router hardware-in-the-loop con un interblocco software di collisione tra simulazione e hardware reale (testato senza hardware reale).
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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app companion WearOS con schemi di avviso aptico e un relay vocale verso il telefono abbinato (non ancora eseguita su un orologio fisico).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware per un rack di montaggio schede con vera decodifica ID utensile e logica di pre-riscaldamento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware più un vero compagno di visione Python per una testa di ispezione termica/RGB.

## 📚 Documentazione

Dove leggere di più:

* **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — ogni sottocomando `--cli`, con output di esempio reale.
* **[docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md)** — il meccanismo reale `firstrun.sh` riprodotto da questo strumento, e perché.
* [Base di sicurezza dell'ecosistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Modello delle minacce dell'ecosistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Registro delle modifiche di questo repository](CHANGELOG.md)
* [Licenza di questo repository](LICENSE.md)

## 🤝 Contribuire e comunità

* Prima di una pull request esegui `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (oppure `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`): deve stampare `CI_VALIDATION=PASS`. Non eseguire `build.sh` né `build.bat` per questa verifica; compilare non è verificare.
* I otto README sono scritti da un'unica fonte in HYDRA-UMC-DOCS; non modificarli a mano. Cambia la fonte e riscrivili con `tools/make_readmes.py`.
* Non affermare in un README ciò che non è stato eseguito: scrivi «simulato» o «non provato su hardware» quando è la verità.
* Vedi [CONTRIBUTING.md](CONTRIBUTING.md), il [codice di condotta](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) e [SUPPORT.md](SUPPORT.md).

## 👤 AUTORE

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENZA

GPL-3.0-or-later - [LICENSE](LICENSE).
