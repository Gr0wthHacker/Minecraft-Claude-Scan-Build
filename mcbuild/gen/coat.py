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


def rosettes(cells, ring, ground, *, centre=None, scale: float = 5.0, thickness: float = 0.42,
             broken: float = 0.22, radius: float = 0.60, seed: int = 0) -> dict:
    """A big cat's coat: BROKEN dark rings with a lighter middle, not solid spots.

    That distinction is the whole animal. A leopard has solid spots; a jaguar has rosettes, and a
    voxel build that fills them in reads as a leopard, or as a cow. The ring is the thing.

    Built on the same cellular field as `voronoi`: each seed owns a cell, and the ring is the band of
    cells at a set distance from the seed. `broken` drops a share of the ring so it reads as a cluster
    of marks rather than a drawn circle - real rosettes are made of separate blotches.

    radius     ring radius as a fraction of the seed spacing. Too small and the marks scatter with
               bare ground between them; it wants to be near the cell size so rosettes nearly touch.
    thickness  width of the ring as a fraction of that radius
    broken     share of ring cells left as ground, breaking the outline up
    centre     block for the inside of the rosette (a jaguar's is warmer than its ground); None = ground
    """
    out = {}
    for (x, y, z) in cells:
        d1, _d2, owner = _two_nearest(x, y, z, scale, 0.85, seed)
        r = scale * radius
        inner = r * (1.0 - thickness)
        if inner <= d1 <= r and hash01(x, y, z, 211, seed + owner % 97) > broken:
            out[(x, y, z)] = ring
        elif centre is not None and d1 < inner * 0.72:
            out[(x, y, z)] = centre
        else:
            out[(x, y, z)] = ground
    return out


def shade(cells, ramp, *, base=None, strength: float = 1.0, seed: int = 0, jitter: float = 0.05) -> dict:
    """Shade a solid by FORM: light on what faces the sky, dark in creases and undersides.

    This is the difference between a coloured shape and a statue. A single flat colour gives the eye
    nothing to read the volume by, so a big smooth animal comes out as a grey blob however good its
    proportions are - and every one of these did. Real sculpture is read by its shadows.

    Two things drive it, and they are what a viewer's eye actually uses:
      SKY      how much open air sits directly above a cell. A back is lit; a belly is not.
      CREVICE  how enclosed it is among its 26 neighbours. Necks, armpits and the join between a leg
               and a barrel are the places a form reads as folding into itself.

    `ramp` is a list of blocks dark->light (build one with `mcbuild.blocks.ramp`). A little jitter
    breaks up the banding you get when a smooth surface crosses a threshold all at once.
    """
    import numpy as np
    from .. import morph
    if not ramp:
        return {}
    cells = list(cells)
    xs = [c[0] for c in cells]; ys = [c[1] for c in cells]; zs = [c[2] for c in cells]
    ox, oy, oz = min(xs) - 2, min(ys) - 2, min(zs) - 2
    a = np.zeros((max(ys) - oy + 3, max(zs) - oz + 3, max(xs) - ox + 3), dtype=bool)
    for (x, y, z) in cells:
        a[y - oy, z - oz, x - ox] = True
    n26 = morph.neighbor_count(a, conn=26)
    # sky: how far up is clear, capped - beyond a few blocks it stops mattering to the eye
    CAP = 4
    sky = np.zeros(a.shape, dtype=float)
    for k in range(1, CAP + 1):
        shifted = np.zeros_like(a)
        shifted[:-k or None] = a[k:]
        sky += (~shifted).astype(float)
    # SKIN ONLY. An interior cell has nothing above it and neighbours on all sides, so it scores as
    # the deepest crease there is - and since most of a solid animal is interior, shading everything
    # made two thirds of the elephant deepslate. Nobody can see those blocks; they take the mid tone.
    n6 = morph.neighbor_count(a, conn=6)
    mid = ramp[len(ramp) // 2]
    out = {}
    top = len(ramp) - 1
    # normalise across the SURFACE's own range, so the ramp is actually used end to end
    vals = {}
    for (x, y, z) in cells:
        iy, iz, ix = y - oy, z - oz, x - ox
        if n6[iy, iz, ix] >= 6:
            continue                                     # buried
        lit = sky[iy, iz, ix] / CAP
        open_ = 1.0 - n26[iy, iz, ix] / 26.0
        # SKY dominates. On a smooth body the 26-neighbour term varies block to block and reads as
        # speckle, not as form; weighting it heavily gave the elephant a mottled coat that looked
        # like noise. It is worth keeping only as a small hint for genuine creases.
        vals[(x, y, z)] = 0.86 * lit + 0.14 * open_
    if not vals:
        return {c: mid for c in cells}
    lo, hi = min(vals.values()), max(vals.values())
    span = max(1e-6, hi - lo)
    for c in cells:
        if c not in vals:
            out[c] = mid
            continue
        v = (vals[c] - lo) / span
        v += jitter * (hash01(c[0], c[1], c[2], 131, seed) - 0.5)
        v = 0.5 + (v - 0.5) * strength
        out[c] = ramp[max(0, min(top, int(round(v * top))))]
    return out


def blotches(cells, patch, ground, *, scale: float = 5.0, rate: float = 0.5, seed: int = 0) -> dict:
    """Soft value-noise blobs. Right for a cow or a fox; wrong for a giraffe."""
    sc = max(1.0, scale)
    out = {}
    for (x, y, z) in cells:
        n = sum(hash01(int(x // sc) + a, int(y // sc) + b, int(z // sc) + c, 7, seed)
                for a in (0, 1) for b in (0, 1) for c in (0, 1)) / 8.0
        out[(x, y, z)] = patch if n > rate else ground
    return out
