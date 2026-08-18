"""Read captures made by the chunkscan client mod (`/cscan <name>`).

A capture is a pair in the Litematica schematics folder:
  <name>.litematic   — blocks incl. air, region position (0,0,0)
  <name>.scan.json   — server, dimension, world origin of region [0,0,0], chunk coverage

`load()` gives you the model + sidecar; `cut()` slices a sub-box by WORLD coordinates so you can
capture the whole island once and carve out pieces for design work without losing placement.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from . import schem
from .nbt import Tag, TAG_INT
from .pipeline import DEFAULT_SCHEM_DIR


@dataclass
class Scan:
    model: schem.Model
    meta: dict
    litematic_path: str
    sidecar_path: str

    @property
    def origin(self) -> tuple[int, int, int]:
        o = self.meta["origin"]
        return o["x"], o["y"], o["z"]

    @property
    def size(self) -> tuple[int, int, int]:
        return self.model.shape_xyz


def resolve(name_or_path: str, schem_dir: str = DEFAULT_SCHEM_DIR) -> tuple[str, str]:
    """Return (litematic_path, sidecar_path) for a bare name or either file's path.

    A bare NAME resolves to whichever of `out/` and the schematics folder was written most recently.
    It used to mean the schematics folder only, so anything generated without `--ship` was read back
    as the previous build - which silently produced a stale render three times in one session, and
    once produced a whole set of body measurements for a giraffe that no longer existed.
    """
    p = name_or_path
    if p.endswith(".scan.json"):
        return p[: -len(".scan.json")] + ".litematic", p
    if p.endswith(".litematic"):
        return p, p[: -len(".litematic")] + ".scan.json"
    best, best_mtime = None, -1.0
    for d in ("out", schem_dir):
        lit = os.path.join(d, p + ".litematic")
        if os.path.exists(lit) and os.path.getmtime(lit) > best_mtime:
            best, best_mtime = os.path.join(d, p), os.path.getmtime(lit)
    base = best if best is not None else os.path.join(schem_dir, p)
    return base + ".litematic", base + ".scan.json"


def load(name_or_path: str, schem_dir: str = DEFAULT_SCHEM_DIR) -> Scan:
    lit, side = resolve(name_or_path, schem_dir)
    if not os.path.exists(lit):
        raise FileNotFoundError(lit)
    if not os.path.exists(side):
        raise FileNotFoundError(f"{side} — was this saved with /cscan? plain Litematica saves have no sidecar")
    with open(side, encoding="utf-8") as f:
        meta = json.load(f)
    return Scan(schem.load(lit), meta, lit, side)


def summary(s: Scan) -> str:
    m, meta = s.model, s.meta
    ox, oy, oz = s.origin
    sx, sy, sz = s.size
    srv = meta.get("server", {})
    lines = [
        f"{meta.get('name')}  ({os.path.basename(s.litematic_path)})",
        f"server {srv.get('name', '?')} {srv.get('ip', '')}  dim {meta.get('dimension')}  by {meta.get('player')}  {meta.get('created')}",
        f"origin {ox} {oy} {oz}  ->  {ox + sx - 1} {oy + sy - 1} {oz + sz - 1}   size {sx}x{sy}x{sz}",
        f"blocks {meta.get('non_air_blocks')}  palette {meta.get('palette_size')}  tile entities {meta.get('tile_entities')}",
        f"chunks {len(meta.get('chunks_included', []))} included, radius {meta.get('chunk_radius')}"
        + (", chunk-aligned" if meta.get("chunk_aligned") else ""),
    ]
    missing = meta.get("chunks_missing_in_bounds", [])
    if missing:
        lines.append(f"WARNING {len(missing)} chunks inside the box were not loaded (saved as air): {missing[:12]}"
                     + (" ..." if len(missing) > 12 else ""))
    return "\n".join(lines)


def cut(s: Scan, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int) -> tuple[schem.Model, dict]:
    """Sub-box by world coords (inclusive, any corner order). Returns (model, sidecar) for the cut."""
    ox, oy, oz = s.origin
    sx, sy, sz = s.size
    lx0, lx1 = sorted((x1 - ox, x2 - ox))
    ly0, ly1 = sorted((y1 - oy, y2 - oy))
    lz0, lz1 = sorted((z1 - oz, z2 - oz))
    lx0, ly0, lz0 = max(lx0, 0), max(ly0, 0), max(lz0, 0)
    lx1, ly1, lz1 = min(lx1, sx - 1), min(ly1, sy - 1), min(lz1, sz - 1)
    if lx0 > lx1 or ly0 > ly1 or lz0 > lz1:
        raise ValueError("cut box does not overlap the capture")

    m = s.model.copy()
    m.ids = m.ids[ly0:ly1 + 1, lz0:lz1 + 1, lx0:lx1 + 1].copy()
    m.tile_entities = _shift_tiles(m.tile_entities, lx0, ly0, lz0, lx1, ly1, lz1)
    m.entities = _shift_entities(m.entities, lx0, ly0, lz0, lx1, ly1, lz1)
    m.compact_palette()

    meta = dict(s.meta)
    meta["origin"] = {"x": ox + lx0, "y": oy + ly0, "z": oz + lz0}
    meta["size"] = {"x": lx1 - lx0 + 1, "y": ly1 - ly0 + 1, "z": lz1 - lz0 + 1}
    meta["cut_from"] = os.path.basename(s.litematic_path)
    meta["non_air_blocks"] = int(m.solid().sum())
    meta["palette_size"] = len(m.palette)
    meta["tile_entities"] = len(m.tile_entities)
    for k in ("chunks_included", "chunks_missing_in_bounds", "chunk_radius", "chunk_aligned"):
        meta.pop(k, None)
    return m, meta


def _shift_tiles(tiles: list, x0: int, y0: int, z0: int, x1: int, y1: int, z1: int) -> list:
    out = []
    for t in tiles:
        v = t.value
        x, y, z = v["x"].value, v["y"].value, v["z"].value
        if x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1:
            nv = dict(v)
            nv["x"], nv["y"], nv["z"] = Tag(TAG_INT, x - x0), Tag(TAG_INT, y - y0), Tag(TAG_INT, z - z0)
            out.append(Tag(t.id, nv))
    return out


def _shift_entities(ents: list, x0, y0, z0, x1, y1, z1) -> list:
    """Entity tags carry a relative double Pos; keep those inside the cut and re-base them."""
    out = []
    for e in ents:
        pos = e.value.get("Pos")
        if pos is None or len(pos.value) != 3:
            continue
        x, y, z = (p.value for p in pos.value)
        if x0 <= x < x1 + 1 and y0 <= y < y1 + 1 and z0 <= z < z1 + 1:
            nv = dict(e.value)
            nv["Pos"] = Tag(pos.id, [Tag(pos.value[0].id, x - x0), Tag(pos.value[1].id, y - y0), Tag(pos.value[2].id, z - z0)], subtype=pos.subtype)
            out.append(Tag(e.id, nv))
    return out


def save_pair(path_litematic: str, m: schem.Model, meta: dict, name: str | None = None) -> str:
    """Write <x>.litematic and <x>.scan.json; returns the sidecar path."""
    schem.save(path_litematic, m, name=name)
    side = path_litematic[: -len(".litematic")] + ".scan.json" if path_litematic.endswith(".litematic") else path_litematic + ".scan.json"
    meta = dict(meta)
    meta["file"] = os.path.basename(path_litematic)
    if name:
        meta["name"] = name
    with open(side, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return side


def merge(s: Scan, m: schem.Model, origin: tuple[int, int, int]) -> tuple[schem.Model, int]:
    """Composite model `m` (world origin `origin`) onto the capture. Returns (merged, overlap_count)
    where overlap = cells solid in both. Box = union of both boxes; capture blocks win on overlap."""
    import numpy as np
    ox, oy, oz = s.origin
    mx, my, mz = origin
    csy, csz, csx = s.model.ids.shape
    msy, msz, msx = m.ids.shape
    x0, y0, z0 = min(ox, mx), min(oy, my), min(oz, mz)
    x1 = max(ox + csx, mx + msx); y1 = max(oy + csy, my + msy); z1 = max(oz + csz, mz + msz)
    ids = np.zeros((y1 - y0, z1 - z0, x1 - x0), np.int32)
    off = len(s.model.palette)
    ids[my - y0:my - y0 + msy, mz - z0:mz - z0 + msz, mx - x0:mx - x0 + msx] = np.where(m.ids > 0, m.ids + off, 0)
    cap = ids[oy - y0:oy - y0 + csy, oz - z0:oz - z0 + csz, ox - x0:ox - x0 + csx]
    overlap = int(((cap > 0) & (s.model.ids > 0)).sum())
    ids[oy - y0:oy - y0 + csy, oz - z0:oz - z0 + csz, ox - x0:ox - x0 + csx] = np.where(s.model.ids > 0, s.model.ids, cap)
    merged = schem.Model(ids, list(s.model.palette) + list(m.palette))
    return merged, overlap
