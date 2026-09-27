"""The park's ticketing, against its own recorded contracts - by SIMULATION where it carries a
signal, and by measurement where it does not.

A barrier is the worst possible place to discover that a circuit does nothing. It looks finished,
it audits clean, it costs what it should, and a player drops a ticket in and stands there. Every
mechanical assertion here drives `mcbuild.circuit` and reads the answer out of the world the
generator built, never out of the generator's own intentions.

Four of these pin a fault that was PRODUCED while building this module, each of which had shipped
a build that looked completely correct:

    the delay lane wired with plain dust taps      -> the barrier latched wide open, for ever
    one tap at the end of the lane instead of all  -> the door flickered shut and open again
    the GO lamp hung over the doorway              -> it touched nothing and could never light
    the button's staircase in the paving course    -> opening lane two opened lane one as well
"""
from __future__ import annotations

import pathlib
from collections import deque

import pytest

from mcbuild import blocks, circuit, palette
from mcbuild.gen import GENERATORS, park, ticketing
from mcbuild.gen.vertical import World

KINDS = sorted(ticketing.BUILDERS)
GATES = ("ticketgate", "turnstile", "ridegate")
LANDS = sorted(park.LANDS)
FACINGS = ("east", "north", "west", "south")

# Long enough for the power-on transient to clear. A redstone torch loads LIT, so on the first
# tick every lane's output torch is on and the door is briefly powered; the second torch settles
# it. That is what the game does on chunk load too, and a test that reads "at rest" before it
# clears is testing the transient.
SETTLE = 12


def _cfg(kind, land="midway", facing="east", **kw):
    return {**ticketing.TICKETING, "at": [0, 70, 0], "kind": kind, "land": land,
            "facing": facing, "title": kind.upper(), **kw}


def _build(kind, **kw):
    return GENERATORS["ticketing"].build(_cfg(kind, **kw), [])


def _sim(kind, **kw):
    c = _build(kind, **kw)
    return c, circuit.Circuit.of(c.to_model(), c.world_origin)


def _world(kind, land="midway", facing="east", **kw):
    """The raw World, so a test can ask about cells in WORLD coordinates.

    Asserting in world coordinates rather than canvas ones is a rule this repo already paid for:
    a canvas is sized to its own content, so it shifts between two builds with different settings
    and anything comparing them lines up against nothing.
    """
    p = _cfg(kind, land, facing, **kw)
    w = World()
    ticketing.BUILDERS[kind](w, p, None)
    for pos, (name, _pr) in list(w.cells.items()):
        if name == "air":
            del w.cells[pos]
    return w, park._Frame(p), park.LANDS[land], p


def _components(cells):
    seen, sizes = set(), []
    for start in cells:
        if start in seen:
            continue
        q = deque([start])
        seen.add(start)
        n = 0
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


# ------------------------------------------------------------------ THE MECHANISM, BY SIMULATION

def _open_trace(kind, ticks=70, lane=0, hold_in=4, **kw):
    """Trigger one lane and record, tick by tick, whether each lane's door is powered."""
    c, s = _sim(kind, **kw)
    s.run(SETTLE)
    doors = [tuple(d) for d in c.meta["outputs"]]
    rest = [s.powered(d) for d in doors]
    if kind == "ticketgate":
        hop = tuple(c.meta["inputs"][lane])
        s.fill(hop, 3)
    else:
        s.press(tuple(c.meta["inputs"][lane]), ticks=hold_in)
    trace = []
    for t in range(ticks):
        if kind == "ticketgate" and t == hold_in:
            s.fill(tuple(c.meta["inputs"][lane]), 0)     # the hopper passes the ticket on
        s.step()
        trace.append([s.powered(d) for d in doors])
    return c, s, rest, trace


@pytest.mark.parametrize("kind", GATES)
def test_at_rest_every_door_is_closed(kind):
    """THE FIRST HALF OF THE CONTRACT, and the half a broken build passes by accident.

    A barrier that is open at rest is not a barrier, and one torch instead of two gives exactly
    that - it is the reason there are two.
    """
    _c, _s, rest, _tr = _open_trace(kind, ticks=1)
    assert rest == [False] * len(rest), f"{kind}: a door is powered with nothing driving it"


@pytest.mark.parametrize("kind", GATES)
def test_the_trigger_opens_the_door_and_it_closes_again(kind):
    """The whole point. Open on the trigger, and CLOSED again afterwards - a barrier that latches
    open is worse than one that never opens, because nothing about it looks wrong."""
    _c, _s, _rest, tr = _open_trace(kind)
    lane0 = [row[0] for row in tr]
    assert any(lane0), f"{kind}: the trigger did nothing at all"
    assert not lane0[-1], f"{kind}: the door is still open after {len(tr)} ticks - it latched"


@pytest.mark.parametrize("kind", GATES)
def test_the_hold_has_no_gap_in_it(kind):
    """A DELAY CHAIN DELAYS BOTH EDGES; IT DOES NOT EXTEND A PULSE.

    Tapped only at the end of the lane, the output is the direct pulse and then, some ticks later,
    a second one - the door shuts and opens again in the player's face. Every stage is tapped so
    the taps overlap. This is the assertion that keeps them.
    """
    _c, _s, _rest, tr = _open_trace(kind)
    lane0 = "".join(str(int(row[0])) for row in tr)
    assert "0" not in lane0.strip("0"), f"{kind}: the door flickers - {lane0[:40]}"


@pytest.mark.parametrize("kind", GATES)
def test_the_door_stays_open_long_enough_to_walk_through(kind):
    """A hopper holds its ticket for about four redstone ticks, so with no hold at all the door
    would open for under half a second. The hold is the whole reason this module has a delay lane
    and a crawlspace the length of one."""
    c, _s, _rest, tr = _open_trace(kind)
    ticks = sum(int(row[0]) for row in tr)
    assert ticks >= 2 * c.meta["stages"] + 3, f"{kind}: open for only {ticks} ticks"


@pytest.mark.parametrize("kind", GATES)
def test_one_lane_opening_does_not_open_the_others(kind):
    """LANES ARE INDEPENDENT MACHINES AND THIS IS WHY THEY COST A SPARE COLUMN EACH.

    The version that failed this had its button's staircase in the paving course, one block from
    the NEXT lane's door paving - the single block in a lane that is strongly powered while the
    door is open. Each lane simulated perfectly on its own.
    """
    _c, _s, _rest, tr = _open_trace(kind, lanes=2)
    assert any(row[0] for row in tr), "lane 0 never opened"
    assert not any(row[1] for row in tr), f"{kind}: opening lane 0 also opened lane 1"


@pytest.mark.parametrize("kind", GATES)
def test_a_second_trigger_opens_it_again(kind):
    """A one-shot barrier is a barrier that admits one visitor a day."""
    c, s = _sim(kind, lanes=1)
    s.run(SETTLE)
    door = tuple(c.meta["outputs"][0])
    inp = tuple(c.meta["inputs"][0])
    opened = 0
    for _shot in range(2):
        if kind == "ticketgate":
            s.fill(inp, 3)
        else:
            s.press(inp, ticks=4)
        span = 0
        for t in range(50):
            if kind == "ticketgate" and t == 4:
                s.fill(inp, 0)
            s.step()
            span += int(s.powered(door))
        opened += 1 if span else 0
    assert opened == 2, "the second ticket did nothing"


@pytest.mark.parametrize("hold_in", [2, 4, 8])
def test_it_works_for_any_realistic_length_of_input(hold_in):
    """THE INPUT LENGTH IS THE GAME'S NUMBER, NOT OURS.

    A hopper passes an item on in 8 game ticks and a pressure plate holds for 10 after you step
    off; this simulator has no entities, so the honest thing is to assert the circuit across the
    range those fall in rather than to pick one and hope. A one-tick input is deliberately not in
    the list: a repeater swallows a pulse shorter than its own delay, which is real behaviour and
    is why nothing here is triggered by a one-tick edge.
    """
    _c, _s, _rest, tr = _open_trace("turnstile", hold_in=hold_in, lanes=1)
    lane0 = "".join(str(int(row[0])) for row in tr)
    assert "1" in lane0, f"an input of {hold_in} ticks did nothing"
    assert "0" not in lane0.strip("0"), f"an input of {hold_in} ticks flickers: {lane0[:40]}"
    assert lane0.rstrip("0") != lane0, "it never closed"


def test_the_ride_gates_lamp_is_lit_exactly_while_the_lane_is_open():
    """A GO LAMP THAT CAN DISAGREE WITH THE DOOR IS WORSE THAN NO LAMP.

    Two placements were built and simulated before this one: over the doorway, where it touches
    nothing that is ever powered and could not have lit at all; and beside the door, where the
    torch that is lit when the barrier is SHUT lights it - a lamp saying GO at rest.
    """
    c, s = _sim("ridegate", lanes=1)
    s.run(SETTLE)
    lamp = tuple(c.meta["lamps"][0])
    door = tuple(c.meta["outputs"][0])
    assert s.name(lamp) == "redstone_lamp"
    assert not s.powered(lamp), "the GO lamp is lit at rest"
    s.press(tuple(c.meta["inputs"][0]), ticks=4)
    lit = door_on = 0
    for _ in range(60):
        s.step()
        lit += int(s.powered(lamp))
        door_on += int(s.powered(door))
    assert lit > 0, "the lamp never lit"
    assert abs(lit - door_on) <= 2, f"lamp lit {lit} ticks, door open {door_on} - they disagree"


def test_the_generator_did_not_eat_its_own_components():
    """Every mechanism this module places must still BE there in the finished model.

    A connector that overwrites the thing it connects is the bug that ate the first casino's
    button and its payout dropper, and it audits perfectly clean.
    """
    for kind in GATES:
        c, s = _sim(kind, lanes=2)
        for pos in c.meta["outputs"]:
            assert s.name(tuple(pos)) == "iron_door", f"{kind}: something overwrote a door"
        for pos in c.meta["inputs"]:
            want = "hopper" if kind == "ticketgate" else "stone_button"
            assert s.name(tuple(pos)) == want, f"{kind}: something overwrote the trigger"


def test_A_TICKET_LEFT_IN_THE_READ_HOPPER_HOLDS_THE_LANE_OPEN():
    """THE ONE REAL HAZARD, pinned deliberately rather than hidden.

    The comparator reads the hopper continuously, so an item that never leaves is a signal that
    never falls. In the world it cannot happen while the collection barrel has room - the hopper
    drains itself in 8 game ticks - so the failure mode is 'the barrel is full', and the fix is
    to empty it through the hatch.

    It is asserted rather than fixed because the fix is a latch-and-reset stage this module will
    not invent, and because a hazard nobody has written down is one nobody checks for.
    """
    c, s = _sim("ticketgate", lanes=1)
    s.run(SETTLE)
    s.fill(tuple(c.meta["inputs"][0]), 3)
    s.run(60)
    assert s.powered(tuple(c.meta["outputs"][0])), (
        "if this ever stops being true the hazard is gone - update the docs, not just the test")
    assert c.meta["hazards"], "the hazard must travel with the build, not only with the test"


# ------------------------------------------------------------------ THE HAZARDS THE SIM CANNOT SEE

# What actually disables a hopper: anything that POWERS it. A torch powers all six of its
# neighbours; dust powers what it connects to; a block of redstone powers everything touching it;
# a button or lever strongly powers what it is fixed to. A repeater or comparator is NOT in this
# set, because it drives its FRONT and nothing else - which is why the comparator that READS the
# ticket hopper is allowed to sit behind it, and is checked separately below.
_DISABLES_A_HOPPER = {"redstone_wire", "redstone_torch", "redstone_wall_torch",
                      "redstone_block", "stone_button", "lever"}


@pytest.mark.parametrize("kind", GATES)
def test_no_hopper_touches_a_torch_or_any_wiring(kind):
    """**A HOPPER BESIDE A LIT REDSTONE TORCH IS DISABLED**, and `mcbuild.circuit` has no model of
    a hopper's enabled flag - so nothing in this repo could simulate this failure.

    It matters more than it sounds. A disabled read hopper never passes its ticket on, so the
    comparator goes on reading it, so the door stays open, so the torch stays lit: the barrier is
    latched wide open by a circuit that simulates perfectly. It is designed out - the machine runs
    forward under the forecourt and the ticket runs backward into the hall - and this is what
    keeps it that way.
    """
    w, _f, _pal, _p = _world(kind, lanes=2)
    hoppers = {pos for pos, (n, _p2) in w.cells.items() if n == "hopper"}
    for (x, y, z) in hoppers:
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nb = w.cells.get((x + d[0], y + d[1], z + d[2]))
            if nb and nb[0] in _DISABLES_A_HOPPER:
                raise AssertionError(f"{kind}: a hopper at {(x, y, z)} touches {nb[0]} - it would "
                                     f"be disabled by it, and the simulator cannot see that")
    # ...and nothing may be POINTED at a hopper either. A comparator behind one is how it is read;
    # a comparator or repeater pointing INTO one is a hopper that has been switched off.
    for (x, y, z), (name, props) in w.cells.items():
        if name not in ("repeater", "comparator"):
            continue
        dx, _dy, dz = circuit.DIRS[props["facing"]]
        assert (x + dx, y, z + dz) not in hoppers, \
            f"{kind}: a {name} at {(x, y, z)} points into a hopper and disables it"


@pytest.mark.parametrize("kind", GATES)
def test_the_collection_barrel_can_actually_be_emptied(kind):
    """A barrel that cannot be reached fills after 27 tickets and the lane jams for good.

    The paving over it is a trapdoor - walkable shut, opened to reach the barrel below - and the
    test is that there IS a barrel and that what is over it is not solid paving.
    """
    if kind != "ticketgate":
        pytest.skip("only the ticket gate collects anything")
    w, _f, _pal, _p = _world(kind, lanes=2)
    barrels = [pos for pos, (n, _p2) in w.cells.items() if n == "barrel"]
    assert len(barrels) == 2, f"expected one collection barrel per lane, got {len(barrels)}"
    for (x, y, z) in barrels:
        above = w.cells.get((x, y + 1, z))
        assert above and above[0].endswith("_trapdoor"), \
            f"the barrel at {(x, y, z)} is sealed under {above and above[0]}"


# ------------------------------------------------------------------ it builds, and it is legal

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_kind_builds_at_every_land_and_facing(kind, land, facing):
    c = _build(kind, land=land, facing=facing)
    assert c.to_model().ids.size > 0


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_every_block_state_is_legal(kind, land):
    """Rule 11: ask the game, not your memory. A state the game does not have audits clean here
    and is refused in Litematica an hour later."""
    m = _build(kind, land=land).to_model()
    for n in m.names:
        spec = n.split(":")[-1]
        base = spec.split("[")[0]
        if base == "air":
            continue
        props = {}
        if "[" in spec:
            props = dict(kv.split("=", 1) for kv in spec[spec.index("[") + 1:-1].split(","))
        assert blocks.validate(base, props) == [], f"{kind}/{land}: {spec} is not a legal state"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_nothing_is_currency_or_off_the_1_19_allowlist(kind, land):
    """DIRT AND GRASS ARE MONEY ON THIS SERVER - which is the joke at the heart of this module,
    since grass is what a ticket is bought WITH. It is still not something to build out of."""
    m = _build(kind, land=land).to_model()
    for n in m.names:
        base = n.split(":")[-1].split("[")[0]
        if base == "air":
            continue
        assert blocks.spendable(base), f"{kind}/{land} places CURRENCY: {base}"
        assert blocks.available(base), f"{kind}/{land} places {base}, not on the 1.19 allowlist"


@pytest.mark.parametrize("kind", KINDS)
def test_the_only_expensive_block_is_the_lamp_and_it_is_budgeted(kind):
    """`redstone_lamp` is the one block in the game that lights on a signal and it is expensive
    here. There is no cheap substitute - the nearest cheap colour match is a plank, which is a
    lamp that does not light, and A LIGHT CANNOT BE SUBSTITUTED BY COLOUR. So it is COUNTED into
    the build's budget, as `gen/casino.py` counts its own, and used two at a time."""
    c = _build(kind)
    m = c.to_model()
    dear = {n.split(":")[-1].split("[")[0] for n in m.names
            if n.split(":")[-1].split("[")[0] != "air"
            and palette.tier(n.split(":")[-1].split("[")[0]) == "expensive"}
    assert dear <= set(ticketing.BUDGETED), f"{kind} places unbudgeted expensive blocks: {dear}"
    for name in dear:
        assert c.meta["budget"].get(name), f"{kind} places {name} without counting it"
        assert c.meta["budget"][name] <= 4, f"{kind} places {c.meta['budget'][name]}x {name}"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_kind_is_one_connected_piece(kind, facing):
    """6-CONNECTIVITY: a diagonal neighbour is not a neighbour. A stray cell is a block floating
    in the air, and on the park's own kinds this check found three of them on its first run."""
    w, _f, _pal, _p = _world(kind, facing=facing)
    sizes = _components(set(w.cells))
    assert sizes == [len(w.cells)], f"{kind}/{facing}: {len(sizes)} pieces, largest {sizes[0]}"


# ------------------------------------------------------------------ signs

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_sign_has_a_block_and_a_support_behind_it(kind, facing):
    """The fault `park._sign` exists for: a sign hung on the one column that has an OPENING in it.
    A wall sign floating in air draws exactly like one on a wall, so no render catches it, and
    connectivity only catches some of them - a sign can be adjacent to a canopy above it and
    still have nothing to hang from."""
    w, _f, _pal, _p = _world(kind, facing=facing)
    for (x, y, z) in w.signs:
        assert (x, y, z) in w.cells, "sign TEXT with no sign BLOCK is a corrupt region"
        _name, props = w.cells[(x, y, z)]
        fdx, fdz = park._STEP[props["facing"]]
        assert (x - fdx, y, z - fdz) in w.cells, f"{kind}: sign at {(x, y, z)} has no support"


@pytest.mark.parametrize("kind", KINDS)
def test_no_sign_line_is_wider_than_a_sign(kind):
    """Fifteen characters renders; twenty is a line cut off mid-word, and that only shows up in a
    screenshot after the build has been placed."""
    w, _f, _pal, _p = _world(kind, title="A VERY LONG ATTRACTION NAME INDEED", price="99 grass")
    for t in w.signs.values():
        for line in list(t["front"]) + list(t["back"]):
            assert len(line) <= ticketing.SIGN_WIDTH, f"{kind}: {line!r} clips"


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_carries_its_own_name(kind):
    """A sign the support guard REFUSED is a sign that silently is not there - which is this
    project's most-repeated failure shape, and it is why this test exists rather than a glance."""
    w, _f, _pal, _p = _world(kind, title="NAMEPLATE")
    assert any("NAMEPLATE" in line for t in w.signs.values() for line in t["front"]), \
        f"{kind} dropped its nameplate and nothing noticed"


def test_the_price_board_names_the_currency():
    """The whole economy of the park in one line: a ticket costs GRASS, which is what this server
    uses for money. A board that does not say the price is a board nobody reads."""
    w, _f, _pal, _p = _world("boxoffice", price="8 grass")
    said = " ".join(line for t in w.signs.values() for line in t["front"])
    assert "8 grass" in said, "the price board does not print the price"
    assert "TICKETS" in said


def test_the_barrier_says_what_to_do_with_the_ticket():
    """A mechanism nobody is told how to use is a mechanism nobody uses."""
    w, _f, _pal, _p = _world("ticketgate")
    said = " ".join(line for t in w.signs.values() for line in t["front"]).lower()
    assert "insert" in said and "slot" in said


# ------------------------------------------------------------------ the architecture

@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("kind", GATES)
def test_you_can_walk_through_a_lane(kind, facing):
    """A THRESHOLD, NOT A FACADE WITH A HOLE IN IT. The wall is two deep and both courses of a
    lane are open, with the door in the outer one - so you pass through the barrier rather than
    past it, and the door is the only thing in the way."""
    w, f, pal, p = _world(kind, facing=facing, lanes=2)
    meta = ticketing.BUILDERS[kind](World(), p, None)
    for i in meta["lane_i"]:
        assert w.name(*f.at(i, 1, 0)) is None, "the inner course of a lane is blocked"
        assert w.name(*f.at(i, 1, 1)) is None, "the inner course of a lane is blocked"
        for h in (0, 1):
            assert w.name(*f.at(i, 0, h)) == "iron_door", "the lane has no door in it"


def test_the_queue_is_one_walk_with_two_ends():
    """A SWITCHBACK WHOSE LAST LEG IS CLOSED IS A PEN. Measured by walking it: flood the standing
    course from the entrance and require the exit to be reached, and require the walk to be long
    enough that it actually folds rather than running straight down the middle."""
    w, f, _pal, p = _world("queue", width=11, depth=9)
    meta = ticketing.BUILDERS["queue"](World(), p, None)
    width, depth = meta["width"], meta["depth"]
    free = {(i, d) for i in range(width) for d in range(depth)
            if w.name(*f.at(i, d, 0)) is None}
    start = (0, 0)
    assert start in free, "there is no way in"
    seen, q = {start}, deque([start])
    while q:
        i, d = q.popleft()
        for (di, dd) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (i + di, d + dd)
            if nb in free and nb not in seen:
                seen.add(nb)
                q.append(nb)
    far = [(i, d) for (i, d) in seen if d >= depth - 1]
    assert far, "the queue does not reach the far end - it is a dead end"
    assert len(seen) > width * 2, "the walk is too short to have folded at all"
    assert meta["legs"] >= 3, "a queue with two legs is a corridor"


def test_the_lockers_leave_room_to_stand_in_front_of_them():
    """RULE 10: about three blocks of working room around anything you use. A locker wall you
    cannot stand in front of is a wall of decoration."""
    w, f, _pal, p = _world("lockers", bays=6)
    meta = ticketing.BUILDERS["lockers"](World(), p, None)
    depth = meta["depth"]
    for k in range(meta["bays"]):
        i = k + 1
        clear = [d for d in range(depth - 2) if w.name(*f.at(i, d, 1)) is None
                 and w.name(*f.at(i, d, 2)) is None]
        assert len(clear) >= 3, f"locker {k}: only {len(clear)} clear courses in front of it"


def test_the_box_office_can_be_seen_into_and_served_from():
    """A HALL YOU CANNOT SEE INTO IS A SHED - the casino's eighteen sealed grey cubes are the
    failure being avoided. Every serving hatch is open for two courses and has a chest behind it
    with a clear cell above, or the game will not let anybody open it."""
    w, f, _pal, p = _world("boxoffice", windows=3)
    meta = ticketing.BUILDERS["boxoffice"](World(), p, None)
    for pos in meta["chests"]:
        assert w.cells[tuple(pos)][0] == "chest"
        assert (pos[0], pos[1] + 1, pos[2]) not in w.cells, "a chest with a block over it"
    width = meta["width"]
    open_cells = [i for i in range(1, width - 1)
                  if w.name(*f.at(i, 0, 2)) is None and w.name(*f.at(i, 0, 3)) is None]
    assert len(open_cells) >= meta["windows"], "the counter is walled up"


@pytest.mark.parametrize("land", LANDS)
def test_every_lantern_hangs_from_a_full_block(land):
    """Rule 9, and the lowland's own note: a lamp under a SLAB cap reads as 'hanging from air' in
    the audit, because a slab is not a full block."""
    for kind in KINDS:
        w, _f, _pal, _p = _world(kind, land=land)
        for (x, y, z), (name, props) in w.cells.items():
            if name not in ("lantern", "soul_lantern") or props.get("hanging") != "true":
                continue
            above = w.cells.get((x, y + 1, z))
            assert above and blocks.is_full_cube(above[0]), \
                f"{kind}/{land}: a hanging lantern at {(x, y, z)} has nothing solid over it"


# ------------------------------------------------------------------ the record

@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_records_a_contract(kind):
    """A module with no contract is a shape, and shapes are what this file exists to stop."""
    c = _build(kind)
    assert c.meta["contract"], f"{kind} states no contract"
    assert c.meta["kind"].startswith("ticketing/")
    assert isinstance(c.meta["unverified"], list)


def test_the_box_office_records_why_it_has_no_mechanism():
    """THE ARITHMETIC MUST TRAVEL WITH THE BUILD. Watching the vending chest is the obvious design
    and it cannot work: a comparator reads floor(1 + 14 * fullness), and one stackable item out of
    a 27-slot chest moves fullness by 1/(64*27) against the 1/14 needed. A gate built on it would
    audit clean, cost what it should and never open once.

    Recorded on the build rather than in a chat message, so the next person to have the idea finds
    the answer instead of re-deriving it.
    """
    c = _build("boxoffice")
    said = " ".join(c.meta["unverified"])
    assert "27" in said and "fullness" in said
    assert "hopper" in said, "the version that DOES work must be named, not just the one that does not"


def test_the_module_says_the_pulse_primitive_is_not_used_and_why():
    """`circuits.pulse` claims to turn an input of any length into a fixed-length pulse. Measured
    against the simulator it does not: a held input gives a held output, so it is a DELAY. This
    module's hold is built from repeaters whose behaviour was measured here instead, and saying so
    is what stops the next person reaching for the primitive that reads as if it would do."""
    src = pathlib.Path("mcbuild/gen/ticketing.py").read_text(encoding="utf-8")
    assert "circuits.pulse" in src and "IS NOT USED" in src


def test_an_unknown_kind_or_land_raises_rather_than_defaulting():
    """An unmatched name RAISES rather than quietly falling back to the first entry in the
    catalogue - the planner's own rule, for the same reason."""
    with pytest.raises(ValueError):
        GENERATORS["ticketing"].build(_cfg("carousel"), [])
    with pytest.raises(ValueError):
        GENERATORS["ticketing"].build(_cfg("queue", land="atlantis"), [])
    with pytest.raises(ValueError):
        GENERATORS["ticketing"].build({**_cfg("queue"), "at": None}, [])
