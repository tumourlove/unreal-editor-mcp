# unreal-editor-mcp

Build diagnostics and editor log tools for Unreal Engine AI development via [Model Context Protocol](https://modelcontextprotocol.io/).

Gives AI assistants the ability to trigger Live Coding builds, inspect parsed compile errors, search/filter editor logs, and get crash context — the "feedback loop" for C++ iteration without leaving the AI workflow.

## Why?

When iterating on C++ in UE, the build-test cycle is invisible to AI assistants. They can write code but can't compile it, see if it worked, or read the editor's output. This server closes that loop.

**Complements** (does not replace):
- [unreal-source-mcp](https://github.com/tumourlove/unreal-source-mcp) — Engine-level source intelligence (full UE C++ and HLSL)
- [unreal-project-mcp](https://github.com/tumourlove/unreal-project-mcp) — Project-level source intelligence (your C++ code)
- [unreal-blueprint-mcp](https://github.com/tumourlove/unreal-blueprint-mcp) — Blueprint graph reading (nodes, pins, connections, execution flow)
- [unreal-config-mcp](https://github.com/tumourlove/unreal-config-mcp) — Config/INI intelligence (resolve inheritance chains, search settings, diff from defaults, explain CVars)
- [unreal-material-mcp](https://github.com/tumourlove/unreal-material-mcp) — Material graph intelligence and editing (expressions, connections, parameters, instances, graph manipulation)
- [unreal-api-mcp](https://github.com/nicobailon/unreal-api-mcp) by [Nico Bailon](https://github.com/nicobailon) — API surface lookup (signatures, #include paths, deprecation warnings)

Together these servers give AI agents full-stack UE understanding: engine internals, API surface, your project code, build/runtime feedback, Blueprint graph data, config/INI intelligence, and material graph inspection + editing.

## Prerequisites

- **Python Remote Execution** must be enabled in the editor: **Edit > Project Settings** > search "remote" > under **Python Remote Execution**, check **"Enable Remote Execution?"**. This allows the server to discover and communicate with the running editor. Without it, log tools still work but build triggering will fail.

## Quick Start

### Install from GitHub

```bash
uvx --from git+https://github.com/tumourlove/unreal-editor-mcp.git unreal-editor-mcp
```

### Claude Code Configuration

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "unreal-editor": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/tumourlove/unreal-editor-mcp.git", "unreal-editor-mcp"],
      "env": {
        "UE_PROJECT_PATH": "D:/Unreal Projects/MyProject"
      }
    }
  }
}
```

Or run from local source during development:

```json
{
  "mcpServers": {
    "unreal-editor": {
      "command": "uv",
      "args": ["run", "--directory", "C:/Projects/unreal-editor-mcp", "python", "-m", "unreal_editor_mcp"],
      "env": {
        "UE_PROJECT_PATH": "D:/Unreal Projects/MyProject"
      }
    }
  }
}
```

## Tools

### Build Tools (5)

| Tool | Description |
|------|-------------|
| `trigger_build` | Trigger a Live Coding compile via the editor's Python bridge. Returns a build ID for tracking. |
| `get_build_status` | Check build state: building, succeeded, or failed. Shows error/warning counts. |
| `get_build_errors` | Get parsed build errors with file, line, error code, and message. Filter by module or severity. |
| `get_build_summary` | Overview of the latest build: error count, warning count, duration. |
| `search_build_output` | Regex search across raw build output from the latest build. |

### Log Tools (6)

| Tool | Description |
|------|-------------|
| `get_recent_logs` | Last N log lines, filterable by category (e.g. `LogTemp`, `LogNet`) and severity (`Error`, `Warning`, etc). |
| `search_logs` | Regex search across the current session's log buffer. |
| `get_log_categories` | List all active log categories with their message counts. |
| `get_crash_context` | Last Fatal log entries + crash report directory info from `Saved/Crashes/`. |
| `tail_log` | Recent log output (last N seconds). |
| `get_log_stats` | Error/warning breakdown per category, most active categories. |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `UE_PROJECT_PATH` | Yes | Path to the UE project root (containing the .uproject file) |
| `UE_EDITOR_PYTHON_PORT` | No | TCP port for command connection (default: `6776`) |
| `UE_MULTICAST_GROUP` | No | UDP multicast group for editor discovery (default: `239.0.0.1`) |
| `UE_MULTICAST_PORT` | No | UDP multicast port (default: `6766`) |
| `UE_MULTICAST_BIND` | No | Multicast bind address (default: `127.0.0.1`) |

## How It Works

**Editor Bridge** — Discovers the running UE editor via UDP multicast (the same protocol as UE's built-in `remote_execution.py`). Opens a TCP command channel to execute Python in the editor. Used to trigger Live Coding compiles via `LiveCoding.Compile` console command.

**Log Tailer** — A background thread polls the project's `Saved/Logs/{ProjectName}.log` every 500ms. On startup, reads the last 1000 lines to pre-populate. Maintains a rolling buffer of 10,000 parsed log entries in memory. All log tools query this buffer.

**Build Manager** — When a build is triggered, monitors `LogLiveCoding` log entries to detect completion (`"Live coding succeeded"` / `"Live coding failed"`). Parses MSVC error format (`file(line): error C1234: message`) from build output. Keeps a rolling history of the last 5 builds.

**No database** — all state lives in memory. The server is stateless across restarts.

## Development

```bash
# Clone and install
git clone https://github.com/tumourlove/unreal-editor-mcp.git
cd unreal-editor-mcp
uv sync

# Run tests (57 tests)
uv run pytest -v

# Run locally
UE_PROJECT_PATH="/path/to/project" uv run python -m unreal_editor_mcp
```

## Adding to Your Project's CLAUDE.md

If your UE project has a `CLAUDE.md` (used by Claude Code for project context), add a note so the AI knows build and log tools are available:

```markdown
## MCP Servers

- **unreal-editor-mcp** is configured. Use `trigger_build` to compile via Live Coding,
  `get_build_errors` to inspect failures, and `get_recent_logs` / `search_logs` to
  check editor output. Always check build results after modifying C++ code.
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Unreal Engine 5.x with Python plugin and Remote Execution enabled

## License

MIT
