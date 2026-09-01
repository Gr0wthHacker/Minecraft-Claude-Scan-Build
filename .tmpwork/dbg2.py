import yaml, sys
from mcbuild import circuit
from mcbuild.gen import arcade, casino

MODS = {'arcade': arcade, 'casino': casino}

def build(cfgpath):
    cfg = yaml.safe_load(open(cfgpath))
    p = dict(cfg['params'])
    p.pop('under', None)
    mod = MODS[cfg['gen']]
    return mod.build(p), p

for cfgpath in sys.argv[1:]:
    c, p = build(cfgpath)
    cells = {}
    for pos, (name, props) in c.world.cells.items() if hasattr(c,'world') else []:
        pass
    print(cfgpath, type(c), [a for a in dir(c) if not a.startswith('_')][:30])
