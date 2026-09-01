import yaml, sys, traceback
from mcbuild import circuit
from mcbuild.gen import arcade, casino
from mcbuild.gen.vertical import World

MODS = {'arcade': arcade, 'casino': casino}
TARGETS = set()
LOG = {}

orig_put = World.put
def put(self, x, y, z, name, **props):
    if (x,y,z) in TARGETS:
        st = traceback.extract_stack()[-6:-1]
        LOG.setdefault((x,y,z), []).append((name, [f"{f.name}:{f.lineno}" for f in st]))
    return orig_put(self, x, y, z, name, **props)
World.put = put

cfgpath, *coords = sys.argv[1:]
for c in coords:
    TARGETS.add(tuple(int(v) for v in c.split(',')))
cfg = yaml.safe_load(open(cfgpath))
p = dict(cfg['params']); p.pop('under', None)
MODS[cfg['gen']].build(p)
for k, v in LOG.items():
    print(k)
    for name, st in v:
        print('   ', name, ' <- ', ' | '.join(st))
