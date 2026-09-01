import yaml
from mcbuild import fluids
from mcbuild.gen import coaster
from mcbuild.gen.vertical import World
from mcbuild.gen.park import _Frame
cfg = yaml.safe_load(open("configs/log_flume.yaml"))
p = {**coaster.COASTER, **cfg["params"]}
w = World()
try: coaster._flume(w, p, None)
except Exception as e: print("(exp)", str(e)[:100])
cells={pos:n for pos,(n,_) in w.cells.items()}
srcs=[pos for pos,(n,pr) in w.cells.items() if n=="water" and pr.get("level","0")=="0"]
print("sources", len(srcs))
lv=fluids.spread(cells, srcs, max_steps=50000)
print("wet", len(lv))
s=sorted(srcs, key=lambda c:-c[1])[:3]
for c in s:
    print("src", c, "nbrs:", [(d, cells.get((c[0]+d[0],c[1],c[2]+d[1]))) for d in ((1,0),(-1,0),(0,1),(0,-1))], "below", cells.get((c[0],c[1]-1,c[2])))
