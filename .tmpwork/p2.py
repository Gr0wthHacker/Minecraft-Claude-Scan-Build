from mcbuild import circuit
from mcbuild.gen import GENERATORS
for kind in ("high_roller","double_or_none"):
    c = GENERATORS["casino"].build({"at":[0,70,0],"kind":kind,"outcomes":3,"pit":2,"check":False,"title":"T"}, [])
    s = circuit.Circuit.of(c.to_model(), c.world_origin)
    cmp_=(-3,69,0)
    pts={"rear":(-4,69,0),"sN":(-3,69,-1),"sS":(-3,69,1),"out":(-2,69,0)}
    print(kind, {k:s.name(v) for k,v in pts.items()}, 'cmp', s.name(cmp_), s.at(cmp_).props)
    s.press(tuple(c.meta["inputs"][0]), ticks=4)
    for t in range(8):
        s.step()
        print('  t',t, 'rear',s.level(pts["rear"]),'sN',s.level(pts["sN"]),'sS',s.level(pts["sS"]),
              'state',s.state.get(cmp_),'out',s.level(pts["out"]))
