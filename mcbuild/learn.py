"""Learn placement rules from real world captures.

The audit's placement checks started as hand-written allow-lists ("a lantern stands on a full
cube", "a plant sits on dirt-like"). Real islands break those constantly and are, by
definition, valid — the server enforces placement. So we mine every (block, relation, neighbour)
triple that occurs in a capture and let the audit accept anything that has been seen for real.

    python -m mcbuild learn island [more captures...]     # merges into mcbuild/data/observed.json

Relations: below / above / behind (wall-mounted, opposite of `facing`) / side (vines, per prop).
Air / OOB neighbours are never learned — they are reported as anomalies instead.
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict

import numpy as np

from . import scan as scan_mod, schem
from .audit import DIRV, GROUND_PLANTS, OBSERVED_PATH as DATA_PATH
NOTHING = {"air", "cave_air", "void_air", "OOB"}
CHAIN_SUFFIXES = ("chain",)  # chain, iron_chain, copper_chain, weathered_copper_chain ...


def is_chain(n: str) -> bool:
    return n == "chain" or n.endswith("_chain")


def relations_for(n: str, props: dict) -> list[tuple[str, str, tuple[int, int, int]]]:
    """(kind, relation, offset) cells this block is held by. Empty = not a checked block."""
    if n in ("lantern", "soul_lantern"):
        return [("lantern", "above", (0, 1, 0))] if props.get("hanging") == "true" else [("lantern", "below", (0, -1, 0))]
    if n == "torch" or n == "redstone_torch" or n == "soul_torch":
        return [("torch", "below", (0, -1, 0))]
    if n in ("wall_torch", "redstone_wall_torch", "soul_wall_torch", "ladder") or n.endswith("_wall_sign"):
        dx, dz = DIRV[props.get("facing", "north")]
        return [("wall_torch" if "torch" in n else n if n == "ladder" else "wall_sign", "behind", (-dx, 0, -dz))]
    if is_chain(n):
        return [("chain", "above", (0, 1, 0))] if props.get("axis", "y") == "y" else []
    if n.endswith("_carpet"):
        return [("carpet", "below", (0, -1, 0))]
    if n in GROUND_PLANTS or n.endswith("_tulip") or n in ("lilac", "rose_bush", "peony", "sunflower", "wither_rose", "torchflower"):
        return [(f"plant:{n}", "below", (0, -1, 0))]
    if n in ("cave_vines", "cave_vines_plant", "hanging_roots"):
        return [(n, "above", (0, 1, 0))]
    if n == "pointed_dripstone":
        down = props.get("vertical_direction", "down") == "down"
        return [("dripstone", "above" if down else "below", (0, 1 if down else -1, 0))]
    if n == "vine":
        out = [("vine", "side", (dx, 0, dz)) for d, (dx, dz) in DIRV.items() if props.get(d) == "true"]
        if props.get("up") == "true":
            out.append(("vine", "above", (0, 1, 0)))
        return out
    return []


def mine(m: schem.Model) -> tuple[dict, list[str]]:
    """Return ({kind: {relation: Counter(neighbour)}}, anomalies) for one model."""
    names = np.array([n.split(":")[-1] for n in m.names])
    sy, sz, sx = m.ids.shape
    ids = m.ids
    seen: dict = defaultdict(lambda: defaultdict(Counter))
    anomalies: list[str] = []

    def nm(x, y, z):
        if not (0 <= x < sx and 0 <= y < sy and 0 <= z < sz):
            return "OOB"
        return names[ids[y, z, x]]

    for (y, z, x) in zip(*np.where(ids > 0)):
        n = names[ids[y, z, x]]
        rels = relations_for(n, m.props_at(x, y, z) if n in _PROP_BLOCKS or is_chain(n) or n.endswith("_wall_sign") else {})
        if not rels:
            continue
        if n == "vine":                       # any-of: held by the vine above, or by any flagged side
            _mine_vine(rels, x, y, z, nm, seen, anomalies)
            continue
        for kind, rel, (dx, dy, dz) in rels:  # all-of: exactly one support cell
            nb = nm(x + dx, y + dy, z + dz)
            if nb in NOTHING:
                if nb != "OOB":
                    anomalies.append(f"{n} @({x},{y},{z}) {rel}={nb}")
                continue
            seen[kind][rel][nb] += 1
    return {k: {r: dict(c) for r, c in v.items()} for k, v in seen.items()}, anomalies


def _mine_vine(rels, x, y, z, nm, seen, anomalies):
    if nm(x, y + 1, z) == "vine":
        seen["vine"]["above"]["vine"] += 1
        return
    held = False
    for kind, rel, (dx, dy, dz) in rels:
        nb = nm(x + dx, y + dy, z + dz)
        if nb not in NOTHING:
            seen[kind][rel][nb] += 1
            held = True
    if not held:
        anomalies.append(f"vine @({x},{y},{z}) no attachment")


_PROP_BLOCKS = {"lantern", "soul_lantern", "wall_torch", "redstone_wall_torch", "soul_wall_torch", "ladder",
                "pointed_dripstone", "vine"}


def load_observed() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def mine_palette(m) -> dict:
    """How often each block appears. Placement rules say what is LEGAL; this says what the island is
    actually made of, so a generator can match its texture instead of using hand-tuned weights."""
    import collections
    import numpy as np
    names = [n.split(":")[-1] for n in m.names]
    out = collections.Counter()
    ids, counts = np.unique(m.ids, return_counts=True)
    for i, c in zip(ids.tolist(), counts.tolist()):
        n = names[i]
        if n in ("air", "cave_air", "void_air"):
            continue
        out[n] += int(c)
    return dict(out)


def palette_mix(family: set[str] | None = None, top: int = 12) -> list[tuple[str, float]]:
    """Observed blocks as weights that sum to 1, optionally restricted to a family."""
    counts = load_observed().get("palette", {})
    if family:
        counts = {k: v for k, v in counts.items() if k in family}
    total = sum(counts.values())
    if not total:
        return []
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])[:top]
    scale = sum(c for _, c in ranked)
    return [(n, c / scale) for n, c in ranked]


def merge_into_file(new: dict, source: str, palette: dict | None = None) -> tuple[dict, int]:
    """Merge counts into observed.json; returns (data, number of new (kind, rel, neighbour) triples)."""
    data = load_observed()
    rules = data.setdefault("rules", {})
    added = 0
    for kind, rels in new.items():
        for rel, counts in rels.items():
            bucket = rules.setdefault(kind, {}).setdefault(rel, {})
            for nb, c in counts.items():
                if nb not in bucket:
                    added += 1
                bucket[nb] = bucket.get(nb, 0) + int(c)
    if palette:
        bucket = data.setdefault("palette", {})
        for n, c in palette.items():
            bucket[n] = bucket.get(n, 0) + int(c)
    data.setdefault("sources", [])
    if source not in data["sources"]:
        data["sources"].append(source)
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    return data, added


def learn(names_or_paths: list[str]) -> str:
    lines = []
    for item in names_or_paths:
        try:
            m = scan_mod.load(item).model
        except FileNotFoundError:
            m = schem.load(item)
        mined, anomalies = mine(m)
        _, added = merge_into_file(mined, os.path.basename(item), mine_palette(m))
        triples = sum(len(c) for rels in mined.values() for c in rels.values())
        lines.append(f"{item}: {triples} distinct (block, relation, support) triples, {added} new; "
                     f"{len(anomalies)} anomalies (attached to air)")
        lines += ["   " + a for a in anomalies[:15]]
        if len(anomalies) > 15:
            lines.append(f"   ... {len(anomalies) - 15} more")
    return "\n".join(lines)
