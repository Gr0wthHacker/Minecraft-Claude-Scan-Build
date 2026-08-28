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

    # ---------- the layout: AN UPRIGHT SITTING STATUE ----------
    #
    # Rebuilt from Graysun's Frog Statue, which is the reference that finally said what "cute"
    # means here, and it is not what I had been building. Everything before this was a flat
    # crouching creature copied off the mob's proportions; the statue is UPRIGHT and COMPACT -
    # about as tall as it is wide - and the whole of its front is a FACE, stacked:
    #
    #     two big BRIGHT eyes at the top, dark-framed and proud of the skull
    #     a huge PALE MOUTH band right across the width, a dark line drawn over it
    #     a big PALE BELLY panel under that, inset from the sides
    #     chunky arms down both sides, ending in splayed toed feet on the ground
    #
    # That stack is the design. A frog seen from the front is a face and a belly, and the two
    # references before this one were both saying the same thing in a way I read as being about
    # the body: the house's "eye band and white band" IS this, and the mob's tan throat is the
    # belly. I was measuring their silhouettes and missing their fronts.
    #
    # `length` is the DEPTH here, nose to rump; `height` is the animal, which is now the big
    # dimension. The lot has 113 courses of headroom, so height was always free.
    toe = _f(0.22, L)                          # the front feet occupy the first stations...
    face = toe                                 # ...and the body's flat front face is behind them
    half = W // 2

    # width and depth as fractions of the animal's own, by HEIGHT: narrow-ish at the crown,
    # widest through the belly and the haunches, drawing in at the ground
    # THE HEAD STAYS WIDE ALMOST TO THE CROWN. Tapered from 0.76 up, it was only nine wide
    # where the eyes are and their frames hung out past it on both sides - the bracket problem
    # again, and the narrow ridge left between them read as a mohawk. On the statue the head is
    # a rounded dome that is nearly full width right up to the last course or two.
    WBY = [(0.00, 0.84), (0.15, 1.00), (0.72, 1.00), (0.90, 0.92), (1.00, 0.72)]
    DBY = [(0.00, 0.88), (0.20, 1.00), (0.70, 0.98), (0.90, 0.88), (1.00, 0.70)]

    def wid_at_y(y):
        return max(1, int(round(_at(WBY, y / H) * half)))

    def dep_at_y(y):
        return max(2, int(round(_at(DBY, y / H) * (L - 1 - face))))

    # 1. THE MASS - one rounded upright body with a FLAT FRONT. The face and the belly are a
    #    panel, so the front must be a plane; the back and the sides round away from it.
    for y in range(0, H + 1):
        wid, dep = wid_at_y(y), dep_at_y(y)
        for u in range(face, face + dep + 1):
            for v in range(-wid, wid + 1):
                back = u >= face + dep - 1
                edge = abs(v) >= wid - 1
                if back and edge:              # the back corners are cut away, which is all
                    continue                   # the rounding a voxel mass needs
                put(u, v, y, p["back"], "body")

    # 1b. THE HAUNCHES - a bulge at each rear quarter, standing a cell proud of the flank. The
    #     statue's front is a face and its back is a plain rounded mass, which is true of the
    #     reference too - but from the two profiles a plain mass is all you get, and a frog's
    #     widest point when it sits is the fold of its hind leg.
    for s in (1, -1):
        for u in range(face + _f(0.30, L), face + _f(0.78, L)):
            for y in range(0, _f(0.46, H)):
                put(u, s * (wid_at_y(y) + 1), y, p["back"], "haunch")

    # 2. THE EYES - the statue's loudest feature and the reason it reads from across a room:
    #    two BIG BRIGHT squares set into the top of the head, each ringed in dark, standing a
    #    cell proud of the face. Ours glow for real - `ochre_froglight` is the block Minecraft
    #    makes FROM frogs, this design already carried it for its own lighting, and a lit eye
    #    is exactly what the reference has.
    #
    #    THE FRAME IS NOT DECORATION. A pale square on an orange head is a patch; the dark ring
    #    is what turns it into an eye, and it is what every earlier version of this face was
    #    missing. Same lesson as the mouth line and the deck's zone bands: a light block needs
    #    a dark edge or it reads as a hole.
    #
    #    (The mob's thin gold rim is a different thing and is SUB-BLOCK at our size - one pixel
    #    of a sixteen-pixel face - which is why rounding it up to a whole block made a yellow
    #    shelf. A bright PUPIL is not a rim; it is the size of a block.)
    #    THE FRONT IS A STACK and the courses have to be budgeted, not each placed from its own
    #    fraction: built that way the eye frame and the mouth band overlapped and the face came
    #    out as one pale slab from the brow to the belly.
    #
    #        H            crown - two courses of head ABOVE the eyes, or they read as a visor
    #        0.62H        the eyes, three courses of light in a one-cell dark frame
    #        0.50H        the mouth line, dark, drawn right across
    #        below it     the mouth, two courses pale
    #        0.10H..      the belly panel, pale, inset another cell each side
    #    THREE THINGS WERE WRONG WITH THE FIRST ONES, all of them geometry rather than colour:
    #
    #    * THE FRAME WAS TWO BLOCKS DEEP. It was laid on the protruding plane AND on the face
    #      behind it, so each eye read as a chunky pair of goggles bolted to the head instead of
    #      an outline round a light. One plane. The dark that wraps the sides of the bulge is
    #      the ring's own edge cells seen end-on, which is all the depth it needs.
    #    * THE HEAD STOOD ABOVE THEM. On the statue the eyes are the TOPMOST thing - they rise
    #      over the crown and the dome dips between them, which is what makes it look up at you.
    #      Built under a full head they were a pair of windows in a wall.
    #    * THE BRIGHT PART WAS SMALL INSIDE A HEAVY FRAME. The light is the feature; the ring is
    #      one cell, and never more.
    er = 3                                     # courses of light in each eye
    ew = _f(0.30, W)                           # ...and how far off the middle they sit
    ey = H - er + 1                            # the top course of light stands ONE over the
    for s in (1, -1):                          # crown, which is the statue's own line
        for dy in range(-1, er + 1):
            for dv in range(-2, 3):
                edge = dy in (-1, er) or abs(dv) == 2
                if edge:
                    put(face - 1, s * (ew + dv), ey + dy, p["mark"], "eyes")
        for dy in range(0, er):
            for dv in (-1, 0, 1):
                x, z = fr.xz(face - 1, s * (ew + dv))
                w.put(x, ey + dy + BY, z, p["lamp"])
                cells.add((face - 1, s * (ew + dv), ey + dy))
                feats["eyes"] += 1

    # 3. THE MOUTH - a pale band right across the front with a dark line drawn over it. On the
    #    statue this is the widest thing on the face and it is most of what makes it smile.
    # DIRECTLY UNDER THE EYES. Placed at a fraction of the height it left two courses of brow
    # between the eye frames and the mouth, and on the statue there is none - eyes, a dark lip,
    # then the band. That gap is what was still making it a face painted on a wall.
    my = ey - 2
    for v in range(-wid_at_y(my), wid_at_y(my) + 1):
        feats["mouth"] += paint(face, v, my, p["mark"], over=(p["back"],))
        for dy in (1, 2):
            feats["mouth"] += paint(face, v, my - dy, p["belly"], over=(p["back"],))

    # 4. THE BELLY - a big pale panel under the mouth, inset from the sides so the body's own
    #    colour frames it. The house's white band and the mob's tan throat are both this.
    for y in range(_f(0.08, H), my - 3):
        w2 = wid_at_y(y) - 2
        for v in range(-w2, w2 + 1):
            feats["throat"] += paint(face, v, y, p["belly"], over=(p["back"],))

    # 5. THE ARMS - chunky, down both sides of the belly, standing a little proud of the body
    #    so they read as limbs and not as more body
    for s in (1, -1):
        for y in range(0, _f(0.44, H)):
            v = wid_at_y(y) + 1
            for du in range(0, 3):
                put(face + du, s * v, y, p["back"], "forelegs")

    # 6. THE FEET - splayed forward on the ground with a clear cell between the toes, which is
    #    what the statue does and what says ANIMAL rather than ornament
    for s in (1, -1):
        base = wid_at_y(0) + 1
        for du in range(0, toe + 1):
            put(face - du, s * base, 0, p["back"], "toes")            # the outer toe
            put(face - du, s * (base - 2), 0, p["back"], "toes")      # the inner toe
        for dv in range(-2, 2):                                       # the pad behind them
            put(face, s * (base + dv), 0, p["back"], "toes")
        put(face - toe, s * (base - 1), 0, p["back"], "toes")         # ...and the web at the tip

    # 7. THE HIND FEET - at the rear quarters, pointing outward, the same idiom
    for s in (1, -1):
        for u in range(face + _f(0.34, L), face + _f(0.62, L)):
            put(u, s * (wid_at_y(0) + 1), 0, p["back"], "toes")

    # 8. THE COAT - a few darker patches on the crown and the shoulders. SPOTS, not a line:
    #    a dorsolateral stripe ran on from the mouth seam and banded the animal like a badger.
    for i, (tu, tv, ty) in enumerate(((0.30, 0.55, 0.86), (0.55, -0.40, 0.92),
                                      (0.72, 0.30, 0.78), (0.48, 0.00, 0.96))):
        u = face + _f(tu, L)
        y = _f(ty, H)
        v = int(round(tv * wid_at_y(y)))
        for du, dv in ((0, 0), (1, 0), (0, 1), (0, -1)):
            feats["marks"] += paint(u + du, v + dv, y, p["mark"], over=(p["back"],))

    # 9. ITS OWN LIGHT - THE EYES. Measured on the first build, 129 of the 149 air cells over
    #    this animal's back stood at block light zero, and the island night pass cannot see
    #    them: its classifier takes each column's topmost standable cell, and this lot lies 113
    #    courses under the island's belly. Froglights used to be worked into the back for that.
    #    They are the EYES now, which is both the reference's own look and a better answer -
    #    the light is a feature instead of a fixture. Any shortfall is topped up on the crown.
    tops: dict[tuple[int, int], int] = {}
    for (u, v, y) in cells:
        tops[(u, v)] = max(tops.get((u, v), -99), y)
    #    SPREAD ACROSS THE BACK, not down the spine. Placed along the middle they left the
    #    rear quarters dark - the haunch tops are a course lower than the crown and out of
    #    reach round the shoulder - and those corners are exactly where a mob would stand.
    SPOTS = ((0.30, 0.0), (0.46, 0.55), (0.46, -0.55), (0.62, 0.0),
             (0.70, 0.70), (0.70, -0.70), (0.86, 0.35), (0.86, -0.35))
    for i, (tu, tv) in enumerate(SPOTS[:int(p.get("glow") or 0)]):
        u = face + _f(tu, L)
        for dv in (0, 1, -1, 2, -2):
            v = int(round(tv * (W // 2))) + dv
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
