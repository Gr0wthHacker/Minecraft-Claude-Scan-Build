"""The sky-well court hall.

Every one of these pins a fault that built cleanly and looked wrong, or that this court has already
paid for once in world.
"""
import pytest

from mcbuild import nbt
from mcbuild.gen import courthall
from mcbuild.gen.courthall import build_courthall

X1, X2, Z1, Z2 = -24234, -24222, 30006, 30029
PY = 195


class FakeCourt:
    """A shelf in the void: rock east and west, open sky at both ends, ceiling at Y201.

    z30023 carries a divider with court floor on BOTH sides, which is the third case."""

    def name_at(self, x, y, z):
        on_ring = (X1 <= x <= X2 and Z1 <= z <= Z2 and
                   (x in (X1, X2) or z in (Z1, Z2, 30023)))
        if y == PY and on_ring:
            return "deepslate_bricks"
        if x < X1 or x > X2:                       # the island's flanks: solid rock
            return "cobblestone" if 190 <= y <= 205 else "air"
        if z < Z1 or z > Z2:                       # both ends have fallen away
            return "air"
        if y == PY:
            return "stone_bricks"                  # court floor
        if y == PY - 1 and 30024 <= z <= 30028:
            return "moss_block"                    # the sunken bay's skin
        if y >= 201:
            return "cobblestone"                   # the island's underside
        return "air"


BASE = dict(under="x", box=[X1 - 2, Z1 - 2, X2 + 2, Z2 + 2], plinth_y=PY, bay=3, height=5,
            container_clear=0, mood_every=0, weather=0.0, ruin=0.0, ruin_hard=0.0, seed=0)


def _build(**over):
    saved = courthall.Ctx
    courthall.Ctx = lambda _u: FakeCourt()
    try:
        return build_courthall({**BASE, **over})
    finally:
        courthall.Ctx = saved


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


def test_a_run_with_rock_behind_it_is_never_glazed():
    """The room's own interior is open by definition. Scoring both perpendicular directions and
    taking the more open one made EVERY run glazed - a window onto stone."""
    cells = _cells(_build())
    for x in (X1, X2):
        glass = [c for c, n in cells.items() if c[0] == x and Z1 < c[2] < Z2 and n == "glass_pane"]
        assert not glass, "glazed the rock flank at x%d (%d panes)" % (x, len(glass))


def test_the_open_ends_are_glazed():
    cells = _cells(_build())
    for z in (Z1, Z2):
        glass = [c for c, n in cells.items() if c[2] == z and n == "glass_pane"]
        assert len(glass) >= 8, "end z%d got only %d panes" % (z, len(glass))


def test_a_rock_flank_gets_pilasters_not_a_filled_wall():
    """Filling the bays would hide the island's own flank - the most apocalyptic surface in the
    room - behind 120 blocks of tidy deepslate."""
    cells = _cells(_build())
    west = [c for c in cells if c[0] == X1 and Z1 < c[2] < Z2 and c[1] > PY]
    zs = {c[2] for c in west}
    assert zs, "no pilasters at all"
    # piers stand on the bay rhythm, so consecutive z should NOT all be occupied
    assert len(zs) < (Z2 - Z1 - 1) * 0.6, "the flank is filled, not articulated (%d of %d)" % (
        len(zs), Z2 - Z1 - 1)


def test_the_divider_with_court_on_both_sides_is_a_balustrade():
    cells = _cells(_build())
    mid = [n for c, n in cells.items() if c[2] == 30023 and c[1] == PY + 1]
    assert mid, "divider got nothing"
    assert all("wall" in n for n in mid), "divider is %s, not a balustrade" % set(mid)


def test_panes_carry_their_connection_state():
    """A pane with every side false renders as a lone post rather than as glazing."""
    c = _build()
    ox, oy, oz = c.world_origin
    seen = 0
    for x in range(c.sx):
        for y in range(c.sy):
            for z in range(c.sz):
                if c.get_name(x, y, z).replace("minecraft:", "") != "glass_pane":
                    continue
                p = nbt.state_props(c.palette[c.get(x, y, z)])
                assert "true" in (p["east"], p["west"], p["north"], p["south"]), "pane is a post"
                # the end screens run along X, so they connect east-west
                assert p["east"] == "true" and p["west"] == "true"
                seen += 1
    assert seen


def test_ruin_takes_glass_and_never_the_order():
    """What makes voxels read as architecture is regularity and openings, not damage. Every bay
    keeps its pier and its cornice however hard the ruin is turned up."""
    intact = _cells(_build(ruin=0.0, ruin_hard=0.0))
    wrecked = _cells(_build(ruin=1.0, ruin_hard=1.0))
    piers_i = {c for c, n in intact.items() if "deepslate" in n}
    piers_w = {c for c, n in wrecked.items() if "deepslate" in n}
    assert piers_i == piers_w, "the ruin ate part of the order"
    assert not [n for n in wrecked.values() if n == "glass_pane"], "hard ruin left glass"


def test_the_pool_is_a_closed_tank():
    """The bay's floor is a one-block skin over nothing, and the Y194 course runs on east past the
    plinth: water placed without a floor and four walls drains into the void and leaks out sideways."""
    cells = _cells(_build(pool_box=[-24232, 30025, -24224, 30027], pool_surface_y=194))
    water = [c for c, n in cells.items() if n == "water"]
    assert water, "no pool"
    ctx = FakeCourt()
    PASS = ("air", "cave_air", "void_air", "vine", "glow_lichen", "moss_carpet")
    for c in water:
        for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)):
            n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
            here = cells.get(n) or ctx.name_at(*n)
            assert here not in PASS, "pool leaks at %s toward %s (%s)" % (c, d, here)


def test_every_guard_lantern_is_waterlogged_and_has_footing():
    """Not waterlogged, the water above flows down into it; skipping the water there instead punches
    a hole through the surface of the pool at every guard. And the floor under it is open void."""
    c = _build(pool_box=[-24232, 30025, -24224, 30027], pool_surface_y=194)
    cells = _cells(c)
    ox, oy, oz = c.world_origin
    guards = [k for k, n in cells.items() if n == "lantern"]
    assert guards, "no freeze guard at all - this court has frozen before"
    for g in guards:
        p = nbt.state_props(c.palette[c.get(g[0] - ox, g[1] - oy, g[2] - oz)])
        assert p["waterlogged"] == "true", "guard lantern at %s is not waterlogged" % (g,)
        assert (g[0], g[1] - 1, g[2]) in cells, "guard lantern at %s stands on air" % (g,)
        assert cells.get((g[0], g[1] + 1, g[2])) == "water", "guard is not under the water"
