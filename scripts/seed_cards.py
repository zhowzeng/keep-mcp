from __future__ import annotations

import sys

from keep_mcp.cli import main as cli_main


if __name__ == "__main__":
    cli_main(["seed", *sys.argv[1:]])
