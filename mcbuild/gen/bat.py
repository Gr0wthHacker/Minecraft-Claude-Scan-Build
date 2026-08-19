"""A bat hanging from the cave ceiling. Membrane wings on finger struts - all plane, no volume.

    bat: hangs head-down from a roof, wings half-furled, membrane stretched between splayed fingers.

Same argument as `heron.py`. What this medium renders perfectly is PLANAR form, and a bat's wing is
the purest plane in nature: a single membrane one block thick, stretched between four finger bones
that are themselves straight tapers. There is no muscle to describe anywhere - the body is a small
furred lump and everything else is strut and skin.

It also uses a surface nothing else on this island touches. The lowland is ROOFED - 4,193 of its
columns sit under the plate and 1,504 under the void isle, and only 154 are open to the sky - so
there is a ceiling overhead everywhere you stand and not one thing hanging from it. A bat is the
animal that belongs there, and hanging it inverted costs nothing: `y` counts DOWN from the roof.

The wing membrane is drawn as a filled polygon between the struts rather than as swept spheres,
because a sphere sweep gives a rope and a membrane is a sheet. That is the whole difference.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01

BAT = {
    "size": [56, 40, 22],
    "seed": 0,
    "scale": 1.0,
    # world coordinate of the canvas corner. A bespoke generator has to state this
    # itself - `World.canvas()` does it for the parametric ones - or the pipeline
    # writes no sidecar, and without a sidecar there is no origin, no in-context
    # audit and no `/cscan place`. The gecko still has this gap.
    "at": None,
    # ...or give `hang`, the world block its claws grip. A bat is placed by the ceiling it
    # holds on to, not by the corner of its box.
    "hang": None,
    # A PERCH: its own small floating rock, so the bat does not need a ceiling to exist under. It
    # can then hang in open air anywhere - which is the only way to put one in the gap between two
    # island lobes, where there is nothing overhead to grip.
    "perch": False,
    "perch_h": 8,                # courses of rock above the claws
    "perch_r": 7.0,              # its radius, in the design's own units
    "rock": ["stone", "cobblestone", "deepslate", "mossy_cobblestone"],
    "moss": "moss_block",
    "vine": "vine",
    # A RUIN on the rock's crown. The perch reads as a piece that broke off the plate, so it should
    # carry a piece of what was BUILT on the plate too - and there is a measured reason for its
    # shape. The rock hangs in the gap at Y138 with the island's underside at Y150, so from the SE
    # rim you look down on it at about 13 degrees off vertical: the PLAN view governs, not the
    # profile. A ring of broken wall with a light inside it is unmistakable from straight above,
    # where an arch or a bare snag is a few scattered pixels.
    "ruin": False,
    "ruin_h": 13,                # courses on the TALL side; the shear takes the far side to ~0.3 of it
    "ruin_r": 4.6,               # outer radius of the wall
    "ruin_t": 1.7,               # its thickness
    "ruin_face": 0.9,            # which way the tall side looks, in radians
    # DRESSED stone against the rock's rough stone. That contrast is the whole point - it is what
    # says "built" rather than "more rock", which is the note both review panels keep returning.
    # Moss climbs from the bottom and cracks gather at the top, so the wall weathers upward.
    "ruin_block": "stone_bricks",
    "ruin_moss": "mossy_stone_bricks",
    "ruin_crack": "cracked_stone_bricks",
    # STRING COURSES, and they are what makes it read as masonry rather than as a grey fin.
    # cracked/chiseled/plain stone brick are all within 4 RGB of each other, so weathering them
    # together is invisible at any distance - the wall had no tone and no horizontal at all.
    # deepslate_bricks is 51 darker, and it is the island's OWN stone dressed, which is what a
    # builder up here would have had to hand.
    "ruin_band": "deepslate_bricks",
    "ruin_plinth": "chiseled_stone_bricks",
    "ruin_slab": "stone_brick_slab",
    "ruin_lamp": "lantern",
    "spread": 0.75,              # 0 = furled tight, 1 = wings fully out
    # dark, and deliberately NOT made of the ceiling it hangs from: the lowland's roof is stone,
    # cobble, deepslate and moss, so a bat in those would vanish the way the elephant did.
    # ALL CHEAP TIER. The membrane was `brown_terracotta` and its edge `black_terracotta`, which is
    # 290 blocks of clay on a skyblock for a brown that `brown_wool` gives for a dye. A LIGHTER
    # membrane against dark fur is also what a bat actually looks like: the wing is thin skin and
    # the body is fur, and they should not be the same tone.
    "fur": "dark_oak_wood",
    "fur_dark": "black_wool",
    "skin": "brown_wool",        # the membrane
    "skin_edge": "black_wool",
    # the bones must be DARKER than the membrane but not BLACK: dark_oak_planks was so
    # close to brown_wool the fingers disappeared, and black_wool read as holes.
    "strut": "dark_oak_wood",    # finger bones
    "eye": "orange_wool",
    "snout": "brown_wool",   # a lighter muzzle, so the head reads as a head
    "claw": "bone_block",
}


def _triangle(c: Canvas, a, b, d, blk, sag=0.15):
    """FILL the sheet between two finger struts, by area rather than by a fan of lines.

    It used to draw a fan of thin lines from the wrist out to points along the trailing edge, and a
    fan is exactly the wrong primitive: radial lines diverge, so at the wrist they overlap three
    deep and out at the tips they are more than a block apart. That is where the big holes in the
    wings came from - not a colour problem, a coverage one.

    Filling the triangle in BARYCENTRIC coordinates at a step fine enough for the longest edge
    guarantees there is no gap anywhere in it, whatever the size or the spread.

    `sag` bows the trailing edge back toward the anchor between the two tips - the scallop that says
    "bat" rather than "kite".
    """
    a, b, d = (np.array(q, float) for q in (a, b, d))
    longest = max(np.linalg.norm(a - b), np.linalg.norm(a - d), np.linalg.norm(b - d))
    n = max(8, int(longest * 2.2))                    # samples at most ~0.45 blocks apart
    for i in range(n + 1):
        s = i / n
        edge = a + (b - a) * s
        edge = edge + (d - edge) * (sag * 4.0 * s * (1.0 - s))
        for j in range(n + 1):
            q = d + (edge - d) * (j / n)
            c.put(int(round(q[0])), int(round(q[1])), int(round(q[2])), blk)


def _stick(c: Canvas, x, y, z, blk) -> bool:
    """Place a single cell ONLY where it has something to hold on to.

    Every detached-feature bug in this repo is the same mistake: a detail placed at a COMPUTED
    position rather than against the surface that was actually built.
    """
    x, y, z = int(round(x)), int(round(y)), int(round(z))
    if c.get(x, y, z):
        c.put(x, y, z, blk)
        return True
    for dx, dy, dz in ((0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
        if c.get(x + dx, y + dy, z + dz):
            c.put(x, y, z, blk)
            return True
    return False


def build_bat(cfg: dict, donors=None) -> Canvas:
    p = {**BAT, **cfg}
    sc = float(p.get("scale", 1.0))
    SX, SY, SZ = (max(8, int(round(v * sc))) for v in p["size"])
    seed, spread = int(p["seed"]), float(p["spread"])
    perch = bool(p.get("perch"))
    ph = int(round(float(p["perch_h"]) * sc)) if perch else 0
    # The ruin needs headroom ABOVE the rock, whose top course was the canvas ceiling. Size the box
    # for it here, before the canvas exists, so `hang` still means exactly what it says.
    ruin = bool(p.get("ruin")) and perch
    rh = int(round(float(p["ruin_h"]) * sc)) if ruin else 0
    SY += rh                                          # exactly the ruin's courses: a spare one
                                                      # here lifts the claws off the roof course
    c = Canvas(SX, SY, SZ, donors)
    st = c.state
    S = {k: st(p[k]) for k in ("fur", "fur_dark", "skin", "skin_edge", "strut", "eye", "claw")}
    cx, cz = SX / 2.0, SZ / 2.0
    u = sc
    roof = SY - 1 - ph - rh                           # y counts DOWN from here: the bat hangs

    # ---- THE PERCH. A ragged lump of the island's own rock, wider than it is deep and thickest in
    # the middle, with moss on top and a couple of vines off the rim - so it reads as a piece that
    # broke off the plate rather than as a sphere someone parked there.
    if perch:
        h0 = lambda *a: hash01(*a, seed)
        rock = [st(b) for b in p["rock"]]
        moss, vine = st(p["moss"]), st(p["vine"])
        pr = float(p["perch_r"]) * sc
        for k in range(ph + 1):
            f_ = k / max(1, ph)                       # 0 at the bat's grip, 1 at the top
            r = pr * (0.45 + 0.75 * f_ - 0.35 * f_ * f_)
            for dx in range(-int(r) - 2, int(r) + 3):
                for dz in range(-int(r) - 2, int(r) + 3):
                    d = (dx * dx + dz * dz) ** 0.5
                    # ragged, but not SO ragged that the edge sheds islands - the noise is
                    # smoothed along k so a column cannot appear with nothing under it
                    if d > r * (0.86 + 0.18 * h0(dx, 0, dz, 5)):
                        continue
                    y = roof + k
                    blk = moss if k == ph else rock[int(h0(dx, k, dz, 9) * len(rock)) % len(rock)]
                    c.put(int(round(cx + dx)), int(y), int(round(cz + dz)), blk)
        # vines off the rim. A vine hangs from the block ABOVE it, so each strand starts only
        # where there is rock to hang from and stops the moment the run breaks - placed blind they
        # came away as nine separate floating threads.
        for j in range(max(3, int(round(6 * sc)))):
            a = h0(j, 1, 2, 13) * 6.283
            rx = int(round(cx + pr * 0.82 * np.cos(a)))
            rz = int(round(cz + pr * 0.82 * np.sin(a)))
            if not c.get(rx, roof, rz):
                continue                              # nothing to hang from here
            for k in range(1, 2 + int(6 * h0(j, 3, 4, 17))):
                if not c.get(rx, roof - k + 1, rz):
                    break
                c.put(rx, roof - k, rz, vine)

    # ---- THE RUIN on the crown. A round wall SHEARED diagonally - tall on one side, falling to a
    # stub on the other - with its collapsed course lying on the moss below the low side and a
    # lantern burning inside. Nothing else out here carries a light.
    if ruin:
        h1 = lambda *a: hash01(*a, seed + 7)
        R = float(p["ruin_r"]) * sc
        tk = float(p["ruin_t"]) * sc
        face = float(p["ruin_face"])
        base = roof + ph                              # the moss course; the wall starts one above
        brick, mossy = st(p["ruin_block"]), st(p["ruin_moss"])
        crack, plinth = st(p["ruin_crack"]), st(p["ruin_plinth"])
        slab, lamp = st(p["ruin_slab"]), st(p["ruin_lamp"])

        band = st(p["ruin_band"])
        bands = {1, max(3, int(rh * 0.55))}           # a plinth course and one string course

        def _course(k, fr, dx, dz):
            """weather UPWARD: moss climbs off the rock, cracks gather where the weather gets in.
            Hashed on the CELL. It used to hash on the course alone, so every block in a course
            came out the same and the wall was horizontal stripes of one material."""
            if k in bands:
                return band
            r = h1(dx, k, dz, 23)
            if r < 0.34 * (1.0 - fr) + 0.05:
                return mossy
            if r > 1.0 - (0.30 * fr + 0.05):
                return crack
            return brick

        # the gash goes through the TALL side, splitting the crown into two horns. Behind the
        # low side it did nothing: the silhouette stayed one unbroken wedge, which is a fin.
        gash = face + 0.34
        for dx in range(-int(R) - 2, int(R) + 3):
            for dz in range(-int(R) - 2, int(R) + 3):
                d = (dx * dx + dz * dz) ** 0.5
                if d > R or d < R - tk:
                    continue                          # a RING, not a disc
                a = np.arctan2(dz, dx)
                # THE SHEAR IS A PLANE, not a cosine. A cosine falls away smoothly from the high
                # point in every direction, which is a cone - and it built a witch's hat rather
                # than a ruin. A break is a FLAT crown over a broad arc, then a hard diagonal
                # drop: project onto the shear direction and let the clamps do the flattening.
                proj = (dx * np.cos(face) + dz * np.sin(face)) / max(1e-6, R)
                hh = min(float(rh), max(rh * 0.16, rh * (0.60 + 0.78 * proj)))
                hh -= 3.6 * h1(dx, 5, dz, 29)         # ragged top, so it reads as broken masonry
                da = (a - gash + np.pi) % (2 * np.pi) - np.pi
                if abs(da) < 0.24:                    # the crack: open from the top down to ~40%
                    hh = min(hh, rh * 0.40)
                for k in range(1, int(round(hh)) + 1):
                    y = base + k
                    if not c.get(int(round(cx + dx)), base, int(round(cz + dz))):
                        break                         # never build off the rock's ragged edge
                    c.put(int(round(cx + dx)), int(y), int(round(cz + dz)), _course(k, k / max(1, rh), dx, dz))

        # a window slit high on the tall side, so the light inside has a second way out
        wa = face + 0.55
        wx, wz = int(round(cx + (R - 0.6) * np.cos(wa))), int(round(cz + (R - 0.6) * np.sin(wa)))
        for k in (int(rh * 0.62), int(rh * 0.62) + 1):
            for dd in range(-int(tk) - 1, int(tk) + 2):
                c.put(int(round(wx + dd * np.cos(wa))), base + k, int(round(wz + dd * np.sin(wa))), 0)

        # the LANTERN, on a plinth in the middle. From straight above - which is the angle this is
        # actually seen from - the read is a dark broken ring with one bright point in it.
        c.put(int(cx), base + 1, int(cz), plinth)
        c.put(int(cx), base + 2, int(cz), lamp)

        # ...and the collapsed course, lying on the moss out beyond the LOW side where it fell.
        low = face + np.pi
        for j in range(int(round(30 * sc))):
            a = low + (h1(j, 8, 1, 31) - 0.5) * 2.4
            # OUTSIDE the wall's own footprint: at 0.55-1.40 R most draws landed on the ring
            # itself, were correctly refused, and 16 tries left 2 stones on the ground
            d = R * (1.06 + 0.52 * h1(j, 9, 2, 37))
            rx, rz = int(round(cx + d * np.cos(a))), int(round(cz + d * np.sin(a)))
            if not c.get(rx, base, rz) or c.get(rx, base + 1, rz):
                continue                              # only onto bare moss, never inside the wall
            c.put(rx, base + 1, rz, slab if h1(j, 10, 3, 41) < 0.45 else _course(0, 0.1, rx, rz))

    # ---- FEET, gripping the roof. Two hooked claws, which is the detail that says "hanging"
    # rather than "falling" - without them the whole thing reads as a bat mid-air, upside down.
    for side in (-1, 1):
        fx = cx + side * 1.6 * u
        c.line((fx, roof, cz), (fx, roof - 3.0 * u, cz + 0.4 * u), 0.85 * u, S["fur_dark"])
        for k in (-1, 0, 1):
            c.line((fx, roof, cz + k * 0.9 * u),
                   (fx + side * 0.8 * u, roof - 1.4 * u, cz + k * 1.5 * u), 0.62 * u, S["claw"])

    # ---- BODY: a small lump, head DOWNWARD. Everything about a bat is wing; the body is the least
    # of it and must not be allowed to become a barrel.
    body_y = roof - 8.0 * u
    c.ellipsoid(cx, body_y, cz, 2.6 * u, 5.0 * u, 2.4 * u, S["fur"])
    head_y = body_y - 5.5 * u
    c.ellipsoid(cx, head_y, cz + 0.3 * u, 2.1 * u, 2.2 * u, 2.0 * u, S["fur"])
    for side in (-1, 1):                              # ears: upright planar fans, big, the way a
        ex = cx + side * 1.5 * u                      # bat's really are - and they point DOWN here
        c.line((ex, head_y + 0.5 * u, cz), (ex + side * 1.6 * u, head_y - 4.2 * u, cz - 0.4 * u),
               0.75 * u, S["fur"])
        c.line((ex + side * 0.3 * u, head_y - 0.4 * u, cz),
               (ex + side * 2.4 * u, head_y - 3.4 * u, cz - 0.3 * u), 0.5 * u, S["fur_dark"])
    # ---- THE FACE. It was one orange cell on a dark lump: at any distance the head read as a knot
    # in the body rather than as a head. A bat's face is a short pale snout with the eyes set wide
    # and high on it, so the snout gets its own lighter block and each eye a dark socket to sit in -
    # the same bead-in-a-ring that made the capybara legible.
    #
    # And it is painted on the SURFACE, found by walking outward. Placed at computed positions the
    # cells landed INSIDE the skull, where they are perfectly correct and completely invisible -
    # which is the same mistake as the floating mane, inverted.
    def _skin(x, y, blk, reach=5.0):
        """Paint the outermost solid cell of this column, looking along +z (the face)."""
        xi, yi = int(round(x)), int(round(y))
        for k in range(int(reach * sc), -1, -1):
            zi = int(round(cz + k))
            if c.get(xi, yi, zi):
                c.put(xi, yi, zi, blk)
                return True
        return False

    snout = st(p.get("snout") or p["skin"])
    for dy in (0, 1):                                     # a short pale muzzle
        for dx in (-1, 0, 1):
            _skin(cx + dx * 0.9 * u, head_y - (1.8 + dy) * u, snout)
    _skin(cx, head_y - 2.9 * u, S["fur_dark"])            # nose
    for side in (-1, 1):
        # 1.6 put the eye at the very rim of a 2.1-radius skull, where the column is
        # empty at brow height and one of the two silently found nothing
        ex = cx + side * 1.1 * u
        for dy in (-1, 0, 1):                             # socket
            _skin(ex, head_y + (0.2 + dy) * u, S["fur_dark"])
        _skin(ex, head_y + 0.2 * u, S["eye"])             # the bead, over its own socket

    # ---- WINGS. Arm out to the wrist, then four finger struts fanning back, with the membrane
    # filled between consecutive fingers. `spread` swings the whole fan outward.
    shoulder = (cx, body_y - 2.0 * u, cz - 0.2 * u)
    fingers = max(3, int(round(4 * sc)))
    for side in (-1, 1):
        out = (6.0 + 14.0 * spread) * u
        wrist = (cx + side * out, body_y - 5.0 * u, cz - 0.6 * u)
        bones = [(shoulder, wrist, 1.15 * u, S["strut"])]   # drawn LAST, see below
        tips = []
        for i in range(fingers + 1):
            t = i / fingers
            # the fan: first finger forward and short, last one back along the body and long
            # SWEEP the fan hard: the first finger reaches far out and slightly up to make a real
            # WINGTIP, the last folds back in along the body. Fanning them all to a similar reach
            # gave a rectangle with struts drawn on it - square outer corners and no point.
            tip = (wrist[0] + side * (11.5 - 9.5 * t) * u * (0.45 + 0.75 * spread),
                   wrist[1] + (-1.0 + 13.5 * t) * u,
                   wrist[2] - (0.8 - 1.6 * t) * u)
            tips.append(tip)
            bones.append((wrist, tip, (0.62 - 0.12 * t) * u, S["strut"]))
        # the PROPATAGIUM: the sheet between the ARM and the first finger. It was never drawn at
        # all, which left the largest hole of the lot right where the wing meets the body.
        _triangle(c, shoulder, tips[0], wrist, S["skin"], sag=0.05)
        for i in range(len(tips) - 1):                # the sheet between each pair of fingers
            _triangle(c, tips[i], tips[i + 1], wrist, S["skin"])
        for i in range(len(tips) - 1):                # the trailing edge, following the same scallop
            a_, b_ = np.array(tips[i], float), np.array(tips[i + 1], float)
            w_ = np.array(wrist, float)
            prev = None
            for k in range(13):
                tt = k / 12.0
                e = a_ + (b_ - a_) * tt
                e = e + (w_ - e) * (0.15 * 4.0 * tt * (1.0 - tt))
                if prev is not None:
                    bones.append((tuple(prev), tuple(e), 0.5 * u, S["skin_edge"]))
                prev = e
        # and the sheet from the last finger back to the ankle, which is what makes it a BAT wing
        # rather than a bird's - the membrane runs all the way to the leg
        ankle = (cx + side * 1.6 * u, roof - 3.0 * u, cz + 0.4 * u)
        _triangle(c, tips[-1], ankle, wrist, S["skin"])
        # ...and the sheet on the BODY side of the arm. The wing is a quadrilateral - shoulder,
        # wrist, last fingertip, ankle - and only two of its three triangles were being drawn, so a
        # hole sat between each wing and the body exactly where the arm meets the flank.
        _triangle(c, shoulder, ankle, wrist, S["skin"], sag=0.0)
        # the FINGER BONES go on LAST. They were drawn before the sheets, so every membrane
        # fill painted over them and they survived only as broken dashes scattered across the
        # wing - which reads as damage, not as structure. A bat wing is legible precisely
        # because you can see the fingers through it, so they have to be the top layer.
        for a_, b_, r_, k_ in bones:
            c.line(a_, b_, r_, k_)

    # ---- NO random speckle. 14% of the membrane used to be repainted `skin_edge` for tone, and
    # `skin_edge` is black_wool: against a brown sheet that is not tone, it is a scatter of holes,
    # and that is what it looked like in the world. The wing gets its variation from the finger
    # bones over it and the dark scalloped trailing edge around it, both of which mean something.
    if p.get("hang"):
        hx_, hy_, hz_ = (float(v) for v in p["hang"])
        c.world_origin = (int(round(hx_ - cx)), int(round(hy_ - roof)), int(round(hz_ - cz)))
    elif p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    # its head points at the FLOOR, so "facing" says nothing useful; the view that
    # matters is the one looking along z, straight at the spread wings
    c.meta = {"kind": "bat", "scale": sc, "spread": spread, "profile_view": "face",
                     "features_built": {"wings": 2, "fingers": fingers * 2, "ears": 2,
                                        "claws": 6, "eyes": 2}}
    return c
