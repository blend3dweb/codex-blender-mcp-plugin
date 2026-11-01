import ast
import json
from pathlib import Path
from mcp.server.fastmcp import Context

def register(server):
    source=Path(__file__).with_name('edit_ops.py').read_text(encoding='utf-8')
    @server.mcp.tool()
    def edit_capabilities() -> str:
        """Discover bounded local geometry changes and conflict-aware coordinate restore."""
        module=ast.parse(source)
        catalog=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CATALOG' for t in n.targets))
        return json.dumps(catalog)
    @server.mcp.tool()
    async def edit_session(ctx: Context, operation: str, objects: list[str] | None=None, options: dict | None=None) -> str:
        """Snapshot, deform, compare or restore base-mesh coordinates. Read edit_capabilities first. Memory snapshots are not durable .blend backups. Restore rejects external changes. Camera/frame equality is metadata, not artistic or image equality."""
        payload=json.dumps([operation,objects or [],options or {}],allow_nan=False)
        code=source+'\nimport json\nprint(json.dumps(run_edit(*json.loads('+repr(payload)+')),allow_nan=False))'
        return await server.execute_blender_code(ctx=ctx,code=code)
