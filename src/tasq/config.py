"""Configuration resolution module.

Configuration priority:
1. CLI option --file PATH
2. Environment variable TASQ_FILE
3. Config file
4. Default (./todo.txt or ~/todo.txt)
"""

import os
import sys
from pathlib import Path

# Python 3.11+ has tomllib in standard library
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# Source constants
SOURCE_CLI = "cli"
SOURCE_ENV = "env"
SOURCE_CONFIG = "config"
SOURCE_DEFAULT = "default"

# Environment variable name
ENV_VAR_NAME = "TASQ_FILE"


class Config:
    """Configuration manager for tasq.

    Resolves the todo.txt file path based on priority:
    1. CLI option
    2. Environment variable
    3. Config file
    4. Default fallback

    Attributes:
        cli_path: Path specified via CLI option (if any).
    """

    def __init__(self, cli_path: str | None = None) -> None:
        """Initialize configuration with optional CLI path.

        Args:
            cli_path: Path specified via --file option.
        """
        self._cli_path = cli_path
        self._resolved_path: Path | None = None
        self._resolved_source: str | None = None

    @property
    def todo_file_path(self) -> Path:
        """Get the resolved todo.txt file path.

        Returns:
            Path to the todo.txt file.
        """
        if self._resolved_path is None:
            self._resolve()
        return self._resolved_path  # type: ignore

    @property
    def source(self) -> str:
        """Get the source of the resolved path.

        Returns:
            One of: 'cli', 'env', 'config', 'default'.
        """
        if self._resolved_source is None:
            self._resolve()
        return self._resolved_source  # type: ignore

    @property
    def source_description(self) -> str:
        """Get a human-readable description of the source.

        Returns:
            Description string.
        """
        descriptions = {
            SOURCE_CLI: "CLI option (--file)",
            SOURCE_ENV: f"Environment variable ({ENV_VAR_NAME})",
            SOURCE_CONFIG: f"Config file ({self.get_config_path()})",
            SOURCE_DEFAULT: "Default",
        }
        return descriptions.get(self.source, self.source)

    def _resolve(self) -> None:
        """Resolve the todo.txt path based on priority."""
        # 1. CLI option
        if self._cli_path is not None:
            self._resolved_path = Path(self._cli_path).resolve()
            self._resolved_source = SOURCE_CLI
            return

        # 2. Environment variable
        env_path = os.environ.get(ENV_VAR_NAME)
        if env_path:
            self._resolved_path = Path(env_path).resolve()
            self._resolved_source = SOURCE_ENV
            return

        # 3. Config file
        config = self._read_config()
        config_path = config.get("todo_file")
        if config_path:
            self._resolved_path = Path(config_path).resolve()
            self._resolved_source = SOURCE_CONFIG
            return

        # 4. Default
        self._resolved_path = self._get_default_path()
        self._resolved_source = SOURCE_DEFAULT

    def _read_config(self) -> dict:
        """Read the configuration file.

        Returns:
            Configuration dictionary.
        """
        config_path = self.get_config_path()
        if not config_path.exists():
            return {}

        try:
            with open(config_path, "rb") as f:
                return tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            return {}

    @staticmethod
    def _get_default_path() -> Path:
        """Get the default todo.txt path.

        Returns:
            ./todo.txt if it exists, else ~/todo.txt.
        """
        local_path = Path("./todo.txt")
        if local_path.exists():
            return local_path.resolve()

        return Path.home() / "todo.txt"

    @staticmethod
    def get_config_path() -> Path:
        """Get the configuration file path.

        Returns:
            Path to config.toml.
        """
        # Windows: use %APPDATA%
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "tasq" / "config.toml"
            return Path.home() / ".config" / "tasq" / "config.toml"

        # Linux/macOS: prefer XDG
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "tasq" / "config.toml"

        return Path.home() / ".config" / "tasq" / "config.toml"

    @classmethod
    def save(cls, todo_file: str) -> None:
        """Save the todo.txt path to the config file.

        Args:
            todo_file: Path to save.
        """
        config_path = cls.get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Escape backslashes for TOML on Windows
        escaped_path = todo_file.replace("\\", "\\\\")
        content = f'todo_file = "{escaped_path}"\n'

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)


# Backward compatibility functions
def get_config_path() -> Path:
    """Get the configuration file path.

    Returns:
        Path to config.toml.
    """
    return Config.get_config_path()


def read_config() -> dict:
    """Read the configuration file.

    Returns:
        Configuration dictionary.
    """
    config = Config()
    return config._read_config()


def write_config(todo_file: str) -> None:
    """Write the todo_file path to config.

    Args:
        todo_file: Path to save.
    """
    Config.save(todo_file)


def get_todo_file_path(cli_path: str | None = None) -> tuple[Path, str]:
    """Get the resolved todo.txt path and source.

    Args:
        cli_path: Path specified via CLI (if any).

    Returns:
        Tuple of (path, source).
    """
    config = Config(cli_path)
    return config.todo_file_path, config.source
