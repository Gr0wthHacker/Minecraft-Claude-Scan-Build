"""The frontier zone does things, and every one of them is proven rather than described.

The zone shipped as a western town whose honest answer to *what can a player DO here* was "look at
it": a seven-cell dead-end adit under a headframe, five signed shopfronts opening onto empty boxes,
a saloon with a bar sign and no bar, and a log flume that carried a rider perfectly while draining
its entire channel onto the plot. That last one is the shape of every failure this repo keeps
writing rules about - it passed the audit, the bill of materials, every render, and the generator's
own `fluids.carries` self-check, because `carries` asks whether the PATH is wet and nothing at all
about whether the water stays in the trough.

So the three subsystems are each held to their own simulator, from outside the generator:

    water        `fluids.carries` for the ride, `fluids.escapes` for containment - BOTH
    redstone     `circuit.Circuit`, dark with an empty poke and firing with a stocked one
    walking      `walk.reachable`, with the movement model stated in `mcbuild/walk.py`

and two of the tests here are deliberately about the tests: `test_the_leak_check_can_actually_fail`
puts the flume's uncapped head back and demands the check catch it, and `test_the_walk_model_is_not
_vacuous` walks a sealed box. A check that cannot fail is worse than no check, because it is
counted - and this suite has shipped a vacuous one before.
"""
from __future__ import annotations

import collections
import json
import os
from collections import deque

import numpy as np
import pytest

from mcbuild import blocks, circuit, fluids, nbt, palette, walk
from mcbuild import scan as scan_mod
from mcbuild.gen import coaster, frontiertown as ft
from mcbuild.gen.park import LANDS, SIGN_WIDTH
from mcbuild.gen.vertical import World

OUT = "out"
LANDS_ALL = sorted(LANDS)


# --------------------------------------------------------------------------------- fixtures

def _build(kind, **kw):
    """The raw World and meta, in WORLD coordinates - the canvas is sized to its own content and
    shifts between builds, so anything compared against it lines up against nothing."""
    p = {**ft.FRONTIER, "kind": kind, "at": [0, 100, 0], "facing": "east", "land": "frontier",
         **kw}
    w = World()
    meta = ft.BUILDERS[kind](w, p, None)
    return w, meta, p


def _flume(**kw):
    p = {**coaster.COASTER, "kind": "flume", "at": [0, 100, 0], "facing": "east",
         "land": "frontier", "flume_span": 29, "flume_top": 20, "pool": 4, **kw}
    w = World()
    meta = coaster.BUILDERS["flume"](w, p, None)
    return w, meta, p


def _names(w):
    return {pos: name for pos, (name, _pr) in w.cells.items()}


def _sources(w):
    return [pos for pos, (name, pr) in w.cells.items()
            if name == "water" and pr.get("level", "0") == "0"]


def _components(w):
    cells = set(w.cells)
    seen, sizes = set(), []
    for start in cells:
        if start in seen:
            continue
        q, n = deque([start]), 0
        seen.add(start)
        while q:
            (x, y, z) = q.popleft()
            n += 1
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                t = (x + d[0], y + d[1], z + d[2])
                if t in cells and t not in seen:
                    seen.add(t)
                    q.append(t)
        sizes.append(n)
    return sorted(sizes, reverse=True)


def _design(name):
    """A shipped design as {(x, y, z): (name, props)} in world coordinates, plus its sidecar."""
    path = os.path.join(OUT, f"{name}.litematic")
    if not os.path.exists(path):
        pytest.skip(f"{name} has not been shipped")
    sc = scan_mod.load(path)
    m = sc.model
    ox, oy, oz = sc.origin
    names = [n.split(":")[-1] for n in m.names]
    props = [nbt.state_props(e) for e in m.palette]
    cells = {}
    for (y, z, x) in np.argwhere(m.ids > 0):
        i = int(m.ids[y, z, x])
        if names[i] == "air":
            continue
        cells[(ox + int(x), oy + int(y), oz + int(z))] = (names[i], props[i])
    with open(os.path.join(OUT, f"{name}.scan.json"), encoding="utf-8") as fh:
        side = json.load(fh)
    return cells, side


# ------------------------------------------------------------------------ the flume's water

def test_the_flume_still_carries_a_rider():
    """The original contract, unchanged: every path cell wet AND MOVING, never a source."""
    w, meta, _p = _flume()
    rep = fluids.carries(_names(w), [tuple(c) for c in meta["path"]],
                         [tuple(c) for c in meta["sources"]])
    assert rep["dry"] == 0 and rep["still"] == 0
    assert rep["carries"]


def test_the_flume_water_stays_inside_the_flume():
    """THE BUG THIS FILE EXISTS FOR. The shipped ride reached 199,959 cells and Y-1908."""
    w, meta, _p = _flume()
    out = fluids.escapes(_names(w), _sources(w), [tuple(c) for c in meta["basin"]])
    assert out == [], f"{len(out)} cell(s) escaped, first at {out[0] if out else None}"


@pytest.mark.parametrize("facing", ["east", "north", "west", "south"])
@pytest.mark.parametrize("size", [
    {"flume_span": 29, "flume_top": 20, "pool": 4},
    {"flume_span": 44, "flume_top": 30},
    {"flume_span": 36, "flume_top": 24, "pool": 5},
])
def test_the_flume_holds_its_water_at_every_facing_and_size(facing, size):
    """A containment bug that only appears on one facing is the corner-diagonal bug wearing a hat:
    `_wall_offs` returns different offsets per corner, so every rotation is a different geometry."""
    w, meta, _p = _flume(facing=facing, **size)
    assert fluids.escapes(_names(w), _sources(w), [tuple(c) for c in meta["basin"]]) == []


def test_the_leak_check_can_actually_fail(monkeypatch):
    """TAKE THE SEAL OUT AND THE CHECK MUST CATCH IT.

    Every assertion above passes on a correct build, which is exactly what the shipped flume's own
    self-check did. The only way to know a containment test means anything is to break containment
    and watch it fail. `_shell` is the load-bearing half - it is what fills the corner diagonals
    the walls cannot reach - and stubbing it puts the ride back in the state it shipped in.

    `_cap` is deliberately NOT the one stubbed here, and that is worth writing down: stubbing it
    changes nothing, because `_shell` walls the open head too. The cap survives as the visible
    five-wide end wall a trough should have, not as a load-bearing seal, and pretending otherwise
    in a test would be inventing a second guard nobody is really relying on.
    """
    monkeypatch.setattr(coaster, "_shell", lambda *a, **kw: 0)
    with pytest.raises(ValueError, match="leaks"):
        _flume()


def test_the_flume_has_a_bed_under_every_water_cell():
    w, meta, _p = _flume()
    bad = fluids.unenclosed(_names(w), allow=[tuple(c) for c in meta["basin"]])
    assert bad == [], bad[:3]


def test_the_shipped_frontier_zone_holds_all_of_its_water():
    """The whole zone, as it will be placed, against the flume's own recorded basin.

    Measured before this work: `Park_Left Complete` held ten water cells with an open horizontal
    face, and the flood from its sources left the design entirely. The other two zones held none,
    which is the tell that this was one ride's geometry and not a park-wide palette mistake.
    """
    cells, _side = _design("Park_Left Complete")
    plain = {p: n for p, (n, _pr) in cells.items()}
    src = [p for p, (n, pr) in cells.items()
           if n == "water" and pr.get("level", "0") == "0"]
    assert src, "the frontier zone has no water at all - has the flume been dropped?"

    envelope = set(p for p, (n, _pr) in cells.items() if n == "water")
    _fl, fside = _design("Log Flume")
    envelope |= {tuple(c) for c in fside.get("basin", [])}
    _sl, sside = (None, {})
    if os.path.exists(os.path.join(OUT, "Gold Sluice.scan.json")):
        _sl, sside = _design("Gold Sluice")
        envelope |= {tuple(c) for c in sside.get("basin", [])}

    out = fluids.escapes(plain, src, envelope)
    assert out == [], f"{len(out)} cell(s) of the zone's water end up somewhere no design wanted " \
                      f"them, first at {out[0] if out else None}"


# ------------------------------------------------------------------------ the mine walkthrough

def test_the_mine_is_a_walkthrough_not_a_dead_end():
    """Street to adit to shaft to the far working to the way out - every leg, on foot."""
    w, meta, _p = _build("minehead")
    cells = _names(w)
    reach = walk.reachable(cells, tuple(meta["adit_mouth"]))
    for leg in ("shaft_head", "gallery_far", "way_out"):
        assert tuple(meta[leg]) in reach, f"{leg} at {meta[leg]} is not walkable from the street"


def test_the_mine_goes_down_far_enough_to_be_a_descent():
    _w, meta, _p = _build("minehead")
    assert meta["depth_below"] >= 8, "a descent you can see the bottom of from the top is a step"
    assert meta["hoist_shaft"] >= 8 and meta["escape_shaft"] >= 8


def test_the_mine_has_worked_faces_and_light_in_the_workings():
    _w, meta, _p = _build("minehead")
    assert meta["veins"] >= 12, "a drift with no ore in it is a corridor"
    assert meta["lamps"] >= 4, "an unlit drift is a hole"
    assert meta["sets"] >= 2, "timbering is what says mine rather than tunnel"


def test_the_mine_can_be_switched_off_and_still_builds():
    """`workings: False` has to keep working, because the old shape is what is standing in world."""
    _w, meta, _p = _build("minehead", workings=False)
    assert meta["depth_below"] == 0
    assert "gallery" not in meta


@pytest.mark.parametrize("facing", ["east", "north", "west", "south"])
def test_the_mine_walk_holds_at_every_facing(facing):
    _w, meta, _p = _build("minehead", facing=facing)
    assert meta["walk_cells"] > 200


# ------------------------------------------------------------------------------- the sluice

def test_the_sluice_washes():
    _w, meta, _p = _build("sluice", width=13, depth=13)
    assert meta["flow"]["carries"], meta["flow"]
    assert meta["flow"]["still"] == 0, "a still launder is a puddle you throw things into"


@pytest.mark.parametrize("size", [(11, 11), (13, 13), (17, 12), (21, 17), (15, 25), (11, 30)])
@pytest.mark.parametrize("facing", ["east", "north", "west", "south"])
def test_the_sluice_holds_its_water_at_every_size(size, facing):
    """IT LEAKED AT FOUR SIZES OUT OF FIVE AND NOT AT THE ONE IT WAS BUILT AT.

    The wall used to be three courses over its OWN floor, so it fell with every step and water
    riding a course high ran over the top of the next one down. One hand-checked size found
    nothing; a sweep found it immediately - which is the whole argument for sweeping.
    """
    W, D = size
    w, meta, _p = _build("sluice", width=W, depth=D, facing=facing)
    out = fluids.escapes(_names(w), _sources(w), [tuple(c) for c in meta["basin"]])
    assert out == [], f"{len(out)} cell(s) escaped, first at {out[0] if out else None}"


@pytest.mark.parametrize("size", [(11, 11), (13, 13), (17, 12), (21, 17), (15, 25), (11, 30)])
def test_the_sluice_washes_at_every_size(size):
    W, D = size
    _w, meta, _p = _build("sluice", width=W, depth=D)
    assert meta["flow"]["carries"], meta["flow"]


def test_an_empty_poke_leaves_the_strike_detector_dark():
    """A detector that is always on is a decoration with a redstone bill."""
    w, meta, _p = _build("sluice", width=13, depth=13)
    sim = _sim(w)
    sim.run(12)
    assert not sim.powered(tuple(meta["piston"]))
    assert not sim.powered(tuple(meta["bell"]))


@pytest.mark.parametrize("level", [1, 3, 9, 15])
def test_a_stocked_poke_raises_the_gold_and_rings_the_bell(level):
    w, meta, _p = _build("sluice", width=13, depth=13)
    sim = _sim(w)
    sim.fill(tuple(meta["barrel"]), level)
    sim.run(12)
    assert sim.powered(tuple(meta["piston"])), "the gold block never comes up"
    assert sim.powered(tuple(meta["bell"])), "the bell never rings"


def _sim(w):
    spec = {pos: (name if not pr else
                  name + "[" + ",".join(f"{k}={v}" for k, v in sorted(pr.items())) + "]")
            for pos, (name, pr) in w.cells.items()}
    return circuit.Circuit.from_cells(spec)


def test_the_sluice_reports_what_it_has_not_proven():
    _w, meta, _p = _build("sluice", width=13, depth=13)
    assert meta["unverified"], "a machine with nothing unverified has not been thought about"
    assert any("ITEM" in u for u in meta["unverified"])


# -------------------------------------------------------------------------------- the saloon

def test_the_saloon_can_be_walked_into_and_upstairs():
    _w, meta, _p = _build("saloon", width=17, depth=12)
    assert meta["walk_cells"] > 200


def test_the_saloon_delivers_what_its_sign_promises():
    """`whiskey & beds` was over the door for months with neither behind it."""
    w, meta, _p = _build("saloon", width=17, depth=12)
    names = set(_names(w).values())
    assert "red_bed" in names, "the sign says beds"
    assert {"brewing_stand", "barrel", "cauldron"} <= names, "the sign says whiskey"
    assert "bell" in names, "something in the room has to make a noise"
    assert meta["beds"] >= 2 and meta["tables"] >= 2 and meta["stools"] >= 3


def test_the_saloon_has_no_expensive_instrument():
    """`note_block` AND `jukebox` are both expensive here - the second was assumed not to be."""
    w, _meta, _p = _build("saloon")
    names = set(_names(w).values())
    assert "note_block" not in names and "jukebox" not in names
    assert palette.tier("jukebox") == "expensive"       # pins the fact, not the memory


# ----------------------------------------------------------------------------- prospect row

def test_every_shop_can_be_walked_into_from_the_boardwalk():
    """The generator refuses to build otherwise; this exercises the same contract from outside."""
    w, meta, _p = _build("falsefront", shops=5)
    from mcbuild.gen.park import _Frame
    f = _Frame(_p)
    reach = walk.reachable(_names(w), f.at(meta["width"] // 2, -1, 0))
    assert len(reach) > 100


def test_every_shop_holds_the_tools_of_the_trade_on_its_sign():
    w, meta, _p = _build("falsefront", shops=8)
    names = list(_names(w).values())
    for trade in meta["trades"]:
        for tool in ft.TRADE_KIT[trade]:
            assert tool in names, f"the {trade} has no {tool}"
    assert meta["fitted"] >= 2 * len(meta["trades"])


def test_the_shop_fitout_can_be_switched_off():
    _w, meta, _p = _build("falsefront", shops=5, fitout=False)
    assert meta["fitted"] == 0


def test_every_trade_on_a_sign_has_a_kit_behind_the_counter():
    """A trade with no entry silently falls back to one barrel, which is a shop with a sign and
    nothing in it - the exact failure this whole pass exists to remove, reintroduced by a typo."""
    _w, meta, _p = _build("falsefront", shops=8)
    for trade in meta["trades"]:
        assert trade in ft.TRADE_KIT, f"{trade} has no kit"


# ------------------------------------------------------------------- the rides you board on foot

def test_the_runaway_mine_platform_can_be_reached_on_foot():
    """A boarding platform you cannot walk to is a ride nobody rides.

    Seeded on the design's own ground rather than in the void: this repo has shipped a coaster
    test that seeded outside the model and therefore asserted nothing at all.
    """
    cells, side = _design("Runaway Mine")
    plain = {p: n for p, (n, _pr) in cells.items()}
    board = tuple(side["boarding_at"])
    ground = [p for p in plain
              if walk.stands(plain, (p[0], p[1] + 1, p[2])) and p[1] == side["origin"]["y"] + 1]
    assert ground, "the design has no standable ground at all - the seed would be vacuous"
    reach = set()
    for g in ground[:40]:
        reach |= walk.reachable(plain, (g[0], g[1] + 1, g[2]))
        if board in reach:
            break
    assert board in reach, f"the boarding spot {board} is walled off from its own ride"


def test_the_mine_coasters_track_can_be_reached_on_foot():
    """A closed rail circuit whose station you cannot walk onto is a sculpture of a ride.

    `coaster` records no boarding coordinate, so this asks the honest general question instead:
    seeded on the design's own lowest standable ground, is any of the track walkable? An empty
    answer means the station is walled off from its own platform, which is exactly what a
    228-cell platform did here once.
    """
    cells, side = _design("Mine Coaster")
    plain = {p: n for p, (n, _pr) in cells.items()}
    rails = [p for p, n in plain.items()
             if n in ("rail", "powered_rail", "detector_rail", "activator_rail")]
    assert rails, "the coaster has no track"
    y0 = side["origin"]["y"]
    seeds = [p for p in plain if p[1] == y0 + 1 and walk.stands(plain, (p[0], p[1] + 1, p[2]))]
    assert seeds, "no standable ground at all - a seed here would be vacuous"
    reach = set()
    for g in seeds[:60]:
        reach |= walk.reachable(plain, (g[0], g[1] + 1, g[2]))
        if any(r in reach for r in rails):
            break
    assert [r for r in rails if r in reach], "none of the track can be walked to"


# ------------------------------------------------------------------- the usual gates, per kind

NEW_KINDS = ("sluice", "minehead", "saloon", "falsefront", "powderhouse")


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_each_kind_is_one_connected_piece(kind):
    w, _meta, _p = _build(kind)
    assert _components(w) == [len(w.cells)]


@pytest.mark.parametrize("kind", NEW_KINDS)
@pytest.mark.parametrize("land", LANDS_ALL)
def test_every_block_state_is_legal(kind, land):
    w, _meta, _p = _build(kind, land=land)
    bad = []
    for pos, (name, props) in w.cells.items():
        errs = blocks.validate(name, props)
        if errs:
            bad.append((pos, name, errs))
    assert bad == [], bad[:3]


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_nothing_is_currency_or_off_version(kind):
    """Dirt and grass are MONEY on this server, and the client is 26.2 while the server is 1.19."""
    w, _meta, _p = _build(kind)
    names = {n for n in _names(w).values()}
    assert not {n for n in names if not blocks.spendable(n)}
    assert not {n for n in names if not blocks.available(n)}


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_nothing_new_is_expensive(kind):
    w, _meta, _p = _build(kind)
    dear = sorted({n for n in _names(w).values() if palette.tier(n) == "expensive"})
    assert dear == [], dear


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_every_sign_is_on_a_block_and_fits_on_a_sign(kind):
    """A wall sign floating in air draws exactly like one on a wall, and the game refuses it."""
    from mcbuild.gen.park import _STEP
    w, _meta, _p = _build(kind)
    for pos, t in w.signs.items():
        name, props = w.cells[pos]
        assert name.endswith("_wall_sign")
        fdx, fdz = _STEP[props["facing"]]
        assert (pos[0] - fdx, pos[1], pos[2] - fdz) in w.cells, f"nothing behind the sign at {pos}"
        for line in t["front"] + t["back"]:
            assert len(line) <= SIGN_WIDTH, f"{line!r} clips mid-word"


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_every_kind_states_a_contract(kind):
    _w, meta, _p = _build(kind)
    assert meta.get("contract"), "a kind with no contract is one nobody can audit later"


# ------------------------------------------------------------------ the checks, checked

def test_the_walk_model_is_not_vacuous():
    """A sealed box has no way out; the same box with a door has one.

    Written the lazy way this test passes on a flood fill that returns everything, and this repo
    has shipped exactly that - a coaster boarding test that seeded in the void and asserted
    nothing. Both halves, or neither is evidence.
    """
    room = {}
    for x in range(-1, 4):
        for y in range(-1, 4):
            for z in range(-1, 4):
                edge = x in (-1, 3) or y in (-1, 3) or z in (-1, 3)
                if edge:
                    room[(x, y, z)] = "stone"
    inside, outside = (1, 0, 1), (1, 0, 5)
    room[(5, -1, 5)] = "stone"
    for z in range(4, 7):
        room[(1, -1, z)] = "stone"
    sealed = walk.reachable(room, inside)
    assert outside not in sealed and len(sealed) < 20

    with_door = dict(room)
    for y in (0, 1):
        with_door.pop((1, y, 3), None)
        with_door[(1, -1, 3)] = "stone"
    opened = walk.reachable(with_door, inside)
    assert outside in opened, "a door in the wall must make a route"


def test_the_walk_model_will_not_climb_a_cliff():
    """One course up, not four. A model that steps up three finds routes nobody can walk."""
    world = {(x, -1, 0): "stone" for x in range(4)}
    for h in range(4):
        world[(4, h - 1, 0)] = "stone"
    reach = walk.reachable(world, (0, 0, 0))
    assert (4, 3, 0) not in reach


def test_a_ladder_is_the_only_way_straight_up():
    plain = {(0, -1, 0): "stone"}
    assert (0, 4, 0) not in walk.reachable(plain, (0, 0, 0))
    laddered = dict(plain)
    for h in range(0, 5):
        laddered[(0, h, 0)] = "ladder"
        laddered[(1, h, 0)] = "stone"
    assert (0, 4, 0) in walk.reachable(laddered, (0, 0, 0))


def test_escapes_notices_water_that_gets_out():
    """`fluids.escapes` on a bowl with a notch in it - or the flume tests prove nothing."""
    bowl = {}
    for x in range(-1, 3):
        for z in range(-1, 3):
            bowl[(x, -1, z)] = "stone"
    for (x, z) in ((-1, 0), (-1, 1), (2, 0), (2, 1), (0, -1), (1, -1), (0, 2), (1, 2)):
        bowl[(x, 0, z)] = "stone"
    env = {(0, 0, 0), (1, 0, 0), (0, 0, 1), (1, 0, 1)}
    assert fluids.escapes(bowl, [(0, 0, 0)], env) == []
    bowl.pop((2, 0, 0))                                   # knock a brick out of the rim
    assert fluids.escapes(bowl, [(0, 0, 0)], env) != []


# ------------------------------------------------------------------------- the powder house
#
# THE MEASUREMENT THAT PRODUCED THIS KIND: the whole frontier zone contained ZERO buttons and
# ZERO levers. Every structure in it was either a rail circuit you ride or a room you walk into
# and look at, and the shops were the worst of it - a row of counters with the tools of a trade
# behind them is a crafting village, not an attraction. Prospect Row is cut and this is half of
# what replaces it, so its tests are about the two things it exists to have: an input you can
# press, and feedback you can see from the far end of the drift.


def _fire(w, meta, arm=True, ticks=60, hold=10):
    """Arm (or do not), press, and return {output cell -> first tick it came on}."""
    sim = _sim(w)
    if arm:
        sim.set(tuple(meta["lever"]), True)
        sim.run(6)
    sim.press(tuple(meta["button"]), ticks=hold)
    trace = sim.run(ticks)
    first = {}
    for k, frame in enumerate(trace):
        for pos, on in frame.items():
            if on and pos not in first:
                first[pos] = k
    return first, trace


@pytest.mark.parametrize("facing", ["east", "north", "west", "south"])
def test_the_powder_house_will_not_fire_unless_it_is_armed(facing):
    """THE INTERLOCK IS THE GAME. Three states have to be silent and only the fourth may fire."""
    w, meta, _p = _build("powderhouse", facing=facing)
    live = [tuple(c) for c in meta["outputs"]]

    at_rest = _sim(w)
    at_rest.run(20)
    assert not [c for c in live if at_rest.powered(c)], "it fires the moment it is built"

    unarmed, _tr = _fire(w, meta, arm=False)
    assert not [c for c in live if c in unarmed], "a press with the lever down fired the shot"

    armed_only = _sim(w)
    armed_only.set(tuple(meta["lever"]), True)
    tr = armed_only.run(40)
    ever = {pos for frame in tr for pos, on in frame.items() if on}
    assert not [c for c in live if c in ever], "arming alone fired the shot"


@pytest.mark.parametrize("facing", ["east", "north", "west", "south"])
def test_arming_and_firing_runs_the_shot_all_the_way_to_the_face(facing):
    """Every stage of the chase, in ORDER, then every charge and the bell.

    The order is the assertion that matters: a chain whose stages all came on together is a
    square wave, not a fuse, and it reads as the whole wall flinching at once rather than as
    something running away from you down the drift. It is the same distinction `arcade._reaction`
    draws between a travelling point and a band.
    """
    w, meta, _p = _build("powderhouse", facing=facing)
    first, _tr = _fire(w, meta)

    chase = [first.get(tuple(c)) for c in meta["chase"]]
    assert all(t is not None for t in chase), f"a chase piston never fired: {chase}"
    assert chase == sorted(chase) and chase[0] < chase[-1], f"the chase is not a chase: {chase}"

    missed = [c for c in meta["shots"] if tuple(c) not in first]
    assert missed == [], f"{len(missed)} charge(s) at the face never fired"
    assert tuple(meta["bell"]) in first, "the bell never rang"
    assert first[tuple(meta["bell"])] >= chase[0], "the bell rang before the fuse reached it"


def test_the_blast_ends_by_itself():
    """A STONE BUTTON RELEASES ITSELF, WHICH IS WHY THERE IS NO `circuits.pulse` HERE.

    Held, the one thing a signal could do to this machine is stand every charge out for ever -
    and it cannot, because the button stops holding. `press` models that; a test that drove the
    button with `set` would silently be testing a lever, which is the trap `Circuit.press`'s own
    docstring warns about.
    """
    w, meta, _p = _build("powderhouse")
    _first, trace = _fire(w, meta, ticks=80, hold=10)
    end = trace[-1]
    assert not [c for c in meta["outputs"] if end.get(tuple(c))], "the shot never stopped"


def test_the_interlock_check_can_actually_fail():
    """TAKE THE INVERTER OUT AND AN UNARMED PRESS MUST GET THROUGH.

    Every assertion above passes on a correct build, which is exactly what the shipped flume's
    own self-check did. The only way to know an interlock test means anything is to break the
    interlock and watch the machine start firing without its lever.
    """
    w, meta, _p = _build("powderhouse")
    torch = [pos for pos, (n, _pr) in w.cells.items() if n == "redstone_wall_torch"]
    assert len(torch) == 1, "the ARMED inverter is the only torch in this kind"
    w.cells.pop(torch[0])
    leaked, _tr = _fire(w, meta, arm=False)
    assert [c for c in meta["shots"] if tuple(c) in leaked], \
        "with the inverter gone an unarmed press still fired nothing - the test proves nothing"


def test_a_chase_piston_never_sits_under_a_repeater():
    """A REPEATER STRONGLY POWERS ONE CELL - ITS OWN FRONT - AND NOTHING BENEATH IT.

    So a piston under a repeater is a piston nothing can ever fire, and it is invisible: the
    state is legal, the block is supported, the bill of materials is right and the audit is clean.
    The chain alternates repeater/dust for exactly this reason and the alternation is pinned.
    """
    w, meta, _p = _build("powderhouse")
    for piston in meta["chase"]:
        above = (piston[0], piston[1] + 1, piston[2])
        assert w.name(*above) == "redstone_wire", \
            f"the chase piston at {piston} is fired by {w.name(*above)!r}, not by dust"


@pytest.mark.parametrize("facing", ["east", "north", "west", "south"])
def test_the_powder_houses_drift_is_walkable_with_headroom_end_to_end(facing):
    """A PLAYER IS TWO BLOCKS TALL, and this repo has shipped seven flume cells and eleven ghost
    train cells where the rider does not fit. Flood-filled from real ground outside the mouth -
    the seed is asserted to be standable first, because this suite has shipped a coaster test
    that seeded in the void and therefore asserted nothing at all.
    """
    w, meta, p = _build("powderhouse", facing=facing)
    from mcbuild.gen.park import _Frame
    f = _Frame(p)
    cells = _names(w)
    seed = f.at(8, -1, 0)
    assert walk.stands(cells, seed), "the seed is not standable - the flood would be vacuous"
    reach = walk.reachable(cells, seed)
    # the three-wide walkway, every course of it, from the mouth to the face
    missing = [(i, d) for i in (7, 8, 9) for d in range(1, meta["face"] - 1)
               if f.at(i, d, 0) not in reach]
    assert missing == [], f"{len(missing)} cell(s) of the drift cannot be walked, e.g. {missing[:4]}"
    for name in ("lever", "button"):
        assert tuple(meta[name]) in reach, f"you cannot stand where the {name} is"


def test_the_powder_house_states_what_it_has_not_proven():
    _w, meta, _p = _build("powderhouse")
    assert meta["unverified"], "a machine with nothing unverified has not been thought about"
    assert meta["inputs"] and meta["outputs"]


# --------------------------------------------------------------------- the saloon card table


def _deal(w, meta, you, house, ticks=40):
    """State both readings - the simulator has no entities and cannot turn a card - press once,
    and report whether the pot paid and the bell rang."""
    sim = _sim(w)
    sim.fill(tuple(meta["player_hopper"]), you)
    sim.fill(tuple(meta["house_hopper"]), house)
    sim.press(tuple(meta["table_button"]), ticks=10)
    trace = sim.run(ticks)
    return (sim.fired.get(tuple(meta["table_pot"]), 0),
            any(frame.get(tuple(meta["table_bell"])) for frame in trace))


@pytest.mark.parametrize("facing", ["east", "north", "west", "south"])
def test_the_card_table_pays_every_tie_and_never_a_loss(facing):
    """ALL NINE PAIRS OF THE THREE-OUTCOME MIX, which is what makes the odds a stated fact.

    A comparator in COMPARE mode passes its back when back >= side, so out of {1, 2, 4} six of
    the nine pairs win and ties go to the player: 6 in 9, printed on the table's own sign.
    """
    w, meta, _p = _build("saloon", facing=facing, width=17, depth=12)
    levels = [1, 2, 4]
    wins = 0
    for you in levels:
        for house in levels:
            paid, rang = _deal(w, meta, you, house)
            if you >= house:
                assert paid == 1 and rang, f"you={you} house={house} did not pay"
                wins += 1
            else:
                assert paid == 0 and not rang, f"you={you} house={house} paid on a loss"
    assert wins == 6, f"the odds moved: {wins} in 9"


def test_the_card_table_is_dark_until_somebody_plays_it():
    """A house that pays the moment it is built pays on every chunk load."""
    w, meta, _p = _build("saloon", width=17, depth=12)
    sim = _sim(w)
    sim.run(20)
    assert sim.fired.get(tuple(meta["table_pot"]), 0) == 0
    assert not sim.powered(tuple(meta["table_bell"]))


def test_a_held_press_at_the_card_table_pays_exactly_one_chip():
    """THE POT IS A DROPPER BECAUSE A DROPPER FIRES ON AN EDGE.

    A comparator reads a hopper for as long as the card sits in it, so anything driven by the
    LEVEL stays driven - which is the hazard the casino pins and does not fix. A dropper is the
    cheapest correct answer and this is the assertion that says so.
    """
    w, meta, _p = _build("saloon", width=17, depth=12)
    sim = _sim(w)
    sim.fill(tuple(meta["player_hopper"]), 4)
    sim.fill(tuple(meta["house_hopper"]), 1)
    sim.press(tuple(meta["table_button"]), ticks=60)
    sim.run(80)
    assert sim.fired.get(tuple(meta["table_pot"]), 0) == 1


def test_the_card_table_can_be_switched_off():
    """`game: False` has to keep working - the old shape is what would be standing in world."""
    _w, meta, _p = _build("saloon", width=17, depth=12, game=False)
    assert "table_button" not in meta


def test_the_card_table_is_reachable_and_the_saloon_still_works():
    """The generator refuses to build otherwise; this exercises the same contract from outside,
    and it is the check that catches a table laid across the only way in."""
    w, meta, p = _build("saloon", width=17, depth=12)
    from mcbuild.gen.park import _Frame
    f = _Frame(p)
    cells = _names(w)
    reach = walk.reachable(cells, f.at(p["width"] // 2, -4, 0))
    assert tuple(meta["table_button"]) in reach
    assert f.at(2, p["depth"] - 3, 0) in reach, "the bar is walled off behind the card table"
    assert meta["tables"] >= 2 and meta["beds"] >= 2


def test_the_card_table_states_its_odds_and_what_it_has_not_proven():
    _w, meta, _p = _build("saloon", width=17, depth=12)
    assert "6 in 9" in meta["table_contract"]
    assert meta["table_stock"]["the deal"] and meta["table_stock"]["the house"]


# -------------------------------------------------------- the mine, and its headroom for real


def test_the_mine_has_no_pocket_you_can_stand_in_and_not_reach():
    """EVERY STANDABLE CELL UNDERGROUND IS ON THE TOUR.

    A timber set, a lamp or a shaft lining one cell into a drift does not make the walkthrough
    fail - it makes a pocket you can be in and cannot get to, which no leg-by-leg check sees
    because the legs still connect. Measured off the design's own floor course.
    """
    w, meta, _p = _build("minehead")
    cells = _names(w)
    reach = walk.reachable(cells, tuple(meta["adit_mouth"]))
    fy = meta["floor_h"] + 100                       # `_build` stands the design at y = 100
    stand = {(x, y + 1, z) for (x, y, z) in cells if y == fy}
    stand = {s for s in stand if walk.stands(cells, s)}
    assert len(stand) > 60, "no underground floor at all - the check would be vacuous"
    orphan = sorted(stand - reach)
    assert orphan == [], f"{len(orphan)} standable cell(s) underground are cut off, e.g. {orphan[:3]}"


def test_the_mine_walk_check_can_actually_fail():
    """PLUG BOTH SHAFTS AND THE WORKINGS MUST GO DARK.

    One is not enough and that is the design being right: the tour is a LOOP, so blocking the
    hoist still leaves the escape shaft. A check that cannot fail is worse than no check.
    """
    w, meta, _p = _build("minehead")
    cells = dict(_names(w))
    for leg in ("shaft_head", "way_out"):
        x, y, z = meta[leg]
        cells[(x, y, z)] = "cobblestone"
        cells[(x, y + 1, z)] = "cobblestone"
    reach = walk.reachable(cells, tuple(meta["adit_mouth"]))
    assert tuple(meta["gallery_far"]) not in reach
    fy = meta["floor_h"] + 100
    assert not [c for c in reach if c[1] <= fy + 3], "the workings are still reachable"


# ------------------------------------------------------- the census that started all of this


def test_the_zone_has_something_to_press():
    """ZERO BUTTONS AND ZERO LEVERS IN A WHOLE ZONE IS THE NUMBER THIS PASS EXISTS FOR.

    Counted over the kinds this file owns, because the arcade units and the rides have their own
    suites. It is a floor rather than a target: the point is that the frontier's own buildings
    now contain something a hand can operate.
    """
    inputs = collections.Counter()
    for kind in ("powderhouse", "saloon", "minehead", "sluice"):
        w, _meta, _p = _build(kind, **({"width": 17, "depth": 12} if kind == "saloon" else {}))
        for _pos, (name, _pr) in w.cells.items():
            if name in ("lever", "stone_button"):
                inputs[name] += 1
    assert inputs["lever"] >= 1, "nothing in the zone can be armed"
    assert inputs["stone_button"] >= 2, "nothing in the zone can be pressed"
