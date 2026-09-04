"""Replace expensive blocks with cheap hue-matched equivalents."""
from __future__ import annotations

from collections import Counter

import numpy as np

from .. import nbt, palette
from ..schem import Model


def cheapen(m: Model, *, extra: dict[str, str] | None = None,
            keep: set[str] | None = None) -> Counter:
    """In-place. `extra` adds/overrides substitutions (short or full names).
    `keep` lists names to leave alone (e.g. a 4-block orange_concrete beak).
    Returns Counter of {src_name: count_replaced}."""
    extra = {(k if ":" in k else "minecraft:" + k): (v if ":" in v else "minecraft:" + v)
             for k, v in (extra or {}).items()}
    keep = {(k if ":" in k else "minecraft:" + k) for k in (keep or set())}
    replaced: Counter = Counter()
    for i, e in list(enumerate(m.palette)):
        src = nbt.state_name(e)
        if src in keep:
            continue
        dst = extra.get(src) or palette.substitute(src)
        if not dst or dst == src:
            continue
        di = m.ensure_state(dst)                    # simple state (no props) for the target
        n = int((m.ids == i).sum())
        if n:
            m.ids[m.ids == i] = di
            replaced[src] += n
    m.compact_palette()
    return replaced


def cheapen_by_price(m: Model, *, tolerance: float = 30.0, keep: set[str] | None = None,
                     face: str = "side", schem_dir: str | None = None) -> Counter:
    """In-place, but priced from the SERVER's own shop rather than from the invented tier table.

    `palette.substitute` maps expensive -> cheap by hand and by hue. This asks the shop instead:
    of the blocks that would still look right (within `tolerance` of the original's colour), which
    is the least money. Returns {(src, dst): count}.

    **IT DOES NOTHING WITHOUT A PRICE BOOK**, deliberately. Falling back to the tier table here
    would make `--by-price` a synonym for `cheapen` that merely sounds better informed, and the
    caller would never learn the shop had not been walked.

    **`face` defaults to SIDE, not top.** A statue is read in elevation and 155 blocks differ
    between their two faces; the top-face default is right for a floor and wrong for everything
    this operation is usually pointed at.
    """
    from .. import prices as prices_mod

    if not prices_mod.known(schem_dir):
        return Counter()
    keep = {(k if ":" in k else "minecraft:" + k) for k in (keep or set())}
    pool = None
    replaced: Counter = Counter()
    for i, e in list(enumerate(m.palette)):
        src = nbt.state_name(e)
        if src in keep or src.endswith("air"):
            continue
        rgb = palette.color_of(src, face) if hasattr(palette, "color_of") else None
        from .. import blocks as blocks_mod
        rgb = rgb or blocks_mod.color(src, face)
        if not rgb:
            continue
        if pool is None:
            pool = blocks_mod.candidates(full_only=False)
        here = prices_mod.buy(src, schem_dir)
        dst = prices_mod.cheapest(rgb, tolerance=tolerance, pool=pool, face=face,
                                  schem_dir=schem_dir)
        if not dst:
            continue
        dst = "minecraft:" + dst.split(":")[-1]
        there = prices_mod.buy(dst, schem_dir)
        # Only move for a REAL, PRICED saving. Swapping an unpriced block for another unpriced one
        # is churn dressed up as economy, and it changes how the build looks for nothing.
        if dst == src or here is None or there is None or there >= here:
            continue
        di = m.ensure_state(dst)
        n = int((m.ids == i).sum())
        if n:
            m.ids[m.ids == i] = di
            replaced[(src.split(":")[-1], dst.split(":")[-1])] += n
    m.compact_palette()
    return replaced
