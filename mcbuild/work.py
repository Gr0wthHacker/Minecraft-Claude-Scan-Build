"""`<name>.work.json` — a design flattened to a cell list the chunkscan mod can read.

The mod has a Litematica *writer*, not a reader, and teaching it to unpack straddling bit-packed
block states just to answer "what do I place next" is the wrong trade. So the desktop, which already
has the reader, writes the cells out once per generation and the mod diffs them against the live
world itself. That keeps the answer live — the mod never needs a fresh capture to know what is built.

    {"name": ..., "origin": {...}, "count": N,
     "cells": [[x, y, z, "stone_brick_stairs[facing=east,half=bottom]"], ...],   # world coords
     "dig":   [[x, y, z], ...]}                                                  # from the sidecar

A cell carries the properties the design MEANT, and only those. It used to carry the bare block
name, and that made `/cscan check` blind to orientation: the taproot entrance places
`smooth_stone_slab` as both `type=top` and `type=bottom`, `Island Belly Full` places
`mossy_stone_brick_slab` as `type=double` and `type=top` - and check reported every one of them
built whichever way round they went in. 3,441 cells across the designs are stateful like this.
That is the same hole the stair convention fell through: a flight built the wrong way cannot be
walked up, our renderer draws both identically, and the in-game check could not see it either.

WHY NOT EVERY PROPERTY. Most block states are not a decision - they are the game reacting to the
neighbourhood. A stair's `shape` comes from what is beside it, a wall's `north/south/east/west`
from what it touches, `waterlogged` from whether someone poured water in. Comparing those reports
a deviation for a block that is perfectly correct, and a check that cries wolf is a check nobody
runs. So only INTENTIONAL properties are written, and the mod compares exactly what it is given.
"""
from __future__ import annotations

import json
import os

import numpy as np

from . import scan as scan_mod
from .pipeline import DEFAULT_SCHEM_DIR


def path_for(litematic_path: str) -> str:
    return litematic_path[: -len(".litematic")] + ".work.json"


# Properties a design DECIDES. Everything else the game works out from the neighbourhood, and
# comparing it produces a deviation for a block that is exactly right.
INTENTIONAL = {
    "facing",        # stairs, chains on their side, furnaces, wall-mounted anything
    "half",          # stair tread / door leaf - the stair convention lives here
    "type",          # slab bottom / top / DOUBLE, which is a different block entirely
    "axis",          # logs, chains, bone blocks
    "rotation",      # signs, banners, skulls
    "hanging",       # a lantern under a block vs standing on one
    "face",          # floor / wall / ceiling for buttons and levers
    "orientation",   # jigsaws, crafters
    "hinge", "part",  # doors and beds
    "attachment",    # bells
    "vertical_direction",   # pointed dripstone
    "tilt",
}

# DECIDED and COMPLETE are two different questions, and conflating them was the drift.
#
# `INTENTIONAL` is what a design CHOSE, and it is what gets written into a cell string: a stair's
# facing is a decision, its `waterlogged` is whether anyone has poured water in. But the mod needs
# a second set for a different purpose - what must ALSO be true before a cell counts as finished.
# A waterlogged stair needs a bucket after the stair, a powered rail needs its signal, a leaf a
# player placed is persistent, and an open trapdoor is a click no printer makes. All four should
# stand amber in `/cscan check` waiting for a hand, never be reported as built.
#
# The Java side carried these four inside its own INTENTIONAL and this file carried none of them,
# so the same list written twice had quietly diverged. Both sets ship through
# `tools/export_rules.py` now, and `tests/test_items.py` fails if the file and these disagree.
COMPLETION = {"waterlogged", "powered", "persistent", "open"}
# ...and for these the direction flags ARE the decision, not a connection the game made: a vine
# clings to the face BEHIND it, and which face that is decides whether it hangs at all.
MULTIFACE = {"vine", "glow_lichen", "sculk_vein", "resin_clump"}
FACES = {"north", "south", "east", "west", "up", "down"}


def state_string(name: str, props: dict) -> str:
    """`name[a=b,c=d]`, properties sorted, or a bare name when nothing was intended."""
    short = name.split(":")[-1]
    keep = {k: v for k, v in props.items()
            if k in INTENTIONAL or (short in MULTIFACE and k in FACES)}
    if not keep:
        return short
    inner = ",".join(f"{k}={keep[k]}" for k in sorted(keep))
    return f"{short}[{inner}]"


def build(m, origin: tuple[int, int, int], name: str, dig=()) -> dict:
    from . import nbt
    ox, oy, oz = origin
    names = [state_string(nbt.state_name(e), nbt.state_props(e)) for e in m.palette]
    cells = []
    ys, zs, xs = np.where(m.ids > 0)
    for y, z, x in zip(ys, zs, xs):
        cells.append([int(x) + ox, int(y) + oy, int(z) + oz, names[m.ids[y, z, x]]])
    cells.sort(key=lambda c: (c[1], c[0], c[2]))          # bottom-up: never place past your own reach
    # dig entries are [x, y, z] from some generators and [x, y, z, name] from others; the mod only
    # ever wants the position.
    return {"name": name, "origin": {"x": ox, "y": oy, "z": oz}, "count": len(cells),
            "cells": cells, "dig": [[int(d[0]), int(d[1]), int(d[2])] for d in dig]}


def write(litematic_path: str, m, origin, name: str, dig=()) -> str:
    """Write the manifest beside a design.

    **IT IS A MANIFEST NOW, NOT A COPY OF THE DESIGN.** `<name>.work.json` used to carry every cell
    of the build - 21 MB across the folder - and nothing read them: the mod's `Work.cached` takes
    the LITEMATIC whenever one exists beside the sidecar, which is always, and `loadWork` is the
    fallback for a work list with no schematic. So the cell list was megabytes written on every
    generation, parsed by nobody, and free to go stale - `Park Buildings.work.json` was a day older
    than its own litematic, because this was called at 2 of the 21 places a design gets written.

    What the mod cannot get from a litematic is written instead: the world ORIGIN, the dig list,
    and the count. The cells are emitted only when there is no schematic to read them from, which
    is the one case `loadWork` exists for.
    """
    out = path_for(litematic_path)
    data = build(m, origin, name, dig)
    if os.path.exists(litematic_path):
        # THE CELLS LIVE IN THE SCHEMATIC. Dropping them is only safe because their absence is an
        # ERROR on the Java side rather than an empty design - an empty `cells` array read as "no
        # work" would report every design complete, which is the one failure mode worse than a
        # stale file.
        data["schematic"] = os.path.basename(litematic_path)
        data.pop("cells", None)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return out


def regenerate(design: str, schem_dir: str = DEFAULT_SCHEM_DIR) -> str:
    """Write the worklist for an already-saved design."""
    s = scan_mod.load(design, schem_dir)
    dig = s.meta.get("dig", [])
    return write(s.litematic_path, s.model, s.origin, s.meta.get("name", os.path.basename(design)), dig)
