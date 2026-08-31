"""Export the placement rules the MOD needs into a resource it can read at runtime.

The wand fills a box in a lived-in world, so it has to answer the same three questions every
generator answers — is this block a mechanism I must not cover, is this material CURRENCY on this
server, and does the 1.19 server even have it. Those answers already exist in Python:

    mcbuild/gen/protect.py   MECHANISM   what a generator must never write over
    mcbuild/blocks.py        ECONOMY     dirt and its forms; money, not material
    mcbuild/data/server_blocks.json      the provisional 1.19 allowlist

Retyping any of them in Java would give two lists that disagree the first time one is edited, and
this project has been bitten by exactly that shape of drift before - which is why `proportions`
and `rubric` share one entry point rather than each measuring for themselves.

So: one source, exported. `tests/test_wand_rules.py` fails if the shipped file drifts from the
Python, so the export cannot be forgotten.

    python tools/export_rules.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcbuild import blocks                      # noqa: E402
from mcbuild.gen import protect                 # noqa: E402

# ---------------------------------------------------------------- storage categories
#
# What goes on which bank of the store hall. The hall's own labels come from its config and are
# recorded in its sidecar; these are the item patterns that decide which label an item belongs
# under, matched as substrings against the item name.
#
# THE NAMES HERE MUST MATCH THE LABELS IN `configs/store_hall.yaml`, because that is how a
# container's category finds its wall. A label with no category and a category with no label both
# simply take no traffic, and `/cscan move` says so rather than guessing.
#
# Measured against the real index before writing: of 97 containers holding something, the hall's
# four labels covered 59 and left 38 uncategorised - dominated by 11,840 ink sacs, ~30,000 wool of
# eight colours, 3,662 arrows, 2,047 froglight and 1,385 scaffolding. So `dyes and wool` and
# `tools and redstone` exist here without a wall to land on yet; they are reported as overflow.
CATEGORIES = {
    "ore and stone": [
        "stone", "cobble", "deepslate", "andesite", "diorite", "granite", "ore", "ingot", "raw_",
        "brick", "tuff", "calcite", "basalt", "blackstone", "gravel", "sand", "glass", "quartz",
        "amethyst", "obsidian", "netherrack", "clay", "terracotta", "concrete", "prismarine",
        "nugget", "scrap", "coal", "flint", "froglight", "shroomlight",
    ],
    "wood and saplings": [
        "log", "_wood", "planks", "sapling", "stick", "stripped", "bamboo", "leaves", "fence",
        "door", "trapdoor", "sign", "boat", "chest",
    ],
    "moss and plants": [
        "moss", "azalea", "vine", "lichen", "fern", "grass", "flower", "lily", "roots", "dripleaf",
        "spore", "mushroom", "cactus", "kelp", "seagrass", "coral", "petal", "bone_meal", "dirt",
        "podzol", "mycelium", "soul_sand", "hanging_roots", "big_dripleaf", "small_dripleaf",
    ],
    "food and crops": [
        "beef", "mutton", "pork", "chicken", "cod", "salmon", "bread", "wheat", "carrot", "potato",
        "beetroot", "melon", "pumpkin", "apple", "berr", "sugar", "cocoa", "egg", "stew", "soup",
        "cooked_", "seeds", "cookie", "cake", "honey", "milk", "rotten", "spider_eye", "kelp_dried",
    ],
    # No wall yet. Named so the overflow can be reported as something rather than as "other".
    "dyes and wool": [
        "wool", "carpet", "dye", "ink_sac", "bed", "banner", "candle",
    ],
    "tools and redstone": [
        "redstone", "repeater", "comparator", "piston", "observer", "hopper", "dropper",
        "dispenser", "rail", "torch", "lantern", "arrow", "scaffolding", "bucket", "pickaxe",
        "shovel", "axe", "hoe", "sword", "shears", "bow", "shield", "helmet", "chestplate",
        "leggings", "boots", "potion", "book", "paper", "string", "gunpowder", "slime", "ender",
    ],
}

OUT = ROOT / "chunkscan" / "src" / "main" / "resources" / "chunkscan_rules.json"
RECIPES_OUT = ROOT / "chunkscan" / "src" / "main" / "resources" / "chunkscan_recipes.json"

# ---------------------------------------------------------------- the plot
#
# THE BOUNDARY IS FOUND, NOT TYPED - `mcbuild/plot.py` reads the island's bedrock out of a
# capture and measures 49 out on each axis. The mod could not see it at all, so `/cscan fill`
# would happily draw a box over the line and the Island Run shipped 120 cells past the edge
# before a human noticed. Exported here so the wand answers the same boundary the generators do.
#
# It is a SQUARE. A radius check would waste the corners and overrun the sides.
PLOT_FROM = ROOT / "out" / "island_full.litematic"


def plot_payload() -> dict:
    """The plot square, or a note saying why it could not be found.

    NEVER falls back to a typed centre. A boundary check guarding the wrong square is worse
    than no boundary check, because it is believed.
    """
    from mcbuild import plot as plot_mod
    for cand in (PLOT_FROM, ROOT / "out" / "island_now.litematic"):
        if not cand.exists():
            continue
        try:
            pl = plot_mod.find(str(cand))
        except Exception as e:                                  # noqa: BLE001
            continue
        x0, z0, x1, z1 = pl.bounds
        return {"found": True, "source": cand.name, "cx": pl.cx, "cz": pl.cz,
                "radius": pl.radius, "x0": x0, "z0": z0, "x1": x1, "z1": z1}
    return {"found": False, "why": "no bedrock found in any capture under out/"}


def payload() -> dict:
    server = json.loads((ROOT / "mcbuild" / "data" / "server_blocks.json").read_text("utf-8"))
    return {
        "_comment": "GENERATED by tools/export_rules.py - do not hand-edit. "
                    "Source: mcbuild/gen/protect.py, mcbuild/blocks.py, data/server_blocks.json.",
        # substring match, exactly as `protect.is_protected` does it
        "protected": sorted(protect.MECHANISM),
        # exact short-name match, exactly as `blocks.spendable` does it
        "economy": sorted(blocks.ECONOMY),
        # the server allowlist is PROVISIONAL (191 of 1.19's blocks), so the mod only ever WARNS
        # on it - the same posture `audit` takes. See rule 12.
        "server_blocks": sorted(server.get("blocks", [])),
        "server_authoritative": bool(server.get("authoritative", False)),
        # substring patterns, longest first so a specific match beats a generic one
        "categories": {k: sorted(v, key=len, reverse=True) for k, v in CATEGORIES.items()},
        # the buildable square, derived from the bedrock - see plot_payload()
        "plot": plot_payload(),
    }


def recipes_payload() -> dict:
    """The recipe tree, so `/cscan craft` can answer in game what `mcbuild craft` answers here.

    BAKED INTO THE JAR, unlike designs.json - these change when the GAME changes, which is the
    same test that decides where chunkscan_rules.json lives.
    """
    src = ROOT / "mcbuild" / "data" / "recipes.json"
    if not src.exists():
        return {"recipes": {}, "note": "run tools/extract_recipes.py"}
    d = json.loads(src.read_text("utf-8"))
    return {"_comment": "GENERATED by tools/export_rules.py from mcbuild/data/recipes.json.",
            "note": d.get("note", ""), "recipes": d.get("recipes", {})}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d = payload()
    OUT.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  protected {len(d['protected'])}  economy {len(d['economy'])}  "
          f"server {len(d['server_blocks'])} (authoritative={d['server_authoritative']})  "
          f"categories {len(d['categories'])}")
    pl = d["plot"]
    print("  plot: " + (f"X {pl['x0']}..{pl['x1']} Z {pl['z0']}..{pl['z1']} (from {pl['source']})"
                        if pl.get("found") else "NOT FOUND - " + pl.get("why", "")))
    r = recipes_payload()
    RECIPES_OUT.write_text(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {RECIPES_OUT.relative_to(ROOT)}: {sum(len(v) for v in r['recipes'].values())} "
          f"recipes for {len(r['recipes'])} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
