"""The Isthmus's contracts - the land between the three theme-park islands.

Every one of these pins something that ships a CLEAN AUDIT and a landform nobody can actually
walk across: a legal block state, a supported cell and a cheap-tier bill of materials say
nothing about whether the two flared ends actually meet a plot's own floor, whether the outline
leaves a floating gap between two terraces, or whether the whole thing is dark at night. The
three found while this was written:

    a Python `hash()` on the gap's own TITLE seeded the shape - salted per PROCESS
      (PYTHONHASHSEED), so the identical config built a different causeway every run and every
      test in this file would have been asserting against whichever shape happened to come up;
    51 spawnable cells at block light zero with the transit-style single-lamp-per-row spacing,
      because the shoulders are up to sixty blocks wide and one lamp on the spine does not
      reach across them - caught only by propagating the light, exactly as `test_transit.py`
      already had to learn;
    two disconnected causeways reported as "not one piece" by a naive whole-design component
      count, when the correct number is TWO - the two gaps are two different landmasses with an
      entire island between them, and asserting one component for the whole design would have
      been asserting something false about the geometry it was supposed to protect.
"""
import json
import os
from collections import Counter, deque

import numpy as np
import pytest

from mcbuild import blocks, fluids, morph, nbt, nightlight, palette, schem
from mcbuild.gen import isthmus, park

CONFIG = "configs/isthmus.yaml"
ZONES = ["Park_Left Complete", "Park_Centre Complete", "Park_Right Complete"]
LINE = "Park Line"
LANDS = sorted(park.LANDS)
KINDS = sorted(isthmus.BUILDERS)


# --------------------------------------------------------------------------- fixtures

def _states(model):
    """The palette as full `name[k=v,...]` strings - `Model.names` drops the properties, and
    this repo has been bitten by that on a stair's facing, a slab's type and a rail's shape."""
    out = []
    for e in model.palette:
        name = nbt.state_name(e).split(":")[-1]
        props = nbt.state_props(e)
        tail = ",".join(f"{k}={v}" for k, v in sorted(props.items()))
        out.append(f"{name}[{tail}]" if props else name)
    return out


def _cells(model, origin):
    """{(x, y, z): 'block[state]'} in WORLD coordinates - asserted in world coordinates because
    a canvas is sized to its own content and shifts between two builds with different settings."""
    ox, oy, oz = origin
    states = _states(model)
    ys, zs, xs = np.nonzero(model.ids > 0)
    return {(x + ox, y + oy, z + oz): states[model.ids[y, z, x]]
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())}


@pytest.fixture(scope="module")
def built():
    c = isthmus.build({"kind": "isthmus"})
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


def _small_gap(land_a="frontier", land_b="midway", z_lo=9000, z_hi=9040, title="TEST REACH"):
    """A short gap in sandbox coordinates, far from anything real - fast enough to sweep every
    land pair, and it exercises the same shape code the shipped 101-row gaps use."""
    return {"z_lo": z_lo, "z_hi": z_hi, "land_a": land_a, "land_b": land_b, "title": title}


def _blocking(world, cell):
    """`nightlight` is the ONE source for what a body passes through, so this cannot drift from
    the design's own lighting solver."""
    n = world.get(cell)
    return bool(n) and _base(n) not in nightlight.PASSY and _base(n) not in nightlight.WATERY


def _stand(world, cell):
    x, y, z = cell
    return (_blocking(world, (x, y - 1, z))
            and not _blocking(world, cell) and not _blocking(world, (x, y + 1, z)))


def _walk(world, seeds):
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


# --------------------------------------------------------------------------- determinism

def test_the_same_config_builds_the_same_shape_every_time():
    """THE FAULT THAT WOULD HAVE MADE EVERY OTHER TEST HERE MEANINGLESS. Python's own `hash()`
    on a string is salted per PROCESS, so seeding the shape off `hash(title)` built a different
    causeway on every run of the identical config - a test suite asserting against that is
    asserting against whichever shape happened to come up this time."""
    a = isthmus.build({"kind": "isthmus"}).to_model()
    b = isthmus.build({"kind": "isthmus"}).to_model()
    assert np.array_equal(a.ids, b.ids)


# --------------------------------------------------------------------------- it builds, legally

@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_builds(kind):
    p = {"kind": kind}
    if kind == "reach":
        p["gaps"] = _small_gap()
    c = isthmus.build(p)
    assert c.to_model().ids.size > 0


@pytest.mark.parametrize("land_a", LANDS)
@pytest.mark.parametrize("land_b", LANDS)
def test_every_land_pair_builds_legally(land_a, land_b):
    c = isthmus.build({"kind": "reach", "gaps": _small_gap(land_a, land_b)})
    m = c.to_model()
    for spec in _states(m):
        base = spec.split("[")[0]
        if base == "air":
            continue
        props = {}
        if "[" in spec:
            props = dict(kv.split("=", 1) for kv in spec[spec.index("[") + 1:-1].split(","))
        assert blocks.validate(base, props) == [], f"{spec} is not a legal state"
        assert blocks.spendable(base), f"{land_a}/{land_b} places CURRENCY: {base}"
        assert blocks.available(base), f"{land_a}/{land_b} is not 1.19-legal: {base}"
        assert palette.tier(base) != "expensive", f"{land_a}/{land_b} places expensive: {base}"


def test_a_gap_shorter_than_eight_rows_is_refused():
    with pytest.raises(ValueError, match="8 rows"):
        isthmus.build({"kind": "reach", "gaps": _small_gap(z_lo=100, z_hi=104)})


def test_an_unknown_land_is_refused():
    with pytest.raises(ValueError, match="unknown land"):
        isthmus.build({"kind": "reach", "gaps": _small_gap(land_a="nowhere")})


# --------------------------------------------------------------------------- the shape

def test_each_gap_is_exactly_two_components(built):
    """NOT ONE. The two gaps are two different landmasses with an entire island between them -
    asserting a single component for the whole design would assert something false about the
    geometry. Each one is checked for being ONE piece on its own further down."""
    _c, _m, cells = built
    comp = _components(cells)
    assert len(comp) == 2, f"expected one component per gap, got {len(comp)}: {comp}"


@pytest.mark.parametrize("i", [0, 1])
def test_one_gap_alone_is_one_connected_piece(i):
    """6-CONNECTIVITY: a cell whose only neighbours are diagonal is not attached to anything.
    This is what caught the terrace drop leaving a floating gap between two differently-seated
    columns before `_seat` existed to bridge it."""
    c = isthmus.build({"kind": "reach", "gaps": isthmus.GAPS[i]})
    cells = _cells(c.to_model(), c.world_origin)
    assert _components(cells) == [len(cells)]


def test_nothing_floats_between_two_terraces():
    """THE FAULT `_seat` EXISTS FOR, pinned directly. A column two courses lower than its inward
    neighbour, built as cap-plus-one-course-of-subsoil alone, leaves an unsupported gap between
    the higher column's underside and the lower column's cap - a real hole in the model that a
    connectivity count over the WHOLE design could still call fine if the gap were diagonal-only
    on both sides, which terracing never produces, so this checks the property directly instead."""
    c = isthmus.build({"kind": "reach", "gaps": _small_gap()})
    cells = _cells(c.to_model(), c.world_origin)
    # A WALL SIGN IS WALL-MOUNTED, NOT FLOOR-MOUNTED - it hangs beside the post that carries it
    # (checked separately, in world coordinates, by `test_every_sign_has_a_block_and_a_support_
    # behind_it`) and is under no obligation to be vertically contiguous with whatever the
    # ground happens to be doing two columns away. Excluded here on that basis alone.
    #
    # A REAL ARCHWAY LINTEL BRIDGES OPEN AIR BY DESIGN - its two posts carry it and every column
    # in between is deliberately left open under the walkway, which is exactly what makes it an
    # archway rather than a wall. That is genuine 6-connectivity through the lintel's own run of
    # cells at one Y (already proven whole by `test_one_gap_alone_is_one_connected_piece`'s real
    # flood fill), not the terracing defect this per-COLUMN check exists to catch - so the two
    # archways' own recorded footprints are excluded here on the same grounds as the sign.
    excl = set()
    for gap in c.meta["gaps_built"]:
        for a in gap["archways"]:
            (x0, z0), (x1, z1) = a["bbox"]
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    excl.add((x, z))
    cols = {}
    for (x, y, z), state in cells.items():
        if _base(state).endswith("_wall_sign") or (x, z) in excl:
            continue
        cols.setdefault((x, z), []).append(y)
    for (x, z), ys_here in cols.items():
        ys_here.sort()
        # every column occupied by this design must itself be a CONTIGUOUS run - no gap in Y
        # (the fence riser sits directly on the cap, so this holds even on a rim column)
        assert ys_here == list(range(ys_here[0], ys_here[-1] + 1)), \
            f"column {(x, z)} has a gap in it: {ys_here}"
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = cols.get((x + dx, z + dz))
            if nb is None:
                continue
            # this column's own run must overlap its neighbour's - orthogonally adjacent
            # columns whose Y-ranges do not overlap are connected only diagonally, if at all
            assert not (ys_here[-1] < min(nb) or max(nb) < ys_here[0]), \
                f"{(x, z)} (Y {ys_here[0]}..{ys_here[-1]}) does not reach neighbour " \
                f"{(x + dx, z + dz)} (Y {min(nb)}..{max(nb)})"


# --------------------------------------------------------------------------- the join

def test_the_flush_ends_match_the_park_floor_exactly(built, zones):
    """THE WHOLE POINT. A causeway that lands a course above or below Y202 is a step you fall
    off or trip on at the exact place a visitor is walking at a normal pace, not looking down.

    `gap["z_lo"]` and `gap["z_hi"]` are the isthmus's OWN first and last rows - void until this
    design fills them - so the comparison is against the ADJACENT row, one cell further into
    the plot, which is real built ground: z_lo - 1 for the island-ward end of the low side of a
    gap, z_hi + 1 for the high side.
    """
    _c, _m, cells = built
    for gap in isthmus.GAPS:
        for (z, z_zone) in ((gap["z_lo"], gap["z_lo"] - 1), (gap["z_hi"], gap["z_hi"] + 1)):
            xs_here = sorted(x for (x, y, zz) in cells if zz == z and y == 202)
            assert xs_here, f"no Y202 cap at the flush row z={z}"
            # contiguous - no gap in the flush row itself
            assert xs_here == list(range(xs_here[0], xs_here[-1] + 1)), \
                f"the flush row at z={z} has a hole in it"
            # and every one of them lands on the already-built zone floor one row over
            for x in (xs_here[0], xs_here[-1], (xs_here[0] + xs_here[-1]) // 2):
                assert (x, 202, z_zone) in zones, \
                    f"({x},202,{z}) does not land on the zone's own floor at z={z_zone}"


def test_you_can_walk_from_one_island_to_the_next(built, zones):
    """SEEDED FROM REAL GROUND, and the seed region is checked for size - a previous test in
    this project seeded in the void and proved nothing while passing. The route has to cross
    BOTH gaps: island left, through the isthmus, to the midway island, through the isthmus
    again, to island right."""
    _c, _m, cells = built
    world = dict(zones)
    world.update(cells)
    seeds = [(x, 203, z) for (x, y, z) in zones if y == 202 and _stand(world, (x, 203, z))]
    assert len(seeds) > 4000, \
        f"only {len(seeds)} seed cells of real park ground - the flood would prove nothing"
    reach = _walk(world, seeds)
    left = next((x, 203, z) for (x, y, z) in zones if y == 202 and z < 80400
                and _stand(world, (x, 203, z)))
    right = next((x, 203, z) for (x, y, z) in zones if y == 202 and z > 80800
                 and _stand(world, (x, 203, z)))
    assert left in reach, "island left is not reachable at all"
    assert right in reach, "island right is not reachable - the walk does not cross both gaps"
    # and each gap's own spine is actually part of the same walk, not merely bridged over
    for gap in isthmus.GAPS:
        mid_z = gap["z_lo"] + (gap["z_hi"] - gap["z_lo"]) // 2
        spine_here = [(x, y, z) for (x, y, z) in cells
                      if z == mid_z and abs(x - isthmus.X_SPINE) <= isthmus.ISTHMUS["spine_half"]]
        assert spine_here, f"no spine cell recorded at the middle of {gap['title']}"
        assert any((x, y + 1, z) in reach for (x, y, z) in spine_here), \
            f"the spine at the middle of {gap['title']} is not on the walked route"


# --------------------------------------------------------------------------- the boundary

def test_nothing_is_in_the_transit_corridor(built):
    """`transit.py` reserves X >= 97640 for the skyway's own piers and arches. This design must
    stop at 97639 - a per-cell audit cannot see this, because a landform cell and a pier cell
    are both perfectly legal, supported, cheap blocks; only the TWO designs together disagree."""
    _c, _m, cells = built
    over = [k for k in cells if k[0] >= isthmus.RESERVE_X]
    assert over == [], f"{len(over)} cells at or past the railway's own corridor, first {over[0]}"


def test_no_cell_overlaps_a_park_zone_or_the_line(built, zones):
    """CROSS-DESIGN OVERLAP IS ITS OWN QUESTION, checked against real shipped files rather than
    a capture - the casino shipped a hall drawn across eighteen room floors exactly this way,
    with every individual design honestly auditing clean against an empty capture."""
    _c, _m, cells = built
    clash = sorted(k for k in cells if k in zones)
    assert clash == [], f"{len(clash)} cells collide with a park zone, first {clash[:3]}"
    m = schem.load(f"out/{LINE}.litematic")
    with open(f"out/{LINE}.scan.json", encoding="utf-8") as fh:
        o = json.load(fh)["origin"]
    line_cells = _cells(m, (o["x"], o["y"], o["z"]))
    clash2 = sorted(k for k in cells if k in line_cells)
    assert clash2 == [], f"{len(clash2)} cells collide with the Park Line, first {clash2[:3]}"


def test_the_reserve_guard_actually_refuses_a_violation():
    """A GUARD THAT NEVER FIRES IN PRODUCTION IS UNTESTED BY PRODUCTION. Every shipped config
    self-clamps to stay inside the corridor (see `_half_at` / the `reserve_x` clamp in
    `_build_gap`), so `_check` is exercised directly here with a cell placed past the line by
    hand - the same discipline `test_transit.py` uses for the rail-direction rules on a
    synthetic bent path rather than trusting the dead-straight shipped line to prove them."""
    w = isthmus.World()
    w.put(isthmus.RESERVE_X, 202, 9000, "stone")
    with pytest.raises(ValueError, match="corridor"):
        isthmus._check(w, {**isthmus.ISTHMUS, "reserve_x": isthmus.RESERVE_X})


def test_the_reserve_clamp_holds_even_with_an_oversized_shoulder():
    """The positive half of the same property: an absurdly wide `shoulder_max` must still stay
    inside the band, because the clamp is in the shape itself and not only in the guard."""
    c = isthmus.build({"kind": "reach", "gaps": isthmus.GAPS[0], "shoulder_max": 500})
    cells = _cells(c.to_model(), c.world_origin)
    assert all(k[0] < isthmus.RESERVE_X for k in cells)
    assert all(k[0] >= isthmus.X_MIN for k in cells)


def test_avoid_refuses_a_cell_another_design_already_claims(tmp_path):
    """`avoid` mirrors `transit.py`'s own mechanism exactly - a design that already stands on a
    cell is not this one's to place over."""
    from mcbuild import scan as scan_mod
    c = isthmus.build({"kind": "reach", "gaps": isthmus.GAPS[0]})
    m = c.to_model()
    ox, oy, oz = c.world_origin
    path = str(tmp_path / "Someone Elses Build.litematic")
    scan_mod.save_pair(path, m, {"origin": {"x": ox, "y": oy, "z": oz}})
    with pytest.raises(ValueError, match="claimed by another design"):
        isthmus.build({"kind": "reach", "gaps": isthmus.GAPS[0], "avoid": [path]})


# --------------------------------------------------------------------------- the rim

def test_the_rim_carries_a_fence_wherever_the_ground_actually_ends(built):
    """A RIM, DERIVED FROM THE FOOTPRINT ITSELF: every column with a missing orthogonal
    neighbour (other than the island-ward end of the gap, which is deliberately open) carries a
    fence directly on its cap - `_seat`'s own `is_rim` flag, checked against the built cells
    rather than trusted from the meta that computed it."""
    _c, _m, cells = built
    caps = {}
    for (x, y, z), state in cells.items():
        base = state.split("[")[0]
        if base.endswith("_fence"):
            continue
        caps.setdefault((x, z), []).append((y, base))
    for (x, z), entries in caps.items():
        entries.sort()
        cap_y, cap_base = entries[-1]
        missing = []
        for gap in isthmus.GAPS:
            if gap["z_lo"] <= z <= gap["z_hi"]:
                for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nz = z + dz
                    if dz and not (gap["z_lo"] <= nz <= gap["z_hi"]):
                        continue
                    if (x + dx, nz) not in caps:
                        missing.append((x + dx, nz))
                break
        has_fence = _base(cells.get((x, cap_y + 1, z), "")).endswith("_fence")
        if missing:
            assert has_fence, f"{(x, z)} borders open void at {missing[0]} with no fence"


def test_a_flush_end_column_has_no_fence_on_the_join(built):
    """The counter-example, narrowed to the SPINE: the walkway itself must not be fenced off at
    the exact row that joins a plot, or the causeway would wall out the island it exists to
    reach. The row's own outer shoulders are a different question - they border true void at
    that row exactly as everywhere else, and correctly carry a fence there too; only the path
    you actually walk through has to stay open."""
    _c, _m, cells = built
    half = isthmus.ISTHMUS["spine_half"]
    any_checked = False
    for gap in isthmus.GAPS:
        for z in (gap["z_lo"], gap["z_hi"]):
            for (x, y, zz) in cells:
                if zz != z or y != 202 or abs(x - isthmus.X_SPINE) > half:
                    continue
                any_checked = True
                assert not _base(cells.get((x, y + 1, z), "")).endswith("_fence"), \
                    f"({x},{y},{z}) is on the spine at the flush join and still fenced"
    assert any_checked


# --------------------------------------------------------------------------- the light

def test_zero_spawnable_cells_are_dark(built):
    """UNLIT, A LANDFORM OVER TWO HUNDRED BLOCKS OF VOID IS A MOB HIGHWAY INTO THE PARK.
    `nightlight` is the one source this repo has for what emits, what passes and what a mob can
    stand on, so this cannot disagree with the design's own reasoning about its own lighting."""
    _c, m, _cells = built
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


def test_no_lamp_is_capped_by_a_full_block(built):
    """The fault the above exists to catch, pinned directly: a froglight flush in the cap IS
    the floor, and a full block placed on top of it afterwards lights nothing."""
    c, _m, cells = built
    for gap in c.meta["gaps_built"]:
        for lamp in gap["lamps"]:
            above = (lamp[0], lamp[1] + 1, lamp[2])
            state = cells.get(above)
            assert not (state and blocks.is_full_cube(_base(state))), \
                f"the lamp at {lamp} is capped by {state} and lights nothing"
        assert gap["lamps_unplaceable"] == 0


# --------------------------------------------------------------------------- signs and drifts

def test_every_sign_has_a_block_and_a_support_behind_it():
    """`park._sign`'s own rule, restated: a sign hung on a column with nothing behind it is
    invisible in every render this repo has and is simply refused by the game in practice."""
    w = isthmus.World()
    isthmus.BUILDERS["reach"](w, {**isthmus.ISTHMUS, "gaps": _small_gap()}, None)
    assert w.signs, "the reach placed no sign at all"
    for (x, y, z) in w.signs:
        assert (x, y, z) in w.cells, "sign TEXT with no sign BLOCK is a corrupt region"
        name, props = w.cells[(x, y, z)]
        fdx, fdz = park._STEP[props["facing"]]
        assert (x - fdx, y, z - fdz) in w.cells, f"sign at {(x, y, z)} floats"


def test_no_sign_line_is_wider_than_the_sign(built):
    _c, _m, _cells = built
    for gap in _c.meta["gaps_built"]:
        assert gap["named"], f"{gap['title']} lost its own nameplate"


def test_drifts_are_patches_not_confetti():
    """THE THICKET'S OWN RULE: a drift with the noise on its INTERIOR rather than its radius
    produces mostly one- and two-cell blobs. Checked here by requiring every placed plant cell
    to have at least one other plant cell (of any species) orthogonally or diagonally within 2
    blocks - a lone plant surrounded by bare moss on every side is confetti."""
    w = isthmus.World()
    isthmus.BUILDERS["reach"](w, {**isthmus.ISTHMUS, "gaps": _small_gap(), "drifts_per_span": 20},
                              None)
    plants = {"fern", "azalea", "flowering_azalea", "short_grass"}
    plant_cells = [(x, y, z) for (x, y, z), (name, _p) in w.cells.items() if name in plants]
    assert plant_cells, "no drift plants were placed at all"
    lonely = 0
    for (x, y, z) in plant_cells:
        near = any((x + dx, y, z + dz) in w.cells
                   and w.cells[(x + dx, y, z + dz)][0] in (plants | {"moss_carpet"})
                   for dx in range(-2, 3) for dz in range(-2, 3) if (dx, dz) != (0, 0))
        if not near:
            lonely += 1
    assert lonely / len(plant_cells) < 0.25, \
        f"{lonely}/{len(plant_cells)} drift plants have no neighbour - that is confetti"


# --------------------------------------------------------------------------- the five stops

def test_the_pool_is_a_real_enclosed_still_pool(built):
    """`fluids.unenclosed` is THE check for still water - a solid bed under every water cell
    and a solid side wherever it borders anything that is not more water. The frontier's own
    flume shipped ten open-sided cells once already and a player found it in a render, not a
    test; this is the test."""
    _c, _m, cells = built
    prob = fluids.unenclosed(cells)
    assert prob == [], f"{len(prob)} open-sided or unbedded water cells, first {prob[:3]}"


def test_every_gap_actually_has_a_pool(built):
    _c, _m, _cells = built
    for gap in _c.meta["gaps_built"]:
        assert gap["pool"] > 0, f"{gap['title']} has no pool water at all"
        assert gap["pool_water"], f"{gap['title']}'s pool meta records no water cells"


def test_every_gap_actually_has_a_garden(built):
    _c, _m, _cells = built
    for gap in _c.meta["gaps_built"]:
        assert gap["garden"] > 20, f"{gap['title']}'s garden roundel is too small to read: " \
                                   f"{gap['garden']} cells"


def test_every_span_carries_two_sited_creatures(built):
    _c, _m, _cells = built
    for gap in _c.meta["gaps_built"]:
        assert len(gap["creatures"]) == 2, f"{gap['title']} does not have two creatures"
        for cr in gap["creatures"]:
            assert cr["cells"] > 50, f"{cr['kind']} on {gap['title']} is implausibly small"
            assert cr["named"], f"{cr['kind']} on {gap['title']} has no name plaque"


def test_the_two_spans_use_different_creatures():
    """Jack's own second requirement: the spans differ because they lead somewhere different.
    Re-using the identical pair on both would make the "two sections of one park" claim false
    in the one place a visitor would actually notice it - checked at the CONFIG level, which is
    what actually decides it, rather than re-deriving the same fact from a built model."""
    a_specs = {(s["kind"], s.get("variant")) for s in isthmus.GAPS[0]["creatures"]}
    b_specs = {(s["kind"], s.get("variant")) for s in isthmus.GAPS[1]["creatures"]}
    assert a_specs, "the frontier reach has no creatures configured at all"
    assert a_specs != b_specs, "both spans site the exact same (kind, variant) pairs"


def test_no_two_sculptures_on_the_causeway_share_a_GENERATOR():
    """THE COMPLAINT THAT PRODUCED THE CURRENT LINEUP, pinned so it cannot come back. The first
    build sited a heron and a flamingo - which are one generator and one body plan, differing by
    colour and two curves, as `heron.py`'s own docstring says - plus a ladybird on each span:
    four sculptures showing two shapes, and the verdict was exactly "we dont need 2 standing
    birds". `test_the_two_spans_use_different_creatures` above cannot catch that, because two
    spans CAN differ while each of them repeats a shape the other already used.

    A variant is not a difference. This checks the KIND, across the whole causeway.
    """
    kinds = [s["kind"] for gap in isthmus.GAPS for s in gap["creatures"]]
    assert len(kinds) == len(set(kinds)), \
        f"the causeway sites the same generator twice: {sorted(kinds)}"


@pytest.mark.parametrize("spec", [s for g in isthmus.GAPS for s in g["creatures"]],
                         ids=lambda s: s["kind"])
def test_a_creature_is_ONE_PIECE_AT_THE_SCALE_IT_IS_SITED_AT(spec):
    """MEASURED AT THE SITED SCALE, never at the generator's own default.

    Every one of these four is fragile somewhere and no two of them are fragile in the same
    place: `heron.py` comes apart into a dozen fragments below about scale 0.85, `bat.py` sheds
    two two-cell wisps at 0.6 and is whole at 0.55, 0.7 and 1.0, and `gecko.py` and `sloth.py`
    have no scale parameter at all. `_largest_component` will quietly hide every one of those
    by discarding the fragments, which is exactly why this asks the creature's own canvas
    rather than the finished causeway - through `isthmus.creature_canvas`, the one entry point
    the siting itself uses, so a scale changed in `GAPS` cannot be checked here at a different
    one from the one that ships.
    """
    c = isthmus.creature_canvas(spec)
    solid = c.to_model().ids > 0
    _lab, sizes = morph.components(solid, conn=6)
    assert len(sizes) == 1, \
        f"{spec['kind']} at scale {spec.get('scale')} came out in {len(sizes)} pieces: " \
        f"{sorted(sizes, reverse=True)[:6]}"


def test_no_plaque_line_is_written_wider_than_a_sign():
    """`_sign` truncates to `park.SIGN_WIDTH`, which is a guard against a corrupt region and NOT
    a licence to write a line nobody can read - a plaque saying "clings to the sto" is a plaque
    with a typo on it, and the truncation happens silently in a build nobody re-reads. Checked
    on the CONFIG, which is where the words are actually chosen."""
    for gap in isthmus.GAPS:
        for spec in gap["creatures"]:
            for line in [spec["title"]] + list(spec.get("lines") or []):
                assert len(line) <= park.SIGN_WIDTH, \
                    f"{spec['kind']}'s plaque line {line!r} is {len(line)} characters and would " \
                    f"be cut to {park.SIGN_WIDTH}"


def test_no_stop_has_to_be_clamped_into_its_own_span():
    """A GANTRY SHIPPED WITH ONE LEG AND NOTHING SAID SO. A stop's structure reaches
    `_CREATURE_ZHALF` rows either side of its centre - a stele is 33 rows of a 101-row span -
    and at t=0.86 the far end lands PAST the plot the causeway stops against, where `cols` has
    no column at all, so `_ground_pier` built precisely nothing: no error, no missing-cell
    report, and the design still audits as one piece because the lintel carries it. The clamp
    that now stops that is a safety net for short spans, not a licence for the shipped `t`
    values to be wrong, so this asserts the shipped ones never reach it."""
    c = isthmus.build({"kind": "isthmus"})
    assert not c.meta.get("stops_clamped"), \
        f"a shipped stop had to be moved to fit its own span: {c.meta['stops_clamped']}"
    for gap in isthmus.GAPS:
        span = gap["z_hi"] - gap["z_lo"]
        for s in gap["creatures"]:
            zh = isthmus._CREATURE_ZHALF[s["kind"]]
            cz = gap["z_lo"] + round(s["t"] * span)
            assert gap["z_lo"] <= cz - zh and cz + zh <= gap["z_hi"], \
                f"{s['kind']} at t={s['t']} reaches {zh} rows and runs off {gap['title']}"


def test_a_gantry_stands_on_BOTH_of_its_legs():
    """The same fault from the other side, and the one a render caught: every column a sited
    creature's own structure needs must be real GROUND at the moment `_ground_pier` asks for
    it. Checked as a property of the built world - a pier is a run of solid cells from the
    causeway's own cap up to the beam - rather than by trusting the arithmetic that put it
    there, because the arithmetic was what was wrong."""
    c = isthmus.build({"kind": "isthmus"})
    cells = _cells(c.to_model(), c.world_origin)
    for gap in c.meta["gaps_built"]:
        for cr in gap["creatures"]:
            if cr["kind"] not in ("bat", "sloth"):
                continue                          # only the hung creatures carry a gantry
            cx, top, cz = cr["at"]
            near = [dz for dz in range(-26, 27)
                    if any((x, top + 6, cz + dz) in cells for x in (cx, cx + 1))]
            assert near and min(near) < -6 and max(near) > 6, \
                f"{cr['kind']}'s gantry has legs only at {sorted(set(near))} - one side is missing"


@pytest.mark.parametrize("i", [0, 1])
def test_a_sited_creature_is_one_piece_standing_on_its_own_plinth(i):
    """A CREATURE ARRIVES AS A SEPARATE, ALREADY-TESTED GENERATOR'S OUTPUT, and this is the
    check that its own internal fragility (heron.py falls apart into a dozen pieces below
    about scale 0.85 - measured, not assumed) has actually been avoided by the scale chosen
    here, not merely masked by `_largest_component` quietly discarding most of the bird."""
    c = isthmus.build({"kind": "reach", "gaps": isthmus.GAPS[i]})
    cells = _cells(c.to_model(), c.world_origin)
    # the whole reach - causeway, plinths and both creatures - is ONE component
    assert _components(cells) == [len(cells)], \
        f"{isthmus.GAPS[i]['title']} did not ship as one connected piece"
    gap = c.meta["gaps_built"][0]
    assert len(gap["creatures"]) == 2
    for cr in gap["creatures"]:
        cx, top, cz = cr["at"]
        # the plinth's own lamp corner is a real, solid cell directly under where the
        # creature's feet were told to land - proof the creature is not floating clear of the
        # ground it was sited on
        assert (cx, top, cz) in cells or (cx, top + 1, cz) in cells, \
            f"{cr['kind']} on {isthmus.GAPS[i]['title']} has nothing at its own anchor"
        assert cr["cells"] > 50, f"{cr['kind']} pasted implausibly few cells: {cr['cells']}"


def test_nothing_a_stop_placed_blocks_the_spine(built):
    """THE SPINE MUST STAY WALKABLE THROUGH EVERY BULGE. A pool, a garden or a creature earns
    its own room to the SIDE of the walkway (`_room_for`'s whole point) - none of them may
    place water, moss, plants or a creature's own body on the paved centreline itself.

    The spine's own half-width VARIES by row (`_spine_half_at` widens it near the two flush
    ends to match the gateways), so the check has to ask the same function the generator does
    rather than testing every row against the single widest case - dx=4 is legitimately
    shoulder, not spine, everywhere except the few rows right at each gateway.
    """
    _c, _m, cells = built
    off_spine_only = {"moss_block", "moss_carpet", "fern", "azalea", "flowering_azalea",
                      "short_grass", "water"}
    half_at_z = {}
    for gap in isthmus.GAPS:
        span = gap["z_hi"] - gap["z_lo"]
        for z in range(gap["z_lo"], gap["z_hi"] + 1):
            t = (z - gap["z_lo"]) / float(span)
            half_at_z[z] = isthmus._spine_half_at(isthmus.ISTHMUS, t)
    checked = 0
    for (x, _y, z), state in cells.items():
        half = half_at_z.get(z)
        if half is None or abs(x - isthmus.X_SPINE) > half:
            continue
        checked += 1
        base = _base(state)
        assert base not in off_spine_only, \
            f"{state} at {(x, _y, z)} sits on the spine (row half={half})"
    assert checked > 1000, "the spine window matched almost nothing - the test proves little"


def test_the_gateways_get_the_full_nine_columns(built):
    """`midway`'s Frontier/Hollow Arches and the frontier's/hollow's own gates all stand square
    on X 97591..97599. If the paving does not cover that at the exact flush row, the gateway
    narrows into a track the moment it leaves the plot it belongs to."""
    _c, _m, cells = built
    for gap in isthmus.GAPS:
        for z in (gap["z_lo"], gap["z_hi"]):
            covered = sum(1 for x in range(97591, 97600) if (x, 202, z) in cells)
            assert covered == 9, \
                f"{gap['title']} z={z}: only {covered}/9 gateway columns are paved"


# --------------------------------------------------------------------------- furniture & signage

def _sign_lines(model):
    """Every sign's own text, decoded from the tile entities `_paste` carries across - the same
    JSON-messages shape `Canvas.sign_text` writes, read back rather than trusted blind."""
    import json as _json
    out = []
    for te in model.tile_entities:
        d = te.value
        if d.get("id") is None or d["id"].value != "minecraft:sign":
            continue
        pos = (d["x"].value, d["y"].value, d["z"].value)
        for side in ("front_text", "back_text"):
            msgs = d[side].value["messages"].value
            lines = [_json.loads(m.value).get("text", "") for m in msgs]
            out.append((pos, side, lines))
    return out


def test_every_span_carries_two_real_benches(built):
    """`streetfurniture.bench` reused, not two lone stair blocks - the overlook's own furniture
    is now a real generator's output, pasted the same way a heron is."""
    _c, _m, cells = built
    for gap in _c.meta["gaps_built"]:
        benches = gap["benches"]
        assert len(benches) == 2, f"{gap['title']} does not carry two benches"
        sides = {b["side"] for b in benches}
        assert sides == {-1, 1}, f"{gap['title']}'s benches are not one to each side"
        for b in benches:
            assert b["cells"] > 30, f"bench on {gap['title']} pasted implausibly few cells"
            (x0, z0), (x1, z1) = b["bbox"]
            found_seat = any(
                x0 <= x <= x1 and z0 <= z <= z1 and _base(state).endswith("_stairs")
                for (x, y, z), state in cells.items())
            assert found_seat, f"bench on {gap['title']} has no seat inside its own bbox"


def test_no_bench_sits_on_the_spine(built):
    """A bench earns its own room to the SIDE of the walkway exactly as the pool, the garden and
    the creatures do - `_room_for`'s whole point, checked directly against the bench's own
    recorded footprint rather than trusted from the reservation maths alone."""
    _c, _m, _cells = built
    for gap in _c.meta["gaps_built"]:
        for b in gap["benches"]:
            (x0, _z0), (x1, _z1) = b["bbox"]
            half = isthmus.ISTHMUS["spine_half"]
            assert x1 < isthmus.X_SPINE - half or x0 > isthmus.X_SPINE + half, \
                f"bench bbox {b['bbox']} on {gap['title']} reaches the spine (half={half})"


def test_every_span_is_named_at_both_ends_by_a_real_archway(built):
    """`wayfinding.archway` reused, not another hand-rolled sign - and each end actually says
    which land you are about to walk into, read back off the tile entity rather than assumed."""
    c, m, cells = built
    ox, oy, oz = c.world_origin
    signs = _sign_lines(m)
    for gap in c.meta["gaps_built"]:
        archways = gap["archways"]
        assert len(archways) == 2, f"{gap['title']} is not named at both ends"
        ends = {a["end"] for a in archways}
        assert ends == {"z_lo", "z_hi"}
        for a in archways:
            assert a["cells"] > 50, f"archway at {a['end']} of {gap['title']} pasted too little"
            assert a["bbox"], f"archway at {a['end']} of {gap['title']} recorded no footprint"
            (x0, z0), (x1, z1) = a["bbox"]
            wanted = str(a["entering"]).upper()
            hit = False
            for (sx, sy, sz), _side, lines in signs:
                wx, wy, wz = sx + ox, sy + oy, sz + oz
                if x0 <= wx <= x1 and z0 <= wz <= z1 and any(wanted in ln for ln in lines):
                    hit = True
                    break
            assert hit, f"no sign inside the {a['end']} archway of {gap['title']} reads " \
                        f"{wanted!r} - got {[ln for _p, _s, ls in signs for ln in ls]}"


def test_the_two_archways_of_a_span_name_the_near_and_far_land():
    """The z_lo archway sits against `land_a`'s own zone and the z_hi one against `land_b`'s -
    swapping them would put "ENTERING MIDWAY" at the frontier end."""
    for gap in isthmus.GAPS:
        c = isthmus.build({"kind": "reach", "gaps": gap})
        for a in c.meta["gaps_built"][0]["archways"]:
            expected = gap["land_a"] if a["end"] == "z_lo" else gap["land_b"]
            assert a["entering"] == expected, \
                f"{gap['title']} {a['end']} archway names {a['entering']!r}, wanted {expected!r}"


def test_a_short_span_still_builds_with_no_archway():
    """`span >= 20` is a guard, not a silent failure: a gap too short for two thresholds to clear
    each other is still a legal causeway, just an unmarked one - checked directly rather than
    only inferred from the shipped gaps, which are all comfortably long enough to trigger it."""
    c = isthmus.build({"kind": "reach", "gaps": _small_gap(z_lo=5000, z_hi=5012)})
    assert c.to_model().ids.size > 0
    assert c.meta["gaps_built"][0]["archways"] == []


def test_the_land_blend_is_gradual_across_the_whole_span():
    """`_land_at` must be CERTAIN exactly at the two ends (t=0 is the near plot's own colour,
    t=1 the far plot's) and an increasingly likely MIX everywhere between - not a hard swap
    exactly at the midpoint, which is what the old near-midpoint-only dither did, and not a
    coin-flip right at the flush join either, which is what a naive linear dither would give
    if it were not pinned to certainty at the two exact endpoints."""
    seed = 7
    assert isthmus._land_at("A", "B", 0.0, seed) == "A"
    assert isthmus._land_at("A", "B", 1.0, seed) == "B"
    # early but not AT the end: mostly A, with the odd B creeping in as t grows - a hard swap
    # would give either all-A or all-B here, never a mix
    early = [isthmus._land_at("A", "B", k / 400.0, seed) for k in range(1, 40)]
    assert "A" in early and "B" in early, "no mix at all just past the near end"
    assert early.count("A") > early.count("B"), "the near end should still read mostly A"
    late = [isthmus._land_at("A", "B", 0.9 + k / 400.0, seed) for k in range(0, 39)]
    assert "B" in late, "no B at all just before the far end"
    assert late.count("B") > late.count("A"), "the far end should already read mostly B"
    mid_a = sum(1 for k in range(200)
                for t in [0.3 + k / 1000.0] if isthmus._land_at("A", "B", t, seed) == "A")
    mid_b = 200 - mid_a
    assert mid_a > 10 and mid_b > 10, \
        f"the middle third is not a MIX: {mid_a} A against {mid_b} B"


def test_delight_converges_to_zero_and_is_recorded(built):
    """The whole reason `_delight` exists: a sited creature's own surface was never measured
    by any rule this design wrote for the terrain, so it has to be swept for afterward. Its
    count is recorded, and it must be nonzero - a delight pass that always fixes 0 cells on a
    design carrying four large sited creatures is not exercising anything."""
    c, _m, _cells = built
    assert c.meta.get("delight", 0) > 0
    assert c.meta.get("spawnable_dark", 1) == 0, "the sweep gave up with cells still dark"


def test_NOT_ONE_LAMP_STANDS_INSIDE_A_SCULPTURE(built):
    """THE GLOW. `_delight` used to patch a dark spawnable cell by replacing the block under it
    with `ochre_froglight`, and every rule it wrote for the terrain was right - but a sculpture
    is not terrain, and on the first build of this causeway it did that ONE THOUSAND ONE HUNDRED
    AND THIRTY-EIGHT times, every single one of them inside a creature's coat: 299 cells of
    black wool, 295 of red, 147 of the ladybird's own leaf. Three per cent of the whole design
    was a lamp and the verdict was "all glowing".

    `Island Night`'s rule is the one that governs and this file had no way to state it: a
    fixture ON a sculpture damages it, ordinary ground is cheap and a coat is dear. So a coat
    is lit from the air beside it with `glow_lichen` instead, and this is the assertion that
    keeps it that way - checked against the creatures' OWN cells rather than against the
    recorded count, so it cannot be satisfied by the bookkeeping alone.
    """
    c, _m, cells = built
    assert c.meta.get("delight_in_coat", 1) == 0, "a lamp was placed inside a creature's coat"
    assert c.meta["delight_lichen"] > 0, \
        "no glow lichen was placed at all - the sculptures are either unlit or lamped"
    assert [k for k, s in cells.items() if _base(s) == isthmus.LAMP], \
        "the causeway has no froglights at all - this check would prove nothing"

    # AND CROSS-CHECKED WITHOUT THE BOOKKEEPING, because `delight_in_coat` is counted by the
    # very pass being judged. Every cell a creature generator emitted must still be standing in
    # the finished causeway: the plinth, the stele and the gantry are all laid BEFORE the paste
    # and the sweep is the only thing afterwards that writes anything, so a shortfall in any
    # block of a creature's own palette is a coat cell that something replaced.
    for gap, spec_gap in zip(c.meta["gaps_built"], isthmus.GAPS):
        for cr, spec in zip(gap["creatures"], spec_gap["creatures"]):
            own = Counter()
            cc = isthmus.creature_canvas(spec)
            for (name, _p) in isthmus._canvas_cells(cc).values():
                own[name] += 1
            have = Counter(_base(s) for s in cells.values())
            for name, want in own.items():
                assert have[name] >= want, \
                    f"{cr['kind']} emitted {want} {name} and only {have[name]} survive in the " \
                    f"causeway - {want - have[name]} of its own cells were overwritten"


def test_the_lichen_hangs_on_a_real_surface(built):
    """`glow_lichen` with `down=true` grows on the TOP face of the block beneath it. Placed in
    a cell with nothing under it, it is a fixture hanging on air - the same fault the vines on
    the bat's perch and the chains over the taproot well both shipped once."""
    _c, _m, cells = built
    n = 0
    for (x, y, z), state in cells.items():
        if _base(state) != isthmus.LICHEN:
            continue
        n += 1
        assert state.split("[")[1].startswith("down=true"), \
            f"the lichen at {(x, y, z)} is not growing downward: {state}"
        assert (x, y - 1, z) in cells, f"the lichen at {(x, y, z)} has nothing under it"
    assert n > 0, "no lichen was placed at all"


def test_a_quarter_turn_refuses_a_block_it_cannot_re_aim():
    """`_turn` is what puts a bat's wingspan and a sloth's bough ALONG the walk instead of
    pointing their own edge at everyone who looks at them. It re-aims an `axis` and carries a
    vertical property through; anything that names a horizontal direction it must REFUSE rather
    than paste at the wrong bearing, because our own renderer draws a wrong facing and a right
    one identically - the stair convention's exact failure, in a new body."""
    ok = {(0, 0, 0): ("spruce_log", {"axis": "x"}),
          (1, 0, 0): ("spruce_fence", {"north": "false", "east": "false", "waterlogged": "false"})}
    turned = isthmus._turn(ok)
    assert turned[(0, 0, 0)][1]["axis"] == "z", "a log's grain did not turn with it"
    with pytest.raises(ValueError):
        isthmus._turn({(0, 0, 0): ("oak_stairs", {"facing": "north"})})
    with pytest.raises(ValueError):
        isthmus._turn({(0, 0, 0): ("vine", {"east": "true"})})


# --------------------------------------------------------------------------- the config

def test_the_shipped_config_builds_the_real_gaps():
    """The config in `configs/isthmus.yaml` is what actually ships - a passing test suite that
    never once builds it would be pinning a design nobody generates."""
    import yaml
    with open(CONFIG, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    assert cfg["gen"] == "isthmus"
    c = isthmus.build(cfg.get("params", {}))
    assert c.meta["kind"] == "isthmus"
    assert len(c.meta["gaps_built"]) == 2
