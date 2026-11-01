import bpy,importlib.util,sys,os
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'test-output'
spec=importlib.util.spec_from_file_location('codex_test_addon',root/'assets/blender_mcp.py');addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon);addon.register()
bpy.context.scene.blendermcp_auto_start_server=False
server=addon.BlenderMCPServer(host='127.0.0.1',port=int(os.environ['CODEX_TEST_PORT']));server.start();assert server.running
(out/'mcp.ready').write_text(bpy.app.version_string)
def stop():
 if (out/'mcp.stop').exists():server.stop();bpy.ops.wm.quit_blender();return None
 return .2
bpy.app.timers.register(stop,first_interval=.2)
