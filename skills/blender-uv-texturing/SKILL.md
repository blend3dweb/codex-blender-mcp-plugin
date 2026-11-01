---
name: blender-uv-texturing
description: UV unwrap, seams, texture painting, PBR image maps and baking in Blender.
---

# UV и текстуры

Read the sibling blender-mcp skill for connection and shared workflow. Start with get_scene_info and inspect the actual tool schemas.

Inspect UV layers and material assignments first. Use studio_action uv_smart for initial automatic layouts; seams and manual islands need bpy/bmesh. Check stretching with a checker and inspect UV overlap and padding. Color textures use an appropriate color space; roughness, metallic and normal data use Non-Color. Connect normal maps through a Normal Map node. Configure image resolution, active bake target, UV map and padding before baking. Save generated/painted images explicitly; saving .blend alone may not preserve external image edits. Interactive paint strokes require a valid viewport and brush context; test a small area first.

Use execute_blender_code for operations outside studio_action. Treat this workflow as guidance, not evidence that all branches have been tested. Inspect the output and report concrete checks and remaining limitations.
