"""THE SAUROPOD - the Lost Plateau's landmark, and the one big animal this system is good at.

**IT IS BUILT BECAUSE OF THE RULE, NOT IN SPITE OF IT.** CLAUDE.md's hardest-won finding is that
this medium renders PLANAR and COLUMNAR shapes natively and VOLUMETRIC muscle worst of anything -
eight mammals scored GOOD on every measured dimension and were retired on sight, and the jaguar at
2.6x and 60,000 blocks failed exactly as the 27-block one did. A brachiosaur is the good half of
that line, three times over:

* **the neck is a column** - the giraffe is the one quadruped in this repo that works, and it works
  because its identity is a neck;
* **the legs are columns** - straight tapers, which is what killed the cats (constant-width posts at
  the corners) and what a sauropod actually has;
* **and the silhouette carries it entirely.** You can name this animal from an outline at a quarter
  scale, which is the panel review's only real question.

A T-REX IS THE ONE EVERYBODY WANTS AND THE ONE THIS SYSTEM IS WORST AT - a heavy biped is
compound volumetric muscle over a short deep body, which is the jaguar's failure standing up. If
one is ever built here it is built as a SKELETON, which is planar, and which `gen/wyrm.py`'s
40-block skull already proves reads.

**THE PROFILE IS A BRACHIOSAUR AND THAT IS A DECISION, NOT A DEFAULT.** A diplodocid carries its
neck level, which foreshortens to nothing from three of four bearings and reads as a log on legs. A
brachiosaur's front legs are LONGER than its back ones, so the back slopes down to the tail and the
neck rises nearly vertical - the outline is a diagonal and a column, and its head ends up higher
than anything else in the land.

**THE COAT IS A HUE FLIP FROM THE CANOPY, MEASURED.** The plateau is `jungle_leaves` (73,103,27),
so a green animal is the green-turtle mistake: `brown_wool` is 53 RGB from the leaves and
`gray_wool` 58 - both vanish. The ladder is `gray_wool` 67 / `light_gray_wool` 141 / `white_wool`
236, which is 74 and 95 of luminance a rung against the ~15 below which a tone stops being a tone,
and the flank sits 134 RGB clear of the leaves it stands against.

**COUNTERSHADED OFF THE BUILT FORM, NEVER A COMPUTED RADIUS.** `relax` and a sweep both move a
surface, so the belly line is read back out of the finished columns - the same rule that stopped a
lion's mane shipping as seven floating fragments, and the reason a pale band round a sitting cat's
knees was a bug rather than a choice.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import Ctx

#: Every entry cheap, on the 1.19 server, spendable and non-falling - `tests/test_sauropod.py`
#: asks the registry rather than trusting this list.
HIDE = {
    "back": "gray_wool",          # L67
    "flank": "light_gray_wool",   # L141
    "belly": "white_wool",        # L236
    "mark": "brown_wool",         # the blotching, and the one warm note
    "eye": "black_wool",
    "eye_ring": "white_wool",
    "claw": "bone_block",
    "crest": "light_gray_wool",
}

#: +f is FORWARD, toward the head. `park._Frame`'s convention, so a facing bug is one bug.
_STEP = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}

SAUROPOD = {
    "kind": "brachiosaur",
    "at": None,                  # [V, U] - between the front feet
    "anchor": [97500, 203, 80300],
    "under": None,               # the world it stands on, so the feet find real ground
    "facing": "west",            # the way it LOOKS
    "height": 34,                # crown of the head above the feet
    "scale": 1.0,
    "ground": True,              # seat the feet on the world's own surface
    "seed": 0,
    "title": "THE SAUROPOD",
}


# --------------------------------------------------------------------------- the frame


class _Frame:
    """The animal's own axes, so every part is written in (forward, side, up).

    THE BEARING CONVENTION IS THE ONE THING A RENDER CANNOT CHECK - our raycaster draws a facing
    and its opposite identically, which is how the stair convention got got wrong twice in one
    session. One frame, one bug.
    """

    def __init__(self, c: Canvas, cv: int, cu: int, facing: str):
        if facing not in _STEP:
            raise ValueError(f"a sauropod needs a real facing, not {facing!r}")
        self.c, self.cv, self.cu = c, cv, cu
        self.fx, self.fz = _STEP[facing]
        self.sx, self.sz = -self.fz, self.fx
        self.facing = facing
        self.placed = 0
        self.refused = 0
        #: **THE CELLS THE COAT PASS MAY NOT REPAINT, BY COORDINATE.** Keyed on MATERIAL instead,
        #: this protected every cell made of that material - and the crest is `light_gray_wool`,
        #: which is also the flank the whole animal is swept in, so the countershading skipped all
        #: 2,333 cells and the sauropod shipped monochrome with a tally of four zeros. It is the
        #: same mistake as answering rule 15 with a material list (`gen/claimrow.py`), one level
        #: down: a set of things is not a set of cells.
        self.fixed: set = set()

    def at(self, f, s):
        return (self.cv + self.fx * f + self.sx * s, self.cu + self.fz * f + self.sz * s)

    def put(self, f, s, y, key, protect=False) -> bool:
        v, u = self.at(int(round(f)), int(round(s)))
        y = int(round(y))
        if not (0 <= v < self.c.sx and 0 <= u < self.c.sz and 0 <= y < self.c.sy):
            self.refused += 1
            return False
        self.c.put(v, y, u, self.c.state(HIDE.get(key, key)))
        if protect:
            self.fixed.add((v, y, u))
        self.placed += 1
        return True

    def surface_s(self, f, y, limit=6):
        """The outermost cell of the animal at this station - **FOUND, NOT COMPUTED.**

        A sweep moves a surface, so an eye placed at a calculated half-width either floats proud of
        the head or is buried a cell inside it. Both have shipped on this island's animals; the
        recorded fix is to read the built form back, and the axolotl's eye is the FRONTMOST body
        cell of its own band for exactly this reason.
        """
        for s in range(limit, 0, -1):
            v, u = self.at(int(round(f)), s)
            yy = int(round(y))
            if not (0 <= v < self.c.sx and 0 <= u < self.c.sz and 0 <= yy < self.c.sy):
                continue
            if self.c.solid(v, yy, u):
                return s
        return None


def _ball(fr: _Frame, f, s, y, r, key="flank") -> int:
    """One sphere of the sweep. **THE CENTRE IS KEPT OFF THE HALF-CELL** - `round()` is banker's
    rounding, so a centre landing on x.5 skips every other column and a swept limb comes out as a
    row of separate towers. The ladybird's clod shipped exactly that."""
    n = 0
    ri = int(math.ceil(r))
    for df in range(-ri, ri + 1):
        for ds in range(-ri, ri + 1):
            for dy in range(-ri, ri + 1):
                if df * df + ds * ds + dy * dy > r * r:
                    continue
                if fr.put(f + df, s + ds, y + dy, key):
                    n += 1
    return n


def _sweep(fr: _Frame, a, b, ra, rb, key="flank", step=0.34) -> int:
    """A tapered capsule from a to b, each a (forward, side, up) triple.

    **STEP FINE ENOUGH THAT THE SPHERES OVERLAP.** A sweep whose cells are only diagonal
    neighbours is not 6-connected, and the ear tips of two different animals broke off that way
    before the rule was written down.
    """
    d = math.dist(a, b)
    n = max(2, int(d / max(0.05, step)) + 1)
    out = 0
    for i in range(n + 1):
        t = i / n
        f = a[0] + (b[0] - a[0]) * t
        s = a[1] + (b[1] - a[1]) * t
        y = a[2] + (b[2] - a[2]) * t
        out += _ball(fr, f, s, y, ra + (rb - ra) * t, key)
    return out


# --------------------------------------------------------------------------- the animal


def _legs(fr: _Frame, d: dict) -> dict:
    """Four columnar legs, and the front pair LONGER than the back.

    That is the brachiosaur's whole profile: it tilts the spine so the back falls away to the tail
    and the neck leaves from the highest point of the animal. A level-backed sauropod is a log.

    **AND A LEG TAPERS.** The cats were retired for constant-width posts at the extreme corners -
    "why does your jaguar have four table legs" - so the thigh is thick, the cannon is slim and the
    foot spreads again, which is also what a graviportal limb actually does.
    """
    out = {}
    fh, bh = d["shoulder"], d["hip"]
    for name, f, y1, rt, rb in (("fore", d["fore_f"], fh, 2.5, 1.7),
                                ("hind", d["hind_f"], bh, 2.9, 1.9)):
        cells = 0
        for s in (d["stance"], -d["stance"]):
            cells += _sweep(fr, (f, s, y1), (f, s, y1 * 0.42), rt, rb * 1.05, "flank")
            cells += _sweep(fr, (f, s, y1 * 0.42), (f, s, 1.2), rb, rb * 0.92, "flank")
            # the foot: a spread pad, because a column that stops in mid-air reads as a peg
            cells += _ball(fr, f, s, 0.6, rb * 1.35, "flank")
            cells += _ball(fr, f, s, 0.0, rb * 1.15, "flank")
        out[name] = cells
    return out


def _body(fr: _Frame, d: dict) -> int:
    """The barrel: a SPINDLE, widest between the shoulder and the hip and tapering to both.

    A constant-depth body is the jaguar's recorded failure - "the outline is a constant-depth
    rectangle, so the animal has no centre of gravity". Here the depth is a real curve and the
    spine falls from the withers to the hip, which is what makes the profile a diagonal.
    """
    fh, bh = d["shoulder"], d["hip"]
    chest, hip = d["chest_f"], d["hip_f"]
    n = 0
    steps = 22
    prev = None
    for i in range(steps + 1):
        t = i / steps
        f = chest + (hip - chest) * t
        y = fh + (bh - fh) * t
        # widest at 0.45 of the way back, which is where a sauropod's ribcage actually is
        w = d["body_r"] * (0.62 + 0.38 * math.sin(math.pi * min(1.0, (t + 0.12) / 1.12)))
        node = (f, 0.0, y)
        if prev is not None:
            n += _sweep(fr, prev[0], node, prev[1], w, "flank", step=0.3)
        prev = (node, w)
    return n


def _neck(fr: _Frame, d: dict) -> dict:
    """The neck, and it is the whole animal.

    **IT RISES STEEPLY AND IT TAPERS.** A neck that leaves the shoulder at forty degrees reads as a
    ramp; the giraffe works here because its neck is a COLUMN, and a brachiosaur's is more vertical
    still. The rise is eased (t ** 0.78) so the base sweeps out of the withers rather than kinking
    off it - a kink at the shoulder is the one thing that makes a swept neck look stuck on.
    """
    fh = d["shoulder"]
    f0, y0 = d["chest_f"] - 0.5, fh + d["body_r"] * 0.55
    reach, rise = d["neck_f"], d["head_y"] - y0
    n, steps = 0, 26
    prev = None
    for i in range(steps + 1):
        t = i / steps
        f = f0 + reach * (t ** 1.25)
        y = y0 + rise * (t ** 0.78)
        r = d["neck_r0"] + (d["neck_r1"] - d["neck_r0"]) * t
        node = (f, 0.0, y)
        if prev is not None:
            n += _sweep(fr, prev[0], node, prev[1], r, "flank", step=0.28)
        prev = (node, r)
    return {"cells": n, "tip": prev[0]}


def _head(fr: _Frame, d: dict, tip) -> dict:
    """A small blunt head with the nasal crest that names the genus, and one eye a side.

    **AN EYE IS A BEAD, NOT A BAR, AND IT IS RINGED.** A two-cell eye reads as a stripe and an eye
    the same tone as the coat is invisible - both are recorded failures on this island's animals.
    """
    f0, _, y0 = tip
    n = 0
    n += _sweep(fr, (f0, 0, y0), (f0 + 2.6, 0, y0 + 0.35), 1.5, 1.7, "flank", step=0.25)
    n += _sweep(fr, (f0 + 2.6, 0, y0 + 0.35), (f0 + 4.4, 0, y0 - 0.2), 1.6, 1.05, "flank",
                step=0.25)
    # the crest: a raised arch over the nostrils, and the one feature that says brachiosaur
    crest = 0
    for df in range(-1, 2):
        for ds in (-1, 0, 1):
            if fr.put(f0 + 2.4 + df, ds, y0 + 2.0, "crest", protect=True):
                crest += 1
    for ds in (-1, 0, 1):
        if fr.put(f0 + 2.4, ds, y0 + 2.7, "crest", protect=True):
            crest += 1
    # **AN EYE IS A BEAD ON THE SURFACE, AND ITS RING IS QUIET.** The first build put a five-cell
    # white ring on a head 3 wide - a clown patch, and 169 points of luminance against a coat that
    # needs 35 to read. `light_gray_wool` is 74 clear of the back and disappears at distance while
    # the bead still reads, which is what a ring is for.
    eyes = 0
    for sign in (1, -1):
        edge = fr.surface_s(f0 + 2.2, y0 + 0.9)
        if edge is None:
            continue
        s = sign * edge
        if fr.put(f0 + 2.2, s, y0 + 0.9, "eye", protect=True):
            eyes += 1
        for df, dy in ((0, 1), (0, -1)):
            fr.put(f0 + 2.2 + df, s, y0 + 0.9 + dy, "eye_ring", protect=True)
    return {"cells": n, "crest": crest, "eyes": eyes}


def _tail(fr: _Frame, d: dict) -> dict:
    """The tail: as long as the neck, sweeping back and DOWN and then levelling to a whip.

    It is the counterweight, and in the silhouette it is what stops the animal reading as a giraffe
    - a giraffe's tail is a string, a sauropod's is half the outline.
    """
    bh = d["hip"]
    f0, y0 = d["hip_f"] + 0.5, bh + d["body_r"] * 0.3
    n, steps = 0, 30
    prev = None
    for i in range(steps + 1):
        t = i / steps
        f = f0 - d["tail_f"] * t
        y = y0 - (y0 - d["tail_y"]) * (t ** 1.5)
        r = d["tail_r0"] * (1.0 - t) ** 1.35 + 0.55
        node = (f, 0.0, y)
        if prev is not None:
            n += _sweep(fr, prev[0], node, prev[1], r, "flank", step=0.26)
        prev = (node, r)
    return {"cells": n, "tip": prev[0]}


def _coat(c: Canvas, fixed: set, seed: int) -> dict:
    """Countershading and blotches, read off the BUILT form.

    **THE BELLY LINE IS MEASURED, NEVER COMPUTED.** Anything derived from a nominal radius drifts
    off the surface a sweep actually produced - the mane came off as seven floating fragments and
    the ossicones detached before this rule existed. Every column is asked where its own top and
    bottom are.
    """
    back = c.state(HIDE["back"])
    flank = c.state(HIDE["flank"])
    belly = c.state(HIDE["belly"])
    mark = c.state(HIDE["mark"])
    tally = {"back": 0, "flank": 0, "belly": 0, "mark": 0}
    for v in range(c.sx):
        for u in range(c.sz):
            ys = [y for y in range(c.sy) if c.solid(v, y, u)]
            if not ys:
                continue
            lo, hi = ys[0], ys[-1]
            span = max(1, hi - lo)
            for y in ys:
                if (v, y, u) in fixed:
                    continue
                t = (y - lo) / span
                if t < 0.22:
                    c.put(v, y, u, belly)
                    tally["belly"] += 1
                elif t > 0.70:
                    # the blotching goes on a COARSE lattice, or it is confetti - the rule the
                    # deck soffit and the Lowland Thicket both had to be rebuilt for.
                    if hash01(v // 3, u // 3, y // 3, seed + 5) < 0.26:
                        c.put(v, y, u, mark)
                        tally["mark"] += 1
                    else:
                        c.put(v, y, u, back)
                        tally["back"] += 1
                else:
                    c.put(v, y, u, flank)
                    tally["flank"] += 1
    return tally


# --------------------------------------------------------------------------- entry point


def _dims(height: float) -> dict:
    """Every measurement as a fraction of the crown height, so ONE number scales the animal.

    Per-species absolutes are what this repo's animal work spent a year unlearning: "anything in
    absolute blocks has this latent", and a tail hardcoded at 13 blocks was once longer than a
    deer's legs.
    """
    H = float(height)
    return {
        "shoulder": H * 0.52,
        "hip": H * 0.42,
        "fore_f": H * 0.16,
        "hind_f": -H * 0.20,
        "chest_f": H * 0.24,
        "hip_f": -H * 0.26,
        "stance": max(2.0, H * 0.095),
        "body_r": H * 0.115,
        "neck_f": H * 0.24,
        "neck_r0": H * 0.075,
        "neck_r1": H * 0.040,
        "head_y": H * 0.94,
        "tail_f": H * 0.62,
        "tail_y": H * 0.10,
        "tail_r0": H * 0.085,
    }


def build(cfg: dict, donors=None) -> Canvas:
    p = {**SAUROPOD, **(cfg or {})}
    H = float(p.get("height") or 34) * float(p.get("scale") or 1.0)
    if H < 18:
        raise ValueError("a sauropod under 18 blocks cannot carry a neck, a tail and four legs; "
                         "its identity is the SILHOUETTE and there is nothing left of it")
    d = _dims(H)
    seed = int(p.get("seed", 0))
    # the box: tail tip to head, plus the stance, plus a margin the sweep can round into
    span_back = d["tail_f"] + abs(d["hip_f"]) + 6
    span_fore = d["chest_f"] + d["neck_f"] + 10
    length = int(span_back + span_fore)
    width = int(d["stance"] * 2 + d["body_r"] * 2 + 8)
    sy = int(H + 6)
    facing = str(p.get("facing", "west"))
    if facing not in _STEP:
        raise ValueError(f"a sauropod needs a real facing, not {facing!r}")
    # **THE CANVAS IS SIZED BY THE FACING, NOT BY THE ANIMAL.** A box that is always long in X is
    # long in the WRONG axis for a north-south animal: built facing north the sauropod came out
    # clipped to 22 blocks - head, neck and half the tail simply refused - and the only symptom was
    # a refusal count nobody was reading. The frame maps forward and side onto the world; the box
    # has to be mapped the same way or the two disagree.
    along_x = facing in ("east", "west")
    sx = length if along_x else width
    sz = width if along_x else length
    c = Canvas(sx, sy, sz, donors)
    cv = int(span_back) if along_x else sx // 2
    cu = sz // 2 if along_x else int(span_back)
    if facing == "east":
        cv = sx - int(span_back)
    if facing == "south":
        cu = sz - int(span_back)
    fr = _Frame(c, cv, cu, facing)

    parts = {"legs": _legs(fr, d), "body": _body(fr, d)}
    neck = _neck(fr, d)
    parts["neck"] = neck["cells"]
    parts["head"] = _head(fr, d, neck["tip"])
    tail = _tail(fr, d)
    parts["tail"] = tail["cells"]
    parts["coat"] = _coat(c, fr.fixed, seed)

    at_v, at_u = (int(x) for x in (p.get("at") or (0, 0)))
    ax, ay, az = (int(x) for x in p["anchor"])
    y = ay
    if p.get("ground") and p.get("under"):
        # THE FEET FIND REAL GROUND. A landmark seated on a nominal plane sinks into a rise or
        # hovers over a fall, and this land's ground rolls.
        ctx = Ctx(p["under"])
        x0, z0 = ax + at_v, az + at_u
        for probe in range(ay + 8, ay - 12, -1):
            n = ctx.name_at(x0, probe, z0).split(":")[-1]
            if n not in ("air", "cave_air", "void_air", "moss_carpet"):
                y = probe + 1
                break
    c.world_origin = (ax + at_v - fr.cv, y, az + at_u - fr.cu)
    c.meta = {
        "kind": "sauropod",
        "land": "frontier",
        "facing": p.get("facing", "west"),
        "height": round(H, 1),
        "profile_axis": "u" if p.get("facing") in ("east", "west") else "v",
        "refused": fr.refused,
        "parts": parts,
        "contract": (
            "a brachiosaur: four columnar tapered legs with the FRONT pair longer, a spindle "
            "barrel whose back falls away to the hip, a neck that rises nearly vertical to a "
            "crested head, and a tail as long as the neck. One piece, countershaded off its own "
            "built form, and every tone a measured hue flip from the canopy it stands against."),
    }
    return c
