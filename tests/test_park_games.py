"""Every game in the park's buildings against its own stated CONTRACT, by SIMULATION.

A kind whose contract is not asserted here does not belong in `gen/park_games.py`. That rule is
not decoration: a redstone build is the one thing in this project whose wrongness is invisible in
every render, every audit and every bill of materials - it looks finished and does nothing - and
two finished casino games were deleted for failing exactly this check.

**AN ENTITY IS AN INPUT YOU STATE.** `mcbuild.circuit` has no entities, so it cannot fire an arrow
into a target, put items on a scale or stock a barrel. Every one of those is driven here with
`set_signal` and `fill`, which is precisely how the item sorter, the dropper randomiser and the
arcade are already tested. What that leaves unproven travels in each build's `unverified` list
rather than being quietly assumed.

**AND A BOUND LOOSER THAN THE BUG IS NOT A TEST.** `circuits.pulse` shipped as a bare repeater for
months because its own test asserted `high < 20` out of twenty ticks, which a permanent delay
satisfies as comfortably as a pulse; `circuits.latch` still ships a test that asserts only that the
latch "has state at all", and the latch does not hold. So everything below asserts the CONTRACT:
which lamp, which lane, which of eight settings, and - just as hard - that nothing else did
anything at all, and that nothing fires the moment the machine is built.
"""
from __future__ import annotations

import collections
import glob
import itertools
import os

import pytest
import yaml

from mcbuild import audit, blocks, nbt, palette
from mcbuild.circuit import Circuit
from mcbuild.gen import park_games as pg

FACINGS = ("east", "west", "north", "south")
LANDS = ("midway", "frontier", "prismworks")
KINDS = sorted(pg.BUILDERS)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGS = sorted(glob.glob(os.path.join(ROOT, "configs", "pf_game_*.yaml")))
WORLD = os.path.join(ROOT, "out", "Park Complete.litematic")


def build(kind: str, **cfg):
    return pg.build({"at": [0, 64, 0], "kind": kind, "facing": "east", "land": "midway", **cfg})


def sim(kind: str, **cfg):
    """A built machine and a circuit over it, in WORLD coordinates - the frame the sidecars carry
    everywhere else, so a meta coordinate can be handed straight to the simulator."""
    c = build(kind, **cfg)
    return c, Circuit.of(c.to_model(), c.world_origin)


def names_of(c) -> collections.Counter:
    m = c.to_model()
    out = collections.Counter()
    for i in set(m.ids[m.ids > 0].ravel().tolist()):
        out[nbt.state_name(m.palette[i]).split(":")[-1]] += int((m.ids == i).sum())
    return out


# --------------------------------------------------------------------------- every kind, in general


def test_every_kind_states_a_contract_and_says_what_it_cannot_prove():
    for kind in KINDS:
        c = build(kind)
        assert c.meta.get("contract"), f"{kind} has no contract"
        assert "unverified" in c.meta, f"{kind} does not say what it cannot prove"


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_is_one_connected_piece_with_no_placement_problems(kind):
    """**A COMPONENT COUNT IS THE ONLY CHECK THAT SEES A FLOATING CONSOLE.** Built one course above
    its own plinth, a cabinet ships in two pieces with zero placement problems reported, because
    every cell has something under it at its OWN course."""
    for facing in FACINGS:
        for land in LANDS:
            c = build(kind, facing=facing, land=land)
            r = audit.audit(c.to_model())
            assert not r.problems, f"{kind}/{facing}/{land}: {r.problems[:3]}"
            assert len(r.components) == 1, f"{kind}/{facing}/{land}: {r.components}"


@pytest.mark.parametrize("kind", KINDS)
def test_nothing_reaches_below_the_course_a_player_stands_on(kind):
    """**THE ONE PROPERTY THAT KEEPS THIS OFF THE BUILDING'S FLOOR.** `arcade`'s games hide their
    machines in a pit; a console fitted into a finished room cannot, because the cell under the
    standing course belongs to somebody else's design and taking it is an overlap, not a
    composition. Everything here is built upward from h=0 and this is what says so."""
    for facing in FACINGS:
        c = build(kind, facing=facing)
        assert c.meta["courses"][0] >= 0, f"{kind}/{facing} reaches {c.meta['courses']}"


@pytest.mark.parametrize("kind", KINDS)
def test_no_live_component_shows_on_the_outside_of_the_cabinet(kind):
    """A wire on the perimeter is a machine a player can break by accident and a machine the
    concealment rule forbids. `_ring` counts them rather than trusting the layout."""
    for facing in FACINGS:
        for land in LANDS:
            c = build(kind, facing=facing, land=land)
            assert c.meta["leaks"] == [], f"{kind}/{facing}/{land} leaks {c.meta['leaks']}"


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_is_legal_affordable_and_1_19(kind):
    """Rules 12, 13 and 16 at once: a real block, a 1.19 block, and not CURRENCY. Dirt and grass
    are money on this server, which is how a lion once shipped with a coat of 5,173 dirt."""
    for land in LANDS:
        c = build(kind, land=land)
        counts = names_of(c)
        for n in counts:
            assert blocks.exists(n), f"{kind}/{land}: {n} is not a block"
            assert blocks.spendable(n), f"{kind}/{land}: {n} is CURRENCY on this server"
        assert "cobblestone" not in counts, f"{kind}/{land} uses cobblestone"
        assert not audit.report_server_blocks(c.to_model()), f"{kind}/{land} uses a non-1.19 block"
        assert not audit.check_states(c.to_model()), f"{kind}/{land} emits an illegal block state"


@pytest.mark.parametrize("kind", KINDS)
def test_the_only_expensive_block_is_the_lamp_and_it_is_counted(kind):
    """A LIGHT CANNOT BE SUBSTITUTED BY COLOUR - a dark block that looks like a lamp is a display
    that does not work - so `redstone_lamp` is priced into `budget` rather than swapped out."""
    c = build(kind)
    counts = names_of(c)
    dear = {n: v for n, v in counts.items() if palette.tier(n) == "expensive"}
    assert set(dear) <= {"redstone_lamp"}, f"{kind} spends on {sorted(set(dear) - {'redstone_lamp'})}"
    assert c.meta["budget"].get("redstone_lamp", 0) == dear.get("redstone_lamp", 0)


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_signs_itself(kind):
    """A GAME NOBODY CAN WORK OUT HOW TO PLAY IS AN EMPTY STRUCTURE, which is the whole complaint
    this module answers. `_sign` REFUSES a cell with no block behind it and returns False, so a
    console with an open back ships its name and its rules SILENTLY missing on a build that audits
    perfectly clean - five arcade kinds once did exactly that."""
    for facing in FACINGS:
        for land in LANDS:
            c = build(kind, facing=facing, land=land)
            assert c.meta["signed"] is True, f"{kind}/{facing}/{land} lost a sign"


def test_every_sign_line_fits_on_a_sign():
    """FIFTEEN CHARACTERS. Longer clips mid-word and it only shows up in a screenshot after the
    build has been placed.

    **THE TEXT LIVES IN `Canvas.tiles`, NOT IN A `signs` ATTRIBUTE**, and the first version of this
    test read the attribute that does not exist: the loop had nothing to iterate and the test
    passed on every kind, including one whose title was deliberately made too long to check it.
    A test that cannot fail is worse than no test, because it is counted."""
    import json as _json

    from mcbuild.gen.park import SIGN_WIDTH
    seen = 0
    for kind in KINDS:
        c = build(kind)
        assert c.tiles, f"{kind} placed no sign text at all"
        for text in c.tiles.values():
            for line in list(text["front"]) + list(text["back"]):
                seen += 1
                assert len(_json.loads(line).get("text", "")) <= SIGN_WIDTH, f"{kind}: {line!r}"
    assert seen >= 8 * len(KINDS), f"only {seen} sign lines were checked"


def _sign_lines(c) -> list:
    import json as _json
    return [_json.loads(l).get("text", "")
            for t in c.tiles.values() for l in list(t["front"]) + list(t["back"])]


def test_a_game_whose_rule_is_a_NUMBER_prints_that_NUMBER():
    """**THE FIFTEEN-CHARACTER CUT IS SILENT, AND IT ATE THE ONE THING THAT MATTERED.** "stop at
    exactly 4" is sixteen characters, so `_sign` clipped it to "stop at exactly" - a precision game
    whose sign does not say what to stop at, on a build where every other check passed and every
    line was within the width. Checking the LENGTH cannot see that; checking that the number
    survived can."""
    for want in (3, 5, 9):
        assert any(str(want) in l for l in _sign_lines(build("mark", mark=want, band=1))), \
            f"the mark {want} is not on the sign"
    for want in (4, 7):
        assert any(str(want) in l for l in _sign_lines(build("aim", score=want))), \
            f"the aim score {want} is not on the sign"
        assert any(str(want) in l for l in _sign_lines(build("striker", score=want))), \
            f"the striker score {want} is not on the sign"
    for n in (2, 3, 4):
        pat = [True] * n
        assert any(str(n) in l for l in _sign_lines(build("pattern", pattern=pat))), \
            f"the lever count {n} is not on the sign"


# --------------------------------------------------------------------------- the contracts


@pytest.mark.parametrize("facing", FACINGS)
def test_the_target_wall_reads_a_hit_as_a_length_and_rings_only_on_a_maximum(facing):
    """THE DECAY IS THE MEASUREMENT AND IT IS ALSO THE THRESHOLD: a run of `score` cells lights its
    last lamp exactly when the reading reached the end of it, so the bell needs no gate."""
    score = 6
    for level in (0, 1, 3, 5, 6, 9, 15):
        c, s = sim("aim", facing=facing, score=score)
        if level:
            s.set_signal(tuple(c.meta["targets"][0]), level)
        s.run(14)
        lit = [i for i, l in enumerate(c.meta["lamps"][0]) if s.powered(tuple(l))]
        assert lit == list(range(min(level, score))), f"{facing}: level {level} lit {lit}"
        assert s.powered(tuple(c.meta["bells"][0])) is (level >= score), f"{facing}: level {level}"


@pytest.mark.parametrize("facing", FACINGS)
def test_no_two_discs_answer_for_each_other(facing):
    """**ADJACENT DUST IS ONE NETWORK.** Laid two cells apart, one lane's last dust cell sits beside
    the next lane's disc and every disc answers for every bar - which is the plinko board's own
    recorded failure, and it audits perfectly clean."""
    for hit in range(3):
        c, s = sim("aim", facing=facing, discs=3, score=8)
        s.set_signal(tuple(c.meta["targets"][hit]), 8)
        s.run(16)
        lit = [sum(1 for l in row if s.powered(tuple(l))) for row in c.meta["lamps"]]
        assert lit == [8 if k == hit else 0 for k in range(3)], f"{facing}: hit {hit} lit {lit}"
        bells = [s.powered(tuple(b)) for b in c.meta["bells"]]
        assert bells == [k == hit for k in range(3)], f"{facing}: hit {hit} rang {bells}"


@pytest.mark.parametrize("facing", FACINGS)
def test_the_striker_climbs_and_only_a_maximum_reaches_the_bell(facing):
    rungs = 8
    for level in (0, 1, 4, 7, 8, 15):
        c, s = sim("striker", facing=facing, score=rungs)
        if level:
            s.set_signal(tuple(c.meta["target"]), level)
        s.run(18)
        lit = [i for i, l in enumerate(c.meta["lamps"]) if s.powered(tuple(l))]
        assert lit == list(range(min(level, rungs))), f"{facing}: level {level} lit {lit}"
        assert s.powered(tuple(c.meta["bell"])) is (level >= rungs), f"{facing}: level {level}"


def test_a_striker_has_no_repeater_in_its_column():
    """THE DECAY IS THE MEASUREMENT. One repeater anywhere in the climb restores the signal to 15
    and lights the whole tower on any hit at all - which is a lamp, not an instrument."""
    c = build("striker", score=8)
    m = c.to_model()
    lamps = [tuple(x) for x in c.meta["lamps"]]
    ox, oy, oz = c.world_origin
    lo = min(l[1] for l in lamps)
    for (x, y, z) in [(x, y, z) for y in range(lo - oy, lo - oy + 8)
                      for z in range(m.shape_xyz[2]) for x in range(m.shape_xyz[0])]:
        assert not m.name_at(x, y, z).split(":")[-1].startswith("repeater"), "repeater in the column"


@pytest.mark.parametrize("facing", FACINGS)
def test_the_mark_pays_for_exactly_the_mark_and_going_over_loses_it(facing):
    """THE ONLY BET HERE THAT IS NOT A MAXIMUM. One under is dark, one OVER is dark again, and that
    losing case is the whole game - `circuits.window`'s exact-value form once silently degraded to a
    threshold for every caller there was, so it is asserted from both sides."""
    for want in (3, 4, 6):
        for level in range(0, want + 3):
            c, s = sim("mark", facing=facing, mark=want, band=1)
            if level:
                s.set_signal(tuple(c.meta["plate"]), level)
            s.run(18)
            hit = level == want
            assert s.powered(tuple(c.meta["lamp"])) is hit, f"{facing}: mark {want} level {level}"
            assert s.powered(tuple(c.meta["bell"])) is hit, f"{facing}: mark {want} level {level}"


@pytest.mark.parametrize("facing", FACINGS)
def test_the_double_needs_both_hands(facing):
    """An AND that is really an OR pays on either half of a two-player game, which is the whole
    difference between reading the players and ignoring one of them."""
    for a, b in itertools.product((False, True), repeat=2):
        c, s = sim("pair", facing=facing)
        btns = [tuple(x) for x in c.meta["buttons"]]
        if a:
            s.press(btns[0], 8)
        if b:
            s.press(btns[1], 8)
        ever = False
        for _ in range(26):
            s.step()
            ever = ever or s.powered(tuple(c.meta["lamp"]))
        assert ever is (a and b), f"{facing}: A={a} B={b}"


@pytest.mark.parametrize("facing", FACINGS)
def test_a_torch_gate_does_not_pay_the_moment_it_is_built(facing):
    """**A TORCH GATE IS TRUE FOR TWO TICKS THE MOMENT IT IS BUILT.** Every torch starts lit, so the
    output is briefly high before the inverters settle - and it happens again on every chunk load.
    Measured at exactly two ticks on the first version of `pair`, which rang its own bell with
    nobody in the room. `_guard` is the delay-2 repeater that swallows it."""
    for kind in ("pair", "pattern"):
        c, s = sim(kind, facing=facing)
        for _ in range(20):
            s.step()
            if kind == "pair":
                assert not s.powered(tuple(c.meta["lamp"])), f"{kind}/{facing} fired at rest"
            else:
                assert not all(s.powered(tuple(l)) for l in c.meta["lamps"]), \
                    f"{kind}/{facing} opened at rest"


@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("want", [(True, False, True), (True, True, True), (False, True, False)])
def test_exactly_one_lever_setting_opens_the_lock(facing, want):
    """Eight settings, one answer. An inverted input is a torch in its own lane, so the answer is
    never "all of them up" - which is a lock with one obvious key."""
    for combo in itertools.product((False, True), repeat=3):
        c, s = sim("pattern", facing=facing, pattern=list(want))
        for lever, v in zip(c.meta["levers"], combo):
            s.set(tuple(lever), v)
        s.run(32)
        open_ = all(s.powered(tuple(l)) for l in c.meta["lamps"])
        assert open_ is (combo == want), f"{facing}: want {want} tried {combo}"


@pytest.mark.parametrize("facing", FACINGS)
def test_the_vault_door_opens_on_the_answer_and_on_nothing_else(facing):
    """The one output in this file a player walks THROUGH. In Minecraft powering either half of an
    iron door opens both, so the lower half is what is asserted."""
    want = (True, False, True)
    for combo in itertools.product((False, True), repeat=3):
        c, s = sim("pattern", facing=facing, pattern=list(want), door=True)
        assert len(c.meta["door"]) == 2
        for lever, v in zip(c.meta["levers"], combo):
            s.set(tuple(lever), v)
        s.run(32)
        assert s.powered(tuple(c.meta["door"][0])) is (combo == want), f"{facing}: {combo}"


@pytest.mark.parametrize("facing", FACINGS)
def test_the_countdown_walks_the_board_in_order_and_the_bell_is_last(facing):
    """A ONE-TICK PULSE IS SWALLOWED BY A DELAY-ONE REPEATER, in this model and in the game's own
    scheduler alike, so the press is stretched before it enters the chain. A bell that rings before
    the light has arrived is a starter nobody can time against."""
    stages = 5
    c, s = sim("starter", facing=facing, stages=stages)
    s.press(tuple(c.meta["button"]), 4)
    first, bell_at = {}, None
    for t in range(60):
        s.step()
        for k, l in enumerate(c.meta["lamps"]):
            if s.powered(tuple(l)) and k not in first:
                first[k] = t
        if bell_at is None and s.powered(tuple(c.meta["bell"])):
            bell_at = t
    assert sorted(first) == list(range(stages)), f"{facing}: only {sorted(first)} ever lit"
    order = [first[k] for k in range(stages)]
    assert order == sorted(order) and order[0] < order[-1], f"{facing}: lit in order {order}"
    assert bell_at is not None and bell_at >= first[stages - 1], f"{facing}: bell at {bell_at}"


def test_the_countdown_does_nothing_until_it_is_pressed():
    c, s = sim("starter", stages=5)
    s.run(30)
    assert not any(s.powered(tuple(l)) for l in c.meta["lamps"])
    assert not s.powered(tuple(c.meta["bell"]))


@pytest.mark.parametrize("facing", FACINGS)
def test_each_prize_window_answers_only_for_its_own_barrel(facing):
    """A counter that lies about its stock is worse than a counter with no lamps: it sends somebody
    to a window with nothing behind it."""
    lanes = 4
    for stocked in ([], [0], [1, 3], [0, 1, 2, 3]):
        c, s = sim("counter", facing=facing, lanes=lanes)
        for k in stocked:
            s.fill(tuple(c.meta["barrels"][k]), 5)
        s.run(12)
        lit = [s.powered(tuple(l)) for l in c.meta["lamps"]]
        assert lit == [k in stocked for k in range(lanes)], f"{facing}: stocked {stocked} -> {lit}"


def test_the_call_button_rings_the_counter_bell():
    c, s = sim("counter", lanes=4)
    s.run(6)
    assert not s.powered(tuple(c.meta["bell"]))
    s.press(tuple(c.meta["button"]), 6)
    s.run(3)
    assert s.powered(tuple(c.meta["bell"]))


# --------------------------------------------------------------------------- the shipped park


def _cells(path):
    """Every solid cell of a shipped design, in WORLD coordinates."""
    import json

    from mcbuild import schem
    m = schem.load(path)
    side = json.load(open(path.replace(".litematic", ".scan.json"), encoding="utf-8"))
    o = side["origin"]
    sx, sy, sz = m.shape_xyz
    solid = m.solid()
    out = set()
    for y in range(sy):
        for z in range(sz):
            for x in range(sx):
                if solid[y, z, x]:
                    out.add((o["x"] + x, o["y"] + y, o["z"] + z))
    return out, side


def _shipped():
    got = []
    for cfg in CONFIGS:
        with open(cfg, encoding="utf-8") as fh:
            spec = yaml.safe_load(fh)
        lit = os.path.join(ROOT, "out", spec["name"] + ".litematic")
        if os.path.exists(lit):
            got.append((spec, lit))
    return got


def test_every_config_names_this_generator_and_a_building():
    assert CONFIGS, "no pf_game_* configs found"
    for cfg in CONFIGS:
        with open(cfg, encoding="utf-8") as fh:
            spec = yaml.safe_load(fh)
        assert spec["gen"] == "park_games", cfg
        assert spec["params"]["kind"] in pg.BUILDERS, cfg
        assert spec["params"].get("building"), f"{cfg} does not say which building it fits out"
        assert spec["params"].get("under"), f"{cfg} builds without a world to keep out of"
        assert spec["name"].startswith("PF Game "), cfg


@pytest.mark.skipif(not os.path.exists(WORLD), reason="the composited park has not been built")
def test_no_shipped_game_takes_a_cell_the_park_already_owns():
    """**RULE 2, AND THE ONE PROPERTY THAT MAKES THIS SAFE TO PLACE.** A console is fitted into a
    room that exists; a cell the capture owns is not a cell to compose with, it is an overlap. The
    generator refuses those cells and COUNTS them, because a machine missing a cell is a machine
    that does nothing - so a non-zero count is a siting error, not a tidy-up.

    **AND `Park Complete` IS A SNAPSHOT OF A PARK THAT NOW CONTAINS THESE GAMES**, which is the
    trap this repo has shipped three times. Read as "the world before the design", the composite
    reports a placed game as colliding with ITSELF - the moment `tools/park_place.py` started
    placing the three frontier games that had been built and left unplaced, this failed on
    `PF Game Pan Line` at three of its own cells. What rule 15 actually says is that an overlap
    is a cell where the world holds something DIFFERENT, so a cell the game already occupies with
    its own state is built progress rather than a clash.
    """
    shipped = _shipped()
    if not shipped:
        pytest.skip("no game designs have been generated yet")
    from mcbuild import schem
    from mcbuild.gen.vertical import Ctx
    ctx = Ctx(WORLD)
    for spec, lit in shipped:
        cells, side = _cells(lit)
        assert side.get("refused") == [], f"{spec['name']} refused {side.get('refused')}"
        mine = schem.load(lit)
        o = side["origin"]
        own = {}
        for y, z, x in zip(*mine.solid().nonzero()):
            own[(int(x) + o["x"], int(y) + o["y"], int(z) + o["z"])] = \
                mine.names[int(mine.ids[y, z, x])].split("[")[0].split(":")[-1]
        clash = [c for c in cells
                 if ctx.occupied(*c) and ctx.name_at(*c).split(":")[-1] != own.get(c)]
        assert not clash, f"{spec['name']} overlaps the park at {clash[:3]}"


def test_no_two_games_share_a_cell():
    """Ten consoles in nine rooms. Two designs claiming one cell is two printers fighting over it,
    and `verify_against` cannot see it: it audits each design against the CAPTURE, which does not
    contain the other nine."""
    shipped = _shipped()
    if len(shipped) < 2:
        pytest.skip("fewer than two game designs have been generated")
    seen = {}
    for spec, lit in shipped:
        cells, _side = _cells(lit)
        for cell in cells:
            other = seen.get(cell)
            assert other is None, f"{spec['name']} and {other} share {cell}"
            seen[cell] = spec["name"]


def test_every_shipped_game_records_a_contract_and_its_building():
    shipped = _shipped()
    if not shipped:
        pytest.skip("no game designs have been generated yet")
    for spec, lit in shipped:
        _cells_unused, side = _cells(lit)
        assert side.get("contract"), f"{spec['name']} shipped with no contract in its sidecar"
        assert side.get("building"), f"{spec['name']} does not record the building it fits out"
        assert side.get("leaks") == [], f"{spec['name']} leaks {side.get('leaks')}"
