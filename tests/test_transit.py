"""The Park Line's contracts.

Every one of these pins something that ships a CLEAN AUDIT and a broken railway. That is the
whole difficulty of this design: a rail is a legal block state, on a supported cell, inside the
plot, in 1.19, at cheap tier, and none of that has anything to say about whether a cart moves,
whether a visitor can get on it, or whether it goes anywhere. `shape` and `powered` are derived
by the GAME, so the schematic, the audit, the bill of materials and every render in this repo
agree with each other perfectly while the line does not run.

The three that found real faults while this was being written:

    a nine-cell landing pad floating beside its own stair, because the stringer stopped one
      course short of the street - caught only by counting connected components;
    127 deck cells at block light ZERO on a span the design believed it had lit, because the
      lamp spacing (8) and the bay spacing (12) coincide every 24 cells and a portal post sat
      on top of the froglight - caught only by propagating the light;
    and the same again, five courses up, on the portal beams: every lamp was on one kerb and
      the far side of the deck measured 0 - caught only by asking about SPAWNABLE cells rather
      than about the ones a visitor walks on.
"""
import json
from collections import deque

import numpy as np
import pytest
import yaml

from mcbuild import blocks, nbt, nightlight, palette, schem
from mcbuild.gen import park, transit
from mcbuild.gen.railspiral import power_cells, runs_of, shapes_for

CONFIG = "configs/park_line.yaml"
ZONES = ["Park_Left Complete", "Park_Centre Complete", "Park_Right Complete"]
CASINO = "Casino Complete"
LANDS = sorted(park.LANDS)
KINDS = sorted(transit.BUILDERS)


# --------------------------------------------------------------------------- fixtures

def _cfg():
    with open(CONFIG, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["params"]


def _states(model):
    """The palette as full `name[k=v,...]` strings.

    **`Model.names` DROPS THE PROPERTIES**, which this repo has been bitten by three times: a
    stair's `facing`, a slab's `type` and a rail's `shape` all vanish, so a test that greps the
    names for `half=bottom` is testing the wrong artifact and passes on a build that has none.
    Read the palette NBT.
    """
    out = []
    for e in model.palette:
        name = nbt.state_name(e).split(":")[-1]
        props = nbt.state_props(e)
        tail = ",".join(f"{k}={v}" for k, v in sorted(props.items()))
        out.append(f"{name}[{tail}]" if props else name)
    return out


def _cells(model, origin):
    """{(x, y, z): 'block[state]'} in WORLD coordinates, properties included.

    Asserting in world coordinates is a rule this repo has already paid for: a canvas is sized
    to its own content, so it shifts between two builds with different settings and anything
    comparing them lines up against nothing.
    """
    ox, oy, oz = origin
    states = _states(model)
    ys, zs, xs = np.nonzero(model.ids > 0)
    return {(x + ox, y + oy, z + oz): states[model.ids[y, z, x]]
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())}


@pytest.fixture(scope="module")
def line():
    c = transit.build(_cfg())
    return c, c.to_model(), _cells(c.to_model(), c.world_origin)


@pytest.fixture(scope="module")
def zones():
    out = {}
    for nm in ZONES:
        m = schem.load(f"out/{nm}.litematic")
        with open(f"out/{nm}.scan.json", encoding="utf-8") as fh:
            o = json.load(fh)["origin"]
        out.update(_cells(m, (o["x"], o["y"], o["z"])))
    return out


def _base(state):
    return state.split("[")[0]


def _blocking(world, cell):
    """Occupies the cell you would stand in. `nightlight` is the ONE source for what light and
    a body pass through, so this cannot drift from the design's own lighting solver."""
    n = world.get(cell)
    return bool(n) and _base(n) not in nightlight.PASSY and _base(n) not in nightlight.WATERY


def _stand(world, cell):
    x, y, z = cell
    return (_blocking(world, (x, y - 1, z))
            and not _blocking(world, cell) and not _blocking(world, (x, y + 1, z)))


def _walk(world, seeds):
    """Every cell reachable on foot from `seeds`: orthogonal steps, one course up or down."""
    seeds = [s for s in seeds if _stand(world, s)]
    seen, q = set(seeds), deque(seeds)
    while q:
        x, y, z = q.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                nb = (x + dx, y + dy, z + dz)
                if nb in seen or not _stand(world, nb):
                    continue
                seen.add(nb)
                q.append(nb)
    return seen


def _components(cells):
    occ, seen, sizes = set(cells), set(), []
    for start in occ:
        if start in seen:
            continue
        q, n = deque([start]), 0
        seen.add(start)
        while q:
            x, y, z = q.popleft()
            n += 1
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (x + d[0], y + d[1], z + d[2])
                if nb in occ and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        sizes.append(n)
    return sorted(sizes, reverse=True)


def _small(kind, land="midway", axis="z", forward=1):
    """A short line with no `avoid` and no plot: fast enough to sweep every kind and land."""
    return {"kind": kind, "axis": axis, "forward": forward, "at": [0, 64, 0], "length": 61,
            "land": land, "street_y": 60, "title": "TEST LINE",
            "stations": [{"at_a": 12, "land": land, "title": "ALPHA", "stair": -1},
                         {"at_a": 48, "land": land, "title": "OMEGA", "stair": 1}]}


# --------------------------------------------------------------------------- it builds, legally

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("axis,forward", [("z", 1), ("z", -1), ("x", 1), ("x", -1)])
def test_every_kind_builds_on_every_land_and_every_heading(kind, land, axis, forward):
    c = transit.build(_small(kind, land, axis, forward))
    assert c.to_model().ids.size > 0


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_every_block_state_is_legal(kind, land):
    m = transit.build(_small(kind, land)).to_model()
    for spec in _states(m):                 # the STATES, not `m.names` - see `_states`
        base = spec.split("[")[0]
        if base == "air":
            continue
        props = {}
        if "[" in spec:
            props = dict(kv.split("=", 1) for kv in spec[spec.index("[") + 1:-1].split(","))
        assert blocks.validate(base, props) == [], f"{spec} is not a legal state"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_nothing_built_is_currency_unavailable_or_expensive(kind, land):
    """DIRT IS MONEY ON THIS SERVER, and a 1.20 block passes every other check in the pipeline.
    The palette table being clean is not the same as the BUILD being clean - a generator can
    reach past its own palette, and two of them here do (`park.LANDS` for the fence and the
    canopy, `LAMP` for the light)."""
    m = transit.build(_small(kind, land)).to_model()
    for n in m.names:
        b = n.split(":")[-1].split("[")[0]
        if b == "air":
            continue
        assert blocks.spendable(b), f"{kind}/{land} places CURRENCY: {b}"
        assert blocks.available(b), f"{kind}/{land} is not 1.19-legal: {b}"
        assert palette.tier(b) != "expensive", f"{kind}/{land} places expensive: {b}"


@pytest.mark.parametrize("land", LANDS)
def test_every_land_can_actually_draw_a_line(land):
    """A VALUE LADDER MUST BE MEASURED ACROSS MATERIAL FAMILIES. Three separate notes in this
    repo conclude that the economy has no value contrast, and every one of them searched inside
    ONE family, where a ladder cannot exist by construction. Under about 15 luminance a trim
    course stops reading as a line and the span is one flat tone from end to end."""
    span = transit.SPAN[land]

    def lum(name):
        r, g, b = blocks.color(name, "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    deck = lum(span["deck"])
    for key in ("kerb", "arch"):
        gap = abs(lum(span[key]) - deck)
        assert gap >= 15, f"{land}: {key} is {gap:.0f} from the deck - that is not a line"


# --------------------------------------------------------------------------- the railway

def _rail_cells(cells):
    return {c for c, st in cells.items() if _base(st) in ("rail", "powered_rail")}


def test_the_track_is_one_line_from_the_left_station_to_the_right(line):
    """WALKED CELL TO CELL, not counted. A track can have the right number of rails, one per
    column, and still be two railways: a single skipped cell is a gap that the audit reads as
    one connected solid because the deck under it is continuous."""
    c, _m, cells = line
    rails = _rail_cells(cells)
    meta = c.meta
    assert len(rails) == meta["track"] == len(meta["rail"])
    ends = [tuple(meta["rail"][0]), tuple(meta["rail"][-1])]
    seen, q = {ends[0]}, deque([ends[0]])
    while q:
        x, y, z = q.popleft()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
            for dy in (0, 1, -1):          # a slope's two ends are one course apart
                nb = (x + d[0], y + dy, z + d[2])
                if nb in rails and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
    assert ends[1] in seen, "the far terminus is not on the same line as the near one"
    assert seen == rails, f"{len(rails - seen)} rails are not joined to the line"


def test_the_line_passes_through_every_station(line):
    """One line THROUGH the centre, not two lines that both end there."""
    c, _m, cells = line
    rails = _rail_cells(cells)
    stations = c.meta["stations_built"]
    assert len(stations) == 3, "the park is three islands and wants three stations"
    for st in stations:
        assert st["boarding"], f"{st['title']} has no boarding gate"
        for b in st["boarding"]:
            assert tuple(b) in rails, f"{st['title']}: a boarding cell is not on the track"


def test_no_rail_is_dead(line):
    """AN UNPOWERED POWERED_RAIL IS A BRAKE, so 'mostly powered rails' is not a saving, it is a
    line that stops. Every one has to be within `power_every` of a redstone_block in its own
    bed, and the runs are counted BETWEEN CORNERS because a plain rail does not propagate the
    chain - a flat spacing leaves a dead rail past every turn, and a dead rail on a viaduct over
    the void is a cart in the void."""
    c, _m, cells = line
    p = _cfg()
    rail = [tuple(r) for r in c.meta["rail"]]
    sources = {tuple(s) for s in c.meta["power_sources"]}
    assert sources, "no power at all"
    every = int(p["power_every"])
    lit = [i for i, r in enumerate(rail) if (r[0], r[1] - 1, r[2]) in sources]
    for i, r in enumerate(rail):
        assert _base(cells[r]) == "powered_rail", f"{r} is a plain rail on a straight run: iron"
        assert min(abs(i - j) for j in lit) <= every, \
            f"rail {i} at {r} is more than {every} from a source - it is a brake"
    # ...and the sources are dealt per run, which on this line is one run because it is straight
    assert c.meta["runs"] == len(runs_of([(*r, False) for r in rail]))


def test_both_termini_carry_a_stop_block(line):
    """A stationary cart on a powered rail launches AWAY from the adjacent solid block. Without
    one at each end the line only runs whichever way you happened to shove the cart - and a
    connection a visitor cannot come back along has not connected anything."""
    c, _m, cells = line
    rail = [tuple(r) for r in c.meta["rail"]]
    stops = [tuple(s) for s in c.meta["stops"]]
    assert len(stops) == 2
    for end, nxt, stop in ((rail[0], rail[1], stops[0]), (rail[-1], rail[-2], stops[1])):
        assert stop == (2 * end[0] - nxt[0], end[1], 2 * end[2] - nxt[2]), \
            "a stop block goes on the far side of the terminus from the track"
        assert stop in cells, "the stop block was never placed"
        assert blocks.is_full_cube(_base(cells[stop])), \
            f"{cells[stop]} is not a full block, so a cart is not launched off it"


def test_this_line_spends_no_iron_at_all(line):
    """THE HEADLINE, AND IT IS A CONSEQUENCE OF THE GEOMETRY. A powered rail cannot curve, so
    every direction change is a plain rail and therefore iron - and iron is this server's scarce
    metal while gold is farmable. The three islands lie on one axis, so a straight run needs no
    corner and the whole railway's metal is gold. A `lantern` would have undone it single-
    handedly: 45 of them is more iron than a bent line would have cost."""
    _c, _m, cells = line
    kinds = {_base(s) for s in cells.values()}
    for iron in ("rail", "lantern", "soul_lantern", "chain", "iron_bars", "detector_rail",
                 "activator_rail", "hopper", "iron_door", "iron_trapdoor"):
        assert iron not in kinds, f"{iron} is iron on a line whose whole argument is that it is not"


# ------------------------------------------ the rail rules, exercised on a path that HAS corners

def _track_rules(cells, shapes):
    """Everything a rail path must satisfy. Returns the list of violations, so a test can assert
    both that a good path has none AND that a bad one is caught."""
    bad = []
    for i, (x, y, z, corner) in enumerate(cells):
        if corner:
            for j in (i - 1, i + 1):
                if 0 <= j < len(cells) and cells[j][1] != y:
                    bad.append(f"corner {i} at {(x, y, z)} has a neighbour at a different height")
            if not shapes[i].endswith(("_east", "_west")) or shapes[i].startswith("ascending"):
                if shapes[i] in ("north_south", "east_west") or shapes[i].startswith("ascending"):
                    bad.append(f"corner {i} emitted {shapes[i]}, which is not a curve")
        if shapes[i].startswith("ascending_"):
            want = shapes[i][len("ascending_"):]
            hi = [c for c in (cells[i - 1] if i else None,
                              cells[i + 1] if i + 1 < len(cells) else None)
                  if c is not None and c[1] > y]
            if not hi:
                bad.append(f"cell {i} ascends toward nothing")
            else:
                got = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[
                    (hi[0][0] - x, hi[0][2] - z)]
                if got != want:
                    bad.append(f"cell {i} says ascending_{want} and climbs {got}")
    return bad


def _bent_path():
    """A synthetic path that turns twice and climbs once, so the rules above are actually
    exercised. THE SHIPPED LINE IS STRAIGHT AND LEVEL - a test that only ran on it would be
    asserting nothing at all, which is a shape of failure this repo has shipped before."""
    cells = []
    for z in range(0, 8):
        cells.append((0, 64, z, False))
    for i in range(1, 4):                     # the climb, before the turn and clear of it
        cells.append((0, 64 + i, 8 + i - 1, False))
    cells.append((0, 67, 11, True))           # corner: turn east
    for x in range(1, 6):
        cells.append((x, 67, 11, False))
    cells.append((6, 67, 11, True))           # corner: turn south
    for z in range(12, 16):
        cells.append((6, 67, z, False))
    return cells


def test_a_corner_is_flat_on_both_sides_and_a_slope_climbs_the_way_it_says():
    cells = _bent_path()
    assert sum(1 for c in cells if c[3]) == 2, "the fixture must actually contain corners"
    shapes = shapes_for(cells)
    assert any(s.startswith("ascending_") for s in shapes), "the fixture must contain a slope"
    assert any(s in ("north_east", "north_west", "south_east", "south_west") for s in shapes)
    assert _track_rules(cells, shapes) == []


def test_the_rule_actually_refuses_a_descent_into_a_corner():
    """NEVER DESCEND INTO A CORNER: a curve has no ascending shape, so the game re-derives the
    turn as a slope and the line dead-ends. The negative control matters more than the positive
    one - a checker that passes everything passes a broken railway too."""
    cells = _bent_path()
    i = next(k for k, c in enumerate(cells) if c[3])
    cells[i - 1] = (cells[i - 1][0], cells[i - 1][1] + 1, cells[i - 1][2], False)
    assert _track_rules(cells, shapes_for(cells)) != []


def test_the_shipped_line_has_no_corner_and_therefore_no_iron(line):
    c, _m, _cells = line
    p = _cfg()
    cells = transit.plan(p)
    assert c.meta["corners"] == 0
    assert _track_rules(cells, shapes_for(cells)) == []
    assert all(not cell[3] for cell in cells), \
        "a corner would be a plain rail, and the whole economy of this line is that there is none"


def test_power_is_dealt_per_run_not_on_a_flat_spacing():
    """The property that a flat spacing breaks: put a corner mid-line and both sides of it must
    still be powered at their own ends, because a plain rail does not carry the chain."""
    cells = _bent_path()
    picks = power_cells(cells, 8)
    for a, b in runs_of(cells):
        assert a in picks and b - 1 in picks, f"run {a}..{b} is not powered at both ends"


# --------------------------------------------------------------------------- getting on it

def test_you_can_board_on_foot_from_every_zone(line, zones):
    """THE ONE THAT DECIDES WHETHER ANY OF THIS IS USABLE. A platform you can see from the plaza
    is not a platform you can board. Seeded from the ZONES' OWN GROUND - this repo has shipped a
    228-cell platform walled off from its own track, and the first test written for it was
    VACUOUS because it seeded in the void and flooded nothing."""
    c, _m, cells = line
    world = dict(zones)
    world.update(cells)
    seeds = [(x, 203, z) for (x, y, z) in zones
             if y == 202 and x <= 97639 and _stand(world, (x, 203, z))]
    assert len(seeds) > 4000, \
        f"only {len(seeds)} seed cells of real park ground - the flood would prove nothing"
    reach = _walk(world, seeds)
    for st in c.meta["stations_built"]:
        for b in st["boarding"]:
            assert tuple(b) in reach, \
                f"{st['title']}: you cannot walk from the park to the boarding rail at {b}"
        for pad in st["pad"]:
            assert (pad[0], pad[1] + 1, pad[2]) in reach, \
                f"{st['title']}: the stair's own landing pad is cut off from the zone"


def test_the_walkway_is_continuous_from_one_island_to_the_next(line):
    """SOMEONE WHO MISSES THE TRAIN CAN WALK IT. The deck carries a walkway as well as a track,
    and the boarding fence at each station must not cut it: the through lanes run behind the
    fence, which is the only reason a station can have a real barrier at all."""
    c, _m, cells = line
    reach = _walk(cells, [tuple(c.meta["stations_built"][0]["boarding"][0])])
    for st in c.meta["stations_built"]:
        for b in st["boarding"]:
            assert tuple(b) in reach, f"the deck walk does not reach {st['title']}"
    rail = [tuple(r) for r in c.meta["rail"]]
    assert all(r in reach for r in rail), "part of the deck cannot be walked to"
    assert len(reach) > 3 * len(rail), "a one-cell-wide thread is not a walkway"


def test_the_boarding_gate_is_a_real_gate_in_a_real_fence(line):
    """A platform with no barrier is just more walkway and nothing says where you get on."""
    _c, _m, cells = line
    kinds = {_base(s) for s in cells.values()}
    assert any(k.endswith("_fence_gate") for k in kinds)
    assert any(k.endswith("_fence") for k in kinds)


# --------------------------------------------------------------------------- nothing floats

def test_the_whole_line_is_one_connected_piece(line):
    """6-CONNECTIVITY: a cell whose only neighbours are diagonal is not attached to anything.
    This caught the landing pad shipping as a nine-cell island beside its own stair, because
    the stringer under the lowest tread stopped one course above the street."""
    _c, _m, cells = line
    assert _components(cells) == [len(cells)]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_every_kind_is_one_connected_piece(kind, land):
    c = transit.build(_small(kind, land))
    assert _components(_cells(c.to_model(), c.world_origin)) == [len(c.to_model().ids.nonzero()[0])]


def test_the_span_hangs_from_the_deck_and_the_piers_reach_its_underside(line):
    """A pier over the void reaches nothing - there is nothing to reach - so what makes it not
    floating is that it is attached to the deck it carries. Assert the relationship rather than
    a support block that cannot exist: every cell below the deck must climb to the deck course
    through its own neighbours, which one connected component already gives; what this adds is
    that the pier bottoms really are below the deck and really are joined."""
    c, _m, cells = line
    deck_y = int(c.meta["line_origin"][1]) - 1
    below = [k for k in cells if k[1] < deck_y]
    assert below, "a viaduct with nothing under it is a plank"
    assert min(k[1] for k in below) == deck_y - int(_cfg()["pier_depth"])


# --------------------------------------------------------------------------- the light

def test_nothing_spawnable_on_the_line_is_dark(line):
    """UNLIT, A SPAN OVER THE VOID IS A MOB HIGHWAY INTO THE PARK - and the surfaces that matter
    are not only the ones a visitor walks on. Measured, the first build had 540 spawnable cells
    at block light zero: the deck itself where a portal post capped a froglight, the far kerb
    and the portal beams over it because every lamp was on one edge, the station canopy ROOFS,
    and the piers' own flared bases nine courses down. `nightlight` is the one source for what
    emits, what light passes and what a mob can stand on, so this cannot disagree with the
    design's own reasoning about it."""
    _c, m, _cells = line
    # THE FULL STATES, not `m.names` - a bottom slab and a top slab are the same NAME and only
    # one of them is a thing a mob can stand on, so the classifier needs the properties.
    opaque, emit, passy, spawn, _water = nightlight.classify(_states(m))
    ids = m.ids
    light = nightlight.propagate(opaque[ids], emit[ids])
    clear = passy[ids] | (ids == 0)
    standable = spawn[ids]
    ny = ids.shape[0]
    dark = []
    for y in range(ny - 1):
        zz, xx = np.nonzero(standable[y])
        for z, x in zip(zz.tolist(), xx.tolist()):
            head = clear[y + 2, z, x] if y + 2 < ny else True
            if clear[y + 1, z, x] and head and light[y + 1, z, x] < 1:
                dark.append((x, y + 1, z))
    assert dark == [], f"{len(dark)} spawnable cells at block light 0, first {dark[:3]}"


def test_a_lamp_is_never_capped_by_a_full_block(line):
    """THE FAULT THE ABOVE EXISTS FOR, pinned directly so a change to `bay` or `light_every`
    fails HERE and says why. A froglight is flush in the deck: it IS the floor, and an opaque
    block on top of it means the light never reaches the air at all. The lamp spacing and the
    bay spacing are independent numbers and they WILL coincide."""
    c, _m, cells = line
    for lamp in c.meta["lamps"]:
        above = (lamp[0], lamp[1] + 1, lamp[2])
        state = cells.get(above)
        assert not (state and blocks.is_full_cube(_base(state))), \
            f"the lamp at {lamp} is capped by {state} and lights nothing"
    assert c.meta["lamps_unplaceable"] == 0


# --------------------------------------------------------------------------- signs and stairs

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_every_sign_has_a_block_and_a_support_behind_it(kind, land):
    """`park._sign`'s rule, restated: four of the park's seven kinds shipped a sign hung on the
    one column that has an opening in it, and a wall sign floating in air draws exactly like one
    on a wall in every render this repo has."""
    p = _small(kind, land)
    w = transit.World()
    transit.BUILDERS[kind](w, {**transit.TRANSIT, **p}, None)
    assert w.signs, f"{kind}/{land} placed no sign at all"
    for (x, y, z) in w.signs:
        assert (x, y, z) in w.cells, "sign TEXT with no sign BLOCK is a corrupt region"
        _name, props = w.cells[(x, y, z)]
        fdx, fdz = park._STEP[props["facing"]]
        assert (x - fdx, y, z - fdz) in w.cells, f"{kind}/{land}: sign at {(x, y, z)} floats"


def test_every_station_and_tower_is_actually_NAMED(line):
    """A sign the support guard REFUSED is a sign that silently does not exist, which is this
    project's most-repeated failure shape."""
    c, _m, _cells = line
    for st in c.meta["stations_built"]:
        assert st["named"], f"{st['title']} lost its nameplate"
        assert st["board"], f"{st['title']} lost its departure board"
    for f in c.meta["features_built"]:
        assert f["named"], f"the tower at {f['at']} lost its sign"


def test_no_sign_line_is_wider_than_the_sign(line):
    """Fifteen characters. A longer line clips mid-word and the failure only appears in a
    screenshot taken after the thing is built."""
    p = _cfg()
    w = transit.World()
    transit.BUILDERS["line"](w, {**transit.TRANSIT, **p, "title": "A VERY LONG NAME INDEED"}, None)
    for t in w.signs.values():
        for ln in list(t["front"]) + list(t["back"]):
            assert len(ln) <= transit.SIGN_WIDTH, f"{ln!r} clips"


def test_the_flight_treads_lean_the_way_they_ascend(line):
    """A STAIR'S TALL SIDE IS ITS `facing`, and a flight ascending toward D has every tread
    `facing=D, half=bottom`. Built the other way the risers face into the descent and you
    cannot walk up it - and OUR RENDERER DRAWS BOTH DIRECTIONS IDENTICALLY, so this is asserted
    and never eyeballed. The bench stairs are excluded by name, because a bench is one course
    with no rise and the rule does not apply to it."""
    c, _m, cells = line
    for st in c.meta["stations_built"]:
        flight = [tuple(f) for f in st["flight"]]
        assert flight, f"{st['title']} has no stair"
        bench = {tuple(b) for b in st["bench"]}
        assert not (set(flight) & bench)
        # the flight ascends back toward the platform, which is -stair_dir along the line
        ys = sorted({f[1] for f in flight})
        assert len(ys) >= 3, "a four-course drop wants a four-tread flight"
        facings = set()
        for f in flight:
            state = cells[f]
            assert "half=bottom" in state, f"{f} is an upside-down tread in a flight"
            facings.add(state[state.index("facing=") + 7:].split(",")[0].rstrip("]"))
        assert len(facings) == 1, f"{st['title']}: a flight faces one way, got {facings}"
        face = facings.pop()
        # ...and that way is UP the flight: the higher tread lies in the facing direction
        dx, dz = park._STEP[face]
        top = max(flight, key=lambda f: f[1])
        low = min(flight, key=lambda f: f[1])
        step = (top[0] - low[0], top[2] - low[2])
        assert (dx and step[0] * dx > 0) or (dz and step[1] * dz > 0), \
            f"{st['title']}: treads face {face} but the flight climbs {step}"


# --------------------------------------------------------------------------- the boundary

def test_the_line_stays_inside_the_plots_shared_x_band(line):
    """THE PLOT IS FOUND, NOT TYPED - and this is the check the Island Run did not have when it
    shipped 120 cells over the edge. Only X is gated: the three plots share one X and differ
    only in Z, and the void between two of them in Z is exactly what this design exists to
    cross, so a Z gate would be guarding the wrong thing."""
    c, _m, cells = line
    lo, hi = c.meta["x_band"]
    assert (lo, hi) == (97551, 97649)
    over = [k for k in cells if not lo <= k[0] <= hi]
    assert over == [], f"{len(over)} cells past the plot edge, first {over[0]}"


def test_not_found_is_not_the_same_as_inside():
    """A boundary guard that silently passes everything is the failure it exists to prevent,
    wearing the opposite hat. With no capture to read a bedrock out of there is no band, and the
    build says so by not claiming one rather than by reporting a pass."""
    c = transit.build(_small("line"))
    assert "x_band" not in c.meta


def test_no_cell_of_the_line_shares_a_cell_with_a_park_zone(line, zones):
    """CROSS-DESIGN OVERLAP IS ITS OWN QUESTION. `finish.verify_against` audits a design against
    a CAPTURE, and the capture of these islands is 144 blocks of starter pad - so every zone and
    this line honestly report overlap 0 against the world while being free to collide with each
    other. The casino shipped a hall drawn across eighteen room floors that way."""
    _c, _m, cells = line
    clash = sorted(k for k in cells if k in zones)
    assert clash == [], f"{len(clash)} cells collide with a park zone, first {clash[:3]}"


def test_a_track_cell_may_never_yield_to_another_design():
    """A TRACK CELL IS NOT OPTIONAL. Dressing may yield anywhere; a rail that yields is a GAP,
    and a gap in a line hanging over the void is a cart in the void - and it audits clean,
    because the deck under it is still one connected solid. So the build refuses outright rather
    than skipping and reporting."""
    p = {**_cfg()}
    # aim the corridor straight through the middle of the centre zone
    p["at"] = [97600, 207, 80421]
    with pytest.raises(ValueError, match="claimed by another design|outside the plots"):
        transit.build(p)


def test_the_stations_yield_only_below_the_deck(line):
    """The stair's pad and stringer are the ONLY things allowed to give way to the park, and
    what they give way to is the zone's own floor - which is what makes the two designs meet
    instead of fight. Anything above the deck yielding would be a hole in the viaduct."""
    c, _m, _cells = line
    skipped = sum(st["skipped_to_park"] for st in c.meta["stations_built"])
    assert 0 < skipped < 40, \
        f"{skipped} cells yielded: too many means the station is sited on top of the zone"


def test_the_sidecar_origin_is_the_PASTE_origin(line):
    """A generator's meta is merged straight into the sidecar, and the sidecar's `origin` is
    where Litematica pastes the file. A meta key called `origin` overwrote it with the line's
    own first rail cell - which places the whole design six east, ten up and two south of where
    it belongs, silently, with nothing in the file to say so. The line's own datum is
    `line_origin`, and the two must never be the same key again."""
    c, _m, _cells = line
    assert "origin" not in c.meta
    assert c.meta["line_origin"] == list(_cfg()["at"])


def test_the_only_known_conflict_is_the_casino_and_it_is_BOUNDED(line):
    """A KNOWN CONFLICT RECORDED IS WORTH MORE THAN A CLAIM, and this one is not ours to settle.

    `Casino Complete` stands on newisle at X 97556..97643 / Z 80555..80643 - and it already
    shares **2,356 cells with `Park_Centre Complete`**, so the middle island currently holds two
    designs that cannot both be built. Its east wall runs the full length of the plot at X 97643,
    Y203-208, with a floor apron out to X 97640 at Y203, which is exactly the ground a station
    stair has to land on.

    So the corridor was moved one column east until the LINE ITSELF is clean - deck, track,
    piers, arches and towers all clear of the casino as well as of the park - and what is left is
    confined to the Midway station's own platform and flight. This test pins that boundary: if a
    change starts putting the RAILWAY through the casino, or the conflict grows past the one
    station, it fails and says so. It does not assert zero, because zero is a decision about
    which of two other designs is authoritative and that decision is Jack's.
    """
    c, _m, cells = line
    m = schem.load(f"out/{CASINO}.litematic")
    with open(f"out/{CASINO}.scan.json", encoding="utf-8") as fh:
        o = json.load(fh)["origin"]
    casino = _cells(m, (o["x"], o["y"], o["z"]))
    clash = sorted(set(cells) & set(casino))
    rail = {tuple(r) for r in c.meta["rail"]}
    assert not (rail & set(casino)), "the RAILWAY is inside the casino - move the corridor"
    deck_y = int(c.meta["line_origin"][1]) - 1
    assert all(k[1] <= deck_y for k in clash), "the conflict has reached the deck course or above"
    mid = next(st for st in c.meta["stations_built"] if st["land"] == "midway")
    lo, hi = mid["a0"] - 8, mid["a1"] + 8
    z0 = int(c.meta["line_origin"][2])
    assert all(z0 + lo <= k[2] <= z0 + hi for k in clash),         "the conflict has spread past the Midway station's own footprint"
    assert len(clash) < 60, f"the casino conflict has grown to {len(clash)} cells"
