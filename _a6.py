import sys; sys.path.insert(0, r"C:\Users\Jack\mctest")
import numpy as np, json, os, math
from mcbuild import schem, scan
cap = schem.load("out/island_full.litematic"); sc = scan.load("out/island_full.scan.json")
o = sc.meta['origin']; ox,oy,oz = o['x'],o['y'],o['z']
Y0,Y1 = 36, 150
occ = np.zeros((Y1-Y0+1, cap.ids.shape[1], cap.ids.shape[2]), bool)
sub = cap.ids[Y0-oy:Y1-oy+1]
occ |= (sub != 0)
# reserve every design cell too (built or not), so we never site into planned work
for f in os.listdir("out"):
    if not f.endswith(".work.json"): continue
    try: w = json.load(open("out/"+f, encoding="utf-8"))
    except Exception: continue
    for x,y,z,b in w.get("cells", []):
        if Y0<=y<=Y1 and 0<=z-oz<occ.shape[1] and 0<=x-ox<occ.shape[2]:
            occ[y-Y0, z-oz, x-ox] = True
print("occupied cells in Y36-150 (world + every design):", int(occ.sum()))
# iterative dilation distance transform (numpy only - no scipy), capped
dist = np.zeros(occ.shape, np.int16)
cur = occ.copy()
for step in range(1, 26):
    nxt = cur.copy()
    for ax in (0,1,2):
        nxt |= np.roll(cur, 1, axis=ax); nxt |= np.roll(cur, -1, axis=ax)
    newly = nxt & ~cur
    dist[newly] = step
    cur = nxt
    if cur.all(): break
free = ~occ
dist[occ] = 0
best = []
ys,zs,xs = np.nonzero(free & (dist >= 9))
for y,z,x in zip(ys,zs,xs):
    best.append((int(dist[y,z,x]), x+ox, y+Y0, z+oz))
best.sort(reverse=True)
print(f"\nfree cells at least 9 from anything: {len(best)}")
AX,AZ = -24200, 30018
seen=[]
print(f"{'clear':>6}{'x':>9}{'y':>6}{'z':>8}{'r_axis':>8}   (dedup 12 apart)")
for d,x,y,z in best:
    if any(abs(x-a)<12 and abs(y-b)<12 and abs(z-c)<12 for _,a,b,c in seen): continue
    seen.append((d,x,y,z))
    print(f"{d:>6}{x:>9}{y:>6}{z:>8}{math.hypot(x-AX,z-AZ):>8.1f}")
    if len(seen)>=14: break
