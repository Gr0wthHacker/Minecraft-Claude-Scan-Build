"""The night pass: light the guest paths a land's own street lighting could not reach.

    python tools/park_night.py                 all three zones
    python tools/park_night.py --plan park_left --no-ship

**A LAMP POST NEEDS SOMEWHERE TO STAND, AND SOME STREETS HAVE NOWHERE.** `gen/park._paths` puts a
post on the verge, falls back to the kerb, and gives up when a walk is squeezed between two
buildings - which is exactly the tightest, most enclosed street in a land and the one a guest most
wants lit. Measured after every spacing and fallback change that could be made, 45 walkable route
cells across the two side lands were still at block light 0.

So the last of it is done the way this island already lights itself: **an ochre froglight set FLUSH
into the paving**. It is the floor rather than something standing on it, so it needs no side room
at all, it cannot be knocked off a walkway, and it is Jack's own idiom - 39 of them were scattered
by hand across the lowland before any tool did it.

**REACH IS ONE LESS THAN THE LIGHT.** A flush froglight is an opaque emitter a course DOWN, so the
cell a mob would stand in reads 14, not 15. Crediting it 15 left 21 cells dark at the edges of its
coverage the last time this project made that mistake.

**AND IT IS A FIXPOINT, NOT ONE PASS.** Placing a light changes what is dark; the cover is
recomputed until nothing is left, exactly as `Island Night` had to be.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import evidence, pathgraph as P, planner, scan  # noqa: E402
from mcbuild.gen.canvas import Canvas  # noqa: E402
from mcbuild.gen.vertical import World  # noqa: E402
from mcbuild.pipeline import Settings  # noqa: E402

ZONES = ("park_centre", "park_left", "park_right")

#: A froglight in the floor lights the cell above it to 14 - it IS the floor, an opaque emitter a
#: course down, so its reach is one less than its light level.
LIGHT, REACH = "ochre_froglight", 14
MAX_ROUNDS = 6


def dark_cells(plan: dict, out_dir: str = "out") -> list:
    """Every walkable guest-path cell at block light 0, with the course it stands on."""
    found, _missing = evidence._artifacts(plan, out_dir)
    if not found:
        return []
    routes = P.normalise(plan.get("routes") or [])
    hub = next((m for m in plan["modules"] if m.get("covers") and m["kind"] == "plaza"), None)
    if hub is None:
        return []
    levels = P.levels(routes, int(hub["at"][1]))
    walk = P.interior(routes)
    footprints = [evidence._box_of(m) for m in plan["modules"]
                  if not m.get("covers") and m["kind"] not in {"paths", "plaza"}]

    def indoors(x, z):
        return any(x0 <= x <= x1 and z0 <= z <= z1 for (x0, z0, x1, z1) in footprints)

    light, origin = evidence._light_field(found)
    out = []
    for (x, z), courses in levels.items():
        if indoors(x, z) or (x, z) not in walk:
            continue
        for y in courses:
            value = evidence._at(light, origin, x, y, z)
            if value is not None and value <= 0:
                out.append((x, y, z))
    return out


def cover(cells: list) -> list:
    """A greedy set of positions whose reach covers every dark cell.

    Greedy rather than exhaustive: the sets are small and the difference between an optimal cover
    and a greedy one here is a lantern or two, which is not worth the search.
    """
    remaining, chosen = list(cells), []
    while remaining:
        best, lit = None, []
        for candidate in remaining:
            near = [c for c in remaining
                    if abs(c[0] - candidate[0]) + abs(c[1] - candidate[1])
                    + abs(c[2] - candidate[2]) <= REACH]
            if len(near) > len(lit):
                best, lit = candidate, near
        if best is None:
            break
        chosen.append(best)
        remaining = [c for c in remaining if c not in set(lit)]
    return chosen


def build(plan_name: str, out_dir: str = "out", ship: bool = True) -> tuple:
    plan = dict(planner.Plan.load(plan_name).__dict__)
    world = World()
    placed, rounds = [], 0
    for rounds in range(1, MAX_ROUNDS + 1):
        dark = dark_cells(plan, out_dir)
        if not dark:
            break
        spots = cover(dark)
        if not spots:
            break
        for (x, y, z) in spots:
            # The floor is the course UNDER the cell a guest stands in.
            world.put(x, y - 1, z, LIGHT)
            placed.append([x, y - 1, z])
        name = f"{plan.get('name', plan_name).title()} Night"
        canvas = world.canvas({
            "kind": "park/night", "land": plan["theme"], "lights": len(placed),
            "contract": "every walkable guest-path cell in the land is above block light 0, "
                        "lit by froglights set flush in the paving so nothing stands in a walk",
        })
        path = os.path.join(out_dir, f"{name}.litematic")
        scan.save_pair(path, canvas.to_model(), {**canvas.meta,
                                                 "origin": dict(zip("xyz", canvas.world_origin))},
                       name=name)
        # **THE NEXT ROUND MEASURES THE WORLD THIS ONE MADE.** Placing a light changes what is
        # dark - a lamp at the mouth of an alley lights three cells down it - so the cover has to
        # be recomputed rather than trusted. Round 2 typically places a handful; round 3 none.
        plan.setdefault("modules", []).append(
            {"name": name, "gen": "park", "kind": "night", "at": list(canvas.world_origin),
             "size": list(canvas.to_model().shape_xyz), "anchor_offset": [0, 0, 0],
             "params": {"land": plan["theme"], "facing": "east"}})
        plan["modules"] = [m for m in plan["modules"] if m["name"] != name] + [plan["modules"][-1]]
    # **SHIP WHAT EXISTS, NOT WHAT THIS RUN HAPPENED TO PLACE.** Gated on `placed`, a design
    # produced by an earlier dry run never reached the game: the second run measured the world
    # the first one had already lit, correctly placed nothing, and shipped nothing - so
    # `Park_Left Night` sat in `out/` while the land it lights was in the schematics folder
    # without it. A pass that is a fixpoint converges to placing zero, which is success.
    if ship:
        settings = Settings()
        name = f"{plan.get('name', plan_name).title()} Night"
        for suffix in (".litematic", ".scan.json"):
            src = os.path.join(out_dir, name + suffix)
            if os.path.exists(src):
                with open(src, "rb") as handle:
                    data = handle.read()
                with open(os.path.join(settings.schem_dir, name + suffix), "wb") as handle:
                    handle.write(data)
    return len(placed), rounds


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", action="append", help="default: all three zones")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--no-ship", action="store_true")
    a = ap.parse_args()
    for name in (a.plan or list(ZONES)):
        lights, rounds = build(name, a.out_dir, ship=not a.no_ship)
        print(f"{name}: {lights} froglight(s) over {rounds} round(s)")


if __name__ == "__main__":
    main()
