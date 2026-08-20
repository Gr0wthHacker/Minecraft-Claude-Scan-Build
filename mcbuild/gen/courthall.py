"""The sky-well court as a hall: an order raised on the deepslate Jack laid, glazed where there is
something to look at, and a black basin in the sunken bay.

    courthall: piers and glazing raised off an existing plinth course, with the treatment of each
               run DERIVED from what is behind it, plus a contained pool for the lower bay.

## What the site actually is, because it decided everything

The court is a **one-block shelf hanging in the void**. Measured off the 10:58 capture, the column
at x-24229 has exactly one solid course between Y150 and the plate: Y194. Rock closes it east and
west; both ENDS have fallen away into open sky; the island's underside is the ceiling at Y201/202.

That is why this file does not glaze the long sides:

| run | outside is open at Y196-200 |
|---|---|
| west  x-24234 | **0%**  - solid rock |
| east  x-24222 | **8%**  - rock and moss |
| north end z30006 | **95%** - open void |
| south end z30029 | **96%** - open void |

Glass in front of rock is a window onto stone. So the rule here is measured, never configured:
**a bay is glazed when the space behind it is open, and solid when it is not.** Same discipline as
the store hall deriving its doorway from where the banks really are.

## Ruin is applied to an order, never instead of one

The void tower already paid for this lesson: *what makes voxels read as ARCHITECTURE is regularity
and openings, not damage* - its first sheared, jagged attempt was rejected on sight as "a tossed
grouping of vague blocks". So every bay keeps its pier and its cornice; what the ruin takes is
GLASS, from the top down. A building that has taken damage, not damage that suggests a building.

## The pool freezes if you let it

The court is open to the sky in a SNOWY biome and **this exact court has frozen before** - 29 ice
blocks on the first build, which is why `court.yaml` carries `freeze_guard`. Water needs block
light >= 10 or it turns to ice. 16 of the sunken bay's 55 columns are open sky, so the guard is not
optional. Plain `lantern` is light 15; `soul_lantern` is exactly 10 and is one block of falloff
away from failing, so the guard lanterns are plain and the soul lanterns are mood only.

And the basin is built as a TANK. The bay's floor is a one-block skin over nothing, so water placed
on it drains into the void and water not walled on its east side runs out past x-24222, where the
Y194 course continues. Floor, four walls, then water.

## Palette, and why there is no stained glass

On this economy `glass_pane` is **ok** and every stained pane, plain `glass` and `tinted_glass` is
**expensive**. There are 1,060 glass in store (~2,800 panes) and 26-49 of each stained pane, so the
cheap material is also the only one there is enough of. The order is `deepslate_bricks` - Jack's own
edging block, `ok` tier, and 51 darker than stone brick, which is the one real value contrast this
economy has. Cracked and chiseled stone brick are within 4 RGB of plain and draw no line at all.
"""
from __future__ import annotations

from . import protect
from .canvas import Canvas, hash01
from .vertical import Ctx, World

COURTHALL = {
    "under": None,
    "box": None,                    # [x1, z1, x2, z2] the court extent to consider
    "plinth_y": 195,                # the course Jack laid; the order starts one above it
    "plinth_block": "deepslate_bricks",   # READ, never re-laid - it is already in world
    "bay": 3,                       # pier rhythm along a run
    "pier": "deepslate_bricks",
    "glaze": "glass_pane",
    "cornice": "deepslate_bricks",
    "height": 5,                    # courses above the plinth, clipped to real headroom
    "min_height": 3,                # below this a bay is not worth raising
    "open_probe": 4,                # cells to look outward to call a run "open"
    "open_frac": 0.6,               # ... and the share of probed cells that must be air
    "ruin": 0.34,                   # share of glazed bays that lose their top glass course
    "ruin_hard": 0.13,              # ... and the share that lose all of it
    "weather": 0.16,
    # --- the divider between the raised and sunken bays -----------------------------------------
    "balustrade": True,
    "balustrade_block": "deepslate_brick_wall",
    # --- the pool -------------------------------------------------------------------------------
    "pool_box": None,               # [x1, z1, x2, z2] water footprint; None to skip the pool
    "pool_surface_y": 194,          # water course; its top face is the sunken bay's walking level
    "pool_floor_block": "deepslate_bricks",
    "kerb_box": None,               # [x1,z1,x2,z2] perimeter laid at plinth_y as a slab lip
    "kerb_block": "smooth_stone_slab",
    "guard_light": "lantern",       # light 15. soul_lantern is 10 and freezes one block out
    "guard_every": 4,
    "mood_light": "soul_lantern",
    "mood_every": 6,
    "container_clear": 3,
    "clear_exempt_plinth": True,    # the perimeter runs ignore it - see _order
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air")
PASSABLE = set(AIRY) | {"vine", "glow_lichen", "moss_carpet", "short_grass", "tall_grass", "fern",
                        "azalea", "flowering_azalea", "pointed_dripstone"}
FIXTURES = ("chest", "barrel", "furnace", "hopper", "shulker", "crafting_table", "anvil",
            "dispenser", "observer", "piston", "lever", "spawner", "lectern")


def build_courthall(cfg: dict, donors=None) -> Canvas:
    p = {**COURTHALL, **cfg}
    if not p.get("box"):
        raise ValueError("courthall needs params.box = [x1, z1, x2, z2]")
    ctx = Ctx(p["under"]) if p.get("under") else None
    if ctx is None:
        raise ValueError("courthall reads the plinth off a capture; params.under is required")
    w = World()
    seed = int(p["seed"])
    x1, z1, x2, z2 = (int(v) for v in p["box"])
    x1, x2 = min(x1, x2), max(x1, x2)
    z1, z2 = min(z1, z2), max(z1, z2)
    py = int(p["plinth_y"])

    plinth = {(x, z) for x in range(x1, x2 + 1) for z in range(z1, z2 + 1)
              if ctx.name_at(x, py, z) == p["plinth_block"]}
    blocked = _fixtures(ctx, x1, z1, x2, z2, py, int(p["container_clear"]))
    runs = _runs(plinth)

    counts = {"piers": 0, "panes": 0, "cornice": 0, "solid": 0, "balustrade": 0,
              "glazed_runs": 0, "solid_runs": 0, "internal_runs": 0}
    for cells, axis in runs:
        kind = _kind(ctx, cells, axis, p)
        counts[kind + "_runs"] += 1
        if kind == "internal":
            counts["balustrade"] += _balustrade(ctx, w, cells, py, p, blocked)
        else:
            _order(ctx, w, cells, axis, py, p, seed, blocked, glazed=(kind == "glazed"), counts=counts)

    pool = _pool(ctx, w, p, seed) if p.get("pool_box") else {}
    pool["kerb"] = _kerb(ctx, w, p)

    meta = {"kind": "courthall", "box": [x1, z1, x2, z2], "plinth": len(plinth),
            "runs": len(runs), **counts, **pool}
    return w.canvas(meta)


# ---------------------------------------------------------------------------- the plinth, in runs

def _runs(plinth: set):
    """Group the plinth into straight runs. A cell can belong to both a row and a column (the
    corners do); the longer run wins, so a corner is raised once, not twice."""
    byx, byz = {}, {}
    for (x, z) in plinth:
        byx.setdefault(x, []).append(z)
        byz.setdefault(z, []).append(x)
    out, taken = [], set()
    cand = []
    for x, zs in byx.items():
        for seg in _segments(sorted(zs)):
            cand.append(([(x, z) for z in seg], "z"))
    for z, xs in byz.items():
        for seg in _segments(sorted(xs)):
            cand.append(([(x, z) for x in seg], "x"))
    for cells, axis in sorted(cand, key=lambda c: -len(c[0])):
        keep = [c for c in cells if c not in taken]
        if len(keep) < 3:
            continue
        taken.update(keep)
        out.append((keep, axis))
    return out


def _segments(vals, gap=1):
    seg, out = [], []
    for v in vals:
        if seg and v - seg[-1] > gap:
            out.append(seg); seg = []
        seg.append(v)
    if seg:
        out.append(seg)
    return out


def _kind(ctx, cells, axis, p) -> str:
    """glazed / solid / internal, decided by what is BEHIND the run.

    The perpendicular direction has to be resolved into INWARD and OUTWARD first. Scoring both and
    taking the more open one is wrong in the specific way that matters here: the room's own interior
    is open by definition, so every run scores as open and the rock flanks come out GLAZED - a
    window onto stone, which is what this file exists to avoid. Inward is the side that carries the
    court FLOOR; outward is the other one.

    A window onto rock is not a window. The two long sides of this court are the island's own flanks
    and measure 0% and 8% open; the two ends are 95% and 96%. None of that is guessable."""
    probe, frac = int(p["open_probe"]), float(p["open_frac"])
    py = int(p["plinth_y"])
    dirs = [(1, 0), (-1, 0)] if axis == "z" else [(0, 1), (0, -1)]
    score = {}
    for d in dirs:
        floor = air = tot = 0
        for (x, z) in cells:
            for k in range(1, probe + 1):
                ax, az = x + d[0] * k, z + d[1] * k
                tot += 1
                if any(ctx.name_at(ax, y, az) not in PASSABLE for y in (py, py - 1)):
                    floor += 1
                if all(ctx.name_at(ax, y, az) in PASSABLE for y in range(py + 1, py + 5)):
                    air += 1
        score[d] = (floor / max(tot, 1), air / max(tot, 1))
    inward = max(dirs, key=lambda d: score[d][0])          # the side with the court floor under it
    outward = [d for d in dirs if d != inward][0]
    out_floor, out_air = score[outward]
    # What is behind it is settled by what is ABOVE, not by what is underfoot. Rock and court floor
    # both read as "solid below" - the island's flank and the room's own paving are equally floor -
    # so a test written on that alone calls the rock flanks internal dividers. The three cases
    # separate cleanly one course up: rock is closed above, court is open above AND floored below,
    # void is open above with nothing under it at all.
    if out_air < 0.5:
        return "solid"                                      # the island's own flank: a wall
    if out_floor > 0.5:
        return "internal"                                   # court on both sides: a divider
    return "glazed" if out_air >= frac else "solid"


# ------------------------------------------------------------------------------------- the order

def _order(ctx, w: World, cells, axis, py, p, seed, blocked, glazed: bool, counts):
    """Piers on the bay rhythm, glazing between them where there is a view, cornice over both."""
    bay, hmax = int(p["bay"]), int(p["height"])
    cells = sorted(cells, key=lambda c: c[1] if axis == "z" else c[0])
    exempt = bool(p.get("clear_exempt_plinth", True))
    for i, (x, z) in enumerate(cells):
        if (x, z) in blocked and not exempt:
            continue
        head = _headroom(ctx, w, x, py, z, hmax)
        if head < int(p["min_height"]):
            continue
        is_pier = (i % bay == 0) or i == len(cells) - 1
        if is_pier:
            for k in range(head):
                _put(ctx, w, x, py + 1 + k, z, _weathered(p["pier"], x, py + 1 + k, z, float(p["weather"]), seed))
            counts["piers"] += 1
            if _put(ctx, w, x, py + 1 + head, z, p["cornice"]):
                counts["cornice"] += 1
            continue
        # --- between the piers ------------------------------------------------------------------
        if not glazed:
            # Nothing. A run with rock behind it gets PILASTERS, not infill: the island's flank is
            # the most apocalyptic surface in the room and filling 24x5 cells of deepslate over it
            # would hide the ruin behind a tidy wall - and cost 120 blocks to make the hall duller.
            # The surviving order is the piers; the rock between them is the point.
            continue
        else:
            lost = _ruin(x, z, seed, float(p["ruin"]), float(p["ruin_hard"]))
            for k in range(head):
                if lost == 2 or (lost == 1 and k >= head - 1):
                    continue                          # the damage takes GLASS, never the order
                st = _pane_state(axis)
                if _put(ctx, w, x, py + 1 + k, z, p["glaze"], **st):
                    counts["panes"] += 1
        if _put(ctx, w, x, py + 1 + head, z, p["cornice"]):
            counts["cornice"] += 1
    _lights(ctx, w, cells, axis, py, p, seed, blocked, counts)


def _pane_state(axis) -> dict:
    """A pane with every side false renders as a lone post, not as glazing. It has to be told which
    way its own wall runs."""
    if axis == "z":
        return {"north": "true", "south": "true", "east": "false", "west": "false",
                "waterlogged": "false"}
    return {"east": "true", "west": "true", "north": "false", "south": "false",
            "waterlogged": "false"}


def _ruin(x, z, seed, soft, hard) -> int:
    h = hash01(x, 0, z, seed + 4409)
    if h < hard:
        return 2
    return 1 if h < hard + soft else 0


def _headroom(ctx, w, x, py, z, hmax) -> int:
    """How many courses are really free over this plinth cell. The ceiling here is the island's own
    underside and it steps; forcing one height either buries the order or leaves it short."""
    n = 0
    for k in range(hmax):
        y = py + 1 + k
        nme = ctx.name_at(x, y, z)
        if nme not in PASSABLE or protect.is_protected(nme):
            break
        n += 1
    return n


def _lights(ctx, w, cells, axis, py, p, seed, blocked, counts):
    every = int(p["mood_every"])
    if not every or not p.get("mood_light"):
        return
    for i, (x, z) in enumerate(cells):
        if i % every or (x, z) in blocked:
            continue
        head = _headroom(ctx, w, x, py, z, int(p["height"]))
        if head < 2:
            continue
        y = py + head                                  # hung just under the cornice
        if w.name(x, y, z) not in (None, p["glaze"]):
            continue
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ax, az = x + d[0], z + d[1]
            if w.has(ax, y, az) or ctx.name_at(ax, y, az) not in PASSABLE:
                continue
            if ctx.name_at(ax, y + 1, az) in PASSABLE and not w.has(ax, y + 1, az):
                continue                               # a hanging lantern needs a ceiling
            w.put(ax, y, az, p["mood_light"], hanging="true", waterlogged="false")
            counts["lanterns"] = counts.get("lanterns", 0) + 1
            break


def _balustrade(ctx, w: World, cells, py, p, blocked) -> int:
    """The step between the raised bay and the sunken one: low enough to see the water over."""
    if not p.get("balustrade"):
        return 0
    n = 0
    for (x, z) in cells:
        if (x, z) in blocked:
            continue
        if _put(ctx, w, x, py + 1, z, p["balustrade_block"], up="true", north="none",
                south="none", east="none", west="none", waterlogged="false"):
            n += 1
    return n


def _kerb(ctx, w: World, p) -> int:
    """A slab lip on the plinth course, just inside the bay's frame.

    Jack added this by hand after the hall went up and it is the right detail - a half-height ring
    round the basin, so the deepslate frame reads as an edge you look over rather than a wall you
    walk into. It lives in the config now so a regeneration records it rather than merely failing to
    disturb it: designs here are remaining-work, and remaining-work forgets anything it never knew."""
    if not p.get("kerb_box"):
        return 0
    x1, z1, x2, z2 = (int(v) for v in p["kerb_box"])
    x1, x2 = min(x1, x2), max(x1, x2)
    z1, z2 = min(z1, z2), max(z1, z2)
    y = int(p["plinth_y"])
    n = 0
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            if not (x in (x1, x2) or z in (z1, z2)):
                continue
            if _put(ctx, w, x, y, z, p["kerb_block"], type="top", waterlogged="false"):
                n += 1
    return n


# ---------------------------------------------------------------------------------------- the pool

def _pool(ctx, w: World, p, seed) -> dict:
    """A tank, not a puddle. Floor, four walls, water, then the freeze guard."""
    x1, z1, x2, z2 = (int(v) for v in p["pool_box"])
    x1, x2 = min(x1, x2), max(x1, x2)
    z1, z2 = min(z1, z2), max(z1, z2)
    sy = int(p["pool_surface_y"])
    floor_y = sy - 1
    made = {"pool_water": 0, "pool_floor": 0, "pool_wall": 0, "pool_guard": 0}
    water = [(x, z) for x in range(x1, x2 + 1) for z in range(z1, z2 + 1)]
    for (x, z) in water:
        if _put(ctx, w, x, floor_y, z, p["pool_floor_block"], force=True):
            made["pool_floor"] += 1
    # the wall is the ring OUTSIDE the water, at the water course and the floor course, so the tank
    # cannot drain sideways into the void or east past the plinth line
    for x in range(x1 - 1, x2 + 2):
        for z in range(z1 - 1, z2 + 2):
            if x1 <= x <= x2 and z1 <= z <= z2:
                continue
            for y in (floor_y, sy):
                if _put(ctx, w, x, y, z, _weathered(p["pool_floor_block"], x, y, z, float(p["weather"]), seed)):
                    made["pool_wall"] += 1
    guard = int(p["guard_every"])
    for i, (x, z) in enumerate(sorted(water)):
        on_edge = x in (x1, x2) or z in (z1, z2)
        if guard and on_edge and i % guard == 0:
            # Set INTO the floor, so it lights the water from beneath. Two things about this cell:
            # a lantern is not a full cube and the bay's floor is a skin over open VOID, so it needs
            # its own footing (without one it audits as "standing on air"); and it is WATERLOGGED,
            # because the water above would otherwise flow down into it - and skipping the water
            # here instead leaves a hole punched through the surface of the pool at every guard.
            w.put(x, floor_y - 1, z, p["pool_floor_block"])
            w.put(x, floor_y, z, p["guard_light"], hanging="false", waterlogged="true")
            made["pool_guard"] += 1
        if _put(ctx, w, x, sy, z, "water", level="0", force=True):
            made["pool_water"] += 1
    return made


# ------------------------------------------------------------------------------------------ util

def _put(ctx, w: World, x, y, z, name, force=False, **props) -> bool:
    if w.has(x, y, z):
        return False
    if ctx is not None:
        nme = ctx.name_at(x, y, z)
        if protect.is_protected(nme) and nme not in PASSABLE:
            return False                               # never cover a mechanism or a container
        if not force and nme not in PASSABLE:
            return False                               # never cover what is already standing
    w.put(x, y, z, name, **props)
    return True


def _fixtures(ctx, x1, z1, x2, z2, py, clear) -> set:
    """Cells within `clear` of anything installed. Rule 10, read off the capture rather than written
    down: the four chests in this court are Jack's build supply and they will move."""
    if clear <= 0:
        return set()
    out = set()
    for x in range(x1 - clear, x2 + clear + 1):
        for z in range(z1 - clear, z2 + clear + 1):
            for y in range(py - 2, py + 7):
                if any(k in ctx.name_at(x, y, z) for k in FIXTURES):
                    for dx in range(-clear, clear + 1):
                        for dz in range(-clear, clear + 1):
                            out.add((x + dx, z + dz))
                    break
    return out


def _weathered(field: str, x, y, z, rate: float, seed: int) -> str:
    """Hashed on the CELL. Hashed on the course a wall comes out as horizontal stripes of one
    material - the deck soffit shipped exactly that once."""
    if rate <= 0 or not field.startswith("deepslate"):
        return field
    h = hash01(x, y, z, seed + 1811)
    return "cracked_deepslate_bricks" if h < rate else field
