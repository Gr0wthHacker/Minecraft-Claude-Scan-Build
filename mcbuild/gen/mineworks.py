"""THE MINE WORKS: an ore line, a stamp mill that RUNS, and the dock the ore leaves by.

Jack: *"figure out what we can build that supports the coaster, and is interesting + visual."*

The Frontier's whole interactive inventory, measured over `out/Park Complete.litematic`, is 646
rails, 2 buttons, 2 bells and 2 detector rails - every verb in the land belongs to the coaster.
Six modules stand around it and not one of them is a thing a guest DOES. This is the second half
of the answer to that: a working operation whose parts tie the ride to the town.

    THE ORE LINE   an elevated ore railway on timber trestles, from the ridge's east foot to
                   the dock, crossing the guest walk and the service lane OVER them rather
                   than across them, so a guest walks under it
    THE STAMP MILL a five-head stamp battery a guest FIRES: a button, a pulse, five pistons, a
                   bell and a running lamp. Its contract is asserted by SIMULATION in
                   `tests/test_mineworks.py`, which is the only reason it is allowed to exist
    THE DOCK       a tipple over a stone loading bank beside the park railway, so the story has
                   an end: ore comes out of the mountain, is stamped, and leaves by rail

**THE SITE WAS MEASURED, NOT CHOSEN.** V157-169 is the one long empty corridor in the Frontier -
column-exact off `Park Ways` and `Park Complete`, U0-125 holds 114 blocks in 13 x 126 of lawn,
all of them moss carpet and one fence. It lies between the service lane at V154-156 and the park
railway at V172-187, which is exactly where a works belongs: back of the town, on the railway.

**A POWERED RAIL CANNOT CURVE.** Off the registry rather than off memory: `powered_rail`'s legal
shapes are the six straights and no corner at all. So every direction change on this line is
plain `rail`, and the line is otherwise powered rail because on this server gold is farmable and
iron is not - a powered rail is ~1 gold and a plain rail ~0.375 IRON, so the cheap rail is the
gold one. `tests/test_mineworks.py` asserts the registry fact rather than trusting this comment.

**AN UNPOWERED POWERED RAIL IS A BRAKE**, so every run carries a `redstone_block` in the deck
under it before the chain can die, and the runs are counted BETWEEN CORNERS - a flat spacing
leaves a dead rail past every turn, and a dead rail is a cart that stops in mid-air.

**THE LINE IS LEVEL FOR ITS WHOLE LENGTH.** Not laziness: a curve has no ascending shape either,
so a corner and both its neighbours must share one height, and the surest way to keep that true
on a line with four corners is to have no gradient at all. The height it is level AT is what
makes it read - five courses up, a guest walks under it twice.

**NOTHING HERE DISPENSES A PRIZE**, which is `park_games`' own rule. The stamp battery's output
is motion, a bell and a lamp; a machine whose output is a lamp cannot lose money by accident and
the Assay Office is where a prize is redeemed.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .frontier_builds import PAL, _Lot
from . import circuits

#: The works' own palette. Timber and stone from the land's kit (so the mill reads as the same
#: hand as Boomtown), plus the working blocks a mill needs. Checked in `tests/test_mineworks.py`
#: against `blocks.available`, `blocks.spendable` and `palette.tier`.
WORKS = {
    "plinth": "polished_blackstone_bricks",
    "base": "stone_bricks",
    "base_worn": "cracked_stone_bricks",
    "base_moss": "mossy_stone_bricks",
    "band": "smooth_stone",
    "timber": "spruce_planks",
    "post": "spruce_log",
    "beam": "stripped_spruce_log",
    "roof": "dark_oak_stairs",
    "roof_slab": "dark_oak_slab",
    "roof_field": "dark_oak_planks",
    "fence": "spruce_fence",
    "slab": "spruce_slab",
    "stair": "spruce_stairs",
    "shutter": "spruce_trapdoor",
    "grille": "iron_bars",
    "glass": "glass_pane",
    "lamp": "lantern",
    "glow": "ochre_froglight",
    "sign": "spruce_wall_sign",
    "rock": "cobblestone",
    "rock_b": "andesite",
    "scree": "gravel",
    "ore": "coal_ore",
    "barrel": "barrel",
    # --- the machine ------------------------------------------------------------------
    "stamp": "piston",
    "bell": "bell",
    "button": "stone_button",
    "wire": "redstone_wire",
    "source": "redstone_block",
    "lit": "redstone_lamp",
    "rail": "powered_rail",
    "curve": "rail",
    "detect": "detector_rail",
}

WORKSDEF = {
    "kind": "works",
    "lot": None,
    "at": None,
    "anchor": [97500, 203, 80300],
    "lane": None,          # [v0, v1] - the service lane INSIDE this lot, which nothing may touch
    "walk": None,          # [u0, u1] - the guest cross walk, likewise
    "line_v": 12,          # the ore line's own column, north of the corner
    "line_y": 5,           # ...and its deck height. A guest walks UNDER it twice.
    "spur_v": 2,           # the stub at the ridge's foot
    "corner_u": 86,        # where the stub turns east onto the main run
    "mill": [9, 21, 34, 70],   # v0, v1, u0, u1
    "dock": [9, 21, 8, 30],
    "power_every": 8,
    # **THE ORE LINE IS OFF, AND IT WAS DELETED ON SIGHT.** Jack: "the 2nd strange mining track
    # placement that goes through the building should be deleted." He is right and the fault was
    # mine twice over: the line was routed THROUGH the stamp mill on purpose - ore arriving on a
    # trestle over the stamp floor is what a real mill looks like - and what that reads as from
    # outside is a railway piercing a building's wall five courses up. Worse, the land already has
    # two railways (the coaster and the park line), so a third elevated track is not more industry,
    # it is a third thing to work out.
    #
    # The machinery stays and is correct; point it at a site where the line is not a third railway
    # crossing somebody's roof and turn it on. `tests/test_mineworks.py` skips the line's own
    # assertions when it is off rather than passing them vacuously.
    "line": False,
    "seed": 0,
}


# --------------------------------------------------------------------------- the kit


def _weather(lot: _Lot, v, u, y) -> str:
    r = hash01(v * 7 + 3, u * 13 + 5, y * 29 + 11, lot.seed)
    return "base" if r < 0.74 else ("base_worn" if r < 0.90 else "base_moss")


def _box(lot: _Lot, v0, v1, u0, u1, y0, y1, key):
    for y in range(y0, y1 + 1):
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                lot.put(v, y, u, WORKS[key])


def _walls(lot: _Lot, v0, v1, u0, u1, y0, y1, key, *, weathered=False, skip=()):
    for y in range(y0, y1 + 1):
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if v not in (v0, v1) and u not in (u0, u1):
                    continue
                if (v, u) in skip:
                    continue
                lot.put(v, y, u, WORKS[_weather(lot, v, u, y) if weathered else key])


def _gable(lot: _Lot, v0, v1, u0, u1, y0) -> int:
    """A pitched roof over a box, ridged along U. Every tread leans TOWARD its own ridge - the
    rule `tests/test_stairhead.py` pins, because our renderer draws both directions identically."""
    half = (v1 - v0) // 2
    for i in range(half + 1):
        y = y0 + i
        for u in range(u0, u1 + 1):
            if i == half and (v1 - v0) % 2 == 0:
                lot.slab(v0 + i, y, u, WORKS["roof_slab"], "bottom")
                continue
            lot.stair(v0 + i, y, u, WORKS["roof"], facing="east")
            lot.stair(v1 - i, y, u, WORKS["roof"], facing="west")
        # the gable ends are filled so the roof is not a pair of loose slopes
        for v in (v0 + i, v1 - i):
            for u in (u0, u1):
                for yy in range(y0, y):
                    lot.put(v, yy, u, WORKS["timber"])
    return y0 + half


def _frame(lot: _Lot, v0, v1, u0, u1, y0, y1):
    """Corner posts and a head beam - what turns four walls into a BUILDING."""
    for v in (v0, v1):
        for u in (u0, u1):
            for y in range(y0, y1 + 1):
                lot.log(v, y, u, WORKS["post"], axis="y")
    for v in range(v0, v1 + 1):
        for u in (u0, u1):
            lot.log(v, y1 + 1, u, WORKS["beam"], axis="x")
    for u in range(u0 + 1, u1):
        for v in (v0, v1):
            lot.log(v, y1 + 1, u, WORKS["beam"], axis="z")



# --------------------------------------------------------------------------- circuits, laid


def _parse(spec: str):
    """`"repeater[facing=south,delay=1]"` -> ("repeater", {"facing": "south", "delay": "1"})."""
    if "[" not in spec:
        return spec, {}
    name, rest = spec.split("[", 1)
    props = {}
    for pair in rest.rstrip("]").split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            props[k.strip()] = v.strip()
    return name, props


def _lay(lot: _Lot, mod: dict, *, floor: str | None = None) -> int:
    """Write a `gen/circuits` module's cells into the lot, giving dust a floor where it has none.

    **COMPOSING VERIFIED MODULES DOES NOT GIVE YOU A VERIFIED MACHINE** - the casino's first slot
    was a correct pulse, a correct randomiser and a correct payout with nothing between them. What
    this does is only the writing; the composition is asserted by simulation in
    `tests/test_mineworks.py`, over the cells this actually emitted.
    """
    n = 0
    for (x, y, z), spec in mod["cells"].items():
        name, props = _parse(spec)
        if floor and name in ("redstone_wire", "repeater", "comparator", "redstone_lamp")                 and not lot.has(x, y - 1, z):
            lot.put(x, y - 1, z, floor)
        if lot.put(x, y, z, name, **props):
            n += 1
    return n


# --------------------------------------------------------------------------- the ore line


def _trestle_bent(lot: _Lot, v, u, y_deck, *, skip_v=()):
    """One bent: two legs and a cap. A leg is REFUSED where the ground below it is somebody
    else's - the service lane and the guest walk are crossed, never stood on."""
    if v in skip_v:
        return 0
    n = 0
    for y in range(0, y_deck):
        n += 1 if lot.log(v, y, u, WORKS["post"], axis="y") else 0
    return n


def _line(lot: _Lot, p: dict) -> dict:
    """The ore line: a level elevated railway with four corners and no gradient at all.

    THE DECK IS A SOLID FLOOR AND THE RAIL SITS ON IT, so every rail has something to place
    against and the whole run is one connected piece with the trestles under it. A `redstone_block`
    replaces a deck cell before the power chain can die - counted BETWEEN CORNERS, because a plain
    rail does not propagate the chain and a flat spacing leaves a dead rail past every turn.
    """
    lv, ly = int(p["line_v"]), int(p["line_y"])
    sv = int(p["spur_v"])
    cu = int(p["corner_u"])
    lane = tuple(p.get("lane") or ())
    walk = tuple(p.get("walk") or ())
    du = lot.du
    every = int(p.get("power_every", 8))

    runs = [
        # (kind, fixed, from, to)   'u' runs along U at v=fixed; 'v' runs along V at u=fixed
        ("u", sv, du - 3, cu + 1),               # the stub, north out of the ridge's foot
        ("v", cu, sv + 1, lv - 1),               # east across the lane, on the trestle
        ("u", lv, cu - 1, int(p["dock"][2]) + 2),  # the main run, north to the dock
    ]
    corners = [(sv, cu), (lv, cu)]
    lane_v = set(range(lane[0], lane[1] + 1)) if lane else set()
    walk_u = set(range(walk[0], walk[1] + 1)) if walk else set()

    deck, rails, sources, bents = 0, 0, 0, 0
    cells: list[tuple[int, int]] = []
    for axis, fixed, a, b in runs:
        stepd = 1 if b >= a else -1
        for t in range(a, b + stepd, stepd):
            v, u = (fixed, t) if axis == "u" else (t, fixed)
            cells.append((v, u))
    cells += corners
    seen = set()
    for v, u in cells:
        if (v, u) in seen:
            continue
        seen.add((v, u))
        # the deck, one course under the rail, and a kerb either side so it reads as a bridge
        if lot.put(v, ly - 1, u, WORKS["timber"]):
            deck += 1
    # the rail itself, laid run by run so the power spacing is counted between corners
    corner_set = set(corners)
    for axis, fixed, a, b in runs:
        stepd = 1 if b >= a else -1
        run = [((fixed, t) if axis == "u" else (t, fixed)) for t in range(a, b + stepd, stepd)]
        since = every                       # the first cell of every run is powered
        for v, u in run:
            if (v, u) in corner_set:
                continue
            if since >= every:
                lot.put(v, ly - 1, u, WORKS["source"])
                sources += 1
                since = 0
            lot.put(v, ly, u, WORKS["rail"],
                    shape="north_south" if axis == "u" else "east_west", powered="false",
                    waterlogged="false")
            rails += 1
            since += 1
    # A CORNER IS PLAIN RAIL, because a powered rail has no corner shape in the registry at all.
    for i, (v, u) in enumerate(corners):
        shape = "south_east" if i == 0 else "north_west"
        lot.put(v, ly, u, WORKS["curve"], shape=shape, waterlogged="false")
        lot.put(v, ly - 1, u, WORKS["timber"])
        rails += 1
    # **INSIDE THE MILL THE BUILDING CARRIES THE LINE**, so no bent and no handrail goes there.
    # Without this the handrail runs down the mill's own interior at v11 and v13 - and v11 is the
    # drive column, so it overwrote two courses of the battery's climb and the machine simulated
    # as dead. The line is generated FIRST for the same reason: where the two want one cell, the
    # thing with a circuit in it wins.
    mv0, mv1, mu0, mu1 = (int(x) for x in p["mill"])

    def indoors(v, u):
        return mv0 <= v <= mv1 and mu0 <= u <= mu1

    for v, u in sorted(seen):                               # the bents, every third cell
        if (v + u) % 3 or v in lane_v or u in walk_u or indoors(v, u):
            continue
        bents += 1 if _trestle_bent(lot, v, u, ly - 1) else 0
        for s in (-1, 1):                                   # a brace, so a bent is not a post
            lot.log(v, ly - 2, u + s, WORKS["beam"], axis="z")
    for v, u in sorted(seen):                               # the handrail
        for s in (-1, 1):
            a, b = (v + s, u)
            if (a, b) in seen or indoors(a, b) or lot.has(a, ly, b):
                continue
            lot.fence(a, ly, b, "u", key=WORKS["fence"])
    return {"rails": rails, "deck": deck, "sources": sources, "bents": bents,
            "corners": [list(c) for c in corners], "cells": len(seen),
            "contract": f"a level line, every corner plain rail, a source every {every} "
                        f"within a run, and no leg in the lane or the walk"}


# --------------------------------------------------------------------------- the stamp mill


def _mill(lot: _Lot, p: dict) -> dict:
    """A five-head stamp battery in a stepped timber mill, and a guest can work it.

    IT STEPS DOWN THE WAY THE ORE TRAVELS - bin, battery, tables - because that is what gravity
    feeding looks like and because three masses of three heights are a silhouette where one box
    of one height is a shed. The line arrives at the TOP of the first step.

    THE MACHINE FACES THE LANE, which is the side a guest walks. A stamp battery inside a closed
    shed is a rumour; the whole west bay of the middle step is open, framed, and lit.
    """
    v0, v1, u0, u1 = (int(x) for x in p["mill"])
    ly = int(p["line_y"])
    out: dict = {}

    # ---- the plinth: one battered stone base under all three steps ---------------------
    for y in range(0, 3):
        _box(lot, v0 + (y // 2), v1 - (y // 2), u0 + (y // 2), u1 - (y // 2), y, y, "base")
    for v in range(v0, v1 + 1):
        for u in (u0, u1):
            lot.put(v, 0, u, WORKS["plinth"])
    for u in range(u0, u1 + 1):
        for v in (v0, v1):
            lot.put(v, 0, u, WORKS["plinth"])

    # ---- three steps, north (high) to south (low) --------------------------------------
    span = (u1 - u0 + 1) // 3
    # **THE STEPS ARE TALLER THAN A SHED AND THAT IS THE WHOLE POINT.** Measured, 3.8% of the
    # Frontier stands over twenty courses and exactly two things break twenty-five; a works that
    # tops out at fifteen is a seventh building rather than a second landmark.
    steps = [("bin", u0, u0 + span - 1, ly + 14),
             ("battery", u0 + span, u0 + 2 * span - 1, ly + 8),
             ("tables", u0 + 2 * span, u1, ly + 3)]
    for name, a, b, top in steps:
        _walls(lot, v0, v1, a, b, 3, top, "timber", weathered=False)
        _frame(lot, v0, v1, a, b, 3, top)
        out[name + "_top"] = _gable(lot, v0, v1, a, b, top + 2)
        for u in range(a + 2, b - 1, 3):                    # glazing, so it is not a blank wall
            for y in (top - 2, top - 3):
                lot.pane(v1, y, u, WORKS["glass"], along="u")
    out["steps"] = [[n, a, b, t] for n, a, b, t in steps]

    # ---- the machine bay: the west face of the middle step, open and framed -------------
    ba, bb = steps[1][1], steps[1][2]
    bay = (ba + 1, bb - 1)
    for u in range(bay[0], bay[1] + 1):
        for y in range(3, steps[1][3] - 1):
            lot.c.put(v0, y, u, 0)
    for u in (bay[0] - 1, bay[1] + 1):                      # the bay's own jambs
        for y in range(3, steps[1][3]):
            lot.log(v0, y, u, WORKS["post"], axis="y")
    for u in range(bay[0] - 1, bay[1] + 2):
        lot.log(v0, steps[1][3] - 1, u, WORKS["beam"], axis="z")

    out["machine"] = _battery(lot, v0, bay, p)

    # ---- the ore bin: the line arrives on top of the north step -------------------------
    for u in range(u0 + 1, u0 + span - 1):
        for v in range(v0 + 2, v1 - 1):
            lot.put(v, ly + 8, u, WORKS["shutter"], facing="north", half="top", open="true",
                    powered="false", waterlogged="false")
    for u in range(u0 + 2, u0 + span - 2, 2):
        lot.put(v1 - 1, 4, u, WORKS["barrel"], facing="up", open="false")

    # ---- the launder out of the south step, down to the tables --------------------------
    # **A LAUNDER IS A TROUGH ON TRESTLES, AND THE TRESTLES ARE THE POINT.** Built as two beams
    # and a slab it came out as two free-floating six-cell fragments - it has no wall to hang off
    # in the middle of a room, and a chute with nothing under it is exactly the class of stray
    # this project's component count exists to catch.
    for k, u in enumerate(range(u1 - 6, u1 + 1)):
        y = 6 - k // 2
        for v in (v0 + 3, v0 + 5):
            lot.log(v, y, u, WORKS["beam"], axis="z")
            if k % 3 == 0:
                for yy in range(3, y):
                    lot.log(v, yy, u, WORKS["post"], axis="y")
        lot.slab(v0 + 4, y, u, WORKS["slab"], "bottom")
    out["launder"] = [v0 + 4, u1 - 6, u1]

    # ---- names, and the one lamp that says the mill is lit ------------------------------
    # **THE SIGN GOES ON A COLUMN THAT HAS A WALL IN IT.** The mill's midpoint is the open
    # machine bay, and a wall sign hung there floats: this park has already shipped four kinds
    # with a sign on the one column of a wall that has an opening in it, and it is invisible in
    # every render because a sign in air draws exactly like a sign on a wall. `_Lot.sign` refuses
    # it, so the failure is a missing sign rather than a floating one - which is why the count is
    # returned and asserted.
    signs = 0
    if lot.sign(v0 - 1, 6, u0 + 3, "west", ["THE STAMP MILL", "five heads",
                                            "press to run", "ore from the adit"]):
        signs += 1
    if lot.sign(v0 - 1, 6, u1 - 3, "west", ["ORE FROM THE", "ADIT No.1", "stamped here",
                                            "shipped by rail"]):
        signs += 1
    for u in range(u0 + 3, u1, 6):
        lot.hang(v0 - 1, 4, u)
    # **A TOWN IS MASONRY AND A FAIRGROUND IS CANVAS**, and this land already learned it once:
    # measured on its first build the whole Frontier ran 0.0-2.6% coloured or lit blocks, which is
    # a correct way to build a village and the wrong way to build an attraction. The mill gets the
    # land's own two-tone awning down the face a guest walks, and a painted name board over it -
    # `red_wool` 65 against `white_wool` 236 is 171 points of luminance, the biggest cheap step
    # this economy has.
    # **AN AWNING BELONGS TO A STEP, NOT TO A BUILDING.** Run at one height across all three it
    # had no wall behind it over two of them and shipped as floating wool - and `wool` has no slab
    # in the game either, which the state audit caught as thirty-three illegal blocks. Each step
    # gets its own, one course under its own eave, and every cell is checked against the wall it
    # hangs off.
    awning = 0
    for _name, a, b, top in steps:
        for k, u in enumerate(range(a + 1, b)):
            if not lot.has(v0, top - 1, u):
                continue
            if lot.put(v0 - 1, top - 1, u, "canvas_a" if (k // 2) % 2 else "canvas_b"):
                awning += 1
    for u in range(u0 + 3, u0 + 10):                  # the painted name board over the bin step
        if lot.has(v0, steps[0][3], u):
            lot.put(v0 - 1, steps[0][3], u, "board")
            lot.put(v0 - 1, steps[0][3] + 1, u, "paint")
    out["awning"] = awning
    out["signs"] = signs
    return out


def _battery(lot: _Lot, v0, bay, p: dict) -> dict:
    """The stamp battery, and the circuit that fires it.

    **A HELD INPUT MUST BECOME AN EDGE BEFORE IT TRAVELS**, which is the casino's most expensive
    lesson: `circuits.pulse` is the standard AND-NOT monostable, so a button held down still
    yields exactly one stroke. Without it a guest leaning on the button runs the mill for ever.

    **THE MACHINE COURSE IS CARVED OUT OF THE MILL'S OWN PLINTH**, at y2, and the control chain
    runs NORTH under the ore-bin step. That is not a style choice, it is the only place it fits:
    laid along the machine bay the chain is longer than the bay, and the first build put the boost
    two cells past the pulse's output and the drive line past the end of the bay - so the run was
    broken in two places and the machine simulated as doing nothing at all, exactly the failure
    this whole file exists to catch before it is placed.

    **NO BOOST.** A comparator in subtract mode outputs a computed level, and with the side dark
    that level is the full 15 - so the pulse's own output already travels. A boost here was one
    more module to get adjacent, and it was the one that was not.

    **AN ANALOG VALUE CANNOT TRAVEL, SO NOTHING ANALOG DOES.** Only a boolean climbs; the pistons,
    the bell and the lamp all want on or off.

    The stamps are `piston[facing=down]` over a mortar box: the head drops, which is what a stamp
    battery DOES, and it is the only mechanism in this land that visibly moves.
    """
    a, b = bay
    y_head = 7
    y_mach = 2
    drive_v = v0 + 2
    pist_v = v0 + 1
    n = max(3, min(5, (b - a) // 2))
    heads = [(pist_v, a + 1 + i * 2) for i in range(n)]

    # the mortar box the heads drop into, and the beams they hang from
    for v in range(v0 + 1, v0 + 4):
        for u in range(a, b + 1):
            lot.put(v, 3, u, WORKS["rock"])
            lot.put(v, 4, u, WORKS["scree"] if hash01(v, u, lot.seed) < 0.4 else WORKS["ore"])
    for u in range(a - 1, b + 2):
        lot.log(pist_v, y_head + 1, u, WORKS["beam"], axis="z")
        lot.log(drive_v + 1, y_head + 1, u, WORKS["beam"], axis="z")

    # ---- the control chain, in a course carved out of the plinth ----------------------
    mu = a - 1
    # CLAMPED TO THE MILL'S OWN FOOTPRINT: the chain is twelve cells long and the ore-bin step is
    # twelve, so an unclamped carve lays the machine course's lid out on the open lawn.
    mu0 = int(p["mill"][2])
    for u in range(max(mu0, mu - 12), b + 3):        # carve the machine course, keep y0-1 solid
        for v in range(drive_v - 1, drive_v + 3):
            lot.c.put(v, y_mach, u, 0)
    for u in range(max(mu0, mu - 12), b + 3):        # ...and put its lid back on
        for v in range(drive_v - 1, drive_v + 3):
            lot.put(v, y_mach + 1, u, WORKS["timber"])

    lot.c.put(drive_v, y_mach + 1, mu, 0)
    lot.put(drive_v, y_mach + 1, mu, WORKS["band"])                  # the console pad
    lot.put(drive_v, y_mach + 2, mu, WORKS["button"], face="floor", facing="south",
            powered="false")
    lot.put(drive_v, y_mach, mu, WORKS["wire"])                      # under it: the button's out

    pulse = circuits.pulse((drive_v, y_mach, mu - 1), length=3, facing="north")
    laid = _lay(lot, pulse, floor=WORKS["base"])

    # **THE CLIMB RUNS IN ITS OWN COLUMN, ONE CELL OFF THE DRIVE LINE**, and that is a fix rather
    # than a preference. Climbing in the drive's own column puts the staircase's second-from-top
    # DUST directly under the drive line's first cell - so the repeater there stands on redstone
    # dust, which is not a placement the game allows and which the model resolved by feeding the
    # whole staircase backwards: measured, the levels rose from 9 at the comparator to 14 at the
    # top, and the battery latched on for as long as the button was held. A machine that fires for
    # ever is the one failure a park must not ship, and nothing but the simulator could see it.
    # ...**AND IT STEPS ACROSS ONE CELL PAST THE COMPARATOR, NOT BESIDE IT.** The pulse's delay
    # leg runs on that same flank and ends one cell off the comparator's own output; a step-across
    # laid level with the output touches it, and fifteen goes straight round the gate into the
    # climb. Measured, the battery latched on for as long as the button was held and every module
    # in the chain was individually correct - which is this file's own rule about composing
    # verified modules, met a third time.
    climb_v = drive_v + 1
    ou = pulse["out"][2] - 1
    lot.put(drive_v, y_mach, ou, WORKS["wire"])                    # the output, one cell on
    lot.put(climb_v, y_mach, ou, WORKS["wire"])                    # ...and the step across
    climb = circuits.climb((climb_v, y_mach, ou), (climb_v, y_head, ou),
                           block=WORKS["base"], facing="north")
    for (cx, cy, cz) in list(climb["cells"]):                      # the shaft it rises through
        for yy in range(cy, y_head + 1):
            lot.c.put(cx, yy, cz, 0)
    laid += _lay(lot, climb)

    # the drive line: dust along the heads' own course, one cell behind them, with a repeater
    # before the signal would die. **WIRE DIES AT 15** and this run is over twenty cells; what
    # arrives off a five-course climb is about eight, so the FIRST repeater is the one that
    # restores it and the spacing is counted from there rather than from the climb.
    top = climb["top"]
    drive = []
    for k, u in enumerate(range(top[2], b + 2)):
        lot.c.put(drive_v, y_head, u, 0)
        if not lot.has(drive_v, y_head - 1, u):
            lot.put(drive_v, y_head - 1, u, WORKS["timber"])
        if k and (k - 1) % 13 == 0:
            lot.put(drive_v, y_head, u, "repeater", facing="south", delay="1",
                    locked="false", powered="false")
        else:
            lot.put(drive_v, y_head, u, WORKS["wire"])
        drive.append((drive_v, y_head, u))

    for hv, hu in heads:                             # the heads, adjacent to the drive line
        for yy in range(5, y_head + 1):
            lot.c.put(hv, yy, hu, 0)
        lot.put(hv, y_head, hu, WORKS["stamp"], facing="down", extended="false")

    # the bell and the running lamp, at the far end where a guest sees both from the bay
    bell = (pist_v, y_head, b + 1)
    lot.c.put(bell[0], bell[1], bell[2], 0)
    lot.put(bell[0], bell[1], bell[2], WORKS["bell"], facing="west",
            attachment="single_wall", powered="false")
    lamp = (drive_v + 1, y_head, b + 1)
    lot.c.put(lamp[0], lamp[1], lamp[2], 0)
    lot.put(lamp[0], lamp[1], lamp[2], WORKS["lit"], lit="false")

    return {"heads": [[v, y_head, u] for v, u in heads], "drive_v": drive_v,
            "button": [drive_v, y_mach + 2, mu], "bell": list(bell), "lamp": list(lamp),
            "n": n, "laid": laid, "drive": [list(d) for d in drive],
            "contract": (f"one press - however long it is held - drops all {n} heads once, rings "
                         "the bell and lights the running lamp, and the battery resets")}


# --------------------------------------------------------------------------- the dock


def _dock(lot: _Lot, p: dict) -> dict:
    """A tipple over a stone loading bank, beside the park railway.

    THE STORY HAS TO HAVE AN END. Ore out of the mountain, stamped in the mill, and then nothing
    is a works with no purpose; a dock on the railway is where it goes, and the railway is
    already built and running past this corridor at V172-187.
    """
    v0, v1, u0, u1 = (int(x) for x in p["dock"])
    ly = int(p["line_y"])
    # **THE BANK IS BATTERED, AND THE KERB GOES ON WHAT THE BATTER LEAVES.** Written as a kerb
    # along the OUTER line of a battered platform it stood a course above nothing - thirteen
    # cells of plinth floating over the step below, and the four lamps beside it likewise. A
    # course that steps IN has to be trimmed with the course that is actually under it.
    for y in range(0, 3):
        _box(lot, v0 + y, v1, u0 + y, u1 - y, y, y, "base")
    for v in range(v0 + 2, v1 + 1):
        lot.put(v, 2, u0 + 2, WORKS["plinth"])
        lot.put(v, 2, u1 - 2, WORKS["plinth"])
    for u in range(u0 + 2, u1 - 1):
        lot.put(v0 + 2, 2, u, WORKS["plinth"])
    # the tipple: a timber tower over the line, with chutes down to the bank
    tv, tu = int(p["line_v"]), (u0 + u1) // 2
    for s in (-2, 2):
        for y in range(0, ly + 6):
            lot.log(tv + s, y, tu - 2, WORKS["post"], axis="y")
            lot.log(tv + s, y, tu + 2, WORKS["post"], axis="y")
    for v in range(tv - 2, tv + 3):
        for u in (tu - 2, tu + 2):
            lot.log(v, ly + 6, u, WORKS["beam"], axis="x")
    for u in range(tu - 2, tu + 3):
        for v in (tv - 2, tv + 2):
            lot.log(v, ly + 6, u, WORKS["beam"], axis="z")
    _gable(lot, tv - 2, tv + 2, tu - 2, tu + 2, ly + 7)
    # the chute: shutters falling from the deck to the bank
    for k in range(4):
        lot.put(tv - 3 - k // 2, ly - 2 - k, tu, WORKS["shutter"], facing="east", half="top",
                open="true", powered="false", waterlogged="false")
    # A DETECTOR RAIL WITH NO LINE ON IT IS A RAIL IN A ROOF. It was the tipple's own trip - a
    # cart running under it rang the bell - and with the line gone there is nothing to trip it, so
    # it is not placed. The bell stays: it hangs in the tipple and a guest can ring it.
    if p.get("line"):
        lot.put(tv, ly, tu, WORKS["detect"], shape="north_south", powered="false",
                waterlogged="false")
    lot.put(tv, ly + 1, tu, WORKS["bell"], facing="west", attachment="ceiling", powered="false")
    # ...and the dock's goes on the tipple's own leg, which is the only vertical face it has:
    # its bank is three courses of platform and a sign wants a wall.
    signs = 1 if lot.sign(tv - 3, 4, tu - 2, "west",
                          ["ORE DOCK", "loads for the", "frontier line"]) else 0
    # THE LAMPS ARE SET FLUSH IN THE BANK'S OWN TOP COURSE, which is Jack's idiom on this island
    # and the one light nobody can knock off a loading platform. Flush means it IS the floor: the
    # cell it replaces is solid, so it can never be the stray a lamp standing on air becomes.
    for u in range(u0 + 3, u1 - 2, 5):
        lot.put(v0 + 3, 2, u, WORKS["glow"])
    return {"bank": [v0, v1, u0, u1], "tipple": [tv, tu], "signs": signs}


# --------------------------------------------------------------------------- entry point


KINDS = {"works": None}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**WORKSDEF, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the mine works needs its measured lot: lot: [dv, du]")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    c = Canvas(dv, int(p.get("sy") or 40), du, donors)
    lot = _Lot(c, dv, du, seed=int(p.get("seed", 0)))

    # ORDER IS SIGNIFICANT AND IT IS THE CIRCUIT THAT DECIDES IT. The line is laid first so that
    # anywhere the mill wants a cell the line also wants, the mill - which has a machine in it -
    # wins. Built the other way round the line's handrail cut two courses out of the battery's
    # climb and the whole mill simulated as dead while auditing perfectly clean.
    parts = {}
    if p.get("line"):
        parts["line"] = _line(lot, p)
    parts["mill"] = _mill(lot, p)
    parts["dock"] = _dock(lot, p)

    av, ay, au = (int(v) for v in p["anchor"])
    at_v, at_u = (int(v) for v in (p.get("at") or (0, 0)))
    c.world_origin = (av + at_v, ay, au + at_u)
    c.meta = {
        "kind": "mine_works",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "frontier",
        "facing": "west",
        "profile_axis": "u",
        "signs": lot.signs,
        "refused": lot.refused,
        "parts": parts,
        "contract": (
            "an ore line whose every corner is plain rail and whose every powered run carries a "
            "source before the chain dies, level for its whole length, with no trestle leg in "
            "the service lane or the guest walk; a stamp mill whose battery fires once per "
            "press however long the button is held; and a dock on the park railway"),
    }
    return c
