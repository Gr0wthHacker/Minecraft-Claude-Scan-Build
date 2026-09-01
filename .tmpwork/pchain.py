from mcbuild import circuit
from mcbuild.gen import GENERATORS, circuits
for kind, width in (("high_roller",6),("double_or_none",5)):
    c = GENERATORS["casino"].build({"at":[0,70,0],"kind":kind,"outcomes":3,"pit":2,"check":False,"title":"T"}, [])
    s = circuit.Circuit.of(c.to_model(), c.world_origin)
    btn = tuple(c.meta["inputs"][0])
    pulse = circuits.pulse((0-5, 69, 0), length=2, facing="east", side=-1)
    pts = {"btn":btn, "p_in":pulse["in"], "p_foot":(-5,69,0), "p_cmp":(-3,69,0),
           "p_out":pulse["out"], "rnd_in":(2,67,0), "drop":(3,67,0)}
    s.press(btn, ticks=4)
    print(kind, {k:(s.name(v)) for k,v in pts.items()})
    for t in range(12):
        s.step()
        print('  t',t, {k: s.level(v) for k,v in pts.items()})
