"""What the corrected colours change — reported, never applied.

`tools/recolour.py` fixed two things in the block knowledge base: the biome TINT the game applies
(so `grass_block` is green rather than [147,147,147]) and the fact that a block has a top face AND a
side face. Nothing about any DESIGN was touched, and this is the tool that says what that decision
is costing or hiding.

Three separate kinds of drift, and only the first is cosmetic:

  1. RENDERS. `views.py` draws with these numbers, so any design holding a re-coloured block now
     renders differently. On the island that is a third of every picture.
  2. SCORES. The rubric's `palette` and `form` dimensions are measured off block colours, so an
     animal's grade can move without a single cell changing.
  3. CHOICES. Anything that picks a block by colour - `blocks.nearest` - can now reach blocks it
     could not see before, and can be pulled away from ones it used to like.

    python tools/colour_drift.py                 # designs + scores
    python tools/colour_drift.py --picks         # ...and what nearest() would now choose

Run it against a saved copy of the old database to compare:

    python tools/colour_drift.py --old <blocks.json before recolour>
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np                                  # noqa: E402

from mcbuild import schem                           # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB = ROOT / "mcbuild/data/blocks.json"


def _load(path) -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _rgb(rec):
    return tuple(rec.get("rgb") or ()) or None


def changed(old: dict, new: dict) -> dict:
    """name -> (old rgb, new rgb, max channel delta)"""
    out = {}
    for name, rec in new.items():
        a, b = _rgb(old.get(name, {})), _rgb(rec)
        if not a or not b or a == b:
            continue
        out[name] = (a, b, max(abs(p - q) for p, q in zip(a, b)))
    return out


def designs_affected(drift: dict, out_dir="out"):
    """Per design: how many of its cells are a block whose colour moved."""
    rows = []
    for lit in sorted(pathlib.Path(out_dir).glob("*.litematic")):
        side = lit.with_suffix("").with_suffix(".scan.json")
        if not side.exists():
            side = pathlib.Path(str(lit)[: -len(".litematic")] + ".scan.json")
        if not side.exists():
            continue
        try:
            m = schem.load(str(lit))
        except Exception:
            continue
        names = [n.split(":")[-1].split("[")[0] for n in m.names]
        total = hit = 0
        worst = collections.Counter()
        for i, n in enumerate(names):
            if n in ("air", "cave_air", "void_air"):
                continue
            k = int((m.ids == i).sum())
            total += k
            if n in drift:
                hit += k
                worst[n] += k
        if hit:
            rows.append((lit.stem, total, hit, worst.most_common(3)))
    rows.sort(key=lambda r: -(r[2] / max(1, r[1])))
    return rows


def score_drift(old_db: dict):
    """Re-score every built animal against the OLD colours and the new ones."""
    from mcbuild import blocks
    import importlib
    try:
        rubric = importlib.import_module("tools.rubric")
    except Exception:
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            rubric = importlib.import_module("rubric")
        except Exception:
            return []
    if not hasattr(rubric, "score"):
        return []

    designs = [p.stem for p in sorted(pathlib.Path("out").glob("X *.litematic"))]
    rows = []
    for name in designs:
        try:
            new = rubric.score(name)
        except Exception:
            continue
        blocks._db.cache_clear()
        original = DB.read_text(encoding="utf-8")
        try:
            DB.write_text(json.dumps(old_db), encoding="utf-8")
            blocks._db.cache_clear()
            old = rubric.score(name)
        except Exception:
            old = None
        finally:
            DB.write_text(original, encoding="utf-8")
            blocks._db.cache_clear()
        if old is not None:
            rows.append((name, old, new))
    return rows


def pick_drift(old_db: dict, new_db: dict, targets):
    """For a handful of target colours, what nearest() chose then and chooses now."""
    from mcbuild import blocks

    def pick_with(db, rgb, face):
        original = DB.read_text(encoding="utf-8")
        try:
            DB.write_text(json.dumps(db), encoding="utf-8")
            blocks._db.cache_clear()
            return blocks.nearest(rgb, face=face)
        finally:
            DB.write_text(original, encoding="utf-8")
            blocks._db.cache_clear()

    rows = []
    for label, rgb in targets:
        for face in ("top", "side"):
            a = pick_with(old_db, rgb, face)
            b = pick_with(new_db, rgb, face)
            if a != b:
                rows.append((label, rgb, face, a, b))
    return rows


TARGETS = [
    ("leaf green", (60, 100, 30)),
    ("grass green", (90, 130, 60)),
    ("moss", (90, 110, 50)),
    ("water blue", (60, 100, 180)),
    ("golden tan", (190, 150, 90)),
    ("bark brown", (110, 85, 50)),
    ("bone pale", (230, 226, 205)),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--old", help="a blocks.json from before the recolour")
    ap.add_argument("--picks", action="store_true")
    ap.add_argument("--scores", action="store_true")
    a = ap.parse_args()

    new = _load(DB)
    if not a.old:
        print("no --old given: reporting the two-face split only\n")
        two = {n: r for n, r in new.items() if r.get("rgb_side") and r.get("rgb_side") != r.get("rgb_top")}
        print(f"blocks whose top and side differ: {len(two)}")
        worst = sorted(two.items(),
                       key=lambda kv: -max(abs(p - q) for p, q in zip(kv[1]["rgb_top"], kv[1]["rgb_side"])))
        for n, r in worst[:12]:
            d = max(abs(p - q) for p, q in zip(r["rgb_top"], r["rgb_side"]))
            print(f"   {d:4d}  {n:28s} top {r['rgb_top']}  side {r['rgb_side']}")
        return 0

    old = _load(a.old)
    drift = changed(old, new)
    print(f"blocks whose recorded colour changed: {len(drift)}")
    for n, (o, b, d) in sorted(drift.items(), key=lambda kv: -kv[1][2])[:10]:
        print(f"   {d:4d}  {n:26s} {list(o)} -> {list(b)}")

    print("\n--- designs whose RENDER changes ---")
    rows = designs_affected(drift)
    if not rows:
        print("   none")
    for name, total, hit, worst in rows[:14]:
        share = 100.0 * hit / max(1, total)
        w = ", ".join(f"{k}x{v}" for k, v in worst)
        print(f"   {share:5.1f}%  {name:28s} {hit}/{total}   {w}")

    if a.picks:
        print("\n--- what nearest() now chooses instead ---")
        pr = pick_drift(old, new, TARGETS)
        if not pr:
            print("   nothing changed")
        for label, rgb, face, was, now in pr:
            print(f"   {label:12s} {rgb} [{face:4s}]  {was}  ->  {now}")

    if a.scores:
        print("\n--- rubric scores ---")
        for name, o, n in score_drift(old):
            print(f"   {name:24s} {o} -> {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
