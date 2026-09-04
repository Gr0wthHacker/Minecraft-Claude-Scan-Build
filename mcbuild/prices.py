"""What blocks actually cost, read off the server's own shop by the mod.

`palette.tier()` sorts the whole registry into three hand-written buckets - cheap, ok, expensive -
with the real numbers noted in a COMMENT ("terracotta, 10 grass each"). Every palette this project
has ever picked rests on that table, and CLAUDE.md already calls it invented. `/cscan prices on`
walks the shop menus you open and writes `schematics/prices.json`; this is the read side.

    known()                       is there a price book at all
    buy("stone")                  coins for ONE, or None
    cheapest(pool, rgb, face)     the cheapest block that still matches the colour

**A PRICE IS EVIDENCE, A TIER IS A GUESS, AND THE TWO MUST NOT BE AVERAGED.** Where a price
exists it decides; where it does not, the tier still does, and the caller is told which happened.
Silently filling a missing price with a tier's midpoint would produce a table that looks complete
and is half invented - which is the thing being replaced.

**AND AN UNKNOWN PRICE IS NOT ZERO.** That is the single most dangerous default here: every
unpriced block would become the cheapest thing in the game and every palette would collapse onto
whatever the shop happens not to sell.
"""
from __future__ import annotations

import functools
import json
import os

from . import blocks, palette

# What a tier is worth when there is no real price, ONLY for ordering blocks that have none
# against each other. Never mixed with real coins in a total.
TIER_RANK = {"cheap": 0, "ok": 1, "expensive": 2, "currency": 3}


def path(schem_dir: str | None = None) -> str:
    from .profile import load as load_profile
    return os.path.join(schem_dir or load_profile()["schem_dir"], "prices.json")


@functools.lru_cache(maxsize=4)
def _book(p: str) -> dict:
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def load(schem_dir: str | None = None) -> dict:
    return _book(path(schem_dir))


def known(schem_dir: str | None = None) -> bool:
    return bool(load(schem_dir).get("prices"))


def _short(n: str) -> str:
    return n.split(":")[-1].split("[")[0]


def buy(name: str, schem_dir: str | None = None) -> float | None:
    """Coins to buy ONE, or None when the shop was never seen to sell it."""
    rec = load(schem_dir).get("prices", {}).get(_short(name))
    if not rec:
        return None
    v = rec.get("buy", -1)
    return None if v is None or v < 0 else float(v)


def sell(name: str, schem_dir: str | None = None) -> float | None:
    rec = load(schem_dir).get("prices", {}).get(_short(name))
    if not rec:
        return None
    v = rec.get("sell", -1)
    return None if v is None or v < 0 else float(v)


def cost(counts, schem_dir: str | None = None) -> tuple[float, dict, dict]:
    """(coins, priced, unpriced) for a {block: n} tally.

    The two halves are returned APART on purpose: "4,120 coins" over a bill that is 60% unpriced
    is a number that will be quoted later without its caveat.
    """
    total = 0.0
    priced, unpriced = {}, {}
    for name, n in dict(counts).items():
        c = buy(name, schem_dir)
        if c is None:
            unpriced[_short(name)] = n
        else:
            priced[_short(name)] = c * n
            total += c * n
    return total, priced, unpriced


def rank(name: str, schem_dir: str | None = None) -> tuple[int, float]:
    """Sort key: real prices first and cheapest wins; unpriced blocks fall back to their tier.

    Two keys rather than one number, so a priced block can never sort against a tier estimate as
    though the two were the same kind of evidence.
    """
    c = buy(name, schem_dir)
    if c is not None:
        return (0, c)
    return (1, float(TIER_RANK.get(palette.tier("minecraft:" + _short(name)), 2)))


def cheapest(rgb, tolerance: float = 30.0, pool: list[str] | None = None,
             face: str = "top", schem_dir: str | None = None, **kw) -> str | None:
    """The cheapest block whose colour is still within `tolerance` of the target.

    THE TOLERANCE IS THE WHOLE DESIGN. Nearest-by-colour ignores cost and cheapest-overall ignores
    the build; this asks the only useful question - *of the blocks that would look right, which is
    the least money* - and the answer is only as good as what "look right" is allowed to mean.
    30 is about the gap this file's own notes call invisible (`light_gray_concrete` to `stone` is
    11, `gray_concrete` to `gray_wool` is 15), so it admits real substitutes and not a hue change.
    """
    pool = pool if pool is not None else blocks.candidates(**kw)
    near = []
    for n in pool:
        c = blocks.color(n, face)
        if not c:
            continue
        d = blocks._dist(rgb, c)
        if d <= tolerance:
            near.append((n, d))
    if not near:
        return blocks.nearest(rgb, pool=pool, face=face)      # nothing close: colour wins outright
    near.sort(key=lambda t: (rank(t[0], schem_dir), t[1]))
    return near[0][0]


def report(schem_dir: str | None = None) -> str:
    b = load(schem_dir)
    if not b.get("prices"):
        return (f"no prices yet ({path(schem_dir)}).\n"
                "In game: /cscan prices on, then walk the shop and open every category.")
    rows = []
    for name, rec in b["prices"].items():
        rows.append((name, rec.get("buy", -1), rec.get("sell", -1)))
    rows.sort(key=lambda r: (-(r[1] if r[1] and r[1] > 0 else 0)))
    out = [f"{len(rows)} priced item(s), seen {b.get('updated', '?')} on {b.get('server', '?')}"]
    if b.get("skipped"):
        out.append(f"  {b['skipped']} shop slot(s) had no readable price - "
                   f"tune the patterns in Prices.java if that is most of them")
    out.append(f"  {'item':28s} {'buy':>9s} {'sell':>9s}")
    for name, bu, se in rows[:40]:
        out.append(f"  {name:28s} {bu if bu and bu > 0 else '-':>9} {se if se and se > 0 else '-':>9}")
    if len(rows) > 40:
        out.append(f"  ...and {len(rows) - 40} more")
    return "\n".join(out)
