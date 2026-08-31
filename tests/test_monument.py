"""The grand centre monument's contracts.

Two of these pin bugs that shipped once during this file's own development and were invisible in
every other check: a stair rung with its facing backwards (our renderer draws both directions
identically, so this is the stairhead rule, applied to a spiral instead of a flight) and thirty-
nine floating treads (a flood test seeded in the void proves nothing - the axolotl's own lesson -
so this one is seeded from a real ground cell and the reached region is measured, not assumed).
"""
from collections import deque

import pytest

from mcbuild import blocks, palette
from mcbuild.gen import GENERATORS, monument
from mcbuild.gen.vertical import World

LANDS = sorted(monument.LANDS)
FACINGS = ("east", "north", "west", "south")

# world-axis unit step per compass name, so a tread's `facing` can be checked against where its
# neighbour actually landed, rather than trusted because it looks like a compass word.
_STEP = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def _cfg(land="midway", facing="east", **kw):
    return {**monument.MONUMENT, "at": [0, 64, 0], "land": land, "facing": facing,
            "title": "THE FOUNDERS", **kw}


def _built(land="midway", facing="east", **kw):
    """The raw World and meta, in WORLD coordinates - the same discipline `test_park.py` uses,
    because the canvas is sized to its own content and shifts between two builds."""
    p = _cfg(land, facing, **kw)
    w = World()
    meta = monument.BUILDERS["monument"](w, p, None)
    return w, monument._Frame(p), monument.LANDS[land], p, meta


def _reachable(cells, seed):
    seen = {seed}
    q = deque([seed])
    while q:
        x, y, z = q.popleft()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + dx, y + dy, z + dz)
            if n in cells and n not in seen:
                seen.add(n)
                q.append(n)
    return seen


# ------------------------------------------------------------------ it builds, and it is legal

@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_it_builds_and_is_tall_enough(land, facing):
    c = GENERATORS["monument"].build(_cfg(land, facing), None)
    assert c.to_model().ids.size > 0
    assert c.meta["height"] >= monument.MIN_HEIGHT


@pytest.mark.parametrize("land", LANDS)
def test_every_block_state_is_legal(land):
    m = GENERATORS["monument"].build(_cfg(land), None).to_model()
    for n in m.names:
        spec = n.split(":")[-1]
        base = spec.split("[")[0]
        if base == "air":
            continue
        props = {}
        if "[" in spec:
            props = dict(kv.split("=", 1) for kv in spec[spec.index("[") + 1:-1].split(","))
        assert blocks.validate(base, props) == [], f"{spec} is not a legal state"


@pytest.mark.parametrize("land", LANDS)
def test_nothing_built_is_currency_or_expensive(land):
    m = GENERATORS["monument"].build(_cfg(land), None).to_model()
    for n in m.names:
        base = n.split(":")[-1].split("[")[0]
        if base == "air":
            continue
        assert blocks.spendable(base), f"{land} places CURRENCY: {base}"
        assert blocks.available(base), f"{land} places a block off the 1.19 allowlist: {base}"
        assert palette.tier(base) != "expensive", f"{land} places expensive: {base}"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_the_whole_monument_is_one_connected_piece(land, facing):
    """The generic version of the flood test below - every cell reachable from every other,
    which is the property a printer needs and the property the climb-specific test below only
    samples one path through."""
    w, f, _pal, _p, _meta = _built(land, facing)
    cells = set(w.cells)
    seed = next(iter(cells))
    assert _reachable(cells, seed) == cells


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_sign_has_a_block_and_a_support_behind_it(land, facing):
    from mcbuild.gen.park import _STEP as WORLD_STEP
    w, _f, _pal, _p, _meta = _built(land, facing)
    for (x, y, z) in w.signs:
        assert (x, y, z) in w.cells, "sign TEXT with no sign BLOCK is a corrupt region"
        _name, props = w.cells[(x, y, z)]
        fdx, fdz = WORLD_STEP[props["facing"]]
        assert (x - fdx, y, z - fdz) in w.cells, f"sign at {(x, y, z)} has no support behind it"


def test_no_sign_line_is_wider_than_the_sign():
    w, _f, _pal, _p, _meta = _built(title="A VERY LONG MONUMENT NAME INDEED FOR SURE")
    for t in w.signs.values():
        for line in list(t["front"]) + list(t["back"]):
            assert len(line) <= monument.SIGN_WIDTH, f"{line!r} clips"


# ------------------------------------------------------------------ the climb is real

def test_the_climb_reaches_the_minimum_length():
    _w, _f, _pal, _p, meta = _built()
    assert meta["climb_length"] >= monument.MIN_CLIMB


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_the_gallery_is_reachable_from_real_ground(land, facing):
    """THE FLOOD, SEEDED FROM GROUND, NOT FROM THE VOID. `Island Night`'s and the ladybird's own
    lesson: a walkable-region test that seeds itself in open air proves nothing, because an empty
    region is trivially "connected" to nothing at all. This seeds from the monument's own paved
    apron - the literal plaza a visitor stands on - and the reached region is asserted LARGE
    before anything about the gallery is trusted, exactly as CLAUDE.md's own precedent for this
    class of test insists.
    """
    w, f, _pal, p, meta = _built(land, facing)
    cells = set(w.cells)
    c = monument.PAD_R
    ground = f.at(c, c, -1)                      # the plaza floor, dead centre of the apron
    assert ground in cells, "the seed itself is not real ground - the test proves nothing"
    reached = _reachable(cells, ground)
    assert len(reached) > 2000, f"the reachable region is only {len(reached)} cells - too small " \
                                 "to trust a claim about it reaching the gallery"

    gal_h = p["at"][1] + meta["gallery_height"]
    gallery = [pos for pos in cells if pos[1] == gal_h]
    assert len(gallery) > 20, "the gallery floor did not build"
    assert all(pos in reached for pos in gallery), \
        "the viewing gallery exists but is NOT reachable from the ground - a climb that does " \
        "not connect is a monument that lied on its own plaque"


def test_the_climb_treads_are_a_real_path_not_a_scatter():
    """Every tread the build actually placed is walked in order and checked against the geometry
    it claims: consecutive treads are exactly one course apart in height (never a jump, never
    flat), and the horizontal step between them is exactly one cell - which is what makes the
    riser between them (see `monument._turret`'s own docstring) able to touch both."""
    _w, _f, _pal, _p, meta = _built()
    treads = meta["climb_treads"]
    assert len(treads) == meta["climb_length"]
    for (a, _fa), (b, _fb) in zip(treads, treads[1:]):
        dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        assert dy == 1, f"tread pair {a}->{b} does not rise exactly one course"
        assert abs(dx) + abs(dz) == 1, f"tread pair {a}->{b} steps more than one cell over"


def test_a_flight_that_ascends_toward_d_has_every_tread_facing_d():
    """THE STAIR RULE, off `tests/test_stairhead.py`: 'a flight that ascends toward D has every
    tread facing=D, half=bottom.' Our renderer draws a stair facing either way identically, so a
    backwards tread audits clean, costs nothing, and cannot be walked up - the same failure this
    project pinned once already, here checked against a winding stair rather than a straight one.

    Each tread's recorded facing is checked against the WORLD-COORDINATE direction of the very
    next tread, which is the direction you are actually walking as you climb off it.
    """
    _w, _f, _pal, _p, meta = _built()
    treads = meta["climb_treads"]
    for (a, face), (b, _fb) in zip(treads, treads[1:]):
        dx, dz = b[0] - a[0], b[2] - a[2]
        assert (dx, dz) in _STEP.values(), f"tread step {a}->{b} is not a single compass step"
        assert _STEP[face] == (dx, dz), \
            f"tread at {a} faces {face} but the next tread is {(dx, dz)} away"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_tread_is_half_bottom_and_shape_straight(land, facing):
    w, _f, _pal, _p, meta = _built(land, facing)
    for pos, _face in meta["climb_treads"]:
        name, props = w.cells[pos]
        assert props.get("half") == "bottom"
        assert props.get("shape") == "straight"


def test_the_gallery_has_a_rail_gap_where_the_bridge_lands():
    """THE GAP IS LEFT BY THE LOOP, never punched afterwards - the void tower's own rule, and
    `_gallery`'s own docstring states it. If the loop ever "fixes" itself by filling the ring
    solid and cutting a hole in a second pass, the bridge silently walks into a wall."""
    w, f, _pal, _p, meta = _built()
    c = monument.PAD_R
    gap = f.at(c, c + monument.GAL_R, meta["gallery_height"])
    assert gap in w.cells, "the bridge floor should occupy the gap cell"
    name, _props = w.cells[gap]
    assert "wall" not in name, "the balustrade was not actually left open at the bridge"


# ------------------------------------------------------------------ the detail vocabulary

_DETAIL_SUFFIXES = ("_stairs", "_slab", "_trapdoor", "_fence", "_fence_gate", "_wall", "_pane")


def _detail_fraction(land):
    m = GENERATORS["monument"].build(_cfg(land), None).to_model()
    total = detail = 0
    for i, n in enumerate(m.names):
        base = n.split(":")[-1].split("[")[0]
        if base == "air":
            continue
        k = int((m.ids == i).sum())
        total += k
        if base.endswith(_DETAIL_SUFFIXES):
            detail += k
    return detail / total


@pytest.mark.parametrize("land", LANDS)
def test_the_detail_vocabulary_clears_the_measured_floor(land):
    """CLAUDE.md's own corpus measurement: outside sculpture runs ~17% detail blocks, and this
    project's own builds have run as low as 0.5%. The monument was 12.9% before the climb was
    added (stairs, slabs, fences and a wall now do real structural work rather than sitting only
    in the mouldings) and is asserted here so the next refactor cannot quietly regress it."""
    frac = _detail_fraction(land)
    assert frac >= 0.14, f"{land} detail fraction is {frac:.3f}, below the measured floor"


# ------------------------------------------------------------------ the value ladder

def test_the_wall_and_trim_are_a_real_value_step_in_every_land():
    """CLAUDE.md records THREE separate wrong conclusions that 'this economy has no value
    contrast', each one from measuring luminance INSIDE one material family. Measured ACROSS
    families the gap is real - this asserts it directly with `blocks.color` rather than trusting
    the prose, so a future land added to `park.LANDS` with too little contrast fails here instead
    of shipping a monument with an invisible moulding line."""
    def lum(rgb):
        r, g, b = rgb
        return 0.299 * r + 0.587 * g + 0.114 * b

    for land in LANDS:
        pal = monument.LANDS[land]
        wall = blocks.color(pal["wall"], "side") or blocks.color(pal["wall"], "top")
        trim = blocks.color(pal["trim"], "side") or blocks.color(pal["trim"], "top")
        assert wall is not None and trim is not None
        gap = abs(lum(wall) - lum(trim))
        assert gap >= 15, f"{land}: wall/trim luminance gap is only {gap:.1f}"
