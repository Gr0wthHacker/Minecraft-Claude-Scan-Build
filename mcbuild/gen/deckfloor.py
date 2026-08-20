"""The working deck's floor: resolve the scatter, draw an edge, and shut the moss farm in a room.

WHY THIS EXISTS, measured off the 2026-08-19 19:09 capture. The deck has 2,145 floor columns and
they are a patchwork of six materials:

    1,060  dressed brick        the intended floor
      499  green                ONE real 269-cell zone (the moss farm) + 230 cells of scatter
      266  rough stone/cobble   biggest blob 58, the rest scatter
      236  vine                 127 blobs averaging under two cells

So ~730 cells across 113 separate blobs are noise rather than design, and only 44% of the floor is
walkable with three courses clear. That patchwork is also why the taproot entrance does not read:
its apron is grey on a grey field, and an entrance cannot be the figure when the ground is the same
tone and equally busy. Quieting the floor is what makes the entrance legible - it is not a separate
job from building the entrance, it is the other half of it.

THREE MOVES, and each one is derived rather than drawn:

  1. RESOLVE THE SCATTER to the field material. Only vine, stray rough stone and stray green - the
     moss farm is left alone, and anything that is not on the whitelist is left alone, because a
     cell holding something unexpected belongs to a machine this design knows nothing about.

  2. DRAW THE EDGE. The deck's rim is every floor column with a missing neighbour - 883 of them,
     found by flood, never by a hand-written box. In `deepslate_bricks`, which is the only strong
     value contrast this economy offers at cheap-or-ok tier: 51 RGB darker than stone brick, where
     cracked, chiseled and smooth stone are all within 4 and draw nothing at all.

  3. SHUT THE MOSS FARM IN. It is a WORKING farm - 29 ice, 12 water, glow lichen, carpet - so the
     wall must not cut its water, and a rectangle will not do: the box one cell out from the farm
     is 58% air, and two cells out 70%, because the farm sits on an irregular lobe. A rectangular
     room would float over holes. So the wall follows the farm's OWN dilated edge and lays only
     where there is floor under it and the cell is free - and it counts what it skipped, because a
     wall with unreported gaps is worse than no wall.

The palette is the atelier's greys plus the deepslate band, the same hand as the stair head and the
court, so the whole deck reads as one build rather than as four.
"""
from __future__ import annotations

import collections

from .canvas import Canvas, hash01
from .protect import is_protected
from .vertical import Ctx, World

DECKFLOOR = {
    "under": None,
    "floor_y": 194,
    "field": "stone_bricks",           # what the scatter resolves to
    "field_alt": "cracked_stone_bricks",   # a little grain so it is not a sheet
    "alt_rate": 0.14,
    "border": "deepslate_bricks",      # the only real value contrast at cheap-or-ok tier
    "band": "deepslate_bricks",
    "room_wall": "stone_bricks",
    "room_plinth": "deepslate_bricks",
    "room_glass": "glass_pane",
    "room_cap": "stone_brick_slab",
    "lamp": "lantern",
    "room_h": 3,                       # courses of wall above the floor
    "room_glass_at": 2,                # which course is glazed, so you can see the farm working
    "lamp_every": 7,
    "door_toward": [-24202, 30001],   # the doorway goes on the wall column nearest this point
    # LINKS. The deck is not one room, it is 61 separate walkable pieces - the moss farm's 247
    # cells are their own island, four blocks and two courses from the main deck. A link is a
    # stepped path between two points; slabs carry the half-courses so it walks.
    "links": [],               # world [[x1,y1,z1, x2,y2,z2], ...]
    "link_deck": "stone_bricks",
    "link_step": "stone_brick_slab",
    "border_ring": 0,                  # cells of rim taken by the edge course; 0 = no border
    "zones": [],                       # world [x1,z1,x2,z2] boxes to outline in the floor

    # ---- the ceiling and the light. The floor pass fixed the ground and left the two surfaces
    # that actually say "unfinished": 29% of what is overhead is raw cobblestone and another 8%
    # is moss, and the deck is lit by 20 torches against 8 lanterns.
    # OFF DECK-WIDE, and this is a measured verdict rather than a preference.
    #
    # A SOFFIT BELONGS TO A ROOM, NOT TO A DECK. This one was drawn over whatever happened to be
    # overhead, and off the 2026-08-20 capture that is not a ceiling: of 1,224 columns with a real
    # underside, only 421 are raw enough to treat, and those 421 are 25 SEPARATE LACY PATCHES at
    # SIX different heights (Y197-Y202). The largest is 92 cells and fills 40% of its own bounding
    # box. Nothing can be drawn on that:
    #
    #     grid at 3/4/5/6/8 cells, run threshold 3/4/6  ->  0 to 33 grid cells, all 1-3 long
    #     edge ring per patch                           ->  79% of the treated cells become edge
    #     grid on the single biggest patch alone        ->  10 cells at best
    #
    # ...and one material across 25 islands in a cobble field is scatter, which is exactly what
    # this design's FLOOR pass exists to remove. It is the same finding as `border_ring: 0` one
    # surface up: a third of a line is a dashed scribble, so do not draw the line.
    #
    # The machinery below is correct and stays, because it works on a ROOM - the taproot entrance
    # already lays one flat plane inside its own four walls and that reads. Point it at a zone
    # with a real ceiling and turn it on there.
    "soffit": False,
    "soffit_panel": "smooth_stone",    # the pale coffer panel
    # STONE AND DEEPSLATE. The grid was `dark_oak_wood` and it was the worst block in the design.
    # Measured off the 23:55 capture: the 421 treatable ceiling columns are 57 SEPARATE PATCHES
    # (biggest 97 cells, 29 of them 4 cells or fewer), so a world-aligned 4-grid over them came
    # out as 215 runs of which 184 were one or two cells long - 168 lone blocks. Of the 70 already
    # placed in world ALL are on a grid line, and 27 have no wood neighbour at all.
    #
    # That is the SAME mistake `gallery.py` already made and removed, one file over, for the same
    # stated reason: to move a palette number (wood 7% against the plate's 23%). It is the wrong
    # reason to put a block anywhere, and it is deleted as a goal here too. The deck's ceiling is
    # the island's own rock, so it is dressed in the island's own rock.
    #
    # `deepslate_bricks` is 51 darker than stone brick - the one real value contrast this economy
    # has at cheap-or-ok tier, and the same block the stair head, the zone bands and the void
    # tower draw their lines with, which is what makes them read as one hand.
    "soffit_grid": "deepslate_bricks",
    "soffit_grid_at": 4,               # grid every N cells, in WORLD coordinates so it stays
                                       # aligned even where the ceiling steps up or down
    # ...and A LINE IS ONLY A LINE IF IT RUNS. A grid cell whose run along its own axis is shorter
    # than this demotes to panel, so the grid draws where the ceiling can carry it and nowhere
    # else. Same rule, same reason, as `gallery._MIN_RUN`.
    "soffit_min_run": 4,
    # ...and A PATCH IS ONLY A CEILING IF THERE IS ENOUGH OF IT. Re-materialising a 3-cell island
    # of cobble into smooth stone is scatter - precisely what the floor pass of this same design
    # exists to REMOVE. Patches smaller than this are left as the rock they are.
    "soffit_min_patch": 8,
    "soffit_raw": ("cobblestone", "mossy_cobblestone", "moss_block", "stone", "gravel",
                   "dirt", "andesite", "diorite", "granite", "cobbled_deepslate"),
    "soffit_max": 10,                  # courses above the floor worth calling a ceiling
    # ...and take the grid back out. See 6b: the pass cannot see its own blocks through any gate
    # above, so they are named here explicitly.
    "reclaim_wood": True,
    "reclaim_reach": 4,                # cells past the deck's bounding box to sweep; see 6b
    "reclaim_grid_at": 4,              # the spacing the wood grid WAS built on. History, not a
                                       # setting - it must not follow `soffit_grid_at`.
    "reclaim_wood_blocks": ("dark_oak_wood", "dark_oak_log", "stripped_dark_oak_wood",
                            "stripped_dark_oak_log"),
    "relight": True,                   # torches become lanterns; 95% of the floor is already
                                       # within 7 of a light, so this is purely how it READS
    "lamp_block": "lantern",
    "seed": 0,
}

# scatter: what this design is allowed to replace with field
SCATTER = ("stone", "cobblestone", "mossy_cobblestone", "andesite", "gravel",
           "moss_block", "azalea_leaves", "flowering_azalea_leaves", "grass_block",
           "moss_carpet", "dirt", "coarse_dirt", "rooted_dirt", "podzol")
# ...and what the field itself already is, so the rim course may overwrite it
FIELD_OK = ("stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks", "chiseled_stone_bricks",
            "smooth_stone", "air") + SCATTER
# never touched, at any height: the farm's machinery and anyone's fixtures
# vine is KEPT, not resolved. 111 of them sit on the floor course and 107 are on the rim -
# they are the deck edge's planting hanging DOWN, not mess on the floor, and turning them
# into solid dark blocks both strips the greenery and fills a see-through edge.
KEEP = ("vine", "water", "ice", "lava", "glow_lichen", "chest", "barrel", "hopper", "furnace", "smoker",
        "blast_furnace", "dispenser", "dropper", "piston", "sticky_piston", "observer",
        "spawner", "beehive", "bee_nest", "rail", "powered_rail", "detector_rail", "lectern",
        "note_block", "composter", "cauldron", "crafting_table", "anvil", "loom", "stonecutter",
        "smithing_table", "cartography_table", "fletching_table", "grindstone", "brewing_stand",
        "enchanting_table", "jukebox", "bed", "sign", "banner", "torch", "lantern", "campfire",
        "bamboo", "sugar_cane", "wheat", "carrots", "potatoes", "sapling", "farmland")
# the border may only be laid where the edge is already hard masonry or bare rock
EDGEABLE = ("stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks", "chiseled_stone_bricks",
            "smooth_stone", "stone", "cobblestone", "mossy_cobblestone", "andesite")
GREEN = ("moss_block", "azalea_leaves", "flowering_azalea_leaves", "grass_block", "moss_carpet")
NB4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
AIR = ("air", "cave_air", "void_air")
# Every wood family, for the reclaim: healing dark oak into oak is still wood in the ceiling.
WOODY = ("oak", "spruce", "birch", "jungle", "acacia", "mangrove", "cherry", "bamboo",
         "crimson", "warped", "pale_oak")


def _is_woody(name: str) -> bool:
    n = name.split(":")[-1].split("[")[0]
    return any(k in n for k in WOODY)


def _blobs(pts):
    S, seen, out = set(pts), set(), []
    for p in pts:
        if p in seen:
            continue
        stack, cur = [p], []
        while stack:
            q = stack.pop()
            if q in seen:
                continue
            seen.add(q)
            cur.append(q)
            for dx, dz in NB4:
                r = (q[0] + dx, q[1] + dz)
                if r in S and r not in seen:
                    stack.append(r)
        out.append(cur)
    return sorted(out, key=len, reverse=True)


def build_deckfloor(cfg: dict, donors=None) -> Canvas:
    p = {**DECKFLOOR, **cfg}
    if not p.get("under"):
        raise ValueError("deckfloor needs params.under - it is a REMEDIAL design and must read "
                         "the world it is repairing")
    ctx = Ctx(p["under"])
    fy, seed = int(p["floor_y"]), int(p["seed"])
    w = World()

    def name(x, y, z):
        return ctx.name_at(x, y, z).split(":")[-1].split("[")[0]

    def keep(x, y, z):
        n = name(x, y, z)
        return any(k in n for k in KEEP) or is_protected(n)

    # ---- the deck floor, found by reading the course rather than by a hand-written box
    floor = set()
    box = p.get("box")
    if box:
        bx1, bz1, bx2, bz2 = (int(v) for v in box)
    else:                                   # scan the whole capture's footprint for this course
        bx1, bz1, bx2, bz2 = -100000, -100000, 100000, 100000
    all_cells = _course_cells(ctx, fy, bx1, bz1, bx2, bz2)
    # THE DECK IS THE BIGGEST CONNECTED BLOB of the course, not every cell on it. Taking the whole
    # course swept in 97x93 of island underside - scraps of belly, rim shelves, the lot - and the
    # edge course alone came to 819 cells with 59 free-floating clusters drawn round islands two
    # cells wide. Deriving the blob keeps this a DECK design without a hand-written box.
    # A FLOOR IS ONLY A FLOOR IF YOU CAN STAND ON IT. `_course_cells` returns every non-air cell
    # on the course, and a great many of them are buried INSIDE a moss bank or a cobble mass -
    # not a surface at all. Repaving those inserted a lone stone block into the middle of a solid
    # body, 120 times, which is what reads in world as random blocks. Require air above.
    surface = [c for c in all_cells
               if name(c[0], fy + 1, c[1]) in ("air", "cave_air", "void_air")]
    blobs = _blobs(surface)
    floor = set(blobs[0]) if blobs else set()
    counts_pre = (len(all_cells), len(floor))
    # ...and the DECK, which is the same blob without the standable test. `floor` is where you can
    # stand (892 cells); the deck is every column of the course (1,779). Anything about what is
    # OVERHEAD has to use the deck: a wood block in the ceiling above a moss bank is still in the
    # ceiling, and scoping the reclaim to `floor` reached only 17 of the 70.
    deck_blobs = _blobs(all_cells)
    deck = set(deck_blobs[0]) if deck_blobs else set()

    counts = collections.Counter()
    dig = []          # cells to BREAK; a litematic stores no air

    # ---- 1. THE MOSS FARM. Found as the biggest green blob, not named by hand, so it survives the
    # farm being extended. Everything else green is scatter.
    # the FARM is found on the whole course, not the walkable surface: its own floor has moss
    # growing ON it, so none of it is an exposed surface and the surface-only rule lost the farm
    # entirely - along with the room and its doorway.
    green = [c for c in all_cells if name(c[0], fy, c[1]) in GREEN]
    gb = _blobs(green)
    farm = set(gb[0]) if gb else set()
    counts["farm_cells"] = len(farm)

    # ---- 2. RESOLVE THE SCATTER
    for (x, z) in sorted(floor):
        if (x, z) in farm:
            continue
        n = name(x, fy, z)
        if n not in SCATTER:
            continue
        if keep(x, fy + 1, z):              # something stands on it - that cell is spoken for
            counts["skipped_occupied"] += 1
            continue
        blk = p["field_alt"] if hash01(x, z, 5, seed) < float(p["alt_rate"]) else p["field"]
        w.put(x, fy, z, blk)
        counts["resolved"] += 1

    # ---- 3. DRAW THE EDGE. Every floor column with a missing neighbour.
    # THE OUTER BOUNDARY ONLY, found by flooding the outside. Taking every floor cell with a
    # missing neighbour is NOT the deck's outline: this deck has 25 interior holes, so 269 of the
    # 529 rim cells were hole edges and the border came out as dark rings round 94 separate
    # interior gaps - scribbles all over the floor. That is what "all messed up" was.
    ring = int(p["border_ring"])
    # ...and it is OFF by default on this deck, because the edge cannot take it. Of 260 outer
    # cells, 92 are vine and 64 moss - the hem's planting - and another 139 carry fixtures, so a
    # hard line lands on 82 of them. A third of a line is a dashed scribble, which reads worse
    # than no line at all. `border_ring: 0` says so out loud rather than shipping the dashes.
    xs = [c[0] for c in floor]
    zs = [c[1] for c in floor]
    X0, X1, Z0, Z1 = min(xs) - 1, max(xs) + 1, min(zs) - 1, max(zs) + 1
    outside, st = set(), [(X0, Z0)]
    while st:
        q = st.pop()
        if q in outside or q in floor or not (X0 <= q[0] <= X1 and Z0 <= q[1] <= Z1):
            continue
        outside.add(q)
        for dx, dz in NB4:
            st.append((q[0] + dx, q[1] + dz))
    rim = ({c for c in floor if any((c[0] + dx, c[1] + dz) in outside for dx, dz in NB4)}
           if ring > 0 else set())
    for _ in range(ring - 1):
        rim |= {(c[0] + dx, c[1] + dz) for c in rim for dx, dz in NB4
                if (c[0] + dx, c[1] + dz) in floor}
    counts["outer_rim"] = len(rim)
    for (x, z) in sorted(rim):
        if (x, z) in farm or keep(x, fy + 1, z) or keep(x, fy, z):
            counts["skipped_occupied"] += 1
            continue
        n = name(x, fy, z)
        # ...and only where the edge is already HARD. 92 of this deck's 260 outer cells are vine
        # and 64 are moss: a dark line laid through those stripes out the planting that softens
        # the deck's edge, which is a deliberate part of the hem, not scatter.
        if n not in EDGEABLE:
            counts["skipped_planted"] += 1
            continue
        w.put(x, fy, z, p["border"])
        counts["border"] += 1

    # ---- 4. THE MOSS ROOM. The wall follows the farm's own dilated edge - a rectangle one cell
    # out is 58% air and two cells out 70%, because the farm sits on an irregular lobe of deck.
    wall_line = sorted({(x + dx, z + dz) for (x, z) in farm for dx, dz in NB4
                        if (x + dx, z + dz) not in farm and (x + dx, z + dz) in floor})
    rh = int(p["room_h"])
    glaze = int(p["room_glass_at"])
    # A DOORWAY, chosen from the columns that will ACTUALLY BE BUILT. The first attempt picked
    # the wall cell nearest the deck and 18 of the 41 wall cells are skipped anyway (water, moss,
    # lichen the farm needs) - so it removed one that was never going to exist and the room stayed
    # sealed. The flow audit is what caught it: the moss farm read simply UNREACHABLE.
    buildable = [c for c in wall_line
                 if not any(keep(c[0], fy + k, c[1]) for k in range(0, rh + 1))]
    door = set()
    if buildable:
        ex, ez = (int(v) for v in p.get("door_toward", [-24202, 30001]))
        dcx, dcz = min(buildable, key=lambda c: abs(c[0] - ex) + abs(c[1] - ez))
        door = {(dcx, dcz)}
        for cand in buildable:                     # widen to two where the wall allows
            if cand != (dcx, dcz) and abs(cand[0] - dcx) + abs(cand[1] - dcz) == 1:
                door.add(cand)
                break
    counts["door"] = len(door)
    built_wall = []
    for i, (x, z) in enumerate(wall_line):
        if (x, z) in door:
            put_lintel = p["room_plinth"]          # a head over the opening, and nothing below it
            _put(w, ctx, x, fy + rh + 1, z, put_lintel)
            continue
        if any(keep(x, fy + k, z) for k in range(0, rh + 1)):
            counts["room_skipped"] += 1     # water, lichen, a torch - never cut the farm
            continue
        ok = False
        for k in range(1, rh + 1):
            if k == glaze:
                # glazed, so the farm is on show rather than shut away. Connections along the
                # wall: a pane with every side false renders as a lone post, not as glazing.
                ax = _pane_axis(wall_line, x, z)
                ok |= _put(w, ctx, x, fy + k, z, p["room_glass"], **ax)
            else:
                blk = p["room_plinth"] if k == 1 else p["room_wall"]
                ok |= _put(w, ctx, x, fy + k, z, blk)
        if ok:
            built_wall.append((x, z))
            counts["room_wall"] += 1
    for k, (x, z) in enumerate(built_wall):
        if k % max(1, int(p["lamp_every"])) == 0:
            if _put(w, ctx, x, fy + rh + 1, z, p["lamp"], hanging="false", waterlogged="false"):
                counts["room_lamps"] += 1
        else:
            _put(w, ctx, x, fy + rh + 1, z, p["room_cap"], type="bottom", waterlogged="false")

    # ---- 5. ZONE BANDS. A drawn outline round each working area, so the floor separates the
    # rooms instead of walls doing it and eating the headroom.
    for zb in p.get("zones") or []:
        zx1, zz1, zx2, zz2 = (int(v) for v in zb)
        zx1, zx2 = min(zx1, zx2), max(zx1, zx2)
        zz1, zz2 = min(zz1, zz2), max(zz1, zz2)
        line = ([(x, zz1) for x in range(zx1, zx2 + 1)] + [(x, zz2) for x in range(zx1, zx2 + 1)]
                + [(zx1, z) for z in range(zz1 + 1, zz2)] + [(zx2, z) for z in range(zz1 + 1, zz2)])
        for (x, z) in line:
            if (x, z) not in floor or (x, z) in farm or keep(x, fy + 1, z):
                continue
            if name(x, fy, z) not in FIELD_OK:
                continue
            w.put(x, fy, z, p["band"])
            counts["band"] += 1

    # ---- 5b. LINKS between walkable islands.
    #
    # The path is an L, not a diagonal. A diagonal run of single cells is not 4-connected, so it
    # is a staircase you cannot walk up - the first version placed ten blocks and joined nothing.
    for lk in p.get("links") or []:
        ax, ay, az, bx, by, bz = (int(v) for v in lk)
        leg1 = [(x, az) for x in range(ax, bx + (1 if bx >= ax else -1), 1 if bx >= ax else -1)]
        leg2 = [(bx, z) for z in range(az, bz + (1 if bz >= az else -1), 1 if bz >= az else -1)]
        route = leg1 + leg2[1:]
        n = max(1, len(route) - 1)
        for i, (x, z) in enumerate(route):
            # INTEGER steps. A half-course wants a bottom slab at floor(walk) - place it at
            # walk-1 like a full block and it sits a whole course low, which is how the first two
            # attempts placed 24 blocks and joined nothing. Whole steps walk perfectly well.
            walk = int(round(ay + (by - ay) * i / n))
            wide = 1 if abs(bx - ax) >= abs(bz - az) else 0
            for w2 in (-1, 0, 1):
                px, pz = (x, z + w2) if wide else (x + w2, z)
                if keep(px, walk - 1, pz):
                    continue
                w.put(px, walk - 1, pz, p["link_deck"])
                counts["link"] += 1
                for k in range(0, 3):              # and the headroom to use it
                    if not keep(px, walk + k, pz) and name(px, walk + k, pz) in SCATTER:
                        dig.append((px, walk + k, pz))
                        counts["link_clear"] += 1

    # ---- 6. THE SOFFIT. The biggest untouched surface on the deck. It is NOT flattened: across
    # 1,725 columns the ceiling genuinely steps SIX times - Y197 through Y202, and the largest
    # single plane is only 537 of 1,224 columns - so forcing one plane would either bury the
    # structures under it or leave a shelf. What is fixed is the MATERIAL, and it is fixed only
    # where there is enough continuous ceiling for the fix to read. Finished ceilings are left
    # alone; only the quarry ones are replaced.
    #
    # Built in three passes rather than one, because every gate has to see its neighbours:
    #   a. CANDIDATES - raw material, a room under it, part of a plane
    #   b. PATCHES    - drop any connected patch too small to read as a ceiling at all
    #   c. GRID       - and demote any grid cell whose line does not actually run
    if p.get("soffit"):
        raw = tuple(p["soffit_raw"])
        g = max(2, int(p["soffit_grid_at"]))
        min_run = max(1, int(p.get("soffit_min_run", 4)))
        min_patch = max(1, int(p.get("soffit_min_patch", 8)))

        # (a) candidates
        cand = {}
        for (x, z) in sorted(floor):
            roof = None
            for y in range(fy + 3, fy + int(p["soffit_max"]) + 1):
                n = name(x, y, z)
                if n not in ("air", "cave_air", "void_air"):
                    roof = y
                    break
            if roof is None or name(x, roof, z) not in raw:
                continue
            if keep(x, roof, z):
                continue
            # A SOFFIT IS ONLY A SOFFIT WHERE THERE IS A ROOM UNDER IT. "The first solid block
            # above the floor" is not a ceiling in most columns - it is the side of a moss bank or
            # a cobble mass - and replacing one cell in the middle of a solid body inserts a lone
            # block into it. 259 of those, which read in world as random rubble.
            # Require two clear courses beneath: then it is an exposed underside you stand below.
            if any(name(x, roof - k, z) not in ("air", "cave_air", "void_air") for k in (1, 2)):
                counts["soffit_no_room"] += 1
                continue
            # ...and it must be part of a PLANE, not a lone cell: at least two of its four
            # neighbours must be ceiling at the same height.
            nb = sum(1 for dx, dz in NB4
                     if name(x + dx, roof, z + dz) not in ("air", "cave_air", "void_air")
                     and all(name(x + dx, roof - k, z + dz) in ("air", "cave_air", "void_air")
                             for k in (1, 2)))
            if nb < 2:
                counts["soffit_lone"] += 1
                continue
            cand[(x, z)] = roof

        # (b) patches, connected at the SAME ceiling height - a patch that steps is two patches,
        # because a grid line cannot carry across a step and the eye does not join one either.
        patches = _blobs_level(cand)
        keep_cells = {}
        for patch in patches:
            if len(patch) < min_patch:
                counts["soffit_small_patch"] += len(patch)
                continue
            for c in patch:
                keep_cells[c] = cand[c]
        counts["soffit_patches"] = sum(1 for q in patches if len(q) >= min_patch)

        # (c) grid, then the run gate. A grid cell survives only if its run along its OWN axis
        # reaches min_run inside the kept cells; otherwise it is a lone dark block, and it draws
        # as panel instead.
        grid = {c for c in keep_cells if c[0] % g == 0 or c[1] % g == 0}

        def run_along(c, axis):
            """Length of the unbroken grid line through `c` along `axis`, at c's own height.

            A line at constant X runs along Z, and vice versa. Scoring a cell ACROSS its own line
            measures every run as 1, and the threshold then lets isolated cells through - that
            inversion shipped once.
            """
            n = 1
            for step in (1, -1):
                q = list(c)
                while True:
                    q[axis] += step
                    t = (q[0], q[1])
                    if t in grid and keep_cells.get(t) == keep_cells[c]:
                        n += 1
                    else:
                        break
            return n

        drawn = set()
        for c in grid:
            # AN INTERSECTION BELONGS TO BOTH LINES, so it survives if EITHER of them runs. Testing
            # only one axis demoted intersections whose other line was long - which punched a hole
            # through that line and orphaned the cell beside it. Two such orphans, and the whole
            # point of the gate is that there are none.
            ok = ((c[0] % g == 0 and run_along(c, 1) >= min_run)
                  or (c[1] % g == 0 and run_along(c, 0) >= min_run))
            if ok:
                drawn.add(c)
            else:
                counts["soffit_grid_demoted"] += 1

        for c, roof in sorted(keep_cells.items()):
            w.put(c[0], roof, c[1], p["soffit_grid"] if c in drawn else p["soffit_panel"])
            counts["soffit"] += 1
        counts["soffit_grid_cells"] = len(drawn)

    # ---- 6b. RECLAIM. A litematic cannot express removal and the soffit pass cannot see its own
    # mistake: `dark_oak_wood` is not in `soffit_raw`, so the 70 grid blocks already standing in
    # world would have sat there for good. 50 of them have since had moss placed under them and so
    # fail the room test as well - they are unreachable by every gate above.
    #
    # So they are healed directly, and only ever into what already surrounds them: the commonest
    # SOLID same-course neighbour, which measures 57 smooth_stone and 10 stone_bricks against the
    # wood's own 28. That turns each one back into the plane it interrupted instead of punching a
    # hole in a ceiling.
    #
    # Scoped by the pass's OWN SIGNATURE - a cell on the grid line - so it can only ever reclaim
    # its own work. All 70 are on one (43.75% would be chance), which is how they were identified.
    if p.get("reclaim_wood"):
        # ...on the grid the MISTAKE was made on, which is history and does not move. Reading
        # `soffit_grid_at` here couples the fix to the current setting: retuning the grid to 5
        # silently dropped the reclaim from 70 blocks to 26, because the wood is on a 4-grid and
        # nothing else knows that.
        g = max(2, int(p.get("reclaim_grid_at", 4)))
        wood = tuple(p["reclaim_wood_blocks"])
        # ...over the deck's BOUNDING BOX, not its footprint. 11 of the 70 sit in the ceiling
        # above a rim column that carries no block on the floor course at all - the pass placed
        # them when the floor below them still existed - and five of those are out on the east
        # arm, past any sane dilation. The box is the right scope because THE GATE IS THE
        # SIGNATURE, NOT THE FOOTPRINT: a dark oak block on a grid line in these courses is one
        # of this pass's own, and every dark oak block in Y195-203 over this deck is one of the 70.
        reach = max(0, int(p.get("reclaim_reach", 4)))
        rx1 = min(c[0] for c in deck) - reach
        rx2 = max(c[0] for c in deck) + reach
        rz1 = min(c[1] for c in deck) - reach
        rz2 = max(c[1] for c in deck) + reach
        for (x, z) in sorted((i, k) for i in range(rx1, rx2 + 1) for k in range(rz1, rz2 + 1)):
            if not (x % g == 0 or z % g == 0):
                continue
            for y in range(fy + 1, fy + int(p["soffit_max"]) + 1):
                if name(x, y, z) not in wood:
                    continue
                near = collections.Counter()
                for dx, dz in NB4:
                    n = name(x + dx, y, z + dz)
                    # ...and never heal wood into WOOD. `wood` is only the dark oak this pass
                    # placed, so `oak_wood` - which the root break legitimately puts through this
                    # ceiling - was a candidate, and got picked. The design's rule is no wood at
                    # all, so the whole family is barred from being a heal material.
                    # ...and the heal material must be PLAIN. `KEEP` alone let `gray_wool` win,
                    # which is the sculk sensor's shielding by the tree - a design that manufactures
                    # wool to patch a ceiling is a design that will one day manufacture redstone.
                    # `is_protected` is the safe set every generator consults; use it here too.
                    if (n in AIR or n in wood or _is_woody(n)
                            or is_protected(n) or any(k in n for k in KEEP)):
                        continue
                    near[n] += 1
                heal = near.most_common(1)[0][0] if near else p["soffit_panel"]
                w.put(x, y, z, heal)
                counts["reclaimed_wood"] += 1

    # ---- 7. RELIGHT. Twenty torches against eight lanterns is the single clearest "unfinished
    # base" tell there is, and with 95% of the floor already within 7 of a light this changes
    # nothing functional - it is entirely how the room reads.
    #
    # A standing torch becomes a standing lantern. A WALL torch does not: a lantern cannot mount
    # on a wall, so it is only swapped where there is a block overhead to hang it from, and left
    # alone otherwise rather than deleting someone's light.
    if p.get("relight"):
        for (x, z) in sorted(floor):
            for y in range(fy + 1, fy + int(p["soffit_max"]) + 1):
                n = name(x, y, z)
                if n == "torch":
                    if name(x, y - 1, z) not in ("air", "cave_air", "void_air"):
                        w.put(x, y, z, p["lamp_block"], hanging="false", waterlogged="false")
                        counts["relit"] += 1
                elif n == "wall_torch":
                    if name(x, y + 1, z) not in ("air", "cave_air", "void_air"):
                        w.put(x, y, z, p["lamp_block"], hanging="true", waterlogged="false")
                        counts["relit"] += 1
                    else:
                        counts["torch_left"] += 1

    return w.canvas({"dig": [list(d) for d in dig],
                     "kind": "deckfloor", "floor_y": fy, "floor_cells": len(floor), "deck_cells": len(deck),
                     "course_cells": counts_pre[0],
                     "farm_box": _bounds(farm), "wall_line": len(wall_line), **counts})


def _blobs_level(cells: dict):
    """connected patches of ceiling AT THE SAME HEIGHT. A patch that steps is two patches: a grid
    line cannot carry across a step, and the eye does not join them across one either."""
    seen, out = set(), []
    for p0 in cells:
        if p0 in seen:
            continue
        st, cur = [p0], []
        while st:
            q = st.pop()
            if q in seen:
                continue
            seen.add(q)
            cur.append(q)
            for dx, dz in NB4:
                r = (q[0] + dx, q[1] + dz)
                if r in cells and r not in seen and cells[r] == cells[q]:
                    st.append(r)
        out.append(cur)
    return out


def _put(w: World, ctx, x, y, z, name, **props):
    n = ctx.name_at(x, y, z).split(":")[-1].split("[")[0]
    if any(k in n for k in KEEP):
        return False
    w.put(x, y, z, name, **props)
    return True


def _pane_axis(line, x, z):
    """connect the pane along the wall it sits in"""
    S = set(line)
    ew = ((x - 1, z) in S) or ((x + 1, z) in S)
    ns = ((x, z - 1) in S) or ((x, z + 1) in S)
    if ew and not ns:
        return {"east": "true", "west": "true", "north": "false", "south": "false",
                "waterlogged": "false"}
    if ns and not ew:
        return {"north": "true", "south": "true", "east": "false", "west": "false",
                "waterlogged": "false"}
    return {"north": "true", "south": "true", "east": "true", "west": "true",
            "waterlogged": "false"}


def _bounds(cells):
    if not cells:
        return None
    xs = [c[0] for c in cells]
    zs = [c[1] for c in cells]
    return [min(xs), min(zs), max(xs), max(zs)]


def _course_cells(ctx, y, bx1, bz1, bx2, bz2):
    """every non-air cell on one course of the capture"""
    import numpy as np
    m = ctx.m
    ox, oy, oz = ctx.ox, ctx.oy, ctx.oz
    j = y - oy
    if not (0 <= j < m.ids.shape[0]):
        return []
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    out = []
    layer = m.ids[j]
    for k in range(layer.shape[0]):
        row = layer[k]
        for i in np.nonzero(row)[0]:
            if names[row[i]] == "air":
                continue
            x, z = ox + int(i), oz + k
            if bx1 <= x <= bx2 and bz1 <= z <= bz2:
                out.append((x, z))
    return out
