"""Build manager: trigger builds, track status, maintain history."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from unreal_editor_mcp.build.parser import BuildError, parse_build_error
from unreal_editor_mcp.logs.parser import LogEntry

logger = logging.getLogger(__name__)

_DEFAULT_MAX_HISTORY = 5


class BuildStatus(Enum):
    BUILDING = "building"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class BuildRecord:
    """Record of a single build."""
    build_id: str
    build_type: str
    status: BuildStatus = BuildStatus.BUILDING
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    raw_output: list[str] = field(default_factory=list)
    errors: list[BuildError] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.build_id,
            "type": self.build_type,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "error_count": sum(1 for e in self.errors if e.severity == "error"),
            "warning_count": sum(1 for e in self.errors if e.severity == "warning"),
        }


class BuildManager:
    """Manages build triggering, status tracking, and history."""

    def __init__(self, bridge, tailer, max_history: int = _DEFAULT_MAX_HISTORY) -> None:
        self._bridge = bridge
        self._tailer = tailer
        self._max_history = max_history
        self._history: list[BuildRecord] = []
        self._current: BuildRecord | None = None

        # Subscribe to live log entries so we detect build completion.
        if hasattr(tailer, "subscribe"):
            tailer.subscribe(self.process_log_entry)

    def trigger_build(self, build_type: str = "live_coding") -> BuildRecord:
        """Trigger a build via the editor bridge."""
        if build_type == "live_coding":
            result = self._bridge.run_command(
                'import unreal; unreal.SystemLibrary.execute_console_command(None, "LiveCoding.Compile")',
                exec_mode="ExecuteFile",
            )
            self._on_build_started(build_type)
            if not result.get("success", False):
                self._add_build_output(result.get("result", "Failed to trigger Live Coding"))
                self._on_build_completed(success=False)
        else:
            raise ValueError(f"Unsupported build type: {build_type}")
        return self._current

    def process_log_entry(self, entry: LogEntry) -> None:
        """Process a log entry to detect build status changes."""
        if not self._current or self._current.status != BuildStatus.BUILDING:
            return
        if entry.category == "LogLiveCoding":
            msg_lower = entry.message.lower()
            if "succeeded" in msg_lower:
                self._on_build_completed(success=True)
            elif "failed" in msg_lower:
                self._on_build_completed(success=False)
        elif entry.category in ("LogCompile", "CompilerResultsLog"):
            self._add_build_output(entry.message)

    def get_latest_build(self) -> BuildRecord | None:
        return self._current

    def get_build(self, build_id: str) -> BuildRecord | None:
        for record in self._history:
            if record.build_id == build_id:
                return record
        if self._current and self._current.build_id == build_id:
            return self._current
        return None

    def get_build_history(self) -> list[BuildRecord]:
        return list(self._history)

    def get_build_summary(self, build_id: str | None = None) -> dict:
        record = self.get_build(build_id) if build_id else self._current
        if not record:
            return {"status": "no_builds", "error_count": 0, "warning_count": 0}
        error_count = sum(1 for e in record.errors if e.severity == "error")
        warning_count = sum(1 for e in record.errors if e.severity == "warning")
        duration = (record.end_time - record.start_time) if record.end_time else None
        return {
            "id": record.build_id,
            "type": record.build_type,
            "status": record.status.value,
            "error_count": error_count,
            "warning_count": warning_count,
            "duration": duration,
            "total_output_lines": len(record.raw_output),
        }

    def _on_build_started(self, build_type: str) -> None:
        if self._current:
            self._history.append(self._current)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        self._current = BuildRecord(
            build_id=str(uuid.uuid4())[:8],
            build_type=build_type,
        )

    def _on_build_completed(self, success: bool) -> None:
        if not self._current:
            return
        self._current.status = BuildStatus.SUCCEEDED if success else BuildStatus.FAILED
        self._current.end_time = time.time()

    def _add_build_output(self, line: str) -> None:
        if not self._current:
            return
        self._current.raw_output.append(line)
        error = parse_build_error(line)
        if error:
            self._current.errors.append(error)
