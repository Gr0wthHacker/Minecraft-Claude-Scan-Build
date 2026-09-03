"""THE MINE RIDGE: the mountain the Mine Coaster is cut into, and the adit through its foot.

Jack: *"frontier in its current design is useless outside of the rollercoaster, lets think about
this area differently and figure out what we can build that supports the coaster."*

Measured before anything was drawn, over `out/Park Complete.litematic`:

    the Frontier is 200 x 170 = 34,000 columns and 66% of it is bare lawn
    its whole interactive inventory is 646 rails, 2 buttons, 2 bells and 2 detector rails
    3.8% of it stands over 20 courses; exactly two things break 25
    the Mine Coaster tops out 42 courses over the plane

and the review sheet says the rest: **the coaster's PLAN IS A RECTANGLE** - a timber trestle
perimeter round a terraced grey mass with vertical faces - and its silhouette is unnameable. It
does not read as a mine in a mountain because there is no mountain; it reads as a quarry heap
standing on a lawn, in `cracked_stone_bricks`, which is a BRICK.

**THIS DESIGN NEVER TOUCHES THE RIDE.** It reads the coaster's own artifact, and a cell the ride
occupies is one this generator refuses - so the two compose rather than contend, and `overlap 0`
is a property of the construction. What it adds is the three things a mass needs to read as rock:

  TALUS      a battered apron round the ride's whole outline, thick at the foot and thinning
             upward, so a vertical brick wall becomes a slope. The reach and the height of the
             apron are both functions of the FACE it stands under - a taller face throws a
             longer scree - which is what stops it reading as a uniform skirt.
  A CREST    a peak SOUTH of the ride, where the coaster's own mass is lowest (its last ten
             courses read 0-15 against 42 at the lift hill). It stands BEHIND the ride from the
             guest's approach, which is the classic composition and the reason it does not
             have to be squeezed in beside anything: the mountain is the backdrop, the ride is
             cut into its near face.
  THE ADIT   a walk-through gallery bored into the foot of the cut face - timber sets, rail,
             an ore chamber and a winze - because a mine you can only look at is scenery.

**THE MATERIAL IS THE POINT AS MUCH AS THE SHAPE.** The ride is 10,657 cells of
`cracked_stone_bricks`: dressed masonry, which is why the mass reads as rubble rather than as
geology. Everything here is what that brick would have been QUARRIED FROM - stone, andesite,
cobble, cobbled deepslate at depth, gravel scree, moss at the wet foot, and coal and gold in the
faces - so the brick reads as the worked part of a rock that is still standing around it.

**THE CREST IS TERRACED ONLY WHERE IT IS STEEP.** A slope gentle enough to walk is left smooth;
a face too steep to stand on is snapped to benches, which is both what a worked-out mountain
looks like and the one thing that stops a 50-course fall reading as a wall. `_terrace` is that
rule and nothing else in this file quantises a height.

**NOISE GOES ON THE HEIGHT FIELD AT A COARSE GRAIN, NEVER PER CELL.** Per cell it is confetti -
the Lowland Thicket shipped that once and came out as 191 blobs of which 75% were one or two
cells. Here the perturbation is bilinear over a 7-cell lattice, so the boundary wobbles and the
interior stays solid.

**GRAVEL IS A FALLING BLOCK** (rule 13). It is placed only on the CRUST of a column that is
solid to the ground beneath it, never as a face, never over the adit's void.
"""
from __future__ import annotations

import numpy as np

from .. import schem
from .canvas import Canvas, hash01
from .frontier_builds import _Lot

#: WHAT THE BRICK WAS QUARRIED FROM. Every entry is checked by `tests/test_mineridge.py` against
#: `blocks.available` (the 1.19 server), `blocks.spendable` (dirt and grass are CURRENCY here)
#: and `palette.tier`; nothing here is expensive.
ROCK = {
    "deep": "cobbled_deepslate",       # the foot: the rock under the rock
    "deep_b": "deepslate",
    "rock": "stone",                   # the bulk
    "rock_b": "andesite",
    "rock_c": "cobblestone",
    "rock_moss": "mossy_cobblestone",
    "scree": "gravel",                 # CRUST ONLY - it falls
    "turf": "moss_block",
    "coal": "coal_ore",
    "gold": "gold_ore",
    "tuff": "tuff",                    # L108 - a cool mid, off the stone band
    "granite": "granite",              # L112 - the ore seam's warm hue
    "drip": "dripstone_block",         # L112 - and its second tone
    "pale": "diorite",                 # L188 - the summit, and the one real highlight
    "step": "cobblestone_stairs",
    "slab": "cobblestone_slab",
    "kerb": "cobbled_deepslate_wall",
}

#: The adit's own kit - the town's timber, so the gallery reads as the same hand as the buildings.
TIMBER = {
    "post": "spruce_log",
    "beam": "stripped_spruce_log",
    "plank": "spruce_planks",
    "fence": "spruce_fence",
    "slab": "spruce_slab",
    "stair": "spruce_stairs",
    "rail": "rail",
    "lamp": "lantern",
    "sign": "spruce_wall_sign",
    "glow": "ochre_froglight",
    "barrel": "barrel",
    "bars": "iron_bars",
}

#: **THE VALUE LADDER IS MEASURED ACROSS FAMILIES, NEVER INSIDE ONE**, and this file was written
#: the wrong way round first. Measured with `blocks.color(..., "side")`:
#:
#:     stone 126 . andesite 136 . cobblestone 127 . gravel 128
#:
#: - four materials inside 10 points of luminance, which is BELOW the ~15 at which a tone stops
#: being a tone at all. A mass built out of those four is one grey whatever the mix, which is the
#: same mistake three separate notes in CLAUDE.md record about stone brick and about blackstone.
#: Across families the rungs are real: `cobbled_deepslate` 77, `moss_block` 101, `tuff` 108,
#: `granite` 112, `stone` 126, `diorite` 188.
#:
#: **SO THE MASS IS BEDDED, NOT SPECKLED.** Rock has bedding planes; a horizontal band is the one
#: thing that reads at the distance a guest actually stands, and speckling four indistinguishable
#: greys reads as noise close up and as nothing at all far off. The bands are jittered by the same
#: coarse noise the height field uses, so they are not dead level.
_DARK = (("deep", 0.52), ("deep_b", 0.22), ("rock_c", 0.26))
_MID = (("rock", 0.48), ("rock_c", 0.24), ("rock_b", 0.16), ("tuff", 0.12))
_SEAM = (("granite", 0.26), ("drip", 0.18), ("rock", 0.24), ("coal", 0.20), ("gold", 0.12))
_HIGH = (("rock", 0.52), ("rock_b", 0.26), ("rock_c", 0.22))
_PALE = (("rock", 0.44), ("pale", 0.30), ("rock_b", 0.26))
_CRUST = (("rock", 0.30), ("scree", 0.26), ("rock_c", 0.22), ("rock_b", 0.12),
          ("rock_moss", 0.10))

#: **THE BEDS REPEAT, because real bedding does and because one ladder spread over fifty courses
#: puts every accent in the bottom third where nothing can see it.** That was the second build: a
#: seam at y14-22 on a 48-course crag, invisible. Here the cycle is six courses and MID sits
#: between every accent, so a seam reads as a discrete bed rather than as a stripe in a pattern.
#: The first four courses are always dark - the rock under the rock - wherever the mass is deep.
_STRATA = (_MID, _SEAM, _MID, _HIGH, _MID, _DARK, _MID, _PALE)
_BAND = 6

RIDGE = {
    "kind": "ridge",
    "lot": None,                     # [dv, du] - the hard boundary
    "at": None,                      # [V, U] - the lot's near corner in park coordinates
    "anchor": [97500, 203, 80300],
    "ride": None,                    # the coaster's artifact - the shape this is built around
    "ride_at": [0, 0],               # its near corner INSIDE this lot
    "ride_plane": 13,                # which course of the ride's own canvas is the ground
    "spine": [],                     # [[v0, u0, v1, u1, height, width], ...] - the ridgeline
    "talus_reach": 16,               # the longest scree this ridge throws
    "bench": 4,                      # the terrace step on a face too steep to stand on
    "spoil": [],                     # [[v, u, radius], ...] - tips at the foot
    "keep_out": [],                  # [[v0, v1, u0, u1], ...] - ground that belongs to somebody
    "adit": None,                    # see `_adit`
    "seed": 0,
    "title": "MINE RIDGE",
}


# --------------------------------------------------------------------------- the height field


def _noise(dv: int, du: int, seed: int, grain: int = 7) -> np.ndarray:
    """Smooth [0,1) noise, bilinear over a `grain`-cell lattice.

    COARSE AND SMOOTH, because the alternative has already cost this project a rebuild: noise
    evaluated per cell thresholds into confetti, and the Lowland Thicket's own fix was to move
    the randomness onto the drift's RADIUS rather than its interior. Here it perturbs the height
    field, so the mountain's outline wobbles and its body stays whole.
    """
    gv, gu = dv // grain + 2, du // grain + 2
    lat = np.array([[hash01(a, b, seed) for b in range(gu)] for a in range(gv)])
    v = np.arange(dv) / grain
    u = np.arange(du) / grain
    v0, u0 = v.astype(int), u.astype(int)
    fv, fu = (v - v0)[:, None], (u - u0)[None, :]
    a = lat[np.ix_(v0, u0)]
    b = lat[np.ix_(v0 + 1, u0)]
    c = lat[np.ix_(v0, u0 + 1)]
    d = lat[np.ix_(v0 + 1, u0 + 1)]
    return (a * (1 - fv) * (1 - fu) + b * fv * (1 - fu) + c * (1 - fv) * fu + d * fv * fu)


def _talus(face: np.ndarray, blocked: np.ndarray, reach_max: int) -> np.ndarray:
    """Scree off every face, by a max-first flood that carries each source's own slope.

    **THE APRON IS A FUNCTION OF THE FACE IT STANDS UNDER**, which is the whole difference
    between a talus and a skirt: a forty-course wall throws scree fifteen cells and a six-course
    one throws it three, so the outline of the finished mass is irregular by construction rather
    than by noise. `face` is the ride's own top height per column and 0 where there is no ride.

    A single flood, popping the highest candidate first, gives every cell the maximum over all
    sources of `h0(F) - d * slope(F)` - which is what taking a max over the neighbourhood would
    give, at a fraction of the work.
    """
    import heapq
    dv, du = face.shape
    out = np.zeros((dv, du))
    seen = np.zeros((dv, du), bool)
    heap: list = []
    for v, u in zip(*np.nonzero(face > 0)):
        f = float(face[v, u])
        # A TALL FACE IS NOT ALL TALUS. Scree climbs about half a cliff and the rest stays cut
        # rock; a skirt that reached the top would bury the ride's own trestles.
        h0 = min(max(f * 0.46, 3.0), 19.0)
        reach = min(max(f * 0.44, 4.0), float(reach_max))
        slope = h0 / reach
        for dvv, duu in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = int(v) + dvv, int(u) + duu
            if 0 <= a < dv and 0 <= b < du and not blocked[a, b]:
                heapq.heappush(heap, (-(h0 - slope), a, b, slope))
    while heap:
        neg, v, u, slope = heapq.heappop(heap)
        h = -neg
        if h <= 0.0 or seen[v, u]:
            continue
        seen[v, u] = True
        out[v, u] = h
        for dvv, duu in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = v + dvv, u + duu
            if 0 <= a < dv and 0 <= b < du and not blocked[a, b] and not seen[a, b]:
                heapq.heappush(heap, (-(h - slope), a, b, slope))
    return out


def _away(mask: np.ndarray, cap: int) -> np.ndarray:
    """Chebyshev-ish distance from `mask`, capped - iterative dilation, numpy only (no scipy).

    The ladybird's siting used the same thing for the same reason: this repo has numpy and Pillow
    and nothing else, and a capped distance is all any of it ever needs.
    """
    d = np.where(mask, 0.0, float(cap))
    cur = mask.copy()
    for k in range(1, cap):
        grown = cur.copy()
        grown[1:, :] |= cur[:-1, :]
        grown[:-1, :] |= cur[1:, :]
        grown[:, 1:] |= cur[:, :-1]
        grown[:, :-1] |= cur[:, 1:]
        d = np.where(grown & ~cur, float(k), d)
        cur = grown
    return d


def _crest(dv: int, du: int, spine) -> np.ndarray:
    """The ridgeline: distance to a SEGMENT, with a flat-topped falloff. `max`, never a sum.

    **CONES ARE THE WRONG PRIMITIVE AND THE FIRST BUILD PROVED IT.** Three point-sources with a
    `(1-d)**1.6` falloff came out as three sharp spires - a tent is what that exponent draws, and
    the terracing then wrapped each one in concentric contour rings, so the mass read as a stack
    of grey wedding cakes. A crag is a LINE with a shoulder: distance to a segment gives the line,
    and a near-linear falloff off that line gives a RIDGE. Pushed further - an exponent well below
    one - it becomes a mesa, and a terraced mesa is a ziggurat: that was the second build, a broad
    flat-topped slab with rectangular steps down its sides. A ridge with two octaves of noise on
    it is the one that reads as rock.

    `spine` entries are [v0, u0, v1, u1, height, width]; a segment of zero length is a knoll.
    """
    out = np.zeros((dv, du))
    if not spine:
        return out
    vv = np.arange(dv)[:, None].astype(float)
    uu = np.arange(du)[None, :].astype(float)
    for a in spine:
        v0, u0, v1, u1, ph, pw = (float(x) for x in a)
        dv_, du_ = v1 - v0, u1 - u0
        ln = dv_ * dv_ + du_ * du_
        if ln <= 0:
            t = np.zeros((dv, du))
        else:
            t = np.clip(((vv - v0) * dv_ + (uu - u0) * du_) / ln, 0.0, 1.0)
        d = np.sqrt((vv - (v0 + t * dv_)) ** 2 + (uu - (u0 + t * du_)) ** 2) / max(pw, 1.0)
        out = np.maximum(out, ph * np.clip(1.0 - d, 0.0, 1.0) ** 0.95)
    return out


def _terrace(h: np.ndarray, step: int, jitter: np.ndarray) -> np.ndarray:
    """Snap to benches ONLY on a face too steep to stand on, and never at the foot.

    **APPLIED EVERYWHERE THIS BUILDS A ZIGGURAT**, which the first pass shipped: a cone is
    uniformly steep, so every column snapped and the peaks came out as concentric contour rings.
    The threshold is now 1.6 courses per cell - genuinely unclimbable rather than merely sloping -
    the foot is exempt, and the bench height carries the height field's own coarse jitter so a
    shelf wanders instead of drawing a contour line.
    """
    gv = np.abs(np.gradient(h, axis=0))
    gu = np.abs(np.gradient(h, axis=1))
    steep = np.maximum(gv, gu) > 2.0
    bench = np.round((h + (jitter - 0.5) * step) / step) * step
    return np.where(steep & (h > step * 2), bench, h)


# --------------------------------------------------------------------------- the ride


def _ride_columns(p: dict, dv: int, du: int):
    """(occupied, top) in LOT coordinates and this canvas's own y.

    `occupied[v, u, y]` is a cell the coaster owns and this design must refuse; `top[v, u]` is
    how far it stands over the plane, which is what the talus is a function of. The ride's own
    canvas has `ride_plane` courses BELOW the plane - trestle footings that end up under the
    park's lawn - and they are dropped here, because a talus is a thing you can see.
    """
    occ = np.zeros((dv, du, 1), bool)
    top = np.zeros((dv, du))
    if not p.get("ride"):
        return np.zeros((dv, du, 0), bool), top
    m = schem.load(str(p["ride"]))
    sol = m.solid()                                  # [y, U, V]
    plane = int(p.get("ride_plane", 13))
    rv, ru = (int(x) for x in (p.get("ride_at") or (0, 0)))
    sy, su, sv = sol.shape
    hy = max(0, sy - plane)
    occ = np.zeros((dv, du, hy), bool)
    for y in range(plane, sy):
        layer = sol[y]                               # [U, V]
        for u, v in zip(*np.nonzero(layer)):
            a, b = int(v) + rv, int(u) + ru
            if 0 <= a < dv and 0 <= b < du:
                occ[a, b, y - plane] = True
                top[a, b] = max(top[a, b], y - plane + 1)
    return occ, top


# --------------------------------------------------------------------------- the adit


def _adit_plan(p: dict, dv: int, du: int) -> dict | None:
    """The gallery's own cells, as a PLAN, so the mass can be guaranteed over it before it is cut.

    **A TUNNEL IS A VOID WITH ROCK ON TOP, AND THE ROCK HAS TO BE PUT THERE FIRST.** Carved out
    of whatever the talus happened to give, a gallery under a thin part of the apron comes out as
    an open trench with two walls - which audits clean, renders as a gallery from the one bearing
    that looks down it, and is a slot in the hillside from every other.

    THE TWO PORTALS SHARE A FACE AND THE GALLERY IS A U, so it is a walk-THROUGH rather than a
    dead end you have to turn round in - the same rule the ruinway settled about paths: a way is
    real when both of its ends are places.
    """
    a = p.get("adit")
    if not a:
        return None
    v0, u0 = (int(x) for x in a["at"])
    ln = max(6, int(a.get("length", 22)))
    cross = max(4, int(a.get("cross", 12)))
    half = max(0, int(a.get("width", 3)) // 2)
    clear = max(3, int(a.get("height", 4)))
    step = -1 if a.get("into", "west") == "west" else 1
    far = v0 + step * (ln - 1)

    lanes = [
        {"axis": "v", "cells": [(v0 + step * i, u0) for i in range(ln)]},
        {"axis": "u", "cells": [(far, u0 + j) for j in range(cross)]},
        {"axis": "v", "cells": [(v0 + step * i, u0 + cross - 1) for i in range(ln)]},
    ]
    cells = set()
    for lane in lanes:
        across = 1 if lane["axis"] == "v" else 0          # widen ACROSS the lane's own run
        for cv, cu in lane["cells"]:
            for k in range(-half, half + 1):
                cells.add((cv, cu + k) if across else (cv + k, cu))
    chamber = a.get("chamber")
    if chamber:
        cv, cu, r = (int(x) for x in chamber)
        for dvv in range(-r, r + 1):
            for duu in range(-r, r + 1):
                if abs(dvv) + abs(duu) <= r + 1:
                    cells.add((cv + dvv, cu + duu))
    cells = {(v, u) for v, u in cells if 0 <= v < dv and 0 <= u < du}
    return {"cells": cells, "lanes": lanes, "step": step, "length": ln, "cross": cross,
            "half": half, "clear": clear, "chamber": chamber,
            "portals": [(v0, u0), (v0, u0 + cross - 1)],
            "cover": max(2, int(a.get("cover", 4)))}


def _cut_adit(lot: _Lot, plan: dict, seed: int) -> dict:
    """Hollow the gallery, floor it, timber it, rail it and light it.

    THE SET IS THE STRUCTURE AND THE STRUCTURE IS THE STORY. A bored hole in rock reads as a
    cave; two posts and a cap beam every third cell read as a MINE, and cost eleven blocks a set.

    y0 IS THE FLOOR COURSE AND y1 IS WHERE A GUEST STANDS - the same convention every building
    in this land uses, so a gallery mouth is level with the ground outside it rather than a step
    down into a pit.
    """
    clear = plan["clear"]
    out = {"sets": 0, "lamps": 0, "rail": 0}
    for v, u in plan["cells"]:                                   # 1. the void
        for y in range(1, clear + 1):
            lot.c.put(v, y, u, 0)
        lot.put(v, 0, u, ROCK["rock_c"] if hash01(v, u, seed + 3) < 0.7 else ROCK["scree"])
    for lane in plan["lanes"]:                                   # 2. sets, rail, light
        across = "u" if lane["axis"] == "v" else "v"
        beam_axis = "z" if lane["axis"] == "v" else "x"
        for i, (v, u) in enumerate(lane["cells"]):
            if i % 3 == 0:
                for s in (-1, 1):
                    a, b = (v, u + s * (plan["half"] + 1)) if across == "u" else                            (v + s * (plan["half"] + 1), u)
                    # **A SET'S POST MAY NOT STAND IN THE GALLERY.** Where the cross-cut meets the
                    # corridor its own posts land in the lane that feeds it - the same cell is a
                    # wall to one lane and a walkway to the other - so a leg placed blind bricks
                    # up the junction. Nothing in an audit, a BOM or a render can see that; the
                    # only symptom is a guest who cannot get through.
                    if (a, b) in plan["cells"]:
                        continue
                    for y in range(1, clear + 1):
                        lot.log(a, y, b, TIMBER["post"], axis="y")
                for k in range(-plan["half"] - 1, plan["half"] + 2):
                    a, b = (v, u + k) if across == "u" else (v + k, u)
                    lot.log(a, clear + 1, b, TIMBER["beam"], axis=beam_axis)
                out["sets"] += 1
            if i % 2 == 0:
                lot.put(v, 1, u, TIMBER["rail"],
                        shape="north_south" if lane["axis"] == "u" else "east_west",
                        waterlogged="false")
                out["rail"] += 1
            if i % 7 == 3 and lot.hang(v, clear, u):
                out["lamps"] += 1
    return out


def _portals(lot: _Lot, plan: dict) -> dict:
    """A framed mouth on each end of the U, and a named board over it.

    A hole in a hillside is a cave. A hole with two posts, a cap beam and a name over it is a
    MINE, and the frame is also what tells a guest the hole is a way IN rather than scenery.
    """
    clear, step, half = plan["clear"], plan["step"], plan["half"]
    made = 0
    facing = "east" if step < 0 else "west"                      # the mouth looks OUT
    for i, (pv, pu) in enumerate(plan["portals"]):
        fv = pv - step                                           # the frame, in the open air
        # **A PORTAL BURIED IN ITS OWN TALUS IS NOT A PORTAL.** The mass is filled before the
        # gallery is cut, so without this the scree stands right against the mouth: there is no
        # approach, and the name board over it is refused for having no empty cell to hang in -
        # which is how one of the two shipped unsigned while the other did not.
        for d in range(0, 3):
            for k in range(-half - 1, half + 2):
                for y in range(1, clear + 3):
                    lot.c.put(fv - step * d, y, pu + k, 0)
        for s in (-1, 1):
            for y in range(1, clear + 1):
                lot.log(fv, y, pu + s * (half + 1), TIMBER["post"], axis="y")
        for k in range(-half - 1, half + 2):
            lot.log(fv, clear + 1, pu + k, TIMBER["beam"], axis="z")
            lot.put(fv, clear + 2, pu + k, TIMBER["plank"])
        lines = (["ADIT No.1", "ore level", "mind your head"] if i == 0
                 else ["ADIT No.1", "way out", "to the workings"])
        if lot.sign(fv - step, clear + 2, pu, facing, lines):
            made += 1
        else:                                    # ...and if the lot's own edge is in the way,
            lot.sign(fv, clear + 2, pu - 1, "north" if step < 0 else "south", lines) and None
        for s in (-1, 1):                                        # a lamp each side of the mouth
            lot.put(fv, clear, pu + s * (half + 1), TIMBER["glow"])
    return {"portals": len(plan["portals"]), "portal_signs": made}


def _chamber(lot: _Lot, plan: dict, seed: int) -> dict:
    """The stope at the far end: an ore face, a winze you can look down, and a working bench.

    THE REVEAL IS PASSED, NOT STOOD IN. A guest walks THROUGH the cross-cut, so the ore face is
    on the wall opposite the lane rather than in the middle of it - the undercroft's own rule,
    learned when every chamber put its own thing in the middle of its own corridor and the lane
    had to be re-cleared afterwards.
    """
    ch = plan.get("chamber")
    if not ch:
        return {}
    cv, cu, r = (int(x) for x in ch)
    clear, step = plan["clear"], plan["step"]
    n_ore = 0
    v = cv - step * (r + 1)                                      # the back wall, past the lane
    for u in range(cu - r, cu + r + 1):
        for y in range(1, clear + 1):
            if not lot.inside(v, u):
                continue
            rr = hash01(v, y, u, seed + 71)
            key = "gold" if rr < 0.20 else ("coal" if rr < 0.52 else "rock_b")
            if lot.put(v, y, u, ROCK[key]):
                n_ore += 1
    wv, wu = cv + step, cu                                       # the winze, fenced and lit
    for dv_ in (-1, 0, 1):
        for du_ in (-1, 0, 1):
            if abs(dv_) + abs(du_) == 1:
                lot.fence(wv + dv_, 1, wu + du_, "u", key=TIMBER["fence"])
    lot.put(wv, 0, wu, TIMBER["glow"])
    lot.put(cv, 1, cu + r - 1, TIMBER["barrel"], facing="up", open="false")
    return {"ore_face": n_ore, "winze": [wv, 0, wu]}


# --------------------------------------------------------------------------- the build


def _build(lot: _Lot, p: dict) -> dict:
    dv, du = lot.dv, lot.du
    seed = int(p.get("seed", 0))
    occ, face = _ride_columns(p, dv, du)
    ride_any = occ.any(axis=2) if occ.shape[2] else np.zeros((dv, du), bool)
    # **GROUND THAT BELONGS TO SOMEBODY ELSE.** Measured off `Park Complete`: 271 columns of this
    # lot carry something that is not the ride - the coaster's own switchback queue, the Ridge
    # Water Tower and two ore-cart props, all of them `PF Front Frontier`'s, all of them in the
    # south band. A mountain deferring round a 7 x 30 queue is a mountain with a rectangular bite
    # out of it, so this keeps out rather than defers, and the boxes carry their own margin.
    for box in (p.get("keep_out") or []):
        a, b, c_, d = (int(x) for x in box)
        ride_any[max(0, a):min(dv, b + 1), max(0, c_):min(du, d + 1)] = True

    # ---- the height field -------------------------------------------------------------
    talus = _talus(face, ride_any, int(p.get("talus_reach", 16)))
    crest = _crest(dv, du, p.get("spine") or [])
    # **THE CRAG MUST NOT GROW THROUGH THE RIDE**, and refusing the ride's own cells is not
    # enough to stop it: a column one cell off the track took the crest's full height, so the
    # first build swallowed the coaster whole - the mass was there and the thing it exists to
    # support was invisible from three bearings out of four. The crest is held down near the ride
    # and reaches its full height only `stand` cells clear of it, which leaves a moat the track
    # reads against. The TALUS is deliberately not capped: hugging the ride is its entire job.
    stand = max(1, int(p.get("stand_off", 7)))
    crest *= np.clip((_away(ride_any, stand + 2) - 1.0) / stand, 0.0, 1.0)
    # TWO OCTAVES. One grain-7 octave alone perturbs a 48-course crag by whole shoulders and
    # leaves its faces glassy; the grain-3 octave is what puts crags and gullies on them. Both are
    # on the FIELD, never on the cell - per cell this is confetti, which the Thicket shipped once.
    noise = _noise(dv, du, seed)
    fine = _noise(dv, du, seed + 7, grain=3)
    h = np.maximum(talus, crest)
    h *= 0.82 + 0.30 * noise + 0.14 * (fine - 0.5)
    h = _terrace(h, int(p.get("bench", 4)), _noise(dv, du, seed + 101, grain=5))
    h[ride_any] = 0.0                                        # the ride owns its own columns

    # ---- the adit, whose cover is guaranteed BEFORE anything is filled -----------------
    plan = _adit_plan(p, dv, du)
    if plan:
        # the void is y1..clear, the cap beam sits at clear+1, and the cover is the rock over it
        need = plan["clear"] + 2 + plan["cover"]
        for v, u in plan["cells"]:
            if not ride_any[v, u]:
                h[v, u] = max(h[v, u], need)
                # ...and one cell of shoulder either side, or the gallery's own walls are the
                # outside of the hill and it is a trench rather than a tunnel.
                for a in range(max(0, v - 1), min(dv, v + 2)):
                    for b in range(max(0, u - 1), min(du, u + 2)):
                        if not ride_any[a, b]:
                            h[a, b] = max(h[a, b], need)

    keep = np.zeros((dv, du), bool)
    for box in (p.get("keep_out") or []):
        a, b, c_, d = (int(x) for x in box)
        keep[max(0, a):min(dv, b + 1), max(0, c_):min(du, d + 1)] = True

    # ---- fill ------------------------------------------------------------------------
    hi = np.floor(h + 0.5).astype(int)
    hi = np.clip(hi, 0, lot.c.sy - 1)
    placed = 0
    for v in range(dv):
        for u in range(du):
            n = int(hi[v, u])
            if n <= 0 or ride_any[v, u]:
                continue
            # THE BAND BOUNDARIES ARE JITTERED, or the strata draw a contour map round the crag
            lift = (noise[v, u] - 0.5) * 7.0
            for y in range(n):
                if y >= n - 1:
                    key = _pick(_CRUST, v, u, y, seed)
                elif n <= 6:
                    key = _pick(_MID, v, u, y, seed)       # a thin apron has no strata to show
                elif y < 3:
                    key = _pick(_DARK, v, u, y, seed)      # the rock under the rock
                else:
                    band = int((y + lift) // _BAND) % len(_STRATA)
                    key = _pick(_STRATA[band], v, u, y, seed)
                if key == "scree" and y < n - 1:
                    key = "rock"                       # gravel is a CRUST material; it falls
                if lot.put(v, y, u, ROCK[key]):
                    placed += 1
            # moss at the wet foot of a face, never on a summit
            if n and n <= 3 and hash01(v, u, seed + 9) < 0.28:
                lot.put(v, n - 1, u, ROCK["turf"])

    parts = {"talus_cells": placed, "crest": float(crest.max()) if crest.size else 0.0,
             "top": int(hi.max())}

    # ---- spoil tips, boulders, and the cut face's own steps ---------------------------
    parts["spoil"] = _spoil(lot, p.get("spoil") or [], hi, ride_any, seed)
    parts["boulders"] = _boulders(lot, hi, ride_any, seed)

    # ---- the adit --------------------------------------------------------------------
    if plan:
        parts["adit"] = _cut_adit(lot, plan, seed)
        parts["adit"].update(_portals(lot, plan))
        parts["adit"].update(_chamber(lot, plan, seed))
    return parts


def _pick(table, v, u, y, seed) -> str:
    r = hash01(v * 5 + 1, u * 11 + 7, y * 17 + 3, seed)
    acc = 0.0
    for key, share in table:
        acc += share
        if r < acc:
            return key
    return table[0][0]


def _spoil(lot: _Lot, tips, hi, ride_any, seed) -> int:
    """Gravel cones at the foot. A tip is what a mine PUTS somewhere, and it is the cheapest
    thing in the vocabulary that says the mountain is being worked rather than merely standing."""
    n = 0
    for tv, tu, tr in tips:
        tv, tu, tr = int(tv), int(tu), int(tr)
        for v in range(tv - tr, tv + tr + 1):
            for u in range(tu - tr, tu + tr + 1):
                if not lot.inside(v, u) or ride_any[v, u]:
                    continue
                d = ((v - tv) ** 2 + (u - tu) ** 2) ** 0.5
                if d > tr:
                    continue
                top = int(round(tr * 0.85 * (1 - d / tr) ** 0.9))
                base = int(hi[v, u])
                for y in range(base, base + top):
                    key = "scree" if y >= base + top - 2 else "rock_c"
                    if lot.put(v, y, u, ROCK[key]):
                        n += 1
    return n


def _boulders(lot: _Lot, hi, ride_any, seed) -> int:
    """Lumps ON the surface. A talus computed from a height field is a smooth ramp, and a smooth
    ramp at this scale reads as a poured embankment; boulders are what make it rock."""
    dv, du = hi.shape
    n = 0
    for v in range(2, dv - 2, 3):
        for u in range(2, du - 2, 3):
            if ride_any[v, u] or hi[v, u] < 2:
                continue
            if hash01(v, u, seed + 31) > 0.055:
                continue
            r = 1 + int(hash01(v, u, seed + 32) * 2)
            base = int(hi[v, u])
            for a in range(v - r, v + r + 1):
                for b in range(u - r, u + r + 1):
                    if not lot.inside(a, b) or ride_any[a, b]:
                        continue
                    d = ((a - v) ** 2 + (b - u) ** 2) ** 0.5
                    if d > r:
                        continue
                    for y in range(base, base + max(1, r)):
                        if lot.put(a, y, b, ROCK["rock_c" if (a + b) % 3 else "rock_b"]):
                            n += 1
    return n


# --------------------------------------------------------------------------- entry point


def build(cfg: dict, donors=None) -> Canvas:
    p = {**RIDGE, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("a mine ridge needs its measured lot: lot: [dv, du]")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    sy = int(p.get("sy") or 64)
    c = Canvas(dv, sy, du, donors)
    lot = _Lot(c, dv, du, seed=int(p.get("seed", 0)))
    parts = _build(lot, p)

    av, ay, au = (int(v) for v in p["anchor"])
    at_v, at_u = (int(v) for v in (p.get("at") or (0, 0)))
    c.world_origin = (av + at_v, ay, au + at_u)
    c.meta = {
        "kind": "mine_ridge",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "frontier",
        "facing": "west",
        "profile_axis": "u",
        "signs": lot.signs,
        "refused": lot.refused,
        "parts": parts,
        "contract": (
            "a rock mass that wraps the Mine Coaster without occupying one cell the ride owns: "
            "talus whose reach and height are functions of the face above it, a crest south of "
            "the ride where the ride is lowest, benches only where the face is too steep to "
            "stand on, gravel only on a crust that is solid to the ground, and a walk-through "
            "adit whose cover is guaranteed before the mass is filled"),
    }
    return c
