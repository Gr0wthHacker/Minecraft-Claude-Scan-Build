"""The Island Line's contracts.

Almost everything here pins something that produces a CLEAN AUDIT AND A BROKEN RAILWAY: a schematic
with zero problems, zero overlap and a correct bill of materials that a minecart cannot ride. The
audit can only see that the design is one connected solid; it has no idea what a rail is for.
"""
import json
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import blocks, schem                                    # noqa: E402
from mcbuild.gen import railspiral as rs                             # noqa: E402

CFG = os.path.join("configs", "rail_spiral.yaml")
SHIPPED = os.path.join("out", "Rail Spiral.litematic")
SIDECAR = os.path.join("out", "Rail Spiral.scan.json")


@pytest.fixture(scope="module")
def params():
    return yaml.safe_load(open(CFG, encoding="utf-8"))["params"]


@pytest.fixture(scope="module")
def cells(params):
    """Through `plan`, the same entry point the build uses - computing the route a second way here
    is how the stop-block test came to fail against a design that has stop blocks."""
    return rs.plan(params)


# --------------------------------------------------------------------------- the game's own rules

def test_a_powered_rail_has_no_curved_shape():
    """The fact the whole design turns on, read off the registry rather than remembered. If this
    ever fails the corners could be gold and the iron argument evaporates."""
    db = json.load(open(os.path.join("mcbuild", "data", "blocks.json"), encoding="utf-8"))
    curves = {"south_east", "south_west", "north_west", "north_east"}
    assert curves & set(db["rail"]["props"]["shape"]) == curves
    assert not curves & set(db["powered_rail"]["props"]["shape"])


def test_every_corner_is_a_normal_rail_and_every_straight_is_powered(cells):
    shapes = rs.shapes_for(cells)
    curves = {"south_east", "south_west", "north_west", "north_east"}
    for (x, y, z, corner), shape in zip(cells, shapes):
        if corner:
            assert shape in curves, f"corner at {(x, y, z)} emitted {shape}, which is not a curve"
        else:
            assert shape not in curves, f"straight at {(x, y, z)} emitted a curve"


def test_no_corner_is_ever_on_a_slope(cells):
    """A curve has no ascending shape. Drop into a corner and the game re-derives the turn as a
    slope: the line dead-ends, and nothing in the model, the audit or the BOM looks wrong."""
    for i, (x, y, z, corner) in enumerate(cells):
        if not corner:
            continue
        for j in (i - 1, i + 1):
            if 0 <= j < len(cells):
                assert cells[j][1] == y, (
                    f"corner at {(x, y, z)} has a neighbour at y={cells[j][1]} - it would slope")


def test_a_slope_ascends_toward_the_higher_neighbour(cells):
    """The lower cell of a step carries the ascending shape, pointing at the cell above it."""
    shapes = rs.shapes_for(cells)
    seen = 0
    for i in range(1, len(cells)):
        x, y, z, _ = cells[i]
        px, py, pz, _ = cells[i - 1]
        if py != y + 1:
            continue
        seen += 1
        want = rs._DIRS[(px - x, pz - z)]
        assert shapes[i] == "ascending_" + want, (
            f"{(x, y, z)} steps down from {(px, py, pz)} but emitted {shapes[i]}")
    assert seen > 100, "expected the descent to be made of steps"


def test_the_track_descends_the_whole_way(cells, params):
    """The line starts at the COURT, above the helix's own y_top - the approach spur runs out to a
    floor you can already stand on, because a helix that begins in mid-air is complete and
    unreachable."""
    start = params.get("approach_from")
    assert cells[0][1] == (start[1] if start else params["y_top"])
    assert cells[-1][1] <= params["y_bottom"] + 2
    ys = [c[1] for c in cells]
    assert ys == sorted(ys, reverse=True), "the line must never climb on the way down"


# --------------------------------------------------------------------------- power

def test_every_powered_rail_is_reached_by_a_source_on_its_own_run(cells, params):
    """An UNPOWERED powered_rail is a BRAKE, and a normal rail does not propagate the chain - so a
    source on the far side of a corner powers nothing. Runs are what must be covered, not distance."""
    every = params["power_every"]
    picks = rs.power_cells(cells, every)
    for a, b in rs.runs_of(cells):
        on_run = sorted(i for i in picks if a <= i < b)
        assert on_run, f"run {a}..{b} has no power source at all - every rail in it is a brake"
        assert on_run[0] == a and on_run[-1] == b - 1, "a run must be powered at both ends"
        for lo, hi in zip(on_run, on_run[1:]):
            assert hi - lo <= every, f"gap of {hi - lo} rails between sources exceeds {every}"


def test_a_power_source_never_lands_on_a_corner(cells, params):
    """A redstone block under a normal rail powers nothing and wastes nine redstone."""
    for i in rs.power_cells(cells, params["power_every"]):
        assert not cells[i][3]


# --------------------------------------------------------------------------- siting

def test_the_line_stays_inside_the_plot(cells):
    from mcbuild.plot import find as find_plot
    plot = find_plot("out/island_28.litematic")
    for x, y, z, _ in cells:
        assert plot.contains(x, z), f"track cell {(x, y, z)} is off the plot"


def test_it_keeps_well_clear_of_the_staircase(cells, params):
    """Jack's whole correction: the rail and the stair are separate things and must read as two."""
    (kx, kz, kr), = [tuple(c) for c in params["clear_of"]]
    worst = min(max(abs(x - kx), abs(z - kz)) for x, y, z, _ in cells)
    assert worst > kr, f"closest approach to the stair column is {worst}, inside the {kr} keep-out"
    assert worst >= 15


def test_the_line_starts_at_the_courtyard(cells, params):
    """Jack: the rail should start and connect to the courtyard at the edge. The court floor is
    Y195; the helix's own top is open air with the nearest island block 22 away."""
    from mcbuild.gen.vertical import Ctx
    start = params.get("approach_from")
    assert start, "the line no longer connects to anything you can stand on"
    x, y, z = start
    assert (x, y, z) == cells[0][:3], "the first rail is not the stated start"
    ctx = Ctx(params["under"])
    touching = [(x + dx, y, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if ctx.occupied(x + dx, y, z + dz)]
    assert touching, f"the start {start} touches no existing floor - it connects to nothing"


def test_the_approach_costs_no_iron(cells, params):
    """It shares an axis with the helix's first cell, so it needs no curve - and a curve is the
    only thing on this railway that is iron."""
    start = params.get("approach_from")
    if not start:
        pytest.skip("no approach")
    n = max(abs(start[0] - cells[0][0]), abs(start[2] - cells[0][2]))
    spur = [c for c in cells if c[1] > params["y_top"]] or cells[:1]
    assert not any(c[3] for c in spur), "the approach spur contains a corner rail"
    assert len({c[0] for c in spur}) == 1 or len({c[2] for c in spur}) == 1, (
        "the approach is not axis-aligned, so it would need corners")


def test_the_bottom_terminus_lands_on_real_ground(cells, params):
    """The first build ended 43 blocks over open void - you step out of the cart and fall. 55 of
    the 240 ring columns have no floor at all, so the line has to ASK, not assume."""
    from mcbuild.gen.vertical import Ctx
    ctx = Ctx(params["under"])
    x, y, z, _ = cells[-1]
    assert ctx.occupied(x, y - 1, z), f"terminus {(x, y, z)} has nothing under it"


def test_a_blocked_track_cell_raises_rather_than_leaving_a_gap(params):
    """The first build silently skipped two track cells and shipped 0 problems, 0 overlap and
    THREE components. A gap in a line 150 blocks up is a cart in the void, so it is fatal now."""
    p = dict(params)
    p["clear_of"] = [[p["center"][0] + p["radius"], p["center"][1], 2]]   # sit a keep-out on the ring
    with pytest.raises(ValueError, match="clear_of"):
        rs.build_railspiral(p)


# --------------------------------------------------------------------------- the shipped model

@pytest.fixture(scope="module")
def shipped():
    if not os.path.exists(SHIPPED):
        pytest.skip("Rail Spiral not generated")
    m = schem.load(SHIPPED)
    o = json.load(open(SIDECAR, encoding="utf-8"))["origin"]
    return m, (o["x"], o["y"], o["z"])


def cellmap(shipped):
    import numpy as np
    m, (ox, oy, oz) = shipped
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    air = [i for i, n in enumerate(names) if n == "air"]
    ys, zs, xs = np.where(~np.isin(m.ids, air))
    return {(int(x) + ox, int(y) + oy, int(z) + oz): names[m.ids[y, z, x]]
            for y, z, x in zip(ys, zs, xs)}


def test_every_rail_has_a_bed_directly_under_it(shipped):
    got = cellmap(shipped)
    for (x, y, z), n in got.items():
        if "rail" not in n:
            continue
        under = got.get((x, y - 1, z))
        assert under is not None, f"rail at {(x, y, z)} has nothing under it"
        assert "rail" not in under, f"rail at {(x, y, z)} is standing on another rail"


def test_nothing_is_ever_placed_on_the_track(shipped):
    """The first build stood a lantern on a powered rail: the perpendicular flips through a corner
    and the dressing offset walked back onto the line."""
    got = cellmap(shipped)
    for (x, y, z), n in got.items():
        if n in ("lantern", "soul_lantern", "ochre_froglight") or n.endswith("_wall"):
            below = got.get((x, y - 1, z), "")
            assert "rail" not in below, f"{n} at {(x, y, z)} is standing on {below}"


def test_the_line_is_one_piece(shipped):
    got = cellmap(shipped)
    start = next(iter(got))
    seen, stack = {start}, [start]
    while stack:
        x, y, z = stack.pop()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nb = (x + d[0], y + d[1], z + d[2])
            if nb in got and nb not in seen:
                seen.add(nb)
                stack.append(nb)
    assert len(seen) == len(got), f"{len(got) - len(seen)} cells are not connected to the line"


def test_both_termini_have_a_stop_block(shipped):
    """A stationary cart on a powered rail launches AWAY from an adjacent solid block. Without one
    the cart sits at the terminus and the line only runs whichever way you shove it."""
    got = cellmap(shipped)
    track = rs.plan(yaml.safe_load(open(CFG, encoding="utf-8"))["params"])
    for x, y, z, _ in (track[0], track[-1]):          # the ACTUAL ends, not the lowest cells
        neigh = [got.get((x + dx, y, z + dz), "") for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        assert any(n and "rail" not in n for n in neigh), (
            f"terminus at {(x, y, z)} has no stop block behind it")


def test_the_lighting_costs_no_iron(shipped):
    """58 lanterns came to ~52 iron against the corner rails' 4 - the LIGHTING was ten times the
    metal of the railway, on the island whose scarce metal is iron. Froglight is the fix and it is
    this island's own idiom; if a lantern ever creeps back in, that trade is being silently undone."""
    got = cellmap(shipped)
    lights = {n for n in got.values() if "froglight" in n or "lantern" in n or n == "torch"}
    assert lights, "the viaduct is unlit - it is ~2,000 new walkable cells hung in the void"
    assert not {n for n in lights if "lantern" in n}, f"iron-cost lights crept back: {lights}"


def test_it_is_all_cheap_or_ok_and_all_1_19(shipped):
    from mcbuild import palette
    got = cellmap(shipped)
    for n in set(got.values()):
        assert palette.tier(n) != "expensive", f"{n} is expensive tier"
        assert blocks.spendable(n), f"{n} is CURRENCY on this server"
        assert blocks.available(n), f"{n} is not on the 1.19 server list"


def test_work_json_does_not_pin_a_derived_rail_shape():
    """`shape` is resolved by the game from the neighbourhood, exactly as a stair's is. Recording it
    would report every correctly-placed rail as a deviation in /cscan check."""
    from mcbuild import work
    assert "shape" not in work.INTENTIONAL
    assert "powered" not in work.INTENTIONAL
    wj = os.path.join("out", "Rail Spiral.work.json")
    if not os.path.exists(wj):
        pytest.skip("work.json not shipped")
    cellsw = json.load(open(wj, encoding="utf-8"))["cells"]
    rails = [c[3] for c in cellsw if "rail" in c[3]]
    assert rails, "no rails in the work list"
    for n in rails:
        assert "[" not in n, f"work.json pinned a derived property: {n}"
