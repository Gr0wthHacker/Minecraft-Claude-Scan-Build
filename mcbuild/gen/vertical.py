"""Vertical additions fitted to a capture: taproot and shed shard.

Every builder takes `under` (capture .litematic with .scan.json) and world coordinates, and returns a
Canvas with `world_origin` set, so the pipeline writes a paste-origin sidecar and can verify in context.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

from .canvas import Canvas, hash01
from .. import schem

ROCK = [("cobblestone", 0.34), ("stone", 0.24), ("mossy_cobblestone", 0.18), ("stone_bricks", 0.10),
        ("mossy_stone_bricks", 0.08), ("cracked_stone_bricks", 0.06)]


# ------------------------------------------------------------------ world buffer

class World:
    """Sparse world-coordinate buffer -> Canvas with world_origin."""

    def __init__(self):
        self.cells: dict[tuple[int, int, int], tuple[str, dict]] = {}

    def put(self, x, y, z, name, **props):
        self.cells[(int(x), int(y), int(z))] = (name, props)

    def has(self, x, y, z):
        return (int(x), int(y), int(z)) in self.cells

    def name(self, x, y, z):
        v = self.cells.get((int(x), int(y), int(z)))
        return v[0] if v else None

    def canvas(self, meta: dict | None = None) -> Canvas:
        if not self.cells:
            raise ValueError("nothing built")
        xs, ys, zs = zip(*self.cells)
        x0, y0, z0 = min(xs), min(ys), min(zs)
        c = Canvas(max(xs) - x0 + 1, max(ys) - y0 + 1, max(zs) - z0 + 1)
        for (x, y, z), (name, props) in self.cells.items():
            c.put(x - x0, y - y0, z - z0, c.raw_state(name, **props))
        c.world_origin = (x0, y0, z0)
        c.meta = meta or {}
        return c


def load_capture(path: str):
    path = resolve_capture(path)
    m = schem.load(path)
    side = path[:-len(".litematic")] + ".scan.json"
    with open(side, encoding="utf-8") as f:
        o = json.load(f)["origin"]
    return m, (int(o["x"]), int(o["y"]), int(o["z"]))


def resolve_capture(path: str) -> str:
    """Let a config name a capture without spelling out a machine path.

    Tried as given first, then relative to the profile's schematics folder. A generator should never
    need an absolute path in its config - that is what profile.yaml is for."""
    if os.path.exists(path):
        return path
    from ..profile import load as load_profile
    cand = os.path.join(load_profile()["schem_dir"], path)
    return cand if os.path.exists(cand) else path


class Ctx:
    """Capture + optional belly, queried in world coordinates.

    `under` may be a LIST, and when it is, later captures WIN where they have content.

    THE GENERATOR MUST ASK THE SAME WORLD THE AUDIT VERIFIES AGAINST. The shop islet asked
    `island_deep` (which reads air at Y150) while `verify_against` used `island_deep` AND
    `island_now` (which holds Jack's cobblestone there). So it planted short_grass on what it
    believed was its own moss - and the moss is never placed, because `ROCK_FAMILY` counts
    cobblestone as satisfying it, so the grass ends up rooted in stone. One design, two worlds,
    two answers: the same drift `proportions` and `rubric` share an entry point to avoid.
    """

    def __init__(self, under, belly: str | None = None):
        extra = []
        if isinstance(under, (list, tuple)):
            under, extra = under[0], list(under[1:])
        self.m, (self.ox, self.oy, self.oz) = load_capture(under)
        self.names = np.array([n.split(":")[-1] for n in self.m.names])
        self.solid = (self.m.ids != 0) & ~np.isin(self.names[self.m.ids], ["vine", "water", "bubble_column"])
        self._extra = []
        for e in extra:
            if os.path.exists(e):
                em, eo = load_capture(e)
                self._extra.append((em, eo, np.array([n.split(":")[-1] for n in em.names])))
        self.b = None
        if belly and os.path.exists(belly):
            self.b, (self.bx, self.by, self.bz) = load_capture(belly)
            self.bsolid = self.b.ids > 0

    def name_at(self, x, y, z) -> str:
        # LATER CAPTURES WIN where they hold something: they are newer, and a stale capture that
        # still reads air is exactly how the islet planted grass on Jack's cobblestone.
        for em, (ex, ey, ez), enames in reversed(getattr(self, "_extra", [])):
            lx, ly, lz = x - ex, y - ey, z - ez
            if 0 <= ly < em.ids.shape[0] and 0 <= lz < em.ids.shape[1] and 0 <= lx < em.ids.shape[2]:
                n = str(enames[em.ids[ly, lz, lx]])
                if n not in ("air", "cave_air", "void_air"):
                    return n
        lx, ly, lz = x - self.ox, y - self.oy, z - self.oz
        if 0 <= ly < self.m.ids.shape[0] and 0 <= lz < self.m.ids.shape[1] and 0 <= lx < self.m.ids.shape[2]:
            return str(self.names[self.m.ids[ly, lz, lx]])
        return "air"

    def occupied(self, x, y, z) -> bool:
        n = self.name_at(x, y, z)
        if n not in ("air", "cave_air", "void_air", "vine"):
            return True
        if self.b is not None:
            lx, ly, lz = x - self.bx, y - self.by, z - self.bz
            if 0 <= ly < self.b.ids.shape[0] and 0 <= lz < self.b.ids.shape[1] and 0 <= lx < self.b.ids.shape[2]:
                return bool(self.bsolid[ly, lz, lx])
        return False

    def belly_bottom(self, x, z):
        if self.b is None:
            return None
        lx, lz = x - self.bx, z - self.bz
        if not (0 <= lz < self.b.ids.shape[1] and 0 <= lx < self.b.ids.shape[2]):
            return None
        col = np.where(self.bsolid[:, lz, lx])[0]
        return int(col.min() + self.by) if col.size else None

    def lowest_solid(self, x, z, max_y=None):
        lx, lz = x - self.ox, z - self.oz
        if not (0 <= lz < self.m.ids.shape[1] and 0 <= lx < self.m.ids.shape[2]):
            return None
        col = np.where(self.solid[:, lz, lx])[0]
        if max_y is not None:
            col = col[col + self.oy <= max_y]
        return int(col.min() + self.oy) if col.size else None


def rock_name(x, y, z, seed):
    h = hash01(x, y, z, 5, seed)
    acc = 0.0
    for name, w in ROCK:
        acc += w
        if h < acc:
            return name
    return ROCK[-1][0]


# ------------------------------------------------------------------ taproot

TAPROOT = {"under": None, "belly": None, "x": None, "z": None, "top_y": None, "length": 40, "strands": 3,
           "top_radius": 4.0, "twist": 2.2, "moss": 0.16, "vine_rate": 0.25, "lanterns": 3, "seed": 0}


def build_taproot(cfg: dict, donors=None) -> Canvas:
    p = {**TAPROOT, **cfg}
    ctx = Ctx(p["under"], p["belly"])
    cx, cz = int(p["x"]), int(p["z"])
    top = p["top_y"] if p["top_y"] is not None else (ctx.belly_bottom(cx, cz) or ctx.lowest_solid(cx, cz)) - 1
    L, seed = int(p["length"]), int(p["seed"])
    w = World()
    for k in range(int(p["strands"])):
        _strand(w, ctx, cx, top, cz, L, k, int(p["strands"]), float(p["top_radius"]), float(p["twist"]), seed)
    _flare(w, ctx, cx, top, cz, float(p["top_radius"]), seed)
    _root_dress(w, ctx, p, cx, top, cz, L, seed)
    return w.canvas({"kind": "taproot", "attach": [cx, top, cz], "tip_y": top - L})


def _strand(w, ctx, cx, top, cz, L, k, n, r0, twist, seed):
    prev = None
    for i in range(L + 1):
        t = i / L
        r = 0.6 + (r0 - 0.6) * (1 - t) ** 0.75
        a = twist * 2 * math.pi * t + 2 * math.pi * k / n + 0.7 * math.sin(3 * t + k)
        x = cx + r * math.cos(a) + 0.35 * math.sin(7 * t + k)
        z = cz + r * math.sin(a) + 0.35 * math.cos(6 * t + 2 * k)
        y = top - i
        cur = (int(round(x)), y, int(round(z)))
        for (px, py, pz) in _bridge(prev, cur):
            if not ctx.occupied(px, py, pz):
                thick = (1 - t) > 0.55 and hash01(px, py, pz, 3, seed) < 0.6
                w.put(px, py, pz, "oak_wood", axis="y")
                if thick:
                    dx, dz = (1, 0) if hash01(px, pz, 9, seed) < 0.5 else (0, 1)
                    if not ctx.occupied(px + dx, py, pz + dz):
                        w.put(px + dx, py, pz + dz, "oak_wood", axis="y")
        prev = cur


def _bridge(a, b):
    """Cells from a to b (inclusive of b), 6-connected steps so strands never break."""
    if a is None:
        return [b]
    out = []
    x, y, z = a
    while (x, y, z) != b:
        if x != b[0]:
            x += 1 if b[0] > x else -1
        elif z != b[2]:
            z += 1 if b[2] > z else -1
        else:
            y += 1 if b[1] > y else -1
        out.append((x, y, z))
    return out


def _flare(w, ctx, cx, top, cz, r0, seed):
    """Root collar under the attach point: a ragged disc that merges the strands into the underside."""
    R = r0 + 1.5
    for dz in range(-int(R) - 1, int(R) + 2):
        for dx in range(-int(R) - 1, int(R) + 2):
            d = math.hypot(dx, dz) + 0.9 * (hash01(dx, dz, 21, seed) - 0.5)
            if d <= R and not ctx.occupied(cx + dx, top, cz + dz):
                w.put(cx + dx, top, cz + dz, "moss_block" if hash01(dx, dz, 23, seed) < 0.45 else "oak_wood", **({} if hash01(dx, dz, 23, seed) < 0.45 else {"axis": "y"}))
            if d <= R - 2 and not ctx.occupied(cx + dx, top - 1, cz + dz):
                w.put(cx + dx, top - 1, cz + dz, "oak_wood", axis="y")


def _root_dress(w, ctx, p, cx, top, cz, L, seed):
    """Moss patches on the wood, vine tufts off the sides, a few lanterns near the tip."""
    wood = [k for k, v in w.cells.items() if v[0] == "oak_wood"]
    for (x, y, z) in wood:
        if hash01(x, y, z, 31, seed) < p["moss"]:
            w.cells[(x, y, z)] = ("moss_block", {})
    DIR = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}
    for (x, y, z) in wood:
        if hash01(x, y, z, 33, seed) >= p["vine_rate"] * 0.25:
            continue
        for dname, (dx, dz) in DIR.items():
            vx, vz = x - dx, z - dz          # vine sits beside the wood, prop points back at it
            if w.has(vx, y, vz) or ctx.occupied(vx, y, vz):
                continue
            ln = 2 + int(hash01(x, y, z, 35, seed) * 4)
            for i in range(ln):
                if w.has(vx, y - i, vz) or ctx.occupied(vx, y - i, vz):
                    break
                w.put(vx, y - i, vz, "vine", **{d: ("true" if d == dname else "false") for d in ("east", "west", "south", "north", "up")})
            break
    tip = top - L
    lows = sorted(wood, key=lambda c: c[1])[:60]
    placed = 0
    for (x, y, z) in lows:
        if placed >= int(p["lanterns"]):
            break
        if hash01(x, y, z, 37, seed) < 0.5 and not w.has(x, y - 1, z) and not w.has(x, y - 2, z):
            w.put(x, y - 1, z, "iron_chain", axis="y", waterlogged="false")
            w.put(x, y - 2, z, "lantern", hanging="true", waterlogged="false")
            placed += 1


# ------------------------------------------------------------------ shed shard

SHARD = {"under": None, "belly": None, "x": None, "z": None, "gap": 22, "rx": 4.0, "ry": 2.5, "rz": 4.0,
         "chains": 3, "seed": 0}


def build_shard(cfg: dict, donors=None) -> Canvas:
    p = {**SHARD, **cfg}
    ctx = Ctx(p["under"], p["belly"])
    cx, cz, seed = int(p["x"]), int(p["z"]), int(p["seed"])
    bb = ctx.belly_bottom(cx, cz)
    if bb is None:
        raise ValueError(f"no belly above ({cx},{cz}) to hang from")
    top = bb - int(p["gap"])
    rx, ry, rz = float(p["rx"]), float(p["ry"]), float(p["rz"])
    w = World()
    cy = top - int(ry)
    for dy in range(-int(ry) - 1, int(ry) + 2):
        for dz in range(-int(rz) - 1, int(rz) + 2):
            for dx in range(-int(rx) - 1, int(rx) + 2):
                d = (dx / rx) ** 2 + (dy / ry) ** 2 + (dz / rz) ** 2
                d += 0.35 * (hash01(dx, dy, dz, 41, seed) - 0.5)
                if d <= 1.0:
                    x, y, z = cx + dx, cy + dy, cz + dz
                    if ctx.occupied(x, y, z):
                        continue
                    topface = (dx / rx) ** 2 + ((dy + 1) / ry) ** 2 + (dz / rz) ** 2 > 1.0
                    w.put(x, y, z, "moss_block" if topface and hash01(dx, dz, 43, seed) < 0.6 else rock_name(x, y, z, seed))
    # solid on purpose: hollowing a 5-layer ellipsoid detaches its caps, and it's ~180 blocks anyway
    _shard_chains(w, ctx, cx, cz, seed, int(p["chains"]))
    return w.canvas({"kind": "shard", "hangs_from_y": bb, "top_y": top})


def _hollow_world(w):
    solid = set(w.cells)
    keep = {}
    for (x, y, z), v in w.cells.items():
        if any((x + dx, y + dy, z + dz) not in solid for dx, dy, dz in
               [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]):
            keep[(x, y, z)] = v
    w.cells = keep


def _shard_chains(w, ctx, cx, cz, seed, n):
    tops = {}
    for (x, y, z) in w.cells:
        if (x, z) not in tops or y > tops[(x, z)]:
            tops[(x, z)] = y
    picks = sorted(tops.items(), key=lambda kv: hash01(kv[0][0], kv[0][1], 47, seed))
    done = 0
    for (x, z), ytop in picks:
        if done >= n:
            continue
        bb = ctx.belly_bottom(x, z)
        if bb is None or bb - 1 <= ytop:
            continue
        for y in range(ytop + 1, bb):
            if ctx.occupied(x, y, z):
                break
            w.put(x, y, z, "iron_chain", axis="y", waterlogged="false")
        done += 1
    # one lantern under the shard
    (x, z), _ = min(tops.items(), key=lambda kv: kv[1])
    ybot = min(y for (xx, y, zz) in w.cells if xx == x and zz == z)
    w.put(x, ybot - 1, z, "iron_chain", axis="y", waterlogged="false")
    w.put(x, ybot - 2, z, "lantern", hanging="true", waterlogged="false")
