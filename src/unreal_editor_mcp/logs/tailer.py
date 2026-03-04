"""File tailer for UE editor logs with a rolling in-memory buffer."""

from __future__ import annotations

import re
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from unreal_editor_mcp.logs.parser import LogEntry, parse_log_line

_DEFAULT_BUFFER_SIZE = 10_000
_TAIL_INTERVAL = 0.5
_INITIAL_LINES = 1000

LogSubscriber = Callable[[LogEntry], None]


class LogTailer:
    """Tails a UE log file and maintains a rolling buffer of parsed entries."""

    def __init__(
        self,
        log_path: Path,
        auto_start: bool = True,
        buffer_size: int = _DEFAULT_BUFFER_SIZE,
    ) -> None:
        self._log_path = log_path
        self._buffer_size = buffer_size
        self._buffer: list[LogEntry] = []
        self._lock = threading.Lock()
        self._file_pos: int = 0
        self._running = False
        self._thread: threading.Thread | None = None
        self._category_counts: dict[str, int] = defaultdict(int)
        self._severity_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._subscribers: list[LogSubscriber] = []
        if auto_start:
            self.start()

    def start(self) -> None:
        """Start the background tailing thread."""
        if self._running:
            return
        self._running = True
        self._read_initial()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the background tailing thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _run(self) -> None:
        """Background thread main loop."""
        while self._running:
            self._read_new_lines()
            time.sleep(_TAIL_INTERVAL)

    def _read_initial(self) -> None:
        """Read the last N lines of the log file on startup."""
        if not self._log_path.exists():
            return
        try:
            text = self._log_path.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            tail = lines[-_INITIAL_LINES:] if len(lines) > _INITIAL_LINES else lines
            self._ingest_lines(tail)
            self._file_pos = len(text.encode("utf-8", errors="replace"))
        except OSError:
            pass

    def _read_new_lines(self) -> None:
        """Read any new lines appended since last read."""
        if not self._log_path.exists():
            return
        try:
            with open(self._log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._file_pos)
                new_text = f.read()
                if not new_text:
                    return
                self._file_pos += len(new_text.encode("utf-8", errors="replace"))
                lines = new_text.splitlines()
                if lines:
                    self._ingest_lines(lines)
        except OSError:
            pass

    def subscribe(self, callback: LogSubscriber) -> None:
        """Register a callback to be invoked for each new log entry."""
        self._subscribers.append(callback)

    def _ingest_lines(self, lines: list[str]) -> None:
        """Parse lines and add to buffer, trimming to buffer_size."""
        entries = []
        for line in lines:
            entry = parse_log_line(line)
            if entry:
                entries.append(entry)
        if not entries:
            return
        with self._lock:
            self._buffer.extend(entries)
            if len(self._buffer) > self._buffer_size:
                self._buffer = self._buffer[-self._buffer_size:]
            for entry in entries:
                self._category_counts[entry.category] += 1
                self._severity_counts[entry.category][entry.severity] += 1
        for entry in entries:
            for subscriber in self._subscribers:
                try:
                    subscriber(entry)
                except Exception:
                    pass

    def get_recent(
        self,
        count: int = 0,
        category: str | None = None,
        severity: str | None = None,
    ) -> list[LogEntry]:
        """Get recent log entries, optionally filtered."""
        with self._lock:
            entries = list(self._buffer)
        if category:
            entries = [e for e in entries if e.category == category]
        if severity:
            entries = [e for e in entries if e.severity == severity]
        if count > 0:
            entries = entries[-count:]
        return entries

    def search(self, pattern: str, count: int = 0) -> list[LogEntry]:
        """Search log entries by regex pattern against the message."""
        compiled = re.compile(pattern)
        with self._lock:
            entries = list(self._buffer)
        results = [e for e in entries if compiled.search(e.message)]
        if count > 0:
            results = results[-count:]
        return results

    def get_categories(self) -> dict[str, int]:
        """Get all categories with their total message counts."""
        with self._lock:
            return dict(self._category_counts)

    def get_category_stats(self) -> dict[str, dict[str, int]]:
        """Get per-category severity breakdown."""
        with self._lock:
            return {cat: dict(sevs) for cat, sevs in self._severity_counts.items()}
