"""Cut the workshop deck a gallery, timber it, plant it, and give it a basin.

WHY, measured rather than felt. Against the island's own plate the deck reads as follows:

                        plate (outside)   deck (inside)
    distinct blocks           143              91
    mean saturation          50.5            22.3
    colour spread            54.1            25.1
    grey fraction             36%             62%
    wood                      23%              7%

The deck is half as colourful as the outside and nearly twice as grey, and the outside is a third
wood where the deck has almost none. Tidying it made it tidier, not better - every pass so far
added another grey.

    AND THE THING THAT ACTUALLY MATTERS: 179 of the deck's 260 rim columns look out into open air.
    132 of them are WALLED two or three blocks high. There is not one window.

It hangs under a floating island with an uninterrupted view of the void, the lowland far below, the
bat's rock and the ladybird - and it is a sealed grey box with its back to all of it. The single
best thing the outside has is the view; the inside has the same view on 179 columns and uses none
of it. No amount of coffering fixes a room with no windows, which is why this is mostly REMOVAL.

Four moves:

  1. THE GALLERY. Arched bays cut through the walled rim on a rhythm - three open, three pier -
     so it reads as a cloister rather than as holes. Sill left at chest height, opening above it,
     arch head over.
  2. TIMBER. The piers between bays become dark oak, and a beam ties their heads together. That
     alone moves wood from 7% toward the outside's 23%, and it is warm against every grey here.
  3. PLANTING. Vines off the beam into the bay heads. Cheap, green, and they frame a view rather
     than blocking it - the outside is 46% plant and the deck's greenery is all behind the moss
     farm's wall now.
  4. A BASIN. Both spaces are at 1% water and the plate's pond is one of its landmarks. Fully
     rimmed and floored, because this deck hangs in the air and a leak drains into the undercroft.
"""
from __future__ import annotations

import collections

from .canvas import Canvas, hash01
from .protect import is_protected
from .vertical import Ctx, World

GALLERY = {
    "under": None,
    "floor_y": 194,
    "bay": 3,                  # cells of opening...
    "pier": 2,                 # ...between piers. The banks are short runs, so a 3/2
                               # rhythm gets openings out of them where 3/3 does not.
    "sill": 1,                 # courses of wall left under the opening
    "open_h": 2,               # courses of opening
    "arch": True,              # a head over each bay
    "timber": "dark_oak_log",
    "beam": "dark_oak_wood",
    "sill_cap": "stone_brick_slab",
    "jamb": "deepslate_bricks",
    "vine": "vine",
    "vine_rate": 0.45,
    "sill_green": "moss_block",
    "moss": "moss_block",
    "lamp": "lantern",
    "lamp_every": 3,           # every Nth pier carries one
    "basin": None,             # world [x1,z1,x2,z2] for the water feature; None = none
    "basin_rim": "deepslate_bricks",
    "basin_floor": "smooth_stone",
    "water": "water",
    "seed": 0,
}

AIR = ("air", "cave_air", "void_air")
# what a bay may be cut through: the deck's own plain fabric and nothing else
# MASONRY. A bay is a hole cut in a WALL, so there has to be a wall - and this deck's rim is very
# largely planting. Cutting a "window" through a curtain of hanging vine gives you a frame around
# nothing, which is exactly what three of the first bays were: their columns read vine/vine/vine.
WALL_MATS = ("stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks", "chiseled_stone_bricks",
             "smooth_stone", "stone", "cobblestone", "mossy_cobblestone", "andesite",
             "deepslate_bricks", "polished_andesite", "stone_brick_slab", "smooth_stone_slab")
# ...and PLANTING is never cut. 64 vine cells and 19 of moss went to masonry and timber in the
# first build - the same mistake as paving the floor's scatter, which was the deck's only colour.
PLANTING = ("vine", "moss_block", "moss_carpet", "azalea_leaves", "flowering_azalea_leaves",
            "azalea", "flowering_azalea", "grass_block", "short_grass", "fern", "glow_lichen",
            "hanging_roots", "lily_pad", "sugar_cane", "leaves")
CUTTABLE = WALL_MATS + AIR
NB4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
# The deck's outline is JAGGED, not walled: of its rim runs, 52 are a single cell long, 16 are two,
# and only five reach six or more. So a full bay-and-pier rhythm is only possible on a handful of
# stretches. 4 is the honest threshold - it keeps 11 runs and 70 rim cells, against 44 at 6 - and
# the steps shorter than that stay walled, because a head course over them has nothing to reach.
_MIN_RUN = 3


def build_gallery(cfg: dict, donors=None) -> Canvas:
    p = {**GALLERY, **cfg}
    if not p.get("under"):
        raise ValueError("gallery needs params.under - it cuts holes in a deck that exists")
    ctx = Ctx(p["under"])
    fy, seed = int(p["floor_y"]), int(p["seed"])
    w = World()
    counts = collections.Counter()

    def name(x, y, z):
        return ctx.name_at(x, y, z).split(":")[-1].split("[")[0]

    def cuttable(x, y, z):
        n = name(x, y, z)
        return (n in CUTTABLE or any(k in n for k in PLANTING)) and not is_protected(n)

    def planted(x, z):
        return any(any(k in name(x, fy + q, z) for k in PLANTING)
                   for q in range(sill, sill + 1 + oh))

    def is_wall(x, z):
        """A bay needs a BANK to cut - masonry or planted, but something. Only 17 of this deck's
        163 view-facing rim cells are masonry: the rim is a vegetated bank, not a parapet, so
        requiring stone gave three windows in the whole gallery. What must not happen is cutting
        a frame through a curtain of hanging vine with no bank behind it at all."""
        courses = [name(x, fy + k, z) for k in range(sill, sill + 1 + oh)]
        solid = sum(1 for c in courses
                    if c in WALL_MATS or c in ("moss_block", "dirt", "grass_block",
                                               "mossy_cobblestone", "coarse_dirt"))
        return solid >= 2

    # ---- the deck, and the boundary that faces open air
    floor = _deck(ctx, fy)
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

    # a rim cell only earns a window if there is actually something to LOOK AT: three clear
    # blocks straight out. 81 of the 260 rim columns face another part of the island.
    rim = {}
    rejected = collections.Counter()
    for c in floor:
        d = next((d for d in NB4 if (c[0] + d[0], c[1] + d[1]) in outside), None)
        if d is None:
            continue
        if any(not _air(ctx, c[0] + d[0] * k, fy + 2, c[1] + d[1] * k) for k in (1, 2, 3)):
            continue
        rim[c] = d
    counts["rim_with_view"] = len(rim)
    # ...and only the stretches that are actually WALLED. 25 of the first build's 33 bays cut
    # through planting, three of them through nothing but hanging vine.
    sill, oh = int(p["sill"]), int(p["open_h"])
    for c in list(rim):
        if not is_wall(*c):
            del rim[c]
            rejected["not a wall"] += 1
    counts["rim_walled"] = len(rim)
    counts["rejected_unwalled"] = rejected["not a wall"]

    # ---- walk each straight run of rim so the rhythm follows the WALL, not the compass. Spacing
    # bays by a global grid puts a pier in one corner and half a bay in the next.
    period = int(p["bay"]) + int(p["pier"])
    piers = []
    for run in _runs(rim):
        for i, (c, d) in enumerate(run):
            x, z = c
            if i % period < int(p["bay"]):
                # THE BAY. Cut the opening, leave the sill, cap it, and head it with an arch.
                cut = 0
                for k in range(sill + 1, sill + 1 + oh):
                    if cuttable(x, fy + k, z):
                        w.put(x, fy + k, z, "air")
                        cut += 1
                if not cut:
                    continue
                counts["opened"] += cut
                green = planted(x, z)
                if cuttable(x, fy + sill, z):
                    # a window cut through a MOSSY bank gets a mossy sill. Capping it in stone is
                    # what made the first build read as masonry punched through the planting.
                    if green:
                        w.put(x, fy + sill, z, p["sill_green"])
                        counts["sill_green"] += 1
                    else:
                        w.put(x, fy + sill, z, p["sill_cap"], type="top", waterlogged="false")
                        counts["sill"] += 1
                if p.get("arch") and cuttable(x, fy + sill + oh + 1, z):
                    w.put(x, fy + sill + oh + 1, z, p["jamb"])
                    counts["arch"] += 1
                # the vine hangs from the ARCH above it, not off the wall - the wall is what
                # this bay just removed, so a side-attached vine has nothing left to cling to
                # ...and the greenery comes BACK into the reveal, at a much higher rate where the
                # bank was planted, so the opening is framed by what it was cut out of rather than
                # replacing it. The first build took out 64 vine and 19 moss and gave back 16.
                rate = float(p["vine_rate"]) * (2.0 if green else 1.0)
                if p.get("arch") and hash01(x, z, 3, seed) < rate:
                    if cuttable(x, fy + sill + oh, z):
                        w.put(x, fy + sill + oh, z, p["vine"], up="true", north="false",
                              south="false", east="false", west="false")
                        counts["vine"] += 1
            else:
                piers.append((x, z, d))

    # ---- 2. TIMBER. The piers become wood and a beam ties their heads together. This is the move
    # that puts the deck's 7% wood anywhere near the outside's 23%.
    for n, (x, z, d) in enumerate(piers):
        ok = False
        pier_green = planted(x, z)
        for k in range(sill + 1, sill + 1 + oh):
            if cuttable(x, fy + k, z):
                # a timber post driven through a mossy bank replaces the bank; keep the moss on
                # the outer course and put the post behind it
                w.put(x, fy + k, z, p["moss"] if (pier_green and k == sill + 1) else p["timber"],
                      **({} if (pier_green and k == sill + 1) else {"axis": "y"}))
                ok = True
        if ok:
            counts["pier"] += 1
        if cuttable(x, fy + sill + oh + 1, z):
            w.put(x, fy + sill + oh + 1, z, p["beam"], axis="x" if d[1] else "z")
            counts["beam"] += 1
        if ok and n % max(1, int(p["lamp_every"])) == 0:
            # a lantern hangs from the block ABOVE it, and inboard of the pier there is only room
            # - so the beam is carried one cell in to make a BRACKET, and the lamp hangs off that.
            ix, iz = x - d[0], z - d[1]                 # inboard of the pier, over the floor
            if _air(ctx, ix, fy + sill + oh, iz) and _air(ctx, ix, fy + sill + oh + 1, iz):
                w.put(ix, fy + sill + oh + 1, iz, p["beam"], axis="x" if d[0] else "z")
                w.put(ix, fy + sill + oh, iz, p["lamp"], hanging="true", waterlogged="false")
                counts["lamp"] += 1
                counts["bracket"] += 1

    # ---- 4. THE BASIN. Fully rimmed and floored: this deck hangs in the air and a leak drains
    # into the undercroft, which is the one mistake here that would be a nuisance to undo.
    bx = p.get("basin")
    if bx:
        x1, z1, x2, z2 = (int(v) for v in bx)
        x1, x2 = min(x1, x2), max(x1, x2)
        z1, z2 = min(z1, z2), max(z1, z2)
        clear = all((x, z) in floor and _air(ctx, x, fy + 1, z) and _air(ctx, x, fy + 2, z)
                    for x in range(x1, x2 + 1) for z in range(z1, z2 + 1))
        if clear:
            for x in range(x1, x2 + 1):
                for z in range(z1, z2 + 1):
                    edge = x in (x1, x2) or z in (z1, z2)
                    if edge:
                        w.put(x, fy + 1, z, p["basin_rim"])
                        counts["basin"] += 1
                    else:
                        w.put(x, fy, z, p["basin_floor"])       # a floor it cannot leak through
                        w.put(x, fy + 1, z, p["water"], level="0")
                        counts["basin"] += 2
        else:
            counts["basin_blocked"] = 1

    return w.canvas({"kind": "gallery", "floor_y": fy, "deck_cells": len(floor), **counts})


def _air(ctx, x, y, z):
    return ctx.name_at(x, y, z).split(":")[-1].split("[")[0] in AIR


def _vine_face(d):
    """a vine clings to the face BEHIND it, i.e. the side the wall is on"""
    return {"north": "true" if d == (0, 1) else "false",
            "south": "true" if d == (0, -1) else "false",
            "east": "true" if d == (-1, 0) else "false",
            "west": "true" if d == (1, 0) else "false", "up": "false"}


def _runs(rim: dict):
    """straight runs of rim sharing one outward direction, in order along the wall"""
    out = []
    by_dir = collections.defaultdict(list)
    for c, d in rim.items():
        by_dir[d].append(c)
    for d, cells in by_dir.items():
        along = 1 if d[0] else 0                 # runs go across the outward normal
        lines = collections.defaultdict(list)
        for c in cells:
            lines[c[1 - along]].append(c)
        for _, line in sorted(lines.items()):
            line.sort(key=lambda c: c[along])
            cur = [line[0]]
            for c in line[1:]:
                if c[along] == cur[-1][along] + 1:
                    cur.append(c)
                else:
                    out.append([(q, d) for q in cur])
                    cur = [c]
            out.append([(q, d) for q in cur])
    # a run shorter than one full period cannot alternate, so its bay never meets a pier and the
    # head course over it lands as two or three blocks with nothing to place against. Those short
    # stretches - corners, notches, the odd two-cell ledge - stay walled.
    return [r for r in out if len(r) >= _MIN_RUN]


def _deck(ctx, fy):
    """the biggest connected blob of the floor course - the deck, without a hand-written box"""
    import numpy as np
    m, (ox, oy, oz) = ctx.m, (ctx.ox, ctx.oy, ctx.oz)
    j = fy - oy
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    cells = set()
    layer = m.ids[j]
    for k in range(layer.shape[0]):
        for i in np.nonzero(layer[k])[0]:
            if names[layer[k][i]] not in AIR:
                cells.add((ox + int(i), oz + k))
    seen, best = set(), []
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
                if r in cells and r not in seen:
                    st.append(r)
        if len(cur) > len(best):
            best = cur
    return set(best)
