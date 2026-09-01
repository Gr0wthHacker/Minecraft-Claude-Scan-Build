"""A pale wyrm rearing off a black milestone. The causeway's dark landmark.

WHY A SERPENT AND NOT A BEAST. CLAUDE.md's line is PLANAR/COLUMNAR against VOLUMETRIC, measured
over eight failed mammals: what kills a voxel animal is compound muscle - a shoulder, a haunch -
and what saves one is a plane, a taper or a column. A snake is the purest taper in nature. It
has no shoulder, no haunch, no joint, and no proportion that has to be right to a few per cent;
it is a tube that gets thinner, which is the same primitive as the elephant's trunk (385 cells,
still the best-reading feature in the repo) and the giraffe's neck. And a HOOD is a flat plate,
which is the sky bird's wing and the gecko's splayed limbs - the one thing this medium renders
better than any other.

**THE FIRST BUILD WOUND IT ROUND THE POST AND IT FAILED THE ONLY TEST THAT MATTERS.** Two and a
quarter turns of body on a twenty-course obelisk was a real helix, one connected piece,
correctly banded - and its silhouette was a lumpy vertical mass with a hook on the top. It read
as a totem, or a chess piece. The reason is structural rather than a matter of tuning, and it
is worth stating because the idea will look attractive again: **a coil round a column reads
through COLOUR AND DEPTH, and its OUTLINE is a bumpy column.** On this causeway there is
nothing behind a sculpture but open sky, so the outline is all there is, and the whole coil was
being spent on the one channel that does not survive the distance.

So the coil stays where it is cheap - one and a half turns at the BASE, where it does the
anchoring and gives the plan view a pair of concentric rings - and everything above it is spent
on outline:

    the S       a free rise of sixteen courses, cantilevered forward and back. An S-curve is
                the most recognisable line a snake has and it costs nothing but a taper
    the hood    a flared plate, 11 wide and 9 tall, 2 thick. It is the feature that makes the
                thing nameable in a thumbnail, and it is a PLANE - the shape voxels give away
    the head    forward of the hood, jaw open, so the hood is read as behind a head rather than
                as a paddle

**AND THE TWO VIEWS A WALKER GETS ARE DELIBERATELY DIFFERENT.** The causeway's spine runs along
Z and a stop stands off it in X, so a visitor abreast of it looks along X and a visitor
approaching looks along Z. The head faces the walkway, which means the hood - whose whole job
is to be seen by whatever the snake is facing - flares square to the person standing nearest
it, and the S-curve, which lives in the same plane the body bends in, shows in full to the
person still walking toward it. Neither bearing gets the edge of everything, which is the
failure `dragonfly.py` has by construction and the reason it was refused this job.

**THE MILESTONE IS ARCHITECTURE, AND ARCHITECTURE IS REGULARITY.** The void tower settled that
once and had its first attempt rejected on sight as "a tossed grouping of vague blocks": what
makes voxels read as built is REGULARITY AND OPENINGS, never damage. So the stone is a plain
banded stub with a footing and a cap, and every irregular thing in the piece is the animal.

PALETTE. The hollow's own ground is blackstone and deepslate, and a creature the colour of its
ground is not a creature (`turtle.py`, measured). The value ladder is taken ACROSS material
families, never within one - this repo concluded three separate times that this economy has no
value contrast, and all three measurements were made inside a single family, where a ladder
cannot exist by construction:

    bone_block 198 . light_gray_wool 140 . deepslate_bricks 71 . polished_blackstone_bricks 47
    . black_wool 23

so the wyrm stands 127 clear of its own stone and 175 clear of its own markings. The stone's
two blocks are 24 apart, which `park.py` already measures as the smallest step that draws a
line on this land.

THE BANDING IS SPARSE, and that is the second thing the first build got wrong: a chevron every
eleven stations of a hundred and fifty made the body a stack of alternating pale and dark
blobs, which is exactly how a continuous ribbon stops reading as one. A snake's bands are far
apart relative to its own thickness.

NO LIGHT IS BUILT INTO THE COAT - `isthmus._delight` lights a sculpture from the air beside it
with lichen, and a lamp this generator placed itself would be indistinguishable from the 1,138
the night sweep once drove into these creatures' coats.
"""
from __future__ import annotations

import math

from .canvas import Canvas

WYRM = {
    "seed": 0,
    "scale": 1.0,
    # world coordinate of the canvas corner - a bespoke generator states this itself or the
    # pipeline writes no sidecar, and without one there is no origin and no `/cscan place`.
    "at": None,
    # ...or give `stand`, the world cell the MILESTONE'S OWN LOWEST COURSE occupies.
    "stand": None,
    # +1 rears the head toward +x, -1 toward -x. A sited wyrm aims it at the walkway it is
    # meant to be looked at from; there is no rotation anywhere, because a quarter turn of a
    # built canvas can only ever re-aim the states it understands (`isthmus._turn`).
    "face": 1,

    "stone_h": 8,            # courses of milestone above its own footing
    "turns": 1.55,           # ...and the last of them lands the body pointing along +face
    "body_r": 1.85,
    "rise": 16,              # courses of free S between the coil and the hood
    "band_every": 26,        # STATIONS between the body's dark bands - see the docstring
    "band_wide": 4,
    "hood_w": 5.4,           # half the hood, across the walk
    "hood_h": 4.6,

    "post": "deepslate_bricks",
    "band": "polished_blackstone_bricks",
    "body": "bone_block",
    "belly": "light_gray_wool",
    "mark": "black_wool",
    "eye": "red_wool",
}


def build_wyrm(cfg: dict, donors=None) -> Canvas:
    p = {**WYRM, **cfg}
    sc = float(p.get("scale", 1.0))
    fx = 1 if int(p.get("face", 1)) >= 0 else -1
    stone_h = max(4, int(round(float(p["stone_h"]) * sc)))
    body_r = float(p["body_r"]) * sc
    rise = max(8, int(round(float(p["rise"]) * sc)))
    hw_hood = float(p["hood_w"]) * sc
    hh_hood = float(p["hood_h"]) * sc

    y_stone = 2 + stone_h - 1                  # the milestone's own last shaft course
    y_hood = y_stone + rise + 4
    SX, SZ = 35, 25
    SY = int(y_hood + hh_hood + 4)
    c = Canvas(SX, SY, SZ, donors)
    st = c.state
    S = {k: st(p[k]) for k in ("post", "band", "body", "belly", "mark", "eye")}
    cx, cz = SX // 2, SZ // 2

    # ---- THE MILESTONE: a 7x7 footing, a banded 5x5 stub, a 3x3 cap. Plain on purpose.
    for y in (0, 1):
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                c.put(cx + dx, y, cz + dz, S["band"])
    for y in range(2, y_stone + 1):
        blk = S["band"] if (y - 2) % 3 == 0 else S["post"]
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                c.put(cx + dx, y, cz + dz, blk)
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            c.put(cx + dx, y_stone + 1, cz + dz, S["band"])

    ce, cw = max(6, int(p["band_every"])), max(1, int(p["band_wide"]))
    marks = 0

    def _sweep(path, r_of, phase=0):
        """One tapering tube, drawn as a dense sweep of spheres.

        DENSE, because a swept feature whose cells are only DIAGONAL neighbours is not
        connected in this project's sense, and that has cost it ear tips, ossicones, a whole
        dragonfly and - on this very generator's first pass - a one-cell tail tip that shipped
        as a second component while everything else audited clean.
        """
        nonlocal marks
        for i, (px, py, pz, t) in enumerate(path):
            dark = ((i + phase) % ce) < cw
            c.sphere(px, py, pz, r_of(t), S["mark"] if dark else S["body"])
            marks += 1 if dark else 0

    # ---- THE COIL, one and a half turns at the base. It anchors the animal, it gives the PLAN
    # view a pair of concentric rings, and it is deliberately not asked to carry the outline.
    turns = float(p["turns"])
    theta0 = -turns * 2 * math.pi               # ...so the last station points along +x
    y0c, y1c = 3.6, y_stone + 0.6
    steps = max(50, int(round((y1c - y0c) * 11)))
    coil = []
    for i in range(steps + 1):
        t = i / float(steps)
        y = y0c + (y1c - y0c) * t
        rad = 2 + body_r * 0.62 + 0.55
        th = theta0 + turns * 2 * math.pi * t
        coil.append((cx + fx * rad * math.cos(th), y, cz + rad * math.sin(th), t))
    _sweep(coil, lambda t: body_r * (0.72 + 0.28 * t))

    # the belly: the lowest cell of each of the coil's own columns, so the tube has an
    # underside and does not read as one flat tone wrapped round a stone
    for (px, py, pz, _t) in coil[::2]:
        ix, iz = int(round(px)), int(round(pz))
        for iy in range(int(py - body_r - 2), int(py + body_r + 2)):
            if c.solid(ix, iy, iz) and not c.solid(ix, iy - 1, iz):
                if c.get(ix, iy, iz) == S["body"]:
                    c.put(ix, iy, iz, S["belly"])
                break

    # ---- THE FREE TAIL, off the bottom of the coil, out past the footing and flicked up. It
    # is what stops the base being a symmetrical doughnut, and it is grown from the coil's own
    # first station so it cannot arrive detached.
    tx, ty, tz, _ = coil[0]
    tail = []
    for i in range(41):
        t = i / 40.0
        a, b, d = (1 - t) ** 2, 2 * (1 - t) * t, t * t
        tail.append((a * tx + b * (tx + fx * 2.6) + d * (tx + fx * 5.4),
                     a * ty + b * (ty - 1.4) + d * (ty + 2.6),
                     a * tz + b * (tz - 2.6) + d * (tz - 4.4), t))
    _sweep(tail, lambda t: max(0.85, body_r * (0.66 - 0.30 * t)))

    # ---- THE S. Nineteen courses of free rise, forward then back then forward, in the plane
    # the body actually bends in - which is the plane a visitor still walking toward the stop
    # is looking straight at. This is the whole outline of the piece.
    nx, ny, nz, _ = coil[-1]
    hx, hy, hz = cx + fx * 1.2, y_hood, cz
    # THE S SWINGS IN Z AS WELL AS IN X, and that is not decoration. Kept purely in the x-y
    # plane the curve is invisible from the one bearing a visitor standing on the spine
    # actually has - it foreshortens into a straight vertical, and the animal reads as a post
    # with a disc on it. A lateral weave costs nothing, keeps the profile's S intact, and gives
    # the head-on view a body that moves.
    P = [(nx, ny, nz),
         (nx + fx * 5.6, ny + rise * 0.34, nz + 6.0),
         (cx - fx * 3.4, ny + rise * 0.72, cz - 5.6),
         (hx, hy - hh_hood * 0.35, hz)]
    esses = []
    n = 76
    for i in range(n + 1):
        t = i / float(n)
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        d = 3 * (1 - t) * t * t
        e = t ** 3
        esses.append((a * P[0][0] + b * P[1][0] + d * P[2][0] + e * P[3][0],
                      a * P[0][1] + b * P[1][1] + d * P[2][1] + e * P[3][1],
                      a * P[0][2] + b * P[1][2] + d * P[2][2] + e * P[3][2], t))
    _sweep(esses, lambda t: body_r * (1.0 - 0.22 * t), phase=7)

    # ---- THE HOOD: a flared plate, two thick, square to the walkway. Its DARK RIM is what
    # draws the outline at distance - a pale plate against a pale sky is a shape with no edge -
    # and the two eyespots are the pattern that makes it a hood rather than a paddle. That is
    # the ladybird's own case: a pattern on a plane, which is what this medium is best at.
    hood, rim, spots = 0, 0, 0
    for dz in range(-int(hw_hood) - 1, int(hw_hood) + 2):
        for dy in range(-int(hh_hood) - 1, int(hh_hood) + 2):
            q = (dz / hw_hood) ** 2 + (dy / hh_hood) ** 2
            if q > 1.0:
                continue
            blk = S["mark"] if q > 0.84 else S["body"]
            for k in range(2):
                if c.put(int(round(hx)) - fx * k, int(round(hy)) + dy, cz + dz, blk):
                    hood += 1
                    rim += 1 if blk == S["mark"] else 0
    for side in (-1, 1):
        ez = cz + int(round(side * hw_hood * 0.46))
        for dz in range(-1, 2):
            for dy in range(-1, 2):
                # a PLUS, not a square: a 3x3 of dark on a 2-thick plate is a hole punched
                # through it, and the pair then reads as two windows rather than as markings
                if abs(dz) + abs(dy) > 1:
                    continue
                if c.get(int(round(hx)), int(round(hy)) + dy, ez + dz) == S["body"]:
                    c.put(int(round(hx)), int(round(hy)) + dy, ez + dz, S["mark"])
                    spots += 1

    # ---- THE NECK THROUGH THE HOOD, AND THE HEAD IN FRONT OF IT. The head has to stand PROUD
    # of the plate or the whole thing reads as a paddle with a bump on it.
    c.line((hx, hy - hh_hood * 0.4, hz), (hx + fx * 2.0, hy + hh_hood * 0.34, hz),
           body_r * 0.82, S["body"])
    ex_h, ey_h = hx + fx * 4.4, hy + hh_hood * 0.52
    c.ellipsoid(ex_h, ey_h, hz, 2.9, 1.8, 2.1, S["body"])
    # the snout, a straight taper forward off the skull - the elephant's trunk primitive
    c.line((ex_h + fx * 1.0, ey_h + 0.1, hz), (ex_h + fx * 3.4, ey_h - 0.7, hz), 1.30, S["body"])
    c.line((ex_h + fx * 2.6, ey_h - 0.5, hz), (ex_h + fx * 4.4, ey_h - 1.1, hz), 0.80, S["body"])
    # THE OPEN JAW, hung under the snout with air between them. The gap is the feature: a closed
    # muzzle at this size is a blunt end, and a blunt end is what made the felid skull read as
    # a deer.
    c.line((ex_h + fx * 0.6, ey_h - 1.9, hz), (ex_h + fx * 3.8, ey_h - 3.0, hz), 1.00, S["belly"])

    # ---- EYES, taken off the BUILT surface rather than from a radius: `loft.surface_out`'s own
    # rule, and the reason the axolotl's beads finally read from both bearings. The OUTERMOST
    # solid cell of the row, so by construction nothing stands in front of one. Aimed at the
    # skull's middle course.
    #
    # IT SEARCHES FOR A ROW WIDE ENOUGH TO CARRY A PAIR, and that is not fussiness. Fixed at
    # one computed offset it landed on a course where the skull is two cells across and the
    # half-cell centring made those two ASYMMETRIC about the midline - so one side found a
    # block, the other found air, and the wyrm shipped with ONE eye, twice, with no error
    # anywhere and nothing in the audit, the component count or the bill of materials to say
    # so. A feature that can silently half-exist has to be measured, not computed.
    eyes = 0
    seat = None
    for dy in (0, 1, -1):
        for step in (1.2, 0.4, 2.0):
            ex, ey = int(round(ex_h + fx * step)), int(round(ey_h)) + dy
            zs = [z for z in range(int(round(hz)) - 4, int(round(hz)) + 5) if c.solid(ex, ey, z)]
            if len(zs) >= 3:
                seat = (ex, ey, zs)
                break
        if seat:
            break
    if seat:
        ex, ey, zs = seat
        for z in (min(zs), max(zs)):
            c.put(ex, ey, z, S["eye"])
            eyes += 1

    if p.get("stand"):
        wx, wy, wz = (int(round(float(v))) for v in p["stand"])
        c.world_origin = (wx - cx, wy, wz - cz)
    elif p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    # `hood_plane` is RECORDED because the hood's rim and the body's bands are the same block,
    # so nothing downstream can tell one from the other by looking - and the one thing worth
    # checking about this animal is that the head stands forward of the plate rather than
    # buried in it. A test that took every `black_wool` cell would be measuring the tail.
    c.meta = {"kind": "wyrm", "scale": sc, "facing": [fx, 0], "hood_plane": int(round(hx)),
              "features_built": {"coil_stations": len(coil), "tail": 1, "rise": len(esses),
                                 "hood": hood, "hood_rim": rim, "eyespots": spots,
                                 "bands": marks, "skull": 1, "jaw": 1, "eyes": eyes}}
    return c


build = build_wyrm
DEFAULTS = WYRM
