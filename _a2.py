import sys; sys.path.insert(0, r"C:\Users\Jack\mctest")
import numpy as np, collections
from mcbuild import schem, scan
cap = schem.load("out/island_full.litematic"); sc = scan.load("out/island_full.scan.json")
o = sc.meta['origin']; ox,oy,oz = o['x'],o['y'],o['z']
pal=[n.split(":")[-1] for n in cap.names]; base=[p.split("[")[0] for p in pal]
ids = cap.ids
AX, AZ = -24200, 30018          # the stair's axis (taproot keel)
ys,zs,xs = np.nonzero(ids != 0)
wx, wy, wz = xs+ox, ys+oy, zs+oz
STAIRISH = {"stone_brick_wall","deepslate_brick_wall","polished_blackstone_brick_wall",
            "stone_brick_slab","deepslate_brick_slab","polished_blackstone_brick_slab",
            "cobbled_deepslate_slab","mossy_stone_brick_slab","blackstone_slab",
            "lantern","soul_lantern","oak_wood","oak_log"}
d = np.abs(wx-AX) + 0  # use radial
r = np.sqrt((wx-AX)**2 + (wz-AZ)**2)
print("descending the helix: what stands within 30 blocks of the axis, per 10-course slice")
print(f"{'Y':>10}{'within30':>10}{'not-stair':>11}   what")
for lo in range(150, 35, -10):
    hi = lo+9
    m = (wy>=lo)&(wy<=hi)&(r<=30)
    n = int(m.sum())
    names = [base[ids[y,z,x]] for y,z,x in zip(ys[m],zs[m],xs[m])]
    other = [q for q in names if q not in STAIRISH]
    c = collections.Counter(other).most_common(3)
    print(f"{lo:>4}-{hi:<5}{n:>10}{len(other):>11}   {', '.join(f'{k}:{v}' for k,v in c) if c else '(stair only)'}")
