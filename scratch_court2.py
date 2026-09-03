"""Replace the court block in midway_builds.py: from `# ---- the court kit` to `_KINDS = {`."""
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
    cube near the head. There is no reading of that which is not what he said.

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
    from above they read as blobs dropped on a grid. Identical trees on derived centres read as
    planting; four species at eleven hand-chosen points read as a nursery.
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


def _swag(L, v, u0, u1, y, m) -> int:
    """BUNTING ACROSS THE WALK: a red-and-white line that dips in the middle.

    A LINE THAT DOES NOT SAG IS A BEAM. The dip is what says fabric, and it is the cheapest thing
    in this design that says FAIRGROUND rather than civic square - which is the whole of Jack's
    *"make sure this court also fits the theme of the center island area"*. It is strung six
    courses up, so a walker passes under it and the vista to the wheel runs beneath it.
    """
    mid = (u0 + u1) // 2
    span = max(1, (u1 - u0) // 2)
    made = 0
    for u in range(u0, u1 + 1):
        dip = 1 if abs(u - mid) * 3 < span else 0
        mat = PAL["band"] if ((u - u0) // 2) % 2 == 0 else PAL["frame"]
        made += bool(L.put(v, y - dip, u, mat))
    m["bunting"] += 1
    return made


def _pavilion(L, v0, u0, v1, u1, seed, m) -> dict:
    """AN OPEN CANVAS PAVILION - the piece that makes this court read as a fairground.

    Eight timber posts, a white frieze and a STRIPED CANVAS ROOF: `crimson_stairs` L62 against
    `polished_diorite_stairs` L193, which is the same pair the Midway's four buildings roof with,
    measured rather than remembered and 131 points of luminance apart in one step. So the court's
    two pavilions are the same hand as the Arrival Court and the Skill Arcade, and the flank they
    stand on stops being lawn.

    IT IS OPEN ON ALL FOUR SIDES. A shed here would be a fifth building on a lot whose job is to
    be walked across; what a walk-up wants is shelter you can see through, with a seat in it.
    """
    made = {"posts": 0, "seats": 0}
    for v in range(v0, v1 + 1):
        for u in (u0, u1):
            if v in (v0, v1) or (v - v0) % 3 == 0:
                for y in range(1, 6):
                    made["posts"] += bool(L.put(v, y, u, PAL["beam"], axis="y"))
    for u in range(u0 + 1, u1):
        for v in (v0, v1):
            if (u - u0) % 3 == 0:
                for y in range(1, 6):
                    made["posts"] += bool(L.put(v, y, u, PAL["beam"], axis="y"))
    for v in range(v0, v1 + 1):                    # the frieze the roof sits on
        for u in range(u0, u1 + 1):
            if v in (v0, v1) or u in (u0, u1):
                L.put(v, 6, u, PAL["frame"])
    m["roof"] = _hip(L, v0, u0, v1, u1, 7, seed, stripe=CANVAS)
    for v in range(v0 + 2, v1 - 1, 3):             # ...and the lights hung off its own frieze
        for u in (u0 + 1, u1 - 1):
            m["lamps"] += bool(_lamp(L, v, 5, u))
    return made


def _hedge(L, cells, m) -> int:
    """A CLIPPED HEDGE: one course of leaves on the bed's own kerb.

    It is what turns a kerbed square of moss into a BED. Persistent, because a leaf block with
    `persistent=false` and no log within six decays - the one property of a leaf that a render
    cannot show and that every leaf this repo places has had set since the first sky bird.
    """
    n = 0
    for v, u in cells:
        n += bool(L.put(v, 1, u, PAL["leaf"], distance="1", persistent="true",
                        waterlogged="false"))
    m["hedge"] += n
    return n


def _court_pave(v, u, mid, axis, seed, half, rad) -> str:
    """The court's floor, and EVERY LINE IN IT IS DERIVED FROM THE AXIS.

    A pattern laid on world coordinates is right for a building, whose rooms have to line up with
    each other; it is wrong for a composition whose whole subject is one centre line, because the
    grid then lands wherever the lot happens to start. Here the rings are concentric on the basin
    and the bands are measured from the axis, so the floor itself says where the middle is.

    THE RED AND WHITE DASH IS THE MIDWAY'S OWN COLOUR IN THE FLOOR. It runs the walk's inner edge
    and the roundel's inner ring in runs of three - a one-cell alternation is noise past ten
    blocks, and a solid band of either is a stripe the whole park already has too much of.
    """
    du, dv = abs(u - axis), v - mid
    d2 = dv * dv + (u - axis) ** 2
    r = int(d2 ** 0.5)
    if du == half or r == rad:
        return PAL["inlay"]                        # the kerb of the walk and of the roundel
    if du == half - 1 or r == rad - 3:
        return PAL["band"] if ((v + u) // 3) % 2 == 0 else PAL["frame"]
    if r in (rad - 1, rad - 2):
        return PAL["field"]
    if du < half and (v - mid) % 6 == 0:
        return PAL["field"]                        # the walk's rungs
    return PAL["floor2"] if (v + u) % 2 == 0 or hash01(v, u, seed) < 0.12 else PAL["floor"]


def _welcome_court(L, p) -> dict:
    """THE WALK-UP: what a visitor crosses between the entry gate and the wheel.

        V24-74 x U270-330, axis U300, centre V49 - fifty-one deep by SIXTY-ONE wide

    Jack, in two passes: *"gates and a board etc are all overlapping and chaotic with the entrance
    to the main center ... make the entrance experience, and the leading park in front of it
    before the ferris wheel perfect, highly detailed, sophisticated, no weird blocks, or overlaps,
    no bad placements ... we need this to feel premium and clean"*, and then *"this court also
    fits the theme of the center island area, and fills the space nicely, we dont want immediate
    large amounts of empty green."*

    WHAT WAS HERE, measured off the shipped park rather than described: 4,613 blocks paved edge to
    edge on one world-aligned grid, eleven trees of four species at eleven positions nothing
    derived, nine `magenta_wool` and fifteen `light_blue_wool` cells with no other member of their
    own colour near them, and lamp standards whose head course was a `yellow_wool` block. Nothing
    in it was symmetric about the axis it stands on - and the axis is the ONE thing this lot has:
    the entry gate's two doors, this court and the Sky Lift's hub all sit on U300, and the wheel's
    densest column is U300 with 435 cells against 375 at each neighbour.

    THE LOT IS SIXTY-ONE WIDE AND WAS FORTY-ONE. Measured off the shipped ground layer, the two
    flanks either side of the old lot were **714 columns of bare moss each** and nothing else, in
    full view of the gate - which is exactly the "immediate large amounts of empty green". At
    U270-330 the court now has the SAME FRONTAGE AS THE ENTRY GATE, whose compound is U270-330 to
    the cell, so the two read as one composition rather than as a gate with a smaller thing behind
    it.

    THE COMPOSITION IS THE AXIS, and every piece is derived from it:

        the great walk   U294-306, V24 to V74 - thirteen wide, the spine's own width
        the roundel      r=13 on (V49, U300), where the walk opens out
        the basin        a raised stone fountain on the axis: two tiers, four courses, water
        two pavilions    V43-55 x U270-278 and U322-330, striped canvas on timber posts
        the cross walk   V46-52, joining the roundel to both pavilions
        four parterres   kerbed, hedged, two oaks each, on the four quadrant centres
        two garden rooms V64-74 at both rear corners - see the queue, below
        lamp standards   the lamp above, paired about the axis and never on it
        bunting          four swags across the walk, six courses up

    **NOTHING OF THIS COURT'S STANDS IN THE WALK.** Every lamp, pier, bench, post and tree is at
    |U-300| >= 7, so the thirteen-wide walk is clear above its own floor course for all fifty-one
    courses except the basin - which is on the axis deliberately, four courses high against a
    seventy-four-course wheel behind it. `tests/test_midway_builds.py` measures that rather than
    trusting this paragraph.

    **THE POOL CANNOT DRAIN.** Its wall is built by the shell rule - the cells outside the disc
    that have a face neighbour inside it - so there is no diagonal gap for water to find, and the
    course under every water cell is this court's own paving.

    **THE WHEEL'S QUEUE OWNS THE WEST REAR CORNER AND THIS DESIGN DOES NOT TOUCH IT.** Measured
    off `out/PF Front Midway.litematic`, the Sky Lift's queue occupies exactly V65-74 x U270-279
    inside this lot - fifty-four columns, a clean ten by ten. It is named in `blocked`, so wanting
    one of its cells raises here rather than shipping as an overlap nobody can see. The court
    frames that corner as a hedged garden room and builds nothing inside it; the east corner is
    the same room with seats in it, so the plan is symmetric in FRAME while one of the two rooms
    honestly holds a queue.
    """
    seed = int(p["seed"])
    v0, u0, v1, u1 = (int(q) for q in p["lot"])
    axis = (u0 + u1) // 2                          # U300 - the gate's doors and the wheel's hub
    mid = (v0 + v1) // 2                           # V49
    half = 6                                       # the great walk is thirteen wide
    rad = 13                                       # the roundel
    m = {"signs": 0, "lamps": 0, "benches": 0, "trees": 0, "beds": 0, "floor": 0, "water": 0,
         "steps": 0, "hedge": 0, "bunting": 0, "axis": axis, "centre": mid}

    #: THE WHEEL'S QUEUE, and the court builds nothing here. Ten by ten at the west rear corner,
    #: read off the frontage design rather than assumed.
    queue = {(v, u) for v in range(65, v1 + 1) for u in range(u0, u0 + 10)}

    walk = {(v, u) for v in range(v0, v1 + 1) for u in range(axis - half, axis + half + 1)}
    roundel = _disc(mid, axis, rad)
    pavilions = [(mid - 6, u0, mid + 6, u0 + 8), (mid - 6, u1 - 8, mid + 6, u1)]
    cross = {(v, u) for v in range(mid - 3, mid + 4) for u in range(u0 + 8, u1 - 7)}
    paved = walk | roundel | cross
    for pv0, pu0, pv1, pu1 in pavilions:
        paved |= {(v, u) for v in range(pv0, pv1 + 1) for u in range(pu0, pu1 + 1)}

    # THE FOUR PARTERRES, on the quadrant centres and mirrored twice. Thirteen by seventeen: big
    # enough for two trees and a hedge round them, which is what stops a bed reading as a pot.
    beds = [(v, u, du) for v, du in ((mid - 16, 1), (mid + 16, -1))
            for u in (axis - 17, axis + 17)]
    bed_in, bed_kerb = set(), set()
    for bv, bu, _d in beds:
        inner = {(v, u) for v in range(bv - 5, bv + 6) for u in range(bu - 7, bu + 8)}
        outer = {(v, u) for v in range(bv - 6, bv + 7) for u in range(bu - 8, bu + 9)}
        bed_in |= inner
        bed_kerb |= outer - inner

    # the two rear garden rooms, framed on their inner edges so the frame never enters the queue
    rooms = [(v0 + 40, u0, v1, u0 + 9), (v0 + 40, u1 - 9, v1, u1)]
    room_kerb = set()
    for rv0, ru0, rv1, ru1 in rooms:
        room_kerb |= {(rv0, u) for u in range(ru0, ru1 + 1)}
        room_kerb |= {(v, ru0 if ru0 > u0 else ru1) for v in range(rv0, rv1 + 1)}

    # -- 1. the podium ---------------------------------------------------------------------------
    # ONE COURSE, because every lot in this park is one course over the lawn the streets are cut
    # into. The threshold on the axis is a stair rather than a kerb, at both ends, so the walk-up
    # is a step rather than a ledge.
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            if (v, u) in queue:
                continue
            if v in (v0, v1) and abs(u - axis) <= half:
                # A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD facing=D - the convention pinned
                # in `test_stairhead`, and one our own renderer draws identically either way.
                m["steps"] += bool(L.put(v, 0, u, PAL["trim"],
                                         facing="east" if v == v0 else "west",
                                         half="bottom", shape="straight", waterlogged="false"))
                continue
            if v in (v0, v1) or u in (u0, u1) or (v, u) in bed_kerb or (v, u) in room_kerb:
                mat = PAL["inlay"]                 # the kerb: this court's own dark line
            elif (v, u) in bed_in:
                mat = PAL["lawn"]
            elif (v, u) in paved:
                mat = _court_pave(v, u, mid, axis, seed, half, rad)
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
            elif dv and du:
                # A CORNER OF THE FLARE FACES TWO WAYS AND A STAIR FACES ONE, so a corner cell is
                # a slab. Given a facing it would lean along whichever axis was written first and
                # break the bowl's own symmetry - which our renderer draws exactly as it draws a
                # correct one.
                L.put(mid + dv, 3, axis + du, PAL["cap"], type="top", waterlogged="false")
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

    # -- 3. the two pavilions --------------------------------------------------------------------
    for pv0, pu0, pv1, pu1 in pavilions:
        _pavilion(L, pv0, pu0, pv1, pu1, seed, m)
        inward = 1 if pu0 == u0 else -1
        for v in (pv0 + 3, pv1 - 3):               # seats under it, facing the court
            _bench(L, v, pu0 + 4, 0, inward, 3, m)
    m["pavilions"] = len(pavilions)

    # -- 4. the parterres ------------------------------------------------------------------------
    for bv, bu, _d in beds:
        _hedge(L, [(v, u) for v, u in bed_kerb
                   if max(abs(v - bv) - 5, abs(u - bu) - 7) == 1], m)
        for du in (-4, 4):
            _tree(L, bv, bu + du, m)
        for dv, du in ((-3, 0), (3, 0), (0, -7), (0, 7)):
            L.put(bv + dv, 1, bu + du, PAL["shrub"])
        m["beds"] += 1

    # -- 5. the garden rooms ---------------------------------------------------------------------
    # ONE OF THESE HOLDS THE WHEEL'S QUEUE AND THE OTHER HOLDS SEATS, and only the second is built
    # in: a frame drawn round somebody else's design is the most a court may honestly do there.
    for rv0, ru0, rv1, ru1 in rooms:
        if any((rv0 + 1, u) in queue for u in range(ru0, ru1 + 1)):
            continue
        cu = (ru0 + ru1) // 2
        _tree(L, rv0 + 4, cu, m)
        _bench(L, rv0 + 8, cu, -1, 0, 3, m)
        _standard(L, rv0 + 2, cu, m)

    # -- 6. the standards, the benches, the bunting and the thresholds ---------------------------
    # PAIRED ABOUT THE AXIS AND NEVER ON IT. Every one of these is at |U-300| >= 7, which is what
    # keeps the vista from the gate to the wheel clear of this court's own furniture.
    for v in (v0 + 5, mid - 16, mid + 16, v1 - 5):
        for u in (axis - half - 1, axis + half + 1):
            _standard(L, v, u, m)
        _swag(L, v, axis - half - 1, axis + half + 1, 6, m)
    for dv, look in ((-rad + 4, 1), (rad - 4, -1)):
        _bench(L, mid + dv, axis - half - 3, look, 0, 3, m)
        _bench(L, mid + dv, axis + half + 3, look, 0, 3, m)

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

p = 'mcbuild/gen/midway_builds.py'
s = open(p, encoding='utf-8').read()
start = s.index('# ---------------------------------------------------------------------------- the court kit')
end = s.index('_KINDS = {')
s = s[:start] + NEW + s[end:]
open(p, 'w', encoding='utf-8').write(s)
print('replaced', end - start, 'chars with', len(NEW))
