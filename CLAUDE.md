# CLAUDE.md — unreal-editor-mcp

## Project Overview

**unreal-editor-mcp** — Build diagnostics and editor log tools for Unreal Engine AI development.

An MCP (Model Context Protocol) server that provides structured access to UE editor build output and log files. Trigger Live Coding builds, inspect parsed errors, search/filter editor logs, and get crash context — all without leaving the AI workflow.

**Complements** (does not replace):
- `unreal-source-mcp` — Engine-level source intelligence
- `unreal-project-mcp` — Project-level source intelligence
- `unreal-api-mcp` — API surface (signatures, includes, deprecation)

**We provide:** Build control and log visibility — the "feedback loop" for C++ iteration.

## Tech Stack

- **Language:** Python 3.11+
- **MCP SDK:** `mcp` Python package (FastMCP)
- **Distribution:** PyPI via `uvx unreal-editor-mcp`
- **Package manager:** `uv` (for dev and build)
- **No database** — all state in memory (rolling buffers, build history)

## Project Structure

    unreal-editor-mcp/
    ├── pyproject.toml
    ├── CLAUDE.md
    ├── src/
    │   └── unreal_editor_mcp/
    │       ├── __init__.py          # Version
    │       ├── __main__.py          # CLI entry point
    │       ├── config.py            # UE_PROJECT_PATH, port config, path helpers
    │       ├── server.py            # FastMCP + 11 tool definitions
    │       ├── editor_bridge.py     # UE remote execution protocol client
    │       ├── build/
    │       │   ├── __init__.py
    │       │   ├── manager.py       # Build state, history, trigger logic
    │       │   └── parser.py        # MSVC/UBT error format parsing
    │       └── logs/
    │           ├── __init__.py
    │           ├── tailer.py        # File tailing + rolling buffer
    │           └── parser.py        # UE log format parsing
    └── tests/
        ├── test_log_parser.py
        ├── test_log_tailer.py
        ├── test_build_parser.py
        ├── test_build_manager.py
        └── test_server.py

## Build & Run

```bash
uv sync                                    # Install deps
uv run pytest                              # Run tests
uv run python -m unreal_editor_mcp         # Run MCP server
```

## MCP Configuration (for Claude Code)

```json
{
  "mcpServers": {
    "unreal-editor": {
      "command": "uvx",
      "args": ["unreal-editor-mcp"],
      "env": {
        "UE_PROJECT_PATH": "D:/Unreal Projects/Leviathan"
      }
    }
  }
}
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `UE_PROJECT_PATH` | Path to UE project root (contains .uproject) — required |
| `UE_EDITOR_PYTHON_PORT` | TCP port for command connection (default: 6776) |
| `UE_MULTICAST_GROUP` | UDP multicast group for discovery (default: 239.0.0.1) |
| `UE_MULTICAST_PORT` | UDP multicast port (default: 6766) |
| `UE_MULTICAST_BIND` | Multicast bind address (default: 127.0.0.1) |

## MCP Tools (11)

### Build Tools (5)

| Tool | Purpose |
|------|---------|
| `trigger_build` | Trigger Live Coding build via editor Python bridge |
| `get_build_status` | Check build state: building/succeeded/failed |
| `get_build_errors` | Get parsed errors with file, line, code, message |
| `get_build_summary` | Error/warning counts, duration overview |
| `search_build_output` | Regex search across raw build output |

### Log Tools (6)

| Tool | Purpose |
|------|---------|
| `get_recent_logs` | Last N log lines, filterable by category/severity |
| `search_logs` | Regex search across session log buffer |
| `get_log_categories` | Active categories with message counts |
| `get_crash_context` | Fatal entries + crash report directory info |
| `tail_log` | Recent log output (last N seconds) |
| `get_log_stats` | Error/warning breakdown per category |

## Architecture Notes

- **Stateless server** — no SQLite, all data in memory
- **Log tailer** runs a background thread, polls log file every 500ms, maintains 10K-line rolling buffer
- **Editor bridge** uses UE's remote execution protocol: UDP multicast discovery → TCP command connection
- **Build manager** monitors `LogLiveCoding` log entries to detect build completion
- Tool handlers are thin wrappers over the build manager and log tailer

## Coding Conventions

- Follow standard Python conventions: snake_case, type hints, docstrings on public functions
- Use `logging` module, not print statements
- Tests use pytest
- Keep dependencies minimal — just `mcp>=1.0.0`
