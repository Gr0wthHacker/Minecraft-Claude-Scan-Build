"""The Park Line: the rail rules, the corridor, the three stations, and the material policy.

**EVERY RAIL RULE HERE IS ASSERTED RATHER THAN LOOKED AT, AND THAT IS THE POINT.** `shape` and
`powered` are DERIVED by the game, `work.INTENTIONAL` does not compare them, and `render3d` draws a
rail facing the wrong way exactly as it draws one facing the right way - so a line that cannot be
ridden passes the audit, the bill of materials, the component count and every render in this repo.
The only checks that can catch it are these.

The power is checked by SIMULATION, not by counting redstone blocks. `mcbuild.circuit` models the
real rule - a powered rail carries its own state eight rails past a source - which is the only way
to answer "is any cell of this line a brake" and the only way to prove that the station brakes are
dead when their levers are down and live when they are up.
"""
from __future__ import annotations

import pathlib

import pytest
import yaml

from mcbuild import audit as audit_mod, blocks, palette
from mcbuild.circuit import Circuit
from mcbuild.gen import parkrail
from mcbuild.gen.railspiral import runs_of, shapes_for

CONFIG = pathlib.Path(__file__).resolve().parents[1] / "configs" / "park_rail.yaml"

#: Blocks the game gained AFTER 1.19. The server is 1.19 and the client is 26.2, so any of these
#: is in the registry, has legal states, renders in a card, passes every audit - and cannot be
#: placed. `blocks.available` cannot be used as the gate here: the allowlist is provisional, built
#: from what captures happen to hold, and would reject `allium`.
POST_1_19 = {
    "mud", "mud_bricks", "packed_mud", "cherry_planks", "cherry_log", "bamboo_planks",
    "pale_oak_planks", "pale_oak_log", "tuff_bricks", "polished_tuff", "chiseled_tuff",
    "copper_bulb", "copper_grate", "chiseled_copper", "suspicious_sand", "suspicious_gravel",
    "calibrated_sculk_sensor", "crafter", "trial_spawner", "vault", "heavy_core", "resin_block",
    "pink_petals", "torchflower", "pitcher_plant", "short_grass",
}

#: Jack rejected an earlier park at 17.7% of this block. It is banned outright, not budgeted.
BANNED = {"cobblestone", "mossy_cobblestone", "cobblestone_slab", "cobblestone_stairs",
          "cobblestone_wall"}

#: The slim vocabulary. A post, a railing or a balustrade must come out of this list - "nothing may
#: be a full-block pillar where a slim block will do", and `render3d` draws every one of them as a
#: full cube, so slimness is checked by BLOCK TYPE and can never be checked by looking.
SLIM_SUFFIX = ("_wall", "_fence", "_pane", "_bars", "_trapdoor", "_slab", "_stairs", "_sign",
               "_rod", "_chain")


def _params() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["params"]


@pytest.fixture(scope="module")
def canvas():
    return parkrail.build(_params())


@pytest.fixture(scope="module")
def model(canvas):
    return canvas.to_model()


@pytest.fixture(scope="module")
def meta(canvas):
    return canvas.meta


@pytest.fixture(scope="module")
def cells():
    return parkrail.plan(_params())


def _named(model):
    """{(x, y, z): bare block name} for every solid cell."""
    import numpy as np
    names = [n.split(":")[-1].split("[")[0] for n in model.names]
    out = {}
    ys, zs, xs = np.where(model.solid())
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        out[(x, y, z)] = names[int(model.ids[y, z, x])]
    return out


def _props(model, x, y, z):
    return model.props_at(x, y, z)


# ------------------------------------------------------------------ the rail rules


def test_a_powered_rail_cannot_curve_and_the_registry_is_what_says_so():
    """The rule the whole line's shape is planned around, read off `blocks.json` not remembered."""
    powered = set(blocks.props("powered_rail")["shape"])
    plain = set(blocks.props("rail")["shape"])
    curves = {"south_east", "south_west", "north_west", "north_east"}
    assert curves <= plain, "a plain rail is the only one that can turn"
    assert not (curves & powered), "a powered rail has no curve shape at all"
    assert all(blocks.validate("powered_rail", {"shape": s}) == [] for s in powered)
    for s in curves:
        assert blocks.validate("powered_rail", {"shape": s}), \
            "a curved powered rail must be rejected by the registry, or nothing else here is safe"


def test_the_line_has_no_corner_so_it_costs_no_iron(cells, model):
    """Iron is the scarce metal here and gold is farmable, so a corner is the only expensive cell.

    This line lies on one axis and turns nowhere, which is why every rail on it is a powered rail
    and its iron cost is zero. If a future corridor bends, this test is the one that will fail
    first, and the fix is a PLAIN rail at the bend - never a powered one.
    """
    assert [c for c in cells if c[3]] == [], "the line records no corner"
    assert runs_of(cells) == [(0, len(cells))], "no corner means exactly one powered run"
    named = _named(model)
    assert not any(n == "rail" for n in named.values()), "no plain rail: nothing turns"


def test_every_rail_is_a_powered_rail_in_a_legal_straight_state(model, cells):
    named = _named(model)
    rails = {p: n for p, n in named.items() if n.endswith("rail")}
    assert len(rails) == len(cells)
    for (x, y, z), name in rails.items():
        assert name == "powered_rail"
        props = _props(model, x, y, z)
        assert blocks.validate(name, props) == [], f"{name}{props} at {(x, y, z)}"
        assert props["shape"] in ("north_south", "east_west"), \
            "a level straight line may only take a straight shape"


def test_shapes_for_gives_a_corner_a_curve_and_a_slope_an_ascent():
    """The shared implementation is exercised on a bent and a sloped path, because a straight line
    proves nothing about either - `transit` and `railspiral` lean on the same function."""
    bend = [(0, 9, 0, False), (0, 9, 1, False), (0, 9, 2, True), (1, 9, 2, False)]
    got = shapes_for(bend)
    assert got[2] in ("south_east", "south_west", "north_west", "north_east")
    assert blocks.validate("rail", {"shape": got[2]}) == []
    assert blocks.validate("powered_rail", {"shape": got[2]}), \
        "the corner shape must be one a powered rail cannot hold - that is the whole rule"
    slope = [(0, 9, 0, False), (0, 10, 1, False), (0, 10, 2, False)]
    assert shapes_for(slope)[0] == "ascending_south"


def test_never_descend_into_a_corner(cells):
    """A curve has no ascending shape, so a corner and both of its neighbours must share one
    height. Built wrong the game re-derives the turn as a slope, the turn is lost and the line
    dead-ends - and nothing in the model looks any different."""
    for i, (_x, y, _z, corner) in enumerate(cells):
        if not corner:
            continue
        for j in (i - 1, i + 1):
            if 0 <= j < len(cells):
                assert cells[j][1] == y, "a corner and its neighbours must be level"
    assert len({c[1] for c in cells}) == 1, "this line is dead level end to end"


def test_the_line_is_unbroken_and_every_rail_stands_on_a_bed(model, cells, meta):
    """A TRACK CELL IS NOT OPTIONAL. A gap in a line eight courses over the ground is a cart in
    mid-air, and a broken line still audits as one clean solid with nothing to say about it."""
    named = _named(model)
    zs = sorted(z for (_x, _y, z), n in named.items() if n == "powered_rail")
    assert zs == list(range(zs[0], zs[0] + len(zs))), "no gap anywhere in the run"
    for (x, y, z, _c) in cells:
        assert named.get((x, y, z)) == "powered_rail"
        bed = named.get((x, y - 1, z))
        assert bed is not None, f"the rail at {(x, y, z)} stands on air"
        assert blocks.is_full_cube(bed), f"the bed at {(x, y - 1, z)} is {bed}, not a full block"


def test_a_track_cell_that_cannot_be_placed_is_an_error_and_not_a_skip():
    """A design may yield a lamp; it may never yield a rail."""
    bad = {**_params(), "track_v": 99}
    with pytest.raises(ValueError):
        parkrail.plan(bad)
    short = {**_params(), "bounds": [0, 0, 7, 5]}
    with pytest.raises(ValueError):
        parkrail.plan(short)


def test_a_terminus_needs_a_stop_block_at_both_ends(model, cells, meta):
    """A stationary cart on a powered rail launches AWAY from the adjacent solid block, so with
    neither end blocked the line only runs whichever way you happened to shove it."""
    named = _named(model)
    assert meta["stop_blocks"] == 2
    (x0, y0, z0, _), (x1, y1, z1, _) = cells[0], cells[-1]
    for x, y, z in ((x0, y0, z0 - 1), (x1, y1, z1 + 1)):
        stop = named.get((x, y, z))
        assert stop is not None and blocks.is_full_cube(stop), \
            f"no stop block at {(x, y, z)}: the cart would only ever run one way"


# ------------------------------------------------------------------ the power, by simulation


@pytest.fixture(scope="module")
def sim(model):
    return Circuit.of(model)


def _rails(sim):
    return [p for p, cell in sim.cells.items() if cell.name == "powered_rail"]


def _levers(sim):
    return [p for p, cell in sim.cells.items() if cell.name == "lever"]


def test_an_unpowered_powered_rail_is_a_brake_so_the_line_is_live_end_to_end(sim, meta):
    """With every signal lever up, not one cell of six hundred is a brake.

    Counted rather than reasoned about: `power_every` alone does not prove this, because a powered
    rail carries its own state at most eight rails past a source and the station dead zones move
    every source near them.
    """
    rails, levers = _rails(sim), _levers(sim)
    assert len(rails) == meta["track_cells"]
    assert len(levers) == len(meta["stations"]) == 3
    for lv in levers:
        sim.set(lv, True)
    sim.run(ticks=4)
    assert [p for p in rails if not sim.powered(p)] == []


def test_a_station_lever_down_stops_a_cart_exactly_on_its_own_platform(model, meta):
    """The brake, both ways round, which is the only reason a station can be boarded at all.

    A continuously powered line cannot be got on to - the cart never stops. What is asserted is
    that the dead stretch exists, that it is the size the design says, and that it is centred on
    the platform rather than somewhere in the open.
    """
    sim = Circuit.of(model)
    rails = _rails(sim)
    for lv in _levers(sim):
        sim.set(lv, False)
    sim.run(ticks=4)
    dead = sorted(z for (_x, _y, z) in rails if not sim.powered((_x, _y, z)))
    groups: list[list[int]] = []
    for z in dead:
        if groups and z == groups[-1][-1] + 1:
            groups[-1].append(z)
        else:
            groups.append([z])
    half = int(_params()["brake_half"])
    assert len(groups) == 3, "one dead zone per station, and nowhere else"
    centres = sorted(s["at_u"] for s in meta["stations"])
    for g, centre in zip(groups, centres):
        assert len(g) == 2 * half + 1
        assert (g[0] + g[-1]) // 2 == centre, "the cart must stop AT the platform"


def test_the_quiet_band_is_arithmetic_and_the_arithmetic_is_in_one_place():
    """`_sources` owns the whole brake geometry, so moving `brake_half` moves it correctly."""
    n, every, half = 400, 8, 8
    picks, quiet = parkrail._sources(n, every, [200], half)
    assert quiet == set(range(200 - 2 * half, 200 + 2 * half + 1))
    assert not (picks & quiet), "no source may stand inside the band that must go dead"
    assert 200 - 2 * half - 1 in picks and 200 + 2 * half + 1 in picks, \
        "the band's two shoulders are FORCED, or the lever cannot bridge the gap when it is up"
    live = sorted(i for i in picks)
    for a, b in zip(live, live[1:]):
        if not (set(range(a + 1, b)) & quiet):
            assert b - a <= every, f"a {b - a}-cell gap between sources leaves a dead rail"


# ------------------------------------------------------------------ the corridor


def test_nothing_leaves_the_corridor(model, meta):
    """V0-7 for the full six hundred, and NOT ONE CELL AT Y0: the lawn under the viaduct belongs to
    `Park Ways`, so the two designs share the strip without contesting a single cell of it."""
    v0, u0, v1, u1 = meta["bounds"]
    sx, sy, sz = model.shape_xyz
    assert (sx, sz) == (v1 - v0 + 1, u1 - u0 + 1) == (8, 600)
    named = _named(model)
    assert all(0 <= x < 8 for (x, _y, _z) in named)
    assert not any(y == 0 for (_x, y, _z) in named), \
        "y0 is the park's own lawn course and this design never claims it"


def test_it_is_one_piece_with_no_placement_problems(model):
    res = audit_mod.audit(model, ground=False)
    assert res.problems == [], "\n".join(str(p) for p in res.problems[:10])
    assert len(res.components) == 1, f"components: {sorted(res.components, reverse=True)[:6]}"


# ------------------------------------------------------------------ the three stations


def test_there_are_three_stations_one_per_land_each_fully_fitted(meta):
    detail = meta["station_detail"]
    assert len(detail) == 3
    assert sorted(s["land"] for s in detail) == ["frontier", "midway", "prismworks"]
    for s in detail:
        assert s["lever"], f"{s['title']} has no signal lever, so its brake cannot be released"
        assert s["board"], f"{s['title']} has no departure board"
        assert s["name_signs"] >= 1, f"{s['title']} is not named anywhere"
        assert s["platform"] >= 21
        assert s["lanterns"] >= 3


def test_a_station_wears_its_own_land_and_no_other(model, meta):
    """Three stations, not one station painted three colours: each is built out of the materials
    `parkways` gives its own land, so a visitor can tell where they are with their eyes shut."""
    import numpy as np
    names = [n.split(":")[-1].split("[")[0] for n in model.names]
    half = int(_params()["station_half"])
    unique = {}
    for land, pal in parkrail.SPAN.items():
        others = {b for other, q in parkrail.SPAN.items() if other != land for b in q.values()}
        unique[land] = {b for b in pal.values() if b not in others}
        assert unique[land], f"{land} shares every block with another land"
    for s in meta["station_detail"]:
        lo, hi = s["at_u"] - half, s["at_u"] + half
        here = {names[int(i)] for i in np.unique(model.ids[:, lo:hi + 1, :]) if i}
        assert here & unique[s["land"]], f"{s['title']} shows nothing of its own land"
        for other, own in unique.items():
            if other != s["land"]:
                assert not (here & own), f"{s['title']} is wearing {other}'s materials"


def _local(p):
    """(stair columns, track column, park face) in MODEL coordinates.

    Everything in the config is absolute V; the model's x is V minus the corridor's own v0.
    Those were the same number while the corridor started at V0, so three tests hard-coded
    ``x >= 5`` and ``x in (6, 7)`` - and every one of them read a different part of the viaduct
    the moment the corridor moved to the rim and the park side mirrored with it. Derived from
    `parkrail._sides` so the test and the build cannot drift.
    """
    from mcbuild.gen.parkrail import _sides, PARKRAIL
    v0 = p["bounds"][0]
    side, park_edge, _void = _sides({**PARKRAIL, **p})
    w = max(2, int(p.get("stair_w", PARKRAIL.get("stair_w", 2))))
    stair = tuple(sorted(park_edge - side * k - v0 for k in range(w)))
    return stair, int(p["track_v"]) - v0, park_edge - v0


def test_every_tread_of_every_flight_ascends_toward_the_platform(model, meta):
    """A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D, half=bottom.

    Built the other way round the risers face into the descent and you cannot walk up it - and our
    renderer draws both directions identically, which is why this is asserted and never eyeballed.
    """
    named = _named(model)
    p = _params()
    ground_y, deck_y = int(p["ground_y"]), int(p["deck_y"])
    stair_x, _track_x, _face = _local(p)
    for s in meta["station_detail"]:
        lo, hi = s["stair_from_u"], s["stair_to_u"]
        ascend = "north" if s["at_u"] < lo else "south"
        seen = {}
        for (x, y, z), n in named.items():
            if lo <= z <= hi and n.endswith("_stairs") and x in stair_x:
                props = _props(model, x, y, z)
                assert props["half"] == "bottom", f"{s['title']} tread at {(x, y, z)} is upside down"
                assert props["facing"] == ascend, \
                    f"{s['title']} tread at {(x, y, z)} faces {props['facing']}, not {ascend}"
                seen.setdefault(z, set()).add(y)
        assert len(seen) == deck_y - ground_y + 1 == hi - lo + 1
        heights = [min(seen[z]) for z in sorted(seen)]
        if ascend == "north":                     # the flight descends toward +U
            assert heights == sorted(heights, reverse=True)
        else:
            assert heights == sorted(heights)
        assert min(heights) == ground_y and max(heights) == deck_y, \
            "a flight has to reach the lawn at one end and the deck at the other"


def test_a_flight_you_cannot_walk_down_is_not_a_flight(model, meta):
    """The courses over every tread must be air, or the deck the flight descends through is a
    ceiling - a stairwell is a HOLE, and a buried flight audits as one clean solid."""
    named = _named(model)
    p = _params()
    walk_y = int(p["deck_y"]) + 1
    stair_x, _track_x, _face = _local(p)
    for s in meta["station_detail"]:
        for z in range(s["stair_from_u"], s["stair_to_u"] + 1):
            for x in stair_x:
                # THE TOPMOST STAIR IN THE COLUMN IS THE TREAD. Everything under it is the
                # stringer the flight stands on - masonry, and meant to be there; the first
                # version of this test took the LOWEST block in the column and read the stringer
                # as a burial, which is a test failing a correct build.
                tread = max(y for (xx, y, zz), n in named.items()
                            if (xx, zz) == (x, z) and n.endswith("_stairs"))
                for y in range(tread + 1, walk_y + 2):
                    assert (x, y, z) not in named, \
                        f"{s['title']}: the flight is buried at {(x, y, z)}"


def test_the_signal_lever_can_actually_reach_the_track(model, meta):
    """A lever powers the block it is attached to, and a powered block beside a powered rail
    energises it. Placed one cell further back it powers nothing and the station never releases."""
    named = _named(model)
    p = _params()
    _stair_x, track_x, _face = _local(p)
    walk_y = int(p["deck_y"]) + 1
    levers = [(x, y, z) for (x, y, z), n in named.items() if n == "lever"]
    assert len(levers) == 3
    for x, y, z in levers:
        assert _props(model, x, y, z)["face"] == "floor"
        below = named.get((x, y - 1, z))
        assert below is not None and blocks.is_full_cube(below), "a lever needs a pedestal"
        assert abs(x - track_x) == 1 and y - 1 == walk_y, \
            "the pedestal must sit beside the rail, in the rail's own course"


# ------------------------------------------------------------------ the material policy


def test_every_block_is_real_1_19_and_spendable(model):
    """`grass_block` and every form of dirt are CURRENCY on this server: real, legal, placeable,
    and money. That is a third axis beside "does it exist" and "does 1.19 have it"."""
    for name in {n.split(":")[-1].split("[")[0] for n in model.names} - {"air"}:
        assert blocks.exists(name), name
        assert name not in POST_1_19, f"{name} is newer than the 1.19 server"
        assert blocks.spendable(name), f"{name} is currency on this server"
        assert not blocks.falls(name), f"{name} falls, and most of this design has air under it"


def test_the_park_s_banned_block_appears_nowhere(model):
    got = {n.split(":")[-1].split("[")[0] for n in model.names} & BANNED
    assert not got, f"cobblestone was rejected once at 17.7% of a park: {sorted(got)}"


def test_the_tier_split_spends_nothing_expensive(model):
    res = audit_mod.audit(model, ground=False)
    total = res.blocks
    expensive = res.tiers.get("expensive", 0)
    ok = res.tiers.get("ok", 0)
    assert expensive == 0, "nothing expensive is declared functional here, so nothing is spent"
    assert 0.08 <= ok / total <= 0.16, f"ok tier is {ok / total:.1%}"
    assert res.tiers.get("cheap", 0) / total >= 0.78


def test_a_post_is_a_slim_block_and_never_a_pillar(model, meta):
    """`render3d` draws a fence, a wall and a rod as full cubes, so this can only ever be checked
    by BLOCK TYPE. Every parapet, portal leg and canopy post is one of the slim families."""
    for land, pal in parkrail.SPAN.items():
        for key in ("parapet", "post"):
            assert pal[key].endswith(SLIM_SUFFIX), f"{land}.{key} is {pal[key]}, a full block"


def test_the_lights_that_carry_the_line_cost_no_metal(model, meta):
    """A lantern is an iron ingot each. The deck and the arcade are lit by flush froglights - the
    island's own idiom - so the metal goes on the handful of lanterns that hang, and nowhere else.
    """
    named = _named(model)
    frog = sum(1 for n in named.values() if n == parkrail.FLUSH_LIGHT)
    metal = sum(1 for n in named.values() if n in ("lantern", "soul_lantern"))
    assert frog >= meta["flush_lights"]
    assert frog > metal, "most of the light on this line must cost nothing"
    assert metal < 60, f"{metal} lanterns is more iron than the whole railway"


# ------------------------------------------------------------------ the viaduct


def test_every_pier_carries_a_gate_that_reaches_the_park_face(model, meta):
    """Cut through the middle instead, the arcade under the deck is a tunnel with a solid wall at
    both ends of it: walkable once you are inside, and nowhere on six hundred blocks to get in."""
    named = _named(model)
    p = _params()
    v0, u0, v1, u1 = p["bounds"]
    gate_lo, gate_hi = p["gate_v"]
    _stair_x, _track_x, face = _local(p)
    assert face + v0 in (gate_lo, gate_hi), "the gate must reach the corridor's park face"
    # ...and from here on in MODEL coordinates. `named` is keyed by the canvas x, so comparing it
    # against an absolute V made `open_here` list three columns that are not in the model at all -
    # every one of them trivially "open", which is a gate check that cannot fail.
    gate_lo, gate_hi = sorted((gate_lo - v0, gate_hi - v0))
    void_x = (v1 if face + v0 == v0 else v0) - v0
    ground_y, bay, pier_u = int(p["ground_y"]), int(p["bay"]), int(p["pier_u"])
    for b0 in range(u0, u1 + 1, bay):
        for u in range(b0, min(b0 + pier_u, u1 + 1)):
            # NOT EVERY COLUMN OF EVERY GATE: a station's own flight lands on masonry that
            # legitimately refills the two columns nearest the park, so the gate under a platform
            # is one cell wide rather than three. What must be true everywhere is that SOMETHING
            # is open - and that the walk it belongs to actually runs, which is the next test.
            # A WALK NEEDS HEADROOM OVER ITS OWN FLOOR, NOT AN EMPTY COLUMN. Outside a station
            # the arcade's floor is the lawn one course below this design, so ground_y is the
            # cell you stand in and an empty column is the right test. At a station the forecourt
            # is a RAISED apron - which is what Jack asked the entries for - so the floor is
            # ground_y and you stand on top of it. Demanding an empty column reads a platform as
            # a wall, so what is asserted is the property that actually matters: somewhere in the
            # gate band there is a column with two clear courses above whatever its floor is.
            def _clear_above(v, floor):
                return all((v, y, u) not in named
                           for y in range(floor + 1, floor + int(p["gate_h"])))
            open_here = [v for v in range(gate_lo, gate_hi + 1)
                         if ((v, ground_y, u) not in named and _clear_above(v, ground_y - 1))
                         or ((v, ground_y, u) in named and _clear_above(v, ground_y))]
            assert open_here, f"the pier at u={u} is not walkable through at all"
            assert (void_x, ground_y, u) in named, "...and the rest of the pier still stands"


def test_the_arcade_under_the_deck_is_walkable_end_to_end(model, meta):
    """THE REAL PROPERTY IS THE WALK, NOT THE HOLE. A gate in every pier proves nothing on its own:
    a doorway that lines up with nothing is a hole rather than an arcade. So the ground course is
    flooded from one end of the corridor to the other and the answer has to come out the far side.
    """
    named = _named(model)
    p = _params()
    v0, u0, v1, u1 = p["bounds"]
    g = int(p["ground_y"])
    free = {(v, u) for u in range(u0, u1 + 1) for v in range(v0, v1 + 1)
            if (v, g, u) not in named and (v, g + 1, u) not in named}
    seen = {c for c in free if c[1] == u0}
    stack = list(seen)
    while stack:
        v, u = stack.pop()
        for nb in ((v + 1, u), (v - 1, u), (v, u + 1), (v, u - 1)):
            if nb in free and nb not in seen:
                seen.add(nb)
                stack.append(nb)
    assert any(u == u1 for _v, u in seen), "the arcade does not reach the far end of the park"
    assert len({u for _v, u in seen}) == u1 - u0 + 1, \
        "the walk under the viaduct breaks somewhere along its own length"


def test_the_arch_springs_from_the_pier_and_crowns_under_the_deck():
    """A profile that never reaches its crown is a lintel with the corners chamfered off - which is
    what eight courses of deck gave, and what the elevation was rebuilt at twelve to fix."""
    p = _params()
    span, ys = int(p["bay"]) - int(p["pier_u"]), int(p["spring_y"])
    yc = int(p["deck_y"]) - 1 - int(p["crown_gap"])
    prof = [parkrail._intrados(i, span, ys, yc) for i in range(span)]
    assert prof == prof[::-1], "an arch is symmetric about its own crown"
    assert max(prof) == yc and prof[0] < yc and prof[-1] < yc
    assert prof[span // 2] == yc, "the crown has to be at mid-span"
    assert all(b - a <= 2 for a, b in zip(prof, prof[1:span // 2 + 1])), \
        "a step of three is a staircase, not a curve"


def test_you_can_walk_from_the_park_onto_every_platform():
    """Jack: "the access to the railways stairs are on the wrong side for us to actually access."

    He was right, and it was worse than a side. The flight lands on the reserve lawn at V171 and
    between there and the service lane are FOURTEEN BLOCKS OF BARE GRASS, with the rim's posts
    every six along the way - no route at all, and the lane it eventually reaches is back-of-house.
    Each station's portal now sits on the column of a walk carried through the rim from an avenue,
    so a guest steps off the park's own street into the station.

    **THIS IS A COMPOSITE WALK AND IT HAS TO BE.** Neither design can answer it alone: the railway
    audits clean with no way to reach it, and the ground layer audits clean with nothing to reach.
    Cross-design access is a different question from a per-design audit, exactly as cross-design
    overlap is - and this project has been bitten by that twice.
    """
    from collections import deque
    from pathlib import Path
    from mcbuild import schem

    root = Path(__file__).resolve().parents[1]
    ways, rail = root / "out" / "Park Ways.litematic", root / "out" / "Park Rail.litematic"
    if not (ways.exists() and rail.exists()):
        pytest.skip("the shipped park is not built here")
    w, r = schem.load(str(ways)), schem.load(str(rail))
    ws, rs = w.solid(), r.solid()
    v0 = _params()["bounds"][0]
    SX, SZ, H = ws.shape[2], ws.shape[1], max(ws.shape[0], rs.shape[0])

    def solid(v, y, u):
        if not (0 <= v < SX and 0 <= u < SZ and 0 <= y < H):
            return True
        if v0 <= v < v0 + rs.shape[2] and y < rs.shape[0] and rs[y, u, v - v0]:
            return True
        return bool(y < ws.shape[0] and ws[y, u, v])

    def stand(v, y, u):                       # feet at y, head clear, floor under
        return solid(v, y - 1, u) and not solid(v, y, u) and not solid(v, y + 1, u)

    for st in _meta_stations():
        start = next(((20, y, st["portal_u"]) for y in range(1, 8)
                      if stand(20, y, st["portal_u"])), None)
        assert start, f"{st['title']}: nowhere to stand on the spine verge at its own avenue"
        # BOUNDED, AND IT STOPS THE MOMENT IT ARRIVES. An unbounded flood over this park is a
        # hundred and twenty thousand standable cells per station and minutes of wall clock; the
        # question is only whether a route EXISTS, so the search is corridor-shaped - within
        # sixteen columns of the station's own walk - and returns on the first cell of deck.
        deck_y = int(_params()["deck_y"]) + 1
        seen, q, found = {start}, deque([start]), False
        while q and not found:
            v, y, u = q.popleft()
            for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for dy in (0, 1, -1):         # a step up or down of one, never a fall
                    n = (v + dv, y + dy, u + du)
                    if n in seen or not (0 <= n[0] < SX and 0 <= n[2] < SZ):
                        continue
                    if abs(n[2] - st["portal_u"]) > 16 and n[1] < deck_y:
                        continue
                    if not stand(*n):
                        continue
                    if n[1] >= deck_y:
                        found = True
                        break
                    seen.add(n)
                    q.append(n)
                if found:
                    break
        assert found, f"{st['title']}: the platform cannot be reached on foot from the spine"


def _meta_stations():
    """Each station's title and the U its PORTAL stands on - derived, never retyped."""
    p = _params()
    half, hh = int(p["station_half"]), int(p.get("head_half", 5))
    out = []
    for s in p["stations"]:
        step = 1 if int(s.get("stair", 1)) >= 0 else -1
        out.append({"title": s["title"], "portal_u": int(s["at_u"]) + step * (half + hh + 1)})
    return out


def test_every_portal_stands_on_a_walk_the_ground_layer_draws():
    """The two configs have to agree about three numbers and nothing enforces it but this.

    Move `rail_stations` in `configs/park_ways.yaml` without moving the stations and the walk
    arrives BESIDE the station - which looks entirely correct in every render, because a walk to
    nowhere and a walk to a door are the same paving.
    """
    import yaml
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    ways = yaml.safe_load((root / "configs" / "park_ways.yaml").read_text(encoding="utf-8"))
    walks = set(ways["params"]["parts"][0]["params"]["rail_stations"])
    portals = {s["portal_u"] for s in _meta_stations()}
    assert portals == walks, f"portals at {sorted(portals)} against walks at {sorted(walks)}"
