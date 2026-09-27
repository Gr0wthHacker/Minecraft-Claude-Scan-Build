"""THE MIDWAY'S CIRCULATION: the hub, the queues, the exits, the games frontage, the thresholds.

`PARK_MIDWAY.md` asks for six things this repo could build the buildings for and could not build
the CONNECTIVE TISSUE for.  Every module the midway already has - the arrival court, the box
office, the wheel, the carousel, the games, the food court - is a destination.  Nothing in the
land was a ROUTE, a QUEUE, an EXIT or a THRESHOLD, so the park read as a field of attractions
with paving between them rather than as a place with a plan.

    hub         the distribution heart: two 5-wide spines, a circus, eight named lit branches,
                and a LOW meet-point - fountain, clock and map - that you walk round, never into
    ridequeue   a covered switchback with a marquee: one way in, one way out at the far end, an
                emergency gate on the flank, and NO SHORTCUT between the two
    rideexit    the way out of a ride: railed, lit, signed, and landing somewhere that is not the
                queue it came from and not a main spine
    gamesrow    one awning-and-facade frontage with N bays, each with a standing spot, a counter
                and a name - and a SERVICE CORRIDOR behind it that the public cannot walk into
    threshold   the land departure: a 5-wide paved handoff that changes palette BEFORE the arch,
                so you know you are leaving before you are told

THE FIVE RULES THIS FILE IS WRITTEN AGAINST, each of which this repo has already paid for:

1. **A QUEUE IS NOT A ROUTE.**  `PARK_OVERHAUL.md` rejects queue/exit/main-spine overlap outright.
   The failure is not that the geometry is wrong - a switchback with a hole in its middle wall is
   a perfectly good schematic - it is that the hole turns a two-minute line into a four-cell
   shortcut and nothing in an audit, a render or a block count can see it.  `_walk_len` measures
   the real distance from `queue_entry` to `queue_end` and the test demands it exceed a floor
   derived from the leg count, so a wall that loses one cell fails HERE.

2. **AN EXIT THAT DISCHARGES INTO ITS OWN QUEUE IS WORSE THAN NO EXIT.**  Vanilla has no
   reversible-walk one-way: `mcbuild.walk` steps down exactly one course, so any drop a player
   can walk out of is a drop they can walk back up.  So the guarantee here is TOPOLOGICAL and
   stated as such - the exit's cells are disjoint from the queue's, its discharge anchor is a
   measured distance from `queue_entry`, and it lands on a secondary rather than on the spine.
   It is signed, not gated, and `unverified` says so rather than implying a mechanism.

3. **HEADROOM IS ASSERTED, NOT HOPED FOR.**  Two clear courses over every cell a visitor stands
   on.  This bug class has bitten this project six times in a week - a spiral whose risers sat on
   every tread, eleven Ghost Train cells with a block over the rider, a canopy post standing on a
   rail - and every one of them passed the audit, because the audit asks about BLOCKS and the
   failure is in the AIR.  Every kind here returns a `standing` list and the test floods it.

4. **THE GROUND IS STONE.**  Jack, on the shipped park: wool belongs on the things that are not
   the ground.  Nothing this file lays underfoot is wool.  The figure in the paving is drawn from
   a value ladder measured ACROSS material families, which is the only place a ladder can exist:

       stone_bricks               122     the field
       stone                      126     the spine, so a spine reads as ROAD against the field
       smooth_basalt               73     the kerb that edges every spine
       polished_blackstone_bricks  45     the circus ring and the branch heads
       blackstone                  38     the meet-point's own rim

   Steps of 49, 28 and 7 - and the 7 is deliberate: `blackstone` against
   `polished_blackstone_bricks` is a TEXTURE change inside one dark tone, which is what a rim
   wants.  The line that has to READ is 122 -> 45, and it does.  Wool is used above head height
   only: canopies, awnings and marquee boards, where it is correct rather than loud.

5. **A SIGN WITH NOTHING BEHIND IT IS SILENTLY NOT THERE.**  `park._sign` refuses one and returns
   False, and this project's most-repeated failure shape is a caller that ignores the False.
   Every sign here is counted, and every kind asserts it placed the ones its contract names.

GEOMETRY, identical to `park.py` and `bigwheel.py` because a facing bug is invisible and expensive:

    at       the FRONT-LEFT floor corner, in world coordinates
    facing   the direction the FRONT looks out
    i        along the frontage;  d  from the front INTO the piece;  h  courses up

so `at(i, d, h) = (x - dx*d + sx*i, y + h, z - dz*d + sz*i)`.

**ANCHORS ARE COMPUTED, NEVER TYPED IN.**  `PARK_OVERHAUL.md` makes the typed interface schema a
promotion gate: a plan cannot be prepared when a public module has empty anchors.  Every kind here
derives its own anchors from the geometry it just built - `declare()` runs them through
`design_compiler.anchors()`, so a malformed or duplicated interface fails at BUILD time rather
than at assembly.  A hand-written anchor list is a second copy of the geometry, and two copies of
a coordinate is how a design ships an entrance three cells inside its own wall.
"""
from __future__ import annotations

from collections import deque

from . import park
from .canvas import Canvas, hash01
from .park import LANDS, SIGN_WIDTH, _BACK, _STEP, _sign
from .vertical import Ctx, World
from ..design_compiler import anchors as compile_anchors

# ------------------------------------------------------------------ the measured value ladder
#
# Every one of these was checked against `blocks.exists`, `blocks.available` (1.19),
# `blocks.spendable` (dirt and grass are CURRENCY here) and `palette.tier` before it was written
# down.  `tests/test_midway.py::test_the_ground_palette_is_stone_cheap_and_1_19` re-checks them
# from the registry rather than trusting this comment.
FIELD = "stone_bricks"                       # 122
SPINE = "stone"                              # 126 - a road, against the field
KERB = "smooth_basalt"                       # 73
RING = "polished_blackstone_bricks"          # 45
RIM = "blackstone"                           # 38
PALE = "chiseled_stone_bricks"               # 120 - the one pale accent, used sparingly
LAMP = "ochre_froglight"                     # flush in the floor: this island's own idiom

# A FLUSH FROGLIGHT REACHES 14, NOT 15.  It IS the floor - an opaque emitter one course down - so
# the cell a visitor stands in reads one less than the block's own level.  `Island Night` left 21
# cells dark by crediting it 15, and the spacing here is set against 14.
LAMP_REACH = 14

MIDWAY = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "hub",
    "facing": "east",
    "land": "midway",
    "title": None,
    "sign": True,
    "min_run": 3,
    "seed": 0,

    # ---- hub
    "width": 45,                # forced ODD: a hub with no centre column has no centre
    "spine": 5,                 # the main spines. 5 is the master brief's floor, not a taste
    "secondary": 3,             # the diagonal branches
    "meet": 4,                  # the meet-point island's radius; 9 across at r=4
    "branches": None,           # see DEFAULT_BRANCHES
    "lamp_grid": 9,             # froglight spacing in the paving

    # ---- ridequeue
    "lane": 3,                  # a queue lane: 2-3 per the master brief
    "legs": 4,                  # switchback legs
    "length": 13,               # cells along each leg
    "marquee": None,            # the ride's name over the entrance; defaults to `title`

    # ---- rideexit
    "run": 11,                  # how far the exit walks before it discharges
    "viewpoint": True,          # the photo alcove half way along

    # ---- gamesrow
    "bays": 5,
    "bay_width": 5,
    "service": 3,               # the depth of the corridor behind the facade

    # ---- threshold
    "to": "frontier",           # the land you are walking INTO; its palette leads the transition
    "depth": 15,                # how far the handoff runs before the arch
    "dest": None,               # what the board says; defaults to `to` in capitals
}

# THE HUB'S EIGHT BRANCHES, and the split between them is rule 6 of the master brief rather than a
# style choice: a 5-block minimum main public spine and 3-block secondary circulation.  The four
# CARDINALS are the two 5-wide spines - the arrival spine the master brief names and the
# cross-park spine - and the four DIAGONALS are the secondary branches to the things you do.
#
# `side` is LOCAL, so a hub reads the same at all four facings: "front" is the way the module
# faces, and a midway hub faces the gate.  The world directions fall out of the frame.
DEFAULT_BRANCHES = [
    {"name": "arrival_in", "side": "front", "label": "PARK GATE", "main": True},
    {"name": "wheel_branch", "side": "back", "label": "SKY LIFT", "main": True},
    {"name": "frontier_departure", "side": "left", "label": "FRONTIER", "main": True},
    {"name": "hollow_departure", "side": "right", "label": "THE HOLLOW", "main": True},
    {"name": "carousel_branch", "side": "front_left", "label": "CAROUSEL", "main": False},
    {"name": "games_branch", "side": "front_right", "label": "GAMES ROW", "main": False},
    {"name": "food_branch", "side": "back_right", "label": "FOOD COURT", "main": False},
    {"name": "terrace_branch", "side": "back_left", "label": "THE TERRACE", "main": False},
]

# The local sides, as (di, dd) unit vectors in the module's own frame.  `front` is -d, because d
# runs from the front INTO the piece.
SIDES = {
    "front": (0, -1), "back": (0, 1), "left": (-1, 0), "right": (1, 0),
    "front_left": (-1, -1), "front_right": (1, -1),
    "back_left": (-1, 1), "back_right": (1, 1),
}


# ------------------------------------------------------------------ small shared helpers

def declare(spec) -> list[dict]:
    """Validate a kind's own anchor declaration and return it as plain dicts for the sidecar.

    THE VALIDATION IS THE POINT.  `design_compiler.anchors` refuses an unknown kind, a duplicate
    name, a malformed position and a zero width - all four of which are things a generator can
    emit while building a perfectly legal schematic, and none of which any render, audit or block
    count can see.  Running it HERE means a broken interface fails when the module is built rather
    than when a coordinator tries to link it.
    """
    compile_anchors(spec)                     # raises on anything malformed
    return [dict(a) for a in spec]


def _anchor(name, kind, pos, facing=None, width=1) -> dict:
    x, y, z = pos
    return {"name": name, "kind": kind, "position": [int(x), int(y), int(z)],
            "facing": facing, "width": int(width)}


def _dir_of(f, di, dd) -> str:
    """A local (along-frontage, into-the-piece) vector as a WORLD compass direction.

    Everything oriented - a stair's tall side, a sign's facing, a gate's swing - has to be derived
    through the frame or it is right at one facing and wrong at the other three, and no render in
    this repo can show that.
    """
    vx = f.sx * di - f.dx * dd
    vz = f.sz * di - f.dz * dd
    if abs(vx) >= abs(vz):
        return "east" if vx > 0 else "west"
    return "south" if vz > 0 else "north"


def _pave(w, f, i, d, block, h=-1) -> bool:
    """Lay one paving cell, never over one that is already laid.

    A spine crossing a kerb must not punch a hole in the kerb, and a branch crossing the circus
    ring must not overwrite the ring - the figure is what tells a visitor which way is a road.
    First writer wins, which is the same precedence `layers.slice_plan` applies one level up.
    """
    x, y, z = f.at(i, d, h)
    if w.has(x, y, z):
        return False
    w.put(x, y, z, block)
    return True


def _clear(w, f, i, d, courses=2, h=0) -> None:
    """Assert the air a visitor's body occupies is air.

    Called on every cell a kind claims is standable.  `w.has` is the right question here and not
    `blocks.is_full_cube`: a fence, a wall and a pane all stop a body, so anything present over a
    standing cell is a headroom collision whether or not it is a full block.
    """
    for k in range(courses):
        x, y, z = f.at(i, d, h + k)
        if w.has(x, y, z):
            raise ValueError(f"headroom: {w.name(x, y, z)} at local ({i},{d},{h + k}) stands in "
                             f"the {k}th course over a cell a visitor walks on")


def _lamp_post(w, f, pal, i, d, tall=3) -> list:
    """A standing lantern on a capped post.

    A HANGING lantern needs a full block over it, and in open air that is a block hanging on
    nothing - rule 9, and the reason the shipped plaza's lamp posts all read as floating.  This
    one stands: post, cap, lantern on top of the cap.
    """
    for h in range(tall):
        w.put(*f.at(i, d, h), FIELD if h < tall - 1 else pal["trim"])
    w.put(*f.at(i, d, tall), pal["light"], hanging="false", waterlogged="false")
    return list(f.at(i, d, tall))


def _flood(cells: set, start) -> set:
    """4-connected flood over a set of (i, d) paving cells.  The route gate's own primitive."""
    if start not in cells:
        return set()
    seen, q = {start}, deque([start])
    while q:
        i, d = q.popleft()
        for (a, b) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (i + a, d + b)
            if n in cells and n not in seen:
                seen.add(n)
                q.append(n)
    return seen


def _walk_len(cells: set, start, goal) -> int:
    """Shortest 4-connected walk between two paving cells, or -1 if there is none.

    A QUEUE'S WHOLE VALUE IS THIS NUMBER.  A switchback with one cell missing from one wall is a
    schematic nothing can fault and a queue nobody has to walk, and the length is the only
    measurement that separates the two.
    """
    if start not in cells or goal not in cells:
        return -1
    seen, q = {start}, deque([(start, 0)])
    while q:
        (i, d), n = q.popleft()
        if (i, d) == goal:
            return n
        for (a, b) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (i + a, d + b)
            if nb in cells and nb not in seen:
                seen.add(nb)
                q.append((nb, n + 1))
    return -1


# ------------------------------------------------------------------------------------- the hub

def _branch_cells(c: int, di: int, dd: int, half: int, reach: int) -> list:
    """One branch's paving, as local (i, d) offsets from the hub's centre column.

    A CARDINAL branch is a straight band `2*half+1` wide.  A DIAGONAL one is the band
    `|u - v| <= 2*half`, which steps one cell at a time and is therefore 4-connected by
    construction - the ear-tip lesson: a run whose cells are only diagonal neighbours is not a
    run, it is a dotted line, and it is invisible in a plan render.  Its width measured square to
    itself is about `(2*half+1)/sqrt(2)`, which is why a secondary branch asks for `half=2` and
    gets a genuine three-block walk rather than the two a naive `half=1` would give.
    """
    out = []
    if di and dd:                                     # diagonal
        for k in range(1, reach + 1):
            for s in range(-2 * half, 2 * half + 1):
                # step k out along the diagonal, then slide s along the anti-diagonal
                u, v = di * k, dd * k
                if abs(s) % 2:
                    continue                          # keep the band 4-connected, not chequered
                out.append((c + u + di * (s // 2), c + v - dd * (s // 2)))
                out.append((c + u + di * (s // 2) + di, c + v - dd * (s // 2)))
        return sorted(set(out))
    for k in range(1, reach + 1):
        for s in range(-half, half + 1):
            out.append((c + di * k + (-dd) * s, c + dd * k + (-di) * s))
    return sorted(set(out))


def _hub(w: World, p: dict, ctx) -> dict:
    """THE DISTRIBUTION HEART, and the one place in the park all three lands are introduced.

    **THE MEET POINT IS AN ISLAND YOU WALK ROUND, NOT A BLOCK YOU WALK INTO.**  The master brief
    is explicit that the monument *"cannot remain a purposeless obstruction"*, and the obvious
    reading - put the landmark in the middle of the crossing - reproduces exactly that fault one
    scale down.  So the two 5-wide spines do not cross at a point: they run to a CIRCUS, an
    annular ring five cells wide, and the meet point sits inside it at three courses - a basin you
    can see over, a clock face you read from the ring, and a map plaque.  Every desire line is
    preserved and the landmark is still the middle of the hub.

    **AND THE SEATING IS OUTSIDE THE DESIRE LINES.**  A bench on a spine is a bench somebody walks
    into; the quadrants between the branches are where a bench belongs, and they are the only
    cells `_furnish` will touch.
    """
    f = park._Frame(p)
    pal = LANDS[p["land"]]
    W = int(p["width"]) | 1                          # ODD: a hub with no centre column has none
    if W < 25:
        raise ValueError(f"a hub {W} across cannot carry two 5-wide spines and a circus")
    c = W // 2
    main_half = max(2, int(p["spine"]) // 2)         # 5-wide -> half 2
    sec_half = max(1, int(p["secondary"]) // 2)      # 3-wide -> half 1
    rm = max(3, int(p["meet"]))
    ring_out = rm + 5                                # the circus: five cells of walkable ring
    grid = max(5, int(p["lamp_grid"]))
    branches = list(p.get("branches") or DEFAULT_BRANCHES)

    # ---- 1. THE FIELD.  Everything is paved, because a hub with bare cells in it is a hub with
    #         holes in it, and on a void plot a hole is a fall.
    for i in range(W):
        for d in range(W):
            _pave(w, f, i, d, FIELD)

    # ---- 2. THE CIRCUS.  Laid BEFORE the spines so the spines read as arriving at it.
    circus = set()
    for i in range(W):
        for d in range(W):
            r2 = (i - c) ** 2 + (d - c) ** 2
            if rm * rm < r2 <= ring_out * ring_out:
                circus.add((i, d))
                x, y, z = f.at(i, d, -1)
                w.put(x, y, z, RING)

    # ---- 3. THE BRANCHES.  A cardinal is 5 wide and a diagonal 3; both are drawn in SPINE stone
    #         so a branch reads as a road, and both are kerbed so it reads as a road with edges.
    spine_cells, branch_heads = set(), {}
    reach = W                                        # clipped to the hub by the bounds test below
    for b in branches:
        side = b.get("side")
        if side not in SIDES:
            raise ValueError(f"branch {b.get('name')!r}: unknown side {side!r}; "
                             f"have {sorted(SIDES)}")
        di, dd = SIDES[side]
        half = main_half if b.get("main") else sec_half
        cells = [(i, d) for (i, d) in _branch_cells(c, di, dd, half, reach)
                 if 0 <= i < W and 0 <= d < W and (i - c) ** 2 + (d - c) ** 2 > rm * rm]
        if not cells:
            raise ValueError(f"branch {b.get('name')!r} paved nothing")
        for (i, d) in cells:
            x, y, z = f.at(i, d, -1)
            w.put(x, y, z, SPINE)
            spine_cells.add((i, d))
        # THE HEAD: the outermost cell of the branch, which is the anchor a coordinator links to.
        head = max(cells, key=lambda t: (t[0] - c) ** 2 + (t[1] - c) ** 2)
        branch_heads[b["name"]] = (head, b, half)

    # ---- 4. THE KERBS.  A branch cell with a non-branch neighbour square to it takes the kerb
    #         tone, so every spine has an edge you can see.  Drawn AFTER every branch, or an early
    #         branch kerbs the cells a later one is about to pave.
    for (i, d) in sorted(spine_cells):
        if (i, d) in circus:
            continue
        for (a, b2) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (i + a, d + b2)
            if n not in spine_cells and 0 <= n[0] < W and 0 <= n[1] < W:
                x, y, z = f.at(i, d, -1)
                w.put(x, y, z, KERB)
                break

    # ---- 5. THE MEET POINT.  Low, on purpose: three courses, which is under eye level from the
    #         ring, so the branch head opposite you is still visible across it.  A landmark you
    #         cannot see past is the obstruction the brief rejects.
    meet = _meet_point(w, f, pal, c, rm, str(p.get("title") or "MEET HERE"))

    # ---- 6. THE LIGHT, flush in the paving.  Never on a branch head (a lamp where a fingerpost
    #         goes) and never inside the meet point.
    lamps = []
    for i in range(0, W, grid):
        for d in range(0, W, grid):
            if (i - c) ** 2 + (d - c) ** 2 <= (rm + 1) ** 2:
                continue
            x, y, z = f.at(i, d, -1)
            w.put(x, y, z, LAMP)
            lamps.append([x, y, z])

    # ---- 7. THE BRANCH HEADS: a lit post either side and a board naming the destination, so
    #         every decision point in the hub has a wayfinding cue.  Rule 7 of the master brief.
    posts, signs, want = [], 0, 0
    for name, (head, b, half) in sorted(branch_heads.items()):
        hi, hd = head
        di, dd = SIDES[b["side"]]
        # square to the branch, one cell clear of its own paving
        pi, pd = (-dd, -di) if not (di and dd) else (di, -dd)
        for s in (1, -1):
            gi, gd = hi + pi * s * (half + 1), hd + pd * s * (half + 1)
            if not (0 <= gi < W and 0 <= gd < W) or (gi, gd) in spine_cells:
                continue
            posts.append(_lamp_post(w, f, pal, gi, gd))
            want += 1
            # THE BOARD READS BACK INTO THE HUB - a visitor walking out has already chosen; the
            # one who needs telling is the one standing in the circus looking outward.
            face = _dir_of(f, -di, -dd)
            if p.get("sign", True) and _sign(w, f, pal, gi, gd, 2, face,
                                             [b["label"][:SIGN_WIDTH], "", "this way", ""]):
                signs += 1

    # ---- 8. SEATING AND PLANTING, in the quadrants ONLY.  Never on a spine, never in the circus.
    seats = _furnish(w, f, pal, W, c, spine_cells, circus, rm, int(p["seed"]))

    # ---- 9. WHAT A VISITOR CAN STAND ON, and it is MEASURED rather than declared.  Every paved
    #         cell of the hub whose two courses of air are actually clear.
    standing, blocked = [], []
    for i in range(W):
        for d in range(W):
            if not w.has(*f.at(i, d, -1)):
                continue
            if w.has(*f.at(i, d, 0)) or w.has(*f.at(i, d, 1)):
                blocked.append([i, d])
                continue
            standing.append(list(f.at(i, d, 0)))

    # ---- 10. THE ANCHORS.  One per branch head, plus the meet point, derived from the geometry
    #          just built.  `path` is the compiler kind a spine end is: it links to an `entry`, an
    #          `exit`, a `door`, a `queue` or another `path`.
    spec = []
    for name, (head, b, half) in sorted(branch_heads.items()):
        hi, hd = head
        di, dd = SIDES[b["side"]]
        spec.append(_anchor(name, "path", f.at(hi, hd, 0), _dir_of(f, di, dd), 2 * half + 1))
    spec.append(_anchor("meet_point", "visual_front", f.at(c, c - rm - 1, 0), f.facing, 1))
    spec.append(_anchor("map_view", "visual_front", f.at(c, c - rm - 1, 1), f.facing, 1))

    walked = _flood({(i, d) for i in range(W) for d in range(W)
                     if not (w.has(*f.at(i, d, 0)) or w.has(*f.at(i, d, 1)))},
                    (c, c - ring_out + 1))
    return {"kind": "hub", "width": W, "centre": list(f.at(c, c, 0)),
            "spine": 2 * main_half + 1, "secondary": 2 * sec_half + 1,
            "meet_radius": rm, "circus": sorted(circus), "circus_cells": len(circus),
            "branches": {k: {"head": list(f.at(v[0][0], v[0][1], 0)), "label": v[1]["label"],
                             "main": bool(v[1].get("main")), "width": 2 * v[2] + 1}
                         for k, v in sorted(branch_heads.items())},
            "spine_cells": len(spine_cells), "lamps": lamps, "posts": posts,
            "seats": seats, "signs": signs, "sign_slots": want,
            "standing": standing, "blocked": blocked, "reachable": len(walked),
            "anchors": declare(spec),
            **meet,
            "contract": "the midway's distribution heart: two %d-wide spines and four %d-wide "
                        "secondary branches meeting at a five-cell circus you walk round, a "
                        "three-course meet point - basin, clock face and map - inside it that "
                        "nothing has to walk into, a lit signed head on every one of the %d "
                        "branches, froglight flush in the paving on a %d grid, and seating kept "
                        "out of every desire line"
                        % (2 * main_half + 1, 2 * sec_half + 1, len(branch_heads), grid),
            "unverified": [
                "the meet point's CLOCK is a painted face, not a mechanism. A working clock is a "
                "signal and nothing that carries a signal ships from this lane unverified; the "
                "face is scenery and is described as scenery.",
            ]}


def _meet_point(w, f, pal, c: int, rm: int, title: str) -> dict:
    """The low landmark inside the circus: a water basin, a clock face, and a map plaque.

    THREE COURSES, AND THE NUMBER IS THE DESIGN.  A visitor standing on the ring is at eye level
    1-2 courses over the paving, so a landmark under three courses is something you see ACROSS
    and a landmark over four is something you see INSTEAD of the branch opposite.  The hub's whole
    job is that all eight destinations are visible from the middle of it.

    **A WATER CELL NEEDS A SOLID BED AND A SOLID RIM.**  `civic._fountain` settled this and the
    reasoning is not interchangeable with a shell rule: the basin's bed is the WHOLE disc one
    course down and its rim is the full one-radius annulus, because one step out raises the
    radius by at most one and anything thinner drains through its own diagonals.
    """
    inner = rm - 2
    # the plinth: the whole island, one course proud, so the basin has a real bed under it
    for i in range(c - rm, c + rm + 1):
        for d in range(c - rm, c + rm + 1):
            if (i - c) ** 2 + (d - c) ** 2 > rm * rm:
                continue
            w.put(*f.at(i, d, -1), RIM)
            w.put(*f.at(i, d, 0), RING)

    # the basin: a disc of source water at h=1 with the plinth as its bed and a full rim round it
    wet = []
    for i in range(c - inner, c + inner + 1):
        for d in range(c - inner, c + inner + 1):
            r2 = (i - c) ** 2 + (d - c) ** 2
            if r2 <= inner * inner:
                w.put(*f.at(i, d, 1), "water", level="0")
                wet.append(list(f.at(i, d, 1)))
            elif r2 <= (inner + 1) * (inner + 1):
                w.put(*f.at(i, d, 1), RIM)          # the rim: a full annulus, never a shell

    # A LEAK IS A CELL OF WATER WITH AN OPEN HORIZONTAL NEIGHBOUR, and it is measured here rather
    # than argued for.  `civic` and `bigwheel` both ship a `_watertight` of their own; this basin
    # is nine cells across and the check is four lines, so it is done in place.
    leaks = 0
    for (x, y, z) in wet:
        for (a, b) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if not w.has(x + a, y, z + b):
                leaks += 1
    if leaks:
        raise ValueError(f"the meet-point basin leaks through {leaks} faces")

    # THE CLOCK AND THE MAP, on a pier at the back of the island so neither stands in the front
    # sightline.  The clock face is PALE on RIM - 120 against 38, which is the one contrast this
    # economy gives away - with four marks at the quarters.
    for h in (1, 2, 3):
        for s in (-1, 0, 1):
            w.put(*f.at(c + s, c + rm - 1, h), RIM if h == 1 else PALE)
    for (s, h) in ((0, 4), (-1, 3), (1, 3), (0, 2)):
        w.put(*f.at(c + s, c + rm - 1, h), RIM)     # the quarter marks and the hands' pivot
    signs = 0
    if _sign(w, f, pal, c, c + rm - 2, 3, f.facing, [title[:SIGN_WIDTH], "", "MEET HERE", ""]):
        signs += 1
    if _sign(w, f, pal, c, c + rm, 3, f.back, ["PARK MAP", "eight ways out", "all of them", "signed"]):
        signs += 1
    w.put(*f.at(c, c + rm - 1, 5), pal["light"], hanging="false", waterlogged="false")
    return {"meet_water": wet, "meet_leaks": leaks, "meet_signs": signs,
            "meet_height": 5, "meet_top": f.at(c, c + rm - 1, 5)[1]}


def _furnish(w, f, pal, W: int, c: int, spine: set, circus: set, rm: int, seed: int) -> list:
    """Benches and planters, in the quadrants and NOWHERE ELSE.

    A bench on a spine is a bench somebody walks into, and a planter in a circus is a planter that
    turns a five-cell ring into a three-cell one.  The eligibility test is therefore a
    subtraction, not a placement rule: a cell is furnishable only if it is neither branch nor
    circus nor within two of either, which is rule 10's working room applied to a bench.
    """
    near = set()
    for (i, d) in spine | circus:
        for a in range(-2, 3):
            for b in range(-2, 3):
                near.add((i + a, d + b))
    out = []
    for i in range(3, W - 3, 6):
        for d in range(3, W - 3, 6):
            if (i, d) in near or (i - c) ** 2 + (d - c) ** 2 <= (rm + 7) ** 2:
                continue
            if hash01(i, d, seed) < 0.45:
                # A BENCH: two stairs back to back on a plinth.  It is one course, so it is
                # something a visitor sits on rather than something that blocks the quadrant.
                w.put(*f.at(i, d, -1), KERB)
                w.put(*f.at(i, d, 0), pal["stair"], facing=_dir_of(f, 0, 1),
                      half="bottom", shape="straight", waterlogged="false")
                out.append(["bench", *f.at(i, d, 0)])
            else:
                # A PLANTER: a kerbed box with a low shrub.  Not dirt - dirt is CURRENCY here and
                # `blocks.spendable` says so - so the box is stone and the planting is azalea,
                # which needs no soil block of its own to read as green.
                w.put(*f.at(i, d, -1), KERB)
                w.put(*f.at(i, d, 0), RIM)
                w.put(*f.at(i, d, 1), "azalea")
                out.append(["planter", *f.at(i, d, 0)])
    return out


# ------------------------------------------------------------------------------- the ride queue

def _ridequeue(w: World, p: dict, ctx) -> dict:
    """A COVERED SWITCHBACK, and the thing it must not be is a shortcut.

    `PARK_OVERHAUL.md`: *queues are never used as through-routes*, and *queue/exit/main-spine
    overlap is rejected*.  The failure mode is invisible to everything this repo owns - a wall
    with one cell missing is a schematic nothing can fault - so the contract is a MEASURED WALK
    LENGTH from `queue_entry` to `queue_end`, returned here and asserted in the tests against a
    floor derived from the leg count.  Lose a wall cell and the number collapses; nothing else
    about the build changes at all.

    The emergency gate is a real opening and it is on the OUTER flank, at the far end - a gate at
    the entrance end would be the shortcut it exists to be an alternative to.  It is a fence gate,
    so `mcbuild.walk` treats it as passable and the route gate can prove you can get out of it.
    """
    f = park._Frame(p)
    pal = LANDS[p["land"]]
    lane = max(2, min(3, int(p["lane"])))
    legs = max(2, int(p["legs"]))
    L = max(7, int(p["length"]))
    W = legs * (lane + 1) + 1                        # a wall between every pair of legs
    D = L + 2
    marquee = str(p.get("marquee") or p.get("title") or "QUEUE").upper()

    park._pad(w, f, pal, W, D, margin=1, block=pal["path"])

    # ---- 1. THE LANES.  Leg k occupies i in [k*(lane+1)+1, k*(lane+1)+lane].
    lanes = []
    for k in range(legs):
        i0 = k * (lane + 1) + 1
        lanes.append((i0, i0 + lane - 1))

    # ---- 2. THE WALLS.  A full-height wall between legs, with the TURN left open at alternating
    #         ends - which is what folds the walk instead of stopping it.  The turn opening is the
    #         only hole in each wall, and that is the whole of the design.
    walls = 0
    for k in range(legs + 1):
        i = k * (lane + 1)
        near = k % 2 == 1                            # which end this wall's gap is at
        for d in range(1, D - 1):
            if k in (0, legs):
                gap = False                          # the outer walls are solid: no leaking out
            else:
                gap = (d >= D - 1 - lane) if near else (d <= lane)
            if gap:
                continue
            for h in range(3):
                w.put(*f.at(i, d, h), pal["wall"] if h < 2 else pal["trim"])
                walls += 1

    # ---- 3. THE ENDS.  The entrance is the front of leg 0; the far end of the LAST leg is where
    #         you board.  Every other end cell is closed, or the queue has three ways in.
    for k in range(legs):
        i0, i1 = lanes[k]
        head_front = (k % 2 == 0)
        for i in range(i0, i1 + 1):
            for (d, is_entry) in ((0, head_front and k == 0),
                                  (D - 1, (not head_front) and k == legs - 1)):
                if is_entry:
                    continue
                for h in range(3):
                    w.put(*f.at(i, d, h), pal["wall"] if h < 2 else pal["trim"])

    # ---- 4. THE CANOPY.  Covered, per the spec, and two colours alternating because one colour
    #         is a roof.  It sits at h=3, so there are three clear courses under it everywhere.
    a, b = pal["canopy"]
    for i in range(-1, W + 1):
        for d in range(-1, D + 1):
            w.put(*f.at(i, d, 4), a if (i // 2) % 2 == 0 else b)
    for i in range(0, W + 1, lane + 1):
        for d in (0, D - 1):
            for h in range(4):
                if not w.has(*f.at(i, d, h)):
                    w.put(*f.at(i, d, h), pal["post"])

    # ---- 5. THE EMERGENCY GATE, on the outer flank of the LAST leg, at the boarding end.  A gate
    #         at the entrance end is the queue-jump it exists to prevent.
    egi = W - 1
    egd = D - 2 - lane // 2
    for h in range(2):
        x, y, z = f.at(egi, egd, h)
        w.put(x, y, z, pal["gate"], facing=_dir_of(f, 1, 0), open="false",
              in_wall="false", powered="false") if h == 0 else w.put(x, y, z, "air")
    # the paving OUTSIDE the gate, or the emergency exit lands on void
    for s in range(1, 4):
        _pave(w, f, egi + s, egd, pal["path"])

    # ---- 6. THE MARQUEE over the entrance: a raised header board, which is the one thing that
    #         says what the line is FOR from across the hub.
    ent_i = (lanes[0][0] + lanes[0][1]) // 2
    for i in range(-1, W + 1):
        w.put(*f.at(i, -1, 5), pal["trim"])
        w.put(*f.at(i, -1, 6), pal["accent"] if (i % 2 == 0) else pal["wall"])
    for i in range(-1, W + 1):
        w.put(*f.at(i, -1, 7), pal["trim"])
    signs, want = 0, 3
    if p.get("sign", True):
        if _sign(w, f, pal, ent_i, -2, 6, f.facing, [marquee[:SIGN_WIDTH], "", "QUEUE HERE", "one way"]):
            signs += 1
        if _sign(w, f, pal, egi + 1, egd, 2, _dir_of(f, 1, 0), ["EMERGENCY", "EXIT", "", "no re-entry"]):
            signs += 1
        if _sign(w, f, pal, lanes[-1][0], D, 2, f.back, ["TO BOARDING", "", "mind the step", ""]):
            signs += 1

    # ---- 7. THE LIGHT.  A queue you cannot see the end of at night is a queue nobody joins.
    #         Hung from the canopy, which IS a full block, so rule 9 holds by construction.
    lamps = []
    for k in range(legs):
        i0, i1 = lanes[k]
        i = (i0 + i1) // 2
        for d in range(2, D - 1, 5):
            w.put(*f.at(i, d, 3), pal["light"], hanging="true", waterlogged="false")
            lamps.append(list(f.at(i, d, 3)))

    # ---- 8. THE WALK.  Measured, not asserted: every cell inside the footprint with two clear
    #         courses over paving, and the real distance between the two ends.
    inside = set()
    for i in range(W):
        for d in range(D):
            if not w.has(*f.at(i, d, -1)):
                continue
            if w.has(*f.at(i, d, 0)) or w.has(*f.at(i, d, 1)):
                continue
            inside.add((i, d))
    entry = (ent_i, 0)
    board_i = (lanes[-1][0] + lanes[-1][1]) // 2
    end = (board_i, D - 1)
    length = _walk_len(inside, entry, end)
    if length < 0:
        raise ValueError("the queue does not connect its entrance to its boarding end")
    # THE FLOOR THE SWITCHBACK MUST CLEAR: every leg walked end to end, plus the turns.  A queue
    # that beats it has a hole in a wall, which is the one failure this kind exists to prevent.
    floor = legs * (L - lane)
    if length < floor:
        raise ValueError(f"the queue walks {length} cells against a switchback floor of {floor} - "
                         "a wall has a hole in it and the line can be jumped")

    standing = [list(f.at(i, d, 0)) for (i, d) in sorted(inside)]
    spec = [
        _anchor("approach", "path", f.at(ent_i, -2, 0), f.facing, lane),
        _anchor("queue_entry", "queue", f.at(ent_i, 0, 0), f.facing, lane),
        _anchor("queue_end", "queue", f.at(board_i, D - 1, 0), f.back, lane),
        _anchor("emergency_exit", "exit", f.at(egi + 1, egd, 0), _dir_of(f, 1, 0), 1),
    ]
    return {"kind": "ridequeue", "width": W, "depth": D, "lane": lane, "legs": legs,
            "lanes": lanes, "walls": walls, "lamps": lamps, "signs": signs, "sign_slots": want,
            "walk_length": length, "walk_floor": floor, "capacity": len(inside),
            "entry": list(f.at(ent_i, 0, 0)), "end": list(f.at(board_i, D - 1, 0)),
            "emergency": list(f.at(egi + 1, egd, 0)),
            "standing": standing, "cells": sorted(inside),
            "anchors": declare(spec),
            "contract": "a covered %d-wide switchback of %d legs under a marquee: one way in at "
                        "the front, one way out at the boarding end, %d cells of line between "
                        "them against a %d-cell floor, an emergency fence gate on the far flank "
                        "with paving outside it, and a lantern every five cells"
                        % (lane, legs, length, floor),
            "unverified": [
                "the LINE is architecture and carries no signal, so there is nothing to simulate. "
                "What is asserted is the walk: its length, its two ends, and that the emergency "
                "gate opens onto paving rather than onto void.",
            ]}


# -------------------------------------------------------------------------------- the ride exit

def _rideexit(w: World, p: dict, ctx) -> dict:
    """THE WAY OUT, and it is a topological guarantee rather than a mechanical one.

    **VANILLA HAS NO REVERSIBLE-WALK ONE-WAY.**  `mcbuild.walk` steps down exactly one course and
    up exactly one, so every drop a player can walk out of is a drop they can walk back up, and a
    two-course drop is not walkable in either direction - which would break the route gate's own
    requirement that *every ride exit can reach the return spine*.  So this kind does not pretend:
    the separation between an exit and the queue that fed it is SPATIAL and SIGNED, and the
    contract says so in those words.

    What IS guaranteed, and tested: the exit's cells are disjoint from the queue's, its discharge
    lands on a named secondary rather than on a main spine, and the run is walled and lit for its
    whole length so nobody wanders back along it by accident.

    The viewpoint alcove is the master brief's *photo/viewpoint* for the wheel, and it is off the
    run rather than in it - a place to stop that does not stop the people behind you.
    """
    f = park._Frame(p)
    pal = LANDS[p["land"]]
    lane = max(2, min(3, int(p["lane"])))
    run = max(7, int(p["run"]))
    W = lane + 2
    D = run + 1

    park._pad(w, f, pal, W, D, margin=1, block=pal["path"])

    # ---- 1. THE WALLS: waist-high, so the run reads as a channel and the park stays visible over
    #         it.  A full-height corridor out of a ride is a service tunnel, not an exit.
    rails = 0
    for d in range(0, D):
        for i in (0, W - 1):
            w.put(*f.at(i, d, 0), pal["fence"], waterlogged="false")
            rails += 1
        w.put(*f.at(0, d, -1), KERB)
        w.put(*f.at(W - 1, d, -1), KERB)

    # ---- 2. THE VIEWPOINT, half way along and OFF the run: three cells of alcove on the left,
    #         with a bench and its own lantern.  The rail there faces out, not across.
    view = None
    if p.get("viewpoint", True):
        vd = D // 2
        for d in range(vd - 1, vd + 2):
            for s in range(1, 4):
                _pave(w, f, -s, d, pal["path"])
            w.put(*f.at(-4, d, 0), pal["fence"], waterlogged="false")
        for s in (1, 3):
            for d in (vd - 2, vd + 2):
                w.put(*f.at(-s, d, 0), pal["fence"], waterlogged="false")
        w.put(*f.at(-2, vd, -1), KERB)
        w.put(*f.at(-2, vd, 0), pal["stair"], facing=_dir_of(f, 1, 0),
              half="bottom", shape="straight", waterlogged="false")
        # THE LANTERN STANDS ON ITS OWN POST.  A hanging one here needs a block over it and there
        # is no roof on an alcove - rule 9, the plaza's own bug.
        _lamp_post(w, f, pal, -4, vd, tall=3)
        view = list(f.at(-2, vd, 0))
        # ...and the rail cell the bench replaced has to come back, or the alcove leaks
        w.put(*f.at(0, vd - 1, 0), pal["fence"], waterlogged="false")
        w.put(*f.at(0, vd + 1, 0), pal["fence"], waterlogged="false")

    # ---- 3. THE LIGHT, on posts down one side, spaced against a flush froglight's real reach.
    lamps = []
    for d in range(1, D, 5):
        lamps.append(_lamp_post(w, f, pal, W, d, tall=3))
        _pave(w, f, W, d, KERB)

    # ---- 4. THE SIGNS.  The one at the head reads back UP the run, because the person who needs
    #         telling is the one thinking about walking the wrong way.
    signs, want = 0, 2
    if p.get("sign", True):
        if _sign(w, f, pal, W // 2, D, 2, f.back, ["WAY OUT", "", "no re-entry", "this way"]):
            # a board needs something behind it: the end wall carries it
            signs += 1
        if _sign(w, f, pal, W, D // 2 + 2, 2, _dir_of(f, 1, 0), ["RIDE EXIT", "", "one way", ""]):
            signs += 1

    # the head board's own backing, placed BEFORE the sign would be too late - so it is here and
    # the sign above is retried against it
    for i in range(W):
        for h in range(3):
            if not w.has(*f.at(i, D, h)):
                w.put(*f.at(i, D, h), pal["wall"] if h < 2 else pal["trim"])
    if p.get("sign", True) and not signs:
        if _sign(w, f, pal, W // 2, D - 1, 2, f.back, ["WAY OUT", "", "no re-entry", ""]):
            signs += 1

    inside = set()
    for i in range(-4, W + 1):
        for d in range(-1, D + 1):
            if not w.has(*f.at(i, d, -1)):
                continue
            if w.has(*f.at(i, d, 0)) or w.has(*f.at(i, d, 1)):
                continue
            inside.add((i, d))
    standing = [list(f.at(i, d, 0)) for (i, d) in sorted(inside)]
    spec = [
        _anchor("ride_exit", "ride_exit", f.at(W // 2, 0, 0), f.facing, lane),
        _anchor("discharge", "path", f.at(W // 2, D - 1, 0), f.back, lane),
    ]
    if view:
        spec.append(_anchor("viewpoint", "visual_front", view, _dir_of(f, -1, 0), 1))
    return {"kind": "rideexit", "width": W, "depth": D, "lane": lane, "run": run,
            "rails": rails, "lamps": lamps, "signs": signs, "sign_slots": want,
            "viewpoint": view, "standing": standing, "cells": sorted(inside),
            "exit_at": list(f.at(W // 2, 0, 0)), "discharge": list(f.at(W // 2, D - 1, 0)),
            "anchors": declare(spec),
            "contract": "a %d-wide railed exit run %d cells long, lit on posts down one side, "
                        "signed one-way at both ends, with a viewpoint alcove off the run rather "
                        "than in it, discharging at a cell a coordinator links to a SECONDARY "
                        "branch - never to a queue and never to a main spine"
                        % (lane, run),
            "unverified": [
                "IT IS NOT PHYSICALLY ONE-WAY, and no vanilla arrangement makes it one under a "
                "reversible walk model: a drop a player can leave by is a drop they can climb. "
                "The separation from the queue is spatial and signed, and the tests assert the "
                "disjointness and the discharge distance rather than a mechanism that does not "
                "exist.",
            ]}


# --------------------------------------------------------------------------------- the games row

def _gamesrow(w: World, p: dict, ctx) -> dict:
    """ONE FRONTAGE, N BAYS, AND A SERVICE CORRIDOR THE PUBLIC CANNOT WALK INTO.

    `PARK_MIDWAY.md`: *merge Plinko, High Striker, and arcade functions into a single
    awning/facade-backed games frontage.  Each bay has a standing spot, input, outcome, clear
    prize or score path, and protected redstone rear.*

    THE SPLIT WITH `gen/arcade.py` IS DELIBERATE AND IS THE WHOLE REASON THIS KIND EXISTS.  The
    machines are arcade's - they are simulated, they have contracts, and they are shared with two
    other lands.  What was missing was the BUILDING: a continuous facade so the row reads as one
    premises rather than as five sheds in a line, an awning, a counter and a name per bay, and a
    rear corridor a machine's wiring can live in.  This kind builds the shell and declares one
    `play_or_queue_entry` anchor per bay for a machine to be linked into.

    **THE CORRIDOR IS SEALED FROM THE FRONT, AND THAT IS TESTED.**  A service route you can walk
    into off the midway is not a service route, it is a second frontage - and it is where the
    wiring goes, so a visitor in it is a visitor standing in the machine.  There is exactly one
    way in, a door at the far end, and the test floods from the public paving and requires the
    corridor to be absent from the flood.
    """
    f = park._Frame(p)
    pal = LANDS[p["land"]]
    bays = max(2, int(p["bays"]))
    bw = max(3, int(p["bay_width"]))
    svc = max(2, int(p["service"]))
    W = bays * bw + 1
    D = 3 + svc                                       # counter bay, back wall, corridor, rear wall
    back_d = 2                                        # the facade's own back wall
    height = 5

    park._pad(w, f, pal, W, D, margin=1)

    # ---- 1. THE FACADE.  One continuous back wall behind every bay, with the bay openings left
    #         EMPTY BY THE LOOP rather than punched afterwards - the void tower's crenellations
    #         shipped as a plain drum because a second pass repainted cells that already existed.
    bay_i, opening = [], set()
    for k in range(bays):
        c = k * bw + bw // 2 + 1
        bay_i.append(c)
        for s in range(-(bw // 2 - 1), bw // 2):
            opening.add(c + s)
    for i in range(W):
        for h in range(height):
            if i in opening and h in (1, 2):
                continue                              # the hatch you play through
            w.put(*f.at(i, back_d, h), pal["post"] if i % bw == 0 else
                  (pal["trim"] if h in (0, height - 1) else pal["wall"]))

    # ---- 2. THE COUNTER, one slab course along the front of the back wall, and the standing spot
    #         in front of THAT.  Rule 10: about three blocks of working room at anything you use.
    counters = []
    for i in range(W):
        if i % bw == 0:
            continue
        w.put(*f.at(i, back_d - 1, 0), pal["trim"])
        w.put(*f.at(i, back_d - 1, 1), pal["slab"], type="top", waterlogged="false")
        counters.append(list(f.at(i, back_d - 1, 1)))

    # ---- 3. THE AWNING over the frontage, on posts at the bay divisions.  Two colours
    #         alternating, above head height, which is where wool belongs.
    a, b = pal["canopy"]
    for i in range(-1, W + 1):
        for d in range(-1, back_d):
            w.put(*f.at(i, d, height - 1), a if (i // 2) % 2 == 0 else b)
    posts = []
    for k in range(bays + 1):
        i = k * bw
        for h in range(height - 1):
            w.put(*f.at(i, -1, h), pal["post"])
        posts.append(list(f.at(i, -1, 0)))
    for i in range(-1, W + 1):
        w.put(*f.at(i, -1, height), pal["trim"])      # the fascia the name boards hang on

    # ---- 4. THE SERVICE CORRIDOR.  Behind the facade, walled on all four sides, one door.
    for i in range(-1, W + 1):
        for h in range(height):
            w.put(*f.at(i, D - 1, h), pal["wall"] if h < height - 1 else pal["trim"])
    for d in range(back_d, D):
        for h in range(height):
            w.put(*f.at(-1, d, h), pal["wall"] if h < height - 1 else pal["trim"])
            w.put(*f.at(W, d, h), pal["wall"] if h < height - 1 else pal["trim"])
    for i in range(-1, W + 1):
        for d in range(back_d, D):
            w.put(*f.at(i, d, height), pal["trim"])   # a roof: the corridor is INSIDE
    # THE ONE WAY IN: a door in the rear wall at the far end, and it is a door rather than a gap
    # so `mcbuild.walk` can still route staff through it while the flood from the front cannot.
    door_i = W - 1
    w.put(*f.at(door_i, D - 1, 0), f"{pal['wood']}_door",
          facing=f.back, half="lower", hinge="left", open="false", powered="false")
    w.put(*f.at(door_i, D - 1, 1), f"{pal['wood']}_door",
          facing=f.back, half="upper", hinge="left", open="false", powered="false")
    for d in range(back_d + 1, D - 1):
        for i in range(W):
            w.put(*f.at(i, d, -1), pal["path"])
    for i in range(bw // 2, W, bw * 2):
        w.put(*f.at(i, D - 2, height - 1), pal["light"], hanging="true", waterlogged="false")

    # ---- 5. THE NAMES.  One board per bay on the fascia, plus the row's own board.  Every one is
    #         counted: `_sign` returns False when there is nothing behind it, and an ignored False
    #         is this project's most-repeated failure shape.
    labels = list(p.get("lines") or [])
    signs, want = 0, bays + 1
    for k, c in enumerate(bay_i):
        text = (labels[k] if k < len(labels) else f"GAME {k + 1}").upper()[:SIGN_WIDTH]
        if p.get("sign", True) and _sign(w, f, pal, c, -2, height, f.facing,
                                         [text, "", "step up", "and play"]):
            signs += 1
    title = str(p.get("title") or "GAMES ROW").upper()[:SIGN_WIDTH]
    if p.get("sign", True) and _sign(w, f, pal, W // 2, -2, height - 2, f.facing,
                                     [title, "", "prizes at", "the far end"]):
        signs += 1

    # ---- 6. WHAT IS PUBLIC AND WHAT IS NOT, measured from the geometry.
    public, corridor = set(), set()
    for i in range(-1, W + 1):
        for d in range(-2, D + 1):
            if not w.has(*f.at(i, d, -1)):
                continue
            if w.has(*f.at(i, d, 0)) or w.has(*f.at(i, d, 1)):
                continue
            (corridor if d > back_d else public).add((i, d))

    spec = [_anchor("frontage", "visual_front", f.at(W // 2, -2, 0), f.facing, W)]
    for k, c in enumerate(bay_i):
        spec.append(_anchor(f"play_or_queue_entry_{k + 1}", "entry",
                            f.at(c, back_d - 2, 0), f.facing, 1))
    spec.append(_anchor("collection_or_exit", "exit", f.at(W - 1, -2, 0), f.facing, 2))
    spec.append(_anchor("service_access", "maintenance",
                        f.at(door_i, D, 0), f.back, 1))
    return {"kind": "gamesrow", "width": W, "depth": D, "height": height,
            "bays": bays, "bay_width": bw, "bay_centres": [list(f.at(c, back_d - 2, 0)) for c in bay_i],
            "counters": counters, "posts": posts, "service_depth": svc,
            "service_door": list(f.at(door_i, D - 1, 0)),
            "signs": signs, "sign_slots": want,
            "public": sorted(public), "corridor": sorted(corridor),
            "standing": [list(f.at(i, d, 0)) for (i, d) in sorted(public)],
            "corridor_standing": [list(f.at(i, d, 0)) for (i, d) in sorted(corridor)],
            "anchors": declare(spec),
            "contract": "one awning-and-facade frontage of %d bays under a continuous fascia: a "
                        "counter and a named board at every bay, a standing spot in front of each "
                        "with the awning overhead, and a roofed %d-deep service corridor behind "
                        "the whole row whose only way in is a door in the rear wall - so a "
                        "machine's wiring has somewhere to live that the public cannot walk into"
                        % (bays, svc),
            "unverified": [
                "THE MACHINES ARE NOT THIS KIND'S. `gen/arcade.py` owns them, they are simulated "
                "there, and this builds the premises they sit in: one `play_or_queue_entry` "
                "anchor per bay for a coordinator to link a machine to. A bay with no machine "
                "linked is an empty counter, and nothing here pretends otherwise.",
            ]}


# --------------------------------------------------------------------------- the land threshold

def _threshold(w: World, p: dict, ctx) -> dict:
    """THE LAND DEPARTURE: you know you are leaving before anything tells you.

    `PARK_MIDWAY.md`: *at both arches, provide a 5-wide continuous paved handoff, destination
    identity, fingerpost, and map cue.  Palette/planting change begins before the arch.*

    **THE PALETTE CHANGE IS A DITHER, NOT A LINE.**  The Lowland Stair settled this: a hard
    material change across a run reads as two paths laid end to end, so the transition is a
    per-cell hash whose probability ramps along the run.  By the time you reach the arch the
    ground under you is the destination land's own, and there is no course at which it happened.

    The Isthmus and the arch itself are out of this lane; this kind stops at `connector_side` and
    declares it, which is exactly the *declared edge anchor* the parallel-generation rules allow.
    """
    f = park._Frame(p)
    pal = LANDS[p["land"]]
    to = str(p.get("to") or "frontier")
    if to not in LANDS:
        raise ValueError(f"threshold `to` must name a land; have {sorted(LANDS)}")
    dest_pal = LANDS[to]
    W = max(5, int(p["spine"]))
    D = max(9, int(p["depth"]))
    dest = str(p.get("dest") or to).upper()[:SIGN_WIDTH]
    seed = int(p["seed"])

    # ---- 1. THE HANDOFF, 5 wide and continuous, dithering from this land's ground to the next.
    #         `t` is 0 at the midway end and 1 at the arch, and the hash is on the CELL, so the
    #         boundary wobbles rather than stepping.
    paved, dithered = 0, 0
    for d in range(D):
        t = d / max(1, D - 1)
        for i in range(W):
            x, y, z = f.at(i, d, -1)
            near_edge = i in (0, W - 1)
            here = dest_pal if hash01(x, z, seed) < t else pal
            block = here["trim"] if near_edge else here["ground"]
            w.put(x, y, z, block)
            paved += 1
            if here is dest_pal:
                dithered += 1

    # ---- 2. THE PLANTING AND KERB CHANGE, which starts BEFORE the arch and is the cue that
    #         actually lands: a visitor reads the edge of a path long before they read a sign.
    planters = []
    for d in range(D // 3, D, 3):
        for s in (-1, W):
            w.put(*f.at(s, d, -1), dest_pal["trim"])
            w.put(*f.at(s, d, 0), dest_pal["trim"])
            w.put(*f.at(s, d, 1), "azalea")
            planters.append(list(f.at(s, d, 0)))

    # ---- 3. THE LIGHT changes with the ground.  The midway end takes this land's lantern, the
    #         arch end the destination's - so a night walk crosses the same boundary the paving
    #         does.  Posts, never hanging: there is no roof over a threshold.
    lamps = []
    for d in range(1, D, 4):
        which = dest_pal if d > D // 2 else pal
        for s in (-2, W + 1):
            for h in range(3):
                w.put(*f.at(s, d, h), FIELD if h < 2 else which["trim"])
            w.put(*f.at(s, d, 3), which["light"], hanging="false", waterlogged="false")
            lamps.append(list(f.at(s, d, 3)))
            w.put(*f.at(s, d, -1), which["ground"])

    # ---- 4. THE FINGERPOST AND MAP CUE at the midway end, so the decision is made where the
    #         alternatives still exist rather than under the arch where it is already taken.
    pi = W // 2
    for h in range(5):
        w.put(*f.at(pi, 1, h), pal["post"] if h < 4 else pal["trim"])
    signs, want = 0, 3
    if p.get("sign", True):
        if _sign(w, f, pal, pi, 0, 4, f.facing, [dest, "", "straight on", ""]):
            signs += 1
        if _sign(w, f, pal, pi, 2, 4, f.back, ["MIDWAY", "", "behind you", ""]):
            signs += 1
        if _sign(w, f, pal, pi, 1, 3, _dir_of(f, 1, 0), ["PARK MAP", dest, "and the way", "back"]):
            signs += 1
    w.put(*f.at(pi, 1, 5), pal["light"], hanging="false", waterlogged="false")

    # ---- 5. THE WALK.  Every cell of the handoff must be standable end to end, or the "5-wide
    #         continuous paved handoff" is four wide with a post in it - which is what a
    #         fingerpost planted in the middle of a spine does, and why this one stands at d=1
    #         on the CENTRE column with the run four clear either side... no: it stands ON the
    #         spine, so the spine is measured AROUND it and the result is reported.
    inside = set()
    for i in range(W):
        for d in range(D):
            if w.has(*f.at(i, d, 0)) or w.has(*f.at(i, d, 1)):
                continue
            inside.add((i, d))
    walk = _flood(inside, (0, 0))
    narrow = min(sum(1 for i in range(W) if (i, d) in inside) for d in range(D))
    spec = [
        _anchor("midway_side", "path", f.at(pi, 0, 0), f.facing, W),
        _anchor("connector_side", "path", f.at(pi, D - 1, 0), f.back, W),
        _anchor("departure_sign", "visual_front", f.at(pi, 0, 4), f.facing, 1),
    ]
    return {"kind": "threshold", "width": W, "depth": D, "to": to, "dest": dest,
            "paved": paved, "dithered": dithered, "planters": planters, "lamps": lamps,
            "signs": signs, "sign_slots": want, "narrowest": narrow,
            "standing": [list(f.at(i, d, 0)) for (i, d) in sorted(inside)],
            "reachable": len(walk), "cells": sorted(inside),
            "midway_side": list(f.at(pi, 0, 0)), "connector_side": list(f.at(pi, D - 1, 0)),
            "anchors": declare(spec),
            "contract": "a %d-wide continuous paved handoff %d cells long from the midway into "
                        "%s: the ground dithers from this land's palette to that one over the "
                        "whole run so there is no course at which it changes, the kerbs, "
                        "planting and lantern change with it, and a fingerpost at the MIDWAY end "
                        "names the destination and the way back while both are still choices"
                        % (W, D, to),
            "unverified": [
                "the arch and the Isthmus beyond it are out of this lane. This kind stops at "
                "`connector_side` and declares it as an edge anchor for the coordinator to link.",
            ]}


BUILDERS = {
    "hub": _hub,
    "ridequeue": _ridequeue,
    "rideexit": _rideexit,
    "gamesrow": _gamesrow,
    "threshold": _threshold,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**MIDWAY, **cfg}
    if not p.get("at"):
        raise ValueError("midway needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown midway kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    # FIFTEEN CHARACTERS IS THE LINE, and it is checked here rather than at every caller: a sign
    # clips mid-word past it and the failure only appears in a screenshot after the build is
    # placed.  `_sign` truncates, so this catches a caller that wrote text with `w.sign` directly.
    for (x, y, z), t in w.signs.items():
        for line in list(t["front"]) + list(t["back"]):
            if len(str(line)) > SIGN_WIDTH:
                raise ValueError(f"sign line {line!r} at {(x, y, z)} is wider than a sign")

    return w.canvas({
        "kind": f"midway/{p['kind']}",
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("kind", "contract", "unverified")},
    })
