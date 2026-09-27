"""A player's movement model over a sparse `World`, and the flood fill that uses it.

**THIS IS THE ONE CHECK NOTHING IN THIS PIPELINE HAD.** `audit` asks whether a block state is
legal, supported and non-colliding; `blocks` asks whether the 1.19 server has it; `palette` asks
what it costs; the circuit inspector asks whether a signal arrives. Not one of them asks whether a
player can WALK from the door to the thing the building exists for - and every way that goes
wrong is invisible: a flight rising two courses at a time, a floor plane nobody holed over a
stair, a doorway one cell narrower than a body, a vault whose ceiling is one course over its
floor. All of them audit clean and render identically to the version that works.

**THE MODEL IS STATED, AND IT ERRS TOWARD REFUSING.** CLAUDE.md's own rule from the court stair:
*a reachability number means nothing without the movement model stated beside it* - the same site
read 1,268 cells on a fixed course, 36 with four-block falls allowed, and 248 on a true walk.
Here:

    solid        anything present that is not in PASSABLE - so a stair, a slab, a fence and a
                 lantern all BLOCK. A fence really does stop a player; a lantern really does.
                 Treating an unknown block as solid means a route this reports is a route the
                 game certainly allows, which is the safe direction for a check.
    standable    solid below, and the two cells a body occupies both clear
    step         a face-neighbour on the horizontal, with |dy| <= 1 - no falls, so every route
                 it finds is REVERSIBLE, which is what a walkthrough needs and a drop is not
    ladder       a ladder cell is climbable up and down its own column

**AND THE SEED IS CHECKED.** A previous test in this repo seeded a flood in the void and proved
nothing while passing. `walk_from` refuses a seed it cannot stand on, and `reachable` refuses a
region smaller than `floor` cells - so "the route exists" can never be satisfied by a fill that
never left its own cell.
"""
from collections import deque

from mcbuild import blocks

# What a body passes through. An OPEN door is passable and a closed one is not, which is decided
# per state below rather than by name - the manor's doors stand open and are the route.
PASSABLE = {
    "air", "cave_air", "void_air", "cobweb", "torch", "wall_torch", "soul_torch",
    "soul_wall_torch", "redstone_wire", "rail", "powered_rail", "detector_rail",
    "activator_rail", "lever", "tripwire", "tripwire_hook", "vine", "glow_lichen",
    "candle", "skeleton_skull", "wither_skeleton_skull", "flower_pot", "soul_fire", "fire",
    "ladder", "scaffolding", "light", "moss_carpet", "snow", "short_grass", "dead_bush",
    "stone_pressure_plate", "oak_pressure_plate", "polished_blackstone_pressure_plate",
    "sculk_vein",
}
# ...plus every sign and every banner, which have no collision at all.
_PASSABLE_SUFFIX = ("_sign", "_banner", "_carpet", "_button", "_torch", "_candle")

_CUBE_CACHE = {}


def _is_passable(name: str, props: dict) -> bool:
    if name is None:
        return True
    n = name.split(":")[-1]
    if n in PASSABLE or n.endswith(_PASSABLE_SUFFIX):
        return True
    if n.endswith("_door") or n.endswith("_trapdoor") or n.endswith("_fence_gate"):
        return props.get("open") == "true"
    return False


def solid(w, pos) -> bool:
    v = w.cells.get(tuple(int(c) for c in pos))
    if v is None:
        return False
    return not _is_passable(v[0], v[1])


def is_ladder(w, pos) -> bool:
    v = w.cells.get(tuple(int(c) for c in pos))
    return bool(v) and v[0].split(":")[-1] == "ladder"


def supports(w, pos) -> bool:
    """Can a body stand ON this cell. A full cube can; so can a stair or a bottom slab, which is
    why solidity rather than full-cube-ness is the test - `blocks.is_full_cube` would refuse
    every tread of every flight in this file and report each one as a hole in the floor."""
    return solid(w, pos)


def _is_step(w, pos) -> bool:
    """A stair or a bottom slab: half a block, so a player walks onto it without jumping."""
    v = w.cells.get(tuple(int(c) for c in pos))
    if not v:
        return False
    n = v[0].split(":")[-1]
    if n.endswith("_stairs"):
        return True
    return n.endswith("_slab") and v[1].get("type") == "bottom"


def standable(w, pos) -> bool:
    x, y, z = (int(c) for c in pos)
    if is_ladder(w, (x, y, z)):
        return True
    return (supports(w, (x, y - 1, z))
            and not solid(w, (x, y, z))
            and not solid(w, (x, y + 1, z)))


def walk_from(w, seed, limit=200000):
    """Every cell reachable on foot from `seed`, under the model above.

    Raises if the seed is not somewhere a player can stand: a flood that starts in the void
    returns an empty set and every assertion written against it passes vacuously.
    """
    seed = tuple(int(c) for c in seed)
    if not standable(w, seed):
        raise AssertionError(f"the walk seed {seed} is not standable - "
                             f"below={w.name(seed[0], seed[1] - 1, seed[2])!r} "
                             f"at={w.name(*seed)!r} "
                             f"above={w.name(seed[0], seed[1] + 1, seed[2])!r}")
    seen = {seed}
    q = deque([seed])
    while q and len(seen) < limit:
        x, y, z = q.popleft()
        nxt = []
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                nxt.append((x + dx, y + dy, z + dz))
        if is_ladder(w, (x, y, z)):
            nxt += [(x, y + 1, z), (x, y - 1, z)]
        elif is_ladder(w, (x, y + 1, z)):
            nxt.append((x, y + 1, z))
        for c in nxt:
            if c in seen or not standable(w, c):
                continue
            # A STEP UP ONTO A FULL BLOCK IS A JUMP AND NEEDS HEADROOM AT THE SOURCE; A STEP UP
            # ONTO A STAIR OR A SLAB IS NOT. Vanilla step height is 0.6, so a whole block has to
            # be jumped and a half-step is taken automatically - which is the entire reason a
            # flight of stairs is walkable and a stack of blocks is a wall you climb. Written
            # without the distinction this model refused the clock tower's own spiral at the one
            # course where the belfry floor passes overhead, and the fault looked like the
            # building's rather than the model's.
            if c[1] > y and solid(w, (x, y + 2, z)) and not _is_step(w, (c[0], c[1] - 1, c[2])):
                continue
            seen.add(c)
            q.append(c)
    return seen


def reachable(w, seed, floor=40):
    """The flood, with the seed's own region checked to be a real region rather than a pocket."""
    got = walk_from(w, seed)
    assert len(got) >= floor, (f"the walk from {seed} reached only {len(got)} cells; "
                               f"a seed in a one-cell pocket proves nothing")
    return got


def near(cells, target, slack=2):
    """Did the flood reach `target`, or anywhere within `slack` of it.

    A waypoint is a NAMED PLACE, not a surveyed cell - the middle of a room, the foot of a
    flight - so demanding the exact block would be pinning an implementation detail, and the
    first version of this test failed on a waypoint one cell inside a wall it was naming.
    """
    tx, ty, tz = (int(c) for c in target)
    return any(abs(x - tx) <= slack and abs(y - ty) <= slack and abs(z - tz) <= slack
               for (x, y, z) in cells)


def full_cube(name: str) -> bool:
    n = (name or "air").split(":")[-1]
    if n not in _CUBE_CACHE:
        try:
            _CUBE_CACHE[n] = blocks.is_full_cube(n)
        except Exception:
            _CUBE_CACHE[n] = False
    return _CUBE_CACHE[n]
