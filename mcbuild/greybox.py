"""Fast, low-detail architectural previews for rejecting bad layouts before full generation."""
from __future__ import annotations

import numpy as np

from . import nbt, schem
from .blueprint import compile as compile_blueprint


def build(brief: dict) -> tuple[schem.Model, dict]:
    """Render a blueprint as floors, shell, roofline mass, and visibly distinct public/service rooms."""
    plan = compile_blueprint(brief); fp = plan["footprint"]
    w, d, h = fp["width"], fp["depth"], fp["floors"] * fp["story_height"]
    palette = [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:light_gray_concrete"),
               nbt.block_state("minecraft:cyan_concrete"), nbt.block_state("minecraft:orange_concrete")]
    ids = np.zeros((max(h, max(plan["facade"]["profile"])) + 2, d, w), dtype=np.int32)
    ids[0, :, :] = 1
    ids[:h + 1, 0, :] = 1; ids[:h + 1, -1, :] = 1; ids[:h + 1, :, 0] = 1; ids[:h + 1, :, -1] = 1
    for room in plan["rooms"]:
        ids[1, room["z"]:room["z"] + room["depth"], 1:w - 1] = 2 if room["access"] == "public" else 3
    for x, roof in enumerate(plan["facade"]["profile"]): ids[h:roof + 1, -1, x] = 1
    return schem.Model(ids, palette), plan
