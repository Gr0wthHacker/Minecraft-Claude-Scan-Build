"""Sweeping solid shapes along a spine, and finding the surface of what you swept.

The primitives every organic build in this repo now uses:

    lerp(keys, t)          piecewise-linear through keyframes - the shape of a part, as a table
    disc(...)              a HORIZONTAL superellipse section, where the spine runs vertically
    rib(...)               a VERTICAL section across the heading, where the spine runs horizontally
    surface_out(...)       walk outward until you hit the skin, and return that cell
    crest(...)             the top of a column

    Frame(canvas, ...)     an animal's own (forward, side, up) axes on a Canvas
    r(v)                   round HALF AWAY FROM ZERO - `round()` skips alternate columns
    ball / sweep / thread  a sphere, a tapered capsule, and a guaranteed-connected core

The second group came out of `gen/stegosaur.py`, which needed all of it and was about to be copied
wholesale into a second animal. Every one of them carries a bug this repo has already paid for
once, so a private second copy is a second place for those bugs to come back.

Why lofting rather than stacking boxes: an integer half-width holds for several courses and then
steps, so a stack of boxes has a measurable plateau-then-jump signature. A float radius shrinks a
little every course, and the superellipse exponent rounds off the corners a filled rectangle always
has. `n=2` is an ellipse, large `n` is a rectangle; 2.0-2.4 reads as an animal that still looks built.

Why `surface_out` and `crest` matter more than they look: anything placed at a CALCULATED radius is
wrong the moment the shape is smoothed, because smoothing moves the surface. Eyes ended up as a band
across the face, the mane came off as seven floating fragments, and the ossicones and ears detached
entirely - all the same bug. Measure the skin, never assume where it is.
"""
from __future__ import annotations

import math


def lerp(keys, t: float):
    """Piecewise-linear through (t, value...) keyframes. Values are tuples of floats."""
    # always a TUPLE - the clamped branches used to return the keyframe's own list, so the return
    # type depended on where t fell. Every caller unpacks, so it never broke; it would have.
    if t <= keys[0][0]:
        return tuple(keys[0][1:])
    for (t0, *v0), (t1, *v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return tuple(a + (b - a) * u for a, b in zip(v0, v1))
    return tuple(keys[-1][1:])


def disc(hide: set, cx, cy, cz, f, s, r_along, r_across, n: float):
    """A horizontal superellipse section - for a spine that runs vertically (legs, neck)."""
    ra, rb = max(0.5, r_along), max(0.5, r_across)
    for a in range(-int(ra + 1), int(ra + 2)):
        for b in range(-int(rb + 1), int(rb + 2)):
            if (abs(a) / ra) ** n + (abs(b) / rb) ** n > 1.0:
                continue
            hide.add((int(round(cx + f[0] * a + s[0] * b)), int(round(cy)),
                      int(round(cz + f[1] * a + s[1] * b))))


def rib(hide: set, cx, cy, cz, f, s, r_across, r_up, n: float, squash_lo: float = 1.0):
    """A vertical superellipse section ACROSS the heading - for a horizontal spine (body, head).

    `squash_lo` scales the lower half only, which is what turns a tube into something with a belly."""
    rb, rv = max(0.5, r_across), max(0.5, r_up)
    for b in range(-int(rb + 1), int(rb + 2)):
        for k in range(-int(rv + 2), int(rv + 2)):
            rr = rv * (squash_lo if k < 0 else 1.0)
            if (abs(b) / rb) ** n + (abs(k) / max(0.5, rr)) ** n > 1.0:
                continue
            hide.add((int(round(cx + s[0] * b)), int(round(cy)) + k, int(round(cz + s[1] * b))))


def surface_out(hide: set, cx, cy, cz, dx, dz, reach: int):
    """Walk outward from a centre and return the OUTERMOST cell that exists, with its distance.

    Use this for anything that sits on a surface - an eye, an ear, a mane, a fin. Placing such a
    thing at a computed radius breaks as soon as the shape is relaxed, because relaxing moves the
    surface; every detached-feature bug in this repo has been that mistake.
    """
    for b in range(reach, 0, -1):
        c = (int(round(cx + dx * b)), int(round(cy)), int(round(cz + dz * b)))
        if c in hide:
            return c, b
    return None, 0


def crest(hide: set, x, z):
    """The highest cell in a column, or None. What to stand a horn or a crest on."""
    ys = [c[1] for c in hide if c[0] == x and c[2] == z]
    return max(ys) if ys else None


# --------------------------------------------------------------- the animal's own frame


def r(v: float) -> int:
    """Round HALF AWAY FROM ZERO, which `round()` does not do and `int()` does not either.

    **`round()` IS BANKER'S ROUNDING AND IT SKIPS ALTERNATE COLUMNS.** `round(4.5) == 4` while
    `round(5.5) == 6`, so a sphere swept about a centre landing on x.5 fills one column, misses
    the next and fills the one after. A stegosaur's legs stand at 0.150 of its length, which at
    length 30 is exactly 4.5: every foot came out as a COMB of separate pads, four feet read as
    eight, and only the ground course's own component count could see it. The ladybird shipped the
    same bug as eighteen one-wide towers where a clod should have been.

    Away from zero rather than toward +inf, because the SIDE axis is signed about the sagittal
    plane: `floor(v + 0.5)` sends 2.5 to 3 and -2.5 to -2, a shape one cell wider on one flank -
    which is the squid's own 5,375-cell mirror fault arrived at from a different direction.
    """
    return int(math.floor(v + 0.5)) if v >= 0 else -int(math.floor(-v + 0.5))


#: +f is FORWARD, toward the head - `gen/park.py`'s convention, so a facing bug is one bug.
STEP = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


class Frame:
    """An animal's own axes on a Canvas, so every part is written in (forward, side, up).

    THE BEARING CONVENTION IS THE ONE THING A RENDER CANNOT CHECK - the raycaster draws a facing
    and its opposite identically until `render3d.subdivide` expands a stair, which is how the stair
    convention got got wrong twice in one session. One frame, one bug.

    `hide` is the material lookup the caller passes: `put` takes a KEY, so a generator names what a
    cell is for rather than what it is made of, and a palette change is one table.
    """

    def __init__(self, c, cv: int, cu: int, facing: str, hide: dict):
        if facing not in STEP:
            raise ValueError(f"an animal needs a real facing, not {facing!r}")
        self.c, self.cv, self.cu, self.hide = c, cv, cu, hide
        self.fx, self.fz = STEP[facing]
        self.sx, self.sz = -self.fz, self.fx
        self.facing = facing
        self.placed = 0
        #: **A REFUSAL BELOW THE GROUND PLANE IS NOT THE SAME FAULT AS ONE OFF THE END.** A foot pad
        #: is a sphere centred on the course the animal stands on, so its lower half is always
        #: outside the box - that is the ground, not a clip. A refusal in f or s is the sauropod's
        #: recorded disaster: built facing north it was clipped to 22 blocks of 48, head and half
        #: the tail simply refused, and the only symptom was a refusal count nobody was reading.
        self.refused = 0
        self.clipped = 0
        #: Cells a later pass may not repaint, BY COORDINATE. Keyed on MATERIAL instead this
        #: protects every cell made of that material - the sauropod's crest is the same wool as the
        #: flank it is swept in, so its countershading skipped all 2,333 cells and it shipped
        #: monochrome with a tally of four zeros. A set of things is not a set of cells.
        self.fixed: set = set()
        #: Cells ANOTHER DESIGN owns, in this canvas's coordinates. A `put` here is declined and
        #: counted rather than clipped or refused, because it is neither a mistake nor an edge: it
        #: is this build correctly giving way. `gen/ribwalk.py` uses it so that "the causeway was
        #: cut THROUGH the skeleton" is a property of the construction rather than a number to
        #: hope for - a rib arrives at the deck, stops, and picks up again underneath.
        self.taken: set = set()
        self.declined = 0

    def at(self, f, s):
        return (self.cv + self.fx * f + self.sx * s, self.cu + self.fz * f + self.sz * s)

    def fs(self, v, u):
        """The inverse: (forward, side) for a canvas column."""
        return ((v - self.cv) * self.fx + (u - self.cu) * self.fz,
                (v - self.cv) * self.sx + (u - self.cu) * self.sz)

    def put(self, f, s, y, key, protect=False) -> bool:
        v, u = self.at(r(f), r(s))
        y = r(y)
        if not (0 <= v < self.c.sx and 0 <= u < self.c.sz and 0 <= y < self.c.sy):
            if 0 <= v < self.c.sx and 0 <= u < self.c.sz and y < 0:
                self.refused += 1
            else:
                self.clipped += 1
            return False
        if (v, y, u) in self.taken:
            self.declined += 1
            return False
        self.c.put(v, y, u, self.c.state(self.hide.get(key, key)))
        if protect:
            self.fixed.add((v, y, u))
        self.placed += 1
        return True

    def solid(self, f, s, y) -> bool:
        v, u = self.at(r(f), r(s))
        return self.c.solid(v, r(y), u)

    def top_y(self, f, s, ceiling=None):
        """The highest solid course in this column - **FOUND, NOT COMPUTED.**

        `Canvas.solid`, never `if c.get(...)`: `get` returns -1 out of bounds and -1 is TRUTHY,
        which is how the ladybird painted all seven of its spots into thin air above itself while
        the audit, the BOM and the component count all reported a clean build.
        """
        v, u = self.at(r(f), r(s))
        hi = self.c.sy - 1 if ceiling is None else min(int(ceiling), self.c.sy - 1)
        for y in range(hi, -1, -1):
            if self.c.solid(v, y, u):
                return y
        return None


def ball(fr: Frame, f, s, y, ra, key="flank", protect=False, rs=None, ry=None) -> int:
    """One ellipsoid of a sweep. `rs`/`ry` default to `ra`, which makes it a sphere."""
    rs = ra if rs is None else rs
    ry = ra if ry is None else ry
    n = 0
    for df in range(-int(math.ceil(ra)), int(math.ceil(ra)) + 1):
        for ds in range(-int(math.ceil(rs)), int(math.ceil(rs)) + 1):
            for dy in range(-int(math.ceil(ry)), int(math.ceil(ry)) + 1):
                if (df / max(0.4, ra)) ** 2 + (ds / max(0.4, rs)) ** 2 + (dy / max(0.4, ry)) ** 2 > 1.0:
                    continue
                if fr.put(f + df, s + ds, y + dy, key, protect):
                    n += 1
    return n


def sweep(fr: Frame, a, b, ra, rb, key="flank", step=0.34, protect=False) -> int:
    """A tapered capsule from a to b, each a (forward, side, up) triple.

    **STEP FINE ENOUGH THAT THE SPHERES OVERLAP.** A sweep whose consecutive cells are only
    diagonal neighbours is not 6-connected, and the ear tips of two different animals broke off
    that way before the rule was written down.
    """
    d = math.dist(a, b)
    n = max(2, int(d / max(0.05, step)) + 1)
    out = 0
    for i in range(n + 1):
        t = i / n
        out += ball(fr, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t,
                    a[2] + (b[2] - a[2]) * t, ra + (rb - ra) * t, key, protect)
    return out


def thread(fr: Frame, a, b, key="flank", protect=False, step=0.12) -> int:
    """A one-cell 6-CONNECTED core from a to b, filling every corner ONE AXIS AT A TIME.

    **A TAPER THAT ENDS UNDER ONE CELL CANNOT BE SWEPT INTO EXISTENCE.** Below about r=0.87 a
    sphere is a single cell, and two single cells whose centres moved on two axes at once are
    DIAGONAL neighbours. It cost the stegosaur its tail spikes at exactly two lengths out of seven
    and not at the one it was being looked at, and the pterosaur came apart at three separate
    spans. A step fine enough is not a guarantee, it is a hope that scales.
    """
    d = math.dist(a, b)
    n = max(2, int(d / max(0.02, step)) + 1)
    out, prev = 0, None
    for i in range(n + 1):
        t = i / n
        cell = (r(a[0] + (b[0] - a[0]) * t), r(a[1] + (b[1] - a[1]) * t),
                r(a[2] + (b[2] - a[2]) * t))
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
