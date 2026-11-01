---
name: blender-simulation
description: Rigid bodies, cloth, soft bodies, fluid and particle simulations in Blender.
---

# Симуляции

Read the sibling blender-mcp skill for connection and shared workflow. Start with get_scene_info and inspect the actual tool schemas.

Inspect units, scale, collision shapes and frame range. studio_action supports basic rigid bodies and cloth modifiers; other simulation systems require bpy and version checks. Set cache locations inside the project. Test a short coarse simulation first and check initial intersections and stability. Changing geometry or solver parameters invalidates baked caches. Report modifier setup separately from a completed simulation bake. Use a separate Blender process for long bakes; monitor its process and output rather than repeat a timed-out operation.

Use execute_blender_code for operations outside studio_action. Treat this workflow as guidance, not evidence that all branches have been tested. Inspect the output and report concrete checks and remaining limitations.
