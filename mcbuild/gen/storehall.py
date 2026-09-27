"""A storage hall: chests banked around the walls of one room instead of strung along a wall.

    storehall: a rectangular room whose perimeter is chest banks, several tiers high, with a lintel
               course above them carrying the category signs and a lit open floor in the middle.

The point is topology. A linear bank costs the whole length every time you look for something; a
room costs you its half-width. Sixty-one containers on a 35-block wall become sixty-three in a room
you can cross in four steps.
"""
from __future__ import annotations

from . import protect
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
    # --- the room shell -------------------------------------------------------------------------
    # The banks alone are a freestanding ring of chests on open deck: from outside you are looking at
    # chest backs. The shell is the course-for-course wall directly behind them, so the hall reads as
    # a room rather than as furniture. It does NOT carry a ceiling - the Deck Vault already owns Y200
    # over this footprint (49 designed cells), and two designs drawing one surface is the overlap
    # problem finish.defer_to exists to stop.
    "shell": False,
    "shell_block": "stone_bricks",      # the island's own rock, dressed - same hand as the stair head
    "shell_trim": "deepslate_bricks",   # plinth and cornice. 51 darker than stone brick and the only
                                        # real value contrast this economy has at cheap-or-ok tier;
                                        # cracked/chiseled stone brick are within 4 RGB of plain and
                                        # draw no line at all.
    "shell_weather": 0.18,              # share of field cells in mossy/cracked, hashed on the CELL -
                                        # hashed on the course a whole course goes one way and the
                                        # wall comes out as horizontal stripes of one material.
    "door_high": 2,                     # courses of the doorway left open: a player is 2 tall
    "seed": 0,
}

def _container_state(name: str, facing: str) -> dict:
    """Only the properties this container actually declares, filled from its own defaults."""
    from .. import blocks
    legal = blocks.props(name)
    if not legal:                                    # knowledge base absent: chest-shaped guess
        return {"facing": facing, "type": "single", "waterlogged": "false"}
    st = dict(blocks.default(name))
    if "facing" in legal:
        st["facing"] = facing
    return {k: v for k, v in st.items() if k in legal}


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
    labels = list(p.get("labels") or [])
    placed, labelled = 0, 0
    for wall, cells in runs:
        for (x, z) in cells:
            # only the courses this hall actually occupies: chests plus the lintel. Checking one
            # higher hits the vault's coffer beams at Y200 and silently drops half the banks.
            if (x, z) in blocked or (ctx is not None and _busy(ctx, x, fy, z, tiers + 1)):
                continue
            for t in range(tiers):
                # This hall serves chests AND barrels, and they take different properties: a chest has
                # type/waterlogged, a barrel has facing/open. Emitting the chest set on a barrel is an
                # illegal state the game refuses - ask the registry which properties this one has.
                w.put(x, fy + 1 + t, z, p["chest"], **_container_state(p["chest"], INWARD[wall]))
                placed += 1
            w.put(x, fy + 1 + tiers, z, p["lintel"])
    labelled = _signs(ctx, w, runs, blocked, x1, z1, x2, z2, fy, tiers, p)
    lit = _lights(ctx, w, runs, blocked, x1, z1, x2, z2, fy, tiers, p, seed)
    walled, doorway = _shell(ctx, w, x1, z1, x2, z2, fy, tiers, p, seed)

    # WHICH BANK IS WHICH, recorded whether or not anything was placed this run. Once the hall is
    # built the design emits nothing - `chests: 0` - so a tool that reads the design to find out
    # where the "food and crops" wall is would learn nothing at exactly the point it matters. The
    # labels are the design's INTENT and they outlive its remaining work.
    banks = {}
    for i, (wall, cells) in enumerate(runs):
        label = labels[i] if i < len(labels) else ""
        banks[wall] = {"label": label,
                       "cells": [[int(x), int(z)] for (x, z) in cells]}

    return w.canvas({"kind": "storehall", "box": [x1, z1, x2, z2], "floor_y": fy,
                     "chests": placed, "signs": labelled, "lanterns": lit,
                     "shell": walled, "doorway": doorway,
                     "tiers": tiers, "banks": banks,
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


def _shell(ctx, w: World, x1, z1, x2, z2, fy, tiers, p, seed):
    """The wall course-for-course behind the chest banks, with the doorway derived from the banks.

    Two things here are measured rather than configured, and both are the same lesson:

    - The DOORWAY is wherever the bank run is actually open, not `door`/`door_width`. Those two say
      where the generator INTENDED a gap; the chests standing in the world are where the gap really
      is. On this hall they disagree - the config asks for three cells and the world has one, because
      Jack filled two of them when he moved the containers in. Walling to the config would have built
      a doorway into the back of a chest and bricked up the only way in.
    - The CORNERS of the bank ring carry no chest (a corner chest faces two ways and can face only
      one), so they are gaps in the ring. They are filled solid, which turns four holes into four
      corner piers.
    """
    if not p.get("shell"):
        return 0, 0
    field, trim = p["shell_block"], p["shell_trim"]
    y0, y1 = fy + 1, fy + 1 + tiers          # plinth course .. cornice course, inclusive
    weather = float(p["shell_weather"])
    dh = int(p["door_high"])

    # --- where is the bank run actually open? ---------------------------------------------------
    # a bank cell counts as open when neither this design nor the world puts anything in it
    def bank_open(x, z):
        if w.has(x, y0, z):
            return False
        return ctx is None or ctx.name_at(x, y0, z) in AIRY

    # map each bank-ring cell to the shell cell directly behind it
    behind = {}
    for x in range(x1, x2 + 1):
        behind[(x, z1)] = (x, z1 - 1)
        behind[(x, z2)] = (x, z2 + 1)
    for z in range(z1, z2 + 1):
        behind[(x1, z)] = (x1 - 1, z)
        behind[(x2, z)] = (x2 + 1, z)
    corners = {(x1, z1), (x1, z2), (x2, z1), (x2, z2)}
    # The opening is the INTERSECTION of where a door was asked for and where the banks are really
    # open. Either half alone is wrong: the config alone walls a doorway into the back of a chest,
    # and "wherever the banks are open" alone turns every cell a fixture happened to block into a
    # second hole in the wall - a gap in the banks is not a door.
    intended = {c for c in _walls_door_cells(x1, z1, x2, z2, p) if c not in corners}
    door_cells = {behind[c] for c in intended if bank_open(*c)}

    # --- the shell ring -------------------------------------------------------------------------
    ring = [(x, z) for x in range(x1 - 1, x2 + 2) for z in range(z1 - 1, z2 + 2)
            if x in (x1 - 1, x2 + 1) or z in (z1 - 1, z2 + 1)]
    placed = 0
    for (x, z) in ring:
        for y in range(y0, y1 + 1):
            if (x, z) in door_cells and y < y0 + dh:
                continue                                   # the opening
            if w.has(x, y, z):
                continue
            if ctx is not None:
                n = ctx.name_at(x, y, z)
                if n not in AIRY:
                    continue                               # never cover what is already there
                if protect.is_protected(n):
                    continue
            if y == y0 or y == y1:
                b = trim                                   # plinth and cornice draw the horizontals
            else:
                b = _weathered(field, x, y, z, weather, seed)
            w.put(x, y, z, b)
            placed += 1

    # --- corner piers ---------------------------------------------------------------------------
    for (x, z) in corners:
        for y in range(y0, y1 + 1):
            if w.has(x, y, z):
                continue
            if ctx is not None:
                n = ctx.name_at(x, y, z)
                if n not in AIRY or protect.is_protected(n):
                    continue
            w.put(x, y, z, trim if y in (y0, y1) else _weathered(field, x, y, z, weather, seed))
            placed += 1
    return placed, len(door_cells)


def _weathered(field: str, x, y, z, rate: float, seed: int) -> str:
    """Hashed on the CELL. Hashed on the course, every block in a course comes out identical and the
    wall reads as horizontal stripes of one material - that shipped once in the deck soffit."""
    if rate <= 0:
        return field
    h = hash01(x, y, z, seed + 977)
    if h < rate * 0.6:
        return "mossy_stone_bricks"
    if h < rate:
        return "cracked_stone_bricks"
    return field


def _walls_door_cells(x1, z1, x2, z2, p) -> set:
    """The bank cells `_walls` cuts for the doorway - the same arithmetic, so the two cannot drift."""
    runs = {
        "north": [(x, z1) for x in range(x1 + 1, x2)],
        "south": [(x, z2) for x in range(x1 + 1, x2)],
        "west": [(x1, z) for z in range(z1 + 1, z2)],
        "east": [(x2, z) for z in range(z1 + 1, z2)],
    }
    cells = runs.get(p["door"], [])
    dw = int(p["door_width"])
    if not cells or dw <= 0:
        return set()
    mid = len(cells) // 2
    lo = max(0, mid - dw // 2)
    return set(cells[lo:lo + dw])
