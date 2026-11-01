"""Register additive tools without modifying the vendored upstream server."""
import json
from pathlib import Path
from mcp.server.fastmcp import Context

def register(server):
    source = Path(__file__).with_name('studio_ops.py').read_text(encoding='utf-8')

    @server.mcp.tool()
    def studio_capabilities() -> str:
        """List structured operations, their parameters, and verification limits."""
        import ast
        module = ast.parse(source)
        catalog = next(ast.literal_eval(n.value) for n in module.body
                       if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'OPERATIONS' for t in n.targets))
        return json.dumps({'operations': catalog, 'note': 'Other Blender workflows use execute_blender_code. Changes are not transactional. Inspect targets and save a copy before destructive operations.'})

    @server.mcp.tool()
    async def studio_action(ctx: Context, operation: str, objects: list[str], options: dict | None = None) -> str:
        """Apply one documented Blender operation to explicitly named objects. Read studio_capabilities for options. No implicit selection. sculpt_deform changes vertices; save a backup first. Changes to existing materials affect all users of that material. Does not provide automatic rollback."""
        payload = json.dumps([operation, objects, options or {}])
        code = source + '\nimport json\nprint(json.dumps(run(*json.loads(' + repr(payload) + '))))'
        return await server.execute_blender_code(ctx=ctx, code=code)
