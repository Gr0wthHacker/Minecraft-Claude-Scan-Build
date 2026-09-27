"""Does the water actually carry you? - a spread simulator for water rides.

**A TROUGH OF SOURCE BLOCKS IS STILL WATER.** The first log flume placed 564 water cells and every
single one was `level=0`, a source. It audited clean, cost nothing, looked exactly like a water
ride in every render, and a player dropped into it would float in a stationary channel and stop.
Jack put it plainly: *"the water slide etc are a good idea but functionally dont actually work so
it makes it difficult"*.

That is this project's cardinal sin - a machine that looks like it works - and the answer here is
the answer `circuit.py` already gave for redstone: SIMULATE IT, and let a design that cannot carry
a rider fail in a test rather than in the world an hour later.

WHAT IS MODELLED, from the game's own rules:

    a SOURCE (level 0) spreads to its four horizontal neighbours at level+1, up to level 7
    water above air FALLS; falling water is level 8 and spreads again from where it lands
    flowing water only enters a cell that is air (or already weaker water)
    a solid block stops it; the bed under a channel must be solid or the water drains away

WHAT IS NOT MODELLED, stated because a simulator trusted past its limits is worse than none:
infinite-source formation, water/lava interaction, waterlogging, and the exact sub-tick order the
game uses to pick a flow direction when two are equally downhill. None of those decide whether a
slide carries a rider; the DRY GAP does, and that is what this finds.

THE FAILURE IT EXISTS TO CATCH is a horizontal run longer than seven blocks with no new source and
no drop in it. Water dies at seven, so the eighth cell is dry, and a rider stops there - which is
exactly what "it does not work" looks like from inside the ride.
"""
from __future__ import annotations

from collections import deque

# Blocks a rider and the water both pass through. Deliberately short: anything not named here is
# treated as SOLID, which errs toward reporting a blockage that is not there rather than passing a
# channel that is. `park`/`coaster` builds use a small palette, so this covers them.
PASSABLE = {
    "air", "water", "lantern", "soul_lantern", "torch", "wall_torch", "soul_torch",
    "rail", "powered_rail", "detector_rail", "activator_rail", "ladder", "vine",
    "oak_sign", "oak_wall_sign", "spruce_wall_sign", "dark_oak_wall_sign", "lily_pad",
    "moss_carpet", "white_carpet", "red_carpet", "glow_lichen", "end_rod", "chain",
}

MAX_LEVEL = 7          # water dies at seven blocks from its source
FALLING = 8            # the level the game gives falling water


def _passable(name: str | None) -> bool:
    if name is None:
        return True                      # nothing there: air
    return name.split("[")[0] in PASSABLE


def spread(cells: dict, sources: list, bounds=None, max_steps: int = 200000) -> dict:
    """Flood water from `sources` through `cells`, returning {(x,y,z): level}.

    `cells` maps (x, y, z) -> block name, as `World.cells` does once flattened. A cell absent from
    the map is air.
    """
    level: dict = {}
    q: deque = deque()
    for s in sources:
        level[s] = 0
        q.append(s)
    steps = 0
    while q and steps < max_steps:
        steps += 1
        (x, y, z) = q.popleft()
        lv = level[(x, y, z)]
        below = (x, y - 1, z)
        if bounds is None or _in(below, bounds):
            if _passable(cells.get(below)) and level.get(below, 99) > FALLING:
                # WATER FALLS BEFORE IT SPREADS, and it spreads again from where it lands, which
                # is why a drop in a channel resets the seven-block budget.
                level[below] = FALLING
                q.append(below)
                continue
            if _passable(cells.get(below)) and below not in level:
                level[below] = FALLING
                q.append(below)
                continue
        nxt = 1 if lv == FALLING else lv + 1
        if nxt > MAX_LEVEL:
            continue
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y, z + dz)
            if bounds is not None and not _in(n, bounds):
                continue
            if not _passable(cells.get(n)):
                continue
            if level.get(n, 99) <= nxt:
                continue
            level[n] = nxt
            q.append(n)
    return level


def _in(p, b):
    (x, y, z) = p
    (x0, y0, z0, x1, y1, z1) = b
    return x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1


def carries(cells: dict, path: list, sources: list, bounds=None) -> dict:
    """Would a rider be carried along `path`? Returns a report, never a bare bool.

    `path` is the ride's own channel, in order from the top. Every cell of it must hold moving
    water: a cell with no water at all is where the rider stops, and a cell holding a SOURCE is
    where the rider floats, because a source does not push.
    """
    lv = spread(cells, sources, bounds)
    dry = [c for c in path if c not in lv]
    still = [c for c in path if lv.get(c) == 0]
    moving = [c for c in path if lv.get(c, 99) not in (0, 99)]
    # the first dry cell is the honest answer to "where does the rider stop"
    stops_at = None
    for c in path:
        if c not in lv:
            stops_at = c
            break
    return {
        "cells": len(path),
        "wet": len(path) - len(dry),
        "dry": len(dry),
        "still": len(still),
        "moving": len(moving),
        "stops_at": stops_at,
        "carries": not dry and not still,
        "levels": lv,
    }


def dry_runs(path: list, sources: set) -> list:
    """Stretches of `path` longer than the flow limit with no source in them.

    A purely geometric check, so it is usable while DESIGNING a channel rather than only after
    building one: water dies at seven, so an eighth cell with no new source and no drop is dry.
    """
    out, run = [], []
    for c in path:
        if c in sources:
            run = []
            continue
        run.append(c)
        if len(run) > MAX_LEVEL:
            out.append(list(run))
            run = []
    return out


def escapes(cells: dict, sources: list, envelope, bounds=None,
            max_steps: int = 400000) -> list:
    """Every cell the flood reaches that the design never meant water to occupy.

    **`carries` AND THIS ARE DIFFERENT QUESTIONS AND A RIDE NEEDS BOTH ANSWERED.** `carries` asks
    whether the PATH is wet and moving - it says nothing at all about the cells beside the path.
    The shipped log flume returned `carries: True` and simultaneously poured its entire channel
    out of the open head of its dock, over the apron and off the plot: 199,959 wet cells reaching
    Y-1908 before the step budget stopped counting. Every render, every audit, the bill of
    materials and the generator's own self-check passed it.

    So a water design states the cells water is ALLOWED in - its `envelope` - and this returns the
    ones it got to anyway. An empty list is the only acceptable answer. The envelope is the
    generator's own geometry (the trough interior, the pool interior), not a bounding box: a box
    round a flume contains the apron it spills onto and would have passed the shipped build.
    """
    env = {tuple(c) for c in envelope}
    lv = spread(cells, sources, bounds, max_steps)
    return sorted(c for c in lv if c not in env)


def unenclosed(cells: dict, allow=()) -> list:
    """Water blocks in `cells` with nowhere for the water to stay: no bed, or an open side.

    A STATIC check, so it is usable on a finished litematic with no idea what the design intended.
    It is deliberately weaker than `escapes`: a cell whose sideways neighbour is air is fine IF
    that neighbour has a solid bed, because water spreading one cell into a bedded trough is what
    a three-wide channel is FOR. What it catches is the two genuinely unsurvivable shapes - water
    over a hole, and water beside a hole.

    **IT IS THE CHECK FOR STILL WATER, AND A CASCADE NEEDS `allow`.** A graded channel steps down
    a course at a time, so every cell's downhill neighbour IS a hole - that is the ride. Pass the
    design's own envelope as `allow` and a hole inside it stops being a fault; a design with no
    envelope to declare is one whose water is not supposed to be going anywhere, and the default
    empty `allow` is exactly right for it.

    Returns [(cell, reason, neighbour)]. Empty is the only acceptable answer for a shipped design.
    """
    ok = {tuple(c) for c in allow}
    def water(p):
        n = cells.get(p)
        return n is not None and n.split("[")[0] == "water"

    def bedded(p):
        n = cells.get((p[0], p[1] - 1, p[2]))
        return n is not None and (not _passable(n) or n.split("[")[0] == "water")

    out = []
    for p, name in cells.items():
        if name.split("[")[0] != "water":
            continue
        if not bedded(p) and (p[0], p[1] - 1, p[2]) not in ok:
            out.append((p, "no bed", (p[0], p[1] - 1, p[2])))
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (p[0] + dx, p[1], p[2] + dz)
            if water(n) or n in ok:
                continue
            if not _passable(cells.get(n)):
                continue
            if not bedded(n):
                out.append((p, "open side over a hole", n))
    return out
