"""Can a player actually get there? - a walk flood fill, with the movement model stated.

**A REACHABILITY NUMBER MEANS NOTHING WITHOUT THE MOVEMENT MODEL STATED BESIDE IT.** This repo has
that in writing already, from the court stair: the same site read 1,268 standable cells on a fixed
course, 36 with four-block falls allowed, and 248 on a true walk - three different answers to "can
you get there", every one correct for the question it asked, and the first of them declared a court
orphaned that was not. So the model is here, in one place, and every caller gets the same one.

    a cell is OPEN if nothing is there or the block does not stop a body
    you STAND in an open cell with an open cell over your head and something solid under your feet
    you also stand on a LADDER, and a ladder is the only way to move straight up or down
    you step UP one course, with a clear cell over your own head to do it in
    you step DOWN one course - one, not four: this is a walk, and every route it finds is
      reversible, which is what makes it a route rather than a drop

Nothing about sprinting, jumping gaps, swimming or falling damage is modelled. A route this finds
is one a player can walk both ways; a route it misses may still be survivable one way down.
"""
from __future__ import annotations

from collections import deque

# Blocks a body passes through. Anything not named is solid, which errs toward reporting a route
# BLOCKED that is walkable rather than promising one that is not - the safe direction for a
# walkthrough attraction, whose whole contract is that you can get from one end to the other.
PASSABLE = {
    "air", "cave_air", "void_air", "ladder", "rail", "powered_rail", "detector_rail",
    "activator_rail", "torch", "wall_torch", "soul_torch", "redstone_torch", "lantern",
    "soul_lantern", "vine", "lily_pad", "glow_lichen", "tripwire", "redstone_wire",
    "lever", "stone_button", "oak_button", "spruce_button", "chain", "end_rod",
    "oak_sign", "spruce_sign", "dark_oak_sign", "oak_wall_sign", "spruce_wall_sign",
    "dark_oak_wall_sign", "white_carpet", "red_carpet", "moss_carpet", "flower_pot",
    "stone_pressure_plate", "oak_pressure_plate", "spruce_pressure_plate",
    "cobweb", "water",
}

# Passable AND climbable: the only cells a body may move vertically through.
CLIMB = {"ladder", "vine", "scaffolding"}

# A door or a fence gate is a hole you can open, so a route through one is a real route. They are
# kept apart from PASSABLE because a CLOSED door is not a cell you may stand IN.
DOORS = {"oak_door", "spruce_door", "dark_oak_door", "iron_door",
         "oak_fence_gate", "spruce_fence_gate", "dark_oak_fence_gate"}


def _bare(n):
    return None if n is None else n.split("[")[0].split(":")[-1]


def _open(cells, p) -> bool:
    n = _bare(cells.get(p))
    return n is None or n in PASSABLE or n in DOORS


def _climb(cells, p) -> bool:
    return _bare(cells.get(p)) in CLIMB


def stands(cells, p) -> bool:
    """Could a player be standing here: room for the body, and something under the feet."""
    (x, y, z) = p
    if not (_open(cells, p) and _open(cells, (x, y + 1, z))):
        return False
    return _climb(cells, p) or not _open(cells, (x, y - 1, z))


def reachable(cells: dict, start, limit: int = 400000) -> set:
    """Every cell a player can walk or climb to from `start`, under the model above.

    `cells` maps (x, y, z) -> block name, as `World.cells` does once flattened.
    """
    start = tuple(start)
    if not stands(cells, start):
        return set()
    seen = {start}
    q = deque([start])
    while q and len(seen) < limit:
        (x, y, z) = q.popleft()
        cand = []
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                t = (x + dx, y + dy, z + dz)
                if dy == 1 and not _open(cells, (x, y + 2, z)):
                    continue                       # no headroom to climb into
                if dy == 1 and not _open(cells, (x + dx, y + 2, z)):
                    continue
                if dy == -1 and not _open(cells, (x + dx, y, z + dz)):
                    continue                       # nothing to step down THROUGH
                cand.append(t)
        if _climb(cells, (x, y, z)):
            cand += [(x, y + 1, z), (x, y - 1, z)]
        for t in cand:
            if t in seen or not stands(cells, t):
                continue
            seen.add(t)
            q.append(t)
    return seen


def connects(cells: dict, a, b) -> bool:
    """Is `b` walkable from `a`? The one question a walkthrough attraction has to answer yes to."""
    return tuple(b) in reachable(cells, a)
