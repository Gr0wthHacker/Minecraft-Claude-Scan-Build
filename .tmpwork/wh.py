from mcbuild import circuit
from mcbuild.gen import GENERATORS, circuits
c = GENERATORS["casino"].build({"at": [0,70,0], "kind":"wheel","pit":2,"check":False,"facing":"east","title":"W"}, [])
pockets=[tuple(v) for v in c.meta["pockets"]]
m=c.to_model()
for roll in (1,2,4):
    s=circuit.Circuit.of(m, c.world_origin)
    s.fill(tuple(c.meta["rng_hopper"]), roll)
    s.press(tuple(c.meta["inputs"][0]), ticks=4); s.run(80)
    print('roll',roll,[ (i, s.powered(q), q) for i,q in enumerate(pockets)])
# geometry
hop=tuple(c.meta["rng_hopper"])
print('hop',hop)
s=circuit.Circuit.of(m, c.world_origin)
for y in (hop[1],):
    for z in range(hop[2]-6, hop[2]+7):
        print(f'z{z} ' + ''.join((s.name((x,y,z)) or 'air')[:13].ljust(13) for x in range(hop[0]-8, hop[0]+3)))
