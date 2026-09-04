"""BONES - the skeleton primitives, and the trench a dig lays one in.

Jack: *"do the dig site first."*

**A SKELETON IS THE ONE ANIMAL SHAPE THIS MEDIUM CANNOT GET WRONG.** CLAUDE.md's central sculpture
finding is planar and columnar against volumetric: a spread wing, a neck, a stilt leg and a splayed
limb are flat sheets and straight tapers, which voxels render natively, while a shoulder or a haunch
is compound muscle, which they render worst of anything. **A skeleton is nothing BUT sheets and
tapers** - a spine is a line of blocks, a rib is a curve one block thick, a skull is a small box
with holes in it - and `gen/wyrm.py`'s 40-block skull already proves bone reads at scale.

**AND THE PLAN IS THE MONEY VIEW, WHICH VOXELS GIVE AWAY FREE.** A dig is looked INTO. Everything
here is laid flat on a trench floor and read from above, which is the same reason the ladybird and
the turtle work: their canonical view is the one this medium is best at.

**THE FLOOR IS DARK BECAUSE THE BONE IS PALE.** `bone_block` is 225 luminance; on the diggings'
own gravel and cobble (127-128) it is a 98-point step, which reads - and on `cobbled_deepslate`
(77) it is 148, which reads from the trail above. The contrast is the whole exhibit, and this repo
has laid four separate greys on top of each other before measuring across families.

**A TRENCH IS A HOLE IN THE SPOIL, NOT A DIG.** A litematic cannot express removal, so an
excavation cut below the plane would be a dig list. It does not need to be: the diggings' own
ground stands up to eleven courses above the plane, so forcing the height field to ZERO inside a
box - the way `_shop_reserve` forces mass over a shop - leaves a real cut with real walls, benched
on its sides, at no cost and with nothing to break first.
"""
from __future__ import annotations

import math

from .canvas import hash01
from .frontier_builds import _Lot

#: Checked against `blocks.available` (1.19), `blocks.spendable` (dirt is CURRENCY here) and
#: `palette.tier` by `tests/test_fossils.py`, which asks the registry rather than this comment.
BONE = {
    "bone": "bone_block",              # L225
    "floor": "cobbled_deepslate",      # L77  - 148 under the bone, which is the exhibit
    "matrix": "dripstone_block",       # L112 - the rock the bones are still half in
    "grit": "gravel",
    "bench": "cobblestone",
    "kerb": "cobbled_deepslate_slab",
    "stake": "spruce_fence",
    "post": "spruce_log",
    "beam": "stripped_spruce_log",
    "plank": "spruce_planks",
    "slab": "spruce_slab",
    "canvas_a": "white_wool",          # the shelter, and the plaster jackets
    "canvas_b": "red_wool",
    "crate": "barrel",
    "lamp": "lantern",
    "glow": "ochre_froglight",
    "sign": "spruce_wall_sign",
}


# --------------------------------------------------------------------------- the trench


def reserve(h, spec: dict) -> None:
    """Force the height field FLAT inside the trench and its benches, before anything is filled.

    **ORDER IS THE WHOLE THING, AND THIS FILE'S NEIGHBOUR RECORDS WHY.** `diggings._shop_reserve`
    had its call in the wrong place once and the cover over a shop was never placed at all; the
    ridge's first tunnel was an open cutting for the same reason. A trench cut into whatever the
    bank happened to give at that column is a dent; a trench the ground was built around is a cut.
    """
    v0, u0 = int(spec["v"]), int(spec["u"])
    w, d = int(spec.get("w", 30)), int(spec.get("d", 16))
    bench = int(spec.get("bench", 3))
    dv, du = h.shape
    for v in range(v0 - bench, v0 + w + bench):
        for u in range(u0 - bench, u0 + d + bench):
            if not (0 <= v < dv and 0 <= u < du):
                continue
            inside = v0 <= v < v0 + w and u0 <= u < u0 + d
            if inside:
                h[v, u] = 0.0
                continue
            # the benches: one step per course out, so the sides are walkable rather than a wall
            out = max(v0 - v, v - (v0 + w - 1), u0 - u, u - (u0 + d - 1), 0)
            h[v, u] = min(h[v, u], max(0.0, (out - 0.5) * 1.6))


def floor(lot: _Lot, spec: dict, seed: int) -> dict:
    """The trench floor and its benched sides."""
    v0, u0 = int(spec["v"]), int(spec["u"])
    w, d = int(spec.get("w", 30)), int(spec.get("d", 16))
    n = 0
    for v in range(v0, v0 + w):
        for u in range(u0, u0 + d):
            if lot.has(v, 0, u):
                continue
            r = hash01(v // 2, u // 2, seed + 3)
            key = "floor" if r < 0.55 else ("matrix" if r < 0.82 else "grit")
            n += 1 if lot.put(v, 0, u, BONE[key]) else 0
    # a kerb round the lip, so the cut has an edge rather than fraying into the spoil
    kerb = 0
    for v in range(v0 - 1, v0 + w + 1):
        for u in (u0 - 1, u0 + d):
            if not lot.has(v, 1, u):
                kerb += 1 if lot.slab(v, 1, u, BONE["kerb"], "bottom") else 0
    for u in range(u0, u0 + d):
        for v in (v0 - 1, v0 + w):
            if not lot.has(v, 1, u):
                kerb += 1 if lot.slab(v, 1, u, BONE["kerb"], "bottom") else 0
    return {"cells": n, "kerb": kerb, "box": [v0, u0, w, d]}


# --------------------------------------------------------------------------- the skeleton


#: The trench a skeleton is being laid in, as (v0, u0, w, d) - set by `skeleton` for the duration
#: of one build. **THE BOUND IS CHECKED IN `_bone` AND NOWHERE ELSE**, which is `_Lot.put`'s own
#: discipline: a generator that checks its own arithmetic at each call site gets it right in five
#: places and wrong in the sixth. Guarded per feature, the loose limbs were confined and the RIBS
#: were not - 45 cells of rib reaching over the trench lip, and a femur in the guest walk before
#: that. One check, one place.
_BOUNDS = None


def _inside(v, u) -> bool:
    if _BOUNDS is None:
        return True
    v0, u0, w, d = _BOUNDS
    return v0 <= v < v0 + w and u0 <= u < u0 + d


def _bone(lot: _Lot, v, u, y=1, key="bone") -> int:
    v, u = int(round(v)), int(round(u))
    if not _inside(v, u):
        return 0
    return 1 if lot.put(v, int(y), u, BONE[key]) else 0


def _line(lot: _Lot, a, b, y=1, key="bone") -> int:
    """A bone as a line of cells. **STEPPED FINE ENOUGH TO BE 6-CONNECTED** - a curve sampled
    coarsely is a row of diagonal neighbours, which is not connected, and two of this island's
    animals shed a feature that way before the rule was written down."""
    d = math.dist(a, b)
    n = max(1, int(d * 2))
    out = 0
    for i in range(n + 1):
        t = i / n
        out += _bone(lot, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, y, key)
    return out


def spine(lot: _Lot, spec: dict) -> dict:
    """The backbone, laid along the trench and CURVED - a skeleton in situ is never straight.

    Each vertebra is a centrum with a neural spine standing off it, so from above the line reads as
    a segmented backbone rather than as a stripe. That segmentation is the only thing separating a
    spine from a painted line at plan scale.
    """
    v0, u0 = float(spec["v"]), float(spec["u"])
    length = int(spec.get("length", 30))
    bow = float(spec.get("bow", 3.0))
    n = verts = 0
    pts = []
    for i in range(length + 1):
        t = i / length
        v = v0 + t * length
        u = u0 + bow * math.sin(math.pi * t)
        pts.append((v, u))
        n += _bone(lot, v, u)
        if i % 2 == 0:                       # the neural spine, one cell off the centrum
            side = 1 if (i // 2) % 2 == 0 else -1
            n += _bone(lot, v, u + side)
            verts += 1
    return {"cells": n, "vertebrae": verts, "path": pts}


def ribs(lot: _Lot, path, spec: dict) -> dict:
    """Ribs fanning from the spine, each one a curve a single block thick.

    **A RIB CAGE IS THE MOST LEGIBLE THING IN A SKELETON AND IT IS PURE SHEET.** Seen from the
    trail above, the fan is what says BONES rather than debris.
    """
    a, b = int(spec.get("from", 6)), int(spec.get("to", 20))
    span = float(spec.get("span", 6.0))
    every = max(1, int(spec.get("every", 2)))
    n = pairs = 0
    for i in range(a, min(b, len(path) - 1), every):
        v, u = path[i]
        t = (i - a) / max(1, b - a)
        reach = span * (0.45 + 0.55 * math.sin(math.pi * min(1.0, t)))
        for side in (1, -1):
            # a rib CURVES away and then back in, which is what stops it reading as a comb
            steps = max(3, int(reach * 2))
            for k in range(1, steps + 1):
                f = k / steps
                du = side * reach * f
                dv = 2.2 * math.sin(math.pi * f * 0.8)
                n += _bone(lot, v + dv, u + du)
        pairs += 1
    return {"cells": n, "pairs": pairs}


def skull(lot: _Lot, v0, u0, facing_v=1) -> dict:
    """A small elongated skull with two orbits - the one part a stranger looks for.

    **THE ORBITS ARE HOLES, AND A HOLE IS WHY IT READS AS A SKULL.** Filled in, a skull at this
    size is a lozenge; the two gaps are what a stranger's eye finds, which is the same reason the
    void tower is regularity and OPENINGS rather than damage.
    """
    n = 0
    for k in range(0, 7):
        wide = 2 if 1 <= k <= 4 else 1
        for du in range(-wide, wide + 1):
            if k in (2, 3) and abs(du) == wide:      # the orbits
                continue
            n += _bone(lot, v0 + facing_v * k, u0 + du)
    # the jaw, offset, as though it has dropped away from the cranium
    for k in range(1, 6):
        n += _bone(lot, v0 + facing_v * k, u0 + 3)
    return {"cells": n, "at": [v0, u0]}


def limb(lot: _Lot, v0, u0, length=7, angle=0.6) -> int:
    """One long bone, loose in the matrix: a shaft with a head at each end."""
    v1 = v0 + length * math.cos(angle)
    u1 = u0 + length * math.sin(angle)
    n = _line(lot, (v0, u0), (v1, u1))
    for (a, b) in ((v0, u0), (v1, u1)):
        for dv, du in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            n += _bone(lot, a + dv * 0.8, b + du * 0.8)
    return n


def skeleton(lot: _Lot, spec: dict, seed: int) -> dict:
    """A sauropod lying on its side, half out of the matrix - spine, ribs, skull, tail, loose limbs.

    It is the SAME ANIMAL standing on the rim two hundred blocks away, which is the point: the dig
    is where it came from.
    """
    global _BOUNDS
    box = spec.get("bounds")
    _BOUNDS = tuple(int(x) for x in box) if box else None
    try:
        return _skeleton(lot, spec, seed)
    finally:
        _BOUNDS = None


def _skeleton(lot: _Lot, spec: dict, seed: int) -> dict:
    out = {}
    sp = spine(lot, spec)
    out["spine"] = {k: v for k, v in sp.items() if k != "path"}
    path = sp["path"]
    out["ribs"] = ribs(lot, path, spec.get("ribs") or {})
    # **A RIB CAGE HANGS BETWEEN TWO GIRDLES**, and without them it is a fan of loose curves. The
    # pelvis and the shoulder are two short heavy arcs across the spine, and they are what make the
    # plan read as one animal rather than as a scatter of bones.
    # **THE GIRDLES SCALE WITH THE RIBS**, because both are bounded by the same trench: written as
    # absolutes 4.0 and 5.0 they reached past a twelve-deep cut and the bound clipped them to
    # thirteen cells - half a pelvis, which reads as neither a girdle nor a rib.
    rib_spec = spec.get("ribs") or {}
    rspan = float(rib_spec.get("span", 6.0))
    girdles = 0
    for idx, spread in ((int(rib_spec.get("from", 5)), rspan * 0.72),
                        (int(rib_spec.get("to", 20)), rspan * 0.88)):
        if 0 <= idx < len(path):
            gv, gu = path[idx]
            for side in (1, -1):
                girdles += _line(lot, (gv, gu), (gv + side * 1.5, gu + side * spread))
    out["girdles"] = girdles
    hv, hu = path[-1]
    out["skull"] = skull(lot, hv + 2, hu, facing_v=1)
    out["neck"] = _line(lot, path[-1], (hv + 2, hu))
    # Loose bones, scattered where a dig would still be working.
    #
    # **AND NOTHING MAY LEAVE THE TRENCH.** The offsets are hand-written against the skeleton, and
    # the skeleton sits in the middle of a cut - so a limb thrown nine cells sideways lands on the
    # bench, or, measured, in the TRAIL: `bone_block at (16,1,21)`, a femur in the one walk the
    # whole block exists to carry. It is the fourth time this land has needed the rule that a way
    # is stated and refused rather than remembered, so the trench states its own bounds and every
    # bone is checked against them.
    loose = 0
    for dv, du, ln, ang in (spec.get("loose") or
                            ((-4, 8, 7, 0.5), (10, -7, 8, 2.2), (22, 9, 6, 1.1))):
        loose += limb(lot, float(spec["v"]) + dv, float(spec["u"]) + du, ln, ang)
    out["loose"] = loose
    return out


# --------------------------------------------------------------------------- the dig around it


def _surface(lot: _Lot, v, u, cap=24):
    """The top of whatever is standing in this column, or None.

    **A STAKE STANDS ON THE BENCH, NOT ON THE TRENCH FLOOR**, and the first build asked for a cell
    with the floor under it and nothing on top - which is true nowhere on a benched lip, because
    the bench IS something on top. Every stake, crate and light was silently refused: `stakes: 0`
    in a design whose whole subject is a gridded excavation. Find the surface; never assume it.
    """
    for y in range(cap, -1, -1):
        if lot.has(v, y, u):
            return y
    return None


def furniture(lot: _Lot, spec: dict, seed: int) -> dict:
    """What makes a trench read as a DIG rather than a hole with bones in it.

    Corner stakes with a grid line between them, a canvas shelter over the skull, crates, jacketed
    finds, and a light. **THE STAKES ARE THE GRID**, which is the one thing every photograph of a
    real excavation has in it.
    """
    v0, u0 = int(spec["v"]), int(spec["u"])
    w, d = int(spec.get("w", 30)), int(spec.get("d", 16))
    out = {"stakes": 0, "jackets": 0, "crates": 0, "lights": 0}
    # the grid: a stake every fourth cell round the lip, standing on the bench's own surface
    for v in range(v0 - 1, v0 + w + 1, 4):
        for u in (u0 - 1, u0 + d):
            top = _surface(lot, v, u)
            if top is None:
                continue
            for y in (top + 1, top + 2):
                out["stakes"] += 1 if lot.fence(v, y, u, "v", BONE["stake"]) else 0
    for u in range(u0 - 1, u0 + d + 1, 4):
        for v in (v0 - 1, v0 + w):
            top = _surface(lot, v, u)
            if top is None:
                continue
            for y in (top + 1, top + 2):
                out["stakes"] += 1 if lot.fence(v, y, u, "u", BONE["stake"]) else 0
    # plaster jackets - finds already wrapped, waiting to be lifted
    for k in range(4):
        v = v0 + 3 + int(hash01(k, 1, seed + 11) * (w - 6))
        u = u0 + 1 + int(hash01(k, 2, seed + 12) * (d - 2))
        if lot.has(v, 1, u):
            continue
        out["jackets"] += 1 if lot.put(v, 1, u, BONE["canvas_a"]) else 0
    # crates and lights on the bench, out of the cut, on whatever the bench's surface is
    for k in range(4):
        v = v0 + 2 + k * max(3, w // 5)
        for u in (u0 - 2, u0 + d + 1):
            top = _surface(lot, v, u)
            if top is None:
                continue
            if lot.put(v, top + 1, u, BONE["crate"], facing="up", open="false"):
                out["crates"] += 1
            break
    for v in (v0 + 2, v0 + w // 2, v0 + w - 3):
        for u in (u0 - 1, u0 + d):
            top = _surface(lot, v, u)
            if top is None:
                continue
            out["lights"] += 1 if lot.put(v, top + 1, u, BONE["glow"]) else 0
    return out


def shelter(lot: _Lot, v0, u0, w, d, h=4) -> dict:
    """A canvas over the best find: four posts, a beam frame and a striped awning.

    **IT IS THE ONE THING IN THE TRENCH WITH COLOUR IN IT**, which is what makes a plan view of a
    dig read as a place somebody works rather than as an outline. Red and white are the land's own
    show tones, so it belongs to the park rather than to this design.
    """
    n = 0
    for v in (v0, v0 + w - 1):
        for u in (u0, u0 + d - 1):
            for y in range(1, h):
                n += 1 if lot.log(v, y, u, BONE["post"], axis="y") else 0
    for v in range(v0, v0 + w):
        for u in (u0, u0 + d - 1):
            n += 1 if lot.log(v, h, u, BONE["beam"], axis="x") else 0
    for u in range(u0, u0 + d):
        for v in (v0, v0 + w - 1):
            n += 1 if lot.log(v, h, u, BONE["beam"], axis="z") else 0
    # **STRIPES, NOT A CHECKER.** `(v + u) % 2` is a checkerboard, and a checkerboard at this size
    # reads as a picnic blanket - the one thing in the trench with colour in it looked like
    # somebody's lunch. An awning is BANDS, two cells wide, running one way.
    canvas = 0
    for v in range(v0, v0 + w):
        key = "canvas_a" if (v // 2) % 2 == 0 else "canvas_b"
        for u in range(u0, u0 + d):
            if lot.put(v, h + 1, u, BONE[key]):
                canvas += 1
    return {"cells": n + canvas, "canvas": canvas, "box": [v0, u0, w, d]}
