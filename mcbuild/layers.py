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
    """Every cell of a design as {(x, y, z): (name, props)}, plus its sign text."""
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
    return cells, signs


def slice_plan(plan_name: str, floor_y: int, out_dir: str = "out",
               prefix: str | None = None) -> list:
    """Write one complete design per layer. Returns [(name, cells)] in BUILD order."""
    from . import planner
    pl = planner.Plan.load(plan_name)
    prefix = prefix or plan_name.title()

    cells: dict = {}
    signs: dict = {}
    for m in pl.modules:
        c, s = _read(m["name"], out_dir)
        # LAST WRITER WINS, and it does not matter: the plan is already asserted to have zero
        # cross-design clashes, so where two modules share a cell they agree on what is in it.
        cells.update(c)
        signs.update(s)

    buckets: dict = collections.defaultdict(dict)
    for pos, (name, props) in cells.items():
        buckets[_which(name, pos[1], floor_y)][pos] = (name, props)

    written = []
    for layer in LAYERS:
        got = buckets.get(layer)
        if not got:
            continue
        name = f"{prefix} {LAYERS.index(layer) + 1} {layer}"
        written.append((name, _write_layer(name, got, signs, out_dir)))
    return written


def _write_layer(name: str, cells: dict, signs: dict, out_dir: str) -> int:
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
        "note": "one complete build step; layers cannot collide, so nothing defers",
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
