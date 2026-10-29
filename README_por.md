<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-OS-REBUILDER banner" width="100%">
</p>

# 🏗️ HYDRA-UMC-OS-REBUILDER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | 🇵🇹 <b>Português</b></p>

### 📀 Construa uma imagem da CM5 pronta a gravar e totalmente atual

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="PySide6 Qt Quick desktop GUI">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Windows and Linux">
</p>

> **Estado: v0.3.2, funcional.** A CLI, a descoberta do ecossistema, o gerador
> de configuração de primeiro arranque e o shell da GUI são reais e testados.
> A construção real de imagem de ponta a ponta (descarregar → montar em loop
> → instalar em chroot → desmontar) está implementada, mas só corre num
> anfitrião Linux real com root - ver
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) para a fronteira exata da
> plataforma e o porquê de existir.

**Verificação de honestidade - o que realmente funciona hoje:** a CLI (`main.py`), a descoberta dinâmica do ecossistema que reutiliza o próprio cliente GitHub do `hydra_umc_updater` em vez de uma segunda cópia dele (`ecosystem_plan.py` - que agora pára de forma limpa e reporta uma mensagem real e acionável no instante em que o limite horário de pedidos do próprio GitHub é atingido, em vez de listar em silêncio menos projetos por cada consulta de SHA de commit que falha), o gerador puro de configuração de primeiro arranque `firstrun.sh`/`cmdline.txt`, sem acesso ao sistema de ficheiros e com a sua própria proteção do procedimento de recuperação (`firstboot_config.py`), os manifestos de versão congelados por perfil - congelar/comparar/atualizar seletivamente uma combinação testada de componentes em vez de reconstruir sempre a partir do que for o mais recente (`profile_manifest.py`), as traduções da GUI em 8 idiomas (`i18n.py`) e o shell de desktop Qt Quick (`qt_gui.py`, `qml/Main.qml`, que agora mostra erros reais de descoberta em vez de apenas uma contagem de projetos a diminuir) são reais e testados (132 testes, `pytest`). O pipeline de descarregar/verificar checksum/montar em loop/instalar em chroot/desmontar do `image_builder.py`, o seu cálculo de hash por projeto do que realmente ficou em disco e a sua verificação, antes da promoção, de uma palavra-passe Wi-Fi/chave SSH privada/histórico de shell/ficheiro `.env` que tenha ficado para trás são código real, protegido por `check_build_platform()` - só executam num anfitrião Linux real com root e `losetup`/`chroot` no `PATH`, e não foram executados de ponta a ponta contra uma gravação real num cartão SD/eMMC da CM5 neste ambiente; no Windows ou com um utilizador Linux sem root, `build-image`/`profile-build` terminam cedo com `BUILD_BLOCKED reason=...` em vez de fingirem ter êxito. `status`/`config`/`profile-freeze`/`profile-diff` foram exercitados a sério contra a descoberta real e em direto do GitHub. Consulte o `CHANGELOG.md` para saber exatamente o que já foi entregue e o ROTEIRO abaixo para o que fica em aberto.

---

> **Estado de segurança (safety e security):** este ecossistema não é um sistema de segurança certificado. Ainda não existe um caminho de E-STOP por hardware, nem limites ou interlocks impostos pelo firmware, nem um comando de movimento verificado; as imagens de firmware são verificadas com CRC32 e um HMAC-SHA256 de chave partilhada, não com uma assinatura assimétrica; TLS e TLS mútuo são opcionais e estão desativados por defeito; nenhuma placa própria foi ainda montada ou testada. Leia a [base de segurança](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e o [modelo de ameaças](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de confiar em qualquer afirmação aqui para a segurança de uma pessoa.

## 📋 Num relance

| | |
|---|---|
| Versão | `0.3.2` |
| Maturidade | Funcional |
| Testes | 158 (`pytest`) |
| Tecnologia | Python 3.10+ / PySide6 / QML / Raspberry Pi OS / GitHub raw content |
| Destino | O PC de quem o usa |
| Em hardware real | Ainda não: não há registo de execução em hardware real para esta versão |

## 🚦 Estado do projeto

Cada linha é uma parte deste repositório e a luz diz até onde chega hoje. É escrita com o que o repositório consegue demonstrar (testes, compilações, execuções), não com o que está previsto.

🟢 Feito e verificado · 🟡 Funciona, com limites conhecidos · 🟠 Feito a meio ou ainda por verificar · 🔴 Por fazer ou a não funcionar

| Área | Estado | O que significa aqui |
|---|---|---|
| Software | 🟡 | Funciona para o seu propósito principal; a verificação de honestidade acima lista o que ainda falta |
| Testes | 🟢 | 158 testes automáticos, executados a cada alteração |
| Hardware real | 🔴 | Ainda não: não há registo de execução em hardware real para esta versão |
| Documentação | 🟢 | README em oito idiomas, verificado contra o manifesto a cada alteração |

## 1. 🛠️ VISÃO TÉCNICA GERAL

O HYDRA-UMC-OS-REBUILDER é uma ferramenta de desktop para Windows/Linux - GUI
com janela por defeito, CLI completa com `--cli` - que responde à pergunta a
que um desdobramento real de uma CM5 acaba sempre por precisar de resposta:
**«construa-me uma imagem nova de cartão SD/eMMC, com a versão real mais
atual de cada projeto do ecossistema já instalada, e deixe-me definir
Wi-Fi/utilizador/nome do anfitrião/SSH antes de a gravar.»**

**O que a imagem contém:** as cópias dos projetos em `/opt/hydra-umc/<nome>` nas versões previstas e o que a compilação de cada projeto lá produziu. Não cria utilizadores de serviço nem unidades systemd e não prepara o `/etc/hydra-umc`, pelo que nenhum serviço arranca sozinho no primeiro arranque; os scripts de aprovisionamento do HYDRA-UMC-OS continuam a ter de ser executados na placa.

Faz três coisas reais:

1. **Consulta o GitHub.** Cada repositório do ecossistema HYDRA-UMC/URTC cujo
   próprio `hydra-umc.project.json` declare `"deployment_target": "cm5"` é
   descoberto dinamicamente (nunca uma lista fixa) e a sua versão publicada
   atual é lida - dependendo do `hydra-umc-updater` como biblioteca real para
   isso, e não de uma segunda reimplementação, a derivar de forma
   independente, do seu próprio código de descoberta.
2. **Constrói uma imagem real.** Descarrega uma imagem base fixada e com
   checksum verificado do Raspberry Pi OS, monta-a em loop e instala/atualiza
   cada projeto descoberto executando o **`build.sh` desse próprio projeto**
   dentro do chroot da própria imagem - nunca uma reimplementação dos passos
   de compilação de qualquer projeto.
3. **Escreve a configuração real de primeiro arranque.** Nome do anfitrião,
   um utilizador novo com uma palavra-passe com hash real do `passlib`,
   Wi-Fi, fuso horário, disposição do teclado e SSH - exatamente o mesmo
   mecanismo `firstrun.sh` que o ecrã «OS Customisation» do próprio Raspberry
   Pi Imager usa numa imagem Raspberry Pi OS (Trixie+), pelo que o cartão SD
   resultante se comporta exatamente como um que o próprio Raspberry Pi Imager
   teria produzido. Ver [docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md).
4. **Verifica a sua própria saída antes de a promover.** Antes de a imagem
   construída ser movida para o seu caminho final, o rootfs montado é
   verificado quanto a uma palavra-passe Wi-Fi real deixada num
   `wpa_supplicant.conf`/perfil de ligação do NetworkManager, uma chave SSH
   privada real, um histórico de shell não vazio ou um ficheiro `.env`
   perdido - qualquer achado real bloqueia a promoção por completo, tal como
   uma falha de limpeza já o faz. A verificação de checksum só cobria a imagem
   base de ENTRADA; esta é a primeira verificação do que a própria construção
   deixa na SAÍDA.

```
$ hydra-umc-os-rebuilder --cli status
HYDRA-UMC-SERVER 0.4.8 (api/node)
HYDRA-UMC-VISION-STREAMER 0.0.3 (service/python)
HYDRA-UMC-GATEWAY-INDUSTRIAL 0.0.3 (api/node)
...
TOTAL=27

$ hydra-umc-os-rebuilder --cli config --out ./boot \
    --hostname hydra-umc-cm5 --username hydra-umc --password 'change-me' \
    --wifi-ssid MyNetwork --wifi-password 'wifi-pass' --wifi-country ES
CONFIG_WRITTEN out=boot firstrun=firstrun.sh
```

Executá-lo sem argumentos abre a mesma informação num shell de desktop Qt
Quick - reutilizando a linguagem visual do próprio HYDRA-UMC-UPDATER (a mesma
paleta escura, tipografia e conjunto de componentes) em três separadores:
Estado do ecossistema, Construir imagem e Configuração de primeiro arranque.

## 2. 🧱 ARQUITETURA E DECISÕES DE DESIGN

- **Chave SSH da máquina fixada na primeira utilização e sem país Wi-Fi por omissão.** Uma compilação remota recusa uma máquina cuja chave não fixou e mostra a impressão digital SHA-256 da chave; introduza essa impressão digital (verificada na própria máquina) e a chave fica fixada: daí em diante só essa chave é aceite e uma diferente é recusada como chave alterada. O código de país Wi-Fi da imagem deixou de ter valor por omissão (`--wifi-country` / o campo do país é obrigatório com uma rede Wi-Fi), porque define as regras de rádio do país onde a máquina vai estar.
- **O `ecosystem_plan.py` nunca reimplementa a descoberta do GitHub.**
  Depende do `hydra-umc-updater` como pacote Python real
  (`hydra_umc_updater.github_client.discover_remote_projects()`) em vez de uma
  segunda cópia da sua lógica de validação de manifestos/repetição/backoff - uma
  correção ou melhoria feita aí beneficia esta ferramenta automaticamente.
- **O `image_builder.py` nunca reimplementa a compilação de um projeto.** Cada
  projeto do ecossistema é clonado e colocado no seu próprio SHA de commit real
  e imutável (resolvido a partir do GitHub no momento do planeamento, nunca um
  nome de ramo mutável que se pudesse mover entre o planeamento e a
  construção) e compilado executando o SEU PRÓPRIO `build.sh`, em chroot no
  rootfs de destino - o mesmo princípio de «delegar no script de compilação de
  cada projeto» que o próprio `install.py` do `hydra-umc-updater` já documenta.
  A versão reportada para cada projeto instalado é lida de volta do seu próprio
  manifesto DEPOIS de o `build.sh` ter corrido, e não do valor pré-obtido do
  plano - esse passo de compilação sobe a versão por si, a convenção universal
  deste ecossistema.
- **A fronteira de plataforma Linux/root é sempre verificada primeiro.** O
  `check_build_platform()` é a primeiríssima coisa que o `build_image()` faz -
  uma construção que não faz nada em silêncio num anfitrião não suportado
  (Windows, um utilizador Linux sem root, um `losetup`/`chroot` em falta) seria
  pior do que uma que se recusa a arrancar com um motivo claro.
- **O `firstboot_config.py` é um gerador puro, sem efeitos secundários.** Só
  produz conteúdo de ficheiros em texto simples (uma cadeia `firstrun.sh`, uma
  cadeia de remendo do `cmdline.txt`) - nunca toca numa imagem ou sistema de
  ficheiros reais, pelo que continua trivialmente testável sem root nem uma
  imagem real. Só o `image_builder.py` é responsável por escrever de facto esse
  conteúdo numa partição de arranque real.
- **Uma configuração de primeiro arranque que deixaria o operador de fora é
  recusada, não construída.** Desativar o SSH sem configurar nenhuma conta
  deixa as imagens base oficiais desta ferramenta (sem utilizador por defeito
  no Trixie e posteriores) sem nenhum caminho de login - recusado a menos que
  `acknowledge_no_remote_access=True` o aceite explicitamente.
  O `describe_recovery_procedure()` indica o caminho de recuperação real para o
  que a configuração deixar em aberto.
- **Um perfil congelado é uma receita real e persistida, nunca voltada a
  obter.** O `freeze_profile()`/`profile-build` do `profile_manifest.py` fixa
  cada projeto no SHA de commit exato em que foi testado - uma construção
  posterior nunca substitui em silêncio o que o GitHub chame «mais recente» nesse
  momento. O `diff_profile()` compara um perfil congelado com o ecossistema em
  direto projeto a projeto (não como um único booleano), já que os próprios
  números de versão deste ecossistema são um odómetro em base 10 sem significado
  de versionamento semântico e nunca podem ser, por si, um sinal honesto de
  compatibilidade.
- **Hash de palavra-passe SHA-512-crypt real, não o módulo `crypt` da biblioteca
  padrão.** O `crypt` só envolve a chamada de libc do *próprio anfitrião*
  (apenas Unix, e removido por completo no Python 3.13) - o `passlib` produz o
  formato real `$6$...` byte a byte idêntico que o `chpasswd -e` espera, em
  todas as plataformas em que esta própria ferramenta corre, incluindo o
  Windows. O hash usa 500000 rondas, e não as 5000 por defeito do glibc, que
  datam do ano 2000, pelo que atacar uma cópia da imagem ou de `/etc/shadow`
  custa muito mais; o yescrypt (`$y$`) que o próprio dispositivo prefere não
  pode ser produzido de forma portável a partir do Python no Windows.
- **As palavras-passe já não viajam como argumentos.** `--password` e `--wifi-password` continuam a funcionar, mas uma linha de comandos é visível a todos os utilizadores da máquina e o `sudo` escreve-a no registo de autenticação; a CLI lê-as por isso também de `HYDRA_UMC_FIRSTBOOT_PASSWORD` / `HYDRA_UMC_FIRSTBOOT_WIFI_PASSWORD` ou, com `--secrets-stdin`, de um objeto JSON (`{"password": "...", "wifiPassword": "..."}`) na entrada padrão. A compilação remota (SSH) da interface envia-as assim e já não as põe no comando executado.
- **O chroot está completo e a compilação remota fica fixada.** A compilação monta `/proc`, `/sys`, `/dev` e `/dev/pts` na imagem e dá-lhe a resolução de nomes do equipamento enquanto os projetos são compilados (o `resolv.conf` próprio da imagem é reposto no fim), para que `pip`, `npm` e `go` cheguem à rede a partir do chroot. Uma compilação remota por SSH instala esta ferramenta a partir da etiqueta da versão em execução (`HYDRA_UMC_REBUILDER_REMOTE_REF` indica outra etiqueta ou commit) e compila a partir do perfil congelado do plano revisto (`profile-build`) em vez de voltar a descobrir o ecossistema no equipamento remoto. Nada disto correu ainda num equipamento Linux real com root.

## 📂 ESTRUTURA DE DIRETORIAS

```
HYDRA-UMC-OS-REBUILDER/
├── src/hydra_umc_os_rebuilder/
│   ├── __init__.py          # Versão do pacote
│   ├── ecosystem_plan.py    # Plano real de projetos/versões da CM5, construído sobre a própria descoberta do hydra_umc_updater
│   ├── firstboot_config.py  # Gerador puro de firstrun.sh/cmdline.txt - sem acesso ao sistema de ficheiros; proteção do procedimento de recuperação
│   ├── profile_manifest.py  # Manifestos de versão congelados por perfil: congelar/comparar/atualizar seletivamente, nunca «mais recente» a meio de um ensaio
│   ├── image_builder.py     # Pipeline real de descarregar/montar em loop/instalar em chroot, protegido por Linux/root
│   ├── i18n.py               # Traduções reais e completas da GUI (8 idiomas)
│   ├── qt_gui.py             # Ponte Qt Quick sobre os módulos reais voltados para a CLI acima
│   ├── qml/Main.qml          # Shell de desktop com tema: Estado do ecossistema / Construir imagem / Configuração de primeiro arranque
│   ├── main.py                # Despacho: GUI por defeito, --cli para status/config/build-image
│   ├── remote_install.py      # De onde uma compilação remota instala e compila (revisão fixada, não a ponta de main)
│   └── ssh_hostkeys.py        # Confiança na primeira utilização da chave SSH da máquina de compilação remota, com impressão digital fixada
├── tests/                    # Testes reais: firstboot_config, ecosystem_plan, profile_manifest, image_builder, i18n, main
├── docs/
│   ├── CLI_REFERENCE.md       # Referência de comandos
│   ├── FIRST_BOOT_CONFIG.md   # O mecanismo real de firstrun.sh que esta ferramenta reproduz, e porquê
│   └── MATURITY_CRITERIA.md   # Critérios de saída da maturidade (o que tem de ser verdade para subir de nível)
├── images/                    # Multimédia, ícone da aplicação e faixa
├── tools/
│   ├── build_test.py          # Verificação de compilação sem alterar versões
│   ├── ci_validate.py         # Validação de manifesto/CHANGELOG/docs usada pelo CI
│   ├── _doc_policy.py         # Regras de documentação partilhadas pela família (cópia da de HYDRA-UMC-SDK, mantida em sincronia)
│   ├── _readme_parity.py      # Verificação de que os oito README partilham a mesma estrutura (cópia da de HYDRA-UMC-SDK, mantida em sincronia)
│   └── hydra_project_tool.py  # Os mesmos comandos em todos os repositórios: validate, test, ci, version, status, bump
├── build.sh / build.bat       # venv + instalação editável + verificação de compilação
├── run.sh / run.bat           # GUI por defeito / ponto de entrada da CLI
├── run-gui.vbs                # Lançador gráfico para Windows sem janela de consola
├── bump_version.py            # Subida de versão ao estilo conta-quilómetros (executada só pelo comando `bump` explícito)
└── bump_manifest_version.py   # Sincroniza a versão do hydra-umc.project.json com a nativa (--sync)
```

## ⚙️ GUIA DE COMPILAÇÃO E EXECUÇÃO

```bash
chmod +x build.sh   # uma única vez
./build.sh          # cria o .venv, pip install -e ".[dev,gui]", verifica a compilação de tudo, executa o pytest
./run.sh                                # GUI com janela (por defeito)
./run.sh --cli status                   # a versão real mais recente no GitHub de cada projeto do ecossistema
./run.sh --cli config --out ./boot ...  # escreve a configuração de primeiro arranque (ver docs/CLI_REFERENCE.md para cada flag)
./run.sh --cli build-image --out FILE   # constrói uma .img pronta a gravar (só Linux/root)
./run.sh --cli profile-freeze --name cm5-production --out profiles/cm5-production.json  # fixa uma combinação testada real
./run.sh --cli profile-diff --manifest profiles/cm5-production.json                     # o que mudou desde que foi congelada
./run.sh --cli profile-update --manifest profiles/cm5-production.json --project X       # volta a congelar apenas X, deixa o resto fixado
./run.sh --cli profile-set-required-resources --manifest profiles/cm5-production.json --project X --resource dist/index.html  # define o que X tem de produzir
./run.sh --cli profile-build --manifest profiles/cm5-production.json --out FILE         # constrói a partir EXATAMENTE desse perfil congelado
```

No Windows: `build.bat` e depois `run.bat` (GUI) / `run.bat --cli status` /
`run.bat --cli config ...`. O `build-image` continua a precisar de um anfitrião
Linux real com root de qualquer das formas - ver
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

**Resolução de problemas**

- O `--cli build-image` termina com `BUILD_BLOCKED reason=...`: leia o motivo -
  nomeia a peça exata em falta (não é Linux, não é root, ou uma ferramenta
  concreta em falta no `PATH`) em vez de uma falha genérica.
- O `--cli config` levanta um erro de validação: o nome do anfitrião/utilizador/
  código de país Wi-Fi que indicou não corresponde à forma real e estreita que
  esses campos exigem - ver a validação do próprio `firstboot_config.py`.
- O `--cli config`/`build-image` recusa com «no login path at all»: o SSH foi
  desativado sem configurar também uma conta - configure uma, ou passe
  `acknowledge_no_remote_access=True` (GUI/API) se houver outra forma de entrar
  com certeza. Ver `describe_recovery_procedure()`.
- O `profile-build` recusa um projeto com «no real, resolved commit SHA»: o
  manifesto congelado é anterior a um repositório ter sido renomeado ou tornado
  privado - volte a congelar o perfil (`profile-freeze`) contra o ecossistema
  atual em direto.
- O `profile-build` recusa com «missing N required resource(s)»: um projeto
  definido com `profile-set-required-resources` teve o seu próprio `build.sh`
  executado, mas um caminho relativo declarado continua a não existir em disco
  depois - uma construção real e incompleta, nunca salva por um ficheiro
  deixado noutro sítio; a imagem não é promovida.
- O separador Estado do ecossistema da GUI fica vazio: verifique a sua rede -
  esta ferramenta precisa de uma ligação real a `github.com`/
  `raw.githubusercontent.com` para o `status`/descoberta, tal como o próprio
  `hydra-umc-updater`.
- **A contagem de projetos continua a diminuir em atualizações repetidas (p.
  ex. 42 -> 9 -> 0), mesmo depois de reiniciar a aplicação** - um erro real,
  anteriormente não reportado: resolver o SHA de commit real de cada projeto
  gasta uma chamada à `api.github.com` POR PROJETO, num orçamento *sem
  autenticação* de 60 pedidos POR HORA partilhado com tudo o resto que esta
  ferramenta (e o `hydra-umc-updater`) faz - com mais de 50 projetos reais do
  ecossistema, uma única atualização pode esgotá-lo, e é a própria janela horária
  do GitHub (não o estado desta aplicação) que tem de se repor, algo que um
  reinício não resolve. Corrigido para o reportar com honestidade em vez de
  listar em silêncio menos projetos: o aviso âmbar sob a lista de projetos
  nomeia agora exatamente quantos projetos foram resolvidos antes do muro e
  quando o limite do GitHub se repõe (ver
  `ecosystem_plan.GitHubRateLimitedError`). Defina uma variável de ambiente
  `GITHUB_TOKEN` (um token de acesso pessoal simples do GitHub, sem âmbitos para
  repositórios públicos) antes de lançar esta ferramenta para aumentar o
  orçamento para 5000/hora - tanto a listagem de repositórios como a resolução
  do SHA de commit por projeto o respeitam agora de forma consistente.

## 🚀 ROTEIRO

- Suporte a cloud-init como mecanismo alternativo de primeiro arranque para uma
  imagem base que não seja Pi, ao lado do caminho atual do `firstrun.sh`.
- Atualizações incrementais de imagem (remendar uma `.img` existente no sítio
  em vez de uma reconstrução completa) quando houver uma necessidade real para
  lá de uma construção de raiz.
- Um modo de saída `--json` para o `status`, para o usar em scripts.
- Executável autónomo da GUI empacotado (PyInstaller), em linha com a convenção
  `build_exe.bat`/`.sh` do próprio HYDRA-UMC-SUITE, para uma instalação com
  duplo clique sem qualquer passo de `pip`/venv.
- Uma caixa de seleção na GUI para `acknowledge_no_remote_access` - hoje a GUI
  mostra com honestidade a mensagem real do `FirstBootConfigError` (sem falha,
  sem operação nula silenciosa), mas não tem controlo próprio para a aceitar,
  só a CLI/API o têm.
- Um painel da GUI sobre o `profile_manifest.py` (congelar/comparar/atualizar a
  partir do shell de desktop, e não apenas da CLI).

---

## 🔗 Projetos relacionados

Este projeto faz parte do ecossistema de robótica HYDRA-UMC do mesmo autor (JuanenRac / Electro Hobby 3D). Vale a pena conhecê-los, porque um pedido pode ser, na verdade, sobre um destes e não sobre este repositório.

**Diretamente relacionados**
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — a camada de produto reproduzível do Raspberry Pi OS DE QUE esta ferramenta realmente constrói uma imagem: agente só de leitura, configuração/perfis validados, provisionamento Wi-Fi de primeiro contacto.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — a ferramenta irmã de operações do ecossistema de que esta depende como biblioteca real para a descoberta no GitHub - deteta, instala e atualiza manualmente todo o ecossistema numa máquina já em funcionamento, onde esta ferramenta constrói uma nova de raiz.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordenador de incidentes de manutenção: um papel de borda de poucos privilégios recolhe um inventário/estado higienizado, um papel de plano de controlo mostra-o só de leitura e pede a um fornecedor de IA que sugira um diagnóstico; nunca aplica um patch nem implanta nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — anfitrião de desenvolvimento reproduzível (Raspberry Pi 5 / CM5) que guarda o código-fonte do ecossistema e executa tarefas limitadas de compilação/teste numa fila durável; um papel de desenvolvimento dedicado, explicitamente não um CM5 operacional.

**Também fazem parte do ecossistema**

*Hardware e plataforma centrais*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — o contrato JSON-Schema partilhado e a fronteira de software de controlo de trabalhos contra a qual cada bridge valida os seus comandos (não é uma função de segurança certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registo declarativo de manifestos de adaptador e validador para conectores de máquinas externas; estende a ideia de contrato do SDK a máquinas externas sem substituir os projetos de gateway industrial.

*Backend central e clientes*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — o desenho da placa-mãe do braço robótico: anfitrião CM5 + STM32H745 de dois núcleos, pensado para orquestrar até 8 braços de ferramenta por CAN-OTA/SPI-OTA (firmware numa fase inicial; ainda sem placa montada).
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — o back-end headless real (REST/WebSocket) com que todos os clientes de controlo realmente comunicam.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — painel web de controlo com visualização 3D em tempo real de vários robôs.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de comando de enxame para desktop (PySide6) para vários servidores ao mesmo tempo.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — aplicação Android nativa de controlo, com início de sessão biométrico e um companheiro Wear OS emparelhado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — aplicação de controlo para iOS/iPadOS (Flutter) com sincronização WebSocket em tempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tátil nativa para o ecrã tátil DSI de 7" integrado, executada no próprio CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — criador/editor gráfico de URDF para desktop que envia os modelos concluídos para o catálogo do STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de modelos STL para desktop que transforma/substitui/remove/adiciona peças reais no mesmo catálogo de modelos que o HYDRA-UMC-EDITOR-URDF também edita.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — fronteira de coordenação para frotas AGV/AMR através de um publicador MQTT VDA 5050 (testado apenas contra uma frota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordenador de células CNC de alto nível com acesso ao estado GRBL e aos bytes de controlo (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — fronteira de coordenação para droides com patas/humanoides, com um emissor de comandos para o Boston Dynamics Spot (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordenador de células laser que lê 3 sinais GPIO (chave, caixa e interlock) (testado apenas contra um chip simulado; não pode armar nem disparar um laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordenador seguro de fluxo de placa de alto nível para pick-and-place com OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — fronteira de coordenação segura para impressoras 3D Moonraker/Klipper, com comandos de trabalho reais protegidos por portas.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordenador com um transporte ROS 2 baseado em rclpy importado sob demanda (ainda não executado contra uma instalação ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — fronteira de coordenação para UAV com câmara, com um emissor de comandos MAVLink (testado apenas contra um emulador).

*Plataforma de ferramentas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware da placa física Universal Robot Tool Controller, mais de 25 perfis de ferramenta por barramento CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — ferramenta gráfica de gravação para desktop das placas URTC, por CAN-OTA e também SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — ferramenta de diagnóstico CAN em tempo real para desktop das placas URTC, com um painel por perfil de ferramenta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa no navegador ao URTC-TESTER através da Web Serial API, sem instalação local.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — gateway à frente do barramento CAN do URTC: lista de identificadores permitidos, limite de taxa e chave de sessão; software testado num computador, ainda não num barramento real.

*Nó de IA de visão (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — centro de integração do pipeline de visão Hailo-8, com uma verificação real de prontidão de hardware por fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registo real de modelos compilados com verificação segura de carga por arquitetura Hailo e soma de verificação.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer real e gerador de configuração MediaMTX com uma fronteira de integração HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — lei de correção de servovisão baseada em posição com autorização condicionada ao estado da zona; ainda sem estimativa de pose por câmara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — lógica v0 de violação de zonas, atualidade da calibração e pedido de E-STOP que lê as posições dos objetos de um ficheiro; nenhum detetor a alimenta e ainda não há E-STOP físico ligado.

*Nó de IA cognitiva (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — centro de integração do pipeline cognitivo do Hailo-10 (orquestração de LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificação/descodificação real de tokens de ação e geração de trajetórias para um modelo Visão-Linguagem-Ação.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analisador de intenções) com um relé para o relógio limitado e protegido por confirmação.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — decomposição real de tarefas baseada em regras e recuperação semântica de erros sobre os códigos de erro do MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — pesquisa real de documentos TF-IDF só com a biblioteca padrão sobre a documentação Markdown deste ecossistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de manutenção de IA local, protegido por políticas, para o próprio ecossistema: observa, diagnostica e propõe correções; os dois níveis de maior risco não estão implementados de propósito.

*Orquestração e enxame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — centro de integração com um contrato real de relatório de saúde gRPC/Protobuf e uma máquina de estados de missões.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — fila real de trabalhos por prioridade com deduplicação, sobre uma API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vigilante real de saúde da frota por gRPC com repetição/recuo e deteção de identidade incoerente.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planeador real de trajetórias 3D baseado em RRT com validação real de colisões com obstáculos e espaço de trabalho.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronização real de estado CRDT LWW-Element-Map, testada por propriedades para a convergência de várias células.

*Gémeo digital e simulação*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — centro de integração do motor de gémeo digital, com um contrato real de sincronização de compatibilidade de versões.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — encaminhador hardware-in-the-loop com um interlock de software de colisão entre a simulação e o hardware real (testado sem hardware real).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática direta real e validação de limites de juntas sobre um subconjunto real de URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — gerador procedural real de cenas 2D com exportação de anotações YOLO/COCO.

*Dados e análise*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — armazém real de séries temporais sobre sqlite3 com uma API HTTP real de ingestão/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detetor real de anomalias por FFT e linha de base estatística, com monitorização de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidade sobre o histórico do DATALAKE, com exportação CSV reprodutível.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingestão CAN/WebSocket para o DATALAKE, com deduplicação por sequência.

*Gateway industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — centro de integração que retransmite para protocolos industriais, com uma camada real de lista de comandos permitidos e contrapressão.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espaço de endereços OPC-UA real, verificado com uma sessão de cliente real do protocolo binário.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real com autenticação opcional por cliente e ACL de tópicos.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML MTConnect `/probe` e `/current` reais com saída em modo degradado.

*Ferramentas complementares e operações do ecossistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — painéis de Resumos Inteligentes e Realce de Anomalias sobre o DATALAKE/ANOMALY-DETECTOR, com um recurso estatístico honesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI da frota com um contrato de códigos de saída real e estável, um cliente vivo genuíno da API do HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — aplicação companheira WearOS com padrões de alerta tátil e um relé de voz para o telemóvel emparelhado (ainda não executada num relógio físico).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware de um rack de montagem de placas com descodificação real do ID da ferramenta e lógica de pré-aquecimento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware mais um companheiro de visão em Python real para uma cabeça de ferramenta de inspeção térmica/RGB.

---

## 📚 Documentação e comunidade

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — cada subcomando `--cli`, com saída de exemplo real.
- **[docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md)** — o mecanismo real de `firstrun.sh` que esta ferramenta reproduz, e porquê.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pilha tecnológica e diretrizes de código para um pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — as normas de comportamento esperadas nesta comunidade.
- **[SECURITY.md](SECURITY.md)** — como comunicar uma vulnerabilidade e as áreas de segurança em que este projeto se concentra.
- **[SUPPORT.md](SUPPORT.md)** — onde fazer perguntas e comunicar erros.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENÇA

GPL-3.0-or-later (software) / CC BY-SA 4.0 (documentação) - veja [LICENSE.md](LICENSE.md).

