"""Pixel-diff evidence for approved visual review packets."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def compare(reference: str | Path, candidate: str | Path, *, channel_delta: int = 12) -> dict:
    """Measure changed pixels without declaring that a visual change is necessarily bad."""
    left = np.asarray(Image.open(reference).convert("RGB"), dtype=np.int16)
    right = np.asarray(Image.open(candidate).convert("RGB"), dtype=np.int16)
    if left.shape != right.shape:
        return {"compatible": False, "reason": "different dimensions", "changed_fraction": 1.0}
    delta = np.abs(left - right).max(axis=2)
    changed = delta > int(channel_delta)
    return {"compatible": True, "changed_pixels": int(changed.sum()),
            "changed_fraction": round(float(changed.mean()), 6), "max_channel_delta": int(delta.max())}
