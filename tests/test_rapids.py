"""The rapids run is RIDEABLE - proven, not asserted, and the proof includes the player's head.

The log flume it replaced carried water end to end and still could not be used, because seven of
its 137 water cells had less than two clear courses over them and a player is two blocks tall. That
fault was invisible to every check this project had, and the reason is worth stating once: every
one of them asks about BLOCKS - is the state legal, is it in 1.19, is it affordable, does it have
support, does the water flow - and the failure was in the AIR.

So the first test here is the headroom one, and it runs over every cell the water actually REACHES
rather than over the source blocks the design emits: a design ships sources and the game computes
the flow, so checking `w.cells` for `water` inspects a few dozen cells and misses the three hundred
a rider is carried through.

Nothing here re-derives the ride's geometry. `_rapids` exposes its own `path` (the cells a rider
travels), `sources` (what feeds them), `basin` (every cell water is allowed in) and the three
coordinates the walk has to connect, and it already refuses to build anything that fails them -
these tests exercise the same contract from the outside, on the shipped materials.
"""
from __future__ import annotations

from collections import deque

import pytest

from mcbuild import blocks, fluids, palette, walk
from mcbuild.gen import coaster, park
from mcbuild.gen.coaster import BUILDERS, COASTER, _HEADROOM, _MAX_FLAT
from mcbuild.gen.vertical import World

LANDS = sorted(park.LANDS)
FACINGS = ("east", "north", "west", "south")

# The default, one at each end of what the geometry will take, and one in between. Every size here
# broke at least once while this was being built, so they all stay.
SIZES = [
    {},
    {"rapids_span": 23, "rapids_top": 10, "pool": 4},
    {"rapids_span": 28, "rapids_top": 18, "pool": 5},
    {"rapids_span": 40, "rapids_top": 30},
]

_CACHE = {}


def _built(land="frontier", facing="south", **kw):
    """The raw World and meta, so a test can ask about cells in WORLD coordinates - the canvas is
    sized to its own content and shifts between builds, so anything compared against it lines up
    against nothing."""
    key = (land, facing, tuple(sorted(kw.items())))
    if key not in _CACHE:
        p = {**COASTER, "kind": "rapids", "at": [0, 100, 0], "facing": facing, "land": land, **kw}
        w = World()
        _CACHE[key] = (w, BUILDERS["rapids"](w, p, None), p)
    return _CACHE[key]


def _cells(w) -> dict:
    return {pos: name for pos, (name, _props) in w.cells.items()}


def _wet(w, meta) -> dict:
    """Every cell the game will actually put water in, and at what level."""
    return fluids.spread(_cells(w), [tuple(c) for c in meta["sources"]])


def _clear(cells, pos, cap) -> int:
    (x, y, z) = pos
    k = 0
    for dy in range(1, cap + 1):
        n = cells.get((x, y + dy, z))
        if n is None or n.split("[")[0] in fluids.PASSABLE:
            k += 1
        else:
            break
    return k


# ------------------------------------------------------------------------------ A PLAYER FITS

@pytest.mark.parametrize("facing", FACINGS)
def test_every_water_cell_has_two_clear_courses(facing):
    """THE ONE THE FLUME FAILED. 130 of its cells had three courses clear, four had one and three
    had none - and you stop at the first of those, part way down, which is the whole bug."""
    w, meta, _p = _built(facing=facing)
    cells = _cells(w)
    tight = {c: _clear(cells, c, _HEADROOM) for c in _wet(w, meta)}
    bad = {c: k for c, k in tight.items() if k < _HEADROOM}
    assert not bad, f"{len(bad)} wet cell(s) a player cannot fit through, e.g. {sorted(bad)[:3]}"


@pytest.mark.parametrize("size", SIZES)
def test_it_fits_a_player_at_every_size(size):
    w, meta, _p = _built(**size)
    cells = _cells(w)
    assert all(_clear(cells, c, _HEADROOM) >= _HEADROOM for c in _wet(w, meta))


def test_the_headroom_check_can_actually_fail():
    """A control. Drop a lid one course over the water and the same measurement must catch it -
    otherwise the test above is only asserting that nothing happens to be in the way."""
    w, meta, _p = _built()
    cells = _cells(w)
    (x, y, z) = tuple(meta["path"][len(meta["path"]) // 2])
    cells[(x, y + 1, z)] = "stone_bricks"
    assert _clear(cells, (x, y, z), _HEADROOM) < _HEADROOM


@pytest.mark.parametrize("facing", FACINGS)
def test_the_channel_is_at_least_two_cells_wide(facing):
    """A one-wide gutter is a wall you scrape the whole way down. Measured as the widest open run
    through the cell on either horizontal axis, at the cell's own course."""
    w, meta, _p = _built(facing=facing)
    cells = _cells(w)
    widths = [coaster._lane_width(cells, tuple(c)) for c in meta["path"]]
    assert min(widths) >= 2, f"narrowest channel cell is {min(widths)} wide"


# ------------------------------------------------------------------------------ THE WATER WORKS

def test_the_channel_carries_a_rider():
    w, meta, _p = _built()
    report = fluids.carries(_cells(w), [tuple(c) for c in meta["path"]],
                            [tuple(c) for c in meta["sources"]])
    assert report["carries"], report
    assert report["dry"] == 0 and report["still"] == 0
    assert report["moving"] == report["cells"]


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("facing", FACINGS)
def test_it_carries_at_every_facing_and_size(facing, size):
    w, meta, _p = _built(facing=facing, **size)
    report = fluids.carries(_cells(w), [tuple(c) for c in meta["path"]],
                            [tuple(c) for c in meta["sources"]])
    assert report["carries"], (facing, size, report["stops_at"])


def test_the_reported_flow_matches_a_fresh_check():
    """The generator ships its own answer in `flow`; recomputing it from the materials has to
    agree, or the sidecar is telling a story about a build nobody has."""
    w, meta, _p = _built()
    fresh = fluids.carries(_cells(w), [tuple(c) for c in meta["path"]],
                           [tuple(c) for c in meta["sources"]])
    for k, v in meta["flow"].items():
        assert fresh[k] == v, k


def test_no_cell_a_rider_travels_holds_a_source():
    """A source does not push - a trough of them is STILL water and the rider floats where they
    land. That is what withdrew the first flume, and it is why the start box is off the path."""
    w, meta, _p = _built()
    srcs = {tuple(c) for c in meta["sources"]}
    assert not [c for c in meta["path"] if tuple(c) in srcs]


def test_one_source_feeds_the_whole_descent():
    """Falling water is level 8 and spreads again from where it lands, so every step down restarts
    the seven-block budget. The flume needed a source every six cells and shipped 193 of them for
    a player to place by hand; the channel here needs exactly one."""
    w, meta, _p = _built()
    basin = {tuple(c) for c in meta["basin"]}
    pool = {tuple(c) for c in meta["sources"]} - {tuple(meta["board"])}
    assert tuple(meta["board"]) in basin
    channel_sources = [c for c in meta["sources"] if tuple(c) not in pool]
    assert len(channel_sources) == 1, f"{len(channel_sources)} sources in the channel"


def test_nothing_escapes_the_basin():
    """`carries` walks the PATH and has nothing to say about the cells beside it. The shipped flume
    passed it while pouring 199,959 cells of water off the plot, so a water ride needs both."""
    w, meta, _p = _built()
    out = fluids.escapes(_cells(w), [tuple(c) for c in meta["sources"]],
                         [tuple(c) for c in meta["basin"]])
    assert out == [], f"{len(out)} cell(s) outside the basin, first {out[:1]}"


@pytest.mark.parametrize("facing", FACINGS)
def test_every_water_cell_is_enclosed(facing):
    w, meta, _p = _built(facing=facing)
    stranded = fluids.unenclosed(_cells(w), allow=[tuple(c) for c in meta["basin"]])
    assert stranded == [], stranded[:3]


def test_the_leak_check_can_actually_fail():
    """A control, for the same reason as the headroom one: knock a hole in the bed and `escapes`
    must find it, or an empty answer is proving nothing."""
    w, meta, _p = _built()
    cells = _cells(w)
    (x, y, z) = tuple(meta["path"][len(meta["path"]) // 2])
    cells.pop((x, y - 1, z), None)
    out = fluids.escapes(cells, [tuple(c) for c in meta["sources"]],
                         [tuple(c) for c in meta["basin"]])
    assert out, "a hole punched in the bed drained nowhere - the check is asleep"


def test_the_run_never_stays_level_past_the_flow_limit():
    """Water reaches seven blocks from where it last fell, so an eighth level cell is dry and the
    rider stops there. The grade is checked before a block is placed; this is the same arithmetic
    from the outside, on the heights the build actually used."""
    w, meta, _p = _built()
    ys = [c[1] for c in meta["path"]]
    run = 0
    for a, b in zip(ys, ys[1:]):
        run = 0 if b < a else run + 1
        assert run <= _MAX_FLAT, f"{run} level cells in a row"


# ------------------------------------------------------------------------------ YOU CAN RIDE IT

@pytest.mark.parametrize("facing", FACINGS)
def test_you_can_walk_from_the_forecourt_to_the_start_box(facing):
    """**THE ASCENT IS THE REASON THIS REPLACED THE FLUME.** Vanilla has no chain lift, and the one
    mechanism that raises a player through water - a soul-sand bubble column - has to be sealed on
    every side above the waterline, so its only opening is one course tall and no flood fill can
    prove you get aboard. A staircase can be walked, and `walk.py` walks it."""
    w, meta, _p = _built(facing=facing)
    cells = _cells(w)
    ground, board = tuple(meta["ground"]), tuple(meta["board"])
    assert walk.stands(cells, ground), "the forecourt is not somewhere a player can stand"
    assert walk.connects(cells, ground, board), "no route from the street to the start box"


@pytest.mark.parametrize("facing", FACINGS)
def test_you_can_walk_out_of_the_splash_pool(facing):
    """A ride that ends somewhere you cannot climb out of is a hole with water in it."""
    w, meta, _p = _built(facing=facing)
    cells = _cells(w)
    assert walk.connects(cells, tuple(meta["exit"]), tuple(meta["ground"]))


def test_the_walk_is_reversible_by_construction():
    """`walk.py` steps one course either way, so a route it finds is one a player walks BOTH ways -
    which is what makes the pool an exit as well as a landing. Asserted rather than assumed,
    because a one-way flight is exactly the fault the court stair shipped once."""
    w, meta, _p = _built()
    cells = _cells(w)
    assert walk.connects(cells, tuple(meta["board"]), tuple(meta["ground"]))


def test_the_stair_treads_lean_the_way_they_climb():
    """A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D, half=bottom - the convention
    `test_stairhead` pins. It is asserted rather than looked at because our renderer draws a stair
    facing either way identically, so a backwards flight is invisible offline and unwalkable in
    game."""
    w, meta, _p = _built()
    treads = sorted(((pos, props) for pos, (name, props) in w.cells.items()
                     if name.endswith("_stairs")),
                    key=lambda t: t[0][1])
    assert len(treads) >= meta["treads"], "the stair tower has lost its treads"
    step = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
    checked = 0
    for (pos, props) in treads:
        assert props["half"] == "bottom"
        # the next tread of THIS flight: one course up and one cell along. Both flights - the
        # tower's spiral and the slipway out of the pool - are covered, and a stair that is not
        # part of a flight (a coping, a lone step) is left alone rather than guessed at.
        up = [q for (q, _pp) in treads
              if q[1] == pos[1] + 1 and abs(q[0] - pos[0]) + abs(q[2] - pos[2]) == 1]
        if len(up) != 1:
            continue
        (dx, dz) = step[props["facing"]]
        assert (pos[0] + dx, pos[2] + dz) == (up[0][0], up[0][2]), (
            f"tread at {pos} faces {props['facing']} but the flight climbs toward {up[0]}")
        checked += 1
    assert checked >= meta["treads"] - 2, f"only {checked} treads were part of a flight"


# ------------------------------------------------------------------------------ ONE PIECE, LEGAL

def _components(w):
    cells = set(w.cells)
    seen, sizes = set(), []
    for start in cells:
        if start in seen:
            continue
        q, k = deque([start]), 0
        seen.add(start)
        while q:
            (x, y, z) = q.popleft()
            k += 1
            for (dx, dy, dz) in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                 (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                t = (x + dx, y + dy, z + dz)
                if t in cells and t not in seen:
                    seen.add(t)
                    q.append(t)
        sizes.append(k)
    return sorted(sizes, reverse=True)


@pytest.mark.parametrize("facing", FACINGS)
def test_it_is_one_connected_piece(facing):
    w, _meta, _p = _built(facing=facing)
    sizes = _components(w)
    assert len(sizes) == 1, f"{len(sizes)} pieces: {sizes[:6]}"


@pytest.mark.parametrize("size", SIZES)
def test_it_is_one_piece_at_every_size(size):
    assert len(_components(_built(**size)[0])) == 1


def test_the_ride_says_what_it_is_and_where_you_get_on():
    w, meta, _p = _built()
    assert meta["signs"] == 2
    text = " ".join(" ".join(t["front"]) for t in w.signs.values()).upper()
    assert "RAPIDS" in text and "BOARDING" in text


def test_no_sign_line_is_wider_than_the_sign():
    w, _meta, _p = _built()
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


@pytest.mark.parametrize("land", LANDS)
def test_every_block_state_is_legal(land):
    w, _meta, _p = _built(land=land)
    for name, props in w.cells.values():
        assert blocks.validate(name, props) == [], f"{name}{props} is not a legal state"


@pytest.mark.parametrize("land", LANDS)
def test_nothing_built_is_currency_or_expensive(land):
    w, _meta, _p = _built(land=land)
    for name, _props in w.cells.values():
        assert blocks.spendable(name), f"{land} rapids places CURRENCY: {name}"
        assert blocks.available(name), f"{land} rapids places a 1.19-illegal block: {name}"
        assert palette.tier(name) != "expensive", f"{land} rapids places expensive: {name}"


@pytest.mark.parametrize("land", LANDS)
def test_it_builds_a_real_canvas(land):
    p = {"kind": "rapids", "at": [0, 100, 0], "facing": "south", "land": land}
    c = coaster.build(p, [])
    assert c.to_model().ids.size > 0
    assert c.meta["kind"] == "rapids"


def test_a_size_the_geometry_cannot_build_is_refused_by_name():
    """The guard is the arithmetic and it names the dimension at fault - `_feasible`'s rule, which
    exists because two hand-written minimums in this module disagreed with the geometry under
    them and refused sizes that build perfectly well."""
    with pytest.raises(ValueError, match="rapids_span"):
        _built(rapids_span=18, rapids_top=14)
    with pytest.raises(ValueError, match="rapids_top"):
        _built(rapids_span=30, rapids_top=4)
    with pytest.raises(ValueError, match=r"level for"):
        _built(rapids_span=23, rapids_top=7)
