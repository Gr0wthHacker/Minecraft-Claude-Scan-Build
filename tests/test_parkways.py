"""THE GROUND LAYER IS ONLY AS GOOD AS THE LOTS IT LEAVES.

The first version of this grid divided every land into four avenues every 42 U with one mid-block
walk at one depth. Every check the pipeline had passed it: `problems: 0`, one connected component,
zero currency, zero expensive, no cobblestone. And measured with `tools/park_lots.py` its largest
lot was 34 x 32, against a park that owes a 111 x 71 Mine Coaster, a 93 x 72 Prism Ascent and a
68 x 71 Carousel Court. TWENTY OF ITS TWENTY-FOUR BUILDS HAD NOWHERE TO STAND.

Nothing could see it, and the reason generalises: every check in this pipeline is PER CELL - is
this block state legal, is it in 1.19, is it spendable, does it have support - and the failure is
a property of the SHAPE OF THE HOLES BETWEEN the cells. So the lot rule is the test this file
exists for, and the rest of it pins the things that were quietly eating those holes.
"""
from collections import Counter

import numpy as np
import pytest

from mcbuild import blocks, palette
from mcbuild.gen import parkways
from tools.park_lots import (NOT_A_LOT, PLACEMENT, RETIRED, load_modules, params_from_config,
                             surface, verify)

#: THE RESIDUALS, AS MEASURED, AND THEY ARE A CEILING RATHER THAN A SNAPSHOT. A build may improve
#: and this test still passes; it may not get worse. Pinning the exact number would be the trap
#: this repo has already fallen into twice - an assertion on a snapshot of remaining work fails
#: the moment the work starts going right.
#:
#: All four are programme conflicts rather than grid faults, and all four have the same character:
#: a module declaring a footprint the 200-deep envelope cannot give it once its own streets are
#: drawn. See PARK_GRID_PLAN.md for the arithmetic and the recommended re-spec of each.
#: EMPTY, AND IT IS MEANT TO BE. All four shortfalls were programme conflicts rather than grid
#: faults, and each was resolved in `park_final.world.json` by measurement:
#:   Mining Square  56 -> 41 deep, behind a new V77-79 walk. Frontier B then reads 53 + 3 + 41 =
#:                  exactly 97, and its front door addresses a street instead of Boomtown's back.
#:   Works Yard     18 -> 13 deep. The service band IS 18 and the lane takes three of it, so a
#:   Service Gallery              lane inside the band and an 18-deep yard behind it cannot both
#:                  exist; both gain width, which the band has.
#:   Signal Heron   52x45 -> 20x38. It reached four columns into the Midway and overlapped
#:                  Arrival Court by 152 cells. THE BIRD MEASURES 14 x 32.
#: An entry here is a debt, so it should be added only with the arithmetic that justifies it.
KNOWN_SHORT: dict = {}


@pytest.fixture(scope="module")
def params():
    return params_from_config()


@pytest.fixture(scope="module")
def ground(params):
    """(lawn mask [V, U], canvas). Built once - it is 131k blocks and about ten seconds."""
    return surface(params)


# --------------------------------------------------------------------------- THE LOT RULE

def test_every_build_the_park_owes_has_a_lot_that_holds_it(params):
    """The one that matters. Every module in `park_final.world.json` that needs ground is placed
    on lawn at a stated corner, and every cell of its declared footprint is open lawn."""
    rows = verify(params, load_modules())
    assert rows, "no placements verified - the tool or the config moved"
    for name, _v, _u, dv, du, note in rows:
        if name in KNOWN_SHORT:
            continue
        assert note == "fits", f"{name} ({dv}x{du}) does not fit its lot: {note}"


def test_the_known_shortfalls_are_a_ceiling_and_never_get_worse(params):
    """Four modules declare more than the envelope can give once its streets are drawn. Each is
    recorded with the shortfall it had when it was measured; this fails if any grows."""
    rows = {r[0]: r for r in verify(params, load_modules())}
    for name, (max_deep, max_wide) in KNOWN_SHORT.items():
        _n, _v, _u, dv, du, note = rows[name]
        deep = int(note.split(" DEEP")[0].split()[-1]) if "DEEP short" in note else 0
        wide = int(note.split(" WIDE")[0].split()[-1]) if "WIDE short" in note else 0
        assert deep <= max_deep and wide <= max_wide, \
            f"{name} got worse: {note} (recorded ceiling {max_deep} deep / {max_wide} wide)"


def test_every_module_is_either_placed_or_declared_not_to_need_ground():
    """A module that is neither placed nor named as grid-provided is one nobody noticed.

    THREE WAYS TO BE ACCOUNTED FOR, and they are kept apart because they mean different things: it
    has a lot, the grid already draws it, or it is RETIRED with a reason written beside it. Filing
    a retirement under `NOT_A_LOT` would claim a building exists somewhere it does not.
    """
    names = {m["name"] for m in load_modules()}
    unaccounted = names - set(PLACEMENT) - NOT_A_LOT - RETIRED
    assert not unaccounted, f"no lot and no reason: {sorted(unaccounted)}"


def test_the_biggest_lot_in_each_land_is_bigger_than_a_car_park_tile(ground, params):
    """THE REGRESSION GUARD ON THE WHOLE EXERCISE. The uniform grid's largest lot anywhere was
    34 x 32; a lot that size can hold a snack window and nothing else. Any future schedule that
    goes back to dividing a land by a ruler fails here rather than four steps downstream."""
    from tools.park_lots import measure
    rows = measure(params)
    biggest = max(r["rect_area"] for r in rows)
    assert biggest >= 111 * 71, \
        f"largest lot is only {biggest} cells - the Mine Coaster alone needs {111 * 71}"


# --------------------------------------------------------------------------- LAMPS

MASTS = {"lightning_rod", "dark_oak_fence", "polished_blackstone_brick_wall"}


def _mast_cells(c):
    names = {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(c.palette)}
    ids = [i for i, n in names.items() if n in MASTS]
    zs, xs = np.nonzero(np.isin(c.ids[3], ids))
    return [(int(x), int(z)) for x, z in zip(xs, zs)]


def test_a_lamp_stands_on_one_line_and_never_wanders_across_it(ground, params):
    """Jack, on the shipped version: "still lots of issues with lamp placements, awkward, weird."

    Counted off the block list the masts stood on FOURTEEN different V lines, with thirteen piled
    on one of them and ten on another - the nudge that walks a lamp off paving was moving it
    ACROSS its own verge and stacking it wherever it first found grass. A street lamp sits on one
    line per verge; that is the whole of what makes a row of them read as a row.
    """
    lawn, c = ground
    sv, sh = params["spine_v"], params["spine_half"]
    pv, ph = params["promenade_v"], params["promenade_half"]
    lines = {sv - sh - 2, sv + sh + 2, pv - ph - 2, pv + ph + 2}
    # ONE SOURCE. This was a bare `range(start, service_v, lamp_every)`, which was right only
    # while an avenue was spaced by a plain step - the moment the runs were cut at their own
    # crossings it called every correctly-placed avenue lamp a stray.
    lines |= set(parkways.avenue_stations(params))
    # ...and the cross walks, which are streets and lit like streets - they were completely dark,
    # and they are the entire street access for three attractions.
    for land in params["lands"]:
        for wk in land.get("walks") or ():
            wv, wh = int(wk["v"]), int(wk.get("half", 1))
            lines |= {wv - wh - 1, wv + wh + 1}
    off = sorted({v for v, _ in _mast_cells(c)} - lines)
    assert not off, f"lamps standing off every named verge and rhythm line: {off}"


def test_the_back_promenade_is_actually_lit(ground, params):
    """It was not. Its two verge lines carried ZERO masts over a 600-block walked route, while
    `lamps_refused_on_paving` reported 0 - so something was swallowing them silently, which is
    this project's most-repeated failure shape."""
    _lawn, c = ground
    pv, ph = params["promenade_v"], params["promenade_half"]
    per = Counter(v for v, _ in _mast_cells(c))
    for line in (pv - ph - 2, pv + ph + 2):
        assert per[line] >= 8, f"promenade verge V{line} carries {per[line]} lamps"


def test_no_lamp_stands_on_paving_or_inside_reserved_ground(ground, params):
    """A LAMP STANDS ON LAWN. Jack: "several areas have lamp posts on walk ways and in weird
    places." A mast's own footing replaces the lawn under it, so this is asserted against the
    cells AROUND it: a post in the middle of a path has paving on every side."""
    lawn, c = ground
    for v, u in _mast_cells(c):
        around = [lawn[v + dv, u + du]
                  for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if 0 <= v + dv < lawn.shape[0] and 0 <= u + du < lawn.shape[1]]
        assert any(around), f"lamp at V{v} U{u} has paving on every side - it is IN a path"
    for f in (params.get("feature_lots") or []):
        inside = [(v, u) for v, u in _mast_cells(c)
                  if f["v0"] <= v <= f["v1"] and f["u0"] <= u <= f["u1"]]
        assert not inside, f"lamps inside the reserved {f['name']}: {inside}"


def test_two_lamps_never_bunch(ground):
    """Two nudged off the same plaza from opposite verges came out one and two blocks apart -
    a pair of posts side by side, which reads worse than the gap they were avoiding."""
    pts = _mast_cells(ground[1])
    for i, (a, b) in enumerate(pts):
        for c2, d in pts[i + 1:]:
            assert abs(a - c2) + abs(b - d) >= 8, f"lamps bunched at V{a} U{b} and V{c2} U{d}"


# --------------------------------------------------------------------------- THE PROGRAMME

def test_the_protected_rim_reserve_carries_nothing(ground, params):
    """V171-199 is protected rim, terrain and void-view reserve. The rim EDGE at V170 is the one
    course allowed to be dressed, and everything past it must stay untouched ground."""
    lawn, _c = ground
    rim = params["rim_v"]
    assert lawn[rim + 1:, :].all(), \
        f"{int((~lawn[rim + 1:, :]).sum())} paved cells inside the rim reserve V{rim + 1}-199"


def test_the_lot_bands_are_lawn_and_the_street_bands_are_paved(ground, params):
    """The depth programme, asserted at a U where no avenue crosses. A band that has quietly
    slid a course is invisible in a render and fatal to a placement table."""
    lawn, _c = ground
    u = 30                                       # Frontier col A, clear of every avenue
    sv, sh = params["spine_v"], params["spine_half"]
    assert not lawn[sv, u] and not lawn[sv - sh, u] and not lawn[sv + sh, u], "spine missing"
    assert lawn[sv + sh + 1, u], "no verge behind the spine"
    for v in range(24, 120):
        assert lawn[v, u], f"public floor lot band broken at V{v}"


def test_the_promenade_stops_over_the_three_columns_with_no_slack(ground, params):
    """WHERE THERE IS NOWHERE TO SWERVE TO, THE PROMENADE STOPS. The Mine Coaster is 111 deep,
    the Carousel over the Sky Lift 130, the Prism Array over the Resonance Vault 109 - each one
    deeper than any promenade can clear. Drawing a street through them is what put "buildings on
    top of each other" in the park in the first place."""
    lawn, _c = ground
    pv = params["promenade_v"]
    for u0, u1 in params["promenade_gaps"]:
        mid = (u0 + u1) // 2
        assert lawn[pv, mid], f"promenade drawn at V{pv} U{mid}, inside a declared gap"
    assert not lawn[pv, 30], "promenade missing where it should run"


def test_a_reach_separates_the_lands_it_joins(ground, params):
    """Without the threshold handoffs the Frontier's coaster column, the whole Claim Line reach
    and the Midway's arrival column measured as ONE 20,097-cell lot spanning two territories:
    nothing at all crossed a reach except the spine, so two lands shared one lot."""
    lawn, _c = ground
    for th in params["thresholds"]:
        u = th["at"]
        assert not lawn[60, u], f"threshold at U{u} is not laid"


# --------------------------------------------------------------------------- GEOMETRY

def test_a_round_plaza_gives_its_corners_back_to_the_lawn(ground, params):
    """A square lot around a radial thing wastes its four corners. `plaza_shape: round` is not a
    decoration - the corners it does not pave are lot ground, and this is what says it is a disc
    rather than a square with a curved pattern painted on it."""
    lawn, _c = ground
    sv, hh = params["spine_v"], params["plaza_half"]
    u = params["lands"][0]["avenues"][0]["at"]
    assert not lawn[sv, u], "plaza centre is not paved"
    assert lawn[sv - hh + 1, u - hh + 1], "the plaza's corner is paved - it is a square"


def test_the_circus_is_a_RING_with_a_green_in_it(ground, params):
    """A roundabout is a ring road round an island; a disc is a plaza. The difference is that the
    middle is RESERVED - which is also what stops a path, a lamp or a bench landing on it."""
    lawn, _c = ground
    rb = params["roundabouts"][0]
    cv, cu, r, ring = rb["v"], rb["u"], rb["r"], rb["ring"]
    assert lawn[cv, cu], "the circus island is paved - it is a disc, not a roundabout"
    assert lawn[cv, cu + r - ring - 2], "island not clear out to its own radius"
    for du in (r - ring + 1, -(r - ring + 1)):
        assert not lawn[cv, cu + du], f"the ring road is missing at U{cu + du}"
    # ...and the outside is measured ACROSS the promenade, not along it: the circus stands ON the
    # back promenade, so due east and west of it is the promenade itself and always paved.
    assert lawn[cv - r - 2, cu] and lawn[cv + r + 2, cu], "the ring road has no outside"


def test_the_balloon_sits_wholly_on_the_circus_island(params):
    """A SET PIECE GETS A LOT, IT DOES NOT GET WHAT IS LEFT. Jack: "the air balloon is in the dead
    center of one of the walkways ... same with the bird" - both were placed by a hand-typed
    offset that nothing checked against the paths."""
    from mcbuild.gen import balloon
    m = balloon.build_balloon({})
    occ = (m.ids > 0).any(axis=0)                       # [z, x]
    zs, xs = np.nonzero(occ)
    rb = params["roundabouts"][0]
    d = np.hypot(115 + xs - rb["v"], 225 + zs - rb["u"])   # the config's own offset
    assert d.max() < rb["r"] - rb["ring"] - 0.5, \
        f"balloon reaches {d.max():.1f} from the circus centre, past its island"


def test_the_heron_sits_wholly_inside_its_own_garden(params):
    from mcbuild.gen import heron
    m = heron.build_heron({"variant": "heron", "at": [0, 0, 0], "scale": 1.0, "seed": 0})
    occ = (m.ids > 0).any(axis=0)
    zs, xs = np.nonzero(occ)
    v0, v1, u0, u1 = 26 + xs.min(), 26 + xs.max(), 176 + zs.min(), 176 + zs.max()
    g = [f for f in params["feature_lots"] if f["name"] == "heron garden"][0]
    assert g["v0"] <= v0 and v1 <= g["v1"] and g["u0"] <= u0 and u1 <= g["u1"], \
        f"heron V{v0}-{v1} U{u0}-{u1} is not inside {g}"


# --------------------------------------------------------------------------- MATERIALS

def test_nothing_in_the_ground_layer_is_currency_expensive_or_cobblestone(ground):
    """`grass_block` and every form of dirt are CURRENCY on this server, which is why the lawn is
    moss; cobblestone was 17.7% of an earlier version and Jack rejected it outright."""
    _lawn, c = ground
    names = {e.value["Name"].value.split(":")[-1] for e in c.palette[1:]}
    assert not [n for n in names if not blocks.spendable(n)], "currency in the ground layer"
    assert not [n for n in names if "cobble" in n], "cobblestone is the park's banned block"
    assert not [n for n in names if palette.tier(n) == "expensive"], "expensive tier"
    assert not [n for n in names if not blocks.available(n)], "not placeable on the 1.19 server"


def test_the_paving_is_ONE_CONNECTED_WALK(ground, params):
    """THE COMPONENT COUNT ON THE MODEL SAYS NOTHING - the lawn covers all 120,000 cells, so any
    ground layer is trivially one piece. The question is whether the PAVING is one walk.

    Asked properly, it was not: the Prismworks cross walk came out as 153 cells reaching NEITHER
    avenue - a 51-block walkway between the Prism Array and the Resonance Vault with no way off
    it - because a column's usable width stops one cell short of the avenue at its lamp line, and
    the walk was drawn to the column rather than to the streets it joins.
    """
    from collections import deque
    lawn, _c = ground
    pav = ~lawn
    pav[params["rim_v"]:, :] = False        # the rim edge course is a dressed edge, not a walk
    sx, sz = pav.shape
    seen = np.zeros_like(pav)
    comps = []
    for x0 in range(sx):
        for z0 in range(sz):
            if pav[x0, z0] and not seen[x0, z0]:
                q, n = deque([(x0, z0)]), 0
                seen[x0, z0] = True
                while q:
                    x, z = q.popleft()
                    n += 1
                    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        a, b = x + dx, z + dz
                        if 0 <= a < sx and 0 <= b < sz and pav[a, b] and not seen[a, b]:
                            seen[a, b] = True
                            q.append((a, b))
                comps.append(n)
    # a lamp's own footing is a single non-lawn cell standing on the verge, and is not a walk
    strays = [n for n in comps if n > 4]
    assert len(strays) == 1, f"the paved walk is in {len(strays)} pieces: {sorted(strays)[::-1]}"


def test_the_lawn_covers_the_whole_envelope(ground, params):
    """No void anywhere, and a path only reads as a path if there is something it is NOT."""
    _lawn, c = ground
    assert (c.ids[0] > 0).all(), "there is bare void in the ground layer"


def _masts(c) -> set:
    """Every lamp shaft, as (V, U). Read at y3 - the one course every land's lamp has a mast in.

    NEVER FROM A PICTURE. `render3d` draws a lightning rod, a fence, a wall and iron bars all as
    full cubes, and it has hidden six separate faults on this park already.
    """
    names = {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(c.palette)}
    ids = {i for i, n in names.items()
           if n in {"lightning_rod", "dark_oak_fence", "polished_blackstone_brick_wall"}}
    zs, xs = np.nonzero(np.isin(c.ids[3], list(ids)))
    return {(int(x), int(z)) for x, z in zip(xs, zs)}


def _crossings(params):
    """(centre V, street half-width, U, axis) for every meeting of two streets in the park.

    `axis` is the direction the CROSSING street runs, which decides the symmetry that applies. An
    avenue and a threshold both run along V, so the mirror that must hold at their meetings is the
    one across the street they meet - and where that street stops on one side, along it as well.
    """
    out = []
    for land in params["lands"]:
        for av in land.get("avenues") or ():
            for cv, half in ((params["spine_v"], params["spine_half"]),
                             (params["promenade_v"], params["promenade_half"])):
                out.append((cv, half, int(av["at"])))
    # A THRESHOLD IS A STREET AND THE JUNCTION PASS COULD NOT SEE ONE - it walks the `avenues`
    # list and a threshold is not in it, so all four handoffs were lit by whatever the runs left.
    for th in (params.get("thresholds") or ()):
        for cv, half in ((params["spine_v"], params["spine_half"]),
                         (params["promenade_v"], params["promenade_half"])):
            out.append((cv, half, int(th["at"])))
    return out


def test_a_crossing_is_lit_four_square_or_not_at_all(ground, params):
    """Jack: "lots of lamp placements around intersections are still weird, non symmetric."

    Measured against the build he was looking at, EVERY crossing in the park was asymmetric and
    five of the six avenue/spine junctions carried no lamp at all. The cause is not tuning: a
    rhythm walked down a line as `(z + phase) % every == 0` cannot know a crossing is there, so a
    junction gets nought, one, two or four lamps at whatever offset the counter happens to be at -
    and one phase serves six hundred blocks and twelve junctions at once.

    A crossing is lit BY THE CROSSING now: four lamps where the two streets' own verge lines meet,
    pushed out by one offset shared by all four. This asserts the property that buys - four, or
    none, and mirrored about both axes.
    """
    _lawn, c = ground
    pts = _masts(c)
    for cv, half, u in _crossings(params):
        near = sorted((v - cv, z - u) for v, z in pts
                      if abs(z - u) <= 14 and abs(v - cv) <= half + 3)
        # 4 at a crossing, 2 at a T where the street stops - and 0 where neither will stand.
        assert len(near) in (0, 2, 4), f"crossing V{cv}/U{u} has {len(near)} lamps"
        # A T HAS ONE AXIS AND A CROSSING HAS TWO, and which axis a T keeps depends on which way
        # the street that stops was running: the promenade's Ts stop along U and keep the mirror
        # across it, a threshold leaves the spine southward and keeps the mirror along it. So the
        # rule is that AT LEAST ONE mirror holds, and a full crossing holds both.
        across = near == sorted((-dv, du) for dv, du in near)
        along = near == sorted((dv, -du) for dv, du in near)
        assert across or along, f"crossing V{cv}/U{u} is mirrored on neither axis: {near}"
        if len(near) == 4:
            assert across and along,                 f"crossing V{cv}/U{u} is a full crossing but not mirrored both ways: {near}"


def test_every_crossing_the_street_reaches_actually_gets_its_four(ground, params):
    """The rule above is satisfied by a park with no junction lamps anywhere, which is exactly the
    state it was written to fix. This pins that every crossing the crossing street actually
    reaches is really lit.

    A crossing where the street STOPS is excluded, and that is not a let-off: the promenade dies
    at three ride columns, and Frontier's second avenue meets it four blocks before the first of
    them. Four corners there would stand past the end of the promenade on the Mine Coaster's own
    ground - which is what they did, and it cost the largest lot in the park fourteen of depth.
    """
    _lawn, c = ground
    pts = _masts(c)
    gaps = params.get("promenade_gaps") or []
    prom_v, prom_h = params["promenade_v"], params["promenade_half"]

    def open_sides(cv, half, u):
        if cv != prom_v:
            return 2                         # the spine runs the whole 600
        return sum(not any(a <= uu <= b for a, b in gaps)
                   for uu in (u - half - 2, u + half + 2))

    ths = {int(th["at"]) for th in (params.get("thresholds") or ())}
    unlit = [(cv, u, open_sides(cv, half, u)) for cv, half, u in _crossings(params)
             # a threshold meets the SPINE on one verge only - it leaves the spine rather than
             # crossing it, so two masts is its complete answer and there is no far quadrant
             if len([1 for v, z in pts if abs(z - u) <= 14 and abs(v - cv) <= half + 3])
             != (2 if u in ths and cv == params["spine_v"] else 2 * open_sides(cv, half, u))]
    assert not unlit, f"crossings the street reaches but nothing lights: {unlit}"


def test_the_two_verges_of_a_street_carry_the_same_lamps(ground, params):
    """A street read walking down it is symmetric ACROSS, and that is the symmetry you actually
    see. Both verges are driven from one run, so their U positions must be identical."""
    _lawn, c = ground
    pts = _masts(c)
    # A THRESHOLD IS THE ONE THING THAT BREAKS THIS, AND LEGITIMATELY. It leaves the spine at
    # the spine's own centre line and runs south to the service lane, so it meets ONE verge and
    # there is no northern quadrant to mirror. Its columns are excluded and nothing else is.
    # A SPUR IS ON ONE SIDE OF ITS STREET, so the two verges legitimately differ at its column:
    # the spine's east verge is paved there and its west verge is not, and the run on the paved
    # side steps aside. Excluded exactly like a threshold, and for the same reason.
    ths = {int(th["at"]) for th in (params.get("thresholds") or [])}
    ths |= {int(sp["u"]) for sp in (params.get("spurs") or [])}
    for cv, half in ((params["spine_v"], params["spine_half"]),
                     (params["promenade_v"], params["promenade_half"])):
        def side(sign):
            return sorted(z for v, z in pts if v == cv + sign * (half + 2)
                          and not any(abs(z - t) <= half + 26 for t in ths))
        west, east = side(-1), side(1)
        assert west == east, (f"the verges of the street at V{cv} do not match: "
                              f"{len(west)} west, {len(east)} east")


def test_no_lamp_stands_off_a_verge_line(ground, params):
    """Six masts once stood on V113 and V115, two lines that exist nowhere else in the park -
    avenue posts NUDGED off their own rhythm by a junction lamp four blocks away in the same
    column. A run drops rather than nudges near a crossing; this is what says so."""
    _lawn, c = ground
    lines = {params["spine_v"] - params["spine_half"] - 2,
             params["spine_v"] + params["spine_half"] + 2,
             params["promenade_v"] - params["promenade_half"] - 2,
             params["promenade_v"] + params["promenade_half"] + 2}
    # ...plus the avenue rhythm's own depths, which are a step of lamp_every from its start
    lines |= set(parkways.avenue_stations(params))   # ONE SOURCE: the build's own arithmetic
    # ...and the cross walks, which are streets and lit like streets - they were completely dark,
    # and they are the entire street access for three attractions.
    for land in params["lands"]:
        for wk in land.get("walks") or ():
            wv, wh = int(wk["v"]), int(wk.get("half", 1))
            lines |= {wv - wh - 1, wv + wh + 1}
    off = sorted({v for v, _z in _masts(c)} - lines)
    assert not off, f"masts standing off every verge line: V{off}"
