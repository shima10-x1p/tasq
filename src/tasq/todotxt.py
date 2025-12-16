"""todo.txt形式のパースと操作モジュール

todo.txt形式のルール:
- 完了タスク: `x YYYY-MM-DD` で始まる
- 優先度: `(A)` のような形式で行頭に配置
- 作成日: 優先度の後または行頭にYYYY-MM-DD形式で配置
- プロジェクト: `+project` 形式
- コンテキスト: `@context` 形式
- キー値: `key:value` 形式
"""

import re
from datetime import date


# 完了タスクの正規表現: x YYYY-MM-DD で始まる
COMPLETED_PATTERN = re.compile(r"^x\s+(\d{4}-\d{2}-\d{2})\s+")

# 優先度の正規表現: (A) のような形式
PRIORITY_PATTERN = re.compile(r"^\(([A-Z])\)\s+")

# 日付の正規表現: YYYY-MM-DD
DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+")

# プロジェクトの正規表現: +project
PROJECT_PATTERN = re.compile(r"\+(\S+)")

# コンテキストの正規表現: @context
CONTEXT_PATTERN = re.compile(r"@(\S+)")

# キー値の正規表現: key:value（URLは除外するため、://を含まないもの）
KEY_VALUE_PATTERN = re.compile(r"(?<!\S)([a-zA-Z_][a-zA-Z0-9_]*):([^\s]+)(?!\S*://)")


def is_completed(line: str) -> bool:
    """タスク行が完了済みかどうかを判定する

    Args:
        line: タスク行

    Returns:
        完了済みならTrue
    """
    return line.strip().startswith("x ")


def parse_task(line: str) -> dict:
    """タスク行をパースする

    Args:
        line: タスク行

    Returns:
        パース結果の辞書:
        - completed: 完了フラグ
        - completion_date: 完了日（なければNone）
        - creation_date: 作成日（なければNone）
        - priority: 優先度（なければNone）
        - text: タスクテキスト
        - projects: プロジェクトリスト
        - contexts: コンテキストリスト
        - key_values: キー値の辞書
    """
    result = {
        "completed": False,
        "completion_date": None,
        "creation_date": None,
        "priority": None,
        "text": line.strip(),
        "projects": [],
        "contexts": [],
        "key_values": {},
    }

    remaining = line.strip()

    # 完了チェック
    completed_match = COMPLETED_PATTERN.match(remaining)
    if completed_match:
        result["completed"] = True
        result["completion_date"] = completed_match.group(1)
        remaining = remaining[completed_match.end() :]

    # 優先度チェック（完了タスクでも残っている場合がある）
    priority_match = PRIORITY_PATTERN.match(remaining)
    if priority_match:
        result["priority"] = priority_match.group(1)
        remaining = remaining[priority_match.end() :]

    # 作成日チェック
    date_match = DATE_PATTERN.match(remaining)
    if date_match:
        result["creation_date"] = date_match.group(1)
        remaining = remaining[date_match.end() :]

    # プロジェクトを抽出
    result["projects"] = PROJECT_PATTERN.findall(remaining)

    # コンテキストを抽出
    result["contexts"] = CONTEXT_PATTERN.findall(remaining)

    # キー値を抽出
    for match in KEY_VALUE_PATTERN.finditer(remaining):
        key, value = match.groups()
        result["key_values"][key] = value

    return result


def format_new_task(text: str, add_creation_date: bool = True) -> str:
    """新規タスク行を生成する

    Args:
        text: タスクテキスト（改行は除去される）
        add_creation_date: 作成日を付与するかどうか

    Returns:
        フォーマットされたタスク行
    """
    # 改行を除去して単一行にする
    clean_text = text.replace("\n", " ").replace("\r", " ").strip()

    if not add_creation_date:
        return clean_text

    today = date.today().isoformat()

    # 優先度が先頭にある場合は、優先度の後に日付を挿入
    priority_match = PRIORITY_PATTERN.match(clean_text)
    if priority_match:
        priority = priority_match.group(0)
        rest = clean_text[priority_match.end() :]
        return f"{priority}{today} {rest}"

    return f"{today} {clean_text}"


def mark_complete(line: str) -> str:
    """タスク行を完了としてマークする

    todo.txt完了ルール:
    - `x ` + 完了日を先頭に追加
    - 作成日がある場合は完了日の後に配置
    - 優先度(A)がある場合は削除し、pri:Aをタスク末尾に追加

    Args:
        line: 元のタスク行

    Returns:
        完了マーク済みのタスク行
    """
    if is_completed(line):
        return line  # 既に完了している場合はそのまま返す

    remaining = line.strip()
    today = date.today().isoformat()
    priority_tag = ""
    creation_date = ""

    # 優先度を抽出して削除
    priority_match = PRIORITY_PATTERN.match(remaining)
    if priority_match:
        priority = priority_match.group(1)
        priority_tag = f" pri:{priority}"
        remaining = remaining[priority_match.end() :]

    # 作成日を抽出
    date_match = DATE_PATTERN.match(remaining)
    if date_match:
        creation_date = date_match.group(1) + " "
        remaining = remaining[date_match.end() :]

    # 完了形式で組み立て: x 完了日 [作成日] タスク内容 [pri:X]
    result = f"x {today} {creation_date}{remaining}{priority_tag}"

    return result
