"""Architectural enrichment: the detail our buildings have never had.

WHY, MEASURED. `tools/corpus.py` compares our designs against 31 builds by other people. On
the two numbers that describe how detailed a building is, we lose badly and consistently:

    architecture     palette (median)   detail % (median)
        theirs              37               17.3
          ours              14               11.4

and building by building it is worse than the median suggests. The Lowland Campanile is 575
cells of 12 block types at **1.4% detail** - a bell tower made of three blackstone variants
stacked. Their comparable watchtower is 45 types at 48.9%. The Sanctum, "the quarter's one
complete building", is nine block types.

THE MISSING VOCABULARY IS SPECIFIC. Per thousand cells, ours against theirs:

    stairs    0.64 vs 4.51     seven times under
    fences    0.07 vs 2.22     thirty times under
    trapdoors 0.00 vs 1.07     we have never placed one
    panes     0.08 vs 0.49

while we OVER-use the chunky families - walls 1.8x, carpet 9.9x, lanterns 3x. That is the
whole diagnosis: we build in full blocks, slabs and walls, and skip the three families that
make a surface read as built. An open trapdoor is the vertical slab Minecraft never shipped;
an upside-down stair is an eave or a corbel; a fence is a railing or a thin column.

AND THE ECONOMY IS NOT THE CONSTRAINT. 350 detail blocks are 1.19-legal and spendable, 38 of
them stone-family ones already sitting in the quarter's own palette. This was self-imposed.

ADDITIVE ONLY. Every one of these buildings is 89-97% BUILT, and the deck floor settled how to
measure a remedial design: its damage is what it REPLACES, not what it places. So this pass
writes into AIR and never over anything standing. It cannot deepen the palette of a wall that
already exists - only of the detail hung on it - and that is the right trade against asking
for hundreds of placed blocks to be broken.

RUNS, NOT CELLS - the one rule that decides whether this reads. The deck soffit drew a coffer
grid per cell and produced 215 runs of which 184 were one or two cells: "it is not a grid, it
is confetti", in the loudest block available. A cornice that appears on scattered cells is the
same mistake with a different block. So every treatment here is applied to a RUN of wall - a
contiguous span at one height with one outward face - and a run shorter than `min_run` gets
nothing at all.

THE FOUR MOVES, each a real architectural element rather than a texture:

    cornice   an upside-down stair in the face cell at a wall's TOP course, tall side against
              the wall, so the top oversails instead of stopping dead
    plinth    the same right way up at the wall's BASE, so the wall meets the ground on a
              splay instead of a butt joint
    sill      a slab under an opening, on the outside
    rail      a fence or wall along a flat top that a person could fall off

An opening's flanks are left for a later pass: a trapdoor shutter is the strongest single move
in the corpus and it wants its own look at the geometry.
"""
from __future__ import annotations

from . import protect
from .canvas import Canvas, hash01
from .vertical import Ctx, World

ENRICH = {
    "under": None,
    "zones": [],            # [{name, box:[x0,y0,z0,x1,y1,z1]}] - measured footprints
    "min_run": 4,           # a run shorter than this gets NOTHING. See the soffit.
    "cornice": True,
    "plinth": True,
    "sill": True,
    "rail": False,          # off by default: a rail on the wrong edge reads as a fence in a field
    "weather": 0.16,        # share of detail cells taking the family's weathered variant
    "see_out": 2,           # a face needs this much open air outward, or nobody can see it
    "seed": 5,
}

AIRY = ("air", "cave_air", "void_air")
_PASSABLE = set(AIRY) | {"vine", "short_grass", "tall_grass", "fern", "large_fern",
                         "moss_carpet", "azalea", "flowering_azalea", "glow_lichen",
                         "hanging_roots", "dead_bush", "snow", "tripwire"}

# masonry we are willing to dress, and what its family offers. Primary stair, primary slab,
# and a weathered alternate so the detail carries a little tone of its own - which is the
# only palette depth an additive pass can add.
FAMILY = {
    "polished_blackstone_bricks": ("polished_blackstone_brick_stairs",
                                   "polished_blackstone_brick_slab", "blackstone_stairs"),
    "cracked_polished_blackstone_bricks": ("polished_blackstone_brick_stairs",
                                           "polished_blackstone_brick_slab", "blackstone_stairs"),
    "chiseled_polished_blackstone": ("polished_blackstone_brick_stairs",
                                     "polished_blackstone_brick_slab", "blackstone_stairs"),
    "gilded_blackstone": ("polished_blackstone_brick_stairs",
                          "polished_blackstone_brick_slab", "blackstone_stairs"),
    "blackstone": ("blackstone_stairs", "blackstone_slab", "polished_blackstone_stairs"),
    "polished_blackstone": ("polished_blackstone_stairs", "polished_blackstone_slab",
                            "blackstone_stairs"),
    "stone_bricks": ("stone_brick_stairs", "stone_brick_slab", "mossy_stone_brick_stairs"),
    "cracked_stone_bricks": ("stone_brick_stairs", "stone_brick_slab",
                             "mossy_stone_brick_stairs"),
    "chiseled_stone_bricks": ("stone_brick_stairs", "stone_brick_slab",
                              "mossy_stone_brick_stairs"),
    "mossy_stone_bricks": ("mossy_stone_brick_stairs", "mossy_stone_brick_slab",
                           "stone_brick_stairs"),
    "cobblestone": ("cobblestone_stairs", "cobblestone_slab", "mossy_cobblestone_stairs"),
    "mossy_cobblestone": ("mossy_cobblestone_stairs", "mossy_cobblestone_slab",
                          "cobblestone_stairs"),
    "deepslate_bricks": ("deepslate_brick_stairs", "deepslate_brick_slab",
                         "cobbled_deepslate_stairs"),
    "cracked_deepslate_bricks": ("deepslate_brick_stairs", "deepslate_brick_slab",
                                 "cobbled_deepslate_stairs"),
    "deepslate_tiles": ("deepslate_tile_stairs", "deepslate_tile_slab",
                        "deepslate_brick_stairs"),
    "polished_deepslate": ("polished_deepslate_stairs", "polished_deepslate_slab",
                           "deepslate_brick_stairs"),
    "smooth_stone": ("stone_brick_stairs", "smooth_stone_slab", "stone_brick_stairs"),
}
_SIDES = ((1, 0), (-1, 0), (0, 1), (0, -1))
# a stair's tall side is its `facing`, per the convention pinned in test_stairhead - so a
# cornice or a plinth faces INTO the wall it grows out of
_FACE = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}


def build_enrich(cfg: dict, donors=None) -> Canvas:
    p = {**ENRICH, **cfg}
    if not p.get("under"):
        raise ValueError("enrich needs params.under")
    if not p.get("zones"):
        raise ValueError("enrich needs params.zones")
    ctx = Ctx(p["under"])
    w = World()
    seed = p["seed"]
    feats = {"cornice": 0, "plinth": 0, "sill": 0, "rail": 0, "runs": 0, "skipped_runs": 0}

    def name(x, y, z):
        return ctx.name_at(x, y, z)

    def empty(x, y, z):
        """Additive only: detail goes into air and never over anything standing."""
        return name(x, y, z) in AIRY

    def airy(x, y, z):
        return name(x, y, z) in _PASSABLE

    def mason(x, y, z):
        return name(x, y, z) in FAMILY

    def free(x, y, z):
        return empty(x, y, z) and not w.has(x, y, z) and not protect.is_protected(name(x, y, z))

    def variant(mat_stair, alt, x, y, z):
        return alt if hash01(x, y, z, seed, 2) < p["weather"] else mat_stair

    def runs_of(cells, axis):
        """Contiguous spans along `axis`, keyed by everything else. RUNS, NOT CELLS."""
        by = {}
        for c in cells:
            key = (c[1], c[3], c[4], c[2] if axis == "x" else c[0])
            by.setdefault(key, []).append(c)
        out = []
        for key, group in by.items():
            group.sort(key=lambda c: c[0] if axis == "x" else c[2])
            span = [group[0]]
            for prev, cur in zip(group, group[1:]):
                a = prev[0] if axis == "x" else prev[2]
                b = cur[0] if axis == "x" else cur[2]
                if b == a + 1:
                    span.append(cur)
                else:
                    out.append(span)
                    span = [cur]
            out.append(span)
        return out

    def emit_runs(cells, kind):
        """cells are (x, y, z, dx, dz): the AIR face cell and the direction of its wall.

        THE GATE MUST RUN ON WHAT WILL ACTUALLY BE PLACED, not on the candidates. Filtering
        after grouping let a five-cell run with two blocked cells ship three scattered stairs
        - the run passed the threshold and the placement did not, which is the soffit's bug
        wearing a different hat. So `free` is applied BEFORE the spans are cut."""
        cells = [c for c in cells if free(c[0], c[1], c[2]) and FAMILY.get(
            name(c[0] + c[3], c[1], c[2] + c[4]))]
        # ...and ONE RECORD PER CELL. An inside corner has masonry on two sides, so it enters
        # as two candidates with two normals; left in, it counted toward a run on BOTH axes
        # while only ever being placed once, and three stairs shipped in runs of one because
        # the other axis' span had been emptied by the first. A cell belongs to one run.
        seen_cell = set()
        uniq = []
        for c in cells:
            if (c[0], c[1], c[2]) in seen_cell:
                continue
            seen_cell.add((c[0], c[1], c[2]))
            uniq.append(c)
        cells = uniq
        placed = 0
        for axis in ("x", "z"):
            for span in runs_of([c for c in cells if (c[4] if axis == "x" else c[3])], axis):
                if len(span) < p["min_run"]:
                    feats["skipped_runs"] += 1
                    continue
                feats["runs"] += 1
                for (x, y, z, dx, dz) in span:
                    if not free(x, y, z):
                        continue
                    m = name(x + dx, y, z + dz)
                    fam = FAMILY.get(m)
                    if not fam:
                        continue
                    stair, slab, alt = fam
                    if kind == "sill":
                        w.put(x, y, z, slab, type="bottom", waterlogged="false")
                    else:
                        w.put(x, y, z, variant(stair, alt, x, y, z),
                              facing=_FACE[(dx, dz)],
                              half="top" if kind == "cornice" else "bottom",
                              shape="straight", waterlogged="false")
                    feats[kind] += 1
                    placed += 1
        return placed

    for zone in p["zones"]:
        x0, y0, z0, x1, y1, z1 = zone["box"]
        tops, bases, sills = [], [], []
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    if not mason(x, y, z):
                        continue
                    top = airy(x, y + 1, z)
                    base = mason(x, y - 1, z) is False and not airy(x, y - 1, z)
                    for dx, dz in _SIDES:
                        fx, fz = x + dx, z + dz
                        if not free(fx, y, fz):
                            continue
                        # it has to be SEEN: a face with one cell of air in front of it is
                        # a crevice, and dressing it hides the detail inside the building
                        if not all(airy(x + dx * k, y, z + dz * k)
                                   for k in range(1, p["see_out"] + 1)):
                            continue
                        rec = (fx, y, fz, -dx, -dz)
                        if top:
                            tops.append(rec)
                        elif base:
                            bases.append(rec)
        # OPENINGS are found in their own sweep, over the wall plane rather than off a face.
        # Looking for masonry above and below a FACE cell asks whether the air OUTSIDE the
        # wall is boxed in, which it never is - that is why the first version emitted no
        # sills at all. A window is a hole IN the wall: air, with masonry over and under it
        # and masonry on two opposite sides. The sill is then a slab in the open air one
        # course below it, projecting - a drip course under the light, not a shelf across it.
        for y in range(y0 + 1, y1):
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    if not airy(x, y, z) or not mason(x, y + 1, z) or not mason(x, y - 1, z):
                        continue
                    for dx, dz in _SIDES:
                        if not (mason(x + dx, y, z + dz) and mason(x - dx, y, z - dz)):
                            continue                      # a jamb either side: a real opening
                        for ox_, oz_ in ((dz, dx), (-dz, -dx)):   # the two ways it faces
                            sx, sz = x + ox_, z + oz_
                            if not free(sx, y - 1, sz) or not mason(x, y - 1, z):
                                continue
                            if not all(airy(x + ox_ * k, y - 1, z + oz_ * k)
                                       for k in range(1, p["see_out"] + 1)):
                                continue
                            sills.append((sx, y - 1, sz, -ox_, -oz_))
        if p["cornice"]:
            emit_runs(tops, "cornice")
        if p["plinth"]:
            emit_runs(bases, "plinth")
        if p["sill"]:
            # NO RUN GATE HERE, and the distinction is the point. The gate exists to stop a
            # COURSE appearing on scattered cells - the soffit's confetti. A sill is not a
            # course: it is anchored to one opening, and an opening on this island is one to
            # three cells wide, so every sill was a run of length 1 and the gate ate all 46
            # of them. What justifies a sill is the window above it, not its length.
            for (x, y, z, dx, dz) in sills:
                if not free(x, y, z):
                    continue
                fam = FAMILY.get(name(x + dx, y, z + dz))
                if not fam:
                    continue
                w.put(x, y, z, fam[1], type="bottom", waterlogged="false")
                feats["sill"] += 1

    if not w.cells:
        raise ValueError("enrich placed nothing - check the zone boxes")
    return w.canvas({"kind": "enrich", "profile_view": "side", "facing": [0, 1],
                     "features_built": feats})
