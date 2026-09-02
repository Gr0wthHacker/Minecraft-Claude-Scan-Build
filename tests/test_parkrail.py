"""The Park Line: the rail rules, the corridor, the three island stations, and the material policy.

**EVERY RAIL RULE HERE IS ASSERTED RATHER THAN LOOKED AT, AND THAT IS THE POINT.** `shape` and
`powered` are DERIVED by the game, `work.INTENTIONAL` does not compare them, and `render3d` draws a
rail facing the wrong way exactly as it draws one facing the right way - so a line that cannot be
ridden passes the audit, the bill of materials, the component count and every render in this repo.
The only checks that can catch it are these.

The power is checked by SIMULATION, not by counting redstone blocks. `mcbuild.circuit` models the
real rule - a powered rail carries its own state eight rails past a source - which is the only way
to answer "is any cell of this line a brake" and the only way to prove that the six platform bays
are dead when nobody is touching them and live for as long as somebody holds their own button.

And the SYMMETRY is measured off the block list, never off a picture: `render3d` draws a fence, a
wall, a chain and a pane of iron bars as full cubes, and it has hidden six separate faults on this
park already.

**ONE TEST IN THE PREVIOUS VERSION OF THIS FILE WAS VACUOUS AND HAD ALWAYS BEEN.**
`test_the_arcade_under_the_deck_is_walkable_end_to_end` built its free-cell set out of ABSOLUTE V
(172..179) and looked those up in a map keyed by the MODEL's x (0..7). Nothing ever matched, every
cell read as free, the flood swept the whole corridor and the assertion could not fail. Measured
properly, the shipped arcade was severed at all three stations - the raised apron and the flight's
own stringer took every column at the station's own pier. The same class of bug is called out in
`test_every_pier_carries_a_gate...`'s own comments, where it was found and fixed once; it was not
looked for here. It is now a real standability flood, and the arcade is genuinely walkable.
"""
from __future__ import annotations

import pathlib

import pytest
import yaml

from mcbuild import audit as audit_mod, blocks
from mcbuild.circuit import Circuit
from mcbuild.gen import parkrail
from mcbuild.gen.railspiral import shapes_for

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

#: THE RESERVE. `PARK_600X200_AUDIT` calls V171-199 "protected rim, terrain, support roots,
#: view/void reserve" and the rim fence stands at V170 in front of it. The line may spend those
#: columns OUTWARD, toward the void; it may never take V170 or the park behind it, and it has to
#: leave a real reserve at the far end.
RIM_EDGE = 170
RESERVE_LAST = 199


def _params() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["params"]


def _sec(p=None) -> dict:
    """The cross-section, from the generator's own one source. Every column of this design is
    derived from `bounds` and `park_side`, so a test that retypes a V is a test that will read a
    different part of the viaduct the day the corridor moves - which is exactly what happened to
    three of them when it moved to the rim."""
    p = p or _params()
    return parkrail._section({**parkrail.PARKRAIL, **p})


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


@pytest.fixture(scope="module")
def named(model):
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
    # ...and a detector rail cannot curve either, which is why one may only ever be put on a
    # straight and why the six of them sit on the platform approaches and nowhere near a turnback.
    assert not (curves & set(blocks.props("detector_rail")["shape"]))


def test_the_corner_budget_is_four_and_that_is_what_the_iron_buys(cells, meta, named):
    """Iron is the scarce metal here and gold is farmable, so a corner is the only expensive cell.

        rail          6 iron -> 16 rails   0.375 iron each
        powered_rail  6 gold ->  6 rails   1.0   gold each

    Four corners - two turnbacks - is 1.5 ingots, and what it buys is that the up line and the down
    line are one closed circuit rather than two out-and-back stubs. Six detector rails at 1 ingot
    each is the rest. **The whole railway's iron is under ten ingots**, and if a future corridor
    bends this is the test that will complain first.
    """
    corners = [c for c in cells if c[3]]
    assert len(corners) == 4 == meta["corners"], "two turnbacks, two corners each, and no more"
    assert meta["corners"] < 100, "corners are the only iron in the track; keep the budget small"
    plain = sum(1 for n in named.values() if n == "rail")
    detectors = sum(1 for n in named.values() if n == "detector_rail")
    assert plain == 4 and detectors == 6 == meta["detector_rails"]
    ingots = plain * 0.375 + detectors * 1.0
    assert ingots <= 10, f"{ingots} ingots of iron in the track"


def test_every_rail_is_the_right_KIND_of_rail_in_a_legal_state(model, cells, named):
    """A powered rail on the straights, a PLAIN rail at a corner because a powered one has no curve
    shape at all, and a detector rail only where a bay's approach wants one."""
    rails = {p: n for p, n in named.items() if n.endswith("rail")}
    assert len(rails) == len(cells)
    corners = {(x, z) for (x, _y, z, corner) in cells if corner}
    for (x, y, z), name in rails.items():
        props = _props(model, x, y, z)
        assert blocks.validate(name, props) == [], f"{name}{props} at {(x, y, z)}"
        if (x, z) in corners:
            assert name == "rail", "a powered rail cannot hold a curve shape"
            assert props["shape"] in ("south_east", "south_west", "north_west", "north_east")
        else:
            assert name in ("powered_rail", "detector_rail")
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


def test_a_ring_closes_and_shapes_for_alone_cannot_know_that(cells):
    """`_loop_shapes` is not decoration. A ring's first and last cells are neighbours, and handed
    the bare list `shapes_for` sees one link at each end - so the corner at the seam comes out as a
    STRAIGHT, which the game derives as a dead end and which our renderer draws exactly like a
    corner."""
    naive = shapes_for(cells)
    closed = parkrail._loop_shapes(cells)
    seam = len(cells) - 1
    assert cells[seam][3], "the ring is written so its seam falls on a corner"
    assert naive[seam] in ("north_south", "east_west"), "...which the bare call gets wrong"
    assert closed[seam] in ("south_east", "south_west", "north_west", "north_east")
    for i, (x, _y, z, corner) in enumerate(cells):
        if corner:
            assert closed[i] in ("south_east", "south_west", "north_west", "north_east")


def test_never_descend_into_a_corner(cells):
    """A curve has no ascending shape, so a corner and both of its neighbours must share one
    height. Built wrong the game re-derives the turn as a slope, the turn is lost and the line
    dead-ends - and nothing in the model looks any different."""
    n = len(cells)
    for i, (_x, y, _z, corner) in enumerate(cells):
        if not corner:
            continue
        for j in ((i - 1) % n, (i + 1) % n):     # the ring wraps: the seam corner has both
            assert cells[j][1] == y, "a corner and its neighbours must be level"
    assert len({c[1] for c in cells}) == 1, "this circuit is dead level end to end"


def test_the_line_is_one_closed_circuit_and_therefore_has_no_terminus(cells, named, meta):
    """**A TRACK CELL IS NOT OPTIONAL**, and this is the strongest form of that check.

    A stop block is what a TERMINUS needs, and a closed circuit has none - so the rule is not
    relaxed, it is replaced by a stronger property that a line with a missing cell cannot have:
    every rail has exactly two rail neighbours, and the whole ring is ONE cycle. A gap anywhere
    would show up as two cells of degree one; a spur would show up as a cell of degree three.
    """
    rails = {p for p, n in named.items() if n.endswith("rail")}
    assert len(rails) == len(cells) == meta["track_cells"]

    def nbrs(pos):
        x, y, z = pos
        return [q for q in ((x + 1, y, z), (x - 1, y, z), (x, y, z + 1), (x, y, z - 1))
                if q in rails]

    assert all(len(nbrs(r)) == 2 for r in rails), "a gap is a degree-1 cell; a spur is degree 3"
    start = next(iter(rails))
    prev, cur, n = None, start, 0
    while True:
        n += 1
        nxt = [q for q in nbrs(cur) if q != prev]
        prev, cur = cur, nxt[0]
        if cur == start:
            break
    assert n == len(rails), "the ring must be ONE cycle, not two"
    assert meta["closed_circuit"] is True


def test_two_carts_cannot_meet_head_on_and_it_is_the_GEOMETRY_that_says_so(cells, meta):
    """THE COLLISION MECHANISM, and it is not redstone.

    A single line with three stations is a line on which two carts can be presented to each other
    on the same rails. Two running lines, one direction each, joined only at the two turnbacks,
    cannot be - and that is a property of the track's shape rather than of a circuit that has to
    keep working. Take the four corners out and what is left is two long legs, each of them
    entirely inside ONE column, plus the two short crossings: so the only way from the up line to
    the down line is round an end, and a cart that goes round an end is still going the same way
    round the circuit.
    """
    v0 = _params()["bounds"][0]
    xa, xb = meta["track_a"] - v0, meta["track_b"] - v0
    assert xa != xb
    open_cells = {(x, z) for (x, _y, z, corner) in cells if not corner}
    seen, legs = set(), []
    for c in open_cells:
        if c in seen:
            continue
        comp, stack = set(), [c]
        while stack:
            x, z = stack.pop()
            if (x, z) in comp:
                continue
            comp.add((x, z))
            for q in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
                if q in open_cells and q not in comp:
                    stack.append(q)
        seen |= comp
        legs.append(comp)
    legs.sort(key=len, reverse=True)
    assert len(legs) == 4, "two running lines and two turnback crossings, and nothing else"
    up, down = legs[0], legs[1]
    assert {x for x, _z in up} == {xa} or {x for x, _z in up} == {xb}
    assert {x for x, _z in down} == {xa} or {x for x, _z in down} == {xb}
    assert {x for x, _z in up} != {x for x, _z in down}, \
        "the two running lines must not share a column, or they are one line"
    assert len(up) == len(down), "one direction each, the same length"


def test_every_rail_stands_on_a_full_block_bed(model, cells, named):
    """A rail on air is a cart in mid-air, and the bed is also where the power comes from."""
    for (x, y, z, _c) in cells:
        bed = named.get((x, y - 1, z))
        assert bed is not None, f"the rail at {(x, y, z)} stands on air"
        assert blocks.is_full_cube(bed), f"the bed at {(x, y - 1, z)} is {bed}, not a full block"


def test_a_track_cell_that_cannot_be_placed_is_an_error_and_not_a_skip():
    """A design may yield a lamp; it may never yield a rail - and a corridor it cannot be built in
    is an error at PLAN time rather than a quiet skip at build time."""
    p = _params()
    with pytest.raises(ValueError):
        parkrail.plan({**p, "bounds": [172, 0, 179, 599]})     # too narrow for two tracks
    with pytest.raises(ValueError):
        parkrail.plan({**p, "bounds": [172, 0, 185, 599]})     # even width: no centre column
    with pytest.raises(ValueError):
        parkrail.plan({**p, "bounds": [172, 0, 186, 5]})       # no room for a circuit
    with pytest.raises(ValueError):
        parkrail.build({**p, "bay_half": 8})                   # a bay its own button cannot light


# ------------------------------------------------------------------ the power, by simulation


@pytest.fixture(scope="module")
def sim(model):
    s = Circuit.of(model)
    s.run(ticks=2)
    return s


def _rails(sim):
    return [p for p, cell in sim.cells.items() if cell.name == "powered_rail"]


def _groups(zs):
    out = []
    for z in sorted(zs):
        if out and z == out[-1][-1] + 1:
            out[-1].append(z)
        else:
            out.append([z])
    return out


def test_an_unpowered_powered_rail_is_a_brake_so_the_line_is_live_everywhere_but_the_bays(
        sim, meta):
    """With nobody touching anything, the ONLY dead rails on twelve hundred cells are the six
    platform bays - one per track per station, each `2 * bay_half + 1` long and centred on its own
    platform.

    Counted rather than reasoned about: `power_every` alone proves nothing, because a powered rail
    carries its own state at most eight rails past a source, a corner and a detector rail both
    break the chain, and every bay moves the sources near it.
    """
    v0 = _params()["bounds"][0]
    half = int(_params()["bay_half"])
    centres = sorted(s["at_u"] for s in meta["stations"])
    for track in ("track_a", "track_b"):
        x = meta[track] - v0
        dead = [p[2] for p in _rails(sim) if p[0] == x and not sim.powered(p)]
        groups = _groups(dead)
        assert len(groups) == 3, f"{track}: one dead bay per station and nowhere else"
        for g, centre in zip(groups, centres):
            assert len(g) == 2 * half + 1, f"{track}: bay is {len(g)} cells, not {2 * half + 1}"
            assert (g[0] + g[-1]) // 2 == centre, "the cart must stop AT the platform"
    others = [p for p in _rails(sim)
              if p[0] not in (meta["track_a"] - v0, meta["track_b"] - v0)]
    assert others and all(sim.powered(p) for p in others), \
        "the turnback crossings are their own runs and each needs its own source"


def test_an_arriving_cart_stops_BY_ITSELF_and_a_button_is_the_only_way_to_send_it_on(model, meta):
    """THE STATION CONTRACT, and both states are simulated because neither is visible.

        at rest              the bay is DEAD, so a cart that runs into it brakes and stops
        button held          the bay is LIVE, end to end, and only that bay on only that track
        button released      the bay is DEAD again, by itself, with nobody having to do anything

    The old design held its bay dead with a LEVER, and a lever is a STATE: left up, that station
    never stops a cart again and nothing on the platform says so. A momentary button cannot be left
    anywhere, which is why the default here is stop.
    """
    p = _params()
    v0, half = p["bounds"][0], int(p["bay_half"])
    walk_y = int(p["deck_y"]) + 1
    sec = _sec(p)
    sim = Circuit.of(model)
    sim.run(2)
    buttons = sorted(q for q, cell in sim.cells.items() if cell.name.endswith("_button"))
    assert len(buttons) == 6, "one release per track per station"

    u0 = p["bounds"][1]

    def bay(track_v, centre):
        x = track_v - v0
        return [(x, walk_y, centre - u0 + dz) for dz in range(-half, half + 1)]

    ac = sorted(s["at_u"] for s in meta["stations"])[0]
    mine = bay(sec["track_a"], ac)
    theirs = bay(sec["track_b"], ac)
    far = bay(sec["track_a"], sorted(s["at_u"] for s in meta["stations"])[1])
    assert not any(sim.powered(q) for q in mine), "AT REST A BAY IS DEAD - that is the auto-stop"

    press = next(q for q in buttons if q[0] == sec["track_a"] - v0 + (1 if sec["side"] < 0 else -1)
                 and q[2] == ac - u0)
    sim.press(press, ticks=15)
    sim.run(2)
    assert all(sim.powered(q) for q in mine), "the button must light the WHOLE of its own bay"
    assert not any(sim.powered(q) for q in theirs), "...and not the other track's"
    assert not any(sim.powered(q) for q in far), "...and not another station's"
    sim.run(20)                                    # the button pops out on its own
    assert not any(sim.powered(q) for q in mine), \
        "a released button must leave the bay dead again, or the station stops working"


def test_a_cart_on_the_approach_rings_the_platform_bell_and_nothing_else(model, meta):
    """The one signal a walker on the promenade gets, and it has NO WIRE ANYWHERE: a detector rail
    powers what stands next to it, and the bell stands next to it.

    The cart is an INPUT, exactly as `circuit`'s own docstring requires - the simulator has no
    entities, so a test states that a cart reached the detector rather than pretending to know.
    """
    sim = Circuit.of(model)
    sim.run(2)
    detectors = sorted(q for q, c in sim.cells.items() if c.name == "detector_rail")
    bells = sorted(q for q, c in sim.cells.items() if c.name == "bell")
    assert len(detectors) == len(bells) == 6
    for det in detectors:
        near = [b for b in bells if abs(b[0] - det[0]) + abs(b[2] - det[2]) == 1]
        assert len(near) == 1, f"the detector at {det} has no bell beside it"
    assert not any(sim.powered(b) for b in bells), "a bell does not ring on its own"
    sim.set_signal(detectors[0], 15)
    out = sim.step()
    mine = [b for b in bells if abs(b[0] - detectors[0][0]) + abs(b[2] - detectors[0][2]) == 1][0]
    assert out.get(mine) is True, "a cart on the detector must ring the bell beside it"
    assert sum(1 for b in bells if out.get(b)) == 1, "...and only that one"
    # AND IT MUST NOT WAKE THE BAY. A detector rail powers its neighbours, rails included, so one
    # placed a cell nearer the platform would light the very stretch that has to stay dead.
    p = _params()
    v0, half = p["bounds"][0], int(p["bay_half"])
    x = meta["track_a"] - v0
    ac = sorted(s["at_u"] for s in meta["stations"])[0]
    walk_y = int(p["deck_y"]) + 1
    assert not any(sim.powered((x, walk_y, ac + dz)) for dz in range(-half, half + 1)), \
        "the approach detector must not power the bay it is warning about"


def test_the_quiet_band_is_arithmetic_and_the_arithmetic_is_in_one_place():
    """`_sources` owns the whole brake geometry, so moving `bay_half` moves it CORRECTLY.

    The band is `[c - h - 8, c + h + 8]` with the shoulders forced at `c +/- (h + 9)`; each
    shoulder then covers the eight quiet cells nearest it and leaves exactly `2h + 1` dead. The
    version this replaces wrote the band as `[c - 2h, c + 2h]`, which leaves `4h - 15` dead -
    equal to `2h + 1` at h=8 and at no other value, under a docstring that promised the arithmetic
    moved with the parameter. It was right for the one number it had.
    """
    for half in (2, 3, 5, 7):
        n, every, c = 400, 8, 200
        picks, quiet = parkrail._sources(n, every, [c], half)
        assert quiet == set(range(c - half - 8, c + half + 9))
        assert not (picks & quiet), "no source may stand inside the band that must go dead"
        assert {c - half - 9, c + half + 9} <= picks, \
            "the band's two shoulders are FORCED, or the bay's own button cannot bridge the gap"
        reach = set()
        for i in picks:
            reach |= set(range(i - 8, i + 9))
        dead = sorted(set(range(n)) - reach)
        assert dead == list(range(c - half, c + half + 1)), \
            f"half={half} must leave exactly {2 * half + 1} dead, centred on the platform"
    # ...and a break is a wall a source cannot reach past: a corner and a detector rail are both
    # plain rails, so power is dealt per RUN.
    picks, _quiet = parkrail._sources(60, 8, [], 3, breaks={30})
    assert 29 in picks and 31 in picks, "each run needs a source of its own at its own end"
    assert 30 not in picks, "a source under a plain rail powers exactly itself"


# ------------------------------------------------------------------ the corridor and the reserve


def test_nothing_leaves_the_corridor(model, meta, named):
    """V172-186 for the full six hundred, and NOT ONE CELL AT Y0: the lawn under the viaduct
    belongs to `Park Ways`, so the two designs share the strip without contesting a cell of it."""
    v0, u0, v1, u1 = meta["bounds"]
    sx, _sy, sz = model.shape_xyz
    assert (sx, sz) == (v1 - v0 + 1, u1 - u0 + 1) == (15, 600)
    assert all(0 <= x < sx for (x, _y, _z) in named)
    assert not any(y == 0 for (_x, y, _z) in named), \
        "y0 is the park's own lawn course and this design never claims it"


def test_the_line_grows_OUTWARD_and_leaves_a_real_reserve(meta):
    """Jack: "we can use more space" - and the only direction there is any is toward the VOID.

    V170 is the rim edge and everything below it is the park; V171-199 is the protected rim and
    void reserve. The line takes fifteen of those thirty columns, all of them outward: it starts
    at V172 exactly where it did, so the reserve lawn the station walks land on is untouched, and
    it stops at V186 with **thirteen columns, V187-199, left clear at the far end**.
    """
    v0, _u0, v1, _u1 = meta["bounds"]
    assert v0 > RIM_EDGE, "the rim edge and the park behind it are not this design's to take"
    assert v0 == 172, "the reserve lawn at V171 is where the park's own walks land"
    assert v1 <= RESERVE_LAST
    spent, left = v1 - v0 + 1, RESERVE_LAST - v1
    assert spent == 15
    assert left >= 12, f"only {left} reserve columns left past the viaduct"


def test_it_is_one_piece_with_no_placement_problems(model):
    res = audit_mod.audit(model, ground=False)
    assert res.problems == [], "\n".join(str(p) for p in res.problems[:10])
    assert len(res.components) == 1, f"components: {sorted(res.components, reverse=True)[:6]}"


# ------------------------------------------------------------------ the symmetry


def test_the_facade_is_SYMMETRIC_and_it_is_measured_not_looked_at(named, model):
    """Jack: "they look decent but are a little asymettric with the hanging facade which is a bit
    strange."

    Measured on the old line: the section was eight columns deep with the track at V177, so the
    deck's own centre line fell on V175.5 - **there was no centre column for anything to be
    symmetric about**. The canopy was a six-column roof with an eave on one edge only and two bare
    columns on the other; the portal frames spanned all eight columns and hung one lantern at V175,
    half a block off the axis of the frame it hung from. 10,232 of 22,362 cells had no mirror.

    An odd section with two tracks mirrored about a real centre column fixes it by construction,
    and this is the number that says so: **at and above the deck - which is the whole of what a
    rider or a walker sees - fewer than one cell in a thousand has no mirror image.**

    The six that do are the approach bells, and they are RIGHT: a bell belongs at the end of the
    platform its own track arrives from, and the two tracks arrive from opposite ends. They mirror
    under the half-turn a double-track island station actually has, which is the next test.
    """
    sx = model.shape_xyz[0]
    deck_y = int(_params()["deck_y"])
    occ = set(named)
    above = [q for q in occ if q[1] >= deck_y]
    orphan = [q for q in above if (sx - 1 - q[0], q[1], q[2]) not in occ]
    assert len(orphan) / len(above) < 0.001, \
        f"{len(orphan)} of {len(above)} cells above the deck have no mirror: {sorted(orphan)[:6]}"
    assert {named[q] for q in orphan} <= {"bell"}, \
        f"only the approach bells may be one-sided, not {sorted({named[q] for q in orphan})}"
    # ...and the whole design, entrances and all, is within a per-cent of symmetric.
    all_orphan = [q for q in occ if (sx - 1 - q[0], q[1], q[2]) not in occ]
    assert len(all_orphan) / len(occ) < 0.02


def test_the_two_bells_of_a_station_are_a_HALF_TURN_of_each_other(named, meta, model):
    """The only deliberately one-sided thing on the deck, and the reason is direction of travel.

    Track A arrives at a platform from one end and track B from the other, so each bell stands at
    its own track's approach. Reflected across the corridor they do not match; turned through half
    a turn about the platform's own centre they do exactly - which is what a real double-track
    island station looks like and what makes the pair symmetric rather than lopsided.
    """
    sx = model.shape_xyz[0]
    bells = sorted(q for q, n in named.items() if n == "bell")
    assert len(bells) == 6
    for s in meta["station_detail"]:
        ac = s["at_u"]
        pair = [b for b in bells if abs(b[2] - ac) <= int(_params()["station_half"])]
        assert len(pair) == 2, f"{s['title']} has {len(pair)} bells"
        a, b = pair
        assert (sx - 1 - a[0], a[1], 2 * ac - a[2]) == (b[0], b[1], b[2]), \
            "the pair must be a half-turn about the platform centre"


def test_the_canopy_is_a_PITCHED_roof_and_it_is_symmetric_about_the_island_s_own_axis(
        named, meta):
    """The specific thing that read as lopsided, and the specific fix.

    A canopy over an island platform is symmetric or it is nothing: posts on both platform edges,
    a roof across the whole island, an eave leaning out over EACH track, a ridge beam on the axis,
    and the hanging lanterns in mirrored pairs. `render3d` draws a fence and a chain as full cubes,
    so every one of these is counted off the block list.

    **AND IT IS PITCHED.** The first version was one flat plate of slabs, which in the round is one
    plane, one tone and no shadow anywhere - a lid. Two courses of rise over four columns each side
    is a shallow gable; what is asserted is the PROFILE, because a roof that rises on one side and
    not the other is the same fault the whole design was rebuilt to remove.
    """
    p = _params()
    sec, v0 = _sec(p), p["bounds"][0]
    half = int(p["station_half"])
    canopy_y = int(p["deck_y"]) + 1 + int(p["canopy_h"])
    cols = [sec["edge_a"]] + list(sec["island"]) + [sec["edge_b"]]
    mid = (len(cols) - 1) // 2
    for s in meta["station_detail"]:
        ac = s["at_u"]
        for u in range(ac - half, ac + half + 1):
            top = []
            for v in cols:
                hits = [dy for dy in (0, 1, 2) if (v - v0, canopy_y + dy, u) in named]
                assert hits, f"{s['title']}: a hole in the roof at v={v}, u={u}"
                top.append(max(hits))
            assert top == top[::-1], f"{s['title']} at u={u}: the roof profile is lopsided: {top}"
            assert top[mid] == 2, "the ridge beam sits on the axis"
            assert top[0] == top[-1] == 0, "the eaves are the lowest course"
            for a, b in zip(top[:mid], top[1:mid + 1]):
                assert b >= a, f"{s['title']}: the pitch has to rise toward the ridge: {top}"
            for track in (sec["track_a"], sec["track_b"]):
                assert (track - v0, canopy_y, u) in named,                     f"{s['title']}: no eave over {track} at u={u}"
        chains = [q for q, n in named.items()
                  if n == "iron_chain" and abs(q[2] - ac) <= half]
        assert chains and len(chains) % 2 == 0, f"{s['title']}: lanterns hang in pairs or not at all"
        for x, y, z in chains:
            assert (sec["w"] - 1 - x, y, z) in named, "every hanging thing has a mirror"


def test_every_eave_and_bench_leans_the_way_its_own_side_says(model, named, meta):
    """A stair's TALL side IS its `facing`, and our renderer draws both directions identically -
    which is why this is asserted rather than eyeballed. An eave sheltering a track has its tall
    side toward the roof it grows from; a bench's backrest is its tall side, so the pair backs on
    to the island's own centre and each half looks out over its own track."""
    p = _params()
    sec, v0 = _sec(p), p["bounds"][0]
    side = sec["side"]
    canopy_y = int(p["deck_y"]) + 1 + int(p["canopy_h"])
    inward_a = parkrail._v_dir(-side)      # from track A toward the island
    inward_b = parkrail._v_dir(side)
    seen = 0
    for s in meta["station_detail"]:
        for u in range(s["at_u"] - 13, s["at_u"] + 14):
            for track, want in ((sec["track_a"], inward_a), (sec["track_b"], inward_b)):
                x = track - v0
                if (x, canopy_y, u) not in named:
                    continue
                pr = _props(model, x, canopy_y, u)
                assert pr["half"] == "bottom" and pr["facing"] == want, \
                    f"the eave at {(x, canopy_y, u)} leans {pr['facing']}, not {want}"
                seen += 1
    assert seen >= 150, "every platform column carries an eave over each of its two tracks"


# ------------------------------------------------------------------ the three stations


def test_there_are_three_stations_one_per_land_each_fully_fitted(meta):
    detail = meta["station_detail"]
    assert len(detail) == 3
    assert sorted(s["land"] for s in detail) == ["frontier", "midway", "prismworks"]
    for s in detail:
        assert s["buttons"] == 2, f"{s['title']}: a release on each platform edge"
        assert s["bells"] == 2, f"{s['title']}: an approach bell on each track"
        assert s["board"] == 2, f"{s['title']}: a departure board on each approach"
        assert s["name_signs"] == 2, f"{s['title']}: the name on each face of the pylon"
        assert s["screens"] == 4, f"{s['title']}: a gable screen at each end, both sides"
        assert s["platform"] >= 21
        assert s["lanterns"] >= 6


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


def test_every_tread_of_every_flight_ascends_toward_the_platform(model, meta, named):
    """A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D, half=bottom.

    Built the other way round the risers face into the descent and you cannot walk up it - and our
    renderer draws both directions identically, which is why this is asserted and never eyeballed.
    """
    p = _params()
    v0 = p["bounds"][0]
    ground_y, deck_y = int(p["ground_y"]), int(p["deck_y"])
    stair_x = {v - v0 for v in _sec(p)["stair_v"]}
    for s in meta["station_detail"]:
        lo, hi = s["stair_from_u"], s["stair_to_u"]
        ascend = "north" if s["at_u"] < lo else "south"
        seen = {}
        for (x, y, z), n in named.items():
            # ONLY THE FLIGHT'S OWN TREADS. The canopy's pitch puts riser STAIRS in the same
            # three columns twenty courses higher, and they lean across the roof rather than along
            # the flight - so a test that took every stair in the column would fail a correct
            # build and, read the other way, would pass a flight whose treads had gone missing.
            if lo <= z <= hi and n.endswith("_stairs") and x in stair_x and y <= deck_y:
                pr = _props(model, x, y, z)
                assert pr["half"] == "bottom", f"{s['title']} tread at {(x, y, z)} is upside down"
                assert pr["facing"] == ascend, \
                    f"{s['title']} tread at {(x, y, z)} faces {pr['facing']}, not {ascend}"
                seen.setdefault(z, set()).add(y)
        assert len(seen) == deck_y - ground_y + 1 == hi - lo + 1
        heights = [min(seen[z]) for z in sorted(seen)]
        if ascend == "north":                     # the flight descends toward +U
            assert heights == sorted(heights, reverse=True)
        else:
            assert heights == sorted(heights)
        assert min(heights) == ground_y and max(heights) == deck_y, \
            "a flight has to reach the lawn at one end and the deck at the other"


def test_a_flight_you_cannot_walk_down_is_not_a_flight(meta, named):
    """The courses over every tread must be air, or the deck the flight descends through is a
    ceiling - a stairwell is a HOLE, and a buried flight audits as one clean solid."""
    p = _params()
    v0 = p["bounds"][0]
    deck_y = int(p["deck_y"])
    walk_y = deck_y + 1
    stair_x = {v - v0 for v in _sec(p)["stair_v"]}
    for s in meta["station_detail"]:
        for z in range(s["stair_from_u"], s["stair_to_u"] + 1):
            for x in stair_x:
                # THE TOPMOST STAIR IN THE COLUMN IS THE TREAD. Everything under it is the
                # stringer the flight stands on - masonry, and meant to be there.
                # ...and the TREAD is the flight's own topmost stair, never the canopy's riser
                # twenty courses over it: taking the column's maximum picked the roof, and the
                # window this test then checks came out EMPTY, so it asserted nothing at all.
                tread = max(y for (xx, y, zz), n in named.items()
                            if (xx, zz) == (x, z) and n.endswith("_stairs") and y <= deck_y)
                for y in range(tread + 1, walk_y + 2):
                    assert (x, y, z) not in named, \
                        f"{s['title']}: the flight is buried at {(x, y, z)}"


def test_the_promenade_gets_PAST_the_stairwell_on_both_sides(named, meta):
    """The island is the promenade for six hundred blocks, and the flight is cut out of its own
    three centre columns - so the walk has to survive on each side of the well or the line is two
    promenades with a hole between them. Two clear columns each side, and they are checked at the
    walking course, not on a plan."""
    p = _params()
    sec, v0 = _sec(p), p["bounds"][0]
    walk_y = int(p["deck_y"]) + 1
    stair = set(sec["stair_v"])
    flank = [v for v in sec["island"] if v not in stair]
    assert len(flank) >= 4, "an island only as wide as its own flight is not a promenade"
    for s in meta["station_detail"]:
        for z in range(s["stair_from_u"], s["stair_to_u"] + 1):
            clear = [v for v in flank
                     if (v - v0, walk_y, z) not in named and (v - v0, walk_y + 1, z) not in named]
            assert len(clear) >= 4, f"{s['title']}: the promenade is pinched at u={z}"


def test_the_release_button_can_actually_reach_its_own_track(model, meta, named):
    """A button strongly powers the block it is attached to, and a strongly powered block beside a
    powered rail energises it. Placed one cell further back it powers nothing and the station never
    releases - which looks exactly like a station that works."""
    p = _params()
    v0 = p["bounds"][0]
    walk_y = int(p["deck_y"]) + 1
    tracks = {meta["track_a"] - v0, meta["track_b"] - v0}
    buttons = [(x, y, z) for (x, y, z), n in named.items() if n.endswith("_button")]
    assert len(buttons) == 6
    for x, y, z in buttons:
        assert _props(model, x, y, z)["face"] == "floor"
        below = named.get((x, y - 1, z))
        assert below is not None and blocks.is_full_cube(below), "a button needs a plinth"
        assert y - 1 == walk_y, "the plinth must stand in the rail's own course"
        assert min(abs(x - t) for t in tracks) == 1, \
            "the plinth must sit beside a rail, or it energises nothing"
    assert len({b[0] for b in buttons}) == 2, "one release on each platform edge"


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
    assert res.tiers.get("expensive", 0) == 0, \
        "nothing expensive is declared functional here, so nothing is spent"
    ok = res.tiers.get("ok", 0)
    assert 0.08 <= ok / total <= 0.18, f"ok tier is {ok / total:.1%}"
    assert res.tiers.get("cheap", 0) / total >= 0.78


def test_a_post_is_a_slim_block_and_never_a_pillar(model, meta):
    """`render3d` draws a fence, a wall and a rod as full cubes, so this can only ever be checked
    by BLOCK TYPE. Every parapet, portal leg and canopy post is one of the slim families."""
    for land, pal in parkrail.SPAN.items():
        for key in ("parapet", "post"):
            assert pal[key].endswith(SLIM_SUFFIX), f"{land}.{key} is {pal[key]}, a full block"


def test_the_lights_that_carry_the_line_cost_no_metal(named, meta):
    """A lantern is an iron ingot and a chain is another, and the line is twice the width it was
    with six platforms on it. So the viaduct's own rhythm of light - a froglight in every portal
    beam, in every other arch crown and in the lintel of every pier passage - costs nothing, and
    the iron goes only where a light has to HANG: the six station canopies and the three station
    doors, which are the three places a visitor stands still."""
    frog = sum(1 for n in named.values() if n == parkrail.FLUSH_LIGHT)
    metal = sum(1 for n in named.values() if n in ("lantern", "soul_lantern"))
    chain = sum(1 for n in named.values() if n == "iron_chain")
    assert frog >= meta["flush_lights"]
    assert frog > 5 * metal, "the overwhelming majority of the light must cost nothing"
    assert metal + chain < 80, f"{metal} lanterns and {chain} chains is a lot of iron"


# ------------------------------------------------------------------ the viaduct


def test_every_pier_carries_TWO_passages_one_off_each_face(named, meta):
    """One wide cut off the park face is the single biggest asymmetry a viaduct of this section can
    have - measured, it left 441 more cells on the void half of the deck than on the park half and
    put every pier's remaining leg on one side. A band off EACH face with the pier's own core
    between them reaches the park face just as well, gives the arcade a second lane at the piers
    where a station's raised apron takes the first, and mirrors exactly.

    ...and the whole thing is in MODEL coordinates. `named` is keyed by the canvas x, and a check
    written against an absolute V matches nothing at all and therefore passes on every design ever
    put through it. That is not hypothetical - see this module's own docstring.
    """
    p = _params()
    v0, u0, _v1, u1 = p["bounds"]
    sec = _sec(p)
    gk, w = sec["gate_k"], sec["w"]
    assert sec["park"] in sec["gate_cols"], "the passage must reach the corridor's park face"
    assert sec["void"] in sec["gate_cols"], "...and the other one must reach the void face"
    assert 2 * gk + int(p["stair_w"]) <= w, "the core has to carry the flight's own stringer"
    gate_x = {v - v0 for v in sec["gate_cols"]}
    core_x = set(range(w)) - gate_x
    ground_y, bay, pier_u = int(p["ground_y"]), int(p["bay"]), int(p["pier_u"])
    for b0 in range(u0, u1 + 1, bay):
        for u in range(b0, min(b0 + pier_u, u1 + 1)):
            # NOT EVERY COLUMN OF EVERY PASSAGE: a station's flight lands on masonry that
            # legitimately refills the core, and the apron raises the park-side lane. What must be
            # true everywhere is that SOMETHING is open in each passage, at whatever its own floor
            # is - and that the walk it belongs to actually runs, which is the next test.
            def _clear(v, floor):
                return all((v, y, u) not in named
                           for y in range(floor + 1, floor + int(p["gate_h"])))
            openings = [v for v in gate_x
                        if ((v, ground_y, u) not in named and _clear(v, ground_y - 1))
                        or ((v, ground_y, u) in named and _clear(v, ground_y))]
            assert openings, f"the pier at u={u} is not walkable through at all"
            assert any((v, ground_y, u) in named for v in core_x), \
                f"the pier at u={u} has no core left to stand on"


def test_the_arcade_under_the_deck_is_walkable_end_to_end(named, meta):
    """THE REAL PROPERTY IS THE WALK, NOT THE HOLE, and this test could not fail until today.

    It used to build its free-cell set out of absolute V and look those up in a model-indexed map,
    so nothing ever matched, every cell read as free, and the flood swept a corridor it had never
    actually looked at. Measured properly, the arcade under the shipped line was SEVERED at all
    three stations: the raised apron took every park-side column and the pier's own mass took the
    rest, and there was no lane left at the station's own pier.

    And the model has to be a WALK rather than an empty column: a station's forecourt is a RAISED
    apron - which is what Jack asked the entries for - so the floor there is one course up and you
    stand on top of it. What is flooded is standable cells, with a step of one either way.
    """
    p = _params()
    v0, u0, v1, u1 = p["bounds"]
    sx = v1 - v0 + 1
    g = int(p["ground_y"])

    def stand(x, y, z):
        return ((y == g or (x, y - 1, z) in named)
                and (x, y, z) not in named and (x, y + 1, z) not in named)

    start = [(x, y, 0) for x in range(sx) for y in (g, g + 1, g + 2) if stand(x, y, 0)]
    assert start, "there is nowhere to stand at the near end of the arcade"
    seen, stack = set(start), list(start)
    while stack:
        x, y, z = stack.pop()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                n = (x + dx, y + dy, z + dz)
                if n in seen or not (0 <= n[0] < sx and 0 <= n[2] <= u1 - u0):
                    continue
                if not (g <= n[1] <= g + 4) or not stand(*n):
                    continue
                seen.add(n)
                stack.append(n)
    reached = {z for _x, _y, z in seen}
    missing = sorted(set(range(u1 - u0 + 1)) - reached)
    assert not missing, f"the walk under the viaduct breaks at u={missing[:12]}"


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
    between there and the service lane are FOURTEEN BLOCKS OF BARE GRASS - no route at all. Each
    station's portal now sits on the column of a walk carried through the rim from an avenue, so a
    guest steps off the park's own street into the station.

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
    if rs.shape[2] != _params()["bounds"][2] - v0 + 1:
        pytest.skip("out/Park Rail.litematic is a different section from the config - regenerate")
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
    import yaml as _yaml
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    ways = _yaml.safe_load((root / "configs" / "park_ways.yaml").read_text(encoding="utf-8"))
    walks = set(ways["params"]["parts"][0]["params"]["rail_stations"])
    portals = {s["portal_u"] for s in _meta_stations()}
    assert portals == walks, f"portals at {sorted(portals)} against walks at {sorted(walks)}"
