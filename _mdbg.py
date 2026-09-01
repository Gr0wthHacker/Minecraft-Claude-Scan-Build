import yaml
from mcbuild import walk
from mcbuild.gen import frontiertown as ft
from mcbuild.gen.vertical import World
cfg = yaml.safe_load(open("configs/the_mine_head.yaml"))
p = {**ft.FRONTIER, **cfg["params"]}
w = World()
try: ft._minehead(w, p, None)
except Exception as e: print("(exp)", str(e)[:120])
cells={pos:n for pos,(n,_) in w.cells.items()}
from mcbuild.gen.park import _Frame
f=_Frame(p); W=17; D=16; ci=8; lo=ft.MINE_FLOOR
reach = walk.reachable(cells, f.at(ci,-1,0))
print("reach", len(reach), "min y", min(c[1] for c in reach))
for lbl,pt in (("shafthead",f.at(ci,D-3,0)),("lad-1",f.at(ci,D-3,-1)),("lad-5",f.at(ci,D-3,-5)),
               ("foot",f.at(ci,D-3,lo+1)),("drift mid",f.at(ci,8,lo+1)),
               ("cross",f.at(ci,3,lo+1)),("stope",f.at(W-5,6,lo+1)),("out",f.at(3,2,0))):
    print(f"  {lbl:10} {pt} in_reach={pt in reach} name={cells.get(pt)} stands={walk.stands(cells,pt)}")
