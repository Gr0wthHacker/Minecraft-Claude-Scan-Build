"""Measure paved% and furnished% for a planned park zone, first-writer-wins composited.

`furnished` = share of plot columns carrying a contiguous run of >=3 solid cells somewhere in
their stack (a wall, a tree, a bed kerb+bush, a tower leg - anything that isn't just a thin
paving skin). `paved` = share of plot columns with ANY solid cell at all.

Standalone diagnostic, not part of the test suite - it needs the real island captures in out/
and writes nothing.
"""
import collections
import sys

from mcbuild import planner, islands
from mcbuild.gen import GENERATORS

ZONE_WORLD = {"midway": ("newisle", "out/newisle.litematic"),
              "frontier": ("islandleft", "out/islandleft.litematic"),
              "hollow": ("islandright", "out/islandright.litematic")}


def module_world_cells(m):
    gen = GENERATORS[m["gen"]]
    p = dict(m.get("params", {}))
    p["at"] = m["at"]
    p["kind"] = m["kind"]
    c = gen.build(p, None)
    x0, y0, z0 = c.world_origin
    ys, zs, xs = c.ids.nonzero()
    return x0, y0, z0, xs, ys, zs


def measure(zone: str, plane: int = 203):
    isl, world = ZONE_WORLD[zone]
    pl = planner.make(zone, world, name=f"_furnish_{zone}", theme=zone, island=isl, plane=plane)
    plot = islands.plot_of(isl)

    # first-writer-wins in plan order, same rule `layers.slice_plan` uses.
    claimed: dict = {}
    for m in pl.modules:
        x0, y0, z0, xs, ys, zs = module_world_cells(m)
        for xx, yy, zz in zip(xs, ys, zs):
            pos = (x0 + int(xx), y0 + int(yy), z0 + int(zz))
            if pos not in claimed:
                claimed[pos] = m["name"]

    by_col = collections.defaultdict(list)
    for (x, y, z) in claimed:
        if plot.contains(x, z):
            by_col[(x, z)].append(y)

    total = (2 * plot.radius + 1) ** 2
    paved, furnished = 0, 0
    for (x, z), ys in by_col.items():
        paved += 1
        if max(ys) - min(ys) + 1 >= 3:
            furnished += 1
    return total, paved, furnished


if __name__ == "__main__":
    zones = sys.argv[1:] or list(ZONE_WORLD)
    for zone in zones:
        total, paved, furnished = measure(zone)
        print(f"{zone:10s} plot={total:6d} paved={paved:6d} ({100*paved/total:5.1f}%) "
              f"furnished={furnished:6d} ({100*furnished/total:5.1f}%)")
