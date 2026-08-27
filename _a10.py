import sys; sys.path.insert(0, r"C:\Users\Jack\mctest")
import numpy as np, collections
from mcbuild import schem, scan, nightlight
cap = schem.load("out/island_full.litematic"); sc = scan.load("out/island_full.scan.json")
o = sc.meta['origin']; ox,oy,oz = o['x'],o['y'],o['z']
pal=[n.split(":")[-1] for n in cap.names]; base=[p.split("[")[0] for p in pal]
Y0,Y1 = 22, 70
sub = cap.ids[Y0-oy:Y1-oy+1]
op,em,pa,spn,wa = nightlight.classify(pal)
opaque = op[sub]; passy = pa[sub]; water = wa[sub]
NY,NZ,NX = sub.shape
# CEILINGS: an air cell with an opaque block directly above, and open air below it
ceil = []
for y in range(NY-1):
    m = (~opaque[y]) & (~water[y]) & opaque[y+1]
    zs,xs = np.nonzero(m)
    for z,x in zip(zs,xs):
        # needs a few courses of air under it or it's a crevice
        if y>=2 and not opaque[y-1,z,x] and not opaque[y-2,z,x]:
            ceil.append((x+ox, y+Y0, z+oz, base[sub[y+1,z,x]]))
print(f"CEILING cells in Y{Y0}-{Y1} (hang cave vines / spore blossom / dripstone): {len(ceil)}")
print("   ceiling material:", collections.Counter(c[3] for c in ceil).most_common(6))
byy = collections.Counter(c[1] for c in ceil)
print("   by height:", ", ".join(f"Y{k}:{v}" for k,v in sorted(byy.items()) if v>40))
# FLOOR: walkable surface in the lowland
surf = nightlight.surface(passy, spn[sub], water)
floors = collections.Counter()
for (x,iy,z) in surf: floors[base[sub[iy-1,z,x]]] += 1
print(f"\nWALKABLE lowland surface cells: {len(surf)}")
print("   floor material:", floors.most_common(8))
# WATER surface (for lily pad / dripleaf / seagrass)
ws=0; shallow=0
for z in range(NZ):
    for x in range(NX):
        col = np.nonzero(water[:,z,x])[0]
        if not len(col): continue
        top = col.max()
        if not opaque[top+1,z,x] if top+1<NY else True:
            ws += 1
            depth = 1
            yy = top
            while yy-depth >= 0 and water[yy-depth,z,x]: depth += 1
            if depth <= 3: shallow += 1
print(f"\nWATER surface columns: {ws}  (of which <=3 deep, plantable: {shallow})")
