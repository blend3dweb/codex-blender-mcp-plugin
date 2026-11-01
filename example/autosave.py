"""Execute in Blender with EXAMPLE_ROOT set to an absolute local project folder.

Saves only the active project file, in Object Mode, with ten rotating copies.
The timer is session-local: rerun after restarting Blender. No auto-executed .blend text.
"""
import bpy
import json
from datetime import datetime, timezone
from pathlib import Path

_KEY = 'codex_example_autosave'


def install_example_autosave(root, interval=120):
    root = Path(root).resolve()
    current = root / 'current.blend'
    if Path(bpy.data.filepath).resolve() != current:
        raise ValueError('Save the intended scene as EXAMPLE_ROOT/current.blend first')
    if interval < 30:
        raise ValueError('Autosave interval must be at least 30 seconds')
    previous = bpy.app.driver_namespace.get(_KEY)
    if previous and bpy.app.timers.is_registered(previous['callback']):
        bpy.app.timers.unregister(previous['callback'])
    folder = root / 'autosave'
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / 'owner.json'
    if marker.exists():
        owner = json.loads(marker.read_text(encoding='utf-8'))
        if owner.get('owner') != _KEY or owner.get('project') != str(root):
            raise ValueError('Autosave folder belongs to another project')
    elif any(folder.iterdir()):
        raise ValueError('Refusing to overwrite an unowned autosave folder')
    else:
        marker.write_text(json.dumps({'owner':_KEY, 'project':str(root)}), encoding='utf-8')
    state = {'project':str(root), 'interval_seconds':interval, 'saved':0,
             'last_saved':None, 'error':None}

    def save_tick(force=False):
        if Path(bpy.data.filepath).resolve() != current:
            return interval
        if bpy.context.mode != 'OBJECT' or bpy.context.window_manager.is_interface_locked:
            return interval
        if not force and not bpy.data.is_dirty:
            return interval
        try:
            # Resume rotation from the oldest of our ten files, including after reinstall.
            slots = [folder / f'slot-{i:02d}.blend' for i in range(10)]
            target = min(slots, key=lambda p:p.stat().st_mtime if p.exists() else -1)
            pending = folder / 'pending.blend'
            bpy.ops.wm.save_as_mainfile(filepath=str(pending), copy=True, check_existing=False)
            if not pending.is_file() or pending.stat().st_size == 0:
                raise RuntimeError('Blender did not create the autosave')
            pending.replace(target)
            state['saved'] += 1
            state['last_saved'] = str(target)
            state['saved_at_utc'] = datetime.now(timezone.utc).isoformat()
            state['error'] = None
        except Exception as exc:
            state['error'] = str(exc)
        (folder/'status.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
        return interval

    bpy.app.driver_namespace[_KEY] = {'callback':save_tick, 'state':state}
    bpy.app.timers.register(save_tick, first_interval=interval)
    return state


if 'EXAMPLE_ROOT' in globals():
    print(json.dumps(install_example_autosave(EXAMPLE_ROOT)))
