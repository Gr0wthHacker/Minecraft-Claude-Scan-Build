"""The BESPOKE sculptures on the isthmus - `gen/balloon.py`, `gen/wyrm.py` and
`gen/stegosaur.py`.

WHAT THIS FILE IS FOR. `tests/test_isthmus.py` already checks the causeway's own contracts over
whatever creatures `GAPS` happens to name, and it is right to be written that way. What it
cannot do is pin the pieces THEMSELVES: that a balloon still has a gap under its envelope, that
a wyrm's head still stands proud of its hood, that a stegosaur's crest is still four separate
paired plates and not one sail, that none of them has quietly grown a lamp inside its own coat.
Those are properties of the shapes, they are the properties that would be lost first to a
well-meant tweak, and every one of them is invisible to the audit, to the bill of materials and
to the component count.

EVERY ONE OF THESE EXISTS BECAUSE THE BUG HAD ALREADY SHIPPED ONCE:

    the wyrm's eye probe was a computed offset and landed on a course where the skull is two
      cells wide and - because of the half-cell centring - ASYMMETRIC about the midline. One
      side found a block, the other found air, and the piece shipped with ONE eye. Twice. No
      error, nothing in the audit, nothing in the count;
    the wyrm's first tail was a thin dark tip laid over a thicker sweep, and its last sphere
      came out at radius 0.62 as a ONE-CELL SECOND COMPONENT - the ear-tip failure, in a build
      that was clean everywhere else;
    the stegosaur shipped every plate as ALTERNATE COURSES WITH A HOLE BETWEEN THEM, because
      each course re-probed the back and found the course it had just laid - fifty four-cell
      strays, and a component count was the only thing that could see it. Then its feet came
      out as COMBS, because its legs stand at 0.150 of its length and `round()` is banker's
      rounding, so at length 30 every foot sphere was centred on x.5 and skipped alternate
      columns. Then its tail spikes detached at two lengths out of seven - and NOT at the one
      it was being looked at. Then, after a width fix that was perfect at length 34, two of its
      four plates fused at 30, 40 and 50. Every one of those is why the scale sweep is here;
    and its crest ALTERNATED, which is what the real animal does and which Jack rejected on
      sight - measured, it was the only asymmetry in the whole build.
"""
from collections import Counter

import numpy as np
import pytest

from mcbuild import blocks, morph, nbt, nightlight, palette
from mcbuild.gen import balloon, isthmus, stegosaur, wyrm
from mcbuild.gen.stegosaur import HIDE

# THE CAUSEWAY'S WYRM IS THE RETIRED SERPENT, NOT THE DEFAULT FORM, and this file has to say so
# explicitly. `wyrm.py` now defaults to the locked W1 threshold - a ribcage you walk through, with
# no coil, no hood and no eyes - so a maker that took the default would be testing a shape this
# causeway never sites. `tests/test_wyrm.py` owns that one. Spelt the same way `isthmus.py`
# spells it, so the two cannot drift into testing and siting different animals.
MAKERS = {"balloon": lambda **kw: balloon.build_balloon(kw),
          "wyrm": lambda **kw: wyrm.build_wyrm({"form": "serpent", **kw}),
          # THE STEGOSAUR HAS NO `face`: it is a compass animal, and which way it looks is a
          # FACING rather than a signed multiplier. Both are mapped here so the shared checks
          # still exercise two genuinely different arithmetics - a north build and a south one
          # are separate roundings of the same shape, which is what the parametrisation is for.
          "stegosaur": lambda face=1, **kw: stegosaur.build_stegosaur(
              {"facing": "north" if face > 0 else "south", **kw})}

#: The pieces that bring their own ground. **THE STEGOSAUR IS NOT ONE OF THEM AND MUST NOT BE
#: SWEPT IN**: a balloon stands on its basket and a wyrm on its milestone, so each lands on one
#: solid footing, while a stegosaur stands on FOUR FEET on the causeway's own plinth and its
#: lowest course is four separate pads with air between them. That is `_site_footed`'s contract,
#: not `_site_standing`'s, and running the wrong one over it would fail a correct build.
SELF_CARRYING = {"balloon", "wyrm"}


def _cells(c):
    """{(x, y, z): name} in the canvas's OWN coordinates."""
    names = [nbt.state_name(e).split(":")[-1] for e in c.palette]
    ys, zs, xs = np.nonzero(c.ids > 0)
    return {(x, y, z): names[int(c.ids[y, z, x])]
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())}


def _new_specs():
    """The shipped specs for the bespoke pieces, read off `GAPS` rather than re-typed - a test
    that pins a scale the design does not actually site at pins nothing at all."""
    return [s for g in isthmus.GAPS for s in g["creatures"] if s["kind"] in MAKERS]


def _standing_specs():
    """...and of those, only the ones that carry their own ground. See `SELF_CARRYING`."""
    return [s for s in _new_specs() if s["kind"] in SELF_CARRYING]


# ----------------------------------------------------------------- both, as shapes

@pytest.mark.parametrize("kind", sorted(MAKERS))
@pytest.mark.parametrize("face", [1, -1])
def test_it_is_ONE_PIECE_at_every_orientation_it_can_be_sited_at(kind, face):
    """6-CONNECTED, AND MEASURED RATHER THAN ASSUMED. A swept feature whose cells are only
    diagonal neighbours is not connected, and that has cost this project ear tips, ossicones,
    a detached mane and a whole dragonfly. Both faces, because the wyrm is built from a signed
    x multiplier rather than mirrored afterwards, so the two are genuinely different arithmetic
    and a rounding that works one way round can fail the other."""
    c = MAKERS[kind](face=face)
    _lab, sizes = morph.components(c.to_model().ids > 0, conn=6)
    assert len(sizes) == 1, \
        f"{kind} at face={face} came out in {len(sizes)} pieces: {sorted(sizes, reverse=True)[:6]}"


@pytest.mark.parametrize("kind", sorted(MAKERS))
def test_every_block_is_spendable_available_and_not_dear(kind):
    """The three axes this project keeps separate on purpose: does the block EXIST, does the
    1.19 SERVER have it (the client is 26.2), and is it CURRENCY here - dirt and grass are
    money on this skyblock and passed every other check in the pipeline while the lion shipped
    with a coat of 5,173 of them."""
    for name in set(_cells(MAKERS[kind]()).values()):
        assert blocks.exists(name), f"{kind} places {name}, which is not a block"
        assert blocks.available(name), f"{kind} places {name}, which the 1.19 server has not got"
        assert blocks.spendable(name), f"{kind} places {name}, which is CURRENCY on this server"
        assert palette.tier(name) != "expensive", f"{kind} places expensive {name}"


@pytest.mark.parametrize("kind", sorted(MAKERS))
def test_A_SCULPTURE_IS_NOT_A_LAMP(kind):
    """`isthmus._delight` records every cell a sculpture emits and lights it from the AIR
    BESIDE IT with lichen, because a fixture ON a sculpture damages it (`Island Night`'s own
    cost model). It once drove 1,138 froglights into these creatures' coats and the verdict on
    seeing it was "all glowing". A generator that places its own emitter is indistinguishable
    from that failure, and the balloon's burner is exactly the tempting place to do it - which
    is why the mouth is `yellow_wool`, the COLOUR of the flame and not the light of it."""
    emit = nightlight.classify([f"minecraft:{n}" for n in sorted(set(_cells(MAKERS[kind]()).values()))])[1]
    assert not emit.any(), f"{kind} builds a light source into its own coat"


@pytest.mark.parametrize("kind", sorted(MAKERS))
def test_the_tones_it_uses_are_a_LADDER(kind):
    """A VALUE LADDER IS MEASURED ACROSS MATERIAL FAMILIES, NEVER WITHIN ONE. This repo
    concluded three separate times, in three different files, that this economy has almost no
    value contrast - and all three measurements were taken inside a single family, where a
    ladder cannot exist by construction: dressing a stone does not change how much light it
    returns. Scored on the SMALLEST adjacent step, never the range, because 236/159/151 has a
    wide range and two rungs nobody can tell apart (`tools/ladder.py`'s own rule)."""
    lums = sorted({round(sum(blocks.color(n, "side")) / 3.0)
                   for n in set(_cells(MAKERS[kind]()).values())})
    steps = [b - a for a, b in zip(lums, lums[1:])]
    assert lums[-1] - lums[0] > 140, f"{kind} spans only {lums[-1] - lums[0]} of luminance: {lums}"
    assert max(steps) > 60, f"{kind} has no real value step anywhere in it: {lums}"


# ----------------------------------------------------------------- the balloon

def test_the_gap_under_the_envelope_is_REAL():
    """THE NEGATIVE SPACE IS THE FEATURE. Between the basket's rim and the envelope's mouth
    there are courses crossed by NOTHING but the four rope lines; fill them in and the
    silhouette is a blob on a stick rather than a balloon. This is the ladybird's spot-spacing
    rule and the frog's hand rule in a third body, and it is the single thing a later
    "let's thicken the rigging" would destroy."""
    cells = _cells(balloon.build_balloon({}))
    per_course = Counter(y for (_x, y, _z) in cells)
    rig = [y for y, n in per_course.items() if n <= 8]
    assert rig, "there is no course anywhere with only the rigging in it"
    assert max(rig) - min(rig) + 1 == len(rig), "the rigging courses are not contiguous"
    for y in rig:
        assert per_course[y] == 4, f"course {y} carries {per_course[y]} cells, not four ropes"


def test_the_rigging_is_VERTICAL_and_lands_on_both_the_basket_and_the_mouth():
    """A real balloon's lines splay outward to a much wider hem, and a splayed line is a
    DIAGONAL - which is not connected in this project's own sense. So the envelope pinches to a
    mouth no wider than the basket and every line is dead vertical. Checked as a property of
    the built cells: each rope column is one (x, z) with something solid directly above the top
    of it and directly below the bottom."""
    cells = _cells(balloon.build_balloon({}))
    ropes = {(x, y, z) for (x, y, z), n in cells.items() if n.endswith("_fence")}
    cols = {(x, z) for (x, _y, z) in ropes}
    assert len(cols) == 4, f"the rigging is {len(cols)} columns, not four"
    for (x, z) in cols:
        ys = sorted(y for (rx, y, rz) in ropes if (rx, rz) == (x, z))
        assert ys == list(range(ys[0], ys[-1] + 1)), f"the rope at {(x, z)} has a gap in it"
        assert (x, ys[0] - 1, z) in cells, f"the rope at {(x, z)} does not reach the basket"
        assert (x, ys[-1] + 1, z) in cells, f"the rope at {(x, z)} does not reach the mouth"


def test_the_gores_alternate_and_the_crown_valve_is_ONE_COURSE():
    """THE GORES ARE THE IDENTITY - a pattern on a convex mass, the ladybird's own category -
    so both tones have to be present in real quantity rather than one having quietly swallowed
    the other. And the valve gets ONE course: given the top TWO it covered a disc of radius 5.5
    out of 7.5, and the PLAN - a view every visitor gets off the skyway - was a black hole with
    a red-and-white fringe round it."""
    c = balloon.build_balloon({})
    cells = _cells(c)
    n = Counter(cells.values())
    assert min(n["red_wool"], n["white_wool"]) > 0.4 * max(n["red_wool"], n["white_wool"]), \
        f"one gore tone has swallowed the other: {n['red_wool']} red, {n['white_wool']} white"
    top = max(y for (_x, y, _z) in cells)
    valve = {y for (_x, y, _z), name in cells.items() if name == "black_wool" and y > top - 4}
    assert valve == {top}, f"the crown valve covers courses {sorted(valve)}, not just {top}"
    assert c.meta["features_built"]["gores"] >= 10, "fewer than ten gores reads as a beach ball"


# ----------------------------------------------------------------- the wyrm

@pytest.mark.parametrize("face", [1, -1])
def test_the_head_stands_PROUD_of_the_hood(face):
    """A hood with the head buried in it is a paddle. The skull has to be forward of the plate
    along the face axis, by enough to read as a head in front of a hood rather than a bump on
    one - and 'forward' is a signed direction, so this is checked at both faces or a sign error
    passes half the time."""
    c = wyrm.build_wyrm({"form": "serpent", "face": face})
    cells = _cells(c)
    # THE HOOD'S RIM AND THE BODY'S BANDS ARE THE SAME BLOCK, so "every black_wool cell" is not
    # the hood - it is the hood plus the tail, and the tail is at the far end of the animal.
    # The generator records the plane instead. (Written the naive way this test failed at
    # face=-1 and passed at face=+1, which is exactly how a sign error survives.)
    hood = c.meta["hood_plane"]
    head = [x for (x, _y, _z), n in cells.items() if n == "red_wool"]
    assert head, "the wyrm has no eyes, so there is no head to measure"
    assert (min(head) - hood) * face >= 3,         f"the head at x={sorted(set(head))} does not stand clear of the hood plane x={hood}"


@pytest.mark.parametrize("face", [1, -1])
def test_it_has_TWO_eyes_and_they_are_a_pair(face):
    """SHIPPED WITH ONE EYE, TWICE. The probe was a computed offset onto a course where the
    skull is two cells wide, and the half-cell centring makes those two asymmetric about the
    midline: one side found a block, the other found air. No error anywhere. The probe now
    SEARCHES for a row wide enough to carry a pair, which is the only version of this that can
    survive somebody moving the head."""
    c = wyrm.build_wyrm({"form": "serpent", "face": face})
    cells = _cells(c)
    eyes = [k for k, n in cells.items() if n == "red_wool"]
    assert len(eyes) == 2, f"the wyrm has {len(eyes)} eyes"
    assert c.meta["features_built"]["eyes"] == 2
    (x0, y0, z0), (x1, y1, z1) = eyes
    assert (x0, y0) == (x1, y1), "the two eyes are not on one row of the skull"
    assert abs(z0 - z1) >= 2, "the two eyes are adjacent - that is one bar, not a pair"


def test_the_hood_is_a_PLANE_with_a_dark_rim():
    """The hood is the feature that makes the thing nameable in a thumbnail, and it works
    because it is FLAT - two courses thick against eleven wide - with a dark rim drawing its
    edge. A pale plate against a pale sky is a shape with no outline, which on a causeway with
    nothing behind it but open air is the whole ball game."""
    c = wyrm.build_wyrm({"form": "serpent", "face": 1})
    f = c.meta["features_built"]
    assert f["hood"] > 100, f"the hood is only {f['hood']} cells - too small to read"
    assert 0.1 < f["hood_rim"] / f["hood"] < 0.45, \
        f"the rim is {f['hood_rim']} of {f['hood']} hood cells - a line, or a black plate?"
    assert f["eyespots"] > 0, "the hood carries no pattern at all"


def test_the_coil_stays_at_the_BASE_and_the_rise_carries_the_outline():
    """THE RECORDED VERDICT, PINNED. The first build wound two and a quarter turns up a
    twenty-course obelisk. It was a real helix, one connected piece, correctly banded - and its
    silhouette was a lumpy vertical mass with a hook on top: a totem, or a chess piece. A coil
    round a column reads through COLOUR AND DEPTH and its OUTLINE is a bumpy column, and on
    this causeway there is nothing behind a sculpture but sky. So the coil is short and low and
    the free rise is what is spent on the outline; this fails if that trade is ever reversed."""
    c = wyrm.build_wyrm({"form": "serpent", "face": 1})
    f = c.meta["features_built"]
    assert f["rise"] > f["coil_stations"], \
        "the coil has more of the animal in it than the free rise - that build was rejected"
    cells = _cells(c)
    top = max(y for (_x, y, _z) in cells)
    stone = max(y for (_x, y, _z), n in cells.items()
                if n in ("deepslate_bricks", "polished_blackstone_bricks"))
    assert top - stone > 15, \
        f"only {top - stone} courses of animal stand clear of the milestone"


# ----------------------------------------------------------------- as SITED

@pytest.mark.parametrize("spec", _new_specs(), ids=lambda s: s["kind"])
def test_every_plaque_line_fits_on_a_sign(spec):
    """`isthmus._sign` truncates at `park.SIGN_WIDTH`, which is a guard against a corrupt
    region and NOT a licence to write a line nobody can read: a plaque saying "moored over tw"
    is a plaque with a typo on it, and the truncation is silent in a build nobody re-reads."""
    from mcbuild.gen import park
    for line in [spec["title"]] + list(spec.get("lines") or []):
        assert len(line) <= park.SIGN_WIDTH, \
            f"{spec['kind']}'s plaque line {line!r} is {len(line)} characters"


@pytest.mark.parametrize("spec", _standing_specs(), ids=lambda s: s["kind"])
def test_a_sited_piece_carries_its_own_ground(spec):
    """NEITHER OF THESE NEEDS ONE BLOCK OF STRUCTURE FROM THE CAUSEWAY, and that is the whole
    reason `_site_standing` is three lines where a gantry's siter is thirty. A balloon brings
    its own basket and a wyrm its own milestone, so the piece's LOWEST COURSE lands square on
    the plinth's top on a FOOTPRINT - one solid patch, with the mass standing over it - rather
    than on the scatter of separate contact points a gantry or a stele reduces to, which is
    the failure a render caught once when a gantry shipped with one leg.

    THE CHECK IS THE SHAPE OF THE FOOTING, NOT WHAT IS DIRECTLY ABOVE EACH CELL. Written the
    obvious way - every seat cell carries something on top of it - it fails a basket, whose
    floor is deliberately open above because that is what makes it a basket rather than a
    crate. What matters is that the piece has one footing and stands on it.
    """
    c = isthmus.creature_canvas(spec, [0, 0, 0])
    cells = _cells(c)
    floor = min(y for (_x, y, _z) in cells)
    seat = {(x, z) for (x, y, z) in cells if y == floor}
    assert len(seat) >= 9, f"{spec['kind']} rests on {len(seat)} cells - that is a spike"
    seen, q = {next(iter(seat))}, [next(iter(seat))]
    while q:
        x, z = q.pop()
        for nb in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if nb in seat and nb not in seen:
                seen.add(nb)
                q.append(nb)
    assert seen == seat, \
        f"{spec['kind']}'s footing is in pieces: {len(seat) - len(seen)} cells stand apart"
    xs = [x for (x, _y, _z) in cells]
    zs = [z for (_x, _y, z) in cells]
    for mid, axis, got in (((min(xs) + max(xs)) // 2, 0, {p[0] for p in seat}),
                           ((min(zs) + max(zs)) // 2, 1, {p[1] for p in seat})):
        assert min(got) <= mid <= max(got), \
            f"{spec['kind']} does not stand over its own footing on axis {axis}"


def test_the_causeway_sites_them_whole_and_lights_neither_of_them():
    """The end-to-end check, in the finished causeway rather than in a canvas: every cell each
    generator emitted is still standing (the plinth is laid BEFORE the paste and the night
    sweep is the only thing afterwards that writes anything, so a shortfall in any block of a
    creature's own palette IS a coat cell something replaced), and not one lamp went into
    either coat."""
    c = isthmus.build({"kind": "isthmus"})
    model = c.to_model()
    names = [nbt.state_name(e).split(":")[-1] for e in model.palette]
    have = Counter()
    for i in np.unique(model.ids):
        if i:
            have[names[int(i)]] += int((model.ids == i).sum())
    for spec in _new_specs():
        want = Counter(_cells(isthmus.creature_canvas(spec)).values())
        for name, n in want.items():
            assert have[name] >= n, \
                f"{spec['kind']} emitted {n} {name} and only {have[name]} survive"
    assert c.meta["delight_in_coat"] == 0
    assert c.meta["spawnable_dark"] == 0


# ----------------------------------------------------------------- the stegosaur

#: Built facing NORTH throughout this section, because a compass animal's own axes are only
#: fixed once its facing is: at north the side axis is x and the walk axis is z, which is what
#: every assertion below is written in. The shared checks above already exercise the other
#: facing, and `test_nothing_is_CLIPPED_off_its_own_canvas` covers all four.
CREST = {"white_wool", "stone"}
#: **THE COAT'S SHAPE-BLOCK FORMS COUNT AS BODY.** `shell.slab_shell` and `_chamfer` replace skin
#: cells with the slab and the stair of the same colour family, so a mask written as the three coat
#: WOOLS silently loses a hundred cells of flank - and every test measuring the plan silhouette or
#: the leg tone then measures a body with holes in it while passing.
HIDE_BODY = {"brown_wool", "acacia_planks", "light_gray_wool",
             "spruce_slab", "acacia_slab", "andesite_slab",
             "spruce_stairs", "acacia_stairs", "andesite_stairs"}


def _steg(**kw):
    return stegosaur.build_stegosaur({"facing": "north", **kw})


def _mask(c, mats):
    """A boolean grid of just these materials, in the canvas's own (y, z, x) order."""
    m = c.to_model()
    names = [nbt.state_name(e).split(":")[-1].split("[")[0] for e in m.palette]
    out = np.zeros(m.ids.shape, bool)
    for i, n in enumerate(names):
        if n in mats:
            out |= (m.ids == i)
    return out


_FLIP = {"east": "west", "west": "east", "north": "north", "south": "south"}


def _mirrored(state: str) -> str:
    """A block state as its own reflection across the animal's sagittal plane.

    **A FACING MIRRORS, IT DOES NOT COPY**, and only the ACROSS axis flips - a stair leaning fore
    or aft leans the same way on both flanks. The frog shipped 60 of its 134 stairs facing the
    same way on both sides, which our renderer drew identically until `render3d.subdivide` learned
    to expand a stair, so it was wrong in game and invisible in every sheet.
    """
    if "facing=" not in state:
        return state
    head, rest = state.split("[", 1)
    props = dict(p.split("=") for p in rest.rstrip("]").split(","))
    props["facing"] = _FLIP[props["facing"]]
    return head + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"


def _norm(state: str) -> str:
    if "[" not in state:
        return state
    head, rest = state.split("[", 1)
    props = dict(p.split("=") for p in rest.rstrip("]").split(","))
    return head + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"


def _lr(c):
    """(shape mismatches, colour mismatches) across the animal's own sagittal plane.

    Compares FULL BLOCK STATES with the facing mirrored, not bare names: a stair facing the wrong
    way is a real defect and a bare-name comparison cannot see it. `north` is the animal's facing
    here, so the across axis is x and east/west is what flips.
    """
    m = c.to_model()
    names = [nbt.state_name(e).split(":")[-1] for e in m.palette]
    ids, mid = m.ids, c.sx // 2
    shape = colour = 0
    for y in range(ids.shape[0]):
        for z in range(ids.shape[1]):
            for s in range(1, mid + 1):
                a, b = mid + s, mid - s
                if b < 0 or a >= ids.shape[2]:
                    continue
                na, nb = names[int(ids[y, z, a])], names[int(ids[y, z, b])]
                if (na == "air") != (nb == "air"):
                    shape += 1
                elif na != "air" and _mirrored(na) != _norm(nb):
                    colour += 1
    return shape, colour


def test_it_is_MIRRORED_in_shape_AND_IN_COLOUR():
    """**THE TEST JACK'S OWN VERDICT WROTE.** The first build's crest ALTERNATED, the way the
    real animal's does, and measured block by block that was the only asymmetry anywhere in it:
    99 cells, every one a plate, with the mass and the coat exactly mirrored. It is not a
    detail - head-on, two rows offset one cell either side of a nine-wide back are not two rows,
    they are two chimneys at different depths, and in plan they are a zigzag. A real stegosaur is
    two metres wide and staggers its plates by a hand's breadth; a voxel one at this size has one
    cell to say it with, and one cell reads as a mistake.

    **BOTH HALVES, because the first mirror check only compared solid against air** and would
    have passed a build whose left flank was a different colour from its right - which is exactly
    the fault the frog shipped, and the squid shipped 5,375 cells of.
    """
    shape, colour = _lr(_steg())
    assert (shape, colour) == (0, 0), \
        f"{shape} cells differ in SHAPE and {colour} in COLOUR across the sagittal plane"


def test_the_crest_is_FOUR_PAIRED_PLATES_and_never_a_sail():
    """THE PLATES ARE THE ANIMAL, AND A MERGED CREST IS A DIFFERENT ANIMAL. Built with a broad
    root they fused along the spine into one continuous sheet - a dimetrodon, and the naming test
    fails outright on that. Built with a one-cell root they came apart the other way and hovered
    on stalks with daylight under them.

    **AND THE SPACING IS EXACT INTEGER GEOMETRY, which took two goes to get right.** The width
    curve alone let `plate_half` scale to 2.54 for the plate nearest the peak, `floor(2.54 + 0.5)`
    is 3, and that one plate went from five cells across to SEVEN and fused with its neighbour -
    four plates read as three. Capping the width against `run / count` fixed that length and not
    the next, because the stations are floats and `_r` rounds them together about half the time.
    The width is chosen first and the pitch derived as `2 * wi + 2`, so there is exactly one cell
    of sky between neighbours at any length, count or curve.

    Counted 6-connected among the crest's OWN cells, and the answer is TWICE the plate count
    because each plate is a pair - one sheet either side of the spine.
    """
    c = _steg()
    _lab, sizes = morph.components(_mask(c, CREST), conn=6)
    assert c.meta["parts"]["plates"] == 4
    assert len(sizes) == 8, \
        f"the crest came out in {len(sizes)} pieces, not 4 plates x 2 rows: {sorted(sizes)}"
    assert min(sizes) >= 12, f"a plate of {min(sizes)} cells is a bump, not a plate: {sizes}"


def test_the_plates_are_PAIRED_either_side_of_the_spine():
    """**PAIRED, NOT STAGGERED AND NOT CENTRED**, and each of those alternatives was built and
    rejected by looking. Staggered is the real animal and is the asymmetry Jack called out.
    Centred on the sagittal plane is symmetric and turns the crest into a single one-block blade
    standing out of the spine - a MAST, head-on. Paired at the same station either side of the
    midline is symmetric AND is what a stegosaur looks like from the front: two pale blades
    flanking a ridge with the spine showing between them."""
    c = _steg()
    _ys, _zs, xs = np.nonzero(_mask(c, CREST))
    mid = c.sx // 2
    assert set(xs.tolist()) == {mid - 1, mid + 1}, \
        f"the plates stand at x {sorted(set(xs.tolist()))}, not one column either side of {mid}"
    assert (xs == mid - 1).sum() == (xs == mid + 1).sum(), "the two rows are not the same size"


def test_every_plate_STANDS_ON_THE_BACK_it_grew_from():
    """**ANYTHING CLINGING IS ANCHORED TO THE BUILT SURFACE, NEVER TO A COMPUTED RADIUS** - the
    rule that stopped a lion's mane shipping as seven floating fragments and a giraffe's
    ossicones detaching. The back ARCHES, so a plate placed at a computed height is wrong by two
    courses at one end of the run and right in the middle. And the surface has to be SNAPSHOTTED
    before any plate is laid: probed live, the second course of a plate finds the first course of
    that same plate and lands one higher again, which shipped every plate as alternate courses
    with a hole between them - fifty four-cell strays.

    Checked as two properties rather than as the mechanism: no plate column has a gap in it, and
    every PLATE has real contact with the back.

    **PER PLATE, NOT PER COLUMN**, and the difference is the shape of the thing: a kite is three
    cells at the root and five at its widest, so its outer wings BEGIN two courses up and
    legitimately overhang. Written per column this failed a correct build - which is the right
    way round to discover that the contract had been stated as "nothing overhangs" when what was
    meant was "nothing floats".
    """
    c = _steg()
    crest, body = _mask(c, CREST), _mask(c, HIDE_BODY)
    for x in range(c.sx):
        for z in range(c.sz):
            col = np.nonzero(crest[:, z, x])[0]
            if len(col):
                assert col.max() - col.min() + 1 == len(col), \
                    f"the plate column at {(x, z)} has a hole in it: {col.tolist()}"
    lab, sizes = morph.components(crest, conn=6)
    for k in range(1, len(sizes) + 1):
        ys, zs, xs = np.nonzero(lab == k)
        rooted = sum(1 for y, z, x in zip(ys, zs, xs) if y and body[y - 1, z, x])
        assert rooted >= 3, \
            f"plate {k} meets the back at {rooted} cells - it is standing on a stalk"


def test_the_plan_silhouette_is_a_SPINDLE_and_not_a_slab():
    """**RULE 4 OF THE PANEL REVIEW, AND THE FIRST BUILD FAILED IT.** A quadruped is widest at the
    shoulder and the haunch with a WAIST between; a constant-depth rectangle from shoulder to rump
    is what retired the jaguar ("the animal has no centre of gravity"). The first stegosaur swept
    SPHERES, so a station's width in plan and its depth in profile were the same number by
    construction and the plan came out as one flat mass. The spine carries a half-depth and a
    half-width separately now, and the body is lofted station by station.

    Measured as the property: the plan width has TWO maxima with a real dip between them.
    """
    c = _steg()
    body = _mask(c, HIDE_BODY)
    prof = []
    for z in range(c.sz):
        xs = np.nonzero(body[:, z, :].any(axis=0))[0]
        if len(xs):
            prof.append(int(xs.max() - xs.min() + 1))
    peaks = [i for i in range(1, len(prof) - 1)
             if prof[i] > prof[i - 1] and prof[i] >= prof[i + 1]]
    assert max(prof) - min(prof) >= 4, f"the plan barely changes width: {prof}"
    assert len(peaks) >= 2, f"the plan has no waist - it is a slab: {prof}"


def test_the_LEGS_are_one_colour_and_not_countershaded_like_a_barrel():
    """**A LEG IS NOT ITS OWN ANIMAL.** `_coat` measures each column between its own lowest and
    highest cell, which is right for a barrel and absurd for a leg: four courses got the full
    ladder - pale at the foot, mid at the knee, dark at the top - so the animal stood on four
    grey posts and read as a barrel on a stone plinth. Everything below the body's own belly line
    at its station takes the flank tone and nothing else."""
    c = _steg()
    m = c.to_model()
    names = [nbt.state_name(e).split(":")[-1].split("[")[0] for e in m.palette]
    d = stegosaur._dims(float(c.meta["length"]))
    # well below the belly line at any station: legs, feet and nothing else
    floor = int(stegosaur._belly_at(d, 0.0)) - 3
    got = {names[int(m.ids[y, z, x])]
           for y in range(max(1, floor)) for z in range(c.sz) for x in range(c.sx)
           if names[int(m.ids[y, z, x])] in HIDE_BODY}
    assert got <= {HIDE["flank"]}, f"the legs carry {sorted(got)}, not just the flank tone"


def test_it_stands_on_FOUR_FEET():
    """FOUR PADS, NOT EIGHT. Its legs stand at 0.150 of its length, and `round()` is banker's
    rounding: `round(4.5) == 4` while `round(5.5) == 6`, so at any length where that lands on x.5
    every foot sphere skipped alternate columns and came out as a comb of separate pads. Four feet
    read as eight, at one length and not at its neighbours, and nothing but the ground course's
    own component count could see it."""
    c = _steg()
    ground = (c.to_model().ids[0] > 0)[None, :, :]
    _lab, sizes = morph.components(ground, conn=6)
    assert len(sizes) == 4, f"it touches down in {len(sizes)} patches, not four: {sizes}"


def test_the_head_is_small_PALE_and_carried_low():
    """Both are cues rather than details: a stegosaur's skull is the smallest thing on it and
    every reconstruction a stranger has ever seen has it near the ground. And it is BONE, because
    painted as body it is the end of a taper with no line anywhere for a head to begin at - and a
    black eye bead on a dark flank has nowhere to go, which is the bear's own recorded failure,
    still open in CLAUDE.md."""
    c = _steg()
    cells = _cells(c)
    nose = min(z for (_x, _y, z) in cells)            # facing north: forward is -z
    assert {n for (_x, _y, z), n in cells.items() if z <= nose + 1} == {"bone_block"}, \
        "the front of the animal is not a pale skull"
    head_top = max(y for (_x, y, z) in cells if z <= nose + 3)
    tall = max(y for (_x, y, _z) in cells)
    assert head_top < tall * 0.5, \
        f"the head reaches {head_top} of {tall} - it is not carried low"
    assert c.meta["parts"]["eyes"] == 2


@pytest.mark.parametrize("length", [22, 26, 30, 34, 40, 46, 54])
def test_it_survives_EVERY_LENGTH_it_can_be_built_at(length):
    """**A SCALE SWEEP IS THE ONLY THING THAT CATCHES A FEATURE THAT HALF-EXISTS.** This animal
    shipped with NO EYES at length 24 - the nominal course was a cell above the widest part of a
    small skull, so neither side had anything to sit on - and shed its tail spikes at lengths 26
    and 34 and at neither of their neighbours, and fused two of its plates at 30, 40 and 50 after
    a fix that worked perfectly at 34. Every one was silent: no error, nothing in the audit,
    nothing in the component count of the length anybody happened to be looking at."""
    c = stegosaur.build_stegosaur({"length": length})
    _lab, sizes = morph.components(c.to_model().ids > 0, conn=6)
    assert len(sizes) == 1, f"at length {length} it came out in {len(sizes)} pieces: {sizes[:6]}"
    assert c.meta["parts"]["eyes"] == 2, f"at length {length} it has {c.meta['parts']['eyes']} eyes"
    _lab2, crest = morph.components(_mask(c, CREST), conn=6)
    assert len(crest) == 2 * c.meta["parts"]["plates"], \
        f"at length {length} the crest is {len(crest)} pieces for {c.meta['parts']['plates']} plates"
    assert _lr(c) == (0, 0), f"at length {length} it is asymmetric: {_lr(c)}"


@pytest.mark.parametrize("facing", ["north", "south", "east", "west"])
def test_nothing_is_CLIPPED_off_its_own_canvas(facing):
    """**THE BOX IS SIZED BY THE FACING, NOT BY THE ANIMAL.** A canvas that is always long in X
    is long in the WRONG axis for a north-south animal: the sauropod built facing north came out
    clipped to 22 blocks of 48 - head, neck and half the tail simply refused - and the render
    still showed a plausible small dinosaur. The only symptom was a refusal count nobody read,
    which is why `clipped` is counted apart from `refused`: a foot pad's lower hemisphere is
    always outside the box and always will be, because that is the ground."""
    c = stegosaur.build_stegosaur({"facing": facing})
    assert c.meta["clipped"] == 0, f"facing {facing} clips {c.meta['clipped']} cells off the box"


def test_it_REFUSES_a_length_that_cannot_carry_a_plate():
    """Its identity is the CREST, the tallest plate is about 0.24 of the length, and a plate under
    five courses is a bump on a back. Below that there is nothing left of the animal, so it says
    so rather than building something that audits clean and cannot be named."""
    with pytest.raises(ValueError, match="plate"):
        stegosaur.build_stegosaur({"length": 18})


def test_the_SURFACE_IS_SMOOTHED_and_not_merely_stacked():
    """**THE THREE PASSES THAT ANSWER "SUPER BLOCKY AND ROUGH", AND EACH ONE FAILS SILENTLY.**

    `relax` is step 2 of CLAUDE.md's own build order (`mass -> relax -> features -> face -> coat`)
    and this animal skipped it for two versions. `shell.slab_shell` halves every cell that sits
    proud of its neighbours - and reported ZERO for a while because the block name was read with
    `str()` off an NBT Tag, which is a repr, so every colour lookup missed and the pass looked
    exactly like one that had nothing to do. `_chamfer` turns one-course steps into ramps with
    stairs, which the download corpus measures this repo at a SEVENTH of the outside rate.

    Every one of those, switched off, leaves a build that is legal, one piece, correctly
    proportioned, audits clean and looks like a stack of boxes. So the counts are asserted, and
    so is the measured result: `spike_rate` counts solid cells with too few neighbours, which is
    exactly "a limb that seems to have gravel stuck to it".
    """
    from mcbuild.gen import smooth
    c = _steg()
    p = c.meta["parts"]
    assert p["shell"]["slabs"] > 20, f"the half-block pass placed {p['shell']['slabs']} slabs"
    assert p["stairs"] > 20, f"the chamfer pass placed {p['stairs']} stairs"
    skin = _mask(c, HIDE_BODY)
    ys, zs, xs = np.nonzero(skin)
    r = smooth.roughness({(int(x), int(y), int(z)) for x, y, z in zip(xs, ys, zs)})
    assert r["notches"] == 0, f"the skin has {r['notches']} one-block dents in it"
    assert r["spike_rate"] < 14, f"the skin's spike rate is {r['spike_rate']:.1f} - it is gravelly"


def test_the_LEGS_do_not_stick_out_THROUGH_the_flank():
    """**THE LUMPS WERE THE LEGS, AND SCALING THE ANIMAL UP MADE THEM WORSE.** The half-width at
    the shoulder and the hip was a number chosen by eye, and it was smaller than `stance + leg
    radius`: 2.65 of gauge plus 2.38 of thigh reaches 5.03 where the flank reached 3.67, so each
    leg pushed a cell and a half out THROUGH the side of the animal. Four lumps, at the four
    places a quadruped is supposed to be smoothest - and because they scale with the animal,
    building it half again as big made them bigger rather than finer, which is what proved the
    roughness was geometry and not resolution.

    Sized to cover the legs, the same cells are the HAUNCH and the SHOULDER - rule 1 of the panel
    review, "legs must merge into the body as a haunch and a shoulder".
    """
    d = stegosaur._dims(34.0)
    at = {round(f, 3): hw for (f, _y, _hd, hw) in d["spine"]}
    for name, f, r in (("shoulder", d["fore_f"], d["fore_r0"]),
                       ("hip", d["hind_f"], d["hind_r0"])):
        near = min(at, key=lambda k: abs(k - f))
        assert at[near] + 1e-6 >= d["stance"] + r, (
            f"the {name} is {at[near]:.2f} half-wide but the leg reaches "
            f"{d['stance'] + r:.2f} - it sticks out through the flank")
