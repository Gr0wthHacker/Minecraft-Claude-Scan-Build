"""A giraffe, lofted along a spine rather than stacked out of boxes.

    giraffe: superellipse cross-sections swept along four spines (legs, body, neck, head), with float
             radii interpolated from a handful of keyframes, then dressed in a Voronoi coat.

Four versions to get here, and each failure taught something worth keeping:

1. ELLIPSOIDS look melted - as whole body parts. Solved by snapping the heading to a cardinal and
   keeping the massing crisp. That still holds: what changed in v5 is only the CROSS-SECTION.
2. PROPORTION names the animal, detail does not. Neck longer than the body, legs about as long as the
   neck, and a back that falls hard from withers to hips. v3 got these wrong and was an alpaca.
3. The COAT is a Voronoi diagram, not noise - hard patches with pale grout. See `coat.py`.
4. STACKED BOXES ARE LUMPY, and measurably so. v4's neck held exactly 17 cells for eleven courses and
   then jumped to 26, because an integer half-width holds and then steps. Its head ballooned from 9
   cells to 34 in one course - a pinhead on a stick. Both are fixed by the same thing: sweep a
   superellipse whose radii are FLOATS along a spine. A float radius shrinks a little every course, so
   the taper is smooth, and the exponent rounds off the corners a filled rectangle always has.

`SECTION_N` is the shape dial: 2 is an ellipse, large is a rectangle. It sits at 2.4 - round enough to
read as an animal, square enough to still look built.
"""
from __future__ import annotations

from . import coat, smooth
from . import giraffe_parts as G
from .canvas import Canvas
from .vertical import Ctx, World

GIRAFFE = {
    "under": None,
    "feet": None,               # world (x, y, z) the hooves stand on
    "look_at": None,            # world (x, y, z) it faces; snapped to the nearest cardinal
    # -- proportions. These ARE the design; everything else is dressing.
    "leg": 20,                  # hoof to belly. About as long as the neck: that is a giraffe.
    "hoof": 3,
    "leg_r": 1.7,               # leg half-width at the knee; ankles and haunch derive from it
    "body_len": 15,             # SHORTER than the neck
    "withers": 10,              # body depth at the shoulder
    "hips": 6,                  # ...and at the rump. The drop between them is the back slope
    "body_r": 4.4,              # body half-width across the barrel
    "neck": 21,                 # LONGER than the body
    "neck_r0": 2.9,             # half-width at the shoulder
    "neck_r1": 1.7,             # ...and at the jaw
    "neck_lean": 0.40,          # blocks forward per block up
    "head_len": 9,
    "head_r": 2.6,              # cranium half-width
    "section_n": 2.4,           # superellipse exponent: 2 = round, big = square
    # -- palette, chosen from all 1193 real block colours (see `mcbuild.blocks.nearest`)
    "coat_block": "smooth_sandstone",        # pale straw
    "patch": "smooth_red_sandstone",         # ochre
    "patch_alt": "cut_red_sandstone",        # same colour, different texture: variety without noise
    "hoof_block": "dark_oak_wood",
    "dark": "black_wool",
    "muzzle": "bone_block",                  # giraffes have a pale muzzle and pale eye rings
    "patch_scale": 5.5,
    "grout": 0.85,
    # -- smoothing. See `smooth.py`; measure the effect with `tools/smoothness.py`.
    "relax_rounds": 2,
    "relax_fill": 14,           # air cells with this many of 26 solid neighbours fill in
    "relax_keep": 9,            # solid cells with fewer than this are shaved off
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air", "vine")
CARDINALS = {(1, 0): (0, 1), (-1, 0): (0, -1), (0, 1): (-1, 0), (0, -1): (1, 0)}


def build_giraffe(cfg: dict, donors=None) -> Canvas:
    p = {**GIRAFFE, **cfg}
    for k in ("feet", "look_at"):
        if p.get(k) is None:
            raise ValueError(f"giraffe needs params.{k}")
    ctx = Ctx(p["under"]) if p.get("under") else None
    fx, fy, fz = (int(v) for v in p["feet"])
    tx, _ty, tz = (int(v) for v in p["look_at"])

    dx, dz = tx - fx, tz - fz
    f = (1 if dx > 0 else -1, 0) if abs(dx) >= abs(dz) else (0, 1 if dz > 0 else -1)
    s = CARDINALS[f]

    # ---- 1. the solid MASS: legs, body, neck, skull. Nothing thin, nothing coloured.
    hide: set = set()
    accent: dict = {}
    belly = fy + int(p["leg"])
    hoofs = G.legs(hide, ctx, fx, fy, fz, f, s, p)
    shoulder = G.body(hide, fx, belly, fz, f, s, p)
    neck_top, neck_r = G.neck(hide, shoulder, f, s, p)
    head_at = G.head(hide, neck_top, neck_r, f, s, p)

    # ---- 2. relax it. Cellular smoothing fills the one-block dents a loft leaves between sections
    # and shaves the single blocks poking out of them - the two things that read as "lumpy".
    # It runs on the MASS ALONE: an ossicone or a tail has few neighbours by nature, and the same
    # rule that shaves a pimple eats them whole. They are added after.
    if int(p["relax_rounds"]):
        # The air BETWEEN the legs is barred from filling. Left to itself the fill pass reads two leg
        # surfaces facing each other across a narrow gap as a dent and welds them: the audit found
        # the four legs merged into one or two parts for the whole lower half, an 11-block "leg"
        # against a target of 3. Below the belly, only cells near a leg's own axis may be filled.
        gap = set()
        reach = float(p["leg_r"]) + 1.4
        for (lx, lz, gy, _r) in hoofs:
            for y in range(min(g for (_a, _b, g, _c) in hoofs) - 1, belly + 1):
                for dx in range(-int(reach) - 4, int(reach) + 5):
                    for dz in range(-int(reach) - 4, int(reach) + 5):
                        c = (lx + dx, y, lz + dz)
                        if all((abs(c[0] - ax) ** 2 + (c[2] - az) ** 2) ** 0.5 > reach
                               for (ax, az, _g, _rr) in hoofs):
                            gap.add(c)
        hide = smooth.relax(hide, rounds=int(p["relax_rounds"]), fill=int(p["relax_fill"]),
                            keep=int(p["relax_keep"]), forbid=gap)

    # ---- 3. thin features and colour, onto the smoothed mass
    for (lx, lz, gy, lrad) in hoofs:
        for c in hide:
            if gy <= c[1] < gy + int(p["hoof"]) and abs(c[0] - lx) <= lrad and abs(c[2] - lz) <= lrad:
                accent[c] = p["hoof_block"]
    G.mane(hide, shoulder, f, s, p)
    G.crown(hide, accent, head_at, f, s, p)
    G.face(hide, accent, head_at, f, s, p)
    G.tail(hide, accent, fx, belly, fz, f, s, p)

    skin = coat.voronoi(hide, p["patch"], p["coat_block"], scale=float(p["patch_scale"]),
                        grout_width=float(p["grout"]), seed=int(p["seed"]),
                        tones=[p["patch"], p["patch_alt"]])
    w = World()
    for cell in sorted(hide):
        w.put(*cell, accent.get(cell) or skin.get(cell, p["coat_block"]))

    hi = max(y for (_x, y, _z) in hide)
    hits = 0 if ctx is None else sum(1 for c in hide if ctx.name_at(*c) not in AIRY)
    return w.canvas({"kind": "giraffe", "feet": [fx, fy, fz], "facing": list(f),
                     "height": hi - fy, "top_y": hi, "neck_top_y": neck_top[1], "collisions": hits})
