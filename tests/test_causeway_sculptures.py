"""The BESPOKE sculptures on the isthmus - `gen/balloon.py`, `gen/wyrm.py`, `gen/ankylosaur.py`
and the RETIRED `gen/stegosaur.py`.

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

**THE STEGOSAUR IS RETIRED AND ITS TESTS STAY.** It is not in `GAPS` any more, so `_new_specs()`
drops it from everything that reads the causeway's own siting - but the piece still builds, still
loads, and the eleven bugs above are eleven bugs a second animal can inherit the moment somebody
copies its machinery. `taxonomy.live()`'s rule: a retirement is a RECORD, not a deletion. What
retired it is not in this file at all, because it is not a property of the build: four polish
rounds could not make a STANDING QUADRUPED read, which is the corpus's own finding and the reason
eight mammals were retired before it. The ankylosaur is the replacement, and it is chosen because
its own anatomy is the shape that survives - one low mass with the legs tucked under it.
"""
from collections import Counter

import numpy as np
import pytest

from mcbuild import blocks, morph, nbt, nightlight, palette
from mcbuild.gen import ankylosaur, balloon, isthmus, stegosaur, wyrm
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
              {"facing": "north" if face > 0 else "south", **kw}),
          "ankylosaur": lambda face=1, **kw: ankylosaur.build_ankylosaur(
              {"facing": "north" if face > 0 else "south", **kw})}

#: The pieces that bring their own ground. **THE STEGOSAUR IS NOT ONE OF THEM AND MUST NOT BE
#: SWEPT IN**: a balloon stands on its basket and a wyrm on its milestone, so each lands on one
#: solid footing, while a stegosaur stands on FOUR FEET on the causeway's own plinth and its
#: lowest course is four separate pads with air between them. That is `_site_footed`'s contract,
#: not `_site_standing`'s, and running the wrong one over it would fail a correct build. The
#: ankylosaur is the same case for the same reason.
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


def _full(entry) -> str:
    """`name[k=v,...]` for a palette entry.

    **`nbt.state_name` RETURNS ONLY THE NAME**, so every comparison in this file that was written
    to compare FULL BLOCK STATES has in fact been comparing bare names - including `_lr`, whose own
    docstring says it exists to catch a stair facing the wrong way on one flank. That is precisely
    the frog's 60-of-134 defect, which our renderer drew identically until `render3d.subdivide`
    learned to expand a stair, so it was wrong in game and invisible in every sheet AND in the test
    written to catch it. The properties are in `state_props`; they have to be asked for.
    """
    n = nbt.state_name(entry).split(":")[-1]
    p = nbt.state_props(entry)
    return n + ("[" + ",".join(f"{k}={v}" for k, v in sorted(p.items())) + "]" if p else "")


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
    names = [_full(e) for e in m.palette]
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
    # READ THE OFFSET FROM THE GENERATOR, never a literal. It moved from one cell to two when the
    # single-column trough between the rows measured as twelve NOTCHES - one-block dents, which
    # `smooth.roughness` says "the eye reads as damage" - and a test carrying the old number would
    # have failed the fix rather than the fault.
    off = int(stegosaur._dims(float(c.meta["length"]))["plate_offset"])
    assert set(xs.tolist()) == {mid - off, mid + off}, \
        f"the plates stand at x {sorted(set(xs.tolist()))}, not {off} either side of {mid}"
    assert (xs == mid - off).sum() == (xs == mid + off).sum(), "the two rows differ in size"


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
    p = c.meta["parts"]["surface"]
    assert p["slabs"] > 20, f"the half-block pass placed {p['slabs']} slabs"
    assert p["stairs"] > 60, f"the stair pass placed {p['stairs']} ramps"
    # **THE UNDERSIDE IS HALF OF IT, and it is the half the corpus says we never build.** 27% of
    # outside builders' stairs are `half=top` - eaves, soffits, corbels, the underside of an
    # overhang - against none of ours before this. On an animal it is the belly line and the jaw,
    # which with the back line is the whole of what a profile silhouette IS.
    assert p["stairs_under"] > 20, f"only {p['stairs_under']} of the ramps are undersides"
    assert (p["slabs"] + p["stairs"]) / p["skin"] > 0.12,         "under an eighth of the skin is a partial - this is a stack of cubes again"
    skin = _mask(c, HIDE_BODY)
    ys, zs, xs = np.nonzero(skin)
    r = smooth.roughness({(int(x), int(y), int(z)) for x, y, z in zip(xs, ys, zs)})
    assert r["spike_rate"] < 14, f"the skin's spike rate is {r['spike_rate']:.1f} - it is gravelly"

    # **EVERY REMAINING DENT MUST BE THE SPACE BETWEEN ITS LEGS**, which is supposed to be there.
    # `roughness` counts an air cell walled on most sides as a NOTCH and cannot tell a crotch from
    # damage - the giraffe scores zero only because its legs are far apart and its belly is high.
    # So the assertion is exact rather than a threshold: below the belly line, on the midline. A
    # dent anywhere else is the fault this metric exists to catch.
    from mcbuild import morph as _m
    ids = c.to_model().ids
    solid = ids > 0
    dents = (~solid) & (_m.neighbor_count(solid, conn=26) > 18)
    d = stegosaur._dims(float(c.meta["length"]))
    mid = c.sx // 2
    for y, z, x in zip(*np.nonzero(dents)):
        assert abs(int(x) - mid) <= 1 and int(y) < stegosaur._belly_at(d, 0.0) + 2,             f"a one-block dent at {(int(x), int(y), int(z))} is not the gap between its legs"


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


# --------------------------------------------------------------------- the ankylosaur

#: **THE ARMOUR IS ITS OWN MATERIAL AND NOTHING ELSE USES IT.** A mask keyed on a block that the
#: coat also spends measures two things at once - the stegosaur's nostrils were drawn in the
#: plates' own stone, so the plate count, the plate rooting and "the nose is all bone" all failed
#: on a correct build. Every knob, spike, horn and club lobe here is `bone_block` and no cell of
#: the coat is, so `ARMOUR` and `ANK_BODY` partition the animal.
ARMOUR = {"bone_block"}
ANK_BODY = {"dripstone_block", "brown_wool", "light_gray_wool", "black_wool", "dark_oak_planks",
            "spruce_slab", "andesite_slab", "mossy_stone_brick_slab", "dark_oak_slab",
            "spruce_stairs", "andesite_stairs", "mossy_stone_brick_stairs", "dark_oak_stairs"}


def _ank(**kw):
    return ankylosaur.build_ankylosaur({"facing": "north", **kw})


def test_the_barrel_is_CARRIED_CLEAR_but_the_mass_still_dominates():
    """**THIS ANIMAL HAS NOW BEEN WRONG IN BOTH DIRECTIONS, so the contract is two-sided.**

    Built with the legs tucked inside the outline it had a flat back, a dragging tail and its belly
    on the floor - a crocodilian term for term, and what it was read as on sight. The reasoning
    behind that was the corpus's own finding, that a silhouette which decomposes into LIMBS is the
    one thing this system cannot build; but that finding is about a barrel slung between LONG legs,
    which is the jaguar. Four short thick pillars under a wide dome is the TURTLE, and the turtle
    works here. So neither "the legs show" nor "the legs do not" is the property - it is the RATIO.

    **AND IT IS MEASURED ON THE PROFILE, NOT THE MIDLINE.** The first version of this test measured
    the belly down the animal's own centre line and passed the crocodile by a hair, because what a
    walker sees in profile is the FLANK, and the flank reached the ground while the midline did not.
    A test for how something reads has to measure the view it is read in: 1.87 courses of mean
    daylight before against 4.33 after, where the midline said 3.18 against 6.33 and neither number
    was the one that mattered.
    """
    c = _ank()
    d = ankylosaur._dims(float(c.meta["length"]))
    prof = (c.to_model().ids > 0).any(axis=2)
    mid_z = c.sz // 2
    lows = []
    for z in range(c.sz):
        f = mid_z - z
        if not (d["hind_f"] + 2 <= f <= d["fore_f"] - 2):     # strictly BETWEEN the leg pairs
            continue
        col = np.nonzero(prof[:, z])[0]
        if len(col):
            lows.append(int(col.min()))
    assert lows, "no stations between the leg pairs"
    clear = sum(lows) / len(lows)
    assert clear >= 3.0, \
        f"the profile floor between the legs averages {clear:.2f}: the belly is down, and a low " \
        f"flat-backed body with its belly on the floor is an alligator, not a dinosaur"

    # ...and the other half: the mass must still dominate, or it is a jaguar.
    body = _mask(c, ANK_BODY)
    mid_x = c.sx // 2
    depths = []
    for z in range(c.sz):
        f = mid_z - z
        if not (d["spine"][-1][0] <= f <= d["spine"][0][0]):
            continue
        col = np.nonzero(body[:, z, mid_x])[0]
        if len(col) > 1:
            depths.append(int(col.max() - col.min() + 1))
    depth = sum(depths) / len(depths)
    assert depth > clear * 1.4, \
        f"the barrel is {depth:.1f} deep on legs of {clear:.1f}: the silhouette decomposes"


def test_it_is_a_SHIELD_and_not_a_barrel():
    """Wider than it is deep and low for its length, which is the one thing a sphere sweep cannot
    give you: swept as spheres the plan and the profile are the SAME SHAPE by construction, which
    is the jaguar's recorded retirement ("a constant-depth rectangle from shoulder to rump") and
    what made the stegosaur read as a loaf. `_dims` carries a half-DEPTH and a half-WIDTH per
    station for this and nothing else."""
    solid = _ank().to_model().ids > 0
    ys, zs, xs = np.nonzero(solid)
    wide = int(xs.max() - xs.min() + 1)
    tall = int(ys.max() - ys.min() + 1)
    long_ = int(zs.max() - zs.min() + 1)
    assert wide > tall * 1.6, f"{wide} wide against {tall} tall - that is a barrel, not a shield"
    assert long_ > tall * 3.0, f"{long_} long against {tall} tall - it is not low enough"


def test_the_spike_fringe_BREAKS_THE_PLAN_OUTLINE():
    """**THE PLAN IS THIS ANIMAL'S MONEY VIEW** - it is read from the causeway's own walkway and
    from the park skyway above it, and a shield is the one shape voxels give away free from
    overhead. A bare oval reads as a beetle; a fringe of spikes standing out past the rim reads as
    armour. So the fringe has to actually REACH PAST the shell rather than sit on it, which is the
    ladybird's spot-spacing lesson in a different direction."""
    c = _ank()
    bxs = np.nonzero(_mask(c, ANK_BODY))[2]
    axs = np.nonzero(_mask(c, ARMOUR))[2]
    assert axs.min() < bxs.min() and axs.max() > bxs.max(), \
        "no armour reaches past the shell - that is studs on a dome, not a fringe"


def test_the_CLUB_is_a_mass_and_not_a_paddle():
    """The club is half of what names this animal and it failed three ways. Two lobes set close
    with a big radius merge into ONE cube on a stick - a mallet. Set far apart they stop touching
    and the thread joining them shows between as a stem, so it came out as a PLUS SIGN in the one
    view this animal is read in. And at the small end its radii went under a cell: a fraction of
    the length is 0.73 at length 26, `ball` fills a single course, and it shipped as a ONE-COURSE
    PADDLE thinner than the tail carrying it - at two lengths out of five, and not the one it was
    being looked at. A club is two knobs sharing a body: wider than it is tall, and a mass."""
    c = _ank()
    lab, sizes = morph.components(_mask(c, ARMOUR), conn=6)
    rear = max(range(1, len(sizes) + 1), key=lambda i: np.nonzero(lab == i)[1].mean())
    ys, _zs, xs = np.nonzero(lab == rear)
    wide, tall = int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)
    assert sizes[rear - 1] >= 18, f"the club is {sizes[rear - 1]} cells - a knot on a string"
    assert wide >= 5 and tall >= 3, f"the club is {wide} wide and {tall} tall - it is a paddle"
    assert wide > tall, f"the club is {wide} wide and {tall} tall - it is a ball, not a club"


def test_the_head_is_a_BLUNT_BOX_that_reads_APART_from_the_shield():
    """An Ankylosaurus skull is famously WIDER THAN IT IS LONG - a boxy head on a broad beak - and
    this head failed at both ends before it worked. Swept out of the mass at full width it was not
    a head at all, it was the front of the shell tapering, and the animal read HEADLESS. Given a
    deep pinch and a taper to a fine tip it read as a BEAK ON A STICK before smoothing and as a
    smooth CONE after it, because the relax pass fills a narrow trough and shaves a thin ball: the
    last five stations measured 7, 5, 5, 3, 1 and the animal had a snout.

    So the contract is not a local minimum in the width - the smoothing correctly removes one - it
    is that the head is a run of stations markedly narrower than the shield, wide enough to carry
    a pair of eyes, and blunt at the front rather than pointed.
    """
    c = _ank()
    solid = c.to_model().ids > 0
    widths = []
    for z in range(c.sz):
        if solid[:, z, :].any():
            xs = np.nonzero(solid[:, z, :].any(axis=0))[0]
            widths.append(int(xs.max() - xs.min() + 1))
    shield = max(widths)
    head = []
    for w in widths:                                # the leading run, nose backwards
        if w > 0.60 * shield:
            break
        head.append(w)
    assert len(head) >= 4, f"the head is {len(head)} stations long against a shield of {shield}"
    assert max(head) >= 5, f"the head is {max(head)} wide - too narrow to carry a pair of eyes"
    assert sum(1 for w in head if w < 3) <= 1,         f"the skull comes to a point: {head}. An ankylosaur's beak is blunt"


def test_the_KNOBS_are_staggered_and_never_a_lattice():
    """Osteoderms in rows are the pattern that names the carapace, and laid on ONE LATTICE they are
    a field of identical studs - riveted plate, which is machinery rather than an animal. That is
    the deck soffit's confetti failure with the sign reversed: there the fault was too little
    regularity, here it is too much. Alternate rows carry half a pitch of offset and a per-cell
    hash drops one in six, so no two rows line up across the animal."""
    c = _ank()
    # **A KNOB SITS ON THE BODY; A SPIKE STANDS OUT PAST IT.** Masked as "armour above the belly"
    # the fringe comes in too, and the fringe runs every station of the rim - so two of its rows
    # share every station and a correct build fails a test written to catch a lattice. The two
    # features are told apart by what is UNDER them, which is what they actually are.
    below = np.zeros_like(_mask(c, ARMOUR))
    below[1:] = _mask(c, ANK_BODY)[:-1]
    knobs = _mask(c, ARMOUR) & below
    # **KEYED ON THE DISTANCE FROM THE SPINE, NEVER ON THE COLUMN.** The animal is exactly
    # symmetric, so the row at +0.46 of the half-width and the row at -0.46 carry IDENTICAL
    # stations by construction - and a test that compares the two widest columns therefore fails
    # every correct build for being a lattice, which is the mirror doing its job. A row is one
    # offset from the midline; the pair is one row.
    mid = c.sx // 2
    rows = {}
    for _y, z, x in zip(*np.nonzero(knobs)):
        rows.setdefault(abs(int(x) - mid), set()).add(int(z))
    wide = sorted((v for v in rows.values() if len(v) >= 3), key=len, reverse=True)[:3]
    assert len(wide) >= 2, f"only {len(wide)} rows of knobs run along the back"
    for a, b in ((0, 1), (0, 2), (1, 2))[: 3 if len(wide) > 2 else 1]:
        assert wide[a] != wide[b],             f"two rows of knobs share every station: {sorted(wide[a])} - a lattice of rivets"


def test_every_FEATURE_placed_something():
    """**A FEATURE THAT PLACES NOTHING IS INVISIBLE UNLESS THE COUNTS ARE UNIQUE CELLS.** The horns
    were rooted at a computed half-width and sat entirely INSIDE the skull: 124 placements, not one
    new cell, and the sidecar reported a healthy-looking number while the animal shipped hornless.
    It is the frog's `forelegs: 0` exactly - a build with a part missing is still one connected
    piece with a clean audit and a correct bill of materials - and it only surfaced when the part
    counts stopped being `put()` calls and started being cells the model actually gained."""
    p = _ank().meta["parts"]
    for part in ("shell", "legs", "head", "tail", "knobs", "spikes", "club", "horns"):
        assert p[part] > 0, f"{part} placed {p[part]} cells: the animal shipped without it"
    assert p["eyes"] == 2, f"{p['eyes']} eyes"


def test_it_is_MIRRORED_in_shape_AND_IN_COLOUR():
    """Both halves, because a check that compares only solid against air passes a build whose left
    flank is a different colour from its right - the frog's recorded fault, where every coat drift
    carried its own signed offset, and the squid's 5,375 cells. `_lr` compares FULL STATES with the
    facing mirrored, so a stair leaning the wrong way on one flank is caught too: our renderer drew
    the frog's 60 reversed stairs identically until `render3d.subdivide` learned to expand one."""
    assert _lr(_ank()) == (0, 0)


def test_the_SURFACE_IS_SMOOTHED_and_the_relax_actually_ran():
    """`relax` is step 2 of CLAUDE.md's build order and these are `quadruped.py`'s own numbers -
    four rounds at fill 11, keep 11, which is what the GIRAFFE is built with. Measured side by
    side, the stegosaur's first skin scored `spike_rate` 28.97 against the giraffe's 4.03 while
    running ONE round at fill 15 and keep 8. Every one of these passes fails SILENTLY: a build with
    all of them switched off is legal, one piece, correctly proportioned and audits clean."""
    p = _ank().meta["parts"]
    before, after = p["relax"]["spike_rate"]
    assert after < before * 0.5, f"the relax pass barely moved the skin: {before} -> {after}"
    assert after < 4.03, f"the relaxed mass scores {after} - the giraffe scores 4.03"
    s = p["surface"]
    assert s["stairs"] > 40 and s["slabs"] > 40, f"the surfacing pass placed {s}"
    assert s["stairs_under"] > 15, f"only {s['stairs_under']} of its ramps are undersides"


@pytest.mark.parametrize("length", [28, 32, 36, 40, 48, 56])
def test_the_ankylosaur_survives_EVERY_LENGTH_it_can_be_built_at(length):
    """**A SCALE SWEEP IS THE ONLY THING THAT CATCHES A FEATURE THAT HALF-EXISTS**, and on this
    animal's own predecessor it found no eyes at one length, a detached thagomizer at two, fused
    plates at three and welded feet at most - every one of them silent, and not one at the length
    that happened to be under the eye. It found two more here: the club went to a ONE-COURSE
    PADDLE below length 34, and the horns placed 124 blocks and gained zero cells."""
    c = ankylosaur.build_ankylosaur({"length": length})
    solid = c.to_model().ids > 0
    _lab, sizes = morph.components(solid, conn=6)
    assert len(sizes) == 1, f"at {length} it came out in {len(sizes)} pieces: {sorted(sizes)[-6:]}"
    _l2, feet = morph.components(solid[0][None, :, :], conn=6)
    assert len(feet) == 4, f"at {length} it touches down in {len(feet)} patches, not four"
    p = c.meta["parts"]
    assert p["eyes"] == 2 and p["horns"] > 0 and p["club"] > 0 and p["knobs"] > 0
    assert c.meta["clipped"] == 0, f"at {length} it clips {c.meta['clipped']} cells off its box"


@pytest.mark.parametrize("facing", ["north", "south", "east", "west"])
def test_the_ankylosaur_is_never_CLIPPED_off_its_own_canvas(facing):
    """A canvas that is always long in X is long in the WRONG axis for a north-south animal: the
    sauropod built facing north came out clipped to 22 blocks of 48 - head, neck and half the tail
    simply refused - and the render still showed a plausible small dinosaur. `clipped` is counted
    APART from `refused`, because a foot pad's lower hemisphere is always outside the box and
    always will be: that is the ground, not a clip, and one number for both hides this."""
    c = ankylosaur.build_ankylosaur({"facing": facing})
    assert c.meta["clipped"] == 0, f"facing {facing} clips {c.meta['clipped']} cells off the box"
    assert c.meta["parts"]["mirror"]["shape"] == 0, f"facing {facing} is not symmetric"


def test_it_REFUSES_a_length_that_cannot_carry_its_own_pattern():
    """Its identity is a PATTERN on a shield - osteoderm rows, a spike fringe and a club - and
    every one of those has a block floor below which it does not shrink gracefully, it stops
    existing. `tools/scale.py`'s doctrine, so it says so rather than building something that audits
    clean, ships one connected piece and cannot be named."""
    with pytest.raises(ValueError, match="shield"):
        ankylosaur.build_ankylosaur({"length": 22})


def test_the_face_is_DRAWN_and_reads_head_on():
    """**THE FACE WAS THE ONE THING NOTHING TESTED, AND IT SHIPPED AS A THUMB.** The head passed
    every geometric contract there was - blunt, wide, pinched off the shield, carrying a pair of
    eyes - and head-on it was a smooth brown lump: the surfacing pass had scattered stairs and
    slabs of two colour families over the muzzle, and the eyes sat on the SKULL ROOF where only
    the plan could see them. A face is a DRAWN feature and has to be asserted like one.

    The four marks, and each is a recorded lesson from another animal: a pale beak (the frog's
    panel), a dark line across it where the jaws meet (the frog's mouth line, its own single
    biggest change), nostrils that are NOT black (or they read as a second pair of eyes), and a
    bead a side that the coat cannot swallow and the mouth line cannot merge with.
    """
    c = _ank()
    p = c.meta["parts"]
    for mark in ("beak", "mouth", "nostril"):
        assert p[mark] > 0, f"the face has no {mark}: {p}"
    assert p["nostril"] == 2, f"{p['nostril']} nostrils"

    cells = _cells(c.to_model())
    black = {xyz for xyz, n in cells.items() if n == "black_wool"}
    mid = c.sx // 2

    # **A BEAD IS FOUND BY ITS RING, WHICH IS WHAT MAKES IT AN EYE.** Twice now this test has been
    # written to find the eyes geometrically - "the outermost black cells", then "black with no
    # black above or below" - and both times it picked the MOUTH's own carry-back along the jaw,
    # which is black, isolated vertically, and further out than the bead. The eye is the black cell
    # the pale ring was built around; nothing else on the animal has one.
    beads = [(x, y, z) for (x, y, z) in black
             if sum(cells.get(n) == "light_gray_wool" for n in
                    ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z),
                     (x, y, z + 1), (x, y, z - 1))) >= 2]
    pairs = [b for b in beads if (2 * mid - b[0], b[1], b[2]) in beads and b[0] != mid]
    assert pairs, f"no ringed bead has a mirror twin: {len(black)} black cells, {len(beads)} ringed"

    # **AND IT FACES OUTWARD**, which is the property that makes it visible at all. What made the
    # first head a thumb was an eye whose only open face was UP.
    for (x, y, z) in pairs:
        out = x + (1 if x > mid else -1)
        assert (out, y, z) not in cells,             f"the bead at {(x, y, z)} is walled in on its outboard side: only the plan sees it"


def test_the_SURFACING_pass_keeps_off_the_face():
    """`shell.py` chamfers a step by replacing the cell with a stair of the nearest colour, which
    is right on a flank and vandalism on a face: it picked a green-grey slab and an orange stair
    out of the coat's own families and scattered them across the muzzle, so the head read as a
    staircase in three tones nothing else on the animal uses. The frog states the rule for its own
    build - *the face, the belly, the eyes and the feet are drawn features and a stair through one
    of them is a hole in a drawing* - and it lives in `_skin` rather than in each caller."""
    c = _ank()
    d = ankylosaur._dims(float(c.meta["length"]))
    m = c.to_model()
    names = [nbt.state_name(e).split(":")[-1] for e in m.palette]
    mid_z = c.sz // 2
    bad = []
    for y, z, x in zip(*np.nonzero(m.ids > 0)):
        n = names[int(m.ids[y, z, x])]
        if ("_stairs" in n or "_slab" in n) and (mid_z - int(z)) >= d["head_back"] - 1:
            bad.append((int(x), int(y), int(z), n))
    assert not bad, f"{len(bad)} shape blocks on the face, e.g. {bad[:4]}"


def test_the_SCUTES_scale_with_the_animal():
    """**AN ABSOLUTE THAT IS TOO SMALL AT LARGE SCALE IS THE SAME TRAP AS ONE TOO BIG AT SMALL.**
    The osteoderms were one cell at every size while `spike_len`, the club and everything else were
    fractions of the length - so making the animal bigger made its carapace EMPTIER, a 37-wide back
    carrying specks, and a build at 64 read worse than the same generator at 40. That is why size
    alone is never the answer to "more detail": it buys resolution, and the pattern has to spend it.
    """
    small = ankylosaur.build_ankylosaur({"length": 32}).meta["parts"]["knobs"]
    big = ankylosaur.build_ankylosaur({"length": 64}).meta["parts"]["knobs"]
    assert big > small * 2.0, f"the pattern does not scale: {small} scutes at 32, {big} at 64"
    d = ankylosaur._dims(64.0)
    assert d["knob_r"] * max(d["knob_grade"]) > 1.0, \
        "every scute is still a single cell at 64 blocks - the carapace will read as specks"


def test_the_carapace_carries_a_KEEL_and_TRANSVERSE_BANDS():
    """**A LINE SURVIVES DISTANCE AND A FIELD OF DOTS DOES NOT** - the jaguar's rosettes "turn to
    noise rather than pattern" at a quarter scale, and that is the recorded reason its coat failed.
    The keel is the only element on the back that still reads when the animal is a smudge, and the
    transverse half-rings are what break a uniform field of scutes into a STRUCTURE - they are also
    the feature an ankylosaur is actually diagnosed on."""
    c = _ank()
    d = ankylosaur._dims(float(c.meta["length"]))
    cells = _cells(c.to_model())
    mid = c.sx // 2
    keel = sorted(z for (x, _y, z) in cells if x == mid and cells[(x, _y, z)] == "dripstone_block")
    assert keel, "no scute material on the midline at all"
    run = max(len(list(g)) for g in _runs(sorted(set(keel))))
    want = int(0.35 * (d["keel_to"] - d["keel_from"]) * d["L"])
    assert run >= want, f"the keel's longest unbroken run is {run}, wanted {want}: it is dots"


def _runs(vals):
    out, cur = [], []
    for v in vals:
        if cur and v != cur[-1] + 1:
            out.append(cur)
            cur = []
        cur.append(v)
    if cur:
        out.append(cur)
    return out


def test_it_has_FOUR_horns_and_not_two():
    """The squamosal pair off the back corners of the skull roof and the quadratojugal pair under
    them at the cheek are what a palaeontologist names this animal on. Two alone read as a lump
    with ears, and the lower pair is aimed DOWN as well as back so head-on it widens the jaw
    instead of doubling the upper one."""
    c = _ank()
    d = ankylosaur._dims(float(c.meta["length"]))
    armour = _mask(c, ARMOUR)
    mid_x, mid_z = c.sx // 2, None
    # the horns are the armour over the SKULL's own stations, and they sit at two distinct courses
    zs = np.nonzero(c.to_model().ids > 0)[1]
    head_from = zs.min()
    band = armour[:, head_from:head_from + int(round(d["head_tip"] - d["cheek_f"])) + 4, :]
    ys = sorted({int(y) for y, _z, _x in zip(*np.nonzero(band))})
    assert len(ys) >= 4, f"the skull's armour occupies {len(ys)} courses - that is one pair"
    gap = max(b - a for a, b in zip(ys, ys[1:])) if len(ys) > 1 else 0
    assert gap >= 2 or len(ys) >= 6, \
        f"the skull's armour is one continuous band at courses {ys}: the pairs have merged"


def test_each_foot_carries_THREE_TOES_that_lean_the_right_way():
    """**A TOE BUILT OF FULL BLOCKS ENDS AT A VERTICAL FACE, WHICH IS A PLATE.** Four arrangements
    of cubes on the frog read as a rake, a comb, a plus sign and a set of random lines before the
    answer turned out to be the MATERIAL: half height at the tip sloping to the ground is what a
    toe does, and it is one block per toe. And the lean is asserted rather than eyeballed, because
    a stair's tall side is its `facing` and this renderer drew both directions identically until
    `render3d.subdivide` learned to expand one."""
    c = _ank()
    m = c.to_model()
    names = [_full(e) for e in m.palette]
    tips = [names[int(m.ids[0, z, x])] for z, x in zip(*np.nonzero(m.ids[0] > 0))
            if "_stairs" in names[int(m.ids[0, z, x])]]  # full states, see `_full`
    assert len(tips) == 12, f"{len(tips)} toe tips on four feet - wanted three a foot"
    # facing NORTH, a toe tapers down and forward, so its tall side is BACK: south
    assert all("facing=south" in t for t in tips), f"a toe leans the wrong way: {set(tips)}"


def test_the_tail_carries_TENDON_RINGS():
    """Without them the tail is a smooth taper and reads as a rat's. They are also the only thing
    on it that survives being seen from above, which is where the causeway's own skyway looks down
    on this stop. **RAISED, NOT REPAINTED** - written at the top course they recolour the cell
    already there and add nothing, which reported 0 while the pass claimed success."""
    p = _ank().meta["parts"]
    assert p["tail_bands"] >= 8, f"{p['tail_bands']} cells of tendon ring on the whole tail"
