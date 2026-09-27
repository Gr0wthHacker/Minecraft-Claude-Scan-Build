"""The park's flow audit: can a visitor get everywhere on foot, and where do they have to choose?

    python tools/park_flow.py                     the full report - ON FOOT, no railway
    python tools/park_flow.py --rail               ...and again with the line, for comparison
    python tools/park_flow.py --gap 0              strict flood - no jump allowed across a seam

WHY THIS EXISTS. `tests/test_park_plan.py` already proves each zone's own street network is one
connected walk that reaches every door - but it proves that against the PLANNED routes, never
against what actually got BUILT, and never across the void between islands. This reads the real
shipped litematics off disk and floods a standable-cell graph over them, which is the same
"flood-fill from real ground, seed region asserted large" discipline this project's own night
pass and Nav model already use. It found a real seam the planned-route tests could never see,
because the transit station's landing pad is a SEPARATE design from the zone's own paving and
nothing had ever asked whether the two physically touch.

**AND IT ANSWERED THE WRONG QUESTION FOR ITS FIRST WHOLE LIFE.** It composited `Park Line` and
omitted `Isthmus`, so its three-zones-all-reached result was a fact about a park you can only
cross by train - the exact thing Jack then complained about. See `DESIGNS` below.

WHAT COUNTS AS STANDABLE. A cell one course above a solid block, with the block itself and the one
above THAT both clear - two courses of headroom, the same rule `Nav.standable` in the mod uses.
Restricted to Y 199-213 (street level 203, transit deck 207, canopy roofs and station stairs all
fall inside it) or the flood would also "reach" every rooftop, ride platform and tower parapet in
the park, which are real standable surfaces nobody is meant to walk to from the ground.

A GAP OF ONE MISSING COLUMN IS JUMPABLE. Minecraft clears a one-block horizontal gap on foot
without even sprinting, so `--gap 1` (the default) also connects two standable cells two columns
apart when the column between them is empty air over a void - which is exactly the shape of the
seam this audit found at the frontier and hollow transit stations. `--gap 0` gives the strict,
floor-only number for comparison; the difference between the two IS the finding.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcbuild import scan as scan_mod, planner                     # noqa: E402

# THE RAILWAY IS NOT IN THIS LIST, AND THAT IS THE POINT.
#
# This audit shipped composited as [three zones + `Park Line`] and WITHOUT `Isthmus`, so every
# "all doors reached" it ever printed was a claim about a park whose three islands are joined
# only by a viaduct. Jack, on the shipped park: *"all land needs to be connected, the train is
# just fast transport - not the only way to reach these areas"*. A connectivity audit that
# includes the shortcut cannot answer that question at all.
#
# So the default composite is the WALKABLE park - the three zones, the causeway between them, and
# the pieces sited on the midway - and `--rail` adds the line back for comparison. The difference
# between the two runs is the railway's real contribution, which is what it should have been
# measuring all along.
DESIGNS = ["Park_Left Complete", "Park_Centre Complete", "Park_Right Complete",
           "Isthmus", "Park Gate", "Park Notices", "Park Arrival"]
RAIL = ["Park Line"]
Y_BAND = (199, 213)

ZONE_PLAN = {"frontier": "park_left", "midway": "park_centre", "hollow": "park_right"}
ZONE_Z = {"frontier": (80351, 80449), "midway": (80551, 80649), "hollow": (80751, 80849)}


def load_world(designs=DESIGNS) -> dict:
    """Composite the shipped litematics. A design that has not been generated yet is SKIPPED and
    named, never fatal: this tool has to keep working the day somebody adds a module."""
    world = {}
    for name in designs:
        if not os.path.exists(f"out/{name}.litematic"):
            print(f"  (skipped, not shipped: {name})")
            continue
        s = scan_mod.load(f"out/{name}.litematic")
        m = s.model
        ox, oy, oz = s.origin
        solid = m.solid()
        ys, zs, xs = solid.nonzero()
        names = m.names
        ids = m.ids
        for y, z, x in zip(ys, zs, xs):
            world[(int(x) + ox, int(y) + oy, int(z) + oz)] = names[ids[y, z, x]].split(":")[-1]
    return world


def standable(world: dict, y_band=Y_BAND) -> set:
    ymin, ymax = y_band
    out = set()
    for (x, y, z) in world:
        if not (ymin <= y <= ymax):
            continue
        top = y + 1
        if (x, top, z) not in world and (x, top + 1, z) not in world:
            out.add((x, top, z))
    return out


def _by_xz(stand: set) -> dict:
    by_xz: dict = {}
    for (x, y, z) in stand:
        by_xz.setdefault((x, z), []).append(y)
    return by_xz


def flood_dist(stand: set, start: tuple, max_step: int = 1, gap: int = 1) -> dict:
    """Like `flood`, but returns {cell: hop count} - an unweighted BFS depth, which on a grid of
    1-block steps is a fair stand-in for walking distance. Used only for the "how far" figures in
    the report; the reachability claims elsewhere use plain `flood`."""
    by_xz = _by_xz(stand)
    if start not in stand:
        ys = by_xz.get((start[0], start[2]))
        if not ys:
            raise ValueError(f"no standable cell anywhere near {start}")
        start = (start[0], min(ys, key=lambda y: abs(y - start[1])), start[2])
    dist = {start: 0}
    q = deque([start])
    steps = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    while q:
        x, y, z = q.popleft()
        for dx, dz in steps:
            targets = [(1, dx, dz)]
            if gap:
                targets.append((1 + gap, dx, dz))
            for mult, ddx, ddz in targets:
                nx, nz = x + ddx * mult, z + ddz * mult
                ys = by_xz.get((nx, nz))
                if not ys:
                    continue
                for ny in ys:
                    if abs(ny - y) <= max_step and (nx, ny, nz) not in dist:
                        dist[(nx, ny, nz)] = dist[(x, y, z)] + mult
                        q.append((nx, ny, nz))
    return dist


def flood(stand: set, start: tuple, max_step: int = 1, gap: int = 1) -> set:
    """3D flood fill over standable cells. Adjacent columns connect if some pair of their
    standable Y's differs by at most `max_step` (a player can step up/down about one block, and a
    stair flight moves one course per cell along its own run so this threads it too). `gap` also
    tries a hop two columns over when the column directly between is empty - a jump across a
    one-wide gap, never wider."""
    by_xz = _by_xz(stand)
    if start not in stand:
        ys = by_xz.get((start[0], start[2]))
        if not ys:
            raise ValueError(f"no standable cell anywhere near {start}")
        start = (start[0], min(ys, key=lambda y: abs(y - start[1])), start[2])
    seen = {start}
    q = deque([start])
    steps = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    while q:
        x, y, z = q.popleft()
        for dx, dz in steps:
            targets = [(1, dx, dz)]
            if gap:
                targets.append((1 + gap, dx, dz))
            for mult, ddx, ddz in targets:
                nx, nz = x + ddx * mult, z + ddz * mult
                ys = by_xz.get((nx, nz))
                if not ys:
                    continue
                for ny in ys:
                    if abs(ny - y) <= max_step and (nx, ny, nz) not in seen:
                        seen.add((nx, ny, nz))
                        q.append((nx, ny, nz))
    return seen


def zone_of(z: int) -> str:
    """Which piece of the park a Z row belongs to. The two void gaps get their own names rather
    than being lumped in as "transit": with the causeway in the composite they are LAND now, and
    calling the walk across them transit is the same conflation this tool's own DESIGNS list made.
    """
    for zone, (lo, hi) in ZONE_Z.items():
        if lo - 5 <= z <= hi + 5:
            return zone
    if 80450 <= z <= 80550:
        return "causeway N"
    if 80650 <= z <= 80750:
        return "causeway S"
    return "off-park"


def entrance_seed(stand: set) -> tuple:
    """A standable cell just inside the Park Gate - west edge of the midway, near its lanes."""
    for i in range(0, 10):
        for d in range(0, 19):
            c = (97553 + i, 203, 80561 + d)
            if c in stand:
                return c
    raise SystemExit("could not find a standable seed near the Park Gate")


def module_targets():
    """Every real module's door point, per zone, from the shipped plans - the same link point
    `planner._add_paths` itself joins to the street (`_front_of`, or `_inside_of` for an edge
    module whose front lies off the owned land - a gate or arch faces OUT of the park by
    definition, so ITS front is beyond the plot boundary on purpose and only its inside face is
    ever meant to be reached on foot). Using plain `_front_of` for every module would falsely
    flag every gate and arch as unreached, since their front point is deliberately over open void.
    """
    from mcbuild import islands as islands_mod
    out = []
    for zone, plan_name in ZONE_PLAN.items():
        try:
            pl = planner.Plan.load(plan_name)
        except FileNotFoundError:
            continue
        island = {"frontier": "islandleft", "midway": "newisle", "hollow": "islandright"}[zone]
        plot = islands_mod.plot_of(island)
        own = planner._owned_bounds(plot, planner.THEMES[zone]) if plot is not None else None
        for m in pl.modules:
            if m["kind"] in ("paths",) or m.get("covers") or m["gen"] == "streetfurniture":
                continue
            front = planner._front_of(m)
            if m.get("edge") and own is not None and not (
                    own[0] <= front[0] <= own[1] and own[2] <= front[1] <= own[3]):
                pt = planner._inside_of(m)
            else:
                pt = front
            out.append((zone, m["name"], (pt[0], 203, pt[1])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", type=int, default=1, help="widest jumpable gap in columns (0 = strict)")
    ap.add_argument("--rail", action="store_true",
                    help="add Park Line to the composite. OFF by default: the railway is a "
                         "shortcut, and an audit that includes it cannot say whether the land "
                         "is connected")
    args = ap.parse_args()

    designs = DESIGNS + (RAIL if args.rail else [])
    print(f"composite: {', '.join(designs)}")
    print("THE RAILWAY IS " + ("INCLUDED (--rail)" if args.rail
                               else "EXCLUDED - this is the walk") + "\n")
    world = load_world(designs)
    print(f"world cells: {len(world)}")
    stand = standable(world)
    print(f"standable cells, Y {Y_BAND[0]}-{Y_BAND[1]}: {len(stand)}")
    assert len(stand) > 5000, "the seed region is suspiciously small - is out/ stale?"

    seed = entrance_seed(stand)
    print(f"entrance seed: {seed}\n")

    for gap in sorted({0, args.gap}):
        reached = flood(stand, seed, gap=gap)
        by_zone: dict = {}
        for c in reached:
            by_zone.setdefault(zone_of(c[2]), 0)
            by_zone[zone_of(c[2])] += 1
        print(f"--- gap={gap} ---")
        print(f"reached from the gate: {len(reached)} / {len(stand)} standable cells")
        order = ("frontier", "causeway N", "midway", "causeway S", "hollow", "off-park")
        print(f"  by zone: { {k: by_zone.get(k, 0) for k in order} }")
        for zone in ("frontier", "midway", "hollow"):
            print(f"    {zone:9s} {'REACHED' if by_zone.get(zone) else 'NOT REACHED'}")
        print()

    # the seam itself, measured directly rather than inferred from the flood counts
    print("--- the seam between each zone's paving and the transit corridor, X=97636..97643 ---")
    for zone, zc in (("frontier", 80433), ("midway", 80600), ("hollow", 80776)):
        for x in range(97636, 97644):
            ys = sorted(y for (xx, y, z) in stand if xx == x and abs(z - zc) <= 3)
            state = "empty" if not ys else f"y={sorted(set(ys))}"
            print(f"  {zone:9s} x={x} near z={zc}: {state}")
        print()

    # every real attraction door, and whether it is reachable at gap=1 (a player's real movement)
    reached1 = flood(stand, seed, gap=1)
    reached1_xz = {(x, z) for (x, y, z) in reached1}
    print("--- every attraction door, gap=1 ---")
    missing = []
    for zone, name, pt in module_targets():
        near = any((pt[0] + dx, pt[2] + dz) in reached1_xz
                   for dx in (-1, 0, 1) for dz in (-1, 0, 1))
        if not near:
            missing.append((zone, name, pt))
    print(f"{len(module_targets()) - len(missing)} / {len(module_targets())} doors reached")
    for zone, name, pt in missing:
        print(f"  UNREACHED: {zone:9s} {name:20s} at {pt}")

    # distance from the gate to every door, gap=1 - an unweighted BFS depth over 1-block steps
    dist = flood_dist(stand, seed, gap=1)
    dist_xz = {(x, z): d for (x, y, z), d in dist.items()}

    def nearest_dist(pt):
        best = None
        for dx in (-2, -1, 0, 1, 2):
            for dz in (-2, -1, 0, 1, 2):
                d = dist_xz.get((pt[0] + dx, pt[2] + dz))
                if d is not None and (best is None or d < best):
                    best = d
        return best

    print("\n--- walking distance from the Park Gate (gap=1, BFS hops ~= blocks) ---")
    ranked = sorted(((nearest_dist(pt), zone, name) for zone, name, pt in module_targets()
                     if nearest_dist(pt) is not None), reverse=True)
    for d, zone, name in ranked[:10]:
        print(f"  {d:5d}  {zone:9s} {name}")
    if ranked:
        print(f"  furthest attraction: {ranked[0][2]} ({ranked[0][1]}) at ~{ranked[0][0]} blocks")


if __name__ == "__main__":
    main()
