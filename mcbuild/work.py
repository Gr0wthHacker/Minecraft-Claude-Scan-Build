"""`<name>.work.json` — a design flattened to a cell list the chunkscan mod can read.

The mod has a Litematica *writer*, not a reader, and teaching it to unpack straddling bit-packed
block states just to answer "what do I place next" is the wrong trade. So the desktop, which already
has the reader, writes the cells out once per generation and the mod diffs them against the live
world itself. That keeps the answer live — the mod never needs a fresh capture to know what is built.

    {"name": ..., "origin": {...}, "count": N,
     "cells": [[x, y, z, "mossy_stone_bricks"], ...],   # world coordinates, air excluded
     "dig":   [[x, y, z], ...]}                          # carried through from the sidecar
"""
from __future__ import annotations

import json
import os

import numpy as np

from . import scan as scan_mod
from .pipeline import DEFAULT_SCHEM_DIR


def path_for(litematic_path: str) -> str:
    return litematic_path[: -len(".litematic")] + ".work.json"


def build(m, origin: tuple[int, int, int], name: str, dig=()) -> dict:
    ox, oy, oz = origin
    names = [n.split(":")[-1] for n in m.names]
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
    out = path_for(litematic_path)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(build(m, origin, name, dig), f)
    return out


def regenerate(design: str, schem_dir: str = DEFAULT_SCHEM_DIR) -> str:
    """Write the worklist for an already-saved design."""
    s = scan_mod.load(design, schem_dir)
    dig = s.meta.get("dig", [])
    return write(s.litematic_path, s.model, s.origin, s.meta.get("name", os.path.basename(design)), dig)
