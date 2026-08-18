"""Patterned hide for statues: the pattern, separated from the animal.

    voronoi(...)   polygonal patches with a pale line BETWEEN them - a giraffe's coat, literally.
                   Cellular (Worley) noise: scatter seeds on a jittered lattice, give every cell to
                   its nearest seed, and paint the cells where the nearest two seeds are almost tied.
    blotches(...)  the older soft value-noise blobs, for coats that really are blobby (cow, fox).

Why this is its own module: the first three giraffes used value noise, which makes amorphous clouds
that run into each other. A giraffe's patches are hard-edged polygons divided by cream channels, and
that grout is the single most identifying thing about the animal - more than the neck, at a distance.
Value noise cannot make it at any parameter setting, because the thing that defines it is a BOUNDARY
between regions, and value noise has no regions.

Both take and return plain (x, y, z) -> block name, so any generator can dress a shape with them.
"""
from __future__ import annotations

import math

from .canvas import hash01


def voronoi(cells, patch, grout, *, scale: float = 6.0, grout_width: float = 0.55,
            jitter: float = 0.85, seed: int = 0, tones=None) -> dict:
    """Hard-edged patches separated by grout lines.

    scale        average patch width in blocks
    grout_width  how wide the pale channel is; the units are "difference between the distances to the
                 nearest two seeds", so it stays about constant in blocks as `scale` changes
    tones        optional list of patch blocks; each patch takes one, so the coat has tonal variation
                 without the boundaries going soft
    """
    out = {}
    for (x, y, z) in cells:
        d1, d2, owner = _two_nearest(x, y, z, scale, jitter, seed)
        if d2 - d1 < grout_width:
            out[(x, y, z)] = grout
        elif tones:
            out[(x, y, z)] = tones[owner % len(tones)]
        else:
            out[(x, y, z)] = patch
    return out


def _two_nearest(x, y, z, scale, jitter, seed):
    """Distance to the closest and second-closest seed, and a stable id for the closest.

    Seeds live one per lattice cell of side `scale`, jittered inside it. Searching the 3x3x3 lattice
    block around the point is enough: a seed further than one cell away cannot be nearest.
    """
    fx, fy, fz = x / scale, y / scale, z / scale
    ix, iy, iz = math.floor(fx), math.floor(fy), math.floor(fz)
    d1 = d2 = 1e9
    owner = 0
    for gx in range(ix - 1, ix + 2):
        for gy in range(iy - 1, iy + 2):
            for gz in range(iz - 1, iz + 2):
                sx = gx + 0.5 + jitter * (hash01(gx, gy, gz, 101, seed) - 0.5)
                sy = gy + 0.5 + jitter * (hash01(gx, gy, gz, 103, seed) - 0.5)
                sz = gz + 0.5 + jitter * (hash01(gx, gy, gz, 107, seed) - 0.5)
                d = math.sqrt((fx - sx) ** 2 + (fy - sy) ** 2 + (fz - sz) ** 2) * scale
                if d < d1:
                    d2, d1 = d1, d
                    owner = (gx * 73856093) ^ (gy * 19349663) ^ (gz * 83492791)
                elif d < d2:
                    d2 = d
    return d1, d2, abs(owner)


def blotches(cells, patch, ground, *, scale: float = 5.0, rate: float = 0.5, seed: int = 0) -> dict:
    """Soft value-noise blobs. Right for a cow or a fox; wrong for a giraffe."""
    sc = max(1.0, scale)
    out = {}
    for (x, y, z) in cells:
        n = sum(hash01(int(x // sc) + a, int(y // sc) + b, int(z // sc) + c, 7, seed)
                for a in (0, 1) for b in (0, 1) for c in (0, 1)) / 8.0
        out[(x, y, z)] = patch if n > rate else ground
    return out
