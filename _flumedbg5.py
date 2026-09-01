import yaml
from mcbuild import fluids
from mcbuild.gen import coaster
from mcbuild.gen.vertical import World
from mcbuild.gen.park import _Frame

cfg = yaml.safe_load(open("configs/log_flume.yaml"))
p = {**coaster.COASTER, **cfg["params"]}
w = World()
try: coaster._flume(w, p, None)
except Exception as e: print("(expected)", str(e)[:80])
cells = {pos: n for pos, (n,_) in w.cells.items()}
srcs = [pos for pos,(n,pr) in w.cells.items() if n=="water" and pr.get("level","0")=="0"]
xs=[c[0] for c in cells]; ys=[c[1] for c in cells]; zs=[c[2] for c in cells]
b=(min(xs)-1,min(ys)-1,min(zs)-1,max(xs)+1,max(ys)+1,max(zs)+1)
print("design bbox", b)
lv = fluids.spread(cells, srcs, bounds=b)
print("wet in box", len(lv))
# rebuild envelope
f=_Frame(p)
wps=coaster._flume_plan(p); pts,marks=coaster._trace(wps)
corners=coaster._corners(pts,False); hs=coaster._profile(pts,marks,wps,corners)
n=len(pts)
def nb_h(j):
    out=[hs[j]]
    if j: out.append(hs[j-1])
    if j+1<n: out.append(hs[j+1])
    return out
env=set()
for j,(i,d) in enumerate(pts):
    for (oi,od) in [(0,0)]+coaster._wall_offs(pts,j):
        for hh in range(min(nb_h(j))+1, max(nb_h(j))+3):
            env.add(f.at(i+oi,d+od,hh))
m,s,t,half,dock,run = coaster._flume_dims(p)
pool_i,pool_d = pts[-1][0], pts[-1][1]-1
pi0,pi1=pool_i-half,pool_i+half; pd0,pd1=pool_d-half-2,pool_d
end_h=hs[-1]
for i in range(pi0,pi1+1):
    for d in range(pd0,pd1+1):
        for hh in (end_h+1,end_h+2): env.add(f.at(i,d,hh))
esc = sorted(c for c in lv if c not in env)
print("escapes in box:", len(esc))
for c in esc[:25]: print("  ", c, "lvl", lv[c], "under:", cells.get((c[0],c[1]-1,c[2])))

print("=== escapes by y, highest first")
from collections import Counter
print(sorted(Counter(c[1] for c in esc).items(), reverse=True)[:12])
hi = sorted((c for c in esc), key=lambda c: -c[1])[:30]
for c in hi: print("  ", c, "lvl", lv[c], "under:", cells.get((c[0],c[1]-1,c[2])), "here:", cells.get(c))
