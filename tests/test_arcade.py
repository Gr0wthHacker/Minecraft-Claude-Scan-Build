"""Every arcade machine against its own stated CONTRACT, by SIMULATION.

A kind whose contract is not asserted here does not belong in `gen/arcade.py`. That rule is not
decoration: a redstone build is the one thing in this project whose wrongness is invisible in every
render, every audit and every bill of materials - it looks finished and does nothing - and two
finished casino games were deleted for failing exactly this check.

**AN ENTITY IS AN INPUT YOU STATE.** `mcbuild.circuit` has no entities, so it cannot drop a ball
into a hopper, fire an arrow into a target, stand on a plate, turn a page or make a noise. Every
one of those is driven here with `Circuit.fill`, which is precisely how the item sorter and the
dropper randomiser are already tested. What that leaves unproven travels in each build's
`unverified` list rather than being quietly assumed.

**AND A BOUND LOOSER THAN THE BUG IS NOT A TEST.** `circuits.pulse` shipped as a bare repeater for
months because its test asserted `high < 20` out of twenty ticks, which a permanent delay satisfies
as comfortably as a pulse. Everything below asserts the CONTRACT: which lamps, which lane, how many
prizes, and - just as hard - that the other lanes did nothing at all.
"""
from __future__ import annotations

import collections

import pytest

from mcbuild import audit, blocks, nbt, palette
from mcbuild.circuit import Circuit, Cell, inspect
from mcbuild.gen import arcade

FACINGS = ("east", "west", "north", "south")
LANDS = ("midway", "frontier", "hollow")


def build(kind: str, **cfg):
    return arcade.build({"at": [0, 64, 0], "kind": kind, "facing": "east",
                         "land": "midway", **cfg})


def sim(kind: str, **cfg):
    """A built machine and a circuit over it, in WORLD coordinates - the same frame the sidecars
    carry everywhere else, so a meta coordinate can be handed straight to the simulator."""
    c = build(kind, **cfg)
    m = c.to_model() if hasattr(c, "to_model") else c
    return c, Circuit.of(m, c.world_origin)


def fired(s: Circuit, droppers) -> int:
    return sum(s.fired[tuple(d)] for d in droppers)


def model_of(c):
    return c.to_model() if hasattr(c, "to_model") else c


def names_of(c) -> collections.Counter:
    m = model_of(c)
    out = collections.Counter()
    for i in set(m.ids[m.ids > 0].ravel().tolist()):
        out[nbt.state_name(m.palette[i]).split(":")[-1]] += int((m.ids == i).sum())
    return out


# --------------------------------------------------------------------------- the primitives
#
# TESTED BEFORE ANYTHING IS BUILT ON THEM, which is the ordering `circuits.climb` was written
# without: it was used in the same breath it was written, failed silently three times inside the
# casino, and gave up its bug the moment it was finally exercised alone.


def _drive(c: Circuit, cells):
    for pos in cells:
        c.cells[pos] = Cell("lever", {"face": "floor", "facing": "north"})


@pytest.mark.parametrize("facing", FACINGS)
def test_the_and_gate_is_an_and_gate_and_not_an_or(facing):
    """Four inputs, four answers. An AND that is really an OR pays on either half of a skill game,
    which is the whole difference between reading the player and ignoring them."""
    side = arcade._SIDE[facing]
    mod = arcade.and_gate((0, 0, 0), facing, side)
    for a in (False, True):
        for b in (False, True):
            c = Circuit.from_cells(mod["cells"])
            _drive(c, (mod["a"], mod["b"]))
            c.set(mod["a"], a)
            c.set(mod["b"], b)
            c.run(20)
            assert c.powered(mod["out"]) is (a and b), f"{facing}: A={a} B={b}"


def test_a_three_input_and_needs_all_three():
    mod = arcade.and_gate((0, 0, 0), "east", "north", inputs=3)
    for k in range(4):
        c = Circuit.from_cells(mod["cells"])
        _drive(c, mod["feeds"])
        for j, feed in enumerate(mod["feeds"]):
            c.set(feed, j < k)          # k of the three high
        c.run(24)
        assert c.powered(mod["out"]) is (k == 3), f"{k} of 3 high"


def test_the_and_gates_odd_rows_are_left_empty():
    """THE CELL BETWEEN TWO INPUT SUPPORTS POWERS BOTH INVERTERS AT ONCE. Anything routed through
    it turns the gate silently into an OR, so the gate names those cells and nothing writes them."""
    mod = arcade.and_gate((0, 0, 0), "east", "north", inputs=3)
    for pos in mod["keep_clear"]:
        assert pos not in mod["cells"], f"{pos} must stay empty"


def test_a_ladder_reads_a_level_as_a_height():
    """The instrument three of the games are built on: level L lights the bottom L lamps."""
    mod = arcade.ladder((0, 0, 0), 8, "east", "north")
    for level in (1, 3, 5, 8, 15):
        c = Circuit.from_cells(mod["cells"])
        c.cells[(-1, 0, 0)] = Cell("comparator", {"facing": "east", "mode": "compare"})
        c.cells[(-2, 0, 0)] = Cell("barrel")
        c.fill((-2, 0, 0), level)
        c.run(16)
        lit = [i for i, l in enumerate(mod["lamps"]) if c.powered(l)]
        assert lit == list(range(min(level, mod["rungs"]))), f"level {level} lit {lit}"


def test_a_ladder_has_no_repeater_in_it():
    """THE DECAY IS THE MEASUREMENT. One repeater anywhere in the climb restores the signal to 15
    and lights the whole tower on any hit at all - which is a lamp, not an instrument."""
    mod = arcade.ladder((0, 0, 0), 12, "east", "north")
    assert not [v for v in mod["cells"].values() if v.startswith("repeater")]


def test_a_ladder_is_dark_with_no_signal():
    mod = arcade.ladder((0, 0, 0), 6, "east", "north")
    c = Circuit.from_cells(mod["cells"])
    c.run(10)
    assert not any(c.powered(l) for l in mod["lamps"])


@pytest.mark.parametrize("facing", FACINGS)
def test_a_local_clock_never_settles_at_any_facing(facing):
    """`circuits.clock` is not rotated by its own `facing` - it always builds along +x and +z, as
    its docstring says. Used inside a `_Frame` that made the reaction game run facing east and not
    at all facing west, north or south, which no test of the default facing would ever have seen."""
    mod = arcade.clock((0, 0, 0), facing, arcade._SIDE[facing], period=1)
    c = Circuit.from_cells(mod["cells"])
    seen = set()
    for _ in range(24):
        c.step()
        seen.add(c.powered(mod["out"]))
    assert seen == {True, False}, f"{facing}: a clock must take both states, for ever"


def test_a_slower_clock_is_slower():
    def edges(period):
        mod = arcade.clock((0, 0, 0), "east", "north", period=period)
        c = Circuit.from_cells(mod["cells"])
        last, n = None, 0
        for _ in range(60):
            c.step()
            now = c.powered(mod["out"])
            if last is not None and now != last:
                n += 1
            last = now
        return n
    assert edges(1) > edges(4)


def test_read_out_puts_the_container_at_the_comparators_back():
    """A COMPARATOR READS WHAT IS BEHIND IT AND OUTPUTS WHERE IT FACES. Written the other way round
    the machine can never fire, every check in this pipeline still passes, and our renderer draws
    both directions identically - which is how the item sorter shipped backwards in every lane."""
    for facing in FACINGS:
        mod = arcade.read_out((0, 64, 0), facing)
        c = Circuit.from_cells(mod["cells"])
        assert c._back((0, 64, 0), c.at((0, 64, 0))) == mod["reads"]
        assert c._front((0, 64, 0), c.at((0, 64, 0))) == mod["out"]
        c.cells[mod["reads"]] = Cell("barrel")
        c.fill(mod["reads"], 7)
        c.run(4)
        assert c.state.get((0, 64, 0)) == 7


def test_the_side_axis_matches_the_frames_own_i_axis():
    """`_SIDE` is a hand-written table of what `_Frame`'s i axis is called. Derived wrongly, every
    circuit module pointed along the frontage would be built across the building instead."""
    from mcbuild.gen.park import _Frame, _STEP
    for facing in FACINGS:
        f = _Frame({"at": [0, 64, 0], "facing": facing})
        step = _STEP[arcade._SIDE[facing]]
        assert f.at(1, 0, 0) == (step[0], 64, step[1])


def test_the_inverse_of_the_frame_is_the_inverse_of_the_frame():
    """`_ij` is what lets a caller ask where a circuit module's WORLD output landed in building
    axes. Every hand-derived version of it in the first draft was wrong by a cell or two, and a
    route that is off by one cell is a route that connects nothing."""
    from mcbuild.gen.park import _Frame
    for facing in FACINGS:
        f = _Frame({"at": [10, 64, -7], "facing": facing})
        for i in (-3, 0, 5):
            for d in (-1, 0, 4):
                for h in (-2, 0, 3):
                    assert arcade._ij(f, f.at(i, d, h)) == (i, d, h)


# --------------------------------------------------------------------------- every kind, in general


def test_every_kind_states_a_contract_and_says_what_it_cannot_prove():
    for kind in arcade.BUILDERS:
        c = build(kind)
        assert c.meta.get("contract"), f"{kind} has no contract"
        assert "unverified" in c.meta, f"{kind} does not say what it cannot prove"


@pytest.mark.parametrize("kind", sorted(arcade.BUILDERS))
def test_every_kind_is_one_connected_piece_with_no_placement_problems(kind):
    """**A COMPONENT COUNT IS THE ONLY CHECK THAT SEES A FLOATING SHELL.** Begun one course above
    its own pad, four kinds shipped in exactly two pieces - the ground and the building - with zero
    placement problems reported, because every cell had something under it at its OWN course."""
    for facing in FACINGS:
        c = build(kind, facing=facing)
        r = audit.audit(model_of(c))
        assert not r.problems, f"{kind}/{facing}: {r.problems[:3]}"
        assert len(r.components) == 1, f"{kind}/{facing}: {r.components}"


@pytest.mark.parametrize("kind", sorted(arcade.BUILDERS))
def test_every_kind_is_legal_affordable_and_1_19(kind):
    """Rules 12, 13 and 16 at once: a real block, a 1.19 block, and not CURRENCY. Dirt and grass
    are money on this server, which is how a lion once shipped with a coat of 5,173 dirt."""
    c = build(kind)
    counts = names_of(c)
    for n in counts:
        assert blocks.exists(n), f"{kind}: {n} is not a block"
        assert blocks.spendable(n), f"{kind}: {n} is CURRENCY on this server"
    assert not audit.report_server_blocks(model_of(c)), f"{kind} uses a non-1.19 block"
    assert not audit.check_states(model_of(c)), f"{kind} emits an illegal block state"


@pytest.mark.parametrize("kind", sorted(arcade.BUILDERS))
def test_the_only_expensive_block_is_the_lamp_and_it_is_counted(kind):
    """A LIGHT CANNOT BE SUBSTITUTED BY COLOUR - a dark block that looks like a lamp is a display
    that does not work - so `redstone_lamp` is priced into `budget` rather than swapped out. Every
    other expensive block would be a smuggled one."""
    c = build(kind)
    counts = names_of(c)
    dear = {n: v for n, v in counts.items() if palette.tier(n) == "expensive"}
    assert set(dear) <= {"redstone_lamp"}, f"{kind} spends on {sorted(set(dear) - {'redstone_lamp'})}"
    assert c.meta["budget"].get("redstone_lamp", 0) == dear.get("redstone_lamp", 0)
    assert dear.get("redstone_lamp", 0) <= 20, f"{kind} wants {dear} lamps - keep the count small"


@pytest.mark.parametrize("kind", sorted(arcade.BUILDERS))
def test_every_kind_signs_itself(kind):
    """A GAME NOBODY CAN WORK OUT HOW TO PLAY IS AN EMPTY STRUCTURE. `_sign` REFUSES a cell with no
    block behind it and returns False, so five kinds once shipped with their name and their rules
    silently missing on a build that audited perfectly clean."""
    for facing in FACINGS:
        for land in LANDS:
            c = build(kind, facing=facing, land=land)
            assert c.meta["signed"] is True, f"{kind}/{facing}/{land} lost a sign"


@pytest.mark.parametrize("kind", sorted(arcade.BUILDERS))
def test_no_sign_line_is_wider_than_a_sign(kind):
    """FIFTEEN CHARACTERS IS THE LINE. A line that reads well in a python file is a line cut off
    mid-word in game, and the failure only shows up in a screenshot after the build is placed."""
    import json
    c = build(kind)
    # **A TEST THAT READS THE WRONG FIELD PASSES VACUOUSLY**, which the first version of this one
    # did: it asked for `front_text`, a Canvas sign tile carries `front`, and it silently checked
    # nothing at all on every kind. The count is asserted so it cannot go quiet again.
    seen = 0
    for t in (c.tiles or {}).values():
        for side in ("front", "back"):
            for raw in t.get(side) or []:
                text = json.loads(raw).get("text", "")
                seen += 1
                assert len(text) <= arcade.SIGN_WIDTH, f"{kind}: {text!r} is {len(text)} chars"
    assert seen >= 8, f"{kind}: only {seen} sign lines were checked"


@pytest.mark.parametrize("kind", sorted(arcade.BUILDERS))
def test_every_kind_says_how_to_play_it_and_not_just_its_name(kind):
    """A name over a door is a label. What makes a machine playable is the three lines under it -
    what to do, and what it pays."""
    import json
    c = build(kind)
    boards = []
    for t in (c.tiles or {}).values():
        lines = [json.loads(r).get("text", "") for r in (t.get("front") or [])]
        if sum(1 for l in lines if l.strip()) >= 3:
            boards.append(lines)
    assert boards, f"{kind} has a name but no instructions"


@pytest.mark.parametrize("kind", sorted(arcade.BUILDERS))
def test_every_lamp_a_kind_reports_is_actually_a_lamp(kind):
    """**`Circuit.powered` ANSWERS FOR A COORDINATE AND DOES NOT CARE WHAT BLOCK IS THERE.** The
    high striker's own award chain quietly replaced its top lamp with a comparator, and every
    simulated assertion in this file still passed. A lamp that has been overwritten is lit in the
    simulator and dark in the game."""
    c, s = sim(kind)
    lamps = c.meta.get("lamps") or []
    groups = lamps if (lamps and isinstance(lamps[0][0], list)) else [lamps]
    for g in groups:
        for pos in g:
            assert s.name(tuple(pos)) == "redstone_lamp", f"{kind}: {pos} is {s.name(tuple(pos))}"
    for key, want in (("bell", "bell"), ("door", "iron_door"), ("plate",
                                                                "light_weighted_pressure_plate")):
        if c.meta.get(key):
            assert s.name(tuple(c.meta[key])) == want
    for group in (c.meta.get("droppers") or []):
        for pos in (group if isinstance(group[0], list) else [group]):
            assert s.name(tuple(pos)) == "dropper"


@pytest.mark.parametrize("kind", sorted(arcade.BUILDERS))
def test_the_circuit_inspection_finds_nothing_but_the_windows_own_side_tap(kind):
    """Calibration, in the sense `tests/test_circuit_calibration.py` established: the only question
    that decides whether a checker gets used is whether it stays QUIET on a machine that works.

    The one finding allowed is `circuits.window`'s own side-input repeater, whose back is
    deliberately empty when `high == low + 1`. `casino/lucky_number` reports exactly the same, and
    it is a property of that shared module rather than of anything here.
    """
    c = build(kind)
    findings = inspect(model_of(c), c.world_origin)
    unexpected = [f for f in findings if f[0] != "repeater reads nothing"]
    assert not unexpected, f"{kind}: {unexpected}"


# --------------------------------------------------------------------------- plinko


def test_plinko_pays_the_channel_the_ball_landed_in_and_no_other():
    for facing in FACINGS:
        c, _ = sim("plinko", facing=facing)
        M = c.meta
        for k, hopper in enumerate(M["hoppers"]):
            _, s = sim("plinko", facing=facing)
            s.fill(tuple(hopper), 3)
            s.run(30)
            got = [fired(s, M["droppers"][j]) for j in range(len(M["hoppers"]))]
            want = [M["prizes"][k] if j == k else 0 for j in range(len(M["hoppers"]))]
            assert got == want, f"{facing} channel {k}: {got} != {want}"


def test_a_stuck_ball_pays_once_and_only_once():
    """**THE HOUSE MUST NOT BE ABLE TO LOSE BY ACCIDENT.** The casino pins a hazard where a stuck
    item reads a winning level against an edge that never falls and pays for ever; every lane here
    turns the reading into a fixed 2-tick pulse the moment it is read, so a ball that never leaves
    the hopper is one prize and not a drained bank."""
    c, _ = sim("plinko")
    M = c.meta
    _, s = sim("plinko")
    s.fill(tuple(M["hoppers"][0]), 3)
    s.run(400)
    assert fired(s, M["droppers"][0]) == M["prizes"][0]


def test_a_second_ball_pays_again():
    """One prize per ball is the contract; one prize per CHUNK LOAD would be a broken machine."""
    c, _ = sim("plinko")
    M = c.meta
    _, s = sim("plinko")
    s.fill(tuple(M["hoppers"][0]), 3)
    s.run(20)
    s.fill(tuple(M["hoppers"][0]), 0)
    s.run(12)
    s.fill(tuple(M["hoppers"][0]), 5)
    s.run(20)
    assert fired(s, M["droppers"][0]) == 2 * M["prizes"][0]


def test_plinko_pays_nothing_at_all_until_a_ball_arrives():
    _, s = sim("plinko")
    c, _ = sim("plinko")
    s.run(120)
    assert sum(fired(s, g) for g in c.meta["droppers"]) == 0


def test_the_plinko_channels_are_worth_different_amounts():
    """A board where every channel pays the same is a board with nothing to aim at. The curve is
    symmetric about the middle and the OUTSIDE pays most, because the outside is the hard place to
    land - which is what the peg lattice is for."""
    c = build("plinko")
    prizes = c.meta["prizes"]
    assert prizes == prizes[::-1]
    assert prizes[0] > prizes[len(prizes) // 2]


# --------------------------------------------------------------------------- the range


def test_each_target_scores_on_its_own_column_and_nobody_elses():
    for facing in FACINGS:
        c, _ = sim("range", facing=facing)
        M = c.meta
        for lane in range(3):
            for level in (1, 3, 5):
                _, s = sim("range", facing=facing)
                s.fill(tuple(M["targets"][lane]), level)
                s.run(20)
                lit = [[i for i, l in enumerate(M["lamps"][j]) if s.powered(tuple(l))]
                       for j in range(3)]
                want = [list(range(level)) if j == lane else [] for j in range(3)]
                assert lit == want, f"{facing} lane {lane} level {level}: {lit}"


def test_only_a_full_score_on_the_far_target_rings_the_bell_and_pays():
    c, _ = sim("range")
    M = c.meta
    for lane in range(3):
        for level in (1, M["score"] - 1, M["score"], 15):
            _, s = sim("range", )
            s.fill(tuple(M["targets"][lane]), level)
            s.run(24)
            win = lane == 2 and level >= M["score"]
            assert s.powered(tuple(M["bell"])) is win, f"lane {lane} level {level}"
            assert fired(s, M["droppers"]) == (1 if win else 0)


def test_the_range_is_silent_and_dark_with_nothing_shot_at_it():
    c, s = sim("range")
    s.run(40)
    assert not any(s.powered(tuple(l)) for g in c.meta["lamps"] for l in g)
    assert fired(s, c.meta["droppers"]) == 0


# --------------------------------------------------------------------------- the high striker


def test_the_striker_climbs_with_the_hit_and_rings_only_at_the_top():
    for facing in FACINGS:
        c, _ = sim("strength", facing=facing)
        M = c.meta
        for level in (1, 4, M["rungs"] - 1, M["rungs"], 15):
            _, s = sim("strength", facing=facing)
            s.fill(tuple(M["target"]), level)
            s.run(24)
            lit = [i for i, l in enumerate(M["lamps"]) if s.powered(tuple(l))]
            assert lit == list(range(min(level, M["rungs"]))), f"{facing} level {level}: {lit}"
            assert s.powered(tuple(M["bell"])) is (level >= M["rungs"])
            assert fired(s, M["droppers"]) == (1 if level >= M["rungs"] else 0)


def test_the_strikers_reading_enters_the_ladder_at_full_strength():
    """**A CELL OF DUST COSTS A LEVEL.** Nudged one cell along to keep the first lamp off its own
    comparator, an eight-rung tower needed a hit of NINE to ring - an instrument lying about what
    it measured. The comparator sits beside the disc instead, and the ladder starts on its output."""
    c, _ = sim("strength")
    M = c.meta
    _, s = sim("strength")
    s.fill(tuple(M["target"]), 1)
    s.run(16)
    assert s.powered(tuple(M["lamps"][0])), "a hit of 1 must light exactly the first lamp"


# --------------------------------------------------------------------------- the scale


def test_the_scale_pays_on_the_exact_weight_and_nothing_else():
    """A `threshold` would pay for anything heavier, which is not a guessing game, it is a shelf."""
    for facing in FACINGS:
        c, _ = sim("weigh", facing=facing)
        M = c.meta
        target = M["target"]
        for level in (1, target - 1, target, target + 1, M["rungs"]):
            _, s = sim("weigh", facing=facing)
            s.fill(tuple(M["plate"]), level)
            s.run(24)
            assert fired(s, M["droppers"]) == (1 if level == target else 0), \
                f"{facing}: {level} against a target of {target}"
            assert s.powered(tuple(M["bell"])) is (level == target)


def test_the_scale_shows_the_weight_while_you_are_building_it_up():
    """Two comparators read the ONE plate, because a spur off one of them is already a level down
    and the readout and the judge would disagree about what the scale says."""
    c, _ = sim("weigh")
    M = c.meta
    for level in range(1, M["rungs"] + 1):
        _, s = sim("weigh")
        s.fill(tuple(M["plate"]), level)
        s.run(20)
        lit = [i for i, l in enumerate(M["lamps"]) if s.powered(tuple(l))]
        assert lit == list(range(level)), f"level {level} showed {lit}"


# --------------------------------------------------------------------------- reaction


def test_the_light_actually_runs_along_the_row():
    """A square wave lights half the row at once, which is a band and not a runner - which is what
    a chain fed straight from the clock does. What travels is a PULSE."""
    for facing in FACINGS:
        c, s = sim("reaction", facing=facing)
        M = c.meta
        seen = set()
        for _ in range(60):
            s.step()
            seen |= {i for i, l in enumerate(M["lamps"]) if s.powered(tuple(l))}
        assert seen == set(range(M["stages"])), f"{facing}: only {sorted(seen)} ever lit"


def test_a_repeater_of_delay_n_needs_n_plus_one_ticks_of_input():
    """The reason the chain is delay 2 against a 3-tick launch. At delay 3 the first repeater's
    countdown was reset by the input falling before it expired: the row was dark for ever while
    every block in it was legal, supported and correctly wired."""
    c = build("reaction")
    m = model_of(c)
    delays = set()
    for i in set(m.ids[m.ids > 0].ravel().tolist()):
        e = m.palette[i]
        if nbt.state_name(e).split(":")[-1] == "repeater":
            props = nbt.state_props(e)
            delays.add(props.get("delay"))
    assert "2" in delays, "the runner's own stages must be delay 2"


def test_pressing_while_the_mark_is_lit_pays_and_pressing_at_random_does_not():
    """The whole game. The winning window is four ticks wide and lands on the mark's own four lit
    ticks to within one - a tenth of a second of lead, which is inside human reaction noise and far
    inside the 0.4 s the light is actually on the square."""
    for facing in FACINGS:
        c, _ = sim("reaction", facing=facing)
        M = c.meta
        mark = tuple(M["lamps"][M["mark"]])
        button = tuple(M["button"])
        wins, lits = [], []
        for t0 in range(6, 46):
            _, s = sim("reaction", facing=facing)
            for _ in range(t0):
                s.step()
            before, lit = fired(s, M["droppers"]), s.powered(mark)
            s.press(button, 6)
            for _ in range(30):
                s.step()
            if fired(s, M["droppers"]) > before:
                wins.append(t0)
            if lit:
                lits.append(t0)
        assert lits, f"{facing}: the mark never lit at all"
        assert wins, f"{facing}: no press ever won"
        on_the_mark = set(wins) & set(lits)
        assert len(on_the_mark) >= 6, f"{facing}: only {sorted(on_the_mark)} won on the mark"
        # ...and a press nowhere near it does nothing. Half a cycle from a winning press.
        cycle = 14
        cold = [t for t in range(6, 46) if t not in wins]
        assert len(cold) > len(wins), f"{facing}: almost every tick wins - that is not a skill game"
        assert any(abs(t - w) >= cycle // 3 for t in cold for w in wins[:1])


def test_the_reaction_game_pays_nothing_when_it_is_first_built():
    """**A TORCH GATE IS HIGH FOR TWO TICKS THE MOMENT IT IS BUILT**, because every torch starts
    lit and the inverters take a tick each to settle - so it paid one prize out of the bank on
    every chunk load. A delay-2 repeater needs three consecutive ticks and swallows the glitch."""
    for facing in FACINGS:
        c, s = sim("reaction", facing=facing)
        s.run(120)
        assert fired(s, c.meta["droppers"]) == 0, f"{facing} pays for being switched on"


def test_the_reaction_game_has_no_randomiser_in_it():
    """After five games decided by a dropper's item mix, the point of this one is that there is
    nothing random in it at all."""
    counts = names_of(build("reaction"))
    assert "dropper" in counts        # ...the payout, which is not the same thing
    assert "hopper" not in counts, "a hopper here would mean a randomiser"


# --------------------------------------------------------------------------- the safe


def test_the_safe_opens_only_on_the_whole_combination():
    for facing in FACINGS:
        c, _ = sim("safe", facing=facing)
        M = c.meta
        combo = M["combo"]
        wrong = [
            [combo[0], combo[1], combo[2] + 1],
            [combo[0] + 1, combo[1], combo[2]],
            [combo[0], combo[1] + 1, combo[2]],
            [combo[0], combo[2], combo[1]],
            [combo[0], combo[1], 0],
            [0, 0, 0],
            [12, 12, 12],
        ]
        _, s = sim("safe", facing=facing)
        for dial, v in zip(M["dials"], combo):
            s.fill(tuple(dial), v)
        s.run(50)
        assert s.powered(tuple(M["door"])), f"{facing}: the right combination did not open it"
        for trial in wrong:
            _, s = sim("safe", facing=facing)
            for dial, v in zip(M["dials"], trial):
                s.fill(tuple(dial), v)
            s.run(50)
            assert not s.powered(tuple(M["door"])), f"{facing}: {trial} opened the safe"


@pytest.mark.parametrize("combo", ([2, 7, 11], [1, 4, 12], [4, 6, 9]))
def test_the_safe_works_at_any_combination(combo):
    """The combination is one line of config, so it has to be one line of config that WORKS - the
    routing depends on the dials being sorted and on the gate sitting past every window band."""
    c, _ = sim("safe", combo=combo)
    M = c.meta
    _, s = sim("safe", combo=combo)
    for dial, v in zip(M["dials"], M["combo"]):
        s.fill(tuple(dial), v)
    s.run(50)
    assert s.powered(tuple(M["door"]))
    _, s = sim("safe", combo=combo)
    for dial, v in zip(M["dials"], [M["combo"][0], M["combo"][1], M["combo"][2] + 1]):
        s.fill(tuple(dial), v)
    s.run(50)
    assert not s.powered(tuple(M["door"]))


def test_the_safe_door_does_not_flick_open_when_the_chunk_loads():
    for facing in FACINGS:
        c, s = sim("safe", facing=facing)
        for _ in range(20):
            s.step()
            assert not s.powered(tuple(c.meta["door"])), f"{facing}: the door opened by itself"


def test_the_safe_refuses_a_combination_it_cannot_build():
    for bad in ([3, 3, 5], [0, 5, 8], [3, 5], [3, 5, 13]):
        with pytest.raises(ValueError):
            build("safe", combo=bad)


def test_the_safe_dials_are_lecterns_because_an_item_frame_is_an_entity():
    """`blocks.exists("item_frame")` is False and it is false correctly - a frame lives in a
    region's Entities list, not in its block palette, so no litematic this pipeline writes can
    place one. A lectern is a block and its comparator reads the page just as well."""
    assert not blocks.exists("item_frame")
    c, s = sim("safe")
    for dial in c.meta["dials"]:
        assert s.name(tuple(dial)) == "lectern"


# --------------------------------------------------------------------------- the quiet room


def test_the_quiet_rooms_door_is_held_open_until_something_makes_a_noise():
    """**THE OPPOSITE OF EVERY OTHER DOOR IN THIS REPO**, and it needs the inverter to be that way
    round: a door wired the ordinary way would be shut until the alarm opened it, which is a
    machine that rewards being loud."""
    for facing in FACINGS:
        c, _ = sim("quiet", facing=facing)
        M = c.meta
        _, s = sim("quiet", facing=facing)
        s.run(20)
        assert s.powered(tuple(M["door"])), f"{facing}: the door is shut at rest"
        assert not any(s.powered(tuple(a)) for a in M["lamps"])
        for k in range(len(M["sensors"])):
            _, s = sim("quiet", facing=facing)
            s.fill(tuple(M["sensors"][k]), M["trip"])
            s.run(20)
            assert not s.powered(tuple(M["door"])), f"{facing}: sensor {k} did not shut the door"
            assert all(s.powered(tuple(a)) for a in M["lamps"]), "the alarm must light everywhere"


def test_a_vibration_under_the_threshold_is_ignored():
    c, _ = sim("quiet")
    M = c.meta
    _, s = sim("quiet")
    s.fill(tuple(M["sensors"][0]), M["trip"] - 1)
    s.run(20)
    assert s.powered(tuple(M["door"]))


def test_the_quiet_rooms_floor_offers_a_wool_route():
    """WOOL ABSORBS A VIBRATION - that is the trick, and the whole game is knowing it. The sign
    hints at it rather than stating it, so the floor has to actually give you a way through."""
    counts = names_of(build("quiet"))
    assert counts.get("white_wool", 0) > 20, "there is no quiet route to find"


# --------------------------------------------------------------------------- the prize counter


def test_each_barrels_lamp_answers_for_its_own_barrel():
    for facing in FACINGS:
        c, _ = sim("prizecounter", facing=facing)
        M = c.meta
        for k in range(len(M["barrels"])):
            _, s = sim("prizecounter", facing=facing)
            s.fill(tuple(M["barrels"][k]), 5)
            s.run(8)
            lit = [s.powered(tuple(l)) for l in M["lamps"]]
            assert lit == [j == k for j in range(len(M["lamps"]))], f"{facing} barrel {k}: {lit}"


def test_an_empty_counter_is_a_dark_counter():
    c, s = sim("prizecounter")
    s.run(10)
    assert not any(s.powered(tuple(l)) for l in c.meta["lamps"])


def test_the_prize_counter_cannot_hand_anything_out_by_itself():
    """The one kind here the house cannot lose money on: there is no dispenser in it, because
    handing over a prize is a person's job and the prices are a person's decision."""
    counts = names_of(build("prizecounter"))
    assert "dispenser" not in counts and "dropper" not in counts


def test_the_prize_counter_is_somewhere_to_sit():
    """An arcade is somewhere people LINGER, not a room of machines. A game with nothing to spend
    its prizes on is a game worth playing once."""
    counts = names_of(build("prizecounter"))
    assert counts.get("stone_brick_stairs", 0) >= 4, "no bench"
    assert counts.get("lantern", 0) >= 2, "no light over it"
    assert counts.get("barrel", 0) >= 2


# --------------------------------------------------------------------------- what is NOT here


def test_nothing_reaches_for_a_block_this_server_will_not_have():
    """Rule 12 from the direction that bit this project before: `blocks.available()` is a no-op
    while the allowlist is provisional, so a 1.20 or 1.21 block passes every check in the pipeline
    and cannot be placed. These four were all considered for this file and all rejected."""
    everything = collections.Counter()
    for kind in arcade.BUILDERS:
        everything |= names_of(build(kind))
    for later in ("chiseled_bookshelf", "crafter", "copper_bulb", "calibrated_sculk_sensor",
                  "pale_oak_planks"):
        assert later not in everything, f"{later} is not a 1.19 block"


def test_the_module_is_registered():
    from mcbuild.gen import GENERATORS
    assert GENERATORS["arcade"] is arcade
    assert arcade.DEFAULTS is arcade.ARCADE
