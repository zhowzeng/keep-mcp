#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    server_params = StdioServerParameters(
        command="uv",
        args=[
            "run",
            "python",
            "-m",
            "keep_mcp.cli",
            "serve",
            "--db-path",
            "data/memory.db",
        ],
        env={"UV_INDEX": os.environ.get("UV_INDEX", "")},
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])

            # Optional: call a tool if present
            if any(t.name == "memory.recall" for t in tools.tools):
                result = await session.call_tool("memory.recall", {"limit": 1})
                print("Recall result structured:", getattr(result, "structuredContent", None))


if __name__ == "__main__":
    asyncio.run(main())
