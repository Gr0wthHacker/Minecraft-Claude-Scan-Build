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

from . import coat
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

    hide: set = set()
    accent: dict = {}
    belly = fy + int(p["leg"])
    _legs(hide, accent, ctx, fx, fy, fz, f, s, p)
    shoulder = _body(hide, fx, belly, fz, f, s, p)
    neck_top, neck_r = _neck(hide, shoulder, f, s, p)
    _head(hide, accent, neck_top, neck_r, f, s, p)
    _tail(hide, accent, fx, belly, fz, f, s, p)

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


# ------------------------------------------------------------------ lofting

def _lerp(keys, t: float):
    """Piecewise-linear through (t, value...) keyframes. Values are tuples of floats."""
    if t <= keys[0][0]:
        return keys[0][1:]
    for (t0, *v0), (t1, *v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return tuple(a + (b - a) * u for a, b in zip(v0, v1))
    return keys[-1][1:]


def _disc(hide: set, cx, cy, cz, f, s, r_along, r_across, n: float, height: int = 1):
    """A horizontal superellipse section - used where the spine runs vertically (legs, neck)."""
    ra, rb = max(0.5, r_along), max(0.5, r_across)
    for a in range(-int(ra + 1), int(ra + 2)):
        for b in range(-int(rb + 1), int(rb + 2)):
            if (abs(a) / ra) ** n + (abs(b) / rb) ** n > 1.0:
                continue
            x = int(round(cx + f[0] * a + s[0] * b))
            z = int(round(cz + f[1] * a + s[1] * b))
            for k in range(height):
                hide.add((x, int(round(cy)) + k, z))


def _rib(hide: set, cx, cy, cz, f, s, r_across, r_up, n: float, squash_lo: float = 1.0):
    """A vertical superellipse section ACROSS the heading - used where the spine runs horizontally
    (body, head). `squash_lo` flattens the underside, which is what gives a belly rather than a tube."""
    rb, rv = max(0.5, r_across), max(0.5, r_up)
    for b in range(-int(rb + 1), int(rb + 2)):
        for k in range(-int(rv + 2), int(rv + 2)):
            rr = rv * (squash_lo if k < 0 else 1.0)
            if (abs(b) / rb) ** n + (abs(k) / max(0.5, rr)) ** n > 1.0:
                continue
            hide.add((int(round(cx + s[0] * b)), int(round(cy)) + k, int(round(cz + s[1] * b))))


# ------------------------------------------------------------------ parts

def _legs(hide: set, accent: dict, ctx, fx, fy, fz, f, s, p):
    """Four legs, each finding its OWN ground - the isle rolls, and a level hoof line either floats
    on the high side or buries its feet on the low.

    Lofted, so a leg swells at the haunch and narrows at the ankle instead of being a 3x3 post."""
    bl, br, lr = int(p["body_len"]), float(p["body_r"]), float(p["leg_r"])
    n = float(p["section_n"])
    top = fy + int(p["leg"])
    # (t up the leg, half-width) - thick where it meets the body, thin at the ankle, flared at the hoof
    KEYS = [(0.00, lr + 0.6), (0.10, lr + 0.1), (0.45, lr - 0.2), (0.72, lr + 0.05), (1.00, lr + 0.15)]
    for along, side in ((bl // 2 - 3, 1), (bl // 2 - 3, -1), (-(bl // 2 - 3), 1), (-(bl // 2 - 3), -1)):
        lx = fx + f[0] * along + s[0] * round(br - 1.4) * side
        lz = fz + f[1] * along + s[1] * round(br - 1.4) * side
        hoof = fy
        if ctx is not None:
            for probe in range(fy + 6, fy - 8, -1):
                if ctx.name_at(lx, probe, lz) not in AIRY:
                    hoof = probe + 1
                    break
        span = max(1, top - hoof)
        for y in range(hoof, top + 1):
            t = 1.0 - (y - hoof) / span                  # 1 at the hoof, 0 at the top
            (r,) = _lerp(KEYS, t)
            here: set = set()
            _disc(here, lx, y, lz, f, s, r, r, n)
            hide |= here
            if y < hoof + int(p["hoof"]):
                for c in here:
                    accent[c] = p["hoof_block"]


def _body(hide: set, fx, belly, fz, f, s, p) -> tuple:
    """A barrel whose back falls away from the withers. Returns where the neck rises from.

    The back line and the belly line are set independently: the back drops steeply, the belly stays
    near level, so the body deepens toward the chest the way an animal does."""
    bl, br = int(p["body_len"]), float(p["body_r"])
    withers, hips = float(p["withers"]), float(p["hips"])
    n = float(p["section_n"])
    half = bl // 2
    # t: 0 at the rump, 1 at the chest. (half-width, back height above belly)
    KEYS = [(0.00, br - 1.6, hips - 1.0), (0.12, br - 0.5, hips),
            (0.45, br, hips + (withers - hips) * 0.45),
            (0.78, br, withers), (0.92, br - 0.3, withers), (1.00, br - 1.3, withers - 1.0)]
    for a in range(-half, bl - half):
        t = (a + half) / max(1, bl - 1)
        rb, back = _lerp(KEYS, t)
        mid = belly + back / 2.0                          # section centre between belly and back
        _rib(hide, fx + f[0] * a, mid, fz + f[1] * a, f, s, rb, back / 2.0, n, squash_lo=1.12)
    return (fx + f[0] * (half - 2), belly + withers - 1.0, fz + f[1] * (half - 2))


def _neck(hide: set, shoulder, f, s, p):
    """A long neck that tapers smoothly and leans forward, with a mane ridge down its back edge.

    The lean is carried as a FLOAT and the section is re-centred every course, so the neck is a clean
    diagonal instead of the staircase a whole-box step produces."""
    sx, sy, sz = shoulder
    ln, r0, r1 = int(p["neck"]), float(p["neck_r0"]), float(p["neck_r1"])
    n, lean = float(p["section_n"]), float(p["neck_lean"])
    # a real neck is not a cone: it flares into the shoulders, then tapers evenly to the jaw
    KEYS = [(0.00, r0 + 1.3), (0.10, r0), (0.45, r0 - (r0 - r1) * 0.45), (1.00, r1)]
    x = float(sx)
    z = float(sz)
    top = (sx, sy, sz)
    for k in range(ln):
        t = k / max(1, ln - 1)
        (r,) = _lerp(KEYS, t)
        x += f[0] * lean
        z += f[1] * lean
        y = sy + k
        _disc(hide, x, y, z, f, s, r, r * 0.92, n)
        # mane: one course proud of the back edge, so the neck has an edge instead of being a tube
        if k < ln - 1:
            hide.add((int(round(x - f[0] * (r + 0.9))), int(round(y)),
                      int(round(z - f[1] * (r + 0.9)))))
        top = (x, y, z)
    return top, _lerp(KEYS, 1.0)[0]


def _head(hide: set, accent: dict, top, neck_r, f, s, p):
    """The face, lofted along the muzzle rather than assembled from boxes.

    Six keyframes carry it from the back of the skull to the nose: the cranium is tall and wide, the
    brow holds the widest point (that is where the eyes sit), the cheek narrows, and the muzzle drops
    and slims to a blunt nose. The vertical centre falls along the way, which is what gives a giraffe
    its long down-tilted face instead of a box stuck on a pole.

    It starts one course BELOW the neck top and at the neck's own radius, so the join is continuous -
    v4 stepped from 9 cells to 34 in one course and read as a pinhead.
    """
    hx, hy, hz = top
    hl, hr, n = int(p["head_len"]), float(p["head_r"]), float(p["section_n"])
    # (t, half-width, vertical centre offset, half-height)
    # A giraffe's muzzle stays DEEP - it is a blunt snout, not a beak. v5 dropped the half-height from
    # hr-0.1 at the cranium to hr-1.5 at the nose, so the face tapered to a point two blocks tall on a
    # five block skull, and the head read as a lump with a spike on it.
    KEYS = [(0.00, max(neck_r, hr - 1.2), 0.4, hr - 0.3),      # continuous with the neck
            (0.20, hr, 0.5, hr + 0.15),                         # cranium
            (0.42, hr - 0.05, 0.1, hr - 0.1),                   # brow / eye line - widest of the face
            (0.65, hr - 0.5, -0.5, hr - 0.45),                  # cheek and jaw
            (0.88, hr - 0.85, -1.0, hr - 0.7),                  # muzzle - still a substantial mass
            (1.00, hr - 0.95, -1.25, hr - 0.8)]                 # blunt nose
    ax = az = 0
    for i in range(hl):
        t = i / max(1, hl - 1)
        rb, dy, rv = _lerp(KEYS, t)
        cx = hx + f[0] * i
        cz = hz + f[1] * i
        _rib(hide, cx, hy + dy, cz, f, s, rb, rv, n, squash_lo=0.92)
        if abs(t - 0.40) < 0.5 / hl:
            ax, az = cx, cz                                     # remember the brow for the eyes
    _face(hide, accent, hx, hy, hz, ax, az, hl, hr, f, s, p)


def _face(hide: set, accent: dict, hx, hy, hz, ax, az, hl, hr, f, s, p):
    """Eyes, nostrils, pale muzzle, ears and ossicones - the things you actually read a face by."""
    nose_x = int(round(hx + f[0] * (hl - 1)))
    nose_z = int(round(hz + f[1] * (hl - 1)))
    # pale muzzle: giraffes have one, and it is what separates the nose from the coat at a distance.
    # The whole front of the face, not just the underside - a band across the top of the snout too.
    for c in list(hide):
        along = (c[0] - hx) * f[0] + (c[2] - hz) * f[1]
        if along >= hl - 3:
            accent[c] = p["muzzle"]
    for b in (-1, 0, 1):
        for dy in (-1, 0):
            c = (int(nose_x + s[0] * b), int(round(hy + dy - 1)), int(nose_z + s[1] * b))
            if c in hide and abs(b) + abs(dy) < 2:
                accent[c] = p["dark"]                           # nostrils and lip line
    for side in (1, -1):
        # eye: a two-tall dark bead ringed in pale, on the SIDE of the brow where a giraffe's sits.
        # One dark block on a head this size disappears from any distance you would view it at.
        for b in range(int(hr - 1), int(hr + 2)):
            for k in (0, 1):
                c = (int(ax + s[0] * b * side), int(round(hy + k)), int(az + s[1] * b * side))
                if c in hide:
                    accent[c] = p["dark"]
            for k in (-1, 2):                                   # the pale ring above and below
                c = (int(ax + s[0] * b * side), int(round(hy + k)), int(az + s[1] * b * side))
                if c in hide:
                    accent[c] = p["muzzle"]
        # ear: a plate two courses tall, swept BACK and slightly down as it goes out. One course
        # tall it reads as an antenna; a giraffe's ear is a broad leaf shape held out and back.
        for b in range(1, 4):
            for a in (-1, 0, 1):
                for dyk in (0, 1):
                    if b >= 2 and dyk and a == 1:
                        continue                        # taper the outer tip
                    c = (int(round(hx + f[0] * (a + 1 - b * 0.5) + s[0] * (hr - 0.4 + b) * side)),
                         int(round(hy + 1 + dyk - b * 0.25)),
                         int(round(hz + f[1] * (a + 1 - b * 0.5) + s[1] * (hr - 0.4 + b) * side)))
                    hide.add(c)
                    accent[c] = p["coat_block"]
        # ossicone: a stalk with a dark knob, set just inboard of the ears
        ox = int(round(hx + f[0] * 2 + s[0] * 1.2 * side))
        oz = int(round(hz + f[1] * 2 + s[1] * 1.2 * side))
        for k in range(int(hr) + 1, int(hr) + 3):
            hide.add((ox, int(round(hy + k)), oz))
            accent[(ox, int(round(hy + k)), oz)] = p["coat_block"]
        knob = (ox, int(round(hy + hr + 3)), oz)
        hide.add(knob)
        accent[knob] = p["dark"]


def _tail(hide: set, accent: dict, fx, belly, fz, f, s, p):
    """Hangs clear of the rump - inside the silhouette it reads as nothing at all."""
    half = int(p["body_len"]) // 2
    x = int(fx - f[0] * (half + 1))
    z = int(fz - f[1] * (half + 1))
    top = int(belly + int(p["hips"]) - 2)
    for k in range(11):
        hide.add((x, top - k, z))
        if k >= 8:
            accent[(x, top - k, z)] = p["dark"]                 # the tuft
