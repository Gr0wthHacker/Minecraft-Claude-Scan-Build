"""THE SILHOUETTE RIDES: the three park pieces whose whole job is to be recognised from far away.

**WHY THESE THREE, AND WHY THEY ARE NOT ANIMALS.** `gen/park.py` settled that a park's variety
comes from ARCHITECTURE, and this file is the part of that argument that has to carry across the
zone. A stall reads at fifteen blocks; a skyline piece has to read at a hundred and fifty, from an
angle nobody chose, against open sky - which is exactly the case this repo has measured most often
and got wrong most often. The download corpus says it in one number: the builds strangers pick out
are the ones whose identity is an OUTLINE - a wing, a neck, a ring - and every one of the eight
mammals that failed was a compound volume. So:

    A RING, A COLUMN AND A CONE. All three are voxel primitives, and all three are read from
    OUTSIDE against sky rather than from a path at ground level.

That is not a stylistic preference, it is the one thing this project has evidence for. A ferris
wheel is a circle two cells thick - the medium draws it natively and no amount of tuning is
involved; a drop tower is a straight taper with openings in it, which is the void tower's own
finding (*regularity and openings, not damage*); a carousel is a cone with alternating wedges,
which is a pattern on a convex mass, the ladybird's category.

**EVERY STRUCTURE CARRIES ITS OWN GROUND.** A skyblock plot is VOID. Nothing here may assume
terrain, so each kind lays a pad at h=-1 and everything above it is carried to that pad by legs,
A-frames or a plinth - the wheel's rim hangs 45 courses up and there is a measured line of blocks
from every rim cell to the floor. `tests` in the throwaway harness assert ONE 6-connected
component, because a floating fragment is invisible in every render this repo owns.

**THE FAIRGROUND PALETTE IS THE LAND'S OWN.** Colours come from `park.LANDS[land]`, so a wheel in
the Hollow is a black ring with soul lanterns and a wheel on the Midway is red-and-white - the same
geometry reading as two different places, which is the whole argument for lands over signage. The
only additions are the sixteen wools (all cheap) for gondolas, canopy wedges and carousel mounts,
and `glass_pane` (ok) for the drop tower's glazed panels. Nothing here is expensive, nothing is
currency, nothing falls.

GEOMETRY, identical to `park.py` because a facing bug is invisible and expensive:

    at       the FRONT-LEFT floor corner, in world coordinates
    facing   the direction the FRONT looks out
    i        along the frontage;  d  from the front INTO the piece;  h  courses up

so `at(i, d, h) = (x - dx*d + sx*i, y + h, z - dz*d + sz*i)`. Round things are placed in the same
frame: `i` and `d` index the piece's own bounding footprint and the circle is centred inside it, so
`at` still means the front-left corner and all four facings build the same object.

**VARIETY IS HASHED, NEVER RANDOM.** Gondola colours, canopy wedges, mount colours, shaft
weathering and which tower panels are glazed all come from `canvas.hash01` of the cell or the
index, so two runs of the same config are the same build and two different pieces are different
ones. `random` would make a design that cannot be regenerated, which on an island of remaining-work
designs is the same as a design that cannot be built.
"""
from __future__ import annotations

import math

from .. import blocks
from .canvas import Canvas, hash01
from .park import LANDS, SIGN_WIDTH, _Frame, _STEP, _sign
from .vertical import Ctx, World

_DIR = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}
_LEAN = {"east": "west", "west": "east", "north": "south", "south": "north"}

# The sixteen cheap wools, checked against `blocks.spendable` / `palette.tier` before being written
# down. A gondola, a hobby horse and a canopy wedge are the three places on this island where a
# SATURATED colour is correct rather than loud - everything else here is the land's own stone.
BRIGHT = ["red_wool", "yellow_wool", "light_blue_wool", "lime_wool", "orange_wool",
          "magenta_wool", "cyan_wool", "pink_wool", "purple_wool", "white_wool",
          "blue_wool", "green_wool"]

RIDES = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "wheel",
    "facing": "east",
    "land": "midway",
    "title": None,
    "lines": None,
    "min_run": 3,               # a trim course shorter than this is not drawn at all
    "sign": True,
    # SIZE IS None AND EACH KIND SUPPLIES ITS OWN FLOOR. `diameter` means two different things to
    # a ferris wheel and a carousel - 41 and 25 - and one shared default silently built a carousel
    # forty-one across, whose mounts then stood at a radius where the canopy is two courses up:
    # twelve hobby horses floating in six pieces. A default that is right for one kind and wrong
    # for another is worse than no default.
    "diameter": None,           # wheel 41 (>= 40 is the brief) / carousel 25; forced odd
    "spokes": 12,
    "cars": 12,
    "shaft": None,              # drop: the tower's side, odd (9)
    "height": None,             # drop: shaft courses (54); the cap adds ~13 on top
    "mounts": 12,
}


# ------------------------------------------------------------------ small shared helpers

def _full(w: World, x, y, z) -> bool:
    """Is there a FULL CUBE here. `w.has` is not the same question.

    A lantern hangs from a full block and a wall sign is fixed to one; `has` answers true for a
    fence, a stair and a lantern, all of which hold up neither. The lowland's own note: a lamp
    under a slab cap reads as 'hanging from air' in the audit, because a slab is not a full block.
    """
    n = w.name(x, y, z)
    return bool(n) and blocks.is_full_cube(n)


def _signed(w, f, pal, i, d, h, facing, front, back=()) -> bool:
    """`park._sign`, with the support tested for being a FULL CUBE rather than merely present."""
    fdx, fdz = _STEP[facing]
    x, y, z = f.at(i, d, h)
    if not _full(w, x - fdx, y, z - fdz):
        return False
    return _sign(w, f, pal, i, d, h, facing, front, back)


def _lamp(w, x, y, z, light) -> bool:
    """A lantern that works out for itself whether it stands or hangs, and refuses if neither.

    Rule 9 exists because the plaza's lamp posts shipped `hanging=true` on all three lands - a lamp
    looking for a block ABOVE it, finding open sky. The question is answered from the world here
    rather than from the caller's memory of what it built.
    """
    if w.has(x, y, z):
        return False
    if _full(w, x, y - 1, z):
        w.put(x, y, z, light, hanging="false", waterlogged="false")
        return True
    if _full(w, x, y + 1, z):
        w.put(x, y, z, light, hanging="true", waterlogged="false")
        return True
    return False


def _ground(w, f, pal, i0, i1, d0, d1, h=-1):
    """The pad. A skyblock plot is VOID, so every kind brings its own floor and every leg lands
    on it. Paved on a WORLD-ALIGNED checker so two adjacent pieces line up rather than seaming."""
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            x, y, z = f.at(i, d, h)
            w.put(x, y, z, pal["ground"] if (x + z) % 2 == 0 else pal["path"])
            n += 1
    return n


def _line2(u0, v0, u1, v1):
    """A 6-CONNECTED 2-D path. Bresenham alone steps diagonally, and a diagonal step is not
    connectivity - the ear-tip lesson, and the reason the lowland root shipped as 26 components.
    Where both coordinates would move at once an intermediate cell is inserted."""
    du, dv = u1 - u0, v1 - v0
    n = max(abs(du), abs(dv))
    if n == 0:
        return [(u0, v0)]
    out, prev = [(u0, v0)], (u0, v0)
    for k in range(1, n + 1):
        u = u0 + int(round(du * k / n))
        v = v0 + int(round(dv * k / n))
        if (u, v) == prev:
            continue
        if u != prev[0] and v != prev[1]:
            out.append((u, prev[1]))
        out.append((u, v))
        prev = (u, v)
    return out


def _annulus(R, thick=2.0):
    """The rim: every cell whose radius falls in a band `thick` wide, inside R.

    A voxel circle is the one shape this medium draws natively and it needs no smoothing, no
    tuning and no reference table - which is exactly why the skyline piece is a ring.
    """
    lo = (R - thick) ** 2
    out = []
    for a in range(-R, R + 1):
        for b in range(-R, R + 1):
            r2 = a * a + b * b
            if lo < r2 <= R * R:
                out.append((a, b))
    return out


def _disc(R):
    return [(a, b) for a in range(-R, R + 1) for b in range(-R, R + 1) if a * a + b * b <= R * R]


def _wedge(a, b, n=12):
    """Which of `n` angular wedges this cell falls in. What makes a canopy or a rim read as a
    FAIRGROUND rather than as a roof: one colour is a roof, two alternating is a big top."""
    th = math.atan2(b, a)
    return int(((th + math.pi) / (2 * math.pi)) * n) % n


def _wdir(f, di, dd) -> str:
    """A local (along-frontage, into-the-piece) unit vector as a world compass direction.

    Everything oriented - a stair's tall side, a pane's connections, a seat's facing - has to be
    derived through the frame or it is right at one facing and wrong at the other three, which no
    render in this repo can show.
    """
    vx = f.sx * di - f.dx * dd
    vz = f.sz * di - f.dz * dd
    if abs(vx) >= abs(vz):
        return _DIR[(1 if vx > 0 else -1, 0)]
    return _DIR[(0, 1 if vz > 0 else -1)]


def _pane(w, f, x, y, z, di, dd):
    """A glass pane with its connections set ALONG the wall it fills.

    With every side false a pane renders as a lone post rather than as glazing - the campanile's
    own note. The connection is game-derived in world, so this is for the RENDER and for anyone
    reading the litematic; `work.INTENTIONAL` rightly drops it again.
    """
    a, bkt = _wdir(f, di, dd), _wdir(f, -di, -dd)
    w.put(x, y, z, "glass_pane", waterlogged="false", **{a: "true", bkt: "true"})


def _stair_run(w, f, pal, cells, min_run, half="top", block=None):
    """Lay a stair course only where it makes a RUN of `min_run`, never on scattered cells.

    The deck soffit drew a coffer grid per cell and produced 215 runs of which 184 were one or two
    cells - confetti, in the loudest block available. `cells` is a list of (key, order, i-or-d,
    facing); a run is consecutive `order` within one `key`, which is the line's OWN axis. Scoring
    it across its own axis is the inversion that shipped once and made every run measure 1.
    """
    by_key = {}
    for (key, order, pos, face) in cells:
        by_key.setdefault(key, []).append((order, pos, face))
    laid = 0
    for key, row in by_key.items():
        row.sort()
        run = []
        for item in row:
            if run and item[0] == run[-1][0] + 1:
                run.append(item)
            else:
                laid += _flush_run(w, run, pal, min_run, half, block)
                run = [item]
        laid += _flush_run(w, run, pal, min_run, half, block)
    return laid


def _flush_run(w, run, pal, min_run, half, block):
    if len(run) < min_run:
        return 0
    for (_order, pos, face) in run:
        w.put(pos[0], pos[1], pos[2], block or pal["stair"],
              facing=face, half=half, shape="straight", waterlogged="false")
    return len(run)


# ------------------------------------------------------------------ the ferris wheel

def _wheel(w: World, p: dict, ctx) -> dict:
    """A FERRIS WHEEL: a ring standing in the frontage plane on two A-frames carried to the floor.

    **THE RING IS THE WHOLE PIECE AND IT IS DRAWN, NOT MODELLED.** A two-cell annulus is a circle
    at any diameter, so the only decisions left are the ones that make it read as a machine rather
    than as a hoop: spokes to a hub (a hoop with no spokes is a letter O), cars around the outside
    (which is what says it turns), and A-frames straddling it in DEPTH (which is what says it is
    held up). All three are outside-the-rim or inside-the-rim by construction, so the silhouette
    stays a clean circle with bumps - never a circle with a mess in it.

    **THE CARS HANG OUTSIDE THE RIM, and that is a geometry decision rather than a style one.** A
    car hung below its own rim point crosses the rim at every angle except the top and the bottom -
    at three o'clock the cell four courses under the rim is inside the ring - so the wheel would
    have twelve boxes buried in its own structure. Mounted radially outward they can never
    intersect it at any angle, and the bottom car lands one course above the boarding platform,
    which is what makes the platform a place rather than a plinth.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    mr = int(p["min_run"])

    D = max(41, int(p["diameter"] or 41) | 1)
    R = D // 2
    ncar = max(8, int(p["cars"]))
    nspoke = max(8, int(p["spokes"]))

    CAR_R = R + 3                       # car centres ride this radius; outer reach CAR_R + 1
    W = 2 * (CAR_R + 1) + 1             # the footprint the cars need, not the one the ring needs
    ci = W // 2
    DEPTH = 6                           # frame | . | rim rim | . | frame
    RIM_D = (2, 3)
    FRAME_D = (0, DEPTH - 1)
    rim_bottom = 5
    hh = rim_bottom + R                 # the axle

    _ground(w, f, pal, -2, W + 1, -3, DEPTH + 1)

    # ---- the boarding platform, one course proud of the pad, skirted in stairs.
    plat = range(ci - 8, ci + 9)
    for i in plat:
        for d in range(DEPTH):
            w.put(*f.at(i, d, 0), pal["path"] if (i + d) % 2 else pal["ground"])
    skirt = [(0, i, f.at(i, 0, 0), f.facing) for i in plat]
    _stair_run(w, f, pal, skirt, mr, half="bottom")
    for d in range(DEPTH):              # a rail down both sides, the front left open to board
        for i in (ci - 8, ci + 8):
            w.put(*f.at(i, d, 1), pal["fence"])
    for i in plat:
        w.put(*f.at(i, DEPTH - 1, 1), pal["fence"])

    # ---- the rim. Alternating wedges: one colour is a hoop, two is a fairground.
    ring = _annulus(R, 2.0)
    ca, cb = pal["canopy"]
    for (a, b) in ring:
        blk = ca if _wedge(a, b, 12) % 2 == 0 else cb
        for d in RIM_D:
            w.put(*f.at(ci + a, d, hh + b), blk)

    # ---- hub and spokes. The hub spans the WHOLE depth so it ties both A-frames to the wheel;
    # without that the two frames are separate pieces standing next to a floating ring.
    for (a, b) in _disc(3):
        for d in range(DEPTH):
            w.put(*f.at(ci + a, d, hh + b), pal["trim"])
    for k in range(nspoke):
        th = 2 * math.pi * k / nspoke
        ei = int(round((R - 1) * math.cos(th)))
        eb = int(round((R - 1) * math.sin(th)))
        for (a, b) in _line2(0, 0, ei, eb):
            if a * a + b * b < 9:
                continue
            for d in RIM_D:
                w.put(*f.at(ci + a, d, hh + b), pal["beam"])

    # ---- the A-frames, one in front of the wheel and one behind it, feet on the pad.
    foot = R - 3
    for d in FRAME_D:
        for s in (-1, 1):
            for (a, b) in _line2(s * foot, 0, 0, hh):
                w.put(*f.at(ci + a, d, b), pal["post"])
                if b == 0:              # a footing pad, so a leg lands on something
                    for j in (-1, 1):
                        w.put(*f.at(ci + a + j, d, 0), pal["trim"])
        for tie_h in (hh // 3, (2 * hh) // 3):
            span = int(round(foot * (1 - tie_h / hh)))
            if span * 2 + 1 >= mr:
                for a in range(-span, span + 1):
                    w.put(*f.at(ci + a, d, tie_h), pal["trim"])

    # ---- the cars. Radially outward of the rim so they can never cross it, hung on a strut.
    cars, car_lamps = 0, 0
    for m in range(ncar):
        th = 2 * math.pi * m / ncar + math.pi / (2 * ncar)
        cia = int(round(CAR_R * math.cos(th)))
        cib = int(round(CAR_R * math.sin(th)))
        for (a, b) in _line2(int(round((R - 1) * math.cos(th))),
                             int(round((R - 1) * math.sin(th))), cia, cib):
            for d in RIM_D:
                w.put(*f.at(ci + a, d, hh + b), pal["trim"])

        # TWELVE OF ONE BOX IS A ROW OF ONE BOX. Colour, roof tone, depth and whether the car
        # carries an awning are all hashed off the car's index and the piece's own world position,
        # so the ring is varied, two wheels in one park differ, and the same config regenerates
        # cell for cell. `random` would give a design that cannot be built twice.
        body = BRIGHT[int(hash01(m, R, f.x, f.z) * len(BRIGHT))]
        roof = pal["trim"] if hash01(m, 7, f.z) < 0.5 else BRIGHT[(m * 5 + 3) % len(BRIGHT)]
        style = int(hash01(m, 13, f.x) * 3)
        d_lo, d_hi = (1, DEPTH - 2) if style != 2 else (1, DEPTH - 3)   # a pod, or a full cabin
        i0, h0 = ci + cia, hh + cib
        for di in (-1, 0, 1):
            for d in range(d_lo, d_hi + 1):
                w.put(*f.at(i0 + di, d, h0 - 1), pal["beam"])        # floor
                w.put(*f.at(i0 + di, d, h0 + 1), roof)               # roof
                edge = di in (-1, 1) or d in (d_lo, d_hi)
                if not edge:
                    continue
                if di == 0 and d == d_lo:                            # the way in
                    continue
                w.put(*f.at(i0 + di, d, h0), body)
        awn = [f.at(i0 + di, d_lo - 1, h0 + 1) for di in (-1, 0, 1)]
        # AN AWNING OVER THE DOOR - three cells, exactly the shortest run rule 9 allows, and
        # the only thing on this piece that leans. All three or none: two of them, where an
        # A-frame member already stands in the third, is the scattered course rule 9 is about.
        #
        # AND IT IS GATED ON `min_run` LIKE EVERY OTHER TRIM COURSE. Placed with a bare `put` it
        # bypassed the gate entirely, so a config asking for runs of five still got this run of
        # three - the one place in the piece where the documented rule and the code disagreed,
        # and invisible because the default `min_run` is exactly 3.
        if style == 1 and mr <= 3 and not any(w.has(*cell) for cell in awn):
            for cell in awn:
                w.put(*cell, pal["stair"], facing=_wdir(f, 0, 1),
                      half="top", shape="straight", waterlogged="false")
        # A LIGHT RIDING THE RIM, UNDER WHICHEVER OF THE CAR'S THREE FLOOR COLUMNS IS FREE.
        # The centre column alone lost two of twelve and said nothing: the car's own radial
        # strut climbs through that column at some angles, and the bottom car hangs over the
        # boarding platform, which owns the cell outright. All three columns carry the same
        # floor overhead, so a side column is the same lamp. The bottom car still cannot have
        # one - there is a platform where the lamp would go - so the count is REPORTED rather
        # than assumed, because a lamp that quietly is not there is the failure this file keeps
        # writing rules about.
        for lit_di in (0, -1, 1):
            if _lamp(w, *f.at(i0 + lit_di, (d_lo + d_hi) // 2, h0 - 2), pal["light"]):
                car_lamps += 1
                break
        cars += 1

    # ---- a lamp ring on the rim, interleaved between the cars, each on its own BRACKET.
    #
    # A lantern needs a full block above it or below it, and on a circle neither is true at the
    # sides: at three o'clock the cell under a rim cell is outside the annulus and the cell over it
    # is too, so a naive ring lit only the top and the bottom arcs and quietly skipped the rest -
    # `_lamp` returning False is exactly the "does nothing, quietly" failure this repo keeps
    # writing rules about. A one-cell bracket proud of the rim makes the answer the same at every
    # angle, and it is drawn from the rim outward so it can never be a floating stub.
    #
    # **AND THE LAMP MUST BE TRIED ON BOTH SIDES OF THE TIP.** The bracket alone did not deliver
    # that promise, and the measurement is the exact inverse of the paragraph above: hanging the
    # lantern under the tip placed 15 of 24, and every one of the nine that vanished was on the
    # TOP arc. "Below the tip" points away from the hub on the lower half - open air - and back
    # TOWARD it on the upper half, where it lands on the bracket's own radial line or back inside
    # the annulus. Whichever of the two neighbours is inward is the one that is occupied, so the
    # other is free by construction: try under the tip, then over it, and a refusal on both is a
    # real obstruction rather than an artefact of which way round the circle we are.
    lit = 0
    for k in range(ncar * 2):
        th = math.pi * k / ncar
        ba = int(round((R + 1) * math.cos(th)))
        bb = int(round((R + 1) * math.sin(th)))
        for (a, b) in _line2(int(round((R - 1) * math.cos(th))),
                             int(round((R - 1) * math.sin(th))), ba, bb):
            for d in RIM_D:
                if not w.has(*f.at(ci + a, d, hh + b)):
                    w.put(*f.at(ci + a, d, hh + b), pal["trim"])
        if (_lamp(w, *f.at(ci + ba, RIM_D[0], hh + bb - 1), pal["light"])
                or _lamp(w, *f.at(ci + ba, RIM_D[0], hh + bb + 1), pal["light"])):
            lit += 1

    # ---- entrance pylons, which are also the only thing a nameplate can hang on out here.
    title = str(p.get("title") or "BIG WHEEL").upper()
    signs = 0
    for k, i in enumerate((1, W - 2)):
        for h in range(6):
            w.put(*f.at(i, -1, h), pal["post"])
        w.put(*f.at(i, -1, 6), pal["trim"])
        _lamp(w, *f.at(i, -1, 7), pal["light"])
        lines = ([title[:SIGN_WIDTH], "", "board below", ""] if k == 0
                 else [title[:SIGN_WIDTH], "", f"{ncar} cars", f"{D} across"])
        if p.get("sign", True) and _signed(w, f, pal, i, -2, 3, f.facing, lines):
            signs += 1

    return {"kind": "wheel", "width": W, "depth": DEPTH, "diameter": D,
            "top": hh + CAR_R + 1, "cars": cars, "spokes": nspoke, "rim_lamps": lit,
            "rim_lamp_slots": ncar * 2, "car_lamps": car_lamps, "signs": signs,
            "contract": "a two-cell ring spoked to a hub, straddled by two A-frames whose feet "
                        "reach the pad, with cars mounted OUTSIDE the rim so the silhouette stays "
                        "a circle and the lowest car lands on the boarding platform"}


# ------------------------------------------------------------------ the drop tower

def _drop(w: World, p: dict, ctx) -> dict:
    """A DROP TOWER: a latticed shaft with real openings, a car near the top, a house and a cap.

    The void tower settled the shape of this and it is followed rather than re-derived: a plinth,
    regular coursework, openings that are OPENINGS, a string course per tier, a corbelled overhang
    and a crowned top. Its first attempt was a sheared jagged stub and was rejected on sight as
    *"a tossed grouping of vague blocks"* - what makes voxels read as a building is regularity.

    **THE OPENINGS ARE LEFT EMPTY BY THE WALL LOOP.** Building the ring and cutting holes
    afterwards repaints cells that already exist; the void tower's crenellations shipped as a plain
    drum for exactly that reason and nothing about the code looked wrong.

    **AND THE GLAZING IS DECIDED PER PANEL, NOT PER CELL.** Hashed per cell it is confetti - the
    deck soffit's 184 runs of one or two cells, in glass. One hash per (tier, face) glazes a whole
    panel or none of it, so the tower reads as a building with some windows in rather than as a
    building with a rash.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    mr = int(p["min_run"])

    S = max(7, int(p["shaft"] or 9) | 1)
    H = max(48, int(p["height"] or 54))
    W, DP = S + 6, S + 4
    i0, d0 = (W - S) // 2, (DP - S) // 2
    QUEUE = 5

    _ground(w, f, pal, -1, W, -QUEUE - 1, DP)

    # ---- the base station: a walled room round the shaft's foot, with the door left empty.
    door = {W // 2 - 1, W // 2, W // 2 + 1}
    for i in range(W):
        for d in range(DP):
            if not (i in (0, W - 1) or d in (0, DP - 1)):
                continue
            corner = i in (0, W - 1) and d in (0, DP - 1)
            w.put(*f.at(i, d, -1), pal["trim"])
            for h in range(5):
                if d == 0 and i in door and h < 4:
                    continue
                w.put(*f.at(i, d, h), pal["post"] if corner else pal["wall"])
    # roof over the ring between the station wall and the shaft, never over the shaft itself
    for i in range(-1, W + 1):
        for d in range(-1, DP + 1):
            if i0 <= i < i0 + S and d0 <= d < d0 + S:
                continue
            w.put(*f.at(i, d, 5), pal["trim"])
    # A CORNICE UNDER IT - AND IT LEAVES THE DOOR COLUMNS AS A PLAIN LINTEL BAND. Run across them
    # it replaces the top wall course with stairs, and the nameplate over the door then has a STAIR
    # behind it rather than a full block, so the sign is silently refused and the entrance ends up
    # unnamed. The gatehouse already knew this: a lintel band over an opening reads as an arcade,
    # and it is the only thing a front sign has to hang on.
    corn = []
    for i in range(W):
        for d in range(DP):
            if not (i in (0, W - 1) or d in (0, DP - 1)):
                continue
            if d == 0 and i in door:
                continue
            face = f.inward(i, d, W, DP)
            if face:
                corn.append(((d, "i") if d in (0, DP - 1) else (i, "d"),
                             i if d in (0, DP - 1) else d, f.at(i, d, 4), _LEAN[face]))
    _stair_run(w, f, pal, corn, mr, half="top")

    # ---- the shaft. Corner posts always; a full ring on the string courses; between them a
    # panel with two real openings per face.
    solid_k = {0, 1, S // 2, S - 2, S - 1}
    glazed, opened = 0, 0
    for h in range(H):
        band = (h % 6 == 0) or h >= H - 2
        proud = h % 12 == 0 and h > 0
        for i in range(i0, i0 + S):
            for d in range(d0, d0 + S):
                ei = i in (i0, i0 + S - 1)
                ed = d in (d0, d0 + S - 1)
                if not (ei or ed):
                    continue
                corner = ei and ed
                if corner:
                    w.put(*f.at(i, d, h), pal["post"])
                    continue
                # which face, and how far along it - the run's OWN axis
                if ed:
                    k, face_ix, nrm = i - i0, (0 if d == d0 else 1), (0, 1 if d == d0 else -1)
                else:
                    k, face_ix, nrm = d - d0, (2 if i == i0 else 3), (1 if i == i0 else -1, 0)
                # THE WAY INTO THE SHAFT IS TESTED FIRST, and that order is the whole of it. Asked
                # after the solid test, the door's own middle column is already claimed by
                # `solid_k` and the check can never fire: the tower shipped with two thin slots
                # either side of a solid pier and NO DOOR, aligned perfectly with the station's
                # own doorway, and every render showed a lattice that looked exactly right.
                if d == d0 and abs(k - S // 2) <= 1 and 1 <= h <= 3:
                    opened += 1
                    continue
                if band or k in solid_k:
                    x, y, z = f.at(i, d, h)
                    # WEATHERING IS HASHED ON THE CELL. Hashed on the COURSE a whole course comes
                    # out one material and the shaft is horizontal stripes; the deck soffit shipped
                    # exactly that once and nothing about the code looked wrong.
                    hot = hash01(x, y, z) < (0.30 if band else 0.16)
                    if band:
                        # ...but the band's OWN material changes by tier, so fifty-four courses of
                        # tower are not nine identical storeys stacked.
                        blk = pal["trim"] if hash01(f.x, f.z, h // 6, 5) < 0.62 else pal["post"]
                    else:
                        blk = pal["trim"] if hot else pal["wall"]
                    w.put(x, y, z, blk)
                    continue
                # an OPENING. Glazed or open, decided once per panel.
                tier = h // 6
                if hash01(f.x, f.z, tier, face_ix) < 0.34:
                    _pane(w, f, *f.at(i, d, h), *(-nrm[1], nrm[0]))
                    glazed += 1
                else:
                    opened += 1
        if proud:
            for i in range(i0 - 1, i0 + S + 1):
                for d in range(d0 - 1, d0 + S + 1):
                    if i in (i0 - 1, i0 + S) or d in (d0 - 1, d0 + S):
                        w.put(*f.at(i, d, h), pal["trim"])

    # ---- the car, parked at a string course so its floor has a full ring to hold on to.
    car_h = (H - 12) - ((H - 12) % 6)
    seats, rails = [], 0
    for i in range(i0 - 2, i0 + S + 2):
        for d in range(d0 - 2, d0 + S + 2):
            ring = max(abs(i - (i0 + S // 2)), abs(d - (d0 + S // 2))) - S // 2
            if ring not in (1, 2):
                continue
            w.put(*f.at(i, d, car_h), pal["accent"] if ring == 1 else pal["trim"])
            if ring == 2:
                w.put(*f.at(i, d, car_h + 1), pal["fence"])
                rails += 1
            else:
                # A SEAT'S RUN GOES ALONG ITS OWN FACE. Keyed the other way round every run
                # measures one cell and the whole course is dropped as confetti - the deck
                # soffit's inverted axis, which shipped once and made a measurement and the code
                # acting on it agree with each other perfectly.
                ai, ad = abs(i - (i0 + S // 2)), abs(d - (d0 + S // 2))
                di = (1 if i > i0 + S // 2 else -1) if ai > ad else 0
                dd = 0 if di else (1 if d > d0 + S // 2 else -1)
                key, order = (("ni", i), d) if di else (("nd", d), i)
                seats.append((key, order, f.at(i, d, car_h + 1), _wdir(f, di, dd)))
    nseat = _stair_run(w, f, pal, seats, mr, half="bottom")

    # ---- corbel, top house, cap. Each course steps OUT, which is what a corbel is; a plain
    # extruded box with a hat on it is the thing this is avoiding.
    #
    # **A CORBEL COURSE MUST INCLUDE THE SHAFT'S OWN RING, not just the ring outside it.** Drawn as
    # the 11x11 perimeter alone it sits one cell clear of a 9x9 shaft on every side and touches
    # nothing: the house, the cap and both corbels shipped as three separate lumps 54 courses up,
    # 500-odd blocks of building hanging in the sky. Nothing about the code looked wrong and every
    # block state was legal - it is the connectivity check that catches this and only that.
    for k, h in enumerate((H, H + 1)):
        for i in range(i0 - 2, i0 + S + 2):
            for d in range(d0 - 2, d0 + S + 2):
                ring = max(abs(i - (i0 + S // 2)), abs(d - (d0 + S // 2))) - S // 2
                if 0 <= ring <= k + 1:
                    w.put(*f.at(i, d, h), pal["trim"])
    hi0, hd0, HS = i0 - 1, d0 - 1, S + 2
    for i in range(hi0, hi0 + HS):                     # the machine-room floor is a RING; the
        for d in range(hd0, hd0 + HS):                 # shaft stays open all the way up
            if i in (hi0, hi0 + HS - 1) or d in (hd0, hd0 + HS - 1):
                w.put(*f.at(i, d, H + 2), pal["trim"])
    for h in range(H + 3, H + 7):
        for i in range(hi0, hi0 + HS):
            for d in range(hd0, hd0 + HS):
                ei = i in (hi0, hi0 + HS - 1)
                ed = d in (hd0, hd0 + HS - 1)
                if not (ei or ed):
                    continue
                mid = (abs(i - (hi0 + HS // 2)) <= 1) if ed else (abs(d - (hd0 + HS // 2)) <= 1)
                if mid and h in (H + 4, H + 5):
                    continue                            # the winch-room windows
                w.put(*f.at(i, d, h), pal["post"] if (ei and ed) else pal["wall"])
    house_c = []
    for i in range(hi0, hi0 + HS):
        for d in range(hd0, hd0 + HS):
            ei = i in (hi0, hi0 + HS - 1)
            ed = d in (hd0, hd0 + HS - 1)
            if not (ei or ed):
                continue
            face = f.inward(i - hi0, d - hd0, HS, HS)
            if face:
                house_c.append(((d, "i") if ed else (i, "d"), i if ed else d,
                                f.at(i, d, H + 6), _LEAN[face]))
    _stair_run(w, f, pal, house_c, mr, half="top")
    cap = HS // 2
    for k in range(cap + 1):
        blk = _cap_band(pal, k)
        for i in range(hi0 + k, hi0 + HS - k):
            for d in range(hd0 + k, hd0 + HS - k):
                w.put(*f.at(i, d, H + 7 + k), blk)
    top = H + 7 + cap
    _lamp(w, *f.at(hi0 + HS // 2, hd0 + HS // 2, top + 1), pal["light"])

    # ---- the queue: a switchback of rail in front of the door, lit on its posts.
    for lane in range(2):
        d = -2 - lane * 2
        lo, hi = (1, W - 3) if lane == 0 else (2, W - 2)
        for i in range(lo, hi + 1):
            w.put(*f.at(i, d, 0), pal["fence"])
    for i in (1, W - 2):
        for h in range(3):
            w.put(*f.at(i, -QUEUE, h), pal["post"])
        w.put(*f.at(i, -QUEUE, 3), pal["trim"])
        _lamp(w, *f.at(i, -QUEUE, 4), pal["light"])
    for i in range(1, W - 1):
        if i in door:
            continue                     # the way IN is left empty by the loop, never punched
        w.put(*f.at(i, -QUEUE, 0), pal["fence"])

    # ---- lights under the station eaves, and the signs.
    for i in (1, W - 2):
        for d in (1, DP - 2):
            _lamp(w, *f.at(i, d, 4), pal["light"])
    title = str(p.get("title") or "DROP TOWER").upper()
    lines = list(p.get("lines") or ["hold the bar", "one drop", "mind the step"])
    signs = 0
    if p.get("sign", True):
        signs += _signed(w, f, pal, W // 2, -1, 4, f.facing,
                         [title[:SIGN_WIDTH], "", f"{top + 1} up", ""])
        signs += _signed(w, f, pal, W // 2 + 2, 1, 2, f.back,
                         ["RULES"] + [str(s)[:SIGN_WIDTH] for s in lines[:3]])

    return {"kind": "drop", "width": W, "depth": DP, "shaft": S, "height": H,
            "top": top + 1, "car_h": car_h, "glazed": glazed, "openings": opened,
            "rails": rails, "seats": nseat, "signs": signs,
            "contract": "a latticed shaft with real openings and glazed panels, a ring car parked "
                        "at a string course, a corbelled top house with a stepped cap, and a "
                        "queue rail leading to the one door"}


def _cap_band(pal, k):
    """The cap's banding: the land's two canopy colours alternating up the pyramid."""
    a, b = pal["canopy"]
    return a if k % 2 == 0 else b


# ------------------------------------------------------------------ the carousel

def _carousel(w: World, p: dict, ctx) -> dict:
    """A CAROUSEL: a raised disc, a banded column, a wedge-striped cone, and mounts on poles.

    **THE CONE IS THE PIECE AND THE STRIPES ARE THE IDENTITY.** A cone in one colour is a roof; the
    same cone in alternating radial wedges is a big top, and nothing else in the build has to do
    any work. That is the ladybird's category exactly - a pattern on a convex mass, read from the
    PLAN, which is the view voxels give away free.

    **A CONE MUST CARRY ITS RISERS OR IT IS NOT ONE PIECE.** Ring r sits at apex-r and ring r+1 at
    apex-r-1: orthogonal neighbours one course apart, which is DIAGONAL in 3-D and not connected.
    Each ring therefore also fills the course above it, so consecutive rings share a face. Same
    lesson as the twisted root that shipped as 26 components.

    **AND EVERY MOUNT'S POLE RUNS THROUGH TO THE CANOPY**, which is both what a carousel looks like
    and what ties twelve small masses into the one component.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    mr = int(p["min_run"])

    Dm = max(15, int(p["diameter"] or 25) | 1)
    R = Dm // 2
    RC = R + 1                          # the canopy oversails the deck by one
    W = 2 * RC + 1
    c = W // 2
    # THE EAVE IS ELEVEN ABOVE THE DECK WHATEVER THE DIAMETER, so a wider carousel
    # raises its own cone instead of dropping it onto the mounts.
    APEX = RC + 11
    nm = max(8, int(p["mounts"]))
    ring_r = max(4, R - 2)

    def h_of(a, b):
        return APEX - int(round(math.sqrt(a * a + b * b)))

    # ---- pad, then the deck one course proud of it: radial wedges, not a slab.
    for (a, b) in _disc(RC):
        w.put(*f.at(c + a, c + b, -1), pal["trim"] if a * a + b * b > R * R else pal["ground"])
    deck = set()
    for (a, b) in _disc(R):
        r = math.hypot(a, b)
        if r > R - 1.2 or (a == 0 and b == 0):
            blk = pal["accent"]
        elif _wedge(a, b, 12) % 2 == 0:
            blk = pal["ground"]
        else:
            blk = pal["path"]
        w.put(*f.at(c + a, c + b, 0), blk)
        deck.add((a, b))

    # ---- the rail: the deck's own outer edge, with four ways in.
    gates, fenced = 0, 0
    for (a, b) in sorted(deck):
        if all((a + u, b + v) in deck for (u, v) in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        if abs(a) <= 1 and abs(b) > 1:
            if a == 0:
                w.put(*f.at(c + a, c + b, 1), pal["gate"],
                      facing=_wdir(f, 0, -1) if b > 0 else _wdir(f, 0, 1),
                      open="true", in_wall="false", powered="false")
                gates += 1
            continue
        if abs(b) <= 1 and abs(a) > 1:
            if b == 0:
                w.put(*f.at(c + a, c + b, 1), pal["gate"],
                      facing=_wdir(f, 1, 0) if a > 0 else _wdir(f, -1, 0),
                      open="true", in_wall="false", powered="false")
                gates += 1
            continue
        w.put(*f.at(c + a, c + b, 1), pal["fence"])
        fenced += 1
    # A step up at each of the four gates - three cells, exactly the shortest run allowed. THE PAD
    # IS LAID UNDER THEM FIRST: the disc reaches (R+1, 0) and not (R+1, 1), so two stairs in every
    # flight would have stood on nothing. A skyblock plot is void; anything outside the disc has to
    # bring its own floor.
    steps = []
    for (ui, ud) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for t in (-1, 0, 1):
            a = ui * (R + 1) + (0 if ui else t)
            b = ud * (R + 1) + (0 if ud else t)
            w.put(*f.at(c + a, c + b, -1), pal["trim"])
            steps.append((("s", ui, ud), t + 1, f.at(c + a, c + b, 0), _wdir(f, ui, ud)))
    _stair_run(w, f, pal, steps, mr, half="bottom")

    # ---- the centre column: banded, with a stair corbel top and bottom. It runs to APEX-2 so its
    # crown meets the canopy's r=1 ring at APEX-1; a course short of that the cone hangs off
    # nothing but its own outer rings.
    for h in range(1, APEX - 1):
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                band = (h % 4 in (0, 1))
                w.put(*f.at(c + a, c + b, h), pal["accent"] if band else pal["trim"])
    for k in (3, APEX - 4):
        corb = []
        for (ui, ud) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for t in (-1, 0, 1):
                a = ui * 2 + (0 if ui else t)
                b = ud * 2 + (0 if ud else t)
                corb.append((("c", k, ui, ud), t + 1, f.at(c + a, c + b, k),
                             _wdir(f, -ui, -ud)))
        _stair_run(w, f, pal, corb, mr, half="top")

    # ---- the mounts. One colour each, varied between them, all left-right symmetric about
    # their own axis; the pole runs deck to canopy, which is both correct and what connects them.
    #
    # **THE MOUNT'S LENGTH IS GRADED BY ITS OWN ARC, and it has to be.** Twelve five-cell horses
    # round a ring 44 cells long is 3.7 cells each: they touch, and in the PLAN - the view this
    # medium gives away free - the ring reads as one continuous bar of wool with no horses in it
    # at all. Every check passed, because a fused ring is still one connected piece of legal cheap
    # blocks. So a crowded ring gets ponies and a roomy one gets full horses, and either way there
    # is a clear cell between them. It is `tools/scale.py`'s rule seen from the side: a feature
    # needs a minimum of space to read, and below it the honest move is to build a smaller feature.
    arc = 2 * math.pi * ring_r / nm
    barrel, tailed = ((-1, 0, 1), True) if arc >= 6.0 else                      ((-1, 0, 1), False) if arc >= 4.5 else ((0, 1), False)
    mounts = []
    for m in range(nm):
        th = 2 * math.pi * m / nm
        a = int(round(ring_r * math.cos(th)))
        b = int(round(ring_r * math.sin(th)))
        tu = (-math.sin(th), math.cos(th))
        if abs(tu[0]) >= abs(tu[1]):
            ui, ud = (1 if tu[0] > 0 else -1), 0
        else:
            ui, ud = 0, (1 if tu[1] > 0 else -1)
        # ONE COLOUR EACH, DIFFERENT BETWEEN THEM, and some of them rear. A mount is a small convex
        # mass on a pole - a barrel, a neck, a head, a tail - and at five cells long that is all
        # the anatomy there is room for. Trying for more is the eight-mammal mistake at 1/20 scale.
        coat = BRIGHT[int(hash01(m, nm, f.x, f.z) * len(BRIGHT))]
        base = 4 if hash01(m, 3, f.z) < 0.5 else 5      # some ride high, some low
        rear = hash01(m, 9, f.x) < 0.34                 # ...and some rear, head up a course
        for h in range(1, h_of(a, b)):                  # the pole, deck to canopy
            w.put(*f.at(c + a, c + b, h), pal["post"])
        for t in barrel:                                # barrel
            for h in (base, base + 1):
                w.put(*f.at(c + a + ui * t, c + b + ud * t, h), coat)
        w.put(*f.at(c + a + ui * 2, c + b + ud * 2, base + 1), coat)     # neck
        w.put(*f.at(c + a + ui * 2, c + b + ud * 2, base + 2), coat)     # head
        if rear:
            w.put(*f.at(c + a + ui * 2, c + b + ud * 2, base + 3), coat)
        if tailed:
            w.put(*f.at(c + a - ui * 2, c + b - ud * 2, base + 1), coat)  # tail
        mounts.append((coat, base, rear))

    # ---- the canopy: alternating wedges, every ring carrying its own riser.
    # TWO COLOURS ALTERNATING, never six: one colour is a roof, two is a big top, and a wedge each
    # from a list of twelve is a beach ball. The second colour is hashed per build, so two
    # carousels in one park are the same geometry and different places.
    ca = pal["canopy"][0]
    alt = BRIGHT[int(hash01(f.x, f.z, 11) * len(BRIGHT))]
    for (a, b) in _disc(RC):
        blk = ca if _wedge(a, b, 12) % 2 == 0 else alt
        h = h_of(a, b)
        w.put(*f.at(c + a, c + b, h), blk)
        w.put(*f.at(c + a, c + b, h + 1), blk)

    # ---- the eave fringe. THE RUN HERE IS THE WHOLE RING, measured along its own axis: it is one
    # closed course of ~56 cells, not a scattered course, which is what rule 9 is about.
    eave = [(a, b) for (a, b) in _disc(RC) if int(round(math.hypot(a, b))) == RC]
    if len(eave) >= mr:
        for (a, b) in eave:
            face = _wdir(f, -1 if a > 0 else (1 if a < 0 else 0), 0) if abs(a) >= abs(b) \
                else _wdir(f, 0, -1 if b > 0 else 1)
            w.put(*f.at(c + a, c + b, h_of(a, b) - 1), pal["stair"],
                  facing=face, half="top", shape="straight", waterlogged="false")

    # ---- lights hung under the canopy, one ring in from the eave.
    lit = 0
    for k in range(8):
        th = 2 * math.pi * k / 8 + math.pi / 8
        a = int(round((RC - 2) * math.cos(th)))
        b = int(round((RC - 2) * math.sin(th)))
        if int(round(math.hypot(a, b))) == RC:
            continue                    # that course belongs to the eave fringe
        if _lamp(w, *f.at(c + a, c + b, h_of(a, b) - 1), pal["light"]):
            lit += 1

    title = str(p.get("title") or "CAROUSEL").upper()
    signs = 0
    if p.get("sign", True):
        signs += _signed(w, f, pal, c, c - 2, 6, f.facing,
                         [title[:SIGN_WIDTH], "", f"{nm} mounts", "all ages"])
        signs += _signed(w, f, pal, c, c + 2, 6, f.back,
                         [title[:SIGN_WIDTH], "", "hold the pole", ""])

    return {"kind": "carousel", "width": W, "depth": W, "diameter": Dm, "top": APEX + 1,
            "mounts": len(mounts), "colours": len({m[0] for m in mounts}),
            "shapes": len(set(mounts)), "mount_arc": round(arc, 2), "gates": gates,
            "rail": fenced, "lamps": lit, "signs": signs,
            "contract": "a raised disc ringed by rail with four gated steps, a banded column, a "
                        "wedge-striped cone whose every ring carries its riser, and mounts whose "
                        "poles run from the deck to the canopy"}


BUILDERS = {
    "wheel": _wheel,
    "drop": _drop,
    "carousel": _carousel,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**RIDES, **cfg}
    if not p.get("at"):
        raise ValueError("bigwheel needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown bigwheel kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    # `kind` IS EXCLUDED FROM THE MERGE ON PURPOSE. Every builder returns its own bare `kind`, and
    # spread last it overwrites the namespaced one - the sidecar then reads `wheel`, which is also
    # what `casino` calls one of its games. A sidecar's kind is how a design is identified later;
    # two subsystems answering to one word is a collision waiting for whoever reads it next.
    return w.canvas({
        "kind": f"bigwheel/{p['kind']}",
        "ride": p["kind"],
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("kind", "contract", "unverified")},
    })
