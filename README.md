# Obsidian Transcriber

[![Python](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![uv](https://img.shields.io/badge/uv-compatible-orange)](https://github.com/astral-sh/uv)

Groq Whisper APIを使用した高速・高精度な音声文字起こしツールです。指定されたフォルダを監視し、新しい音声ファイルを検知したら自動で文字起こし・要約の生成を行います。
このプロジェクトとObsidian Syncを組み合わせることで、音声メモや会議の録音をObsidianにアップロードするだけで、自動的に文字起こしと要約が生成され、効率的な情報管理が可能になります。

## ✨ 特徴
- 🎙️ **多様な音声形式対応**: MP3, WAV, M4A, AAC, FLAC, OGG, OPUS, WEBM, WMA
- 🔄 **自動分割処理**: 25MB超のファイルを自動分割。オーバーラップ付きで境界での文字切れを防止し、重複部分は自動削除。
- 📁 **フォルダ監視**: フォルダを監視して、新しい音声ファイルが検知されたら自動文字起こし・要約を生成。
- 📝 **Obsidian連携**: Obsidian Syncと組み合わせることにより、音声メモや会議の録音を自動的に文字起こし・要約することが可能。
- 🔒 **信頼性**: エラーハンドリングやリトライ機能を搭載。
- ⚡ **高速処理**: Groq Whisperによる216倍速のリアルタイム処理。

## 📋 必要条件

- Python 3.13以上
- Groq API キー（文字起こし用）
- Google Gemini API キー（要約用）
- FFmpeg（非WAV形式の処理に必要）

## 🚀 クイックスタート

### uvを使用（推奨・高速）

```bash
# uvのインストール（まだの場合）
pip install uv

# プロジェクトの初期化と依存関係のインストール
uv sync

# Obsidian監視モード
uv run main.py /path/to/obsidian/vault

# 単体ファイルの文字起こし
uv run transcribe_cli.py audio.mp3 -o output.txt
```

### pipを使用

```bash
# 依存関係のインストール
pip install -r requirements.txt

# Obsidian監視モード
python main.py /path/to/obsidian/vault

# 単体ファイルの文字起こし
python transcribe_cli.py audio.mp3 -o output.txt
```

## ⚙️ セットアップ

### 1. FFmpegのインストール

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
winget install ffmpeg
```

### 2. APIキーの設定

このツールを使用するには、2つのAPIキーが必要です。どちらも無料枠で利用可能です。

#### Groq API キー（文字起こし用）

Groq Whisper APIを使用して音声を文字起こしします。

1. [Groq Console](https://console.groq.com/) にアクセス
2. サインアップ/ログイン
3. 「API Keys」をクリック
4. 「Create API Key」をクリックしてキーを生成
5. 生成されたキーをコピー（一度しか表示されません）

#### Google Gemini API キー（要約用）

Gemini APIを使用して文字起こし結果を要約します。

1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. ログイン
3. 左メニューの「Get API key」をクリック
4. 「Create API key」をクリック
5. プロジェクトを選択（または新規作成）してキーを生成
6. 生成されたキーをコピー


#### `.env`ファイルの作成

プロジェクトのルートディレクトリに`.env`ファイルを作成し、取得したAPIキーを設定します：

```bash
# .envファイルを作成
touch .env
```

以下の内容を`.env`ファイルに記述：

```bash
# Groq API キー（文字起こし用）
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Gemini API キー（要約用）
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> **注意**: `.env`ファイルはGitにコミットしないでください（`.gitignore`に含まれています）

## 📚 使用方法

### フォルダ監視モード

新しい音声ファイルを自動的に検出して処理：

```bash
# 基本的な使用
python main.py /path/to/obsidian/vault

# 既存ファイルもスキャン
python main.py /path/to/obsidian/vault --scan-existing

# 要約を無効化（文字起こしのみ）
python main.py /path/to/obsidian/vault --no-summary

# チャンクオーバーラップを変更（デフォルト: 10秒）
python main.py /path/to/obsidian/vault --chunk-overlap 15

# 詳細ログ表示
python main.py /path/to/obsidian/vault -v

# ログファイル出力
python main.py /path/to/obsidian/vault --log-file app.log
```

### 🔄 自動起動設定（systemdサービス）

PCの起動時に自動で文字起こしサービスを開始できます（Linux限定、systemdを使用）：

#### インストールと有効化

```bash
# サービスのインストール（現在の環境に合わせて自動設定）
./setup_service.sh install

# サービスの開始
./setup_service.sh start

# サービス状態の確認
./setup_service.sh status
```

#### サービス管理コマンド

```bash
./setup_service.sh install   # サービスをインストール・有効化
./setup_service.sh start     # サービスを開始
./setup_service.sh stop      # サービスを停止
./setup_service.sh restart   # サービスを再起動
./setup_service.sh status    # サービス状態を確認
./setup_service.sh logs      # ログを表示（過去50行）
./setup_service.sh follow    # ログをリアルタイム表示
./setup_service.sh update    # サービス設定を更新
./setup_service.sh uninstall # サービスを削除
```

#### 設定の仕組み

- **自動環境検出**: スクリプト実行時の環境（ディレクトリ、Python、ユーザー）を自動検出
- **テンプレート生成**: 環境に合わせてsystemdサービスファイルを動的生成
- **ポータブル**: どのディレクトリでも`./setup_service.sh install`で動作

サービスが有効になると、PC起動時に自動的にObsidian Vault監視が開始されます。

### CLIモード

単体ファイルの文字起こし：

```bash
# 基本的な使用
python transcribe_cli.py audio.mp3 -o output.txt

# チャンクオーバーラップを指定
python transcribe_cli.py audio.mp3 -o output.txt --chunk-overlap 15

# 詳細表示
python transcribe_cli.py audio.mp3 -o output.txt -v
```

### 生成されるファイル

1. **`ファイル名_文字起こし.md`**: 完全な文字起こし内容
   - メタ情報（録音時間、ファイルサイズ等）
   - タイムスタンプ
   - 全文テキスト

2. **`ファイル名_要約.md`**: AI生成の構造化要約
   - 主要トピック（3-5個）
   - 重要ポイント（5-7個）
   - 結論・まとめ
   - キーワード

## 🏗️ プロジェクト構造

```
src/
├── api/          # APIクライアント
│   ├── groq_client.py  # Groq Whisper（文字起こし）
│   ├── client.py       # Gemini（要約）
│   └── retry.py        # リトライロジック
├── audio/        # 音声処理
│   ├── chunking.py     # 大容量ファイル分割
│   └── utils.py        # ユーティリティ
├── transcription/# 文字起こしサービス
├── obsidian/     # Obsidian統合
│   ├── watcher.py    # ファイル監視
│   ├── note.py       # ノート生成
│   ├── handler.py    # 処理ハンドラ
│   └── database.py   # 処理済みファイルDB
├── utils/        # ユーティリティ
│   ├── text.py       # テキスト処理（重複削除）
│   └── logging.py    # ロギング
└── config.py     # 設定管理
```

## 🗄️ データベース

処理済みファイルは自動的に追跡され、重複処理を防ぎます：

- **保存場所**: `.obsidian/.transcription_db.json`
- **統計情報**: 処理数、合計時間、エラー数等
- **オーファン削除**: 削除されたファイルのエントリを自動クリーンアップ

## 🛠️ 開発

### 開発環境のセットアップ

```bash
# uvを使用
uv sync --dev

# または pip
pip install -r requirements-dev.txt
```

### テストの実行

```bash
# 全テスト実行
uv run pytest

# カバレッジレポート付き
uv run pytest --cov=src --cov-report=html
```

### コード品質チェック

```bash
# Ruffによるコードチェック（フォーマット、Linting、インポート整理）
uv run ruff check src tests

# Ruffによる自動修正
uv run ruff check --fix src tests

# Ruffによるフォーマット
uv run ruff format src tests

# 型チェック
uv run mypy src
```

## 📊 技術仕様

- **最大音声長**: 制限なし（25MB以上は自動分割）
- **分割閾値**: 24MB（Groq 25MB制限に余裕を持たせる）
- **チャンクオーバーラップ**: デフォルト10秒（設定可能）
- **重複削除**: セグメント境界で自動的に重複テキストを検出・削除
- **文字起こしモデル**: Groq Whisper Large v3 Turbo（216x リアルタイム速度）
- **要約モデル**: Google Gemini Flash
- **リトライ**: 最大5回（指数バックオフ）
- **タイムアウト**: チャンクごとに5分
- **対応Python**: 3.13+

## 🐛 トラブルシューティング

### FFmpeg関連のエラー
```bash
# インストール確認
ffmpeg -version

# 権限確認（Linux/Mac）
which ffmpeg
```

### メモリ不足エラー
- 大容量ファイルは自動的に分割されますが、極端に大きいファイルではメモリ使用量が増加する可能性があります

### APIエラー
- Groq APIキーの確認: [Groq Console](https://console.groq.com/)
- Gemini APIキーの確認: [Google AI Studio](https://aistudio.google.com/)

### 重複テキストが残る場合
- 漢字/ひらがなの違いなど、文字起こし結果が異なる場合は両方のバージョンが保持されます
- これは意図的な動作で、情報の欠落を防ぐためです

## 📝 ライセンス

MIT License - 詳細は[LICENSE](LICENSE)を参照

## 🤝 コントリビューション

プルリクエスト歓迎です！大きな変更の場合は、まずissueを開いて変更内容を議論してください。

## 🙏 謝辞

- [Groq](https://groq.com/) - 超高速Whisper API
- [Google Gemini](https://ai.google.dev/) - 高品質な要約生成
- [Obsidian](https://obsidian.md/) - 素晴らしいノートアプリ
