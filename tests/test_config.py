"""Configuration command tests."""

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
    """Tests for tasq config path command."""

    def test_config_path_with_cli_option(self, tmp_path: Path) -> None:
        """Verify CLI option takes highest priority."""
        todo_file = tmp_path / "cli-todo.txt"

        result = runner.invoke(app, ["--file", str(todo_file), "config", "path"])

        assert result.exit_code == 0
        assert str(todo_file) in result.stdout
        assert "CLI option" in result.stdout

    def test_config_path_with_env_var(self, tmp_path: Path) -> None:
        """Verify environment variable is used."""
        todo_file = tmp_path / "env-todo.txt"

        with patch.dict(os.environ, {"TASQ_FILE": str(todo_file)}):
            result = runner.invoke(app, ["config", "path"])

        assert result.exit_code == 0
        assert str(todo_file) in result.stdout
        assert "Environment variable" in result.stdout

    def test_config_path_json_output(self, tmp_path: Path) -> None:
        """Verify JSON output mode."""
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
    """Tests for tasq config set-path command."""

    def test_config_set_path_creates_config_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify config file is created."""
        config_dir = tmp_path / "config"
        config_file = config_dir / "tasq" / "config.toml"

        # Set platform-specific config directory
        if sys.platform == "win32":
            monkeypatch.setenv("APPDATA", str(config_dir))
        else:
            monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))

        todo_file = tmp_path / "my-todo.txt"

        result = runner.invoke(app, ["config", "set-path", str(todo_file)])

        assert result.exit_code == 0
        assert "Configuration saved" in result.stdout

        # Verify config file was created
        assert config_file.exists()
        content = config_file.read_text(encoding="utf-8")
        # Path is escaped in TOML file on Windows
        escaped_path = str(todo_file.resolve()).replace("\\", "\\\\")
        assert escaped_path in content or str(todo_file.resolve()) in content

    def test_config_set_path_json_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify JSON output mode."""
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
    """Tests for configuration precedence."""

    def test_cli_overrides_env(self, tmp_path: Path) -> None:
        """Verify CLI option overrides environment variable."""
        cli_file = tmp_path / "cli.txt"
        env_file = tmp_path / "env.txt"

        with patch.dict(os.environ, {"TASQ_FILE": str(env_file)}):
            result = runner.invoke(app, ["--file", str(cli_file), "config", "path"])

        assert result.exit_code == 0
        assert str(cli_file) in result.stdout
        assert "CLI option" in result.stdout

    def test_env_overrides_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify environment variable overrides config file."""
        config_dir = tmp_path / "config"
        config_file = config_dir / "tasq" / "config.toml"
        config_file.parent.mkdir(parents=True)

        config_todo = tmp_path / "config.txt"
        env_todo = tmp_path / "env.txt"

        # Create config file (escape backslashes for Windows)
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
        assert "Environment variable" in result.stdout

    def test_config_overrides_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify config file overrides default."""
        config_dir = tmp_path / "config"
        config_file = config_dir / "tasq" / "config.toml"
        config_file.parent.mkdir(parents=True)

        config_todo = tmp_path / "my-todo.txt"

        # Create config file (escape backslashes for Windows)
        escaped_path = str(config_todo).replace("\\", "\\\\")
        config_file.write_text(f'todo_file = "{escaped_path}"\n', encoding="utf-8")

        if sys.platform == "win32":
            monkeypatch.setenv("APPDATA", str(config_dir))
        else:
            monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        # Remove TASQ_FILE environment variable
        monkeypatch.delenv("TASQ_FILE", raising=False)

        result = runner.invoke(app, ["config", "path"])

        assert result.exit_code == 0
        assert str(config_todo) in result.stdout
        assert "Config file" in result.stdout


class TestGetTodoFilePath:
    """Tests for get_todo_file_path function."""

    def test_cli_path_highest_priority(self) -> None:
        """Verify CLI path has highest priority."""
        path, source = get_todo_file_path("/cli/path/todo.txt")
        assert source == "cli"
        assert path == Path("/cli/path/todo.txt").resolve()

    def test_env_var_used_when_no_cli(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify environment variable is used when no CLI path."""
        monkeypatch.setenv("TASQ_FILE", "/env/todo.txt")
        path, source = get_todo_file_path(None)
        assert source == "env"

    def test_default_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify fallback to default."""
        # Remove environment variable
        monkeypatch.delenv("TASQ_FILE", raising=False)
        # Set config file location to non-existent path
        if sys.platform == "win32":
            monkeypatch.setenv("APPDATA", str(tmp_path / "nonexistent"))
        else:
            monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nonexistent"))
        # Change to directory without todo.txt
        monkeypatch.chdir(tmp_path)

        path, source = get_todo_file_path(None)
        assert source == "default"
