---
name: blender-rigging
description: Armatures, bone constraints, IK, weights and shape keys in Blender.
---

# Риггинг

Read the sibling blender-mcp skill for connection and shared workflow. Start with get_scene_info and inspect the actual tool schemas.

Inspect mesh transforms, armature axes, existing bone names and animations. Create or edit rigs through bpy with explicit mode transitions. Keep deformation bones distinct from controls. Verify constraint spaces, IK pole direction and bone roll. Test weights with several extreme poses and inspect unweighted vertices. Preserve shape keys; topology changes can invalidate them. Restore rest/pose state after checks. Do not describe automatic weighting as production-ready without deformation inspection.

Use execute_blender_code for operations outside studio_action. Treat this workflow as guidance, not evidence that all branches have been tested. Inspect the output and report concrete checks and remaining limitations.
