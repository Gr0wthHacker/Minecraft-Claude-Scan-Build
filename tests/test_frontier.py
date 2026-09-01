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

NEW_KINDS = ("sluice", "minehead", "saloon", "falsefront")


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
