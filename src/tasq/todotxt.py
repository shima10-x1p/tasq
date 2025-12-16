"""todo.txt format parsing and manipulation module.

Follows the official todo.txt format rules:
- Completed task: starts with `x YYYY-MM-DD`
- Priority: `(A)` format at the beginning of the line
- Creation date: YYYY-MM-DD format after priority or at the beginning
- Projects: `+project` format
- Contexts: `@context` format
- Key-values: `key:value` format
"""

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Self


# Regular expression patterns for parsing todo.txt format
COMPLETED_PATTERN = re.compile(r"^x\s+(\d{4}-\d{2}-\d{2})\s+")
PRIORITY_PATTERN = re.compile(r"^\(([A-Z])\)\s+")
DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+")
PROJECT_PATTERN = re.compile(r"\+(\S+)")
CONTEXT_PATTERN = re.compile(r"@(\S+)")
# Key-value pattern: excludes URLs by not matching ://
KEY_VALUE_PATTERN = re.compile(r"(?<!\S)([a-zA-Z_][a-zA-Z0-9_]*):([^\s]+)(?!\S*://)")


@dataclass
class Task:
    """Represents a single todo.txt task line.

    Attributes:
        text: The main task description text.
        completed: Whether the task is marked as complete.
        completion_date: Date when the task was completed (YYYY-MM-DD).
        creation_date: Date when the task was created (YYYY-MM-DD).
        priority: Task priority (A-Z).
        projects: List of project tags (+project).
        contexts: List of context tags (@context).
        key_values: Dictionary of key:value metadata.
    """

    text: str
    completed: bool = False
    completion_date: str | None = None
    creation_date: str | None = None
    priority: str | None = None
    projects: list[str] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)
    key_values: dict[str, str] = field(default_factory=dict)

    @classmethod
    def parse(cls, line: str) -> Self:
        """Parse a todo.txt line into a Task object.

        Args:
            line: A single line from a todo.txt file.

        Returns:
            A Task object with parsed fields.
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

        # Check for completion marker
        completed_match = COMPLETED_PATTERN.match(remaining)
        if completed_match:
            result["completed"] = True
            result["completion_date"] = completed_match.group(1)
            remaining = remaining[completed_match.end() :]

        # Check for priority
        priority_match = PRIORITY_PATTERN.match(remaining)
        if priority_match:
            result["priority"] = priority_match.group(1)
            remaining = remaining[priority_match.end() :]

        # Check for creation date
        date_match = DATE_PATTERN.match(remaining)
        if date_match:
            result["creation_date"] = date_match.group(1)
            remaining = remaining[date_match.end() :]

        # Extract projects
        result["projects"] = PROJECT_PATTERN.findall(remaining)

        # Extract contexts
        result["contexts"] = CONTEXT_PATTERN.findall(remaining)

        # Extract key-values
        for match in KEY_VALUE_PATTERN.finditer(remaining):
            key, value = match.groups()
            result["key_values"][key] = value

        # Store the remaining text as the task description
        result["text"] = line.strip()

        return cls(**result)

    @classmethod
    def create(cls, text: str, add_creation_date: bool = True) -> Self:
        """Create a new task with optional creation date.

        Args:
            text: The task description (newlines will be stripped).
            add_creation_date: Whether to add today's date as creation date.

        Returns:
            A new Task object.
        """
        # Remove newlines to ensure single line
        clean_text = text.replace("\n", " ").replace("\r", " ").strip()

        # Check if text starts with priority
        priority = None
        remaining = clean_text
        priority_match = PRIORITY_PATTERN.match(clean_text)
        if priority_match:
            priority = priority_match.group(1)
            remaining = clean_text[priority_match.end() :]

        creation_date = date.today().isoformat() if add_creation_date else None

        # Extract projects, contexts, and key-values from the text
        projects = PROJECT_PATTERN.findall(remaining)
        contexts = CONTEXT_PATTERN.findall(remaining)
        key_values = {}
        for match in KEY_VALUE_PATTERN.finditer(remaining):
            key, value = match.groups()
            key_values[key] = value

        return cls(
            text=remaining,
            completed=False,
            creation_date=creation_date,
            priority=priority,
            projects=projects,
            contexts=contexts,
            key_values=key_values,
        )

    def mark_complete(self) -> Self:
        """Mark the task as complete following todo.txt rules.

        - Adds `x ` prefix with completion date.
        - Preserves creation date after completion date.
        - Converts priority (A) to pri:A key-value.

        Returns:
            A new Task object marked as complete.
        """
        if self.completed:
            return self  # Already complete

        new_key_values = dict(self.key_values)

        # Convert priority to pri:X key-value
        if self.priority:
            new_key_values["pri"] = self.priority

        return Task(
            text=self.text,
            completed=True,
            completion_date=date.today().isoformat(),
            creation_date=self.creation_date,
            priority=None,  # Priority is removed on completion
            projects=self.projects,
            contexts=self.contexts,
            key_values=new_key_values,
        )

    def to_line(self) -> str:
        """Convert the Task object back to a todo.txt line string.

        Returns:
            A properly formatted todo.txt line.
        """
        parts = []

        # Completion marker
        if self.completed and self.completion_date:
            parts.append(f"x {self.completion_date}")

        # Creation date (for completed tasks, appears after completion date)
        if self.creation_date:
            parts.append(self.creation_date)

        # Priority (only for incomplete tasks)
        if self.priority and not self.completed:
            # Priority comes before creation date
            if self.creation_date and parts:
                parts.insert(0 if not self.completed else 1, f"({self.priority})")
            else:
                parts.insert(0, f"({self.priority})")

        # Task text (extract just the description without metadata)
        text_to_add = self.text

        # For new tasks created via create(), use the stored text
        # For parsed tasks, the text already contains the full line
        if self._is_newly_created():
            parts.append(text_to_add)
            # Add pri:X if task was completed and had priority
            if self.completed and "pri" in self.key_values:
                parts.append(f"pri:{self.key_values['pri']}")
        else:
            # For parsed tasks that were modified, reconstruct the line
            if self.completed and self.completion_date:
                # Extract just the task description from the original text
                remaining = self._extract_description()
                parts.append(remaining)
                if (
                    "pri" in self.key_values
                    and f"pri:{self.key_values['pri']}" not in remaining
                ):
                    parts.append(f"pri:{self.key_values['pri']}")
            else:
                parts.append(text_to_add)

        return " ".join(parts)

    def _is_newly_created(self) -> bool:
        """Check if this task was newly created (not parsed from file)."""
        # Newly created tasks have text that doesn't contain dates/completion markers
        return not (
            self.text.startswith("x ")
            or PRIORITY_PATTERN.match(self.text)
            or DATE_PATTERN.match(self.text)
        )

    def _extract_description(self) -> str:
        """Extract the task description from the full line text."""
        remaining = self.text

        # Remove completion marker
        completed_match = COMPLETED_PATTERN.match(remaining)
        if completed_match:
            remaining = remaining[completed_match.end() :]

        # Remove priority
        priority_match = PRIORITY_PATTERN.match(remaining)
        if priority_match:
            remaining = remaining[priority_match.end() :]

        # Remove creation date
        date_match = DATE_PATTERN.match(remaining)
        if date_match:
            remaining = remaining[date_match.end() :]

        return remaining.strip()

    def to_dict(self) -> dict:
        """Convert the Task to a dictionary for JSON serialization.

        Returns:
            A dictionary representation of the task.
        """
        return {
            "text": self.text,
            "completed": self.completed,
            "completion_date": self.completion_date,
            "creation_date": self.creation_date,
            "priority": self.priority,
            "projects": self.projects,
            "contexts": self.contexts,
            "key_values": self.key_values,
        }


# Backward compatibility functions
def is_completed(line: str) -> bool:
    """Check if a task line is marked as complete.

    Args:
        line: A todo.txt line.

    Returns:
        True if the task is complete.
    """
    return line.strip().startswith("x ")


def parse_task(line: str) -> dict:
    """Parse a task line into a dictionary.

    Args:
        line: A todo.txt line.

    Returns:
        A dictionary with parsed fields.
    """
    task = Task.parse(line)
    return task.to_dict()


def format_new_task(text: str, add_creation_date: bool = True) -> str:
    """Format a new task line with optional creation date.

    Args:
        text: The task description.
        add_creation_date: Whether to add creation date.

    Returns:
        A formatted todo.txt line.
    """
    task = Task.create(text, add_creation_date)
    return task.to_line()


def mark_complete(line: str) -> str:
    """Mark a task line as complete.

    Args:
        line: The original task line.

    Returns:
        The completed task line.
    """
    task = Task.parse(line)
    completed_task = task.mark_complete()
    return completed_task.to_line()
