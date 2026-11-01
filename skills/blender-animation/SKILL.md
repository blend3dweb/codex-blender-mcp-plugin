---
name: blender-animation
description: Keyframes, actions, NLA, shape-key animation and camera motion in Blender.
---

# Анимация

Read the sibling blender-mcp skill for connection and shared workflow. Start with get_scene_info and inspect the actual tool schemas.

Inspect FPS, frame range, rotation modes and current actions. Use studio_action keyframe or turntable for simple motion. Existing keys at the same frame/property may be replaced. Turntable uses the current default keyframe interpolation; inspect and set linear interpolation through the current action/channel API when constant angular speed is required. For complex animation inspect installed Blender RNA instead of assuming legacy Action.fcurves. Check start, middle and end frames, constraints, looping and contact points. Make a low-resolution preview before final rendering.

Use execute_blender_code for operations outside studio_action. Treat this workflow as guidance, not evidence that all branches have been tested. Inspect the output and report concrete checks and remaining limitations.
