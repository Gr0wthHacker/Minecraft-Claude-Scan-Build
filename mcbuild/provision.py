"""What a design needs BEFORE anyone can build it, and the part of it that is buildable today.

**THE LOOP IS A LAST MILE WITH NO SUPPLY CHAIN.** Measured against `Park Complete` and the live
container index: the park-local chests cover **9 of 180 materials**, 413,685 blocks (76%) have no
reachable source, and the worst single line is 103,089 `moss_block` - which has no recipe at all,
because moss is a bone-meal FARM. Every stall, every message-spam fix and every flight repair of
the last month has been the last mile of a journey whose goods were never made.

The mod can already `craft`, `smelt`, `buy`, `farm` and `take`. What nothing did was plan
ACQUISITION as part of a build, so the loop's honest answer to three quarters of that design was a
shrug it had no way to express: it flew to the work, found nothing it could place, and reported a
dead end.

Two outputs, and the second is the point:

* a **shortfall classified by how it can actually be obtained** - covered by stock, craftable from
  stock, smeltable, buyable at a known price, farmable here, or nothing-we-know-of;
* a **WORK PACKAGE**: the subset of the design whose materials are covered, written out as its own
  design at the parent's own origin. `/cscan follow` on that can finish. `follow` on the whole park
  cannot, and had no way to say so.

**IT NEVER GUESSES A SOURCE.** A material with no recipe, no price and no stock is reported as
having none, rather than folded into "farm it" because that sounds like an answer. That is the same
posture the ten park gates take: a gate with no evidence blocks rather than passing.
"""
from __future__ import annotations

import collections
import os

from . import coop, items, recipes, scan


#: How a shortfall can be answered, best first, so the report reads as a plan.
SOURCES = ("craft", "smelt", "buy", "farm", "none")

#: Materials this island produces itself, so "you are short" has a real answer rather than a shrug.
#:
#: DELIBERATELY SHORT AND EVIDENCE-BASED. A long guessed list would turn "we do not know" into
#: "farm it", which is exactly the confident-sounding non-answer this module exists to avoid.
FARMED = {
    "moss_block", "moss_carpet", "oak_log", "birch_log", "spruce_log", "jungle_log",
    "acacia_log", "dark_oak_log", "mangrove_log", "cherry_log", "bamboo", "sugar_cane",
    "kelp", "cactus", "wheat", "carrot", "potato", "beetroot", "melon", "pumpkin",
    "cobblestone", "stone", "gravel", "sand", "clay_ball", "dirt", "ice", "snowball",
    "glow_berries", "sweet_berries", "vine", "glow_lichen", "azalea", "flowering_azalea",
    "oak_leaves", "birch_leaves", "spruce_leaves", "jungle_leaves", "acacia_leaves",
    "dark_oak_leaves", "mangrove_leaves", "cherry_leaves", "azalea_leaves",
    "flowering_azalea_leaves", "pointed_dripstone", "dripstone_block", "water_bucket",
    "lava_bucket", "sugar", "bone_meal", "string", "wheat_seeds",
}


class Package:
    """What is covered, what is short and why, and how much of the design is buildable today."""

    def __init__(self, design: str):
        self.design = design
        self.want: collections.Counter = collections.Counter()      # item -> cells wanting it
        self.have: collections.Counter = collections.Counter()      # item -> in your containers
        self.short: collections.Counter = collections.Counter()     # item -> still missing
        self.source: dict[str, str] = {}                            # item -> one of SOURCES
        self.cells_total = 0
        self.cells_ready = 0
        self.steps: list = []

    @property
    def coverage(self) -> float:
        return self.cells_ready / self.cells_total if self.cells_total else 0.0

    def report(self, top: int = 15) -> str:
        out = [f"{self.design}: {self.cells_ready:,} of {self.cells_total:,} cells have their"
               f" material ({100 * self.coverage:.0f}%)"]
        if not self.short:
            out.append("nothing is short - this design can be built from what you own")
            return "\n".join(out)
        by = collections.Counter(self.source.get(i, "none") for i in self.short)
        out.append("materials short, by how they can be got: "
                   + ", ".join(f"{k} {by[k]}" for k in SOURCES if by[k]))
        for src in SOURCES:
            rows = [(i, n) for i, n in self.short.most_common() if self.source.get(i) == src]
            if not rows:
                continue
            out.append(f"  {src.upper()}")
            for item, n in rows[:top]:
                out.append(f"    {item:30s} {n:9,}")
            if len(rows) > top:
                out.append(f"    ... and {len(rows) - top} more")
        if self.steps:
            out.append(f"({len(self.steps)} of these can be made from stock - `mcbuild craft` "
                       f"prints the order)")
        return "\n".join(out)


def _classify(item: str, prices: dict) -> str:
    """How this shortfall could be answered. Never a guess - see the module docstring."""
    ways = recipes.ways(item)
    if ways:
        kinds = {r.get("kind") for r in ways}
        if kinds and not (kinds - {"smelt", "cook"}):
            return "smelt"
        return "craft"
    if item in prices:
        return "buy"
    return "farm" if item in FARMED else "none"


def plan(design: str, world: str | None = None, *, schem_dir: str | None = None,
         boxed: bool = True) -> Package:
    """Resolve `design` to what must be acquired, and to what is buildable right now.

    `world` measures against a capture first, so a half-built design asks about what is LEFT.
    Without one every cell counts, which is the right question for a design nobody has started.
    """
    p = Package(os.path.basename(design))
    cells = (coop.progress(design, world).remaining_cells if world
             else list(coop.Grid(scan.load(design)).cells()))
    for _pos, name in cells:
        p.want[items.item_for(name)] += 1
    p.cells_total = sum(p.want.values())
    p.have = coop.load_storage(schem_dir, boxed=boxed)
    prices = coop.load_prices()

    # WHAT THE STOCK COVERS, then what the stock can be MADE into: two different answers, and the
    # second is only worth having where the first ran out. So the recipe resolver is pointed at
    # the SHORTFALL rather than at the whole design - which is also what stops it planning a
    # thousand crafts for material already sitting in a chest.
    shortfall = collections.Counter()
    for item, n in p.want.items():
        got = min(n, p.have.get(item, 0))
        if n > got:
            shortfall[item] = n - got
    if shortfall and recipes.available():
        made = recipes.plan(shortfall, p.have)
        p.steps = made.steps
        p.short.update({i: n for i, n in made.short.items() if n > 0})
    else:
        p.short.update(shortfall)

    for item in p.short:
        p.source[item] = _classify(item, prices)

    for item, n in p.want.items():
        p.cells_ready += max(0, n - p.short.get(item, 0))
    return p


def write_package(design: str, out: str, world: str | None = None, *,
                  schem_dir: str | None = None, boxed: bool = True) -> tuple[str, Package]:
    """Write the buildable subset as its own design, AT THE PARENT'S ORIGIN.

    Same origin, because a package is a view of one design rather than a new one: place it, follow
    it, and every block lands exactly where the parent wanted it. A package with an origin of its
    own would be a second thing to keep aligned, which is the trap `origin_lock` exists for.

    A material only partly covered contributes that many cells, taken in the design's own order -
    so the package builds bottom-up exactly as the whole design would rather than scattering the
    covered part across the build.
    """
    import numpy as np
    p = plan(design, world, schem_dir=schem_dir, boxed=boxed)
    d = scan.load(design)
    names = {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(d.model.palette)}
    budget = collections.Counter({i: n - p.short.get(i, 0) for i, n in p.want.items()})
    keep = np.zeros(d.model.ids.shape, bool)
    ys, zs, xs = np.where(d.model.ids > 0)
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        it = items.item_for(names[int(d.model.ids[y, z, x])])
        if budget[it] > 0:
            budget[it] -= 1
            keep[y, z, x] = True
    m = d.model.copy()
    m.ids = np.where(keep, m.ids, 0)
    m.tile_entities = [t for t in (getattr(m, "tile_entities", None) or [])
                       if keep[t.value["y"].value, t.value["z"].value, t.value["x"].value]]
    m.compact_palette()
    meta = {**d.meta, "package_of": os.path.basename(d.litematic_path),
            "kind": "work-package",
            "coverage_pct": round(100 * p.coverage, 1),
            "non_air_blocks": int((m.ids > 0).sum()),
            "note": "the part of the parent design whose materials are covered - `/cscan follow` "
                    "this and it can finish; the parent cannot and could not say so"}
    side = scan.save_pair(out, m, meta, name=os.path.splitext(os.path.basename(out))[0])
    return side, p
