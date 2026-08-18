"""Sweeping solid shapes along a spine, and finding the surface of what you swept.

The primitives every organic build in this repo now uses:

    lerp(keys, t)          piecewise-linear through keyframes - the shape of a part, as a table
    disc(...)              a HORIZONTAL superellipse section, where the spine runs vertically
    rib(...)               a VERTICAL section across the heading, where the spine runs horizontally
    surface_out(...)       walk outward until you hit the skin, and return that cell
    crest(...)             the top of a column

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


def lerp(keys, t: float):
    """Piecewise-linear through (t, value...) keyframes. Values are tuples of floats."""
    if t <= keys[0][0]:
        return keys[0][1:]
    for (t0, *v0), (t1, *v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return tuple(a + (b - a) * u for a, b in zip(v0, v1))
    return keys[-1][1:]


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
