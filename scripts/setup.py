"""Prepare a private runtime; register Codex only with --register-codex."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]

def register(python, name):
    codex = shutil.which('codex.exe') or shutil.which('codex')
    if not codex:
        raise RuntimeError('Codex CLI not found. Use codex-mcp.toml in your MCP settings.')
    existing = subprocess.run([codex, 'mcp', 'list', '--json'], check=True,
                              capture_output=True, text=True, encoding='utf-8')
    entries = json.loads(existing.stdout)
    if any(item.get('name') == name for item in entries):
        raise RuntimeError(f'MCP entry {name!r} already exists; no settings changed. Choose --name.')
    config_root = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    config = config_root / 'config.toml'
    if config.exists():
        suffix = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup = config.with_name(f'config.toml.blender-{suffix}.bak')
        shutil.copy2(config, backup)
        print(f'Config backup: {backup}')
    subprocess.run([codex, 'mcp', 'add', name,
                    '--env', 'BLENDER_MCP_DISABLE_TELEMETRY=1',
                    '--env', 'BLENDER_HOST=127.0.0.1', '--env', 'BLENDER_PORT=9876',
                    '--', str(python), str(ROOT / 'scripts' / 'serve.py')], check=True)
    print('Codex configured. Restart Codex to load the new MCP tools.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--register-codex', action='store_true')
    parser.add_argument('--name', default='codex-blender')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.name):
        parser.error('--name must contain only letters, digits, underscore or hyphen.')
    if sys.version_info < (3, 10):
        parser.error('Python 3.10 or newer is required.')
    runtime = Path(os.environ.get('PLUGIN_DATA', str(ROOT))) / '.venv'
    python = runtime / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(runtime)
    lock = ROOT / 'requirements.lock.txt'
    requirements = lock if lock.exists() else ROOT / 'requirements.txt'
    subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
                    '-r', str(requirements)], check=True)
    # JSON string escaping is compatible with these TOML basic strings/arrays.
    config = '\n'.join([
        f'[mcp_servers.{args.name}]',
        'command = ' + json.dumps(str(python)),
        'args = ' + json.dumps([str(ROOT / 'scripts' / 'serve.py')]),
        f'[mcp_servers.{args.name}.env]',
        'BLENDER_MCP_DISABLE_TELEMETRY = "1"',
        'BLENDER_HOST = "127.0.0.1"', 'BLENDER_PORT = "9876"', ''
    ])
    (ROOT / 'codex-mcp.toml').write_text(config, encoding='utf-8')
    print(f'Runtime ready: {python}')
    print('Blender: Preferences > Add-ons > Install from Disk > assets/blender_mcp.py')
    print('Enable MCP for Blender. N > MCP for Blender > Start MCP Server.')
    if args.register_codex:
        register(python, args.name)
    else:
        print('Global Codex settings unchanged. To register, run again with --register-codex.')
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'Setup failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
