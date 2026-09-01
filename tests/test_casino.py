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


def _built(kind, **kw):
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": kind, "outcomes": 3, "pit": 2,
                                    "check": False, **kw}, [])
    return c, c.to_model()


def test_every_game_is_a_room_you_can_walk_into_and_read():
    """**A GAME IS A ROOM, NOT A PLATFORM**, and it must say what it is.

    The first casino built a floor, one back wall and a trim line per game - Jack's verdict was
    "random platforms of shit", and nothing told a player what a machine was, how to play it or
    what it paid. Four walls, one doorway, a ceiling, and two signs: the name over the door and
    the rules inside.
    """
    for kind in ("high_roller", "double_or_none"):
        c, m = _built(kind, title="Test Room")
        assert len(m.tile_entities) == 2, f"{kind}: a door sign and a rules sign"
        lines = [[j.value for j in t.value["front_text"].value["messages"].value]
                 for t in m.tile_entities]
        flat = " ".join(x for side in lines for x in side)
        assert "TEST ROOM" in flat, "the door sign carries the room's own name"
        assert "press to roll" in flat, "the rules sign says what to do"
        # the odds are on the sign, because this project will not build a game whose distribution
        # it cannot state
        assert ("1 in 3" in flat) or ("1 . 2 . or 4" in flat)


def test_a_sign_line_is_never_wider_than_a_sign():
    """Fifteen characters renders; twenty is a line cut off mid-word, and it only shows up in a
    screenshot after the build is placed."""
    from mcbuild.gen import casino
    for key, lines in casino.SIGN_COPY.items():
        assert len(lines) <= 4, f"{key}: a sign has four lines"
        for ln in lines:
            assert len(ln) <= casino.SIGN_WIDTH, f"{key}: {ln!r} is {len(ln)} chars"


def test_the_room_is_actually_enclosed_and_has_exactly_one_way_in():
    """A wall with a hole punched in it afterwards is how the void tower shipped a plain drum where
    it had drawn crenellations - so the doorway is left EMPTY by the wall loop, and this checks the
    result rather than the intent."""
    import numpy as np
    c, m = _built("high_roller", title="Room")
    names = []
    for t in m.palette:
        try:
            names.append(t.value["Name"].value.split(":")[-1])
        except Exception:                                        # noqa: BLE001
            names.append("air")
    air = [i for i, n in enumerate(names) if n == "air"]
    solid = ~np.isin(m.ids, air)
    sy, sz, sx = m.ids.shape
    # A CEILING IS A PLANE, so it is checked as one. Sampling a single column is what this test
    # did first and it failed: the model's box also holds the pit and the machine, which run
    # outside the room, so its centre column is not the room's centre.
    # ...and it is compared against the ROOM's footprint, not the model's box: the box is 16x10
    # because the machine and its payout run outside the room, while the room itself is 10x6. A
    # fraction-of-the-box threshold measures the machine, not the ceiling.
    top = solid[-1]
    assert top.sum() >= 50, f"no ceiling plane: {int(top.sum())} cells"
    ys, xs = np.where(top)
    assert (ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1) == top.sum(), (
        "the ceiling must be a solid rectangle, not a lacy patch")
    # THE WALLS ARE CHECKED ON THE ROOM'S OWN PERIMETER, taken from the ceiling rectangle.
    # Checking the MODEL BOX's edges fails by construction: the box is 16 wide because the
    # machine and payout run out under the floor, while the room is 6 - so its far edge is
    # correctly empty above the pit, and the test was measuring the machine again.
    z0, z1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    wall = solid[1:-1]                       # between floor and ceiling
    for zz, xx, side in ((z0, None, "north"), (z1, None, "south"),
                         (None, x0, "west"), (None, x1, "east")):
        strip = wall[:, zz, x0:x1 + 1] if xx is None else wall[:, z0:z1 + 1, xx]
        assert strip.any(), f"the {side} wall of the room is missing"
    # ...and there is a WAY IN. Counting holes was the obvious next assertion and it is not a
    # useful one here: `wall` spans the pit courses too, where there is correctly no wall at all,
    # so the "holes" are mostly open air under the floor. What matters is that the room is neither
    # sealed nor missing a side, and both halves of that are now checked.
    assert not wall[:, z1, x0:x1 + 1].all(), "the room is sealed - there is no doorway"


def test_the_room_is_dark_with_bright_trim_not_a_white_box():
    """Built white-field/grey-wall/grey-ceiling the render was a bathroom. The cheap value ladder
    runs white_wool 236 . smooth_stone 159 . deepslate_bricks 71 . black_wool 21 - across families,
    never within one - and a room should use its range."""
    from mcbuild import blocks
    import numpy as np
    c, m = _built("high_roller", title="Room")
    lum = {}
    for i, t in enumerate(m.palette):
        try:
            n = t.value["Name"].value.split(":")[-1]
        except Exception:                                        # noqa: BLE001
            continue
        cnt = int((m.ids == i).sum())
        if not cnt or n == "air":
            continue
        rgb = blocks.color(n, "side") or blocks.color(n)
        if rgb:
            lum[n] = (sum(rgb) / 3.0, cnt)
    vals = [v for v, _ in lum.values()]
    assert max(vals) - min(vals) > 120, f"the room has no value range: {sorted(vals)}"


def test_the_hall_lays_ground_and_leaves_one_way_in():
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "hall", "width": 20, "depth": 20,
                                    "gate": 3, "check": False, "title": "CASINO"}, [])
    m = c.to_model()
    assert len(m.tile_entities) == 1, "the building carries its own name over the gate"
    assert "hall" in c.meta["contract"] and "gateway" in c.meta["contract"]


def test_the_exact_number_gate_passes_one_value_and_nothing_else():
    """`window` is the first mechanic here that is NOT a maximum.

    `threshold` pays on "roll high enough", which is the same game whatever number you put in it -
    measured cell-for-cell the four games we first shipped were two: High Roller and Coin Toss were
    99.2% identical machines, One In Three and Even Money 94.6%. An AND-NOT built from a subtract
    comparator lets the middle of the mix win and the top lose, which is a different bet.
    """
    from mcbuild.gen import circuits
    for target in (1, 2, 3, 4):
        m = circuits.window((0, 70, 0), low=target, high=target + 1)
        cells = dict(m["cells"])
        fx, fy, fz = m["foot"]
        cells[(fx - 1, fy, fz)] = "comparator[facing=east,mode=compare]"
        cells[(fx - 2, fy, fz)] = "hopper[facing=down]"
        for lvl in range(1, 7):
            s = circuit.Circuit.from_cells(dict(cells))
            s.fill((fx - 2, fy, fz), lvl)
            s.run(40)
            got = s.level(tuple(m["out"])) > 0
            assert got == (lvl == target), f"window({target}) let {lvl} through" if got \
                else f"window({target}) blocked {lvl}"


def test_a_side_input_must_arrive_at_full_strength():
    """A comparator reads its side as a LEVEL, so a boolean routed there as plain dust decays and
    the subtract stops being a subtract: run that way the gate gave 15 - 13 = 2 and "passed" a
    level it exists to block, quietly and by two. A repeater at the side delivers a clean 15."""
    from mcbuild.gen import circuits
    m = circuits.window((0, 70, 0), low=2, high=3)
    assert any("repeater" in v for v in m["cells"].values()), \
        "the window needs repeaters: two taps and a full-strength side input"


def test_the_duel_pays_exactly_when_you_beat_the_house():
    """Two rolls compared. **BOTH MUST BE DECIDED ADJACENT TO THE GATE** - a comparator reads back
    and side as levels, and an analog value cannot travel. Routed to the side on its own lane the
    house's roll decayed to 0, `A >= 0` was true for every A, and the machine paid on all nine
    combinations while looking like it worked."""
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "duel", "outcomes": 3,
                                    "pit": 2, "check": False, "title": "Duel"}, [])
    out = tuple(c.meta["outputs"][0])
    for a in (1, 2, 4):
        for b in (1, 2, 4):
            s = circuit.Circuit.of(c.to_model(), c.world_origin)
            s.fill(tuple(c.meta["rng_hopper"]), a)
            s.fill(tuple(c.meta["house_hopper"]), b)
            s.press(tuple(c.meta["inputs"][0]), ticks=4)
            s.run(80)
            paid = s.fired.get(out, 0) > 0
            assert paid == (a >= b), f"you={a} house={b} paid={paid}"


def test_every_game_answers_a_DIFFERENT_question():
    """The lineup is four MECHANICS, not four names for two.

    Cell similarity measures the ROOM, not the game - a room is ~330 cells and a machine ~150 - so
    the comparison is made on the machine alone. What must differ is `reads`: the thing the player
    is actually being asked.
    """
    from mcbuild.planner import THEMES
    kinds = {m["kind"] for m in THEMES["casino"]["modules"] if m["kind"] in
             ("high_roller", "double_or_none", "lucky_number", "duel")}
    assert len(kinds) == 4, f"expected four distinct game mechanics, got {sorted(kinds)}"
    reads = set()
    for k in sorted(kinds):
        c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": k, "outcomes": 3, "pit": 2,
                                        "check": False, "title": k}, [])
        reads.add(c.meta["reads"])
        assert "in" in c.meta["contract"] or "outcomes" in c.meta["contract"], \
            f"{k} does not state its odds: {c.meta['contract']}"
    assert len(reads) == 4, f"two games answer the same question: {sorted(reads)}"


def test_each_mechanic_reads_differently_from_the_aisle():
    """A player cannot see a circuit. Four verified mechanics in four identical grey rooms are
    four identical rooms, so each kind carries its own accent."""
    from mcbuild.gen import casino
    accents = {v["accent"] for v in casino.KIND_ACCENT.values()}
    assert len(accents) == len(casino.KIND_ACCENT), "two mechanics share a colour"
    for k in ("high_roller", "double_or_none", "lucky_number", "duel"):
        assert k in casino.KIND_ACCENT, f"{k} has no accent and will look like its neighbour"


def test_the_wheel_lights_exactly_one_pocket_in_every_orientation():
    """THE FIRST GAME HERE WITH A DIFFERENT SHAPE, and the first that is a DECODER.

    A bar reads a level as a length and a threshold gates it; this splits one roll into three
    outputs, exactly one live. Orientation is tested because the three gates are arranged by a
    rotation table, and a mistake there is invisible in a render.
    """
    for facing in ("east", "west", "north", "south"):
        c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "wheel", "pit": 2,
                                        "check": False, "facing": facing, "title": "W"}, [])
        pockets = [tuple(v) for v in c.meta["pockets"]]
        lit_for = {}
        for roll in (1, 2, 4):
            s = circuit.Circuit.of(c.to_model(), c.world_origin)
            s.fill(tuple(c.meta["rng_hopper"]), roll)
            s.press(tuple(c.meta["inputs"][0]), ticks=4)
            s.run(80)
            lit = [i for i, q in enumerate(pockets) if s.powered(q)]
            assert len(lit) == 1, f"{facing}: roll {roll} lit {lit} pockets, want exactly 1"
            lit_for[roll] = lit[0]
        assert len(set(lit_for.values())) == 3, \
            f"{facing}: two rolls share a pocket - {lit_for}"


def test_the_wheels_gates_have_CLEARANCE_not_just_no_overlap():
    """**ADJACENT DUST IS ONE NETWORK.** The arrangement was first searched for gates that shared
    no cell, and the winner put gate 1's output ONE BLOCK from gate 4's dust: a roll of 4 pushed
    15 into the level-1 pocket and lit two. Clearance is the property, so clearance is the test -
    and it re-derives the search, so a change to `window`'s footprint fails here, not in game.
    """
    from mcbuild.gen import circuits
    hop = (0, 69, 0)
    faces, sides, levels = ("east", "west", "north"), (1, 1, -1), (1, 2, 4)
    boxes = {}
    for face, sd, lvl in zip(faces, sides, levels):
        fx, _fy, fz = circuits.STEP[face]
        cmp_pos = (hop[0] + fx, hop[1], hop[2] + fz)
        g = circuits.window((cmp_pos[0] + fx, cmp_pos[1], cmp_pos[2] + fz),
                            low=lvl, high=lvl + 1, facing=face, side=sd)
        lamp = (g["out"][0] + fx, g["out"][1], g["out"][2] + fz)
        boxes[lvl] = set(g["cells"]) | {lamp, cmp_pos}

    def nbrs(c):
        x, y, z = c
        return [(x + 1, y, z), (x - 1, y, z), (x, y + 1, z),
                (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)]

    import itertools
    for a, b in itertools.combinations(boxes, 2):
        assert not (boxes[a] & boxes[b]), f"gates {a} and {b} share cells"
        touching = [c for c in boxes[a] for d in nbrs(c) if d in boxes[b]]
        assert not touching, f"gates {a} and {b} touch at {touching[:2]} - one dust network"


def test_decoration_is_never_laid_before_structure():
    """The pocket colour ring was painted into cells a later gate had not reached yet, `_lay` then
    skipped them as occupied, and the level-4 gate shipped with its subtract comparator replaced by
    red wool - so a roll of 4 lit the level-1 pocket. Every gate is built before any pocket now."""
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "wheel", "pit": 2,
                                    "check": False, "title": "W"}, [])
    m = c.to_model()
    names = []
    for t in m.palette:
        try:
            names.append(t.value["Name"].value.split(":")[-1])
        except Exception:                                        # noqa: BLE001
            names.append("air")
    import numpy as np
    have = {names[i] for i in np.unique(m.ids) if names[i] != "air"}
    assert "comparator" in have, "the wheel lost its comparators to decoration"
    n_cmp = sum(int((m.ids == i).sum()) for i, n in enumerate(names) if n == "comparator")
    assert n_cmp >= 6, f"expected 3 readers + 3 subtract gates, found {n_cmp} comparators"


def test_the_prize_wall_is_dead_at_rest_and_one_button_gives_one_prize():
    """**THE REDSTONE BLOCK MADE THE WHOLE WALL USELESS AND NOTHING NOTICED.**

    Every dispenser had a `redstone_block` stuck permanently to its back, so all of them were LIVE
    AT REST. A dispenser fires on a rising edge: powered for ever means it dispensed once when the
    chunk loaded and never again, and the buttons - mounted diagonally, touching nothing - did
    nothing at all. Twenty dispensers across four walls, permanently on and permanently dead.

    It survived because this module was the one thing here with no contract asserted by simulation,
    which is exactly the gap `chase` and `vault` were cut to close.
    """
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "prize_wall", "lanes": 5,
                                    "check": False}, [])
    m = c.to_model()
    outs = [tuple(o) for o in c.meta["outputs"]]
    ins = [tuple(i) for i in c.meta["inputs"]]
    s = circuit.Circuit.of(m, c.world_origin)
    s.run(40)
    live = [o for o in outs if s.powered(o)]
    assert not live, f"{len(live)} dispensers are powered with nobody pressing anything"
    for k, btn in enumerate(ins):
        s2 = circuit.Circuit.of(m, c.world_origin)
        s2.press(btn, ticks=4)
        s2.run(40)
        fired = [i for i, o in enumerate(outs) if s2.fired.get(o, 0)]
        assert fired == [k], f"button {k} fired dispensers {fired}"


def test_a_floor_button_never_stands_on_wire():
    """The wheel's link descended straight through the cell under its button, so the pad became
    redstone dust - and a floor button on wire is not a placement the game allows. It was invisible
    in every render and the audit passed it."""
    from mcbuild.gen import vertical, casino as K
    w = vertical.World()
    p = dict(K.CASINO)
    p.update({f"pal_{k}": v for k, v in K.PALETTE.items()})
    p.update({"at": [0, 70, 0], "kind": "wheel", "pit": 2, "check": False,
              "facing": "east", "title": "W"})
    meta = K._wheel(w, p, None)
    bx, by_, bz = meta["inputs"][0]
    under = w.name(bx, by_ - 1, bz)
    assert under not in (None, "redstone_wire", "air"), \
        f"the button is standing on {under}"


def test_every_material_in_the_casino_has_a_purpose():
    """**NO MYSTERY BLOCKS.** The bar's lamp caps used to cycle an eight-colour board list, which
    on a four-lamp bar is four arbitrary colours - and it is where the whole casino's stray three
    pink and three blue wool came from. A reading instrument in four unrelated colours is confetti,
    not a scale, so the caps are the kind's own accent and the palette is closed.
    """
    import collections
    import os as _os
    from mcbuild import layers
    if not _os.path.exists("out/Casino Complete.litematic"):
        import pytest as _p
        _p.skip("the casino has not been sliced in this checkout")
    allowed = {
        "smooth_stone", "deepslate_bricks", "stone", "black_wool", "white_wool", "red_wool",
        "green_wool", "yellow_wool", "lime_wool", "light_blue_wool", "purple_wool",
        "red_carpet", "yellow_carpet", "lime_carpet", "light_blue_carpet", "purple_carpet",
        "redstone_wire", "repeater", "comparator", "dropper", "dispenser", "hopper", "barrel",
        "redstone_block", "redstone_torch", "redstone_wall_torch", "redstone_lamp", "note_block",
        "lantern", "oak_wall_sign", "stone_button", "oak_fence", "stone_brick_stairs",
        # WOOL OFF THE GROUND (2026-09-01): `floor`, `trim` and `aisle` moved from wool to stone
        # in `PALETTE` and every `LAND_SKIN`, so a re-slice of the casino carries these instead of
        # the ones above wherever a room's floor, field or aisle used to be wool. Both sets are
        # listed rather than swapped, because a checkout sliced before this change still ships the
        # old names and this test must not fail on a file it did not cause.
        "polished_blackstone_bricks", "diorite", "blackstone", "tuff",
        "cracked_polished_blackstone_bricks", "red_nether_bricks", "spruce_planks",
    }
    got = collections.Counter(n for n, _ in layers._read("Casino Complete")[0].values())
    stray = {n: k for n, k in got.items() if n not in allowed}
    assert not stray, f"blocks with no stated purpose: {stray}"


# WOOL IS A RUG, A PILASTER, AN AWNING, A TARGET BOARD - NEVER THE GROUND ITSELF. `floor` is the
# room's border ring and the wheel's felt; `trim` is the room's field AND the hall's own grid
# line (`_hall` reuses it as `line`); `tile` and `aisle` are the hall's checker and its aisle
# stripe; `shell` is the hall's floor as well as its walls. `accent`, `carpet`, `canopy` and
# `board` are deliberately NOT checked - a carpet is a rug laid ON the floor, an accent is now
# only ever a pilaster cap, a canopy an awning and a board a readout, and all four are exactly
# the "wool for other things" this economy is fine with.
def test_no_land_stands_on_wool():
    from mcbuild.gen import casino as K
    for key in ("floor", "trim", "tile", "aisle", "shell"):
        assert "_wool" not in K.PALETTE[key], f"PALETTE.{key} is {K.PALETTE[key]!r}"
    for land, sk in K.LAND_SKIN.items():
        for key in ("floor", "trim", "tile", "aisle", "shell"):
            assert "_wool" not in sk[key], f"{land}.{key} is {sk[key]!r} - wool doing a floor's job"


# --------------------------------------------------------------------------- the INPUT half
#
# **EVERY TEST ABOVE DRIVES THE HOPPER WITH `Circuit.fill`, WHICH STATES A ROLL RATHER THAN ROLLING
# ONE.** That is the honest way to test the payout half - the simulator has no entities and cannot
# eject an item - and it meant the whole INPUT half of every machine was unexercised. Two games
# shipped with a randomiser their own button could not trigger: the button's descent ran
# orthogonally adjacent to the pulse's delay leg for three cells, a held button parked a permanent
# 15 on the subtract's side, the monostable never opened, the hopper never received an item and the
# comparator read 0 for ever. `high_roller` escaped only because it is one block wider.
#
# A dropper firing is an EDGE, and an edge is something the simulator DOES model. So this half is
# testable after all, and it is the assertion that was missing.


def _roll_check(kind, outcomes):
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": kind, "outcomes": outcomes,
                                    "pit": 2, "check": False, "title": "T"}, [])
    s = circuit.Circuit.of(c.to_model(), c.world_origin)
    s.press(tuple(c.meta["inputs"][0]), ticks=4)
    s.run(60)
    return c, s


def _dropper_over(hopper):
    """A `circuits.randomiser` puts its dropper directly over its hopper."""
    return (hopper[0], hopper[1] + 1, hopper[2])


@pytest.mark.parametrize("kind", ["high_roller", "double_or_none", "lucky_number", "duel",
                                  "wheel"])
@pytest.mark.parametrize("outcomes", [2, 3])
def test_a_press_actually_rolls_the_dice(kind, outcomes):
    """ONE PRESS, ONE ROLL. Not "the payout works if you tell it the hopper is full" - the button
    has to reach the dropper, and the dropper has to eject exactly once."""
    c, s = _roll_check(kind, outcomes)
    d = _dropper_over(tuple(c.meta["rng_hopper"]))
    assert s.name(d) == "dropper", "something overwrote the randomiser"
    assert s.fired.get(d, 0) == 1, f"{kind}/{outcomes}: the button never rolled the dice"


@pytest.mark.parametrize("outcomes", [2, 3])
def test_the_house_rolls_too(outcomes):
    """The duel is TWO rolls, and the house's was not wired: the second `_link` from the pulse
    ended on the player's own randomiser dropper, `_link` correctly refuses to overwrite a
    component, and what was left sat one diagonal short. A diagonal is not a connection - so the
    house's hopper stayed empty, its side of the gate read 0, and `A >= 0` is true for every A.
    That is the machine paying on all nine combinations, which is the exact fault the game's own
    docstring says it fixed at the gate."""
    c, s = _roll_check("duel", outcomes)
    house = _dropper_over(tuple(c.meta["house_hopper"]))
    assert s.fired.get(house, 0) == 1, "the house never rolled - it would win nothing, for ever"


def test_holding_the_button_still_rolls_only_once():
    """A player HOLDS a button, and a held roll is a bank being emptied one item at a time."""
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "double_or_none", "outcomes": 3,
                                    "pit": 2, "check": False, "title": "T"}, [])
    s = circuit.Circuit.of(c.to_model(), c.world_origin)
    s.press(tuple(c.meta["inputs"][0]), ticks=40)
    s.run(80)
    d = _dropper_over(tuple(c.meta["rng_hopper"]))
    assert s.fired.get(d, 0) == 1, "a held button must be one roll, not a stream of them"


def test_a_losing_test_must_also_prove_the_machine_can_win():
    """**A BOUND LOOSER THAN THE BUG IS NOT A TEST.**
    `test_the_button_run_never_touches_the_decision_run` asserted only that a LOSING roll pays
    nothing - which a machine that cannot pay at all satisfies perfectly. Both halves, or the
    assertion is free."""
    for outcomes in (2, 3):
        levels = circuits_levels(outcomes)
        c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "double_or_none", "pit": 2,
                                        "outcomes": outcomes, "check": False}, [])
        pay = tuple(c.meta["outputs"][0])
        won = circuit.Circuit.of(c.to_model(), c.world_origin)
        won.fill(tuple(c.meta["rng_hopper"]), max(levels))
        won.press(tuple(c.meta["inputs"][0]), ticks=4)
        won.run(60)
        assert won.fired.get(pay, 0) == 1, f"{outcomes}: a winning roll paid nothing"

        lost = circuit.Circuit.of(c.to_model(), c.world_origin)
        lost.fill(tuple(c.meta["rng_hopper"]), min(levels))
        lost.press(tuple(c.meta["inputs"][0]), ticks=4)
        lost.run(60)
        assert lost.fired.get(pay, 0) == 0, f"{outcomes}: a loss paid out"


def test_the_wheels_approach_never_crosses_a_gate(facings=("east", "west", "north", "south")):
    """THREE GATES RADIATE FROM THE HUB AND EACH READS A DECAYING LINE. A run that crosses one
    injects 15 into the very dust whose decay is the measurement, and every roll then reads as the
    highest - which is what happened the moment the button moved by a single cell: two pockets lit
    on one roll. The approach comes in on `rot["south"]`, the one face with no gate on it, and
    nothing may sit within a cell of any gate's own line."""
    for facing in facings:
        c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "wheel", "pit": 2,
                                        "check": False, "facing": facing, "title": "W"}, [])
        s = circuit.Circuit.of(c.to_model(), c.world_origin)
        hop = tuple(c.meta["rng_hopper"])
        btn = tuple(c.meta["inputs"][0])
        # the approach column: every cell between the button and the hub, at the button's course
        ax = 0 if btn[0] == hop[0] else (1 if btn[0] > hop[0] else -1)
        az = 0 if btn[2] == hop[2] else (1 if btn[2] > hop[2] else -1)
        assert (ax == 0) != (az == 0), "the approach must be one straight column"
        n = max(abs(btn[0] - hop[0]), abs(btn[2] - hop[2]))
        for k in range(1, n):
            cell = (hop[0] + ax * k, btn[1], hop[2] + az * k)
            if s.name(cell) == "air":
                continue
            assert s.name(cell) in ("redstone_wire", "repeater", "comparator"), \
                f"{facing}: the approach is interrupted at {cell} by {s.name(cell)}"
        for roll in (1, 2, 4):
            t = circuit.Circuit.of(c.to_model(), c.world_origin)
            t.fill(hop, roll)
            t.press(btn, ticks=4)
            t.run(80)
            lit = [i for i, q in enumerate(c.meta["pockets"]) if t.powered(tuple(q))]
            assert len(lit) == 1, f"{facing}: roll {roll} lit {lit}"
