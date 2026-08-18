"""A giraffe standing in the void, craning its head up toward a floating platform.

    giraffe: legs, a shoulder-high body, a long neck bent toward a target, and a small head with
             ossicones. Built in WORLD coordinates so it gets a paste origin and `/cscan place` works.

The whole point is the neck: it is aimed at a coordinate rather than a compass direction, so the head
arrives beside whatever you told it to look at. Give it `feet` and `look_at`, and the height it needs
falls out of the two.

Coat is value-noise blotches - a lattice sampled coarsely and thresholded - because giraffe patches
are big irregular polygons, and per-block noise gives you static instead.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World

GIRAFFE = {
    "under": None,             # capture, so the statue can be checked for collisions
    "feet": None,              # world (x, y, z) the hooves stand on
    "look_at": None,           # world (x, y, z) the head reaches toward
    "leg": 20,                 # hoof to belly
    "body": [13, 8, 8],        # length, height, width
    "neck": 18,                # shoulder to jaw
    "coat": "white_wool",
    "patch": "orange_wool",
    "dark": "black_wool",
    "muzzle": "light_gray_wool",
    "patch_scale": 3,          # lattice size of the blotches; bigger = larger patches
    "patch_rate": 0.52,
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
    tx, ty, tz = (int(v) for v in p["look_at"])
    seed = int(p["seed"])
    leg, neck = int(p["leg"]), int(p["neck"])
    bl, bh, bw = (int(v) for v in p["body"])

    # unit heading from the feet toward whatever it is looking at
    hx, hz = tx - fx, tz - fz
    mag = max(1e-6, math.hypot(hx, hz))
    ux, uz = hx / mag, hz / mag
    px, pz = -uz, ux                                  # sideways, for the legs and the body's width

    w = World()
    body_y = fy + leg + bh // 2
    _legs(w, ctx, fx, fy, fz, ux, uz, px, pz, leg, bl, bw, p, seed)
    _body(w, fx, body_y, fz, ux, uz, px, pz, bl, bh, bw, p, seed)
    shoulder = (fx + ux * (bl * 0.32), body_y + bh * 0.45, fz + uz * (bl * 0.32))
    head = _neck(w, shoulder, ux, uz, neck, p, seed)
    _head(w, head, ux, uz, px, pz, p, seed)
    _tail(w, fx - ux * (bl * 0.42), body_y + bh * 0.25, fz - uz * (bl * 0.42), p)

    top = max(y for (_x, y, _z) in w.cells)
    hits = 0 if ctx is None else sum(1 for (x, y, z) in w.cells
                                     if ctx.name_at(x, y, z) not in AIRY)
    return w.canvas({"kind": "giraffe", "feet": [fx, fy, fz], "look_at": [tx, ty, tz],
                     "head": [int(head[0]), int(head[1]), int(head[2])],
                     "height": top - fy, "top_y": top, "collisions": hits})


# ------------------------------------------------------------------ parts

def _coat(w: World, x, y, z, p, seed):
    """Cream with big orange blotches - coarse value noise, not per-block static."""
    s = max(1, int(p["patch_scale"]))
    n = sum(hash01(x // s + a, y // s + b, z // s + c, 7, seed)
            for a in (0, 1) for b in (0, 1) for c in (0, 1)) / 8.0
    w.put(x, y, z, p["patch"] if n > p["patch_rate"] else p["coat"])


def _blob(w: World, cx, cy, cz, rx, ry, rz, p, seed, name=None):
    for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for z in range(int(cz - rz) - 1, int(cz + rz) + 2):
                d = ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 + ((z + .5 - cz) / rz) ** 2
                if d <= 1.0:
                    if name:
                        w.put(x, y, z, name)
                    else:
                        _coat(w, x, y, z, p, seed)


def _legs(w: World, ctx, fx, fy, fz, ux, uz, px, pz, leg, bl, bw, p, seed):
    """Four of them, front pair under the shoulders, back pair under the hips. Dark hooves.

    Each leg meets the ground UNDER IT rather than a flat line: the isle's surface rolls, and a statue
    with a level hoof line either floats on the high side or buries its feet on the low side."""
    for along, side in ((0.30, 1), (0.30, -1), (-0.34, 1), (-0.34, -1)):
        lx = fx + ux * (bl * along) + px * (bw * 0.30 * side)
        lz = fz + uz * (bl * along) + pz * (bw * 0.30 * side)
        hoof = fy
        if ctx is not None:
            for probe in range(fy + 6, fy - 8, -1):
                if ctx.name_at(int(round(lx)), probe, int(round(lz))) not in AIRY:
                    hoof = probe + 1
                    break
        top = fy + leg
        for k in range(top - hoof + 1):
            r = 1.7 if k > (top - hoof) * 0.65 else 1.35    # thicker toward the body, like a real leg
            _blob(w, lx, hoof + k, lz, r, 0.6, r, p, seed,
                  name=p["dark"] if k <= 1 else None)


def _body(w: World, fx, by, fz, ux, uz, px, pz, bl, bh, bw, p, seed):
    """A barrel that slopes: a giraffe's shoulders sit well above its hips."""
    for t in range(-bl // 2, bl // 2 + 1):
        f = t / (bl / 2.0)
        cx = fx + ux * t
        cz = fz + uz * t
        rise = 1.6 * f                                 # front end higher
        taper = 1.0 - 0.28 * abs(f) ** 1.6
        _blob(w, cx, by + rise, cz, bw * 0.5 * taper, bh * 0.5 * taper, bw * 0.5 * taper, p, seed)


def _neck(w: World, shoulder, ux, uz, neck, p, seed):
    """A shallow S from the shoulders, leaning the way it is looking. Returns where the head goes."""
    sx, sy, sz = shoulder
    hx = hy = hz = 0.0
    for k in range(neck + 1):
        t = k / float(neck)
        lean = (t ** 1.5) * neck * 0.42                # straight at the base, tipping forward at the top
        hx = sx + ux * lean
        hy = sy + k
        hz = sz + uz * lean
        r = 2.5 - 1.0 * t                              # thick at the shoulder, slim at the jaw
        _blob(w, hx, hy, hz, r, 0.7, r, p, seed)
        if k > neck * 0.25 and k % 2 == 0:             # mane down the back of the neck
            w.put(int(round(hx - ux * (r + 0.4))), int(round(hy)), int(round(hz - uz * (r + 0.4))),
                  p["dark"])
    return (hx, hy, hz)


def _head(w: World, head, ux, uz, px, pz, p, seed):
    """Skull, muzzle, ears and two ossicones - the horns are what make it read as a giraffe."""
    hx, hy, hz = head
    _blob(w, hx, hy + 1.0, hz, 2.0, 1.6, 1.8, p, seed)
    _blob(w, hx + ux * 2.4, hy + 0.4, hz + uz * 2.4, 1.5, 1.1, 1.3, p, seed, name=p["muzzle"])
    w.put(int(round(hx + ux * 3.4)), int(round(hy + 0.4)), int(round(hz + uz * 3.4)), p["dark"])
    for side in (1, -1):
        ex = hx + ux * 1.5 + px * 1.7 * side
        ez = hz + uz * 1.5 + pz * 1.7 * side
        w.put(int(round(ex)), int(round(hy + 1.4)), int(round(ez)), p["dark"])          # eye
        # ear, out and back
        w.put(int(round(hx + px * 2.6 * side)), int(round(hy + 1.8)),
              int(round(hz + pz * 2.6 * side)), p["coat"])
        # ossicone: a stub with a dark knob
        ox = hx + px * 0.9 * side - ux * 0.2
        oz = hz + pz * 0.9 * side - uz * 0.2
        for k in (2, 3):
            w.put(int(round(ox)), int(round(hy + k)), int(round(oz)), p["coat"])
        w.put(int(round(ox)), int(round(hy + 4)), int(round(oz)), p["dark"])


def _tail(w: World, x, y, z, p):
    for k in range(6):
        w.put(int(round(x)), int(round(y - k)), int(round(z)), p["coat"] if k < 4 else p["dark"])
