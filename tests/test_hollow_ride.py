"""The Ghost Train's contracts, and the two the Hollow's climb and its descent still owed.

`tests/test_hollow_flow.py` pins the Hollow's own kinds - the manor's walkthrough, the clock
tower's climb, the seance's machine. The Ghost Train is the zone's third real ride and it lives in
`gen/attractions.py`, so it was outside that file's `KINDS` and nothing in this repo had ever asked
the one question the zone was rejected over: **is there anything there.**

The answer, measured on the build before this file existed, was no:

    light sources in the whole attraction          0
    ...inside the dark ride                        0
    ...on the boarding platform                    0
    set pieces of any kind                         0
    track cells with a solid block over the rider  11 of 50

Every one of those is a *thing that does nothing, quietly* - this repo's most-repeated failure
shape. Both light calls RETURNED FALSE and both returns were dropped: the interior lamps were asked
for in open air with nothing to stand on or hang from, and the platform lamps were asked for before
the post that fills their own cell was built. `meta["lamps"]` shipped 0 and nobody read it. And the
suffocation tunnel is the same class as everything else pinned here - legal, connected, affordable,
and identical in every render to the version that works, because a wall resting on a rail draws
exactly like a wall resting on the ground.

So the counts are asserted EXACTLY rather than loosely. A bound of `lamps >= 1` passes on a ride
with one lantern in it, which is the bug back in a hat: `circuits.pulse` shipped as a bare repeater
for months behind exactly that kind of bound.
"""
from collections import deque

import pytest

from mcbuild import blocks, palette
from mcbuild.gen import attractions as A, hollowmanor as H
from mcbuild.gen.park import SIGN_WIDTH, _Frame
from mcbuild.gen.vertical import World

import hollowwalk as HW

LANDS = ("hollow", "midway", "frontier")
FACINGS = ("east", "north", "west", "south")

RAILS = {"rail", "powered_rail", "detector_rail", "activator_rail"}
LIGHTS = {"lantern", "soul_lantern", "candle"}


def _ride(land="hollow", facing="east", **kw):
    """The raw World, in WORLD coordinates - a canvas is sized to its own content and shifts
    between builds, so anything comparing two of them lines up against nothing."""
    p = {**A.ATTRACTIONS, "at": [0, 64, 0], "kind": "ghosttrain", "land": land,
         "facing": facing, "title": "GHOST TRAIN", **kw}
    w = World()
    meta = A.BUILDERS["ghosttrain"](w, p, None)
    return w, _Frame(p), meta


def _rail_cells(w):
    return {pos for pos, (n, _pr) in w.cells.items() if n.split(":")[-1] in RAILS}


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
            for c in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z),
                      (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)):
                if c in cells and c not in seen:
                    seen.add(c)
                    q.append(c)
        sizes.append(n)
    return sorted(sizes, reverse=True)


# ------------------------------------------------------------------ getting to the ride

@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("land", LANDS)
def test_the_ghost_train_is_boarded_ON_FOOT_FROM_REAL_GROUND(land, facing):
    """**THE SEED IS THE FAR SIDE OF THE MODULE'S OWN PAD**, not the platform itself.

    `test_attractions.py` already floods from `boarding_at` and proves the platform is not sealed
    off from its track - a real check, and a different one. It cannot say whether a visitor
    arriving off the zone's paving can GET to the platform, because it starts standing on it. A
    flood seeded on the thing it means to prove reachable proves only that the thing exists.

    `HW.reachable` refuses a seed it cannot stand on and refuses a region smaller than `floor`, so
    neither half of that can happen quietly here.
    """
    w, _f, m = _ride(land, facing)
    got = HW.reachable(w, m["approach_at"], floor=150)
    assert HW.near(got, m["boarding_at"], 0), \
        f"{land}/{facing}: you cannot walk from the approach to the boarding platform"
    assert HW.near(got, m["entry_at"], 0), \
        f"{land}/{facing}: you cannot walk in through the entry arch to reach a cart"


@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("land", LANDS)
def test_no_rider_passes_under_a_solid_block(land, facing):
    """**A SUFFOCATION TUNNEL IS NOT A RIDE.** The loop's front leg runs in the front wall's own
    plane, so `_lay_loop` overwrote that wall's ground course with rail and left the course above
    it solid - eleven of fifty track cells with a wool block where the rider's head goes.

    Exactly zero, not `< 3`: a bound with slack in it is a bound that lets the bug back one cell
    at a time, and there is no cell of a ride where a block on your head is acceptable.
    """
    w, _f, _m = _ride(land, facing)
    blocked = [(x, y, z) for (x, y, z) in _rail_cells(w)
               if HW.solid(w, (x, y + 1, z))]
    assert blocked == [], \
        f"{land}/{facing}: {len(blocked)} track cell(s) have a block over the rider: {blocked[:4]}"


# ------------------------------------------------------------------ what the rider passes

@pytest.mark.parametrize("land", LANDS)
def test_THE_DARK_RIDE_IS_ACTUALLY_LIT(land):
    """The whole finding, pinned as an exact arithmetic identity rather than a threshold.

    Every light this build asks for is COUNTED, and the count returned - so a lantern that does
    not land shows up as a number rather than as a dark ride. Four grilles with a lantern behind
    each, two tombs with a lit candle, four hung chandeliers, two platform posts: twelve, and the
    world must actually contain twelve.
    """
    w, _f, m = _ride(land)
    placed = [pos for pos, (n, _pr) in w.cells.items() if n.split(":")[-1] in LIGHTS]
    want = m["windows"] + m["tombs"] + m["chandeliers"] + 2
    assert m["lamps"] == want == 12, \
        f"{land}: the build reports {m['lamps']} lights and its own parts want {want}"
    assert len(placed) == m["lamps"], \
        f"{land}: {m['lamps']} lights were counted and {len(placed)} are in the world"


@pytest.mark.parametrize("land", LANDS)
def test_there_is_something_to_look_at_and_it_is_not_all_one_thing(land):
    """A dark ride is a sequence of tableaux. One lit box in the middle is a lit box."""
    _w, _f, m = _ride(land)
    assert m["windows"] == 4, "the mausoleum does not face the rider on all four legs"
    assert m["tombs"] == 2 and m["chandeliers"] == 4
    assert m["webs"] >= 6, f"{land}: only {m['webs']} cobwebs anchored"


@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("land", LANDS)
def test_no_set_piece_stands_in_the_track_or_over_it(land, facing):
    """The casino's own lesson, where a link laid before the thing it linked turned a button pad
    into redstone dust: **decoration placed after structure eats structure**, and `put` overwrites.
    The mausoleum is inset two cells from the loop on all four sides and every prop outside it
    sits in the one-cell alley between - which is asserted against the built rail set rather than
    against the arithmetic that placed them.
    """
    w, f, m = _ride(land, facing)
    rails = _rail_cells(w)
    assert len(rails) == m["track"], \
        f"{land}/{facing}: {m['track']} rails were laid and {len(rails)} survive - one was eaten"
    mi0, mi1, md0, md1 = m["tomb_bounds"]
    tomb = {f.at(i, d, h)
            for i in range(mi0 - 1, mi1 + 2)
            for d in range(md0 - 1, md1 + 2)
            for h in range(-1, m["height"])}
    assert not (tomb & rails), "the centrepiece and its alleys overlap the track"


@pytest.mark.parametrize("land", LANDS)
def test_every_prop_and_every_light_is_really_attached(land):
    """A candle, a skull and a standing lantern all need a full cube UNDER them and the game
    refuses them without one; a hanging lantern needs something over it, and a chain is not a full
    cube - which is why `_lamp` correctly refuses to hang one and the state is stated by hand.
    None of this is visible in a render: a lantern floating in air draws exactly like one on a
    post, and this attraction had already shipped two lights that were never placed at all.
    """
    w, _f, _m = _ride(land)
    for (x, y, z), (name, props) in w.cells.items():
        base = name.split(":")[-1]
        if base in ("candle", "skeleton_skull"):
            assert HW.full_cube(w.name(x, y - 1, z)), \
                f"{base} at {(x, y, z)} stands on {w.name(x, y - 1, z)!r}"
        elif base in ("lantern", "soul_lantern"):
            if props.get("hanging") == "true":
                assert w.has(x, y + 1, z), f"a hung lantern at {(x, y, z)} hangs from nothing"
            else:
                assert HW.full_cube(w.name(x, y - 1, z)), \
                    f"a standing lantern at {(x, y, z)} stands on {w.name(x, y - 1, z)!r}"
        elif base == "cobweb":
            assert any(w.has(x + a, y + b, z + c)
                       for (a, b, c) in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                         (0, -1, 0), (0, 0, 1), (0, 0, -1))), \
                f"the cobweb at {(x, y, z)} is a floating singleton"


# ------------------------------------------------------------------ the generic gates

@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("land", LANDS)
def test_the_ride_is_one_connected_piece(land, facing):
    w, _f, _m = _ride(land, facing)
    assert _components(w) == [len(w.cells)]


@pytest.mark.parametrize("land", LANDS)
def test_every_block_state_in_the_ride_is_legal(land):
    w, _f, _m = _ride(land)
    for (name, props) in w.cells.values():
        base = name.split(":")[-1]
        assert blocks.validate(base, props) == [], f"{land}: {base}{props} is not legal"
        assert blocks.available(base), f"{land}: {base} is not on the 1.19 server"


@pytest.mark.parametrize("land", LANDS)
def test_nothing_in_the_ride_is_currency_or_expensive(land):
    """DIRT IS MONEY ON THIS SERVER, and `bookshelf` - the obvious block for a haunted library -
    is `expensive` here, which is why the mausoleum is barred and lit rather than furnished."""
    w, _f, _m = _ride(land)
    for (name, _props) in w.cells.values():
        base = name.split(":")[-1]
        assert blocks.spendable(base), f"{land} places CURRENCY: {base}"
        assert palette.tier(base) != "expensive", f"{land} places an undeclared {base}"


@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("land", LANDS)
def test_the_ride_says_what_you_do_at_it_at_EYE_LEVEL(land, facing):
    """A name eight courses up says what the building is, not what you do. The second sign hangs
    two columns outside the entry arch, because the arch's own column is an OPENING and `_sign`
    refuses a support that is not there - four of the park's seven kinds shipped a sign attached
    to nothing before that guard existed."""
    w, _f, m = _ride(land, facing)
    assert m["signs"] == 2, f"{land}/{facing}: the ride carries {m['signs']} sign(s)"
    step = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
    found = 0
    for (x, y, z), (name, props) in w.cells.items():
        if not name.split(":")[-1].endswith("_wall_sign"):
            continue
        found += 1
        dx, dz = step[props["facing"]]
        assert HW.full_cube(w.name(x - dx, y, z - dz)), \
            f"the sign at {(x, y, z)} hangs on {w.name(x - dx, y, z - dz)!r}"
    assert found == 2


def test_no_line_of_the_rides_signs_is_clipped():
    """Fifteen characters, and past it a line clips mid-word - which only a screenshot of the
    placed build would ever show."""
    for line in ("GHOST TRAIN", "dare to ride", "RIDE THE CART", "board here", "one at a time"):
        assert len(line) <= SIGN_WIDTH, f"{line!r} is {len(line)} characters"


# ------------------------------------------------------------------ the climb, and the descent

@pytest.mark.parametrize("facing", FACINGS)
def test_EVERY_TREAD_of_the_clock_tower_climb_has_headroom(facing):
    """**ASSERT HEADROOM ON EVERY TREAD, NOT JUST ON THE TREADS.**

    `gen/monument.py` records what this costs: a riser placed one course above the previous tread
    instead of under the next one stands in the cell a walker occupies, and all 39 of that build's
    treads were unwalkable while passing legality, connectivity, tread-path and stair-facing
    checks. A flood fill from the door catches it too - but it reports one failure ("the gallery
    is unreachable") for a fault that could be at any of twenty-nine courses, and it cannot say
    which. This names the course.

    The tread list comes from the build's own sidecar. Re-derived here from `_ring` and a
    remembered base course, the check would agree with the build by repeating its arithmetic -
    and arithmetic is this flight's entire failure mode.
    """
    p = {**H.HOLLOW, "at": [0, 64, 0], "kind": "clocktower", "land": "hollow", "facing": facing}
    w = World()
    m = H.BUILDERS["clocktower"](w, p, None)
    assert m["tread_cells"] and len(m["tread_cells"]) == m["treads"]
    for (x, y, z) in m["tread_cells"]:
        # A walker standing on the tread occupies y+1 and y+2. Both have to be clear, and the
        # second is the one the belfry floor takes.
        assert not HW.solid(w, (x, y + 1, z)), \
            f"{facing}: the tread at {(x, y, z)} has {w.name(x, y + 1, z)!r} in the walker's feet"
        assert not HW.solid(w, (x, y + 2, z)), \
            f"{facing}: the tread at {(x, y, z)} has {w.name(x, y + 2, z)!r} on the walker's head"


def test_the_hollow_HAS_A_WAY_DOWN_and_it_is_the_manors_cellar():
    """The zone's only undercroft. The Graveyard and its crypt were dropped from the roster to
    make room for things to ride, and with them went the quarter's only other descent - so if the
    manor's cellar is not a real, reachable room, the Hollow has no below-ground at all.

    Asserted from the FRONT DOOR, because a cellar you can only reach by falling into it is not
    part of the walkthrough. `HW.walk_from`'s model steps down one course at a time and never
    falls, so every cell it reaches down there is one you can also climb back out of.
    """
    p = {**H.HOLLOW, "at": [0, 64, 0], "kind": "manor", "land": "hollow", "facing": "east"}
    w = World()
    m = H.BUILDERS["manor"](w, p, None)
    got = HW.reachable(w, m["entry_at"], floor=500)
    below = [c for c in got if c[1] < m["entry_at"][1]]
    assert len(below) >= 60, \
        f"the manor's cellar is {len(below)} walkable cells below the door - not a room"
    assert m["niches"] >= 4 and m["vault_lamps"] >= 4, \
        "the cellar is unlit or has nothing in it, which is a hole rather than a room"
    named = [n for (n, _c) in m["route"]]
    assert any("cellar" in n.lower() for n in named), \
        f"the route does not name the descent: {named}"
