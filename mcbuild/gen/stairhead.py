"""The head of the taproot staircase: the entrance you arrive at on the deck.

Jack cut a well through the deck floor at Y194 and left it raw - an open hole with the workshop
stairwell somewhere down in the dark. This is what turns that into a front door.

WHAT THE SITE IS, all measured off the 2026-08-19 19:09 capture and not assumed:

    Y200-201   ceiling over the well (6-7 courses of headroom)
    Y194       the deck floor, with a well cut through it: X-24205..-24200 / Z30002..30010,
               narrowing to a 3-wide neck at X-24205..-24203 for Z30002..30004
    Y191-193   open undercroft, the shaft cased at Z30010-30011
    Y190       the belly skin you land on, moss, with a 3x3 hole at X-24203..-24201 / Z30008..30010
    Y189 down  the existing workshop stairwell, then the root stair

So the entrance has exactly one job in the vertical: carry you from the deck at Y194 down four
courses to the undercroft floor at Y190, and hand you to the shaft that is already built. The neck
is 3 wide, which is a flight; everything else is what makes it read as ARCHITECTURE rather than as
a hole with steps in it - an apron, a lip, a balustrade, corner piers, and light.

IT USES REAL STAIRS, and that is a deliberate departure from the project rule.

    The rule said no stairs because a stair is DIRECTIONAL, `facing` is easy to get backwards, and
    "the capture holds ten stair blocks and none records its state, so there was nothing to settle
    the convention from". Both halves of that are now false. The 19:09 capture holds 463 placed
    stairs and the palette carries their full properties - the earlier reading looked at bare names,
    which drop them. The convention is settled EMPIRICALLY off Jack's own flight at
    X-24213..-24210 / Y195-198 / Z30028, four consecutive treads all `facing=east` climbing east:

        A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D, half=bottom.

    So a flight descending south is built facing NORTH - you climb north out of it. Getting this
    backwards produces a staircase you cannot walk up, and it is invisible in our own renderer,
    which is why it is asserted in tests rather than eyeballed.

The palette is the atelier's four greys plus a dark band, on purpose: the court below, the workshop
above and this head between them should read as one hand. `deepslate_bricks` for the lip is the one
addition - 51 RGB darker than stone brick, and the thing that made the void tower read as masonry
rather than as a grey fin. cracked/chiseled/plain stone brick are all within 4 RGB of each other,
so they carry texture but no tone; do not expect them to draw a line.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx, World

STAIRHEAD = {
    "under": None,             # the capture, so this emits REMAINING work and never fights the world
    "well": None,              # world [x1, z1, x2, z2] of the opening cut in the deck floor
    "neck": None,              # world [x1, z1, x2, z2] of the narrow approach the flight runs down
    "shaft": None,             # world [x1, z1, x2, z2] of the hole in the undercroft floor
    "floor_y": 194,            # the deck course the well is cut through
    "under_y": 190,            # the undercroft floor you land on
    "ceiling_y": 200,          # what the lanterns hang from
    "apron": 2,                # cells of paving worked around the well's lip
    "mouth_w": 3,              # width of the gap left in the balustrade to walk in

    # the atelier's four greys, so the whole complex reads as one hand
    "pale": "smooth_stone",
    "mid": "stone_bricks",
    "figure": "cracked_stone_bricks",
    "verge": "mossy_stone_bricks",
    "medallion": "chiseled_stone_bricks",
    "lip": "deepslate_bricks",         # the dark course that draws the opening
    "wall": "stone_brick_wall",
    "cap": "smooth_stone_slab",
    "tread": "stone_brick_stairs",
    "step": "stone_brick_slab",
    "lamp": "lantern",
    "chain": "iron_chain",
    "seed": 0,
}

# what the entrance is allowed to pave over. Anything else in a cell means the cell belongs to
# something the capture knows about and this design does not - leave it alone.
PLAIN = ("air", "cave_air", "stone_bricks", "smooth_stone", "stone", "cobblestone",
         "mossy_stone_bricks", "cracked_stone_bricks", "moss_block", "stone_brick_slab",
         "smooth_stone_slab", "mossy_stone_brick_slab", "vine", "grass_block", "dirt")

DIRS4 = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def _box(v):
    x1, z1, x2, z2 = (int(q) for q in v)
    return min(x1, x2), min(z1, z2), max(x1, x2), max(z1, z2)


def build_stairhead(cfg: dict, donors=None) -> Canvas:
    p = {**STAIRHEAD, **cfg}
    for k in ("well", "neck", "shaft"):
        if p.get(k) is None:
            raise ValueError(f"stairhead needs params.{k}")
    ctx = Ctx(p["under"]) if p.get("under") else None
    wx1, wz1, wx2, wz2 = _box(p["well"])
    nx1, nz1, nx2, nz2 = _box(p["neck"])
    sx1, sz1, sx2, sz2 = _box(p["shaft"])
    fy, uy, cy = int(p["floor_y"]), int(p["under_y"]), int(p["ceiling_y"])
    seed = int(p["seed"])
    w = World()

    def free(x, y, z) -> bool:
        """may this design write here? Only over the deck's own plain materials."""
        if ctx is None:
            return True
        return ctx.name_at(x, y, z).split(":")[-1].split("[")[0] in PLAIN

    def put(x, y, z, name, **props):
        if free(x, y, z):
            w.put(x, y, z, name, **props)
            return True
        return False

    well = {(x, z) for x in range(wx1, wx2 + 1) for z in range(wz1, wz2 + 1)}
    counts = {"apron": 0, "lip": 0, "balustrade": 0, "treads": 0, "landing": 0,
              "piers": 0, "lamps": 0, "revet": 0}

    # ---- 1. THE APRON. Paving worked round the lip so the opening sits in something, rather than
    # being a rectangle punched in a field of stone brick. Rings out from the edge, and the tone
    # settles to the deck's own material at the last ring so there is no hard join.
    ap = int(p["apron"])
    for x in range(wx1 - ap, wx2 + ap + 1):
        for z in range(wz1 - ap, wz2 + ap + 1):
            if (x, z) in well:
                continue
            d = max(wx1 - x, x - wx2, wz1 - z, z - wz2)      # Chebyshev rings out of the well
            if d < 1 or d > ap:
                continue
            if d == 1:
                blk = p["lip"]                                # the dark course that draws it
            else:
                r = hash01(x, z, 3, seed)
                blk = p["pale"] if r < 0.62 else (p["figure"] if r < 0.80 else p["mid"])
            if put(x, fy, z, blk):
                counts["lip" if d == 1 else "apron"] += 1

    # ---- 2. THE REVETMENT. The well's cut faces are raw undercroft - moss, casing, whatever the
    # belly happens to be. Line them, or the handsome opening looks down onto a building site.
    for y in range(uy + 1, fy):
        for x in range(wx1, wx2 + 1):
            for z in range(wz1, wz2 + 1):
                edge = x in (wx1, wx2) or z in (wz1, wz2)
                if not edge:
                    continue
                blk = p["mid"] if (y - uy) % 3 else p["figure"]
                if put(x, y, z, blk):
                    counts["revet"] += 1

    # ---- 3. THE FLIGHT. Down the neck, four treads, Y194 to Y191, landing on the moss at Y190.
    #
    # It descends SOUTH, so every tread is facing=north: you climb north out of the well. See the
    # module docstring - this is the convention read off Jack's own built flight, not a guess.
    run = list(range(nz1 + 1, nz1 + 1 + (fy - uy)))          # one tread per course of drop
    tread_x = range(nx1, nx2 + 1)
    for i, z in enumerate(run):
        y = fy - i
        for x in tread_x:
            if put(x, y, z, p["tread"], facing="north", half="bottom",
                   shape="straight", waterlogged="false"):
                counts["treads"] += 1
        # a solid cheek under each tread so the flight is not a floating ribbon of steps
        for x in tread_x:
            for yy in range(uy + 1, y):
                if x in (nx1, nx2):
                    put(x, yy, z, p["mid"])

    # ---- 4. THE LANDING at the bottom, paved out to the shaft mouth, with the mouth itself
    # ringed in the dark course so you can see the drop before you are in it.
    shaft = {(x, z) for x in range(sx1, sx2 + 1) for z in range(sz1, sz2 + 1)}
    for x in range(wx1, wx2 + 1):
        for z in range(run[-1] + 1 if run else wz1, wz2 + 1):
            if (x, z) in shaft:
                continue
            ring = any((x + dx, z + dz) in shaft for dx, dz in DIRS4.values())
            blk = p["lip"] if ring else (p["pale"] if hash01(x, z, 7, seed) < 0.55 else p["mid"])
            if put(x, uy, z, blk):
                counts["landing"] += 1

    # ---- 5. THE BALUSTRADE. A wall on the lip capped with a slab - 1.5 blocks, which is the
    # height that reads as a railing rather than as a kerb - all the way round except the mouth.
    mouth = set()
    mw = int(p["mouth_w"])
    mid_x = (nx1 + nx2) // 2
    for dx in range(-(mw // 2), mw // 2 + 1):
        mouth.add((mid_x + dx, wz1 - 1))
    for x in range(wx1 - 1, wx2 + 2):
        for z in range(wz1 - 1, wz2 + 2):
            if (x, z) in well or (x, z) in mouth:
                continue
            if not (wx1 - 1 <= x <= wx2 + 1 and wz1 - 1 <= z <= wz2 + 1):
                continue
            on_ring = x in (wx1 - 1, wx2 + 1) or z in (wz1 - 1, wz2 + 1)
            if not on_ring:
                continue
            corner = x in (wx1 - 1, wx2 + 1) and z in (wz1 - 1, wz2 + 1)
            if corner:
                continue                                      # the piers take the corners
            if put(x, fy + 1, z, p["wall"]):
                counts["balustrade"] += 1
                put(x, fy + 2, z, p["cap"], type="bottom", waterlogged="false")

    # ---- 6. THE PIERS. Four corner posts, taller than the rail, each carrying a lantern. They are
    # what stop the balustrade reading as a fence: a rail between posts is architecture, a rail on
    # its own is safety equipment.
    for cx in (wx1 - 1, wx2 + 1):
        for cz in (wz1 - 1, wz2 + 1):
            ok = False
            for k in range(1, 4):
                blk = p["medallion"] if k == 3 else p["mid"]
                ok |= put(cx, fy + k, cz, blk)
            if ok:
                counts["piers"] += 1
                if put(cx, fy + 4, cz, p["lamp"], hanging="false", waterlogged="false"):
                    counts["lamps"] += 1

    # ---- 7. HANGING LIGHT. Nothing reaches down here - the undercroft has no daylight at all and
    # the well is the only thing that will ever light the landing. Lanterns on chains from the
    # ceiling, hung over the WELL so the light falls down the shaft rather than onto the deck.
    for fx in (0.28, 0.72):
        for fz in (0.30, 0.70):
            x = int(round(wx1 + (wx2 - wx1) * fx))
            z = int(round(wz1 + (wz2 - wz1) * fz))
            if (x, z) in shaft:
                continue
            # a chain hangs from the block ABOVE it. Find a real ceiling first, or the string
            # comes away as four floating links - the same failure the bat's perch vines had, and
            # the audit calls it out as a cluster with nothing to place against.
            roof = None
            for yy in range(cy, cy + 5):
                if ctx is None or ctx.name_at(x, yy, z).split(":")[-1].split("[")[0] not in (
                        "air", "cave_air", "void_air"):
                    roof = yy
                    break
            if roof is None:
                continue
            drop = 3
            hung = 0
            for k in range(1, drop + 1):
                if put(x, roof - k, z, p["chain"], axis="y", waterlogged="false"):
                    hung += 1
            if hung == drop and put(x, roof - drop - 1, z, p["lamp"],
                                    hanging="true", waterlogged="false"):
                counts["lamps"] += 1

    meta = {"kind": "stairhead", "well": [wx1, wz1, wx2, wz2], "neck": [nx1, nz1, nx2, nz2],
            "shaft": [sx1, sz1, sx2, sz2], "floor_y": fy, "under_y": uy, "ceiling_y": cy,
            "stair_facing": "north", "descends": "south", **counts}
    return w.canvas(meta)
