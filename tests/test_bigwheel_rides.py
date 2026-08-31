"""THE THREE RIDES, AND WHETHER THEY ACTUALLY CARRY A PLAYER.

Every assertion here pins something that produces A CLEAN AUDIT AND A BROKEN RIDE. That is the
whole reason the file exists: `audit` answers whether every block state is legal, supported,
affordable and in 1.19, and a schematic can pass all four while being a water shaft that drains
onto the platform, a chute with a block in it, or a circle of rail a minecart stops halfway round.
None of those is visible in any render this repo owns.

The chain each ride is proved against, end to end:

    WHEEL / DROP    walk from real ground to the pool -> swim to the foot of the column ->
                    the column is water, sealed, and unbroken to the deck -> step out onto the
                    deck -> the chute below the deck is clear -> the fall ends in water
    CAROUSEL        walk from real ground to the boarding rail -> the circuit is ONE simple cycle
                    -> every corner is a plain rail and flat -> every powered rail is reached by
                    a source ON ITS OWN RUN -> zero dead rails

and two properties that are about the tools rather than the builds: the registry fact the whole
rail design turns on, and that the leak guard is not vacuous - a check that cannot fail is worse
than no check, because it is counted.
"""
import json
import os
import sys
from collections import Counter, deque

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import blocks, fluids, palette                          # noqa: E402
from mcbuild.gen import bigwheel                                     # noqa: E402
from mcbuild.gen.vertical import World                               # noqa: E402

KINDS = ("wheel", "drop", "carousel")
LANDS = ("midway", "frontier", "hollow")
FACINGS = ("east", "north", "west", "south")

CURVES = {"south_east", "south_west", "north_west", "north_east"}

# What a PLAYER passes through. Deliberately short and separate from `fluids.PASSABLE`: a glass
# pane stops a body and a fence stops one too, while water does not - and the two questions have
# different answers often enough that sharing one list would quietly make a wall walkable.
WALK_THROUGH = {
    "air", "water", "rail", "powered_rail", "detector_rail", "activator_rail",
    "lantern", "soul_lantern", "torch", "soul_torch", "wall_torch", "ladder", "vine",
    "oak_wall_sign", "spruce_wall_sign", "dark_oak_wall_sign", "oak_sign", "spruce_sign",
    "dark_oak_sign", "oak_fence_gate", "spruce_fence_gate", "dark_oak_fence_gate",
}


# ------------------------------------------------------------------ harness

def _params(kind, land="midway", facing="east", **kw):
    p = {**bigwheel.RIDES, "at": [0, 64, 0], "kind": kind, "land": land, "facing": facing,
         "title": kind.upper()}
    p.update(kw)
    return p


def _built(kind, land="midway", facing="east", **kw):
    """The raw World plus the builder's own meta.

    Asserted in WORLD coordinates, never canvas ones: the canvas is sized to its own content, so
    it shifts between two builds with different settings and anything comparing them lines up
    against nothing.
    """
    p = _params(kind, land, facing, **kw)
    w = World()
    meta = bigwheel.BUILDERS[kind](w, p, None)
    return w, meta


@pytest.fixture(scope="module")
def wheel():
    return _built("wheel")


@pytest.fixture(scope="module")
def drop():
    return _built("drop")


@pytest.fixture(scope="module")
def carousel():
    return _built("carousel")


def _name(w, p):
    return w.name(*p)


def _solid(w, p):
    """Anything a body or a fluid cannot pass. Absent is air, which is neither."""
    n = _name(w, p)
    return bool(n) and n.split("[")[0] not in fluids.PASSABLE


def _components(cells):
    cells = set(cells)
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
                o = (x + d[0], y + d[1], z + d[2])
                if o in cells and o not in seen:
                    seen.add(o)
                    q.append(o)
        sizes.append(n)
    return sorted(sizes, reverse=True)


def _walkable(w, seed, limit=400000):
    """Every cell a player can STAND in, flooded from `seed`.

    Two courses of clearance, a solid support underfoot, and a step of at most one course up or
    down - which is what a player can do without jumping down a hole or clipping a lintel. Seeded
    from REAL GROUND, because a flood seeded in the void reports a region that proves nothing:
    this repo shipped a 228-cell platform walled off from its own track and the test written for
    it passed vacuously for exactly that reason.
    """
    def stands(p):
        x, y, z = p
        if _solid(w, p) or _solid(w, (x, y + 1, z)):
            return False
        return _solid(w, (x, y - 1, z))

    assert stands(seed), "the flood was seeded somewhere a player cannot stand: %s (%s under it)" \
                         % (seed, _name(w, (seed[0], seed[1] - 1, seed[2])))
    seen = {seed}
    q = deque([seed])
    while q and len(seen) < limit:
        x, y, z = q.popleft()
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                o = (x + dx, y + dy, z + dz)
                if o in seen or not stands(o):
                    continue
                if dy == 1 and _solid(w, (x, y + 2, z)):
                    continue                    # no headroom to step up
                seen.add(o)
                q.append(o)
    return seen


def _water_body(w, seed):
    """The 6-connected body of water reachable from `seed`. A swim, not a walk."""
    if _name(w, seed) != "water":
        return set()
    seen, q = {seed}, deque([seed])
    while q:
        x, y, z = q.popleft()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            o = (x + d[0], y + d[1], z + d[2])
            if o not in seen and _name(w, o) == "water":
                seen.add(o)
                q.append(o)
    return seen


# ------------------------------------------------------------------ the game's own rules

def test_a_powered_rail_has_no_curved_shape():
    """The registry fact the carousel's whole cost model turns on, read rather than remembered.

    If this ever fails the corners could be gold and the iron argument evaporates - and, far worse,
    a curved powered rail would be a legal state, so nothing downstream would notice.
    """
    db = json.load(open(os.path.join("mcbuild", "data", "blocks.json"), encoding="utf-8"))
    assert CURVES & set(db["rail"]["props"]["shape"]) == CURVES
    assert not CURVES & set(db["powered_rail"]["props"]["shape"])


def test_soul_sand_and_water_are_spendable_and_in_1_19():
    """A ride made of a block the server does not have is a design nobody can build. Soul sand is
    the one block in this module that came in for the RIDE rather than for the look."""
    for n in ("water", "soul_sand", "rail", "powered_rail", "redstone_block"):
        assert blocks.available(n), n
        assert blocks.spendable(n), "%s is currency here" % n
        assert palette.tier(n) in ("cheap", "ok"), (n, palette.tier(n))


# ------------------------------------------------------------------ the carousel's circuit

def test_the_circuit_is_one_simple_cycle_and_every_rail_cell_exists(carousel):
    """**A TRACK CELL IS NOT OPTIONAL.** A rail quietly skipped for a fence post or a mount's pole
    is a dead end, and the design still audits as one connected solid with a correct bill of
    materials. Walked cell to cell rather than counted."""
    w, meta = carousel
    path = [tuple(c) for c in meta["rail_path"]]
    assert len(path) == meta["track"] == 80
    assert len(set(path)) == len(path), "the circuit visits a cell twice"
    for c in path:
        n = _name(w, c)
        assert n in ("rail", "powered_rail"), "track cell %s holds %s" % (c, n)
    # consecutive, and it closes
    for a, b in zip(path, path[1:] + path[:1]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) == 1, \
            "the circuit jumps from %s to %s" % (a, b)
    # and no cell has a THIRD rail neighbour, which is what makes the game connect it the way the
    # path says rather than by its own priority
    s = set(path)
    for c in path:
        deg = sum(1 for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1))
                  if (c[0] + d[0], c[1] + d[1], c[2] + d[2]) in s)
        assert deg == 2, "track cell %s has %d rail neighbours" % (c, deg)
    assert _components(path) == [len(path)], "the circuit is not one piece"


def test_every_corner_is_a_plain_rail_and_every_straight_is_powered(carousel):
    w, meta = carousel
    path = [tuple(c) for c in meta["rail_path"]]
    corners = set(meta["rail_corners"])
    assert len(corners) == meta["corners"] > 0
    for j, c in enumerate(path):
        st = w.cells[c]
        name, props = st[0], st[1]
        if j in corners:
            assert name == "rail", "corner %d is a %s, which cannot curve" % (j, name)
            assert props["shape"] in CURVES, "corner %d emitted %s" % (j, props["shape"])
        else:
            assert name == "powered_rail", "straight %d is a %s" % (j, name)
            assert props["shape"] not in CURVES


def test_no_corner_is_ever_on_a_slope(carousel):
    """A curve has no ascending state. Drop into a corner and the game re-derives the turn as a
    slope: the turn is lost, the line dead-ends, and nothing in the model, the audit or the BOM
    looks wrong. The carousel's circuit is level, so this is the strongest form of the rule -
    a corner AND both its neighbours share one height, everywhere."""
    _w, meta = carousel
    path = [tuple(c) for c in meta["rail_path"]]
    n = len(path)
    for j in meta["rail_corners"]:
        for k in (j - 1, j, (j + 1) % n):
            assert path[k][1] == path[j][1], \
                "corner %d has a neighbour at y=%d - the game would slope it" % (j, path[k][1])


def test_no_rail_carries_an_ascending_shape_on_a_level_circuit(carousel):
    """The other half of the same rule. A level track that emits `ascending_*` anywhere is a track
    whose shapes were not derived from its own neighbours."""
    w, meta = carousel
    for c in (tuple(q) for q in meta["rail_path"]):
        assert not w.cells[c][1]["shape"].startswith("ascending_"), c


def test_the_shape_rule_puts_the_ascending_state_on_the_LOWER_cell():
    """Pinned on a synthetic ramp, because the carousel is flat and would never exercise it.

    Our renderer draws an ascending rail identically whichever way it points, and so does every
    orthographic view in this repo - the same blind spot the stair convention has. `coaster._shapes`
    is the one implementation; a second one here would drift from it.
    """
    from mcbuild.gen.coaster import _shapes
    cells = [(0, 64, 0), (1, 64, 0), (2, 65, 0), (3, 65, 0)]
    got = _shapes(cells, set(), False)
    assert got[1] == "ascending_east", got          # the low cell points at the high one
    assert got[2] == "east_west"


def test_every_powered_rail_is_reached_by_a_source_on_its_own_run(carousel):
    """**AN UNPOWERED POWERED_RAIL IS A BRAKE**, and a plain rail does not carry the power chain -
    so a source on the far side of a corner powers nothing. RUNS are what must be covered, never
    distance along the circuit, and a flat spacing leaves a dead rail past every single turn."""
    w, meta = carousel
    path = [tuple(c) for c in meta["rail_path"]]
    corners = set(meta["rail_corners"])
    sources = {tuple(c) for c in meta["rail_power"]}
    every = int(bigwheel.RIDES["power_every"])

    # a source is a redstone_block in the BED, one course under its rail
    powered_ix = set()
    for j, c in enumerate(path):
        if (c[0], c[1] - 1, c[2]) in sources:
            powered_ix.add(j)
    for c in sources:
        assert _name(w, c) == "redstone_block", "%s is %s, not a source" % (c, _name(w, c))

    from mcbuild.gen.coaster import _runs
    dead = []
    for a, b in _runs(len(path), corners):
        on_run = sorted(j for j in powered_ix if a <= j < b)
        assert on_run, "run %d..%d has no source at all - every rail in it is a brake" % (a, b)
        assert on_run[0] == a and on_run[-1] == b - 1, \
            "run %d..%d is not powered at both ends" % (a, b)
        for lo, hi in zip(on_run, on_run[1:]):
            if hi - lo > every:
                dead.append((lo, hi))
    assert not dead, "gaps longer than %d rails between sources: %s" % (every, dead[:3])
    # ...and every source is under a rail of the circuit, which is the same statement from the
    # other end: a redstone block anywhere else is nine redstone powering nothing.
    assert len(powered_ix) == len(sources) == meta["sources"]
    assert set(range(len(path))) - corners == {j for a, b in _runs(len(path), corners)
                                               for j in range(a, b)}


def test_a_power_source_never_lands_under_a_corner(carousel):
    """A redstone block under a plain rail powers nothing and wastes nine redstone."""
    _w, meta = carousel
    path = [tuple(c) for c in meta["rail_path"]]
    beds = {(c[0], c[1] - 1, c[2]): j for j, c in enumerate(path)}
    for c in (tuple(q) for q in meta["rail_power"]):
        assert beds[c] not in set(meta["rail_corners"])


def test_every_rail_stands_on_a_solid_bed(carousel):
    """A rail with nothing under it is not placeable, and the audit's own ground check is about
    the design as a solid rather than about this cell in particular."""
    w, meta = carousel
    for c in (tuple(q) for q in meta["rail_path"]):
        below = (c[0], c[1] - 1, c[2])
        assert _solid(w, below), "rail at %s stands on %s" % (c, _name(w, below))


def test_the_boarding_rail_is_reachable_on_foot_from_the_ground(carousel):
    """The failure this repo has already shipped: a boarding platform walled off from its own
    track. Seeded on the forecourt, which is real ground a visitor arrives on."""
    w, meta = carousel
    f = bigwheel._Frame(_params("carousel"))
    RC = (meta["diameter"] // 2) + 1
    c = meta["width"] // 2
    seed = f.at(c, c - (RC + 4), 0)             # the forecourt, in front of the entrance
    region = _walkable(w, seed)
    board = tuple(meta["board"])
    assert board in region, "the boarding rail at %s is not walkable from the forecourt" % (board,)
    # and so is the rest of the circuit - you can get off wherever you like
    reached = sum(1 for q in meta["rail_path"] if tuple(q) in region)
    assert reached == len(meta["rail_path"]), \
        "only %d of %d track cells are reachable on foot" % (reached, len(meta["rail_path"]))


def test_the_mounts_and_the_fence_keep_off_the_track(carousel):
    """Two rings of poles either side of a circuit is exactly the arrangement that eats a rail
    cell, and the generator raises rather than skipping - but only if the radii really differ."""
    _w, meta = carousel
    assert meta["track_r"] not in (meta["diameter"] // 2 - 1, max(5, meta["diameter"] // 2 - 8))


def test_the_gate_steps_ascend_toward_the_deck(carousel):
    """**A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D.** Built the other way round the
    risers face into the descent and the step cannot be walked up - and our renderer draws both
    directions identically, which is why this is asserted and never eyeballed. It shipped
    backwards once, on all four flights."""
    w, meta = carousel
    p = _params("carousel")
    f = bigwheel._Frame(p)
    R = meta["diameter"] // 2
    c = meta["width"] // 2
    seen = 0
    for (ui, ud) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        want = bigwheel._wdir(f, -ui, -ud)       # inward: the way you climb
        for t in (-1, 0, 1):
            a = ui * (R + 1) + (0 if ui else t)
            b = ud * (R + 1) + (0 if ud else t)
            pos = f.at(c + a, c + b, 0)
            name, props = w.cells[pos]
            assert name.endswith("_stairs"), "%s is %s" % (pos, name)
            assert props["half"] == "bottom"
            assert props["facing"] == want, \
                "the %s flight faces %s; it ascends toward %s" % ((ui, ud), props["facing"], want)
            seen += 1
    assert seen == 12


# ------------------------------------------------------------------ the bubble lifts

@pytest.mark.parametrize("kind", ("wheel", "drop"))
def test_the_lift_is_an_unbroken_water_column_over_soul_sand(kind, request):
    """A bubble column is water SOURCES the whole way with soul sand under the bottom one. A gap
    anywhere is a rider who stops at that course - inside a shaft with no door."""
    w, meta = request.getfixturevalue(kind)
    col = [tuple(c) for c in meta["lift"]]
    soul = [tuple(c) for c in meta["lift_soul"]]
    assert col and soul
    for c in col:
        assert _name(w, c) == "water", "lift cell %s holds %s" % (c, _name(w, c))
    ys = sorted(c[1] for c in col)
    assert ys == list(range(ys[0], ys[0] + len(ys))), "the lift column has a gap in it"
    for s in soul:
        assert _name(w, s) == "soul_sand"
        # the pump has to be under WATER, not under the casing
        assert _name(w, (s[0], s[1] + 1, s[2])) == "water", \
            "the soul sand at %s has %s over it" % (s, _name(w, (s[0], s[1] + 1, s[2])))


@pytest.mark.parametrize("kind", ("wheel", "drop"))
def test_the_lift_is_sealed_on_every_course(kind, request):
    """**A WATER SHAFT CANNOT HAVE A DOOR.** One open cell beside the column at any course and the
    whole thing drains through it onto the boarding platform. Checked per cell rather than trusted
    to the casing loop, because the casing is drawn through the hub, the gallery and the A-frames
    and any of those could have left a hole."""
    w, meta = request.getfixturevalue(kind)
    wet = {tuple(c) for c in meta["lift"]} | {tuple(c) for c in meta["pool"]}
    holes = []
    for c in sorted(wet):
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            o = (c[0] + dx, c[1], c[2] + dz)
            if o not in wet and not _solid(w, o):
                holes.append((c, o, _name(w, o)))
        below = (c[0], c[1] - 1, c[2])
        if below not in wet and not _solid(w, below):
            holes.append((c, below, _name(w, below)))
    assert not holes, "%d holes in the water, the first %s" % (len(holes), holes[:3])


@pytest.mark.parametrize("kind", ("wheel", "drop"))
def test_the_water_goes_exactly_where_it_was_put_and_nowhere_else(kind, request):
    """The simulator's own verdict on the finished model, which is the check the builder runs on
    itself before it emits. It catches a leak opened by ANY part of the build, not only by the
    casing - a car strut, an A-frame leg, a sign."""
    w, meta = request.getfixturevalue(kind)
    wet = [tuple(c) for c in meta["lift"]] + [tuple(c) for c in meta["pool"]]
    assert not bigwheel._watertight(w, wet)


def test_the_leak_guard_is_not_vacuous():
    """A check that cannot fail is worse than no check, because it is counted. Punch one hole in
    the casing beside the column and the generator must refuse to emit."""
    orig = bigwheel._fill_water
    fired = {}

    def holed(w, f, core, h0, h1):
        if len(core) == 1 and h1 > 30:               # the lift column, not the pool
            (i, d), = core
            pos = f.at(i, d + 1, 20)                 # an ORTHOGONAL neighbour of the shaft
            if pos in w.cells:
                w.cells.pop(pos)
                fired["holed"] = pos
        return orig(w, f, core, h0, h1)

    bigwheel._fill_water = holed
    try:
        with pytest.raises(ValueError, match="leaks"):
            _built("wheel")
    finally:
        bigwheel._fill_water = orig
    assert fired, "the test did not actually punch a hole"


@pytest.mark.parametrize("kind", ("wheel", "drop"))
def test_you_can_walk_from_the_ground_to_the_pool_and_swim_to_the_lift(kind, request):
    """The whole entrance, in one assertion, because it is one chain and any link breaks it:

    the queue is real ground -> the pool's edge is walkable -> the pool is one body of water with
    the foot of the lift column. That last hop is the one that has no door and therefore no other
    way of being proved.
    """
    w, meta = request.getfixturevalue(kind)
    p = _params(kind)
    f = bigwheel._Frame(p)
    board = tuple(meta["board"])
    # The pad in front of the entrance, and OFF the wheel's centre-line, because the wheel's own
    # channel runs down it: a seed in the pool is a flood that proves the pool is connected to
    # itself. Real ground, or the whole test is theatre.
    seed = f.at(meta["width"] // 2 + (3 if kind == "wheel" else 0), -1, 0)
    region = _walkable(w, seed)
    # the pool edge: a standable cell orthogonally beside the pool's surface
    pool = {tuple(c) for c in meta["pool"]}
    top = meta["pool_top"]
    edge = {(c[0] + dx, c[1] + 1, c[2] + dz) for c in pool if c[1] == top
            for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1))}
    assert edge & region, "no cell of the pool's edge is walkable from the queue"
    # ...and the pool and the column are one body of water you can swim between
    body = _water_body(w, sorted(pool)[0])
    assert board in body or _name(w, board) == "water" or board in pool
    lift_foot = min((tuple(c) for c in meta["lift"]), key=lambda c: c[1])
    assert lift_foot in body, \
        "the foot of the lift is not in the same water as the pool - there is no way in"


@pytest.mark.parametrize("kind", ("wheel", "drop"))
def test_the_lift_delivers_you_onto_a_deck_you_can_stand_on(kind, request):
    """The exit, which is the half of a bubble elevator that is easy to get wrong: the column's
    TOP water sits level with the deck, you are pushed one course clear of it, and you step out.
    A column that stops under the deck strands the rider inside the shaft."""
    w, meta = request.getfixturevalue(kind)
    deck_y = meta["gallery_y"] if kind == "wheel" else meta["platform_y"]
    col = [tuple(c) for c in meta["lift"]]
    top = max(c[1] for c in col)
    assert top == deck_y, "the column tops out at y=%d and the deck is at y=%d" % (top, deck_y)
    head = [c for c in col if c[1] == top][0]
    stand = (head[0], head[1] + 1, head[2])
    assert not _solid(w, stand), "the column's mouth is capped"
    out = [(stand[0] + dx, stand[1], stand[2] + dz)
           for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    ok = [o for o in out if not _solid(w, o) and not _solid(w, (o[0], o[1] + 1, o[2]))
          and _solid(w, (o[0], o[1] - 1, o[2]))]
    assert ok, "there is nowhere to step out onto at the top of the lift"


# ------------------------------------------------------------------ the drops

@pytest.mark.parametrize("kind", ("wheel", "drop"))
def test_the_chute_is_clear_the_whole_way_down(kind, request):
    """A fall that hits a block is a fall that hurts, and one stray cell in fifty courses does it.
    Every cell, not a sample."""
    w, meta = request.getfixturevalue(kind)
    for c in (tuple(q) for q in meta["chute"]):
        n = _name(w, c)
        assert n is None or n == "water", "the chute is blocked at %s by %s" % (c, n)


@pytest.mark.parametrize("kind", ("wheel", "drop"))
def test_nothing_the_fall_can_drift_into_misses_the_water(kind, request):
    """A walled chute is one way to be safe and it is not the only one: the tower's shaft is open
    below its platform and the whole interior is the tank, so drifting sideways is fine there and
    fatal in the wheel's one-cell tube. So the question is not "is it walled" but "does every
    column a body could end up in still land in water", which is the one that actually matters -
    and the answer differs per ride, so each ride states its own fall zone instead of the test
    assuming one."""
    w, meta = request.getfixturevalue(kind)
    chute = {tuple(c) for c in meta["chute"]}
    zone = {tuple(q) for q in meta["fall_zone"]}
    lo, hi = meta["fall_to"], meta["fall_from"]

    escapes = []
    for c in sorted(chute):
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            o = (c[0] + dx, c[1], c[2] + dz)
            if (o[0], o[2]) in zone or _solid(w, o):
                continue
            escapes.append((c, o, _name(w, o)))
    assert not escapes, "%d ways out of the fall zone, the first %s" % (len(escapes), escapes[:3])

    for (x, z) in sorted(zone):
        for y in range(lo + 1, hi):
            n = _name(w, (x, y, z))
            assert n is None or n == "water", \
                "the fall zone is blocked at %s by %s" % ((x, y, z), n)
        assert _name(w, (x, lo, z)) == "water", "column %s does not end in water" % ((x, z),)
        assert _name(w, (x, lo - 1, z)) == "water", \
            "the landing at %s is one course deep" % ((x, z),)


@pytest.mark.parametrize("kind", ("wheel", "drop"))
def test_the_fall_lands_in_water(kind, request):
    """**LANDING IN WATER CANCELS ALL FALL DAMAGE**, and it is the only thing that does - which is
    why the bottom of the chute is asserted rather than assumed. Two courses, so a rider who
    clips the wall on the way down still enters water rather than the tank's floor."""
    w, meta = request.getfixturevalue(kind)
    chute = {tuple(c) for c in meta["chute"]}
    floor = min(c[1] for c in chute)
    for c in sorted(q for q in chute if q[1] == floor):
        below = (c[0], c[1] - 1, c[2])
        assert _name(w, below) == "water", \
            "the chute at %s ends over %s, not water" % (c, _name(w, below))
        assert _name(w, (below[0], below[1] - 1, below[2])) == "water", \
            "the landing is only one course deep under %s" % (c,)


def test_the_wheels_drop_is_a_real_drop(wheel):
    """Fifty-odd courses, or it is a step. Measured off the build rather than declared."""
    _w, meta = wheel
    chute = [tuple(c) for c in meta["chute"]]
    assert max(c[1] for c in chute) - min(c[1] for c in chute) >= 40


# ------------------------------------------------------------------ the whole piece

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_ride_is_one_piece_at_every_facing(kind, facing):
    """A floating fragment is invisible in every render this repo owns, and a facing bug is
    invisible in all four of them at once."""
    w, _meta = _built(kind, facing=facing)
    assert _components(set(w.cells)) == [len(w.cells)]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_nothing_is_currency_expensive_or_post_1_19(kind, land):
    w, _meta = _built(kind, land=land)
    names = Counter(v[0] for v in w.cells.values())
    for n in names:
        assert blocks.available(n), "%s is not on the 1.19 server" % n
        assert blocks.spendable(n), "%s is CURRENCY on this island" % n
        assert not blocks.falls(n), "%s falls; this build has open air under it" % n
        assert palette.tier(n) in ("cheap", "ok"), "%s is %s" % (n, palette.tier(n))


@pytest.mark.parametrize("kind", KINDS)
def test_every_sign_is_short_enough_and_has_a_wall_behind_it(kind):
    """Fifteen characters, or the line clips mid-word - and a wall sign with no full block behind
    it is one the game refuses to place. Both failures only appear in a screenshot."""
    w, meta = _built(kind)
    assert meta["signs"] >= 1, "the ride is unnamed"
    assert len(w.signs) == meta["signs"]
    for pos, text in w.signs.items():
        assert w.name(*pos) is not None, "sign text at %s with no sign block" % (pos,)
        for line in list(text["front"]) + list(text["back"]):
            assert len(str(line)) <= 15, "%r is %d characters" % (line, len(str(line)))
        nb = [w.name(pos[0] + dx, pos[1], pos[2] + dz)
              for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        assert any(n and blocks.is_full_cube(n) for n in nb), \
            "the sign at %s hangs on nothing" % (pos,)


def test_the_wheels_lamp_ring_is_complete(wheel):
    """It shipped lighting 15 of 24 positions with the whole TOP arc dark, because "below the rim
    tip" points back INTO the annulus on the upper half. A ring with a dark half is not a ring."""
    _w, meta = wheel
    assert meta["rim_lamps"] == meta["rim_lamp_slots"], \
        "%d of %d rim lamps placed" % (meta["rim_lamps"], meta["rim_lamp_slots"])
    assert meta["car_lamps"] == meta["cars"]
    assert meta["gallery_lamps"] == 4


@pytest.mark.parametrize("kind", KINDS)
def test_every_ride_states_its_contract_and_what_is_still_unverified(kind):
    """A machine whose promise lives only in a chat message is one nobody can audit a month later,
    and a ride nobody has ridden must SAY so rather than being quietly presented as proven."""
    w, meta = _built(kind)
    assert len(meta["contract"]) > 120
    assert meta["unverified"], "%s claims to be verified in game and it is not" % kind
    assert meta["ride"] in ("minecart circuit", "bubble lift + free fall")


def test_the_wheel_is_at_least_sixty_five_across(wheel):
    """The brief's floor. A wheel that does not dominate the skyline is a fairground hoop."""
    _w, meta = wheel
    assert meta["diameter"] >= 65
    assert meta["top"] >= 75


def test_the_drop_tower_is_tall_enough_to_be_a_drop_tower(drop):
    _w, meta = drop
    assert meta["top"] >= 65
    assert meta["fall"] >= 45
