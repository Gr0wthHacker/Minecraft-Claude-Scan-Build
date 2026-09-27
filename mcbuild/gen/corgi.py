"""A SITTING CORGI - and the one dog whose anatomy lands inside the category this repo can build.

**WHY A CORGI, AND WHY SITTING.** CLAUDE.md's measured line is PLANAR / COLUMNAR / ONE CONVEX MASS
against VOLUMETRIC, sharpened by the download corpus into the sentence that actually decides it:
*"the line is not the species, it is whether the silhouette decomposes into LIMBS"* - a corpus of 31
outside builds contains no realistically-proportioned quadruped at all, and eight mammals plus a
stegosaur plus an ankylosaur were retired here for exactly that.

A standing dog decomposes. A SITTING one does not: the haunches are folded onto the ground, the
chest hangs between the forelegs almost to the floor, and what is left is one mass with two big
planar ears on top. That is `Warm Snooze`'s category - the outside builder's curled tabby that reads
instantly - and this file's own amendment says a mammal folded into one mass *"is worth one attempt,
at a wide low footprint, judged on its plan"*. A corgi is the breed that needs the least help
getting there, because its legs are about a seventh of its height even standing up.

**AND ITS IDENTITY IS A PATTERN AND TWO SHEETS, NOT MUSCLE.** What names a corgi to a stranger, in
order: the EARS (huge, upright, rounded triangles, oversized for the skull - flat sheets, which is
the one thing voxels render natively, and they break the outline the way a lion's mane had to); the
WHITE MARKINGS (blaze, bib, socks, bum - hard high-contrast pattern on a convex mass, the ladybird's
and the turtle's category); the fox MUZZLE with the dark nose and the upturned mouth line. Not one
of those asks the grid to describe a joint.

**THE MONEY VIEW IS HEAD-ON**, which is unusual here and is why the pattern is spent where it is:
head-on gives the ear pair, the blaze between them, the eyes, the nose and the whole white bib at
once. The profile gives the sit. The plan gives the ears and the round rump, and is the weakest of
the three - the opposite of the ladybird and the turtle, and the reason the bib is built as a
FRONT-FACING zone found off the skin rather than as a band at a height.

PALETTE - measured with `blocks.color(name, "side")`, and every block WITNESSED in `island_full`
rather than merely cheap by the tier table (rule 12, which this file has now been bitten by four
times):

    mangrove_planks 67 . acacia_planks 104 . white_wool 236 . black_wool 21

The coat ladder is 67 -> 104, a step of 37; the markings are 104 -> 236, a step of 132. The second
one is deliberately enormous: a Pembroke's white is the loudest thing about it and the boundary is
HARD, so nothing dithers across it. Only the sable/coat boundary drifts, because that one is
shading rather than a marking. `bone_block` measures closer to fur and is a `rotated_pillar`, which
`shell.slab_for` refuses on sight - the recorded reason being that the colour DB samples a block's
TOP face and a log's top is end grain. `white_wool` has no slab in the game at all, so the white
markings take no surfacing; the red mass does, at a colour distance of 0 (acacia planks -> acacia
slab and stair, same material family).

SIZE FROM THE EAR, which is this repo's own sizing doctrine: an animal's critical size is the
largest of its features' own floors. The ear has to be a rounded triangle with a coat-coloured
border and a cream core, so its base needs 4 cells minimum, and the base is 0.150 of the total
height - which puts the floor at 24 and makes anything smaller an animal with two red tabs on it.
The default is 32, where the ear is 5 x 9 and the border/core reads cleanly.
"""
from __future__ import annotations

import math

import numpy as np

from .. import nbt
from . import loft, shell, smooth
from .canvas import Canvas, hash01

HIDE = {
    # THE COAT LADDER. `sable` is the deeper red along the spine and the back of the ears - real
    # Pembrokes carry it, and without it the whole red mass is one flat tone and the value panel
    # shows a shape with a pattern on it rather than a form. It is applied as a DRIFT off the
    # measured back line, never as a band at a fixed height: a band at a height on a lofted body
    # follows nothing the body is doing and reads as a stripe.
    "sable": "mangrove_planks",     # L67
    "coat": "acacia_planks",        # L104 - the working tone, and most of the animal
    # THE MARKINGS. One block, and the boundary against the coat never dithers. A Pembroke's white
    # is not shading, it is a map: blaze, bib, socks, bum, inner ear. Dither it and it stops being
    # a marking and becomes weathering, which is the deck soffit's confetti with the sign reversed.
    "cream": "white_wool",          # L236
    # THE FACE. The nose, the mouth line and the pupils are the only black on the animal, so black
    # means exactly one thing - the frog's rule that a mark meaning something different is a
    # different block, and the ankylosaur's correction that a mark meaning the SAME thing must not
    # be. The eye's RING is `sable` rather than a pale ring: at L104 coat against L21 pupil the
    # bead already has 83 of contrast, well past this file's own 35, and a pale ring on a red head
    # reads as a googly eye where a dark rim is what a dog actually has.
    "eye": "black_wool",
    "nose": "black_wool",
    "mouth": "black_wool",
    "ring": "mangrove_planks",
}

CORGI = {
    "kind": "corgi",
    # HEIGHT INCLUDING THE EARS, because the ears are the tallest thing on the animal and the
    # feature every other measurement is derived from. Measuring to the crown instead would make
    # the one number a reader tunes mean something other than how big the statue looks.
    "height": 32,
    "scale": 1.0,
    "facing": "north",              # the way it LOOKS
    "at": None,                     # world coordinate of the canvas corner
    "stand": None,                  # ...or the world cell the PAWS occupy - see `build_corgi`
    "seed": 0,
    "title": "THE CORGI",
    # smoothing, `quadruped.py`'s own numbers - see `_relax_mass`
    "relax_rounds": 4,
    "relax_fill": 11,
    "relax_keep": 11,
}


def _dims(H: float) -> dict:
    """Every number a FRACTION OF THE TOTAL HEIGHT, never a block count.

    "Feature sizes must scale" is one of CLAUDE.md's named traps - a tail hardcoded at 13 blocks was
    once longer than a deer's legs and broke a model in two, and the ankylosaur's club silently
    became a one-course paddle below length 34 because two radii were absolute among ratios.

    **THE SIT IS THE GEOMETRY, AND THE CHEST IS WHAT KEEPS IT OFF THE JAGUAR'S LIST.** The haunch
    sits ON the ground (its centre is exactly its own vertical radius above y=0) and the sternum
    hangs to 0.15H, so the forelegs are merged into the chest for their whole upper half and only
    separate into two short columns near the floor. Sized any other way this is four table legs and
    a barrel, which is the shape this system has now failed ten times.

    **AND THE SKULL IS BUILT WIDE ENOUGH TO CARRY THE EAR BASES.** An ear base that overhangs its
    own skull has to be anchored on a crown that is not under it, and every one of this repo's
    detached manes, ossicones and ear tips is that same fault. `skull_rs` is derived from the ear's
    own outer reach rather than chosen, so widening the ears cannot orphan them.
    """
    ear_c0, ear_half0 = 0.075 * H, 0.095 * H          # ear base: centre and half-span across
    # **THE RUMP'S CENTRE HEIGHT IS AN INTEGER.** `loft.ball` steps whole-cell offsets from its
    # centre and rounds each one, so from a float centre there is simply no offset that lands on
    # y=0: at 24 and 30 blocks the seated animal floated a course clear of the ground, with
    # `refused: 0`, `problems: 0` and a render that showed a dog sitting down. This file's own trap
    # list has it - *"keep centres INTEGER and add offsets to them"* - and the extra courses of
    # radius are what give the contact a pad rather than a single column.
    hy = loft.r(0.230 * H)
    return {
        "H": H,
        # ---- the seated mass: (forward, centre height, half-depth, half-width, half-height)
        # The haunch's centre height EQUALS its vertical radius, so it rests on the ground by
        # construction rather than by a number that has to be kept in step with it.
        #
        # **THESE ARE MEASURED RATIOS AND THE FIRST SET WERE NOT.** Built from a mental image of a
        # sitting dog the animal came out 0.39 wide and 0.64 deep against its own height, and it
        # rendered as a RABBIT - a tall narrow column with two long ears. A sitting corgi measures
        # about 0.50 wide and 0.83 deep against the height to the ear tips, and it is that width
        # that makes it read as a dog rather than as a rodent: the haunches spread, the base is
        # broad, and the mass is low. It is the same finding as the frog's - the cure for "it does
        # not read" was the PROPORTION, not another pass of detail on the face.
        # **THE VERTICAL RADIUS IS BIGGER THAN THE CENTRE HEIGHT, ON PURPOSE.** Made exactly equal
        # the rump lands on the floor by arithmetic and misses it by rounding: `loft.ball` steps its
        # offsets in whole cells from a FLOAT centre, so at 24 and 30 blocks no offset rounded to
        # y=0 and the seated animal floated a course clear of the ground with a clean audit. The
        # paws already solve it the same way - a ball whose lower half is refused below the floor -
        # and a refusal under the ground plane is the ground, not a clip.
        "haunch": (-0.190 * H, hy, 0.230 * H, 0.200 * H, hy + 1.0),
        "loin": (-0.020 * H, 0.265 * H, 0.180 * H, 0.215 * H, 0.215 * H),
        "chest": (0.110 * H, 0.330 * H, 0.150 * H, 0.190 * H, 0.185 * H),

        # ---- neck: SHORT and THICK, which is most of what makes a corgi a corgi in profile. A
        # long neck is what turns a seated dog into a meerkat, and it is the second half of why
        # the first build read as a rabbit.
        # **AND IT IS THINNER THAN THE HEAD, OR THERE IS NO HEAD IN THE PROFILE.** At a radius
        # within a cell of the skull's own the neck fills the whole gap between the chest and the
        # cranium, the relax pass welds the three into one mass, and side-on the animal reads as a
        # SEAL - a smooth teardrop with two fins on the back. A corgi's neck is genuinely thick;
        # what it is not is as thick as its head.
        "neck_a": (0.130 * H, 0.470 * H), "neck_b": (0.195 * H, 0.640 * H),
        "neck_r0": 0.105 * H, "neck_r1": 0.098 * H,

        # ---- skull and muzzle. The skull is SHORT front-to-back and the muzzle is LONG, or the
        # face is flat: at 2.1 cells of projection past the skull front there is no muzzle in the
        # profile at all, and a dog seen side-on with no muzzle is a bear cub.
        # **AND IT MUST DROP.** Run level with the skull the muzzle puts the nose at the EYE LINE,
        # and the nose, the mouth and the two pupils come out as one dark bar across the front -
        # thirteen black cells reading as a mask, which is the axolotl's "a two-cell bar, not a
        # bead" in its third costume. A dog's muzzle leaves the skull BELOW the eyes and points
        # down; here that is 2.7 cells of drop at H=32, and it is what turns a mask into a face.
        # **THE HEAD IS FORWARD OF THE CHEST, NOT SET INTO IT.** At 0.165 the skull's own centre
        # sits BEHIND the chest's front plane, so most of the cranium is inside the shoulders and
        # the ears come off the animal's back like a dorsal fin. A sitting dog carries its head out
        # over its own forefeet.
        "skull_f": 0.205 * H, "skull_y": 0.715 * H,
        # **THE HEAD IS THE MOB'S, NOT THE ANIMAL'S.** At anatomical proportions the muzzle is 4.5
        # cells across at H=32 and cannot carry a nose, a mouth line, a white side and a red bridge
        # at once - the nose and the mouth merged into one black mask and the white disappeared
        # entirely. That is the frog's own recorded finding: *"anatomically-correct proportions gave
        # a toad"*, and the naming test is against what people PICTURE, which for a corgi is a big
        # round head with a short broad muzzle.
        "skull_rf": 0.105 * H, "skull_rs": ear_c0 + ear_half0, "skull_ry": 0.095 * H,
        # ...and it PROJECTS, because a muzzle is the other half of what tells a dog outline from a
        # rabbit's. A rabbit's face is a smooth curve off the skull; a dog's is a wedge that sticks
        # out of it. At four cells of projection the silhouette had no muzzle worth the name.
        "muzzle_a": (0.290 * H, 0.672 * H), "muzzle_b": (0.480 * H, 0.585 * H),
        # **AND IT IS DEEPER THAN IT IS WIDE.** Swept as spheres the muzzle's width and its height
        # are the same number, so thinning it for the silhouette's sake left no material BELOW the
        # nose and the mouth collapsed to a single cell - `mouth: 1` in the sidecar, and a face
        # with no mouth in it. A dog's muzzle is a narrow deep box; the width is what makes the
        # wedge and the depth is what carries the jaw.
        "muzzle_r0": 0.082 * H, "muzzle_r1": 0.052 * H,
        # **AND IT NEEDS SIX COURSES AT THE TIP, WHICH IS AN ARITHMETIC FLOOR RATHER THAN A TASTE.**
        # Top to bottom the snout has to carry a red bridge, a three-course nose, a course of white,
        # the mouth line and a white chin. At four courses the nose and the mouth are adjacent and
        # merge into one black slab - a snout, not a face - which is the same collision the frog
        # records between its own eyes and its jaw line, one part further forward.
        "muzzle_h0": 0.090 * H, "muzzle_h1": 0.092 * H,

        # ---- the ears, which are the whole animal's headline feature
        # They lean BACK and OUT as they rise: a corgi's ears splay, and a pair of vertical tabs
        # reads as a crest rather than as ears. Two cells thick in the forward axis - the front
        # cell is the cream inner face, the back cell the coat outer - because at one cell there
        # is no inside of an ear to see and head-on is this animal's money view.
        #
        # **AND THEY ARE ROUGHLY AS WIDE AS THEY ARE TALL.** At 0.247 of the total height they are
        # RABBIT ears and the whole animal reads as one; a corgi's are big, broad triangles at
        # about a fifth of the seated height. The ratio is the tell, not the size.
        # **AN ERECT DOG EAR IS A ROLLED CONE, NOT A FLAT PLATE, AND THE SILHOUETTE IS WHY.** At a
        # constant two cells the two ears superimpose edge-on into ONE TALL NARROW SPIKE, and the
        # profile silhouette - the only question the panel review says finally matters - read as a
        # RABBIT. Deep at the base and narrowing to the tip it is a triangle from the side as well
        # as from the front, which is both what the animal actually has and what stops the outline
        # naming the wrong species.
        "ear_f0": 0.205 * H, "ear_f1": 0.183 * H,
        "ear_d0": 0.170 * H, "ear_d1": 0.030 * H,
        "ear_c0": ear_c0, "ear_c1": 0.115 * H,
        "ear_half0": ear_half0, "ear_half1": 0.028 * H,
        "ear_top": 1.000 * H,

        # ---- forelegs, AT THE CHEST'S OWN FRONT PLANE rather than under its middle.
        #
        # **A LEG BEHIND THE CHEST'S FRONT FACE IS NOT A LEG, IT IS THE CHEST.** Built at f=0 the
        # column stood 5.5 blocks behind the chest's own front (8.3), so measured in profile the
        # front of the animal SLOPED BACKWARD as it descended - y=9 at f=8, y=5 at f=4, y=3 at f=3 -
        # which is a sack tapering to the floor and is exactly what Jack read off the render.
        # A sitting dog is the opposite: the chest is set BACK and two vertical columns stand in
        # front of it, so the lowest part of the front outline is the FURTHEST FORWARD.
        #
        # **AND THE SEPARATION IS IN DEPTH, NOT IN WIDTH.** Prising the legs apart sideways is the
        # one thing this animal must not do - `test_the_SILHOUETTE_DOES_NOT_DECOMPOSE_INTO_LIMBS`
        # is the whole reason a corgi is buildable where eight mammals were retired, and daylight
        # under a barrel is that failure. What reads instead is the leg standing PROUD of the chest
        # wall behind it, with the paw and its toes further forward again: from the side a column
        # and a foot, from the front two legs either side of a narrow keel, and not one cell of sky
        # under the brisket.
        "leg_f": 0.155 * H, "leg_s": 0.105 * H,
        "leg_r0": 0.075 * H, "leg_r1": 0.062 * H, "leg_top": 0.360 * H,
        # the front paw, which is the part that actually projects: a flattened pad in front of the
        # chest plane carrying the same three-toe fan as the hind foot.
        "foot_f": 0.205 * H, "foot_r": 0.078 * H,
        # ---- THE HIND LEGS, which the first eleven builds simply did not have.
        #
        # **A PAD ON THE FLOOR IS NOT A LEG.** What was here was a flat sweep lying beside the
        # forefoot, and measured in plan the whole ground course came out as ONE CONTINUOUS WHITE
        # SLAB from the front paws to the rump - no thigh, no hock, no limb, and Jack read it off
        # the render immediately as "the back legs are missing". Every check passed it, because a
        # missing limb is still one connected piece with a clean audit: the frog shipped with
        # `forelegs: 0` in its own sidecar for the same reason.
        #
        # A seated dog's hind leg is THREE things and the eye needs all three to follow it: a THIGH
        # bulging outboard of the rump, a HOCK folded at the back, and a PASTERN running forward
        # along the floor to the paw. The thigh is also where the animal is WIDEST - the rump's
        # width IS its thighs - so the haunch itself is narrowed to 0.200 and the width put back
        # into these, which is what gives the flank a visible thigh line instead of one smooth
        # barrel.
        "thigh_f": -0.120 * H, "thigh_s": 0.150 * H, "thigh_y": 0.235 * H,
        "thigh_rf": 0.155 * H, "thigh_rs": 0.095 * H, "thigh_ry": 0.185 * H,
        "hock_f": -0.150 * H, "hock_y": 0.085 * H,
        "paw_s": 0.215 * H, "paw_f0": 0.030 * H, "paw_f1": 0.130 * H, "paw_r": 0.058 * H,
        "toe_r": 0.030 * H, "toe_len": 0.085 * H,

        # ---- the famous bobtail. A stump, not a tail: a Pembroke is docked, and a thin tail is a
        # taper that comes apart below one cell (the stegosaur's spikes, the pterosaur's spans).
        #
        # **IT IS A HEIGHT AND A RADIUS; ITS FORWARD STATION IS FOUND.** Placed at a computed f it
        # landed inside the rump's own curve - the haunch reaches back to -14 at y=6..11 and the
        # stump was centred at -13.8 - so it gained 32 cells of skin thickness and nothing that
        # reads as a tail. `_stump` walks back along the croup at this height, takes the rearmost
        # cell the mass ACTUALLY has, and hangs the nub off it. Same rule as the toes, the ears and
        # the eyes: measure the skin, never assume where it is.
        #
        # **AND IT SITS ABOVE THE WHITE.** A white nub on a white rear has no contrast at all, so
        # `bum_hi` stops below the tail's own underside and the bobtail is a RED knob on a WHITE
        # bottom - 132 points of luminance, and what a Pembroke's rear actually looks like.
        "tail_y": 0.400 * H, "tail_r": 0.062 * H,

        # ---- the section exponent. 2.0 is an ellipse; a little over reads as an animal that
        # still looks built, which is `loft.py`'s own note.
        "n_sec": 2.2,

        # ---- the coat map, all of it in fractions of H
        "sock_y": 0.135 * H,            # white below this on the hind paws
        # **THE FRONT SOCK IS WHAT DRAWS THE FORELEG OUT OF THE CHEST.** Moved forward to the
        # chest's own front plane the leg is geometrically right and still reads as a WALL: in
        # profile it is one unbroken red surface from the chin to the floor, because a silhouette
        # cannot show an edge between two things of the same tone facing the same way. This animal
        # already records the rule for its hind limb - *the limb reads by its own TONE, not by a
        # gap* - and it is the same rule here. White to the pastern, and BOUNDED FORWARD so the
        # boundary lands on the leg's own back edge rather than belting the belly and the rump.
        "fore_sock_y": 0.250 * H,
        "under_y": 0.045 * H,           # ...and on everything, which is the undercarriage
        "bib_lo": 0.110 * H, "bib_hi": 0.545 * H, "bib_half": 0.078 * H,
        "throat_hi": 0.640 * H, "throat_half": 0.082 * H,
        "blaze_half": 0.045 * H, "blaze_half_top": 0.020 * H,
        "bum_f": -0.320 * H, "bum_lo": 0.100 * H, "bum_hi": 0.345 * H,
        "sable_band": 0.050 * H,
        # **THE SABLE DRIFT STOPS AT THE NECK.** Run over the head as well it lands on the muzzle
        # bridge and the brow - where the measured top line is low, so the band swallows the whole
        # face - and it merges with the eyes into ONE DARK BAR across the front. That is the
        # axolotl's "a two-cell bar, not a bead" and the frog's sunglasses, arrived at from a third
        # direction, and it was the single worst thing in the first render. A corgi's head is
        # uniform red anyway.
        "sable_to": 0.100 * H,
        "coat_min_depth": 0.09 * H,

        "relax_rounds": 4, "relax_fill": 11, "relax_keep": 11,
    }


def _muzzle_y(d: dict, f: float) -> float:
    """The height of the muzzle's own axis at forward station `f`, extended past both ends.

    The white on a corgi's face is *below the muzzle line*, not below a height - the muzzle drops
    as it runs forward, so a flat cut whites the bridge at the nose and leaves the chin red.
    """
    (af, ay), (bf, by) = d["muzzle_a"], d["muzzle_b"]
    t = 0.0 if bf == af else (f - af) / (bf - af)
    return ay + (by - ay) * t


def _blaze_half(d: dict, y: float) -> float:
    """The blaze narrows as it climbs - broad where it joins the white muzzle, a thread on the crown.

    Drawn at one width it is a stripe painted on, and at any width wide enough to read low down it
    swallows the whole forehead. A real blaze is a wedge, and a wedge is one line of arithmetic.
    """
    lo, hi = d["muzzle_a"][1], d["skull_y"] + d["skull_ry"]
    t = 0.0 if hi == lo else max(0.0, min(1.0, (y - lo) / (hi - lo)))
    return d["blaze_half"] + (d["blaze_half_top"] - d["blaze_half"]) * t


def _muzzle_h(d: dict, f: float) -> float:
    """The muzzle's own half-HEIGHT at forward station `f`, clamped at both ends."""
    (af, _ay), (bf, _by) = d["muzzle_a"], d["muzzle_b"]
    t = 0.0 if bf == af else max(0.0, min(1.0, (f - af) / (bf - af)))
    return d["muzzle_h0"] + (d["muzzle_h1"] - d["muzzle_h0"]) * t


def _muzzle_r(d: dict, f: float) -> float:
    """The muzzle's own half-width at forward station `f`, clamped at both ends."""
    (af, _ay), (bf, _by) = d["muzzle_a"], d["muzzle_b"]
    t = 0.0 if bf == af else max(0.0, min(1.0, (f - af) / (bf - af)))
    return d["muzzle_r0"] + (d["muzzle_r1"] - d["muzzle_r0"]) * t


def _solid_cells(c: Canvas) -> set:
    ys, zs, xs = np.nonzero(c.ids > 0)
    return {(int(x), int(y), int(z)) for x, y, z in zip(xs.tolist(), ys.tolist(), zs.tolist())}


# ------------------------------------------------------------------------------------ the mass


def _lump(fr: loft.Frame, spec, key="coat") -> None:
    """One body mass as a superellipsoid - separate depth, width and height radii.

    **A SPHERE HAS ONE RADIUS AND THIS ANIMAL'S PLAN AND PROFILE ARE DIFFERENT SHAPES.** Swept as
    spheres they are the same shape by construction, which is the jaguar's recorded retirement (*"a
    constant-depth rectangle from shoulder to rump"*) and what made the stegosaur read as a loaf.
    """
    f0, y0, rf, rs, ry = spec
    for df in range(-int(math.ceil(rf)), int(math.ceil(rf)) + 1):
        for ds in range(-int(math.ceil(rs)), int(math.ceil(rs)) + 1):
            for dy in range(-int(math.ceil(ry)), int(math.ceil(ry)) + 1):
                if (abs(df) / rf) ** 2 + (abs(ds) / rs) ** 2 + (abs(dy) / ry) ** 2 > 1.0:
                    continue
                fr.put(f0 + df, ds, y0 + dy, key)


def _body(fr: loft.Frame, d: dict) -> None:
    """Haunch, loin and chest, plus the bridges between them so the mass is one piece.

    The three lumps overlap by design, and the bridging sweeps exist for the case they do not: at
    the small end of the size range a gap of one cell between two ellipsoids is a second component
    with a perfectly clean audit, which is the ear-tip failure wearing a body.
    """
    for spec in (d["haunch"], d["loin"], d["chest"]):
        _lump(fr, spec)
    for a, b in ((d["haunch"], d["loin"]), (d["loin"], d["chest"])):
        loft.sweep(fr, (a[0], 0.0, a[1]), (b[0], 0.0, b[1]),
                   min(a[2], a[4]) * 0.8, min(b[2], b[4]) * 0.8, "coat")


def _neck_head(fr: loft.Frame, d: dict) -> None:
    """A short thick neck, a broad skull and a fox muzzle tapering to a blunt cap.

    **THE TAPER STOPS SHORT OF THE TIP AND A CAP FINISHES IT.** The head is built as MASS, so the
    relax pass runs over it, and relax fills a narrow trough and shaves a thin tip - the
    ankylosaur's skull came to a POINT and the animal read with a snout where a blunt muzzle should
    be. Ending the sweep early and capping it with a flattened ellipsoid gives relax something with
    neighbours to keep.
    """
    (af, ay), (bf, by) = d["neck_a"], d["neck_b"]
    loft.sweep(fr, (af, 0.0, ay), (bf, 0.0, by), d["neck_r0"], d["neck_r1"], "coat")
    _lump(fr, (d["skull_f"], d["skull_y"], d["skull_rf"], d["skull_rs"], d["skull_ry"]))


def _muzzle(fr: loft.Frame, d: dict) -> None:
    """The snout. Built separately from the skull SO THAT IT CAN BE PROTECTED FROM THE RELAX PASS.

    **A MUZZLE IS A THIN PROTRUSION AND `keep` EATS THOSE.** Left unprotected the smoothing shaved
    its whole underside away - the tip existed from y=20 up and simply was not there below - so the
    jaw line had no surface to be found on and the mouth collapsed to a handful of cells on the
    cheeks. CLAUDE.md's rule is that only the legs are protected because *"a leg genuinely has too
    few neighbours to survive `keep`; a skull does not"*; a muzzle is a leg by that test, not a
    skull, and the ankylosaur hit the same wall from the other side when its snout came to a POINT.
    """
    (mf, my), (nf, ny) = d["muzzle_a"], d["muzzle_b"]
    _taper(fr, (mf, my), (nf, ny), d["muzzle_r0"], d["muzzle_r1"],
           d["muzzle_h0"], d["muzzle_h1"])


def _taper(fr: loft.Frame, a, b, rs0, rs1, ry0, ry1, key="coat") -> None:
    """A capsule from a to b with its WIDTH and its HEIGHT tapering independently.

    `loft.sweep` is spherical, so anything swept with it is as deep as it is wide by construction -
    which is the jaguar's constant-depth slab in miniature and, on the muzzle, the reason there was
    no room under the nose for a mouth.
    """
    (af, ay), (bf, by) = a, b
    n = max(2, int(math.dist((af, ay), (bf, by)) / 0.30) + 1)
    for i in range(n + 1):
        t = i / n
        loft.ball(fr, af + (bf - af) * t, 0.0, ay + (by - ay) * t,
                  rs0 + (rs1 - rs0) * t, key,
                  rs=rs0 + (rs1 - rs0) * t, ry=ry0 + (ry1 - ry0) * t)


def _legs(fr: loft.Frame, d: dict) -> None:
    """Two short forelegs, standing at the chest's front plane with their paws in front of it.

    **THE LEG IS A VERTICAL COLUMN AND THE PAW IS WHAT PROJECTS.** Elbow to pastern a sitting dog's
    foreleg is plumb - the slight forward lean here is the pastern, not the leg - and then the foot
    runs forward along the floor. That is what puts the animal's frontmost cell at the BOTTOM of the
    front outline instead of at the top, and it is the whole difference between a chest with legs
    and a sack.
    """
    for sgn in (1, -1):
        s = sgn * d["leg_s"]
        loft.sweep(fr, (d["leg_f"] - 0.010 * d["H"], s, d["leg_top"]),
                   (d["leg_f"] + 0.015 * d["H"], s, d["leg_r1"] * 0.6),
                   d["leg_r0"], d["leg_r1"], "coat")
        # the paw itself, flattened and set FORWARD of the chest, so the leg meets the ground in a
        # foot rather than a stump - and so that a viewer in profile sees a foot at all.
        loft.ball(fr, d["foot_f"], s, d["leg_r1"] * 0.55, d["foot_r"],
                  "coat", rs=d["foot_r"] * 0.88, ry=d["foot_r"] * 0.56)



def _hind(fr: loft.Frame, d: dict) -> None:
    """Thigh, hock and pastern - the limb the animal was missing.

    **THE THIGH IS MASS AND THE PASTERN IS A FEATURE, AND THEY ARE TREATED DIFFERENTLY.** The thigh
    goes in before the relax pass so that it BLENDS into the rump - built afterwards it is luggage
    strapped to the flank, which is the ankylosaur's recorded "crates" failure - while the pastern
    and the paw are protected, because they are thin protrusions and `keep` eats those exactly as it
    ate the muzzle's underside.

    **AND THE LIMB READS BY ITS OWN TONE, NOT BY A GAP.** A real dog's hind foot does touch its
    front foot when it sits; what separates them for a viewer is that the thigh above is RED and the
    pastern below is WHITE. Chasing a gap in the geometry instead would have to splay the feet wider
    than the body, which is a different animal.
    """
    for sgn in (1, -1):
        st = sgn * d["thigh_s"]
        loft.ball(fr, d["thigh_f"], st, d["thigh_y"], d["thigh_rf"], "coat",
                  rs=d["thigh_rs"], ry=d["thigh_ry"])
        sp = sgn * d["paw_s"]
        knee = d["hock_f"] + 0.055 * d["H"]
        # **NOT `protect=True`.** `Frame.put` uses that flag for two different jobs - keeping a cell
        # off the relax pass, and putting it in `fixed` so no later pass repaints it - and the coat
        # skips `fixed`. Protected here, the whole hind limb kept its build-time red and the animal
        # came out with white front socks and BARE RED HIND FEET. The relax protection it actually
        # needs comes from the cell set handed to `_relax_mass`, not from this flag.
        loft.sweep(fr, (d["hock_f"], st, d["hock_y"]), (knee, sp, d["paw_r"] * 0.75),
                   d["paw_r"] * 1.20, d["paw_r"], "coat")
        loft.sweep(fr, (knee, sp, d["paw_r"] * 0.75), (d["paw_f1"], sp, d["paw_r"] * 0.55),
                   d["paw_r"], d["paw_r"] * 0.90, "coat")
        loft.ball(fr, d["paw_f1"], sp, d["paw_r"] * 0.55, d["paw_r"] * 1.30, "coat",
                  rs=d["paw_r"] * 1.05, ry=d["paw_r"] * 0.70)


def _stump(fr: loft.Frame, d: dict) -> None:
    """The bobtail, HUNG OFF THE CROUP THAT WAS ACTUALLY BUILT.

    **A FEATURE PLACED AT A COMPUTED STATION IS INSIDE THE ANIMAL.** The first eleven builds put
    this ball at a fixed f behind the haunch's own centre, and the haunch reaches further back than
    that at every height the tail could sit at: it gained 32 cells - one course of skin thickness -
    and read as a bump. The mane came off as seven fragments, the ossicones detached and the ear
    tips broke away for the same reason, which is why `surface_out` exists.

    It also runs AFTER the relax pass, with the ears, because it is a thin protrusion and the rule
    that shaves a one-block pimple off a shoulder eats a nub whole - and because a stump built
    before smoothing is smoothed back into the rump it is supposed to stand out of.
    """
    y = loft.r(d["tail_y"])
    back = None
    for f in range(int(math.floor(-d["H"])), 2):
        if fr.solid(f, 0, y):
            back = f
            break
    if back is None:                       # no croup at this height: nothing to hang a tail on
        return
    # **A NUB, NOT A BALL, AND IT HAS TO CLEAR THE RUMP'S OWN REARMOST POINT.** Hung as a sphere a
    # third of a radius outside the surface it stood exactly flush with the widest part of the
    # bottom - 26 cells that filled the croup's curve back to vertical and changed the outline by
    # nothing, which is the same failure as placing it at a computed f, one step further on. A
    # sitting dog's tail leaves the TOP of the croup and points back and UP, so it is a short
    # tapered sweep rooted well inside the mass (a fat overlap is what keeps it 6-connected at
    # every size) and reaching a clear two blocks past the silhouette behind it.
    loft.sweep(fr, (back + d["tail_r"] * 0.5, 0.0, d["tail_y"]),
               (back - d["tail_r"] * 2.0, 0.0, d["tail_y"] + d["tail_r"] * 0.7),
               d["tail_r"], d["tail_r"] * 0.70, "coat")


def _clear_below(d: dict, f: float) -> float:
    """The course below which air must STAY air at station `f`.

    Only in front of the haunch: behind it the animal is sitting on the ground and there is no
    undercarriage to protect. In front, this is the slot between the two forelegs and the daylight
    either side of them - and if it closes, a sitting dog becomes a sack.
    """
    front_of_haunch = d["haunch"][0] + d["haunch"][2] * 0.55
    if f <= front_of_haunch:
        return 0.0
    return d["chest"][1]


def _relax_mass(fr: loft.Frame, d: dict, protect: set) -> dict:
    """Step 2 of CLAUDE.md's build order - `mass -> relax -> features -> face -> coat`.

    **`quadruped.py`'s OWN NUMBERS** - four rounds at fill 11 and keep 11, which is what the giraffe
    is built with. The stegosaur ran one round at fill 15 / keep 8 and measured `spike_rate` 9.4
    against the giraffe's 4.0; the warning that "every smoothing pass rewards thickening" is about
    tuning smoothing ALONE against the rubric and is not an argument for under-smoothing.

    **ONLY THE LEGS ARE PROTECTED.** A protected cell is never shaved, so protecting the head and
    the muzzle as well leaves them exactly as lumpy as they were built while the mass smooths around
    them. A foreleg genuinely has too few neighbours to survive `keep`; a skull does not.

    **AND THE AIR IN FRONT OF AND BETWEEN THE FORELEGS IS FORBIDDEN, except inside a leg's own
    cylinder** - filling is blind to anatomy and reads a two-cell slot between two legs as a dent
    worth closing, which welded the giraffe's four legs into one part for its whole lower half. The
    reach is CLAMPED TO HALF THE LEG SPACING, this file's own rule: unclamped, a thigh standing 2.8
    off the midline with a radius of 1.9 reaches the midline itself and protects nothing.
    """
    c = fr.c
    mass = _solid_cells(c)
    reach = min(d["leg_r0"] + 0.6, max(0.6, d["leg_s"] - 0.6))
    forbid = set()
    for v in range(c.sx):
        for u in range(c.sz):
            f, sd = fr.fs(v, u)
            inside_leg = (abs(abs(sd) - d["leg_s"]) < reach
                          and -d["leg_r0"] < f < d["foot_f"] + d["foot_r"] * 2)
            inside_paw = (abs(abs(sd) - d["paw_s"]) < d["paw_r"] + 0.6
                          and d["paw_f0"] - 1 < f < d["paw_f1"] + 1)
            if inside_leg or inside_paw:
                continue
            for y in range(int(math.ceil(_clear_below(d, f))) + 1):
                if (v, y, u) not in mass:
                    forbid.add((v, y, u))
    out = smooth.relax(mass, rounds=int(d["relax_rounds"]), fill=int(d["relax_fill"]),
                       keep=int(d["relax_keep"]), protect=protect, forbid=forbid)
    coat = c.state(HIDE["coat"])
    for (v, y, u) in mass - out:
        c.put(v, y, u, 0)
    for (v, y, u) in out - mass:
        c.put(v, y, u, coat)
    before, after = smooth.roughness(mass), smooth.roughness(out)
    return {"filled": len(out - mass), "shaved": len(mass - out),
            "spike_rate": [round(before["spike_rate"], 2), round(after["spike_rate"], 2)],
            "notches": [before["notches"], after["notches"]],
            "jerk_rel": [round(before["jerk_rel"], 1), round(after["jerk_rel"], 1)]}


# ---------------------------------------------------------------------------------- the ears


def _ears(fr: loft.Frame, d: dict) -> dict:
    """Two upright sheets, ANCHORED ON THE CROWN THAT WAS ACTUALLY BUILT.

    **ANYTHING CLINGING MUST BE ANCHORED TO THE BUILT SURFACE, NEVER PLACED AT A COMPUTED HEIGHT.**
    Relax moves the surface: the lion's mane came off as seven floating fragments, the giraffe's
    ossicones detached, a cat's ear tips broke away on the diagonal. `Frame.top_y` finds the crown
    each column actually has, and every course is threaded to the one below it so the sheet is
    6-connected by construction rather than by a step size that happens to be fine enough.

    **THE GAP BETWEEN THE EARS IS A FEATURE.** Run together across the midline they are a crest, not
    a pair - the ladybird's spot spacing and the frog's eye pair, arrived at from a third direction.
    The bases stop clear of s=0 and the tips lean further apart still.

    **AND THE BORDER IS WHAT MAKES IT AN EAR RATHER THAN A TAB.** The front face is cream inside a
    coat-coloured outline, which is what the inside of a dog's ear looks like and is the single
    strongest thing in the head-on view. Drawn as one flat colour the pair reads as two red flags.
    """
    H, cells = d["H"], 0
    top = d["ear_top"]
    for sgn in (1, -1):
        # each course, base to tip: (f centre, s centre, half-span across)
        plan = []
        n = max(3, int(round(top * 0.5)))
        for i in range(n + 1):
            t = i / n
            fc = d["ear_f0"] + (d["ear_f1"] - d["ear_f0"]) * t
            sc = sgn * (d["ear_c0"] + (d["ear_c1"] - d["ear_c0"]) * t)
            half = d["ear_half0"] + (d["ear_half1"] - d["ear_half0"]) * t
            plan.append((t, fc, sc, half))
        # THE BASE COURSE IS FOUND, NOT ASSUMED: the crown under the ear's own centre column.
        crown = fr.top_y(plan[0][1], plan[0][2], ceiling=fr.c.sy - 1)
        if crown is None:
            raise ValueError("the skull has no crown under the ear base: the head is not built")
        base_y = crown - 1                          # one course down, so the ear is rooted IN it
        span = max(2.0, top - base_y)
        prev = None
        for (t, fc, sc, half) in plan:
            y = base_y + span * t
            lo, hi = loft.r(sc - half), loft.r(sc + half)
            if lo > hi:
                lo, hi = hi, lo
            # **EACH EAR STAYS ON ITS OWN SIDE OF THE MIDLINE.** Guarded only against s=0 the two
            # rows both reached to s = -/+1 and OVERLAPPED there, so whichever ear the loop built
            # second painted over the first - the shape stayed exactly symmetric and the COLOUR did
            # not, which is the one cell the mirror check kept reporting at every size. A guard
            # written against the centre column is not a guard against crossing it.
            row = [k for k in range(lo, hi + 1) if k * sgn >= 1]
            if not row:
                row = [sgn]
            thick = max(1, loft.r(d["ear_d0"] + (d["ear_d1"] - d["ear_d0"]) * t))
            for k, s in enumerate(row):
                edge = (k == 0 or k == len(row) - 1 or t > 0.90)
                for df in range(thick):
                    f = fc + df - (thick - 1) / 2.0
                    if df == thick - 1 and thick > 1:
                        # the face that looks FORWARD: cream inside a coat-coloured outline, which
                        # is what the inside of a dog's ear looks like and is the single strongest
                        # thing in the head-on view
                        key = "coat" if edge else "cream"
                    elif df == 0 and thick > 2:
                        key = "sable"            # the back of the ear, a shade deeper than the head
                    else:
                        key = "coat"
                    if fr.put(f, s, y, key, protect=True):
                        cells += 1
            # ...and a threaded spine up the middle of the sheet, so no course can be left
            # diagonal to the one below it however the rounding falls
            here = (fc, sc, y)
            if prev is not None:
                loft.thread(fr, prev, here, "coat", protect=True)
            prev = here
    return {"cells": cells}


def _toes(fr: loft.Frame, d: dict) -> int:
    """Three toes on each forepaw - separated by AIR and tapered by LENGTH, not by half-blocks.

    **A HAND IS MOSTLY AIR.** The frog's own recorded finding, after four arrangements of full
    blocks read as a rake, a comb, a plus sign and a set of random lines: three prongs with a clear
    cell between them are a foot, and the same three filled in are a boot. The gaps are the feature,
    which is the ear pair's rule and the ladybird's spot spacing arrived at from a third direction.

    **AND THERE IS NO STAIR TO TAPER THEM WITH, WHICH IS A MEASUREMENT RATHER THAN AN OMISSION.**
    The frog's toes are stairs, because a cube toe ends at a vertical face and a stair toe falls
    away - and these toes sit on the white socks. Measured over this economy there is NO pale stair
    to do it with: wool has no slab in the game at all, `bone_block` and `diorite` have no trusted
    slab, and `smooth_quartz`, `calcite` and `quartz_block` are every one of them expensive. A red
    stair on a white sock is worse than a blunt white toe, so the taper is carried by the middle toe
    being longer than the outer pair, and the separation by the air between them.
    """
    out = 0
    # **THE SCAN STARTS IN FRONT OF THE FRONTMOST PAD.** Derived from the leg's radius alone it was
    # a number that happened to cover the feet while they stood under the chest; the front paw is
    # forward of the chest plane now and a toe whose search never reaches its own pad is a toe that
    # roots on the animal behind it.
    reach = int(math.ceil(max(d["foot_f"] + d["foot_r"], d["paw_f1"] + d["paw_r"]))) + 2
    # **BOTH FEET, because the front paw and the hind paw TOUCH and no spacing separates them.**
    # A sitting dog's feet really are side by side; what breaks them into two feet for a viewer is
    # the toes, which is the frog's "a hand is mostly air" said about a foot. Given none, the whole
    # ground course reads as one white pad and the hind leg is invisible however well it is built.
    for sgn in (1, -1):
        for s0 in (loft.r(sgn * d["leg_s"]), loft.r(sgn * d["paw_s"])):
            for k in (-1, 0, 1):
                s = s0 + k * 2                   # ONE clear cell between toes: the gap is the toe
                # **THE TOE WALKS BACK TO THE PAD'S OWN FRONTMOST CELL, AND A TOE WITH NO FOOT IS
                # SKIPPED.** Started at a computed offset the inner toe landed in the slot BETWEEN
                # the two legs, where the paw's ellipsoid has nothing at the ground course: two
                # one-cell components, a clean audit, a correct bill of materials and a render that
                # showed a perfectly good foot. The frog's toes detached at three lengths out of
                # nine for exactly this.
                root = None
                for i in range(reach, -1, -1):
                    if fr.solid(i, s, 0):
                        root = i
                        break
                if root is None:
                    continue
                length = max(1, int(round(d["toe_len"] * (1.0 if k == 0 else 0.70))))
                for i in range(1, length + 1):
                    if fr.put(root + i, s, 0, "coat"):
                        out += 1
    return out


# ---------------------------------------------------------------------------------- the coat


def _back_at(fr: loft.Frame, d: dict) -> dict:
    """The measured top of the mass at each forward station - the back LINE, not a computed one.

    Written as a fraction of a column's own height the bands follow whatever that column happens to
    be, and on a lofted body every column is different: the result is not three bands, it is grey
    blotches wandering the flank, which a close render reads as mould. That was most of what "super
    blocky and rough" turned out to mean on the stegosaur, and it was not geometry at all.
    """
    c, out = fr.c, {}
    for v in range(c.sx):
        for u in range(c.sz):
            f, _s = fr.fs(v, u)
            for y in range(c.sy - 1, -1, -1):
                if c.solid(v, y, u):
                    fk = int(round(f))
                    out[fk] = max(out.get(fk, 0), y)
                    break
    return out


def _front_cells(fr: loft.Frame) -> set:
    """Cells whose FORWARD neighbour is air - the surface a visitor standing in front of it sees.

    The bib is a front-facing zone rather than a band at a height, because on a seated animal the
    chest, the throat and the sternum are all different heights and all the same marking. Defined
    by height alone it wraps round the flanks and the dog gets a white belt.
    """
    c, out = fr.c, set()
    for (v, y, u) in _solid_cells(c):
        av, au = v + fr.fx, u + fr.fz
        if not (0 <= av < c.sx and 0 <= au < c.sz) or not c.solid(av, y, au):
            out.add((v, y, u))
    return out


def _coat(fr: loft.Frame, d: dict) -> dict:
    """The pattern: a sable drift along the back, then the white markings, hard-edged.

    **THE MARKINGS DO NOT DITHER AND THE SHADING DOES.** A Pembroke's white is a MAP - blaze, bib,
    socks, bum - and softening its edge turns a marking into weathering, which is the deck soffit's
    confetti with the sign reversed. The sable/coat boundary is the opposite case: it is shading, so
    the noise goes on the BOUNDARY and never on the interior, which is the thicket's rule (191 blobs
    of which 75% were one or two cells, until the noise moved off the cell and onto the radius).

    **AND THE DITHER IS HASHED ON THE DISTANCE FROM THE MIDLINE.** Keyed on the column it is a
    different number on each flank, and the animal comes out exactly symmetric in SHAPE and sixteen
    cells adrift in COLOUR - the frog's own recorded fault, where every coat drift carried its own
    signed offset.
    """
    c = fr.c
    S = {k: c.state(HIDE[k]) for k in ("coat", "sable", "cream")}
    back = _back_at(fr, d)
    front = _front_cells(fr)
    tally = {"coat": 0, "sable": 0, "cream": 0}
    for (v, y, u) in sorted(_solid_cells(c)):
        if (v, y, u) in fr.fixed:
            continue
        f, across = fr.fs(v, u)
        a = abs(across)
        key = "coat"

        # --- the sable drift along the spine, off the MEASURED back line
        top = back.get(int(round(f)))
        if top is not None and f <= d["sable_to"]:
            # **THE NOISE GOES ON THE BOUNDARY AND IT HAS TO BE BIG.** A constant offset from the
            # measured top of a DOMED back is a contour line by construction, and the first build
            # drew the rump as a set of dark rings. At noise comparable to the band's own depth the
            # boundary lobes instead, which is the thicket's rule - 191 blobs of which 75% were one
            # or two cells, until the noise moved off the cell and onto the radius.
            jitter = (hash01(a // 2, y // 2, int(round(f)) // 2, 5, 11) - 0.5) * (d["sable_band"] * 1.6)
            if y > top - d["sable_band"] + jitter:
                key = "sable"

        # --- the white markings, hard-edged, each one a real thing on a real dog
        cream = False
        if y <= d["under_y"]:                                       # the undercarriage and pads
            cream = True
        elif (y <= d["fore_sock_y"] and f >= d["leg_f"] - d["leg_r0"] * 1.1
              and abs(a - d["leg_s"]) < d["leg_r0"] * 1.25):
            cream = True                                             # the front socks, to the wrist
        elif (y <= d["sock_y"] and f >= d["hock_f"] - 1.0
              and (abs(a - d["leg_s"]) < d["leg_r0"] * 1.25
                   or abs(a - d["paw_s"]) < d["paw_r"] * 1.4)):
            cream = True                                             # the hind sock, on the FOOT
            # **AND IT IS BOUNDED FORWARD, WHICH IT NEVER WAS.** The branch's own comment said "on
            # the FEET only" and it carried no forward bound at all, so it whited a hem at that
            # height from the nose to the tail: 481 of 487 skin cells in the bottom band, which is
            # two thirds of all the white on the animal and a white plinth under the whole statue.
            # `_hind`'s contract is that the thigh above is RED and the pastern below is WHITE, and
            # a hem that reaches the rump has no thigh left to be red.
            # **A SOCK IS ON A LEG, AND `a > leg_s - r` IS TRUE ALMOST EVERYWHERE.** Written as a
            # threshold rather than as a distance to the leg's own axis it whited every cell of the
            # animal below the pastern - the belly, the rump's underside and the ground contact all
            # at once - and the profile grew a white plinth running the full depth of the statue.
        elif (f >= 0.0 and (v, y, u) in front
              and d["bib_lo"] <= y <= d["bib_hi"] and a <= d["bib_half"]):
            cream = True                                             # the bib
            # **AND IT IS BOUNDED BEHIND.** `front` is any cell whose forward neighbour is air,
            # which is true of every concavity on the animal, not only of the chest - the tail nub
            # slopes up and away from the croup, so its own tip qualified and one white cell
            # appeared on a red bobtail fifteen courses up at the BACK of the dog.
        elif (f >= 0.0 and (v, y, u) in front and d["bib_hi"] < y <= d["throat_hi"]
              and a <= d["throat_half"] and f < d["muzzle_a"][0]):
            cream = True                                             # the throat, UNDER THE JAW
            # **AND BEHIND THE MUZZLE.** Unbounded forward it climbs the front of the snout and
            # whites the BRIDGE - the one strip of red the blaze is supposed to run down - so the
            # face came out white from the nose to the eyes with no bridge left to mark.
        elif (f >= d["muzzle_a"][0] and y < _muzzle_y(d, f)
              and a <= _muzzle_r(d, f) + 1.4):
            cream = True                                             # the muzzle BELOW ITS OWN AXIS
            # **THE BRIDGE STAYS RED AND SO DO THE CHEEKS.** Written as "the whole head below the
            # skull's centre" this whited the muzzle, both cheeks and the jowls at once, and the
            # animal came out 35% white against a Pembroke's ~22% - a husky's mask, not a corgi's
            # markings. What a corgi actually has is white on the muzzle SIDES and the chin with
            # the bridge red between them, which is the surface the blaze then runs up.
        elif (a <= _blaze_half(d, y) and f >= d["skull_f"] - d["skull_rf"] * 0.2):
            cream = True                                             # the blaze, nose to crown
        elif f <= d["bum_f"] and d["bum_lo"] <= y <= d["bum_hi"]:
            cream = True                                             # the white rear
        if cream:
            key = "cream"

        c.put(v, y, u, S[key])
        tally[key] += 1
    return tally


# ---------------------------------------------------------------------------------- the face


def _face(fr: loft.Frame, d: dict) -> dict:
    """The nose, the mouth line and the eyes - the three marks that make a blocky front a FACE.

    **THE NOSE IS FOUND, NOT FILLED.** Painted as every cell of the front two stations it is not a
    nose, it is a black MUZZLE - the ankylosaur's beak came out as 84 cells and the animal had a
    robot's face. It is the frontmost solid cell of each line through the muzzle tip and nothing
    else.

    **AND THE MOUTH TURNS UP.** What makes a blocky front a face is a LINE: the frog's recorded
    finding, where five passes of eye work went into a front that was a pale rectangle and what
    fixed it was one dark line across it. Here the line runs across the front of the muzzle and
    carries back along each jaw - drawn on the front plane alone it is a head-on-only feature and
    the profile has no mouth at all - and it STEPS UP one course at its back end, which is the
    corgi smile and is the single most recognisable thing about the breed's face.
    """
    H = d["H"]
    nf, ny = d["muzzle_b"]
    reach = int(math.ceil(d["muzzle_r0"])) + 2
    out = {"nose": 0, "mouth": 0}

    def _jaw(f):
        """The muzzle's real lowest course at station `f` - **FOUND, NEVER COMPUTED.**

        Derived from the nominal half-height it lands one course INTO THE AIR: `loft.ball` rounds
        each offset from a float centre, so the lowest course the snout actually has is not the one
        the arithmetic names, and the whole mouth was drawn against nothing. This repo's oldest rule
        about features, and the relax pass moves this surface as well.
        """
        top = loft.r(_muzzle_y(d, f))
        found = None
        for probe in range(top, top - 8, -1):
            if fr.solid(f, 0, probe):
                found = probe
        return found

    # **EVERY MARK ON THE SNOUT IS MEASURED UP FROM THE FOUND JAW, NOT FROM THE AXIS.** Derived
    # independently the nose and the mouth landed on adjacent courses THREE separate times - a
    # 3 x 4 black slab where a face should be, which is a bandit mask - because each was correct
    # about its own arithmetic and neither knew where the other was. Anchored to one course they
    # cannot collide: the mouth is the jaw, the course above it is white by construction, and the
    # nose starts above that. It is the same reasoning that put `skull_rs` in terms of the ear's
    # own reach rather than choosing it.
    jaw = _jaw(nf)
    if jaw is None:
        raise ValueError("the muzzle has no lowest course to hang a face on: it did not build")
    top_of_snout = loft.r(_muzzle_y(d, nf) + _muzzle_h(d, nf))
    nose_lo = jaw + 2
    # TWO COURSES, and a third only when there is a spare one - the course under the eyes is the
    # BRIDGE, and it has to stay red or the blaze has nothing to run down and the nose runs into
    # the eyes instead.
    nose_hi = min(nose_lo + 1, top_of_snout - 1)
    if top_of_snout - nose_lo >= 4:
        nose_hi = nose_lo + 2

    # ---- the nose: a solid pad on the front of the snout, found on the skin.
    # **A CIRCLE EQUATION AT RADIUS ONE IS A PLUS SIGN, NOT A DISC.** `dx**2 + dy**2 <= r**2` at
    # r ~ 1.1 admits exactly the centre and its four orthogonal neighbours, and the nose shipped as
    # a black CROSS. The frog records the same thing about its own blotches. Raising the exponent
    # is not enough either - at n=3 the corner test still came to 1.10 - so at this size the honest
    # shape is a rectangle whose corners are clipped only when there are corners worth clipping.
    nose_rw = max(1, int(round(d["muzzle_r1"] * 0.75)))
    for ds in range(-nose_rw, nose_rw + 1):
        for y in range(nose_lo, nose_hi + 1):
            if nose_rw >= 2 and abs(ds) == nose_rw and y in (nose_lo, nose_hi):
                continue
            for step in range(0, reach + 4):
                f = nf + d["muzzle_r1"] + 1 - step
                if fr.solid(f, ds, y):
                    if fr.put(f, ds, y, "nose", protect=True):
                        out["nose"] += 1
                    break

    def _jaw(f):
        """The muzzle's real lowest course at station `f` - **FOUND, NEVER COMPUTED.**

        Derived from the nominal half-height it lands one course INTO THE AIR: `loft.ball` rounds
        each offset from a float centre, so the lowest course the snout actually has is not the one
        the arithmetic names, and the whole mouth was drawn against nothing. This repo's oldest rule
        about features, and the relax pass moves this surface as well.
        """
        top = loft.r(_muzzle_y(d, f))
        found = None
        for probe in range(top, top - 7, -1):
            if fr.solid(f, 0, probe):
                found = probe
        return found

    # ---- ACROSS THE FRONT OF THE SNOUT, on the frontmost cell of each line.
    # **THE LINE HAS TO BE ON THE SURFACE OR IT IS INSIDE THE HEAD.** Placed at the station the
    # loop was standing on, the front of the mouth came to rest BEHIND the snout's own front face
    # and the head-on view - this animal's money view - showed a white chin with two dots on it.
    # It is the same fix the nose needs and the axolotl's eye needed: walk forward to the skin.
    jy = jaw
    if jy is not None:
        for ds in range(-reach, reach + 1):
            for step in range(0, reach + 4):
                f = nf + d["muzzle_r1"] + 1 - step
                if fr.solid(f, ds, jy):
                    if fr.put(f, ds, jy, "mouth", protect=True):
                        out["mouth"] += 1
                    break

    # ---- ...AND BACK ALONG EACH JAW, on the outermost cell, TURNING UP at the corner.
    # Drawn on the front plane alone it is a head-on-only feature and the profile has no mouth in
    # it at all; and the lift at the end is the whole of the difference between a mouth and a slot,
    # which is what everybody draws when they draw a happy dog.
    back_len = max(3, int(round(0.110 * H)))
    for i in range(1, back_len + 1):
        f = nf - i
        jy = _jaw(f)
        if jy is None:
            continue
        rise = 1 if i >= back_len - 1 else 0
        for sgn in (1, -1):
            for sd in range(reach + 2, -1, -1):
                if fr.solid(f, sgn * sd, jy + rise) and not fr.solid(f, sgn * (sd + 1), jy + rise):
                    if fr.put(f, sgn * sd, jy + rise, "mouth", protect=True):
                        out["mouth"] += 1
                    break

    out.update(_eyes(fr, d))
    return out


def _eyes(fr: loft.Frame, d: dict) -> dict:
    """One bead a side, high on the skull's front corner and ON ITS SIDE SURFACE.

    **A COLUMN SCAN CANNOT FIND THE SKULL, BECAUSE THE SKULL IS NOT A SEPARATE COLUMN.** Written as
    the ankylosaur writes it - take the column at the head's own station, and search down from its
    upper third - the column runs unbroken from the GROUND to the crown on a seated animal, so
    `hi - lo` is the whole height of the statue and "the upper third of the skull" landed three
    cells BELOW the skull entirely, on the root of the muzzle. The pupils came to rest two cells
    from the nose on the same course and the face read as one black bar. That animal had a
    perfectly clean audit, a correct bill of materials, `eyes: 2` in its own sidecar, and no eyes.

    **SO THE COURSE IS DERIVED FROM THE ANATOMY AND THEN FOUND WITHIN A WINDOW.** A dog's eye sits
    just above and behind where the muzzle leaves the skull - that is a relationship between two
    parts this generator already knows - and the search is a couple of courses either side of it,
    which keeps the repo's rule that a feature is measured off the built surface rather than placed
    at a computed radius.

    **AND IT TAKES THE OUTERMOST SOLID PAIR**, so the bead lands on the side of the head rather than
    inside the brow. Set inboard it exists only in the plan view: the profile is this animal's
    second money view and it had no eye in it at all.
    """
    want_y = d["muzzle_a"][1] + 0.030 * d["H"]
    f = d["skull_f"] + d["skull_rf"] * 0.85
    reach = int(math.ceil(d["skull_rs"])) + 1
    window = max(2, int(round(0.035 * d["H"])))
    for dy in [0] + [k for i in range(1, window + 1) for k in (i, -i)]:
        y = loft.r(want_y) + dy
        for sd in range(reach, 0, -1):
            if not (fr.solid(f, sd, y) and fr.solid(f, -sd, y)):
                continue
            # **ONE CELL, AND NO PALE RING.** The ring is the axolotl's fix for a bead the coat can
            # swallow, and here the coat cannot: `black_wool` L21 on `acacia_planks` L104 is 83 of
            # contrast against this file's own 35 threshold, and with the sable drift held off the
            # head there is nothing dark near it. Ringed as well the pair came out as two five-cell
            # blobs - the frog's "the eyes are giant boxes".
            # **AND THEN ONE CELL INBOARD.** Left on the outermost solid column the bead is ON the
            # silhouette, and a black cell on an outline is not an eye - it is a notch, which under
            # the ear bases read as two shadows rather than as a face. Stepped in by one it sits in
            # the head with the cheek's own edge beside it, and still catches the profile because
            # the head falls away immediately outboard of it.
            inb = sd - 1 if sd > 1 and fr.solid(f, sd - 1, y) and fr.solid(f, -(sd - 1), y) else sd
            # **AND THEN FORWARD, TO THE FRONTMOST CELL OF ITS OWN CHEEK BAND.** Placed at the
            # station the search happened to be standing on, the bead came to rest ONE CELL DEEP -
            # there was solid head in front of it - so it existed in the model, in the sidecar and
            # in the part count, and was invisible from the one view this animal is built for. The
            # axolotl records exactly this: *"chosen by proximity instead ... one bead landed a
            # cell deep, painted over from exactly the head-on view"*. Taking the frontmost cell of
            # the band makes an occluded eye impossible by construction rather than by luck.
            out = {"eyes": 2, "eye_y": y, "eye_s": inb}
            for sgn in (1, -1):
                ef = f
                for step in range(1, int(math.ceil(d["skull_rf"])) + 4):
                    if not fr.solid(f + step, sgn * inb, y):
                        break
                    ef = f + step
                fr.put(ef, sgn * inb, y, "eye", protect=True)
            return out
    raise ValueError("no course near the brow carries a pair of eyes: the head is too small at this "
                     "height, and an animal that ships eyeless does it silently")


# ------------------------------------------------------------------------------- the surfacing


def _skin(fr: loft.Frame, d: dict) -> dict:
    """{cell: block name} for the animal's own COAT - never a drawn feature, and never the face.

    `gen/shell.py` chamfers a step by replacing the cell with a stair of the nearest colour, which
    is exactly right on a haunch and is vandalism on a face: on the ankylosaur it picked a green-grey
    slab and an orange stair out of the coat's own colour families and scattered them over the
    muzzle. The frog states the rule for its own build - *"the face, the belly, the eyes and the
    feet are drawn features and a stair through one of them is a hole in a drawing"* - and it
    belongs to the SKIN function rather than to each caller, or the next pass forgets it.

    **AND THE WHITE MARKINGS TAKE NO PARTIALS AT ALL**, which is honest rather than fixable: wool
    has no slab in the game, `bone_block` is a `rotated_pillar` that `slab_for` refuses on sight,
    and `smooth_quartz` is expensive on this economy. The red mass gets the relief; the markings
    stay full cubes, and at a 132-luminance step the boundary is doing the work anyway.

    A palette entry is an NBT Tag, so `str()` on it is a repr: read that way every name matches
    nothing, every colour lookup fails and the surfacing pass reports zero cells while looking
    exactly like a pass that had nothing to do.
    """
    c = fr.c
    names = [nbt.state_name(e).split(":")[-1].split("[")[0] for e in c.reg.palette]
    # **THE CUTOFF IS THE BACK OF THE SKULL, NOT THE ROOT OF THE MUZZLE.** Set at the muzzle the
    # pass still owns the whole cranium, and it chamfered the brow, the crown and the blaze into a
    # field of orange stairs - the ankylosaur's recorded fault verbatim, and it wrecks the one view
    # this animal is built for. A head is a DRAWN feature from the ears down.
    face = d["skull_f"] - d["skull_rf"]
    partial = {HIDE["coat"], HIDE["sable"]}
    out = {}
    for (v, y, u) in _solid_cells(c):
        if (v, y, u) in fr.fixed or (v, y + 1, u) in fr.fixed:
            continue
        if fr.fs(v, u)[0] >= face:
            continue
        name = names[int(c.ids[y, u, v])]
        if name in partial:
            out[(v, y, u)] = name
    return out


def _surface(fr: loft.Frame, d: dict) -> dict:
    """Stair and half-block surfacing over the coat, through `gen/shell.py`.

    STAIRS FIRST, THEN SLABS ON WHAT IS LEFT: on the top face the two are disjoint by construction -
    a slab wants NO higher neighbour and a stair wants exactly one - but an underside stair and a
    top slab can both want the same cell, and a cell may only have one shape.
    """
    c = fr.c
    skin = _skin(fr, d)
    ramps = shell.stair_shell(set(skin), skin, HIDE["coat"], under=True, floor_y=0)
    rest = {k: v for k, v in skin.items() if k not in ramps}
    cut = shell.slab_shell(set(rest), rest, HIDE["coat"], floor_y=0)
    for cell, (name, props) in list(ramps.items()) + list(cut.items()):
        c.put(cell[0], cell[1], cell[2], c.state(name, **props))
    tops = sum(1 for _n, p in ramps.values() if p["half"] == "bottom")
    return {"stairs": len(ramps), "stairs_under": len(ramps) - tops,
            "slabs": len(cut), "skin": len(skin)}


def _mirror(fr: loft.Frame) -> dict:
    """**ENFORCE THE MIRROR, NEVER ASSUME IT.**

    Every part here is built for both signs and every span is centred, so the shape is symmetric by
    construction - and the squid was too, and came out 5,375 cells different left to right, because
    a limb swept from a float centre mirrors about a column's EDGE rather than its middle.

    **AND A FACING MIRRORS, IT DOES NOT COPY.** Written the obvious way the sweep assigns each
    cell's state verbatim to its twin, and 60 of the frog's 134 stairs came out facing the same way
    on both sides - a chamfer leaning into the wall on one flank and out of it on the other, which
    `render3d` drew identically until `subdivide` learned to expand a stair. Only the ACROSS axis
    flips; a stair leaning fore or aft leans the same way both sides.
    """
    c = fr.c
    shape = colour = 0
    reach = max(c.sx, c.sz)
    across_x = fr.sx != 0
    flip = {"east": "west", "west": "east"} if across_x else {"north": "south", "south": "north"}
    for f in range(-reach, reach + 1):
        for s in range(1, reach + 1):
            (av, au), (bv, bu) = fr.at(f, s), fr.at(f, -s)
            if not (0 <= av < c.sx and 0 <= au < c.sz and 0 <= bv < c.sx and 0 <= bu < c.sz):
                continue
            for y in range(c.sy):
                sa, sb = c.solid(av, y, au), c.solid(bv, y, bu)
                if sa != sb:
                    shape += 1
                    continue
                if not sa:
                    continue
                ea, eb = c.reg.palette[int(c.ids[y, au, av])], c.reg.palette[int(c.ids[y, bu, bv])]
                na, nb = nbt.state_name(ea), nbt.state_name(eb)
                pa = dict(nbt.state_props(ea) or {})
                pb = dict(nbt.state_props(eb) or {})
                if "facing" in pa:
                    pa["facing"] = flip.get(pa["facing"], pa["facing"])
                if na != nb or pa != pb:
                    colour += 1
    return {"shape": shape, "colour": colour}


# ------------------------------------------------------------------------------------- the build


def build_corgi(cfg: dict, donors=None) -> Canvas:
    p = {**CORGI, **(cfg or {})}
    H = float(p.get("height") or 32) * float(p.get("scale") or 1.0)
    if H < 24:
        raise ValueError(
            "a corgi under 24 blocks tall cannot carry its own ears, and the ears are what name "
            "it. The base of an ear is 0.150 of the total height, so below 24 it is under four "
            "cells across and cannot hold a coat-coloured border round a cream core - which leaves "
            "two red tabs on a head. `tools/scale.py`'s doctrine is that an animal's critical size "
            "is the largest of its features' own floors, and here that feature is the ear")
    d = _dims(H)
    for k in ("relax_rounds", "relax_fill", "relax_keep"):
        if p.get(k) is not None:
            d[k] = p[k]
    facing = str(p.get("facing", "north"))
    if facing not in loft.STEP:
        raise ValueError(f"a corgi needs a real facing, not {facing!r}")

    # **THE CANVAS IS SIZED BY THE FACING, NOT BY THE ANIMAL.** A box that is always long in X is
    # long in the WRONG axis for a north-south animal: the sauropod built facing north came out
    # clipped to 22 blocks of 48 - head, neck and half the tail simply refused - and the render
    # still showed a plausible small dinosaur, because what survived was the near end.
    # **AND THE MARGINS ARE A FRACTION, NOT A CONSTANT.** Fixed at 3 they are generous at 24 and
    # gone by 60: the toes, the ears and the paws all scale, so the room they need past the nominal
    # body scales with them.
    pad = int(math.ceil(0.06 * H)) + 3
    span_fore = int(math.ceil(max(d["muzzle_b"][0] + d["muzzle_r1"] * 2,
                                  d["foot_f"] + d["foot_r"] + d["toe_len"]) + d["toe_len"])) + pad
    span_back = int(math.ceil(-(d["haunch"][0] - d["haunch"][2])
                              + d["tail_r"] * 3)) + pad
    length = span_fore + span_back + 1
    width = int(math.ceil(max(d["haunch"][3], d["paw_s"] + d["paw_r"],
                              d["ear_c1"] + d["ear_half1"] + 1) * 2)) + 2 * pad
    sy = int(math.ceil(d["ear_top"])) + pad

    along_x = facing in ("east", "west")
    sx = length if along_x else width
    sz = width if along_x else length
    c = Canvas(sx, sy, sz, donors)
    cv = span_back if along_x else sx // 2
    cu = sz // 2 if along_x else span_back
    if facing == "east":
        cv = sx - 1 - span_back
    if facing == "south":
        cu = sz - 1 - span_back
    fr = loft.Frame(c, cv, cu, facing, HIDE)

    # MASS -> RELAX -> FEATURES -> FACE -> COAT, which is CLAUDE.md's own build order. Features go
    # in after the smoothing because the rule that shaves a pimple off a shoulder eats an ear whole,
    # and the coat goes last because the pattern must measure the ANIMAL rather than the plan.
    # **A PART'S COUNT IS UNIQUE CELLS, NEVER `put()` CALLS.** A sweep steps finely enough that its
    # spheres overlap, so a call count is an artefact of how a part is DRAWN: the squid's sidecar
    # reported 251,264 arm blocks in a 116,000-block animal, which reads as a measurement, and the
    # ankylosaur's horns reported 124 placements while gaining ZERO cells because every one of them
    # landed inside the skull.
    seen: set = set()

    def _step(fn):
        nonlocal seen
        fn()
        now = _solid_cells(c)
        new_cells = now - seen
        seen = now
        return new_cells

    parts = {"body": len(_step(lambda: _body(fr, d)))}
    parts["head"] = len(_step(lambda: _neck_head(fr, d)))
    muzzle = _step(lambda: _muzzle(fr, d))
    parts["muzzle"] = len(muzzle)
    legs = _step(lambda: _legs(fr, d))
    parts["legs"] = len(legs)
    hind = _step(lambda: _hind(fr, d))
    parts["hind"] = len(hind)
    parts["relax"] = _relax_mass(fr, d, protect=legs | muzzle | hind)
    seen = _solid_cells(c)
    # **THE STUMP IS A FEATURE, SO IT GOES IN AFTER THE SMOOTHING** - the rule that shaves a
    # one-block pimple off a shoulder eats a nub whole, and a tail built into the mass is a tail
    # smoothed back into the rump it exists to stand out of.
    parts["stump"] = len(_step(lambda: _stump(fr, d)))
    parts["ears"] = len(_step(lambda: _ears(fr, d)))
    parts["toes"] = len(_step(lambda: _toes(fr, d)))
    parts["coat"] = _coat(fr, d)
    parts.update(_face(fr, d))
    parts["surface"] = _surface(fr, d)
    parts["mirror"] = _mirror(fr)

    if p.get("stand"):
        wx, wy, wz = (int(round(float(v))) for v in p["stand"])
        c.world_origin = (wx - cv, wy, wz - cu)
    elif p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    c.meta = {
        "kind": "corgi",
        "facing": facing,
        "height": round(H, 1),
        "profile_axis": "u" if along_x else "v",
        # **THE FRAME'S OWN ORIGIN, so nothing has to re-derive it.** The test file used to repeat
        # this canvas arithmetic line for line, which is the trap `Work.sortKey` was pulled out for:
        # a checker that re-implements its subject grades a copy, and the day `tail_f` stopped
        # existing 55 tests failed on the duplicate rather than on the animal.
        "frame_origin": [cv, cu],
        "refused": fr.refused,
        "clipped": fr.clipped,
        "parts": parts,
        "contract": (
            "a sitting corgi: ONE convex seated mass - haunch on the ground, chest hanging between "
            "two short forelegs - carrying two oversized upright ear sheets with cream centres and "
            "coat-coloured borders. The markings are a MAP and never a shade: blaze, bib, socks, "
            "bum. A fox muzzle with a found nose, an upturned mouth line and one ringed bead a "
            "side. One piece, exactly symmetric in shape and in colour."),
    }
    return c


build = build_corgi
DEFAULTS = CORGI
