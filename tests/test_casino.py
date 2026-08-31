"""The casino machines, against their own recorded contracts, by simulation.

A slot machine is the worst possible place to discover that a circuit does nothing: it looks
finished, it audits clean, it costs what it should, and a player presses the button and gets
nothing. Every assertion here is the machine's OWN contract, read back out of the sidecar the
generator writes - so a build whose promise changes has to change its test in the same commit.
"""
from __future__ import annotations

import pytest

from mcbuild import circuit
from mcbuild.gen import GENERATORS


def slot(**kw):
    # `slot` became `game` when this was rebuilt against the reference casino: the machine lives
    # under the floor now, and a 24-block cabinet is not what a casino game is.
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "game", "outcomes": 3,
                                    "check": False, **kw}, [])
    m = c.to_model() if hasattr(c, "to_model") else c
    return c, circuit.Circuit.of(m, c.world_origin)


def test_a_press_pays_exactly_once():
    """THE CONTRACT. A dropper that fired every tick would empty the bank into the floor.

    THE RANDOMISER GATES ON ITEMS, so the win is STATED rather than simulated: the machine's odds
    come from a dropper ejecting a uniformly random one of its slots, and this simulator has no
    entities. `fill` is how the simulator says "a container reads this much", which is exactly the
    contract it documents. An earlier version of this test passed WITHOUT the fill - and it was
    passing for the wrong reason, on a randomiser that never gated on anything.
    """
    c, sim = slot()
    btn = tuple(c.meta["inputs"][0])
    out = tuple(c.meta["outputs"][0])
    assert sim.name(btn) == "stone_button", "the connector ate the button"
    assert sim.name(out) == "dropper", "the connector ate the payout"
    hopper = (c.meta["rng_hopper"][0], c.meta["rng_hopper"][1], c.meta["rng_hopper"][2])
    sim.fill(hopper, 4)                      # a winning read, stated
    sim.press(btn, ticks=4)
    sim.run(30)
    assert sim.fired.get(out, 0) == 1, "one press must pay once, not zero and not ten"


def test_holding_the_button_still_pays_once():
    """A player HOLDS a button. This is why every input goes through a pulse first."""
    c, sim = slot()
    btn = tuple(c.meta["inputs"][0])
    out = tuple(c.meta["outputs"][0])
    sim.fill(tuple(c.meta["rng_hopper"]), 4)
    sim.set(btn, True)
    sim.run(40)
    assert sim.fired.get(out, 0) == 1


def test_an_untouched_machine_pays_nothing():
    """The house does not lose by accident."""
    c, sim = slot()
    sim.run(40)
    assert sim.fired.get(tuple(c.meta["outputs"][0]), 0) == 0


def test_the_odds_are_known_and_recorded():
    """The earlier randomiser took any N and admitted it could not say what the odds were. For a
    slot machine that is not a caveat, it is a bug: a house that does not know its own odds cannot
    know whether it is losing money. minecraft.wiki gives an equal-probability figure for exactly
    two mixes, so those are the only two on offer."""
    import pytest as _p
    from mcbuild.gen import circuits
    c, _ = slot(outcomes=3)
    assert "equally likely" in c.meta["contract"]
    assert c.meta["stock"]["dropper"], "the required item mix must travel with the build"
    assert len(c.meta["stock"]["dropper"]) == 3
    with _p.raises(ValueError, match="uniform distribution"):
        circuits.randomiser((0, 0, 0), outputs=5)


def test_the_machine_records_what_it_cannot_promise():
    """Randomness comes from item routing and this simulator has no entities. Saying so, in the
    sidecar, is the feature - a machine whose caveat lives only in a chat message is one nobody
    can audit a month later."""
    c, _ = slot()
    assert c.meta["unverified"], "the randomiser's caveat must travel with the build"
    said = " ".join(c.meta["unverified"])
    assert "ITEM MIX" in said and "no entities" in said,         "the caveat must name WHY it cannot be checked here, not just that it cannot"


def test_every_casino_kind_builds_and_records_a_contract():
    for kind in ("game", "prize_wall", "marquee", "counter"):
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


def test_the_display_is_off_and_says_why():
    """THREE ATTEMPTS DID NOT GET A SIGNAL FROM THE PIT TO THE BOARD, so the board does not ship.

    A display that looked like a readout and was not would be exactly the failure this whole
    subsystem exists to prevent: it would pass the audit, the bill of materials and the eye. What
    ships is the machine, whose contract IS verified.
    """
    from mcbuild.gen import casino
    assert casino.CASINO["display"] is False
    c, _ = slot()
    assert "display OFF" in c.meta["contract"], "the build must SAY the board is not wired"
    assert not c.meta["lamps"], "no lamps may be placed while the display cannot drive them"


def test_the_machine_still_pays_with_the_display_off():
    """The part that works must keep working when the part that does not is removed."""
    c, sim = slot()
    sim.fill(tuple(c.meta["rng_hopper"]), 4)
    sim.press(tuple(c.meta["inputs"][0]), ticks=4)
    sim.run(40)
    assert sim.fired.get(tuple(c.meta["outputs"][0]), 0) == 1
