"""Entry point for `python -m unreal_editor_mcp` and `uvx unreal-editor-mcp`."""

from __future__ import annotations

import argparse

from unreal_editor_mcp import __version__


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="unreal-editor-mcp",
        description="Build diagnostics and editor log tools for Unreal Engine AI development.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    args = parser.parse_args()
    _run_server()


def _run_server() -> None:
    from unreal_editor_mcp.server import main
    main()


if __name__ == "__main__":
    cli()
