"""Tests for the log file tailer and rolling buffer."""

import tempfile
from pathlib import Path

from unreal_editor_mcp.logs.tailer import LogTailer
from unreal_editor_mcp.logs.parser import LogEntry


def _make_log_line(category: str = "LogTemp", severity: str = "Warning", message: str = "test", frame: int = 0) -> str:
    return f"[2024.03.01-12.34.56:789][{frame:3d}]{category}: {severity}: {message}"


class TestLogTailerBuffer:
    def test_ingest_lines(self):
        tailer = LogTailer(log_path=Path("/nonexistent"), auto_start=False)
        lines = [_make_log_line(message=f"msg{i}") for i in range(5)]
        tailer._ingest_lines(lines)
        assert len(tailer.get_recent()) == 5

    def test_rolling_buffer_limit(self):
        tailer = LogTailer(log_path=Path("/nonexistent"), auto_start=False, buffer_size=10)
        lines = [_make_log_line(message=f"msg{i}") for i in range(20)]
        tailer._ingest_lines(lines)
        entries = tailer.get_recent()
        assert len(entries) == 10
        assert entries[-1].message == "msg19"
        assert entries[0].message == "msg10"

    def test_get_recent_with_limit(self):
        tailer = LogTailer(log_path=Path("/nonexistent"), auto_start=False)
        lines = [_make_log_line(message=f"msg{i}") for i in range(20)]
        tailer._ingest_lines(lines)
        entries = tailer.get_recent(count=5)
        assert len(entries) == 5
        assert entries[-1].message == "msg19"

    def test_filter_by_category(self):
        tailer = LogTailer(log_path=Path("/nonexistent"), auto_start=False)
        lines = [
            _make_log_line(category="LogTemp", message="a"),
            _make_log_line(category="LogNet", message="b"),
            _make_log_line(category="LogTemp", message="c"),
        ]
        tailer._ingest_lines(lines)
        entries = tailer.get_recent(category="LogTemp")
        assert len(entries) == 2
        assert all(e.category == "LogTemp" for e in entries)

    def test_filter_by_severity(self):
        tailer = LogTailer(log_path=Path("/nonexistent"), auto_start=False)
        lines = [
            _make_log_line(severity="Warning", message="a"),
            _make_log_line(severity="Error", message="b"),
            _make_log_line(severity="Warning", message="c"),
        ]
        tailer._ingest_lines(lines)
        entries = tailer.get_recent(severity="Error")
        assert len(entries) == 1
        assert entries[0].severity == "Error"

    def test_category_stats(self):
        tailer = LogTailer(log_path=Path("/nonexistent"), auto_start=False)
        lines = [
            _make_log_line(category="LogTemp", severity="Warning"),
            _make_log_line(category="LogTemp", severity="Error"),
            _make_log_line(category="LogNet", severity="Warning"),
        ]
        tailer._ingest_lines(lines)
        stats = tailer.get_category_stats()
        assert stats["LogTemp"]["Warning"] == 1
        assert stats["LogTemp"]["Error"] == 1
        assert stats["LogNet"]["Warning"] == 1

    def test_get_categories(self):
        tailer = LogTailer(log_path=Path("/nonexistent"), auto_start=False)
        lines = [
            _make_log_line(category="LogTemp"),
            _make_log_line(category="LogNet"),
            _make_log_line(category="LogTemp"),
        ]
        tailer._ingest_lines(lines)
        cats = tailer.get_categories()
        assert cats["LogTemp"] == 2
        assert cats["LogNet"] == 1

    def test_search_pattern(self):
        tailer = LogTailer(log_path=Path("/nonexistent"), auto_start=False)
        lines = [
            _make_log_line(message="Loading asset /Game/Maps/Level1"),
            _make_log_line(message="Connection established"),
            _make_log_line(message="Loading asset /Game/Maps/Level2"),
        ]
        tailer._ingest_lines(lines)
        results = tailer.search("Loading asset")
        assert len(results) == 2

    def test_search_regex(self):
        tailer = LogTailer(log_path=Path("/nonexistent"), auto_start=False)
        lines = [
            _make_log_line(message="Error code: 404"),
            _make_log_line(message="Error code: 500"),
            _make_log_line(message="Success"),
        ]
        tailer._ingest_lines(lines)
        results = tailer.search(r"Error code: \d+")
        assert len(results) == 2

    def test_continuation_lines_skipped(self):
        tailer = LogTailer(log_path=Path("/nonexistent"), auto_start=False)
        lines = [
            _make_log_line(message="start"),
            "    continuation line",
            _make_log_line(message="end"),
        ]
        tailer._ingest_lines(lines)
        assert len(tailer.get_recent()) == 2


class TestLogTailerFile:
    def test_read_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as f:
            for i in range(5):
                f.write(_make_log_line(message=f"init{i}") + "\n")
            f.flush()
            log_path = Path(f.name)

        tailer = LogTailer(log_path=log_path, auto_start=False)
        tailer._read_initial()
        entries = tailer.get_recent()
        assert len(entries) == 5
        log_path.unlink()

    def test_tail_new_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as f:
            for i in range(3):
                f.write(_make_log_line(message=f"init{i}") + "\n")
            f.flush()
            log_path = Path(f.name)

        tailer = LogTailer(log_path=log_path, auto_start=False)
        tailer._read_initial()
        assert len(tailer.get_recent()) == 3

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(_make_log_line(message="new1") + "\n")
            f.write(_make_log_line(message="new2") + "\n")

        tailer._read_new_lines()
        entries = tailer.get_recent()
        assert len(entries) == 5
        assert entries[-1].message == "new2"
        log_path.unlink()
