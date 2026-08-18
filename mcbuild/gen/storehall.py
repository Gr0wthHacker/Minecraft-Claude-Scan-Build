"""A storage hall: chests banked around the walls of one room instead of strung along a wall.

    storehall: a rectangular room whose perimeter is chest banks, several tiers high, with a lintel
               course above them carrying the category signs and a lit open floor in the middle.

The point is topology. A linear bank costs the whole length every time you look for something; a
room costs you its half-width. Sixty-one containers on a 35-block wall become sixty-three in a room
you can cross in four steps.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .vertical import Ctx, World

STOREHALL = {
    "under": None,             # capture: nothing is placed where the world already holds something
    "box": None,               # [x1, z1, x2, z2] the room's floor, walls included
    "floor_y": 194,            # the deck slab it stands on
    "tiers": 3,                # chest courses above the floor
    "door": "west",            # which wall the doorway is in
    "door_width": 3,
    "chest": "chest",
    "lintel": "stone_bricks",  # course above the top tier; the signs hang off it
    "sign": "oak_wall_sign",
    "labels": [],              # one per bank run, in order
    "lantern_every": 4,        # a lantern in the lintel course every N cells
    "clear": 3,                # never build within this of a fixture already in the world
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air", "vine")
FIXTURES = ("chest", "barrel", "furnace", "hopper", "shulker", "crafting_table", "anvil",
            "dispenser", "observer", "piston", "lever", "comparator", "repeater", "spawner")
# facing names the direction a chest's front looks, so a bank on the north wall faces south
INWARD = {"north": "south", "south": "north", "east": "west", "west": "east"}


def build_storehall(cfg: dict, donors=None) -> Canvas:
    p = {**STOREHALL, **cfg}
    if not p.get("box"):
        raise ValueError("storehall needs params.box = [x1, z1, x2, z2]")
    ctx = Ctx(p["under"]) if p.get("under") else None
    x1, z1, x2, z2 = (int(v) for v in p["box"])
    x1, x2 = min(x1, x2), max(x1, x2)
    z1, z2 = min(z1, z2), max(z1, z2)
    fy, tiers, seed = int(p["floor_y"]), int(p["tiers"]), int(p["seed"])

    blocked = _fixtures(ctx, x1, z1, x2, z2, fy, int(p["clear"]))
    w = World()
    runs = _walls(x1, z1, x2, z2, p)
    placed, labelled = 0, 0
    for wall, cells in runs:
        for (x, z) in cells:
            # only the courses this hall actually occupies: chests plus the lintel. Checking one
            # higher hits the vault's coffer beams at Y200 and silently drops half the banks.
            if (x, z) in blocked or (ctx is not None and _busy(ctx, x, fy, z, tiers + 1)):
                continue
            for t in range(tiers):
                w.put(x, fy + 1 + t, z, p["chest"], facing=INWARD[wall], type="single",
                      waterlogged="false")
                placed += 1
            w.put(x, fy + 1 + tiers, z, p["lintel"])
    labelled = _signs(ctx, w, runs, blocked, x1, z1, x2, z2, fy, tiers, p)
    lit = _lights(ctx, w, runs, blocked, x1, z1, x2, z2, fy, tiers, p, seed)

    return w.canvas({"kind": "storehall", "box": [x1, z1, x2, z2], "floor_y": fy,
                     "chests": placed, "signs": labelled, "lanterns": lit,
                     "interior": (x2 - x1 - 1) * (z2 - z1 - 1)})


def _fixtures(ctx, x1, z1, x2, z2, fy, clear) -> set:
    """Cells within `clear` of anything already installed - the working room rule, read off the world."""
    if ctx is None or clear <= 0:
        return set()
    out = set()
    for x in range(x1 - clear, x2 + clear + 1):
        for z in range(z1 - clear, z2 + clear + 1):
            for y in range(fy - 4, fy + 8):
                if any(k in ctx.name_at(x, y, z) for k in FIXTURES):
                    for dx in range(-clear, clear + 1):
                        for dz in range(-clear, clear + 1):
                            out.add((x + dx, z + dz))
                    break
    return out


def _busy(ctx: Ctx, x, fy, z, height) -> bool:
    return any(ctx.name_at(x, fy + 1 + k, z) not in AIRY for k in range(height))


def _walls(x1, z1, x2, z2, p):
    """The four wall runs, corners left out, with the doorway cut from one of them."""
    runs = {
        "north": [(x, z1) for x in range(x1 + 1, x2)],
        "south": [(x, z2) for x in range(x1 + 1, x2)],
        "west": [(x1, z) for z in range(z1 + 1, z2)],
        "east": [(x2, z) for z in range(z1 + 1, z2)],
    }
    door, dw = p["door"], int(p["door_width"])
    cells = runs[door]
    if cells and dw > 0:
        mid = len(cells) // 2
        keep = set(range(len(cells))) - set(range(max(0, mid - dw // 2), min(len(cells), mid - dw // 2 + dw)))
        runs[door] = [c for i, c in enumerate(cells) if i in keep]
    return [(k, v) for k, v in runs.items() if v]


def _signs(ctx, w: World, runs, blocked, x1, z1, x2, z2, fy, tiers, p) -> int:
    """One sign a bank, hung off the lintel and facing into the room."""
    y = fy + 1 + tiers
    off = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}
    n = 0
    labels = list(p["labels"])
    for wall, cells in runs:
        live = [c for c in cells if (c[0], c[1]) not in blocked and w.has(c[0], fy + 1, c[1])]
        if not live:
            continue
        x, z = live[len(live) // 2]
        dx, dz = off[wall]
        sx, sz = x + dx, z + dz
        if w.has(sx, y, sz) or (ctx is not None and ctx.name_at(sx, y, sz) not in AIRY):
            continue
        w.put(sx, y, sz, p["sign"], facing=INWARD[wall], waterlogged="false")
        n += 1
        if labels:
            labels.pop(0)
    return n


def _lights(ctx, w: World, runs, blocked, x1, z1, x2, z2, fy, tiers, p, seed) -> int:
    """Lanterns hung under the lintel so the banks are lit and nothing spawns on the floor."""
    lintel_y = fy + 1 + tiers                        # the course the corbel joins
    off = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}
    n = 0
    for wall, cells in runs:
        dx, dz = off[wall]
        for i, (x, z) in enumerate(cells):
            if i % int(p["lantern_every"]) or (x, z) in blocked or not w.has(x, fy + 1, z):
                continue
            lx, lz = x + dx, z + dz
            # A hanging lantern needs a block directly above it, and the lintel sits in the WALL
            # plane, not over the aisle. Corbel one cell inward and hang the lantern under that.
            if w.has(lx, lintel_y, lz) or (ctx is not None and ctx.name_at(lx, lintel_y, lz) not in AIRY):
                continue
            if w.has(lx, lintel_y - 1, lz) or (ctx is not None and ctx.name_at(lx, lintel_y - 1, lz) not in AIRY):
                continue
            w.put(lx, lintel_y, lz, p["lintel"])
            w.put(lx, lintel_y - 1, lz, "lantern", hanging="true", waterlogged="false")
            n += 1
    return n
