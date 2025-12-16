"""Task command tests."""

import json
from pathlib import Path

from typer.testing import CliRunner

from tasq.cli import app

runner = CliRunner()


class TestTaskIn:
    """Tests for tasq task in command."""

    def test_task_in_adds_task_with_date(self, tmp_path: Path) -> None:
        """Verify task is added with creation date."""
        todo_file = tmp_path / "todo.txt"

        result = runner.invoke(
            app, ["--file", str(todo_file), "task", "in", "Test task"]
        )

        assert result.exit_code == 0
        assert "Added:" in result.stdout

        # Verify file content
        content = todo_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 1

        # Verify creation date (YYYY-MM-DD format) is present
        import re

        assert re.match(r"\d{4}-\d{2}-\d{2} Test task", lines[0])

    def test_task_in_appends_to_existing_file(self, tmp_path: Path) -> None:
        """Verify task is appended to existing file."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("Existing task\n", encoding="utf-8")

        result = runner.invoke(
            app, ["--file", str(todo_file), "task", "in", "New task"]
        )

        assert result.exit_code == 0
        lines = todo_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "Existing task"
        assert "New task" in lines[1]

    def test_task_in_with_priority(self, tmp_path: Path) -> None:
        """Verify priority task is formatted correctly."""
        todo_file = tmp_path / "todo.txt"

        result = runner.invoke(
            app, ["--file", str(todo_file), "task", "in", "(A) Important task"]
        )

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8").strip()
        # Priority should come before date
        import re

        assert re.match(r"\(A\) \d{4}-\d{2}-\d{2} Important task", content)

    def test_task_in_strips_newlines(self, tmp_path: Path) -> None:
        """Verify newlines are stripped from task text."""
        todo_file = tmp_path / "todo.txt"

        result = runner.invoke(
            app, ["--file", str(todo_file), "task", "in", "Task\nwith newline"]
        )

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8")
        # Newline should be replaced with space, single line in file
        assert content.count("\n") == 1

    def test_task_in_json_output(self, tmp_path: Path) -> None:
        """Verify JSON output mode."""
        todo_file = tmp_path / "todo.txt"

        result = runner.invoke(
            app, ["--file", str(todo_file), "--json", "task", "in", "JSON test"]
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "added" in data
        assert "JSON test" in data["added"]


class TestTaskNext:
    """Tests for tasq task next command."""

    def test_task_next_returns_first_incomplete(self, tmp_path: Path) -> None:
        """Verify first incomplete task is returned."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("First task\nSecond task\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "next"])

        assert result.exit_code == 0
        assert "First task" in result.stdout

    def test_task_next_skips_completed(self, tmp_path: Path) -> None:
        """Verify completed tasks are skipped."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("x 2024-01-01 Done task\nTodo task\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "next"])

        assert result.exit_code == 0
        assert "Todo task" in result.stdout
        assert "Done task" not in result.stdout

    def test_task_next_no_incomplete_tasks(self, tmp_path: Path) -> None:
        """Verify error when no incomplete tasks."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("x 2024-01-01 Done task\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "next"])

        assert result.exit_code == 1
        assert "No incomplete tasks" in result.stdout

    def test_task_next_file_not_found(self, tmp_path: Path) -> None:
        """Verify error when file doesn't exist."""
        todo_file = tmp_path / "nonexistent.txt"

        result = runner.invoke(app, ["--file", str(todo_file), "task", "next"])

        assert result.exit_code == 1

    def test_task_next_json_output(self, tmp_path: Path) -> None:
        """Verify JSON output mode."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text(
            "(A) 2024-01-15 Important task +project @context due:2024-02-01\n",
            encoding="utf-8",
        )

        result = runner.invoke(
            app, ["--file", str(todo_file), "--json", "task", "next"]
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["index"] == 0
        assert data["priority"] == "A"
        assert data["creation_date"] == "2024-01-15"
        assert "project" in data["projects"]
        assert "context" in data["contexts"]
        assert data["key_values"]["due"] == "2024-02-01"


class TestTaskDone:
    """Tests for tasq task done command."""

    def test_task_done_marks_first_incomplete(self, tmp_path: Path) -> None:
        """Verify first incomplete task is marked complete."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("Task 1\nTask 2\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        assert "Done:" in result.stdout

        lines = todo_file.read_text(encoding="utf-8").strip().split("\n")
        assert lines[0].startswith("x ")
        assert "Task 1" in lines[0]
        # Second task unchanged
        assert lines[1] == "Task 2"

    def test_task_done_with_completion_date(self, tmp_path: Path) -> None:
        """Verify completion date is added correctly."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("Task\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8").strip()
        # Should start with x YYYY-MM-DD
        import re

        assert re.match(r"x \d{4}-\d{2}-\d{2} Task", content)

    def test_task_done_preserves_creation_date(self, tmp_path: Path) -> None:
        """Verify creation date is preserved."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("2024-01-15 Task\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8").strip()
        # Should be: x completion_date creation_date Task
        import re

        match = re.match(r"x (\d{4}-\d{2}-\d{2}) (\d{4}-\d{2}-\d{2}) Task", content)
        assert match
        assert match.group(2) == "2024-01-15"  # Creation date preserved

    def test_task_done_priority_to_key_value(self, tmp_path: Path) -> None:
        """Verify priority (A) is converted to pri:A."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("(A) Important task\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8").strip()
        # Should not start with (A) and should have pri:A
        assert not content.startswith("(A)")
        assert "pri:A" in content

    def test_task_done_priority_with_creation_date(self, tmp_path: Path) -> None:
        """Verify priority and creation date are handled correctly."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("(B) 2024-01-15 Task\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8").strip()
        import re

        # Should be: x completion_date creation_date Task pri:B
        match = re.match(
            r"x (\d{4}-\d{2}-\d{2}) (\d{4}-\d{2}-\d{2}) Task pri:B", content
        )
        assert match
        assert match.group(2) == "2024-01-15"

    def test_task_done_skips_completed(self, tmp_path: Path) -> None:
        """Verify already completed tasks are skipped."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("x 2024-01-01 Done task\nTodo task\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        lines = todo_file.read_text(encoding="utf-8").strip().split("\n")
        # First line unchanged
        assert lines[0] == "x 2024-01-01 Done task"
        # Second line completed
        assert lines[1].startswith("x ")
        assert "Todo task" in lines[1]

    def test_task_done_no_incomplete_tasks(self, tmp_path: Path) -> None:
        """Verify error when no incomplete tasks."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("x 2024-01-01 Done task\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 1
