"""A giraffe standing in the void, craning its head up toward a floating platform.

    giraffe: proper anatomy - deep chest, shoulder hump, sloping back, thick tapering neck, and a head
             modelled in parts (cranium, muzzle, jaw, eyes, ears, ossicones) rather than one lump.

Built in WORLD coordinates so it gets a paste origin and `/cscan place` works. The neck aims at a
COORDINATE, so the head arrives beside whatever you told it to look at, and the height needed falls
out of `feet` and `look_at`.

On mass: the island's own owl and fox fill 23-32% of their bounding box. The first version of this
filled 7% and read as a wireframe - stick legs, a two-wide neck tube, a head you could not find. A
statue this tall needs limbs and a skull in proportion, so nothing here is thinner than three blocks.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World

GIRAFFE = {
    "under": None,             # capture, so the statue can be checked for collisions
    "feet": None,              # world (x, y, z) the hooves stand on
    "look_at": None,           # world (x, y, z) the head reaches toward
    "leg": 22,                 # hoof to belly
    "body": [18, 10, 9],       # length, depth, width
    "neck": 19,                # shoulder to jaw
    "coat": "white_wool",
    "patch": "orange_wool",
    "dark": "black_wool",
    "muzzle": "light_gray_wool",
    "eye": "black_wool",
    "patch_scale": 6,          # lattice size: giraffe patches are 5-6 blocks across, not speckle
    "patch_rate": 0.50,
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air", "vine")


def build_giraffe(cfg: dict, donors=None) -> Canvas:
    p = {**GIRAFFE, **cfg}
    for k in ("feet", "look_at"):
        if p.get(k) is None:
            raise ValueError(f"giraffe needs params.{k}")
    ctx = Ctx(p["under"]) if p.get("under") else None
    fx, fy, fz = (int(v) for v in p["feet"])
    tx, _ty, tz = (int(v) for v in p["look_at"])
    seed = int(p["seed"])
    leg, neck = int(p["leg"]), int(p["neck"])
    bl, bd, bw = (int(v) for v in p["body"])

    dx, dz = tx - fx, tz - fz
    mag = max(1e-6, math.hypot(dx, dz))
    u = (dx / mag, dz / mag)                          # heading
    q = (-u[1], u[0])                                 # sideways

    w = World()
    belly = fy + leg
    _legs(w, ctx, fx, fy, fz, u, q, leg, bl, bw, p, seed)
    _body(w, fx, belly, fz, u, q, bl, bd, bw, p, seed)
    # the shoulder hump is the highest point of the back, and the neck leaves from it
    sx = fx + u[0] * (bl * 0.30)
    sz = fz + u[1] * (bl * 0.30)
    sy = belly + bd * 0.85
    head = _neck(w, (sx, sy, sz), u, q, neck, p, seed)
    _head(w, head, u, q, p, seed)
    _tail(w, fx - u[0] * (bl * 0.46), belly + bd * 0.55, fz - u[1] * (bl * 0.46), p)

    top = max(y for (_x, y, _z) in w.cells)
    xs = [c[0] for c in w.cells]
    ys = [c[1] for c in w.cells]
    zs = [c[2] for c in w.cells]
    vol = (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1) * (max(zs) - min(zs) + 1)
    hits = 0 if ctx is None else sum(1 for c in w.cells if ctx.name_at(*c) not in AIRY)
    return w.canvas({"kind": "giraffe", "feet": [fx, fy, fz], "look_at": [tx, _ty, tz],
                     "head": [int(head[0]), int(head[1]), int(head[2])],
                     "height": top - fy, "top_y": top, "collisions": hits,
                     "density": round(len(w.cells) / vol, 3)})


# ------------------------------------------------------------------ surface

def _coat(w: World, x, y, z, p, seed):
    """Cream with big orange blotches. Coarse value noise: patches are polygons, not static."""
    s = max(1, int(p["patch_scale"]))
    n = sum(hash01(x // s + a, y // s + b, z // s + c, 7, seed)
            for a in (0, 1) for b in (0, 1) for c in (0, 1)) / 8.0
    w.put(x, y, z, p["patch"] if n > p["patch_rate"] else p["coat"])


def _blob(w: World, cx, cy, cz, rx, ry, rz, p, seed, name=None):
    for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for z in range(int(cz - rz) - 1, int(cz + rz) + 2):
                d = ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 + ((z + .5 - cz) / rz) ** 2
                if d > 1.0:
                    continue
                if name:
                    w.put(x, y, z, name)
                else:
                    _coat(w, x, y, z, p, seed)


# ------------------------------------------------------------------ parts

def _legs(w: World, ctx, fx, fy, fz, u, q, leg, bl, bw, p, seed):
    """Three-wide legs with a knee swell and a black hoof. Each finds the ground under IT: the isle
    rolls, and a level hoof line either floats on the high side or buries its feet on the low."""
    for along, side in ((0.30, 1), (0.30, -1), (-0.32, 1), (-0.32, -1)):
        lx = fx + u[0] * (bl * along) + q[0] * (bw * 0.32 * side)
        lz = fz + u[1] * (bl * along) + q[1] * (bw * 0.32 * side)
        hoof = fy
        if ctx is not None:
            for probe in range(fy + 6, fy - 8, -1):
                if ctx.name_at(int(round(lx)), probe, int(round(lz))) not in AIRY:
                    hoof = probe + 1
                    break
        top = fy + leg
        span = max(1, top - hoof)
        for k in range(span + 1):
            t = k / float(span)
            r = 1.6 + 0.9 * t ** 1.4                   # slim at the hoof, heavy into the body
            if 0.42 < t < 0.58:
                r += 0.5                                # knee
            _blob(w, lx, hoof + k, lz, r, 0.6, r, p, seed,
                  name=p["dark"] if k <= 1 else None)


def _body(w: World, fx, belly, fz, u, q, bl, bd, bw, p, seed):
    """Deep chest at the front, a shoulder hump, and a back that slopes away to lower hips."""
    for t in range(-bl // 2, bl // 2 + 1):
        f = t / (bl / 2.0)                             # -1 rump .. +1 chest
        cx = fx + u[0] * t
        cz = fz + u[1] * t
        depth = bd * (0.52 + 0.20 * f)                 # chest deeper than rump
        width = bw * (0.50 + 0.06 * f)
        rise = 2.2 * f + (1.6 if 0.15 < f < 0.62 else 0.0)   # hump over the shoulders
        taper = 1.0 - 0.30 * max(0.0, abs(f) - 0.55) / 0.45
        _blob(w, cx, belly + depth * 0.5 + rise, cz,
              width * taper, depth * 0.5 * taper, width * taper, p, seed)


def _neck(w: World, shoulder, u, q, neck, p, seed):
    """Thick at the shoulder, tapering to the jaw, leaning the way it looks. Mane along the back."""
    sx, sy, sz = shoulder
    hx = hy = hz = 0.0
    for k in range(neck + 1):
        t = k / float(neck)
        lean = (t ** 1.35) * neck * 0.50
        hx, hy, hz = sx + u[0] * lean, sy + k, sz + u[1] * lean
        r = 3.3 - 1.5 * t                              # 3.3 at the base down to 1.8 at the jaw
        _blob(w, hx, hy, hz, r, 0.75, r, p, seed)
        if k % 2 == 0 and t > 0.12:                    # mane ridge on the back edge
            for s2 in (-0.4, 0.4):
                _blob(w, hx - u[0] * (r + 0.3) + q[0] * s2, hy + 0.4,
                      hz - u[1] * (r + 0.3) + q[1] * s2, 0.7, 0.7, 0.7, p, seed, name=p["dark"])
    return (hx, hy, hz)


def _head(w: World, head, u, q, p, seed):
    """Cranium, tapering muzzle, jaw, eyes on the sides, flared ears and knobbed ossicones.

    Modelled in parts on purpose - one ellipsoid gave a lump you could not find on a 50 block statue.
    """
    hx, hy, hz = head
    f, s = u, q

    def at(a, up, side, r, name=None, ry=None):
        _blob(w, hx + f[0] * a + s[0] * side, hy + up, hz + f[1] * a + s[1] * side,
              r, ry if ry is not None else r, r, p, seed, name=name)

    at(0.0, 1.2, 0, 2.6, ry=2.2)                       # cranium
    at(2.2, 0.7, 0, 2.1, ry=1.7)                       # cheek and jaw
    at(4.2, 0.2, 0, 1.7, ry=1.4, name=p["muzzle"])     # muzzle
    at(5.6, 0.0, 0, 1.3, ry=1.1, name=p["muzzle"])     # nose
    for side in (1, -1):
        at(6.2, 0.2, 0.7 * side, 0.6, name=p["dark"])  # nostril
        # eye: a dark bead in a pale socket, on the SIDE where a giraffe's eyes actually sit
        at(1.4, 1.6, 2.3 * side, 1.0, name=p["muzzle"])
        at(1.7, 1.6, 2.6 * side, 0.7, name=p["eye"])
        for k in range(3):                             # ear, flared out and back
            _blob(w, hx - f[0] * (0.4 + k * 0.7) + s[0] * (2.6 + k * 0.8) * side, hy + 1.9 + k * 0.3,
                  hz - f[1] * (0.4 + k * 0.7) + s[1] * (2.6 + k * 0.8) * side,
                  0.9 - k * 0.15, 0.55, 0.9 - k * 0.15, p, seed)
        # ossicone: a stalk with a dark knob - the thing that says giraffe
        ox = hx + s[0] * 1.1 * side - f[0] * 0.3
        oz = hz + s[1] * 1.1 * side - f[1] * 0.3
        for k in (3, 4):
            _blob(w, ox, hy + k, oz, 0.85, 0.6, 0.85, p, seed)
        _blob(w, ox, hy + 5.2, oz, 1.05, 0.9, 1.05, p, seed, name=p["dark"])
    return (hx, hy, hz)


def _tail(w: World, x, y, z, p):
    for k in range(9):
        r = 1 if k < 6 else 2
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                if dx * dx + dz * dz > r:
                    continue
                w.put(int(round(x)) + dx, int(round(y - k)), int(round(z)) + dz,
                      p["coat"] if k < 6 else p["dark"])
