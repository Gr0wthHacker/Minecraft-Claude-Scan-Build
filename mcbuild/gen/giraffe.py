"""A giraffe, built the way Minecraft builds read: rectangular masses, not ellipsoids.

    giraffe: boxes. A boxy skull with a squared muzzle, flat ear plates, a big black eye, a thick
             column neck, a slab body and four square legs with dark hooves.

Modelled on the reference build Jack supplied. Three things it taught, all of which the earlier
ellipsoid version got wrong:

1. It is BOXY. Rounded blobs read as a lumpy toy at this scale; crisp rectangular masses with stepped
   shoulders read as a giraffe. Everything here is a box, and the heading is snapped to a cardinal
   direction so the boxes stay axis-aligned - which is what makes a Minecraft build look built.
2. The coat is muted clay, not bright wool: terracotta patches on bone block, not orange wool on white.
3. The head is LARGE and the features are big enough to see - a 2-tall black eye, ear plates that
   stick right out, a squared-off muzzle. Subtle detail vanishes on a statue this size.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .vertical import Ctx, World

GIRAFFE = {
    "under": None,
    "feet": None,              # world (x, y, z) the hooves stand on
    "look_at": None,           # world (x, y, z) it faces; snapped to the nearest cardinal
    "leg": 20,                 # hoof to belly
    "hoof": 3,
    "body": [13, 9, 9],        # length, depth, width
    "neck": 16,
    "neck_w": 5,
    "head": [7, 5, 6],         # length, depth, width
    "coat": "bone_block",
    "patch": "terracotta",
    "hoof_block": "dark_oak_log",
    "dark": "black_wool",
    "patch_scale": 5,
    "patch_rate": 0.47,
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air", "vine")
# (forward dx, dz) -> (sideways dx, dz)
CARDINALS = {(1, 0): (0, 1), (-1, 0): (0, -1), (0, 1): (-1, 0), (0, -1): (1, 0)}


def build_giraffe(cfg: dict, donors=None) -> Canvas:
    p = {**GIRAFFE, **cfg}
    for k in ("feet", "look_at"):
        if p.get(k) is None:
            raise ValueError(f"giraffe needs params.{k}")
    ctx = Ctx(p["under"]) if p.get("under") else None
    fx, fy, fz = (int(v) for v in p["feet"])
    tx, _ty, tz = (int(v) for v in p["look_at"])
    seed = int(p["seed"])

    # Snap to a cardinal. A statue built on the diagonal is all stair-stepping and reads as noise;
    # every good Minecraft animal is built square to the grid.
    dx, dz = tx - fx, tz - fz
    f = (1 if dx > 0 else -1, 0) if abs(dx) >= abs(dz) else (0, 1 if dz > 0 else -1)
    s = CARDINALS[f]

    leg, hoofh = int(p["leg"]), int(p["hoof"])
    bl, bd, bw = (int(v) for v in p["body"])
    neck, nw = int(p["neck"]), int(p["neck_w"])
    hl, hd, hw = (int(v) for v in p["head"])

    w = World()
    belly = fy + leg
    _legs(w, ctx, fx, fy, fz, f, s, leg, hoofh, bl, bw, p, seed)
    _body(w, fx, belly, fz, f, s, bl, bd, bw, p, seed)
    # neck rises from the front of the body and steps forward as it climbs
    nx = fx + f[0] * (bl // 2 - 1)
    nz = fz + f[1] * (bl // 2 - 1)
    top = _neck(w, nx, belly + bd, nz, f, s, neck, nw, p, seed)
    _head(w, top, f, s, hl, hd, hw, p, seed)
    # one block clear of the rump, or it hides inside the body silhouette and reads as nothing
    _tail(w, fx - f[0] * (bl // 2 + 1), belly + bd - 1, fz - f[1] * (bl // 2 + 1), p)

    hi = max(y for (_x, y, _z) in w.cells)
    hits = 0 if ctx is None else sum(1 for c in w.cells if ctx.name_at(*c) not in AIRY)
    return w.canvas({"kind": "giraffe", "feet": [fx, fy, fz], "facing": list(f),
                     "height": hi - fy, "top_y": hi, "collisions": hits})


# ------------------------------------------------------------------ primitives

def _coat(p, x, y, z, seed) -> str:
    """Big clay blotches on bone. Coarse value noise so patches are polygons, not speckle."""
    sc = max(1, int(p["patch_scale"]))
    n = sum(hash01(x // sc + a, y // sc + b, z // sc + c, 7, seed)
            for a in (0, 1) for b in (0, 1) for c in (0, 1)) / 8.0
    return p["patch"] if n > p["patch_rate"] else p["coat"]


def _box(w: World, cx, cy, cz, f, s, length, height, width, p, seed, name=None, y0=None):
    """A rectangular mass, `length` along the heading and `width` across it."""
    for a in range(-(length // 2), length - length // 2):
        for k in range(height):
            for b in range(-(width // 2), width - width // 2):
                x = int(round(cx + f[0] * a + s[0] * b))
                z = int(round(cz + f[1] * a + s[1] * b))
                y = int(round((y0 if y0 is not None else cy) + k))
                w.put(x, y, z, name or _coat(p, x, y, z, seed))


# ------------------------------------------------------------------ parts

def _legs(w: World, ctx, fx, fy, fz, f, s, leg, hoofh, bl, bw, p, seed):
    """Four square legs. Each meets the ground under IT - the isle rolls, and a level hoof line
    either floats on the high side or buries its feet on the low."""
    for along, side in ((bl // 2 - 2, 1), (bl // 2 - 2, -1), (-(bl // 2 - 2), 1), (-(bl // 2 - 2), -1)):
        lx = fx + f[0] * along + s[0] * (bw // 2 - 1) * side
        lz = fz + f[1] * along + s[1] * (bw // 2 - 1) * side
        hoof = fy
        if ctx is not None:
            for probe in range(fy + 6, fy - 8, -1):
                if ctx.name_at(lx, probe, lz) not in AIRY:
                    hoof = probe + 1
                    break
        top = fy + leg
        for y in range(hoof, top + 1):
            name = p["hoof_block"] if y < hoof + hoofh else None
            _box(w, lx, y, lz, f, s, 3, 1, 3, p, seed, name=name)


def _body(w: World, fx, belly, fz, f, s, bl, bd, bw, p, seed):
    """A slab body with a stepped shoulder: the front two courses sit a block higher and wider."""
    for k in range(bd):
        # taper the belly and the top so it is not a plain brick
        inset = 1 if k == 0 or k == bd - 1 else 0
        _box(w, fx, belly + k, fz, f, s, bl - 2 * inset, 1, bw - 2 * inset, p, seed)
    # shoulder hump over the front third
    hump_x = fx + f[0] * (bl // 4)
    hump_z = fz + f[1] * (bl // 4)
    _box(w, hump_x, belly + bd, hump_z, f, s, bl // 2, 2, bw - 2, p, seed)


def _neck(w: World, nx, ny, nz, f, s, neck, nw, p, seed):
    """A thick column that steps forward as it rises. Returns the top, where the head sits."""
    x, z = nx, nz
    for k in range(neck):
        if k and k % 5 == 0:                          # step forward every five courses
            x += f[0]
            z += f[1]
        width = nw if k < neck * 0.6 else nw - 1      # slims toward the jaw
        _box(w, x, ny + k, z, f, s, width, 1, width, p, seed)
    return (x, ny + neck, z)


def _head(w: World, top, f, s, hl, hd, hw, p, seed):
    """A boxy skull with a squared muzzle, ear plates that stick right out, and a 2-tall black eye.

    Everything here is deliberately oversized. On a 50 block statue a one-block eye disappears."""
    hx, hy, hz = top
    # skull
    _box(w, hx, hy, hz, f, s, hl - 2, hd, hw, p, seed)
    # muzzle, forward and a course lower
    mx = hx + f[0] * (hl // 2)
    mz = hz + f[1] * (hl // 2)
    _box(w, mx, hy, mz, f, s, 4, hd - 2, hw - 2, p, seed)
    # nose tip
    _box(w, mx + f[0] * 2, hy, mz + f[1] * 2, f, s, 1, 2, hw - 3, p, seed, name=p["dark"])
    for side in (1, -1):
        # eye: two blocks tall on the side of the skull, set forward
        ex = hx + f[0] * 1 + s[0] * (hw // 2) * side
        ez = hz + f[1] * 1 + s[1] * (hw // 2) * side
        for k in (1, 2):
            w.put(ex, hy + k, ez, p["dark"])
        # ear: a flat plate straight out the side
        for b in range(1, 4):
            for a in (-1, 0):
                w.put(hx + f[0] * a + s[0] * (hw // 2 + b) * side, hy + hd - 2,
                      hz + f[1] * a + s[1] * (hw // 2 + b) * side,
                      _coat(p, hx + a, hy, hz + b, seed))
        # ossicone: a two-block stalk with a dark knob
        ox = hx + s[0] * 1 * side
        oz = hz + s[1] * 1 * side
        for k in (0, 1):
            w.put(ox, hy + hd + k, oz, p["coat"])
        w.put(ox, hy + hd + 2, oz, p["dark"])


def _tail(w: World, x, y, z, p):
    """Hangs clear of the rump: two blocks thick at the root, a dark tuft on the end."""
    for k in range(10):
        w.put(x, y - k, z, p["coat"] if k < 7 else p["dark"])
        if k < 3:                                     # thicker where it leaves the body
            w.put(x, y - k + 1, z, p["coat"]) if not w.has(x, y - k + 1, z) else None
