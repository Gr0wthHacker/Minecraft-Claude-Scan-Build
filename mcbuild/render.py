"""Orthographic previews, slices, ASCII block maps, contact sheets.

Renders are for eyeballing only -- depth-shading darkens recesses more than
in-game lighting does. For ground truth use `ascii_map`.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from . import palette
from .schem import Model

VIEWS = ("face", "front", "side", "left", "top", "back")


def _rgb(m: Model) -> np.ndarray:
    out = np.zeros((len(m.palette), 3), np.uint8)
    for i, n in enumerate(m.names):
        out[i] = palette.color_of(n)
    return out


def elevation(m: Model, view: str = "face", shade: bool = True) -> np.ndarray:
    """First solid block seen from a camera. face=+z, front=-z, side=+x,
    left=-x, top=+y, back = front. Returns HxWx3 uint8, row 0 = highest y."""
    ids, s = m.ids, m.solid()
    rgb = _rgb(m)
    sy, sz, sx = ids.shape
    if view in ("face",):
        order, shape, pick, depth = range(sz - 1, -1, -1), (sy, sx), (lambda k: (s[:, k, :], ids[:, k, :])), sz
    elif view in ("front", "back"):
        order, shape, pick, depth = range(sz), (sy, sx), (lambda k: (s[:, k, :], ids[:, k, :])), sz
    elif view == "side":
        order, shape, pick, depth = range(sx - 1, -1, -1), (sy, sz), (lambda k: (s[:, :, k], ids[:, :, k])), sx
    elif view == "left":
        order, shape, pick, depth = range(sx), (sy, sz), (lambda k: (s[:, :, k], ids[:, :, k])), sx
    elif view == "top":
        order, shape, pick, depth = range(sy - 1, -1, -1), (sz, sx), (lambda k: (s[k], ids[k])), sy
    else:
        raise ValueError(view)
    img = np.full(shape + (3,), 245, np.uint8)
    done = np.zeros(shape, bool)
    for step, k in enumerate(order):
        sm, im = pick(k)
        hit = sm & ~done
        if not hit.any():
            continue
        f = 1.0 - 0.45 * (step / depth) if shade else 1.0
        img[hit] = (rgb[im[hit]] * f).astype(np.uint8)
        done |= hit
    if view != "top":
        img = img[::-1]
    if view in ("left", "front"):
        img = img[:, ::-1]
    return img


def slice_img(m: Model, axis: str, k: int) -> np.ndarray:
    rgb = _rgb(m)
    s = m.solid()
    if axis == "y":
        ids, sm = m.ids[k], s[k]
    elif axis == "z":
        ids, sm = m.ids[:, k, :], s[:, k, :]
    else:
        ids, sm = m.ids[:, :, k], s[:, :, k]
    img = np.full(ids.shape + (3,), 245, np.uint8)
    img[sm] = rgb[ids[sm]]
    return img[::-1] if axis in ("z", "x") else img


def sheet(images: list[np.ndarray], scale: int = 10, pad: int = 12,
          align_bottom: bool = True) -> Image.Image:
    ims = [Image.fromarray(a).resize((a.shape[1] * scale, a.shape[0] * scale), Image.NEAREST)
           for a in images]
    w = sum(i.width for i in ims) + pad * (len(ims) + 1)
    h = max(i.height for i in ims) + 2 * pad
    canvas = Image.new("RGB", (w, h), (215, 215, 215))
    x = pad
    for i in ims:
        y = h - pad - i.height if align_bottom else pad
        canvas.paste(i, (x, y))
        x += i.width + pad
    return canvas


def contact_sheet(m: Model, views=("face", "side", "front", "top"), scale: int = 10) -> Image.Image:
    return sheet([elevation(m, v) for v in views], scale=scale)


def ascii_map(m: Model, view: str = "face", chars: dict | None = None,
              y_from: int = 0, y_to: int | None = None) -> str:
    """Block map of the frontmost cell per (y, x). Ground truth for faces."""
    s = m.solid()
    sy, sz, sx = s.shape
    names = [n.split(":")[-1] for n in m.names]
    y_to = sy if y_to is None else y_to
    if view == "face":
        zi = np.where(s, np.arange(sz)[None, :, None], -1)
        f = zi.max(axis=1)
        cell = lambda y, x: (y, f[y, x], x) if f[y, x] >= 0 else None
        cols = sx
    elif view == "front":
        zi = np.where(s, np.arange(sz)[None, :, None], sz + 9)
        f = zi.min(axis=1)
        cell = lambda y, x: (y, f[y, x], x) if f[y, x] < sz else None
        cols = sx
    elif view == "side":
        xi = np.where(s, np.arange(sx)[None, None, :], -1)
        f = xi.max(axis=2)
        cell = lambda y, z: (y, z, f[y, z]) if f[y, z] >= 0 else None
        cols = sz
    else:
        raise ValueError(view)
    chars = chars or {}
    auto: dict[str, str] = {}
    lines = []
    for y in range(min(y_to, sy) - 1, y_from - 1, -1):
        row = ""
        for c in range(cols):
            k = cell(y, c)
            if k is None:
                row += " "
                continue
            n = names[m.ids[k]]
            ch = chars.get(n)
            if ch is None:
                ch = auto.setdefault(n, chr(ord("a") + len(auto) % 26))
            row += ch
        if row.strip():
            lines.append(f"{y:3d} {row}")
    legend = "  ".join(f"{v}={k}" for k, v in {**chars, **auto}.items())
    return "\n".join(lines) + "\n     " + legend


# ------------------------------------------------------------------ isometric

_THIN = {"moss_carpet": 0.07, "lily_pad": 0.07, "pink_petals": 0.07, "redstone_wire": 0.08}
_HALF = ("_slab",)
_POST = {"chain": 0.2, "oak_fence": 0.3, "spruce_fence": 0.3, "cobblestone_wall": 0.5, "lantern": 0.45,
         "soul_lantern": 0.45, "iron_bars": 0.2, "vine": 0.15, "campfire": 0.9}
_PLANT = {"wheat": 0.8, "carrots": 0.5, "potatoes": 0.5, "beetroots": 0.5, "sweet_berry_bush": 0.8,
          "azalea": 0.9, "flowering_azalea": 0.9, "fern": 0.6, "short_grass": 0.5, "dandelion": 0.5,
          "poppy": 0.5, "oxeye_daisy": 0.5, "cornflower": 0.5, "allium": 0.6, "azure_bluet": 0.4}


def _block_box(n: str, props: dict) -> tuple[float, float, float]:
    """(width fraction, height fraction, y-offset fraction) for drawing."""
    if n in _THIN:
        return 1.0, _THIN[n], 0.0
    if n.endswith(_HALF):
        return (1.0, 0.5, 0.5) if props.get("type") == "top" else (1.0, 0.5, 0.0)
    if n.endswith("_trapdoor"):
        return (1.0, 0.2, 0.8) if props.get("half") == "top" else (1.0, 0.2, 0.0)
    if n in _POST:
        return _POST[n], 1.0, 0.0
    if n in _PLANT:
        return 0.55, _PLANT[n], 0.0
    if n == "water":
        return 1.0, 0.85, 0.0
    if n.endswith("_stairs"):
        return 1.0, 1.0, 0.0
    if n == "farmland":
        return 1.0, 0.94, 0.0
    return 1.0, 1.0, 0.0


def isometric(m: Model, scale: int = 18, flip: bool = False, ground_rows: int = 0) -> Image.Image:
    """Painter's-order isometric render. Camera from +x,+z (or -x,+z when flip)."""
    from PIL import ImageDraw
    ids = m.ids
    sy, sz, sx = ids.shape
    names = [n.split(":")[-1] for n in m.names]
    rgb = _rgb(m)
    s = float(scale)
    W = int((sx + sz) * s + 4 * s); H = int((sx + sz) * s / 2 + sy * s + 4 * s)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img, "RGBA")
    ox = sz * s + 2 * s
    oy = 2 * s + sy * s
    solid = m.solid()

    def proj(x, y, z):
        xx = (sx - 1 - x) if flip else x
        return ox + (xx - z) * s, oy + (xx + z) * s / 2 - y * s

    cells = [(y, z, x) for (y, z, x) in zip(*np.where(ids > 0))]
    cells.sort(key=lambda c: (c[2] + c[1] + c[0]) if not flip else ((sx - 1 - c[2]) + c[1] + c[0]))
    for (y, z, x) in cells:
        i = int(ids[y, z, x]); n = names[i]
        # skip fully buried full blocks (all three visible faces covered)
        nx = x + 1 if not flip else x - 1
        if (0 <= nx < sx and solid[y, z, nx]) and (z + 1 < sz and solid[y, z + 1, x]) and (y + 1 < sy and solid[y + 1, z, x]) \
                and names[int(ids[y, z, nx])] not in _PLANT and names[int(ids[y, z + 1, x])] not in _PLANT \
                and names[int(ids[y + 1, z, x])] not in _PLANT and not names[int(ids[y + 1, z, x])].endswith("_slab") \
                and names[int(ids[y + 1, z, x])] not in _THIN and names[int(ids[y + 1, z, x])] not in _POST:
            continue
        w, h, dy = _block_box(n, m.props_at(x, y, z))
        col = tuple(int(v) for v in rgb[i])
        alpha = 170 if n == "water" else 255
        top = tuple(min(255, int(v * 1.0)) for v in col) + (alpha,)
        left = tuple(int(v * 0.72) for v in col) + (alpha,)
        right = tuple(int(v * 0.55) for v in col) + (alpha,)
        # cube corner: block centre offset for narrow boxes
        cx0 = (1 - w) / 2
        bx, by = proj(x + cx0, y + dy, z + cx0)
        # top-face rhombus corners for a w x w footprint at height h
        def P(dx, dz, dyy):
            px, py = proj(x + cx0 + dx * w, y + dy + dyy, z + cx0 + dz * w)
            return (px, py)
        t0, t1, t2, t3 = P(0, 0, h), P(1, 0, h), P(1, 1, h), P(0, 1, h)
        b1, b2, b3 = P(1, 0, 0), P(1, 1, 0), P(0, 1, 0)
        edge = tuple(int(v * 0.38) for v in col) + (alpha,)
        if flip:
            # visible sides are -x and +z faces
            dr.polygon([t3, t2, b2, b3], fill=right, outline=edge)
            dr.polygon([t0, t3, b3, P(0, 0, 0)], fill=left, outline=edge)
        else:
            dr.polygon([t1, t2, b2, b1], fill=left, outline=edge)
            dr.polygon([t3, t2, b2, b3], fill=right, outline=edge)
        dr.polygon([t0, t1, t2, t3], fill=top, outline=edge)
    # crop to content with margin
    bbox = img.getbbox()
    if bbox:
        img = img.crop((bbox[0] - 8, bbox[1] - 8, bbox[2] + 8, bbox[3] + 8))
    bg = Image.new("RGBA", img.size, (236, 232, 222, 255))
    bg.alpha_composite(img)
    return bg.convert("RGB")
