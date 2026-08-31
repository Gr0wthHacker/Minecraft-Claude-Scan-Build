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


def _station(w, f, pal, p, seed, i0, i1, dt):
    """The building you board in: a platform beside the track, a canopy over both, a back wall
    with windows, and its name over the door.

    THE ROOF SPANS THE TRACK. A station whose canopy stops at the platform edge is a bus shelter;
    what makes this read as a station is that the cart runs UNDER the roof, which means the far
    columns stand on the deck's own outer edge and the safety rail is suppressed for the length
    of the platform - you cannot board through a fence.
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
    for i in range(i0, i1 + 3):
        for d in range(dt - 2, dt + 8):
            w.put(*f.at(i, d, ceil), a if (i + d) % 2 == 0 else b)
            n += 1
    # ...and an eave of upside-down stairs all round it, so the roof has an edge rather than
    # stopping at a cliff. Every run here is the full frontage, so the min_run gate is moot and
    # asserted rather than assumed.
    span_i = list(range(i0, i1 + 3))
    if len(span_i) >= int(p["min_run"]):
        for i in span_i:
            w.put(*f.at(i, dt - 3, ceil), pal["stair"],
                  facing=_LEAN[f.facing], half="top", shape="straight", waterlogged="false")
            w.put(*f.at(i, dt + 8, ceil), pal["stair"],
                  facing=_LEAN[f.back], half="top", shape="straight", waterlogged="false")
            n += 2

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


def _flume_plan(p):
    """The channel, as waypoints in (i, d, h). NOT a circuit: a flume is a one-way ride that
    ends in the pool it started beside. Dock, LIFT, a top traverse, THE DROP, a run-out."""
    m, s, t, _half, dock, run = _flume_dims(p)
    return [
        (m,          m + 2,    0),      # the dock
        (m + dock,   m + 2,    0),      # dock end (colinear)
        (s,          m + 2,    t),      # CORNER - the lift, an enclosed tube
        (s,          s,        t),      # CORNER - the top traverse, open to the sky
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

    # THE TROUGH. Floor, then two courses of water source, then side walls.
    #
    # THE FLOOR IS A COLUMN, NOT A COURSE. Filled at one level per cell it is a diagonal
    # staircase on any graded run, and diagonal is not 6-connected - the ride would ship as one
    # fragment per flight. Filling from the LOWEST neighbour up to this cell's own level makes
    # every floor cell face-adjacent to the next by construction.
    water = 0
    for j, (i, d) in enumerate(pts):
        lo, hi = min(nb_h(j)), hs[j]
        for (oi, od) in [(0, 0)] + side_of[j] + [(o[0] * 2, o[1] * 2) for o in side_of[j]]:
            for hh in range(lo, hi + 1):
                w.put(*f.at(i + oi, d + od, hh), pal["ground"])
        for (oi, od) in [(0, 0)] + side_of[j]:
            for hh in (hs[j] + 1, hs[j] + 2):
                w.put(*f.at(i + oi, d + od, hh), "water", level="0")
                water += 1

    # THE WALLS, at twice the perpendicular offset, three courses over the floor. On the graded
    # sections - the lift and the drop, which is the whole ride - the two water courses are
    # GLAZED, because a graded channel has to be roofed (see the module docstring) and a roofed
    # ride you cannot see into is a corridor.
    graded = {j for j in range(n) if len(set(nb_h(j))) > 1}
    panes = 0
    for j, (i, d) in enumerate(pts):
        nxt = pts[j + 1] if j + 1 < n else pts[j - 1]
        for (oi, od) in [(o[0] * 2, o[1] * 2) for o in side_of[j]]:
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
        for hh in range(hs[j] + 3, want + 1):
            for (oi, od) in [(0, 0)] + side_of[j] + [(o[0] * 2, o[1] * 2) for o in side_of[j]]:
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

    sealed = _seal(w, pal["ground"])

    return {
        "kind": "flume",
        "channel": n, "corners": len(corners), "water": water, "panes": panes,
        "roof_cells": roofed, "trestles": trestles, "gantries": gantry,
        "pool": (pi1 - pi0 + 1) * (pd1 - pd0 + 1), "rim": rim, "sealed": sealed,
        "signs": signed, "top": int(p["flume_top"]), "span": s,
        "contract": "a one-way water ride whose bed is water SOURCES cell by cell, so it neither "
                    "drains nor stops seven blocks from a source. Every water cell has a solid "
                    "bed and a solid or glazed face on all four sides - which is why the graded "
                    "lift and drop are roofed and the flat runs are open.",
        "unverified": ["nothing about a BOAT has been simulated - the channel is verified as "
                       "watertight geometry, not as a ride that carries anything."],
    }


def _seal(w: World, mat: str) -> int:
    """The backstop: any empty cell touching a water source horizontally, or holding it up, is
    filled. A source flows into open air, so an unsealed face is not a cosmetic problem - it is
    the pool draining across the plot overnight. Nothing already placed is overwritten, so this
    only ever finds what the trough's own geometry missed."""
    n = 0
    for (x, y, z), (name, _props) in list(w.cells.items()):
        if name != "water":
            continue
        for (ox, oy, oz) in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)):
            q = (x + ox, y + oy, z + oz)
            if not w.has(*q):
                w.put(*q, mat)
                n += 1
    return n


BUILDERS = {"coaster": _coaster, "flume": _flume}


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
