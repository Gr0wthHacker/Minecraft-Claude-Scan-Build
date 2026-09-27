"""The Falls - the island's water, made legible from the plate to the harbor.

THE PHENOMENON WAS ALREADY THERE, AND IT WAS AN ACCIDENT. Measured off the 15:54 scan: the
plate's pond (Y202/203, X-24205..-24193 / Z30002..30010) drains through a surface stream that
runs north-west along X-24209 at Y203, steps down to Y202 at Z29992, and at Z29991 runs out of
island and pours over the rim - ONE column of water falling 107 courses, Y202 down to Y96,
where it lands in the void isle's pond. It is the only long fall on the island and nothing
about it reads as intended: no lip, no basin, no outlet, just water leaving over moss.

So this design does not build a waterfall. IT BUILDS THE THINGS THAT LET WATER FALL, and lets
Minecraft do the rest - which is also why it is cheap. Three works:

  THE HEAD    the outfall on the plate rim: cheek piers either side of the mouth and a dressed
              sill, so the stream leaves the island through a made opening
  THE CISTERN the isle is the middle basin. A channel is CUT at pond level from the pond's
              south shore across the isle's rim, opening into a spill apron
  THE TAIL    a notch cut clean through the isle's thin south shelf, where the water leaves
              and falls ~60 courses into the lowland harbor at Y37

WHY THE SECOND FALL IS WORTH CUTTING. The three levels of this island - plate, void, lowland -
have never had one element that crosses all of them; the descent is a stair you walk and the
belly is scenery you pass. Water is the one thing that can join them because the eye follows
it down. The chain then explains the harbor: the lowland's water arrives from the island above
it, rather than simply being there.

FOUR MEASUREMENTS DECIDED THE SITE, none of them guessable:

1. The isle's pond is FULLY ENCLOSED - 132 cells at Y99 and not one edge cell has a clear drop
   beneath it, so there is no place the cistern spills by itself. It has to be cut.
2. The isle's south rim is a thin SHELF: rock at Y96-99 with open void below Y95. That is four
   courses to cut through rather than the ten the pond's own bed would have needed, and it is
   why the tail leaves from the rim and not from under the pond.
3. The axolotl lies along the harbor's west bank (X-24246..-24221), so the fall must land east
   of it - every candidate west of X-24216 drops within 5 blocks of the animal.
4. The Lowland Stair screws down at (-24200, 30018). At X-24212 the fall is ~13 blocks from it:
   far enough not to crowd the helix, close enough that you descend the last turns beside it.

HYDRAULICS, AND THE ONE THING THAT WOULD HAVE MADE IT DECORATIVE. Flowing water dies seven
blocks from its source, and the cut channel is seven long - exactly the distance at which the
flow would have arrived at the lip as nothing. So the channel bed carries WATER SOURCES, placed
cell by cell, and the last of them stands at the apron. A source is infinite in Minecraft, so
the pond is not drained and the fall does not stop.

THE CHANNEL IS A DIG AND A LITEMATIC CANNOT EXPRESS REMOVAL, so every rock cell over the
channel bed and every cell of the notch goes to the sidecar's `dig` list, which is what
`/cscan dig` reads. Cut the notch LAST: it is the plug, and pulling it before the channel is
dressed floods the trench you are still standing in.
"""
from __future__ import annotations

from . import protect
from .canvas import Canvas, hash01
from .vertical import Ctx, World

FALLS = {
    "under": None,

    # --- the head, on the plate rim -------------------------------------------------
    "head": True,
    "head_axis_x": -24209,        # the stream's column, measured
    "head_lip_z": 29992,          # last cell with a bed under it; it falls from lip_z - 1
    "head_pier": "stone_bricks",
    "head_sill": "stone_bricks",
    "head_courses": 2,            # how tall the cheek piers stand above the water

    # --- the cistern channel, cut across the isle's south rim ------------------------
    "cistern": True,
    "water_y": 99,                # the isle pond's surface, measured
    "lanes": [-24213, -24212, -24211],
    "channel_from_z": 29997,      # first cut cell (the pond's shore is the cell before)
    "apron_from_z": 30000,        # ...where the one-lane run opens to the full width
    "apron_to_z": 30001,          # the channel opens into an apron ending here
    "notch_z": 30002,             # cut clean through the shelf here; the water leaves
    "notch_depth": 4,             # courses of shelf to take out under the water course
    "open_above": 2,              # courses cleared over the water so it is a trench, not a culvert
    "kerb": "mossy_stone_bricks",  # the isle's own dressed stone
    "kerb_alt": "stone_bricks",
    "bed": "stone_bricks",        # laid only where the cut leaves no floor
    "weather": 0.3,
    "seed": 0,
}

AIRY = ("air", "cave_air", "void_air")
# vine and grass are NOT rock: the rim-stair lesson, and reading them as footing built a
# flight of twelve floating treads once.
_PASSABLE = set(AIRY) | {"vine", "short_grass", "tall_grass", "fern", "large_fern",
                         "moss_carpet", "azalea", "flowering_azalea", "glow_lichen",
                         "hanging_roots", "dead_bush", "seagrass", "kelp", "kelp_plant"}


def build_falls(cfg: dict, donors=None) -> Canvas:
    p = {**FALLS, **cfg}
    if not p.get("under"):
        raise ValueError("falls needs params.under")
    ctx = Ctx(p["under"])
    w = World()
    dig: list[tuple[int, int, int]] = []
    feats = {"head": 0, "kerb": 0, "bed": 0, "water": 0, "notch": 0}

    def name(x, y, z):
        return ctx.name_at(x, y, z)

    def is_air(x, y, z):
        return name(x, y, z) in _PASSABLE

    def solid(x, y, z):
        return not is_air(x, y, z) and name(x, y, z) != "water"

    def cut(x, y, z):
        """Record a removal. Never take a mechanism, and never take water - the pond above
        this channel is the thing being tapped, not something to drain."""
        n = name(x, y, z)
        if n in _PASSABLE or n == "water":
            return False
        if protect.is_protected(n):
            raise ValueError(f"the cut at {(x, y, z)} would take {n}, which is protected")
        dig.append((x, y, z))
        return True

    # ---------------------------------------------------------------- THE HEAD
    if p["head"]:
        ax, lip = p["head_axis_x"], p["head_lip_z"]
        # the sill: the bed the water crosses on its last cell of island, dressed
        sy = None
        for y in range(p.get("water_y_head", 202), 190, -1):
            if solid(ax, y, lip):
                sy = y
                break
        if sy is None:
            raise ValueError("the head has no bed under its lip - resite it")
        for dx in (-1, 0, 1):
            if solid(ax + dx, sy, lip):
                w.put(ax + dx, sy, lip, p["head_sill"])
                feats["head"] += 1
        # cheek piers: they flank the mouth and project one cell past the lip, so the water
        # leaves BETWEEN two stones instead of over an eroded edge
        for dx in (-1, 1):
            for dz in (0, -1):
                for c in range(p["head_courses"]):
                    x, y, z = ax + dx, sy + 1 + c, lip + dz
                    if not is_air(x, y, z):
                        continue
                    if not (solid(x, y - 1, z) or w.has(x, y - 1, z)):
                        continue
                    w.put(x, y, z, p["head_pier"] if hash01(x, y, z, p["seed"]) > p["weather"]
                          else p["kerb"])
                    feats["head"] += 1

    # ---------------------------------------------------------------- THE CISTERN
    if p["cistern"]:
        wy = p["water_y"]
        z0, z1, nz = p["channel_from_z"], p["apron_to_z"], p["notch_z"]
        lanes = list(p["lanes"])
        mid = lanes[len(lanes) // 2]

        def wet(z):
            """The lanes carrying water at this z: one for the run, the full width once the
            channel opens into the apron. A 60-course fall one block wide is a thread nobody
            sees from the lowland floor, so the tail leaves three wide - and for that the
            water has to arrive already spread, which is what the apron is for."""
            return lanes if z >= p["apron_from_z"] else [mid]

        for z in range(z0, z1 + 1):
            for x in wet(z):
                cut(x, wy, z)                                  # the water course itself
                for c in range(1, p["open_above"] + 1):        # a trench, not a culvert
                    cut(x, wy + c, z)
                if not solid(x, wy - 1, z):                    # a bed only where there is none
                    w.put(x, wy - 1, z, p["bed"])
                    feats["bed"] += 1
                w.put(x, wy, z, "water", level="0")             # sources: 7 blocks is not enough
                feats["water"] += 1

        # The trench has to HOLD the water it carries. Cut through rock it does, but the cut
        # runs out to the isle's rim where the rock thins, and a missing side wall does not
        # read as a leak in a render - it reads as a channel that quietly empties over the
        # edge somewhere it was never meant to.
        for z in range(z0, z1 + 1):
            lane = wet(z)
            for x in (lane[0] - 1, lane[-1] + 1):
                if solid(x, wy, z):
                    w.put(x, wy, z, p["kerb"] if hash01(x, wy, z, p["seed"]) > p["weather"]
                          else p["kerb_alt"])
                    feats["kerb"] += 1
                else:
                    w.put(x, wy, z, p["kerb"])                 # wall it, or the channel leaks
                    feats["kerb"] += 1
                if not solid(x, wy - 1, z) and not w.has(x, wy - 1, z):
                    w.put(x, wy - 1, z, p["bed"])
                    feats["bed"] += 1

        # ------------------------------------------------------------ THE TAIL
        # The lip: the course the water actually pours over. Left as found it is the isle's own
        # broken rock, and the whole work then ends in the one place it is being looked at with
        # the least care on it - so the last bed row is dressed whether or not it needed a bed.
        for x in lanes:
            w.put(x, wy - 1, z1, p["bed"])
            feats["bed"] += 1

        # the notch: take the shelf out from under the water course so the cistern spills into
        # open air. Cut this LAST in game - it is the plug.
        for x in lanes:
            for c in range(p["notch_depth"]):
                if cut(x, wy - c, nz):
                    feats["notch"] += 1
            for c in range(1, p["open_above"] + 1):
                cut(x, wy + c, nz)

    return w.canvas({"kind": "falls", "profile_view": "side", "facing": [0, 1],
                     "features_built": feats, "dig": [list(d) for d in dig]})
