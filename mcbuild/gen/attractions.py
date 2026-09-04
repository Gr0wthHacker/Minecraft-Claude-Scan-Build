"""MORE RIDES: the park was "single small structures... some infrastructure and some huts", and
scale plus real mechanics is the fix. Nine kinds, three per land, and every one that CAN function
as a ride, mechanism or walkable route DOES - vanilla Minecraft cannot fake a moving structure, so
where this file claims a ride it is a rail circuit, a body of real water, or a flood-fill-proven
walkable route, never a static prop shaped like one. That is this project's cardinal sin, paid for
twice already: the log flume that shipped 564 water SOURCE blocks and never carried a rider, and
the coaster whose first platform was walled off from its own track.

    swings           midway   architecture - a chairoplane tower, chains swung out, no mechanism
    teacups          midway   RIDE - a graded circuit that rises over the cups. DUPLICATES the
                              carousel and no zone plans it; the recommendation is to retire it
    arcade           midway   architecture - an open pavilion
    runawaymine      frontier RIDE - out of the station shed, seven courses up on trestles past
                              the headframe, over the spoil heaps, and down
    shootinggallery  frontier architecture - a false-fronted range
    riverboat        frontier RIDE-ADJACENT - moored on real still water, a walkable gangway
    ghosttrain       hollow   RIDE - boards outside, runs the frontage, in one arch at ground, up
                              to a gallery over the lit tomb, down, out the other arch
    mirrormaze       hollow   WALKTHROUGH - a real maze: one solved route, real branches, real dead ends
    chapel           hollow   architecture - a ruin, regular and ordered, never a jagged pile

**A LAP IS NOT A RIDE, AND ALL THREE OF THESE WERE LAPS.** Every rail circuit here used to be a
flat rectangle - 46 to 72 cells on ONE course, in one side and out the other, past scenery seen
once from one height. The shipped park's verdict was *"the hollow rollercoaster which is just a
circle feel pointless and weird filler"*, and the diagnosis under it is general: what makes a
rail ride worth riding is a CHANGE OF HEIGHT (there are no drops, no crest and no view without
one), a JOURNEY rather than a lap (out and back, through a building, over a thing), SOMETHING TO
SEE timed to the ride, and a REAL STATION to board at. All four are buildable here and all four
are now built; `_Circuit` is where the first of them lives.

**THE RAIL RULES, from `railspiral.py`'s own hard-won notes, restated because getting any one of
them wrong ships a schematic that passes every check here and does not connect in the world:**

    powered_rail CANNOT CURVE (blocks.json: no south_east/south_west/north_west/north_east for
    it) - every direction change is a plain `rail`, and iron is the scarce metal on this server
    while gold is farmable, so the PLAN SHAPE is an economic decision and every corner is counted.
    AN UNPOWERED powered_rail IS A BRAKE - a redstone_block sits in the bed roughly every 8 cells,
    counted per RUN BETWEEN CORNERS, because a corner does not carry the signal chain.
    NEVER DESCEND INTO A CORNER - this used to say "not used here at all: every circuit in this
    file is FLAT", which was true and was the bug. Every circuit is GRADED now, so the rule is
    live: `coaster._profile` freezes the height at every corner and at both its neighbours.
    NOTHING MAY STAND ON, OR OVER, THE TRACK - two clear courses over every rail cell, checked
    against the finished world at generation time by `_Circuit.verify` and at every facing by
    `tests/test_attractions.py`. A post resting on a rail draws exactly like a post resting on
    the ground, which is how the teacups shipped four of them and the Ghost Train eleven.
    A CART AT REST LAUNCHES AWAY FROM AN ADJACENT SOLID BLOCK - moot here: every circuit is a
    CLOSED LOOP with no free end, so there is no terminus to stop at and nothing to launch from.

`coaster.py` already solved closed-circuit corner detection, the height profile, the feasibility
check, rail shaping and per-run power for exactly this kind of circuit (`_corners`, `_profile`,
`_feasible`, `_shapes`, `_power`, plus `_RIDER_THROUGH`) - all reused here rather than
re-derived, which is the one-source rule this repo keeps re-learning the hard way.

**WHAT A RIDE HERE DOES AND DOES NOT CLAIM.** There is no cart-physics model in this repo, so no
contract in this file states a speed or promises a completed lap. What is verified is that the
circuit is closed, that every straight run is powered at both ends, that every corner is flat on
both sides, that every slope ascends toward its higher neighbour, that every elevated cell is
carried to the apron, that two courses over every rail cell are clear, and that the platform is
walkable from real ground. Each kind's own contract says exactly that, and says what is left.

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
from .coaster import (_corners as _loop_corners, _feasible as _loop_feasible,
                      _power as _loop_power, _profile as _loop_profile,
                      _shapes as _loop_shapes, _trace as _loop_trace,
                      _RIDER_HEAD, _RIDER_THROUGH)
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
    # PRISMWORKS. `park.LANDS` gained a third land and every per-land table in the park had to
    # gain one with it - a land that is in one table and not another does not fail loudly, it
    # raises a KeyError deep inside a generator, and 157 of this file's tests parameterise over
    # `sorted(park.LANDS)`. The machine land's rock is its own polished deepslate rather than a
    # cobble, because cobblestone is banned here.
    "prismworks": {"rock": "polished_deepslate", "rock_stair": "polished_deepslate_stairs",
                   "aged": "smooth_basalt", "bark": "stripped_dark_oak_log",
                   "trap": "dark_oak_trapdoor"},
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


class _Circuit:
    """A CLOSED, GRADED minecart circuit: PLANNED first, RESERVED, and LAID last.

    **A LOOP THAT STAYS ON ONE COURSE IS A CIRCLE, NOT A RIDE.** Every rail ride in this file used
    to be a flat rectangle - you got in, went round once past nothing at one height, and arrived
    where you started. The verdict on the shipped park was *"just a circle... pointless and weird
    filler"* and it was correct: a ride is a JOURNEY, which means a climb, a crest, a fall and
    something to look at from the cart on the way. `coaster.py` already solved every piece of that
    - the corner rule, the height profile, the feasibility check, the shapes and the per-run power
    - so this reuses all six rather than re-deriving them. One source, so the coaster and these
    three cannot quietly disagree about what a corner is.

    THE FOUR RAIL RULES, restated because each one ships a schematic that passes every check here
    and does not work in the world:

        powered_rail CANNOT CURVE - `data/blocks.json` gives it north_south, east_west and the
        four ascending states and NOTHING ELSE, so every direction change is a plain `rail` and
        therefore IRON, the scarce metal on this server against gold which is farmable. Corners
        are counted and the bill is reported.
        AN UNPOWERED powered_rail IS A BRAKE - `_power` puts a `redstone_block` in the bed at
        both ends of every run and every `power_every` along it, counted BETWEEN CORNERS, because
        a plain rail does not carry the chain and a flat spacing leaves a dead rail past a turn.
        NEVER DESCEND INTO A CORNER - a curve has no ascending state, so `_profile` freezes the
        height at every corner AND at the cell on each side of it.
        NOTHING MAY STAND ON, OR OVER, THE TRACK - and this is the one the other three do not
        cover, because it is not about the rail at all. A post resting on a rail draws exactly
        like a post resting on the ground; a wall over a rail draws exactly like a wall over the
        floor. The teacups put four canopy posts on their own loop and the Ghost Train put solid
        wool over eleven of its fifty track cells - a suffocation tunnel - and both passed legal
        states, connectivity, closure, power and the bill of materials.

    So the circuit is a RESERVATION before it is a build. `owns(i, d, h)` answers for the rail
    cell, its bed, the `HEAD` courses over it that a rider's body occupies, and every pier column
    that carries an elevated cell down to the apron; every structural loop in this file asks it
    before placing, and `verify` re-asks it against the FINISHED world so a cell taken by
    something written later is a generation-time error rather than a ride nobody can survive.

    **WHAT IS AND IS NOT VERIFIED.** There is no cart-physics model in this repo, so nothing here
    claims a speed, a completed lap or that a crest is crossed. What IS verified: the circuit is
    CLOSED, every straight run is POWERED at both ends, every corner is FLAT on both sides, every
    slope ascends toward its higher neighbour, every elevated cell is carried to the apron, and
    every rider cell is clear. That distinction is stated in each kind's own contract.
    """

    # Courses over a rail cell a rider's body occupies. COASTER.PY'S number, imported rather than
    # restated, for the same reason `_RIDER_THROUGH` is - see the note under this class.
    HEAD = _RIDER_HEAD

    def __init__(self, wps, power_every=8, pier_every=4, what="the circuit"):
        full, marks = _loop_trace(wps)
        if full[-1] != full[0]:
            raise ValueError("%s: the waypoints must close on themselves" % what)
        self.pts = full[:-1]
        self.corners = _loop_corners(self.pts, True)
        # `_profile` walks the OPEN list, so the seam corner is named in BOTH index spaces or the
        # closing leg is free to keep descending straight into the turn it closes on.
        seam = self.corners | ({len(full) - 1} if 0 in self.corners else set())
        _loop_feasible(full, marks, wps, seam, what)
        hs = _loop_profile(full, marks, wps, seam)
        if hs[-1] != hs[0]:
            raise ValueError("%s: the circuit does not close in height (%d -> %d)"
                             % (what, hs[0], hs[-1]))
        self.hs = hs[:-1]
        self.n = len(self.pts)
        self.what = what
        self.powered = _loop_power(self.n, self.corners, max(1, int(power_every)))

        # Where a pier stands. Only the columns that actually carry something, so the space
        # between them stays available for the scenery the ride exists to run past.
        every = max(2, int(pier_every))
        self.pier_at = {j for j in range(self.n)
                        if self.hs[j] >= 1 and (j % every == 0 or j in self.corners)}

        self.rail, self.bed, self.head, self.piers = set(), set(), set(), set()
        for j, (i, d) in enumerate(self.pts):
            h = self.hs[j]
            self.rail.add((i, d, h))
            self.bed.add((i, d, h - 1))
            for k in range(1, self.HEAD + 1):
                self.head.add((i, d, h + k))
            if j in self.pier_at:
                for hh in range(h - 2, -2, -1):
                    self.piers.add((i, d, hh))
        self.owned = self.rail | self.bed | self.head | self.piers

    # ---- what the ride is, in numbers a report can print

    @property
    def rise(self):
        """Courses climbed and courses fallen over one lap. A ride with (0, 0) is a circle."""
        up = down = 0
        for a, b in zip(self.hs, self.hs[1:] + self.hs[:1]):
            up += max(0, b - a)
            down += max(0, a - b)
        return up, down

    @property
    def top(self):
        return max(self.hs)

    def bill(self):
        """The metal. A corner is a plain rail (6 iron makes 16) and a straight is powered
        (6 gold makes 6), which is why the PLAN SHAPE is an economic decision here."""
        c, straight = len(self.corners), self.n - len(self.corners)
        return {"corners": c, "powered": straight,
                "iron_ingots": round(c * 6 / 16.0, 1), "gold_ingots": straight,
                "redstone_blocks": len(self.powered)}

    def owns(self, i, d, h) -> bool:
        return (i, d, h) in self.owned

    def column_free(self, i, d, h0, h1) -> bool:
        """THE WHOLE COLUMN, not its foot. A post whose foot is clear and whose head lands in a
        leg passing overhead puts a log in the rider - `coaster._coaster`'s own lamp-post note,
        and the failure the teacups shipped four times over."""
        return all(not self.owns(i, d, h) for h in range(h0, h1 + 1))

    # ---- laying it

    def lay(self, w, f, pal, deck=None, pier=None):
        """Beds, power, piers, then rails - in that order, and LAST of everything in a builder.

        A rail cell that is already occupied is an ERROR, never a skip: a rail quietly dropped
        for a fence post is a dead end that audits perfectly clean.
        """
        cells = [f.at(i, d, h) for (i, d), h in zip(self.pts, self.hs)]
        shapes = _loop_shapes(cells, self.corners, True)
        deckmat = deck or pal["path"]
        piermat = pier or pal["post"]
        piers = 0
        for j, (i, d) in enumerate(self.pts):
            h = self.hs[j]
            w.put(*f.at(i, d, h - 1), "redstone_block" if j in self.powered else deckmat)
            if j in self.pier_at:
                for hh in range(h - 2, -2, -1):
                    w.put(*f.at(i, d, hh), piermat)
                piers += 1
        for j, (i, d) in enumerate(self.pts):
            pos = f.at(i, d, self.hs[j])
            if w.has(*pos):
                raise ValueError("%s: track cell %d at %s is occupied by %s"
                                 % (self.what, j, (i, d), w.name(*pos)))
            w.put(*pos, "rail" if j in self.corners else "powered_rail", shape=shapes[j])
        # `bill()` is merged LAST and it owns `corners` and `powered` - as COUNTS. The index
        # sets keep their own names, because a caller that reads `corners` expecting a number and
        # gets a set (or the reverse) fails somewhere else entirely.
        out = {"cells": cells, "corner_idx": self.corners, "powered_idx": self.powered,
               "track": self.n, "piers": piers, "rise": self.rise[0], "fall": self.rise[1],
               "track_top": self.top}
        out.update(self.bill())
        return out

    def verify(self, w, f):
        """**THE CHECK NOTHING ELSE MAKES**, run against the FINISHED world.

        Two courses clear over every rail cell. `tests/test_attractions.py` asserts it at every
        facing too, and it is asserted HERE as well because a generator that can only be told it
        is wrong by a test suite is one that ships wrong to anybody who calls it directly.
        """
        bad = []
        for j, (i, d) in enumerate(self.pts):
            for k in range(1, self.HEAD + 1):
                x, y, z = f.at(i, d, self.hs[j] + k)
                n = w.name(x, y, z)
                if n is not None and n.split(":")[-1] not in _RIDER_THROUGH:
                    bad.append(((i, d, self.hs[j] + k), n))
        if bad:
            raise ValueError("%s: %d track cell(s) have something in the rider: %s"
                             % (self.what, len(bad), bad[:4]))
        return True


# _RIDER_THROUGH - what a rider passes through unharmed - is `coaster.py`'s now, imported above:
# both this file's loop rides and `coaster.py`'s own track check judge a rail cell's rider space
# by the same set, so the two cannot drift apart the way two copies of "what can a rider pass
# through" eventually do.


def _rect_wps(i0, i1, d0, d1, lift=0, low=0, near_break=None):
    """A rectangular circuit that CLIMBS one side, runs its far leg high, and falls down the
    other - the smallest change that turns a lap into a ride, and the one two kinds here use.

    The near leg (`d0`) is the station straight and stays at `low`; the far leg (`d1`) is the
    crest. Both ends of a leg carry the same height, which is "never descend into a corner"
    expressed as geometry rather than hoped for from `_profile`.

    `near_break` names an `i` on the near leg to plant an extra COLINEAR waypoint at, so a caller
    can hold a stretch of it flat for a platform without turning it into a corner.
    """
    if lift < 0:
        raise ValueError("a circuit cannot lift by %d" % lift)
    near = [(i0, d0, low)]
    if near_break is not None and i0 < near_break < i1:
        near.append((near_break, d0, low))
    return near + [(i1, d0, low), (i1, d1, low + lift),
                   (i0, d1, low + lift), (i0, d0, low)]


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
    """A RIDE - and, honestly, THE ONE KIND IN THIS FILE THAT DUPLICATES ANOTHER.

    A cart going round under a canopy is the CAROUSEL (`bigwheel._carousel`), which does it
    better: a true rasterised circle rather than a rectangle, two rings of mounts either side of
    the rail, and a wedge-striped cone over it. This kind was the same idea with worse geometry,
    and it is not in any zone's module list - the planner drops it. **The recommendation is to
    retire it and keep the carousel**; it is graded here rather than deleted only so that nothing
    in the repo still ships a flat lap, and because deleting a kind is not this pass's call.

    What it is now: the loop still rings the cups, but the far leg RISES FOUR COURSES on piers,
    so the back half of the lap runs over the cup ring and a rider looks DOWN into the cups
    instead of past them. Board at the front gate, climb the right side, cross the hump, fall
    down the left, arrive back at the gate. The cups themselves still never move, because nothing
    in vanilla can move them - and the ride does not pretend otherwise.

    **THE CANOPY HAD TO GO UP WITH THE TRACK.** Its cone started at h=6 and the raised leg tops
    out at h=4, which leaves ONE clear course over the rider - a moving cart under a solid roof
    two cells above the rail. The cone starts at h=8 now and the posts are eight courses; the
    rule that forced it is `_Circuit.HEAD`, and it is checked against the finished world rather
    than against this paragraph.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    R_plat = 11
    n_cups = max(4, int(p["cups"]))
    r_cup = 6
    lr = R_plat - 2                     # the loop's half-extent
    LIFT = 4                            # courses the far leg rises
    EAVE = 8                            # the cone's first course: HEAD + the crest, and no less

    # ---- THE CIRCUIT IS PLANNED FIRST, so every post, cup and pier below can ask whether a cell
    # belongs to the rider before it takes it. Four canopy posts once stood ON this loop's own
    # rectangle: the loop was laid afterwards, overwrote each post's ground cell with rail and
    # left the post standing in the course above - a rider hits a log at speed, and every check
    # passed. `circ.owns` is why that cannot happen again by arithmetic.
    circ = _Circuit(_rect_wps(-lr, lr, -lr, lr, lift=LIFT),
                    int(p["power_every"]), pier_every=4, what="the teacups' circuit")

    footprint = [(a, b) for a in range(-R_plat - 4, R_plat + 5) for b in range(-R_plat - 4, R_plat + 5)]
    _ground(w, f, pal, footprint)

    # THE CANOPY: six posts INSIDE the loop, a stepped cone roof collapsing to a centre post - a
    # tent, not a plate, which is what separates this from the wheel's flat crown.
    posts = 0
    n_post = 6
    for k in range(n_post):
        th = 2 * math.pi * k / n_post
        pi, pb = round((lr - 2) * math.cos(th)), round((lr - 2) * math.sin(th))
        if max(abs(pi), abs(pb)) >= lr or not circ.column_free(pi, pb, -1, EAVE):
            continue
        for h in range(EAVE):
            w.put(*f.at(pi, pb, h), pal["post"])
        posts += 1
    # A SOLID STEPPED CONE, not a stack of thin rings: `_disc(R)` at each step is a strict subset
    # of the disc below it (radius shrinks by 2 a step), so every layer's footprint sits directly
    # over the one before it and the whole roof is ONE connected mass by construction. Thin
    # annuli at shrinking, non-overlapping radii were the first attempt and shipped as four
    # separate floating rings - a filled cone reads as a tent roof just as well and cannot do that.
    ca, cb = pal["canopy"]
    for step, R in enumerate((R_plat - 1, R_plat - 3, R_plat - 5, R_plat - 7, R_plat - 9, 1)):
        h = EAVE + step
        for (a, b) in _disc(max(R, 1)):
            if circ.owns(a, b, h):
                continue
            w.put(*f.at(a, b, h), ca if (a + b + step) % 2 == 0 else cb)
    w.put(*f.at(0, 0, EAVE + 6), pal["trim"])

    # THE CUPS: small drums, three-quarter walled with a boarding gap, a floor and a hub.
    cups = 0
    for m in range(n_cups):
        th = 2 * math.pi * m / n_cups + math.pi / n_cups
        ci, cb2 = round(r_cup * math.cos(th)), round(r_cup * math.sin(th))
        colour = BRIGHT[int(hash01(m, r_cup, f.x, f.z) * len(BRIGHT))]
        for (a, b) in _disc(2):
            if circ.owns(ci + a, cb2 + b, -1):
                continue
            w.put(*f.at(ci + a, cb2 + b, -1), pal["path"] if (a + b) % 2 else pal["ground"])
        for (a, b) in _annulus(2, 1.4):
            # leave a gap facing outward, away from centre, to board from the rim side
            if (a * math.cos(th) + b * math.sin(th)) > 0.5:
                continue
            if circ.owns(ci + a, cb2 + b, 0):
                continue
            w.put(*f.at(ci + a, cb2 + b, 0), colour)
        w.put(*f.at(ci, cb2, 0), pal["fence"])          # the centre "wheel" to hold onto
        cups += 1

    # A GATED BOARDING PLATFORM at the front of the loop, on the circuit's own LOW leg - the
    # station straight, which is what `_rect_wps` keeps flat.
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

    loop = circ.lay(w, f, pal, deck=pal["path"], pier=pal["post"])
    circ.verify(w, f)

    return {"kind": "teacups", "diameter": R_plat * 2, "height": EAVE + 7, "cups": cups,
            "posts": posts, "track": loop["track"], "corners": loop["corners"],
            "powered": loop["powered"], "piers": loop["piers"],
            "rise": loop["rise"], "fall": loop["fall"], "lift": LIFT,
            "iron_ingots": loop["iron_ingots"], "gold_ingots": loop["gold_ingots"],
            "redstone_blocks": loop["redstone_blocks"], "signed": bool(signed),
            "boarding_at": list(f.at(gate_i, -lr - 2, 0)),
            "duplicate_of": "carousel",
            "contract": "a closed, powered minecart circuit ringing the stationary cups, whose "
                        "far leg rises %d courses on piers so the back half of the lap looks "
                        "DOWN into them. %d cells, %d corners, %d courses of rise and the same "
                        "of fall. VERIFIED: closed, every run powered at both ends, every corner "
                        "flat on both sides, every elevated cell carried to the apron, two clear "
                        "courses over every rail cell, boardable on foot through the front gate. "
                        "NOT verified: cart speed - there is no cart-physics model here. AND "
                        "NOTE: this kind duplicates the carousel and no zone plans it; the "
                        "recommendation is to retire it."
                        % (LIFT, loop["track"], loop["corners"], loop["rise"])}


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
    """A RIDE, AND A CLIMB OUT OF THE VALLEY. It was a flat rectangle beside a shed - forty-six
    cells on one course, past a headframe that stood OUTSIDE the loop where a rider never got
    near it.

    What it is now, in the order you ride it:

        1. board on the platform under the station shed, at ground
        2. run the station straight, out under two timbered MINE PORTALS
        3. CLIMB the east side seven courses on trestles - the ride leaves the ground
        4. cross the whole back leg at h=7, over the spoil heaps and level with the HEADFRAME's
           hoist beam, which now stands inside the loop where you pass it
        5. FALL seven courses down the west side
        6. arrive back at the platform

    Sixty-two cells, four corners, seven courses of rise and seven of fall, in the footprint the
    planner already reserved for it (26 x 23).

    **THE HEADFRAME MOVED INSIDE THE LOOP AND THAT IS THE WHOLE POINT OF THE REBUILD.** A ride's
    content is what you pass, and a hoist standing four cells beyond the far rail was scenery for
    somebody on the ground rather than for the rider. Inside, at the middle of the circuit, the
    crest runs level with its beam. Nothing about it may touch the track, which is asserted
    against `circ.owns` per cell rather than against this paragraph - the shed's own far posts
    used to be sited by arithmetic that put four of the teacups' posts straight onto the rail.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    mr = int(p["min_run"])
    li0, li1, ld0, ld1 = 2, 20, 4, 17          # the circuit, in local (i, d)
    LIFT = 7                                   # courses the far leg climbs
    APEX = 11                                  # the headframe's beam, and the module's own top

    # ---- PLANNED FIRST. Everything below asks `circ` before it places.
    circ = _Circuit(_rect_wps(li0, li1, ld0, ld1, lift=LIFT),
                    int(p["power_every"]), pier_every=4, what="the Runaway Mine's circuit")

    footprint = [(i, d) for i in range(-2, 24) for d in range(-2, 21)]
    _ground(w, f, pal, footprint, block=pal["ground"], alt=ex["rock"])

    def free_put(i, d, h, name, **props):
        if circ.owns(i, d, h):
            return 0
        w.put(*f.at(i, d, h), name, **props)
        return 1

    # THE STATION SHED: open-sided, posts and a roof, over a platform beside the circuit's own
    # LOW leg - the straight `_rect_wps` holds flat so that a boarder's feet are level with the
    # cart. The roof SPANS THE TRACK, which is what makes it read as a station rather than a bus
    # shelter, and it clears the rider by four courses.
    plat_d = ld0 - 3                           # d = 1; the platform runs d=1..3
    for i in range(li0, 15):
        for d in range(plat_d, ld0):
            free_put(i, d, 0, pal["ground"] if (i + d) % 2 else pal["path"])
    for i in (li0 + 1, 13):
        for d in (plat_d - 1, ld0 + 2):
            for h in range(6):
                free_put(i, d, h, pal["post"])
    for i in range(li0, 15):
        for d in range(plat_d - 2, ld0 + 3):
            free_put(i, d, 6, pal["beam"])
    _trim_run(w, f, pal, [(i, plat_d - 2, f.back) for i in range(li0, 15)], 6, mr, half="top")
    for i in range(li0 + 2, 13, 5):
        _hang_light(w, f, pal, i, plat_d, 5)

    # a fence between the platform and the near edge of the track, with a boarding gap
    for i in range(li0, 15):
        if li0 + 3 <= i <= li0 + 5:
            continue
        free_put(i, ld0 - 1, 1, pal["fence"])

    # A DISPLAY ORE CART: a barrel standing on the platform's own floor. Deliberately NOT on its
    # own rail spur - an unpowered, unconnected rail cell sitting there for decoration is exactly
    # the "dead rail" this file's rail-circuit tests exist to catch.
    free_put(li0, plat_d, 1, "barrel", facing="up", open="false")

    # TWO TIMBERED MINE PORTALS over the station straight, out past the shed. A post either side
    # and a beam across at h=3 - which is ONE COURSE OVER the rider's head, and no closer: a
    # portal at h=2 is a lintel in the face. This is the vocabulary the corpus says we are seven
    # times short of, used for the thing it is actually for.
    portals = 0
    for pi in (16, 19):
        if not (circ.column_free(pi, ld0 - 1, 0, 3) and circ.column_free(pi, ld0 + 1, 0, 3)):
            continue
        for h in range(3):
            free_put(pi, ld0 - 1, h, pal["post"])
            free_put(pi, ld0 + 1, h, pal["post"])
        for d in (ld0 - 1, ld0, ld0 + 1):
            free_put(pi, d, 3, pal["beam"])
        portals += 1

    # THE HEADFRAME, INSIDE the circuit at its centre: two raking legs to a beam, then a hoist
    # chain down to a bucket. `_chain_path` is the one helper here guaranteed to lay a
    # 6-connected, axis-correct diagonal member.
    hx0, hd0 = (li0 + li1) // 2, (ld0 + ld1) // 2
    _chain_path(w, f.at(hx0 - 2, hd0, 0), f.at(hx0, hd0, APEX), pal["post"])
    _chain_path(w, f.at(hx0 + 2, hd0, 0), f.at(hx0, hd0, APEX), pal["post"])
    for i in range(-2, 3):
        free_put(hx0 + i, hd0, APEX, pal["beam"])
    _chain_path(w, f.at(hx0, hd0, APEX - 1), f.at(hx0, hd0, 1), "iron_chain")
    free_put(hx0, hd0, 0, "barrel", facing="up", open="false")

    # SPOIL HEAPS, INSIDE the loop under the crest, so the high leg runs over them.
    heaps = 0
    for (hi, hd) in ((li0 + 4, ld1 - 3), (li1 - 4, ld1 - 3)):
        for r in range(3, -1, -1):
            for (a, b) in _disc(r):
                free_put(hi + a, hd + b, 3 - r, ex["aged"])
        heaps += 1

    # Hung off the shed's own corner POST (a full column), one cell further out than it - the
    # shed is open-sided by design, so nowhere along its open front has a wall to hang from.
    title = str(p.get("title") or "RUNAWAY MINE").upper()
    signed = _sign(w, f, pal, li0 + 1, plat_d - 2, 2, f.facing,
                   [title[:SIGN_WIDTH], "", "board the cart", "hold the rail"])

    # ---- THE TRACK, LAID LAST, then VERIFIED against the finished world.
    loop = circ.lay(w, f, pal, deck=ex["rock"], pier=pal["post"])
    circ.verify(w, f)

    return {"kind": "runawaymine", "width": 26, "depth": 23, "height": APEX + 1,
            "track": loop["track"], "corners": loop["corners"], "powered": loop["powered"],
            "piers": loop["piers"], "portals": portals, "heaps": heaps,
            "rise": loop["rise"], "fall": loop["fall"], "crest": LIFT,
            "iron_ingots": loop["iron_ingots"], "gold_ingots": loop["gold_ingots"],
            "redstone_blocks": loop["redstone_blocks"], "signed": bool(signed),
            "platform_at": list(f.at(li0 + 1, plat_d, 0)),
            "boarding_at": list(f.at(li0 + 4, ld0 - 1, 1)),  # h=1: standing ON the h=0 platform
            "contract": "a closed, powered minecart circuit that leaves a roofed station "
                        "straight, runs out under two timbered mine portals, climbs %d courses "
                        "on trestles up the east side, crosses the crest level with the "
                        "headframe's hoist beam and over the spoil heaps, and falls %d courses "
                        "back to the platform. %d cells, %d corners. VERIFIED: closed, every run "
                        "powered at both ends, every corner flat on both sides, every elevated "
                        "cell carried to the apron on piers, two clear courses over every rail "
                        "cell, and the platform walkable from the ground it stands on. NOT "
                        "verified: cart speed - there is no cart-physics model here, so ride it "
                        "once before anyone is told it completes the lap."
                        % (loop["rise"], loop["fall"], loop["track"], loop["corners"])}


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

# The four world directions in a frame's own terms. `hollowmanor._ax` says the same thing for the
# quarter's own kinds; a grille needs it here because a run of `iron_bars` with every side false
# renders as a lone POST rather than as bars - the campanile's own note - so the run's axis is
# always stated and never left to default.
_FACE = {v: k for k, v in _STEP.items()}


def _bars(f, along_i: bool) -> dict:
    p = {"north": "false", "south": "false", "east": "false", "west": "false",
         "waterlogged": "false"}
    a, b = ((_FACE[(f.sx, f.sz)], _FACE[(-f.sx, -f.sz)]) if along_i
            else (f.facing, f.back))
    p[a] = p[b] = "true"
    return p


def _web(w, f, i, d, h) -> bool:
    """A cobweb, ANCHORED to a cell that is already built.

    A cobweb hanging in open air with nothing beside it is a floating singleton and its own
    component - `hollowmanor._cobwebs`' note, and the same 6-connectivity trap that broke the
    leopard's ear tips. It is also the one prop a body passes THROUGH, so it may never be placed
    where the ride or the walk needs the cell: every call site here passes a ceiling corner or a
    cell against the mausoleum's outer wall, never a track column.
    """
    x, y, z = f.at(i, d, h)
    if w.has(x, y, z):
        return False
    if not any(w.has(x + a, y + b, z + c)
               for (a, b, c) in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                 (0, -1, 0), (0, 0, 1), (0, 0, -1))):
        return False
    w.put(x, y, z, "cobweb")
    return True


def _ghost_scenes(w, f, pal, ex, width, depth, height, i0, i1, circ=None) -> dict:
    """THE THING A DARK RIDE IS FOR, and this one shipped without any of it.

    **MEASURED ON THE BUILD BEFORE THIS: THE WHOLE ATTRACTION CONTAINED ZERO LIGHT SOURCES.**
    1,689 cells, and a census of them returned wool, blackstone, deepslate, rail and one sign -
    not a lantern, not a torch, not a candle. Both places light was asked for returned False and
    both returns were dropped on the floor:

        the three interior lamps sat at h=2 in open air, with nothing under them to stand on and
        nothing over them to hang from, so `_lamp` refused all three and `meta["lamps"]` shipped 0
        the two platform lamps were asked for at h=2 BEFORE the post that fills h=0..2 was built,
        so each was refused for empty air and then had a post put through its own cell

    That is this repo's most-repeated failure shape - *a thing that does nothing, quietly* - and
    it is why `_lamp` returns a bool at all. Every light placed here is counted and the count is
    returned, so a lamp that does not land shows up as a number rather than as a dark ride.

    What the rider passes, in order round the circuit: a MAUSOLEUM standing in the middle of the
    hall, a closed tomb with a barred window on each of its four faces and a lantern burning
    behind each grille; two raised tombs with a skull and a lit candle standing proud in the side
    alleys; four chained lanterns hung from the hall's own lid at the corners; and - added with
    the gallery - FOUR ROOF BEACONS standing on the tomb's lid.

    **THE BEACONS EXIST BECAUSE THE RIDE GAINED A SECOND LEVEL.** Every light in this building
    used to sit at h=1 to h=3, which is right for a track that never leaves the floor and wrong
    the moment a leg crosses the hall at h=5: on the crest a rider is ABOVE every lamp in the
    room, looking at the dark top of a tomb. A lantern on a short post at the lid's four corners
    is at the gallery's own eye height, so the crest is the best-lit part of the ride rather than
    the darkest - which is the whole reason to climb.

    **NOTHING HERE MAY STAND IN A TRACK COLUMN.** The mausoleum is inset two cells from the
    climbing alleys on all four sides and every prop outside it sits in the alley between - and
    that is not trusted to arithmetic: `circ.owns` is consulted per cell, and `_Circuit.verify`
    re-asks it against the finished world.
    """
    mi0, mi1 = i0 + 2, i1 - 2
    md0, md1 = 2, depth - 4
    TOP = 3                                    # the tomb's wall head; a ground rider's eye is h=1
    out = {"lamps": 0, "webs": 0, "windows": 0, "tombs": 0, "chandeliers": 0, "beacons": 0,
           "bounds": [mi0, mi1, md0, md1]}
    if mi1 - mi0 < 4 or md1 - md0 < 4:
        return out                             # no room for a centrepiece; leave the hall empty

    def free(i, d, h):
        return circ is None or not circ.owns(i, d, h)

    # THE WINDOWS ARE DECIDED BEFORE THE WALL IS DRAWN, never cut out of it afterwards. `put`
    # overwrites and cannot remove, so an opening made after the ring exists has to repaint cells
    # that are already there - which is exactly how the void tower shipped a plain drum where it
    # had "alternated" merlons over a course it had already filled.
    ci, cd = (mi0 + mi1) // 2, (md0 + md1) // 2
    lights = [(ci, md0, 1), (ci, md1, -1), (mi0, cd, 1), (mi1, cd, -1)]
    win = {(i, d, h) for (i, d, _s) in lights for h in (1, 2)}

    for i in range(mi0, mi1 + 1):
        for d in range(md0, md1 + 1):
            if i in (mi0, mi1) or d in (md0, md1):
                for h in range(TOP + 1):
                    if (i, d, h) in win or not free(i, d, h):
                        continue
                    x, y, z = f.at(i, d, h)
                    # weathered per CELL - hashed on the course, a course comes out all one
                    # material and the wall is horizontal stripes (the deck soffit's own bug)
                    w.put(x, y, z, ex["aged"] if hash01(x, y, z) < 0.18 else pal["wall"])
            if free(i, d, TOP + 1):
                w.put(*f.at(i, d, TOP + 1), pal["trim"])      # the lid, and the tomb is closed

    for (i, d, s) in lights:
        along_i = d in (md0, md1)
        for h in (1, 2):
            w.put(*f.at(i, d, h), "iron_bars", **_bars(f, along_i))
        # THE LANTERN BURNS BEHIND THE GRILLE, on a pedestal of its own. The tomb's interior
        # floor is the module's pad at h=-1, so a lantern asked for at h=1 has nothing under it -
        # the same refusal that left this building dark in the first place.
        (pi, pd) = (i, d + s) if along_i else (i + s, d)
        w.put(*f.at(pi, pd, 0), pal["trim"])
        if _lamp(w, *f.at(pi, pd, 1), pal["light"]):
            out["lamps"] += 1
        out["windows"] += 1

    # THE ROOF BEACONS, at the GALLERY's own eye height. A post on the lid and a lantern on top
    # of it: standing, not hanging - written `hanging=true` a lamp looks for a block ABOVE it,
    # finds the hall's open air, and hangs from nothing.
    for (bi, bd) in ((mi0 + 1, md0 + 1), (mi1 - 1, md0 + 1),
                     (mi0 + 1, md1 - 1), (mi1 - 1, md1 - 1)):
        if not free(bi, bd, TOP + 2) or not free(bi, bd, TOP + 3):
            continue
        w.put(*f.at(bi, bd, TOP + 2), pal["post"])
        if _lamp(w, *f.at(bi, bd, TOP + 3), pal["light"]):
            out["lamps"] += 1
            out["beacons"] += 1

    # THE TOMBS, proud in the side alleys where a rider passes within one cell of them.
    for (ti, td) in ((mi0 - 1, md0 + 1), (mi1 + 1, md1 - 1)):
        w.put(*f.at(ti, td, 0), ex["aged"])
        w.put(*f.at(ti, td + 1, 0), ex["aged"])
        w.put(*f.at(ti, td, 1), pal["trim"])
        w.put(*f.at(ti, td, 2), "skeleton_skull", rotation="0", powered="false")
        w.put(*f.at(ti, td + 1, 1), "candle", candles="2", lit="true", waterlogged="false")
        out["lamps"] += 1
        out["tombs"] += 1

    # THE CHANDELIERS. A lantern hangs from a chain, and a chain is not a full cube - so `_lamp`
    # correctly refuses it and the hanging state is stated here instead.
    for (hi, hd) in ((mi0 - 1, md0 - 1), (mi1 + 1, md0 - 1),
                     (mi0 - 1, md1 + 1), (mi1 + 1, md1 + 1)):
        for h in range(4, height):
            _member(w, *f.at(hi, hd, h), "iron_chain", "y")
        w.put(*f.at(hi, hd, 3), pal["light"], hanging="true", waterlogged="false")
        out["lamps"] += 1
        out["chandeliers"] += 1

    for (bi, bd, bh) in ((1, 1, height - 1), (width - 2, 1, height - 1),
                         (1, depth - 2, height - 1), (width - 2, depth - 2, height - 1),
                         (mi0 - 1, md0 + 3, TOP), (mi1 + 1, md1 - 3, TOP),
                         (mi0 + 3, md0 - 1, TOP), (mi1 - 3, md1 + 1, TOP)):
        if free(bi, bd, bh):
            out["webs"] += _web(w, f, bi, bd, bh)
    return out


def _ghosttrain(w: World, p: dict, ctx) -> dict:
    """A RIDE, AND A JOURNEY RATHER THAN A LAP. **This is the ride the park was rejected over** -
    *"the hollow rollercoaster which is just a circle feel pointless and weird filler"* - and it
    was a flat rectangle inside a sealed box: fifty cells at one course, in one door and out the
    other, past a tomb you saw once from one side.

    What it is now, in the order you ride it:

        1. board on the lit platform OUTSIDE the facade, at ground
        2. run the FRONTAGE past the queue - the ride is visible from the street, which is the
           thing the zone was told it lacked
        3. IN through the left arch at ground, into the dark
        4. CLIMB the west alley five courses, passing the mausoleum's west grille
        5. cross the whole back leg on a GALLERY at h=5, looking DOWN on the lit tomb roof and
           level with the hung lanterns
        6. FALL five courses down the east alley, past the east grille and the candle-lit tombs
        7. OUT through the right arch, and back along the frontage to the platform

    So: a climb, a crest, a fall, and the same set pieces seen from two heights rather than one.
    Ten courses of vertical over a 58-cell lap, four corners, in a footprint that did not grow.

    **THE FRONT LEG MOVED OUT OF THE WALL AND THAT FIXED TWO THINGS AT ONCE.** It used to run in
    the front wall's own plane, so the loop overwrote the wall's ground course and left the
    course above solid - eleven track cells with a block on the rider's head - and the cure at
    the time was to leave a slot at h=1. With two courses of headroom now required rather than
    one, that slot would have had to be two courses of open wall the length of the frontage. Run
    OUTSIDE at d=-2 instead, the arch is the only thing the track passes through, the facade is a
    facade again, and the carts run past the people waiting for them.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    width = max(17, int(p["width"] or 21))
    depth = max(13, int(p["depth"] or 15))
    height = 12
    mr = int(p["min_run"])
    entry_i, exit_i = 3, width - 4
    GALLERY = 5                                 # the crest, in courses over the hall floor

    # ---- THE CIRCUIT IS PLANNED BEFORE ANYTHING IS BUILT, so every structural loop below can
    # ask whether a cell belongs to the rider before it takes it. The two waypoints at d=1 are
    # COLINEAR - they exist to hold the arch passage flat, because an ascending rail in a
    # four-course opening is a rider's head in the lintel.
    front_d = -2
    back_d = depth - 2
    wps = [(entry_i, front_d, 0), (entry_i, 1, 0), (entry_i, back_d, GALLERY),
           (exit_i, back_d, GALLERY), (exit_i, 1, 0), (exit_i, front_d, 0),
           (entry_i, front_d, 0)]
    circ = _Circuit(wps, int(p["power_every"]), pier_every=3, what="the Ghost Train's circuit")

    _pad(w, f, pal, width, depth, margin=2)

    # THE WHOLE SHELL, ONE PASS: the facade IS the front wall of the perimeter, with two ARCHED
    # openings left EMPTY BY THE LOOP - building the ring first and cutting a hole afterwards
    # repaints cells that already exist, which the void tower's own crenellations paid for once.
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

    # THE SET PIECES - a mausoleum with lit grilles, tombs and chandeliers, plus the ROOF BEACON
    # the gallery run needed: at h=5 a rider is above every ground-level lamp in the building, so
    # a dark ride whose lights are all at h=1 goes dark for the whole crest.
    scenes = _ghost_scenes(w, f, pal, ex, width, depth, height, entry_i, exit_i, circ)
    lamps = scenes["lamps"]

    # A BOARDING PLATFORM in front of the facade, OUTSIDE the track, lit and signed. The floor is
    # h=-1, matching `_pad`: built at h=0 it sat one course above its own margin and read as one
    # connected piece in every render while being, in world coordinates, floating beside it.
    for i in range(-2, width + 2):
        for d in (-3, -4, -5):
            w.put(*f.at(i, d, -1), pal["path"] if (i + d) % 2 else pal["ground"])
    # a queue rail along the platform's outer edge, with the way through left open at the middle
    for i in range(-2, width + 2):
        if abs(i - width // 2) <= 2:
            continue
        w.put(*f.at(i, -5, 0), pal["fence"])
    for i in (-2, width + 1):
        # THE POST GOES IN BEFORE THE LAMP THAT STANDS ON IT. Asked for first, at h=2, the lamp
        # was refused for empty air - and then the post was driven through the cell it had just
        # been refused. Both platform lights were missing and nothing said so.
        for h in range(3):
            w.put(*f.at(i, -3, h), pal["post"])
        if _lamp(w, *f.at(i, -3, 3), pal["light"]):
            lamps += 1

    title = str(p.get("title") or "GHOST TRAIN").upper()
    signed = _sign(w, f, pal, width // 2, -1, height - 3, f.facing,
                   [title[:SIGN_WIDTH], "", "dare to ride", ""])
    # ...and a second sign at EYE LEVEL beside the entry arch, because a name eight courses up
    # says what the building is and not what you do at it. It hangs on the wall two columns
    # outside the arch - the arch's own column is an OPENING, and `_sign` refuses a support that
    # is not there rather than shipping a sign attached to nothing.
    boarded = _sign(w, f, pal, max(0, entry_i - 2), -1, 2, f.facing,
                    ["RIDE THE CART", "board here", "one at a time", ""])

    # ---- THE TRACK, LAID LAST so nothing can quietly take one of its cells, and then VERIFIED
    # against the finished world rather than against the arithmetic that placed everything else.
    loop = circ.lay(w, f, pal, deck=ex["rock"], pier=pal["post"])
    circ.verify(w, f)

    return {"kind": "ghosttrain", "width": width, "depth": depth, "height": height,
            "track": loop["track"], "corners": loop["corners"],
            "powered": loop["powered"], "lamps": lamps,
            "rise": loop["rise"], "fall": loop["fall"], "gallery": GALLERY,
            "piers": loop["piers"], "iron_ingots": loop["iron_ingots"],
            "gold_ingots": loop["gold_ingots"], "redstone_blocks": loop["redstone_blocks"],
            "signed": bool(signed) and bool(boarded), "signs": int(signed) + int(boarded),
            "boarding_at": list(f.at(width // 2, -3, 0)),
            "approach_at": list(f.at(width // 2, depth + 1, 0)),
            "entry_at": list(f.at(entry_i, 0, 0)), "exit_at": list(f.at(exit_i, 0, 0)),
            "windows": scenes["windows"], "tombs": scenes["tombs"],
            "chandeliers": scenes["chandeliers"], "webs": scenes["webs"],
            "beacons": scenes["beacons"], "tomb_bounds": scenes["bounds"],
            "contract": "a closed, powered minecart circuit that boards OUTSIDE the facade, runs "
                        "the frontage past the queue, enters the left arch at ground, climbs %d "
                        "courses up the west alley, crosses the whole back leg on a gallery "
                        "looking down on the lit tomb, falls %d courses down the east alley and "
                        "leaves by the right arch. %d cells, %d corners, %d courses of rise and "
                        "the same of fall. VERIFIED: closed, every run powered at both ends, "
                        "every corner flat on both sides, every elevated cell carried to the "
                        "apron, two clear courses over every rail cell, and the platform "
                        "walkable from the zone's own paving. NOT verified: cart speed - there "
                        "is no cart-physics model here, so ride it once before anyone is told it "
                        "completes the lap."
                        % (loop["rise"], loop["fall"], loop["track"], loop["corners"],
                           loop["rise"])}


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
