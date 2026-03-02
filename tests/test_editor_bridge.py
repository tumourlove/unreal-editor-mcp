"""Tests for the editor bridge (UE remote execution client)."""

import json

from unreal_editor_mcp.editor_bridge import (
    EditorBridge,
    EditorNotRunning,
    _build_message,
    _parse_message,
    PROTOCOL_VERSION,
    PROTOCOL_MAGIC,
)


class TestMessageFormat:
    def test_build_message(self):
        msg = _build_message("ping", "node-1")
        parsed = json.loads(msg)
        assert parsed["version"] == PROTOCOL_VERSION
        assert parsed["magic"] == PROTOCOL_MAGIC
        assert parsed["type"] == "ping"
        assert parsed["source"] == "node-1"
        assert "dest" not in parsed

    def test_build_message_with_dest_and_data(self):
        msg = _build_message("command", "node-1", dest="node-2", data={"command": "print(1)"})
        parsed = json.loads(msg)
        assert parsed["dest"] == "node-2"
        assert parsed["data"]["command"] == "print(1)"

    def test_parse_message_valid(self):
        raw = json.dumps({
            "version": PROTOCOL_VERSION,
            "magic": PROTOCOL_MAGIC,
            "type": "pong",
            "source": "editor-1",
            "data": {"user": "test"},
        })
        result = _parse_message(raw)
        assert result is not None
        assert result["type"] == "pong"
        assert result["source"] == "editor-1"

    def test_parse_message_wrong_magic(self):
        raw = json.dumps({
            "version": PROTOCOL_VERSION,
            "magic": "wrong",
            "type": "pong",
            "source": "editor-1",
        })
        result = _parse_message(raw)
        assert result is None

    def test_parse_message_wrong_version(self):
        raw = json.dumps({
            "version": 999,
            "magic": PROTOCOL_MAGIC,
            "type": "pong",
            "source": "editor-1",
        })
        result = _parse_message(raw)
        assert result is None


class TestEditorBridgeDetection:
    def test_is_editor_running_returns_bool(self):
        bridge = EditorBridge(auto_connect=False)
        result = bridge.is_editor_running()
        assert isinstance(result, bool)

    def test_bridge_not_connected_initially(self):
        bridge = EditorBridge(auto_connect=False)
        assert not bridge.is_connected()
