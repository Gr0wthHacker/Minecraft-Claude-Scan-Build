"""NO OPEN WIRING, ANYWHERE. The contract, asserted rather than eyeballed.

Jack, on the shipped park: *"we need redstone to be covered, we shouldnt have open ended visible
redstone to players it breaks the experience"*. Measured before this file existed, the park's
machines showed **about 900 cells** of dust, repeaters, comparators and torches lying on open
ground - and every one of them passed the audit, the bill of materials, the circuit inspection and
the census, because not one of those asks what a player can SEE.

THE RULE, and there is no softer version of it:

    for every machine kind, in every facing and every land, NO `redstone_wire`, `repeater`,
    `comparator` or `redstone_torch` has a face on the outside surface.

`circuit.visible_redstone` is the measurement and `gen/conceal.conceal` is the pass that satisfies
it; both read `circuit.visible_in`, so the thing that hides the wiring and the thing that grades it
cannot drift - the same one-source rule `proportions.measure` and `rubric.score` share, and the
absence of which is exactly how the `circuits.window` bug survived (the simulator agreed with the
broken build).

**AND COVERING IT MUST NOT BREAK THE GAME OR THE FLOOR.** Two of these tests exist only because
both of those happened: a machine pit that ate four cells of its own play floor, and a pass that
capped five casino machines' comparator inputs and turned all five off while every block in them
stayed legal, supported and affordable. So the suite asserts the walk and the wiring as well as
the cover.
"""
from __future__ import annotations

import collections

import pytest

from mcbuild import audit, blocks, circuit
from mcbuild.circuit import Circuit
from mcbuild.gen import arcade, casino, conceal, frontiertown, hollowmanor, spectacle, ticketing
from mcbuild.gen.vertical import World

FACINGS = ("east", "west", "north", "south")

# Every generator that places a redstone component, with the land parameter each one wants.
MACHINES = [
    ("arcade", arcade, "midway"),
    ("casino", casino, None),
    ("ticketing", ticketing, "midway"),
    ("spectacle", spectacle, "midway"),
    ("frontiertown", frontiertown, "frontier"),
    ("hollowmanor", hollowmanor, "hollow"),
]

CASES = [(mod_name, mod, land, kind)
         for mod_name, mod, land in MACHINES
         for kind in sorted(mod.BUILDERS)]


def _build(mod, land, kind, facing="east", **cfg):
    p = {"at": [0, 64, 0], "kind": kind, "facing": facing, **cfg}
    if land:
        p["land"] = land
    return mod.build(p)


def _model(c):
    return c.to_model() if hasattr(c, "to_model") else c


# --------------------------------------------------------------------------- the measurement
#
# TESTED BEFORE ANYTHING IS BUILT ON IT. `circuits.climb` was written and used in the same breath,
# failed silently three times inside the casino, and gave up its bug the moment it was exercised
# alone; a checker nobody has exercised alone is the same bet with more riding on it.


def test_a_bare_run_of_dust_is_visible():
    cells = {(0, 0, 0): "stone", (0, 1, 0): "redstone_wire",
             (1, 0, 0): "stone", (1, 1, 0): "redstone_wire"}
    assert len(circuit.visible_in(cells)) == 2


def test_a_run_under_a_solid_floor_is_not():
    cells = {}
    for x in range(-1, 3):
        for z in (-1, 0, 1):
            cells[(x, 0, z)] = "stone"          # the deck it stands on
            cells[(x, 2, z)] = "stone"          # the floor over it
    for x in range(-1, 3):
        cells[(x, 1, -1)] = "stone"
        cells[(x, 1, 1)] = "stone"
    cells[(-1, 1, 0)] = "stone"
    cells[(2, 1, 0)] = "stone"
    cells[(0, 1, 0)] = "redstone_wire"
    cells[(1, 1, 0)] = "redstone_wire"
    assert circuit.visible_in(cells) == []


def test_glass_does_not_hide_anything():
    """**A FULL CUBE IS NOT THE SAME QUESTION AS AN OPAQUE ONE.** Glass is a full cube and you look
    straight through it, so a shape test would pass a machine displayed in a vitrine."""
    cells = {(0, 0, 0): "stone", (0, 1, 0): "redstone_wire"}
    for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0)):
        cells[(d[0], 1 + d[1], d[2])] = "glass"
    assert len(circuit.visible_in(cells)) == 1
    for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0)):
        cells[(d[0], 1 + d[1], d[2])] = "stone"
    assert circuit.visible_in(cells) == []


def test_a_hopper_is_not_a_window_onto_the_comparator_that_reads_it():
    """A hopper is not a full cube and you cannot see past one either - it is full width from
    every horizontal direction and the only opening is the funnel in its own top. Counted as a
    window, the plinko board's five input hoppers made its whole machine room visible, which is a
    rule nobody could build to."""
    cells = {(0, 0, 0): "stone", (0, 1, 0): "comparator", (1, 1, 0): "hopper",
             (0, 2, 0): "stone", (0, 1, 1): "stone", (0, 1, -1): "stone", (-1, 1, 0): "stone"}
    assert circuit.visible_in(cells) == []


def test_a_button_does_not_expose_the_run_it_starts():
    """The same rule from the other side, and the one that makes the contract satisfiable at all:
    an input has to TOUCH the wiring, so if you could see past a button every machine would be
    open by construction."""
    cells = {(0, 0, 0): "stone", (0, 1, 0): "redstone_wire", (0, 2, 0): "stone",
             (1, 1, 0): "stone_button", (-1, 1, 0): "stone",
             (0, 1, 1): "stone", (0, 1, -1): "stone"}
    assert circuit.visible_in(cells) == []


# --------------------------------------------------------------------------- the contract


class _NoCover:
    """Build the SAME design without the concealment pass, by neutering it for one call.

    The generators call `conceal.conceal` through the module, so swapping that one name gives an
    honest before-and-after of the whole `build` - including its palette, its skinning and its
    footprint report - rather than a hand-rolled config that drifts from the real one.
    """

    def __enter__(self):
        self.real = conceal.conceal
        conceal.conceal = lambda *a, **k: {"placed": 0, "swapped": 0, "rounds": 0, "left": []}
        return self

    def __exit__(self, *exc):
        conceal.conceal = self.real
        return False


@pytest.mark.parametrize("mod_name,mod,land,kind", CASES,
                         ids=[f"{m}-{k}" for m, _mod, _l, k in CASES])
def test_no_machine_shows_a_player_any_wiring(mod_name, mod, land, kind):
    """THE HEADLINE. Not "mostly hidden", not "hidden from the front": zero, in every facing."""
    for facing in FACINGS:
        c = _build(mod, land, kind, facing)
        left = circuit.visible_redstone(_model(c), c.world_origin)
        assert left == [], (
            f"{mod_name}/{kind}/{facing}: {len(left)} visible - "
            f"{collections.Counter(n for _p, n in left).most_common()} e.g. {left[0]}")


@pytest.mark.parametrize("land", ["midway", "frontier", "hollow"])
@pytest.mark.parametrize("kind", sorted(arcade.BUILDERS))
def test_the_arcade_is_covered_in_every_land(kind, land):
    """A land changes every material in the build, and `blocks.is_full_cube` is what decides
    whether a lid is a lid. A casing that works in wool and leaks in cobble is a casing nobody
    checked."""
    c = _build(arcade, land, kind)
    assert circuit.visible_redstone(_model(c), c.world_origin) == []


@pytest.mark.parametrize("mod_name,mod,land,kind", CASES,
                         ids=[f"{m}-{k}" for m, _mod, _l, k in CASES])
def test_covering_it_leaves_one_connected_piece_with_no_placement_problems(
        mod_name, mod, land, kind):
    """**A COMPONENT COUNT IS THE ONLY CHECK THAT SEES A FLOATING LID.** The first torch chimney
    roofed its own air gap one course up, where the lid touches the four walls only DIAGONALLY -
    and the safe shipped in five pieces, one building and four single blocks hanging over its
    torches, with zero placement problems reported.

    Measured BOTH SIDES of the pass rather than against 1, because `casino/prize_wall` is five
    separate units by design ("furniture rather than rooms - they line a corridor and must not each
    be boxed in") and asserting 1 there would be asserting something this pass is not responsible
    for. What it IS responsible for is not making the count worse, and a lid hanging over a torch
    makes it worse whatever the design started at."""
    with _NoCover():
        bare = _build(mod, land, kind)
    over = _build(mod, land, kind)
    before = audit.audit(_model(bare))
    after = audit.audit(_model(over))
    assert not after.problems, f"{mod_name}/{kind}: {after.problems[:3]}"
    assert len(after.components) <= len(before.components), (
        f"{mod_name}/{kind}: the cover left {len(after.components)} pieces where the bare build "
        f"had {len(before.components)} - {after.components}")


# --------------------------------------------------------------------------- and it still works


def _stand_set(names):
    """Every cell a player could stand in: solid under the feet, two clear courses for the body."""
    out = set()
    for p, name in names.items():
        if not blocks.is_full_cube(name):
            continue
        a = (p[0], p[1] + 1, p[2])
        b = (p[0], p[1] + 2, p[2])
        if a in names and blocks.is_full_cube(names[a]):
            continue
        if b in names and blocks.is_full_cube(names[b]):
            continue
        out.add(a)
    return out


def _walk(stand, starts):
    seen = {s for s in starts if s in stand}
    queue = collections.deque(seen)
    while queue:
        x, y, z = queue.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                q = (x + dx, y + dy, z + dz)
                if q in stand and q not in seen:
                    seen.add(q)
                    queue.append(q)
    return seen


def _reached_model(model, origin, inputs):
    """Which of these cells a player can get within arm's reach of, walking in from outside."""
    names = circuit._cells_of(model, origin)
    stand = _stand_set(names)
    xs = [p[0] for p in names]
    zs = [p[2] for p in names]
    ys = [p[1] for p in names]
    edge = [p for p in stand
            if p[0] in (min(xs), max(xs)) or p[2] in (min(zs), max(zs)) or p[1] >= max(ys) - 1]
    walked = _walk(stand, edge)
    out = set()
    for c in inputs:
        c = tuple(int(v) for v in c)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1, 2):
                for dz in (-1, 0, 1):
                    if (c[0] + dx, c[1] + dy, c[2] + dz) in walked:
                        out.add(c)
    return out


@pytest.mark.parametrize("mod_name,mod,land,kind", CASES,
                         ids=[f"{m}-{k}" for m, _mod, _l, k in CASES])
def test_covering_the_wiring_never_walls_a_player_away_from_an_input(mod_name, mod, land, kind):
    """**A MACHINE PIT COSTS A FLOOR**, and this repo has already shipped one that ate four cells
    of its own play floor. The pass adds blocks and never removes one, so it cannot open a hole -
    what it CAN do is stand a lid where a player was going to walk. Measured both sides of the
    pass: an input you could reach before must still be reachable after.

    Targets and sensors meant to be shot or heard from a distance are unreachable both times,
    which is why this is a NO-REGRESSION test rather than an absolute one."""
    with _NoCover():
        bare = _build(mod, land, kind)
    over = _build(mod, land, kind)
    ins = bare.meta.get("inputs") or []
    if not ins:
        pytest.skip("nothing a player touches")
    before = _reached_model(_model(bare), bare.world_origin, ins)
    after = _reached_model(_model(over), over.world_origin, ins)
    assert before <= after, f"{mod_name}/{kind}: covered up {sorted(before - after)}"


@pytest.mark.parametrize("mod_name,mod,land,kind", CASES,
                         ids=[f"{m}-{k}" for m, _mod, _l, k in CASES])
def test_covering_the_wiring_does_not_change_what_the_circuit_does(mod_name, mod, land, kind):
    """**A LID IS A CONDUCTOR.** Capped without care, five casino machines stopped rolling in one
    pass - a block in a comparator's side input reads whatever dust touches it, where the empty
    cell it replaced read nothing at all. Every block still legal, supported and affordable, and
    not one of them rolled.

    So the whole machine is simulated with and without the cover and every component's settled
    state is compared. This is the assertion the per-kind contract tests cannot make: they know
    what ONE machine promises, and this knows what all of them do."""
    with _NoCover():
        bare = _build(mod, land, kind)
    over = _build(mod, land, kind)

    def trace(c, ticks=40):
        """**A TRACE, NOT A SETTLED STATE.** Half the machines here are pulses and clocks: a
        comparison taken once at tick 24 misses a shot that fires two ticks early, a door that
        flicks open on load and a chase that runs in the wrong order, all of which are exactly
        what a stray conductor does to a machine."""
        s = Circuit.of(_model(c), c.world_origin)
        watched = sorted(q for q, cell in s.cells.items()
                         if cell.name in ("repeater", "comparator", "redstone_torch",
                                          "redstone_wall_torch", "redstone_lamp", "iron_door",
                                          "dropper", "dispenser", "piston", "sticky_piston",
                                          "bell", "note_block"))
        rows = []
        for _ in range(ticks):
            s.step()
            rows.append(tuple(s.powered(q) for q in watched))
        return watched, rows, dict(s.power)

    bare_cells, bare_rows, bare_wire = trace(bare)
    over_cells, over_rows, over_wire = trace(over)
    assert bare_cells == over_cells, f"{mod_name}/{kind}: the cover added or moved a component"
    for t, (a, b) in enumerate(zip(bare_rows, over_rows)):
        if a != b:
            i = next(k for k in range(len(a)) if a[k] != b[k])
            raise AssertionError(
                f"{mod_name}/{kind}: at tick {t} the cover changed {bare_cells[i]} "
                f"({bare_rows[t][i]} -> {over_rows[t][i]})")
    hot = [q for q, v in bare_wire.items() if v != over_wire.get(q, v)]
    assert not hot, f"{mod_name}/{kind}: the cover changed {len(hot)} wire level(s), e.g. {hot[0]}"


# --------------------------------------------------------------------------- the pass's own rules


def _world(cells):
    w = World()
    for pos, spec in cells.items():
        name = spec.split("[")[0]
        props = {}
        if "[" in spec:
            for part in spec[spec.index("[") + 1:-1].split(","):
                k, _, v = part.partition("=")
                props[k.strip()] = v.strip()
        w.put(pos[0], pos[1], pos[2], name, **props)
    return w


def test_it_caps_an_exposed_run():
    w = _world({(0, 0, 0): "stone", (0, 1, 0): "redstone_wire",
                (1, 0, 0): "stone", (1, 1, 0): "redstone_wire"})
    out = conceal.conceal(w, "stone")
    assert out["left"] == []
    assert out["placed"] > 0


def test_it_never_caps_a_hoppers_mouth():
    """A hopper takes the ball, the coin, the item that IS the input. A lid there turns the
    machine off in the only way a player can see and cannot fix."""
    w = _world({(0, 0, 0): "stone", (0, 1, 0): "hopper[facing=down]",
                (1, 1, 0): "comparator[facing=east]", (1, 0, 0): "stone"})
    conceal.conceal(w, "stone")
    assert not w.has(0, 2, 0), "the funnel was capped"


def test_it_never_puts_a_block_directly_over_a_lit_torch():
    """A torch strongly powers the block above it, so a lid there is not a lid - it is a new 15 in
    the middle of the machine. The chimney seals the gap from the sides instead."""
    w = _world({(0, 0, 0): "stone", (0, 1, 0): "redstone_torch[lit=true]"})
    out = conceal.conceal(w, "stone")
    assert not w.has(0, 2, 0), "a lid was dropped straight onto the torch"
    assert out["left"] == [], "and the torch was left visible instead"


def test_no_lid_ever_lands_live_beside_a_hopper():
    """**A HOPPER BESIDE A POWERED BLOCK IS A LOCKED HOPPER, AND THE SIMULATOR CANNOT SEE IT.**
    `circuit` has no entities, so nothing in the pipeline would report a ticket slot that has
    stopped taking tickets - the machine would test perfectly and refuse every ticket in game.
    `ticketing._torch_pair` designed this out by hand and said so; a lid is exactly the thing that
    would put it back.

    Asserted over every real machine rather than a fixture, because the failure is geometric and
    the geometry is the generators'."""
    for mod_name, mod, land, kind in CASES:
        c = _build(mod, land, kind)
        s = Circuit.of(_model(c), c.world_origin)
        s.run(1)
        for pos, cell in s.cells.items():
            if cell.name != "hopper":
                continue
            for d in circuit.DIRS.values():
                nb = (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])
                if not s.opaque(nb):
                    continue
                assert s._block_power(nb, s._last_src) == 0, (
                    f"{mod_name}/{kind}: the block at {nb} beside the hopper at {pos} is powered "
                    f"at rest - that hopper is locked and no simulation here would notice")


def test_it_never_puts_a_block_where_a_comparator_reads_live_power():
    """The five-machines-off bug, pinned. A comparator reads its back and BOTH sides; a lid in one
    of those cells delivers whatever dust touches it."""
    cells = {(0, 0, 0): "stone", (0, 1, 0): "comparator[facing=east]",
             (-1, 0, 0): "stone", (-1, 1, 0): "hopper[facing=down]",
             (1, 0, 0): "stone", (1, 1, 0): "redstone_wire",
             (0, 0, 2): "stone", (0, 1, 2): "redstone_wire",
             (1, 0, 2): "stone", (1, 1, 2): "redstone_wire"}
    w = _world(cells)
    conceal.conceal(w, "stone")
    assert not w.has(0, 1, 1), "a lid went into the comparator's own side input"


def test_a_lid_beside_a_repeater_is_allowed_because_a_repeater_reads_only_its_back():
    """The mirror of the rule above, and it is worth a test of its own: refusing every cell beside
    every timing part cost six repeaters their cover in the ticket gates for a leak that cannot
    happen. A repeater's sides are for LOCKING and a lock comes from another repeater or
    comparator, never from a plain block."""
    w = _world({(0, 0, 0): "stone", (0, 1, 0): "repeater[facing=east]",
                (-1, 0, 0): "stone", (-1, 1, 0): "redstone_wire",
                (1, 0, 0): "stone", (1, 1, 0): "redstone_wire",
                (0, 0, 1): "stone", (0, 0, -1): "stone"})
    conceal.conceal(w, "stone")
    assert w.has(0, 1, 1) and w.has(0, 1, -1), "the repeater's sides were left open"
    assert not w.has(-1, 1, 0) or w.name(-1, 1, 0) == "redstone_wire"


def test_it_is_a_fixpoint_and_says_how_many_rounds_it_took():
    w = _world({(x, 0, 0): "stone" for x in range(6)}
               | {(x, 1, 0): "redstone_wire" for x in range(6)})
    out = conceal.conceal(w, "stone")
    assert out["left"] == []
    assert out["rounds"] >= 1
    again = conceal.conceal(w, "stone")
    assert again["placed"] == 0, "a second pass over a covered machine should place nothing"


# --------------------------------------------------------------------------- the one command


def test_the_audit_tool_reports_visible_redstone_per_design(tmp_path):
    """DELIVERABLE 2: one command answers it for the whole folder.

    `tools/redstone_audit.py` already answered "is the wiring sound" and "can a player press it and
    see it happen". It could not answer the question Jack actually asked, so a design shipped with
    its guts on the grass looked identical to one that did not. Exercised here on a real design
    with the cover taken off, so the assertion is about the TOOL rather than about today's
    generators - if concealment regressed, the per-kind tests catch it; if the tool stopped
    looking, only this does."""
    import json
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "tools"))
    import redstone_audit

    with _NoCover():
        bare = _build(arcade, "midway", "plinko")
    covered = _build(arcade, "midway", "plinko")

    def report(c):
        side = {"kind": "arcade/plinko", "origin": dict(zip("xyz", c.world_origin)),
                "inputs": c.meta.get("inputs", []), "outputs": c.meta.get("outputs", []),
                "contract": c.meta.get("contract", "")}
        return redstone_audit.Report("Plinko", _model(c), json.loads(json.dumps(side)))

    exposed = report(bare)
    assert exposed.visible, "the tool saw nothing on a design with its cover off"
    assert exposed.exposed["redstone_wire"] > 0
    assert "EXPOSED" in redstone_audit._row(exposed)

    clean = report(covered)
    assert clean.visible == [], "the tool reported open wiring on a covered design"
    assert "EXPOSED" not in redstone_audit._row(clean)
