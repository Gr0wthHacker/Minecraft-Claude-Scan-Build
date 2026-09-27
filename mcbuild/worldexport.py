"""Export occupied sparse Skyblock chunks as independently placeable schematic models."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import nbt, scan, schem


def _state(value: str):
    """Parse the portable ``block[prop=value]`` form without losing stairs/doors orientation."""
    if "[" not in value: return nbt.block_state(value)
    if not value.endswith("]"): raise ValueError(f"malformed block state {value!r}")
    name, raw = value[:-1].split("[", 1)
    props = {}
    for pair in raw.split(","):
        if "=" not in pair: raise ValueError(f"malformed block property {pair!r}")
        key, val = pair.split("=", 1); props[key.strip()] = val.strip()
    return nbt.block_state(name.strip(), **props)


def chunk_model(world, chunk: tuple[int, int, int]) -> schem.Model:
    """Make a compact model for one sparse chunk; no empty island-sized bounding box is created."""
    cells = world.iter_chunk(chunk)
    if not cells: raise ValueError(f"chunk {chunk} is empty")
    xs, ys, zs = zip(*(position for position, _state in cells))
    x0, y0, z0 = min(xs), min(ys), min(zs)
    ids = np.zeros((max(ys) - y0 + 1, max(zs) - z0 + 1, max(xs) - x0 + 1), dtype=np.int32)
    palette = [nbt.block_state("minecraft:air")]
    index = {"minecraft:air": 0}
    for (x, y, z), state in cells:
        if state not in index:
            index[state] = len(palette); palette.append(_state(state))
        ids[y - y0, z - z0, x - x0] = index[state]
    model = schem.Model(ids, palette)
    model.world_origin = (x0, y0, z0)
    return model


def export_chunks(world, directory: str | Path, *, prefix: str = "world") -> list[str]:
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for chunk in sorted(world.chunks):
        model = chunk_model(world, chunk)
        suffix = "_".join(map(str, chunk))
        path = directory / f"{prefix}_{suffix}.litematic"
        ox, oy, oz = model.world_origin
        scan.save_pair(str(path), model, {"origin": {"x": ox, "y": oy, "z": oz},
                                          "size": {"x": model.shape_xyz[0], "y": model.shape_xyz[1], "z": model.shape_xyz[2]},
                                          "generated_by": "sparse_world_export"}, name=f"{prefix} {suffix}")
        paths.append(str(path))
    return paths
