"""Re-slice a plan's modules into a few COMPLETE layers, one per build step.

**A DESIGN THAT DEFERS IS INCOMPLETE ON ITS OWN, AND THAT IS WHAT MAKES THIRTY OF THEM
UNREADABLE.** `finish.defer_to` settles which design owns a shared cell, which is exactly right
for cell ownership and exactly wrong for looking at the result: every module ends up as a fragment
with holes in it where a neighbour won. Load all thirty and you are looking at thirty overlapping
boxes, each one missing pieces - Jack's report was "empty floors with holes in it for redstone and
nothing above it", which is a precise description of the hall on its own.

So the plan is sliced by LAYER instead:

    1 Floor      the walking surface - one plane you can stand on
    2 Machines   everything under it: pits, wire, droppers, the whole mechanism
    3 Walls      everything over it: room walls, ceilings, the perimeter, stairs
    4 Fittings   signs, lanterns, buttons, carpet - what makes it readable

**LAYERS CANNOT COLLIDE, SO NOTHING DEFERS.** The partition is a function of the cell, so every
cell lands in exactly one layer by construction - there is no ownership question left to settle
and no design is missing anything. Each one is complete, loads on its own, and the four together
are the whole casino with nothing hidden.

It also gives a build ORDER that matches how you would actually build it: stand the floor, hang
the machines under it, raise the walls, then fit it out.
"""
from __future__ import annotations

import collections
import json
import os

import numpy as np

from . import scan as scan_mod
from . import schem, work
from .gen.canvas import Canvas

# What goes in the fittings layer wherever it sits: these are the READABLE parts, and pulling them
# out means you can place the whole casino and then decide whether you want the dressing.
FITTINGS = {
    "oak_wall_sign", "sign", "lantern", "soul_lantern", "torch", "wall_torch",
    "stone_button", "redstone_lamp", "red_carpet", "carpet",
}

# Anything that is part of a mechanism belongs with the machines wherever it sits - a button is a
# fitting but the wire it drives is not, and a lamp above the floor is a display.
MACHINE = {
    "redstone_wire", "repeater", "comparator", "dropper", "dispenser", "hopper", "observer",
    "piston", "sticky_piston", "redstone_block", "redstone_torch", "redstone_wall_torch",
    "note_block", "barrel", "chest", "trapped_chest", "lever", "target", "daylight_detector",
}

LAYERS = ["Floor", "Machines", "Walls", "Fittings"]


def _which(name: str, y: int, floor_y: int) -> str:
    """THE PARTITION. One cell, one layer, decided by what it is and where it sits.

    Machines win over height, because a mechanism that is half under the floor and half above it
    is still one machine and splitting it would give you two layers neither of which works.
    """
    if name in MACHINE:
        return "Machines"
    if name in FITTINGS:
        return "Fittings"
    if y < floor_y:
        return "Machines"          # anything under the floor is the mechanism's basement
    if y == floor_y:
        return "Floor"
    return "Walls"


def _read(design: str, out_dir: str = "out"):
    """Every cell of a design as {(x, y, z): (name, props)}, its sign text, and its DIG list.

    **A LITEMATIC CANNOT EXPRESS REMOVAL, SO THE PREP WORK LIVES IN THE SIDECAR - AND THE SLICE
    WAS DROPPING IT.** `layers.py` had no notion of `dig` at all, so every module's "break this
    first" list vanished the moment the plan was sliced: the Arrival Court declares 324 cells of
    starter pad and tree that have to come out before a printer can lay its floor, and the
    shipped `Park_Centre Complete` reported `dig 0`. `/cscan dig` would have shown nothing and
    the first anybody knew of it would be a printer refusing to place on a grass block.
    """
    mo = schem.load(os.path.join(out_dir, f"{design}.litematic"))
    sc = scan_mod.load(os.path.join(out_dir, f"{design}.scan.json"))
    ox, oy, oz = sc.origin
    names, props = [], []
    for t in mo.palette:
        try:
            names.append(t.value["Name"].value.split(":")[-1])
            pr = t.value.get("Properties")
            props.append({k: v.value for k, v in pr.value.items()} if pr is not None else {})
        except Exception:                                        # noqa: BLE001
            names.append("air")
            props.append({})
    cells = {}
    ys, zs, xs = np.nonzero(mo.ids)
    for y, z, x in zip(ys, zs, xs):
        i = mo.ids[y, z, x]
        if names[i] == "air":
            continue
        cells[(ox + int(x), oy + int(y), oz + int(z))] = (names[i], props[i])

    signs = {}
    for t in mo.tile_entities:
        v = t.value
        try:
            pos = (ox + int(v["x"].value), oy + int(v["y"].value), oz + int(v["z"].value))
            front = [j.value for j in v["front_text"].value["messages"].value]
            signs[pos] = front
        except Exception:                                        # noqa: BLE001
            continue
    # `Scan` does not surface `dig` as an attribute, so read the sidecar's own JSON.
    import json as _json
    with open(os.path.join(out_dir, f"{design}.scan.json"), encoding="utf-8") as fh:
        _raw = _json.load(fh)
    return cells, signs, [tuple(int(v) for v in c) for c in (_raw.get("dig") or [])]


def _plan_plane(pl) -> int | None:
    """The course this plan's own build plane sits on, read off the module that IS the ground.

    A plaza covers a land and never moves off the plane, so it is the one module whose height
    answers "what is level zero here". Deriving it from the modules' average or their lowest cell
    would move it every time a ride went underground - which is the very thing it has to measure
    the lift against. A plan with no plaza has one level and says so with `None`.
    """
    hub = next((m for m in getattr(pl, "modules", ())
                if m.get("covers") and m.get("kind") == "plaza"), None)
    return int(hub["at"][1]) if hub else None


def slice_plan(plan_name: str, floor_y: int, out_dir: str = "out",
               prefix: str | None = None) -> list:
    """Write one complete design per layer. Returns [(name, cells)] in BUILD order."""
    from . import planner
    pl = planner.Plan.load(plan_name)
    prefix = prefix or plan_name.title()

    # **THE PRECEDENCE LIVES HERE, ONCE, AND IT IS EXPLICIT.**
    #
    # The modules no longer defer, so they overlap - the hall's floor runs under every room. FIRST
    # WRITER WINS, in plan order, which is the same precedence `defer_to` used to enforce by
    # deleting cells from the loser: a room owns its own floor and the hall lays only the ground
    # between them. Doing it here means the modules stay whole and one place decides.
    # **A SLICE IS PER BAND, NOT PER PLAN.** `_which` puts everything below `floor_y` into
    # Machines, which was right while the only thing under a park's floor WAS its wiring. A
    # vertical park has ROOMS down there - the Frontier's mine ride stands 24 courses under its
    # own headframe - and sliced against one global floor the whole ride came out as the
    # mechanism's basement: a printer would be handed a Machines layer containing a station, its
    # walls and its track.
    #
    # So each cell is judged against the floor of the MODULE it came from, which is the plan's
    # own floor shifted by that module's lift off the build plane. Recorded at the moment a cell
    # is claimed, because first-writer-wins runs across modules and the loser's floor is not the
    # one the cell was built to.
    plane = _plan_plane(pl)
    cells: dict = {}
    floors: dict = {}
    signs: dict = {}
    dig: list = []
    seen_dig: set = set()
    contested = 0
    for m in pl.modules:
        c, s, d = _read(m["name"], out_dir)
        here = floor_y if plane is None else floor_y + (int(m["at"][1]) - plane)
        for cell in d:
            if cell not in seen_dig:
                seen_dig.add(cell)
                dig.append(list(cell))
        for pos, v in c.items():
            if pos in cells:
                if cells[pos] != v:
                    contested += 1
                continue                      # first writer keeps it
            cells[pos] = v
            floors[pos] = here
        signs.update(s)
    if contested:
        print(f"  {contested} contested cells resolved by plan order (the hall under the rooms)")
    levels = sorted({v for v in floors.values()})
    if len(levels) > 1:
        print(f"  {len(levels)} build levels: " + ", ".join(f"Y{v}" for v in levels))

    buckets: dict = collections.defaultdict(dict)
    for pos, (name, props) in cells.items():
        buckets[_which(name, pos[1], floors.get(pos, floor_y))][pos] = (name, props)

    written = []
    # **THE WHOLE THING, AS ONE DESIGN.** The layers are the build steps; this is the answer to
    # "let me see everything in totality" - one file, nothing deferred, nothing hidden, which is
    # what you load when you want to look at the casino rather than build it.
    whole = f"{prefix} Complete"
    written.append((whole, _write_layer(whole, cells, signs, out_dir, whole=True, dig=dig)))
    for layer in LAYERS:
        got = buckets.get(layer)
        if not got:
            continue
        name = f"{prefix} {LAYERS.index(layer) + 1} {layer}"
        # A LAYER CARRIES NO DIG LIST. Breaking a block is not part of any one course;
        # it is prep for the build, and it belongs to the design you actually place.
        written.append((name, _write_layer(name, got, signs, out_dir)))
    return written


def _write_layer(name: str, cells: dict, signs: dict, out_dir: str, whole: bool = False,
                 dig=None) -> int:
    xs = [p[0] for p in cells]
    ys = [p[1] for p in cells]
    zs = [p[2] for p in cells]
    x0, y0, z0 = min(xs), min(ys), min(zs)
    c = Canvas(max(xs) - x0 + 1, max(ys) - y0 + 1, max(zs) - z0 + 1)
    for (x, y, z), (blk, props) in cells.items():
        c.put(x - x0, y - y0, z - z0, c.raw_state(blk, **props))
        # A SIGN'S TEXT FOLLOWS ITS BLOCK into whichever layer the block landed in. Left behind it
        # would be a tile entity with no block, which is a corrupt region rather than a lost line.
        if (x, y, z) in signs:
            c.sign_text(x - x0, y - y0, z - z0, signs[(x, y, z)])
    c.world_origin = (x0, y0, z0)
    m = c.to_model()

    path = os.path.join(out_dir, f"{name}.litematic")
    scan_mod.save_pair(path, m, {
        "origin": {"x": x0, "y": y0, "z": z0},
        "size": {"x": m.ids.shape[2], "y": m.ids.shape[0], "z": m.ids.shape[1]},
        "generated_by": "mcbuild.layers",
        "kind": "casino-layer",
        # **A SLICE IS HALF A MACHINE, AND ANY CHECKER MUST BE TOLD SO.** A layer holds the part of
        # every circuit that landed in it, so the wire crossing the floor course reads as dust with
        # no source and the dropper above it reads as unwired - `tools/redstone_audit.py` reported
        # 301 such faults over the layers alone, every one of them a cut rather than a defect. It
        # is rule 2 (verify in CONTEXT, never in isolation) applied to this project's own slicing:
        # the context for a layer is the whole.
        "dig": list(dig or []),
        "slice": not whole,
        "note": ("the whole thing, nothing deferred" if whole else
                 "one build step; a SLICE of the whole, so its circuits are cut at the seam"),
    }, name=name)
    work.write(path, m, (x0, y0, z0), name)
    return int((m.ids > 0).sum())


def ship(written: list, schem_dir: str, out_dir: str = "out") -> None:
    import shutil
    for name, _n in written:
        for ext in (".litematic", ".scan.json", ".work.json"):
            src = os.path.join(out_dir, f"{name}{ext}")
            if os.path.exists(src):
                shutil.copy(src, os.path.join(schem_dir, os.path.basename(src)))
