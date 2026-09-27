"""THE ANKYLOSAUR - a walking shield, and the one dinosaur shape this system is built for.

Jack, after four rounds on a standing stegosaur that measured well and never read:
*"full list of potential dinosaurs"* - and of the thirteen candidates this is the one that lands
squarely inside the category CLAUDE.md has proven rather than beside it.

**WHY THIS ONE, AND WHY THE STEGOSAUR WAS THE WRONG CALL.** The measured line in this repo is
PLANAR / COLUMNAR / ONE CONVEX MASS against VOLUMETRIC, and the download corpus sharpened it into
the sentence that matters: *"the line is not the species, it is whether the silhouette decomposes
into LIMBS"* - a corpus of 31 outside builds contains **no realistically-proportioned quadruped at
all**, and eight mammals were retired here for exactly that. A stegosaur on four legs decomposes
into four legs, a neck, a head and a tail; recommending it as "a convex mass with plates" was
reading the plates and ignoring what carries them.

**AN ANKYLOSAUR DOES NOT DECOMPOSE, AND THAT IS ITS ANATOMY RATHER THAN A POSE.** It is a low broad
armoured dome whose legs are short and tucked under the mass - the animal IS one convex shape, and
what identifies it is a PATTERN on that shape: rows of bone osteoderms, a fringe of lateral spikes,
and a club on the end of the tail. That is the ladybird's category and `Warm Snooze`'s, which are
the two shapes that read instantly in this medium, and none of it asks the voxel grid to describe a
joint.

**AND ITS MONEY VIEW IS THE PLAN, WHICH THIS SITE GIVES AWAY FREE.** The causeway's park skyway
passes overhead, so the view a visitor gets for nothing is the one an armoured shield is best in:
an oval of banded knobs with a club off the back and spikes round the rim. The walk itself gives
the profile, where a low mass with a raised shoulder and a club reads as nothing else.

PROPORTIONS ARE THE ANIMAL'S OWN. A real Ankylosaurus is about 4.3 times as long as it is tall and
nearly as wide as it is tall - so the shell is built WIDE and LOW, half-width 0.17 of the length
against a half-depth of 0.082. Built at the proportions a modeller reaches for by eye it is a
hippo; the whole point of the shape is that it is flatter and broader than feels right.

PALETTE - measured, and armour is bone because osteoderms ARE bone:

    brown_wool 79 . dripstone_block 112 . light_gray_wool 141 . bone_block 225

`dripstone_block` is the Lost Plateau's own rock tone (the declutter pass swapped the land's
andesite for it) and 66 RGB from the `moss_block` shoulder this stands on - `green_wool` is TWELVE
from it, which is the green-turtle mistake and is why nothing here is green. The armour at 225 sits
146 clear of the back it is bedded in, which is the largest step in the build and the reason the
pattern reads at all.
"""
from __future__ import annotations

import math

import numpy as np

from .. import nbt
from . import loft, shell, smooth
from .canvas import Canvas, hash01

#: Checked against `blocks.available` (1.19), `blocks.spendable` and `palette.tier` by
#: `tests/test_causeway_sculptures.py`, which asks the registry rather than trusting this list.
HIDE = {
    # **STACKING THE LADDER WITH THE LIGHT WAS TRIED AND IS WORSE. Recorded so nobody re-derives
    # it.** The reasoning is sound and the result is not: a renderer shades a top face brightest
    # and a bottom face darkest, so countershading (dark back, pale belly) multiplies out to the
    # same rendered value at every course, and the value panel is one flat mass. Inverted - pale
    # carapace, mid flanks, dark underside - the PROFILE got darker rather than lighter, because
    # what a profile shows is almost entirely SIDE faces and the side band had just been made the
    # darkest tone; and the plan went grey-green, because the surfacing pass picks its slabs off
    # the coat and a paler back drew cooler ones. The walkway gives you the profile and the skyway
    # gives you the plan, and the inversion cost both to fix a panel nobody stands in.
    "back": "brown_wool",           # L79  - the spine, bedded darkest
    "flank": "dripstone_block",     # L112 - the shell, and the land's own rock
    "belly": "light_gray_wool",     # L141 - countershading, read off the BUILT form
    "armour": "bone_block",         # L225 - the FRINGE, the horns and the club, and nothing else
    # **A KNOB IS THE HIDE RAISED, NOT A BONE STUCK ON IT.** Drawn in the fringe's own stark bone
    # the osteoderms read from the plan - this animal's money view - as a regular field of white
    # POLKA DOTS on brown: the deck soffit's confetti with the sign reversed, and the row-stagger
    # test passed the whole time because staggered dots are still dots. In `dripstone_block` they
    # are 33 of luminance over the back rather than 146, which is a raised bump catching light
    # instead of a rivet, and it leaves the bone to mean one thing - the features that stand PAST
    # the animal's own outline. The frog's rule ("a mark that means something different is a
    # different block") read the other way round: a mark that means the SAME thing must not be.
    "knob": "dripstone_block",      # L112 against the back's L79
    # **A FACE IS DRAWN, AND A DRAWN FEATURE NEEDS ITS OWN TONES.** Left to the coat and the mass
    # the head came out a smooth brown thumb with no eye, no beak and no mouth visible head-on -
    # and head-on is the bearing the walkway gives you first. These are the frog's own three moves:
    # a pale panel, a dark line across it that reads as a mouth, and a bead the pattern cannot
    # swallow. `beak` is the keratin sheath a real ankylosaur's cropping beak carries.
    "beak": "light_gray_wool",      # L141 against the head's own L112
    "mouth": "black_wool",          # L21 - the single line that makes a blocky front a FACE
    "ring": "light_gray_wool",
    "eye": "black_wool",
    "belly_stair": "andesite_stairs",
}

ANKYLOSAUR = {
    "kind": "ankylosaur",
    # **64, AND THE SIZE IS A MEASUREMENT RATHER THAN A PREFERENCE.** Against the Abyss Squid this
    # animal already wins every density metric the repo uses - accent tail 20.9% against 15.9%,
    # dominant block 48% against 59%, and 62 shape blocks per thousand against none - and loses on
    # exactly one: SURFACE, 1,078 cells against 44,104. What reads as "detailed" at that scale is
    # RESOLUTION, so the fix is the size at which each feature stops being one cell, not more
    # features crammed into 40 blocks. At 64 the surface is 7,148 - more than `X elephant`, this
    # repo's own control that "reads instantly" - and it is what the causeway can carry without
    # the stop being clamped into its span.
    "length": 64,               # NOSE TO CLUB, which is the animal's real measurement
    "scale": 1.0,
    "facing": "north",          # the way it LOOKS
    "at": None,                 # world coordinate of the canvas corner
    "stand": None,              # ...or the world cell the FEET occupy - see `build_ankylosaur`
    "seed": 0,
    "title": "THE ANKYLOSAUR",
}


def _dims(L: float) -> dict:
    """Every number a FRACTION OF THE ANIMAL'S OWN LENGTH, never a block count.

    "Feature sizes must scale" is one of this file's named traps: a tail hardcoded at 13 blocks was
    once longer than a deer's legs and broke a model in two.

    **THE SHELL CARRIES A HALF-DEPTH AND A HALF-WIDTH SEPARATELY**, because a sphere has one radius
    and this animal's whole identity is that it is WIDER THAN IT IS DEEP. Swept as spheres the plan
    and the profile are the same shape by construction, which is the jaguar's recorded retirement
    ("a constant-depth rectangle from shoulder to rump") and what made the stegosaur read as a loaf.

    **AND THE HALF-WIDTH AT THE SHOULDER AND THE HIP IS `stance + leg radius`, NOT A NUMBER CHOSEN
    BY EYE.** Chosen by eye on the stegosaur the legs came out WIDER THAN THE BODY and pushed a
    cell and a half out through the flank as four lumps - at the four places a quadruped is
    supposed to be smoothest, and scaling the animal up made them bigger rather than finer. Sized
    to cover the legs the same cells are the shoulder and the haunch, which is what the panel
    review asks for and what lets this animal read as ONE MASS.
    """
    stance, fore_r0, hind_r0 = 0.085 * L, 0.050 * L, 0.052 * L
    return {
        "L": L,
        # (forward, centre height, half-DEPTH, half-WIDTH) - front, shoulder, mid, hip, rump
        "spine": [(0.300 * L, 0.140 * L, 0.052 * L, 0.092 * L),
                  (0.160 * L, 0.170 * L, 0.078 * L, stance + fore_r0),
                  (-0.020 * L, 0.186 * L, 0.090 * L, 0.170 * L),
                  (-0.160 * L, 0.192 * L, 0.090 * L, stance + hind_r0),
                  (-0.300 * L, 0.158 * L, 0.060 * L, 0.100 * L)],
        # **THE SECTION IS FLAT ON TOP AND ROUNDED UNDER.** A shield is not an ellipse: a high
        # exponent above the centre line keeps the carapace a plane with its edges turned down,
        # which is what makes the osteoderm bands sit on something rather than wrap a tube.
        "section_top": 3.6, "section_low": 2.2,
        "stance": stance,
        "fore_f": 0.150 * L, "fore_r0": fore_r0, "fore_r1": 0.042 * L,
        "hind_f": -0.150 * L, "hind_r0": hind_r0, "hind_r1": 0.044 * L,
        # the head: LOW, WIDE and blunt, carried out in front rather than up
        "head_back": 0.290 * L, "head_tip": 0.455 * L,
        "head_y": 0.118 * L, "head_r0": 0.080 * L, "head_r1": 0.068 * L,
        "horn_f": 0.310 * L, "horn_len": 0.090 * L, "horn_r": 0.028 * L,
        # **FOUR HORNS, NOT TWO.** The squamosal pair off the back corners of the skull roof and
        # the quadratojugal pair under them at the cheek are what a palaeontologist names this
        # animal on, and two alone read as a lump with ears. The lower pair is shorter and aimed
        # DOWN as well as back, so head-on they widen the jaw instead of doubling the upper pair.
        "cheek_f": 0.295 * L, "cheek_len": 0.062 * L, "cheek_r": 0.024 * L,
        # three toes a foot, and a foot is mostly the AIR BETWEEN THEM
        "toe_len": 0.055 * L, "toe_r": 0.020 * L,
        # ossified tendon rings along the tail - the reason a real one is a rigid club-carrier
        "tail_bands": 4,
        # the tail, and the club that names the animal
        # **THE TAIL IS A THIRD OF THE ANIMAL, and at 0.115 of the length past the rump it was a
        # STUB WITH A LUMP ON IT.** In the profile silhouette - the panel's only real question -
        # that reads as an armadillo or a horseshoe crab, because the club is the feature that
        # names this animal alongside the armour and a club needs a tail to be on the end of. A
        # real Ankylosaurus carries about 38% of its length behind the hips.
        "tail_f": -0.560 * L, "tail_y": 0.165 * L, "tail_r0": 0.068 * L, "tail_r1": 0.052 * L,
        # ...and THICK. At 0.048 tapering to 0.028 the tail came out ONE CELL WIDE at its end and
        # the profile silhouette read as a lollipop - a thread with a lump on it. An ankylosaur's
        # tail is a stiffened rod of ossified tendon, near as deep as it is wide, leaving the hip
        # at almost the rump's own girth: the club has to look CARRIED, not hung.
        # **THE CLUB IS BILOBED AND FLAT, NOT A BALL.** Two lobes at 0.62 of the club's half-width
        # with a radius of 0.55 merge into ONE 5-wide cube on the end of a stick - a mallet, which
        # is what it first shipped as. But set FAR apart they stop touching, and the thread that
        # joins them shows between as a stem: the club came out as a PLUS SIGN in plan, which is
        # the view this animal is read in. At 0.52 the lobes overlap into one flattened mass with
        # a notch across its end - two knobs sharing a body, which is what a club is - and the
        # squash keeps it flatter than it is wide, which is what stops it reading as a ball.
        "club_f": -0.610 * L, "club_r": 0.068 * L, "club_split": 0.52, "club_flat": 0.72,
        # the pattern: longitudinal rows of scutes, a keel down the spine, transverse bands over
        # the shoulder, and a fringe of spikes round the rim
        "knob_rows": (0.46, 0.84),        # as a fraction of the local half-width
        "knob_pitch": 0.075 * L,
        # **A SCUTE HAS A SIZE, AND AT ONE CELL IT DOES NOT HAVE ONE.** Every other feature here is
        # a fraction of the length and this was an absolute: at 40 blocks a one-cell knob is a
        # scute and at 64 it is a speck on a 37-wide back, so scaling the animal made the carapace
        # EMPTIER rather than finer. That is this file's own "feature sizes must scale" trap
        # running backwards - an absolute that is too small at large scale rather than too big at
        # small - and it is why a bigger build of the same generator reads worse.
        "knob_r": 0.024 * L,
        # ...and they are GRADED. A field of identical studs is riveted plate whatever its size;
        # a real carapace carries big keeled scutes at the flank and small ones over the spine.
        "knob_grade": (1.45, 0.85),       # rim -> spine, multiplying `knob_r`
        # **THE KEEL IS A LINE AND THE SCUTES ARE DOTS.** A line survives distance and a field of
        # dots turns to noise - the jaguar's rosettes are the recorded case. The midline carries a
        # continuous low ridge instead of a row of knobs, which is also what the animal has.
        "keel_from": -0.30, "keel_to": 0.24,      # as fractions of L along the spine
        # transverse half-rings over the shoulder: the one thing that breaks a uniform field into
        # a structure, and the feature an ankylosaur is actually diagnosed on.
        "bands": (0.20, 0.10, 0.00),      # station, as a fraction of L
        # A SPIKE AND A KNOB MUST NOT BE THE SAME SIZE, or the fringe reads as more rivets.
        "spike_pitch": 0.150 * L, "spike_len": 0.095 * L, "spike_r": 0.022 * L,
        # smoothing: `quadruped.py`'s own numbers, which is what the giraffe is built with
        "relax_rounds": 4, "relax_fill": 11, "relax_keep": 11,
        "coat_min_depth": 5.0,
    }


# ------------------------------------------------------------------------------- the spine


def _band(d: dict, f: float) -> tuple:
    """(belly, back, half-width) at this station, over ONE CONTINUOUS SPINE nose to club.

    The head's and the tail's keyframes are folded in at both ends, so a station anywhere on the
    animal has a real pair of lines to be measured between and the countershading runs unbroken.
    """
    keys = ([(d["head_tip"], d["head_y"], d["head_r1"], d["head_r1"]),
             (d["head_back"], d["head_y"], d["head_r0"] * 0.7, d["head_r0"])]
            + [(f0, y0, hd, hw) for (f0, y0, hd, hw) in d["spine"]]
            + [(d["tail_f"], d["tail_y"], d["tail_r1"], d["tail_r1"]),
               (d["club_f"], d["tail_y"], d["club_r"], d["club_r"])])
    if f >= keys[0][0]:
        _f, y, hd, hw = keys[0]
    elif f <= keys[-1][0]:
        _f, y, hd, hw = keys[-1]
    else:
        y = hd = hw = 0.0
        for i in range(len(keys) - 1):
            (f0, y0, d0, w0), (f1, y1, d1, w1) = keys[i], keys[i + 1]
            if f1 <= f <= f0:
                t = 0.0 if f0 == f1 else (f0 - f) / (f0 - f1)
                y, hd, hw = (y0 + (y1 - y0) * t, d0 + (d1 - d0) * t, w0 + (w1 - w0) * t)
                break
    return y - hd, y + hd, hw


def _belly_at(d: dict, f: float) -> float:
    return _band(d, f)[0]


# ------------------------------------------------------------------------------------ the mass


def _shell(fr: loft.Frame, d: dict) -> int:
    """The carapace, LOFTED station by station - one cell thick along the body, so consecutive
    stations are 6-adjacent by construction and the plan and the profile can be designed apart.

    This is the whole animal. Everything else on it is a pattern, a stub or a club.
    """
    keys = d["spine"]
    e_hi, e_lo = float(d["section_top"]), float(d["section_low"])
    n = 0
    for fi in range(int(math.floor(keys[-1][0])), int(math.ceil(keys[0][0])) + 1):
        f = float(fi)
        for i in range(len(keys) - 1):
            if keys[i + 1][0] <= f <= keys[i][0]:
                (f0, y0, d0, w0), (f1, y1, d1, w1) = keys[i], keys[i + 1]
                break
        else:
            continue
        t = 0.0 if f0 == f1 else (f0 - f) / (f0 - f1)
        yc, hd, hw = y0 + (y1 - y0) * t, d0 + (d1 - d0) * t, w0 + (w1 - w0) * t
        for ds in range(-int(math.ceil(hw)) - 1, int(math.ceil(hw)) + 2):
            for dy in range(-int(math.ceil(hd)) - 1, int(math.ceil(hd)) + 2):
                e = e_hi if dy >= 0 else e_lo
                if (abs(ds) / hw) ** e + (abs(dy) / hd) ** e > 1.0:
                    continue
                if fr.put(f, ds, yc + dy, "flank"):
                    n += 1
    return n


def _legs(fr: loft.Frame, d: dict) -> dict:
    """Four SHORT PILLARS, and they carry the barrel clear of the ground.

    **HIDING THEM IS WHAT MADE THIS ANIMAL AN ALLIGATOR.** The first build tucked the legs inside
    the outline and dropped the belly onto the floor, on the reasoning that a leg the silhouette
    decomposes into is the one thing this animal was chosen to avoid. Measured, the barrel had
    ZERO courses of clearance, the back was flat and the tail dragged - which is a crocodilian's
    profile term for term, and it is what Jack read it as on sight.

    The corpus rule is about a barrel slung between LONG legs, which is the jaguar. Four short
    thick pillars under a wide dome is the TURTLE, and the turtle works in this repo. What keeps
    it on the right side of the line is the ratio rather than the presence: the barrel is deeper
    than the legs are long, so the mass still dominates the outline and there is daylight under
    it. `test_the_barrel_is_CARRIED_CLEAR_but_the_mass_still_dominates` pins both halves, because
    the animal has now been wrong in each direction.
    """
    out = {}
    st = d["stance"]
    for name, f, r0, r1 in (("fore", d["fore_f"], d["fore_r0"], d["fore_r1"]),
                            ("hind", d["hind_f"], d["hind_r0"], d["hind_r1"])):
        cells = 0
        floor = _belly_at(d, f)
        for s in (st, -st):
            cells += loft.sweep(fr, (f, s, floor + 0.4), (f, s, r1 * 1.1), r0, r1)
            cells += loft.ball(fr, f, s, r1 * 0.5, r1 * 1.25)
            cells += loft.ball(fr, f, s, 0.0, r1 * 1.05)
        out[name] = cells
    return out


def _head(fr: loft.Frame, d: dict) -> int:
    """Low, wide and blunt, carried out in front rather than up.

    An ankylosaur has no neck to speak of - the skull sits on the front of the shell - so this is
    a short taper off the mass rather than a head on a stalk, and it is the SAME material as the
    shell. A pale head would read as a separate object stuck on the front, which is the failure
    the stegosaur's bone skull kept having.
    """
    # **A PINCH WHERE THE HEAD LEAVES THE SHELL.** Swept straight out of the mass at full width the
    # head is not a head, it is the front of the shell tapering - the animal reads HEADLESS, which
    # is what it first shipped as. A neck narrower than both the shell behind it and the skull in
    # front is the one line that separates the two, and it is the axolotl's own recorded fix
    # ("without it the animal read as a worm with a face").
    # **THE PINCH IS SHALLOW BECAUSE THE RELAX FILLS A DEEP ONE ANYWAY.** At 0.58 of the skull's
    # radius the head came out as a beak on a STICK before smoothing and as a smooth CONE after it
    # - the pass fills a narrow trough and shaves a thin tip, so a deep pinch buys a defect at both
    # ends. What survives four rounds is a shallow waist between two masses that are each thick
    # enough to keep their neighbours.
    neck = (d["head_back"] + (d["head_tip"] - d["head_back"]) * 0.22, 0.0,
            d["head_y"] + d["head_r0"] * 0.10)
    a = (d["head_back"], 0.0, d["head_y"] + d["head_r0"] * 0.15)
    b = (d["head_tip"], 0.0, d["head_y"])
    # **AND THE SKULL ENDS BLUNT, which is the whole difference between this head and a snout.**
    # An Ankylosaurus skull is WIDER THAN IT IS LONG - a boxy head on a broad beak - and a taper
    # that runs all the way to the tip comes to a POINT, because the relax pass then eats the last
    # thin ball for having too few neighbours. Measured, the head ran 7, 5, 5, 3, 1 wide over its
    # last five stations and read as a snout stuck on a shield. So the taper stops short and a
    # FLATTENED WIDE ellipsoid caps it, which is what a beak is: broad across, low, and square on
    # the front. The stegosaur's skull had the opposite problem and the same cause - a ball where
    # a shape was wanted - so neither is a tuning number, it is which primitive the part is.
    beak = d["head_tip"] - d["head_r1"] * 0.55
    n = loft.thread(fr, a, (beak, 0.0, d["head_y"]), "flank")
    n += loft.sweep(fr, a, neck, d["head_r0"] * 0.92, d["head_r0"] * 0.74, "flank", step=0.22)
    n += loft.sweep(fr, neck, (beak, 0.0, d["head_y"]), d["head_r0"] * 0.84, d["head_r1"] * 0.90,
                    "flank", step=0.22)
    return n + loft.ball(fr, beak + d["head_r1"] * 0.35, 0.0, d["head_y"], d["head_r1"] * 0.72,
                         "flank", rs=d["head_r0"] * 0.98, ry=d["head_r0"] * 0.50)


def _tail(fr: loft.Frame, d: dict) -> int:
    """From the rump, back and slightly down - the shaft only; the club is a feature."""
    rump = d["spine"][-1]
    a = (rump[0], 0.0, rump[1])
    b = (d["tail_f"], 0.0, d["tail_y"])
    return loft.thread(fr, a, b, "flank") + loft.sweep(fr, a, b, d["tail_r0"], d["tail_r1"], "flank")


# ------------------------------------------------------------------------------ the smoothing


def _solid_cells(c: Canvas) -> set:
    ys, zs, xs = np.nonzero(c.ids > 0)
    return {(int(x), int(y), int(z)) for x, y, z in zip(xs.tolist(), ys.tolist(), zs.tolist())}


def _relax_mass(fr: loft.Frame, d: dict, protect: set) -> dict:
    """Step 2 of CLAUDE.md's build order - `mass -> relax -> features -> face -> coat`.

    **`quadruped.py`'s OWN NUMBERS**, four rounds at fill 11 and keep 11, which is what the giraffe
    is built with and what a side-by-side measurement said the stegosaur was missing: its skin
    scored `spike_rate` 9.4 against the giraffe's 4.0 while running ONE round at fill 15 and keep 8.
    The warning in CLAUDE.md that "every smoothing pass rewards thickening" is about tuning
    smoothing ALONE against the rubric; it is not an argument for under-smoothing.

    **ONLY THE LEGS ARE PROTECTED.** A protected cell is never shaved, so protecting the head and
    the tail as well leaves them exactly as lumpy as they were built while the mass smooths around
    them. A leg genuinely has too few neighbours to survive `keep`; a tail does not.

    **AND THE AIR BELOW THE BELLY IS FORBIDDEN, except inside a leg's own cylinder** - filling is
    blind to anatomy and reads the gap between two legs as a dent worth closing, which welded the
    giraffe's four legs into one part for the whole lower half. The reach is CLAMPED TO HALF THE
    LEG SPACING, this file's own rule: unclamped, a thigh standing 3.4 off the midline with a
    radius of 2.1 reaches the midline itself and protects nothing.
    """
    c = fr.c
    mass = _solid_cells(c)
    legs = [(d["fore_f"], d["fore_r0"]), (d["hind_f"], d["hind_r0"])]
    forbid = set()
    for v in range(c.sx):
        for u in range(c.sz):
            f, sd = fr.fs(v, u)
            inside_leg = any(abs(abs(sd) - d["stance"]) < min(r + 0.6, d["stance"] - 0.6)
                             and abs(f - lf) < r + 0.6 for lf, r in legs)
            if inside_leg:
                continue
            for y in range(int(math.ceil(_belly_at(d, f))) + 1):
                if (v, y, u) not in mass:
                    forbid.add((v, y, u))
    out = smooth.relax(mass, rounds=int(d["relax_rounds"]), fill=int(d["relax_fill"]),
                       keep=int(d["relax_keep"]), protect=protect, forbid=forbid)
    flank = c.state(HIDE["flank"])
    for (v, y, u) in mass - out:
        c.put(v, y, u, 0)
    for (v, y, u) in out - mass:
        c.put(v, y, u, flank)
    before, after = smooth.roughness(mass), smooth.roughness(out)
    return {"filled": len(out - mass), "shaved": len(mass - out),
            "spike_rate": [round(before["spike_rate"], 2), round(after["spike_rate"], 2)],
            "notches": [before["notches"], after["notches"]],
            "jerk_rel": [round(before["jerk_rel"], 1), round(after["jerk_rel"], 1)]}


# -------------------------------------------------------------------------------- the pattern


def _knobs(fr: loft.Frame, d: dict) -> int:
    """Graded scutes over the carapace, a keel down the spine, and transverse bands at the shoulder.

    **ROOTED ON THE SURFACE THE SHELL ACTUALLY BUILT, and snapshotted before any of it is laid.**
    Probed live, a scute finds the scute in front of it and climbs: the stegosaur's plates shipped
    as alternate courses with a hole between them, fifty four-cell strays, and only a component
    count could see it. MEASURE THE MASS, NEVER THE ACCUMULATING BUFFER.

    **THE ROWS ARE STAGGERED AND THINNED**, or the carapace reads as riveted plate - the deck
    soffit's confetti failure with the sign reversed, where the fault is too much regularity rather
    than too little. Alternate rows are offset half a pitch and a per-cell hash drops one in six.
    """
    f0, f1 = d["spine"][0][0], d["tail_f"]
    pitch = max(2, int(round(d["knob_pitch"])))
    L = d["L"]
    tops, plan = {}, []
    for row, frac in enumerate(d["knob_rows"]):
        off = (pitch // 2) if row % 2 else 0
        grade = d["knob_grade"][min(row, len(d["knob_grade"]) - 1)]
        for fi in range(int(math.ceil(f1)) + off, int(math.floor(f0)) + 1, pitch):
            _lo, _hi, hw = _band(d, float(fi))
            for sgn in (1, -1):
                sd = loft.r(sgn * frac * hw)
                if (fi, sd) in tops or hash01(abs(sd), row, fi, 11, 5) < 0.17:
                    continue
                tops[(fi, sd)] = fr.top_y(fi, sd)
                plan.append((fi, sd, grade))
    n = 0
    for (fi, sd, grade) in plan:
        top = tops[(fi, sd)]
        if top is None:
            continue
        r = d["knob_r"] * grade
        if r < 0.85:
            n += bool(fr.put(fi, sd, top + 1, "knob", protect=True))
        else:
            # A SCUTE IS A LOW MOUND, NOT A TOWER: it is squashed in y, or a big one at the flank
            # becomes a second spike and the fringe stops being the thing that breaks the outline.
            n += loft.ball(fr, fi, sd, top + 1, r, "knob", protect=True, ry=max(0.5, r * 0.55))
    return n + _keel(fr, d) + _bands(fr, d)


def _keel(fr: loft.Frame, d: dict) -> int:
    """A continuous low ridge along the midline of the carapace.

    **A LINE SURVIVES DISTANCE AND A FIELD OF DOTS DOES NOT** - the jaguar's rosettes "turn to
    noise rather than pattern" at a quarter scale, and that is the recorded reason its coat failed.
    The spine row used to be scutes like the others; as one ridge it is the only element on the
    back that still reads when the animal is a smudge.
    """
    n = 0
    for fi in range(loft.r(d["keel_from"] * d["L"]), loft.r(d["keel_to"] * d["L"]) + 1):
        top = fr.top_y(fi, 0)
        if top is not None:
            n += bool(fr.put(fi, 0, top + 1, "knob", protect=True))
    return n


def _bands(fr: loft.Frame, d: dict) -> int:
    """Transverse half-rings of fused osteoderms over the shoulder.

    An ankylosaur's cervical half-rings are what a palaeontologist diagnoses it on, and they are
    the one thing that breaks a uniform field of scutes into a STRUCTURE. Laid across the animal
    rather than along it, so they read as bands rather than as more of the same rows.
    """
    n = 0
    for frac in d["bands"]:
        fi = loft.r(frac * d["L"])
        _lo, _hi, hw = _band(d, float(fi))
        for sd in range(-int(hw) - 1, int(hw) + 2):
            top = fr.top_y(fi, sd)
            if top is not None:
                n += bool(fr.put(fi, sd, top + 1, "knob", protect=True))
    return n


def _spikes(fr: loft.Frame, d: dict) -> int:
    """The fringe: bone spikes standing out sideways along the rim of the shell.

    **THIS IS WHAT BREAKS THE PLAN SILHOUETTE**, which is this animal's money view - a bare oval
    reads as a beetle, and a fringe of spikes reads as armour. Rooted INSIDE the shell and threaded
    first: a taper that ends under one cell cannot be swept into existence, and the stegosaur's
    thagomizer came away as one piece at four lengths out of seventeen for exactly that.
    """
    pitch = max(3, int(round(d["spike_pitch"])))
    n = 0
    for fi in range(int(math.ceil(d["tail_f"] * 0.55)), int(math.floor(d["spine"][0][0])), pitch):
        _lo, _hi, hw = _band(d, float(fi))
        mid = (_lo + _hi) / 2.0
        for sgn in (1, -1):
            a = (float(fi), sgn * (hw - 1.0), mid + 0.2)
            b = (float(fi) - d["spike_len"] * 0.35, sgn * (hw + d["spike_len"]), mid + 0.6)
            n += loft.thread(fr, a, b, "armour", protect=True)
            n += loft.sweep(fr, a, b, d["spike_r"] * 1.7, d["spike_r"] * 0.8, "armour",
                            step=0.18, protect=True)
    return n


def _club(fr: loft.Frame, d: dict) -> int:
    """The club: two bone lobes on the end of the tail, and the second thing that names it.

    **ROOTED IN THE TAIL THAT WAS BUILT, never at the height it was drawn at.** The relax pass
    moves the tail's surface, and the stegosaur's spikes started in mid-air for precisely that -
    `loft.surface_out`'s rule, which has already cost this project a mane, a pair of ossicones and
    a tail that floated 45 cells clear.
    """
    f, y = d["tail_f"], d["tail_y"]
    found = False
    # SEARCH TOWARD THE BODY, which is INCREASING f - the tail's own stations are negative, so
    # `f - df` walks further OUT along a tail that is no longer there and the club shipped as a
    # 45-cell piece hanging in the air behind the animal. The stegosaur's thagomizer has this
    # search written the right way round; writing it again from memory got the sign wrong.
    for df in range(0, int(math.ceil(abs(d["club_f"] - d["tail_f"]))) + 6):
        for dy in (0, -1, 1, -2, 2, -3, 3):
            if fr.solid(f + df, 0, y + dy):
                f, y, found = f + df, y + dy, True
                break
        if found:
            break
    n = loft.thread(fr, (f, 0.0, y), (d["club_f"], 0.0, y), "armour", protect=True)
    r0 = d["club_r"]
    # **A LOBE'S RADII HAVE A FLOOR IN BLOCKS, because a fraction of the length goes under one cell
    # long before the animal stops being buildable.** At 0.058 of the length the vertical radius is
    # 0.73 at length 26, `ball` fills a single course, and the club shipped as a one-course PADDLE
    # thinner than the tail carrying it - at two lengths out of five, and not at the one it was
    # being looked at. It is the same class as `MIN_BLOCKS`: a feature below its own legible size
    # does not shrink gracefully, it stops existing.
    ra = max(1.6, r0 * 0.78)
    ry = max(1.05, r0 * 0.78 * d["club_flat"])
    for sgn in (1, -1):
        n += loft.ball(fr, d["club_f"] + r0 * 0.15, sgn * r0 * d["club_split"], y,
                       ra, "armour", protect=True, ry=ry)
    # **A KEEL ALONG THE SEAM, so the two lobes read as two.** Merged into one mass the club is a
    # mallet, which is what it first shipped as; the notch between them is what says "two knobs
    # sharing a body", and at any size above the floor a raised midline states it outright.
    for df in range(-int(ra), int(ra) + 1):
        top = fr.top_y(d["club_f"] + r0 * 0.15 + df, 0)
        if top is not None:
            n += bool(fr.put(d["club_f"] + r0 * 0.15 + df, 0, top, "armour", protect=True))
    return n


def _horns(fr: loft.Frame, d: dict) -> int:
    """Two bone horns off the back corners of the skull, pointing back and out.

    **ROOTED ON THE SKULL THE BUILD ACTUALLY HAS, NOT AT A COMPUTED HALF-WIDTH.** Placed at
    `hw * 0.55` they were entirely INSIDE the head: 124 placements, not one new cell, and the
    animal shipped hornless while the sidecar reported a healthy-looking count - which is exactly
    the frog's `forelegs: 0`, and it was invisible until the part counts became unique cells. The
    relax pass moves the surface, so anything clinging has to find it; `loft.surface_out` exists
    for this and it has already cost this project a mane, a pair of ossicones and a tail that
    floated 45 cells clear.
    """
    n = 0
    f = d["horn_f"]
    y = loft.r(d["head_y"] + d["head_r0"] * 0.35)
    reach = int(math.ceil(d["L"] * 0.30))
    for sgn in (1, -1):
        edge = next((s for s in range(reach, 0, -1) if fr.solid(f, sgn * s, y)), None)
        if edge is None:
            continue
        b = (f - d["horn_len"] * 0.85, sgn * (edge + d["horn_len"]),
             y + d["head_r0"] * 0.25)
        # The THREAD reaches back INTO the skull so the horn cannot come away; the SWEEP starts at
        # the skin, so its taper is spent outside the animal rather than buried in it.
        n += loft.thread(fr, (f, sgn * (edge - 1), float(y)), b, "armour", protect=True)
        n += loft.sweep(fr, (f, sgn * float(edge), float(y)), b,
                        d["horn_r"] * 1.5, d["horn_r"] * 0.6, "armour",
                        step=0.18, protect=True)
    # the quadratojugal pair, under the eye and aimed DOWN as well as back
    fc = d["cheek_f"]
    yc = loft.r(d["head_y"] - d["head_r0"] * 0.30)
    for sgn in (1, -1):
        edge = next((sd for sd in range(reach, 0, -1) if fr.solid(fc, sgn * sd, yc)), None)
        if edge is None:
            continue
        b = (fc - d["cheek_len"] * 0.75, sgn * (edge + d["cheek_len"]),
             yc - d["head_r0"] * 0.22)
        n += loft.thread(fr, (fc, sgn * (edge - 1), float(yc)), b, "armour", protect=True)
        n += loft.sweep(fr, (fc, sgn * float(edge), float(yc)), b,
                        d["cheek_r"] * 1.5, d["cheek_r"] * 0.6, "armour",
                        step=0.18, protect=True)
    return n


#: A stair's TALL side is its `facing`, so a toe that tapers down and FORWARD leans BACK toward
#: the body. Our renderer drew both the same until `render3d.subdivide` learned to expand a stair,
#: which is why the frog asserts this rather than eyeballing it.
_OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}


def _toes(fr: loft.Frame, d: dict) -> int:
    """Three toes a foot, tapered with stairs, with a clear cell between them.

    **A TOE BUILT OF FULL BLOCKS ENDS AT A VERTICAL FACE, WHICH IS A PLATE.** That is why four
    separate arrangements of cubes on the frog read as a rake, a comb, a plus sign and a set of
    random lines: half height at the tip sloping to the ground is what a toe actually does, and it
    is one block per toe. **AND THE GAPS ARE THE FEATURE** - three prongs with air between them
    read as a foot, and the same three filled in read as a boot.
    """
    n = 0
    back = _OPPOSITE[fr.facing]
    for f, r1 in ((d["fore_f"], d["fore_r1"]), (d["hind_f"], d["hind_r1"])):
        # **THE SPREAD IS THE FOOT'S OWN WIDTH, NOT A FIXED GAP.** Spaced by a multiple of the toe's
        # radius the outer pair walked off the pad entirely at three lengths out of five - three
        # separate ground patches a side, five components, and it audits clean because a detached
        # toe is still a legal block on the ground. A foot is as wide as a foot.
        gap = max(1, int(round(r1 * 0.85)))
        for sgn in (1, -1):
            base = sgn * d["stance"]
            for k in (-1, 0, 1):
                sd = base + k * gap
                # **THE TOE IS ROOTED ON THE PAD THE BUILD ACTUALLY HAS, NOT ON ONE COMPUTED FROM
                # ITS RADIUS.** The foot is a ball and the relax pass shaves it, so at the outer
                # toes' offset the ground course is sometimes simply not there: the toes came away
                # as separate ground patches at three lengths out of nine, five components and a
                # perfectly clean audit, because a detached toe is still a legal block on a floor.
                # Walk back to the pad's own frontmost solid cell, and skip a toe with no foot.
                root = None
                for step in range(0, int(math.ceil(r1 * 1.6)) + 1):
                    if fr.solid(f + r1 * 0.7 - step, sd, 0):
                        root = f + r1 * 0.7 - step
                        break
                if root is None:
                    continue
                a = (root, sd, 0.0)
                b = (root + d["toe_len"], sd, 0.0)
                n += loft.thread(fr, a, b, "belly", protect=True)
                tip = fr.at(loft.r(b[0]), loft.r(sd))
                if 0 <= tip[0] < fr.c.sx and 0 <= tip[1] < fr.c.sz:
                    fr.c.put(tip[0], 0, tip[1],
                             fr.c.state(HIDE["belly_stair"], facing=back, half="bottom"))
                    fr.fixed.add((tip[0], 0, tip[1]))
    return n


def _tail_bands(fr: loft.Frame, d: dict) -> int:
    """Rings of ossified tendon along the tail, which is what makes it a rigid club-carrier.

    Without them the tail is a smooth taper and reads as a rat's; the bands are also the only thing
    on it that survives being seen from above, which is where the skyway looks down on this stop.
    """
    n = 0
    a, b = d["spine"][-1][0], d["tail_f"]
    for k in range(1, int(d["tail_bands"]) + 1):
        fi = loft.r(a + (b - a) * k / (d["tail_bands"] + 1.0))
        for sd in range(-4, 5):
            top = fr.top_y(fi, sd)
            # **RAISED, NOT REPAINTED.** Written at `top` the band recolours the cell already
            # there and adds nothing: the part count read 0 while the pass reported success, which
            # is the same shape as the horns that sat inside the skull. A band you can only see in
            # colour is not a tendon ring, it is a stripe.
            if top is not None:
                n += bool(fr.put(fi, sd, top + 1, "knob", protect=True))
    return n


def _eyes(fr: loft.Frame, d: dict) -> int:
    """One bead a side, ON THE CHEEK, ringed pale so the coat cannot swallow it.

    **AN EYE IS FOUND, NOT COMPUTED, AND SO IS THE COURSE IT SITS ON.** The wyrm shipped with ONE
    eye, twice, because a computed offset landed on a course where the skull is two cells wide and
    asymmetric about the midline; the stegosaur shipped with NONE at one length. An eyeless build
    is a fault, not a style, so this RAISES rather than shipping silently.

    **AND THE COURSE IS CHOSEN, NOT TAKEN FROM THE TOP.** Walking down from the crown for the first
    course carrying a pair puts the beads on the SKULL ROOF, where they are invisible from every
    bearing but the plan - the head read as a featureless thumb head-on with two black cells lying
    on top of it. An eye belongs at about two thirds of the skull's height on its widest station,
    which is the cheek, and that is where a real ankylosaur's is.

    The ring is the axolotl's fix and the reason is measured: `black_wool` is L21 and the head's
    own `dripstone_block` is L112, which is contrast enough - until the coat's back band lands the
    same cell in `brown_wool` at L79 and the bead has nowhere to go. Pale neighbours give it
    somewhere by construction, and this file's own threshold is 35 clear.
    """
    lo, hi = None, None
    for y in range(fr.c.sy):
        if fr.solid(d["head_tip"] - (d["head_tip"] - d["head_back"]) * 0.45, 0, y):
            lo = y if lo is None else lo
            hi = y
    if lo is None:
        raise ValueError("the skull has no solid column to set an eye course against")
    # **AT THE SKULL'S FRONT CORNER, NOT HALFWAY BACK.** At 0.55 the bead sat two stations behind
    # the head's widest point, so the muzzle in front of it occluded it completely head-on - the
    # bearing the walkway gives you first - and the face read as a blank brown thumb with an eye
    # only a profile could find. On the corner it catches both.
    #
    # **AND THE STATION IS SEARCHED, NOT PINNED.** At length 26 and 30 the skull is ONE CELL WIDE
    # at the corner, so a pinned station raises on a perfectly good animal - which the scale sweep
    # found within a second of the change being made. It walks back from the corner toward the
    # cheek and takes the FRONTMOST station that carries a pair.
    reach = int(math.ceil(d["head_r0"] * 2.2)) + 1
    span = d["head_tip"] - d["head_back"]
    for frac in (0.80, 0.72, 0.64, 0.56, 0.48):
        if _bead_pair(fr, d["head_back"] + span * frac, reach, lo, hi):
            return 2
    raise ValueError("no course of the skull carries a pair of eyes: the head is too small at this "
                     "length for a bead a side, and an animal that ships eyeless does it silently")


def _bead_pair(fr: loft.Frame, f: float, reach: int, lo: int, hi: int) -> bool:
    """One try at one station: the highest course carrying a solid cell BOTH sides, ringed pale.

    **IT SITS CLEAR OF THE JAW LINE.** At 0.30 down from the crown the bead landed ONE COURSE above
    the mouth's own carry-back along the cheek and the two merged into a single black blob - the
    axolotl's "a two-cell bar, not a bead" and the frog's sunglasses, arrived at from a third
    direction. Two courses of hide between them is what makes each read as itself.
    """
    # CLAMPED TO `lo`: on a short animal the probe column is a single course, so `hi - 1` lands
    # BELOW it and `range(1, 1, -1)` is EMPTY - the search never ran at all and reported that no
    # course carries a pair. A loop that cannot execute looks exactly like a loop that found
    # nothing, which is why it read as the head being too small.
    for y in range(max(lo, hi - max(1, int(round((hi - lo) * 0.16)))), lo - 1, -1):
        for sd in range(reach, 0, -1):
            if not (fr.solid(f, sd, y) and fr.solid(f, -sd, y)):
                continue
            for sgn in (1, -1):
                s = sgn * sd
                for df, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if fr.solid(f + df, s, y + dy):
                        fr.put(f + df, s, y + dy, "ring", protect=True)
                fr.put(f, s, y, "eye", protect=True)
            return True
    return False


def _face(fr: loft.Frame, d: dict) -> dict:
    """The beak, the mouth line and the nostrils - the three marks that make a blocky front a FACE.

    **THE BEAK IS THE FRONT CAP, ONE CELL DEEP.** Painted as every cell of the front three stations
    it is not a beak, it is a grey HEAD: 84 cells, and the animal came out with a robot's face. A
    beak is the sheath over the front of the lower muzzle and nothing else, so it is found - the
    frontmost solid cell of each line through the skull - rather than filled.

    **AND THE MOUTH IS ONE COURSE.** Laid on the lowest cell of every beak column it read head-on
    as a black cavern under a grey mask. What makes a blocky front a face is a LINE: the frog's
    recorded finding, where five passes of eye work went into a front that was a pale rectangle and
    what fixed it was one dark line across it. Here the line is where the jaws actually meet - the
    top edge of the beak - and it carries three stations back along each jaw, because drawn on the
    front plane alone it is a head-on-only feature and the profile has no mouth at all.

    **A NOSTRIL IS NOT BLACK.** Two black cells between two black pupils read as a second pair of
    eyes - the frog shipped exactly that - so they take the head's own mid tone against the pale
    beak and are read as holes by their shadow rather than by their colour.
    """
    span = d["head_tip"] - d["head_back"]
    reach = int(math.ceil(d["head_r0"] * 2)) + 1
    f_lo, f_hi = int(math.floor(d["head_back"])), int(math.ceil(d["head_tip"])) + 2

    # the head's own vertical extent, measured on its widest station rather than assumed
    col = [y for y in range(fr.c.sy) if fr.solid(d["head_back"] + span * 0.45, 0, y)]
    if not col:
        return {"beak": 0, "mouth": 0, "nostril": 0}
    lo, hi = col[0], col[-1]
    jaw = lo + max(1, int(round((hi - lo) * 0.42)))          # where the jaws meet

    front = {}
    for sd in range(-reach, reach + 1):
        for y in range(lo, hi + 1):
            fi = max((f for f in range(f_lo, f_hi) if fr.solid(f, sd, y)), default=None)
            if fi is not None and fi >= d["head_tip"] - span * 0.45:
                front[(sd, y)] = fi

    n = {"beak": 0, "mouth": 0, "nostril": 0}
    # A DRAWN FEATURE NEVER REPAINTS ANOTHER ONE. `Frame.put` records `fixed` and does not enforce
    # it, so a later pass will happily paint a beak over an eye - and an eye that has been painted
    # out is a build with a part missing that audits perfectly clean.
    front = {k: v for k, v in front.items() if fr.at(v, k[0]) + (k[1],) not in fr.fixed}
    for (sd, y), fi in front.items():
        if y < jaw and fr.put(fi, sd, y, "beak", protect=True):
            n["beak"] += 1
    for (sd, y), fi in front.items():
        if y == jaw and fr.put(fi, sd, y, "mouth", protect=True):
            n["mouth"] += 1
    # ...carried back along each jaw, or the mouth exists in exactly one view
    for sgn in (1, -1):
        for back in range(1, 4):
            sd = None
            for cand in range(reach, 0, -1):
                if fr.solid(d["head_tip"] - span * 0.18 - back, sgn * cand, jaw):
                    sd = sgn * cand
                    break
            if sd is not None and fr.put(d["head_tip"] - span * 0.18 - back, sd, jaw,
                                         "mouth", protect=True):
                n["mouth"] += 1
    # two nostrils, ABOVE the mouth line and in the head's own mid tone: at jaw - 1 they
    # sat under it, which is a face with its nose below its mouth
    tip = max(front.values(), default=None)
    if tip is not None:
        for sgn in (1, -1):
            sd = sgn * max(1, int(round(d["head_r1"] * 0.40)))
            y = jaw + 1
            # ...in the BACK's brown, not the flank's own dripstone, which is what the face is
            # made of - a nostril the same tone as the cheek is a nostril nobody can see, and it
            # reported 2 while placing nothing anybody could find. Not black either: two black
            # cells under two black pupils read as a second pair of eyes, which the frog shipped.
            if front.get((sd, y)) is not None and fr.put(front[(sd, y)], sd, y, "back",
                                                         protect=True):
                n["nostril"] += 1
    return n


# ----------------------------------------------------------------------------------- the coat


def _coat(fr: loft.Frame, d: dict) -> dict:
    """Countershading measured against the BODY'S OWN LINE at each station, never per column.

    Written per column - each cell's height as a fraction between that column's own lowest and
    highest cell - the band boundaries follow whatever the column happens to be, and on a lofted
    body every column is a different height. The result is not three bands, it is GREY BLOTCHES
    WANDERING OVER THE FLANK, which a close render reads as mould. That was most of what "super
    blocky and rough" turned out to mean on the stegosaur, and it was not geometry at all.

    A LEG IS NOT ITS OWN ANIMAL: everything below the belly line is one tone, or four courses of
    leg get the full ladder and the animal stands on four pale posts. And COUNTERSHADING NEEDS
    THICKNESS - below `coat_min_depth` a part is one tone, or a three-cell tail lands a cell in
    each band and reads as an alternating chain. The dither is hashed on the DISTANCE FROM THE
    MIDLINE: keyed on the column it differs on each flank and the animal comes out asymmetric in
    COLOUR while its shape is exact, which is the frog's own recorded fault.
    """
    c = fr.c
    S = {k: c.state(HIDE[k]) for k in ("back", "flank", "belly")}
    tally = {"back": 0, "flank": 0, "belly": 0}
    for v in range(c.sx):
        for u in range(c.sz):
            f, across = fr.fs(v, u)
            floor, top, _hw = _band(d, f)
            span = max(1.0, top - floor)
            deep = span >= float(d["coat_min_depth"])
            for y in range(c.sy):
                if not c.solid(v, y, u) or (v, y, u) in fr.fixed:
                    continue
                fy = (y - floor) / span
                jitter = (hash01(abs(across), y, int(round(f)), 7, 3) - 0.5) * (0.5 / span)
                if not deep or y < floor - 0.5:
                    key = "flank"
                elif fy + jitter > 0.72:
                    key = "back"
                elif fy + jitter < 0.26:
                    key = "belly"
                else:
                    key = "flank"
                c.put(v, y, u, S[key])
                tally[key] += 1
    return tally


def _skin(fr: loft.Frame, d: dict) -> dict:
    """{cell: block name} for the animal's own COAT - never a drawn feature.

    **AND NEVER THE HEAD.** `gen/shell.py` chamfers a step by replacing the cell with a stair of
    the nearest colour, which is exactly right on a flank and is vandalism on a face: it picked a
    green-grey slab and an orange stair out of the coat's own colour families and scattered them
    over the muzzle, so the face read as a staircase in three tones nothing else on the animal
    uses. The frog states the rule for its own build - *"only the skin, and only single steps; the
    face, the belly, the eyes and the feet are drawn features and a stair through one of them is a
    hole in a drawing"* - and it belongs to the SKIN function rather than to each caller, or the
    next pass added here forgets it.

    A palette entry is an NBT Tag, so `str()` on it is a repr: read that way every name matches
    nothing, every colour lookup fails and the surfacing pass reports zero cells while looking
    exactly like a pass that had nothing to do.
    """
    c = fr.c
    names = [nbt.state_name(e).split(":")[-1].split("[")[0] for e in c.reg.palette]
    face = d["head_back"] - 1.0
    out = {}
    for (v, y, u) in _solid_cells(c):
        if (v, y, u) in fr.fixed or (v, y + 1, u) in fr.fixed:
            continue
        if fr.fs(v, u)[0] >= face:
            continue
        out[(v, y, u)] = names[int(c.ids[y, u, v])]
    return out


def _surface(fr: loft.Frame, d: dict) -> dict:
    """Stair and half-block surfacing over the coat, through `gen/shell.py`.

    STAIRS FIRST, THEN SLABS ON WHAT IS LEFT: on the top face the two are disjoint by construction
    - a slab wants NO higher neighbour and a stair wants exactly one - but an underside stair and a
    top slab can both want the same cell, and a cell may only have one shape.
    """
    c = fr.c
    skin = _skin(fr, d)
    ramps = shell.stair_shell(set(skin), skin, HIDE["flank"], under=True, floor_y=0)
    rest = {k: v for k, v in skin.items() if k not in ramps}
    cut = shell.slab_shell(set(rest), rest, HIDE["flank"], floor_y=0)
    for cell, (name, props) in list(ramps.items()) + list(cut.items()):
        c.put(cell[0], cell[1], cell[2], c.state(name, **props))
    tops = sum(1 for _n, p in ramps.values() if p["half"] == "bottom")
    return {"stairs": len(ramps), "stairs_under": len(ramps) - tops,
            "slabs": len(cut), "skin": len(skin)}


def _mirror(fr: loft.Frame) -> dict:
    """**ENFORCE THE MIRROR, NEVER ASSUME IT.** Every part here is built for both signs and every
    span is centred, so the shape is symmetric by construction - and the squid was too, and came
    out 5,375 cells different left to right because a limb swept from a float centre mirrors about
    a column's EDGE rather than its middle."""
    c = fr.c
    shape = 0
    reach = c.sx if fr.sx else c.sz
    for f in range(-reach, reach + 1):
        for s in range(1, reach + 1):
            a, b = fr.at(f, s), fr.at(f, -s)
            for y in range(c.sy):
                if c.solid(a[0], y, a[1]) != c.solid(b[0], y, b[1]):
                    shape += 1
    return {"shape": shape}


# ------------------------------------------------------------------------------------- the build


def build_ankylosaur(cfg: dict, donors=None) -> Canvas:
    p = {**ANKYLOSAUR, **(cfg or {})}
    L = float(p.get("length") or 40) * float(p.get("scale") or 1.0)
    if L < 28:
        raise ValueError(
            "an ankylosaur under 28 blocks cannot carry a club, a spike fringe, a row of "
            "osteoderms and a face: its identity is the PATTERN on a shield and there is no "
            "shield left. The binding floor is the FACE - at 26 the relax pass leaves a skull "
            "one course tall, which cannot hold a pair of eyes either side of a midline, and "
            "`tools/scale.py`'s doctrine is that the animal's critical size is the largest of "
            "its features' own floors rather than a number chosen for the biggest one")
    d = _dims(L)
    for k in ("relax_rounds", "relax_fill", "relax_keep"):
        if p.get(k) is not None:
            d[k] = p[k]
    facing = str(p.get("facing", "north"))
    if facing not in loft.STEP:
        raise ValueError(f"an ankylosaur needs a real facing, not {facing!r}")

    # **THE CANVAS IS SIZED BY THE FACING, NOT BY THE ANIMAL.** A box that is always long in X is
    # long in the WRONG axis for a north-south animal: the sauropod built facing north came out
    # clipped to 22 blocks of 48 - head, neck and half the tail simply refused - and the render
    # still showed a plausible small dinosaur.
    # **THE MARGINS ARE A FRACTION, NOT A CONSTANT.** Fixed at 3 and 5 they are generous at 40
    # blocks and gone by 76: the scutes, the fringe and the toes all scale, so the room they need
    # past the nominal body scales with them, and `clipped` climbed back off zero above 70 while
    # every other contract still passed. A refusal off the end of the box is the sauropod's own
    # recorded disaster and the render never shows it.
    pad = int(math.ceil(0.06 * L)) + 3
    span_fore = int(math.ceil(d["head_tip"] + d["head_r1"] * 2 + d["toe_len"])) + pad
    span_back = int(math.ceil(-d["club_f"] + d["club_r"] * 2)) + pad
    length = span_fore + span_back + 1
    width = int(math.ceil((0.170 * L + d["spike_len"] + d["spike_r"] * 2) * 2)) + 2 * pad
    sy = int(math.ceil(d["spine"][2][1] + d["spine"][2][2] + d["knob_r"] * 2)) + pad

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
    # in after the smoothing because the rule that shaves a pimple off a shoulder eats a horn
    # whole, and the coat goes in after them because the countershade must measure the ANIMAL.
    # **A PART'S COUNT IS UNIQUE CELLS, NEVER `put()` CALLS.** A sweep steps finely enough that its
    # spheres overlap, so the call count is an artefact of how a part is DRAWN: the squid's sidecar
    # reported 251,264 arm blocks in a 116,000-block animal, which reads as a measurement. Counted
    # by diffing the canvas, the numbers partition the model and a reader can trust them.
    seen: set = set()

    def _step(fn):
        nonlocal seen
        fn()
        now = _solid_cells(c)
        new_cells = now - seen
        seen = now
        return new_cells

    parts = {"shell": len(_step(lambda: _shell(fr, d)))}
    legs = _step(lambda: _legs(fr, d))
    parts["legs"] = len(legs)
    parts["head"] = len(_step(lambda: _head(fr, d)))
    parts["tail"] = len(_step(lambda: _tail(fr, d)))
    parts["relax"] = _relax_mass(fr, d, protect=legs)
    seen = _solid_cells(c)
    parts["knobs"] = len(_step(lambda: _knobs(fr, d)))
    parts["spikes"] = len(_step(lambda: _spikes(fr, d)))
    parts["club"] = len(_step(lambda: _club(fr, d)))
    parts["toes"] = len(_step(lambda: _toes(fr, d)))
    parts["tail_bands"] = len(_step(lambda: _tail_bands(fr, d)))
    parts["horns"] = len(_step(lambda: _horns(fr, d)))
    parts["eyes"] = _eyes(fr, d)
    parts.update(_face(fr, d))
    parts["coat"] = _coat(fr, d)
    parts["surface"] = _surface(fr, d)
    parts["mirror"] = _mirror(fr)

    if p.get("stand"):
        wx, wy, wz = (int(round(float(v))) for v in p["stand"])
        c.world_origin = (wx - cv, wy, wz - cu)
    elif p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    c.meta = {
        "kind": "ankylosaur",
        "facing": facing,
        "length": round(L, 1),
        "profile_axis": "u" if along_x else "v",
        "refused": fr.refused,
        "clipped": fr.clipped,
        "parts": parts,
        "contract": (
            "an ankylosaur: ONE low convex armoured mass, wider than it is deep, on four short "
            "columns tucked under it so the silhouette never decomposes into limbs. Longitudinal "
            "rows of bone osteoderms and a fringe of lateral spikes are the pattern; a two-lobed "
            "club on the tail and two horns off the skull are the features. One piece, "
            "countershaded off its own finished form, exactly symmetric."),
    }
    return c


build = build_ankylosaur
DEFAULTS = ANKYLOSAUR
