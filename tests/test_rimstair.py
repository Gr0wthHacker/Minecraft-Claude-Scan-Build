"""The rim stair down into the sky-well court.

Each of these pins something that produced a clean audit and a wrong build while it was being
written. The vine one is the reason this file exists at all.
"""
import pytest

from mcbuild.gen import rimstair
from mcbuild.gen.rimstair import build_rimstair


class FakeCtx:
    """A rim: rock at `rock_x`, a vine curtain at `vine_x` hanging over a floor at `floor_y`."""

    def __init__(self, rock_x, vine_x, floor_y=194, pool=()):
        self.rock_x, self.vine_x, self.floor_y, self.pool = rock_x, vine_x, floor_y, set(pool)

    def name_at(self, x, y, z):
        if (x, y, z) in self.pool:
            return "ice"
        if y <= self.floor_y:
            return "moss_block"
        if x == self.rock_x:
            return "cobblestone"
        if x == self.vine_x:
            return "vine"
        return "air"


BASE = dict(axis="z", cut_lane=-24221, air_lane=-24222, top=30019, bottom=30014,
            y_top=201, floor_y=194, lantern_every=0, landing=0, threshold=0, weather=0.0, seed=0)


def _cells(c):
    ox, oy, oz = c.world_origin
    out = {}
    for x in range(c.sx):
        for y in range(c.sy):
            for z in range(c.sz):
                n = c.get_name(x, y, z).replace("minecraft:", "")
                if n not in ("air", "cave_air", "void_air", "OOB"):
                    out[(x + ox, y + oy, z + oz)] = n
    return out


def test_a_vine_curtain_is_not_footing():
    """The rim's west face is vine hanging in OPEN AIR. `name_at` reports it by name, so a
    'is this empty' test written as `name not in AIRY` reads the curtain as ground and every
    stringer stops at the top of the cliff - the flight ships as twelve floating treads."""
    ctx = FakeCtx(rock_x=-24221, vine_x=-24222)
    c = build_rimstair({**BASE, "under": None})       # no ctx: nothing to stand on, nothing filled
    cells = _cells(c)
    assert cells, "built nothing"
    # with the rim ctx the air lane must be filled all the way down to the floor
    import mcbuild.gen.rimstair as rs
    saved = rs.Ctx
    rs.Ctx = lambda _u: ctx
    try:
        cells = _cells(build_rimstair({**BASE, "under": "x"}))
    finally:
        rs.Ctx = saved
    # top tread is Y201 at z30019; the floor is Y194, so Y195..Y200 must all be stringer
    for y in range(195, 201):
        assert (-24222, y, 30019) in cells, "stringer stopped on a vine at Y%d" % y


def test_the_stringer_stops_on_real_footing_and_never_fills_the_pool():
    pool = {(-24222, y, 30017) for y in range(195, 199)}
    ctx = FakeCtx(rock_x=-24221, vine_x=-24222, pool=pool)
    import mcbuild.gen.rimstair as rs
    saved = rs.Ctx
    rs.Ctx = lambda _u: ctx
    try:
        cells = _cells(build_rimstair({**BASE, "under": "x"}))
    finally:
        rs.Ctx = saved
    for c in pool:
        assert cells.get(c) != "stone_bricks", "stringer drove a pier through the pool at %s" % (c,)


def test_the_tread_cell_in_rock_is_itself_a_dig():
    """Listing only the courses ABOVE a tread says the flight is clear while the stair is still
    inside the cliff."""
    ctx = FakeCtx(rock_x=-24221, vine_x=-24222)
    import mcbuild.gen.rimstair as rs
    saved = rs.Ctx
    rs.Ctx = lambda _u: ctx
    try:
        c = build_rimstair({**BASE, "under": "x"})
    finally:
        rs.Ctx = saved
    dug = {(d[0], d[1], d[2]) for d in c.meta["dig"]}
    for i, z in enumerate(range(30019, 30013, -1)):
        assert (-24221, 201 - i, z) in dug, "tread cell at z%d not in the dig list" % z


@pytest.mark.parametrize("top,bottom,axis,want", [
    (30019, 30014, "z", "south"),      # descends north -> ascends south
    (30014, 30019, "z", "north"),      # descends south -> ascends north
    (-24219, -24224, "x", "east"),     # descends west  -> ascends east
    (-24224, -24219, "x", "west"),
])
def test_tread_facing_comes_from_the_geometry(top, bottom, axis, want):
    """A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D. Built the other way the risers face
    into the descent and you cannot walk up it - and our renderer draws both identically."""
    lanes = dict(cut_lane=-24221, air_lane=-24222) if axis == "z" else dict(cut_lane=30019, air_lane=30020)
    c = build_rimstair({**BASE, **lanes, "axis": axis, "top": top, "bottom": bottom, "under": None})
    assert c.meta["facing"] == want
    ox, oy, oz = c.world_origin
    for x in range(c.sx):
        for y in range(c.sy):
            for z in range(c.sz):
                n = c.get_name(x, y, z).replace("minecraft:", "")
                if "stairs" in n:
                    import mcbuild.nbt as nbt
                    pr = nbt.state_props(c.palette[c.get(x, y, z)])
                    assert pr["facing"] == want and pr["half"] == "bottom"


def test_every_row_gets_a_tread_in_both_lanes():
    c = build_rimstair({**BASE, "under": None})
    cells = _cells(c)
    for i, z in enumerate(range(30019, 30013, -1)):
        for lane in (-24221, -24222):
            assert "stairs" in cells.get((lane, 201 - i, z), ""), "no tread at lane %d z%d" % (lane, z)
