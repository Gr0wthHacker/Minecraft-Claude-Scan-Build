"""Post-downscale polish: despeckle, designed-region repaint, mirroring.

Downscaling turns deliberate patterns (a dotted chest panel, a floral
crown, a 2x2 eye) into noise. No filter recovers a pattern -- so the
approach is: remove the noise (despeckle), then REPAINT the design
explicitly at target scale with `paint_front()` and friends, using
coordinates you read off `render.ascii_map`.
"""
from __future__ import annotations

import numpy as np

from .. import morph
from ..schem import Model

N26 = [(dy, dz, dx) for dy in (-1, 0, 1) for dz in (-1, 0, 1) for dx in (-1, 0, 1)
       if (dy, dz, dx) != (0, 0, 0)]


def front_depth(m: Model) -> np.ndarray:
    """z index of the frontmost (+z) solid cell per (y, x); -1 if none."""
    s = m.solid()
    zi = np.where(s, np.arange(s.shape[1])[None, :, None], -1)
    return zi.max(axis=1)


def despeckle(m: Model, *, protected: set[str] = frozenset(), max_size: int = 2,
              passes: int = 2, ground: bool = True) -> int:
    """Absorb same-material surface clusters of <= max_size cells into the
    dominant surrounding material. `protected` names are never changed and
    never chosen as replacements. Returns cells changed."""
    protected = {p if ":" in p else "minecraft:" + p for p in protected}
    names = m.names
    total = 0
    for _ in range(passes):
        s = m.solid()
        ext = morph.flood_outside(s, pad=True, ground=ground)
        surf = morph.surface(s, ext)
        ids = m.ids
        cells = list(zip(*np.where(surf)))
        cellset = set(cells)
        seen: set = set()
        changed = 0
        for c0 in cells:
            if c0 in seen:
                continue
            mat = ids[c0]
            if names[mat] in protected:
                seen.add(c0)
                continue
            stack, comp = [c0], []
            seen.add(c0)
            while stack:
                p = stack.pop()
                comp.append(p)
                for dy, dz, dx in N26:
                    q = (p[0] + dy, p[1] + dz, p[2] + dx)
                    if q in cellset and q not in seen and ids[q] == mat:
                        seen.add(q)
                        stack.append(q)
            if len(comp) > max_size:
                continue
            votes: dict[int, int] = {}
            for p in comp:
                for dy, dz, dx in N26:
                    q = (p[0] + dy, p[1] + dz, p[2] + dx)
                    if q in cellset and ids[q] != mat and names[ids[q]] not in protected:
                        votes[ids[q]] = votes.get(ids[q], 0) + 1
            if votes:
                win = max(votes.items(), key=lambda kv: kv[1])[0]
                for p in comp:
                    ids[p] = win
                changed += len(comp)
        total += changed
        if changed == 0:
            break
    return total


def paint_front(m: Model, cells: dict[tuple[int, int], str], *, only_if: set[str] | None = None) -> int:
    """Paint the frontmost cell at each (y, x) with the named block.
    `only_if` restricts to cells currently holding one of those names."""
    fd = front_depth(m)
    names = m.names
    n = 0
    for (y, x), blk in cells.items():
        if not (0 <= y < m.ids.shape[0] and 0 <= x < m.ids.shape[2]):
            continue
        z = fd[y, x]
        if z < 0:
            continue
        cur = names[m.ids[y, z, x]]
        if only_if is not None and cur not in only_if:
            continue
        m.ids[y, z, x] = m.ensure_state(blk)
        n += 1
    return n


def fill_front_region(m: Model, y_range: tuple[int, int], x_range: tuple[int, int],
                      block: str, *, only_if: set[str] | None = None) -> int:
    cells = {(y, x): block for y in range(*y_range) for x in range(*x_range)}
    return paint_front(m, cells, only_if=only_if)


def mirror_front(m: Model, *, y_from: int = 0, take: str = "left") -> int:
    """Copy the front-face pattern from one half onto the other."""
    fd = front_depth(m)
    sx = m.ids.shape[2]
    n = 0
    for y in range(y_from, m.ids.shape[0]):
        for x in range(sx // 2):
            xl, xr = x, sx - 1 - x
            zl, zr = fd[y, xl], fd[y, xr]
            if zl < 0 or zr < 0:
                continue
            if take == "left":
                m.ids[y, zr, xr] = m.ids[y, zl, xl]
            else:
                m.ids[y, zl, xl] = m.ids[y, zr, xr]
            n += 1
    return n


def clean_body(m: Model, base_block: str, *, keep_front_rows: tuple[int, int] | None = None,
               keep_names: set[str] = frozenset(), ground_row_names: set[str] = frozenset()) -> int:
    """Set every surface cell that is not in a kept zone to `base_block`.
    Kept: front-face cells within keep_front_rows, any cell whose name is in
    keep_names, and y==0 cells whose name is in ground_row_names."""
    names = m.names
    s = m.solid()
    ext = morph.flood_outside(s, pad=True)
    surf = morph.surface(s, ext)
    fd = front_depth(m)
    bi = m.ensure_state(base_block)
    keep_names = {k if ":" in k else "minecraft:" + k for k in keep_names}
    ground_row_names = {k if ":" in k else "minecraft:" + k for k in ground_row_names}
    n = 0
    for (y, z, x) in zip(*np.where(surf)):
        nm = names[m.ids[y, z, x]]
        if m.ids[y, z, x] == bi or nm in keep_names:
            continue
        if y == 0 and nm in ground_row_names:
            continue
        if keep_front_rows and z == fd[y, x] and keep_front_rows[0] <= y < keep_front_rows[1]:
            continue
        m.ids[y, z, x] = bi
        n += 1
    return n
