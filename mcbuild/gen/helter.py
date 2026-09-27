"""THE HELTER SKELTER - the Midway's third ride, and the one you actually descend.

    V100-153 x U345-384, the whole rear of Midway column C

Jack, standing in it: *"theres a strip here before the prism area that has these buildings and
this empty plot, i think we can do more with this area thats more impactful to the player, and
cooler."*

**THE PLOT WAS THE EMPTIEST GROUND OF ITS SIZE IN THE PARK AND IT IS MEASURED, NOT DESCRIBED.**
Read off `out/Park Complete.litematic` before any of this was drawn:

    2,160 columns, streets on all four sides
    0.09 blocks per column          1,953 of 2,160 surface cells bare moss
    0.9% standing three courses     13 lanterns in the whole thing
    tops out at Y208                against Y223 for the Skill Arcade beside it and Y276 for the wheel

Mining Square - the lot Jack had replaced in the Frontier for being a car park - measured 1.4
blocks per column. This was fifteen times emptier, and a hole in the skyline as well as on the
ground.

**AND THE MIDWAY HAD TWO RIDES.** The Sky Lift and the Carousel, against the Frontier's coaster,
cart ride, mountain and two dinosaurs. `PARK_MIDWAY.md` calls this land "the park's arrival-and-
fairground district" and a fairground with two gentle rides and no third is a fairground missing
its third.

## What a ride can BE here, which is the constraint the whole design turns on

A "ride" in this park can only be a rail circuit, a bubble column or a walk-through; anything else
is a sculpture with a queue, and this repo has already retired eight of those. So:

    UP    a 3x3 soul-sand bubble column inside the drum, 25 courses
    DOWN  1.76 turns of BLUE ICE helix wrapped round the outside

**THE DESCENT IS DRY ON PURPOSE.** A helical open water chute is the shape that drained 199,959
cells to Y-1908 the one time this repo built one, and `fluids.escapes` exists because of it. Blue
ice is the fastest block in the game, it carries a rider down a graded ramp with no fluid at all,
and its worst case is a walkable spiral ramp - which is still a helter-skelter. All the water in
this design is ONE sealed vertical shaft, verified with the same tool.

**AND THE ASCENT IS BOARDED FROM A POOL, WHICH IS THE ONLY LEAK-FREE WAY IN.** A doorway into the
side of a water column at the water's own level is a hole in the side of a water column. The
guest wades over a kerb into a shallow pool whose water IS the bottom of the shaft, so every water
cell is walled at its own course and capped by air above it, and `escapes` returns nothing.

## The geometry, and the two numbers that fixed it

    centre        (V142, U365)
    drum          shell at r5, y0-y29, window band y26-28
    shaft         a 5x5 box V140-144 x U363-367; soul sand y0, water y1-y25 in the middle 3x3
    upper floor   y25 inside the drum - you step off the water onto it and out of the doorway
    chute         floor blue_ice at r6-7, soffit at r6-8 one course under, wall at r8 three high
    cap           y30-y39, r5 tapering to r1; crown at world Y242

**THE CENTRE IS V142 BECAUSE OF THE GROUND LAYER'S LAMPS.** Three mast lines stand at U345, U363
and U382, and their arms reach four courses into this lot on the promenade verges at V119-122 and
V128-131. At V141 the outer wall at r8 reaches (V133, U363) and clears them; at V140 it does not.
They are named in `blocked` as well, so wanting one of their cells RAISES here rather than
shipping as an overlap no render can show - a lantern inside a wall draws exactly like a wall.

**AND THE RAMP IS TWO COURSES THICK BECAUSE A HELIX IS NOT 6-CONNECTED.** Consecutive cells along
the descent sit one course apart and one cell apart, which is a DIAGONAL neighbour - the rule that
once broke a pair of ear tips off a cat. The course under the ice is what joins them, and it is
`white_wool` rather than more ice so the ribbon reads as a white soffit carrying a blue channel.

## The promenade is not this design's ground

`Park Ways` runs the back promenade through V123-127 of this lot and the service lane through
V154-156. Both are in `blocked`, so this cannot pave over a street it did not build.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .midway_builds import PAL, SIGN_WIDTH, _Lot, _dir  # noqa: F401  - one palette, one lot class

#: Everything this design adds to the Midway's own masonry. `blue_ice` and `packed_ice` are the
#: slide; `soul_sand` is the lift. All four are cheap tier, in the 1.19 registry, neither currency
#: nor a falling block - asserted in `tests/test_helter.py` rather than remembered.
ICE = {
    "chute":  "blue_ice",          # the fastest block in the game, and the one the ride IS
    "run":    "packed_ice",        # the run-out, slower on purpose: you are meant to STOP
    #: WHAT MAKES THE HELIX 6-CONNECTED TO ITSELF, and it is DARK for a second reason. Built white
    #: on a red-and-white drum the whole ribbon vanished into the tower - one glance at the first
    #: render and the slide read as lumps of foam stuck to a barber's pole, because a spiral drawn
    #: in a mass's own two colours is not a spiral. `polished_blackstone_bricks` at 45 against
    #: `white_wool` at 236 is the deepest cheap step this economy has, and it draws the ramp's
    #: underside as one continuous shadow line all the way round.
    "soffit": "polished_blackstone_bricks",
    "lift":   "soul_sand",
    "water":  "water",
    "buffer": "hay_block",         # the run-out's stop; cuts fall damage by 80% and reads fairground
}

HELTER = {
    "lot": None,               # [v0, u0, v1, u1] in park V/U - the canvas IS this
    "at": None,                # [x, y, z] of (lot v0, the first course above the lawn, lot u0)
    "blocked": (),             # cells the ground layer already owns; wanting one RAISES
    "height": 44,
    "seed": 0,
    "centre": None,            # [V, U] of the drum's axis
    "drum_r": 5,
    "wall_r": 8,               # the chute's outer parapet
    "top": 25,                 # the upper floor course, and the top of the water
    "drum_top": 29,
    "cap_top": 39,
    "turns": None,             # computed from the drop if not given
    #: WHERE THE HELIX HANDS OVER TO THE RUN-OUT, and both read it. Written as a literal in each,
    #: the two disagreed by two courses and the join was only walkable because the run-out happens
    #: to be built last and overwrites what the helix left - a ride that works by accident.
    "chute_bottom": 3,
    "run_per_course": 3.0,     # cells of travel per course of descent - a 19 degree slide
    "rear": None,              # [v0, v1] of the tower's half - the promenade splits the lot
    "front": None,             # [v0, v1] of the forecourt half, or None for no forecourt
    "arch_at": None,           # V of the entrance arch across the walk
    "walk_half": 6,            # the forecourt walk is thirteen wide, as the Welcome Court's is
}


# ---------------------------------------------------------------------------- geometry


def _r(v, u, cv, cu) -> float:
    return math.hypot(v - cv, u - cu)


def _ring(cv, cu, r0, r1, v0, v1, u0, u1):
    """Cells whose distance from the axis rounds into [r0, r1], inside the lot."""
    out = []
    for v in range(max(v0, cv - r1 - 1), min(v1, cv + r1 + 1) + 1):
        for u in range(max(u0, cu - r1 - 1), min(u1, cu + r1 + 1) + 1):
            if r0 <= round(_r(v, u, cv, cu)) <= r1:
                out.append((v, u))
    return out


def _disc(cv, cu, r, v0, v1, u0, u1):
    return [(v, u)
            for v in range(max(v0, cv - r), min(v1, cv + r) + 1)
            for u in range(max(u0, cu - r), min(u1, cu + r) + 1)
            if round(_r(v, u, cv, cu)) <= r]


def _angle(v, u, cv, cu) -> float:
    """The cell's bearing about the axis, in [0, 2pi)."""
    return math.atan2(u - cu, v - cv) % (2 * math.pi)


def _plain(name: str) -> str:
    """A block name with neither its namespace nor its state. `Canvas.get_name` returns
    `minecraft:stone`, so a bare membership test against a palette entry matches NOTHING - which
    is how the yard shipped with zero lights in it and a count of 8 that all came from elsewhere.
    """
    return (name or "").split(":")[-1].split("[")[0]


def _owned(L) -> set:
    """The COLUMNS the ground layer owns, from the same `blocked` boxes that raise on a hit.

    A paving loop crossing a promenade verge legitimately meets a lamp mast, and paving over its
    base is a real fault rather than a near miss - so the ground pass SKIPS these deliberately
    and the tripwire stays armed for everything that is not paving. One source: the skip and the
    raise read the same boxes, so a mast moved in the config cannot be honoured by one and not
    the other.
    """
    return {(v, u) for v, _y, u in L._blocked}


# ---------------------------------------------------------------------------- the kit


def _floor_mat(v, u):
    """The Midway's own two-tone paving with a grid every eight, set in WORLD V/U so the pattern
    runs continuously out of the Welcome Court and the Midway Row rather than restarting here."""
    if v % 8 == 0 or u % 8 == 0:
        return PAL["field"]
    return PAL["floor"] if (v + u) % 4 == 0 else PAL["floor2"]


def _stripe(v, u, cv, cu) -> str:
    """The drum is PALE with narrow vertical pinstripes, and the ribbon is the loud thing.

    **A SPIRAL DRAWN IN THE MASS'S OWN TWO COLOURS IS NOT A SPIRAL.** The first build gave the
    drum eight broad red bands and eight white ones and wrapped a white-walled chute round it; at
    every bearing the ride read as lumps stuck to a barber's pole, because the one element that
    has to be legible from across the park was the same value as the thing behind it. So the
    tower is `white_wool` with a `red_wool` stripe on four of sixteen segments - quiet, and it
    still reads as fairground - and the helix carries the red.

    Measured across families, which is the only place this economy's contrast has ever been:
    `polished_blackstone_bricks` 45, `red_wool` 65, `blue_ice` 158, `white_wool` 236.
    """
    seg = int(round(_angle(v, u, cv, cu) / (2 * math.pi) * 16)) % 16
    return PAL["band"] if seg % 4 == 0 else PAL["frame"]


def _bench(L, v, u0, u1, y, facing="north") -> int:
    """A seat is a stair, and its tall side is its `facing` - so a bench faces the walk it is set
    beside. `render3d` draws a stair the wrong way round exactly as it draws one the right way."""
    n = 0
    for u in range(u0, u1 + 1):
        n += bool(L.put(v, y, u, PAL["seat"], facing=facing, half="bottom",
                        shape="straight", waterlogged="false"))
    return n


def _tree(L, cv, cu, top=6, owned=()) -> int:
    """One species, so a terrace reads as one planting rather than as a collection.

    **A CANOPY IS CELLS AND A LAWN TEST IS A COLUMN.** The trunk clears the ground layer's lamp
    masts and the leaves do not: planted three cells off a mast line the crown still reaches it,
    which is the guard covering the group rather than the thing it is written next to - a bug
    this park has already shipped once, in the Diggings' terrace.
    """
    if any((v, u) in owned
           for v in range(cv - 2, cv + 3) for u in range(cu - 2, cu + 3)):
        return 0
    if not (L.v0 + 2 <= cv <= L.v1 - 2 and L.u0 + 2 <= cu <= L.u1 - 2):
        return 0
    n = 0
    for y in range(0, top - 1):
        n += bool(L.put(cv, y, cu, PAL["trunk"], axis="y"))
    for y in range(top - 2, top + 1):
        rad = 2 if y < top else 1
        for v in range(cv - rad, cv + rad + 1):
            for u in range(cu - rad, cu + rad + 1):
                if abs(v - cv) + abs(u - cu) > rad + 1:
                    continue
                if v == cv and u == cu and y < top:
                    continue
                if not L.has(v, y, u):
                    n += bool(L.put(v, y, u, PAL["leaf"], persistent="true", distance="1"))
    return n


# ---------------------------------------------------------------------------- the tower


def _helix(L, p, cv, cu, m) -> dict:
    """The descent: turns of blue ice from the drum's top door to the run-out.

    **THE RAMP IS TWO COURSES THICK AND THAT IS STRUCTURAL, NOT DECORATION.** Consecutive cells
    along a helix sit one cell apart horizontally AND one course apart vertically, which is a
    DIAGONAL neighbour and is not 6-connectivity. The `white_wool` course under the ice is what
    joins them; without it the slide ships as scores of free-floating fragments and every render
    here draws it exactly as it draws a solid ramp.
    """
    drum_r, wall_r = int(p["drum_r"]), int(p["wall_r"])
    top, bot = int(p["top"]), int(p["chute_bottom"])
    r_mid = (drum_r + 1 + wall_r - 1) / 2.0
    span = (top - bot) * float(p["run_per_course"]) / r_mid          # radians of descent
    turns = float(p["turns"]) if p.get("turns") else span / (2 * math.pi)
    span = turns * 2 * math.pi
    per_rad = (top - bot) / span
    th0 = math.pi                                                    # the head, on the -V face
    v0, u0, v1, u1 = L.v0, L.u0, L.v1, L.u1
    floors = 0
    for v, u in _ring(cv, cu, drum_r + 1, wall_r, v0, v1, u0, u1):
        rr = round(_r(v, u, cv, cu))
        s = (_angle(v, u, cv, cu) - th0) % (2 * math.pi)
        while s <= span + 1e-9:
            y = int(round(top - s * per_rad))
            if y < bot:
                break
            L.put(v, y - 1, u, ICE["soffit"])
            if rr <= wall_r - 1:
                L.put(v, y, u, ICE["chute"])
                floors += 1
            else:
                # TWO COURSES, NOT THREE. The wall's top sits at the rider's own feet, which is
                # enough to stop them walking off it, and a third course buried the blue channel
                # from every view but the plan - which is the view this ride is least read from.
                for k in range(0, 2):
                    L.put(v, y + k, u, PAL["band"])
            s += 2 * math.pi
    m["chute"] = floors
    foot = (th0 + span) % (2 * math.pi)
    return {"turns": round(turns, 2), "head_angle": round(th0, 3), "foot_angle": round(foot, 3),
            "courses": top - bot}


def _drum(L, p, cv, cu, m) -> None:
    """The tower: a striped drum with a window band at the top and a doorway onto the chute."""
    drum_r, top, dtop = int(p["drum_r"]), int(p["top"]), int(p["drum_top"])
    v0, v1, u0, u1 = L.v0, L.v1, L.u0, L.u1
    shell = _ring(cv, cu, drum_r, drum_r, v0, v1, u0, u1)
    # THE DOORWAY IS LEFT EMPTY BY THE SHELL LOOP, NEVER PUNCHED AFTERWARDS. Building the ring and
    # cutting a hole repaints cells that already exist, which is how the void tower's crenellations
    # shipped as a plain drum with nothing about the code looking wrong.
    head = math.pi                                        # the chute starts on the -V face
    for v, u in shell:
        door = abs(u - cu) <= 1 and v < cv               # the way out, onto the head of the chute
        for y in range(0, dtop + 1):
            if door and y in (top + 1, top + 2):
                continue
            if y in (top + 2, top + 3) and (u + v) % 2 == 0:
                continue                                  # the window band: see out from the top
            if y == 0 or y in (top, dtop):
                L.put(v, y, u, PAL["plinth"])              # plinth, string course, cornice
            else:
                L.put(v, y, u, _stripe(v, u, cv, cu))
    for v, u in _disc(cv, cu, drum_r - 1, v0, v1, u0, u1):
        L.put(v, 0, u, PAL["floor2"])                      # the plant room's own floor
        L.put(v, top, u, PAL["floor2"])                    # the upper floor you step out onto
    m["drum"] = len(shell)


def _shaft(L, p, cv, cu) -> dict:
    """The lift: a 3x3 soul-sand bubble column, and the trough a rider wades in through.

    **EVERY WATER CELL IS WALLED AT ITS OWN COURSE.** A doorway into the side of a water column at
    the water's own level is a hole in the side of a water column, so there is no doorway: the
    trough IS the bottom two courses of the same body, kerbed all round, and a rider steps down
    off the boarding platform into it. `tests/test_helter.py` runs `fluids.escapes` over the
    finished model with these cells as the envelope and requires nothing outside it.
    """
    top = int(p["top"])
    env = []
    for v in range(cv - 1, cv + 2):                       # the column
        for u in range(cu - 1, cu + 2):
            L.put(v, 0, u, ICE["lift"])
            for y in range(1, top + 1):
                L.put(v, y, u, ICE["water"], level="0")
                env.append((v, y, u))
    for y in range(1, top + 1):                           # its casing
        for v in range(cv - 2, cv + 3):
            for u in range(cu - 2, cu + 3):
                if abs(v - cv) <= 1 and abs(u - cu) <= 1:
                    continue
                if y <= 2 and abs(v - cv) <= 1 and u == cu - 2:
                    continue                              # the trough's mouth
                L.put(v, y, u, PAL["field"])
    for u in range(cu - 8, cu - 1):                       # the trough
        for v in range(cv - 1, cv + 2):
            L.put(v, 0, u, PAL["plinth"])
            for y in (1, 2):
                L.put(v, y, u, ICE["water"], level="0")
                env.append((v, y, u))
        for v in (cv - 2, cv + 2):
            for y in (1, 2):
                L.put(v, y, u, PAL["field"])
    for v in range(cv - 2, cv + 3):                       # its far end
        for y in (0, 1, 2):
            L.put(v, y, cu - 9, PAL["plinth"] if y == 0 else PAL["field"])
    return {"envelope": env}


def _cap(L, p, cv, cu, m) -> None:
    """The cone, in the ride's own two colours, banded so it reads at distance."""
    dtop, ctop, drum_r = int(p["drum_top"]), int(p["cap_top"]), int(p["drum_r"])
    v0, v1, u0, u1 = L.v0, L.v1, L.u0, L.u1
    n = 0
    for y in range(dtop + 1, ctop + 1):
        t = (y - dtop) / float(ctop - dtop)
        r = max(1, int(round(drum_r * (1.0 - t) + t)))
        mat = PAL["band"] if ((y - dtop - 1) // 2) % 2 == 0 else PAL["frame"]
        for v, u in _disc(cv, cu, r, v0, v1, u0, u1):
            n += bool(L.put(v, y, u, mat))
    for y in range(ctop + 1, ctop + 3):
        n += bool(L.put(cv, y, cu, PAL["post"]))
    m["cap"] = n


def _runout(L, p, cv, cu, m) -> dict:
    """The exit: a packed-ice run-out straight out of the chute's mouth into the +U yard.

    **THE FOOT ANGLE IS CHOSEN, NOT DISCOVERED.** `turns` is 1.75, so the descent starts on the
    drum's -V face and ends exactly a quarter turn short of it - pointing +U, at the opposite side
    of the tower from the boarding pool. `PARK_MIDWAY.md`: *"The exit cannot feed into waiting
    guests."* A ride whose run-out is a function of wherever the arithmetic happened to land is a
    ride whose exit walks into its own queue.

    It is `packed_ice` and not `blue_ice` on purpose: the run-out is where you are meant to STOP.
    """
    bot, wall_r = int(p["chute_bottom"]), int(p["wall_r"])
    end = cu + 16
    n = 0
    for i, u in enumerate(range(cu + wall_r - 2, end + 1)):
        y = max(0, bot - i // 3)
        for v in range(cv - 1, cv + 2):
            n += bool(L.put(v, y, u, ICE["run"]))
        if u < end - 2:                                    # the last three cells are open: you walk out
            for v in (cv - 2, cv + 2):
                for k in range(0, 3):
                    L.put(v, y + k, u, PAL["frame"] if k < 2 else PAL["band"])
        if y > 0:
            for v in range(cv - 2, cv + 3):
                for yy in range(0, y):
                    L.put(v, yy, u, PAL["field"])
    for v in range(cv - 1, cv + 2):                        # the buffer you come to rest against
        L.put(v, 1, end - 1, ICE["buffer"], axis="x")
        L.put(v, 1, end, ICE["buffer"], axis="x")
    m["runout"] = n
    return {"exit": [cv, end + 1]}


def _boarding(L, p, cv, cu, m) -> dict:
    """The queue, and the deck you step off into the water.

    A rider walks the switchback at apron level, climbs two courses onto the boarding deck, and
    steps off its end into the trough - so the water is entered over a kerb that is also the
    deck's own last course, and nothing about the way in is a hole in the side of a column.
    """
    v0, v1 = cv - 4, cv + 4
    u0, u1 = cu - 14, cu - 9
    n = 0
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            for y in (0, 1):
                n += bool(L.put(v, y, u, PAL["field"]))
            n += bool(L.put(v, 2, u, PAL["floor2"]))
    for u in range(u0, u1 + 1):                             # the deck's own rail
        for v in (v0, v1):
            n += bool(L.put(v, 3, u, PAL["rail"]))
    for v in range(v0 + 1, v1):                             # the steps up onto it
        L.put(v, 0, u0 - 1, PAL["trim"], facing="south", half="bottom",
              shape="straight", waterlogged="false")
        L.put(v, 1, u0 - 1, PAL["trim"], facing="south", half="bottom",
              shape="straight", waterlogged="false")
    # THE SWITCHBACK. Three lanes of fence, and the mouth is at the -U end so a queue forms in the
    # yard rather than across the walk that feeds it.
    qu0 = max(L.u0 + 1, cu - 24)
    for v in (cv - 5, cv + 1):
        for u in range(qu0, cu - 14):
            n += bool(L.put(v, 0, u, PAL["post"]))
    for u in (qu0, cu - 15):
        for v in range(cv - 5, cv + 2):
            if (u == qu0 and v > cv - 2) or (u == cu - 15 and v < cv - 2):
                n += bool(L.put(v, 0, u, PAL["post"]))
    m["queue"] = n
    return {"queue_mouth": [cv + 4, qu0]}


def _yard(L, p, cv, cu, seed, m) -> None:
    """The tower's own plaza, the two yards, and the lawn the design deliberately does not pave.

    **A FULLY PAVED LOT IS A CAR PARK AND THIS PARK HAS ALREADY REPLACED ONE FOR BEING ONE.** So
    what is paved is what is walked - the apron ring, the approach off the promenade, and the two
    yards - and everything else stays the ground layer's own moss, planted.
    """
    u0, u1 = L.u0, L.u1
    v0, v1 = (int(q) for q in p["rear"])
    wall_r = int(p["wall_r"])
    owned = _owned(L)
    paved = 0
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            r = _r(v, u, cv, cu)
            walk = abs(u - cu) <= 6 and v < cv - wall_r        # off the back promenade
            ring = wall_r < r <= wall_r + 3
            yard = (u <= cu - 9 or u >= cu + 9) and abs(v - cv) <= 9
            if not (walk or ring or yard) or (v, u) in owned:
                continue
            if L.has(v, 0, u):
                continue
            mat = PAL["inlay"] if abs(round(r) - (wall_r + 3)) == 0 else _floor_mat(v, u)
            paved += bool(L.put(v, 0, u, mat))
    # THE LIGHT IS FLUSH IN THE PAVING. Reach is one LESS than the light for a froglight set in
    # the floor - it is an opaque emitter a course down - so the spacing is set against 14.
    for v in range(v0, v1 + 1, 7):
        for u in range(u0, u1 + 1, 7):
            if _plain(L.name_at(v, 0, u)) in (PAL["floor"], PAL["floor2"], PAL["field"]):
                L.put(v, 0, u, PAL["glow"])
                m["lamps"] += 1
    m["paved"] += paved
    # ...and the planting on what is left.
    for cvv, cuu in ((cv - 12, cu - 15), (cv + 12, cu - 15), (cv - 12, cu + 15),
                     (cv + 12, cu + 15), (cv + 13, cu), (cv + 13, cu - 7), (cv + 13, cu + 7)):
        if not L.has(cvv, 0, cuu):
            m["trees"] += bool(_tree(L, cvv, cuu, owned=owned))


def _forecourt(L, p, seed, m) -> None:
    """The approach: a thirteen-wide walk off the Prize Point, an arch that names the ride, and a
    planted terrace either side of it. NOT ONE BUILDING - Jack has rejected a splatter of small
    sheds in this park three separate times, and the forecourt's job is to frame the tower."""
    fv0, fv1 = (int(q) for q in p["front"])
    u0, u1 = L.u0, L.u1
    axis = (u0 + u1) // 2
    half = int(p["walk_half"])
    owned = _owned(L)
    for v in range(fv0, fv1 + 1):
        for u in range(u0, u1 + 1):
            if abs(u - axis) > half + 2 or (v, u) in owned:
                continue
            mat = PAL["inlay"] if abs(u - axis) == half else _floor_mat(v, u)
            m["paved"] += bool(L.put(v, 0, u, mat))
    for v in range(fv0, fv1 + 1, 6):                       # the walk's own lights, flush
        for u in (axis - half + 1, axis + half - 1):
            if (v, u) not in owned and L.put(v, 0, u, PAL["glow"]):
                m["lamps"] += 1
    # -- the terraces: hedged beds with a tree apiece and a bench facing the walk
    for side in (-1, 1):
        for v in range(fv0 + 2, fv1 - 1, 8):
            cu2 = axis + side * (half + 6)
            if not (u0 + 3 <= cu2 <= u1 - 3):
                continue
            for vv in range(v, min(v + 5, fv1)):
                for uu in range(cu2 - 3, cu2 + 4):
                    if (vv, uu) in owned:
                        continue
                    if vv in (v, min(v + 4, fv1 - 1)) or uu in (cu2 - 3, cu2 + 3):
                        m["paved"] += bool(L.put(vv, 0, uu, PAL["inlay"]))
                    else:
                        m["paved"] += bool(L.put(vv, 0, uu, PAL["lawn"]))
            m["trees"] += bool(_tree(L, v + 2, cu2, owned=owned))
            bu = axis + side * (half + 1)
            m["benches"] += _bench(L, v + 2, bu, bu, 1, "west" if side < 0 else "east")
            m["benches"] += _bench(L, v + 3, bu, bu, 1, "west" if side < 0 else "east")
    # -- the arch, and it is the only structure in the forecourt
    av = int(p["arch_at"])
    for side in (-1, 1):
        u = axis + side * half
        for v in (av, av + 3):
            for y in range(1, 7):
                m["arch"] += bool(L.put(v, y, u, PAL["plinth"] if y in (1, 6) else
                                        (PAL["band"] if y % 2 else PAL["frame"])))
        for v in (av + 1, av + 2):
            for y in (5, 6):
                m["arch"] += bool(L.put(v, y, u, PAL["frame"]))
    for u in range(axis - half, axis + half + 1):          # the lintel and the name board
        for v in range(av, av + 4):
            m["arch"] += bool(L.put(v, 7, u, PAL["frame"] if abs(u - axis) % 2 else PAL["band"]))
        m["arch"] += bool(L.put(av, 8, u, PAL["plinth"]))
        m["arch"] += bool(L.put(av + 3, 8, u, PAL["plinth"]))


def _signs(L, p, cv, cu, m) -> None:
    """What the ride is, what it costs you, and where the way out is.

    FIFTEEN CHARACTERS IS THE LINE and `_Lot.sign` truncates at it, so every line here is counted.
    This park has shipped `MINE CART ESCAP`, `and prize windo` and `ore from the ad`; a board that
    clips mid-word is only ever discovered in a screenshot of a placed build.
    """
    axis = (L.u0 + L.u1) // 2
    av = int(p["arch_at"])
    n = 0
    n += bool(L.sign(av - 1, 7, axis, -1, 0, ["HELTER SKELTER", "climb it", "slide it", "no queue jump"]))
    n += bool(L.sign(av + 4, 7, axis, 1, 0, ["HELTER SKELTER", "", "ride exit east", ""]))
    # the queue mouth, at the -U yard
    n += bool(L.sign(cv + 5, 2, cu - 12, 1, 0,
                     ["JOIN THE QUEUE", "wade in and", "hold on - water", "lifts you"]))
    # the top: this is the observation the exit band is programmed for, so it says what you see
    # ...and NOT on the cell over the doorway, which is the one column of this wall that has an
    # opening in it. That is the mistake four of an earlier park's seven building kinds shipped,
    # and a sign hung on air draws exactly like a sign hung on a wall.
    n += bool(L.sign(cv - int(p["drum_r"]) + 1, int(p["top"]) + 1, cu + 2, 1, 0,
                     ["THE TOP", "wheel to west", "prismworks east", "mind the step"]))
    # the way out
    n += bool(L.sign(cv - 3, 2, cu + 13, -1, 0, ["WAY OUT", "", "prizes: west", ""]))
    m["signs"] = n


def _bell(L, cv, cu, m) -> None:
    """A bell at the run-out, because a slide with nothing to do at the bottom of it ends twice."""
    if not L.has(cv + 3, 0, cu + 15):
        return
    if L.put(cv + 3, 1, cu + 15, PAL["plinth"]) and L.put(cv + 3, 2, cu + 15, "bell",
                                                          facing="north", attachment="floor"):
        m["bell"] = 1


def build(cfg: dict, donors=None) -> Canvas:
    p = {**HELTER, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the helter skelter needs params.lot = [v0, u0, v1, u1]")
    v0, u0, v1, u1 = (int(q) for q in p["lot"])
    if v1 < v0 or u1 < u0:
        raise ValueError(f"lot {p['lot']} is empty")
    cv, cu = (int(q) for q in (p.get("centre") or [(v0 + v1) // 2, (u0 + u1) // 2]))
    c = Canvas(v1 - v0 + 1, int(p["height"]), u1 - u0 + 1, donors)
    L = _Lot(c, (v0, u0, v1, u1), p.get("blocked") or ())
    m = {"paved": 0, "lamps": 0, "trees": 0, "benches": 0, "arch": 0, "signs": 0, "bell": 0}

    # ORDER IS LOAD-BEARING, and each step cuts into the one before it:
    #   the drum, then the helix wrapped round it, then the shaft CUT THROUGH both, then the
    #   run-out cut through the helix's outer wall at the foot. A shaft built before the drum is a
    #   shaft the drum then walls up, and a helix built after the run-out closes the mouth again.
    _drum(L, p, cv, cu, m)
    helix = _helix(L, p, cv, cu, m)
    water = _shaft(L, p, cv, cu)
    run = _runout(L, p, cv, cu, m)
    _cap(L, p, cv, cu, m)
    board = _boarding(L, p, cv, cu, m)
    _yard(L, p, cv, cu, int(p["seed"]), m)
    if p.get("front"):
        _forecourt(L, p, int(p["seed"]), m)
    _signs(L, p, cv, cu, m)
    _bell(L, cv, cu, m)

    if L.refused or L.blocked_hits:
        raise ValueError(f"helter: {L.refused} cell(s) outside lot {p['lot']}, "
                         f"{L.blocked_hits} on cells the ground layer already owns")
    if p.get("at"):
        c.world_origin = tuple(int(q) for q in p["at"])
    c.meta = {
        "kind": "ride", "build": "helter_skelter", "name": "PF Helter Skelter",
        "lot": [v0, u0, v1, u1], "centre": [cv, cu],
        # THE HEIGHTS TRAVEL WITH THE BUILD. A test that types 25 for the top of the lift is
        # pinning a DECISION, and it goes on passing - under-testing - the day the tower grows.
        "top": int(p["top"]), "drum_top": int(p["drum_top"]), "cap_top": int(p["cap_top"]),
        "chute_bottom": int(p["chute_bottom"]),
        # THE FACING IS A COMPASS WORD - "the direction the FRONT looks out" - which is what
        # `park.py` records and what `tools/look.py` and `tools/panel.py` both read. The forecourt
        # and the arch address -V, back toward the Prize Point and the park's own entrance.
        "facing": "west",
        "water_envelope": [list(q) for q in water["envelope"]],
        "anchors": {
            "queue_entry": board["queue_mouth"],
            "board": [cv, cu - 9],
            "ride_exit": run["exit"],
            "gallery": [cv, cu],
        },
        **helix, **m,
        "contract": (
            "one connected ride inside V%d-%d U%d-%d: a %d-course soul-sand lift inside the drum, "
            "%s turns of blue ice down the outside, boarding at -U and discharge at +U so the exit "
            "cannot feed into the queue, and every water cell inside the declared envelope"
            % (v0, v1, u0, u1, int(p["top"]), helix["turns"])),
        # WHAT A LITEMATIC CANNOT CARRY, stated rather than implied. The lift is a bubble column
        # and needs nothing stocked; the ride is the ride. What it DOES need is that the water is
        # placed as SOURCES - `level=0` - which is what the shaft writes and what
        # `tests/test_helter.py` asserts, because a trough of flowing water lifts nobody.
        "note": "the lift is a soul-sand bubble column; nothing to stock",
    }
    return c
