<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="Banner de HYDRA-UMC-OS-REBUILDER" width="100%">
</p>

# 🏗️ HYDRA-UMC-OS-REBUILDER

<p align="center"><a href="README.md">🇺🇸 English</a> | 🇪🇸 <b>Español</b> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 📀 Construye una Imagen Lista para Grabar y Totalmente Actualizada de la CM5

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="GUI de escritorio PySide6 Qt Quick">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Windows y Linux">
</p>

> **Estado: v0.1.6, esqueleto.** La CLI, el descubrimiento del ecosistema,
> el generador de configuración de primer arranque y la interfaz gráfica
> son reales y están probados. La construcción de imagen real de extremo a
> extremo (descarga → montaje loop → instalación en chroot → desmontaje)
> está implementada pero solo funciona en un host Linux real con root -
> ver [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) para el límite exacto
> de plataforma y por qué existe.

---

## 1. 🛠️ VISIÓN TÉCNICA GENERAL

HYDRA-UMC-OS-REBUILDER es una herramienta de escritorio Windows/Linux -
interfaz gráfica por defecto, CLI completa con `--cli` - que responde a la
pregunta que toda instalación real de CM5 termina necesitando: **"crear una
imagen fresca de tarjeta SD/eMMC, con la versión real más reciente de cada
proyecto del ecosistema ya instalada, y dejarme configurar Wi-Fi/usuario/
hostname/SSH antes de grabarla."**

Hace tres cosas reales:

1. **Consulta GitHub.** Cada repositorio del ecosistema HYDRA-UMC/URTC cuyo
   propio `hydra-umc.project.json` declara
   `"deployment_target": "cm5"` se descubre de forma dinámica (nunca una
   lista fija) y se lee su versión publicada actual - dependiendo de
   `hydra-umc-updater` como librería real para esto, no una segunda
   reimplementación que pueda divergir en silencio de su propio código de
   descubrimiento.
2. **Construye una imagen real.** Descarga una imagen base de Raspberry Pi
   OS fijada y verificada por checksum, la monta en loop, e instala/
   actualiza cada proyecto descubierto ejecutando **el `build.sh` propio de
   ese proyecto** dentro del chroot de la imagen - nunca reimplementa los
   pasos de compilación de ningún proyecto.
3. **Escribe configuración real de primer arranque.** Hostname, un usuario
   nuevo con una contraseña con hash real de `passlib`, Wi-Fi, zona horaria,
   distribución de teclado y SSH - el mismo mecanismo `firstrun.sh` real que
   usa la propia pantalla "OS Customisation" de Raspberry Pi Imager en una
   imagen de Raspberry Pi OS (Bookworm o posterior), así que la tarjeta SD
   resultante se comporta exactamente igual que una que hubiera producido
   el propio Raspberry Pi Imager. Ver
   [docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md).
4. **Escanea su propia salida antes de publicarla.** Antes de que la
   imagen construida se mueva a su ruta final, se comprueba el rootfs
   montado en busca de una contraseña Wi-Fi real dejada en
   `wpa_supplicant.conf`/un perfil de conexión de NetworkManager, una
   clave SSH privada real, un historial de shell no vacío, o un fichero
   `.env` suelto - cualquier hallazgo real bloquea la publicación por
   completo, igual que ya hace un fallo de limpieza. La verificación de
   checksum solo cubría la ENTRADA (la imagen base); esta es la primera
   comprobación de lo que la propia construcción deja en la SALIDA.

```
$ hydra-umc-os-rebuilder --cli status
HYDRA-UMC-SERVER 0.4.8 (api/node)
HYDRA-UMC-VISION-STREAMER 0.0.3 (service/python)
HYDRA-UMC-GATEWAY-INDUSTRIAL 0.0.3 (api/node)
...
TOTAL=27

$ hydra-umc-os-rebuilder --cli config --out ./boot \
    --hostname hydra-umc-cm5 --username hydra-umc --password 'cambia-esto' \
    --wifi-ssid MiRed --wifi-password 'clave-wifi' --wifi-country ES
CONFIG_WRITTEN out=boot firstrun=firstrun.sh
```

Al ejecutarla sin argumentos se abre la misma información en un panel de
escritorio Qt Quick - reutilizando el mismo lenguaje visual de
HYDRA-UMC-UPDATER (misma paleta oscura, tipografía y conjunto de
componentes) en tres pestañas: Estado del Ecosistema, Crear Imagen y
Configuración de Primer Arranque.

## 2. 🧱 ARQUITECTURA Y DECISIONES DE DISEÑO

- **`ecosystem_plan.py` nunca reimplementa el descubrimiento de GitHub.**
  Depende de `hydra-umc-updater` como paquete Python real
  (`hydra_umc_updater.github_client.discover_remote_projects()`) en lugar
  de una segunda copia de su lógica de validación de manifiestos/
  reintentos/backoff - una corrección o mejora hecha allí beneficia
  automáticamente a esta herramienta.
- **`image_builder.py` nunca reimplementa la compilación de un proyecto.**
  Cada proyecto del ecosistema se clona en su propia versión real fijada y
  se compila ejecutando SU PROPIO `build.sh`, en chroot dentro del rootfs
  destino - el mismo principio de "delegar en el script de compilación
  propio de cada proyecto" que ya documenta el propio `install.py` de
  `hydra-umc-updater`.
- **El límite de plataforma Linux/root se comprueba primero, siempre.**
  `check_build_platform()` es lo primero que hace `build_image()` - una
  construcción que se queda silenciosamente en no-op en un host no
  soportado (Windows, un usuario Linux sin root, un `losetup`/`chroot`
  ausente) sería peor que una que se niega a empezar con un motivo claro.
- **`firstboot_config.py` es un generador puro sin efectos secundarios.**
  Solo produce contenido de archivo en texto plano (una cadena
  `firstrun.sh`, una cadena de parche para `cmdline.txt`) - nunca toca una
  imagen o sistema de archivos real, así que se mantiene trivialmente
  testeable sin root ni una imagen real. Solo `image_builder.py` es
  responsable de escribir de verdad ese contenido en una partición boot
  real.
- **Hash de contraseña SHA-512-crypt real, no el módulo `crypt` de la
  stdlib.** `crypt` solo envuelve la llamada propia de libc del *host*
  (solo Unix, y eliminado directamente en Python 3.13) - `passlib` produce
  el mismo formato real `$6$...` byte a byte que espera `chpasswd -e`, en
  cualquier plataforma donde corra esta herramienta, incluyendo Windows.

## 📂 ESTRUCTURA DE DIRECTORIOS

```
HYDRA-UMC-OS-REBUILDER/
├── src/hydra_umc_os_rebuilder/
│   ├── ecosystem_plan.py    # Plan real de proyectos/versiones CM5, construido sobre el descubrimiento propio de hydra_umc_updater
│   ├── firstboot_config.py  # Generador puro de firstrun.sh/cmdline.txt - sin acceso al sistema de archivos
│   ├── image_builder.py     # Pipeline real de descarga/montaje loop/instalación en chroot, limitado a Linux/root
│   ├── i18n.py               # Traducciones reales y completas de la GUI (7 idiomas)
│   ├── qt_gui.py             # Puente Qt Quick sobre los módulos reales de arriba, los mismos que usa la CLI
│   ├── qml/Main.qml          # Interfaz temática de escritorio: Estado del Ecosistema / Crear Imagen / Configuración de Primer Arranque
│   └── main.py                # Despacho: GUI por defecto, --cli para status/config/build-image
├── tests/                    # Tests reales: firstboot_config, ecosystem_plan, i18n
├── docs/
│   ├── CLI_REFERENCE.md       # Referencia de comandos
│   └── FIRST_BOOT_CONFIG.md   # El mecanismo real de firstrun.sh que reproduce esta herramienta, y por qué
├── images/                    # Recursos, icono de la app y banner
├── tools/
│   ├── build_test.py          # Comprobación de compilación sin versionado
│   └── ci_validate.py         # Validación de manifiesto/CHANGELOG/documentación usada por la CI
├── build.sh / build.bat       # venv + instalación editable + comprobación de compilación
├── run.sh / run.bat           # GUI por defecto / punto de entrada CLI
├── run-gui.vbs                # Lanzador gráfico en Windows sin ventana de consola
├── bump_version.py            # Incremento tipo odómetro de todo el ecosistema (pyproject.toml + __init__.py)
└── bump_manifest_version.py   # Sincroniza la versión de hydra-umc.project.json con la nativa (--sync)
```

## ⚙️ GUÍA DE COMPILACIÓN Y EJECUCIÓN

```bash
chmod +x build.sh   # una sola vez
./build.sh          # crea .venv, pip install -e ".[dev,gui]", comprueba compilación, ejecuta pytest
./run.sh                                # GUI en ventana (por defecto)
./run.sh --cli status                   # versión real de GitHub más reciente de cada proyecto del ecosistema
./run.sh --cli config --out ./boot ...  # escribe configuración de primer arranque (ver docs/CLI_REFERENCE.md para cada opción)
./run.sh --cli build-image --out FILE   # construye un .img listo para grabar (solo Linux/root)
```

En Windows: `build.bat`, luego `run.bat` (GUI) / `run.bat --cli status` /
`run.bat --cli config ...`. `build-image` sigue necesitando un host Linux
real con root de todas formas - ver
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

**Solución de problemas**

- `--cli build-image` termina con `BUILD_BLOCKED reason=...`: lee el
  motivo - nombra la pieza exacta que falta (no es Linux, no hay root, o
  falta una herramienta concreta en el `PATH`) en vez de un fallo
  genérico.
- `--cli config` lanza un error de validación: el hostname/usuario/código
  de país Wi-Fi que diste no cumple la forma real y estricta que exigen
  esos campos - ver la validación propia de `firstboot_config.py`.
- La pestaña Estado del Ecosistema de la GUI se queda vacía: revisa tu red
  - esta herramienta necesita una conexión real a
  `github.com`/`raw.githubusercontent.com` para `status`/el descubrimiento,
  igual que el propio `hydra-umc-updater`.

## 🚀 HOJA DE RUTA

- Soporte de cloud-init como mecanismo alternativo de primer arranque para
  una imagen base que no sea de Raspberry Pi, junto al camino actual de
  `firstrun.sh`.
- Actualizaciones incrementales de imagen (parchear un `.img` existente en
  vez de una reconstrucción completa) cuando haya una necesidad real más
  allá de una construcción desde cero.
- Un modo de salida `--json` para `status`, para poder usarlo desde
  scripts.
- Ejecutable de GUI independiente (PyInstaller), siguiendo la misma
  convención que `build_exe.bat`/`.sh` de HYDRA-UMC-SUITE, para una
  instalación de doble clic sin ningún paso de `pip`/venv.

## 🔗 Proyectos Relacionados

Este proyecto es parte del ecosistema de robótica HYDRA-UMC del mismo autor (JuanenRac / Electro Hobby 3D). Vale la pena conocerlo, ya que una petición podría en realidad ser sobre alguno de estos en vez de sobre este repositorio.

**Directamente Relacionados**
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — la capa de producto reproducible de Raspberry Pi OS de la que esta herramienta construye realmente una imagen: agente de solo lectura, configuración/perfiles validados, aprovisionamiento de primer contacto Wi-Fi.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — la herramienta hermana de operaciones del ecosistema de la que esta depende como librería real para el descubrimiento en GitHub - detecta, instala y actualiza manualmente todo el ecosistema en una máquina ya en marcha, mientras que esta herramienta construye una nueva desde cero.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinador de incidencias de mantenimiento: un rol edge de bajo privilegio recopila un snapshot de inventario/salud saneado, un rol control-plane lo renderiza de solo lectura y pide a un proveedor de IA que sugiera un diagnóstico - nunca aplica un parche ni despliega nada.

**También Parte del Ecosistema**

*Núcleo de Hardware y Plataforma*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — el contrato compartido en JSON-Schema y el límite de la puerta de seguridad contra el que valida sus comandos cada puente.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registro declarativo y validador de manifiestos de adaptador para conectores de máquinas externas; extiende la propia idea de contrato del SDK a máquinas externas sin sustituir a los proyectos de pasarela industrial.

*Backend y Clientes Principales*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la placa madre física del brazo robótico: host CM5 + coprocesador STM32H745 de doble núcleo, coordinando hasta 8 brazos herramienta por CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — el backend real sin interfaz (REST/WebSocket) con el que habla de verdad cada cliente de control.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — panel de control web con visualización 3D multi-robot en tiempo real.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de mando de enjambre de escritorio (PySide6) para varios servidores a la vez.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app de control Android nativa con login biométrico y una compañera Wear OS emparejada.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app de control iOS/iPadOS (Flutter) con sincronización WebSocket en tiempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaz táctil nativa para la pantalla DSI de 7" integrada en la propia CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creador/editor gráfico de escritorio de URDF que envía los modelos terminados al catálogo propio de STUDIO.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — límite de coordinación para flotas AGV/AMR mediante un publicador MQTT real de VDA 5050.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinador de celda CNC de alto nivel con acceso real a estado/byte de control GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — límite de coordinación para droides con patas/humanoides, con un emisor real de comandos Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinador de seguridad de celda láser leyendo 3 protecciones GPIO reales de llave/recinto/enclavamiento.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinador seguro de alto nivel del flujo de placas para pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — límite de coordinación segura para impresoras 3D Moonraker/Klipper, con comandos de trabajo realmente controlados.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinador de seguridad con un transporte real rclpy de ROS 2, importado de forma perezosa.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — límite de coordinación para UAVs equipados con cámara, con un emisor real de comandos MAVLink.

*Plataforma de Herramientas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware para la placa física Universal Robot Tool Controller, 25+ perfiles de herramienta sobre bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — herramienta de escritorio con GUI para grabar placas URTC, CAN-OTA además de SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — herramienta de escritorio de diagnóstico en vivo del bus CAN para placas URTC, un panel por perfil de herramienta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa en navegador a URTC-TESTER vía la Web Serial API, sin instalación local.

*Nodo de Visión IA (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — centro de integración del pipeline de visión Hailo-8, con una comprobación real de preparación de hardware por etapa.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro real de modelos compilados con verificación segura de arquitectura/checksum Hailo.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generador real de pipeline GStreamer + configuración MediaMTX con un límite real de integración HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ley real de corrección Position-Based Visual Servoing, con puerta de seguridad según el estado de zona ascendente.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — comprobación real de invasión de zona y solicitud de parada de emergencia, con exigencia de calibración vigente.

*Nodo Cognitivo IA (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — centro de integración del pipeline cognitivo Hailo-10 (orquestación LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificación/decodificación real de tokens de acción y generación de trayectorias para un modelo Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analizador de intención) con un relé al Watch acotado y con confirmación.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — descomposición de tareas real basada en reglas y recuperación semántica de errores sobre códigos de error del MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — búsqueda real de documentos con TF-IDF solo con la stdlib sobre la documentación Markdown propia de este ecosistema.

*Orquestación y Enjambre*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — centro de integración con un contrato real de informe de salud gRPC/Protobuf y máquina de estados de misión.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — cola de trabajos real basada en prioridad con deduplicación, sobre una API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vigilante real de salud de flota basado en gRPC con reintentos/backoff y detección de discrepancia de identidad.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planificador de rutas 3D real basado en RRT con validación real de colisión de obstáculos/espacio de trabajo.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronización real de estado CRDT LWW-Element-Map, probada con tests de propiedades para convergencia multi-celda.

*Gemelo Digital y Simulación*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — centro de integración para el motor de gemelo digital, con un contrato real de sincronización de compatibilidad de versiones.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — enclavamiento de seguridad real hardware-in-the-loop, dirigiendo comandos entre la simulación y el hardware real.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática directa real y validación de límites de articulación sobre un subconjunto real de URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — generador procedural real de escenas 2D con exportación de anotaciones YOLO/COCO.

*Datos y Analítica*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — almacén real de series temporales sobre sqlite3 con una API HTTP real de ingesta/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detector real de anomalías por FFT + línea base estadística con monitorización de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidad sobre el histórico de DATALAKE, con exportación CSV reproducible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingesta CAN/WebSocket hacia DATALAKE, con deduplicación por secuencia.

*Pasarela Industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — centro de integración que retransmite a protocolos industriales, con una capa real de lista blanca de comandos/contrapresión.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espacio de direcciones OPC-UA real, verificado con una sesión de cliente real de protocolo binario.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real con autenticación opcional por cliente y ACLs de topic.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML reales `/probe` y `/current` de MTConnect con salida en modo degradado.

*Herramientas Complementarias y Operaciones del Ecosistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — paneles de Resúmenes Inteligentes y Resaltado de Anomalías sobre DATALAKE/ANOMALY-DETECTOR, con un respaldo estadístico honesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flota con un contrato real y estable de códigos de salida, un cliente genuino y en vivo de la API propia de HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app compañera WearOS con alertas hápticas reales y un relé de voz al teléfono emparejado.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware para un rack de montaje de placas con decodificación real de ID de herramienta y lógica de precalentamiento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware más un compañero de visión real en Python para un cabezal de inspección térmica/RGB.

---

## 📚 Documentación y Comunidad

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — cada subcomando `--cli`, con salida de ejemplo real.
- **[docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md)** — el mecanismo real de `firstrun.sh` que reproduce esta herramienta, y por qué.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pila tecnológica y guías de código para una pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — los estándares de comportamiento esperados en esta comunidad.
- **[SECURITY.md](SECURITY.md)** — cómo reportar una vulnerabilidad, y las áreas reales de seguridad de este proyecto.
- **[SUPPORT.md](SUPPORT.md)** — dónde hacer preguntas y reportar errores.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCIA

GPL-3.0 (software) / CC BY-SA 4.0 (documentación) - ver [LICENSE.md](LICENSE.md).
