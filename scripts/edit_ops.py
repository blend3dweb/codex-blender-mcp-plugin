"""Bounded, reversible base-mesh coordinate edits in the current Blender session."""
import bpy
import uuid
import math
import hashlib
from array import array
from mathutils import Vector

KEY='_codex_geometry_edits_v1'
CATALOG={
 'snapshot':'Explicit mesh objects, label optional. Up to 4 in-memory snapshots, 128 MB of original coordinate buffers. Object Mode, single-user meshes without shape keys. Not a .blend backup; lost on reload/exit.',
 'deform':'snapshot_id, center=[x,y,z], radius>0, displacement=[x,y,z], all WORLD units; smooth radial falloff. Applies to all snapshot targets. Base geometry only. Rejects intervening coordinate/topology/transform changes.',
 'compare':'snapshot_id. Reports world-space displacement relative to snapshot and whether camera/frame match. Does not assess artistic quality. Use look(mode="camera") before/after with the same camera for images.',
 'restore':'snapshot_id. Restores original vertex coordinates only; refuses to overwrite intervening edits. Does not restore materials, modifiers, object transforms or the entire scene.',
 'list':'List current in-memory snapshots.',
 'discard':'snapshot_id. Frees this snapshot without modifying geometry.'
}

def _coords(mesh):
 values=array('f',[0.0])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',values);return values

def _digest(o):
 me=o.data;loops=array('i',[0])*len(me.loops);me.loops.foreach_get('vertex_index',loops)
 edges=array('i',[0])*(len(me.edges)*2);me.edges.foreach_get('vertices',edges)
 faces=array('i',[0])*len(me.polygons);me.polygons.foreach_get('loop_total',faces)
 return hashlib.sha256(_coords(me).tobytes()+loops.tobytes()+edges.tobytes()+faces.tobytes()+repr(list(o.matrix_world)).encode()).hexdigest()

def _view():
 s=bpy.context.scene;c=s.camera
 return {'frame':s.frame_current,'camera':c.name if c else None,'matrix':list(map(list,c.matrix_world)) if c else None,'projection':[c.data.type,c.data.lens,c.data.ortho_scale,c.data.shift_x,c.data.shift_y,c.data.sensor_width,c.data.sensor_height,c.data.sensor_fit] if c else None,'resolution':[s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage,s.render.pixel_aspect_x,s.render.pixel_aspect_y]}

def _eligible(o):
 if o is None or o.type!='MESH':raise ValueError('Every target must be an existing mesh')
 if o.mode!='OBJECT':raise ValueError('Object Mode required')
 if o.data.users!=1 or o.data.shape_keys or o.library or o.data.library:raise ValueError('Use local single-user meshes without shape keys')
 if abs(o.matrix_world.to_3x3().determinant())<1e-12:raise ValueError('Non-invertible object transform')

def _vector(value,name):
 if not isinstance(value,(list,tuple)) or len(value)!=3 or not all(math.isfinite(float(v)) for v in value):raise ValueError(name+' requires three finite values')
 return Vector(value)

def run_edit(operation,names=None,options=None):
 p=options or {};names=names or []
 if operation not in CATALOG:raise ValueError('Unknown edit operation')
 states=bpy.app.driver_namespace.setdefault(KEY,{})
 if operation=='list':return [{'snapshot_id':key,'label':s['label'],'objects':list(s['objects'])} for key,s in states.items()]
 if operation=='snapshot':
  if not names or len(set(names))!=len(names):raise ValueError('Supply unique explicit mesh names')
  objects=[bpy.data.objects.get(name) for name in names]
  for o in objects:_eligible(o)
  used=sum(len(entry['original'])*4 for s in states.values() for entry in s['objects'].values())
  required=sum(len(o.data.vertices)*12 for o in objects)
  if len(states)>=4 or used+required>128*1024*1024:raise ValueError('Snapshot budget reached; discard an unused snapshot')
  rows={o.name:{'object':o,'mesh':o.data,'original':_coords(o.data),'last_hash':_digest(o),'matrix':o.matrix_world.copy()} for o in objects}
  identifier=uuid.uuid4().hex
  states[identifier]={'label':str(p.get('label','Geometry edit'))[:200],'objects':rows,'view':_view()}
  return {'snapshot_id':identifier,'objects':names,'coordinate_bytes':required,'scope':'base mesh vertex coordinates only','persistence':'memory; lost on file reload or Blender exit','view':states[identifier]['view']}
 identifier=p.get('snapshot_id');state=states.get(identifier)
 if state is None:raise ValueError('Snapshot not found in current Blender session')
 if names and names!=list(state['objects']):raise ValueError('Target names must match the snapshot order')
 if operation=='discard':del states[identifier];return {'snapshot_id':identifier,'discarded':True}
 # Preflight every target before writing any coordinates.
 for name,row in state['objects'].items():
  o=bpy.data.objects.get(name)
  _eligible(o)
  if o!=row['object'] or o.data!=row['mesh'] or _digest(o)!=row['last_hash']:raise ValueError('Intervening geometry or transform change on '+name+'; restore refused to preserve newer work')
 if operation=='compare':
  results=[]
  for name,row in state['objects'].items():
   now=_coords(row['mesh']);old=row['original'];matrix=row['matrix'].to_3x3();count=0;maximum=total=0.
   for i in range(0,len(now),3):
    distance=(matrix@Vector([now[i+k]-old[i+k] for k in range(3)])).length
    count+=distance>1e-7;maximum=max(maximum,distance);total+=distance*distance
   results.append({'object':name,'changed_vertices':count,'max_world_displacement':maximum,'rms_world_displacement':math.sqrt(total/max(1,len(now)//3))})
  return {'snapshot_id':identifier,'objects':results,'same_camera_and_frame':_view()==state['view'],'snapshot_view':state['view'],'distance_unit':'Blender world unit'}
 if operation=='deform':
  center=_vector(p.get('center'), 'center');delta=_vector(p.get('displacement'),'displacement')
  radius=float(p.get('radius',0))
  if not math.isfinite(radius) or radius<=0:raise ValueError('radius must be finite and positive')
  if delta.length>radius:raise ValueError('displacement must not exceed radius; use smaller inspected steps')
 before={name:_coords(row['mesh']) for name,row in state['objects'].items()};proposed={};changed={}
 for name,row in state['objects'].items():
  values=array('f',before[name]);count=0
  if operation=='restore':values=array('f',row['original']);count=sum(values[i:i+3]!=before[name][i:i+3] for i in range(0,len(values),3))
  else:
   o=row['object'];inv=o.matrix_world.inverted().to_3x3()
   for i in range(0,len(values),3):
    local=Vector(values[i:i+3]);distance=(o.matrix_world@local-center).length
    if distance>=radius:continue
    t=1-distance/radius;movement=inv@(delta*(t*t*(3-2*t)))
    for k in range(3):values[i+k]+=movement[k]
    count+=movement.length>1e-7
  proposed[name]=values;changed[name]=count
 try:
  for name,row in state['objects'].items():row['mesh'].vertices.foreach_set('co',proposed[name]);row['mesh'].update()
 except Exception:
  for name,row in state['objects'].items():row['mesh'].vertices.foreach_set('co',before[name]);row['mesh'].update()
  raise
 for row in state['objects'].values():row['last_hash']=_digest(row['object'])
 return {'snapshot_id':identifier,'operation':operation,'changed_vertices':changed,'scope':'base mesh vertex coordinates only'}
