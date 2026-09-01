import yaml, sys
from mcbuild import circuit
from mcbuild.gen import arcade, casino
MODS = {'arcade': arcade, 'casino': casino}
cfgpath, cx, cy, cz, r = sys.argv[1], *map(int, sys.argv[2:6])
cfg = yaml.safe_load(open(cfgpath)); p = dict(cfg['params']); p.pop('under', None)
c = MODS[cfg['gen']].build(p)
m = c.to_model(); o = c.world_origin
sim = circuit.Circuit.of(m, o)
for y in range(cy-2, cy+3):
    print(f'--- y={y}')
    for z in range(cz-r, cz+r+1):
        row=[]
        for x in range(cx-r, cx+r+1):
            n = sim.name((x,y,z))
            n = {'air':'.'}.get(n, n)
            row.append(n[:14].ljust(14))
        print(f'z{z} ' + ''.join(row))
