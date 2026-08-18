"""Hanging sloth — for the underside of an island. Audience is BELOW.

Silhouette first: a hammock body sagging ~6 below a 2x2 spruce branch, four
LONG 2x2 limbs angling up to it, three fence claws per limb hooked over the
branch top, a small round head hung low at the front with a pale face plate
on its underside (black eyes, mask stripes sweeping back, snub nose, smile).
Shaggy back with moss/algae. Log stubs on the TOP layer are attach points
(paste with the top layer touching the underside). Hollowed by the pipeline.

Cheap: brown / light-grey / white / black wool, spruce logs + fences, moss.
"""
from __future__ import annotations

from .canvas import Canvas, hash01

DEFAULTS = {"size": [28, 19, 11], "seed": 0}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    SX, SY, SZ = p["size"]; seed = int(p["seed"])
    c = Canvas(SX, SY, SZ, donors)
    st = c.state
    S = {
        "fur": st("brown_wool"), "fur2": st("light_gray_wool"), "face": st("white_wool"),
        "dark": st("black_wool"), "moss": st("moss_block"),
        "log_x": st("spruce_log", axis="x"), "log_y": st("spruce_log", axis="y"),
        "claw": st("spruce_fence", north="false", south="false", east="false", west="false", waterlogged="false"),
    }
    h = lambda *a: hash01(*a, seed)
    top = SY - 1
    cz = SZ / 2.0
    zc0, zc1 = int(cz) - 1, int(cz)
    # ---- branch + attach stubs
    for x in range(1, SX - 1):
        for y in (top - 2, top - 1):
            for z in (zc0, zc1):
                c.put(x, y, z, S["log_x"])
    for x in (2, 3, SX - 4, SX - 3):
        for z in (zc0, zc1):
            c.put(x, top, z, S["log_y"])
    # ---- hammock body: spheres along a sagging curve, 6 below the branch at the middle
    bx = 12.0
    yb = top - 10.5                                         # lowest point of the body centre line
    curve = [(bx - 6, yb + 1.4, cz), (bx - 3, yb + 0.3, cz), (bx, yb, cz), (bx + 3, yb + 0.3, cz), (bx + 6, yb + 1.2, cz)]
    c.bezier(curve, 2.7, S["fur"], n=40)
    # ---- head: small, round, hung low at the front
    hx, hy = bx + 8.4, yb - 0.2
    c.sphere(hx, hy, cz, 2.8, S["fur"], squash=0.85)
    for y in range(int(hy - 4), int(hy + 4)):               # face plate = underside + front of the head
        for z in range(SZ):
            for x in range(int(hx - 4), SX):
                if c.get(x, y, z) != S["fur"]:
                    continue
                dx, dy = x + 0.5 - hx, y + 0.5 - hy
                if (dy < 0.4 and c.get(x, y - 1, z) == 0) or (dx > 1.8 and dy < 1.2):
                    c.put(x, y, z, S["face"])
                elif dy > 1.2 or dx > 1.0:
                    c.put(x, y, z, S["fur2"])               # pale cap on top/front
    def face_put(x, z, blk):
        for y in range(0, SY):
            if c.get(x, y, z) == S["face"]:
                c.put(x, y, z, blk); return
    ex = int(hx + 1)                                        # eyes forward; mask stripes sweep back and out
    for z, out in ((zc0 - 1, -1), (zc1 + 1, 1)):
        face_put(ex, z, S["dark"])
        face_put(ex - 1, z + out, S["dark"])
        face_put(ex - 2, z + out, S["dark"])
        face_put(ex - 3, z + 2 * out, S["dark"])
    face_put(ex - 1, zc0, S["dark"]); face_put(ex - 1, zc1, S["dark"])              # snub nose
    for z in (zc0 - 1, zc0, zc1, zc1 + 1):                                            # smile: gentle U
        face_put(ex - 3, z, S["dark"])
    face_put(ex - 2, zc0 - 2, S["dark"]); face_put(ex - 2, zc1 + 2, S["dark"])
    # ---- shaggy back: moss + pale tufts on the downward-facing fur
    for y in range(0, top - 3):
        for z in range(SZ):
            for x in range(SX):
                if c.get(x, y, z) == S["fur"] and c.get(x, y - 1, z) == 0:
                    k = h(x, y, z, 11)
                    if k < 0.20:
                        c.put(x, y, z, S["moss"])
                    elif k < 0.30:
                        c.put(x, y, z, S["fur2"])
    # ---- limbs: 2x2, from the body's flanks angling up to the branch; arms (front) longer
    for lx0, grip in ((int(bx - 5), int(bx - 6)), (int(bx + 3), int(bx + 6))):
        for lz, inward in ((zc0 - 2, 1), (zc1 + 2, -1)):
            for y in range(int(yb + 2), top):
                # slide the column from the body toward the grip point as it rises
                t = (y - (yb + 2)) / max(1, (top - 1 - (yb + 2)))
                x = int(round(lx0 + (grip - lx0) * t))
                for dx in (0, 1):
                    for dz in (0, inward):
                        if c.get(x + dx, y, lz + dz) == 0:
                            c.put(x + dx, y, lz + dz, S["fur"])
            for dx in (0, 1):                               # three claws per limb, hooked over the branch top
                for dz in (0, inward, 2 * inward):
                    c.put(grip + dx, top, lz + dz, S["claw"])
    return c
