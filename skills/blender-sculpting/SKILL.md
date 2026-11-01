---
name: blender-sculpting
description: Sculpt and reshape Blender meshes, remesh, masks and multiresolution workflows.
---

# Скульптинг

Read the sibling blender-mcp skill for connection and shared workflow. Start with get_scene_info and inspect the actual tool schemas.

Save a copy before changing vertices or remeshing. Inspect vertex density and shared mesh users. studio_action sculpt_deform uses OBJECT-LOCAL coordinates and a smooth radial falloff; it is not a Blender brush stroke and repeated calls accumulate deformation. For actual brushes inspect installed brush assets and operator RNA, active mode, viewport region and stroke coordinates. Test one stroke on a duplicate first. Do not claim high-detail sculpting is verified merely because a coarse deformation succeeded. Compare silhouette from several directions; avoid remesh on UV-mapped or rigged meshes without preserving a source copy.

Use execute_blender_code for operations outside studio_action. Treat this workflow as guidance, not evidence that all branches have been tested. Inspect the output and report concrete checks and remaining limitations.
