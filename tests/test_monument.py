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
    solid and cutting a hole in a second pass, the bridge silently walks into a wall.

    IT IS TESTED AT THE RAIL COURSE, NOT THE FLOOR. Written against `H_GALLERY` this asserted
    that the gallery FLOOR is not a wall, which is true of every cell of it and of every design
    that has ever been built here - the test passed for a whole version while pointing at the
    wrong course AND, after the tower moved to the flank, at the wrong side of the monument.
    """
    w, f, _pal, _p, meta = _built()
    c = monument.PAD_R
    h = meta["gallery_height"] + 1                       # the balustrade course
    gap = f.at(c - monument.GAL_R, c, h)
    assert gap not in w.cells, "the balustrade was not left open where the bridge arrives"
    ring = [f.at(c + di, c + dd, h) for (di, dd) in
            monument._annulus(monument.GAL_R, monument._disc)]
    walls = [pos for pos in ring if pos in w.cells and "wall" in w.cells[pos][0]]
    assert len(walls) == len(ring) - 1, \
        "the gap must be exactly one cell - a rail with holes in it is not a rail"


# ------------------------------------------------------------------ THE WAY IN, AND THE WALK

# What a player can move through. Everything else placed is treated as SOLID, which is the
# conservative direction: a route that survives calling a lantern a wall really is a route.
_PASSABLE = ("_sign",)


def _solid(w, pos):
    v = w.cells.get(pos)
    return bool(v) and not v[0].endswith(_PASSABLE)


def _standable(w, pos):
    """Feet in `pos`: something solid underfoot, and two clear courses for a body."""
    x, y, z = pos
    return (_solid(w, (x, y - 1, z)) and not _solid(w, pos)
            and not _solid(w, (x, y + 1, z)))


def _walk(w, seed):
    """Every standing position reachable from `seed`, stepping one cell at a time and at most one
    course up or down - which is exactly what a spiral stair asks of a player.

    THE STANDING SPACE, NOT THE BLOCKS. `_reachable` above floods the SOLID cells and answers
    "is this one printable piece"; it cannot tell a staircase from a sculpture of one, and for a
    whole version of this design it did not: the climb had a riser resting on every tread and
    every block-level check passed.
    """
    seen = {seed}
    q = deque([seed])
    while q:
        x, y, z = q.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                n = (x + dx, y + dy, z + dz)
                if n not in seen and _standable(w, n):
                    seen.add(n)
                    q.append(n)
    return seen


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_the_door_is_on_the_apron_and_reachable_from_the_plaza(land, facing):
    """THE DOOR HAS TO BE FINDABLE BEFORE IT HAS TO BE USEFUL. Seeded at the front of the apron -
    the cell a visitor arriving from the plaza actually stands on, dead on the monument's own
    approach axis - and the reached region is asserted LARGE before any claim about the doorway
    is trusted, because a flood seeded somewhere empty is trivially "connected" to nothing.
    """
    w, f, _pal, p, meta = _built(land, facing)
    c = monument.PAD_R
    front = f.at(c, c - monument.PAD_R, 0)               # standing on the apron, facing the steps
    assert _standable(w, front), "the seed itself is not somewhere a visitor can stand"
    reached = _walk(w, front)
    assert len(reached) > 300, \
        f"only {len(reached)} standing cells reachable from the plaza - too small to trust"
    assert tuple(meta["door"]) in reached, \
        "the tower's doorway cannot be walked to from the front of the monument"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_the_gallery_can_be_walked_to_from_the_door(land, facing):
    """**THE CLIMB, WALKED.** From the doorway cell the generator itself records - never a cell
    picked because it happened to work - up the spiral, across the landing and the bridge, onto
    the deck. This is the test the design failed silently for a whole version: the riser sat on
    top of every tread, so the flight was a picture of a staircase.
    """
    w, f, _pal, p, meta = _built(land, facing)
    c = monument.PAD_R
    door = tuple(meta["door"])
    assert _standable(w, door), "the portal's own threshold is not standable"
    reached = _walk(w, door)
    deck_y = p["at"][1] + meta["gallery_height"] + 1
    deck = [pos for pos in reached
            if pos[1] == deck_y
            and max(abs(pos[0] - f.at(c, c)[0]), abs(pos[2] - f.at(c, c)[2])) <= monument.GAL_R]
    assert len(deck) >= 20, \
        f"only {len(deck)} cells of the viewing gallery can be stood on after climbing to it"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_no_tread_has_anything_resting_on_it(land, facing):
    """The bug itself, pinned. A tread with a block one course above it cannot be stood on, and
    the riser that ties the flight together used to be exactly that block."""
    w, _f, _pal, _p, meta = _built(land, facing)
    for pos, _face in meta["climb_treads"]:
        above = (pos[0], pos[1] + 1, pos[2])
        assert not _solid(w, above), \
            f"tread at {pos} is roofed by {w.cells[above][0]} - the climb cannot be walked"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_a_lamp_post_never_stands_in_the_staircase(land, facing):
    """The foot lamps are placed LAST and `w.put` overwrites, so one of the eight used to land on
    a tread and win. A stair with a lamp post where its third step should be is a stair that
    stops at the second."""
    w, _f, _pal, _p, meta = _built(land, facing)
    treads = {pos for pos, _face in meta["climb_treads"]}
    for pos in treads:
        name, _props = w.cells[pos]
        assert name.endswith("_stairs"), f"{pos} should be a tread and is {name}"
    assert meta["posts_skipped"] >= 1, "the lamp ring no longer knows about the turret at all"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_the_portal_is_a_real_opening_that_is_framed_and_lit(land, facing):
    """A doorway that is not a hole is a decoration, and a doorway nobody can see at night is one
    nobody uses. Three clear courses, a jamb either side, a lintel over it, and two lamps."""
    w, f, _pal, _p, meta = _built(land, facing)
    c = monument.PAD_R
    i, d = c + monument.PORTAL_I, c + monument.PORTAL_D
    for h in range(0, 3):
        assert f.at(i, d, h) not in w.cells, f"the doorway is blocked at course {h}"
    for di in (monument.PORTAL_I - 1, monument.PORTAL_I + 1):
        for h in range(0, 3):
            assert f.at(c + di, d, h) in w.cells, "the portal has no jamb"
        assert f.at(c + di, d, 3) in w.cells, "the portal has no lintel"
    assert meta["portal_lanterns"] == 2, "the portal is not lit on both shoulders"


@pytest.mark.parametrize("land", LANDS)
def test_the_signs_say_what_it_is_and_what_you_do(land):
    """A stranger works out what a building is from its signs before anything else. The climb has
    to be named, counted and offered somewhere on this monument, or the whole exercise is a
    tower with a secret."""
    w, _f, _pal, _p, meta = _built(land)
    text = " ".join(" ".join(list(t["front"]) + list(t["back"])).lower()
                    for t in w.signs.values())
    for want in ("climb the tower", "tower entrance", "viewing tower", "steps up", "view from"):
        assert want in text, f"no sign anywhere on the monument says {want!r}"
    assert str(meta["climb_length"]) in text, "no sign states how many steps the climb is"
    assert meta["signs_placed"] == meta["signs"], \
        "a sign was silently refused - `park._sign` places nothing when the wall behind it is a hole"


def test_the_route_to_the_door_is_marked_on_the_ground():
    """The park is reviewed from ABOVE, where a lintel and a lamp are invisible and paving is
    not. The walkway ring is repaved from the front round to the portal with a gilded dash."""
    w, f, _pal, _p, meta = _built()
    c, pal = monument.PAD_R, monument.LANDS["midway"]
    assert meta["marked_route"] >= 30, "the marked route is too short to read as a route"
    ring = [t for t in monument._band(monument.STEP_R[0], monument.PAD_R)
            if t[0] <= 0 and t[1] <= 0]
    dashes = [t for t in ring if w.cells[f.at(c + t[0], c + t[1], -1)][0] == pal["accent"]]
    assert 5 <= len(dashes) <= len(ring) // 2, \
        "the dashes are either not there or the whole quadrant is painted accent"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_the_reward_at_the_top_exists_and_needs_no_signal(land, facing):
    """A bell rings on a right-click and is cheap; a note block is expensive here before anyone
    asks what would drive it. Nothing on this monument carries a signal, so nothing on it can
    ship unverified."""
    w, _f, _pal, _p, _meta = _built(land, facing)
    bells = [(pos, props) for pos, (name, props) in w.cells.items() if name == "bell"]
    assert len(bells) == 1, "the gallery has no bell to ring"
    (pos, props) = bells[0]
    assert props["attachment"] == "floor"
    assert (pos[0], pos[1] - 1, pos[2]) in w.cells, "the bell stands on nothing"
    redstone = {"redstone_wire", "repeater", "comparator", "observer", "piston", "sticky_piston",
                "redstone_torch", "redstone_block", "dispenser", "dropper", "note_block"}
    assert not (redstone & {n for n, _ in w.cells.values()}), \
        "this design carries a signal and nothing here is verified to carry one"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_the_climb_is_lit_the_whole_way(land, facing):
    """An unlit spiral is a spiral nobody takes. One pedestal a revolution left eleven-course
    gaps of dark on a forty-course flight; two leaves four."""
    w, _f, _pal, _p, meta = _built(land, facing)
    pal = monument.LANDS[land]
    ys = sorted({pos[1] for pos, (name, _p) in w.cells.items() if name == pal["light"]})
    treads = sorted(pos[1] for pos, _f in meta["climb_treads"])
    lit = [y for y in ys if treads[0] <= y <= treads[-1]]
    assert len(lit) >= 8, f"only {len(lit)} lit courses over the whole climb"
    gaps = [b - a for a, b in zip(lit, lit[1:])]
    assert max(gaps) <= 6, f"a {max(gaps)}-course unlit stretch on the stair"


@pytest.mark.parametrize("land", LANDS)
def test_the_gallery_is_lit_from_underneath(land):
    """The one cue that says "somebody is up there" from forty courses below. A hanging lantern
    needs a FULL block over it - under the corbel's stairs it reads as hanging from air."""
    w, f, _pal, _p, meta = _built(land)
    assert meta["gallery_soffit_lanterns"] == 4
    for pos, (name, props) in w.cells.items():
        if props.get("hanging") == "true":
            over = (pos[0], pos[1] + 1, pos[2])
            assert over in w.cells, f"{name} at {pos} hangs from nothing"
            assert not w.cells[over][0].endswith(("_slab", "_stairs")), \
                f"{name} at {pos} hangs from a half block"


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
