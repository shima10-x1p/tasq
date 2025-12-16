"""設定解決モジュール

設定の優先順位:
1. CLIオプション --file PATH
2. 環境変数 TASQ_FILE
3. 設定ファイル
4. デフォルト（./todo.txt または ~/todo.txt）
"""

import os
import sys
from pathlib import Path

# Python 3.11以上はtomllibが標準ライブラリに含まれる
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# 設定ソースを示す定数
SOURCE_CLI = "cli"
SOURCE_ENV = "env"
SOURCE_CONFIG = "config"
SOURCE_DEFAULT = "default"

# 環境変数名
ENV_VAR_NAME = "TASQ_FILE"


def get_config_path() -> Path:
    """設定ファイルのパスを取得する

    Returns:
        設定ファイルのPath（存在有無に関わらず）
    """
    # Windowsの場合は%APPDATA%を使用
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "tasq" / "config.toml"
        # フォールバック
        return Path.home() / ".config" / "tasq" / "config.toml"

    # Linux/macOSの場合はXDGを優先
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "tasq" / "config.toml"

    return Path.home() / ".config" / "tasq" / "config.toml"


def read_config() -> dict:
    """設定ファイルを読み込む

    Returns:
        設定の辞書（ファイルが存在しない場合は空辞書）
    """
    config_path = get_config_path()
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def write_config(todo_file: str) -> None:
    """設定ファイルにtodo_fileパスを書き込む

    Args:
        todo_file: 保存するtodo.txtのパス
    """
    config_path = get_config_path()

    # 親ディレクトリを作成
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # TOML形式で書き込み
    content = f'todo_file = "{todo_file}"\n'
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)


def get_default_todo_path() -> Path:
    """デフォルトのtodo.txtパスを取得する

    Returns:
        ./todo.txtが存在すればそれ、なければ~/todo.txt
    """
    local_path = Path("./todo.txt")
    if local_path.exists():
        return local_path.resolve()

    return Path.home() / "todo.txt"


def get_todo_file_path(cli_path: str | None = None) -> tuple[Path, str]:
    """todo.txtのパスを解決する

    優先順位:
    1. CLIオプション
    2. 環境変数 TASQ_FILE
    3. 設定ファイル
    4. デフォルト

    Args:
        cli_path: CLIで指定されたパス（Noneの場合は未指定）

    Returns:
        (解決されたPath, ソース文字列) のタプル
    """
    # 1. CLIオプション
    if cli_path is not None:
        return Path(cli_path).resolve(), SOURCE_CLI

    # 2. 環境変数
    env_path = os.environ.get(ENV_VAR_NAME)
    if env_path:
        return Path(env_path).resolve(), SOURCE_ENV

    # 3. 設定ファイル
    config = read_config()
    config_path = config.get("todo_file")
    if config_path:
        return Path(config_path).resolve(), SOURCE_CONFIG

    # 4. デフォルト
    return get_default_todo_path(), SOURCE_DEFAULT
