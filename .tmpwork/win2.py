from mcbuild import circuit
from mcbuild.gen import circuits

def drive(low, high, level, facing="west", side=1):
    g = circuits.window((0,0,0), low, high, facing=facing, side=side)
    cells = dict(g["cells"])
    dx,_,dz = circuits.STEP[facing]
    pos = g["in"]
    for i in range(15-level):
        cells[pos] = "redstone_wire"
        pos = (pos[0]-dx, pos[1], pos[2]-dz)
    cells[pos] = "redstone_block"
    for p in list(cells):
        cells.setdefault((p[0],p[1]-1,p[2]), "smooth_stone")
    c = circuit.Circuit.from_cells(cells)
    c.run(ticks=30)
    return c, g

c,g = drive(5,9,9)
dx,_,dz = circuits.STEP["west"]
sx,sz = (-dz, -dx)
def at(i,j): return (0+dx*i+sx*j, 0, 0+dz*i+sz*j)
for j in range(5):
    row=[]
    for i in range(-1,10):
        p=at(i,j)
        row.append(f"{i},{j}:{c.name(p)[:4]}={c.level(p)}")
    print(' | '.join(row))
print('out', g['out'], c.level(g['out']))
