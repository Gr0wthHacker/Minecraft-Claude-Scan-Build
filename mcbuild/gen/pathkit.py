"""Path kit — meandering slab/moss paths with lamp posts and edge dressing.

Sits ON the paste surface (grass/moss); nothing below y0. Routes are bezier
curves in canvas x/z; each is a ragged 2-3 wide band of cobble / mossy /
stone-brick slabs and moss carpet with occasional gaps so grass shows.
Lamp posts alternate sides every `post_spacing` blocks (fence x3, slab cap,
slab arm over the path, hanging lantern). Cells just outside the path get
azalea, ferns, flowers, carpet and the odd mossy boulder.

Cut whatever part you need in Litematica; rotate as required.
"""
from __future__ import annotations

import math

import numpy as np

from .canvas import Canvas, hash01

DEFAULTS = {
    "size": 41,
    "routes": [
        [[20, 40], [13, 33], [27, 26], [15, 17], [24, 9], [12, 2]],   # main: dock -> centre -> top-left, sinuous
        [[22, 22], [29, 22], [33, 14], [40, 12]],                      # branch right
        [[19, 19], [12, 24], [8, 20], [1, 27]],                        # branch left
    ],
    "half_width": 1.25,      # centre-line distance covered (2-3 wide with jitter)
    "gap_p": 0.08,           # chance a path cell is left as grass (ragged look)
    "post_spacing": 7,
    "dressing": True,
    "seed": 0,
}


def _states(c: Canvas) -> dict:
    st, raw = c.state, c.raw_state
    return {
        "cobble_slab": st("cobblestone_slab", type="bottom", waterlogged="false"),
        "mosscobble_slab": raw("mossy_cobblestone_slab", type="bottom", waterlogged="false"),
        "brick_slab": raw("stone_brick_slab", type="bottom", waterlogged="false"),
        "carpet": st("moss_carpet"), "mosscobble": st("mossy_cobblestone"),
        "fence": st("oak_fence", north="false", south="false", east="false", west="false", waterlogged="false"),
        "oslab": st("oak_slab", type="bottom", waterlogged="false"),
        "lant_h": st("lantern", hanging="true", waterlogged="false"),
        "azalea": st("azalea"), "fazalea": st("flowering_azalea"),
        "fern": raw("fern"), "grass": raw("short_grass"),
        "flowers": [raw("dandelion"), raw("poppy"), st("oxeye_daisy"), raw("cornflower"), st("allium"), raw("azure_bluet")],
    }


def _bezier(pts, n):
    pts = [np.array(p, float) for p in pts]
    out = []
    for t in np.linspace(0, 1, n):
        layer = pts
        while len(layer) > 1:
            layer = [(1 - t) * u + t * v for u, v in zip(layer, layer[1:])]
        out.append(layer[0])
    return out


def build(cfg: dict, donors=None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    N = int(p["size"]); seed = int(p["seed"]); hw = float(p["half_width"])
    c = Canvas(N, 6, N, donors); S = _states(c)
    h = lambda *a: hash01(*a, seed)
    path = np.zeros((N, N), bool)                     # [z, x]
    posts: list[tuple[int, int, float, float]] = []   # x, z, nx, nz  (normal pointing away from the path)
    for ri, route in enumerate(p["routes"]):
        pts = _bezier(route, 400)
        # arc-length walk for post placement
        acc, last = 0.0, None
        side = 1 if ri % 2 == 0 else -1
        for i, q in enumerate(pts):
            x, z = q
            r = hw + 0.5 * (h(int(x * 2), int(z * 2), ri) - 0.5)
            for zz in range(int(z - 2), int(z + 3)):
                for xx in range(int(x - 2), int(x + 3)):
                    if 0 <= xx < N and 0 <= zz < N and math.hypot(xx + 0.5 - x, zz + 0.5 - z) <= r:
                        path[zz, xx] = True
            if last is not None:
                acc += float(np.linalg.norm(q - last))
                if acc >= p["post_spacing"] and 4 < i < len(pts) - 4:
                    d = pts[i + 3] - pts[i - 3]; d /= (np.linalg.norm(d) + 1e-9)
                    nx, nz = -d[1] * side, d[0] * side
                    px, pz = int(x + nx * (hw + 1.6)), int(z + nz * (hw + 1.6))
                    posts.append((px, pz, nx, nz))
                    acc = 0.0; side = -side
            last = q
    # lay the path
    for z in range(N):
        for x in range(N):
            if not path[z, x]:
                continue
            k = h(x, z, 3)
            if k < p["gap_p"]:
                continue
            k = h(x, z, 5)
            c.put(x, 0, z, S["cobble_slab"] if k < 0.38 else S["mosscobble_slab"] if k < 0.68
                  else S["brick_slab"] if k < 0.84 else S["carpet"])
    # lamp posts
    for px, pz, nx, nz in posts:
        if not (0 <= px < N and 0 <= pz < N) or path[pz, px]:
            continue
        ax, az = (-1 if nx < 0 else 1, 0) if abs(nx) >= abs(nz) else (0, -1 if nz < 0 else 1)
        ax, az = -ax, -az                                # arm points back toward the path
        for y in range(0, 3):
            c.put(px, y, pz, S["fence"])
        c.put(px, 3, pz, S["oslab"]); c.put(px + ax, 3, pz + az, S["oslab"])
        c.put(px + ax, 2, pz + az, S["lant_h"])
    # edge dressing
    if p["dressing"]:
        for z in range(N):
            for x in range(N):
                if path[z, x] or c.get(x, 0, z) != 0:
                    continue
                near = any(0 <= x + dx < N and 0 <= z + dz < N and path[z + dz, x + dx]
                           for dx in (-1, 0, 1) for dz in (-1, 0, 1))
                if not near:
                    continue
                k = h(x, z, 7); j = h(x, z, 9)
                if k < 0.16:
                    c.put(x, 0, z, S["flowers"][int(j * 6) % 6])
                elif k < 0.26:
                    c.put(x, 0, z, S["fern"] if j < 0.5 else S["grass"])
                elif k < 0.33:
                    c.put(x, 0, z, S["azalea"] if j < 0.6 else S["fazalea"])
                elif k < 0.40:
                    c.put(x, 0, z, S["carpet"])
                elif k < 0.43:
                    c.put(x, 0, z, S["mosscobble"])
                    if j < 0.5:
                        c.put(x, 1, z, S["mosscobble_slab"])
    return c
