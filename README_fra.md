<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="Bannière HYDRA-UMC-OS-REBUILDER" width="100%">
</p>

# 🏗️ HYDRA-UMC-OS-REBUILDER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | 🇫🇷 <b>Français</b> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 📀 Construire une Image CM5 Prête à Graver et Totalement à Jour

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="Interface de bureau PySide6 Qt Quick">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Windows et Linux">
</p>

> **Statut : v0.1.7, squelette.** La CLI, la découverte de l'écosystème, le
> générateur de configuration de premier démarrage et l'interface
> graphique sont réels et testés. La construction d'image réelle de bout
> en bout (téléchargement → montage loop → installation en chroot →
> démontage) est implémentée mais ne fonctionne que sur un véritable hôte
> Linux avec les droits root - voir
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) pour la limite exacte de
> plateforme et pourquoi elle existe.

**Vérification d'honnêteté - ce qui fonctionne réellement aujourd'hui :** la CLI (`main.py`), la découverte dynamique de l'écosystème qui réutilise le client GitHub de `hydra_umc_updater` plutôt que d'en dupliquer un second (`ecosystem_plan.py`), le générateur pur de `firstrun.sh`/`cmdline.txt` sans accès au système de fichiers (`firstboot_config.py`), les traductions de l'interface en 7 langues (`i18n.py`) et l'interface de bureau Qt Quick (`qt_gui.py`, `qml/Main.qml`) sont réels et testés (67 tests, `pytest`). Le pipeline de `image_builder.py` (téléchargement/vérification de somme de contrôle/montage loop/installation en chroot/démontage), son hachage de contenu par projet de ce qui a réellement atterri sur le disque, et son analyse avant promotion à la recherche d'un mot de passe Wi-Fi divulgué/une clé SSH privée/un historique de shell/un fichier `.env` sont du code réel, verrouillé derrière `check_build_platform()` - ils ne s'exécutent que sur un véritable hôte Linux avec les droits root et `losetup`/`chroot` sur le `PATH`, et n'ont pas été exécutés de bout en bout contre une écriture réelle de carte SD/eMMC d'une CM5 dans cet environnement ; sous Windows ou avec un utilisateur Linux non root, `build-image` s'arrête immédiatement avec `BUILD_BLOCKED reason=...` plutôt que de simuler un succès. `status`/`config` ont bien été testés en conditions réelles contre la découverte GitHub en direct. Voir `CHANGELOG.md` pour ce qui a déjà été livré exactement, et la feuille de route (ROADMAP) ci-dessous pour ce qui reste ouvert.

---

## 1. 🛠️ APERÇU TECHNIQUE

HYDRA-UMC-OS-REBUILDER est un outil de bureau Windows/Linux - interface
graphique par défaut, CLI complète avec `--cli` - qui répond à la question
que tout déploiement réel de CM5 finit par se poser : **« construis-moi
une image fraîche de carte SD/eMMC, avec la version réelle la plus récente
de chaque projet de l'écosystème déjà installée, et laisse-moi configurer
le Wi-Fi/utilisateur/hostname/SSH avant de l'écrire. »**

Il fait trois choses réelles :

1. **Interroge GitHub.** Chaque dépôt de l'écosystème HYDRA-UMC/URTC dont
   le propre `hydra-umc.project.json` déclare
   `"deployment_target": "cm5"` est découvert dynamiquement (jamais une
   liste fixe) et sa version publiée actuelle est lue - en dépendant de
   `hydra-umc-updater` comme véritable bibliothèque pour cela, pas d'une
   seconde implémentation qui pourrait dériver silencieusement de son
   propre code de découverte.
2. **Construit une image réelle.** Télécharge une image de base Raspberry
   Pi OS fixée et vérifiée par somme de contrôle, la monte en loop, et
   installe/met à jour chaque projet découvert en exécutant **le
   `build.sh` propre à ce projet** dans le chroot de l'image - sans jamais
   réimplémenter les étapes de construction d'aucun projet.
3. **Écrit une configuration réelle de premier démarrage.** Hostname, un
   nouvel utilisateur avec un mot de passe réellement haché par
   `passlib`, Wi-Fi, fuseau horaire, disposition du clavier et SSH - le
   même mécanisme `firstrun.sh` réel que celui utilisé par l'écran « OS
   Customisation » de Raspberry Pi Imager sur une image Raspberry Pi OS
   (Bookworm et ultérieur), de sorte que la carte SD résultante se
   comporte exactement comme celle que Raspberry Pi Imager lui-même
   aurait produite. Voir
   [docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md).
4. **Analyse sa propre sortie avant de la publier.** Avant que l'image
   construite ne soit déplacée vers son chemin final, le rootfs monté est
   vérifié à la recherche d'un vrai mot de passe Wi-Fi laissé dans
   `wpa_supplicant.conf`/un profil de connexion NetworkManager, d'une
   vraie clé SSH privée, d'un historique shell non vide, ou d'un fichier
   `.env` égaré - toute découverte réelle bloque entièrement la
   publication, de la même façon qu'un échec de nettoyage le fait déjà.
   La vérification de somme de contrôle ne couvrait que l'ENTRÉE (l'image
   de base) ; ceci est le premier contrôle sur ce que la construction
   elle-même laisse dans la SORTIE.

```
$ hydra-umc-os-rebuilder --cli status
HYDRA-UMC-SERVER 0.4.8 (api/node)
HYDRA-UMC-VISION-STREAMER 0.0.3 (service/python)
HYDRA-UMC-GATEWAY-INDUSTRIAL 0.0.3 (api/node)
...
TOTAL=27

$ hydra-umc-os-rebuilder --cli config --out ./boot \
    --hostname hydra-umc-cm5 --username hydra-umc --password 'a-changer' \
    --wifi-ssid MonReseau --wifi-password 'mdp-wifi' --wifi-country FR
CONFIG_WRITTEN out=boot firstrun=firstrun.sh
```

Lancé sans argument, il ouvre la même information dans une interface de
bureau Qt Quick - réutilisant le même langage visuel que
HYDRA-UMC-UPDATER (même palette sombre, typographie et jeu de
composants) sur trois onglets : État de l'Écosystème, Créer l'Image et
Configuration du Premier Démarrage.

## 2. 🧱 ARCHITECTURE ET DÉCISIONS DE CONCEPTION

- **`ecosystem_plan.py` ne réimplémente jamais la découverte GitHub.** Il
  dépend de `hydra-umc-updater` comme véritable paquet Python
  (`hydra_umc_updater.github_client.discover_remote_projects()`) plutôt
  que d'une seconde copie de sa logique de validation de manifeste/
  réessai/backoff - une correction ou amélioration faite là-bas profite
  automatiquement à cet outil.
- **`image_builder.py` ne réimplémente jamais la construction d'un
  projet.** Chaque projet de l'écosystème est cloné à sa propre version
  réelle fixée et construit en exécutant SON PROPRE `build.sh`, en chroot
  dans le rootfs cible - le même principe « déléguer au script de
  construction propre à chaque projet » déjà documenté par le
  `install.py` propre à `hydra-umc-updater`.
- **La limite de plateforme Linux/root est toujours vérifiée en
  premier.** `check_build_platform()` est la toute première chose que
  fait `build_image()` - une construction qui échoue silencieusement sur
  un hôte non pris en charge (Windows, un utilisateur Linux sans root, un
  `losetup`/`chroot` manquant) serait pire qu'une qui refuse de démarrer
  avec une raison claire.
- **`firstboot_config.py` est un générateur pur, sans effet de bord.** Il
  ne produit que du contenu de fichier en texte brut (une chaîne
  `firstrun.sh`, une chaîne de correctif `cmdline.txt`) - il ne touche
  jamais une image ou un système de fichiers réel, ce qui le rend
  trivialement testable sans root ni image réelle. `image_builder.py` est
  seul responsable d'écrire réellement ce contenu sur une partition boot
  réelle.
- **Hachage de mot de passe SHA-512-crypt réel, pas le module `crypt` de
  la stdlib.** `crypt` ne fait qu'envelopper l'appel libc de *l'hôte*
  lui-même (Unix uniquement, et purement supprimé dans Python 3.13) -
  `passlib` produit le même format réel `$6$...` octet pour octet
  qu'attend `chpasswd -e`, sur toute plateforme où tourne cet outil, y
  compris Windows.

## 📂 STRUCTURE DES RÉPERTOIRES

```
HYDRA-UMC-OS-REBUILDER/
├── src/hydra_umc_os_rebuilder/
│   ├── ecosystem_plan.py    # Plan réel projets/versions CM5, construit sur la découverte propre de hydra_umc_updater
│   ├── firstboot_config.py  # Générateur pur firstrun.sh/cmdline.txt - aucun accès au système de fichiers
│   ├── image_builder.py     # Pipeline réel téléchargement/montage loop/installation chroot, limité à Linux/root
│   ├── i18n.py               # Traductions réelles et complètes de la GUI (7 langues)
│   ├── qt_gui.py             # Pont Qt Quick sur les modules réels ci-dessus, les mêmes qu'utilise la CLI
│   ├── qml/Main.qml          # Interface de bureau thématique : État de l'Écosystème / Créer l'Image / Configuration du Premier Démarrage
│   └── main.py                # Répartition : GUI par défaut, --cli pour status/config/build-image
├── tests/                    # Tests réels : firstboot_config, ecosystem_plan, image_builder, i18n, main
├── docs/
│   ├── CLI_REFERENCE.md       # Référence des commandes
│   └── FIRST_BOOT_CONFIG.md   # Le mécanisme réel firstrun.sh reproduit par cet outil, et pourquoi
├── images/                    # Ressources, icône de l'app et bannière
├── tools/
│   ├── build_test.py          # Vérification de compilation sans versionnage
│   └── ci_validate.py         # Validation manifeste/CHANGELOG/documentation utilisée par la CI
├── build.sh / build.bat       # venv + installation éditable + vérification de compilation
├── run.sh / run.bat           # GUI par défaut / point d'entrée CLI
├── run-gui.vbs                # Lanceur graphique Windows sans fenêtre de console
├── bump_version.py            # Incrément type odomètre pour tout l'écosystème (pyproject.toml + __init__.py)
└── bump_manifest_version.py   # Synchronise la version de hydra-umc.project.json avec la version native (--sync)
```

## ⚙️ GUIDE DE COMPILATION ET D'EXÉCUTION

```bash
chmod +x build.sh   # une seule fois
./build.sh          # crée .venv, pip install -e ".[dev,gui]", vérifie la compilation, exécute pytest
./run.sh                                # GUI en fenêtre (par défaut)
./run.sh --cli status                   # version GitHub réelle la plus récente de chaque projet de l'écosystème
./run.sh --cli config --out ./boot ...  # écrit la configuration de premier démarrage (voir docs/CLI_REFERENCE.md pour chaque option)
./run.sh --cli build-image --out FILE   # construit un .img prêt à graver (Linux/root uniquement)
```

Sous Windows : `build.bat`, puis `run.bat` (GUI) / `run.bat --cli status` /
`run.bat --cli config ...`. `build-image` nécessite quand même un
véritable hôte Linux avec root - voir
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

**Dépannage**

- `--cli build-image` se termine avec `BUILD_BLOCKED reason=...` : lisez
  la raison - elle nomme précisément l'élément manquant (pas Linux, pas
  root, ou un outil spécifique manquant sur le `PATH`) plutôt qu'un échec
  générique.
- `--cli config` lève une erreur de validation : le hostname/nom
  d'utilisateur/code pays Wi-Fi donné ne correspond pas à la forme réelle
  et stricte exigée par ces champs - voir la validation propre de
  `firstboot_config.py`.
- L'onglet État de l'Écosystème de la GUI reste vide : vérifiez votre
  réseau - cet outil a besoin d'une vraie connexion à
  `github.com`/`raw.githubusercontent.com` pour `status`/la découverte,
  comme `hydra-umc-updater` lui-même.

## 🚀 FEUILLE DE ROUTE

- Support de cloud-init comme mécanisme alternatif de premier démarrage
  pour une image de base non-Pi, en plus du chemin actuel `firstrun.sh`.
- Mises à jour incrémentales d'image (corriger un `.img` existant au lieu
  d'une reconstruction complète) une fois qu'un vrai besoin apparaîtra
  au-delà d'une construction depuis zéro.
- Un mode de sortie `--json` pour `status`, pour le scripting.
- Exécutable GUI autonome (PyInstaller), suivant la même convention que
  `build_exe.bat`/`.sh` de HYDRA-UMC-SUITE, pour une installation en un
  double-clic sans aucune étape `pip`/venv.

## 🔗 Projets Liés

Ce projet fait partie de l'écosystème robotique HYDRA-UMC du même auteur (JuanenRac / Electro Hobby 3D). À connaître, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt.

**Directement Liés**
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — la couche produit reproductible Raspberry Pi OS dont cet outil construit réellement une image : agent en lecture seule, configuration/profils validés, approvisionnement Wi-Fi de premier contact.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — l'outil frère d'opérations de l'écosystème dont celui-ci dépend comme véritable bibliothèque pour la découverte GitHub - détecte, installe et met à jour manuellement tout l'écosystème sur une machine déjà en service, là où cet outil en construit une nouvelle depuis zéro.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinateur d'incidents de maintenance : un rôle edge à faible privilège collecte un instantané d'inventaire/santé assaini, un rôle control-plane le rend en lecture seule et demande à un fournisseur d'IA de suggérer un diagnostic - n'applique jamais de correctif ni ne déploie rien.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — hôte de développement reproductible (Raspberry Pi 5 / CM5) qui héberge le code source de l'écosystème et exécute des tâches de compilation/test délimitées via une file d'attente durable ; un rôle de développement dédié, explicitement distinct d'un CM5 opérationnel.

**Également Partie de l'Écosystème**

*Noyau Matériel et Plateforme*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — le contrat JSON-Schema partagé et la limite de la porte de sécurité contre laquelle chaque pont valide ses commandes.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registre déclaratif et validateur de manifestes d'adaptateur pour les connecteurs de machines externes ; étend la propre idée de contrat du SDK aux machines externes sans remplacer les projets de passerelle industrielle.

*Backend et Clients Principaux*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la carte mère physique du bras robotique : hôte CM5 + coprocesseur STM32H745 double cœur, coordonnant jusqu'à 8 bras-outils via CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le véritable backend sans interface (REST/WebSocket) auquel parle réellement chaque client de contrôle.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle web avec visualisation 3D multi-robot en temps réel.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centre de commande d'essaim de bureau (PySide6) pour plusieurs serveurs à la fois.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application de contrôle Android native avec connexion biométrique et compagnon Wear OS jumelé.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application de contrôle iOS/iPadOS (Flutter) avec synchronisation WebSocket en temps réel.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native pour l'écran DSI 7" embarqué sur la CM5 elle-même.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau d'URDF qui envoie les modèles finis vers le catalogue propre de STUDIO.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — limite de coordination pour flottes AGV/AMR via un véritable éditeur MQTT VDA 5050.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinateur de cellule CNC de haut niveau avec accès réel au statut/octet de contrôle GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — limite de coordination pour droïdes à pattes/humanoïdes, avec un véritable émetteur de commandes Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinateur de sécurité de cellule laser lisant 3 véritables sécurités GPIO clé/enceinte/verrouillage.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinateur sûr de haut niveau du flux de cartes pour le pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — limite de coordination sûre pour imprimantes 3D Moonraker/Klipper, avec des commandes de travail réellement contrôlées.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinateur de sécurité avec un vrai transport rclpy ROS 2, importé paresseusement.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — limite de coordination pour UAV équipés de caméra, avec un véritable émetteur de commandes MAVLink.

*Plateforme d'Outils URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware pour la carte physique Universal Robot Tool Controller, 25+ profils d'outils sur bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — outil de bureau avec GUI pour flasher les cartes URTC, CAN-OTA plus SWD/JTAG puce complète.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — outil de bureau de diagnostic bus CAN en direct pour cartes URTC, un panneau par profil d'outil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative dans le navigateur à URTC-TESTER via la Web Serial API, sans installation locale.

*Nœud Vision IA (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub d'intégration pour le pipeline vision Hailo-8, avec une véritable vérification de préparation matérielle par étape.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registre réel de modèles compilés avec vérification sécurisée d'architecture/somme de contrôle Hailo.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — générateur réel de pipeline GStreamer + configuration MediaMTX avec une véritable limite d'intégration HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — véritable loi de correction Position-Based Visual Servoing, avec porte de sécurité selon l'état de zone en amont.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — véritable vérification de franchissement de zone et demande d'arrêt d'urgence, avec exigence de calibration à jour.

*Nœud Cognitif IA (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub d'intégration pour le pipeline cognitif Hailo-10 (orchestration LLM/VLA/voix).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — véritable encodage/décodage de jetons d'action et génération de trajectoire pour un modèle Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — véritable interface vocale (VAD + analyseur d'intention) avec un relais Watch borné et soumis à confirmation.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — véritable décomposition de tâches basée sur des règles et récupération sémantique d'erreurs sur les codes d'erreur du MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — véritable recherche de documents TF-IDF avec seulement la stdlib sur la documentation Markdown propre de cet écosystème.

*Orchestration et Essaim*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub d'intégration avec un véritable contrat de rapport de santé gRPC/Protobuf et machine à états de mission.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — véritable file de travaux basée sur la priorité avec déduplication, sur une véritable API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — véritable surveillant de santé de flotte basé sur gRPC avec réessai/backoff et détection d'incohérence d'identité.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — véritable planificateur de chemin 3D basé sur RRT avec validation réelle de collision obstacle/espace de travail.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — véritable synchronisation d'état CRDT LWW-Element-Map, testée par propriétés pour la convergence multi-cellule.

*Jumeau Numérique et Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub d'intégration pour le moteur de jumeau numérique, avec un véritable contrat de synchronisation de compatibilité de versions.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — véritable verrouillage de sécurité hardware-in-the-loop, dirigeant les commandes entre simulation et matériel réel.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — véritable cinématique directe et validation des limites d'articulation sur un véritable sous-ensemble URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — véritable générateur procédural de scènes 2D avec export d'annotations YOLO/COCO.

*Données et Analytique*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — véritable entrepôt de séries temporelles sur sqlite3 avec une véritable API HTTP d'ingestion/requête.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — véritable détecteur d'anomalies par FFT + ligne de base statistique avec surveillance de dérive.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — véritable calcul OEE/disponibilité sur l'historique DATALAKE, avec export CSV reproductible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — véritable pipeline d'ingestion CAN/WebSocket vers DATALAKE, avec déduplication par séquence.

*Passerelle Industrielle*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub d'intégration relayant vers des protocoles industriels, avec une véritable couche de liste blanche de commandes/contre-pression.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — véritable espace d'adressage OPC-UA, vérifié avec une véritable session client de protocole binaire.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — véritable broker MQTT avec authentification par client optionnelle et ACL de topics.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — véritables endpoints XML `/probe` et `/current` MTConnect avec sortie en mode dégradé.

*Outils Complémentaires et Opérations de l'Écosystème*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — panneaux de Résumés Intelligents et de Mise en Évidence d'Anomalies sur DATALAKE/ANOMALY-DETECTOR, avec un repli statistique honnête.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flotte avec un véritable contrat de codes de sortie stable, un véritable client en direct de l'API propre de HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — application compagnon WearOS avec de véritables alertes haptiques et un relais vocal vers le téléphone jumelé.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware pour un rack de montage de cartes avec décodage réel d'ID d'outil et logique de préchauffage Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus un véritable compagnon de vision Python pour une tête d'inspection thermique/RGB.

---

## 📚 Documentation et Communauté

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — chaque sous-commande `--cli`, avec une sortie d'exemple réelle.
- **[docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md)** — le mécanisme réel `firstrun.sh` reproduit par cet outil, et pourquoi.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pile technologique et lignes directrices de code pour une pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — les standards de comportement attendus dans cette communauté.
- **[SECURITY.md](SECURITY.md)** — comment signaler une vulnérabilité, et les véritables axes de sécurité de ce projet.
- **[SUPPORT.md](SUPPORT.md)** — où poser des questions et signaler des bugs.

## 👤 AUTEUR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCE

GPL-3.0 (logiciel) / CC BY-SA 4.0 (documentation) - voir [LICENSE.md](LICENSE.md).
