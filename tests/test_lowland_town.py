"""The lowland town: hamlet, campanile, turtle (2026-08-22; the harbor light is retired).

The properties pinned here are the ones that shipped wrong once, in this ensemble or in the
builds it inherits from: a lane paved through its own street lamp, a lintel floating over a
doorway, a crenellation course repainted into a plain drum, flippers that came off as their own components, and water columns claimed
by a design whose whole rule is that the pond keeps every cell it owns.
"""
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
import yaml

from mcbuild.gen import GENERATORS
from mcbuild.gen.vertical import Ctx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = os.path.join(ROOT, "out", "island_full.litematic")

needs_world = pytest.mark.skipif(not os.path.exists(FULL),
                                 reason="needs out/island_full.litematic")


def _cfg(name):
    return yaml.safe_load(open(os.path.join(ROOT, "configs", name)))


def _cells(gen, params):
    from mcbuild import nbt
    c = GENERATORS[gen].build(params, None)
    m = c.to_model()
    ox, oy, oz = c.world_origin
    cells = {}
    for i, entry in enumerate(m.palette):
        short = nbt.state_name(entry).split(":")[-1]
        if short in ("air", "cave_air", "void_air"):
            continue
        props = nbt.state_props(entry)
        if props:
            short += "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"
        ys, zs, xs = np.where(m.ids == i)
        for y, z, x in zip(ys, zs, xs):
            cells[(int(x) + ox, int(y) + oy, int(z) + oz)] = short
    return c, cells


@pytest.fixture(scope="module")
def hamlet():
    return _cells("hamlet", _cfg("lowland_hamlet.yaml")["params"])


@pytest.fixture(scope="module")
def campanile():
    return _cells("campanile", _cfg("lowland_campanile.yaml")["params"])


@pytest.fixture(scope="module")
def turtle():
    return _cells("turtle", _cfg("lowland_turtle.yaml")["params"])


@pytest.fixture(scope="module")
def ctx():
    return Ctx(FULL)


# ---------------------------------------------------------------- the hamlet

@needs_world
def test_no_hamlet_cell_stands_in_a_lantern_column(hamlet):
    p = _cfg("lowland_hamlet.yaml")["params"]
    forbid = {(int(a), int(b)) for a, b in p["lantern_grid"]}
    _c, cells = hamlet
    hits = [(x, y, z) for (x, y, z) in cells if (x, z) in forbid]
    assert hits == []


@needs_world
def test_every_door_frame_stands_whole_whatever_fell(hamlet):
    """The ruin is the wall, never the doorway - and the lintel sits between jamb tops,
    never floating over the opening."""
    p = _cfg("lowland_hamlet.yaml")["params"]
    _c, cells = hamlet
    for h in p["houses"]:
        ax, az = h["at"]
        FY = h["floor_y"]
        zf = az - h["l"] // 2            # every house doors north
        for dx in (-1, 1):
            for k in range(3):
                assert (ax + dx, FY + 1 + k, zf) in cells, (h["state"], "jamb", dx, k)
        assert (ax, FY + 3, zf) in cells, (h["state"], "lintel")
        assert (ax, FY + 1, zf) not in cells and (ax, FY + 2, zf) not in cells, \
            (h["state"], "the doorway is filled")


@needs_world
def test_the_whole_house_is_roofed_and_the_roofless_one_is_not(hamlet):
    p = _cfg("lowland_hamlet.yaml")["params"]
    _c, cells = hamlet

    def stairs_over(h):
        ax, az = h["at"]
        r = h["w"] // 2 + 1
        return sum(1 for (x, y, z), n in cells.items()
                   if abs(x - ax) <= r and abs(z - az) <= h["l"] // 2 + 1
                   and n.startswith("polished_blackstone_brick_stairs")
                   and y > h["floor_y"] + 2)

    whole = next(h for h in p["houses"] if h["state"] == "whole")
    roofless = next(h for h in p["houses"] if h["state"] == "roofless")
    assert stairs_over(whole) >= 20
    assert stairs_over(roofless) == 0


@needs_world
def test_the_hearth_lantern_stands_on_something_real(hamlet, ctx):
    _c, cells = hamlet
    from mcbuild.gen.ruinring import _PASSABLE
    for (x, y, z), n in cells.items():
        if n.split("[")[0] != "soul_lantern":
            continue
        below_design = (x, y - 1, z) in cells
        below_world = ctx.name_at(x, y - 1, z) not in _PASSABLE
        assert below_design or below_world, ("soul lantern on air", x, y, z)


@needs_world
def test_the_lane_reaches_toward_the_way(hamlet):
    _c, cells = hamlet
    spur = [1 for (x, y, z), n in cells.items()
            if n.startswith("polished_blackstone_brick_slab") and z <= 30027]
    assert len(spur) >= 3


# ------------------------------------------------------------- the campanile

@needs_world
def test_the_crenellations_are_actually_crenellated(campanile):
    """Merlons AND gaps on the crown ring - a full course repainted is a plain drum, which
    is exactly what the void tower shipped once."""
    _c, cells = campanile
    p = _cfg("lowland_campanile.yaml")["params"]
    ax, az = p["at"]
    top = max(y for (x, y, z), n in cells.items()
              if n.startswith("chiseled") and abs(x - ax) <= 3 and abs(z - az) <= 3)
    ring = [(x, z) for x in range(ax - 3, ax + 4) for z in range(az - 3, az + 4)
            if x in (ax - 3, ax + 3) or z in (az - 3, az + 3)]
    merlons = sum(1 for (x, z) in ring if (x, top, z) in cells)
    gaps = sum(1 for (x, z) in ring if (x, top, z) not in cells)
    assert merlons >= 5 and gaps >= 5, (merlons, gaps)


@needs_world
def test_the_shear_takes_the_ne_corner_and_leaves_the_sw(campanile):
    _c, cells = campanile
    p = _cfg("lowland_campanile.yaml")["params"]
    ax, az = p["at"]
    ys = [y for (x, y, z) in cells]
    # the SW corner column runs higher than the NE one - the plane fell that way
    sw = max(y for (x, y, z) in cells if x == ax - 3 and z == az + 3)
    ne = max(y for (x, y, z) in cells if x == ax + 3 and z == az - 3)
    assert sw > ne, (sw, ne)


@needs_world
def test_the_panes_connect_along_their_wall(campanile):
    """A pane with every side false renders as a lone post, not glazing."""
    _c, cells = campanile
    panes = [n for n in cells.values() if n.startswith("glass_pane")]
    assert panes, "no glazing emitted"
    for n in panes:
        assert "north=true" in n and "south=true" in n, n


@needs_world
def test_the_bell_hangs_from_a_real_ceiling(campanile):
    _c, cells = campanile
    bells = [(x, y, z) for (x, y, z), n in cells.items() if n.split("[")[0] == "bell"]
    assert len(bells) == 1
    x, y, z = bells[0]
    n = cells[bells[0]]
    assert "attachment=ceiling" in n
    assert (x, y + 1, z) in cells, "nothing above the bell to hang from"


@needs_world
def test_the_owl_sits_on_built_masonry_and_its_eyes_lead(campanile):
    _c, cells = campanile
    wool = {(x, y, z): n for (x, y, z), n in cells.items() if n.endswith("_wool")}
    assert wool, "no owl"
    base = min(y for (x, y, z) in wool)
    for (x, y, z) in [c for c in wool if c[1] == base]:
        assert (x, y - 1, z) in cells, ("the owl floats", x, y, z)
    eyes = [(x, y, z) for (x, y, z), n in wool.items() if n.startswith("black_wool")]
    assert len(eyes) == 2
    for (x, y, z) in eyes:
        assert (x, y, z + 1) not in cells, "something stands in front of an eye"


# ----------------------------------------------------------------- the turtle

def _components(cells):
    todo = set(cells)
    comps = []
    while todo:
        seed = todo.pop()
        comp, q = {seed}, deque([seed])
        while q:
            x, y, z = q.popleft()
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
                               (0, 0, 1), (0, 0, -1)):
                n = (x + dx, y + dy, z + dz)
                if n in todo:
                    todo.remove(n)
                    comp.add(n)
                    q.append(n)
        comps.append(comp)
    return comps


@needs_world
def test_the_turtle_is_one_piece(turtle):
    _c, cells = turtle
    comps = _components(cells)
    assert len(comps) == 1, sorted(len(c) for c in comps)


@needs_world
def test_the_turtle_is_dry_but_the_water_is_close(turtle, ctx):
    _c, cells = turtle
    for (x, y, z) in cells:
        assert ctx.name_at(x, y, z) not in ("water", "ice"), (x, y, z)
    nose_x = min(x for (x, y, z) in cells)
    rows = {z for (x, y, z) in cells if x == nose_x}
    near = any(ctx.name_at(nose_x - d, y, z) == "water"
               for d in (1, 2, 3, 4) for z in rows for y in range(36, 40))
    assert near, "the turtle is nowhere near its water"


@needs_world
def test_the_eyes_lead_the_face(turtle):
    _c, cells = turtle
    p = _cfg("lowland_turtle.yaml")["params"]
    ax = p["at"][0]
    eyes = [(x, y, z) for (x, y, z), n in cells.items()
            if n.startswith("black_wool") and x < ax - p["shell_l"] // 2]
    assert len(eyes) == 2
    for (x, y, z) in eyes:
        assert (x - 1, y, z) not in cells, "something stands in front of an eye"


@needs_world
def test_the_shell_reads_in_plan(turtle):
    """Plates AND seams on the dome's own top surface - the pattern IS the animal."""
    _c, cells = turtle
    top = {}
    for (x, y, z), n in cells.items():
        if (x, z) not in top or y > top[(x, z)][0]:
            top[(x, z)] = (y, n)
    names = [n.split("[")[0] for _y, n in top.values()]
    plates = names.count("brown_wool")
    seams = names.count("black_wool")
    assert plates >= 12 and seams >= 12, (plates, seams)
    assert 0.25 <= plates / (plates + seams) <= 0.75, (plates, seams)
