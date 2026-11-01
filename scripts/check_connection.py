"""Read-only end-to-end MCP check. Run using .venv's Python."""
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]

async def check():
    params = StdioServerParameters(command=sys.executable,
                                   args=[str(ROOT / 'scripts' / 'serve.py')],
                                   env={**os.environ, 'BLENDER_MCP_DISABLE_TELEMETRY': '1'})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=45)) as session:
            info = await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool('get_scene_info', {})
            body = '\n'.join(item.text for item in result.content if item.type == 'text')
            if result.isError or body.lstrip().lower().startswith(('error', 'failed')):
                raise RuntimeError(body)
            print(json.dumps({'server': info.serverInfo.name, 'tool_count': len(tools.tools),
                              'connection': 'ok', 'scene': body}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    asyncio.run(asyncio.wait_for(check(), timeout=70))
