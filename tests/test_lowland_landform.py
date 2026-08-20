"""The lowland's landform: a massif, a basin, and a pond that has to survive `finish.hollow`.

The lowland was deliberately flat everywhere because it had to hold statues, which gave 6,800
columns of one height and no landscape. These pin the landform that replaced that, and in
particular the three ways the pond shipped broken before it shipped right.
"""
import pytest

from mcbuild.gen import lowland
from mcbuild.gen.lowland import LOWLAND, _surface, _water, _smoothstep
from mcbuild.gen.vertical import World

# a square of ground, so the geometry is the only thing under test
FOOT = {(x, z) for x in range(-24240, -24160) for z in range(29980, 30060)}
DIST = {c: 40 for c in FOOT}                      # far from any rim: no rim taper in the way
TY = 40


def _p(**over):
    return {**LOWLAND, "top_y": TY, "relief": 0, "rim_band": 0, "rim_drop": 0, "seed": 0, **over}


def test_smoothstep_is_clamped_and_monotonic():
    assert _smoothstep(-1) == 0.0 and _smoothstep(2) == 1.0
    vals = [_smoothstep(i / 10) for i in range(11)]
    assert vals == sorted(vals)


def test_the_massif_rises_toward_its_direction_and_leaves_the_low_end_flat():
    p = _p(massif={"dir": [1, 1], "rise": 15, "start": 0.45, "rough": 0})
    surf = _surface(FOOT, DIST, TY, p, 0)
    lo = [h for (x, z), h in surf.items() if x < -24230 and z < 29990]     # the low corner
    hi = [h for (x, z), h in surf.items() if x > -24170 and z > 30050]     # the high corner
    assert set(lo) == {TY}, "the flat end is not flat: %s" % sorted(set(lo))
    assert min(hi) > TY + 10, "the massif did not rise: max %d" % max(hi)
    assert max(surf.values()) <= TY + 15


def test_massif_roughness_only_touches_the_high_ground():
    """Roughening everywhere is what destroys the pads the statues need."""
    p = _p(massif={"dir": [1, 0], "rise": 15, "start": 0.5, "rough": 6})
    surf = _surface(FOOT, DIST, TY, p, 0)
    low = {h for (x, z), h in surf.items() if x < -24225}
    assert low == {TY}, "roughness leaked into the flat band: %s" % sorted(low)


def test_the_basin_digs_a_hole():
    p = _p(basin={"at": [-24200, 30020], "r": 20, "depth": 8, "water_y": 37})
    surf = _surface(FOOT, DIST, TY, p, 0)
    assert surf[(-24200, 30020)] == TY - 8, "basin centre is Y%d" % surf[(-24200, 30020)]
    assert surf[(-24240, 29980)] == TY, "the basin reached outside its radius"


def _pond(**basin):
    p = _p(basin={"at": [-24200, 30020], "r": 20, "depth": 8, "water_y": 37, **basin})
    surf = _surface(FOOT, DIST, TY, p, 0)
    w = World()
    n, lit, wet = _water(w, surf, p)
    return w, surf, n, lit, wet, p


def test_the_pond_is_bounded_by_the_hollow_shell():
    """`finish.hollow` keeps three courses measured from the model's EXTERIOR and the water counts
    as mass, so a bed four down from the surface is interior and gets carved - the pond then ships
    as a skin of water floating over nothing, with its guard lanterns hanging under it."""
    w, surf, n, lit, wet, p = _pond(max_depth=2)
    ys = {y for (x, y, z), (nm, _) in w.cells.items() if nm == "water"}
    assert ys, "no water"
    assert max(ys) - min(ys) + 1 <= 2, "pond is %d deep - deeper than the shell" % (max(ys) - min(ys) + 1)


def test_every_pond_column_has_a_real_bed_under_it():
    w, surf, n, lit, wet, p = _pond(max_depth=2)
    for (x, z) in wet:
        col = [y for (xx, y, zz), (nm, _) in w.cells.items()
               if (xx, zz) == (x, z) and nm == "water"]
        if not col:
            continue
        bed = w.name(x, min(col) - 1, z)
        assert bed is not None and bed != "water", "no bed under the pond at x%d z%d" % (x, z)


def test_the_flood_is_confined_to_the_basin():
    """The rim drops 3 and the relief rolls another 3, so 'every column under the water line' ponds
    every dip in the outer band as well - pools perched on the edge with nothing holding them in."""
    p = _p(basin={"at": [-24200, 30020], "r": 12, "depth": 8, "water_y": 37, "max_depth": 2})
    surf = _surface(FOOT, DIST, TY, p, 0)
    surf[(-24239, 29981)] = TY - 6                     # a stray low spot out at the rim
    w = World()
    n, lit, wet = _water(w, surf, p)
    assert (-24239, 29981) not in wet, "the flood escaped to a dip on the rim"


def test_the_bank_is_filled_across_the_water_band():
    """Ground beside a sunken pond looks solid at the surface and is hollow behind, so the pond
    drains sideways into the island's own cavity."""
    w, surf, n, lit, wet, p = _pond(max_depth=2)
    wy = 37
    for (x, z) in wet:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (x + dx, z + dz)
            if nb in wet:
                continue
            for y in range(wy - 2, wy + 1):
                assert w.has(nb[0], y, nb[1]), "bank open at x%d z%d Y%d" % (nb[0], nb[1], y)


def test_the_guard_is_submerged_and_stands_on_the_bed():
    """Set INTO the bed it is the only block in the column once hollow has been through, and audits
    as standing on air. One course up it is still under the surface and still light 15."""
    w, surf, n, lit, wet, p = _pond(max_depth=2)
    guards = [(x, y, z) for (x, y, z), (nm, _) in w.cells.items() if nm == "lantern"]
    assert guards, "no freeze guard - this project has iced two pools already"
    for (x, y, z) in guards:
        below = w.name(x, y - 1, z)
        assert below not in (None, "water"), "guard at x%d z%d stands on %s" % (x, z, below)
