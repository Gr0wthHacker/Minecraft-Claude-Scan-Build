"""The two NEW sculptures on the isthmus - `gen/balloon.py` and `gen/wyrm.py`.

WHAT THIS FILE IS FOR. `tests/test_isthmus.py` already checks the causeway's own contracts over
whatever creatures `GAPS` happens to name, and it is right to be written that way. What it
cannot do is pin the two pieces THEMSELVES: that a balloon still has a gap under its envelope,
that a wyrm's head still stands proud of its hood, that neither of them has quietly grown a
lamp inside its own coat. Those are properties of the shapes, they are the properties that
would be lost first to a well-meant tweak, and every one of them is invisible to the audit, to
the bill of materials and to the component count.

TWO OF THESE EXIST BECAUSE THE BUG HAD ALREADY SHIPPED ONCE EACH:

    the wyrm's eye probe was a computed offset and landed on a course where the skull is two
      cells wide and - because of the half-cell centring - ASYMMETRIC about the midline. One
      side found a block, the other found air, and the piece shipped with ONE eye. Twice. No
      error, nothing in the audit, nothing in the count;
    the wyrm's first tail was a thin dark tip laid over a thicker sweep, and its last sphere
      came out at radius 0.62 as a ONE-CELL SECOND COMPONENT - the ear-tip failure, in a build
      that was clean everywhere else.
"""
from collections import Counter

import numpy as np
import pytest

from mcbuild import blocks, morph, nbt, nightlight, palette
from mcbuild.gen import balloon, isthmus, wyrm

# THE CAUSEWAY'S WYRM IS THE RETIRED SERPENT, NOT THE DEFAULT FORM, and this file has to say so
# explicitly. `wyrm.py` now defaults to the locked W1 threshold - a ribcage you walk through, with
# no coil, no hood and no eyes - so a maker that took the default would be testing a shape this
# causeway never sites. `tests/test_wyrm.py` owns that one. Spelt the same way `isthmus.py`
# spells it, so the two cannot drift into testing and siting different animals.
MAKERS = {"balloon": lambda **kw: balloon.build_balloon(kw),
          "wyrm": lambda **kw: wyrm.build_wyrm({"form": "serpent", **kw})}


def _cells(c):
    """{(x, y, z): name} in the canvas's OWN coordinates."""
    names = [nbt.state_name(e).split(":")[-1] for e in c.palette]
    ys, zs, xs = np.nonzero(c.ids > 0)
    return {(x, y, z): names[int(c.ids[y, z, x])]
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())}


def _new_specs():
    """The shipped specs for the two new pieces, read off `GAPS` rather than re-typed - a test
    that pins a scale the design does not actually site at pins nothing at all."""
    return [s for g in isthmus.GAPS for s in g["creatures"] if s["kind"] in MAKERS]


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


@pytest.mark.parametrize("spec", _new_specs(), ids=lambda s: s["kind"])
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
