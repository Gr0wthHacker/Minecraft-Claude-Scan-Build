import sys; sys.path.insert(0, r"C:\Users\Jack\mctest")
import json, os, collections
import numpy as np
from mcbuild import schem, scan, nightlight

Y_LO, Y_HI = 20, 215
cap = schem.load("out/island_full.litematic"); sc = scan.load("out/island_full.scan.json")
o = sc.meta['origin']; ox,oy,oz = o['x'],o['y'],o['z']
pal=[n.split(":")[-1] for n in cap.names]
NZ,NX = cap.ids.shape[1], cap.ids.shape[2]
NY = Y_HI-Y_LO+1
name = np.empty((NY,NZ,NX), dtype=object)
for y in range(Y_LO, Y_HI+1):
    rows = cap.ids[y-oy]
    for z in range(NZ):
        for x in range(NX): name[y-Y_LO,z,x] = pal[rows[z,x]]
def place(p):
    if not os.path.exists(p): return
    for x,y,z,b in json.load(open(p,encoding="utf-8"))["cells"]:
        if Y_LO<=y<=Y_HI and 0<=z-oz<NZ and 0<=x-ox<NX: name[y-Y_LO,z-oz,x-ox]=b
for d in ("out/Falls.scan.json",):
    for x,y,z in (json.load(open(d,encoding="utf-8")).get("dig") or []):
        if Y_LO<=y<=Y_HI: name[y-Y_LO,z-oz,x-ox]="air"
place("out/Falls.work.json"); place("out/Island Night.work.json")

flat = name.reshape(-1); states = sorted(set(flat.tolist()))
ix = {s:i for i,s in enumerate(states)}
ids = np.array([ix[s] for s in flat],dtype=np.int32).reshape(name.shape)
op,em,pa,spn,wa = nightlight.classify(states)
light = nightlight.propagate(op[ids], em[ids].astype(np.int16))

def route_light(label, path, pred=None):
    if not os.path.exists(path): print(f"{label:<22} (no work.json)"); return
    cells = json.load(open(path,encoding="utf-8"))["cells"]
    vals=[]
    for x,y,z,b in cells:
        bb=b.split("[")[0]
        if pred and not pred(bb,b): continue
        ay = y+1                      # the cell you stand IN, above the tread
        if not (Y_LO<=ay<=Y_HI and 0<=z-oz<NZ and 0<=x-ox<NX): continue
        vals.append(int(light[ay-Y_LO, z-oz, x-ox]))
    if not vals: print(f"{label:<22} (no matching cells)"); return
    v=np.array(vals)
    print(f"{label:<22} n={len(v):>5}  dark(0)={int((v==0).sum()):>5} ({100*(v==0).mean():>5.1f}%)"
          f"  dim(<5)={int((v<5).sum()):>5}  median={int(np.median(v)):>3}")
STAIR = lambda bb,b: "slab" in bb or "stairs" in bb
print("LIGHT ON THE ROUTES (block light in the cell you stand in), after the night pass\n")
route_light("Lowland Stair treads","out/Lowland Stair.work.json",STAIR)
route_light("Root Stair treads","out/Root Stair.work.json",STAIR)
route_light("Court Stair treads","out/Court Stair.work.json",STAIR)
route_light("Ruinway pavement","out/Lowland Ruinway.work.json")
route_light("Path Network","out/Path Network.work.json")
route_light("Lowland ground","out/Lowland.work.json")
