"""THINGS TO DO IN THE HOLLOW, and every one of them driven rather than looked at.

The zone was rejected a second time - *"more interaction or 'games' vs empty buildings ... it feels
like it's just an abandoned town vs a theme park"* - and the number behind that verdict is that the
whole quarter contained **three buttons and three sculk sensors**, against 215 cells of redstone
wire. Wiring with almost nothing for a player to touch.

Two things were added and both are pinned here, because both fail INVISIBLY:

    the manor's SET PIECES    a plate, a lever and a button, each firing a piston, a lamp and a
                              dispenser ONCE and resetting. Wired straight through they would hold
                              while a player stood on the plate, which is a stuck prop rather than
                              a scare - and the render is identical.
    the OSSUARY               three shroud-levers into `arcade.and_gate`; the vault opens only
                              while all three are up. An AND gate whose keep-clear rows get
                              anything powered in them is silently an OR, which is a puzzle that
                              solves itself.

Nothing here is eyeballed. Every mechanism is SIMULATED through `mcbuild.circuit`, including that
it RESETS; every walk is FLOODED FROM REAL GROUND with the seed checked to be standable and the
region checked to be a region; and the headroom a player needs is asserted rather than assumed,
because seven flume cells, eleven ghost-train cells and four teacup rail cells have failed exactly
that in one week and not one of them showed in a render.
"""
import itertools
from collections import deque

import pytest

from mcbuild import blocks, circuit
from mcbuild.gen import hollowmanor as H
from mcbuild.gen.arcade import _ij, and_gate
from mcbuild.gen.vertical import World

import hollowwalk as HW

FACINGS = ("east", "north", "west", "south")


def _built(kind, land="hollow", facing="east", **kw):
    p = {**H.HOLLOW, "at": [0, 64, 0], "kind": kind, "land": land, "facing": facing, **kw}
    w = World()
    meta = H.BUILDERS[kind](w, p, None)
    return w, H._Frame(p), meta, p


def _spec(w):
    """The World as `circuit.Circuit.from_cells` wants it: one state string per cell."""
    return {pos: n + ("[" + ",".join(f"{k}={v}" for k, v in pr.items()) + "]" if pr else "")
            for pos, (n, pr) in w.cells.items()}


def _drive(c, trigger, kind, on=True):
    """A BUTTON IS A PULSE AND A LEVER IS A STATE, and a test that holds a button for ever is
    silently testing a lever. `Circuit.press` models the real thing; `set` is for the other two.

    **RELEASING A BUTTON IS THE PULSE EXPIRING, NOT AN INPUT.** Written to `press` again on the
    way down, the release RE-ARMED the button - so two rounds of trigger-and-release were four
    overlapping presses with the input never once going low, and the set piece correctly fired on
    the single rising edge that produced. The test failed and the machine was right.
    """
    if kind == "button":
        if on:
            c.press(trigger, ticks=6)
        return
    c.set(trigger, on)


def _vents(scare):
    return [tuple(c) for cs in scare["vents"].values() for c in cs]


def _headroom(w, cells):
    """Every cell a player stands in must have its own cell and the one over its head clear.

    `HW.standable` already demands this, so a flood cannot contain a cell that fails it - which
    is exactly why it is asserted separately: the check is only worth anything if the walk model
    and the assertion are not the same line of code read twice.
    """
    bad = []
    for (x, y, z) in cells:
        if HW.solid(w, (x, y, z)) or HW.solid(w, (x, y + 1, z)):
            bad.append((x, y, z))
    return bad


# ------------------------------------------------------------------ the trigger coupling

def test_a_floor_trigger_STRONGLY_POWERS_THE_BLOCK_BENEATH_IT():
    """**A REAL BUG IN THE SIMULATOR, FOUND BY BUILDING A SET PIECE AND NOT BY READING THE CODE.**

    `circuit._sources` read every manual input through `_attachment(pos, face, facing)`, and a
    pressure plate has NEITHER of those properties - so it fell to the default `face="wall"` and
    `facing="north"` and strongly powered a cell to one SIDE of itself. A plate lies on the ground
    and strongly powers the block BENEATH it, which is the only way a machine hidden under a floor
    can take its trigger. Every block of the set piece was legal, supported and affordable, and
    nothing fired.

    Hand-worked, because that is the only kind of case worth pinning a mechanic on: a plate, a
    block under it, and dust under THAT. The dust must read 15.
    """
    for trig in ("stone_pressure_plate", "lever[face=floor,facing=east]",
                 "stone_button[face=floor,facing=east]"):
        cells = {(0, 66, 0): trig, (0, 65, 0): "smooth_stone", (0, 64, 0): "redstone_wire",
                 (0, 63, 0): "stone"}
        c = circuit.Circuit.from_cells(cells)
        c.set((0, 66, 0), True)
        c.run(4)
        assert c.level((0, 64, 0)) == 15, f"{trig} does not feed the dust under its own support"


def test_a_plate_does_not_STRONGLY_power_a_cell_beside_itself():
    """The other half of the same fix, and it needs a fixture built to catch it rather than an
    assertion bolted onto the first one.

    A block BESIDE a plate is weakly powered - `emit` reaches all six neighbours and that part was
    always right - and a weakly powered block drives a lamp but does NOT re-power wire on the far
    side of it. That distinction is the whole of `circuit._sources`. With the wall default in
    place the plate STRONGLY powered the block to its south, so dust two cells away, touching
    nothing the builder had connected to anything, read 15.

    So: a plate, a block to one side of it, and dust beyond that block. The dust must be dark.
    """
    cells = {(0, 65, 0): "stone_pressure_plate", (0, 64, 0): "smooth_stone",
             (0, 65, 1): "smooth_stone",                       # the cell the old default picked
             (0, 65, 2): "redstone_wire", (0, 64, 2): "stone"}  # ...and dust beyond it
    c = circuit.Circuit.from_cells(cells)
    c.set((0, 65, 0), True)
    c.run(4)
    assert c.level((0, 65, 2)) == 0, \
        "a plate is re-powering wire through a block it only weakly powers"


# ------------------------------------------------------------------ the manor's set pieces

def test_the_manor_has_set_pieces_at_all():
    """The number the whole complaint rests on. A walkthrough with nothing in it is a corridor."""
    _w, _f, m, _p = _built("manor")
    assert len(m["scares"]) >= 3, f"the manor carries only {len(m['scares'])} set pieces"
    assert len({s["kind"] for s in m["scares"]}) == 3, \
        "all three set pieces take the same input - a visitor meets one idea three times"


@pytest.mark.parametrize("facing", FACINGS)
def test_every_set_piece_is_dark_and_still_at_rest(facing):
    """A prop that is already out, already lit and already fired is scenery. This is also the
    assertion that catches a machine wired to a constant, which renders identically."""
    w, _f, m, _p = _built("manor", facing=facing)
    c = circuit.Circuit.from_cells(_spec(w))
    c.run(12)
    for s in m["scares"]:
        for v in _vents(s):
            assert not c.powered(v), f"{facing}: {s['where']} is live before anyone touches it"
    assert not c.fired, f"{facing}: something dispensed itself at rest"


@pytest.mark.parametrize("facing", FACINGS)
def test_every_set_piece_fires_EVERY_vent_together(facing):
    """THE CONTRACT, SIMULATED. Three outputs on one spine: the floor lurches, the floor lights
    and something comes out of the floor, all at once. A spine long enough to lose its signal
    before the last vent is the `lamp_bank` failure - the far end simply never lights - and it is
    invisible in every render and in the block count."""
    w, _f, m, _p = _built("manor", facing=facing)
    spec = _spec(w)
    for s in m["scares"]:
        vents = _vents(s)
        assert len(vents) == 3, f"{s['where']} has {len(vents)} vents"
        c = circuit.Circuit.from_cells(spec)
        _drive(c, tuple(s["trigger"]), s["kind"])
        together = 0
        for _ in range(30):
            c.step()
            together += int(all(c.powered(v) for v in vents))
        assert together >= 1, f"{facing}: {s['where']} never had all three vents lit at once"


@pytest.mark.parametrize("facing", FACINGS)
def test_a_HELD_trigger_does_not_hold_the_set_piece_on(facing):
    """**THE ONE ASSERTION THE WHOLE PRIMITIVE EXISTS FOR.** A player stands on a plate and leans
    on a lever; wired straight through, the piston stays out and the lamp stays on for as long as
    they do, and the dispenser empties itself. `circuits.pulse` records that its own first version
    was a bare repeater, that a repeater delays BOTH edges, and that a held lever therefore drove a
    casino payout for 21 ticks out of 24 - and that it shipped because the test bounded the output
    at "fewer than twenty of twenty", which a delay satisfies as easily as a pulse.

    So the bound here is tight and it is stated as a fraction of the run: at most a quarter of
    thirty-two ticks, with the trigger held down the whole time."""
    w, _f, m, _p = _built("manor", facing=facing)
    spec = _spec(w)
    for s in m["scares"]:
        c = circuit.Circuit.from_cells(spec)
        _drive(c, tuple(s["trigger"]), s["kind"])
        high = [0] * 3
        for _ in range(32):
            c.step()
            for k, v in enumerate(_vents(s)):
                high[k] += int(c.powered(v))
        assert max(high) <= 8, f"{facing}: {s['where']} stayed live for {high} of 32 ticks"
        assert max(high) >= 1, f"{facing}: {s['where']} never fired at all"


@pytest.mark.parametrize("facing", FACINGS)
def test_a_set_piece_RESETS_and_can_be_fired_again(facing):
    """A scare that works once is a scare the second visitor never sees. Only the DISPENSER can
    answer this honestly - `circuit` counts its rising edges - because a lamp and a piston that
    went off and came back on again look the same as ones that never moved."""
    w, _f, m, _p = _built("manor", facing=facing)
    spec = _spec(w)
    for s in m["scares"]:
        drops = [tuple(c) for c in s["dispensers"]]
        assert drops, f"{s['where']} has no dispenser to count edges on"
        c = circuit.Circuit.from_cells(spec)
        trig = tuple(s["trigger"])
        for _round in range(2):
            _drive(c, trig, s["kind"], True)
            c.run(12)
            _drive(c, trig, s["kind"], False)
            c.run(8)
        assert c.fired[drops[0]] == 2, \
            f"{facing}: {s['where']} fired {c.fired[drops[0]]} times in two triggers"


def test_every_vent_is_a_full_cube_so_the_walked_floor_is_unbroken():
    """THE PROPERTY THAT LETS A MACHINE SIT IN A FLOOR PEOPLE WALK ON. A piston, a lamp and a
    dispenser are all full cubes, so at rest each one IS the floorboard over the wiring. Anything
    that is not - a bell, a repeater, a slab - punches a cell a player cannot stand on, and on a
    route that is a hole in the dark nobody could have seen in a render."""
    w, _f, m, _p = _built("manor")
    for s in m["scares"]:
        for v in _vents(s):
            name = w.name(*v)
            assert blocks.is_full_cube(name), f"{s['where']} vents through {name}, not a full cube"


def test_the_set_pieces_do_not_break_the_manors_walkthrough():
    """A set piece that costs the building its route is a worse building. The route and the check
    read ONE list - `meta["route"]` - so a test cannot agree with a build by re-deriving the same
    mistake."""
    w, _f, m, _p = _built("manor")
    got = HW.reachable(w, m["entry_at"], floor=500)
    for (name, cell) in m["route"]:
        assert HW.near(got, cell, 0), f"the route breaks at {name} {cell}"
    assert not _headroom(w, got), "the manor's walk contains cells with no headroom"


@pytest.mark.parametrize("facing", FACINGS)
def test_every_trigger_can_be_reached_on_foot(facing):
    """A verified machine you cannot walk up to is scenery with a circuit in it - the seance's own
    lesson, and the one that decides whether any of this is interaction at all."""
    w, _f, m, _p = _built("manor", facing=facing)
    got = HW.reachable(w, m["entry_at"], floor=500)
    for s in m["scares"]:
        assert HW.near(got, s["trigger"], 1), f"{facing}: nobody can reach {s['where']}"


def test_the_manor_names_every_set_piece():
    """A trigger nobody knows is a trigger is a plate you walk over and a lever you walk past.
    `park._sign` REFUSES a column with an opening in it and returns False, so a count is a count
    of signs that will actually stand - which is the only way this can be checked, because a wall
    sign hanging on air renders exactly like one on a wall."""
    _w, _f, m, _p = _built("manor")
    assert m["signs"] >= 10, f"the manor places only {m['signs']} signs"
    for s in m["scares"]:
        assert s["sign"][0], f"{s['where']} has no name"
        for line in s["sign"]:
            assert len(line) <= 15, f"{s['where']}: {line!r} is wider than a sign"


def test_the_manor_says_what_it_cannot_verify():
    """That the dispenser fires exactly once per trigger IS verified. What comes OUT of it is an
    entity and the simulator has none, so the loading instruction travels in the sidecar exactly
    as the randomiser's item mix does rather than being quietly assumed."""
    _w, _f, m, _p = _built("manor")
    assert m["unverified"], "the manor claims a scare it cannot check"
    assert m["stock"]["dispenser"], "nothing says what to load the dispensers with"


# ------------------------------------------------------------------ the ossuary

@pytest.mark.parametrize("facing", FACINGS)
def test_the_vault_opens_ONLY_when_all_three_pulls_are_up(facing):
    """ALL EIGHT COMBINATIONS, because an AND that is really an OR passes the one case anybody
    checks by hand. `and_gate`'s own docstring says how it happens: the input supports sit two
    apart so a feed can power one without powering its neighbour, and anything powered in the row
    BETWEEN them powers both - at which point the puzzle solves itself on the first lever."""
    w, _f, m, _p = _built("ossuary", facing=facing)
    spec = _spec(w)
    levers = [tuple(c) for c in m["levers"]]
    outs = [tuple(c) for c in m["doors"]] + [tuple(m["vault_lamp"])]
    for combo in itertools.product((False, True), repeat=3):
        c = circuit.Circuit.from_cells(spec)
        for lv, on in zip(levers, combo):
            c.set(lv, on)
        c.run(16)
        lit = [c.powered(o) for o in outs]
        if all(combo):
            assert all(lit), f"{facing}: all three pulled and the vault stayed shut ({lit})"
        else:
            assert not any(lit), f"{facing}: {combo} opened the vault ({lit})"


@pytest.mark.parametrize("facing", FACINGS)
def test_each_pull_lights_its_OWN_lamp(facing):
    """The per-input feedback, without which three levers in a dark room are three levers in a
    dark room. It is also the check that catches two feeds shorted together, which would light
    both lamps off one pull and read as a wiring fault nobody could see."""
    w, _f, m, _p = _built("ossuary", facing=facing)
    spec = _spec(w)
    levers = [tuple(c) for c in m["levers"]]
    lamps = [tuple(c) for c in m["pull_lamps"]]
    for k in range(3):
        c = circuit.Circuit.from_cells(spec)
        c.set(levers[k], True)
        c.run(8)
        got = [c.powered(x) for x in lamps]
        assert got == [i == k for i in range(3)], f"{facing}: pull {k} lit {got}"


def test_letting_one_pull_go_shuts_the_vault_again():
    """IT IS COMBINATIONAL AND IT HAS NO MEMORY, which is the difference between this and the
    manor's monostables and the reason the zone now has one of each. A latch here would be a vault
    that opens once and stays open for ever, which is a prize counter with the door taken off."""
    w, _f, m, _p = _built("ossuary")
    c = circuit.Circuit.from_cells(_spec(w))
    levers = [tuple(x) for x in m["levers"]]
    doors = [tuple(x) for x in m["doors"]]
    for lv in levers:
        c.set(lv, True)
    c.run(16)
    assert all(c.powered(d) for d in doors), "all three up and the doors did not open"
    c.set(levers[1], False)
    c.run(16)
    assert not any(c.powered(d) for d in doors), "a pull was let go and the vault stayed open"


def test_BOTH_vault_doors_are_driven():
    """Fed at one column only, the second door is a door nothing drives - legal, supported,
    affordable, and shut for ever behind a vault that reports itself open."""
    w, _f, m, _p = _built("ossuary")
    assert len(m["doors"]) == 2
    c = circuit.Circuit.from_cells(_spec(w))
    for lv in m["levers"]:
        c.set(tuple(lv), True)
    c.run(16)
    for d in m["doors"]:
        assert c.powered(tuple(d)), f"the door at {d} is not driven by anything"


def test_the_gates_keep_clear_rows_are_actually_clear():
    """**THE ONE WAY AN AND GATE GOES WRONG SILENTLY.** `and_gate` returns `keep_clear` precisely
    because the odd perpendicular rows between its input supports must stay empty: anything
    powered there powers two inverters at once and the gate becomes an OR. It is asserted against
    the BUILT world rather than against the module, because what matters is that the ossuary's own
    walls, floor slab, route and dressing did not land in them."""
    w, f, m, _p = _built("ossuary")
    gate = and_gate(f.at(2, 9, 2), facing=H._ax(f)["back"], side=H._ax(f)["ip"], inputs=3)
    for cell in gate["keep_clear"]:
        assert not w.has(*cell), \
            f"{w.name(*cell)!r} stands in a keep-clear cell at {cell} - the AND is now an OR"


@pytest.mark.parametrize("facing", FACINGS)
def test_you_can_walk_into_the_ossuary_and_reach_all_three_pulls(facing):
    """A puzzle behind a wall is a wall. The flood starts on the pad OUTSIDE the doorway, so the
    door itself is part of what is being tested."""
    w, f, m, _p = _built("ossuary", facing=facing)
    got = HW.reachable(w, f.at(m["width"] // 2, -2, 1), floor=40)
    assert HW.near(got, m["entry_at"], 0), f"{facing}: you cannot get in the door"
    for k, lv in enumerate(m["levers"]):
        assert HW.near(got, lv, 1), f"{facing}: pull {k} cannot be reached"
    assert not _headroom(w, got), f"{facing}: the ossuary's walk has cells with no headroom"


def test_the_ossuary_chamber_is_a_room_and_not_a_crawlspace():
    """Three clear courses is a room; two is a slot the walk correctly refuses to enter, and a
    chamber that fails this looks exactly like a doorway that does not connect."""
    w, f, m, _p = _built("ossuary")
    got = HW.walk_from(w, f.at(m["width"] // 2, -2, 1))
    inside = [c for c in got if _ij(f, c)[1] >= 1]
    assert len(inside) >= 40, f"the chamber is only {len(inside)} cells of walkable floor"


def test_a_visitor_cannot_walk_into_the_machine_room():
    """THE SERVICE VOID IS BEHIND THE BACK WALL AND MUST STAY THERE. A gap in that wall is not a
    placement problem, a collision or a currency error - it is a player standing in the gate,
    breaking a torch, and a puzzle that never opens again."""
    w, f, m, _p = _built("ossuary")
    got = HW.walk_from(w, f.at(m["width"] // 2, -2, 1))
    # ...INSIDE THE FOOTPRINT ONLY. Written as "anything past the back wall" it swept in 162 cells
    # of the pad round the outside of the building, which is a path and not a machine room - the
    # same shape of mistake as reserving a design's bounding box instead of its cells.
    void = [c for c in got
            if 1 <= _ij(f, c)[0] <= m["width"] - 2
            and 8 <= _ij(f, c)[1] <= m["depth"] - 2
            and 1 <= _ij(f, c)[2] <= m["height"]]
    assert not void, f"{len(void)} cells of the service void are walkable, e.g. {void[:3]}"


def test_the_prize_is_BEHIND_the_doors():
    """A reward you can take without solving the puzzle is not a reward. Every barrel must lie on
    the far side of the door plane from the chamber."""
    w, f, m, _p = _built("ossuary")
    assert m["prizes"] >= 2, "the vault holds nothing to win"
    doors_d = {_ij(f, tuple(d))[1] for d in m["doors"]}
    barrels = [c for c, (n, _p2) in w.cells.items() if n == "barrel"]
    assert barrels, "no barrel was placed"
    for b in barrels:
        assert _ij(f, b)[1] > max(doors_d), f"a prize barrel at {b} is in front of the doors"


def test_the_ossuary_names_itself_and_says_how_to_play():
    """A game nobody can work out how to play is an empty structure - and `_sign` refuses a column
    with an opening in it, so an unnamed build is one that placed its signs on the doorway."""
    _w, _f, m, _p = _built("ossuary")
    assert m["signs"] >= 3, f"the ossuary places only {m['signs']} signs"


# ------------------------------------------------------------------ the zone

def test_the_hollow_is_no_longer_three_buttons():
    """**THE NUMBER THE WHOLE COMPLAINT RESTS ON.** The quarter contained three buttons and three
    sculk sensors against 215 cells of wire, and it read as an abandoned town. This counts what a
    visitor can actually TOUCH across the kinds this module owns, and it is a floor rather than a
    target: a future pass that quietly drops a set piece to simplify something fails here."""
    touchable = 0
    for kind in ("manor", "seance", "ossuary"):
        _w, _f, m, _p = _built(kind)
        touchable += len(m.get("inputs", []))
    assert touchable >= 7, f"the Hollow's own buildings offer {touchable} things to touch"


def test_every_input_and_output_recorded_in_a_sidecar_is_a_real_block():
    """A sidecar that names a cell nothing was placed in is a contract about a machine that does
    not exist - and every tool downstream of it, `/cscan check` included, believes it."""
    for kind in ("manor", "seance", "ossuary"):
        w, _f, m, _p = _built(kind)
        for role in ("inputs", "outputs"):
            for cell in m.get(role, []):
                assert w.has(*cell), f"{kind}: {role} names {cell}, where nothing was placed"


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


@pytest.mark.parametrize("facing", FACINGS)
def test_nothing_added_here_floats(facing):
    """6-connectivity, for the two kinds this file touched. A machine's own floor course, a lamp
    hung over a lever and a barrel on a shelf are all cells placed one at a time into open air,
    which is exactly how the clock tower shipped three floating lanterns."""
    for kind in ("manor", "ossuary"):
        w, _f, _m, _p = _built(kind, facing=facing)
        assert _components(w) == [len(w.cells)], f"{kind}/{facing} is in pieces"


@pytest.mark.parametrize("kind", ("manor", "ossuary"))
def test_the_new_machinery_has_nothing_suspicious_in_it(kind):
    """The static inspection, over the finished build. It is calibrated against four outside
    contraptions that demonstrably work and returns one informational line on each of them, so a
    real finding here is a real finding: dust that dies before its end, a comparator reading
    nothing, a repeater driving air."""
    c = H.build({**H.HOLLOW, "at": [0, 64, 0], "kind": kind, "land": "hollow", "facing": "east"})
    findings = circuit.inspect(c.to_model(), (0, 0, 0))
    real = [x for x in findings if "quasi-connectivity" not in str(x).lower()]
    assert not real, f"{kind}: {real[:5]}"
