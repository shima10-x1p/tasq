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


class TestTaskList:
    """Tests for tasq task list command."""

    def test_list_default_shows_incomplete_only(self, tmp_path: Path) -> None:
        """Verify default behavior shows only incomplete tasks."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text(
            "Task 1\nx 2024-01-01 Done task\nTask 2\n", encoding="utf-8"
        )

        result = runner.invoke(app, ["--file", str(todo_file), "task", "list"])

        assert result.exit_code == 0
        assert "[0] Task 1" in result.stdout
        assert "[2] Task 2" in result.stdout
        assert "Done task" not in result.stdout

    def test_list_all_includes_completed(self, tmp_path: Path) -> None:
        """Verify --all includes completed tasks."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text(
            "Task 1\nx 2024-01-01 Done task\nTask 2\n", encoding="utf-8"
        )

        result = runner.invoke(app, ["--file", str(todo_file), "task", "list", "--all"])

        assert result.exit_code == 0
        assert "[0] Task 1" in result.stdout
        assert "[1] x 2024-01-01 Done task" in result.stdout
        assert "[2] Task 2" in result.stdout

    def test_list_completed_only(self, tmp_path: Path) -> None:
        """Verify --completed shows only completed tasks."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("Task 1\nx 2024-01-01 Done task\n", encoding="utf-8")

        result = runner.invoke(
            app, ["--file", str(todo_file), "task", "list", "--completed"]
        )

        assert result.exit_code == 0
        assert "Task 1" not in result.stdout
        assert "[1] x 2024-01-01 Done task" in result.stdout

    def test_list_limit(self, tmp_path: Path) -> None:
        """Verify --limit caps output after filtering."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("Task 1\nTask 2\nTask 3\nTask 4\n", encoding="utf-8")

        result = runner.invoke(
            app, ["--file", str(todo_file), "task", "list", "--limit", "2"]
        )

        assert result.exit_code == 0
        assert "[0] Task 1" in result.stdout
        assert "[1] Task 2" in result.stdout
        assert "Task 3" not in result.stdout
        assert "Task 4" not in result.stdout

    def test_list_json_output(self, tmp_path: Path) -> None:
        """Verify JSON output format."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text(
            "(A) 2024-01-15 Task +project @context due:2024-02-01\n",
            encoding="utf-8",
        )

        result = runner.invoke(
            app, ["--file", str(todo_file), "--json", "task", "list"]
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data) == 1
        assert data[0]["index"] == 0
        assert data[0]["completed"] is False
        assert data[0]["priority"] == "A"
        assert data[0]["creation_date"] == "2024-01-15"
        assert "project" in data[0]["projects"]
        assert "context" in data[0]["contexts"]
        assert data[0]["key_values"]["due"] == "2024-02-01"

    def test_list_preserves_file_order(self, tmp_path: Path) -> None:
        """Verify tasks are listed in file order, not sorted."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text(
            "(C) Low priority\n(A) High priority\n(B) Medium priority\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["--file", str(todo_file), "task", "list"])

        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        assert "Low priority" in lines[0]
        assert "High priority" in lines[1]
        assert "Medium priority" in lines[2]

    def test_list_file_missing(self, tmp_path: Path) -> None:
        """Verify empty output when file is missing."""
        todo_file = tmp_path / "nonexistent.txt"

        result = runner.invoke(app, ["--file", str(todo_file), "task", "list"])

        assert result.exit_code == 0
        assert result.stdout.strip() == ""

    def test_list_empty_file(self, tmp_path: Path) -> None:
        """Verify empty output for empty file."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "list"])

        assert result.exit_code == 0
        assert result.stdout.strip() == ""


class TestTaskSkip:
    """Tests for tasq task skip command."""

    def test_skip_moves_first_incomplete_to_end(self, tmp_path: Path) -> None:
        """Verify first incomplete task moves to end of incomplete block."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("Task 1\nTask 2\nTask 3\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "skip"])

        assert result.exit_code == 0
        assert "Skipped:" in result.stdout
        assert "Task 1" in result.stdout

        lines = todo_file.read_text(encoding="utf-8").strip().split("\n")
        assert lines[0] == "Task 2"
        assert lines[1] == "Task 3"
        assert lines[2] == "Task 1"

    def test_skip_keeps_completed_at_bottom(self, tmp_path: Path) -> None:
        """Verify completed tasks stay at the bottom."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text(
            "Task 1\nTask 2\nx 2024-01-01 Done task\n", encoding="utf-8"
        )

        result = runner.invoke(app, ["--file", str(todo_file), "task", "skip"])

        assert result.exit_code == 0
        lines = todo_file.read_text(encoding="utf-8").strip().split("\n")
        assert lines[0] == "Task 2"
        assert lines[1] == "Task 1"
        assert lines[2] == "x 2024-01-01 Done task"

    def test_skip_no_content_change(self, tmp_path: Path) -> None:
        """Verify task content is not modified."""
        todo_file = tmp_path / "todo.txt"
        original_task = "(A) 2024-01-15 Important task +project @context"
        todo_file.write_text(f"{original_task}\nTask 2\n", encoding="utf-8")

        runner.invoke(app, ["--file", str(todo_file), "task", "skip"])

        lines = todo_file.read_text(encoding="utf-8").strip().split("\n")
        assert lines[1] == original_task

    def test_skip_single_incomplete_task(self, tmp_path: Path) -> None:
        """Verify skip does nothing with only one incomplete task."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("Only task\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "skip"])

        assert result.exit_code == 1
        # Error output goes to stderr, use result.output
        assert "No incomplete tasks to skip" in result.output

    def test_skip_no_incomplete_tasks(self, tmp_path: Path) -> None:
        """Verify error when no incomplete tasks."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("x 2024-01-01 Done task\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "skip"])

        assert result.exit_code == 1
        # Error output goes to stderr, use result.output
        assert "No incomplete tasks to skip" in result.output

    def test_skip_file_missing(self, tmp_path: Path) -> None:
        """Verify error when file doesn't exist."""
        todo_file = tmp_path / "nonexistent.txt"

        result = runner.invoke(app, ["--file", str(todo_file), "task", "skip"])

        assert result.exit_code == 1

    def test_skip_json_output(self, tmp_path: Path) -> None:
        """Verify JSON output format."""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("Task 1\nTask 2\n", encoding="utf-8")

        result = runner.invoke(
            app, ["--file", str(todo_file), "--json", "task", "skip"]
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["moved"] is True
        assert data["from_index"] == 0
        assert data["to_index"] == 1
        assert data["raw"] == "Task 1"
