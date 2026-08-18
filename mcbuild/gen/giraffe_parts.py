"""The giraffe's parts. Split out of `giraffe.py` only to keep each file readable.

Build order matters and is the whole point of the split:

    the solid MASS   legs, body, neck, skull - lofted, nothing thin, nothing coloured
    relax            cellular smoothing over that mass alone (see `smooth.py`)
    thin features    mane, ears, ossicones, tail - added AFTER, because the same rule that shaves a
                     one-block pimple off a shoulder would eat an ossicone whole
    the face         read off the SMOOTHED surface, never assumed from a radius
"""
from __future__ import annotations

AIRY = ("air", "cave_air", "void_air", "vine")


def lerp(keys, t: float):
    """Piecewise-linear through (t, value...) keyframes."""
    if t <= keys[0][0]:
        return keys[0][1:]
    for (t0, *v0), (t1, *v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return tuple(a + (b - a) * u for a, b in zip(v0, v1))
    return keys[-1][1:]


def disc(hide: set, cx, cy, cz, f, s, r_along, r_across, n: float):
    """A horizontal superellipse section - where the spine runs vertically (legs, neck)."""
    ra, rb = max(0.5, r_along), max(0.5, r_across)
    for a in range(-int(ra + 1), int(ra + 2)):
        for b in range(-int(rb + 1), int(rb + 2)):
            if (abs(a) / ra) ** n + (abs(b) / rb) ** n > 1.0:
                continue
            hide.add((int(round(cx + f[0] * a + s[0] * b)), int(round(cy)),
                      int(round(cz + f[1] * a + s[1] * b))))


def rib(hide: set, cx, cy, cz, f, s, r_across, r_up, n: float, squash_lo: float = 1.0):
    """A vertical superellipse section ACROSS the heading - where the spine runs horizontally.

    `squash_lo` flattens the underside, which is what gives a belly rather than a tube."""
    rb, rv = max(0.5, r_across), max(0.5, r_up)
    for b in range(-int(rb + 1), int(rb + 2)):
        for k in range(-int(rv + 2), int(rv + 2)):
            rr = rv * (squash_lo if k < 0 else 1.0)
            if (abs(b) / rb) ** n + (abs(k) / max(0.5, rr)) ** n > 1.0:
                continue
            hide.add((int(round(cx + s[0] * b)), int(round(cy)) + k, int(round(cz + s[1] * b))))


# ------------------------------------------------------------------ mass

def legs(hide: set, ctx, fx, fy, fz, f, s, p) -> list:
    """Four legs, each finding its OWN ground - the isle rolls, and a level hoof line either floats
    on the high side or buries its feet on the low.

    The top of each leg flares hard and carries three courses UP INTO the barrel, so a leg meets the
    body as a haunch instead of as a post pushed into a wall; `relax` then blends that corner. This
    is what stops the legs reading as four sticks stapled on.

    Returns (x, z, ground_y, radius) per leg so hooves can be coloured after smoothing.
    """
    bl, br, lr = int(p["body_len"]), float(p["body_r"]), float(p["leg_r"])
    n = float(p["section_n"])
    top = fy + int(p["leg"])
    # (t up the leg, half-width). t=1 is the hoof, t=0 the haunch.
    KEYS = [(0.00, lr + 1.6), (0.05, lr + 0.9), (0.15, lr + 0.15), (0.46, lr - 0.3),
            (0.76, lr + 0.05), (1.00, lr + 0.4)]
    out = []
    for along, side in ((bl // 2 - 3, 1), (bl // 2 - 3, -1), (-(bl // 2 - 3), 1), (-(bl // 2 - 3), -1)):
        off = max(1, round(br - lr - 0.4))          # tucked under the barrel, not splayed past it
        lx = int(fx + f[0] * along + s[0] * off * side)
        lz = int(fz + f[1] * along + s[1] * off * side)
        hoof = fy
        if ctx is not None:
            for probe in range(fy + 6, fy - 8, -1):
                if ctx.name_at(lx, probe, lz) not in AIRY:
                    hoof = probe + 1
                    break
        span = max(1, top - hoof)
        for y in range(hoof, top + 4):              # +4: carry the haunch up inside the body
            t = max(0.0, 1.0 - (y - hoof) / span)
            (r,) = lerp(KEYS, t)
            disc(hide, lx, y, lz, f, s, r, r, n)
        out.append((lx, lz, hoof, lr + 0.8))
    return out


def body(hide: set, fx, belly, fz, f, s, p) -> tuple:
    """A barrel whose back falls away from the withers. Returns where the neck rises from.

    Back line and belly line are set independently: the back drops steeply while the belly stays near
    level, so the body deepens toward the chest the way an animal does."""
    bl, br = int(p["body_len"]), float(p["body_r"])
    withers, hips = float(p["withers"]), float(p["hips"])
    n = float(p["section_n"])
    half = bl // 2
    # t: 0 at the rump, 1 at the chest. (half-width, back height above the belly)
    KEYS = [(0.00, br - 2.1, hips - 1.3), (0.08, br - 1.0, hips - 0.2),
            (0.22, br - 0.2, hips + 0.9), (0.45, br, hips + (withers - hips) * 0.5),
            (0.72, br, withers), (0.88, br - 0.4, withers), (1.00, br - 1.6, withers - 1.3)]
    for a in range(-half, bl - half):
        t = (a + half) / max(1, bl - 1)
        rb, back = lerp(KEYS, t)
        rib(hide, fx + f[0] * a, belly + back / 2.0, fz + f[1] * a, f, s,
            rb, back / 2.0, n, squash_lo=1.12)
    return (fx + f[0] * (half - 2), belly + withers - 1.0, fz + f[1] * (half - 2))


def neck(hide: set, shoulder, f, s, p):
    """A long neck that tapers smoothly and leans forward.

    The lean is carried as a FLOAT and the section re-centred every course, so the neck is a clean
    diagonal rather than the staircase that stepping a whole box produces. It also starts two courses
    down INSIDE the shoulder mass, so there is no seam where it leaves the body."""
    sx, sy, sz = shoulder
    ln, r0, r1 = int(p["neck"]), float(p["neck_r0"]), float(p["neck_r1"])
    n, lean = float(p["section_n"]), float(p["neck_lean"])
    KEYS = [(0.00, r0 + 1.9), (0.05, r0 + 0.9), (0.15, r0),
            (0.50, r0 - (r0 - r1) * 0.5), (1.00, r1)]
    x, z = float(sx), float(sz)
    top = (sx, sy, sz)
    for k in range(-3, ln):
        t = max(0.0, k / max(1, ln - 1))
        (r,) = lerp(KEYS, t)
        x += f[0] * lean
        z += f[1] * lean
        disc(hide, x, sy + k, z, f, s, r, r * 0.94, n)
        top = (x, sy + k, z)
    return top, lerp(KEYS, 1.0)[0]


def head(hide: set, top, neck_r, f, s, p) -> tuple:
    """The skull, lofted along the muzzle - six keyframes from cranium to nose.

    It starts at the NECK's own radius so the join is continuous: an early version stepped from 9
    cells to 34 in one course and read as a pinhead on a stick. The muzzle keeps its DEPTH to the
    nose, because tapering the height away gives a giraffe a beak."""
    hx, hy, hz = top
    hl, hr, n = int(p["head_len"]), float(p["head_r"]), float(p["section_n"])
    KEYS = [(0.00, max(neck_r, hr - 1.0), 0.4, hr - 0.2),
            (0.20, hr, 0.5, hr + 0.15),
            (0.42, hr - 0.05, 0.1, hr - 0.1),
            (0.65, hr - 0.5, -0.5, hr - 0.45),
            (0.88, hr - 0.85, -1.0, hr - 0.7),
            (1.00, hr - 0.95, -1.25, hr - 0.8)]
    brow = (hx, hz)
    for i in range(hl):
        t = i / max(1, hl - 1)
        rb, dy, rv = lerp(KEYS, t)
        cx, cz = hx + f[0] * i, hz + f[1] * i
        rib(hide, cx, hy + dy, cz, f, s, rb, rv, n, squash_lo=0.92)
        if abs(t - 0.42) < 0.5 / hl:
            brow = (cx, cz)
    return (hx, hy, hz, hl, hr, brow[0], brow[1])


# ------------------------------------------------------------------ thin features (post-relax)

def mane(hide: set, shoulder, f, s, p):
    """A ridge down the BACK of the neck, laid one cell behind whatever the surface actually is.

    It must be measured, not calculated: `relax` shrinks the neck, so a mane placed at the pre-relax
    radius hangs in the air. That is precisely what happened - the mane came out as seven floating
    fragments stepping diagonally up the back of the neck, each one its own component.
    """
    sx, sy, sz = shoulder
    ln = int(p["neck"])
    reach = int(p["neck_r0"]) + 3
    for k in range(ln - 1):
        y = int(round(sy + k))
        # walk FORWARD from well behind the neck until the surface is found, then sit just behind it
        back = None
        for d in range(reach, 0, -1):
            probe = (int(round(sx - f[0] * d)), y, int(round(sz - f[1] * d)))
            if probe in hide:
                back = probe
                break
        if back is None:
            continue
        hide.add((int(back[0] - f[0]), y, int(back[2] - f[1])))


def crown(hide: set, accent: dict, head_at, f, s, p):
    """Ears and ossicones, GROWN OUT OF the smoothed skull rather than placed at a guessed radius.

    Relax changes the head's surface, so anything positioned from the pre-relax radius can end up
    hanging in the air: the first attempt left six disconnected components - two ears and two
    ossicones floating a block off the head. Both now start from a cell that is actually there.
    """
    hx, hy, hz, _hl, hr, _bx, _bz = head_at
    for side in (1, -1):
        # ear: find the skull's outer surface at ear height, then sweep outward, back and down
        for a in (-1, 0, 1):
            anchor = None
            for b in range(int(hr) + 2, 0, -1):
                c = (int(round(hx + f[0] * (a + 1) + s[0] * b * side)), int(round(hy + 1)),
                     int(round(hz + f[1] * (a + 1) + s[1] * b * side)))
                if c in hide:
                    anchor = (b, c)
                    break
            if anchor is None:
                continue
            b0 = anchor[0]
            # A CONTIGUOUS outward run at one height, starting from the surface cell. Sweeping the
            # ear back and down as it went out made consecutive cells diagonal neighbours, which is
            # not connected under the 6-connectivity the audit uses - the tips broke off.
            for dyk in (0, 1):
                if dyk and a == 1:
                    continue                        # the outer row is one course, so it tapers
                # Two cells out, not three. Making the run contiguous fixed the broken tips but left
                # an ear reaching 3 clear of a skull only ~5 wide - from the front they read as wings.
                for b in range(1, 3 if a != 1 else 2):
                    c = (int(round(hx + f[0] * (a + 1) + s[0] * (b0 + b) * side)),
                         int(round(hy + 1 + dyk)),
                         int(round(hz + f[1] * (a + 1) + s[1] * (b0 + b) * side)))
                    hide.add(c)
                    accent[c] = p["coat_block"]
        # ossicone: stand it on the actual top of the skull at that column
        ox = int(round(hx + f[0] * 2 + s[0] * 1.2 * side))
        oz = int(round(hz + f[1] * 2 + s[1] * 1.2 * side))
        crest = max((c[1] for c in hide if c[0] == ox and c[2] == oz), default=None)
        if crest is None:
            continue
        for k in (1, 2):
            hide.add((ox, crest + k, oz))
            accent[(ox, crest + k, oz)] = p["coat_block"]
        knob = (ox, crest + 3, oz)
        hide.add(knob)
        accent[knob] = p["dark"]


def face(hide: set, accent: dict, head_at, f, s, p):
    """Pale muzzle, nostrils and eyes - read off the SMOOTHED surface, never assumed."""
    hx, hy, hz, hl, hr, ax, az = head_at
    nose_x = int(round(hx + f[0] * (hl - 1)))
    nose_z = int(round(hz + f[1] * (hl - 1)))
    for c in list(hide):
        along = (c[0] - hx) * f[0] + (c[2] - hz) * f[1]
        # the LOWER front of the face only: a giraffe has a pale lip, not a pale slab on its nose
        if along >= hl - 3 and c[1] <= hy:
            accent[c] = p["muzzle"]
    for b in (-1, 0, 1):
        for dy in (-1, 0):
            c = (int(nose_x + s[0] * b), int(round(hy + dy - 1)), int(nose_z + s[1] * b))
            if c in hide and abs(b) + abs(dy) < 2:
                accent[c] = p["dark"]
    for side in (1, -1):
        # eye: a dark bead on the OUTER SURFACE of the brow. Walk outward and take the first cell
        # that is really there - assuming a width merged both eyes into a band across the face.
        for k in (0, 1):
            y = int(round(hy + k))
            edge = None
            for b in range(int(hr) + 2, 0, -1):
                c = (int(ax + s[0] * b * side), y, int(az + s[1] * b * side))
                if c in hide:
                    edge = c
                    break
            if edge is None:
                continue
            accent[edge] = p["dark"]
            for dy in (-1, 2):
                ring = (edge[0], int(round(hy + dy)), edge[2])
                if ring in hide and ring not in accent:
                    accent[ring] = p["muzzle"]


def tail(hide: set, accent: dict, fx, belly, fz, f, s, p):
    """A tail with a switch on the end. One block wide it is invisible - the rump slice held exactly
    11 cells and the render showed nothing at all."""
    half = int(p["body_len"]) // 2
    x = int(fx - f[0] * (half + 1))
    z = int(fz - f[1] * (half + 1))
    top = int(belly + int(p["hips"]) - 2)
    for k in range(13):
        cells = [(x, top - k, z)]
        if k < 3:
            cells.append((int(x - f[0]), top - k, int(z - f[1])))
        if 9 <= k < 12:
            cells += [(int(x + s[0] * b), top - k, int(z + s[1] * b)) for b in (-1, 1)]
        for c in cells:
            hide.add(c)
            if k >= 9:
                accent[c] = p["dark"]
