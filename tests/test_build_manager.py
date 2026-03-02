"""Tests for the build manager."""

import time
from unittest.mock import MagicMock

from unreal_editor_mcp.build.manager import BuildManager, BuildRecord, BuildStatus
from unreal_editor_mcp.logs.parser import LogEntry


def _make_log_entry(category: str, severity: str, message: str, timestamp: str = "2024.03.01-12.34.56:789") -> LogEntry:
    return LogEntry(
        timestamp=timestamp, frame=0, category=category,
        severity=severity, message=message, raw=f"[{timestamp}][  0]{category}: {severity}: {message}",
    )


class TestBuildRecord:
    def test_initial_state(self):
        record = BuildRecord(build_id="build-1", build_type="live_coding")
        assert record.status == BuildStatus.BUILDING
        assert record.errors == []
        assert record.raw_output == []
        assert record.end_time is None

    def test_to_dict(self):
        record = BuildRecord(build_id="build-1", build_type="live_coding")
        d = record.to_dict()
        assert d["id"] == "build-1"
        assert d["type"] == "live_coding"
        assert d["status"] == "building"


class TestBuildManager:
    def test_initial_state(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock())
        assert mgr.get_latest_build() is None
        assert mgr.get_build_history() == []

    def test_process_live_coding_start(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock())
        mgr._on_build_started("live_coding")
        latest = mgr.get_latest_build()
        assert latest is not None
        assert latest.status == BuildStatus.BUILDING

    def test_process_live_coding_success(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock())
        mgr._on_build_started("live_coding")
        mgr._on_build_completed(success=True)
        latest = mgr.get_latest_build()
        assert latest is not None
        assert latest.status == BuildStatus.SUCCEEDED

    def test_process_live_coding_failure(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock())
        mgr._on_build_started("live_coding")
        mgr._on_build_completed(success=False)
        latest = mgr.get_latest_build()
        assert latest.status == BuildStatus.FAILED

    def test_add_build_output(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock())
        mgr._on_build_started("live_coding")
        mgr._add_build_output(r"D:\Src\MyFile.cpp(42): error C2065: 'foo': undeclared identifier")
        latest = mgr.get_latest_build()
        assert len(latest.raw_output) == 1
        assert len(latest.errors) == 1
        assert latest.errors[0].code == "C2065"

    def test_history_limit(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock(), max_history=3)
        for i in range(5):
            mgr._on_build_started("live_coding")
            mgr._on_build_completed(success=True)
        history = mgr.get_build_history()
        assert len(history) == 3

    def test_get_build_by_id(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock())
        mgr._on_build_started("live_coding")
        build_id = mgr.get_latest_build().build_id
        found = mgr.get_build(build_id)
        assert found is not None
        assert found.build_id == build_id

    def test_get_build_not_found(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock())
        assert mgr.get_build("nonexistent") is None

    def test_build_summary(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock())
        mgr._on_build_started("live_coding")
        mgr._add_build_output(r"D:\Src\A.cpp(1): error C2065: foo")
        mgr._add_build_output(r"D:\Src\B.cpp(2): warning C4267: bar")
        mgr._add_build_output(r"D:\Src\C.cpp(3): error C2065: baz")
        mgr._on_build_completed(success=False)
        summary = mgr.get_build_summary()
        assert summary["error_count"] == 2
        assert summary["warning_count"] == 1
        assert summary["status"] == "failed"

    def test_detect_live_coding_completion(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock())
        mgr._on_build_started("live_coding")
        mgr.process_log_entry(_make_log_entry("LogLiveCoding", "Display", "Live coding succeeded."))
        latest = mgr.get_latest_build()
        assert latest.status == BuildStatus.SUCCEEDED

    def test_detect_live_coding_failure(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock())
        mgr._on_build_started("live_coding")
        mgr.process_log_entry(_make_log_entry("LogLiveCoding", "Warning", "Live coding failed."))
        latest = mgr.get_latest_build()
        assert latest.status == BuildStatus.FAILED

    def test_non_lc_log_ignored(self):
        mgr = BuildManager(bridge=MagicMock(), tailer=MagicMock())
        mgr._on_build_started("live_coding")
        mgr.process_log_entry(_make_log_entry("LogTemp", "Display", "some other log"))
        latest = mgr.get_latest_build()
        assert latest.status == BuildStatus.BUILDING
