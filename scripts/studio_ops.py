"""Structured operations executed inside Blender; all targets are explicit."""
import bpy
import math
from mathutils import Vector

OPERATIONS = {
    'inspect': 'objects: mesh counts, dimensions and modifiers',
    'bevel': 'objects; width=0.05, segments=3',
    'subdivide': 'objects; levels=2 (0..6)',
    'decimate': 'objects; ratio=0.5 (0..1)',
    'remesh': 'objects; voxel_size=0.1; adds a non-applied voxel modifier',
    'sculpt_deform': 'objects; center=[0,0,0] in object space, radius=1, displacement=[0,0,0.1]; radial smooth deformation, not a brush stroke',
    'uv_smart': 'mesh objects; angle_degrees=66, island_margin=0.02',
    'material': 'objects; name, color=[0.3,0.5,0.7,1], metallic=0, roughness=0.5',
    'keyframe': 'objects; frame=1, property=location|rotation_euler|scale, value=[x,y,z]; rotation in radians',
    'turntable': 'objects; start=1, end=120; full local Z rotation; default Blender interpolation',
    'rigid_body': 'mesh objects; body_type=ACTIVE|PASSIVE, mass=1',
    'cloth': 'mesh objects; quality=5; adds modifier, does not bake',
    'render_settings': 'engine=CYCLES|BLENDER_EEVEE, width=640, height=480, samples=32; configuration only',
    'save_copy': 'absolute path ending .blend; existing destination rejected',
}

def run(operation, names, options):
    if operation not in OPERATIONS:
        raise ValueError('Unknown operation: ' + operation)
    missing = [n for n in names if n not in bpy.data.objects]
    if missing:
        raise ValueError('Objects not found: ' + ', '.join(missing))
    objects = [bpy.data.objects[n] for n in dict.fromkeys(names)]
    scene = bpy.context.scene
    if operation not in {'render_settings', 'save_copy'} and not objects:
        raise ValueError('Explicit object names are required')
    mesh_ops = {'bevel', 'subdivide', 'decimate', 'remesh', 'sculpt_deform', 'uv_smart', 'rigid_body', 'cloth'}
    if operation in mesh_ops and any(o.type != 'MESH' for o in objects):
        raise ValueError('This operation requires mesh objects')
    if bpy.context.mode != 'OBJECT' and operation != 'inspect':
        raise ValueError('Switch to Object Mode before this operation')
    p = options
    def number(key, default, lo, hi):
        value = float(p.get(key, default))
        if not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f'{key} must be within {lo}..{hi}')
        return value
    def vector(key, default, size=3):
        value = p.get(key, default)
        if len(value) != size or not all(math.isfinite(float(x)) for x in value):
            raise ValueError(f'{key} must have {size} finite values')
        return tuple(float(x) for x in value)
    def modifier(obj, kind):
        name = 'Codex_' + operation
        existing = obj.modifiers.get(name)
        if existing and existing.type != kind:
            raise ValueError('Modifier name collision: ' + name)
        return existing or obj.modifiers.new(name, kind)
    if operation == 'inspect':
        return [{'name': o.name, 'type': o.type, 'dimensions': list(o.dimensions),
                 'vertices': len(o.data.vertices) if o.type == 'MESH' else None,
                 'faces': len(o.data.polygons) if o.type == 'MESH' else None,
                 'modifiers': [m.type for m in o.modifiers]} for o in objects]
    if operation == 'render_settings':
        engine = p.get('engine', 'CYCLES')
        if engine not in {'CYCLES', 'BLENDER_EEVEE'}:
            raise ValueError('Unsupported engine')
        width = int(number('width', 640, 16, 16384))
        height = int(number('height', 480, 16, 16384))
        samples = int(number('samples', 32, 1, 4096))
        scene.render.engine = engine
        scene.render.resolution_x, scene.render.resolution_y = width, height
        scene.render.resolution_percentage = 100
        if engine == 'CYCLES':
            scene.cycles.samples = samples
        return {'engine': engine, 'resolution': [width, height], 'cycles_samples': samples if engine == 'CYCLES' else None}
    if operation == 'save_copy':
        from pathlib import Path
        path = Path(p['path'])
        if not path.is_absolute() or path.suffix.lower() != '.blend' or path.exists():
            raise ValueError('Use a new absolute .blend path')
        if not path.parent.is_dir():
            raise ValueError('Destination folder does not exist')
        bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True)
        return {'path': str(path), 'bytes': path.stat().st_size}
    # Validate all shared values before modifying any target.
    if operation == 'bevel':
        width, segments = number('width', .05, 0, 10000), int(number('segments', 3, 1, 32))
    elif operation == 'subdivide':
        levels = int(number('levels', 2, 0, 6))
    elif operation == 'decimate':
        ratio = number('ratio', .5, .001, 1)
    elif operation == 'remesh':
        voxel = number('voxel_size', .1, .0001, 10000)
    elif operation == 'sculpt_deform':
        center, delta = Vector(vector('center', [0, 0, 0])), Vector(vector('displacement', [0, 0, .1]))
        radius = number('radius', 1, .00001, 100000)
        if any(o.data.users > 1 for o in objects):
            raise ValueError('Make target meshes single-user before deforming shared geometry')
    elif operation == 'material':
        color = vector('color', [.3, .5, .7, 1], 4)
        metallic, roughness = number('metallic', 0, 0, 1), number('roughness', .5, 0, 1)
    elif operation == 'keyframe':
        prop = p.get('property', 'location')
        if prop not in {'location', 'rotation_euler', 'scale'}:
            raise ValueError('Unsupported animated property')
        value = vector('value', [0, 0, 0])
        frame = number('frame', 1, -1048574, 1048574)
    elif operation == 'turntable':
        start, end = number('start', 1, -1048574, 1048574), number('end', 120, -1048574, 1048574)
        if end <= start or any(o.rotation_mode in {'QUATERNION', 'AXIS_ANGLE'} for o in objects):
            raise ValueError('End must follow start; targets must use Euler rotation')
    elif operation == 'uv_smart':
        angle, margin = math.radians(number('angle_degrees', 66, 1, 89)), number('island_margin', .02, 0, 1)
    elif operation == 'rigid_body':
        body_type = p.get('body_type', 'ACTIVE')
        mass = number('mass', 1, .001, 1000000)
        if body_type not in {'ACTIVE', 'PASSIVE'}:
            raise ValueError('Invalid body_type')
    elif operation == 'cloth':
        quality = int(number('quality', 5, 1, 80))
    selected, active = list(bpy.context.selected_objects), bpy.context.view_layer.objects.active
    try:
        for obj in objects:
            if operation == 'bevel':
                m = modifier(obj, 'BEVEL'); m.width = width; m.segments = segments
            elif operation == 'subdivide':
                m = modifier(obj, 'SUBSURF'); m.levels = levels; m.render_levels = levels
            elif operation == 'decimate':
                modifier(obj, 'DECIMATE').ratio = ratio
            elif operation == 'remesh':
                m = modifier(obj, 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = voxel
            elif operation == 'sculpt_deform':
                for vertex in obj.data.vertices:
                    t = max(0, 1 - (vertex.co - center).length / radius)
                    vertex.co += delta * (t * t * (3 - 2 * t))
                obj.data.update()
            elif operation == 'material':
                name = p.get('name', 'Codex_Material')
                mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
                mat.use_nodes = True
                node = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if node is None:
                    raise ValueError('Existing material has no Principled BSDF')
                node.inputs['Base Color'].default_value = color
                node.inputs['Metallic'].default_value = metallic
                node.inputs['Roughness'].default_value = roughness
                mat.diffuse_color = color
                if mat.name not in obj.data.materials:
                    obj.data.materials.append(mat)
            elif operation == 'keyframe':
                setattr(obj, prop, value); obj.keyframe_insert(data_path=prop, frame=frame)
            elif operation == 'turntable':
                z = obj.rotation_euler.z
                obj.keyframe_insert(data_path='rotation_euler', index=2, frame=start)
                obj.rotation_euler.z = z + 2 * math.pi
                obj.keyframe_insert(data_path='rotation_euler', index=2, frame=end)
                obj.rotation_euler.z = z
            elif operation == 'cloth':
                modifier(obj, 'CLOTH').settings.quality = quality
            elif operation in {'uv_smart', 'rigid_body'}:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True); bpy.context.view_layer.objects.active = obj
                if operation == 'rigid_body':
                    if obj.rigid_body is None:
                        bpy.ops.rigidbody.object_add()
                    obj.rigid_body.type = body_type; obj.rigid_body.mass = mass
                else:
                    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
                    try:
                        bpy.ops.uv.smart_project(angle_limit=angle, island_margin=margin)
                    finally:
                        bpy.ops.object.mode_set(mode='OBJECT')
    finally:
        if bpy.context.mode == 'OBJECT':
            bpy.ops.object.select_all(action='DESELECT')
            for obj in selected:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = active
    return {'operation': operation, 'objects': [o.name for o in objects], 'status': 'applied'}
