"""Parse MSVC/UBT build error output into structured errors."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_MSVC_RE = re.compile(
    r"(?P<file>[A-Za-z]:[^\(]+|[^\(:\s]+)"
    r"\((?P<line>\d+)(?:,(?P<col>\d+))?\)"
    r":\s*(?P<severity>error|warning|note)"
    r"(?:\s+(?P<code>[A-Z]+\d+))?"
    r":\s*(?P<message>.*)"
)

_LINKER_RE = re.compile(
    r"(?P<file>[^\s:]+\.obj)\s*:\s*"
    r"(?P<severity>error|warning)"
    r"(?:\s+(?P<code>[A-Z]+\d+))?"
    r":\s*(?P<message>.*)"
)


@dataclass(slots=True)
class BuildError:
    """A single parsed build error/warning."""
    file: str
    line: int
    column: int
    severity: str
    code: str
    message: str
    raw: str = ""

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }


def parse_build_error(line: str) -> BuildError | None:
    """Parse a build output line into a BuildError, or None if not an error/warning."""
    m = _MSVC_RE.match(line)
    if m:
        return BuildError(
            file=m.group("file"),
            line=int(m.group("line")),
            column=int(m.group("col")) if m.group("col") else 0,
            severity=m.group("severity"),
            code=m.group("code") or "",
            message=m.group("message"),
            raw=line,
        )
    m = _LINKER_RE.match(line)
    if m:
        return BuildError(
            file=m.group("file"),
            line=0,
            column=0,
            severity=m.group("severity"),
            code=m.group("code") or "",
            message=m.group("message"),
            raw=line,
        )
    return None
