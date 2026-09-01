import sys
import numpy as np
from mcbuild import schem, scan as scanmod, fluids, nbt

def cells_of(path):
    sc = scanmod.load(path)
    m = sc.model
    ox, oy, oz = sc.origin
    names = m.names
    props = [nbt.state_props(e) for e in m.palette]
    out = {}
    ids = m.ids
    nz = np.argwhere(ids != 0) if names[0] in ("minecraft:air", "air") else np.argwhere(np.ones_like(ids, bool))
    for (y, z, x) in nz:
        i = int(ids[y, z, x])
        n = names[i].split(":")[-1]
        if n == "air":
            continue
        p = props[i]
        out[(ox+int(x), oy+int(y), oz+int(z))] = (n, p)
    return out

def audit(nm):
    c = cells_of(f"out/{nm}.litematic")
    plain = {p: v[0] for p, v in c.items()}
    water = {p: v[1] for p, v in c.items() if v[0] == "water"}
    src = [p for p, pr in water.items() if pr.get("level", "0") == "0"]
    leaks = []
    for (x, y, z) in water:
        for dx, dz in ((1,0),(-1,0),(0,1),(0,-1)):
            nb = (x+dx, y, z+dz)
            if nb in water: continue
            if fluids._passable(plain.get(nb)):
                leaks.append(((x,y,z), nb, plain.get(nb)))
    # bed check
    nobed = [p for p in water if fluids._passable(plain.get((p[0], p[1]-1, p[2]))) and (p[0],p[1]-1,p[2]) not in water]
    print(f"{nm}: {len(water)} water, {len(src)} sources, {len(water)-len(src)} flowing, LEAKS {len(leaks)}, NO-BED {len(nobed)}")
    for l in leaks[:20]:
        print("   leak", l)
    return leaks

for nm in ["Park_Centre Complete", "Park_Left Complete", "Park_Right Complete"]:
    audit(nm)

print("=== per design ===")
import glob, os
for f in sorted(glob.glob("out/*.litematic")):
    nm = os.path.basename(f)[:-len(".litematic")]
    if nm.startswith("Park_") and "Complete" not in nm: pass
    try:
        c = cells_of(f)
    except Exception as e:
        continue
    plain = {p: v[0] for p, v in c.items()}
    water = {p: v[1] for p, v in c.items() if v[0] == "water"}
    if not water: continue
    leaks = set()
    for (x,y,z) in water:
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            nb=(x+dx,y,z+dz)
            if nb in water: continue
            if fluids._passable(plain.get(nb)): leaks.add((x,y,z))
    src=[p for p,pr in water.items() if pr.get("level","0")=="0"]
    print(f"  {nm}: {len(water)} water {len(src)} src, leaking cells {len(leaks)}")
