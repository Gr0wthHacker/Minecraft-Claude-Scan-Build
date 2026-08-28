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

    "back": "orange_wool",     # three tones of one hue, brightest first
    "flank": "acacia_planks",
    "mark": "brown_wool",
    "belly": "birch_planks",
    "iris": "yellow_wool",
    "pupil": "black_wool",
    "lamp": "ochre_froglight",
    "glow": 3,                 # froglights worked into the back; 0 turns them off
    "eye_gold": False,         # the mob's gold rim is SUB-BLOCK at this size - see the eyes
}


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
    feats = {k: 0 for k in ("head", "body", "haunch", "shin", "forelegs", "toes", "skirt",
                            "eyes", "mouth", "throat", "nostril", "marks", "glow")}
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

    # ---------- the layout, every number of it derived from L, W and H ----------
    hu = _f(0.42, L) - 1                       # last station of the head
    # THE PLAN NEEDS A WAIST. At head 11, body 9 and haunches 13 the envelope was a constant
    # rectangle 17x15 and the animal read as a brick from above - which is the view this medium
    # gives away free, so it is the one that must not be a box. Narrow head, narrower body,
    # wide haunches, and the eyes and the feet standing outside the head's own width.
    # THE HEAD IS THE WIDEST THING ON THE ANIMAL. Measured off the mob: its skull is wider
    # than the body behind it, and the eyes sit on top of that width. Built at 0.32 of W the
    # head was narrower than the haunches, so the widest part of the frog was its backside and
    # the front tapered away - which is a rodent.
    hw = _f(0.46, W)                           # head half-width
    bw = _f(0.24, W)                           # body half-width
    qw = _f(0.50, W)                           # haunch outer offset - the animal's widest
    chin = _f(0.25, H)                         # the head's underside: air below it
    # THE HAUNCH IS AS TALL AS THE HEAD, and the body between them is a WAIST. Built at 0.80
    # of the skull height the rear was lower than the front all the way back, so the profile
    # was a head on a loaf; a sitting frog is two masses of about one height with a dip
    # between them, and that dip is the whole line.
    body_top = _f(0.55, H)
    haunch_top = H
    hip_u, rump_u = _f(0.48, L), L - 2

    # 1. THE HEAD - a flat-topped box, nearly half the animal, held clear of the ground. Its
    #    front face is FLAT and square on the grid: that face is what a frog is known by.
    box(1, hu, -hw, hw, chin, H, p["back"], "head", chamfer=("uv", "uy"))
    # THE SNOUT is a step, not a chamfer: the front station is one course lower and one cell
    # narrower on each side, which turns a cube into a face that has a front to it
    box(0, 0, -hw + 1, hw - 1, chin, H - 1, p["back"], "head")
    # ...and the TOP course still runs out to the nose at full width, so it overhangs the face
    # below it on three sides. That brow is what the reference house has over its eye band, and
    # it costs nothing: the animal cannot grow forward, the nose is 3 blocks off a church wall
    box(0, 0, -hw, hw, H, H, p["back"], "head")

    # 2. THE BODY - lower and narrower than the head, sitting on the ground, and STEPPED: it
    #    rounds toward the back and falls away at the rump instead of ending in a wall
    for sgn in (1, -1):
        mass(hu + 1, L - 1, 0, sgn * bw, 0, body_top, p["back"], "body",
             front=0, rear=1, out=1, per=3)

    # 3. THE HAUNCHES - big blocky folded legs, standing PROUD of the body's back line so the
    #    profile gets its second hump, and past its sides so the plan gets its outline
    for s in (1, -1):
        # PER=3, NOT 2. An animal this size is 7 or 8 courses tall, so a step every second
        # course insets four times before the top and the mass tapers to nothing: the haunch
        # came out as a flat shelf at half height with one lone column standing on it. One
        # step every third course rounds it and still arrives.
        mass(hip_u, rump_u, s * bw, s * qw, 0, haunch_top, p["back"], "haunch",
             front=0, rear=1, out=1, per=3)
        # the shin, folded forward along the flank at the animal's own widest
        # NO CHAMFER, AND IT MUST REACH THE HAUNCH. Chamfered, a part only two cells wide
        # loses both of its end stations entirely - the shin came out as a 2x3 slab floating
        # beside the body, seven cells the component check caught and nothing else would have
        box(hip_u - 3, hip_u, s * (qw - 1), s * qw, 0, _f(0.25, H), p["back"], "shin")

    # 4. THE FEET - flat on the ground, pointing forward, WITH GAPS BETWEEN THE TOES. Three
    #    prongs with a clear cell between them read as a foot; five touching ones are a paddle
    for s in (1, -1):
        box(_f(0.18, L), hu, s * (qw - 1), s * qw, 0, 0, p["back"], "toes")
        for k, reach in ((0, 0.18), (2, 0.10)):          # two long toes, and the gap between
            for u in range(0, _f(reach, L) + 1):
                put(u, s * (qw - k), 0, p["back"], "toes")
        put(_f(0.10, L), s * (qw - 2), 0, p["back"], "toes")     # the inner toe, short
        put(_f(0.16, L), s * (qw - 2), 0, p["back"], "toes")

    # 5. THE ARMS - straight, under the front of the head, holding the chest up. The air
    #    between them and under the chin is what makes the head read as a separate part
    arm_u = _f(0.26, L)
    for s in (1, -1):
        # THE ARM IS UNDER THE SHOULDER, NOT AT THE HEAD'S EDGE. Once the head grew to the
        # animal's full width its edge IS where the hind feet are, so every arm cell found the
        # ground course taken and `forelegs: 0` shipped for the second time - which is the one
        # failure this build has now made twice, and the reason the count is a test.
        aw = max(2, hw - 2)
        box(arm_u, arm_u + 1, s * (aw - 1), s * aw, 0, chin - 1, p["back"], "forelegs")
        # THE HAND IS A SPLAYED PAD WITH GAPS, reaching forward to the line of the snout: on
        # the reference house and the voxel frog the front feet are the detail that says
        # ANIMAL rather than ornament, and they are visible from the front, under the chin,
        # and in plan poking past the face. They stay INBOARD of the hind feet - out at the
        # animal's own widest there is no room, and the nose is 3 blocks off a church wall
        for u in range(0, arm_u):
            put(u, s * (aw - 1), 0, p["back"], "toes")           # the middle toe, longest
        for u in range(1, arm_u):
            put(u, s * (aw - 2), 0, p["back"], "toes")           # the inner toe - at aw-3 it
                                                                 # had no neighbour and both
                                                                 # hands shipped as strays
        for u in range(1, arm_u - 1):
            put(u, s * aw, 0, p["back"], "toes")                 # the outer toe, shortest
        put(arm_u, s * (aw - 2), 0, p["back"], "toes")           # the web behind them

    # 6. THE EYES - the feature that names the animal. Domes on TOP of the skull at its back
    #    corners, protruding above the head line AND past its sides: on the mob they bulge off
    #    the outline in every view, and a bulge inside the outline is a patch, not an eye
    #    Jack, on the three-course gold dome: "too obnoxious, and they feel weird." Both were
    #    true and they had different causes.
    #
    #    OBNOXIOUS: A SUB-BLOCK DETAIL MUST BE DROPPED, NOT ROUNDED UP TO A BLOCK. The gold came
    #    from the mob, where the eye is a dark ball with a bright ring - and that ring is ONE
    #    PIXEL of a sixteen-pixel face. This animal is about one mob long, so the ring is a
    #    sixteenth of a block; rounding it up multiplies its weight by sixteen, and it stopped
    #    being a rim and became a yellow shelf. The house's eye is a plain dark band and the
    #    outside voxel frog's are bumps in the body's own colour - neither has any gold at all.
    #
    #    WEIRD: IT HUNG OFF THE SKULL ON A BRACKET. Reaching from the head's edge to two cells
    #    past it, two thirds of its base stood in open air. On the mob the bulge is ATTACHED.
    #
    #    And set BACK: at 0.16 of the length the front row sat over the head box's own chamfered
    #    corner, so part of the base rested on holes. 0.22 is solid skull, and it is where the
    #    mob's eyes are - on the crown, not over the snout.
    eu = _f(0.22, L)
    # with the gold off the lower course is the MID tone, not the coat: left as the coat only
    # the cap read, and two small dark plusses on the corners of a skull are ears
    rim = p["iris"] if p.get("eye_gold", False) else p["mark"]
    for s in (1, -1):
        for du in range(-1, 2):
            for dv in (-1, 0, 1):
                put(eu + du, s * (hw + dv), H + 1, rim, "eyes")
        for du in range(-1, 2):
            for dv in (-1, 0, 1):
                if abs(du) + abs(dv) < 2:
                    put(eu + du, s * (hw + dv), H + 2, p["pupil"], "eyes")

    # 7. THE FACE - a wide mouth line right across the front, a pale throat under it, and
    #    nostrils. The mouth is a LINE, never scattered cells: the deck soffit's rule
    # THE PALE BAND IS TWO COURSES AND THE MOUTH SITS ON TOP OF IT. One course of birch under
    # a dark line is a seam; the reference house carries a band you can see from across the
    # water, and it is half of what makes a blocky orange box read as a face
    for v in range(-hw, hw + 1):
        feats["mouth"] += paint(0, v, chin + 2, p["mark"], over=(p["back"],))
        feats["throat"] += paint(0, v, chin + 1, p["belly"], over=(p["back"],))
        feats["throat"] += paint(0, v, chin, p["belly"], over=(p["back"],))
    for u in range(1, hu + 1):                                   # ...and back along the jaw
        for s in (1, -1):
            feats["mouth"] += paint(u, s * hw, chin + 2, p["mark"], over=(p["back"],))
            feats["throat"] += paint(u, s * hw, chin + 1, p["belly"], over=(p["back"],))
    for u in range(0, hu):                                       # the pale chin, underneath
        for v in range(-hw + 1, hw):
            feats["throat"] += paint(u, v, chin, p["belly"], over=(p["back"],))
    # ...and in the MID tone, not black. Two black cells on the brow between two black pupils
    # read as a second pair of eyes from head-on, which is the only view that shows them.
    for s in (1, -1):                          # ON THE BROW, at the snout's own tip. Set back
        feats["nostril"] += paint(0, s, H, p["mark"], over=(p["back"],))   # on the skull they
                                                                            # are hidden behind
                                                                            # the overhang

    # 8. THE COAT - a dorsolateral line down each side of the body and mottling in the MID
    #    tone. Dark blotches on the back turned the plan into noise, and the plan is the view
    #    this medium gives away free
    for u in range(hu + 1, hip_u):
        for s in (1, -1):
            feats["marks"] += paint(u, s * bw, body_top, p["mark"], over=(p["back"],))
    # NO BLOTCHES. Three attempts at mottling produced, in order: brown confetti, regular
    # crosses (radius 1.4 over a lofted top yields the five-cell orthogonal plus) and a
    # diamond stamped on the flat back of the box build. The animal reads better plain, and
    # the dorsolateral line above is the one marking that is a LINE rather than a stain.

    # 9. ITS OWN LIGHT - see the docstring. In the skin, never on it: a fixture laid over a
    #    coat is the hole in a sculpture that the night pass's own rule forbids
    tops: dict[tuple[int, int], int] = {}
    for (u, v, y) in cells:
        tops[(u, v)] = max(tops.get((u, v), -99), y)
    for i in range(int(p.get("glow") or 0)):
        uc = _f(0.52 + 0.16 * i, L)
        for v in (0, 1, -1, 2, -2):
            if (uc, v) in tops and paint(uc, v, tops[(uc, v)], p["lamp"],
                                         over=(p["back"], p["flank"], p["mark"])):
                feats["glow"] += 1
                break
    for s in (1, -1):                          # and one in each hind foot: the back lamps
        fu = _f(0.14, L)                       # cannot send light round the body to the toes,
        # AT THE FOOT'S OWN COURSE, not the column's top. The eye sits directly over the hind
        # foot in plan - it is as wide as the haunch, which is what the mob looks like - so
        # asking for the topmost cell of that column returns an eye, `paint` correctly refuses
        # to recolour it, and both foot lamps were silently never placed
        for du, dv in ((0, 0), (1, 0), (0, -1), (1, -1)):
            if paint(fu + du, s * (qw + dv), 0, p["lamp"],
                     over=(p["back"], p["flank"], p["mark"])):
                feats["glow"] += 1
                break
    if int(p.get("glow") or 0):                # ...and one on the crown, because the EYES are
        for v in (0, 1, -1):                   # the highest cells on the animal and the back
            if (hu - 1, v) in tops and paint(hu - 1, v, tops[(hu - 1, v)], p["lamp"],
                                             over=(p["back"], p["mark"])):
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
