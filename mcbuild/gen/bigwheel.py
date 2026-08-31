"""THE THREE BIG RIDES: recognised from far away, and RIDEABLE when you get there.

**THEY WERE SCULPTURE AND NOW THEY ARE RIDES.** Jack: *"when relevant - fully functional as
rides"*. Vanilla cannot rotate a structure, so no wheel turns and no carousel spins - but three
mechanics in the game DO carry a player, and each piece now uses the one that suits it:

    wheel      a soul-sand bubble lift up the king post to a gallery at the axle, and a walled
               chute back down into the channel you set off from
    drop       the same lift up the shaft, a platform under the winch house, and fifty courses of
               open shaft into the tank at the bottom
    carousel   an eighty-cell minecart circuit running between two rings of mounts

and one thing that is NOT possible, stated plainly because it is the first thing anybody reaches
for: **A FERRIS WHEEL'S RIM CANNOT CARRY A RAIL.** A rail lies flat and ascends 45 degrees once;
a wheel's rim is vertical at three o'clock and inverted over the top. No diameter, no amount of
iron and no cleverness changes it, so the wheel's ride is the ASCENT rather than the rotation.

Everything about those three is asserted by simulation in `tests/test_bigwheel_rides.py` before it
ships, because this is the subsystem where a clean audit and a broken ride look identical: a water
column with one hole drains onto the platform, a chute with one block in it hurts, and an
unpowered powered_rail is a brake. See THE RIDE MECHANICS below.

WHY THESE THREE SHAPES, AND WHY THEY ARE NOT ANIMALS. `gen/park.py` settled that a park's variety
comes from ARCHITECTURE, and this file is the part of that argument that has to carry across the
zone. A stall reads at fifteen blocks; a skyline piece has to read at a hundred and fifty, from an
angle nobody chose, against open sky - which is exactly the case this repo has measured most often
and got wrong most often. The download corpus says it in one number: the builds strangers pick out
are the ones whose identity is an OUTLINE - a wing, a neck, a ring - and every one of the eight
mammals that failed was a compound volume. So:

    A RING, A COLUMN AND A CONE. All three are voxel primitives, and all three are read from
    OUTSIDE against sky rather than from a path at ground level.

That is not a stylistic preference, it is the one thing this project has evidence for. A ferris
wheel is a circle two cells thick - the medium draws it natively and no amount of tuning is
involved; a drop tower is a straight taper with openings in it, which is the void tower's own
finding (*regularity and openings, not damage*); a carousel is a cone with alternating wedges,
which is a pattern on a convex mass, the ladybird's category.

**EVERY STRUCTURE CARRIES ITS OWN GROUND.** A skyblock plot is VOID. Nothing here may assume
terrain, so each kind lays a pad at h=-1 and everything above it is carried to that pad by legs,
A-frames or a plinth - the wheel's rim hangs 45 courses up and there is a measured line of blocks
from every rim cell to the floor. `tests` in the throwaway harness assert ONE 6-connected
component, because a floating fragment is invisible in every render this repo owns.

**THE FAIRGROUND PALETTE IS THE LAND'S OWN.** Colours come from `park.LANDS[land]`, so a wheel in
the Hollow is a black ring with soul lanterns and a wheel on the Midway is red-and-white - the same
geometry reading as two different places, which is the whole argument for lands over signage. The
only additions are the sixteen wools (all cheap) for gondolas, canopy wedges and carousel mounts,
and `glass_pane` (ok) for the drop tower's glazed panels. Nothing here is expensive, nothing is
currency, nothing falls.

GEOMETRY, identical to `park.py` because a facing bug is invisible and expensive:

    at       the FRONT-LEFT floor corner, in world coordinates
    facing   the direction the FRONT looks out
    i        along the frontage;  d  from the front INTO the piece;  h  courses up

so `at(i, d, h) = (x - dx*d + sx*i, y + h, z - dz*d + sz*i)`. Round things are placed in the same
frame: `i` and `d` index the piece's own bounding footprint and the circle is centred inside it, so
`at` still means the front-left corner and all four facings build the same object.

**VARIETY IS HASHED, NEVER RANDOM.** Gondola colours, canopy wedges, mount colours, shaft
weathering and which tower panels are glazed all come from `canvas.hash01` of the cell or the
index, so two runs of the same config are the same build and two different pieces are different
ones. `random` would make a design that cannot be regenerated, which on an island of remaining-work
designs is the same as a design that cannot be built.
"""
from __future__ import annotations

import math

from .. import blocks, fluids
from .canvas import Canvas, hash01
from .coaster import _corners, _power, _shapes
from .park import LANDS, SIGN_WIDTH, _Frame, _STEP, _sign
from .vertical import Ctx, World

_DIR = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}
_LEAN = {"east": "west", "west": "east", "north": "south", "south": "north"}

# The sixteen cheap wools, checked against `blocks.spendable` / `palette.tier` before being written
# down. A gondola, a hobby horse and a canopy wedge are the three places on this island where a
# SATURATED colour is correct rather than loud - everything else here is the land's own stone.
BRIGHT = ["red_wool", "yellow_wool", "light_blue_wool", "lime_wool", "orange_wool",
          "magenta_wool", "cyan_wool", "pink_wool", "purple_wool", "white_wool",
          "blue_wool", "green_wool"]

RIDES = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "wheel",
    "facing": "east",
    "land": "midway",
    "title": None,
    "lines": None,
    "min_run": 3,               # a trim course shorter than this is not drawn at all
    "sign": True,
    # SIZE IS None AND EACH KIND SUPPLIES ITS OWN FLOOR. `diameter` means two different things to
    # a ferris wheel and a carousel - 41 and 25 - and one shared default silently built a carousel
    # forty-one across, whose mounts then stood at a radius where the canopy is two courses up:
    # twelve hobby horses floating in six pieces. A default that is right for one kind and wrong
    # for another is worse than no default.
    "diameter": None,           # wheel 65 / carousel 31; forced odd
    "spokes": 12,
    "cars": 12,
    "shaft": None,              # drop: the tower's side, odd (9)
    "height": None,             # drop: shaft courses (56); the cap adds 13 on top
    "mounts": 12,               # carousel: the OUTER ring; the inner is two thirds of it
    # THE CAROUSEL'S CIRCUIT, and it is the one number a rider feels. A redstone_block goes in the
    # bed at both ends of every run BETWEEN CORNERS and then every `power_every` along it - a
    # plain rail does not carry the power chain, so a flat spacing leaves a dead rail past every
    # turn, and an unpowered powered_rail is a BRAKE.
    "power_every": 8,
}


# ------------------------------------------------------------------ small shared helpers

def _full(w: World, x, y, z) -> bool:
    """Is there a FULL CUBE here. `w.has` is not the same question.

    A lantern hangs from a full block and a wall sign is fixed to one; `has` answers true for a
    fence, a stair and a lantern, all of which hold up neither. The lowland's own note: a lamp
    under a slab cap reads as 'hanging from air' in the audit, because a slab is not a full block.
    """
    n = w.name(x, y, z)
    return bool(n) and blocks.is_full_cube(n)


def _signed(w, f, pal, i, d, h, facing, front, back=()) -> bool:
    """`park._sign`, with the support tested for being a FULL CUBE rather than merely present."""
    fdx, fdz = _STEP[facing]
    x, y, z = f.at(i, d, h)
    if not _full(w, x - fdx, y, z - fdz):
        return False
    return _sign(w, f, pal, i, d, h, facing, front, back)


def _lamp(w, x, y, z, light) -> bool:
    """A lantern that works out for itself whether it stands or hangs, and refuses if neither.

    Rule 9 exists because the plaza's lamp posts shipped `hanging=true` on all three lands - a lamp
    looking for a block ABOVE it, finding open sky. The question is answered from the world here
    rather than from the caller's memory of what it built.
    """
    if w.has(x, y, z):
        return False
    if _full(w, x, y - 1, z):
        w.put(x, y, z, light, hanging="false", waterlogged="false")
        return True
    if _full(w, x, y + 1, z):
        w.put(x, y, z, light, hanging="true", waterlogged="false")
        return True
    return False


def _ground(w, f, pal, i0, i1, d0, d1, h=-1):
    """The pad. A skyblock plot is VOID, so every kind brings its own floor and every leg lands
    on it. Paved on a WORLD-ALIGNED checker so two adjacent pieces line up rather than seaming."""
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            x, y, z = f.at(i, d, h)
            w.put(x, y, z, pal["ground"] if (x + z) % 2 == 0 else pal["path"])
            n += 1
    return n


def _line2(u0, v0, u1, v1):
    """A 6-CONNECTED 2-D path. Bresenham alone steps diagonally, and a diagonal step is not
    connectivity - the ear-tip lesson, and the reason the lowland root shipped as 26 components.
    Where both coordinates would move at once an intermediate cell is inserted."""
    du, dv = u1 - u0, v1 - v0
    n = max(abs(du), abs(dv))
    if n == 0:
        return [(u0, v0)]
    out, prev = [(u0, v0)], (u0, v0)
    for k in range(1, n + 1):
        u = u0 + int(round(du * k / n))
        v = v0 + int(round(dv * k / n))
        if (u, v) == prev:
            continue
        if u != prev[0] and v != prev[1]:
            out.append((u, prev[1]))
        out.append((u, v))
        prev = (u, v)
    return out


def _annulus(R, thick=2.0):
    """The rim: every cell whose radius falls in a band `thick` wide, inside R.

    A voxel circle is the one shape this medium draws natively and it needs no smoothing, no
    tuning and no reference table - which is exactly why the skyline piece is a ring.
    """
    lo = (R - thick) ** 2
    out = []
    for a in range(-R, R + 1):
        for b in range(-R, R + 1):
            r2 = a * a + b * b
            if lo < r2 <= R * R:
                out.append((a, b))
    return out


def _disc(R):
    return [(a, b) for a in range(-R, R + 1) for b in range(-R, R + 1) if a * a + b * b <= R * R]


def _wedge(a, b, n=12):
    """Which of `n` angular wedges this cell falls in. What makes a canopy or a rim read as a
    FAIRGROUND rather than as a roof: one colour is a roof, two alternating is a big top."""
    th = math.atan2(b, a)
    return int(((th + math.pi) / (2 * math.pi)) * n) % n


def _wdir(f, di, dd) -> str:
    """A local (along-frontage, into-the-piece) unit vector as a world compass direction.

    Everything oriented - a stair's tall side, a pane's connections, a seat's facing - has to be
    derived through the frame or it is right at one facing and wrong at the other three, which no
    render in this repo can show.
    """
    vx = f.sx * di - f.dx * dd
    vz = f.sz * di - f.dz * dd
    if abs(vx) >= abs(vz):
        return _DIR[(1 if vx > 0 else -1, 0)]
    return _DIR[(0, 1 if vz > 0 else -1)]


def _pane(w, f, x, y, z, di, dd):
    """A glass pane with its connections set ALONG the wall it fills.

    With every side false a pane renders as a lone post rather than as glazing - the campanile's
    own note. The connection is game-derived in world, so this is for the RENDER and for anyone
    reading the litematic; `work.INTENTIONAL` rightly drops it again.
    """
    a, bkt = _wdir(f, di, dd), _wdir(f, -di, -dd)
    w.put(x, y, z, "glass_pane", waterlogged="false", **{a: "true", bkt: "true"})


def _stair_run(w, f, pal, cells, min_run, half="top", block=None):
    """Lay a stair course only where it makes a RUN of `min_run`, never on scattered cells.

    The deck soffit drew a coffer grid per cell and produced 215 runs of which 184 were one or two
    cells - confetti, in the loudest block available. `cells` is a list of (key, order, i-or-d,
    facing); a run is consecutive `order` within one `key`, which is the line's OWN axis. Scoring
    it across its own axis is the inversion that shipped once and made every run measure 1.
    """
    by_key = {}
    for (key, order, pos, face) in cells:
        by_key.setdefault(key, []).append((order, pos, face))
    laid = 0
    for key, row in by_key.items():
        row.sort()
        run = []
        for item in row:
            if run and item[0] == run[-1][0] + 1:
                run.append(item)
            else:
                laid += _flush_run(w, run, pal, min_run, half, block)
                run = [item]
        laid += _flush_run(w, run, pal, min_run, half, block)
    return laid


def _flush_run(w, run, pal, min_run, half, block):
    if len(run) < min_run:
        return 0
    for (_order, pos, face) in run:
        w.put(pos[0], pos[1], pos[2], block or pal["stair"],
              facing=face, half=half, shape="straight", waterlogged="false")
    return len(run)


# ------------------------------------------------------------------ THE RIDE MECHANICS
#
# **VANILLA CANNOT ROTATE A STRUCTURE, SO A "RIDE" HAS TO BE A MECHANIC THE GAME ACTUALLY HAS.**
# There are exactly three that carry a player, and this module uses all three:
#
#     a MINECART on rail            the carousel's circuit
#     a SOUL-SAND BUBBLE COLUMN     the lift in the wheel's mast and in the drop tower
#     a FREE FALL INTO WATER        the descent from both, which costs no damage at all
#
# and one that does NOT exist, stated plainly because it is the first thing anybody reaches for:
# **A FERRIS WHEEL'S RIM CANNOT CARRY A RAIL.** A rail lies in the horizontal plane and an
# ascending rail climbs exactly one course per cell - 45 degrees, once. A wheel's rim is VERTICAL
# at three o'clock and INVERTED over the top. There is no arrangement of rails that follows it, at
# any diameter, and no amount of iron changes that. The wheel's ride is therefore the ASCENT.
#
# **THE WATER RULES, from the game and re-checked by simulation rather than remembered:**
#
#     soul sand under a column of water SOURCES pushes an entity UP the whole column
#     a source with an AIR neighbour FLOWS, and flowing water on a walkway is a leak
#     water does not flow upward, so a column may be open at the top and sealed nowhere else
#     landing in water cancels ALL fall damage, at any height
#
# The second of those decides every piece of geometry here. **A WATER SHAFT CANNOT HAVE A DOOR.**
# Put a doorway in the casing at the water's own level and the column drains through it across the
# boarding platform - so you go in from BELOW, swimming under the casing out of a sunk basin whose
# surface sits one course under the walking level. That is not decoration, it is the only entrance
# a sealed column can have, and it is why both lift rides have a pool at their foot.
#
# `_watertight` runs `fluids.spread` over the FINISHED model and the builders REFUSE TO EMIT a
# build whose water reaches one cell it was not placed in. Same posture as `coaster._feasible`
# about a leg that cannot absorb its own climb: a ride that does not work fails here, at generation
# time, rather than in the world an hour later.

WATER = "water"
SOUL = "soul_sand"


def _shell_of(core):
    """The cells ORTHOGONALLY outside a footprint - exactly the ones water could escape through.

    Diagonals are deliberately absent: water spreads on the four horizontal neighbours, so a
    diagonal gap is not a leak. A mast still gets its four corners for the look; watertightness
    only ever needs this set, and keeping the two apart is what makes the guarantee checkable.
    """
    ring = set()
    for (i, d) in core:
        for (ui, ud) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (i + ui, d + ud) not in core:
                ring.add((i + ui, d + ud))
    return ring


def _case(w, f, pal, ring, h0, h1, block=None):
    """Solid casing over a set of (i, d) for every course h0..h1. NEVER overwrites.

    It refuses to overwrite because the casing runs through the hub, the gallery and the A-frames,
    all of which are already solid there - and replacing a hub cell with wall would punch a hole
    through the one part of the wheel that reads as machinery.
    """
    n = 0
    for h in range(h0, h1 + 1):
        for (i, d) in sorted(ring):
            if not _full(w, *f.at(i, d, h)):
                w.put(*f.at(i, d, h), block or pal["wall"])
                n += 1
    return n


def _fill_water(w, f, core, h0, h1):
    """Water SOURCES, cell by cell.

    Every cell a source, and here that is right for the opposite reason it was wrong in the flume:
    a flume of sources carries nobody because a source does not push, and a LIFT column must stand
    still and hold its height - what pushes is the soul sand at the bottom of it.
    """
    out = []
    for h in range(h0, h1 + 1):
        for (i, d) in sorted(core):
            w.put(*f.at(i, d, h), WATER, level="0")
            out.append(f.at(i, d, h))
    return out


def _basin(w, f, pal, cells, top, depth, floor_block=None):
    """A sunk tank whose surface is FLUSH with the course under the walking level.

    That flush surface is the whole point. A pool whose lip stands proud is a wall you cannot step
    over; a pool whose water is AT walking level leaks across the floor. One course down, the pad's
    own blocks are the tank's top rim and you step off the edge straight into it.
    """
    cells = set(cells)
    floor = top - depth
    for (i, d) in sorted(cells):
        w.put(*f.at(i, d, floor), floor_block or pal["trim"])
    for (i, d) in sorted(_shell_of(cells)):
        for h in range(floor, top + 1):
            if not _full(w, *f.at(i, d, h)):
                w.put(*f.at(i, d, h), pal["trim"])
    return _fill_water(w, f, cells, floor + 1, top)


def _watertight(w, sources):
    """Every cell the water would reach that we did not place it in. Empty, or the build is wrong.

    Run over the WHOLE model, so it catches a leak opened by any other part of the build - a car
    strut, an A-frame leg, a sign - and not only by the shaft's own casing.
    """
    cells = {q: v[0] for q, v in w.cells.items()}
    xs = [q[0] for q in cells]
    ys = [q[1] for q in cells]
    zs = [q[2] for q in cells]
    pad = 2
    bounds = (min(xs) - pad, min(ys) - pad, min(zs) - pad,
              max(xs) + pad, max(ys) + pad, max(zs) + pad)
    lv = fluids.spread(cells, list(sources), bounds)
    return sorted(set(lv) - set(sources))


def _clear_fall(w, f, core, h0, h1):
    """Cells of a drop chute that are NOT open. A chute is a ride only if all of them are air."""
    bad = []
    for h in range(h0, h1 + 1):
        for (i, d) in sorted(core):
            n = w.name(*f.at(i, d, h))
            if n is not None and n != WATER:
                bad.append((f.at(i, d, h), n))
    return bad


def _ring_path(R):
    """A rasterised circle as an ORDERED, SIMPLE, 6-CONNECTED CYCLE - a rail circuit's plan.

    **A CIRCLE IS THE EXPENSIVE SHAPE AND THE COST IS IRON.** `powered_rail` has no curved state at
    all - read off `data/blocks.json`, asserted by this module's test, never remembered - so every
    direction change is a plain `rail`, and a voxel circle changes direction more than half the
    time. The Island Line took a SQUARE helix rather than pay that. Here the shape IS the ride: a
    carousel that goes round a square is not a carousel, and at this radius the bill is about
    twenty iron, which this island can find.

    Two properties are checked rather than hoped for, because both fail silently in game: every
    cell appears ONCE, and every cell has EXACTLY TWO path neighbours. A cell with three orthogonal
    rail neighbours does not connect the way the path says - the game picks two by its own priority
    - and the circuit quietly becomes a dead end.
    """
    n = max(64, int(2 * math.pi * R * 4))
    raw = []
    for k in range(n):
        th = 2 * math.pi * k / n
        q = (int(round(R * math.cos(th))), int(round(R * math.sin(th))))
        if not raw or q != raw[-1]:
            raw.append(q)
    if len(raw) > 1 and raw[0] == raw[-1]:
        raw.pop()
    out = []
    for a, b in zip(raw, raw[1:] + raw[:1]):
        out.extend(_line2(a[0], a[1], b[0], b[1])[:-1])
    seen = set(out)
    if len(seen) != len(out):
        raise ValueError("the r=%d track visits a cell twice; it is not a simple circuit" % R)
    for q in out:
        deg = sum(1 for (u, v) in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if (q[0] + u, q[1] + v) in seen)
        if deg != 2:
            raise ValueError("track cell %s has %d rail neighbours, not 2 - the game would not "
                             "connect the circuit the way the path says" % (q, deg))
    return out


# ------------------------------------------------------------------ the ferris wheel

def _wheel(w: World, p: dict, ctx) -> dict:
    """A FERRIS WHEEL, AND THE RIDE INSIDE IT: a bubble lift up the mast to a gallery at the axle,
    and a free-fall chute back down into the pool you set off from.

    **THE WHEEL CANNOT TURN AND ITS RIM CANNOT CARRY A RAIL.** Both are facts about the game, not
    limits of effort: nothing rotates a structure in vanilla, and a rail lies flat with a single
    45-degree ascending state, so it cannot follow a circle that is vertical at three o'clock and
    inverted over the top. Every mechanic that would make a wheel a wheel is unavailable. What IS
    available is the thing a wheel is actually FOR - going up and looking out - so that is what
    was built, and the loop is:

        queue -> the splash pool -> the bubble lift, 48 courses -> the gallery at the axle
              -> the chute -> back into the pool

    **THE COST OF THAT IS A CENTRAL MAST AND IT IS PAID DELIBERATELY.** A bubble column is vertical
    by definition, so the lift cannot live in an A-frame's raking leg; it needs a straight shaft
    from the pad to the axle, and the only place a shaft reaches the axle is under it. So the
    support is now an A-frame WITH A KING POST - two 5x5 masts straddling the wheel's plane, cased
    round a 3x3 water shaft each - and from the front there is a five-wide tower up the middle of a
    seventy-three-wide wheel. That is 7% of the silhouette, it reads as the tower carrying the
    axle, and it is the price of the ride being real. The alternative - a mast outside the ring and
    a thirty-eight-block gantry to the hub at axle height - spends the same silhouette horizontally
    and is structurally absurd.

    **THE CARS THEREFORE GET THEIR OWN DEPTH BAND.** A car at the bottom of the ring sits at the
    wheel's own centre-line, which is exactly where the mast is; drawn over the full depth as
    before, every car passing six o'clock would be built inside the tower. The depth is banded
    instead - mast, cars, rim, cars, mast - so the two can never share a cell at any angle, and
    `rim_bottom` is raised so the lowest car clears the station roof rather than the boarding
    platform.

    **THE LIFT HAS NO DOOR, AND THAT IS NOT AN OVERSIGHT.** A doorway in the casing at the water's
    own level drains the column across the platform. You go in from BELOW: a channel of water three
    courses deep runs the whole depth of the piece under both masts, its surface flush one course
    under the walking level, and you dive at the front, swim under the casing, and surface in the
    column over the soul sand. The same channel is what the chute drops you into, so the ride
    closes without leaving the water. `_watertight` proves it at generation time.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    mr = int(p["min_run"])

    D = max(41, int(p["diameter"] or 65) | 1)
    R = D // 2
    ncar = max(8, int(p["cars"]))
    nspoke = max(8, int(p["spokes"]))

    CAR_R = R + 3                       # car centres ride this radius; outer reach CAR_R + 1
    W = 2 * (CAR_R + 1) + 1             # the footprint the cars need, not the one the ring needs
    ci = W // 2

    # THE DEPTH IS BANDED, and the bands are what keep the cars out of the masts.
    #     0..4   front mast (5x5 cased, 3x3 shaft)      9..13  back mast
    #     5..8   the cars' band                          6,7   the rim, centred inside it
    # **A SHAFT IS ONE CELL WIDE AND THAT IS A COST DECISION, NOT A GEOMETRIC ONE.** A 3x3 lift is
    # a nicer thing to swim up and it is 477 water SOURCES; a bubble column has to be source blocks
    # the whole way, which is a bucket per cell by hand - nobody would ever build it. One cell wide
    # is 53, the mast that cases it is 3x3 rather than 5x5, and the tower costs 4% of the
    # silhouette instead of 7%.
    MAST = 3
    FRONT0, FRONT1 = 0, MAST - 1
    BACK0, BACK1 = MAST + 4, 2 * MAST + 3
    DEPTH = BACK1 + 1
    CAR_D = (MAST, MAST + 3)
    RIM_D = (MAST + 1, MAST + 2)
    FRAME_D = (FRONT0, BACK1)
    LIFT = {(ci, FRONT0 + 1)}
    CHUTE = {(ci, BACK0 + 1)}
    CORES = LIFT | CHUTE
    MAST_RING = ({(ci + a, FRONT0 + b) for a in (-1, 0, 1) for b in range(MAST)} |
                 {(ci + a, BACK0 + b) for a in (-1, 0, 1) for b in range(MAST)}) - CORES

    rim_bottom = 12                     # the lowest car then clears the station, not the pad
    hh = rim_bottom + R                 # the axle
    G = hh + 4                          # the gallery deck, one course over the hub
    QUEUE = 6
    POOL_D = 3

    _ground(w, f, pal, -2, W + 1, -QUEUE, DEPTH + 2)

    # ---- THE CHANNEL. One body of water from the forecourt to the back of the piece, three
    # courses deep, surface flush at h=-1. It is the lift's entrance, the chute's landing and the
    # walk between them, and it is the only way into a shaft that may not have a door.
    chan = {(ci + a, d) for a in (-1, 0, 1) for d in range(-2, DEPTH + 2)}
    wet = _basin(w, f, pal, chan, top=-1, depth=POOL_D)
    for (i, d) in sorted(LIFT):         # the pump: soul sand under the lift, and only there
        w.put(*f.at(i, d, -1 - POOL_D), SOUL)

    # ---- the masts, cased to the gallery. The casing is what makes the shaft watertight and it
    # is also the tower, so it is drawn as a full 5x5 ring rather than as the four faces water
    # could actually escape through.
    _case(w, f, pal, MAST_RING, 0, G, pal["wall"])
    for h in range(0, G + 1):           # corner posts, and a string course every sixth
        for (i, d) in ((ci - 1, FRONT0), (ci + 1, FRONT0), (ci - 1, FRONT1), (ci + 1, FRONT1),
                       (ci - 1, BACK0), (ci + 1, BACK0), (ci - 1, BACK1), (ci + 1, BACK1)):
            w.put(*f.at(i, d, h), pal["post"])
        if h % 6 == 0:
            for (i, d) in sorted(MAST_RING):
                w.put(*f.at(i, d, h), pal["trim"])

    # ---- the rim. Alternating wedges: one colour is a hoop, two is a fairground.
    ring = _annulus(R, 2.0)
    ca, cb = pal["canopy"]
    for (a, b) in ring:
        blk = ca if _wedge(a, b, 12) % 2 == 0 else cb
        for d in RIM_D:
            w.put(*f.at(ci + a, d, hh + b), blk)

    # ---- hub and spokes. The hub spans the WHOLE depth so it ties both masts and both A-frames
    # to the wheel; without that they are separate pieces standing next to a floating ring. The
    # two shafts are skipped through it - a hub cell in the lift's column is a plug in the lift.
    for (a, b) in _disc(3):
        for d in range(DEPTH):
            if (ci + a, d) in CORES:
                continue
            w.put(*f.at(ci + a, d, hh + b), pal["trim"])
    for k in range(nspoke):
        th = 2 * math.pi * k / nspoke
        ei = int(round((R - 1) * math.cos(th)))
        eb = int(round((R - 1) * math.sin(th)))
        for (a, b) in _line2(0, 0, ei, eb):
            if a * a + b * b < 9:
                continue
            for d in RIM_D:
                w.put(*f.at(ci + a, d, hh + b), pal["beam"])

    # ---- the A-frames, one in front of the wheel and one behind it, feet on the pad.
    foot = R - 3
    for d in FRAME_D:
        for s in (-1, 1):
            for (a, b) in _line2(s * foot, 0, 0, hh):
                if (ci + a, d) in CORES:
                    continue
                w.put(*f.at(ci + a, d, b), pal["post"])
                if b == 0:              # a footing pad, so a leg lands on something
                    for j in (-1, 1):
                        if (ci + a + j, d) not in CORES:
                            w.put(*f.at(ci + a + j, d, 0), pal["trim"])
        for tie_h in (hh // 3, (2 * hh) // 3):
            span = int(round(foot * (1 - tie_h / hh)))
            if span * 2 + 1 >= mr:
                for a in range(-span, span + 1):
                    if (ci + a, d) in CORES:
                        continue
                    w.put(*f.at(ci + a, d, tie_h), pal["trim"])

    # ---- the cars, in their own depth band so no car can ever be built inside a mast.
    cars, car_lamps = 0, 0
    d_lo, d_hi = CAR_D
    for m in range(ncar):
        th = 2 * math.pi * m / ncar + math.pi / (2 * ncar)
        cia = int(round(CAR_R * math.cos(th)))
        cib = int(round(CAR_R * math.sin(th)))
        for (a, b) in _line2(int(round((R - 1) * math.cos(th))),
                             int(round((R - 1) * math.sin(th))), cia, cib):
            for d in RIM_D:
                w.put(*f.at(ci + a, d, hh + b), pal["trim"])

        # TWELVE OF ONE BOX IS A ROW OF ONE BOX. Colour, roof tone, depth and whether the car
        # carries an awning are all hashed off the car's index and the piece's own world position,
        # so the ring is varied, two wheels in one park differ, and the same config regenerates
        # cell for cell. `random` would give a design that cannot be built twice.
        body = BRIGHT[int(hash01(m, R, f.x, f.z) * len(BRIGHT))]
        roof = pal["trim"] if hash01(m, 7, f.z) < 0.5 else BRIGHT[(m * 5 + 3) % len(BRIGHT)]
        style = int(hash01(m, 13, f.x) * 3)
        lo, hi = (d_lo, d_hi) if style != 2 else (d_lo, d_hi - 1)   # a pod, or a full cabin
        i0, h0 = ci + cia, hh + cib
        for di in (-1, 0, 1):
            for d in range(lo, hi + 1):
                w.put(*f.at(i0 + di, d, h0 - 1), pal["beam"])        # floor
                w.put(*f.at(i0 + di, d, h0 + 1), roof)               # roof
                edge = di in (-1, 1) or d in (lo, hi)
                if not edge:
                    continue
                if di == 0 and d == lo:                              # the way in
                    continue
                w.put(*f.at(i0 + di, d, h0), body)
        awn = [f.at(i0 + di, lo - 1, h0 + 1) for di in (-1, 0, 1)]
        # AN AWNING OVER THE DOOR - three cells, exactly the shortest run rule 9 allows, and gated
        # on `min_run` like every other trim course. Placed with a bare `put` it bypassed the gate
        # entirely, so a config asking for runs of five still got this run of three.
        if style == 1 and mr <= 3 and not any(w.has(*cell) for cell in awn):
            for cell in awn:
                w.put(*cell, pal["stair"], facing=_wdir(f, 0, 1),
                      half="top", shape="straight", waterlogged="false")
        for lit_di in (0, -1, 1):
            if _lamp(w, *f.at(i0 + lit_di, (lo + hi) // 2, h0 - 2), pal["light"]):
                car_lamps += 1
                break
        cars += 1

    # ---- a lamp ring on the rim, interleaved between the cars, each on its own BRACKET.
    #
    # A lantern needs a full block above it or below it, and on a circle neither is true at the
    # sides: at three o'clock the cell under a rim cell is outside the annulus and the cell over it
    # is too, so a naive ring lit only the top and the bottom arcs and quietly skipped the rest.
    # A one-cell bracket proud of the rim makes the answer the same at every angle, and the lamp is
    # tried on BOTH sides of the tip - hanging it under the tip alone placed 15 of 24, and every
    # one of the nine that vanished was on the TOP arc, where "below" points back toward the hub.
    lit = 0
    for k in range(ncar * 2):
        th = math.pi * k / ncar
        ba = int(round((R + 1) * math.cos(th)))
        bb = int(round((R + 1) * math.sin(th)))
        for (a, b) in _line2(int(round((R - 1) * math.cos(th))),
                             int(round((R - 1) * math.sin(th))), ba, bb):
            for d in RIM_D:
                if not w.has(*f.at(ci + a, d, hh + b)):
                    w.put(*f.at(ci + a, d, hh + b), pal["trim"])
        if (_lamp(w, *f.at(ci + ba, RIM_D[0], hh + bb - 1), pal["light"])
                or _lamp(w, *f.at(ci + ba, RIM_D[0], hh + bb + 1), pal["light"])):
            lit += 1

    # ---- THE GALLERY at the axle: the place the lift delivers you to, and the reason to go up.
    # It is laid over the hub across the whole depth, with the lift's column and the chute's mouth
    # left OPEN by the loop rather than punched afterwards - the void tower's crenellations shipped
    # as a plain drum for exactly that mistake and nothing about the code looked wrong.
    gal = [(i, d) for i in range(ci - 4, ci + 5) for d in range(DEPTH)
           if (i, d) not in CORES]
    for (i, d) in gal:
        w.put(*f.at(i, d, G), pal["trim"] if (i + d) % 2 else pal["ground"])
    galset = set(gal)
    rails, mouth = 0, None
    for (i, d) in gal:                  # a rail wherever the deck ends, and round the chute mouth
        # **THE LIFT'S OWN COLUMN IS NOT AN EDGE.** Counted as one, all four cells round the
        # column got a fence and the ride delivered the rider into a pen he could not step out of
        # - which is the whole ride failing, silently, with every block legal and the piece one
        # connected solid. `test_the_lift_delivers_you_onto_a_deck_you_can_stand_on` pins it.
        edge = any((i + u, d + v) not in galset and (i + u, d + v) not in CORES
                   for (u, v) in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        at_mouth = any((i + u, d + v) in CHUTE for (u, v) in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if (i, d) in LIFT:
            continue
        if edge or at_mouth:
            # the one gap in the rail round the mouth is the way in - a hole you step into on
            # purpose, not one you walk into
            if at_mouth and d == min(dd for (_ii, dd) in CHUTE) - 1 and i == ci:
                mouth = f.at(i, d, G + 1)
                w.put(*mouth, pal["gate"], facing=_wdir(f, 0, 1),
                      open="true", in_wall="false", powered="false")
            else:
                w.put(*f.at(i, d, G + 1), pal["fence"])
            rails += 1
    gal_lamps = 0
    for (i, d) in ((ci - 4, FRONT0), (ci + 4, FRONT0), (ci - 4, BACK1), (ci + 4, BACK1)):
        for h in range(G + 1, G + 4):
            w.put(*f.at(i, d, h), pal["post"])
        w.put(*f.at(i, d, G + 4), pal["trim"])
        if _lamp(w, *f.at(i, d, G + 5), pal["light"]):
            gal_lamps += 1

    # ---- THE WATER, last, so every cell that has to seal it is already standing.
    wet += _fill_water(w, f, LIFT, 0, G)
    leaks = _watertight(w, wet)
    if leaks:
        raise ValueError("the wheel's lift leaks at %d cells, the first %s - a water shaft with a "
                         "hole in it drains onto the platform" % (len(leaks), leaks[:3]))
    blocked = _clear_fall(w, f, CHUTE, 0, G)
    if blocked:
        raise ValueError("the wheel's chute is obstructed at %s - a fall that hits a block is a "
                         "fall that hurts" % (blocked[:3],))

    # ---- the boarding house over the pool mouth, the queue, and the signs.
    signs = 0
    title = str(p.get("title") or "BIG WHEEL").upper()
    for i in (ci - 3, ci + 3):
        for h in range(5):
            w.put(*f.at(i, -2, h), pal["post"])
        w.put(*f.at(i, -3, 0), pal["trim"])
        _lamp(w, *f.at(i, -3, 4), pal["light"])
    for i in range(ci - 3, ci + 4):     # the lintel the nameplate hangs on
        w.put(*f.at(i, -2, 5), pal["trim"])
    for i in range(ci - 4, ci + 5):
        w.put(*f.at(i, -3, 6), pal["trim"])
    if p.get("sign", True) and _signed(w, f, pal, ci, -3, 5, f.facing,
                                       [title[:SIGN_WIDTH], "", "dive in below",
                                        "lift to the top"]):
        signs += 1
    for lane in range(2):               # a switchback queue in front of the mouth
        d = -4 - lane
        lo, hi = (2, W - 4) if lane == 0 else (3, W - 3)
        for i in range(lo, hi + 1):
            if abs(i - ci) <= 1 and lane == 0:
                continue                # the way through
            w.put(*f.at(i, d, 0), pal["fence"])
    for i in (2, W - 3):
        for h in range(3):
            w.put(*f.at(i, -QUEUE, h), pal["post"])
        w.put(*f.at(i, -QUEUE, 3), pal["trim"])
        _lamp(w, *f.at(i, -QUEUE, 4), pal["light"])

    # ---- entrance pylons, which are also the only thing a second nameplate can hang on out here.
    for k, i in enumerate((1, W - 2)):
        for h in range(6):
            w.put(*f.at(i, -1, h), pal["post"])
        w.put(*f.at(i, -1, 6), pal["trim"])
        _lamp(w, *f.at(i, -1, 7), pal["light"])
        lines = ([title[:SIGN_WIDTH], "", "%d cars" % ncar, "%d across" % D] if k == 0
                 else [title[:SIGN_WIDTH], "", "%d up" % (G + 1), "then jump"])
        if p.get("sign", True) and _signed(w, f, pal, i, -2, 3, f.facing, lines):
            signs += 1

    board = f.at(ci, -1, -1)            # the cell you step into to start the ride
    return {"kind": "wheel", "width": W, "depth": DEPTH, "diameter": D,
            "top": hh + CAR_R + 1, "cars": cars, "spokes": nspoke, "rim_lamps": lit,
            "rim_lamp_slots": ncar * 2, "car_lamps": car_lamps, "gallery_lamps": gal_lamps,
            "signs": signs, "gallery_rail": rails,
            "ride": "bubble lift + free fall",
            "board": list(board),
            "gallery_y": f.at(0, 0, G)[1],
            "mouth": list(mouth) if mouth else None,
            "lift": [list(f.at(i, d, h)) for h in range(0, G + 1) for (i, d) in sorted(LIFT)],
            "lift_soul": [list(f.at(i, d, -1 - POOL_D)) for (i, d) in sorted(LIFT)],
            "chute": [list(f.at(i, d, h)) for h in range(0, G + 1) for (i, d) in sorted(CHUTE)],
            # THE COLUMNS A FALLING BODY CAN OCCUPY, which is not the same set as the chute: the
            # wheel's chute is a walled tube so the two coincide, and the drop tower's does not.
            # Stated per ride so the test asks about the real landing area rather than assuming it.
            "fall_zone": [[f.at(i, d, 0)[0], f.at(i, d, 0)[2]] for (i, d) in sorted(CHUTE)],
            "fall_from": f.at(0, 0, G)[1],
            "fall_to": f.at(0, 0, -1)[1],
            "pool": [list(c) for c in sorted(wet)],
            "pool_top": f.at(0, 0, -1)[1],
            "contract": "a two-cell ring spoked to a hub and straddled by two masts, and A RIDE: a "
                        "soul-sand bubble column lifts you %d courses up the front mast to a "
                        "gallery at the axle, and a walled chute drops you back into the same "
                        "three-course channel you set off from, which cancels the fall entirely. "
                        "The shaft has no door because a water shaft cannot have one - you swim in "
                        "under the casing - and the whole water body is proved leak-free by "
                        "simulation before the design is emitted." % (G + 1 + POOL_D),
            "unverified": ["nobody has ridden it in game. The bubble column, the seal and the "
                           "clear fall are all simulated here; the FEEL of a 50-course drop into "
                           "three courses of water is reasoning until someone jumps."]}


# ------------------------------------------------------------------ the drop tower

def _drop(w: World, p: dict, ctx) -> dict:
    """A DROP TOWER, AND IT IS THE ONE RIDE VANILLA GIVES YOU OUTRIGHT.

    A soul-sand bubble column lifts you the full height of the shaft, you step out onto a platform
    under the winch house, and then you jump: fifty courses of open shaft with the park flashing
    past the window slits, into two courses of water at the bottom. **LANDING IN WATER CANCELS ALL
    FALL DAMAGE AT ANY HEIGHT**, which is why this is the one park mechanic that needs no machine,
    no redstone and no compromise. Then you swim four cells to the lift and go again.

    The architecture is the void tower's, followed rather than re-derived: a plinth, regular
    coursework, openings that are OPENINGS, a string course per tier, a corbelled overhang and a
    crowned top. Its first attempt was a sheared jagged stub and was rejected on sight as *"a
    tossed grouping of vague blocks"* - what makes voxels read as a building is regularity.

    **THE OPENINGS ARE LEFT EMPTY BY THE WALL LOOP.** Building the ring and cutting holes
    afterwards repaints cells that already exist; the void tower's crenellations shipped as a plain
    drum for exactly that reason and nothing about the code looked wrong.

    **AND THE GLAZING IS DECIDED PER PANEL, NOT PER CELL.** Hashed per cell it is confetti - the
    deck soffit's 184 runs of one or two cells, in glass. One hash per (tier, face) glazes a whole
    panel or none of it.

    **THE THREE THINGS THE RIDE ITSELF IMPOSES**, none of which is negotiable:

      the shaft interior must be EMPTY over the drop zone, all the way down, or the fall is a fall
      onto a block. `_clear_fall` refuses to emit a tower whose chute is obstructed;
      the lift cannot have a door at the water's level, so the pool at the base is its entrance and
      the base of the tower is a tank, not a floor;
      and the platform is a FLOOR WITH A HOLE IN IT, the hole left open by the loop rather than
      punched afterwards, ringed in rail with a single gate. A hole you can walk into by accident
      is not a ride, it is a hazard.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    mr = int(p["min_run"])

    S = max(9, int(p["shaft"] or 9) | 1)
    H = max(48, int(p["height"] or 56))
    W, DP = S + 6, S + 4
    i0, d0 = (W - S) // 2, (DP - S) // 2
    QUEUE = 5
    POOL_D = 2

    # the shaft's own interior, and the two things that live in it
    IN_I = range(i0 + 1, i0 + S - 1)
    IN_D = range(d0 + 1, d0 + S - 1)
    INSIDE = {(i, d) for i in IN_I for d in IN_D}
    LIFT = {(i0 + 2, d0 + 2)}
    CASE = {(i, d) for i in range(i0 + 1, i0 + 4) for d in range(d0 + 1, d0 + 4)} - LIFT
    dz_i, dz_d = i0 + 4, d0 + 3
    DROP = {(i, d) for i in range(dz_i, dz_i + 3) for d in range(dz_d, dz_d + 3)}
    if DROP & CASE:
        raise ValueError("the drop chute and the lift casing share a cell; the shaft is too narrow")
    PLAT = 6 * ((H - 6) // 6)           # the platform lands ON a string course, never between two

    _ground(w, f, pal, -1, W, -QUEUE - 1, DP)

    # ---- THE TANK. The tower's base is not a floor, it is the pool the ride lands in - and it is
    # also the only way into the lift, because a water shaft may not have a door at its own level.
    wet = _basin(w, f, pal, INSIDE, top=-1, depth=POOL_D)
    for (i, d) in sorted(LIFT):
        w.put(*f.at(i, d, -1 - POOL_D), SOUL)

    # ---- the base station: a walled room round the shaft's foot, with the door left empty.
    door = {W // 2 - 1, W // 2, W // 2 + 1}
    for i in range(W):
        for d in range(DP):
            if not (i in (0, W - 1) or d in (0, DP - 1)):
                continue
            corner = i in (0, W - 1) and d in (0, DP - 1)
            w.put(*f.at(i, d, -1), pal["trim"])
            for h in range(5):
                if d == 0 and i in door and h < 4:
                    continue
                w.put(*f.at(i, d, h), pal["post"] if corner else pal["wall"])
    # roof over the ring between the station wall and the shaft, never over the shaft itself
    for i in range(-1, W + 1):
        for d in range(-1, DP + 1):
            if i0 <= i < i0 + S and d0 <= d < d0 + S:
                continue
            w.put(*f.at(i, d, 5), pal["trim"])
    # A CORNICE UNDER IT - AND IT LEAVES THE DOOR COLUMNS AS A PLAIN LINTEL BAND. Run across them
    # it replaces the top wall course with stairs, and the nameplate over the door then has a STAIR
    # behind it rather than a full block, so the sign is silently refused and the entrance ends up
    # unnamed. A lintel band over an opening reads as an arcade, and it is the only thing a front
    # sign has to hang on.
    corn = []
    for i in range(W):
        for d in range(DP):
            if not (i in (0, W - 1) or d in (0, DP - 1)):
                continue
            if d == 0 and i in door:
                continue
            face = f.inward(i, d, W, DP)
            if face:
                corn.append(((d, "i") if d in (0, DP - 1) else (i, "d"),
                             i if d in (0, DP - 1) else d, f.at(i, d, 4), _LEAN[face]))
    _stair_run(w, f, pal, corn, mr, half="top")

    # ---- the shaft. Corner posts always; a full ring on the string courses; between them a
    # panel with two real openings per face.
    solid_k = {0, 1, S // 2, S - 2, S - 1}
    glazed, opened = 0, 0
    for h in range(H):
        band = (h % 6 == 0) or h >= H - 2
        proud = h % 12 == 0 and h > 0
        for i in range(i0, i0 + S):
            for d in range(d0, d0 + S):
                ei = i in (i0, i0 + S - 1)
                ed = d in (d0, d0 + S - 1)
                if not (ei or ed):
                    continue
                corner = ei and ed
                if corner:
                    w.put(*f.at(i, d, h), pal["post"])
                    continue
                if ed:
                    k, face_ix, nrm = i - i0, (0 if d == d0 else 1), (0, 1 if d == d0 else -1)
                else:
                    k, face_ix, nrm = d - d0, (2 if i == i0 else 3), (1 if i == i0 else -1, 0)
                # THE WAY INTO THE SHAFT IS TESTED FIRST, and that order is the whole of it. Asked
                # after the solid test, the door's own middle column is already claimed by
                # `solid_k` and the check can never fire: the tower shipped with two thin slots
                # either side of a solid pier and NO DOOR, aligned perfectly with the station's
                # own doorway, and every render showed a lattice that looked exactly right.
                #
                # AND IT STARTS AT THE FLOOR. At h=1 it was a one-course step up out of a station
                # whose walking level is h=0 - a threshold you have to jump, on the way out of a
                # pool.
                if d == d0 and abs(k - S // 2) <= 1 and 0 <= h <= 2:
                    opened += 1
                    continue
                if band or k in solid_k:
                    x, y, z = f.at(i, d, h)
                    # WEATHERING IS HASHED ON THE CELL. Hashed on the COURSE a whole course comes
                    # out one material and the shaft is horizontal stripes; the deck soffit shipped
                    # exactly that once and nothing about the code looked wrong.
                    hot = hash01(x, y, z) < (0.30 if band else 0.16)
                    if band:
                        blk = pal["trim"] if hash01(f.x, f.z, h // 6, 5) < 0.62 else pal["post"]
                    else:
                        blk = pal["trim"] if hot else pal["wall"]
                    w.put(x, y, z, blk)
                    continue
                tier = h // 6
                if hash01(f.x, f.z, tier, face_ix) < 0.34:
                    _pane(w, f, *f.at(i, d, h), *(-nrm[1], nrm[0]))
                    glazed += 1
                else:
                    opened += 1
        if proud:
            for i in range(i0 - 1, i0 + S + 1):
                for d in range(d0 - 1, d0 + S + 1):
                    if i in (i0 - 1, i0 + S) or d in (d0 - 1, d0 + S):
                        w.put(*f.at(i, d, h), pal["trim"])

    # ---- THE LIFT CASING, floor to platform. It stands in the pool, so the water runs UNDER it
    # and that is how you get in: dive, swim four cells, surface over the soul sand, go up.
    _case(w, f, pal, CASE, 0, PLAT, pal["trim"])

    # ---- THE PLATFORM. A floor with a hole in it, the hole left open by the loop.
    plat_cells = sorted(INSIDE - DROP - LIFT)
    for (i, d) in plat_cells:
        w.put(*f.at(i, d, PLAT), pal["trim"] if (i + d) % 2 else pal["wall"])
    plat_set = set(plat_cells)
    rails, gate_at, mouth = 0, None, None
    for (i, d) in plat_cells:
        if not any((i + u, d + v) in DROP for (u, v) in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        if gate_at is None and d == min(dd for (_i, dd) in DROP) - 1 and i == dz_i + 1:
            gate_at = (i, d)
            mouth = f.at(i, d, PLAT + 1)
            w.put(*mouth, pal["gate"], facing=_wdir(f, 0, 1),
                  open="true", in_wall="false", powered="false")
        else:
            w.put(*f.at(i, d, PLAT + 1), pal["fence"])
        rails += 1
    plat_lamps = 0
    for (i, d) in ((i0 + 1, d0 + S - 2), (i0 + S - 2, d0 + 1), (i0 + S - 2, d0 + S - 2)):
        if (i, d) not in plat_set:
            continue
        for h in (PLAT + 1, PLAT + 2):
            w.put(*f.at(i, d, h), pal["post"])
        if _lamp(w, *f.at(i, d, PLAT + 3), pal["light"]):
            plat_lamps += 1

    # ---- corbel, top house, cap. Each course steps OUT, which is what a corbel is; a plain
    # extruded box with a hat on it is the thing this is avoiding.
    #
    # **A CORBEL COURSE MUST INCLUDE THE SHAFT'S OWN RING, not just the ring outside it.** Drawn as
    # the perimeter alone it sits one cell clear of the shaft on every side and touches nothing:
    # the house, the cap and both corbels shipped as three separate lumps 54 courses up. Nothing
    # about the code looked wrong and every block state was legal - it is the connectivity check
    # that catches this and only that.
    for k, h in enumerate((H, H + 1)):
        for i in range(i0 - 2, i0 + S + 2):
            for d in range(d0 - 2, d0 + S + 2):
                ring = max(abs(i - (i0 + S // 2)), abs(d - (d0 + S // 2))) - S // 2
                if 0 <= ring <= k + 1:
                    w.put(*f.at(i, d, h), pal["trim"])
    hi0, hd0, HS = i0 - 1, d0 - 1, S + 2
    for i in range(hi0, hi0 + HS):                     # the winch room's floor is a RING; the
        for d in range(hd0, hd0 + HS):                 # shaft stays open all the way up
            if i in (hi0, hi0 + HS - 1) or d in (hd0, hd0 + HS - 1):
                w.put(*f.at(i, d, H + 2), pal["trim"])
    for h in range(H + 3, H + 7):
        for i in range(hi0, hi0 + HS):
            for d in range(hd0, hd0 + HS):
                ei = i in (hi0, hi0 + HS - 1)
                ed = d in (hd0, hd0 + HS - 1)
                if not (ei or ed):
                    continue
                mid = (abs(i - (hi0 + HS // 2)) <= 1) if ed else (abs(d - (hd0 + HS // 2)) <= 1)
                if mid and h in (H + 4, H + 5):
                    continue                            # the winch-room windows
                w.put(*f.at(i, d, h), pal["post"] if (ei and ed) else pal["wall"])
    house_c = []
    for i in range(hi0, hi0 + HS):
        for d in range(hd0, hd0 + HS):
            ei = i in (hi0, hi0 + HS - 1)
            ed = d in (hd0, hd0 + HS - 1)
            if not (ei or ed):
                continue
            face = f.inward(i - hi0, d - hd0, HS, HS)
            if face:
                house_c.append(((d, "i") if ed else (i, "d"), i if ed else d,
                                f.at(i, d, H + 6), _LEAN[face]))
    _stair_run(w, f, pal, house_c, mr, half="top")
    cap = HS // 2
    for k in range(cap + 1):
        blk = _cap_band(pal, k)
        for i in range(hi0 + k, hi0 + HS - k):
            for d in range(hd0 + k, hd0 + HS - k):
                w.put(*f.at(i, d, H + 7 + k), blk)
    top = H + 7 + cap
    _lamp(w, *f.at(hi0 + HS // 2, hd0 + HS // 2, top + 1), pal["light"])

    # ---- the queue: a switchback of rail in front of the door, lit on its posts.
    for lane in range(2):
        d = -2 - lane * 2
        lo, hi = (1, W - 3) if lane == 0 else (2, W - 2)
        for i in range(lo, hi + 1):
            w.put(*f.at(i, d, 0), pal["fence"])
    for i in (1, W - 2):
        for h in range(3):
            w.put(*f.at(i, -QUEUE, h), pal["post"])
        w.put(*f.at(i, -QUEUE, 3), pal["trim"])
        _lamp(w, *f.at(i, -QUEUE, 4), pal["light"])
    for i in range(1, W - 1):
        if i in door:
            continue                     # the way IN is left empty by the loop, never punched
        w.put(*f.at(i, -QUEUE, 0), pal["fence"])

    # ---- lights under the station eaves, and the signs.
    for i in (1, W - 2):
        for d in (1, DP - 2):
            _lamp(w, *f.at(i, d, 4), pal["light"])

    # ---- THE WATER, last, so everything that has to seal it is already standing.
    wet += _fill_water(w, f, LIFT, 0, PLAT)
    leaks = _watertight(w, wet)
    if leaks:
        raise ValueError("the tower's lift leaks at %d cells, the first %s - a water shaft with a "
                         "hole in it drains across the station floor" % (len(leaks), leaks[:3]))
    blocked = _clear_fall(w, f, DROP, 0, PLAT)
    if blocked:
        raise ValueError("the drop chute is obstructed at %s - a fall that hits a block is a fall "
                         "that hurts" % (blocked[:3],))

    title = str(p.get("title") or "DROP TOWER").upper()
    # FIFTEEN CHARACTERS. Longer and the line is silently truncated by `_signed`, which reads as
    # a typo in game and cannot be seen in any render here.
    lines = list(p.get("lines") or ["swim in and up", "then step off", "water catches"])
    signs = 0
    if p.get("sign", True):
        signs += _signed(w, f, pal, W // 2, -1, 4, f.facing,
                         [title[:SIGN_WIDTH], "", "%d up" % (PLAT + 1), "%d down" % (PLAT + 2)])
        signs += _signed(w, f, pal, W // 2 + 2, 1, 2, f.back,
                         ["RULES"] + [str(s)[:SIGN_WIDTH] for s in lines[:3]])

    return {"kind": "drop", "width": W, "depth": DP, "shaft": S, "height": H,
            "top": top + 1, "glazed": glazed, "openings": opened,
            "platform_y": f.at(0, 0, PLAT)[1], "platform_rail": rails,
            "mouth": list(mouth) if mouth else None,
            "platform_lamps": plat_lamps, "signs": signs,
            "ride": "bubble lift + free fall",
            "fall": PLAT + 2,
            "board": list(f.at(W // 2, d0 + 1, -1)),
            "lift": [list(f.at(i, d, h)) for h in range(0, PLAT + 1) for (i, d) in sorted(LIFT)],
            "lift_soul": [list(f.at(i, d, -1 - POOL_D)) for (i, d) in sorted(LIFT)],
            "chute": [list(f.at(i, d, h)) for h in range(0, PLAT + 1) for (i, d) in sorted(DROP)],
            # **THE TOWER'S CHUTE IS NOT WALLED AND IT DOES NOT NEED TO BE**: the whole shaft
            # interior is open below the platform and the whole shaft interior is the tank, so a
            # body that drifts sideways on the way down still lands in water. That is a property
            # of THIS tower and not of a chute in general, so it is stated rather than assumed.
            "fall_zone": [[f.at(i, d, 0)[0], f.at(i, d, 0)[2]] for (i, d) in sorted(INSIDE - CASE)],
            "fall_from": f.at(0, 0, PLAT)[1],
            "fall_to": f.at(0, 0, -1)[1],
            "pool": [list(c) for c in sorted(wet)],
            "pool_top": f.at(0, 0, -1)[1],
            "contract": "a latticed shaft with real openings and glazed panels, and A RIDE: a "
                        "soul-sand bubble column lifts you %d courses from the pool in the "
                        "tower's base to a platform under the winch house, and the platform is a "
                        "floor with a %dx%d hole in it. The chute below that hole is proved clear "
                        "cell by cell and lands in two courses of water, which cancels the fall "
                        "entirely; the lift's seal is proved by simulation. You swim back to the "
                        "lift without leaving the tank." % (PLAT + 1 + POOL_D, 3, 3),
            "unverified": ["nobody has ridden it in game. The column, the seal and the clear fall "
                           "are simulated here; whether a %d-course drop lands cleanly in the "
                           "middle of a 3x3 chute is reasoning until someone jumps." % (PLAT + 2)]}


def _cap_band(pal, k):
    """The cap's banding: the land's two canopy colours alternating up the pyramid."""
    a, b = pal["canopy"]
    return a if k % 2 == 0 else b


# ------------------------------------------------------------------ the carousel

def _mount(w, f, pal, c, a, b, coat, base, rear, tailed, barrel, top_h):
    """One hobby horse on its pole: a small convex mass, and the pole that ties it to the canopy.

    A mount is a barrel, a neck, a head and sometimes a tail, at five cells long, and that is all
    the anatomy there is room for - trying for more is the eight-mammal mistake at 1/20 scale. The
    pole runs deck to canopy because that is both what a carousel looks like and what turns twelve
    small masses into one connected piece.
    """
    tu = (-b, a)
    if abs(tu[0]) >= abs(tu[1]):
        ui, ud = (1 if tu[0] > 0 else -1), 0
    else:
        ui, ud = 0, (1 if tu[1] > 0 else -1)
    for h in range(1, top_h):
        w.put(*f.at(c + a, c + b, h), pal["post"])
    for t in barrel:
        for h in (base, base + 1):
            w.put(*f.at(c + a + ui * t, c + b + ud * t, h), coat)
    w.put(*f.at(c + a + ui * 2, c + b + ud * 2, base + 1), coat)     # neck
    w.put(*f.at(c + a + ui * 2, c + b + ud * 2, base + 2), coat)     # head
    if rear:
        w.put(*f.at(c + a + ui * 2, c + b + ud * 2, base + 3), coat)
    if tailed:
        w.put(*f.at(c + a - ui * 2, c + b - ud * 2, base + 1), coat)
    return (coat, base, rear)


def _carousel(w: World, p: dict, ctx) -> dict:
    """A CAROUSEL, AND A RIDE THAT ACTUALLY GOES ROUND: a minecart circuit between two rings of
    mounts, under a wedge-striped cone.

    **THE HORSES CANNOT MOVE, SO THE RIDER DOES.** Nothing in vanilla rotates a structure, and no
    amount of redstone will turn a canopy - but a minecart on a closed circle is genuinely a
    carousel from inside the cart, which is the only seat that matters. So the mounts stand still
    on their poles and a rail circuit runs between the inner ring and the outer one, boarded off
    the front gate, continuously powered so that a cart put on it goes.

    **THE CIRCLE IS WHAT THE IRON IS SPENT ON, AND IT IS SPENT DELIBERATELY.** `powered_rail` has
    no curved state at all, so every direction change is a plain `rail` - iron, the scarce metal
    here, against gold which is farmable. A voxel circle at r=11 is 88 cells of which 52 are
    corners: about twenty iron ingots. The Island Line took a SQUARE helix to dodge exactly this
    bill, and here it is paid, because a carousel that goes round a square is not a carousel. The
    corner count, the iron and the gold are all reported rather than buried.

    **AN UNPOWERED POWERED_RAIL IS A BRAKE.** So the sources are dealt PER RUN between corners - a
    plain rail does not carry the chain, and a flat spacing leaves a dead rail on the far side of
    every turn, which is a cart that stops in mid-ride. `coaster._runs` and `coaster._power` are
    the same code the roller coaster uses; two implementations of that rule would drift.

    **AND THE CONE IS STILL THE PIECE.** A cone in one colour is a roof; the same cone in
    alternating radial wedges is a big top, read from the PLAN, which is the view voxels give away
    free. Every ring of it carries a riser, because ring r sits at apex-r and ring r+1 at
    apex-r-1 - orthogonal neighbours one course apart, which is DIAGONAL in 3-D and not connected.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    mr = int(p["min_run"])

    Dm = max(21, int(p["diameter"] or 31) | 1)
    R = Dm // 2
    RC = R + 1                          # the canopy oversails the deck by one
    W = 2 * RC + 1
    c = W // 2
    APEX = RC + 11                      # the eave sits eleven over the deck whatever the diameter
    n_out = max(8, int(p["mounts"]))
    n_in = max(6, (n_out * 2) // 3)
    out_r = R - 1
    in_r = max(5, R - 8)
    track_r = (out_r + in_r) // 2       # BETWEEN the two rings, which is where a rider belongs
    FORE = 5                            # the forecourt in front of the entrance gate

    def h_of(a, b):
        return APEX - int(round(math.sqrt(a * a + b * b)))

    # ---- THE TRACK, PLANNED FIRST. It is the one thing here that may not be skipped: a rail cell
    # quietly dropped for a pole or a fence is a broken circuit that audits perfectly clean, so
    # the path is reserved before anything else is drawn and every later loop is checked against it.
    track = _ring_path(track_r)
    tset = set(track)
    for r in (in_r, out_r):
        if r == track_r:
            raise ValueError("a mount ring and the track share a radius; the poles are on the rail")
    corners = _corners(track, True)
    power = _power(len(track), corners, int(p.get("power_every", 8)))

    # ---- pad, forecourt, then the deck one course proud of it: radial wedges, not a slab.
    for (a, b) in _disc(RC):
        w.put(*f.at(c + a, c + b, -1), pal["trim"] if a * a + b * b > R * R else pal["ground"])
    for a in range(-4, 5):
        for b in range(-(RC + FORE), -RC):
            w.put(*f.at(c + a, c + b, -1), pal["path"] if (a + b) % 2 else pal["ground"])
    deck = set()
    for (a, b) in _disc(R):
        r = math.hypot(a, b)
        if (a, b) in tset:
            blk = pal["trim"]           # the track's own bed, one tone, so the circuit reads
        elif r > R - 1.2 or (a == 0 and b == 0):
            blk = pal["accent"]
        elif _wedge(a, b, 12) % 2 == 0:
            blk = pal["ground"]
        else:
            blk = pal["path"]
        w.put(*f.at(c + a, c + b, 0), blk)
        deck.add((a, b))
    missing = tset - deck
    if missing:
        raise ValueError("%d track cells have no deck under them, the first %s"
                         % (len(missing), sorted(missing)[:3]))

    # ---- the rail: the deck's own outer edge, with four ways in.
    gates, fenced = 0, 0
    for (a, b) in sorted(deck):
        if all((a + u, b + v) in deck for (u, v) in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        if abs(a) <= 1 and abs(b) > 1:
            if a == 0:
                w.put(*f.at(c + a, c + b, 1), pal["gate"],
                      facing=_wdir(f, 0, -1) if b > 0 else _wdir(f, 0, 1),
                      open="true", in_wall="false", powered="false")
                gates += 1
            continue
        if abs(b) <= 1 and abs(a) > 1:
            if b == 0:
                w.put(*f.at(c + a, c + b, 1), pal["gate"],
                      facing=_wdir(f, 1, 0) if a > 0 else _wdir(f, -1, 0),
                      open="true", in_wall="false", powered="false")
                gates += 1
            continue
        w.put(*f.at(c + a, c + b, 1), pal["fence"])
        fenced += 1
    # A step up at each of the four gates - three cells, exactly the shortest run allowed. THE PAD
    # IS LAID UNDER THEM FIRST: the disc reaches (R+1, 0) and not (R+1, 1), so two stairs in every
    # flight would have stood on nothing. A skyblock plot is void; anything outside the disc has to
    # bring its own floor.
    steps = []
    for (ui, ud) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for t in (-1, 0, 1):
            a = ui * (R + 1) + (0 if ui else t)
            b = ud * (R + 1) + (0 if ud else t)
            w.put(*f.at(c + a, c + b, -1), pal["trim"])
            # **A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D.** These steps climb from
            # the forecourt INWARD onto the deck, so the facing is inward - `(ui, ud)` points the
            # other way, out of the ride. Written outward the risers face into the descent and the
            # step cannot be walked up; our renderer draws both directions identically, so this is
            # asserted in `tests/test_bigwheel_rides.py` rather than eyeballed.
            steps.append((("s", ui, ud), t + 1, f.at(c + a, c + b, 0), _wdir(f, -ui, -ud)))
    _stair_run(w, f, pal, steps, mr, half="bottom")

    # ---- the centre column: banded, with a stair corbel top and bottom. It runs to APEX-2 so its
    # crown meets the canopy's r=1 ring at APEX-1; a course short of that the cone hangs off
    # nothing but its own outer rings.
    for h in range(1, APEX - 1):
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                band = (h % 4 in (0, 1))
                w.put(*f.at(c + a, c + b, h), pal["accent"] if band else pal["trim"])
    for k in (3, APEX - 4):
        corb = []
        for (ui, ud) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for t in (-1, 0, 1):
                a = ui * 2 + (0 if ui else t)
                b = ud * 2 + (0 if ud else t)
                corb.append((("c", k, ui, ud), t + 1, f.at(c + a, c + b, k),
                             _wdir(f, -ui, -ud)))
        _stair_run(w, f, pal, corb, mr, half="top")

    # ---- the mounts, in two rings with the track running between them.
    #
    # **THE MOUNT'S LENGTH IS GRADED BY ITS OWN ARC, and it has to be.** Twelve five-cell horses
    # round a ring 44 cells long is 3.7 cells each: they touch, and in the PLAN the ring reads as
    # one continuous bar of wool with no horses in it at all. Every check passed, because a fused
    # ring is still one connected piece of legal cheap blocks. So a crowded ring gets ponies and a
    # roomy one gets full horses, and either way there is a clear cell between them.
    mounts, arcs = [], []
    for (r, n) in ((out_r, n_out), (in_r, n_in)):
        arc = 2 * math.pi * r / n
        arcs.append(round(arc, 2))
        barrel, tailed = (((-1, 0, 1), True) if arc >= 6.0 else
                          ((-1, 0, 1), False) if arc >= 4.5 else ((0, 1), False))
        for m in range(n):
            th = 2 * math.pi * m / n + (0.0 if r == out_r else math.pi / n)
            a = int(round(r * math.cos(th)))
            b = int(round(r * math.sin(th)))
            if (a, b) in tset:
                raise ValueError("mount %d of the r=%d ring stands on the track at %s"
                                 % (m, r, (a, b)))
            coat = BRIGHT[int(hash01(m, n, r, f.x) * len(BRIGHT))]
            base = 4 if hash01(m, 3, r, f.z) < 0.5 else 5
            rear = hash01(m, 9, r, f.x) < 0.34
            mounts.append(_mount(w, f, pal, c, a, b, coat, base, rear, tailed, barrel,
                                 h_of(a, b)))

    # ---- the canopy: alternating wedges, every ring carrying its own riser.
    # TWO COLOURS ALTERNATING, never six: one colour is a roof, two is a big top, and a wedge each
    # from a list of twelve is a beach ball. The second colour is hashed per build, so two
    # carousels in one park are the same geometry and different places.
    ca = pal["canopy"][0]
    alt = BRIGHT[int(hash01(f.x, f.z, 11) * len(BRIGHT))]
    for (a, b) in _disc(RC):
        blk = ca if _wedge(a, b, 12) % 2 == 0 else alt
        h = h_of(a, b)
        w.put(*f.at(c + a, c + b, h), blk)
        w.put(*f.at(c + a, c + b, h + 1), blk)

    # ---- the eave fringe. THE RUN HERE IS THE WHOLE RING, measured along its own axis: it is one
    # closed course of ~56 cells, not a scattered course, which is what rule 9 is about.
    eave = [(a, b) for (a, b) in _disc(RC) if int(round(math.hypot(a, b))) == RC]
    if len(eave) >= mr:
        for (a, b) in eave:
            face = _wdir(f, -1 if a > 0 else (1 if a < 0 else 0), 0) if abs(a) >= abs(b) \
                else _wdir(f, 0, -1 if b > 0 else 1)
            w.put(*f.at(c + a, c + b, h_of(a, b) - 1), pal["stair"],
                  facing=face, half="top", shape="straight", waterlogged="false")

    # ---- lights hung under the canopy, one ring in from the eave.
    lit = 0
    for k in range(8):
        th = 2 * math.pi * k / 8 + math.pi / 8
        a = int(round((RC - 2) * math.cos(th)))
        b = int(round((RC - 2) * math.sin(th)))
        if int(round(math.hypot(a, b))) == RC:
            continue                    # that course belongs to the eave fringe
        if _lamp(w, *f.at(c + a, c + b, h_of(a, b) - 1), pal["light"]):
            lit += 1

    # ---- THE CIRCUIT, laid last so nothing can quietly take one of its cells. A cell that is
    # already occupied is an ERROR, never a skip: a rail dropped for a fence post is a dead end
    # a hundred blocks from anything that would show it.
    shapes = _shapes([f.at(c + a, c + b, 1) for (a, b) in track], corners, True)
    for j in power:
        a, b = track[j]
        w.put(*f.at(c + a, c + b, 0), "redstone_block")
    for j, (a, b) in enumerate(track):
        pos = f.at(c + a, c + b, 1)
        if w.has(*pos):
            raise ValueError("track cell %d at %s is occupied by %s"
                             % (j, (a, b), w.name(*pos)))
        w.put(*pos, "rail" if j in corners else "powered_rail", shape=shapes[j])

    # ---- the station: the gate you board at, its canopy, its queue and its name.
    board_j = min(range(len(track)),
                  key=lambda j: track[j][0] ** 2 + (track[j][1] + track_r) ** 2)
    board = f.at(c + track[board_j][0], c + track[board_j][1], 1)
    signs = 0
    title = str(p.get("title") or "CAROUSEL").upper()
    for a in (-3, 3):
        for h in range(5):
            w.put(*f.at(c + a, c - (RC + 1), h), pal["post"])
    for a in range(-3, 4):
        w.put(*f.at(c + a, c - (RC + 1), 5), pal["trim"])
    for a in range(-4, 5):
        w.put(*f.at(c + a, c - (RC + 2), 6), pal["trim"])
    # THE LAMPS COME AFTER THE LINTEL THEY HANG FROM. Placed before it, `_lamp` finds no full
    # block above OR below, refuses, returns False, and the entrance is unlit in silence - the
    # exact "does nothing, quietly" failure this file keeps writing rules about.
    for a in (-3, 3):
        _lamp(w, *f.at(c + a, c - (RC + 2), 5), pal["light"])
    if p.get("sign", True) and _signed(w, f, pal, c, c - (RC + 2), 5, f.facing,
                                       [title[:SIGN_WIDTH], "", "%d mounts" % len(mounts),
                                        "board inside"]):
        signs += 1
    for lane in range(2):               # a switchback queue on the forecourt
        b = -(RC + 2) - lane
        lo, hi = (-4, 2) if lane == 0 else (-2, 4)
        for a in range(lo, hi + 1):
            if lane == 0 and abs(a) <= 1:
                continue                # the way through
            w.put(*f.at(c + a, c + b, 0), pal["fence"])
    # ...and two on the column itself, which is what a rider reads from the cart.
    if p.get("sign", True) and _signed(w, f, pal, c, c - 2, 7, f.facing,
                                       [title[:SIGN_WIDTH], "", "%d mounts" % len(mounts),
                                        "%d-cell circuit" % len(track)]):
        signs += 1
    if p.get("sign", True) and _signed(w, f, pal, c, c + 2, 7, f.back,
                                       [title[:SIGN_WIDTH], "", "mind the rail", "hold the pole"]):
        signs += 1

    iron = round(len(corners) * 6 / 16.0, 1)
    return {"kind": "carousel", "width": W, "depth": W + FORE, "diameter": Dm,
            "top": APEX + 1, "mounts": len(mounts), "colours": len({m[0] for m in mounts}),
            "shapes": len(set(mounts)), "mount_arcs": arcs, "gates": gates,
            "rail": fenced, "lamps": lit, "signs": signs,
            "ride": "minecart circuit",
            "track_r": track_r, "track": len(track), "corners": len(corners),
            "powered": len(track) - len(corners), "sources": len(power),
            "iron_ingots": iron, "gold_ingots": len(track) - len(corners),
            "rail_path": [list(f.at(c + a, c + b, 1)) for (a, b) in track],
            "rail_corners": sorted(corners),
            "rail_power": [list(f.at(c + track[j][0], c + track[j][1], 0)) for j in sorted(power)],
            "board": list(board),
            "contract": "a raised disc ringed by rail with four gated steps, a banded column, a "
                        "wedge-striped cone whose every ring carries its riser, twenty mounts in "
                        "two rings - and A RIDE: a closed minecart circuit of %d cells running "
                        "between the two rings. Every direction change is a plain rail because a "
                        "powered rail has no curved state; every straight run between corners "
                        "carries a redstone_block at both ends, because an unpowered powered rail "
                        "is a brake. %d corners, %d powered rails: about %s iron and %d gold."
                        % (len(track), len(corners), len(track) - len(corners), iron,
                           len(track) - len(corners)),
            "unverified": ["nobody has ridden it in game. The circuit's geometry, its power chain "
                           "and its clearances are asserted here; whether a cart holds speed round "
                           "a corner every other cell is reasoning until someone rides it."]}


BUILDERS = {
    "wheel": _wheel,
    "drop": _drop,
    "carousel": _carousel,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**RIDES, **cfg}
    if not p.get("at"):
        raise ValueError("bigwheel needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown bigwheel kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    # `kind` IS EXCLUDED FROM THE MERGE ON PURPOSE. Every builder returns its own bare `kind`, and
    # spread last it overwrites the namespaced one - the sidecar then reads `wheel`, which is also
    # what `casino` calls one of its games. A sidecar's kind is how a design is identified later;
    # two subsystems answering to one word is a collision waiting for whoever reads it next.
    return w.canvas({
        "kind": f"bigwheel/{p['kind']}",
        "ride": p["kind"],
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("kind", "contract", "unverified")},
    })
