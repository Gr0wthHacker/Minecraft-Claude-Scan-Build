"""What the park's three high points PROMISE, and the FLOOD that proves a visitor can reach them.

The one assertion this file exists for is the last kind: **a flood from the park's own ground to
each summit, and back down again.** This repo has shipped a flight that was one-way - the rim
ledge stood at 202.0 against a land bridge at 203.0, so its top tread topped out at 201.5, a 1.5
step against a player's 1.25 climb - and the audit was clean, the geometry legal and the build
unusable. A stair is not proved by its block states; it is proved by walking it.

Everything else here is a CONTRACT rather than a snapshot. A test that pins "4,494 blocks" fails
the first time somebody improves the tower, which trains people to edit the test. What is pinned
is what was expensive to learn: the stair convention our renderer cannot draw wrong, headroom over
every tread, the lot boundary, the park's own street, the reserves, and the fact that these three
claim no mechanism at all.

Runtime note: the flood runs once for the whole module and is shared by every test that needs it -
`out/Park Complete.litematic` is 26.4 million cells and re-flooding it per test would make this
file the slowest thing in the suite.
"""
from __future__ import annotations

import collections
import os
import sys

import numpy as np
import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcbuild import blocks, palette, schem                                # noqa: E402
from mcbuild.gen import park_vantage as pv                                # noqa: E402
from mcbuild.gen.parkways import LANDS as WAYS_LANDS                      # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
GROUND = os.path.join(ROOT, "out", "Park Complete.litematic")
WAYS = os.path.join(ROOT, "out", "Park Ways.litematic")

CONFIGS = ["pf_vantage_frontier_lookout", "pf_vantage_midway_belvedere",
           "pf_vantage_prism_summit"]

#: `out/Park Complete.litematic`'s own frame: V -> world X, U -> world Z, and park y counts up
#: from world Y190. The lawn's top course is park y12, so a visitor standing on it has their feet
#: in park y13 - which is canvas y0 of every design in this file.
PARK_ORIGIN = (97500, 190, 80300)
LAWN = 12
GROUND_Y = LAWN + 1

#: The lawn's own trim, and the ONLY block in the world these designs may stand where. Every park
#: module carries the same exemption; see `configs/pf_prismworks_prism_ascent.yaml`.
CLEARABLE = {"moss_carpet"}

#: Seeds for the flood: the middle of the spine in each land and at each reach, at ground level.
#: The spine's centre line is V12 and it runs the whole 600, so any of these reaches all of it.
SPINE_SEEDS = [(GROUND_Y, u, 12) for u in (20, 100, 235, 300, 380, 500, 560)]


# --------------------------------------------------------------------------- fixtures


def _cfg(stem: str) -> dict:
    with open(os.path.join(ROOT, "configs", f"{stem}.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _build(stem: str):
    cfg = _cfg(stem)
    assert cfg["gen"] == "park_vantage", f"{stem} is not a park_vantage config"
    return pv.build(cfg["params"])


@pytest.fixture(scope="module")
def designs():
    return {stem: _build(stem) for stem in CONFIGS}


@pytest.fixture(scope="module")
def world():
    if not os.path.exists(GROUND):
        pytest.skip("out/Park Complete.litematic is not in the tree")
    return schem.load(GROUND)


@pytest.fixture(scope="module")
def street():
    """Every column of the park that carries a street, path, plaza, verge fixture or lamp.

    Derived from the shipped ground rather than from a list of coordinates: `Park Ways` paves in
    `moss_block` where it means LAWN and in a land palette where it means STREET, and everything
    it stands on the ground - lamp posts, benches, the lamps' own iron-bars arms at world Y209 -
    is a column no building may claim. `moss_carpet` is the lawn's TRIM and is excluded, because
    it is the one thing every park module is allowed to stand over."""
    if not os.path.exists(WAYS):
        pytest.skip("out/Park Ways.litematic is not in the tree")
    m = schem.load(WAYS)
    idx = {n: i for i, n in enumerate(m.names)}
    moss, carpet = idx["minecraft:moss_block"], idx.get("minecraft:moss_carpet", -1)
    paved = (m.ids[0] != moss) & (m.ids[0] != 0)
    standing = ((m.ids[1:] != 0) & (m.ids[1:] != carpet)).any(axis=0)
    return paved | standing                                   # [U, V]


def _cells(c):
    """Every cell of a design, in park coordinates, as {(y, u, v): name}."""
    ox, oy, oz = c.world_origin
    v0, y0, u0 = ox - PARK_ORIGIN[0], oy - PARK_ORIGIN[1], oz - PARK_ORIGIN[2]
    out = {}
    ids = c.ids
    for y in range(ids.shape[0]):
        zs, xs = np.nonzero(ids[y])
        for z, x in zip(zs, xs):
            out[(y0 + y, u0 + int(z), v0 + int(x))] = c.get_name(int(x), y, int(z)).split(":")[-1]
    return out


#: A `wall` or a `fence` is a block and a HALF tall. A player steps up 0.6 and jumps 1.25, so
#: from an adjacent floor at the same level you cannot get on top of one - which is the entire
#: reason those blocks exist and the entire reason every parapet, balustrade and window sill in
#: this design is made of them. The voxel model would otherwise report their tops as ordinary
#: floor one course up and cheerfully route a visitor over every railing in the park.
def _is_tall(name: str) -> bool:
    n = name.split("[")[0].split(":")[-1]
    return n.endswith("_wall") or n.endswith("_fence") or n.endswith("_fence_gate")


@pytest.fixture(scope="module")
def placed(designs, world):
    """The world with all three vantages standing in it, plus each design's own cell map."""
    occ = world.ids != 0
    tall = np.array([_is_tall(n) for n in world.names], bool)[world.ids]
    mine = {stem: _cells(c) for stem, c in designs.items()}
    for cells in mine.values():
        for (y, u, v), name in cells.items():
            occ[y, u, v] = True
            tall[y, u, v] = _is_tall(name)
    return occ, tall, mine


# --------------------------------------------------------------------------- the walk model


def standable(occ: np.ndarray, tall: np.ndarray | None = None) -> np.ndarray:
    """Solid below, two clear courses for the body - and the block below is one you can stand on.

    The first two are the brief's own definition. The third is the correction above: a railing is
    1.5 tall and cannot be climbed onto from the floor beside it, and without that every parapet
    in this park reads as a step."""
    st = np.zeros_like(occ)
    st[1:-1] = occ[:-2] & ~occ[1:-1] & ~occ[2:]
    if tall is not None:
        st[1:-1] &= ~tall[:-2]
    return st


def flood(occ: np.ndarray, seeds, tall: np.ndarray | None = None) -> np.ndarray:
    """Every standable cell reachable on foot, stepping at most one course either way.

    The step relation is SYMMETRIC by construction - |dy| <= 1 between two standable cells reads
    the same from both ends - so a cell in this set is one you can walk to AND walk back from.
    That is what makes the one-way-flight failure impossible to hide here, and
    `test_every_summit_is_walkable_in_BOTH_directions` re-derives it from the far end anyway
    rather than resting on the argument."""
    st = standable(occ, tall)
    seen = np.zeros_like(occ)
    dq = collections.deque()
    for s in seeds:
        if st[s] and not seen[s]:
            seen[s] = True
            dq.append(s)
    ny, nz, nx = occ.shape
    while dq:
        y, z, x = dq.popleft()
        for dz, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            z2, x2 = z + dz, x + dx
            if not (0 <= z2 < nz and 0 <= x2 < nx):
                continue
            for dy in (0, 1, -1):
                y2 = y + dy
                if 1 <= y2 < ny - 1 and st[y2, z2, x2] and not seen[y2, z2, x2]:
                    seen[y2, z2, x2] = True
                    dq.append((y2, z2, x2))
                    break
    return seen


@pytest.fixture(scope="module")
def before(world):
    tall = np.array([_is_tall(n) for n in world.names], bool)[world.ids]
    return flood(world.ids != 0, SPINE_SEEDS, tall)


@pytest.fixture(scope="module")
def after(placed):
    occ, tall, _ = placed
    return flood(occ, SPINE_SEEDS, tall)


def _deck(c) -> tuple:
    """(park y of the deck's walking surface, the lot box) for a design."""
    v0, u0, v1, u1 = c.meta["lot"]
    return GROUND_Y + int(c.meta["deck_surface_above_lawn"]), (v0, u0, v1, u1)


# --------------------------------------------------------------------------- the gap


def test_the_park_had_no_vertical_experience_at_all(before):
    """The measurement these three exist to answer, re-derived rather than quoted.

    If the park ever grows a high place of its own these numbers move, and this test is where
    that shows up - which is the point: the case for three towers is a measurement, not a taste."""
    total = int(before.sum())
    bottom_ten = int(before[:GROUND_Y + 10].sum())
    assert total > 100_000, "the park's ground should be one big connected floor"
    # 0.85 rather than the 0.955 measured on the day: `out/Park Complete.litematic` is rebuilt by
    # four other streams and the share drifts a point or two with every module they add. What is
    # being pinned is the PREMISE - that this park is overwhelmingly flat - not a reading.
    assert bottom_ten / total > 0.85, (
        f"the premise has changed: {bottom_ten}/{total} of the reachable park is in its bottom "
        f"ten courses, and these towers were built because that share was 95.5%")
    highest = int(np.nonzero(before.any(axis=(1, 2)))[0].max())
    assert highest < 60, f"something already reaches park y{highest}; re-read the brief"


# --------------------------------------------------------------------------- the flood proof


def test_every_summit_is_reachable_on_foot_from_the_parks_own_ground(designs, after):
    """THE ASSERTION THIS FILE EXISTS FOR. Flood from the spine; land on every deck."""
    for stem, c in designs.items():
        y, (v0, u0, v1, u1) = _deck(c)
        reached = int(after[y, u0:u1 + 1, v0:v1 + 1].sum())
        assert reached >= 40, (
            f"{stem}: only {reached} cells of its deck at park y{y} can be reached on foot from "
            f"the spine - the climb is broken")


def test_every_summit_is_walkable_in_BOTH_directions(designs, placed):
    """Down as well as up, seeded from the deck rather than from the ground.

    The rim ledge failed exactly here: you could get down and not back up, and nothing but a walk
    could see it. Flooding from the top and demanding the spine back is the other half of the
    same proof, and it is run separately rather than argued from the symmetry of the step rule."""
    occ, tall, _ = placed
    st = standable(occ, tall)
    for stem, c in designs.items():
        y, (v0, u0, v1, u1) = _deck(c)
        seeds = [(y, u, v) for u in range(u0, u1 + 1) for v in range(v0, v1 + 1) if st[y, u, v]]
        assert seeds, f"{stem}: nothing is standable on its own deck"
        down = flood(occ, seeds, tall)
        assert down[GROUND_Y, 300, 12] or down[GROUND_Y, 100, 12] or down[GROUND_Y, 560, 12], (
            f"{stem}: you can get onto its deck and not back down to the spine")


def test_the_towers_put_a_visitor_above_the_park_where_nothing_could_before(before, after):
    """The whole point, as one number, both sides."""
    hi = GROUND_Y + 17          # park y30 - the brief's own line
    was, now = int(before[hi:].sum()), int(after[hi:].sum())
    assert was < 500, f"the baseline moved: {was} reachable cells above park y30"
    assert now > 5 * was, (
        f"only {now} reachable cells above park y30 against a baseline of {was}; three towers "
        f"should be worth far more than that")
    top_before = int(np.nonzero(before.any(axis=(1, 2)))[0].max())
    top_after = int(np.nonzero(after.any(axis=(1, 2)))[0].max())
    assert top_after >= top_before + 20, (
        f"the highest a visitor can stand only moved from park y{top_before} to y{top_after}")


def test_the_prism_ascents_podium_roof_becomes_reachable(designs, before, after):
    """THE ONE DELIBERATE ATTACHMENT, proved rather than described.

    The Ascent's podium roof is a finished walkable gallery at park y25 that nothing could reach.
    If its owner moves that course, or closes the cell at U542, this fails HERE - which is the
    only reason it is safe to depend on somebody else's geometry at all."""
    roof = (slice(25, 27), slice(542, 584), slice(51, 90))
    assert int(before[roof].sum()) == 0, (
        "the Ascent's podium roof is already reachable; the Summit's bridge is no longer the "
        "thing that opens it and its `rise: 13` may no longer be justified")
    opened = int(after[roof].sum())
    assert opened >= 300, (
        f"the bridge only opened {opened} cells of the podium roof - check park y25 is still the "
        f"podium's own slab course and U542 is still clear at y26")


def test_each_land_gets_a_high_place(designs, after):
    """One per land, and each of them genuinely above its own land."""
    lands = {}
    for stem, c in designs.items():
        y, (v0, u0, v1, u1) = _deck(c)
        lands.setdefault(c.meta["land"], []).append((stem, y))
        assert int(after[y, u0:u1 + 1, v0:v1 + 1].sum()) > 0
    assert set(lands) == {"frontier", "midway", "prismworks"}, (
        f"a land has no vantage: {sorted(lands)}")


def test_the_summit_is_the_highest_of_the_three_and_it_is_the_prismworks_one(designs):
    tops = {stem: c.meta["deck_surface_above_lawn"] for stem, c in designs.items()}
    best = max(tops, key=tops.get)
    assert best == "pf_vantage_prism_summit", f"{best} has become the park's summit"
    assert tops[best] >= 60, "a summit under sixty courses does not look down the whole 600"
    others = [v for k, v in tops.items() if k != best]
    assert all(v + 15 <= tops[best] for v in others), (
        "the summit must read as the summit; the others are too close to it")


def test_no_vantage_out_tops_the_parks_own_skyline_dominants(designs):
    """The Prism Ascent is 83 courses and the Sky Lift 76. A stair tower is a way UP, not a
    fourth silhouette, and the moment one of these out-tops them the park has a new problem
    rather than a new view."""
    for stem, c in designs.items():
        assert c.meta["height"] <= 78, (
            f"{stem} is {c.meta['height']} courses tall; the Sky Lift is 76 and the Prism "
            f"Ascent 83, and neither should be beaten by a stair tower")


# --------------------------------------------------------------------------- the climb itself


def test_every_tread_faces_its_own_ascent(designs):
    """The stair convention, asserted because a picture cannot check it.

    A flight ascending toward D has every tread `facing=D, half=bottom`; built the other way the
    risers face into the descent and it cannot be walked up - and this repo's renderer draws both
    identically, so a backwards flight is invisible in every sheet and wrong in game for ever."""
    step = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
    for stem, c in designs.items():
        flights = c.meta["flights"]
        assert flights, f"{stem} has no flights"
        for f in flights:
            du = step[f["facing"]][1]
            assert du != 0, f"{stem}: a flight along U must face north or south"
            assert (f["u_to"] - f["u_from"]) * du > 0, (
                f"{stem}: a flight running {f['u_from']}->{f['u_to']} along U cannot face "
                f"{f['facing']} - it is built backwards and cannot be climbed")
            for v in range(f["band"][0], f["band"][1] + 1):
                for i in range(abs(f["u_to"] - f["u_from"]) + 1):
                    u = f["u_from"] + du * i
                    name = c.get_name(v, f["from"] + i, u)
                    assert name != "OOB" and "stairs" in name, (
                        f"{stem}: no tread at V+{v} U+{u} y{f['from'] + i}")
                    props = _props(c, v, f["from"] + i, u)
                    assert props.get("facing") == f["facing"], (
                        f"{stem}: tread at y{f['from'] + i} faces {props.get('facing')} in a "
                        f"flight ascending {f['facing']}")
                    assert props.get("half") == "bottom", (
                        f"{stem}: tread at y{f['from'] + i} is a top half - you walk under it")


def _props(c, x, y, z) -> dict:
    i = c.get(x, y, z)
    if i < 0:
        return {}
    e = c.palette[i].value
    p = e.get("Properties")
    return {k: str(v.value) for k, v in p.value.items()} if p else {}


def test_every_tread_has_two_clear_courses_over_it(designs):
    """A buried flight audits as one clean solid: every cell legal, supported, affordable, one
    connected piece, and unwalkable. Headroom is the only thing that separates the two."""
    for stem, c in designs.items():
        for f in c.meta["flights"]:
            du = 1 if f["u_to"] > f["u_from"] else -1
            for v in range(f["band"][0], f["band"][1] + 1):
                for i in range(abs(f["u_to"] - f["u_from"]) + 1):
                    u, y = f["u_from"] + du * i, f["from"] + i
                    for dy in (1, 2):
                        assert not c.solid(v, y + dy, u), (
                            f"{stem}: the tread at V+{v} U+{u} y{y} has a block {dy} over it - "
                            f"the flight is buried")


def test_the_flights_climb_from_the_ground_to_the_deck_with_no_gap(designs):
    """A dog-leg is a chain: every flight must start where the last one finished, or the tower is
    a stack of stairs that do not meet."""
    for stem, c in designs.items():
        flights = c.meta["flights"]
        assert flights[0]["from"] == 0, f"{stem}: the first tread is not at ground level"
        for a, b in zip(flights, flights[1:]):
            assert b["from"] == a["to"] + 1, (
                f"{stem}: a flight ends at y{a['to']} and the next starts at y{b['from']}")
            assert a["facing"] != b["facing"], (
                f"{stem}: two flights in a row climb the same way - that is one long flight, not "
                f"a dog-leg, and the landing between them does nothing")
        assert flights[-1]["to"] == c.meta["deck_surface_above_lawn"] - 1, (
            f"{stem}: the last tread does not land on the deck")


def test_the_deck_is_a_room_and_not_a_ledge(designs, after):
    """A summit is somewhere for more than one person. Twenty standable cells is a landing; this
    demands a room, and a parapet a visitor cannot walk off."""
    for stem, c in designs.items():
        y, (v0, u0, v1, u1) = _deck(c)
        assert int(after[y, u0:u1 + 1, v0:v1 + 1].sum()) >= 40, f"{stem}: the deck is a ledge"
        # the rim is guarded: no reachable deck cell sits on the lot's own boundary line
        for u in range(u0, u1 + 1):
            for v in (v0, v1):
                assert not after[y, u, v], (
                    f"{stem}: a visitor can stand on the deck's outer line at V{v} U{u} - the "
                    f"parapet is missing and they can walk off it")


def test_you_cannot_climb_out_of_a_window(designs, after):
    """An opening that begins at the sill is a window a visitor steps into and falls out of.

    A one-course step is a legal step, so this is not hypothetical: the flood found it twice
    while this design was being written - once through a window slot reached sideways off a
    tread, and once through a loggia whose accent rhythm laid ONE full block in a run of
    `wall`, which is a stile a visitor climbs onto out of a balustrade they cannot climb. Both
    are what the sill guard and the three-course colonnette exist to stop, and this is what
    proves they worked.

    The one place a visitor is meant to leave the wall line is the Summit's declared bridge,
    which is named here rather than excused by a looser rule."""
    for stem, c in designs.items():
        v0, u0, _, _ = c.meta["lot"]
        sv, su = c.meta["shaft"]
        v1, u1 = v0 + sv - 1, u0 + su - 1
        top = GROUND_Y + int(c.meta["deck_surface_above_lawn"])
        crossing = GROUND_Y + c.meta["bridge"]["walk_y"] if "bridge" in c.meta else None
        for y in range(GROUND_Y + 2, top):
            if y == crossing:
                continue
            for u in range(u0, u1 + 1):
                for v in (v0, v1):
                    assert not after[y, u, v], (
                        f"{stem}: a visitor can stand in the wall line at V{v} U{u} park y{y}")
            for v in range(v0, v1 + 1):
                for u in (u0, u1):
                    assert not after[y, u, v], (
                        f"{stem}: a visitor can stand in the wall line at V{v} U{u} park y{y}")


def test_every_storey_is_a_room_you_can_stand_in(designs, after):
    """"Places to stand and look, NOT JUST TO ARRIVE AT." A stair with landings you cannot stop
    on is a fire escape, so every storey's floor has to be reachable floor, not a step."""
    for stem, c in designs.items():
        v0, u0, _, _ = c.meta["lot"]
        sv, su = c.meta["shaft"]
        rise, storeys = c.meta["rise"], c.meta["storeys"]
        for k in range(1, storeys):
            y = GROUND_Y + k * rise
            room = int(after[y, u0 + 1:u0 + su - 1, v0 + 1:v0 + sv - 1].sum())
            assert room >= 30, (
                f"{stem}: storey {k} at park y{y} has only {room} standable cells - it is a "
                f"landing, not a room")


def test_the_loggia_is_open_and_it_is_somewhere_to_stop(designs, after):
    """Each tower opens one whole face part way up. It is the single most useful thing on the
    climb - the view a visitor gets before they have finished climbing - and it is the easiest
    thing for a later pass to quietly wall back in."""
    for stem, c in designs.items():
        cfg = _cfg(stem)["params"]
        gs = cfg.get("loggia") or []
        assert gs, f"{stem} has no loggia; the climb has nowhere to stop and look"
        v0, u0, _, _ = c.meta["lot"]
        sv, su = c.meta["shaft"]
        for g in gs:
            y = GROUND_Y + int(g["level"]) * c.meta["rise"]
            face = g["face"]
            # the arcade's open courses, one in from the face, must be reachable AND open
            if face in ("west", "east"):
                v = v0 + (1 if face == "west" else sv - 2)
                line = [(u, v) for u in range(u0 + 1, u0 + su - 1)]
                wall = [(u, v0 + (0 if face == "west" else sv - 1)) for u, _ in line]
            else:
                u = u0 + (1 if face == "north" else su - 2)
                line = [(u, v) for v in range(v0 + 1, v0 + sv - 1)]
                wall = [(u0 + (0 if face == "north" else su - 1), v) for _, v in line]
            stood = sum(1 for (u, v) in line if after[y, u, v])
            assert stood >= len(line) // 2, (
                f"{stem}: only {stood} of {len(line)} cells along its {face} loggia can be "
                f"stood in")
            openness = sum(1 for (u, v) in wall if not c.solid(v - v0, y - GROUND_Y + 2, u - u0))
            assert openness >= len(wall) // 2, (
                f"{stem}: its {face} loggia is only {openness}/{len(wall)} open - it has been "
                f"walled back in and is a corridor with slots")


# --------------------------------------------------------------------------- the hard rules


def test_nothing_touches_a_street_a_path_a_plaza_a_verge_or_a_lamp(designs, street):
    """Rule one of the park, and the difference between this and the chaos Jack rejected.

    Measured cell by cell against the shipped `Park Ways`, not against a list of coordinates."""
    for stem, c in designs.items():
        hits = sorted({(u, v) for (_, u, v) in _cells(c) if street[u, v]})
        assert not hits, f"{stem} stands on {len(hits)} street columns, first {hits[:4]}"


def test_nothing_stands_in_the_rim_reserve_or_either_reach(designs):
    for stem, c in designs.items():
        v0, u0, v1, u1 = c.meta["lot"]
        assert v1 < pv.RIM_RESERVE[0], f"{stem} reaches the protected rim reserve"
        for a, b in pv.REACHES:
            assert not (u0 <= b and u1 >= a), f"{stem} stands in the reach U{a}-{b}"


def test_the_generator_refuses_a_lot_in_a_reserve():
    """The reserves are a REFUSAL at the door, not something an audit finds afterwards."""
    base = dict(_cfg("pf_vantage_midway_belvedere")["params"])
    with pytest.raises(ValueError, match="rim reserve"):
        pv.build({**base, "at": [160, 228]})
    with pytest.raises(ValueError, match="reach"):
        pv.build({**base, "at": [139, 400]})


def test_not_one_cell_leaves_its_own_lot(designs):
    for stem, c in designs.items():
        assert c.meta["outside_lot_refused"] == 0, (
            f"{stem} wanted {c.meta['outside_lot_refused']} cells outside its lot - a cropped "
            f"parapet is not a fault anything downstream can report")
        v0, u0, v1, u1 = c.meta["lot"]
        for (_, u, v) in _cells(c):
            assert v0 <= v <= v1 and u0 <= u <= u1, f"{stem}: a cell at V{v} U{u} is off its lot"


def test_nothing_shares_a_cell_with_anything_already_standing(designs, world):
    """Overlap 0 in context, with one exemption and one only: the lawn's own carpet trim."""
    names = world.names
    for stem, c in designs.items():
        bad = []
        for (y, u, v) in _cells(c):
            w = int(world.ids[y, u, v])
            if w and names[w].split(":")[-1] not in CLEARABLE:
                bad.append((y, u, v, names[w]))
        assert not bad, f"{stem} collides with {len(bad)} standing blocks, first {bad[:3]}"


def test_no_two_vantages_share_a_cell(designs):
    seen = {}
    for stem, c in designs.items():
        for k in _cells(c):
            assert k not in seen, f"{stem} and {seen[k]} both claim {k}"
            seen[k] = stem


def test_every_design_stands_on_the_lawn_and_never_replaces_it(designs, world):
    """Canvas y0 is the first course ABOVE the lawn, so a vantage owns no ground at all."""
    for stem, c in designs.items():
        assert c.world_origin[1] == pv.ANCHOR[1], f"{stem} does not start above the lawn"
        lowest = min(y for (y, _, _) in _cells(c))
        assert lowest == GROUND_Y, f"{stem}'s lowest cell is at park y{lowest}"


def test_each_tower_is_one_piece_with_nothing_to_scaffold(designs, world):
    """ONE 6-CONNECTED PIECE, and every cell with a face to place it against.

    This is the check that found four real defects nothing else could see: a hip roof built as
    concentric rings (179 cells of dark oak touching only diagonally), a cabin lantern hung in
    mid-air, a bench laid over a stair well, and sixteen three-cell islands of tread where a
    window slot had been opened through the stringer the flight hangs on. Every one of them
    audited clean and would have needed scaffolding to build."""
    N6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    wocc = world.ids != 0
    for stem, c in designs.items():
        cells = set(_cells(c))
        floating = [k for k in cells if not any(
            (k[0] + d[0], k[1] + d[1], k[2] + d[2]) in cells
            or wocc[k[0] + d[0], k[1] + d[1], k[2] + d[2]] for d in N6)]
        assert not floating, f"{stem}: {len(floating)} cells have nothing to place against"
        seen, start = set(), next(iter(cells))
        dq = collections.deque([start])
        seen.add(start)
        while dq:
            y, u, v = dq.popleft()
            for d in N6:
                n = (y + d[0], u + d[1], v + d[2])
                if n in cells and n not in seen:
                    seen.add(n)
                    dq.append(n)
        assert len(seen) == len(cells), (
            f"{stem} is {len(cells) - len(seen)} cells short of one piece - a stray group is "
            f"joined to the tower by nothing but a diagonal")


def test_a_loggia_may_not_be_cut_through_its_own_stairs_stringer():
    """The refusal, not the repair. Patching one course of an open arcade leaves a block in the
    middle of it, which is a step a visitor climbs onto and walks off the tower; leaving the
    arcade open takes the stringer out from under the flight. So the combination raises."""
    base = dict(_cfg("pf_vantage_midway_belvedere")["params"])
    with pytest.raises(ValueError, match="stringer"):
        pv.build({**base, "stair_from": "west"})
    # ...and the same tower is legal the moment the flight climbs the other wall
    assert pv.build({**base, "stair_from": "east"}) is not None


# --------------------------------------------------------------------------- materials


def test_every_block_is_1_19_legal_spendable_and_not_a_currency(designs):
    """Rule 12 and rule 16 together: the client is 26.2 and the server is 1.19, and dirt is money.

    Both are asked of the REGISTRY rather than of a list in this file."""
    for stem, c in designs.items():
        for name in {n for n in _cells(c).values()}:
            assert blocks.exists(name), f"{stem}: {name} is not a block"
            assert blocks.available(name), f"{stem}: {name} is not on the 1.19 server"
            assert blocks.spendable(name), f"{stem}: {name} is currency on this economy"
            assert "dirt" not in name and "grass" not in name and "podzol" not in name, (
                f"{stem}: {name} is in the dirt family")
            assert "cobblestone" not in name, f"{stem}: {name} is cobblestone"


def test_the_bulk_is_cheap_and_nothing_is_expensive(designs):
    """The park's material policy: cheap in bulk, `ok` only as trim, expensive never."""
    for stem, c in designs.items():
        tally = collections.Counter(_cells(c).values())
        tiers = collections.Counter()
        for name, n in tally.items():
            tiers[palette.tier(name)] += n
        assert tiers["expensive"] == 0, f"{stem} spends {tiers['expensive']} expensive blocks"
        total = sum(tiers.values())
        assert tiers["cheap"] / total > 0.8, (
            f"{stem} is only {tiers['cheap'] / total:.0%} cheap-tier; the bulk of a tower must "
            f"not be a paving material")


def test_each_land_keeps_its_own_materials(designs):
    """Three towers, three palettes - or the park has one building three times.

    The materials that tie a tower to the ground it stands on are READ off `parkways.LANDS` and
    never retyped here; what this pins is that they really are, and that the three walls differ."""
    walls = {}
    for stem, c in designs.items():
        land = c.meta["land"]
        pal = pv._pal(land)
        w = WAYS_LANDS[land]
        assert pal["thresh"] == w["core"] and pal["light"] == w["light"], (
            f"{stem}: the tower has stopped inheriting its land's own ground palette - its deck "
            f"is paved in that land's own street material and lit with that land's own light")
        walls[land] = pal["field"]
        used = set(_cells(c).values())
        assert pal["field"] in used and pal["accent"] in used
    assert len(set(walls.values())) >= 2, f"the three lands share one wall material: {walls}"
    assert "spruce" in str(pv._pal("frontier")), "the Frontier has lost its timber"
    assert pv._pal("midway")["trim"] == "white_wool", "the Midway has lost its white pilaster"
    assert pv._pal("prismworks")["band"] == "smooth_basalt", (
        "Prismworks has lost its basalt pier")


def test_the_value_ladder_each_land_draws_its_lines_with_is_real(designs):
    """MEASURED, because this repo has three separate times concluded that this economy has no
    value contrast - and all three measurements were taken inside ONE material family, where a
    ladder cannot exist by construction."""
    for land in ("frontier", "midway", "prismworks"):
        pal = pv._pal(land)
        lum = {k: sum(blocks.color(pal[k], "side")) / 3 for k in ("plinth", "field", "accent")}
        # The pairs that have to READ are the ones that meet on the wall: the field against its
        # own base course, and the field against the crown band. The plinth and the accent never
        # touch - they are sixty courses apart - so they are not compared.
        for other in ("plinth", "accent"):
            gap = abs(lum["field"] - lum[other])
            assert gap >= 15, (
                f"{land}: `{other}` is {gap:.0f} of luminance off the field it is drawn on, and "
                f"below about 15 a course of trim stops being a line: {lum}")


def test_no_mechanism_is_claimed(designs):
    """These are architecture. A redstone component here would be a machine nobody has judged by
    simulation, and this repo cut two finished casino games rather than ship one."""
    parts = ("redstone", "repeater", "comparator", "observer", "piston", "dispenser", "dropper",
             "hopper", "lever", "button", "pressure_plate", "target", "note_block", "rail")
    for stem, c in designs.items():
        for name in set(_cells(c).values()):
            assert not any(p in name for p in parts), f"{stem} places a {name}"
        assert any("no mechanism" in r for r in c.meta["requires_in_game"])


# --------------------------------------------------------------------------- the config

def test_every_config_names_this_generator_and_locks_nothing(designs):
    for stem in CONFIGS:
        cfg = _cfg(stem)
        assert cfg["gen"] == "park_vantage"
        assert cfg["origin_lock"] is False, (
            f"{stem}: a park module is placed at its own lot corner, never at the origin lock")
        assert cfg["finish"]["verify_against"].endswith("Park Complete.litematic")
        assert cfg["finish"]["verify_replaceable"] == ["moss_carpet"]
        assert cfg["name"].startswith("PF Vantage ")


def test_the_bridge_is_declared_by_exactly_one_design(designs):
    bridged = [s for s, c in designs.items() if "bridge" in c.meta]
    assert bridged == ["pf_vantage_prism_summit"], (
        f"a bridge onto somebody else's building is a deliberate act, not a default: {bridged}")
    b = designs["pf_vantage_prism_summit"].meta["bridge"]
    assert b["walk_y"] == 13, (
        f"the bridge walks at canvas y{b['walk_y']}; the Prism Ascent's podium roof is walked at "
        f"canvas y13 (park y26) and the two must be the same course")
