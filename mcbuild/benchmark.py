"""Small repeatable performance evidence for generation paths."""
from __future__ import annotations

import os
import time


def measure(fn, *args, **kwargs) -> tuple[object, dict]:
    start = time.perf_counter(); result = fn(*args, **kwargs); elapsed = time.perf_counter() - start
    return result, {"seconds": round(elapsed, 6)}


def artifact(path: str) -> dict:
    return {"path": path, "bytes": os.path.getsize(path) if os.path.exists(path) else 0}
