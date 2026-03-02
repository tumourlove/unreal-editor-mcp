"""MCP server with 11 tools for UE build diagnostics and editor log access."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from unreal_editor_mcp.config import UE_PROJECT_PATH, get_log_path, get_crash_dir, _detect_project_name
from unreal_editor_mcp.editor_bridge import EditorBridge, EditorNotRunning
from unreal_editor_mcp.logs.tailer import LogTailer
from unreal_editor_mcp.build.manager import BuildManager

mcp = FastMCP(
    "unreal-editor",
    instructions=(
        "Build diagnostics and editor log tools for Unreal Engine. "
        "Trigger Live Coding builds, inspect build errors, "
        "search and filter editor logs, and get crash context."
    ),
)

_tailer: LogTailer | None = None
_bridge: EditorBridge | None = None
_build_mgr: BuildManager | None = None


def _reset_state() -> None:
    """Reset all singletons (for testing)."""
    global _tailer, _bridge, _build_mgr
    if _tailer:
        _tailer.stop()
    _tailer = None
    _bridge = None
    _build_mgr = None


def _get_tailer(project_path: Path | None = None) -> LogTailer:
    """Lazy-init the log tailer."""
    global _tailer
    if _tailer is not None:
        return _tailer
    if project_path:
        project_name = _detect_project_name()
        log_path = project_path / "Saved" / "Logs" / f"{project_name}.log"
    else:
        log_path = get_log_path()
    _tailer = LogTailer(log_path=log_path, auto_start=True)
    return _tailer


def _get_bridge() -> EditorBridge:
    """Lazy-init the editor bridge."""
    global _bridge
    if _bridge is not None:
        return _bridge
    _bridge = EditorBridge(auto_connect=False)
    return _bridge


def _get_build_mgr() -> BuildManager:
    """Lazy-init the build manager."""
    global _build_mgr
    if _build_mgr is not None:
        return _build_mgr
    _build_mgr = BuildManager(bridge=_get_bridge(), tailer=_get_tailer())
    return _build_mgr


# -- Build Tools (5) ------------------------------------------------------


@mcp.tool()
def trigger_build(build_type: str = "live_coding") -> str:
    """Start a build. Default: Live Coding (requires editor running).

    build_type: 'live_coding' (default). Returns build ID for status tracking.
    """
    mgr = _get_build_mgr()
    try:
        record = mgr.trigger_build(build_type)
        return (
            f"Build triggered: {record.build_id}\n"
            f"Type: {record.build_type}\n"
            f"Status: {record.status.value}\n"
            "Use get_build_status to check progress."
        )
    except EditorNotRunning as e:
        return f"Cannot trigger build: {e}"
    except ValueError as e:
        return str(e)


@mcp.tool()
def get_build_status(build_id: str = "") -> str:
    """Get build status. Latest build if no ID given.

    Returns: building, succeeded, or failed with error/warning counts.
    """
    mgr = _get_build_mgr()
    record = mgr.get_build(build_id) if build_id else mgr.get_latest_build()
    if not record:
        return "No builds recorded."
    d = record.to_dict()
    lines = [
        f"Build: {d['id']}",
        f"Type: {d['type']}",
        f"Status: {d['status']}",
        f"Errors: {d['error_count']}",
        f"Warnings: {d['warning_count']}",
    ]
    return "\n".join(lines)


@mcp.tool()
def get_build_errors(module: str = "", severity: str = "", limit: int = 50) -> str:
    """Get parsed build errors from the latest build.

    module: filter by source file path containing this string
    severity: 'error' or 'warning'
    limit: max errors to return (default 50)
    """
    mgr = _get_build_mgr()
    record = mgr.get_latest_build()
    if not record:
        return "No builds recorded."
    errors = record.errors
    if severity:
        errors = [e for e in errors if e.severity == severity]
    if module:
        errors = [e for e in errors if module.lower() in e.file.lower()]
    errors = errors[:limit]
    if not errors:
        return "No errors found matching filters."
    lines = []
    for e in errors:
        lines.append(f"[{e.severity}] {e.file}({e.line}): {e.code} {e.message}")
    return "\n".join(lines)


@mcp.tool()
def get_build_summary() -> str:
    """Overview of the latest build: error count, warning count, duration."""
    mgr = _get_build_mgr()
    summary = mgr.get_build_summary()
    if summary["status"] == "no_builds":
        return "No builds recorded."
    lines = [
        f"Build: {summary['id']}",
        f"Type: {summary['type']}",
        f"Status: {summary['status']}",
        f"Errors: {summary['error_count']}",
        f"Warnings: {summary['warning_count']}",
        f"Output lines: {summary['total_output_lines']}",
    ]
    if summary.get("duration"):
        lines.append(f"Duration: {summary['duration']:.1f}s")
    return "\n".join(lines)


@mcp.tool()
def search_build_output(pattern: str) -> str:
    """Regex search across raw build output from the latest build."""
    mgr = _get_build_mgr()
    record = mgr.get_latest_build()
    if not record:
        return "No builds recorded."
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Invalid regex: {e}"
    matches = [line for line in record.raw_output if compiled.search(line)]
    if not matches:
        return f"No matches for '{pattern}' in build output."
    return "\n".join(matches[:50])


# -- Log Tools (6) --------------------------------------------------------


@mcp.tool()
def get_recent_logs(category: str = "", severity: str = "", count: int = 50) -> str:
    """Get recent log lines, optionally filtered by category and/or severity.

    category: e.g. 'LogTemp', 'LogNet', 'LogLiveCoding'
    severity: 'Fatal', 'Error', 'Warning', 'Display', 'Log', 'Verbose', 'VeryVerbose'
    count: max lines to return (default 50)
    """
    tailer = _get_tailer()
    entries = tailer.get_recent(
        count=count,
        category=category or None,
        severity=severity or None,
    )
    if not entries:
        return "No log entries found matching filters."
    lines = []
    for e in entries:
        lines.append(f"[{e.timestamp}] {e.category}: {e.severity}: {e.message}")
    return "\n".join(lines)


@mcp.tool()
def search_logs(pattern: str, category: str = "", count: int = 50) -> str:
    """Regex search across the current session log buffer.

    pattern: regex pattern to search for in log messages
    category: optional category filter applied before search
    count: max results (default 50)
    """
    tailer = _get_tailer()
    try:
        results = tailer.search(pattern, count=count)
    except re.error as e:
        return f"Invalid regex: {e}"
    if category:
        results = [e for e in results if e.category == category]
    if not results:
        return f"No log entries matching '{pattern}'."
    lines = []
    for e in results:
        lines.append(f"[{e.timestamp}] {e.category}: {e.severity}: {e.message}")
    return "\n".join(lines)


@mcp.tool()
def get_log_categories() -> str:
    """List all active log categories with their message counts."""
    tailer = _get_tailer()
    cats = tailer.get_categories()
    if not cats:
        return "No log categories found."
    lines = []
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        lines.append(f"  {cat}: {count}")
    return "\n".join(lines)


@mcp.tool()
def get_crash_context() -> str:
    """Get crash context: last Fatal log entries and crash report directory info."""
    tailer = _get_tailer()
    fatal_entries = tailer.get_recent(severity="Fatal", count=20)

    lines: list[str] = []
    if fatal_entries:
        lines.append("=== Fatal Log Entries ===")
        for e in fatal_entries:
            lines.append(f"[{e.timestamp}] {e.category}: {e.message}")
    else:
        lines.append("No Fatal log entries in current session.")

    crash_dir = get_crash_dir()
    if crash_dir.exists():
        crash_folders = sorted(crash_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        crash_folders = [f for f in crash_folders if f.is_dir()][:5]
        if crash_folders:
            lines.append("\n=== Recent Crash Reports ===")
            for folder in crash_folders:
                lines.append(f"  {folder.name}")
                ctx_file = folder / "CrashContext.runtime-xml"
                if ctx_file.exists():
                    lines.append(f"    Context: {ctx_file}")
    return "\n".join(lines) if lines else "No crash data available."


@mcp.tool()
def tail_log(category: str = "", severity: str = "", seconds: int = 30) -> str:
    """Get log output from the last N seconds.

    category: optional category filter
    severity: optional severity filter
    seconds: how many seconds back to look (default 30)
    """
    tailer = _get_tailer()
    entries = tailer.get_recent(
        category=category or None,
        severity=severity or None,
    )
    if not entries:
        return "No log entries found."
    count = max(10, seconds * 2)
    entries = entries[-count:]
    lines = []
    for e in entries:
        lines.append(f"[{e.timestamp}] {e.category}: {e.severity}: {e.message}")
    return "\n".join(lines)


@mcp.tool()
def get_log_stats() -> str:
    """Summary: errors/warnings per category, most active categories."""
    tailer = _get_tailer()
    stats = tailer.get_category_stats()
    if not stats:
        return "No log statistics available."

    lines = ["=== Log Statistics ==="]

    error_cats = {cat: sevs.get("Error", 0) for cat, sevs in stats.items() if sevs.get("Error", 0) > 0}
    if error_cats:
        lines.append("\nCategories with Errors:")
        for cat, count in sorted(error_cats.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: {count} errors")

    warn_cats = {cat: sevs.get("Warning", 0) for cat, sevs in stats.items() if sevs.get("Warning", 0) > 0}
    if warn_cats:
        lines.append("\nCategories with Warnings:")
        for cat, count in sorted(warn_cats.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: {count} warnings")

    total_counts = tailer.get_categories()
    lines.append("\nMost Active Categories:")
    for cat, count in sorted(total_counts.items(), key=lambda x: -x[1])[:10]:
        lines.append(f"  {cat}: {count} messages")

    return "\n".join(lines)


# -- Entry point -----------------------------------------------------------


def main() -> None:
    """Run the MCP server."""
    mcp.run()
