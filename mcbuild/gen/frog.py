"""A frog, sitting - the churchyard animal for the lot east of the sanctum.

ONE CONVEX MASS WITH A PATTERN ON IT, AND THAT IS THE WHOLE LESSON. It took seven rebuilds and
the 3-D sheets to arrive at, and the record of what failed is worth more than the frog.

The first version was a LOFTED superellipse - the same machinery as the axolotl and the turtle -
and it read as a lumpy wedge, because a loft averages every part into one hill. So it was rebuilt
from BOXES, which is what the references are made of, and that was right about the head and the
eyes and wrong about everything else: box by box the animal acquired a haunch, a shoulder, a
waist and a knee, and the orbit sheet called every one of them luggage.

  a haunch and a shoulder bolted on  -> crates you could see daylight behind, four ledges a flank
  a waist dip two courses deep       -> a head crate and a rump crate with a slot between them
  the haunch raised across the back  -> a flat-topped box: a rucksack
  the knee raised at the flanks only -> a rectangle floating above the outer wall

Every one of those is a correct piece of frog anatomy. AT THIS SCALE THERE IS NO RESOLUTION FOR
ANATOMY: thirteen wide and eight courses tall, every feature is one or two cells, and a one-cell
step does not read as modelled form - it reads as the seam between two objects. What the download
corpus says about exactly this scale is that a sculpture reads when it is ONE CONVEX MASS with a
pattern on it: the ladybird, the curled cat, and Coldrobin's frog, which is one flat-fronted box.

So the geometry is a loaf that only ever falls away from the head - `col_top` is monotonic and
`test_the_mass_only_ever_falls_away_from_the_head` pins it - and EVERY FROG CUE IS CARRIED BY THE
COAT: a mouth line that turns up at the corners and runs back along the jaw, one huge pale belly
panel, two eye boxes on the crown with the iris on the front AND the outer face, dark blotches,
and feet on the ground in a brighter tone.

TWO OF THOSE WERE MISSING FOR FIVE PASSES and no geometry substituted for either. There was no
MOUTH, so head-on was a pale rectangle between two dark bars. And the eye was black on its outer
face, so it existed in exactly one view - every bearing but head-on had two dark tabs and no eye,
which is most of why the profile could not be named.

SIZE COMES FROM THE EYE. A bulge needs 3x3 and a clear cell between the pair or the two read as
one brow (the ladybird's spot spacing), so the skull cannot be under 11 wide - and the eyes
then take the animal to 13 across, which is what the measured lot will hold.

COLOUR IS THE REFERENCE'S OWN, MATCHED BY MEASUREMENT - see the palette in FROG below. The
saturated orange this carried for four passes was picked against the moss on LUMINANCE and is
most of why it never looked like the statue; the ground test is colour DISTANCE now, which the
turtle proved is what carries on this floor. And the blotches are DARK, because a real frog's
markings are dark on a lighter skin: built pale they read as bleached patches, which is wear.

IT CARRIES ITS OWN LIGHT, and that had to be measured to find out. Propagated through the
finished world, 129 of the 149 air cells over the first build's back stood at block light ZERO.
The island night pass does not see them: its classifier takes each column's TOPMOST standable
cell, and this lot lies 113 courses under the island's belly, so the frog and the whole lot are
invisible to it. Froglights go IN the skin - one in each front foot's web, and the rest set in
the middle of the back's dark drifts, because scattered on their own they came out in plan as five
bright squares in a dice-five and read as damage rather than as spots.

THE FEET ARE STAIRS, and that is the fifth foot shape. A cube toe ENDS - at a vertical face one
block high, which is a plate - and that is why four earlier arrangements read as a rake, a comb, a
plus sign and a set of random lines however the prongs were spaced. A stair TAPERS. Jack read it
straight off the reference; the taper was then invisible in every sheet here until `render3d`
learned to draw a stair as anything but a cube, which is its own note in CLAUDE.md.
"""
from __future__ import annotations

from math import atan2 as _atan2, sin as _sin

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .ruinring import _free, _surface

FROG = {
    "under": None,             # capture/composite the ground is read from - required
    "at": None,                # [x, z] the body centroid sits over - required
    "facing": [-1, 0],         # CARDINAL only: the head is straight and its faces lie on the
                               # block grid. Aimed off-axis a flat face becomes a diagonal
                               # staircase of corners - the axolotl paid three passes for that
    "base_y": None,            # the belly plane - PIN it once built, or a rescan drifts it
    "length": 17,              # nose to rump along the gaze axis
    "width": 13,               # across the eyes and the haunches, the animal's widest
    "height": 8,               # belly plane to the top of the SKULL; the eyes go above it
    "seed": 0,

    # THE STATUE'S OWN PALETTE, matched by measurement. Its body is mud brick; `mud_bricks`
    # (137,104,79) and `packed_mud` are both CURRENCY on this server, and `jungle_planks`
    # (160,115,81) is 23 RGB off the first and cheap. The saturated orange this build carried
    # before was chosen against the moss on luminance, and it is most of why it did not look
    # like the reference: the statue reads soft and warm, not fluorescent.
    #
    #   jungle_planks  160,115,81   the body            lum 119
    #   spruce_planks  115, 85,49   shade and mottle    lum  83
    #   dark_oak       67, 43,20    the eye frames      lum  43
    #   birch_planks  192,175,121   mouth and belly     lum 163
    #
    # Against moss (89,110,45) the body is 80 apart in RGB - a full hue flip, which is what the
    # turtle proved carries on this floor, not a luminance gap.
    "back": "jungle_planks",
    "flank": "spruce_planks",
    "mark": "dark_oak_planks",
    "belly": "bone_block",          # the bright core of the belly, the chin and the irises
    "belly2": "birch_planks",       # ...and a WARMER rim round it. `bone_block` alone is only
                                    # 21 apart in R-B and reads cool grey next to the body;
                                    # birch is 71, and the reference's belly is cream, not
                                    # concrete. Two tones is also a rounded belly rather than a
                                    # flat cut-out. (`chiseled_sandstone` measures better than
                                    # either and is NOT WITNESSED anywhere in this world - the
                                    # tier table calls it cheap, which is a gap in the table,
                                    # not evidence the server can supply it.)
    "iris": "yellow_wool",
    "pupil": "black_wool",
    "lamp": "ochre_froglight",
    "hand_light": "ochre_froglight",  # the hands need their own; see the feet for why
    "eye_frame": "spruce_planks",   # kept for callers; the statue's eye is a black band
    "foot": "acacia_planks",        # the feet are BRIGHTER than the body in the reference
    "stair": "jungle_stairs",       # the RELIEF. Same family as the body, so a chamfer is
                                    # geometry and never a colour - a stair in a different
                                    # tone is a stripe, not a step
    "toe_stair": "acacia_stairs",   # ...and the TOES, which are the foot's own brighter tone
    "mottle": "stripped_oak_log",   # ...and a lighter warm tan for the coat's third tone
    "plinth": "polished_blackstone_bricks",   # the base. The CHURCH'S own block - see the plinth
    "glow": 3,                 # froglights worked into the back; 0 turns them off
    "eye_gold": False,         # the mob's gold rim is SUB-BLOCK at this size - see the eyes
}


def _at(keys, t):
    """Piecewise-linear read of a keyframe table. The caller ROUNDS the result, which is what
    keeps the outline a staircase of whole blocks rather than a curve pretending to be one."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return keys[-1][1]


def _f(frac, size):
    """A fraction of one of the animal's own dimensions, as whole blocks."""
    return int(round(frac * size))


class _Frame:
    """(station along the body, offset across it) -> world x, z. The gaze is cardinal, so this
    is a rotation by a multiple of 90 degrees and nothing ever lands off the block grid."""

    def __init__(self, ax, az, facing, L):
        fx, fz = (int(v) for v in facing)
        if abs(fx) + abs(fz) != 1:
            raise ValueError(f"facing must be one cardinal unit vector, got {facing}")
        self.fx, self.fz = fx, fz
        self.sx, self.sz = -fz, fx
        self.ax, self.az, self.L = ax, az, L

    def xz(self, u, v):
        along = (self.L - 1) / 2.0 - u          # u = 0 is the NOSE, the forward-most station
        return (int(round(self.ax + self.fx * along + self.sx * v)),
                int(round(self.az + self.fz * along + self.sz * v)))


def build_frog(cfg: dict, donors=None) -> Canvas:
    p = {**FROG, **cfg}
    if not p.get("under") or not p.get("at"):
        raise ValueError("frog needs params.under and params.at")
    ctx = Ctx(p["under"])
    ax, az = (int(v) for v in p["at"])
    L, W, H = int(p["length"]), int(p["width"]), int(p["height"])
    seed = int(p["seed"])
    fr = _Frame(ax, az, p["facing"], L)

    def ground(x, z):
        g, nm = _surface(ctx, x, z)
        return g if g is not None and nm not in ("water", "ice") else None

    if p.get("base_y") is not None:
        BY = int(p["base_y"])
    else:                                       # then PIN it in the config
        gs = sorted(g for u in range(L) for v in range(-W // 2, W // 2 + 1)
                    for g in [ground(*fr.xz(u, v))] if g is not None)
        BY = gs[len(gs) // 2] + 1

    w = World()
    # `forelegs` IS BACK, and it is the point of the rebuild: upright, the animal has real arms
    # down the front corners. It was removed when the loaf swallowed them - a part that is not
    # built is not a part, and left in the dict it ships as `0` in the sidecar for ever, which
    # is the signal that once hid a frog with no arms through two passes.
    feats = {k: 0 for k in ("body", "forelegs", "toes", "plinth",
                            "eyes", "mouth", "throat", "marks", "glow", "relief")}
    cells: set[tuple[int, int, int]] = set()    # (u, v, y) - OUR OWN map. Canvas.get returns
                                                # -1 out of bounds and -1 is truthy, which has
                                                # produced a clean audit and a wrong build twice

    def put(u, v, y, name, part=None, **props):
        x, z = fr.xz(u, v)
        if not _free(ctx, x, y + BY, z) or w.has(x, y + BY, z):
            return 0
        w.put(x, y + BY, z, name, **props)
        cells.add((u, v, y))
        if part:
            feats[part] += 1
        return 1

    # WHICH WAY A STAIR LEANS. Its TALL side is its `facing` - the convention this repo settled
    # off Jack's own flight and pinned in `test_stairhead.py`, because our renderer draws both
    # directions identically. A toe tapers DOWN and FORWARD, so its tall side is the one facing
    # back toward the body: the direction of increasing u, which is the opposite of the gaze.
    _NAMES = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}
    BACK = _NAMES[(-fr.fx, -fr.fz)]

    def paint(u, v, y, name, over=None, props=None):
        """Recolour a cell that is already built - a marking, never a new block."""
        x, z = fr.xz(u, v)
        cur = w.name(x, y + BY, z)
        if cur is None or (over is not None and cur not in over):
            return 0
        w.put(x, y + BY, z, name, **(props or {}))
        return 1

    def box(u0, u1, v0, v1, y0, y1, name, part, chamfer=()):
        """A rectangular part. `chamfer` names the edge PAIRS whose shared corner cells are
        dropped, which is all the rounding a voxel animal wants: a smooth taper averages the
        parts back into one hill, which is exactly what the first build got wrong."""
        for u in range(u0, u1 + 1):
            for v in range(min(v0, v1), max(v0, v1) + 1):
                for y in range(y0, y1 + 1):
                    eu = u == u0 or u == u1
                    ev = v == min(v0, v1) or v == max(v0, v1)
                    ey = y == y0 or y == y1
                    if ("uv" in chamfer and eu and ev) or ("vy" in chamfer and ev and ey) \
                            or ("uy" in chamfer and eu and ey):
                        continue
                    put(u, v, y, name, part)

    def mass(u0, u1, v0, v1, y0, y1, name, part, front=0, rear=1, out=1, per=2):
        """A box that STEPS IN as it rises - the voxel way to round a mass.

        A plain box with a chamfered corner is still a crate, and the 3-D pass caught exactly
        that: in profile the haunch was a flat-sided rectangle with a hard vertical rear face,
        and the value panel showed it as one untouched mid-grey - the jaguar's own failure, in
        a build that passes head-on. `front`/`rear`/`out` are how many cells the course steps
        in per `per` courses at the nose end, the tail end and the outboard side.
        """
        sgn = 1 if v1 >= v0 else -1
        for y in range(y0, y1 + 1):
            k = (y - y0 + per - 1) // per
            a0, a1 = u0 + front * k, u1 - rear * k
            b0, b1 = v0, v1 - sgn * out * k
            if a0 > a1 or (sgn > 0 and b1 < b0) or (sgn < 0 and b1 > b0):
                break
            box(a0, a1, b0, b1, y, y, name, part)

    # ---------- the layout: GRAYSUN'S FROG STATUE, AND IT IS UPRIGHT ----------
    #
    # THE WHOLE ANIMAL WAS THE WRONG SHAPE, and the rule that made it so was mine.
    #
    # This file used to say, in capitals, that a sculpture at this scale must be ONE CONVEX MASS
    # with a pattern on it, because four attempts at anatomy - a bolted-on haunch, a shoulder, a
    # waist, a knee - each came out as luggage. That was measured at EIGHT COURSES of body
    # height, where every feature is one or two cells and a one-cell step is not modelled form,
    # it is the seam between two objects.
    #
    # IT IS A SCALE LAW AND IT WAS WRITTEN DOWN AS A UNIVERSAL ONE. The reference does not delete
    # the anatomy; it makes the animal TALL ENOUGH TO HOLD IT. At twenty-odd courses a head is
    # seven cells, an arm is thirteen and a haunch is seven - those are masses, not seams. Built
    # as one mass instead, this animal came out a crate three times running, which is recorded in
    # this repo twice and was called a crate by Jack a third time. The rule that keeps producing
    # a crate is the rule that is wrong.
    #
    # The lot was re-measured before this was written: 15x13 is the largest pad at roll <= 1 and
    # it carries 107 COURSES OF HEADROOM. Height is free here; the footprint is the constraint.
    #
    # The statue is a STACK, and every part of it is legible because it has the room to be:
    #
    #     eyes         two boxes on the crown, breaking the top outline, PALE with dark pupils
    #     head         wide, sitting on a shoulder that is narrower than it
    #     torso        NARROW - nine wide - because the ARMS are what fill it back out to
    #                  thirteen, and the pale belly panel is the strip of torso between them
    #     arms         real limbs down the front corners, shoulder to hand
    #     haunches     the widest part of the body, at the bottom, where the weight is
    #     feet         hands splayed forward on the ground, hind feet out at the sides
    #
    bw = _f(0.43, W)                        # 6 -> haunches and head are 13 wide
    tw = bw - 1                             # 5 -> the torso is 11, and the ARMS take its edges
    fw = bw + 1                             # 7 -> the feet are the widest thing, at 15
    uf = _f(0.31, L)                        # 4 -> the body's front face
    ub = L - 1                              # ...and its back

    # THE PROFILE, course by course, as fractions of the body's own height. Read off the
    # reference: the HEAD IS ABOUT A THIRD OF THE ANIMAL. Built at 15% - which is what a real
    # frog measures and what the first upright pass used - the thing came out a totem pole: a
    # tall plain torso with a small head on it. A statue is not a measurement of an animal.
    #
    # And the front STEPS: the head projects past the arms, the arms hang in front of the chest,
    # the chest is the recessed plane that carries the pale belly.
    #
    # AND IT IS SQUAT. Measured off the picture the head and eyes are about FORTY PER CENT of
    # the total height and the body below is wider than it is tall. Built at a third that, over
    # a long torso, the first upright pass came out as a gravestone with a frog's head on it -
    # a tall narrow box whose pale belly read as a DOOR. Upright is not the same as tall.
    #
    # The waist is a real pinch - two cells, not one - so the silhouette is an hourglass rather
    # than a column: wide haunches, a narrow chest with the arms in front of it, a wide head.
    # SEVEN BANDS, NOT FOUR. At four the body was a rectangular PRISM and the pale belly inset
    # into it read as a DOORWAY - the whole animal a gravestone with a frog's head. A living
    # mass swells and pinches: the base draws in, the haunches are the widest thing, the waist
    # pinches, the shoulders flare, the head is wide again.
    #                t0    t1     hw       front   back
    #
    # AND THE BODY BELOW THE HEAD IS WIDER THAN IT IS TALL. That is the measurement that finally
    # broke the gravestone: at seventeen courses on a thirteen-wide animal the torso was a
    # COLUMN however it was tapered or coloured, and a pale panel on a column is a door. On the
    # reference the body is about 130 units tall against 155 wide, and the head sits almost
    # straight on the haunches - there is no torso to speak of.
    #                t0    t1     hw       front   back
    #
    # AND THE BACK FALLS AWAY. Given the head the same depth as the body, the whole rear was one
    # flat wall from crown to ground and the PROFILE read as a boot - a tall front with a slab
    # behind it and no frog anywhere. A sitting frog is head forward and HIGH, rump back and
    # LOW; the head is the shortest band front-to-back and the haunches are the deepest.
    #                t0    t1     hw       front   back
    PROFILE = ((0.00, 0.10, bw - 1,  uf,     ub - 1),    # the base draws in
               (0.10, 0.30, bw,      uf,     ub),        # haunches - deepest, and the widest
               (0.30, 0.44, bw - 1,  uf,     ub - 1),
               (0.44, 0.55, bw - 2,  uf,     ub - 3),    # the waist: narrow, and the back
               (0.55, 0.62, bw - 1,  uf - 1, ub - 4),    # draws in behind the shoulder
               (0.62, 0.90, bw,      uf - 2, ub - 4),    # the head, wide, forward and SHORT
               (0.90, 1.01, bw - 1,  uf - 2, ub - 5))    # ...and its crown draws in, so
                                                         # the relief pass has a step to
                                                         # work: without one the head was
                                                         # a flat slab and the flattest
                                                         # thing left on the animal

    def _prof(y):
        t = y / max(1, H)
        for (t0, t1, hw, u0, u1) in PROFILE:
            if t0 <= t < t1:
                return hw, u0, u1
        return PROFILE[-1][2:]

    # 1. THE MASS, course by course. The corners are cut; that is all the rounding a voxel mass
    #    takes, and any more of it terraces.
    for y in range(0, H + 1):
        hw, u0, u1 = _prof(y)
        for u in range(u0, u1 + 1):
            for v in range(-hw, hw + 1):
                if abs(v) == hw and (u == u0 or u == u1):
                    continue                          # the vertical arrises
                put(u, v, y, p["back"], "body")

    # 2. THE ARMS - real limbs, hanging IN FRONT of the chest rather than out at its sides.
    #
    #    That is the correction that made them work. Set beside the body they are swallowed by
    #    the haunches, which are wider than they are - the first upright pass had arms visible
    #    over six courses out of twenty-four. In front they read their whole length, they cast a
    #    shadow onto the chest, and they carry the eye down to the hands. It is also what the
    #    reference does: you can see daylight between the arm and the body's own flank.
    #
    #    They are what the loaf could never carry: at eight courses an arm is two cells and
    #    reads as a lump. Here it is fourteen.
    # ONE COLUMN WIDE, AND THEY FOLLOW THE BODY. Two wide at a fixed offset they filled
    # the waist back out and HID the pinch - the body read as a straight-sided box
    # because its own outline was covered by its arms.
    aw0, aw1 = bw - 2, bw - 2
    for s in (1, -1):
        for y in range(0, int(round(0.58 * H)) + 1):   # TO THE GROUND: cut off a
            hw = _prof(y)[0]                           # course above it, the hands
            for v in range(min(aw0, hw - 1), hw):      # had nothing to hang on and
                put(uf - 1, s * v, y, p["flank"], "forelegs")   # shipped as two strays

    # 3. THE HANDS - splayed on the ground in front, in a brighter tone, three toes a clear cell
    #    apart with a stair at each tip so the toe TAPERS rather than ending at a wall.
    #
    #    A HAND IS MOSTLY AIR. Twenty solid cells apiece is a boot with claws; the reference's
    #    are a flat wrist one course deep and thin toes with a gap between them. The gaps are the
    #    feature, exactly as they are on the eye pair and the ladybird's spots.
    for s in (1, -1):
        pv = (aw0 + aw1) // 2                                    # under the arm it belongs to
        for dv in range(-2, 3):                                  # the wrist: ONE row, one course
            put(uf - 2, s * (pv + dv), 0, p["foot"], "toes")
        for dv in (-2, 0, 2):                                    # three toes, a clear cell apart
            put(uf - 3, s * (pv + dv), 0, p["foot"], "toes")
            put(uf - 4, s * (pv + dv), 0, p["toe_stair"], "toes",
                facing=BACK, half="bottom")
        for y in (0, 1):                                         # ...and an ANKLE, so the arm
            put(uf - 2, s * (pv + 1), y, p["flank"], "forelegs")  # meets the hand instead of
                                                                  # standing on it
        # THE LOW LIGHT GOES ON THE HOCK, NOT IN THE HAND. The hands do need lighting - the
        # body's lamps are high on the back and light does not turn corners, and with none at
        # all the air over them measures block light ZERO. But a cream froglight set in an
        # acacia wrist is a pale CHIP, and at the bottom of the animal it was the loudest thing
        # on it: two bright squares where the toes should read. On the haunch's outer face, a
        # course off the ground, it is a lit spot on a flank - it reaches the hand round the
        # corner (light floods air; it needs no line of sight) and lights the hind foot on the
        # way. There is no cheaper way round the colour: `shroomlight` measures 95 RGB from the
        # foot and `glowstone` 53, and both are EXPENSIVE on this economy.
        if p.get("hand_lamp", True):
            feats["glow"] += paint(uf + 4, s * (bw - 1), 1, p["hand_light"],
                                   over=(p["back"], p["flank"], p["mottle"]))

    # 4. THE HIND FEET - at the sides, BEHIND the hands, tucked under the haunch's overhang.
    #
    #    THEY MUST NOT MEET THE HANDS. Run forward to the same stations as the front feet they
    #    merge with them round the corner into ONE L-SHAPED ORANGE PLATE, and the animal reads
    #    as standing on a plinth rather than on four feet. The gap is in DEPTH, not in width:
    #    the hands are in front of the body's face, the hind feet start behind it, and the arm's
    #    own station is the clear course between them.
    for s in (1, -1):
        hb = uf + 3
        for u in range(hb, hb + 4):                              # the sole, tucked under
            for dv in (0, 1):
                put(u, s * (fw - 1 + dv), 0, p["foot"], "toes")
        for du, dv in ((1, 0), (1, 1), (2, 0)):                  # ...and it splays forward
            put(hb - du, s * (fw - 1 + dv), 0, p["foot"], "toes")
        put(hb - 3, s * (fw - 1), 0, p["toe_stair"], "toes", facing=BACK, half="bottom")

    # 5. THE EYE BOXES - on the crown, at the front, breaking the top outline.
    #
    #    PALE WITH A DARK PUPIL, which is the reference and is the opposite of what this build
    #    carried. Its eyes were a dark band with gold set in it: at any distance that reads as
    #    sunglasses, and it goes black at the 1/6 thumbnail. On the statue the eyes are the
    #    BRIGHTEST thing on the animal, which is why you can name it across a room.
    ew = _f(0.13, W)                                    # inner edge of the pair
    eye_u = uf - 2                                      # flush with the head's face
    for s in (1, -1):
        for u in range(eye_u, eye_u + 3):
            for v in range(ew, ew + 4):
                put(u, s * v, H + 3, p["back"], "eyes")             # the lid
                put(u, s * v, H + 2, p["pupil"], "eyes")
                put(u, s * v, H + 1, p["pupil"], "eyes")            # ...on a dark box
        for dv in range(0, 4):                                      # the face of it: a pale
            v = ew + dv                                             # iris in a dark rim...
            for y, blk in ((H + 2, p["belly"]), (H + 1, p["belly"])):
                if dv in (0, 3):
                    continue
                x, z = fr.xz(eye_u, s * v)
                w.put(x, y + BY, z, blk)
                cells.add((eye_u, s * v, y))
        x, z = fr.xz(eye_u, s * (ew + 2))                           # ...and the PUPIL in it
        w.put(x, H + 1 + BY, z, p["pupil"])
        x, z = fr.xz(eye_u + 1, s * (ew + 3))                       # one on the outer face, or
        w.put(x, H + 2 + BY, z, p["belly"])                         # the eye exists in ONE view
        cells.add((eye_u + 1, s * (ew + 3), H + 2))
        feats["eyes"] += 1

    # 6. THE BELLY - the strip of torso between the arms, ground up, which is what makes the
    #    front of the reference read as a face over a chest rather than as a painted wall.
    bt = int(round(0.58 * H))
    #
    #    IT IS AN OVAL, AND THAT IS THE FIX FOR THE DOORWAY. A pale rectangle with hard vertical
    #    edges, inset in a darker frame, is a DOOR - it does not matter how well the animal above
    #    it is proportioned, and four passes of retuning the body could not shift the reading.
    #    A belly is a lens: widest at the middle, closing top and bottom. The straight line is
    #    what says architecture; the curve is what says creature.
    for y in range(1, bt + 1):
        hw = _prof(y)[0]
        t = (y - 1) / max(1, bt - 1)
        half = max(1, int(round((hw - 1) * (1.0 - abs(t - 0.42) * 1.15))))
        for v in range(-half, half + 1):
            # TWO TONES: the bright core, and a warmer rim one cell in from the oval's edge.
            # One flat tone over eighty cells is the flattest surface on the animal, and the
            # rim is what stops the oval reading as a cut-out pasted onto the chest.
            blk = p["belly"] if abs(v) < half and 1 < y < bt else p["belly2"]
            feats["throat"] += paint(uf, v, y, blk, over=(p["back"],))

    # 7. THE MOUTH - a dark line across the head's front, TURNING UP at the ends, and carrying
    #    on round the jaw. Without it the front is a pale rectangle between two dark bars, and
    #    the review sheet said so at every distance.
    hy = int(round(0.78 * H))
    hf = uf - 2                                         # the head's own front plane
    for v in range(-bw + 3, bw - 2):
        feats["mouth"] += paint(hf, v, hy, p["mark"], over=(p["back"], p["belly"]))
    for v in (bw - 2, -bw + 2):
        feats["mouth"] += paint(hf, v, hy + 1, p["mark"], over=(p["back"], p["belly"]))
    for s in (1, -1):                                   # ...and round the jaw
        for du in range(1, 4):
            feats["mouth"] += paint(hf + du, s * bw, hy + 1, p["mark"], over=(p["back"],))
    for v in range(-bw + 3, bw - 2):                    # a pale chin under it
        for y in range(hy - 3, hy):
            feats["throat"] += paint(hf, v, y, p["belly"], over=(p["back"],))

    # 8. THE COAT - DRIFTS ON THE SKIN, never confetti and never the interior. Measured against
    #    the download corpus the one difference between their sculpture and ours is the accent
    #    tail: theirs carry 18.5% of their cells beyond their top three blocks and ours carried
    #    6. Blobs with a LOBED radius - the noise belongs on the drift's BOUNDARY, never on the
    #    cell - and DARK, because a frog's markings are dark on a lighter skin; built pale they
    #    read as bleached patches, which is wear.
    skin = {c for c in cells
            if not all((c[0] + a, c[1] + b, c[2] + d) in cells
                       for a, b, d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                       (0, -1, 0), (0, 0, 1), (0, 0, -1)))}
    #
    #    AND THEY ARE MIRRORED. Placed independently per side - twelve blobs, each with its own
    #    signed offset - the dark drifts land in different places left and right, and Jack read
    #    the result straight off: *"one side is more lumpy than the other."* He is right, and it
    #    is not a lighting artefact: a dark patch reads as a RECESS, so a coat that is not
    #    mirrored is a body that looks dented on one side. 104 of 1,615 cells differed across
    #    the sagittal plane.
    #
    #    A real frog's blotches are not symmetric. A STATUE of one is, and the reference is; the
    #    rubric has a whole dimension for this and allows asymmetry only where it was
    #    deliberately asked for. Nothing here asked for it.
    for (uu, vf, yf, tone, rad, phase) in (
            (0.50, 1.00, 0.14, "dark", 2.6, 0.4), (0.30, 1.00, 0.22, "dark", 2.3, 2.1),
            (0.80, 1.00, 0.34, "dark", 2.4, 1.2), (0.60, 1.00, 0.46, "dark", 2.6, 3.4),
            (0.35, 1.00, 0.58, "dark", 2.4, 0.9), (0.75, 1.00, 0.66, "dark", 2.2, 4.7),
            (0.55, 1.00, 0.80, "dark", 2.3, 2.8), (0.30, 1.00, 0.86, "dark", 2.2, 1.7),
            (0.95, 0.45, 0.30, "light", 2.2, 5.2), (0.95, 0.50, 0.62, "dark", 2.4, 0.2),
            (0.95, 0.00, 0.88, "dark", 2.1, 3.9), (0.20, 0.85, 0.10, "dark", 2.0, 2.4)):
        blk = p["flank"] if tone == "dark" else p["mottle"]
        pr = {"axis": "y"} if "_log" in blk else None
        for sgn in ((1, -1) if vf else (1,)):
            cu, cv, cy = uf + uu * (ub - uf), sgn * vf * bw, yf * H
            for (u, v, y) in skin:
                if y > H or u < uf - 1:        # not the eye boxes, not the face, not the feet
                    continue
                du, dv, dy = u - cu, v - cv, y - cy
                d = (du * du + dv * dv + dy * dy) ** 0.5
                if d > rad * 1.6:
                    continue
                r = rad * (1.0 + 0.30 * _sin(3.0 * _atan2(dy, du) + phase))
                if d <= r:
                    feats["marks"] += paint(u, v, y, blk, over=(p["back"],), props=pr)

    # 9. ITS OWN LIGHT. The island night pass cannot see this lot - its classifier takes each
    #    column's topmost standable cell and the lot lies over a hundred courses under the
    #    island's belly - so the animal lights itself. Each lamp is set in the middle of a dark
    #    drift: scattered on their own they read in plan as bright squares, which is damage.
    tops: dict[tuple[int, int], int] = {}
    for (u, v, y) in cells:
        tops[(u, v)] = max(tops.get((u, v), -99), y)
    # PAIRS OR THE CENTRE LINE, NEVER A LONE SIDE. With `glow: 5` the old table's fifth entry
    # was a single lamp at +0.75 whose partner was never reached - one bright cell on one flank,
    # which is the loudest kind of asymmetry there is.
    SPOTS = ((0.30, 0.0), (0.60, 0.55), (0.60, -0.55), (0.85, 0.0),
             (0.45, 0.75), (0.45, -0.75), (0.95, 0.0))
    for tu, tv in SPOTS[:int(p.get("glow") or 0)]:
        u = uf + _f(tu, ub - uf)
        for dv in (0, 1, -1, 2, -2):
            v = int(round(tv * bw)) + dv
            if tops.get((u, v), 0) > H:
                continue                       # NEVER ON AN EYE BOX: its lid is the body's own
            if (u, v) in tops and paint(u, v, tops[(u, v)], p["lamp"],
                                        over=(p["back"], p["flank"], p["mark"],
                                              p["mottle"])):
                feats["glow"] += 1
                break

    # 10. THE RELIEF - EVERY STEP IN THE MASS GETS A STAIR WORKED INTO IT.
    #
    #     Measured against the download corpus this is the last big gap and it is not close:
    #     their sculpture runs about 17% detail blocks and this animal ran 0.5%. Every plane
    #     here was a flat field of one block meeting the next at a hard right angle, which is
    #     what makes a voxel mass read as a CRATE however well it is proportioned - and it is
    #     the reason the reference looks like carved stone and ours looked like a box.
    #
    #     The rule is general and needs no hand-placed cells: wherever a course steps IN, the
    #     shelf it leaves gets a stair leaning into the wall above it, and wherever it steps
    #     OUT, the overhang gets an upside-down stair tucked under it. Every hard ledge becomes
    #     a cove. `shell.py` has done this for years and was never pointed at an animal.
    #
    #     ONLY THE SKIN, and only single steps. The face, the belly, the eyes and the feet are
    #     drawn features and a stair through one of them is a hole in a drawing; and a stair
    #     cut into a two-course jump leaves a gap rather than a chamfer.
    fxx, fzz, sxx, szz = fr.fx, fr.fz, fr.sx, fr.sz
    _CARD = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}

    def _face(du, dv):
        dx, dz = (-fxx * du + sxx * dv, -fzz * du + szz * dv)
        return _CARD[(dx, dz)]

    SKIN = (p["back"], p["flank"], p["mottle"])
    solid = set(cells)
    shelf = []
    for (u, v, y) in cells:
        if y < 1 or y >= H:                       # not the ground course, not the crown
            continue
        x, z = fr.xz(u, v)
        if w.name(x, y + BY, z) not in SKIN:
            continue
        up, dn = (u, v, y + 1) in solid, (u, v, y - 1) in solid
        if up == dn:                              # buried, or a free-standing cell: leave it
            continue
        want = y + 1 if not up else y - 1
        half = "bottom" if not up else "top"
        for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (u + du, v + dv, want) in solid and (u + du, v + dv, y) in solid:
                shelf.append((u, v, y, _face(du, dv), half))
                break
    for (u, v, y, facing, half) in shelf:
        x, z = fr.xz(u, v)
        w.put(x, y + BY, z, p["stair"], facing=facing, half=half)
        feats["relief"] = feats.get("relief", 0) + 1

    # 10. THE PLINTH - a LEVEL base the statue stands on, which meets the sloping ground the
    #     way a foundation does.
    #
    #     THIS REPLACES THE SKIRT, AND THE SKIRT IS WHY THE ANIMAL LOOKED LOPSIDED. It filled
    #     each ground column down to its own turf in the body's own dark flank block, and the
    #     ground here drops two courses to one side - so ALL 34 of its columns were on one
    #     flank. Measured: 34 of 34. Jack read it off the render as one side being lumpier, and
    #     it was not the coat and not the mass, it was a dark fringe hanging off one set of feet.
    #
    #     A skirt cannot be symmetric on sloping ground: `put` refuses a cell the terrain owns,
    #     so the high side cannot be given the fill the low side needs, and the only way to
    #     equalise DOWNWARD is to leave the low side floating. The way out is UPWARD - seat the
    #     animal a course clear of the highest ground under it (`base_y` = max + 2) so there is
    #     a full course of air under every column, and fill that as a deliberate base. The
    #     plinth's TOP is then level everywhere and the ANIMAL is perfectly symmetric; only its
    #     underside follows the slope, which is what a foundation is supposed to do.
    #
    #     AND IT IS INVISIBLE: each column continues its OWN material down. Built as a base in
    #     the church's own blackstone it put a black post under every separate toe and the
    #     animal looked like it was wearing boots - a plinth that follows the outline of a
    #     splayed foot is not a plinth, it is a shadow. Matched to what it carries, the fill
    #     reads as the toe REACHING the ground, which is what it is.
    for (u, v) in {(u, v) for (u, v, y) in cells if y == 0}:
        x, z = fr.xz(u, v)
        g = ground(x, z)
        if g is None:
            continue
        top = w.name(x, BY, z)
        under = p["foot"] if top in (p["foot"], p["toe_stair"], p["hand_light"]) else p["back"]
        for y in range(g + 1, BY):
            if _free(ctx, x, y, z) and not w.has(x, y, z):
                w.put(x, y, z, under)
                feats["plinth"] += 1

    # ---- SYMMETRY SWEEP. The animal is symmetric BY CONSTRUCTION - every part is built for
    # `s in (1, -1)` and every span is centred - and it still came out lopsided, because
    # construction is not the only thing that decides what gets placed. `put` refuses a cell the
    # TERRAIN owns, and this lot rolls a course or two, so a foot cell can exist on one side and
    # not the other. Measured on the finished build that was one cell; it only takes one.
    #
    # So the mirror is ENFORCED rather than assumed: above the belly plane, a cell whose mirror
    # is missing is dropped, and where the two sides disagree about the block, the +v side wins.
    # Dropping rather than adding is the only safe direction - the missing cell is missing
    # because something real is already there.
    #
    # THE SKIRT IS EXEMPT, and must be: it fills each column down to its OWN ground, and the
    # ground is not symmetric. Mirroring it would leave the animal hovering over the dip.
    lo, hi = {}, {}
    for (x, y, z), blkname in list(w.cells.items()):
        if y < BY:
            continue                       # the skirt follows the ground, not the animal
        along = fr.fx * (x - ax) + fr.fz * (z - az)
        across = fr.sx * (x - ax) + fr.sz * (z - az)
        (lo if across < 0 else hi)[(along, abs(across), y)] = (x, y, z)
    # A FACING MIRRORS, IT DOES NOT COPY. Written the obvious way this pass assigned the +v
    # cell's STATE verbatim to its twin, and 60 of the 134 stairs came out facing the same way
    # on both sides - a chamfer leaning out of the wall on one flank and into it on the other.
    # The renderer had only just learned to draw a stair as anything but a cube, so this would
    # have been invisible here a day ago and wrong in game for ever. Only the ACROSS axis flips:
    # a stair leaning fore or aft leans the same way on both sides.
    _NS = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}
    _FLIP = {_NS[(fr.sx, fr.sz)]: _NS[(-fr.sx, -fr.sz)],
             _NS[(-fr.sx, -fr.sz)]: _NS[(fr.sx, fr.sz)]}

    def _mirror(v):
        name, props = v
        f = props.get("facing")
        return (name, {**props, "facing": _FLIP[f]}) if f in _FLIP else v

    for key, cell in list(hi.items()):
        if key[1] == 0:
            continue
        twin = lo.get(key)
        if twin is None:
            w.cells.pop(cell, None)
        else:
            w.cells[twin] = _mirror(w.cells[cell])
    for key, cell in list(lo.items()):
        if key[1] and key not in hi:
            w.cells.pop(cell, None)

    # ---- ORPHAN SWEEP. The ground wins where it rises into the animal: `put` refuses a cell
    # the terrain already owns, and a neighbour that was relying on it is then left standing
    # alone. Dropped to a fixpoint; for an ANIMAL a cell attached only to the ground is an
    # orphan whether or not it happens to be sitting on rock.
    while True:
        gone = []
        for (x, y, z) in list(w.cells):
            near = [(x+1, y, z), (x-1, y, z), (x, y+1, z), (x, y-1, z), (x, y, z+1), (x, y, z-1)]
            if not any(w.has(*n) for n in near):
                gone.append((x, y, z))
        if not gone:
            break
        for k in gone:
            w.cells.pop(k, None)

    # NO `profile_view` HERE ON PURPOSE. panel.py derives it from the facing - an animal
    # looking along x shows its profile to a viewer looking along z - and stating "side"
    # overrides that with the head-on view, which is the one view a profile must not be.
    return w.canvas({"kind": "frog", "facing": [int(v) for v in p["facing"]], "base_y": BY,
                     "features_built": feats, "dig": []})
