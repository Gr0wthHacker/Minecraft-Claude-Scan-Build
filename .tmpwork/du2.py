from mcbuild import circuit
from mcbuild.gen import GENERATORS
c = GENERATORS["casino"].build({"at":[0,70,0],"kind":"duel","outcomes":3,"pit":2,"check":False,"title":"T"}, [])
s = circuit.Circuit.of(c.to_model(), c.world_origin)
for z in range(-4,3):
    print(f'z{z:3d} ' + ''.join((s.name((x,67,z)) or 'air')[:12].ljust(13) for x in range(-2,8)))
print('---- after press')
s.press(tuple(c.meta["inputs"][0]), ticks=4)
for t in range(6):
    s.step()
    print(t, [(x, s.level((x,67,0))) for x in range(0,5)], [(x, s.level((x,67,-1))) for x in range(1,5)])
