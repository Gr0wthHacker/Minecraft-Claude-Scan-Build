import yaml
from mcbuild import fluids
from mcbuild.gen import coaster
from mcbuild.gen.vertical import World
from mcbuild.gen.park import _Frame

cfg = yaml.safe_load(open("configs/log_flume.yaml"))
p = {**coaster.COASTER, **cfg["params"]}
w = World(); rep = coaster._flume(w, p, None)
cells = {pos: n for pos, (n, _) in w.cells.items()}
lv = fluids.spread(cells, [tuple(s) for s in rep["sources"]], max_steps=40000)
# escape lips: wet, at/above y=200, with air below and below not wet-by-design bed
lips = sorted(c for c in lv if c[1] >= 200 and not w.has(c[0], c[1]-1, c[2]))
print("escape lips (design range):", len(lips))
for c in lips[:40]: print("  ", c, "lvl", lv[c])
