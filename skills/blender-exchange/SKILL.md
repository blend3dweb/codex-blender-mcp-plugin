---
name: blender-exchange
description: Save Blender projects and import/export GLB, FBX, OBJ, STL and related formats.
---

# Файлы и экспорт

Read the sibling blender-mcp skill for connection and shared workflow. Start with get_scene_info and inspect the actual tool schemas.

Resolve absolute input/output paths and inspect pending unsaved work before opening another .blend. Use studio_action save_copy for a new backup path. Check available import/export operators; do not silently install extensions. Confirm target units, up axis, applied transforms, selected objects and animation inclusion. For GLB check packed textures; for STL check manifold geometry and units. Reimport into a separate scene/process to verify bounds, materials and animations. Retain the editable .blend alongside exports.

Use execute_blender_code for operations outside studio_action. Treat this workflow as guidance, not evidence that all branches have been tested. Inspect the output and report concrete checks and remaining limitations.
