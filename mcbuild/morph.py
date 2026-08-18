"""3-D boolean morphology on numpy arrays indexed [y, z, x].

Hand-rolled (no scipy dependency). Every function takes and returns bool
arrays. `flood_outside` is the workhorse: it decides what counts as
"outside", and every hollowing / shell / sealing decision hangs off it, so
its options matter:

  pad     - add a 1-cell air margin before flooding. ALWAYS use this when the
            model is cropped flush to its bounding box, otherwise cells on
            the boundary have no "outside" neighbour and get misclassified.
  ground  - treat the plane below y=0 as solid (the model sits on ground),
            so air under overhangs is still exterior but the floor is not.
  ceiling - treat the plane above the top as solid (something sits on top,
            e.g. an island above an underside kit).
"""
from __future__ import annotations

import numpy as np

NEIGH6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]


def shift(a: np.ndarray, dy: int, dz: int, dx: int, fill=False) -> np.ndarray:
    out = np.full_like(a, fill)
    ys = slice(max(dy, 0), a.shape[0] + min(dy, 0))
    zs = slice(max(dz, 0), a.shape[1] + min(dz, 0))
    xs = slice(max(dx, 0), a.shape[2] + min(dx, 0))
    yd = slice(max(-dy, 0), a.shape[0] + min(-dy, 0))
    zd = slice(max(-dz, 0), a.shape[1] + min(-dz, 0))
    xd = slice(max(-dx, 0), a.shape[2] + min(-dx, 0))
    out[ys, zs, xs] = a[yd, zd, xd]
    return out


def _offsets(r: int, conn: int):
    rng = range(-r, r + 1)
    for dy in rng:
        for dz in rng:
            for dx in rng:
                if dy == dz == dx == 0:
                    continue
                if conn == 6 and abs(dy) + abs(dz) + abs(dx) > r:
                    continue
                yield dy, dz, dx


def dilate(a: np.ndarray, r: int = 1, conn: int = 26) -> np.ndarray:
    out = a.copy()
    for d in _offsets(r, conn):
        out |= shift(a, *d, fill=False)
    return out


def erode(a: np.ndarray, r: int = 1, conn: int = 26) -> np.ndarray:
    out = a.copy()
    for d in _offsets(r, conn):
        out &= shift(a, *d, fill=True)
    return out


def close(a, r=1, conn=26):
    return erode(dilate(a, r, conn), r, conn)


def open_(a, r=1, conn=26):
    return dilate(erode(a, r, conn), r, conn)


def neighbor_count(a: np.ndarray, conn: int = 6) -> np.ndarray:
    out = np.zeros(a.shape, dtype=np.int8)
    offs = NEIGH6 if conn == 6 else list(_offsets(1, 26))
    for d in offs:
        out += shift(a, *d, fill=False).astype(np.int8)
    return out


def flood_outside(blocked: np.ndarray, *, pad: bool = True,
                  ground: bool = False, ceiling: bool = False) -> np.ndarray:
    """Cells reachable from outside without entering `blocked` (6-conn).

    Returns a bool array the same shape as `blocked` (padding is stripped).
    """
    b = np.pad(blocked, 1, constant_values=False) if pad else blocked.copy()
    if ground:
        b[0, :, :] = True
    if ceiling:
        b[-1, :, :] = True
    reach = np.zeros_like(b)
    reach[0, :, :] = reach[-1, :, :] = True
    reach[:, 0, :] = reach[:, -1, :] = True
    reach[:, :, 0] = reach[:, :, -1] = True
    reach &= ~b
    free = ~b
    while True:
        grown = reach.copy()
        for d in NEIGH6:
            grown |= shift(reach, *d, fill=False)
        grown &= free
        if grown.sum() == reach.sum():
            break
        reach = grown
    return reach[1:-1, 1:-1, 1:-1] if pad else reach


def surface(solid: np.ndarray, exterior: np.ndarray) -> np.ndarray:
    """Solid cells with at least one 6-neighbour that is exterior air."""
    return solid & dilate(exterior, 1, conn=6)


def components(mask: np.ndarray, conn: int = 6) -> tuple[np.ndarray, list[int]]:
    """Label connected components. Returns (labels, sizes) with labels 1-based."""
    labels = np.zeros(mask.shape, np.int32)
    sizes: list[int] = []
    seen = np.zeros(mask.shape, bool)
    offs = NEIGH6 if conn == 6 else list(_offsets(1, 26))
    cur = 0
    for start in map(tuple, np.argwhere(mask)):
        if seen[start]:
            continue
        cur += 1
        stack = [start]
        seen[start] = True
        n = 0
        while stack:
            y, z, x = stack.pop()
            labels[y, z, x] = cur
            n += 1
            for dy, dz, dx in offs:
                p = (y + dy, z + dz, x + dx)
                if (0 <= p[0] < mask.shape[0] and 0 <= p[1] < mask.shape[1]
                        and 0 <= p[2] < mask.shape[2] and mask[p] and not seen[p]):
                    seen[p] = True
                    stack.append(p)
        sizes.append(n)
    return labels, sizes


def drop_small_components(mask: np.ndarray, min_size: int, conn: int = 6) -> np.ndarray:
    labels, sizes = components(mask, conn)
    keep = np.array([False] + [s >= min_size for s in sizes], bool)
    return keep[labels]
