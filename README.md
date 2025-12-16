# tasq

**todo.txt互換のFIFOキュー型タスク管理CLIツール**

tasqは人間を「チューブ（FIFOキュー）」として扱うタスク管理ツールです。優先度管理のUXを排除し、ファイルの順序がそのままキューの順序となります。

## 特徴

- 📋 **todo.txt形式完全互換** - 既存のtodo.txtエコシステムと連携可能
- 🔄 **FIFOキュー** - 最初のタスクから順番に処理
- ⚡ **シンプルなワークフロー** - `in`（追加）→ `next`（確認）→ `done`（完了）
- 🔧 **柔軟な設定** - CLI、環境変数、設定ファイルで設定可能

## インストール

### uv tools でインストール（推奨）

```bash
# 試用（一時的に実行）
uvx --from git+https://github.com/<USER>/<REPO> tasq --help

# 永続インストール
uv tool install git+https://github.com/<USER>/<REPO>

# PATHが通っていない場合
uv tool update-shell
```

### pip でインストール

```bash
pip install git+https://github.com/<USER>/<REPO>
```

## 使い方

### 基本的なワークフロー

```bash
# タスクを追加（キューの末尾に追加）
tasq task in "レポートを書く"
tasq task in "メールを返信する"
tasq task in "(A) 緊急の電話をかける"

# 次のタスクを確認（キューの先頭）
tasq task next
# 出力: 2024-12-16 レポートを書く

# タスクを完了（キューの先頭を完了としてマーク）
tasq task done
# 出力: 完了: x 2024-12-16 2024-12-16 レポートを書く

# 次のタスクを確認
tasq task next
# 出力: 2024-12-16 メールを返信する
```

### 設定

```bash
# 現在のtodo.txtパスを確認
tasq config path

# todo.txtのパスを設定
tasq config set-path ~/Documents/todo.txt

# 環境変数で設定
export TASQ_FILE=~/my-todo.txt

# CLIオプションで一時的に指定
tasq --file ./project-todo.txt task next
```

### 設定優先順位

1. CLIオプション (`--file PATH`)
2. 環境変数 (`TASQ_FILE`)
3. 設定ファイル (`~/.config/tasq/config.toml`)
4. デフォルト (`./todo.txt` または `~/todo.txt`)

### JSON出力

```bash
# 機械可読なJSON形式で出力
tasq --json task next
# 出力: {"index": 0, "text": "2024-12-16 タスク", "completed": false, ...}
```

## コマンド一覧

| コマンド | 説明 |
|---------|------|
| `tasq task in TEXT` | 新しいタスクをキューの末尾に追加 |
| `tasq task next` | キューの先頭にある次の未完了タスクを表示 |
| `tasq task done` | キューの先頭のタスクを完了としてマーク |
| `tasq config path` | 現在のtodo.txtパスとソースを表示 |
| `tasq config set-path PATH` | デフォルトのtodo.txtパスを設定 |
| `tasq self version` | バージョンを表示 |

## グローバルオプション

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--file PATH` | `-f` | todo.txtファイルのパスを指定 |
| `--json` | `-j` | JSON形式で出力 |
| `--verbose` | `-v` | 詳細ログを表示 |
| `--version` | `-V` | バージョンを表示 |

## todo.txt互換性

tasqは[todo.txt形式](https://github.com/todotxt/todo.txt)に完全準拠しています：

- **優先度**: `(A) タスク` - A-Zの優先度
- **作成日**: `YYYY-MM-DD タスク` - ISO 8601形式
- **完了**: `x YYYY-MM-DD タスク` - 完了日付き
- **プロジェクト**: `+project` - プロジェクトタグ
- **コンテキスト**: `@context` - コンテキストタグ
- **メタデータ**: `key:value` - カスタムメタデータ

### 完了時の処理

- `x ` + 完了日を先頭に追加
- 作成日がある場合は完了日の後に配置
- 優先度 `(A)` は `pri:A` に変換して保持

## 開発

```bash
# リポジトリをクローン
git clone https://github.com/<USER>/<REPO>
cd tasq

# 開発環境セットアップ
uv sync --dev

# テスト実行
uv run pytest tests/ -v

# ローカルで実行
uv run tasq --help
```

## ライセンス

MIT License