import bpy, importlib.util, json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ops',root/'scripts/studio_ops.py')
ops=importlib.util.module_from_spec(spec);spec.loader.exec_module(ops)
checks=[]
def call(op,names,options={}):
    result=ops.run(op,names,options);checks.append(op);return result
cube=bpy.data.objects['Cube']
call('bevel',['Cube']);call('bevel',['Cube'])
assert len([m for m in cube.modifiers if m.name=='Codex_bevel'])==1
call('subdivide',['Cube']);assert cube.modifiers['Codex_subdivide'].levels==2
call('decimate',['Cube']);assert cube.modifiers['Codex_decimate'].ratio==.5
call('remesh',['Cube']);assert cube.modifiers['Codex_remesh'].mode=='VOXEL'
call('uv_smart',['Cube']);assert len(cube.data.uv_layers)>0
call('material',['Cube'],{'name':'StudioTest'});assert 'StudioTest' in cube.data.materials
before=cube.data.vertices[0].co.copy()
call('sculpt_deform',['Cube'],{'radius':10});assert (cube.data.vertices[0].co-before).length>0
call('keyframe',['Cube'],{'frame':1,'value':[0,0,0]})
call('keyframe',['Cube'],{'frame':10,'value':[1,2,3]})
bpy.context.scene.frame_set(10);assert tuple(cube.location)==(1,2,3)
call('turntable',['Cube']);assert cube.animation_data.action
call('rigid_body',['Cube']);assert cube.rigid_body.type=='ACTIVE'
call('cloth',['Cube']);assert cube.modifiers['Codex_cloth'].type=='CLOTH'
call('render_settings',[],{'width':800,'height':600});assert bpy.context.scene.render.resolution_x==800
call('inspect',['Cube'])
path=root/'test-output/studio-test-copy.blend'
if path.exists():path.unlink()
call('save_copy',[],{'path':str(path)});assert path.stat().st_size>1000
for op,names,options in [('bevel',['Missing'],{}),('subdivide',['Cube'],{'levels':99}),('save_copy',[],{'path':str(path)})]:
    try:ops.run(op,names,options)
    except ValueError:checks.append('rejected:'+op)
    else:raise AssertionError('Expected rejection')
(root/'test-output/studio-results.json').write_text(json.dumps({'blender':bpy.app.version_string,'checks':checks},indent=2))
print('STUDIO_CHECKS_PASSED',len(checks))
