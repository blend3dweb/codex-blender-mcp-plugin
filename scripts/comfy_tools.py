"""Local ComfyUI bridge. No model downloads, cloud calls or server startup."""
import hashlib
import json
import os
import struct
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from mcp.server.fastmcp import Context

ROOT = Path(__file__).resolve().parents[1]


def endpoint():
    value = os.environ.get('COMFYUI_URL', 'http://127.0.0.1:8188').rstrip('/')
    parsed = urlsplit(value)
    if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
            or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise ValueError('COMFYUI_URL must be a loopback HTTP origin, e.g. http://127.0.0.1:8188')
    return value


def workflow(image, checkpoint, seed=0, steps=20, resolution=192):
    if not 0 <= seed < 2**64 or not 1 <= steps <= 50 or resolution not in (128, 192, 256):
        raise ValueError('seed: uint64; steps: 1..50; resolution: 128, 192 or 256')
    def node(name, **inputs):
        return {'class_type': name, 'inputs': inputs}
    return {
        '1': node('ImageOnlyCheckpointLoader', ckpt_name=checkpoint),
        '2': node('LoadImage', image=image),
        '3': node('CLIPVisionEncode', clip_vision=['1', 1], image=['2', 0], crop='none'),
        '4': node('Hunyuan3Dv2Conditioning', clip_vision_output=['3', 0]),
        '5': node('EmptyLatentHunyuan3Dv2', resolution=3072, batch_size=1),
        '10': node('ModelSamplingAuraFlow', model=['1', 0], shift=1.0),
        '6': node('KSampler', model=['10', 0], positive=['4', 0], negative=['4', 1],
                  latent_image=['5', 0], seed=seed, steps=steps, cfg=1.0,
                  sampler_name='euler', scheduler='normal', denoise=1.0),
        '7': node('VAEDecodeHunyuan3D', samples=['6', 0], vae=['1', 2],
                  num_chunks=4000, octree_resolution=resolution),
        '8': node('VoxelToMesh', voxel=['7', 0], algorithm='surface net', threshold=0.6),
        '9': node('SaveGLB', mesh=['8', 0], filename_prefix='codex/hunyuan'),
    }


async def request(client, method, path, **kwargs):
    response = await client.request(method, endpoint() + path, **kwargs)
    if response.is_error:
        raise RuntimeError(f'ComfyUI HTTP {response.status_code}: {response.text[:2000]}')
    return response.json()


def client():
    return httpx.AsyncClient(timeout=30, trust_env=False, follow_redirects=False)


async def history(http, prompt_id):
    prompt_id = str(uuid.UUID(prompt_id))
    records = await request(http, 'GET', '/history/' + prompt_id)
    record = records.get(prompt_id)
    if record:
        status = record.get('status', {})
        if status.get('status_str') == 'error':
            return {'state': 'failed', 'details': status.get('messages', [])}
        if status.get('completed'):
            files = []
            for output in record.get('outputs', {}).values():
                for entries in output.values():
                    if isinstance(entries, list):
                        files.extend(e for e in entries if isinstance(e, dict)
                                     and str(e.get('filename', '')).lower().endswith('.glb')
                                     and e.get('type') == 'output')
            return {'state': 'completed', 'files': files}
    queue = await request(http, 'GET', '/queue')
    for key, state in [('queue_running', 'running'), ('queue_pending', 'queued')]:
        if any(len(row) > 1 and row[1] == prompt_id for row in queue.get(key, [])):
            return {'state': state}
    return {'state': 'unknown', 'note': 'No queue/history entry; server may have restarted. Do not resubmit automatically.'}


def validate_glb(data):
    if len(data) < 20:
        raise ValueError('Truncated GLB')
    magic, version, length = struct.unpack('<4sII', data[:12])
    if magic != b'glTF' or version != 2 or length != len(data):
        raise ValueError('Invalid GLB header or length')


def register(server):
    @server.mcp.tool()
    async def comfy_status() -> str:
        """Inspect local ComfyUI, Hunyuan3D node availability and installed checkpoints. Does not start services."""
        async with client() as http:
            stats = await request(http, 'GET', '/system_stats')
            info = await request(http, 'GET', '/object_info')
        needed = {n['class_type'] for n in workflow('image.png', 'model').values()}
        checkpoints = info.get('ImageOnlyCheckpointLoader', {}).get('input', {}).get('required', {}).get('ckpt_name', [[]])[0]
        return json.dumps({'endpoint': endpoint(), 'system': stats,
                           'missing_nodes': sorted(needed - info.keys()), 'checkpoints': checkpoints})

    @server.mcp.tool()
    async def comfy_generate(image_path: str, checkpoint: str = 'hunyuan3d-dit-v2.safetensors',
                             seed: int = 0, steps: int = 20, resolution: int = 192) -> str:
        """Upload a local PNG/JPEG and queue Hunyuan3D 2.0 geometry only. Use an isolated subject on a plain background. Returns prompt_id; poll comfy_job. No automatic retry: submission timeouts may still have queued work. Requires installed weights; no textures, rig or guaranteed likeness."""
        path = Path(image_path)
        if path.suffix.lower() not in ('.png', '.jpg', '.jpeg') or not path.is_file():
            raise ValueError('Expected an existing PNG/JPEG')
        if path.stat().st_size > 20 * 1024**2:
            raise ValueError('Image limit: 20 MiB')
        graph = workflow('pending.png', checkpoint, seed, steps, resolution)
        async with client() as http:
            info = await request(http, 'GET', '/object_info')
            missing = {n['class_type'] for n in graph.values()} - info.keys()
            if missing:
                raise ValueError('Missing ComfyUI nodes: ' + ', '.join(sorted(missing)))
            choices = info['ImageOnlyCheckpointLoader']['input']['required']['ckpt_name'][0]
            if checkpoint not in choices:
                raise ValueError('Checkpoint not installed: ' + checkpoint)
            filename = 'codex-' + uuid.uuid4().hex + path.suffix.lower()
            uploaded = await request(http, 'POST', '/upload/image',
                                     files={'image': (filename, path.read_bytes())}, data={'overwrite': 'false'})
            graph['2']['inputs']['image'] = '/'.join(filter(None, [uploaded.get('subfolder'), uploaded['name']]))
            result = await request(http, 'POST', '/prompt', json={'prompt': graph, 'client_id': str(uuid.uuid4())})
        return json.dumps(result)

    @server.mcp.tool()
    async def comfy_job(prompt_id: str) -> str:
        """Read queued/running/completed/failed/unknown state without blocking for generation."""
        async with client() as http:
            return json.dumps(await history(http, prompt_id))

    @server.mcp.tool()
    async def comfy_import(ctx: Context, prompt_id: str, file_index: int = 0) -> str:
        """Download a completed job's GLB to plugin data and import into current Blender scene. Preserves existing objects; repeat imports of identical bytes are skipped. Inspect scene first and review with look afterward. Does not save or replace the .blend."""
        async with client() as http:
            result = await history(http, prompt_id)
            if result['state'] != 'completed':
                raise ValueError('Job is not completed: ' + result['state'])
            if not 0 <= file_index < len(result['files']):
                raise ValueError('No GLB at requested file index')
            entry = result['files'][file_index]
            params = {k: entry.get(k, '') for k in ('filename', 'subfolder', 'type')}
            data = bytearray()
            async with http.stream('GET', endpoint() + '/view', params=params) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 256 * 1024**2:
                        raise ValueError('GLB exceeds 256 MiB')
        validate_glb(data)
        digest = hashlib.sha256(data).hexdigest()
        folder = Path(os.environ.get('PLUGIN_DATA', str(ROOT))) / '.state' / 'comfy' / 'models'
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / (digest + '.glb')
        target.write_bytes(data)
        code = f'''import bpy, json
digest = {digest!r}
existing = [o.name for o in bpy.data.objects if o.get('codex_comfy_sha256') == digest]
if existing:
    print(json.dumps({{'already_imported': existing}}))
else:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath={str(target)!r})
    added = [o for o in bpy.data.objects if o not in before]
    for o in added:
        o['codex_comfy_sha256'] = digest
    print(json.dumps({{'imported': [o.name for o in added], 'source': {str(target)!r}}}))
'''
        return await server.execute_blender_code(ctx=ctx, code=code)
