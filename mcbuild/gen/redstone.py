"""Functional redstone fitted to a capture. First one: the hopper-line item sorter.

    sorter: a straight run of filter cells. Items travel along a hopper line under a feeder chest;
            each cell's filter hopper points into a chest, is held shut by a redstone torch, and
            opens only when its comparator reads the filter stock. One cell per category.

Every cell is 1 wide along the run and 5 tall, so a 16-lane sorter is 16x5x3.

    y+3   feeder hopper line  (items travel along this, pointing to the next cell)
    y+2   filter hopper       (points DOWN into the chest; holds 1 target + 4 filler)
    y+1   chest               (the sorted output)
    y+0   comparator + torch  (comparator reads the filter hopper, torch locks it shut)

The filter stock is the part people get wrong: each filter hopper wants ONE of the target item plus
FOUR unstackable filler items, so the comparator reads exactly the level the torch is tuned to. The
generator cannot place items, so `filters` only labels the lanes with signs and the meta carries the
list for you to load by hand.
"""
from __future__ import annotations

from .canvas import Canvas
from .vertical import Ctx, World

SORTER = {
    "under": None,             # capture, so the run can be checked against the real world
    "start": None,             # world (x, y, z) of the first cell's comparator course
    "run": "z+",               # direction the items travel: x+, x-, z+ or z-
    "lanes": 12,               # one category per lane
    "filters": [],             # item names, one per lane; only used for the sign labels
    "chest": "chest",
    "body": "stone_bricks",    # the block the torches sit on
    "sign": "oak_wall_sign",
    "check": True,             # refuse cells that collide with the capture
}

STEP = {"x+": (1, 0), "x-": (-1, 0), "z+": (0, 1), "z-": (0, -1)}
# a hopper's `facing` is the side it pushes OUT of, so the line points along the run
FACE = {"x+": "east", "x-": "west", "z+": "south", "z-": "north"}
BACK = {"x+": "west", "x-": "east", "z+": "north", "z-": "south"}


def build_sorter(cfg: dict, donors=None) -> Canvas:
    p = {**SORTER, **cfg}
    if not p.get("start"):
        raise ValueError("sorter needs params.start = [x, y, z] of the first cell")
    if p["run"] not in STEP:
        raise ValueError(f"run must be one of {sorted(STEP)}")
    ctx = Ctx(p["under"]) if p.get("under") else None
    sx, sy, sz = (int(v) for v in p["start"])
    dx, dz = STEP[p["run"]]
    w, placed, skipped = World(), [], []

    for i in range(int(p["lanes"])):
        x, z = sx + dx * i, sz + dz * i
        if p["check"] and ctx is not None and _busy(ctx, x, sy, z):
            skipped.append([x, sy, z])
            continue
        # comparator course: the torch sits on a body block and locks the filter hopper above it
        w.put(x, sy, z, p["body"])
        w.put(x - dz, sy, z - dx, p["body"])                     # the torch's own block, beside the run
        w.put(x - dz, sy + 1, z - dx, "redstone_torch", lit="true")
        w.put(x, sy + 1, z, p["chest"], facing=BACK[p["run"]], type="single", waterlogged="false")
        w.put(x, sy + 2, z, "hopper", facing="down", enabled="true")          # filter -> chest
        w.put(x, sy + 3, z, "hopper", facing=FACE[p["run"]], enabled="true")  # the travelling line
        w.put(x + dz, sy + 2, z + dx, "comparator", facing=_toward(dz, dx),
              mode="compare", powered="false")
        w.put(x + dz, sy + 1, z + dx, p["body"])
        label = p["filters"][i] if i < len(p["filters"]) else ""
        if label:
            w.put(x - dz, sy + 2, z - dx, p["sign"], facing=BACK[p["run"]], waterlogged="false")
        placed.append([x, sy, z, label])

    if not placed:
        raise ValueError("every lane collided with the capture - move `start` or shorten the run")
    return w.canvas({
        "kind": "sorter", "run": p["run"], "lanes": len(placed), "skipped": skipped,
        "cells": placed,
        "filter_stock": [{"lane": i, "item": c[3], "target": 1, "filler": 4} for i, c in enumerate(placed)],
        "note": "each filter hopper needs 1 of its target item + 4 UNSTACKABLE filler items; "
                "the generator cannot place items, load them by hand",
    })


def _toward(dz: int, dx: int) -> str:
    """Facing that points a comparator back at the filter hopper beside it."""
    if dz:
        return "west" if dz > 0 else "east"
    return "north" if dx > 0 else "south"


def _busy(ctx: Ctx, x: int, y: int, z: int) -> bool:
    for dy in range(0, 4):
        for ox in (-1, 0, 1):
            for oz in (-1, 0, 1):
                if ctx.name_at(x + ox, y + dy, z + oz) not in ("air", "cave_air", "void_air", "vine"):
                    return True
    return False
