"""A colossal squid rising through the dark under the theme park.

WHY A SQUID, AND WHY IT IS NOT A GAMBLE. CLAUDE.md's measured line is PLANAR/COLUMNAR against
VOLUMETRIC, learned on eight failed mammals: compound muscle is the one thing voxels render
worst and no amount of scale rescues it - the jaguar at 2.6x and 60,000 blocks failed exactly
as the 27-block one did. A squid has no muscle mass to describe anywhere:

    mantle      a long taper. The giraffe's neck, which is the one quadruped part this system
                has ever got right
    fins        two flat sheets. The sky bird's wing and the bat's membrane
    arms        eight tapers, curved. Columns
    tentacles   two more, longer and thinner. Columns
    eyes        two convex domes carrying a pattern - the ladybird's own category. A colossal
                squid's eye is the largest in nature, about 6% of its length, so the one
                feature this medium is best at is also the animal's headline

There is not one joint in it and not one proportion that has to be right to a few per cent for
a stranger to name it. That is the whole argument, and it is the same argument `balloon.py`
makes for a dome on lines over a box.

THE SITE IS PITCH DARK AND THAT DECIDED THE DESIGN. Measured over `out/Park Complete
.litematic`: of the 120,000 columns in the park's own 200x600 shadow, 114,267 have something
overhead - 100% under the Frontier, the Midway and both causeway gaps, and only the Prism
Well's own mouth is open at all. There is no sky light in that void at any hour. So the animal
cannot be lit from outside and has to be its own light source, which is what a deep-sea
cephalopod IS. The photophores are not decoration, they are the only reason anything down
there can be seen - and they are why the coat is deep red, because red is the first colour to
vanish at depth and a red animal in the dark is a black animal with lights on it.

    ochre_froglight   the flank rows, the eye organs and the limbs   (light 15, cheap)
    glow_lichen       a fine speckle over the skin                   (light  7, cheap)

and there is only one full-block light in the palette because there is only one in this WORLD.
`verdant` and `pearlescent` froglight are cheap, legal and better - real bioluminescence is
blue-green - and they appear in no capture at all. They appear in `out/Park Complete.litematic`
because one of our own designs puts them there, which is the trap: a witness set built from
`out/` is circular. The captures are the witness.

THE KEEP-OUT IS A SAFETY NUMBER, NOT A SHAPE. The Prism Well is lined to r52 and stops: below
Y187 its shaft is open void with nothing in it but a 27x27 return column and two parkour
helices at r19-23 and r31-35. A runner who misses a landing falls 86 courses through that.
NOTHING IN THIS DESIGN MAY ENTER r52 OF (97590, 80815) - a surface inside the fall column does
not save a runner, it strands one sixty blocks out in the void with no way back. `keep_out`
refuses every cell by construction and the meta records the closest approach actually
achieved, so the number is measured rather than trusted.

THE COMPOSITION IS DEPTH, AND THE GEOMETRY FORCES IT. Three layouts fought this before the
arithmetic was written down: an arm of length L off a head at distance D reaches r = D - L, so
an 85-block crown on a head 80 blocks out lands inside the shaft every time, whichever way it
is aimed. The head has to stand at r >= 52 + arm_len. That is not a compromise - it puts the
ARM TIPS near, filling the view, the HEAD mid, and the MANTLE receding into black, which is
the one arrangement that gives a voxel sculpture in empty space any sense of scale. The
ladybird needed a leaf for exactly this reason; this needs its own far end.

THE SPINE HAS NO SIDEWAYS SWAY. All of the curve is in Y - the animal rises. A body axis that
wanders in X breaks bilateral symmetry (0.09 of the rubric) for nothing, and it puts the head
off the block grid, which is the axolotl's recorded failure: a head aimed forty degrees off
cardinal is a diagonal staircase of corners in game and reads as a blob, while every
orthographic sheet de-jags it by construction and looks perfectly correct.

MIRRORED BY CONSTRUCTION, NEVER BY INSPECTION. Every paired part is drawn from one `sgn` loop
about an INTEGER centre column, and every hash that decides a colour or a scallop is folded on
|x - XC| first. The frog shipped 104 unmirrored cells out of a mass that was symmetric by
construction, because its coat carried a signed offset per drift - a dark patch reads as a
RECESS, so an unmirrored coat looks like a body dented down one side.
"""
from __future__ import annotations

import math

import numpy as np

from .canvas import Canvas, hash01
from .loft import lerp

# part ids, so the coat can repaint the body without ever touching a sucker, an eye or a lamp
P_MANTLE, P_HEAD, P_FIN, P_ARM, P_TENT, P_CLUB, P_FUNNEL, P_LICHEN = range(1, 9)

SQUID = {
    "seed": 7,
    "scale": 1.0,
    # the world cell the canvas corner occupies. A bespoke generator states this itself or the
    # pipeline writes no sidecar - and with no sidecar there is no origin, no in-context audit
    # and no `/cscan place`.
    "at": None,
    # (x, z, r): a vertical cylinder in WORLD coordinates no cell may enter. The Prism Well's
    # fall column. Refused per cell, and the achieved minimum is reported in the sidecar.
    "keep_out": None,

    # ---- the mantle. 165 long and 28 across is about 6:1, which is a giant squid rather than
    # a colossal one (nearer 2.5:1). The fatter ratio is anatomically truer and costs three
    # hundred thousand blocks; 6:1 is also what makes the far end read as a taper receding
    # into black rather than as a log, which is the whole job of the far end.
    "mantle_len": 165,
    "mantle_r": 13.0,
    "sect_n": 2.2,          # superellipse exponent: 2 is an ellipse, large is a box
    "tip_y": 6,             # canvas Y of the body axis at the mantle's point
    "collar_y": 44,         # ...and at the collar. The difference IS the rise
    "rise_pow": 1.8,        # >1 puts the climb at the FRONT: an animal powering upward

    "head_len": 30,
    "head_rise": 6,

    "fin_from": 0.10,       # fraction along the mantle
    "fin_to": 0.46,
    "fin_span": 42.0,       # beyond the mantle's own surface
    "fin_thick": 3.0,

    "arms": 8,
    "arm_len": 92.0,
    "arm_r": 6.0,
    "arm_spread": 0.68,     # the tip's radial reach, as a fraction of arm_len
    "crown_squash": 0.60,   # THE CROWN IS AN ELLIPSE, NOT A CIRCLE, and this is a site fact
                            # rather than a taste. A crown of radius R opens 2R across the plane
                            # perpendicular to the body, and this body is nearly horizontal, so a
                            # round crown is 124 courses tall in a void that is 93 deep - the
                            # first build clipped its four lower arms against the canvas floor
                            # and still rendered as a plausible squid, which is the sauropod's
                            # own recorded bug. Squashed, the fan spreads sideways instead, which
                            # is both what a lunging squid does and the better view from a shaft.
    "arm_reach": 0.56,      # ...and its forward reach. LESS than the mid control point, so the
                            # crown opens like an umbrella and the tips curl outward and BACK
    "sucker_every": 4.0,

    "tent_len": 150.0,
    "tent_r": 3.4,
    "tent_up": 0.22,        # the club's rise, as a fraction of tent_len. This is what sets the
                            # design's ceiling, and the ceiling is the park's own underside
    "club_frac": 0.16,      # the last sixth of a tentacle is the club
    "club_r": 7.0,

    "eye_r": 10.0,
    "eye_at": 0.34,         # fraction along the head

    "photo_every": 5.0,     # blocks between photophores along a row
    "lichen_p": 0.03,       # fraction of skin cells taking a lichen speckle

    # ---- palette. EVERY BLOCK IS WITNESSED IN A WORLD CAPTURE, not in the tier table and not
    # in `out/`. The first build's base coat was `nether_wart_block` - cheap by the table, legal
    # in 1.19, and it has NEVER BEEN SEEN in this world: 90,766 blocks of a material with no
    # evidence behind it, which is rule 12 exactly. And the first photophore was
    # `verdant_froglight`, which IS in `out/Park Complete.litematic` - because one of our own
    # designs puts it there. **A witness set built from `out/` is circular.** Checked against
    # `island_full` and `island_now`, which are captures of the real world:
    #
    #   ochre_froglight  39      the ONLY froglight in this world, and Jack's own idiom
    #   glow_lichen     191      mangrove_planks   33      red_wool     3720
    #   black_wool     2815      magenta_wool     111      pink_wool     682
    #   bone_block     4007
    #
    # THE BULK IS PLANKS, NOT WOOL, AND THAT IS AN ECONOMY DECISION. 90,000 of anything is a
    # real ask on a skyblock. Mangrove is four planks a log off a tree that replants itself;
    # the same count in wool is 90,000 shears plus 11,000 red dye. It is also the right colour:
    # a deep-sea squid is a dull brick red, not a postbox red, and red is the first colour to
    # vanish at depth - so a red animal in the dark is a black animal with lights on it.
    #
    # The value ladder is measured ACROSS families and never inside one - this repo drew the
    # opposite conclusion four separate times, within stone brick, within blackstone and twice
    # within the greys, and every one of those searches was inside a family where a ladder
    # cannot exist by construction:
    #
    #   black_wool 21 . mangrove_planks 73 / red_wool 75 . magenta_wool 118 . pink_wool 173
    #   . bone_block 227
    #
    # Steps of 52, 45, 55 and 54. Mangrove and red sit at the SAME value on purpose: they are
    # 48 apart in RGB and identical in luminance, which is what a chromatophore mottle is - a
    # change of colour across a surface that does not break its form.
    "deep": "mangrove_planks",         # the bulk of the coat: dull deep red
    "mid": "red_wool",                 # the saturated chromatophore mottle
    "lift": "magenta_wool",            # ventral
    "pale": "pink_wool",               # the arms' inner face, so the crown draws its own line
    "dark": "black_wool",              # dorsal shadow, pupil, eye rim, beak
    "sucker": "bone_block",
    # ONE LIGHT BLOCK, because there is only one in this world. `verdant` and `pearlescent`
    # froglight would be better - real bioluminescence is blue-green - and CLAUDE.md already
    # records their stock as zero. One line changes them back the day a cold frog exists here.
    "photo": "ochre_froglight",        # flank rows and the dorsal ridge
    "organ": "ochre_froglight",        # eye light organs, arm tips, tentacle clubs
}


# --------------------------------------------------------------------------- geometry


def _bez(p, t):
    """Cubic Bezier through four control points, as numpy vectors."""
    u = 1.0 - t
    return (u * u * u) * p[0] + (3 * u * u * t) * p[1] + (3 * u * t * t) * p[2] + (t * t * t) * p[3]


def _sample(pts, n):
    """Points along a cubic, densely enough that consecutive balls always overlap.

    A path stepped coarsely is a row of DIAGONAL neighbours, which is not connected in this
    project's own sense and has cost it a pair of ear tips, a set of ossicones and a whole
    dragonfly. The step here is well under the smallest radius any part ever uses.
    """
    return [_bez(pts, i / float(n - 1)) for i in range(n)]


def _unit(v):
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.array([0.0, 0.0, 1.0])


def _core(b, pts, blk, part) -> int:
    """A one-cell connected thread down a limb's own path, laid BEFORE the balls.

    A swept ball of radius 0.55 at the tip of an arm covers exactly one cell, and two
    consecutive centres less than a cell apart can round to cells that are DIAGONAL
    neighbours - which is not connected in this project's own sense and is what broke a pair
    of ear tips, a set of ossicones and a whole dragonfly. The first build of this animal shed
    four cells off three arm tips the same way, and the audit's own component count was the
    only thing that could see it.

    The fix is prevention rather than a stitch: walk the path's rounded cells and, wherever
    consecutive ones differ on more than one axis, fill the corner one axis at a time. A
    corner fill that mends one axis mends one axis, so it walks all three.
    """
    n, prev = 0, None
    for q in pts:
        cell = (int(round(q[0])), int(round(q[1])), int(round(q[2])))
        if cell == prev:
            continue
        if prev is None:
            n += b_put(b, cell[0], cell[1], cell[2], blk, part)
        else:
            x, y, z = prev
            for ax, tgt in enumerate(cell):
                while (x, y, z)[ax] != tgt:
                    d = 1 if tgt > (x, y, z)[ax] else -1
                    x, y, z = (x + d, y, z) if ax == 0 else (x, y + d, z) if ax == 1 else (x, y, z + d)
                    n += b_put(b, x, y, z, blk, part)
        prev = cell
    return n


class _Body:
    """The canvas, plus the one rule every cell in this design has to obey.

    `put` is the only way anything is written, so the keep-out cannot be forgotten by a part
    added later - which is how the Lost Plateau stood a timber set's post on a live rail three
    separate times, each of them caught by a walk rather than by any audit.
    """

    def __init__(self, c: Canvas, at, keep_out):
        self.c = c
        self.at = at
        self.ko = keep_out
        self.part = np.zeros_like(c.ids, dtype=np.uint8)
        self.refused = 0
        self.closest = float("inf")

    def allowed(self, x, z) -> bool:
        if not self.ko:
            return True
        d = math.hypot(self.at[0] + x - self.ko[0], self.at[2] + z - self.ko[1])
        if d < self.ko[2]:
            return False
        if d < self.closest:
            self.closest = d
        return True

    def put(self, x, y, z, blk, part) -> bool:
        x, y, z = int(round(x)), int(round(y)), int(round(z))
        if not self.c.inb(x, y, z):
            return False
        if not self.allowed(x, z):
            self.refused += 1
            return False
        self.c.ids[y, z, x] = blk
        self.part[y, z, x] = part
        return True

    def paint(self, x, y, z, blk, part=None) -> bool:
        """Recolour a cell that already exists, and NEVER create one.

        A paint over air is a feature that silently did not happen, and this repo has shipped
        that four times - the frog's nostrils, its foot lamps, the ladybird's seven spot caps
        and the axolotl's gills all audited clean while not existing.
        """
        x, y, z = int(round(x)), int(round(y)), int(round(z))
        if not self.c.inb(x, y, z) or self.c.ids[y, z, x] == 0:
            return False
        self.c.ids[y, z, x] = blk
        if part is not None:
            self.part[y, z, x] = part
        return True

    def solid(self, x, y, z) -> bool:
        return self.c.solid(int(round(x)), int(round(y)), int(round(z)))

    def ball(self, p, r, blk, part) -> int:
        cx, cy, cz = float(p[0]), float(p[1]), float(p[2])
        n = 0
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            dy2 = (y + 0.5 - cy) ** 2
            for z in range(int(cz - r - 1), int(cz + r + 2)):
                dz2 = (z + 0.5 - cz) ** 2
                if dy2 + dz2 > r * r:
                    continue
                for x in range(int(cx - r - 1), int(cx + r + 2)):
                    if (x + 0.5 - cx) ** 2 + dy2 + dz2 <= r * r:
                        n += b_put(self, x, y, z, blk, part)
        return n

    def surface(self, p, d, reach):
        """The outermost solid cell along a ray from an interior point, and the air past it.

        Anything clinging goes HERE and never at a computed radius. Every detached-feature bug
        in this repo is that one mistake: the mane came off as seven fragments, the ossicones
        detached, the tail floated 45 cells clear, and the axolotl's fin drifted a course.
        """
        last = None
        for i in range(1, int(reach) + 1):
            q = (p[0] + d[0] * i, p[1] + d[1] * i, p[2] + d[2] * i)
            if self.solid(*q):
                last = q
            elif last is not None:
                return last, q
        return last, None


def b_put(b, x, y, z, blk, part) -> int:
    return 1 if b.put(x, y, z, blk, part) else 0


# --------------------------------------------------------------------------- the build


def build_squid(cfg: dict, donors=None) -> Canvas:
    p = {**SQUID, **cfg}
    sc = float(p.get("scale", 1.0))
    seed = int(p.get("seed", 7))

    ML = float(p["mantle_len"]) * sc
    MR = float(p["mantle_r"]) * sc
    HL = float(p["head_len"]) * sc
    AL = float(p["arm_len"]) * sc
    TL = float(p["tent_len"]) * sc
    n_sect = float(p["sect_n"])
    up_f = float(p["tent_up"])

    # ---- the frame. The canvas is sized for the ORIENTATION the animal is actually built in.
    # The sauropod's box was always long in X, so built facing north it was clipped to 22
    # blocks of 48 - head, neck and half the tail simply refused - and the render still showed
    # a plausible small dinosaur, because the only symptom was a refusal count nobody read.
    arm_out = AL * float(p["arm_spread"]) * 1.14
    crown_up = arm_out * float(p["crown_squash"])
    fin_out = MR + float(p["fin_span"]) * sc
    half_x = int(math.ceil(max(arm_out, fin_out, TL * 0.32))) + 6
    XC = half_x                                   # INTEGER, so the mirror is exact
    SX = 2 * half_x + 1

    ZT = 3.0                                      # the mantle's point
    ZC = ZT + ML                                  # the collar
    ZA = ZC + HL                                  # the arm base
    SZ = int(ZA + max(AL * float(p["arm_reach"]) * 1.2, TL * 0.50)) + 8

    # THE FLOOR MARGIN IS DERIVED, NOT TYPED. Four arms of the crown open DOWNWARD, so the
    # canvas floor has to sit under the lowest of them - and a canvas that is one course short
    # does not raise, it silently truncates and still renders as a plausible animal.
    YC = float(p["collar_y"]) * sc
    YA = YC + float(p["head_rise"]) * sc
    floor = max(0.0, crown_up - YA + float(p["arm_r"]) * sc + 3.0)
    YT = float(p["tip_y"]) * sc + floor
    YC += floor
    YA += floor
    SY = int(max(YA + crown_up, YA + TL * up_f + float(p["club_r"]) * sc)) + 8

    c = Canvas(SX, SY, SZ, donors)
    st = c.state
    S = {k: st(p[k]) for k in ("deep", "mid", "lift", "pale", "dark", "sucker", "photo",
                               "organ")}
    at = tuple(int(v) for v in p["at"]) if p.get("at") else (0, 0, 0)
    ko = tuple(float(v) for v in p["keep_out"]) if p.get("keep_out") else None
    b = _Body(c, at, ko)
    counts: dict = {}

    def spine_y(s: float) -> float:
        """Canvas Y of the body axis at fraction `s` along the mantle, 0 at the point."""
        return YT + (YC - YT) * (max(0.0, min(1.0, s)) ** float(p["rise_pow"]))

    # every radius is a FRACTION of MR, so one number moves the animal's girth and nothing
    # else has to be kept in step with it. Anything in absolute blocks has the tail bug latent:
    # a tail hardcoded at 13 blocks was once longer than a deer's legs.
    # THE MANTLE IS WIDEST AT THE COLLAR AND TAPERS ALL THE WAY TO THE POINT. The first build
    # peaked at 0.60 of its own length and narrowed again toward the head, which is a CIGAR -
    # and the panel read it exactly that way, as a constant-depth wedge with no line in it,
    # which is the jaguar's own recorded failure. A squid's mantle is a cone whose base is the
    # mantle opening; the taper is convex rather than straight, so the outline falls away
    # rather than ruling a line.
    RKEYS = [(0.00, 0.05), (0.08, 0.30), (0.20, 0.55), (0.38, 0.75), (0.58, 0.88),
             (0.78, 0.96), (1.00, 1.00)]
    # ...and the head PINCHES behind the eyes. Without a neck the animal reads as a worm with
    # a face - the axolotl's own finding, and it is why the head starts at 0.74 of the mantle's
    # own girth. The step from 1.00 to 0.74 in one course is not a cliff to be smoothed away:
    # it IS the mantle opening, which is a hard rim on a real squid.
    HKEYS = [(0.00, 0.74), (0.20, 0.90), (0.45, 0.88), (0.75, 0.62), (1.00, 0.44)]
    AK = [(0.00, 1.00), (0.15, 0.85), (0.40, 0.62), (0.70, 0.37), (0.90, 0.21), (1.00, 0.11)]
    TK = [(0.00, 0.94), (0.20, 0.80), (0.55, 0.68), (0.85, 0.60), (1.00, 0.66)]

    def mantle_r(s):
        return MR * lerp(RKEYS, max(0.0, min(1.0, s)))[0]

    def head_r(u):
        return MR * lerp(HKEYS, max(0.0, min(1.0, u)))[0]

    def head_y(u):
        return YC + (YA - YC) * max(0.0, min(1.0, u))

    def axis_at(z):
        """The body axis and its girth at a canvas z - what the coat reads its gradient off."""
        if z <= ZC:
            s = (z - ZT) / ML
            return spine_y(s), max(1.0, mantle_r(s))
        if z <= ZA:
            u = (z - ZC) / HL
            return head_y(u), max(1.0, head_r(u))
        return YA, MR

    def sect(cx, cy, cz, r, part, blk) -> int:
        """One vertical superellipse slice across the heading.

        Drawn per INTEGER z, so consecutive slices are one apart and always overlap: the sweep
        is 6-connected by construction rather than by a stitch afterwards.
        """
        n, ri = 0, int(r) + 2
        for dy in range(-ri, ri + 1):
            fy = (abs(dy) / r) ** n_sect
            if fy > 1.0:
                continue
            for dx in range(-ri, ri + 1):
                if fy + (abs(dx) / r) ** n_sect <= 1.0:
                    n += b_put(b, cx + dx, cy + dy, cz, blk, part)
        return n

    # ---- 1. MANTLE --------------------------------------------------------------------
    n = 0
    for z in range(int(ZT), int(ZC) + 1):
        s = (z - ZT) / ML
        n += sect(XC, int(round(spine_y(s))), z, max(0.6, mantle_r(s)), P_MANTLE, S["deep"])
    counts["mantle"] = n

    # ---- 2. HEAD ----------------------------------------------------------------------
    n = 0
    for z in range(int(ZC) + 1, int(ZA) + 1):
        u = (z - ZC) / HL
        n += sect(XC, int(round(head_y(u))), z, max(0.6, head_r(u)), P_HEAD, S["deep"])
    counts["head"] = n

    # ---- 3. FINS ----------------------------------------------------------------------
    # TWO FLAT SHEETS, which is the shape this medium renders natively and half the reason a
    # squid was chosen over a whale. The trailing edge is SCALLOPED - a fin cut off square
    # reads as a shelf - and the scallop is noise on the OUTLINE and never on the interior: a
    # threshold applied per cell is what turned the lowland thicket into 191 blobs of one and
    # two cells, and it is the deck soffit's confetti in a third body.
    f0, f1 = float(p["fin_from"]), float(p["fin_to"])
    span, thick = float(p["fin_span"]) * sc, float(p["fin_thick"]) * sc
    n = 0
    for z in range(int(ZT + f0 * ML), int(ZT + f1 * ML) + 1):
        s = (z - ZT) / ML
        # CLAMPED: the loop walks integer z, so its first and last steps fall a little
        # outside the fin's own fractional span and a negative u raised to a fractional
        # power is a COMPLEX number rather than an error anybody would read.
        u = max(0.0, min(1.0, (s - f0) / (f1 - f0)))
        w = span * max(0.0, math.sin(math.pi * (u ** 0.78)))
        w *= 1.0 + 0.11 * (hash01(seed, 11, z // 5) - 0.5)      # the scallop, on the OUTLINE
        if w < 1.0:
            continue
        cy, r = int(round(spine_y(s))), mantle_r(s)
        root = max(1, int(r) - 2)
        for sgn in (1, -1):
            for k in range(root, int(r + w) + 1):
                out = (k - root) / max(1.0, w)
                if out > 1.0:
                    continue
                th = max(1.0, thick * (1.0 - 0.74 * out))
                for dy in range(-int(th), int(th) + 1):
                    n += b_put(b, XC + sgn * k, cy + dy, z, S["deep"], P_FIN)
    counts["fin"] = n

    # ---- 4. ARMS ----------------------------------------------------------------------
    # Eight, in four MIRRORED pairs about the integer centre column. The crown opens like an
    # umbrella: the third control point reaches further forward than the fourth, so the tips
    # curl outward and BACK. Arms that point straight forward read as a broom.
    # THE MIRROR PLANE IS THE CENTRE OF COLUMN XC, WHICH IS X = XC + 0.5, NOT X = XC.
    # `Canvas` tests a ball against cell CENTRES at x + 0.5, so a limb swept from `float(XC)`
    # is mirrored about the column's own EDGE - and 5,375 cells, a tenth of this animal, came
    # out different left to right. Every one of them was in the arm crown and the tentacles,
    # which are the only parts swept as balls; the mantle and the head are drawn in cell
    # indices about XC and were exact all along. A half-block, and it is invisible in every
    # render because a squid's arms are supposed to look a bit different from each other.
    base = np.array([XC + 0.5, YA, ZA])
    fwd = np.array([0.0, 0.0, 1.0])
    arm_paths = []
    n = 0
    pairs = max(2, int(p["arms"]) // 2)
    squash = float(p["crown_squash"])
    for i in range(pairs):
        a = math.pi * (0.14 + 0.72 * (i / float(pairs - 1)))    # 25 to 155 degrees off "up"
        j = hash01(seed, 3, i)      # per PAIR, so both sides get the same variation
        reach = AL * float(p["arm_reach"]) * (0.86 + 0.28 * j)
        out = AL * float(p["arm_spread"]) * (0.88 + 0.24 * (1.0 - j))
        for sgn in (1, -1):
            rad = np.array([sgn * math.sin(a), math.cos(a) * squash, 0.0])
            # the fourth point reaches LESS far forward than the third, and that is the whole
            # of what makes the crown open like an umbrella rather than point like a broom.
            # There is no downward term: a squid is neutrally buoyant and its arms do not
            # droop, and a universal droop is also what put four of them through the floor.
            ctrl = [base,
                    base + fwd * (AL * 0.42) + rad * (AL * 0.10),
                    base + fwd * (AL * 0.82) + rad * (out * 0.60),
                    base + fwd * reach + rad * out]
            pts = _sample(ctrl, 200)
            arm_paths.append((pts, rad))
            n += _core(b, pts, S["deep"], P_ARM)
            for k, q in enumerate(pts):
                r = float(p["arm_r"]) * sc * lerp(AK, k / float(len(pts) - 1))[0]
                n += b.ball(q, max(0.55, r), S["deep"], P_ARM)
    counts["arm"] = n

    # ---- 5. TENTACLES -----------------------------------------------------------------
    # The two hunting tentacles: a thin stalk and a widened CLUB. They are the nearest part of
    # the animal to the well, the brightest thing on it, and what a runner meets first.
    # S-curved, because a straight one is a pole.
    cf = float(p["club_frac"])
    tent_paths = []
    n = ncl = 0
    for sgn in (1, -1):
        rad = np.array([float(sgn), 0.0, 0.0])
        up = np.array([0.0, 1.0, 0.0])
        tb = base + np.array([sgn * MR * 0.30, -MR * 0.34, -HL * 0.06])
        ctrl = [tb,
                tb + fwd * (TL * 0.38) + rad * (TL * 0.28),
                tb + fwd * (TL * 0.62) + rad * (TL * 0.12) + up * (TL * (up_f * 0.70)),
                tb + fwd * (TL * 0.46) + rad * (TL * 0.26) + up * (TL * up_f)]
        pts = _sample(ctrl, 320)
        tent_paths.append((pts, rad))
        n += _core(b, pts, S["deep"], P_TENT)
        for k, q in enumerate(pts):
            t = k / float(len(pts) - 1)
            if t < 1.0 - cf:
                r = float(p["tent_r"]) * sc * lerp(TK, t / (1.0 - cf))[0]
                n += b.ball(q, max(0.55, r), S["deep"], P_TENT)
            else:
                # CLAMPED, for the reason the fin's own u is: 1.0 - 0.16 is not 0.84 in
                # binary, so v comes out a hair over 1, sin goes negative, and a negative
                # raised to a fractional power is a COMPLEX number - which fails as a
                # comparison error twenty lines away from the cause.
                v = max(0.0, min(1.0, (t - (1.0 - cf)) / cf))
                bulge = max(0.0, math.sin(math.pi * (0.16 + 0.84 * v)))
                r = float(p["club_r"]) * sc * max(0.34, bulge ** 0.55)
                ncl += b.ball(q, max(0.6, r), S["mid"], P_CLUB)
    counts["tentacle"] = n
    counts["club"] = ncl

    # ---- 6. FUNNEL and BEAK -----------------------------------------------------------
    # The siphon is the one piece of hardware on the animal, and it is what a squid steers
    # with - so it is also the thing that says this one is under power rather than drifting.
    n = 0
    for k in range(int(MR * 1.0)):
        t = k / max(1.0, MR)
        n += b.ball((XC + 0.5, head_y(0.40) - head_r(0.40) * 0.70 - k * 0.30,
                     ZC + HL * 0.42 + k * 0.92), max(1.0, MR * 0.30 * (1.0 - 0.45 * t)),
                    S["mid"], P_FUNNEL)
    counts["funnel"] = n
    nb = 0
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if abs(dx) + abs(dy) <= 2:
                nb += 1 if b.paint(XC + dx, YA + dy, ZA + 2, S["dark"], P_HEAD) else 0
    counts["beak"] = nb

    # ---- 7. COAT ----------------------------------------------------------------------
    # Painted on the SKIN only, and only over cells the body itself placed. The tone is a
    # value gradient from a dark dorsal to a lit ventral with chromatophore drifts crossing
    # it, and the drift is noise on a COARSE lattice with a fine term over it - per cell it is
    # static rather than pattern, which is the same mistake in a fourth body.
    skin = _skin(c.ids)
    body = skin & np.isin(b.part, (P_MANTLE, P_HEAD, P_FIN, P_ARM, P_TENT))
    ys, zs, xs = np.nonzero(body)
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        ay, r0 = axis_at(z)
        h = (y - ay) / r0                                     # -1 belly, +1 back
        dx = abs(x - XC)                                      # FOLDED, so the coat mirrors
        # THE BAND AND THE MOTTLE ARE TWO DIFFERENT DECISIONS, and the first build merged them
        # into one number. That is the confetti failure this repo has now recorded five times -
        # the deck soffit's grid, the thicket's drifts, the frog's blotches, the claim row's
        # ground - and it rendered here as black-and-red static over the whole mantle.
        #
        #   BAND is the value gradient, dark dorsal to lit ventral. A COARSE drift wobbles its
        #        boundary so it is not a stripe; nothing fine ever touches it, because noise on
        #        a boundary is an outline and noise on an interior is static.
        #   MOTTLE is the chromatophore: mangrove against red_wool, two blocks at the SAME
        #        luminance and 48 apart in RGB, so it changes the colour of the skin without
        #        breaking the form the band describes.
        band = h + 0.35 * (hash01(seed, 5, dx // 16, y // 16, z // 16) - 0.5)
        if band > 0.86:
            blk = S["dark"]                                   # a ridge line, not a black back
        elif band > -0.34:
            mottle = (0.68 * hash01(seed, 6, dx // 11, y // 11, z // 11)
                      + 0.32 * hash01(seed, 8, dx // 4, y // 4, z // 4))
            blk = S["mid"] if mottle > 0.60 else S["deep"]
        elif band > -0.76:
            blk = S["lift"]
        else:
            blk = S["pale"]
        c.ids[y, z, x] = blk
    counts["coat"] = int(body.sum())

    # ---- 8. SUCKERS -------------------------------------------------------------------
    # THE ONE DETAIL THAT SAYS TENTACLE RATHER THAN TUBE, and the reason each arm also gets a
    # pale stripe: a double row of bone discs down the INNER face draws the arm's own line, so
    # the crown reads as ten limbs rather than as a bush. Every cell is found by walking out
    # from the arm's own path to its BUILT surface - never at a computed radius, because the
    # coat pass has already changed what the surface reads as.
    ns = nstripe = 0
    step = max(2.0, float(p["sucker_every"]) * sc)
    for pts, rad in arm_paths:
        L = len(pts)
        inw = -rad
        along = 0.0
        for k in range(1, L - 1):
            q = np.array(pts[k], float)
            along += float(np.linalg.norm(q - np.array(pts[k - 1], float)))
            r = float(p["arm_r"]) * sc * lerp(AK, k / float(L - 1))[0]
            tang = _unit(np.array(pts[k + 1], float) - np.array(pts[k - 1], float))
            lat = _unit(np.cross(tang, inw))
            half = max(0, int(round(r * 0.78)))
            for o in range(-half, half + 1):
                cell, _ = b.surface(q + lat * o, (inw[0], inw[1], inw[2]), int(r) + 4)
                if cell is None:
                    continue
                nstripe += 1 if b.paint(*cell, S["pale"]) else 0
            if along < step:
                continue
            along = 0.0
            sep = max(1, int(round(r * 0.52)))
            for lane in (-sep, sep):
                w = 0 if r < 2.4 else 1
                for a in range(-w, w + 1):
                    cell, _ = b.surface(q + lat * (lane + a), (inw[0], inw[1], inw[2]),
                                        int(r) + 4)
                    if cell is not None:
                        ns += 1 if b.paint(*cell, S["sucker"]) else 0
    counts["arm_stripe"] = nstripe

    # the clubs carry the big ones, which is what a club IS
    for pts, rad in tent_paths:
        L = len(pts)
        for k in range(int(L * (1.0 - cf)), L - 1, 2):
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1)):
                cell, _ = b.surface(pts[k], d, int(float(p["club_r"]) * sc) + 4)
                if cell is None:
                    continue
                if hash01(seed, 9, abs(int(cell[0]) - XC), int(cell[1]), int(cell[2])) < 0.42:
                    ns += 1 if b.paint(*cell, S["sucker"]) else 0
    counts["sucker"] = ns

    # ---- 9. EYES ----------------------------------------------------------------------
    # A colossal squid's eye is the largest in nature, so the one feature voxels are best at
    # is also the animal's headline. Built as rings by radius on the head's OWN surface, with
    # a PROUD lens: a flat disc reads as a decal from every bearing except the one a flat
    # sheet happens to be square to, which is the axolotl's recorded eye bug.
    ER, eu = float(p["eye_r"]) * sc, float(p["eye_at"])
    ez, ey = ZC + HL * eu, head_y(eu)
    eyes = organs = 0
    for sgn in (1, -1):
        for dz in range(-int(ER) - 1, int(ER) + 2):
            for dy in range(-int(ER) - 1, int(ER) + 2):
                d = math.hypot(dz, dy) / ER
                if d > 1.0:
                    continue
                yy, zz = int(round(ey + dy)), int(round(ez + dz))
                cell, air = b.surface((XC, yy, zz), (sgn, 0, 0), int(MR) + 5)
                if cell is None:
                    continue
                blk = (S["dark"] if d <= 0.40 else S["lift"] if d <= 0.66
                       else S["sucker"] if d <= 0.86 else S["dark"])
                eyes += 1 if b.paint(*cell, blk, P_HEAD) else 0
                if air is None:
                    continue
                if d <= 0.30:
                    eyes += b_put(b, air[0], air[1], air[2], S["dark"], P_HEAD)   # the lens
                elif d > 0.86 and dy < -ER * 0.40:
                    # THE LIGHT ORGAN. A real colossal squid carries one under each eye, and
                    # two glowing crescents in a black void is the whole of what makes this
                    # animal frightening rather than merely large.
                    organs += b_put(b, air[0], air[1], air[2], S["organ"], P_HEAD)
    counts["eye"] = eyes
    counts["eye_organ"] = organs

    # ---- 10. PHOTOPHORES --------------------------------------------------------------
    # The only light in the void. Three rows down the body - the dorsal ridge and both flanks
    # - and a lamp every few blocks along every arm and tentacle. Set INTO the skin rather
    # than laid on it, which is the frog's rule and the exact opposite of what a night sweep
    # does to a sculpture: `isthmus._delight` once drove 1,138 froglights into creatures that
    # had not asked for them. Here they ARE the creature.
    every = max(3.0, float(p["photo_every"]) * sc)
    lamps = 0
    z = int(ZT + ML * 0.10)
    while z <= ZA - 2:
        cy, _ = axis_at(z)
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
            cell, _ = b.surface((XC, cy, z), d, int(fin_out) + 6)
            if cell is not None:
                lamps += 1 if b.paint(*cell, S["photo"]) else 0
        z += int(every)
    for pts, rad in arm_paths + tent_paths:
        L = len(pts)
        stride = max(4, int(L * every / max(AL, TL)))
        for k in range(int(L * 0.16), L - 2, stride):
            cell, _ = b.surface(pts[k], (rad[0], rad[1], 0.0), 10)
            if cell is not None:
                lamps += 1 if b.paint(*cell, S["organ"]) else 0
    counts["photophore"] = lamps

    # NO LICHEN, AND THAT IS A REVERSAL. A fine speckle of `glow_lichen` over the skin went in
    # for light 7 and a little texture, and a close render settled it: 1,443 face-attached
    # cells evenly spread over a live animal read as GREY POX, which is this repo's confetti
    # rule arriving in a sixth body - static, not pattern. Two other things were wrong with it
    # and neither is about density. **A live animal does not have lichen growing on it** - that
    # is a thing that happens to a statue, and this one is swimming. And `render3d` draws a
    # lichen as a full opaque cube, so it is the one element on this build these sheets cannot
    # judge at all: a change nobody can look at is how the axolotl's head happened.
    #
    # The 451 froglights carry the light on their own, at 15 against the lichen's 7.
    counts["lichen"] = 0

    # THE COUNTS ARE UNIQUE CELLS, NOT put() CALLS. A swept limb writes the same cell dozens of
    # times, so the first version of this reported 251,264 arm blocks in a 128,687-block animal
    # - a number that reads as a measurement and is an artefact of how the arm was drawn.
    for nm, pid in (("mantle", P_MANTLE), ("head", P_HEAD), ("fin", P_FIN), ("arm", P_ARM),
                    ("tentacle", P_TENT), ("club", P_CLUB), ("funnel", P_FUNNEL),
                    ("lichen", P_LICHEN)):
        counts[nm] = int((b.part == pid).sum())
    counts["sucker"] = int((c.ids == S["sucker"]).sum())
    counts["photophore"] = int(((c.ids == S["photo"]) | (c.ids == S["organ"])).sum())
    counts["total"] = int((c.ids > 0).sum())

    # AND THEN ENFORCED, with the count reported. Fixing the half-block above is the real fix;
    # this is the guarantee, and it is only worth having because it COUNTS what it changed - a
    # silent enforcement would let the next arithmetic slip hide behind it for good. Anything
    # over a handful of cells means something upstream has stopped being symmetric.
    half = min(XC, c.sx - 1 - XC)
    lo = c.ids[:, :, XC - half:XC]
    hi = c.ids[:, :, XC + 1:XC + 1 + half][:, :, ::-1]
    # ...and the two halves of that count are different facts. SHAPE must be symmetric by
    # construction and is the one that catches a real fault - the half-block above showed up
    # here as 3,521 cells of it. COLOUR is decoration the enforcement legitimately owns: the
    # arm stripes and suckers are found by walking a ray from a point that can land exactly on
    # a cell BOUNDARY, and `round()` is banker's rounding, which does not mirror at a .5 tie.
    # That is this repo's own recorded trap - keep centres integer and add offsets to them -
    # and here the honest answer is to let the mirror settle it rather than to nudge the ray.
    counts["mirror_shape_fixed"] = int(((lo > 0) != (hi > 0)).sum())
    counts["mirror_paint_fixed"] = int(((lo > 0) & (hi > 0) & (lo != hi)).sum())
    c.ids[:, :, XC - half:XC] = hi

    if p.get("at"):
        c.world_origin = at
    c.meta = {
        "kind": "squid", "scale": sc, "facing": [0, 1],
        "keep_out": list(ko) if ko else None,
        "closest_to_keep_out": None if b.closest == float("inf") else round(b.closest, 1),
        "refused_by_keep_out": b.refused,
        "features_built": counts,
    }
    return c


def _skin(ids):
    """Solid cells with at least one air face - the only cells a coat may ever touch."""
    occ = ids > 0
    pad = np.pad(occ, 1, constant_values=False)
    inner = (pad[2:, 1:-1, 1:-1] & pad[:-2, 1:-1, 1:-1] & pad[1:-1, 2:, 1:-1] &
             pad[1:-1, :-2, 1:-1] & pad[1:-1, 1:-1, 2:] & pad[1:-1, 1:-1, :-2])
    return occ & ~inner


build = build_squid
DEFAULTS = SQUID
