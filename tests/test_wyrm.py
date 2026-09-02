"""WYRM'S CROSSING - the locked W1 threshold in `gen/wyrm.py`.

WHAT THIS FILE PINS, AND WHY EACH OF IT IS INVISIBLE TO EVERYTHING ELSE IN THE PIPELINE.

`PARK_VISUAL_AND_BUDGET_SPEC.md` locks this setpiece to a partial skull, 4-6 articulated ribs,
broken spine segments, dark recesses and one rune panel, at 52-68 x 20-28 x 14-20 and 7,000-
10,000 blocks; `PARK_FINAL_ARCHITECTED_PLAN.md` and the W1 card add a continuous 5-wide public
transit, three rune inputs at player height in a SIDE alcove, and service behind the rim. Every
one of those is a shape or an arrangement, and the audit, the bill of materials, the component
count and every render in this repo pass a build that gets all of them wrong.

AND THE FIRST TEST HERE IS A NEGATIVE ONE, WHICH IS THE UNUSUAL PART. The form this generator
used to build - a free-standing reared serpent on a milestone - is the spec's FIRST rejection
condition, and it is a genuinely good sculpture: one piece, correctly banded, nameable in a
thumbnail. Nothing measurable was wrong with it. So the only thing that can stop it coming back
is a test that says, in as many words, that this module does not produce a coil.

THE SECOND UNUSUAL ONE IS THE FACING. `facing` was accepted and did nothing for a while - every
cardinal returned the identical 7,293 blocks with the length always on z - which is this repo's
most repeated failure shape, and on this module it is load-bearing: the Prism Reach is 45 blocks
along U against a lot 63 along V, so a 60-long crossing only fits with its length on x. A
parameter that is accepted and does nothing needs a test that MEASURES the difference.

The retired serpent still exists behind `form: "serpent"` because `isthmus.GAPS` sites it on the
causeway; `tests/test_causeway_sculptures.py` owns that shape. Nothing here may reach it.
"""
from collections import Counter

import numpy as np
import pytest

from mcbuild import blocks, morph, nbt, palette
from mcbuild.gen import GENERATORS, kit, wyrm

# the spec's own envelope, transcribed once so no test re-types half of it
LONG = (52, 68)
HIGH = (20, 28)
DEEP = (14, 20)
BUDGET = (7000, 10000)

CARDINALS = ["north", "east", "south", "west"]


def _build(**kw):
    """The SHIPPED default, at the SHIPPED default scale. A test that quietly passes a smaller
    scale to make an envelope fit is testing a build nobody generates."""
    return wyrm.build_wyrm({"at": [0, 0, 0], **kw})


def _cells(c):
    """{(x, y, z): name} in the canvas's OWN coordinates."""
    names = [nbt.state_name(e).split(":")[-1] for e in c.palette]
    ys, zs, xs = np.nonzero(c.ids > 0)
    return {(x, y, z): names[int(c.ids[y, z, x])]
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())}


def _props(c, pt):
    """One built cell's own block state."""
    x, y, z = (int(v) for v in pt)
    pr = c.palette[int(c.ids[y, z, x])].value.get("Properties")
    return {k: v.value for k, v in pr.value.items()} if pr else {}


def _in_box(pt, box):
    (x0, z0), (x1, z1) = box
    return x0 <= pt[0] <= x1 and z0 <= pt[2] <= z1


def _path_box(c):
    pa = c.meta["path"]
    return [[pa["x_lo"], pa["z_lo"]], [pa["x_hi"], pa["z_hi"]]]


def _bbox(ids):
    ys, zs, xs = np.nonzero(ids > 0)
    return (int(xs.max() - xs.min() + 1),
            int(ys.max() - ys.min() + 1),
            int(zs.max() - zs.min() + 1))


# ------------------------------------------------------------------ the rejected form

def test_the_generator_defaults_to_the_CROSSING_and_not_to_the_serpent():
    """`GENERATORS['wyrm'].build(...)` is what every caller in this repo reaches for and what a
    config gets when it names this generator. The locked form has to be the one that comes out of
    the DEFAULT, or the rejection is a comment rather than a decision."""
    c = GENERATORS["wyrm"].build({"at": [0, 0, 0]}, None)
    assert c.meta["form"] == "wyrm_crossing"
    assert wyrm.WYRM["form"] == "crossing"


def test_NO_COIL_AND_NO_FREE_STANDING_SNAKE_IS_PRODUCED():
    """THE SPEC'S FIRST REJECTION CONDITION, PINNED AS GEOMETRY AND NOT AS A LABEL.

    A coil, a helix or a snake body is CONTINUOUS along its own length: take any horizontal slice
    through the middle of it and you get one run of cells that goes on and on. A ribcage is the
    opposite thing - at mid height it is nothing but the ribs, so the slice breaks into one
    cluster per rib with real air between them. That difference survives any amount of retuning
    and it is exactly what would be lost the moment somebody wound a body back through here,
    which is why it is measured rather than asserted off `meta`.

    The two cheap checks come with it: the recorded form, and the absence of the serpent's own
    feature keys - a build that starts reporting `coil_stations` again has a coil in it.
    """
    c = _build()
    f = c.meta["features_built"]
    assert c.meta["form"] == "wyrm_crossing"
    for gone in ("coil_stations", "hood", "hood_rim", "eyespots", "turns", "bands"):
        assert gone not in f, f"the crossing reports {gone!r} - that is the rejected serpent"

    ids = c.to_model().ids
    y_cap = c.meta["path"]["deck_y"] + 1 + 3
    mid = (y_cap + int(ids.shape[0]) - 1) // 2          # mid height, above every rim course
    occupied = sorted({int(z) for z in np.nonzero(ids[mid] > 0)[0]})
    assert occupied, f"nothing at all stands at mid height y={mid}"
    gaps = [b - a - 1 for a, b in zip(occupied, occupied[1:]) if b - a > 1]
    runs = len(gaps) + 1
    # one run per rib, plus at most one for the head, which legitimately fills a quarter of the
    # length at this height. Derived from the rib count rather than typed, so moving that count
    # inside the spec's own 4-6 cannot silently turn this into a test of nothing.
    assert f["ribs"] <= runs <= f["ribs"] + 1, \
        f"mid height y={mid} breaks into {runs} runs along the crossing against {f['ribs']} " \
        "ribs - a continuous body at mid height is a snake, which is the rejected form"
    # THE GAPS ARE THE ASSERTION, not the occupancy: the skull legitimately fills a whole quarter
    # of the length at this height, so a flat "less than half is solid" reads a correct ribcage
    # as a body. What a coil can never have is real air BETWEEN consecutive ribs.
    assert len([g for g in gaps if g >= 2]) >= f["ribs"] - 1, \
        f"the gaps at mid height are {gaps} - consecutive ribs are not separated by open air"


# ------------------------------------------------------------------ envelope and budget

def test_it_fits_the_locked_size_envelope():
    """52-68 long, 20-28 high, 14-20 deep - and the height ceiling is the load-bearing one: "low
    enough to FRAME rather than create another crown". Only the Sky Lift, the Mine Ridge and the
    Prism Spire are allowed into the crown bands."""
    across, high, along = _bbox(_build().to_model().ids)
    assert LONG[0] <= along <= LONG[1], f"{along} long, wanted {LONG}"
    assert HIGH[0] <= high <= HIGH[1], f"{high} high, wanted {HIGH}"
    assert DEEP[0] <= across <= DEEP[1], f"{across} deep, wanted {DEEP}"


def test_it_costs_what_the_ledger_budgeted():
    """7,000-10,000 blocks INCLUDING the rim anchors, the rune alcove and the service enclosure -
    so this is measured on the whole model and not on the sculpture alone.

    THE FLOOR IS THE CONSTRAINT AND THE CEILING IS A GUARD. Jack's own direction is that over
    budget is fine when the extra buys something real, so nothing here should ever be trimmed to
    protect this number - deeper rib articulation, a heavier skull or a more legible rune alcove
    all beat a tidier total. What the floor catches is the opposite failure: a threshold with no
    mass in it, which at this scale reads as scaffolding rather than as architecture."""
    n = int((_build().to_model().ids > 0).sum())
    assert BUDGET[0] <= n <= BUDGET[1], f"{n} blocks, wanted {BUDGET}"


# ------------------------------------------------------------------ the facing

def test_FACING_ACTUALLY_TURNS_THE_BUILD():
    """IT DID NOT, FOR A WHILE, AND THAT WAS THE WHOLE PROBLEM. Every cardinal returned an
    identical 7,293-block model in a (17, 27, 60) box: `facing` was accepted, recorded and inert,
    which is this repo's most repeated failure shape - a thing that does nothing, quietly.

    Here it decides whether the module fits its own plot. The Prism Reach is 45 blocks along U
    and the ledger puts Wyrm's Crossing at V18-80 by U390-425 - 63 along V, 36 along U - so a
    52-68 length can only lie on V, which is local x. At 60-along-z the build overflows its lot
    by 25 blocks and there is no orientation of that reach in which it fits.

    So the property is measured: an odd quarter turn puts the LENGTH on x and the depth on z,
    an even one leaves them, and the block count never moves because a rotation is a bijection.
    """
    base = int((_build(facing="north").to_model().ids > 0).sum())
    boxes = {}
    for f in CARDINALS:
        c = _build(facing=f)
        boxes[f] = _bbox(c.to_model().ids)
        assert int((c.to_model().ids > 0).sum()) == base, \
            f"facing={f} changed the block count - a turn is a bijection, not a rebuild"
        assert c.meta["facing"] == f
    for f in ("north", "south"):
        across, _high, along = boxes[f]
        assert LONG[0] <= along <= LONG[1] and DEEP[0] <= across <= DEEP[1], \
            f"facing={f} is {across} x {along} - a half turn must leave the length on z"
        assert _build(facing=f).meta["long_axis"] == "z"
    for f in ("east", "west"):
        across, _high, along = boxes[f]
        assert LONG[0] <= across <= LONG[1], \
            f"facing={f} is {across} on x - a quarter turn has to put the LENGTH there"
        assert DEEP[0] <= along <= DEEP[1], \
            f"facing={f} is {along} on z - the depth belongs there after a quarter turn"
        assert _build(facing=f).meta["long_axis"] == "x"
    # ...and the lot it has to fit: 63 along V by 36 along U. The turned build is the only one
    # that does, which is the whole reason this parameter had to stop being inert.
    assert boxes["east"][0] <= 63 and boxes["east"][2] <= 36, \
        f"turned east the crossing is {boxes['east']} and does not fit its own lot"


@pytest.mark.parametrize("face", CARDINALS)
def test_a_facing_ROTATES_rather_than_COPIES(face):
    """EVERY DIRECTIONAL STATE TURNS WITH THE GEOMETRY. Written the lazy way a turn assigns each
    cell's state verbatim to its new home, and the corbels then lean out of the wall they grow
    from, the levers hang on nothing, and the sign faces the block it is nailed to. `render3d`
    draws a wrong facing exactly like a right one, so nothing offline in this repo would show it
    - which is why this is asserted rather than looked at.

    Measured as a SET on the whole build: at north the crossing's stateful blocks look east/west,
    and a quarter turn has to move that set to north/south. A copy leaves it where it was.
    """
    c = _build(facing=face)
    ids = c.to_model().ids
    seen = {}
    for i, e in enumerate(c.palette):
        n = int((ids == i).sum())
        if not n or i == 0:
            continue
        name = nbt.state_name(e).split(":")[-1]
        pr = e.value.get("Properties")
        got = ({k: v.value for k, v in pr.value.items()} if pr else {}).get("facing")
        if name in ("stone_brick_stairs", "lever", "iron_trapdoor", "oak_wall_sign") and got:
            seen.setdefault(name, set()).add(got)
    assert set(seen) == {"stone_brick_stairs", "lever", "iron_trapdoor", "oak_wall_sign"}
    want = {"north", "south"} if face in ("east", "west") else {"east", "west"}
    for name, faces in seen.items():
        assert faces <= want, \
            f"at facing={face} the {name} states are {sorted(faces)} - they were not turned"
    # the corbels still come in mirrored PAIRS within one build: a turn must not flatten that
    assert seen["stone_brick_stairs"] == want, \
        "the corbels no longer lean opposite ways on the two flanks"


def test_a_half_turn_is_exactly_kit_s_two_mirrors():
    """`kit.flip` is the obvious helper to reach for and it is the WRONG one: a mirror reverses
    handedness, so it turns an `inner_left` stair into an `inner_right` one and swaps a door's
    hinge, where a rotation preserves both. What the two genuinely share is that a HALF turn is
    both of kit's mirrors composed - so that identity is asserted here, and the two files cannot
    drift apart on which direction is opposite which."""
    for d in CARDINALS:
        both = kit.flip(kit.flip({"facing": d}, "x"), "z")["facing"]
        assert wyrm.turn_props({"facing": d}, 2)["facing"] == both
    # ...and the differences are real and deliberate
    assert wyrm.turn_props({"shape": "inner_left"}, 1)["shape"] == "inner_left", \
        "a rotation must not swap a stair's corner hand - only a mirror does that"
    assert wyrm.turn_props({"axis": "x"}, 1)["axis"] == "z", \
        "a rotation must swap a pillar's axis - a mirror leaves it alone"
    assert wyrm.turn_props({"axis": "x"}, 2)["axis"] == "x"


# ------------------------------------------------------------------ connectivity

@pytest.mark.parametrize("face", CARDINALS)
def test_it_is_ONE_6_CONNECTED_PIECE(face):
    """MEASURED, NEVER ASSUMED, AND AT EVERY ORIENTATION IT CAN BE SITED AT. A feature whose
    cells are only DIAGONAL neighbours is not connected, and that has cost this project ear tips,
    ossicones, a detached mane, a floating dorsal fin and a whole dragonfly - every one of them in
    a build the audit, the BOM and the component count called clean. The broken spine is the place
    it would happen here: the gaps between vertebrae are the feature, so every segment has to be
    seated on the rib under it rather than on the one beside it."""
    ids = _build(facing=face).to_model().ids
    _lab, sizes = morph.components(ids > 0, conn=6)
    assert len(sizes) == 1, \
        f"facing={face} came out in {len(sizes)} pieces: {sorted(sizes, reverse=True)[:6]}"


# ------------------------------------------------------------------ the form itself

def test_it_has_four_to_six_articulated_ribs_and_they_ROOT_INTO_THE_RIM():
    """The spec asks for 4-6 ribs and for them to root into the bridge rim - "structural
    attachment, not floating" - which is what separates a ribcage from bones lying about, the
    second rejection condition. So the count is checked AND the feet are: every rib's lowest bone
    course has to stand on the rim's own masonry, not out over the deck or over the path."""
    c = _build()
    f = c.meta["features_built"]
    assert 4 <= f["ribs"] <= 6, f"{f['ribs']} ribs, the spec allows 4-6"
    assert f["spine_segments"] == f["ribs"], \
        "a vertebra survives only where a rib holds it up - that is what makes the spine broken"

    cells = _cells(c)
    cap_y = c.meta["path"]["deck_y"] + 1 + 3
    rim_x = {x for (x, y, _z), n in cells.items()
             if y == cap_y and n in ("stone_bricks", "stone_brick_stairs")}
    assert rim_x, "there is no rim cap course for a rib to root into"
    # THE HEAD'S CHIN LANDS ON THE SAME COURSES A RIB FOOT DOES, out of the same block, so a
    # check written on block names alone reads the mandible as a rib standing in the wrong place.
    # The generator records the skull's own box for exactly this.
    skull = c.meta["skull_box"]
    feet = {(x, z) for (x, y, z), n in cells.items()
            if n in ("bone_block", "light_gray_wool") and y in (cap_y, cap_y + 1)
            and not _in_box((x, y, z), skull)}
    assert feet, "no rib touches the rim cap at all - the ribcage is floating"
    for x, z in feet:
        assert min(abs(x - r) for r in rim_x) <= 1, \
            f"a rib foot at x={x} stands clear of the rim ({sorted(rim_x)})"
    box = _path_box(c)
    assert not any(_in_box((x, 0, z), box) for x, z in feet), \
        "a rib foot stands inside the public path"


def test_it_has_a_partial_skull_with_dark_recesses():
    """"Partial skull/head" plus "dark recesses". Both are shapes: the skull is BROKEN - the back
    of the braincase is open and the void inside it shows at the cut - and the recesses are real
    black-wool cells rather than a note in a docstring. Broken along the crossing rather than
    across it, deliberately, so the head is still a mirror of itself and there is something left
    to check the symmetry against."""
    c = _build()
    f = c.meta["features_built"]
    assert f["skull"] == 1
    assert f["skull_break"] > 0, "the braincase is closed - that is a bust, not a partial skull"
    assert f["eye_sockets"] >= 2, "the skull has fewer than two eye sockets"
    assert f["jaw_buttresses"] == 2, "the skull is not seated on the rim on both sides"
    assert f["recesses"] > 0, "the rim has no dark recesses in its face"
    n = Counter(_cells(c).values())
    assert n["black_wool"] > 50, f"only {n['black_wool']} void cells anywhere in it"
    assert n["bone_block"] > 500, "there is barely any skeleton in this skeleton"


@pytest.mark.parametrize("face", CARDINALS)
def test_the_public_5_WIDE_BYPASS_IS_NEVER_BLOCKED(face):
    """"Any blocked main route" is a rejection condition and the W1 card is explicit: normal
    5-wide Prism transit CONTINUES. The prism is five columns wide and three courses tall for the
    whole length, and it is checked at every orientation, because the alcove, the screen and the
    service hatch are one-sided and an error in the turn puts one of them in the road.

    The generator raises on an intrusion of its own accord; this exists so that the raise is not
    the only thing standing between a blocked route and a shipped design."""
    c = _build(facing=face)
    ids = c.to_model().ids
    pa = c.meta["path"]
    prism = ids[pa["y_lo"]:pa["y_hi"] + 1, pa["z_lo"]:pa["z_hi"] + 1, pa["x_lo"]:pa["x_hi"] + 1]
    wide = (pa["x_hi"] - pa["x_lo"] + 1, pa["z_hi"] - pa["z_lo"] + 1)
    across, along = wide if c.meta["across_axis"] == "x" else wide[::-1]
    assert across == 5, f"the declared bypass is {across} wide, not five"
    assert along >= LONG[0], f"the bypass runs {along}, not the whole length of the crossing"
    assert not (prism > 0).any(), \
        f"{int((prism > 0).sum())} cells stand inside the public bypass at facing={face}"
    # ...and it is a route because you can walk on it: the deck is unbroken beneath the prism
    deck = ids[pa["deck_y"], pa["z_lo"]:pa["z_hi"] + 1, pa["x_lo"]:pa["x_hi"] + 1]
    assert (deck > 0).all(), "the bypass has holes in its own floor"


# ------------------------------------------------------------------ the riddle

def test_there_is_ONE_rune_panel_and_it_faces_the_public_approach():
    """"One visible rune panel", and "riddle cues unreadable from public approach" is the fourth
    rejection condition. So the panel is a real block of rune colour on the alcove's back wall,
    beyond the verge rather than in the road, and it is lit."""
    c = _build()
    f = c.meta["features_built"]
    assert f["rune_panel"] == 1, "the crossing has more than one rune panel, or none"
    assert f["rune_panel_cells"] >= 9, "the panel is too small to be a panel"
    n = Counter(_cells(c).values())
    rune = n["light_blue_wool"] + n["cyan_wool"] + n["blue_wool"]
    assert rune >= 3, f"only {rune} cells of rune colour anywhere"
    al = c.meta["alcove"]
    assert not _in_box(al["panel"], _path_box(c)), \
        "the panel's wall stands in the public path rather than beyond the verge"
    assert _cells(c).get(tuple(al["panel"])) in ("light_blue_wool", "cyan_wool", "blue_wool"), \
        "the recorded panel cell is not a rune block"
    assert f["rune_lamps"] >= 1, "the panel is not lit; a cue nobody can read is not a cue"


@pytest.mark.parametrize("face", CARDINALS)
def test_THREE_rune_inputs_stand_at_PLAYER_HEIGHT_in_the_side_alcove(face):
    """Three inputs, at player height, in a SIDE alcove - the W1 card's own words. Height is
    measured from the ALCOVE'S OWN FLOOR and not from the canvas, because the two differ by the
    whole abutment and a lever four courses underground would pass a check written against y=0.

    Checked at every orientation: the alcove is the one deliberately one-sided thing in this
    build, so it is the one thing an error in the turn can put somewhere silly.
    """
    c = _build(facing=face)
    inputs = c.meta["rune_inputs"]
    assert len(inputs) == 3, f"{len(inputs)} rune inputs, the plan asks for three"
    assert c.meta["features_built"]["rune_inputs"] == 3
    assert len({tuple(i) for i in inputs}) == 3, "two of the three inputs are the same cell"

    cells = _cells(c)
    al, floor = c.meta["alcove"], c.meta["alcove"]["floor_y"]
    for (x, y, z) in inputs:
        assert cells.get((x, y, z)) == "lever", f"the input at {(x, y, z)} is not an input"
        assert 1 <= y - floor <= 2, \
            f"an input stands {y - floor} above the alcove floor, not at player height"
        assert _in_box((x, y, z), al["box"]), "an input is outside the alcove it belongs to"
        assert not _in_box((x, y, z), _path_box(c)), "an input stands in the public path"
        # A LEVER IS AN ATTACHED BLOCK and its `facing` is the way it LOOKS, so the wall it hangs
        # on is one step the OTHER way. Written as a fixed +x this passes only at the single
        # orientation it was written at - which is the whole class of bug the parametrisation
        # here exists to catch.
        dx, dz = wyrm._VEC[_props(c, (x, y, z))["facing"]]
        assert (x - dx, y, z - dz) in cells, f"the lever at {(x, y, z)} hangs on nothing"


def test_the_alcove_is_off_the_route_and_rejoins_it():
    """"Optional side alcove offers a riddle and reconnects ahead", with the public bypass always
    visible. The bay is screened from the verge, and the screen is open at BOTH ends - one to walk
    in by and one to rejoin - which is the 2-wide rejoin the plan asks for."""
    c = _build()
    f = c.meta["features_built"]
    (_ax0, az0), (_ax1, az1) = c.meta["alcove"]["box"]
    assert f["alcove"] > 0, "nothing was cut back for the alcove"
    assert f["screen"] > 0, "the alcove is not screened from the verge at all"
    assert az1 - az0 + 1 >= 9, "the bay is too short to stand three inputs in"
    ids = c.to_model().ids
    pa = c.meta["path"]
    screen_x = pa["x_hi"] + 2
    band = [z for z in range(az0 - 1, az1 + 2) if ids[pa["deck_y"] + 1, z, screen_x] == 0]
    assert len(band) >= 4, f"the screen leaves {len(band)} open cells - no entry and no rejoin"


def test_service_lives_behind_the_rim_and_not_on_the_route():
    """"Service/reset lives behind the rim" and the ledger counts the service enclosure inside
    this setpiece's budget, so it is a real room rather than a promise. Carved out of the rim's
    own mass, on the far side from the riddle, and reached by a hatch rather than by a hole in the
    public deck."""
    c = _build()
    f = c.meta["features_built"]
    assert f["service_enclosure"] == 1
    assert f["service_void"] >= 12, "the service enclosure has no room to stand up in"
    hatch = [k for k, n in _cells(c).items() if n == "iron_trapdoor"]
    assert len(hatch) == 1, f"{len(hatch)} service hatches"
    assert not _in_box(hatch[0], _path_box(c)), "the service hatch opens in the public path"
    assert not _in_box(hatch[0], c.meta["alcove"]["box"]), \
        "the service hatch is inside the riddle bay, on the wrong side of the crossing"


# ------------------------------------------------------------------ symmetry and materials

def test_it_is_symmetric_where_symmetry_is_INTENDED():
    """SYMMETRIC BY CONSTRUCTION, AND THE ASYMMETRY IS DECLARED RATHER THAN TOLERATED. Rim, deck,
    colonnade, ribs, spine and skull are drawn once per side from a signed multiplier; the alcove
    and the service crawl are deliberately one-sided and the band they occupy is recorded as
    `asym_box`, so this excludes exactly that and nothing else.

    IT CAUGHT TWO REAL BUGS THE DAY IT WAS WRITTEN, both of the same shape. `sphere` measures from
    a cell's own centre at x+0.5, so the mirror axis of a swept shape is `cx + 0.5` and not `cx` -
    centred on the integer column, every rib came out a cell wider on one flank than the other.
    And the skull's ragged break was hashed on x, so the two flanks broke in different places:
    eight cells of asymmetry in the one feature the whole piece is read by, at the one edge nobody
    would think to look at.
    """
    c = _build(facing="north")                    # the canonical build: the mirror axis is x
    ids = c.to_model().ids
    (_ax0, lo), (_ax1, hi) = c.meta["asym_box"]
    W = ids.shape[2]
    bad = [(int(z), int(y), int(x))
           for z in range(ids.shape[1]) if not lo <= z <= hi
           for y in range(ids.shape[0]) for x in range(W)
           if (ids[y, z, x] > 0) != (ids[y, z, W - 1 - x] > 0)]
    assert not bad, f"{len(bad)} cells break the mirror outside the declared band, e.g. {bad[:4]}"


def test_the_mirrored_corbels_LEAN_OPPOSITE_WAYS():
    """A MIRROR FLIPS A FACING, IT DOES NOT COPY IT. Written the obvious way, the two flanks get
    the same state and half the corbels lean out of the wall they are supposed to grow from -
    invisible in every render this repo has, because `render3d` drew a stair's two facings
    identically until the day it learned about shapes."""
    c = _build(facing="north")
    cells = _cells(c)
    ids = c.to_model().ids
    W = ids.shape[2]
    (_ax0, lo), (_ax1, hi) = c.meta["asym_box"]
    stairs = [(x, y, z) for (x, y, z), n in cells.items()
              if n == "stone_brick_stairs" and not lo <= z <= hi]
    assert stairs, "there are no corbels to check a mirror against"
    for (x, y, z) in stairs:
        mine = _props(c, (x, y, z))["facing"]
        twin = _props(c, (W - 1 - x, y, z))["facing"]
        assert {mine, twin} == {"east", "west"}, \
            f"the corbel at {(x, y, z)} faces {mine} and its mirror faces {twin} - that is a copy"


def test_every_block_is_1_19_spendable_and_not_dear():
    """The three axes this project keeps separate on purpose: does the block EXIST, does the 1.19
    SERVER have it (the client is 26.2), and is it CURRENCY here - dirt and grass are money on
    this skyblock and passed every other check in the pipeline while the lion shipped with a coat
    of 5,173 of them. Plus the material policy: nothing expensive as bulk, which for a threshold
    built almost entirely of stone means nothing expensive at all."""
    n = Counter(_cells(_build()).values())
    for name in n:
        assert blocks.exists(name), f"the crossing places {name}, which is not a block"
        assert blocks.available(name), f"{name} is not on the 1.19 server"
        assert blocks.spendable(name), f"{name} is CURRENCY on this server"
        assert palette.tier(name) != "expensive", f"{name} is expensive tier"
    dear = sum(k for name, k in n.items() if palette.tier(name) != "cheap")
    assert dear < 0.16 * sum(n.values()), \
        f"{dear} of {sum(n.values())} cells are above cheap tier - the policy allows 10-16% okay"


@pytest.mark.parametrize("face", CARDINALS)
def test_every_block_state_it_emits_is_legal(face):
    """An illegal state fails here rather than in Litematica an hour later, silently refusing to
    place. At every orientation, because the turn REWRITES every directional state and a rewrite
    that produced `facing=up` on a stair would look exactly like one that did not."""
    c = _build(facing=face)
    ids = c.to_model().ids
    bad = []
    for i, e in enumerate(c.palette):
        if i == 0 or not (ids == i).any():
            continue
        name = nbt.state_name(e).split(":")[-1]
        pr = e.value.get("Properties")
        got = blocks.validate(name, {k: v.value for k, v in pr.value.items()} if pr else {})
        if got:
            bad.append((name, got))
    assert not bad, f"illegal block states at facing={face}: {bad}"


# ------------------------------------------------------------------ the parameter surface

def test_the_at_facing_and_scale_surface_still_loads():
    """`at`, `facing` and `scale` are the parameter surface every existing caller and config
    speaks, and `face` is the legacy spelling `isthmus.py` passes: +1 was the unturned build and
    -1 the turned one, so they map onto north and south. An unreadable facing RAISES rather than
    defaulting quietly - a threshold pointing the wrong way is the one mistake no render in this
    repo can see."""
    assert wyrm.build_wyrm({"at": [10, 20, 30]}).world_origin == (10, 20, 30)
    assert wyrm.build_wyrm({"stand": [0, 64, 0]}).world_origin[1] == 64
    assert wyrm.build_wyrm({"facing": "north"}).meta["facing_vec"] == [0, -1]
    assert wyrm.build_wyrm({"facing": "east"}).meta["facing_vec"] == [1, 0]
    assert wyrm.build_wyrm({"facing": "south"}).meta["facing_vec"] == [0, 1]
    assert wyrm.build_wyrm({"facing": "west"}).meta["facing_vec"] == [-1, 0]
    assert wyrm.build_wyrm({"face": 1}).meta["facing"] == "north"
    assert wyrm.build_wyrm({"face": -1}).meta["facing"] == "south"
    with pytest.raises(ValueError):
        wyrm.build_wyrm({"facing": "sideways"})
    with pytest.raises(ValueError):
        wyrm.build_wyrm({"form": "snake"})
    # scale moves the whole thing together rather than one axis of it
    big, base = _bbox(wyrm.build_wyrm({"scale": 1.1}).to_model().ids), _bbox(_build().to_model().ids)
    assert big[2] > base[2] and big[1] > base[1]


def test_the_retired_serpent_is_reachable_ONLY_by_name():
    """It is kept because `isthmus.GAPS` still sites it and `test_isthmus` requires two creatures
    a span; the two assets Jack removed from that file are the only replacements that exist, so
    deleting it here would silently cost the causeway a stop. RECORDED, NOT DEFAULTED - a flag
    with no reason beside it gets removed by whoever finds it inconvenient, and a retired form
    that is still the default is not retired at all."""
    s = wyrm.build_wyrm({"form": "serpent"})
    assert s.meta["form"] == "serpent"
    assert "coil_stations" in s.meta["features_built"]
    assert _build().meta["form"] == "wyrm_crossing"
