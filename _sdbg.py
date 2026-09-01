from mcbuild import fluids
from mcbuild.gen import frontiertown as ft
from mcbuild.gen.vertical import World
from mcbuild.gen.park import _Frame
p = {**ft.FRONTIER, "kind":"sluice","land":"frontier","facing":"east","at":[97600,203,80400],
     "width":13,"depth":13,"title":"Gold Sluice"}
w = World()
try: ft._sluice(w,p,None)
except Exception as e: print("(exp)", e)
f=_Frame(p); W=13; D=13; ci=6; TOP=5; d0,d1=1,11
def bed(d): return max(1, TOP-(d-d0)//3)
cells={pos:n for pos,(n,_) in w.cells.items()}
srcs=[pos for pos,(n,pr) in w.cells.items() if n=="water" and pr.get("level","0")=="0"]
env={f.at(i,d,hh) for d in range(d0,d1+1) for i in range(ci-1,ci+2) for hh in range(bed(d)+1,bed(d)+3)}
lv=fluids.spread(cells,srcs,max_steps=60000)
esc=sorted(c for c in lv if c not in env)
print("wet",len(lv),"esc",len(esc))
for c in esc[:12]:
    # decode local
    d = p["at"][0]-c[0]; i = c[2]-p["at"][2]; h=c[1]-p["at"][1]
    print("  ",c,"local i,d,h=",i,d,h,"lvl",lv[c],"under",cells.get((c[0],c[1]-1,c[2])))
