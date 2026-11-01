"""Read-only world-space geometry queries, executed within Blender."""
import bpy
import math
import hashlib
from array import array
from contextlib import contextmanager
from mathutils import Vector
from mathutils.bvhtree import BVHTree

CATALOG = {
 'topology': 'One mesh. evaluated=true; component_limit=20 (max 100). Counts connected components, boundary/nonmanifold/loose edges and degenerate faces. Does NOT test self-intersection.',
 'elements': 'One mesh. evaluated=true; kind=vertices|edges|faces; offset=0; limit=100 (max 500); optional indices=[...], expected_hash. Returns world positions/normals, connectivity and base selection flags. Evaluated indices are NOT editable base-mesh indices.',
 'section': 'One mesh. origin=[x,y,z], normal=[x,y,z], limit=500 (max 2000). Intersects evaluated triangles with a world-space plane; reports coplanar triangles separately. Returns segments, not ordered contours.',
 'proximity': 'Two meshes: source then target. samples=1000 (max 5000). Samples source vertices against target surface, unsigned distances only. Positive minimum does NOT prove separation; zero does NOT prove attachment or penetration.',
 'project': 'One mesh. camera=object name; landmarks=[{vertex:int, uv:[u,v]}], max 100; evaluated=false by default; expected_hash optional. uv normalized, origin TOP LEFT. Returns projected coordinates, pixel residuals at configured render resolution. Does not infer landmarks or depth from photos.',
}

def integer(p,k,default,lo,hi):
 v=p.get(k,default)
 if isinstance(v,bool) or not isinstance(v,int) or not lo<=v<=hi:raise ValueError(f'{k} must be an integer in {lo}..{hi}')
 return v

def vec(value):
 if not isinstance(value,(list,tuple)) or len(value)!=3 or not all(math.isfinite(float(x)) for x in value):raise ValueError('Expected three finite world coordinates')
 return Vector(value)

@contextmanager
def snapshot(name,evaluated):
 o=bpy.data.objects.get(name)
 if o is None or o.type!='MESH':raise ValueError('Mesh not found: '+name)
 if o.mode!='OBJECT':raise ValueError('Switch target to Object Mode to obtain a consistent geometry snapshot')
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else None
 me=ev.to_mesh() if ev else o.data
 try:
  if len(me.vertices)>2000000 or len(me.polygons)>2000000:raise ValueError('Query budget: use a lower-resolution mesh (max 2 million vertices/faces)')
  coords=array('f',[0.0])*(len(me.vertices)*3);me.vertices.foreach_get('co',coords)
  indices=array('i',[0])*len(me.loops);me.loops.foreach_get('vertex_index',indices)
  edges=array('i',[0])*(len(me.edges)*2);me.edges.foreach_get('vertices',edges)
  digest=hashlib.sha256(coords.tobytes()+indices.tobytes()+edges.tobytes()+repr(list(o.matrix_world)).encode()).hexdigest()
  verts=[o.matrix_world@v.co for v in me.vertices]
  yield o,me,verts,{'object':name,'evaluated':evaluated,'index_space':'evaluated_snapshot' if evaluated else 'base_mesh','geometry_hash':digest,'frame':bpy.context.scene.frame_current,'coordinate_space':'WORLD','distance_unit':'Blender world unit','meters_per_unit':bpy.context.scene.unit_settings.scale_length}
 finally:
  if ev:ev.to_mesh_clear()

def run_spatial(operation,names,options=None):
 p=options or {}
 if operation not in CATALOG:raise ValueError('Unknown spatial operation: '+operation)
 if len(names)!=(2 if operation=='proximity' else 1):raise ValueError('Supply exactly two meshes for proximity, one for other operations')
 evaluated=p.get('evaluated',operation!='project')
 if not isinstance(evaluated,bool):raise ValueError('evaluated must be boolean')
 with snapshot(names[0],evaluated) as (o,me,verts,meta):
  if p.get('expected_hash') is not None and p['expected_hash']!=meta['geometry_hash']:raise ValueError('Stale geometry hash: inspect again before using vertex indices')
  if operation=='topology':
   parent=list(range(len(verts)))
   def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
   degree=[0]*len(verts);usage=[0]*len(me.edges)
   for e in me.edges:
    a,b=e.vertices;degree[a]+=1;degree[b]+=1;a,b=find(a),find(b)
    if a!=b:parent[b]=a
   degenerate=0
   for face in me.polygons:
    if face.area<1e-12:degenerate+=1
    for idx in face.loop_indices:usage[me.loops[idx].edge_index]+=1
   groups={}
   for i in range(len(verts)):
    root=find(i)
    if root not in groups:groups[root]={'vertices':0,'sample_vertex':i,'min':list(verts[i]),'max':list(verts[i])}
    g=groups[root];g['vertices']+=1
    for k in range(3):g['min'][k]=min(g['min'][k],verts[i][k]);g['max'][k]=max(g['max'][k],verts[i][k])
   ordered=sorted(groups.values(),key=lambda x:x['vertices'],reverse=True);limit=integer(p,'component_limit',20,1,100)
   return {**meta,'vertices':len(verts),'edges':len(me.edges),'faces':len(me.polygons),'connected_components':len(groups),'components':ordered[:limit],'components_truncated':len(groups)>limit,'boundary_edges':usage.count(1),'nonmanifold_edges':sum(x!=2 for x in usage),'loose_edges':usage.count(0),'isolated_vertices':degree.count(0),'degenerate_faces':degenerate,'self_intersections':'not tested'}
  if operation=='elements':
   kind=p.get('kind','vertices')
   if kind not in {'vertices','edges','faces'}:raise ValueError('kind must be vertices, edges or faces')
   data={'vertices':me.vertices,'edges':me.edges,'faces':me.polygons}[kind];limit=integer(p,'limit',100,1,500);offset=integer(p,'offset',0,0,len(data))
   ids=p.get('indices',list(range(offset,min(offset+limit,len(data)))))
   if not isinstance(ids,list) or len(ids)>500 or any(type(i)!=int or i<0 or i>=len(data) for i in ids):raise ValueError('Invalid element indices (max 500)')
   nmat=o.matrix_world.to_3x3().inverted_safe().transposed();rows=[]
   for i in ids:
    item=data[i];row={'index':i,'selected':bool(item.select) if not evaluated else None}
    if kind=='vertices':row.update(position=list(verts[i]),normal=list((nmat@item.normal).normalized()))
    else:
     row['vertices']=list(item.vertices);row['positions']=[list(verts[j]) for j in item.vertices]
     if kind=='faces':row['normal']=list((nmat@item.normal).normalized())
    rows.append(row)
   return {**meta,'kind':kind,'total':len(data),'elements':rows,'next_offset':min(offset+limit,len(data)) if 'indices' not in p and offset+limit<len(data) else None}
  if operation=='section':
   origin=vec(p.get('origin',[0,0,0]));normal=vec(p.get('normal',[0,0,1]));limit=integer(p,'limit',500,1,2000)
   if normal.length<1e-12:raise ValueError('Plane normal cannot be zero')
   normal.normalize();me.calc_loop_triangles();segments=[];total=0;coplanar=0;eps=1e-7
   for tri in me.loop_triangles:
    ps=[verts[i] for i in tri.vertices];ds=[(v-origin).dot(normal) for v in ps]
    if all(abs(d)<eps for d in ds):coplanar+=1;continue
    hits=[]
    for i in range(3):
     j=(i+1)%3
     if abs(ds[i])<eps:hits.append(ps[i])
     if ds[i]*ds[j]<0:hits.append(ps[i].lerp(ps[j],ds[i]/(ds[i]-ds[j])))
    unique=[]
    for point in hits:
     if all((point-q).length>eps for q in unique):unique.append(point)
    if len(unique)==2:
     total+=1
     if len(segments)<limit:segments.append([list(v) for v in unique])
   return {**meta,'origin':list(origin),'normal':list(normal),'segments':segments,'total_segments':total,'truncated':total>limit,'coplanar_triangles_skipped':coplanar}
  if operation=='proximity':
   samples=integer(p,'samples',1000,1,5000)
   if not verts:raise ValueError('Source mesh is empty')
   with snapshot(names[1],evaluated) as (_,target,tverts,tmeta):
    if not target.polygons:raise ValueError('Target has no surface')
    tree=BVHTree.FromPolygons(tverts,[tuple(f.vertices) for f in target.polygons]);count=min(samples,len(verts));ids=[i*len(verts)//count for i in range(count)];hits=[]
    for i in ids:
     pos,n,face,d=tree.find_nearest(verts[i]);hits.append((d,i,pos,face))
    best=min(hits,key=lambda row:row[0])
    return {**meta,'target':tmeta,'sample_count':count,'source_vertex_count':len(verts),'sampled_min_distance':best[0],'sampled_max_distance':max(row[0] for row in hits),'sampled_mean_distance':sum(row[0] for row in hits)/count,'closest_sample':{'vertex':best[1],'position':list(verts[best[1]]),'target_position':list(best[2]),'target_face':best[3]},'penetration':'not determined','warning':'Unsigned sampled vertex-to-surface distance; not a collision or attachment test.'}
  if operation=='project':
   from bpy_extras.object_utils import world_to_camera_view
   cam=bpy.data.objects.get(p.get('camera',''))
   if cam is None or cam.type!='CAMERA':raise ValueError('Explicit camera object is required')
   landmarks=p.get('landmarks',[])
   if not isinstance(landmarks,list) or not 1<=len(landmarks)<=100:raise ValueError('Provide 1..100 landmarks')
   s=bpy.context.scene;width=s.render.resolution_x*s.render.resolution_percentage/100;height=s.render.resolution_y*s.render.resolution_percentage/100;rows=[]
   for mark in landmarks:
    idx=mark.get('vertex');uv=mark.get('uv')
    if type(idx)!=int or not 0<=idx<len(verts):raise ValueError('Invalid landmark vertex')
    if not isinstance(uv,list) or len(uv)!=2 or not all(math.isfinite(float(v)) and 0<=float(v)<=1 for v in uv):raise ValueError('uv must contain two values within 0..1')
    co=world_to_camera_view(s,cam,verts[idx]);u,v=co.x,1-co.y;err=math.hypot((u-uv[0])*width,(v-uv[1])*height)
    rows.append({'vertex':idx,'projected_uv':[u,v],'reference_uv':uv,'depth':co.z,'in_front':co.z>0,'inside_frame':co.z>0 and 0<=u<=1 and 0<=v<=1,'error_pixels':err if co.z>0 else None})
   valid=[r['error_pixels'] for r in rows if r['error_pixels'] is not None]
   return {**meta,'camera':cam.name,'image_size':[width,height],'uv_origin':'top_left','landmarks':rows,'rms_pixels':math.sqrt(sum(v*v for v in valid)/len(valid)) if valid else None,'excluded_behind_camera':len(rows)-len(valid)}
