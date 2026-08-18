"""Interior shell fitted to a capture: the vaulted hall under the island plate.

    vault:  reads the working deck (a flat slab hanging under the plate) as one room - a railing on
            the open rim, a colonnade on a fixed bay grid, a coffered lattice under the plate and
            lanterns hung from it. Everything already standing (chests, hoppers, redstone, spawners)
            is dilated by `clearance` and never touched; `keep_boxes` carries the constraints geometry
            cannot see - spawner spawn volumes, an AFK sightline, a hopper chute's air gap.

The grid is anchored to a world coordinate rather than to the slab's bounding box, so regenerating
against a newer capture can never shift a pillar (see rule 1 in CLAUDE.md).
"""
from __future__ import annotations

import numpy as np

from .belly import dilate
from .canvas import Canvas, hash01
from .vertical import Ctx, World

VAULT = {
    "under": None,               # capture that supplies the slab geometry - pin it once building starts
    "floor_y": 194,              # the deck slab
    "ceil_y": 201,               # underside of the island plate
    "box": None,                 # [x1, z1, x2, z2] window to look for the slab in
    "bay": 6,                    # pillar grid spacing
    "anchor": None,              # world (x, z) the grid passes through; defaults to the slab centre
    "clearance": 1,              # cells kept clear around anything already standing
    "keep_boxes": [],            # world [x1, y1, z1, x2, y2, z2]: never build here
    "rail": True,                # wall railing where the rim drops away
    "coffer": True,              # beam lattice under the plate
    "lantern_bay": 2,            # hang a lantern every Nth bay along the beams
    "capitals": True,            # stair corbels where a pillar meets its beams
    "pillar": "stone_bricks",
    "beam": "mossy_stone_bricks",
    "rail_block": "stone_brick_wall",
    "stair": "stone_brick_stairs",
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air", "vine")
DIRS = (("east", 1, 0), ("west", -1, 0), ("south", 0, 1), ("north", 0, -1))


def build_vault(cfg: dict, donors=None) -> Canvas:
    p = {**VAULT, **cfg}
    ctx = Ctx(p["under"])
    fy, cy, bay = int(p["floor_y"]), int(p["ceil_y"]), int(p["bay"])
    seed = int(p["seed"])

    slab = _slab(ctx, fy, p["box"])
    # keep-outs bite per course, not over the whole height: a box that guards redstone at head height
    # must still let the coffer cross above it.
    keep = {y: _keep_at(ctx, p["keep_boxes"], y, slab.shape) for y in range(fy + 1, cy)}
    lvl = {y: _free_at(ctx, slab, y) & ~keep[y] for y in range(fy + 1, cy)}
    column = np.logical_and.reduce([lvl[y] for y in sorted(lvl)])  # clear floor to plate: only pillars need this
    build = column & ~dilate(~column & slab, int(p["clearance"]))

    w, dig = World(), []
    ax, az = _anchor(ctx, slab, p["anchor"], bay)
    pillars = _pillars(ctx, w, dig, build, slab, fy, cy, ax, az, bay, p)
    beams = _beams(ctx, w, dig, slab, lvl[cy - 1], cy, ax, az, bay, p, seed) if p["coffer"] else []
    if p["capitals"]:
        _capitals(ctx, w, pillars, beams, cy, p)
    lanterns = _lanterns(ctx, w, beams, lvl[cy - 2], cy, ax, az, bay, int(p["lantern_bay"]), p)
    rails = _railing(ctx, w, dig, slab, lvl[fy + 1], fy, cy, p) if p["rail"] else 0
    _settle_walls(w, ctx, p["rail_block"])

    return w.canvas({
        "kind": "vault", "bay": bay, "anchor": [ax, az], "floor_y": fy, "ceil_y": cy,
        "pillars": len(pillars), "beam_cells": len(beams), "lanterns": lanterns, "rail_cells": rails,
        "dig": [list(d) for d in dig],
        # NOT `exclude_boxes`: the pipeline reads that key as "erase whatever is here before auditing",
        # which is the opposite of what these boxes mean. They are recorded for reference only.
        "keep_boxes": [list(map(int, b)) for b in p["keep_boxes"]],
    })


# ------------------------------------------------------------------ masks

def _slab(ctx: Ctx, fy: int, box) -> np.ndarray:
    """Largest connected run of floor at `fy` inside `box` - the deck, not the rock around it."""
    ly = fy - ctx.oy
    solid = ctx.solid[ly].copy()
    if box:
        x1, z1, x2, z2 = box
        win = np.zeros_like(solid)
        win[max(0, min(z1, z2) - ctx.oz):max(z1, z2) - ctx.oz + 1,
            max(0, min(x1, x2) - ctx.ox):max(x1, x2) - ctx.ox + 1] = True
        solid &= win
    return _largest_component(solid)


def _largest_component(mask: np.ndarray) -> np.ndarray:
    seen = np.zeros_like(mask)
    best: list[tuple[int, int]] = []
    for z0, x0 in np.argwhere(mask):
        if seen[z0, x0]:
            continue
        stack, cells = [(z0, x0)], []
        seen[z0, x0] = True
        while stack:
            z, x = stack.pop()
            cells.append((z, x))
            for dz, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nz, nx = z + dz, x + dx
                if 0 <= nz < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[nz, nx] and not seen[nz, nx]:
                    seen[nz, nx] = True
                    stack.append((nz, nx))
        if len(cells) > len(best):
            best = cells
    out = np.zeros_like(mask)
    for z, x in best:
        out[z, x] = True
    return out


def _free_at(ctx: Ctx, slab: np.ndarray, y: int) -> np.ndarray:
    """Slab cells that are open at exactly this course (vines do not count as occupied)."""
    out = slab.copy()
    for z, x in np.argwhere(slab):
        if ctx.name_at(x + ctx.ox, y, z + ctx.oz) not in AIRY:
            out[z, x] = False
    return out


def _keep_at(ctx: Ctx, boxes, y: int, shape) -> np.ndarray:
    """Config boxes flattened to (x, z), but only those that actually span this course."""
    out = np.zeros(shape, bool)
    for x1, y1, z1, x2, y2, z2 in boxes:
        if not (min(y1, y2) <= y <= max(y1, y2)):
            continue
        out[max(0, min(z1, z2) - ctx.oz):max(z1, z2) - ctx.oz + 1,
            max(0, min(x1, x2) - ctx.ox):max(x1, x2) - ctx.ox + 1] = True
    return out


def _anchor(ctx: Ctx, slab: np.ndarray, anchor, bay: int) -> tuple[int, int]:
    if anchor:
        return int(anchor[0]), int(anchor[1])
    zs, xs = np.where(slab)
    return int(round(xs.mean())) + ctx.ox, int(round(zs.mean())) + ctx.oz


def _on_grid(v: int, a: int, bay: int) -> bool:
    return (v - a) % bay == 0


# ------------------------------------------------------------------ pieces

def _pillars(ctx, w, dig, build, slab, fy, cy, ax, az, bay, p) -> list[tuple[int, int]]:
    """A column at every grid point that is buildable and sits a full cell in off the rim."""
    out = []
    for z, x in np.argwhere(build):
        X, Z = x + ctx.ox, z + ctx.oz
        if not (_on_grid(X, ax, bay) and _on_grid(Z, az, bay)):
            continue
        if not all(_at(slab, z + dz, x + dx) for _, dx, dz in DIRS):
            continue
        for y in range(fy + 1, cy - 1):                       # body stops one below the beam course
            _place(w, dig, ctx, X, y, Z, p["pillar"])
        out.append((X, Z))
    return out


def _beams(ctx, w, dig, slab, ok, cy, ax, az, bay, p, seed) -> list[tuple[int, int]]:
    """Lattice one course under the plate, running the full grid across the room.

    The coffer is the piece that makes the slab read as a single hall, so it crosses over the
    machines too - six blocks up it is clear of all of them. It only wants the plate directly
    above to hang from."""
    by, cells = cy - 1, []
    for z, x in np.argwhere(slab & ok):
        X, Z = x + ctx.ox, z + ctx.oz
        if not (_on_grid(X, ax, bay) or _on_grid(Z, az, bay)):
            continue
        if ctx.name_at(X, cy, Z) in AIRY:                     # no plate to hang the beam from
            continue
        name = p["beam"] if hash01(X, Z, 17, seed) < 0.7 else p["pillar"]
        if _place(w, dig, ctx, X, by, Z, name):
            cells.append((X, Z))
    return cells


def _capitals(ctx, w, pillars, beams, cy, p):
    """Top-half stair corbels springing from each pillar toward the beams it carries."""
    bset, py = set(beams), cy - 2
    for (X, Z) in pillars:
        for facing, dx, dz in DIRS:
            nx, nz = X + dx, Z + dz
            if (nx, nz) not in bset or w.has(nx, py, nz) or ctx.name_at(nx, py, nz) not in AIRY:
                continue
            w.put(nx, py, nz, p["stair"], facing=facing, half="top", shape="straight", waterlogged="false")


def _lanterns(ctx, w, beams, ok, cy, ax, az, bay, every, p) -> int:
    """Hang a lantern under the lattice on a coarser grid than the bays: 12 blocks apart puts the
    darkest floor cell well clear of light 0, so nothing spawns in the hall."""
    if every <= 0:
        return 0
    step, n, ly = bay * every, 0, cy - 2
    for (bx, bz) in beams:
        # spaced along the runs, not only where two runs cross - crossings alone leave dark corners
        if not ((_on_grid(bx, ax, bay) and _on_grid(bz, az, step)) or
                (_on_grid(bz, az, bay) and _on_grid(bx, ax, step))):
            continue
        if w.has(bx, ly, bz) or not _at(ok, bz - ctx.oz, bx - ctx.ox):
            continue
        w.put(bx, ly, bz, "lantern", hanging="true", waterlogged="false")
        n += 1
    return n


def _railing(ctx, w, dig, slab, ok, fy, cy, p) -> int:
    """Wall course on the rim cells where the deck drops straight into open air."""
    n = 0
    for z, x in np.argwhere(slab & ok):
        X, Z = x + ctx.ox, z + ctx.oz
        for _, dx, dz in DIRS:
            if _at(slab, z + dz, x + dx):
                continue
            if any(ctx.name_at(X + dx, y, Z + dz) not in AIRY for y in range(fy, cy)):
                continue                                       # rock or a build backs it: not a drop
            if _place(w, dig, ctx, X, fy + 1, Z, p["rail_block"], up="true",
                      north="none", south="none", east="none", west="none", waterlogged="false"):
                n += 1
            break
    return n


def _settle_walls(w: World, ctx: Ctx, rail_block: str):
    """Give each placed wall the state the game will give it, so the Litematica overlay stays clean."""
    walls = [(x, y, z) for (x, y, z), (name, _) in w.cells.items() if name == rail_block]
    for (x, y, z) in walls:
        sides = {}
        for facing, dx, dz in DIRS:
            n = w.name(x + dx, y, z + dz) or ctx.name_at(x + dx, y, z + dz)
            sides[facing] = "low" if (n == rail_block or n not in AIRY) else "none"
        joined = [d for d in sides if sides[d] != "none"]
        straight = len(joined) == 2 and {"east", "west"} != set(joined) != {"north", "south"}
        above = w.has(x, y + 1, z) or ctx.name_at(x, y + 1, z) not in AIRY
        up = above or not (len(joined) == 2 and not straight)
        w.put(x, y, z, rail_block, up="true" if up else "false", waterlogged="false", **sides)


# ------------------------------------------------------------------ helpers

def _at(mask: np.ndarray, z: int, x: int) -> bool:
    return bool(mask[z, x]) if 0 <= z < mask.shape[0] and 0 <= x < mask.shape[1] else False


def _place(w: World, dig: list, ctx: Ctx, x, y, z, name, **props) -> bool:
    """Put a block, recording any vine that has to come down first."""
    if w.has(x, y, z):
        return False
    here = ctx.name_at(x, y, z)
    if here not in AIRY:
        return False
    if here == "vine":
        dig.append((int(x), int(y), int(z)))
    w.put(x, y, z, name, **props)
    return True
