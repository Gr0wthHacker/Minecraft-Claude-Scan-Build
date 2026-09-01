from mcbuild import circuit
from mcbuild.gen import GENERATORS
for kind in ("high_roller","double_or_none","lucky_number","duel","wheel"):
    for outcomes in (2,3):
        try:
            c = GENERATORS["casino"].build({"at":[0,70,0],"kind":kind,"outcomes":outcomes,
                                            "pit":2,"check":False,"title":"T"}, [])
        except Exception as e:
            print(kind, outcomes, 'build fail', e); continue
        s = circuit.Circuit.of(c.to_model(), c.world_origin)
        s.press(tuple(c.meta["inputs"][0]), ticks=4); s.run(60)
        rolls = [tuple(c.meta["rng_hopper"])]
        drops = []
        # find the dropper above each hopper
        for h in rolls:
            drops.append((h[0], h[1]+1, h[2]))
        if c.meta.get("house_hopper"):
            hh = tuple(c.meta["house_hopper"]); drops.append((hh[0],hh[1]+1,hh[2]))
        print(kind, outcomes, [(d, s.name(d), s.fired.get(d,0)) for d in drops])
