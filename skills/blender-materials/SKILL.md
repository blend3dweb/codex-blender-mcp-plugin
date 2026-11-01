---
name: blender-materials
description: Build and edit Blender shader nodes, PBR materials and procedural surfaces.
---

# Материалы

Read the sibling blender-mcp skill for connection and shared workflow. Start with get_scene_info and inspect the actual tool schemas.

Inspect existing node graphs and material users. studio_action material modifies the named material for every user; copy it first for a per-object change. Keep existing graphs unless replacement is requested. Use bpy for procedural textures and image nodes. Check scale, UV or Generated coordinates, normal strength, roughness and color management under neutral lighting. Compare Cycles and Eevee only if both are target engines.

Use execute_blender_code for operations outside studio_action. Treat this workflow as guidance, not evidence that all branches have been tested. Inspect the output and report concrete checks and remaining limitations.
