"""A turtle, basking on the harbor's north shore - the quarter's second animal accent.

WHY A TURTLE PASSES WHERE THE MAMMALS FAILED. Same test as the ladybird: its identity is a
PATTERN ON A SINGLE CONVEX DOME - scute seams on a shell - and the canonical view is the
PLAN, which voxels give away free. The dome is a primitive, the head is a taper, the flippers
are splayed pads: hardware, all of it. And like the ladybird it needs a scale reference,
which the shore gives it - a shell beside a quay is instantly an animal, not a rock.

SIZE FROM THE PATTERN, SPACING FROM THE LADYBIRD. A scute plate needs ~2-3 cells to read and
a seam needs its own cell between plates; a 3x3 grid of plates with seams sets the shell at
~9 long, total animal ~14. Bigger would crowd the quay it borrows scale from.

COLOUR AGAINST THE GROUND, MEASURED. The moss floor is (89,110,45) - a green turtle vanishes
on it, the elephant's deepslate lesson. Shell plates are brown_wool (114,72,41), a full hue
flip; seams black_wool; skin oak_planks (162,131,79), pale tan, 48+ off both the shell and
the moss, uniform-textured so no log-face problem.

THE GAZE IS CARDINAL AND THE FEET ARE DRY - both axolotl lessons. It faces WEST, head toward
the water, nose stopping short of the line; every column seats on its own dry ground and the
shell's rim drops a skirt to meet the terrain so nothing floats over a dip. Eyes are the
FRONTMOST cell of their cheek, ringed pale, so nothing can stand in front of them.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .ruinring import _free, _surface

TURTLE = {
    "under": None,
    "at": None,                # [x, z] centre of the SHELL; the head extends west of it
    "base_y": None,            # plastron plane - PIN once built
    "shell_l": 9,              # along X (the axis of travel)
    "shell_w": 8,              # across Z
    "dome_h": 4,
    "seed": 0,

    "plate": "brown_wool",
    "seam": "black_wool",
    "skin": "oak_planks",
    "eye": "black_wool",
    "ring": "white_wool",
}


def _put(w, ctx, x, y, z, name, **props):
    if _free(ctx, x, y, z) and not w.has(x, y, z):
        w.put(x, y, z, name, **props)
        return 1
    return 0


def _dry(ctx, x, z):
    g, nm = _surface(ctx, x, z)
    return (g, nm) if g is not None and nm not in ("water", "ice") else (None, None)


def build_turtle(cfg: dict, donors=None) -> Canvas:
    p = {**TURTLE, **cfg}
    if not p.get("under") or not p.get("at"):
        raise ValueError("turtle needs params.under and params.at")
    ctx = Ctx(p["under"])
    seed = int(p["seed"])
    ax, az = (int(v) for v in p["at"])
    L, Wd, Hd = int(p["shell_l"]), int(p["shell_w"]), int(p["dome_h"])
    a, b = L / 2.0, Wd / 2.0
    if p.get("base_y") is not None:
        BY = int(p["base_y"])
    else:
        gs = sorted(g for dx in range(-L // 2, L // 2 + 1) for dz in range(-Wd // 2, Wd // 2 + 1)
                    for g, nm in [_dry(ctx, ax + dx, az + dz)] if g is not None)
        BY = gs[len(gs) // 2] + 1                      # then PIN it in the config

    w = World()
    feats = {"shell": 0, "skirt": 0, "skin": 0, "eyes": 0}
    top_at = {}                                        # our own top map - no Canvas.get -1 trap

    # ---- the dome, solid from the plastron plane up; rim columns skirt down to ground ----
    for dx in range(-L // 2, L // 2 + 1):
        for dz in range(-Wd // 2, Wd // 2 + 1):
            u = (dx / a) ** 2 + (dz / b) ** 2
            if u > 1.0:
                continue
            x, z = ax + dx, az + dz
            g, _nm = _dry(ctx, x, z)
            if g is None:
                continue                               # the water keeps its column
            h = max(1, int(round(Hd * (1.0 - u) ** 0.7)))
            for k in range(h):
                feats["shell"] += _put(w, ctx, x, BY + k, z, p["plate"])
            top_at[(x, z)] = BY + h - 1
            if u > 0.55:                               # the rim: drop to meet the ground
                for y in range(g + 1, BY):
                    feats["skirt"] += _put(w, ctx, x, y, z, p["plate"])

    # ---- scutes: seams painted on the dome's own top cells, spine plus 3-grid ----
    for (x, z), ty in top_at.items():
        dx, dz = x - ax, z - az
        u = (dx / a) ** 2 + (dz / b) ** 2
        rim = u > 0.72
        seam = rim or dz == 0 or (dx % 3 == 0 and abs(dz) <= b) or (abs(dz) == 2)
        if seam and w.name(x, ty, z) == p["plate"]:
            w.put(x, ty, z, p["seam"])

    # ---- the head: a blunt taper west, CARDINAL, the neck stepping one course down
    # toward the water so the head rides near its own ground rather than hovering ----
    hx0 = ax - L // 2 - 1                              # neck starts here, head runs west
    for dz in (-1, 0):
        feats["skin"] += _put(w, ctx, hx0, BY, az + dz, p["skin"])
        feats["skin"] += _put(w, ctx, hx0, BY - 1, az + dz, p["skin"])
    for hx in (hx0 - 1, hx0 - 2):
        for dz in (-1, 0):
            for y in (BY - 1, BY):
                feats["skin"] += _put(w, ctx, hx, y, az + dz, p["skin"])
    for dz in (-1, 0):                                 # the nose, one course, blunt
        feats["skin"] += _put(w, ctx, hx0 - 3, BY - 1, az + dz, p["skin"])
    # eyes: the FRONTMOST cell of each cheek band, ringed pale above and behind
    ex = hx0 - 2
    for dz in (-2, 1):
        eye = _put(w, ctx, ex, BY, az + dz, p["eye"])
        feats["eyes"] += eye
        if eye:
            _put(w, ctx, ex + 1, BY, az + dz, p["ring"])
            _put(w, ctx, ex, BY + 1, az + dz, p["ring"])

    # ---- flippers: splayed pads ROOTED at the shell's edge and run outward - a pad placed
    # at the diagonal is a separate component, which is how ear tips broke off once ----
    flip = 0
    front = ((-3, 3), (-4, 3), (-4, 4), (-5, 4))       # fore flippers sweep forward
    rear = ((3, 3), (4, 3), (4, 4))                    # hind ones shorter
    for offs, sz in ((front, 1), (front, -1), (rear, 1), (rear, -1)):
        cells = [(ax + odx, az + odz * sz, g) for (odx, odz) in offs
                 for g, _nm in [_dry(ctx, ax + odx, az + odz * sz)] if g is not None]
        if not cells:
            continue
        # one level per flipper - cells on different courses touch only diagonally and a
        # flipper on a ground step would come off as its own component
        level = min(BY, max(g for _x, _z, g in cells) + 1)
        for x, z, _g in cells:
            flip += _put(w, ctx, x, level, z, p["skin"])
    feats["flippers"] = flip
    # ---- the tail: one cell east, on the spine line ----
    feats["tail"] = _put(w, ctx, ax + L // 2 + 1, BY, az, p["skin"])

    return w.canvas({"kind": "turtle", "profile_view": "side", "facing": [-1, 0],
                     "base_y": BY, "features_built": feats})
