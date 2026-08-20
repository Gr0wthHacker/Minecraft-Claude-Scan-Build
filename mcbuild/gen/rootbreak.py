"""The taproot's passage through the deck: the root the room was always supposed to be about.

THE STORY FAILURE THIS FIXES. The sequence is meant to run: a mystical, half-apocalyptic plate
with giant animals on it -> an interior that holds the awe -> a descent down the taproot to the
void. The deck is the hinge of that. And the taproot **tops out at Y188**, six courses below the
deck floor, so the one room whose entire purpose is to hand you to the root NEVER SHOWS YOU THE
ROOT. You cross a grey workshop and find a hole.

This is not an invention. The geometry already says it and so does the taproot's own config -
*"The centre tree's roots break through the deck skin and twist down into the void."* Reading the
capture through the root's 90-cell footprint:

    Y203+     oak_wood, 31 cells       <- the great tree, directly overhead
    Y200      the deck's ceiling
    Y195-199  2 to 20 of 90 solid      <- THE ROOM. empty.
    Y194      90/90 stone_bricks       <- the deck floor
    Y191-193  empty                    <- the undercroft
    Y188      70 cells of taproot      <- the root's head, directly below

The tree is above, the root is below, and the root is missing exactly where the room is. Building
that passage costs a few hundred blocks and gives the room the only things the audit said it
lacked - a focal point, organic form against the grid, wood, and colour - and gives all four of
them a REASON, which is the difference between decoration and a place.

It breaks through three surfaces on the way: the ceiling at Y200, the deck floor at Y194 and the
belly skin at Y190. Each break is heaved, not cut - cracked masonry and cobble shoved aside, some
cells simply gone. A clean hole reads as a designed opening; a broken one reads as something that
came through, which is the whole point.

Light is BIOLUMINESCENT, not lamps: glow lichen on the bark, soul fire at the base. The plate above
is lit by daylight and the lowland by lanterns; this room should be lit by the thing growing
through it.
"""
from __future__ import annotations

import collections
import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World

ROOTBREAK = {
    "under": None,
    "x": -24200,               # the taproot's own column
    "z": 30018,
    "y_from": 188,             # the taproot's head - where this picks the root up
    "y_to": 203,               # the tree's own wood on the plate - where it hands it back
    "strands": 3,
    "trunk_r": 3.4,            # at the top, where it is still one mass
    "strand_r": 1.5,
    "spread": 4.0,             # how far the strands orbit by the time they reach the head
    "twist": 2.0,              # radians over the whole run
    "wood": "oak_wood",        # the taproot's own material, so the two read as one root
    "bark_alt": "mangrove_roots",
    "moss": "moss_block",
    "lichen": "glow_lichen",
    "vine": "vine",
    "roots": "hanging_roots",
    "rubble": "cracked_stone_bricks",
    "rubble_alt": "cobblestone",
    "soul": "soul_lantern",
    "breaks": [190, 194, 200],  # belly skin, deck floor, ceiling
    "break_r": 2.2,            # how far the heave reaches past the root
    "moss_rate": 0.55,
    "lichen_rate": 0.16,
    "vine_rate": 0.40,
    "seed": 0,
}

AIR = ("air", "cave_air", "void_air")
# what the root is allowed to shoulder aside. Anything else is a machine or someone's fixture.
BREAKABLE = ("stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks", "chiseled_stone_bricks",
             "smooth_stone", "stone", "cobblestone", "mossy_cobblestone", "moss_block",
             "gray_wool", "black_wool", "dirt", "gravel", "andesite", "vine", "moss_carpet",
             "stone_brick_slab", "smooth_stone_slab", "deepslate_bricks") + AIR


def build_rootbreak(cfg: dict, donors=None) -> Canvas:
    p = {**ROOTBREAK, **cfg}
    if not p.get("under"):
        raise ValueError("rootbreak needs params.under - it has to know what it is breaking")
    ctx = Ctx(p["under"])
    w = World()
    cx, cz = int(p["x"]), int(p["z"])
    y0, y1 = int(p["y_from"]), int(p["y_to"])
    seed = int(p["seed"])
    n_str = int(p["strands"])
    counts = collections.Counter()
    h = lambda *q: hash01(*q, seed)

    def name(x, y, z):
        return ctx.name_at(x, y, z).split(":")[-1].split("[")[0]

    def free(x, y, z):
        return name(x, y, z) in BREAKABLE

    def put(x, y, z, blk, **props):
        if free(x, y, z):
            w.put(x, y, z, blk, **props)
            return True
        return False

    span = max(1, y1 - y0)
    cells = {}

    # ---- THE ROOT. One trunk where it leaves the tree, splitting into strands as it descends, so
    # that by the time it reaches Y188 it lands on the head that is already built there.
    for y in range(y0, y1 + 1):
        t = (y1 - y) / span                       # 0 at the tree, 1 at the existing root head
        ang0 = float(p["twist"]) * t
        if t < 0.35:                              # still one mass, just under the tree
            r = float(p["trunk_r"]) * (1.0 - 0.35 * t)
            for dx in range(-int(r) - 1, int(r) + 2):
                for dz in range(-int(r) - 1, int(r) + 2):
                    if math.hypot(dx, dz) > r * (0.88 + 0.22 * h(dx, y, dz, 5)):
                        continue
                    cells[(cx + dx, y, cz + dz)] = True
        else:
            f = (t - 0.35) / 0.65
            orbit = float(p["spread"]) * f
            rr = float(p["strand_r"]) * (1.0 + 0.25 * f)
            for s in range(n_str):
                a = ang0 + s * 2 * math.pi / n_str
                sx = cx + orbit * math.cos(a)
                sz = cz + orbit * math.sin(a)
                for dx in range(-int(rr) - 1, int(rr) + 2):
                    for dz in range(-int(rr) - 1, int(rr) + 2):
                        if math.hypot(dx, dz) > rr * (0.85 + 0.25 * h(dx, y, dz, 7)):
                            continue
                        cells[(int(round(sx)) + dx, y, int(round(sz)) + dz)] = True

    # PLACED, not intended. A cell the world refused is not root, and anything anchored to it -
    # a vine, a lichen, a hanging root - has nothing to hold. Every dressing pass below reads this
    # set rather than `cells`, which is the same lesson as the mane that came off in seven pieces.
    placed, solid_wood = set(), set()
    for (x, y, z) in sorted(cells):
        r = h(x, y, z, 11)
        blk = p["bark_alt"] if r < 0.18 else p["wood"]
        if put(x, y, z, blk, **({"axis": "y"} if blk.endswith("_wood") else {})):
            placed.add((x, y, z))
            # mangrove_roots is NOT a full cube, so nothing hangs off its underside - a hanging
            # root under one audits as "from air". Only the solid wood can carry anything.
            if blk == p["wood"]:
                solid_wood.add((x, y, z))
            counts["root"] += 1

    # ---- THE BREAKS. Three surfaces get shouldered aside: the ceiling, the deck floor and the
    # belly skin. Heaved, not cut - a clean hole reads as a designed opening, a broken one reads
    # as something that came THROUGH, which is the entire point of the object.
    br = float(p["break_r"])
    for by in p["breaks"]:
        near = {(x, z) for (x, y, z) in cells if y == by}
        if not near:
            continue
        for (nx, nz) in list(near):
            for dx in range(-int(br) - 1, int(br) + 2):
                for dz in range(-int(br) - 1, int(br) + 2):
                    d = math.hypot(dx, dz)
                    if d < 0.9 or d > br:
                        continue
                    x, z = nx + dx, nz + dz
                    if (x, by, z) in cells or not free(x, by, z):
                        continue
                    q = h(x, by, z, 13)
                    if q < 0.30:                  # simply gone - the fracture
                        w.put(x, by, z, "air")
                        counts["heaved"] += 1
                    elif q < 0.75:                # cracked, and shoved half a course proud
                        w.put(x, by, z, p["rubble"] if q < 0.55 else p["rubble_alt"])
                        counts["rubble"] += 1

    # ---- DRESSING. Moss where light would reach a top face, lichen on the bark, vines and
    # hanging roots off the underside where the root crosses the room's open air.
    top = {}
    for (x, y, z) in placed:
        if (x, y + 1, z) not in placed:
            top[(x, z)] = max(top.get((x, z), -9999), y)
    for (x, z), y in top.items():
        if h(x, y, z, 17) < float(p["moss_rate"]):
            if put(x, y, z, p["moss"]):
                counts["moss"] += 1
    for (x, y, z) in sorted(placed):
        if h(x, y, z, 19) >= float(p["lichen_rate"]):
            continue
        for dx, dy, dz, face in ((1, 0, 0, "east"), (-1, 0, 0, "west"),
                                 (0, 0, 1, "south"), (0, 0, -1, "north")):
            q = (x + dx, y + dy, z + dz)
            if q in placed or not free(*q) or name(*q) not in AIR:
                continue
            w.put(*q, p["lichen"], **{face: "true", "waterlogged": "false"})
            counts["lichen"] += 1
            break
    # ---- (hanging roots off the underside: REMOVED.) They audit as "from air" in context, and
    # the reason is worth keeping: `verify_against` composites the design onto the capture without
    # overwriting, so where the root wants to replace an existing slab the audit still sees the
    # SLAB overhead - and nothing hangs from a slab's underside. Two blocks were not worth a
    # special case, and the root reads without them.

    # ---- SOUL FIRE at the base, where the root meets the deck floor. The plate above is lit by
    # daylight and the lowland by lanterns; this room should be lit by the thing growing through it.
    lit = 0
    for (x, z), y in sorted(top.items()):
        if lit >= 3 or not (194 <= y <= 197):
            continue
        if h(x, y, z, 37) < 0.12 and put(x, y + 1, z, p["soul"], hanging="false",
                                         waterlogged="false"):
            counts["soul"] += 1
            lit += 1

    return w.canvas({"kind": "rootbreak", "x": cx, "z": cz, "y_from": y0, "y_to": y1,
                     "strands": n_str, **counts})
