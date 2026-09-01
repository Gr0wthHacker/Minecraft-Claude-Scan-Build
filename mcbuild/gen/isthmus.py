"""The Isthmus: the land between the theme park's three islands.

THE THREE PLOTS WERE JOINED BY A BRIDGE AND NOTHING ELSE. `gen/transit.py` hangs a skyway four
courses over the street from one island to the next - a real fix for "you cannot get there" -
but it is a viaduct on piers, not ground, and Jack asked for the gap ITSELF to be built: "we need
to build all the land etc and fill in the areas between the islands outside of just the
connecting rails". A visitor who never once uses the railway should still be able to WALK across.

**THE GAPS, MEASURED OFF THE THREE SHIPPED ZONES** (`out/Park_{Left,Centre,Right} Complete`):
every zone's own floor is flush at Y202, edge to edge, and the boundary Z row of each is paved
solid the whole way across - so there is no wall to break through, only void to cross.

    islandleft   Z 80351..80449   frontier
    newisle      Z 80551..80649   midway     (the entrance)
    islandright  Z 80751..80849   hollow

    gap A: Z 80450..80550   frontier <-> midway    101 columns of void
    gap B: Z 80650..80750   midway  <-> hollow      101 columns of void

**THE AVENUE IS ALREADY AIMED AT THE GAP, AND THAT DECIDED THE SITE.** Every zone's own
north-south avenue lands its kerb lamp posts at X 97592 and X 97598 on EVERY boundary row of
all three zones - the same two columns, on four different edges of three unrelated builds. That
can only mean one thing: the main avenue is centred on X 97595 and runs the zone's own full Z
span, edge to edge. So the isthmus's own spine is laid at that exact centre and width (kerb to
kerb, half-width 3) - not chosen to match, INCAPABLE of not matching, because it is the same
road continuing.

**THE EAST STRIP IS THE RAILWAY'S, NOT OURS.** `transit.py` reserves X 97640..97649 for the
skyway's piers and arches (measured there as "not one cell at X >= 97643 in any zone"); this
design stops at X 97639 and never claims a column past it, so the skyway's piers pass overhead
in the open air this leaves them.

**A NARROWED CAUSEWAY WITH A SHELL, NOT A SOLID SLAB - the cost the brief itself calls out.** A
flat 99-wide plate at three courses deep across both gaps is 2*101*99*3 = 60,000 blocks, which
is more than the entire built park. Two things cut that by construction rather than by hollowing
it out afterward:

    NARROW    the outline flares to meet each plot and pinches to a neck at the void's own
              midpoint - "shoulder_max" wide at the ends, "shoulder_min" plus the spine at the
              waist - so most of a gap's width is never built at all.
    SHELL     every column is capped and given exactly enough rock underneath to reach its
              LOWEST orthogonal neighbour (see `_seat`) plus one extra course at the true
              outline - never a fixed deep fill. The interior is two or three blocks thick; only
              the outline reads as a cliff.

**THE RIM IS DERIVED, NOT DRAWN.** A column is an edge - and gets the kerb, the fence and the
deeper shell - exactly where an orthogonal neighbour is MISSING from the shape, except at the
two ends where the missing neighbour is the island's own already-built ground. Drawing the rim
from a hand-picked outline shipped the void tower's own mistake in a new body once already in
this project (a punched doorway repaints cells that already exist); deriving it from the
footprint itself means an overlook bulge or an edge-noise ripple gets a rim for free, everywhere
one is actually needed, and nowhere the shape flush-joins a plot.

**PLANT IN DRIFTS, ON MOSS, NEVER ON THE SPINE.** `gen/thicket.py`'s own rule, copied rather
than reinvented: the noise belongs on a drift's RADIUS, not on its interior, or the first result
is 191 blobs of which three quarters are one or two cells. Grass and dirt are CURRENCY on this
server (`blocks.spendable`) - the shoulders are `moss_block` with a `moss_carpet` fringe, exactly
`thicket`'s own soil, and the spine is never planted on at all.

**THE LIGHT IS THE SURFACE, NOT A FIXTURE ON IT** - `ochre_froglight` flush in the cap, this
island's own idiom since the lowland turf and the skyway's own deck. Verified to zero spawnable
cells by `nightlight`, the one source this repo has for what emits, what passes, and what a mob
can stand on - the same discipline `transit.py` and `Island Night` already keep, because a lamp
that looks placed and lights nothing has shipped from this project more than once.

GEOMETRY, stated once because getting it wrong is invisible in every render:

    t     0 at the gap's own first row (flush with the northern/western plot), 1 at its last
    x     world X; the spine is centred on X_SPINE and is unaffected by t
    dx    abs(x - X_SPINE); 0 on the spine's own centreline
"""
from __future__ import annotations

import math

from . import park
from .canvas import Canvas, hash01
from .vertical import World

# --------------------------------------------------------------------------------- the geometry

X_SPINE = 97595          # measured: every zone's own avenue is centred here - see module docstring
X_MIN = 97551             # measured: the plots' shared west edge (`transit.PLOT_RADIUS` band)
RESERVE_X = 97640         # measured: transit.py's own corridor starts here. Never build at >= this.

BASE_Y = 202               # the park's own floor course; flush ends must land exactly on it

# The two gaps, measured off the shipped zones - see the module docstring's table.
GAPS = [
    {"z_lo": 80450, "z_hi": 80550, "land_a": "frontier", "land_b": "midway",
     "title": "THE FRONTIER REACH"},
    {"z_lo": 80650, "z_hi": 80750, "land_a": "midway", "land_b": "hollow",
     "title": "THE HOLLOW REACH"},
]

ISTHMUS = {
    "under": None,
    "kind": "isthmus",          # "isthmus" (both gaps, shipped) or "reach" (one, for tuning/tests)
    "gaps": None,                # reach only: overrides GAPS[0] with an explicit single gap dict
    "avoid": None,                # design .litematic paths whose cells are already somebody's

    "x_spine": X_SPINE,
    "x_min": X_MIN,
    "reserve_x": RESERVE_X,       # None disables the check - never used for the shipped kind

    "spine_half": 3,              # HALF the avenue's own measured width - the two must match
    "shoulder_min": 4,            # half-width of moss beyond the spine at the narrowest waist
    "shoulder_max": 30,           # half-width of moss beyond the spine where it meets a plot
    "flare_power": 1.6,           # > 1 keeps the waist narrow for longer before it flares
    "edge_noise": 0.22,           # per-row ripple on the outline, so the coastline is not a curve
    "rise_max": 2,                 # courses the spine humps up at the gap's own midpoint
    "terrace_drop_max": 2,        # courses the shoulder steps down before it reaches the rim
    "overlook_half": 9,            # half-width of the rest-stop bulge at midspan
    "overlook_span": 6,            # +/- rows of the bulge around midspan
    "rim_shell": 4,                # extra courses the true outline drops below its own neighbours
    "light_every": 9,
    "drifts_per_span": 9,          # drift centres per gap, scaled by length inside `_build_gap`
    "drift_min_gap": 7,
    "drift_radius": 3.2,
    "seed": 0,
}

LAMP = "ochre_froglight"


def _land_at(land_a, land_b, t, seed, blend=0.16):
    """Which land's masonry the spine takes at fraction t: the far side's, dithered near the
    midpoint - `transit._land_at`'s own rule, restated for a plain two-land blend with no
    stations to anchor it."""
    if t <= 0.5 - blend:
        return land_a
    if t >= 0.5 + blend:
        return land_b
    frac = (t - (0.5 - blend)) / (2 * blend)
    return land_b if hash01(int(round(t * 4000)), seed, 41) < frac else land_a


def _half_at(p, t, mid_bulge):
    """The shape's own half-width beyond the centreline at fraction t, BEFORE per-row noise."""
    flare = abs(2 * t - 1) ** p["flare_power"]
    half = p["shoulder_min"] + (p["shoulder_max"] - p["shoulder_min"]) * flare
    if mid_bulge:
        half = max(half, p["overlook_half"])
    return p["spine_half"] + half


def _edge_fade(t, e=0.14):
    """0 at the two flush ends, 1 through the middle - keeps a terrace from cutting into the
    exact row that has to match a plot's own flat floor."""
    return max(0.0, min(1.0, min(t, 1.0 - t) / e))


# --------------------------------------------------------------------------------- one gap

def _sign(w, x, y, z, facing, wood, front, back=()):
    """A wall sign in the cell IN FRONT of its wall, its text facing away from its support.
    `park._sign` / `transit._sign`'s own rule: the support is CHECKED, never assumed."""
    fdx, fdz = park._STEP[facing]
    if not w.has(x - fdx, y, z - fdz):
        return False
    lines = [str(t)[:park.SIGN_WIDTH] for t in list(front)[:4]]
    lines += [""] * (4 - len(lines))
    w.put(x, y, z, f"{wood}_wall_sign", facing=facing, waterlogged="false")
    w.sign(x, y, z, front=lines, back=[str(t)[:park.SIGN_WIDTH] for t in list(back)[:4]],
           colour="white", glowing=True)
    return True


def _build_gap(w: World, p: dict, gap: dict, meta: dict) -> None:
    z_lo, z_hi = int(gap["z_lo"]), int(gap["z_hi"])
    if z_hi - z_lo < 8:
        raise ValueError("a gap needs at least 8 rows - it is not worth a shape below that")
    land_a, land_b = gap["land_a"], gap["land_b"]
    for land in (land_a, land_b):
        if land not in park.LANDS:
            raise ValueError(f"unknown land {land!r}; have {sorted(park.LANDS)}")
    xs = int(p["x_spine"])
    # NEVER Python's own `hash()` on a string here - it is salted per PROCESS
    # (PYTHONHASHSEED), so two runs of the identical config would build two different shapes.
    # `sum(map(ord, ...))` is what the rest of this codebase uses for exactly this reason.
    seed = int(p["seed"]) + sum(map(ord, str(gap.get("title") or ""))) % 97
    span = z_hi - z_lo
    mid_z = z_lo + span // 2
    ov_span = max(1, int(p["overlook_span"]))
    spine_half = max(1, int(p["spine_half"]))

    # ------------------------------------------------------------ pass 1: the footprint + height
    # cols[(x, z)] = {"y": cap height, "band": "spine"|"shoulder"|"rim-to-be", "t": fraction}
    cols = {}
    row_half = {}
    for z in range(z_lo, z_hi + 1):
        t = (z - z_lo) / float(span)
        bulge = abs(z - mid_z) <= ov_span
        half = _half_at(p, t, bulge)
        noise = 1.0 + p["edge_noise"] * (hash01(z, seed, 7) - 0.5) * (0.0 if bulge else 2.0)
        half = max(spine_half + 2, half * noise)
        half = min(half, xs - p["x_min"])
        if p.get("reserve_x") is not None:
            half = min(half, int(p["reserve_x"]) - 1 - xs)
        half = int(round(half))
        row_half[z] = half
        rise = int(round(p["rise_max"] * math.sin(math.pi * t)))
        fade = _edge_fade(t)
        for x in range(xs - half, xs + half + 1):
            dx = abs(x - xs)
            if dx <= spine_half:
                y = BASE_Y + rise
                band = "spine"
            else:
                extent = max(1.0, half - spine_half)
                frac = min(1.0, (dx - spine_half) / extent)
                drop = int(round(frac * p["terrace_drop_max"] * fade))
                y = BASE_Y + rise - drop
                band = "spine" if bulge and dx <= p["overlook_half"] else "shoulder"
            cols[(x, z)] = {"y": y, "band": band, "t": t, "bulge": bulge}

    # ------------------------------------------------------------ pass 2: seat every column on
    # its lowest orthogonal neighbour, and mark the true outline (`_seat` is the fix for a
    # floating gap between two differently-terraced columns - see the module docstring).
    def _seat(x, z):
        info = cols[(x, z)]
        y = info["y"]
        floor = y
        is_rim = False
        for ddx, ddz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + ddx, z + ddz
            if ddz and not (z_lo <= nz <= z_hi):
                continue          # the island-ward end: treated as already-built, never a rim
            nb = cols.get((nx, nz))
            if nb is None:
                is_rim = True
                continue
            floor = min(floor, nb["y"])
        info["fill_bottom"] = floor - 1 - (int(p["rim_shell"]) if is_rim else 0)
        info["rim"] = is_rim

    for (x, z) in cols:
        _seat(x, z)

    # ------------------------------------------------------------ pass 3: place the mass
    rim_n = spine_n = shoulder_n = 0
    for (x, z), info in cols.items():
        land = _land_at(land_a, land_b, info["t"], seed)
        pal = park.LANDS[land]
        y, bottom = info["y"], info["fill_bottom"]
        if info["band"] == "spine":
            spine_n += 1
            if info.get("bulge"):
                cap = pal["trim"] if (x + z) % 6 == 0 else (pal["ground"] if (x + z) % 2 == 0 else pal["path"])
            elif abs(x - xs) == spine_half:
                cap = pal["trim"]                                    # the kerb line
            else:
                cap = pal["ground"] if (x + z) % 2 == 0 else pal["path"]
        else:
            shoulder_n += 1
            cap = "moss_block"
        w.put(x, y, z, cap)
        for yy in range(y - 1, bottom - 1, -1):
            core = "cobblestone" if hash01(x, yy, z, seed, 9) < 0.4 else "stone"
            w.put(x, yy, z, core)
        if info["rim"]:
            rim_n += 1
            w.put(x, y + 1, z, pal["fence"])

    # ------------------------------------------------------------ pass 4: drifts on the shoulder
    shoulder_cells = [(x, z, info["y"]) for (x, z), info in cols.items()
                       if info["band"] != "spine" and not info["rim"]]
    n_drifts = max(1, int(round(p["drifts_per_span"] * span / 100.0)))
    order = sorted(shoulder_cells, key=lambda c: hash01(c[0], c[1], seed, 51))
    picked, drifted = [], 0
    for (cx, cz, cy) in order:
        if any(abs(cx - a) < p["drift_min_gap"] and abs(cz - b) < p["drift_min_gap"]
               for a, b in picked):
            continue
        picked.append((cx, cz))
        if len(picked) >= n_drifts:
            break
    for (cx, cz) in picked:
        rad = p["drift_radius"] * (0.7 + 0.6 * hash01(cx, cz, seed, 12))
        for dxx in range(-4, 5):
            for dzz in range(-4, 5):
                x, z = cx + dxx, cz + dzz
                info = cols.get((x, z))
                if not info or info["band"] == "spine" or info["rim"]:
                    continue
                d = (dxx * dxx + dzz * dzz) ** 0.5
                if d > rad:
                    continue
                # THE NOISE IS ON THE RADIUS, NEVER THE INTERIOR - `thicket`'s own rule.
                if d > rad * (0.7 + 0.5 * hash01(x, z, seed, 13)):
                    w.put(x, info["y"] + 1, z, "moss_carpet")
                else:
                    r = hash01(x, z, seed, 14)
                    if r < 0.28:
                        w.put(x, info["y"] + 1, z,
                              "flowering_azalea" if hash01(x, z, seed, 15) < 0.25 else "azalea")
                    elif r < 0.6:
                        w.put(x, info["y"] + 1, z, "fern")
                    elif r < 0.85:
                        w.put(x, info["y"] + 1, z, "short_grass")
                drifted += 1

    # ------------------------------------------------------------ pass 5: the overlook - "a
    # moment", not a building. Benches face the rim; the post carries the name and the light.
    land_mid = _land_at(land_a, land_b, 0.5, seed)
    pal_mid = park.LANDS[land_mid]
    bench_n = 0
    for side, bz in ((-1, mid_z - 3), (1, mid_z + 3)):
        bx = xs - side * (spine_half + 2)
        info = cols.get((bx, bz))
        if not info or w.has(bx, info["y"] + 1, bz):
            continue
        w.put(bx, info["y"] + 1, bz, pal_mid["stair"], facing="east" if side < 0 else "west",
              half="bottom", shape="straight", waterlogged="false")
        bench_n += 1
    post_x, post_z = xs, mid_z
    info = cols.get((post_x, post_z))
    named = False
    if info:
        py = info["y"] + 1
        for h in range(2):
            w.put(post_x, py + h, post_z, pal_mid["post"])
        w.put(post_x, py + 2, post_z, LAMP)
        title = str(gap.get("title") or "THE REACH")
        named = _sign(w, post_x, py + 1, post_z - 1, "north", pal_mid["wood"],
                      [title[:park.SIGN_WIDTH], "", land_a.upper(), land_b.upper()])

    # ------------------------------------------------------------ pass 6: the light, last - a
    # brick grid over the WHOLE shape, not just the spine, offset row to row so no seam lines
    # up twice. Slides to the nearest column whose own cell above is clear - `transit._lamps`'s
    # own rule, because a lamp under a fence or a bench is not a lamp. RIM COLUMNS ARE SKIPPED
    # ON PURPOSE: the fence already standing on one blocks the headroom `nightlight.surface`
    # needs before it calls a cell spawnable at all, so lighting a rim cell lights nothing the
    # classifier was ever going to call dark.
    every = max(3, int(p["light_every"]))
    lamps, missed = [], 0
    placed_at = set()
    for row_i, z0 in enumerate(range(z_lo, z_hi + 1, every)):
        half = row_half.get(z0, spine_half)
        offset = (every // 2) if row_i % 2 else 0
        for dx in range(-half + offset, half + 1, every):
            tx = xs + dx
            found = False
            for r in range(0, every + 1):
                ring = [(0, 0)] if r == 0 else [(r, 0), (-r, 0), (0, r), (0, -r)]
                for (ddx, ddz) in ring:
                    x, z = tx + ddx, z0 + ddz
                    if not z_lo <= z <= z_hi or (x, z) in placed_at:
                        continue
                    info = cols.get((x, z))
                    if not info or info["rim"] or w.has(x, info["y"] + 1, z):
                        continue
                    w.put(x, info["y"], z, LAMP)
                    lamps.append([x, info["y"], z])
                    placed_at.add((x, z))
                    found = True
                    break
                if found:
                    break
            if not found:
                missed += 1

    meta.setdefault("gaps_built", []).append({
        "title": gap.get("title"), "z_lo": z_lo, "z_hi": z_hi,
        "land_a": land_a, "land_b": land_b,
        "spine": spine_n, "shoulder": shoulder_n, "rim": rim_n, "drifted": drifted,
        "bench": bench_n, "named": named, "lamps": lamps, "lamps_unplaceable": missed,
        "columns": list(cols.keys()),
    })


# --------------------------------------------------------------------------------- the builders

def _check(w: World, p: dict) -> None:
    """Refuse a build that has actually crossed a line, BEFORE it ships. Both checks here are
    ones a per-cell audit cannot see: a cell claimed by another design, or one east of the
    railway's own corridor - `transit._check`'s own two failures, restated for a landform that
    has no track to make the first of them automatic."""
    avoid = set()
    for path in (p.get("avoid") or []):
        from .railspiral import _reserved as rs_reserved
        avoid |= rs_reserved([path])
    reserve_x = p.get("reserve_x")
    for (x, y, z) in w.cells:
        if (x, y, z) in avoid:
            raise ValueError(f"cell {(x, y, z)} is claimed by another design - move the isthmus")
        if reserve_x is not None and x >= int(reserve_x):
            raise ValueError(f"cell {(x, y, z)} is at x={x}, inside the railway's own corridor "
                             f"(>= {reserve_x}) - narrow the shape")


def _reach(w: World, p: dict, ctx) -> dict:
    """One gap alone - for tuning a single span and for fast tests."""
    gap = p.get("gaps") or GAPS[0]
    meta = {}
    _build_gap(w, p, gap, meta)
    _check(w, p)
    meta["kind"] = "reach"
    meta["contract"] = ("a walkable causeway across one void gap: a paved spine at the avenue's "
                        "own width joining flush to both plots, moss shoulders that flare to "
                        "meet them and narrow between, a fenced rim wherever the ground actually "
                        "ends, and a lit rest stop at the middle with nothing left dark")
    return meta


def _isthmus(w: World, p: dict, ctx) -> dict:
    """Both gaps, shipped as one design - `transit._line`'s own reasoning: split in two they
    would only ever be generated and looked at together, and nothing here contests a shared
    cell between them, so there is no `defer_to` question to create by splitting."""
    gaps = p.get("gaps") or GAPS
    meta = {}
    for gap in gaps:
        _build_gap(w, p, gap, meta)
    _check(w, p)
    meta["kind"] = "isthmus"
    meta["contract"] = ("the void between every pair of theme-park islands, walkable end to "
                        "end: a paved spine continuing each zone's own avenue, moss shoulders "
                        "that narrow to a neck at the midpoint and flare to meet each plot, a "
                        "fenced rim wherever the ground gives way to the two-hundred-block "
                        "drop, and a lit rest stop over each gap with zero spawnable dark")
    return meta


BUILDERS = {"isthmus": _isthmus, "reach": _reach}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**ISTHMUS, **(cfg or {})}
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown isthmus kind {p['kind']!r}; have {sorted(BUILDERS)}")
    w = World()
    meta = BUILDERS[p["kind"]](w, p, None)
    return w.canvas({
        "kind": f"isthmus/{p['kind']}",
        "facing": "south",
        "x_spine": int(p["x_spine"]),
        "contract": meta.get("contract", ""),
        **{k: v for k, v in meta.items() if k != "contract"},
    })
