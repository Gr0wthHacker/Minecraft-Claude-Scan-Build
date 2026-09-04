"""The log flume actually carries a rider - proven, not asserted.

The first flume audited clean, cost the right materials, and rendered like a water ride while
every one of its 564 water cells was `level=0`, a SOURCE. A source does not push - a trough of
them is STILL water, and a rider dropped in floats where they land and goes nowhere. That is this
project's cardinal sin, the same one the casino's `chase` and `vault` were cut for: a machine that
looks like it works. `mcbuild/fluids.py` exists to catch exactly this, by simulating the spread
the same way `mcbuild/circuit.py` simulates redstone, and these tests hold the generator to it.

Nothing here re-derives the channel's geometry. `_flume` exposes its own `path` (the cells a rider
travels) and `sources` (the cells that feed them, deliberately not on the path - a source cell is
where the rider floats) in the design's meta, and `_flume` itself already refuses to build a
channel `fluids.carries` calls dry: these tests exercise that same contract from the outside, on
the actual shipped materials.
"""
from __future__ import annotations

from collections import deque

import pytest

from mcbuild import blocks, fluids, palette
from mcbuild.gen import park
from mcbuild.gen.coaster import BUILDERS, COASTER
from mcbuild.gen.vertical import World

LANDS = sorted(park.LANDS)
FACINGS = ("east", "north", "west", "south")

# The shipped ride (`planner.py`'s frontier zone) plus a couple of other sizes this generator has
# to support - the default, and one bigger than either. Every one of these failed at least once
# during development, so they all stay.
SIZES = [
    {"flume_span": 29, "flume_top": 20, "pool": 4},          # the shipped Log Flume
    {"flume_span": 44, "flume_top": 30},                      # the module default
    {"flume_span": 36, "flume_top": 24, "pool": 5},
]


def _built(land="frontier", facing="south", **kw):
    """The raw World and meta, so a test can ask about cells in WORLD coordinates - the same
    reason `test_park.py._built` does it: the canvas is sized to its own content and shifts
    between builds, so anything compared against it lines up against nothing."""
    p = {**COASTER, "kind": "flume", "at": [0, 100, 0], "facing": facing, "land": land,
         "flume_span": 44, "flume_top": 30, **kw}
    w = World()
    meta = BUILDERS["flume"](w, p, None)
    return w, meta, p


def _cells(w) -> dict:
    """`fluids.spread` wants (x, y, z) -> block name; `World.cells` is (x, y, z) -> (name, props),
    which is the SAME dict `_flume` itself checks against before it will build at all."""
    return {pos: name for pos, (name, _props) in w.cells.items()}


def _components(w):
    cells = set(w.cells)
    seen, sizes = set(), []
    for start in cells:
        if start in seen:
            continue
        q, seen_here = deque([start]), 0
        seen.add(start)
        while q:
            x, y, z = q.popleft()
            seen_here += 1
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                n = (x + d[0], y + d[1], z + d[2])
                if n in cells and n not in seen:
                    seen.add(n)
                    q.append(n)
        sizes.append(seen_here)
    return sorted(sizes, reverse=True)


# ------------------------------------------------------------------ the contract itself

def test_the_channel_carries_a_rider():
    """THE POINT OF THIS FILE. `fluids.carries` must be True over the ride's own exposed path -
    no dry cell (the rider stops) and no still cell (the rider floats) anywhere but the sources
    the ride declares."""
    w, meta, _p = _built()
    cells = _cells(w)
    path = [tuple(c) for c in meta["path"]]
    sources = [tuple(c) for c in meta["sources"]]
    report = fluids.carries(cells, path, sources)
    assert report["carries"], report
    assert report["dry"] == 0
    assert report["still"] == 0
    assert report["cells"] == len(path) > 0
    assert report["moving"] == report["cells"], "every non-source cell must be FLOWING water"


def test_the_reported_flow_matches_a_fresh_check():
    """`_flume` runs this same check at generation time and refuses to build if it fails - so the
    `flow` it reports in its own meta should be reproducible from the outside, not just trusted."""
    w, meta, _p = _built()
    cells = _cells(w)
    path = [tuple(c) for c in meta["path"]]
    sources = [tuple(c) for c in meta["sources"]]
    report = fluids.carries(cells, path, sources)
    assert report["cells"] == meta["flow"]["cells"]
    assert report["dry"] == meta["flow"]["dry"] == 0
    assert report["still"] == meta["flow"]["still"] == 0


def test_no_dry_runs_along_the_path():
    """The purely geometric check - usable without building anything - agrees with the simulated
    one: no stretch of the path longer than seven cells with no source in reach. `dry_runs` wants
    the FULL ride sequence with the sources left in (it resets its own budget on each one), which
    is exactly what `meta["sequence"]` is for - `meta["path"]` has the sources already removed,
    for `fluids.carries`, and handing that to `dry_runs` would never see a reset at all."""
    w, meta, _p = _built()
    sources = {tuple(c) for c in meta["sources"]}
    sequence = [tuple(c) for c in meta["sequence"]]
    assert fluids.dry_runs(sequence, sources) == []


def test_the_bed_is_solid_under_every_water_cell():
    """Water on air drains away instead of flowing where it is meant to. Every cell that ever
    holds water - the flowing path AND the still sources - must have something solid one course
    down, or the channel is a leak rather than a ride."""
    w, meta, _p = _built()
    cells = _cells(w)
    for c in list(meta["path"]) + list(meta["sources"]):
        x, y, z = c
        below = (x, y - 1, z)
        assert below in cells, f"{c} has an open bed at {below}"
        assert cells[below] != "air"


@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"span{s['flume_span']}")
@pytest.mark.parametrize("facing", FACINGS)
def test_it_carries_at_every_facing_and_size(facing, size):
    """The channel geometry is built relative to the ride's own frame, so a facing rotation or a
    span/top change must not be able to reopen the corner-collision bug this file exists to pin -
    a corner's own doubled offset landing on a straight cell of one of its two legs, two indices
    away, which happened three separate ways (a wall, a roof fill, and the floor bed) before the
    fix was general rather than local to one of them."""
    w, meta, _p = _built(facing=facing, **size)
    cells = _cells(w)
    path = [tuple(c) for c in meta["path"]]
    sources = [tuple(c) for c in meta["sources"]]
    report = fluids.carries(cells, path, sources)
    assert report["carries"], (facing, size, report)


def test_it_never_needed_the_bed_backstop():
    """`_seal` is a conservative below-only backstop now, not the blind horizontal fill that
    walled every spaced source into its own sealed pocket. On a geometry that is correct by
    construction it should find nothing to do."""
    w, meta, _p = _built()
    assert meta["sealed"] == 0


# ------------------------------------------------------------------ it is a real ride

def test_it_has_a_lift_and_at_least_two_drops():
    """A flume that only descends is a chute; a flume with no lift is a fall. `_flume_plan`'s own
    waypoints are the ride's spine - a climb (the lift hill), then multiple descending legs."""
    from mcbuild.gen.coaster import _flume_plan
    w, _meta, p = _built()
    wps = _flume_plan(p)
    deltas = [b[2] - a[2] for a, b in zip(wps, wps[1:])]
    assert any(d > 0 for d in deltas), "no lift hill"
    assert sum(1 for d in deltas if d < 0) >= 2, "fewer than two drops"


def test_it_has_a_stair_climbed_loading_platform():
    """The dock: a platform you reach by a real flight of stairs, not a teleport onto the boat."""
    w, _meta, p = _built()
    stair = park.LANDS[p["land"]]["stair"]
    assert any(name == stair for name, _props in w.cells.values())


def test_it_is_one_connected_piece():
    w, _meta, _p = _built()
    assert _components(w) == [len(w.cells)]


def test_the_sign_names_the_ride():
    w, _meta, p = _built(title="LOG FLUME")
    assert any("LOG FLUME" in line for t in w.signs.values() for line in t["front"])


def test_no_sign_line_is_wider_than_the_sign():
    w, _meta, _p = _built(title="A VERY LONG ATTRACTION NAME INDEED")
    for t in w.signs.values():
        for line in list(t["front"]) + list(t["back"]):
            assert len(line) <= park.SIGN_WIDTH, f"{line!r} clips"


def test_every_sign_has_a_block_and_support_behind_it():
    w, _meta, _p = _built()
    for (x, y, z) in w.signs:
        assert (x, y, z) in w.cells, "sign TEXT with no sign BLOCK is a corrupt region"
        _name, props = w.cells[(x, y, z)]
        fdx, fdz = park._STEP[props["facing"]]
        assert (x - fdx, y, z - fdz) in w.cells, f"sign at {(x, y, z)} has no support"


# ------------------------------------------------------------------ legal, 1.19, and not currency

@pytest.mark.parametrize("land", LANDS)
def test_every_block_state_is_legal(land):
    w, _meta, _p = _built(land=land)
    for name, props in w.cells.values():
        assert blocks.validate(name, props) == [], f"{name}{props} is not a legal state"


@pytest.mark.parametrize("land", LANDS)
def test_nothing_built_is_currency_or_expensive(land):
    w, _meta, _p = _built(land=land)
    for name, _props in w.cells.values():
        assert blocks.spendable(name), f"{land} flume places CURRENCY: {name}"
        assert blocks.available(name), f"{land} flume places a block off the 1.19 allowlist: {name}"
        assert palette.tier(name) != "expensive", f"{land} flume places expensive: {name}"


@pytest.mark.parametrize("land", LANDS)
def test_it_builds_a_real_canvas(land):
    from mcbuild.gen import coaster
    p = {"kind": "flume", "at": [0, 100, 0], "facing": "south", "land": land,
         "flume_span": 29, "flume_top": 20, "pool": 4}
    c = coaster.build(p, [])
    assert c.to_model().ids.size > 0
