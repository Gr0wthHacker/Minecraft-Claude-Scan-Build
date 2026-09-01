from mcbuild import circuit
from mcbuild.gen import GENERATORS
kind="double_or_none"
c = GENERATORS["casino"].build({"at":[0,70,0],"kind":kind,"outcomes":3,"pit":2,"check":False,"title":"T"}, [])
m=c.to_model(); s = circuit.Circuit.of(m, c.world_origin)
btn = tuple(c.meta["inputs"][0]); print('btn', btn, s.name(btn))
s.press(btn, ticks=8); s.run(6)
hop = tuple(c.meta["rng_hopper"])
for y in range(hop[1]-1, btn[1]+1):
    print('--- y', y)
    for z in range(-4, 5):
        row=[]
        for x in range(-8, 8):
            n = s.name((x,y,z)) or 'air'
            lv = s.level((x,y,z)) if n=='redstone_wire' else ''
            row.append((n[:10]+str(lv)).ljust(12) if n!='air' else '.'.ljust(12))
        print(f'z{z:3d} ' + ''.join(row))
