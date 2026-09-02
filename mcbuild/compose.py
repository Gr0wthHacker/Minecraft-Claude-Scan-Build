"""Compose several generator canvases into one design.

A WorldSpec lot is a *place*, not a single generator call. A Frontier gate is an arch plus the
two buildings that frame it plus its apron; a prospecting porch is two distinct games plus the
counter between them. Modelled as one generator each, those lots ship as thin prototypes - which
is exactly the failure PARK_VISUAL_AND_BUDGET_SPEC.md opens by naming.

Two rules the merge does NOT get to be casual about:

* **Block STATE is carried, never re-derived.** A stair's `facing`, a sign's `facing`, a rail's
  `shape` are decisions, and this renderer draws a wrong facing identically to a right one. The
  merge copies the source palette Tag itself and lets `Registry._add` dedupe by state key.
* **A contested cell is reported, not silently resolved.** First writer wins - the same
  precedence `layers.slice_plan` applies - and the count comes back in the meta so a lot whose
  parts are fighting says so instead of looking finished.

Sign TEXT follows its sign block. A tile entity with no block is a corrupt region, not a lost
line, so text is only carried across when the block that carries it actually survived the merge.
"""
from __future__ import annotations

from .gen.canvas import Canvas


def _bounds(parts):
    xs0 = min(off[0] for _c, off in parts); ys0 = min(off[1] for _c, off in parts)
    zs0 = min(off[2] for _c, off in parts)
    xs1 = max(off[0] + c.sx for c, off in parts); ys1 = max(off[1] + c.sy for c, off in parts)
    zs1 = max(off[2] + c.sz for c, off in parts)
    return (xs0, ys0, zs0), (xs1 - xs0, ys1 - ys0, zs1 - zs0)


def merge(parts, *, meta: dict | None = None) -> Canvas:
    """Merge ``[(canvas, (dx, dy, dz)), ...]`` into one canvas. First writer wins.

    Offsets are in composite-local space and may be negative; the result is shifted so its own
    minimum corner is the origin, exactly as a generator's own canvas is.
    """
    parts = [(c, tuple(int(v) for v in off)) for c, off in parts]
    if not parts:
        raise ValueError("compose.merge needs at least one part")
    (ox, oy, oz), (sx, sy, sz) = _bounds(parts)
    out = Canvas(sx, sy, sz)
    # ownership, not merely "is this cell written": a losing part's sign text would otherwise
    # overwrite the winning part's on a contested cell, leaving the right block under the wrong
    # words - which no render and no block count in this repo would ever show.
    owner: dict[tuple[int, int, int], int] = {}
    contested = 0
    for index, (canvas, (dx, dy, dz)) in enumerate(parts):
        shift = (dx - ox, dy - oy, dz - oz)
        remap: dict[int, int] = {}
        ys, zs, xs = canvas.ids.nonzero()
        for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
            pos = (x + shift[0], y + shift[1], z + shift[2])
            if pos in owner:
                contested += 1
                continue
            src = int(canvas.ids[y, z, x])
            blk = remap.get(src)
            if blk is None:
                blk = remap[src] = out.reg._add(canvas.reg.palette[src])
            out.put(pos[0], pos[1], pos[2], blk)
            owner[pos] = index
        for (tx, ty, tz), tile in canvas.tiles.items():
            pos = (tx + shift[0], ty + shift[1], tz + shift[2])
            # text follows its own block: a tile whose sign lost the cell is dropped, and a
            # tile may never be attached to a block another part placed.
            if owner.get(pos) == index and out.solid(*pos):
                out.tiles[pos] = dict(tile)
    out.meta = {**(meta or {}), "parts": len(parts), "contested_cells": contested}
    return out


def build(cfg: dict, donors=None) -> Canvas:
    """Generator entry point: ``gen: compose`` with ``params.parts``.

    Each part is ``{gen, params, offset: [x, y, z]}``. Parts are built in declaration order and
    that order IS the precedence, so declare the ground first and the buildings that stand on it
    after - the same way ``layers.slice_plan`` resolves a contested cell.
    """
    from .gen import GENERATORS
    spec = cfg.get("parts")
    if not isinstance(spec, list) or not spec:
        raise ValueError("compose needs params.parts = [{gen, params, offset}, ...]")
    built = []
    for index, part in enumerate(spec):
        name = part.get("gen")
        if name not in GENERATORS:
            raise ValueError(f"compose part {index}: unknown generator {name!r}")
        offset = part.get("offset", [0, 0, 0])
        if not isinstance(offset, (list, tuple)) or len(offset) != 3:
            raise ValueError(f"compose part {index} ({name}): offset must be [x, y, z]")
        built.append((GENERATORS[name].build(part.get("params", {}) or {}, donors), offset))
    return merge(built, meta={"kind": "compose",
                              "part_generators": [p.get("gen") for p in spec]})


DEFAULTS = {"parts": None}
