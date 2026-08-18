"""A helical stair wound around a vertical design (the taproot).

    spiral: reads the thing it wraps and tapers with it. The taproot is a cone - radius 1.4 near its
            tip, 5.8 at its head - so a constant-radius helix would either clip the root at the top or
            hang in space at the bottom. Radius here is measured off the target per course, plus a
            clearance, so the stair hugs the root the whole way up.

Pitch: `rise_every` treads per block of rise, and an angular step of 1/r radians so consecutive
treads touch. One tread per rise is too steep - each course's rail lands exactly where the next
tread wants to go - so the default is two.

The audit will report this design as MULTIPLE COMPONENTS, and that is correct. A walkable stair
rises diagonally (you step from one tread onto the next, one along and one up), and diagonal cells
are not face-connected. Forcing 6-connectivity means stacking a tread directly over another, which
buries the step below it. Walkable wins; the component count is the wrong metric for a helix.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .interior import _settle_walls
from .vertical import Ctx, World, load_capture

SPIRAL = {
    "under": None,             # capture, for collision checks
    "around": None,            # design .litematic to wrap (its radius per course drives the taper)
    "center": None,            # world (x, z); defaults to the wrapped design's centre
    "y0": None, "y1": None,    # first and last tread
    "clearance": 2,            # treads sit this far outside the wrapped design
    "min_radius": 3.0,
    "start_angle": 0.0,
    "direction": 1,            # +1 anticlockwise, -1 clockwise
    "width": 2,                # tread depth, measured outward from the inner edge
    # NOT stairs. A stair's `shape` is recomputed by the game from its neighbours, so a schematic
    # cannot dictate it - treads next to each other silently become inner/outer corner pieces. A
    # half-slab then a full block gives a 0.5 rise per tread, which walks smoothly and has no
    # neighbour-dependent state at all.
    "step_low": "stone_brick_slab",
    "step_high": "mossy_stone_bricks",
    "inner": "mossy_stone_bricks",
    "rail": "stone_brick_wall",
    "rise_every": 2,           # treads per block of rise; 2 = slab, block, slab, block -> 0.5 a tread
    "top_landing": True,       # widen the last tread so the arrival is standable
    "lantern_every": 8,        # a lantern on the rail every N steps; 0 for none
    "seed": 0,
}

DIRS4 = (("east", 1, 0), ("west", -1, 0), ("south", 0, 1), ("north", 0, -1))


def build_spiral(cfg: dict, donors=None) -> Canvas:
    p = {**SPIRAL, **cfg}
    ctx = Ctx(p["under"]) if p.get("under") else None
    prof, (cx, cz), (ry0, ry1) = _target(p)
    prof = _smooth(prof, float(p["clearance"]), float(p["min_radius"]))
    y0 = int(p["y0"]) if p["y0"] is not None else ry0
    y1 = int(p["y1"]) if p["y1"] is not None else ry1
    if y1 <= y0:
        raise ValueError(f"spiral needs y1 > y0 (got {y0}..{y1})")

    w = World()
    theta = float(p["start_angle"])
    spin = 1 if int(p["direction"]) >= 0 else -1
    rise = max(1, int(p["rise_every"]))
    treads, cells, lanterns, turns = [], set(), 0, 0.0
    r0 = prof.get(y0) or max(float(p["min_radius"]), float(p["clearance"]))
    prev = (cx + int(round(r0 * math.cos(theta))), cz + int(round(r0 * math.sin(theta))))
    y = y0
    step = 0
    guard = 0
    while y <= y1 and guard < 4000:
        guard += 1
        r = prof.get(y) or max(float(p["min_radius"]), float(p["clearance"]))
        # Advance the angle until the rounded cell actually moves, then walk there face-adjacently.
        cur = prev
        spin_guard = 0
        while cur == prev and spin_guard < 64:
            theta += spin / max(1.0, r)
            turns += (1.0 / max(1.0, r)) / (2 * math.pi)
            cur = (cx + int(round(r * math.cos(theta))), cz + int(round(r * math.sin(theta))))
            spin_guard += 1
        low = (step % rise) == 0                        # slab, then block, then up a course
        for (px, pz), _yy, _last in _path(prev, cur, y):
            _tread(w, px, y, pz, cx, cz, r, low, p, cells)
            treads.append([px, y, pz])
        if step % rise == 0 and p["lantern_every"] and (step // rise) % int(p["lantern_every"]) == 0:
            if _lantern(w, cur[0], y, cur[1], cx, cz, r, p):
                lanterns += 1
        prev = cur
        step += 1
        if step % rise == 0:                            # only climb every `rise_every` treads: at one
            y += 1                                      # block per tread the rail of each course lands
                                                        # exactly where the next tread wants to be
    _clear_heads(w, cells, p)
    if p["top_landing"]:
        _landing(w, treads[-1], cx, cz, p)
    _settle_walls(w, ctx or _NoCtx(), p["rail"])
    hits = 0 if ctx is None else sum(1 for (x, y, z) in w.cells
                                     if ctx.name_at(x, y, z) not in ("air", "cave_air", "void_air", "vine"))
    return w.canvas({"kind": "spiral", "center": [cx, cz], "y0": y0, "y1": y1,
                     "treads": len(treads), "turns": round(turns, 2), "lanterns": lanterns,
                     "collisions": hits, "first": treads[0], "last": treads[-1]})


# ------------------------------------------------------------------ the thing being wrapped

def _target(p) -> tuple[dict, tuple[int, int], tuple[int, int]]:
    """Max radius per course of the wrapped design, plus its centre and vertical extent."""
    if not p.get("around"):
        if not p.get("center") or p["y0"] is None or p["y1"] is None:
            raise ValueError("spiral needs params.around, or an explicit center + y0 + y1")
        cx, cz = (int(v) for v in p["center"])
        return {}, (cx, cz), (int(p["y0"]), int(p["y1"]))
    import numpy as np
    m, (ox, oy, oz) = load_capture(p["around"])
    ys, zs, xs = np.where(m.ids > 0)
    if p.get("center"):
        cx, cz = (int(v) for v in p["center"])
    else:
        cx, cz = int(round(xs.mean())) + ox, int(round(zs.mean())) + oz
    prof: dict[int, float] = {}
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        Y = y + oy
        r = math.hypot(x + ox - cx, z + oz - cz)
        if r > prof.get(Y, -1.0):
            prof[Y] = r
    return prof, (cx, cz), (min(prof), max(prof))


def _smooth(prof: dict, clearance: float, min_r: float) -> dict:
    """A monotone, gently growing radius.

    The raw profile of the taproot jumps - 2.2 to 4.0 in one course - and a helix that widens that
    fast folds back over the course below it, burying treads. Take a running maximum so the stair
    never narrows, then cap how fast it may grow."""
    if not prof:
        return prof
    out, run, prev = {}, 0.0, None
    for y in sorted(prof):
        run = max(run, prof[y])
        want = max(min_r, run + clearance)
        if prev is not None:
            want = min(want, prev + 0.34)               # at most a third of a block wider per course
        out[y] = want
        prev = want
    return out


# ------------------------------------------------------------------ pieces

def _tread(w: World, x: int, y: int, z: int, cx: int, cz: int, r: float, low: bool, p: dict, treads: set):
    """One step. `low` alternates: a bottom slab (walking surface y+0.5) then a full block (y+1), so
    each tread is half a block above the last and you walk up without jumping."""
    if low:
        w.put(x, y, z, p["step_low"], type="bottom", waterlogged="false")
    else:
        w.put(x, y, z, p["step_high"])
    treads.add((x, y, z))
    ux, uz = _outward(x, z, cx, cz)
    for k in range(1, int(p["width"])):                 # widen INWARD, toward the root
        w.put(x - ux * k, y, z - uz * k, p["inner"])    # structural: never skipped, it carries the walk
    rx, rz = x + ux, z + uz                             # the cell just outside the tread
    if w.has(rx, y + 1, rz) or not _free(treads, rx, y, rz) or not _free(treads, rx, y + 1, rz):
        return
    w.put(rx, y, rz, p["inner"])                        # the rail needs something to stand on
    w.put(rx, y + 1, rz, p["rail"], up="true", north="none", south="none",
          east="none", west="none", waterlogged="false")


def _clear_heads(w: World, treads: set, p: dict):
    """Drop any rail sitting on a tread's head.

    Within one course the rail is placed before the treads that follow it, so a later tread can land
    under an earlier rail. Guarding at placement time cannot see that; sweeping afterwards can. Rails
    are decorative - the walk and the connectivity live in the treads and their fill."""
    for (x, y, z) in list(treads):
        for k in (1, 2):
            if w.name(x, y + k, z) == p["rail"]:
                del w.cells[(x, y + k, z)]


def _free(treads: set, x: int, y: int, z: int) -> bool:
    """False when this cell is directly over a tread (or two over, where a rail would sit)."""
    return (x, y - 1, z) not in treads and (x, y - 2, z) not in treads


def _landing(w: World, last, cx: int, cz: int, p: dict):
    """Widen the final tread into a small platform, so the climb ends somewhere rather than stopping."""
    x, y, z = last
    ux, uz = _outward(x, z, cx, cz)
    for a in (-1, 0, 1):
        px, pz = (x + a, z) if uz else (x, z + a)
        for k in range(0, int(p["width"])):
            if not w.has(px - ux * k, y, pz - uz * k):
                w.put(px - ux * k, y, pz - uz * k, p["inner"])


def _lantern(w: World, x: int, y: int, z: int, cx: int, cz: int, r: float, p: dict) -> bool:
    ux, uz = _outward(x, z, cx, cz)
    rx, rz = x + ux, z + uz
    if w.name(rx, y + 1, rz) != p["rail"] or w.has(rx, y + 2, rz):
        return False
    w.put(rx, y + 2, rz, "lantern", hanging="false", waterlogged="false")
    return True


def _outward(x: int, z: int, cx: int, cz: int) -> tuple[int, int]:
    """Unit step away from the axis, snapped to whichever of x/z dominates."""
    dx, dz = x - cx, z - cz
    if abs(dx) >= abs(dz):
        return (1 if dx > 0 else -1), 0
    return 0, (1 if dz > 0 else -1)


def _path(prev, cur, y):
    """Face-adjacent cells from prev to cur, ALL on the same course.

    Dropping the intermediates a course lower seemed tidier, but then the next step's fill lands on
    their heads and you cannot stand on them. Keeping the walk flat makes a two-cell move read as a
    small landing, which is what a spiral wants anyway; yields (cell, y, is_last)."""
    (x0, z0), (x1, z1) = prev, cur
    cells = []
    x, z = x0, z0
    while x != x1:
        x += 1 if x1 > x else -1
        cells.append((x, z))
    while z != z1:
        z += 1 if z1 > z else -1
        cells.append((x, z))
    if not cells:
        cells = [cur]
    return [(c, y, i == len(cells) - 1) for i, c in enumerate(cells)]


def _facing(prev, cur) -> str:
    """Stairs face the way you are travelling, so you ascend into the riser."""
    if prev is None:
        return "north"
    dx, dz = cur[0] - prev[0], cur[1] - prev[1]
    if abs(dx) >= abs(dz):
        return "east" if dx > 0 else "west"
    return "south" if dz > 0 else "north"


class _NoCtx:
    """Stand-in when no capture is given: nothing exists, so walls only see their own neighbours."""

    def name_at(self, x, y, z) -> str:
        return "air"
