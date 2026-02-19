# Agent Instructions for nanobot

This repository contains the source code for **nanobot**, an ultra-lightweight personal AI assistant.

## 1. Environment & Build

- **Language**: Python 3.11+
- **Build System**: `hatchling` (configured in `pyproject.toml`)
- **Package Manager**: `pip` / `uv`

### Common Commands

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_file.py

# Run a specific test function
pytest tests/test_file.py::test_function_name

# Linting (Ruff)
ruff check .

# Formatting (Ruff)
ruff format .
```

## 2. Code Style & Conventions

### General
- **Formatting**: Follows `ruff` defaults (similar to Black). Line length is **100** characters.
- **Indentation**: 4 spaces.
- **Quotes**: Double quotes `"` for strings.
- **Async/Await**: The core is built on `asyncio`. Use `async/await` for I/O operations.

### Type Hinting
- **Strict Typing**: All function signatures must have type hints.
- **Collections**: Use `list`, `dict`, `tuple` (generic aliases) or `typing.List`, `typing.Dict` etc.
- **Optional**: Use `str | None` (Python 3.10+) or `Optional[str]`.

### Imports
Organize imports in three blocks, separated by a blank line:
1.  **Standard Library**: `import os`, `import asyncio`, `from pathlib import Path`
2.  **Third-Party**: `import typer`, `from loguru import logger`, `from rich.console import Console`
3.  **Local (nanobot)**: `from nanobot.config import ...`, `from nanobot.agent import ...`

### Naming
- **Variables/Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private**: `_leading_underscore` for internal methods/variables.

### Error Handling & Logging
- **Logging**: Use `loguru`.
  ```python
  from loguru import logger
  logger.info("Message")
  logger.error(f"Error: {e}")
  ```
- **Exceptions**: Use specific exception types. Avoid bare `except:`.

### Documentation
- **Docstrings**: Use triple double quotes `"""`. Google style or simple description.
  - Module level docstring at the top of the file.
  - Function/Class docstrings explaining purpose and args.

## 3. Architecture Overview

- **Entry Point**: `nanobot/cli/commands.py` (`nanobot` command).
- **Core Loop**: `nanobot/agent/loop.py` (`AgentLoop` class).
- **Configuration**: `nanobot/config/` (Pydantic models).
- **Providers**: `nanobot/providers/` (LLM integrations via `litellm`).
- **Tools**: `nanobot/agent/tools/` (Agent capabilities).

## 4. Testing
- Use `pytest` for testing.
- Tests are located in `tests/`.
- Use `pytest-asyncio` for async tests.
