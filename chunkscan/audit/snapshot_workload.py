"""Read-only autonomy audit snapshot. Run from repository root; no game files are changed."""
import collections
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from mcbuild import scan, nbt, work
import numpy as np

dest = ROOT / 'chunkscan/build/audit/autonomy/snapshot'
dest.mkdir(parents=True, exist_ok=True)
profile = pathlib.Path(sys.argv[1])
sources = [ROOT / 'out/Park Complete.litematic', ROOT / 'out/Park Complete.scan.json',
           profile / 'islands.json', profile / 'storage.json', profile / 'designs.json']
# Detect concurrent replacement during the read. This cannot prove the producer published
# a semantically matched pair; a release manifest is required for that stronger guarantee.
for attempt in range(4):
    blobs = {p: p.read_bytes() for p in sources}
    if all(p.read_bytes() == data for p, data in blobs.items()):
        break
else:
    raise RuntimeError('Audit inputs are changing; no stable snapshot obtained')
manifest = {}
for p, data in blobs.items():
    (dest / p.name).write_bytes(data)
    manifest[p.name] = {'source': str(p), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
s = scan.load(str(dest / 'Park Complete.litematic'))
counts = np.bincount(s.model.ids.ravel(), minlength=len(s.model.palette))
materials = collections.Counter()
derived = 0
for entry, count in zip(s.model.palette, counts):
    name = nbt.state_name(entry).split(':')[-1]
    if name in {'air', 'cave_air', 'void_air'}:
        continue
    materials[name] += int(count)
    props = nbt.state_props(entry)
    omitted = set(props) - work.INTENTIONAL
    if name in work.MULTIFACE:
        omitted -= work.FACES
    if omitted:
        derived += int(count)
result = {'manifest': manifest, 'size_xyz': list(s.size), 'nonair': sum(materials.values()),
          'volume': int(s.model.ids.size), 'origin': s.meta['origin'],
          'anchor_status': s.meta.get('anchor_status'), 'dig': len(s.meta.get('dig', [])),
          'palette_size': len(s.model.palette), 'cells_with_properties_omitted_by_python': derived,
          'materials': dict(materials.most_common())}
(dest.parent / 'workload.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in {'manifest', 'materials'}}, indent=2))
