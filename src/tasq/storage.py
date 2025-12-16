"""ストレージモジュール - ファイルI/O操作

アトミック書き込みとファイルロックを提供する。
"""

import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# Windowsの場合はmsvcrt、それ以外はfcntlを使用
if sys.platform == "win32":
    import msvcrt

    def _lock_file(f) -> None:
        """Windowsでファイルをロックする"""
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock_file(f) -> None:
        """Windowsでファイルロックを解除する"""
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass  # ロック解除失敗は無視
else:
    import fcntl

    def _lock_file(f) -> None:
        """Unix系でファイルをロックする"""
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock_file(f) -> None:
        """Unix系でファイルロックを解除する"""
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


@contextmanager
def file_lock(path: Path) -> Generator[None, None, None]:
    """ファイルロックを取得するコンテキストマネージャ

    ベストエフォートでロックを取得する。
    ロック取得に失敗した場合でも処理は継続する（警告のみ）。

    Args:
        path: ロック対象のファイルパス

    Yields:
        None
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_file = None

    try:
        # ロックファイルを作成してロック取得
        lock_file = open(lock_path, "w", encoding="utf-8")
        try:
            _lock_file(lock_file)
        except (OSError, BlockingIOError):
            # ロック取得失敗は警告のみで継続
            pass

        yield

    finally:
        if lock_file:
            try:
                _unlock_file(lock_file)
            except (OSError, ValueError):
                pass
            lock_file.close()
            # ロックファイルを削除（失敗しても無視）
            try:
                lock_path.unlink()
            except OSError:
                pass


def read_lines(path: Path) -> list[str]:
    """ファイルから全行を読み込む

    Args:
        path: 読み込むファイルのパス

    Returns:
        行のリスト（改行文字は含まない）

    Raises:
        FileNotFoundError: ファイルが存在しない場合
    """
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n\r") for line in f]


def write_lines_atomic(path: Path, lines: list[str]) -> None:
    """ファイルにアトミックに行を書き込む

    一時ファイルに書き込み、fsyncしてからリネームすることで
    書き込み途中でのデータ破損を防ぐ。

    Args:
        path: 書き込み先のファイルパス
        lines: 書き込む行のリスト
    """
    # 親ディレクトリを取得（同一ファイルシステム内でリネームするため）
    parent_dir = path.parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    # 一時ファイルに書き込み
    fd, tmp_path = tempfile.mkstemp(dir=parent_dir, prefix=".tasq_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

        # アトミックにリネーム
        # Windowsではos.replaceで既存ファイルを上書き可能
        os.replace(tmp_path, path)
    except Exception:
        # エラー時は一時ファイルを削除
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def append_line(path: Path, line: str) -> None:
    """ファイルに1行追加する

    ファイルが存在しない場合は作成する。

    Args:
        path: 追加先のファイルパス
        line: 追加する行（改行は自動付与）
    """
    # 親ディレクトリを作成
    path.parent.mkdir(parents=True, exist_ok=True)

    with file_lock(path):
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())


def update_line(path: Path, index: int, new_line: str) -> None:
    """ファイル内の特定行を更新する

    Args:
        path: 更新するファイルのパス
        index: 更新する行のインデックス（0始まり）
        new_line: 新しい行の内容

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        IndexError: インデックスが範囲外の場合
    """
    with file_lock(path):
        lines = read_lines(path)
        if index < 0 or index >= len(lines):
            raise IndexError(f"Line index {index} out of range (0-{len(lines) - 1})")
        lines[index] = new_line
        write_lines_atomic(path, lines)
