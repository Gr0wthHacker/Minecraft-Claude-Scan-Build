"""The park's water: does it hold, does it freeze, and does it touch anything it must not.

**THE THREE PROPERTIES THIS FILE EXISTS FOR ARE ALL RE-DERIVED FROM THE FINISHED MODEL**, in the
composite with the park that is already standing - never read back out of the generator's own
sidecar. That is the whole lesson of the log flume: it self-checked with `fluids.carries`, which
asks whether the ride PATH is wet, reported success, and drained 199,959 cells to Y-1908 while the
render, the audit and the bill of materials all passed it. A generator's own opinion of its water
is worth nothing.

    1. IT CANNOT LEAK      every water cell bedded and walled - `fluids.unenclosed` is empty, and
                           `fluids.escapes` reaches not one cell outside the lake
    2. IT CANNOT FREEZE    block light >= 10 in every water cell, propagated through the composite
    3. IT TOUCHES NOTHING  not one cell on a street, path, plaza, verge, lamp, bench or building -
                           the world under every design cell is lawn, and nothing else

Fixtures read the SHIPPED litematic rather than regenerating, for the reason the lowland town
tests record: a design here is remaining work, so a regeneration against a moved world strips
every cell that has since been built and the test starts measuring a different design.
"""
from __future__ import annotations

import os

import numpy as np
import pytest

from mcbuild import fluids, nightlight, scan

DESIGN = "out/PF Water Claim Lake.litematic"
GARDEN = "out/PF Water Wyrm Garden.litematic"
CONTEXT = "out/Park Complete.litematic"

#: THE THREE PROPERTIES ARE ABOUT WATER, NOT ABOUT THIS LAKE. Both pieces are run through them -
#: the Claim Lake and the smaller Wyrm Garden - because a second piece of water built from the
#: same generator with the terrace and the crossing switched off is exactly where a containment
#: rule that only held for one shape would come apart.
PIECES = [DESIGN, GARDEN]

#: What each piece owns, so nothing can wander into a threshold path or a promenade verge.
#: {litematic: (v0, v1, u0, u1)}
BANDS = {DESIGN: (24, 112, 173, 211), GARDEN: (87, 119, 388, 426)}

#: The park's own lawn, and the only two blocks this design is allowed to find in its way.
LAWN = {"moss_block", "moss_carpet"}
GROUND_Y = 202
FREEZE = 10                     # water under this turns to ice


# --------------------------------------------------------------------------- fixtures


def _need(path: str):
    if not os.path.exists(path):
        pytest.skip(f"{path} is not built - run configs/pf_water_claim_lake.yaml first")
    return scan.load(path)


@pytest.fixture(scope="module", params=PIECES, ids=lambda p: os.path.basename(p).split(".")[0])
def piece(request):
    return _need(request.param)


@pytest.fixture(scope="module")
def design():
    return _need(DESIGN)


@pytest.fixture(scope="module")
def context():
    return _need(CONTEXT)


def _cells(s):
    """{(x, y, z): name} in WORLD coordinates. Assert in world coordinates, never in canvas ones:
    two models sized to their own content line up against nothing."""
    ox, oy, oz = s.origin
    names = [n.split(":")[-1] for n in s.model.names]
    ids = s.model.ids
    out = {}
    for y, z, x in zip(*np.nonzero(ids)):
        out[(ox + int(x), oy + int(y), oz + int(z))] = names[ids[y, z, x]]
    return out


@pytest.fixture(scope="module")
def built(design):
    return _cells(design)


@pytest.fixture(scope="module")
def wet(piece):
    return _cells(piece)


@pytest.fixture(scope="module")
def merged(piece, context):
    return _composite(piece, context)


@pytest.fixture(scope="module")
def composite(design, context):
    return _composite(design, context)


def _composite(design, context):
    """A piece of water standing in the park it is built into - which is the only world it will
    ever be in, and the only one worth measuring."""
    cells = {}
    ox, oy, oz = context.origin
    names = [n.split(":")[-1] for n in context.model.names]
    ids = context.model.ids
    dx0, dy0, dz0 = design.origin
    dsy, dsz, dsx = design.model.ids.shape
    lo = (dx0 - 3, dy0 - 3, dz0 - 3)
    hi = (dx0 + dsx + 2, dy0 + dsy + 12, dz0 + dsz + 2)
    for y, z, x in zip(*np.nonzero(ids)):
        p = (ox + int(x), oy + int(y), oz + int(z))
        if all(lo[i] <= p[i] <= hi[i] for i in range(3)):
            cells[p] = names[ids[y, z, x]]
    dig = {tuple(d) for d in (design.meta.get("dig") or [])}
    for p in dig:
        cells.pop(p, None)                       # the player breaks these before placing
    cells.update(_cells(design))
    return cells, lo, hi


# --------------------------------------------------------------------------- 1. it cannot leak


def test_every_water_cell_is_bedded_and_walled(merged):
    """`fluids.unenclosed` over the finished composite: water over a hole, or beside one.

    The park is a ONE-BLOCK plate with open void under it, so the whole basin - bed and wall
    both - is placed by this design. There is no terrain to be wrong about.
    """
    cells, _lo, _hi = merged
    bad = fluids.unenclosed(cells)
    assert bad == [], f"{len(bad)} unenclosed water cell(s), first: {bad[:5]}"


def test_the_water_never_reaches_a_cell_the_design_did_not_mean_it_to(merged, wet):
    """`escapes`, which is a DIFFERENT question from `unenclosed` and the one the flume failed.

    `unenclosed` is static and local; this floods the lake from every one of its own sources and
    reports every cell the flood arrives at that is not lake. An empty list is the only
    acceptable answer.
    """
    cells, lo, hi = merged
    envelope = [p for p, n in wet.items() if n == "water"]
    assert envelope, "the design holds no water at all"
    bounds = (lo[0], lo[1], lo[2], hi[0], hi[1], hi[2])
    out = fluids.escapes(cells, envelope, envelope, bounds=bounds)
    assert out == [], f"water escapes to {len(out)} cell(s), first: {out[:5]}"


def test_the_lake_is_one_body_of_water(wet):
    """A bridge over a lake, not two ponds either side of a causeway - which is what a deck laid
    at the water's own course would have made of it."""
    pool = {p for p, n in wet.items() if n == "water"}
    seen, comps = set(), []
    for start in pool:
        if start in seen:
            continue
        stack, n = [start], 0
        seen.add(start)
        while stack:
            x, y, z = stack.pop()
            n += 1
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                q = (x + d[0], y + d[1], z + d[2])
                if q in pool and q not in seen:
                    seen.add(q)
                    stack.append(q)
        comps.append(n)
    assert len(comps) == 1, f"the water is in {len(comps)} pieces: {sorted(comps, reverse=True)}"


def test_the_bed_is_never_a_block_that_falls(wet):
    """Sand and gravel are the two obvious lake beds in Minecraft and both would pour into the
    void the moment the plate under them is cut - which this design does by definition."""
    from mcbuild import blocks
    fell = sorted({n for n in wet.values() if blocks.falls(n)})
    assert fell == [], f"gravity blocks over an open basin: {fell}"


# --------------------------------------------------------------------------- 2. it cannot freeze


def _light(cells, lo, hi):
    nx, ny, nz = (hi[i] - lo[i] + 1 for i in range(3))
    names = sorted({"air"} | set(cells.values()))
    index = {n: i for i, n in enumerate(names)}
    opaque_p, emit_p, _passy, _spawn, water_p = nightlight.classify(names)
    ids = np.zeros((ny, nz, nx), np.int32)
    for (x, y, z), n in cells.items():
        ids[y - lo[1], z - lo[2], x - lo[0]] = index[n]
    light = nightlight.propagate(opaque_p[ids], emit_p[ids].astype(np.int16))
    return light, water_p[ids], ids


def test_no_water_cell_is_dark_enough_to_freeze(merged):
    """Propagated, not asserted. The court hall's pool froze on its first build - 29 ice blocks -
    and every check it had passed it, because none of them was a light model.

    The volume is cut to the design's own box plus a little, so the park's distant lamps do not
    count toward the answer: that under-reports the light, which is the safe direction.
    """
    cells, lo, hi = merged
    light, water, _ids = _light(cells, lo, hi)
    dark = np.argwhere(water & (light < FREEZE))
    worst = int(light[water].min())
    assert not len(dark), (f"{len(dark)} water cell(s) below {FREEZE} - the lake ices over. "
                           f"darkest is {worst}")


def test_the_light_keeps_a_course_of_margin_over_the_freezing_floor(merged):
    """EXACTLY TEN IS ONE FALLOFF FROM FAILING. It is the difference between `lantern` at 15 and
    `soul_lantern` at exactly 10 that made this repo write down that a soul lantern is mood and
    never a guard; the same reasoning applies to the answer a solver stops at."""
    cells, lo, hi = merged
    light, water, _ids = _light(cells, lo, hi)
    assert int(light[water].min()) >= FREEZE + 1


def test_the_light_comes_from_the_bed_and_never_from_a_fixture_in_the_lake(wet):
    """A lantern standing in a lake is a lantern standing in a lake. Every emitter under the
    water line is a froglight, which IS the bed."""
    surface = GROUND_Y
    inside = [(p, n) for p, n in wet.items()
              if p[1] <= surface and n in nightlight.EMIT and nightlight.EMIT[n] > 0]
    assert inside, "the lake is not lit from within at all"
    assert {n for _p, n in inside} == {"ochre_froglight"}, \
        f"something other than the bed is lighting the water: {sorted({n for _p, n in inside})}"


def test_every_bed_light_is_actually_part_of_the_bed(wet):
    """A froglight is placed by replacing a bed cell or stacking on one; a floating light in the
    middle of the water would be a fixture wearing the bed's clothes."""
    glow = [p for p, n in wet.items() if n == "ochre_froglight"]
    assert glow, "the lake carries no bed light at all"
    for x, y, z in glow:
        assert y < GROUND_Y, f"froglight at {(x, y, z)} is not under the water line"
        above = wet.get((x, y + 1, z))
        assert above in ("water", "ochre_froglight"), \
            f"froglight at {(x, y, z)} has {above} over it, so it is not part of the bed"


# --------------------------------------------------------------------------- 3. it touches nothing


def test_not_one_cell_of_this_design_stands_on_anything_but_lawn(wet, context):
    """THE PROPERTY THAT IS THE DIFFERENCE BETWEEN THIS PARK AND THE ONE JACK THREW AWAY.

    Zero of the park's placed modules touches another. A lawn cell is fair game - a lake is made
    by removing ground - and a paved cell, a lamp mast, a bench, a rail or a heron leg is not.
    Measured cell by cell against the shipped park rather than argued from the plan.
    """
    ox, oy, oz = context.origin
    names = [n.split(":")[-1] for n in context.model.names]
    ids = context.model.ids
    sy, sz, sx = ids.shape
    clashes = []
    for (x, y, z) in wet:
        i, j, k = y - oy, z - oz, x - ox
        if not (0 <= i < sy and 0 <= j < sz and 0 <= k < sx):
            continue
        held = names[ids[i, j, k]]
        if held != "air" and held not in LAWN:
            clashes.append(((x, y, z), held))
    assert clashes == [], f"{len(clashes)} cell(s) on something that is not lawn: {clashes[:6]}"


def test_it_keeps_off_the_two_threshold_paths_and_the_promenade(piece, wet):
    """The reach's own streets, measured off the shipped ground: the handoffs at U170-172 and
    U212-214 run the full depth, the back promenade is V123-127 and its lamp line is V121."""
    v0, v1, u0, u1 = BANDS[piece.litematic_path.replace("\\", "/")]
    for (x, y, z) in wet:
        v, u = x - 97500, z - 80300
        assert u0 <= u <= u1, f"cell at U{u} is on a threshold path"
        assert v0 <= v <= v1, f"cell at V{v} is outside the band this design owns"


def test_the_dig_list_names_every_lawn_cell_the_lake_breaks(piece, wet, context):
    """A litematic cannot express removal, so every cell of the park's own ground that this
    design covers has to be in the sidecar or nobody is ever told to break it."""
    dig = {tuple(d) for d in (piece.meta.get("dig") or [])}
    ox, oy, oz = context.origin
    names = [n.split(":")[-1] for n in context.model.names]
    ids = context.model.ids
    sy, sz, sx = ids.shape
    missing = []
    for (x, y, z) in wet:
        i, j, k = y - oy, z - oz, x - ox
        if 0 <= i < sy and 0 <= j < sz and 0 <= k < sx and names[ids[i, j, k]] in LAWN:
            if (x, y, z) not in dig:
                missing.append((x, y, z))
    assert missing == [], f"{len(missing)} lawn cell(s) covered and not dug: {missing[:6]}"


def test_a_carpet_is_never_left_standing_on_the_lake(piece, wet, context):
    """The lawn's own moss-carpet scatter sits at Y203. Over a cell that becomes water it would
    be left floating - and nothing in the pipeline reports it, because a leftover is not a
    collision. It goes in the dig list with everything else."""
    dig = {tuple(d) for d in (piece.meta.get("dig") or [])}
    ox, oy, oz = context.origin
    names = [n.split(":")[-1] for n in context.model.names]
    ids = context.model.ids
    sy, sz, sx = ids.shape
    stranded = []
    for (x, y, z), n in wet.items():
        if n != "water" or y != GROUND_Y:
            continue
        i, j, k = y + 1 - oy, z - oz, x - ox
        if 0 <= i < sy and 0 <= j < sz and 0 <= k < sx and names[ids[i, j, k]] == "moss_carpet":
            if (x, y + 1, z) not in dig and (x, y + 1, z) not in wet:
                stranded.append((x, y + 1, z))
    assert stranded == [], f"{len(stranded)} moss carpet(s) left on the water: {stranded[:6]}"


# --------------------------------------------------------------------------- the heron


def test_the_heron_still_stands_on_something(built, context):
    """A wading bird in the shallows, not a bird hovering over a lake. Its two feet are at Y203
    on (V45,U198) and (V52,U198); the shoal has to carry them, and this design must not have
    turned the ground under either into water."""
    for v, u in ((45, 198), (52, 198)):
        p = (97500 + v, GROUND_Y, 80300 + u)
        here = built.get(p)
        if here is None:
            ox, oy, oz = context.origin
            names = [n.split(":")[-1] for n in context.model.names]
            here = names[context.model.ids[p[1] - oy, p[2] - oz, p[0] - ox]]
        assert here not in ("water", "air"), f"the heron's foot at V{v} U{u} stands on {here}"


def test_the_creek_actually_reaches_the_heron(built):
    """A shoal with no water in it is a lawn with a bird on it. There has to be water inside the
    heron's own footprint - between its legs, which is where a heron fishes."""
    wet = {(p[0] - 97500, p[2] - 80300) for p, n in built.items()
           if n == "water" and p[1] == GROUND_Y}
    creek = [(v, u) for v, u in wet if 46 <= v <= 51 and 194 <= u <= 203]
    assert len(creek) >= 20, f"only {len(creek)} water cells between the heron's legs"


# --------------------------------------------------------------------------- the built pieces


def test_the_boardwalk_crosses_the_whole_reach_and_lands_on_both_banks(built):
    """A crossing is a route, and a route with one end is a pier. It runs from the U173 bank to
    the U211 bank - one cell clear of each threshold path - and every column of it is decked."""
    deck = {(p[0] - 97500, p[2] - 80300) for p, n in built.items()
            if p[1] == GROUND_Y + 1 and n in ("oak_planks", "spruce_planks", "oak_stairs")}
    for u in range(173, 212):
        assert any((v, u) in deck for v in range(78, 90)), f"the boardwalk has no deck at U{u}"


def test_the_water_runs_under_the_boardwalk(built):
    """The deck is a course ABOVE the lake, on piles, so it is one lake with a bridge over it.
    Laid at the water's own course it would have cut the lake in two."""
    deck = [(p, n) for p, n in built.items()
            if p[1] == GROUND_Y + 1 and n in ("oak_planks", "spruce_planks")]
    under = [built.get((p[0], GROUND_Y, p[2])) for p, _n in deck]
    assert under.count("water") >= 40, "the boardwalk never actually crosses open water"
    piles = [p for p, n in built.items() if n == "spruce_log"]
    assert piles, "a deck over water with no piles under it"


def test_every_stair_leans_the_way_it_climbs(design):
    """A STAIR'S TALL SIDE IS ITS `facing`, and our renderer draws a backwards stair identically
    to a right one - so this is asserted, never eyeballed.

      * the terrace's approach is a flight of TWO, because the deck stands two courses up:
        V25 at Y203 and V26 at Y204, both climbing EAST onto the deck (+V is +x, east)
      * the flights down the bank climb WEST, back toward the higher level: V32 at Y205 off the
        walk onto the deck, V35 at Y203 off the quay onto the walk
      * the boardwalk's two landings climb inward off the bank: SOUTH at U173, NORTH at U211
    """
    m = design.model
    ox, oy, oz = design.origin
    want = {}
    for u in range(180, 205):
        want[(25, GROUND_Y + 1, u)] = "east"
        want[(26, GROUND_Y + 2, u)] = "east"
    for u in (185, 192, 199):
        for du in (-1, 0, 1):
            want[(32, GROUND_Y + 3, u + du)] = "west"
            want[(35, GROUND_Y + 1, u + du)] = "west"
    for v in range(84, 87):
        want[(v, GROUND_Y + 1, 173)] = "south"
        want[(v, GROUND_Y + 1, 211)] = "north"
    seen = 0
    for (v, y, u), facing in want.items():
        x, z = 97500 + v - ox, 80300 + u - oz
        i = m.ids[y - oy, z, x]
        name = m.names[i].split(":")[-1]
        if "stairs" not in name:
            continue
        props = m.props_at(x, y - oy, z)
        assert props.get("facing") == facing, \
            f"stair at V{v} U{u} faces {props.get('facing')}, should climb {facing}"
        assert props.get("half") == "bottom"
        seen += 1
    assert seen >= 12, f"only {seen} of the expected stairs are there at all"


def test_the_flights_are_the_only_gaps_in_the_balustrade(built):
    """A balustrade with a gap nobody can use is a hole; a flight with a wall across it is a
    balcony. The three gaps in the rail at V31 are exactly where the three flights stand."""
    rail = {p[2] - 80300 for p, n in built.items()
            if n == "stone_brick_wall" and p[0] - 97500 == 31}
    flight = {p[2] - 80300 for p, n in built.items()
              if "stairs" in n and p[0] - 97500 == 32}
    assert flight, "no flight down from the terrace at all"
    assert rail, "no balustrade along the terrace's water edge at all"
    assert not (rail & flight), "the balustrade is drawn across a flight"


def test_the_terrace_is_a_stepped_bank_and_not_a_slab(built):
    """Three levels, each a course lower than the last, or it is a path beside a lake rather than
    somewhere a crowd stands and looks. Measured as the height a walker's feet are at."""
    # the PAVING, not what stands on it: a bench and a lamp plinth sit a course above the deck
    paving = {"stone_bricks", "smooth_stone", "cracked_stone_bricks", "polished_blackstone_bricks"}

    def top(v):
        ys = [p[1] for p, n in built.items()
              if p[0] - 97500 == v and 182 <= p[2] - 80300 <= 202 and n in paving]
        return max(ys) if ys else None
    deck, walk, quay = top(29), top(33), top(36)
    assert (deck, walk, quay) == (GROUND_Y + 2, GROUND_Y + 1, GROUND_Y), \
        f"the bank does not step: deck {deck}, walk {walk}, quay {quay}"


def test_the_terrace_holds_a_crowd_and_faces_the_water(built):
    """A bench is not a congregation point. Standing room is counted, and every seat looks at the
    lake - a stair's TALL side is its backrest, so a west-facing bench seats you facing east."""
    from mcbuild import scan as _s
    stand = {(p[0] - 97500, p[2] - 80300) for p, n in built.items()
             if 27 <= p[0] - 97500 <= 37 and "stairs" not in n and n != "stone_brick_wall"}
    assert len(stand) >= 180, f"only {len(stand)} columns of terrace to stand on"
    seats = [p for p, n in built.items() if n == "oak_stairs" and p[0] - 97500 < 60]
    assert len(seats) >= 8, f"only {len(seats)} seats on the terrace"


def test_nothing_expensive_and_nothing_this_server_cannot_spend(wet):
    """Rule 16 - dirt and its whole family are CURRENCY here, which is why the park's lawn is
    moss - and the cost tiers, which a 5,000-block landscape can blow through without noticing."""
    from mcbuild import blocks, palette
    names = sorted(set(wet.values()))
    currency = [n for n in names if not blocks.spendable(n)]
    expensive = [n for n in names if palette.tier(n) == "expensive"]
    assert currency == [], f"currency blocks: {currency}"
    assert expensive == [], f"expensive blocks: {expensive}"


def test_the_shore_is_a_gradient_and_not_a_line(wet):
    """A hard edge between lawn and water is a pond liner. The shingle thins with distance from
    the water, so at least three materials share the strand and none of them is a solid ring."""
    strand = [n for p, n in wet.items() if p[1] == GROUND_Y
              and n in ("stone", "andesite", "mossy_stone_bricks")]
    kinds = {n for n in strand}
    assert len(kinds) == 3, f"the strand is drawn in {sorted(kinds)}"
    for n in kinds:
        assert strand.count(n) >= 30, f"only {strand.count(n)} cells of {n} in the shore"


def test_the_lake_has_all_three_depths(wet):
    """Shallows AND depth, which is the brief. A basin of one depth is a swimming pool."""
    col = {}
    for p, n in wet.items():
        if n == "water":
            col[(p[0], p[2])] = col.get((p[0], p[2]), 0) + 1
    hist = {d: sum(1 for c in col.values() if c == d) for d in (1, 2, 3)}
    assert all(hist[d] >= 9 for d in (1, 2, 3)), f"depth histogram {hist}"
    assert max(col.values()) == 3
