import sys
from collections import deque
from mcbuild import blocks, palette
from mcbuild.gen.vertical import World

def components(w):
    cells=set(w.cells); seen=set(); out=[]
    for s in cells:
        if s in seen: continue
        q=deque([s]); seen.add(s); n=0
        while q:
            x,y,z=q.popleft(); n+=1
            for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                t=(x+d[0],y+d[1],z+d[2])
                if t in cells and t not in seen: seen.add(t); q.append(t)
        out.append(n)
    return sorted(out, reverse=True)

def check(w, label):
    comps = components(w)
    bad_state, currency, expensive, unavail = [], [], [], []
    for pos,(n,pr) in w.cells.items():
        errs = blocks.validate(n, pr)
        if errs: bad_state.append((n, pr, errs))
        if not blocks.spendable(n): currency.append(n)
        if palette.tier(n) == "expensive": expensive.append(n)
        if not blocks.available(n): unavail.append(n)
    print(f"{label}: cells={len(w.cells)} components={comps[:5]} ({len(comps)})")
    print(f"   illegal={len(bad_state)} {set(x[0] for x in bad_state) if bad_state else ''}")
    print(f"   currency={set(currency)} expensive={set(expensive)} unavailable={set(unavail)}")
    for b in bad_state[:4]: print("     ", b)
