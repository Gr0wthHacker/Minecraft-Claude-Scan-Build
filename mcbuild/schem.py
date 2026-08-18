"""Litematica schematic model: load, save, crop, and bit-packing.

A `Model` holds an int32 array `ids` indexed [y, z, x] into `palette`, a
list of block-state Tags. Index 0 is always air. Metadata is carried on
`root` so a loaded file round-trips with its author/timestamps intact; a
fresh model gets a minimal valid root.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from . import nbt
from .nbt import Tag, TAG_COMPOUND, TAG_LIST, TAG_LONG_ARRAY, TAG_INT, TAG_LONG, TAG_STRING

AIR_NAMES = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
DEFAULT_DATA_VERSION = 3955          # 1.21


def bits_for(n: int) -> int:
    return max(2, (n - 1).bit_length())


def unpack(longs, volume: int, bits: int) -> np.ndarray:
    """Decode Litematica's straddling bit-packed block state array."""
    arr = np.array(longs, dtype=np.int64).astype(np.uint64)
    idx = np.arange(volume, dtype=np.uint64)
    b = np.uint64(bits)
    off = idx * b
    start = (off >> np.uint64(6)).astype(np.int64)
    end = (((idx + np.uint64(1)) * b - np.uint64(1)) >> np.uint64(6)).astype(np.int64)
    sb = off & np.uint64(63)
    mask = np.uint64((1 << bits) - 1)
    low = arr[start] >> sb
    hi = np.where(sb == np.uint64(0), np.uint64(0),
                  arr[end] << ((np.uint64(64) - sb) & np.uint64(63)))
    return ((low | hi.astype(np.uint64)) & mask).astype(np.int32)


def pack(values, bits: int) -> list[int]:
    volume = len(values)
    out = [0] * ((volume * bits + 63) // 64)
    mask = (1 << bits) - 1
    for i, v in enumerate(values):
        v = int(v) & mask
        off = i * bits
        li, sb = off >> 6, off & 63
        out[li] |= (v << sb) & 0xFFFFFFFFFFFFFFFF
        if sb + bits > 64:
            out[li + 1] |= v >> (64 - sb)
    return [x - (1 << 64) if x >= (1 << 63) else x for x in out]


@dataclass
class Model:
    ids: np.ndarray                                  # int32 [y, z, x]
    palette: list                                    # list[Tag]
    root: Tag | None = None
    root_name: str = ""
    region_name: str = "Unnamed"
    tile_entities: list = field(default_factory=list)
    entities: list = field(default_factory=list)      # entity Tags with relative Pos (item frames, stands...)

    # ---- basic queries -----------------------------------------------------
    @property
    def names(self) -> list[str]:
        return [nbt.state_name(e) for e in self.palette]

    @property
    def shape_xyz(self) -> tuple[int, int, int]:
        sy, sz, sx = self.ids.shape
        return sx, sy, sz

    def solid(self) -> np.ndarray:
        air = np.array([n in AIR_NAMES for n in self.names])
        return ~air[self.ids]

    def name_at(self, x: int, y: int, z: int) -> str:
        sy, sz, sx = self.ids.shape
        if not (0 <= x < sx and 0 <= y < sy and 0 <= z < sz):
            return "OOB"
        return self.names[self.ids[y, z, x]]

    def props_at(self, x: int, y: int, z: int) -> dict:
        return nbt.state_props(self.palette[self.ids[y, z, x]])

    def index_of(self, name: str, **props) -> int | None:
        key = nbt.state_key(nbt.block_state(name, **props))
        for i, e in enumerate(self.palette):
            if nbt.state_key(e) == key:
                return i
        return None

    def ensure_state(self, name: str, **props) -> int:
        i = self.index_of(name, **props)
        if i is not None:
            return i
        self.palette.append(nbt.block_state(name, **props))
        return len(self.palette) - 1

    # ---- edits -----------------------------------------------------------
    def crop_to_content(self) -> "Model":
        s = self.solid()
        if not s.any():
            return self
        ys, zs, xs = np.where(s)
        self.ids = self.ids[ys.min():ys.max() + 1, zs.min():zs.max() + 1, xs.min():xs.max() + 1]
        return self

    def compact_palette(self) -> "Model":
        used = sorted(set(np.unique(self.ids).tolist()) | {0})
        lut = {o: n for n, o in enumerate(used)}
        self.palette = [self.palette[i] for i in used]
        self.ids = np.vectorize(lut.get)(self.ids).astype(np.int32)
        return self

    def copy(self) -> "Model":
        return Model(self.ids.copy(), list(self.palette), self.root, self.root_name,
                     self.region_name, list(self.tile_entities), list(self.entities))


# ---- io -------------------------------------------------------------------

def load(path: str) -> Model:
    root_name, root = nbt.read(path)
    regions = root.value["Regions"].value
    region_name, reg_tag = next(iter(regions.items()))
    reg = reg_tag.value
    sx = abs(reg["Size"].value["x"].value)
    sy = abs(reg["Size"].value["y"].value)
    sz = abs(reg["Size"].value["z"].value)
    pal = reg["BlockStatePalette"].value
    ids = unpack(reg["BlockStates"].value, sx * sy * sz, bits_for(len(pal))).reshape(sy, sz, sx)
    tes = reg.get("TileEntities")
    ents = reg.get("Entities")
    return Model(ids, list(pal), root, root_name, region_name, list(tes.value) if tes else [],
                 list(ents.value) if ents and ents.value else [])


def new_root(name: str, author: str, data_version: int = DEFAULT_DATA_VERSION) -> Tag:
    now = int(time.time() * 1000)
    return Tag(TAG_COMPOUND, {
        "MinecraftDataVersion": Tag(TAG_INT, data_version),
        "Version": Tag(TAG_INT, 7),
        "SubVersion": Tag(TAG_INT, 1),
        "Metadata": Tag(TAG_COMPOUND, {
            "Name": Tag(TAG_STRING, name),
            "Author": Tag(TAG_STRING, author),
            "Description": Tag(TAG_STRING, ""),
            "TimeCreated": Tag(TAG_LONG, now),
            "TimeModified": Tag(TAG_LONG, now),
            "RegionCount": Tag(TAG_INT, 1),
            "TotalVolume": Tag(TAG_INT, 0),
            "TotalBlocks": Tag(TAG_INT, 0),
            "EnclosingSize": nbt.ivec(0, 0, 0),
        }),
        "Regions": Tag(TAG_COMPOUND, {
            "Unnamed": Tag(TAG_COMPOUND, {
                "Position": nbt.ivec(0, 0, 0),
                "Size": nbt.ivec(0, 0, 0),
                "BlockStatePalette": Tag(TAG_LIST, [], subtype=TAG_COMPOUND),
                "BlockStates": Tag(TAG_LONG_ARRAY, []),
                "TileEntities": Tag(TAG_LIST, [], subtype=TAG_COMPOUND),
                "Entities": Tag(TAG_LIST, [], subtype=0),
                "PendingBlockTicks": Tag(TAG_LIST, [], subtype=0),
                "PendingFluidTicks": Tag(TAG_LIST, [], subtype=0),
            }),
        }),
    })


def save(path: str, m: Model, name: str | None = None, author: str | None = None) -> int:
    """Write model; returns solid block count. Verifies round-trip."""
    if m.root is None:
        m.root = new_root(name or "mcbuild", author or "mcbuild")
        m.region_name = "Unnamed"
    sy, sz, sx = m.ids.shape
    reg = m.root.value["Regions"].value[m.region_name].value
    reg["Position"] = nbt.ivec(0, 0, 0)
    reg["Size"] = nbt.ivec(sx, sy, sz)
    reg["BlockStatePalette"] = Tag(TAG_LIST, m.palette, subtype=TAG_COMPOUND)
    reg["BlockStates"] = Tag(TAG_LONG_ARRAY, pack(m.ids.ravel().tolist(), bits_for(len(m.palette))))
    reg["TileEntities"] = Tag(TAG_LIST, m.tile_entities, subtype=TAG_COMPOUND)
    reg["Entities"] = Tag(TAG_LIST, list(m.entities), subtype=TAG_COMPOUND if m.entities else 0)
    total = int(m.solid().sum())
    md = m.root.value["Metadata"].value
    if name:
        md["Name"] = Tag(TAG_STRING, name)
    if author:
        md["Author"] = Tag(TAG_STRING, author)
    md["EnclosingSize"] = nbt.ivec(sx, sy, sz)
    md["TotalVolume"] = Tag(TAG_INT, sx * sy * sz)
    md["TotalBlocks"] = Tag(TAG_INT, total)
    md["RegionCount"] = Tag(TAG_INT, 1)
    md["TimeModified"] = Tag(TAG_LONG, int(time.time() * 1000))
    nbt.write(path, m.root_name, m.root)
    chk = load(path)
    if not np.array_equal(chk.ids, m.ids):
        raise RuntimeError("round-trip mismatch after save")
    return total
