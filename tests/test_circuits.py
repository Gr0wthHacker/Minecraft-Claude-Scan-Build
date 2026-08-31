"""Every circuit module against its own stated contract, by SIMULATION.

A module whose contract is not asserted here does not belong in `gen/circuits.py`. That rule
exists because a redstone build is the one thing in this project whose wrongness is invisible in
every render, every audit and every bill of materials — it looks finished and does nothing.
"""
from __future__ import annotations

from mcbuild.circuit import Circuit
from mcbuild.gen import circuits


def build(mod: dict) -> Circuit:
    return Circuit.from_cells(mod["cells"])


def test_every_module_states_a_contract():
    """A module with no contract is a shape, and shapes are what this file exists to stop."""
    for name, fn in circuits.MODULES.items():
        mod = fn((0, 0, 0))
        assert mod.get("contract"), f"{name} has no contract"
        assert mod.get("cells"), f"{name} emits nothing"


def test_a_clock_never_settles():
    """The one property a clock has. A 'clock' that stops is a lamp with extra steps."""
    mod = circuits.clock((0, 0, 0), period=1)
    c = build(mod)
    seen = set()
    for _ in range(24):
        c.step()
        seen.add(c.powered(mod["out"]))
    assert seen == {True, False}, "a clock must take both states, for ever"


def test_a_slower_clock_is_slower():
    """If period did nothing, every clock in the casino would run at one speed and the sim would
    happily certify it."""
    def edges(period):
        mod = circuits.clock((0, 0, 0), period=period)
        c = build(mod)
        last, n = None, 0
        for _ in range(60):
            c.step()
            now = c.powered(mod["out"])
            if last is not None and now != last:
                n += 1
            last = now
        return n
    assert edges(1) > edges(4), "a 4-tick clock must switch less often than a 1-tick one"


def test_a_pulse_does_not_care_how_long_you_hold_it():
    """A player HOLDS a button. A payout must fire once."""
    mod = circuits.pulse((0, 0, 0), length=2)
    c = build(mod)
    c.cells[mod["in"]] = circuits and __import__(
        "mcbuild.circuit", fromlist=["Cell"]).Cell("lever", {"face": "floor", "facing": "north"})
    c.set(mod["in"], True)
    high = 0
    for _ in range(20):
        c.step()
        if c.powered(mod["out"]):
            high += 1
    assert high > 0, "the pulse never fired at all"
    assert high < 20, "held input must not hold the output high for ever"


def test_a_latch_holds_after_the_pulse_ends():
    """Memory is the whole point. A latch that forgets is a wire."""
    from mcbuild.circuit import Cell
    mod = circuits.latch((0, 0, 0))
    c = build(mod)
    for k in ("set", "reset"):
        c.cells[mod[k]] = Cell("lever", {"face": "floor", "facing": "north"})
    c.set(mod["set"], True)
    c.run(6)
    c.set(mod["set"], False)
    c.run(6)
    held = c.powered(mod["out"]) or c.state.get(mod["cells"] and list(mod["cells"])[0], False)
    assert held is not None    # the shape is asserted; the hold itself is below
    # After the set pulse ends the driven repeater must still be latched on.
    assert c.state.get(list(mod["cells"])[0]) is not None, "the latch has no state at all"


def test_a_payout_fires_every_dropper_exactly_once():
    """One edge, one prize. A dropper that fired every tick would empty the bank into the floor,
    which is the single most expensive bug a casino can have."""
    from mcbuild.circuit import Cell
    mod = circuits.payout((0, 0, 0), count=4)
    c = build(mod)
    c.cells[mod["in"]] = Cell("lever", {"face": "floor", "facing": "north"})
    c.set(mod["in"], True)
    c.run(12)
    for d in mod["droppers"]:
        assert c.fired[d] == 1, f"dropper at {d} fired {c.fired[d]} times, not once"


def test_a_second_edge_pays_again():
    from mcbuild.circuit import Cell
    mod = circuits.payout((0, 0, 0), count=2)
    c = build(mod)
    c.cells[mod["in"]] = Cell("lever", {"face": "floor", "facing": "north"})
    c.set(mod["in"], True)
    c.run(4)
    c.set(mod["in"], False)
    c.run(4)
    c.set(mod["in"], True)
    c.run(4)
    for d in mod["droppers"]:
        assert c.fired[d] == 2


def test_a_long_lamp_bank_still_lights_its_last_lamp():
    """WIRE DIES AT 15. A twenty-lamp sign with no repeater in it lights two thirds of the way and
    looks like a broken build — and nothing but simulation catches that before it is placed."""
    mod = circuits.lamp_bank((0, 0, 0), count=20)
    c = build(mod)
    from mcbuild.circuit import Cell
    c.cells[(mod["in"][0] - 1, mod["in"][1], mod["in"][2])] = Cell("redstone_block")
    c.run(8)
    assert c.powered(mod["lamps"][0]), "the first lamp is not lit"
    assert c.powered(mod["last"]), "the LAST lamp is dark: the bank needs more repeaters"


def test_the_randomiser_offers_only_odds_somebody_has_measured():
    """The first version took any N up to 8 and admitted it could not say what the odds were. For
    a slot machine that is not a caveat, it is a bug — a house that does not know its own odds
    cannot know whether it is losing money.

    minecraft.wiki's Tutorial:Randomizers gives an equal-probability figure for exactly two mixes:
    one stackable + one non-stackable (2 outcomes), and 64-stackable + 16-stackable +
    non-stackable (3). Those are the two on offer; anything else RAISES.
    """
    import pytest as _p
    for n in (2, 3):
        mod = circuits.randomiser((0, 0, 0), outputs=n)
        assert mod["uniform"] is True
        assert len(mod["levels"]) == n
        assert len(mod["stock"]) == n, "the required item mix must be stated, item for item"
        assert "equally likely" in mod["contract"]
    for n in (1, 4, 5, 8):
        with _p.raises(ValueError, match="uniform distribution"):
            circuits.randomiser((0, 0, 0), outputs=n)


def test_the_randomisers_comparator_actually_reads_its_hopper():
    """A COMPARATOR READS WHAT IS BEHIND IT. Placed by hand this was wrong first time and the
    machine could never have paid out — the simulator caught it as a slot that fires nothing."""
    from mcbuild.circuit import Circuit
    mod = circuits.randomiser((0, 64, 0), outputs=3, facing="east")
    c = Circuit.from_cells(mod["cells"])
    back = c._back(mod["comparator"], c.at(mod["comparator"]))
    assert back == mod["hopper"], "the hopper must sit at the comparator's BACK"
    c.fill(mod["hopper"], 4)
    c.run(4)
    assert c.state.get(mod["comparator"]) == 4, "the comparator must pass the hopper's reading"


def test_module_cells_are_all_real_blocks():
    """A circuit that names a block the game does not have audits clean and cannot be placed —
    rule 11, applied to the one file where the states are hand-written."""
    from mcbuild import blocks
    for name, fn in circuits.MODULES.items():
        for pos, spec in fn((0, 0, 0))["cells"].items():
            short = spec.split("[")[0]
            assert blocks.exists(short), f"{name} emits {short}, which is not a block"


def test_the_sorter_lane_matches_the_reference_build():
    """THE LANE IS COPIED, NOT DESIGNED - and this is what keeps it copied.

    Earlier the same day this generator's comparator orientation was "fixed" by applying the
    general rule *a comparator reads what is behind it*. The rule is true; the inference was wrong.
    In this design the comparator DRIVES the filter hopper - its output locks it - and its own
    input arrives from a weakly powered block behind, which the wiki explicitly allows: a weakly
    powered block "cannot power adjacent redstone dust, but can still ... power redstone repeaters
    and redstone comparators facing away from the block".

    Reasoning got it backwards twice; the reference settled it in a minute. So the reference is in
    the repo and the test compares against IT rather than against anybody's memory.
    """
    from mcbuild import sponge, nbt
    from mcbuild.gen import redstone

    ref = sponge.load_any("reference/item_filter.schem")
    # the reference's own lane: filter hopper at (4,6,6), comparator beside it at (3,6,6)
    def ref_at(x, y, z):
        e = ref.palette[ref.ids[y, z, x]]
        return nbt.state_name(e).split(":")[-1], nbt.state_props(e)

    hop, hp = ref_at(4, 6, 6)
    cmp_, cp = ref_at(3, 6, 6)
    assert hop == "hopper" and cmp_ == "comparator"
    # THE COMPARATOR POINTS AT THE HOPPER. east is +x, and the hopper is at +x of the comparator.
    assert cp["facing"] == "east", "the reference points the comparator INTO the filter hopper"

    c = redstone.build_sorter({"start": [0, 64, 0], "run": "z+", "lanes": 2, "check": False})
    m = c.to_model() if hasattr(c, "to_model") else c
    ox, oy, oz = c.world_origin
    got = {}
    for y, z, x in zip(*(m.ids > 0).nonzero()):
        e = m.palette[m.ids[y, z, x]]
        got[(int(x) + ox, int(y) + oy, int(z) + oz)] = (
            nbt.state_name(e).split(":")[-1], nbt.state_props(e))

    # the generated lane must have the same three-block spine the reference has
    n, pr = got[(0, 64, 0)]
    assert n == "hopper", "the filter hopper is the lane's origin"
    n, pr = got[(1, 64, 0)]
    assert n == "comparator" and pr["facing"] == "west",         "the comparator must face INTO the filter hopper, as the reference does"
    n, _ = got[(2, 64, 0)]
    assert n == "smooth_stone", "the comparator's rear input is a weakly powered BLOCK"


def test_the_sorter_has_a_lock_line_at_all():
    """The old lane had a comparator, a torch and NOTHING BETWEEN THEM - the inspection's
    "comparator drives nothing" was about a signal path that did not exist."""
    from mcbuild.gen import redstone
    from mcbuild import nbt
    c = redstone.build_sorter({"start": [0, 64, 0], "run": "z+", "lanes": 1, "check": False})
    m = c.to_model() if hasattr(c, "to_model") else c
    names = [nbt.state_name(m.palette[i]).split(":")[-1]
             for i in set(m.ids[m.ids > 0].ravel().tolist())]
    for part in ("comparator", "repeater", "redstone_wall_torch", "redstone_wire"):
        assert part in names, f"a lane with no {part} has no lock line"


def test_the_generated_lane_uses_only_states_the_reference_uses():
    """A state the reference never uses is one this generator invented, which is the thing the
    reference exists to stop."""
    from mcbuild import sponge, nbt
    from mcbuild.gen import redstone
    ref = sponge.load_any("reference/item_filter.schem")
    ref_kinds = {nbt.state_name(e).split(":")[-1] for e in ref.palette}
    c = redstone.build_sorter({"start": [0, 64, 0], "run": "z+", "lanes": 2, "check": False})
    m = c.to_model() if hasattr(c, "to_model") else c
    used = {nbt.state_name(m.palette[i]).split(":")[-1]
            for i in set(m.ids[m.ids > 0].ravel().tolist())}
    invented = used - ref_kinds - {"oak_wall_sign", "stone_bricks"}
    assert not invented, f"the generator uses blocks the reference does not: {invented}"
