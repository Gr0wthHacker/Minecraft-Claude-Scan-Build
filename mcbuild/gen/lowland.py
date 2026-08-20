"""The ground far below the island: a landform whose OUTLINE is read off the island itself.

    lowland: a multi-layered ground plane around Y40, following the island's own footprint, with a
             surface that rolls gently, a rim that thins and falls away, planting, vines off the
             underside and lanterns because nothing at this depth sees the sun.

Two things make this different from `voidisle`, which is the nearest neighbour:

* **The outline is not invented.** `voidisle` takes an ellipse and wobbles it. Here the footprint is
  the island's own column shadow, taken from the capture - the last block placed on each side IS the
  edge. Interior holes are filled (a pond is not a hole in the ground below it) and only the largest
  connected piece is kept, so a stray lightpost off the rim cannot grow a peninsula.

* **Flat has to survive.** This doubles as the place statues finally fit - the plate's best flat area
  is 13x13 and an elephant needs 15x29. So the relief is deliberately broad and shallow: large-scale
  noise moving the surface a block or two, never the per-column jitter that would look like ground
  but leave nowhere to stand. `_flat_pads` measures what actually came out and records it, so the
  question "does an elephant fit" is answered by measurement rather than by hope.

Thickness and height both taper toward the rim off a real distance-to-edge transform, not a radius:
the shape is irregular, so an ellipse would cut the taper through the middle of the lobes.
"""
from __future__ import annotations

from collections import deque

import numpy as np

from .canvas import Canvas, hash01
from .ground import prune_plants
from .vertical import Ctx, World, load_capture

LOWLAND = {
    "under": None,             # capture the outline is read from - required
    "top_y": 40,               # nominal surface; the height field moves around this
    "relief": 2,               # how far the surface rolls up and down
    "noise_scale": 11,         # BROAD - small values jitter and destroy every flat pad
    "rim_band": 10,            # over how many blocks the rim tapers
    "rim_drop": 3,             # how far the surface falls at the very edge
    "depth": 5,                # layers under the surface in the middle
    "rim_depth": 2,            # ... and at the rim, so it does not read as a cut slab
    "dome": 1.4,               # how much of the depth is a swell toward the middle vs a rim taper
    "under_wobble": 3,         # irregularity in the underside - without it the bottom is a plane
    "erode": 0,                # shrink the traced outline by N columns
    "ragged": 0.10,            # chance an edge column is bitten out, so it is land not a stencil
    # NO DIRT, in any form. On skyblock.net dirt, coarse dirt, rooted dirt, podzol and grass_block
    # are CURRENCY - see blocks.ECONOMY. Moss is the ground here, over a mossy-stone substrate that
    # dries into plain rock with depth, which is also a better read: the eye gets green at the top,
    # green-grey under it, then stone, instead of the brown band a dirt profile would have given.
    "soil": [("moss_block", 0.62), ("mossy_cobblestone", 0.22), ("mossy_stone_bricks", 0.16)],
    "sub": [("mossy_cobblestone", 0.44), ("cobblestone", 0.32), ("stone", 0.24)],
    # `dripstone_block` where andesite used to be. Andesite is another mid-grey in a body that was
    # already stone/cobblestone/tuff/deepslate - five greys, which is why the rock read as one flat
    # tone in the side view. Dripstone is warm (134,108,93) against all of them, it is natural cave
    # rock rather than something quarried, and it is cheap tier where andesite was ok.
    "rock": [("stone", 0.40), ("dripstone_block", 0.20), ("cobblestone", 0.16),
             ("tuff", 0.12), ("deepslate", 0.12)],
    "sub_depth": 2,            # dirt layers between the soil and the rock
    "carpet": 0.10, "grass": 0.16, "fern": 0.05, "azalea": 0.03, "flower": 0.02,
    "trees": 6,
    "vine_rate": 0.16, "vine_len": [3, 9],
    "lantern_step": 9,         # lantern grid pitch; nothing down here sees daylight
    "seed": 0,
}

SOIL = ("moss_block", "grass_block", "dirt", "coarse_dirt", "rooted_dirt", "podzol", "mud", "clay")
DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def build_lowland(cfg: dict, donors=None) -> Canvas:
    p = {**LOWLAND, **cfg}
    if not p.get("under"):
        raise ValueError("lowland needs params.under - the outline is read from a capture")
    seed, ty = int(p["seed"]), int(p["top_y"])

    foot, dist, bounds = _footprint(p, seed)
    surf = _surface(foot, dist, ty, p, seed)
    w = World()
    bottom = _body(w, surf, dist, p, seed)
    planted = _planting(w, surf, p, seed)
    trees = _trees(w, surf, dist, p, seed)
    vines = _vines(w, surf, foot, bottom, p, seed)
    lit = _lanterns(w, surf, p)
    ctx = Ctx(p["under"])
    prune_plants(w, ctx)

    pads = _flat_pads(surf)
    ys = [h for h in surf.values()]
    return w.canvas({"kind": "lowland", "top_y": ty,
                     "columns": len(surf), "bounds": bounds,
                     "surface_y": [min(ys), max(ys)],
                     "planted": planted, "trees": trees, "vines": vines, "lanterns": lit,
                     "flat_pads": pads,
                     "features_built": {"columns": len(surf), "trees": trees,
                                        "vines": vines, "lanterns": lit}})


# ------------------------------------------------------------------ the outline

def _footprint(p, seed):
    """The island's own column shadow, cleaned up into one solid piece of ground.

    Vines are excluded before projecting: eight strands dangle from the plate all the way to bedrock,
    and tracing them would hang thin spurs of ground off the edge that nothing above justifies.
    """
    m, (ox, oy, oz) = load_capture(p["under"])
    names = np.array([n.split(":")[-1] for n in m.names])
    skip = np.isin(names, ["air", "cave_air", "void_air", "vine"])
    mask = (~skip[m.ids]).any(axis=0)                      # (z, x)

    mask = _fill_holes(mask)                               # a pond is not a hole in the ground below
    mask = _largest_piece(mask)
    for _ in range(int(p["erode"])):
        mask = _erode(mask)

    # Bite the rim, THEN heal. Taking a column out of a one-wide spur strands whatever was beyond it,
    # and a stranded column is a gate failure ("one connected piece"), not a cosmetic flaw - the first
    # build lost a 7-cell and a 6-cell crumb this way.
    rag = float(p["ragged"])
    if rag > 0:
        rim = _edge_distance(mask)
        for z, x in np.argwhere(mask):
            if rim[z, x] <= 1 and hash01(ox + int(x), oz + int(z), 13, seed) < rag:
                mask[z, x] = False
        mask = _largest_piece(mask)

    # ... and measure the distance transform on the FINAL shape. Computing it before the bite made
    # the thickness taper follow an edge that no longer existed.
    dist = _edge_distance(mask)
    foot = {(ox + int(x), oz + int(z)) for z, x in np.argwhere(mask)}
    d = {(ox + int(x), oz + int(z)): int(dist[z, x]) for z, x in np.argwhere(mask)}
    xs = [c[0] for c in foot]
    zs = [c[1] for c in foot]
    return foot, d, [min(xs), min(zs), max(xs), max(zs)]


def _fill_holes(mask):
    """Anything not reachable from outside is interior - fill it."""
    H, W = mask.shape
    seen = np.zeros_like(mask, bool)
    dq = deque()
    for z in range(H):
        for x in (0, W - 1):
            if not mask[z, x] and not seen[z, x]:
                seen[z, x] = True
                dq.append((z, x))
    for x in range(W):
        for z in (0, H - 1):
            if not mask[z, x] and not seen[z, x]:
                seen[z, x] = True
                dq.append((z, x))
    while dq:
        z, x = dq.popleft()
        for dz, dx in DIRS4:
            nz, nx = z + dz, x + dx
            if 0 <= nz < H and 0 <= nx < W and not mask[nz, nx] and not seen[nz, nx]:
                seen[nz, nx] = True
                dq.append((nz, nx))
    return mask | (~mask & ~seen)


def _largest_piece(mask):
    H, W = mask.shape
    best, seen = None, np.zeros_like(mask, bool)
    for z in range(H):
        for x in range(W):
            if not mask[z, x] or seen[z, x]:
                continue
            comp, dq = [], deque([(z, x)])
            seen[z, x] = True
            while dq:
                a, b = dq.popleft()
                comp.append((a, b))
                for dz, dx in DIRS4:
                    na, nb = a + dz, b + dx
                    if 0 <= na < H and 0 <= nb < W and mask[na, nb] and not seen[na, nb]:
                        seen[na, nb] = True
                        dq.append((na, nb))
            if best is None or len(comp) > len(best):
                best = comp
    out = np.zeros_like(mask, bool)
    for a, b in best or []:
        out[a, b] = True
    return out


def _erode(mask):
    H, W = mask.shape
    out = mask.copy()
    for z, x in np.argwhere(mask):
        for dz, dx in DIRS4:
            nz, nx = z + dz, x + dx
            if not (0 <= nz < H and 0 <= nx < W) or not mask[nz, nx]:
                out[z, x] = False
                break
    return out


def _edge_distance(mask):
    """Multi-source BFS inward from the boundary. The shape is irregular, so a radius would put the
    taper through the middle of a lobe instead of round the edge of one."""
    H, W = mask.shape
    dist = np.zeros(mask.shape, int)
    dq = deque()
    for z, x in np.argwhere(mask):
        for dz, dx in DIRS4:
            nz, nx = z + dz, x + dx
            if not (0 <= nz < H and 0 <= nx < W) or not mask[nz, nx]:
                dist[z, x] = 1
                dq.append((z, x))
                break
    while dq:
        z, x = dq.popleft()
        for dz, dx in DIRS4:
            nz, nx = z + dz, x + dx
            if 0 <= nz < H and 0 <= nx < W and mask[nz, nx] and dist[nz, nx] == 0:
                dist[nz, nx] = dist[z, x] + 1
                dq.append((nz, nx))
    return dist


# ------------------------------------------------------------------ the land

def _noise(x, z, seed, scale):
    """Smooth value noise over a COARSE lattice, averaged with its neighbours - the surface has to
    roll over tens of blocks, not wobble every column."""
    gx, gz = x // scale, z // scale
    tot = 0.0
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            tot += hash01(gx + dx, gz + dz, 7, seed)
    return tot / 9.0


def _surface(foot, dist, ty, p, seed) -> dict:
    relief, band, drop = int(p["relief"]), int(p["rim_band"]), int(p["rim_drop"])
    scale = int(p["noise_scale"])
    out = {}
    for (x, z) in foot:
        h = ty + int(round(relief * (_noise(x, z, seed, scale) - 0.5) * 2))
        d = dist.get((x, z), band)
        if d < band:                                   # the ground falls away toward the rim
            h -= int(round(drop * (1.0 - d / band)))
        out[(x, z)] = h
    return out


def _body(w: World, surf: dict, dist: dict, p, seed) -> dict:
    """Soil, then dirt, then rock - thinning toward the rim so the edge is a slope, not a cut.

    The thickness is TWO terms, because one is not enough. A pure rim taper reaches full depth a few
    blocks in and then stops, which builds a plate with bevelled edges - from the side the underside
    is a dead flat plane a hundred blocks long. So the rim term is blended with a swell that keeps
    deepening all the way to the middle, and the whole thing is roughened by its own noise field.
    Ground has a keel; a slab does not.
    """
    depth, rim, band = int(p["depth"]), int(p["rim_depth"]), int(p["rim_band"])
    subn, scale = int(p["sub_depth"]), int(p["noise_scale"])
    dome, wob = float(p["dome"]), int(p["under_wobble"])
    dmax = max(dist.values()) if dist else band
    bottom = {}
    for (x, z), h in surf.items():
        d = dist.get((x, z), band)
        near = min(1.0, d / max(1, band))                  # the rim taper
        deep = (d / max(1, dmax)) ** dome                   # ... and the swell toward the middle
        thick = rim + int(round((depth - rim) * (0.55 * near + 0.45 * deep)))
        if wob:                                             # own noise field, so the underside does
            thick += int(round(wob * (_noise(x + 977, z - 431, seed + 5,  # not mirror the surface
                                             max(2, scale * 2)) - 0.5) * 2))
        thick = max(rim, thick)
        w.put(x, h, z, _pick(p["soil"], x, h, z, seed))
        for k in range(1, thick + 1):
            y = h - k
            table = p["sub"] if k <= subn else p["rock"]
            w.put(x, y, z, _pick(table, x, y, z, seed))
        bottom[(x, z)] = h - thick
    return bottom


def _planting(w: World, surf: dict, p, seed) -> int:
    """Ground cover. Kept sparse on purpose - this is a floor things get built on as well as land."""
    n = 0
    a, f, g, c = p["azalea"], p["fern"], p["grass"], p["carpet"]
    for (x, z), h in surf.items():
        if w.has(x, h + 1, z):
            continue
        r = hash01(x, z, 31, seed)
        ground = w.name(x, h, z) or "air"
        if ground not in SOIL:
            if r < c:
                w.put(x, h + 1, z, "moss_carpet")
                n += 1
            continue
        if r < a:
            w.put(x, h + 1, z, "flowering_azalea" if r < a * 0.4 else "azalea")
        elif r < a + f:
            w.put(x, h + 1, z, "fern")
        elif r < a + f + g:
            w.put(x, h + 1, z, "short_grass")
        elif r < a + f + g + c:
            w.put(x, h + 1, z, "moss_carpet")
        elif r < a + f + g + c + p["flower"]:
            w.put(x, h + 1, z, "poppy" if r < a + f + g + c + p["flower"] * 0.5 else "dandelion")
        else:
            continue
        n += 1
    return n


def _trees(w: World, surf: dict, dist: dict, p, seed) -> int:
    """Small oak clumps, kept well inside the rim and well apart - they mark scale without filling
    the flat ground the statues need."""
    want = int(p["trees"])
    if want <= 0:
        return 0
    inner = sorted(c for c in surf if dist.get(c, 0) >= int(p["rim_band"]))
    placed, spots = 0, []
    for c in inner:
        if placed >= want:
            break
        if hash01(c[0], c[1], 37, seed) > 0.10:
            continue
        if any(abs(c[0] - a) + abs(c[1] - b) < 22 for a, b in spots):
            continue
        x, z = c
        h = surf[c]
        trunk = 4 + int(hash01(x, z, 41, seed) * 3)
        for k in range(1, trunk + 1):
            w.put(x, h + k, z, "oak_log", axis="y")
        top = h + trunk
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                for dy in (0, 1):
                    if abs(dx) + abs(dz) + dy * 2 > 3 or (dx == 0 and dz == 0 and dy == 0):
                        continue
                    w.put(x + dx, top + dy, z + dz, "oak_leaves",
                          distance="1", persistent="true", waterlogged="false")
        spots.append(c)
        placed += 1
    return placed


def _vines(w: World, surf: dict, foot: set, bottom: dict, p, seed) -> int:
    """Strands off the underside rim so the ground hangs rather than floats.

    Anchored to the real bottom of each column, which the body pass recorded - the taper means the
    underside is not at a computed depth.
    """
    lo, hi = p["vine_len"]
    n = 0
    for c in surf:
        if all((c[0] + dx, c[1] + dz) in foot for dx, dz in DIRS4):
            continue
        for dx, dz, facing in ((1, 0, "west"), (-1, 0, "east"), (0, 1, "north"), (0, -1, "south")):
            if (c[0] + dx, c[1] + dz) in foot:
                continue
            if hash01(c[0], c[1], 43, seed) >= p["vine_rate"]:
                continue
            y = bottom.get(c, surf[c])
            L = lo + int(hash01(c[0], c[1], 47, seed) * (hi - lo + 1))
            props = {"east": "false", "north": "false", "south": "false",
                     "west": "false", "up": "false", facing: "true"}
            for k in range(L):
                if w.has(c[0] + dx, y - k, c[1] + dz):
                    break
                w.put(c[0] + dx, y - k, c[1] + dz, "vine", **props)
                n += 1
            break
    return n


def _lanterns(w: World, surf: dict, p) -> int:
    """A jittered grid. Nothing at Y40 sees the sun, and greedy set cover over five thousand columns
    is minutes of work for a result a grid gives instantly."""
    step = int(p["lantern_step"])
    if step <= 0:
        return 0
    lit = 0
    for (x, z), h in surf.items():
        if x % step or z % step:
            continue
        w.cells.pop((x, h + 1, z), None)
        w.put(x, h + 1, z, "lantern", hanging="false", waterlogged="false")
        lit += 1
    return lit


# ------------------------------------------------------------------ what fits on it

def _flat_pads(surf: dict, want: int = 4):
    """Largest level rectangles, per surface height.

    The whole point of building this is that nothing fit upstairs, so the answer has to be measured:
    an elephant needs 15x29 and the plate's best was 13x13.
    """
    if not surf:
        return []
    xs = [c[0] for c in surf]
    zs = [c[1] for c in surf]
    x0, z0 = min(xs), min(zs)
    W, H = max(xs) - x0 + 1, max(zs) - z0 + 1
    out = []
    for h in sorted(set(surf.values())):
        grid = np.zeros((H, W), bool)
        for (x, z), v in surf.items():
            if v == h:
                grid[z - z0, x - x0] = True
        best = _max_rect(grid)
        if best:
            ax, az, rows, cols = best
            out.append({"y": h, "size": [cols, rows], "at": [x0 + ax, z0 + az]})
    out.sort(key=lambda d: -(d["size"][0] * d["size"][1]))
    return out[:want]


def _max_rect(grid):
    """Largest all-true axis-aligned rectangle, by the standard histogram scan."""
    H, W = grid.shape
    heights = np.zeros(W, int)
    best = None
    for z in range(H):
        heights = np.where(grid[z], heights + 1, 0)
        stack = []
        for x in range(W + 1):
            cur = int(heights[x]) if x < W else 0
            start = x
            while stack and stack[-1][1] >= cur:
                s, hh = stack.pop()
                area = hh * (x - s)
                if hh > 0 and (best is None or area > best[0]):
                    best = (area, s, z - hh + 1, hh, x - s)
                start = s
            stack.append((start, cur))
    if not best or best[0] <= 0:
        return None
    _, sx, sz, rows, cols = best
    return sx, sz, rows, cols


def _pick(table, x, y, z, seed) -> str:
    """Weighted choice, deterministic in world coordinates so a rebuild is identical."""
    h = hash01(x, y, z, 53, seed)
    acc = 0.0
    for name, weight in table:
        acc += weight
        if h < acc:
            return name
    return table[-1][0]
