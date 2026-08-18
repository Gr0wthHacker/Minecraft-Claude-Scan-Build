"""Build the block knowledge base from the GAME, not from memory.

Two authoritative sources, both offline:

  1. Mojang's data generator (`net.minecraft.data.Main --reports`) -> `blocks.json`: every block in the
     registry, every state property, every legal value for it. 1196 blocks / 32366 states on 26.2.
  2. The client jar's own assets -> the real colour of every block, by resolving
     blockstates/<name>.json -> models/block/*.json (through the parent chain) -> textures/block/*.png
     and averaging the pixels that are actually opaque.

Why this exists: `palette.COLORS` was ~150 hand-typed RGB guesses, and every block outside it rendered
magenta or silently fell back. Worse, nothing checked that a block state we emit is LEGAL - an invalid
property value only turns up when Litematica refuses to place it, in game, an hour later.

Run it when the game updates:

    python tools/extract_blocks.py --reports <dir with reports/blocks.json>

It writes `mcbuild/data/blocks.json`. `mcbuild/blocks.py` is the query side.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import zipfile

from PIL import Image

JAR = pathlib.Path.home() / ".gradle/caches/fabric-loom/26.2/minecraft-client.jar"
OUT = pathlib.Path(__file__).resolve().parent.parent / "mcbuild/data/blocks.json"

# Which face to sample, in order of preference. `top` first: a schematic is nearly always read from
# above, and a block's top face is the colour Minecraft's own maps use.
FACE_ORDER = ("top", "all", "end", "side", "texture", "cross", "pattern", "front", "up")
# Textures that say nothing about the block's colour.
SKIP_TEX = ("overlay", "_stage", "particle")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reports", required=True, help="datagen output dir (contains reports/blocks.json)")
    ap.add_argument("--jar", default=str(JAR))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    reg = json.loads((pathlib.Path(a.reports) / "reports/blocks.json").read_text(encoding="utf-8"))
    zf = zipfile.ZipFile(a.jar)
    cache: dict[str, dict] = {}
    tex_cache: dict[str, tuple] = {}

    out, no_color = {}, []
    for full, entry in sorted(reg.items()):
        name = full.split(":", 1)[-1]
        props = entry.get("properties") or {}
        rec = {"type": (entry.get("definition") or {}).get("type", "").split(":")[-1],
               "props": props,
               "states": len(entry.get("states") or ())}
        rgb = _color_of(zf, cache, tex_cache, name)
        if rgb:
            rec["rgb"] = list(rgb)
        else:
            no_color.append(name)
        # the default state, so callers can emit a block without naming every property
        for st in entry.get("states") or ():
            if st.get("default"):
                if st.get("properties"):
                    rec["default"] = st["properties"]
                break
        out[name] = rec

    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"{len(out)} blocks -> {a.out}")
    print(f"  with colour: {sum(1 for v in out.values() if 'rgb' in v)}")
    print(f"  without    : {len(no_color)}" + (f"  e.g. {no_color[:6]}" if no_color else ""))
    print(f"  states     : {sum(v['states'] for v in out.values())}")


# ---------------------------------------------------------------- asset resolution

def _read(zf, path: str, cache: dict):
    if path not in cache:
        try:
            cache[path] = json.loads(zf.read(path).decode("utf-8"))
        except KeyError:
            cache[path] = None
    return cache[path]


def _models_for(zf, cache, name: str) -> list[str]:
    """Every model a blockstate can resolve to. Handles both `variants` and `multipart`."""
    bs = _read(zf, f"assets/minecraft/blockstates/{name}.json", cache)
    if not bs:
        return []
    found = []

    def take(node):
        if isinstance(node, dict):
            if "model" in node and isinstance(node["model"], str):
                found.append(node["model"])
            for v in node.values():
                take(v)
        elif isinstance(node, list):
            for v in node:
                take(v)

    take(bs.get("variants") or {})
    take(bs.get("multipart") or [])
    return found


def _textures_for(zf, cache, model: str, depth: int = 0) -> dict:
    """Collect a model's textures, walking `parent` so inherited slots are included."""
    if depth > 8:
        return {}
    m = _read(zf, f"assets/minecraft/models/{model.split(':')[-1]}.json", cache)
    if not m:
        return {}
    tex = {}
    if m.get("parent"):
        tex.update(_textures_for(zf, cache, m["parent"], depth + 1))
    tex.update(m.get("textures") or {})
    return tex


def _resolve(tex: dict, key: str, depth: int = 0):
    """`#side` style indirection: a slot can point at another slot.

    26.2 also lets a slot be an OBJECT - {"sprite": "...", "force_translucent": true} - which is how
    every translucent block is declared now. Reading only the string form silently lost all 37 of
    them (stained glass and panes) to the no-colour list."""
    v = tex.get(key)
    if isinstance(v, dict):
        v = v.get("sprite")
    if not isinstance(v, str) or depth > 6:
        return v
    return _resolve(tex, v[1:], depth + 1) if v.startswith("#") else v


def _color_of(zf, cache, tex_cache, name: str):
    tex = {}
    for model in _models_for(zf, cache, name):
        tex.update(_textures_for(zf, cache, model))
    if not tex:
        return None
    keys = [k for k in FACE_ORDER if k in tex] + sorted(k for k in tex if k not in FACE_ORDER)
    for k in keys:
        path = _resolve(tex, k)
        if not isinstance(path, str) or any(s in path for s in SKIP_TEX):
            continue
        rgb = _average(zf, tex_cache, path)
        if rgb:
            return rgb
    # Fallback: take the skipped ones after all. Crops are ONLY ever `_stage` textures, so skipping
    # them on the first pass and accepting them here gets the ripe look without preferring an overlay.
    for k in keys:
        path = _resolve(tex, k)
        if isinstance(path, str):
            rgb = _average(zf, tex_cache, path)
            if rgb:
                return rgb
    return None


def _average(zf, tex_cache, path: str):
    """Mean of the opaque pixels. Transparent ones would drag every plant toward black."""
    if path in tex_cache:
        return tex_cache[path]
    p = f"assets/minecraft/textures/{path.split(':')[-1]}.png"
    out = None
    try:
        with zf.open(p) as fh:
            im = Image.open(fh).convert("RGBA")
            # animated textures (water, fire) are a vertical strip of frames: take the first
            if im.height > im.width and im.height % im.width == 0:
                im = im.crop((0, 0, im.width, im.width))
            px = [q for q in im.getdata() if q[3] > 128]
            if not px:
                # stained glass and ice sit at alpha ~100: opaque enough to have a colour, and the
                # only thing the strict threshold was ever excluding.
                px = [q for q in im.getdata() if q[3] > 16]
            if px:
                n = len(px)
                out = (round(sum(q[0] for q in px) / n), round(sum(q[1] for q in px) / n),
                       round(sum(q[2] for q in px) / n))
    except (KeyError, OSError):
        out = None
    tex_cache[path] = out
    return out


if __name__ == "__main__":
    main()
