from mcbuild import circuit
from mcbuild.gen import circuits

def drive(low, high, level, facing="east", side=1):
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
    return c.power.get(g["out"], 0)

bad = 0
for facing in ("east","west","north","south"):
    for sd in (1,-1):
        for low, high in ((6,7),(3,4),(1,2),(2,3),(4,5),(5,9),(2,5),(12,13)):
            for lv in range(1,16):
                p = drive(low,high,lv,facing,sd)
                want = (low <= lv < high)
                got = p > 0
                if want != got:
                    bad += 1
                    print(f"FAIL {facing} side={sd} window({low},{high}) level {lv} -> {p} want {want}")
print("mismatches:", bad)
