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
from .protect import is_protected, is_used
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

    # ---- the upgrade. The first build was a 3-course railing in a 6-course room: the ceiling is
    # SEVEN courses above the deck floor and made of raw cobblestone, and none of that volume was
    # used. An entrance is a ROOM, and a room is defined by what is overhead as much as underfoot.
    "columns": True,           # corner piers carried the full height, with base and capital
    "cornice": True,           # an oversailing course at the head of the wall
    "arch": True,              # a portal over the mouth, so the way down is a DOOR
    "ceiling": True,           # coffered panels replacing the raw cobble overhead
    "chandelier": True,        # one hanging cluster over the well, not four lonely lanterns
    "handrail": True,          # a rail down the flight, which is what makes it read as a stair
    "cornice_off": 4,          # courses above the floor the cornice sits at
    # THE APPROACH. Standing at the mouth looking north there were seven blocks of nothing at head
    # height: the entrance was the only vertical event in a 989-column room, and you did not
    # discover it, you simply arrived at it. A paved runway between paired piers makes it a
    # destination - which is most of what "grand" means for a door.
    "approach": 7,             # cells of runway north of the mouth; 0 = none
    "approach_w": 5,
    "pier_every": 3,

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
        n = ctx.name_at(x, y, z).split(":")[-1].split("[")[0]
        if n not in PLAIN or is_protected(n):
            return False
        # ...and no STRUCTURE crowding something you stand at and use. Paving the floor beside a
        # chest is fine - it is still floor - but a balustrade or a cornice there is not.
        if y > fy:
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-1, 0, 1):
                    for dz in (-2, -1, 0, 1, 2):
                        if max(abs(dx), abs(dz)) > 1:
                            continue
                        if is_used(ctx.name_at(x + dx, y + dy, z + dz)):
                            return False
        return True

    def put(x, y, z, name, **props):
        if free(x, y, z):
            w.put(x, y, z, name, **props)
            return True
        return False

    well = {(x, z) for x in range(wx1, wx2 + 1) for z in range(wz1, wz2 + 1)}
    counts = {"apron": 0, "lip": 0, "balustrade": 0, "treads": 0, "landing": 0,
              "piers": 0, "lamps": 0, "revet": 0, "column": 0, "cornice": 0, "arch": 0,
              "ceiling": 0, "chandelier": 0, "handrail": 0, "cheek": 0,
              "approach": 0, "pier": 0}

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
    mouth_wide = set()
    mw = int(p["mouth_w"])
    mid_x = (nx1 + nx2) // 2
    for dx in range(-(mw // 2), mw // 2 + 1):
        mouth.add((mid_x + dx, wz1 - 1))
    for dx in range(-(mw // 2) - 1, mw // 2 + 2):
        for dz in (wz1 - 1, wz1 - 2):
            mouth_wide.add((mid_x + dx, dz))
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

    # ---- 7. (was four single hanging lanterns.) REMOVED: the soffit's coffer recesses land on
    # exactly the courses their chains occupied, so each string lost a link and the lantern under
    # it hung from a top slab, whose underside is not solid. They were four lonely dots anyway -
    # the chandelier below is what replaced them, and it throws light DOWN the shaft.

    # ---- 7b. THE SOFFIT. It was raw cobblestone and nothing had ever been done to it - but the
    # first pass coffered it PER COLUMN, following a ceiling that is 6 courses up in some places
    # and 7 in others, so the panels came out as a patchwork that copied the mess instead of
    # correcting it. A soffit is a FLAT PLANE. Take the lowest roof over the footprint, lay the
    # whole ceiling at that one height, and the room finally has a lid.
    soffit = None
    if p.get("ceiling"):
        hs = [r for x in range(wx1 - 2, wx2 + 3) for z in range(wz1 - 2, wz2 + 3)
              for r in [_roof(ctx, x, z, fy + 3, cy + 8, cy)] if r is not None]
        if hs:
            soffit = max(fy + 5, min(hs))
            for x in range(wx1 - 2, wx2 + 3):
                for z in range(wz1 - 2, wz2 + 3):
                    grid = (x - wx1) % 3 == 0 or (z - wz1) % 3 == 0
                    if put(x, soffit, z, p["lip"] if grid else p["pale"]):
                        counts["ceiling"] += 1
                    # the coffer's recess: a lipped slab hung under each panel
                    if not grid and put(x, soffit - 1, z, p["cap"], type="top",
                                        waterlogged="false"):
                        counts["ceiling"] += 1

    # ---- 8. COLUMNS. (after the soffit, so they can reach it) The corner piers ran three courses and stopped in mid-air, which reads as
    # four bollards. Carried to the ceiling with a base and a capital they become an ORDER, and the
    # room acquires a height - the single biggest change between "a railed hole" and "a room".
    if p.get("columns"):
        for cx in (wx1 - 1, wx2 + 1):
            for cz in (wz1 - 1, wz2 + 1):
                roof = soffit if soffit is not None else _roof(ctx, cx, cz, fy + 2, cy + 8, cy)
                if roof is None:
                    continue
                for k in range(fy + 1, roof):
                    off = k - fy
                    if off == 1:
                        blk = p["lip"]                     # base
                    elif off == int(p["cornice_off"]):
                        blk = p["medallion"]               # a band where the cornice springs
                    elif k == roof - 1:
                        blk = p["lip"]                     # capital
                    else:
                        blk = p["mid"]
                    if put(cx, k, cz, blk):
                        counts["column"] += 1

    # ---- 9. THE CORNICE. One oversailing course round the head of the wall. A wall that stops
    # dead is a fence; a wall with a cornice is architecture, and it costs one course.
    if p.get("cornice"):
        cyy = fy + int(p["cornice_off"])
        for x in range(wx1 - 2, wx2 + 3):
            for z in range(wz1 - 2, wz2 + 3):
                on = (x in (wx1 - 2, wx2 + 2) or z in (wz1 - 2, wz2 + 2))
                if not on or (x, z) in mouth_wide:
                    continue
                nbr = sum(1 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
                          if (wx1 - 2 <= x + dx <= wx2 + 2 and wz1 - 2 <= z + dz <= wz2 + 2
                              and (x + dx in (wx1 - 2, wx2 + 2) or z + dz in (wz1 - 2, wz2 + 2))
                              and (x + dx, z + dz) not in mouth_wide))
                if nbr == 0:
                    continue
                if put(x, cyy, z, p["cap"], type="top", waterlogged="false"):
                    counts["cornice"] += 1

    # ---- 10. THE ARCH over the mouth. This is what makes the descent a DOOR rather than a gap in
    # a railing - you pass THROUGH something. Two jambs and a flat-headed arch with the corners
    # stepped in, which is as close to a curve as a 3-wide opening allows.
    if p.get("arch"):
        az = wz1 - 1
        span = sorted({x for (x, z) in mouth})
        if span:
            a0, a1 = span[0] - 1, span[-1] + 1
            roof = _roof(ctx, (a0 + a1) // 2, az, fy + 2, cy + 6, cy) or (fy + 6)
            head = min(roof - 1, fy + 5)
            for x in (a0, a1):                              # the jambs
                for k in range(fy + 1, head):
                    if put(x, k, az, p["mid"] if (k - fy) % 3 else p["lip"]):
                        counts["arch"] += 1
            for x in range(a0, a1 + 1):                     # the head
                if put(x, head, az, p["medallion"] if x in (a0, a1) else p["lip"]):
                    counts["arch"] += 1
            for x in (a0 + 1, a1 - 1):                      # stepped haunches
                if put(x, head - 1, az, p["mid"]):
                    counts["arch"] += 1
            if put((a0 + a1) // 2, head + 1, az, p["medallion"]):
                counts["arch"] += 1                         # keystone

    # ---- 12. THE CHANDELIER. Four single lanterns at the corners lit nothing and read as four
    # dots. One cluster over the middle of the well throws its light DOWN the shaft, which is the
    # only thing that will ever light the landing.
    if p.get("chandelier"):
        mx, mz = (wx1 + wx2) // 2, (wz1 + wz2) // 2
        roof = soffit if soffit is not None else _roof(ctx, mx, mz, fy + 3, cy + 8, cy)
        if roof is not None:
            for k in range(1, 4):
                put(mx, roof - k, mz, p["chain"], axis="y", waterlogged="false")
            hub = roof - 4
            if put(mx, hub, mz, p["medallion"]):
                counts["chandelier"] += 1
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                # the arms are FULL blocks. A lantern hangs from the block above it and a slab
                # will not carry one - the first pass hung all four off `type=top` slabs, whose
                # underside is not solid, and the audit called every one of them "hanging from
                # air". Four floating single cells, which is exactly what it looked like.
                if put(mx + dx, hub, mz + dz, p["medallion"]):
                    counts["chandelier"] += 1
                if put(mx + dx, hub - 1, mz + dz, p["lamp"],
                       hanging="true", waterlogged="false"):
                    counts["lamps"] += 1

    # ---- 13. THE HANDRAIL down the flight. A flight with no rail is a ramp with lines on it.
    # A rail post sits one course DOWN and one step ALONG from the last, so a bare row of them is
    # a diagonal ladder - and diagonal cells are not 6-connected, so all four came away as separate
    # floating blocks. A stone stair has a solid CHEEK under its rail; build that and the rail has
    # something to stand on, which is both correct and connected.
    if p.get("handrail") and run:
        for i, z in enumerate(run):
            y = fy - i
            for x in (nx1 - 1, nx2 + 1):
                for yy in range(uy + 1, y + 1):
                    if put(x, yy, z, p["mid"]):
                        counts["cheek"] += 1
                if put(x, y + 1, z, p["wall"]):
                    counts["handrail"] += 1

    # ---- 14. THE APPROACH: a runway north of the mouth, flanked by piers carrying lanterns.
    ap_len = int(p.get("approach") or 0)
    if ap_len:
        aw = int(p["approach_w"]) // 2
        for i in range(1, ap_len + 1):
            z = wz1 - 1 - i
            for dx in range(-aw, aw + 1):
                x = mid_x + dx
                edge = abs(dx) == aw
                blk = p["lip"] if edge else (p["pale"] if (i + dx) % 4 else p["figure"])
                if put(x, fy, z, blk):
                    counts["approach"] += 1
            if i % max(1, int(p["pier_every"])) == 0:
                for dx in (-aw, aw):
                    x = mid_x + dx
                    roof = _roof(ctx, x, z, fy + 2, cy + 8, cy)
                    hi = min(roof - 1, fy + 4) if roof else fy + 4
                    ok = False
                    for k in range(fy + 1, hi):
                        ok |= put(x, k, z, p["lip"] if k == fy + 1 else p["mid"])
                    if ok:
                        counts["pier"] += 1
                        if put(x, hi, z, p["medallion"]):
                            counts["pier"] += 1
                        if put(x, hi + 1, z, p["lamp"], hanging="false", waterlogged="false"):
                            counts["lamps"] += 1

    meta = {"kind": "stairhead", "well": [wx1, wz1, wx2, wz2], "neck": [nx1, nz1, nx2, nz2],
            "shaft": [sx1, sz1, sx2, sz2], "floor_y": fy, "under_y": uy, "ceiling_y": cy,
            "stair_facing": "north", "descends": "south", **counts}
    return w.canvas(meta)

def _roof(ctx, x, z, y_from, y_to, fallback=None):
    """The first solid course above `y_from` - what a chain or a coffer actually hangs on.

    With no capture there is nothing to read, so it falls back to the DECLARED `ceiling_y`. That
    is what the parameter is for, and without it a build with no `under` quietly lost its soffit,
    columns, cornice, arch and chandelier - every part that needs to know where the roof is."""
    if ctx is None:
        return fallback
    for y in range(y_from, y_to):
        if ctx.name_at(x, y, z).split(":")[-1].split("[")[0] not in ("air", "cave_air", "void_air"):
            return y
    return None
