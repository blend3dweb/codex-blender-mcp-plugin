"""Live MCP test. Requires the prepared .venv and an interactive Blender-capable host."""
import asyncio,base64,json,os,subprocess,sys,time,argparse,shutil
from pathlib import Path
from datetime import timedelta
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
root=Path(__file__).resolve().parents[1];out=root/'test-output';out.mkdir(exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('--blender',default=os.environ.get('BLENDER_BIN') or shutil.which('blender'));parser.add_argument('--port',type=int,default=19877);args=parser.parse_args()
if not args.blender:parser.error('Specify --blender')
env={**os.environ,'CODEX_TEST_PORT':str(args.port),'BLENDER_PORT':str(args.port),'BLENDER_HOST':'127.0.0.1','BLENDER_MCP_DISABLE_TELEMETRY':'1'}
for name in ['mcp.ready','mcp.stop']:(out/name).unlink(missing_ok=True)
async def test():
 params=StdioServerParameters(command=sys.executable,args=[str(root/'scripts/serve.py')],env=env)
 async with stdio_client(params) as (read,write):
  async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=90)) as session:
   await session.initialize();names=[t.name for t in (await session.list_tools()).tools];assert {'edit_session','edit_capabilities','spatial_inspect'}<=set(names)
   checks=['new tools listed']
   async def call(name,arguments):
    r=await session.call_tool(name,arguments);body='\n'.join(c.text for c in r.content if c.type=='text')
    assert not r.isError and not body.lower().startswith(('error','failed')),body
    assert "isn't available here" not in body,body
    return r,body
   async def edit(op,options=None,objects=None):
    _,body=await call('edit_session',{'operation':op,'options':options or {},'objects':objects or []});return json.loads(body[body.index('{'):]) if op!='list' else body
   await call('edit_capabilities',{});checks.append('edit catalog accessible')
   await call('spatial_inspect',{'operation':'topology','objects':['Cube']});checks.append('spatial topology accessible')
   await call('execute_blender_code',{'code':"import bpy\nfrom mathutils import Vector\nc=bpy.context.scene.camera\nc.location=(5,-7,4)\nc.rotation_euler=(-c.location).to_track_quat('-Z','Y').to_euler()\nc.data.type='ORTHO'\nc.data.ortho_scale=5"})
   snap=await edit('snapshot',objects=['Cube']);sid=snap['snapshot_id'];checks.append('snapshot created')
   async def capture(filename):
    r,_=await call('look',{'mode':'camera','shading':'wireframe','max_size':800});images=[c for c in r.content if c.type=='image'];assert images
    (out/filename).write_bytes(base64.b64decode(images[0].data))
   await capture('before.png');checks.append('before image')
   await edit('deform',{'snapshot_id':sid,'center':[1,1,1],'radius':2,'displacement':[0,0,.6]})
   comparison=await edit('compare',{'snapshot_id':sid});assert comparison['objects'][0]['changed_vertices']>0 and comparison['same_camera_and_frame'];checks.append('local deform and fixed-view comparison')
   await capture('after.png');checks.append('after image')
   await edit('restore',{'snapshot_id':sid});comparison=await edit('compare',{'snapshot_id':sid});assert comparison['objects'][0]['changed_vertices']==0;checks.append('exact restore')
   await call('execute_blender_code',{'code':"import bpy\nbpy.data.objects['Cube'].data.vertices[0].co.x+=.1"})
   r=await session.call_tool('edit_session',{'operation':'restore','options':{'snapshot_id':sid}});body='\n'.join(c.text for c in r.content if c.type=='text');assert 'Intervening geometry' in body;checks.append('external edit protected')
   await edit('discard',{'snapshot_id':sid});checks.append('snapshot discarded')
   (out/'mcp-results.json').write_text(json.dumps({'blender':(out/'mcp.ready').read_text(),'tools':names,'checks':checks},indent=2));print('MCP_CHECKS_PASSED',len(checks))
startup=None
if os.name=='nt':
 startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=subprocess.SW_HIDE
with (out/'blender-mcp.log').open('w',encoding='utf-8') as log:
 proc=subprocess.Popen([args.blender,'--factory-startup','--no-splash','--python',str(root/'tests/mcp_bootstrap.py')],env=env,startupinfo=startup,stdout=log,stderr=subprocess.STDOUT)
 try:
  deadline=time.monotonic()+60
  while not (out/'mcp.ready').exists():
   if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Test Blender did not start; see test-output/blender-mcp.log')
   time.sleep(.2)
  asyncio.run(asyncio.wait_for(test(),timeout=180))
 finally:
  (out/'mcp.stop').touch()
  try:proc.wait(timeout=15)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
