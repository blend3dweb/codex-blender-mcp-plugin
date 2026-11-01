"""Spatial diagnostic MCP tools; upstream code stays unchanged."""
import ast
import json
from pathlib import Path
from mcp.server.fastmcp import Context

def register(server):
    source=Path(__file__).with_name('spatial_ops.py').read_text(encoding='utf-8')
    @server.mcp.tool()
    def spatial_capabilities() -> str:
        """Discover read-only geometry queries and existing multi-angle viewport workflow."""
        module=ast.parse(source)
        catalog=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CATALOG' for t in n.targets))
        return json.dumps({'operations':catalog,'visual_inspection':'Use look(mode="angles", target=[object names], views=["front","right","top","three_quarter"], shading="solid" or "wireframe" or "xray"). Inspect returned text: fallback viewport is NOT proof of requested views.','limits':'Object Mode required. Geometry is read-only. World units, not necessarily metres. No photo-to-3D reconstruction or automatic likeness scoring.'})
    @server.mcp.tool()
    async def spatial_inspect(ctx: Context, operation: str, objects: list[str], options: dict | None=None) -> str:
        """Read world-space topology, paginated elements, sections, sampled proximity or camera landmark residuals. Read spatial_capabilities first. Does not edit meshes. Evaluated vertex indices are snapshot-specific, not base mesh editing indices."""
        payload=json.dumps([operation,objects,options or {}],allow_nan=False)
        code=source+'\nimport json\nprint(json.dumps(run_spatial(*json.loads('+repr(payload)+')),allow_nan=False))'
        return await server.execute_blender_code(ctx=ctx,code=code)
