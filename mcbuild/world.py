"""Sparse, chunk-addressable voxel storage for worlds larger than one schematic."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict


CHUNK = 16


def chunk_of(position: tuple[int, int, int], size: int = CHUNK) -> tuple[int, int, int]:
    x, y, z = map(int, position)
    return x // size, y // size, z // size


class SparseWorld:
    """A deterministic sparse world; unloaded air consumes no dense-volume allocation."""
    def __init__(self, *, chunk_size: int = CHUNK):
        if chunk_size < 1: raise ValueError("chunk_size must be positive")
        self.chunk_size = chunk_size
        self.chunks: dict[tuple[int, int, int], dict[tuple[int, int, int], str]] = defaultdict(dict)

    def put(self, x: int, y: int, z: int, state: str) -> None:
        key = (int(x), int(y), int(z)); chunk = chunk_of(key, self.chunk_size)
        if state in {"air", "minecraft:air", None}:
            self.chunks[chunk].pop(key, None)
            if not self.chunks[chunk]: self.chunks.pop(chunk, None)
        else:
            self.chunks[chunk][key] = str(state)

    def get(self, x: int, y: int, z: int) -> str:
        return self.chunks.get(chunk_of((x, y, z), self.chunk_size), {}).get((x, y, z), "minecraft:air")

    def fill_box(self, lower, upper, state: str) -> int:
        x0, y0, z0 = map(int, lower); x1, y1, z1 = map(int, upper)
        if x1 < x0 or y1 < y0 or z1 < z0: raise ValueError("box upper must not precede lower")
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1): self.put(x, y, z, state)
        return (x1 - x0 + 1) * (y1 - y0 + 1) * (z1 - z0 + 1)

    def iter_chunk(self, chunk):
        return sorted(self.chunks.get(tuple(chunk), {}).items())

    def digest(self, chunk=None) -> str:
        rows = self.iter_chunk(chunk) if chunk is not None else sorted(
            (pos, state) for cells in self.chunks.values() for pos, state in cells.items())
        return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()

    def summary(self) -> dict:
        return {"chunk_size": self.chunk_size, "chunks": len(self.chunks),
                "blocks": sum(len(cells) for cells in self.chunks.values()),
                "chunk_digests": {"/".join(map(str, c)): self.digest(c) for c in sorted(self.chunks)}}
