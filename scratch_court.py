NEW = '''# ---------------------------------------------------------------------------- the court kit


def _disc(cv, cu, r):
    return {(v, u)
            for v in range(cv - r, cv + r + 1)
            for u in range(cu - r, cu + r + 1)
            if (v - cv) ** 2 + (u - cu) ** 2 <= r * r}


def _ring(cv, cu, r):
    """THE SHELL RULE: the cells OUTSIDE a disc that have a FACE neighbour inside it.

    A rasterised circle taken from a band in the radius equation is fat at the diagonals and thin
    on the axes - the void tower's own finding - and worse here, because a basin wall with one
    diagonal gap in it is a basin that drains. Water spreads to its four face neighbours only, so
    a wall built as "outside, with a face neighbour inside" holds BY CONSTRUCTION whatever the
    rasteriser does at the corners.
    """
    inside = _disc(cv, cu, r)
    out = set()
    for v, u in inside:
        for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (v + dv, u + du) not in inside:
                out.add((v + dv, u + du))
    return inside, out


def _standard(L, v, u, m) -> bool:
    """THE COURT'S LAMP, AND THE REASON THIS BUILD EXISTS AT ALL.

    Jack, on the shipped court: *"get rid of the crappy lamp posts with yellow wool tops and crap
    - we need this to feel premium and clean."* Measured off `out/Park Complete.litematic` the old
    court's standards were an oak-log foot, four oak fence courses, another log, a blackstone cap,
    **a `yellow_wool` block** and a lantern on top of that - twelve courses of timber with a wool
    cube near the head, thirty-nine of them. There is no reading of that which is not what he said.

    This is a lamp STANDARD: a dark plinth, a stone base, a three-course wall shaft - a wall
    renders as a slender post rather than as a block - a dressed head, and ONE lantern on it. Six
    courses, one cell square, one light.

    THE HEAD IS A FULL BLOCK BECAUSE A LANTERN CANNOT STAND ON A WALL: `blocks.supports_top` says
    so for `stone_brick_wall`, which is the same rule that cost the Prismworks lamp its first
    build and put 104 placement problems in it.
    """
    if not L.put(v, 0, u, PAL["inlay"]):
        return False
    L.put(v, 1, u, PAL["course"])
    for y in (2, 3, 4):
        L.put(v, y, u, PAL["rail"], up="true", north="none", south="none", east="none",
              west="none", waterlogged="false")
    L.put(v, 5, u, PAL["course"])
    L.put(v, 6, u, PAL["light"], hanging="false", waterlogged="false")
    m["lamps"] += 1
    return True


def _bench(L, v, u, nv, nu, length, m) -> int:
    """A SEAT FACING SOMETHING, with a stone end at each end of it.

    `(nv, nu)` is the direction the sitter LOOKS. A stair's tall side is its `facing`, so the back
    of a seat is on the far side from the view and the stair faces AWAY from it - written the
    obvious way round every bench faces its own back, and `render3d` draws both the same.
    """
    tv, tu = (0, 1) if nv else (1, 0)
    made = 0
    half = length // 2
    for k in range(-half, half + 1):
        made += bool(L.put(v + tv * k, 1, u + tu * k, PAL["seat"], facing=_opp(nv, nu),
                           half="bottom", shape="straight", waterlogged="false"))
    for k in (-half - 1, half + 1):                # the stone ends, so a bench has arms
        made += bool(L.put(v + tv * k, 1, u + tu * k, PAL["cap"], type="bottom",
                           waterlogged="false"))
    m["benches"] += 1
    return made


def _tree(L, cv, cu, m) -> int:
    """One oak, on the centre of its own bed. Small, round, and THE SAME IN EVERY BED.

    The shipped court had eleven trees of four species at eleven positions nothing derived, and
    from above they read as blobs dropped on a grid. Four identical trees on the four quadrant
    centres read as planting.
    """
    made = 0
    for y in range(1, 5):
        made += bool(L.put(cv, y, cu, PAL["trunk"], axis="y"))
    for y, r in ((4, 2), (5, 2), (6, 1)):
        for v in range(cv - r, cv + r + 1):
            for u in range(cu - r, cu + r + 1):
                if (v - cv) ** 2 + (u - cu) ** 2 > r * r:
                    continue
                if v == cv and u == cu and y < 6:
                    continue                       # the trunk runs up through its own crown
                made += bool(L.put(v, y, u, PAL["leaf"], distance="1", persistent="true",
                                   waterlogged="false"))
    made += bool(L.put(cv, 6, cu, PAL["leaf"], distance="1", persistent="true",
                       waterlogged="false"))
    m["trees"] += 1
    return made


def _seat_arc(L, v, cu, side, mid, m) -> None:
    """One row of an exedra: the curved bench that closes a cross arm."""
    u = cu + side * (3 - abs(v - mid))
    L.put(v, 1, u, PAL["seat"], facing=_dir(0, -side), half="bottom", shape="straight",
          waterlogged="false")
    L.put(v, 1, u + side, PAL["cap"], type="bottom", waterlogged="false")
    if abs(v - mid) == 2:
        m["benches"] += 1


def _court_pave(v, u, mid, axis, seed) -> str:
    """The court's own floor, and EVERY LINE IN IT IS DERIVED FROM THE AXIS.

    A pattern laid on world coordinates is right for a building, whose rooms have to line up with
    each other; it is wrong for a composition whose whole subject is one centre line, because the
    grid then lands wherever the lot happens to start. Here the rings are concentric on the basin
    and the bands are measured from the axis, so the floor itself says where the middle is.
    """
    if abs(u - axis) in (5, 6):
        return PAL["inlay"]                        # the great walk's own kerb lines
    r = int(((v - mid) ** 2 + (u - axis) ** 2) ** 0.5)
    if r in (8, 11, 12):
        return PAL["field"]                        # the roundel's concentric courses
    if abs(u - axis) < 5 and (v - mid) % 6 == 0:
        return PAL["field"]                        # the walk's rungs
    return PAL["floor2"] if (v + u) % 2 == 0 or hash01(v, u, seed) < 0.12 else PAL["floor"]


def _welcome_court(L, p) -> dict:
    """THE WALK-UP: what a visitor crosses between the entry gate and the wheel.

        V24-74 x U280-320, axis U300, centre V49

    Jack: *"gates and a board etc are all overlapping and chaotic with the entrance to the main
    center ... carefully just work on making the entrance experience, and the leading park in
    front of it before the ferris wheel and surrounding area perfect, highly detailed,
    sophisticated, no weird blocks, or overlaps, no bad placements ... we need this to feel
    premium and clean."*

    WHAT WAS HERE, measured off the shipped park rather than described: 4,613 blocks paved edge to
    edge on one world-aligned grid, eleven trees of four species at eleven positions nothing
    derived, nine `magenta_wool` and fifteen `light_blue_wool` cells with no other member of their
    own colour near them, and lamp standards whose head course was a `yellow_wool` block. Nothing
    in it was symmetric about the axis it stands on - and the axis is the ONE thing this lot has:
    the entry gate's two doors, this court and the Sky Lift's hub all sit on U300.

    SO THE COMPOSITION IS THE AXIS, and every piece is derived from it:

        the great walk   U295-305, V24 to V74, unbroken - the vista from the gate to the wheel
        the round        a paved roundel r=12 on (V49, U300), where the walk opens out
        the basin        a raised stone fountain on the axis: two tiers, four courses, water
        two exedras      a curved bench recess closing the round's east and west arms
        four beds        9 x 9, kerbed and coped, one oak each, on the four quadrant centres
        twelve standards the lamp above - paired about the axis and never on it
        four piers       two at each threshold, flanking the walk and carrying the name

    **NOTHING OF THIS COURT'S STANDS IN THE WALK.** Every lamp, pier, bench and tree is at
    |U-300| >= 6, so the eleven-wide walk is clear above its own floor course for all fifty-one
    courses except the basin - which is on the axis deliberately, four courses high against a
    seventy-four-course wheel behind it. `tests/test_midway_builds.py` measures that rather than
    trusting this paragraph.

    **THE POOL CANNOT DRAIN.** Its wall is built by the shell rule - the cells outside the disc
    that have a face neighbour inside it - so there is no diagonal gap for water to find, and the
    course under every water cell is this court's own paving.

    **HALF THE LOT IS GREEN.** A field of one material over two thousand cells is a slab and not a
    floor, which is the casino hall's own finding, and this is the LEADING PARK rather than a
    plaza: the paving is the walk, the roundel and the two arms, and everything else is lawn.
    """
    seed = int(p["seed"])
    v0, u0, v1, u1 = (int(q) for q in p["lot"])
    axis = (u0 + u1) // 2                          # U300 - the gate's doors and the wheel's hub
    mid = (v0 + v1) // 2                           # V49
    half = 5                                       # the great walk is eleven wide
    m = {"signs": 0, "lamps": 0, "benches": 0, "trees": 0, "beds": 0, "floor": 0,
         "water": 0, "steps": 0, "axis": axis, "centre": mid}

    walk = {(v, u) for v in range(v0, v1 + 1) for u in range(axis - half, axis + half + 1)}
    roundel = _disc(mid, axis, 12)
    exedras = [(mid, u0 + 4, -1), (mid, u1 - 4, 1)]
    arms = set()
    for cv, cu, _side in exedras:
        arms |= _disc(cv, cu, 4)
        lo, hi = sorted((cu, axis))
        arms |= {(v, u) for v in range(cv - 3, cv + 4) for u in range(lo, hi + 1)}
    paved = walk | roundel | arms

    beds = [(mid - 16, axis - 13), (mid - 16, axis + 13),
            (mid + 16, axis - 13), (mid + 16, axis + 13)]
    bed_cells, bed_kerb = set(), set()
    for bv, bu in beds:
        inner = {(v, u) for v in range(bv - 3, bv + 4) for u in range(bu - 3, bu + 4)}
        outer = {(v, u) for v in range(bv - 4, bv + 5) for u in range(bu - 4, bu + 5)}
        bed_cells |= inner
        bed_kerb |= outer - inner

    # -- 1. the podium ---------------------------------------------------------------------------
    # ONE COURSE, because every lot in this park is one course over the lawn the streets are cut
    # into. The threshold on the axis is a stair rather than a kerb, at both ends, so the walk-up
    # is a step rather than a ledge.
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            edge = v in (v0, v1) or u in (u0, u1)
            if v in (v0, v1) and abs(u - axis) <= half:
                # A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D - the convention pinned
                # in `test_stairhead`, and one our own renderer draws identically either way.
                m["steps"] += bool(L.put(v, 0, u, PAL["trim"],
                                         facing="east" if v == v0 else "west",
                                         half="bottom", shape="straight", waterlogged="false"))
                continue
            if edge or (v, u) in bed_kerb:
                mat = PAL["inlay"]                 # the kerb: this court's own dark line
            elif (v, u) in bed_cells:
                mat = PAL["lawn"]
            elif (v, u) in paved:
                mat = _court_pave(v, u, mid, axis, seed)
            else:
                mat = PAL["lawn"]
            m["floor"] += bool(L.put(v, 0, u, mat))

    # -- 2. the basin ----------------------------------------------------------------------------
    pool, wall = _ring(mid, axis, 4)
    for v, u in wall:
        L.put(v, 1, u, PAL["inlay"])
        L.put(v, 2, u, PAL["cap"], type="bottom", waterlogged="false")
    for v, u in pool:
        if max(abs(v - mid), abs(u - axis)) <= 1:
            continue                               # the pedestal stands where the water is not
        m["water"] += bool(L.put(v, 1, u, "water", level="0"))
    for v in range(mid - 1, mid + 2):
        for u in range(axis - 1, axis + 2):
            L.put(v, 1, u, PAL["field"])           # the pedestal, rising out of the pool
    L.put(mid, 2, axis, PAL["course"])             # the stem
    for dv in (-1, 0, 1):                          # the bowl's corbelled underside
        for du in (-1, 0, 1):
            if dv == du == 0:
                L.put(mid, 3, axis, PAL["field"])
            else:
                L.put(mid + dv, 3, axis + du, PAL["trim"], facing=_opp(dv, du), half="top",
                      shape="straight", waterlogged="false")
    for dv in (-1, 0, 1):                          # ...and the upper bowl standing on it
        for du in (-1, 0, 1):
            if dv == du == 0:
                m["water"] += bool(L.put(mid, 4, axis, "water", level="0"))
            else:
                L.put(mid + dv, 4, axis + du, PAL["field"])
    m["basin"] = [mid, axis]

    # -- 3. the two exedras ----------------------------------------------------------------------
    # A PATH THAT ENDS NOWHERE IS NOT A PATH. The round's two cross arms are short and each closes
    # in a seat rather than at the lot's own kerb, so the cross axis is somewhere to sit and look
    # back down the walk rather than a corridor running out into the lawn.
    for cv, cu, side in exedras:
        for v in range(cv - 2, cv + 3):
            _seat_arc(L, v, cu, side, cv, m)
        _standard(L, cv - 4, cu, m)
        _standard(L, cv + 4, cu, m)

    # -- 4. the beds -----------------------------------------------------------------------------
    for bv, bu in beds:
        for v, u in bed_kerb:
            if max(abs(v - bv), abs(u - bu)) == 4:
                L.put(v, 1, u, PAL["cap"], type="bottom", waterlogged="false")
        _tree(L, bv, bu, m)
        for dv, du in ((-2, -2), (-2, 2), (2, -2), (2, 2)):
            L.put(bv + dv, 1, bu + du, PAL["shrub"])
        m["beds"] += 1

    # -- 5. the standards, the benches and the two thresholds ------------------------------------
    # PAIRED ABOUT THE AXIS AND NEVER ON IT. Every one of these is at |U-300| >= 6, which is what
    # keeps the vista from the gate to the wheel clear of this court's own furniture.
    for v in (v0 + 6, mid - 16, mid + 16, v1 - 6):
        for u in (axis - half - 1, axis + half + 1):
            _standard(L, v, u, m)
    for v, look in ((mid - 13, 1), (mid + 13, -1)):
        _bench(L, v, axis - half - 3, look, 0, 3, m)
        _bench(L, v, axis + half + 3, look, 0, 3, m)

    for v, inward in ((v0 + 2, 1), (v1 - 2, -1)):
        for u in (axis - half - 2, axis + half + 2):
            for dv in (0, inward):                 # a 2 x 1 pier, its long side down the walk
                for y in range(1, 5):
                    L.put(v + dv, y, u, PAL["frame"] if y == 4 else PAL["field"])
                L.put(v + dv, 5, u, PAL["cap"], type="bottom", waterlogged="false")
            L.put(v, 5, u, PAL["course"])
            L.put(v, 6, u, PAL["light"], hanging="false", waterlogged="false")
            m["lamps"] += 1
    m["signs"] += bool(L.sign(v0 + 2, 3, axis - half - 3, 0, -1,
                              ["WELCOME COURT", "", "the big wheel", "straight ahead"]))
    m["signs"] += bool(L.sign(v0 + 2, 3, axis + half + 3, 0, 1,
                              ["WELCOME COURT", "", "carousel and", "arcade beyond"]))
    return m


'''

import io
p = 'mcbuild/gen/midway_builds.py'
s = open(p, encoding='utf-8').read()
anchor = '_KINDS = {\n    "arrival_court": (_arrival_court, "PF Arrival Court"),'
assert anchor in s
s = s.replace(anchor, NEW + anchor)
s = s.replace('    "arrival_court": (_arrival_court, "PF Arrival Court"),',
              '    "arrival_court": (_arrival_court, "PF Arrival Court"),\n'
              '    "welcome_court": (_welcome_court, "PF Welcome Court"),', 1)
open(p, 'w', encoding='utf-8').write(s)
print("inserted")
