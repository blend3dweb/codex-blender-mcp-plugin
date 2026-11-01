---
name: blender-geometry-nodes
description: Procedural Blender geometry, node groups, instances and distributions.
---

# Geometry Nodes

Read the sibling blender-mcp skill for connection and shared workflow. Start with get_scene_info and inspect the actual tool schemas.

Use bpy to build named node groups and expose meaningful parameters. Inspect current node socket names/types in installed Blender. Avoid overwriting shared node groups; duplicate when the change is local. Keep instances unrealized until downstream operations need geometry. Use deterministic seeds, bounded counts and explicit dimensions. Test parameter extremes and evaluated bounds; inspect a preview before increasing density.

Use execute_blender_code for operations outside studio_action. Treat this workflow as guidance, not evidence that all branches have been tested. Inspect the output and report concrete checks and remaining limitations.
