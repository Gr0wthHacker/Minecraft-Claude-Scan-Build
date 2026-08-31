"""The Park Line: a skyway and a railway joining three skyblock islands that do not touch.

THE PARK IS THREE ISLANDS AND YOU CANNOT GET BETWEEN THEM. `islandleft` (frontier),
`newisle` (midway, the entrance) and `islandright` (hollow) sit at bedrock Z 80400 / 80600 /
80800 with **~100 blocks of open void** between each pair. The centre zone carries a Frontier
Arch on its north edge and a Hollow Arch on its south edge and both of them lead to nothing at
all: a visitor arrives at the gate and can reach one third of the park.

Two kinds, and a third that composes them:

    skyway    the span - a viaduct on piers and arches carrying a walkway AND a rail line
    station   a terminal - platform, canopy, boarding gate, departure board, benches, stair
    line      the whole system: one track, one deck, three stations, end to end

**THE LINE IS DEAD STRAIGHT AND DEAD LEVEL, AND THAT IS THE DESIGN.** Read off `blocks.json`
rather than remembered:

    powered_rail  shape = north_south, east_west, ascending_{n,s,e,w}
    rail          shape = ...those six, PLUS south_east, south_west, north_west, north_east

A POWERED RAIL CANNOT CURVE, so every direction change is a normal rail and therefore IRON -
and on this server iron is the scarce metal while gold is farmable (6 gold -> 6 powered rails;
6 iron -> 16 plain ones). The Island Line paid for that lesson with a square helix instead of a
round one. Here the three islands lie on one axis, so a straight Z-axis run needs **no corner
at all**: the whole railway costs ZERO iron and its metal is entirely gold. Every rail on it is
a powered rail and every one of them carries signal.

AN UNPOWERED POWERED_RAIL IS A BRAKE. That is what makes "all powered rail" different in kind
from "mostly rail": you cannot lay 357 of them and energise some. The bed cell under the track
becomes a `redstone_block` every `power_every` cells - and the runs are counted BETWEEN CORNERS
(`railspiral.runs_of`), because a plain rail does not propagate the chain. Nothing about the
emitted model looks wrong when this is missed: `shape` and `powered` are DERIVED by the game
(neither is in `work.INTENTIONAL`, exactly as a stair's shape is not), so the schematic, the
audit and the bill of materials all pass while the line does not run.

NEVER DESCEND INTO A CORNER. A curve has no ascending shape either, so a corner and both of its
neighbours must sit at one height. This line has no corners and no slopes, so the rule costs it
nothing - but `shapes_for` is shared with `railspiral` so that the rule is enforced by one
implementation rather than two, and `tests/test_transit.py` exercises it on a synthetic bent and
sloped path rather than pretending a straight line has tested it.

A TERMINUS NEEDS A BLOCK BEHIND IT. A stationary cart on a powered rail launches AWAY from the
adjacent solid block, so each end gets a stop block or the line only runs whichever way you
happened to shove the cart. Two stops, so it runs both ways - which is the whole point: a
visitor has to be able to come back.

**THE CORRIDOR WAS MEASURED, NOT CHOSEN.** Every park module of all three zones was loaded and
binned by X: content runs 97551..97642 and there is **not one cell at X >= 97643 in any zone**,
at any height, over the whole Z of every plot. The plots end at X 97649. So the line runs down
the east edge on X 97643..97648 with the track at 97646, and it collides with nothing. It is
also where each zone's own paving comes closest to it - all three plazas sit at X 97639, and
each zone has floor reaching X 97638+ over a long Z run (left 80360..80439, centre 80560..80639,
right 80760..80839), which is what the station stairs land beside.

**THE DECK IS FOUR COURSES OVER THE STREET, AND THE NUMBER IS THE STAIR'S.** The park's floor
blocks are at Y202 and you stand at Y203; the deck floor is Y206 and the rail Y207. Four courses
is exactly a four-tread flight, and the flight has to fit in the four columns X 97640..97643
that are free of park content beside the station - one course per cell is the most a stair can
fall. Higher and the flight runs out of ground before it runs out of height; lower and the
viaduct is a road.

WHAT MAKES 350 BLOCKS OF SPAN READ AS ARCHITECTURE IS REGULARITY AND OPENINGS, NOT LENGTH - the
void tower's rule, and a viaduct is the purest case of it. A bay repeats every `bay` cells: a
pier dropping into the void, a segmental arch springing from it to a crown just under the deck,
and a portal frame over the deck so you ride and walk THROUGH something. The spandrels are left
open on purpose; filling them is 3,000 blocks of wall and turns an arcade into a plank on edge.

THE LIGHT IS THE DECK, NOT A FIXTURE ON IT. The span hangs over void and unlit it is a mob
highway into the park. A `lantern` costs iron - 45 of them would be more metal than the entire
railway - so the lamps are `ochre_froglight` set FLUSH IN THE DECK EDGE, which is this island's
own idiom (Island Night, the lowland turf), costs no metal, cannot be knocked off a walkway a
hundred blocks over the void, and leaves the deck clear to walk. A flush froglight reaches 14
rather than 15 - it IS the floor, an opaque emitter a course down - and that is what the spacing
is set against. One tone the whole way: verdant and pearlescent froglight stock on this server
is zero, so the cold half of the gradient is carried by the STONE and not by the light.

GEOMETRY, stated once because getting it wrong is invisible in every render:

    a   runs ALONG the line, a=0 at the first track cell, +a in the direction of travel
    s   runs across it; +s is +X for a Z-axis line, +Z for an X-axis one
    h   courses up from the RAIL, so the deck floor is h=-1 and the street is h=-5

so `at(a, s, h)` is the one place the axis is resolved and a facing bug is one bug.
"""
from __future__ import annotations

import math

from . import park
from .canvas import Canvas, hash01
from .railspiral import power_cells, runs_of, shapes_for
from .vertical import Ctx, World

_ALONG = {"z": (0, 1), "x": (1, 0)}
_PERP = {"z": (1, 0), "x": (0, 1)}
_NAME = {(0, 1): "south", (0, -1): "north", (1, 0): "east", (-1, 0): "west"}

SIGN_WIDTH = park.SIGN_WIDTH        # fifteen characters; a line clips mid-word past it
PLOT_RADIUS = 49                    # measured: placed content is bedrock +/- 49 on both axes

# The span's own masonry, per land. NOT the same table as `park.LANDS` and not a second copy of
# it either: a viaduct wants a value LADDER between deck, kerb and arch, and a land's own trim is
# chosen for a wall rather than for a soffit read from below. Every step here is >= 15 luminance,
# which is the threshold under which a trim course stops reading as a line - measured ACROSS
# material families, because inside one family a ladder cannot exist by construction and this
# repo has concluded three times over that the economy has no contrast by searching inside one.
#
#     midway    black_wool 21  <  stone_bricks 122  <  smooth_stone 159
#     frontier  spruce_log 41  <  spruce_planks 89  <  cobblestone 127
#     hollow    black_wool 21  <  polished_blackstone_bricks 45  <  deepslate_bricks 71
SPAN = {
    "midway": {"deck": "stone_bricks", "kerb": "black_wool",
               "pier": "stone_bricks", "arch": "smooth_stone"},
    "frontier": {"deck": "cobblestone", "kerb": "spruce_log",
                 "pier": "spruce_log", "arch": "spruce_planks"},
    "hollow": {"deck": "polished_blackstone_bricks", "kerb": "deepslate_bricks",
               "pier": "polished_blackstone_bricks", "arch": "black_wool"},
}

# One tone the whole way, and it is stated rather than assumed: verdant and pearlescent
# froglight stock on this server is zero, so a cold lamp for the Hollow half would have to be a
# `soul_lantern` - which is iron, on the one line whose whole economy argument is that it spends
# none. The gradient is carried by the stone.
LAMP = "ochre_froglight"

TRANSIT = {
    "under": None,
    "kind": "line",
    "axis": "z",                # the line's axis; "z" or "x"
    "forward": 1,               # +1 walks the axis upward, -1 downward
    "at": None,                 # world [x, y, z] of the FIRST TRACK CELL; y is the RAIL course
    "length": None,             # track cells, including both termini
    "land": "midway",           # the land used when no station says otherwise
    "deck_left": 3,             # deck cells on the -s side of the track (the park side)
    "deck_right": 2,            # deck cells on the +s side
    "bay": 12,                  # pier-to-pier
    "arch_rise": 5,             # how far the arch springs below the deck
    "pier_depth": 9,            # how far a pier drops into the void, from the deck's underside
    "portal_h": 4,              # clear courses under a portal beam
    "power_every": 8,           # a redstone_block in the bed this often, per RUN between corners
    "light_every": 8,           # a froglight flush in the deck edge this often
    "railing_every": 2,
    "band_blend": 24,           # cells over which one land's masonry dithers into the next
    "street_y": None,           # world Y of the STREET FLOOR BLOCK a station stair lands beside
    "stations": None,           # see _station
    "features": None,           # [a] of the mid-span towers; default: the midpoint of each hop
    "title": "THE SKYWAY",
    "avoid": None,              # design .litematic paths whose cells are already somebody's
    "plot_from": None,          # a capture: its bedrock gives the X band the deck must stay in
    "seed": 0,
}

STATION = {
    "at_a": None,               # a of the platform's CENTRE
    "length": 15,               # platform length along the line, odd
    "land": None,
    "title": "STATION",
    "board": None,              # the departure board's four lines
    "stair": -1,                # +1/-1: which way along the line the stair descends
    "back": 6,                  # the back wall stands at s = -back
    "gates": 3,                 # boarding gates in the platform fence
}


# ------------------------------------------------------------------------------ the frame

class _Line:
    """The line's own axes. Everything is placed through this, so an axis bug is one bug."""

    def __init__(self, at, axis="z", forward=1):
        self.x, self.y, self.z = (int(v) for v in at)
        if axis not in _ALONG:
            raise ValueError(f"axis must be 'x' or 'z', got {axis!r}")
        self.axis = axis
        self.fwd = 1 if int(forward) >= 0 else -1
        ax, az = _ALONG[axis]
        self.adx, self.adz = ax * self.fwd, az * self.fwd
        self.pdx, self.pdz = _PERP[axis]

    def at(self, a, s, h=0):
        return (self.x + self.adx * a + self.pdx * s,
                self.y + h,
                self.z + self.adz * a + self.pdz * s)

    @property
    def heading(self):
        return _NAME[(self.adx, self.adz)]

    @property
    def behind(self):
        return _NAME[(-self.adx, -self.adz)]

    def along_name(self, sign):
        return _NAME[(self.adx * sign, self.adz * sign)]

    def perp_name(self, sign):
        return _NAME[(self.pdx * sign, self.pdz * sign)]


def _pal(land):
    """A land's park palette with the span's own masonry laid over it."""
    if land not in park.LANDS:
        raise ValueError(f"unknown land {land!r}; have {sorted(park.LANDS)}")
    return {**park.LANDS[land], **SPAN[land]}


def _sign(w, x, y, z, facing, wood, front, back=()):
    """A wall sign in the cell IN FRONT of its wall, its text facing away from its support.

    THE SUPPORT IS CHECKED, NOT ASSUMED - `park._sign`'s rule, restated in world coordinates
    because a line has no `_Frame`. Written without the check, four of the park's seven kinds
    shipped a sign hung on the one column that has an opening in it, and the mistake is
    invisible in every render: a wall sign floating in air draws exactly like one on a wall.

    Returns True if it was placed. A caller that ignores a False is asking for the bug back.
    """
    fdx, fdz = park._STEP[facing]
    if not w.has(x - fdx, y, z - fdz):
        return False
    lines = [str(t)[:SIGN_WIDTH] for t in list(front)[:4]]
    lines += [""] * (4 - len(lines))
    w.put(x, y, z, f"{wood}_wall_sign", facing=facing, waterlogged="false")
    w.sign(x, y, z, front=lines,
           back=[str(t)[:SIGN_WIDTH] for t in list(back)[:4]], colour="white", glowing=True)
    return True


# ------------------------------------------------------------------------------ the track

def plan(params: dict):
    """THE track for a config: the one entry point the build and the tests both go through.

    Written twice they drift - `railspiral`'s tests called `route` without a ground table, got
    a terminus the design does not have, and reported a missing stop block on a line that has
    one. Same rule `proportions.measure` and `rubric.score` already follow.

    Returns [(x, y, z, is_corner)], which is `railspiral`'s own cell shape, so `shapes_for`,
    `runs_of` and `power_cells` all apply unchanged.
    """
    p = {**TRANSIT, **(params or {})}
    if not p.get("at"):
        raise ValueError("transit needs params.at = [x, y, z] of the first track cell")
    n = int(p.get("length") or 0)
    if n < 4:
        raise ValueError("transit needs params.length >= 4 track cells")
    ln = _Line(p["at"], p["axis"], p["forward"])
    return [(*ln.at(a, 0, 0), False) for a in range(n)]


def _land_at(p, stations, a):
    """Which land's masonry a cell takes: the nearest station's, dithered across the midpoint.

    A HARD SEAM ACROSS A LONG SPAN READS AS TWO VIADUCTS STACKED - the Lowland Stair's finding,
    and the reason its bands dither per CELL rather than per course. The blend is centred on the
    midpoint between two stations, which on this line falls in the middle of the open void: the
    park changes colour where there is nothing but sky to see it against, which is the one place
    a change of material cannot look like a mistake.
    """
    if not stations:
        return p["land"]
    if a <= stations[0]["at_a"]:
        return stations[0]["land"]
    if a >= stations[-1]["at_a"]:
        return stations[-1]["land"]
    for i in range(len(stations) - 1):
        a0, a1 = stations[i]["at_a"], stations[i + 1]["at_a"]
        if not (a0 <= a <= a1):
            continue
        blend = max(1, int(p["band_blend"]))
        mid = (a0 + a1) / 2.0
        if a < mid - blend / 2.0:
            return stations[i]["land"]
        if a > mid + blend / 2.0:
            return stations[i + 1]["land"]
        t = (a - (mid - blend / 2.0)) / float(blend)
        return stations[i + 1]["land"] if hash01(a, i, int(p["seed"]), 91) < t \
            else stations[i]["land"]
    return p["land"]


# ------------------------------------------------------------------------------ the span

def _deck(w, ln, p, cells, land_of, avoid, meta):
    """Deck, track, power, railings and lamps: everything at or above the deck floor."""
    left, right = int(p["deck_left"]), int(p["deck_right"])
    shapes = shapes_for(cells)
    powered = power_cells(cells, int(p["power_every"]))
    rail_every = max(1, int(p["railing_every"]))
    sources = []

    for a in range(len(cells)):
        pal = _pal(land_of(a))
        for s in range(-left, right + 1):
            edge = s in (-left, right)
            blk = pal["kerb"] if edge else pal["deck"]
            if s == 0:
                # THE BED FIRST, and the bed is the track's own floor. A redstone_block here is
                # not decoration: an unpowered powered rail is a brake, so this cell IS the
                # railway. The worklist sorts bottom-up so it is in before the rail lands on it.
                blk = "redstone_block" if a in powered else pal["deck"]
                if a in powered:
                    sources.append(list(ln.at(a, 0, -1)))
            w.put(*ln.at(a, s, -1), blk)
        # A TRACK CELL IS NOT OPTIONAL. Dressing may yield anywhere; a skipped rail is a GAP,
        # and a gap in a line hanging over the void is a cart in the void. Nothing is consulted
        # here - not the avoid set, not the world - and anything that would contest the track is
        # a fatal error raised by `_check` before a block is placed.
        w.put(*ln.at(a, 0, 0), "powered_rail", shape=shapes[a])
        # the railing, on both kerbs. A fence over a flush lamp is fine - a fence is not a full
        # cube, so light passes it; a POST is what puts a lamp out, and `_lamps` runs last so it
        # can see one.
        if a % rail_every == 0:
            for s in (-left, right):
                w.put(*ln.at(a, s, 0), pal["fence"])

    # THE STOPS. A stationary cart on a powered rail is launched away from the adjacent solid
    # block. Two of them, one at each terminus, because the line has to run BOTH WAYS: a visitor
    # who cannot come back has not been connected to anything.
    stops = []
    for a, out in ((0, -1), (len(cells) - 1, 1)):
        pal = _pal(land_of(a))
        w.put(*ln.at(a + out, 0, 0), pal["kerb"])
        w.put(*ln.at(a + out, 0, -1), pal["deck"])
        stops.append(list(ln.at(a + out, 0, 0)))
    meta["power_sources"], meta["stops"] = sources, stops
    return powered, shapes


def _arcade(w, ln, p, n, land_of, meta):
    """The bays: a pier into the void, a segmental arch, and a portal frame over the deck.

    A VIADUCT IS THE PUREST CASE OF THE VOID TOWER'S RULE - regularity and openings. The
    spandrel between an arch and the deck is left OPEN deliberately: filling it is three
    thousand blocks of wall and turns an arcade into a plank on edge. The openings are the
    architecture; the blocks are only what holds them apart.
    """
    left, right = int(p["deck_left"]), int(p["deck_right"])
    bay = max(4, int(p["bay"]))
    rise = max(1, int(p["arch_rise"]))
    depth = max(rise + 2, int(p["pier_depth"]))
    ph = max(3, int(p["portal_h"]))
    piers, arches, portals = 0, 0, 0

    def soffit(u):
        """The intrados: lowest at the springing, crown one course under the deck."""
        return -2 - int(round(rise * (1.0 - math.sin(math.pi * min(1.0, max(0.0, u))))))

    for b in range(0, n, bay):
        pal = _pal(land_of(min(b, n - 1)))
        # THE PIER, two cells thick along the line so it reads as a pier and not as a thread.
        for a in (b, b + 1):
            if not 0 <= a < n:
                continue
            for s in (-left, right):
                for h in range(-2, -2 - depth, -1):
                    w.put(*ln.at(a, s, h), pal["pier"])
                piers += 1
        # A FLARED BASE, so the pier ENDS rather than stopping - and it is a BOTTOM SLAB, which
        # is not decoration. A full block here is a 1x1 shelf nine courses under the deck, open
        # to the sky, that a mob spawns on and drops off; a bottom slab is the same silhouette
        # and nothing can stand on it. The two cells under the pier itself keep their full block
        # because the shaft is already standing on them.
        for a in (b - 1, b + 2):
            if not 0 <= a < n:
                continue
            for s in (-left, right):
                w.put(*ln.at(a, s, -1 - depth), pal["slab"],
                      type="bottom", waterlogged="false")
        # THE PORTAL over the deck: posts on both kerbs and a beam across, so you ride and walk
        # THROUGH something. Four clear courses under the beam - a player needs two.
        for a in (b, b + 1):
            if not 0 <= a < n:
                continue
            for s in (-left, right):
                for h in range(0, ph):
                    w.put(*ln.at(a, s, h), pal["post"])
            for s in range(-left, right + 1):
                w.put(*ln.at(a, s, ph), pal["beam"])
            portals += 1
        # THE ARCH, springing from this pier to the next. One cell thick, and FILLED VERTICALLY
        # between consecutive cells: a swept curve whose cells are only diagonal neighbours is
        # not connected at all, which is how the ear tips came off the first cats.
        span = min(bay, n - b) - 2
        if span < 3:
            continue
        prev = None
        for k in range(span + 1):
            a = b + 2 + k
            if a >= n:
                break
            u = k / float(span)
            hy = soffit(u)
            lo, hi = (hy, hy) if prev is None else (min(hy, prev), max(hy, prev))
            for h in range(lo, hi + 1):
                for s in (-left, right):
                    w.put(*ln.at(a, s, h), pal["arch"])
            prev = hy
            arches += 1
    meta["piers"], meta["arch_cells"], meta["portals"] = piers, arches, portals



def _lamps(w, ln, p, n, land_of, meta):
    """The deck's lights, placed LAST and only where they can actually shine.

    **A LAMP UNDER A POST IS NOT A LAMP.** The first build set a froglight flush in the deck
    edge every 8 cells and a portal post on the same kerb every 12, and every 24 cells the two
    landed in the same column: the post sits directly over the lamp, light cannot leave an
    opaque cell into another opaque cell, and 127 deck cells stood at block light ZERO on a span
    the design believed it had lit. Nothing in the model looks wrong - the lamp is placed, it is
    the right block, the bill of materials counts it. Only propagating the light finds it.

    So the pass runs after the arcade and the towers, and slides each nominal position to the
    nearest column whose cell ABOVE is clear. A fence is fine to stand under - it is not a full
    cube and light passes it - and that distinction is the whole check.
    """
    every = max(0, int(p["light_every"]))
    if not every:
        meta["lamps"] = []
        return
    left, right = int(p["deck_left"]), int(p["deck_right"])
    lamps, missed = [], 0
    from .. import blocks as _blocks

    def blocked_above(a, s):
        name = w.name(*ln.at(a, s, 0))
        if name is None:
            return False
        try:
            return _blocks.is_full_cube(name)
        except Exception:
            return True

    # THE LAMPS ALTERNATE KERBS, which is not a stylistic choice. All on one edge, the far kerb
    # is `deck_left + deck_right` cells away and anything standing on a portal beam over it - a
    # real surface, five courses up - measured block light ZERO. Alternating halves the worst
    # crossing distance and lights the park-facing edge, which is the one people see.
    for i, a0 in enumerate(range(0, n, every)):
        s = right if i % 2 == 0 else -left
        pick = None
        for d in range(0, every):
            for a in ([a0] if d == 0 else [a0 + d, a0 - d]):
                if 0 <= a < n and not blocked_above(a, s):
                    pick = a
                    break
            if pick is not None:
                break
        if pick is None:
            missed += 1
            continue
        w.put(*ln.at(pick, s, -1), LAMP)
        lamps.append(list(ln.at(pick, s, -1)))
    meta["lamps"], meta["lamps_unplaceable"] = lamps, missed


def _feature(w, ln, p, a, land_of, meta, subtitle=()):
    """The mid-span tower: the thing that makes a hundred blocks of span have a MIDDLE.

    A repeating bay carries a span; it does not give it a centre, and a crossing with no centre
    reads as a corridor however well it is detailed. This is a taller portal with a solid crown,
    crenellations, hanging lamps and the crossing's name on it - and it stands where the two
    lands' masonry is dithering into each other, so the one place the span changes colour is
    also the one place it has a landmark.
    """
    left, right = int(p["deck_left"]), int(p["deck_right"])
    ph = max(3, int(p["portal_h"]))
    pal = _pal(land_of(a))
    top = ph + 4
    for k in (0, 1):
        for s in (-left, right):
            for h in range(0, top + 1):
                w.put(*ln.at(a + k, s, h), pal["post"])
        for s in range(-left, right + 1):
            w.put(*ln.at(a + k, s, top - 1), pal["wall"])
            w.put(*ln.at(a + k, s, top), pal["kerb"])
    # THE CROWN COURSE IS LEFT EMPTY BY THE LOOPS ABOVE for the merlons to alternate into.
    # Building a full ring first and alternating over it repaints cells that already exist -
    # it alternates perfectly, changes nothing, and the crown ships as a plain drum.
    merlons = 0
    for k in (0, 1):
        for s in range(-left, right + 1):
            if (s + k) % 2:
                continue
            w.put(*ln.at(a + k, s, top + 1), pal["kerb"])
            merlons += 1
    # THE BEACON IS THE MASONRY, NOT A LANTERN ON IT. A lantern is iron, on the one line whose
    # whole economy argument is that it spends none, and a hanging lamp on a tower over the void
    # is a lamp somebody knocks off. Two froglights set into the crown panel itself light the
    # tower and the deck under it and cost nothing.
    for s in (-left + 1, right - 1):
        for k in (0, 1):
            w.put(*ln.at(a + k, s, top - 1), LAMP)
            # ...and in the crown's own top course, or the merlons themselves are a lit tower's
            # one dark shelf: block light does not climb two courses through solid stone.
            w.put(*ln.at(a + k, s, top), LAMP)
    # The name hangs off the crown's own panel, one cell back along the line, so its support is
    # a block this function has already placed rather than a hope.
    lines = [str(p.get("title") or "THE SKYWAY")[:SIGN_WIDTH], ""] + list(subtitle)[:2]
    named = _sign(w, *ln.at(a - 1, 0, top - 1), ln.behind, pal["wood"], lines)
    meta.setdefault("features_built", []).append(
        {"a": a, "at": list(ln.at(a, 0, 0)), "merlons": merlons, "named": bool(named)})


# ------------------------------------------------------------------------------ the station

def _station(w, ln, p, st, land_of, avoid, meta):
    """A terminal: platform, canopy, back wall, boarding gates, departure board, benches, stair.

    THE STAIR IS THE HALF THAT MAKES THE LINE USABLE. A viaduct four courses over the street is
    a viaduct you cannot get onto, and 'you can see the platform from the plaza' is not the same
    as 'you can board'. It descends ALONG the line on the platform's own western strip - never
    across it, which would cut the through-walkway - and lands on a pad at street level whose
    outer edge is one cell from the zone's own paving.

    A CELL THE PARK ALREADY OWNS IS NOT OURS TO PLACE. The zones' paving reaches X 97640 in
    places, so the pad and the stringer skip anything in `avoid` and the park's own floor serves
    - which is what makes the two designs meet rather than fight. That is only safe below the
    deck: the track and the deck never yield, and `_check` refuses the build if they would have
    to.
    """
    s0 = {**STATION, **st}
    land = s0.get("land") or p["land"]
    pal = _pal(land)
    a_c = int(s0["at_a"])
    half = max(3, int(s0["length"]) // 2)
    a0, a1 = a_c - half, a_c + half
    left, right = int(p["deck_left"]), int(p["deck_right"])
    back = max(left + 2, int(s0["back"]))
    step = 1 if int(s0["stair"]) >= 0 else -1
    street_y = p.get("street_y")
    if street_y is None:
        raise ValueError("a station needs params.street_y - the Y of the street FLOOR block it "
                         "lands beside, or its stair has no bottom")
    drop = (ln.y - 1) - int(street_y)          # deck floor down to the street floor, in courses
    if drop < 2:
        raise ValueError(f"the deck is only {drop} courses over the street: no flight fits")

    # THE PLATFORM: the deck widened west, on the strip the through-deck does not use.
    for a in range(a0, a1 + 1):
        for s in range(-back, -left):
            w.put(*ln.at(a, s, -1), pal["deck"] if s > -back else pal["kerb"])
    # THE BACK WALL - and it is the only thing on a station a sign can hang from. An open
    # platform has no wall, which is the stall's fascia problem in a different hat.
    for a in range(a0, a1 + 1):
        for h in range(0, 4):
            w.put(*ln.at(a, -back, h), pal["wall"] if h < 3 else pal["kerb"])
    # THE CANOPY, two colours alternating: one colour is a roof, two is a station.
    ca, cb = pal["canopy"]
    for a in range(a0, a1 + 1):
        for s in range(-back, right + 1):
            w.put(*ln.at(a, s, 4), ca if a % 2 == 0 else cb)
    # A ROOF IS A FLOOR TO WHATEVER IS ON TOP OF IT. A station canopy is ~135 cells of open,
    # unlit surface directly over the platform, which is a mob spawning above the one place
    # visitors queue. Two froglights set into the roof itself light the whole of it and cost
    # nothing; hanging a lamp under it would light the platform and leave the roof dark.
    for a in (a0 + (a1 - a0) // 4, a1 - (a1 - a0) // 4):
        w.put(*ln.at(a, (right - back) // 2, 4), LAMP)
    for a in range(a0, a1 + 1, 4):
        for h in range(0, 4):
            w.put(*ln.at(a, right, h), pal["post"])

    # THE BOARDING GATE. A fence between the platform and the track, with gates in it: without
    # one the 'platform' is just more walkway and nothing says where you get on. The through
    # walkway survives on the far side of it, which is what keeps the walk across continuous.
    gates = max(1, int(s0["gates"]))
    stops = [a0 + 2 + k * max(2, (a1 - a0 - 4) // max(1, gates - 1)) for k in range(gates)] \
        if gates > 1 else [a_c]
    boarding = []
    for a in range(a0, a1 + 1):
        if a in stops:
            w.put(*ln.at(a, -1, 0), pal["gate"],
                  facing=ln.perp_name(1), open="false", in_wall="false")
            boarding.append(list(ln.at(a, 0, 0)))
        else:
            w.put(*ln.at(a, -1, 0), pal["fence"])

    # BENCHES - stairs, facing the track. Not a flight: a bench is one course and has no rise,
    # so the ascending-tread rule does not apply to it and the test that pins that rule is told
    # which cells are a flight rather than being left to guess from the block name.
    bench = []
    for a in range(a0 + 2, a1 - 1, 5):
        for k in range(3):
            if a + k > a1 - 1:
                break
            w.put(*ln.at(a + k, -back + 1, 0), pal["stair"],
                  facing=ln.perp_name(1), half="bottom", shape="straight", waterlogged="false")
            bench.append(list(ln.at(a + k, -back + 1, 0)))

    # THE DEPARTURE BOARD and the name, on the back wall, facing whoever is on the platform.
    wood = pal["wood"]
    board = list(s0.get("board") or ["DEPARTURES", "", "", ""])
    named = _sign(w, *ln.at(a_c, -back + 1, 2), ln.perp_name(1), wood,
                  [str(s0.get("title") or "STATION")[:SIGN_WIDTH], "", "", ""])
    boarded = _sign(w, *ln.at(a_c - 2, -back + 1, 2), ln.perp_name(1), wood, board)

    # THE STAIR, descending along the line on the platform's own strip.
    flight, skipped = [], 0
    a_head = (a1 + 1) if step > 0 else (a0 - 1)
    for t in range(drop):
        a = a_head + step * t
        for s in range(-back, -left):
            w.put(*ln.at(a, s, -1 - t), pal["stair"],
                  facing=ln.along_name(-step), half="bottom", shape="straight",
                  waterlogged="false")
            flight.append(list(ln.at(a, s, -1 - t)))
            # THE STRINGER, or the flight is a run of treads with nothing under them: the
            # thing you climb has to be attached to the thing you climb it from.
            # ...all the way to the street course, INCLUSIVE. Stopping one short left the
            # lowest tread with nothing under it and the landing pad as a nine-cell island
            # floating beside the flight - one connected piece is the only thing that caught it.
            for h in range(-2 - t, -2 - drop, -1):
                cell = ln.at(a, s, h)
                if cell in avoid:
                    skipped += 1
                    continue
                w.put(*cell, pal["pier"])
    # THE PAD at street level, whose outer edge is 6-adjacent to the zone's own paving. Any cell
    # the park already holds is skipped, not fought over.
    pad = []
    for t in range(drop, drop + 3):
        a = a_head + step * t
        for s in range(-back, -left):
            cell = ln.at(a, s, -1 - drop)
            if cell in avoid:
                skipped += 1
                continue
            w.put(*cell, pal["path"] if s > -back else pal["ground"])
            pad.append(list(cell))
    # ONE LAMP IN THE PAD ITSELF. The deck's lamps are four courses up and eight cells across,
    # and the terminal stations' pads run past the end of the deck entirely - measured, the
    # Hollow pad stood at block light zero, which is a mob spawning on the doormat. It also
    # marks the foot of the stair from across the plaza, which is where you look for it from.
    if pad:
        w.put(*pad[len(pad) // 2], LAMP)

    meta.setdefault("stations_built", []).append({
        "title": s0.get("title"), "land": land, "at": list(ln.at(a_c, 0, 0)),
        "a": a_c, "a0": a0, "a1": a1, "back": back,
        "boarding": boarding, "flight": flight, "bench": bench, "pad": pad,
        "stair_dir": step, "named": bool(named), "board": bool(boarded),
        "skipped_to_park": skipped,
    })


# ------------------------------------------------------------------------------ the checks

def _reserved(paths):
    """Every cell any named design claims. `railspiral._reserved`'s job, kept local so a change
    to one line's reservations cannot silently move the other's."""
    if not paths:
        return set()
    from .railspiral import _reserved as rs_reserved
    return rs_reserved(paths)


def _x_band(p):
    """The X the deck must stay inside: the plots' shared band, DERIVED from the bedrock.

    All three park islands share one X and differ only in Z, so the band is one square's width
    and the line is gated on X alone. **Z IS DELIBERATELY NOT GATED**: the void between two
    plots is exactly what this design exists to cross, and a boundary check that refused it
    would be guarding the wrong thing. NOT FOUND is not the same as INSIDE - with no capture to
    read a bedrock out of, the check reports that it could not be made rather than passing.
    """
    if not p.get("plot_from"):
        return None
    from ..plot import find as find_plot
    plot = find_plot(p["plot_from"], PLOT_RADIUS)
    return (plot.cx - PLOT_RADIUS, plot.cx + PLOT_RADIUS)


def _check(w, ln, p, cells, avoid, band):
    """Refuse a build the track cannot survive, BEFORE a block is placed.

    Both failures here are ones that ship a clean audit: a track cell yielded to another design
    is a gap in a railway that still reads as one connected solid, and a deck cell past the plot
    edge is 120 cells over the line that a HUMAN caught on the Island Run.
    """
    left, right = int(p["deck_left"]), int(p["deck_right"])
    for (x, y, z, _c) in cells:
        if (x, y, z) in avoid or (x, y - 1, z) in avoid:
            raise ValueError(f"track cell {(x, y, z)} is claimed by another design - move the "
                             f"line; a rail that yields is a gap, and a gap is a cart in the void")
    if band:
        lo, hi = band
        for a in range(len(cells)):
            for s in (-left, right):
                x, _y, _z = ln.at(a, s, 0)
                if not lo <= x <= hi:
                    raise ValueError(f"deck column x={x} is outside the plots' shared band "
                                     f"{lo}..{hi} - move the corridor")


# ------------------------------------------------------------------------------ the builders

def _skyway(w: World, p: dict, ctx) -> dict:
    """The span alone: deck, track, arcade, mid-span towers. No stations."""
    ln = _Line(p["at"], p["axis"], p["forward"])
    cells = plan(p)
    n = len(cells)
    stations = [{**STATION, **s} for s in (p.get("stations") or [])]
    for s in stations:
        s.setdefault("land", p["land"])
    avoid = _reserved(p.get("avoid"))
    _check(w, ln, p, cells, avoid, _x_band(p))

    def land_of(a):
        return _land_at(p, stations, a)

    meta = {"track": n, "corners": sum(1 for c in cells if c[3]), "runs": len(runs_of(cells))}
    _deck(w, ln, p, cells, land_of, avoid, meta)
    _arcade(w, ln, p, n, land_of, meta)

    # A MID-SPAN TOWER GOES WHERE THE MASONRY IS ALREADY CHANGING - the midpoint between two
    # stations, which on this line is the middle of the open void. It names both ends, so the
    # one place you cannot see either island is the one place a sign tells you where you are.
    feats, subs = list(p.get("features") or []), []
    if p.get("features") is None and len(stations) >= 2:
        feats = []
        for i in range(len(stations) - 1):
            feats.append(int(round((stations[i]["at_a"] + stations[i + 1]["at_a"]) / 2.0)))
            subs.append([f"{ln.along_name(-1)}  {stations[i]['land'].upper()}",
                         f"{ln.along_name(1)}  {stations[i + 1]['land'].upper()}"])
    for i, a in enumerate(feats):
        if 2 <= int(a) < n - 2:
            _feature(w, ln, p, int(a), land_of, meta, subs[i] if i < len(subs) else ())
    # LAST, so it can see every post that would have put it out. See `_lamps`.
    _lamps(w, ln, p, n, land_of, meta)

    meta["rail"] = [[x, y, z] for (x, y, z, _c) in cells]
    meta["heading"] = ln.heading
    meta["contract"] = ("a continuous deck and a continuous powered-rail line between two "
                        "islands: every rail within power_every of a source, a stop block at "
                        "each terminus so it runs both ways, and a walkway beside the track "
                        "for anyone who misses the train")
    return meta


def _station_only(w: World, p: dict, ctx) -> dict:
    """One terminal, with just enough deck under it to stand on. The kind exists so a station
    can be looked at and tested on its own; `line` is what ships."""
    st = (p.get("stations") or [None])[0]
    if not st:
        raise ValueError("transit/station needs params.stations = [ {...} ]")
    st = {**STATION, **st}
    st.setdefault("land", p["land"])
    if p.get("street_y") is None:
        raise ValueError("transit/station needs params.street_y")
    half = max(3, int(st["length"]) // 2)
    a_c = int(st["at_a"])
    # enough deck either side for the flight to leave the platform and land
    lead = ((int(p["at"][1]) - 1) - int(p["street_y"])) + 4
    local = {**p, "at": list(_Line(p["at"], p["axis"], p["forward"]).at(a_c - half - lead, 0, 0)),
             "length": 2 * half + 1 + 2 * lead, "features": [],
             "stations": [{**st, "at_a": half + lead}]}
    meta = _skyway(w, local, ctx)
    ln = _Line(local["at"], local["axis"], local["forward"])
    _station(w, ln, local, local["stations"][0], lambda a: _land_at(local, local["stations"], a),
             _reserved(p.get("avoid")), meta)
    meta["kind"] = "station"
    meta["contract"] = ("a terminal you can board from the street: a platform behind a fence "
                        "with real gates, a canopy, a departure board on a wall that exists, "
                        "and a flight down to a pad one cell from the zone's own paving")
    return meta


def _line(w: World, p: dict, ctx) -> dict:
    """The whole system, as one design.

    ONE DESIGN, NOT SIX, AND THAT IS THE POINT. Split into a span and three stations they would
    contest the deck cells they share, and `finish.defer_to` would resolve that by DELETING them
    from the loser - so every piece would ship with holes in it and nobody could look at the
    result. The casino spent three rounds on exactly that before it was rebuilt as one.
    """
    meta = _skyway(w, p, ctx)
    ln = _Line(p["at"], p["axis"], p["forward"])
    stations = [{**STATION, **s} for s in (p.get("stations") or [])]
    for s in stations:
        s.setdefault("land", p["land"])
    avoid = _reserved(p.get("avoid"))
    for st in stations:
        _station(w, ln, p, st, lambda a: _land_at(p, stations, a), avoid, meta)
    meta["kind"] = "line"
    meta["contract"] = ("one powered-rail line and one walkway from the frontier island to the "
                        "hollow island through the midway: every rail powered, a stop at each "
                        "terminus so it runs both ways, a station you can reach on foot from "
                        "each zone's own paving, and a deck you can walk end to end if you "
                        "miss the train")
    return meta


BUILDERS = {
    "skyway": _skyway,
    "station": _station_only,
    "line": _line,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**TRANSIT, **(cfg or {})}
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown transit kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in park.LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(park.LANDS)}")
    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)
    ln = _Line(p["at"], p["axis"], p["forward"])
    # THE BOUNDARY IS CHECKED ON WHAT WAS PLACED, not on what was planned. `_check` gates the
    # deck columns before a block goes down, which is what the track needs; a station widens the
    # deck by three more columns after that, and the Island Run shipped 120 cells past the plot
    # edge because its guard was asking about the wrong box.
    band = _x_band(p)
    if band:
        lo, hi = band
        over = [c for c in w.cells if not lo <= c[0] <= hi]
        if over:
            raise ValueError(f"{len(over)} cells are outside the plots' shared X band {lo}..{hi}, "
                             f"first {over[0]} - move the corridor")
        meta["x_band"] = [lo, hi]
    return w.canvas({
        "kind": f"transit/{p['kind']}",
        "land": p["land"],
        "facing": ln.heading,
        "axis": p["axis"],
        "origin": list(p["at"]),
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", [
            "a cart does not stop by itself at the middle station - it is a boarding point, "
            "not an automatic halt. Stopping one needs a detector-and-lever mechanism this "
            "repo's simulator has no model of, and an unverified mechanism does not ship."]),
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
