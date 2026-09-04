"""Drawing canvas for parametric generators + deterministic hashing."""
from __future__ import annotations

import json

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
        # TILE ENTITIES, which every layer below this could already carry and nothing above it
        # could produce. The writer emits them, the pipeline shifts them when a design is padded -
        # and a Canvas had no way to make one, so this project has never placed a sign in a year of
        # building. A room with no sign is a room nobody can be told the rules in.
        self.tiles: dict = {}

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

    def solid(self, x, y, z) -> bool:
        """Is there a real block here? USE THIS, not `if c.get(...)`.

        `get` returns -1 out of bounds so `get_name` can report OOB - and -1 is TRUTHY, so every
        `if c.get(x, y, z):` in a generator silently treats everything outside the canvas as solid
        rock. That is not a hypothetical: the ladybird's spots searched downward for the top of its
        shell from two courses above the canvas ceiling, "found" a block there every time, and
        painted all seven caps into thin air above the bug. The shell came out plain red and
        nothing in the audit, the BOM or the component count said a word.
        """
        return self.get(x, y, z) > 0

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
    def sign_text(self, x, y, z, front=(), back=(), colour="black", glowing=False) -> None:
        """Record the TEXT of a sign already placed at this cell.

        The BLOCK and its TEXT are separate things - `put` places an oak_wall_sign, this says what
        it reads - because the block is a palette entry and the text is a tile entity, and they
        live in different halves of the file.

        26.x nests the lines under `front_text`/`back_text` with a `messages` list of JSON strings,
        four of them ALWAYS: a sign with two lines still stores four, and a shorter list is a sign
        the game refuses to load. That is why the lines are padded here rather than at the caller.
        """
        def side(lines):
            out = [json.dumps({"text": str(t)}) for t in list(lines)[:4]]
            out += ['{"text":""}'] * (4 - len(out))
            return out
        self.tiles[(int(x), int(y), int(z))] = {
            "front": side(front), "back": side(back),
            "colour": colour, "glowing": bool(glowing)}

    def _tile_tags(self, ox=0, oy=0, oz=0) -> list:
        from ..nbt import Tag, TAG_COMPOUND, TAG_INT, TAG_STRING, TAG_LIST, TAG_BYTE
        out = []
        for (x, y, z), t in sorted(self.tiles.items()):
            def txt(key):
                return Tag(TAG_COMPOUND, {
                    "messages": Tag(TAG_LIST, [Tag(TAG_STRING, m) for m in t[key]],
                                    subtype=TAG_STRING),
                    "color": Tag(TAG_STRING, t["colour"]),
                    "has_glowing_text": Tag(TAG_BYTE, 1 if t["glowing"] else 0),
                })
            out.append(Tag(TAG_COMPOUND, {
                "id": Tag(TAG_STRING, "minecraft:sign"),
                "x": Tag(TAG_INT, int(x) + ox),
                "y": Tag(TAG_INT, int(y) + oy),
                "z": Tag(TAG_INT, int(z) + oz),
                "is_waxed": Tag(TAG_BYTE, 0),
                "front_text": txt("front"),
                "back_text": txt("back"),
            }))
            if getattr(self, "legacy_signs", False):
                # Java 1.19 reads Text1..4, Color and GlowingText. Keep the
                # modern fields too for previews in a newer client.
                out[-1].value.update({f"Text{i+1}": Tag(TAG_STRING, message)
                                      for i, message in enumerate(t["front"])})
                out[-1].value["Color"] = Tag(TAG_STRING, t["colour"])
                out[-1].value["GlowingText"] = Tag(TAG_BYTE, int(t["glowing"]))
        return out

    def to_model(self) -> Model:
        return Model(self.ids.copy(), list(self.reg.palette),
                     tile_entities=self._tile_tags())
