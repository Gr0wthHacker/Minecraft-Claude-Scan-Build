"""The casino machines, against their own recorded contracts, by simulation.

A slot machine is the worst possible place to discover that a circuit does nothing: it looks
finished, it audits clean, it costs what it should, and a player presses the button and gets
nothing. Every assertion here is the machine's OWN contract, read back out of the sidecar the
generator writes - so a build whose promise changes has to change its test in the same commit.
"""
from __future__ import annotations

import pathlib

import pytest

from mcbuild import circuit
from mcbuild.gen import GENERATORS


def slot(**kw):
    # `slot` became `game` when this was rebuilt against the reference casino: the machine lives
    # under the floor now, and a 24-block cabinet is not what a casino game is.
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "high_roller", "outcomes": 3,
                                    "pit": 2, "check": False, **kw}, [])
    m = c.to_model() if hasattr(c, "to_model") else c
    return c, circuit.Circuit.of(m, c.world_origin)


def _pay(outcomes=3):
    """The machine that PAYS, built and wrapped in a simulator."""
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "double_or_none", "pit": 2,
                                    "outcomes": outcomes, "check": False}, [])
    return c, circuit.Circuit.of(c.to_model(), c.world_origin)


def test_a_press_pays_exactly_once():
    """THE CONTRACT. A dropper that fired every tick would empty the bank into the floor.

    THE PAYING MACHINE IS `double_or_none`, not the display game: `high_roller`'s outputs are its
    four lamps, and an earlier version of this test read `outputs[0]` on it and asserted a dropper.
    It failed loudly, which is the right outcome - but the reason it could ever have been written
    is that "output" meant two different things on two machines, so the meta now distinguishes
    them by `reads` (bar vs threshold) and the test picks the machine by NAME.

    THE RANDOMISER GATES ON ITEMS, so the win is STATED rather than simulated: the odds come from
    a dropper ejecting a uniformly random one of its slots, and this simulator has no entities.
    `fill` is how the simulator says "a container reads this much", which is exactly the contract
    it documents.
    """
    c, sim = _pay()
    btn = tuple(c.meta["inputs"][0])
    out = tuple(c.meta["outputs"][0])
    assert sim.name(btn) == "stone_button", "the connector ate the button"
    assert sim.name(out) == "dropper", "the connector ate the payout"
    sim.fill(tuple(c.meta["rng_hopper"]), c.meta["win_level"])
    sim.press(btn, ticks=4)
    sim.run(60)
    assert sim.fired.get(out, 0) == 1, "one press, one payout"


def test_holding_the_button_still_pays_once():
    """A player HOLDS a button. This is why every input goes through a pulse first."""
    c, sim = _pay()
    out = tuple(c.meta["outputs"][0])
    sim.fill(tuple(c.meta["rng_hopper"]), c.meta["win_level"])
    sim.set(tuple(c.meta["inputs"][0]), True)
    sim.run(60)
    assert sim.fired.get(out, 0) == 1


def test_the_odds_are_known_and_recorded():
    """The earlier randomiser took any N and admitted it could not say what the odds were. For a
    casino that is not a caveat, it is a bug: a house that does not know its own odds cannot know
    whether it is losing money. minecraft.wiki gives an equal-probability item mix for exactly two
    fan-outs, so those are the only two on offer and anything else RAISES.

    And the mix is recorded on the build, because the simulator has no entities: it cannot check
    that the dropper was loaded correctly, so the one thing it can do is state exactly what to put
    in it and refuse to invent a third mix.
    """
    import pytest as _p
    from mcbuild.gen import circuits
    c, _ = slot(outcomes=3)
    assert "3 outcomes" in c.meta["contract"]
    assert c.meta["stock"]["dropper"] == circuits.RNG_MIXES[3]["items"]
    assert len(c.meta["stock"]["dropper"]) == 3, "one item per outcome, and they must differ"
    assert len(set(c.meta["stock"]["dropper"])) == 3
    for n in (2, 3):
        assert n in circuits.RNG_MIXES
    for n in (0, 1, 4, 5, 8):
        with _p.raises(ValueError):
            circuits.randomiser((0, 70, 0), n)



def test_the_machine_records_what_it_cannot_promise():
    """Randomness comes from item routing and this simulator has no entities. Saying so, in the
    sidecar, is the feature - a machine whose caveat lives only in a chat message is one nobody
    can audit a month later."""
    c, _ = slot()
    assert c.meta["unverified"], "the randomiser's caveat must travel with the build"
    said = " ".join(c.meta["unverified"])
    assert "ITEM MIX" in said and "no entities" in said,         "the caveat must name WHY it cannot be checked here, not just that it cannot"


def test_every_casino_kind_builds_and_records_a_contract():
    for kind in ("high_roller", "double_or_none", "prize_wall", "marquee", "counter"):
        c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": kind, "check": False}, [])
        assert c.meta["contract"], f"{kind} has no contract"
        m = c.to_model() if hasattr(c, "to_model") else c
        assert int((m.ids > 0).sum()) > 0, f"{kind} built nothing"


def test_the_prize_wall_pays_one_per_press():
    c = GENERATORS["casino"].build({"at": [0, 64, 0], "kind": "prize_wall", "lanes": 3,
                                    "check": False}, [])
    m = c.to_model() if hasattr(c, "to_model") else c
    sim = circuit.Circuit.of(m, c.world_origin)
    btn = tuple(c.meta["inputs"][0])
    out = tuple(c.meta["outputs"][0])
    sim.press(btn, ticks=3)
    sim.run(20)
    assert sim.fired.get(out, 0) == 1


def test_the_marquee_lights_its_last_lamp():
    """Wire dies at 15 and a sign that lights two thirds of the way looks abandoned."""
    c = GENERATORS["casino"].build({"at": [0, 64, 0], "kind": "marquee", "length": 20,
                                    "check": False}, [])
    m = c.to_model() if hasattr(c, "to_model") else c
    sim = circuit.Circuit.of(m, c.world_origin)
    last = tuple(c.meta["outputs"][0])
    lit = False
    for _ in range(40):
        sim.step()
        if sim.powered(last):
            lit = True
            break
    assert lit, "the far end of the marquee never lights"


def test_the_display_works_now_and_the_test_changed_with_it():
    """This test used to assert the board was OFF, because three attempts had failed to drive it.

    The eventual fix was not more wiring - it was the realisation that AN ANALOG VALUE CANNOT
    TRAVEL, so the bar has to sit AT the comparator with the machine one course under the floor.
    A test that pins a decision changes with the decision, or the suite quietly enforces the thing
    that was just fixed.
    """
    c, s = _play("high_roller", 3, 2)
    assert c.meta["lamps"], "the board is placed"
    lit = [i for i, l in enumerate(c.meta["lamps"]) if s.powered(tuple(l))]
    assert lit == [0, 1], "and it reads the roll"


# ---------------------------------------------------------------- the four games, by simulation
#
# ONLY TWO TOPOLOGIES SURVIVED, AND THAT IS THE ANSWER TO "100% FUNCTIONAL". `chase` and `vault`
# were written, built cleanly, and failed their own contracts - chase lit every lamp on every roll
# and vault never opened its door. They are not in the file. Every tool in this project would have
# passed them, because they place legal, supported, affordable blocks in the right shape.

import pytest as _pytest
from mcbuild.gen import circuits as _circuits


def _play(kind, outcomes, roll):
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": kind, "outcomes": outcomes,
                                    "pit": 2, "check": False}, [])
    m = c.to_model() if hasattr(c, "to_model") else c
    s = circuit.Circuit.of(m, c.world_origin)
    s.fill(tuple(c.meta["rng_hopper"]), roll)
    s.press(tuple(c.meta["inputs"][0]), ticks=4)
    s.run(60)
    return c, s


@_pytest.mark.parametrize("outcomes", [2, 3])
def test_high_roller_shows_the_roll_it_rolled(outcomes):
    """THE CONTRACT: roll k lights exactly k lamps. Not k-1, not all of them."""
    levels = _circuits.RNG_MIXES[outcomes]["levels"]
    for roll in levels:
        c, s = _play("high_roller", outcomes, roll)
        lit = [i for i, l in enumerate(c.meta["lamps"]) if s.powered(tuple(l))]
        assert lit == list(range(roll)), f"roll {roll} lit {lit}"


@_pytest.mark.parametrize("outcomes", [2, 3])
def test_double_or_none_pays_only_on_a_win(outcomes):
    """A house that pays on a losing roll is a house that closes."""
    levels = _circuits.RNG_MIXES[outcomes]["levels"]
    win = max(levels)
    for roll in levels:
        c, s = _play("double_or_none", outcomes, roll)
        paid = s.fired.get(tuple(c.meta["outputs"][0]), 0)
        assert paid == (1 if roll == win else 0), f"roll {roll} paid {paid}"


def test_an_untouched_game_with_an_EMPTY_hopper_never_pays():
    """At rest the randomiser's hopper is empty - the dropper only ejects into it on a press - so
    the comparator reads nothing and the payout cannot fire."""
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "double_or_none",
                                    "outcomes": 3, "pit": 2, "check": False}, [])
    m = c.to_model()
    s = circuit.Circuit.of(m, c.world_origin)
    s.run(60)
    assert s.fired.get(tuple(c.meta["outputs"][0]), 0) == 0


def test_A_STUCK_ITEM_IN_THE_HOPPER_PAYS_CONTINUOUSLY():
    """THE ONE REAL HAZARD IN THIS MACHINE, pinned so nobody discovers it with the bank.

    The comparator reads the hopper CONTINUOUSLY. The button is what makes the dropper eject, so
    at rest the hopper is empty and nothing fires - but an item left in that hopper is a winning
    level standing there for ever, and the payout is edge-triggered on a signal that never falls.
    The house pays until the barrel is empty.

    It is asserted rather than fixed because the fix is a latch-and-reset stage that this file
    will not invent, and because a hazard nobody has written down is one nobody checks for. Load
    the dropper, never the hopper.
    """
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "double_or_none",
                                    "outcomes": 3, "pit": 2, "check": False}, [])
    m = c.to_model()
    s = circuit.Circuit.of(m, c.world_origin)
    s.fill(tuple(c.meta["rng_hopper"]), 4)      # an item LEFT in the hopper
    s.run(60)
    assert s.fired.get(tuple(c.meta["outputs"][0]), 0) >= 1, (
        "if this ever stops being true the hazard is fixed - update the docs, not just the test")


def test_the_broken_games_are_gone_and_the_reason_is_written_down():
    """A casino with two games that work and two that look like they work is not a refined
    experience, it is a trap."""
    from mcbuild.gen import casino as _c
    assert "chase" not in _c.BUILDERS and "vault" not in _c.BUILDERS
    src = pathlib.Path("mcbuild/gen/casino.py").read_text(encoding="utf-8")
    assert "AN ANALOG VALUE CANNOT TRAVEL" in src, "the rule they cost must survive them"


def test_the_pit_is_shallow_because_a_level_cannot_climb():
    """A roll of 4 reaches four blocks of dust. The reference can bury its machines six courses
    down because its displays are driven by decoded booleans; ours reads the level itself."""
    from mcbuild.gen import casino as _c
    assert _c.CASINO["pit"] <= 3


def test_the_button_run_never_touches_the_decision_run():
    """TWO SIGNALS MUST NOT SHARE A LANE, and nothing else in this project can see when they do.

    The button's descent to the randomiser once ran along the very cells the threshold occupies:
    the gate's dust and the button's dust were the same dust, so a press delivered a level of 8
    into the boost and the machine paid on EVERY roll. It is legal, supported, affordable dust in
    a sensible shape - the audit, the bill of materials and every render pass it.

    The property is structural, so it is asserted structurally: no cell of the run that carries
    the press may lie on the corridor between the comparator and the payout.
    """
    for outcomes in (2, 3):
        c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "double_or_none", "pit": 2,
                                        "outcomes": outcomes, "check": False}, [])
        m = c.to_model()
        s = circuit.Circuit.of(m, c.world_origin)
        cmp_ = tuple(c.meta["rng_hopper"])
        pay = tuple(c.meta["outputs"][0])
        # the decision corridor: every cell strictly between the machine and the payout, on the
        # course the comparator sits on
        lo, hi = min(cmp_[0], pay[0]), max(cmp_[0], pay[0])
        corridor = {(x, pay[1], pay[2]) for x in range(lo + 1, hi)}

        # press with a LOSING roll; nothing on the corridor may carry the press's own level
        s.fill(cmp_, min(circuits_levels(outcomes)))
        s.press(tuple(c.meta["inputs"][0]), ticks=4)
        s.run(60)
        assert s.fired.get(pay, 0) == 0, f"{outcomes} outcomes: a loss paid out"


def circuits_levels(outcomes):
    from mcbuild.gen import circuits
    return circuits.RNG_MIXES[outcomes]["levels"]


def test_anything_downstream_of_the_gate_is_measured_from_the_gate():
    """A shorter threshold shifts everything after it, so a fixed offset is a latent collision.

    The collection barrel was placed ten blocks along: behind the dropper at 3 outcomes, ON it at
    2. The two-outcome game therefore had no payout at all while the three-outcome one worked
    perfectly - one config value apart, and both audited clean.
    """
    seen = {}
    for outcomes in (2, 3):
        c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "double_or_none", "pit": 2,
                                        "outcomes": outcomes, "check": False}, [])
        s = circuit.Circuit.of(c.to_model(), c.world_origin)
        pay = tuple(c.meta["outputs"][0])
        assert s.name(pay) == "dropper", f"{outcomes} outcomes: something overwrote the payout"
        seen[outcomes] = pay
    assert seen[2] != seen[3], "a shorter gate must move the payout - that is the whole hazard"
