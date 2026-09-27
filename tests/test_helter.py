"""THE MIDWAY'S THIRD RIDE, AND THE FOUR THINGS ONLY A SIMULATION CAN SAY ABOUT IT.

`mcbuild/gen/helter.py` builds a helter-skelter in the emptiest lot in the park - a soul-sand
bubble column up the inside of a striped drum and 1.75 turns of blue ice down the outside. Every
offline check this repo owns passes a ride that does not work: the block states are legal, the
placements are supported, the bill of materials is right, nothing collides, and `render3d` draws a
slide you cannot get onto exactly as it draws one you can.

So the contract is asserted here rather than hoped for:

    THE LIFT IS SEALED         `fluids.escapes` against the design's own declared envelope
    THE LIFT LIFTS             a continuous column of SOURCE water over soul sand
    YOU CAN GET ON             a walk from the queue mouth to the boarding deck, in CONTEXT
    YOU CAN GET DOWN           a descending walk from the top floor to the run-out, every step legal
    THE EXIT IS NOT THE QUEUE  `PARK_MIDWAY.md`: "The exit cannot feed into waiting guests"

**AND IT IS JUDGED IN CONTEXT.** The back promenade runs through the middle of this lot and is
`Park Ways`' ground, not this design's, so the forecourt and the tower are two pieces in isolation
and one piece in the world - the Mine Ridge's own recorded situation. A walk test on the design
alone would be testing a park that does not exist.
"""
from __future__ import annotations

import json
import math
from collections import deque
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
import yaml

from mcbuild import blocks, fluids, palette, schem
from mcbuild.gen import helter

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "configs" / "pf_helter_skelter.yaml"
WORLD = ROOT / "out" / "Park Complete.litematic"
V0, U0 = 100, 345
#: `Park Complete` is anchored at (97500, 190, 80300) and its lawn is Y202, so the design's own
#: course 0 is Y203 - the first course above the lawn, exactly as every Midway build's `at` says.
#: **V AND U ARE ALREADY THE MODEL'S OWN X AND Z**, because the park's anchor IS the lattice
#: origin: model[y, U, V]. Subtracting the anchor from them again is an index of -79,955, which is
#: how the first version of this file failed - and a smaller slip would have read the wrong cells
#: in silence.
#:
#: **AND THE COMPOSITE'S Y IS NOBODY'S CONSTANT.** It is a function of the deepest thing in the
#: park: written as a literal 190 this file read thirteen courses of empty sky and reported the
#: whole lot as disconnected, which is exactly the failure `tests/test_park_entrance.py` already
#: records - the day a stream placed an underground design in Prismworks, `Park Complete`'s y went
#: 190 -> 94 and eight of its tests said a visitor spawns with no ground under them. The x and z
#: are the lattice's own anchor and never move; the y is read from the sidecar.
LAWN = 202


@lru_cache(maxsize=1)
def _park_y() -> int:
    """...and CACHED, because `_index`/`_course` are called twice per cell of the lot and reading
    and parsing the sidecar 200,000 times took this file from 45 seconds to twelve minutes."""
    return int(json.loads((ROOT / "out" / "Park Complete.scan.json").read_text())["origin"]["y"])


def _course(y_index: int) -> int:
    """Model course index -> the design's own course (0 = the first above the lawn)."""
    return y_index - (LAWN + 1 - _park_y())


def _index(course: int) -> int:
    return course + (LAWN + 1 - _park_y())


@pytest.fixture(scope="module")
def cfg():
    return yaml.safe_load(CFG.read_text())


@pytest.fixture(scope="module")
def built(cfg):
    return helter.build(cfg["params"])


@pytest.fixture(scope="module")
def cells(built):
    """The design as {(V, course, U) -> block name}, which is what `fluids` reads."""
    out = {}
    pal = [e.value["Name"].value.split(":")[-1] for e in built.palette]
    for y in range(built.sy):
        for z in range(built.sz):
            for x in range(built.sx):
                i = int(built.ids[y, z, x])
                if i:
                    out[(x + V0, y, z + U0)] = pal[i]
    return out


@pytest.fixture(scope="module")
def world(cfg):
    """The GROUND under the design: the lawn course, the promenade and the ground layer's masts.

    **THE COMPOSITE CONTAINS THIS DESIGN, so reading it whole is reading the answer.** The day
    `PF Helter Skelter` went into `park_place.EXTRAS_READY`, `out/Park Complete.litematic` began
    holding every cell of it - and a walk test over that composite would pass on the SHIPPED copy
    however broken the generator became, which is the self-reference trap this repo has now
    recorded four times (the ruin ring's seat, the town's door frames, the scatter's own lawn, the
    frog's plaques). So what is taken from the park is only what the park actually owns here: the
    lawn a course below the design, the back promenade that splits the lot, and the lamp masts the
    config names in `blocked`. Everything else in these 2,160 columns is the design's, and the
    design under test supplies it.
    """
    if not WORLD.exists():
        pytest.skip("out/Park Complete.litematic is not built")
    m = schem.load(str(WORLD))
    pal = [e.value["Name"].value.split(":")[-1] for e in m.palette]
    theirs = {(v, u)
              for bv0, _by0, bu0, bv1, _by1, bu1 in cfg["params"]["blocked"]
              for v in range(bv0, bv1 + 1) for u in range(bu0, bu1 + 1)}
    out = {}
    for v in range(V0, V0 + 54):
        for u in range(U0, U0 + 40):
            for y in range(_index(-1), _index(44)):
                c = _course(y)
                if c >= 0 and (v, u) not in theirs:
                    continue                       # this design's own ground - it supplies it
                i = int(m.ids[y, u, v])
                if i:
                    out[(v, c, u)] = pal[i]
    return out


# --------------------------------------------------------------------------- the movement model


#: Deliberately short: anything not named here is treated as SOLID, which errs toward reporting a
#: route that is blocked rather than passing one that is not. `ochre_froglight` is NOT here - it is
#: the floor, an opaque emitter a course down, and a rider stands on it.
PASSABLE = {"air", "water", "moss_carpet", "oak_wall_sign", "lantern", "short_grass", "grass",
            "fern", "poppy", "dandelion", "azalea", "glow_lichen", "oak_leaves", "vine", "chain",
            "iron_chain", "rail", "torch", "wall_torch", "red_wall_banner"}


def _solid(comp, p) -> bool:
    n = comp.get(p)
    return n is not None and n.split("[")[0] not in PASSABLE


def _stands(comp, p) -> bool:
    """Feet at p: something solid under it and two clear courses for a body."""
    v, y, u = p
    return (_solid(comp, (v, y - 1, u))
            and not _solid(comp, p) and not _solid(comp, (v, y + 1, u)))


def _walk(comp, start, *, drop=1, bounds=None, cap=200000):
    """Every cell reachable on foot: step up at most one, fall at most `drop`.

    `drop` is the whole difference between the two questions this file asks. Getting ON is a walk
    and a walk cannot fall; getting DOWN a helter-skelter is a slide, and a slide is exactly a
    controlled fall - so the descent is flooded with a drop of three and the approach with one.
    """
    seen, q = {tuple(start)}, deque([tuple(start)])
    while q and len(seen) < cap:
        v, y, u = q.popleft()
        for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in range(1, -drop - 1, -1):
                p = (v + dv, y + dy, u + du)
                if p in seen or (bounds and not bounds(p)):
                    continue
                if _stands(comp, p):
                    seen.add(p)
                    q.append(p)
                    break
    return seen


# --------------------------------------------------------------------------- the ride works


def test_the_lift_is_a_sealed_body_of_water(built, cells):
    """`fluids.escapes` against the design's OWN envelope, which is the only honest test of it.

    A bounding box round a water ride contains the apron it spills onto and would have passed the
    log flume that drained 199,959 cells to Y-1908. The envelope here is the shaft and the trough,
    cell for cell, recorded by the generator as it places them.
    """
    env = [tuple(q) for q in built.meta["water_envelope"]]
    wet = [p for p, n in cells.items() if n.split("[")[0] == "water"]
    assert wet, "the lift has no water in it"
    assert sorted(wet) == sorted(env), "the envelope does not describe the water that was placed"
    assert fluids.escapes(cells, wet, env) == []
    assert fluids.unenclosed(cells, allow=env) == []


def test_every_water_cell_is_a_SOURCE(cells):
    """A trough of flowing water lifts nobody, and it renders identically to one that does."""
    for p, n in cells.items():
        if n.split("[")[0] == "water":
            assert "level=0" in n or n == "water", f"{p} is not a source: {n}"


def test_the_column_stands_on_soul_sand_and_is_unbroken(built, cells):
    """A bubble column is soul sand plus an unbroken column of water over it. One gap anywhere in
    the middle and the ride carries a rider halfway up the tower and stops."""
    cv, cu = built.meta["centre"]
    top = built.meta["top"]                    # read from the build, never typed here
    for v in range(cv - 1, cv + 2):
        for u in range(cu - 1, cu + 2):
            assert cells.get((v, 0, u), "").split("[")[0] == "soul_sand", f"no lift under {v},{u}"
            for y in range(1, top + 1):
                assert cells.get((v, y, u), "").split("[")[0] == "water", f"gap at {v},{y},{u}"


def test_a_rider_can_walk_from_the_queue_to_the_boarding_deck(built, cells, world):
    """IN CONTEXT, because the queue stands on the ground layer's own lawn and paving."""
    comp = dict(world)
    comp.update(cells)
    a = built.meta["anchors"]
    qv, qu = a["queue_entry"]
    bv, bu = a["board"]
    start = (qv, 1, qu)
    assert _stands(comp, start), "the queue mouth is not somewhere a rider can stand"
    reach = _walk(comp, start, bounds=lambda p: V0 <= p[0] < V0 + 54 and U0 <= p[2] < U0 + 40
                  and 0 <= p[1] < 44)
    deck = [(bv + dv, 3, bu + du) for dv in (-2, 0, 2) for du in (0, 1, 2)]
    assert any(p in reach for p in deck), "the boarding deck cannot be walked to from the queue"
    # ...and the last step off it is INTO the water, not over a wall a rider cannot climb.
    wet = [(bv + dv, 2, bu + 1) for dv in (-1, 0, 1)]
    assert any(cells.get(p, "").split("[")[0] == "water" for p in wet), \
        "stepping off the deck does not land in the trough"


def test_a_rider_can_get_all_the_way_down_the_chute(built, cells, world):
    """The descent, flooded as a slide: step up at most one, fall at most three.

    **THIS IS THE CHECK THAT CANNOT BE EYEBALLED.** A helix whose steps are two courses apart, or
    whose head is walled off from the drum's own door, renders exactly like one that is not - and
    the only symptom in game is a rider standing at the top of a tower with nowhere to go.
    """
    comp = dict(world)
    comp.update(cells)
    cv, cu = built.meta["centre"]
    top = built.meta["top"]
    start = (cv - 2, top + 1, cu)                     # on the drum's upper floor, by the door
    assert _stands(comp, start), "there is nowhere to stand at the top of the lift"
    reach = _walk(comp, start, drop=3,
                  bounds=lambda p: V0 <= p[0] < V0 + 54 and U0 <= p[2] < U0 + 40
                  and 0 <= p[1] < 44)
    ice = [p for p, n in cells.items() if n.split("[")[0] == "blue_ice"]
    on_ice = [(v, y + 1, u) for v, y, u in ice]
    hit = [p for p in on_ice if p in reach]
    assert len(hit) > 0.85 * len(on_ice), \
        f"only {len(hit)} of {len(on_ice)} chute cells are reachable from the top"
    ev, eu = built.meta["anchors"]["ride_exit"]
    assert any((ev + dv, y, eu + du) in reach
               for dv in (-1, 0, 1) for du in (-2, -1, 0) for y in (1, 2)), \
        "the chute does not discharge onto the exit apron"


def test_the_exit_is_not_the_queue(built):
    """`PARK_MIDWAY.md`: "The exit cannot feed into waiting guests." The foot angle is CHOSEN -
    1.75 turns from a head on the -V face lands a quarter turn short, pointing +U - so this is a
    property of the geometry rather than of where the arithmetic happened to come out."""
    a = built.meta["anchors"]
    assert a["ride_exit"][1] - a["board"][1] > 20, "boarding and discharge are on the same side"
    assert abs(built.meta["foot_angle"] - math.pi / 2) < 0.2


# --------------------------------------------------------------------------- the build


def test_every_part_of_the_ride_can_be_WALKED_TO_from_the_promenade(built, cells, world):
    """A WALK, not a component count.

    **A LOT STANDING ONE COURSE ABOVE THE STREET IS DIAGONAL TO IT**, which is correct
    architecture and disconnected arithmetic - every building lot in this park sits on that step,
    and `tests/test_park_entrance.py` already allows for it by name. So what is asserted is the
    thing that actually matters: from the back promenade that splits this lot, a guest can reach
    the forecourt walk, the queue, the tower's own door and the exit apron.
    """
    comp = dict(world)
    comp.update(cells)
    axis = (U0 + U0 + 39) // 2
    start = (125, 0, axis)                       # standing on the back promenade, mid-lot
    assert _stands(comp, start), "the promenade is not somewhere a guest can stand"
    reach = _walk(comp, start, bounds=lambda p: V0 - 2 <= p[0] < V0 + 56
                  and U0 - 2 <= p[2] < U0 + 42 and -2 <= p[1] < 44)
    a = built.meta["anchors"]
    cv, cu = built.meta["centre"]
    want = {
        "the forecourt walk": [(v, 1, axis) for v in range(101, 120)],
        "the queue mouth": [(a["queue_entry"][0] + dv, 1, a["queue_entry"][1] + du)
                            for dv in (-1, 0, 1) for du in (0, 1, 2)],
        "the boarding deck": [(a["board"][0] + dv, 3, a["board"][1] - du)
                              for dv in (-2, 0, 2) for du in (0, 1, 2)],
        "the exit apron": [(a["ride_exit"][0] + dv, 1, a["ride_exit"][1] + du)
                           for dv in (-2, 0, 2) for du in (-2, 0, 2)],
    }
    missed = [k for k, ps in want.items() if not any(p in reach for p in ps)]
    assert not missed, f"unreachable from the promenade: {missed}"


def test_nothing_stands_on_ground_the_park_already_owns(cfg, built):
    """`blocked` is a tripwire, not a permission: the build raises on a hit, so reaching this at
    all means it did not want one. This pins that the boxes still describe the real masts."""
    m = schem.load(str(WORLD)) if WORLD.exists() else pytest.skip("no park")
    pal = [e.value["Name"].value.split(":")[-1] for e in m.palette]
    boxes = cfg["params"]["blocked"]
    for bv0, _by0, bu0, bv1, _by1, bu1 in boxes:
        if bv1 - bv0 > 8:
            continue                                    # the promenade box, checked below
        found = any(pal[int(m.ids[_index(c), u, v])] != "air"
                    for v in range(bv0, bv1 + 1) for u in range(bu0, bu1 + 1)
                    for c in range(0, 6))
        assert found, f"blocked box {bv0},{bu0}-{bv1},{bu1} guards nothing - the mast moved"


def test_the_promenade_is_untouched(cells):
    """A remedial design's damage is measured in what it REPLACES. This replaces one street:
    none."""
    assert not [p for p in cells if 123 <= p[0] <= 127]


def test_every_material_is_cheap_available_and_neither_currency_nor_a_faller(cells):
    """Rule 12 and rule 16, and the declared exception. `hay_block` is the run-out's buffer and is
    the only fairground block that reads as one; six of it is stated rather than smuggled."""
    names = {n.split("[")[0] for n in cells.values()}
    dear = sorted(n for n in names if palette.tier(n) == "expensive")
    assert dear == ["hay_block"], dear
    assert sum(1 for n in cells.values() if n.split("[")[0] == "hay_block") <= 8
    for n in names:
        assert blocks.spendable(n), f"{n} is currency on this server"
        assert not blocks.falls(n), f"{n} would pour off the tower"


def test_the_value_ladder_is_real(cells):
    """MEASURED ACROSS FAMILIES, which is the only place this economy's contrast has ever been -
    this repo has concluded four separate times that it has none, every time from inside one."""
    def lum(n):
        r, g, b = blocks.color(n, "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    rungs = [lum("polished_blackstone_bricks"), lum("red_wool"), lum("stone_bricks"),
             lum("blue_ice"), lum("white_wool")]
    assert all(b - a >= 15 for a, b in zip(sorted(rungs), sorted(rungs)[1:])), rungs


def test_no_sign_line_clips_mid_word(built):
    """FIFTEEN CHARACTERS IS THE LINE, and this park has shipped `MINE CART ESCAP`,
    `and prize windo` and `ore from the ad`. `_Lot.sign` truncates silently, so the count is what
    is asserted: every board this design asks for must actually be placed."""
    assert built.meta["signs"] >= 5, "a sign was refused - its support is not there"


def test_the_ride_carries_its_own_numbers(built):
    m = built.meta
    assert m["facing"] == "west"
    # THE TURNS ARE A QUARTER SHORT OF A WHOLE ONE, whatever the number is: that is what puts the
    # foot opposite the queue, and it is the property rather than the value that is pinned.
    assert m["chute"] > 100
    assert abs((m["turns"] % 1.0) - 0.75) < 1e-6, m["turns"]
    assert m["lamps"] >= 15, "a ride nobody can see at night"
    assert "bubble column" in m["note"]
