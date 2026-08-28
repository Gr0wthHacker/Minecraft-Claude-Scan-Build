"""A frog, sitting - the churchyard animal for the lot east of the sanctum.

BUILT FROM BOXES, AND THAT IS THE WHOLE LESSON. The first version was a lofted superellipse -
the same machinery as the axolotl and the turtle - and Jack said it did not read as a frog. It
did not. Three references settled why: the Minecraft frog mob, a frog-shaped house, and an
outside builder's voxel frog. NOT ONE OF THEM IS A SMOOTH MASS. All three are assembled
rectangular parts - a flat-topped head box, a lower body box, blocky haunches, splayed feet
with separate toes - and all three read instantly.

That is the void tower's rule said again for a creature: what makes voxels legible is
REGULARITY AND SEPARATION, not smoothing. A lofted dome averages every part into one hill, and
a hill is what the panel could not name. The parts here are boxes with air between them, and
the air does as much work as the blocks: under the chin, between the arms, between the knee
and the back.

AND THE PROPORTIONS ARE THE MOB'S, NOT THE ANIMAL'S. The naming test is "would a stranger say
frog", and on a Minecraft server the stranger's reference is the mob: a HEAD that is nearly
half the length, eyes bulging off the top of it past the outline, a small low body behind, a
pale throat, feet that splay. A correctly-proportioned real frog reads as a toad; this reads as
the thing people have seen a thousand times.

SIZE COMES FROM THE EYE. A bulge needs 3x3 and a clear cell between the pair or the two read as
one brow (the ladybird's spot spacing), so the skull cannot be under 11 wide - and the eyes
then take the animal to 13 across, which is what the measured lot will hold.

COLOUR AGAINST THE GROUND, MEASURED. The moss floor is (89,110,45): a green frog is the
green-turtle mistake, invisible on its own ground. This is the TEMPERATE (orange) frog - a full
hue flip off the moss, three tones of one hue (the flamingo's rule): orange wool (241,118,20)
over acacia planks (168,90,50) over brown wool (114,72,41), with a pale birch throat, a gold
iris and a black pupil. All cheap, all 1.19, none of it currency.

IT CARRIES ITS OWN LIGHT, and that had to be measured to find out. Propagated through the
finished world, 129 of the 149 air cells over the first build's back stood at block light ZERO.
The island night pass does not see them: its classifier takes each column's TOPMOST standable
cell, and this lot lies 113 courses under the island's belly, so the frog and the whole lot are
invisible to it. Froglights go IN the skin - three down the back, one in each hind foot, which
is where they have to be, because the back lamps cannot reach round the body to the toes.
"""
from __future__ import annotations

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
    "belly": "birch_planks",
    "iris": "yellow_wool",
    "pupil": "black_wool",
    "lamp": "ochre_froglight",
    "eye_frame": "spruce_planks",   # kept for callers; the statue's eye is a black band
    "foot": "acacia_planks",        # the feet are BRIGHTER than the body in the reference
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
    feats = {k: 0 for k in ("body", "haunch", "forelegs", "toes", "skirt",
                            "eyes", "mouth", "throat", "marks", "glow")}
    cells: set[tuple[int, int, int]] = set()    # (u, v, y) - OUR OWN map. Canvas.get returns
                                                # -1 out of bounds and -1 is truthy, which has
                                                # produced a clean audit and a wrong build twice

    def put(u, v, y, name, part=None):
        x, z = fr.xz(u, v)
        if not _free(ctx, x, y + BY, z) or w.has(x, y + BY, z):
            return 0
        w.put(x, y + BY, z, name)
        cells.add((u, v, y))
        if part:
            feats[part] += 1
        return 1

    def paint(u, v, y, name, over=None):
        """Recolour a cell that is already built - a marking, never a new block."""
        x, z = fr.xz(u, v)
        cur = w.name(x, y + BY, z)
        if cur is None or (over is not None and cur not in over):
            return 0
        w.put(x, y + BY, z, name)
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

    # ---------- the layout: COLDROBIN'S FROG, READ OFF THE PICTURE ----------
    #
    # Jack, five times: not like the reference. He was right every time, and the reason is that
    # I kept refining MY frog with the reference's features bolted on instead of reading how the
    # reference is BUILT. His last picture is unambiguous, so this is that construction:
    #
    #   * ONE BIG BOX for the body, flat-fronted, with stepped haunches behind.
    #   * THE EYES ARE SEPARATE BOXES SITTING ON TOP OF IT. Each has a flat LID in the body's
    #     own colour, and its FRONT FACE carries a BLACK BAND with a single YELLOW block at the
    #     inner end. That is the whole eye. Not a bright square in a dark ring - which is what I
    #     built four times over, and which is why no amount of resizing or recolouring helped.
    #   * ONE HUGE PALE PANEL for the mouth and belly together, not two bands, with a notch of
    #     body colour cut into the top middle of it - the upper lip.
    #   * FLAT FEET ON THE GROUND in a BRIGHTER tone than the body, splayed forward with three
    #     toes, standing clear of the mass.
    #
    # `length` is the depth, `height` the body's own height; the eye boxes stand above it.
    bw = _f(0.42, W)                           # the body's half-width
    toe = _f(0.28, L)                          # how far the feet reach in front of the face
    face = toe                                 # ...so the flat front face starts here
    depth = L - 1 - face

    # 1. THE BODY - one box, corners stepped in at the top and the back so it is not a crate
    for y in range(0, H + 1):
        # THE CROWN DOES NOT DRAW IN. It used to, for rounding, and it left the outer half of
        # each eye box standing over air - 26 of 46 lid cells with nothing under them. The eye
        # boxes are the thing that sits on the crown, so the crown is the one place this mass
        # stays square; the rounding it needs is at the back corners, which it has.
        pull = 0
        for u in range(face, face + depth + 1):
            for v in range(-bw + pull, bw - pull + 1):
                deep = u >= face + depth - 1
                if deep and abs(v) >= bw - pull - 1:
                    continue                   # rounded back corners
                put(u, v, y, p["back"], "body")

    # 2. THE HAUNCH - ONE mass down each flank that steps down toward the rump, FLUSH with the
    #    body rather than standing off it. Built as two separate blocks of different widths it
    #    read from behind as a pair of crates bolted to the animal: the gaps between them and
    #    the body are what did it, and a haunch is not a thing you can see daylight behind.
    for s in (1, -1):
        for u in range(face + _f(0.34, L), face + depth + 1):
            t = (u - face - _f(0.34, L)) / max(1, depth - _f(0.34, L))
            out = bw + (2 if t < 0.55 else 1)
            top = _f(0.74, H) - int(round(t * _f(0.30, H)))
            for v in range(bw - 1, out + 1):
                for y in range(0, top + 1):
                    put(u, s * v, y, p["back"], "haunch")

    # 3. THE EYE BOXES - on top, at the front, one per side. Lid in the body's colour; the front
    #    face black with ONE yellow block at the inner end, which is the reference exactly.
    ew = _f(0.16, W)                           # inner edge of the box - INSIDE the crown
    for s in (1, -1):
        for u in range(face - 1, face + _f(0.34, L)):   # a LONG lid: the reference's eye box
                                                        # runs well back over the head
            for v in range(ew, ew + 4):
                put(u, s * v, H + 2, p["back"], "eyes")             # the lid
                put(u, s * v, H + 1, p["pupil"], "eyes")            # ...on a dark box
        for v in range(ew, ew + 4):                                 # the black brow band, and
            put(face - 1, s * v, H + 1, p["pupil"], "eyes")         # the eye itself set in it
        x, z = fr.xz(face - 1, s * ew)
        w.put(x, H + 1 + BY, z, p["iris"])
        cells.add((face - 1, s * ew, H + 1))
        feats["eyes"] += 1

    # 4. THE BELLY - ONE pale panel, mouth and belly together, nearly the full width of the
    #    front, with a notch of body colour cut into its top middle for the upper lip
    # ...FROM THE GROUND UP, and about two thirds of the height. At 0.78 it ran nearly to the
    # eyes and the head above it was a narrow band; on the reference there is a good depth of
    # body colour between the pale and the eye boxes.
    btop = _f(0.66, H)
    for y in range(0, btop + 1):
        for v in range(-bw + 1, bw):           # ...and nearly the full width of the front
            feats["throat"] += paint(face, v, y, p["belly"], over=(p["back"],))
    for v in range(-_f(0.10, W), _f(0.10, W) + 1):                  # the lip: a narrow tongue
        for y in range(btop, btop + 1):                             # cut into the panel's top,
                                                                    # not a bite out of it
            feats["mouth"] += paint(face, v, y, p["back"], over=(p["belly"],))

    # 5. THE FEET - THREE TOES FANNING FROM A PAD, which is what a foot is. Built as three
    #    parallel prongs of equal length at equal spacing they were a RAKE: nothing radiates,
    #    nothing tapers, and the eye reads a tool rather than an animal. Each toe here leaves
    #    the pad on its own heading and is drawn as a STAIRCASE, because a diagonal line of
    #    cells touches only at its corners and 6-connectivity calls that three separate toes.
    def toe_run(u0, v0, du, dv, n, part="toes"):
        u, v = u0, v0
        put(u, v, 0, p["foot"], part)
        for i in range(n):
            if dv and (i % 2 == 1 or du == 0):
                v += dv
                put(u, v, 0, p["foot"], part)
            if du:
                u += du
                put(u, v, 0, p["foot"], part)

    for s in (1, -1):
        pad_v = bw
        for dv in range(-2, 2):                                  # the pad the toes spring from
            put(face - 1, s * (pad_v + dv), 0, p["foot"], "toes")
        toe_run(face - 1, s * (pad_v - 2), -1, -s, toe - 1)      # inner toe, angled in
        toe_run(face - 1, s * pad_v, -1, 0, toe)                 # middle toe, straight ahead
        toe_run(face - 1, s * (pad_v + 1), -1, s, toe - 1)       # outer toe, angled out
        # THE LAMP GOES IN THE PAD, AT face-1. On a toe it is a white block in an orange foot
        # and reads as damage - and aimed at `face` it silently did nothing at all, because the
        # BODY already owns that column at the ground course, so `paint` refused a cell that was
        # never foot. The pad is the one course in front of the body.
        feats["glow"] += paint(face - 1, s * (pad_v - 1), 0, p["lamp"], over=(p["foot"],))

    # 6. THE HIND FEET - the same flat idiom, out beside the haunches
    for s in (1, -1):
        u0 = face + _f(0.56, L)
        for du in range(0, _f(0.22, L)):
            put(u0 + du, s * (bw + 2), 0, p["foot"], "toes")
        for dv in range(0, 3):
            put(u0 + _f(0.22, L) - 1, s * (bw + dv), 0, p["foot"], "toes")

    # 7. THE COAT - a few darker patches on the back, the reference's own brick mottle
    # THE REFERENCE'S BODY IS BRICK AND IT VARIES. A single uniform tone over 1,300 cells is
    # the flattest thing in this build; the statue's own mass reads as many blocks because its
    # texture changes across it. Patches of the mid tone on the crown and the shoulders, laid
    # as blobs rather than a hash per cell - hashed per cell it is noise, which the deck soffit
    # and the first three coats of this animal all shipped.
    for tu, tv, ty in ((0.26, 0.55, 0.98), (0.50, -0.45, 0.98), (0.68, 0.35, 0.94),
                       (0.22, 1.00, 0.72), (0.44, -1.00, 0.60), (0.62, 1.00, 0.80),
                       (0.30, -1.00, 0.40), (0.78, 1.00, 0.46), (0.86, -1.00, 0.66)):
        u = face + _f(tu, L)
        v = int(round(tv * bw))
        y = _f(ty, H)
        for du, dv, dy in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 0, -1), (0, 0, -1)):
            feats["marks"] += paint(u + du, v + dv, y + dy, p["flank"], over=(p["back"],))

    # 8. ITS OWN LIGHT. The island night pass cannot see this lot - its classifier takes each
    #    column's topmost standable cell and the lot lies 113 courses under the island's belly -
    #    so the animal lights itself. Froglights are worked into the back, spread rather than
    #    run down the spine: along the middle they leave the rear quarters dark, and those
    #    corners are where a mob would stand.
    tops: dict[tuple[int, int], int] = {}
    for (u, v, y) in cells:
        tops[(u, v)] = max(tops.get((u, v), -99), y)
    SPOTS = ((0.34, 0.0), (0.50, 0.60), (0.50, -0.60), (0.66, 0.0),
             (0.74, 0.72), (0.74, -0.72), (0.88, 0.35), (0.88, -0.35))
    for tu, tv in SPOTS[:int(p.get("glow") or 0)]:
        u = face + _f(tu, L)
        for dv in (0, 1, -1, 2, -2):
            v = int(round(tv * bw)) + dv
            if (u, v) in tops and paint(u, v, tops[(u, v)], p["lamp"],
                                        over=(p["back"], p["flank"], p["mark"])):
                feats["glow"] += 1
                break

    # 10. THE SKIRT - every column that sits on the ground meets its OWN ground. On a course of
    #     roll the animal would otherwise hover over the dip; never dug, only filled
    for (u, v) in {(u, v) for (u, v, y) in cells if y == 0}:
        x, z = fr.xz(u, v)
        g = ground(x, z)
        if g is None:
            continue
        for y in range(g + 1, BY):
            if _free(ctx, x, y, z) and not w.has(x, y, z):
                w.put(x, y, z, p["flank"])
                feats["skirt"] += 1

    # NO `profile_view` HERE ON PURPOSE. panel.py derives it from the facing - an animal
    # looking along x shows its profile to a viewer looking along z - and stating "side"
    # overrides that with the head-on view, which is the one view a profile must not be.
    return w.canvas({"kind": "frog", "facing": [int(v) for v in p["facing"]], "base_y": BY,
                     "features_built": feats, "dig": []})
