---
name: blender-lighting-render
description: Blender cameras, lighting, Cycles/Eevee, render passes and output images.
---

# Свет и рендер

Read the sibling blender-mcp skill for connection and shared workflow. Start with get_scene_info and inspect the actual tool schemas.

Inspect engine, camera, resolution, device availability and color management. Use studio_action render_settings for bounded configuration. Start with a small preview. Configure lights/HDRI and exposure, then inspect shadows and clipping. For final renders verify output format, alpha, samples, denoising and destination. Long animation renders should run in a separate process on a saved scene with recorded PID and log; cancellation may stop only that process. A returned timeout is not proof the render stopped. Verify output files/frame coverage and show the actual rendered image through look.

Use execute_blender_code for operations outside studio_action. Treat this workflow as guidance, not evidence that all branches have been tested. Inspect the output and report concrete checks and remaining limitations.
