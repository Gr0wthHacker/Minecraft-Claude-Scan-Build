from mcbuild import circuit
from mcbuild.gen import circuits

def drive(low, high, level, facing="west"):
    g = circuits.window((0,0,0), low, high, facing=facing, side=1)
    cells = dict(g["cells"])
    # feed the run: put a lever-driven repeater chain? simplest: place a redstone_block far enough
    # to give exact level? Use a wire tail with a source at distance so that level arrives.
    # Instead drive `in` cell with a source of chosen strength: place dust tail of (15-level) cells
    # ending at a redstone_block.
    dx,_,dz = circuits.STEP[facing]
    inp = g["in"]
    n = 15 - level
    pos = inp
    for i in range(n):
        cells[pos] = "redstone_wire"
        pos = (pos[0]-dx, pos[1], pos[2]-dz)
    cells[pos] = "redstone_block"
    # floors
    for p in list(cells):
        cells.setdefault((p[0],p[1]-1,p[2]), "smooth_stone")
    c = circuit.Circuit.from_cells(cells)
    c.run(ticks=25)
    return c.power.get(g["out"], 0), g

for low, high in ((6,7),(3,4),(5,9)):
    print(f"window({low},{high}):")
    for lv in range(1,10):
        p,_ = drive(low,high,lv)
        mark = "PASS" if p else "    "
        print(f"    level {lv:2d} -> out {p:2d}  {mark}")
