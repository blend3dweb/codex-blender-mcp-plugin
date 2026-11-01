"""Launch the bundled MCP server. stdout is reserved for MCP JSON-RPC."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')

def main():
    if not RUNTIME.is_file():
        print('Runtime missing. Run: python scripts/setup.py', file=sys.stderr)
        return 1
    if Path(sys.prefix).resolve() != (ROOT / '.venv').resolve():
        os.execv(str(RUNTIME), [str(RUNTIME), str(Path(__file__).resolve()), *sys.argv[1:]])
    # Disable upstream collection even if a surrounding process enables it.
    os.environ['BLENDER_MCP_DISABLE_TELEMETRY'] = '1'
    os.environ.setdefault('BLENDER_HOST', '127.0.0.1')
    os.environ.setdefault('BLENDER_PORT', '9876')
    # Keep local upstream state inside this package instead of the home folder.
    os.environ['APPDATA'] = str(ROOT / '.state')
    os.environ['XDG_CONFIG_HOME'] = str(ROOT / '.state')
    os.environ['XDG_DATA_HOME'] = str(ROOT / '.state')
    sys.path.insert(0, str(ROOT / 'vendor'))
    from blender_mcp import server
    from studio_tools import register
    register(server)
    from spatial_tools import register as register_spatial
    register_spatial(server)
    from edit_tools import register as register_edits
    register_edits(server)
    server.main()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
