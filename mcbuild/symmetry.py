"""Intent-aware symmetry: preserve structure, permit declared asymmetric storytelling."""
from __future__ import annotations

import numpy as np


def assess(model, *, axis: str = "x", core=None, exceptions=(), min_core_match: float = 0.92) -> dict:
    """Measure mirrored structural balance while excluding intentional asymmetric regions.

    ``core`` is `[x0,y0,z0,x1,y1,z1]`; omissions use the whole model. Exceptions are local boxes
    for doors, chimneys, damage, terrain, service doors, ride exits, or focal composition.
    """
    if axis != "x": raise ValueError("only x-axis facade symmetry is currently supported")
    sy, sz, sx = model.ids.shape
    x0, y0, z0, x1, y1, z1 = core or [0, 0, 0, sx - 1, sy - 1, sz - 1]
    ignored = set()
    for box in exceptions:
        ax0, ay0, az0, ax1, ay1, az1 = map(int, box)
        ignored |= {(x, y, z) for x in range(ax0, ax1 + 1) for y in range(ay0, ay1 + 1) for z in range(az0, az1 + 1)}
    compared = matches = 0
    for y in range(y0, y1 + 1):
        for z in range(z0, z1 + 1):
            for x in range(x0, (x0 + x1 + 1) // 2):
                mirror = x0 + x1 - x
                if (x, y, z) in ignored or (mirror, y, z) in ignored: continue
                compared += 1; matches += int(model.ids[y, z, x] == model.ids[y, z, mirror])
    match = matches / max(1, compared)
    return {"ok": match >= min_core_match, "axis": axis, "core_match": round(match, 4),
            "compared": compared, "intentional_asymmetry_cells": len(ignored),
            "guidance": "symmetry supports formal structure; declare exceptions for focal/story/service asymmetry"}
