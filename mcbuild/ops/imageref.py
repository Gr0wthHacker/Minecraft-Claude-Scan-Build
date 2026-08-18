"""Image reference -> schematic.

What a single image gives you: a SILHOUETTE and COLOURS. It does not give
you depth. So this builds a correctly-proportioned, correctly-coloured,
cheap-material statue *starting point*, not a finished 3-D model:

  1. mask   : alpha channel, or background-key (corner colour) with tolerance
  2. scale  : nearest-neighbour to target height (width follows aspect)
  3. depth  : extrude the mask `depth` blocks; with profile="loft" the
              depth tapers toward the silhouette edge (rounded, not a slab)
  4. colour : each pixel -> nearest block by RGB from an allowed set
              (default: cheap tier only). Optional per-pixel dither off.
  5. shell  : optional hollow, mirror, ground floor

Then use `polish` to fix the face and `audit` before shipping. For a real
3-D read you need a second orthogonal image (side view) -- `from_images`
intersects two silhouettes, which is what most voxel-from-photo tools do.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .. import morph, nbt, palette
from ..schem import Model

_ALLOWED_DEFAULT_EXCLUDE = {"air", "water", "lava", "glass", "glass_pane", "vine", "chain",
                            "lantern", "soul_lantern", "torch", "wall_torch", "ladder", "iron_bars",
                            "cave_vines", "cave_vines_plant", "hanging_roots", "pointed_dripstone",
                            "moss_carpet", "short_grass", "tall_grass", "fern", "azalea",
                            "flowering_azalea", "pink_petals", "oxeye_daisy", "white_tulip",
                            "azure_bluet", "blue_orchid", "allium", "lily_of_the_valley",
                            "campfire", "chest", "barrel", "flower_pot", "tnt", "stone_button",
                            "stone_pressure_plate", "big_dripleaf"}
_ALLOWED_DEFAULT_EXCLUDE |= {n for n in palette.COLORS if n.endswith(("_slab", "_stairs", "_fence",
                                                                        "_trapdoor", "_door", "_leaves",
                                                                        "_stained_glass"))}


def allowed_blocks(tiers=("cheap",), extra_exclude=frozenset(), include=frozenset()) -> list[str]:
    out = []
    for n in palette.COLORS:
        if n in include:
            out.append(n)
            continue
        if n in _ALLOWED_DEFAULT_EXCLUDE or n in extra_exclude:
            continue
        if palette.tier(n) in tiers:
            out.append(n)
    return sorted(set(out))


def _mask_and_rgb(img: Image.Image, bg_tolerance: int = 40):
    img = img.convert("RGBA")
    a = np.array(img)
    rgb = a[..., :3].astype(np.int32)
    alpha = a[..., 3]
    if alpha.min() < 250:                       # real alpha
        return alpha > 127, rgb
    # background key from the four corners
    corners = np.array([rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]])
    bg = np.median(corners, axis=0)
    dist = np.abs(rgb - bg).sum(axis=-1)
    return dist > bg_tolerance, rgb


def _quantize(rgb: np.ndarray, block_names: list[str]) -> np.ndarray:
    """Return index into block_names for each pixel (nearest RGB, weighted)."""
    cols = np.array([palette.color_of(n) for n in block_names], np.float32)
    px = rgb.reshape(-1, 3).astype(np.float32)
    # perceptual-ish weighting
    w = np.array([0.30, 0.59, 0.11], np.float32) * 3
    d = ((px[:, None, :] - cols[None, :, :]) ** 2 * w).sum(axis=-1)
    return d.argmin(axis=1).reshape(rgb.shape[:2])


def from_image(path: str, *, height: int, depth: int = 8, profile: str = "loft",
               tiers=("cheap",), include: set[str] = frozenset(),
               exclude: set[str] = frozenset(), bg_tolerance: int = 40,
               mirror: bool = False, hollow_shell: int | None = None,
               floor: bool = True, palette_size: int | None = None) -> Model:
    img = Image.open(path)
    mask, rgb = _mask_and_rgb(img, bg_tolerance)
    ys, xs = np.where(mask)
    if ys.size == 0:
        raise ValueError("no foreground found in image (try --bg-tolerance)")
    mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    rgb = rgb[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h0, w0 = mask.shape
    W = max(1, int(round(w0 * height / h0)))
    mimg = Image.fromarray((mask * 255).astype(np.uint8)).resize((W, height), Image.BOX)
    cimg = Image.fromarray(rgb.astype(np.uint8)).resize((W, height), Image.BOX)
    m2 = np.array(mimg) > 100
    c2 = np.array(cimg).astype(np.int32)
    if mirror:
        m2 = m2 | m2[:, ::-1]

    names = allowed_blocks(tiers, exclude, include)
    if palette_size:
        # keep the most-used blocks only, re-quantise to that subset
        q = _quantize(c2, names)
        used, cnt = np.unique(q[m2], return_counts=True)
        top = [names[i] for i in used[np.argsort(-cnt)][:palette_size]]
        names = top
    q = _quantize(c2, names)

    # depth profile: distance-to-edge based loft
    if profile == "loft" and depth > 2:
        dist = _edt2d(m2)
        dmax = max(1.0, float(dist.max()))
        thick = np.clip(np.round(depth * np.sqrt(np.clip(dist / dmax, 0, 1))), 1, depth).astype(int)
    else:
        thick = np.where(m2, depth, 0)

    SY, SX, SZ = height, W, depth
    ids = np.zeros((SY, SZ, SX), np.int32)
    pal: list = [nbt.block_state("minecraft:air")]
    index: dict[str, int] = {"minecraft:air": 0}

    def get(n: str) -> int:
        n = "minecraft:" + n
        if n not in index:
            index[n] = len(pal)
            pal.append(nbt.block_state(n))
        return index[n]

    for py in range(height):
        y = height - 1 - py                     # image row 0 = top
        for x in range(W):
            if not m2[py, x]:
                continue
            t = int(thick[py, x])
            blk = get(names[q[py, x]])
            z0 = (depth - t) // 2
            for z in range(z0, z0 + t):
                ids[y, z, x] = blk
    m = Model(ids, pal)
    if floor:
        pass                                    # y0 already the bottom of the silhouette
    if hollow_shell:
        from .hollow import hollow
        hollow(m, shell=hollow_shell, ground=True)
    return m


def from_images(front_path: str, side_path: str, *, height: int, **kw) -> Model:
    """Two orthogonal silhouettes -> intersection volume (front colours win)."""
    f = from_image(front_path, height=height, depth=1, profile="slab", **kw)
    s = from_image(side_path, height=height, depth=1, profile="slab", **kw)
    fm = f.solid()[:, 0, :]                    # (y, x)
    smask = s.solid()[:, 0, :]                 # (y, z)  side image width -> depth
    SY, SX = fm.shape
    SZ = smask.shape[1]
    ids = np.zeros((SY, SZ, SX), np.int32)
    for y in range(SY):
        for x in range(SX):
            if not fm[y, x]:
                continue
            for z in range(SZ):
                if smask[y, z]:
                    ids[y, z, x] = f.ids[y, 0, x]
    m = Model(ids, list(f.palette))
    m.crop_to_content()
    return m


def _edt2d(mask: np.ndarray) -> np.ndarray:
    """Chamfer distance to the nearest False cell (cheap 2-pass EDT)."""
    h, w = mask.shape
    INF = 10 ** 6
    d = np.where(mask, INF, 0).astype(np.int64)
    for y in range(h):
        for x in range(w):
            if d[y, x] == 0:
                continue
            best = d[y, x]
            if y > 0:
                best = min(best, d[y - 1, x] + 1)
            if x > 0:
                best = min(best, d[y, x - 1] + 1)
            d[y, x] = best
    for y in range(h - 1, -1, -1):
        for x in range(w - 1, -1, -1):
            best = d[y, x]
            if y < h - 1:
                best = min(best, d[y + 1, x] + 1)
            if x < w - 1:
                best = min(best, d[y, x + 1] + 1)
            d[y, x] = best
    return d.astype(np.float32)
