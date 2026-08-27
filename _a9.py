import sys; sys.path.insert(0, r"C:\Users\Jack\mctest")
import numpy as np, collections
from mcbuild import schem, scan
cap = schem.load("out/island_full.litematic"); sc = scan.load("out/island_full.scan.json")
o = sc.meta['origin']; ox,oy,oz = o['x'],o['y'],o['z']
pal=[n.split(":")[-1] for n in cap.names]; base=[p.split("[")[0] for p in pal]
ids=cap.ids
def census(y0,y1,label):
    c=collections.Counter()
    sub = ids[y0-oy:y1-oy+1]
    ys,zs,xs=np.nonzero(sub!=0)
    for y,z,x in zip(ys,zs,xs): c[base[sub[y,z,x]]]+=1
    print(f"\n=== {label} (Y{y0}-{y1}) - {sum(c.values())} blocks, {len(c)} types")
    return c
low = census(24,50,"THE LOWLAND FLOOR")
LUSH = ["moss_block","moss_carpet","azalea","flowering_azalea","azalea_leaves",
        "flowering_azalea_leaves","big_dripleaf","small_dripleaf","spore_blossom",
        "cave_vines","cave_vines_plant","glow_lichen","hanging_roots","rooted_dirt",
        "dripstone_block","pointed_dripstone","clay","vine","short_grass","fern",
        "large_fern","lily_pad","seagrass","kelp","glow_berries"]
print("  LUSH-CAVE VOCABULARY present in the lowland:")
for k in LUSH:
    n = low.get(k,0)
    flag = "" if n else "   <-- ABSENT"
    print(f"     {k:<26}{n:>6}{flag}")
print("\n  lowland top 12 materials:", ", ".join(f"{k}:{v}" for k,v in low.most_common(12)))
# water surface area in the harbor
w=0; ys,zs,xs=np.nonzero(ids[36-oy:40-oy+1]!=0)
print("\n  harbor water cells Y36-40:", sum(1 for y,z,x in zip(ys,zs,xs) if base[ids[36+y,z,x]]=="water"))
