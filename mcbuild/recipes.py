"""What a block is MADE of - the query side of `mcbuild/data/recipes.json`.

`bom` and `shop` stop at the block: they say 518 powered rails and leave you to work out that
this is 3,108 gold ingots, 518 redstone and 87 planks, and whether any of that is in a chest.
On a server where nothing is mined that is the only question there is, and it was being answered
by hand.

    ways("powered_rail")            every recipe that produces it
    raw_cost("powered_rail")        how many BASE units one costs, cheapest path
    plan({"powered_rail": 518}, have)   the actual craft: steps in order, stock used, shortfall

Four things this has to get right, and each of them is a way to be confidently wrong:

* **CYCLES.** iron_ingot -> iron_block -> 9 iron_ingot. Every recursion carries the path it came
  by and refuses a recipe that re-enters it; without that, costing any of the 22 storage blocks
  in the game never returns.
* **THE CHEAPEST PATH IS OFTEN THE STONECUTTER.** Crafting stairs is 6 blocks for 4; cutting is
  1 for 1. Over a design that is a third of the stone. `raw_cost` picks per output unit, so the
  cutter wins on its own merits rather than being special-cased.
* **DIRT IS CURRENCY**, so a route that spends it is not a route. Currency carries a cost
  penalty rather than a ban - if it is genuinely the only path the plan still says so, loudly,
  instead of reporting the item as unobtainable.
* **A LIST OF ALTERNATIVES IS RESOLVED BY WHAT YOU HAVE.** `stick` takes any of fourteen planks
  and `torch` takes coal or charcoal. Picking the first one in the file sends you shopping for
  something while the alternative sits in a chest.

The 26.2-vs-1.19 split rides along with every answer: `plan` marks any step whose result or
ingredients are outside the server allowlist, and reports rather than refuses - the allowlist is
provisional and would reject `allium`.
"""
from __future__ import annotations

import collections
import functools
import json
import math
import pathlib

from . import blocks

DATA = pathlib.Path(__file__).resolve().parent / "data/recipes.json"

# A route through currency is not a route. High enough to lose to any real alternative, finite so
# that "the only way is to spend dirt" is still an answer rather than "impossible".
CURRENCY_PENALTY = 1000.0
# Same shape for a block the 1.19 server does not have: prefer anything else, but stay answerable.
OFF_SERVER_PENALTY = 50.0
MAX_DEPTH = 16


@functools.lru_cache(maxsize=1)
def _db() -> dict:
    if not DATA.exists():
        return {"recipes": {}}
    d = json.loads(DATA.read_text(encoding="utf-8"))
    # The file is keyed BY result item, so a recipe on its own does not know what it makes.
    # Stamped once here rather than searched for later.
    for item, rs in d.get("recipes", {}).items():
        for r in rs:
            r["item"] = item
    mark_reversible(d)          # idempotent: a file written before this still reads correctly
    return d


def mark_reversible(d: dict) -> None:
    """Flag every PACKING pair - X made from 9 Y, and Y made from 1 X.

    WRITTEN INTO THE DATA FILE by `tools/extract_recipes.py`, not computed per language. It was
    computed at load time in Python only, and the Java port then read a file with no flag in it -
    so the two resolvers gave different answers to the same question, which is precisely the drift
    `proportions.measure` and `rubric.score` share one entry point to avoid. Still applied on load
    as well, so a recipes.json written before this keeps working.

    THIS IS THE ARBITRAGE THAT MADE THE FIRST RESOLVER LIE. Costing every leaf at 1 unit makes
    `raw_gold_block` (1 item) a cheaper source of `raw_gold` than raw_gold is, because 1 becomes
    9 for free. It planned 518 powered rails out of 58 gold blocks nobody owns, and the cycle
    guard did not catch it - a cycle guard stops the recursion, it does not stop the arithmetic.
    A packing recipe is only ever worth taking when the block is ALREADY IN A CHEST, so these are
    barred from cost-minimisation and offered only against real stock.
    """
    rec = d.get("recipes", {})
    for item, rs in rec.items():
        for r in rs:
            for slot in r["needs"]:
                for a in slot["alts"]:
                    if any(item in s2["alts"] for back in rec.get(a, []) for s2 in back["needs"]):
                        r["reversible"] = True


def available() -> bool:
    """False if nobody has run `tools/extract_recipes.py` yet - callers say so rather than
    silently reporting every block as a raw material."""
    return bool(_db().get("recipes"))


def _short(n: str) -> str:
    return n.split(":")[-1].split("[")[0]


def ways(item: str) -> list[dict]:
    """Every recipe producing `item`, in file order."""
    return _db().get("recipes", {}).get(_short(item), [])


def _off_server(item: str) -> bool:
    """Is this a BLOCK the 1.19 server does not have.

    THE ALLOWLIST HOLDS BLOCKS, AND MOST INGREDIENTS ARE ITEMS. Asking it about `gold_ingot`,
    `stick` or `redstone` gets a no - not because the server lacks them but because a list of
    blocks has nothing to say about an item. Applied blind it priced every ingot 50x a block, so
    the resolver "saved" 518 gold by smelting deepslate gold ore, which no chest on this island
    has ever held. Same shape as rule 11's `NOT_FULL` holding "grass": one list, asked the wrong
    question. Only a name the registry knows as a block can be judged by it.
    """
    return blocks.exists(item) and not blocks.available(item)


def _leaf_cost(item: str) -> float:
    if not blocks.spendable("minecraft:" + item):
        return CURRENCY_PENALTY
    if _off_server(item):
        return OFF_SERVER_PENALTY
    return 1.0


def raw_cost(item: str, _path: frozenset = frozenset(), _depth: int = 0) -> float:
    """Base units one of `item` costs by the cheapest recipe chain. A leaf costs 1.

    Per OUTPUT unit, so a stonecutter recipe (1 -> 1) beats a crafting one (6 -> 4) by the ratio
    that actually matters rather than by ingredient count.
    """
    item = _short(item)
    if item in _path or _depth > MAX_DEPTH:
        return math.inf
    best = _leaf_cost(item)
    path = _path | {item}
    for r in ways(item):
        if r.get("reversible"):
            continue
        tot = 0.0
        for slot in r["needs"]:
            alt = min((raw_cost(a, path, _depth + 1) for a in slot["alts"]), default=math.inf)
            if alt is math.inf:
                tot = math.inf
                break
            tot += alt * slot["n"]
        if tot is not math.inf:
            per = tot / max(1, r["count"])
            if per < best:
                best = per
    return best


class Plan:
    """The answer: what to craft, in what order, out of what, and what is still missing."""

    def __init__(self):
        self.steps: list[dict] = []            # {recipe, item, times, made, kind, depth}
        self.used: collections.Counter = collections.Counter()      # taken from your containers
        self.short: collections.Counter = collections.Counter()     # raw material you must get
        self.raw: collections.Counter = collections.Counter()       # every base unit consumed
        self.off_server: set = set()
        self.currency: collections.Counter = collections.Counter()
        self.no_recipe: set = set()

    @property
    def smelts(self) -> int:
        return sum(s["made"] for s in self.steps if s["kind"] in ("smelt", "cook"))

    def report(self, width: int = 26) -> str:
        out = []
        if self.steps:
            out.append("CRAFT, in this order:")
            for s in self.steps:
                verb = {"craft": "craft", "cut": "cut  ", "smelt": "smelt", "cook": "cook "}[s["kind"]]
                ing = ", ".join(f"{n}x {i}" for i, n in s["from"].items())
                out.append(f"  {verb} {s['made']:6d}x {s['item']:<{width}} from {ing}")
            if self.smelts:
                out.append(f"  ({self.smelts} items to smelt = about {math.ceil(self.smelts / 8)} coal of fuel)")
        if self.used:
            out.append("FROM YOUR CONTAINERS:")
            for k, n in self.used.most_common():
                out.append(f"  {n:8d}x {k}")
        if self.short:
            out.append("SHORT - you must farm, buy or trade for these:")
            for k, n in self.short.most_common():
                tag = ""
                if k in self.currency:
                    tag = "   <- CURRENCY on this server"
                elif k in self.off_server:
                    tag = "   <- not in the 1.19 allowlist (provisional, may be a false alarm)"
                out.append(f"  {n:8d}x {k}{tag}")
        else:
            out.append("SHORT: nothing - this is craftable from what you have.")
        if self.no_recipe:
            out.append("no recipe known for: " + ", ".join(sorted(self.no_recipe))
                       + "  (raw material, or a recipe this version does not have)")
        return "\n".join(out)


def _pick(alts: list[str], have: collections.Counter) -> str:
    """Which alternative to spend. What you HAVE MOST OF wins; ties go to the cheapest to make.

    This is the difference between `stick` sending you for oak when the chest holds 3,000 jungle
    planks, and it just working.
    """
    real = [a for a in alts if blocks.spendable("minecraft:" + a)] or alts
    return max(real, key=lambda a: (have.get(a, 0), -raw_cost(a)))


def _per_unit(r: dict, path: frozenset) -> float:
    """Base units one OUTPUT of this recipe costs, or inf if any ingredient is unreachable."""
    tot = 0.0
    for slot in r["needs"]:
        alt = min((raw_cost(a, path) for a in slot["alts"]), default=math.inf)
        if alt is math.inf:
            return math.inf
        tot += alt * slot["n"]
    return tot / max(1, r["count"])


def _best_recipe(item: str, path: frozenset) -> dict | None:
    best, best_cost = None, math.inf
    for r in ways(item):
        if r.get("reversible"):
            continue
        tot = 0.0
        for slot in r["needs"]:
            if any(_short(a) in path for a in slot["alts"]):
                tot = math.inf
                break
            alt = min((raw_cost(a, path) for a in slot["alts"]), default=math.inf)
            tot = math.inf if alt is math.inf else tot + alt * slot["n"]
            if tot is math.inf:
                break
        if tot is not math.inf:
            per = tot / max(1, r["count"])
            if per < best_cost:
                best, best_cost = r, per
    return best


def plan(want: dict | collections.Counter, have: dict | collections.Counter | None = None) -> Plan:
    """Resolve `want` down to raw materials, spending `have` on the way.

    `have` is consumed as the walk goes, so two targets needing the same ingredient cannot both
    be told the whole stock is theirs - which is the same allocate-in-rank-order rule the build
    loop's `/cscan plan` already follows.
    """
    p = Plan()
    stock = collections.Counter({_short(k): int(v) for k, v in (have or {}).items()})
    times: collections.Counter = collections.Counter()
    recipe_of: dict[str, dict] = {}
    ingredients_of: dict[str, dict] = {}
    depth_of: dict[str, int] = {}

    def need(item: str, qty: int, path: frozenset, depth: int) -> int:
        """Returns the depth of the deepest craft used, so steps can be ordered afterwards."""
        item = _short(item)
        take = min(qty, stock[item])
        if take:
            stock[item] -= take
            p.used[item] += take
            qty -= take
        if qty <= 0:
            return depth
        # Unpack a block you ALREADY HAVE before making anything: a chest of raw_gold_block is
        # 9x raw_gold and no trip. Barred from the cost model above, allowed here against stock.
        for r in ways(item):
            if not r.get("reversible") or qty <= 0:
                continue
            for slot in r["needs"]:
                src = next((a for a in slot["alts"] if stock[a] > 0), None)
                if src is None or len(r["needs"]) != 1:
                    continue
                runs = min(stock[src] // slot["n"], math.ceil(qty / r["count"]))
                if runs <= 0:
                    continue
                stock[src] -= runs * slot["n"]
                p.used[src] += runs * slot["n"]
                times[r["id"]] += runs
                recipe_of[r["id"]] = r
                ingredients_of.setdefault(r["id"], collections.Counter())[src] += runs * slot["n"]
                depth_of[r["id"]] = max(depth_of.get(r["id"], 0), depth)
                made = runs * r["count"]
                stock[item] += max(0, made - qty)
                qty -= min(qty, made)
        if qty <= 0:
            return depth
        if depth > MAX_DEPTH:
            p.short[item] += qty
            return depth
        r = _best_recipe(item, path)
        # CRAFTING IS NOT ALWAYS THE ANSWER. A recipe that costs the same as the thing it makes
        # is a wash, and following it anyway sends you shopping for its ingredients instead:
        # the first version answered "518 powered rails" with "smelt 522 deepslate gold ore",
        # which is not a material this server has in any chest. So craft when it is genuinely
        # cheaper, or when you ALREADY HOLD an ingredient - otherwise say you are short of the
        # item itself, which is the thing you would actually go and buy.
        if r is not None and _per_unit(r, path) >= _leaf_cost(item):
            if not any(stock[a] > 0 for slot in r["needs"] for a in slot["alts"]):
                r = None
        if r is None:
            p.short[item] += qty
            p.raw[item] += qty
            if not blocks.spendable("minecraft:" + item):
                p.currency[item] += qty
            elif _off_server(item):
                p.off_server.add(item)
            if not ways(item):
                p.no_recipe.add(item)
            return depth
        n = math.ceil(qty / r["count"])
        times[r["id"]] += n
        recipe_of[r["id"]] = r
        deepest = depth
        for slot in r["needs"]:
            pick = _pick(slot["alts"], stock)
            ingredients_of.setdefault(r["id"], collections.Counter())[pick] += slot["n"] * n
            deepest = max(deepest, need(pick, slot["n"] * n, path | {item}, depth + 1))
        made = n * r["count"]
        stock[item] += made - qty          # leftovers are real; the next target may want them
        depth_of[r["id"]] = max(depth_of.get(r["id"], 0), deepest)
        if _off_server(item):
            p.off_server.add(item)
        return deepest

    for item, qty in want.items():
        if int(qty) > 0:
            need(item, int(qty), frozenset(), 0)

    # DEEPEST FIRST: a recipe cannot run before the things it eats exist, and the same recipe can
    # be reached from several targets at different depths. Ordering by the deepest reach is what
    # makes one flat list of steps actually runnable top to bottom.
    for rid in sorted(times, key=lambda k: -depth_of.get(k, 0)):
        r = recipe_of[rid]
        p.steps.append({
            "recipe": rid, "item": r["item"], "kind": r["kind"],
            "times": times[rid], "made": times[rid] * r["count"],
            "from": dict(ingredients_of.get(rid, {})),
        })
    return p
