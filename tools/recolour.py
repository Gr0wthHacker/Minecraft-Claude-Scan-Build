"""The real colour of a block: the right FACE, and the biome TINT the game applies to it.

`mcbuild/data/blocks.json` held one RGB per block, sampled from its TOP face and with no tint applied.
Both halves were wrong, and measurably:

    31.7% of the island - 18,006 of 56,739 blocks - is a tint-affected block recorded as GREY.
        13,611 vine        [116,116,116]
         3,066 oak_leaves  [144,144,144]
               grass_block [147,147,147]
    116 blocks have a top and a side face more than 30 apart in some channel
        cherry_log 131 · pale_oak_log 112 · sculk_shrieker 123

Every palette in this project is chosen by `blocks.nearest()` over those numbers, and every render
draws with them, so a third of the island rendered grey and no colour-picked palette could ever
reach for a leaf to get green. It also means the grey-fraction comparisons in CLAUDE.md - the ones
that justified the gallery timber and the soffit wood, both since reverted - were computed with the
foliage counted as stone.

WHY THE FACE IS NOT ONE ANSWER. A floor is read from above and a statue from the side, so this
records BOTH and lets the caller say which it means. Switching everything to the side face would
simply break the floors instead.

    python tools/recolour.py                  # patch mcbuild/data/blocks.json in place
    python tools/recolour.py --report         # say what would change, write nothing

The registry half of the knowledge base is untouched: this needs only the client jar, not a datagen
run. `tools/extract_blocks.py` imports from here so a full re-extract gets the same answer.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import zipfile

from PIL import Image

JAR = pathlib.Path.home() / ".gradle/caches/fabric-loom/26.2/minecraft-client.jar"
OUT = pathlib.Path(__file__).resolve().parent.parent / "mcbuild/data/blocks.json"

# Faces, in preference order, for each of the two answers.
# `side` sits in the TOP order too, ahead of the arbitrary fallback: a grindstone has no top face
# at all (its slots are leg/pivot/round/side) and without this the sorted fallback picked `leg`, the
# dark wooden strut, and called a grey stone block [60,47,26]. A block with no top reads as its side.
TOP_ORDER = ("top", "end", "up", "all", "side", "texture", "cross", "pattern", "front")
SIDE_ORDER = ("side", "north", "all", "texture", "cross", "pattern", "front", "top", "end")
SKIP_TEX = ("overlay", "_stage", "particle")

# ---------------------------------------------------------------------------- tint
#
# The game multiplies certain blocks' greyscale textures by a colour it works out at render time,
# which is why they extract as grey. Three mechanisms, and they are not interchangeable:
#
#   colormap  grass.png / foliage.png, indexed by the biome's temperature and downfall
#   fixed     spruce and birch leaves ignore the biome entirely and use a constant
#   water     its own biome colour, default 0x3F76E4
#
# THE BIOME IS AN ASSUMPTION. skyblock.net's island has no biome we can read offline, so the
# colormap is sampled at PLAINS (temperature 0.8, downfall 0.4) - the game's own default and what
# an unmodified overworld island looks like. If the island turns out to be somewhere else, this is
# the one number to change.
PLAINS_TEMPERATURE, PLAINS_DOWNFALL = 0.8, 0.4

FOLIAGE = ("oak_leaves", "jungle_leaves", "acacia_leaves", "dark_oak_leaves", "mangrove_leaves",
           "pale_oak_leaves", "vine", "oak_sapling", "jungle_sapling", "acacia_sapling",
           "dark_oak_sapling", "mangrove_propagule")
GRASS = ("grass_block", "short_grass", "tall_grass", "fern", "large_fern", "potted_fern",
         "sugar_cane", "attached_melon_stem", "attached_pumpkin_stem", "melon_stem", "pumpkin_stem")
FIXED = {"spruce_leaves": (0x61, 0x99, 0x61), "birch_leaves": (0x80, 0xA7, 0x55),
         "lily_pad": (0x20, 0x80, 0x30)}          # BlockColors.LILY_PAD_IN_WORLD
WATER = ("water", "bubble_column", "water_cauldron")
WATER_RGB = (0x3F, 0x76, 0xE4)


def colormap_rgb(zf: zipfile.ZipFile, which: str, temperature: float, downfall: float):
    """Sample grass.png / foliage.png the way the game indexes them."""
    with zf.open(f"assets/minecraft/textures/colormap/{which}.png") as fh:
        im = Image.open(fh).convert("RGB")
        t = min(max(temperature, 0.0), 1.0)
        d = min(max(downfall, 0.0), 1.0) * t
        x = int((1.0 - t) * 255.0)
        y = int((1.0 - d) * 255.0)
        # the lower-right triangle of the map is undefined; the game never indexes into it
        return im.getpixel((min(x, 255), min(y, 255)))


def tint_for(name: str, tints: dict):
    """The multiplier this block's texture is drawn through, or None if it is drawn as-is."""
    if name in FIXED:
        return FIXED[name]
    if name in WATER:
        return WATER_RGB
    if name in FOLIAGE:
        return tints["foliage"]
    if name in GRASS:
        return tints["grass"]
    return None


def apply_tint(rgb, tint):
    if rgb is None or tint is None:
        return rgb
    return tuple(round(c * t / 255.0) for c, t in zip(rgb, tint))


# ---------------------------------------------------------------------------- textures

def _average(zf, cache, path: str):
    """Mean of the opaque pixels. Transparent ones would drag every plant toward black."""
    if path in cache:
        return cache[path]
    p = f"assets/minecraft/textures/{path.split(':')[-1]}.png"
    out = None
    try:
        with zf.open(p) as fh:
            im = Image.open(fh).convert("RGBA")
            if im.height > im.width and im.height % im.width == 0:
                im = im.crop((0, 0, im.width, im.width))       # first frame of an animation
            px = [q for q in im.getdata() if q[3] > 128]
            if not px:
                px = [q for q in im.getdata() if q[3] > 16]     # stained glass and ice sit near 100
            if px:
                n = len(px)
                out = (round(sum(q[0] for q in px) / n), round(sum(q[1] for q in px) / n),
                       round(sum(q[2] for q in px) / n))
    except (KeyError, OSError):
        out = None
    cache[path] = out
    return out


def _json(zf, path, cache):
    if path in cache:
        return cache[path]
    try:
        with zf.open(path) as fh:
            cache[path] = json.load(fh)
    except (KeyError, OSError, ValueError):
        cache[path] = None
    return cache[path]


def _model_textures(zf, cache, model: str, depth=0) -> dict:
    if depth > 6:
        return {}
    m = _json(zf, f"assets/minecraft/models/{model.split(':')[-1]}.json", cache)
    if not m:
        return {}
    out = {}
    if m.get("parent"):
        out.update(_model_textures(zf, cache, m["parent"], depth + 1))
    for k, v in (m.get("textures") or {}).items():
        out[k] = v.get("sprite") if isinstance(v, dict) else v
    return out


def _models_for(zf, cache, name: str) -> list:
    """Every model any state of this block can use."""
    bs = _json(zf, f"assets/minecraft/blockstates/{name}.json", cache)
    if not bs:
        return [f"block/{name}"]
    out = []

    def walk(node):
        if isinstance(node, dict):
            if "model" in node and isinstance(node["model"], str):
                out.append(node["model"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(bs)
    return out or [f"block/{name}"]


def _resolve(tex, key, depth=0):
    v = tex.get(key)
    if isinstance(v, dict):
        v = v.get("sprite")
    if not isinstance(v, str) or depth > 6:
        return v
    return _resolve(tex, v[1:], depth + 1) if v.startswith("#") else v


def _face(zf, tex, order, tex_cache):
    keys = [k for k in order if k in tex] + sorted(k for k in tex if k not in order)
    for skip in (True, False):
        for k in keys:
            path = _resolve(tex, k)
            if not isinstance(path, str):
                continue
            if skip and any(s in path for s in SKIP_TEX):
                continue
            rgb = _average(zf, tex_cache, path)
            if rgb:
                return rgb
    return None


def colours_for(zf, name: str, caches, tints) -> dict:
    """{'rgb_top': ..., 'rgb_side': ...} with tint applied, or {} if the block has no texture."""
    json_cache, tex_cache = caches
    tex = {}
    for model in _models_for(zf, json_cache, name):
        tex.update(_model_textures(zf, json_cache, model))
    if not tex:
        return {}
    top = _face(zf, tex, TOP_ORDER, tex_cache)
    side = _face(zf, tex, SIDE_ORDER, tex_cache)
    tint = tint_for(name, tints)
    out = {}
    if top:
        out["rgb_top"] = list(apply_tint(top, tint))
    if side:
        out["rgb_side"] = list(apply_tint(side, tint))
    return out


def recolour(jar_path: str, db: dict) -> tuple[dict, list]:
    """Returns (new db, drift rows). Drift rows are (name, old, new_top, delta)."""
    zf = zipfile.ZipFile(jar_path)
    tints = {"grass": colormap_rgb(zf, "grass", PLAINS_TEMPERATURE, PLAINS_DOWNFALL),
             "foliage": colormap_rgb(zf, "foliage", PLAINS_TEMPERATURE, PLAINS_DOWNFALL)}
    caches = ({}, {})
    drift = []
    for name, rec in db.items():
        got = colours_for(zf, name, caches, tints)
        if not got:
            continue
        old = rec.get("rgb")
        rec.update(got)
        # `rgb` stays the TOP face, so every existing caller keeps the meaning it had. What changes
        # is that it is now TINTED, which is the whole point: grass was grey.
        if "rgb_top" in got:
            rec["rgb"] = list(got["rgb_top"])
        if old and rec.get("rgb"):
            d = max(abs(a - b) for a, b in zip(old, rec["rgb"]))
            if d:
                drift.append((name, list(old), list(rec["rgb"]), d))
    drift.sort(key=lambda r: -r[3])
    return db, drift, tints


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jar", default=str(JAR))
    ap.add_argument("--db", default=str(OUT))
    ap.add_argument("--report", action="store_true", help="print the drift and write nothing")
    a = ap.parse_args()

    db = json.loads(pathlib.Path(a.db).read_text(encoding="utf-8"))
    db, drift, tints = recolour(a.jar, db)

    print(f"biome tint sampled at plains (t={PLAINS_TEMPERATURE}, d={PLAINS_DOWNFALL}): "
          f"grass {tints['grass']}  foliage {tints['foliage']}")
    two = sum(1 for r in db.values() if "rgb_side" in r and r.get("rgb_side") != r.get("rgb_top"))
    print(f"blocks with a distinct side face: {two}")
    print(f"blocks whose colour changed: {len(drift)}  (>30: {sum(1 for r in drift if r[3] > 30)})")
    for name, old, new, d in drift[:15]:
        print(f"   {d:4d}  {name:28s} {old} -> {new}")
    if a.report:
        print("\n--report: nothing written")
        return 0
    # compact, matching what tools/extract_blocks.py has always written: this file is 1,196
    # entries and an indented form turns every colour change into a 39,000-line diff.
    pathlib.Path(a.db).write_text(json.dumps(db, separators=(",", ":"), sort_keys=True),
                                  encoding="utf-8")
    print(f"\nwrote {a.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
