"""`out/history.json` — one row per design per sync, so progress has a slope instead of a snapshot.

`progress` answers "how much is left". The question you actually act on is "how many more sessions
is that", which needs a second data point. This appends one, and reports the rate.
"""
from __future__ import annotations

import datetime
import json
import os

PATH = "out/history.json"


def _load(path: str = PATH) -> list:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def record(rows: dict, *, when: str | None = None, path: str = PATH) -> str:
    """rows: {design name: (built, total)}. One entry per call; nothing is ever rewritten."""
    hist = _load(path)
    stamp = when or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    hist.append({"at": stamp, "designs": {k: list(v) for k, v in rows.items()}})
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=1)
    return path


def report(path: str = PATH, top: int = 12) -> str:
    hist = _load(path)
    if len(hist) < 2:
        return f"history: {len(hist)} entry so far - the rate needs a second sync to exist"
    first, last = hist[0], hist[-1]
    lines = [f"history: {len(hist)} syncs, {_short(first['at'])} to {_short(last['at'])}"]
    placed = left = 0
    for name, (b, t) in last["designs"].items():
        b0 = first["designs"].get(name, [0, t])[0]
        placed += max(0, b - b0)
        left += max(0, t - b)
    lines.append(f"  placed {placed} blocks over {len(hist) - 1} sync interval(s), {left} left")
    per = placed / max(1, len(hist) - 1)
    if per > 0:
        lines.append(f"  ~{per:.0f} blocks a sync -> about {left / per:.0f} more to finish everything")
    else:
        lines.append("  no blocks placed between syncs yet")
    moved = sorted(((last["designs"][n][0] - first["designs"].get(n, [0, 0])[0], n)
                    for n in last["designs"]), reverse=True)
    for delta, name in moved[:top]:
        if delta <= 0:
            continue
        b, t = last["designs"][name]
        lines.append(f"    {os.path.basename(name):28s} +{delta:5d}   {b}/{t}")
    return "\n".join(lines)


def _short(stamp: str) -> str:
    return stamp.replace("T", " ")[:16]
