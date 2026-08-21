"""An axolotl on the pond bank - the lush-caves creature, at creature scale.

WHY AN AXOLOTL, WHERE EIGHT MAMMALS FAILED. This system fails where identity is COMPOUND
VOLUMETRIC MUSCLE and succeeds where identity is hardware, a plane, or a pattern. An axolotl is
all three: six flat gill fronds, a laterally-compressed tail fin, a wide flat head and splayed
salamander limbs - the gecko category, which this medium renders natively. The otter's identity
is a pose needing water it cannot legally occupy, and a beaver is a rodent barrel four blocks
from a fifty-block rodent. The axolotl is also the ONE candidate that gets to be pink: the
flamingo proved hue-clash against moss is what reads in lantern light, and a pale leucistic
body stays paler than the flamingo's saturated pink, so the two do not twin.

And on a Minecraft server the naming test is instant - axolotls ARE the lush-caves mob.

SIZE COMES FROM THE GILLS. The finest feature is a frond: it needs ~4 cells of length and 2 of
width to read as a frill rather than as fuzz (the ladybird's spot-spacing lesson - features at
minimum size EXIST but merge), three per side need a head ~8 wide to attach to, and the body
follows from the head. That puts total length at ~26 and height at ~8: half the capybara, and
it does not dwarf its own pond.

THE BODY CONFORMS TO THE BANK, THE OVERHANG STAYS OUT OF THE WATER. Belly height per station is
the smoothed real ground; stations whose column is water keep the belly one clear course above
the surface, so the snout can hang over the shallows while not one water cell is replaced -
water is protected, and the pond's guard lanterns sit inside it.
"""
from __future__ import annotations

import math

from .canvas import Canvas
from .vertical import Ctx, World

AXOLOTL = {
    "under": None,             # capture/composite the bank is read from - required
    "at": None,                # [x, z] the body centroid stands over - required
    "look_at": None,           # [x, z] the head points toward - required
    "length": 26.0,            # nose to tail tip, along the (curved) spine
    "body_w": 9.0,             # widest, across the barrel
    "body_h": 6.5,             # belly to back, before the fin
    "curve": 30.0,             # degrees of plan-curve over the whole body; straight is inert
    "gill_len": 6.5,
    "seed": 0,

    # the MINECRAFT leucistic axolotl's own colour language, which is what makes the naming
    # instant on a server: pale pink body, white belly, MAGENTA tail membrane, red gill frills.
    # The first build's fin was white and read as a mohawk - a fin is a MEMBRANE, darker than
    # the body, not a highlight. All cheap wool; the flamingo owns saturated pink+red+black,
    # this stays pale so the two read as different animals from across the pond.
    "body": "pink_wool",
    "belly": "white_wool",
    "fin": "magenta_wool",
    "gills": "red_wool",
    "gill_tip": "magenta_wool",
    "eye": "black_wool",
    "smile": "magenta_wool",   # the mouth seam - half of what makes an axolotl an axolotl
}

_PASSABLE = {"air", "cave_air", "void_air", "vine", "short_grass", "tall_grass", "fern",
             "large_fern", "moss_carpet", "azalea", "flowering_azalea", "poppy", "dandelion"}


def _free(ctx: Ctx, x, y, z) -> bool:
    return ctx.name_at(int(x), int(y), int(z)) in _PASSABLE


def _ground(ctx: Ctx, x, z, y_top=58, y_bot=24):
    """(surface y, is_water) for a column. Water counts as a surface here - the belly must know
    where the pond starts - but is never footing."""
    for y in range(y_top, y_bot - 1, -1):
        n = ctx.name_at(int(x), y, int(z))
        if n not in _PASSABLE:
            return y, n in ("water", "ice")
    return None, False


def _spine(p):
    """Stations along a gently curved spine, centred so the body centroid lands on `at`.

    The panel retired the jaguar for a spine that was a straight rule - the most inert shape
    available. The curve here is the whole-body arc of a salamander mid-turn."""
    ax, az = (float(v) for v in p["at"])
    lx, lz = (float(v) for v in p["look_at"])
    phi0 = math.atan2(lx - ax, lz - az)                # heading of the NOSE, in plan
    L = float(p["length"])
    curve = math.radians(float(p["curve"]))
    n = max(24, int(L * 2))
    pts, x, z = [], 0.0, 0.0
    for i in range(n + 1):
        t = i / n
        # THE HEAD IS STRAIGHT AND THE TAIL CARRIES ALL THE CURVE. The face must lie on the
        # block grid: gaze down a cardinal axis and the front is a true flat plane. Curved
        # through the skull (or aimed diagonally), the face is a staircase of corners in game -
        # eyes at different depths, the smile stepping - which is exactly the "blob head-on"
        # review. An orthographic render along the body axis CANNOT show this failure; only
        # the grid can.
        phi = phi0 + curve * max(0.0, t - 0.28) / 0.72
        pts.append((x, z, t))
        # t=0 is the NOSE, so the walk goes TAIL-ward: opposite the heading. Stepped along it
        # instead, the body extended INTO the gaze and the animal faced away from its own pond.
        x -= math.sin(phi) * (L / n)
        z -= math.cos(phi) * (L / n)
    mx = sum(q[0] for q in pts) / len(pts)
    mz = sum(q[1] for q in pts) / len(pts)
    # nose at t=0 points AT look_at, so walk the spine backward from the nose
    return [(ax + (q[0] - pts[0][0]) - (mx - pts[0][0]), az + (q[1] - pts[0][1]) - (mz - pts[0][1]), q[2])
            for q in pts], phi0


def _half_width(t, W):
    """Wide flat head, a real NECK PINCH, barrel, then a tail drawn out to a point. Without the
    pinch the head blended straight into the body and the animal read as a worm with a face."""
    if t < 0.04:                                       # the FACE is the full-width plane; only
        return W * (0.40 + 0.06 * (t / 0.04))          # the outermost step is chamfered, or the
                                                       # nose protrudes and the mouth fills it
                                                       # edge to edge - a magenta blob, again
    if t < 0.20:                                       # the skull: as wide as the body itself
        return W * 0.46
    if t < 0.30:                                       # the pinch behind the gills
        return W * (0.46 - 0.10 * (1 - math.cos(math.pi * (t - 0.20) / 0.10)) / 2)
    if t < 0.62:
        return W * (0.36 + 0.12 * math.sin(math.pi * (t - 0.30) / 0.32))
    u = (t - 0.62) / 0.38
    return max(0.6, W * 0.36 * (1.0 - u) ** 1.15)


def _height(t, H):
    """Low flat head, domed barrel, tail kept tall by the fin ridge."""
    if t < 0.24:
        return H * 0.62
    if t < 0.60:
        return H * (0.62 + 0.38 * math.sin(math.pi * (t - 0.24) / 0.36) ** 0.8)
    u = (t - 0.60) / 0.40
    return max(2.0, H * (0.62 - 0.30 * u))


def build_axolotl(cfg: dict, donors=None) -> Canvas:
    p = {**AXOLOTL, **cfg}
    for k in ("under", "at", "look_at"):
        if not p.get(k):
            raise ValueError(f"axolotl needs params.{k}")
    ctx = Ctx(p["under"])
    W2, H = float(p["body_w"]) / 2.0, float(p["body_h"])
    stations, phi0 = _spine(p)

    # ---- belly line: the smoothed real bank, clamped one clear course over any water
    raw = []
    for sx, sz, t in stations:
        g, wet = _ground(ctx, round(sx), round(sz))
        raw.append((g if g is not None else 39, wet))
    belly = []
    for i in range(len(raw)):
        window = [raw[j][0] for j in range(max(0, i - 3), min(len(raw), i + 4))]
        y = sum(window) / len(window)
        if raw[i][1]:
            y = max(y, raw[i][0] + 1.0)                # over water: hover, never displace
        belly.append(y + 1.0)                          # +1: the belly RESTS ON the ground course

    w = World()
    body_cells = set()
    top_at = {}                                        # (x,z) -> highest BODY cell, for the fin

    def put_body(x, y, z, name):
        x, y, z = int(round(x)), int(round(y)), int(round(z))
        if _free(ctx, x, y, z) and (x, y, z) not in body_cells:
            w.put(x, y, z, name)
            body_cells.add((x, y, z))
        return (x, y, z)

    def put_run(x, y, z, name, prev):
        """put_body, with the path to the PREVIOUS cell stitched one axis at a time. A sampled
        line steps diagonally, diagonal neighbours are not 6-connected, and ear tips have
        broken off this way before."""
        cur = (int(round(x)), int(round(y)), int(round(z)))
        if prev is not None and cur != prev:
            sx_, sy_, sz_ = prev
            while (sx_, sy_, sz_) != cur:
                if sx_ != cur[0]:
                    sx_ += 1 if cur[0] > sx_ else -1
                elif sy_ != cur[1]:
                    sy_ += 1 if cur[1] > sy_ else -1
                else:
                    sz_ += 1 if cur[2] > sz_ else -1
                put_body(sx_, sy_, sz_, name)
        else:
            put_body(*cur, name)
        return cur

    # ---- the body: superellipse sections swept along the spine, belly flat, back domed
    for i, (sx, sz, t) in enumerate(stations):
        hw = _half_width(t, W2 * 2.0)
        hh = _height(t, H)
        j = min(i + 1, len(stations) - 1)
        dx, dz = stations[j][0] - sx, stations[j][1] - sz
        nrm = math.hypot(dx, dz) or 1.0
        nx, nz = -dz / nrm, dx / nrm                   # plan normal to the spine
        # the SKULL is a wide flat U - but not a slab. Exponent 6 keeps the top flat across the
        # middle and rounds ONE step down at the cheeks, which is the "little more rounded"
        # the in-game review asked for; the barrel eases back to a rounded 2.6.
        if t < 0.20:
            n_sec = 6.0
        elif t < 0.32:
            n_sec = 2.6 + 3.4 * (0.32 - t) / 0.12
        else:
            n_sec = 2.6
        u = -hw
        while u <= hw:
            span = (1.0 - abs(u / hw) ** n_sec) ** (1 / n_sec) if hw > 0 else 0
            top = hh * span
            v = 0.0
            while v <= top:
                mat = p["belly"] if v < 0.8 else p["body"]
                if t >= 0.93:
                    mat = p["fin"]                     # the tail ENDS in membrane, not in a
                                                       # pink point - the tip is all fin
                cx_, cy_, cz_ = put_body(sx + nx * u, belly[i] + v, sz + nz * u, mat)
                if (cx_, cz_) not in top_at or top_at[(cx_, cz_)] < cy_:
                    top_at[(cx_, cz_)] = cy_
                v += 0.5
            u += 0.4

    # ---- the fin: a one-cell blade along the rear half of the spine, over tail AND rump -
    # the single feature that says amphibian rather than fat lizard. Based on the BUILT top of
    # each column, not on the float the sections were sampled from - the float and the rounded
    # cells drift a course apart and the blade breaks loose (the detached-ossicone rule again).
    fin_n = 0
    prev = None
    for i, (sx, sz, t) in enumerate(stations):
        if t < 0.46:
            continue
        col = (int(round(sx)), int(round(sz)))
        base = top_at.get(col)
        if base is None:
            continue
        rise = 3 if t > 0.85 else (2 if t > 0.60 else 1)
        for k in range(rise):
            prev = put_run(col[0], base + 1 + k, col[1], p["fin"], prev)
            fin_n += 1

    # ---- legs: four, splayed like a salamander's, elbows out, feet ON the bank
    legs = 0
    for t_leg, ahead in ((0.30, 1.6), (0.58, -1.8)):
        i = min(range(len(stations)), key=lambda j: abs(stations[j][2] - t_leg))
        sx, sz, _ = stations[i]
        j = min(i + 1, len(stations) - 1)
        dx, dz = stations[j][0] - sx, stations[j][1] - sz
        nrm = math.hypot(dx, dz) or 1.0
        dxu, dzu = dx / nrm, dz / nrm
        nx, nz = -dzu, dxu
        hw = _half_width(t_leg, W2 * 2.0)
        for side in (-1, 1):
            hipx, hipz = sx + nx * side * (hw - 0.6), sz + nz * side * (hw - 0.6)
            footx = hipx + nx * side * 3.0 + dxu * ahead
            footz = hipz + nz * side * 3.0 + dzu * ahead
            g, wet = _ground(ctx, round(footx), round(footz))
            if g is None or wet:                       # a foot in the pond is a replaced water
                footx, footz = hipx + nx * side * 1.2, hipz + nz * side * 1.2
                g, wet = _ground(ctx, round(footx), round(footz))
                if g is None or wet:
                    continue
            steps = 6
            prev = None
            for s in range(steps + 1):
                f = s / steps
                lx = hipx + (footx - hipx) * f
                lz = hipz + (footz - hipz) * f
                ly = (belly[i] + 1.5) * (1 - f) + (g + 1) * f
                prev = put_run(lx, ly, lz, p["body"], prev)
                put_body(lx, ly + (0 if f > 0.6 else 1), lz, p["body"])
            for toe in (-0.9, 0.0, 0.9):               # three toe nubs, STITCHED off the foot -
                prev = (int(round(footx)), g + 1, int(round(footz)))
                put_run(footx + dxu * 0.9 + nx * toe, g + 1, footz + dzu * 0.9 + nz * toe,
                        p["belly"], prev)
            legs += 1

    # ---- gills: three planar fronds a side, ROOTED inside the skull and grown outward.
    # Anything clinging is anchored to the built surface - the detached-ossicone rule.
    gi = min(range(len(stations)), key=lambda j: abs(stations[j][2] - 0.21))
    sx, sz, _ = stations[gi]
    j = min(gi + 1, len(stations) - 1)
    dx, dz = stations[j][0] - sx, stations[j][1] - sz
    nrm = math.hypot(dx, dz) or 1.0
    dxu, dzu = dx / nrm, dz / nrm                      # toward the TAIL
    nx, nz = -dzu, dxu
    glen = float(p["gill_len"])
    fronds = 0
    head_hw = _half_width(0.19, W2 * 2.0)
    head_top = belly[gi] + _height(0.19, H)
    filaments = 0
    for side in (-1, 1):
        for elev, sweep in ((42.0, 26.0), (18.0, 48.0), (-6.0, 68.0)):
            e, s = math.radians(elev), math.radians(sweep)
            vx = (nx * side * math.cos(s) + dxu * math.sin(s)) * math.cos(e)
            vz = (nz * side * math.cos(s) + dzu * math.sin(s)) * math.cos(e)
            vy = math.sin(e)
            # ROOTED AT THE SKULL SURFACE, running its whole length outward. Rooted at the spine
            # the fronds spent themselves inside the head and nine red cells reached the air.
            rootx = sx + nx * side * (head_hw - 0.8)
            rootz = sz + nz * side * (head_hw - 0.8)
            rooty = head_top - 1.2
            n = int(glen * 3)
            prev = (int(round(rootx - vx)), int(round(rooty - vy)), int(round(rootz - vz)))
            for st in range(n + 1):
                f = st / n
                r = f * glen
                mat = p["gill_tip"] if f > 0.66 else p["gills"]
                gx, gy, gz = rootx + vx * r, rooty + vy * r, rootz + vz * r
                prev = put_run(gx, gy, gz, mat, prev)
                if f < 0.75:                           # thickened VERTICALLY near the base:
                    put_body(gx, gy + 1, gz, mat)      # a frill both sides can afford - the
                                                       # in-plan offset fed one side into the
                                                       # skull and the gills came out lopsided
                # FILAMENTS: short barbs trailing off the stalk, which is what turns three red
                # sticks into a frill. Stitched off the stalk cell so they cannot detach. None
                # at the very tip - a barb past the frond's end is a stray pixel, not a frill.
                if st in (n // 3, (2 * n) // 3):
                    fp = (int(round(gx)), int(round(gy)), int(round(gz)))
                    put_run(gx + dxu * 1.5, gy + 0.7, gz + dzu * 1.5, mat, fp)
                    filaments += 1
            fronds += 1

    # ---- eyes: ONE dark bead each side, every solid neighbour forced pale - the bar-eye and
    # the eye-lost-in-the-coat failures both live in the animals file. The bead goes on the
    # FRONT-TOP CORNER of the face and must have an exposed front or top face: a cell one step
    # back is anatomically fine and invisible from exactly the view a face is for.
    ei = min(range(len(stations)), key=lambda j: abs(stations[j][2] - 0.07))
    ex, ez, _ = stations[ei]
    ffx, ffz = stations[0][0] - stations[1][0], stations[0][1] - stations[1][1]
    ffn = math.hypot(ffx, ffz) or 1.0
    ffx, ffz = ffx / ffn, ffz / ffn                    # out of the face, in plan
    eyes = 0
    hw = _half_width(0.07, W2 * 2.0)
    ty = int(round(belly[ei] + _height(0.07, H) - 1.0))
    for side in (-1, 1):
        # THE BEAD IS THE FRONTMOST BODY CELL OF ITS CHEEK BAND, so by construction nothing can
        # stand in front of it. Chosen by proximity instead, the tail's curve shifts the
        # centroid, the head line drifts half a block, and one bead lands a cell deep - painted
        # over by its own ring from exactly the head-on view. That shipped once.
        want_lat = side * (hw - 0.4)
        band = []
        for c in body_cells:
            if c[1] not in (ty, ty - 1):
                continue
            lat = (c[0] - ex) * nx + (c[2] - ez) * nz
            depth = (c[0] - ex) * ffx + (c[2] - ez) * ffz
            if abs(lat - want_lat) <= 1.3 and depth >= 0:
                band.append((depth, c[1], c))
        if not band:
            continue
        band.sort(key=lambda b: (-b[0], -b[1]))
        spot = band[0][2]
        w.put(*spot, p["eye"])
        eyes += 1
        for ddx, ddy, ddz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0)):
            nb = (spot[0] + ddx, spot[1] + ddy, spot[2] + ddz)
            if nb in body_cells:
                w.put(*nb, p["belly"])

    # ---- the SMILE: one course of darker seam across the front of the muzzle, below the eyes
    # and above the white chin. Half of what makes an axolotl an axolotl is that it looks
    # pleased about something, and no amount of gill work substitutes for it.
    im = min(range(len(stations)), key=lambda j: abs(stations[j][2] - 0.05))
    nosex, nosez, _ = stations[im]
    fx_, fz_ = stations[0][0] - stations[1][0], stations[0][1] - stations[1][1]
    fn = math.hypot(fx_, fz_) or 1.0
    fx_, fz_ = fx_ / fn, fz_ / fn                      # out of the face, in plan
    mouth_y = int(round(belly[im] + 1.2))              # LOW on the face, right on the chin line
                                                       # - a mouth at mid-height reads as a nose
    cand = []
    for (x, y, z) in body_cells:
        if y != mouth_y or math.hypot(x - nosex, z - nosez) > 4.5:
            continue
        outward = (int(round(x + fx_ * 1.2)), y, int(round(z + fz_ * 1.2)))
        if outward not in body_cells:                  # a front-facing surface cell
            perp = abs((x - nosex) * -fz_ + (z - nosez) * fx_)
            cand.append((perp, x, y, z))
    smile = 0
    if len(cand) >= 3:
        for _, x, y, z in sorted(cand)[:7]:
            w.put(x, y, z, p["smile"])
            smile += 1

    pruned = _prune_severed(w)
    return w.canvas({"kind": "axolotl", "profile_view": "top", "facing": [round(math.sin(phi0)), round(math.cos(phi0))],
                     "features_built": {"gill_fronds": fronds, "filaments": filaments,
                                        "legs": legs, "fin": fin_n, "eyes": eyes,
                                        "smile": smile, "pruned": pruned}})


def _prune_severed(w: World) -> int:
    """Drop cells 6-disconnected from the main body. The build conforms to real terrain and
    real foliage, and a cell placed through a gap in a leaf canopy is severed from the animal
    the moment the skipped cells around it are not placed - it belongs to the tree, not to the
    design. Same rule as `_cling`, applied at the end where it cannot be forgotten."""
    from collections import deque
    cells = set(w.cells)
    best = set()
    seen = set()
    for c in cells:
        if c in seen:
            continue
        q, comp = deque([c]), {c}
        seen.add(c)
        while q:
            x, y, z = q.popleft()
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                n = (x + dx, y + dy, z + dz)
                if n in cells and n not in seen:
                    seen.add(n)
                    comp.add(n)
                    q.append(n)
        if len(comp) > len(best):
            best = comp
    dropped = [c for c in cells if c not in best]
    for c in dropped:
        del w.cells[c]
    return len(dropped)
