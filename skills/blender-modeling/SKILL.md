---
name: blender-modeling
description: Mesh modeling, topology, modifiers and precision dimensions in Blender.
---

# Моделирование

Read the sibling blender-mcp skill for connection and shared workflow. Start with get_scene_info and inspect the actual tool schemas.

Inspect units, transforms, topology and bounding boxes. Prefer non-applied modifiers for bevel, mirror, subdivision and decimation. Use studio_action where supported; bmesh for selected topology. Check manifold edges, normals and dimensions after changes. Preserve UVs and material slots. Preview several angles before applying modifiers.

Use execute_blender_code for operations outside studio_action. Treat this workflow as guidance, not evidence that all branches have been tested. Inspect the output and report concrete checks and remaining limitations.
