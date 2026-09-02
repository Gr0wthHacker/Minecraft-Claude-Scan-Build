"""What the Frontier's six buildings PROMISE, asserted rather than eyeballed.

Every test here pins a CONTRACT and not a block count. A snapshot test on a design whose whole
nature is remaining work fails the day the work starts - this repo has shipped that mistake twice
(`assert reclaimed >= 70` on the deck soffit, and the town tests that regenerated against a fresh
capture and found their own door frames already built). What is pinned is the geometry a builder
and a guest both depend on: nothing outside the lot, one piece, whole door frames, risers that
lean the way they climb, signs on walls that exist, and a palette this server can actually buy.

Three of these can only be settled by a test, because `render3d` draws them identically either
way: a stair's facing, a trapdoor's facing, and whether a pane is connected along its wall.
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from mcbuild import audit, blocks, morph, nbt, palette
from mcbuild.gen import frontier_builds as fb

#: The six lots, exactly as `tools/park_lots.PLACEMENT` measures them and as the configs declare.
LOTS = {
    "trailhead": ((45, 39), (24, 0), {"entry_u": 19, "seed": 11}),
    "porch": ((51, 40), (69, 0), {"entry_v": 17, "seed": 23}),
    "boomtown": ((53, 46), (24, 47), {"entry_u": 23, "seed": 37}),
    "square": ((41, 46), (80, 47), {"seed": 51}),
    "assay": ((20, 46), (130, 47), {"entry_u": 23, "seed": 67}),
    "works": ((13, 36), (157, 125), {"seed": 83}),
}

#: Anything that is not a full cube. The corpus measures outside builds at ~17% of these and this
#: repo at a seventh of their rate; the floor below is what stops that regressing.
DETAIL = ("_stairs", "_slab", "_fence", "_trapdoor", "_wall", "_pane", "_door", "_sign",
          "_gate", "iron_bars", "iron_chain", "lantern", "rail")

_STEP = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}


def build(kind: str):
    lot, at, extra = LOTS[kind]
    return fb.build({"kind": kind, "lot": list(lot), "at": list(at), **extra})


@pytest.fixture(scope="module")
def built():
    return {k: build(k) for k in LOTS}


def _cells(c):
    """{(v, y, u): (name, props)} for every solid cell of a canvas."""
    m = c.to_model()
    names = [n.split(":")[-1] for n in m.names]
    props = [nbt.state_props(e) for e in m.palette]
    out = {}
    for y, z, x in zip(*m.solid().nonzero()):
        i = int(m.ids[y, z, x])
        out[(int(x), int(y), int(z))] = (names[i], props[i])
    return out


def _counts(c) -> Counter:
    return Counter(n for n, _ in _cells(c).values())


# ---------------------------------------------------------------- the boundary, and one piece


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_not_one_cell_leaves_its_lot(built, kind):
    """A cell over the line is CROPPED at placement and simply disappears, so a part sitting past
    the boundary is not a collision anybody can see - it is a missing gable that audits clean.
    This park has already lost the Mine Coaster's 71st column to one lamp two cells out."""
    c = built[kind]
    (dv, du), _at, _ = LOTS[kind]
    assert (c.sx, c.sz) == (dv, du)
    assert c.meta["refused"] == 0, (
        f"{kind} tried to place {c.meta['refused']} cells outside its {dv}x{du} lot")


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_each_build_is_one_connected_piece(built, kind):
    """6-connected, on its own. A staircase of single blocks touches its neighbours only at a
    diagonal - the ear-tip failure - and it is invisible in every render."""
    m = built[kind].to_model()
    _lab, sizes = morph.components(m.solid(), conn=6)
    assert len(sizes) == 1, f"{kind} is {len(sizes)} pieces: {sorted(sizes, reverse=True)[:6]}"


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_the_audit_is_clean(built, kind):
    res = audit.audit(built[kind].to_model(), ground=False)
    assert not res.problems, [str(p) for p in res.problems[:8]]
    assert res.leaks == 0


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_nothing_is_built_below_the_lawn(built, kind):
    """Canvas y=0 is the first course above the ground layer's moss. Anything under it would be
    dug into a surface this design does not own."""
    ys = {y for (_v, y, _u) in _cells(built[kind])}
    assert min(ys) == 0


# ---------------------------------------------------------------- the openings


#: Mining Square has no door and needs none: its role is `path`, its openings are two arches and
#: a seven-wide flight, and a square with a doorway in it is a building.
DOORED = sorted(set(LOTS) - {"square"})


@pytest.mark.parametrize("kind", DOORED)
def test_every_opening_has_two_whole_jambs_and_a_lintel_between_their_tops(built, kind):
    """A hole punched in a wall reads as damage; a framed one reads as a door. The jambs run the
    opening's whole height and the lintel spans the opening ONLY - never the jambs - so the frame
    is legible as three parts."""
    c = built[kind]
    cells = _cells(c)
    doors = [d for d in c.meta["doors"] if d["kind"] == "door"]
    assert doors, f"{kind} has no framed opening at all"
    for d in doors:
        y0, y1 = d["y"]
        ly = d["lintel_y"]
        assert ly == y1 + 1, d
        for (jv, ju) in d["jambs"]:
            for y in range(y0, y1 + 1):
                assert (jv, y, ju) in cells, f"{kind}: jamb hole at {(jv, y, ju)} of {d}"
        # the lintel covers the opening, and every one of its cells lies strictly between the
        # jambs on the axis the wall runs along
        (ja, jb) = d["jambs"]
        for v in range(d["v"][0], d["v"][1] + 1):
            for u in range(d["u"][0], d["u"][1] + 1):
                assert (v, ly, u) in cells, f"{kind}: lintel hole at {(v, ly, u)} of {d}"
                if d["axis"] == "u":
                    assert min(ja[1], jb[1]) < u < max(ja[1], jb[1])
                else:
                    assert min(ja[0], jb[0]) < v < max(ja[0], jb[0])
        # ...and the opening is actually OPEN
        for v in range(d["v"][0], d["v"][1] + 1):
            for u in range(d["u"][0], d["u"][1] + 1):
                for y in range(y0, y1 + 1):
                    assert (v, y, u) not in cells, f"{kind}: {d} is bricked up at {(v, y, u)}"


@pytest.mark.parametrize("kind", DOORED)
def test_every_door_step_ascends_toward_its_door(built, kind):
    """A STAIR ASCENDING TOWARD D HAS facing=D - the convention this repo settled off Jack's own
    flight - and our renderer draws a backwards tread identically to a right one, so it is
    asserted here or it is never checked at all. A step built the other way round is a lip you
    trip on rather than a way in."""
    c = built[kind]
    cells = _cells(c)
    seen = 0
    for d in c.meta["doors"]:
        st = d.get("step")
        if not st:
            continue
        dv, du = _STEP[st["facing"]]
        for v in range(st["v"][0], st["v"][1] + 1):
            for u in range(st["u"][0], st["u"][1] + 1):
                got = cells.get((v, 0, u))
                if got is None:                       # the cell may belong to a neighbouring part
                    continue
                name, props = got
                if not name.endswith("_stairs"):
                    continue
                assert props.get("facing") == st["facing"], (kind, d)
                assert props.get("half") == "bottom"
                assert (v + dv, 0, u + du) in cells, (
                    f"{kind}: a step at {(v, u)} climbs toward nothing")
                seen += 1
    assert seen, f"{kind} has no door step at all"


# ---------------------------------------------------------------- the risers


def _wanted(roof, v, u) -> str | None:
    """Which way a tread at (v, u) of this roof must lean, from the roof's OWN idiom.

    THERE ARE THREE IDIOMS AND ONE GEOMETRIC RULE CANNOT SEPARATE THEM. A gable's two slopes face
    each other, a cap's four faces climb to its centre, a lean-to's all climb one way - and a
    purely local "the roof ahead is never lower than the roof behind" test flags a pediment and a
    false front, which are supposed to stand proud of the roof behind them. So each roof declares
    its own idiom as it is laid, and this reads it back."""
    if roof["style"] == "lean":
        return roof["up"]
    if roof["style"] == "rake":
        a = u if roof["axis"] == "u" else v
        if a == roof["apex"]:
            return None
        if roof["axis"] == "u":
            return "south" if a < roof["apex"] else "north"
        return "east" if a < roof["apex"] else "west"
    if roof["style"] == "gable":
        a = v if roof["axis"] == "v" else u
        if a == roof["mid"]:
            return None
        return roof["up"] if a < roof["mid"] else roof["dn"]
    dv, du = v - roof["cv"], u - roof["cu"]
    if roof.get("diagonal") and abs(du) > abs(dv):
        return "north" if du > 0 else "south"
    if not roof.get("diagonal") and not (v in roof["v"] or u in roof["u"]):
        return None
    if roof.get("diagonal") or v in roof["v"]:
        return "west" if dv > 0 else "east"
    return "north" if du > 0 else "south"


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_every_roof_tread_leans_the_way_its_own_roof_climbs(built, kind):
    """A stair's tall side is its `facing`, so a tread facing down its own slope is a roof laid
    backwards - and our renderer drew both identically until `subdivide` was written. Nothing but
    a test can see this, and it caught four reversed idioms the first time it was run: a cap, a
    conical tower roof, a knee brace and a board eave."""
    c = built[kind]
    cells = _cells(c)
    assert c.meta["roofs"], f"{kind} declares no roof"
    checked = 0
    for (v, y, u), (name, props) in cells.items():
        if name != fb.PAL["roof"] or props.get("half") != "bottom":
            continue
        # THE LAST DECLARATION OWNS THE CELL. Elements are laid in order and a later one is drawn
        # over an earlier one - a pediment over a gable eave, a water tower cap over a shop's -
        # so the roof that decides a tread is the one that put it there.
        owner = None
        for roof in c.meta["roofs"]:
            if (roof["v"][0] <= v <= roof["v"][1] and roof["u"][0] <= u <= roof["u"][1]
                    and roof["y0"] <= y <= roof["y1"]):
                owner = roof
        if owner is None:
            continue
        want = _wanted(owner, v, u)
        if want is None:
            continue
        assert props["facing"] == want, (
            f"{kind}: a {owner['style']} tread at {(v, y, u)} faces {props['facing']} "
            f"where its roof climbs {want}")
        checked += 1
    floor = 8 if kind == "square" else 30
    assert checked >= floor, f"{kind} has almost no roof to check ({checked})"


@pytest.mark.parametrize("kind", DOORED)
def test_every_eave_is_an_UPSIDE_DOWN_stair_leaning_back_over_its_wall(built, kind):
    """`half=top` is 27% of the outside corpus's stairs and was 0% of ours. An eave is the whole
    point of it: a stair tucked under an overhang, tall side toward the building it hangs off.
    Mining Square is exempt because it is a floor: it has no wall for a roof to overhang."""
    c = built[kind]
    cells = _cells(c)
    eaves = [(p, k) for k, (n, p) in cells.items()
             if n == fb.PAL["roof"] and p.get("half") == "top"]
    assert eaves, f"{kind} has no eave at all"
    for props, (v, y, u) in eaves:
        dv, du = _STEP[props["facing"]]
        assert (v + dv, y, u + du) in cells, (
            f"{kind}: an eave at {(v, y, u)} leans toward nothing")


# ---------------------------------------------------------------- the fittings


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_every_sign_hangs_on_a_wall_that_is_actually_there(built, kind):
    """A wall sign floating in air draws exactly like one on a wall. Four of the park's seven
    building kinds once shipped a sign on the one column of a wall that has an opening in it."""
    c = built[kind]
    cells = _cells(c)
    assert c.meta["signs"], f"{kind} names nothing"
    for s in c.meta["signs"]:
        v, y, u = s["at"]
        dv, du = _STEP[s["facing"]]
        assert (v - dv, y, u - du) in cells, f"{kind}: sign at {s['at']} hangs on nothing"
        assert all(len(line) <= fb.SIGN_WIDTH for line in s["lines"]), s


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_every_lantern_hangs_and_none_of_them_stands_on_a_post(built, kind):
    """THE GROUND LAYER ALREADY DRAWS EVERY LAMP IN THE PARK. A lantern here may only ever be a
    fitting under a beam, an arch head or a porch roof - a lantern on a post is a lamp post, and
    a second pass of street furniture on top of `Park Ways` is exactly the chaos this rebuild
    exists to undo."""
    for (v, y, u), (name, props) in _cells(built[kind]).items():
        if name != "lantern":
            continue
        assert props.get("hanging") == "true", f"{kind}: a standing lantern at {(v, y, u)}"


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_every_pane_and_grille_is_connected_along_its_own_wall(built, kind):
    """With every side false a pane renders as a lone post in the middle of an opening rather than
    as glazing. The campanile shipped that once."""
    for (v, y, u), (name, props) in _cells(built[kind]).items():
        if name not in ("glass_pane", "iron_bars"):
            continue
        on = [k for k in ("north", "south", "east", "west") if props.get(k) == "true"]
        assert len(on) == 2 and set(on) in ({"north", "south"}, {"east", "west"}), (
            f"{kind}: {name} at {(v, y, u)} is connected {on}")


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_every_trapdoor_faces_away_from_the_wall_it_hangs_on(built, kind):
    """A trapdoor's `facing` points OUT of the block it is attached to. Written the other way
    round it hangs off nothing, and our renderer draws it as a full cube either way."""
    cells = _cells(built[kind])
    for (v, y, u), (name, props) in cells.items():
        if not name.endswith("_trapdoor"):
            continue
        dv, du = _STEP[props["facing"]]
        assert (v - dv, y, u - du) in cells or (v, y - 1, u) in cells, (
            f"{kind}: trapdoor at {(v, y, u)} facing {props['facing']} attaches to nothing")


# ---------------------------------------------------------------- the materials


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_the_palette_is_legal_affordable_and_not_currency(built, kind):
    """Rules 2, 3, 4 and 16 in one place. DIRT AND GRASS ARE MONEY on this server, a block the
    26.2 client knows may not exist on a 1.19 one, and Jack's instruction on this park was
    "use deep slates etc as necessary, smooth stones, bricks" - no cobblestone anywhere."""
    for name in _counts(built[kind]):
        assert blocks.available(name), f"{kind}: {name} is not on the 1.19 server"
        assert blocks.spendable(name), f"{kind}: {name} is currency here"
        assert palette.tier(name) != "expensive", f"{kind}: {name} is expensive tier"
        assert "cobble" not in name, f"{kind}: {name}"
        assert "dirt" not in name and "grass" not in name and "podzol" not in name


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_the_palette_is_deep_and_the_detail_share_reads(built, kind):
    """Measured against the download corpus, outside architecture runs 37 block types and 17%
    detail blocks; ours ran 14 and 11%, and the Campanile ran 12 and 1.4%. These floors are what
    stops a wall being one material with a hat on."""
    cnt = _counts(built[kind])
    total = sum(cnt.values())
    detail = sum(k for n, k in cnt.items() if any(s in n for s in DETAIL))
    assert len(cnt) >= 15, f"{kind}: only {len(cnt)} block types"
    assert detail / total >= 0.10, f"{kind}: detail {100 * detail / total:.1f}%"


def test_the_value_ladder_is_measured_ACROSS_families():
    """Four notes in CLAUDE.md conclude this economy has no value contrast and every one of them
    searched inside ONE material family, where a ladder cannot exist by construction. Across
    families the rungs are real, and this is the ladder the six builds are drawn with."""
    ladder = [PAL_KEY for PAL_KEY in ("plinth", "roof_field", "timber", "base", "band")]
    lums = []
    for key in ladder:
        r, g, b = blocks.color(fb.PAL[key], "side")
        lums.append(0.2126 * r + 0.7152 * g + 0.0722 * b)
    plinth, roof, timber, base, band = lums
    assert timber - plinth >= 30, (plinth, timber)
    assert base - timber >= 30, (timber, base)
    assert band - base >= 30, (base, band)
    assert timber - roof >= 30, "the roof must read against the wall it sits on"
    fams = [fb.PAL[k].replace("polished_", "").replace("_bricks", "").replace("_planks", "")
            for k in ("plinth", "timber", "base", "band")]
    assert len(set(fams)) == 4, fams


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_the_lot_is_not_filled_solid(built, kind):
    """20-30% intentional openness reads better than a dense facade field. Mining Square is the
    one exception and it is exempt BY ROLE: its role in `park_final.world.json` is `path`, and a
    square with no floor is a lawn."""
    m = built[kind].to_model()
    cols = m.solid().any(axis=0)
    share = cols.sum() / (m.ids.shape[1] * m.ids.shape[2])
    ceiling = 0.95 if kind == "square" else 0.80
    assert share <= ceiling, f"{kind} covers {100 * share:.0f}% of its lot"


# ---------------------------------------------------------------- the programme


def test_boomtowns_street_runs_the_whole_lot_and_has_a_place_at_both_ends():
    """A street with a wall at one end is a cul-de-sac of false fronts. This one enters on the
    spine spur and comes out on the V77-79 cross walk the grid cut for it."""
    c = build("boomtown")
    cells = _cells(c)
    eu = LOTS["boomtown"][2]["entry_u"]
    for v in range(c.sx):
        assert (v, 0, eu) in cells, f"the boardwalk has a hole at V{v}"
        # ...and nothing stands in the walking lane below head height, except the east portal's
        # own head, which you walk under
        for y in (1, 2):
            if (v, y, eu) in cells:
                assert v >= c.sx - 7, f"the street is blocked at {(v, y, eu)}"


def test_mining_square_can_be_walked_onto_and_its_flight_climbs_the_right_way():
    """The square stands one course proud of the moss, so it needs a way up onto it on the face
    the V77-79 cross walk delivers a guest to - and a step built the other way round is a lip."""
    c = build("square")
    cells = _cells(c)
    assert c.meta["parts"]["approach_steps"] >= 7, "the flight is narrower than the decision zone"
    treads = [(k, p) for k, (n, p) in cells.items()
              if n == "stone_brick_stairs" and k[1] == 0 and k[0] == 1]
    assert treads
    for (v, y, u), props in treads:
        assert props["facing"] == "east" and props["half"] == "bottom"
        assert (v + 1, 0, u) in cells, "the flight climbs onto nothing"


def test_mining_square_keeps_the_coaster_queue_clear_of_the_ride_exit():
    """`PARK_FULL_BUILD_SPEC` F3 requires the queue entrance to be visibly separated from the
    exit. Two arches on one face is what the old module got wrong."""
    c = build("square")
    q = c.meta["parts"]["queue"]["span"]
    x = c.meta["parts"]["exit"]["span"]
    assert max(q) < min(x), (q, x)
    assert min(x) - max(q) >= 10, f"only {min(x) - max(q)} courses between queue and exit"


def test_the_trailhead_is_a_threshold_you_pass_through():
    """A gate with one opening is a facade. This one is entered from the spine on U19 and left on
    the east flank onto the avenue, so both ends of it are places."""
    c = build("trailhead")
    portal = c.meta["parts"]["portal"]
    exit_ = c.meta["parts"]["exit"]
    assert portal["axis"] == "u" and exit_["axis"] == "v"
    cells = _cells(c)
    eu = LOTS["trailhead"][2]["entry_u"]
    for v in range(portal["piers"][0][0], portal["piers"][1][1] + 1):
        for y in range(1, portal["clear_h"] + 1):
            assert (v, y, eu) not in cells, f"the portal is blocked at {(v, y, eu)}"


def test_the_works_yard_shows_a_guest_only_its_roofline():
    """It is the one lot on the promenade side of the rim, so what it may present to a guest is a
    chimney and a gantry over a wall - never a door."""
    c = build("works")
    assert c.meta["parts"]["chimney"]["top"] >= 9
    for d in c.meta["doors"]:
        assert d["u"][0] < c.sz - 1, "a works door may not open onto the rim face"


@pytest.mark.parametrize("kind", sorted(LOTS))
def test_every_build_records_the_contract_it_is_judged_on(built, kind):
    meta = built[kind].meta
    assert meta["kind"] == f"frontier_{kind}"
    assert meta["lot"] == list(LOTS[kind][0])
    assert meta["at"] == list(LOTS[kind][1])
    assert meta["land"] == "frontier"
    assert "lot" in meta["contract"] and "furniture" in meta["contract"]


def test_the_world_origin_is_the_lots_own_corner_on_the_park_anchor():
    """V0,U0 -> X97500,Z80300 and the course a guest stands on is Y203 - `tools/park_place.ANCHOR`
    and the shipped `Park Ways` sidecar, which puts its lawn at Y202."""
    for kind, ((_dv, _du), (v, u), _extra) in LOTS.items():
        c = build(kind)
        assert c.world_origin == (97500 + v, 203, 80300 + u), kind


def test_an_unknown_kind_and_a_lot_too_small_both_raise():
    """A generator that quietly builds nothing is this repo's most-repeated failure shape."""
    with pytest.raises(ValueError):
        fb.build({"kind": "saloon", "lot": [20, 20]})
    with pytest.raises(ValueError):
        fb.build({"kind": "works", "lot": [4, 4]})
    with pytest.raises(ValueError):
        fb.build({"kind": "works"})
