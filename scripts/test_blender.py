"""Run geometry regressions in fresh factory-startup Blender processes."""
import argparse,subprocess,shutil,os,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--blender',default=os.environ.get('BLENDER_BIN') or shutil.which('blender'));args=parser.parse_args()
if not args.blender:parser.error('Specify --blender /path/to/blender or set BLENDER_BIN')
out=root/'test-output';out.mkdir(exist_ok=True)
for name in ['studio','spatial','edit']:
 with (out/(name+'.log')).open('w',encoding='utf-8') as log:
  subprocess.run([args.blender,'--background','--factory-startup','--python-exit-code','1','--python',str(root/'tests'/('test_'+name+'_ops.py'))],stdout=log,stderr=subprocess.STDOUT,check=True)
 report=json.loads((out/(name+'-results.json')).read_text());print(name+': '+str(len(report['checks']))+' checks passed')
