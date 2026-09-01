from mcbuild import circuit
from mcbuild.gen import GENERATORS
for kind in ("high_roller","double_or_none"):
    c = GENERATORS["casino"].build({"at":[0,70,0],"kind":kind,"outcomes":3,"pit":2,"check":False,"title":"T"}, [])
    s = circuit.Circuit.of(c.to_model(), c.world_origin)
    btn = tuple(c.meta["inputs"][0])
    hop = tuple(c.meta["rng_hopper"]); drop=(hop[0],hop[1]+1,hop[2])
    inn = (drop[0]-1, drop[1], drop[2])
    s.press(btn, ticks=4)
    seq=[]
    for t in range(20):
        s.step()
        seq.append((s.level(inn), s.powered(drop)))
    print(kind, 'in cell:', s.name(inn), 'drop:', s.name(drop))
    print('  ', seq[:14])
