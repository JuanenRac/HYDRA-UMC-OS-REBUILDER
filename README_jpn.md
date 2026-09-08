<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-OS-REBUILDER バナー" width="100%">
</p>

# 🏗️ HYDRA-UMC-OS-REBUILDER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | 🇯🇵 <b>日本語</b></p>

### 📀 書き込み可能な、完全に最新のCM5イメージを構築する

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="PySide6 Qt Quick デスクトップGUI">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="WindowsとLinux">
</p>

> **ステータス: v0.1.7、スキャフォールディング段階。** CLI、エコシステム
> 検出、初回起動設定ジェネレータ、GUIはいずれも実際に動作しテスト済み
> です。実際のエンドツーエンドのイメージビルド（ダウンロード → ループ
> マウント → chrootインストール → アンマウント）は実装済みですが、root
> 権限を持つ実際のLinuxホスト上でのみ動作します - 正確なプラットフォーム
> の境界とその理由については
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) を参照してください。

---

## 1. 🛠️ 技術概要

HYDRA-UMC-OS-REBUILDERは、実際のCM5導入が最終的に必ず必要とする質問に
答えるWindows/Linuxデスクトップツールです - デフォルトはウィンドウ型
GUI、`--cli` で完全なCLIも利用可能: **「エコシステムの各プロジェクトの
最新の実バージョンをすでにインストール済みの、新しいSDカード/eMMC
イメージを構築し、書き込む前にWi-Fi/ユーザー/ホスト名/SSHを設定させて
ほしい」**。

実際に3つのことを行います：

1. **GitHubを確認する。** HYDRA-UMC/URTCエコシステム内で、自身の
   `hydra-umc.project.json` が `"deployment_target": "cm5"` を宣言して
   いるすべてのリポジトリは動的に検出され（固定リストは一切使わない）、
   その現在公開されているバージョンが読み取られます - これは
   `hydra-umc-updater` を実際のライブラリとして依存することで実現して
   おり、その独自の検出コードから静かに乖離しかねない第二の実装を作ら
   ないためです。
2. **実際のイメージを構築する。** 固定された、チェックサムで検証済みの
   Raspberry Pi OSベースイメージをダウンロードし、ループマウントして、
   検出された各プロジェクトを**そのプロジェクト自身の `build.sh`** を
   イメージのchroot内で実行することでインストール/更新します - どの
   プロジェクトのビルド手順も再実装することはありません。
3. **実際の初回起動設定を書き込む。** ホスト名、`passlib` で実際にハッシュ
   化されたパスワードを持つ新しいユーザー、Wi-Fi、タイムゾーン、キー
   ボードレイアウト、SSH - これはRaspberry Pi Imager自身の「OS
   Customisation」画面がRaspberry Pi OS（Bookworm以降）イメージ上で
   使用しているのと同じ実際の `firstrun.sh` の仕組みであり、結果として
   できあがるSDカードはRaspberry Pi Imager自身が生成したものとまったく
   同じように動作します。詳細は
   [docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md) を参照して
   ください。
4. **公開前に自分自身の出力をスキャンします。** 構築されたイメージが最終
   的なパスに移動される前に、マウントされたrootfsに実際のWi-Fiパスワード
   が `wpa_supplicant.conf`/NetworkManagerの接続プロファイルに残されて
   いないか、実際の秘密鍵、空でないシェル履歴、取り残された `.env`
   ファイルがないかを確認します - 実際の発見があれば、クリーンアップの
   失敗時と同様に公開が完全にブロックされます。チェックサム検証はこれ
   まで入力(ベースイメージ)のみを対象としていました - これはビルド自体
   が出力に残すものに対する初めてのチェックです。

```
$ hydra-umc-os-rebuilder --cli status
HYDRA-UMC-SERVER 0.4.8 (api/node)
HYDRA-UMC-VISION-STREAMER 0.0.3 (service/python)
HYDRA-UMC-GATEWAY-INDUSTRIAL 0.0.3 (api/node)
...
TOTAL=27

$ hydra-umc-os-rebuilder --cli config --out ./boot \
    --hostname hydra-umc-cm5 --username hydra-umc --password '変更してください' \
    --wifi-ssid マイネットワーク --wifi-password 'wifiパスワード' --wifi-country JP
CONFIG_WRITTEN out=boot firstrun=firstrun.sh
```

引数なしで実行すると、同じ情報がQt Quickデスクトップシェルで開きます -
HYDRA-UMC-UPDATERと同じビジュアル言語（同じダークパレット、タイポグラフィ、
コンポーネントセット）を再利用し、エコシステム状態・イメージ作成・初回
起動設定の3つのタブに分かれています。

## 2. 🧱 アーキテクチャと設計判断

- **`ecosystem_plan.py` はGitHub検出を決して再実装しません。** マニフェスト
  検証/リトライ/バックオフのロジックを二重に持つのではなく、実際の
  Pythonパッケージとして `hydra-umc-updater`
  （`hydra_umc_updater.github_client.discover_remote_projects()`）に
  依存しています - そちら側で行われた修正や改善は自動的にこのツールにも
  反映されます。
- **`image_builder.py` はプロジェクト自身のビルドを決して再実装しません。**
  各エコシステムプロジェクトは、実際に固定されたバージョンでクローン
  され、対象rootfsのchroot内で**そのプロジェクト自身の** `build.sh` を
  実行することでビルドされます - これは `hydra-umc-updater` 自身の
  `install.py` がすでに文書化している「各プロジェクト自身のビルド
  スクリプトに委任する」という原則と同じです。
- **Linux/rootのプラットフォーム境界は常に最初に確認されます。**
  `check_build_platform()` は `build_image()` が最初に行うことです -
  サポートされていないホスト（Windows、root権限のないLinuxユーザー、
  `losetup`/`chroot` の欠落）で静かに何もせず終わるビルドは、明確な理由
  とともに開始を拒否するビルドよりも悪いものです。
- **`firstboot_config.py` は副作用のない純粋なジェネレータです。** 生成
  するのはプレーンテキストのファイル内容だけです（`firstrun.sh` 文字列、
  `cmdline.txt` パッチ文字列） - 実際のイメージやファイルシステム自体には
  一切触れないため、rootや実際のイメージなしでも簡単にテストできます。
  その内容を実際のbootパーティションに実際に書き込む責任を持つのは
  `image_builder.py` だけです。
- **標準ライブラリの `crypt` モジュールではなく、実際のSHA-512-crypt
  パスワードハッシュを使用。** `crypt` は*ホスト自身*のlibc呼び出しを
  ラップするだけなので（Unix専用で、Python 3.13で完全に削除されました）、
  `passlib` はこのツールが動作するあらゆるプラットフォーム（Windowsを
  含む）で `chpasswd -e` が期待するのとバイト単位で同一の実際の
  `$6$...` 形式を生成します。

## 📂 ディレクトリ構成

```
HYDRA-UMC-OS-REBUILDER/
├── src/hydra_umc_os_rebuilder/
│   ├── ecosystem_plan.py    # hydra_umc_updater自身の検出機能の上に構築された、実際のCM5プロジェクト/バージョン計画
│   ├── firstboot_config.py  # 純粋なfirstrun.sh/cmdline.txtジェネレータ - ファイルシステムへのアクセスなし
│   ├── image_builder.py     # 実際のダウンロード/ループマウント/chrootインストールのパイプライン、Linux/rootに限定
│   ├── i18n.py               # 実際の完全なGUI翻訳（7言語）
│   ├── qt_gui.py             # 上記の実際のモジュール（CLIと同じもの）の上に構築されたQt Quickブリッジ
│   ├── qml/Main.qml          # テーマ化されたデスクトップシェル：エコシステム状態 / イメージ作成 / 初回起動設定
│   └── main.py                # ディスパッチ：デフォルトはGUI、--cliでstatus/config/build-image
├── tests/                    # 実際のテスト：firstboot_config、ecosystem_plan、i18n
├── docs/
│   ├── CLI_REFERENCE.md       # コマンドリファレンス
│   └── FIRST_BOOT_CONFIG.md   # このツールが再現する実際のfirstrun.shの仕組みと、その理由
├── images/                    # メディア、アプリアイコン、バナー
├── tools/
│   ├── build_test.py          # バージョン管理を行わないビルド/コンパイルチェック
│   └── ci_validate.py         # CIで使用されるマニフェスト/CHANGELOG/ドキュメントの検証
├── build.sh / build.bat       # venv + 編集可能インストール + コンパイルチェック
├── run.sh / run.bat           # デフォルトのGUI / CLIエントリーポイント
├── run-gui.vbs                # コンソールウィンドウなしのWindowsグラフィカルランチャー
├── bump_version.py            # エコシステム全体のオドメーター式バージョン更新（pyproject.toml + __init__.py）
└── bump_manifest_version.py   # hydra-umc.project.jsonのバージョンをネイティブのものと同期（--sync）
```

## ⚙️ ビルドと実行ガイド

```bash
chmod +x build.sh   # 初回のみ
./build.sh          # .venvを作成、pip install -e ".[dev,gui]"、コンパイルチェック、pytestを実行
./run.sh                                # ウィンドウ型GUI（デフォルト）
./run.sh --cli status                   # エコシステムの各プロジェクトの最新の実際のGitHubバージョン
./run.sh --cli config --out ./boot ...  # 初回起動設定を書き込む（各オプションはdocs/CLI_REFERENCE.mdを参照）
./run.sh --cli build-image --out FILE   # 書き込み可能な.imgを構築（Linux/rootのみ）
```

Windowsの場合：`build.bat` を実行後、`run.bat`（GUI）/
`run.bat --cli status` / `run.bat --cli config ...`。`build-image` は
いずれの場合もroot権限を持つ実際のLinuxホストが必要です - 詳細は
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) を参照してください。

**トラブルシューティング**

- `--cli build-image` が `BUILD_BLOCKED reason=...` で終了する: その理由
  を読んでください - 汎用的な失敗ではなく、不足している具体的な要素
  （Linuxでない、rootでない、`PATH` に特定のツールが見つからない）を
  正確に示します。
- `--cli config` が検証エラーを発生させる: 指定したホスト名/ユーザー名/
  Wi-Fi国コードが、それらのフィールドが要求する実際の厳密な形式に一致
  していません - `firstboot_config.py` 自身の検証を参照してください。
- GUIの「エコシステム状態」タブが空のまま: ネットワークを確認してくだ
  さい - このツールは `status`/検出のために
  `github.com`/`raw.githubusercontent.com` への実際の接続が必要です、
  `hydra-umc-updater` 自身と同様です。

## 🚀 ロードマップ

- 現在の `firstrun.sh` パスと並行して、Pi以外のベースイメージ向けの
  代替の初回起動メカニズムとしてcloud-initをサポート。
- ゼロからのビルドを超える実際の必要性が生じた場合の、増分的なイメージ
  更新（完全な再構築ではなく既存の `.img` にパッチを当てる）。
- スクリプトから利用するための、`status` の `--json` 出力モード。
- HYDRA-UMC-SUITE自身の `build_exe.bat`/`.sh` と同じ慣習に従った、
  `pip`/venvの手順を一切必要としないダブルクリックインストール用の
  スタンドアロンGUI実行ファイル（PyInstaller）。

## 🔗 関連プロジェクト

このプロジェクトは、同じ作者（JuanenRac / Electro Hobby 3D）によるHYDRA-UMCロボティクスエコシステムの一部です。リクエストが実際にはこのリポジトリではなく、これらのいずれかに関するものである可能性があるため、知っておく価値があります。

**直接関連**
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — このツールが実際にイメージを構築する対象である、再現可能なRaspberry Pi OS製品レイヤー：読み取り専用エージェント、検証済みの設定/プロファイル、Wi-Fi初回接続プロビジョニング。
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — このツールがGitHub検出のために実際のライブラリとして依存している姉妹的なエコシステム運用ツール - すでに稼働中のマシン上でエコシステム全体を検出・インストール・手動更新するのに対し、このツールはゼロから新しいものを構築します。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 保守インシデントコーディネーター: 低権限のエッジ役割がサニタイズされたインベントリ/ヘルスのスナップショットを収集し、コントロールプレーン役割がそれを読み取り専用でレンダリングして AI プロバイダーに診断の提案を依頼します - パッチを適用することも、何かをデプロイすることも決してありません。

**エコシステムの他の一部**

*コアハードウェアとプラットフォーム*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — 各ブリッジが自身のコマンドを検証する際の基準となる、共有のJSON-Schema契約とセーフティゲートの境界。
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — 外部マシン用コネクタのための宣言的アダプターマニフェストのレジストリとバリデーター。SDK 自身の契約という発想を外部マシンにまで拡張し、産業用ゲートウェイ系のプロジェクトを置き換えることはありません。

*コアバックエンドとクライアント*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — ロボットアームの物理マザーボード：CM5ホスト + デュアルコアSTM32H745、CAN-OTA/SPI-OTA経由で最大8本のツールアームを協調制御。
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — すべての制御クライアントが実際に通信する実際のヘッドレスバックエンド（REST/WebSocket）。
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — リアルタイムのマルチロボット3D可視化を備えたWeb制御ダッシュボード。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 複数のサーバーを同時に扱うデスクトップ（PySide6）スウォーム指令センター。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 生体認証ログインとペアリングされたWear OSコンパニオンを備えたネイティブAndroid制御アプリ。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — リアルタイムWebSocket同期を備えたiOS/iPadOS制御アプリ（Flutter）。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — CM5自体に搭載された7インチDSIタッチスクリーン向けのネイティブタッチUI。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 完成したモデルをSTUDIO自身のカタログに送り込む、デスクトップ用グラフィカルURDF作成/編集ツール。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 実際のVDA 5050 MQTTパブリッシャーによるAGV/AMRフリート向けの協調境界。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 実際のGRBLステータス/制御バイトアクセスを備えた高レベルCNCセルコーディネーター。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 実際のBoston Dynamics Spotコマンド送信機を備えた、脚式/ヒューマノイドドロイド向けの協調境界。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 3つの実際のキー/筐体/インターロックGPIO保護装置を読み取るレーザーセル安全コーディネーター。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — OpenPnPピック＆プレース向けの安全な高レベルボードフローコーディネーター。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 実際に制御されたジョブコマンドを備えた、Moonraker/Klipper 3Dプリンター向けの安全な協調境界。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 実際に遅延インポートされるrclpy ROS 2トランスポートを備えた安全コーディネーター。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 実際のMAVLinkコマンド送信機を備えた、カメラ搭載UAV向けの協調境界。

*URTCツールプラットフォーム*
- **[URTC](https://github.com/JuanenRac/URTC)** — 物理的なUniversal Robot Tool ControllerボードのCAN バス経由25以上のツールプロファイル対応ファームウェア。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — URTCボードをフラッシュするデスクトップGUIツール、CAN-OTAに加え完全チップSWD/JTAGにも対応。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — URTCボード向けのデスクトップライブCANバス診断ツール、ツールプロファイルごとに1パネル。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — Web Serial API経由のブラウザベースのURTC-TESTER代替、ローカルインストール不要。

*ビジョンAIノード（Hailo-8）*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Hailo-8ビジョンパイプラインの統合ハブ、実際の段階ごとのハードウェア準備状態チェックを備える。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — Hailoアーキテクチャ/チェックサムの安全な読み込み検証を備えた実際のコンパイル済みモデルレジストリ。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 実際のHailoRT統合境界を備えた実際のGStreamerパイプライン + MediaMTX設定ジェネレータ。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 上流のゾーン状態によって安全ゲートされる、実際の位置ベースビジュアルサーボイング補正則。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — 校正の最新性を強制する、実際のゾーン侵入チェックと緊急停止要求。

*コグニティブAIノード（Hailo-10）*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Hailo-10コグニティブパイプライン（LLM/VLA/音声オーケストレーション）の統合ハブ。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — Vision-Language-Actionモデル向けの実際のアクショントークンのエンコード/デコードと軌道生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 制限された確認必須のWatchリレーを備えた実際の音声フロントエンド（VAD + インテントパーサー）。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — MCUエラーコードに対する実際のルールベースのタスク分解とセマンティックエラー復旧。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — このエコシステム自身のMarkdownドキュメントに対する、実際の標準ライブラリのみによるTF-IDF文書検索。

*オーケストレーションとスウォーム*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 実際のgRPC/Protobufヘルスレポート契約とミッションステートマシンを備えた統合ハブ。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 実際のHTTP API上での、重複排除機能を備えた実際の優先度ベースジョブキュー。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — リトライ/バックオフと識別不一致検出を備えた、実際のgRPCベースのフリートヘルスウォッチドッグ。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 実際の障害物/作業空間衝突検証を備えた実際のRRTベース3Dパスプランナー。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — マルチセル収束についてプロパティテスト済みの実際のCRDT LWW-Element-Map状態同期。

*デジタルツインとシミュレーション*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 実際のバージョン互換性同期契約を備えたデジタルツインエンジンの統合ハブ。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — シミュレーションと実際のハードウェアの間でコマンドをルーティングする実際のハードウェアインザループ安全インターロック。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — 実際のURDFサブセットに対する実際の順運動学と関節限界検証。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — YOLO/COCOアノテーションエクスポートを備えた実際の手続き型2Dシーンジェネレータ。

*データと分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — 実際の取り込み/クエリHTTP APIを備えた、sqlite3による実際の時系列ストア。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — ドリフト監視を備えた実際のFFT + 統計的ベースライン異常検出器。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — DATALAKEの履歴に基づく、再現可能なCSVエクスポートを備えた実際のOEE/稼働率計算。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — シーケンス重複排除を備えた、DATALAKEへの実際のCAN/WebSocket取り込みパイプライン。

*産業用ゲートウェイ*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 実際のコマンド許可リスト/バックプレッシャー層を備えた、産業プロトコルへ中継する統合ハブ。
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — 実際のバイナリプロトコルクライアントセッションで検証済みの実際のOPC-UAアドレス空間。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — クライアントごとの認証とトピックACLをオプションで備えた実際のMQTTブローカー。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — 劣化モード出力を備えた実際のMTConnect `/probe` および `/current` XMLエンドポイント。

*補完ツールとエコシステム運用*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — DATALAKE/ANOMALY-DETECTOR上に構築された、誠実な統計的フォールバックを備えたスマートサマリーと異常ハイライトパネル。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 実際の安定した終了コード契約を備えたフリートCLI、HYDRA-UMC-SERVER自身のAPIの本物のライブクライアント。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 実際の触覚アラートとペアリングされたスマートフォンへの音声リレーを備えたWearOSコンパニオンアプリ。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 実際のツールID解読とSmart Idle予熱ロジックを備えた、ボード取り付けラック用ファームウェア。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — サーマル/RGB検査ツールヘッド向けの実際のPythonビジョンコンパニオンを備えたファームウェア。

---

## 📚 ドキュメントとコミュニティ

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — 実際のサンプル出力付きの、すべての `--cli` サブコマンド。
- **[docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md)** — このツールが再現する実際の `firstrun.sh` の仕組みと、その理由。
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — プルリクエストのための技術スタックとコーディングガイドライン。
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — このコミュニティで期待される行動基準。
- **[SECURITY.md](SECURITY.md)** — 脆弱性の報告方法と、このプロジェクトの実際のセキュリティ重点分野。
- **[SUPPORT.md](SUPPORT.md)** — 質問や不具合報告をどこで行うか。

## 👤 作者
**JuanenRac**（Electro Hobby 3D）
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 ライセンス

GPL-3.0（ソフトウェア）/ CC BY-SA 4.0（ドキュメント） - 詳細は [LICENSE.md](LICENSE.md) を参照してください。
