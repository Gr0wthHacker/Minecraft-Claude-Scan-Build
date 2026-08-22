"""The Sanctum - the building the ring belonged to, standing roofless in the north skylight.

Jack's review of the quarter: "very sparse and vague... too fragmented, we need at least one
more complete actual structure - something that feels real and like it was once impressive."
He is right, and the measured answer is a BASILICA-FORM SANCTUM in the north skylight (blob 1,
105 columns of real sky): the one zone that can hold a real footprint - and only after the
ruinway's apse fragment yields its ground, which is the coherent trade: the fragment becomes
the surviving back wall of the building it was always a fragment of.

The plan, all measured off the blocker map (lanterns on the ground design's 9-grid, the NW oak,
a void hole north of z29965, the flamingo's west margin):

- footprint 11 x ~19, walls at X-24191 and X-24181 - between the lantern columns at X-24192
  and X-24184, so the ground's own lights are DODGED, never covered; the two that fall inside
  the nave stay standing in the ruin floor, which is what a lit ruin looks like.
- the roofless NAVE sits inside the daylight beam. The building's roof is the sky shaft.
- what survives says ONCE IMPRESSIVE the way ruins actually do: the APSE stands to full crest
  (a line, not a peak - the quarter audit's lesson), the FACADE stands whole - grand doorway,
  chiseled frame, an oculus over the lintel, a stepped pediment - and the SIDE WALLS are the
  ruin: high at both ends, collapsed to a course or two in the middle, their tumble lying in
  heaps where they fell. The order survives; the fabric went.
- a chiseled centre aisle runs from the door to a raised altar under the apse, one amethyst
  bloom on it, soul lanterns flanking - the cold light of the quarter, in its holiest room.
- a SPUR of the same ruined pavement leaves the portico steps and joins the way at the
  gatehouse, so the complex is one walk: overlook - ring - gate - sanctum.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .ruinring import _PASSABLE, _free, _surface, _weathered

SANCTUM = {
    "under": None,
    "at": None,                # [x, z] centre of the NAVE (the apse curves north of it)
    "width": 11,               # exterior, across X
    "length": 17,              # apse chord to facade, along Z (facade at the south end)
    "floor_y": None,           # stylobate top; None derives median(ground)+1 and then PIN IT
    "apse_r": 4.5,
    "wall_h": 7,               # the surviving order; side walls collapse below it mid-run
    "facade_h": 8,             # to the pediment springing; the peak rides higher
    "seed": 0,

    "spur_to": None,           # [x, z] on the way; the approach pavement walks there
    "field": "polished_blackstone_bricks",
    "cracked": "cracked_polished_blackstone_bricks",
    "rough": "blackstone",
    "gilded": "gilded_blackstone",
    "chiseled": "chiseled_polished_blackstone",
    "slab": "polished_blackstone_brick_slab",
    "stair": "polished_blackstone_brick_stairs",
    "gild_rate": 0.03,
}


def _put(w, ctx, x, y, z, name, **props):
    if _free(ctx, x, y, z) and not w.has(x, y, z):
        w.put(x, y, z, name, **props)
        return 1
    return 0


def _emit_floor(w, ctx, p, x0, x1, z0, z1, FY, ax, seed) -> int:
    """The stylobate: every column levelled up to one floor plane, the edge course chiseled -
    a building sits ON something, and the platform is half of 'once impressive'. Moss-gapped
    inside (a ruin floor), whole along the chiseled centre aisle."""
    n = 0
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            g, name = _surface(ctx, x, z)
            if g is None or name in ("water", "ice") or g >= FY:
                continue
            edge = x in (x0, x1) or z in (z0, z1)
            aisle = x == ax
            for y in range(g + 1, FY + 1):
                if y == FY and not edge and not aisle and hash01(x, 21, z, seed) < 0.14:
                    continue                           # moss shows through the ruin floor
                mat = p["chiseled"] if (y == FY and (edge or aisle)) \
                    else _weathered(p, hash01(x, y, z, seed))
                n += _put(w, ctx, x, y, z, mat)
    return n


def _emit_apse(w, ctx, p, ax, az_chord, FY, seed) -> int:
    """The surviving back: a half-ring to FULL crest across its back third (a line, not a
    peak - the quarter audit's lesson), buttress ribs outside, a chiseled band course."""
    r = float(p["apse_r"])
    H = int(p["wall_h"]) + 1
    n = 0
    for dx in range(-int(r) - 2, int(r) + 3):
        for dz in range(-int(r) - 2, int(r) + 3):
            if dz > 0:
                continue                               # the apse curves NORTH of the chord
            d = math.hypot(dx, dz)
            ang = math.degrees(math.atan2(-dz, dx)) - 90.0   # 0 = due north = the back
            in_wall = r - 0.5 <= d <= r + 0.5
            in_rib = abs(abs(ang) - 42) < 7 and r + 0.5 < d <= r + 1.5
            if not (in_wall or in_rib):
                continue
            x, z = ax + dx, az_chord + dz
            f = 1.0 - min(1.0, abs(ang) / 90.0)
            h = H if (in_wall and f > 0.55) else max(2, int(round(H * (0.30 + 0.85 * f))))
            if in_rib:
                h = max(2, h - 2)
            for k in range(h):
                y = FY + 1 + k
                band = in_wall and k == 3
                n += _put(w, ctx, x, y, z, p["chiseled"] if band
                          else _weathered(p, hash01(x, y, z, seed)))
    return n


def _emit_side_walls(w, ctx, p, x0, x1, z0, z1, FY, seed) -> int:
    """High at the apse end, high again at the facade, collapsed to a course or two in the
    middle - and the tumble lies in ONE heap per side where it fell, never scatter."""
    H = int(p["wall_h"])
    n = 0
    span = max(1, z1 - z0)
    for x in (x0, x1):
        out = -1 if x == x0 else 1
        for z in range(z0, z1 + 1):
            t = (z - z0) / span
            # a catenary of ruin: ends survive, middle went
            f = 0.55 * (1 - math.cos(2 * math.pi * t)) / 2
            h = max(1, int(round(H * (1.0 - 1.6 * f))))
            pilaster = (z - z0) % 4 == 0 and h >= 3
            for k in range(h):
                y = FY + 1 + k
                n += _put(w, ctx, x, y, z, _weathered(p, hash01(x, y, z, seed)))
            if pilaster:
                n += _put(w, ctx, x + out, FY + 1, z, p["chiseled"])
                for k in range(1, min(h, 3)):
                    n += _put(w, ctx, x + out, FY + 1 + k, z, _weathered(p, hash01(x + out, k, z, seed)))
        mid = (z0 + z1) // 2                           # the heap, half-buried at the wall foot
        for dz in (-1, 0, 1):
            for do in (1, 2):
                x2, z2 = x + out * do, mid + dz
                g2, nm = _surface(ctx, x2, z2)
                if g2 is not None and nm not in ("water", "ice"):
                    if hash01(x2, 31, z2, seed) < 0.75:
                        n += _put(w, ctx, x2, g2 + 1, z2, _weathered(p, hash01(x2, 5, z2, seed)))
    return n


def _emit_facade(w, ctx, p, x0, x1, zf, FY, ax, seed) -> int:
    """The front the building is remembered by, SURVIVING WHOLE: a grand chiseled doorway, an
    oculus over the lintel, a stepped pediment. The ruin is everywhere else; the facade is why
    you believe it was impressive."""
    H = int(p["facade_h"])
    n = 0
    door_x = (ax - 1, ax, ax + 1)
    for x in range(x0, x1 + 1):
        # stepped pediment: rises toward the centre, one course per two cells
        peak = H + max(0, 3 - abs(x - ax) // 2)
        for k in range(peak):
            y = FY + 1 + k
            if x in door_x and k < 5:
                continue                               # the doorway
            if x == ax and k == 6:
                continue                               # the oculus - one round of sky
            jamb = (abs(x - ax) == 2 and k <= 5) or (x in door_x and k == 5)
            ring = abs(x - ax) <= 1 and k in (5, 6, 7) and not (x == ax and k == 6)
            mat = p["chiseled"] if (jamb or ring or k == peak - 1) \
                else _weathered(p, hash01(x, y, zf, seed))
            n += _put(w, ctx, x, y, zf, mat)
    return n


def _emit_interior(w, ctx, p, ax, az_chord, zf, FY, seed) -> dict:
    """Column rows down the nave (ruined to different heights), the altar under the apse with
    its amethyst bloom, and the cold light."""
    feats = {"columns": 0, "altar": 0, "lanterns": 0}
    H = int(p["wall_h"])
    for i, zc in enumerate(range(az_chord + 3, zf - 2, 4)):
        for j, xc in enumerate((ax - 2, ax + 2)):
            h = (H - 1, 3, H - 2, 2, 4, H - 3)[(i * 2 + j) % 6]
            placed = 0
            for k in range(h):
                placed += _put(w, ctx, xc, FY + 1 + k, zc, p["chiseled"] if k == h - 1 and h >= 4
                               else _weathered(p, hash01(xc, k, zc, seed)))
            if placed:
                feats["columns"] += 1
    altar_z = az_chord + 1
    for dx in (0, 1):                                  # a 2x2 chiseled block, two courses
        for dz in (0, 1):
            for k in (1, 2):
                feats["altar"] += _put(w, ctx, ax - 1 + dx, FY + k, altar_z + dz, p["chiseled"])
    if w.has(ax, FY + 2, altar_z):                     # the bloom, on the altar's own top
        feats["altar"] += _put(w, ctx, ax, FY + 3, altar_z, "amethyst_cluster", facing="up")
    for dx in (-3, 3):                                 # the cold light, flanking on the floor
        if w.has(ax + dx, FY, altar_z):
            feats["lanterns"] += _put(w, ctx, ax + dx, FY + 1, altar_z, "soul_lantern",
                                      hanging="false")
    return feats


def _emit_approach(w, ctx, p, ax, zf, FY, spur, seed) -> int:
    """Steps off the stylobate and ruined pavement to the way - the building is ON the walk,
    not beside it. Same rules as the ruinway's own path: slabs, stairs facing the ascent,
    hash gaps, nothing covered."""
    n = 0
    for dx in (-1, 0, 1):                              # the steps south off the platform
        x = ax + dx
        g, nm = _surface(ctx, x, zf + 1)
        if g is not None and nm not in ("water", "ice") and g < FY:
            n += _put(w, ctx, x, g + 1, zf + 1, p["stair"], facing="north", half="bottom")
    if not spur:
        return n
    sx, sz = (int(v) for v in spur)
    px, pz = float(ax), float(zf + 2)
    steps = int(math.hypot(sx - px, sz - pz) * 2)
    for i in range(steps + 1):
        t = i / max(1, steps)
        for u in (-0.5, 0.5):
            dxn, dzn = sz - pz, -(sx - px)             # perpendicular
            dn = math.hypot(dxn, dzn) or 1.0
            x = int(round(px + (sx - px) * t + dxn / dn * u))
            z = int(round(pz + (sz - pz) * t + dzn / dn * u))
            g, nm = _surface(ctx, x, z)
            if g is None or nm in ("water", "ice") or not _free(ctx, x, g + 1, z) or w.has(x, g + 1, z):
                continue
            if hash01(x, 41, z, seed) < 0.16:
                continue                               # ruined, like the way it joins
            w.put(x, g + 1, z, p["slab"], type="bottom")
            n += 1
    return n


def build_sanctum(cfg: dict, donors=None) -> Canvas:
    p = {**SANCTUM, **cfg}
    if not p.get("under") or not p.get("at"):
        raise ValueError("sanctum needs params.under and params.at")
    ctx = Ctx(p["under"])
    seed = int(p["seed"])
    ax, az = (int(v) for v in p["at"])
    W = int(p["width"])
    L = int(p["length"])
    x0, x1 = ax - W // 2, ax + W // 2
    az_chord = az - L // 2                             # the apse springs north of this line
    zf = az + L // 2                                   # the facade line, south
    if p.get("floor_y") is not None:
        FY = int(p["floor_y"])
    else:
        gs = []
        for x in range(x0, x1 + 1):
            for z in range(az_chord, zf + 1):
                g, nm = _surface(ctx, x, z)
                if g is not None and nm not in ("water", "ice"):
                    gs.append(g)
        gs.sort()
        FY = gs[len(gs) // 2] + 1                      # then PIN it in the config, like the ring

    w = World()
    feats = {"floor": _emit_floor(w, ctx, p, x0, x1, az_chord - int(p["apse_r"]) - 1, zf, FY, ax, seed)}
    feats["apse"] = _emit_apse(w, ctx, p, ax, az_chord, FY, seed)
    feats["walls"] = _emit_side_walls(w, ctx, p, x0, x1, az_chord + 1, zf - 1, FY, seed)
    feats["facade"] = _emit_facade(w, ctx, p, x0, x1, zf, FY, ax, seed)
    feats.update(_emit_interior(w, ctx, p, ax, az_chord, zf, FY, seed))
    feats["approach"] = _emit_approach(w, ctx, p, ax, zf, FY, p.get("spur_to"), seed)
    return w.canvas({"kind": "sanctum", "profile_view": "face", "facing": [0, 1],
                     "floor_y": FY, "features_built": feats})
