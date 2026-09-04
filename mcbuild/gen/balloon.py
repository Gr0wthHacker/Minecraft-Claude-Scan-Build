"""A moored show balloon - envelope, rigging, basket. The causeway's bright landmark.

WHY A BALLOON AND NOT AN ANIMAL. CLAUDE.md's measured line is PLANAR/COLUMNAR against
VOLUMETRIC, and it was learned on eight failed mammals: compound muscle is the one thing voxels
render worst, and no amount of scale rescues it. What reads is a plane, a taper, a column, or
**one convex mass with a pattern on it** - the ladybird's category, arrived at again by the
download corpus (`Warm Snooze`, a curled cat, reads instantly where a standing one never did).

A hot-air balloon is that category twice over and nothing else:

    envelope    ONE convex dome, which is a voxel primitive rather than a blend of five muscle
                groups - and its identity is a PATTERN on that dome, exactly the ladybird's own
                claim. Nothing here has to be measured to a percent; the gores have to be the
                right width
    rigging     four vertical lines through open air. A column
    basket      a small square box. A box

There is no volume anywhere that has to describe a joint, and no proportion that has to be
right to within a few per cent for a stranger to name it. A red-and-white dome on lines over a
wicker box is a hot-air balloon to everybody who has ever seen one, from any bearing, at any
distance, and it is a FAIRGROUND object - which is what the midway end of this reach is.

**THE GAP IS THE FEATURE.** The four courses of open air between the basket's rim and the
envelope's mouth, crossed only by four rope lines, are what separate this from a lollipop. Fill
them in and the silhouette is a blob on a stick. This is the ladybird's spot-spacing rule and
the frog's hand rule in a third body: the negative space does as much work as the blocks.

**THE THROAT DECIDES THE RIGGING, AND IT IS 6-CONNECTIVITY THAT DECIDES THE THROAT.** A real
balloon's lines splay outward from the basket to a much wider hem, and a splayed line is a
DIAGONAL - which is not connected in this project's own sense and has cost it ear tips,
ossicones and a whole dragonfly. So the envelope pinches to a mouth no wider than the basket
and the four lines are dead vertical, from the basket's own corner columns to the mouth ring
directly above them. That is also what a balloon under inflation actually looks like.

SIZE COMES FROM THE GORES, the way the ladybird's came from its spots, and the count is a
measured trade rather than a taste. A gore has to be about four cells wide at the equator to
read as a stripe instead of a stagger; a 16-wide dome has ~50 cells of circumference there, so
ten gores is five cells and twelve is four. EIGHT was the first try and it is wrong in the one
view that matters: head-on you see half the envelope, so eight gores is four faces and the
thing reads as a beach ball. Ten gives five. Below about eleven blocks of dome no count works
and what is left is a red ball.

PALETTE - all cheap tier, all wool, and Jack's own rule that wool is for the things that are
not the ground. The value ladder is measured ACROSS families, never within one (this repo drew
the opposite conclusion three times from searching inside a single material):

    white_wool 236 . yellow_wool 162 . stone_bricks 122 . spruce_planks 83 . red_wool 78
    . dark_oak_planks 43 . black_wool 23

so the alternating gores are 158 points apart - the single biggest step this economy offers -
and every horizontal band on the envelope has something to be a line against.

NO LIGHT IS BUILT INTO THE COAT. A burner would be the one honest place for a lamp on this
whole causeway and it still does not get one: `isthmus._delight` records every cell a sculpture
emits and lights it from the air beside it, and a froglight the generator placed itself would
be indistinguishable from the 1,138 the night sweep once drove into these creatures' coats. The
mouth is `yellow_wool` instead - the colour of the flame, not the light of it.
"""
from __future__ import annotations

import math

from .canvas import Canvas

BALLOON = {
    "seed": 0,               # unused: this shape has no noise in it anywhere, and it is here
                             # so a spec written for any other creature still resolves
    "scale": 1.0,
    # world coordinate of the canvas corner. A bespoke generator states this itself or the
    # pipeline writes no sidecar - and with no sidecar there is no origin, no in-context audit
    # and no `/cscan place`.
    "at": None,
    # ...or give `stand`, the world cell the BASKET FLOOR occupies. Anchoring by the thing that
    # carries the weight beats anchoring by the corner of a bounding box, which is the mistake
    # `heron.py` records having made once with `feet`.
    "stand": None,

    "radius": 7.5,          # half the envelope at its widest: 16 across
    "height": 18,           # courses of envelope
    "throat": 3.2,          # the mouth, and therefore the rigging's own footprint
    "gores": 10,            # even, or two gores of one colour meet round the back
    "band_at": 0.31,        # where the one horizontal band crosses the gores
    "basket_half": 2,       # a 5x5 basket: the throat has to cover its corners
    "basket_h": 3,
    "rig": 4,               # courses of OPEN AIR between the basket rim and the mouth

    "gore_a": "red_wool",
    "gore_b": "white_wool",
    "hoop": "black_wool",       # the load hoop at the mouth, and the crown's own valve cap
    "flame": "yellow_wool",     # the throat: the colour of the burner, never its light
    "rope": "dark_oak_fence",
    "basket": "spruce_planks",
    "rim": "dark_oak_planks",
    "sandbag": "brown_wool",
}


def _profile(s: float, throat: float, radius: float) -> float:
    """The envelope's own radius at fraction `s` up it: 0 is the mouth, 1 the crown.

    AN INVERTED TEARDROP, not an ellipse. A balloon swells fast off its throat, carries its
    width high - widest around two thirds up - and rounds over to a broad crown rather than a
    point. Drawn as an ellipsoid it reads as an egg, and the whole naming test is that a
    stranger says "balloon" without being told.
    """
    if s < 0.45:
        return throat + (radius - throat) * (s / 0.45) ** 0.75
    if s < 0.68:
        return radius
    u = (s - 0.68) / 0.345
    return radius * max(0.0, 1.0 - u * u) ** 0.5


def build_balloon(cfg: dict, donors=None) -> Canvas:
    p = {**BALLOON, **cfg}
    sc = float(p.get("scale", 1.0))
    R = float(p["radius"]) * sc
    H = max(6, int(round(float(p["height"]) * sc)))
    throat = max(2.0, float(p["throat"]) * sc)
    bh = max(1, int(round(float(p["basket_half"]) * sc)))
    bhh = max(2, int(round(float(p["basket_h"]) * sc)))
    rig = max(2, int(round(float(p["rig"]) * sc)))
    gores = max(4, int(p["gores"]) // 2 * 2)

    rad = int(math.ceil(R)) + 2
    SX = SZ = 2 * rad + 1
    y_env = bhh + 1 + rig                       # the mouth's own course
    SY = y_env + H + 2
    c = Canvas(SX, SY, SZ, donors)
    st = c.state
    S = {k: st(p[k]) for k in ("gore_a", "gore_b", "hoop", "flame", "rope",
                               "basket", "rim", "sandbag")}
    cx = cz = rad

    # ---- BASKET. A square box with a floor, three courses of side and a darker rim - the rim
    # is what stops it reading as a crate, and it is the only horizontal line down here.
    for dx in range(-bh, bh + 1):
        for dz in range(-bh, bh + 1):
            c.put(cx + dx, 0, cz + dz, S["basket"])
    for y in range(1, bhh + 1):
        blk = S["rim"] if y == bhh else S["basket"]
        for dx in range(-bh, bh + 1):
            for dz in range(-bh, bh + 1):
                if max(abs(dx), abs(dz)) == bh:
                    c.put(cx + dx, y, cz + dz, blk)

    # SANDBAGS on the outside of the basket, one a side. Four cells, and they are the
    # difference between a box and a box somebody flies: they read at distance as the thing
    # hanging off a gondola. Placed against a wall cell that exists, never at a computed
    # offset - every detached-feature bug in this repo is the second of those two.
    bags = 0
    for dx, dz in ((bh + 1, 0), (-bh - 1, 0), (0, bh + 1), (0, -bh - 1)):
        ax, az = cx + dx, cz + dz
        anchor = (cx + (bh if dx > 0 else -bh if dx < 0 else 0),
                  cz + (bh if dz > 0 else -bh if dz < 0 else 0))
        if c.solid(anchor[0], max(1, bhh - 1), anchor[1]):
            c.put(ax, max(1, bhh - 1), az, S["sandbag"])
            bags += 1

    # ---- RIGGING. Four DEAD VERTICAL lines from the basket's own corner columns up to the
    # mouth ring. Vertical because a splayed line is a diagonal and a diagonal is not connected
    # - see the module docstring. This is the whole reason the throat is as wide as it is.
    ropes = []
    for sx in (-bh, bh):
        for sz in (-bh, bh):
            if (sx * sx + sz * sz) ** 0.5 > throat:
                continue                       # the mouth does not reach this corner: no line
            for y in range(bhh + 1, y_env):
                c.put(cx + sx, y, cz + sz, S["rope"])
            ropes.append((sx, sz))

    # ---- ENVELOPE. Stacked discs, coloured by GORE - the angular wedge is the whole identity,
    # and it is a pattern on a convex mass rather than a shape that has to be modelled.
    for i in range(H):
        s = i / float(H - 1)
        r = _profile(s, throat, R)
        y = y_env + i
        for dx in range(-rad, rad + 1):
            for dz in range(-rad, rad + 1):
                if (dx * dx + dz * dz) ** 0.5 > r:
                    continue
                if i == 0:
                    blk = S["hoop"]                       # the load hoop, one course
                elif s < 0.13:
                    blk = S["flame"]                      # the mouth, lit by the burner
                elif i >= H - 1:
                    # THE CROWN VALVE IS ONE COURSE, and that took a render to settle. Given
                    # the top TWO it covered a disc of radius 5.5 out of 7.5 and the plan view -
                    # which is a view every visitor gets from the skyway - was a black hole with
                    # a red-and-white fringe round it. One course is a ring you can read as a
                    # valve, and the gores are left to converge at the top the way a real
                    # envelope's do, which is the whole of what a balloon looks like from above.
                    blk = S["hoop"]
                elif abs(s - float(p["band_at"])) < 0.035:
                    blk = S["hoop"]                       # ONE horizontal band - see below
                else:
                    ang = math.atan2(dz, dx) / (2 * math.pi) + 1.0
                    g = int(ang * gores) % gores
                    blk = S["gore_a"] if g % 2 else S["gore_b"]
                c.put(cx + dx, y, cz + dz, blk)

    # NO SPECKLE, ONE BAND. The first pass scattered "weathered panels" over the gores for
    # tonal variety and they read exactly as this project's own scatter rules predict: dirty
    # rectangles on a clean fabric, the deck soffit's confetti in a third body. A balloon's
    # tone comes from the GORE, which is already a 158-point value step, and its one horizontal
    # element is a band - so there is one band, it is `hoop` black, it is 35 luminance under
    # the red and 213 under the white, and there is nothing else.
    patched = 0

    if p.get("stand"):
        wx, wy, wz = (int(round(float(v))) for v in p["stand"])
        c.world_origin = (wx - cx, wy, wz - cz)
    elif p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    c.meta = {"kind": "balloon", "scale": sc, "facing": [0, 1],
              "features_built": {"gores": gores, "ropes": len(ropes), "sandbags": bags,
                                 "basket": 1, "hoop": 1, "valve": 1, "patches": patched}}
    return c


build = build_balloon
DEFAULTS = BALLOON
