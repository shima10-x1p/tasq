"""tasq CLI module.

Typer-based CLI application entry point.
Subcommand groups: task, config, self
"""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from tasq import __version__
from tasq.config import Config
from tasq.storage import TodoFile
from tasq.todotxt import Task

# Main application
app = typer.Typer(
    name="tasq",
    help="A todo.txt-compatible FIFO queue task management tool",
    no_args_is_help=True,
)

# Subcommand groups
task_app = typer.Typer(
    name="task",
    help="Task operations",
    no_args_is_help=True,
)

config_app = typer.Typer(
    name="config",
    help="Configuration commands",
    no_args_is_help=True,
)

self_app = typer.Typer(
    name="self",
    help="Tool information",
    no_args_is_help=True,
)

# Add subcommand groups to main app
app.add_typer(task_app, name="task")
app.add_typer(config_app, name="config")
app.add_typer(self_app, name="self")


class GlobalContext:
    """Holds global options for commands."""

    def __init__(self) -> None:
        self.file: str | None = None
        self.json_output: bool = False
        self.verbose: bool = False


# Global context instance
_context = GlobalContext()


def version_callback(value: bool) -> None:
    """Callback for --version option."""
    if value:
        typer.echo(f"tasq version {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    file: Annotated[
        Optional[str],
        typer.Option(
            "--file",
            "-f",
            help="Specify the todo.txt file path",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Output in JSON format",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show verbose output",
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """tasq - A todo.txt-compatible FIFO queue task management tool."""
    _context.file = file
    _context.json_output = json_output
    _context.verbose = verbose


# ===== task subcommands =====


@task_app.command("in")
def task_in(
    text: Annotated[
        str,
        typer.Argument(help="Task text to add"),
    ],
) -> None:
    """Add a new task to the end of the queue."""
    config = Config(_context.file)
    todo_path = config.todo_file_path

    if _context.verbose:
        typer.echo(f"[verbose] todo.txt: {todo_path} (from {config.source})")

    # Create new task with creation date
    task = Task.create(text, add_creation_date=True)

    # Append to file
    todo_file = TodoFile(todo_path)
    todo_file.append_task(task)

    task_line = task.to_line()
    if _context.json_output:
        result = {"added": task_line, "file": str(todo_path)}
        typer.echo(json.dumps(result, ensure_ascii=False))
    else:
        typer.echo(f"Added: {task_line}")


@task_app.command("next")
def task_next() -> None:
    """Show the next incomplete task at the front of the queue."""
    config = Config(_context.file)
    todo_path = config.todo_file_path

    if _context.verbose:
        typer.echo(f"[verbose] todo.txt: {todo_path} (from {config.source})")

    todo_file = TodoFile(todo_path)

    # File doesn't exist
    if not todo_file.exists():
        if _context.json_output:
            typer.echo(json.dumps({"error": "No tasks found", "file": str(todo_path)}))
        else:
            typer.echo("No tasks found (file does not exist)")
        raise typer.Exit(code=1)

    # Find first incomplete task
    result = todo_file.get_next_incomplete()
    if result is None:
        if _context.json_output:
            typer.echo(
                json.dumps({"error": "No incomplete tasks", "file": str(todo_path)})
            )
        else:
            typer.echo("No incomplete tasks")
        raise typer.Exit(code=1)

    index, task = result

    if _context.json_output:
        output = {"index": index, **task.to_dict()}
        typer.echo(json.dumps(output, ensure_ascii=False))
    else:
        typer.echo(task.text)


@task_app.command("done")
def task_done() -> None:
    """Mark the next incomplete task as complete."""
    config = Config(_context.file)
    todo_path = config.todo_file_path

    if _context.verbose:
        typer.echo(f"[verbose] todo.txt: {todo_path} (from {config.source})")

    todo_file = TodoFile(todo_path)

    # File doesn't exist
    if not todo_file.exists():
        typer.echo("No tasks found (file does not exist)", err=True)
        raise typer.Exit(code=1)

    # Find and complete first incomplete task
    result = todo_file.get_next_incomplete()
    if result is None:
        typer.echo("No incomplete tasks", err=True)
        raise typer.Exit(code=1)

    index, original_task = result
    completed_task = todo_file.complete_task(index)

    if _context.json_output:
        output = {
            "completed": completed_task.to_line(),
            "original": original_task.text,
            "index": index,
        }
        typer.echo(json.dumps(output, ensure_ascii=False))
    else:
        typer.echo(f"Done: {completed_task.to_line()}")


@task_app.command("list")
def task_list(
    show_all: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help="Include completed tasks",
        ),
    ] = False,
    completed: Annotated[
        bool,
        typer.Option(
            "--completed",
            "-c",
            help="Show only completed tasks",
        ),
    ] = False,
    limit: Annotated[
        Optional[int],
        typer.Option(
            "--limit",
            "-n",
            help="Maximum number of tasks to display",
        ),
    ] = None,
) -> None:
    """List tasks from todo.txt without modifying the file.

    By default, shows only incomplete tasks in file order (queue order).
    Tasks are never sorted; order reflects the queue.
    """
    config = Config(_context.file)
    todo_path = config.todo_file_path

    if _context.verbose:
        typer.echo(f"[verbose] todo.txt: {todo_path} (from {config.source})")

    todo_file = TodoFile(todo_path)

    # Get all tasks with indices
    all_tasks = todo_file.get_all_tasks_with_indices()

    # Filter tasks based on options
    filtered_tasks = []
    for index, raw, task in all_tasks:
        if completed:
            # --completed: only completed tasks
            if task.completed:
                filtered_tasks.append((index, raw, task))
        elif show_all:
            # --all: all tasks
            filtered_tasks.append((index, raw, task))
        else:
            # Default: only incomplete tasks
            if not task.completed:
                filtered_tasks.append((index, raw, task))

    # Apply limit
    if limit is not None and limit > 0:
        filtered_tasks = filtered_tasks[:limit]

    # Output
    if _context.json_output:
        result = []
        for index, raw, task in filtered_tasks:
            result.append(
                {
                    "index": index,
                    "raw": raw,
                    "completed": task.completed,
                    "completion_date": task.completion_date,
                    "creation_date": task.creation_date,
                    "priority": task.priority,
                    "projects": task.projects,
                    "contexts": task.contexts,
                    "key_values": task.key_values,
                }
            )
        typer.echo(json.dumps(result, ensure_ascii=False))
    else:
        for index, raw, task in filtered_tasks:
            typer.echo(f"[{index}] {raw}")


@task_app.command("skip")
def task_skip() -> None:
    """Skip the first incomplete task by moving it to the end of the queue.

    Moves the first incomplete task to after all other incomplete tasks,
    but before any completed tasks. This is equivalent to dequeue+enqueue
    in a FIFO queue.

    The task content is preserved exactly; no timestamps or tags are added.
    """
    config = Config(_context.file)
    todo_path = config.todo_file_path

    if _context.verbose:
        typer.echo(f"[verbose] todo.txt: {todo_path} (from {config.source})")

    todo_file = TodoFile(todo_path)

    # Check if file exists
    if not todo_file.exists():
        if _context.json_output:
            typer.echo(
                json.dumps(
                    {
                        "moved": False,
                        "error": "No tasks found (file does not exist)",
                    }
                )
            )
        else:
            typer.echo("No tasks found (file does not exist)", err=True)
        raise typer.Exit(code=1)

    # Attempt to skip
    result = todo_file.skip_first_incomplete()

    if result is None:
        if _context.json_output:
            typer.echo(
                json.dumps(
                    {
                        "moved": False,
                        "error": "No incomplete tasks to skip",
                    }
                )
            )
        else:
            typer.echo("No incomplete tasks to skip", err=True)
        raise typer.Exit(code=1)

    from_idx, to_idx, raw = result

    if _context.json_output:
        typer.echo(
            json.dumps(
                {
                    "moved": True,
                    "from_index": from_idx,
                    "to_index": to_idx,
                    "raw": raw,
                },
                ensure_ascii=False,
            )
        )
    else:
        typer.echo(f"Skipped: [{from_idx}] → [{to_idx}] {raw}")


# ===== config subcommands =====


@config_app.command("path")
def config_path() -> None:
    """Show the resolved todo.txt path."""
    config = Config(_context.file)

    if _context.json_output:
        result = {
            "path": str(config.todo_file_path),
            "source": config.source,
            "source_description": config.source_description,
            "exists": config.todo_file_path.exists(),
        }
        typer.echo(json.dumps(result, ensure_ascii=False))
    else:
        typer.echo(f"Path: {config.todo_file_path}")
        typer.echo(f"Source: {config.source_description}")
        exists_str = "Yes" if config.todo_file_path.exists() else "No"
        typer.echo(f"Exists: {exists_str}")


@config_app.command("set-path")
def config_set_path(
    path: Annotated[
        str,
        typer.Argument(help="Path to set as default todo.txt"),
    ],
) -> None:
    """Save the default todo.txt path to the config file."""
    abs_path = Path(path).resolve()

    Config.save(str(abs_path))
    config_file = Config.get_config_path()

    if _context.json_output:
        result = {
            "path": str(abs_path),
            "config_file": str(config_file),
        }
        typer.echo(json.dumps(result, ensure_ascii=False))
    else:
        typer.echo(f"Configuration saved: {abs_path}")
        typer.echo(f"Config file: {config_file}")


# ===== self subcommands =====


@self_app.command("version")
def self_version() -> None:
    """Show version information."""
    if _context.json_output:
        result = {"version": __version__}
        typer.echo(json.dumps(result, ensure_ascii=False))
    else:
        typer.echo(f"tasq version {__version__}")


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
