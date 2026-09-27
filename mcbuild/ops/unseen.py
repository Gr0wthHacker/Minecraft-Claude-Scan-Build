"""Take out of a design every block NOBODY CAN SEE, and nothing else.

`hollow.hollow` carves a sculpture to a shell of a stated thickness: it knows the model is one
closed volume, it erodes from the outside, and it raises if the result leaks. That contract does
not fit a park. A composite is not one volume - it is a plate over the void, a mountain cut through
by a coaster, twenty buildings, a lake and four dinosaurs - and there is no single erosion depth
that is right for all of it.

So the question is asked per cell, and it is LOCAL: **are all six of this block's neighbours opaque
full cubes?** If they are, nothing anywhere can see any face of it and it may go. If one of them is
air, or glass, or a slab, then somebody standing in that neighbour is looking at this block.

## THE MISTAKE THAT SHIPPED A BROKEN PARK, because it is the whole reason this file reads as it does

The first version asked a grander question - *can the OUTSIDE see this block* - by flooding from
outside the bounding box through everything you can see through, and keeping whatever that flood
touched. It is a beautiful invariant and it is WRONG, because a park is full of air the outside
cannot reach: a station room, a coaster's tunnel bore, a cavity in the rock. None of that is
exterior, so every wall LINING one read as buried - and taking the lining exposed the next course,
which the same mask had already condemned. Measured on the shipped composite: **8,523 removed cells
had air on a face**, most of them tunnel and station masonry (`cracked_stone_bricks` 2,717,
`cobblestone` 2,388, `mossy_stone_bricks` 888). Roofs went, the rollercoaster went, terrain opened
into cavities.

**NOTHING CAUGHT IT, AND THAT IS THE PART TO REMEMBER.** The invariant held exactly - gutting a
sealed room does not connect it to the outside, so the reachable set really was unchanged. Eight
rendered bearings were pixel-identical, because all of it is behind the outer skin. The whole test
suite was green. It took a person walking around inside. **An invariant about the OUTSIDE cannot
speak for the inside, however precisely it is asserted, and a render cannot see a room.**

`_check` now asserts the thing that actually matters: no cell that had a face onto air or glass was
removed. Per cell, against the model as it was.

## Seeing through is not the same as being air

A neighbour counts as blocking only if it is an OPAQUE FULL CUBE. Glass, leaves, slabs, stairs,
fences, walls, iron bars, water and vines all leave the block behind them visible. `SEE_THROUGH` is
keyed on `blocks.json`'s own `type` field rather than a hand-written block list, so a leaf family
added to the game is covered without anyone remembering.

## Scope is the caller's, and on the park it is the LANDSCAPE

Jack: *"i said landscape terraforming etc only"*. `carve_only` is that - a mask of cells this pass
may touch, with everything else CONTEXT: still deciding what is hidden, never itself removed.
`tools/park_place.TERRAIN_MODULES` builds it from the five modules that are ground, intersected
with the natural rock and soil a terraforming pass lays. A ride, a station, a building and a
sculpture are all somebody's structure and stay whole whatever is buried in them.

## Six guards, and each is a way a hidden block is still load-bearing

Invisible is necessary and not sufficient. None of these shows up in an audit, a bill of materials
or any render:

* **A GRAVITY BLOCK NEEDS THE BLOCK UNDER IT.** The Mine Ridge's crust is gravel; the gravel is
  skin and stays, and the cell beneath it is hidden. Rule 13, from underneath. A stack resolves
  itself, because the cell under the lowest gravel is under a gravel too.
* **A MECHANISM IS MORE THAN ITS OWN CELL** - the block a repeater reads, the block a torch stands
  on, the block above a piston. `mech_clear` keeps a radius round anything `protect` names.
* **...BUT `protect.MECHANISM` HOLDS `wool`, AND WOOL IS 12,500 CELLS OF DINOSAUR.** CLAUDE.md has
  written this down twice: it is the never-OVERWRITE set, and read as a general keep-out it
  swallows every wool block in the park. Fabric is protected by being NEAR a real mechanism, which
  is the thing that was ever true about it, and not by being fabric.
* **A FLUID FLOWS INTO WHAT YOU OPEN.** Subsumed by the local rule at shell 1 and kept anyway: it
  is the guard that would still hold if `opaque` ever widened.
* **ANYTHING NOT A FULL CUBE IS ATTACHED TO SOMETHING** - a buried slab, rail or torch is held up
  by an ordinary cube.
* **A BLOCK THAT EMITS IS A FIXTURE**, against re-opening a spawnable cell nothing would report.

## What it does NOT decide

**A SEALED CAVITY IS DARK, AND DARK IS WHERE MOBS SPAWN.** This pass opens cavities and cannot
light them. The squid was hollowed on exactly that trade, on Jack's own word that mobs do not spawn
here, and the lowland already carries ~3,700 columns of the same thing recorded as an accepted
mob-cap leak. The volume is REPORTED on every run rather than left for somebody to find.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .. import blocks, morph, nbt
from ..gen import protect
from ..schem import Model

AIR = {"air", "cave_air", "void_air", "structure_void"}

#: Block TYPES you can see through even where the SHAPE is a full cube. Read off `blocks.json`'s
#: own `type` field - a hand-written block list goes stale the day a leaf family is added, and the
#: cells behind it would then vanish with nothing to say so.
SEE_THROUGH: frozenset[str] = frozenset({
    "transparent", "stained_glass", "tinted_glass", "half_transparent", "ice", "frosted_ice",
    "leaves", "tinted_particle_leaves", "untinted_particle_leaves",
    "slime", "honey", "barrier", "light", "beacon", "conduit", "spawner",
})

#: Substrings of blocks that EMIT LIGHT. Kept whole - see the module docstring.
EMITS: tuple[str, ...] = (
    "froglight", "glowstone", "sea_lantern", "shroomlight", "jack_o_lantern", "magma_block",
    "redstone_lamp", "lantern", "torch", "campfire", "candle", "lava", "fire", "conduit",
    "end_rod", "glow_lichen", "sculk_catalyst", "crying_obsidian", "respawn_anchor",
    "amethyst_cluster", "budding_amethyst", "beacon", "ochre_froglight",
)

#: Fluids, and the states that carry one. A hidden cell beside any of these is a pool wall.
FLUIDS: tuple[str, ...] = ("water", "lava", "bubble_column")


def _short(name: str) -> str:
    return name.split(":")[-1].split("[")[0]


def _is_fabric(name: str) -> bool:
    """Wool and carpet. In `protect.MECHANISM` as a SHIELD, not as a machine - see the docstring."""
    n = _short(name)
    return n.endswith("_wool") or n.endswith("_carpet") or n in ("wool", "carpet", "moss_carpet")


def _types() -> dict:
    path = Path(__file__).resolve().parents[1] / "data" / "blocks.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _spread(mask: np.ndarray, r: int) -> np.ndarray:
    """Dilate a SPARSE mask by marking a box round each cell.

    `morph.dilate` shifts the whole array once per offset, which at 26 million cells is minutes
    for a set of three thousand. This is the same answer for a set that is mostly empty.
    """
    if r <= 0 or not mask.any():
        return mask
    out = np.zeros_like(mask)
    for y, z, x in np.argwhere(mask):
        out[max(y - r, 0):y + r + 1, max(z - r, 0):z + r + 1, max(x - r, 0):x + r + 1] = True
    return out


#: The twelve EDGE diagonals - one step on each of two axes. Two cells this far apart share an
#: edge and no face, so a printer standing at one has nothing to click to reach the other.
EDGE12: tuple[tuple[int, int, int], ...] = tuple(
    (dy, dz, dx)
    for dy in (-1, 0, 1) for dz in (-1, 0, 1) for dx in (-1, 0, 1)
    if [dy, dz, dx].count(0) == 1
)


#: ...and the six of them that are enough. An unordered pair {A, B} appears twice in `EDGE12` -
#: once as B - A and once as A - B - so walking all twelve visits every join from both ends and
#: puts BOTH of its corners back where one does the job. Keeping the offsets whose first non-zero
#: step is +1 visits each join exactly once.
EDGE_PAIRS: tuple[tuple[int, int, int], ...] = tuple(
    d for d in EDGE12 if next(c for c in d if c) == 1
)


def _axes(d: tuple[int, int, int]) -> tuple[tuple, tuple]:
    """Split an edge diagonal into its two single-axis steps - the two corner cells."""
    a = [(d[0], 0, 0), (0, d[1], 0), (0, 0, d[2])]
    return tuple(s for s in a if any(s))  # type: ignore[return-value]


def _connect(surv: np.ndarray, removed: np.ndarray, rounds: int = 3) -> np.ndarray:
    """Put back the cells a PRINTER needs, and only those. Returns the mask to restore.

    A PRINTER CLICKS A FACE. Solid, a slope is a staircase with its own mass behind it, so every
    tread has a face to place against; hollow it to one course and consecutive treads touch only
    along an EDGE - the design is intact, looks identical, and has to be built by hand a block at
    a time. Measured on the park: a one-deep skin took the printing islands from 1,582 to 3,409.

    THE CORNER IS ALWAYS WITHIN REACH OF THE SKIN, which is why keeping them is so much cheaper
    than keeping a whole second course: where A and B are both skin cells - one step from air - a
    corner face-adjacent to both is at most two steps from air, so it is a cell a two-deep skin
    would have kept anyway. Measured on the park that is ~25,000 cells against the ~77,000 a
    blanket second course costs, for the same printability.

    It does NOT follow that every cell this keeps is inside two of the air, and the test says so:
    it runs to a fixpoint, and a corner between a cell round 1 put back and one a GUARD had already
    held deep can sit deeper than that. Those are few and they are the same kind of cell - one the
    printer cannot do without.

    Restoring only ever ADDS, so it cannot open a sightline: every cell it puts back was solid in
    the design a moment ago and is behind the same skin it was behind before.
    """
    surv = surv.copy()
    removed = removed.copy()
    restore = np.zeros_like(surv)
    for _ in range(rounds):
        got = np.zeros_like(surv)
        for d in EDGE_PAIRS:
            neg = (-d[0], -d[1], -d[2])
            both = surv & morph.shift(surv, *neg, fill=False)
            if not both.any():
                continue
            d1, d2 = _axes(d)
            gap = both & ~morph.shift(surv, *(-c for c in d1), fill=False) \
                       & ~morph.shift(surv, *(-c for c in d2), fill=False)
            if not gap.any():
                continue
            # Prefer whichever corner the design actually had. Both are equally invisible; only
            # one of them is the block that was standing there, and re-inventing a material is
            # what `printable`'s fills have to do because they arrive after the fact.
            take1 = gap & morph.shift(removed, *(-c for c in d1), fill=False)
            got |= morph.shift(take1, *d1, fill=False)
            take2 = (gap & ~take1) & morph.shift(removed, *(-c for c in d2), fill=False)
            got |= morph.shift(take2, *d2, fill=False)
        got &= removed
        if not got.any():
            break
        restore |= got
        surv |= got
        removed &= ~got
    return restore


@dataclass
class Unseen:
    """What a run took out, and what every guard held back."""
    removed: Counter = field(default_factory=Counter)
    held: Counter = field(default_factory=Counter)
    hidden: int = 0
    cavity: int = 0
    before: int = 0
    after: int = 0

    @property
    def n(self) -> int:
        return sum(self.removed.values())

    def report(self, top: int = 12) -> str:
        share = 100.0 * self.n / self.before if self.before else 0.0
        out = [f"unseen: {self.n:,} of {self.hidden:,} hidden cells removed "
               f"({self.before:,} -> {self.after:,} blocks, -{share:.1f}%)"]
        for name, k in self.removed.most_common(top):
            out.append(f"    {k:>8,}  {name}")
        rest = self.n - sum(k for _, k in self.removed.most_common(top))
        if rest:
            out.append(f"    {rest:>8,}  ... and {len(self.removed) - top} more")
        if self.held:
            out.append("  held back: " + ", ".join(f"{r} {k:,}" for r, k in self.held.most_common()))
        out.append(f"  sealed cavity opened: {self.cavity:,} cells - unlit and unreachable, "
                   f"see `mcbuild/ops/unseen.py` on what that trades")
        return "\n".join(out)


def hollow_unseen(m: Model, *, shell: int = 1, only: set[str] | None = None,
                  keep: set[str] | None = None, mech_clear: int = 3,
                  connect: bool = True, carve_only: np.ndarray | None = None) -> Unseen:
    """Remove every opaque full cube the outside cannot see. Returns what moved.

    `shell`   how many cells deep the skin is. 1 is exact - a block with an opaque cube on all six
              sides is invisible, full stop - and more is only ever paranoia about the opacity
              table, paid for in cells that stay.
    `only`    restrict removal to these block names (terrain-only runs); None means anything hidden.
    `keep`    block names never removed whatever else is true.
    `mech_clear`  radius held round every mechanism. 3 is the sculk sensor's own wool shield.
    `carve_only` bool mask, the model's own shape: cells this pass may touch. Anything else is
              CONTEXT - it decides what is hidden and is never itself removed. Use it to scope
              a pass to the landscape and leave every building alone.
    `connect` keep the corner cells a printer needs to get from one course to the next. On by
              default: off, a sloped skin is a staircase of edge-diagonal cells and has to be
              built by hand. See `_connect`.
    """
    keep = {_short(k) for k in (keep or ())}
    only = {_short(o) for o in only} if only is not None else None
    types = _types()
    names = m.names
    short = [_short(n) for n in names]

    def opaque(n: str) -> bool:
        if n in AIR:
            return False
        return blocks.is_full_cube(n) and (types.get(n) or {}).get("type") not in SEE_THROUGH

    solid = m.solid()
    res = Unseen(before=int(solid.sum()))
    op = np.array([opaque(n) for n in short])[m.ids]

    # ---- what nobody can see, and the mistake that cost a shipped park ----------------------
    # THE TEST IS LOCAL. A block is hidden when all six of its neighbours are opaque full cubes,
    # and that is the whole of it - `erode(opaque)`, no flood anywhere.
    #
    # The first version of this asked a different question: is the block adjacent to air the
    # OUTSIDE CAN REACH. That sounds stronger and it is catastrophically weaker, because a park is
    # full of air the outside cannot reach - a station room, a coaster's tunnel bore, a cavity in
    # the rock. None of that is exterior, so every wall LINING one read as buried, and taking the
    # lining left the next course lining it, in the same pass, from the same mask. Measured on the
    # shipped composite: 8,523 removed cells had air on a face, most of them the tunnel and station
    # masonry - `cracked_stone_bricks` 2,717, `cobblestone` 2,388, `mossy_stone_bricks` 888.
    #
    # NEITHER GUARD COULD SEE IT, and that is the part worth keeping. The invariant held, because
    # gutting a sealed room does not connect it to the outside - `reach` really was unchanged. The
    # render matched, because all of it is behind the outer skin. It took a person walking inside.
    # An invariant about the OUTSIDE cannot speak for the inside, however exactly it is asserted.
    pad = shell + 1
    hidden = morph.erode(np.pad(op, pad, constant_values=False), shell, conn=26)
    hidden = hidden[pad:-pad, pad:-pad, pad:-pad]
    res.hidden = int(hidden.sum())
    cand = hidden & op

    # ---- the guards ------------------------------------------------------------------------
    guards: list[tuple[str, np.ndarray]] = []

    emits = np.array([any(e in n for e in EMITS) for n in short])
    guards.append(("emits light", emits[m.ids]))

    # A WATERLOGGED BLOCK IS A BLOCK WITH WATER IN IT, and the state is where that is written -
    # not the name. Read it off the palette entry, the way `work.INTENTIONAL` reads every other
    # property that is a decision rather than something the game derived.
    fluid = np.array([any(f == n or n.startswith(f) for f in FLUIDS) for n in short])
    logged = np.array([nbt.state_props(e).get("waterlogged") == "true" for e in m.palette])
    guards.append(("holds a fluid back", morph.dilate((fluid | logged)[m.ids], 1, conn=6)))

    # THE RADIUS IS FOR MACHINES, and `protect.MECHANISM` is wider than that on purpose: its last
    # two groups are FLUIDS and LIGHT, both of which are guarded above and guarded more precisely -
    # a pool wall is the one course behind the water and a buried lamp is the lamp itself. Held at
    # `mech_clear` as well, `water` alone was keeping 7,803 cells' worth of lake bed three deep.
    # Narrowing the SET is not a loosening; it is replacing a blunt radius with the right one.
    # ...and a `redstone_lamp` is a light AND a machine, so it stays a machine: the fixtures that
    # leave the radius are the ones nothing drives.
    fixture = emits & ~np.array(["redstone" in n for n in short])
    mech = np.array([protect.is_protected(n) for n in short]) & ~fluid & ~fixture
    mech &= np.array([not _is_fabric(n) for n in short])
    guards.append(("near a mechanism", _spread(mech[m.ids], mech_clear)))

    # ANYTHING NOT A FULL CUBE IS ATTACHED TO SOMETHING - a buried slab, rail or torch is held up
    # by an ordinary cube that reads as hidden. One rule, and it covers the ones nobody has built.
    guards.append(("carries a partial block", morph.dilate(solid & ~op, 1, conn=6)))

    falls = np.array([blocks.falls(n) for n in short])[m.ids]
    guards.append(("under a gravity block", morph.shift(falls, -1, 0, 0, fill=False)))

    fixed = np.zeros_like(solid)
    for t in (getattr(m, "tile_entities", None) or []):
        v = t.value
        fixed[int(v["y"].value), int(v["z"].value), int(v["x"].value)] = True
    for e in (getattr(m, "entities", None) or []):
        p = e.value.get("Pos")
        if p is None:
            continue
        x, y, z = (int(np.floor(c.value)) for c in p.value)
        sy, sz, sx = solid.shape
        if 0 <= y < sy and 0 <= z < sz and 0 <= x < sx:
            fixed[y, z, x] = True
    guards.append(("carries a tile entity", _spread(fixed, 1)))

    if keep:
        guards.append(("named in keep", np.array([n in keep for n in short])[m.ids]))
    if only is not None:
        guards.append(("not in only", ~np.array([n in only for n in short])[m.ids]))
    if carve_only is not None:
        guards.append(("outside the carve mask", ~carve_only))

    take = cand.copy()
    for reason, g in guards:
        held = take & g
        k = int(held.sum())
        if k:
            res.held[reason] = k
        take &= ~g

    # ---- and then give the printer its corners back ----------------------------------------
    if connect:
        back = _connect(solid & ~take, take)
        if back.any():
            res.held["a printer needs the corner"] = int(back.sum())
        take &= ~back

    # ---- the invariant ---------------------------------------------------------------------
    ids_gone = m.ids[take]
    m.ids[take] = 0
    _check(m, op, take)

    uniq, cnt = np.unique(ids_gone, return_counts=True)
    for i, k in zip(uniq.tolist(), cnt.tolist()):
        res.removed[short[i]] += int(k)
    after = m.solid()
    res.after = int(after.sum())
    res.cavity = res.before - res.after
    return res


def _check(m: Model, op_before: np.ndarray, gone: np.ndarray) -> None:
    """NO REMOVED CELL HAD A SEE-THROUGH CELL ANYWHERE IN ITS 3x3x3. Per cell, as the model was.

    26 and not 6, and the difference is a hole in a mountain - see the note where `hidden` is
    computed. It does not matter in the slightest whether that neighbour could have been walked to
    from outside the bounding box: if you can see it, it can see this.
    """
    exposed = morph.dilate(~op_before, 1, conn=26) & gone
    if exposed.any():
        n = int(exposed.sum())
        y, z, x = (int(c[0]) for c in np.nonzero(exposed))
        raise RuntimeError(
            f"unseen would remove {n} cell(s) with air or glass in the 3x3x3 around them - the "
            f"first at ({x}, {y}, {z}). Nothing was shipped.")
