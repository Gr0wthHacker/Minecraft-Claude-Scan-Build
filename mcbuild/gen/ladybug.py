"""A seven-spot ladybird on a leaf, hanging in the void under the island.

Why a ladybird is a good fit here, when eight mammals were not. This system fails where identity is
COMPOUND VOLUMETRIC MUSCLE - a cat's shoulder, a bear's haunch - and succeeds where identity is
hardware, a plane, or a pattern. A ladybird is the purest pattern case in nature: its whole
identity is red, seven black spots, a seam down the middle and a black head. The shell under that
pattern is a single convex dome, which is a voxel primitive, not a blend of five muscle groups.
Nothing here needs proportion measured to a percent - it needs the spots to be the right size.

And the canonical view of a ladybird IS the plan view, which is the one voxels give away free.

    SIZE COMES FROM THE SPOTS. The finest feature is a spot, a spot needs about 3 blocks across to
    read as a disc rather than as speckle, and a seven-spot elytra is roughly five spot-diameters
    wide. That puts the floor at ~15 blocks of shell width, and everything else follows from it.
    Below that you get a red dome with pepper on it.

THE LEAF IS NOT DECORATION - it is the scale reference. A red dome alone in the void is an abstract
object of unknown size; the same dome on a leaf is instantly a beetle, because everyone knows how
big a leaf is next to a bug. So the blade has to stay VISIBLE past the bug: the first build had a
26-long leaf under a 17-long beetle, the bug covered 65% of it, and all that showed was a green
fringe. The bug sits well back now and a clear length of blade and its point run out beyond.

The whole thing carries its own ground, the way `bat.perch` does: a small ragged clod of the
island's own rock with moss on it, a stalk, and the leaf. That is what let it be sited in open void
rather than wherever there happened to be a ledge. NOT dirt - dirt is currency on this server
(`blocks.spendable` returns False for it), so the clod is stone, cobble and moss like the bat's.

Two traps this cost, both of which produced a clean audit and a wrong build:

  ROUND() IS BANKER'S ROUNDING. The clod's centre landed on x.5, and round(11.5) == round(12.5)
  == 12 while round(13.5) == 14 - so every other column was skipped and the lump came out as
  eighteen separate one-wide towers. Every centre here is an INTEGER, and offsets are added to it.

  `c.get` RETURNS -1 OUT OF BOUNDS, AND -1 IS TRUTHY. Searching downward for the top of the shell
  from two courses above the canvas ceiling "found" a block immediately, every time, so all seven
  spot caps were painted into thin air above the beetle and the shell came out plain red. Use
  `c.solid()`, which is on Canvas for exactly this reason.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01

LADYBUG = {
    "size": [35, 22, 29],
    "seed": 0,
    "scale": 1.0,
    # world coordinate of the canvas corner. A bespoke generator states this itself, or the
    # pipeline writes no sidecar - and with no sidecar there is no origin, no in-context audit
    # and no `/cscan place`.
    "at": None,
    # ...or give `root`, the world block the clod's lowest course occupies. Anchoring by the thing
    # that holds it up beats anchoring by the corner of its box.
    "root": None,

    # SEVEN spots need LENGTH, not just width. At 17 long the elytra behind the pronotum was 12
    # blocks, four rows of spots sat 3 apart, and 3-block spots at 3-block spacing TOUCH - they
    # merged into one black mass and the beetle read as a black beetle with red veins. 21 long
    # gives a 16-block elytra, four rows 4 apart, and a clear block of red between every spot.
    "shell_l": 21.0,             # along X, head at +X
    "shell_w": 17.0,             # across Z
    "shell_h": 8.0,              # the dome
    # A real seven-spot's spots are about a FIFTH of the elytra's width, so on a 15-wide
    # shell that is ~3 blocks across. At 2.4 the seven caps overlapped into one black mass
    # with red showing through as veins - the beetle read as a black beetle.
    # 1.6 admits only offsets summing to <=2, which is a PLUS, not a disc. 1.85 takes the
    # full 3x3x3 (the corner sums to 3) and reads as a round spot at this size.
    "spot_r": 1.85,              # >= ~1.5 or they turn to pepper; <= ~2.0 or they merge
    "pronotum": 0.23,            # front fraction of the body that is black head and thorax
    "legs": 3,                   # per side

    "leaf_l": 29.0,              # must stay well clear of shell_l or the leaf is a fringe
    "leaf_w": 23.0,
    "leaf_at": 0.40,             # how far along the blade the beetle stands
    "leaf_curl": 0.18,           # how far the blade's edges lift
    "leaf_tilt": 0.12,           # nose-down tilt, so the back turns toward a viewer below
    "stem_h": 5.0,
    "clod_r": 4.6,
    "clod_h": 4,
    "vine_room": 3,              # courses left UNDER the clod for the vines to hang into

    # ALL CHEAP TIER, and no gravity block anywhere: this hangs in open void, and `red_sand` is
    # exactly the sort of thing that would pour the whole design into the abyss (`blocks.falls`).
    "shell": "red_wool",         # the only real red in the game at cheap tier
    "spots": "black_wool",
    "pale": "white_wool",        # the two cheek patches - a ladybird's head is not plain black
    "blade": "lime_wool",        # a FRESH leaf. green_wool is 17 RGB off moss and vanished on it
    "vein": "green_wool",        # ...so the veins are the dark green and the blade is the light
    "stalk": "green_wool",
    "rock": ["stone", "cobblestone", "mossy_cobblestone"],
    "moss": "moss_block",
    "vine": "vine",
}


def _cling(c: Canvas, x, y, z, blk):
    """Place a cell only where it will actually touch the thing it belongs to.

    Anything clinging must be anchored to the surface that was BUILT. This project has paid for
    that four times over - a mane that came off as seven floating fragments, detached ossicones, a
    tail 45 cells clear, and a bat whose eyes sat perfectly inside its own skull.
    """
    x, y, z = int(round(x)), int(round(y)), int(round(z))
    if c.solid(x, y, z):
        c.put(x, y, z, blk)
        return True
    for dx, dy, dz in ((0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
        if c.solid(x + dx, y + dy, z + dz):
            c.put(x, y, z, blk)
            return True
    return False


def build_ladybug(cfg: dict, donors=None) -> Canvas:
    p = {**LADYBUG, **cfg}
    sc = float(p.get("scale", 1.0))
    SX, SY, SZ = (max(8, int(round(v * sc))) for v in p["size"])
    seed = int(p["seed"])
    c = Canvas(SX, SY, SZ, donors)
    st = c.state
    S = {k: st(p[k]) for k in ("shell", "spots", "pale", "blade", "vein", "stalk", "moss", "vine")}
    rock = [st(b) for b in p["rock"]]
    h = lambda *q: hash01(*q, seed)

    cz = SZ // 2                                  # INTEGER centres - see the header
    u = sc
    clod_h = int(round(float(p["clod_h"]) * sc))
    clod_r = float(p["clod_r"]) * sc
    stem_h = float(p["stem_h"]) * sc
    y0 = int(round(float(p["vine_room"]) * sc))   # the clod's lowest course; vines hang below it
    L = float(p["leaf_l"]) * sc
    W = float(p["leaf_w"]) * sc
    leaf_x0 = int(round(3.0 * u))                 # the blade runs from here toward +X
    clod_x, clod_z = leaf_x0 + int(round(3.0 * u)), cz

    # ---- THE CLOD. Its own scrap of ground, so the design needs nothing to stand on. Ragged, and
    # widest near the top, so it reads as a piece that broke off rather than a parked sphere.
    for k in range(clod_h + 1):
        f = k / max(1, clod_h)
        r = clod_r * (0.45 + 0.80 * f - 0.30 * f * f)
        for dx in range(-int(r) - 2, int(r) + 3):
            for dz in range(-int(r) - 2, int(r) + 3):
                if (dx * dx + dz * dz) ** 0.5 > r * (0.85 + 0.20 * h(dx, 0, dz, 5)):
                    continue
                blk = S["moss"] if k == clod_h else rock[int(h(dx, k, dz, 9) * len(rock)) % len(rock)]
                c.put(clod_x + dx, y0 + k, clod_z + dz, blk)

    # a few vines off the rim. Each starts only where there is rock to hang from and stops the
    # moment the run breaks - placed blind they come away as separate floating threads.
    for j in range(max(3, int(round(5 * sc)))):
        a = h(j, 1, 2, 13) * 6.283
        rx = clod_x + int(round(clod_r * 0.8 * np.cos(a)))
        rz = clod_z + int(round(clod_r * 0.8 * np.sin(a)))
        if not c.solid(rx, y0, rz):
            continue
        for k in range(1, y0 + 1):
            if not c.solid(rx, y0 - k + 1, rz):
                break
            c.put(rx, y0 - k, rz, S["vine"])

    # ---- THE STALK, arcing up out of the clod and over to the leaf's base.
    top = y0 + clod_h
    base_y = top + stem_h
    c.bezier([(clod_x, top - 0.5, clod_z),
              (clod_x - 0.5 * u, top + stem_h * 0.60, clod_z + 0.5 * u),
              (leaf_x0, base_y, cz)], 1.15 * u, S["stalk"], n=40)

    # ---- THE LEAF. A flat blade with a raised midrib and veins: a sheet, which is what this
    # medium renders natively, and the only thing here that gives the beetle a SCALE.
    curl = float(p["leaf_curl"])
    tilt = float(p["leaf_tilt"])

    def blade_y(lx, lz):
        """the sheet's own height: tilted along its length, curled up across it"""
        return base_y - tilt * (lx - leaf_x0) + curl * (lz - cz) ** 2 / max(1e-6, W * 0.5)

    def half_width(t):
        """an ovate leaf: broad a third of the way along, drawn to a point at the tip"""
        if t <= 0.0 or t >= 1.0:
            return 0.0
        return (W * 0.5) * (np.sin(np.pi * min(1.0, t ** 0.62)) ** 0.85)

    leaf_cells = {}
    for lx in range(leaf_x0, leaf_x0 + int(L) + 1):
        hw = half_width((lx - leaf_x0) / max(1e-6, L))
        if hw < 1.2:
            continue          # a blade one cell wide sheds isolated cells at the base and the tip
        for lz in range(cz - int(hw) - 1, cz + int(hw) + 2):
            if abs(lz - cz) > hw:
                continue
            y = int(round(blade_y(lx, lz)))
            edge = abs(lz - cz) > hw - 1.2
            mid = abs(lz - cz) < 0.9
            # veins: the midrib, and ribs fanning back off it at a constant angle
            rib = abs(((lx - leaf_x0) * 0.55 + abs(lz - cz)) % (4.2 * u)) < 0.9
            c.put(lx, y, lz, S["vein"] if (mid or (rib and not edge)) else S["blade"])
            leaf_cells[(lx, lz)] = y
            if mid:                               # the midrib stands proud, as a real one does
                c.put(lx, y - 1, lz, S["vein"])

    # The blade is a tilted, curled sheet drawn column by column, so neighbouring columns can land
    # two courses apart and leave a seam of holes. Stitch every vertical gap between side-by-side
    # cells, which also welds the stragglers at the rim back onto the sheet.
    for (lx, lz), y in list(leaf_cells.items()):
        for nx, nz in ((lx + 1, lz), (lx, lz + 1), (lx - 1, lz), (lx, lz - 1)):
            ny = leaf_cells.get((nx, nz))
            if ny is None:
                continue
            for yy in range(min(y, ny), max(y, ny) + 1):
                if not c.solid(nx, yy, nz):
                    c.put(nx, yy, nz, S["blade"])

    # ---- THE BEETLE, standing on the blade. Long axis along X, head at +X.
    SL, SW, SH = (float(p[k]) * sc for k in ("shell_l", "shell_w", "shell_h"))
    bug_x = leaf_x0 + int(round(L * float(p["leaf_at"])))
    bug_z = cz
    body_y = leaf_cells.get((bug_x, bug_z), int(base_y)) + 1   # one clear of the blade

    rx, rz, ry = SL / 2.0, SW / 2.0, SH
    for dx in range(-int(rx) - 2, int(rx) + 3):
        for dz in range(-int(rz) - 2, int(rz) + 3):
            for dy in range(0, int(ry) + 2):
                if (dx / rx) ** 2 + (dz / rz) ** 2 + (dy / ry) ** 2 > 1.0:
                    continue
                c.put(bug_x + dx, body_y + dy, bug_z + dz, S["shell"])

    def dome_top(x, z):
        """the built shell's own top at a column, clamped INSIDE the canvas - see the header"""
        for dy in range(min(int(ry) + 1, SY - 1 - body_y), -1, -1):
            if c.solid(x, body_y + dy, z):
                return body_y + dy
        return None

    # PRONOTUM AND HEAD - the black front, with two pale cheek patches so the head does not read
    # as a hole punched in the shell.
    pro = float(p["pronotum"])
    xcut = rx * (1.0 - 2.0 * pro)
    for dx in range(int(xcut), int(rx) + 2):
        for dz in range(-int(rz) - 2, int(rz) + 3):
            for dy in range(0, int(ry) + 2):
                if c.get(bug_x + dx, body_y + dy, bug_z + dz) == S["shell"]:
                    c.put(bug_x + dx, body_y + dy, bug_z + dz, S["spots"])
    for side in (-1, 1):
        px = bug_x + int(round(rx * 0.78))
        for d in (0, 1):
            for dy in (0, 1):
                _cling(c, px - d, body_y + ry * 0.40 + dy, bug_z + side * rz * 0.58, S["pale"])

    # THE ELYTRAL SEAM. One black line down the join of the two wing cases - the single cue that
    # says "beetle" rather than "red pebble", and it costs a dozen blocks.
    for dx in range(-int(rx) - 1, int(xcut) + 1):
        ty = dome_top(bug_x + dx, bug_z)
        if ty is not None and c.get(bug_x + dx, ty, bug_z) == S["shell"]:
            c.put(bug_x + dx, ty, bug_z, S["spots"])

    # THE SEVEN SPOTS, as spherical caps centred ON THE BUILT SURFACE. Projected flat in plan they
    # smear down the steep sides of the dome and stop being round.
    sr = float(p["spot_r"]) * sc
    # spread over the WHOLE elytra, and the middle pair kept off the seam - at 0.26 of the
    # half-width they touched the seam line and the two merged into a bar
    spots = [(0.18, 0.0)]                         # the scutellar spot straddles the seam
    for side in (-1, 1):
        spots += [(0.40, side * 0.62), (0.66, side * 0.40), (0.88, side * 0.62)]
    placed = 0
    for f, zf in spots:
        dxs = xcut - (xcut + rx) * f
        # the z offset is a fraction of the shell's LOCAL half-width, not of its widest. Taken
        # against rz the rear pair sat at 5 where the dome had already narrowed to 4.4, so both
        # fell off the edge and only five of the seven spots ever landed.
        local = rz * (max(0.0, 1.0 - (dxs / rx) ** 2)) ** 0.5
        sx = bug_x + int(round(dxs))
        sz = bug_z + int(round(zf * local))
        ty = dome_top(sx, sz)
        if ty is None:
            continue
        placed += 1
        for ddx in range(-int(sr) - 1, int(sr) + 2):
            for ddz in range(-int(sr) - 1, int(sr) + 2):
                for ddy in range(-int(sr) - 1, int(sr) + 2):
                    if ddx * ddx + ddy * ddy + ddz * ddz > sr * sr:
                        continue
                    if c.get(sx + ddx, ty + ddy, sz + ddz) == S["shell"]:
                        c.put(sx + ddx, ty + ddy, sz + ddz, S["spots"])

    # ---- LEGS. Six, three a side, from under the shell's rim down onto the blade - which is also
    # what makes the beetle and the leaf ONE piece rather than two objects that happen to touch.
    nlegs = int(p["legs"])
    for side in (-1, 1):
        for i in range(nlegs):
            t = (i + 0.5) / nlegs
            lx = bug_x + int(round(rx * (0.62 - 1.35 * t)))
            lz = bug_z + int(round(side * rz * 0.86))
            tx = lx + int(round((1.4 if t < 0.5 else -1.4) * u))
            tz = lz + int(round(side * 2.6 * u))
            ground = leaf_cells.get((tx, tz))
            if ground is None:                    # off the blade - tuck the foot back onto it
                tx, tz = lx, lz + int(round(side * 1.2 * u))
                ground = leaf_cells.get((tx, tz), body_y - 1)
            knee = (lx, body_y + 0.4, lz + side * 1.5 * u)
            c.line((lx, body_y + 0.9, lz), knee, 0.62 * u, S["spots"])
            c.line(knee, (tx, ground + 1, tz), 0.55 * u, S["spots"])

    # ANTENNAE. Short, but they are the difference between a head and a blunt end - and they are
    # grown OFF the built skull rather than drawn from a point in the air, which is how the first
    # pair ended up as four loose black cells hanging in front of the beetle.
    for side in (-1, 1):
        ax, ay, az = bug_x + rx * 0.84, body_y + ry * 0.38, bug_z + side * rz * 0.30
        for step in range(1, 4):
            _cling(c, ax + step * 0.9 * u, ay + step * 0.5 * u, az + side * step * 0.45 * u,
                   S["spots"])

    if p.get("root"):
        wx, wy, wz = (int(v) for v in p["root"])
        c.world_origin = (wx - clod_x, wy - y0, wz - clod_z)
    elif p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    # it is READ FROM ABOVE - the canonical view of a ladybird, and the one voxels give away free -
    # so the review sheet should open on the plan, not on a profile.
    c.meta = {"kind": "ladybug", "scale": sc, "profile_view": "top",
              "features_built": {"spots": placed, "legs": nlegs * 2, "antennae": 2,
                                 "leaf": 1, "seam": 1}}
    return c
