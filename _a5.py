import sys; sys.path.insert(0, r"C:\Users\Jack\mctest")
import numpy as np, collections
from mcbuild import schem, scan, nightlight
cap = schem.load("out/island_full.litematic"); sc = scan.load("out/island_full.scan.json")
o = sc.meta['origin']; ox,oy,oz = o['x'],o['y'],o['z']
pal=[n.split(":")[-1] for n in cap.names]; base=[p.split("[")[0] for p in pal]
ids = cap.ids
# TERRAIN = the island's own ground. Anything else is a FEATURE someone put there.
TERRAIN = {"stone","cobblestone","mossy_cobblestone","moss_block","dirt","grass_block",
 "coarse_dirt","gravel","sand","andesite","diorite","granite","deepslate","tuff","clay",
 "dripstone_block","pointed_dripstone","water","ice","snow_block","snow","air",
 "short_grass","tall_grass","fern","large_fern","vine","moss_carpet","azalea",
 "flowering_azalea","oak_leaves","oak_log","spruce_leaves","birch_leaves","jungle_leaves",
 "acacia_leaves","dark_oak_leaves","azalea_leaves","flowering_azalea_leaves","mangrove_roots",
 "rooted_dirt","podzol","mycelium","dead_bush","lily_pad","seagrass","kelp","kelp_plant",
 "hanging_roots","glow_lichen","big_dripleaf","small_dripleaf","spore_blossom","cave_vines",
 "cave_vines_plant","sculk_vein","bubble_column","mud","packed_ice","blue_ice","calcite"}
op,em,pa,spn,wa = nightlight.classify(pal)
Y0,Y1 = 196, 214                      # the plate you walk on
sub = ids[Y0-oy:Y1-oy+1]
surf = nightlight.surface(pa[sub], spn[sub], wa[sub])
feat = np.zeros((cap.ids.shape[1], cap.ids.shape[2]), bool)
ys,zs,xs = np.nonzero(ids != 0)
for y,z,x in zip(ys,zs,xs):
    if Y0-4 <= y+oy <= Y1+8 and base[ids[y,z,x]] not in TERRAIN:
        feat[z,x] = True
fz, fx_ = np.nonzero(feat)
print(f"plate walkable cells: {len(surf)}   feature columns near the plate: {len(fz)}")
rows=[]
for (x,iy,z) in surf:
    if not len(fz): break
    d = np.min(np.abs(fz-z) + np.abs(fx_-x))     # manhattan to nearest feature column
    rows.append((d, x+ox, iy+Y0, z+oz))
rows.sort(reverse=True)
print("\nEMPTIEST PLATE GROUND - walkable cells furthest from anything built/planted")
print(f"{'dist':>5}  {'x':>8}{'y':>5}{'z':>7}")
for d,x,y,z in rows[:18]: print(f"{d:>5}  {x:>8}{y:>5}{z:>7}")
ds = np.array([r[0] for r in rows])
print(f"\ndistance-to-feature: median {np.median(ds):.0f}, 90th pct {np.percentile(ds,90):.0f}, max {ds.max()}")
for t in (6,8,10,12):
    print(f"   cells more than {t:>2} from any feature: {int((ds>t).sum()):>4} ({100*(ds>t).mean():.1f}%)")
