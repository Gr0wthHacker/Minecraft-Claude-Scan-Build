"""A heron, standing. The one body plan this medium renders without fighting it.

    heron: stilt legs, an S-curved neck, a dagger beak, a folded wing of layered coverts.

WHY A HERON AND NOT A MAMMAL. Everything in `quadruped.py` that reads badly reads badly for the same
reason: a cat's shoulder and a bear's haunch are COMPOUND VOLUMETRIC MUSCLE, and voxels describe that
worst of anything. What voxels describe perfectly is PLANAR and COLUMNAR form - a flat layered plane,
a straight taper. The two builds players picked out on this island are the sky bird (an 83-block
wingspan of layered primaries) and the giraffe (a neck); the gecko, third, is splayed limbs on a wall.
All planes and columns.

A heron has no volumetric component anywhere:

    dagger beak     a linear taper - the same primitive as the elephant's trunk, which at 385 cells
                    is the best-reading feature in the repo
    S-curved neck   a column, which is the giraffe's entire claim to fame
    stilt legs      columns. "The legs read as posts" was the standing complaint about every mammal
                    here; on a heron a post is CORRECT
    folded wing     flat layered planes - the sky bird's proven strength, and the one thing that
                    genuinely improves with size, because more blocks means more feather COURSES
                    rather than more noise

Built at `scale` for detail. The feather layering, the toes and the eye are per-block work that
cannot exist small, so this is a design that wants to be built big rather than one that survives it.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01

# A WADING BIRD, IN TWO SPECIES. The skeleton is identical - stilt legs, S-neck, dagger, planar
# wing - because that is the body plan the medium can build. What separates them is the same thing
# that separates a lion from a leopard: colour, and two or three curves.
#
#   bill        a heron's is a straight dagger; a flamingo's KINKS DOWN halfway along, and that
#               kink is the single most recognisable thing about the bird
#   neck        a heron folds its neck into a shallow S; a flamingo's is longer and far more
#               sinuous, and it hangs the head lower than the shoulder
#   stance      a flamingo tucks one leg up against the body, which a heron does too but which on
#               a pink bird is the pose everybody pictures
VARIANTS = {
    # EVERY BLOCK CHEAP TIER. The first palette was 45% concrete and terracotta - 3,701 blocks of
    # dye, clay and smelting on a skyblock - for tones that wool and plain stone give away free.
    # `light_gray_concrete` -> `stone` is 11 in RGB; `gray_concrete` -> `gray_wool` is 15.
    "heron": {
        "body": "light_gray_wool", "wing": "stone", "wing_edge": "gray_wool",
        "pale": "white_wool", "dark": "black_wool", "beak": "yellow_wool",
        "eye": "orange_wool", "leg": "dark_oak_planks", "primary": "black_wool",
        "bill_kink": 0.0, "neck_s": 1.0, "neck_len": 20.0, "tuck": False, "speckle": 0.16,
        "body_tilt": 1.2,
        "crest": True,
    },
    "flamingo": {
        # bright, and it is the whole point: pink against dark moss is the strongest signal any
        # animal on this island can send. Measured, the heron's grey sits +40 luminance clear of
        # the lowland floor - a flamingo's pink clears it on HUE as well, which nothing else does.
        # wool the whole way down: a flamingo is the one animal here whose colour needs no clay,
        # because sheep come in exactly these three. Deep red coverts banded over a pale pink body
        # is what the bird actually looks like, and it costs a dye.
        # BLACK PRIMARIES are the flamingo detail, and `magenta_wool` in the courses read as a
        # bruise between the red and the pink - the bands want two tones of the same colour, not a
        # third hue. Red coverts banded over pink, black flight feathers.
        "body": "pink_wool", "wing": "red_wool", "wing_edge": "pink_wool",
        "pale": "pink_wool", "dark": "black_wool", "beak": "pink_wool",
        "eye": "yellow_wool", "leg": "pink_wool", "primary": "black_wool",
        "bill_kink": 1.0, "neck_s": 1.9, "neck_len": 26.0, "tuck": True, "speckle": 0.0,
        # a standing flamingo does NOT hold its body level - it slopes down to the breast,
        # with the tail carried high and the neck leaving from a low point at the front.
        # Level, it read as a pink heron on one leg.
        "body_tilt": 3.0,
        # a flamingo has no nape plumes and no dark eye-stripe; wearing the heron's made it look
        # like a heron someone had painted
        "crest": False,
    },
}

HERON = {
    "variant": "heron",
    "size": [46, 64, 42],
    "seed": 0,
    "scale": 1.0,
    # world coordinate of the canvas corner. A bespoke generator has to state this
    # itself - `World.canvas()` does it for the parametric ones - or the pipeline
    # writes no sidecar, and without a sidecar there is no origin, no in-context
    # audit and no `/cscan place`. The gecko still has this gap.
    "at": None,
    # ...or give `feet` and let it work the corner out. Positioning a bird by the corner of
    # its bounding box means doing the offset by hand every time and getting it wrong once.
    "feet": None,
    # a grey heron: pale body, slate wing, near-white neck, black crest and shoulder stripe.
    # Chosen to sit about +40 luminance clear of the lowland's moss - the elephant failed at a
    # minimum dRGB of 0 by being built out of the ground it stood on.
    "body": "light_gray_wool",
    "wing": "light_gray_concrete",
    "wing_edge": "gray_concrete",
    "pale": "white_wool",
    "dark": "black_wool",
    "beak": "yellow_terracotta",
    "eye": "orange_wool",
    "leg": "brown_terracotta",
}


def _taper(c: Canvas, pts, r0, r1, blk, n=72, squash=1.0):
    """A bezier sweep of shrinking spheres - the repo's one great primitive, taken from gecko.py."""
    pts = [np.array(q, float) for q in pts]
    for i in range(n):
        t = i / max(1, n - 1)
        layer = pts
        while len(layer) > 1:
            layer = [(1 - t) * a + t * b for a, b in zip(layer, layer[1:])]
        q = layer[0]
        c.sphere(q[0], q[1], q[2], r0 + (r1 - r0) * t, blk, squash=squash)


def _stick(c: Canvas, x, y, z, blk) -> bool:
    """Place a single cell ONLY where it has something to hold on to.

    Every detached-feature bug in this repo is the same mistake: a detail placed at a COMPUTED
    position rather than against the surface that was actually built. The eyes and claw tips here
    were floating one cell clear of a curved head, which put the design in four pieces and would
    have failed the `single_component` gate outright.
    """
    x, y, z = int(round(x)), int(round(y)), int(round(z))
    if c.get(x, y, z):
        c.put(x, y, z, blk)
        return True
    for dx, dy, dz in ((0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
        if c.get(x + dx, y + dy, z + dz):
            c.put(x, y, z, blk)
            return True
    return False


def build_heron(cfg: dict, donors=None) -> Canvas:
    p = {**HERON, **cfg}
    p = {**p, **VARIANTS.get(p.get("variant", "heron"), {}), **cfg}
    V = p
    sc = float(p.get("scale", 1.0))
    SX, SY, SZ = (max(8, int(round(v * sc))) for v in p["size"])
    seed = int(p["seed"])
    c = Canvas(SX, SY, SZ, donors)
    st = c.state
    S = {k: st(p[k]) for k in ("body", "wing", "wing_edge", "pale", "dark", "beak", "eye", "leg")}
    S["primary"] = st(p.get("primary") or p["wing_edge"])
    cx, cz = SX / 2.0, SZ / 2.0
    u = sc                                             # one unit of the design's own scale
    foot_y, hock_y, body_y = 1.4, 16.0 * u, 33.0 * u

    # ---- LEGS: columns with a BACKWARD-bending hock, the joint everyone recognises on a wading
    # bird and nobody can name. Feet get three forward toes and one back, splayed flat - the
    # gecko's fanned toes, which are a large part of why it reads.
    for side in (-1, 1):
        lx = cx + side * 3.2 * u
        if V.get("tuck") and side > 0:
            # the STANDING leg carries the whole bird, so it moves under the centre of mass. This
            # has to happen before the columns are drawn, not after - setting it later left the
            # toes 3 blocks from the leg they belong to and put the design in two pieces.
            lx = cx
        if V.get("tuck") and side < 0:
            # ONE LEG FOLDED UP against the body - the pose everyone pictures a flamingo in, and
            # the reason the silhouette is unmistakable even in a thumbnail
            c.line((lx, body_y - 3.0 * u, cz - 0.8 * u),
                   (lx - 0.6 * u, body_y - 7.0 * u, cz + 3.0 * u), 1.15 * u, S["leg"])
            c.line((lx - 0.6 * u, body_y - 7.0 * u, cz + 3.0 * u),
                   (lx + 0.4 * u, body_y - 4.0 * u, cz + 6.0 * u), 0.95 * u, S["leg"])
            continue
        c.line((lx, foot_y, cz + 1.2 * u), (lx, hock_y, cz + 2.6 * u), 1.05 * u, S["leg"])
        c.line((lx, hock_y, cz + 2.6 * u), (lx, body_y - 2.0 * u, cz - 0.8 * u), 1.3 * u, S["leg"])

        # toes get their OWN course at the very bottom and a knuckle at each tip, so they read as
        # toes from the side rather than vanishing into the ground line
        for a, dz in ((0.0, 4.6), (-1.0, 3.6), (1.0, 3.6), (0.0, -3.4)):
            tipx, tipz = lx + a * 2.9 * u, cz + 1.2 * u + dz * u
            # thick enough to WELD to the ankle: at 0.62 the rounding stranded the tips
            # and put the design in four pieces
            c.line((lx, foot_y, cz + 1.2 * u), (tipx, foot_y, tipz), 0.85 * u, S["leg"])
            c.line((lx, foot_y + 0.9 * u, cz + 1.2 * u), (tipx, foot_y + 0.4 * u, tipz),
                   0.5 * u, S["leg"])
            c.sphere(tipx, foot_y, tipz, 0.85 * u, S["dark"])

    # ---- BODY: a compact ovoid tilted nose-up, with tail coverts trailing back and down
    # THE BODY IS SWEPT ALONG A TILTED SPINE, not set as one upright ellipsoid. A single ellipsoid
    # cannot lean, so the body sat dead level however the rest of the bird was posed - and a level
    # body is the one thing that made the flamingo read as a heron wearing pink.
    tilt = float(V["body_tilt"])
    rear = np.array([cx, body_y + tilt * u, cz - 7.5 * u])
    fore = np.array([cx, body_y - tilt * u, cz + 6.5 * u])
    for i in range(26):
        s_ = i / 25.0
        q = rear + (fore - rear) * s_
        w = 1.0 - (2.0 * s_ - 1.0) ** 2                    # 0 at each end, 1 amidships
        c.ellipsoid(q[0], q[1], q[2],
                    (2.0 + 3.6 * w) * u, (2.4 + 4.4 * w) * u, (1.6 + 1.4 * w) * u, S["body"])
    # tail coverts trail back from the RAISED rear, so the tilt carries through the whole line
    _taper(c, [(cx, rear[1] + 0.5 * u, cz - 7.0 * u),
               (cx, rear[1] - 1.5 * u, cz - 13.0 * u),
               (cx, rear[1] - 4.5 * u, cz - 18.0 * u)], 3.4 * u, 0.9 * u, S["wing"])

    # ---- THE S-NECK. A standing heron folds its neck into an S rather than holding it straight,
    # and that kink is most of the outline's signature. Four control points, not two.
    nl, ns = float(V["neck_len"]), float(V["neck_s"])
    neck_top = body_y + nl * u
    # the S is DEEPER on a flamingo and shallower on a heron; `ns` scales how far the middle of the
    # neck swings back before the head comes forward again
    _taper(c, [(cx, body_y + (4.0 - tilt * 0.8) * u, cz + 1.5 * u),
               (cx, body_y + nl * 0.50 * u, cz - 3.4 * ns * u),
               (cx, body_y + nl * 0.80 * u, cz + 1.2 * u),
               (cx, neck_top, cz + 2.8 * u)], 2.7 * u, 1.55 * u, S["pale"])

    # ---- HEAD and the DAGGER: a straight linear taper, the elephant-trunk primitive aimed forward
    c.ellipsoid(cx, neck_top + 1.2 * u, cz + 3.2 * u, 2.3 * u, 2.1 * u, 2.9 * u, S["pale"])
    kink = float(V["bill_kink"])
    # A FLAMINGO'S BILL KINKS DOWN halfway along, and that bend is the single most recognisable
    # thing about the bird - straighten it and you have a pink heron. A heron's is a straight
    # dagger, so `kink` of 0 gives the two control points back in a line.
    _taper(c, [(cx, neck_top + 1.0 * u, cz + 5.0 * u),
               (cx, neck_top + (0.6 - 1.4 * kink) * u, cz + 9.5 * u),
               (cx, neck_top + (0.3 - 5.0 * kink) * u, cz + (13.5 - 2.0 * kink) * u)],
           1.5 * u, 0.42 * u, S["beak"])
    if kink:                                       # a black tip, which a flamingo also has
        c.sphere(cx, neck_top + (0.3 - 5.0 * kink) * u, cz + (13.5 - 2.0 * kink) * u,
                 0.7 * u, S["dark"])
    if V.get("crest", True):
        for k, dz in ((0.0, -3.2), (1.0, -5.0)):       # crest plumes off the nape
            c.line((cx, neck_top + 2.5 * u, cz + 1.0 * u),
                   (cx, neck_top + 1.7 * u - k * u, cz + dz * u), 0.5 * u, S["dark"])

    # ---- WINGS, FOLDED: layered courses of coverts down the flank. This is the sky bird's trick,
    # and the only part of the animal that gets BETTER with scale - each course is one block deep,
    # so a bigger bird has more feathers rather than blurrier ones.
    courses = max(3, int(round(6 * sc)))
    for side in (-1, 1):
        wx = cx + side * 5.2 * u
        for i in range(courses):
            t = i / max(1, courses - 1)
            # the courses lie ALONG the tilted flank: front (t=0) low, rear (t=1) high
            y = body_y + (3.2 - 8.0 * t) * u - tilt * (1.0 - 2.0 * t) * 0.7 * u
            blk = S["wing_edge"] if i % 2 else S["wing"]
            c.line((wx, y - tilt * 0.5 * u, cz + 4.2 * u),
                   (wx + side * 0.8 * u, y - 1.3 * u, cz - (1.0 + 5.4 * t) * u),
                   (1.55 - 0.6 * t) * u, blk)
    for k in range(max(2, int(round(4 * sc)))):        # primaries, so the folded wing ENDS somewhere
        for side in (-1, 1):
            c.line((cx + side * (4.2 + 0.5 * k) * u, body_y - 4.2 * u, cz - 5.0 * u),
                   (cx + side * (3.2 + 0.5 * k) * u, body_y - 6.8 * u - k * 0.6 * u, cz - 14.5 * u),
                   0.6 * u, S["primary"])

    # ---- EYE, and the dark stripe a grey heron carries from the eye back over the nape
    for side in (-1, 1):
        ex, ey, ez = (int(round(cx + side * 2.1 * u)), int(round(neck_top + 1.6 * u)),
                      int(round(cz + 4.2 * u)))
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if c.get(ex, ey + dy, ez + dz):
                    c.put(ex, ey + dy, ez + dz, S["pale"])
        _stick(c, ex, ey, ez, S["eye"])
        _stick(c, ex, ey, ez - 1, S["dark"])
    if V.get("crest", True):                           # the dark eye-to-nape stripe, heron only
        _taper(c, [(cx, neck_top + 0.8 * u, cz - 0.4 * u),
                   (cx, neck_top - 4.5 * u, cz - 1.8 * u)], 1.6 * u, 0.7 * u, S["dark"])

    # ---- speckling down the neck front, which is what a grey heron actually carries and what stops
    # the column reading as a length of pipe
    h = lambda *a: hash01(*a, seed)
    for y in range(int(body_y + 4 * u), int(neck_top)):
        for x in range(SX):
            for z in range(SZ - 2, 0, -1):
                if c.get(x, y, z) == S["pale"] and not c.get(x, y, z + 1):
                    if h(x, y, z, 3) < float(V["speckle"]):
                        c.put(x, y, z, S["dark"])
                    break
    if p.get("feet"):
        fx_, fy_, fz_ = (float(v) for v in p["feet"])
        c.world_origin = (int(round(fx_ - cx)), int(round(fy_ - foot_y)),
                          int(round(fz_ - (cz + 1.2 * u))))
    elif p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    c.meta = {"kind": p.get("variant", "heron"), "scale": sc, "facing": [0, 1],
                     "features_built": {"legs": 2, "toes": 8, "neck": 1, "beak": 1,
                                        "wing_courses": courses * 2, "crest": 2, "eyes": 2}}
    return c
