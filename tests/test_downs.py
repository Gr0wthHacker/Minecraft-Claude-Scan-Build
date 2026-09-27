"""The downs' contracts - and the first of them is the one Jack stated as a requirement.

    "it cant be impassable terrain, it should still feel like a park, gradual hills, small areas"

So the walkability is not a hope, it is a property the finished ground is measured against: no
step anywhere may exceed one course, because a player climbs 1.25 and a two-course step is a wall.
Everything else here pins a decision that was got wrong once while this was built.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import blocks, palette, scan  # noqa: E402
from mcbuild.gen import downs  # noqa: E402

CONFIG = "configs/pf_prism_downs.yaml"
SHIPPED = "out/PF Prism Downs.litematic"


def cfg() -> dict:
    return yaml.safe_load(open(CONFIG, encoding="utf-8"))["params"]


def shipped():
    if not os.path.exists(SHIPPED):
        pytest.skip(f"{SHIPPED} not generated")
    return scan.load(SHIPPED)


# --------------------------------------------------------------------- the palette


def test_every_block_it_places_is_real_spendable_and_cheap_or_ok():
    for key, name in downs.GROUND.items():
        assert blocks.exists(name), f"{key}: {name} is not a block"
        assert blocks.spendable(name), f"{key}: {name} is CURRENCY on this server"
        assert palette.tier(name) in ("cheap", "ok"), f"{key}: {name} is {palette.tier(name)}"


def test_the_rock_is_a_real_value_ladder_measured_ACROSS_families():
    """Four indistinguishable greys are one grey whatever the mix - the mistake three separate
    notes in CLAUDE.md record about stone brick, blackstone and the mine ridge's first draft."""
    def lum(name):
        r, g, b = blocks.color(name, "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    rungs = [downs.GROUND[k] for k in ("deep", "rock", "turf", "rock_b")]
    vals = [lum(n) for n in rungs]
    assert vals == sorted(vals), list(zip(rungs, vals))
    assert min(b - a for a, b in zip(vals, vals[1:])) >= 4, list(zip(rungs, vals))
    assert lum(downs.GROUND["rock_b"]) - lum(downs.GROUND["deep"]) >= 60


def test_nothing_that_falls_is_ever_placed():
    """Rule 13. `gravel` is in the table as a crust material and this generator does not use it;
    a falling block anywhere in a mass with air under it is a hole waiting to happen."""
    used = {v for k, v in downs.GROUND.items() if k != "scree"}
    assert not any(blocks.falls(n) for n in used), [n for n in used if blocks.falls(n)]


# --------------------------------------------------------------------- the ground


class _Flat:
    """A synthetic site: open ground with a street down one edge, so the field can be tested
    without a capture."""

    def __init__(self, dv=60, du=60):
        self.dv, self.du = dv, du
        self.seat = np.zeros((dv, du), np.int16)
        self.street = np.zeros((dv, du), bool)
        self.build = np.zeros((dv, du), bool)
        self.street[0, :] = self.street[-1, :] = True
        self.street[:, 0] = self.street[:, -1] = True

    def buildable(self):
        return self.seat >= 0


def _field(**over):
    p = {**downs.DOWNS, "mouth": [30, 30, 6], "peak": 16.0, "reach": 40.0, "seed": 5, **over}
    site = _Flat()
    h = downs.height(p, site)
    return downs.relax(h, site.buildable()), site


def test_no_step_anywhere_is_more_than_one_course():
    """**THE ONE REQUIREMENT JACK STATED.** A player climbs 1.25; a two-course step is a wall, and
    a hill made of walls is not a park, it is an obstacle."""
    h, _ = _field()
    assert downs._walkable(h) == 0


@pytest.mark.parametrize("peak,slope", [(10.0, 0.5), (18.0, 0.8), (26.0, 1.0)])
def test_it_stays_walkable_at_every_setting(peak, slope):
    """A tuning knob that can produce a cliff is a tuning knob that eventually will."""
    h, _ = _field(peak=peak, slope=slope)
    assert downs._walkable(h) == 0


def test_relax_only_ever_LOWERS_the_ground():
    """Raising the low side would push ground into a street or over a build. The clamp that keeps
    this walkable is expressed as a CEILING, so the pass has to converge downward."""
    site = _Flat()
    p = {**downs.DOWNS, "mouth": [30, 30, 6], "peak": 22.0, "reach": 40.0, "seed": 5}
    h = downs.height(p, site)
    out = downs.relax(h, site.buildable())
    assert (out <= np.rint(h).astype(int) + 0).all()


def test_the_ground_meets_every_street_at_grade():
    """A street with a hill starting at its own kerb is a wall along a guest walk. `margin` gives
    it a dead-level apron first and the slope clamp does the rest."""
    h, site = _field(margin=2)
    assert h[site.street].max() == 0
    # ...and the cells beside a street are low
    edge = np.zeros_like(site.street)
    edge[1, :] = edge[-2, :] = True
    edge[:, 1] = edge[:, -2] = True
    assert h[edge].max() <= 1


def test_the_ground_rises_toward_the_shaft():
    """The whole point: the shaft is a hole in a HILL. If the field does not climb toward the
    mouth then the drop is off a floor, which is what this replaced."""
    h, _ = _field()
    near = h[24:37, 24:37]
    far = h[1:8, 1:8]
    assert near.mean() > far.mean() + 3, (near.mean(), far.mean())


def test_a_build_is_met_with_a_scarp_and_a_street_is_not():
    """**TWO KINDS OF BOUNDARY, AND CONFLATING THEM COSTS THE WHOLE IDEA.** With one mask the
    terrain fell to nothing at the mouth - the exact opposite of what it is for."""
    site = _Flat(60, 60)
    site.build[28:33, 28:33] = True
    p = {**downs.DOWNS, "mouth": [30, 30, 4], "peak": 18.0, "reach": 45.0,
         "slope": 0.5, "build_slope": 1.0, "seed": 5}
    h = downs.relax(downs.height(p, site), site.buildable())
    # eight cells out from the build the ground is already high; eight cells from a STREET it is
    # not, because a street is met at grade
    assert h[41, 30] >= 6, h[41, 30]      # nine cells clear of the build: already a scarp
    assert h[8, 30] <= 5, h[8, 30]        # eight cells from a street: still at grade


def test_a_dell_is_a_hollow_and_not_a_hill():
    h_no, _ = _field(dells=())
    h_yes, _ = _field(dells=[[30, 42, 10, 7]])
    assert h_yes[30, 42] < h_no[30, 42]


# --------------------------------------------------------------------- the shipped design


def test_the_shipped_ground_is_walkable():
    """Measured on the ARTIFACT, not on the field: the fill, the slab softening and the dressing
    all happen after `relax` and any of them could put a block back."""
    s = shipped()
    ids = s.model.ids
    names = np.array([n.split(":")[-1] for n in s.model.names])
    solid = ~np.isin(names[ids], ["air", "cave_air", "void_air"])
    #: A SLAB IS HALF A STEP AND MUST NOT COUNT AS A WHOLE ONE. The riser softening caps a step
    #: with a slab, which is exactly what makes the ground gentler - counting it as a full course
    #: would report the smoothing as the fault.
    top = np.where(solid.any(0), solid.shape[0] - np.argmax(solid[::-1], 0), 0)
    plant = np.isin(names[ids], ["azalea", "flowering_azalea", "fern", "large_fern",
                                 "moss_carpet", "azalea_leaves", "flowering_azalea_leaves",
                                 "oak_log", "glow_lichen"])
    ground = solid & ~plant
    gtop = np.where(ground.any(0), ground.shape[0] - np.argmax(ground[::-1], 0), 0)
    del top
    bad = 0
    for a, b in ((gtop[1:, :], gtop[:-1, :]), (gtop[:, 1:], gtop[:, :-1])):
        both = (a > 0) & (b > 0)
        bad += int(((np.abs(a.astype(int) - b.astype(int)) > 1) & both).sum())
    # a tree trunk is not the ground; allow a small tail for the crowns the mask cannot separate
    assert bad == 0, bad


def test_the_turf_is_the_parks_own_lawn_and_it_dominates():
    """**A HILL THAT IS ROCK ALL OVER IS A QUARRY.** At a clean gradient threshold this came out
    60% bare grey and read as a slag heap; the Lost Plateau is 71% green on top and that is what
    makes it land."""
    s = shipped()
    names = list(s.model.names)
    ids = s.model.ids
    n = {nm.split(":")[-1]: int((ids == i).sum()) for i, nm in enumerate(names)}
    assert n.get("moss_block", 0) > 0
    caps = n.get("moss_block", 0) + n.get("cobbled_deepslate_slab", 0) + \
        n.get("blackstone_slab", 0)
    assert n["moss_block"] / max(1, caps) > 0.45, n


def test_it_is_cheap_tier_terrain():
    """Ninety thousand blocks of `ok` would be a land nobody can afford to print. The interior is
    the cheap basalt and only the top three courses are bedded."""
    s = shipped()
    names = list(s.model.names)
    ids = s.model.ids
    tiers = {"cheap": 0, "ok": 0, "expensive": 0}
    for i, nm in enumerate(names):
        short = nm.split(":")[-1]
        if short == "air":
            continue
        tiers[palette.tier(short)] = tiers.get(palette.tier(short), 0) + int((ids == i).sum())
    assert tiers["expensive"] == 0, tiers
    assert tiers["cheap"] > tiers["ok"] * 2, tiers


def test_it_covers_the_whole_land_and_not_one_lot():
    """Jack: "really terrain the entire area, from the building you removed all the way to the
    railway edge, and all the way to our parkour area"."""
    p = cfg()
    dv, du = p["lot"]
    v, u = p["at"]
    assert v <= 20 and v + dv >= 165, (v, dv)          # spine verge to the rim reserve
    assert u <= 390 and u + du >= 595, (u, du)          # the reach to the park's east edge


# --------------------------------------------------------------------- the way in


def test_the_shaft_can_be_REACHED_ON_FOOT_from_the_park():
    """**THE ONE FUNCTIONAL REQUIREMENT, AND THE FIRST TERRAIN FAILED IT SILENTLY.** Jack: "we
    still need a way for players to actually GET to this so they can either descend, or go up via
    bubble elevator; and i think with the ripple its now very difficult."

    He was right and it was worse than difficult. `relax` caps every step between two TERRAIN
    cells at one course, and the boundary onto a BUILD is not a terrain-to-terrain step - so
    nothing constrained it at all. Measured on the shipped park, the downs stood 7 to 10 courses
    over the well's rim gallery around its whole circumference, and only 3 of 72 sampled bearings
    were at grade. `ramps` cuts four radial valleys down to the collar.

    **AND THIS IS A FLOOD, NOT A RAY.** Sampling a radius counted the well's own masts and end
    rods as ground and reported a 23-course step on a ramp that is in fact walkable end to end -
    twice. The only honest test of "can a player get there" is to walk it.
    """
    park = "out/Park Complete.litematic"
    if not os.path.exists(park):
        pytest.skip("Park Complete not shipped")
    from collections import deque

    s = scan.load(park)
    ox, oy, oz = s.origin
    ids = s.model.ids
    names = np.array([n.split(":")[-1] for n in s.model.names])
    #: a post, a rod, a bar, a rail or a plant is something you walk PAST, never something you
    #: stand on and never something that blocks a step.
    soft = {"air", "cave_air", "void_air", "azalea", "flowering_azalea", "fern", "large_fern",
            "moss_carpet", "glow_lichen", "vine", "short_grass", "tall_grass", "grass",
            "dead_bush", "torch", "lantern", "end_rod", "iron_bars", "rail", "powered_rail",
            "oak_leaves", "azalea_leaves", "flowering_azalea_leaves", "spruce_leaves",
            "jungle_leaves", "amethyst_cluster", "water"}
    solid = ~np.isin(names[ids], list(soft))
    # scoped to Prismworks and its reach, or the flood is the whole park and the test is a minute
    u0, u1 = 80650 - oz, 80899 - oz
    v0, v1 = 97500 - ox, 97699 - ox
    cols = {}
    for u in range(u0, u1 + 1):
        for v in range(v0, v1 + 1):
            col = solid[:, u, v]
            ys = [y for y in range(1, ids.shape[0] - 2)
                  if col[y - 1] and not col[y] and not col[y + 1]]
            if ys:
                cols[(u, v)] = ys

    def step_to(u, v, y):
        for yy in cols.get((u, v), ()):
            if abs(yy - y) <= 1:
                return yy
        return None

    seed = None
    for r in range(50, 62):                       # inward from the collar, on the spine side
        u, v = 80815 - oz, 97590 - ox - r
        for y in cols.get((u, v), ()):
            if abs(y + oy - 203) <= 2:
                seed = (u, v, y)
                break
        if seed:
            break
    assert seed, "no standable cell found on the well's rim"

    seen, q = {seed}, deque([seed])
    while q:
        u, v, y = q.popleft()
        for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = u + du, v + dv
            if not (u0 <= a <= u1 and v0 <= b <= v1):
                continue
            yy = step_to(a, b, y)
            if yy is not None and (a, b, yy) not in seen:
                seen.add((a, b, yy))
                q.append((a, b, yy))

    inside = {(u, v) for u, v, _y in seen if 80688 - oz <= u <= 80899 - oz}
    spine = [c for c in seen if 6 <= c[1] + ox - 97500 <= 18]
    assert len(inside) > 8000, f"only {len(inside)} columns of the land reachable from the rim"
    assert spine, "the rim does not connect to the park's main spine on foot"
