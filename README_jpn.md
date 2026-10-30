<!-- =============================================================================
HYDRA-UMC-OS-REBUILDER - Builds a ready-to-flash CM5 image
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-OS-REBUILDER banner" width="100%">
</p>

# 📀 HYDRA-UMC-OS-REBUILDER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | 🇯🇵 <b>日本語</b> | <a href="README_por.md">🇵🇹 Português</a></p>

### 📀 書き込み可能な、完全に最新のCM5イメージを構築する

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="Desktop">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Tests-183%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.3.3-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

> **安全性とセキュリティの現状:** このエコシステムは認証された安全システムではありません。ハードウェアの E-STOP 経路、ファームウェアが強制する制限やインターロック、検証済みの動作コマンドはまだありません。ファームウェアイメージは CRC-32 と Ed25519 署名で検査し、リリースビルドは公開済みの開発用鍵を拒否します(リレーの先のツールヘッドと拡張ボードは引き続き URTC のブートローダーを使い、署名ではなく共有鍵の HMAC-SHA256 を使います)。TLS と相互 TLS は任意で、既定では無効です。独自基板はまだ実装も試験もされていません。ここに書かれた内容を人の安全のために頼る前に、[セキュリティベースライン](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)と[脅威モデル](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)をお読みください。

---

## 📋 ひと目で

| | |
|---|---|
| バージョン | `0.3.3` |
| 成熟度 | 機能する |
| テスト | 183 (`python -m pytest -q tests`) |
| 技術 | Python 3.10+ / PySide6 / QML / Raspberry Pi OS / GitHub raw content |
| 対象 | 利用者の PC |
| 実機での確認 | まだです：このバージョンについて実機での動作記録はありません |

**移動：** [概要](#-概要) · [アーキテクチャ](#-アーキテクチャ) · [セキュリティと安全](#-セキュリティと安全) · [クイックスタート](#-クイックスタート) · [テスト](#-テスト) · [リポジトリの構成](#-リポジトリの構成) · [関連プロジェクト](#-関連プロジェクト)

## 🚦 プロジェクトの状況

各行はこのリポジトリの一部分で、信号は今日どこまで進んでいるかを示します。計画ではなく、リポジトリが示せるもの（テスト、ビルド、実行）に基づいて書かれています。

🟢 完了・検証済み · 🟡 動作する（既知の制限あり） · 🟠 一部のみ、または未検証 · 🔴 未実装または動作しない

| 領域 | 状態 | ここでの意味 |
|---|---|---|
| ソフトウェア | 🟡 | 主な目的では動作します。足りない点は上の正直さの確認に書かれています |
| テスト | 🟢 | 自動テスト 183 件。変更のたびに実行されます |
| 実機 | 🔴 | まだです：このバージョンについて実機での動作記録はありません |
| ドキュメント | 🟢 | 8 言語の README。変更のたびにマニフェストと照合されます |

## 🎯 概要

HYDRA-UMC-OS-REBUILDERは、実際のCM5導入が最終的に必ず必要とする質問に
答えるWindows/Linuxデスクトップツールです - デフォルトはウィンドウ型
GUI、`--cli` で完全なCLIも利用可能: **「エコシステムの各プロジェクトの
最新の実バージョンをすでにインストール済みの、新しいSDカード/eMMC
イメージを構築し、書き込む前にWi-Fi/ユーザー/ホスト名/SSHを設定させて
ほしい」**。

**イメージの内容:** 計画されたバージョンのプロジェクトのコピーが `/opt/hydra-umc/<名前>` に置かれ、各プロジェクト自身のビルドが生成したものが含まれます。サービス用ユーザーや systemd ユニットは作成せず、`/etc/hydra-umc` も用意しないため、初回起動でサービスが自動的に起動することはありません。HYDRA-UMC-OS のプロビジョニングスクリプトは引き続きボード上で実行する必要があります。

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
   Customisation」画面がRaspberry Pi OS（Trixie以降）イメージ上で
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

## 🧩 HYDRA-UMC での役割

**HYDRA-UMC-OS-REBUILDER** は、エコシステムの各プロジェクトの最新版を最初から収めた新しい CM5 イメージを作り、イメージを書き込む前に初回起動の設定（Wi-Fi、ユーザー、ホスト名、SSH）を書き出します。そのイメージが載せるプラットフォーム層は `HYDRA-UMC-OS` が説明しています。

## 🏛️ アーキテクチャ

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-OS-REBUILDER architecture" width="100%">
</p>

### アーキテクチャと設計判断

- **SSH ホストキーは初回に固定し、Wi-Fi の国コードに既定値はありません。** リモートビルドは、キーを固定していないマシンを拒否し、そのキーの SHA-256 フィンガープリントを表示します。マシン上で確認したそのフィンガープリントを入力するとキーが固定され、以後はそのキーだけが受け入れられ、異なるキーは変更されたキーとして拒否されます。イメージの Wi-Fi 国コードには既定値がなくなりました（Wi-Fi ネットワークを指定する場合は `--wifi-country` / 国フィールドが必須）。マシンが置かれる国の電波規則を決めるためです。
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
- **オペレーターを締め出してしまうファーストブート設定は、構築されずに拒否されます。** アカウントを設定せずに SSH を無効にすると、このツール自身の公式ベースイメージ（Trixie 以降はデフォルトユーザーなし）にログイン手段が全くなくなります。`acknowledge_no_remote_access=True` で明示的に了承しない限り拒否されます。`describe_recovery_procedure()` は、設定が開けたままにするものについての実際の復旧手順を示します。
- **パスワードは引数として渡されなくなりました。** `--password` と `--wifi-password` は引き続き使えますが、コマンドラインはマシンの全ユーザーに見え、`sudo` は認証ログに書き込みます。そのため CLI は `HYDRA_UMC_FIRSTBOOT_PASSWORD` / `HYDRA_UMC_FIRSTBOOT_WIFI_PASSWORD`、または `--secrets-stdin` を指定したときは標準入力の JSON オブジェクト(`{"password": "...", "wifiPassword": "..."}`)からも読み取ります。GUI のリモート(SSH)ビルドはこの方法で送信し、実行するコマンドには含めません。
- **chroot が完全になり、リモートビルドは固定されます。** ビルドはイメージに `/proc`、`/sys`、`/dev`、`/dev/pts` をマウントし、プロジェクトのビルド中はホストの名前解決を与えます(終了後にイメージ自身の `resolv.conf` を戻します)。これにより `pip`、`npm`、`go` が chroot からネットワークに届きます。SSH 経由のリモートビルドは、実行中のバージョンのリリースタグからこのツールをインストールし(`HYDRA_UMC_REBUILDER_REMOTE_REF` で別のタグやコミットを指定可能)、リモートでエコシステムを再探索せず、確認済みプランの固定プロファイル(`profile-build`)からビルドします。これらはまだ root 権限の実 Linux ホストで実行されていません。
- **凍結されたプロファイルは、永続化された本物のレシピであり、再取得されません。** `profile_manifest.py` の `freeze_profile()`/`profile-build` は、各プロジェクトをテストした正確なコミット SHA に固定します。後のビルドが、GitHub が現在「latest」と呼ぶものに黙って置き換えることはありません。`diff_profile()` は、凍結されたプロファイルを現在のエコシステムとプロジェクトごとに（単一の真偽値ではなく）比較します。
- **標準ライブラリの `crypt` モジュールではなく、実際のSHA-512-crypt
  パスワードハッシュを使用。** `crypt` は*ホスト自身*のlibc呼び出しを
  ラップするだけなので（Unix専用で、Python 3.13で完全に削除されました）、
  `passlib` はこのツールが動作するあらゆるプラットフォーム（Windowsを
  含む）で `chpasswd -e` が期待するのとバイト単位で同一の実際の
  `$6$...` 形式を生成します。ハッシュは glibc の既定値である 2000 年当時の 5000 ラウンドではなく 500000 ラウンドを使うため、イメージのコピーや `/etc/shadow` を攻撃するコストがはるかに高くなります。デバイス自身が好む yescrypt（`$y$`）は、Windows 上の Python からは移植可能な形で生成できません。

## 🔒 セキュリティと安全

`--public-image`（`build-image` と `profile-build`、およびビルドウィンドウの **公開イメージ** チェックボックス。既定ではオフ）は、初回起動の設定をすべて拒否し、さらにブートパーティション（`firstrun.sh`、`wpa_supplicant.conf`、`userconf*`、`custom.toml`、`user-data`、`network-config`）と `/opt/hydra-umc`（`.env` ファイルとファイルを含むデータフォルダー）に認証情報がないか調べます。何か見つかるとイメージは昇格されません。Linux が必要なため、実際のイメージではまだ試していません。

## 🚀 クイックスタート

Python 3.10 以上が必要です。

```bash
./build.sh             # Linux, macOS (build.bat on Windows)
./run.sh               # windowed GUI
./run.sh --cli status  # latest real version of every project
```

## 🧪 テスト

`python -m pytest -q tests` で自動テスト 183 件を実行します。 ハードウェアも、このマシンの外にあるものも必要ありません。

CI は `HYDRA_UMC_CI=1 python tools/ci_validate.py` を実行し、マニフェスト、文書、8 つの README、図を検査します。

## 🏗️ ビルドとリリース

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
- `--cli config`/`build-image` が「no login path at all」で拒否する場合：アカウントを設定せずに SSH が無効にされています。アカウントを設定するか、他の接続手段が確実なら `acknowledge_no_remote_access=True`（GUI/API）を渡してください。`describe_recovery_procedure()` を参照してください。
- `profile-build` が「no real, resolved commit SHA」でプロジェクトを拒否する場合：凍結されたマニフェストが、リポジトリの名前変更や非公開化より前のものです。現在のエコシステムに対してプロファイルを再凍結（`profile-freeze`）してください。
- `profile-build` が「missing N required resource(s)」で拒否する場合：`profile-set-required-resources` で整えたプロジェクトが自身の `build.sh` を実行しましたが、宣言された相対パスがその後もディスク上に存在しません。本物の不完全なビルドであり、他の場所に残ったファイルで救済されることはなく、イメージは昇格されません。
- GUIの「エコシステム状態」タブが空のまま: ネットワークを確認してくだ
  さい - このツールは `status`/検出のために
  `github.com`/`raw.githubusercontent.com` への実際の接続が必要です、
  `hydra-umc-updater` 自身と同様です。
- **更新を繰り返すとプロジェクト数が減り続ける（例：42 -> 9 -> 0）、アプリを再起動しても同じ** - これまで報告されていなかった本物のバグです。各プロジェクトの実際のコミット SHA の解決は、プロジェクトごとに `api.github.com` を 1 回呼び出し、このツール（と `hydra-umc-updater`）の他の処理と共有する *未認証* の 1 時間あたり 60 リクエストの予算を消費します。50 を超える実際のエコシステムのプロジェクトがあると、1 回の更新で使い切ることがあり、リセットされるのはこのアプリの状態ではなく GitHub 側の 1 時間の枠で、再起動では解決しません。黙ってプロジェクトを減らして表示する代わりに正直に報告するよう修正しました：プロジェクト一覧の下の琥珀色のバナーが、上限までに解決できたプロジェクト数と GitHub の上限がリセットされる時刻を正確に示します（`ecosystem_plan.GitHubRateLimitedError` を参照）。このツールを起動する前に環境変数 `GITHUB_TOKEN`（公開リポジトリには権限不要の通常の GitHub 個人アクセストークン）を設定すると、予算が 1 時間あたり 5000 に増えます。リポジトリ一覧とプロジェクトごとのコミット SHA 解決の両方が一貫してこれを使用します。

## 📂 リポジトリの構成

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-OS-REBUILDER" width="100%">
</p>

<details>
<summary>ツリーのテキスト版</summary>

```text
HYDRA-UMC-OS-REBUILDER/
├── src/hydra_umc_os_rebuilder/   ソースコード
│   ├── __init__.py               パッケージバージョン
│   ├── ecosystem_plan.py         hydra_umc_updater自身の検出機能の上に構築された、実際のCM5プロジェクト/バージョン計画
│   ├── firstboot_config.py       純粋なfirstrun.sh/cmdline.txtジェネレータ - ファイルシステムへのアクセスなし、復旧手順の保護付き
│   ├── profile_manifest.py       凍結されたプロファイルバージョンマニフェスト：凍結/比較/選択的更新、試用中に「最新版」へ黙って差し替わることはない
│   ├── image_builder.py          実際のダウンロード/ループマウント/chrootインストールのパイプライン、Linux/rootに限定
│   ├── i18n.py                   実際の完全なGUI翻訳（8言語）
│   ├── qt_gui.py                 CLI モジュール上の Qt Quick ブリッジ
│   ├── qml/Main.qml              テーマ化されたデスクトップシェル：エコシステム状態 / イメージ作成 / 初回起動設定
│   ├── main.py                   ディスパッチ：デフォルトはGUI、--cliでstatus/config/build-image
│   ├── remote_install.py         リモートビルドがインストール・ビルドする元 (固定リビジョン。main の先頭ではない)
│   └── ssh_hostkeys.py           リモートビルド機の SSH ホスト鍵を初回に信頼 (フィンガープリントを固定)
├── tests/                        実際のテスト：firstboot_config、ecosystem_plan、profile_manifest、image_builder、i18n、main
├── docs/                         プロジェクトの文書
├── images/                       メディア、アプリアイコン、バナー
├── tools/                        プロジェクトのツールと CI の検査
├── .github/                      CI ワークフローと Issue テンプレート
├── build.sh / build.bat          venv + 編集可能インストール + コンパイルチェック
├── run.sh / run.bat              デフォルトのGUI / CLIエントリーポイント
├── run-gui.vbs                   コンソールウィンドウなしのWindowsグラフィカルランチャー
├── bump_version.py               明示的なバージョン更新
├── bump_manifest_version.py      hydra-umc.project.jsonのバージョンをネイティブのものと同期（--sync）
├── CHANGELOG.md                  各バージョンの変更点
├── build-test.sh                 変更を伴わないビルド確認
├── hydra-umc.project.json        マニフェスト：バージョン、成熟度、ファミリー
├── pyproject.toml                パッケージのメタデータ
└── test.sh                       テストを実行
```

</details>

## 🗺️ ロードマップと既知の制限

**現時点の既知の制限**

- 現在の `firstrun.sh` パスと並行して、Pi以外のベースイメージ向けの
  代替の初回起動メカニズムとしてcloud-initをサポート。
- ゼロからのビルドを超える実際の必要性が生じた場合の、増分的なイメージ
  更新（完全な再構築ではなく既存の `.img` にパッチを当てる）。
- スクリプトから利用するための、`status` の `--json` 出力モード。
- HYDRA-UMC-SUITE自身の `build_exe.bat`/`.sh` と同じ慣習に従った、
  `pip`/venvの手順を一切必要としないダブルクリックインストール用の
  スタンドアロンGUI実行ファイル（PyInstaller）。
- `acknowledge_no_remote_access` 用の GUI チェックボックス - 現在 GUI は `FirstBootConfigError` の実際のメッセージを正直に表示します（クラッシュも無言の無動作もありません）が、了承するための専用コントロールはなく、CLI/API のみが可能です。
- `profile_manifest.py` に対する GUI パネル（CLI だけでなくデスクトップシェルから凍結/比較/更新）。

## 🌍 言語

この README とリポジトリの文書は、英語・スペイン語・ドイツ語・フランス語・イタリア語・日本語・中国語・ポルトガル語（ポルトガル）の 8 言語で提供されています。8 つのファイルは同時に書かれ、同じ節と同じリンクを持つことを CI が確認します。

## 🔗 関連プロジェクト

このプロジェクトは、同じ作者（JuanenRac / Electro Hobby 3D）によるHYDRA-UMCロボティクスエコシステムの一部です。リクエストが実際にはこのリポジトリではなく、これらのいずれかに関するものである可能性があるため、知っておく価値があります。

**直接関連**
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — このツールが実際にイメージを構築する対象である、再現可能なRaspberry Pi OS製品レイヤー：読み取り専用エージェント、検証済みの設定/プロファイル、Wi-Fi初回接続プロビジョニング。
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — このツールがGitHub検出のために実際のライブラリとして依存している姉妹的なエコシステム運用ツール - すでに稼働中のマシン上でエコシステム全体を検出・インストール・手動更新するのに対し、このツールはゼロから新しいものを構築します。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 保守インシデントコーディネーター: 低権限のエッジ役割がサニタイズされたインベントリ/ヘルスのスナップショットを収集し、コントロールプレーン役割がそれを読み取り専用でレンダリングして AI プロバイダーに診断の提案を依頼します - パッチを適用することも、何かをデプロイすることも決してありません。
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — 再現可能な開発ホスト（Raspberry Pi 5 / CM5）。エコシステムのソースコードを保管し、永続キューのもとで境界の明確なビルド/テストタスクを実行する。運用中の CM5 とは明確に異なる、開発専用の役割。

**エコシステムの他の一部**

*コアハードウェアとプラットフォーム*
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — 各ブリッジが自身のコマンドを検証する際の基準となる、共有のJSON-Schema契約とセーフティゲートの境界。
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — 外部マシン用コネクタのための宣言的アダプターマニフェストのレジストリとバリデーター。SDK 自身の契約という発想を外部マシンにまで拡張し、産業用ゲートウェイ系のプロジェクトを置き換えることはありません。

*コアバックエンドとクライアント*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — ロボットアームのマザーボードの設計——CM5 ホスト + デュアルコア STM32H745、CAN-OTA/SPI-OTA 経由で最大 8 本のツールアームを統括することを目指す(ファームウェアは初期段階で、実装済みの基板はまだない)。
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — すべての制御クライアントが実際に通信する実際のヘッドレスバックエンド（REST/WebSocket）。
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — リアルタイムのマルチロボット3D可視化を備えたWeb制御ダッシュボード。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 複数のサーバーを同時に扱うデスクトップ（PySide6）スウォーム指令センター。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 生体認証ログインとペアリングされたWear OSコンパニオンを備えたネイティブAndroid制御アプリ。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — リアルタイムWebSocket同期を備えたiOS/iPadOS制御アプリ（Flutter）。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — CM5自体に搭載された7インチDSIタッチスクリーン向けのネイティブタッチUI。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 完成したモデルをSTUDIO自身のカタログに送り込む、デスクトップ用グラフィカルURDF作成/編集ツール。
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — HYDRA-UMC-EDITOR-URDF も編集する同じモデルカタログ内で、実在するパーツを変換/置換/削除/追加するデスクトップ STL モデルエディタ。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — VDA 5050 MQTT パブリッシャーによる AGV/AMR フリートの調整境界(エミュレートしたフリートに対してのみテスト済み)。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — GRBL ステータス/制御バイトへのアクセスを持つ、CNC セルの高レベルコーディネーター(エミュレーターに対してのみテスト済み)。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Boston Dynamics Spot コマンド送信機能を持つ、脚型/ヒューマノイドドロイドの調整境界(エミュレーターに対してのみテスト済み)。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — キー/筐体/インターロックの GPIO 信号 3 系統を読み取るレーザーセルのコーディネーター(模擬チップに対してのみテスト済み。レーザーの武装や発射はできない)。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — OpenPnPピック＆プレース向けの安全な高レベルボードフローコーディネーター。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 実際に制御されたジョブコマンドを備えた、Moonraker/Klipper 3Dプリンター向けの安全な協調境界。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 遅延インポートの rclpy ROS 2 トランスポートを持つコーディネーター(ROS 2 環境ではまだ実行していない)。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — MAVLink コマンド送信機能を持つ、カメラ搭載 UAV の調整境界(エミュレーターに対してのみテスト済み)。

*URTCツールプラットフォーム*
- **[URTC](https://github.com/JuanenRac/URTC)** — 物理的なUniversal Robot Tool ControllerボードのCAN バス経由25以上のツールプロファイル対応ファームウェア。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — URTCボードをフラッシュするデスクトップGUIツール、CAN-OTAに加え完全チップSWD/JTAGにも対応。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — URTCボード向けのデスクトップライブCANバス診断ツール、ツールプロファイルごとに1パネル。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — Web Serial API経由のブラウザベースのURTC-TESTER代替、ローカルインストール不要。
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — URTC の CAN バスの前に置くゲートウェイ：許可する識別子のリスト、レート制限、セッション鍵。コンピューター上でテスト済みで、実際のバスではまだ試していません。

*ビジョンAIノード（Hailo-8）*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Hailo-8ビジョンパイプラインの統合ハブ、実際の段階ごとのハードウェア準備状態チェックを備える。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — Hailoアーキテクチャ/チェックサムの安全な読み込み検証を備えた実際のコンパイル済みモデルレジストリ。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 実際のHailoRT統合境界を備えた実際のGStreamerパイプライン + MediaMTX設定ジェネレータ。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ゾーン状態を条件に承認する Position-Based Visual Servoing 補正則。カメラによる姿勢推定はまだない。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — 校正の最新性を強制する、実際のゾーン侵入チェックと緊急停止要求。

*コグニティブAIノード（Hailo-10）*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Hailo-10コグニティブパイプライン（LLM/VLA/音声オーケストレーション）の統合ハブ。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — Vision-Language-Actionモデル向けの実際のアクショントークンのエンコード/デコードと軌道生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 制限された確認必須のWatchリレーを備えた実際の音声フロントエンド（VAD + インテントパーサー）。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — MCUエラーコードに対する実際のルールベースのタスク分解とセマンティックエラー復旧。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — このエコシステム自身のMarkdownドキュメントに対する、実際の標準ライブラリのみによるTF-IDF文書検索。
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — エコシステム自身のための、ローカルでポリシーゲート付きのAIメンテナンス技術者 — 観察、診断し、修正を提案する;最上位の2つのリスクレベルは意図的にまだ実装されていない。

*オーケストレーションとスウォーム*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 実際のgRPC/Protobufヘルスレポート契約とミッションステートマシンを備えた統合ハブ。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 実際のHTTP API上での、重複排除機能を備えた実際の優先度ベースジョブキュー。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — リトライ/バックオフと識別不一致検出を備えた、実際のgRPCベースのフリートヘルスウォッチドッグ。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 実際の障害物/作業空間衝突検証を備えた実際のRRTベース3Dパスプランナー。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — マルチセル収束についてプロパティテスト済みの実際のCRDT LWW-Element-Map状態同期。

*デジタルツインとシミュレーション*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 実際のバージョン互換性同期契約を備えたデジタルツインエンジンの統合ハブ。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — シミュレーションと実機の間にソフトウェアの衝突インターロックを備えたハードウェア・イン・ザ・ループのルーター(実機なしでテスト済み)。
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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 触覚アラートのパターンとペアリング済みスマートフォンへの音声リレーを備えた WearOS コンパニオンアプリ(物理的なウォッチではまだ実行していない)。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 実際のツールID解読とSmart Idle予熱ロジックを備えた、ボード取り付けラック用ファームウェア。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — サーマル/RGB検査ツールヘッド向けの実際のPythonビジョンコンパニオンを備えたファームウェア。

## 📚 ドキュメント

さらに読むには：

* **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — 実際のサンプル出力付きの、すべての `--cli` サブコマンド。
* **[docs/FIRST_BOOT_CONFIG.md](docs/FIRST_BOOT_CONFIG.md)** — このツールが再現する実際の `firstrun.sh` の仕組みと、その理由。
* [エコシステムのセキュリティ基準](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [エコシステムの脅威モデル](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [このリポジトリの変更履歴](CHANGELOG.md)
* [このリポジトリのライセンス](LICENSE.md)

## 🤝 コントリビュートとコミュニティ

* プルリクエストの前に `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py`（または `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`）を実行してください。`CI_VALIDATION=PASS` と表示される必要があります。この確認に `build.sh` や `build.bat` は使わないでください。ビルドは検査ではありません。
* 8 つの README は HYDRA-UMC-DOCS の 1 つのソースから書かれます。手で編集しないでください。ソースを変更し、`tools/make_readmes.py` で書き直します。
* 実行していないことを README に書かないでください。事実であれば「シミュレーションのみ」「実機では未確認」と書きます。
* [CONTRIBUTING.md](CONTRIBUTING.md)、[行動規範](CODE_OF_CONDUCT.md)、[SECURITY.md](SECURITY.md)、[SUPPORT.md](SUPPORT.md) を参照してください。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 ライセンス

GPL-3.0-or-later - [LICENSE](LICENSE).
