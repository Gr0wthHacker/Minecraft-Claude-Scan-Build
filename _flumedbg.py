import yaml
from mcbuild import pipeline, fluids
from mcbuild.gen import coaster
from mcbuild.gen.vertical import World
from mcbuild.gen.park import _Frame

cfg = yaml.safe_load(open("configs/log_flume.yaml"))
p = {**coaster.COASTER, **cfg["params"]}
w = World()
rep = coaster._flume(w, p, None)
f = _Frame(p)
cells = {pos: n for pos, (n, _) in w.cells.items()}
water = [pos for pos, n in cells.items() if n == "water"]
print("water", len(water), "path", len(rep["path"]), "sources", len(rep["sources"]))
leaks = []
for (x,y,z) in water:
    for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
        nb=(x+dx,y,z+dz)
        if cells.get(nb)=="water": continue
        if fluids._passable(cells.get(nb)):
            leaks.append(((x,y,z),(dx,dz),cells.get(nb)))
lc = sorted({l[0] for l in leaks})
print("leaking cells", len(lc))
srcset = {tuple(s) for s in rep["sources"]}
pathset = {tuple(s) for s in rep["path"]}
for c in lc:
    print(" ", c, "source" if c in srcset else ("path" if c in pathset else "OTHER"),
          [ (l[1], l[2]) for l in leaks if l[0]==c])

print("=== spread simulation ===")
lv = fluids.spread(cells, [tuple(s) for s in rep["sources"]])
print("wet cells", len(lv))
# a cell with no bed under it and water in it -> water is falling / escaping
nobed = [c for c in lv if fluids._passable(cells.get((c[0], c[1]-1, c[2]))) and (c[0],c[1]-1,c[2]) not in lv]
print("wet cells with no bed:", len(nobed))
for c in sorted(nobed)[:20]: print("  ", c, lv[c])
# envelope
xs=[c[0] for c in lv]; ys=[c[1] for c in lv]; zs=[c[2] for c in lv]
print("wet bbox", min(xs),max(xs), min(ys),max(ys), min(zs),max(zs))
solid = [c for c in cells]
print("design bbox", min(c[0] for c in solid), max(c[0] for c in solid), min(c[1] for c in solid), max(c[1] for c in solid), min(c[2] for c in solid), max(c[2] for c in solid))
print("carries:", {k:v for k,v in rep["flow"].items()})
