"""Place an outside build as an asset: load it, resize it, and make it affordable here.

**SOME THINGS SHOULD NOT BE GENERATED.** The Wyrm's head was a parametric face - sockets, a brow
and a nasal bridge computed onto a 27-course threshold - and it kept reading as a gimmick because
it is roughly two hundred blocks of face pretending to be a skull. The reference in this repo's
own library, `reference/bone_ruins_skull.litematic`, is 54 x 66 x 40 and 38,235 blocks at 26.8%
fill: a hollow skull with sockets you could stand in. No amount of socket tuning closes that, and
the honest move is to use the build rather than imitate it.

Two things this has to do that a plain load does not:

* **RESIZE.** An outside build is whatever size its author made it. `ops.downscale` is the repo's
  own reducer and keeps accents rather than averaging them away.
* **RE-PALETTE.** The reference is 19,877 `light_gray_concrete` plus terracotta, all EXPENSIVE on
  this server, and 1,538 dirt and grass, which is CURRENCY here. `palette.affordable_like` applies
  three gates - cheap by the table, witnessed on this server, and not a functional or machine
  block - and returns nothing rather than a bad substitute, so a block it cannot place is
  REPORTED rather than silently swapped for something wrong.
"""
from __future__ import annotations

from pathlib import Path

from .. import nbt, palette, schem
from ..ops import downscale as downscale_op
from .canvas import Canvas

#: A NEAREST-COLOUR SUBSTITUTE IS NOT ALWAYS A LEGAL ONE. Run over the bone-ruins reference,
#: `palette.affordable_like` proposed `cyan_terracotta -> bedrock`, `dirt -> stripped_spruce_log`
#: and `grass_block -> azalea_leaves` - it optimises colour and knows nothing about what a block
#: IS. So a caller may hand over an explicit map, and for the families this repo actually
#: substitutes there is a default one below: bone reads as wool, soil reads as moss, and nothing
#: functional is ever proposed. Anything not named still goes through `affordable_like`.
SAFE = {
    "light_gray_concrete": "light_gray_wool", "white_terracotta": "white_wool",
    "light_gray_terracotta": "light_gray_wool", "gray_terracotta": "gray_wool",
    "black_terracotta": "black_wool", "black_concrete": "black_wool",
    "brown_concrete": "brown_wool", "green_terracotta": "moss_block",
    "lime_terracotta": "moss_block", "cyan_terracotta": "cyan_wool",
    "orange_terracotta": "orange_wool", "yellow_terracotta": "yellow_wool",
    "orange_concrete": "orange_wool", "yellow_concrete": "yellow_wool",
    "cyan_concrete": "cyan_wool", "terracotta": "brown_wool", "gold_block": "yellow_wool",
    "dirt": "moss_block", "coarse_dirt": "moss_block", "grass_block": "moss_block",
    "short_grass": "moss_carpet", "tall_grass": "moss_carpet",
}

ASSET = {"source": None, "downscale": None, "threshold": 0.42, "min_component": 6,
         "repalette": True, "keep": None, "map": None}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**ASSET, **cfg}
    if not p.get("source"):
        raise ValueError("asset needs params.source = a .litematic path")
    path = Path(p["source"])
    if not path.exists():
        raise ValueError(f"asset source not found: {path}")
    model = schem.load(str(path))
    factor = p.get("downscale")
    if factor and int(factor) > 1:
        model = downscale_op(model, int(factor), threshold=float(p["threshold"]),
                             min_component=int(p["min_component"]))
    sy, sz, sx = model.ids.shape
    canvas = Canvas(sx, sy, sz)
    keep = set(p.get("keep") or ())
    swapped, unplaceable = {}, {}
    remap: dict[int, int] = {}
    for index, entry in enumerate(model.names):
        if not index:
            continue
        name = entry.split("[")[0].replace("minecraft:", "")
        if not p["repalette"] or name in keep:
            remap[index] = canvas.reg._add(model.palette[index]); continue
        if palette.tier(name) == "expensive" or not _spendable(name):
            better = ({**SAFE, **(p.get("map") or {})}).get(name)
            if better is None:
                better, _d = palette.affordable_like(name)
            if better:
                swapped[name] = better
                remap[index] = canvas.state(better)
            else:
                unplaceable[name] = int((model.ids == index).sum())
                remap[index] = 0
        else:
            remap[index] = canvas.reg._add(model.palette[index])
    ys, zs, xs = model.ids.nonzero()
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        blk = remap.get(int(model.ids[y, z, x]), 0)
        if blk:
            canvas.put(x, y, z, blk)
    canvas.meta = {"kind": "asset", "source": str(path), "downscale": factor,
                   "substituted": swapped, "unplaceable": unplaceable,
                   "contract": "an outside build placed as an asset, resized and re-paletted to "
                               "what this server can actually spend - never imitated"}
    return canvas


def _spendable(name: str) -> bool:
    from .. import blocks
    try:
        return blocks.spendable(name)
    except Exception:
        return True


DEFAULTS = ASSET
