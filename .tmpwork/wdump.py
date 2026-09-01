import yaml, sys
from mcbuild import circuit
from mcbuild.gen import casino
cfg = yaml.safe_load(open(sys.argv[1])); p=dict(cfg['params']); p.pop('under',None)
c = casino.build(p)
m=c.to_model(); o=c.world_origin
s=circuit.Circuit.of(m,o)
cx,cy,cz,r = map(int, sys.argv[2:6])
for y in (cy-1,cy,cy+1):
    print('--- y',y)
    for z in range(cz-r,cz+r+1):
        print(f'z{z} ' + ''.join((s.name((x,y,z)) or 'air')[:13].ljust(13) for x in range(cx-r,cx+r+1)))
