# Obsidian Transcriber Project Documentation

## Project Overview

Groq Whisper APIを使用した音声文字起こしシステム。大容量ファイルの自動分割、Obsidian統合、Geminiによる自動要約生成機能を提供。

## Architecture

### Directory Structure

```
obsidian-transcriber/
├── src/
│   ├── api/          # API関連
│   │   ├── client.py      # Gemini APIクライアント（要約用）
│   │   ├── groq_client.py # Groq Whisper APIクライアント（文字起こし用）
│   │   └── retry.py       # リトライロジック
│   ├── audio/        # 音声処理
│   │   ├── utils.py       # 音声ユーティリティ
│   │   └── chunking.py    # 大容量ファイル分割
│   ├── hooks/        # フック機能
│   │   ├── config.py      # フック設定管理
│   │   └── runner.py      # フック実行
│   ├── transcription/# 文字起こしサービス
│   │   └── service.py     # 統合サービス
│   ├── obsidian/     # Obsidian統合
│   │   ├── watcher.py     # ファイル監視
│   │   ├── handler.py     # 処理ハンドラ
│   │   ├── note.py        # ノート生成
│   │   └── database.py    # 処理済みファイルDB
│   ├── utils/        # 共通ユーティリティ
│   │   ├── logging.py     # ロギング設定
│   │   └── system.py      # システムユーティリティ
│   ├── config.py     # 設定管理
│   └── constants.py  # 定数定義
├── tests/           # ユニットテスト
├── hooks.yaml.example # フック設定テンプレート
├── main.py         # メインエントリポイント（Obsidian監視）
└── transcribe_cli.py # CLIツール（単体ファイル処理）
```

## Core Components

### 1. Groq Client (`src/api/groq_client.py`)

**Class: `GroqClient`**
- Groq Whisper APIのラッパー
- モデル: `whisper-large-v3-turbo`
- リトライロジックと統合

**Key Methods:**
- `transcribe_audio()`: 音声ファイルの文字起こし
- `transcribe_audio_segment()`: セグメント情報付き文字起こし

### 2. Gemini Client (`src/api/client.py`)

**Class: `GeminiClient`**
- Gemini APIのラッパー（要約専用）
- モデル: `gemini-flash-latest`

**Key Methods:**
- `summarize_text()`: テキストの要約生成
- `generate_content()`: コンテンツ生成

### 3. Audio Processing (`src/audio/`)

**Audio Chunker (`chunking.py`)**
- 25MB超のファイルを自動分割
- 設定可能なオーバーラップ（デフォルト: 10秒）
- 時間ベースの分割処理

**Audio Utils (`utils.py`)**
- 音声ファイル判定
- 長さ・サイズ取得
- フォーマット処理

### 4. Text Processing (`src/utils/text.py`)

**Functions:**
- `find_overlap()`: セグメント境界での重複テキスト検出
- `merge_segments_with_dedup()`: 2セグメントの重複削除マージ
- `merge_all_segments()`: 複数セグメントの一括マージ

**重複削除ロジック:**
- セグメントAの末尾とセグメントBの先頭で最長共通部分文字列を検索
- 見つかった場合: 重複部分を削除して結合
- 見つからない場合（漢字/ひらがなの違いなど）: 両方を保持

### 5. Transcription Service (`src/transcription/service.py`)

**Class: `TranscriptionService`**
- 音声処理の統合サービス
- 自動チャンキング（25MB閾値）
- セグメント境界での自動重複削除
- Groq文字起こし + Gemini要約

### 6. Hooks (`src/hooks/`)

**Class: `HooksConfig`** (`config.py`)
- YAML設定ファイルからフック設定を読み込み
- フックの有効/無効管理

**Class: `HooksRunner`** (`runner.py`)
- フックコマンドの実行
- プレースホルダー置換（`{file_path}`, `{audio_path}`, etc.）
- タイムアウト、非同期実行、エラー処理

**Hook Types:**
| フック名 | タイミング | 引数 |
|---------|----------|------|
| `on_file_detected` | ファイル検知時 | `{file_path}` |
| `on_audio_detected` | 音声ファイル検知時 | `{audio_path}` |
| `on_transcription_complete` | 文字起こし完了時 | `{audio_path}`, `{transcription_path}` |
| `on_summary_complete` | 要約完了時 | `{audio_path}`, `{transcription_path}`, `{summary_path}` |

**Hook Options:**
- `command`: 実行するコマンド（プレースホルダー使用可）
- `enabled`: 有効/無効（デフォルト: true）
- `timeout_seconds`: タイムアウト秒数（デフォルト: 300）
- `error_action`: エラー時の動作 `continue`/`abort`（デフォルト: continue）
- `run_async`: バックグラウンド実行（デフォルト: false）

### 7. Obsidian Integration (`src/obsidian/`)

**Components:**
- `VaultWatcher`: ファイルシステム監視
- `ObsidianTranscriptionHandler`: 処理統合
- `NoteGenerator`: Markdownノート生成
- `ProcessedFilesDatabase`: 処理済みファイルDB（v1.0.0）

**Database Schema (v1.0.0):**
```json
{
  "version": "1.0.0",
  "created_at": "ISO-8601",
  "last_updated": "ISO-8601",
  "statistics": {
    "total_processed": 0,
    "total_failed": 0,
    "total_size_bytes": 0,
    "total_duration_seconds": 0
  },
  "files": {
    "path/to/file": {
      "hash": "md5",
      "status": "completed|failed|pending",
      "processed_at": "ISO-8601",
      "updated_at": "ISO-8601",
      "outputs": {
        "transcription": "path",
        "summary": "path|null"
      },
      "metadata": {
        "duration_seconds": 0,
        "file_size_bytes": 0
      },
      "error": "string|null"
    }
  }
}
```

## Configuration

### Environment Variables

```bash
GROQ_API_KEY=your_groq_key      # Required - Whisper文字起こし用
GEMINI_API_KEY=your_gemini_key  # Required - 要約生成用
```

### Hooks Configuration (`hooks.yaml`)

フック設定ファイルは以下の場所から自動検索される（優先順）:
1. `--hooks-config`オプションで指定したパス
2. カレントディレクトリの`hooks.yaml`または`hooks.yml`
3. 監視フォルダ内の`hooks.yaml`または`hooks.yml`
4. 監視フォルダ内の`.obsidian/hooks.yaml`または`.obsidian/hooks.yml`

```yaml
settings:
  enabled: true  # マスタースイッチ

hooks:
  on_file_detected:
    command: "echo 'File detected: {file_path}'"
    enabled: false
    timeout_seconds: 300
    error_action: continue
    run_async: false

  on_audio_detected:
    command: "ffmpeg -i {audio_path} -y {audio_path}.converted.mp3"
    enabled: false

  on_transcription_complete:
    command: "/path/to/script.sh {audio_path} {transcription_path}"
    enabled: true

  on_summary_complete:
    command: "osascript -e 'display notification \"{audio_path}\" with title \"完了\"'"
    enabled: true
    run_async: true
```

### Constants (`src/constants.py`)

```python
# Gemini (要約用)
SUMMARY_MODEL = 'gemini-flash-latest'

# Groq Whisper (文字起こし用)
GROQ_TRANSCRIPTION_MODEL = 'whisper-large-v3-turbo'
GROQ_TIMEOUT = 300  # 5分

# Audio Chunking
MAX_CHUNK_SIZE_MB = 24  # 25MB制限に余裕を持たせる
DEFAULT_CHUNK_OVERLAP_SECONDS = 10  # チャンク間オーバーラップ

# Audio
AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.wav', ...}

# Retry
MAX_RETRIES = 5
DEFAULT_TIMEOUT = 600  # 10分
RETRY_BACKOFF_BASE = 10
MAX_RETRY_WAIT = 120
```

## Usage Patterns

### Basic Flow

1. **Audio Detection**: ファイル監視またはCLI引数
2. **Processing**:
   - ハッシュチェックで重複判定
   - サイズチェック（25MB超で自動分割）
   - Groq Whisperで文字起こし
   - Geminiで要約生成（オプション）
3. **Output**:
   - `_文字起こし.md`: 完全な文字起こし
   - `_要約.md`: 構造化された要約
4. **Database Update**: 処理済み記録

### Error Handling

- **Retry Logic**: 指数バックオフで最大5回
- **Timeout**: チャンクごとに5分タイムアウト
- **Failed Files**: DBに記録して再処理可能
- **Logging**: 詳細なログ出力

## Dependencies

### Core
- `google-genai>=1.52.0`: Gemini API（要約用）
- `groq>=0.15.0`: Groq Whisper API（文字起こし用）
- `python-dotenv>=1.2.1`: 環境変数
- `watchdog>=6.0.0`: ファイル監視
- `pyyaml>=6.0.0`: フック設定ファイル

### Audio
- `pydub>=0.25.1`: 音声処理
- `soundfile>=0.13.1`: 音声メタデータ

### System Requirements
- Python 3.13+
- FFmpeg（非WAV形式）

## Package Management

### uv (Recommended)
```bash
uv sync          # 依存関係インストール
uv run main.py   # 実行
```

### pip
```bash
pip install -r requirements.txt
python main.py
```

## Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=src

# Specific test
uv run pytest tests/test_database.py
```

## Common Tasks

### Add New Audio Format
1. `src/constants.py`の`AUDIO_EXTENSIONS`に追加
2. FFmpeg対応確認

### Change Models
1. `src/constants.py`の`GROQ_TRANSCRIPTION_MODEL`/`SUMMARY_MODEL`を変更

### Customize Prompts
1. `src/api/groq_client.py`の`transcribe_audio()`内のプロンプト編集
2. `src/api/client.py`の`summarize_text()`内のプロンプト編集

### Change Chunk Overlap
1. `--chunk-overlap`オプションで指定
2. またはデフォルト値を`src/constants.py`の`DEFAULT_CHUNK_OVERLAP_SECONDS`で変更

### Add Processing Status
1. `src/obsidian/database.py`の`ProcessingStatus` Enumに追加

### Configure Hooks
1. `hooks.yaml.example`を`hooks.yaml`にコピー
2. 必要なフックを有効化（`enabled: true`）
3. コマンドをカスタマイズ
4. `--hooks-config`オプションでパスを指定（オプション）

### Add New Hook Type
1. `src/hooks/config.py`の`HookType` Enumに追加
2. `HooksConfig`クラスに対応するフィールドを追加
3. `HooksRunner`にconvenience methodを追加
4. 適切な場所でフックを呼び出し

## Performance Considerations

- **Auto Chunking**: 25MB超で自動分割（オーバーラップ付き）
- **Sequential Processing**: チャンク処理は順次（API制限考慮）
- **Caching**: 処理済みファイルはハッシュで判定
- **Memory**: 大容量音声は分割処理でメモリ効率化

## Security

- APIキーは環境変数で管理
- `.env`ファイルは`.gitignore`に含める
- ログにAPIキーを含めない

## Migration from VAD-based version

旧バージョン（Silero VAD + Gemini）からの移行:

1. 環境変数の追加:
   ```bash
   GROQ_API_KEY=your_groq_key  # 新規追加
   ```

2. 依存関係の更新:
   ```bash
   uv sync  # torch, torchaudio, silero-vadが削除されgroqが追加される
   ```

3. 既存のデータベースは互換性あり
