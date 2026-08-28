"""A frog, sitting - the churchyard animal for the lot east of the sanctum.

WHY A FROG PASSES. Same test the ladybird, the turtle and the axolotl passed and eight mammals
failed: identity carried by a SINGLE CONVEX MASS with hardware on it, never by compound
volumetric muscle. A sitting frog is one squat dome with four things stuck to it that voxels
render natively - two eye bulges ON TOP, a mouth line running back past them, a folded hind
knee that rises above the back, and a long flat foot lying open on the ground. Three of those
four read in the PLAN, which is the view this medium gives away free, and the fourth (the
knee) is what breaks the profile. The download corpus settled the rest: `Warm Snooze` is a
curled cat that reads instantly because its legs are folded INTO the mass, and a sitting frog
is that shape by anatomy rather than by pose.

And on a 1.19 server the naming test is instant - frogs ARE the mob of this version, and the
ochre froglights already scattered across this island come from them.

SIZE COMES FROM THE EYE. A bulge needs a 3x3 dome plus a clear cell between the pair to read
as two eyes rather than one brow (the ladybird's spot-spacing lesson), so the skull cannot be
under ~9 wide; a frog's head is about four fifths of its body width, which puts the body at 11
and the length at 14. Under that the eyes merge and it is a lump.

COLOUR AGAINST THE GROUND, MEASURED. The lowland floor is moss (89,110,45): a green frog is
the green-turtle mistake, invisible on its own ground. This is the TEMPERATE frog - orange -
a full hue flip off the moss and the one hue the lowland does not already own. Three tones of
ONE hue, which the flamingo proved beats two tones and a third: orange wool (241,118,20) over
acacia planks (168,90,50) over brown wool (114,72,41), with a pale birch throat, a black pupil
and a gold iris. All cheap, all 1.19.

IT CARRIES ITS OWN LIGHT, AND IT HAD TO BE MEASURED TO FIND THAT OUT. A new animal is new
walkable surface; propagated through the finished world, 129 of the 149 air cells over this
one's back stand at block light ZERO, which is a zombie on the frog every night.

The island night pass does not see it, and the reason generalises: its classifier takes each
column's TOPMOST standable cell, and this lot is 113 courses under the island's belly - so
the topmost standable block in every column here is up in the belly skin, and the whole lot,
frog included, is invisible to the pass. That blind spot is not this animal's to fix, but the
dark over its own back is.

So it glows. Three ochre froglights sit IN the dorsal skin, spaced along the spine: light 15
apiece takes every cell over the animal above zero, they read as the pale dorsal spots a real
frog carries, and the block is the one Minecraft makes FROM frogs - which is also the block
Jack has been scattering across this island by hand. `glow: 0` turns them off; then something
else has to light it.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .ruinring import _free, _surface

FROG = {
    "under": None,             # capture/composite the ground is read from - required
    "at": None,                # [x, z] the body centroid sits over - required
    "facing": [-1, 0],         # CARDINAL only: the head is straight and its faces lie on the
                               # block grid. Aimed off-axis, a flat face becomes a diagonal
                               # staircase of corners - the axolotl paid three passes for that
    "base_y": None,            # the belly plane - PIN it once built, or a rescan drifts it
    "length": 14,              # nose to rump along the gaze axis
    "width": 11,               # across, at the haunches
    "height": 7,               # belly plane to the top of the haunch
    "seed": 0,

    "back": "orange_wool",     # three tones of one hue, brightest first
    "flank": "acacia_planks",
    "mark": "brown_wool",
    "belly": "birch_planks",
    "iris": "yellow_wool",
    "pupil": "black_wool",
    "lamp": "ochre_froglight",
    "glow": 3,                 # dorsal froglights - see the docstring; 0 turns them off
    "lamps": [],               # [x, z] turf columns to sink a froglight into; [] = none
}

# Fractions of the animal's own dimensions, so every feature scales with it.
# The waist behind the skull is deliberate. Without it the head is as wide as the body and
# the animal reads as a worm with a face - the axolotl paid a whole pass for that pinch.
_HALFW = [(0.00, 0.16), (0.08, 0.46), (0.20, 0.76), (0.30, 0.72), (0.40, 0.58),
          (0.55, 0.78), (0.74, 1.00), (0.88, 0.86), (1.00, 0.34)]
# TWO HUMPS AND A DIP, or the silhouette is a hill. The panel failed the first profile on
# exactly this: the eye dome sat two courses UNDER the back line and the knee three under it,
# so both features - the only two that say frog - were swallowed by the outline. The eyes now
# finish level with the haunch, the neck dips hard between them, and the knee clears both.
_TOP = [(0.00, 0.55), (0.08, 0.66), (0.20, 0.75), (0.34, 0.50), (0.50, 0.66),
        (0.74, 0.875), (0.88, 0.80), (1.00, 0.50)]
# The chest is held HIGH. At 0.15 the shoulder was one course off the ground, so the foreleg
# was a single cell - a sitting frog props itself up on straight arms, and the lift is also
# what puts the head over the back line where the eyes can break the outline.
_FLOOR = [(0.00, 0.40), (0.12, 0.36), (0.30, 0.28), (0.45, 0.10), (0.60, 0.00), (1.00, 0.00)]

_T_EYE, _T_EAR, _T_FORE, _T_KNEE, _T_HEEL = 0.19, 0.32, 0.30, 0.74, 0.44


def _at(keys, t):
    """Piecewise-linear read of a keyframe profile."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return keys[-1][1]


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
    feats = {k: 0 for k in ("body", "skirt", "eyes", "mouth", "ear", "nostril",
                            "forelegs", "hindlegs", "toes", "belly", "marks", "lamps",
                            "glow")}
    dig: list[tuple[int, int, int]] = []
    top_at: dict[tuple[int, int], int] = {}     # OUR OWN top map: Canvas.get returns -1 out of
                                                # bounds and -1 is truthy, which has produced a
                                                # clean audit and a wrong build twice here
    body: set[tuple[int, int, int]] = set()     # (u, v, y) in body frame, for anchoring limbs
    mass: set[tuple[int, int, int]] = set()     # the MASS alone - see flank_v

    def put(x, y, z, name, **props):
        if _free(ctx, x, y, z) and not w.has(x, y, z):
            w.put(x, y, z, name, **props)
            return 1
        return 0

    # ---- 1. THE MASS. Squat, widest at the haunches, propped at the front: the belly line is
    # set INDEPENDENTLY of the floor, which is what the jaguar panel said a body needs and
    # what makes a sitting frog sit rather than lie ----
    for u in range(L):
        t = u / (L - 1)
        hw = _at(_HALFW, t) * (W / 2.0)
        hi = _at(_TOP, t) * H
        lo = _at(_FLOOR, t) * H
        vi = int(hw + 0.5)
        for v in range(-vi, vi + 1):
            q = 1.0 - (abs(v) / hw) ** 2.2 if hw > 0 else 0.0
            if q <= 0.02:
                continue
            colt = lo + (hi - lo) * q ** 0.45
            x, z = fr.xz(u, v)
            g = ground(x, z)
            if g is None:
                continue
            y0 = BY + int(round(lo))
            y1 = BY + int(round(colt))
            for y in range(y0, y1 + 1):
                skin = (y == y1) or abs(v) >= vi - 1
                feats["body"] += put(x, y, z, p["back"] if skin else p["flank"])
                body.add((u, v, y))
                mass.add((u, v, y))
            top_at[(u, v)] = y1
            # the rim meets its own ground: on a course of roll the skirt is what stops the
            # animal hovering over a dip. Never dug, only filled.
            if int(round(lo)) == 0:
                for y in range(g + 1, BY):
                    feats["skirt"] += put(x, y, z, p["flank"])
            # the pale throat, where the front is held clear of the ground. A PATCH down the
            # middle, not the full width: birch under the whole head reads as a sandwich
            # ...and not at the snout: a pale cell on the first two stations pokes out past
            # the nose in profile and reads as something the animal is holding in its mouth
            if y0 > BY and abs(v) <= 2 and u >= 2:
                if w.name(x, y0, z) in (p["back"], p["flank"]):
                    w.put(x, y0, z, p["belly"])
                    feats["belly"] += 1

    def out_at(u, y, sign):
        """One step OUTSIDE the built skin at this station and height. Anything clinging is
        anchored to the SURFACE THAT EXISTS - a feature placed at a computed radius comes off
        as its own component, which is how the mane, the ossicones and the tail all detached."""
        for v in range(int(W), 0, -1):
            if (u, sign * v, y) in body:
                return sign * (v + 1)
        return None

    def flank_v(u, sign):
        """The body's WIDEST offset at this station, whatever the height.

        Not the widest at the limb's own height, which is what the first build asked for: at
        the knee the leg is ABOVE the dome, so the widest cell at that height is a cell or two
        off the spine and the whole hind leg was laid along the animal's back as a ridge. A
        leg presses against the FLANK, so it follows the flank's plan outline and rises past
        the back line in free air, carried by the cell under it.

        Measured on the MASS, never on everything built so far: reading `body` counts the limb
        cells this walk has already laid, so each pass answered one cell further out than the
        last and the legs crept outward until the animal was 19 wide instead of 15."""
        for v in range(int(W), 0, -1):
            if any((u, sign * v, y) in mass for y in range(BY, BY + H + 3)):
                return sign * v
        return None

    # ---- 2. THE FORELEG: short, straight, propping the chest up - the reason the head is in
    # the air and the profile is not two parallel horizontals.
    #
    # BEFORE the hind leg, because the hind FOOT lies exactly where the hand goes: built after
    # it, every one of its cells found the ground course already taken and the animal shipped
    # with `forelegs: 0` in its own sidecar - and nothing else noticed, because a frog missing
    # its arms is still one connected piece with no placement problem ----
    u_fore = int(round(_T_FORE * (L - 1)))
    fore_y = BY + int(round(_at(_FLOOR, _T_FORE) * H))
    for sign in (1, -1):
        v = out_at(u_fore, fore_y, sign)
        if v is None:
            continue
        v -= sign                               # the leg hangs under the shoulder, not beside
        x, z = fr.xz(u_fore, v)
        g = ground(x, z)
        if g is None:
            continue
        for y in range(g + 1, fore_y + 1):
            feats["forelegs"] += put(x, y, z, p["back"])
        for du, dv in ((1, 0), (2, 0), (1, sign), (1, -sign)):    # four toes, forward
            x2, z2 = fr.xz(u_fore - du, v + dv)
            if ground(x2, z2) is not None:
                feats["toes"] += put(x2, BY, z2, p["back"])

    # ---- 3. THE FOLDED HIND LEG - the half of the silhouette a frog cannot do without: hip
    # low and back, knee up and forward, shin down and forward, and a long flat foot. In the
    # PLAN it is a Z beside the body, which is the view this medium gives away free ----
    # The hip sits at the back, the knee rides high over the flank, the heel comes down at
    # mid-body and the foot runs forward from there - past the shoulder, level with the jaw,
    # which is where a sitting frog's feet really are and what makes the plan read.
    HIP, KNEE, HEEL = (0.92, 0.30), (0.75, 1.00), (0.50, 0.10)
    limb_cells: set[tuple[int, int, int]] = set()

    def limb(t0, h0, t1, h1, sign, thick=1):
        """A staircase along the flank, never a diagonal, and never a gap.

        Two rules, both learned the hard way here. A step that moves in u AND y at once leaves
        two cells touching at a corner only, which 6-connectivity calls two pieces - how the
        first cats' ear tips broke off. And a run steeper than one course per station skips
        courses, so the cells above hang on nothing: the span between one step and the next is
        FILLED, not sampled."""
        u0, u1 = t0 * (L - 1), t1 * (L - 1)
        y0, y1 = BY + int(round(h0 * H)), BY + int(round(h1 * H))
        n = max(abs(int(round(u1 - u0))), abs(y1 - y0)) + 1
        pu, py = None, None
        for i in range(n):
            f = i / max(1, n - 1)
            u = int(round(u0 + (u1 - u0) * f))
            y = int(round(y0 + (y1 - y0) * f))
            for uu in sorted({pu, u} - {None}):
                fv = flank_v(uu, sign)
                if fv is None:
                    continue
                v = fv + sign
                x, z = fr.xz(uu, v)
                lo = min(y, py if py is not None else y) - (thick - 1)
                for yy in range(lo, max(y, py if py is not None else y) + 1):
                    feats["hindlegs"] += put(x, yy, z, p["back"] if yy == y else p["flank"])
                    body.add((uu, v, yy))
                    if yy == y:
                        limb_cells.add((uu, v, yy))
                    # THE THIGH MERGES INTO THE FLANK. The dome falls away fast at its widest
                    # offset, so a leg standing one cell outside it touches the body only near
                    # the ground and the knee hangs on nothing - two clusters of ten cells the
                    # buildability check called unbuildable. Filling the cell inboard both
                    # anchors it and is what a haunch actually looks like: muscle, not a stick
                    if (uu, v - sign, yy) not in body:
                        xi, zi = fr.xz(uu, v - sign)
                        feats["hindlegs"] += put(xi, yy, zi, p["flank"])
                        body.add((uu, v - sign, yy))
            pu, py = u, y

    for sign in (1, -1):
        limb(*HIP, *KNEE, sign, thick=2)                 # thigh, up and forward
        limb(*KNEE, *HEEL, sign, thick=2)                # shin, down and forward
        # THE FOOT - half the body long, flat, pointing forward. THE TOES NEED A GAP: two
        # prongs with a clear cell between them read as a foot, five touching ones read as a
        # paddle (the ladybird's spot-spacing rule), and they must clear the head's own width
        # or the plan view - the only view that shows a foot - hides them under the jaw.
        heel = int(round(HEEL[0] * (L - 1)))
        fv = flank_v(heel, sign)
        if fv is None:
            continue
        v0 = fv + sign
        cells = [(heel - du, v0 + dv * sign) for du in range(0, 4) for dv in (-1, 0, 1)]
        cells += [(heel - 3 - du, v0 + sign) for du in range(1, 5)]      # outer toe, long
        cells += [(heel - 3 - du, v0 - sign) for du in range(1, 4)]      # inner toe, shorter
        cells = [(u, vv) for (u, vv) in cells if u >= 0]
        gs = [g for (u, vv) in cells for g in [ground(*fr.xz(u, vv))] if g is not None]
        if not gs:
            continue
        # ONE level for the whole foot, then filled down to each column's own ground: a pad
        # held at the belly plane over ground that rolls away floats, and per-column seating
        # puts neighbours on two courses, which touch only diagonally
        level = min(BY, max(gs) + 1)
        for (u, vv) in cells:
            x, z = fr.xz(u, vv)
            g = ground(x, z)
            if g is None:
                continue
            for y in range(min(g + 1, level), level + 1):
                feats["toes"] += put(x, y, z, p["back"] if y == level else p["flank"])
                body.add((u, vv, y))
                if y == level:
                    limb_cells.add((u, vv, y))
        # A GLOWING PAD IN THE FOOT. The dorsal lamps sit on the spine and their light has to
        # travel round the body to reach the toes, which are the length of the animal away and
        # in its shadow: measured, the two cells over the outer toe tip stayed at zero however
        # the spine lamps were spaced. A frog's toe pads are pale, so this is where one goes.
        if int(p.get("glow") or 0):
            x, z = fr.xz(heel - 1, v0)
            if w.name(x, level, z) == p["back"]:
                w.put(x, level, z, p["lamp"])
                feats["glow"] = feats.get("glow", 0) + 1

    # ---- 4. THE FACE, read off the mass that was actually built ----
    u_eye = int(round(_T_EYE * (L - 1)))
    v_eye = max(2, int(round(0.26 * W)))
    for sign in (1, -1):
        ty = top_at.get((u_eye, sign * v_eye))
        if ty is None:
            continue
        for du in (-1, 0, 1):                   # a 3x3 cap, then a crown: two courses, so the
            for dv in (-1, 0, 1):               # bulge breaks the head line from the side too
                x, z = fr.xz(u_eye + du, sign * v_eye + dv)
                feats["eyes"] += put(x, ty + 1, z, p["iris"])
        for du, dv in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            x, z = fr.xz(u_eye + du, sign * v_eye + dv)
            feats["eyes"] += put(x, ty + 2, z, p["pupil"] if (du == 0 and dv == 0)
                                 else p["iris"])
        x, z = fr.xz(u_eye, sign * (v_eye + 2))  # a pupil on the outer face, so the eye
        feats["eyes"] += put(x, ty + 1, z, p["pupil"])           # reads in profile as well

    # the mouth: a continuous seam along the jaw from the snout back PAST the eye, which is
    # where a frog's mouth really ends. A line, never scattered cells - the deck soffit's rule
    for u in range(0, int(round(0.42 * (L - 1))) + 1):
        t = u / (L - 1)
        hw = _at(_HALFW, t) * (W / 2.0)
        jaw = BY + int(round(_at(_FLOOR, t) * H))
        for sign in (1, -1):
            for v in range(int(hw + 0.5), 0, -1):
                if (u, sign * v, jaw) in body:
                    x, z = fr.xz(u, sign * v)
                    if w.name(x, jaw, z) in (p["back"], p["flank"]):
                        w.put(x, jaw, z, p["mark"])
                        feats["mouth"] += 1
                    break
        if u <= 1:                              # the snout tip carries the seam across
            for v in range(-1, 2):
                x, z = fr.xz(u, v)
                if w.name(x, jaw, z) in (p["back"], p["flank"]):
                    w.put(x, jaw, z, p["mark"])
                    feats["mouth"] += 1

    # the tympanum: the ear disc behind the eye. A real field mark, four cells, on the skin
    u_ear = int(round(_T_EAR * (L - 1)))
    ear_y = BY + int(round(_at(_TOP, _T_EAR) * H * 0.55))
    for sign in (1, -1):
        for du, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            v = out_at(u_ear + du, ear_y + dy, sign)
            if v is None:
                continue
            x, z = fr.xz(u_ear + du, v - sign)
            if w.name(x, ear_y + dy, z) in (p["back"], p["flank"]):
                w.put(x, ear_y + dy, z, p["mark"])
                feats["ear"] += 1

    for sign in (1, -1):                        # nostrils, on top of the snout
        u = int(round(0.06 * (L - 1)))
        ty = top_at.get((u, sign))
        if ty is not None:
            x, z = fr.xz(u, sign)
            if w.name(x, ty, z) is not None:
                w.put(x, ty, z, p["pupil"])
                feats["nostril"] += 1

    # ---- 5. THE COAT: a dorsolateral LINE and a few drifts. Not confetti - the thicket
    # learned that in green and the deck soffit learned it in wood ----
    for u in range(u_eye + 2, int(round(0.62 * (L - 1)))):
        t = u / (L - 1)
        hw = _at(_HALFW, t) * (W / 2.0)
        for sign in (1, -1):
            v = int(round(sign * hw * 0.78))
            ty = top_at.get((u, v))
            if ty is None:
                continue
            x, z = fr.xz(u, v)
            if w.name(x, ty, z) == p["back"]:
                w.put(x, ty, z, p["mark"])
                feats["marks"] += 1
    # mottling in the MID tone, not the dark one. Brown blotches on the back turned the plan -
    # the view that matters for this animal - into noise; acacia against orange is 40 of
    # luminance, which is texture at arm's length and one colour from across the lot
    # RADII BIG ENOUGH TO BE DISCS. At 1.1-1.8 the test dx^2+dv^2 <= r^2 yields the five-cell
    # orthogonal plus and the back came out stamped with regular crosses - the same confetti
    # failure as the deck soffit, wearing a new hat
    for i, (tc, vc) in enumerate(((0.52, 0.00), (0.70, 0.28), (0.70, -0.28))):
        uc, rad = tc * (L - 1), 2.0 + 0.8 * hash01(seed, i, 11, 5)
        for (u, v), ty in list(top_at.items()):
            if (u - uc) ** 2 + (v - vc * W) ** 2 <= rad ** 2:
                x, z = fr.xz(u, v)
                if w.name(x, ty, z) == p["back"]:
                    w.put(x, ty, z, p["flank"])
                    feats["marks"] += 1

    for (u, v, y) in sorted(limb_cells):
        if (u + max(0, v)) % 3 == 0 and w.name(*fr.xz(u, v)[:1], y, fr.xz(u, v)[1]) is not None:
            x, z = fr.xz(u, v)
            if w.name(x, y, z) == p["back"]:
                w.put(x, y, z, p["mark"])
                feats["marks"] += 1

    # ---- 6a. THE DORSAL FROGLIGHTS. In the skin, not on it: a fixture laid over a coat is
    # the hole in a sculpture the night pass's own rule forbids, while a froglight worked INTO
    # the back is a marking that happens to emit. Spaced along the spine so no cell of the
    # animal is more than a few blocks of open air from one ----
    for i in range(int(p.get("glow") or 0)):
        t = 0.30 + 0.24 * i
        u = int(round(t * (L - 1)))
        for v in (0, 1, -1, 2, -2):                 # the spine first, then step off it if the
            ty = top_at.get((u, v))                 # crown cell is somebody else's already
            if ty is None:
                continue
            x, z = fr.xz(u, v)
            if w.name(x, ty, z) in (p["back"], p["flank"], p["mark"]):
                w.put(x, ty, z, p["lamp"])
                feats["glow"] = feats.get("glow", 0) + 1
                break

    # ---- 6. ITS OWN LIGHT, flush in the turf: the froglight is the frog's own block, and a
    # fixture standing proud of the moss beside an animal reads as a lamp somebody left ----
    for lx, lz in (p.get("lamps") or []):
        g = ground(int(lx), int(lz))
        if g is None:
            raise ValueError(f"lamp at {(lx, lz)} has no ground under it - resite it")
        if w.has(int(lx), g, int(lz)):
            raise ValueError(f"lamp at {(lx, lz)} is inside the frog - resite it")
        dig.append((int(lx), g, int(lz)))       # flush: its own cell is dug first
        w.put(int(lx), g, int(lz), p["lamp"])
        feats["lamps"] += 1

    # NO `profile_view` HERE ON PURPOSE. panel.py derives it from the facing - an animal
    # looking along x shows its profile to a viewer looking along z ("face") - and stating
    # "side" overrides that with the head-on view, which is the one view a profile must not be.
    return w.canvas({"kind": "frog",
                     "facing": [int(v) for v in p["facing"]], "base_y": BY,
                     "features_built": feats, "dig": [list(d) for d in dig]})
