"""THE STEGOSAUR - the Lost Plateau's gate animal, and a sawtooth read against open sky.

Jack: *"i think the heron should be switched to a dinosaure."*

**THE HERON WAS A LEFTOVER AS WELL AS A PREFERENCE.** It stood at the frontier end of the
Frontier Reach under a plaque reading *"stands in the frontier marsh"* - naming a land that was
re-themed to the LOST PLATEAU, and a marsh that has never existed anywhere on this causeway.
That is the same class as the five Prismworks relays that outlived the modules they named: a
sign is physically correct and describes a park that is gone.

**WHY A NEW ANIMAL AND NOT ONE OF THE TWO ALREADY BUILT.** Measured off their own sidecars,
`PF Pterosaur` stands at x97604-97637 / z80406-**80449** - one block off this causeway's own
frontier end, and fifteen from where the heron stood - and `PF Sauropod` at x97681 /
z80290-80370, 117 blocks away on the same rim walk. Pasting either onto this plinth puts two
identical animals in one view, which is precisely what retired the gecko and the bat from the
hollow reach: *"those are used assets, we want NEW things."*

**AND IT IS A STEGOSAUR BECAUSE CLAUDE.md'S OWN LIST SAYS SO.** The measured line is
PLANAR/COLUMNAR against VOLUMETRIC, learned on eight retired mammals, and this animal is on the
good side of it four separate ways with nothing on the bad side:

    body     ONE convex mass carrying a pattern - the ladybird's own winning category, and the
             reason a curled cat reads where a standing one never did. No joint anywhere has to
             be modelled and no proportion has to be right to within a few per cent
    plates   PLANAR SHEETS one block thick, standing on the spine. A sheet is what voxels render
             best of anything, and these are the identity: nobody has ever needed the rest of
             the animal to name it
    legs     columnar tapers - what killed the cats was constant-width posts at the corners
    spikes   four more columns, off the tail

**THE PLATES ALTERNATE, AND THAT IS 6-CONNECTIVITY AND LEGIBILITY AGREEING.** The real animal's
two rows are staggered, and the staggering is exactly what lets a voxel one read: each ROW's own
plates sit two pitches apart, so nothing within a row can merge - while in PROFILE, which is the
view the walkway gives you, the two rows superimpose into a sawtooth at half that pitch. Built
as one row on the midline they would have to be spaced twice as far to stay separate and the
crest would read as four lumps. This is the ladybird's spot-spacing rule, which found that
three-block spots at three-block spacing merge into one mass, arrived at from the other side.

SIZE COMES FROM THE PLATE, the way the ladybird's came from its spots and the balloon's from its
gores. A plate under about five courses is a bump on a back rather than a plate, and the tallest
one is ~0.24 of the animal's length, which puts a floor of ~21 blocks on the whole animal before
anything else is considered. It is built at 30 because the stop can take it - the plinth carries
the FEET and nothing else, which is `_site_heron`'s own rule ("the neck, the wings and the tail
coverts are free to reach out over open air past the plinth's own edge"), and four feet span 13
of a 17-block pedestal.

**THE HEAD IS TINY AND IT IS CARRIED LOW, and both halves of that are a cue rather than a
detail.** A stegosaur's skull is the smallest thing on it and hangs near the ground off a short
down-curving neck; drawn level, or drawn at any size a modeller would think reasonable, the
silhouette turns into a generic quadruped. The back ARCHES to the hips and falls away to the
tail, so the outline is a curve and not a rule - the jaguar's recorded failure was a
constant-depth slab from shoulder to rump, and a belly line parallel to the back is the most
inert shape available.

PALETTE - measured, and every tone a hue this park has not already spent. The other three
sculptures on this causeway are a brown sloth, a red-and-white balloon and a bone wyrm, the
land's own two dinosaurs are grey, and `green_wool` (85,110,28) is TWELVE RGB from the
`moss_block` (89,110,45) shoulder it would stand on - the green-turtle mistake, ruled out by
measurement rather than by taste. What is left unclaimed is the cool half of the wheel, and the
ladder is measured ACROSS families, never within one (this repo has drawn the opposite
conclusion five times from searching inside a single material):

    blue_wool 63 . cyan_wool 114 . light_blue_wool 153        the countershade, steps of 50 and 39
    red_wool 65 . orange_wool 137                             the plate and the flush at its root
    bone_block 225                                            the spikes and the beak

The plates are the one warm thing on a cold animal, which is what a display structure is for, and
`orange_wool` is 254 RGB from the flank it stands on - the largest step anywhere in the build.

NO LIGHT IS BUILT INTO THE COAT, for `balloon.py`'s reason: `isthmus._delight` records every cell
a sculpture emits and lights it from the air beside it, and a froglight this generator placed
itself would be indistinguishable from the 1,138 the night sweep once drove into these creatures'
coats.
"""
from __future__ import annotations

import math

import numpy as np

from . import shell, smooth
from .. import nbt
from .canvas import Canvas, hash01

#: Checked against `blocks.available` (1.19), `blocks.spendable` and `palette.tier` by
#: `tests/test_causeway_sculptures.py`, which asks the registry rather than trusting this
#: list - and which owns this animal's own contracts too, beside the balloon's and the
#: wyrm's, because all three were written for the same two stops.
HIDE = {
    # **DESATURATED BODY, ONE PALE CREST, AND THAT IS THE WHOLE PALETTE DECISION.** The first
    # build was navy / teal / light blue with traffic-orange plates, and the verdict on seeing it
    # was that it "feels bad" - which is what a saturated primary reads as at this size: a toy.
    # Every animal in this park that works is a desaturated mass with ONE thing on it that is
    # not, and the corpus says the same about outside sculpture.
    "back": "brown_wool",           # L79  - the spine
    "flank": "acacia_planks",       # L104 - a warm russet, and the body
    "belly": "light_gray_wool",     # L141 - countershading, read off the BUILT form
    # **THE CREST IS BONE-PALE, NOT A COLOUR.** It is the animal's one structure that is not
    # flesh, so it is the one thing here that is not an earth tone - 157 luminance clear of the
    # back it stands on, which is the largest step in the build and larger than anything the
    # orange ever gave. It also makes the crest, the skull and the spikes read as one material
    # family, which is what they are in life.
    "plate": "white_wool",          # L236
    "plate_root": "stone",          # L126 - the shaded base where a plate enters the back
    "spike": "bone_block",          # L225 - the thagomizer, the beak and the skull
    # **THE NOSTRIL GETS ITS OWN MATERIAL, not the plate's root stone.** Sharing one meant the
    # crest mask counted a nostril as a plate - a one-cell "crest piece" with no back under it -
    # so the plate-count contract, the plate-rooting contract and the "the nose is all bone"
    # contract all failed on a correct build. A mark that means something different is a
    # different block, or every test that masks by material is measuring two things at once.
    "nostril": "cobblestone",       # L127 - 98 under the bone it sits in, and used nowhere else
    "eye": "black_wool",
}


#: +f is FORWARD, toward the head - `park._Frame`'s convention, so a facing bug is one bug.
_STEP = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def _r(v: float) -> int:
    """Round HALF AWAY FROM ZERO, which `round()` does not do and `int()` does not either.

    **`round()` IS BANKER'S ROUNDING AND IT SKIPS ALTERNATE COLUMNS.** `round(4.5) == 4` while
    `round(5.5) == 6`, so a sphere swept about a centre that lands on x.5 fills one column,
    misses the next, fills the one after - and this animal's legs stand at 0.150 of its length,
    which at length 30 is exactly 4.5. Every foot came out as a COMB of three separate pads
    instead of one, four feet read as eight, and the only thing that could see it was counting
    the connected groups of the ground course. The ladybird shipped the same bug as eighteen
    one-wide towers where a clod should have been, and this file's own `_ball` docstring warns
    about it while the frame under it was doing it.

    Away from zero rather than toward +inf, because the SIDE axis is signed about the sagittal
    plane: `floor(v + 0.5)` sends 2.5 to 3 and -2.5 to -2, which is a shape one cell wider on
    one flank than the other - the squid's own 5,375-cell mirror fault, arrived at from a
    different direction.
    """
    return int(math.floor(v + 0.5)) if v >= 0 else -int(math.floor(-v + 0.5))

STEGOSAUR = {
    "kind": "stegosaur",
    "length": 34,               # NOSE TO TAIL TIP, which is the animal's real measurement
    "scale": 1.0,
    "facing": "north",          # the way it LOOKS
    # world coordinate of the canvas corner. A bespoke generator states this itself or the
    # pipeline writes no sidecar - and with no sidecar there is no origin, no in-context audit
    # and no `/cscan place`.
    "at": None,
    # ...or give `stand`, the world cell the FEET occupy. Anchoring by the thing that carries the
    # weight beats anchoring by the corner of a bounding box, which is the mistake `heron.py`
    # records having made once with `feet`.
    "stand": None,
    "plates": 4,                # PAIRED either side of the spine - see `_plates`
    # the smoothing pass. Overridable so it can be SWEPT and measured rather than guessed at -
    # this repo's own rule that you never tune one dimension by eye.
    "relax_rounds": None, "relax_fill": None, "relax_keep": None, "relax_protect": True,
    "seed": 0,                  # unused: there is no noise anywhere in this shape, and it is
                                # here so a spec written for any other creature still resolves
    "title": "THE STEGOSAUR",
}


class _Frame:
    """The animal's own axes, so every part is written in (forward, side, up).

    THE BEARING CONVENTION IS THE ONE THING A RENDER CANNOT CHECK - our raycaster draws a facing
    and its opposite identically, which is how the stair convention got got wrong twice in one
    session. One frame, one bug.
    """

    def __init__(self, c: Canvas, cv: int, cu: int, facing: str):
        if facing not in _STEP:
            raise ValueError(f"a stegosaur needs a real facing, not {facing!r}")
        self.c, self.cv, self.cu = c, cv, cu
        self.fx, self.fz = _STEP[facing]
        self.sx, self.sz = -self.fz, self.fx
        self.facing = facing
        self.placed = 0
        #: **A REFUSAL BELOW THE GROUND PLANE IS NOT THE SAME FAULT AS ONE OFF THE END.** A foot
        #: pad is a sphere centred on the course the animal stands on, so its lower half is
        #: always outside the canvas and always will be - that is the ground, not a clip. A
        #: refusal in f or s is the sauropod's recorded disaster: built facing north it was
        #: clipped to 22 blocks of 48, head and half the tail simply refused, and the only
        #: symptom was a refusal count nobody was reading. One number could not tell them apart,
        #: so a test on it could only ever be a threshold somebody had tuned.
        self.refused = 0            # under the ground plane: expected, and harmless
        self.clipped = 0            # off an end or a side of the box: always a bug
        #: **THE CELLS THE COAT PASS MAY NOT REPAINT, BY COORDINATE.** Keyed on MATERIAL instead
        #: this would protect every cell made of that material - and the sauropod's crest is the
        #: same wool as the flank it is swept in, so its countershading skipped all 2,333 cells
        #: and it shipped monochrome with a tally of four zeros. A set of things is not a set of
        #: cells.
        self.fixed: set = set()

    def at(self, f, s):
        return (self.cv + self.fx * f + self.sx * s, self.cu + self.fz * f + self.sz * s)

    def put(self, f, s, y, key, protect=False) -> bool:
        v, u = self.at(_r(f), _r(s))
        y = _r(y)
        if not (0 <= v < self.c.sx and 0 <= u < self.c.sz and 0 <= y < self.c.sy):
            if 0 <= v < self.c.sx and 0 <= u < self.c.sz and y < 0:
                self.refused += 1
            else:
                self.clipped += 1
            return False
        self.c.put(v, y, u, self.c.state(HIDE.get(key, key)))
        if protect:
            self.fixed.add((v, y, u))
        self.placed += 1
        return True

    def solid(self, f, s, y) -> bool:
        v, u = self.at(_r(f), _r(s))
        return self.c.solid(v, _r(y), u)

    def top_y(self, f, s, ceiling=None):
        """The highest solid course of the animal in this column - **FOUND, NOT COMPUTED.**

        A swept surface is not where the arithmetic that swept it says it is, and anything
        clinging to a computed radius comes off: a lion's mane shipped as seven floating
        fragments, a giraffe's ossicones detached and a tail floated 45 cells clear. Every plate
        on this animal is rooted on the answer this gives.

        `Canvas.solid`, never `if c.get(...)`: `get` returns -1 out of bounds and -1 is TRUTHY,
        which is how the ladybird painted all seven of its spots into thin air above itself while
        the audit, the BOM and the component count all reported a clean build.
        """
        v, u = self.at(_r(f), _r(s))
        hi = self.c.sy - 1 if ceiling is None else min(int(ceiling), self.c.sy - 1)
        for y in range(hi, -1, -1):
            if self.c.solid(v, y, u):
                return y
        return None


def _ball(fr: _Frame, f, s, y, r, key="flank", protect=False) -> int:
    """One sphere of a sweep. **KEEP A CENTRE OFF THE HALF-CELL** - `round()` is banker's
    rounding, so `round(11.5) == round(12.5) == 12` while `round(13.5) == 14`: a centre landing
    on x.5 skips every other column and a swept limb comes out as a row of separate towers. The
    ladybird's clod shipped exactly that."""
    n = 0
    ri = int(math.ceil(r))
    for df in range(-ri, ri + 1):
        for ds in range(-ri, ri + 1):
            for dy in range(-ri, ri + 1):
                if df * df + ds * ds + dy * dy > r * r:
                    continue
                if fr.put(f + df, s + ds, y + dy, key, protect=protect):
                    n += 1
    return n


def _sweep(fr: _Frame, a, b, ra, rb, key="flank", step=0.34, protect=False) -> int:
    """A tapered capsule from a to b, each a (forward, side, up) triple.

    **STEP FINE ENOUGH THAT THE SPHERES OVERLAP.** A sweep whose consecutive cells are only
    diagonal neighbours is not 6-connected, and the ear tips of two different animals broke off
    that way before the rule was written down."""
    d = math.dist(a, b)
    n = max(2, int(d / max(0.05, step)) + 1)
    out = 0
    for i in range(n + 1):
        t = i / n
        out += _ball(fr,
                     a[0] + (b[0] - a[0]) * t,
                     a[1] + (b[1] - a[1]) * t,
                     a[2] + (b[2] - a[2]) * t,
                     ra + (rb - ra) * t, key, protect)
    return out


def _thread(fr: _Frame, a, b, key="flank", protect=False, step=0.12) -> int:
    """A one-cell 6-CONNECTED core from a to b, filling every corner ONE AXIS AT A TIME.

    **A TAPER THAT ENDS UNDER ONE CELL CANNOT BE SWEPT INTO EXISTENCE.** Below about r=0.87 a
    sphere is a single cell, and two single cells whose centres moved on two axes at once are
    DIAGONAL neighbours - which is not connected in this project's sense and has cost it ear
    tips, ossicones, a detached mane and a whole dragonfly. It cost this animal its tail spikes,
    at exactly two lengths out of seven and not at the one it was being looked at: `L=26` shed
    six bone fragments and `L=34` shed two, both silently, both after a rounding change nowhere
    near them. A step fine enough is not a guarantee, it is a hope that scales.

    So connectivity is GUARANTEED rather than hoped for - the pterosaur's own recorded rule
    after it came apart at three separate spans - and the sweep is hung on a core that is
    already connected instead of being asked to stay connected on its own.
    """
    d = math.dist(a, b)
    n = max(2, int(d / max(0.02, step)) + 1)
    out, prev = 0, None
    for i in range(n + 1):
        t = i / n
        cell = (_r(a[0] + (b[0] - a[0]) * t),
                _r(a[1] + (b[1] - a[1]) * t),
                _r(a[2] + (b[2] - a[2]) * t))
        if cell == prev:
            continue
        if prev is None:
            out += bool(fr.put(cell[0], cell[1], cell[2], key, protect))
        else:
            cur = list(prev)
            for ax in range(3):
                while cur[ax] != cell[ax]:
                    cur[ax] += 1 if cell[ax] > cur[ax] else -1
                    out += bool(fr.put(cur[0], cur[1], cur[2], key, protect))
        prev = cell
    return out


# ------------------------------------------------------------------------------- proportions

def _dims(L: float) -> dict:
    """Every number a FRACTION OF THE ANIMAL'S OWN LENGTH, never a block count.

    "Feature sizes must scale" is one of this file's named traps: a tail hardcoded at 13 blocks
    was once longer than a deer's legs and broke a model in two, and the sauropod grew a bigger
    body on the same legs and kept a toy head because its leg radii were absolute.

    **THE SPINE CARRIES A HALF-DEPTH AND A HALF-WIDTH SEPARATELY, AND THAT IS THE FIX FOR A
    SLAB.** The first build swept SPHERES, so a station's width in plan and its depth in profile
    were the same number by construction - and the plan came out as one constant-width mass from
    shoulder to rump, which is the jaguar's recorded failure verbatim ("a constant-depth
    rectangle from shoulder to rump, so the animal has no centre of gravity"). The panel review's
    own rule 4 is that a quadruped is WIDEST AT THE SHOULDER AND THE HAUNCH WITH A WAIST BETWEEN,
    and that a bimodal width profile fixes the plan view immediately. Keyframes are
    (forward, centre height, half-DEPTH, half-WIDTH), and the two now disagree on purpose.

    The BACK LINE (centre + depth) still arches to a single peak over the hips and falls away to
    the tail, while the BELLY LINE (centre - depth) rises toward the rear. Two parallel
    horizontals is the most inert shape available and is what the panel called a table.
    """
    return {
        "L": L,
        # chest -> shoulder -> WAIST -> hip -> rump
        # **THE HALF-WIDTH AT THE SHOULDER AND THE HIP IS `stance + leg radius`, NOT A NUMBER
        # CHOSEN BY EYE.** It was chosen by eye, and the legs were WIDER THAN THE BODY: 2.65 of
        # gauge plus 2.38 of thigh reaches 5.03 where the flank reached 3.67, so each leg pushed
        # a cell and a half out THROUGH the side of the animal and read as a lump stuck on it.
        # Four lumps, at the four places a quadruped is supposed to be smoothest, and scaling the
        # whole animal up made them bigger rather than finer - which is what proved the roughness
        # was geometry rather than resolution.
        #
        # Sized to cover the legs, the same cells become the HAUNCH and the SHOULDER, which is
        # rule 1 of the panel review: "legs must merge into the body as a haunch and a shoulder".
        "spine": [(0.225 * L, 0.200 * L, 0.098 * L, 0.090 * L),
                  (0.130 * L, 0.222 * L, 0.112 * L, 0.126 * L),
                  (0.000 * L, 0.242 * L, 0.118 * L, 0.094 * L),
                  (-0.150 * L, 0.255 * L, 0.113 * L, 0.140 * L),
                  (-0.245 * L, 0.235 * L, 0.082 * L, 0.078 * L)],
        "section": 2.6,               # superellipse exponent: a rounded square, not a circle
        # **THE GIRAFFE'S OWN SMOOTHING PARAMETERS, and copying them was the fix.** Jack, with
        # the reference in hand: *"we want this to feel like the giraffe"* - so the two were
        # measured side by side, and the gap is not taste. Giraffe `spike_rate` 4.0 against this
        # animal's 9.4 on its own skin, `jerk_rel` 8.4 against 20.5, notches 0 against 10.
        #
        # `quadruped.py` relaxes FOUR TIMES at fill 11 and keep 11. This ran ONCE at fill 15 and
        # keep 8 - weaker on every one of the three axes - out of an over-reading of CLAUDE.md's
        # warning that "every smoothing pass rewards thickening". That warning is about tuning
        # smoothing ALONE against the rubric, which took the bear's proportion 0.88 -> 0.50; it is
        # not an argument for under-smoothing, and the giraffe is the counter-example standing in
        # the world. Swept here against every contract at once, four rounds costs 21% more cells
        # and keeps the plan waist, the four feet, the eight crest pieces and exact symmetry.
        "relax_rounds": 4, "relax_fill": 11, "relax_keep": 11,
        "coat_min_depth": 5.0,        # below this a part is ONE tone - see `_coat`
        "stance": 0.078 * L,          # half the gauge between the left and right legs
        "fore_f": 0.150 * L, "fore_r0": 0.048 * L, "fore_r1": 0.043 * L,
        "hind_f": -0.150 * L, "hind_r0": 0.062 * L, "hind_r1": 0.050 * L,
        "neck_f": 0.330 * L, "neck_y": 0.170 * L, "neck_r": 0.058 * L,
        "head_f": 0.440 * L, "head_y": 0.125 * L, "head_r": 0.062 * L,
        # the skull is a TAPER, not a ball: back of the cheek -> beak tip
        "skull_back": 0.370 * L, "skull_tip": 0.555 * L,
        "skull_r0": 0.062 * L, "skull_r1": 0.028 * L, "skull_drop": 0.032 * L,
        "tail_f": -0.500 * L, "tail_y": 0.165 * L, "tail_r": 0.028 * L,
        # the crest: from over the shoulder to well down the tail
        "plate_f0": 0.300 * L, "plate_f1": -0.480 * L,
        "plate_h_max": 0.245 * L,     # over the hips - the tallest, and the naming feature
        "plate_h_min": 0.115 * L,     # at both ends of the run
        "plate_half": 0.075 * L,      # half the WIDEST course, a third of the way up
        # **TWO CELLS EITHER SIDE OF THE SPINE, NOT ONE, AND IT IS MEASURED.** At one the gap
        # between the paired rows is a single column, and `smooth.roughness` counts every cell of
        # it as a NOTCH - a one-block dent, which its own docstring says "the eye reads as
        # damage". Twelve of them, every one on the midline, and they were the entire notch count
        # of the animal: the crest read as a cracked ridge rather than as two rows. At two the
        # spine shows as a real channel between the plates and the count is ZERO, which is what
        # the giraffe measures.
        "plate_offset": 2,
        "spike_f": -0.415 * L, "spike_len": 0.135 * L, "spike_r": 0.028 * L,
    }


def _body(fr: _Frame, d: dict) -> int:
    """The barrel, LOFTED station by station rather than swept as a chain of spheres.

    A sphere has one radius, so a swept body's plan and its profile are the same shape and there
    is no way to say "widest at the shoulder and the haunch, narrow at the waist" at all. Lofting
    an ellipse per station - one cell thick along the body, so consecutive stations are 6-adjacent
    by construction - lets the two silhouettes be designed separately, which is what rule 4 of the
    panel review asks for and what a spindle IS.

    **A SUPERELLIPSE, NOT A CIRCLE.** `roundness` in the rubric is measured against known
    sections and a plain ellipse scores 0.06 where a real voxel body wants a rounded square: at
    this scale a circular section loses its corners to rounding and the flanks come out as a
    stack of narrow strips. Exponent 2.6 keeps a flat-ish flank with a turned edge.
    """
    keys = d["spine"]
    e = float(d["section"])
    f_hi, f_lo = keys[0][0], keys[-1][0]
    n = 0
    for fi in range(int(math.floor(f_lo)), int(math.ceil(f_hi)) + 1):
        f = float(fi)
        # find the pair of keyframes this station lies between
        for i in range(len(keys) - 1):
            if keys[i + 1][0] <= f <= keys[i][0]:
                (f0, y0, d0, w0), (f1, y1, d1, w1) = keys[i], keys[i + 1]
                break
        else:
            continue
        t = 0.0 if f0 == f1 else (f0 - f) / (f0 - f1)
        yc = y0 + (y1 - y0) * t
        hd = d0 + (d1 - d0) * t
        hw = w0 + (w1 - w0) * t
        for ds in range(-int(math.ceil(hw)) - 1, int(math.ceil(hw)) + 2):
            for dy in range(-int(math.ceil(hd)) - 1, int(math.ceil(hd)) + 2):
                if (abs(ds) / hw) ** e + (abs(dy) / hd) ** e > 1.0:
                    continue
                if fr.put(f, ds, yc + dy, "flank"):
                    n += 1
    return n


def _legs(fr: _Frame, d: dict) -> dict:
    """Four columnar tapers, the HIND pair longer and heavier than the fore.

    That difference is the whole reason the back arches, and it is the one proportion on this
    animal a stranger would notice if it were wrong: a level-backed stegosaur is a lizard.

    A LEG TAPERS. "Why does your jaguar have four table legs" is the recorded verdict that
    retired eight mammals, and constant-width posts at the extreme corners is what earned it.
    """
    out = {}
    st = d["stance"]
    for name, f, r0, r1 in (("fore", d["fore_f"], d["fore_r0"], d["fore_r1"]),
                            ("hind", d["hind_f"], d["hind_r0"], d["hind_r1"])):
        cells = 0
        top = None
        for (fk, yk, dk, _wk) in d["spine"]:            # the belly directly over this leg
            if top is None or abs(fk - f) < abs(top[0] - f):
                top = (fk, yk - dk * 0.35)
        for s in (st, -st):
            cells += _sweep(fr, (f, s, top[1]), (f, s, r1 * 1.2), r0, r1)
            # the foot: a spread pad, because a column that simply stops reads as a peg
            cells += _ball(fr, f, s, r1 * 0.6, r1 * 1.30)
            cells += _ball(fr, f, s, 0.0, r1 * 1.05)
        out[name] = cells
    return out


def _neck(fr: _Frame, d: dict) -> dict:
    """A SHORT neck curving DOWN to a very small PALE head carried near the ground.

    Both the size and the height are cues rather than details. A stegosaur's skull is the
    smallest thing on it and every reconstruction a stranger has ever seen has it low; drawn
    level, or drawn at any size a modeller would think reasonable, the outline becomes a generic
    quadruped with a crest.

    **THE SKULL IS BONE, AND THAT IS WHAT MAKES A THREE-CELL HEAD EXIST AT ALL.** Painted as body
    it is the end of a taper: there is no line anywhere for a head to begin at, and a black eye
    bead on a dark flank has nowhere to go - which is the bear's own recorded failure, still
    open in CLAUDE.md ("`mangrove_wood` is dark enough that a black bead on it has nowhere to
    go"), and the reason `_eye_ring` exists at all. Pale, the head is a separate object at any
    distance and the eye is legible on it, and the animal reads bone at both ends.
    """
    chest = d["spine"][0]
    n = _sweep(fr, (chest[0], 0.0, chest[1]), (d["neck_f"], 0.0, d["neck_y"]),
               chest[2] * 0.80, d["neck_r"])
    # **THE NECK STOPS WHERE THE SKULL BEGINS.** Swept on to the nose it buries the head: the
    # skull is the one PALE thing at the front and only its last four cells showed past the
    # russet, so the animal read as a neck with a chip on the end. The giraffe's muzzle is most
    # of its head, and that is why it has a face.
    n += _sweep(fr, (d["neck_f"], 0.0, d["neck_y"]), (d["skull_back"], 0.0, d["head_y"]),
                d["neck_r"], d["skull_r0"] * 0.95)
    return {"neck": n}


def _skull(fr: _Frame, d: dict) -> dict:
    """The head, built AFTER the relax pass - features follow the mass, never the other way round.

    "The rule that shaves a one-block pimple off a shoulder eats a horn whole" is this repo's own
    sentence, and a skull on the end of a neck is exactly the shape it eats.

    **A SKULL IS A TAPER, NOT A BALL, and that is what Jack was looking at.** Set beside the
    giraffe - *"we want this to feel like the giraffe"* - the giraffe has a face: a pale muzzle
    narrowing to a nose, an eye set in it, a jaw. This had a SPHERE with a black cube stuck on it,
    which is a bead on a lump however cleanly the rest of the animal is built. A stegosaur's skull
    is the most distinctive thing about it after the plates - long, low and NARROW, ending in a
    toothless beak - and none of that survives being drawn as a ball.

    Swept back-to-front so the cheek is the widest part and the beak the narrowest, dropping as it
    goes, with a `_thread` core first: at the tip the radius is under one cell, and a taper that
    ends under one cell cannot be swept into existence - consecutive spheres share only a corner.
    """
    a = (d["skull_back"], 0.0, d["head_y"] + d["skull_drop"] * 0.45)
    b = (d["skull_tip"], 0.0, d["head_y"] - d["skull_drop"])
    # **THREAD BACK TO WHAT THE RELAX ACTUALLY LEFT OF THE NECK, never to where it was drawn.**
    # The neck is no longer protected from shaving - that is what smooths it - so `keep` eats its
    # thin front end, and how much it eats depends on the length. Abutted to the neck's DESIGNED
    # tip the skull came away as a separate 24-cell piece at length 22 and 26, and at neither of
    # their neighbours: the animal shipped headless at two scales out of seven, silently. A join
    # is made by OVERLAPPING something that is there, which is the pterosaur's own recorded rule.
    # THE THREAD REACHES BACK; THE SWEEP DOES NOT. Moving the sweep's own start point back
    # stretches its taper over a longer run, so the cheek came out too narrow to carry a pair of
    # eyes and the build RAISED. The skull keeps its designed shape and a one-cell core is run
    # back to whatever the neck actually still has.
    n = 0
    reach = int(math.ceil(abs(d["skull_back"] - d["neck_f"]))) + 3
    for back in range(1, reach + 1):
        f = d["skull_back"] - back
        if fr.solid(f, 0, a[2]) or fr.solid(f, 0, d["neck_y"]):
            n += _thread(fr, (f, 0.0, (a[2] + d["neck_y"]) / 2.0), a, "spike", protect=True)
            break
    n += _thread(fr, a, b, "spike", protect=True)
    n += _sweep(fr, a, b, d["skull_r0"], d["skull_r1"], "spike", step=0.20, protect=True)
    return {"skull": n}


def _muzzle(fr: _Frame, d: dict) -> int:
    """The nostril, and the line of the mouth - the two marks that turn a taper into a face.

    **FOUND ON THE BUILT SURFACE, NEVER AT A COMPUTED OFFSET.** A relaxed and swept skull is not
    where the arithmetic that made it says it is: the axolotl's eye beads landed a cell deep and
    were painted over by their own pale ring, and the frog's nostrils were drawn onto a chamfered
    edge and came out as paint over air - `nostril: 0` in its own sidecar, with a clean audit.

    One cell each side and no more. This head is five cells across at the cheek and three at the
    muzzle; anything wider than a single cell is not a nostril, it is a second pair of eyes, which
    the frog also shipped once.
    """
    n = 0
    f = d["skull_tip"] - (d["skull_tip"] - d["skull_back"]) * 0.32
    y = _r(d["head_y"] - d["skull_drop"] * 0.35)
    for sgn in (1, -1):
        for s in range(int(math.ceil(d["skull_r1"] * 2.5)) + 1, -1, -1):
            if fr.solid(f, sgn * s, y):
                # **A NOSTRIL IS NOT BLACK.** The frog put two black cells on its brow between two
                # black pupils and they read head-on as A SECOND PAIR OF EYES. On a bone skull the
                # mid grey is 99 luminance under the bone and 105 over the pupil, which is a mark
                # that reads as a nostril and cannot be mistaken for one.
                fr.put(f, sgn * s, y, "nostril", protect=True)
                n += 1
                break
    return n


def _eyes(fr: _Frame, d: dict) -> int:
    """One bead a side, on the outermost built cell of a course that CARRIES A PAIR.

    **AN EYE IS FOUND, NOT COMPUTED, AND THE COURSE IS FOUND TOO.** The wyrm shipped with ONE
    eye, twice, because a computed offset onto a course where the skull is two cells wide lands
    inside the mass on one side and in air on the other. This animal shipped with NONE at
    length 24, for the neighbouring reason: the nominal course was a cell above the widest part
    of a small skull, so neither side had anything to sit on. No error, nothing in the audit,
    nothing in the component count, nothing in the bill - a scale sweep is the only thing that
    can see it, which is why one is in the test suite.

    So the courses are walked from the crown down, the first that has a solid cell at the same
    offset BOTH sides takes the pair, and an animal that has no such course anywhere RAISES. An
    eyeless build is a fault, not a style, and this project has shipped enough of them silently.
    """
    f = _r(d["skull_back"] + (d["skull_tip"] - d["skull_back"]) * 0.38)
    reach = int(math.ceil(d["skull_r0"] * 2.4)) + 1
    y0 = _r(d["head_y"] + d["skull_r0"] * 0.9)
    for y in range(y0, _r(d["head_y"] - d["skull_r0"]) - 1, -1):
        for s in range(reach, 0, -1):
            if fr.solid(f, s, y) and fr.solid(f, -s, y):
                fr.put(f, s, y, "eye", protect=True)
                fr.put(f, -s, y, "eye", protect=True)
                return 2
    raise ValueError(
        "no course of the skull carries a pair of eyes: the head is too small at this length "
        "for a bead a side, and an animal that ships eyeless does it silently")


def _plates(fr: _Frame, d: dict, count: int) -> dict:
    """The crest: kite-shaped sheets one block thick, in ONE ROW ON THE SAGITTAL PLANE.

    **THEY USED TO ALTERNATE, THE REAL ANIMAL DOES ALTERNATE, AND IT WAS THE WRONG CALL.** Jack,
    on the first build: *"its asymmetric, theres issues"* - and measured block by block, the
    alternating crest WAS the only asymmetry in the whole animal: 99 cells, every one of them a
    plate, with the coat and the mass exactly mirrored. It costs two of the four views outright.
    Head-on, two rows offset one cell either side of a nine-wide back are not two rows, they are
    TWO ORANGE CHIMNEYS AT DIFFERENT DEPTHS; in plan they are a drunk zigzag rather than a crest.
    A real stegosaur is two metres wide and staggers its plates by a hand's breadth. A voxel one
    at this size has one cell to say it with, and one cell is a fault rather than a stagger.

    **THE ANSWER IS TWO ROWS PAIRED, NOT ONE ROW CENTRED AND NOT TWO ROWS STAGGERED.** Centred
    on the sagittal plane a plate is its own mirror and the asymmetry is gone - and head-on the
    crest becomes a single one-block blade standing straight up out of the spine, which is a MAST.
    Paired at the same station either side of the midline it is symmetric AND it is what a
    stegosaur looks like from the front: two pale blades flanking a ridge, with the spine showing
    between them. In profile the pair superimposes into one plate, so nothing is lost there; in
    plan it is two clean rows instead of a zigzag. `_mirror` reports zero on shape and on colour.

    **AND ON ONE ROW THE PITCH HAS TO CARRY THE WHOLE SEPARATION.** Alternating, two neighbours
    could never touch because they were on different planes; centred, they share a plane and the
    gap is real geometry. Five plates over this run put their widest courses in contact and the
    crest fused into a sail - the failure this file already records from the other direction - so
    it is FOUR, each up to five cells across with a clear cell either side. Four big kites read
    as a stegosaur; six small ones read as a comb.

    Every plate is rooted on the surface the body ACTUALLY BUILT, probed column by column and
    SNAPSHOTTED before any plate is laid. Probed live, the second course of a plate finds the
    first course of that same plate as its own top and lands one higher again: every plate
    shipped as alternate courses with a hole between them, fifty four-cell strays, and only a
    component count could see it. MEASURE THE MASS, NEVER THE ACCUMULATING BUFFER.
    """
    f0, f1 = d["plate_f0"], d["plate_f1"]
    run = f0 - f1
    off = int(d["plate_offset"])
    # **THE SPACING IS EXACT INTEGER GEOMETRY, NOT AN EMERGENT PROPERTY OF A FLOAT STATION.**
    # Two tries got this wrong. Left to the width curve alone, `plate_half` scaled to 2.54 for
    # the plate nearest the peak and `floor(2.54 + 0.5)` is 3, so that one plate jumped from five
    # cells across to SEVEN and fused with its neighbour - the crest read as three plates, not
    # four. Capping the width against `run / count` fixed that length and not the next: the
    # stations are floats, `_r` rounds them, and the achieved gap is a cell narrower than the
    # nominal pitch about half the time.
    #
    # So the WIDTH is chosen first and the PITCH is derived from it as `2 * wi + 2`, which leaves
    # exactly one cell of sky between neighbours whatever the length, the count or the curve. If
    # that many plates will not fit the run, the plates get narrower and then fewer - never
    # closer. A crest that can merge under any tuning is a sail waiting to happen.
    wi_cap = max(1, int(d["plate_half"]))
    while count > 1 and (count - 1) * (2 * wi_cap + 2) + (2 * wi_cap + 1) > run:
        if wi_cap > 1:
            wi_cap -= 1
        else:
            count -= 1
    pitch = 2 * wi_cap + 2
    wi_max = wi_cap + 1
    mid_f = (f0 + f1) / 2.0
    stations = [_r(mid_f + (count - 1) / 2.0 * pitch - i * pitch) for i in range(count)]
    # THE SURFACE IS SNAPSHOTTED PER ROW, BEFORE ANYTHING IS LAID. Both rows probe the back the
    # BODY built, never each other and never their own courses.
    tops = {}
    for f in stations:
        for df in range(-wi_max, wi_max + 1):
            for s_off in (off, -off):
                key = (f + df, s_off)
                if key not in tops:
                    tops[key] = fr.top_y(f + df, s_off)

    built, tallest, skipped = 0, 0, 0
    for i, f in enumerate(stations):
        t = (f0 - f) / max(1e-6, run)             # where along the crest this plate stands
        # tallest OVER THE HIPS, which is 0.55 of the run - the hip keyframe is at -0.15L and the
        # crest runs 0.30L to -0.48L. Peaked at the mid-point instead, the biggest plate stands
        # over the waist, which is nobody's stegosaur.
        u = abs(t - 0.55) / max(0.55, 1.0 - 0.55)
        h = max(3, int(round(d["plate_h_min"]
                             + (d["plate_h_max"] - d["plate_h_min"]) * (1.0 - u * u))))
        half = d["plate_half"] * (0.72 + 0.28 * (1.0 - u * u))   # a short plate is a narrow one
        placed_here = 0
        for j in range(h):
            hf = j / float(max(1, h - 1))
            # A KITE: THREE CELLS AT THE ROOT, FIVE AT THE WIDEST, A POINT AT THE TOP.
            #
            # Both ends of that are a correction. A full-width column all the way down merges the
            # crest into one sheet; a one-cell root leaves each plate hovering on a stalk with
            # daylight between it and the back it is supposed to grow out of. And the widening is
            # SLOW on purpose - reaching the widest by the second course put every plate's base in
            # contact with its neighbour's and ran the root band unbroken from shoulder to tail.
            # Measured off the built courses rather than trusted: the first curve gave
            # `3,5,5,5,5,5,5,3` - a rectangle with one cell chamfered off each end, which is a
            # TOMBSTONE. A plate has to rise fast off a three-cell root, hold its width through
            # the lower half and come to a POINT, which is `3,5,5,5,5,3,3,1`.
            if hf < 0.18:
                w = half * (0.55 + 0.45 * hf / 0.18)
            elif hf < 0.42:
                w = half
            else:
                w = half * (1.0 - 0.88 * (hf - 0.42) / 0.58)
            wi = min(wi_cap, int(math.floor(w + 0.5)))
            for df in range(-wi, wi + 1):
                for s_off in (off, -off):
                    top = tops.get((f + df, s_off))
                    if top is None:
                        continue                  # past the body: no root, no plate column
                    # **A COLUMN REACHES DOWN TO ITS LOWER NEIGHBOUR'S ROOT.** Each column starts
                    # on its own patch of back, and where the back drops two courses between one
                    # column and the next their cell ranges stop overlapping - so a plate's outer
                    # wing comes away as a two-cell stray. At length 30 and not at 26 or 34, which
                    # is the signature of every rounding fault in this file.
                    lo = top
                    for dn in (-1, 1):
                        nb = tops.get((f + df + dn, s_off))
                        if nb is not None:
                            lo = min(lo, nb)
                    for yy in range(lo + 1, top + 1 + j + 1):
                        key = "plate_root" if yy <= lo + 1 else "plate"
                        if fr.put(f + df, s_off, yy, key, protect=True):
                            placed_here += 1
        if placed_here:
            built += 1
            tallest = max(tallest, h)
        else:
            skipped += 1
    return {"plates": built, "tallest": tallest, "skipped": skipped}


def _tail_y_at(d: dict, f: float) -> float:
    """The tail's own centre height at a station, interpolated along the sweep that built it -
    so a spike's root moves with the tail rather than being pinned to a number that was right
    once. Anything clinging to a computed constant is the detached-ossicone bug waiting."""
    rump = d["spine"][-1]
    t = (rump[0] - f) / max(1e-6, rump[0] - d["tail_f"])
    t = max(0.0, min(1.0, t))
    return rump[1] + (d["tail_y"] - rump[1]) * t


def _spikes(fr: _Frame, d: dict) -> int:
    """The thagomizer: four columns off the tail, two a side, angled back, out and up.

    A ONE-CELL SPIKE IS NOT CONNECTED TO ANYTHING. Swept at a radius under about 0.8 the
    consecutive spheres share only a corner, which is the ear-tip failure - so each is swept
    thick enough to overlap along its whole length, and each STARTS INSIDE the tail rather than
    against its computed surface. A join is made by overlapping, never by abutting an edge, which
    is the pterosaur's own recorded rule after it came apart at three separate spans.
    """
    n = 0
    for k, back in enumerate((0.0, -0.105)):
        f = d["spike_f"] + back * d["L"]
        # **ROOTED IN THE TAIL THAT WAS BUILT, NEVER AT THE HEIGHT IT WAS DRAWN AT.** `_tail_y_at`
        # interpolates the tail's designed centre line, which was right while the tail was
        # PROTECTED from the relax pass. Un-protecting it is what finally smoothed it - and the
        # same shave moves its surface, so the spikes started in mid-air and the whole thagomizer
        # came away as one 24-to-90-cell piece at four lengths out of seventeen. `loft.surface_out`
        # exists for exactly this, and it has already cost this project a mane, a pair of
        # ossicones and a tail that floated 45 cells clear.
        # SEARCHED IN BOTH AXES, because the relax can shave the tail's TIP away entirely and
        # then no height at that station has anything in it at all.
        base_y = _tail_y_at(d, f)
        found = False
        for df in range(0, int(math.ceil(d["spike_len"])) + 3):
            for dy in (0, -1, 1, -2, 2, -3, 3, -4, 4):
                if fr.solid(f + df, 0, base_y + dy):
                    f, base_y, found = f + df, base_y + dy, True
                    break
            if found:
                break
        for sgn in (1, -1):
            a = (f, 0.0, base_y)
            # BACK AND OUT, barely up. Aimed upward they came out as two bone cauliflowers on
            # the rump and read as antlers; a thagomizer is four horizontal skewers and its
            # whole job is to widen the tail's own silhouette in PLAN and in profile.
            b = (f - d["spike_len"] * 0.86, sgn * d["spike_len"] * 0.62,
                 base_y + d["spike_len"] * (0.20 + 0.22 * k))
            n += _thread(fr, a, b, "spike")
            n += _sweep(fr, a, b, d["spike_r"] * 1.35, d["spike_r"] * 0.72, "spike", step=0.18)
    return n


def _tail(fr: _Frame, d: dict) -> int:
    """From the rump, back and slightly DOWN, and carried clear of the ground the whole way -
    a stegosaur does not drag its tail, and a tail on the floor reads as a lizard."""
    rump = d["spine"][-1]
    return _sweep(fr, (rump[0], 0.0, rump[1]), (d["tail_f"], 0.0, d["tail_y"]),
                  rump[2], d["tail_r"])


def _band(d: dict, f: float) -> tuple:
    """(belly, back) - the body's own underside and topline at this station.

    ONE CONTINUOUS SPINE FROM NOSE TO TAIL TIP, not just the barrel: the neck's and the tail's own
    keyframes are folded in at both ends, so a station anywhere on the animal has a real pair of
    lines to be measured between and the countershading runs unbroken along the whole length.
    """
    keys = ([(d["head_f"], d["head_y"], d["head_r"]),
             (d["neck_f"], d["neck_y"], d["neck_r"])]
            + [(f0, y0, hd) for (f0, y0, hd, _hw) in d["spine"]]
            + [(d["tail_f"], d["tail_y"], d["tail_r"])])
    if f >= keys[0][0]:
        _f, y, r = keys[0]
    elif f <= keys[-1][0]:
        _f, y, r = keys[-1]
    else:
        for i in range(len(keys) - 1):
            (f0, y0, r0), (f1, y1, r1) = keys[i], keys[i + 1]
            if f1 <= f <= f0:
                t = 0.0 if f0 == f1 else (f0 - f) / (f0 - f1)
                y, r = y0 + (y1 - y0) * t, r0 + (r1 - r0) * t
                break
        else:
            _f, y, r = keys[-1]
    return y - r, y + r


def _belly_at(d: dict, f: float) -> float:
    """The body's own underside at this station - `_band`'s lower half, kept as its own name
    because `_relax_mass` asks only this question and reads better for asking it plainly."""
    return _band(d, f)[0]


def _coat(fr: _Frame, d: dict) -> dict:
    """Countershading measured against the BODY'S OWN LINE at each station, never per column.

    **THIS IS WHAT "SUPER BLOCKY AND ROUGH" ACTUALLY WAS**, and it is not geometry at all. Written
    per column - each cell's height as a fraction between that column's own lowest and highest
    cell - the band boundaries follow whatever the column happens to be tall, and on a lofted body
    every column is a different height. The result is not three bands, it is GREY BLOTCHES
    SCATTERED OVER THE FLANK: pale patches at the shoulder, the hip and along the neck, wandering
    a course up and down from one column to the next. A close render reads it as mould on the
    animal, and no amount of smoothing the mass touches it, because the mass was not the problem.

    Measured against the belly and the back lines the keyframes actually describe, the bands are
    continuous along the whole length by construction and the boundaries are as smooth as the
    spine is. It is the same rule the rest of this repo already follows - a lion's pale belly band
    is set from the POSED skeleton, and getting that wrong left "pale bands round a sitting cat's
    knees".

    **A LEG IS STILL NOT ITS OWN ANIMAL.** Everything below the belly line takes the flank tone
    and nothing else: countershaded per column a leg's four courses got the full ladder, pale at
    the foot and dark at the top, so the animal stood on four grey posts.

    **AND COUNTERSHADING NEEDS THICKNESS.** Three bands want a section deep enough to hold three,
    and a tail two or three cells thick has room for none: measured against its own line, every
    cell of it lands in a different band and the tail comes out as an alternating brown-grey chain,
    which reads as damage. Below `coat_min_depth` the part is one tone. Same reason the plates,
    the skull and the spikes are one tone each - a feature this repo can only draw four cells wide
    is a feature that gets one colour.

    The boundaries are dithered by half a cell, no more. A hard line across a curved flank reads as
    a contour on a map (`spiral.bands` found the same about a helix, where a hard change of stone
    read as two staircases stacked); a wide dither just puts the blotches back.
    """
    c = fr.c
    S = {k: c.state(HIDE[k]) for k in ("back", "flank", "belly")}
    tally = {"back": 0, "flank": 0, "belly": 0}
    for v in range(c.sx):
        for u in range(c.sz):
            f = (v - fr.cv) * fr.fx + (u - fr.cu) * fr.fz
            across = (v - fr.cv) * fr.sx + (u - fr.cu) * fr.sz
            along = int(round(f))
            floor, top = _band(d, f)
            span = max(1.0, top - floor)
            deep = span >= float(d["coat_min_depth"])
            for y in range(c.sy):
                if not c.solid(v, y, u) or (v, y, u) in fr.fixed:
                    continue
                fy = (y - floor) / span
                # **HASHED ON THE DISTANCE FROM THE MIDLINE, NEVER ON THE COLUMN.** Keyed on
                # `v` the dither is a different number on each flank, so the band boundary
                # wobbles independently left and right and the animal comes out sixteen
                # cells asymmetric IN COLOUR while its shape is exact - the frog's own
                # recorded fault, where each coat drift carried its own signed offset and a
                # dark patch on one flank read as a dent rather than as a marking.
                jitter = (hash01(abs(across), y, along, 7, 3) - 0.5) * (0.5 / span)
                if not deep or y < floor - 0.5:
                    key = "flank"       # a leg, a foot, the tail: one tone, never a ladder
                elif fy + jitter > 0.70:
                    key = "back"
                elif fy + jitter < 0.26:
                    key = "belly"
                else:
                    key = "flank"
                c.put(v, y, u, S[key])
                tally[key] += 1
    return tally


def _mirror(fr: _Frame, d: dict) -> dict:
    """**ENFORCE THE MIRROR, NEVER ASSUME IT.** Every part here is built for both signs and every
    span is centred, so the shape is symmetric by construction - and the squid was too, and came
    out 5,375 cells different left to right because a limb swept from a float centre mirrors
    about a column's EDGE rather than its middle.

    Reported in two halves because they are two different facts: the SHAPE count must stay at
    zero and is what catches a real fault, and the PLATE count is expected to be large - the
    crest alternates on purpose, so a plate has no twin and must not be counted as damage.
    """
    c = fr.c
    shape = plates = 0
    reach = int(c.sx if fr.sx else c.sz)
    for f in range(-reach, reach + 1):
        for s in range(1, reach + 1):
            a = fr.at(f, s)
            b = fr.at(f, -s)
            for y in range(c.sy):
                ga = c.solid(a[0], y, a[1])
                gb = c.solid(b[0], y, b[1])
                if ga == gb:
                    continue
                if (a[0], y, a[1]) in fr.fixed or (b[0], y, b[1]) in fr.fixed:
                    plates += 1
                else:
                    shape += 1
    return {"shape": shape, "plates": plates}


def _solid_cells(c: Canvas) -> set:
    """Every cell the build has put down so far, in canvas coordinates."""
    ys, zs, xs = np.nonzero(c.ids > 0)
    return {(int(x), int(y), int(z)) for x, y, z in zip(xs.tolist(), ys.tolist(), zs.tolist())}


def _relax_mass(fr: _Frame, d: dict, protect: set) -> dict:
    """**STEP 2 OF THE BUILD ORDER THIS REPO ALREADY WROTE DOWN, AND THIS ANIMAL SKIPPED IT.**

    CLAUDE.md's ANIMALS section states the order as `mass -> relax -> features -> face -> coat`,
    and every quadruped in this project runs it. The stegosaur went straight from a lofted mass to
    its features, so every station's own ellipse showed as a step in the flank and the verdict was
    the obvious one: *"it feels super blocky and rough."* A loft is a stack of boxes until
    something rounds the joins between them.

    **THE TWO GUARDS ARE NOT OPTIONAL AND BOTH ARE RECORDED FAILURES.**

    `protect` - relax removes any cell with too few neighbours, and a slender leg, a tail or a
    neck HAS too few by nature. Unprotected, the same rule that shaves a pimple off a shoulder
    eats a limb whole; the giraffe lost features to exactly this.

    `forbid` - filling is blind to anatomy. It reads the air between two legs as a one-block dent
    worth filling and WELDS THEM INTO A SLAB: the giraffe's four legs came out as one part for the
    whole lower half, measured 11 blocks wide against a target of 3. So every air cell below the
    body's own belly line is barred - except the air inside a leg's own cylinder, because a dent
    in a LEG is a dent worth filling and barring those would keep the legs as lumpy as they were.
    That distinction is what lets the gaps survive while the limbs still smooth.
    """
    c = fr.c
    mass = _solid_cells(c)
    legs = [(d["fore_f"], d["fore_r0"]), (d["hind_f"], d["hind_r0"])]
    forbid = set()
    for v in range(c.sx):
        for u in range(c.sz):
            f = (v - fr.cv) * fr.fx + (u - fr.cu) * fr.fz
            sd = (v - fr.cv) * fr.sx + (u - fr.cu) * fr.sz
            floor = _belly_at(d, f)
            # **THE DISTANCE FROM THE LEG'S OWN AXIS, WHICH IS AN ABSOLUTE DIFFERENCE.** Written
            # `abs(sd) - stance < r` this is TRUE FOR EVERY CELL ON THE MIDLINE - `0 - stance` is
            # negative - so the entire space between the legs counted as "inside a leg", was never
            # forbidden, and the fill pass welded the feet into pairs. Two feet instead of four at
            # most lengths and four at the one being looked at, which is the giraffe's own
            # recorded disaster: its legs came out as one part for the whole lower half.
            # ...**AND THE REACH IS CLAMPED TO HALF THE LEG SPACING**, which is CLAUDE.md's own
            # sentence: "it must be clamped to half the leg spacing or it protects nothing". At
            # `r + 0.6` alone a thigh 1.86 wide standing 2.34 off the midline reaches the midline
            # itself, so the gap between the two hind feet counted as leg, was never forbidden and
            # the fill pass welded them: three feet instead of four, at most lengths and not at
            # the one being looked at.
            inside_leg = any(abs(abs(sd) - d["stance"]) < min(r + 0.6, d["stance"] - 0.6)
                             and abs(f - lf) < r + 0.6 for lf, r in legs)
            for y in range(int(math.ceil(floor)) + 1):
                if (v, y, u) in mass or inside_leg:
                    continue
                forbid.add((v, y, u))
    out = smooth.relax(mass, rounds=int(d["relax_rounds"]), fill=int(d["relax_fill"]),
                       keep=int(d["relax_keep"]), protect=protect, forbid=forbid)
    flank = c.state(HIDE["flank"])
    for (v, y, u) in mass - out:
        c.put(v, y, u, 0)
    for (v, y, u) in out - mass:
        c.put(v, y, u, flank)
    before = smooth.roughness(mass)
    after = smooth.roughness(out)
    # REPORTED AS BEFORE -> AFTER, and scale-free, because the raw counts grow with the model:
    # ranking variants on them quietly prefers the smallest one, which a girth sweep once
    # "discovered" as thinner being smoother.
    return {"filled": len(out - mass), "shaved": len(mass - out),
            "spike_rate": [round(before["spike_rate"], 4), round(after["spike_rate"], 4)],
            "notches": [before["notches"], after["notches"]],
            "jerk_rel": [round(before["jerk_rel"], 4), round(after["jerk_rel"], 4)]}


def _skin(fr: _Frame) -> dict:
    """{cell: block name} for the animal's own COAT - never a drawn feature.

    **A PALETTE ENTRY IS AN NBT TAG, NOT A STRING.** `str(Tag(10, {'Name': ...}))` is a repr, so a
    name read that way matches nothing, every colour lookup fails and the surfacing pass reports
    zero cells halved while looking exactly like a pass that had nothing to do. `nbt.state_name`
    is the accessor, and it is the same one every test in this repo already uses.

    The plates, the skull, the spikes and the eyes are excluded, and so is any cell a plate ROOTS
    on: the frog's rule that the face and the toes are a DRAWING, and a half block through one of
    them is a hole in it rather than a smoothing.
    """
    c = fr.c
    names = [nbt.state_name(e).split(":")[-1].split("[")[0] for e in c.reg.palette]
    out = {}
    for (v, y, u) in _solid_cells(c):
        if (v, y, u) in fr.fixed or (v, y + 1, u) in fr.fixed:
            continue
        out[(v, y, u)] = names[int(c.ids[y, u, v])]
    return out


def _surface(fr: _Frame, d: dict) -> dict:
    """Half-block and stair surfacing over the coat, through `gen/shell.py`.

    **BOTH PASSES LIVE IN `shell.py` AND NOT HERE, WHICH IS THE POINT OF DOING IT AT ALL.** This
    animal is the first in the repo to need stair surfacing and it will not be the last: the
    module already owned "which cells earn a slab", its own docstring said it was "ready for"
    stairs, and writing a second private copy in one generator is how two rules for one question
    start disagreeing. `shell.stair_shell` is now available to the elephant, the giraffe, the frog
    and everything after them.

    STAIRS FIRST, THEN SLABS ON WHAT IS LEFT. On the TOP face the two are disjoint by construction
    - a slab wants NO higher neighbour and a stair wants exactly one - but an underside stair and
    a top slab can both want the same cell, and a cell may only have one shape.

    **AND NEITHER TOUCHES A DRAWN FEATURE.** `_skin` already withholds the plates, the skull, the
    spikes, the eyes and every cell a plate roots on: the frog's rule that a face or a toe is a
    DRAWING, and a partial through one of them is a hole in it rather than a smoothing.
    """
    c = fr.c
    skin = _skin(fr)
    ramps = shell.stair_shell(set(skin), skin, HIDE["flank"], under=True, floor_y=0)
    rest = {k: v for k, v in skin.items() if k not in ramps}
    cut = shell.slab_shell(set(rest), rest, HIDE["flank"], floor_y=0)
    for cell, (name, props) in list(ramps.items()) + list(cut.items()):
        c.put(cell[0], cell[1], cell[2], c.state(name, **props))
    tops = sum(1 for _n, p in ramps.values() if p["half"] == "bottom")
    return {"stairs": len(ramps), "stairs_under": len(ramps) - tops,
            "slabs": len(cut), "skin": len(skin)}


# ------------------------------------------------------------------------------------- the build

def build_stegosaur(cfg: dict, donors=None) -> Canvas:
    p = {**STEGOSAUR, **(cfg or {})}
    L = float(p.get("length") or 30) * float(p.get("scale") or 1.0)
    if L < 21:
        raise ValueError(
            "a stegosaur under 21 blocks cannot carry a legible plate: the tallest is ~0.24 of "
            "the length and a plate under five courses is a bump on a back. Its identity is the "
            "CREST and there would be nothing left of it")
    d = _dims(L)
    for k in ("relax_rounds", "relax_fill", "relax_keep"):
        if p.get(k) is not None:
            d[k] = p[k]
    facing = str(p.get("facing", "north"))
    if facing not in _STEP:
        raise ValueError(f"a stegosaur needs a real facing, not {facing!r}")

    # **THE CANVAS IS SIZED BY THE FACING, NOT BY THE ANIMAL.** A box that is always long in X is
    # long in the WRONG axis for a north-south animal: the sauropod built facing north came out
    # clipped to 22 blocks of 48 - head, neck and half the tail simply refused - and the only
    # symptom was a refusal count nobody was reading, while the render still showed a plausible
    # small dinosaur. The frame maps forward and side onto the world; the box is mapped the same
    # way or the two disagree.
    span_fore = int(math.ceil(d["head_f"] + d["head_r"] * 3 + 3))
    span_back = int(math.ceil(-d["tail_f"] + d["spike_len"] + 4))
    length = span_fore + span_back + 1
    width = int(math.ceil((d["stance"] + max(d["hind_r0"], d["spike_len"])) * 2 + 5))
    sy = int(math.ceil(d["spine"][3][1] + d["spine"][3][2] + d["plate_h_max"] + 3))

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
    fr = _Frame(c, cv, cu, facing)

    # **MASS -> RELAX -> FEATURES -> COAT, which is CLAUDE.md's own build order and which the
    # first two versions of this animal did not follow.** Every step of it is load-bearing:
    # features go in after the smoothing because the rule that shaves a pimple off a shoulder
    # eats a horn whole, and the coat goes in after the features because the countershade
    # measures each column between its own lowest and highest cell - a crest already standing
    # would make every plated column read as a back seven courses tall.
    parts = {}
    parts["body"] = _body(fr, d)
    seen = _solid_cells(c)
    parts["legs"] = _legs(fr, d)
    # **ONLY THE LEGS ARE PROTECTED, which is what `quadruped.py` does and this did not.** A
    # protected cell is never shaved, so protecting the neck and the tail as well left them
    # exactly as lumpy as they were built while the barrel smoothed around them - the two parts
    # that read worst against the giraffe. A leg genuinely has too few neighbours to survive
    # `keep`; a tail three cells thick does not.
    legs = _solid_cells(c) - seen
    parts["tail"] = _tail(fr, d)
    parts.update(_neck(fr, d))
    parts["relax"] = _relax_mass(fr, d, protect=(legs if p.get("relax_protect", True) else set()))
    parts.update(_skull(fr, d))
    parts["coat"] = _coat(fr, d)
    parts.update(_plates(fr, d, max(3, int(p.get("plates") or 4))))
    parts["spikes"] = _spikes(fr, d)
    parts["eyes"] = _eyes(fr, d)
    parts["nostrils"] = _muzzle(fr, d)
    parts["surface"] = _surface(fr, d)
    parts["mirror"] = _mirror(fr, d)

    if p.get("stand"):
        wx, wy, wz = (int(round(float(v))) for v in p["stand"])
        c.world_origin = (wx - cv, wy, wz - cu)
    elif p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    c.meta = {
        "kind": "stegosaur",
        "facing": facing,
        "length": round(L, 1),
        "profile_axis": "u" if along_x else "v",
        "refused": fr.refused,
        "clipped": fr.clipped,
        "parts": parts,
        "contract": (
            "a stegosaur: one convex arched mass on four columnar tapers, the hind pair longer, "
            "a very small head carried low on a short down-curving neck, a tail held clear of the "
            "ground with four spikes, and a crest of kite-shaped one-block sheets ALTERNATING "
            "either side of the spine, every one rooted on the surface the body actually built. "
            "One piece, countershaded off its own finished form, and every tone a measured step "
            "from the moss it stands on."),
    }
    return c


build = build_stegosaur
DEFAULTS = STEGOSAUR
