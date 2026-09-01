"""Track rides: a roller coaster that returns to its station, and a water flume.

Both are the same shape of problem and it is not the shape any other generator here solves. A
building is a footprint with courses over it; a RIDE is a one-dimensional path through the air
that has to obey the game's own rules about what a rail or a fluid will do, and every one of
those rules is invisible in a render. `railspiral.py` settled the rail half of it and this module
follows it exactly rather than re-deriving it:

    powered_rail  shape = north_south, east_west, ascending_{n,s,e,w}
    rail          shape = ...those six, PLUS south_east, south_west, north_west, north_east

**A POWERED RAIL CANNOT CURVE**, read off `data/blocks.json` and re-asserted by this module's own
test rather than remembered. So every direction change is a plain `rail` and therefore IRON, and
iron is the scarce metal on this server while gold is farmable - which inverts the usual advice
and makes the PLAN SHAPE an economic decision. Hence a circuit of straight flights joined at
right angles, six corners in the whole ride, and everything else powered.

**NEVER DESCEND INTO A CORNER.** A curve has no ascending shape either, so a corner and both of
its neighbours must sit at one height; drop into one and the game re-derives the turn as a slope,
the turn is lost and the line dead-ends. `_profile` freezes the height at every corner and at the
cell on each side of it, and `_feasible` is what turns "this leg cannot absorb its own climb" into
an exception at generation time instead of a coaster that stops in mid-air.

**AN UNPOWERED POWERED_RAIL IS A BRAKE**, so a bed cell becomes a `redstone_block` every
`power_every` - counted BETWEEN CORNERS, because a plain rail does not propagate the chain and a
flat spacing leaves a dead rail on the far side of every turn.

WATER IS THE SAME PROBLEM WITH A DIFFERENT REGISTRY FACT. Flowing water dies seven blocks from
its source, so a flume's bed is `water[level=0]` cell by cell - every cell a source, so the
channel neither drains nor stops. And then:

    A DESCENDING OPEN CHANNEL OF STATIC SOURCES CANNOT EXIST.

That is worth stating because three plausible cross-sections were drawn before it was noticed. A
water cell whose downstream neighbour sits a course lower has an EXPOSED VERTICAL FACE at its own
top level, and an exposed face beside a source is a leak whatever the depth of the channel: at
depth 1 the face is one cell, at depth 2 it is still one cell, one course higher. Sealing it puts
a block directly over the lower cell - which is to say, **a graded flume is a covered flume, by
construction**. So the geometry is not fought: `_seal_column` fills exactly the courses a face
demands and nothing else, which leaves the flat runs OPEN and turns the lift and the drop into
enclosed tubes. Their outer walls are `glass_pane` at the water's own levels, so the one thing
the ride is about is visible through the thing that makes it legal.

GEOMETRY, stated once because getting it wrong is invisible in every render - the same convention
`park.py` and `casino._room` use, and imported from `park` so a facing bug can only be one bug:

    at       the ride's FRONT-LEFT floor corner, in world coordinates
    facing   the direction the FRONT looks out
    i        runs along the frontage; d runs from the front INTO the plot; h courses up
    at(i, d, h) = (x - dx*d + sx*i, y + h, z - dz*d + sz*i)

**THE PLOT IS VOID.** There is no terrain, so h=-1 is an APRON the ride lays for itself along its
own path, and every elevated course is carried down to it on trestles. Nothing floats, and that
is a property of the build rather than a hope: the apron is a continuous band, the deck is a
continuous line, and the trestles join them.
"""
from __future__ import annotations

from .. import fluids, walk
from .canvas import Canvas, hash01
from .park import LANDS, SIGN_WIDTH, _BACK, _Frame, _STEP, _sign
from .vertical import Ctx, World

# World-direction names, for the rail `shape` the game derives on placement. Emitted anyway so
# the render and Litematica's overlay agree with the build - `work.INTENTIONAL` does not compare
# it, exactly as it does not compare a stair's.
_DIRS = {(0, 1): "south", (0, -1): "north", (1, 0): "east", (-1, 0): "west"}
_CURVE = {frozenset(("north", "east")): "north_east",
          frozenset(("north", "west")): "north_west",
          frozenset(("south", "east")): "south_east",
          frozenset(("south", "west")): "south_west"}
_AXIS = {"north": ("north", "south"), "south": ("north", "south"),
         "east": ("east", "west"), "west": ("east", "west")}
_LEAN = {"east": "west", "west": "east", "north": "south", "south": "north"}

# What a rider passes through unharmed. Anything else within two courses over a rail cell is a
# collision or a suffocation, and both are invisible in every render this repo owns - the same
# set `attractions.py` checks its own three loop rides against (`_Circuit.verify`), imported from
# here rather than kept twice: two copies of "what a rider can pass through" is how one of them
# drifts. `_RIDER_HEAD` is how many of those courses a rider's body actually occupies.
_RIDER_THROUGH = {"rail", "powered_rail", "detector_rail", "activator_rail", "air",
                  "cave_air", "void_air", "torch", "wall_torch", "soul_torch", "redstone_wire"}
_RIDER_HEAD = 2                 # courses over a rail cell a rider's body occupies


def _rail_clearance(w, cells) -> list:
    """**THE CHECK NOTHING ELSE MAKES**, run against the FINISHED world.

    `attractions._Circuit.verify` states the reason and it applies here word for word: a
    generator that can only be told it is wrong by a test suite is one that ships wrong to
    anybody who calls it directly. This walks every cell the caller says carries a rail and
    reports every solid thing within `_RIDER_HEAD` courses above it - a roof, a post, a wall,
    anything a fixed-height structure built without knowing where the track ended up.
    """
    bad = []
    for (x, y, z) in cells:
        for k in range(1, _RIDER_HEAD + 1):
            n = w.name(x, y + k, z)
            if n is not None and n.split(":")[-1] not in _RIDER_THROUGH:
                bad.append(((x, y + k, z), n))
    return bad


COASTER = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "coaster",
    "facing": "east",
    "land": "frontier",
    "title": None,
    "seed": 7,

    # --- coaster ---------------------------------------------------------
    "span": 58,                 # the circuit's outer (i, d) extent; >= 55 is the brief
    "top": 45,                  # the lift hill's crest, in courses over the station
    "margin": 4,                # the circuit's inset from the frame origin
    "power_every": 8,           # a redstone_block in the bed this often, PER RUN between corners
    "trestle_every": 6,         # a trestle at least this often under elevated deck
    "light_every": 6,           # a lamp post this often ALONG A LAMP-POST SECTION (fence style 1)
    "fence_from": 3,            # the deck gets a safety rail at or above this height

    # --- flume -----------------------------------------------------------
    "flume_span": 44,
    "flume_top": 30,
    "pool": 7,                  # the splash pool's half-width
    "gantry_every": 5,          # an arch over the lift channel this often

    # --- rapids (the flume's replacement - see the section above it) -----
    "rapids_span": 24,          # the circuit's outer (i, d) extent
    "rapids_top": 14,           # courses the stair tower climbs, and the whole descent

    "min_run": 3,               # a trim course shorter than this is not drawn at all
}
DEFAULTS = COASTER              # the generator-module protocol's own name for it


# --------------------------------------------------------------------------- path & profile

def _trace(wps):
    """Waypoints -> the cell list and the index of each waypoint. Legs must be axis-aligned."""
    pts, marks = [], [0]
    for a, b in zip(wps, wps[1:]):
        if a[0] != b[0] and a[1] != b[1]:
            raise ValueError(f"leg {a[:2]} -> {b[:2]} is diagonal; rails and troughs run on axes")
        n = abs(b[0] - a[0]) + abs(b[1] - a[1])
        if n == 0:
            raise ValueError(f"zero-length leg at {a[:2]}")
        si = (b[0] > a[0]) - (b[0] < a[0])
        sd = (b[1] > a[1]) - (b[1] < a[1])
        if not pts:
            pts.append((a[0], a[1]))
        for k in range(1, n + 1):
            pts.append((a[0] + si * k, a[1] + sd * k))
        marks.append(len(pts) - 1)
    return pts, marks


def _corners(pts, closed):
    """Indices where the direction changes.

    `pts` is a TRUE CYCLE when `closed` - no duplicated endpoint - because the two conventions
    differ by one index at the seam and mixing them silently mis-reads the station's own turn as
    a straight, which the shape lookup then fails on with a frozenset of two OPPOSITE directions.
    """
    n = len(pts)
    out = set()
    for j in range(n):
        p = pts[j - 1] if j else (pts[n - 1] if closed else None)
        q = pts[j + 1] if j + 1 < n else (pts[0] if closed else None)
        if p is None or q is None:
            continue
        din = (pts[j][0] - p[0], pts[j][1] - p[1])
        dout = (q[0] - pts[j][0], q[1] - pts[j][1])
        if din != dout:
            out.add(j)
    return out


def _frozen(n, corners):
    """The cell indices whose height may not change: every corner and both its neighbours.

    ONE SOURCE, because `_profile` and `_feasible` must agree by construction. Written twice they
    drift, and the drift is silent: the check says a leg fits and the builder then raises on it,
    or worse, the check refuses a plan that would have built.
    """
    out = set()
    for c in corners:
        for k in (c - 1, c, c + 1):
            if 0 <= k < n:
                out.add(k)
    return out


def _free_per_leg(pts, marks, corners):
    """How many cells of each leg are actually free to change height. Legs in `marks` order."""
    frozen = _frozen(len(pts), corners)
    return [len([j for j in range(a + 1, b + 1) if j not in frozen])
            for a, b in zip(marks, marks[1:])]


def _feasible(pts, marks, wps, corners, what):
    """THE CHECK THE MODULE DOCSTRING ALWAYS NAMED AND NOBODY EVER WROTE.

    `_profile` does raise when a leg cannot absorb its own climb, but it raises from the middle of
    an index walk, in cell indices - *"only 43 of its 45 cells may change height"* - which says
    nothing about which knob to turn. Worse, both plans carried a hand-written minimum guard
    (`span - margin >= 50`, `flume_span >= 40`) that did not agree with the arithmetic underneath
    it: a coaster at span 55 passed the guard and then failed in `_profile`, and the module's only
    caller - `planner.py`'s frontier zone, at span 48 and flume_span 36 - was refused outright by
    the guard for sizes the geometry can build perfectly well.

    So the guard is the arithmetic now, it runs BEFORE anything is placed, and it names the
    dimension at fault.
    """
    bad = []
    for (a, b), (wa, wb), free in zip(zip(marks, marks[1:]), zip(wps, wps[1:]),
                                      _free_per_leg(pts, marks, corners)):
        delta = int(wb[2]) - int(wa[2])
        if abs(delta) > free:
            bad.append(f"the leg {wa[:2]} -> {wb[:2]} must move {delta} courses and only {free} "
                       f"of its {b - a} cells may change height")
    for wp in wps:
        if int(wp[2]) < 0:
            bad.append(f"waypoint {wp[:2]} sits {-int(wp[2])} courses BELOW the station, which "
                       f"puts the track under its own apron with nothing carrying it")
    if bad:
        raise ValueError(f"{what} cannot be built at this size: " + "; ".join(bad))


def _profile(pts, marks, wps, corners):
    """A height per cell, and the RULE THAT MAKES THE RIDE WORK: the height may not change at a
    corner or at either of its neighbours, and it may never change by more than one course a cell.

    Both are registry facts rather than taste - a curved rail has no ascending shape at all, and
    an ascending rail climbs exactly one course. A build that breaks either emits a schematic that
    passes the audit, the bill of materials and every render, and does not connect in game.
    """
    n = len(pts)
    frozen = _frozen(n, corners)
    h = [None] * n
    h[0] = int(wps[0][2])
    for (a, b), (wa, wb) in zip(zip(marks, marks[1:]), zip(wps, wps[1:])):
        ha, hb = int(wa[2]), int(wb[2])
        if h[a] is not None and h[a] != ha:
            raise ValueError(f"waypoint {wa[:2]} wants h={ha} but the leg into it left h={h[a]}")
        free = [j for j in range(a + 1, b + 1) if j not in frozen]
        delta = hb - ha
        if abs(delta) > len(free):
            raise ValueError(
                f"leg {wa[:2]} -> {wb[:2]} must move {delta} courses but only {len(free)} of its "
                f"{b - a} cells may change height (a corner and both its neighbours are flat)")
        picks = set()
        if delta:
            step = len(free) / float(abs(delta))
            picks = {free[int((k + 0.5) * step)] for k in range(abs(delta))}
        cur = ha
        for j in range(a + 1, b + 1):
            if j in picks:
                cur += 1 if delta > 0 else -1
            h[j] = cur
        if cur != hb:
            raise ValueError(f"leg {wa[:2]} -> {wb[:2]} ended at h={cur}, wanted {hb}")
    return h


def _world_path(f, pts, hs):
    return [f.at(i, d, h) for (i, d), h in zip(pts, hs)]


def _shapes(cells, corners, closed):
    """The rail `shape` for every cell, from its world neighbours."""
    n = len(cells)
    out = []
    for j, (x, y, z) in enumerate(cells):
        links = []
        for k in ((j - 1) if j else (n - 1 if closed else None),
                  (j + 1) if j + 1 < n else (0 if closed else None)):
            if k is None:
                continue
            o = cells[k]
            key = (o[0] - x, o[2] - z)
            if key in _DIRS:
                links.append((_DIRS[key], o[1] - y))
        if not links:
            out.append("north_south")
            continue
        if j in corners and len(links) == 2 and links[0][0] != links[1][0]:
            out.append(_CURVE[frozenset((links[0][0], links[1][0]))])
            continue
        up = [d for d, dy in links if dy > 0]
        if up:                                    # the LOWER cell of a slope ascends toward it
            out.append("ascending_" + up[0])
            continue
        d = links[0][0]
        out.append("north_south" if d in ("north", "south") else "east_west")
    return out


def _runs(n, corners):
    """Index ranges of consecutive POWERED cells. A corner is a plain rail and breaks the signal
    chain, so power is dealt per run - a flat spacing leaves a dead rail past every turn."""
    out, start = [], None
    for j in range(n):
        if j in corners:
            if start is not None:
                out.append((start, j))
            start = None
        elif start is None:
            start = j
    if start is not None:
        out.append((start, n))
    return out


def _power(n, corners, every):
    """Bed indices that become a `redstone_block`: both ends of every run, then every `every`
    along it. Both ends, because a run's far cell is the one a cart leaves a corner onto."""
    picks = set()
    for a, b in _runs(n, corners):
        for j in range(a, b, max(1, int(every))):
            picks.add(j)
        picks.add(b - 1)
    return picks


def _sides(pts, j, closed):
    """The (i, d) offsets of the deck edges at this cell: perpendicular to every direction the
    track leaves in. At a corner that is BOTH axes, which is what fills the elbow - a deck built
    on one perpendicular alone leaves a diagonal-only join, and diagonal is not connected."""
    n = len(pts)
    prev = pts[j - 1] if j else (pts[n - 1] if closed else None)
    nxt = pts[j + 1] if j + 1 < n else (pts[0] if closed else None)
    axes = set()
    for other, sign in ((prev, -1), (nxt, 1)):
        if other is None:
            continue
        di = (other[0] - pts[j][0]) * sign
        dd = (other[1] - pts[j][1]) * sign
        if di:
            axes.add("d")
        if dd:
            axes.add("i")
    offs = []
    if "d" in axes:
        offs += [(0, -1), (0, 1)]
    if "i" in axes:
        offs += [(-1, 0), (1, 0)]
    return offs or [(0, -1), (0, 1)]


# --------------------------------------------------------------------------- shared structure

def _apron(w, f, pal, pts, seed, radius=3):
    """The ground the ride stands on, laid along its own path.

    SEVEN THOUSAND IDENTICAL CELLS IS NOT A FLOOR, IT IS A SLAB - the casino hall's lesson. The
    paving is a world-aligned grid of dark lines with a checker between them and a scatter of the
    path tone, so it stays aligned across module boundaries and the dominant block stays well
    under half. A square of this radius per track cell also makes the band CONTINUOUS by
    construction, which is what the trestles and the station both stand on.
    """
    n = 0
    for (i, d) in pts:
        for oi in range(-radius, radius + 1):
            for od in range(-radius, radius + 1):
                x, y, z = f.at(i + oi, d + od, -1)
                if w.has(x, y, z):
                    continue
                if x % 8 == 0 or z % 8 == 0:
                    blk = pal["trim"]
                elif hash01(x, z, seed) < 0.14:
                    blk = pal["path"]
                elif (x + z) % 2 == 0:
                    blk = pal["ground"]
                else:
                    blk = pal["path"]
                w.put(x, y, z, blk)
                n += 1
    return n


def _pad(w, f, pal, i0, i1, d0, d1, seed):
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            x, y, z = f.at(i, d, -1)
            if w.has(x, y, z):
                continue
            w.put(x, y, z, pal["trim"] if (x % 8 == 0 or z % 8 == 0) else
                  (pal["ground"] if hash01(x, z, seed, 3) < 0.7 else pal["path"]))
            n += 1
    return n


def _trestle(w, f, pal, i, d, deck_h, offs, style, seed):
    """Posts and cross-bracing from the deck's underside down to the apron.

    THREE STYLES, CHOSEN BY A HASH OF THE CELL so the line varies and still regenerates the same
    every time. `random` is barred here for the reason the whole repo bars it: a design that
    cannot be rebuilt identically cannot be audited, diffed or finished by anyone else.

        0  a pair of legs with ties across the gap
        1  the same, flared onto outriggers for the bottom quarter
        2  a masonry pier - a hollow shaft with window gaps, for the tall runs only

    THE LEG SPACING IS READ FROM `offs`, NOT ASSUMED. A coaster's legs sit one cell either side
    of the rail and a flume's sit two either side of a five-wide trough, and a tie or an
    outrigger written for the first is a FLOATING BLOCK under the second - two cells from a leg
    is not adjacent, and a stray reads as a brace in every render.
    """
    n = 0
    o0 = offs[0]
    k = max(abs(o0[0]), abs(o0[1])) or 1
    ui, ud = o0[0] // k, o0[1] // k

    if style == 2 and deck_h >= 12:
        for a in range(-k, k + 1):
            for b in range(-k, k + 1):
                if max(abs(a), abs(b)) != k:
                    continue
                for hh in range(0, deck_h):
                    # window gaps, so the pier reads as masonry rather than as a solid lump. The
                    # ring's own corners run unbroken, so the shaft stays one piece.
                    if hh % 6 == 3 and (a == 0 or b == 0):
                        continue
                    w.put(*f.at(i + a, d + b, hh),
                          pal["trim"] if hh % 6 in (0, 5) else pal["post"])
                    n += 1
        return n

    for (oi, od) in offs:
        for hh in range(0, deck_h):
            w.put(*f.at(i + oi, d + od, hh), pal["post"])
            n += 1
    # TIES ACROSS THE WHOLE GAP, or they touch neither leg.
    for hh in range(2, deck_h, 5):
        for t in range(-k, k + 1):
            w.put(*f.at(i + ui * t, d + ud * t, hh), pal["beam"])
            n += 1
    if style == 1 and deck_h >= 8:
        foot = max(2, deck_h // 4)
        for (oi, od) in offs:
            si = (oi > 0) - (oi < 0)
            sd = (od > 0) - (od < 0)
            for hh in range(0, foot):
                w.put(*f.at(i + oi + si, d + od + sd, hh), pal["post"])
                n += 1
            # THE BRACKET IS A SLAB, which is what makes a flare read as a brace rather than as
            # a second, shorter post standing beside the first. The corpus says this repo places
            # stairs and slabs at a fraction of the rate outside builders do; a trestle is where
            # they earn it.
            w.put(*f.at(i + oi + si, d + od + sd, foot), pal["slab"],
                  type="top", waterlogged="false")
            n += 1
    return n


def _pane_run(w, f, pal, i, d, h, along):
    """A pane whose CONNECTION STATE is set along its own wall. With every side false it renders
    as a lone post rather than as glazing - the void tower's own note, and it is not derived."""
    props = {"north": "false", "south": "false", "east": "false", "west": "false",
             "waterlogged": "false"}
    for k in _AXIS[along]:
        props[k] = "true"
    w.put(*f.at(i, d, h), "glass_pane", **props)


# --------------------------------------------------------------------------- the coaster

def _coaster_plan(p):
    """The circuit, as waypoints in (i, d, h). It is a CLOSED loop: the last waypoint is the
    first, so a cart that leaves the station comes back to it.

    Read as a ride: station straight, flat approach, LIFT HILL, a crest with a jog in it, the
    FIRST DROP, a rise, the SECOND DROP, and a long return leg into the station. Six corners,
    which at one plain rail apiece is about two iron ingots for the whole circuit.

    **EVERY OFFSET AND EVERY DROP IS A FRACTION OF THE CIRCUIT, NOT A CONSTANT.** Written as
    constants - a crest run of 18, a first drop of 31, a second drop that put the last waypoint at
    `top - 39` - the plan only ever described ONE ride. Three things followed, all of them wrong:

      * at `span` 48 the drops were larger than their legs had cells to spend, so the ride could
        not be built at all - and 48 is what `planner.py` asks for;
      * at any `top` under 39 the second drop's `t - 39` went NEGATIVE, so the circuit dived
        under its own station and apron, twenty courses of track hanging with no trestle beneath
        it, and nothing raised: it audited clean, one connected piece, and wrong;
      * the guard that was supposed to catch this tested `span - margin >= 50`, which does not
        make the 55x55 circuit its own message claims (that needs 54) and does not correspond to
        any of the arithmetic above.

    The fractions below are chosen to reproduce the ride this module already shipped: at the
    default 4/58/45 the waypoints come out IDENTICAL to the constants they replace, cell for cell.
    """
    m = int(p["margin"])
    s = int(p["span"])
    t = int(p["top"])
    span = s - m
    if span < 20:
        raise ValueError(f"coaster span - margin is {span}; a circuit under 20 has no room for "
                         f"the 17-cell station, let alone a lift hill")
    if t < 4:
        raise ValueError(f"coaster top is {t}; a lift hill under 4 courses is not a lift hill")

    crest = span // 3               # the crest run along i          58/4  -> 18
    jog = span // 4 + 1             # the crest jog back along d     58/4  -> 14
    far = (span * 3) // 5           # how far the rise carries       58/4  -> 32
    settle = (span * 3) // 10       # the return leg's settle        58/4  -> 16

    # The flat approach is whatever the lift does not need. It is the one length that may shrink
    # to nothing useful, so it is clamped and then checked rather than assumed.
    approach = min(6, span - t - 2)
    if approach < 1:
        raise ValueError(f"a lift of {t} courses needs at least {t + 3} of span - margin to climb "
                         f"in; this circuit has {span}. Raise span or lower top.")

    drop1 = min(max(t // 2, t - 14), span - crest - 3)      # 45/58 -> 31
    rise = min(10, far - jog - 1, drop1)                    # 45/58 -> 10, and never above the crest
    apex = t - drop1 + rise
    drop2 = min(18, span - far - 2, apex)                   # 45/58 -> 18, and never below the apron
    if drop1 < 1 or rise < 0 or drop2 < 1:
        raise ValueError(f"a circuit of span {span} cannot hold a first drop, a rise and a second "
                         f"drop (got {drop1}/{rise}/{drop2}); raise span")
    return [
        (m,              m,          0),                  # station straight begins
        (m,              m + approach, 0),                # flat approach (colinear)
        (m,              s,          t),                  # CORNER - the lift hill's crest
        (m + crest,      s,          t),                  # CORNER - the crest run
        (m + crest,      s - jog,    t),                  # CORNER - the crest jog
        (s,              s - jog,    t - drop1),          # CORNER - FIRST DROP
        (s,              s - far,    apex),               # a rise back up (colinear)
        (s,              m,          apex - drop2),       # CORNER - SECOND DROP
        (m + settle,     m,          0),                  # the return leg settles (colinear)
        (m,              m,          0),                  # CORNER - closes on the station
    ]


def _roofable(w, pos):
    """False if a solid block here would leave a rail cell UNDER it without its two clear
    courses of headroom.

    THE ROOF SPANS THE TRACK - deliberately, see the docstring below - but the lift hill is laid
    before the station and can climb back through this same footprint at whatever height the
    profile put it, not just at the platform's own floor. A fixed `ceil` roof does not know that:
    it shipped an eave stair two courses over a climbing rail cell, which is a suffocating ceiling
    on a cart travelling at speed. Checked in the SAME COLUMN, one and two courses down - a rider
    occupies the cell a rail sits in and the one above it, so both must stay clear of whatever
    this function is about to place.
    """
    x, y, z = pos
    for dy in (1, 2):
        below = (x, y - dy, z)
        if w.has(*below) and "rail" in w.name(*below):
            return False
    return True


def _station(w, f, pal, p, seed, i0, i1, dt):
    """The building you board in: a platform beside the track, a canopy over both, a back wall
    with windows, and its name over the door.

    THE ROOF SPANS THE TRACK. A station whose canopy stops at the platform edge is a bus shelter;
    what makes this read as a station is that the cart runs UNDER the roof, which means the far
    columns stand on the deck's own outer edge and the safety rail is suppressed for the length
    of the platform - you cannot board through a fence.

    **AND THE ROOF MUST YIELD TO THE TRACK, NEVER COVER IT BLIND.** `_station` is built AFTER
    the whole circuit, so the rail is already in `w` by the time the canopy and its eave go up -
    `_roofable` is what reads that back rather than trusting the fixed `ceil` to clear whatever
    the lift hill did at this (i, d). A skipped roof cell is a small hole in the canopy directly
    over the climb, which is the same "left empty by the loop" rule the window openings already
    follow, applied to a hole the geometry demanded rather than one the plan asked for.
    """
    a, b = pal["canopy"]
    ceil = 6
    n = 0

    # PLATFORM. One course up from the apron, which puts a boarder's feet level with the cart.
    for i in range(i0 + 2, i1 + 1):
        for d in range(dt + 1, dt + 6):
            w.put(*f.at(i, d, 0),
                  pal["trim"] if d == dt + 1 else
                  (pal["ground"] if (i + d) % 2 else pal["path"]))
            n += 1

    # BACK AND SIDE WALLS, with window openings LEFT EMPTY BY THE LOOP. Building the ring first
    # and cutting a hole repaints cells that already exist - the void tower shipped a plain drum
    # for exactly this reason and nothing about the code looked wrong.
    holes = set()
    for i in range(i0 + 3, i1, 4):
        holes.add((i, dt + 6, 2))
        holes.add((i, dt + 6, 3))
    for i in range(i0 + 1, i1 + 2):
        for h in range(1, ceil):
            if (i, dt + 6, h) in holes:
                continue
            w.put(*f.at(i, dt + 6, h), pal["post"] if i in (i0 + 1, i1 + 1) else pal["wall"])
            n += 1
    for i in (i0 + 1, i1 + 1):
        for d in range(dt + 1, dt + 6):
            for h in range(1, ceil):
                w.put(*f.at(i, d, h), pal["wall"])
                n += 1

    # THE FAR COLUMNS, on the deck's outer edge, carrying the canopy over the track.
    for i in range(i0 + 1, i1 + 2, 6):
        for h in range(0, ceil):
            w.put(*f.at(i, dt - 1, h), pal["post"])
            n += 1

    # THE CANOPY: two colours alternating, which is what says fairground. One colour is a roof.
    # SKIPPED wherever the climb has come back through underneath - see `_roofable`.
    for i in range(i0, i1 + 3):
        for d in range(dt - 2, dt + 8):
            pos = f.at(i, d, ceil)
            if not _roofable(w, pos):
                continue
            w.put(*pos, a if (i + d) % 2 == 0 else b)
            n += 1
    # ...and an eave of upside-down stairs all round it, so the roof has an edge rather than
    # stopping at a cliff. Every run here is the full frontage, so the min_run gate is moot and
    # asserted rather than assumed - the clearance check is not: the reported bug, a boarding
    # roof intersecting the track, was one of THESE two, not the field above.
    span_i = list(range(i0, i1 + 3))
    if len(span_i) >= int(p["min_run"]):
        for i in span_i:
            front = f.at(i, dt - 3, ceil)
            if _roofable(w, front):
                w.put(*front, pal["stair"],
                      facing=_LEAN[f.facing], half="top", shape="straight", waterlogged="false")
                n += 1
            back = f.at(i, dt + 8, ceil)
            if _roofable(w, back):
                w.put(*back, pal["stair"],
                      facing=_LEAN[f.back], half="top", shape="straight", waterlogged="false")
                n += 1

    # LANTERNS under the canopy. The roof above is a FULL block, which is what a hanging lantern
    # needs - a lamp under a slab reads as 'hanging from air' in the audit, and correctly so.
    for i in range(i0 + 3, i1, 5):
        w.put(*f.at(i, dt + 3, ceil - 1), pal["light"], hanging="true", waterlogged="false")
        n += 1

    title = str(p.get("title") or "COASTER").upper()[:SIGN_WIDTH]
    mid = (i0 + i1) // 2
    signed = 0
    # Outside, over the entrance - a shop sign, read from the midway.
    signed += _sign(w, f, pal, mid, dt + 7, 4, f.back,
                    [title, "", "ride the line", ""])
    # Inside, on the back wall, facing whoever is standing on the platform.
    signed += _sign(w, f, pal, mid, dt + 5, 3, f.facing,
                    ["STATION", "mind the gap", "one lap", "stay seated"])
    return n, signed


def _coaster(w: World, p: dict, ctx) -> dict:
    f = _Frame(p)
    pal = LANDS[p["land"]]
    seed = int(p["seed"])
    wps = _coaster_plan(p)
    full, marks = _trace(wps)
    if full[-1] != full[0]:
        raise ValueError("the coaster's waypoints must close on the station")
    pts = full[:-1]
    corners = _corners(pts, True)
    # `_profile` walks the OPEN list, so the seam corner has to be named in both index spaces or
    # the return leg is free to keep descending straight into the station's turn.
    seam = corners | ({len(full) - 1} if 0 in corners else set())
    _feasible(full, marks, wps, seam, "the coaster's circuit")
    hs_full = _profile(full, marks, wps, seam)
    if hs_full[-1] != hs_full[0]:
        raise ValueError("the circuit does not close in height")
    hs = hs_full[:-1]
    n = len(pts)
    cells = _world_path(f, pts, hs)
    shapes = _shapes(cells, corners, True)
    powered = _power(n, corners, p["power_every"])

    m, s, top = int(p["margin"]), int(p["span"]), int(p["top"])
    st_i0, st_i1, st_dt = m, m + 16, m
    station_zone = set()
    for i in range(st_i0 - 2, st_i1 + 4):
        for d in range(st_dt - 3, st_dt + 9):
            station_zone.add((i, d))

    _apron(w, f, pal, pts, seed)
    _pad(w, f, pal, st_i0 - 2, st_i1 + 3, st_dt - 3, st_dt + 8, seed)

    # THE DECK. The bed under the rail, plus one cell either side - a walkway level with the
    # track, which is what the safety rail stands on and what the trestles carry.
    side_of = [_sides(pts, j, True) for j in range(n)]
    track_at = {cells[j] for j in range(n)}
    for j, (i, d) in enumerate(pts):
        w.put(*f.at(i, d, hs[j] - 1), pal["beam"])
        for (oi, od) in side_of[j]:
            w.put(*f.at(i + oi, d + od, hs[j] - 1), pal["trim"])

    # TRESTLES, and always one at a corner: the elbow is where the deck is widest and where a
    # missing leg would be most obvious.
    trestles = 0
    every = max(2, int(p["trestle_every"]))
    for j, (i, d) in enumerate(pts):
        deck = hs[j] - 1
        if deck < 1:
            continue
        if not (j % every == 0 or j in corners):
            continue
        style = int(hash01(j, seed, 11) * 3)
        _trestle(w, f, pal, i, d, deck, side_of[j][:2], style, seed)
        trestles += 1

    # POWER, then the rails on top of it: a redstone_block under a powered rail is still a bed.
    for j in powered:
        i, d = pts[j]
        w.put(*f.at(i, d, hs[j] - 1), "redstone_block")
    for j, (i, d) in enumerate(pts):
        w.put(*f.at(i, d, hs[j]), "rail" if j in corners else "powered_rail", shape=shapes[j])

    # THE SAFETY RAIL, and the deck's dressing. VARIED BY SECTION, deterministically: a plain
    # fence, a fence with LAMP POSTS, or a fence over a fascia of upside-down slabs under the deck
    # edge. A ride whose every elevated metre looks identical is one long box.
    #
    # STYLE 1 USED TO BE STYLE 0 WITH A DIFFERENT NUMBER ON IT. Its comment always said "a fence
    # with lamp posts" and the lamps were placed by a separate rule that ignored `style` entirely,
    # so nothing in the code ever read the value 1: measured over the default circuit, 87 cells of
    # style 0 and 36 of style 1 emitted byte-identical dressing, and two thirds of the elevated
    # deck was one treatment claiming to be two. The lamp posts belong to the style that is named
    # after them.
    #
    # AND A STYLE THAT CAN EMIT NOTHING IS THE SAME BUG AGAIN, so a lamp-post section is
    # guaranteed its first post: `light_every` spaces the rest of them, and on a section shorter
    # than that spacing the modulo alone would land on no cell at all.
    fences, lamps = 0, 0
    fence_from = int(p["fence_from"])
    lit_sections = set()
    for j, (i, d) in enumerate(pts):
        if hs[j] < fence_from or (i, d) in station_zone:
            continue
        section = j // 12
        style = int(hash01(section, seed, 5) * 3)
        for (oi, od) in side_of[j]:
            pos = f.at(i + oi, d + od, hs[j])
            if pos in track_at or w.has(*pos):
                continue
            w.put(*pos, pal["fence"])
            fences += 1
            if style == 2:
                fascia = f.at(i + oi, d + od, hs[j] - 2)
                if not w.has(*fascia):
                    w.put(*fascia, pal["slab"], type="top", waterlogged="false")
        if style != 1:
            continue
        if section in lit_sections and j % max(4, int(p["light_every"])):
            continue
        oi, od = side_of[j][0]
        # THE WHOLE COLUMN IS TESTED, not just its foot. A post whose head lands in the track of
        # a leg passing above puts a lamp inside the rail - and the foot alone cannot see that.
        column = [f.at(i + oi, d + od, hs[j] + k) for k in range(4)]
        if any(c in track_at for c in column):
            continue
        w.put(*column[0], pal["post"])
        w.put(*column[1], pal["post"])
        w.put(*column[2], pal["trim"])
        # ON TOP OF A POST IT STANDS, it does not hang: written hanging=true the lamp is
        # looking for a block ABOVE it, finds open sky, and hangs from nothing.
        w.put(*column[3], pal["light"], hanging="false", waterlogged="false")
        lit_sections.add(section)
        lamps += 1

    built, signed = _station(w, f, pal, p, seed, st_i0, st_i1, st_dt)

    # THE CHECK NOTHING ELSE MAKES, run against the FINISHED world - after the station, which is
    # the one thing here built with a fixed height that does not itself know where the track
    # ended up. `_roofable` is what stops this ever firing on the station's own canopy; it is
    # asserted here as well because a generator that can only be told it is wrong by a test suite
    # is one that ships wrong to anybody who calls it directly.
    bad = _rail_clearance(w, track_at)
    if bad:
        raise ValueError("coaster: %d track cell(s) have something in the rider: %s"
                          % (len(bad), bad[:4]))

    # THE DROPS ARE MEASURED PER LEG, NOT AS CONTIGUOUS DESCENDING RUNS. A 31-course fall spread
    # evenly over 34 cells has three flat cells in it, and counting runs reported that honest,
    # smooth grade as four little drops of eight.
    drops = sorted((a[2] - b[2] for a, b in zip(wps, wps[1:]) if b[2] < a[2]), reverse=True)

    return {
        "kind": "coaster",
        "track": n, "corners": len(corners), "powered": len(powered),
        "trestles": trestles, "fences": fences, "lamps": lamps,
        "station_blocks": built, "signs": signed,
        "top": top, "span": s, "drops": drops[:4],
        "contract": "a closed circuit: it leaves the station, climbs the lift hill, takes two "
                    "drops and six flat corners, and returns to the same platform. Every corner "
                    "is a plain rail and flat on both sides; every powered run carries a "
                    "redstone_block at both ends and every %d cells; every elevated course "
                    "stands on trestles carried to the apron." % int(p["power_every"]),
        "unverified": ["the ride has not been run in game - a cart's SPEED over this grade and "
                       "power spacing is reasoning, not evidence. Ride it once before anyone is "
                       "told it completes the lap."],
    }


# --------------------------------------------------------------------------- the flume

def _wall_offs(pts, j):
    """`_sides` widened for a vertical WALL, never for a floor.

    At a corner `_sides` deliberately returns BOTH legs' perpendiculars - "at a corner that is
    BOTH axes, which is what fills the elbow" - and two of those four offsets are the unit
    direction TOWARD THE PREVIOUS AND NEXT PATH CELL, because one leg's own perpendicular is the
    other leg's travel axis. That is exactly right for a floor, which should fill the inside of
    the turn, and it is exactly wrong for a wall: doubled for clearance (see `_flume`) it does
    not land on j+1, it lands on j+2 along whichever leg it is - the ACTUAL WORLD POSITION of a
    real path cell two steps up that leg, walled in from outside its own generation pass with no
    way for the water loop to know a wall is coming. Every one of the five dry cells the first
    corner-aware build produced came from exactly this: a corner's own doubled perpendicular
    landing on a straight cell of one of its two legs.

    The fix is not a smaller radius - radius 1 collides with j+1 the same way radius 2 collides
    with j+2, any fixed offset along a leg's own axis eventually lands on a real cell of it. It is
    dropping the two offsets that point along either leg at all, which leaves exactly the corner's
    OUTER perimeter: the outside of the bend, which is the wall a trough actually wants there. The
    inside of the bend is walled by the two straight neighbours either side of the corner, using
    their own single-axis perpendiculars - unaffected, because neither of those offsets points
    along the OTHER leg.
    """
    n = len(pts)
    side = _sides(pts, j, False)
    block = set()
    if j:
        block.add((pts[j - 1][0] - pts[j][0], pts[j - 1][1] - pts[j][1]))
    if j + 1 < n:
        block.add((pts[j + 1][0] - pts[j][0], pts[j + 1][1] - pts[j][1]))
    return [o for o in side if o not in block]


def _cap(w, f, pal, pts, hs, j, wo):
    """Wall the OPEN END of the trough at path cell `j`, one step beyond it.

    A channel's walls are its perpendiculars, so the two ENDS of the run are never walled by the
    wall loop - and the head of this flume was therefore a lip one course above the apron, out of
    which the entire ride drained. The cap is the full five-wide section (centre, the two bed
    lanes, and the two wall lines) from the bed up past the wall top, so it meets the side walls
    face-to-face rather than diagonally: a cap only three wide leaves a diagonal gap at each
    shoulder, and diagonal is not a seal any more than it is a connection.

    **IT IS NOT WHAT MAKES THE RIDE WATERTIGHT, AND SAYING SO WOULD BE A LIE THE NEXT PERSON
    INHERITS.** `_shell` walls every open face of the envelope, the head included, so removing
    this function changes nothing a simulator can see - which is exactly what
    `test_the_leak_check_can_actually_fail` found when it tried to break containment by stubbing
    it. What the cap buys is a deliberate five-wide masonry end where the trough stops, instead of
    a wall shaped by wherever water happened to be able to reach.
    """
    ci, cd = pts[j]
    nxt = pts[j + 1] if j + 1 < len(pts) else pts[j - 1]
    step = (ci - nxt[0], cd - nxt[1])                    # one step OUT of the channel
    step = (max(-1, min(1, step[0])), max(-1, min(1, step[1])))
    offs = [(0, 0)] + wo + [(o[0] * 2, o[1] * 2) for o in wo]
    for (oi, od) in offs:
        for hh in range(hs[j], hs[j] + 4):
            w.put(*f.at(ci + step[0] + oi, cd + step[1] + od, hh), pal["wall"])


def _touches(w: World, pos) -> bool:
    (x, y, z) = pos
    return any(w.has(x + dx, y + dy, z + dz) for (dx, dy, dz) in
               ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))


_SHELL_DROP = 6     # how far a plug reaches for footing before it gives up


def _shell(w: World, pal, envelope, keep=()) -> int:
    """Give every cell water is ALLOWED in a bed, and a wall on every side that is not.

    **`keep` IS WHERE A PLAYER'S HEAD GOES, AND IT IS NOT THE ENVELOPE.** A walkway beside the
    water needs two clear courses over it, and the obvious move - declaring those courses part of
    the envelope - does not work: this walls one ring further out, onto the next cell of the
    approach, which then needs declaring too. Chased along a terrace it never terminates. Cells in
    `keep` are simply never filled, and they are deliberately NOT envelope, so if water ever does
    reach one `fluids.escapes` says so instead of the omission passing quietly.

    **THIS IS `_seal`'S IDEA WITH THE ONE DISTINCTION IT COULD NOT MAKE.** `_seal` filled the
    neighbours of every WATER BLOCK, which walled each spaced source into its own pocket - the
    gap between two sources is deliberately open, and a backstop working off water blocks cannot
    tell "open by design" from "open by accident". Working off the ENVELOPE it can: the gaps
    between sources are inside the envelope and are never touched, and everything outside it is
    a hole by definition.

    The hole this exists for is the OUTER CORNER'S DIAGONAL. `_wall_offs` correctly returns a
    corner's two outer perpendiculars, so the corner gets a bed and a wall on each of them - and
    nothing at all on the cell diagonal between the two, which has neither. Water crossed the bed
    lane, stepped diagonally into that cell, found no floor, and fell twenty courses to the apron
    and off the plot. Two corners, two holes, and the whole ride drained through them.
    """
    keep = {tuple(c) for c in keep}
    open_env = [c for c in envelope
                if (c not in w.cells) or w.cells[c][0] == "water"]
    seen = set(open_env)
    n = 0
    for (x, y, z) in open_env:
        # A BED, unless the cell below is itself part of the envelope - which is what a fall
        # inside the channel looks like. Bedding those would drop cobble straight into the water
        # lane of the cell below, and the ride would report every one of its forty path cells
        # dry while the design still audited clean.
        if (x, y - 1, z) not in seen and not w.has(x, y - 1, z):
            w.put(x, y - 1, z, pal["ground"])
            n += 1
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (x + dx, y, z + dz)
            if nb in seen or nb in keep or w.has(*nb):
                continue
            w.put(*nb, pal["wall"])
            n += 1
            # **AND IT NEEDS SOMETHING TO STAND ON.** A corner diagonal has neither bed nor wall,
            # so the plug filling it hangs in open air with all six neighbours empty - three of
            # them across the whole ride, which the connectivity test caught and nothing else
            # would have. Carried down to whatever is already there it joins the bed lanes either
            # side of it, which is what a corner's outer wall is in the first place.
            cur = nb
            for _k in range(_SHELL_DROP):
                if _touches(w, cur):
                    break
                low = (cur[0], cur[1] - 1, cur[2])
                if low in seen or low in keep or w.has(*low):
                    break
                w.put(*low, pal["ground"])
                n += 1
                cur = low
    return n


_FLUME_M = 4                # the flume's own margin, shared by the plan and the dock


def _flume_dims(p):
    """The two lengths the flume's plan and its buildings BOTH depend on, derived once.

    `flume_span >= 40` was a hand-written guard that neither matched the arithmetic under it nor
    the module's only caller: at span 40 with the default 30-course lift the plan it produced
    could not be built, while `planner.py`'s Log Flume at span 36 was refused before anything was
    measured. Both lengths are now whatever the span leaves over:

      dock  the still run before the lift, which is what the lift does not need to climb in
      run   the run-out to the pool, short enough that THE POOL CLEARS THE DOCK BUILDING - the
            pool is placed from the run-out's last cell, so a run-out sized independently of the
            dock walks the basin straight through the dock's own platform at small spans.

    At the default 44/30 both come out at 7 and 18, which is what they were written as.
    """
    m = _FLUME_M
    s, t = int(p["flume_span"]), int(p["flume_top"])
    half = max(4, int(p["pool"]))
    if t < 4:
        raise ValueError(f"flume_top is {t}; a lift under 4 courses is not a lift")
    dock = min(7, s - m - t - 2)
    run = min(18, s - m - half - 15)
    if dock < 2:
        raise ValueError(f"a lift of {t} courses needs at least {t + 4} of flume_span to climb "
                         f"in; this flume has {s}. Raise flume_span or lower flume_top.")
    if run < 6:
        raise ValueError(f"flume_span {s} leaves no run-out that clears the dock with a pool of "
                         f"half-width {half}; raise flume_span or lower pool")
    return m, s, t, half, dock, run


# Water reaches seven blocks from a source on the flat and a drop restarts that budget, so a
# source every six cells leaves no dry gap even where the channel runs level for a stretch.
SRC_EVERY = 6


def _flume_plan(p):
    """The channel, as waypoints in (i, d, h). NOT a circuit: a flume is a one-way ride that
    ends in the pool it started beside. Dock, LIFT, a top traverse, THE DROP, a run-out."""
    m, s, t, _half, dock, run = _flume_dims(p)
    return [
        (m,          m + 2,    0),      # the dock
        (m + dock,   m + 2,    0),      # dock end (colinear)
        (s,          m + 2,    t),      # CORNER - the lift, a CLIMB (see below), enclosed
        # THE TRAVERSE DESCENDS. Held at a constant t it is a flat canal, and flat canals do not
        # carry anything: water reaches exactly seven blocks from a source and then stops, so the
        # rider stops with it. A gentle fall keeps the flow directed for the whole run.
        (s,          s,        max(6, t - 6)),   # CORNER - the top traverse, open to the sky
        (m + 6,      s,        4),      # CORNER - THE DROP
        (m + 6,      s - run,  0),      # the run-out into the pool
    ]


def _flume(w: World, p: dict, ctx) -> dict:
    f = _Frame(p)
    pal = LANDS[p["land"]]
    seed = int(p["seed"])
    wps = _flume_plan(p)
    pts, marks = _trace(wps)
    corners = _corners(pts, False)
    _feasible(pts, marks, wps, corners, "the flume's channel")
    hs = _profile(pts, marks, wps, corners)
    n = len(pts)
    m, s, _t, half, dock, _run = _flume_dims(p)

    _apron(w, f, pal, pts, seed, radius=4)

    # The splash pool sits beside the dock, at the foot of the run-out.
    pool_i, pool_d = pts[-1][0], pts[-1][1] - 1
    pi0, pi1 = pool_i - half, pool_i + half
    pd0, pd1 = pool_d - half - 2, pool_d
    _pad(w, f, pal, pi0 - 2, pi1 + 2, pd0 - 2, pd1 + 2, seed)

    side_of = [_sides(pts, j, False) for j in range(n)]

    def nb_h(j):
        out = [hs[j]]
        if j:
            out.append(hs[j - 1])
        if j + 1 < n:
            out.append(hs[j + 1])
        return out

    # THE TROUGH. Floor, then a SINGLE centre lane of water, then side walls TWO cells out -
    # never one. At a corner `_sides` hands back the elbow's offsets un-doubled, and at
    # magnitude 1 one of those offsets is exactly the NEXT path cell - a wall built there would
    # seal the very cell the water is meant to reach next. Doubled, the wall clears every path
    # cell (which only ever sits one step away) by construction; this is why the wall loop below
    # keeps the `* 2` the floor already used.
    #
    # THE FLOOR IS A COLUMN, NOT A COURSE. Filled at one level per cell it is a diagonal
    # staircase on any graded run, and diagonal is not 6-connected - the ride would ship as one
    # fragment per flight. Filling from the LOWEST neighbour up to this cell's own level makes
    # every floor cell face-adjacent to the next by construction.
    #
    # **THE WIDE BED USES `_wall_offs`, NOT `side_of`, FOR THE SAME REASON THE WALLS DO.** A
    # corner's doubled perpendicular does not stop at "two cells out" in the abstract - along
    # either leg it lands EXACTLY on the real path cell two indices up that leg, and filling that
    # column up to the CORNER's own height buries whatever that distant cell's own water lane
    # needed to be. This is the one dry cell the wall fix on its own left standing: a corner's bed
    # entombing the drop's next source two cells down the leg, solid straight through height 24
    # where that cell wanted open water at hs+1.
    water = 0
    for j, (i, d) in enumerate(pts):
        lo, hi = min(nb_h(j)), hs[j]
        wo = _wall_offs(pts, j)
        for (oi, od) in [(0, 0)] + wo + [(o[0] * 2, o[1] * 2) for o in wo]:
            for hh in range(lo, hi + 1):
                w.put(*f.at(i + oi, d + od, hh), pal["ground"])

    # **THE HEAD OF THE CHANNEL IS A HOLE UNTIL SOMETHING CAPS IT, AND THAT ONE MISSING WALL
    # EMPTIED THE WHOLE RIDE ONTO THE PLOT.** The wall loop below builds the channel's SIDES -
    # `_sides` returns perpendiculars, and a perpendicular is by definition not the end of a
    # run. So cell 0 had open air where the trough should stop, one course above an apron that
    # is a course lower again: the launch pool poured over the lip, spread across the apron at
    # walking level and off the edge of the island. Simulated, 199,959 cells were wet and the
    # flood reached Y-1908 before the step budget cut it off, and NOTHING saw it - the design
    # audited clean, cost nothing new, and `fluids.carries` reported the ride carrying a rider
    # perfectly, because the path really was wet the whole way. `carries` and `escapes` are two
    # different questions and this ride needed both. See `_cap`.
    _cap(w, f, pal, pts, hs, 0, _wall_offs(pts, 0))
    caps = 1

    # **SPACED SOURCES, ONE LANE, AND NONE ON THE LIFT.** The first version filled every channel
    # cell with level=0 - 564 source blocks - which is STILL water: a source does not push, so
    # the ride carried nobody while looking perfect in every render. The second version spaced
    # sources by the RAW path index (`j % SRC_EVERY == 0`), which keeps counting through the
    # cells the lift skips - so the first real source after the crest could land several cells
    # into the descent with nothing behind it able to reach it (water does not flow uphill, so
    # the last source before the climb is on the far side of a dry gap it cannot cross). Measured,
    # it reached 161 cells and not one of them was flowing - AND `_seal` (below) then walled every
    # one of those sparse sources into its own sealed pocket by filling the very gaps the next
    # source needed to spread through.
    #
    # THE COUNTER NOW TRACKS CELLS SINCE THE LAST SOURCE, NOT THE RAW INDEX, and a climb always
    # resets it so the FIRST CELL AFTER THE CREST IS ALWAYS A SOURCE - the mechanical lift ends,
    # the boat is set down in fresh water, and the slide starts from there. The lift itself stays
    # dry: it is a walk-up tube, water does not flow uphill, and nothing here tries to make it.
    #
    # A source cell is where the rider FLOATS rather than moves, so it is never part of the ride
    # PATH this function reports - `path` below skips every cell this loop marks as a source.
    #
    # **THE CLIMB IS FOUND BY ITS LAST RISE, NOT ITS FIRST FLAT CELL.** `_profile` spreads a
    # leg's climb over its free cells with `int((k + 0.5) * step)` picks, and at this ride's own
    # numbers (30 courses over 31 free cells) that rounds to one cell that repeats its neighbour's
    # height in the MIDDLE of the climb - a real, if tiny, plateau one course below the crest.
    # Treating "the first non-rising cell after a rise" as the crest fired there instead, on the
    # way UP, and placed a source floating mid-shaft while the lift kept climbing past it. The
    # true crest is the LAST cell any leg rises into; everything from the first rise to the last,
    # plateau included, is the lift and stays dry.
    rises = [j for j in range(1, n) if hs[j] > hs[j - 1]]
    lift_lo, lift_hi = (rises[0], rises[-1]) if rises else (n, -1)
    descent0 = lift_hi + 1 if rises else 0     # the cell right after the crest

    since_src = SRC_EVERY               # forces a source at j == 0, the dock's own launch pool
    is_source = [False] * n
    for j, (i, d) in enumerate(pts):
        if lift_lo <= j <= lift_hi:
            since_src = SRC_EVERY       # the lift is dry; the descent starts fresh past it
            continue
        since_src += 1
        crest = bool(rises) and j == descent0
        is_last = j == n - 1
        if crest or since_src >= SRC_EVERY or is_last:
            w.put(*f.at(i, d, hs[j] + 1), "water", level="0")
            water += 1
            since_src = 0
            is_source[j] = True

    # THE EXPOSED CONTRACT: everything from the top of the first drop (the crest cell, which the
    # loop above always makes a source) through the run-out, split into the cells a rider
    # actually travels (`path`) and the cells that feed them (`sources`) - so a caller can hand
    # both straight to `fluids.carries` without re-deriving the geometry. `sequence` is the same
    # stretch with the sources left IN, in ride order - what `fluids.dry_runs` wants, since it
    # resets its own budget on every cell that IS a source rather than being handed two lists
    # that have already had the sources subtracted out of one of them.
    descent_js = [j for j in range(descent0, n)]
    sequence_world = [f.at(pts[j][0], pts[j][1], hs[j] + 1) for j in descent_js]
    path_world = [f.at(pts[j][0], pts[j][1], hs[j] + 1) for j in descent_js if not is_source[j]]
    sources_world = [f.at(pts[j][0], pts[j][1], hs[j] + 1) for j in descent_js if is_source[j]]

    # THE WALLS, at twice the perpendicular offset, three courses over the floor. On the graded
    # sections - the lift and the drop, which is the whole ride - the two water courses are
    # GLAZED, because a graded channel has to be roofed (see the module docstring) and a roofed
    # ride you cannot see into is a corridor.
    graded = {j for j in range(n) if len(set(nb_h(j))) > 1}
    panes = 0
    for j, (i, d) in enumerate(pts):
        nxt = pts[j + 1] if j + 1 < n else pts[j - 1]
        for (oi, od) in [(o[0] * 2, o[1] * 2) for o in _wall_offs(pts, j)]:
            for hh in range(hs[j] + 1, hs[j] + 4):
                pos = f.at(i + oi, d + od, hh)
                if w.has(*pos):
                    continue
                if j in graded and hh <= hs[j] + 2:
                    wx0, _wy, wz0 = f.at(i, d, hh)
                    wx1, _wy1, wz1 = f.at(nxt[0], nxt[1], hh)
                    along = _DIRS.get((max(-1, min(1, wx1 - wx0)),
                                       max(-1, min(1, wz1 - wz0))), "north")
                    _pane_run(w, f, pal, i + oi, d + od, hh, along)
                    panes += 1
                else:
                    w.put(*pos, pal["trim"] if hh == hs[j] + 3 else pal["wall"])

    # THE ROOF, AND ONLY WHERE THE GEOMETRY DEMANDS ONE. A cell whose neighbour's water stands
    # higher than its own has an exposed vertical face, and an exposed face beside a source is a
    # leak. Filling exactly those courses leaves every flat run OPEN to the sky and turns the
    # lift and the drop into tubes - which is the honest answer, not a compromise.
    roofed = 0
    for j, (i, d) in enumerate(pts):
        want = max(nb_h(j)) + 2
        wo = _wall_offs(pts, j)
        for hh in range(hs[j] + 3, want + 1):
            for (oi, od) in [(0, 0)] + wo + [(o[0] * 2, o[1] * 2) for o in wo]:
                pos = f.at(i + oi, d + od, hh)
                if not w.has(*pos):
                    w.put(*pos, pal["trim"])
                    roofed += 1

    # TRESTLES under the trough's own edges.
    trestles = 0
    every = max(2, int(p["trestle_every"]))
    for j, (i, d) in enumerate(pts):
        deck = min(nb_h(j))
        if deck < 1:
            continue
        if not (j % every == 0 or j in corners):
            continue
        style = int(hash01(j, seed, 23) * 3)
        offs = [(o[0] * 2, o[1] * 2) for o in side_of[j][:2]]
        _trestle(w, f, pal, i, d, deck, offs, style, seed)
        trestles += 1

    # GANTRY ARCHES over the lift, standing on the trough's own walls. They are what stops a
    # thirty-course tube reading as a pipe, and they are varied: every third one carries a light.
    gantry = 0
    gap = max(3, int(p["gantry_every"]))
    for j, (i, d) in enumerate(pts):
        if j not in graded or j % gap or hs[j] < 3:
            continue
        offs = [(o[0] * 2, o[1] * 2) for o in side_of[j][:2]]
        # AT LEAST ONE POST COURSE, ALWAYS. At a local peak of the grade the roof stops a course
        # lower, the post range came out empty, and the beam over it shipped as a floating plank
        # - 63 of them, and every one looked like a brace.
        head = max(max(nb_h(j)) + 3, hs[j] + 4)
        for (oi, od) in offs:
            for hh in range(hs[j] + 4, head + 1):
                w.put(*f.at(i + oi, d + od, hh), pal["post"])
        for oi in range(-2, 3):
            o = side_of[j][0]
            w.put(*f.at(i + o[0] * oi, d + o[1] * oi, head + 1), pal["beam"])
        if gantry % 3 == 0:
            o = side_of[j][0]
            w.put(*f.at(i + o[0] * 2, d + o[1] * 2, head), pal["light"],
                  hanging="true", waterlogged="false")
        gantry += 1

    # THE SPLASH POOL: a basin on the apron, its water level continuous with the run-out's, so
    # the last channel cell empties into it rather than over it.
    end_h = hs[-1]
    for i in range(pi0, pi1 + 1):
        for d in range(pd0, pd1 + 1):
            w.put(*f.at(i, d, end_h), pal["ground"])
            for hh in (end_h + 1, end_h + 2):
                w.put(*f.at(i, d, hh), "water", level="0")
                water += 1
    # A DRESSED RIM, one course over the water, with the stair coping the corpus says we under-use.
    rim = 0
    for i in range(pi0 - 1, pi1 + 2):
        for d in range(pd0 - 1, pd1 + 2):
            edge = i in (pi0 - 1, pi1 + 1) or d in (pd0 - 1, pd1 + 1)
            if not edge:
                continue
            for hh in range(end_h, end_h + 3):
                if not w.has(*f.at(i, d, hh)):
                    w.put(*f.at(i, d, hh), pal["wall"] if hh < end_h + 2 else pal["trim"])
            rim += 1

    # THE DOCK: a platform beside the still water at the start, a canopy, and its name.
    # THE DOCK BUILDING ENDS WHERE THE PLAN'S DOCK RUN ENDS. Pinned at `m + 7` while the plan's
    # own dock run shrinks with the span, the building would stand over the climbing channel.
    dock_i0, dock_i1, dock_d = m, m + dock, m + 2
    a, b = pal["canopy"]
    for i in range(dock_i0, dock_i1 + 1):
        for d in range(dock_d + 3, dock_d + 7):
            w.put(*f.at(i, d, 0), pal["ground"] if (i + d) % 2 else pal["path"])
        for h in range(1, 5):
            w.put(*f.at(i, dock_d + 7, h), pal["wall"])
    for i in (dock_i0, dock_i1):
        for h in range(0, 5):
            w.put(*f.at(i, dock_d + 3, h), pal["post"])
            w.put(*f.at(i, dock_d + 7, h), pal["post"])
    for i in range(dock_i0 - 1, dock_i1 + 2):
        for d in range(dock_d + 2, dock_d + 9):
            w.put(*f.at(i, d, 5), a if (i + d) % 2 == 0 else b)
    if dock_i1 - dock_i0 + 3 >= int(p["min_run"]):
        for i in range(dock_i0 - 1, dock_i1 + 2):
            w.put(*f.at(i, dock_d + 9, 5), pal["stair"], facing=_LEAN[f.back],
                  half="top", shape="straight", waterlogged="false")
    w.put(*f.at((dock_i0 + dock_i1) // 2, dock_d + 5, 4), pal["light"],
          hanging="true", waterlogged="false")

    title = str(p.get("title") or "FLUME").upper()[:SIGN_WIDTH]
    signed = 0
    signed += _sign(w, f, pal, (dock_i0 + dock_i1) // 2, dock_d + 8, 3, f.back,
                    [title, "", "you will get", "wet"])
    signed += _sign(w, f, pal, (dock_i0 + dock_i1) // 2, dock_d + 6, 2, f.facing,
                    ["BOARDING", "one to a boat", "hold the bar", ""])

    # **THE ENVELOPE: EVERY CELL THIS RIDE IS WILLING FOR WATER TO BE IN.** The three bed lanes
    # of each path cell, from the water course up to the wall top, plus the pool's two courses.
    # It is stated as geometry rather than as a bounding box on purpose - a box round a flume
    # contains the apron it spilled onto, and would have passed the shipped build.
    #
    # **THE LIFT IS WET, AND SAYING OTHERWISE WAS THE SECOND HALF OF THE LEAK.** The note here
    # used to call it "a walk-up tube - water does not flow uphill, and nothing here tries to
    # make it". Nothing has to: the crest source sits at the top of a staircase that descends in
    # BOTH directions, so it runs back down the lift exactly as it runs down the drop, a fall per
    # step resetting the seven-block budget every time. No source is placed on the lift and the
    # lift fills anyway. That is correct - a real flume's chain lift runs in a wet trough - and it
    # is contained. The envelope says so out loud instead of a comment claiming a dryness the
    # physics never had.
    envelope = set()
    for j, (i, d) in enumerate(pts):
        # FROM THIS CELL'S OWN WATER COURSE UP TO ONE OVER THE HIGHEST NEIGHBOUR. Water arriving
        # from a higher cell crosses at ITS level and falls here, so the column between the two is
        # reachable; anything BELOW this cell's floor belongs to the lower neighbour's own entry,
        # and claiming it here is how the shell came to bed the lane under it.
        for (oi, od) in [(0, 0)] + _wall_offs(pts, j):
            for hh in range(hs[j] + 1, max(nb_h(j)) + 2):
                envelope.add(f.at(i + oi, d + od, hh))
    for i in range(pi0, pi1 + 1):
        for d in range(pd0, pd1 + 1):
            for hh in (end_h + 1, end_h + 2):
                envelope.add(f.at(i, d, hh))
    shelled = _shell(w, pal, envelope)

    sealed = _seal(w, pal["ground"])

    # **VERIFY IT AT GENERATION TIME, THE SAME RULE `_feasible` ALREADY FOLLOWS FOR THE RAIL.**
    # A flume that looks like a water ride and does not carry anyone is this project's cardinal
    # sin, and it shipped once already: 564 source blocks, every one still water, invisible in
    # every render and the audit. `fluids.carries` is cheap (a flood fill over a few hundred
    # cells) and it runs on the SAME `w.cells` the printer will place, so a channel that cannot
    # carry a rider fails here, in the generator, instead of in the world an hour later.
    cells = {pos: name for pos, (name, _props) in w.cells.items()}
    report = fluids.carries(cells, path_world, sources_world)
    if not report["carries"]:
        raise ValueError(
            f"the flume's channel does not carry a rider: {report['dry']} dry cell(s), "
            f"{report['still']} still cell(s) of {report['cells']}, stops at "
            f"{report['stops_at']}")

    # **AND THEN ASK THE OTHER QUESTION.** `carries` walks the PATH; it has nothing to say about
    # the cells beside it, and the shipped flume passed it while draining onto the plot.
    all_sources = [pos for pos, (name, pr) in w.cells.items()
                   if name == "water" and pr.get("level", "0") == "0"]
    out = fluids.escapes(cells, all_sources, envelope)
    if out:
        raise ValueError(
            f"the flume leaks: water reaches {len(out)} cell(s) outside its own trough and "
            f"pool, the first at {out[0]}. A channel end with no cap drains the whole ride.")
    stranded = fluids.unenclosed(cells, allow=envelope)
    if stranded:
        raise ValueError(f"{len(stranded)} water cell(s) are not enclosed: {stranded[:3]}")

    return {
        "kind": "flume",
        "channel": n, "corners": len(corners), "water": water, "panes": panes,
        "roof_cells": roofed, "trestles": trestles, "gantries": gantry,
        "pool": (pi1 - pi0 + 1) * (pd1 - pd0 + 1), "rim": rim, "sealed": sealed,
        "caps": caps, "shelled": shelled,
        # THE WET ENVELOPE, in world coordinates: every cell this ride is willing for water to be
        # in. A caller re-checking a regenerated build hands it straight to `fluids.escapes`
        # rather than re-deriving a trough from a bounding box, which is what would have passed
        # the leaking version.
        "basin": [list(c) for c in sorted(envelope)],
        "signs": signed, "top": int(p["flume_top"]), "span": s,
        # THE GENERATOR'S OWN GEOMETRY, WORLD COORDINATES, so a caller (a test, `fluids.carries`
        # again after a regen, `look.py`) never has to re-derive the channel to check it. `path`
        # is what a rider travels; `sources` is what feeds it - a source cell is still water and
        # is deliberately NOT in `path`, because a rider floats there rather than moving.
        "path": [list(c) for c in path_world],
        "sources": [list(c) for c in sources_world],
        "sequence": [list(c) for c in sequence_world],
        "flow": {k: v for k, v in report.items() if k != "levels"},
        "contract": "a one-way water ride whose channel is FLOWING water and whose water STAYS "
                    "IN IT, both verified at generation time: `fluids.carries` for the ride "
                    "path, and `fluids.escapes` against the declared basin for containment - "
                    "two different questions, and the shipped version passed the first while "
                    "draining the whole ride onto the plot through an uncapped channel head and "
                    "two unfilled corner diagonals.",
        "unverified": ["nothing about a BOAT has been simulated - `fluids.carries` proves the "
                       "water itself is flowing end to end, not that an entity riding it stays "
                       "with the current. Ride it once before anyone is told it completes."],
    }


def _seal(w: World, mat: str) -> int:
    """The backstop: any water cell with nothing solid UNDER it is given a bed.

    ONLY UNDER - NEVER SIDEWAYS. The first version filled all four horizontal neighbours as well
    as the one below, on the reasoning that an unsealed face is a leak. It is also exactly how a
    channel of spaced sources gets walled into a row of sealed pockets: the cell between two
    sources is deliberately left open so the game can fill it with flowing water, and a backstop
    that cannot tell "open by design" from "open by accident" fills both the same way. Measured
    after the fix, every source's forward and backward neighbour is already open by construction
    (the floor is a solid column and the walls sit two cells clear of the centre lane - see
    `_flume`), so the only genuine leak risk left is a water cell with no bed, which this still
    catches. Nothing already placed is overwritten."""
    n = 0
    for (x, y, z), (name, _props) in list(w.cells.items()):
        if name != "water":
            continue
        below = (x, y - 1, z)
        if not w.has(*below):
            w.put(*below, mat)
            n += 1
    return n


# --------------------------------------------------------------------------- the rapids
#
# **THE LOG FLUME IS REPLACED, NOT REPAIRED, AND THE HEADROOM WAS THE SMALLER OF ITS TWO FAULTS.**
#
# Measured off the shipped `out/Log Flume.litematic`, 137 water cells:
#
#     3 courses clear over the water   130
#     1 course  clear                    4      the roof, at water+2 on a graded run
#     0 courses clear                    3      a gantry beam, and the roof at water+1
#
# A player is two blocks tall, so seven cells of that ride are a wall you swim into. That alone is
# a two-line fix - the roof sits at `max(neighbour) + 2` and the highest water a column can hold is
# `max(neighbour) + 1`, so the ceiling lands one course over the water by arithmetic. Move it two
# and every cell clears.
#
# **THE FAULT THAT CANNOT BE FIXED BY GEOMETRY IS THAT THERE IS NO WAY TO THE TOP.** A flume is a
# LIFT HILL and a drop, and vanilla has no chain lift: nothing carries a boat or a player UP a
# water channel. `_flume`'s own docstring records what actually happens - *"the crest source sits
# at the top of a staircase that descends in BOTH directions, so it runs back down the lift exactly
# as it runs down the drop"* - which is to say the lift is twenty courses of water flowing
# downhill AT the rider. Fixing the ceiling would have shipped a ride nobody can start, which is
# this project's cardinal sin wearing a taller hat.
#
# **THE ONLY VANILLA MECHANISM THAT RAISES A PLAYER THROUGH WATER IS A SOUL-SAND BUBBLE COLUMN,
# AND IT WAS BUILT HERE AND THEN TAKEN OUT AGAIN.** A water column standing above the surrounding
# water line has to be sealed on every side above that line or it drains, so its only opening is
# ONE COURSE TALL, at the water, and you swim through it. `bigwheel.py` accepted exactly that and
# wrote the reason down - *"a water shaft cannot have a door... you go in from BELOW"*. A
# one-course gap is a cell a player cannot stand in, so no flood fill can prove you get aboard,
# and this brief asks for that proof. The bubble lift is the right mechanism for a wheel, whose
# rider is already in the water; it is the wrong one for a ride you queue for.
#
# **A REAL WATER SLIDE'S LIFT IS A STAIRCASE.** It is walkable, provable, needs no exotic block,
# and it puts the queue where a queue belongs. So the water feature the frontier keeps is a RAPIDS
# CIRCUIT: a stair tower up to a start box at the head of a wide open channel, and a long gentle
# descent all the way round the plot into a splash pool you climb out of beside the tower. It is
# the brief's "lazy river" and its "rapids run" being the same ride: no lift hill, no drops to
# survive, and WIDTH is the point.
#
# Four things follow, and each is asserted rather than hoped for:
#
#   HEADROOM IS A PROPERTY OF THE ENVELOPE, NOT OF A ROOF. The channel declares `_HEADROOM` clear
#   courses over the deepest water any column can hold, `_shell` walls the outside of THAT, and so
#   the ceiling is two courses clear by construction instead of by a separate roofing pass whose
#   arithmetic nobody rechecked. Nothing is roofed at all: an open channel needs no lid when its
#   walls out-top its own water.
#
#   THE DESCENT IS THE FLOW. Falling water is level 8 and spreads again from where it lands, so
#   every step down restarts the seven-block budget - which means ONE source, in the start box,
#   feeds the entire ride. `_MAX_FLAT` is the rule that keeps it true, and the grade is checked
#   against it before a block is placed. The flume needed a source every six cells and shipped
#   193 of them for a player to place by hand; the channel here needs one.
#
#   A CORNER IS NOT FROZEN HERE. `_profile` holds a corner and both its neighbours at one height
#   because a curved rail has no ascending shape - a registry fact about RAILS. Water has no such
#   rule, and inheriting the rail's constraint is what pushed the flat runs past seven cells and
#   dried the channel out on the first attempt.
#
#   YOU CAN GET IN AND OUT ON FOOT, and `mcbuild/walk.py` proves it from real ground rather than
#   the geometry looking about right.

_RAPIDS_M = 3               # the channel's inset from the frame origin
_HEADROOM = 2               # CLEAR COURSES OVER THE DEEPEST WATER. A PLAYER IS TWO BLOCKS TALL.
_MAX_FLAT = 5               # cells a run may stay level: water reaches 7 from a fall, so 6 is the
                            # true ceiling and 5 leaves the margin the corner freeze once ate
_POOL_TOP = 1 + _HEADROOM   # courses the basin declares: its surface, the course water spreading
                            # in off the outfall stands at, and the headroom over THAT


def _tower_side(top):
    """The stair tower's footprint: big enough that one turn of its perimeter carries the climb.

    A spiral that wraps would put a tread back over a tread sixteen courses down - legal, but it
    is also the only way this shape can eat its own headroom, so it is sized out of existence
    rather than guarded against.
    """
    side = 5
    while 4 * (side - 1) < top + 2:
        side += 1
    return side


def _rapids_dims(p):
    """The circuit's own lengths, derived once so the plan and the buildings cannot disagree.

    The pool is deliberately NOT square with the plot: it is pushed to the low-`i` side, clear of
    the channel's own elevated head, so that no trestle leg ever comes down through the water you
    board in.
    """
    m = _RAPIDS_M
    s = int(p["rapids_span"])
    t = int(p["rapids_top"])
    wide = max(4, min(6, int(p["pool"])))
    if t < 6:
        raise ValueError(f"rapids_top is {t}; a climb under 6 courses is not a ride")
    tside = _tower_side(t)
    need = 2 * m + tside + 12
    if s < need:
        raise ValueError(f"rapids_span {s} cannot close a circuit round a {tside}-wide stair "
                         f"tower; it needs at least {need}")
    pool = (m + 1 - wide, m + 1, m - 3, m + 6)
    return m, s, t, wide, pool, tside


def _rapids_plan(p):
    """The channel's turns, in (i, d): a closed rectangle back over the pool it started above.

    The head sits one cell off the tower's top landing, so you step off the stairs straight into
    the start box. The tail comes back down the low-`i` side and ends IN the splash pool, which
    makes the whole thing a circuit you can ride again without leaving the water.
    """
    m, s, _t, _wide, _pool, tside = _rapids_dims(p)
    return [(m + 3 + tside, m), (s - m, m), (s - m, s - m), (m, s - m), (m, m + 5)]


def _rapids_grade(pts, top):
    """A height per cell: single-course steps from `top` down to the pool's own floor at -1.

    **NO CORNER IS FROZEN**, and that is the difference between this and `_profile`. The rail rule
    exists because a curved rail has no ascending shape; a corner of a water channel is just a
    corner. Freezing them clustered the flat cells at the bends, and a flat run of seven is a DRY
    CELL - water reaches exactly seven blocks from where it last fell, and the eighth is where the
    rider stops. The spacing is checked here rather than discovered by `fluids.carries` later,
    because a failure that names the dimension at fault beats one that names a coordinate.
    """
    n = len(pts)
    drops = top + 1                              # the bed ends a course under the walking level
    if drops >= n:
        raise ValueError(f"a {drops}-course descent cannot be spread over {n} cells")
    step = (n - 1) / float(drops)
    picks = set()
    for k in range(drops):
        j = 1 + int(k * step)
        while j in picks:
            j += 1
        picks.add(j)
    hs, cur, flat = [], top, 0
    for j in range(n):
        if j in picks:
            cur -= 1
            flat = 0
        else:
            flat += 1
            if flat > _MAX_FLAT:
                raise ValueError(
                    f"the rapids run level for {flat} cells at index {j}; water reaches seven "
                    f"blocks from a fall, so anything past {_MAX_FLAT} risks a dry cell. Raise "
                    f"rapids_top or lower rapids_span.")
        hs.append(cur)
    if hs[-1] != -1:
        raise ValueError(f"the channel ends at h={hs[-1]}, not in the pool at -1")
    return hs


def _perimeter(i0, i1, d0, d1):
    """The ring of a rectangle, in walking order - each cell face-adjacent to the next."""
    out = [(i, d0) for i in range(i0, i1)]
    out += [(i1, d) for d in range(d0, d1)]
    out += [(i, d1) for i in range(i1, i0, -1)]
    out += [(i0, d) for d in range(d1, d0, -1)]
    return out


def _rapids(w: World, p: dict, ctx) -> dict:
    f = _Frame(p)
    pal = LANDS[p["land"]]
    seed = int(p["seed"])
    m, s, t, _wide, (pi0, pi1, pd0, pd1), tside = _rapids_dims(p)
    pts, _marks = _trace(_rapids_plan(p))
    corners = _corners(pts, False)
    hs = _rapids_grade(pts, t)
    n = len(pts)

    def nb_h(j):
        out = [hs[j]]
        if j:
            out.append(hs[j - 1])
        if j + 1 < n:
            out.append(hs[j + 1])
        return out

    def in_pool(i, d):
        return pi0 <= i <= pi1 and pd0 <= d <= pd1

    wall_offs = [_wall_offs(pts, j) for j in range(n)]
    # THE TOP OF EACH COLUMN'S ENVELOPE, and the window is the point.
    #
    # **WATER SPREADS SIDEWAYS AT WHATEVER COURSE IT ARRIVES AT, NOT ONLY AT ITS OWN SURFACE.**
    # `fluids.spread` falls first and spreads second - so a cell whose lower neighbour is ALREADY
    # wet keeps travelling horizontally instead of dropping, and the water in a column stands as
    # high as the highest surface within reach UPSTREAM of it, not as high as its own neighbours.
    # Sized off the neighbours alone, thirty-two cells came out with a lid one course over the
    # water: the log flume's own fault, arrived at from a different direction. Water dies seven
    # blocks from where it last fell, so seven cells upstream is the honest window, and the
    # `+ _HEADROOM` on top of it is what makes the clearance arithmetic rather than inspection.
    env_top = [max(hs[max(0, j - fluids.MAX_LEVEL):j + 2]) + 1 + _HEADROOM for j in range(n)]
    # AND THE WALL GOES A COURSE HIGHER THAN THE ENVELOPE WHERE ITS NEIGHBOUR'S DOES. `env_top`
    # steps down along the run, so `_shell` lays a one-course lid across the lane triple wherever
    # the upstream column's envelope reaches above this one's. That lid is harmless to the water -
    # it is `_HEADROOM` clear by construction - and it hangs in mid-air unless the wall beside it
    # is there to hold it, which is twenty-four fragments in nine pieces. Built to the
    # neighbourhood's own maximum, the wall is always there.
    wall_top = [max(env_top[max(0, j - 1):j + 2]) for j in range(n)]
    # THE LANES A RIDER TRAVELS: the centre and one cell either side. Three wide, which is what
    # makes it a river rather than a gutter, and it is the same set the envelope is built from so
    # the two cannot drift.
    lanes = {(i + oi, d + od) for j, (i, d) in enumerate(pts)
             for (oi, od) in [(0, 0)] + wall_offs[j]}

    # ---- the ground. A skyblock plot is void, so the ride brings its own.
    _apron(w, f, pal, pts, seed, radius=3)
    _pad(w, f, pal, pi0 - 4, m + 4 + tside, pd0 - 7, pd1 + 4, seed)

    # ---- THE BED. A COLUMN, NOT A COURSE: filled from the lowest neighbour's level up to this
    # cell's own, so every floor cell is face-adjacent to the next on a graded run. Filled one
    # level per cell it is a diagonal staircase, and diagonal is not 6-connected.
    for j, (i, d) in enumerate(pts):
        lo, hi = min(nb_h(j)), hs[j]
        wo = wall_offs[j]
        for (oi, od) in [(0, 0)] + wo + [(o[0] * 2, o[1] * 2) for o in wo]:
            for hh in range(lo, hi + 1):
                w.put(*f.at(i + oi, d + od, hh), pal["ground"])

    # ---- THE TROUGH'S OWN WALLS, BUILT AS COLUMNS AND NOT LEFT TO THE BACKSTOP. `_shell` fills
    # whatever gap it finds beside the envelope, cell by cell, and carries a plug down only six
    # courses before giving up - which on a channel twenty courses in the air leaves the wall as
    # a scatter of fragments hanging beside the water. Forty of them, in twelve pieces. Drawn here
    # as a column from the bed's own footing up to the top of the envelope, every wall cell stands
    # on the one below it and the shell has nothing left to invent.
    #
    # THE CORNER'S OUTER DIAGONAL IS PART OF THE WALL. `_wall_offs` hands back a corner's two
    # perpendiculars and nothing at all for the cell diagonally between them, which has neither
    # bed nor wall - and that is the hole the whole ride once drained through.
    for j, (i, d) in enumerate(pts):
        wo = wall_offs[j]
        offs = [(o[0] * 2, o[1] * 2) for o in wo]
        # ONLY AT A REAL CORNER, AND ONLY ACROSS TWO AXES. A straight cell's two perpendiculars
        # are opposite ends of ONE axis, so combining them yields (0, 0) - the centre lane - and
        # walling that seals the channel at every cell: 59 of 59 dry, which is at least a failure
        # nobody could miss.
        if j in corners and len(wo) > 1 and wo[0][0] * wo[1][0] + wo[0][1] * wo[1][1] == 0:
            (ai, ad), (bi_, bd) = wo[0], wo[1]
            offs += [(ai * q + bi_ * r, ad * q + bd * r) for q in (1, 2) for r in (1, 2)]
        for (oi, od) in offs:
            for hh in range(min(nb_h(j)), wall_top[j] + 1):
                if not w.has(*f.at(i + oi, d + od, hh)):
                    w.put(*f.at(i + oi, d + od, hh),
                          pal["trim"] if hh == wall_top[j] else pal["wall"])

    # ---- what carries the bed. A low channel gets a solid bank; a high one gets a trestle.
    every = max(2, int(p["trestle_every"]))
    trestles = 0
    for j, (i, d) in enumerate(pts):
        deck = min(nb_h(j))
        if deck < 1 or in_pool(i, d):
            continue
        wo = wall_offs[j]
        offs = [(o[0] * 2, o[1] * 2) for o in wo]
        if deck <= 3:
            for (oi, od) in [(0, 0)] + wo + offs:
                if in_pool(i + oi, d + od):
                    continue
                for hh in range(0, deck):
                    if not w.has(*f.at(i + oi, d + od, hh)):
                        w.put(*f.at(i + oi, d + od, hh), pal["ground"])
        elif j % every == 0 or j in corners:
            _trestle(w, f, pal, i, d, deck, offs, int(hash01(j, seed, 23) * 3), seed)
            trestles += 1

    # ---- THE STAIR TOWER, and it is the whole reason this ride replaced the flume.
    #
    # **VANILLA HAS NO CHAIN LIFT AND ONLY ONE MECHANISM THAT RAISES A PLAYER THROUGH WATER - A
    # SOUL-SAND BUBBLE COLUMN - AND A BUBBLE COLUMN CANNOT BE WALKED INTO.** A water column
    # standing above the surrounding water line has to be sealed on every side above that line or
    # it drains, so its only opening is one course tall at the water and you SWIM through it.
    # `bigwheel.py` accepted exactly that and wrote the reason down: *"a water shaft cannot have a
    # door... you go in from BELOW"*. A one-course gap is a cell a player cannot stand in, so no
    # flood fill can prove you get aboard, and the brief asks for that proof.
    #
    # A real water slide's lift is a STAIRCASE. It is walkable, provable, needs no exotic block,
    # and it puts the queue where a queue belongs. So the tower is a solid core with a single
    # helical flight wrapped round it, sized so one turn carries the whole climb, ending on a
    # landing whose top course is level with the start box's own water - you step DOWN one course
    # into the channel, which is a step `walk.py` takes and which keeps the water walled by the
    # landing rather than spilling over it.
    # **THE FLIGHT MAY NOT END AGAINST THE TROUGH.** `_shell` walls every cell beside the start
    # box's water, so a landing taken on the tower's own east face put the step BEFORE it under
    # that wall - a tread with no headroom, fourteen courses up, and the only symptom was a walk
    # that would not complete. The tower stands a cell clear and a BRIDGE spans the gap: solid, so
    # it is the wall the shell wanted, and walkable, so it is the way in.
    ti0, ti1 = m + 2, m + 1 + tside
    td0, td1 = m - 2, m - 3 + tside
    landing = (ti1, m)
    bridge = (ti1 + 1, m)
    perim = _perimeter(ti0, ti1, td0, td1)
    if landing not in perim:
        raise ValueError(f"the tower's landing {landing} is not on its own stair")
    start = (perim.index(landing) - (t + 1)) % len(perim)
    # THE LANDING'S TOP COURSE MUST BE THE START BOX'S OWN WATER COURSE. Numbered from -1 - the
    # apron - instead of from 0, the whole flight came out a course short, the landing stood at
    # `top` where the water is at `top + 1`, and the start box poured straight over it and off the
    # plot: 193,763 wet cells. One index, and every other check passed.
    treads = [(perim[(start + k) % len(perim)], k) for k in range(t + 2)]
    for (i, d) in {c for c, _h in treads}:
        top_h = max(h for c, h in treads if c == (i, d))
        for hh in range(-1, top_h + 1):
            w.put(*f.at(i, d, hh), pal["ground"])
    for k, ((i, d), h) in enumerate(treads[:-1]):
        # **A TREAD FACES THE CELL IT CLIMBS INTO, NOT THE ONE IT CAME FROM.** A flight that
        # ascends toward D has every tread facing=D - the convention `test_stairhead` pins - and
        # on a spiral D changes every cell, so taking the direction from the PREVIOUS tread puts
        # every riser one step behind and the whole flight faces the wrong way. Our renderer draws
        # a stair facing either way identically, so this is asserted and never eyeballed. The
        # landing is left a full block: it is where you step off, not a tread.
        (ni, nd) = treads[k + 1][0]
        x0, _y, z0 = f.at(i, d, 0)
        x1, _y1, z1 = f.at(ni, nd, 0)
        up = _DIRS.get((max(-1, min(1, x1 - x0)), max(-1, min(1, z1 - z0))))
        if up:
            w.put(*f.at(i, d, h), pal["stair"], facing=up, half="bottom",
                  shape="straight", waterlogged="false")
    w.put(*f.at(bridge[0], bridge[1], t + 1), pal["ground"])
    # WHERE A CLIMBER'S HEAD GOES. Two clear courses over every tread and over the bridge, handed
    # to `_shell` as cells it may not fill - see its docstring for why these are not envelope.
    keep = {f.at(i, d, h + k) for (i, d), h in treads for k in range(1, _HEADROOM + 1)}
    keep |= {f.at(bridge[0], bridge[1], t + 1 + k) for k in range(1, _HEADROOM + 1)}
    core_top = max(h for _c, h in treads)
    for i in range(ti0 + 1, ti1):
        for d in range(td0 + 1, td1):
            for hh in range(-1, core_top + 1):
                w.put(*f.at(i, d, hh), pal["post"] if hh % 5 == 0 else pal["wall"])
    w.put(*f.at((ti0 + ti1) // 2, (td0 + td1) // 2, core_top + 1), pal["light"],
          hanging="false", waterlogged="false")

    # ---- THE POOL, and its SHORE, which is three courses of step and not a decision anyone is
    # free to skip. `_shell` walls one ring outside whatever the water is allowed to occupy, and
    # what the water is allowed to occupy has to include the clear courses over it (see the
    # envelope below) - so the quay stands three courses proud of the surface by construction. A
    # three-course wall is a three-course climb and a flood fill steps ONE, so the slipway is the
    # answer: a trench of step INSIDE the basin, level with the quay at the top and with the
    # water at the bottom, so the whole walk in is single courses.
    #
    # A lane cell never holds water here: a lane holding a SOURCE is a cell where the rider floats
    # and stops, which is the fault `fluids.carries` was written to catch and the one that
    # withdrew the first flume.
    for i in range(pi0, pi1 + 1):
        for d in range(pd0, pd1 + 1):
            if not w.has(*f.at(i, d, -1)):
                w.put(*f.at(i, d, -1), pal["ground"])
    # **THE SLIPWAY IS A TRENCH WITH SOLID SIDES, AND THE SIDES ARE THE WHOLE TRICK.** `_shell`
    # walls every non-envelope neighbour of every open envelope cell, at every course - so any
    # walkable cell beside the basin gets a block on its head, and declaring that cell open just
    # moves the wall one ring out, onto the next cell of the approach. Chased, it never
    # terminates. Flanked by masonry it terminates immediately: each step's clear courses have
    # nothing but solid blocks and other envelope cells beside them, so no wall is generated at
    # all, and the descent is three ordinary one-course steps from the quay to the water.
    bi = m - 1
    slip = {(bi, pd0 + k): _POOL_TOP - 1 - k for k in range(_POOL_TOP)}
    flank = [(bi + k, pd0 + q) for k in (-1, 1) for q in range(-1, _POOL_TOP)]
    flank += [(bi, pd0 - 1)]
    for (i, d) in flank:
        for hh in range(-1, _POOL_TOP + 1):
            w.put(*f.at(i, d, hh), pal["trim"] if hh == _POOL_TOP else pal["path"])
    for (i, d), tp in slip.items():
        for hh in range(-1, tp + 1):
            # A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D. The slipway climbs OUT
            # of the pool, which is toward the frontage - written the other way round it is a
            # flight you cannot walk up, and our renderer draws both identically.
            w.put(*f.at(i, d, hh), pal["stair"] if hh == tp else pal["path"],
                  **({"facing": f.facing, "half": "bottom", "shape": "straight",
                      "waterlogged": "false"} if hh == tp else {}))
    pool_wet = []
    for i in range(pi0, pi1 + 1):
        for d in range(pd0, pd1 + 1):
            if (i, d) in lanes or (i, d) in slip or w.has(*f.at(i, d, 0)):
                continue
            w.put(*f.at(i, d, 0), "water", level="0")
            pool_wet.append(f.at(i, d, 0))

    # ---- THE START BOX. One source, at the head of the channel, and it is the ONLY one the ride
    # needs: falling water is level 8 and spreads again from where it lands, so every step down
    # restarts the seven-block budget and one source feeds sixty cells. The flume needed a source
    # every six cells and shipped 193 for a player to place by hand.
    head = f.at(pts[0][0], pts[0][1], hs[0] + 1)
    w.put(*head, "water", level="0")

    # ---- THE ENVELOPE: every cell this ride is willing for water to be in, PLUS the clear
    # courses a body needs over it. Nothing is roofed; `_shell` walls the OUTSIDE of this.
    #
    # **THE `+ _HEADROOM` IS THE WHOLE FIX, AND WITHOUT IT THIS SHIPPED THE FLUME'S OWN BUG.**
    # Stopped at the deepest water a column can hold, cell j's envelope tops at `max(nb) + 1` -
    # and its UPHILL neighbour's tops one course higher, because that neighbour's own window sees
    # a cell higher again. `_shell` then walls j's column at that course: a lid one block over the
    # water, on every cell below a drop. Measured, that is exactly the log flume's four
    # one-course-clear cells, arrived at from a different direction. Adding the headroom to the
    # envelope makes the first walled course `max(nb) + 2 + _HEADROOM` while the deepest water is
    # `max(nb) + 1`, so the clearance is `_HEADROOM` by arithmetic instead of by inspection.
    #
    # The basin follows the SAME rule for the same reason: a pool declared one course deep has its
    # own surface walled wherever the channel's taller envelope runs beside it.
    envelope = set()
    for j, (i, d) in enumerate(pts):
        for (oi, od) in [(0, 0)] + wall_offs[j]:
            for hh in range(hs[j] + 1, env_top[j] + 1):
                envelope.add(f.at(i + oi, d + od, hh))
    for pos in pool_wet:
        for k in range(_POOL_TOP + 1):
            envelope.add((pos[0], pos[1] + k, pos[2]))
    for (i, d), tp in slip.items():
        for hh in range(tp + 1, _POOL_TOP + 1):
            envelope.add(f.at(i, d, hh))
    envelope.add(head)
    sources_world = sorted(set(pool_wet) | {head})

    # ---- CONTAINMENT, from the envelope rather than from the water. A backstop working off water
    # blocks cannot tell "open by design" from "open by accident"; working off the envelope it can.
    shelled = _shell(w, pal, envelope, keep)

    # ---- DRESSING. A fence along the trough's top rail, and a lantern on it now and then. It is
    # placed AFTER containment and never inside the envelope, so it cannot become the lid the
    # whole design exists to avoid - a rail sited by arithmetic instead took thirty-two cells'
    # headroom the first time.
    lights = 0
    for j, (i, d) in enumerate(pts):
        if j % 3:
            continue
        for (oi, od) in [(o[0] * 2, o[1] * 2) for o in wall_offs[j]]:
            top_h = None
            for hh in range(max(nb_h(j)) + 3 + _HEADROOM, hs[j] - 1, -1):
                if w.has(*f.at(i + oi, d + od, hh)):
                    top_h = hh
                    break
            if top_h is None:
                continue
            pos = f.at(i + oi, d + od, top_h + 1)
            if pos in envelope or w.has(*pos) or w.name(*f.at(i + oi, d + od, top_h)) == "water":
                continue
            if j % 12 == 0:
                w.put(*pos, pal["light"], hanging="false", waterlogged="false")
                lights += 1
            else:
                w.put(*pos, pal["fence"], waterlogged="false",
                      north="false", south="false", east="false", west="false")

    # ---- THE TERRACE. The quay `_shell` builds is three courses; these are the three steps up to
    # the top of it, one course each, so the walk in is continuous from the apron.
    tops = {k: _POOL_TOP - k + 1 for k in range(2, _POOL_TOP + 2)}
    for i in range(pi0 - _POOL_TOP - 2, pi1 + _POOL_TOP + 3):
        for d in range(pd0 - _POOL_TOP - 2, pd1 + _POOL_TOP + 3):
            edge = max(abs(i - min(max(i, pi0), pi1)), abs(d - min(max(d, pd0), pd1)))
            if edge not in tops:
                continue
            for hh in range(-1, tops[edge]):
                pos = f.at(i, d, hh)
                if pos in envelope or w.has(*pos):
                    continue
                w.put(*pos, pal["trim"] if edge == 2 else pal["path"])

    # ---- THE GATEWAY, on the forecourt, with the ride's name and how to ride it.
    gi0, gi1, gd = pi0, pi1, pd0 - 5
    for i in (gi0, gi1):
        for hh in range(0, 4):
            if not w.has(*f.at(i, gd, hh)):
                w.put(*f.at(i, gd, hh), pal["post"])
    for i in range(gi0, gi1 + 1):
        for hh in (2, 3):
            if not w.has(*f.at(i, gd, hh)):
                w.put(*f.at(i, gd, hh), pal["wall"])
    a, b = pal["canopy"]
    for i in range(gi0 - 1, gi1 + 2):
        w.put(*f.at(i, gd, 4), a if (i + gd) % 2 == 0 else b)
    w.put(*f.at((gi0 + gi1) // 2, gd, 3), pal["light"], hanging="true", waterlogged="false")

    title = str(p.get("title") or "RAPIDS").upper()[:SIGN_WIDTH]
    signed = 0
    signed += _sign(w, f, pal, (gi0 + gi1) // 2, gd - 1, 2, f.facing,
                    [title, "", "you will get", "wet"])
    signed += _sign(w, f, pal, gi0, gd - 1, 1, f.facing,
                    ["BOARDING", "wade the pool,", "climb the tower,", "float back down"])

    cells = {pos: name for pos, (name, _props) in w.cells.items()}

    # ---- THE RIDE PATH, in world coordinates: the water lane of every channel cell after the
    # start box, in order. The box itself is the one source and is deliberately not on the path -
    # a source does not push, so a rider floats there until they let go, which is exactly what a
    # start box is for.
    path_world = [f.at(i, d, hs[j] + 1) for j, (i, d) in enumerate(pts)][1:]

    # **VERIFY IT HERE, NOT IN THE WORLD AN HOUR LATER.** Four questions, and a ride needs every
    # one answered: does the water carry a rider, does it stay in, does a BODY FIT, and can a
    # player get on and off.
    report = fluids.carries(cells, path_world, sources_world)
    if not report["carries"]:
        raise ValueError(
            f"the rapids channel does not carry a rider: {report['dry']} dry cell(s), "
            f"{report['still']} still cell(s) of {report['cells']}, stops at {report['stops_at']}")

    out = fluids.escapes(cells, sources_world, envelope)
    if out:
        raise ValueError(
            f"the rapids leak: water reaches {len(out)} cell(s) outside the channel and the pool, "
            f"the first at {out[0]}.")
    stranded = fluids.unenclosed(cells, allow=envelope)
    if stranded:
        raise ValueError(f"{len(stranded)} water cell(s) are not enclosed: {stranded[:3]}")

    # **CHECKED OVER EVERY CELL THE WATER REACHES, NOT OVER THE BLOCKS THAT SHIP.** A design emits
    # SOURCES; the flowing water that fills the channel is computed by the game, so a check that
    # walks `w.cells` for `water` inspects sixty-five cells and misses the sixty a rider is
    # actually carried through - which is exactly where a lid lands.
    wet_cells = set(fluids.spread(cells, sources_world))
    tight = [c for c in sorted(wet_cells) if _clear_over(w, c) < _HEADROOM]
    if tight:
        raise ValueError(
            f"{len(tight)} water cell(s) have less than {_HEADROOM} clear courses over them, the "
            f"first at {tight[0]} - a player is two blocks tall and stops there. This is the "
            f"fault that withdrew the log flume.")

    stray = _floating(w)
    if stray:
        raise ValueError(f"{len(stray)} cell(s) do not touch the rest of the ride, the first at "
                         f"{sorted(stray)[0]}; a design is one piece or it is not a design")

    narrow = [c for c in path_world if _lane_width(cells, c) < 2]
    if narrow:
        raise ValueError(f"{len(narrow)} channel cell(s) are one cell wide, the first at "
                         f"{narrow[0]}; a rider scrapes the wall the whole way down.")

    # ---- AND THAT YOU CAN GET IN AND OUT ON FOOT. `walk.py`'s model is stated in its own module
    # and every caller gets the same one, so a route it finds is one a player walks BOTH ways.
    ground = f.at((pi0 + pi1) // 2, pd0 - 6, 0)
    if not walk.stands(cells, ground):
        raise ValueError(f"the forecourt at {ground} is not somewhere a player can stand")
    walkable = walk.reachable(cells, ground)
    if head not in walkable:
        raise ValueError(f"the start box at {head} cannot be walked to from the forecourt at "
                         f"{ground}; there is no way to board the ride")
    if path_world[-1] not in walkable:
        raise ValueError(f"the splash pool at {path_world[-1]} has no way back up to the "
                         f"forecourt; the ride ends somewhere you cannot get out of")

    return {
        "kind": "rapids",
        "channel": n, "corners": len(corners), "descent": t,
        "water": len(sources_world), "pool_water": len(pool_wet),
        "tower": tside, "treads": len(treads), "trestles": trestles,
        "shelled": shelled, "lights": lights, "signs": signed, "span": s,
        "headroom": _HEADROOM,
        "basin": [list(c) for c in sorted(envelope)],
        "path": [list(c) for c in path_world],
        "sources": [list(c) for c in sources_world],
        "sequence": [list(c) for c in [head] + path_world],
        "board": list(head), "ground": list(ground), "exit": list(path_world[-1]),
        "flow": {k: v for k, v in report.items() if k != "levels"},
        "contract":
            "a rapids circuit a player can actually ride, and every clause of that is checked "
            "before a block is emitted: a stair tower carries you to a start box whose top course "
            "is level with the water so you step down into it (vanilla has no chain lift, and the "
            "one mechanism that raises a player through water - a soul-sand bubble column - "
            "cannot be walked into, which is why this replaced the flume rather than repairing "
            "it); ONE source feeds the whole descent because every step down restarts water's "
            "seven-block budget; `fluids.carries` proves the channel is flowing end to end with "
            "no still cell, `fluids.escapes` proves it stays in, every water cell has two clear "
            "courses over it and every channel cell is at least two wide, and `walk.py` walks a "
            "player from the forecourt to the start box and out of the splash pool.",
        "unverified": [
            "nothing about a BOAT has been simulated. The channel is one deep and the ride is "
            "meant to be swum; a boat may ground on a step.",
            "the current's SPEED is not modelled - `fluids.py` answers where water is and which "
            "way it flows, not how fast it carries you. Ride it once before anyone is told the "
            "descent completes without swimming.",
        ],
    }


def _floating(w: World) -> set:
    """Every cell not 6-connected to the largest mass. Empty, or the design is not one piece.

    **REPORTED, NEVER PRUNED.** Sweeping strays away was tried and it is the wrong operation: one
    of the fifty cells it removed was holding the trough's bed, and dropping it poured four hundred
    thousand cells of water onto the plot. A fragment is evidence that something upstream is wrong,
    so it fails the build and names a coordinate instead of being tidied out of sight.
    Six-connectivity, because that is what the game counts as touching.
    """
    cells = set(w.cells)
    seen, best = set(), set()
    for start in cells:
        if start in seen:
            continue
        stack, group = [start], set()
        seen.add(start)
        while stack:
            (x, y, z) = stack.pop()
            group.add((x, y, z))
            for (dx, dy, dz) in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                 (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                t = (x + dx, y + dy, z + dz)
                if t in cells and t not in seen:
                    seen.add(t)
                    stack.append(t)
        if len(group) > len(best):
            best = group
    return cells - best


def _clear_over(w: World, pos) -> int:
    """How many courses of air a body has over this cell, capped at what it is asked for.

    `fluids.PASSABLE` rather than "is there a block": a lantern, a rail or water itself is not a
    ceiling, and counting them as one would report a perfectly rideable channel as blocked.
    """
    (x, y, z) = pos
    k = 0
    for dy in range(1, _HEADROOM + 1):
        n = w.name(x, y + dy, z)
        if n is None or n.split("[")[0] in fluids.PASSABLE:
            k += 1
        else:
            break
    return k


def _lane_width(cells: dict, pos) -> int:
    """The widest open run through this cell on either horizontal axis, at its own course."""
    (x, y, z) = pos
    best = 0
    for (dx, dz) in ((1, 0), (0, 1)):
        run = 1
        for sgn in (1, -1):
            k = 1
            while fluids._passable(cells.get((x + dx * k * sgn, y, z + dz * k * sgn))):
                run += 1
                k += 1
                if k > 4:
                    break
        best = max(best, run)
    return best


BUILDERS = {"coaster": _coaster, "flume": _flume, "rapids": _rapids}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**COASTER, **cfg}
    if not p.get("at"):
        raise ValueError("coaster needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown coaster kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    return w.canvas({
        "kind": f"coaster/{p['kind']}",
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
