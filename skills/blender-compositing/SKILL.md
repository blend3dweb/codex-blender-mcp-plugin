---
name: blender-compositing
description: Blender compositor, render passes and video sequence editing.
---

# Композитинг и видео

Read the sibling blender-mcp skill for connection and shared workflow. Start with get_scene_info and inspect the actual tool schemas.

Inspect render layers, passes, alpha convention, color space, resolution and frame rate. Use bpy node trees for compositing and the current sequence editor API for editing. Preserve original render outputs and source media. Check a representative frame before rendering the sequence; ensure audio timing, strip offsets and final encoding are correct. Verify final duration and missing frames. Compositor and sequence APIs must be checked against the installed Blender version.

Use execute_blender_code for operations outside studio_action. Treat this workflow as guidance, not evidence that all branches have been tested. Inspect the output and report concrete checks and remaining limitations.
