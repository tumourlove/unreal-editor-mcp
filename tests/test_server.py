"""Tests for the MCP server tool definitions."""

from pathlib import Path
from unittest.mock import patch

import pytest


def _make_log_line(category="LogTemp", severity="Warning", message="test", frame=0):
    return f"[2024.03.01-12.34.56:789][{frame:3d}]{category}: {severity}: {message}"


@pytest.fixture
def server_env(tmp_path):
    """Set up a mock UE project path with a log file."""
    log_dir = tmp_path / "Saved" / "Logs"
    log_dir.mkdir(parents=True)
    log_file = log_dir / "TestProject.log"
    lines = [
        _make_log_line(category="LogInit", severity="Display", message="Engine initialized"),
        _make_log_line(category="LogTemp", severity="Warning", message="Test warning"),
        _make_log_line(category="LogTemp", severity="Error", message="Test error"),
        _make_log_line(category="LogNet", severity="Warning", message="Connection lost"),
        _make_log_line(category="LogLiveCoding", severity="Display", message="Live coding succeeded."),
    ]
    log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (tmp_path / "TestProject.uproject").write_text("{}", encoding="utf-8")

    with patch("unreal_editor_mcp.config.UE_PROJECT_PATH", str(tmp_path)):
        with patch("unreal_editor_mcp.config._detect_project_name", return_value="TestProject"):
            yield tmp_path


class TestServerTools:
    def test_get_recent_logs(self, server_env):
        from unreal_editor_mcp.server import _get_tailer, _reset_state
        _reset_state()
        tailer = _get_tailer(server_env)
        entries = tailer.get_recent()
        assert len(entries) >= 3

    def test_get_recent_logs_filtered(self, server_env):
        from unreal_editor_mcp.server import _get_tailer, _reset_state
        _reset_state()
        tailer = _get_tailer(server_env)
        entries = tailer.get_recent(category="LogTemp")
        assert all(e.category == "LogTemp" for e in entries)

    def test_search_logs(self, server_env):
        from unreal_editor_mcp.server import _get_tailer, _reset_state
        _reset_state()
        tailer = _get_tailer(server_env)
        results = tailer.search("Connection")
        assert len(results) >= 1

    def test_get_log_categories(self, server_env):
        from unreal_editor_mcp.server import _get_tailer, _reset_state
        _reset_state()
        tailer = _get_tailer(server_env)
        cats = tailer.get_categories()
        assert "LogTemp" in cats
        assert "LogInit" in cats

    def test_get_log_stats(self, server_env):
        from unreal_editor_mcp.server import _get_tailer, _reset_state
        _reset_state()
        tailer = _get_tailer(server_env)
        stats = tailer.get_category_stats()
        assert "LogTemp" in stats
        assert stats["LogTemp"]["Warning"] >= 1
