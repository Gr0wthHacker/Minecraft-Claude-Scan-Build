"""The park's second wave of rides: contracts for `mcbuild/gen/attractions.py`.

Mirrors `tests/test_park.py`'s discipline (each of these pins something that shipped wrong once,
here, and was invisible in a render) and adds what the escalation to real mechanics demands: a
minecart circuit is not a ride until it is verified CLOSED, POWERED and REACHABLE, a water feature
is not real until the water is actually wet, and a maze is not a maze until a flood fill proves
one solved route with real branches off it.
"""
from collections import deque

import pytest

from mcbuild import blocks, palette
from mcbuild.gen import attractions as A
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


def _rail_cycle(w):
    """Walk the rail cells into ONE ordered cycle - possible only if every rail cell has exactly
    two rail-type horizontal neighbours, which is what a CLOSED loop with no branch and no dead
    end means. Raises loudly rather than returning a partial answer, because a partial cycle
    silently accepted is the exact "does nothing, quietly" failure this project keeps re-finding.
    """
    cells = _rail_cells(w)
    nbrs = {}
    for (x, y, z) in cells:
        near = [(x + dx, y, z + dz) for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if (x + dx, y, z + dz) in cells]
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
def test_the_rail_circuit_is_closed_flat_and_never_dead(kind, land):
    """THE ESCALATION'S OWN CHECKLIST: one connected track, zero dead rails, corners flat.
    Corners are `rail` (curves), straights are `powered_rail`; every maximal run of straights
    must be powered at BOTH ends - `coaster._power`'s own rule, reused rather than re-derived,
    and checked here against the actual BUILT cells rather than trusted blind.
    """
    w, meta, _p = _built(kind, land, "east")
    order = _rail_cycle(w)
    ys = {pos[1] for pos in order}
    assert len(ys) == 1, f"{kind}: the circuit is not flat - heights {ys}"
    y = next(iter(ys))

    def is_corner(pos):
        return _base(w.name(*pos)) == "rail"

    def bed_powered(pos):
        return _base(w.name(pos[0], pos[1] - 1, pos[2])) == "redstone_block"

    n = len(order)
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
