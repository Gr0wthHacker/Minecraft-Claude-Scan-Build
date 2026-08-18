"""A giraffe. Shape first, then the coat is painted on - the two are separate problems.

    giraffe: long tapered neck, a body that slopes hard from withers to hips, long legs, a boxy skull
             with a big eye and flared ears - dressed in a Voronoi coat (`coat.voronoi`) so the
             patches are polygons with pale channels between them.

Three earlier versions of this failed, each for a different reason, and all three lessons are load
bearing:

1. ELLIPSOIDS look melted. Build rectangular masses and snap the heading to a cardinal so they stay
   square to the grid. A Minecraft statue reads as built or it reads as a blob.
2. PROPORTION is what names the animal, not detail. Version 3 had a 19-block neck on an 18-block body
   with a level back - and that is an alpaca, whatever colour you paint it. The neck must be longer
   than the body, the legs must be about as long as the neck, and the back must fall away steeply
   from the shoulder. Get those three right and the silhouette says giraffe before any colour does.
3. The COAT is a Voronoi diagram, not noise. Hard-edged patches with cream grout between them. Value
   noise makes amorphous clouds that merge into each other and read as a cow. See `coat.py`.
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
    "leg_w": 3,
    "body_len": 14,             # SHORTER than the neck
    "withers": 10,              # body depth at the shoulder
    "hips": 6,                  # body depth at the rump - the drop between these is the back slope
    "body_w": 9,
    "neck": 19,                 # LONGER than the body
    "neck_w0": 5,               # at the shoulder
    "neck_w1": 3,               # at the jaw
    "neck_lean": 0.42,          # blocks forward per block up
    "head_len": 8,
    "head_h": 5,
    "head_w": 5,
    # -- palette, chosen from all 1193 real block colours (see `mcbuild.blocks.nearest`)
    "coat_block": "smooth_sandstone",        # pale straw
    "patch": "smooth_red_sandstone",         # ochre
    "patch_alt": "cut_red_sandstone",        # same colour, different texture: variety without noise
    "hoof_block": "dark_oak_wood",
    "dark": "black_wool",
    "patch_scale": 5.5,         # average patch width
    "grout": 0.55,              # width of the pale channel between patches
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

    # ---- 1. the shape, as a set of cells. No colour decided yet.
    hide: set = set()
    accent: dict = {}                                   # cells whose colour is NOT the coat
    belly = fy + int(p["leg"])
    _legs(hide, accent, ctx, fx, fy, fz, f, s, p)
    top_front = _body(hide, fx, belly, fz, f, s, p)
    neck_top = _neck(hide, top_front, f, s, p)
    _head(hide, accent, neck_top, f, s, p)
    _tail(hide, accent, fx, belly, fz, f, s, p)

    # ---- 2. the coat, painted over the shape
    skin = coat.voronoi(hide, p["patch"], p["coat_block"], scale=float(p["patch_scale"]),
                        grout_width=float(p["grout"]), seed=int(p["seed"]),
                        tones=[p["patch"], p["patch_alt"]])
    w = World()
    for cell in sorted(hide):
        w.put(*cell, accent.get(cell) or skin.get(cell, p["coat_block"]))

    hi = max(y for (_x, y, _z) in hide)
    hits = 0 if ctx is None else sum(1 for c in hide if ctx.name_at(*c) not in AIRY)
    return w.canvas({"kind": "giraffe", "feet": [fx, fy, fz], "facing": list(f),
                     "height": hi - fy, "top_y": hi, "neck_top_y": neck_top[1],
                     "collisions": hits})


# ------------------------------------------------------------------ primitives

def _box(hide: set, cx, cy, cz, f, s, length, height, width, y0=None):
    """A rectangular mass: `length` along the heading, `width` across it."""
    y0 = cy if y0 is None else y0
    for a in range(-(length // 2), length - length // 2):
        for b in range(-(width // 2), width - width // 2):
            x = int(cx + f[0] * a + s[0] * b)
            z = int(cz + f[1] * a + s[1] * b)
            for k in range(height):
                hide.add((x, int(y0) + k, z))


# ------------------------------------------------------------------ parts

def _legs(hide: set, accent: dict, ctx, fx, fy, fz, f, s, p):
    """Four long legs. Each finds its OWN ground - the isle rolls, and a level hoof line either
    floats on the high side or buries its feet on the low."""
    bl, bw, lw = int(p["body_len"]), int(p["body_w"]), int(p["leg_w"])
    top = fy + int(p["leg"])
    for along, side in ((bl // 2 - 2, 1), (bl // 2 - 2, -1),
                        (-(bl // 2 - 2), 1), (-(bl // 2 - 2), -1)):
        lx = fx + f[0] * along + s[0] * (bw // 2 - 1) * side
        lz = fz + f[1] * along + s[1] * (bw // 2 - 1) * side
        hoof = fy
        if ctx is not None:
            for probe in range(fy + 6, fy - 8, -1):
                if ctx.name_at(lx, probe, lz) not in AIRY:
                    hoof = probe + 1
                    break
        for y in range(hoof, top + 1):
            here: set = set()
            _box(here, lx, y, lz, f, s, lw, 1, lw)
            hide |= here
            if y < hoof + int(p["hoof"]):
                for c in here:
                    accent[c] = p["hoof_block"]


def _body(hide: set, fx, belly, fz, f, s, p) -> tuple:
    """A body that FALLS AWAY from the shoulder. The steep withers-to-hips slope is the giraffe's
    profile; a level back is what made version 3 an alpaca.

    Returns the world point the neck rises from."""
    bl, bw = int(p["body_len"]), int(p["body_w"])
    withers, hips = int(p["withers"]), int(p["hips"])
    half = bl // 2
    for a in range(-half, bl - half):
        t = (a + half) / max(1, bl - 1)                  # 0 at the rump, 1 at the chest
        depth = round(hips + (withers - hips) * (t ** 0.85))
        width = bw - (2 if t < 0.25 else 0)              # narrows toward the rump
        cx, cz = fx + f[0] * a, fz + f[1] * a
        for b in range(-(width // 2), width - width // 2):
            x, z = int(cx + s[0] * b), int(cz + s[1] * b)
            for k in range(depth):
                hide.add((x, belly + k, z))
    # chest: the mass in front of the forelegs that the neck grows out of
    _box(hide, fx + f[0] * (half - 1), belly, fz + f[1] * (half - 1), f, s, 3, withers + 1, bw - 2)
    return (fx + f[0] * (half - 2), belly + withers, fz + f[1] * (half - 2))


def _neck(hide: set, top_front, f, s, p) -> tuple:
    """A long neck that tapers and leans forward, with a mane ridge along its back edge."""
    x, by, z = top_front
    n, w0, w1 = int(p["neck"]), int(p["neck_w0"]), int(p["neck_w1"])
    lean = float(p["neck_lean"])
    carried = 0.0
    for k in range(n):
        t = k / max(1, n - 1)
        width = max(w1, round(w0 + (w1 - w0) * t))
        carried += lean
        while carried >= 1.0:                            # step forward, keeping the boxes square
            x += f[0]
            z += f[1]
            carried -= 1.0
        _box(hide, x, by + k, z, f, s, width, 1, width)
        # mane: one course proud of the back edge, so the neck has an edge instead of being a tube
        if k < n - 1:
            hide.add((int(x - f[0] * (width // 2 + 1)), by + k, int(z - f[1] * (width // 2 + 1))))
    return (x, by + n, z)


def _head(hide: set, accent: dict, top, f, s, p):
    """A boxy skull: cranium, tapering muzzle, ears straight out the sides, ossicones, and an eye big
    enough to see. At this size a one-block eye is invisible - it gets two."""
    hx, hy, hz = top
    hl, hh, hw = int(p["head_len"]), int(p["head_h"]), int(p["head_w"])
    _box(hide, hx, hy, hz, f, s, hl - 3, hh, hw)
    # muzzle: forward and narrower
    mx, mz = hx + f[0] * (hl // 2 - 1), hz + f[1] * (hl // 2 - 1)
    _box(hide, mx, hy, mz, f, s, 4, hh - 2, hw - 2)
    # nose
    nx, nz = mx + f[0] * 2, mz + f[1] * 2
    _box(hide, nx, hy, nz, f, s, 1, 2, hw - 2)
    for b in (-1, 0, 1):
        c = (int(nx + s[0] * b), hy, int(nz + s[1] * b))
        if c in hide:
            accent[c] = p["dark"]                        # nostrils and lip
    for side in (1, -1):
        # eye: two tall, on the SIDE of the skull where a giraffe's actually sits
        ex = int(hx + f[0] + s[0] * (hw // 2) * side)
        ez = int(hz + f[1] + s[1] * (hw // 2) * side)
        for k in (2, 3):
            hide.add((ex, hy + k, ez))
            accent[(ex, hy + k, ez)] = p["dark"]
        # ear: a flat plate straight out the side
        for b in range(1, 4):
            for a in (-1, 0):
                hide.add((int(hx + f[0] * a + s[0] * (hw // 2 + b) * side), hy + hh - 2,
                          int(hz + f[1] * a + s[1] * (hw // 2 + b) * side)))
        # ossicone: a stalk with a dark knob
        ox, oz = int(hx + s[0] * side), int(hz + s[1] * side)
        for k in (0, 1):
            hide.add((ox, hy + hh + k, oz))
            accent[(ox, hy + hh + k, oz)] = p["coat_block"]
        hide.add((ox, hy + hh + 2, oz))
        accent[(ox, hy + hh + 2, oz)] = p["dark"]


def _tail(hide: set, accent: dict, fx, belly, fz, f, s, p):
    """Hangs clear of the rump - inside the silhouette it reads as nothing at all."""
    half = int(p["body_len"]) // 2
    x = int(fx - f[0] * (half + 1))
    z = int(fz - f[1] * (half + 1))
    top = belly + int(p["hips"]) - 1
    for k in range(11):
        hide.add((x, top - k, z))
        if k >= 8:
            accent[(x, top - k, z)] = p["dark"]          # the tuft
