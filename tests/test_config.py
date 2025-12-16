"""設定コマンドのテスト"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from tasq.cli import app
from tasq.config import get_todo_file_path

runner = CliRunner()


class TestConfigPath:
    """tasq config path コマンドのテスト"""

    def test_config_path_with_cli_option(self, tmp_path: Path) -> None:
        """CLIオプションで指定したパスが最優先されることを確認"""
        todo_file = tmp_path / "cli-todo.txt"

        result = runner.invoke(app, ["--file", str(todo_file), "config", "path"])

        assert result.exit_code == 0
        assert str(todo_file) in result.stdout
        assert "CLIオプション" in result.stdout

    def test_config_path_with_env_var(self, tmp_path: Path) -> None:
        """環境変数で指定したパスが使用されることを確認"""
        todo_file = tmp_path / "env-todo.txt"

        with patch.dict(os.environ, {"TASQ_FILE": str(todo_file)}):
            result = runner.invoke(app, ["config", "path"])

        assert result.exit_code == 0
        assert str(todo_file) in result.stdout
        assert "環境変数" in result.stdout

    def test_config_path_json_output(self, tmp_path: Path) -> None:
        """JSON出力モードの確認"""
        todo_file = tmp_path / "todo.txt"

        result = runner.invoke(
            app, ["--file", str(todo_file), "--json", "config", "path"]
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "path" in data
        assert "source" in data
        assert data["source"] == "cli"


class TestConfigSetPath:
    """tasq config set-path コマンドのテスト"""

    def test_config_set_path_creates_config_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """設定ファイルが作成されることを確認"""
        config_dir = tmp_path / "config"
        config_file = config_dir / "tasq" / "config.toml"

        # プラットフォームに応じた設定ディレクトリ環境変数を設定
        if sys.platform == "win32":
            monkeypatch.setenv("APPDATA", str(config_dir))
        else:
            monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

        todo_file = tmp_path / "my-todo.txt"

        result = runner.invoke(app, ["config", "set-path", str(todo_file)])

        assert result.exit_code == 0
        assert "設定を保存しました" in result.stdout

        # 設定ファイルが作成されたか確認
        assert config_file.exists()
        content = config_file.read_text(encoding="utf-8")
        assert str(todo_file.resolve()) in content

    def test_config_set_path_json_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JSON出力モードの確認"""
        config_dir = tmp_path / "config"
        if sys.platform == "win32":
            monkeypatch.setenv("APPDATA", str(config_dir))
        else:
            monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

        todo_file = tmp_path / "todo.txt"

        result = runner.invoke(app, ["--json", "config", "set-path", str(todo_file)])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "path" in data
        assert "config_file" in data


class TestConfigPrecedence:
    """設定優先順位のテスト"""

    def test_cli_overrides_env(self, tmp_path: Path) -> None:
        """CLIオプションが環境変数より優先されることを確認"""
        cli_file = tmp_path / "cli.txt"
        env_file = tmp_path / "env.txt"

        with patch.dict(os.environ, {"TASQ_FILE": str(env_file)}):
            result = runner.invoke(app, ["--file", str(cli_file), "config", "path"])

        assert result.exit_code == 0
        assert str(cli_file) in result.stdout
        assert "CLIオプション" in result.stdout

    def test_env_overrides_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数が設定ファイルより優先されることを確認"""
        config_dir = tmp_path / "config"
        config_file = config_dir / "tasq" / "config.toml"
        config_file.parent.mkdir(parents=True)

        config_todo = tmp_path / "config.txt"
        env_todo = tmp_path / "env.txt"

        # 設定ファイルを作成（Windowsのバックスラッシュをエスケープ）
        escaped_path = str(config_todo).replace("\\", "\\\\")
        config_file.write_text(f'todo_file = "{escaped_path}"\n', encoding="utf-8")

        if sys.platform == "win32":
            monkeypatch.setenv("APPDATA", str(config_dir))
        else:
            monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("TASQ_FILE", str(env_todo))

        result = runner.invoke(app, ["config", "path"])

        assert result.exit_code == 0
        assert str(env_todo) in result.stdout
        assert "環境変数" in result.stdout

    def test_config_overrides_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """設定ファイルがデフォルトより優先されることを確認"""
        config_dir = tmp_path / "config"
        config_file = config_dir / "tasq" / "config.toml"
        config_file.parent.mkdir(parents=True)

        config_todo = tmp_path / "my-todo.txt"

        # 設定ファイルを作成（Windowsのバックスラッシュをエスケープ）
        escaped_path = str(config_todo).replace("\\", "\\\\")
        config_file.write_text(f'todo_file = "{escaped_path}"\n', encoding="utf-8")

        if sys.platform == "win32":
            monkeypatch.setenv("APPDATA", str(config_dir))
        else:
            monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        # TASQ_FILE環境変数を削除
        monkeypatch.delenv("TASQ_FILE", raising=False)

        result = runner.invoke(app, ["config", "path"])

        assert result.exit_code == 0
        assert str(config_todo) in result.stdout
        assert "設定ファイル" in result.stdout


class TestGetTodoFilePath:
    """get_todo_file_path 関数のテスト"""

    def test_cli_path_highest_priority(self) -> None:
        """CLIパスが最優先であることを確認"""
        path, source = get_todo_file_path("/cli/path/todo.txt")
        assert source == "cli"
        assert path == Path("/cli/path/todo.txt").resolve()

    def test_env_var_used_when_no_cli(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLIがない場合に環境変数が使用されることを確認"""
        monkeypatch.setenv("TASQ_FILE", "/env/todo.txt")
        path, source = get_todo_file_path(None)
        assert source == "env"

    def test_default_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """デフォルトへのフォールバックを確認"""
        # 環境変数を削除
        monkeypatch.delenv("TASQ_FILE", raising=False)
        # 設定ファイルがない場所を設定
        if sys.platform == "win32":
            monkeypatch.setenv("APPDATA", str(tmp_path / "nonexistent"))
        else:
            monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nonexistent"))
        # カレントディレクトリにtodo.txtがない状態で実行
        monkeypatch.chdir(tmp_path)

        path, source = get_todo_file_path(None)
        assert source == "default"
