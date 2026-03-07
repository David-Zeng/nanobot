"""Tests for tools.disabled feature — verifies disabled tools are excluded from the registry."""

from pathlib import Path
from unittest.mock import MagicMock

from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.config.schema import ToolsConfig


def _make_loop(disabled: list[str] | None = None, tmp_path: Path | None = None) -> AgentLoop:
    """Build a minimal AgentLoop without a real LLM provider."""
    bus = MessageBus()
    provider = MagicMock()
    provider.get_default_model.return_value = "test/model"
    ws = tmp_path or Path("/tmp/test_ws_disabled")
    return AgentLoop(
        bus=bus,
        provider=provider,
        workspace=ws,
        disabled_tools=disabled or [],
    )


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

def test_disabled_field_defaults_to_empty():
    assert ToolsConfig().disabled == []


def test_disabled_accepts_list():
    cfg = ToolsConfig(disabled=["write_file", "exec"])
    assert cfg.disabled == ["write_file", "exec"]


# ---------------------------------------------------------------------------
# Registry tests — use tmp_path fixture for a real workspace path
# ---------------------------------------------------------------------------

def test_write_file_not_registered_when_disabled(tmp_path: Path):
    loop = _make_loop(disabled=["write_file"], tmp_path=tmp_path)
    assert "write_file" not in loop.tools


def test_exec_not_registered_when_disabled(tmp_path: Path):
    loop = _make_loop(disabled=["exec"], tmp_path=tmp_path)
    assert "exec" not in loop.tools


def test_non_disabled_tools_still_present(tmp_path: Path):
    loop = _make_loop(disabled=["write_file"], tmp_path=tmp_path)
    assert "read_file" in loop.tools


def test_definitions_exclude_disabled(tmp_path: Path):
    loop = _make_loop(disabled=["write_file"], tmp_path=tmp_path)
    names = [d["function"]["name"] for d in loop.tools.get_definitions()]
    assert "write_file" not in names


def test_empty_disabled_all_tools_present(tmp_path: Path):
    loop = _make_loop(disabled=[], tmp_path=tmp_path)
    for name in ("read_file", "write_file", "exec", "message"):
        assert name in loop.tools


def test_unknown_disabled_name_ignored(tmp_path: Path):
    loop = _make_loop(disabled=["nonexistent_tool"], tmp_path=tmp_path)
    assert "read_file" in loop.tools


def test_customer_agent_tool_set(tmp_path: Path):
    """Simulate the beauty-salon customer agent's tool restrictions."""
    disabled = ["write_file", "edit_file", "exec", "cron", "spawn"]
    loop = _make_loop(disabled=disabled, tmp_path=tmp_path)
    assert "write_file" not in loop.tools
    assert "edit_file" not in loop.tools
    assert "exec" not in loop.tools
    assert "cron" not in loop.tools
    assert "spawn" not in loop.tools
    assert "read_file" in loop.tools
    assert "message" in loop.tools


def test_web_search_disabled(tmp_path: Path):
    loop = _make_loop(disabled=["web_search"], tmp_path=tmp_path)
    assert "web_search" not in loop.tools
    assert "web_fetch" in loop.tools


def test_message_disabled(tmp_path: Path):
    loop = _make_loop(disabled=["message"], tmp_path=tmp_path)
    assert "message" not in loop.tools
    assert "read_file" in loop.tools
