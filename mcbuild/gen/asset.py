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

#: SWAPPED WHATEVER THE ECONOMY SAYS. `SAFE` is only ever consulted for a block that is expensive
#: or unspendable, so a material that is cheap AND spendable passes straight through - and
#: cobblestone is both. Jack banned it outright ("use deep slates etc as necessary, smooth stones,
#: bricks"), and it arrives with any outside build that uses it, which is how 26 cobblestone walls
#: reached a park whose owner had ruled them out. A ban has to be its own gate or it is not a ban.
BANNED = {
    "cobblestone": "stone_bricks", "mossy_cobblestone": "mossy_stone_bricks",
    "cobblestone_wall": "stone_brick_wall", "mossy_cobblestone_wall": "mossy_stone_brick_wall",
    "cobblestone_stairs": "stone_brick_stairs", "cobblestone_slab": "stone_brick_slab",
    "cobbled_deepslate": "polished_deepslate",
}

ASSET = {"source": None, "downscale": None, "threshold": 0.42, "min_component": 6,
         "repalette": True, "keep": None, "map": None,
         #: 0/90/180/270 clockwise about Y. AN OUTSIDE BUILD ARRIVES FACING WHEREVER ITS AUTHOR
         #: LEFT IT, and this park's lots all front one way - so without this the only control
         #: over which side a visitor sees is which corner of the lot you drop it in, which is no
         #: control at all. The bone skull's face points along +U as loaded, and the reach it
         #: stands in is walked along U: a visitor got the PROFILE, which on a skull is thin and
         #: reads as flat. It is not flat; it was edge-on.
         "rotate": 0}

#: A FACING MIRRORS, IT DOES NOT COPY - and a rotation is the same trap one turn further on. Our
#: renderer draws every one of these identically, so a stair turned the wrong way is invisible
#: here and wrong in game for ever, which is why `tests/test_asset_rotate.py` asserts the table
#: rather than anybody eyeballing a picture.
_CW = {"north": "east", "east": "south", "south": "west", "west": "north"}
#: an axis pillar (log, bone_block, basalt) swaps x and z on an odd quarter turn; y is unmoved
_AXIS_CW = {"x": "z", "z": "x", "y": "y"}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**ASSET, **cfg}
    if not p.get("source"):
        raise ValueError("asset needs params.source = a .litematic path")
    path = Path(p["source"])
    if not path.exists():
        raise ValueError(f"asset source not found: {path}")
    model = schem.load(str(path))
    turns = (int(p.get("rotate") or 0) // 90) % 4
    if turns:
        model = _rotate(model, turns)
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
        banned = BANNED.get(name)
        if banned:
            swapped[name] = banned
            remap[index] = canvas.state(banned); continue
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


def _rotate(model, turns: int):
    """Turn a model `turns` quarter-turns clockwise about Y, STATES AND ALL.

    The array is the easy half: `np.rot90` over the (z, x) plane. The half that goes wrong
    silently is the block states - a stair, a wall sign, a trapdoor, a lantern, an axis pillar all
    carry a direction, and rotating the cells while leaving the states behind gives a build whose
    every stair leans the wrong way. This repo has paid for that lesson twice: once on the frog's
    mirrored toes, and once on the railway, where our renderer drew a wrong rail orientation
    identically to a right one.
    """
    import numpy as np
    ids = model.ids
    for _ in range(turns):
        ids = np.rot90(ids, k=-1, axes=(2, 1))       # (y, z, x): turn the z/x plane clockwise
    pal = [model.palette[0]]
    for entry in model.palette[1:]:
        pal.append(_turn_state(entry, turns))
    return schem.Model(np.ascontiguousarray(ids), pal)


def _turn_state(entry, turns: int):
    """One palette entry, its direction properties advanced `turns` quarter-turns clockwise."""
    import copy
    props = entry.value.get("Properties")
    if props is None:
        return entry
    out = copy.deepcopy(entry)
    op = out.value["Properties"].value
    for key, tag in list(op.items()):
        val = tag.value
        if key in ("facing", "rotation") and val in _CW:
            for _ in range(turns):
                val = _CW[val]
            tag.value = val
        elif key == "axis" and val in _AXIS_CW:
            if turns % 2:
                tag.value = _AXIS_CW[val]
        elif key in ("north", "south", "east", "west"):
            pass                                      # handled below, as a set
    # a multi-face block (fence, wall, vine, glass pane, glow lichen) carries one flag per side,
    # and those have to move TOGETHER or the connection ends up on the wrong face
    sides = [k for k in ("north", "east", "south", "west") if k in op]
    if sides:
        was = {k: op[k].value for k in sides}
        for k in sides:
            src = k
            for _ in range(turns):
                src = {v: kk for kk, v in _CW.items()}[src]
            if src in was:
                op[k].value = was[src]
    return out


def _spendable(name: str) -> bool:
    from .. import blocks
    try:
        return blocks.spendable(name)
    except Exception:
        return True


DEFAULTS = ASSET
