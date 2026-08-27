import sys; sys.path.insert(0, r"C:\Users\Jack\mctest")
import numpy as np, json, os, math
from mcbuild import schem, scan
cap = schem.load("out/island_full.litematic"); sc = scan.load("out/island_full.scan.json")
o = sc.meta['origin']; ox,oy,oz = o['x'],o['y'],o['z']
Y0,Y1 = 50, 100
occ = (cap.ids[Y0-oy:Y1-oy+1] != 0)
for f in os.listdir("out"):
    if not f.endswith(".work.json"): continue
    try: w = json.load(open("out/"+f, encoding="utf-8"))
    except Exception: continue
    for x,y,z,b in w.get("cells", []):
        if Y0<=y<=Y1 and 0<=z-oz<occ.shape[1] and 0<=x-ox<occ.shape[2]:
            occ[y-Y0, z-oz, x-ox] = True
# the lower fall's column is a live feature: reserve it so nothing is sited in the water
for x in (-24213,-24212,-24211):
    for y in range(Y0, 99):
        if 0 <= 30002-oz < occ.shape[1]: occ[y-Y0, 30002-oz, x-ox] = True
dist = np.zeros(occ.shape, np.int16); cur = occ.copy()
for step in range(1, 20):
    nxt = cur.copy()
    for ax in (0,1,2):
        nxt |= np.roll(cur,1,axis=ax); nxt |= np.roll(cur,-1,axis=ax)
    dist[nxt & ~cur] = step; cur = nxt
    if cur.all(): break
AX,AZ = -24200, 30018
cands=[]
ys,zs,xs = np.nonzero(~occ)
for y,z,x in zip(ys,zs,xs):
    wx,wy,wz = x+ox, y+Y0, z+oz
    r = math.hypot(wx-AX, wz-AZ)
    if not (14 <= r <= 34): continue          # seen from the helix, not crowding it
    if not (60 <= wy <= 92): continue         # the measured dead band
    d = int(dist[y,z,x])
    if d < 7: continue
    cands.append((d, r, wx, wy, wz))
cands.sort(key=lambda c: (-c[0], c[1]))
print(f"sites in the descent dead band (Y60-92, 14-34 from the axis, >=7 clear): {len(cands)}")
seen=[]
print(f"{'clear':>6}{'r':>7}{'x':>9}{'y':>6}{'z':>8}")
for d,r,x,y,z in cands:
    if any(abs(x-a)<10 and abs(y-b)<10 and abs(z-c)<10 for _,_,a,b,c in seen): continue
    seen.append((d,r,x,y,z)); print(f"{d:>6}{r:>7.1f}{x:>9}{y:>6}{z:>8}")
    if len(seen)>=12: break
