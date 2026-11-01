import bpy, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('edit_ops',ROOT/'scripts/edit_ops.py');ops=importlib.util.module_from_spec(spec);spec.loader.exec_module(ops)
checks=[]
def check(name,value):
 assert value,name
 checks.append(name)
def reject(name,fn):
 try:fn()
 except ValueError:checks.append(name)
 else:raise AssertionError(name)
def call(op,**options):return ops.run_edit(op,options.pop('objects',[]),options)
cube=bpy.data.objects['Cube'];cube.location=(3,0,0);cube.scale=(2,1,1);bpy.context.view_layer.update()
original=ops._coords(cube.data);s=call('snapshot',objects=['Cube'],label='test')['snapshot_id']
check('snapshot listed',call('list')[0]['snapshot_id']==s)
v=cube.data.vertices[0];center=list(cube.matrix_world@v.co)
result=call('deform',snapshot_id=s,center=center,radius=.5,displacement=[.2,0,0])
check('locality: one vertex moved',result['changed_vertices']['Cube']==1)
r=call('compare',snapshot_id=s);check('world displacement under scaled transform',abs(r['objects'][0]['max_world_displacement']-.2)<1e-5)
check('fixed view metadata',r['same_camera_and_frame'])
bpy.context.scene.frame_set(2);check('changed frame detected',not call('compare',snapshot_id=s)['same_camera_and_frame']);bpy.context.scene.frame_set(1)
call('restore',snapshot_id=s);check('exact coordinate restore',ops._coords(cube.data)==original)
check('compare after restore is zero',call('compare',snapshot_id=s)['objects'][0]['changed_vertices']==0)
reject('oversized displacement refused',lambda:call('deform',snapshot_id=s,center=center,radius=.1,displacement=[1,0,0]))
check('failed validation leaves coordinates intact',ops._coords(cube.data)==original)
cube.data.vertices[1].co.z+=.2
reject('intervening edit protected',lambda:call('restore',snapshot_id=s));check('intervening edit retained',ops._coords(cube.data)!=original)
call('discard',snapshot_id=s);check('discard frees memory',not call('list'))
reject('unknown snapshot refused',lambda:call('restore',snapshot_id=s))
other=bpy.data.objects.new('Shared',cube.data);bpy.context.collection.objects.link(other)
reject('shared data refused',lambda:call('snapshot',objects=['Cube']));bpy.data.objects.remove(other,do_unlink=True)
cube.shape_key_add(name='Basis');reject('shape keys refused',lambda:call('snapshot',objects=['Cube']));cube.shape_key_clear()
bpy.context.view_layer.objects.active=cube;bpy.ops.object.mode_set(mode='EDIT');reject('edit mode refused',lambda:call('snapshot',objects=['Cube']));bpy.ops.object.mode_set(mode='OBJECT')
for i in range(4):call('snapshot',objects=['Cube'])
reject('snapshot budget enforced',lambda:call('snapshot',objects=['Cube']))
for s in call('list'):call('discard',snapshot_id=s['snapshot_id'])
bpy.ops.mesh.primitive_cube_add(location=(0,0,0));other=bpy.context.object;other.name='Other'
s=call('snapshot',objects=['Cube','Other'])['snapshot_id'];before=ops._coords(cube.data);other.location.x+=1;bpy.context.view_layer.update()
reject('all targets preflight before write',lambda:call('deform',snapshot_id=s,center=[3,0,0],radius=10,displacement=[.1,0,0]));check('earlier target unchanged on conflict',ops._coords(cube.data)==before)
out=ROOT/'test-output';out.mkdir(exist_ok=True);(out/'edit-results.json').write_text(json.dumps({'blender':bpy.app.version_string,'checks':checks},indent=2))
print('EDIT_CHECKS_PASSED',len(checks))
