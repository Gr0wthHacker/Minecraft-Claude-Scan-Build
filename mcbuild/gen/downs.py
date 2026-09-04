"""THE PRISM DOWNS - the whole land as gentle ground falling into the shaft.

Jack, after two rejected attempts at putting OBJECTS on this land: *"i think youre doing this idea
all wrong ... get rid of the building, turn it into something else, remove the plaza or make it
blend more naturally, and make this environment significantly better"*, then *"build sophisticated
impressive terrain that fits the area appropriately"*, and the two constraints that decide its
shape:

    "it cant be impassable terrain, it should still feel like a park, gradual hills, small
     areas, etc"

    "really terrain the entire area, from the building you removed all the way to the railway
     edge, and all the way to our parkour area so it feels even that more dramatic of a fall"

**WHY OBJECTS FAILED AND GROUND DOES NOT.** Everything in this park that reads is CONTINUOUS
GROUND - `PF Mine Ridge` is a mountain, `PF Lost Plateau` is that mountain re-clothed, `PF
Frontier Diggings` is worked earth. Everything that has failed is objects standing on a flat lawn:
Boomtown's seven false fronts, Prismworks v1's fourteen buildings, and `gen/seam.py`'s forty
crystal spires. The Frontier's 18% / 24% mid-height bands - the number those spires were chasing -
come from a MOUNTAIN, not from props. A height histogram moves either way and only one of them
looks like anything.

Measured before this was written, over `out/Park Complete.litematic` with the gate and the plate
withdrawn: the land and its reach are **36,550 columns, 95% of them standing 0-2 courses tall**.

## The form

**One shallow dome with a hole through the middle of it.** The ground swells from nothing at the
plot's edges to its crest just outside the well's collar, so the shaft is a hole in a HILL rather
than a hole in a plate - which is the whole of "a more dramatic fall", because you crest a rise
and the drop appears rather than walking up to it across a floor.

**AND IT IS WALKABLE BY CONSTRUCTION, NOT BY INSPECTION.** `h <= distance-to-level * slope` with
slope under one guarantees that every cell is reachable on foot from any street, verge or terrace
that bounds it: a player climbs 1.25, and nothing here rises a full course per cell. That single
clamp is what makes this a park and not a crag, and it is checked rather than hoped for -
`tests/test_downs.py` walks the finished ground.

**THE HILLS ARE GRADUAL AND THE HOLLOWS ARE THE POINT.** A smooth dome is a bowl; what makes
downland is the coarse roll over it - long shoulders and shallow dells - and a handful of cut
DELLS, small level pockets with a rock lip, which are the "small areas" a guest is IN rather than
ON.

## What it is made of

The land's own rock, bedded rather than speckled, with turf over it:

    blackstone            38     the beds under everything
    smooth_basalt         73     the bulk
    cobbled_deepslate     77     texture
    moss_block           101     the turf, and the same green as the park's own lawn
    tuff                 108     the pale bed, and the only real highlight in the mass

Steps of 35, 4, 24 and 7 - measured ACROSS families with `blocks.color(..., "side")`, which is the
only place contrast exists on this economy, and the mistake three separate notes in CLAUDE.md
record about stone brick, blackstone and the mine ridge's own first draft.

**THE TURF IS THE PARK'S OWN LAWN MATERIAL.** That is what keeps this reading as a park rather
than as a quarry: the hills are the same green as the flat ground they grow out of, and rock only
shows where the ground is too steep to hold soil. Azalea, fern and dripleaf over it - the lush
palette, which is Prismworks' own and not the Frontier's jungle.
"""
from __future__ import annotations

import math

import numpy as np

from .canvas import Canvas, hash01
from .frontier_builds import _Lot
from .mineridge import _away, _noise, _terrace
from .frontier_scatter import shipped_cells
from .seam import surface_cells
from .vertical import Ctx

#: Checked by `tests/test_downs.py` against `blocks.available` (1.19), `blocks.spendable` (dirt and
#: grass are CURRENCY here) and `palette.tier`.
GROUND = {
    "deep": "blackstone",              # L38 - the beds under everything
    "deep_b": "cobbled_deepslate",     # L77
    "rock": "smooth_basalt",           # L73 - the bulk, and cheap
    "rock_b": "tuff",                  # L108 - the pale bed
    "rock_c": "deepslate",             # L71
    "seam": "cyan_wool",               # L114 - the vein, IN the rock and never standing on it
    "seam_b": "light_blue_wool",       # L153
    "crystal": "amethyst_cluster",
    "turf": "moss_block",              # L101 - the park's own lawn
    "carpet": "moss_carpet",
    "scree": "gravel",                 # CRUST ONLY - it falls
    "glow": "pearlescent_froglight",   # flush in the turf: Jack's own idiom
    "lichen": "glow_lichen",
    "bush": "azalea",
    "bloom": "flowering_azalea",
    "leaf": "flowering_azalea_leaves",
    "wood": "oak_log",
    "fern": "fern",
    "tall_fern": "large_fern",
    "leaf_b": "azalea_leaves",
    "step": "cobbled_deepslate_stairs",
    "slab": "cobbled_deepslate_slab",
    "slab_b": "blackstone_slab",
    #: THE EJECTA - what the shaft threw out. Dark slate and basalt lying on the turf, thickest at
    #: the rim and thinning outward, which is the same story the ripples tell.
    "debris": "cobbled_deepslate",
    "debris_b": "blackstone",
    "debris_c": "deepslate",
    "debris_d": "tuff",
    "path": "deepslate_tiles",          # the land's own avenue stone
    "path_edge": "polished_deepslate",
    "chip": "cobbled_deepslate_slab",
    "chip_b": "blackstone_slab",
    "chip_c": "deepslate_tile_slab",
}

#: **BEDDED, NOT SPECKLED, AND THE BEDS REPEAT.** Rock has bedding planes; a horizontal band is
#: the one thing that reads at the distance a guest stands, and four indistinguishable greys
#: speckled together read as noise close up and as nothing at all far off. One ladder spread over
#: the whole height would put every accent in the bottom third, so the cycle is short and MID sits
#: between every accent - the mine ridge's own rule, which it learned by shipping the other one.
_DARK = (("deep", 0.55), ("deep_b", 0.25), ("rock_c", 0.20))
_MID = (("rock", 0.58), ("deep_b", 0.20), ("rock_c", 0.12), ("rock_b", 0.10))
_PALE = (("rock_b", 0.46), ("rock", 0.40), ("deep_b", 0.14))
_VEIN = (("seam", 0.34), ("seam_b", 0.20), ("rock", 0.30), ("deep_b", 0.16))
_STRATA = (_MID, _DARK, _MID, _PALE, _MID, _VEIN, _MID, _DARK)
_BAND = 4

DOWNS = {
    "kind": "downs",
    "lot": None,                  # [dv, du]
    "at": None,                   # [V, U]
    "anchor": [97500, 203, 80300],
    "sy": 34,
    "under": None,                # the world this is verified against - ASK THE SAME ONE
    "previous": None,
    "off_limits": (),             # artifacts whose WALKING SURFACE stays level - see `surface_cells`

    #: THE SHAFT, in LOCAL coordinates: [v, u, hold]. The swell rises toward it and holds its
    #: crest from `hold` cells out, so the ground arrives at the mouth high.
    "mouth": None,
    "peak": 13.0,                 # the crest, just outside the collar
    "reach": 150.0,               # ...and how far out the swell is felt at all
    "shape": 0.85,                # <1 fills out toward the edges, >1 hugs the mouth

    #: **THE ONE NUMBER THAT MAKES THIS A PARK.** Height is clamped to `slope` courses per cell of
    #: distance from anything that must stay level, so nothing anywhere rises faster than a player
    #: climbs. Under 1.0 by a margin, because rounding to whole courses adds back up to half of
    #: one.
    "slope": 0.62,
    #: ...and the steeper one, used only against builds and the shaft's own void. A street is met
    #: at grade; the well's collar is met with a scarp, and that scarp is the drama.
    "build_slope": 1.0,
    "margin": 1,                  # cells of dead-level apron around a street before the rise
    #: how far from the edge of its own paving a cell must be to count as a MAIN avenue and
    #: stay perfect. Everything narrower is ground the ripples run over - see `_Site`.
    "main_at": 3.0,
    #: LOCAL [[v0, v1, u0, u1], ...] - routes that stay perfect whatever their width. A
    #: three-wide avenue and a three-wide spur measure the same; only a name separates them.
    "keep": (),
    #: THE SHOCK WAVE off the shaft - see `height`. amp 0 turns it off entirely.
    "ripple": {"amp": 0.0, "wave": 15.0, "decay": 55.0, "stretch": 0.82,
               "wobble": 5.0, "grain": 21},
    #: THE EJECTA RAYS - the half of the impact that reads from the ground. count 0 turns it off.
    "rays": {"count": 0, "sharp": 3.2, "amp": 2.5, "reach": 90.0, "wander": 1.6, "grain": 30},
    "ray_at": 0.30,
    "roll": {"grain": 26, "amp": 5.0},      # the gradual hills
    "fine": {"grain": 9, "amp": 1.4},       # ...and the texture on them
    "bench": 3,                   # terrace step, used only where the ground is genuinely steep

    #: the ejecta scattered over the turf - see `_dress`. density 0 turns it off.
    "debris": {"density": 0.0, "decay": 60.0},
    #: **THE WAYS IN.** [{bearing, width, slope, shoulder}, ...] - radial valleys down to the
    #: shaft. Without them the terrain stands 7-10 courses over the rim gallery all the way
    #: round, because `relax` only ever constrained terrain-to-terrain steps.
    "ramps": (),
    "dells": (),                  # [[v, u, r, depth], ...] - small level pockets with a rock lip
    "turf_slope": 0.75,           # steeper than this and the rock shows through
    "rock_ring": 8,               # ...and it always shows within this of the shaft
    "plant": {"density": 0.16, "tree": 0.014, "fern": 0.10},
    #: small groupings of rock on the turf - see `_boulder`. density 0 turns it off.
    "rocks": {"density": 0.10, "grain": 13},
    "light": 13,                  # a flush froglight about every this many cells of turf
    "seed": 0,
}


# --------------------------------------------------------------------------- the site


class _Site:
    """The world, read once into arrays - and the only thing that decides where ground may go.

    **A PER-COLUMN PROBE THIRTY THOUSAND TIMES IS THE COST HERE**, so it is done once into three
    masks and everything downstream is numpy. `gen/seam.py` asked the world per candidate and
    spent a minute on six thousand columns.
    """

    SOFT = ("air", "cave_air", "void_air", "moss_carpet")
    WET = ("water", "flowing_water", "lava", "bubble_column", "ice")

    def __init__(self, ctx: Ctx, anchor, dv, du, at, surface, mine=None, band: int = 2,
                 head: int = 5, main_at: float = 3.0, keep=()):
        self.ax, self.ay, self.az = anchor
        self.at_v, self.at_u = at
        self.dv, self.du = dv, du
        self.seat = np.full((dv, du), -1, np.int16)
        #: **TWO KINDS OF BOUNDARY, AND CONFLATING THEM COSTS THE WHOLE IDEA.** A STREET has to be
        #: met at grade - the ground eases down to it over many cells, because that is what makes
        #: this a park. A BUILD, and the shaft's own void, does not: the ground may stand tall
        #: against the well's collar and step down to it, and that scarp is the entire "more
        #: dramatic fall". With one mask the terrain fell to nothing at the mouth, which is the
        #: exact opposite of what it is for.
        self.street = np.zeros((dv, du), bool)
        #: **A PAVED CELL IS NOT AUTOMATICALLY A PROTECTED ONE.** Jack: "we have small side paths
        #: that cut through the landscape, these should be broken and impacted by ripples with
        #: only the main larger avenue intact perfectly." So the paving is split by WIDTH, which
        #: is the one honest measure of which street is which - a thirteen-wide spine has cells
        #: six from its own edge and a three-wide service lane has cells one from it. The wide
        #: ones stay level and the narrow ones are ground the terrain may run over.
        self.paved = np.zeros((dv, du), bool)
        self.broken = np.zeros((dv, du), bool)
        self.floor = np.empty((dv, du), object)
        self.build = np.zeros((dv, du), bool)
        self.wet = np.zeros((dv, du), bool)
        #: **RULE 15, AND WITHOUT IT THIS DESIGN CANNOT BE REGENERATED AT ALL.** Once the downs
        #: are in the shipped park, every column of the land holds ground - so a probe that reads
        #: the world honestly reports the whole lot as built-on and the next run emits FIFTY-EIGHT
        #: BLOCKS. A terrain design is the extreme case of the self-reference this repo already
        #: records for the Mine Ridge; the answer is the same one, and it is exact rather than a
        #: material guess: this design's own last artifact, in world coordinates.
        mine = frozenset(mine or ())
        for v in range(dv):
            for u in range(du):
                x, z = self.ax + at[0] + v, self.az + at[1] + u
                s = None
                for y in range(band, -1, -1):
                    fl = ("air" if (x, self.ay + y - 1, z) in mine
                          else ctx.name_at(x, self.ay + y - 1, z).split(":")[-1])
                    if fl in self.SOFT:
                        continue
                    if fl in self.WET:
                        self.wet[v, u] = True
                        break
                    if (x, self.ay + y - 1, z) in surface:
                        self.paved[v, u] = True
                        self.floor[v, u] = fl
                        # ...and whether it stays level is decided AFTER, by how wide it is
                        if all((x, self.ay + y + k, z) in mine
                               or ctx.name_at(x, self.ay + y + k, z).split(":")[-1] in self.SOFT
                               for k in range(head)):
                            self.seat[v, u] = y
                        break
                    if all((x, self.ay + y + k, z) in mine
                           or ctx.name_at(x, self.ay + y + k, z).split(":")[-1] in self.SOFT
                           for k in range(head)):
                        s = y
                    break
                if self.paved[v, u]:
                    continue                       # decided below, by how wide its street is
                if s is None:
                    self.build[v, u] = True        # something stands here, or there is no floor
                else:
                    self.seat[v, u] = s
        # the lot's own edge is a street: the ground must reach the boundary at grade or it ends
        # in a wall against the neighbour's lawn
        # **WIDE STAYS, NARROW BREAKS.** `main_at` is the number of cells a paved cell must be
        # from the edge of its own paving to count as a main avenue: 3 keeps the spine and the
        # seven-wide avenues perfect and lets the ground run over the promenade, the service lane
        # and every spur.
        edge = _away(~self.paved, 8)
        main = self.paved & (edge >= float(main_at))
        #: **WIDTH ALONE BURIES THE LAND'S OWN CIRCULATION.** Prismworks' two avenues are three
        #: cells wide - the same as a spur - so a width rule cannot tell them apart, and the first
        #: pass ran the terrain over both. Measured afterwards, only ONE of four ramps landed on a
        #: surviving route. A route that must stay is NAMED, and named routes are kept only where
        #: they are actually paved, so a box cannot flatten lawn it happens to cover.
        for box in (keep or ()):
            a, b, c, d = (int(x) for x in box)
            main[max(0, a):b + 1, max(0, c):d + 1] |= self.paved[max(0, a):b + 1,
                                                                 max(0, c):d + 1]
        self.street |= main
        self.broken = self.paved & ~main
        #: A MAIN AVENUE IS NOT GROUND. It stays perfect, so nothing may be built on it and the
        #: terrain is clamped to meet it at grade like any other street.
        self.seat[main] = -1
        self.street[0, :] = self.street[-1, :] = True
        self.street[:, 0] = self.street[:, -1] = True
        self.build &= ~self.street

    def buildable(self):
        return self.seat >= 0


# --------------------------------------------------------------------------- the height field


def height(p: dict, site: _Site) -> np.ndarray:
    """The downs, as a field. Everything about the shape of this land is these twenty lines.

    THE SWELL RISES TOWARD THE SHAFT and holds its crest against the collar, so the ground arrives
    at the mouth high and the drop is off a hill rather than off a floor.

    THE CLAMP IS WHAT MAKES IT A PARK. `h <= distance-to-level * slope` guarantees every cell is
    walkable from the street that bounds it, whatever the swell and the roll wanted - and it is
    also what carves the land into hills between the streets rather than one dome over them.
    """
    dv, du = site.dv, site.du
    mv, mu, hold = (float(x) for x in p["mouth"])
    seed = int(p.get("seed", 0))

    vv = np.arange(dv)[:, None].astype(float)
    uu = np.arange(du)[None, :].astype(float)
    d = np.sqrt((vv - mv) ** 2 + (uu - mu) ** 2)

    reach = float(p.get("reach", 150.0))
    t = np.clip((reach - d) / max(1.0, reach - hold), 0.0, 1.0)
    swell = float(p.get("peak", 13.0)) * t ** float(p.get("shape", 0.85))

    r = p.get("roll") or {}
    f = p.get("fine") or {}
    roll = (_noise(dv, du, seed + 11, grain=int(r.get("grain", 26))) - 0.5) * 2 * float(r.get("amp", 5.0))
    fine = (_noise(dv, du, seed + 29, grain=int(f.get("grain", 9))) - 0.5) * 2 * float(f.get("amp", 1.4))
    # **THE RIPPLES: the ground still moving away from whatever went through it.** Jack: "can we
    # make it feel more like ground ripples as if the parkour thing was smashing through the gap,
    # almost giving the feel of motion."
    #
    # Three things separate a shock wave from a dartboard, and all three are the difference:
    #
    #   * THE AMPLITUDE DECAYS OUTWARD. A wave that keeps its height for ever is a corrugated
    #     roof; one that dies away says the energy came from the middle and is spending itself.
    #   * THE WAVELENGTH STRETCHES. Real ripples lengthen as they travel, and a constant spacing
    #     is the single thing that makes concentric rings read as a target.
    #   * THE RADIUS WANDERS. Perfect circles are a graphic, not ground - so the radius carries
    #     the coarse noise, which is this repo's own rule about putting the randomness on a
    #     drift's RADIUS rather than on its cells.
    rp = p.get("ripple") or {}
    amp = float(rp.get("amp", 0.0))
    if amp > 0.0:
        wave = max(4.0, float(rp.get("wave", 15.0)))
        decay = max(4.0, float(rp.get("decay", 55.0)))
        stretch = float(rp.get("stretch", 0.82))
        wob = float(rp.get("wobble", 5.0))
        dr = d + (_noise(dv, du, seed + 53, grain=int(rp.get("grain", 21))) - 0.5) * 2 * wob
        out = np.maximum(0.0, dr - hold)
        phase = 2.0 * np.pi * (out / wave) ** stretch
        wavef = np.cos(phase) * np.exp(-out / decay)
        # **THE RINGS HAVE TO BE VISIBLE IN THE MATERIAL, NOT ONLY IN THE HEIGHT.** At four
        # courses against a five-course random roll the wave was invisible at eye level and the
        # land read as generic hills - which is exactly what Jack said. Published here so the
        # fill can put rock on the crests and turf in the troughs: concentric bands of dark and
        # green read from anywhere, and a four-course undulation does not.
        site.wave = wavef
        swell = swell + amp * wavef

    # **AND THE RAYS, WHICH ARE THE HALF THAT READS FROM THE GROUND.** Concentric rings only work
    # in PLAN: standing on one you cannot see it curve, so it is just a ridge - which is exactly
    # why the first rippled version still read as "hilly terrain" at eye level. A guest is never
    # in plan view. What reads from the ground is RADIAL, because you look ALONG it: streaks of
    # dark slate thrown out of the shaft, thinning as they go, with green between them. Every one
    # of them points at the tower from wherever you stand on it.
    ry = p.get("rays") or {}
    rn = int(ry.get("count", 0) or 0)
    if rn > 0:
        th = np.arctan2(vv - mv, uu - mu)
        wob = (_noise(dv, du, seed + 97, grain=int(ry.get("grain", 30))) - 0.5) * 2.0
        lobe = 0.5 + 0.5 * np.cos(rn * th + float(ry.get("wander", 1.6)) * wob)
        lobe = lobe ** float(ry.get("sharp", 3.2))
        # EVERY RAY A DIFFERENT LENGTH, or it is a pinwheel rather than ejecta. The reach is
        # keyed on the ray's own index, so one throws twice as far as its neighbour.
        idx = np.floor((rn * th) / (2.0 * np.pi) * rn) % max(rn, 1)
        far = np.vectorize(lambda i: 0.45 + 0.9 * hash01(int(i), 7, 0, seed))(idx)
        run = np.maximum(0.0, d - hold) / (float(ry.get("reach", 90.0)) * far)
        site.ray = lobe * np.clip(1.0 - run, 0.0, 1.0) ** 1.3
        swell = swell + float(ry.get("amp", 2.5)) * site.ray

    h = np.maximum(0.0, swell + roll + fine)

    # ...and the clamp. `margin` cells of dead-level apron first, so a street has a verge to it
    # rather than the ground starting to climb from its own kerb.
    cap = int(min(120, max(24, reach)))
    dist = np.maximum(0.0, _away(site.street, cap) - float(p.get("margin", 1)))
    h = np.minimum(h, dist * float(p.get("slope", 0.62)))
    # ...and a SEPARATE, steeper clamp against builds and against the shaft's own void. This is
    # the scarp at the mouth: the ground stands high and steps down to the collar, which is the
    # "more dramatic fall". At one course per cell it is still climbable - `relax` guarantees no
    # step anywhere exceeds one - so the rim can be got on and off at any bearing.
    hard = _away(site.build, 40)
    site.hard = hard
    h = np.minimum(h, hard * float(p.get("build_slope", 1.0)))

    # **THE RAMPS, AND WITHOUT THEM THIS LAND CANNOT BE ENTERED.** Jack: "we still need a way for
    # players to actually GET to this so they can either descend, or go up via bubble elevator;
    # and i think with the ripple its now very difficult."
    #
    # He is right and it was worse than difficult - it was a wall. `relax` caps every step between
    # two TERRAIN cells at one course, and the boundary onto a build is not a terrain-to-terrain
    # step, so nothing constrained it at all: measured on the shipped park, the downs stood 7 to
    # 10 courses over the well's rim gallery around its whole circumference, and only 3 of 72
    # sampled bearings were at grade. The well declares four approaches at 0/90/180/270 that reach
    # out to about r=58; the terrain buried every one of them from r=64 outward.
    #
    # A ramp is a VALLEY, not a slot: the cap rises along the ray at `slope` and rises again as
    # you move sideways out of the corridor, so the ground falls into it from both flanks instead
    # of a trench being cut through a hill.
    site.way = np.zeros(h.shape, bool)
    site.way_edge = np.zeros(h.shape, bool)
    site.way_t = np.zeros(h.shape)
    for spec in (p.get("ramps") or ()):
        a = math.radians(float(spec.get("bearing", 0.0)))
        half = float(spec.get("width", 9)) / 2.0
        rs = float(spec.get("slope", 0.5))
        shoulder = float(spec.get("shoulder", 0.7))
        along = (vv - mv) * math.cos(a) + (uu - mu) * math.sin(a)
        across = np.abs(-(vv - mv) * math.sin(a) + (uu - mu) * math.cos(a))
        cap = (np.maximum(0.0, along - hold + 2.0) * rs
               + np.maximum(0.0, across - half) * shoulder)
        h = np.where(along > 0, np.minimum(h, cap), h)
        # **AND THE ROUTE ITSELF, AS A MASK.** A green valley is not a way in: a guest on the
        # downs sees turf in every direction and no reason to believe one fold of it leads
        # anywhere. The cap material follows this in `_fill`, so the paving IS the ground rather
        # than a second pass laid over it - `Canvas.put` refuses an occupied cell, and a way
        # written afterwards would have been refused by the turf it is meant to replace.
        wh = max(1.0, float(spec.get("way", 3)) / 2.0)
        run = float(spec.get("run", 46))
        on = (along > hold - 3) & (along < hold + run) & (across <= wh + 1.0)
        site.way |= on & (across <= wh)
        site.way_edge |= on & (across > wh)
        site.way_t = np.where(on, np.clip((along - hold + 3.0) / run, 0.0, 1.0), site.way_t)

    # THE DELLS: small level pockets with a lip, which is what a "small area" is. They are cut
    # AFTER the clamp, because a hollow is not a thing the walkability rule has to protect - it is
    # the rule's own shape inverted.
    for spec in (p.get("dells") or ()):
        dvv, duu, rr, depth = (float(x) for x in spec)
        dd = np.sqrt((vv - dvv) ** 2 + (uu - duu) ** 2) / max(1.0, rr)
        bowl = np.clip(1.0 - dd, 0.0, 1.0) ** 0.7
        h = h - bowl * depth
    h = np.maximum(0.0, h)

    h = np.where(site.buildable(), h, 0.0)
    if not hasattr(site, 'wave'):
        site.wave = np.zeros_like(h)
    if not hasattr(site, 'ray'):
        site.ray = np.zeros_like(h)
    for a in ('way', 'way_edge'):
        if not hasattr(site, a):
            setattr(site, a, np.zeros(h.shape, bool))
    if not hasattr(site, 'way_t'):
        site.way_t = np.zeros_like(h)
    return _terrace(h, int(p.get("bench", 3)), _noise(dv, du, seed + 71, grain=11))


def _walkable(h: np.ndarray) -> int:
    """How many neighbouring pairs of the finished ground differ by more than a player can climb.

    A player climbs 1.25, so a two-course step is a wall. This is the number `tests/test_downs.py`
    asserts to zero, and it is the difference between terrain and an obstacle.
    """
    hi = np.rint(h).astype(int)
    bad = 0
    for a, b in ((hi[1:, :], hi[:-1, :]), (hi[:, 1:], hi[:, :-1])):
        bad += int((np.abs(a - b) > 1).sum())
    return bad


def relax(h: np.ndarray, mask: np.ndarray, rounds: int = 24) -> np.ndarray:
    """Beat every step down to one course, by lowering the high side.

    **LOWERING, NEVER RAISING**, and that is the whole of it: raising the low side would push
    ground into a street or over a build, and the clamp that keeps this walkable is expressed as a
    CEILING. A cell may be at most one course over its lowest neighbour, so the pass converges
    downward and cannot violate anything the field already guaranteed.
    """
    out = np.rint(h).astype(np.int16)
    for _ in range(rounds):
        low = out.copy()
        low[1:, :] = np.minimum(low[1:, :], out[:-1, :])
        low[:-1, :] = np.minimum(low[:-1, :], out[1:, :])
        low[:, 1:] = np.minimum(low[:, 1:], out[:, :-1])
        low[:, :-1] = np.minimum(low[:, :-1], out[:, 1:])
        nxt = np.minimum(out, low + 1)
        nxt = np.where(mask, nxt, 0)
        if np.array_equal(nxt, out):
            break
        out = nxt
    return out


# --------------------------------------------------------------------------- the fill


def _pick(table, v, u, y, seed) -> str:
    r = hash01(v * 5 + 1, u * 7 + 3, y * 11 + 5, seed)
    acc = 0.0
    for key, share in table:
        acc += share
        if r < acc:
            return key
    return table[0][0]


#: what a paved flag turns into when it is tilted. A block with no slab keeps its own face.
_SLABS = {"stone": "stone_slab", "smooth_stone": "smooth_stone_slab", "stone_bricks":
          "stone_brick_slab", "deepslate_tiles": "deepslate_tile_slab", "polished_deepslate":
          "polished_deepslate_slab", "blackstone": "blackstone_slab", "cobblestone":
          "cobblestone_slab", "polished_blackstone_bricks": "polished_blackstone_brick_slab",
          "cobbled_deepslate": "cobbled_deepslate_slab", "deepslate_bricks":
          "deepslate_brick_slab", "andesite": "andesite_slab", "granite": "granite_slab"}


def _slab_of(name: str) -> str:
    return _SLABS.get(name, name)


def _steps_down(h: np.ndarray, v: int, u: int) -> bool:
    """Is this column exactly one course over a neighbour? That riser is what the slab softens."""
    top = int(h[v, u])
    dv, du = h.shape
    for a, b in ((v + 1, u), (v - 1, u), (v, u + 1), (v, u - 1)):
        if 0 <= a < dv and 0 <= b < du and int(h[a, b]) == top - 1:
            return True
    return False


def _fill(lot: _Lot, site: _Site, h: np.ndarray, p: dict, seed: int) -> dict:
    """Raise every column, bedded, and cap it with turf or with rock depending on how steep it is.

    **ROCK SHOWS WHERE SOIL CANNOT HOLD.** A hill that is turf all over is a green blancmange and a
    hill that is rock all over is a quarry; the ground is the park's own lawn where it is gentle
    and the land's own basalt where it is not, and the boundary between them is the thing that
    makes it read as landscape rather than as a shape.
    """
    dv, du = site.dv, site.du
    gv, gu = np.gradient(h.astype(float))
    steep = np.maximum(np.abs(gv), np.abs(gu))
    turf_at = float(p.get("turf_slope", 0.75))
    # **THE RIM IS ROCK, NOT LAWN.** Turf everywhere makes a green blancmange with no geology in
    # it, and the one place the ground must read as CUT is the scarp at the shaft - a hundred
    # courses of stone below and grass right up to the lip is the picture of a hole in a plate,
    # which is the thing this design exists to stop being.
    ring = float(p.get("rock_ring", 8))
    hard = getattr(site, "hard", None)
    near = (hard < ring) if hard is not None else np.zeros(h.shape, bool)
    #: THE CREST OF EVERY WAVE IS BARE ROCK AND THE TROUGH IS TURF. This is the one thing that
    #: makes a shock wave read at eye level rather than only in plan.
    wave = getattr(site, "wave", np.zeros(h.shape))
    ray = getattr(site, "ray", np.zeros(h.shape))
    broken = getattr(site, "broken", np.zeros(h.shape, bool))
    way = getattr(site, "way", np.zeros(h.shape, bool))
    way_edge = getattr(site, "way_edge", np.zeros(h.shape, bool))
    way_t = getattr(site, "way_t", np.zeros(h.shape))
    crest = float(p.get("crest_at", 0.45))
    #: A RAY IS A STREAK OF WHAT CAME OUT, so it is bare rock wherever it runs - that is the whole
    #: of why it reads from the ground rather than only from above.
    on_crest = (wave > crest) | (ray > float(p.get("ray_at", 0.30)))
    n = turf = rock = 0
    for v in range(dv):
        for u in range(du):
            top = int(h[v, u])
            if top <= 0:
                continue
            y0 = int(site.seat[v, u])
            # **A CLEAN GRASS/ROCK LINE IS A CONTOUR, AND CONTOURS ARE NOT WHAT GROUND LOOKS
            # LIKE.** Thresholded on the gradient alone this came out 60% bare grey - because the
            # walkability clamp holds whole regions at exactly the threshold slope - and it read
            # as a slag heap. Steep ground is rock only about half the time, so the boundary
            # breaks up into outcrops with turf between them, which is what a hillside is.
            bare = bool(near[v, u] or on_crest[v, u]
                        or (steep[v, u] > turf_at
                            and hash01(v, u, 17, seed) < float(p.get("bare_share", 0.18))))
            for k in range(top):
                # **ONLY THE SKIN IS BEDDED.** Every step here is one course by construction, so
                # nothing deeper than about three is ever seen - and banding the interior spent
                # thirty thousand `ok`-tier blackstone on cells no guest can look at. The bulk is
                # the cheap basalt; the strata are the top three courses, which are the ones a
                # face shows.
                if k < top - 3:
                    key = "rock"
                else:
                    band = _STRATA[((y0 + k) // _BAND) % len(_STRATA)]
                    key = _pick(band, v, u, y0 + k, seed)
                if k == top - 1 and way[v, u]:
                    # **BROKEN NEAR THE SHAFT AND WHOLE FURTHER OUT.** The damage is a function of
                    # distance from the mouth, so the route reads as intact where a guest joins it
                    # and ruined where it arrives - which is the direction they walk. The breaks
                    # are GAPS and heaved flags, never a narrowing: a path that thins to nothing
                    # reads as a mistake, one that keeps its width and loses its surface reads as
                    # damage.
                    t = float(way_t[v, u])
                    r = hash01(v, u, 121, seed)
                    if r < 0.34 * (1.0 - t) ** 1.5:
                        key = "turf"               # a gap: the turf shows through
                        turf += 1
                    elif r < 0.34 * (1.0 - t) ** 1.5 + 0.16 * (1.0 - t):
                        n += int(lot.slab(v, y0 + k, u, GROUND["chip"]))
                        rock += 1
                        continue
                    else:
                        key = "path_edge" if way_edge[v, u] else "path"
                        rock += 1
                    n += int(lot.put(v, y0 + k, u, GROUND[key]))
                    continue
                if k == top - 1 and broken[v, u] and top <= 2:
                    # **A BROKEN PATH IS HEAVED, NOT BURIED.** Jack: "small side paths that cut
                    # through the landscape should be broken and impacted by ripples with only
                    # the main larger avenue intact." Where the ground rises only a course or two
                    # over a side path, the cap is the PATH'S OWN STONE, lifted and tilted - so
                    # the walk reads as something the ground pushed up through rather than as a
                    # walk somebody covered in soil. Deeper than that and it is simply gone under
                    # the hill, which is what the next trough is for.
                    # **ONLY PAVING MAY BE HEAVED.** `surface_cells` holds everything `Park
                    # Ways` owns, furniture included, so the recorded floor under a side path can
                    # be a lamp base or a rail - and re-laying THAT as a flagstone put iron bars,
                    # copper and a froglight into a hillside. A flag is a flag; anything else
                    # falls back to the land's own rock.
                    flag = str(site.floor[v, u] or "")
                    if flag not in _SLABS:
                        flag = GROUND["rock"]
                    # **AND A BLOCK WITH NO SLAB CANNOT BE LAID AS ONE.** `_slab_of` hands back
                    # the block itself when the family has no slab, and `lot.slab` then writes
                    # `type` and `waterlogged` onto a `smooth_basalt` that has neither - seventeen
                    # illegal states, which the state audit caught and nothing else would have.
                    tilt = _slab_of(flag)
                    if tilt != flag and hash01(v, u, 33, seed) < 0.34 and _steps_down(h, v, u):
                        n += int(lot.slab(v, y0 + k, u, tilt))
                    else:
                        n += int(lot.put(v, y0 + k, u, flag))
                    rock += 1
                    continue
                if k == top - 1:
                    if bare:
                        # **A ONE-COURSE STEP IS A STAIR; HALF OF ONE IS A SLOPE.** A rock face
                        # quantised to whole courses reads as stacked cubes, and softening the
                        # risers is the single biggest thing available to voxel terrain. Only the
                        # rock takes it: `moss_block` has no slab, and a plant cannot root on one.
                        if _steps_down(h, v, u) and hash01(v, u, 9, seed) < 0.62:
                            key = "slab_b" if hash01(v, u, 13, seed) < 0.3 else "slab"
                            n += int(lot.slab(v, y0 + k, u, GROUND[key]))
                            rock += 1
                            continue
                        key = "rock_b" if hash01(v, u, 3, seed) < 0.22 else "rock"
                        rock += 1
                    else:
                        key = "turf"
                        turf += 1
                elif k == top - 2 and on_crest[v, u] and hash01(v, u, 23, seed) < 0.34:
                    # THE VEIN, one course under the crest's own cap - so it shows in the face of
                    # every wave and nowhere else. It is the only colour this land has that no
                    # other land in the park does, and it is IN the ground rather than standing
                    # on it, which is the whole difference from the spires.
                    key = "seam" if hash01(v, u, 24, seed) < 0.62 else "seam_b"
                n += int(lot.put(v, y0 + k, u, GROUND[key]))
    return {"cells": n, "turf": turf, "rock": rock,
            "max": int(h.max()) if h.size else 0}


def _dress(lot: _Lot, site: _Site, h: np.ndarray, p: dict, seed: int) -> dict:
    """Plant the turf, lichen the rock, and sink the lamps flush into the ground.

    **A FIXTURE ON A SLOPE IS A POST IN A FIELD.** `pearlescent_froglight` set INTO the turf is
    Jack's own idiom - thirty-nine were scattered by hand across the lowland before any tool did
    it - it cannot be knocked off, it needs no support, and it is what stops a night pass wanting
    to stand a lamp on the hill.
    """
    dv, du = site.dv, site.du
    pl = p.get("plant") or {}
    dens = float(pl.get("density", 0.16))
    tree = float(pl.get("tree", 0.014))
    fern = float(pl.get("fern", 0.10))
    every = max(4, int(p.get("light", 13)))
    # **PLANT IN DRIFTS, NEVER IN CONFETTI.** An even scatter over twenty thousand columns reads
    # as speckle from any distance; the density is modulated by a coarse field so the downs come
    # out as thickets and clearings, which is what makes them somewhere rather than a texture.
    drift = _noise(dv, du, seed + 137, grain=17)
    #: **VEGETATION COLLECTS IN HOLLOWS**, which is true of real ground and is also what keeps
    #: the rings legible: a tree on a crest breaks the band it is standing on.
    wave = getattr(site, "wave", np.zeros(h.shape))
    #: **THE EJECTA FIELD.** Jack: "realistically we should be scattering blocks that arent grass
    #: or wood and are dark slate etc." Thickest at the rim and thinning outward - so the scatter
    #: is the ripples' own story told in material, and the ground round the shaft reads as
    #: something that was thrown out of it rather than as a lawn that happens to be lumpy.
    ray = getattr(site, "ray", np.zeros(h.shape))
    db = p.get("debris") or {}
    d_amt = float(db.get("density", 0.0))
    d_fall = max(6.0, float(db.get("decay", 60.0)))
    mv, mu, hold = (float(x) for x in p["mouth"])
    #: **SMALL GROUPINGS OF ROCK.** Jack: "our tree coverage is too thick and we need to put other
    #: things, small groupings of rock maybe, to make this more real feeling." Real ground is not
    #: uniformly planted: it is thickets, bare shoulders, and boulders lying where they fell. The
    #: clumps are seeded on their own coarse field so they gather rather than speckle - the
    #: thicket's rule, which this file has already had to apply to the planting.
    rk = p.get("rocks") or {}
    r_amt = float(rk.get("density", 0.0))
    r_field = _noise(dv, du, seed + 211, grain=int(rk.get("grain", 13)))
    out = {"bush": 0, "fern": 0, "tree": 0, "lichen": 0, "glow": 0, "carpet": 0, "debris": 0,
           "rocks": 0}
    for v in range(dv):
        for u in range(du):
            top = int(h[v, u])
            if top <= 0:
                continue
            y = int(site.seat[v, u]) + top          # the first free course over the ground
            name = lot.name_at(v, y - 1, u)
            if getattr(site, "way", np.zeros(1, bool)).any() and site.way[v, u]:
                continue          # nothing is planted or dropped in the route
            r = hash01(v, u, 41, seed)
            thick = (0.25 + 1.75 * float(drift[v, u]) ** 1.6) * (1.0 - 0.75 * max(0.0, float(wave[v, u])))
            if name == GROUND["turf"] and d_amt > 0.0:
                rr = max(0.0, ((v - mv) ** 2 + (u - mu) ** 2) ** 0.5 - hold)
                # ...and the ejecta lies ON the rays, thickest near the rim. Scattered evenly it
                # is speckle; scattered along the streaks it is what threw them.
                # CLAMPED. Unbounded, the ray multiplier took the scatter to ~69% of the turf
                # near the rim and the downs came out as a slate field with moss on it - the
                # scatter is meant to be litter on ground, not the ground.
                lane = min(1.6, 0.25 + 2.0 * float(ray[v, u]))
                if hash01(v, u, 61, seed) < d_amt * lane * (0.12 + 0.88 * np.exp(-rr / d_fall)):
                    # **A SLAB, BECAUSE A FULL BLOCK ON TURF IS A NEW STEP.** The ground is
                    # walkable by construction and a boulder dropped on it would undo that one
                    # cell at a time; a bottom slab is half a course and changes nothing. A full
                    # block goes down only where all four neighbours stand at the same height, so
                    # the step it makes is one course from level ground.
                    k = hash01(v, u, 62, seed)
                    flat = all(int(h[a, b]) == top
                               for a, b in ((v + 1, u), (v - 1, u), (v, u + 1), (v, u - 1))
                               if 0 <= a < dv and 0 <= b < du)
                    # **AND THE SLAB NEEDS THE SAME GUARD AS THE BLOCK.** A bottom slab on ground
                    # that already stands a course over its neighbour is a step and a half from
                    # that neighbour, which is over the 1.25 a player climbs - measured, 1,918
                    # such steps, every one of them made by the scatter that was supposed to be
                    # the safe half of it.
                    if not flat:
                        continue
                    if k < 0.34:
                        key = ("debris" if k < 0.14 else
                               "debris_b" if k < 0.24 else
                               "debris_c" if k < 0.30 else "debris_d")
                        out["debris"] += int(lot.put(v, y, u, GROUND[key]))
                    else:
                        key = ("chip" if k < 0.62 else
                               "chip_b" if k < 0.84 else "chip_c")
                        out["debris"] += int(lot.slab(v, y, u, GROUND[key]))
                    continue
            if name == GROUND["turf"]:
                # THE LAMP IS THE GROUND. It replaces the turf rather than standing on it, so it
                # reaches 14 rather than 15 - an opaque emitter a course down - which is what the
                # spacing is set against.
                if (v % every == 0) and (u % every == 0) and r < 0.75:
                    if lot.put(v, y - 1, u, GROUND["glow"]):
                        out["glow"] += 1
                        continue
                if r_amt > 0.0 and float(r_field[v, u]) > 0.62                         and hash01(v, u, 71, seed) < r_amt:
                    out["rocks"] += _boulder(lot, site, h, v, y, u, seed)
                elif r < tree * thick:
                    out["tree"] += _tree(lot, site, v, y, u, seed)
                elif r < (tree + dens) * thick:
                    key = "bloom" if hash01(v, u, 42, seed) < 0.3 else "bush"
                    out["bush"] += int(lot.put(v, y, u, GROUND[key]))
                elif r < (tree + dens + fern) * thick:
                    out["fern"] += int(lot.put(v, y, u, GROUND["fern"]))
                elif r < (tree + dens + fern) * thick + 0.10:
                    out["carpet"] += int(lot.put(v, y, u, GROUND["carpet"]))
            else:
                # GLOW LICHEN ON THE ROCK FACES, which is the one thing that lights a steep face
                # without standing anything on it - and it is the lush palette this land is in.
                if r < 0.18:
                    for face, dvv, duu in (("north", 0, -1), ("south", 0, 1),
                                           ("east", 1, 0), ("west", -1, 0)):
                        a, b = v + dvv, u + duu
                        if not _open(site, a, b):
                            continue
                        if int(h[a, b]) < top - 1 and not lot.has(a, y - 1, b):
                            ok = lot.put(a, y - 1, b, GROUND["lichen"],
                                         **{face: "false", _OPP[face]: "true",
                                            "up": "false", "down": "false",
                                            "waterlogged": "false"})
                            out["lichen"] += int(ok)
                            break
    return out


_OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def _open(site: _Site, v: int, u: int) -> bool:
    """**A CANOPY IS CELLS, NOT A COLUMN.** A crown reaches two cells past its own trunk, and
    placed blind it grows straight into whatever stands there - measured, exactly two cells of
    leaf ended up inside `PF Prism Well` and `PF Water Wyrm Garden`. The scatter and the claim row
    both shipped this once; it is the same rule, a third time."""
    return (0 <= v < site.dv and 0 <= u < site.du and not site.build[v, u])


def _boulder(lot: _Lot, site: _Site, h: np.ndarray, v: int, y: int, u: int, seed: int) -> int:
    """A small group of rock lying on the turf - one to four lumps, one or two courses.

    **IT IS A GROUP, NOT A BLOCK.** A single stone on a lawn is litter; three or four together
    with a course of height between them is an outcrop, and it is the thing that stops downland
    reading as a golf course. Nothing here is over two courses, so the ground stays walkable.
    """
    n = 0
    for k in range(1 + int(hash01(v, u, 81, seed) * 3.4)):
        a = v + int(hash01(v, u, 82 + k, seed) * 5) - 2
        b = u + int(hash01(v, u, 87 + k, seed) * 5) - 2
        if not _open(site, a, b) or int(h[a, b]) <= 0:
            continue
        yy = int(site.seat[a, b]) + int(h[a, b])
        if lot.has(a, yy, b):
            continue
        # **ONE COURSE, ON LEVEL GROUND ONLY.** A boulder is still ground as far as a walk is
        # concerned: dropped on a cell that already stands a course over its neighbour it is a
        # two-course step, which is a wall. The debris pass learned this and the boulders were
        # written without it - the walkability test caught them, which is what it is for.
        if any(int(h[c, d]) != int(h[a, b])
               for c, d in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1))
               if 0 <= c < h.shape[0] and 0 <= d < h.shape[1]):
            continue
        key = ("deep_b" if hash01(a, b, 91, seed) < 0.42 else
               "rock_c" if hash01(a, b, 92, seed) < 0.5 else "deep")
        n += int(lot.put(a, yy, b, GROUND[key]))
    return n


def _tree(lot: _Lot, site: _Site, v: int, y: int, u: int, seed: int) -> int:
    """A small azalea tree - four to six courses, so it dresses the ground rather than becoming a
    second skyline. The Frontier owns the tall canopy; this land is downland."""
    hh = 4 + int(hash01(v, u, 51, seed) * 2.4)
    n = 0
    for k in range(hh):
        n += int(lot.log(v, y + k, u, GROUND["wood"]))
    crown = y + hh - 2
    for dvv in range(-2, 3):
        for duu in range(-2, 3):
            d = abs(dvv) + abs(duu)
            if d > 2 or (dvv == 0 and duu == 0):
                continue
            if not _open(site, v + dvv, u + duu):
                continue
            for k in range(crown, crown + 2):
                if d == 2 and k == crown + 1:
                    continue
                key = "leaf" if hash01(v + dvv, u + duu, 52, seed) < 0.3 else "leaf_b"
                n += int(lot.put(v + dvv, k, u + duu, GROUND[key],
                                 distance="1", persistent="true", waterlogged="false"))
    for duu in (-1, 0, 1):
        if not _open(site, v, u + duu):
            continue
        n += int(lot.put(v, y + hh, u + duu, GROUND["leaf"] if duu == 0 else GROUND["leaf_b"],
                         distance="1", persistent="true", waterlogged="false"))
    return n


# --------------------------------------------------------------------------- build


def build(cfg: dict, donors=None) -> Canvas:
    p = {**DOWNS, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the downs need their measured lot: lot: [dv, du]")
    if not p.get("under"):
        raise ValueError("the downs read the world they are verified against: under: <capture>")
    if not p.get("mouth"):
        raise ValueError("the downs rise toward the shaft: mouth: [v, u, hold]")

    dv, du = int(p["lot"][0]), int(p["lot"][1])
    seed = int(p.get("seed", 0))
    c = Canvas(dv, int(p.get("sy") or 34), du, donors)
    lot = _Lot(c, dv, du, seed=seed)
    anchor = [int(x) for x in p["anchor"]]
    at_v, at_u = (int(x) for x in (p.get("at") or (0, 0)))
    ctx = Ctx(p["under"])
    box = (anchor[0] + at_v - 2, anchor[0] + at_v + dv + 1,
           anchor[1] - 3, anchor[1] + int(p.get("sy") or 34),
           anchor[2] + at_u - 2, anchor[2] + at_u + du + 1)
    site = _Site(ctx, anchor, dv, du, (at_v, at_u),
                 surface_cells(p.get("off_limits") or (), box),
                 mine=shipped_cells(p.get("previous")),
                 main_at=float(p.get("main_at", 3.0)), keep=p.get("keep") or ())

    # **WALKABILITY IS A PROPERTY OF THE ABSOLUTE TOP, NOT OF THE HEIGHT ABOVE THE SEAT.** The
    # world's own floor is not one plane - this lot seats at 0, 1 and 2 - so two neighbours with
    # the same `h` can still be two courses apart in the world. Relaxed on `h` alone the shipped
    # ground had 399 such steps, every one of them invisible in the field and a wall in game.
    h = height(p, site)
    build = site.buildable()
    top = np.where(build, site.seat.astype(np.int16) + np.rint(h).astype(np.int16), 0)
    top = relax(top, build)
    h = np.maximum(0, top - site.seat.astype(np.int16))
    h = np.where(build, h, 0)
    parts = {"ground": _fill(lot, site, h, p, seed)}
    parts["dressing"] = _dress(lot, site, h, p, seed)
    parts["steps"] = int(_walkable(np.where(build, site.seat + h, 0)))
    parts["hills"] = int((h > 0).sum())
    parts["mean"] = round(float(h[h > 0].mean()) if (h > 0).any() else 0.0, 2)

    c.world_origin = (anchor[0] + at_v, anchor[1], anchor[2] + at_u)
    c.meta = {
        "kind": "downs",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "prismworks",
        "facing": "west",
        "profile_axis": "u",
        "refused": lot.refused,
        "parts": parts,
        "contract": (
            "the whole of Prismworks and its reach as gentle downland: ground swelling from "
            "nothing at the plot's edges to a crest against the well's collar, so the shaft is a "
            "hole in a hill rather than a hole in a plate. Turf where soil holds, the land's own "
            "basalt where it does not, azalea and fern over it, and every cell walkable from the "
            "street that bounds it - no step anywhere is more than one course."),
    }
    return c
