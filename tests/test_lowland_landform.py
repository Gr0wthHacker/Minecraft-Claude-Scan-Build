"""The lowland's landform: a massif, a basin, and a pond that has to survive `finish.hollow`.

The lowland was deliberately flat everywhere because it had to hold statues, which gave 6,800
columns of one height and no landscape. These pin the landform that replaced that, and in
particular the three ways the pond shipped broken before it shipped right.
"""
import pytest

from mcbuild.gen import lowland
from mcbuild.gen.lowland import LOWLAND, _surface, _trees, _water, _smoothstep
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


def test_the_pond_ships_as_ice_because_a_printer_cannot_place_water():
    """A litematica printer places blocks out of your inventory and water is not a block, so a
    thousand-cell pond is a thousand bucket trips. Ice IS a block, and breaking one without silk
    touch leaves a water SOURCE - so the whole sheet converts by mining it."""
    w, surf, n, lit, wet, _ = _pond(max_depth=2, fill="ice")
    names = {nm for nm, _ in w.cells.values()}
    assert n > 0 and wet
    assert "ice" in names, "the pond did not ship as ice"
    assert "water" not in names, "still placing water: that is one bucket trip per cell"


def test_ice_carries_no_water_level_property():
    """`level` is a WATER property. Carried onto ice it names a state the block does not have, and
    `Work.matches` reports that as wrong - deliberately, because it is a design bug."""
    w, _, _, _, _, _ = _pond(max_depth=2, fill="ice")
    for (x, y, z), (nm, props) in w.cells.items():
        assert nm != "ice" or props == {}, "ice at %d %d %d carried %r" % (x, y, z, props)


def test_the_pond_still_ships_as_water_when_nothing_asks_for_ice():
    """`fill` defaults to water, so no other lowland moved."""
    w, _, _, _, _, _ = _pond(max_depth=2)
    names = {nm for nm, _ in w.cells.values()}
    assert "water" in names and "ice" not in names


def test_the_sidecar_records_a_count_and_not_a_coordinate():
    """`_water` returns the number of fill cells. The bank loop used to reuse `n` for a neighbour
    coordinate, so the sidecar shipped `"water": [-24198, 30004]` where it meant 1,111. A count
    that is silently a coordinate reads as data rather than as a bug, which is why it survived."""
    w, _, n, lit, wet, _ = _pond(max_depth=2, fill="ice")
    assert isinstance(n, int), "water count came back as %r" % (n,)
    assert n == sum(1 for nm, _ in w.cells.values() if nm == "ice")
    assert isinstance(lit, int) and lit > 0


def test_trees_do_not_grow_out_of_the_pond():
    """A tree is sited on the SURFACE height, and inside the basin that height is under the water
    line - so two oaks were rooted on the pond bed with their trunks standing up through the fill.
    `_lanterns` already took the flooded columns for this reason; `_trees` did not."""
    p = _p(basin={"at": [-24200, 30020], "r": 20, "depth": 8, "water_y": 37,
                  "max_depth": 2, "fill": "ice"}, trees=6)
    surf = _surface(FOOT, DIST, TY, p, 0)
    w = World()
    n, _, wet = _water(w, surf, p)
    before = {c: nm for c, (nm, _) in w.cells.items()}
    _trees(w, surf, DIST, p, 0, skip=wet)
    eaten = [c for c, (nm, _) in w.cells.items() if before.get(c) == "ice" and nm != "ice"]
    assert not eaten, "a tree stands in the pond at %s" % (eaten[:3],)
    assert n == sum(1 for nm, _ in w.cells.values() if nm == "ice")
