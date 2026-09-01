import yaml, sys
from mcbuild import circuit
from mcbuild.gen import arcade, casino

MODS = {'arcade': arcade, 'casino': casino}

def build(cfgpath):
    cfg = yaml.safe_load(open(cfgpath))
    p = dict(cfg['params']); p.pop('under', None)
    return MODS[cfg['gen']].build(p), p

for cfgpath in sys.argv[1:]:
    c, p = build(cfgpath)
    m = c.to_model()
    o = c.world_origin
    sim = circuit.Circuit.of(m, o)
    f = circuit.inspect(m, o)
    print(f'=== {cfgpath}  origin={o} facing={p["facing"]} at={p["at"]}')
    print('    meta:', {k:v for k,v in c.meta.items() if k in ('kind','footprint','contract')})
    for k, pos, d in f:
        if k == 'quasi-connectivity': continue
        print(f'  [{k}] {pos} = {sim.name(pos)} {sim.at(pos).props if sim.at(pos) else ""}')
        for dd, nb in sim.neighbours(pos):
            print(f'        {dd:6s} {nb} {sim.name(nb)}')
