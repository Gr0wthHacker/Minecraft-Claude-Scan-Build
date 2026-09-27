"""Prismworks v2 as a SYSTEM: the well, the course, the gantry and the floor together.

`tests/test_prismwell.py` checks the well on its own. Everything here is a property no single
design can hold, and each one is a way the land silently stops working:

  * A RUN YOU CANNOT START. The course is generated inside a mouth and knows nothing about the
    pier that reaches out to it. If the first landing drifts out of jumping range of the pier's
    head, the whole hundred courses are unreachable and every check still passes.
  * A GANTRY IN THE WAY. The rig hangs four courses over the route because the parkour's own
    headroom is three. One course lower and it is something to clip on the way into a landing -
    invisible in a render, and the sort of thing you find out by falling.
  * A FALL INTO THE VOID. The pool is sized from the course's radius band. If the course wanders
    outside it - the search flexes, and the taper is linear only in intent - a miss from that
    part of the run lands on the apron, the wall, or nothing at all.
  * TWO DESIGNS DRIFTING. The rig is derived from the descent's own recorded route rather than
    re-deriving the helix from the same parameters, which is the drift `proportions.measure` and
    `rubric.score` share an entry point to avoid. If the descent regenerates and the rig does
    not, the gantry hangs over empty air.
"""
import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import schem, scan                      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
WELL, DESC = "PF Prism Well", "PF Prism Descent"
CROWN = "PF Crown Descent"
RIG, FLOOR = "PF Prism Rig", "PF Signal Zero"


def _side(name):
    p = os.path.join(OUT, f"{name}.scan.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def _have(*names):
    return all(os.path.exists(os.path.join(OUT, f"{n}.litematic")) and _side(n) for n in names)


def _cells(name):
    m = schem.load(os.path.join(OUT, f"{name}.litematic"))
    s = scan.load(os.path.join(OUT, f"{name}.scan.json"))
    ox, oy, oz = s.origin
    out = {}
    ys, zs, xs = m.solid().nonzero()
    names = m.names
    for y, z, x in zip(ys, zs, xs):
        out[(int(x + ox), int(y + oy), int(z + oz))] = names[m.ids[y, z, x]].split("[")[0].split(":")[-1]
    return out


def _route(name=DESC):
    return [tuple(c) for c in _side(name)["route"]]


def _routes():
    """Every landing of every run. The well has TWO concentric courses now."""
    out = []
    for n in (DESC, CROWN):
        if _side(n):
            out += _route(n)
    return out


needs = pytest.mark.skipif(not _have(WELL, DESC),
                           reason="needs the well and the descent generated")
needs_rig = pytest.mark.skipif(not _have(WELL, DESC, RIG), reason="needs the rig too")
needs_floor = pytest.mark.skipif(not _have(DESC, FLOOR), reason="needs the floor too")


@needs
def test_the_run_can_actually_be_started():
    """The first landing has to be within a sprint jump of the pier's head.

    The course is generated inside the mouth by `gen/parkour.py`, which knows nothing about the
    pier; the pier is built by the well, which knows nothing about the course. Nothing connects
    them but two numbers in two configs, and if they drift the whole hundred courses is a
    beautifully-verified run that nobody can get onto.
    """
    md = _side(WELL)
    cx, cz = md["centre"]
    route = _route()
    first = route[0]
    cells = _cells(WELL)
    dy = 202
    # the pier's cells: deck-course cells on the entry axis, inside the collar
    pier = [(x, y, z) for (x, y, z), n in cells.items()
            if y == dy and math.hypot(x - cx, z - cz) < md["r_mouth"] - 1]
    assert pier, "the well built no pier inside the mouth at all"
    best = min(math.dist((first[0], first[2]), (px, pz)) for px, _py, pz in pier)
    assert best <= 4.6, (
        f"the first landing at {first[:3]} is {best:.1f} blocks from the nearest pier cell - "
        f"a sprint jump is about 4.5, so the course cannot be entered")


@needs
def test_the_course_never_touches_the_well():
    """A landing inside the collar, the pier or the return column is a landing that is really
    just a floor - and the column in particular would let you ride most of the run."""
    md = _side(WELL)
    cx, cz = md["centre"]
    well = set(_cells(WELL))
    bad = []
    for (x, y, z, kind) in ((c[0], c[1], c[2], c[3]) for c in _routes()):
        if (x, y, z) in well:
            bad.append((x, y, z, kind))
        if math.hypot(x - cx, z - cz) < 8:
            bad.append((x, y, z, f"{kind} inside the return column"))
    assert not bad, f"{len(bad)} moves of the course share a cell with the well: {bad[:5]}"


@needs_rig
def test_the_gantry_is_never_in_a_jump():
    """Four courses over the route, because the parkour's headroom is three.

    A beam one course lower is a block you clip on the way into a landing. It is invisible in
    every render this repo has - a beam above a landing and a beam in front of one draw the same
    - so it is arithmetic or it is nothing.
    """
    rig = _cells(RIG)
    bad = []
    # A REST IS 3x3 AND ONLY ITS CENTRE IS IN THE ROUTE, which is how two beam cells once
    # ended up inside the corner of a checkpoint - invisible to both designs, and reported
    # only by the park assembly's clash check.
    for c in _routes():
        h = 1 if (len(c) > 3 and c[3] == "rest") else 0
        for dx in range(-h, h + 1):
            for dz in range(-h, h + 1):
                for dy in range(0, 4):
                    q = (c[0] + dx, c[1] + dy, c[2] + dz)
                    if q in rig:
                        bad.append((*q, rig[q]))
    assert not bad, f"{len(bad)} rig cells sit in a landing's own column: {bad[:6]}"


@needs_rig
def test_the_gantry_is_one_line_PER_RUN():
    """It exists because 86 scattered landings read as confetti. A gantry in 168 pieces - which
    is what the first build shipped, because a sampled line steps DIAGONALLY and a diagonal
    neighbour is not a neighbour - is confetti with a longer name.

    ONE LINE PER RUN, NOT ONE OBJECT. The well has two concentric courses and their gantries are
    two separate helices ten blocks apart; joining them would draw a beam across open void that
    nobody asked for and that might sit in a jump path. So the assertion is per course, and the
    count of pieces must equal the count of runs - which is also what catches the opposite
    failure, a stitch pass that helpfully bridges them.
    """
    cells = set(_cells(RIG))
    seen, pieces = set(), 0
    for c0 in cells:
        if c0 in seen:
            continue
        pieces += 1
        stack = [c0]
        seen.add(c0)
        while stack:
            x, y, z = stack.pop()
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                q = (x + d[0], y + d[1], z + d[2])
                if q in cells and q not in seen:
                    seen.add(q)
                    stack.append(q)
    runs = sum(1 for n in (DESC, CROWN) if _side(n))
    assert pieces == runs, (
        f"the gantry is in {pieces} pieces for {runs} run(s) - either a line came apart or the "
        f"stitch bridged two courses that should stay separate")


@needs_rig
def test_the_gantry_was_built_from_this_course():
    """One source, so the two cannot drift. If the descent regenerates and the rig does not, the
    gantry hangs over a route that no longer exists - and every check on each design alone still
    passes, because neither knows about the other."""
    md = _side(RIG)
    src = md.get("route_from")
    src = src if isinstance(src, list) else [src]
    assert any(str(x).endswith("PF Prism Descent.scan.json") for x in src), (
        f"the rig was not built from the deck run's sidecar: {src!r}")
    rig = set(_cells(RIG))
    route = _routes()
    hang = 4
    missing = [c[:3] for c in route if not any(
        (c[0] + dx, c[1] + hang, c[2] + dz) in rig
        for dx in (-2, -1, 0, 1, 2) for dz in (-2, -1, 0, 1, 2))]
    assert len(missing) <= len(route) * 0.05, (
        f"{len(missing)} of {len(route)} moves have no gantry over them - the rig is stale: "
        f"{missing[:5]}")


@needs_floor
def test_every_fall_lands_in_the_pool():
    """The one that stops the course being lethal.

    A miss falls straight down from wherever it happened, so the pool has to cover the whole
    radius band the course actually occupies - not the band the config asked for. The taper is
    linear in intent and the search flexes either side of it, so this is measured off the route
    rather than computed from `radius` and `radius_bottom`.
    """
    md = _side(FLOOR)
    cx, cz = md["centre"]
    pr = md["pool_r"]
    out = [(c[0], c[1], c[2], round(math.hypot(c[0] - cx, c[2] - cz), 1))
           for c in _routes() if math.hypot(c[0] - cx, c[2] - cz) > pr - 1.5]
    assert not out, (
        f"{len(out)} moves sit outside the pool's radius of {pr} - a miss there lands on the "
        f"apron, the wall or nothing: {out[:5]}")
    inner = [c[:3] for c in _routes()
             if math.hypot(c[0] - cx, c[2] - cz) < md.get("keep_clear", 6) + 1.5]
    assert not inner, f"{len(inner)} moves sit over the column's kept-clear footprint: {inner[:5]}"


@needs_floor
def test_the_pool_is_a_room_and_not_a_ledge():
    """The floor hangs in open void; its edge is a drop on every side with nothing under it. A
    wall with a gap in it is a chamber you can walk out of."""
    cells = _cells(FLOOR)
    md = _side(FLOOR)
    cx, cz = md["centre"]
    wy = md["y_floor"]
    have = {round(math.degrees(math.atan2(z - cz, x - cx)) % 360.0)
            for (x, y, z), n in cells.items() if y == wy + 1}
    gaps, run = [], 0
    for a in range(360):
        run = 0 if a in have else run + 1
        if a not in have and (a + 1) % 360 in have:
            gaps.append(run)
    assert not [g for g in gaps if g >= 5], f"the chamber wall has openings: {sorted(gaps)[-4:]}"


@needs_floor
def test_the_bell_hangs_from_something():
    """A bell attached to the ceiling needs a real block over it. The bat perch's vines and the
    taproot's lantern chains both shipped as loose links for want of one."""
    cells = _cells(FLOOR)
    bells = [(x, y, z) for (x, y, z), n in cells.items() if n == "bell"]
    assert len(bells) == 1, f"expected exactly one bell, found {len(bells)}"
    x, y, z = bells[0]
    assert (x, y + 1, z) in cells, "the bell hangs from air"


@needs_floor
def test_the_whole_land_is_cheap():
    """v1 was 54% two dark greys and cost nothing. v2 gets a real value ladder across families
    and must still cost nothing - the point was never that the old palette was dear."""
    from mcbuild import palette
    dear = {}
    for n in (WELL, DESC, RIG, FLOOR):
        if not _have(n):
            continue
        for name in set(_cells(n).values()):
            if palette.tier(name) == "expensive":
                dear.setdefault(n, set()).add(name)
    assert not dear, f"expensive blocks in Prismworks v2: {dear}"


needs_crown = pytest.mark.skipif(not _have(WELL, CROWN), reason="needs the sky run generated")


@needs_crown
def test_the_sky_run_stays_inside_the_mouths_cylinder():
    """THE ONE THAT STOPS THE UPPER HALF BEING LETHAL, and it is a safety rule wearing the
    clothes of a shape rule.

    Ninety-eight courses of this course hang in open air ABOVE the deck. Below the deck a miss
    falls down the well into the pool; above it, a landing outside the mouth's r50 falls onto
    the LAWN at Y203 from as much as a hundred courses up, which is fatal, and no amount of
    catch platforms in that airspace would be anything but clutter. Kept inside the cylinder,
    the whole two-hundred-course run has exactly one failure mode and it is the pool.
    """
    md = _side(WELL)
    cx, cz = md["centre"]
    rm = md["r_mouth"]
    out = [(c[0], c[1], c[2], round(math.hypot(c[0] - cx, c[2] - cz), 1))
           for c in _route(CROWN) if math.hypot(c[0] - cx, c[2] - cz) > rm - 4]
    assert not out, (
        f"{len(out)} landings of the sky run sit outside the mouth (r{rm}) - a miss there lands "
        f"on the lawn, not in the water: {out[:5]}")


@needs_crown
def test_the_sky_run_starts_off_the_crown_pier():
    """Same trap as the deck run, ninety-eight courses higher and with no rim to fall back on.

    The crown pier also came out EMPTY once: its body loop read `range(33, 8)`, which runs zero
    times, so only the five-cell head was built and it shipped as a floating component in open
    sky. A loop that never runs looks exactly like one that works.
    """
    md = _side(WELL)
    crown = 300
    cells = _cells(WELL)
    pier = [(x, y, z) for (x, y, z), n in cells.items() if y == crown]
    assert len(pier) > 30, f"the crown deck and pier are only {len(pier)} cells - the pier is missing"
    first = _route(CROWN)[0]
    best = min(math.dist((first[0], first[2]), (px, pz)) for px, _py, pz in pier)
    assert best <= 4.6, (
        f"the sky run's first landing at {first[:3]} is {best:.1f} from the nearest crown cell")


@needs_crown
def test_the_two_runs_are_plainly_apart():
    """Concentric, not interleaved. Two helices at the same radius below the deck would be two
    lines of one-block landings nobody could tell apart mid-run - which is worse than one line,
    because you would follow the wrong one and fall. The sky run holds r30; the deck run stays
    inside it."""
    md = _side(WELL)
    cx, cz = md["centre"]
    def band(name):
        rs = [math.hypot(c[0] - cx, c[2] - cz) for c in _route(name)]
        return min(rs), max(rs)
    dlo, dhi = band(DESC)
    clo, chi = band(CROWN)
    # EITHER ORDER. Which run is inner is a design decision that has already been reversed
    # once - the sky run moved inside to wrap the tower, and the deck run took the outside -
    # so what is asserted is that the BANDS DO NOT OVERLAP, not which one is smaller. A test
    # that pins the order would have failed the moment the towers arrived and told us nothing
    # about the property that matters.
    gap = max(clo - dhi, dlo - chi)
    assert gap > 0, (
        f"the two runs share a radius band: deck {dlo:.0f}-{dhi:.0f}, sky {clo:.0f}-{chi:.0f} - "
        f"below the deck they would interleave into one unreadable mess")
