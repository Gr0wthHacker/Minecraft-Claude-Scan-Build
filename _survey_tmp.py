import yaml, pathlib, numpy as np
import importlib.util
spec = importlib.util.spec_from_file_location("t", "tests/test_park_entrance.py")
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
from mcbuild.gen import park_entrance as PE
from mcbuild import schem
p = T._params(); c = PE.build(p); m = c.to_model(); meta = c.meta
mm = schem.load(str(T.PARK)); ox,oy,oz = T.PARK_ORIGIN
names=[n.split(':')[-1].split('[')[0] for n in mm.names]
lo,hi = T.Y_BAND[0]-oy, T.Y_BAND[1]-oy+1
sub = mm.ids[lo:hi]
world={}
for y,z,x in np.argwhere(sub>0):
    world[(int(x)+ox,int(y)+lo+oy,int(z)+oz)] = names[sub[y,z,x]]
base_stand,_ = T._standable(world)
mine = T._named(m, c.world_origin)
w2 = dict(world); w2.update(mine)
stand, solid = T._standable(w2)
start = tuple(meta['spawn']['world'])
reached = T._flood(stand, solid, start)
print('spawn', start)
print('reachable cells with doors SHUT:', len(reached))
vs = sorted({p[0]-PE.ANCHOR[0] for p in reached}); us = sorted({p[2]-PE.ANCHOR[2] for p in reached})
print('  V range', vs[0], '..', vs[-1], ' U range', us[0], '..', us[-1])
# open doors
m2 = {k:v for k,v in mine.items() if v!='iron_door'}
w3 = dict(world); w3.update(m2)
st3, so3 = T._standable(w3)
r3 = T._flood(st3, so3, start)
us3 = sorted({p[2]-PE.ANCHOR[2] for p in r3}); vs3=sorted({p[0]-PE.ANCHOR[0] for p in r3})
print('reachable cells with doors OPEN:', len(r3), 'V', vs3[0],'..',vs3[-1], 'U', us3[0],'..',us3[-1])
print('  frontier cells reached:', sum(1 for q in r3 if q[2]-PE.ANCHOR[2] <= 169))
print('  prismworks cells reached:', sum(1 for q in r3 if q[2]-PE.ANCHOR[2] >= 430))
# without the design at all
r0 = T._flood(base_stand, {q for q,n in world.items() if not T.passable(n)}, start)
print('reachable with NO gate at all:', len(r0))
print('  frontier:', sum(1 for q in r0 if q[2]-PE.ANCHOR[2] <= 169), ' prismworks:', sum(1 for q in r0 if q[2]-PE.ANCHOR[2] >= 430))
