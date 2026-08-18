"""Which blocks the SERVER actually has - which is not the same as which the client knows.

The client runs 26.2; skyblock.net runs **1.19**. Every block added after 1.19 exists in
`mcbuild/data/blocks.json` (extracted from the 26.2 jar), renders fine in a card, passes every audit -
and cannot be placed on the server. Bamboo and cherry wood, the whole copper build set, tuff variants,
crafter, trial spawner, vault, pale oak, resin, leaf litter, the 26.x copper golem and shelf: all of it
is invisible to this check unless the check exists.

Two ways to build the allowlist, in order of authority:

  --reports <dir>   a 1.19 data-generator dump. AUTHORITATIVE: it is the server version's own registry.
                    Get it the same way as the 26.2 one, from a 1.19 server jar.
  (default)         PROVISIONAL: blocks proven present in a capture of the real world, plus the
                    curated seed below. Sound as far as it goes - a block in a capture is a block the
                    server placed - but a capture only proves what the island happens to contain, so
                    the pool is far smaller than 1.19 really offers.

The file records which source produced it, so `mcbuild.blocks.available` can say how much to trust it.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "mcbuild/data/server_blocks.json"

# Blocks the designs already use that no capture happens to contain. Every one is 1.17 or earlier;
# they are listed by hand ONLY because no 1.19 registry has been supplied yet. Run with --reports to
# replace this with the real thing.
CURATED = [
    "andesite", "cartography_table", "cauldron", "cut_red_sandstone", "dark_oak_wood", "fern",
    "fletching_table", "grindstone", "loom", "mossy_cobblestone_stairs", "red_shulker_box",
    "small_dripleaf", "smithing_table", "smooth_red_sandstone", "smooth_sandstone",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reports", help="1.19 datagen dir (contains reports/blocks.json) - authoritative")
    ap.add_argument("--version", default="1.19")
    ap.add_argument("--captures", nargs="*", default=["island", "island_deep", "island_void"])
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    if a.reports:
        reg = json.loads((pathlib.Path(a.reports) / "reports/blocks.json").read_text(encoding="utf-8"))
        names = sorted(k.split(":", 1)[-1] for k in reg)
        source = f"datagen {a.version}"
    else:
        sys.path.insert(0, str(ROOT))
        from mcbuild import scan
        seen: set[str] = set()
        used = []
        for c in a.captures:
            try:
                s = scan.load(c)
            except Exception:
                continue
            used.append(c)
            seen |= {n.split(":")[-1].split("[")[0] for n in s.model.names}
        seen |= set(CURATED)
        seen.discard("air")
        names = sorted(seen)
        source = f"captures({','.join(used)})+curated"

    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(
        {"version": a.version, "source": source, "authoritative": bool(a.reports), "blocks": names},
        indent=1), encoding="utf-8")
    print(f"{len(names)} blocks -> {a.out}")
    print(f"  version {a.version}  source {source}  authoritative={bool(a.reports)}")


if __name__ == "__main__":
    main()
