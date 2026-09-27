"""The Hollow's contracts: can you GET there, and does the machine answer.

The zone was rejected for serving "low function" and feeling "confusing" - you arrived and there
was nothing to do and no idea where to go. Everything pinned here is one of the four ways that
gets fixed and then quietly un-fixed, and **not one of them is visible in a render**:

    a walkthrough with no route            a flight that rises two courses a tread, a floor plane
                                           nobody holed over a stair, a doorway one cell narrower
                                           than a body - all legal, connected and affordable
    a climb that ends at a plank ceiling   the belfry floor over the last two treads
    a vault with a crawlspace in it        a ceiling one course over its own floor
    a machine that looks like it works     `chase` and `vault` were deleted from the casino for
                                           exactly this, and the randomiser bug this file caught
                                           made every north- and south-facing game a dead one

So the walk is FLOODED FROM REAL GROUND, the seed is checked to be standable, and the flood is
checked to have reached a real region - a previous test in this repo seeded in the void and proved
nothing while passing. The mechanism is SIMULATED. Nothing here is eyeballed.
"""
from collections import deque

import pytest

from mcbuild import blocks, circuit, palette
from mcbuild.gen import circuits, hollowmanor as H
from mcbuild.gen.vertical import World

import hollowwalk as HW

KINDS = sorted(H.BUILDERS)
LANDS = sorted(H.GOTHIC)
FACINGS = ("east", "north", "west", "south")

# THE ONE DECLARED EXCEPTION, and it is declared rather than smuggled. `redstone_lamp` is
# `expensive` on this economy and there is no cheap substitute: a lamp cannot be replaced by
# colour, because the thing it does is switch. The casino budgets its lamps the same way and for
# the same reason. Four is the whole of the Hollow's bill.
#
# The manor's three set pieces take one lamp each, and the ossuary takes one over each of its
# three pulls plus one in the vault. In a quarter whose walls are `black_wool` at luminance 21 a
# lamp is not decoration - it is the only feedback a player can read from across a dark room, and
# the alternative (a `bell`) has to be adjacent to lit dust, which in a room whose floor must stay
# walkable there is nowhere to put. So it is priced: eleven lamps for the whole Hollow.
EXPENSIVE_ALLOWANCE = {"seance": {"redstone_lamp": 4},
                       "manor": {"redstone_lamp": 3},
                       "ossuary": {"redstone_lamp": 4}}


def _cfg(kind, land="hollow", facing="east", **kw):
    return {**H.HOLLOW, "at": [0, 64, 0], "kind": kind, "land": land, "facing": facing, **kw}


def _built(kind, land="hollow", facing="east", **kw):
    """The raw World, so a test can ask about cells in WORLD coordinates.

    Asserting in world coordinates rather than canvas ones is a rule this repo already paid for:
    a canvas is sized to its own content, so it shifts between two builds with different settings
    and anything comparing them lines up against nothing.
    """
    p = _cfg(kind, land, facing, **kw)
    w = World()
    meta = H.BUILDERS[kind](w, p, None)
    return w, H._Frame(p), meta, p


def _spec(w):
    """The World as `circuit.Circuit.from_cells` wants it: one state string per cell."""
    return {pos: n + ("[" + ",".join(f"{k}={v}" for k, v in pr.items()) + "]" if pr else "")
            for pos, (n, pr) in w.cells.items()}


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


# ------------------------------------------------------------------ the walk model itself

def test_the_walk_model_refuses_a_seed_it_cannot_stand_on():
    """A FLOOD THAT STARTS IN THE VOID RETURNS NOTHING AND PASSES EVERY ASSERTION WRITTEN AGAINST
    IT. That has happened in this repo before, so the guard is a test rather than a comment."""
    w, f, _m, _p = _built("crypt")
    with pytest.raises(AssertionError):
        HW.walk_from(w, f.at(0, 0, 200))


def test_a_flight_of_stairs_is_walked_and_a_stack_of_blocks_is_not():
    """The distinction the model turns on: vanilla step height is 0.6, so a whole block has to be
    jumped and a half-step is taken automatically. Written without it the model refused the clock
    tower's own spiral at the one course where the belfry floor passes overhead, and the fault
    looked like the building's rather than the model's."""
    def rise(block, **props):
        """A one-course rise with a CEILING over the walker: the exact case the rule decides."""
        w = World()
        w.put(0, 60, 0, "stone")
        w.put(0, 60, 1, "stone")
        w.put(0, 61, 1, block, **props)          # the thing being stepped onto
        w.put(0, 63, 0, "stone")                 # the ceiling, at the walker's own y + 2
        return (0, 62, 1) in HW.walk_from(w, (0, 61, 0))

    assert rise("polished_blackstone_brick_stairs", facing="south", half="bottom",
                shape="straight", waterlogged="false"), \
        "a stair tread is a half-step and needs no headroom to take"
    assert not rise("stone"), \
        "a full block has to be jumped, and there is a ceiling in the way"


# ------------------------------------------------------------------ the manor walkthrough

def test_the_manor_walks_from_its_front_door_through_every_room_and_out_of_the_back():
    """THE ROUTE AND THE CHECK READ ONE LIST. `meta["route"]` is what the contract promises and
    what this walks, so a test cannot agree with a build by re-deriving the same mistake."""
    w, _f, m, _p = _built("manor")
    got = HW.reachable(w, m["entry_at"], floor=500)
    for (name, cell) in m["route"]:
        assert HW.near(got, cell, 0), f"the manor's route breaks at {name} {cell}"


def test_the_manors_back_door_leads_OUT_and_not_into_another_room():
    """A walkthrough is in at one face and out at the other. An 'exit' that delivers you back
    into the building is a cupboard, and the difference is one wall."""
    w, f, m, _p = _built("manor")
    got = HW.walk_from(w, m["entry_at"])
    D = m["depth"]
    assert HW.near(got, f.at(m["width"] // 2, D + 2, 0), 1), \
        "you cannot get off the back of the manor"


@pytest.mark.parametrize("facing", FACINGS)
def test_the_manor_walkthrough_survives_every_facing(facing):
    """A facing bug is invisible in a render and this repo has shipped two of them. The route is
    built through one `_Frame`, so if it works on one facing it should work on four - which is a
    reason to check, not a reason not to."""
    w, _f, m, _p = _built("manor", facing=facing)
    got = HW.reachable(w, m["entry_at"], floor=500)
    for (name, cell) in m["route"]:
        assert HW.near(got, cell, 0), f"{facing}: the route breaks at {name}"


def test_the_manors_cellar_is_a_room_and_not_a_crawlspace():
    """Four clear courses is a room; two is a slot you cannot enter, and the walk correctly
    refuses it - so a vault that fails this looks exactly like a stair that does not connect."""
    w, _f, m, _p = _built("manor")
    got = HW.walk_from(w, m["entry_at"])
    cellar = [c for c in got if c[1] < 64]
    assert len(cellar) >= 60, f"the cellar is only {len(cellar)} cells of walkable floor"


def test_the_manor_is_named_room_by_room():
    """A route nobody can read is still a maze. Every sign here is placed through `park._sign`,
    which REFUSES a column with a hole in it - so a count is a count of signs that will actually
    stand, and four of the park's seven kinds shipped floating ones before that guard existed."""
    _w, _f, m, _p = _built("manor")
    assert m["signs"] >= 6, f"the manor names only {m['signs']} of its rooms"


# ------------------------------------------------------------------ the clock tower climb

@pytest.mark.parametrize("facing", FACINGS)
def test_the_clock_tower_is_climbable_to_its_gallery_and_its_deck(facing):
    """THE ONE THING A TOWER IS FOR IS HEIGHT YOU CAN BE AT. It was 2,463 blocks with a service
    ladder up the inside and a bell nobody could reach."""
    w, f, m, _p = _built("clocktower", facing=facing)
    got = HW.reachable(w, f.at(m["side"] // 2, -3, 0), floor=120)
    assert HW.near(got, m["climb_from"], 0), f"{facing}: you cannot get in the door"
    assert HW.near(got, m["gallery_at"], 0), f"{facing}: the climb does not reach the gallery"
    assert HW.near(got, m["deck_at"], 1), f"{facing}: the crown deck is unreachable"


def test_no_two_treads_of_the_spiral_are_diagonal_neighbours():
    """A spiral whose consecutive treads share no face is not a stair, it is a row of stairs that
    happen to line up - the 6-connectivity trap that broke the leopard's ear tips - and it is also
    unwalkable, because a diagonal step up is not a step."""
    ring = H._ring(9)
    for k in range(len(ring)):
        a, b = ring[k], ring[(k + 1) % len(ring)]
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1, f"{a} and {b} are not one step apart"


def test_the_belfry_floor_is_open_over_the_LAST_TWO_treads():
    """A walker on the second-to-last tread stands a course below the floor plane and their HEAD
    is in it, so holing only the cell the flight lands on leaves the last step blocked by a plank
    ceiling. That shipped once and no render showed it."""
    w, f, m, _p = _built("clocktower")
    ring = H._ring(m["side"])
    start = ring.index((m["side"] // 2, 1))
    ring = ring[start:] + ring[:start]
    floor_h = 30
    for k in (m["treads"] - 2, m["treads"] - 1):
        ci, cd = ring[k % len(ring)]
        assert not w.has(*f.at(ci, cd, floor_h)) or \
            w.name(*f.at(ci, cd, floor_h)).endswith("_stairs"), \
            "the belfry floor is closed over a tread"


def test_the_gallery_can_actually_be_SEEN_out_of():
    """The whole point of the climb is the view, and a closed trapdoor at eye height is a wall
    with a texture on it. The lower two courses of every opening are a rail and open air."""
    w, f, m, _p = _built("clocktower")
    S, mid = m["side"], m["side"] // 2
    sill = 31
    open_cells = sum(1 for k in (mid - 1, mid, mid + 1)
                     for (i, d) in ((k, 0), (k, S - 1), (0, k), (S - 1, k))
                     if not w.has(*f.at(i, d, sill + 1)))
    assert open_cells == 12, f"only {open_cells} of the gallery's 12 view cells are open"


# ------------------------------------------------------------------ the graveyard vault

@pytest.mark.parametrize("facing", FACINGS)
def test_the_graveyard_vault_is_walkable_from_the_gate_and_back(facing):
    w, _f, m, _p = _built("graveyard", facing=facing)
    assert m["vault"] and m["vault_at"]
    got = HW.reachable(w, m["gate_at"], floor=200)
    assert HW.near(got, m["vault_at"], 0), f"{facing}: the vault cannot be reached from the gate"
    assert HW.near(got, m["sarcophagus_at"], 1), f"{facing}: nothing is at the bottom of the stair"
    # ...and BACK, which the model gives for free: it never allows a fall, so every route it
    # finds is reversible. Asserted rather than assumed, because the model could change.
    back = HW.walk_from(w, m["vault_at"])
    assert HW.near(back, m["gate_at"], 0), f"{facing}: the vault is a one-way trip"


def test_no_headstone_and_no_lamp_post_stands_over_the_open_well():
    """`put` overwrites and reports nothing, so a marker planted on the stair is a marker in mid
    air over a hole - and the lamp rhythm lands one post squarely in it."""
    w, f, m, _p = _built("graveyard")
    mi, md = m["width"] // 2, m["depth"] // 2
    for d in range(md + 4, md + 10):
        for i in range(mi - 1, mi + 2):
            above = w.name(*f.at(i, d, 0))
            assert above is None or above.endswith("_stairs"), \
                f"something stands at ({i},{d}) over the vault's well: {above}"


def test_turning_the_vault_off_leaves_the_graveyard_whole():
    """A feature that cannot be switched off is one nobody can decline. The ground plane has to
    close again when it is, or the enclosure is left with a hole in its lawn."""
    w, f, m, _p = _built("graveyard", vault=False)
    assert m["vault"] is False and m["vault_at"] is None
    mi, md = m["width"] // 2, m["depth"] // 2
    for d in range(md + 4, md + 10):
        assert w.has(*f.at(mi, d, -1)), f"the ground is missing at ({mi},{d})"
    assert _components(w) == [len(w.cells)]


# ------------------------------------------------------------------ the seance

@pytest.mark.parametrize("facing", FACINGS)
def test_the_seance_meter_is_dark_at_rest_and_reads_the_roll(facing):
    """THE CONTRACT, SIMULATED. `circuits.bar` promises that a level of L lights exactly the first
    L lamps; the randomiser promises 1, 2 or 4 at equal odds. Together that is a meter, and the
    only honest way to know it is a meter is to drive it."""
    w, _f, m, _p = _built("seance", facing=facing)
    spec = _spec(w)
    hop, lamps = tuple(m["rng_hopper"]), [tuple(c) for c in m["outputs"]]

    rest = circuit.Circuit.from_cells(spec)
    rest.run(12)
    assert not any(rest.powered(c) for c in lamps), f"{facing}: the meter is lit with no roll"

    for level, want in ((1, 1), (2, 2), (4, 4)):
        c = circuit.Circuit.from_cells(spec)
        c.fill(hop, level)
        c.run(24)
        lit = [c.powered(x) for x in lamps]
        assert lit == [True] * want + [False] * (len(lamps) - want), \
            f"{facing}: a roll of {level} lit {lit}"


@pytest.mark.parametrize("facing", FACINGS)
def test_holding_the_pull_fires_the_dropper_ONCE(facing):
    """A player HOLDS a button. Without the pulse the dropper fires for as long as the button is
    down, which for a fortune teller is a machine that never stops answering - and the casino's
    own note is that its first pulse was a repeater, which delays both edges and pulses nothing."""
    w, _f, m, _p = _built("seance", facing=facing)
    spec = _spec(w)
    hop = tuple(m["rng_hopper"])
    drop = (hop[0], hop[1] + 1, hop[2])
    c = circuit.Circuit.from_cells(spec)
    c.run(8)
    assert not c.powered(drop), f"{facing}: the dropper is live at rest"
    c.press(tuple(m["inputs"][0]), ticks=24)
    high = 0
    for _ in range(28):
        c.step()
        high += int(c.powered(drop))
    assert 1 <= high <= 8, f"{facing}: a held pull drove the dropper for {high} of 28 ticks"


def test_the_seance_button_can_be_reached_on_foot():
    """A verified machine you cannot walk up to is scenery with a circuit in it."""
    w, f, m, _p = _built("seance")
    got = HW.reachable(w, f.at(m["width"] // 2, -2, -1), floor=60)
    btn = m["inputs"][0]
    assert HW.near(got, btn, 1), "nobody can reach the bell-pull"


def test_the_seance_says_what_it_cannot_verify():
    """The odds come from the ITEM MIX and the simulator has no entities. A machine that states
    odds it has not measured is the failure this whole subsystem exists to prevent, so the caveat
    and the exact required mix both travel in the sidecar."""
    _w, _f, m, _p = _built("seance")
    assert m["unverified"], "the seance claims odds it cannot check"
    assert m["stock"]["dropper"], "the required item mix is not recorded"


# ------------------------------------------------------------------ circuits.randomiser

@pytest.mark.parametrize("facing", FACINGS)
def test_the_randomisers_comparator_is_never_placed_on_its_own_hopper(facing):
    """**A REAL BUG, FOUND BY BUILDING THE SEANCE AND NOT BY READING THE CODE.** `STEP` holds
    (dx, dy, dz) and `randomiser` read `STEP[facing][1]` where it meant `[2]` - correct for east
    and west by coincidence, since their dz is 0, and for NORTH and SOUTH it gave dx=0, dz=0 and
    put the comparator inside the hopper. `casino.wheel` takes its facing from the planner, so
    every north- or south-facing game in the park shared it: legal states, affordable blocks, the
    right block count, and a machine that can never fire."""
    r = circuits.randomiser((0, 64, 0), outputs=3, facing=facing)
    assert r["comparator"] != r["hopper"], f"{facing}: the comparator is on the hopper"
    assert r["out"] not in (r["hopper"], r["comparator"], r["dropper"])
    assert len(set(r["cells"])) == 3, f"{facing}: the randomiser lost a cell to an overlap"


# ------------------------------------------------------------------ the generic gates

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_every_block_state_is_legal(kind, land):
    m = H.build(_cfg(kind, land)).to_model()
    for n in m.names:
        spec = n.split(":")[-1]
        base = spec.split("[")[0]
        if base == "air":
            continue
        props = dict(kv.split("=", 1)
                     for kv in spec[spec.index("[") + 1:-1].split(",")) if "[" in spec else {}
        assert blocks.validate(base, props) == [], f"{kind}/{land}: {spec} is not legal"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_nothing_is_currency_and_nothing_expensive_is_undeclared(kind, land):
    """DIRT IS MONEY ON THIS SERVER. And an expensive block is allowed only where the design has
    said in advance how many of them it spends and why - the casino's own posture about lamps and
    note blocks, which is a budget rather than a shrug."""
    w, _f, _m, _p = _built(kind, land)
    spent = {}
    for (name, _props) in w.cells.values():
        base = name.split(":")[-1]
        assert blocks.spendable(base), f"{kind}/{land} places CURRENCY: {base}"
        if palette.tier(base) == "expensive":
            spent[base] = spent.get(base, 0) + 1
    allowed = EXPENSIVE_ALLOWANCE.get(kind, {})
    for base, n in spent.items():
        assert n <= allowed.get(base, 0), \
            f"{kind}/{land} places {n}x {base}, which is expensive and undeclared"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_kind_is_one_connected_piece(kind, facing):
    """A stray cell is a block floating in the air. This found three of them on the clock tower's
    gallery lanterns: `_hang` guarantees a FULL block overhead and cannot guarantee the block is
    attached to anything, which is the distinction a component count exists to catch."""
    w, _f, _m, _p = _built(kind, facing=facing)
    assert _components(w) == [len(w.cells)]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_sign_has_a_solid_block_behind_it(kind, facing):
    """`park._sign` checks that SOMETHING is behind a sign; this checks it is a FULL CUBE. The
    back wall's window rhythm leaves only two-wide gaps, so a sign put on it by eye lands on
    glass - which passes `w.has`, renders identically, and the game refuses to place."""
    w, _f, _m, _p = _built(kind, facing=facing)
    step = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
    for (x, y, z), (name, props) in w.cells.items():
        if not name.endswith("_wall_sign"):
            continue
        dx, dz = step[props["facing"]]
        behind = w.name(x - dx, y, z - dz)
        assert HW.full_cube(behind), \
            f"{kind}/{facing}: the sign at {(x, y, z)} hangs on {behind!r}"
