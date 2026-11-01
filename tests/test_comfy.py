"""Offline bridge contract tests; no model, GPU, network or Blender required."""
import json
import os
import struct
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch, AsyncMock

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import comfy_tools as bridge


class Registry:
    def __init__(self):
        self.mcp = self
        self.functions = {}
        self.execute_blender_code = AsyncMock(return_value='imported')

    def tool(self):
        def wrap(fn):
            self.functions[fn.__name__] = fn
            return fn
        return wrap


class BridgeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.registry = Registry()
        bridge.register(self.registry)
        self.calls = []
        self.prompt_id = str(uuid.uuid4())
        self.info = {node['class_type']: {} for node in bridge.workflow('x', 'model').values()}
        self.info['ImageOnlyCheckpointLoader'] = {'input': {'required': {'ckpt_name': [['model']]}}}
        self.record = {}
        self.queue = {'queue_running': [], 'queue_pending': []}
        self.glb = struct.pack('<4sIIII', b'glTF', 2, 20, 0, 0x4e4f534a)
        self.env = patch.dict(os.environ, {'COMFYUI_URL': 'http://127.0.0.1:8188'})
        self.env.start()
        self.transport = patch.object(bridge, 'client', lambda: httpx.AsyncClient(transport=httpx.MockTransport(self.handle)))
        self.transport.start()

    def tearDown(self):
        self.transport.stop()
        self.env.stop()

    def handle(self, request):
        self.calls.append(request)
        path = request.url.path
        if path == '/object_info':
            return httpx.Response(200, json=self.info)
        if path == '/upload/image':
            return httpx.Response(200, json={'name': 'uploaded.png', 'subfolder': ''})
        if path == '/prompt':
            return httpx.Response(200, json={'prompt_id': self.prompt_id})
        if path.startswith('/history/'):
            return httpx.Response(200, json=self.record)
        if path == '/queue':
            return httpx.Response(200, json=self.queue)
        if path == '/view':
            return httpx.Response(200, content=self.glb)
        return httpx.Response(503, text='unavailable')

    def test_endpoint_restrictions(self):
        for url in ['https://example.org', 'http://127.0.0.1.evil', 'http://user@localhost', 'http://localhost/path']:
            with patch.dict(os.environ, {'COMFYUI_URL': url}), self.assertRaises(ValueError):
                bridge.endpoint()

    def test_workflow_bounds(self):
        for args in [(-1, 20, 192), (0, 51, 192), (0, 20, 512)]:
            with self.assertRaises(ValueError):
                bridge.workflow('x', 'model', *args)

    def test_guidance_bounds(self):
        for value in (0, 11, float('nan')):
            with self.assertRaises(ValueError):
                bridge.workflow('x', 'model', guidance=value)
        self.assertEqual(bridge.workflow('x', 'model', guidance=5.5)['6']['inputs']['cfg'], 5.5)

    async def test_submit_image_and_graph(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / 'image.png'
            image.write_bytes(b'test')
            result = await self.registry.functions['comfy_generate'](str(image), 'model')
        self.assertEqual(json.loads(result)['prompt_id'], self.prompt_id)
        graph = json.loads(self.calls[-1].content)['prompt']
        self.assertEqual(graph['2']['inputs']['image'], 'uploaded.png')
        self.assertEqual(graph['9']['class_type'], 'SaveGLB')

    async def test_missing_model_does_not_submit(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / 'image.png'
            image.write_bytes(b'test')
            with self.assertRaises(ValueError):
                await self.registry.functions['comfy_generate'](str(image), 'absent')
        self.assertEqual(len(self.calls), 1)

    async def test_states_and_failure(self):
        async with bridge.client() as http:
            self.assertEqual((await bridge.history(http, self.prompt_id))['state'], 'unknown')
            self.queue['queue_pending'] = [[1, self.prompt_id]]
            self.assertEqual((await bridge.history(http, self.prompt_id))['state'], 'queued')
            self.queue = {'queue_running': [[1, self.prompt_id]]}
            self.assertEqual((await bridge.history(http, self.prompt_id))['state'], 'running')
            self.record = {self.prompt_id: {'status': {'status_str': 'error', 'messages': ['oom']}}}
            self.assertEqual((await bridge.history(http, self.prompt_id))['state'], 'failed')

    async def test_import_only_completed_glb(self):
        self.record = {self.prompt_id: {'status': {'completed': True}, 'outputs': {'9': {'3d': [
            {'filename': 'dragon.glb', 'subfolder': 'codex', 'type': 'output'}]}}}}
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'PLUGIN_DATA': folder}):
            await self.registry.functions['comfy_import'](None, self.prompt_id)
            self.assertEqual(len(list(Path(folder).rglob('*.glb'))), 1)
            code = self.registry.execute_blender_code.call_args.kwargs['code']
            compile(code, '<blender-import>', 'exec')
            self.assertIn('already_imported', code)
        self.registry.execute_blender_code.reset_mock()
        self.glb = b'not a GLB'
        with self.assertRaises(ValueError):
            await self.registry.functions['comfy_import'](None, self.prompt_id)
        self.registry.execute_blender_code.assert_not_called()

    async def test_running_cannot_import(self):
        self.queue = {'queue_running': [[1, self.prompt_id]]}
        with self.assertRaises(ValueError):
            await self.registry.functions['comfy_import'](None, self.prompt_id)
        self.registry.execute_blender_code.assert_not_called()

    async def test_http_errors_are_visible(self):
        with self.assertRaisesRegex(RuntimeError, '503'):
            await self.registry.functions['comfy_status']()


if __name__ == '__main__':
    unittest.main()
