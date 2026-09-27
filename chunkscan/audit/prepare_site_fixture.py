"""Prepare a separate expanded-park registry for offline integration diagnostics only."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.park_anchor import envelope

source = ROOT / 'chunkscan/build/audit/autonomy/snapshot'
destination = ROOT / 'chunkscan/build/audit/site-model'
destination.mkdir(parents=True, exist_ok=True)
env = envelope(schem_dir=source)
world = json.loads((ROOT / 'park_final.world.json').read_text(encoding='utf-8'))
anchor, bounds = world['site']['anchor'], world['site']['bounds']
assert env['x'] == [anchor[0] + bounds[0], anchor[0] + bounds[2]]
assert env['z'] == [anchor[2] + bounds[1], anchor[2] + bounds[3]]
registry = json.loads((source / 'islands.json').read_text(encoding='utf-8'))
for name, plot in env['plots'].items():
    registry['islands'][name]['site'] = 'park'
    registry['islands'][name]['bounds'] = {
        'min_x':plot['x'][0], 'min_z':plot['z'][0],
        'max_x_exclusive':plot['x'][1]+1, 'max_z_exclusive':plot['z'][1]+1}
(destination / 'islands.json').write_text(json.dumps(registry, indent=2), encoding='utf-8')
for name in ['Park Complete.litematic', 'Park Complete.scan.json', 'storage.json', 'designs.json']:
    shutil.copyfile(source / name, destination / name)
print(json.dumps({'fixture':str(destination), 'plots':env['plots'],
    'islands_sha256':hashlib.sha256((destination/'islands.json').read_bytes()).hexdigest(),
    'game_profile_modified':False},indent=2))
