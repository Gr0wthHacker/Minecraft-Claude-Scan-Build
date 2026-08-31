"""Functional redstone fitted to a capture. First one: the hopper-line item sorter.

**THE LANE IS COPIED FROM A KNOWN-GOOD BUILD, NOT DESIGNED HERE.** Jack supplied
`item_filter.schem` (a working four-lane filter) after this generator's own sorter was found to be
broken, and every redstone cell below is read off that reference. That is the whole lesson of this
file: a sorter that looks right and voids items is worse than one that plainly does not run, so
the circuit is a faithful copy of one that works and the tests compare it against the reference
file rather than against anybody's memory.

The lane, seen from the side (items travel along the top hopper, mechanism to the left):

        y+1   ww ww .. Hp        the travelling line
        y     ww gl ST Cm Hp     comparator, and the FILTER hopper it locks
        y-1   ST TT Rp ST Hp Ch  torch, repeater, and the hopper feeding the chest

**THE COMPARATOR FACES INTO THE FILTER HOPPER, AND IT IS NOT READING IT.** It DRIVES it: a
comparator's output locks the hopper, and its own input arrives from BEHIND, off a smooth-stone
block that the wire bus above weakly powers. The wiki's rule is the one that makes this legal - a
weakly powered block *"cannot power adjacent redstone dust, but can still ... power redstone
repeaters and redstone comparators facing away from the block"*.

That distinction cost a real mistake earlier the same day, and it is worth writing down: this
generator ORIGINALLY had the orientation right, the circuit inspection reported *"comparator reads
nothing"*, and the general rule "a comparator reads what is behind it" was applied to turn it
round. The rule is true and the inference was wrong - the comparator's rear input here is a
weakly-powered BLOCK, not the container, and the old lane's real fault was that it had nothing
behind it and no lock line at all. A reference build settled in one minute what reasoning had got
backwards twice.

The filter stock is the part people get wrong and no generator can place it: each filter hopper
wants ONE of the target item plus FOUR unstackable filler items, so the comparator reads exactly
the level the lock is tuned to. `filters` labels the lanes with signs and the meta carries the
list for you to load by hand.
"""
from __future__ import annotations

from .canvas import Canvas
from .vertical import Ctx, World

SORTER = {
    "under": None,             # capture, so the run can be checked against the real world
    "start": None,             # world (x, y, z) of the first lane's FILTER hopper
    "run": "z+",               # direction the items travel: x+, x-, z+ or z-
    "lanes": 12,               # one category per lane
    "filters": [],             # item names, one per lane; only used for the sign labels
    "chest": "chest",
    "depth": 3,                # chest rows under each lane
    "body": "smooth_stone",    # the block the mechanism sits in, as the reference uses
    "glass": "glass",
    "sign": "oak_wall_sign",
    "check": True,             # refuse cells that collide with the capture
}

STEP = {"x+": (1, 0), "x-": (-1, 0), "z+": (0, 1), "z-": (0, -1)}
# a hopper's `facing` is the side it pushes OUT of, so the line points along the run
FACE = {"x+": "east", "x-": "west", "z+": "south", "z-": "north"}
BACK = {"x+": "west", "x-": "east", "z+": "north", "z-": "south"}
# the mechanism sits to one side of the run; `LEFT` is that side, `RIGHT` is where chests go
LEFT = {"x+": (0, -1), "x-": (0, 1), "z+": (1, 0), "z-": (-1, 0)}
LEFT_FACE = {"x+": "north", "x-": "south", "z+": "east", "z-": "west"}
RIGHT_FACE = {"x+": "south", "x-": "north", "z+": "west", "z-": "east"}


def build_sorter(cfg: dict, donors=None) -> Canvas:
    p = {**SORTER, **cfg}
    if not p.get("start"):
        raise ValueError("sorter needs params.start = [x, y, z] of the first lane's filter hopper")
    if p["run"] not in STEP:
        raise ValueError(f"run must be one of {sorted(STEP)}")
    ctx = Ctx(p["under"]) if p.get("under") else None
    sx, sy, sz = (int(v) for v in p["start"])
    dx, dz = STEP[p["run"]]
    lx, lz = LEFT[p["run"]]                 # one step toward the mechanism
    rx, rz = -lx, -lz                       # ...and toward the chests
    w, placed, skipped = World(), [], []

    for i in range(int(p["lanes"])):
        x, z = sx + dx * i, sz + dz * i
        if p["check"] and ctx is not None and _busy(ctx, x, sy, z):
            skipped.append([x, sy, z])
            continue

        # --- the line and the filter, copied cell for cell from the reference
        w.put(x, sy + 1, z, "hopper", facing=FACE[p["run"]], enabled="true")   # travelling line
        w.put(x, sy, z, "hopper", facing=RIGHT_FACE[p["run"]], enabled="true")  # FILTER

        # --- the lock line, to the LEFT of the run
        # comparator faces INTO the filter hopper: it locks it, and reads the block behind itself.
        w.put(x + lx, sy, z + lz, "comparator",
              facing=RIGHT_FACE[p["run"]], mode="compare", powered="false")
        w.put(x + lx * 2, sy, z + lz * 2, p["body"])          # weakly powered by the bus above
        w.put(x + lx * 3, sy, z + lz * 3, p["glass"])
        w.put(x + lx * 4, sy, z + lz * 4, "redstone_wire")    # the bus, shared down the run
        w.put(x + lx * 4, sy - 1, z + lz * 4, p["body"])
        w.put(x + lx * 3, sy - 1, z + lz * 3, "redstone_wall_torch",
              facing=RIGHT_FACE[p["run"]], lit="true")
        w.put(x + lx * 2, sy - 1, z + lz * 2, "repeater",
              facing=LEFT_FACE[p["run"]], delay="1", powered="false", locked="false")
        w.put(x + lx, sy - 1, z + lz, p["body"])
        w.put(x + lx * 3, sy + 1, z + lz * 3, "redstone_wire")
        w.put(x + lx * 2, sy + 1, z + lz * 2, "redstone_wire")
        w.put(x + lx * 2, sy - 2, z + lz * 2, p["body"])

        # --- the output: a hopper column into chests, to the RIGHT
        for d in range(int(p["depth"])):
            w.put(x, sy - 1 - d, z, "hopper", facing=RIGHT_FACE[p["run"]], enabled="true")
            w.put(x + rx, sy - 1 - d, z + rz, p["chest"],
                  facing=BACK[p["run"]], type="single", waterlogged="false")

        label = p["filters"][i] if i < len(p["filters"]) else ""
        if label:
            w.put(x + rx, sy, z + rz, p["sign"], facing=RIGHT_FACE[p["run"]], waterlogged="false")
        placed.append([x, sy, z, label])

    if not placed:
        raise ValueError("every lane collided with the capture - move `start` or shorten the run")
    return w.canvas({
        "kind": "sorter", "run": p["run"], "lanes": len(placed), "skipped": skipped,
        "cells": placed,
        "source": "item_filter.schem (a working reference build), lane copied cell for cell",
        "filter_stock": [{"lane": i, "item": c[3], "target": 1, "filler": 4}
                         for i, c in enumerate(placed)],
        "note": "each filter hopper needs 1 of its target item + 4 UNSTACKABLE filler items; "
                "the generator cannot place items, load them by hand",
    })


def _busy(ctx: Ctx, x: int, y: int, z: int) -> bool:
    return ctx.occupied(x, y, z)
