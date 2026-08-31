"""MORE RIDES: the park was "single small structures... some infrastructure and some huts", and
scale plus real mechanics is the fix. Nine kinds, three per land, and every one that CAN function
as a ride, mechanism or walkable route DOES - vanilla Minecraft cannot fake a moving structure, so
where this file claims a ride it is a rail circuit, a body of real water, or a flood-fill-proven
walkable route, never a static prop shaped like one. That is this project's cardinal sin, paid for
twice already: the log flume that shipped 564 water SOURCE blocks and never carried a rider, and
the coaster whose first platform was walled off from its own track.

    swings           midway   architecture - a chairoplane tower, chains swung out, no mechanism
    teacups          midway   RIDE - a rectangular minecart loop rings the stationary cups
    arcade           midway   architecture - an open pavilion
    runawaymine      frontier RIDE - a minecart loop out of the station shed and back
    shootinggallery  frontier architecture - a false-fronted range
    riverboat        frontier RIDE-ADJACENT - moored on real still water, a walkable gangway
    ghosttrain       hollow   RIDE - a minecart loop through a dark interior, in one door, out another
    mirrormaze       hollow   WALKTHROUGH - a real maze: one solved route, real branches, real dead ends
    chapel           hollow   architecture - a ruin, regular and ordered, never a jagged pile

**THE RAIL RULES, from `railspiral.py`'s own hard-won notes, restated because getting any one of
them wrong ships a schematic that passes every check here and does not connect in the world:**

    powered_rail CANNOT CURVE (blocks.json: no south_east/south_west/north_west/north_east for
    it) - every direction change is a plain `rail`, and iron is the scarce metal on this server,
    so every corner is a cost that gets counted.
    AN UNPOWERED powered_rail IS A BRAKE - a redstone_block sits in the bed roughly every 8 cells,
    counted per RUN BETWEEN CORNERS, because a corner does not carry the signal chain.
    NEVER DESCEND INTO A CORNER - not used here at all: every circuit in this file is FLAT, which
    sidesteps the grading rules `coaster.py` needs entirely and keeps a minecart loop's geometry
    to what actually matters for these three rides - closed, powered, and reachable.
    A CART AT REST LAUNCHES AWAY FROM AN ADJACENT SOLID BLOCK - moot here too: every circuit is a
    CLOSED LOOP with no free end, so there is no terminus to stop at and nothing to launch from.

`coaster.py` already solved closed-circuit corner detection, rail shaping and per-run power
placement for exactly this kind of loop (`_corners`, `_shapes`, `_power`) - reused here rather
than re-derived, which is the one-source rule this repo keeps re-learning the hard way.

**GEOMETRY**, identical to every other park file because a facing bug is invisible in every
render this repo owns:

    at(i, d, h) = (x - dx*d + sx*i, y + h, z - dz*d + sz*i)

**THE ECONOMY.** Every block this file adds beyond `park.LANDS` is in `EXTRA` below, and every one
was checked against `blocks.available`, `blocks.spendable` and `palette.tier` before being written
down - all cheap or ok, nothing is dirt/grass/podzol/mud (currency), nothing falls, nothing is
`item_frame`/`armor_stand`/`minecart`/`chain` (none are on this server's 1.19 allowlist - the
vertical member is `iron_chain`, which is).
"""
from __future__ import annotations

import math

from .. import blocks
from .canvas import Canvas, hash01
from .coaster import _corners as _loop_corners, _power as _loop_power, _shapes as _loop_shapes
from .park import (LANDS, ROOM_H, SIGN_WIDTH, _Frame, _LEAN, _STEP,
                    _cornice, _crenellate, _hang_light, _pad, _sign, _trim_run, _walls)
from .vertical import Ctx, World

# Extras beyond a land's own palette. Checked against blocks.spendable / blocks.available /
# palette.tier before being written down - every one cheap or ok on this server.
EXTRA = {
    "midway": {"rock": "stone", "rock_stair": "stone_stairs", "aged": "andesite",
               "bark": "stripped_oak_log", "trap": "oak_trapdoor"},
    "frontier": {"rock": "cobblestone", "rock_stair": "cobblestone_stairs", "aged": "mossy_cobblestone",
                 "bark": "stripped_spruce_log", "trap": "spruce_trapdoor"},
    "hollow": {"rock": "cobbled_deepslate", "rock_stair": "cobbled_deepslate_stairs",
               "aged": "polished_blackstone", "bark": "stripped_dark_oak_log",
               "trap": "dark_oak_trapdoor"},
}

# The sixteen cheap wools `bigwheel.py` already validated - gondola colour, seat colour, cup
# colour, anything that wants a saturated pop against a land's own stone.
BRIGHT = ["red_wool", "yellow_wool", "light_blue_wool", "lime_wool", "orange_wool",
          "magenta_wool", "cyan_wool", "pink_wool", "purple_wool", "white_wool",
          "blue_wool", "green_wool"]

ATTRACTIONS = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "swings",
    "facing": "east",
    "land": "midway",
    "title": None,
    "lines": None,
    "min_run": 3,
    "sign": True,
    "seed": 0,
    # sizing knobs - each kind floors its own default rather than sharing one number, exactly the
    # trap `bigwheel.py`'s own notes describe: one shared default is right for one kind and wrong
    # for every other.
    "diameter": None,
    "width": None,
    "depth": None,
    "height": None,
    "seats": 10,
    "cups": 6,
    "maze_w": 7,
    "maze_d": 6,
    "power_every": 8,
}


# ---------------------------------------------------------------------------- shared geometry

def _pal(p):
    return LANDS[p["land"]], EXTRA[p["land"]]


def _member(w, x, y, z, name, axis):
    """Place a block that MAY carry an `axis` - only if the registry says it has one.

    A land's `post` is not always a log: the Hollow's is `blackstone`, which has no `axis`
    property at all, so passing one unconditionally is an illegal state on exactly one of the
    three lands - `frontiertown._timber` paid for this once already and it applies here too,
    to every raking member (a headframe leg, a hoist chain, a paddle-wheel spoke).
    """
    props = blocks.props(name)
    kw = {}
    if "axis" in props:
        kw["axis"] = axis
    if "waterlogged" in props:
        kw["waterlogged"] = "false"
    w.put(x, y, z, name, **kw)


def _full(w: World, x, y, z) -> bool:
    """A FULL CUBE, not merely `w.has`. A lantern hangs from one, a sign is fixed to one - `has`
    is true for a fence, a stair or a pane, none of which hold up either."""
    n = w.name(x, y, z)
    return bool(n) and blocks.is_full_cube(n)


def _lamp(w, x, y, z, light) -> bool:
    """A lantern that decides for itself whether it stands or hangs, from the world - not from
    the caller's memory of what it built. `park.py`'s own plaza shipped `hanging=true` on all
    three lands once for exactly the inverse of this reason."""
    if w.has(x, y, z):
        return False
    if _full(w, x, y - 1, z):
        w.put(x, y, z, light, hanging="false", waterlogged="false")
        return True
    if _full(w, x, y + 1, z):
        w.put(x, y, z, light, hanging="true", waterlogged="false")
        return True
    return False


def _disc(R):
    return [(a, b) for a in range(-R, R + 1) for b in range(-R, R + 1) if a * a + b * b <= R * R]


def _annulus(R, thick=2.0):
    lo = (R - thick) ** 2
    return [(a, b) for a in range(-R, R + 1) for b in range(-R, R + 1)
            if lo < a * a + b * b <= R * R]


def _wedge(a, b, n=12):
    th = math.atan2(b, a)
    return int(((th + math.pi) / (2 * math.pi)) * n) % n


def _ground(w, f, pal, cells, block=None, alt=None, h=-1):
    """A checkered pad under an arbitrary (i, d) footprint - VOID plot, every kind brings its
    own floor. Checkered on WORLD coordinates so two adjacent kinds line up rather than seaming."""
    n = 0
    for (i, d) in cells:
        x, y, z = f.at(i, d, h)
        w.put(x, y, z, (block or pal["ground"]) if (x + z) % 2 == 0 else (alt or pal["path"]))
        n += 1
    return n


def _ortho_path(p0, p1):
    """A 6-CONNECTED path between two points, one axis per step, greedily along whichever
    remaining delta is largest. Every consecutive pair differs by exactly one coordinate by one
    cell - the ear-tip lesson: a diagonal step is not connectivity."""
    x, y, z = p0
    x1, y1, z1 = p1
    cells = [(x, y, z)]
    while (x, y, z) != (x1, y1, z1):
        dx, dy, dz = x1 - x, y1 - y, z1 - z
        if abs(dy) >= abs(dx) and abs(dy) >= abs(dz) and dy != 0:
            y += 1 if dy > 0 else -1
        elif abs(dx) >= abs(dz) and dx != 0:
            x += 1 if dx > 0 else -1
        else:
            z += 1 if dz > 0 else -1
        cells.append((x, y, z))
    return cells


def _chain_path(w, p0, p1, block="iron_chain"):
    """A chain (or any axis-bearing member, including a plain post with no axis at all) laid
    along `_ortho_path`, each cell's `axis` taken from the step that reaches it - so a chain that
    runs briefly sideways is legibly sideways rather than every link defaulting to `y`."""
    cells = _ortho_path(p0, p1)
    n = len(cells)
    for k in range(n):
        x, y, z = cells[k]
        rx, ry, rz = cells[k + 1] if k + 1 < n else cells[k - 1]
        axis = "y" if ry != y else ("x" if rx != x else "z")
        _member(w, x, y, z, block, axis)
    return cells


def _rect_loop_local(i0, i1, d0, d1):
    """A closed rectangle perimeter in (i, d), no duplicated endpoint - the exact convention
    `coaster._corners(pts, closed=True)` expects. Always starts on a true corner, which is what
    lets `coaster._power`'s linear run-scan treat the cyclic seam correctly without ever wrapping
    a run across it."""
    pts = []
    for d in range(d0, d1 + 1):
        pts.append((i0, d))
    for i in range(i0 + 1, i1 + 1):
        pts.append((i, d1))
    for d in range(d1 - 1, d0 - 1, -1):
        pts.append((i1, d))
    for i in range(i1 - 1, i0, -1):
        pts.append((i, d0))
    return pts


def _lay_loop(w, f, pal, pts, h, power_every=8, deck=None):
    """A CLOSED, FLAT minecart loop: rail on top, bed (or a redstone_block) underneath. Reuses
    `coaster.py`'s own closed-circuit corner/shape/power logic rather than re-deriving it - one
    source for what a corner is, so this file and the coaster cannot quietly disagree about it.

    FLAT ON PURPOSE: none of these three rides needs a grade, and skipping it sidesteps the whole
    "never descend into a corner" class of bug - there is nothing to get wrong.
    """
    corners = _loop_corners(pts, True)
    cells = [f.at(i, d, h) for (i, d) in pts]
    shapes = _loop_shapes(cells, corners, True)
    powered = _loop_power(len(pts), corners, power_every)
    deckmat = deck or pal["path"]
    for j, (x, y, z) in enumerate(cells):
        w.put(x, y - 1, z, "redstone_block" if j in powered else deckmat)
        w.put(x, y, z, "rail" if j in corners else "powered_rail", shape=shapes[j])
    return {"cells": cells, "corners": corners, "powered": powered, "track": len(cells)}


# ---------------------------------------------------------------------------- 1. swings (midway)

def _swings(w: World, p: dict, ctx) -> dict:
    """A CHAIROPLANE. ARCHITECTURE, NOT A RIDE - vanilla has no way to spin a structure, so this
    is the silhouette a swing ride reads as: a central tower, a flat canopy, chains swung out on
    the diagonal to seats at a lower radius. Every seat's chain is 6-connected all the way to the
    canopy, which is the one thing that would otherwise ship as `ncar` floating boxes.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    R_seat = max(9, int(p["diameter"] or 26) // 2)
    R_crown = 5
    H_shaft = 13
    n_seats = max(6, int(p["seats"]))
    drop = 7                        # how far below the crown a swung seat hangs

    footprint = [(a, b) for a in range(-R_seat - 2, R_seat + 3)
                 for b in range(-R_seat - 2, R_seat + 3)]
    _ground(w, f, pal, footprint)

    # THE SHAFT, a 3x3 post standing to the crown.
    for h in range(H_shaft):
        for (a, b) in _disc(1):
            w.put(*f.at(a, b, h), pal["post"])

    # THE CROWN: a filled disc roof, alternating wedge colour, with a trim lip underneath so it
    # reads as a canopy rather than a plate, and a finial on top.
    ca, cb = pal["canopy"]
    for (a, b) in _disc(R_crown):
        w.put(*f.at(a, b, H_shaft - 1), pal["trim"])
        w.put(*f.at(a, b, H_shaft), ca if _wedge(a, b, 12) % 2 == 0 else cb)
    w.put(*f.at(0, 0, H_shaft + 1), "end_rod", facing="up")

    # THE CHAINS AND SEATS, swung out on the diagonal from the crown's rim to a seat ring.
    seats, lamps = 0, 0
    for m in range(n_seats):
        th = 2 * math.pi * m / n_seats
        ca_i, ca_b = (round((R_crown - 1) * math.cos(th)), round((R_crown - 1) * math.sin(th)))
        se_i, se_b = (round(R_seat * math.cos(th)), round(R_seat * math.sin(th)))
        top = f.at(ca_i, ca_b, H_shaft - 1)
        bot = f.at(se_i, se_b, H_shaft - drop)
        chain = _chain_path(w, top, bot, "iron_chain")
        seat_pos = chain[-1]
        seat_below = (seat_pos[0], seat_pos[1] - 1, seat_pos[2])
        colour = BRIGHT[int(hash01(m, R_seat, f.x, f.z) * len(BRIGHT))]
        w.put(*seat_below, colour)
        # a backrest, one cell further out, tall side toward the rider (the centre)
        back_i, back_b = (round((R_seat + 1) * math.cos(th)), round((R_seat + 1) * math.sin(th)))
        back = f.at(back_i, back_b, H_shaft - drop)
        w.put(*back, colour)
        if _lamp(w, *f.at(se_i, se_b, H_shaft - drop - 2), pal["light"]):
            lamps += 1
        seats += 1

    # BOARDING PLATFORM: a fenced ring with a gap at the front (negative d - the +facing side,
    # where a visitor stands per the geometry convention), and two lit entrance posts.
    ring_r = R_seat - 2
    gate_span = 2
    for (a, b) in _annulus(ring_r, 1.4):
        if abs(a) <= gate_span and b < 0:
            continue                            # the boarding gap
        w.put(*f.at(a, b, 0), pal["fence"])
    gate_b = -ring_r
    for i in (-gate_span - 1, gate_span + 1):
        for h in range(3):
            w.put(*f.at(i, gate_b, h), pal["post"])
        w.put(*f.at(i, gate_b, 3), pal["trim"])
        _lamp(w, *f.at(i, gate_b, 4), pal["light"])

    # THE SIGN sits one cell further out than its post (per the geometry convention: a sign
    # hangs in the cell IN FRONT of its wall), facing `f.facing` so the support is the post
    # behind it in the +facing direction.
    title = str(p.get("title") or "SWINGS").upper()
    signed = _sign(w, f, pal, -gate_span - 1, gate_b - 1, 1, f.facing,
                   [title[:SIGN_WIDTH], "", "hold on tight", ""])

    return {"kind": "swings", "diameter": R_seat * 2, "height": H_shaft + 2, "seats": seats,
            "lamps": lamps, "signed": bool(signed),
            "contract": "architecture: a chairoplane silhouette, every seat's chain 6-connected "
                        "to the crown - it does not spin, and nothing here claims it does"}


# ---------------------------------------------------------------------------- 2. teacups (midway)

def _teacups(w: World, p: dict, ctx) -> dict:
    """A RIDE. A conical canopy on posts over a ring of stationary teacups, and a real, closed,
    powered minecart loop running round the OUTSIDE of the ring - board at the gate, ride the
    loop, the cups themselves never move because nothing in vanilla can move them."""
    f = _Frame(p)
    pal, ex = _pal(p)
    R_plat = 11
    n_cups = max(4, int(p["cups"]))
    r_cup = 6

    footprint = [(a, b) for a in range(-R_plat - 4, R_plat + 5) for b in range(-R_plat - 4, R_plat + 5)]
    _ground(w, f, pal, footprint)

    # THE CANOPY: six posts at the platform's rim, a stepped cone roof collapsing to a centre
    # post - a tent, not a plate, which is what separates this from the wheel's flat crown.
    n_post = 6
    for k in range(n_post):
        th = 2 * math.pi * k / n_post
        pi, pb = round((R_plat - 1) * math.cos(th)), round((R_plat - 1) * math.sin(th))
        for h in range(6):
            w.put(*f.at(pi, pb, h), pal["post"])
    # A SOLID STEPPED CONE, not a stack of thin rings: `_disc(R)` at each step is a strict subset
    # of the disc below it (radius shrinks by 2 a step), so every layer's footprint sits directly
    # over the one before it and the whole roof is ONE connected mass by construction. Thin
    # annuli at shrinking, non-overlapping radii were the first attempt and shipped as four
    # separate floating rings - a filled cone reads as a tent roof just as well and cannot do that.
    ca, cb = pal["canopy"]
    for step, R in enumerate((R_plat - 1, R_plat - 3, R_plat - 5, R_plat - 7, R_plat - 9, 1)):
        h = 6 + step
        for (a, b) in _disc(max(R, 1)):
            w.put(*f.at(a, b, h), ca if (a + b + step) % 2 == 0 else cb)
    w.put(*f.at(0, 0, 6 + 6), pal["trim"])

    # THE CUPS: small drums, three-quarter walled with a boarding gap, a floor and a hub.
    cups = 0
    for m in range(n_cups):
        th = 2 * math.pi * m / n_cups + math.pi / n_cups
        ci, cb2 = round(r_cup * math.cos(th)), round(r_cup * math.sin(th))
        colour = BRIGHT[int(hash01(m, r_cup, f.x, f.z) * len(BRIGHT))]
        for (a, b) in _disc(2):
            w.put(*f.at(ci + a, cb2 + b, -1), pal["path"] if (a + b) % 2 else pal["ground"])
        for (a, b) in _annulus(2, 1.4):
            # leave a gap facing outward, away from centre, to board from the rim side
            if (a * math.cos(th) + b * math.sin(th)) > 0.5:
                continue
            w.put(*f.at(ci + a, cb2 + b, 0), colour)
        w.put(*f.at(ci, cb2, 0), pal["fence"])          # the centre "wheel" to hold onto
        cups += 1

    # THE TRACK: a rectangular minecart loop ringing the whole cup cluster, powered, flat, closed.
    lr = R_plat - 2
    loop_pts = _rect_loop_local(-lr, lr, -lr, lr)
    loop = _lay_loop(w, f, pal, loop_pts, 0, int(p["power_every"]), deck=pal["path"])

    # A GATED BOARDING PLATFORM at the front of the loop, a fence with one gate.
    gate_i = 0
    for i in range(-3, 4):
        w.put(*f.at(i, -lr - 1, 0), pal["path"])
    for i in (-3, 3):
        for h in range(2):
            w.put(*f.at(i, -lr - 1, h), pal["fence"])
    w.put(*f.at(gate_i, -lr - 1, 0), pal["gate"], facing=f.facing, open="false", in_wall="false")
    _lamp(w, *f.at(-3, -lr - 1, 2), pal["light"])
    _lamp(w, *f.at(3, -lr - 1, 2), pal["light"])

    # The sign hangs off the FENCE POST at i=-3 - the gate itself is one cell wide at h=0 only
    # and has nothing at h=1 to hang a sign against.
    title = str(p.get("title") or "TEACUPS").upper()
    signed = _sign(w, f, pal, -3, -lr - 2, 1, f.facing,
                   [title[:SIGN_WIDTH], "", "board the cart", ""])

    return {"kind": "teacups", "diameter": R_plat * 2, "height": 11, "cups": cups,
            "track": loop["track"], "corners": len(loop["corners"]),
            "powered": len(loop["powered"]), "signed": bool(signed),
            "boarding_at": list(f.at(gate_i, -lr - 2, 0)),
            "contract": "a closed, powered minecart loop rings the stationary cups - a real "
                        "ride you board and ride, since nothing in vanilla can spin the cups "
                        "themselves"}


# ---------------------------------------------------------------------------- 3. arcade (midway)

def _arcade(w: World, p: dict, ctx) -> dict:
    """ARCHITECTURE: a big open-fronted pavilion, a striped awning across the whole front,
    interior counters and open-trapdoor prize shelving, lit signage over the door."""
    f = _Frame(p)
    pal, ex = _pal(p)
    width = max(15, int(p["width"] or 21))
    depth = max(9, int(p["depth"] or 13))
    height = 7
    mr = int(p["min_run"])

    _pad(w, f, pal, width, depth, margin=1)

    for i in range(width):
        for d in range(depth):
            back_or_side = d == depth - 1 or i in (0, width - 1)
            if not back_or_side:
                continue
            for h in range(height):
                w.put(*f.at(i, d, h), pal["wall"] if d == depth - 1 else pal["post"])

    # THE FASCIA over the open front - both the roofline and the only thing a front sign can
    # hang from, since an open front has no wall of its own.
    for i in range(width):
        w.put(*f.at(i, 0, height - 1), pal["trim"])

    # COUNTERS down both interior side walls - a top slab so it reads as a surface, not a step.
    for d in range(1, depth - 2):
        for i in (1, width - 2):
            w.put(*f.at(i, d, 0), pal["trim"])
            w.put(*f.at(i, d, 1), pal["slab"], type="top", waterlogged="false")

    # PRIZE SHELVING on the back wall: OPEN trapdoors are the vertical-slab-and-shelf vocabulary
    # this repo measured itself seven times short on - closed against the wall they are a panel,
    # open they swing to horizontal and read as a ledge.
    shelves = 0
    for i in range(2, width - 2, 3):
        for h in (2, 4):
            w.put(*f.at(i, depth - 2, h), ex["trap"], facing=f.back, half="bottom",
                  open="true", powered="false", waterlogged="false")
            shelves += 1

    a, b = pal["canopy"]
    for i in range(-1, width + 1):
        for d in range(-1, 1):
            w.put(*f.at(i, d, height), a if i % 2 == 0 else b)
    _trim_run(w, f, pal, [(i, -2, f.back) for i in range(width)], height, mr, half="top")

    for i in range(3, width - 3, 5):
        _hang_light(w, f, pal, i, 1, height - 1)

    title = str(p.get("title") or "ARCADE").upper()
    signed = _sign(w, f, pal, width // 2, -1, height, f.facing,
                   [title[:SIGN_WIDTH], "", "win a prize", ""])
    signed2 = _sign(w, f, pal, width // 2, depth - 2, 2, f.facing,
                    ["PRIZES", "tickets", "redeem here", ""])

    return {"kind": "arcade", "width": width, "depth": depth, "height": height,
            "shelves": shelves, "signed": bool(signed) and bool(signed2),
            "contract": "architecture: an open pavilion you can see all the way into, counters "
                        "reachable, shelving that is real open-trapdoor geometry"}


# ------------------------------------------------------------------ 4. runawaymine (frontier)

def _runawaymine(w: World, p: dict, ctx) -> dict:
    """A RIDE. A mine-train station under a timber shed, beside a real closed minecart loop that
    runs out past the spoil heaps and the headframe and back - board it, ride it. A stationary
    "ore cart" (a barrel, since this server has no minecart block on its 1.19 allowlist) sits on
    a display spur, and a hoist chain hangs from the headframe to a bucket at the ground.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    mr = int(p["min_run"])
    li0, li1, ld0, ld1 = 2, 16, 3, 12          # the loop, in local (i, d)

    footprint = [(i, d) for i in range(-4, li1 + 8) for d in range(-4, ld1 + 10)]
    _ground(w, f, pal, footprint, block=pal["ground"], alt=ex["rock"])

    # THE STATION SHED: open-sided, posts and a roof, over a platform beside the loop's front edge.
    plat_d = ld0 - 2
    for i in range(li0 - 1, li1 + 2):
        for d in range(plat_d - 1, ld0):
            w.put(*f.at(i, d, 0), pal["ground"] if (i + d) % 2 else pal["path"])
    for i in (li0 - 2, li1 + 2):
        for d in (plat_d - 2, ld0 + 1):
            for h in range(6):
                w.put(*f.at(i, d, h), pal["post"])
    for i in range(li0 - 3, li1 + 4):
        for d in range(plat_d - 3, ld0 + 2):
            w.put(*f.at(i, d, 6), pal["beam"])
    _trim_run(w, f, pal, [(i, plat_d - 4, f.back) for i in range(li0 - 3, li1 + 4)], 6, mr,
              half="top")
    for i in range(li0, li1, 5):
        _hang_light(w, f, pal, i, plat_d - 1, 5)

    # THE LOOP: out from beside the platform, round the back, and back.
    pts = _rect_loop_local(li0, li1, ld0, ld1)
    loop = _lay_loop(w, f, pal, pts, 0, int(p["power_every"]), deck=ex["rock"])

    # a fence between the platform and the near edge of the track, with a boarding gap
    for i in range(li0, li1 + 1):
        if li0 + 3 <= i <= li0 + 5:
            continue
        w.put(*f.at(i, ld0 - 1, 1), pal["fence"])

    # A DISPLAY ORE CART: a barrel standing on the platform's own floor. Deliberately NOT on its
    # own rail spur - an unpowered, unconnected rail cell sitting there for decoration is exactly
    # the "dead rail" this file's rail-circuit tests exist to catch, and the whole point of this
    # kind is that the track is a real, verified circuit and nothing else pretends to be track.
    w.put(*f.at(li0 - 1, plat_d - 1, 1), "barrel", facing="up", open="false")

    # THE HEADFRAME: an A-frame hoist behind the loop - two raking legs to a beam, then a hoist
    # chain down the centre to a bucket. `_chain_path` is used for the legs too, because it is
    # the one helper here guaranteed to lay a 6-connected, axis-correct diagonal member.
    hx0, hd0 = li1 + 4, ld1 + 2
    apex_h = 11
    for s in (-2, 2):
        _chain_path(w, f.at(hx0 + s, hd0, 0), f.at(hx0, hd0, apex_h), pal["post"])
    for i in range(-2, 3):
        w.put(*f.at(hx0 + i, hd0, apex_h), pal["beam"])
    _chain_path(w, f.at(hx0, hd0, apex_h - 1), f.at(hx0, hd0, 1), "iron_chain")
    w.put(*f.at(hx0, hd0, 0), "barrel", facing="up", open="false")

    # SPOIL HEAPS: two small pyramids of aged rock, outside the loop.
    for k, (hi, hd) in enumerate(((li1 + 6, ld0 - 1), (li1 + 6, ld1 - 3))):
        for r in range(3, -1, -1):
            for (a, b) in _disc(r):
                w.put(*f.at(hi + a, hd + b, 3 - r), ex["aged"])

    # Hung off the shed's own corner POST (a full column), one cell further out than it - the
    # shed is open-sided by design, so nowhere along its open front has a wall to hang from.
    title = str(p.get("title") or "RUNAWAY MINE").upper()
    signed = _sign(w, f, pal, li0 - 2, plat_d - 3, 2, f.facing,
                   [title[:SIGN_WIDTH], "", "board the cart", "hold the rail"])

    return {"kind": "runawaymine", "width": li1 - li0 + 12, "depth": ld1 - ld0 + 14,
            "height": apex_h + 1, "track": loop["track"], "corners": len(loop["corners"]),
            "powered": len(loop["powered"]), "signed": bool(signed),
            "platform_at": list(f.at(li0 + 1, plat_d - 1, 0)),
            "boarding_at": list(f.at(li0 + 4, ld0 - 1, 1)),  # h=1: standing ON the h=0 platform floor
            "contract": "a closed, powered minecart loop out past the headframe and back, "
                        "boarded from a platform under the station roof"}


# --------------------------------------------------------------- 5. shootinggallery (frontier)

def _shootinggallery(w: World, p: dict, ctx) -> dict:
    """ARCHITECTURE: a false-fronted range with a lit backboard of real `target` blocks, a
    counter and a canopy. The odds go on the sign, same rule the casino settled: a house that
    will not print what you are shooting at is not a game."""
    f = _Frame(p)
    pal, ex = _pal(p)
    width = max(11, int(p["width"] or 15))
    depth = max(7, int(p["depth"] or 9))
    height = 5
    mr = int(p["min_run"])

    _pad(w, f, pal, width, depth, margin=1)

    for i in range(width):
        for d in range(depth):
            back_or_side = d == depth - 1 or i in (0, width - 1)
            if not back_or_side:
                continue
            for h in range(height):
                w.put(*f.at(i, d, h), pal["wall"] if d == depth - 1 else pal["post"])

    for i in range(1, width - 1):
        w.put(*f.at(i, 0, 0), pal["trim"])
        w.put(*f.at(i, 0, 1), pal["slab"], type="top", waterlogged="false")
    for i in range(width):
        w.put(*f.at(i, 0, height - 1), pal["trim"])

    # THE BACKBOARD: real `target` blocks in a diamond field, framed in the accent colour.
    targets = 0
    for i in range(2, width - 2):
        for h in range(1, height - 1):
            if abs(i - width // 2) + abs(h - height // 2) <= 2:
                w.put(*f.at(i, depth - 2, h), "target")
                targets += 1
            else:
                w.put(*f.at(i, depth - 2, h), pal["accent"] if (i + h) % 3 == 0 else pal["trim"])

    # A FALSE FRONT: a plain raised parapet, three courses, the frontier idiom for "western".
    for i in range(width):
        for k in range(3):
            w.put(*f.at(i, 0, height + k), pal["trim"] if k == 2 else pal["wall"])
    _trim_run(w, f, pal, [(i, -1, f.back) for i in range(width)], height + 2, mr, half="top")

    a, b = pal["canopy"]
    for i in range(-1, width + 1):
        for d in range(-1, 1):
            w.put(*f.at(i, d, height), a if i % 2 == 0 else b)
    _hang_light(w, f, pal, width // 2, 1, height - 2)

    title = str(p.get("title") or "SHOOTING RANGE").upper()
    signed = _sign(w, f, pal, width // 2, -1, height + 1, f.facing,
                   [title[:SIGN_WIDTH], "3 shots", "1 coin", "hit em all"])

    return {"kind": "shootinggallery", "width": width, "depth": depth, "height": height + 3,
            "targets": targets, "signed": bool(signed),
            "contract": "architecture: a false-fronted range whose backboard is real `target` "
                        "blocks, odds printed on its own sign"}


# --------------------------------------------------------------------- 6. riverboat (frontier)

def _riverboat(w: World, p: dict, ctx) -> dict:
    """RIDE-ADJACENT: a moored paddle steamer on REAL water - source blocks over a sealed solid
    bed, never a puddle-coloured floor - with a boarding gangway that is a genuine walkable
    route from the dock to the main deck. It does not travel: nothing in vanilla moves a
    structure, so this is honest about being a static silhouette piece next to real water rather
    than a flowing ride.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    L = max(21, int(p["depth"] or 27))          # hull runs along d (the long axis)
    Wd = max(7, int(p["width"] or 9))
    mr = int(p["min_run"])
    hull_h = 3

    # THE DOCK: dry land, in front of the hull.
    for i in range(-1, Wd + 1):
        for d in range(-4, 0):
            w.put(*f.at(i, d, -1), pal["ground"] if (i + d) % 2 else pal["path"])

    # THE MOORING POOL: a sealed basin the hull sits beside, real water SOURCES on a solid bed -
    # `coaster._seal`'s own rule, applied by construction: every water cell gets a bed and a wall
    # on every side that is not the hull itself.
    pool_d0, pool_d1 = 0, L
    for i in range(-3, -1):
        for d in range(pool_d0, pool_d1 + 1):
            w.put(*f.at(i, d, -2), ex["rock"])
            w.put(*f.at(i, d, -1), "water", level="0")
        w.put(*f.at(i, pool_d0 - 1, -2), ex["rock"])
        w.put(*f.at(i, pool_d0 - 1, -1), ex["rock"])
        w.put(*f.at(i, pool_d1 + 1, -2), ex["rock"])
        w.put(*f.at(i, pool_d1 + 1, -1), ex["rock"])
    for d in range(pool_d0, pool_d1 + 1):
        w.put(*f.at(-4, d, -2), ex["rock"])
        w.put(*f.at(-4, d, -1), ex["rock"])
        # THE INNER WALL, between the pool and the hull. The hull's own keel is a full cube at
        # h=0, one course ABOVE the water at h=-1 - it shares no face with the water at all, so
        # without a wall here the pool leaks sideways into the gap between i=-1 and the hull.
        w.put(*f.at(-1, d, -2), ex["rock"])
        w.put(*f.at(-1, d, -1), ex["rock"])

    # THE HULL: a full keel plate under the whole footprint - so the deck it carries is never
    # standing on a hole - with planked sides and a stair rake at bow and stern.
    for d in range(L):
        for i in range(Wd):
            w.put(*f.at(i, d, 0), ex["rock"])
    for i in (0, Wd - 1):
        for d in range(L):
            for h in range(1, hull_h):
                w.put(*f.at(i, d, h), ex["bark"], axis="y")
    _trim_run(w, f, pal, [(i, -1, f.back) for i in range(Wd)], hull_h - 1, mr, half="bottom")
    _trim_run(w, f, pal, [(i, L, f.facing) for i in range(Wd)], hull_h - 1, mr, half="bottom")

    # MAIN DECK, with a railing all round, and a walkway from the gangway forward.
    for i in range(Wd):
        for d in range(L):
            w.put(*f.at(i, d, hull_h), pal["beam"])
    for i in (0, Wd - 1):
        for d in range(4, L - 4):
            w.put(*f.at(i, d, hull_h + 1), pal["fence"])

    # SMOKESTACKS
    for si in (Wd // 3, 2 * Wd // 3):
        for h in range(hull_h + 1, hull_h + 7):
            w.put(*f.at(si, L // 3, h), pal["post"])
        w.put(*f.at(si, L // 3, hull_h + 7), pal["trim"])

    # THE WHEELHOUSE, forward on the main deck, glazed, gabled.
    wh_d0, wh_d1 = L - 8, L - 4
    for i in range(1, Wd - 1):
        for d in range(wh_d0, wh_d1):
            edge = i in (1, Wd - 2) or d in (wh_d0, wh_d1 - 1)
            if not edge:
                continue
            for h in range(hull_h + 1, hull_h + 4):
                if h == hull_h + 2 and 2 <= i <= Wd - 3:
                    along = ("north", "south") if d in (wh_d0, wh_d1 - 1) else ("east", "west")
                    props = {"north": "false", "south": "false", "east": "false", "west": "false",
                             "waterlogged": "false"}
                    props[along[0]] = props[along[1]] = "true"
                    w.put(*f.at(i, d, h), "glass_pane", **props)
                else:
                    w.put(*f.at(i, d, h), pal["wall"])
    for i in range(Wd):
        for d in range(wh_d0 - 1, wh_d1 + 1):
            w.put(*f.at(i, d, hull_h + 4), pal["trim"])

    # THE PADDLE WHEEL: a ring mounted BEHIND the stern (d > L), spanning the beam - a vertical
    # circle in the (i, h) plane, exactly like the ferris wheel's rim but sized for a boat - on a
    # support frame that ties it back to the stern's own keel and walls.
    wr = 3
    wheel_ci, wheel_d = Wd // 2, L + 2
    for (a, b) in _annulus(wr, 1.6):
        w.put(*f.at(wheel_ci + a, wheel_d, hull_h + b), pal["trim"])
    for k in range(8):
        th = 2 * math.pi * k / 8
        ei, eb = round((wr - 1) * math.cos(th)), round((wr - 1) * math.sin(th))
        for pt in _ortho_path(f.at(wheel_ci, wheel_d, hull_h), f.at(wheel_ci + ei, wheel_d, hull_h + eb)):
            w.put(*pt, pal["beam"])
    for h in range(0, hull_h + 1):
        for d in range(L, wheel_d):
            w.put(*f.at(wheel_ci - wr, d, h), ex["rock"])
            w.put(*f.at(wheel_ci + wr, d, h), ex["rock"])

    # THE GANGWAY: a real walkable ramp from the dock (d negative, h=0) up onto the main deck
    # (d=0, h=hull_h) - laid with `_ortho_path` so it is 6-CONNECTED BY CONSTRUCTION rather than
    # a diagonal stride, which is exactly the ear-tip bug this repo keeps re-discovering.
    gang_i = Wd // 2
    gd0 = -(hull_h + 1)
    ramp_a = _ortho_path(f.at(gang_i - 1, gd0, 0), f.at(gang_i - 1, -1, hull_h))
    ramp_b = _ortho_path(f.at(gang_i, gd0, 0), f.at(gang_i, -1, hull_h))
    for pt in ramp_a + ramp_b:
        w.put(*pt, pal["slab"], type="bottom", waterlogged="false")
    for i in (gang_i - 2, gang_i + 1):
        for pt in _ortho_path(f.at(i, gd0, 1), f.at(i, -1, hull_h + 1)):
            w.put(*pt, pal["fence"])

    _lamp(w, *f.at(0, L - 2, hull_h + 2), pal["light"])
    _lamp(w, *f.at(Wd - 1, L - 2, hull_h + 2), pal["light"])

    # A DOCKSIDE POST, a full cube (never the gangway's own fence), to carry the sign and a lamp.
    for h in range(3):
        w.put(*f.at(gang_i + 3, -3, h), pal["post"])
    w.put(*f.at(gang_i + 3, -3, 3), pal["trim"])
    _lamp(w, *f.at(gang_i + 3, -3, 4), pal["light"])

    title = str(p.get("title") or "RIVER QUEEN").upper()
    signed = _sign(w, f, pal, gang_i + 3, -4, 1, f.facing, [title[:SIGN_WIDTH], "", "moored", ""])

    return {"kind": "riverboat", "width": Wd, "length": L, "height": hull_h + 7,
            "signed": bool(signed), "gangway_top": list(f.at(gang_i - 1, -1, hull_h)),
            "gangway_bottom": list(f.at(gang_i - 1, gd0, 0)),
            "contract": "moored beside REAL water (source blocks over a sealed solid bed), "
                        "boarded by a genuinely walkable gangway - static, and honest about it"}


# ---------------------------------------------------------------------- 7. ghosttrain (hollow)

def _ghosttrain(w: World, p: dict, ctx) -> dict:
    """A RIDE. A dark-ride facade with a lit sign; track enters through one arch, loops through a
    dark interior past a few lit set-pieces, and comes back out through a second arch, closed
    and powered - the one attraction whose whole point IS the ride."""
    f = _Frame(p)
    pal, ex = _pal(p)
    width = max(17, int(p["width"] or 21))
    depth = max(11, int(p["depth"] or 15))
    height = 12
    mr = int(p["min_run"])
    entry_i, exit_i = 3, width - 4

    _pad(w, f, pal, width, depth, margin=2)

    # THE WHOLE SHELL, ONE PASS: the facade IS the front wall of the perimeter, with two ARCHED
    # openings left EMPTY BY THE LOOP - building the ring first and cutting a hole afterwards
    # repaints cells that already exist, which the void tower's own crenellations paid for once.
    # A second, separate wall pass over the same footprint would silently overwrite these arches
    # with solid wall, which is exactly what shipped here before this was one call.
    holes = set()
    for base_i in (entry_i, exit_i):
        for i in (base_i - 1, base_i, base_i + 1):
            for h in range(4):
                holes.add((i, 0, h))
        holes.add((base_i, 0, 4))                # the arch's point
    _walls(w, f, pal, width, depth, height, openings=holes, corner=pal["post"])
    for base_i in (entry_i, exit_i):
        for i in (base_i - 1, base_i + 1):
            w.put(*f.at(i, 0, 4), pal["trim"])
    for i in range(width):
        for d in range(depth):
            w.put(*f.at(i, d, height), pal["trim"])
    _crenellate(w, f, pal, width, depth, height + 1)
    _cornice(w, f, pal, width, depth, height, mr)

    # THE LOOP: enters at `entry_i`, runs the depth, crosses the back, comes out at `exit_i`.
    pts = _rect_loop_local(entry_i, exit_i, 0, depth - 2)
    loop = _lay_loop(w, f, pal, pts, 0, int(p["power_every"]), deck=ex["rock"])

    # A FEW LIT SET-PIECES along the back stretch - the only light in the building, which is the
    # point of a dark ride.
    lamps = 0
    for i in (entry_i + 2, (entry_i + exit_i) // 2, exit_i - 2):
        if _lamp(w, *f.at(i, depth - 3, 2), pal["light"]):
            lamps += 1

    # A BOARDING PLATFORM in front of the facade, outside, lit and signed. THE FLOOR IS h=-1,
    # matching `_pad` - built at h=0 it sat one course above its own margin and read as one
    # connected piece in every render while being, in world coordinates, floating beside it.
    for i in range(-2, width + 2):
        w.put(*f.at(i, -3, -1), pal["path"] if i % 2 else pal["ground"])
    for i in (-2, width + 1):
        _lamp(w, *f.at(i, -3, 2), pal["light"])
        for h in range(3):
            w.put(*f.at(i, -3, h), pal["post"])

    title = str(p.get("title") or "GHOST TRAIN").upper()
    signed = _sign(w, f, pal, width // 2, -1, height - 3, f.facing,
                   [title[:SIGN_WIDTH], "", "dare to ride", ""])

    return {"kind": "ghosttrain", "width": width, "depth": depth, "height": height,
            "track": loop["track"], "corners": len(loop["corners"]),
            "powered": len(loop["powered"]), "lamps": lamps, "signed": bool(signed),
            "boarding_at": list(f.at(width // 2, -3, 0)),
            "entry_at": list(f.at(entry_i, 0, 0)), "exit_at": list(f.at(exit_i, 0, 0)),
            "contract": "a closed, powered minecart loop that enters one arch, crosses a dark "
                        "interior past lit set-pieces, and leaves through the other - the ride "
                        "IS the attraction"}


# --------------------------------------------------------------------- 8. mirrormaze (hollow)

def _maze_edges(nc, nd, seed):
    """A PERFECT MAZE: a randomized DFS spanning tree over an (nc x nd) grid, HASHED rather than
    `random` - two runs of the same config are the same maze, which on an island of
    remaining-work designs is the difference between buildable and not. A spanning tree is
    connected by construction (any two cells have exactly one route between them) and has real
    dead ends by construction (every leaf), which is what makes it a maze rather than a corridor.
    """
    visited = {(0, 0)}
    stack = [(0, 0)]
    edges = set()
    while stack:
        ci, di = stack[-1]
        cand = [(ci + 1, di), (ci - 1, di), (ci, di + 1), (ci, di - 1)]
        cand = [c for c in cand if 0 <= c[0] < nc and 0 <= c[1] < nd and c not in visited]
        if not cand:
            stack.pop()
            continue
        cand.sort(key=lambda c: hash01(c[0], c[1], ci, di, seed))
        nxt = cand[0]
        edges.add(frozenset(((ci, di), nxt)))
        visited.add(nxt)
        stack.append(nxt)
    return edges


def _mirrormaze(w: World, p: dict, ctx) -> dict:
    """A WALKTHROUGH. A real maze of glass-pane corridors under a roof: a perfect spanning-tree
    maze, so there is exactly one route from the entrance to the exit and real dead-end branches
    off it - never a single corridor with two doors."""
    f = _Frame(p)
    pal, ex = _pal(p)
    nc = max(4, int(p["maze_w"] or 7))
    nd = max(4, int(p["maze_d"] or 6))
    W, D = 2 * nc + 1, 2 * nd + 1
    height = ROOM_H
    seed = int(p["seed"])

    _pad(w, f, pal, W, D, margin=2)

    edges = _maze_edges(nc, nd, seed)
    # every maze cell's own position, plus the wall cell BETWEEN each pair the spanning tree
    # connects - the local (i, d) midpoint of the two cells' own (odd, odd) positions.
    open_cells = {(2 * ci + 1, 2 * di + 1) for ci in range(nc) for di in range(nd)}
    for (a, b) in edges:
        (aci, adi), (bci, bdi) = a, b
        mi = (2 * aci + 1) + (2 * bci + 1)
        md = (2 * adi + 1) + (2 * bdi + 1)
        open_cells.add((mi // 2, md // 2))

    entry_ci, exit_ci = (0, 0), (nc - 1, nd - 1)
    entry_local = (2 * entry_ci[0] + 1, 0)
    exit_local = (2 * exit_ci[0] + 1, D - 1)

    # THE SHELL: solid perimeter, corner turrets, a roof - PANES ONLY INSIDE, the shell reads as
    # a building and never as a hole in a field.
    door_holes = set()
    for h in range(3):
        door_holes.add((entry_local[0], 0, h))
        door_holes.add((exit_local[0], D - 1, h))
    _walls(w, f, pal, W, D, height, openings=door_holes, corner=pal["post"])
    for i in range(W):
        for d in range(D):
            w.put(*f.at(i, d, height), pal["trim"])
    _cornice(w, f, pal, W, D, height, int(p["min_run"]))
    _crenellate(w, f, pal, W, D, height + 1)
    for (ci, di) in ((0, 0), (0, D - 1), (W - 1, 0), (W - 1, D - 1)):
        for h in range(height + 2, height + 4):
            w.put(*f.at(ci, di, h), pal["trim"])

    # THE MAZE PARTITIONS: glass pane, everywhere that is not an open cell or an open edge.
    panes = 0
    for i in range(1, W - 1):
        for d in range(1, D - 1):
            if (i, d) in open_cells:
                continue
            along_i = (i % 2 == 0)
            for h in range(height):
                w.put(*f.at(i, d, h), "glass_pane", waterlogged="false",
                      **({"north": "true", "south": "true"} if not along_i
                         else {"east": "true", "west": "true"}))
            panes += 1

    lamps = 0
    for (ci, di) in ((0, 0), (nc - 1, 0), (0, nd - 1), (nc - 1, nd - 1),
                      (nc // 2, nd // 2)):
        if _lamp(w, *f.at(2 * ci + 1, 2 * di + 1, height - 1), pal["light"]):
            lamps += 1

    # OFFSET FROM THE DOOR ITSELF - the door column is a hole for three courses, so it has
    # nothing behind it; the wall two cells either side of it does.
    title = str(p.get("title") or "MIRROR MAZE").upper()
    signed = _sign(w, f, pal, entry_local[0] + 2, -1, 2, f.facing,
                   [title[:SIGN_WIDTH], "", "find your way", ""])
    signed2 = _sign(w, f, pal, exit_local[0] - 2, D, 2, f.back, ["EXIT", "", "", ""])

    return {"kind": "mirrormaze", "width": W, "depth": D, "height": height,
            "cells_i": nc, "cells_d": nd, "panes": panes, "lamps": lamps,
            "signed": bool(signed) and bool(signed2),
            "entry_at": list(f.at(*entry_local, 0)), "exit_at": list(f.at(*exit_local, 0)),
            "contract": "a real maze: one solved spanning-tree route from the marked entrance to "
                        "the marked exit, with genuine dead-end branches off it, never a plain "
                        "corridor with two doors"}


# ------------------------------------------------------------------------- 9. chapel (hollow)

def _chapel(w: World, p: dict, ctx) -> dict:
    """ARCHITECTURE: a ruined chapel. A complete order with pieces missing, never a jagged pile -
    the void tower's rule applied to a ruin: a whole facade with an arched door and a rose
    window, a regular arcade of piers down each side falling away in even steps toward the back,
    and a back wall whose surviving top edge is a LINE across most of its width, not a shard."""
    f = _Frame(p)
    pal, ex = _pal(p)
    width = max(13, int(p["width"] or 17))
    depth = max(17, int(p["depth"] or 21))
    facade_h = 13
    mr = int(p["min_run"])

    _pad(w, f, pal, width, depth, margin=2, block=pal["ground"])
    # RUBBLE SCATTER, hinting at collapse without being one - and placed by RECOLOURING cells
    # `_pad`'s own margin already built, never by adding new ones beyond it. A stone dropped a
    # few cells past the footprint with nothing under or beside it is not scatter, it is a
    # floating singleton and its own one-cell component - ten of them, the first time this was
    # tried the straightforward way.
    for k in range(10):
        rx = -2 + int(hash01(k, f.x, 1) * (width + 4))
        rd = depth + int(hash01(k, f.z, 2) * 2)
        w.put(*f.at(rx, rd, -1), ex["aged"])

    # THE FACADE, d=0: an arched doorway, a rose window, a stepped pediment.
    door_i = width // 2
    holes = set()
    for i in (door_i - 1, door_i, door_i + 1):
        for h in range(5):
            holes.add((i, 0, h))
    holes.add((door_i, 0, 5))
    for i in range(width):
        for h in range(facade_h):
            if (i, 0, h) in holes:
                continue
            w.put(*f.at(i, 0, h), pal["wall"])
    for i in (door_i - 1, door_i + 1):
        w.put(*f.at(i, 0, 5), pal["trim"])

    # THE ROSE WINDOW: a small pane disc with spoke trim, centred above the door.
    rose_h = 9
    for (a, b) in _disc(2):
        w.put(*f.at(door_i + a, 0, rose_h + b), "glass_pane", waterlogged="false",
              north="true", south="true")
    for (a, b) in _disc(3):
        if not (2 < a * a + b * b <= 9):
            continue
        if _wedge(a, b, 8) % 2 == 0:
            w.put(*f.at(door_i + a, 0, rose_h + b), pal["trim"])

    # A STEPPED PEDIMENT over the roofline, a crest finial on top.
    for k, half_span in enumerate((width // 2, width // 2 - 2, width // 2 - 4, 1)):
        h = facade_h + k
        for i in range(door_i - half_span, door_i + half_span + 1):
            if 0 <= i < width:
                w.put(*f.at(i, 0, h), pal["trim"] if k == 3 else pal["wall"])
    _trim_run(w, f, pal, [(i, -1, f.back) for i in range(width)], facade_h, mr, half="top")

    # SIDE ARCADES: a regular file of piers falling in even steps toward the back. A lancet
    # opening carved into the MIDDLE of a single-column pier severs it into a floating cap and a
    # grounded stub - a pier one cell wide has no "either side of the window" to stay connected
    # through, so the opening is a height reduction, not a hole - the void tower's own rule that
    # what makes a ruin read as architecture is REGULARITY, and a solid falling colonnade is that.
    piers = 0
    for i in (0, width - 1):
        for d in range(1, depth, 3):
            h_here = max(3, facade_h - 2 * (d // 3))
            for h in range(h_here):
                w.put(*f.at(i, d, h), pal["post"] if h_here >= facade_h - 2 else pal["trim"])
            piers += 1

    # THE BACK WALL: a uniform-height stub, a CREST LINE rather than a shard - full width at one
    # low height, which is what makes it read as a deliberate remnant.
    crest_h = 4
    crest_run = 0
    for i in range(1, width - 1):
        for h in range(crest_h):
            w.put(*f.at(i, depth - 1, h), pal["wall"] if h < crest_h - 1 else pal["trim"])
        crest_run += 1

    # COBWEBS, the one atmospheric touch - hung directly against the crest wall's OWN face, one
    # cell in front of it, so each one shares a face with a cell that is already built rather
    # than hanging in open interior air with nothing beside it.
    for k in range(4):
        ci = 1 + (k * 3) % (width - 2)
        w.put(*f.at(ci, depth - 2, 1), "cobweb")

    lights = 0
    for d in range(4, depth - 1, 6):
        if _lamp(w, *f.at(1, d, min(4, facade_h - 2)), pal["light"]):
            lights += 1
        if _lamp(w, *f.at(width - 2, d, min(4, facade_h - 2)), pal["light"]):
            lights += 1

    # Offset from the doorway itself - the door column is a five-course hole with nothing behind
    # it; the facade wall three cells clear of it does.
    title = str(p.get("title") or "OLD CHAPEL").upper()
    signed = _sign(w, f, pal, door_i - 3, -1, 2, f.facing, [title[:SIGN_WIDTH], "", "", ""])

    return {"kind": "chapel", "width": width, "depth": depth, "height": facade_h + 4,
            "piers": piers, "crest_run": crest_run, "lights": lights, "signed": bool(signed),
            "contract": "a ruin that is a complete order with pieces missing: a whole facade, a "
                        "regular arcade falling away in even steps, a crest that is a LINE "
                        "across the back wall rather than a single surviving shard"}


BUILDERS = {
    "swings": _swings,
    "teacups": _teacups,
    "arcade": _arcade,
    "runawaymine": _runawaymine,
    "shootinggallery": _shootinggallery,
    "riverboat": _riverboat,
    "ghosttrain": _ghosttrain,
    "mirrormaze": _mirrormaze,
    "chapel": _chapel,
}

DEFAULTS = ATTRACTIONS


def build(cfg: dict, donors=None) -> Canvas:
    p = {**ATTRACTIONS, **cfg}
    if not p.get("at"):
        raise ValueError("attractions needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown attractions kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    return w.canvas({
        "kind": f"attractions/{p['kind']}",
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
