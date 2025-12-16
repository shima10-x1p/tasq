# tasq

**A todo.txt-compatible task tool that treats a human like a tube (FIFO queue)**

tasq is a task management tool that treats humans as a "tube" (FIFO queue). It eliminates priority management UX for a simpler workflow: first in, first out.

## Features

- 📋 **todo.txt compatible** - Works with the existing todo.txt ecosystem
- 🔄 **FIFO queue** - Process tasks in order, from first to last
- ⚡ **Simple workflow** - `in` (add) → `next` (peek) → `done` (complete)
- 🔧 **Flexible configuration** - CLI, environment variable, or config file

## Installation

### Install with uv tools (recommended)

```bash
# Try it out (temporary)
uvx --from git+https://github.com/shima10-x1p/tasq tasq --help

# Install permanently
uv tool install git+https://github.com/shima10-x1p/tasq

# If PATH is not set
uv tool update-shell
```

### Install with pip

```bash
pip install git+https://github.com/shima10-x1p/tasq
```

## Usage

### Basic Workflow

```bash
# Add tasks (appends to end of queue)
tasq task in "Write report"
tasq task in "Reply to emails"
tasq task in "(A) Make urgent call"

# View next task (peek at front of queue)
tasq task next
# Output: 2024-12-16 Write report

# Complete task (marks front of queue as done)
tasq task done
# Output: Done: x 2024-12-16 2024-12-16 Write report

# View next task
tasq task next
# Output: 2024-12-16 Reply to emails
```

### Configuration

```bash
# Show current todo.txt path
tasq config path

# Set default todo.txt path
tasq config set-path ~/Documents/todo.txt

# Set via environment variable
export TASQ_FILE=~/my-todo.txt

# Override temporarily via CLI
tasq --file ./project-todo.txt task next
```

### Configuration Priority

1. CLI option (`--file PATH`)
2. Environment variable (`TASQ_FILE`)
3. Config file (`~/.config/tasq/config.toml`)
4. Default (`./todo.txt` or `~/todo.txt`)

### JSON Output

```bash
# Machine-readable JSON output
tasq --json task next
# Output: {"index": 0, "text": "2024-12-16 Task", "completed": false, ...}
```

## Commands

| Command | Description |
|---------|-------------|
| `tasq task in TEXT` | Add a new task to the end of the queue |
| `tasq task next` | Show the next incomplete task |
| `tasq task done` | Mark the next incomplete task as complete |
| `tasq config path` | Show the resolved todo.txt path |
| `tasq config set-path PATH` | Set the default todo.txt path |
| `tasq self version` | Show version |

## Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--file PATH` | `-f` | Specify todo.txt file path |
| `--json` | `-j` | Output in JSON format |
| `--verbose` | `-v` | Show verbose output |
| `--version` | `-V` | Show version and exit |

## todo.txt Compatibility

tasq follows the [todo.txt format](https://github.com/todotxt/todo.txt):

- **Priority**: `(A) Task` - A-Z priority levels
- **Creation date**: `YYYY-MM-DD Task` - ISO 8601 format
- **Completion**: `x YYYY-MM-DD Task` - With completion date
- **Projects**: `+project` - Project tags
- **Contexts**: `@context` - Context tags
- **Metadata**: `key:value` - Custom metadata

### Completion Behavior

- Adds `x ` prefix with completion date
- Preserves creation date after completion date
- Converts priority `(A)` to `pri:A` metadata

## Development

```bash
# Clone repository
git clone https://github.com/shima10-x1p/tasq.git
cd tasq

# Setup development environment
uv sync --dev

# Run tests
uv run pytest tests/ -v

# Run locally
uv run tasq --help
```
