"""The park's ENTRANCE ZONE: the arrival experience, not a themed land.

`gen/park.py` builds the attractions - the gate you come through, the arches into each land, the
towers and the walkthroughs. This builds what a visitor stands in the middle of once they are
INSIDE the gate and have not yet chosen a land: a fountain, a memorial, a shopping street, a
bandstand and a guest-services office. Lighthearted, civic, and deliberately palette-bright: it
is `land="midway"` by default, which is the wool-and-stone-brick land.

It follows `park.py`'s conventions exactly and imports its frame, its palettes and its sign,
light and trim helpers rather than restating them - two modules that each own a copy of "which
way does a stair lean" is how a facing bug becomes two facing bugs.

    at       the structure's FRONT-LEFT floor corner, in world coordinates
    facing   the direction the FRONT looks out - a visitor stands in the +facing direction
    i        runs along the frontage (the side axis)
    d        runs from the front INTO the building; d=0 is the front wall
    h        courses up from the floor, and h=-1 is the pad the whole thing stands on

**THE PLOT IS VOID, SO EVERY KIND CARRIES ITS OWN GROUND.** There is no terrain on a skyblock
plot to stand a building on; the pad at h=-1 is not decoration, it is the reason the design is
one connected piece rather than a shape floating over nothing.

**THE FAILURE THIS FILE IS WRITTEN AGAINST IS SAMENESS.** The previous entrance zone was rejected
as *"single small structures... some infrastructure and some huts"* - identical boxes, laid in a
row. So every kind here varies WITHIN itself, from a deterministic hash of the cell or the index
and never from `random`: the statue picks one of three figures, the bandstand one of two plans
and two roof profiles, guest services one of two crowns, and `shopstreet` - which is the whole
argument - varies width, storeys, roof, awning, jetty, door position, window pattern, field
material and accent colour PER SHOP, so no two shops in a terrace are the same building.

**WHAT MAKES VOXELS READ AS ARCHITECTURE IS REGULARITY AND OPENINGS, NOT DAMAGE**, which is the
rule the void tower, the sanctum, the campanile and the casino hall all arrived at separately.
Nothing here is ruined, sheared or weathered; the variety is in the PLAN.

**AND A CIRCLE IS A DISTANCE TEST, NEVER AN OUTLINE YOU DRAW.** The fountain is
`di*di + dd*dd <= r*r`. A hand-drawn ring at this radius is an octagon that lost, and a constant
band in the radius equation is fat at the diagonals and thin on the axes.

But there are TWO ring rules here and they are not interchangeable. A roof ring or an entablature
is a SHELL - inside, with a neighbour outside - which is the rule the sphere fill settled. A
BASIN RIM cannot be: at r=8 the cell (-5,-5) is inside, is not water, and has four neighbours also
inside, so the shell skips it and the basin drains through eight holes on its diagonals. A rim is
the full one-radius `_annulus`, because a step of one raises the radius by at most one.

**A WATER CELL NEEDS A SOLID BED AND A SOLID RIM.** Each of the fountain's three basins is a
disc of source blocks whose bed is the whole disc one course down and whose rim is the annulus
one radius out, so a water cell can never have an open horizontal neighbour: one step out raises
the radius by at most one, and the rim is exactly that one step wide.

MATERIALS. Everything comes from `park.LANDS[land]`; the few blocks added here were each checked
against `blocks.spendable`, `blocks.available` and `palette.tier` before being written down, and
all are cheap or ok:

    water · glass_pane (ok) · end_rod · bell · barrel · the land's own wood trapdoor
    the land's own slab and stairs · eight cheap wools
    stone_brick_wall / cobblestone_wall / polished_blackstone_brick_wall (the balustrade)

No fence and no fence gate: the balustrade is wall-plus-slab, so `pal["fence"]`, `pal["gate"]`,
`pal["beam"]` and `pal["canopy"]` are the four keys of `park.LANDS` this module never reads.

No dirt, grass, podzol or mud - they are CURRENCY on this server. No sand or gravel, which would
pour into the void off an overhanging eave. No quartz, concrete, terracotta, glass block,
sea lantern, glowstone, hay or **note block** - all expensive here, note block deliberately: it is
the reason the bandstand plays with a second BELL rather than a note block. A bell rings on a
right-click whatever powers it and costs nothing; a note block is `expensive` tier
(`palette.tier("note_block") == "expensive"`) even before anyone asks whether it is wired.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .park import (
    LANDS, SIGN_WIDTH, _STEP, _BACK, _LEAN, _Frame,
    _sign, _hang_light, _trim_run,
)

# The direction NAME of a unit step in world coordinates. Everything angular in this file goes
# through it, so "which way is +i" is answered in one place.
_NAME = {(0, -1): "north", (0, 1): "south", (1, 0): "east", (-1, 0): "west"}

# A balustrade is wall-plus-slab at 1.5 blocks - the taproot entrance's own idiom. The wall block
# has to match the land's ground, and there is no one-to-one rule for that, so it is a table.
_BALUSTRADE = {
    "stone_bricks": "stone_brick_wall",
    "cobblestone": "cobblestone_wall",
    "polished_blackstone_bricks": "polished_blackstone_brick_wall",
}

# The terrace's field materials. A row of shops in ONE material is a warehouse with doors in it,
# so each shop draws its field from its land's list by hash. All cheap, all spendable, all 1.19.
_FIELDS = {
    "midway": ["white_wool", "light_gray_wool", "oak_planks", "stone_bricks"],
    "frontier": ["spruce_planks", "oak_planks", "cobblestone", "stone_bricks"],
    "hollow": ["black_wool", "gray_wool", "deepslate_bricks", "polished_blackstone_bricks"],
}

# The shop accents - awning stripes, shutters, sign boards. Eight cheap wools, so two neighbours
# almost never land on the same one.
_ACCENTS = ["red_wool", "yellow_wool", "lime_wool", "light_blue_wool",
            "orange_wool", "purple_wool", "cyan_wool", "magenta_wool"]

# What a shop sells. The sign is the only thing that says so, and a street of unnamed shops is a
# street of sheds.
_TRADES = [
    ("BAKERY", "fresh daily"), ("TOY SHOP", "wind-ups"), ("HAT STAND", "all sizes"),
    ("SWEET SHOP", "by the ounce"), ("MAP SELLER", "know the park"), ("ICE CREAM", "nine flavours"),
    ("FLOWER STALL", "cut and potted"), ("BOOK NOOK", "second hand"), ("CLOCKMAKER", "repairs"),
    ("TEA ROOM", "pot for one"), ("PIN & BADGE", "collect them"), ("KITE SHOP", "windy days"),
]

CIVIC = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "fountain",
    "facing": "east",
    "land": "midway",
    "title": None,
    "lines": None,
    "radius": 8,                # fountain / bandstand
    "width": 15,                # guestservices; shopstreet derives its own
    "depth": 9,
    "shops": 7,                 # shopstreet: at least six, and never two alike
    "shop_depth": 8,
    "figure": None,             # statue: obelisk | robed | emblem; None picks by hash
    "plan": None,               # bandstand: octagon | square; None picks by hash
    "crown": None,              # guestservices: clock | emblem; None picks by hash
    "seed": 0,
    "min_run": 3,
    "sign": True,
}


# ------------------------------------------------------------------ frame-relative directions

def _i_dir(f, s):
    """The world direction name of +i (s=1) or -i (s=-1)."""
    return _NAME[(f.sx * s, f.sz * s)]


def _d_dir(f, s):
    """+d runs INTO the building, which is `f.back`; -d is `f.facing`."""
    return f.back if s > 0 else f.facing


def _face_in(f, i, d, a, b, c, e):
    """For a cell on the border of the rect [a..b]x[c..e], the direction pointing INWARD.

    A roof stair's TALL side is its `facing` and the surface descends outward, so a roof stair
    faces inward - up the slope. Our renderer draws both directions identically, which is exactly
    why this is one function with one test rather than a judgement made at eight call sites.
    """
    ei, ed = min(i - a, b - i), min(d - c, e - d)
    if ei <= ed:
        return _i_dir(f, 1) if (i - a) <= (b - i) else _i_dir(f, -1)
    return _d_dir(f, 1) if (d - c) <= (e - d) else _d_dir(f, -1)


def _face_out_radial(f, di, dd):
    """Outward from a centre, for a ring that is round rather than rectangular."""
    if abs(di) >= abs(dd):
        return _i_dir(f, 1 if di > 0 else -1)
    return _d_dir(f, 1 if dd > 0 else -1)


def _pane_props(f, along_i=True):
    """A pane with every side false renders as a lone post, so its connections are set ALONG the
    wall it is set into - the campanile's own note, arrived at the hard way."""
    a, b = (_i_dir(f, 1), _i_dir(f, -1)) if along_i else (_d_dir(f, 1), _d_dir(f, -1))
    pr = {"north": "false", "south": "false", "east": "false", "west": "false",
          "waterlogged": "false"}
    pr[a] = "true"
    pr[b] = "true"
    return pr


def _stair(w, f, i, d, h, block, facing, half="bottom"):
    w.put(*f.at(i, d, h), block, facing=facing, half=half, shape="straight", waterlogged="false")


def _slab(w, f, i, d, h, block, typ="bottom"):
    w.put(*f.at(i, d, h), block, type=typ, waterlogged="false")


def _free(w, f, i, d, h):
    return not w.has(*f.at(i, d, h))


def _put_free(w, f, i, d, h, block, **props):
    """Place only into an empty cell. Water is laid last through this, so a pedestal standing in a
    basin is never drowned by the fill that comes after it."""
    if _free(w, f, i, d, h):
        w.put(*f.at(i, d, h), block, **props)
        return True
    return False


class _Plaques:
    """Signs, counted. `park._sign` returns False when the wall behind the sign has an OPENING in
    it and places nothing - which is correct, and silent, and is how a kind ships with a nameplate
    that does not exist. Attempted and placed are both reported so the two can be compared.

    IT ALSO OWNS `sign`, because otherwise nobody does. `CIVIC["sign"] = True` was declared and
    never read by any kind: `sign: False` in a config switched nothing off and said nothing about
    it, which is this repo's oldest failure - a setting that reports success and does nothing.
    `park` honours the same key, and two modules that read one key differently is worse than one
    that ignores it.
    """

    def __init__(self, on=True):
        self.on = bool(on)
        self.want = 0
        self.got = 0

    def __call__(self, w, f, pal, i, d, h, facing, lines, back=()):
        for ln in lines:
            assert len(str(ln)) <= SIGN_WIDTH, f"sign line {ln!r} is over {SIGN_WIDTH} chars"
        if not self.on:
            return False
        self.want += 1
        if not _free(w, f, i, d, h):
            return False
        ok = _sign(w, f, pal, i, d, h, facing, lines, back)
        self.got += int(bool(ok))
        return ok


def _lamp_post(w, f, pal, i, d, h0=0, tall=3):
    """A post carrying its own light. The lantern STANDS on the cap - written `hanging=true` it is
    looking for a block above it, finds open sky, and is a lantern hanging from nothing."""
    for h in range(h0, h0 + tall):
        w.put(*f.at(i, d, h), pal["post"])
    w.put(*f.at(i, d, h0 + tall), pal["trim"])
    w.put(*f.at(i, d, h0 + tall + 1), pal["light"], hanging="false", waterlogged="false")


# ------------------------------------------------------------------ shapes

def _disc(di, dd, r):
    return di * di + dd * dd <= r * r


def _oct(di, dd, r, square=False):
    if square:
        return max(abs(di), abs(dd)) <= r
    return max(abs(di), abs(dd)) <= r and abs(di) + abs(dd) <= int(r * 1.5)


def _cells(c, r, test, *a):
    """Every (di, dd) inside a shape of radius r, in a stable order."""
    return [(di, dd) for di in range(-r, r + 1) for dd in range(-r, r + 1) if test(di, dd, r, *a)]


def _border(r, test, *a):
    """Inside, with a neighbour outside - never a band in the radius equation, which is fat at the
    diagonals and thin on the axes. This is the SHELL rule and it is right for a roof ring or an
    entablature; it is NOT watertight, which is what `_annulus` is for."""
    out = []
    for (di, dd) in _cells(0, r, test, *a):
        if any(not test(di + ux, dd + uz, r, *a) for ux, uz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            out.append((di, dd))
    return out


def _annulus(r, test, *a):
    """Inside r and outside r-1: the full one-radius band, which is what a BASIN RIM has to be.

    Built from `_border` instead, the fountain leaked from eight cells on its diagonals - a cell
    like (-5,-5) at radius 7.07 is inside r=8 and has four neighbours also inside it, so it is not
    on the shell, and it is not water either. It came out as a hole in the coping. A step of one
    raises the radius by at most one, so a full band exactly one radius wide cannot be stepped
    over; a shell can.
    """
    inner = set(_cells(0, r - 1, test, *a))
    return [t for t in _cells(0, r, test, *a) if t not in inner]


# ------------------------------------------------------------------ walls, roofs

def _box(w, f, i0, i1, d0, d1, h0, h1, block, corner=None, holes=()):
    """A rectangular wall ring. THE OPENINGS ARE LEFT EMPTY BY THE LOOP, never punched afterwards:
    building the ring first and cutting a hole repaints cells that already exist, which is how the
    void tower's crenellations shipped as a plain drum with nothing about the code looking wrong."""
    holes = set(holes)
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            if not (i in (i0, i1) or d in (d0, d1)):
                continue
            is_corner = i in (i0, i1) and d in (d0, d1)
            for h in range(h0, h1 + 1):
                if (i, d, h) in holes:
                    continue
                w.put(*f.at(i, d, h), (corner or block) if is_corner else block)
                n += 1
    return n


def _plane(w, f, i0, i1, d0, d1, h, block):
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            w.put(*f.at(i, d, h), block)


def _trim_col(w, f, pal, cells, h, min_run=3, half="top"):
    """`park._trim_run`, but running along d instead of along i.

    `_trim_run` groups its cells by d and walks i, which is right for a course that runs along the
    frontage and USELESS for one running into the building: every flank cell arrives as its own
    one-cell row, every row is under `min_run`, and the whole course is dropped in silence. That is
    how the eave shipped on two of a building's four sides - the front and the back were laid, both
    flanks were not, and the only evidence was a return value nobody compared to the ask.

    The `_LEAN` is applied here exactly as `park._flush` applies it, so a cell handed to either
    helper leans the same way. Our renderer draws both directions identically, which is why this is
    one function rather than a judgement made per call site.
    """
    def flush(i, run):
        if len(run) < min_run:
            return 0
        for (d, face) in run:
            _stair(w, f, i, d, h, pal["stair"], _LEAN[face], half=half)
        return len(run)

    by_i = {}
    for (i, d, face) in cells:
        by_i.setdefault(i, []).append((d, face))
    laid = 0
    for i, col in sorted(by_i.items()):
        col.sort()
        run = []
        for (d, face) in col:
            if run and d == run[-1][0] + 1:
                run.append((d, face))
            else:
                laid += flush(i, run)
                run = [(d, face)]
        laid += flush(i, run)
    return laid


def _eave(w, f, pal, i0, i1, d0, d1, h, min_run, front=True, sides=True):
    """An overhanging cornice one cell outside the wall: upside-down stairs whose FULL half is
    against the wall. The corpus says we place stairs at a seventh of the rate outside builders
    do, and a flat wall meeting a flat roof at a right angle is this repo's known weakness.

    `front=False` LEAVES THE FRONT RUN OFF, and that is not a nicety. A shopfront's front edge
    already carries a fascia, and the fascia is the only thing a nameplate has to hang on: the
    eave ran through the sign cell and six of eight shops shipped with no name at all, silently,
    because `park._sign` places nothing when the cell it wants is taken.

    `sides=False` LEAVES BOTH FLANKS OFF, and that is for a TERRACE. A shop's party wall is its
    neighbour's party wall, so a flank eave at `i1 + 1` is a stair stamped a course into the shop
    next door. Free-standing kinds take the flanks; anything sharing a wall must not.

    THE TWO AXES ARE LAID BY DIFFERENT HELPERS ON PURPOSE. `park._trim_run` only ever measures a
    run along i, so handing it the flank cells scored each of them as a run of one and dropped the
    lot - the cornice existed on the front and back and nowhere else, and it audited perfectly
    because nothing that is not placed can be illegal. The flanks go through `_trim_col`, and the
    two counts are added so the caller can compare what was asked for with what was laid.
    """
    rows, cols = [], []
    for i in range(i0 - 1, i1 + 2):
        for d in range(d0 - 1, d1 + 2):
            on_i = i in (i0 - 1, i1 + 1)
            on_d = d in (d0 - 1, d1 + 1)
            if not (on_i or on_d):
                continue
            if on_i and on_d:
                continue                    # a corner faces two ways and can face only one
            if on_d and not front and d == d0 - 1:
                continue
            face = _face_in(f, i, d, i0 - 1, i1 + 1, d0 - 1, d1 + 1)
            (cols if on_i else rows).append((i, d, _LEAN[face]))
    laid = _trim_run(w, f, pal, rows, h, min_run, half="top")
    if sides:
        laid += _trim_col(w, f, pal, cols, h, min_run, half="top")
    return laid


def _roof_gable(w, f, pal, i0, i1, df, db, rh, field, trim):
    """Ridge front-to-back, so the STREET SEES A GABLE END - the classic shopfront.

    The two end walls are FILLED triangles and that is load-bearing, not cosmetic: a roof built as
    slope cells alone is a set of rows one cell wide at rising levels, and consecutive rows meet
    only diagonally. Six-connectivity does not see a diagonal, so the roof would ship as one
    fragment per course. The filled ends tie every level to the one below it.
    """
    half = (i1 - i0) // 2
    top = rh
    for lv in range(half + 1):
        a, b = i0 + lv, i1 - lv
        if a > b:
            break
        top = rh + lv
        for d in (df, db):
            for i in range(a, b + 1):
                w.put(*f.at(i, d, top), field)
        for d in (df - 1, db + 1):          # the bargeboard: a raking verge, proud of the gable
            if a == b:
                w.put(*f.at(a, d, top), trim)
            else:
                w.put(*f.at(a, d, top), trim)
                w.put(*f.at(b, d, top), trim)
        for d in range(df + 1, db):
            if a == b:
                w.put(*f.at(a, d, top), trim)
            else:
                _stair(w, f, a, d, top, pal["stair"], _i_dir(f, 1))
                _stair(w, f, b, d, top, pal["stair"], _i_dir(f, -1))
    return top


def _roof_hip(w, f, pal, i0, i1, df, db, rh, field, trim):
    """A pyramid. Each ring is stairs facing up-slope with a course of SARKING under it, which is
    what ties ring L to ring L-1 - the same diagonal problem the gable's filled ends solve."""
    lv = 0
    top = rh
    while True:
        a, b, c, e = i0 + lv, i1 - lv, df + lv, db - lv
        if a > b or c > e:
            break
        top = rh + lv
        if (b - a) <= 1 or (e - c) <= 1:
            # THE RIDGE NEEDS SARKING TOO. Written as a bare cap it sat one course above the last
            # ring and one cell inside it - diagonal on both axes - and every hip roof in the file
            # shipped its ridge as a separate floating piece, four cells at a time.
            if lv:
                _plane(w, f, a, b, c, e, top - 1, field)
            _plane(w, f, a, b, c, e, top, trim)
            break
        for i in range(a, b + 1):
            for d in range(c, e + 1):
                if not (i in (a, b) or d in (c, e)):
                    continue
                _stair(w, f, i, d, top, pal["stair"], _face_in(f, i, d, a, b, c, e))
                if lv:
                    w.put(*f.at(i, d, top - 1), field)
        lv += 1
    return top


def _roof_flat(w, f, pal, i0, i1, df, db, rh, field, trim, cren=False):
    """A deck with a parapet and a coping. The parapet's crown course is left EMPTY when it is
    crenellated - laying a full ring and alternating merlons over it repaints cells that already
    exist, alternates perfectly and changes nothing."""
    _plane(w, f, i0, i1, df, db, rh, trim)
    _box(w, f, i0, i1, df, db, rh + 1, rh + 1, field, corner=trim)
    for i in range(i0, i1 + 1):
        for d in range(df, db + 1):
            if not (i in (i0, i1) or d in (df, db)):
                continue
            if cren:
                if (i + d) % 2 == 0:
                    w.put(*f.at(i, d, rh + 2), trim)
            else:
                _slab(w, f, i, d, rh + 2, pal["slab"], "bottom")
    return rh + 2


def _roof_crowstep(w, f, pal, i0, i1, df, db, rh, field, trim):
    """A crow-stepped gable: the front and back walls carry on ABOVE the roof deck in steps, each
    step capped with a slab tread. Two courses wide per step, or the 'steps' are a sawtooth."""
    _plane(w, f, i0, i1, df, db, rh, trim)
    for i in range(i0, i1 + 1):             # side parapets, so the deck is not an open shelf
        if i in (i0, i1):
            for d in range(df, db + 1):
                w.put(*f.at(i, d, rh + 1), field)
                _slab(w, f, i, d, rh + 2, pal["slab"], "bottom")
    top = rh + 2
    for k in range(0, (i1 - i0) // 2 + 1):
        a, b = i0 + 2 * k, i1 - 2 * k
        if a > b:
            break
        lv = rh + 1 + k
        for d in (df, db):
            for i in range(a, b + 1):
                w.put(*f.at(i, d, lv), field)
            for i in (a, min(a + 1, b), max(b - 1, a), b):
                _slab(w, f, i, d, lv + 1, pal["slab"], "bottom")
        top = max(top, lv + 1)
    return top


# ------------------------------------------------------------------ the fountain

def _fountain(w: World, p: dict, ctx) -> dict:
    """THE PARK'S CENTREPIECE: three basins of real water on a round stepped surround, and it
    actually CASCADES - see `notch2`/`notch3` below.

    Seventeen across at the widest basin, twenty-one including the seat ring and twenty-five
    including the paving - which is the smallest a three-tier fountain can be and still have a
    tier three: the top dish needs a rim annulus AND water AND a jet column, and below radius two
    those are the same cells.

    (The three radii are `r0`, `r_step = r0 + 2` and `r_pad = r0 + 4`, so 17 / 21 / 25 at the
    floor of `r0 = 8`. This said "twenty-five including the seat ring", which is the PAVING's
    number wearing the seat ring's name - the two are four blocks apart and only one of them is
    what a visitor sits on.)

    THREE POOLS OF NOTHING BUT SOURCE BLOCKS IS THE LOG FLUME'S OWN FAILURE. It audits clean,
    costs nothing, looks exactly like a fountain in every render here, and never moves - Jack's
    own verdict on the flume, word for word, would apply. So each upper rim has ONE open notch
    (never plugged with a block) and the column under it is left open too: real source blocks
    only ever sit in the interior fill, never in the notch, so everything from the notch down to
    where it lands is genuinely FLOWING or FALLING water, which `fluids.spread` in
    `tests/test_civic.py` confirms rather than trusts.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    say = _Plaques(p.get("sign", True))
    r0 = max(8, int(p["radius"]))               # basin one: 2*r0+1 across, so >= 17
    r1 = max(4, r0 - 3)                         # basin two
    r2 = 2                                      # basin three - the smallest dish that works
    r_step = r0 + 2
    r_pad = r0 + 4
    c = r_pad                                   # centre, in frame coordinates
    seed = int(p["seed"]) + f.x * 31 + f.z
    spokes = hash01(seed, 7) < 0.5

    # ---- h=-1 the plaza. A world-aligned grid, so the paving stays lined up across the module
    # boundary into `park._plaza` and `park._paths` - which is the only reason a plaza reads as
    # one square rather than as several designs meeting.
    pad = 0
    for (di, dd) in _cells(c, r_pad, _disc):
        x, y, z = f.at(c + di, c + dd, -1)
        if spokes and (di == 0 or dd == 0 or abs(di) == abs(dd)):
            blk = pal["accent"]
        elif x % 6 == 0 or z % 6 == 0:
            blk = pal["trim"]
        elif (x + z) % 2 == 0:
            blk = pal["ground"]
        else:
            blk = pal["path"]
        w.put(x, y, z, blk)
        pad += 1

    # ---- h=0 the bed, and the seat you step up onto
    for (di, dd) in _cells(c, r0, _disc):
        w.put(*f.at(c + di, c + dd, 0), pal["ground"])
    surround = set(_cells(c, r_step, _disc)) - set(_cells(c, r0, _disc))
    rim_step = set(_border(r_step, _disc))
    for (di, dd) in sorted(surround):
        if (di, dd) in rim_step:
            _stair(w, f, c + di, c + dd, 0, pal["stair"],
                   _BACK[_face_out_radial(f, di, dd)])
        else:
            w.put(*f.at(c + di, c + dd, 0), pal["path"])

    # ---- h=1 basin one: coping ring, water, and the pedestal standing in it
    coping = set(_annulus(r0, _disc))
    for (di, dd) in coping:
        w.put(*f.at(c + di, c + dd, 1), pal["trim"])
    for (di, dd) in _cells(c, r1, _disc):
        w.put(*f.at(c + di, c + dd, 1), pal["ground"])

    # ---- the pedestal: a drum that narrows and then corbels back out under basin two
    for (di, dd) in _cells(c, r1 - 2, _disc):
        w.put(*f.at(c + di, c + dd, 2), pal["ground"])
    for (di, dd) in _cells(c, r1 - 1, _disc):
        w.put(*f.at(c + di, c + dd, 3), pal["trim"])

    # ---- THE CASCADE. Three basins of nothing but source blocks is exactly how the log flume
    # failed - it audits, it costs nothing, and a rider (or here, the water itself) never moves.
    # So each upper rim carries ONE open notch, toward the front where the approach sees it, and
    # nothing is placed in the column under it: water is a SOURCE only where the interior fill
    # puts it, and every cell it reaches past the notch is FLOWING, which is what
    # `tests/test_civic.py` asks `fluids.spread` to prove rather than trusting the geometry.
    notch2 = (0, -r1)           # basin two spills over its own lip, onto the pedestal below it
    notch3 = (0, -r2)           # basin three spills the same way, straight into basin two

    # ---- h=4 basin two
    lip2 = set(_annulus(r1, _disc))
    for (di, dd) in lip2:
        if (di, dd) == notch2:
            continue
        w.put(*f.at(c + di, c + dd, 4), pal["trim"])
    for (di, dd) in _cells(c, r2, _disc):
        if (di, dd) == notch3:
            continue
        w.put(*f.at(c + di, c + dd, 4), pal["ground"])
        w.put(*f.at(c + di, c + dd, 5), pal["ground"])

    # ---- h=6 basin three, a dish around a jet column
    for (di, dd) in set(_annulus(r2, _disc)):
        if (di, dd) == notch3:
            continue
        w.put(*f.at(c + di, c + dd, 6), pal["trim"])
    w.put(*f.at(c, c, 6), pal["accent"])
    w.put(*f.at(c, c, 7), pal["accent"])
    w.put(*f.at(c, c, 8), "end_rod", facing="up")

    # ---- WATER LAST, and only into cells nothing else claimed. Source blocks: flowing water dies
    # seven cells from its source, and a basin fed by flow is a basin that empties - which is
    # fine here, because every source is still an interior fill, never the notch itself, so the
    # notch and everything below it down to the next basin is real FLOWING water, not a second
    # source pretending to be a waterfall.
    water = 0
    for (di, dd) in _cells(c, r0 - 1, _disc):
        water += int(_put_free(w, f, c + di, c + dd, 1, "water", level="0"))
    for (di, dd) in _cells(c, r1 - 1, _disc):
        water += int(_put_free(w, f, c + di, c + dd, 4, "water", level="0"))
    for (di, dd) in _cells(c, 1, _disc):
        water += int(_put_free(w, f, c + di, c + dd, 6, "water", level="0"))

    # ---- light. Lanterns STAND on the coping; posts stand on the seat ring.
    lamps = 0
    rays = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
    for (ux, uz) in rays:
        for t in range(r0, 0, -1):
            di, dd = ux * t, uz * t
            if (di, dd) in coping:
                w.put(*f.at(c + di, c + dd, 2), pal["light"],
                      hanging="false", waterlogged="false")
                lamps += 1
                break
    posts, front_post = 0, None
    for (ux, uz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for t in range(r_step, 0, -1):
            di, dd = ux * t, uz * t
            if (di, dd) in surround and (di, dd) not in rim_step:
                _lamp_post(w, f, pal, c + di, c + dd, 1, 3)
                posts += 1
                if (ux, uz) == (0, -1):
                    front_post = (c + di, c + dd)
                break

    # A plaque on the front post - IN FRONT OF IT, which is one cell shallower in d, not on the
    # post's own cell. Written at the post's coordinates the sign is placed into a solid block,
    # `_free` refuses it, and the fountain ships with a nameplate that does not exist.
    title = str(p.get("title") or "THE FOUNTAIN").upper()
    if front_post:
        say(w, f, pal, front_post[0], front_post[1] - 1, 3, f.facing,
            [title[:SIGN_WIDTH], "", "three tiers", "mind the step"])

    return {"kind": "fountain", "radius": r0, "tiers": 3, "water": water,
            "pad": pad, "lanterns": lamps, "posts": posts,
            "signs": say.want, "signs_placed": say.got,
            "contract": "three basins that hold water: every source has a solid bed one course "
                        "under it and a solid rim exactly one radius out, EXCEPT one open notch "
                        "per upper rim, so water genuinely cascades from tier three through tier "
                        "two into the bottom pool rather than sitting as three static ponds"}


# ------------------------------------------------------------------ the statue

def _plinth(w, f, pal, say, p, title):
    """A 7x7 plinth with a base, a flared skirting, a dado, a corbelled cornice and a cap.

    A plinth is where the relief goes. Four proud courses and two stair rings cost about eighty
    blocks and are the difference between a monument and a block with a thing on top of it.
    """
    _plane(w, f, -2, 8, -2, 8, -1, pal["path"])
    for i in range(-1, 8):
        for d in range(-1, 8):
            if i in (-1, 7) or d in (-1, 7):
                w.put(*f.at(i, d, -1), pal["ground"])
    _plane(w, f, 0, 6, 0, 6, 0, pal["trim"])            # the proud base
    for i in range(0, 7):                               # the flare up to the dado
        for d in range(0, 7):
            if i in (0, 6) or d in (0, 6):
                _stair(w, f, i, d, 1, pal["stair"], _face_in(f, i, d, 0, 6, 0, 6))
    for h in range(1, 5):                               # the dado
        _plane(w, f, 1, 5, 1, 5, h, pal["wall"])
    for i in range(1, 6):                               # a recessed panel on each face
        for d in (1, 5):
            if 1 < i < 5:
                w.put(*f.at(i, d, 3), pal["accent"])
    for d in range(1, 6):
        for i in (1, 5):
            if 1 < d < 5:
                w.put(*f.at(i, d, 3), pal["accent"])
    # THE CORNICE NEEDS ITS OWN CORE COURSE. Built as a ring alone it stands one cell outside the
    # dado and one course above it - diagonal, which six-connectivity does not see - so the
    # cornice, the cap and the entire figure standing on them shipped as one floating piece of a
    # hundred and seventy-four cells with a plinth underneath doing nothing.
    _plane(w, f, 1, 5, 1, 5, 5, pal["trim"])
    for i in range(0, 7):                               # the corbelled cornice
        for d in range(0, 7):
            if i in (0, 6) or d in (0, 6):
                _stair(w, f, i, d, 5, pal["stair"], _face_in(f, i, d, 0, 6, 0, 6), half="top")
    _plane(w, f, 0, 6, 0, 6, 6, pal["trim"])            # the cap
    say(w, f, pal, 3, 0, 3, f.facing,
        [title[:SIGN_WIDTH]] + [str(s)[:SIGN_WIDTH] for s in (p.get("lines") or
                                                              ["raised by the", "park company",
                                                               "in this year"])][:3])
    return 7


def _fig_obelisk(w, f, pal, base):
    """A tapering shaft with relief bands and a pyramidion. Columnar by construction, which is the
    one figure geometry this medium renders natively."""
    top = base
    for h in range(base, base + 10):
        for i in range(2, 5):
            for d in range(2, 5):
                band = (h - base) % 4 == 3
                w.put(*f.at(i, d, h), pal["accent"] if band and (i in (2, 4) or d in (2, 4))
                      else pal["wall"])
        top = h
    for i in range(2, 5):                                # the pyramidion, in stairs
        for d in range(2, 5):
            if i == 3 and d == 3:
                continue
            _stair(w, f, i, d, top + 1, pal["stair"], _face_in(f, i, d, 2, 4, 2, 4))
    w.put(*f.at(3, 3, top + 1), pal["trim"])
    w.put(*f.at(3, 3, top + 2), pal["accent"])
    w.put(*f.at(3, 3, top + 3), "end_rod", facing="up")
    return top + 3


def _fig_robed(w, f, pal, base):
    """A robed standing figure: a flared hem, a mantled torso, planar arms, a neck and a head.

    PLANAR AND COLUMNAR, never volumetric. This repo cannot build compound muscle and has the
    panel verdicts to prove it - a robe is a cone and a pair of arms is a flat bar, and both of
    those are shapes voxels give away free.
    """
    for h in (base, base + 1, base + 2):                # the hem
        for i in range(2, 5):
            for d in range(2, 5):
                w.put(*f.at(i, d, h), pal["wall"])
    for i in range(1, 6):                               # the skirt flare
        for d in range(1, 6):
            if i in (1, 5) or d in (1, 5):
                _stair(w, f, i, d, base, pal["stair"], _face_in(f, i, d, 1, 5, 1, 5))
    for h in range(base + 3, base + 8):                 # the torso, mantled at the front
        for i in range(2, 5):
            for d in (2, 3):
                w.put(*f.at(i, d, h), pal["accent"] if d == 2 else pal["wall"])
    for h in (base + 5, base + 6):                      # the arms: a planar bar
        for i in (1, 5):
            w.put(*f.at(i, 3, h), pal["wall"])
    w.put(*f.at(3, 3, base + 8), pal["trim"])           # the neck
    for h in (base + 9, base + 10):                     # the head
        for i in range(2, 5):
            for d in range(2, 5):
                w.put(*f.at(i, d, h), pal["wall"] if h == base + 9 else pal["trim"])
    for i, d in ((3, 3), (2, 3), (4, 3), (3, 2), (3, 4)):
        w.put(*f.at(i, d, base + 11), pal["accent"])    # a halo, in the land's accent
    return base + 11


def _fig_emblem(w, f, pal, base):
    """A column with a corbelled capital carrying a PLANAR emblem, edge-on to the street."""
    top = base + 8
    for h in range(base, top + 1):
        for i in range(2, 5):
            for d in range(2, 5):
                corner = i in (2, 4) and d in (2, 4)
                w.put(*f.at(i, d, h), pal["trim"] if corner else pal["wall"])
    _plane(w, f, 2, 4, 2, 4, top + 1, pal["trim"])      # the capital's core, over the shaft
    for i in range(1, 6):                               # the capital
        for d in range(1, 6):
            if i in (1, 5) or d in (1, 5):
                _stair(w, f, i, d, top + 1, pal["stair"], _face_in(f, i, d, 1, 5, 1, 5),
                       half="top")
    _plane(w, f, 1, 5, 1, 5, top + 2, pal["trim"])      # the abacus
    cy = top + 5                                        # the emblem's centre
    for di in range(-2, 3):
        for dh in range(-2, 3):
            r = di * di + dh * dh
            if r > 4:
                continue
            blk = pal["accent"] if r <= 1 else pal["trim"]
            w.put(*f.at(3 + di, 3, cy + dh), blk)
    # THREE RAYS, NOT FOUR. There is no downward ray: the cell under the disc is the abacus the
    # emblem stands on, so a fourth ray would be placed into the capital and never seen.
    for di, dh in ((-3, 0), (3, 0), (0, 3)):
        w.put(*f.at(3 + di, 3, cy + dh), pal["accent"])
    return cy + 3


_FIGURES = {"obelisk": _fig_obelisk, "robed": _fig_robed, "emblem": _fig_emblem}


def _statue(w: World, p: dict, ctx) -> dict:
    """A plinth and a figure - never under fourteen courses, because below that the plinth eats
    the figure and the whole thing reads as a bollard."""
    f = _Frame(p)
    pal = LANDS[p["land"]]
    say = _Plaques(p.get("sign", True))
    seed = int(p["seed"]) + f.x * 17 + f.z * 3
    which = p.get("figure") or sorted(_FIGURES)[int(hash01(seed, 11) * len(_FIGURES)) % 3]
    if which not in _FIGURES:
        raise ValueError(f"unknown statue figure {which!r}; have {sorted(_FIGURES)}")
    title = str(p.get("title") or "THE FOUNDER").upper()

    base = _plinth(w, f, pal, say, p, title)
    top = _FIGURES[which](w, f, pal, base)

    # LIGHT AT THE FOOT, not on the figure. A lamp set into a sculpture is a hole in it - the
    # island night pass's own rule, and the reason its cost model makes a coat dear and ordinary
    # ground cheap.
    for (i, d) in ((-1, -1), (7, -1), (-1, 7), (7, 7)):
        _lamp_post(w, f, pal, i, d, 0, 2)

    assert top + 1 >= 14, f"statue is {top + 1} tall, under the fourteen-course floor"
    return {"kind": "statue", "figure": which, "height": top + 1, "plinth": 7,
            "signs": say.want, "signs_placed": say.got,
            "contract": "a moulded plinth carrying a columnar or planar figure at least fourteen "
                        "courses tall, with its inscription on the plinth's own front face"}


# ------------------------------------------------------------------ the shop street

def _deal(options, n, seed, salt):
    """Deal n values so EVERY option is used before any is used twice, then shuffle.

    A hash per shop per property is uniform over many streets and lopsided over one, which is the
    only sample size that exists: the first eight-shop terrace built came out with six one-storey
    shops, three of the four roofs, and not a single jetty - varied on paper and a row of the same
    building to look at. Dealing guarantees the coverage; the shuffle stops it reading as a
    repeating period-four pattern. Deterministic Fisher-Yates over `hash01`, never `random`.
    """
    out = [options[i % len(options)] for i in range(n)]
    for i in range(n - 1, 0, -1):
        j = int(hash01(seed, salt, i) * (i + 1)) % (i + 1)
        out[i], out[j] = out[j], out[i]
    return out


def _shop_specs(n, seed, land):
    """Everything about every shop in the terrace, dealt so no two are the same building.

    Width, storeys, roof, awning, jetty, door position, window pattern, field material, accent
    and trade all move independently, so a stranger can tell any two shops apart at a glance -
    which is the single thing the rejected version could not do.
    """
    width = _deal([5, 6, 7, 8, 9, 10, 11], n, seed, 1)
    storey = _deal([2, 1], n, seed, 2)
    roof = _deal(["gable", "hip", "flat", "crowstep"], n, seed, 3)
    door = _deal(["left", "centre", "right"], n, seed, 4)
    windows = _deal(["wide", "pair", "grid"], n, seed, 5)
    field = _deal(_FIELDS[land], n, seed, 6)
    accent = _deal(_ACCENTS, n, seed, 7)
    trade = _deal(_TRADES, n, seed, 8)
    # A JETTY IS A TWO-STOREY FEATURE, so it is dealt only among the shops that have an upper
    # floor - dealt over the whole row it lands on bungalows and does nothing.
    ups = [k for k in range(n) if storey[k] == 2]
    jet = dict(zip(ups, _deal([True, False], len(ups), seed, 9)))
    awn = _deal(["canopy", "eave", "none"], n, seed, 10)
    out = []
    for k in range(n):
        jetty = jet.get(k, False)
        out.append(dict(width=width[k], storeys=storey[k], roof=roof[k], jetty=jetty,
                        awning="none" if jetty else awn[k], door=door[k], windows=windows[k],
                        field=field[k], accent=accent[k], trade=trade[k],
                        shutters=hash01(seed, 11, k) < 0.5))
    return out


_GND_H = 5          # ground-storey wall courses: h=0..4
_BAND = 5           # the fascia / floor band between storeys
_UP_H = 4           # upper-storey wall courses


def _one_shop(w, f, pal, say, s, i0, depth, min_run):
    """Build one shop of the terrace. Party walls are SHARED: shop k+1 starts at shop k's right
    wall column, so the row is a terrace rather than a line of detached sheds with slots between
    them - and a slot you can walk into but not through is the worst thing on a street."""
    i1 = i0 + s["width"] - 1
    db = depth - 1
    field, accent = s["field"], s["accent"]

    # ---- openings, decided BEFORE the wall goes up
    if s["door"] == "left":
        door = (i0 + 1, i0 + 2)
    elif s["door"] == "right":
        door = (i1 - 2, i1 - 1)
    else:
        mid = (i0 + i1) // 2
        door = (mid, mid + 1) if s["width"] % 2 == 0 else (mid - 1, mid)
    door = tuple(i for i in door if i0 < i < i1)

    free = [i for i in range(i0 + 1, i1) if i not in door]
    if s["windows"] == "wide":
        win = [i for i in free if i0 + 1 <= i <= i1 - 1]
    elif s["windows"] == "pair":
        win = free[:1] + free[-1:] if len(free) >= 2 else free
    else:
        win = free[::2]
    win = [i for i in win if i not in door]

    holes = [(i, 0, h) for i in door for h in (0, 1, 2)]
    holes += [(i, 0, h) for i in win for h in (1, 2)]
    _box(w, f, i0, i1, 0, db, 0, _GND_H - 1, field, corner=pal["post"], holes=holes)

    # ---- the floor, and the ceiling course that doubles as the fascia band
    _plane(w, f, i0, i1, 0, db, -1, pal["ground"])
    _plane(w, f, i0, i1, 0, db, _BAND, pal["trim"])

    # ---- glazing. Panes are connected ALONG the wall; with every side false a pane renders as a
    # lone post rather than as a window.
    pane = _pane_props(f, along_i=True)
    for i in win:
        for h in (1, 2):
            w.put(*f.at(i, 0, h), "glass_pane", **pane)
    if s["shutters"]:
        # OPEN TRAPDOORS, NOT A PAINTED WOOL SQUARE - the vertical panel Minecraft never shipped
        # as a block, and the corpus measurement that says so: outside builders place trapdoors
        # at 1.07 per thousand cells against our 0.00. Mounted one cell PROUD of the wall, beside
        # the window, matching `hollowmanor._facade`'s own shutter idiom - not flush with the
        # wall plane, which is what the wool version did and why it read as a coloured square
        # rather than as a shutter swung open.
        wood = pal["wood"]
        for i in win:
            for j in (i - 1, i + 1):
                if i0 < j < i1 and j not in win and j not in door:
                    for h in (1, 2):
                        w.put(*f.at(j, -1, h), f"{wood}_trapdoor", facing=f.facing,
                              half="bottom", open="true", powered="false", waterlogged="false")

    # ---- the interior: a counter along the back and a light under the ceiling
    for i in range(i0 + 1, i1):
        w.put(*f.at(i, db - 1, 0), pal["trim"])
        _slab(w, f, i, db - 1, 1, pal["slab"], "top")
    _hang_light(w, f, pal, (i0 + i1) // 2, max(1, db // 2), _BAND - 1)

    # ---- the awning, one course under the fascia so the nameplate above it stays clear
    if s["awning"] == "canopy":
        for i in range(i0, i1 + 1):
            for d in (-1, -2):
                w.put(*f.at(i, d, _GND_H - 1), accent if (i + d) % 2 == 0 else pal["wall"])
    elif s["awning"] == "eave":
        cells = [(i, -1, _LEAN[f.facing]) for i in range(i0, i1 + 1)]
        _trim_run(w, f, pal, cells, _GND_H - 1, min_run, half="top")

    # ---- the upper storey, jettied or flush
    df = 0
    if s["storeys"] == 2:
        if s["jetty"]:
            df = -1
            for i in range(i0, i1 + 1):                 # the jetty band, and its brackets
                w.put(*f.at(i, -1, _BAND), pal["trim"])
            cells = [(i, -1, _LEAN[f.facing]) for i in range(i0, i1 + 1)]
            _trim_run(w, f, pal, cells, _BAND - 1, min_run, half="top")
        upw = [i for i in range(i0 + 1, i1) if (i - i0) % 2 == 1]
        uh = [(i, df, h) for i in upw for h in (_BAND + 2, _BAND + 3)]
        _box(w, f, i0, i1, df, db, _BAND + 1, _BAND + _UP_H, field, corner=pal["post"], holes=uh)
        for i in upw:
            for h in (_BAND + 2, _BAND + 3):
                w.put(*f.at(i, df, h), "glass_pane", **pane)
        _plane(w, f, i0, i1, df, db, _BAND + _UP_H + 1, pal["trim"])
        rh = _BAND + _UP_H + 2
    else:
        rh = _BAND + 1

    # ---- the roof
    if s["roof"] == "gable":
        top = _roof_gable(w, f, pal, i0, i1, df, db, rh, field, pal["trim"])
    elif s["roof"] == "hip":
        top = _roof_hip(w, f, pal, i0, i1, df, db, rh, field, pal["trim"])
    elif s["roof"] == "flat":
        top = _roof_flat(w, f, pal, i0, i1, df, db, rh, field, pal["trim"],
                         cren=(s["width"] % 2 == 1))
    else:
        top = _roof_crowstep(w, f, pal, i0, i1, df, db, rh, field, pal["trim"])
    if s["roof"] in ("gable", "hip"):
        # NO FLANKS ON A TERRACE: `i1` is the next shop's `i0`, so a flank eave at `i1 + 1` is a
        # stair driven a course into the neighbour's wall.
        _eave(w, f, pal, i0, i1, df, db, rh - 1, min_run, front=False, sides=False)

    # ---- the nameplate. On a jettied shop the fascia has moved forward with the storey above it,
    # so the sign moves with it - a sign at a fixed offset would be hung on air.
    name, tag = s["trade"]
    say(w, f, pal, (i0 + i1) // 2, df - 1, _BAND, f.facing, [name[:SIGN_WIDTH], tag[:SIGN_WIDTH]])
    return {"i0": i0, "i1": i1, "top": top, "door": door, "windows": win, **s}


def _shopstreet(w: World, p: dict, ctx) -> dict:
    """A TERRACE OF SHOPS SHARING ONE FRONTAGE, and a pavement in front of it.

    The previous entrance zone's shops were identical 9x7 huts, and a row of identical huts is
    storage. Everything about a shop here is drawn from a hash of its index, so the terrace has a
    skyline: widths from five to eleven, one storey or two, four roofs, three awnings, jetties on
    some, and four field materials against eight accents.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    say = _Plaques(p.get("sign", True))
    # A FLOOR OF 6 WAS RIGHT WHEN THE STREET WAS THE CENTRE, AND IS WRONG NOW. It existed because
    # this kind's whole point is a VARIED TERRACE and a terrace of two is not a terrace. But Jack
    # rejected a centre that was "just a bunch of shops" and asked for "maybe 2" beside a grand
    # monument, so two shops is the brief rather than a degenerate case. The per-shop variation
    # still applies - two shops must still be visibly different buildings.
    n = max(2, int(p["shops"]))
    depth = max(6, int(p["shop_depth"]))
    seed = int(p["seed"]) + f.x * 131 + f.z * 7
    min_run = int(p["min_run"])

    specs = _shop_specs(n, seed, p["land"])
    starts, i = [], 0
    for s in specs:
        starts.append(i)
        i += s["width"] - 1                      # party walls are shared
    frontage = i + 1

    # ---- the pavement, the kerb and the road. Laid FIRST so every shop's own floor sits into it
    # and the whole street is one surface.
    pave = 0
    for i in range(-2, frontage + 2):
        for d in range(-6, depth + 2):
            x, y, z = f.at(i, d, -1)
            if d == -6:
                blk = pal["trim"]                # the kerb
            elif d < -5:
                blk = pal["path"]
            elif d < 0:
                blk = pal["ground"] if (x + z) % 2 == 0 else pal["path"]
            else:
                blk = pal["ground"]
            w.put(x, y, z, blk)
            pave += 1

    built = [_one_shop(w, f, pal, say, s, st, depth, min_run) for s, st in zip(specs, starts)]

    # ---- street furniture on the kerb. Lamps on a rhythm, benches between them, and never at a
    # spacing that turns the kerb into a fence.
    lamps, benches, first_post = 0, 0, None
    for i in range(3, frontage - 2, 11):
        _lamp_post(w, f, pal, i, -5, 0, 3)
        lamps += 1
        first_post = first_post if first_post is not None else i
    for i in range(8, frontage - 4, 11):
        for j in range(i, min(i + 3, frontage - 1)):
            _stair(w, f, j, -4, 0, pal["stair"], f.back)
        benches += 1

    # THE STREET SIGN HANGS ON A LAMP POST, because nothing else on a pavement is solid at head
    # height. Hung in open air over the kerb it placed nothing and said nothing about it.
    title = str(p.get("title") or "MARKET ROW").upper()
    if first_post is not None:
        say(w, f, pal, first_post, -6, 2, f.facing,
            [title[:SIGN_WIDTH], "", f"{n} shops", "mind the step"])

    return {"kind": "shopstreet", "shops": n, "frontage": frontage, "depth": depth,
            "pavement": pave, "lamps": lamps, "benches": benches,
            "roofs": sorted({s["roof"] for s in specs}),
            "widths": [s["width"] for s in specs],
            "signs": say.want, "signs_placed": say.got,
            "contract": "at least six shops on one shared frontage, no two of them the same "
                        "building: width, storeys, roof, awning, jetty, door, windows, field "
                        "material and accent all vary by a hash of the shop's index"}


# ------------------------------------------------------------------ the bandstand

def _bandstand(w: World, p: dict, ctx) -> dict:
    """An open pavilion on a stepped base: columns, a balustrade, a stepped roof and a finial.

    OPEN, which is what separates a bandstand from a shed. The balustrade is wall-plus-slab at a
    block and a half so you can see the band over it, the columns carry the roof with nothing
    between them above waist height, and the entrance is a gap the ring loop LEAVES rather than
    a hole cut into a finished ring.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    say = _Plaques(p.get("sign", True))
    rd = max(5, int(p["radius"]) - 3)
    seed = int(p["seed"]) + f.x * 53 + f.z * 11
    plan = p.get("plan") or ("square" if hash01(seed, 3) < 0.35 else "octagon")
    if plan not in ("square", "octagon"):
        raise ValueError(f"unknown bandstand plan {plan!r}; have ['octagon', 'square']")
    sq = plan == "square"
    steep = hash01(seed, 5) < 0.5                # the roof profile: one course per inset, or two
    rail = _BALUSTRADE.get(pal["ground"], "stone_brick_wall")
    c = rd + 3

    def cell(di, dd, r):
        return _oct(di, dd, r, sq)

    # ---- the pad, the podium and the deck, with a stair tread on each step
    for (di, dd) in _cells(c, rd + 3, cell):
        x, y, z = f.at(c + di, c + dd, -1)
        w.put(x, y, z, pal["ground"] if (x + z) % 2 == 0 else pal["path"])
    for (di, dd) in _cells(c, rd + 1, cell):
        w.put(*f.at(c + di, c + dd, 0), pal["ground"])
    step0 = set(_cells(c, rd + 2, cell)) - set(_cells(c, rd + 1, cell))
    for (di, dd) in sorted(step0):
        _stair(w, f, c + di, c + dd, 0, pal["stair"], _BACK[_face_out_radial(f, di, dd)])
    for (di, dd) in _cells(c, rd, cell):
        x, y, z = f.at(c + di, c + dd, 1)
        w.put(x, y, z, pal["accent"] if max(abs(di), abs(dd)) == rd - 1
              else (pal["ground"] if (x + z) % 2 == 0 else pal["path"]))
    step1 = set(_cells(c, rd + 1, cell)) - set(_cells(c, rd, cell))
    for (di, dd) in sorted(step1):
        _stair(w, f, c + di, c + dd, 1, pal["stair"], _BACK[_face_out_radial(f, di, dd)])

    # ---- columns at the plan's own corners, so eight of them land symmetrically.
    #
    # `lim` IS THE OTHER COORDINATE OF THOSE EIGHT POINTS, AND FOR A SQUARE IT MUST NOT BE `rd`.
    # An octagon's edge midline sits at `int(rd*1.5) - rd`, so the two sets {(+-rd, +-lim)} and
    # {(+-lim, +-rd)} are distinct and the pavilion gets eight posts. Written `lim = rd` for the
    # square the two sets COLLAPSE ONTO THE SAME FOUR CORNERS - a set literal silently de-duplicates
    # them - so every square bandstand shipped with four posts under a contract that says eight,
    # and the only number that would have told you was `columns` in its own sidecar.
    #
    # The inset is two rather than the mid-edge, because a post at the mid-edge of the FRONT lands
    # at di=0, which is the middle of the entrance gap the balustrade loop leaves open: eight
    # columns and no way in. `rd >= 5` by construction, so the inset is always at least 3.
    lim = rd - 2 if sq else int(rd * 1.5) - rd
    corners = sorted({(sx * rd, sz * lim) for sx in (1, -1) for sz in (1, -1)} |
                     {(sx * lim, sz * rd) for sx in (1, -1) for sz in (1, -1)})
    for (di, dd) in corners:
        for h in range(2, 7):
            w.put(*f.at(c + di, c + dd, h), pal["post"])

    # ---- the balustrade, with the front face LEFT OPEN as the way in
    edge = [t for t in _border(rd, cell) if t not in corners]
    gap = {t for t in edge if t[1] <= -rd + 1 and abs(t[0]) <= 1}
    rails = 0
    for (di, dd) in edge:
        if (di, dd) in gap:
            continue
        w.put(*f.at(c + di, c + dd, 2), rail)
        _slab(w, f, c + di, c + dd, 3, pal["slab"], "bottom")
        rails += 1

    # ---- the entablature and its overhanging eave
    for (di, dd) in _border(rd, cell):
        w.put(*f.at(c + di, c + dd, 7), pal["trim"])
    for (di, dd) in set(_cells(c, rd + 1, cell)) - set(_cells(c, rd, cell)):
        _stair(w, f, c + di, c + dd, 7, pal["stair"],
               _face_out_radial(f, -di, -dd), half="top")

    # ---- the roof: a stepped cone. Each ring carries a RISER down to the level of the ring
    # outside it, and that riser is the whole reason the roof is one piece: ring L's stairs and
    # ring L-1's stairs meet only DIAGONALLY, and six-connectivity does not see a diagonal. Built
    # without it the roof shipped as four floating rings - and at two courses per inset one
    # course of sarking was still not enough, which is why the fill is a range and not a cell.
    lv, r, top, prev = 8, rd, 8, 8
    first = True
    while r >= 2:
        for (di, dd) in _border(r, cell):
            if not first:
                for hh in range(prev, lv):
                    w.put(*f.at(c + di, c + dd, hh), pal["trim"])
            _stair(w, f, c + di, c + dd, lv, pal["stair"],
                   _BACK[_face_out_radial(f, di, dd)])
        top, prev, first = lv, lv, False
        r -= 1
        lv += 1 if steep else 2
    # A BELL UNDER THE APEX, hung BEFORE the apex is filled so the fill becomes its ceiling:
    # `attachment=ceiling` wants a full block directly above it.
    w.put(*f.at(c, c, prev - 1), "bell", facing=f.facing, attachment="ceiling", powered="false")
    for (di, dd) in _cells(c, 1, _disc):
        for hh in range(prev, lv + 1):
            w.put(*f.at(c + di, c + dd, hh), pal["trim"])
    top = lv

    # A SECOND BELL AT THE ENTRANCE, on the post you pass closest to walking in - NOTHING TO
    # WIRE. A bell rings on a right-click (or an attack) whatever powers it, unlike a note block,
    # which is `expensive` tier here (`palette.tier("note_block") == "expensive"`) and would be
    # the wrong material to reach for on this economy even before asking whether it is wired. Two
    # bells at two heights is a small carillon a visitor can actually play walking in.
    gate_post = min(corners, key=lambda t: (t[1], t[0]))
    w.put(*f.at(c + gate_post[0], c + gate_post[1] + 1, 3), "bell",
          facing=f.back, attachment="single_wall", powered="false")
    w.put(*f.at(c, c, top + 1), pal["accent"])
    w.put(*f.at(c, c, top + 2), "end_rod", facing="up")

    # ---- light hanging from the entablature at the four cardinal points, never from a column
    lamps = 0
    for (ux, uz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for t in range(rd, 0, -1):
            di, dd = ux * t, uz * t
            if (di, dd) in edge:
                _hang_light(w, f, pal, c + di, c + dd, 6)
                lamps += 1
                break

    title = str(p.get("title") or "BANDSTAND").upper()
    front = min(corners, key=lambda t: (t[1], t[0]))
    say(w, f, pal, c + front[0], c + front[1] - 1, 4, f.facing,
        [title[:SIGN_WIDTH], "", "band plays", "on the hour"])

    # THE CONTRACT SAYS EIGHT COLUMNS, SO EIGHT IS ASSERTED - the statue's own fourteen-course
    # floor, one kind over. `corners` is built from a set literal, so a `lim` that collides with
    # `rd` halves it in silence and the only witness is a number in the sidecar nobody reads.
    assert len(corners) == 8, f"{plan} bandstand has {len(corners)} columns, not eight"

    return {"kind": "bandstand", "plan": plan, "radius": rd, "height": top + 2,
            "columns": len(corners), "rails": rails, "lanterns": lamps, "steep": steep,
            "bells": 2, "signs": say.want, "signs_placed": say.got,
            "contract": "an open pavilion: a stepped base you climb, eight columns, a "
                        "waist-height balustrade with the front left open, a stepped roof with "
                        "a bell under its apex, and a second bell at the entrance - both playable "
                        "with a right-click, nothing wired"}


# ------------------------------------------------------------------ guest services

def _clock(w, f, pal, ci, d, base, pale, dark):
    """A five by five clock, read from the forecourt. The bezel is the outer octagon of the
    square, the face is the inner three, and the hands are two cells - at this size a third hand
    is a smudge."""
    n = 0
    for di in range(-2, 3):
        for dh in range(-2, 3):
            if abs(di) + abs(dh) > 3:
                continue
            bezel = max(abs(di), abs(dh)) == 2 or abs(di) + abs(dh) == 3
            w.put(*f.at(ci + di, d, base + dh), dark if bezel else pale)
            n += 1
    for di, dh in ((0, 0), (0, 1), (1, 0)):
        w.put(*f.at(ci + di, d, base + dh), dark)
    return n


def _guestservices(w: World, p: dict, ctx) -> dict:
    """A small civic building: a counter window onto the forecourt, a clock bay, and signage.

    The counter is the point of it. A civic building with a door and no window is an office; the
    serving hatch, its sill and the queue rail in front of it are what say GUEST SERVICES without
    the sign having to.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    say = _Plaques(p.get("sign", True))
    # THREE LINES ARE READ BY INDEX, SO THREE MUST EXIST. `lines` is a caller-supplied list and
    # `params: {lines: ["ask here"]}` is a perfectly reasonable thing to write - it raised
    # IndexError out of the middle of the build, which is the one failure mode a generator must
    # not have: a config that is legal to write must never crash the pipeline. Padded from the
    # default rather than truncated, so a short list adds a line instead of losing the sign.
    _DEFAULT_LINES = ["lost property", "first aid", "ask here"]
    say_lines = list(p.get("lines") or _DEFAULT_LINES)
    say_lines += _DEFAULT_LINES[len(say_lines):]
    width = max(13, int(p["width"]) | 1)
    depth = max(7, int(p["depth"]))
    db = depth - 1
    cx = width // 2
    seed = int(p["seed"]) + f.x * 29 + f.z * 5
    crown = p.get("crown") or ("emblem" if hash01(seed, 2) < 0.4 else "clock")
    if crown not in ("clock", "emblem"):
        raise ValueError(f"unknown guestservices crown {crown!r}; have ['clock', 'emblem']")
    hipped = hash01(seed, 4) < 0.45
    pale = "white_wool" if pal["wall"] != "white_wool" else "light_gray_wool"

    # ---- pad and forecourt
    for i in range(-3, width + 3):
        for d in range(-6, depth + 2):
            x, y, z = f.at(i, d, -1)
            if d < 0:
                blk = pal["trim"] if d == -6 else (pal["ground"] if (x + z) % 2 == 0
                                                   else pal["path"])
            else:
                blk = pal["ground"]
            w.put(x, y, z, blk)

    # ---- the openings, decided before the wall goes up
    entry = (2, 3)
    hatch = tuple(range(cx - 2, cx + 3))
    side_win = (2, depth - 3)
    holes = [(i, 0, h) for i in entry for h in (0, 1, 2)]
    holes += [(i, 0, h) for i in hatch for h in (1, 2, 3)]
    holes += [(i, d, h) for i in (0, width - 1) for d in side_win for h in (2, 3)]
    _box(w, f, 0, width - 1, 0, db, 0, 5, pal["wall"], corner=pal["post"], holes=holes)

    # ---- the counter: a sill of top slabs across the hatch, and a shelf on the outside
    for i in hatch:
        _slab(w, f, i, 0, 1, pal["slab"], "top")
        _slab(w, f, i, -1, 0, pal["slab"], "top")
    # a queue rail two cells out, so the forecourt has a direction
    rail = _BALUSTRADE.get(pal["ground"], "stone_brick_wall")
    for i in range(cx - 3, cx + 4):
        if i in (cx - 3, cx + 3):
            w.put(*f.at(i, -3, 0), rail)
    for d in (-3, -4):
        w.put(*f.at(cx - 3, d, 0), rail)
        w.put(*f.at(cx + 3, d, 0), rail)

    pane = _pane_props(f, along_i=False)
    for i in (0, width - 1):
        for d in side_win:
            for h in (2, 3):
                w.put(*f.at(i, d, h), "glass_pane", **pane)

    # ---- interior: floor band, counter, benches and light
    _plane(w, f, 0, width - 1, 0, db, -1, pal["ground"])
    for i in hatch:
        w.put(*f.at(i, 1, 0), pal["trim"])
        _slab(w, f, i, 1, 1, pal["slab"], "top")
    # BENCHES OF THREE, not single stairs spaced out along the wall. One stair on its own is the
    # confetti the deck soffit's run gate exists to stop; three in a row is a bench.
    for i in range(2, width - 4, 5):
        for j in range(i, min(i + 3, width - 2)):
            _stair(w, f, j, db - 1, 0, pal["stair"], f.facing)
    _hang_light(w, f, pal, cx, db - 2, 4)
    _hang_light(w, f, pal, 3, db - 2, 4)

    # LOST PROPERTY: two barrels, freestanding on the RIGHT flank, clear of the hatch queue and
    # clear of the benches - rule 10, ~3 blocks of working room around anything you use, applied
    # here rather than derived from a capture because this room has no capture to derive it from.
    # Barrels answer `_DEFAULT_LINES[0]` ("lost property") with an actual container rather than
    # only a word on a sign - the difference between a real building and a coloured box.
    lock_i = (width - 4, width - 3)
    for i in lock_i:
        w.put(*f.at(i, 3, 0), "barrel", facing="up", open="false")
    # THE SIGN'S SUPPORT IS HORIZONTAL, AT THE SIGN'S OWN HEIGHT - `park._sign` checks the cell
    # one step behind it at the SAME h, so the sign sits at h=0, level with the barrel it is
    # mounted against, not floating a course above it looking for a wall that is not there.
    say(w, f, pal, lock_i[0], 2, 0, f.facing, ["LOST PROPERTY", "hand it in", "or check here", ""])

    # ---- cornice, ceiling, and the main roof
    _plane(w, f, 0, width - 1, 0, db, 6, pal["trim"])
    _eave(w, f, pal, 0, width - 1, 0, db, 6, int(p["min_run"]))
    if hipped:
        top_main = _roof_hip(w, f, pal, 0, width - 1, 0, db, 7, pal["wall"], pal["trim"])
    else:
        top_main = _roof_flat(w, f, pal, 0, width - 1, 0, db, 7, pal["wall"], pal["trim"])
        for i in (0, width - 1):                # a standing lamp on each parapet corner
            for d in (0, db):
                w.put(*f.at(i, d, 9), pal["light"], hanging="false", waterlogged="false")

    # ---- the crown bay: a raised centre carrying the clock or the emblem.
    #
    # IT IS SOLID FROM THE CORNICE UP, and that is structural, not stylistic. Seated on the roof
    # it stood on whatever the roof happened to leave under it - and a hipped roof over a deep
    # plan draws its rings in from BOTH axes, so at depth 10 the ridge had retreated past the
    # bay's own footprint and the whole tower, clock and finial shipped as a hundred and
    # fifty-seven cells floating over the building. A tower rises THROUGH a roof.
    b0, b1 = cx - 3, cx + 3
    bd = min(2, db)
    base = top_main + 1
    for h in range(7, base):
        _plane(w, f, b0, b1, 0, bd, h, pal["wall"])
    _plane(w, f, b0, b1, 0, bd, base - 1, pal["trim"])
    _box(w, f, b0, b1, 0, bd, base, base + 6, pal["wall"], corner=pal["post"],
         holes=[(i, 0, h) for i in range(b0 + 1, b1) for h in range(base + 1, base + 6)])
    dial = base + 3
    if crown == "clock":
        _clock(w, f, pal, cx, 0, dial, pale, pal["trim"])
    else:
        for di in range(-2, 3):                 # a rayed emblem, the same size as the dial
            for dh in range(-2, 3):
                r = di * di + dh * dh
                if r > 4:
                    continue
                w.put(*f.at(cx + di, 0, dial + dh), pal["accent"] if r <= 1 else pale)
        for di, dh in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
            w.put(*f.at(cx + di, 0, dial + dh), pal["trim"])
    # THE ART IS SET INTO A WALL, so whatever it does not cover is wall and not a hole. Both the
    # dial and the emblem are round and the opening is square, so four corners were coming out as
    # little square windows through the tower - and a hole nobody meant is read as damage.
    for di in range(-2, 3):
        for dh in range(-2, 3):
            _put_free(w, f, cx + di, 0, dial + dh, pal["wall"])
    top = _roof_hip(w, f, pal, b0, b1, 0, bd, base + 7, pal["wall"], pal["trim"])
    w.put(*f.at(cx, min(1, bd), top + 1), pal["accent"])
    w.put(*f.at(cx, min(1, bd), top + 2), "end_rod", facing="up")

    # ---- signage. The nameplate over the hatch, the services beside the door, and a notice
    # inside on the back wall for whoever has come in.
    #
    # THE FLANKING SIGNS ARE PUT ON COLUMNS THAT ARE DERIVED, NOT CHOSEN. At the minimum width of
    # thirteen the hatch reaches i=4, which is exactly where a hand-picked second sign went - and
    # the hatch is an OPENING for three courses, so it hung on nothing and `park._sign` silently
    # placed it nowhere. The wall exists everywhere except the columns somebody signed.
    title = str(p.get("title") or "GUEST SERVICES").upper()
    flank = [i for i in range(1, width - 1) if i not in entry and i not in hatch]
    say(w, f, pal, cx, -1, 4, f.facing, [title[:SIGN_WIDTH], "", "open all day", ""])
    if flank:
        say(w, f, pal, flank[0], -1, 3, f.facing,
            ["INFORMATION", str(say_lines[0])[:SIGN_WIDTH]])
    if len(flank) > 1:
        say(w, f, pal, flank[-1], -1, 3, f.facing,
            [str(say_lines[1])[:SIGN_WIDTH], str(say_lines[2])[:SIGN_WIDTH]])
    say(w, f, pal, cx, db - 1, 3, f.facing, ["NOTICES", "band at three", "fireworks nine", ""])

    for (i, d) in ((-2, -2), (width + 1, -2)):
        _lamp_post(w, f, pal, i, d, 0, 3)

    return {"kind": "guestservices", "width": width, "depth": depth, "crown": crown,
            "hipped": hipped, "height": top + 2, "lockers": 2,
            "signs": say.want, "signs_placed": say.got,
            "contract": "a counter window with a sill and a queue rail onto the forecourt, a "
                        "raised bay carrying a clock or an emblem, two lost-property barrels "
                        "with room to stand in front of them, and five signs that each hang on a "
                        "wall that is actually there"}


BUILDERS = {
    "fountain": _fountain,
    "statue": _statue,
    "shopstreet": _shopstreet,
    "bandstand": _bandstand,
    "guestservices": _guestservices,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**CIVIC, **cfg}
    if not p.get("at"):
        raise ValueError("civic needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown civic kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    return w.canvas({
        "kind": f"civic/{p['kind']}",
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
