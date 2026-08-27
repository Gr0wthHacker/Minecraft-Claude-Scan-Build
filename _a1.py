import sys; sys.path.insert(0, r"C:UsersJackmctest")
import numpy as np, collections
from mcbuild import schem, scan, nightlight
cap = schem.load("out/island_full.litematic"); sc = scan.load("out/island_full.scan.json")
o = sc.meta['origin']; ox,oy,oz = o['x'],o['y'],o['z']
pal=[n.split(":")[-1] for n in cap.names]; base=[p.split("[")[0] for p in pal]
ids = cap.ids
NY,NZ,NX = ids.shape
nonair = ids != 0
ys,zs,xs = np.nonzero(nonair)
wy = ys+oy
BANDS = [("lowland Y20-50",20,50),("descent Y51-99",51,99),("void Y100-149",100,149),
         ("belly Y150-189",150,189),("deck Y190-199",190,199),("plate Y200-215",200,215),
         ("sky Y216-270",216,270)]
print(f"{'band':<18}{'blocks':>9}{'columns':>9}{'density':>9}   top materials")
for nm,a,b in BANDS:
    m = (wy>=a)&(wy<=b)
    n = int(m.sum())
    cols = len({(int(x),int(z)) for x,z in zip(xs[m]+ox, zs[m]+oz)})
    vol = (b-a+1)*NZ*NX
    mats = collections.Counter(base[ids[y,z,x]] for y,z,x in zip(ys[m][:400000],zs[m][:400000],xs[m][:400000]))
    print(f"{nm:<18}{n:>9}{cols:>9}{100*n/vol:>8.2f}%   {', '.join(f'{k}:{v}' for k,v in mats.most_common(4))}")
