---
name: blender-spatial-inspection
description: Inspect Blender geometry in space, diagnose floating parts and gaps, examine mesh sections, or compare a model with image landmarks through a known camera.
---

Use `spatial_capabilities` for exact query parameters. Pair numeric queries with `look`; geometry measurements and images answer different questions.

For shape work, inspect the target with `look(mode="angles", target=[names], views=["front","right","top","three_quarter"], shading="solid")`. Use wireframe or xray when connectivity or hidden surfaces matter. Read the tool's text: a fallback to the current viewport is not a successful multi-view capture. Do not substitute a polished render for geometric inspection.

`spatial_inspect` operations:
- `topology`: count disconnected components and boundary/nonmanifold edges. One object can contain many disconnected islands. A single connected component does not establish good anatomy, manifoldness or lack of self-intersections.
- `elements`: page vertices/edges/faces in world space. Use `evaluated=false` for editable base indices. Evaluated indices can change with modifiers and frame. Preserve and recheck `geometry_hash` when using indices later; do not edit based on stale indices.
- `section`: intersect a plane with evaluated triangles; output segments are not ordered contour loops. Check truncation and skipped coplanar triangles.
- `proximity`: sample source vertices against another mesh surface. It reports unsigned distances, not penetration depth or proof of attachment. Nested solids and intersecting faces can have positive sampled distances. Inspect multiple views; use dedicated intersection methods when required.
- `project`: compare explicit vertex landmarks to reference UV coordinates using a named camera. UV origin is top-left. Match image aspect and camera before interpreting residuals. This does not identify landmarks automatically or reconstruct depth from a photograph.

All queries require Object Mode; ask the existing Blender workflow to switch mode if appropriate, rather than silently changing it in a read operation. Outputs use Blender world units; `meters_per_unit` records unit scale.

For a reversible local adjustment, read `edit_capabilities`. Capture `look(mode="camera")`, create an `edit_session` snapshot, apply a bounded world-space `deform`, then `compare` and capture the same camera again. Keep camera, frame, materials, lighting and viewport shading fixed for the comparison. Restore coordinates if the adjustment fails the task; discard the snapshot after saving accepted geometry. Snapshots are session memory, not durable .blend backups. They do not restore topology, materials or modifiers. A conflict means another edit occurred: inspect it and do not bypass the guard to overwrite newer work.

For modeling from a reference: use a manageable base mesh, match silhouette and landmark projections first, then inspect side and top views. Apply a localized change, repeat the same views/queries, and retain or revert it based on evidence. Do not claim exact likeness from a small projection error or from a watertight mesh. Add density and fine detail only after the large forms are established. Follow the user's agreed checkpoints for moving to materials or animation.
