"""The Island Run - a parkour descent that winds once around the island, plate to lowland.

Jack's idea: jump pads starting at the top that wind all the way around, all the way down. The
PHYSICS decided its shape before any of the design did, and the number is worth keeping:

    drop  2 blocks -> 0.35s of air -> ~2.0 blocks of horizontal reach
    drop 13 blocks -> 0.90s ->       ~5.0
    drop 30 blocks -> 1.37s ->       ~7.7

One turn around this island at r=51 is 320 blocks of travel, and we have Y198 down to Y41 -
157 courses - to spend. So:

  * a FALLING course (slime pads, 13+ course drops) buys ~5 blocks of travel per drop and
    would wind about a QUARTER of a turn before it ran out of island. It cannot do what was
    asked.
  * a JUMPING course of 2-course drops and ~4-block hops needs 80 hops for a full turn and
    spends 160 courses doing it.

157 available against 160 needed is as close to an exact fit as this kind of thing gets, and it
is why the run is a jump course and not a bounce course. It also means NO SLIME: a two-course
drop does no damage, so a bounce pad would be solving a problem the geometry already removed.

THE ROUTE IS SEARCHED, NOT DRAWN. Each hop looks for a site within jumping reach of the last
that is clear of the world, clear of every design, and has headroom - flexing radius, drop and
angle in that order of preference until one is found. That is what lets a single rule thread
past the giraffe, the ladybird, the bat and the shop islet, all of which stand out to r 57-65
in the band the run passes through.

EVERY PAD CARRIES ITS OWN LIGHT, for two reasons that happen to agree. A pad is a new walkable
surface hanging in the void, so without a light it is 77 new places for a mob to stand and the
night pass would have to grow by 77 fixtures. And a lit ring winding once around the island is
the thing this build is actually for after dark.

The stone follows the island's own gradient, the one the Lowland Stair already carries: island
rock at the top, deepslate through the twilight, the quarter's blackstone at the bottom.
"""
from __future__ import annotations

import math

from . import protect
from .canvas import Canvas, hash01
from .vertical import Ctx, World

PARKOUR = {
    "under": None,
    "centre": [-24200, 30000],
    "y_top": 196,
    "y_bottom": 42,
    "radius": 52,
    "radius_flex": [0, 3, -3, 6, -6, 9, -9, 12, -12],
    # NEVER 4. Fall damage in Minecraft is max(0, blocks - 3) half-hearts, so a three-course
    # drop is free and a four-course drop costs half a heart - and a 75-hop run that bleeds
    # you half a heart at a time is a run nobody finishes.
    "drop": [2, 3, 1],             # preferred course drops per hop, in order
    "advance": [4.5, 5.5, 3.5, 6.5, 7.5],   # degrees of turn per hop, in order
    "max_reach": 4.6,              # a jump this island's physics allows; see the docstring
    "pad": 1,                      # pad half-width: 1 -> a 3x3 landing
    "headroom": 3,
    "station_every": 8,            # a wider rest pad, so the run has checkpoints
    "station_pad": 2,              # ...5x5
    "light": "ochre_froglight",    # Jack's own idiom, and it stops the pad being a spawn spot
    "bands": [[150, "stone_bricks", "mossy_stone_bricks"],
              [95, "deepslate_bricks", "cobbled_deepslate"],
              [0, "polished_blackstone_bricks", "blackstone"]],
    "weather": 0.28,
    "seed": 3,
}

AIRY = ("air", "cave_air", "void_air")
_PASSABLE = set(AIRY) | {"vine", "short_grass", "tall_grass", "fern", "large_fern",
                         "moss_carpet", "azalea", "flowering_azalea", "glow_lichen",
                         "hanging_roots", "dead_bush", "snow", "tripwire"}


def _band(p, y):
    for lo, main, alt in p["bands"]:
        if y >= lo:
            return main, alt
    return p["bands"][-1][1], p["bands"][-1][2]


def build_parkour(cfg: dict, donors=None) -> Canvas:
    p = {**PARKOUR, **cfg}
    if not p.get("under"):
        raise ValueError("parkour needs params.under")
    ctx = Ctx(p["under"])
    w = World()
    cx, cz = p["centre"]
    # OUT OF THE CAPTURE IS NOT EMPTY, IT IS UNKNOWN. `Ctx.name_at` answers "air" for any
    # coordinate outside the scanned box, so a search that trusts it happily sites pads in
    # space nobody has ever looked at - the first build put its opening pad a block past the
    # scan's east edge. Same family as "unloaded is not absent" and "passable is not empty".
    from .vertical import load_capture
    _cap, (_cox, _coy, _coz) = load_capture(p["under"])
    _csy, _csz, _csx = _cap.ids.shape

    def in_capture(x, y, z):
        return (_cox <= x < _cox + _csx and _coy <= y < _coy + _csy
                and _coz <= z < _coz + _csz)
    reserved = set()
    for path in (p.get("reserve") or []):
        import json
        import os
        if not os.path.exists(path):
            continue
        for c in json.load(open(path, encoding="utf-8"))["cells"]:
            reserved.add((c[0], c[1], c[2]))

    def name(x, y, z):
        return ctx.name_at(x, y, z)

    def clear(x, y, z, half):
        """A pad needs its own footprint and headroom, and must touch nothing - the run hangs
        in open void and a pad grafted onto the giraffe is not a stepping stone."""
        for dx in range(-half, half + 1):
            for dz in range(-half, half + 1):
                for dy in range(0, p["headroom"] + 1):
                    q = (x + dx, y + dy, z + dz)
                    if not in_capture(*q) or q in reserved:
                        return False
                    n = name(*q)
                    if n not in _PASSABLE or protect.is_protected(n):
                        return False
        return True

    def try_hop(ang, y, prev, half, drops, angles, flexes, reach):
        for dr in flexes:
            for dy in drops:
                for da in angles:
                    r = p["radius"] + dr
                    a = math.radians(ang + da)
                    x = int(round(cx + r * math.cos(a)))
                    z = int(round(cz + r * math.sin(a)))
                    ny = int(round(y - dy))
                    if ny < p["y_bottom"]:
                        continue
                    if prev and math.dist((x, z), (prev[0], prev[2])) > reach:
                        continue
                    if not clear(x, ny, z, half):
                        continue
                    return (x, ny, z, ang + da, half)
        return None

    ang, y, prev = 0.0, float(p["y_top"]), None
    sites, relaxed = [], 0
    while y > p["y_bottom"] and len(sites) < 200:
        half = p["station_pad"] if len(sites) % p["station_every"] == 0 else p["pad"]
        hop = try_hop(ang, y, prev, half, p["drop"], p["advance"], p["radius_flex"],
                      p["max_reach"])
        if hop is None and half > p["pad"]:
            hop = try_hop(ang, y, prev, p["pad"], p["drop"], p["advance"],
                          p["radius_flex"], p["max_reach"])   # a station is a luxury
        if hop is None:
            # A MISS MUST NOT MANUFACTURE A GAP. The first version answered a failed search by
            # dropping two courses and swinging on WITHOUT placing a pad, which quietly put a
            # 118-course fall in the middle of the route - a run that reads as finished and
            # kills you at hop twenty. Relax the search instead, and if even that finds
            # nothing, END the run here rather than inventing a leap nobody can make.
            hop = try_hop(ang, y, prev, p["pad"], p["drop"],
                          [3.0, 4.5, 6.0, 7.5, 9.0, 10.5, 12.0, 2.0, 1.0],
                          [0, 3, -3, 6, -6, 9, -9, 12, -12, 15, -15, 18, -18],
                          p["max_reach"])
            if hop is not None:
                relaxed += 1
        if hop is None:
            break
        x, ny, z, ang, half = hop
        sites.append((x, ny, z, half))
        prev = (x, ny, z)
        y = ny

    if not sites:
        raise ValueError("the run found no sites at all - check the radius against the island")

    feats = {"pads": 0, "stations": 0, "lights": 0, "hops": len(sites),
             "relaxed": relaxed}
    for i, (x, y, z, half) in enumerate(sites):
        main, alt = _band(p, y)
        for dx in range(-half, half + 1):
            for dz in range(-half, half + 1):
                if half > 1 and abs(dx) == half and abs(dz) == half:
                    continue                      # clip the corners: a disc, not a slab
                mat = alt if hash01(x + dx, y, z + dz, p["seed"]) < p["weather"] else main
                w.put(x + dx, y, z + dz, mat)
        if half > 1:
            feats["stations"] += 1
        else:
            feats["pads"] += 1
        # the light is FLUSH in the pad, so nothing stands proud of a landing you are aiming at
        w.put(x, y, z, p["light"])
        feats["lights"] += 1

    return w.canvas({"kind": "parkour", "profile_view": "top", "facing": [0, 1],
                     "features_built": feats,
                     "route": [[int(a), int(b), int(c)] for a, b, c, _h in sites]})
