"""THE SITTING CORGI - the contracts, and the reason each one exists.

Every assertion here was a build that shipped `problems: 0`, a correct bill of materials and a
plausible render, and was wrong. That is the whole reason for the file: this repo's own recorded
failure mode for a sculpture is not a crash, it is a clean audit and an animal nobody can name.

**AND THESE TESTS PIN DECISIONS, NOT A SNAPSHOT.** CLAUDE.md records the trap five times - a test
that asserts a cell COUNT fails the moment the design improves - so nothing here compares against a
number taken from a build. What is pinned is the geometry of a corgi, the separation of the marks
on its face, and the properties that were violated on the way here.
"""
import math

import pytest

from mcbuild import blocks, nbt, palette
from mcbuild.gen import corgi, loft

SIZES = (24, 30, 32, 40, 48)
FACINGS = ("north", "south", "east", "west")


def build(H=32, facing="north"):
    return corgi.build_corgi({"height": H, "facing": facing})


def frame(c, H, facing="north"):
    """The animal's own axes on a finished canvas, READ OFF THE BUILD rather than re-derived.

    This used to repeat `build_corgi`'s canvas arithmetic line for line, and that is the trap this
    repo pulled `Work.sortKey` out of a test for: a checker that re-implements its subject grades a
    copy of it, agrees with itself perfectly, and breaks on any change to the original. The day the
    tail stopped being placed at a computed station, 55 assertions failed on the duplicate rather
    than on the animal.
    """
    return loft.Frame(c, *c.meta["frame_origin"], facing, corgi.HIDE), corgi._dims(float(H))


def components(cells):
    seen, n = set(), 0
    for start in cells:
        if start in seen:
            continue
        n += 1
        stack = [start]
        seen.add(start)
        while stack:
            v, y, u = stack.pop()
            for dv, dy, du in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (v + dv, y + dy, u + du)
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
    return n


def names_of(c):
    return [nbt.state_name(e).split(":")[-1].split("[")[0] for e in c.reg.palette]


def name_at(c, v, y, u):
    return names_of(c)[int(c.ids[y, u, v])]


# ------------------------------------------------------------------ it survives every size it has


@pytest.mark.parametrize("H", SIZES)
@pytest.mark.parametrize("facing", FACINGS)
def test_it_is_ONE_PIECE_at_every_size_and_every_facing(H, facing):
    """A sweep, because **a defect is routinely invisible at the size being looked at.**

    The stegosaur's tail spikes came apart at exactly two lengths out of seven and not at the one
    on screen; the pterosaur split at three separate spans, each time at a size its neighbours
    passed. A single build is not evidence about a generator.
    """
    c = build(H, facing)
    assert components(corgi._solid_cells(c)) == 1


@pytest.mark.parametrize("H", SIZES)
@pytest.mark.parametrize("facing", FACINGS)
def test_NOTHING_IS_CLIPPED_OFF_THE_END_OF_THE_CANVAS(H, facing):
    """**A refusal off the end of the box is the sauropod's own recorded disaster.**

    Built facing north it came out clipped to 22 blocks of 48 - head, neck and half the tail simply
    refused - and the render still showed a plausible small dinosaur, because what survived was the
    near end. The only symptom was a count nobody was reading, so it is read here.

    `refused` is deliberately NOT asserted: a paw is a ball centred on the course the animal stands
    on, so its lower half is always below the floor. That is the ground, not a clip.
    """
    c = build(H, facing)
    assert c.meta["clipped"] == 0


@pytest.mark.parametrize("H", SIZES)
@pytest.mark.parametrize("facing", FACINGS)
def test_it_is_EXACTLY_SYMMETRIC_in_shape_AND_in_colour(H, facing):
    """Symmetric by construction is not symmetric.

    The squid was built for both signs on every part and came out 5,375 cells adrift, because a
    limb swept from a float centre mirrors about a column's EDGE rather than its middle. And the
    COLOUR half is not a lesser check: the frog's coat drifts each carried their own signed offset
    and the animal read as dented down one side while its shape was exact. Here it caught the ears
    OVERLAPPING ACROSS THE MIDLINE at every single size - a guard written against the centre column
    is not a guard against crossing it.
    """
    m = build(H, facing).meta["parts"]["mirror"]
    assert m["shape"] == 0
    assert m["colour"] == 0


@pytest.mark.parametrize("H", SIZES)
def test_EVERY_PART_PLACES_REAL_CELLS(H):
    """**A build with a part missing is still one piece with a clean audit.**

    The frog shipped with `forelegs: 0` in its own sidecar and nobody noticed; the ankylosaur's
    horns reported 124 placements and gained ZERO cells, because every one of them landed inside
    the skull. Counts here are unique cells diffed off the canvas, never `put()` calls, so a part
    that is entirely swallowed reads as the zero it is.
    """
    p = build(H).meta["parts"]
    for part in ("body", "head", "muzzle", "legs", "hind", "stump", "ears", "toes",
                 "nose", "mouth"):
        assert p.get(part), f"{part} placed no cells at height {H}"
    assert p["eyes"] == 2


def test_it_REFUSES_a_size_its_ears_cannot_exist_at():
    """The floor is the EAR, which is `tools/scale.py`'s doctrine: an animal's critical size is the
    largest of its features' own floors, not a number chosen for the biggest feature."""
    with pytest.raises(ValueError, match="ears"):
        corgi.build_corgi({"height": 20})


def test_a_facing_must_be_a_real_ONE():
    with pytest.raises(ValueError, match="facing"):
        corgi.build_corgi({"height": 32, "facing": "up"})


# ------------------------------------------------------------------------------ it is a SITTING dog


@pytest.mark.parametrize("H", SIZES)
def test_the_SILHOUETTE_DOES_NOT_DECOMPOSE_INTO_LIMBS(H):
    """The one property that keeps this animal off the retired list.

    Eight mammals, a stegosaur and an ankylosaur were retired here for the same measured reason -
    *"the line is not the species, it is whether the silhouette decomposes into LIMBS"* - and what
    makes a SITTING corgi different is that the chest hangs between the forelegs almost to the
    floor, so there is no daylight under a barrel.

    **THE STATION IS THE BRISKET, WHICH IS WHERE DAYLIGHT WOULD APPEAR.** It used to be described as
    the forelegs' own station because that was f=0 as well; the legs stand at the chest's front
    plane now, and between the two PAWS the midline is legitimately open - that is a real dog's
    chest hanging behind its feet, and `test_it_HAS_HIND_LEGS` asserts that gap on purpose. What
    must stay closed is the deepest point of the brisket, behind them.
    """
    c = build(H)
    fr, d = frame(c, H)
    lo, hi = int(d["leg_r1"]), int(d["chest"][1])
    filled = sum(1 for y in range(lo, hi + 1) if fr.solid(0.0, 0, y))
    assert filled >= (hi - lo) * 0.8, "the chest does not reach the floor between the forelegs"


@pytest.mark.parametrize("H", SIZES)
def test_the_HAUNCH_SITS_ON_THE_GROUND(H):
    """A seated animal touches the floor at the rump, not only at its feet - it is the whole pose.

    The haunch's centre height EQUALS its own vertical radius, so this is true by construction; it
    is asserted because that relationship is two numbers in a table and nothing else guards it.
    """
    c = build(H)
    fr, d = frame(c, H)
    assert fr.solid(d["haunch"][0], 0, 0), "the rump does not reach the ground"


@pytest.mark.parametrize("H", SIZES)
def test_it_HAS_HIND_LEGS(H):
    """**Eleven builds did not, and every check passed them.**

    What stood in for a hind leg was a flat pad lying beside the forefoot: measured in plan the
    whole ground course came out as ONE CONTINUOUS WHITE SLAB from the front paws to the rump, and
    Jack read it off the render at once - *"the back legs are missing"*. A missing limb is still one
    connected piece with a clean audit and a correct bill of materials, which is exactly how the
    frog shipped with `forelegs: 0`.

    A seated dog's hind leg is three things and the eye needs all three: a THIGH bulging outboard of
    the rump, a HOCK folded at the back, and a PASTERN running forward along the floor to the paw.
    Asserted as the two that can be measured - the thigh is the widest thing on the animal, and the
    ground course under it is not one unbroken pad.
    """
    c = build(H)
    fr, d = frame(c, H)
    assert c.meta["parts"]["hind"] > c.meta["parts"]["legs"],         "the hind limb places less than the forelegs - it is a pad, not a leg"
    # the THIGH is the widest part: on a dog the rump's width IS its thighs
    def width_at(f):
        return max((abs(s) for s in range(-40, 41)
                    for y in range(c.sy) if fr.solid(f, s, y)), default=0)
    assert width_at(d["thigh_f"]) >= width_at(d["chest"][0]),         "the thigh is not the widest part of the animal"
    # ...and the PASTERN runs forward along the floor, which is the third of the three things and
    # the one that turns a thigh into a leg: at the hind foot's own offset there is ground contact
    # well forward of the hock.
    reach = [f for f in range(-40, 41) if fr.solid(f, loft.r(d["paw_s"]), 0)]
    assert reach and max(reach) > d["hock_f"] + 0.10 * H,         "there is no pastern - the hind foot does not run forward from the hock"

    # **THE FRONT AND HIND FEET TOUCH, AND NO SIZE SEPARATES THEM.** Swept over four forward
    # positions x two spacings x seven sizes, the ground course NEVER breaks into four feet: the
    # paws' radii are too large against the spacing, and forcing a gap would splay the hind feet
    # wider than the body, which is a different animal. A sitting dog's feet really do touch. So
    # what is asserted is the separation that does exist and does the work - the MIDLINE gap that
    # makes the front pair two paws rather than one pad.
    #
    # **AT THE PAWS' OWN STATION.** Taken at a station derived from the leg's radius alone this
    # passed for the wrong reason the moment the feet moved forward: there was nothing at f=2.8 to
    # merge, so an animal with one continuous front pad would have satisfied it. A gap is only
    # evidence when there is something either side of it.
    ff = loft.r(d["foot_f"])
    assert fr.solid(ff, loft.r(d["leg_s"]), 0), "there is no front paw to be separate from anything"
    assert not fr.solid(ff, 0, 0), "the front paws have merged across the midline into one pad"


@pytest.mark.parametrize("H", SIZES)
def test_the_HIND_FOOT_WEARS_ITS_SOCK(H):
    """**`protect=True` does two different jobs and one of them is not wanted here.**

    `Frame.put` uses that flag both to keep a cell off the relax pass AND to put it in `fixed`, and
    the coat skips `fixed`. Protected, the whole hind limb kept its build-time red: the animal came
    out with white front socks and BARE RED HIND FEET, which no count could see. The relax
    protection it needs comes from the cell set handed to `_relax_mass`, not from the flag.
    """
    c = build(H)
    fr, d = frame(c, H)
    # **`Frame.at` DOES NOT ROUND** - only `put` and `solid` do, so handing it a float f indexes
    # the array with floats and raises. The generator's own coordinates are floats throughout.
    got = set()
    for s in range(1, 40):
        v, u = fr.at(loft.r(d["paw_f1"]), s)
        if 0 <= v < c.sx and 0 <= u < c.sz and c.solid(v, 0, u):
            got.add(name_at(c, v, 0, u))
    assert corgi.HIDE["cream"] in got, "the hind foot is not white - it kept its build-time coat"


@pytest.mark.parametrize("H", SIZES)
def test_the_PROPORTIONS_are_a_sitting_corgi_and_not_a_rabbit(H):
    """**The first build measured 0.39 wide and 0.64 deep against its own height and rendered as a
    RABBIT** - a tall narrow column with two long ears - and no amount of work on the face was ever
    going to fix it. A sitting corgi is about 0.50 wide and 0.83 deep against the height to the ear
    tips, and it is the WIDTH that makes it read as a dog rather than a rodent.

    The ear is the other half of the same finding: at a quarter of the total height it is a rabbit's
    ear whatever it is coloured. A corgi's is a broad triangle at about a fifth.
    """
    import numpy as np
    c = build(H)
    ys, zs, xs = np.nonzero(c.ids > 0)
    w = (xs.max() - xs.min() + 1) / (ys.max() - ys.min() + 1)
    dp = (zs.max() - zs.min() + 1) / (ys.max() - ys.min() + 1)
    assert 0.42 <= w <= 0.60, f"width/height {w:.2f} - a sitting corgi is ~0.50"
    # THE DEPTH BOUND WAS MEASURED WRONG FIRST: 0.83 is rump-to-front-paws, and this box also
    # holds the nose in front and the rump's own curve behind. Nose to tail against ear tip is
    # nearer 1.0, which is what a long low dog actually is.
    assert 0.80 <= dp <= 1.10, f"depth/height {dp:.2f} - a sitting corgi is ~1.0 nose to tail"
    d = corgi._dims(float(H))
    ear = (d["ear_top"] - (d["skull_y"] + d["skull_ry"])) / H
    assert ear <= 0.24, f"the ear is {ear:.3f} of the height - past ~0.24 it is a rabbit's"


@pytest.mark.parametrize("H", SIZES)
def test_the_MUZZLE_PROJECTS_past_the_skull(H):
    """The other half of what tells a dog outline from a rabbit's.

    A rabbit's face is a smooth curve off the skull; a dog's is a wedge that sticks out of it. At
    four cells of projection the profile silhouette had no muzzle worth the name and read as a hare.
    """
    d = corgi._dims(float(H))
    out = d["muzzle_b"][0] - (d["skull_f"] + d["skull_rf"])
    assert out >= 0.09 * H, f"the muzzle projects {out:.1f} - there is no wedge in the outline"


@pytest.mark.parametrize("H", SIZES)
def test_the_EARS_never_cross_the_midline(H):
    """**A guard written against the centre column is not a guard against crossing it.**

    Written as `abs(s) < 1: continue` both ear rows still reached to s = -/+1 and OVERLAPPED there,
    so whichever the loop built second painted over the first: the shape stayed exactly symmetric
    and the colour did not, which is the one cell the mirror check reported at every size. And the
    gap between the pair is a FEATURE - run together they are a crest, not two ears, which is the
    ladybird's spot spacing and the frog's eye pair arrived at from a third direction.
    """
    c = build(H)
    fr, d = frame(c, H)
    crown = loft.r(d["skull_y"] + d["skull_ry"])
    for y in range(crown + 1, int(d["ear_top"]) + 1):
        assert not fr.solid(d["ear_f0"], 0, y), f"the ears meet on the midline at y={y}"


@pytest.mark.parametrize("H", SIZES)
def test_the_EAR_IS_A_CONE_and_not_a_flat_plate(H):
    """**The profile silhouette is why.** At a constant two cells the two ears superimpose edge-on
    into one tall narrow spike, and the outline read as a RABBIT. A real erect dog ear is a rolled
    cone - deep at the base, narrowing to the tip - so it is a triangle from the side as well as
    from the front.
    """
    d = corgi._dims(float(H))
    assert d["ear_d0"] >= d["ear_d1"] * 3, "the ear does not taper front-to-back"
    assert d["ear_d0"] >= 0.12 * H, "the ear's base is too shallow to read in profile"


@pytest.mark.parametrize("H", SIZES)
def test_the_EAR_carries_a_cream_core_inside_a_coat_border(H):
    """The single strongest thing in the head-on view, which is this animal's money view.

    Drawn as one flat colour the pair reads as two red flags; what makes it an EAR is the inside of
    it being a different tone from its rim, which is what a dog actually has.
    """
    c = build(H)
    fr, d = frame(c, H)
    crown = loft.r(d["skull_y"] + d["skull_ry"])
    seen = set()
    for y in range(crown + 1, int(d["ear_top"]) + 1):
        for s in range(1, int(d["ear_c1"] + d["ear_half0"]) + 3):
            for f in range(int(d["ear_f1"] - d["ear_d0"]), int(d["ear_f0"] + d["ear_d0"]) + 1):
                v, u = fr.at(f, s)
                if 0 <= v < c.sx and 0 <= u < c.sz and c.solid(v, y, u):
                    seen.add(name_at(c, v, y, u))
    assert corgi.HIDE["cream"] in seen, "the ear has no cream inside it"
    assert corgi.HIDE["coat"] in seen, "the ear has no coat-coloured border"


# --------------------------------------------------------------------------------- the FACE reads


@pytest.mark.parametrize("H", SIZES)
def test_the_NOSE_AND_THE_MOUTH_DO_NOT_TOUCH(H):
    """**They collided three separate times, each fix correct about its own arithmetic.**

    Derived independently the two marks landed on adjacent courses and merged into a 3 x 4 black
    slab - a bandit mask, not a face - and the white muzzle they are supposed to sit on had nowhere
    left to be. Both are anchored to ONE found course now, so the white gap between them exists by
    construction rather than by two numbers happening to agree.
    """
    c = build(H)
    fr, d = frame(c, H)
    black = [(f, s, y) for (v, y, u) in corgi._solid_cells(c)
             for f, s in [fr.fs(v, u)] if name_at(c, v, y, u) == corgi.HIDE["nose"]
             and f > d["skull_f"]]
    assert black, "there is no black on the muzzle at all"
    ys = sorted({y for _f, _s, y in black})
    runs = [[ys[0]]]
    for y in ys[1:]:
        (runs[-1] if y == runs[-1][-1] + 1 else runs.append([y]) or runs[-1]).append(y)
    assert len(runs) >= 2, ("the nose and the mouth are one unbroken block of black - there is no "
                            "white muzzle between them and the face reads as a mask")


@pytest.mark.parametrize("H", SIZES)
def test_the_EYES_ARE_NOT_BURIED(H):
    """**An eye a cell deep exists in the model, in the sidecar and in the part count, and is
    invisible from the one view the animal is built for.**

    The axolotl records it exactly: *"chosen by proximity instead ... one bead landed a cell deep,
    painted over from exactly the head-on view"*. Taking the frontmost cell of the bead's own cheek
    band makes an occluded eye impossible rather than unlikely.
    """
    c = build(H)
    fr, _d = frame(c, H)
    # **THE EYE, THE NOSE AND THE MOUTH ARE ALL `black_wool`, SO A BLOCK NAME CANNOT TELL THEM
    # APART.** Written that way this test collected the nose and the jaw line as well and reported
    # a buried eye on a build whose eyes were fine - a test that names the wrong evidence, which is
    # the fault this repo already recorded when `jungle_log` was read as proof of a tree. The
    # generator records where it put them, so that is what is read.
    ey, es = c.meta["parts"]["eye_y"], c.meta["parts"]["eye_s"]
    eyes = [(f, s, y) for (v, y, u) in corgi._solid_cells(c)
            for f, s in [fr.fs(v, u)]
            if y == ey and abs(s) == es and name_at(c, v, y, u) == corgi.HIDE["eye"]]
    assert len(eyes) == 2, f"expected one bead a side at y={ey} s=+/-{es}, found {len(eyes)}"
    for f, s, y in eyes:
        assert not fr.solid(f + 1, s, y), f"the eye at s={s} y={y} has head in front of it"


@pytest.mark.parametrize("H", SIZES)
def test_the_EYE_COURSE_IS_ON_THE_SKULL_and_not_on_the_muzzle_root(H):
    """**A column scan cannot find the skull, because on a seated animal the skull is not a separate
    column** - it runs unbroken from the GROUND to the crown, so "the upper third of the skull"
    landed three cells below the skull entirely and the pupils came to rest two cells from the nose.
    That build had a clean audit, `eyes: 2` in its own sidecar, and no eyes.
    """
    c = build(H)
    d = corgi._dims(float(H))
    y = c.meta["parts"]["eye_y"]
    assert d["skull_y"] - d["skull_ry"] <= y <= d["skull_y"] + d["skull_ry"], \
        "the eye is not on the skull"
    assert y > d["muzzle_b"][1], "the eye is at or below the nose - that is a mask, not a face"


@pytest.mark.parametrize("H", SIZES)
def test_the_MOUTH_TURNS_UP(H):
    """The whole of the difference between a mouth and a slot, and what everybody draws when they
    draw a happy dog. The corners are the outermost mouth cells and they sit HIGHER than the line."""
    c = build(H)
    fr, _d = frame(c, H)
    mouth = [(f, s, y) for (v, y, u) in corgi._solid_cells(c)
             for f, s in [fr.fs(v, u)] if name_at(c, v, y, u) == corgi.HIDE["mouth"]]
    assert mouth
    lowest = min(y for _f, _s, y in mouth)
    corners = [y for _f, s, y in mouth if abs(s) == max(abs(s2) for _f2, s2, _y2 in mouth)]
    assert max(corners) > lowest, "the mouth is a flat slot; nothing lifts at the corner"


# --------------------------------------------------------------------- the markings are a MAP


@pytest.mark.parametrize("H", SIZES)
def test_the_WHITE_IS_A_MARKING_and_not_a_shade(H):
    """A Pembroke's white is a MAP - blaze, bib, socks, bum - and the boundary against the red is
    HARD. Softened it stops being a marking and becomes weathering, which is the deck soffit's
    confetti with the sign reversed.

    Asserted as coverage rather than as a boundary: at 35% the animal was a husky's mask and every
    marking had run into its neighbour; a Pembroke is about a fifth to a quarter white.
    """
    # **MEASURED ON THE SKIN, WHICH IS WHAT A VIEWER SEES.** Counted over the whole volume the
    # number is dominated by cells nobody will ever look at, and a coverage bound on it is a bound
    # on the wrong quantity. A seated corgi is white down its whole front and red over its whole
    # back, so a little under half of its skin is honestly white.
    c = build(H)
    cells = corgi._solid_cells(c)
    skin = [k for k in cells
            if any((k[0] + a, k[1] + b, k[2] + e) not in cells
                   for a, b, e in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                   (0, -1, 0), (0, 0, 1), (0, 0, -1)))]
    cream = sum(1 for (v, y, u) in skin if name_at(c, v, y, u) == corgi.HIDE["cream"])
    assert 0.25 <= cream / len(skin) <= 0.48,         f"{cream / len(skin):.0%} of the skin is white - a corgi's front, not a husky's mask"
    tally = c.meta["parts"]["coat"]
    assert tally["coat"] > tally["cream"], "a red dog is mostly red"


@pytest.mark.parametrize("H", SIZES)
def test_the_SABLE_DRIFT_KEEPS_OFF_THE_HEAD(H):
    """Run over the head as well it lands on the muzzle bridge and the brow - where the measured top
    line is low, so the band swallows the whole face - and it merges with the eyes into ONE DARK BAR
    across the front. That was the single worst thing in the first render, and a corgi's head is
    uniform red anyway."""
    c = build(H)
    fr, d = frame(c, H)
    for (v, y, u) in corgi._solid_cells(c):
        f, _s = fr.fs(v, u)
        if f > d["skull_f"] and name_at(c, v, y, u) == corgi.HIDE["sable"] \
                and (v, y, u) not in fr.fixed:
            assert False, f"sable on the face at f={f} y={y}"


def test_the_PALETTE_IS_A_REAL_VALUE_LADDER():
    """**Measured ACROSS families, never inside one.** CLAUDE.md records this mistake five times -
    stone brick, blackstone, the Mine Ridge, the claim row's worked ground - and every one was made
    by searching within a single material, where a ladder cannot exist by construction. Re-derived
    here rather than trusted, because a ladder that is only asserted goes stale the day a block in
    the table is swapped.
    """
    def lum(rgb):
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    rungs = [lum(blocks.color(corgi.HIDE[k], "side"))
             for k in ("eye", "sable", "coat", "cream")]
    assert rungs == sorted(rungs), "the ladder is out of order"
    for a, b in zip(rungs, rungs[1:]):
        assert b - a >= 15, f"two rungs are {b - a:.0f} apart - under ~15 a tone stops being a tone"


def test_EVERY_BLOCK_IS_CHEAP_SPENDABLE_1_19_AND_WITNESSED_IN_THIS_WORLD():
    """**Rule 12, and it is the one this repo keeps being bitten by** - most recently when a
    sculpture came out 78% `nether_wart_block`, which is cheap by the tier table, legal in 1.19 and
    has NEVER BEEN SEEN in this world. A witness set built from `out/` is circular; these are
    checked against captures of the real place.
    """
    from pathlib import Path
    from mcbuild import schem
    seen = set()
    for w in ("island_full", "island_now"):
        p = Path("out") / f"{w}.litematic"
        if p.exists():
            seen |= {nbt.state_name(e).split(":")[-1].split("[")[0] for e in schem.load(p).palette}
    for name in set(corgi.HIDE.values()):
        assert palette.tier(name) == "cheap", f"{name} is not cheap tier"
        assert blocks.spendable(name), f"{name} is CURRENCY on this server"
        assert blocks.available(name), f"{name} is not in the 1.19 list"
        if seen:
            assert name in seen, f"{name} has never been seen in this world - rule 12"


@pytest.mark.parametrize("H", SIZES)
def test_the_SURFACING_PASS_KEEPS_OFF_THE_HEAD(H):
    """`gen/shell.py` chamfers a step by replacing the cell with a stair of the nearest colour,
    which is right on a haunch and is vandalism on a face: set at the muzzle rather than the back of
    the skull the pass owned the whole cranium and turned the brow, the crown and the blaze into a
    field of orange stairs. A head is a DRAWN feature from the ears down.
    """
    c = build(H)
    fr, d = frame(c, H)
    shapes = {n for n in names_of(c) if n.endswith(("_stairs", "_slab"))}
    for (v, y, u) in corgi._solid_cells(c):
        if name_at(c, v, y, u) in shapes:
            f, _s = fr.fs(v, u)
            assert f < d["skull_f"] - d["skull_rf"] + 1, f"a shape block on the head at f={f}"


@pytest.mark.parametrize("H", SIZES)
def test_the_FORELEGS_STAND_IN_FRONT_OF_THE_CHEST(H):
    """**A LEG BEHIND THE CHEST'S FRONT FACE IS NOT A LEG, IT IS THE CHEST.**

    Jack, on the eleventh build: *"we still need small front legs visible and separate from the
    body"*. Built at f=0 the columns stood five blocks behind the chest's own front plane, so
    measured in profile the front of the animal SLOPED BACKWARD as it descended - f=8 at the
    shoulder and f=3 at the floor - which is a sack tapering to the ground and not a dog. A sitting
    dog is the opposite: the chest is set back, the legs drop in front of it and the feet run
    forward along the floor, so the FRONTMOST cell of the whole lower body is at the BOTTOM of it.

    Two halves, because either alone passes a wrong build: the foot has to reach past the chest,
    and the outline between them must not fall away behind it on the way down.
    """
    c = build(H)
    fr, d = frame(c, H)
    sl = loft.r(d["leg_s"])
    span = range(-3 * int(H), 3 * int(H))

    def front(y):
        got = [f for f in span if fr.solid(f, sl, y)]
        return max(got) if got else None

    chest_y = loft.r(d["chest"][1])
    foot, shoulder = front(0), front(chest_y)
    assert foot is not None and shoulder is not None
    assert foot > shoulder, (
        f"the front foot ({foot}) does not reach past the chest ({shoulder}) - there is no leg, "
        "only a chest that comes down to the floor")
    lows = [front(y) for y in range(0, chest_y + 1)]
    assert None not in lows, "the front of the animal has a hole in it below the chest"
    assert min(lows) >= shoulder - 2, (
        "the front outline falls away behind the shoulder on its way down - that is a sack")


@pytest.mark.parametrize("H", SIZES)
def test_the_FORELEG_READS_AGAINST_THE_CHEST(H):
    """**GEOMETRY ALONE DID NOT MAKE THE LEG VISIBLE, AND ONLY A RENDER SAID SO.**

    With the columns moved to the chest's front plane the animal was right and still read as a WALL
    in profile: one unbroken red surface from the chin to the floor, because a silhouette cannot
    show an edge between two things of the same tone facing the same way. This animal already
    records the rule for its hind limb - *the limb reads by its own TONE, not by a gap* - and the
    front sock is that rule at the other end.

    Asserted as the boundary that does the drawing: white on the leg, coat directly behind it, at
    every course between the hind sock's top and the front sock's.
    """
    c = build(H)
    fr, d = frame(c, H)
    sl, lf = loft.r(d["leg_s"]), loft.r(d["leg_f"])
    band = list(range(int(d["sock_y"]) + 1, int(d["fore_sock_y"]) + 1))
    assert len(band) >= 2, "the front sock is too short to draw a leg at this size"
    for y in band:
        v, u = fr.at(lf, sl)
        assert c.solid(v, y, u) and name_at(c, v, y, u) == corgi.HIDE["cream"], (
            f"the foreleg is not white at y={y} - nothing draws it out of the chest")
        v, u = fr.at(loft.r(d["loin"][0]), sl)
        assert c.solid(v, y, u) and name_at(c, v, y, u) != corgi.HIDE["cream"], (
            f"the belly behind the leg is white too at y={y} - the sock is a hem, not a sock")


@pytest.mark.parametrize("H", SIZES)
def test_the_BOBTAIL_CLEARS_THE_RUMP(H):
    """**A FEATURE PLACED AT A COMPUTED STATION IS INSIDE THE ANIMAL.**

    Jack asked for *"a little clear tail or 'butt'"*, and there was already a stump in the build:
    32 cells, one course of skin thickness, changing the outline by nothing, because the haunch
    reaches further back than the computed centre at every height the ball could sit at. That is
    the mane's seven floating fragments and the detached ossicones with the sign reversed - the
    same mistake makes a feature vanish INTO a shape as readily as off it.

    It is found off the croup the mass actually has, and what is asserted is the only thing that
    matters: at the tail's own height the outline reaches further back than the rump does anywhere
    else, so a viewer in profile sees a tail rather than a rounder bottom.
    """
    c = build(H)
    fr, d = frame(c, H)
    span = range(-3 * int(H), 3 * int(H))

    def back(y):
        got = [f for f in span if fr.solid(f, 0, y)]
        return min(got) if got else None

    ty = loft.r(d["tail_y"])
    tail = [x for x in (back(y) for y in range(ty - 1, ty + int(d["tail_r"]) + 2)) if x is not None]
    rump = [x for x in (back(y) for y in range(1, ty - 1)) if x is not None]
    assert tail and rump
    assert min(tail) < min(rump), (
        f"the bobtail reaches {min(tail)} and the rump already reaches {min(rump)} - "
        "the tail is inside the bottom")


@pytest.mark.parametrize("H", SIZES)
def test_the_BOBTAIL_IS_NOT_THE_TONE_OF_THE_BOTTOM_IT_STANDS_ON(H):
    """A white nub on a white rear has no contrast at all, and a corgi's rear is mostly white.

    So `bum_hi` stops below the tail's own underside: the bobtail is a red-or-sable knob on a white
    bottom, which is 132 points of luminance and is what a Pembroke actually looks like. Asserted
    on the SKIN a viewer sees rather than on the volume, because a marking is a surface.
    """
    c = build(H)
    fr, d = frame(c, H)
    ty = loft.r(d["tail_y"])
    span = range(-3 * int(H), 3 * int(H))

    def rear_skin(y):
        got = [f for f in span if fr.solid(f, 0, y)]
        if not got:
            return None
        v, u = fr.at(min(got), 0)
        return name_at(c, v, y, u)

    assert rear_skin(ty) != corgi.HIDE["cream"], "the bobtail is the same white as the bottom"
    below = [rear_skin(y) for y in range(int(d["bum_lo"]) + 1, ty - 1)]
    assert corgi.HIDE["cream"] in below, "the rear is not white - there is no bottom to read against"
