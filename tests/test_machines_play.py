"""DRIVE THE INPUT, ASSERT THE OUTPUT. Every machine in the park, played rather than inspected.

Jack: *"i think a number of the redstone things like plinko are likely fully non-functional"*. The
per-kind suites already assert each machine's own contract, and the reason that was not enough is
recorded in this repo twice over:

  * **`circuits.window` shipped as a threshold for months** and three casino games paid on any
    value at or above the mark. The simulator AGREED with the broken build, because a repeater's
    side read ambient block power by a route Minecraft does not have.
  * **The whole input half of two casino machines was unexercised**, because their tests drove the
    randomiser's hopper with `Circuit.fill` - which STATES a roll rather than rolling one - and
    never pressed the button at all. Both shipped unable to pay at any odds.

So everything here starts at the thing a PLAYER touches and ends at the thing a player sees. Where
the input is an entity the simulator cannot make - a ball falling into a hopper, an arrow in a
target, a shovelful of gravel - the entity half is stated as a container level or a signal, exactly
as `circuit.set_signal` and `Circuit.fill` are documented to be used, and it is listed in the
build's own `unverified` rather than being quietly assumed away.

**AND EVERY MACHINE MUST RESET.** A game that pays once and latches is a game that pays once.
"""
from __future__ import annotations

import pytest

from mcbuild.circuit import Circuit
from mcbuild.gen import arcade, casino, frontiertown, hollowmanor, spectacle, ticketing

FACINGS = ("east", "west", "north", "south")


def build(mod, kind, land=None, **cfg):
    p = {"at": [0, 64, 0], "facing": "east", "kind": kind, **cfg}
    if land:
        p["land"] = land
    return mod.build(p)


def sim(c):
    return Circuit.of(c.to_model(), c.world_origin)


def fired(s, cells):
    return sum(s.fired.get(tuple(d), 0) for d in cells)


# =========================================================================== PLINKO
#
# Jack named it, so it is first and it is asserted channel by channel rather than "a ball pays
# something". The whole point of a plinko board is that WHERE the ball lands decides what you get,
# and a machine that pays every lane on every ball is exactly as clean in an audit as one that
# does not - this build shipped that once, with the lanes two apart, and only a lane-by-lane
# assertion could ever have caught it.


def _plinko(**cfg):
    c = build(arcade, "plinko", "midway", **cfg)
    return c, c.meta


@pytest.mark.parametrize("lanes", [3, 5, 7])
def test_a_ball_pays_its_own_channel_and_nothing_else(lanes):
    """THE CONTRACT, one channel at a time. A ball read by channel k fires channel k's droppers -
    all of them, exactly once each - and every other channel does nothing at all."""
    c, m = _plinko(lanes=lanes)
    assert len(m["hoppers"]) == lanes
    for k in range(lanes):
        s = sim(c)
        s.fill(tuple(m["hoppers"][k]), 1)          # ONE ball, in channel k
        s.run(40)
        for j in range(lanes):
            got = fired(s, m["droppers"][j])
            want = m["prizes"][j] if j == k else 0
            assert got == want, (
                f"{lanes} lanes, ball in channel {k}: channel {j} fired {got}, wanted {want}")


@pytest.mark.parametrize("facing", FACINGS)
def test_the_channels_stay_apart_at_every_facing(facing):
    """A machine that is correct east and crossed north is a machine nobody rotated. The lanes are
    laid along the frontage, so a facing change re-derives every one of their coordinates."""
    c = build(arcade, "plinko", "midway", facing=facing)
    m = c.meta
    for k in range(m["lanes"]):
        s = sim(c)
        s.fill(tuple(m["hoppers"][k]), 1)
        s.run(40)
        paid = [j for j in range(m["lanes"]) if fired(s, m["droppers"][j])]
        assert paid == [k], f"{facing}: a ball in channel {k} paid channels {paid}"


def test_the_outer_channels_are_worth_more_than_the_middle():
    """WHAT MAKES IT A BET RATHER THAN A DROP. The pegs make the outside hard to reach, so the
    outside is where the prize is; a flat payout is a machine with no reason to aim."""
    _c, m = _plinko(lanes=5)
    assert m["prizes"] == [3, 2, 1, 2, 3]
    assert m["prizes"][0] > m["prizes"][len(m["prizes"]) // 2]


def test_an_empty_board_pays_nothing_at_all():
    """The control, and it is not free: a machine wired to a permanent source pays on load, and
    every assertion above would still pass."""
    c, m = _plinko()
    s = sim(c)
    s.run(60)
    assert sum(s.fired.values()) == 0, "the board paid with no ball in it"


def test_a_ball_left_in_the_hopper_pays_once_and_only_once():
    """**THE HOUSE MUST NOT BE ABLE TO LOSE BY ACCIDENT.** A hopper holding a ball reads a level
    for as long as the ball is in it. `_award` puts a pulse between the reading and the payout so
    a held reading is ONE prize; without it a jammed channel empties the bank."""
    c, m = _plinko()
    s = sim(c)
    s.fill(tuple(m["hoppers"][0]), 1)
    s.run(200)                                     # ...and it never comes out
    assert fired(s, m["droppers"][0]) == m["prizes"][0]


def test_the_board_is_playable_again_after_a_ball():
    """A machine that pays once and latches is a machine that pays once."""
    c, m = _plinko()
    s = sim(c)
    s.fill(tuple(m["hoppers"][1]), 1)
    s.run(40)
    first = fired(s, m["droppers"][1])
    s.fill(tuple(m["hoppers"][1]), 0)              # the ball drops through into the barrel
    s.run(20)
    s.fill(tuple(m["hoppers"][1]), 1)              # ...and the next player drops one
    s.run(40)
    assert fired(s, m["droppers"][1]) == 2 * first, "the second ball paid a different prize"


def test_a_stronger_reading_does_not_pay_more():
    """A hopper reads its FULLNESS, so a channel that happened to collect several balls before
    anyone emptied it must not pay several prizes on the strength of the number alone."""
    c, m = _plinko()
    one = sim(c)
    one.fill(tuple(m["hoppers"][2]), 1)
    one.run(60)
    many = sim(c)
    many.fill(tuple(m["hoppers"][2]), 9)
    many.run(60)
    assert fired(many, m["droppers"][2]) == fired(one, m["droppers"][2])


def test_every_channel_has_a_hopper_a_barrel_and_its_own_droppers():
    """The physical half, because the circuit half cannot see it: a channel with no hopper is a
    channel a ball falls through, and this simulator has no entities to notice."""
    c, m = _plinko()
    s = sim(c)
    seen = set()
    for k, h in enumerate(m["hoppers"]):
        h = tuple(h)
        assert s.name(h) == "hopper", f"channel {k} has {s.name(h)} where its hopper should be"
        assert s.name((h[0], h[1] - 1, h[2])) == "barrel", f"channel {k} has nothing to collect in"
        assert m["droppers"][k], f"channel {k} pays nothing"
        for d in m["droppers"][k]:
            d = tuple(d)
            assert s.name(d) == "dropper", f"channel {k} has {s.name(d)} for a prize dropper"
            assert d not in seen, f"channel {k} shares a dropper with another channel"
            seen.add(d)


# =========================================================================== the bells


@pytest.mark.parametrize("kind", ["range", "strength", "weigh"])
@pytest.mark.parametrize("facing", FACINGS)
def test_a_bell_stands_on_a_block_and_not_on_the_wire_that_rings_it(kind, facing):
    """**A FLOOR BELL NEEDS A FLOOR, AND ALL THREE OF THEM WERE STANDING ON REDSTONE DUST.** The
    range, the high striker and the scale each hung their bell in the cell directly above the wire
    that rings it, with `attachment=floor` - a state the game will not place and a bell that pops
    the moment anyone loads the chunk. Three games' only audible output.

    Every check in this pipeline passed it: the state is legal, the block is cheap, the cell counts
    as supported, and no render shows a bell falling off. Only asking what is UNDER it does."""
    from mcbuild import blocks
    c = build(arcade, kind, "midway", facing=facing)
    bell = tuple(c.meta["bell"])
    s = sim(c)
    assert s.name(bell) == "bell"
    under = s.name((bell[0], bell[1] - 1, bell[2]))
    assert blocks.is_full_cube(under), f"{kind}/{facing}: the bell stands on {under}"


@pytest.mark.parametrize("kind", ["range", "strength", "weigh"])
def test_the_bell_still_rings_where_it_now_stands(kind):
    """Moving it off the wire is worth nothing if it stopped being rung by it. A bell answers to
    any redstone power that reaches it, so beside the run works exactly as well as on top of it -
    which is the claim, so it is the assertion."""
    c = build(arcade, kind, "midway")
    m = c.meta
    bell = tuple(m["bell"])
    s = sim(c)
    s.run(4)
    assert not s.powered(bell), f"{kind}: the bell rings at rest"
    DRIVERS[("arcade", kind)](s, m)
    assert any(_ever_on(s, [bell], 60)), f"{kind}: a winning go did not ring the bell"


# =========================================================================== the quiet room's door


@pytest.mark.parametrize("facing", FACINGS)
def test_the_quiet_rooms_door_is_a_whole_door_at_the_height_of_a_body(facing):
    """**IT WAS HALF A DOOR, TWO COURSES OVER A PLAYER'S HEAD.** Built at h=2 and h=3 with the far
    wall drawn afterwards over h=3, the upper leaf was overwritten by wool the same tick it was
    placed - so the corridor ended in a lower door leaf that blocked nothing at all, in a game
    whose entire point is that the alarm shuts the way out. Every existing test passed: the door
    was powered, unpowered, correct in every facing, and irrelevant.

    A door is at the two courses a body occupies, and it has two halves."""
    c = build(arcade, "quiet", "midway", facing=facing)
    m = c.meta
    s = sim(c)
    lower = tuple(m["door"])
    upper = (lower[0], lower[1] + 1, lower[2])
    assert s.name(lower) == "iron_door", f"{facing}: the door's lower half is {s.name(lower)}"
    assert s.name(upper) == "iron_door", f"{facing}: the door's upper half is {s.name(upper)}"
    assert s.at(lower).prop("half") == "lower" and s.at(upper).prop("half") == "upper"
    # ...and it stands ON the floor, which is what makes it a doorway rather than a hatch.
    floor = (lower[0], lower[1] - 1, lower[2])
    from mcbuild import blocks
    assert blocks.is_full_cube(s.name(floor)), f"{facing}: the door stands on {s.name(floor)}"


@pytest.mark.parametrize("facing", FACINGS)
def test_the_quiet_rooms_corridor_is_clear_of_its_own_machine(facing):
    """The machine used to run at the standing course, three bands of dust and comparators straight
    across the floor the game asks you to cross. It is under the chequer now, which is both the
    cover and better physics: the wool a player is picking their way over is the thing between
    their footsteps and the sensor."""
    c = build(arcade, "quiet", "midway", facing=facing)
    m = c.meta
    s = sim(c)
    door = tuple(m["door"])
    wiring = {"redstone_wire", "repeater", "comparator", "redstone_torch", "redstone_wall_torch"}
    at_or_above = [p for p, cell in s.cells.items()
                   if cell.name in wiring and p[1] >= door[1]]
    assert not at_or_above, f"{facing}: {len(at_or_above)} wiring cell(s) at or above the floor"


# =========================================================================== every other machine
#
# One driver per kind, written the way a player operates that machine - press the button, pull the
# lever, put the ticket in the slot, turn the pages to the combination - and one assertion that the
# thing a player can SEE actually did something. The per-kind suites carry the detailed contracts;
# what this adds is that every machine in the park is exercised from its own input, in one file,
# and that a kind added later without a driver FAILS rather than being quietly skipped.

MODS = {
    "arcade": (arcade, "midway"),
    "casino": (casino, None),
    "ticketing": (ticketing, "midway"),
    "spectacle": (spectacle, "midway"),
    "frontiertown": (frontiertown, "frontier"),
    "hollowmanor": (hollowmanor, "hollow"),
}


def _press(s, m):
    s.press(tuple(m["inputs"][0]), 4)


def _ticket(s, m):
    """A TICKET IS A PULSE, NOT A LEVEL. A hopper holds the item for a moment and passes it on."""
    s.fill(tuple(m["inputs"][0]), 3)
    s.run(4)
    s.fill(tuple(m["inputs"][0]), 0)


def _arm_and_fire(s, m):
    s.set(tuple(m["lever"]), True)
    s.run(6)
    s.press(tuple(m["button"]), 10)


def _casino_roll(s, m):
    """PRESS THE BUTTON, and state the roll the dropper would have made. The press is the half
    that was never exercised; the roll is the half no simulator can make."""
    s.fill(tuple(m["rng_hopper"]), m.get("win_level") or 4)
    if "house_hopper" in m:
        s.fill(tuple(m["house_hopper"]), 1)
    s.press(tuple(m["inputs"][0]), 4)


DRIVERS = {
    ("arcade", "range"): lambda s, m: s.set_signal(tuple(m["targets"][2]), m["score"]),
    ("arcade", "strength"): lambda s, m: s.set_signal(tuple(m["inputs"][0]), 15),
    ("arcade", "weigh"): lambda s, m: s.fill(tuple(m["plate"]), m["target"]),
    ("arcade", "safe"): lambda s, m: [s.fill(tuple(d), v)
                                      for d, v in zip(m["dials"], m["combo"])],
    ("arcade", "quiet"): lambda s, m: s.fill(tuple(m["sensors"][0]), m["trip"]),
    ("arcade", "prizecounter"): lambda s, m: [s.fill(tuple(b), 8) for b in m["barrels"]],
    ("arcade", "plinko"): lambda s, m: s.fill(tuple(m["hoppers"][0]), 1),
    ("arcade", "reaction"): _press,
    ("casino", "high_roller"): _casino_roll,
    ("casino", "double_or_none"): _casino_roll,
    ("casino", "lucky_number"): _casino_roll,
    ("casino", "duel"): _casino_roll,
    ("casino", "wheel"): lambda s, m: (s.fill(tuple(m["rng_hopper"]), 1),
                                       s.press(tuple(m["inputs"][0]), 4)),
    ("casino", "prize_wall"): _press,
    ("casino", "counter"): lambda s, m: [s.fill(tuple(b), 8) for b in m["barrels"]],
    ("ticketing", "ticketgate"): _ticket,
    ("ticketing", "turnstile"): _press,
    ("ticketing", "ridegate"): _press,
    ("spectacle", "fireworks"): lambda s, m: s.set(tuple(m["inputs"][0]), True),
    ("frontiertown", "sluice"): lambda s, m: s.fill(tuple(m["barrel"]), 3),
    ("frontiertown", "powderhouse"): _arm_and_fire,
    ("hollowmanor", "seance"): lambda s, m: (s.fill(tuple(m["rng_hopper"]), 4),
                                             s.press(tuple(m["inputs"][0]), 4)),
    ("hollowmanor", "ossuary"): lambda s, m: [s.set(tuple(lv), True) for lv in m["levers"]],
    ("hollowmanor", "manor"): lambda s, m: s.set(tuple(m["inputs"][0]), True),
}

# Kinds with no input at all - a viewing terrace, a queue, a graveyard. They are architecture and
# the census already names a machine with no input as an ornament; there is nothing to drive.
PROPS = {
    ("casino", "marquee"), ("casino", "hall"),
    ("ticketing", "boxoffice"), ("ticketing", "queue"), ("ticketing", "lockers"),
    ("spectacle", "bandstand_show"), ("spectacle", "foodcourt"), ("spectacle", "viewing"),
    ("spectacle", "leaderboard"),
    ("frontiertown", "saloon"), ("frontiertown", "watertower"), ("frontiertown", "windmill"),
    ("frontiertown", "minehead"), ("frontiertown", "falsefront"),
    ("frontiertown", "trestlebridge"),
    ("hollowmanor", "crypt"), ("hollowmanor", "clocktower"), ("hollowmanor", "graveyard"),
    ("hollowmanor", "deadtree"), ("hollowmanor", "irongate"),
}

PLAYABLE = sorted(DRIVERS)


def _ever_on(s, outs, ticks):
    seen = [False] * len(outs)
    for _ in range(ticks):
        s.step()
        for i, o in enumerate(outs):
            if s.powered(o):
                seen[i] = True
    return seen


def test_every_kind_is_either_driven_here_or_declared_a_prop():
    """**A KIND ADDED WITHOUT A DRIVER MUST FAIL, NOT BE SKIPPED.** A suite that quietly ignores
    what it does not recognise reports success and proves nothing, which is how the whole lowland
    scene once measured 0% built for its entire life."""
    for name, (mod, _land) in MODS.items():
        for kind in mod.BUILDERS:
            assert (name, kind) in DRIVERS or (name, kind) in PROPS, (
                f"{name}/{kind} is neither driven nor declared a prop - write a driver for it")
    for key in list(DRIVERS) + list(PROPS):
        mod, _land = MODS[key[0]]
        assert key[1] in mod.BUILDERS, f"{key} names a kind that no longer exists"


@pytest.mark.parametrize("name,kind", PLAYABLE, ids=[f"{n}-{k}" for n, k in PLAYABLE])
def test_the_input_a_player_touches_makes_something_a_player_can_see_happen(name, kind):
    """END TO END, from the block you press to the block you watch.

    Deliberately weak about WHAT happens - the per-kind suites own that - and completely strict
    about the two things a "non-functional" machine fails: it does nothing when you use it, or it
    does something when nobody has."""
    mod, land = MODS[name]
    c = build(mod, kind, land)
    m = c.meta
    outs = [tuple(o) for o in (m.get("outputs") or [])]
    assert outs, f"{name}/{kind} declares no output a player could see"

    s = sim(c)
    s.run(4)
    DRIVERS[(name, kind)](s, m)
    on = _ever_on(s, outs, 80)
    paid = sum(s.fired.values())
    assert any(on) or paid, f"{name}/{kind}: the input did nothing at all"


@pytest.mark.parametrize("name,kind", PLAYABLE, ids=[f"{n}-{k}" for n, k in PLAYABLE])
def test_nothing_happens_to_a_machine_nobody_is_using(name, kind):
    """THE CONTROL, and it is not free. A machine wired to a permanent source does its whole trick
    on chunk load; every "it responds" assertion above passes on one just as comfortably.

    The two kinds with a free-running clock are exempt BY NAME and for a stated reason - a
    firework show and a marquee are supposed to run themselves - rather than by a rule that would
    quietly excuse the next machine that latches on."""
    if (name, kind) in {("spectacle", "fireworks"), ("arcade", "reaction")}:
        pytest.skip("free-running by design: a firework show and the reaction game's travelling "
                    "light both run themselves, and the light IS the invitation to play")
    mod, land = MODS[name]
    c = build(mod, kind, land)
    m = c.meta
    outs = [tuple(o) for o in (m.get("outputs") or [])]
    s = sim(c)
    idle = _ever_on(s, outs, 80)
    # `quiet` is the one machine whose OUTPUT IS HELD OPEN at rest - the door, and the alarm is
    # what takes it away. Asserted the other way round it would demand the opposite machine.
    if kind == "quiet":
        assert idle[0], "the quiet room's door must be held OPEN until something makes a noise"
        assert not any(idle[1:]), "the alarm lamps are lit with nothing making a sound"
    else:
        assert not any(idle), f"{name}/{kind}: {sum(idle)} output(s) came on with nobody there"
    assert sum(s.fired.values()) == 0, f"{name}/{kind}: it paid out with nobody there"


@pytest.mark.parametrize("name,kind", PLAYABLE, ids=[f"{n}-{k}" for n, k in PLAYABLE])
def test_a_machine_can_be_used_twice(name, kind):
    """**A GAME THAT PAYS ONCE AND LATCHES IS A GAME THAT PAYS ONCE**, and it looks perfect until
    the second player. Every kind here is driven, released, and driven again."""
    if (name, kind) in {("spectacle", "fireworks"), ("arcade", "reaction")}:
        pytest.skip("free-running: a second trigger is not distinguishable from the first cycle")
    mod, land = MODS[name]
    c = build(mod, kind, land)
    m = c.meta
    outs = [tuple(o) for o in (m.get("outputs") or [])]

    def once(s):
        DRIVERS[(name, kind)](s, m)
        on = _ever_on(s, outs, 80)
        return any(on) or sum(s.fired.values()) > 0

    s = sim(c)
    s.run(4)
    assert once(s), f"{name}/{kind}: the first go did nothing"
    # release everything a player could be holding, and let it settle
    for pos in list(s.inputs):
        s.set(pos, False)
    for pos in list(s.container):
        s.fill(pos, 0)
    for pos in list(s.signals):
        s.set_signal(pos, 0)
    s.run(40)
    before = sum(s.fired.values())
    assert once(s), f"{name}/{kind}: the second go did nothing - it latched or it jammed"
    assert sum(s.fired.values()) >= before
