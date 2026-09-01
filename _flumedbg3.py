import yaml
from mcbuild import fluids
from mcbuild.gen import coaster
from mcbuild.gen.vertical import World
from mcbuild.gen.park import _Frame

cfg = yaml.safe_load(open("configs/log_flume.yaml"))
p = {**coaster.COASTER, **cfg["params"]}
w = World(); rep = coaster._flume(w, p, None)
cells = {pos: n for pos, (n,_) in w.cells.items()}
f = _Frame(p)
m,s,t,half,dock,run = coaster._flume_dims(p)
wps = coaster._flume_plan(p); pts, marks = coaster._trace(wps)
corners = coaster._corners(pts, False)
hs = coaster._profile(pts, marks, wps, corners)
print("plan", wps)
print("dims m,s,t,half,dock,run", m,s,t,half,dance if False else half, dock, run)
pool_i, pool_d = pts[-1][0], pts[-1][1]-1
print("pool centre local", pool_i, pool_d, "half", half)
pi0,pi1 = pool_i-half, pool_i+half
pd0,pd1 = pool_d-half-2, pool_d
print("pool local i", pi0, pi1, "d", pd0, pd1)
for i,d in ((pi0,pd0),(pi1,pd1)):
    print("  world corner", f.at(i,d,0))
# water cells by y
from collections import Counter
wat = [pos for pos,n in cells.items() if n=="water"]
print(Counter(c[1] for c in wat))
# check the pool ring at y=204
for i in range(pi0-1, pi1+2):
    for d in range(pd0-1, pd1+2):
        edge = i in (pi0-1,pi1+1) or d in (pd0-1,pd1+1)
        if not edge: continue
        pos = f.at(i,d,1)
        if not w.has(*pos):
            print("  RING GAP at", pos, i, d)
