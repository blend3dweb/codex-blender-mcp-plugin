import bpy, importlib.util, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('spatial',ROOT/'scripts/spatial_ops.py');ops=importlib.util.module_from_spec(spec);spec.loader.exec_module(ops)
checks=[]
def check(label,value):
 assert value,label
 checks.append(label)
def rejected(label,fn):
 try:fn()
 except ValueError:checks.append(label)
 else:raise AssertionError(label)
def call(op,names=['Cube'],**p):return ops.run_spatial(op,names,p)
cube=bpy.data.objects['Cube'];cube.location=(3,0,0);cube.scale=(2,1,1);bpy.context.view_layer.update()
r=call('topology');check('closed cube topology',r['connected_components']==1 and r['boundary_edges']==0 and r['vertices']==8)
r=call('elements',evaluated=False,indices=[0]);check('world coordinates and nonuniform scale',r['elements'][0]['position'][0] in (1.0,5.0));oldhash=r['geometry_hash']
check('pagination',call('elements',limit=3)['next_offset']==3)
check('edge connectivity',len(call('elements',kind='edges',limit=1)['elements'][0]['vertices'])==2)
check('face normals',abs(Vector(call('elements',kind='faces',limit=1)['elements'][0]['normal']).length-1)<1e-6)
cube.data.vertices[0].co.z+=.1
rejected('stale hash refused',lambda:call('elements',evaluated=False,expected_hash=oldhash));cube.data.vertices[0].co.z-=.1;cube.data.update();bpy.context.view_layer.update()
r=call('section',origin=[3,0,0],normal=[0,0,1]);check('plane intersects cube',r['total_segments']==8 and all(abs(v[2])<1e-6 for edge in r['segments'] for v in edge))
check('section limit explicit',call('section',origin=[3,0,0],limit=2)['truncated'])
check('coplanar faces reported',call('section',origin=[0,0,1])['coplanar_triangles_skipped']==2)
bpy.ops.mesh.primitive_cube_add(location=(8,0,0));target=bpy.context.object;target.name='Target';bpy.context.view_layer.update()
r=call('proximity',['Cube','Target']);check('known surface separation',abs(r['sampled_min_distance']-2)<1e-5 and r['penetration']=='not determined')
# Surface distance on nested solids must not be mistaken for no intersection.
target.location=(3,0,0);target.scale=(4,4,4);bpy.context.view_layer.update();r=call('proximity',['Cube','Target']);check('nested solids remain unsigned and inconclusive',r['sampled_min_distance']>0 and r['penetration']=='not determined')
mesh=bpy.data.meshes.new('Disconnected');mesh.from_pydata([(0,0,0),(1,0,0),(0,1,0),(5,0,0)],[(0,1),(1,2),(2,0)],[(0,1,2)]);o=bpy.data.objects.new('Disconnected',mesh);bpy.context.collection.objects.link(o)
r=call('topology',['Disconnected']);check('floating island and open boundary detected',r['connected_components']==2 and r['isolated_vertices']==1 and r['boundary_edges']==3)
bpy.ops.object.camera_add(location=(3,-10,0));cam=bpy.context.object;cam.name='MeasureCamera';cam.rotation_euler=(Vector((3,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=8;bpy.context.view_layer.update()
from bpy_extras.object_utils import world_to_camera_view
point=world_to_camera_view(bpy.context.scene,cam,cube.matrix_world@cube.data.vertices[0].co)
r=call('project',camera=cam.name,landmarks=[{'vertex':0,'uv':[point.x,1-point.y]}]);check('camera reference residual zero',r['rms_pixels']<1e-6)
mod=cube.modifiers.new('Subdivision','SUBSURF');mod.levels=1;bpy.context.view_layer.update()
check('base vs evaluated indices explicit',call('elements',evaluated=True)['total']>call('elements',evaluated=False)['total'])
for label,op,names,p in [('missing mesh','topology',['missing'],{}),('zero plane normal','section',['Cube'],{'normal':[0,0,0]}),('invalid vertex','elements',['Cube'],{'indices':[-1]}),('output cap','elements',['Cube'],{'limit':100000}),('invalid camera','project',['Cube'],{'camera':'Cube'})]:
 rejected(label,lambda op=op,names=names,p=p:ops.run_spatial(op,names,p))
bpy.context.view_layer.objects.active=cube;bpy.ops.object.select_all(action='DESELECT');cube.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
rejected('edit mode rejected without altering it',lambda:call('topology'));check('mode preserved',cube.mode=='EDIT');bpy.ops.object.mode_set(mode='OBJECT')
(ROOT/'test-output/spatial-results.json').write_text(json.dumps({'blender':bpy.app.version_string,'checks':checks},indent=2))
print('SPATIAL_TESTS_PASSED',len(checks))
