"""Storage module for todo.txt file operations.

Provides atomic writes and file locking for safe concurrent access.
"""

import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from tasq.todotxt import Task

# Platform-specific file locking
if sys.platform == "win32":
    import msvcrt

    def _lock_file(f) -> None:
        """Lock a file on Windows."""
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock_file(f) -> None:
        """Unlock a file on Windows."""
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
else:
    import fcntl

    def _lock_file(f) -> None:
        """Lock a file on Unix systems."""
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock_file(f) -> None:
        """Unlock a file on Unix systems."""
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


@contextmanager
def file_lock(path: Path) -> Generator[None, None, None]:
    """Context manager for acquiring a file lock.

    Best-effort locking: continues even if lock acquisition fails.

    Args:
        path: Path to the file to lock.

    Yields:
        None
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_file = None

    try:
        lock_file = open(lock_path, "w", encoding="utf-8")
        try:
            _lock_file(lock_file)
        except (OSError, BlockingIOError):
            pass  # Continue without lock

        yield

    finally:
        if lock_file:
            try:
                _unlock_file(lock_file)
            except (OSError, ValueError):
                pass
            lock_file.close()
            try:
                lock_path.unlink()
            except OSError:
                pass


class TodoFile:
    """Manages reading and writing of a todo.txt file.

    Provides atomic writes and file locking for safe file operations.

    Attributes:
        path: Path to the todo.txt file.
    """

    def __init__(self, path: Path) -> None:
        """Initialize with a path to the todo.txt file.

        Args:
            path: Path to the todo.txt file.
        """
        self.path = path

    def exists(self) -> bool:
        """Check if the todo.txt file exists.

        Returns:
            True if the file exists.
        """
        return self.path.exists()

    def read_lines(self) -> list[str]:
        """Read all lines from the file.

        Returns:
            List of lines without trailing newlines.

        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        with open(self.path, "r", encoding="utf-8") as f:
            return [line.rstrip("\n\r") for line in f]

    def read_tasks(self) -> list[Task]:
        """Read and parse all tasks from the file.

        Returns:
            List of Task objects.

        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        lines = self.read_lines()
        return [Task.parse(line) for line in lines if line.strip()]

    def write_lines(self, lines: list[str]) -> None:
        """Atomically write lines to the file.

        Uses a temporary file and rename for atomicity.

        Args:
            lines: List of lines to write.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            dir=self.path.parent, prefix=".tasq_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, self.path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def write_tasks(self, tasks: list[Task]) -> None:
        """Atomically write tasks to the file.

        Args:
            tasks: List of Task objects to write.
        """
        lines = [task.to_line() for task in tasks]
        self.write_lines(lines)

    def append_task(self, task: Task) -> None:
        """Append a single task to the file.

        Creates the file if it doesn't exist.

        Args:
            task: Task object to append.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with file_lock(self.path):
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(task.to_line() + "\n")
                f.flush()
                os.fsync(f.fileno())

    def get_next_incomplete(self) -> tuple[int, Task] | None:
        """Find the first incomplete task.

        Returns:
            Tuple of (index, Task) or None if no incomplete tasks.
        """
        if not self.exists():
            return None

        lines = self.read_lines()
        for index, line in enumerate(lines):
            if line.strip() and not line.strip().startswith("x "):
                return index, Task.parse(line)

        return None

    def complete_task(self, index: int) -> Task:
        """Mark a task at the given index as complete.

        Args:
            index: Zero-based line index.

        Returns:
            The completed Task object.

        Raises:
            IndexError: If the index is out of range.
        """
        with file_lock(self.path):
            lines = self.read_lines()
            if index < 0 or index >= len(lines):
                raise IndexError(
                    f"Line index {index} out of range (0-{len(lines) - 1})"
                )

            task = Task.parse(lines[index])
            completed_task = task.mark_complete()
            lines[index] = completed_task.to_line()

            self.write_lines(lines)

            return completed_task


# Backward compatibility functions
def read_lines(path: Path) -> list[str]:
    """Read all lines from a file.

    Args:
        path: Path to the file.

    Returns:
        List of lines without trailing newlines.
    """
    todo_file = TodoFile(path)
    return todo_file.read_lines()


def write_lines_atomic(path: Path, lines: list[str]) -> None:
    """Atomically write lines to a file.

    Args:
        path: Path to the file.
        lines: Lines to write.
    """
    todo_file = TodoFile(path)
    todo_file.write_lines(lines)


def append_line(path: Path, line: str) -> None:
    """Append a line to a file.

    Args:
        path: Path to the file.
        line: Line to append.
    """
    task = Task.parse(line)
    todo_file = TodoFile(path)
    todo_file.append_task(task)


def update_line(path: Path, index: int, new_line: str) -> None:
    """Update a specific line in a file.

    Args:
        path: Path to the file.
        index: Zero-based line index.
        new_line: New content for the line.
    """
    with file_lock(path):
        lines = read_lines(path)
        if index < 0 or index >= len(lines):
            raise IndexError(f"Line index {index} out of range (0-{len(lines) - 1})")
        lines[index] = new_line
        write_lines_atomic(path, lines)
