"""Drawing canvas for parametric generators + deterministic hashing."""
from __future__ import annotations

import numpy as np

from ..palette import Registry
from ..schem import Model


def hash01(*args) -> float:
    """Deterministic pseudo-random in [0,1) from integer args."""
    h = 2166136261
    for a in args:
        h ^= (int(a) * 2654435761) & 0xFFFFFFFF
        h = (h * 16777619) & 0xFFFFFFFF
        h ^= h >> 13
    return (h & 0xFFFFFF) / 16777216.0


class Canvas:
    def __init__(self, sx: int, sy: int, sz: int, donors: list | None = None):
        self.sx, self.sy, self.sz = sx, sy, sz
        self.ids = np.zeros((sy, sz, sx), np.int32)
        self.reg = Registry(donors)

    # ---- states -----------------------------------------------------------
    def state(self, name: str, **props) -> int:
        return self.reg.state(name, **props)

    def raw_state(self, name: str, **props) -> int:
        return self.reg.raw(name, **props)

    @property
    def palette(self):
        return self.reg.palette

    # ---- cells ------------------------------------------------------------
    def inb(self, x, y, z) -> bool:
        return 0 <= x < self.sx and 0 <= y < self.sy and 0 <= z < self.sz

    def put(self, x, y, z, blk: int) -> bool:
        x, y, z = int(x), int(y), int(z)
        if self.inb(x, y, z):
            self.ids[y, z, x] = blk
            return True
        return False

    def get(self, x, y, z) -> int:
        x, y, z = int(x), int(y), int(z)
        return int(self.ids[y, z, x]) if self.inb(x, y, z) else -1

    def get_name(self, x, y, z) -> str:
        i = self.get(x, y, z)
        return "OOB" if i < 0 else self.reg.palette[i].value["Name"].value

    # ---- shapes -----------------------------------------------------------
    def sphere(self, cx, cy, cz, r, blk, *, squash=1.0, replace=True, jitter=None):
        for y in range(int(cy - r * squash - 1), int(cy + r * squash + 2)):
            for z in range(int(cz - r - 1), int(cz + r + 2)):
                for x in range(int(cx - r - 1), int(cx + r + 2)):
                    if not self.inb(x, y, z):
                        continue
                    rr = r + (jitter(x, y, z) if jitter else 0.0)
                    d = ((x + 0.5 - cx) ** 2 + ((y + 0.5 - cy) / squash) ** 2 + (z + 0.5 - cz) ** 2) ** 0.5
                    if d <= rr and (replace or self.ids[y, z, x] == 0):
                        self.ids[y, z, x] = blk

    def ellipsoid(self, cx, cy, cz, rx, ry, rz, blk, *, replace=True):
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for z in range(int(cz - rz - 1), int(cz + rz + 2)):
                for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                    if not self.inb(x, y, z):
                        continue
                    d = ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 + ((z + 0.5 - cz) / rz) ** 2
                    if d <= 1.0 and (replace or self.ids[y, z, x] == 0):
                        self.ids[y, z, x] = blk

    def line(self, a, b, r, blk, *, replace=True):
        a, b = np.array(a, float), np.array(b, float)
        n = max(2, int(np.linalg.norm(b - a) * 3))
        for t in np.linspace(0, 1, n):
            p = a + (b - a) * t
            self.sphere(p[0], p[1], p[2], r, blk, replace=replace)

    def bezier(self, pts, r, blk, n=40, *, replace=True):
        pts = [np.array(p, float) for p in pts]
        for t in np.linspace(0, 1, n):
            layer = pts
            while len(layer) > 1:
                layer = [(1 - t) * u + t * v for u, v in zip(layer, layer[1:])]
            p = layer[0]
            self.sphere(p[0], p[1], p[2], r, blk, replace=replace)

    def cylinder_y(self, cx, cz, r, y0, y1, blk, *, hollow_r=None):
        for y in range(int(y0), int(y1) + 1):
            for z in range(self.sz):
                for x in range(self.sx):
                    d = ((x + 0.5 - cx) ** 2 + (z + 0.5 - cz) ** 2) ** 0.5
                    if d <= r and (hollow_r is None or d > hollow_r):
                        self.put(x, y, z, blk)

    # ---- helpers for hangings (used by several generators) ---------------
    def vine(self, x, y, z, facing: str) -> int:
        props = {"east": "false", "north": "false", "south": "false", "west": "false", "up": "false"}
        props[facing] = "true"
        return self.raw_state("vine", **props)

    def hang_string(self, x, ceil_y, z, drop, kind: str, s: dict) -> bool:
        """Chain(s) + lantern from a ceiling block at (x, ceil_y, z)."""
        for i in range(1, drop + 1):
            if self.get(x, ceil_y - i, z) != 0:
                return False
        for i in range(1, drop + 1):
            self.put(x, ceil_y - i, z, s["chain"])
        self.put(x, ceil_y - drop - 1, z, s["soul_h"] if kind == "soul" else s["lant_h"])
        return True

    # ---- export -----------------------------------------------------------
    def to_model(self) -> Model:
        return Model(self.ids.copy(), list(self.reg.palette))
