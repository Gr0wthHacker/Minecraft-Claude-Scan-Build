"""Per-family geometry: the parts that actually differ between a bear, a cat and an elephant.

A shared loft with different NUMBERS produces one animal five times - measured, a lion and a jaguar
came out 0.032 apart on silhouette, which is to say identical. What separates them is structure the
numbers cannot reach, so structure is what lives here.

    LEGS
      digitigrade   walks on its toes: a long shin, a pinched hock, a small paw. Cats, dogs.
      plantigrade   walks on the whole foot: a column onto a LONG FLAT FOOT that projects forward.
                    This single feature is most of what makes a bear look like a bear.
      columnar      a pillar with a flared base and toenails. Elephants, rhinos.
      stubby        barely a leg at all; the body nearly touches the ground. Capybara, badger.
      cursorial     long, slender, built for standing - a giraffe or a horse.

    HEADS
      rounded       short wide cranium, short muzzle, high forehead. A cat.
      broad         a wide FLAT skull with a narrow straight muzzle projecting level from it. A bear's
                    snout is much narrower than its braincase, and that step is the read.
      domed         a high forehead over a small face. An elephant.
      blunt         a deep square box with a flat front. A capybara.
      tapered       long, narrow, gently tapering, eyes set high. A giraffe.

Each builder returns the same thing the generic one did, so `quadruped` only has to dispatch.
"""
from __future__ import annotations

from . import loft


# ------------------------------------------------------------------ legs

def leg_digitigrade(hide, lx, lz, hoof, top, f, s, lr, n, fold=1.0):
    """Toes-down: a long shin, a pinched hock about a third up, then a small paw."""
    KEYS = [[0.00, lr * fold + 1.5], [0.06, lr * fold + 0.8], [0.18, lr * fold + 0.1],
            [0.42, lr * fold - 0.35], [0.62, lr * fold - 0.45],      # the pinch at the hock
            [0.80, lr * fold - 0.10], [1.00, lr * fold + 0.25]]
    span = max(1, top - hoof)
    for y in range(hoof, top + 4):
        (r,) = loft.lerp(KEYS, max(0.0, 1.0 - (y - hoof) / span))
        loft.disc(hide, lx, y, lz, f, s, r, r, n)


def leg_plantigrade(hide, lx, lz, hoof, top, f, s, lr, n, fold=1.0):
    """Heel-down, on a LONG FLAT FOOT.

    The foot is the whole point. A bear's sole runs forward roughly half the length of its lower leg
    and sits flat on the ground; without it a bear is a brown cat, which is exactly what happened."""
    KEYS = [[0.00, lr * fold + 1.4], [0.08, lr * fold + 0.7], [0.22, lr * fold + 0.15],
            [0.55, lr * fold + 0.05], [0.85, lr * fold + 0.2], [1.00, lr * fold + 0.35]]
    span = max(1, top - hoof)
    for y in range(hoof, top + 4):
        (r,) = loft.lerp(KEYS, max(0.0, 1.0 - (y - hoof) / span))
        loft.disc(hide, lx, y, lz, f, s, r, r, n)
    # the sole: two courses, running forward from the ankle
    reach = max(2, int(round(span * 0.45)))
    for k in range(2):
        for a in range(0, reach + 1):
            t = a / max(1, reach)
            w = (lr * fold + 0.3) * (1.0 - 0.35 * t)
            loft.disc(hide, lx + f[0] * a, hoof + k, lz + f[1] * a, f, s, w * 0.9, w, n)


def leg_columnar(hide, lx, lz, hoof, top, f, s, lr, n, fold=1.0):
    """A pillar: almost no taper, a flare at the foot, and a splayed pad."""
    KEYS = [[0.00, lr * fold + 0.9], [0.15, lr * fold + 0.25], [0.55, lr * fold],
            [0.85, lr * fold + 0.25], [1.00, lr * fold + 0.75]]
    span = max(1, top - hoof)
    for y in range(hoof, top + 4):
        (r,) = loft.lerp(KEYS, max(0.0, 1.0 - (y - hoof) / span))
        loft.disc(hide, lx, y, lz, f, s, r, r, n)


def leg_stubby(hide, lx, lz, hoof, top, f, s, lr, n, fold=1.0):
    """Short and near-cylindrical - the body carries the silhouette, not the legs."""
    KEYS = [[0.00, lr * fold + 1.2], [0.25, lr * fold + 0.3], [0.75, lr * fold + 0.1],
            [1.00, lr * fold + 0.35]]
    span = max(1, top - hoof)
    for y in range(hoof, top + 4):
        (r,) = loft.lerp(KEYS, max(0.0, 1.0 - (y - hoof) / span))
        loft.disc(hide, lx, y, lz, f, s, r, r, n)


def leg_cursorial(hide, lx, lz, hoof, top, f, s, lr, n, fold=1.0):
    """Long and slender, flaring hard into the haunch. A giraffe or a horse."""
    KEYS = [[0.00, lr * fold + 1.6], [0.05, lr * fold + 0.9], [0.15, lr * fold + 0.15],
            [0.46, lr * fold - 0.3], [0.76, lr * fold + 0.05], [1.00, lr * fold + 0.4]]
    span = max(1, top - hoof)
    for y in range(hoof, top + 4):
        (r,) = loft.lerp(KEYS, max(0.0, 1.0 - (y - hoof) / span))
        loft.disc(hide, lx, y, lz, f, s, r, r, n)


LEGS = {"digitigrade": leg_digitigrade, "plantigrade": leg_plantigrade, "columnar": leg_columnar,
        "stubby": leg_stubby, "cursorial": leg_cursorial}


# ------------------------------------------------------------------ heads
# (t along the muzzle, half-width, vertical centre, half-height) as multiples of head_r

HEAD_KEYS = {
    # A CAT: short round braincase, wide cheeks, a muzzle that barely projects. The comment said
    # that all along; the numbers said something else. Half-width ran -0.95 -> 0.00 -> -0.80, a
    # steady taper to a point, while the vertical centre dropped 0.40 -> -0.85 - and a long
    # drooping taper is a SNOUT. The panel read the result as a deer, and it was right to.
    #
    # A felid skull is nearly as wide at the muzzle as at the cheeks and it does not droop: the
    # width holds through the face and stops blunt, and the nose sits only a little below the eye.
    "rounded": [[0.00, -0.85, 0.30, -0.12], [0.20, 0.05, 0.34, 0.12], [0.45, -0.02, 0.12, 0.04],
                [0.70, -0.16, -0.10, -0.10], [0.90, -0.26, -0.24, -0.20],
                [1.00, -0.34, -0.32, -0.26]],
    # a bear: a WIDE FLAT skull, then a distinct STEP down to a narrow straight muzzle that runs
    # level rather than drooping. The step is the thing your eye reads as "bear".
    "broad": [[0.00, -0.55, 0.20, -0.30], [0.18, 0.05, 0.25, -0.20], [0.38, 0.00, 0.15, -0.25],
              [0.52, -0.55, 0.00, -0.45],                       # the step from cranium to snout
              [0.75, -0.70, -0.10, -0.55], [1.00, -0.75, -0.20, -0.58]],
    # an elephant: a high domed forehead over a small face
    "domed": [[0.00, -0.70, 0.55, -0.10], [0.20, 0.00, 0.70, 0.20], [0.45, -0.15, 0.25, -0.10],
              [0.70, -0.55, -0.25, -0.45], [1.00, -0.80, -0.65, -0.65]],
    # a capybara: a deep square box with a flat front - almost no taper at all
    "blunt": [[0.00, -0.40, 0.15, -0.20], [0.25, 0.00, 0.15, 0.00], [0.60, -0.05, 0.05, -0.05],
              [0.85, -0.20, -0.10, -0.15], [1.00, -0.30, -0.20, -0.25]],
    # a giraffe: long, narrow, gently tapering, with the eyes set high
    "tapered": [[0.00, -1.00, 0.40, -0.20], [0.20, 0.00, 0.50, 0.15], [0.42, -0.05, 0.10, -0.10],
                [0.65, -0.50, -0.50, -0.45], [0.88, -0.85, -1.00, -0.70], [1.00, -0.95, -1.25, -0.80]],
}


def head(hide, top, neck_r, f, s, p, shape: str):
    """Loft the skull along the muzzle using the family's own profile."""
    hx, hy, hz = top
    hl, hr, n = int(p["head_len"]), float(p["head_r"]), float(p["section_n"])
    keys = HEAD_KEYS.get(shape, HEAD_KEYS["rounded"])
    KEYS = [[t, max(neck_r, hr + dw * hr) if t == 0.0 else hr + dw * hr, dy * hr, hr + dh * hr]
            for t, dw, dy, dh in keys]
    brow = (hx, hz)
    for i in range(hl):
        t = i / max(1, hl - 1)
        rb, dy, rv = loft.lerp(KEYS, t)
        cx, cz = hx + f[0] * i, hz + f[1] * i
        loft.rib(hide, cx, hy + dy, cz, f, s, rb, rv, n, squash_lo=0.92)
        if abs(t - 0.42) < 0.5 / hl:
            brow = (cx, cz)
    return (hx, hy, hz, hl, hr, brow[0], brow[1])
