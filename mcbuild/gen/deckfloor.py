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
    "soffit": True,
    "soffit_panel": "smooth_stone",    # the pale coffer panel
    # TIMBER JOISTS, not a stone grid. The gallery moved the palette almost nothing - 230 blocks
    # against a 14,400-block deck - and the soffit is where the leverage is: 717 cells overhead,
    # all stone. Making the grid wood is one parameter and it is what a workshop ceiling actually
    # looks like, which is also how the outside gets to 23% wood against this room's 7%.
    "soffit_grid": "dark_oak_wood",
    "soffit_grid_at": 4,               # grid every N cells, in WORLD coordinates so it stays
                                       # aligned even where the ceiling steps up or down
    "soffit_raw": ("cobblestone", "mossy_cobblestone", "moss_block", "stone", "gravel",
                   "dirt", "andesite", "diorite", "granite", "cobbled_deepslate"),
    "soffit_max": 10,                  # courses above the floor worth calling a ceiling
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
    blobs = _blobs(all_cells)
    floor = set(blobs[0]) if blobs else set()
    counts_pre = (len(all_cells), len(floor))

    counts = collections.Counter()

    # ---- 1. THE MOSS FARM. Found as the biggest green blob, not named by hand, so it survives the
    # farm being extended. Everything else green is scatter.
    green = [c for c in floor if name(c[0], fy, c[1]) in GREEN]
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
                        w.put(px, walk + k, pz, "air")
                        counts["link_clear"] += 1

    # ---- 6. THE SOFFIT. The biggest untouched surface on the deck. It is NOT flattened: across
    # 1,725 columns the ceiling genuinely steps, and forcing one plane would either bury the
    # structures under it or leave a shelf. What is fixed is the MATERIAL - raw cobble and moss
    # become panels with a dark grid, and the grid is set in WORLD coordinates so it stays aligned
    # across a step. Finished ceilings are left alone; only the quarry ones are replaced.
    if p.get("soffit"):
        raw = tuple(p["soffit_raw"])
        g = max(2, int(p["soffit_grid_at"]))
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
            grid = (x % g == 0) or (z % g == 0)
            w.put(x, roof, z, p["soffit_grid"] if grid else p["soffit_panel"])
            counts["soffit"] += 1

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

    return w.canvas({"kind": "deckfloor", "floor_y": fy, "floor_cells": len(floor),
                     "course_cells": counts_pre[0],
                     "farm_box": _bounds(farm), "wall_line": len(wall_line), **counts})


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
