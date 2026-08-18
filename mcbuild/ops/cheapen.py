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
