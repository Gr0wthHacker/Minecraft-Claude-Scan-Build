"""Low-memory metadata inspection for external Minecraft schematics.

Reference schematics are design evidence, never executable instructions.  This
module reads only their NBT structure, palette names, and region dimensions;
it deliberately skips packed block-state arrays so a city-scale ``.litematic``
can be evaluated without allocating its full voxel volume.
"""
from __future__ import annotations

from dataclasses import dataclass
import gzip
import os
import struct
from typing import BinaryIO

from . import nbt


@dataclass(frozen=True)
class ReferenceRegion:
    """Non-voxel metadata for one litematic region."""

    name: str
    size: tuple[int, int, int] | None
    palette_states: int | None
    entities: int | None
    tile_entities: int | None

    @property
    def envelope_volume(self) -> int | None:
        if self.size is None:
            return None
        x, y, z = self.size
        return abs(x * y * z)


@dataclass(frozen=True)
class ReferenceSummary:
    """Safe, bounded evidence extracted from an external schematic."""

    path: str
    bytes_on_disk: int
    regions: tuple[ReferenceRegion, ...]

    @property
    def envelope_volume(self) -> int:
        return sum(region.envelope_volume or 0 for region in self.regions)


class _Stream:
    def __init__(self, fh: BinaryIO):
        self.fh = fh

    def read_exact(self, amount: int) -> bytes:
        out = self.fh.read(amount)
        if len(out) != amount:
            raise ValueError("truncated NBT stream")
        return out

    def number(self, fmt: str, amount: int) -> int:
        return struct.unpack(fmt, self.read_exact(amount))[0]

    def byte(self) -> int:
        return self.number(">b", 1)

    def integer(self) -> int:
        return self.number(">i", 4)

    def string(self) -> str:
        amount = self.number(">H", 2)
        return self.read_exact(amount).decode("utf-8", errors="replace")

    def discard(self, amount: int) -> None:
        while amount:
            chunk = self.fh.read(min(amount, 1 << 20))
            if not chunk:
                raise ValueError("truncated NBT stream")
            amount -= len(chunk)


def _skip_payload(stream: _Stream, tag_id: int) -> None:
    fixed = {nbt.TAG_BYTE: 1, nbt.TAG_SHORT: 2, nbt.TAG_INT: 4,
             nbt.TAG_LONG: 8, nbt.TAG_FLOAT: 4, nbt.TAG_DOUBLE: 8}
    if tag_id in fixed:
        stream.discard(fixed[tag_id])
    elif tag_id == nbt.TAG_BYTE_ARRAY:
        stream.discard(stream.integer())
    elif tag_id == nbt.TAG_STRING:
        stream.discard(stream.number(">H", 2))
    elif tag_id == nbt.TAG_LIST:
        subtype, count = stream.byte(), stream.integer()
        for _ in range(count):
            _skip_payload(stream, subtype)
    elif tag_id == nbt.TAG_COMPOUND:
        while (child_type := stream.byte()) != nbt.TAG_END:
            stream.string()
            _skip_payload(stream, child_type)
    elif tag_id == nbt.TAG_INT_ARRAY:
        stream.discard(4 * stream.integer())
    elif tag_id == nbt.TAG_LONG_ARRAY:
        stream.discard(8 * stream.integer())
    else:
        raise ValueError(f"unknown NBT tag {tag_id}")


def _read_vec(stream: _Stream) -> tuple[int, int, int] | None:
    values: dict[str, int] = {}
    while (tag_id := stream.byte()) != nbt.TAG_END:
        name = stream.string()
        if tag_id == nbt.TAG_INT and name in {"x", "y", "z"}:
            values[name] = stream.integer()
        else:
            _skip_payload(stream, tag_id)
    return tuple(values[key] for key in ("x", "y", "z")) if len(values) == 3 else None


def _read_region(stream: _Stream, name: str) -> ReferenceRegion:
    size = None
    palette_states = entities = tile_entities = None
    while (tag_id := stream.byte()) != nbt.TAG_END:
        field = stream.string()
        if field == "Size" and tag_id == nbt.TAG_COMPOUND:
            size = _read_vec(stream)
        elif field in {"BlockStatePalette", "Entities", "TileEntities"} and tag_id == nbt.TAG_LIST:
            subtype, count = stream.byte(), stream.integer()
            if field == "BlockStatePalette":
                palette_states = count
            elif field == "Entities":
                entities = count
            else:
                tile_entities = count
            for _ in range(count):
                _skip_payload(stream, subtype)
        else:
            _skip_payload(stream, tag_id)
    return ReferenceRegion(name, size, palette_states, entities, tile_entities)


def inspect_litematic(path: str) -> ReferenceSummary:
    """Read litematic metadata while skipping every packed voxel array.

    This establishes scale and complexity without trusting, executing, or
    importing anything contained in the reference file.
    """
    with open(path, "rb") as raw:
        magic = raw.read(2)
    opener = gzip.open if magic == b"\x1f\x8b" else open
    with opener(path, "rb") as fh:
        stream = _Stream(fh)
        root_type, _root_name = stream.byte(), stream.string()
        if root_type != nbt.TAG_COMPOUND:
            raise ValueError("litematic root must be an NBT compound")
        regions: list[ReferenceRegion] = []
        while (tag_id := stream.byte()) != nbt.TAG_END:
            field = stream.string()
            if field == "Regions" and tag_id == nbt.TAG_COMPOUND:
                while (region_type := stream.byte()) != nbt.TAG_END:
                    region_name = stream.string()
                    if region_type == nbt.TAG_COMPOUND:
                        regions.append(_read_region(stream, region_name))
                    else:
                        _skip_payload(stream, region_type)
            else:
                _skip_payload(stream, tag_id)
    return ReferenceSummary(os.path.abspath(path), os.path.getsize(path), tuple(regions))
