"""Build `mcbuild/data/recipes.json` from the client jar's own recipe data.

    python tools/extract_recipes.py                       # finds the loom jar itself
    python tools/extract_recipes.py --jar <path to minecraft-client.jar>

**1,585 recipe files and 191 item tags are sitting inside the client jar**, under
`data/minecraft/recipe/` and `data/minecraft/tags/item/`. No datagen run is needed - this is the
same jar `tools/extract_blocks.py` already opens for textures. Rule 11 says ask the game rather
than your memory, and until now the BOM stopped at the block because nothing had asked the game
what a block is MADE of.

NOTE the folder is `recipe/`, singular, in 26.x. It was `recipes/` up to 1.20.

**THE VERSION SPLIT APPLIES HERE TOO, AND HARDER THAN IT DOES FOR BLOCKS.** These are 26.2
recipes and skyblock.net runs 1.19: a recipe can exist for a block the server does not have, and
a ratio can have been retuned between versions. On top of that a skyblock server may add or
remove recipes outright. So this file is PROVISIONAL exactly as `server_blocks.json` is - every
consumer reports rather than refuses, and `mcbuild.recipes` marks any step whose result or
ingredients are outside the 1.19 allowlist so the doubt travels with the answer.

What is kept, and what is deliberately dropped:

    kept     crafting_shaped · crafting_shapeless · stonecutting · smelting · blasting ·
             smoking · campfire_cooking · crafting_transmute
    dropped  smithing_* and every crafting_special_* - a firework, a banner duplicate or an
             item repair has no fixed ingredient list, so a resolver cannot cost it and
             pretending otherwise is worse than saying nothing

An ingredient is one of three shapes and all three are normalised to a LIST OF ALTERNATIVES:
a plain item, a `#tag` reference (flattened here, recursively - tags nest), or an inline array
of items. The resolver then picks between alternatives by what is actually in your containers,
which is the whole reason the alternatives are preserved rather than collapsed to the first one.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "mcbuild/data/recipes.json"

RECIPE_DIR = "data/minecraft/recipe/"
TAG_DIR = "data/minecraft/tags/item/"

# Every type whose ingredients are a fixed, costable list. Anything else is dropped by name.
KINDS = {
    "minecraft:crafting_shaped": "craft",
    "minecraft:crafting_shapeless": "craft",
    "minecraft:crafting_transmute": "craft",
    "minecraft:stonecutting": "cut",
    "minecraft:smelting": "smelt",
    "minecraft:blasting": "smelt",
    "minecraft:smoking": "cook",
    "minecraft:campfire_cooking": "cook",
}


def find_jar() -> pathlib.Path | None:
    """The loom cache holds several jars and only the merged one carries data/."""
    home = pathlib.Path.home() / ".gradle/caches/fabric-loom"
    best = None
    for j in home.rglob("*.jar"):
        n = j.name
        if "minecraft" in n and ("client" in n or "common" in n) and "only" not in n:
            if best is None or j.stat().st_size > best.stat().st_size:
                best = j
    return best


def _short(name: str) -> str:
    return name.split(":")[-1] if not name.startswith("#") else name


def _flatten_tag(tag: str, tags: dict, seen: set | None = None) -> list[str]:
    """A tag's items, following nested `#tag` references. Cycles are impossible in vanilla data
    but a malformed pack would hang this, so the seen-set is not optional."""
    seen = seen or set()
    if tag in seen:
        return []
    seen.add(tag)
    out = []
    for v in tags.get(tag, []):
        if isinstance(v, dict):
            v = v.get("id", "")
        if not isinstance(v, str) or not v:
            continue
        if v.startswith("#"):
            out.extend(_flatten_tag(v[1:].split(":")[-1], tags, seen))
        else:
            out.append(v.split(":")[-1])
    return out


def _alts(ing, tags: dict) -> list[str]:
    """One ingredient -> the list of items that satisfy it, short names, order preserved."""
    if ing is None:
        return []
    if isinstance(ing, str):
        if ing.startswith("#"):
            return _flatten_tag(ing[1:].split(":")[-1], tags)
        return [ing.split(":")[-1]]
    if isinstance(ing, dict):
        if "tag" in ing:
            return _flatten_tag(str(ing["tag"]).split(":")[-1], tags)
        if "item" in ing:
            return [str(ing["item"]).split(":")[-1]]
        if "id" in ing:
            return [str(ing["id"]).split(":")[-1]]
        return []
    if isinstance(ing, list):
        out = []
        for e in ing:
            out.extend(_alts(e, tags))
        return out
    return []


def _needs(rec: dict, tags: dict) -> list[tuple[list[str], int]]:
    """(alternatives, quantity) per distinct ingredient slot."""
    t = rec.get("type", "")
    if t == "minecraft:crafting_shaped":
        key = rec.get("key", {})
        counts: collections.Counter = collections.Counter()
        for row in rec.get("pattern", []):
            for ch in row:
                if ch != " ":
                    counts[ch] += 1
        out = []
        for ch, n in counts.items():
            a = _alts(key.get(ch), tags)
            if a:
                out.append((a, n))
        return out
    if t == "minecraft:crafting_shapeless":
        counts = collections.Counter()
        order: list[tuple] = []
        for ing in rec.get("ingredients", []):
            a = tuple(_alts(ing, tags))
            if not a:
                continue
            if a not in counts:
                order.append(a)
            counts[a] += 1
        return [(list(a), counts[a]) for a in order]
    if t == "minecraft:crafting_transmute":
        out = []
        for k in ("input", "material"):
            a = _alts(rec.get(k), tags)
            if a:
                out.append((a, 1))
        return out
    a = _alts(rec.get("ingredient"), tags)
    return [(a, 1)] if a else []


def _grid(rec: dict, tags: dict) -> list | None:
    """The 3x3 crafting grid, as nine slots of alternatives (empty slots are []).

    `_needs` aggregates a recipe to totals, which is all a COST needs and not enough to CRAFT:
    putting six stone bricks anywhere in the grid does not make stairs. Shaped recipes are
    anchored top-left, which is where the game matches them from; shapeless ones are filled in
    order, because for those any arrangement works by definition.

    Only crafting recipes get one. A stonecutter has a button, and a furnace has two slots.
    """
    t = rec.get("type", "")
    if t == "minecraft:crafting_shaped":
        key = rec.get("key", {})
        pat = rec.get("pattern", [])
        if len(pat) > 3 or any(len(r) > 3 for r in pat):
            return None
        g = [[] for _ in range(9)]
        for r, row in enumerate(pat):
            for c, ch in enumerate(row):
                if ch != " ":
                    g[r * 3 + c] = _alts(key.get(ch), tags)
        return g
    if t == "minecraft:crafting_shapeless":
        flat = []
        for ing in rec.get("ingredients", []):
            a = _alts(ing, tags)
            if a:
                flat.append(a)
        if len(flat) > 9:
            return None
        return flat + [[] for _ in range(9 - len(flat))]
    return None


def build(jar: pathlib.Path) -> dict:
    tags: dict[str, list] = {}
    raw: list[tuple[str, dict]] = []
    with zipfile.ZipFile(jar) as z:
        for n in z.namelist():
            if n.startswith(TAG_DIR) and n.endswith(".json"):
                try:
                    tags[n[len(TAG_DIR):-5]] = json.loads(z.read(n)).get("values", [])
                except Exception:                              # noqa: BLE001
                    continue
            elif n.startswith(RECIPE_DIR) and n.endswith(".json"):
                try:
                    raw.append((n[len(RECIPE_DIR):-5], json.loads(z.read(n))))
                except Exception:                              # noqa: BLE001
                    continue

    out: dict[str, list] = {}
    dropped: collections.Counter = collections.Counter()
    for rid, rec in sorted(raw):
        kind = KINDS.get(rec.get("type", ""))
        if kind is None:
            dropped[rec.get("type", "?")] += 1
            continue
        res = rec.get("result") or {}
        item = str(res.get("id", "")).split(":")[-1]
        if not item:
            dropped["no result id"] += 1
            continue
        needs = _needs(rec, tags)
        if not needs:
            dropped["no ingredients"] += 1
            continue
        entry = {
            "id": rid, "kind": kind, "count": int(res.get("count", 1) or 1),
            "needs": [{"alts": a, "n": n} for a, n in needs],
        }
        g = _grid(rec, tags)
        if g is not None:
            entry["grid"] = g
        out.setdefault(item, []).append(entry)

    # Marked HERE, in the file, so the Python and the Java resolver read one source. Computed at
    # load time it existed only in Python, and the Java port silently priced a gold block as a
    # cheap source of gold.
    sys.path.insert(0, str(ROOT))
    from mcbuild import recipes as recipes_mod
    recipes_mod.mark_reversible({"recipes": out})

    return {
        "source": jar.name,
        "note": "26.2 client recipes; skyblock.net is 1.19. PROVISIONAL - report, never refuse.",
        "recipes": out,
        "tags": {k: _flatten_tag(k, tags) for k in ("planks", "logs", "stone_crafting_materials",
                                                    "wooden_slabs", "coals")
                 if k in tags},
        "dropped": dict(dropped),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jar", help="minecraft-client.jar (the MERGED one, with data/ in it)")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)

    jar = pathlib.Path(a.jar) if a.jar else find_jar()
    if not jar or not jar.exists():
        print("no client jar found under ~/.gradle/caches/fabric-loom - pass --jar", file=sys.stderr)
        return 2
    data = build(jar)
    if not data["recipes"]:
        print(f"{jar} holds no {RECIPE_DIR} entries - wrong jar? (the client-ONLY jar has no data/)",
              file=sys.stderr)
        return 2
    pathlib.Path(a.out).write_text(json.dumps(data, separators=(",", ":"), sort_keys=True),
                                   encoding="utf-8")
    n = sum(len(v) for v in data["recipes"].values())
    print(f"{a.out}: {n} recipes for {len(data['recipes'])} items, from {jar.name}")
    if data["dropped"]:
        print("dropped (no fixed ingredient list): "
              + ", ".join(f"{k.split(':')[-1]} x{v}" for k, v in sorted(data["dropped"].items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
