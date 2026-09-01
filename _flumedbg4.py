import yaml
from collections import deque
from mcbuild import fluids
from mcbuild.gen import coaster
from mcbuild.gen.vertical import World
from mcbuild.gen.park import _Frame

cfg = yaml.safe_load(open("configs/log_flume.yaml"))
p = {**coaster.COASTER, **cfg["params"]}
w = World(); rep = coaster._flume(w, p, None)
cells = {pos: n for pos, (n,_) in w.cells.items()}
srcs = [tuple(s) for s in rep["sources"]]
# BFS with parent tracking, stop at first fall below 204
level={}; par={}; q=deque()
for s in srcs: level[s]=0; par[s]=None; q.append(s)
falls=[]
steps=0
while q and steps<200000:
    steps+=1
    (x,y,z)=q.popleft(); lv=level[(x,y,z)]
    below=(x,y-1,z)
    if fluids._passable(cells.get(below)) and level.get(below,99)>8:
        if y-1 < 203: falls.append(((x,y,z), par.get((x,y,z))))
        level[below]=8; par[below]=(x,y,z); q.append(below); continue
    nxt = 1 if lv==8 else lv+1
    if nxt>7: continue
    for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
        n=(x+dx,y,z+dz)
        if not fluids._passable(cells.get(n)): continue
        if level.get(n,99)<=nxt: continue
        level[n]=nxt; par[n]=(x,y,z); q.append(n)
print("fall points below y203:", len(falls))
seen=set()
for c,pr in falls[:200]:
    if c[1]!=203: continue
    if c in seen: continue
    seen.add(c)
    # trace back to a source
    chain=[c]; cur=pr
    while cur is not None and len(chain)<25:
        chain.append(cur); cur=par.get(cur)
    print("  fall at", c, "chain->", chain[1:8])
    if len(seen)>6: break
