"""タスクコマンドのテスト"""

import json
from pathlib import Path

from typer.testing import CliRunner

from tasq.cli import app

runner = CliRunner()


class TestTaskIn:
    """tasq task in コマンドのテスト"""

    def test_task_in_adds_task_with_date(self, tmp_path: Path) -> None:
        """タスク追加時に作成日が付与されることを確認"""
        todo_file = tmp_path / "todo.txt"

        result = runner.invoke(
            app, ["--file", str(todo_file), "task", "in", "テストタスク"]
        )

        assert result.exit_code == 0
        assert "追加:" in result.stdout

        # ファイル内容を確認
        content = todo_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 1

        # 作成日（YYYY-MM-DD形式）が含まれていることを確認
        import re

        assert re.match(r"\d{4}-\d{2}-\d{2} テストタスク", lines[0])

    def test_task_in_appends_to_existing_file(self, tmp_path: Path) -> None:
        """既存ファイルへのタスク追加を確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("既存タスク\n", encoding="utf-8")

        result = runner.invoke(
            app, ["--file", str(todo_file), "task", "in", "新規タスク"]
        )

        assert result.exit_code == 0
        lines = todo_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "既存タスク"
        assert "新規タスク" in lines[1]

    def test_task_in_with_priority(self, tmp_path: Path) -> None:
        """優先度付きタスクの追加を確認"""
        todo_file = tmp_path / "todo.txt"

        result = runner.invoke(
            app, ["--file", str(todo_file), "task", "in", "(A) 重要タスク"]
        )

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8").strip()
        # 優先度の後に日付が挿入される
        import re

        assert re.match(r"\(A\) \d{4}-\d{2}-\d{2} 重要タスク", content)

    def test_task_in_strips_newlines(self, tmp_path: Path) -> None:
        """改行文字が除去されることを確認"""
        todo_file = tmp_path / "todo.txt"

        result = runner.invoke(
            app, ["--file", str(todo_file), "task", "in", "タスク\n改行あり"]
        )

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8")
        # 改行がスペースに置き換えられて1行になっている
        assert content.count("\n") == 1

    def test_task_in_json_output(self, tmp_path: Path) -> None:
        """JSON出力モードの確認"""
        todo_file = tmp_path / "todo.txt"

        result = runner.invoke(
            app, ["--file", str(todo_file), "--json", "task", "in", "JSONテスト"]
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "added" in data
        assert "JSONテスト" in data["added"]


class TestTaskNext:
    """tasq task next コマンドのテスト"""

    def test_task_next_returns_first_incomplete(self, tmp_path: Path) -> None:
        """最初の未完了タスクが返されることを確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("最初のタスク\n2番目のタスク\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "next"])

        assert result.exit_code == 0
        assert "最初のタスク" in result.stdout

    def test_task_next_skips_completed(self, tmp_path: Path) -> None:
        """完了タスクがスキップされることを確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text(
            "x 2024-01-01 済みタスク\nやることタスク\n", encoding="utf-8"
        )

        result = runner.invoke(app, ["--file", str(todo_file), "task", "next"])

        assert result.exit_code == 0
        assert "やることタスク" in result.stdout
        assert "済みタスク" not in result.stdout

    def test_task_next_no_incomplete_tasks(self, tmp_path: Path) -> None:
        """未完了タスクがない場合のエラー確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("x 2024-01-01 済みタスク\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "next"])

        assert result.exit_code == 1
        assert "未完了タスクがありません" in result.stdout

    def test_task_next_file_not_found(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合のエラー確認"""
        todo_file = tmp_path / "nonexistent.txt"

        result = runner.invoke(app, ["--file", str(todo_file), "task", "next"])

        assert result.exit_code == 1

    def test_task_next_json_output(self, tmp_path: Path) -> None:
        """JSON出力モードの確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text(
            "(A) 2024-01-15 重要タスク +project @context due:2024-02-01\n",
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
    """tasq task done コマンドのテスト"""

    def test_task_done_marks_first_incomplete(self, tmp_path: Path) -> None:
        """最初の未完了タスクが完了としてマークされることを確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("タスク1\nタスク2\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        assert "完了:" in result.stdout

        lines = todo_file.read_text(encoding="utf-8").strip().split("\n")
        assert lines[0].startswith("x ")
        assert "タスク1" in lines[0]
        # 2番目は未変更
        assert lines[1] == "タスク2"

    def test_task_done_with_completion_date(self, tmp_path: Path) -> None:
        """完了日が正しい形式で追加されることを確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("タスク\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8").strip()
        # x YYYY-MM-DD 形式で始まる
        import re

        assert re.match(r"x \d{4}-\d{2}-\d{2} タスク", content)

    def test_task_done_preserves_creation_date(self, tmp_path: Path) -> None:
        """作成日が保持されることを確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("2024-01-15 タスク\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8").strip()
        # x 完了日 作成日 タスク の順序
        import re

        match = re.match(r"x (\d{4}-\d{2}-\d{2}) (\d{4}-\d{2}-\d{2}) タスク", content)
        assert match
        assert match.group(2) == "2024-01-15"  # 作成日が保持されている

    def test_task_done_priority_to_key_value(self, tmp_path: Path) -> None:
        """優先度(A)がpri:Aに変換されることを確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("(A) 重要タスク\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8").strip()
        # 先頭に(A)がなく、末尾にpri:Aがある
        assert not content.startswith("(A)")
        assert "pri:A" in content

    def test_task_done_priority_with_creation_date(self, tmp_path: Path) -> None:
        """優先度と作成日の両方がある場合の完了処理を確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("(B) 2024-01-15 タスク\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        content = todo_file.read_text(encoding="utf-8").strip()
        import re

        # x 完了日 作成日 タスク pri:B の順序
        match = re.match(
            r"x (\d{4}-\d{2}-\d{2}) (\d{4}-\d{2}-\d{2}) タスク pri:B", content
        )
        assert match
        assert match.group(2) == "2024-01-15"

    def test_task_done_skips_completed(self, tmp_path: Path) -> None:
        """既に完了したタスクがスキップされることを確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text(
            "x 2024-01-01 済みタスク\nやることタスク\n", encoding="utf-8"
        )

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 0
        lines = todo_file.read_text(encoding="utf-8").strip().split("\n")
        # 1行目は変更なし
        assert lines[0] == "x 2024-01-01 済みタスク"
        # 2行目が完了に
        assert lines[1].startswith("x ")
        assert "やることタスク" in lines[1]

    def test_task_done_no_incomplete_tasks(self, tmp_path: Path) -> None:
        """未完了タスクがない場合のエラー確認"""
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("x 2024-01-01 済みタスク\n", encoding="utf-8")

        result = runner.invoke(app, ["--file", str(todo_file), "task", "done"])

        assert result.exit_code == 1
