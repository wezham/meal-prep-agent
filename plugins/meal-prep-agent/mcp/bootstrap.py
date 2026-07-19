"""Prepare Playwright's browser and launch the bundled Woolworths MCP server."""

from __future__ import annotations

import subprocess
import sys


def install_chromium() -> None:
    """Install Chromium if absent while keeping MCP stdout protocol-clean."""
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
        stdout=sys.stderr,
        stderr=sys.stderr,
    )


def main() -> None:
    """Bootstrap runtime dependencies and start the stdio server."""
    install_chromium()

    from woolworths_mcp.server import main as run_server

    run_server()


if __name__ == "__main__":
    main()
