"""Parse Unreal Engine log lines into structured entries."""

from __future__ import annotations

import re
from dataclasses import dataclass

SEVERITIES = ("Fatal", "Error", "Warning", "Display", "Log", "Verbose", "VeryVerbose")
_SEVERITY_SET = set(SEVERITIES)

_LOG_RE = re.compile(
    r"\[(?P<timestamp>[\d.:\-]+)\]"
    r"\[\s*(?P<frame>\d+)\]"
    r"(?P<category>\w+):\s*"
    r"(?:(?P<severity>" + "|".join(SEVERITIES) + r"):\s*)?"
    r"(?P<message>.*)"
)


@dataclass(slots=True)
class LogEntry:
    """A single parsed UE log line."""
    timestamp: str
    frame: int
    category: str
    severity: str
    message: str
    raw: str


def parse_log_line(line: str) -> LogEntry | None:
    """Parse a UE log line. Returns None for continuation/non-log lines."""
    if not line:
        return None
    m = _LOG_RE.match(line)
    if not m:
        return None
    severity = m.group("severity") or "Log"
    return LogEntry(
        timestamp=m.group("timestamp"),
        frame=int(m.group("frame")),
        category=m.group("category"),
        severity=severity,
        message=m.group("message"),
        raw=line,
    )
