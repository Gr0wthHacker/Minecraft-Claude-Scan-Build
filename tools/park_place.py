"""Put the modules that ARE BUILT onto the ground layer, at their measured lots.

Jack: "unless we need size adjustments... use existing modules for major things like ferris wheel,
and only use new agents to build new things for the gaps of areas that we dont have things for."

**TWENTY-NINE MODULES WERE ALREADY BUILT** in `out/park_final/artifacts/` - 250,000 blocks
including the Sky Lift, the Mine Coaster and the Prism Ascent - and nothing was placing them,
because the assembly step still used `park_final.world.json`'s own `at` values. Those predate the
grid rework and the audit found them incompatible with any street plan: eight modules sat inside
the arrival spine band. `tools/park_lots.PLACEMENT` is the measured table that supersedes them.

    python tools/park_place.py            place every built module, report clashes
    python tools/park_place.py --ship     ...and merge to `Park Buildings` and ship it

THE FIVE `* Line` MODULES ARE SUPERSEDED AND SKIPPED. They are the old per-land path strips;
`Park Ways` is the ground layer now and draws all of it, so placing them would put two designs on
one surface - the exact thing `finish.defer_to` exists to stop, and the reason the casino was
sliced into layers rather than shipped as thirty overlapping fragments.

A MODULE'S OWN y=0 IS NOT ITS FLOOR. `parkbuild` records which course of each canvas is the build
plane in `planes.json` - a lot with a basement starts below it - so the vertical offset is
`plane - planes[name]`, never zero. Placed without it every below-plane reservation ends up in
the air, which is how the coaster once floated thirteen courses over its own ridge.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcbuild import nbt, profile as mcprofile, scan, schem  # noqa: E402
from tools.park_lots import PLACEMENT  # noqa: E402

ARTIFACTS = ROOT / "out" / "park_final" / "artifacts"
#: superseded by `Park Ways` - see the module docstring
#: JACK KEPT THREE. "the ferris wheel itself, the merry go round itself, and the roller coaster
#: are worthy saves from that buildings bunch, everything else should be rebuilt to properly fit
#: themes, available spaces, etc, without the chaos that exists currently."
#:
#: So this is a KEEP list rather than a skip list, and the difference matters: a skip list grows
#: quietly wrong as modules are added, while a keep list can only ever place what somebody named.
#: `Carousel Court` and `Sky Lift` are now their ride and nothing else - part 0 of a compose of
#: seventeen and twenty-seven - because the courts around them were the chaos.
KEEP = {"Sky Lift", "Carousel Court", "Mine Coaster"}

#: V0 -> X, U0 -> Z, and the floor course. Derived by tools/park_anchor.py from the island
#: registry; stated here only so a shipped sidecar can carry it.
ANCHOR = (97500, 202, 80300)


def plane_of(model, role: str = "") -> int:
    """Which course of a module's own canvas is its GROUND, DERIVED rather than looked up.

    `parkbuild` writes this to `planes.json` - and a FILTERED rebuild REPLACES that file with only
    the modules it built, so rebuilding four of twenty-one reduced it to a single entry and every
    other module's plane silently became 0. The Mine Coaster's is 13: at 0 it hangs thirteen
    courses over its own ridge with 4,650 of its 4,662 columns touching nothing, which is exactly
    what "the rollercoaster is still floating in mid air" was. Nothing this cheap to measure
    should depend on a side file that a partial run can truncate.

    The rule is `parkbuild`'s own: the lowest course covering most of the module's own columns.
    A bare hanging creature is exempt - the Sloth's densest course is 23 up and lowering it by
    that would bury it in the deck - but a sculpture COMPOSED on its own apron does have ground.
    """
    sol = model.solid()
    if role == "sculpture":
        return 0
    cols = len({(int(x), int(z)) for _y, z, x in zip(*sol.nonzero())})
    per = sol.sum(axis=(1, 2))
    return next((int(y) for y, n in enumerate(per) if n >= 0.60 * cols), 0)


def lots() -> dict:
    spec = json.loads((ROOT / "park_final.world.json").read_text(encoding="utf-8"))
    return ({m["name"]: m.get("footprint") for m in spec["modules"]},
            {m["name"]: m.get("role", "") for m in spec["modules"]})


def modules(report=False) -> list:
    """(name, V, U, model, plane) for every built module that has a measured lot.

    CROPPED TO ITS LOT, and the crop is REPORTED rather than silent. One cell outside a lot costs
    the neighbour behind it a course - this park has already lost a 111-block ride to a single
    lamp - so the boundary is enforced at placement whatever a generator emitted.
    """
    out = []
    box, roles = lots()
    for name, (v, u) in sorted(PLACEMENT.items()):
        if name not in KEEP and not (ROOT / "out" / f"PF {name}.litematic").exists():
            continue
        # A `PF ` BUILD SUPERSEDES THE RETIRED ARTIFACT OF THE SAME NAME. The three lands were
        # rebuilt from scratch into `out/PF <name>.litematic`; `out/park_final/artifacts` still
        # holds the previous attempt, and only the three rides Jack kept are taken from there.
        pf = ROOT / "out" / f"PF {name}.litematic"
        f = pf if pf.exists() else ARTIFACTS / f"{name}.litematic"
        if not f.exists():
            continue
        m = schem.load(str(f))
        fp = box.get(name)
        if fp:
            deep, wide = int(fp[0]), int(fp[1])
            _sy, sz, sx = m.ids.shape
            if sx > deep or sz > wide:
                before = int(m.solid().sum())
                m = schem.Model(m.ids[:, :min(sz, wide), :min(sx, deep)].copy(), m.palette)
                if report:
                    print(f"  cropped {name}: {before - int(m.solid().sum())} cells "
                          f"outside its {deep}x{wide} lot")
        out.append((name, int(v), int(u), m, plane_of(m, roles.get(name, ""))))
    return out


def merge(items) -> schem.Model:
    """One model, module by module, first writer winning a contested cell."""
    import numpy as np
    cells, pal, index = {}, [nbt.block_state("minecraft:air")], {}
    for name, v, u, m, plane in items:
        names = {i: e.value["Name"].value for i, e in enumerate(m.palette)}
        props = {i: e.value.get("Properties") for i, e in enumerate(m.palette)}
        for y, z, x in zip(*m.solid().nonzero()):
            # the module's own build plane is the ground layer's floor course
            pos = (int(x) + v, int(y) - plane + 1, int(z) + u)
            if pos in cells:
                continue
            key = int(m.ids[y, z, x])
            state = (names[key], str(props[key]))
            slot = index.get(state)
            if slot is None:
                slot = index[state] = len(pal)
                pal.append(m.palette[key])
            cells[pos] = slot
    xs = [p[0] for p in cells]; ys = [p[1] for p in cells]; zs = [p[2] for p in cells]
    ox, oy, oz = min(xs), min(ys), min(zs)
    ids = np.zeros((max(ys) - oy + 1, max(zs) - oz + 1, max(xs) - ox + 1), np.int32)
    for (x, y, z), slot in cells.items():
        ids[y - oy, z - oz, x - ox] = slot
    return schem.Model(ids, pal), (ox, oy, oz)


def clashes(items) -> list:
    """Which two modules contend for which cells - a work problem, so reported per PAIR."""
    owner, pairs = {}, Counter()
    for name, v, u, m, plane in items:
        for y, z, x in zip(*m.solid().nonzero()):
            pos = (int(x) + v, int(y) - plane + 1, int(z) + u)
            prior = owner.get(pos)
            if prior is None:
                owner[pos] = name
            elif prior != name:
                pairs[tuple(sorted((prior, name)))] += 1
    return [(a, b, n) for (a, b), n in pairs.most_common()]


def against_ground(model, origin) -> int:
    """Cells the buildings and the ground layer both claim. The ground's own floor is y0."""
    ways = ROOT / "out" / "Park Ways.litematic"
    if not ways.exists():
        return -1
    w = schem.load(str(ways)).solid()
    ox, oy, oz = origin
    hit = 0
    for y, z, x in zip(*model.solid().nonzero()):
        gx, gy, gz = int(x) + ox, int(y) + oy, int(z) + oz
        if 0 <= gy < w.shape[0] and 0 <= gz < w.shape[1] and 0 <= gx < w.shape[2] and w[gy, gz, gx]:
            hit += 1
    return hit



def complete(items):
    """GROUND + RAILWAY + BUILDINGS AS ONE DESIGN, because three placements hide each other.

    Jack: "the land disappears when i try to place the buildings, i need to be able to see all."
    Three schematics whose bounding boxes overlap are three placements Litematica draws on top of
    one another, and the one you are looking at is whichever won - which is the same complaint the
    casino produced ("stop with the defer crap so i can actually see everything in totality") and
    the same answer: ship the whole thing as one artifact and keep the pieces for building in
    stages.

    PRECEDENCE IS BUILDINGS > RAILWAY > GROUND, and it is REPORTED rather than applied quietly.
    The ground is laid under a building on purpose - a floor that stops at the wall leaves a hole
    the moment anything moves - so the building has to win the cells they share or the picture
    shows paving drawn through a wall.
    """
    import numpy as np
    from collections import Counter
    ways = schem.load(str(ROOT / "out" / "Park Ways.litematic"))
    rail = schem.load(str(ROOT / "out" / "Park Rail.litematic"))
    model, origin = merge(items)

    height = 220
    sz, sx = ways.ids.shape[1], ways.ids.shape[2]
    ids = np.zeros((height, sz, sx), np.int32)
    pal, index = [nbt.block_state("minecraft:air")], {}
    contested = Counter()

    def lay(m, ov, oy, ou, tag):
        names = {i: e.value["Name"].value for i, e in enumerate(m.palette)}
        props = {i: e.value.get("Properties") for i, e in enumerate(m.palette)}
        for y, z, x in zip(*m.solid().nonzero()):
            Y, Z, X = int(y) + oy, int(z) + ou, int(x) + ov
            if not (0 <= Y < height and 0 <= Z < sz and 0 <= X < sx):
                continue
            if ids[Y, Z, X]:
                contested[tag] += 1
                continue
            key = int(m.ids[y, z, x])
            state = (names[key], str(props[key]))
            slot = index.get(state)
            if slot is None:
                slot = index[state] = len(pal); pal.append(m.palette[key])
            ids[Y, Z, X] = slot

    lay(model, origin[0], origin[1] - min(0, origin[1]), origin[2], "buildings")
    lay(rail, 172, 0 - min(0, origin[1]), 0, "railway")
    lay(ways, 0, 0 - min(0, origin[1]), 0, "ground")
    return schem.Model(ids, pal), (0, min(0, origin[1]), 0), contested


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ship", action="store_true")
    args = ap.parse_args()

    items = modules(report=True)
    print(f"{len(items)} built modules with a measured lot\n")
    for name, v, u, m, plane in items:
        sy, sz, sx = m.ids.shape
        print(f"  {name:<24}{int(m.solid().sum()):>7} at V{v:<4}U{u:<4} {sx:>3}x{sy:>3}x{sz:<3}"
              f"  plane {plane}")
    found = clashes(items)
    print("\nmodule clashes:", "none" if not found else "")
    for a, b, n in found:
        print(f"  {a} x {b}: {n} cells")

    model, origin = merge(items)
    sy, sz, sx = model.ids.shape
    print(f"\nPark Buildings  {sx}x{sy}x{sz}  {int(model.solid().sum()):,} blocks"
          f"  origin V{origin[0]} y{origin[1]} U{origin[2]}")
    print(f"cells also claimed by the ground layer: {against_ground(model, origin)}")

    if args.ship:
        out = ROOT / "out" / "Park Buildings.litematic"
        meta = {"origin": {"x": ANCHOR[0] + origin[0], "y": ANCHOR[1] + origin[1],
                           "z": ANCHOR[2] + origin[2]},
                "kind": "park", "name": "Park Buildings",
                "generated_by": "tools/park_place.py",
                "anchor_status": "PREVIEW placement; rebase before building",
                "contains": [i[0] for i in items]}
        scan.save_pair(str(out), model, meta, name="Park Buildings")
        dest = Path(mcprofile.load()["schem_dir"])
        shutil.copy2(out, dest / out.name)
        (dest / "Park Buildings.scan.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"\nshipped -> {dest / out.name}")

        whole, worigin, contested = complete(items)
        wout = ROOT / "out" / "Park Complete.litematic"
        wmeta = {"origin": {"x": ANCHOR[0] + worigin[0], "y": ANCHOR[1] + worigin[1],
                            "z": ANCHOR[2] + worigin[2]},
                 "kind": "park", "name": "Park Complete",
                 "generated_by": "tools/park_place.py",
                 "anchor_status": "PREVIEW placement; rebase before building",
                 "contains": ["Park Ways", "Park Rail"] + [i[0] for i in items]}
        scan.save_pair(str(wout), whole, wmeta, name="Park Complete")
        shutil.copy2(wout, dest / wout.name)
        (dest / "Park Complete.scan.json").write_text(json.dumps(wmeta, indent=2), encoding="utf-8")
        wy, wz, wx = whole.ids.shape
        print("")
        print(f"Park Complete   {wx}x{wy}x{wz}  {int(whole.solid().sum()):,} blocks")
        print(f"   contested cells yielded to the winner: {dict(contested)}")
        print(f"shipped -> {dest / wout.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
