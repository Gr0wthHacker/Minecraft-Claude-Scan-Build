"""The park's second wave of rides: contracts for `mcbuild/gen/attractions.py`.

Mirrors `tests/test_park.py`'s discipline (each of these pins something that shipped wrong once,
here, and was invisible in a render) and adds what the escalation to real mechanics demands: a
minecart circuit is not a ride until it is verified CLOSED, POWERED and REACHABLE, a water feature
is not real until the water is actually wet, and a maze is not a maze until a flood fill proves
one solved route with real branches off it.
"""
from collections import deque

import pytest

from mcbuild import blocks, palette, walk
from mcbuild.gen import attractions as A
from mcbuild.gen import coaster as C
from mcbuild.gen.park import LANDS, SIGN_WIDTH
from mcbuild.gen.vertical import World

KINDS = sorted(A.BUILDERS)
LAND_NAMES = sorted(LANDS)
FACINGS = ("east", "north", "west", "south")
RAIL_KINDS = ("teacups", "runawaymine", "ghosttrain")

# A rider, and the water simulator, both pass through these without being stopped by them.
_RIDER_PASSABLE = {"rail", "powered_rail", "lantern", "soul_lantern", "torch", "wall_torch",
                    "soul_torch", "oak_sign", "oak_wall_sign", "spruce_wall_sign",
                    "dark_oak_wall_sign", "ladder", "cobweb", "iron_bars", "end_rod"}


def _cfg(kind, land="midway", facing="east", **kw):
    cfg = {**A.ATTRACTIONS, "at": [0, 64, 0], "kind": kind, "land": land, "facing": facing,
           "title": kind.upper(), **kw}
    return cfg


def _built(kind, land="midway", facing="east", **kw):
    """The raw World and its meta, in WORLD coordinates - the canvas is sized to its own content
    and shifts between builds, which is why every assertion here works in world space."""
    p = {**A.ATTRACTIONS, **_cfg(kind, land, facing, **kw)}
    w = World()
    meta = A.BUILDERS[kind](w, p, None)
    return w, meta, p


def _components(w):
    cells = set(w.cells)
    seen, sizes = set(), []
    for start in cells:
        if start in seen:
            continue
        q, n = deque([start]), 0
        seen.add(start)
        while q:
            x, y, z = q.popleft()
            n += 1
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (x + d[0], y + d[1], z + d[2])
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        sizes.append(n)
    return sorted(sizes, reverse=True)


def _base(name):
    return (name or "").split("[")[0]


# ------------------------------------------------------------------ it builds, and it is legal

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LAND_NAMES)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_kind_builds_at_every_land_and_facing(kind, land, facing):
    c = A.build(_cfg(kind, land, facing))
    assert c.to_model().ids.size > 0


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LAND_NAMES)
def test_every_block_state_is_legal(kind, land):
    m = A.build(_cfg(kind, land)).to_model()
    for n in m.names:
        base = _base(n.split(":")[-1])
        if base == "air":
            continue
        spec = n.split(":")[-1]
        props = {}
        if "[" in spec:
            props = dict(kv.split("=", 1) for kv in spec[spec.index("[") + 1:-1].split(","))
        assert blocks.validate(base, props) == [], f"{spec} is not a legal state"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LAND_NAMES)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_kind_is_one_connected_piece(kind, land, facing):
    """The fault this whole file exists for, in a new hat: a chairoplane seat swung out on its
    own chain, a stepped cone roof built from four non-overlapping annuli, a lancet window carved
    into a pier one cell wide - every one shipped a clean-looking build and a floating fragment."""
    w, _meta, _p = _built(kind, land, facing)
    assert _components(w) == [len(w.cells)]


# ------------------------------------------------------------------ the economy

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LAND_NAMES)
def test_nothing_built_is_currency_or_expensive(kind, land):
    m = A.build(_cfg(kind, land)).to_model()
    for n in m.names:
        base = _base(n.split(":")[-1])
        if base == "air":
            continue
        assert blocks.spendable(base), f"{kind}/{land} places CURRENCY: {base}"
        assert blocks.available(base), f"{kind}/{land} places a block not on the 1.19 allowlist: {base}"
        assert palette.tier(base) != "expensive", f"{kind}/{land} places expensive: {base}"


# ------------------------------------------------------------------ signs

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LAND_NAMES)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_sign_has_a_block_behind_it_and_fits_the_line_width(kind, land, facing):
    w, _meta, _p = _built(kind, land, facing)
    assert w.signs, f"{kind} placed no sign at all at {land}/{facing}"
    for (x, y, z), t in w.signs.items():
        assert (x, y, z) in w.cells, f"{kind}: sign at {(x, y, z)} has no block of its own"
        for line in t["front"] + t["back"]:
            assert len(line) <= SIGN_WIDTH, f"{kind}: sign line {line!r} exceeds {SIGN_WIDTH}"


# --------------------------------------------------------------- stairs rotate with the frame

_ROT = {"east": "north", "north": "west", "west": "south", "south": "east"}


def _stair_facings(kind, land, facing):
    w, _meta, _p = _built(kind, land, facing)
    out = []
    for (name, props) in w.cells.values():
        if name.endswith("_stairs") and "facing" in props:
            out.append(props["facing"])
    return out


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LAND_NAMES)
def test_stair_facings_rotate_with_the_structure_rather_than_being_hardcoded(kind, land):
    """THE BUG THIS PINS: a trim run built with a literal `"north"` face string is legal at every
    facing (any cardinal validates) and WRONG at three of the four, because the moulding does not
    turn with the building. Rotating the whole structure 90 degrees must rotate every stair's
    `facing` by the same 90 degrees - checked by mapping the east-build's facings through the
    rotation and comparing the resulting multiset to the north-build's own.
    """
    east = sorted(_ROT[fc] for fc in _stair_facings(kind, land, "east"))
    north = sorted(_stair_facings(kind, land, "north"))
    if not east and not north:
        pytest.skip(f"{kind} places no stairs")
    assert east == north, (
        f"{kind}/{land}: stair facings did not rotate with the frame - "
        f"east->north gives {east}, actual north build is {north}")


# ------------------------------------------------------------------ walkability: a generic flood

def _walkable(w, pos):
    """Is a player-height cell open - present but rider-passable, or simply not built.

    Slabs and stairs are walkable-through (a bottom slab or a stair tread is exactly how a real
    ramp or a real step is built in this repo - the gangway and the flush froglight idiom both
    rest on it), which `fluids.PASSABLE` deliberately does not grant since water treats them as
    solid; a WALKER is not water.
    """
    n = w.name(*pos)
    if n is None:
        return True
    base = _base(n)
    return base in _RIDER_PASSABLE or base.endswith("_slab") or base.endswith("_stairs")


def _flood(w, start, bounds=None, max_steps=200000):
    """A feet+head flood that may STEP up or down by one course - the practical proxy this repo
    uses when a full 3D walker (`Nav` in the Java mod) is not available in Python. A one-block
    step is real player movement (a stair, a slab, a station platform one course above its own
    apron - `coaster._station`'s own convention, which several of these kinds reuse), so refusing
    it would fail a platform that is honestly walkable.
    """
    seen = {start}
    q = deque([start])
    steps = 0
    while q and steps < max_steps:
        steps += 1
        x, y, z = q.popleft()
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                n = (x + dx, y + dy, z + dz)
                if n in seen:
                    continue
                if bounds and not (bounds[0] <= n[0] <= bounds[3] and
                                    bounds[1] <= n[1] <= bounds[4] and
                                    bounds[2] <= n[2] <= bounds[5]):
                    continue
                if _walkable(w, n) and _walkable(w, (n[0], n[1] + 1, n[2])):
                    seen.add(n)
                    q.append(n)
    return seen


# ------------------------------------------------------------------ the three rail circuits

def _rail_cells(w):
    return {pos for pos, (name, _p) in w.cells.items() if _base(name) in ("rail", "powered_rail")}


def _props(w, pos):
    return w.cells[pos][1]


def _rail_cycle(w):
    """Walk the rail cells into ONE ordered cycle - possible only if every rail cell has exactly
    two rail-type neighbours, which is what a CLOSED loop with no branch and no dead end means.
    Raises loudly rather than returning a partial answer, because a partial cycle silently
    accepted is the exact "does nothing, quietly" failure this project keeps re-finding.

    **THE NEIGHBOUR SEARCH IS 3-D, and it was 2-D until these circuits started climbing.** A rail
    on a slope has its next cell one course UP, so a fixed-height walk sees a dead end at the foot
    of every hill and reports a perfectly good ride as broken - or worse, walks a subset of the
    loop and calls that closed. `dy` is allowed +-1 and no more, which is the game's own limit:
    an ascending rail climbs exactly one course.
    """
    cells = _rail_cells(w)
    nbrs = {}
    for (x, y, z) in cells:
        near = [(x + dx, y + dy, z + dz)
                for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)) for dy in (0, 1, -1)
                if (x + dx, y + dy, z + dz) in cells]
        assert len(near) == 2, f"rail cell {(x, y, z)} has {len(near)} rail neighbours, not 2 - " \
                               f"a closed loop must have no branch and no dead end"
        nbrs[(x, y, z)] = near
    start = next(iter(cells))
    order = [start]
    prev, cur = None, start
    while True:
        a, b = nbrs[cur]
        nxt = a if a != prev else b
        if nxt == start:
            break
        order.append(nxt)
        prev, cur = cur, nxt
    assert len(order) == len(cells), "the rail cells do not form a single closed cycle"
    return order


@pytest.mark.parametrize("kind", RAIL_KINDS)
@pytest.mark.parametrize("land", LAND_NAMES)
def test_the_rail_circuit_is_closed_GRADED_and_never_dead(kind, land):
    """**THIS TEST USED TO ASSERT THE CIRCUITS WERE FLAT, AND THAT WAS THE BUG.**

    It read `assert len(ys) == 1, "the circuit is not flat"` - a check that PINNED the fault the
    whole park was rejected for: *"the hollow rollercoaster which is just a circle feel pointless
    and weird filler"*. Every one of these three was a rectangle on one course, so a rider got in,
    went round once past nothing at one height, and arrived where they started. A test that pins a
    decision has to change when the decision does, or the suite quietly enforces the thing that was
    just rejected - which this repo has now written down about a frog's proportions, a casino's
    game list and a reference build's construction, and here it is a fourth time.

    So the assertion is inverted: a circuit must GO SOMEWHERE. And the three rules that make a
    graded circuit work in the world are checked with it, because every one of them is invisible in
    a render and fatal in game:

        NEVER DESCEND INTO A CORNER - a curve has no ascending state at all, so a corner and both
        of its neighbours must sit at one height. Drop into one and the game re-derives the turn as
        a slope, the turn is lost, and the line dead-ends.
        A SLOPE ASCENDS TOWARD ITS HIGHER NEIGHBOUR - `ascending_east` on the wrong cell of a pair
        is a legal state, draws identically in every render this repo owns, and does not connect.
        AN UNPOWERED powered_rail IS A BRAKE - every maximal run of straights carries a
        redstone_block at BOTH ends, counted between corners, because a plain rail does not
        propagate the chain.
    """
    w, meta, _p = _built(kind, land, "east")
    order = _rail_cycle(w)
    ys = [pos[1] for pos in order]

    assert len(set(ys)) > 1, (
        f"{kind}: the circuit is FLAT - {len(order)} cells on one course is a lap, not a ride")
    assert meta["rise"] == meta["fall"] >= 4, (
        f"{kind}: it rises {meta['rise']} and falls {meta['fall']}; a closed circuit must return "
        f"to its own station, and under four courses is a bump rather than a hill")
    assert max(ys) - min(ys) == meta["rise"], (
        f"{kind}: reports a rise of {meta['rise']} and spans {max(ys) - min(ys)} courses")

    def is_corner(pos):
        return _base(w.name(*pos)) == "rail"

    def bed_powered(pos):
        return _base(w.name(pos[0], pos[1] - 1, pos[2])) == "redstone_block"

    n = len(order)
    for j, pos in enumerate(order):
        if not is_corner(pos):
            continue
        a, b = order[(j - 1) % n], order[(j + 1) % n]
        assert a[1] == pos[1] == b[1], (
            f"{kind}: the corner at {pos} is entered from {a[1]} and left at {b[1]} - a curve has "
            f"no ascending state, so the game would re-derive it as a slope and lose the turn")

    # A SLOPE'S `shape` MUST NAME THE DIRECTION OF ITS HIGHER NEIGHBOUR.
    dirs = {(0, 1): "south", (0, -1): "north", (1, 0): "east", (-1, 0): "west"}
    for j, pos in enumerate(order):
        higher = [o for o in (order[(j - 1) % n], order[(j + 1) % n]) if o[1] > pos[1]]
        shape = _props(w, pos).get("shape")
        if not higher:
            assert not str(shape).startswith("ascending_"), (
                f"{kind}: {pos} is shaped {shape} with no higher neighbour to ascend toward")
            continue
        want = "ascending_" + dirs[(higher[0][0] - pos[0], higher[0][2] - pos[2])]
        assert shape == want, f"{kind}: the slope at {pos} is {shape}, and it climbs {want[10:]}"

    # every run of consecutive STRAIGHT (powered_rail) cells, cyclically
    runs, run = [], []
    start_corner = next(i for i in range(n) if is_corner(order[i]))
    seq = order[start_corner:] + order[:start_corner]
    for pos in seq:
        if is_corner(pos):
            if run:
                runs.append(run)
                run = []
            continue
        run.append(pos)
    if run:
        runs.append(run)
    assert runs, f"{kind}: no powered straight runs at all"
    for run in runs:
        assert bed_powered(run[0]) and bed_powered(run[-1]), (
            f"{kind}: run from {run[0]} to {run[-1]} is not powered at both ends - a dead rail")
    assert meta["track"] == len(order) == len(_rail_cells(w))


@pytest.mark.parametrize("kind", RAIL_KINDS)
@pytest.mark.parametrize("land", LAND_NAMES)
def test_every_elevated_rail_cell_is_carried_to_the_ground(kind, land):
    """A GRADED CIRCUIT CAN FLOAT AND A FLAT ONE CANNOT, which is why this test did not exist
    before. Every rail cell has a bed directly under it; an elevated stretch also needs PIERS
    carrying that bed down to the apron, or the ride is a ribbon hanging in the air with a clean
    audit and a clean bill of materials.

    **THE PROPERTY IS SPACING, NOT EVERY-COLUMN.** A pier under every elevated cell is a wall, not
    a trestle - it would brick up the alleys the Ghost Train's set pieces stand in and bury the
    Runaway Mine's spoil heaps. What must hold is that no run of elevated track goes further than
    `GAP` cells without a column reaching the ground, measured ALONG THE TRACK's own cycle. And it
    is measured rather than read off `meta["piers"]`, because a count of twelve says nothing about
    WHICH twelve and the failure mode is one unsupported corner.
    """
    GAP = 4
    w, meta, _p = _built(kind, land, "east")
    order = _rail_cycle(w)
    floor = min(pos[1] for pos in w.cells)
    for (x, y, z) in order:
        assert w.name(x, y - 1, z), f"{kind}: the rail at {(x, y, z)} has no bed under it"

    n = len(order)
    grounded = [all(w.has(x, h, z) for h in range(floor, y - 1)) for (x, y, z) in order]
    far = []
    for j, (x, y, z) in enumerate(order):
        if y - 1 <= floor:
            continue                                    # it stands on the apron already
        if not any(grounded[(j + k) % n] or grounded[(j - k) % n] for k in range(GAP + 1)):
            far.append((x, y, z))
    assert not far, (
        f"{kind}: {len(far)} elevated rail cell(s) further than {GAP} cells along the track from "
        f"any column that reaches the ground - e.g. {far[:3]}")


@pytest.mark.parametrize("kind", RAIL_KINDS)
@pytest.mark.parametrize("land", LAND_NAMES)
def test_the_boarding_platform_is_reachable_from_the_approach_ground(kind, land):
    """THE COASTER'S OWN FIRST MISTAKE, PINNED SO IT CANNOT HAPPEN HERE: a platform 228 cells
    wide, walled off from its own track, whose first test seeded the flood in the void and so
    never noticed. The flood starts at the module's own `boarding_at` - the approach point a
    park path would join - and must reach a real rail cell without being blocked by a wall.
    """
    w, meta, _p = _built(kind, land, "east")
    start = tuple(meta["boarding_at"])
    assert _walkable(w, start), f"{kind}: its own boarding_at is not walkable ground"
    reached = _flood(w, start)
    rails = _rail_cells(w)
    assert reached & rails, (
        f"{kind}: flood from {start} never reaches a rail cell - the platform is sealed off "
        f"from its own track")


@pytest.mark.parametrize("kind", RAIL_KINDS)
@pytest.mark.parametrize("land", LAND_NAMES)
@pytest.mark.parametrize("facing", FACINGS)
def test_the_ride_is_BOARDABLE_ON_FOOT_FROM_REAL_GROUND(kind, land, facing):
    """**THE SEED IS THE FAR CORNER OF THE MODULE'S OWN APRON, NOT THE PLATFORM.**

    The test above floods from `boarding_at` and proves the platform is not sealed off from its
    own track. It cannot say whether a visitor arriving off the zone's paving can GET to the
    platform, because it starts standing on it - and a flood seeded on the thing it means to
    prove reachable proves only that the thing exists. That is exactly how a coaster shipped a
    228-cell platform walled off from its track with a green test beside it.

    So: `mcbuild.walk`'s stated movement model (step up one, step down one, no falls, so every
    route it finds is reversible), seeded on the apron cell FURTHEST from the boarding point, and
    the seed region is asserted LARGE before anything is asked of it - a fill that never left its
    own cell would otherwise satisfy every question put to it.

    The one thing it deliberately does not claim: that the CART completes the lap. There is no
    cart-physics model in this repo, so what a ride can honestly promise is that it is closed,
    powered, unobstructed and that a player can walk up to it and get in.
    """
    w, meta, _p = _built(kind, land, facing)
    cells = {pos: name for pos, (name, _pr) in w.cells.items()}
    board = tuple(meta["boarding_at"])
    floor = min(pos[1] for pos in cells)

    stands = [(x, y, z) for (x, y, z) in
              {(px, floor + 1, pz) for (px, _py, pz) in cells}
              if walk.stands(cells, (x, y, z))]
    assert stands, f"{kind}/{facing}: the module laid no standable ground at all"
    seed = max(stands, key=lambda c: (c[0] - board[0]) ** 2 + (c[2] - board[2]) ** 2)

    got = walk.reachable(cells, seed)
    assert len(got) >= 120, (
        f"{kind}/{facing}: the walk from {seed} covers {len(got)} cells - that is a seed stuck in "
        f"its own cell, not a route across the ride's apron")
    assert board in got or any(abs(board[0] - c[0]) + abs(board[1] - c[1]) +
                               abs(board[2] - c[2]) <= 1 for c in got), (
        f"{kind}/{facing}: you cannot walk from the ground at {seed} to the boarding point "
        f"{board} - the platform is cut off from the park")
    rails = {pos for pos, n in cells.items() if _base(n) in ("rail", "powered_rail")}
    assert got & rails, (
        f"{kind}/{facing}: the walk never reaches a rail cell - there is no way to get INTO a "
        f"cart from the ground")


# ------------------------------------------------------------------ riverboat

def test_the_mooring_pool_is_real_water_on_a_sealed_bed():
    """Real, not decorative: every water cell is a SOURCE, sitting on a solid bed, with a solid
    wall on every side that is not open water or the hull - `coaster._seal`'s own rule, checked
    directly against the build rather than assumed from the code that placed it."""
    w, _meta, _p = _built("riverboat", "frontier", "east")
    water = [pos for pos, (name, _pr) in w.cells.items() if name == "water"]
    assert water, "no water was placed at all"
    for (x, y, z) in water:
        assert w.cells[(x, y, z)][1].get("level") == "0", f"{(x, y, z)} is not a source"
        below = w.name(x, y - 1, z)
        assert below and below != "water" and _base(below) != "air", \
            f"water at {(x, y, z)} has no solid bed"
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            side = (x + dx, y, z + dz)
            sname = w.name(*side)
            assert sname is not None, f"water at {(x, y, z)} leaks into open air at {side}"


def test_the_gangway_is_a_real_walkable_route_to_the_deck():
    w, meta, _p = _built("riverboat", "frontier", "east")
    bottom = tuple(meta["gangway_bottom"])
    top = tuple(meta["gangway_top"])
    reached = _flood(w, bottom)
    # the flood is 2D at fixed height; the gangway itself climbs, so walk it explicitly cell by
    # cell instead and confirm every step is open both at foot and head height.
    from mcbuild.gen.attractions import _ortho_path
    path = _ortho_path(bottom, top)
    for pos in path:
        assert _walkable(w, pos), f"gangway blocked at {pos}"
        assert _walkable(w, (pos[0], pos[1] + 1, pos[2])), f"gangway headroom blocked at {pos}"


# ------------------------------------------------------------------ mirror maze

@pytest.mark.parametrize("land", LAND_NAMES)
def test_the_maze_has_one_solved_route_and_real_dead_ends(land):
    """A REAL MAZE, NOT A CORRIDOR WITH TWO DOORS: the spanning tree that generated it has at
    least one branch (a node of degree >= 3) and at least one dead end (a leaf, degree 1) beyond
    the entrance and exit themselves - and separately, a flood fill over the ACTUAL BUILT cells
    proves the entrance and exit are really connected, which the tree alone only promises."""
    p = _cfg("mirrormaze", land, "east")
    nc, nd, seed = p["maze_w"], p["maze_d"], p["seed"]
    edges = A._maze_edges(nc, nd, seed)
    degree = {}
    for e in edges:
        for node in e:
            degree[node] = degree.get(node, 0) + 1
    assert any(d >= 3 for d in degree.values()), "no branch point - this is a single corridor"
    assert sum(1 for d in degree.values() if d == 1) >= 2, "no real dead ends off the solved route"

    w, meta, _p = _built("mirrormaze", land, "east")
    entry = tuple(meta["entry_at"])
    exitc = tuple(meta["exit_at"])
    reached = _flood(w, entry)
    assert exitc in reached, "the entrance does not reach the exit through the built maze"


# ------------------------------------------------------------------ per-kind contract sanity

@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_states_a_contract(kind):
    _w, meta, _p = _built(kind, "midway", "east")
    assert meta.get("contract"), f"{kind} has no stated contract"


def test_swings_every_seat_hangs_from_a_chain_reaching_the_crown():
    """Architecture, not a ride - but the one thing that must never ship is a seat with a broken
    chain, since that is invisible in a render and obvious the moment someone looks up."""
    w, meta, _p = _built("swings", "midway", "east")
    assert meta["seats"] >= 6
    # every iron_chain cell must have at least one 6-connected chain/post/full-block neighbour -
    # already guaranteed by the whole-structure connectivity test, so this pins the COUNT instead:
    # a seat lost off its own chain silently drops the seat count without breaking connectivity.
    chains = sum(1 for (name, _p2) in w.cells.values() if name == "iron_chain")
    assert chains >= meta["seats"], "fewer chain cells than seats - at least one seat is unlinked"


# ------------------------------------------------- nothing stands on, or over, a rider

RIDE_KINDS = [("teacups", "midway"), ("runawaymine", "frontier"), ("ghosttrain", "hollow")]


@pytest.mark.parametrize("kind,land", RIDE_KINDS)
@pytest.mark.parametrize("facing", ["east", "north", "west", "south"])
def test_no_rider_passes_under_or_into_a_solid_block(kind, land, facing):
    """**A POST RESTING ON A RAIL DRAWS EXACTLY LIKE A POST RESTING ON THE GROUND.**

    The teacups' six canopy posts were sited at a radius that put four of them on the loop's own
    rectangle. The loop is laid afterwards, so it overwrote each post's ground cell with rail and
    left the post standing in the course above - a rider hits a log at speed. Every check passed:
    legal states, one connected piece, a closed powered circuit with no dead rails, and the
    footprint measured correctly. The Ghost Train had the same bug worse, with a solid block over
    eleven of its fifty track cells, which is a suffocation tunnel rather than a collision.

    So this asks the one question none of those checks does: is the cell a rider OCCUPIES clear?
    """
    import numpy as np
    c = A.build({"kind": kind, "land": land, "at": [0, 64, 0], "facing": facing})
    cells = {}
    ys, zs, xs = np.nonzero(c.ids)
    for y, z, x in zip(ys, zs, xs):
        cells[(int(x), int(y), int(z))] = c.get_name(int(x), int(y), int(z))
    rail = [pos for pos, n in cells.items() if "rail" in n]
    assert rail, f"{kind}: no track at all"
    blocked = []
    for (x, y, z) in rail:
        # **TWO COURSES, NOT ONE.** A rider in a minecart occupies the rail's own cell and the one
        # over it, and a check that looked one course up would pass a build whose SECOND course
        # was solid - a head in a ceiling at speed rather than a suffocation: different symptom,
        # same invisible cause. It matters more now that every circuit climbs, because a leg
        # passing over another part of the same ride is a real possibility and nothing else here
        # would catch it.
        for k in (1, 2):
            over = (cells.get((x, y + k, z)) or "air").split("[")[0].split(":")[-1]
            if over not in A._RIDER_THROUGH:
                blocked.append(((x, y, z), k, over))
    assert not blocked, (
        f"{kind} facing {facing}: {len(blocked)} track cell(s) with something solid in the "
        f"rider - e.g. {blocked[:3]}")


# THE COASTER LIVES IN A SEPARATE MODULE (`mcbuild/gen/coaster.py`) and builds its own track by
# hand rather than through `attractions._Circuit`, so the rule above never covered it. It shipped
# the same failure anyway: `out/Mine Coaster.litematic` carried a `spruce_stairs` two courses over
# an ASCENDING rail cell at (97615, 207, 80386) - the lift hill climbs back through the station's
# own footprint, and the canopy's fixed `ceil` had no idea the track was there. `coaster._roofable`
# is the fix and `coaster._rail_clearance` is the same self-check `_Circuit.verify` makes, run
# against `coaster.py`'s own track - this is that same contract, asserted from outside too, at
# every land and facing rather than only the one shipped design that happened to fail.
COASTER_KINDS = [("coaster", "midway"), ("coaster", "frontier"), ("coaster", "hollow")]


@pytest.mark.parametrize("kind,land", COASTER_KINDS)
@pytest.mark.parametrize("facing", ["east", "north", "west", "south"])
def test_no_rider_passes_under_or_into_a_solid_block_on_the_coaster(kind, land, facing):
    import numpy as np
    # span/top MATCH THE SHIPPED RIDE (`configs/mine_coaster.yaml`) - the default span (58) and
    # top (45) do not reproduce the bug at all, because it depends on the lift hill's own profile
    # landing back inside the station's footprint at a height the fixed canopy did not expect.
    c = C.build({"kind": kind, "land": land, "at": [0, 100, 0], "facing": facing,
                 "span": 44, "top": 34})
    cells = {}
    ys, zs, xs = np.nonzero(c.ids)
    for y, z, x in zip(ys, zs, xs):
        cells[(int(x), int(y), int(z))] = c.get_name(int(x), int(y), int(z))
    rail = [pos for pos, n in cells.items() if "rail" in n]
    assert rail, f"{kind}: no track at all"
    blocked = []
    for (x, y, z) in rail:
        # TWO COURSES, NOT ONE - see the rail-loop version of this test above; the reported bug
        # was in the SECOND course, which a one-course check would have missed entirely.
        for k in (1, 2):
            over = (cells.get((x, y + k, z)) or "air").split("[")[0].split(":")[-1]
            if over not in C._RIDER_THROUGH:
                blocked.append(((x, y, z), k, over))
    assert not blocked, (
        f"{kind}/{land} facing {facing}: {len(blocked)} track cell(s) with something solid in "
        f"the rider - e.g. {blocked[:3]}")
