"""tasq CLIモジュール

Typerを使用したCLIアプリケーションのエントリーポイント。
サブコマンドグループ: task, config, self
"""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from tasq import __version__
from tasq.config import (
    SOURCE_CLI,
    SOURCE_CONFIG,
    SOURCE_DEFAULT,
    SOURCE_ENV,
    get_config_path,
    get_todo_file_path,
    write_config,
)
from tasq.storage import append_line, read_lines, update_line
from tasq.todotxt import format_new_task, is_completed, mark_complete, parse_task

# メインアプリケーション
app = typer.Typer(
    name="tasq",
    help="todo.txt互換のFIFOキュー型タスク管理ツール",
    no_args_is_help=True,
)

# サブコマンドグループ
task_app = typer.Typer(
    name="task",
    help="タスク操作コマンド",
    no_args_is_help=True,
)

config_app = typer.Typer(
    name="config",
    help="設定コマンド",
    no_args_is_help=True,
)

self_app = typer.Typer(
    name="self",
    help="ツール情報コマンド",
    no_args_is_help=True,
)

# サブコマンドグループをメインアプリに追加
app.add_typer(task_app, name="task")
app.add_typer(config_app, name="config")
app.add_typer(self_app, name="self")


# グローバルオプション用のコンテキスト
class GlobalContext:
    """グローバルオプションを保持するコンテキスト"""

    def __init__(self) -> None:
        self.file: str | None = None
        self.json_output: bool = False
        self.verbose: bool = False


# コンテキスト変数
_context = GlobalContext()


def version_callback(value: bool) -> None:
    """--version オプションのコールバック"""
    if value:
        typer.echo(f"tasq version {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    file: Annotated[
        Optional[str],
        typer.Option(
            "--file",
            "-f",
            help="todo.txtファイルのパスを指定",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="JSON形式で出力",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="詳細ログを表示",
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="バージョンを表示",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """tasq - todo.txt互換のFIFOキュー型タスク管理ツール"""
    _context.file = file
    _context.json_output = json_output
    _context.verbose = verbose


# ===== task サブコマンド =====


@task_app.command("in")
def task_in(
    text: Annotated[
        str,
        typer.Argument(help="追加するタスクのテキスト"),
    ],
) -> None:
    """新しいタスクをキューの末尾に追加する"""
    todo_path, source = get_todo_file_path(_context.file)

    if _context.verbose:
        typer.echo(f"[verbose] todo.txt: {todo_path} (from {source})")

    # 新規タスク行を生成（作成日付き）
    task_line = format_new_task(text, add_creation_date=True)

    # ファイルに追加
    append_line(todo_path, task_line)

    if _context.json_output:
        result = {"added": task_line, "file": str(todo_path)}
        typer.echo(json.dumps(result, ensure_ascii=False))
    else:
        typer.echo(f"追加: {task_line}")


@task_app.command("next")
def task_next() -> None:
    """キューの先頭にある次の未完了タスクを表示する"""
    todo_path, source = get_todo_file_path(_context.file)

    if _context.verbose:
        typer.echo(f"[verbose] todo.txt: {todo_path} (from {source})")

    # ファイルが存在しない場合
    if not todo_path.exists():
        if _context.json_output:
            typer.echo(json.dumps({"error": "No tasks found", "file": str(todo_path)}))
        else:
            typer.echo("タスクがありません（ファイルが存在しません）")
        raise typer.Exit(code=1)

    # 最初の未完了タスクを探す
    lines = read_lines(todo_path)
    for index, line in enumerate(lines):
        if line.strip() and not is_completed(line):
            parsed = parse_task(line)

            if _context.json_output:
                result = {
                    "index": index,
                    "text": line,
                    "completed": parsed["completed"],
                    "completion_date": parsed["completion_date"],
                    "creation_date": parsed["creation_date"],
                    "priority": parsed["priority"],
                    "projects": parsed["projects"],
                    "contexts": parsed["contexts"],
                    "key_values": parsed["key_values"],
                }
                typer.echo(json.dumps(result, ensure_ascii=False))
            else:
                typer.echo(line)
            return

    # 未完了タスクが見つからない場合
    if _context.json_output:
        typer.echo(json.dumps({"error": "No incomplete tasks", "file": str(todo_path)}))
    else:
        typer.echo("未完了タスクがありません")
    raise typer.Exit(code=1)


@task_app.command("done")
def task_done() -> None:
    """キューの先頭にある次の未完了タスクを完了としてマークする"""
    todo_path, source = get_todo_file_path(_context.file)

    if _context.verbose:
        typer.echo(f"[verbose] todo.txt: {todo_path} (from {source})")

    # ファイルが存在しない場合
    if not todo_path.exists():
        typer.echo("タスクがありません（ファイルが存在しません）", err=True)
        raise typer.Exit(code=1)

    # 最初の未完了タスクを探して完了にする
    lines = read_lines(todo_path)
    for index, line in enumerate(lines):
        if line.strip() and not is_completed(line):
            # タスクを完了としてマーク
            completed_line = mark_complete(line)

            # ファイルを更新
            update_line(todo_path, index, completed_line)

            if _context.json_output:
                result = {
                    "completed": completed_line,
                    "original": line,
                    "index": index,
                }
                typer.echo(json.dumps(result, ensure_ascii=False))
            else:
                typer.echo(f"完了: {completed_line}")
            return

    # 未完了タスクが見つからない場合
    typer.echo("未完了タスクがありません", err=True)
    raise typer.Exit(code=1)


# ===== config サブコマンド =====


@config_app.command("path")
def config_path() -> None:
    """現在解決されているtodo.txtのパスを表示する"""
    todo_path, source = get_todo_file_path(_context.file)

    # ソースの説明
    source_descriptions = {
        SOURCE_CLI: "CLIオプション (--file)",
        SOURCE_ENV: "環境変数 (TASQ_FILE)",
        SOURCE_CONFIG: f"設定ファイル ({get_config_path()})",
        SOURCE_DEFAULT: "デフォルト",
    }
    source_desc = source_descriptions.get(source, source)

    if _context.json_output:
        result = {
            "path": str(todo_path),
            "source": source,
            "source_description": source_desc,
            "exists": todo_path.exists(),
        }
        typer.echo(json.dumps(result, ensure_ascii=False))
    else:
        typer.echo(f"パス: {todo_path}")
        typer.echo(f"ソース: {source_desc}")
        typer.echo(f"存在: {'はい' if todo_path.exists() else 'いいえ'}")


@config_app.command("set-path")
def config_set_path(
    path: Annotated[
        str,
        typer.Argument(help="設定するtodo.txtのパス"),
    ],
) -> None:
    """todo.txtのデフォルトパスを設定ファイルに保存する"""
    # パスを絶対パスに変換
    abs_path = Path(path).resolve()

    # 設定ファイルに書き込み
    write_config(str(abs_path))

    config_file = get_config_path()

    if _context.json_output:
        result = {
            "path": str(abs_path),
            "config_file": str(config_file),
        }
        typer.echo(json.dumps(result, ensure_ascii=False))
    else:
        typer.echo(f"設定を保存しました: {abs_path}")
        typer.echo(f"設定ファイル: {config_file}")


# ===== self サブコマンド =====


@self_app.command("version")
def self_version() -> None:
    """バージョン情報を表示する"""
    if _context.json_output:
        result = {"version": __version__}
        typer.echo(json.dumps(result, ensure_ascii=False))
    else:
        typer.echo(f"tasq version {__version__}")


def main() -> None:
    """CLIエントリーポイント"""
    app()


if __name__ == "__main__":
    main()
