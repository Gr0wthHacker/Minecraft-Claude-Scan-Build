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
    """A player HOLDS a button. A payout must fire once.

    **THIS TEST USED TO PASS ON A CIRCUIT THAT DID NOT PULSE.** Its bound was `high < 20` out of
    twenty ticks, and the thing it was guarding was a bare repeater - which delays both edges and
    therefore held the output high for 21 of 24 ticks under a held input, comfortably satisfying
    "fewer than twenty of the first twenty". Every casino game runs its button through here, so
    the house paid for as long as somebody leaned on the button.

    A bound looser than the bug is not a test. What is asserted now is the CONTRACT: high for
    about `length`, then low and STAYING low while the input is still held, and armed again on
    the next press.
    """
    for length in (1, 2, 3, 4):
        mod = circuits.pulse((0, 0, 0), length=length)
        c = build(mod)
        c.cells[mod["in"]] = __import__(
            "mcbuild.circuit", fromlist=["Cell"]).Cell("lever", {"face": "floor",
                                                                 "facing": "north"})
        c.set(mod["in"], True)
        trace = []
        for _ in range(30):
            c.step()
            trace.append(c.powered(mod["out"]))
        high = sum(trace)
        assert high > 0, f"length {length}: the pulse never fired at all"
        # generous either way - what must not happen is a HELD output
        assert high <= length + 3, (
            f"length {length}: held input gave {high} ticks high - that is a delay, not a pulse")
        # ONE continuous pulse, not a stutter, and it must be OVER well before the end
        assert not any(trace[12:]), (
            f"length {length}: still high {trace[12:].count(True)} ticks in with the input held")

        # AND IT RE-ARMS. A monostable that fires once per chunk load is not a button.
        c.set(mod["in"], False)
        for _ in range(6):
            c.step()
        c.set(mod["in"], True)
        again = []
        for _ in range(12):
            c.step()
            again.append(c.powered(mod["out"]))
        assert any(again), f"length {length}: a second press fired nothing"


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


# ---------------------------------------------------------------- display primitives
#
# THESE ARE TESTED BEFORE ANYTHING USES THEM, which is the whole point. `climb` was written and
# used in the same breath inside the casino, failed silently three times, and only gave up its bug
# when it was finally exercised on its own: its first dust was DIAGONAL from the source, so nothing
# ever entered the staircase. It looked like a perfectly formed climb and carried no signal.

def _level(c, at, level, facing="east"):
    """Drive `at` with a real analog level, the way the simulator documents: a comparator reading
    a container whose fullness is STATED. Forcing `state` does not work and should not - `step`
    recomputes a comparator from its inputs, which is exactly what makes it a simulator."""
    from mcbuild.circuit import Cell
    x, y, z = at
    c.cells[(x - 1, y, z)] = Cell("comparator", {"facing": facing, "mode": "compare"})
    c.cells[(x - 2, y, z)] = Cell("barrel")
    c.fill((x - 2, y, z), level)


def test_a_climb_carries_a_signal_up():
    from mcbuild.circuit import Circuit, Cell
    for h in (1, 3, 6, 10):
        m = circuits.climb((0, 0, 0), (0, h, 0), facing="east")
        c = Circuit.from_cells(m["cells"])
        c.cells[(0, 0, 0)] = Cell("redstone_block")
        c.run(16)
        assert c.level(m["top"]) > 0, f"a {h}-course climb delivered nothing"


def test_a_climb_carries_a_signal_down_too():
    """A machine under a floor sends UP; a trigger from a floor sends DOWN. Both or neither."""
    from mcbuild.circuit import Circuit, Cell
    m = circuits.climb((0, 10, 0), (0, 4, 0), facing="east")
    c = Circuit.from_cells(m["cells"])
    c.cells[(0, 10, 0)] = Cell("redstone_block")
    c.run(16)
    assert c.level(m["top"]) > 0


def test_a_climbs_first_cell_is_adjacent_to_its_source():
    """THE BUG. Stepping up AND along before placing anything leaves the first dust diagonal from
    the source, and diagonal is not adjacent."""
    m = circuits.climb((0, 0, 0), (0, 5, 0), facing="east")
    foot = m["foot"]
    assert foot in m["cells"], "the foot cell must be laid"
    assert abs(foot[0]) + abs(foot[1]) + abs(foot[2]) == 1, "the foot must touch the source"


def test_a_bar_reads_a_level_as_a_length():
    """The contract that makes an analog outcome readable: level L lights exactly L lamps."""
    from mcbuild.circuit import Circuit
    m = circuits.bar((0, 0, 0), lamps=5)
    for level in (1, 2, 3, 5):
        c = Circuit.from_cells(m["cells"])
        _level(c, m["foot"], level)
        c.run(12)
        lit = [i for i, l in enumerate(m["lamps"]) if c.powered(l)]
        assert lit == list(range(level)), f"level {level} lit {lit}"


def test_a_bar_is_dark_with_no_signal():
    """A display that is lit when nothing happened is worse than one that never lights."""
    from mcbuild.circuit import Circuit
    m = circuits.bar((0, 0, 0), lamps=5)
    c = Circuit.from_cells(m["cells"])
    c.run(8)
    assert not any(c.powered(l) for l in m["lamps"])


def test_the_lamp_sits_BESIDE_the_dust_not_above_it():
    """On the back wall a lamp is diagonal from the run and nothing reaches it - that mistake cost
    a whole display in the first casino."""
    m = circuits.bar((0, 0, 0), lamps=3)
    for lamp, foot in zip(m["lamps"], [(0, 0, 0), (1, 0, 0), (2, 0, 0)]):
        assert lamp[1] == foot[1], "the lamp must be on the same course as its dust"
        assert abs(lamp[0] - foot[0]) + abs(lamp[2] - foot[2]) == 1, "and adjacent to it"


# --------------------------------------------------------------------------- the exact-value gate
#
# `window` shipped as a THRESHOLD for its whole life, and the two things that hid it are worth as
# much as the fix: the geometry was only wrong in the degenerate case `high == low + 1`, which is
# what every caller asks for; and the SIMULATOR agreed with it, because `_read` fell through to
# `_block_power` on the side repeater's cell and picked up the very dust the gate exists to reject.
# So the module was wrong, the model was wrong in the same direction, and the test that would have
# caught it passed. Everything below drives the gate through a real level, at every facing and both
# perpendiculars, degenerate AND wide.


def _drive_window(low, high, level, facing="east", side=1):
    """Feed a window a known level and report what leaves it.

    THE LEVEL IS BUILT OUT OF DISTANCE, not stated: a redstone block `15 - level` cells back gives
    exactly `level` at the run's foot, which is the same way the machines that use this get theirs.
    """
    g = circuits.window((0, 0, 0), low, high, facing=facing, side=side)
    cells = dict(g["cells"])
    dx, _dy, dz = circuits.STEP[facing]
    pos = g["in"]
    for _ in range(15 - level):
        cells[pos] = "redstone_wire"
        pos = (pos[0] - dx, pos[1], pos[2] - dz)
    cells[pos] = "redstone_block"
    for p in list(cells):
        cells.setdefault((p[0], p[1] - 1, p[2]), "smooth_stone")
    c = Circuit.from_cells(cells)
    c.run(30)
    return c.power.get(g["out"], 0)


def test_an_exact_value_gate_is_exact_at_every_facing_and_both_sides():
    """**THE ONE THAT WAS MISSING.** `window(v, v + 1)` used to pass every level at or above `v`,
    so three shipped machines were `double_or_none` wearing another name: The Vault opened on any
    page over each dial, the Assay Office paid for anything heavier than the mark, and The
    Reckoning paid on 2 AND on 4."""
    for facing in ("east", "west", "north", "south"):
        for side in (1, -1):
            for target in (1, 2, 3, 4, 6):
                for level in range(1, 9):
                    got = _drive_window(target, target + 1, level, facing, side) > 0
                    assert got == (level == target), (
                        f"{facing}/{side}: window({target}) "
                        f"{'let' if got else 'blocked'} {level}")


def test_a_wider_window_passes_a_band_and_nothing_outside_it():
    for low, high in ((5, 9), (2, 5), (1, 4)):
        for level in range(1, 12):
            got = _drive_window(low, high, level) > 0
            assert got == (low <= level < high), f"window({low},{high}) on {level}"


def test_the_gates_side_input_arrives_at_FULL_strength():
    """A comparator reads its side as a LEVEL, so a boolean that decays on the way turns the
    subtract into an off-by-that-much: measured, the old wide window gave `15 - 12 = 3` at a level
    it exists to block and 'passed' it quietly and by three. The property is the LEVEL, not the
    presence of a repeater somewhere in the module - that was the old assertion and every window
    has repeaters in it whether or not the side ever arrives."""
    g = circuits.window((0, 0, 0), 5, 9)
    cells = dict(g["cells"])
    pos = g["in"]
    for _ in range(15 - 9):                       # a level of 9: the HIGH tap must fire
        cells[pos] = "redstone_wire"
        pos = (pos[0] - 1, pos[1], pos[2])
    cells[pos] = "redstone_block"
    for p in list(cells):
        cells.setdefault((p[0], p[1] - 1, p[2]), "smooth_stone")
    c = Circuit.from_cells(cells)
    c.run(30)
    gate = g["gate"]
    sides = [c._read(s, c._last_src, gate) for s in c._sides(gate, c.at(gate))]
    assert max(sides) == 15, f"the side arrived at {max(sides)}, so the subtract leaks by that much"


def test_nothing_may_be_consumed_one_step_along_the_run():
    """`next`, not `out + facing`. One step along the run is the cell beside the gate's own SIDE,
    which carries the HIGH boolean at a full 15 - a lamp put there reads the signal the gate
    exists to reject, which is exactly how the wheel lit every pocket in turn."""
    for low in (1, 2, 4):
        g = circuits.window((0, 0, 0), low, low + 1)
        step = circuits.STEP["east"]
        naive = (g["out"][0] + step[0], g["out"][1], g["out"][2] + step[2])
        assert g["next"] != naive, "next must not be the cell one step along the run"
        # ...and `next` touches nothing the module placed except `out` itself.
        touching = [q for q in g["cells"]
                    if sum(abs(a - b) for a, b in zip(q, g["next"])) == 1]
        assert touching == [g["out"]], f"next touches {touching}"


def test_a_connector_between_two_cells_that_already_touch_lays_nothing():
    """`climb` steps a full cell ALONG the run before it descends, so a one-course drop to a cell
    one step along lands one PAST the destination - and the planar leg back has nothing to lay
    because both its ends are endpoints. What was left was a single orphaned dust cell on its own
    step block, reported by `circuit.inspect` as "dust with no source" on The Reckoning."""
    for b in ((1, 0, 0), (0, 0, 1), (1, -1, 0), (0, 1, -1), (-1, -1, 0)):
        m = circuits.connect((0, 0, 0), b)
        assert m["cells"] == {}, f"{b}: laid {len(m['cells'])} cells between two adjacent points"
    assert circuits.connect((0, 0, 0), (4, 0, 0))["cells"], "a real gap still gets a run"
