"""The Harbor Light - a small beacon at the root of the quay, where the mole meets the shore.

WHY AT THE ROOT AND NOT THE TIP. The pond is the harbor and a harbor gets a light - but the
quay's lip is a diagonal ribbon one to three cells wide (measured off the 15:01 scan), and no
tower base sits on it without covering the landing steps or standing on a designed slab. The
mole ROOT at X-24205..-24203 / Z30017..30019 is dry moss plus the quay's own corner masonry,
clear of the steps by four and the watergate by six, and a light at the root is real harbor
grammar anyway: it marks the entrance from the shore and rises over the whole quay in the
west-bank money view, the ring behind it.

NOT ONE WATER CELL IS REPLACED - the axolotl's rule, the quay's rule. Every column seats on
its own dry ground; where the 5x5 plinth would reach the pond it simply stops, and the torn
lakeward edge is the ruin: the water took the outworks, the light still burns.

The lamp is a SOUL LANTERN in an open lightroom - four corner posts and a cap, nothing else -
because the harbor's own mooring light is already cold, and cold-against-warm is the quarter's
colour system. The lantern hangs from the cap, which is the chain rule: a chain hangs from the
block ABOVE it, so the string finds a real ceiling.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .ruinring import _free, _surface, _weathered

HARBORLIGHT = {
    "under": None,
    "at": None,                # [x, z] centre of the 3x3 shaft
    "base_y": None,            # plinth top - PIN once built
    "shaft_h": 9,
    "seed": 0,

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


def build_harborlight(cfg: dict, donors=None) -> Canvas:
    p = {**HARBORLIGHT, **cfg}
    if not p.get("under") or not p.get("at"):
        raise ValueError("harborlight needs params.under and params.at")
    ctx = Ctx(p["under"])
    seed = int(p["seed"])
    ax, az = (int(v) for v in p["at"])
    if p.get("base_y") is not None:
        FY = int(p["base_y"])
    else:
        gs = sorted(g for x in range(ax - 1, ax + 2) for z in range(az - 1, az + 2)
                    for g, nm in [_surface(ctx, x, z)]
                    if g is not None and nm not in ("water", "ice"))
        FY = gs[len(gs) // 2] + 1

    w = World()
    feats = {}

    # ---- plinth 5x5: dry columns only - the pond keeps every cell it owns ----
    n = 0
    for x in range(ax - 2, ax + 3):
        for z in range(az - 2, az + 3):
            g, nm = _surface(ctx, x, z)
            if g is None or nm in ("water", "ice") or g >= FY:
                continue
            for y in range(g + 1, FY + 1):
                mat = p["chiseled"] if y == FY else _weathered(p, hash01(x, y, z, seed))
                n += _put(w, ctx, x, y, z, mat)
    feats["plinth"] = n

    # ---- shaft 3x3, solid, weathered; one chiseled band at half height ----
    H = int(p["shaft_h"])
    n = 0
    band = FY + 1 + H // 2
    for k in range(H):
        y = FY + 1 + k
        for x in range(ax - 1, ax + 2):
            for z in range(az - 1, az + 2):
                mat = p["chiseled"] if y == band and (x != ax or z != az) \
                    else _weathered(p, hash01(x, y, z, seed))
                n += _put(w, ctx, x, y, z, mat)
    feats["shaft"] = n

    # ---- gallery: a 5x5 chiseled-edged deck the keeper would have stood on ----
    n = 0
    yg = FY + H + 1
    for x in range(ax - 2, ax + 3):
        for z in range(az - 2, az + 3):
            edge = x in (ax - 2, ax + 2) or z in (az - 2, az + 2)
            n += _put(w, ctx, x, yg, z, p["chiseled"] if edge
                      else _weathered(p, hash01(x, yg, z, seed)))
    # corner nubs on the gallery rim - a parapet the weather has mostly taken
    for dx in (-2, 2):
        for dz in (-2, 2):
            if hash01(ax + dx, 61, az + dz, seed) < 0.75:
                n += _put(w, ctx, ax + dx, yg + 1, az + dz, p["rough"])
    feats["gallery"] = n

    # ---- lightroom: four posts, a cap, and the lamp hanging inside ----
    n = 0
    for dx in (-1, 1):
        for dz in (-1, 1):
            for k in (1, 2):
                n += _put(w, ctx, ax + dx, yg + k, az + dz, p["chiseled"])
    for x in range(ax - 1, ax + 2):
        for z in range(az - 1, az + 2):
            if x == ax and z == az:
                # the lamp hangs from THIS cell, and a lantern hangs from a full block -
                # a slab cap read as "hanging from air" in the audit, in context too
                n += _put(w, ctx, x, yg + 3, z, p["chiseled"])
            else:
                n += _put(w, ctx, x, yg + 3, z, p["slab"], type="bottom")
    n += _put(w, ctx, ax, yg + 4, az, p["chiseled"])   # the finial
    feats["lightroom"] = n
    feats["lamp"] = _put(w, ctx, ax, yg + 2, az, "soul_lantern", hanging="true") \
        if w.has(ax, yg + 3, az) else 0

    return w.canvas({"kind": "harborlight", "profile_view": "face", "facing": [-1, 0],
                     "base_y": FY, "features_built": feats})
