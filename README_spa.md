<!-- =============================================================================
HYDRA-UMC-OS-REBUILDER - Builds a ready-to-flash CM5 image
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-OS-REBUILDER banner" width="100%">
</p>

# 📀 HYDRA-UMC-OS-REBUILDER

<p align="center"><a href="README.md">🇺🇸 English</a> | 🇪🇸 <b>Español</b> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 📀 Construye una Imagen Lista para Grabar y Totalmente Actualizada de la CM5

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="Desktop">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Tests-177%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.3.3-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

> **Estado de seguridad física y de ciberseguridad:** este ecosistema no es un sistema de seguridad certificado. Todavía no existe una ruta de E-STOP por hardware, ni límites ni enclavamientos aplicados por el firmware, ni un comando de movimiento verificado; las imágenes de firmware se comprueban con CRC-32 y una firma Ed25519, y una compilación de versión rechaza las claves de desarrollo publicadas (los cabezales de herramienta y las placas de expansión detrás del relé siguen con cargadores de URTC, que usan un HMAC-SHA256 de clave compartida en lugar de una firma); TLS y TLS mutuo son opcionales y están desactivados por defecto; aún no se ha poblado ni probado ninguna placa propia. Lee la [línea base de seguridad](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) y el [modelo de amenazas](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de fiarte de cualquier afirmación de aquí para la seguridad de una persona.

---

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.3.3` |
| Madurez | Funcional |
| Tests | 177 (`python -m pytest -q tests`) |
| Tecnología | Python 3.10+ / PySide6 / QML / Raspberry Pi OS / GitHub raw content |
| Destino | El PC de quien lo usa |
| En hardware real | Todavía no: no consta ninguna ejecución en hardware real para esta versión |

**Ir a:** [Resumen](#-resumen) · [Arquitectura](#-arquitectura) · [Inicio rápido](#-inicio-rápido) · [Pruebas](#-pruebas) · [Estructura del repositorio](#-estructura-del-repositorio) · [Proyectos relacionados](#-proyectos-relacionados)

## 🚦 Estado del proyecto

Cada línea es una parte de este repositorio y la luz dice hasta dónde llega hoy. Se escribe con lo que el repositorio puede demostrar (pruebas, compilaciones, ejecuciones), no con lo previsto.

🟢 Hecho y verificado · 🟡 Funciona, con límites conocidos · 🟠 Hecho a medias o sin verificar · 🔴 Sin hacer o sin funcionar

| Área | Estado | Qué significa aquí |
|---|---|---|
| Software | 🟡 | Funciona para su propósito principal; la comprobación de honestidad de arriba lista lo que aún falta |
| Pruebas | 🟢 | 177 pruebas automáticas, ejecutadas en cada cambio |
| Hardware real | 🔴 | Todavía no: no consta ninguna ejecución en hardware real para esta versión |
| Documentación | 🟢 | README en ocho idiomas, comprobado contra el manifiesto en cada cambio |

## 🎯 Resumen

HYDRA-UMC-OS-REBUILDER es una herramienta de escritorio Windows/Linux -
interfaz gráfica por defecto, CLI completa con `--cli` - que responde a la
pregunta que toda instalación real de CM5 termina necesitando: **"crear una
imagen fresca de tarjeta SD/eMMC, con la versión real más reciente de cada
proyecto del ecosistema ya instalada, y dejarme configurar Wi-Fi/usuario/
hostname/SSH antes de grabarla."**

**Qué contiene la imagen:** las copias de los proyectos en `/opt/hydra-umc/<nombre>` en las versiones del plan y lo que generó la compilación de cada proyecto. No crea usuarios de servicio ni unidades de systemd ni prepara `/etc/hydra-umc`, así que ningún servicio arranca solo en el primer arranque; los scripts de aprovisionamiento de HYDRA-UMC-OS siguen teniendo que ejecutarse en la placa.

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
   imagen de Raspberry Pi OS (Trixie o posterior), así que la tarjeta SD
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

## 🧩 Papel en HYDRA-UMC

**HYDRA-UMC-OS-REBUILDER** construye una imagen nueva de la CM5 con la versión actual de cada proyecto del ecosistema ya incluida, y escribe los ajustes del primer arranque (Wi-Fi, usuario, nombre de equipo, SSH) antes de grabar la imagen. La capa de plataforma que lleva esa imagen la describe `HYDRA-UMC-OS`.

## 🏛️ Arquitectura

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-OS-REBUILDER architecture" width="100%">
</p>

### ARQUITECTURA Y DECISIONES DE DISEÑO

- **Clave SSH del equipo fijada al primer uso y sin país Wi-Fi por defecto.** Una compilación remota rechaza una máquina cuya clave no ha fijado y muestra la huella SHA-256 de la clave; escribe esa huella (comprobada en la propia máquina) y la clave queda fijada: desde entonces solo se acepta esa clave y una distinta se rechaza como clave cambiada. El código de país Wi-Fi de la imagen ya no tiene valor por defecto (`--wifi-country` / el campo de país es obligatorio con una red Wi-Fi), porque fija las reglas de radio del país donde estará la máquina.
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
- **Una configuración de primer arranque que dejaría fuera al operador se rechaza, no se construye.** Desactivar SSH sin configurar ninguna cuenta dejaría las propias imágenes base oficiales de esta herramienta (sin usuario por defecto desde Trixie) sin ninguna vía de acceso - se rechaza salvo que `acknowledge_no_remote_access=True` lo acepte explícitamente. `describe_recovery_procedure()` indica la vía real de recuperación para lo que la configuración deja abierto.
- **Las contraseñas ya no viajan como argumentos.** `--password` y `--wifi-password` siguen funcionando, pero una línea de comandos la ve cualquier usuario de la máquina y `sudo` la escribe en el registro de autenticación, así que la CLI también las lee de `HYDRA_UMC_FIRSTBOOT_PASSWORD` / `HYDRA_UMC_FIRSTBOOT_WIFI_PASSWORD` o, con `--secrets-stdin`, de un objeto JSON (`{"password": "...", "wifiPassword": "..."}`) por la entrada estándar. La compilación remota (SSH) de la GUI las envía así y ya no las pone en el comando que ejecuta.
- **El chroot está completo y la compilación remota va fijada.** La compilación monta `/proc`, `/sys`, `/dev` y `/dev/pts` en la imagen y le da la resolución de nombres del equipo mientras se compilan los proyectos (después se devuelve el `resolv.conf` propio de la imagen), de modo que `pip`, `npm` y `go` llegan a la red desde el chroot. Una compilación remota por SSH instala esta herramienta desde la etiqueta de versión que se está ejecutando (`HYDRA_UMC_REBUILDER_REMOTE_REF` indica otra etiqueta o commit) y compila desde el perfil congelado del plan que se revisó (`profile-build`) en lugar de volver a descubrir el ecosistema en el equipo remoto. Nada de esto se ha ejecutado aún en un equipo Linux real con root.
- **Un perfil congelado es una receta real y persistida, nunca se vuelve a descargar.** `freeze_profile()`/`profile-build` de `profile_manifest.py` fijan cada proyecto al SHA exacto del commit con el que se probó - una compilación posterior nunca sustituye en silencio lo que GitHub llame «latest» en ese momento. `diff_profile()` compara un perfil congelado con el ecosistema real proyecto a proyecto (no como un único booleano), porque los números de versión de este ecosistema son un cuentakilómetros en base 10 sin significado semántico y nunca pueden ser, por sí solos, una señal honesta de compatibilidad.
- **Hash de contraseña SHA-512-crypt real, no el módulo `crypt` de la
  stdlib.** `crypt` solo envuelve la llamada propia de libc del *host*
  (solo Unix, y eliminado directamente en Python 3.13) - `passlib` produce
  el mismo formato real `$6$...` byte a byte que espera `chpasswd -e`, en
  cualquier plataforma donde corra esta herramienta, incluyendo Windows. El hash usa 500000 rondas, no las 5000 por defecto de glibc, que datan del año 2000, de modo que atacar una copia de la imagen o de `/etc/shadow` cuesta mucho más; el yescrypt (`$y$`) que prefiere el propio dispositivo no puede generarse de forma portable desde Python en Windows.

## 🚀 Inicio rápido

Requiere Python 3.10 o superior.

```bash
./build.sh             # Linux, macOS (build.bat on Windows)
./run.sh               # windowed GUI
./run.sh --cli status  # latest real version of every project
```

## 🧪 Pruebas

177 pruebas automáticas se ejecutan con `python -m pytest -q tests`. No necesitan hardware ni nada fuera de esta máquina.

El CI ejecuta `HYDRA_UMC_CI=1 python tools/ci_validate.py`, que comprueba el manifiesto, los documentos, los ocho README y las imágenes.

## 🏗️ Compilación y publicación

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
- `--cli config`/`build-image` rechaza con «no login path at all»: se desactivó SSH sin configurar una cuenta - configura una, o pasa `acknowledge_no_remote_access=True` (GUI/API) si hay otra forma segura de entrar. Consulta `describe_recovery_procedure()`.
- `profile-build` rechaza un proyecto con «no real, resolved commit SHA»: el manifiesto congelado es anterior a que un repositorio se renombrara o se hiciera privado - vuelve a congelar el perfil (`profile-freeze`) contra el ecosistema real actual.
- `profile-build` rechaza con «missing N required resource(s)»: un proyecto curado con `profile-set-required-resources` ejecutó su propio `build.sh`, pero una ruta relativa declarada sigue sin existir en el disco después - una compilación real e incompleta, nunca rescatada por un archivo sobrante en otro sitio; la imagen no se promueve.
- La pestaña Estado del Ecosistema de la GUI se queda vacía: revisa tu red
  - esta herramienta necesita una conexión real a
  `github.com`/`raw.githubusercontent.com` para `status`/el descubrimiento,
  igual que el propio `hydra-umc-updater`.
- **El número de proyectos sigue disminuyendo en cada actualización (p. ej. 42 -> 9 -> 0), incluso tras reiniciar la aplicación** - un error real no informado antes: resolver el SHA de commit real de cada proyecto gasta una llamada a `api.github.com` POR PROYECTO, con un presupuesto *sin autenticar* de 60 peticiones POR HORA compartido con todo lo demás que hace esta herramienta (y `hydra-umc-updater`) - con más de 50 proyectos reales del ecosistema, una sola actualización puede agotarlo, y lo que tiene que reiniciarse es la ventana horaria de GitHub (no el estado de esta aplicación), algo que un reinicio no arregla. Corregido para informarlo con honestidad en vez de listar en silencio menos proyectos: el aviso ámbar bajo la lista de proyectos indica exactamente cuántos proyectos se resolvieron antes del límite y cuándo se reinicia el límite de GitHub (ver `ecosystem_plan.GitHubRateLimitedError`). Define la variable de entorno `GITHUB_TOKEN` (un simple token de acceso personal de GitHub, sin permisos para repositorios públicos) antes de lanzar esta herramienta para subir el presupuesto a 5000/hora - tanto el listado de repositorios como la resolución del SHA por proyecto lo respetan ahora de forma consistente.

## 📂 Estructura del repositorio

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-OS-REBUILDER" width="100%">
</p>

<details>
<summary>Versión en texto del árbol</summary>

```text
HYDRA-UMC-OS-REBUILDER/
├── src/hydra_umc_os_rebuilder/   código fuente
│   ├── __init__.py               Versión del paquete
│   ├── ecosystem_plan.py         Plan real de proyectos/versiones CM5, construido sobre el descubrimiento propio de hydra_umc_updater
│   ├── firstboot_config.py       Generador puro de firstrun.sh/cmdline.txt - sin acceso al sistema de archivos; protección de recuperación
│   ├── profile_manifest.py       Manifiestos de perfil de versión congelados: congelar/comparar/actualizar selectivamente, nunca "lo último" a mitad de ensayo
│   ├── image_builder.py          Pipeline real de descarga/montaje loop/instalación en chroot, limitado a Linux/root
│   ├── i18n.py                   Traducciones reales y completas de la GUI (8 idiomas)
│   ├── qt_gui.py                 puente Qt Quick sobre los módulos de la CLI
│   ├── qml/Main.qml              Interfaz temática de escritorio: Estado del Ecosistema / Crear Imagen / Configuración de Primer Arranque
│   ├── main.py                   Despacho: GUI por defecto, --cli para status/config/build-image
│   ├── remote_install.py         De qué instala y compila una compilación remota (revisión fijada, no la punta de main)
│   └── ssh_hostkeys.py           Confianza en el primer uso de la clave SSH de la máquina de compilación remota, con huella fijada
├── tests/                        Tests reales: firstboot_config, ecosystem_plan, profile_manifest, image_builder, i18n, main
├── docs/                         documentos del proyecto
├── images/                       Recursos, icono de la app y banner
├── tools/                        herramientas del proyecto y comprobaciones del CI
├── .github/                      flujo de CI y plantillas de incidencias
├── build.sh / build.bat          venv + instalación editable + comprobación de compilación
├── run.sh / run.bat              GUI por defecto / punto de entrada CLI
├── run-gui.vbs                   Lanzador gráfico en Windows sin ventana de consola
├── bump_version.py               Incremento de versión tipo cuentakilómetros (solo lo ejecuta el comando `bump` explícito)
├── bump_manifest_version.py      Sincroniza la versión de hydra-umc.project.json con la nativa (--sync)
├── CHANGELOG.md                  qué cambió en cada versión
├── build-test.sh                 comprobación de compilación sin cambios
├── hydra-umc.project.json        manifiesto: versión, madurez, familia
├── pyproject.toml                metadatos del paquete
└── test.sh                       ejecuta las pruebas
```

</details>

## 🗺️ Hoja de ruta y límites conocidos

**Límites conocidos hoy**

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
- Una casilla en la GUI para `acknowledge_no_remote_access` - hoy la GUI muestra con honestidad el mensaje real de `FirstBootConfigError` (sin fallo ni acción silenciosa) pero no tiene un control dedicado para aceptarlo, solo la CLI/API.
- Un panel de la GUI sobre `profile_manifest.py` (congelar/comparar/actualizar desde el escritorio, no solo desde la CLI).

## 🌍 Idiomas

Este README y los documentos del repositorio existen en ocho idiomas: inglés, español, alemán, francés, italiano, japonés, chino y portugués (Portugal). Se escriben a la vez y el CI comprueba que los ocho ficheros tengan las mismas secciones y los mismos enlaces.

## 🔗 Proyectos relacionados

Este proyecto es parte del ecosistema de robótica HYDRA-UMC del mismo autor (JuanenRac / Electro Hobby 3D). Vale la pena conocerlo, ya que una petición podría en realidad ser sobre alguno de estos en vez de sobre este repositorio.

**Directamente Relacionados**
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — la capa de producto reproducible de Raspberry Pi OS de la que esta herramienta construye realmente una imagen: agente de solo lectura, configuración/perfiles validados, aprovisionamiento de primer contacto Wi-Fi.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — la herramienta hermana de operaciones del ecosistema de la que esta depende como librería real para el descubrimiento en GitHub - detecta, instala y actualiza manualmente todo el ecosistema en una máquina ya en marcha, mientras que esta herramienta construye una nueva desde cero.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinador de incidencias de mantenimiento: un rol edge de bajo privilegio recopila un snapshot de inventario/salud saneado, un rol control-plane lo renderiza de solo lectura y pide a un proveedor de IA que sugiera un diagnóstico - nunca aplica un parche ni despliega nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — host de desarrollo reproducible (Raspberry Pi 5 / CM5) que almacena el código del ecosistema y ejecuta tareas acotadas de compilación/pruebas bajo una cola duradera; un rol de desarrollo dedicado, explícitamente distinto de un CM5 operativo.

**También Parte del Ecosistema**

*Núcleo de Hardware y Plataforma*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — el contrato JSON-Schema compartido y la barrera de software de puerta de trabajos contra la que cada bridge valida sus comandos (no es una función de seguridad certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registro declarativo y validador de manifiestos de adaptador para conectores de máquinas externas; extiende la propia idea de contrato del SDK a máquinas externas sin sustituir a los proyectos de pasarela industrial.

*Backend y Clientes Principales*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — el diseño de la placa madre del brazo robótico: host CM5 + coprocesador STM32H745 de doble núcleo, pensado para coordinar hasta 8 brazos herramienta por CAN-OTA/SPI-OTA (firmware en fase temprana; todavía no hay ninguna placa poblada).
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — el backend real sin interfaz (REST/WebSocket) con el que habla de verdad cada cliente de control.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — panel de control web con visualización 3D multi-robot en tiempo real.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de mando de enjambre de escritorio (PySide6) para varios servidores a la vez.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app de control Android nativa con login biométrico y una compañera Wear OS emparejada.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app de control iOS/iPadOS (Flutter) con sincronización WebSocket en tiempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaz táctil nativa para la pantalla DSI de 7" integrada en la propia CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creador/editor gráfico de escritorio de URDF que envía los modelos terminados al catálogo propio de STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de escritorio de modelos STL, que transforma/reemplaza/quita/añade piezas reales en el mismo catálogo de modelos que también edita HYDRA-UMC-EDITOR-URDF.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — barrera de coordinación para flotas AGV/AMR mediante un publicador MQTT VDA 5050 (probado solo contra una flota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinador de alto nivel para celdas CNC con acceso a estado/bytes de control GRBL (probado solo contra un emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — barrera de coordinación para droides con patas/humanoides, con un emisor de comandos para Boston Dynamics Spot (probado solo contra un emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinador de celdas láser que lee 3 señales GPIO de llave/carcasa/enclavamiento (probado solo contra un chip simulado; no puede armar ni disparar un láser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinador seguro de alto nivel del flujo de placas para pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — límite de coordinación segura para impresoras 3D Moonraker/Klipper, con comandos de trabajo realmente controlados.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinador con un transporte ROS 2 rclpy importado de forma perezosa (todavía no ejecutado contra una instalación de ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — barrera de coordinación para UAV equipados con cámara, con un emisor de comandos MAVLink (probado solo contra un emulador).

*Plataforma de Herramientas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware para la placa física Universal Robot Tool Controller, 25+ perfiles de herramienta sobre bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — herramienta de escritorio con GUI para grabar placas URTC, CAN-OTA además de SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — herramienta de escritorio de diagnóstico en vivo del bus CAN para placas URTC, un panel por perfil de herramienta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa en navegador a URTC-TESTER vía la Web Serial API, sin instalación local.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — pasarela delante del bus CAN de URTC: lista de identificadores permitidos, límite de tasa y clave de sesión; software probado en ordenador, aún no en un bus real.

*Nodo de Visión IA (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — centro de integración del pipeline de visión Hailo-8, con una comprobación real de preparación de hardware por etapa.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro real de modelos compilados con verificación segura de arquitectura/checksum Hailo.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generador real de pipeline GStreamer + configuración MediaMTX con un límite real de integración HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ley de corrección Position-Based Visual Servoing con autorización condicionada al estado de zona; todavía sin estimación de pose por cámara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — comprobación real de invasión de zona y solicitud de parada de emergencia, con exigencia de calibración vigente.

*Nodo Cognitivo IA (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — centro de integración del pipeline cognitivo Hailo-10 (orquestación LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificación/decodificación real de tokens de acción y generación de trayectorias para un modelo Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analizador de intención) con un relé al Watch acotado y con confirmación.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — descomposición de tareas real basada en reglas y recuperación semántica de errores sobre códigos de error del MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — búsqueda real de documentos con TF-IDF solo con la stdlib sobre la documentación Markdown propia de este ecosistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de mantenimiento con IA local y con puertas de política para el propio ecosistema - observa, diagnostica y propone arreglos; los dos niveles de riesgo más altos están deliberadamente sin implementar todavía.

*Orquestación y Enjambre*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — centro de integración con un contrato real de informe de salud gRPC/Protobuf y máquina de estados de misión.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — cola de trabajos real basada en prioridad con deduplicación, sobre una API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vigilante real de salud de flota basado en gRPC con reintentos/backoff y detección de discrepancia de identidad.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planificador de rutas 3D real basado en RRT con validación real de colisión de obstáculos/espacio de trabajo.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronización real de estado CRDT LWW-Element-Map, probada con tests de propiedades para convergencia multi-celda.

*Gemelo Digital y Simulación*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — centro de integración para el motor de gemelo digital, con un contrato real de sincronización de compatibilidad de versiones.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — enrutador hardware-in-the-loop con un enclavamiento de software por colisión entre simulación y hardware real (probado sin hardware real).
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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app compañera de WearOS con patrones de alerta háptica y un relé de voz al teléfono emparejado (todavía no ejecutada en un reloj físico).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware para un rack de montaje de placas con decodificación real de ID de herramienta y lógica de precalentamiento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware más un compañero de visión real en Python para un cabezal de inspección térmica/RGB.

## 📚 Documentación

Dónde leer más:

* **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — cada subcomando `--cli`, con salida de ejemplo real.
* **[docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md)** — el mecanismo real de `firstrun.sh` que reproduce esta herramienta, y por qué.
* [Base de seguridad del ecosistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Modelo de amenazas del ecosistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Historial de cambios de este repositorio](CHANGELOG.md)
* [Licencia de este repositorio](LICENSE.md)

## 🤝 Contribuir y comunidad

* Antes de un pull request ejecuta `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (o `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`): debe imprimir `CI_VALIDATION=PASS`. No ejecutes `build.sh` ni `build.bat` para esta comprobación; compilar no es comprobar.
* Los ocho README se escriben desde una sola fuente en HYDRA-UMC-DOCS; no los edites a mano. Cambia la fuente y vuelve a escribirlos con `tools/make_readmes.py`.
* No afirmes en un README lo que no se ha ejecutado: di «simulado» o «sin probar en hardware» cuando esa sea la verdad.
* Mira [CONTRIBUTING.md](CONTRIBUTING.md), el [código de conducta](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) y [SUPPORT.md](SUPPORT.md).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCIA

GPL-3.0-or-later - [LICENSE](LICENSE).
