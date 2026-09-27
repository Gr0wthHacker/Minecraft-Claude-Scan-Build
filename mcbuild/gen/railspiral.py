"""The Island Line - a minecart spiral from the deck to the lowland, and back up.

Jack's idea: delete the connecting tracks and run a spiral all the way down, ridable both ways,
built out of MORE POWERED RAILS THAN NORMAL ONES because iron is dear. The premise about iron is
right for this island and the reason is the opposite of the obvious one:

    rail          6 iron  -> 16 rails     0.375 iron each
    powered_rail  6 gold  -> 6  rails     1.0   gold each

Gold is farmable here and iron is not, so the cheap rail is the GOLD one. That inverts the usual
advice and it decides the whole design: lay powered rail everywhere and spend iron only where the
game leaves no choice.

THE GAME LEAVES NO CHOICE AT CORNERS, and this is the load-bearing fact. Read off blocks.json
rather than remembered:

    powered_rail  shape = north_south, east_west, ascending_{n,s,e,w}
    rail          shape = ...those six, PLUS south_east, south_west, north_west, north_east

A POWERED RAIL CANNOT CURVE. So every direction change is a normal rail and therefore iron, which
makes the PLAN SHAPE of the spiral an iron decision rather than an aesthetic one. Measured at
r=30: a square lap turns 4 times, a rasterised circle turns 60 times. Round costs fifteen times
the iron for the same descent - more iron than is in store. Hence a SQUARE helix: four straight
flights a lap with a landing at each corner, which is also how the void tower and the sanctum earn
their read, by regularity rather than by curves.

AN UNPOWERED POWERED_RAIL IS A BRAKE. That is what makes "mostly powered rails" different in kind
from "mostly rails": you cannot lay 634 of them and energise some. Every one has to carry signal,
so the bed cell under the track becomes a `redstone_block` every `power_every` cells - and the runs
are counted BETWEEN CORNERS, because a normal rail does not propagate the chain. A design that
powered on a flat spacing would leave a dead rail on the far side of every turn, and a dead rail is
a cart that stops in mid-air a hundred blocks up.

NEVER DESCEND INTO A CORNER. A curve has no ascending shape either, so a corner and both of its
neighbours must sit at one height; drop into one and the game re-derives it as a slope, the turn is
lost and the track dead-ends. The grade therefore skips the cell before a corner as well as the
corner itself. Nothing about the emitted model looks wrong when this is missed - `shape` is
DERIVED by the game (it is not in `work.INTENTIONAL`, exactly as a stair's is not), so the
schematic, the audit and the bill of materials all pass while the line does not connect.

THE RADIUS WAS SWEPT, AND THE FIRST SWEEP ASKED THE WRONG QUESTION. Scoring whether the whole RING
was clear at each course said r=12 was the only option and everything wider was 105-152 courses
blocked. But a helix occupies ONE CELL PER COURSE, not the ring: a blocked ring only means the
helix must arrive at a different PHASE. Swept over centre, radius and phase - the same start-angle
sweep the Lowland Stair already uses - r=30 at (-24206, 30014) threads the whole descent breaking
nothing, and stands 15 clear of the stair's outer edge instead of 3. Jack's word for the first one
was that it made no sense as a separate thing, and it did not.

Wider is not better past that. At r=36 only 42% of the track has island overhead - most of the
ride is a viaduct in open sky rather than one threading the island's underside - and the boarding
platform lands 85 blocks from the deck rail head against 28 at r=30.

THE VIADUCT CARRIES ITS OWN LIGHT, for the Island Run's reason: it is ~1,900 new walkable cells
hung in a void that the night pass solved without them. Lanterns ride the deck EDGE and never the
track, so nothing a cart runs over is a fixture.

A TERMINUS NEEDS A BLOCK BEHIND IT. A stationary cart on a powered rail is launched AWAY from the
adjacent solid block, so without a stop block at each end the cart sits there and the line only
works in whichever direction you happen to shove it.
"""
from __future__ import annotations

from ..audit import GROUND_PLANTS
from . import protect
from ..plot import find as find_plot
from .canvas import Canvas, hash01
from .vertical import Ctx, World

RAILSPIRAL = {
    "under": None,
    "center": None,            # world (x, z) of the helix axis
    "radius": 30,
    "y_top": 192,
    "y_bottom": 42,
    "grade": 4,                # one course of drop per N straight track cells
    "start_angle": 0,          # phase along the lap, in cells - SWEEP it, do not guess
    "direction": 1,            # +1 walks the lap one way, -1 the other
    "deck_width": 3,           # bed + walkway, odd. 1 is a bare rail and reads as a thread
    "power_every": 8,          # a redstone_block in the bed this often, per RUN between corners
    "light_every": 11,         # a lantern on the deck edge this often
    "railing": True,           # a wall on the outer edge - it is a viaduct 150 blocks up
    "railing_every": 2,
    # MATERIAL BANDS, top first. A course takes the first band whose from_y it is at or above,
    # dithered per CELL over band_blend courses: a hard seam across a helix reads as two viaducts
    # stacked. Same gradient the Lowland Stair carries, so the two read as one hand - island stone
    # brick at the top, deepslate through the twilight, the quarter's blackstone on the ground -
    # and the light goes cold with the stone.
    "bands": None,
    "band_blend": 6,
    "land": True,              # end the descent on the lowland floor, not at y_bottom
    # WHERE THE LINE STARTS. [x, y, z] of the first rail, out at a place you can already stand -
    # the sky-well court's edge. The helix cannot reach it itself: the ring's west leg IS the
    # court's rock wall, solid Y194-200, not its floor. Must share an axis with the helix's top
    # cell, so the spur needs no corner and therefore no iron.
    "approach_from": None,
    "reserve": None,           # design .litematic paths to keep clear of
    "clear_of": None,          # [[x, z, radius]] columns to stay out of, e.g. the stair
    "seed": 0,
}

# What the track may CLEAR rather than be stopped by: the lowland floor it lands on is grass and
# fern, and a printer places into air only. Structural blocks are never on this list.
CLEARABLE = set(GROUND_PLANTS) | {"vine", "glow_lichen", "moss_carpet", "hanging_roots",
                                  "cave_vines", "cave_vines_plant", "seagrass", "grass", "snow"}

_DIRS = {(0, 1): "south", (0, -1): "north", (1, 0): "east", (-1, 0): "west"}
_CURVE = {frozenset(("north", "east")): "north_east",
          frozenset(("north", "west")): "north_west",
          frozenset(("south", "east")): "south_east",
          frozenset(("south", "west")): "south_west"}


def lap(cx: int, cz: int, r: int, direction: int = 1):
    """One lap of the square ring, in order. Corners are where the heading changes."""
    p = []
    for t in range(-r, r):
        p.append((cx + r, cz + t))
    for t in range(r, -r, -1):
        p.append((cx + t, cz + r))
    for t in range(r, -r, -1):
        p.append((cx - r, cz + t))
    for t in range(-r, r):
        p.append((cx + t, cz - r))
    return p if direction >= 0 else [p[0]] + p[:0:-1]


def corners_of(path) -> set:
    n = len(path)
    out = set()
    for i in range(n):
        a, b, c = path[i - 1], path[i], path[(i + 1) % n]
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            out.add(b)
    return out


def route(cx, cz, r, y_top, y_bottom, grade, phase, direction=1, ground=None):
    """The track, top to bottom: [(x, y, z, is_corner)].

    THE DROP IS SUPPRESSED BEFORE A CORNER AS WELL AS ON IT. A curve has no ascending shape, so a
    corner and both its neighbours must share one height, or the game re-derives the turn as a
    slope and the line dead-ends - silently, because `shape` is derived and the model looks fine.

    THE LINE SEEKS ITS OWN GROUND. `ground(x, z)` gives the lowland's surface under a column, or
    None over void, and the descent ends the moment the track can sit on it. Ending at a fixed
    y_bottom instead put the first terminus in the ONE 33-cell stretch of the ring with no floor
    beneath it - a platform 43 blocks over the void, which you step out of the cart and fall off.
    A railway ends at the ground or it is not a station.
    """
    ring = lap(cx, cz, r, direction)
    n = len(ring)
    corners = corners_of(ring)
    cells, y, i, step = [], float(y_top), int(phase), 0
    limit = n * 12
    while True:
        x, z = ring[i % n]
        nxt = ring[(i + 1) % n]
        here_corner = (x, z) in corners
        yy = int(round(y))
        g = ground(x, z) if ground is not None else None
        if g is not None and not here_corner and yy <= g + 1:
            cells.append((x, g + 1, z, False))         # the last tread rests on the floor itself
            break
        if ground is None and yy <= y_bottom:
            break
        cells.append((x, yy, z, here_corner))
        i += 1
        step += 1
        if len(cells) > limit:
            raise ValueError("the line never reached ground - no column on the ring can be landed "
                             "on; lower y_bottom, move the centre, or set land: false")
        if here_corner or nxt in corners:
            continue                                  # keep the turn flat on both sides of it
        if step % grade != 0:
            continue
        # IN THE LANDING BAND, DESCEND ONLY WHERE THERE IS SOMETHING TO DESCEND TOWARD. 55 of the
        # 240 ring columns are open void, and running the grade blindly through them spends the
        # last of the height over the chasm - which is exactly where the first terminus ended up.
        # Over void the line holds level and keeps circling until floor comes back under it.
        if y > y_bottom or g is not None:
            y -= 1.0
    return cells


def straight_run(start, end):
    """An axis-aligned approach from `start` to (but not including) `end`, descending evenly.

    THE LINE HAS TO START SOMEWHERE YOU ALREADY ARE. A helix that begins in mid-air is complete
    and unreachable - you ride up to the top station and are stranded - so the top of the line runs
    level out to a place with a floor. Here that is the sky-well court's east edge: the ring's own
    west leg is the court's rock WALL (solid at Y194-200), not its floor, so the helix cannot pass
    through the court however it is phased, and the connection is a spur by necessity.

    Straight and axis-aligned on purpose: a corner is the only thing on this railway that costs
    iron, and an approach that shares an axis with the helix's first cell needs none.
    """
    sx, sy, sz = start
    ex, ey, ez = end
    if sx != ex and sz != ez:
        raise ValueError(f"the approach {start} -> {end} is not axis-aligned; a bent spur would "
                         f"need corner rails, which are the only iron on the line")
    n = max(abs(ex - sx), abs(ez - sz))
    if n == 0:
        return []
    if sy < ey:
        raise ValueError(f"the approach must descend toward the helix: {sy} -> {ey}")
    dx = (ex - sx) // n if ex != sx else 0
    dz = (ez - sz) // n if ez != sz else 0
    drop = sy - ey
    if drop > n:
        raise ValueError(f"the approach falls {drop} over {n} cells - a rail drops at most one "
                         f"course per cell")
    out = []
    for i in range(n):                       # up to, not including, the helix's own first cell
        y = sy - int(round(drop * i / float(n)))
        out.append((sx + dx * i, y, sz + dz * i, False))
    return out


def shapes_for(cells):
    """The rail `shape` for every cell, from its neighbours.

    Emitted so the render and Litematica's overlay agree with the build; the GAME derives it on
    placement and `work.INTENTIONAL` does not compare it, exactly as it does not compare a stair's.
    """
    out = []
    n = len(cells)
    for i, (x, y, z, corner) in enumerate(cells):
        links = []
        for other in (cells[i - 1] if i else None, cells[i + 1] if i + 1 < n else None):
            if other is None:
                continue
            key = (other[0] - x, other[2] - z)
            if key in _DIRS:
                links.append((_DIRS[key], other[1] - y))
        if not links:
            out.append("north_south")
            continue
        if corner and len(links) == 2 and links[0][0] != links[1][0]:
            out.append(_CURVE[frozenset((links[0][0], links[1][0]))])
            continue
        up = [d for d, dy in links if dy > 0]
        if up:                                        # the lower cell of a slope ascends toward it
            out.append("ascending_" + up[0])
            continue
        d = links[0][0]
        out.append("north_south" if d in ("north", "south") else "east_west")
    return out


def runs_of(cells):
    """Index ranges of consecutive POWERED cells. A corner is a normal rail and breaks the signal
    chain, so power is dealt per run - a flat spacing leaves a dead rail past every turn."""
    out, start = [], None
    for i, cell in enumerate(cells):
        if cell[3]:
            if start is not None:
                out.append((start, i))
            start = None
        elif start is None:
            start = i
    if start is not None:
        out.append((start, len(cells)))
    return out


def power_cells(cells, every: int) -> set:
    """Indices whose BED becomes a redstone_block: one at each run's start and end, then every
    `every` along it. Both ends, because a run's far cell is the one a cart leaves a corner onto."""
    picks = set()
    for a, b in runs_of(cells):
        for i in range(a, b, max(1, every)):
            picks.add(i)
        picks.add(b - 1)
    return picks


def side_of(cells, i):
    """Unit vector perpendicular to travel at cell i, in the XZ plane."""
    a = cells[max(0, i - 1)]
    b = cells[min(len(cells) - 1, i + 1)]
    dx, dz = b[0] - a[0], b[2] - a[2]
    if dx == 0 and dz == 0:
        dx = 1
    if abs(dx) >= abs(dz):
        return (0, 1 if dx > 0 else -1)
    return (1 if dz < 0 else -1, 0)


def band_at(bands, y, blend, x, z, seed):
    """The material band for a course, dithered per CELL across the seam."""
    if not bands:
        return {}
    for k, b in enumerate(bands):
        if y >= b["from_y"]:
            if k and blend and y < b["from_y"] + blend:
                t = (y - b["from_y"]) / float(blend)
                if hash01(x, y, z, seed, 77) < t:
                    return bands[k - 1]
            return b
    return bands[-1]


def ground_under(ctx, cx, cz, r, direction, y_bottom):
    """Top solid course under each ring column, or None over void.

    185 of the 240 columns at r=30 have lowland floor and 55 do not, which is why the line has to
    ask rather than assume - a fixed y_bottom put the first terminus in the one 33-cell gap.
    """
    lo, hi = int(y_bottom) - 8, int(y_bottom) + 20
    table = {}
    for (gx, gz) in lap(cx, cz, r, direction):
        top = None
        for gy in range(hi, lo - 1, -1):
            if ctx.occupied(gx, gy, gz) and not protect.is_protected(ctx.name_at(gx, gy, gz)):
                top = gy
                break
        table[(gx, gz)] = top
    return table


def plan(params: dict, ctx=None):
    """THE track for a config: the one entry point the build and the tests both go through.

    Written twice, they drift - the tests called `route` without a ground table, got the old
    over-the-void terminus, and reported a stop block missing from a design that has one. Same rule
    `proportions.measure` and `rubric.score` already follow: one source, so two cannot disagree.
    """
    p = dict(RAILSPIRAL)
    p.update(params or {})
    if ctx is None and p.get("under"):
        ctx = Ctx(p["under"])
    cx, cz = p["center"]
    r, d = int(p["radius"]), int(p["direction"])
    ground = None
    if ctx is not None and p.get("land", True):
        table = ground_under(ctx, cx, cz, r, d, int(p["y_bottom"]))
        # NOT `table.get` - dict.get(x, z) reads z as the DEFAULT, so a miss returned a Z
        # coordinate as a height and the route terminated on its first cell.
        ground = lambda gx, gz: table.get((gx, gz))          # noqa: E731
    cells = route(cx, cz, r, int(p["y_top"]), int(p["y_bottom"]),
                  int(p["grade"]), int(p["start_angle"]), d, ground=ground)
    if p.get("approach_from"):
        ax, ay, az = (int(v) for v in p["approach_from"])
        cells = straight_run((ax, ay, az), (cells[0][0], cells[0][1], cells[0][2])) + cells
    return cells


def _reserved(paths):
    """Every cell any named design claims, so the line never contests live work."""
    import numpy as np
    from .vertical import load_capture
    out = set()
    for path in paths or []:
        m, (ox, oy, oz) = load_capture(path)
        ys, zs, xs = np.where(m.ids > 0)
        for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
            out.add((x + ox, y + oy, z + oz))
    return out


def build_railspiral(cfg: dict, donors=None) -> Canvas:
    p = dict(RAILSPIRAL)
    p.update(cfg or {})
    ctx = Ctx(p["under"]) if p.get("under") else None
    plot = find_plot(p["under"]) if p.get("under") else None
    reserved = _reserved(p.get("reserve"))
    seed = int(p["seed"])

    cx, cz = p["center"]
    r = int(p["radius"])

    cells = plan(p, ctx)
    shapes = shapes_for(cells)
    powered = power_cells(cells, int(p["power_every"]))
    half = max(0, (int(p["deck_width"]) - 1) // 2)

    w = World()
    skipped = {"plot": 0, "world": 0, "reserved": 0, "protected": 0, "clear_of": 0}
    keepout = [tuple(c) for c in (p.get("clear_of") or [])]

    def blocked(x, y, z):
        """Why this DRESSING cell may not be built. Dressing yields to everything, quietly."""
        if plot and not plot.contains(x, z):
            skipped["plot"] += 1
            return True
        for kx, kz, kr in keepout:
            if max(abs(x - kx), abs(z - kz)) <= kr:
                skipped["clear_of"] += 1
                return True
        if (x, y, z) in reserved:
            skipped["reserved"] += 1
            return True
        if ctx:
            nm = ctx.name_at(x, y, z)
            if protect.is_protected(nm):
                skipped["protected"] += 1
                return True
            if ctx.occupied(x, y, z):
                skipped["world"] += 1
                return True
        return False

    # A TRACK CELL IS NOT OPTIONAL. Dressing may yield anywhere; the track may not, because a
    # skipped rail is a GAP, and a gap in a line 150 blocks up is a cart in the void. The first
    # build skipped two and shipped 0 problems, 0 overlap and THREE components - the audit caught
    # it only because a broken line happens also to be a broken solid. So the two kinds of cell are
    # judged apart: anything the WORLD holds, or that is protected or off-plot, is fatal and named;
    # a cell only a DESIGN claims is CLAIMED and reported, because on this island nothing old is
    # live (sync tracks nothing, every design was accepted as complete) and an unbuilt plant cannot
    # outrank a continuous railway. Never silently, either way.
    claimed = []
    dig = set()
    cleared_names = set()
    for i, (x, y, z, corner) in enumerate(cells):
        for (ax, ay, az) in ((x, y, z), (x, y - 1, z)):
            if plot and not plot.contains(ax, az):
                raise ValueError(f"track cell {(ax, ay, az)} is outside the plot - move the centre "
                                 f"or shrink the radius")
            for kx, kz, kr in keepout:
                if max(abs(ax - kx), abs(az - kz)) <= kr:
                    raise ValueError(f"track cell {(ax, ay, az)} is inside a clear_of column "
                                     f"{(kx, kz, kr)} - re-sweep start_angle or move the centre")
            if ctx:
                nm = ctx.name_at(ax, ay, az)
                if protect.is_protected(nm) or protect.is_used(nm):
                    raise ValueError(f"track cell {(ax, ay, az)} is {nm!r}, which is protected - "
                                     f"re-sweep start_angle")
                if ctx.occupied(ax, ay, az):
                    # A PLANT IS NOT AN OBSTRUCTION, BUT IT IS NOT NOTHING EITHER. The line lands
                    # on the lowland floor, which is grass and fern; a printer places into AIR
                    # only, so a track cell inside grass is a cell that never gets placed - a gap,
                    # arrived at from the other direction. Plants go on the DIG list and are
                    # cleared, which is the sidecar's own answer for this. Anything else is fatal:
                    # the line may not be routed through rock and quietly lose a rail.
                    if nm in CLEARABLE:
                        dig.add((ax, ay, az))
                        cleared_names.add(nm)
                        continue
                    raise ValueError(f"track cell {(ax, ay, az)} is {nm!r} in the world - "
                                     f"re-sweep start_angle or the line will have a gap")
            if (ax, ay, az) in reserved:
                claimed.append((ax, ay, az))

    placed = []
    for i, (x, y, z, corner) in enumerate(cells):
        b = band_at(p["bands"], y, int(p["band_blend"]), x, z, seed)
        deck = b.get("deck", "stone_bricks")
        edge = b.get("edge", deck)
        # the bed FIRST: the worklist sorts bottom-up, so it is in before the rail lands on it
        w.put(x, y - 1, z, "redstone_block" if i in powered else deck)
        w.put(x, y, z, "rail" if corner else "powered_rail", shape=shapes[i])
        placed.append(i)
        sx, sz = side_of(cells, i)
        for k in range(1, half + 1):
            for s in (1, -1):
                dx, dz = x + sx * k * s, z + sz * k * s
                if not blocked(dx, y - 1, dz):
                    w.put(dx, y - 1, dz, edge if k == half else deck)
    # THE LINE OWNS ITS OWN CELLS. Dressing is placed in a second pass over what actually got
    # built - the enrichment lesson, that a gate scoring CANDIDATES ships fixtures on runs never
    # laid - and it may never land on the track or its bed. The first build put a lantern ON a
    # powered rail, because the perpendicular flips through a corner and the offset walked back
    # onto the line: the frog's "the eye sits over the hind foot in plan" wearing a hard hat. A
    # fixture that belongs beside a thing has to be excluded from the thing, by construction.
    line = set()
    for i in placed:
        x, y, z, _ = cells[i]
        line.add((x, y, z))
        line.add((x, y - 1, z))
    built = set(placed)
    lights = 0
    for n, i in enumerate(placed):
        x, y, z, _ = cells[i]
        b = band_at(p["bands"], y, int(p["band_blend"]), x, z, seed)
        sx, sz = side_of(cells, i)
        if not half:
            continue
        lit = int(p["light_every"]) and n % int(p["light_every"]) == 0
        railed = p["railing"] and n % max(1, int(p["railing_every"])) == 0
        for s in (1, -1):
            rx, rz = x + sx * half * s, z + sz * half * s
            if (rx, rz) == (x, z) or (rx, y, rz) in line or blocked(rx, y, rz):
                continue
            # THE LIGHT IS THE DECK, NOT A FIXTURE ON IT. Lanterns cost iron - 58 of them came to
            # ~52 ingots against the 11 corner rails' 4, so the LIGHTING was ten times the metal
            # of the railway. A froglight set flush in the deck edge costs none, is the idiom this
            # island already lights itself with (Island Night, the lowland turf), cannot be knocked
            # off a walkway 150 blocks up, and leaves the 3-wide deck clear to walk. It reaches 14
            # rather than 15 - it IS the floor, an opaque emitter a course down - which is what the
            # spacing is set against.
            if lit and s == 1 and (rx, y - 1, rz) not in line and w.has(rx, y - 1, rz):
                w.put(rx, y - 1, rz, b.get("light", "ochre_froglight"))
                lights += 1
                continue
            if not w.has(rx, y - 1, rz):          # nothing under it: a post on air is not a post
                continue
            if railed:
                w.put(rx, y, rz, b.get("railing", "stone_brick_wall"))
    # THE STOPS. A stationary cart on a powered rail launches away from the adjacent solid block,
    # so each terminus gets one or the line only runs the way you happen to shove it.
    # The stop goes on the far side of the terminus from the track: mirror the NEIGHBOUR through
    # the end cell. Written the other way round first - indexing off the end of the list at one
    # terminus and off the front at the other - it placed neither, silently, and the line would
    # have run only whichever way you happened to shove the cart.
    stops = 0
    for i, j in ((placed[0], placed[1]), (placed[-1], placed[-2])):
        x, y, z, _ = cells[i]
        bx, bz = 2 * x - cells[j][0], 2 * z - cells[j][2]
        b = band_at(p["bands"], y, int(p["band_blend"]), x, z, seed)
        # A BLOCK THE WORLD ALREADY HOLDS IS A STOP. At the court end the mirror cell is the
        # court's own deepslate plinth, so placing one would both overlap and be pointless - the
        # cart launches off what is already there. Counting only what WE place reported stops: 1
        # on a line with two working ones, which is the kind of number that gets 'fixed' later.
        if ctx and ctx.occupied(bx, y, bz) and not protect.is_protected(ctx.name_at(bx, y, bz)):
            stops += 1
            continue
        if not blocked(bx, y, bz):
            w.put(bx, y, bz, b.get("deck", "stone_bricks"))
            if not blocked(bx, y - 1, bz):
                w.put(bx, y - 1, bz, b.get("deck", "stone_bricks"))
            stops += 1

    meta = {
        "kind": "railspiral",
        "center": [cx, cz], "radius": r, "grade": int(p["grade"]),
        "start_angle": int(p["start_angle"]),
        "track": len(placed),
        "powered": sum(1 for i in placed if not cells[i][3]),
        "corners": sum(1 for i in placed if cells[i][3]),
        "power_sources": len(powered & built),
        "runs": len(runs_of(cells)),
        "turns": round(len(cells) / (8.0 * r), 2),
        "y_top": cells[0][1], "y_bottom": cells[-1][1],
        "stops": stops,
        "lights": lights,
        "claimed": [list(c) for c in claimed],
        "dig": sorted(list(c) for c in dig),
        # `clear` is CATEGORIES by name - what verify_in_context is allowed to see the
        # design standing where the world holds a plant. Without it the cleared cells
        # read as overlap, which is the one number a remedial design is judged on.
        "clear": sorted(cleared_names),
        "cleared": len(dig),
        "skipped": skipped,
    }
    return w.canvas(meta)
