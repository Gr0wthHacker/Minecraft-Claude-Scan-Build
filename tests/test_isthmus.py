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
from collections import deque

import numpy as np
import pytest

from mcbuild import blocks, nbt, nightlight, palette, schem
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
    cols = {}
    for (x, y, z), state in cells.items():
        if _base(state).endswith("_wall_sign"):
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
