"""Apothecary Farm v4 — octagonal apiary pavilion + stepped crop terrace + honey hall.

Fits the `build-farm-area` footprint (28x15). The footprint's y=1 layer is
the moss surface; below it is a box (6+ deep, same footprint) that we are
allowed to rebuild. Canvas layers:

    y = 0            cellar floor            (file y = -depth+1)
    y = 1..depth-1   cellar interior         (file y = ... 0)
    y = depth        moss surface (copied)   (file y = 1)
    y = depth+1 = B  first build layer above ground

Paste at build-farm-area's origin shifted DOWN by (depth-1) blocks with
replace = "with non-air". Two moss blocks over the stairwell must be
broken by hand (they're air in the schematic).

Surface (x east-west 0..27, z north-south 0..15):
  z=2..3   hedge + lamp posts
  z=4..8   stepped crop terrace, 3 beds x 2 rows, raised channel, festoon lights
  z=9..10  path; double doors into the skep at x=14; arbor at x=18
  west     APIARY PAVILION: 10-wide octagon, stone plinth with campfire
           hearths, timber walls, 6 hives on the cardinal faces, fence windows
           on the diagonals, stair eave + hollow 45-degree stair roof, fenced
           cupola with lanterns; stair down to the honey hall inside
  south    meadow · bench · azalea tree · berries · cistern

Honey hall (underground, x=8..25, z=5..12, 5 tall):
  z=5..7   automated hive bank facing south:
             y=1 plinth · y=2 hopper (west chain -> chest) · y=3 hive
             y=3 observer behind · y=3 block · y=4 dust · y=4 block+dust
             y=4 dispenser (shears) above hive · y=5 dust on top
           any hive changing honey level pulses the whole dust sheet, so
           every dispenser tries to shear; shears fail silently unless full.
  z=8      forage aisle: moss + flowers, hanging lanterns
  z=9      stair from the skep (x=8..13), aisle east of it
  z=10..12 hall: pillars, flower beds, barrels along the south wall
"""
from __future__ import annotations

import math
import os

import numpy as np

from .canvas import Canvas, hash01

DEFAULTS = {
    "footprint": "build-farm-area.litematic",
    "schem_dir": None,                 # None = whatever profile.yaml says; never hard-code a path here
    "surface_y": 1, "surface_block": "moss_block",
    "size": [28, 16],
    "pad_north": 3,                  # rows added north of the footprint for the forecourt + gate
    "depth": 6,                        # cellar rows below the moss (floor + interior)
    "bed_z0": 4, "bed_x": [17, 27], "dividers": [22],
    "corridor_x": [14, 16],          # forecourt -> path, between pavilion and terrace
    "crops": ["wheat", "carrots"],
    "path_z": [9, 10],
    "skep": {"cx": 10.0, "cz": 10.0, "r": 4.5, "corner": 1.4, "wall_h": 3},
    "cistern": {"x": 23, "z": 11},
    "meadow_x": [15, 22], "arbor_x": 18, "tree_at": [20, 13],
    "bee_x": 14, "bee_y": 19, "bee_z": 4,   # head column x, bottom y, north edge z (file coords)
    "cellar": {"x": [7, 26], "z": [4, 13], "hive_x0": 11, "hives": 12, "stair_z": 9},
    "seed": 0,
}


# ------------------------------------------------------------------ states

def _states(c: Canvas) -> dict:
    st, raw = c.state, c.raw_state
    S = {
        "moss": st("moss_block"), "carpet": st("moss_carpet"),
        "cobble": st("cobblestone"), "mosscobble": st("mossy_cobblestone"),
        "brick": st("stone_bricks"), "mossbrick": st("mossy_stone_bricks"), "crackbrick": st("cracked_stone_bricks"),
        "cobble_slab": st("cobblestone_slab", type="bottom", waterlogged="false"),
        "mosscobble_slab": raw("mossy_cobblestone_slab", type="bottom", waterlogged="false"),
        "brick_slab": raw("stone_brick_slab", type="bottom", waterlogged="false"),
        "water": st("water", level="0"), "lily": raw("lily_pad"),
        "slog_y": raw("stripped_spruce_log", axis="y"), "slog_x": raw("stripped_spruce_log", axis="x"),
        "slog_z": raw("stripped_spruce_log", axis="z"),
        "log_y": st("spruce_log", axis="y"), "log_x": st("spruce_log", axis="x"),
        "planks": st("spruce_planks"), "oak": st("oak_planks"), "birch": raw("birch_planks"),
        "sslab": st("spruce_slab", type="bottom", waterlogged="false"),
        "bslab": raw("birch_slab", type="bottom", waterlogged="false"),
        "oslab": st("oak_slab", type="bottom", waterlogged="false"),
        "fence": st("oak_fence", north="false", south="false", east="false", west="false", waterlogged="false"),
        "sfence": st("spruce_fence", north="false", south="false", east="false", west="false", waterlogged="false"),
        "trap": st("spruce_trapdoor", facing="north", half="top", open="false", powered="false", waterlogged="false"),
        "chain": st("chain", axis="y", waterlogged="false"), "chain_x": raw("chain", axis="x", waterlogged="false"),
        "lant_h": st("lantern", hanging="true", waterlogged="false"),
        "farmland": raw("farmland", moisture="7"),
        "wheat": raw("wheat", age="7"), "carrots": raw("carrots", age="7"),
        "potatoes": raw("potatoes", age="7"), "beetroots": raw("beetroots", age="3"),
        "door_l": raw("spruce_door", facing="west", half="lower", hinge="left", open="false", powered="false"),
        "door_l_up": raw("spruce_door", facing="west", half="upper", hinge="left", open="false", powered="false"),
        "door_r": raw("spruce_door", facing="west", half="lower", hinge="right", open="false", powered="false"),
        "door_r_up": raw("spruce_door", facing="west", half="upper", hinge="right", open="false", powered="false"),
        "composter": raw("composter", level="0"), "barrel": st("barrel", facing="up", open="false"),
        "barrel_s": raw("barrel", facing="south", open="false"),
        "chest": raw("chest", facing="south", type="single", waterlogged="false"),
        "craft": raw("crafting_table"),
        "azalea": st("azalea"), "fazalea": st("flowering_azalea"),
        "dandelion": raw("dandelion"), "poppy": raw("poppy"), "daisy": st("oxeye_daisy"),
        "cornflower": raw("cornflower"), "allium": st("allium"), "bluet": raw("azure_bluet"),
        "fern": raw("fern"), "grass": raw("short_grass"),
        "berry": st("sweet_berry_bush", age="3"), "berry2": raw("sweet_berry_bush", age="2"),
        "cobble_wall": st("cobblestone_wall", up="true", north="none", south="none", east="none", west="none", waterlogged="false"),
        "aleaves": raw("azalea_leaves", distance="1", persistent="true", waterlogged="false"),
        "yellow": st("yellow_wool"), "black": st("black_wool"), "white": st("white_wool"),
        "lblue": st("light_blue_wool"), "orange": st("orange_wool"),
        "faleaves": raw("flowering_azalea_leaves", distance="1", persistent="true", waterlogged="false"),
        # honey hall machinery
        "observer_s": raw("observer", facing="south", powered="false"),
        "dispenser_d": raw("dispenser", facing="down", triggered="false"),
        "hopper_w": raw("hopper", facing="west", enabled="true"),
        "dust_x": raw("redstone_wire", east="side", west="side", north="none", south="up", power="0"),
        "dust_xn": raw("redstone_wire", east="side", west="side", north="side", south="none", power="0"),
        "dust_xs": raw("redstone_wire", east="side", west="side", north="none", south="side", power="0"),
    }
    for f in ("north", "south", "east", "west"):
        S["hive_" + f] = raw("beehive", facing=f, honey_level="0")
        S["fire_" + f] = raw("campfire", facing=f, lit="true", signal_fire="false", waterlogged="false")
        S["stairs_" + f] = st("spruce_stairs", facing=f, half="bottom", shape="straight", waterlogged="false")
        S["bstairs_" + f] = raw("stone_brick_stairs", facing=f, half="bottom", shape="straight", waterlogged="false")
        S["mstairs_" + f] = raw("mossy_stone_brick_stairs", facing=f, half="bottom", shape="straight", waterlogged="false")
    S["flowers"] = [S[k] for k in ("dandelion", "poppy", "daisy", "cornflower", "allium", "bluet")]
    return S


def _load_mask(p: dict, SX: int, SZ: int, pad: int = 0) -> np.ndarray:
    mask = np.zeros((SZ, SX), bool)
    fp = p.get("footprint")
    if not fp:
        mask[:] = True
        return mask
    from .. import schem
    from .vertical import resolve_capture
    full = fp if os.path.isabs(fp) else os.path.join(p["schem_dir"], fp) if p.get("schem_dir") else fp
    m = schem.load(resolve_capture(full))
    y = int(p["surface_y"])
    want = p["surface_block"] if ":" in p["surface_block"] else "minecraft:" + p["surface_block"]
    for z in range(min(m.shape_xyz[2], SZ - pad)):
        for x in range(min(m.shape_xyz[0], SX)):
            if m.name_at(x, y, z) == want:
                mask[z + pad, x] = True
    return mask


# ------------------------------------------------------------------ builder

class _Farm:
    def __init__(self, p: dict, donors):
        self.p = p
        pad = int(p.get("pad_north", 0)); self.pad = pad
        SX, SZ = p["size"]; SZ += pad
        p["bed_z0"] += pad; p["path_z"] = [z + pad for z in p["path_z"]]
        p["skep"]["cz"] += pad; p["cistern"]["z"] += pad
        p["tree_at"] = [p["tree_at"][0], p["tree_at"][1] + pad]
        p["cellar"]["z"] = [z + pad for z in p["cellar"]["z"]]; p["cellar"]["stair_z"] += pad
        p["bee_z"] += pad
        self.D = int(p["depth"])           # surface layer index
        self.B = self.D + 1                # first build layer above ground
        self.SY = self.B + 20
        self.c = Canvas(SX, self.SY, SZ, donors)
        self.S = _states(self.c)
        self.mask = _load_mask(p, SX, SZ, pad)
        self.seed = int(p["seed"])
        self.reserved: set[tuple[int, int]] = set()

    # -- helpers ------------------------------------------------------------
    def on(self, x, z) -> bool:
        return 0 <= z < self.mask.shape[0] and 0 <= x < self.mask.shape[1] and bool(self.mask[z, x])

    def put(self, x, y, z, blk):
        self.c.put(x, y, z, blk)

    def ground(self, x, z, blk) -> bool:
        if self.on(x, z) and (x, z) not in self.reserved:
            self.c.put(x, self.B, z, blk)
            return True
        return False

    def h(self, *args) -> float:
        return hash01(*args, self.seed)

    def flower(self, x, z, k) -> int:
        f = self.S["flowers"]
        return f[int(k * len(f)) % len(f)]

    def brickmix(self, *args) -> int:
        k = self.h(*args, 5)
        return self.S["brick"] if k < 0.5 else self.S["mossbrick"] if k < 0.85 else self.S["crackbrick"]

    def lamp_post(self, x, z, y0, arm_dz):
        S, c = self.S, self.c
        top = y0 + 2
        for y in range(y0, top):
            c.put(x, y, z, S["fence"])
        c.put(x, top, z, S["oslab"]); c.put(x, top, z + arm_dz, S["oslab"])
        c.put(x, top - 1, z + arm_dz, S["lant_h"])

    def stair_ring(self, x0, x1, z0, z1, y, kind="stairs"):
        S = self.S
        for z in range(z0, z1 + 1):
            for x in range(x0, x1 + 1):
                if x in (x0, x1) or z in (z0, z1):
                    f = "south" if z == z0 else "north" if z == z1 else "east" if x == x0 else "west"
                    self.put(x, y, z, S[f"{kind}_{f}"])

    # -- surface copy ---------------------------------------------------------
    def surface(self):
        for z in range(self.mask.shape[0]):
            for x in range(self.mask.shape[1]):
                if self.mask[z, x]:
                    self.put(x, self.D, z, self.S["moss"])

    # -- crop terrace -----------------------------------------------------------
    def beds(self):
        p, S, B = self.p, self.S, self.B
        z0 = int(p["bed_z0"]); xa, xb = p["bed_x"]
        z_rail, z_water, z_hi, z_lo, z_front = z0, z0 + 1, z0 + 2, z0 + 3, z0 + 4
        posts = [xa] + list(p["dividers"]) + [xb]
        for x in range(xa, xb + 1):
            if not self.on(x, z_rail):
                continue
            self.put(x, B, z_rail, S["mossbrick"] if self.h(x, 41) < 0.6 else S["mosscobble"])
            self.put(x, B + 1, z_rail, S["log_y"] if x in posts else S["slog_x"])
            self.put(x, B, z_water, S["log_y"] if x in (xa, xb) else S["mossbrick"])
            self.put(x, B + 1, z_water, S["slog_z"] if x in (xa, xb) else S["water"])
            if x in posts:
                self.put(x, B, z_hi, S["log_y"]); self.put(x, B + 1, z_hi, S["log_y"])
                self.put(x, B, z_lo, S["log_y"])
            else:
                self.put(x, B, z_hi, S["slog_x"]); self.put(x, B + 1, z_hi, S["farmland"])
                self.put(x, B, z_lo, S["farmland"])
            self.put(x, B, z_front, S["log_y"] if x in posts else S["slog_x"])
        for i, (e0, e1) in enumerate(zip(posts, posts[1:])):
            crop = S[p["crops"][i % len(p["crops"])]]
            for x in range(e0 + 1, e1):
                self.put(x, B + 2, z_hi, crop); self.put(x, B + 1, z_lo, crop)
        for x in posts:
            if x != int(p["arbor_x"]) and self.on(x, z_front):
                self.lamp_post(x, z_front, B + 1, +1)
        ax = int(p["arbor_x"])
        for x in range(posts[0] + 1, posts[-1]):
            if x in posts or x == ax:
                continue
            self.put(x, B + 3, z_front, S["chain_x"])
            if (x - posts[0]) % 5 in (2, 3):
                self.put(x, B + 2, z_front, S["lant_h"])

    # -- path + arbor -----------------------------------------------------------
    def path(self):
        S, B = self.S, self.B
        sk = self.p["skep"]; cx, cz, R = sk["cx"], sk["cz"], sk["r"]
        for z in self.p["path_z"]:
            for x in range(self.mask.shape[1]):
                if not self.on(x, z):
                    continue
                dx, dz = abs(x + 0.5 - cx), abs(z + 0.5 - cz)
                if dx <= R and dz <= R and x < cx:
                    continue                                   # west half of the pavilion interior stays moss
                k = self.h(x, z, 101)
                self.put(x, B, z, S["cobble_slab"] if k < 0.38 else S["mosscobble_slab"] if k < 0.68
                         else S["brick_slab"] if k < 0.82 else S["carpet"])

    def arbor(self):
        S, B, p = self.S, self.B, self.p
        x = int(p["arbor_x"]); zf1 = int(p["bed_z0"]) + 4; zs = p["path_z"][-1] + 1
        for y in range(B + 1, B + 4):
            self.put(x, y, zf1, S["fence"])
        for y in range(B, B + 4):
            self.put(x, y, zs, S["fence"])
        for z in range(zf1, zs + 1):
            self.put(x, B + 4, z, S["sslab"])
        for z in p["path_z"]:
            self.put(x - 1, B + 4, z, S["trap"]); self.put(x + 1, B + 4, z, S["trap"])
        self.put(x, B + 3, p["path_z"][0], S["lant_h"])
        self.put(x, B + 3, p["path_z"][1], self.c.vine(x, B + 3, p["path_z"][1], "up"))

    # -- octagonal apiary pavilion --------------------------------------------
    def _oct(self, r):
        """Cells inside the octagon of half-width r; perimeter = cells with a 4-neighbour outside."""
        sk = self.p["skep"]; cx, cz, k = sk["cx"], sk["cz"], sk["corner"]

        def inside(x, z):
            dx, dz = abs(x + 0.5 - cx), abs(z + 0.5 - cz)
            return dx <= r and dz <= r and dx + dz <= r * k
        cells, perim = [], []
        for z in range(-1, self.mask.shape[0] + 1):
            for x in range(-1, self.mask.shape[1] + 1):
                if inside(x, z):
                    cells.append((x, z))
                    if any(not inside(x + dx, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        perim.append((x, z))
        return cells, perim

    def _dxdz(self, x, z):
        sk = self.p["skep"]
        return x + 0.5 - sk["cx"], z + 0.5 - sk["cz"]

    def _face(self, x, z):
        dx, dz = self._dxdz(x, z)
        return ("east" if dx > 0 else "west") if abs(dx) >= abs(dz) else ("south" if dz > 0 else "north")

    def _oct_ring(self, r, y, kind):
        for x, z in self._oct(r)[1]:
            self.put(x, y, z, self.S[f"{kind}_{self._face(x, z)}"] if kind else self.S["planks"])

    def _oct_roof_row(self, r, y):
        """Stairs on the perimeter of r, planks everywhere inside r except the
        deep interior of r-1 (keeps the roof hollow AND sealed at the diagonals)."""
        inside, perim = self._oct(r)
        inner, iperim = self._oct(r - 1)
        deep = set(inner) - set(iperim)
        for x, z in inside:
            if (x, z) in perim:
                self.put(x, y, z, self.S["stairs_" + self._face(x, z)])
            elif (x, z) not in deep:
                self.put(x, y, z, self.S["planks"])

    def skep(self):
        S, B, c = self.S, self.B, self.c
        sk = self.p["skep"]; R, WH = sk["r"], int(sk["wall_h"])
        _, perim = self._oct(R)
        ad = lambda x, z: sorted((abs(self._dxdz(x, z)[0]), abs(self._dxdz(x, z)[1])))
        posts = [(x, z) for x, z in perim if ad(x, z) == [1.5, R]]
        hives = [(x, z) for x, z in perim if ad(x, z) == [0.5, R] and self._dxdz(x, z)[0] < R - 1]
        wins = [(x, z) for x, z in perim if 1.5 < abs(self._dxdz(x, z)[0]) < R and 1.5 < abs(self._dxdz(x, z)[1]) < R]
        for x, z in perim:                                          # plinth + walls
            self.put(x, B, z, S["mossbrick"] if self.h(x, z, 71) < 0.7 else S["brick"])
            f = self._face(x, z)
            for y in range(B + 1, B + WH + 1):
                if (x, z) in posts:
                    blk = S["slog_y"]
                elif y == B + 1:
                    blk = S["slog_x"] if f in ("north", "south") else S["slog_z"]
                elif y == B + WH:
                    blk = S["oak"]
                else:
                    blk = S["planks"]
                self.put(x, y, z, blk)
            self.put(x, B + WH + 1, z, S["slog_x"] if f in ("north", "south") else S["slog_z"])   # top plate
        for x, z in hives:                                          # hives over hearths
            f = self._face(x, z)
            self.put(x, B + 2, z, S["hive_" + f]); self.put(x, B, z, S["fire_" + f])
            ox, oz = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}[f]
            self.ground(x + ox, z + oz, S["fazalea"]); self.reserved.add((x + ox, z + oz))
        for x, z in wins:
            self.put(x, B + 2, z, S["fence"])
        self._skep_roof()
        self._skep_door()
        self._skep_interior()
        self._skep_skirt(perim, posts)
        for x, z in perim:                                          # vines on the north wall, never over a hive front
            if self._face(x, z) == "north" and (x, z) not in hives and self.h(x, z, 73) < 0.4:
                for y in range(B + 3, B + 1, -1):
                    if c.get(x, y, z - 1) == 0:
                        self.put(x, y, z - 1, c.vine(x, y, z - 1, "south"))

    def _skep_roof(self):
        S, B = self.S, self.B
        sk = self.p["skep"]; R, WH = sk["r"], int(sk["wall_h"]); cx, cz = sk["cx"], sk["cz"]
        y0 = B + WH + 1                                             # top-plate row
        self._oct_ring(R + 1, y0, "stairs")                         # eave, one out from the wall
        r, y = R, y0 + 1
        while r >= 2.5:                                             # hollow 45-degree roof
            self._oct_roof_row(r, y)
            r -= 1; y += 1
        cx0, cz0 = int(cx - 2), int(cz - 2)                         # 4x4 cap that carries the cupola
        for x in range(cx0, cx0 + 4):
            for z in range(cz0, cz0 + 4):
                edge = x in (cx0, cx0 + 3) or z in (cz0, cz0 + 3)
                self.put(x, y, z, S["stairs_" + self._face(x, z)] if edge else S["planks"])
        for yy in (y + 1, y + 2):                                   # cupola: posts + fence sides
            for x in range(cx0, cx0 + 4):
                for z in range(cz0, cz0 + 4):
                    corner = x in (cx0, cx0 + 3) and z in (cz0, cz0 + 3)
                    edge = x in (cx0, cx0 + 3) or z in (cz0, cz0 + 3)
                    if corner:
                        self.put(x, yy, z, S["slog_y"])
                    elif edge:
                        self.put(x, yy, z, S["sfence"])
        for x in range(cx0, cx0 + 4):                               # cap + crown
            for z in range(cz0, cz0 + 4):
                edge = x in (cx0, cx0 + 3) or z in (cz0, cz0 + 3)
                self.put(x, y + 3, z, S["stairs_" + self._face(x, z)] if edge else S["planks"])
        for x in (cx0 + 1, cx0 + 2):
            for z in (cz0 + 1, cz0 + 2):
                self.put(x, y + 4, z, S["sslab"])
        self.put(cx0 + 1, y + 2, cz0 + 1, S["lant_h"]); self.put(cx0 + 2, y + 2, cz0 + 2, S["lant_h"])
        for x, z in ((int(cx - 0.5), int(cz - R - 1)), (int(cx + 0.5), int(cz + R + 1)),      # eave lanterns N/S/W
                     (int(cx - R - 1), int(cz - 0.5)), (int(cx - R - 1), int(cz + 0.5))):
            self.put(x, y0 - 1, z, S["lant_h"])

    def _skep_skirt(self, perim, posts):
        """Stone-brick stair skirt round the plinth (grounds the building) and a
        hanging lantern under the eave outside every corner post."""
        S, B = self.S, self.B
        inside = set(self._oct(self.p["skep"]["r"])[0])
        for x, z in perim:
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ox, oz = x + dx, z + dz
                if (ox, oz) in inside or not self.on(ox, oz) or self.c.get(ox, B, oz) != 0:
                    continue
                if (ox, oz) in self.reserved:
                    continue
                # high side against the wall: facing = direction from the skirt cell toward the wall
                f = {(1, 0): "west", (-1, 0): "east", (0, 1): "north", (0, -1): "south"}[(dx, dz)]
                self.put(ox, B, oz, S["mstairs_" + f] if self.h(ox, oz, 111) < 0.6 else S["bstairs_" + f])
                self.reserved.add((ox, oz))
        WH = int(self.p["skep"]["wall_h"]); y0 = B + WH + 1
        for x, z in posts:                                          # eave lanterns outside each post
            dx, dz = self._dxdz(x, z)
            ox, oz = (x + (1 if dx > 0 else -1), z) if abs(dx) > abs(dz) else (x, z + (1 if dz > 0 else -1))
            if self.c.get(ox, y0, oz) != 0 and self.c.get(ox, y0 - 1, oz) == 0:
                self.put(ox, y0 - 1, oz, S["lant_h"])

    # vanilla bee.png body faces (7w x 7h x 10d), classified: Y yellow, K dark, O orange belly, B eye
    BEE_TEX = {
        "FRONT": ["YYYYYYY", "YKYYYKY", "OYYYYYO", "KBYYYBK", "KKYYYKK", "KKYYYKK", "OOOYOOO"],
        "WEST": ["KKYKYKYYYY", "KKYKYKYYYY", "KKYKYKYYYO", "KKOKYKYYYK", "KKOKYKYYYK", "KKOKOKOYYK", "KKKKOKOOOO"],   # front at col 9
        "EAST": ["YYYYKYKYKK", "YYYYKYKYKK", "OYYYKYKYKK", "KYYYKYKOKK", "KYYYKYKOKK", "KYYOKOKKKK", "OOOOKKKKKK"],   # front at col 0
        "TOP": ["KKKKKKK", "KKKKKKK", "YYYYYYY", "KKKKKKK", "YYYYYYY", "KKKKKKK", "YYYYYYY", "YYYYYYY", "YYYYYYY", "YYYYYYY"],   # row 9 = front
        "BOTTOM": ["KKKKKKK", "KKKKKKK", "KKKKKKK", "KKKKKKK", "KKKKKKK", "KKKKKKK", "OOKKKOO", "OOKKKOO", "OOOOOOO", "OOOOOOO"],
    }

    def bee(self):
        """The vanilla bee, voxelised from its actual texture and scaled to
        11 long x 8 wide x 7 tall, flying west toward the pavilion. Plain box
        like the mob; each surface cell samples the matching face of bee.png."""
        S, c = self.S, self.c
        hx, y0, z0 = int(self.p["bee_x"]), int(self.p["bee_y"]), int(self.p["bee_z"])
        L, W, H = 11, 8, 7
        T = self.BEE_TEX
        col = {"Y": S["yellow"], "K": S["black"], "O": S["orange"], "B": S["lblue"]}
        for i in range(L):
            d = int(i * 9 / (L - 1) + 0.5)                     # 0 = front .. 9 = tail
            for j in range(H):
                v = H - 1 - j                                  # texture row, 0 = top
                for k in range(W):
                    u = int(k * 6 / (W - 1) + 0.5)             # 0..6 across the width
                    if i == 0:
                        ch = T["FRONT"][v][u]
                    elif i == L - 1:
                        ch = "K"
                    elif j == H - 1:
                        ch = T["TOP"][9 - d][u]
                    elif j == 0:
                        ch = T["BOTTOM"][9 - d][u]
                    elif k == 0:
                        ch = T["WEST"][v][9 - d]
                    elif k == W - 1:
                        ch = T["EAST"][v][d]
                    else:
                        ch = "Y"
                    self.put(hx + i, y0 + j, z0 + k, col[ch])
        wy = y0 + H - 1                                        # wings: swept back off the shoulders
        for rows in ((z0, z0 - 1, z0 - 2, z0 - 3), (z0 + W - 1, z0 + W, z0 + W + 1, z0 + W + 2)):
            for r, (i0, i1) in enumerate(((2, 5), (3, 6), (3, 5), (4, 5))):
                for i in range(i0, i1 + 1):
                    if c.get(hx + i, wy, rows[r]) == 0:
                        self.put(hx + i, wy, rows[r], S["white"])
        for i in (2, 4, 6):                                    # legs
            for k in (1, W - 2):
                self.put(hx + i, y0 - 1, z0 + k, S["sfence"])
        for k in (1, W - 2):                                   # antennae at the black roots on the face
            self.put(hx + 1, y0 + H, z0 + k, S["sfence"])
        for k in (W // 2 - 1, W // 2):                         # stinger
            self.put(hx + L, y0 + H // 2, z0 + k, S["black"])

    def _skep_door(self):
        S, B, sk = self.S, self.B, self.p["skep"]
        x = int(sk["cx"] + sk["r"] - 0.5)
        z0, z1 = int(sk["cz"] - 0.5), int(sk["cz"] + 0.5)
        self.put(x, B, z0, S["door_l"]); self.put(x, B + 1, z0, S["door_l_up"])
        self.put(x, B, z1, S["door_r"]); self.put(x, B + 1, z1, S["door_r_up"])
        self.door_x = x

    def _skep_interior(self):
        S, B, c = self.S, self.B, self.c
        sk = self.p["skep"]; cx, cz, R = sk["cx"], sk["cz"], sk["r"]
        for x, z in ((int(cx - 0.5), int(cz - 0.5)), (int(cx + 0.5), int(cz + 0.5))):
            y = B + 1
            while y < self.SY and c.get(x, y, z) == 0:              # first ceiling block above the floor
                y += 1
            self.put(x, y - 1, z, S["chain"]); self.put(x, y - 2, z, S["chain"]); self.put(x, y - 3, z, S["lant_h"])
        wx = int(cx - 2.5)
        for z, blk in ((int(cz - 1.5), S["barrel"]), (int(cz - 0.5), S["craft"]),
                       (int(cz + 0.5), S["barrel"]), (int(cz + 1.5), S["composter"])):
            self.ground(wx, z, blk); self.reserved.add((wx, z))
        self.put(wx, B + 1, int(cz - 1.5), S["barrel"])
        inside, perim = self._oct(R)
        for x, z in inside:
            if (x, z) not in perim:
                self.reserved.add((x, z))
                d = math.hypot(x + 0.5 - cx, z + 0.5 - cz)
                if 2.4 < d < 3.6 and c.get(x, B, z) == 0 and self.on(x, z) and self.h(x, z, 79) < 0.5:
                    self.put(x, B, z, S["carpet"])

    # -- cistern / tree / meadow / hedge / fringes --------------------------------
    def cistern(self):
        S, B = self.S, self.B
        cs = self.p["cistern"]; x0, z0 = int(cs["x"]), int(cs["z"]); x1, z1 = x0 + 3, z0 + 3
        for z in range(z0, z1 + 1):
            for x in range(x0, x1 + 1):
                ring = x in (x0, x1) or z in (z0, z1)
                for y in (B, B + 1):
                    self.put(x, y, z, self.brickmix(x, y, z) if ring else S["water"])
                if not ring:
                    self.put(x, B - 1, z, S["mossbrick"])
        for x, z in ((x0, z0), (x1, z0), (x0, z1), (x1, z1)):
            self.put(x, B + 2, z, S["cobble_wall"])
            for y in (B + 3, B + 4):
                self.put(x, y, z, S["sfence"])
        self.put(x0 + 2, B + 2, z0 + 1, S["lily"])
        ry = B + 5
        for z in range(z0, z1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, ry, z, S["planks"])
        self.stair_ring(x0 - 1, x1 + 1, z0 - 1, z1 + 1, ry)
        self.stair_ring(x0, x1, z0, z1, ry + 1)
        for x in (x0 + 1, x0 + 2):
            for z in (z0 + 1, z0 + 2):
                self.put(x, ry + 1, z, S["planks"]); self.put(x, ry + 2, z, S["sslab"])
        for x, z in ((x0 + 1, z0 + 1), (x0 + 2, z0 + 2)):
            self.put(x, ry - 1, z, S["chain"]); self.put(x, ry - 2, z, S["lant_h"])
        for x, z in ((x0 - 1, z0 - 1), (x1 + 1, z0 - 1), (x0 - 1, z1 + 1), (x1 + 1, z1 + 1)):
            self.put(x, ry - 1, z, S["lant_h"])
        c = self.c
        for z in (z0 + 1, z0 + 2):
            for y in (B + 1, B):
                if self.h(x1 + 1, y, z, 47) < 0.7:
                    self.put(x1 + 1, y, z, c.vine(x1 + 1, y, z, "west"))
        for x in (x0 + 1, x0 + 2):
            self.put(x, B + 1, z1 + 1, c.vine(x, B + 1, z1 + 1, "north"))
        self.put(x0 + 1, B + 2, z0, S["carpet"]); self.put(x1, B + 2, z0 + 2, S["carpet"])

    def tree(self):
        S, B, c = self.S, self.B, self.c
        tx, tz = self.p["tree_at"]
        if not self.on(tx, tz):
            return
        for y in range(B, B + 4):
            self.put(tx, y, tz, S["log_y"])
        self.put(tx + 1, B + 3, tz, S["log_x"]); self.put(tx, B + 3, tz - 1, S["log_y"])
        cy = B + 4.5
        jit = lambda x, y, z: 0.6 * (self.h(x, y, z, 53) - 0.5)
        c.sphere(tx + 0.5, cy, tz + 0.5, 2.6, S["aleaves"], squash=0.7, replace=False, jitter=jit)
        c.sphere(tx + 1.2, cy + 1.2, tz - 0.3, 1.6, S["aleaves"], squash=0.8, replace=False, jitter=jit)
        for y in range(B + 2, B + 8):
            for z in range(tz - 3, tz + 4):
                for x in range(tx - 3, tx + 4):
                    if c.get(x, y, z) == S["aleaves"] and self.h(x, y, z, 59) < 0.35:
                        self.put(x, y, z, S["faleaves"])
        for x, z in ((tx - 2, tz), (tx, tz + 2), (tx - 1, tz - 2)):
            if c.get(x, B + 3, z) in (S["aleaves"], S["faleaves"]) and c.get(x, B + 2, z) == 0:
                self.put(x, B + 2, z, S["lant_h"])
                break

    def meadow(self):
        S, B = self.S, self.B
        xa, xb = self.p["meadow_x"]
        z0 = self.p["path_z"][-1] + 1
        ax = int(self.p["arbor_x"]); tx, tz = self.p["tree_at"]
        for z in (z0, z0 + 1):
            for x in range(xa, xb + 1):
                if x == ax and z == z0:
                    continue
                k = self.h(x, z, 11); j = self.h(x, z, 13)
                if k < 0.62:
                    self.ground(x, z, self.flower(x, z, j))
                elif k < 0.72 and z == z0 + 1:
                    self.ground(x, z, S["azalea"] if j < 0.6 else S["fazalea"])
                elif k < 0.85:
                    self.ground(x, z, S["carpet"])
        bx = xa + 6
        if self.on(bx, z0 + 1) and (bx, z0 + 1) != (tx, tz):
            self.ground(bx, z0 + 1, S["mosscobble"]); self.put(bx, B + 1, z0 + 1, S["cobble_slab"])
        zb = z0 + 2
        self.ground(xa, zb, S["log_y"]); self.ground(xa + 3, zb, S["log_y"])
        for x in range(xa, xa + 4):
            self.put(x, B + 1, zb, S["log_x"])
        for x in range(xa + 4, xb + 1):
            if (x, zb) != (tx, tz) and self.h(x, zb, 61) < 0.6:
                self.ground(x, zb, self.flower(x, zb, self.h(x, zb, 63)))
        for x in range(xa - 1, xb + 1):
            k = self.h(x, zb + 1, 19)
            self.ground(x, zb + 1, S["berry"] if k < 0.55 else S["berry2"] if k < 0.7 else
                        S["azalea"] if k < 0.85 else S["fern"])

    def entrance(self):
        """North forecourt: a 10x5 stone deck built 3 blocks out past the island
        edge (over the box rim), gate with pillars + log beam + pitched roof +
        lanterns, railings, lamp posts, slab path straight through to a 3-wide
        corridor between the pavilion and the terrace."""
        S, B, D = self.S, self.B, self.D
        z0 = int(self.p["bed_z0"]); cx0, cx1 = self.p["corridor_x"]
        xs = [x for x in range(self.mask.shape[1]) if self.on(x, z0 - 1) and x < 17]
        xa, xb = xs[0], xs[-1]                                       # forecourt width = the bump (x=7..16)
        z_gate, z_land = z0 - 5, z0 - 1                              # deck rows z_gate..z_land

        def slab(x, z):
            k = self.h(x, z, 131)
            return S["brick_slab"] if k < 0.4 else S["mosscobble_slab"] if k < 0.7 else S["cobble_slab"] if k < 0.9 else S["carpet"]
        for z in range(z_gate, z_land + 1):
            for x in range(xa, xb + 1):
                if not self.on(x, z):                                # deck where there is no moss
                    self.put(x, D, z, self.brickmix(x, D, z))
                    if z <= z_gate + 1:
                        self.put(x, D - 1, z, self.brickmix(x, D - 1, z))
                self.reserved.add((x, z))
                edge = x in (xa, xb) or z == z_gate
                self.put(x, B, z, S["cobble_wall"] if edge else slab(x, z))
        for z in range(z0, self.p["path_z"][0]):                    # corridor
            for x in range(cx0, cx1 + 1):
                if self.on(x, z):
                    self.put(x, B, z, slab(x, z)); self.reserved.add((x, z))
        # gate: pillars, beam, pitched roof, lanterns; opening 4 wide in the middle
        gx0, gx1 = xa + 2, xb - 2
        for x in range(gx0 + 1, gx1):
            self.put(x, B, z_gate, slab(x, z_gate))
        for x in (gx0, gx1):
            for y in range(B, B + 5):
                self.put(x, y, z_gate, self.brickmix(x, y, z_gate) if y < B + 4 else S["cobble_wall"])
        for x in range(gx0, gx1 + 1):
            self.put(x, B + 5, z_gate, S["slog_x"])
        for x in range(gx0 - 1, gx1 + 2):
            self.put(x, B + 6, z_gate - 1, S["stairs_south"]); self.put(x, B + 6, z_gate + 1, S["stairs_north"])
            self.put(x, B + 6, z_gate, S["planks"]); self.put(x, B + 7, z_gate, S["sslab"])
        for x in (gx0 + 1, gx1 - 1):
            self.put(x, B + 4, z_gate, S["lant_h"])
        for x in (xa, xb):                                           # lamp posts at the inner corners
            self.put(x, B, z_land, S["fence"]); self.lamp_post(x, z_land, B + 1, +1)
        for x, z in ((gx0 - 1, z_gate + 1), (gx1 + 1, z_gate + 1)):  # planters flanking the gate inside
            self.put(x, D, z, S["moss"])
            self.put(x, B, z, S["fazalea"] if self.h(x, z, 137) < 0.5 else S["azalea"])
        # hedge along the pavilion's north wall, west of the corridor
        for x in range(0, cx0):
            if self.on(x, z0) and (x, z0) not in self.reserved and self.c.get(x, B, z0) == 0:
                k = self.h(x, z0, 23)
                self.ground(x, z0, S["berry"] if k < 0.4 else S["azalea"] if k < 0.65 else S["fazalea"] if k < 0.85 else S["fern"])

    def fringes(self):
        S, B = self.S, self.B
        pz = self.p["path_z"]
        xb = self.p["bed_x"][1] + 1; z0 = int(self.p["bed_z0"])
        self.ground(xb, z0 + 1, S["composter"]); self.ground(xb, z0 + 2, S["barrel"])
        self.put(xb, B + 1, z0 + 2, S["barrel"]); self.ground(xb, z0 + 3, S["barrel"])
        if self.ground(self.mask.shape[1] - 1, pz[0] - 1, S["mosscobble"]):
            self.put(self.mask.shape[1] - 1, B + 1, pz[0] - 1, S["mosscobble_slab"])
        for z in range(z0, self.mask.shape[0]):
            for x in range(self.mask.shape[1]):
                if not self.on(x, z) or (x, z) in self.reserved or self.c.get(x, B, z) != 0:
                    continue
                k = self.h(x, z, 31); j = self.h(x, z, 37)
                if k < 0.34:
                    self.ground(x, z, self.flower(x, z, j))
                elif k < 0.48:
                    self.ground(x, z, S["carpet"])
                elif k < 0.55:
                    self.ground(x, z, S["azalea"])

    # -- honey hall (underground) ----------------------------------------------
    def cellar_shell(self):
        S, D = self.S, self.D
        cl = self.p["cellar"]; (x0, x1), (z0, z1) = cl["x"], cl["z"]
        corners = ((x0, z0), (x1, z0), (x0, z1), (x1, z1))
        for z in range(z0, z1 + 1):
            for x in range(x0, x1 + 1):
                k = self.h(x, z, 83)
                self.put(x, 0, z, S["brick"] if k < 0.45 else S["mossbrick"] if k < 0.75 else
                         S["crackbrick"] if k < 0.85 else S["cobble"])
                if x in (x0, x1) or z in (z0, z1):
                    pil = ((x - x0) % 5 == 0 or (z - z0) % 4 == 0) and (x, z) not in corners
                    for y in range(1, D):
                        self.put(x, y, z, S["slog_y"] if pil else self.brickmix(x, y, z))
        self.cellar_garden()

    def cellar_garden(self):
        """Forage aisle in front of the hives + flower beds in the hall; the bees need it."""
        S, D = self.S, self.D
        cl = self.p["cellar"]; (x0, x1), (z0, z1) = cl["x"], cl["z"]
        sz = int(cl["stair_z"])
        aisle = z0 + 4
        for x in range(x0 + 1, x1):
            self.put(x, 0, aisle, S["moss"])
            k = self.h(x, aisle, 89)
            if k < 0.45:
                self.put(x, 1, aisle, self.flower(x, aisle, self.h(x, aisle, 91)))
            elif k < 0.55:
                self.put(x, 1, aisle, S["fazalea"])
            elif k < 0.7:
                self.put(x, 1, aisle, S["carpet"])
            if x % 3 == 0:
                self.put(x, D - 1, aisle, S["lant_h"])          # hangs from the moss ceiling
        for bx0 in (x0 + 8, x0 + 14):                          # hall flower beds
            for z in (sz + 1, sz + 2):
                for x in range(bx0, bx0 + 4):
                    self.put(x, 0, z, S["moss"])
                    k = self.h(x, z, 93)
                    self.put(x, 1, z, S["fazalea"] if k < 0.25 else
                             self.flower(x, z, self.h(x, z, 95)) if k < 0.8 else S["carpet"])
        for x in (x0 + 6, x0 + 12, x0 + 18):                  # pillars + lantern chains
            for y in range(1, D):
                self.put(x, y, sz + 1, S["slog_y"])
            self.put(x, D - 1, sz + 3, S["chain"]); self.put(x, D - 2, sz + 3, S["lant_h"])
        for x in range(x0 + 2, x1 - 1):                        # barrels along the south wall
            if self.h(x, 97) < 0.6:
                self.put(x, 1, z1 - 1, S["barrel_s"])
                if self.h(x, 99) < 0.5:
                    self.put(x, 2, z1 - 1, S["barrel_s"])

    def cellar_hives(self):
        """Automated hive bank along the north wall, facing south. See module doc."""
        S = self.S
        cl = self.p["cellar"]; (x0, x1), (z0, z1) = cl["x"], cl["z"]
        hx0, n = int(cl["hive_x0"]), int(cl["hives"])
        zh = z0 + 3
        for i in range(n):
            x = hx0 + i
            self.put(x, 1, zh, S["brick"])
            self.put(x, 2, zh, S["hopper_w"])
            self.put(x, 3, zh, S["hive_south"])
            self.put(x, 4, zh, S["dispenser_d"])
            self.put(x, 5, zh, S["dust_xn"])
            self.put(x, 3, zh - 1, S["observer_s"])
            self.put(x, 4, zh - 1, S["brick"]); self.put(x, 5, zh - 1, S["dust_xs"])
            self.put(x, 3, zh - 2, S["brick"])
            self.put(x, 4, zh - 2, S["dust_x"])
        self.put(hx0 - 1, 2, zh, S["chest"]); self.put(hx0 - 1, 1, zh, S["brick"])
        for x in list(range(x0 + 1, hx0 - 1)) + list(range(hx0 + n, x1)):
            for y in (1, 2, 3):
                self.put(x, y, zh, S["barrel_s"] if self.h(x, y, 103) < 0.7 else S["brick"])
        for x in range(x0 + 1, x1):                            # solid backing behind the machinery
            for z in (zh - 1, zh - 2):
                for y in range(1, self.D):
                    if self.c.get(x, y, z) == 0 and not (hx0 <= x < hx0 + n and y >= 3):
                        self.put(x, y, z, self.brickmix(x, y, z))

    def stair(self):
        """From just inside the skep doors down to the hall floor, descending west."""
        S, D = self.S, self.D
        z = int(self.p["cellar"]["stair_z"])
        x, y = self.door_x - 1, D
        while y >= 1:
            self.put(x, y, z, S["bstairs_west"])
            for yy in (y + 1, y + 2):
                self.put(x, yy, z, 0)                          # headroom; also opens the moss / path
            if self.c.get(x, D, z) == 0:
                self.put(x, self.B, z, 0)                      # no slab floating over a hole
            for yy in range(1, y):
                self.put(x, yy, z, self.brickmix(x, yy, z))
            x -= 1; y -= 1
        self.put(x + 1, D - 1, z, S["lant_h"])                 # landing lantern from the ceiling

    def build(self) -> Canvas:
        self.surface()
        self.cellar_shell(); self.cellar_hives()
        self.beds(); self.path(); self.arbor()
        self.entrance()
        self.skep(); self.stair()
        self.cistern(); self.meadow(); self.tree(); self.fringes()
        self.bee()
        return self.c


def build(cfg: dict, donors=None) -> Canvas:
    p = {**DEFAULTS, **cfg}
    for k in ("skep", "cistern", "cellar"):
        p[k] = {**DEFAULTS[k], **(cfg.get(k) or {})}
    return _Farm(p, donors).build()
