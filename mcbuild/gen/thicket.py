"""The Lowland Thicket - planting the cave that was only ever quarried.

WHAT THE AUDIT FOUND, and it is the largest single gap on the island. The lowland is described
everywhere in this file as "Minecraft's lush-caves palette - moss, azalea, fern, dripstone".
Measured against the 15:54 scan, the built lowland holds 38 block types and its whole flora is

    moss_block 3986 · dripstone_block 4141 · vine 1098 · moss_carpet 56

and ZERO of everything else - no azalea, no fern, no grass, no dripleaf, no spore blossom, no
cave vines, no lily pad, and, despite 4,141 dripstone BLOCKS, not one pointed dripstone. It is
a cave built out of rock and moss. It is not yet a LUSH cave.

It was never removed, either: the `Lowland` ground design's own cell list contains moss_block
and vine and no other plant, so this is unbuilt work rather than something Jack cleared. The
32,369 vines he purged were vines, and only vines.

THE SITES ARE ABUNDANT, so the design problem is restraint and not room: 11,478 ceiling cells
to hang from, 6,803 walkable floor cells, 617 shallow water columns.

PLANT IN DRIFTS, NEVER IN CONFETTI. This is the deck floor's lesson said in green: that pass
measured 127 vine blobs averaging under two cells and called them noise, and `border_ring: 0`
exists because a third of a line is a dashed scribble. So nothing here is sprinkled by a
per-cell probability. Every plant belongs to a DRIFT with a centre, one dominant species and a
falloff, and the centres are spaced apart - which is also how real vegetation reads, in patches
that thin at their edges rather than as an even dusting.

WHAT EACH SPECIES IS FOR:
  cave vines      the signature, and they carry GLOW BERRIES - light 14, so the hanging
                  gardens light themselves. Kept clustered and moderate on purpose: Jack has
                  just removed 32,369 vines and this must not read as the vines coming back.
  spore blossom   rare and large, and it DRIPS - one of the very few sources of motion this
                  island can have. Placed as moments, far apart, never in a row.
  dripstone       the cave's own texture, and the thing 4,141 dripstone blocks have been
                  promising and never delivering. Stalactites hang and stalagmites rise, both
                  built as real tapers (base-middle-frustum-tip), never as single stubs.
  azalea / fern   the floor, in drifts on moss, with a moss-carpet fringe so a drift fades out
                  instead of ending on a hard edge.
  lily / seagrass the harbor margin, sparse - the pond reads from above, and a covered pond
                  stops being water.

WHAT IT MAY NOT TOUCH: an animal's coat (the night pass's rule - nothing lands on an animal but
lichen), anything `protect` calls a mechanism, the Falls' cut channel and the column its water
falls down, and the masonry FACES of the quarter - plants grow at the feet of a ruin and through
its broken paving, not across the wall you are meant to read.

POINTED DRIPSTONE IS THE ONE PLANT HERE THAT IS NOT PASSABLE, so a stalagmite standing in a
walking cell moves the surface classifier down a course and can open a spawn spot under it.
That is why this design is built BEFORE the night pass, and the night pass is re-solved after.
"""
from __future__ import annotations

from . import protect
from .canvas import Canvas, hash01
from .vertical import Ctx, World

THICKET = {
    "under": None,
    "y_lo": 22,
    "y_hi": 74,
    "seed": 11,

    # floor drifts
    "drifts": 34,
    "drift_min_gap": 8,
    "drift_radius": 3.0,
    "drift_density": 0.62,   # kept for the pavement fuzz; the drift edge is noised on RADIUS
    "pavement_share": 0.055,     # the fuzz through the quarter's broken flagstones

    # hanging
    "vine_clusters": 38,
    "vine_min_gap": 6,
    "vine_spread": 2.2,
    "vine_len": [2, 6],
    "berry_share": 0.45,
    "spore": 12,
    "spore_min_gap": 14,

    # dripstone
    "stalactites": 26,
    "stalagmites": 16,
    "drip_min_gap": 5,
    "drip_spread": 1.8,

    # the water margin
    "lily": 20,
    "seagrass": 64,
    "dripleaf": 14,

    # the Falls: never plant in the channel or the column its water falls down
    "falls_lanes": [-24213, -24212, -24211],
    "falls_z": [29996, 30003],
}

AIRY = ("air", "cave_air", "void_air")
_PASSABLE = set(AIRY) | {"vine", "short_grass", "tall_grass", "fern", "large_fern",
                         "moss_carpet", "azalea", "flowering_azalea", "glow_lichen",
                         "hanging_roots", "dead_bush", "seagrass", "kelp", "kelp_plant",
                         "lily_pad", "cave_vines", "cave_vines_plant", "spore_blossom",
                         "small_dripleaf", "big_dripleaf", "sculk_vein", "tripwire"}
# A PLANT ROOTS IN THE DIRT FAMILY AND NOWHERE ELSE. The first build listed mossy cobble and
# clay here because they look like ground, and the audit returned 173 placement problems -
# fern and grass on mossy_cobblestone, azalea on mossy_stone_bricks. Rule 11 again: ask the
# game, not your eye. Moss carpet is the exception and goes on any solid block, which is what
# lets a drift fade off its soil patch onto the rock around it.
_SOIL = {"moss_block", "dirt", "grass_block", "coarse_dirt", "podzol", "rooted_dirt",
         "mycelium", "mud", "muddy_mangrove_roots"}
_ROCK = _SOIL | {"stone", "cobblestone", "dripstone_block", "deepslate", "andesite",
                 "diorite", "granite", "gravel", "tuff", "calcite"}
_COAT = {c + "_wool" for c in ("white", "orange", "magenta", "light_blue", "yellow", "lime",
                               "pink", "gray", "light_gray", "cyan", "purple", "blue",
                               "brown", "green", "red", "black")} | {"bone_block"}
_MASONRY = {"polished_blackstone_bricks", "chiseled_polished_blackstone", "gilded_blackstone",
            "cracked_polished_blackstone_bricks", "blackstone", "polished_blackstone",
            "deepslate_bricks", "stone_bricks", "mossy_stone_bricks", "cracked_stone_bricks"}

_TAPER = {1: ["tip"], 2: ["frustum", "tip"], 3: ["middle", "frustum", "tip"]}


def _taper(n):
    """Thickness from the ATTACHED end outward. A dripstone that is one `tip` block is a
    spike; a real one narrows, and the sequence is what makes it read as stone rather than
    as a placed decoration."""
    if n in _TAPER:
        return _TAPER[n]
    return ["base"] + ["middle"] * (n - 3) + ["frustum", "tip"]


def build_thicket(cfg: dict, donors=None) -> Canvas:
    p = {**THICKET, **cfg}
    if not p.get("under"):
        raise ValueError("thicket needs params.under")
    ctx = Ctx(p["under"])
    w = World()
    seed = p["seed"]
    ylo, yhi = p["y_lo"], p["y_hi"]
    feats = {k: 0 for k in ("vines", "berries", "spore", "stalactite", "stalagmite",
                            "bush", "fern", "grass", "carpet", "lily", "seagrass",
                            "dripleaf")}
    fl_lanes = set(p["falls_lanes"])
    fz0, fz1 = p["falls_z"]

    def name(x, y, z):
        return ctx.name_at(x, y, z)

    def air(x, y, z):
        return name(x, y, z) in _PASSABLE

    def solid(x, y, z):
        n = name(x, y, z)
        return n not in _PASSABLE and n != "water"

    def empty(x, y, z):
        """PASSABLE IS NOT EMPTY. `air()` answers "can a body or light pass through this",
        which is what headroom needs; it says yes to vine and grass. Used as the test for
        "may I build here" it grew a stalagmite up through two of Jack's vines - the design
        claimed cells the world still fills, the composite kept the vine, and the audit
        correctly reported a spike floating above it. This design never replaces anything:
        it plants in air."""
        return name(x, y, z) in AIRY

    def banned(x, y, z):
        if x in fl_lanes and fz0 <= z <= fz1:
            return True
        n = name(x, y, z)
        return protect.is_protected(n) or n in _COAT

    # ---------------------------------------------------------------- survey
    floor, ceil, wet = [], [], []
    for x in range(-24251, -24148):
        for z in range(29949, 30052):
            for y in range(yhi, ylo - 1, -1):
                if solid(x, y, z) and air(x, y + 1, z) and air(x, y + 2, z):
                    if not banned(x, y, z) and empty(x, y + 1, z):
                        floor.append((x, y + 1, z, name(x, y, z)))
                    break
            for y in range(ylo + 3, yhi):
                if air(x, y, z) and solid(x, y + 1, z) and air(x, y - 1, z) \
                        and air(x, y - 2, z) and air(x, y - 3, z):
                    if not banned(x, y + 1, z) and name(x, y + 1, z) in _ROCK:
                        ceil.append((x, y, z))
                    break
            for y in range(yhi, ylo - 1, -1):
                if name(x, y, z) == "water" and air(x, y + 1, z):
                    # NOT `banned()` here: `is_protected` holds "water" - rightly, because a
                    # generator must never overwrite a fluid - and applying it to the survey
                    # banned every water cell, so the whole margin came out empty in silence.
                    # A waterlogged plant does not remove the water; the BED is what must be
                    # checked, and that is checked at placement.
                    if x not in fl_lanes or not (fz0 <= z <= fz1):
                        # record the SURFACE and the BED separately. Seagrass and dripleaf
                        # root in the bed, and planting them at the surface of a pond two or
                        # three deep meant their support was more water - 44 of 64 seagrass
                        # were silently skipped for having nothing under them.
                        bed = y
                        while bed - 1 >= ylo and name(x, bed - 1, z) == "water":
                            bed -= 1
                        wet.append((x, y, z, bed))
                    break

    def pick(cands, n, gap):
        """Drift centres, spaced apart: shuffle deterministically, then take greedily. This
        is what makes a patch a patch instead of a dusting."""
        order = sorted(cands, key=lambda c: hash01(c[0], c[1], c[2], seed))
        out = []
        for c in order:
            cx, cy, cz = c[0], c[1], c[2]
            if any(abs(cx - a) < gap and abs(cy - b) < gap and abs(cz - d) < gap
                   for a, b, d in out):
                continue
            out.append((cx, cy, cz))
            if len(out) >= n:
                break
        return out

    byxz = {(c[0], c[2]): c for c in floor}

    # ---------------------------------------------------------------- floor drifts
    soil = [c for c in floor if c[3] in _SOIL]
    hard = [c for c in floor if c[3] in _MASONRY]
    for (cx, cy, cz) in pick(soil, p["drifts"], p["drift_min_gap"]):
        r = hash01(cx, cz, seed, 3)
        species = "azalea" if r < 0.30 else "fern" if r < 0.62 else "grass"
        rad = p["drift_radius"] * (0.7 + 0.9 * hash01(cx, cz, seed, 4))
        for dx in range(-4, 5):
            for dz in range(-4, 5):
                c = byxz.get((cx + dx, cz + dz))
                if not c or abs(c[1] - cy) > 2:
                    continue
                x, y, z, fl = c
                if fl not in _SOIL or w.has(x, y, z):
                    continue
                d = (dx * dx + dz * dz) ** 0.5
                if d > rad:
                    continue
                # A DRIFT IS A PATCH WITH A RAGGED EDGE, NOT A DUSTING INSIDE A CIRCLE.
                # Thresholding a per-cell hash against a falloff - the obvious way to write
                # this - produced 191 blobs of which 75% were one or two cells: confetti, by
                # this project's own definition, and exactly what the deck floor pass exists
                # to remove. The noise belongs on the drift's RADIUS, not on its interior, so
                # the middle fills solid and only the boundary wobbles.
                if d > rad * (0.72 + 0.5 * hash01(x, z, seed, 5)):
                    continue
                if d > rad * 0.62:
                    w.put(x, y, z, "moss_carpet")
                    feats["carpet"] += 1
                elif species == "azalea":
                    flow = hash01(x, z, seed, 6) < 0.22
                    w.put(x, y, z, "flowering_azalea" if flow else "azalea")
                    feats["bush"] += 1
                elif species == "fern":
                    # single ferns only: `large_fern` is legal but its upper half stands on
                    # its own lower half, which the learned placement rules have never seen
                    # on this island (there are no large ferns anywhere) and therefore
                    # report as a problem. Not worth a false alarm in every future audit.
                    w.put(x, y, z, "fern")
                    feats["fern"] += 1
                else:
                    w.put(x, y, z, "short_grass")
                    feats["grass"] += 1

    # a thin fuzz through the quarter's broken paving: the ruinway is meant to be decaying,
    # and a fern through a flagstone says so better than another cracked block does
    for (x, y, z, fl) in hard:
        # hashed on a COARSE 2x2 cell, so the moss comes through the paving in small patches
        # rather than as single squares - the same reason the drift edge is noised on radius
        if w.has(x, y, z) or hash01(x // 2, z // 2, seed, 8) > p["pavement_share"] * 2.2:
            continue
        w.put(x, y, z, "moss_carpet")     # carpet sits on anything; a fern cannot
        feats["carpet"] += 1

    # ---------------------------------------------------------------- hanging gardens
    lo, hi = p["vine_len"]
    for (cx, cy, cz) in pick(ceil, p["vine_clusters"], p["vine_min_gap"]):
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                x, z = cx + dx, cz + dz
                d = (dx * dx + dz * dz) ** 0.5
                if d > p["vine_spread"] or hash01(x, cy, z, seed, 10) > 0.72 - 0.18 * d:
                    continue
                if not (solid(x, cy + 1, z) and air(x, cy, z)) or banned(x, cy + 1, z):
                    continue
                n = lo + int(hash01(x, z, seed, 11) * (hi - lo + 1))
                run = []
                for k in range(n):
                    yy = cy - k
                    if yy < ylo or not empty(x, yy, z) or w.has(x, yy, z):
                        break
                    run.append(yy)
                if len(run) < 2:
                    continue
                for k, yy in enumerate(run):
                    berry = hash01(x, yy, z, seed, 12) < p["berry_share"]
                    bs = "true" if berry else "false"
                    if k == len(run) - 1:
                        w.put(x, yy, z, "cave_vines", berries=bs, age="25")
                    else:
                        w.put(x, yy, z, "cave_vines_plant", berries=bs)
                    feats["vines"] += 1
                    feats["berries"] += 1 if berry else 0

    free_ceil = [c for c in ceil if not w.has(c[0], c[1], c[2])]
    for (cx, cy, cz) in pick(free_ceil, p["spore"], p["spore_min_gap"]):
        if w.has(cx, cy, cz) or not solid(cx, cy + 1, cz) or banned(cx, cy + 1, cz):
            continue
        w.put(cx, cy, cz, "spore_blossom")
        feats["spore"] += 1

    # ---------------------------------------------------------------- dripstone
    for (cx, cy, cz) in pick(ceil, p["stalactites"], p["drip_min_gap"]):
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                x, z = cx + dx, cz + dz
                d = (dx * dx + dz * dz) ** 0.5
                if d > p["drip_spread"] or hash01(x, cy, z, seed, 13) > 0.7 - 0.2 * d:
                    continue
                if not (solid(x, cy + 1, z) and air(x, cy, z)) or banned(x, cy + 1, z):
                    continue
                n = 1 + int(hash01(x, z, seed, 14) * 4)
                run = []
                for k in range(n):
                    yy = cy - k
                    if yy < ylo or not empty(x, yy, z) or w.has(x, yy, z):
                        break
                    run.append(yy)
                for th, yy in zip(_taper(len(run)), run):
                    w.put(x, yy, z, "pointed_dripstone", thickness=th,
                          vertical_direction="down", waterlogged="false")
                    feats["stalactite"] += 1

    for (cx, cy, cz) in pick([c for c in floor if c[3] in _ROCK],
                             p["stalagmites"], p["drip_min_gap"]):
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                c = byxz.get((cx + dx, cz + dz))
                if not c or c[3] not in _ROCK or w.has(c[0], c[1], c[2]):
                    continue
                x, y, z, _fl = c
                if hash01(x, y, z, seed, 15) > 0.62:
                    continue
                # the base must stand on real rock, not on the vine or grass that happens to
                # fill the cell under it - one stalagmite grew out of a vine before this
                if not solid(x, y - 1, z):
                    continue
                n = 1 + int(hash01(x, z, seed, 16) * 3)
                run = []
                for k in range(n):
                    yy = y + k
                    if not empty(x, yy, z) or w.has(x, yy, z):
                        break
                    run.append(yy)
                for th, yy in zip(_taper(len(run)), run):
                    w.put(x, yy, z, "pointed_dripstone", thickness=th,
                          vertical_direction="up", waterlogged="false")
                    feats["stalagmite"] += 1

    # ---------------------------------------------------------------- the water margin
    bedof = {(c[0], c[2]): c[3] for c in wet}
    lily_cols = set()
    for (cx, cy, cz) in pick(wet, p["lily"], 3):
        if w.has(cx, cy + 1, cz) or not empty(cx, cy + 1, cz):
            continue
        w.put(cx, cy + 1, cz, "lily_pad")        # lily_pad has NO properties in 26.2
        lily_cols.add((cx, cz))
        feats["lily"] += 1
    # A LILY PAD FLOATS ON WATER, so nothing else may take the cell under it. Where the pond
    # is one deep the bed IS the surface, and seagrass planted there left eight lily pads
    # sitting on seagrass instead of on water.
    for (cx, cy, cz) in pick([c for c in wet
                              if not w.has(c[0], c[3], c[2]) and (c[0], c[2]) not in lily_cols],
                             p["seagrass"], 2):
        by = bedof.get((cx, cz), cy)
        if w.has(cx, by, cz) or not solid(cx, by - 1, cz) or banned(cx, by - 1, cz):
            continue
        w.put(cx, by, cz, "seagrass")
        feats["seagrass"] += 1
    for (cx, cy, cz) in pick([c for c in wet
                              if not w.has(c[0], c[3], c[2]) and (c[0], c[2]) not in lily_cols],
                             p["dripleaf"], 4):
        by = bedof.get((cx, cz), cy)
        if w.has(cx, by, cz) or not solid(cx, by - 1, cz) or banned(cx, by - 1, cz):
            continue
        f = ("north", "east", "south", "west")[int(hash01(cx, by, cz, seed, 17) * 4) % 4]
        w.put(cx, by, cz, "small_dripleaf", facing=f, half="lower", waterlogged="true")
        if not w.has(cx, by + 1, cz) and name(cx, by + 1, cz) in ("water",):
            w.put(cx, by + 1, cz, "small_dripleaf", facing=f, half="upper",
                  waterlogged="true")
        feats["dripleaf"] += 1

    return w.canvas({"kind": "thicket", "profile_view": "top", "facing": [0, 1],
                     "features_built": feats})
