"""THE LEFT ZONE: a western mining town - spruce, cobble and stone, on a plot that is VOID.

**WHY A TOWN AND NOT A ROW OF HUTS.** The previous attempt at this zone was rejected as *"single
small structures... some infrastructure and some huts"*, and the diagnosis is the one this repo
has written down three times already in three different places - the void tower's jagged stub
(*"a tossed grouping of vague blocks"*), the deck soffit's 184 one-cell grid runs, and the
casino's eighteen sealed grey cubes:

    WHAT MAKES VOXELS READ AS ARCHITECTURE IS REGULARITY AND OPENINGS, NOT DAMAGE -
    AND WHAT MAKES A TOWN IS THAT NO TWO BUILDINGS ARE THE SAME BUILDING.

So every kind here carries a SILHOUETTE that nothing else in the park has: a false front (a
parapet standing above its own roof, which is the one detail that says *western* and nothing
else), a tank on legs, four sails, an A-frame headframe, a row of shopfronts of four different
widths, a trestle on braced bents. Variety inside a kind comes from `canvas.hash01` of the cell
or the index - deterministic, reproducible, and never `random`, because a design that regenerates
differently cannot be diffed against the world it is half-built into.

**THE PALETTE IS THE LAND'S, MEASURED BEFORE IT WAS WRITTEN DOWN.** Colours come from
`park.LANDS[land]`; the few extras this file needs are in `EXTRA` below and every one of them was
checked against `blocks.spendable`, `blocks.available` and `palette.tier` - all cheap except
`andesite`, `polished_blackstone` and `cobbled_deepslate`, which are `ok` and are used as LINES
rather than as fields. Nothing here is dirt, grass, podzol or mud (all CURRENCY on this server),
nothing is sand, gravel or concrete powder (they fall, and this plot is air all the way down),
and nothing is quartz, concrete, terracotta, glass, sea lantern, glowstone, hay, note block or
redstone lamp (all expensive here). `glass_pane` is `ok` and is the one glazing this economy has.

**EVERY STRUCTURE CARRIES ITS OWN GROUND.** A skyblock plot is void: there is no terrain to stand
on, to dig into or to bury a footing in. So every kind lays its own pad at h=-1 first, and
anything raised - a tank, a deck, a headframe - reaches that pad with legs rather than hanging.

GEOMETRY, the same convention as `gen/park.py` and `casino._room`, stated once because a facing
bug is invisible in every render this repo can produce:

    at       the structure's FRONT-LEFT floor corner, in world coordinates
    facing   the direction the FRONT looks out
    i        runs along the frontage; d runs from the front INTO the build; h courses up
    at(i, d, h) = (x - dx*d + sx*i, y + h, z - dz*d + sz*i)

A wall sign hangs in the cell IN FRONT of its wall and its `facing` is the direction the TEXT
looks, away from the block holding it up - and the support is CHECKED, never assumed, because a
sign floating in air draws exactly like one on a wall and the game simply refuses to place it.

A STAIR'S TALL SIDE IS ITS `facing`. Our renderer draws a stair the same both ways round, so
every stair here is reasoned rather than eyeballed: a cornice tucked under a ceiling is
`half="top"` with its tall side into the wall, a roof eave is `half="bottom"` with its tall side
toward the building it grows out of.
"""
from __future__ import annotations

from .. import blocks
from .canvas import Canvas, hash01
from .park import LANDS, SIGN_WIDTH, _Frame, _STEP, _hang_light, _sign
from .vertical import Ctx, World

# The blocks this file needs that a LAND does not name. Every one checked with
# blocks.spendable() / blocks.available() / palette.tier() before it was written here.
EXTRA = {
    "frontier": {
        "rock": "cobblestone", "rock_stair": "cobblestone_stairs", "rock_slab": "cobblestone_slab",
        "aged": "mossy_cobblestone", "worn": "cracked_stone_bricks",
        "band": "stripped_spruce_log", "bark": "spruce_wood",
        "trap": "spruce_trapdoor", "door": "spruce_door",
    },
    "midway": {
        "rock": "stone", "rock_stair": "stone_stairs", "rock_slab": "stone_slab",
        "aged": "andesite", "worn": "cracked_stone_bricks",
        "band": "stripped_oak_log", "bark": "oak_wood",
        "trap": "oak_trapdoor", "door": "oak_door",
    },
    "hollow": {
        "rock": "blackstone", "rock_stair": "blackstone_stairs", "rock_slab": "blackstone_slab",
        "aged": "cobbled_deepslate", "worn": "polished_blackstone",
        "band": "stripped_dark_oak_log", "bark": "dark_oak_wood",
        "trap": "dark_oak_trapdoor", "door": "dark_oak_door",
    },
}

# THE FOUR FALSE-FRONT PROFILES. A false front is the whole point of a western street, and four
# identical ones are one false front drawn four times - which is the failure this zone was sent
# back for. The style is picked by a hash of the SHOP, so a row is varied and a regeneration is
# identical.
FRONTS = ("flat", "stepped", "triangular", "bracketed")

FRONTIER = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "saloon",
    "facing": "east",
    "land": "frontier",
    "title": None,
    "lines": None,
    "width": 17,
    "depth": 12,
    "height": None,             # watertower / windmill: overall reach, floored per kind
    "shops": 5,                 # falsefront: how many storefronts in the row
    "length": 24,               # trestlebridge: how far it spans
    "deck": 8,                  # trestlebridge: how high the deck rides over its own ground
    "min_run": 3,               # a trim course shorter than this is not drawn at all
    "sign": True,
}


# ------------------------------------------------------------------------------------ helpers

def _pal(p):
    return LANDS[p["land"]], EXTRA[p["land"]]


def _axis_dirs(f):
    """The two cardinal names of the frontage axis, as (+i, -i)."""
    if f.sx == 1:
        return "east", "west"
    if f.sx == -1:
        return "west", "east"
    if f.sz == 1:
        return "south", "north"
    return "north", "south"


def _log_axis(f, along):
    """A horizontal log must lie ALONG its run, or a belt course comes out as end grain."""
    if along == "i":
        return "x" if f.sx else "z"
    if along == "d":
        return "x" if f.dx else "z"
    return "y"


def _timber(w, f, i, d, h, name, axis="y"):
    """Place a post or beam that MAY carry an axis.

    A LAND'S `post` IS NOT ALWAYS A LOG. The Hollow's is `blackstone`, which has no `axis`
    property at all, so passing one is an illegal block state - and it is illegal on exactly one
    of the three lands, which is the shape of bug that ships green on the land you happened to
    test. The registry is asked rather than remembered.
    """
    w.put(*f.at(i, d, h), name, **({"axis": axis} if "axis" in blocks.props(name) else {}))


def _pane(w, f, i, d, h, along="i"):
    """Glazing. A PANE'S CONNECTIONS MUST BE SET ALONG ITS WALL - with every side false it renders
    as a lone post rather than as a window, which the campanile's slits already paid for."""
    pi, mi = _axis_dirs(f)
    props = {"north": "false", "south": "false", "east": "false", "west": "false",
             "waterlogged": "false"}
    if along == "i":
        props[pi] = props[mi] = "true"
    else:
        props[f.facing] = props[f.back] = "true"
    w.put(*f.at(i, d, h), "glass_pane", **props)


def _stair(w, f, i, d, h, name, facing, half="bottom"):
    w.put(*f.at(i, d, h), name, facing=facing, half=half, shape="straight", waterlogged="false")


def _slab(w, f, i, d, h, name, type_="bottom"):
    w.put(*f.at(i, d, h), name, type=type_, waterlogged="false")


def _pad(w, f, pal, i0, i1, d0, d1, block=None, h=-1):
    """The ground this structure stands on. THE PLOT IS VOID; nothing here has terrain to sit on."""
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            w.put(*f.at(i, d, h), block or pal["ground"])
            n += 1
    return n


def _run_i(w, f, name, i0, i1, d, h, facing, half, min_run):
    """A stair run ALONG the frontage at one depth, gated on length.

    RULE 9, AND THE DECK SOFFIT'S OWN LESSON: that pass drew a coffer grid per cell and produced
    215 runs of which 184 were one or two cells - confetti, in the loudest block available. A
    course shorter than `min_run` is not drawn at all.
    """
    if i1 - i0 + 1 < min_run:
        return 0
    for i in range(i0, i1 + 1):
        _stair(w, f, i, d, h, name, facing, half)
    return i1 - i0 + 1


def _run_d(w, f, name, i, d0, d1, h, facing, half, min_run):
    if d1 - d0 + 1 < min_run:
        return 0
    for d in range(d0, d1 + 1):
        _stair(w, f, i, d, h, name, facing, half)
    return d1 - d0 + 1


def _eaves(w, f, name, width, depth, h, min_run):
    """A ring of eave stairs one cell outside the wall, sloping down and OUTWARD.

    The tall side is toward the building - which is what makes it read as a roof edge rather than
    as a shelf - so `facing` is the inward direction on each side.
    """
    pi, mi = _axis_dirs(f)
    n = 0
    n += _run_i(w, f, name, -1, width, -1, h, f.back, "bottom", min_run)
    n += _run_i(w, f, name, -1, width, depth, h, f.facing, "bottom", min_run)
    n += _run_d(w, f, name, -1, -1, depth - 1, h, pi, "bottom", min_run)
    n += _run_d(w, f, name, width, -1, depth - 1, h, mi, "bottom", min_run)
    return n


def _brace(w, f, i0, d, h0, di, dh, n, name, facing):
    """A DIAGONAL TIMBER THAT IS ACTUALLY CONNECTED.

    A cell chain stepping one along and one up is DIAGONAL, and diagonal is not 6-connected - the
    ear tips broke off this way, the root braid shipped as 26 components, and a brace that reads
    perfectly in a render is a separate component in the audit. Each step therefore places two
    cells that share a face, and consecutive steps share a face with each other: a stair pair
    (bottom then top) reads as one continuous raking timber and is connected by construction.
    """
    cells = 0
    for k in range(n):
        i, h = i0 + di * k, h0 + dh * k
        _stair(w, f, i, d, h, name, facing, "bottom" if dh > 0 else "top")
        _stair(w, f, i, d, h + dh, name, facing, "top" if dh > 0 else "bottom")
        cells += 2
    return cells


def _profile(style, width, base=3):
    """The false front's extra courses above the roof line, per column.

    EVERY COLUMN CARRIES AT LEAST `base`, in every style, because the big sign hangs on the
    parapet's first course and a sign with no wall behind it is the one mistake `_sign` exists to
    catch - and `_sign` returning False is silent, so the guarantee is made here as well.

    **AND THE FOUR STYLES MUST BE FOUR SHAPES, WHICH IS THE WHOLE REASON THIS FUNCTION EXISTS.**
    `stepped` and `triangular` used to be `+2/+1/+0` on thresholds of t and `round(2*(1-t))`, and
    those are the SAME FUNCTION at every width the town actually uses: identical at 5, 6, 9, 11,
    14 and 17 - which is every shop width and the saloon's own default. Four names, three
    silhouettes, and a row of shops quietly drawing one parapet twice - exactly the failure this
    zone was sent back for, hiding inside the code written to prevent it. They are now separated
    by KIND rather than by threshold and cannot coincide at any width:

        flat        a level wall
        stepped     a broad plateau one course over broad shoulders - two levels, hard edges
        triangular  a ramp to a +3 apex, so its peak is always a course above stepped's
        bracketed   raised end piers over a lower middle

    `tests` for it is `_profile` itself: at every width 5..30 the four are pairwise different.
    """
    c = (width - 1) / 2.0
    out = []
    # the end pier scales with the front, or a narrow shop is ALL pier and `bracketed` comes out
    # as a flat wall - the fourth style collapsing into the first, which is the same bug again.
    pier = max(1, min(3, width // 4))
    for i in range(width):
        t = abs(i - c) / max(1.0, c)
        if style == "flat":
            v = base
        elif style == "stepped":
            # A PLATEAU, NOT A RAMP. Two levels only: nothing here is allowed to interpolate, or
            # it becomes `triangular` drawn with worse arithmetic.
            v = base + (2 if t < 0.5 else 1)
        elif style == "triangular":
            v = base + int(round(3 * (1 - t)))
        else:
            # BRACKETED: raised end piers over a lower middle. The fourth style was a SCALLOP -
            # `+1 where i % 3 == 1` - and in the render it came out as a castle: six merlons and
            # five gaps, which is the deck soffit's confetti wearing a cowboy hat.
            end = i < pier or i >= width - pier
            v = base + (2 if end else (1 if abs(i - c) <= max(1.0, width * 0.18) else 0))
        out.append(max(1, int(v)))
    return out


def _false_front(w, f, pal, ex, width, roof, style, seed, min_run, d=0):
    """The parapet standing proud of its own roof. The defining western detail, and the reason
    this zone reads as a street rather than as a row of sheds."""
    prof = _profile(style, width, 3)
    top = roof + 1
    for i in range(width):
        for k in range(prof[i]):
            h = top + k
            last = k == prof[i] - 1
            w.put(*f.at(i, d, h),
                  pal["trim"] if last else _weather(pal["wall"], ex["band"], f, i, d, h, seed))
        # a one-cell RETURN at each end, so the false front has thickness rather than being a card
        if i in (0, width - 1):
            for k in range(prof[i]):
                w.put(*f.at(i, d + 1, top + k), pal["trim"] if k == prof[i] - 1 else pal["wall"])
    # the moulding at the parapet's base: one long run, outside the plane, tall side into the wall
    _run_i(w, f, pal["stair"], 0, width - 1, d - 1, top, f.back, "top", min_run)
    return prof


def _weather(base, alt, f, i, d, h, seed, p=0.13):
    """Board-to-board variation, HASHED ON THE CELL.

    Hashed on the course instead, every cell of a course comes out identical and the wall is
    horizontal stripes of one material - which the store hall shipped once and the deck soffit
    shipped twice.
    """
    x, y, z = f.at(i, d, h)
    return alt if hash01(x, y, z, seed) < p else base


def _lamp_post(w, f, pal, i, d, h0=0, tall=3):
    """A post carrying its own lantern. A LANTERN ON TOP OF A POST STANDS ON IT: written
    `hanging=true` it looks for a block ABOVE it, finds open sky, and hangs from nothing."""
    for h in range(h0, h0 + tall):
        _timber(w, f, i, d, h, pal["post"], "y")
    w.put(*f.at(i, d, h0 + tall), pal["trim"])
    w.put(*f.at(i, d, h0 + tall + 1), pal["light"], hanging="false", waterlogged="false")


# ------------------------------------------------------------------------------ 1. the saloon

def _saloon(w: World, p: dict, ctx) -> dict:
    """TWO STOREYS, A FALSE FRONT, A PORCH AND A BALCONY - the town's one big building.

    The false front and the balcony over the porch are what a stranger names it by, so both are
    built at full size rather than suggested: the parapet stands three to SIX courses above the
    roof - flat 3, stepped and bracketed 5, triangular 6, measured off `_profile` rather than
    remembered - and the balcony is a real deck you could walk, with a fence rail on it.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    W = max(15, int(p["width"]))
    D = max(12, int(p["depth"]))
    P = 3                       # porch depth, in front of the front wall
    DECK, ROOF = 5, 11          # first floor, and the roof plane over the second
    mr = int(p["min_run"])
    seed = f.x * 131 + f.z
    style = FRONTS[int(hash01(f.x, f.z, 3) * len(FRONTS)) % len(FRONTS)]
    pi, mi = _axis_dirs(f)

    # ---- the ground it stands on, and the boardwalk in front of it
    _pad(w, f, pal, -1, W, -(P + 1), D)
    _pad(w, f, pal, -1, W, -P, -1, block=pal["beam"])            # boardwalk
    _pad(w, f, pal, 1, W - 2, 1, D - 2, block=pal["beam"])       # interior floorboards

    # ---- openings, LEFT EMPTY BY THE WALL LOOP and never punched afterwards
    dc = W // 2 - 1
    holes, panes = set(), []
    for h in range(3):                                          # the swing doors
        holes.add((dc, 0, h))
        holes.add((dc + 1, 0, h))
    for h in range(DECK + 1, DECK + 4):                         # the balcony doorway, upstairs
        holes.add((dc, 0, h))
        holes.add((dc + 1, 0, h))
    for i in (2, 3, W - 4, W - 3):                              # front windows, both storeys
        for h in (1, 2, 7, 8):
            holes.add((i, 0, h))
            panes.append((i, 0, h, "i"))
    for d in (3, 4, D - 5, D - 4):                              # side windows, both storeys
        for i in (0, W - 1):
            for h in (1, 2, 7, 8):
                holes.add((i, d, h))
                panes.append((i, d, h, "d"))
    for i in (2, 3, W - 4, W - 3):                              # back windows, upstairs only
        for h in (7, 8):
            holes.add((i, D - 1, h))
            panes.append((i, D - 1, h, "i"))
    bd = W // 2                                                 # the back door
    holes.add((bd, D - 1, 0))
    holes.add((bd, D - 1, 1))

    # ---- the shell
    for i in range(W):
        for d in range(D):
            if not (i in (0, W - 1) or d in (0, D - 1)):
                continue
            corner = i in (0, W - 1) and d in (0, D - 1)
            along = "i" if d in (0, D - 1) else "d"
            for h in range(ROOF):
                if (i, d, h) in holes:
                    continue
                if h == 0:
                    w.put(*f.at(i, d, h), _weather(pal["trim"], ex["worn"], f, i, d, h, seed, 0.2))
                elif corner:
                    _timber(w, f, i, d, h, pal["post"], "y")
                elif h == DECK:
                    # THE BELT COURSE. A two-storey box with no line at the floor level reads as
                    # one tall storey, which is the flat-wall failure the corpus measures us on.
                    _timber(w, f, i, d, h, ex["band"], _log_axis(f, along))
                else:
                    w.put(*f.at(i, d, h), _weather(pal["wall"], ex["band"], f, i, d, h, seed))
    for (i, d, h, along) in panes:
        _pane(w, f, i, d, h, along)
    # the batwing half-doors: waist height, open above and below, which is the joke and the detail
    for i in (dc, dc + 1):
        w.put(*f.at(i, 0, 1), pal["gate"], facing=f.facing, open="false",
              in_wall="false", powered="false")
    for k, half in ((0, "lower"), (1, "upper")):
        w.put(*f.at(bd, D - 1, k), ex["door"], facing=f.back, half=half,
              hinge="left", open="false", powered="false")

    # ---- roof, eaves and the false front
    for i in range(W):
        for d in range(D):
            w.put(*f.at(i, d, ROOF), pal["beam"])
    _eaves(w, f, pal["stair"], W, D, ROOF, mr)
    prof = _false_front(w, f, pal, ex, W, ROOF, style, seed, mr)

    # ---- the porch, and the balcony that is its roof
    posts = list(range(1, W - 1, 3))
    if W - 2 not in posts:
        posts.append(W - 2)
    for i in posts:
        # UP TO THE FASCIA, NOT THROUGH IT. Run to DECK the post's top course is the fascia's own,
        # so the beam repainted every post head - a cell written twice is a cell you do not have.
        for h in range(0, DECK - 1):
            _timber(w, f, i, -P, h, pal["post"], "y")
        # CORBEL BRACKETS, a PAIR at every post - a rhythm rather than a scatter, which is the
        # distinction rule 9 is really about.
        #
        # A BRACKET GOES *UNDER* THE BEAM IT CARRIES. Drawn at DECK-1 they sat in the fascia's own
        # course, and the fascia is laid afterwards across the WHOLE frontage - so all eleven were
        # overwritten and the porch shipped as six bare posts under a plain board. Nothing could
        # see it: the design is still one piece, still audits clean, still costs the same, and the
        # bracket is a stair whose absence no render of ours distinguishes from its presence.
        for (di, face) in ((-1, pi), (1, mi)):
            if 0 <= i + di < W:
                _stair(w, f, i + di, -P, DECK - 2, pal["stair"], face, "top")
    for i in range(-1, W + 1):                                  # the fascia board
        w.put(*f.at(i, -P, DECK - 1), pal["trim"])
    for i in range(-1, W + 1):                                  # balcony floor = porch roof
        for d in range(-P, 0):
            w.put(*f.at(i, d, DECK), pal["beam"])
    for i in range(-1, W + 1):                                  # the rail, which is the silhouette
        w.put(*f.at(i, -P, DECK + 1), pal["fence"])
    for d in range(-P, 0):
        w.put(*f.at(-1, d, DECK + 1), pal["fence"])
        w.put(*f.at(W, d, DECK + 1), pal["fence"])

    # ---- inside: an upper floor, a flight up to it, a bar, and light
    stair_hi, stair_lo = W - 2, W - 6
    for i in range(1, W - 1):
        for d in range(1, D - 1):
            if stair_lo <= i <= stair_hi and d >= D - 3:
                continue                                        # the stair well
            w.put(*f.at(i, d, DECK), pal["beam"])
    for k in range(5):                                          # ASCENDING TOWARD -i, so facing=-i
        i = stair_hi - k
        _stair(w, f, i, D - 2, k, pal["stair"], mi, "bottom")
        for h in range(k):
            w.put(*f.at(i, D - 2, h), pal["beam"])
    for i in range(1, max(2, W // 2 - 2)):                       # the bar
        w.put(*f.at(i, D - 2, 0), pal["trim"])
        _slab(w, f, i, D - 2, 1, pal["slab"], "top")
    for i in (2, W - 3):
        w.put(*f.at(i, D // 2, DECK - 1), pal["light"], hanging="true", waterlogged="false")
        w.put(*f.at(i, D // 2, ROOF - 1), pal["light"], hanging="true", waterlogged="false")
    for i in (1, W - 2):                                        # porch lamps, hung off the fascia
        _hang_light(w, f, pal, i, -P + 1, DECK - 2)

    # ---- signs. The big one goes on the false front, where the centre column is tallest.
    title = str(p.get("title") or "SALOON").upper()
    signed = 0
    if p.get("sign", True):
        signed += _sign(w, f, pal, W // 2, -1, ROOF + 1, f.facing,
                        [title[:SIGN_WIDTH], "", "whiskey & beds", ""])
        signed += _sign(w, f, pal, dc, -1, 4, f.facing, ["ROOMS 2 BITS", "", "", ""])
        lines = list(p.get("lines") or ["no shooting", "settle up", "at the bar"])
        signed += _sign(w, f, pal, W // 2, D, 2, f.back, ["HOUSE RULES"] + lines)
    return {"kind": "saloon", "width": W, "depth": D, "height": ROOF + 1 + max(prof),
            "front": style, "signs": signed,
            "contract": "two storeys under a false front, a covered porch on posts with a railed "
                        "balcony over it, and a stair inside that actually reaches the first floor"}


# ------------------------------------------------------------------------------ 2. water tower

def _octagon(R):
    """The tank's plan. A CIRCLE THIS SMALL RASTERISES AS A LUMP; an octagon is a decision, reads
    as coopered staves, and gives the banding four flat faces to run along."""
    cut = R + R // 2
    return {(di, dd) for di in range(-R, R + 1) for dd in range(-R, R + 1)
            if abs(di) <= R and abs(dd) <= R and abs(di) + abs(dd) <= cut}


def _watertower(w: World, p: dict, ctx) -> dict:
    """A TANK ON LEGS. It exists to be a silhouette, so everything below the tank is open frame.

    Minimum 18 tall by the spec and 26 as built, counted rather than estimated: twelve courses of
    leg, the tank floor, seven courses of stave, the rim plate, three of stepped cone, and a
    finial of fence and lantern. The bracing is what stops four posts reading as four posts.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    R = 4
    LEG = max(12, int(p["height"] or 24) - 12)
    TANK = 7
    c = R + 1
    seed = f.x * 977 + f.z
    ring = _octagon(R)
    edge = {(di, dd) for (di, dd) in ring
            if not all((di + a, dd + b) in ring for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))}

    _pad(w, f, pal, -1, 2 * c + 1, -1, 2 * c + 1)
    # a paved apron under the frame, so the legs stand on something dressed
    for (di, dd) in ring:
        w.put(*f.at(c + di, c + dd, -1), pal["path"])

    # ---- four legs, on the square inscribed in the tank
    legs = [(c - 3, c - 3), (c + 3, c - 3), (c - 3, c + 3), (c + 3, c + 3)]
    for (li, ld) in legs:
        for h in range(LEG):
            _timber(w, f, li, ld, h, pal["post"], "y")

    # ---- girts and cross-bracing. Four posts with nothing between them is scaffolding.
    girts = [LEG // 3, 2 * LEG // 3]
    for g in girts:
        for i in range(c - 3, c + 4):
            w.put(*f.at(i, c - 3, g), pal["beam"])
            w.put(*f.at(i, c + 3, g), pal["beam"])
        for d in range(c - 3, c + 4):
            w.put(*f.at(c - 3, d, g), pal["beam"])
            w.put(*f.at(c + 3, d, g), pal["beam"])
    pi, mi = _axis_dirs(f)
    span = girts[1] - girts[0]
    n = min(6, span)
    # A BRACE STARTS INSIDE THE LEG IT BRACES. Run from the leg's own column it OVERWRITES two
    # courses of post with stairs, and the audit caught it from three rooms away: the ladder that
    # climbs that leg reported "no wall behind" at exactly the two courses the brace had eaten.
    for d in (c - 3, c + 3):
        _brace(w, f, c - 2, d, girts[0] + 1, 1, 1, n - 1, pal["stair"], pi)
        _brace(w, f, c + 2, d, girts[0] + 1, -1, 1, n - 1, pal["stair"], mi)

    # ---- the tank: a floor, staves, and three hoops
    for (di, dd) in ring:
        w.put(*f.at(c + di, c + dd, LEG), pal["beam"])
    for k in range(1, TANK + 1):
        hoop = k in (1, TANK // 2 + 1, TANK)
        for (di, dd) in edge:
            along = "i" if abs(dd) >= abs(di) else "d"
            if hoop:
                _timber(w, f, c + di, c + dd, LEG + k, ex["bark"], _log_axis(f, along))
            else:
                w.put(*f.at(c + di, c + dd, LEG + k),
                      _weather(pal["wall"], ex["band"], f, c + di, c + dd, LEG + k, seed))

    # ---- the catwalk round the tank, and a ladder up to it
    #
    # THE LADDER'S OWN COLUMN GETS NO RAIL, AND THAT IS THE DIFFERENCE BETWEEN A LADDER AND A
    # DECORATION. The rail ran the whole ring, so the climb ended with a fence in the cell you
    # step out into: you could go up and not get off. Nothing measures this - the design is one
    # piece, every block is legal and supported, and only walking it finds the lid.
    lad = (c - 3, c - 4)
    walk = 0
    for (di, dd) in edge:
        for (a, b) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            o = (di + a, dd + b)
            if o in ring or abs(o[0]) > R + 1 or abs(o[1]) > R + 1:
                continue
            _slab(w, f, c + o[0], c + o[1], LEG, pal["slab"], "top")
            if (c + o[0], c + o[1]) != lad:
                w.put(*f.at(c + o[0], c + o[1], LEG + 1), pal["fence"])
            walk += 1
    # ...and it reaches the WALKING level, not the floor course. Stopping at LEG left the top rung
    # inside a top slab, which is a step you cannot take. The stave behind it at LEG+1 is a full
    # block, so the rung has something to hang on.
    for h in range(1, LEG + 2):
        w.put(*f.at(*lad, h), "ladder", facing=f.facing, waterlogged="false")

    # ---- the cap: a stepped cone, with an eave course of stairs at its skirt
    top = LEG + TANK + 1
    for (di, dd) in edge:
        face = pi if di > 0 else (mi if di < 0 else (f.back if dd > 0 else f.facing))
        _stair(w, f, c + di, c + dd, top, ex["rock_stair"], face, "bottom")
    # THE RIM PLATE, and it is not decoration. Built as an eave RING alone, the cone above stood
    # on nothing: the ring is the octagon's EDGE cells and the first cone course is an inner disc,
    # so the two never touch and the whole cap - 65 cells, cone, finial and lantern - shipped as a
    # second component floating over the tank. A roof needs a plate under it.
    for (di, dd) in ring - edge:
        w.put(*f.at(c + di, c + dd, top), pal["beam"])
    for k, rr in enumerate((R - 1, R - 2, R - 3)):
        for (di, dd) in _octagon(max(1, rr)):
            if k:
                w.put(*f.at(c + di, c + dd, top + 1 + k), pal["trim"])
            else:
                _timber(w, f, c + di, c + dd, top + 1 + k, ex["bark"])
    w.put(*f.at(c, c, top + 4), pal["fence"])
    w.put(*f.at(c, c, top + 5), pal["light"], hanging="false", waterlogged="false")

    # ---- the downspout, which is what says WATER rather than grain
    for h in range(1, LEG + 1):
        w.put(*f.at(c, -1, h), pal["fence"])
    # THE SPLASH STAIR IS THE SPOUT'S FOOT, and the apron used to run straight over it: the slab
    # loop included i == c, so the stair was placed and then deleted one line later. The apron
    # lies either side of it now.
    _stair(w, f, c, -1, 0, pal["stair"], f.facing, "bottom")
    for i in (c - 1, c + 1):
        _slab(w, f, i, -1, 0, ex["rock_slab"], "bottom")

    signed = 0
    if p.get("sign", True):
        title = str(p.get("title") or "WATER").upper()
        # ON THE OTHER LEG: hung on the ladder's column it replaces a rung, and a ladder with a
        # sign where its fourth step should be is a ladder you cannot climb.
        signed += _sign(w, f, pal, c + 3, c - 4, 2, f.facing,
                        [title[:SIGN_WIDTH], "", "town supply", ""])
    return {"kind": "watertower", "legs": len(legs), "tank_r": R, "walk": walk,
            "height": top + 6, "signs": signed,
            "contract": "a tank carried on four braced legs, read as a silhouette: open frame "
                        "below, banded staves above, a conical cap and a downspout to the ground"}


# --------------------------------------------------------------------------------- 3. windmill

def _windmill(w: World, p: dict, ctx) -> dict:
    """A TAPERING TOWER AND FOUR SAILS, and THE SAILS ARE THE POINT.

    Ten-block arms on a hub fifteen courses up put the sail circle across twenty-one blocks in
    both axes, which is bigger than the tower it turns on - so the outline is broken by something
    no other structure in the park has. Each arm is a real lattice: two fence spines with a
    trapdoor cloth between them, which is the vertical panel Minecraft never shipped as a block
    and the single strongest piece of vocabulary in the download corpus.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    H = max(18, int(p["height"] or 22) - 4)     # shaft courses; cap and finial ride above
    Rb, Rt = 4.2, 2.6
    c = 5
    seed = f.x * 613 + f.z
    pi, mi = _axis_dirs(f)

    def rad(h):
        return Rb + (Rt - Rb) * (h / max(1.0, H - 1.0))

    _pad(w, f, pal, -1, 2 * c + 1, -1, 2 * c + 1)

    # ---- the shaft. A SHELL 1.2 THICK, so two neighbouring courses always overlap: a tapering
    # ring drawn one cell wide can step clean off the ring below it and shed a component.
    shell = {}
    for h in range(H):
        r = rad(h)
        cells = []
        for di in range(-5, 6):
            for dd in range(-5, 6):
                dist = (di * di + dd * dd) ** 0.5
                if r - 1.25 < dist <= r:
                    cells.append((di, dd))
        shell[h] = cells

    holes = set()
    for h in range(3):                                          # the door, front and centre
        for (di, dd) in shell[h]:
            if abs(di) <= 1 and dd < 0:
                holes.add((c + di, c + dd, h))
    glaze = []
    for h in (7, 8, 12, 13):
        for (di, dd) in shell[h]:
            if abs(dd) <= 1 and abs(di) >= 3:
                glaze.append((c + di, c + dd, h))
    for h in range(H):
        stone = h < 6
        for (di, dd) in shell[h]:
            cell = (c + di, c + dd, h)
            if cell in holes:
                continue
            if cell in glaze:
                _pane(w, f, cell[0], cell[1], cell[2], "d")
                continue
            base = ex["rock"] if stone else pal["wall"]
            alt = ex["aged"] if stone else ex["band"]
            w.put(*f.at(*cell), _weather(base, alt, f, cell[0], cell[1], cell[2], seed, 0.18))
    for h in (6, 12):                                           # string courses, one cell proud
        r = rad(h)
        for di in range(-6, 7):
            for dd in range(-6, 7):
                dist = (di * di + dd * dd) ** 0.5
                if r < dist <= r + 1.0:
                    w.put(*f.at(c + di, c + dd, h), pal["trim"])
    for (di, dd) in shell[3]:                                   # the door's lintel
        if abs(di) <= 1 and dd < 0:
            _timber(w, f, c + di, c + dd, 3, ex["band"], _log_axis(f, "i"))

    # ---- the stage: a gallery ring you could walk, with a rail and corbels under it
    gal = 9
    rg = rad(gal)
    stage = []
    for di in range(-6, 7):
        for dd in range(-6, 7):
            dist = (di * di + dd * dd) ** 0.5
            if rg < dist <= rg + 1.2:
                stage.append((di, dd))
    for (di, dd) in stage:
        _slab(w, f, c + di, c + dd, gal, pal["slab"], "top")
        w.put(*f.at(c + di, c + dd, gal + 1), pal["fence"])
    for k, (di, dd) in enumerate(sorted(stage)):                # corbels, every third cell
        if k % 3:
            continue
        face = pi if di > 0 else (mi if di < 0 else (f.back if dd > 0 else f.facing))
        _stair(w, f, c + di, c + dd, gal - 1, ex["rock_stair"], face, "top")

    # ---- the cap
    top = H
    for (di, dd) in shell[H - 1]:
        face = pi if di > 0 else (mi if di < 0 else (f.back if dd > 0 else f.facing))
        _stair(w, f, c + di, c + dd, top, pal["stair"], face, "bottom")
    for k, rr in enumerate((2.4, 1.6, 0.9)):
        for di in range(-3, 4):
            for dd in range(-3, 4):
                if (di * di + dd * dd) ** 0.5 <= rr:
                    _timber(w, f, c + di, c + dd, top + 1 + k, ex["bark"], "y")
    w.put(*f.at(c, c, top + 4), pal["fence"])
    w.put(*f.at(c, c, top + 5), pal["light"], hanging="false", waterlogged="false")

    # ---- the sails. The hub hangs one cell clear of the shaft, found by asking the world where
    # the shaft actually stopped rather than by trusting the radius arithmetic.
    hub_h = H - 3
    # CLEAR OF THE WIDEST COURSE, NOT OF THE HUB'S OWN. Measured at hub height alone the sail
    # plane sat one cell off a tower that is a block and a half fatter at its foot, so the whole
    # down-arm was swallowed by the plinth and the mill had three sails from the front.
    front = c
    for h in range(H):
        for d in range(-1, c + 1):
            if w.has(*f.at(c, d, h)):
                front = min(front, d)
                break
    hd = front - 1
    for di in (-1, 0, 1):
        for dh in (-1, 0, 1):
            _timber(w, f, c + di, hd, hub_h + dh, ex["band"], _log_axis(f, "d"))
    # THE WINDSHAFT, which is what joins the sails to the mill: without it the hub hangs two
    # cells clear of the tower and the whole sail assembly is a second component.
    for d in range(hd + 1, c + 1):
        if w.has(*f.at(c, d, hub_h)):
            break
        _timber(w, f, c, d, hub_h, ex["band"], _log_axis(f, "d"))

    # A SAIL IS A FRAME WITH HOLES IN IT. Built as a spine with the cloth filling every cell
    # beside it, the four arms rendered as four solid planks - a cross, not a windmill, and
    # exactly the "single mass" failure this repo keeps writing down. Two rails with rungs every
    # other course leave the gaps that make it read as lattice, and hanging the cloth on ONE side
    # of each arm - rotated a quarter turn per arm - gives the pinwheel its direction.
    L = 10
    cloth = 0
    arms = ((0, 1), (0, -1), (1, 0), (-1, 0))                   # (di, dh) along each arm
    for (ai, ah) in arms:
        pi_, ph = ah, -ai                                       # the perpendicular, turned +90
        for k in range(2, L + 1):
            base_i, base_h = c + ai * k, hub_h + ah * k
            for o in (0, 3):                                    # the two rails
                w.put(*f.at(base_i + pi_ * o, hd, base_h + ph * o), pal["fence"])
            if k % 2:
                continue
            for o in (1, 2):                                    # the cloth, every other course
                w.put(*f.at(base_i + pi_ * o, hd, base_h + ph * o), ex["trap"],
                      facing=f.facing, half="bottom", open="true",
                      powered="false", waterlogged="false")
                cloth += 1

    signed = 0
    if p.get("sign", True):
        title = str(p.get("title") or "MILL").upper()
        # THE NAMEPLATE HANGS ON THE COURSE IT IS ACTUALLY AT. A round tower's front column moves
        # in as it tapers, so a depth read off the base is air four courses up - and `_sign`
        # answers that by silently declining, which is a sign nobody notices is missing.
        sd = c
        for d in range(-1, c + 1):
            if w.has(*f.at(c, d, 4)):
                sd = d
                break
        signed += _sign(w, f, pal, c, sd - 1, 4, f.facing,
                        [title[:SIGN_WIDTH], "", "grain & feed", ""])
    return {"kind": "windmill", "height": hub_h + L + 1, "shaft": H, "arm": L, "cloth": cloth,
            "signs": signed,
            "contract": "four ten-block lattice sails on a hub clear of a tapering tower, so the "
                        "silhouette is the sail circle and not the shaft"}


# --------------------------------------------------------------------------------- 4. minehead

def _minehead(w: World, p: dict, ctx) -> dict:
    """THE LAND'S SIGNATURE: a timbered portal into a spoil bank under an A-frame headframe.

    A mine entrance is three things at once and all three are built - the hole, the timber that
    keeps the hole open, and the machine that lifts out of it. At 21 courses the headframe is the
    third tallest thing in the zone, behind the windmill and the water tower at 26 apiece (it was
    written here as the second, which measuring says it never was), and the sheave wheel at the
    top is the one round shape in a town made of squares.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    W = max(13, int(p["width"]))
    D = max(16, int(p["depth"]))
    ci = W // 2
    face_d = 9                                  # the mound's front face
    seed = f.x * 449 + f.z
    pi, mi = _axis_dirs(f)
    mr = int(p["min_run"])

    _pad(w, f, pal, -2, W + 1, -2, D)

    # ---- the spoil bank, with the adit driven through it. THE TUNNEL IS LEFT EMPTY BY THE LOOP.
    def bank_h(i, d):
        t = (d - face_d) / max(1.0, D - 1 - face_d)
        e = 1.0 - abs(i - ci) / max(1.0, ci + 1.0)
        # STEEP OFF THE FACE. A linear bank rose so gently that it read as scattered rubble
        # rather than as a hillside with a hole cut in it; the adit has to go INTO something.
        v = 1 + 9 * (t ** 0.55) * (0.40 + 0.60 * e)
        return max(0, int(round(v + hash01(i, d, seed) * 1.4 - 0.4)))

    tunnel = {(i, d) for i in range(ci - 2, ci + 3) for d in range(face_d, D)}
    for i in range(W):
        for d in range(face_d, D):
            for h in range(bank_h(i, d) + 1):
                if (i, d) in tunnel and h <= 3:
                    continue
                base = ex["rock"] if h else ex["aged"]
                w.put(*f.at(i, d, h), _weather(base, ex["aged"] if h else ex["rock"],
                                               f, i, d, h, seed, 0.3))
    # timber sets down the adit: posts at the ribs, a cap over them, a lantern every other set
    for k, d in enumerate(range(face_d, D, 2)):
        for i in (ci - 2, ci + 2):
            for h in range(4):
                _timber(w, f, i, d, h, pal["post"], "y")
        for i in range(ci - 2, ci + 3):
            _timber(w, f, i, d, 4, ex["band"], _log_axis(f, "i"))
        if k % 2 == 0:
            w.put(*f.at(ci, d, 3), pal["light"], hanging="true", waterlogged="false")

    # ---- the portal: a bigger frame standing proud of the bank, with a header board over it
    for i in (ci - 3, ci + 3):
        for h in range(6):
            _timber(w, f, i, face_d, h, pal["post"], "y")
            _timber(w, f, i, face_d - 1, h, pal["post"], "y")
    for i in range(ci - 3, ci + 4):
        _timber(w, f, i, face_d, 6, ex["band"], _log_axis(f, "i"))
        _timber(w, f, i, face_d - 1, 6, ex["band"], _log_axis(f, "i"))
        # THE HEADER BOARD IS TWO CELLS DEEP, AND THAT IS STRUCTURAL, NOT TASTE. Built at face_d
        # alone, the cornice one cell proud of it at face_d-2 touched NOTHING: the cap band below
        # is at face_d-1, which is diagonal to it, and diagonal is not 6-connected. So the whole
        # seven-stair moulding shipped as a separate component - and the connectivity check PASSED,
        # because the nameplate happened to bridge the gap. A sign is not a structural member: set
        # `sign: False` and the same design sheds a floating run. The board carries it now.
        w.put(*f.at(i, face_d, 7), pal["wall"])                 # the header board, for the sign
        w.put(*f.at(i, face_d - 1, 7), pal["wall"])
    _run_i(w, f, pal["stair"], ci - 3, ci + 3, face_d - 2, 7, f.back, "top", mr)
    for i in (ci - 3, ci + 3):
        w.put(*f.at(i, face_d - 2, 5), pal["trim"])
        w.put(*f.at(i, face_d - 2, 4), pal["light"], hanging="true", waterlogged="false")
    # retaining walls battering back from the portal, so the bank has a built edge not a slump
    for k in range(1, 4):
        for i in (ci - 3 - k, ci + 3 + k):
            if not 0 <= i < W:
                continue
            for h in range(max(1, 5 - k)):
                w.put(*f.at(i, face_d, h), _weather(pal["trim"], ex["worn"], f, i, face_d, h, seed))

    # ---- the headframe: four splayed legs to a platform, braced, with a sheave wheel on top
    PH = 15
    legs = ((ci - 4, 5), (ci + 4, 5), (ci - 4, face_d), (ci + 4, face_d))
    for (li, ld) in legs:
        di = 1 if li < ci else -1
        for h in range(PH + 1):
            step = h * 2 // PH                                  # 0,1,2 - the splay, in two kinks
            _timber(w, f, li + di * step, ld, h, pal["post"], "y")
            if h and h * 2 % PH == 0:                           # the kink cell, so it stays joined
                _timber(w, f, li + di * step, ld, h - 1, pal["post"], "y")
    for g in (5, 10):                                           # girts and X braces on all faces
        for i in range(ci - 4, ci + 5):
            w.put(*f.at(i, 5, g), pal["beam"])
            w.put(*f.at(i, face_d, g), pal["beam"])
        for d in range(5, face_d + 1):
            w.put(*f.at(ci - 4, d, g), pal["beam"])
            w.put(*f.at(ci + 4, d, g), pal["beam"])
    for d in (5, face_d):
        _brace(w, f, ci - 3, d, 6, 1, 1, 4, pal["stair"], pi)
        _brace(w, f, ci + 3, d, 6, -1, 1, 4, pal["stair"], mi)
    for i in range(ci - 2, ci + 3):                             # the platform, a ring round a shaft
        for d in range(6, face_d):
            if i == ci and d == 7:
                continue                                        # the hoist shaft stays open
            w.put(*f.at(i, d, PH), pal["beam"])
    for i in (ci - 2, ci + 2):
        for h in (PH + 1, PH + 2, PH + 3):
            _timber(w, f, i, 7, h, pal["post"], "y")
    # THE SHEAVE WHEEL: a square ring is the one wheel shape that is 6-connected all the way
    # round. A rasterised circle of this radius breaks at the diagonals and sheds four cells.
    wheel = 0
    for di in range(-2, 3):
        for dh in range(-2, 3):
            if max(abs(di), abs(dh)) == 2:
                _timber(w, f, ci + di, 7, PH + 3 + dh, ex["band"], _log_axis(f, "d"))
                wheel += 1
    for (di, dh) in ((1, 0), (-1, 0), (0, 1), (0, -1)):         # spokes, or the hub is an island
        w.put(*f.at(ci + di, 7, PH + 3 + dh), pal["fence"])
    _timber(w, f, ci, 7, PH + 3, ex["bark"], _log_axis(f, "d"))
    # THE CABLE LEAVES FROM UNDER THE WHEEL, NOT THROUGH IT. Run to PH+3 it climbed back up the
    # sheave's own column and repainted two of its cells - the bottom of the ring at PH+1 and the
    # bottom spoke at PH+2 - so the wheel shipped as a broken ring with three spokes while `meta`
    # cheerfully reported sixteen. It still audited clean and it was still one piece; the chain
    # simply stood in for the blocks it had eaten. It now hangs from the ring below the wheel,
    # which is where a hoist rope actually comes off a sheave.
    for h in range(PH - 4, PH + 1):                             # the cable, hung from the wheel
        w.put(*f.at(ci, 7, h), "iron_chain", axis="y", waterlogged="false")

    # ---- the tramway out of the adit, and two ore tubs on it
    rail_shape = "east_west" if f.sx else "north_south"
    tubs = []
    for d in range(0, face_d):
        w.put(*f.at(ci, d, 0), pal["beam"])                     # the sleeper bed
        for i in (ci - 1, ci + 1):
            _slab(w, f, i, d, 0, pal["slab"], "bottom")
        if d in (2, 3, 6):
            tubs.append(d)
            w.put(*f.at(ci, d, 1), ex["rock"])                  # the ore in the tub
            for (ti, td, fc) in ((ci - 1, d, mi), (ci + 1, d, pi)):
                w.put(*f.at(ti, td, 1), ex["trap"], facing=fc, half="bottom",
                      open="true", powered="false", waterlogged="false")
        else:
            w.put(*f.at(ci, d, 1), "rail", shape=rail_shape, waterlogged="false")
    for d in (1, 5):                                            # trackside lamps
        _lamp_post(w, f, pal, ci - 3, d, 0, 3)

    signed = 0
    if p.get("sign", True):
        title = str(p.get("title") or "NO. 3 MINE").upper()
        # SET INTO THE CORNICE, backed by the header board that now stands behind it - the same
        # arrangement the shopfronts use, and the one that keeps the sign on a FULL block.
        signed += _sign(w, f, pal, ci, face_d - 2, 7, f.facing,
                        [title[:SIGN_WIDTH], "", "hard hats on", ""])
        signed += _sign(w, f, pal, ci - 3, face_d - 2, 2, f.facing,
                        ["ASSAY OFFICE", "", "ore weighed", "here"])
    return {"kind": "minehead", "width": W, "depth": D, "height": PH + 6,
            "wheel": wheel, "tubs": len(tubs), "signs": signed,
            "contract": "a timbered adit through a spoil bank, a braced A-frame headframe with a "
                        "sheave wheel and a hanging cable, and a tramway with loaded tubs on it"}


# ------------------------------------------------------------------------------- 5. falsefront

def _shopfront(w, f, pal, ex, p, i0, width, D, k, mr):
    """One storefront of the row. EVERY DECISION HERE IS HASHED ON ITS INDEX, so the row is varied
    and a regeneration is identical - `random` would make the design undiffable against the world.
    """
    seed = f.x * 37 + f.z * 11 + k * 101
    style = FRONTS[int(hash01(k, f.x, f.z) * len(FRONTS)) % len(FRONTS)]
    roof = 4 + int(hash01(k, 5, f.z) * 3)                       # 4..6 courses to the roof plane
    porch = hash01(k, 9, f.x) < 0.6
    wide_win = hash01(k, 13, f.z) < 0.5
    body = pal["wall"] if hash01(k, 17, f.x) < 0.6 else ex["band"]
    dc = i0 + width // 2
    pi, mi = _axis_dirs(f)

    for i in range(i0, i0 + width):
        for d in range(D):
            if not (i in (i0, i0 + width - 1) or d in (0, D - 1)):
                continue
            corner = i in (i0, i0 + width - 1) and d in (0, D - 1)
            along = "i" if d in (0, D - 1) else "d"
            for h in range(roof):
                if d == 0 and i == dc and h < 3:
                    continue                                    # the doorway
                if d == 0 and h in ((1, 2) if wide_win else (2,)) and i in (
                        dc - 2, dc - 1, dc + 1, dc + 2) and i0 < i < i0 + width - 1:
                    continue                                    # the shop window
                if h == 0:
                    w.put(*f.at(i, d, h), _weather(pal["trim"], ex["worn"], f, i, d, h, seed, 0.25))
                elif corner:
                    _timber(w, f, i, d, h, pal["post"], "y")
                else:
                    w.put(*f.at(i, d, h),
                          _weather(body, pal["trim"] if body != pal["wall"] else ex["band"],
                                   f, i, d, h, seed))
            if d == 0 and i0 < i < i0 + width - 1:
                for h in ((1, 2) if wide_win else (2,)):
                    if i in (dc - 2, dc - 1, dc + 1, dc + 2):
                        _pane(w, f, i, 0, h, "i")
    for i in range(i0, i0 + width):                             # roof plane
        for d in range(D):
            w.put(*f.at(i, d, roof), pal["beam"])
    _run_i(w, f, pal["stair"], i0, i0 + width - 1, -1, roof, f.back, "bottom", mr)
    _run_i(w, f, pal["stair"], i0, i0 + width - 1, D, roof, f.facing, "bottom", mr)

    # the false front, which is what makes a shed a storefront
    prof = _profile(style, width, 2 + int(hash01(k, 3, f.x) * 3))
    for n, i in enumerate(range(i0, i0 + width)):
        for c in range(prof[n]):
            h = roof + 1 + c
            w.put(*f.at(i, 0, h),
                  pal["trim"] if c == prof[n] - 1 else _weather(body, ex["band"], f, i, 0, h, seed))
    _run_i(w, f, pal["stair"], i0, i0 + width - 1, -1, roof + 1, f.back, "top", mr)

    if porch:
        for i in (i0 + 1, i0 + width - 2):
            for h in range(3):
                _timber(w, f, i, -2, h, pal["post"], "y")
        # THE HEADER IS A FULL BEAM AND THE ROOF IS SLABS - and in that order the slab loop ran
        # over d=-2 and ATE the header it had just laid, which only showed up as the porch lamp
        # reporting that it was hanging from a slab. A cell written twice is a cell you do not
        # have.
        for i in range(i0, i0 + width):
            w.put(*f.at(i, -2, 3), pal["trim"])
            _slab(w, f, i, -1, 3, pal["slab"], "bottom")
        # THE BRACKETS TAKE THE NEAREST COLUMN THAT IS ACTUALLY FREE, and on a narrow front that
        # is not the one beside the post. Fixed at i0+2 and i0+width-3 they landed on the door
        # centre on a 5- and 6-wide shop, where the porch lantern - placed afterwards - deleted
        # them without a word: those porches shipped as two bare posts under a board. Three
        # columns of this plane are already spoken for, and only one of them is visible in the
        # cells the shopfront itself writes:
        #
        #     the two porch posts        this loop, above
        #     the door centre            the porch lantern, four lines down
        #     the LAST column            `_falsefront`'s boardwalk lamp post, which is a whole
        #                                function away and eats an outboard bracket in silence
        #
        # A 5-wide porch has exactly one free column and gets one bracket. That is the front
        # being small, not the rule failing, so it is allowed rather than forced.
        taken = {i0 + 1, i0 + width - 2, dc, i0 + width - 1}
        for post_i in (i0 + 1, i0 + width - 2):
            inward = 1 if post_i == i0 + 1 else -1
            for off in (inward, -inward, 2 * inward, -2 * inward,
                        3 * inward, -3 * inward, 4 * inward, -4 * inward):
                bi = post_i + off
                if bi in taken or not i0 <= bi <= i0 + width - 1:
                    continue
                taken.add(bi)
                _stair(w, f, bi, -2, 2, pal["stair"], mi if bi > post_i else pi, "top")
                break
        # HUNG FROM THE HEADER, NOT FROM THE PORCH SLABS. A lantern wants a FULL block over it;
        # under a slab cap it reads as hanging from air, which is the exact fault the lowland's
        # lightroom shipped once and its own notes wrote down.
        w.put(*f.at(dc, -2, 2), pal["light"], hanging="true", waterlogged="false")
    else:
        # no porch: an awning of upside-down stairs instead, so the front still has relief
        _run_i(w, f, pal["stair"], i0, i0 + width - 1, -1, 3, f.back, "top", mr)

    for h in range(2):                                          # a real door in the doorway
        w.put(*f.at(dc, 0, h), ex["door"], facing=f.facing,
              half="lower" if h == 0 else "upper", hinge="left" if k % 2 else "right",
              open="false", powered="false")
    trades = ["GENERAL STORE", "ASSAY OFFICE", "BARBER", "LIVERY", "GUNSMITH",
              "BANK", "TELEGRAPH", "FEED & SEED"]
    trade = trades[k % len(trades)]
    signed = _sign(w, f, pal, dc, -1, roof + 1, f.facing, [trade[:SIGN_WIDTH], "", "", ""])
    return {"width": width, "style": style, "roof": roof, "porch": porch,
            "trade": trade, "signed": bool(signed)}


def _falsefront(w: World, p: dict, ctx) -> dict:
    """A ROW OF STOREFRONTS, AND NO TWO OF THEM MAY READ THE SAME.

    Width, false-front profile, roof height, porch-or-awning, window pattern, wall tone, door
    hinge and trade all vary by a hash of the shop's index. Four shops of one design is a repeated
    box, which is exactly what this zone was sent back for.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    n = max(4, int(p["shops"]))
    D = max(6, min(9, int(p["depth"])))
    mr = int(p["min_run"])

    widths = [5 + int(hash01(k, f.x, f.z, 2) * 5) for k in range(n)]
    total = sum(widths)

    _pad(w, f, pal, -1, total, -3, D)
    _pad(w, f, pal, -1, total, -2, -1, block=pal["beam"])        # the boardwalk joins them all
    for i in range(-1, total + 1):
        _slab(w, f, i, -3, -1, pal["slab"], "top")               # its kerb, a step down to the road

    shops, i0 = [], 0
    for k in range(n):
        shops.append(_shopfront(w, f, pal, ex, p, i0, widths[k], D, k, mr))
        i0 += widths[k]
    for k in range(0, n):                                        # a lamp on the boardwalk kerb
        _lamp_post(w, f, pal, min(total - 1, sum(widths[:k + 1]) - 1), -2, 0, 3)

    styles = {s["style"] for s in shops}
    return {"kind": "falsefront", "shops": len(shops), "width": total, "depth": D,
            "styles": sorted(styles), "widths": widths,
            "signs": sum(1 for s in shops if s["signed"]),
            "trades": [s["trade"] for s in shops],
            "contract": "at least four storefronts sharing one boardwalk, each with its own "
                        "width, parapet profile, roof height, porch and glazing"}


# ---------------------------------------------------------------------------- 6. trestlebridge

def _trestlebridge(w: World, p: dict, ctx) -> dict:
    """A TIMBER TRESTLE ON BRACED BENTS - the structure the corpus says we never build, because
    it is nothing but stairs, fences and repetition.

    The deck rides eight courses over its own ground, so the bents are the whole design: two
    battered posts, a cap beam, sway bracing between them, and longitudinal stringers tying every
    bent to the next. Every third bent gets a masonry pier instead of a timber footing, which is
    what stops twenty-four blocks of identical frame reading as a comb.
    """
    f = _Frame(p)
    pal, ex = _pal(p)
    L = max(20, int(p["length"]))
    DH = max(6, int(p["deck"]))
    mr = int(p["min_run"])
    seed = f.x * 271 + f.z
    pi, mi = _axis_dirs(f)
    rail_shape = "east_west" if f.sx else "north_south"

    _pad(w, f, pal, -2, L + 1, -2, 4)

    bents = list(range(1, L, 4))
    piers = 0
    for k, i in enumerate(bents):
        stone = k % 3 == 2
        for d in (0, 2):
            # BATTERED POSTS: the foot stands one cell wider than the head, with the kink cell
            # doubled so the leg is one 6-connected timber and not two.
            out = -1 if d == 0 else 3
            half = DH // 2
            for h in range(half):
                _timber(w, f, i, out, h, ex["rock"] if stone else pal["post"])
            _timber(w, f, i, d, half - 1, pal["post"], "y")
            for h in range(half - 1, DH):
                _timber(w, f, i, d, h, pal["post"], "y")
        if stone:
            piers += 1
            for d in range(-1, 4):
                w.put(*f.at(i, d, 0), _weather(ex["rock"], ex["aged"], f, i, d, 0, seed, 0.3))
        # the cap beam over the bent, and sway bracing under it
        for d in range(-1, 4):
            _timber(w, f, i, d, DH - 1, ex["band"], _log_axis(f, "d"))
        for h in (DH // 2 + 1,):
            for d in range(0, 3):
                w.put(*f.at(i, d, h), pal["beam"])
        _stair(w, f, i, 1, DH - 2, pal["stair"], f.back, "top")
        # X BRACING BETWEEN BENTS, IN THE LOWER HALF. Run in the top half it was drawn straight
        # through the stringers and the deck that are laid afterwards, so three quarters of every
        # brace was overwritten and the bridge shipped with stubs - a design detail deleted by
        # build ORDER, which no audit can see because the result is still one solid piece.
        if i + 4 < L:
            _brace(w, f, i + 1, 0, 1, 1, 1, 3, pal["stair"], pi)
            _brace(w, f, i + 3, 0, 1, -1, 1, 3, pal["stair"], mi)
            _brace(w, f, i + 1, 2, 1, 1, 1, 3, pal["stair"], pi)
            _brace(w, f, i + 3, 2, 1, -1, 1, 3, pal["stair"], mi)

    # longitudinal stringers: what makes a row of bents into a bridge
    for d in (0, 2):
        for i in range(0, L):
            w.put(*f.at(i, d, DH - 1), pal["beam"])
    for i in range(0, L):                                       # the deck, and the rail on it
        for d in range(-1, 4):
            w.put(*f.at(i, d, DH), pal["beam"] if -1 < d < 3 else pal["trim"])
        w.put(*f.at(i, 1, DH + 1), "rail", shape=rail_shape, waterlogged="false")
        w.put(*f.at(i, -1, DH + 1), pal["fence"])
        w.put(*f.at(i, 3, DH + 1), pal["fence"])
    _run_i(w, f, pal["stair"], 0, L - 1, -2, DH, f.back, "top", mr)
    _run_i(w, f, pal["stair"], 0, L - 1, 4, DH, f.facing, "top", mr)

    # abutments: the bridge has to land on something at both ends
    for i in (-1, L):
        for d in range(-1, 4):
            for h in range(DH + 1):
                w.put(*f.at(i, d, h), _weather(pal["trim"], ex["worn"], f, i, d, h, seed, 0.2))
    for i in (-1, L):
        for d in (-1, 3):
            w.put(*f.at(i, d, DH + 1), pal["trim"])
            w.put(*f.at(i, d, DH + 2), pal["light"], hanging="false", waterlogged="false")

    signed = 0
    if p.get("sign", True):
        title = str(p.get("title") or "TRESTLE 4").upper()
        # ON THE ABUTMENT'S END FACE, read from off the end of the bridge. Hung at d=-2 facing
        # `back` it asked for a support at d=-3, where there is nothing at all - and `_sign`
        # returned False and the design shipped with no sign and no complaint, which is exactly
        # the silent failure its support check exists to make loud.
        signed += _sign(w, f, pal, -2, 1, DH - 1, mi,
                        [title[:SIGN_WIDTH], "", "load limit", "one cart"])
    return {"kind": "trestlebridge", "length": L, "deck": DH, "bents": len(bents),
            "piers": piers, "signs": signed,
            "contract": "a decked trestle on battered, braced and stringered bents, landing on a "
                        "masonry abutment at each end - never a plank floating between two posts"}


BUILDERS = {
    "saloon": _saloon,
    "watertower": _watertower,
    "windmill": _windmill,
    "minehead": _minehead,
    "falsefront": _falsefront,
    "trestlebridge": _trestlebridge,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**FRONTIER, **cfg}
    if not p.get("at"):
        raise ValueError("frontiertown needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    # AN UNKNOWN KIND RAISES. Defaulting to the first builder ships a design nobody asked for
    # under a name nobody will recognise, which is worse than a stack trace.
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown frontiertown kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    return w.canvas({
        "kind": f"frontiertown/{p['kind']}",
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
