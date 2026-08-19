"""Half-block surfacing: give a voxel skin twice the vertical resolution it was built at.

    over = slab_shell(cells, skin, base="oak_log")
    for cell, (name, props) in over.items():
        w.put(*cell, name, **props)

WHY. Everything in this repo is built from full cubes, so a curved surface can only descend in whole
blocks and a back or a flank comes out as a staircase. A slab is half a block, which is the cheapest
possible doubling of resolution on exactly the cells where the staircase shows - the ones sitting
proud of their neighbours.

WHY SLABS AND NOT STAIRS. Stairs would cut convex corners better than a slab can, and the geometry
here is ready for them. They are not used because a stair is DIRECTIONAL, `facing` is easy to get
backwards, and a mirrored stair on every edge of a statue would be invisible in our own renderer -
which draws from the same colour table it would mirror. The capture holds ten stair blocks and none
of them records its state, so there was no evidence to settle the convention from. A slab has only
`type=top|bottom`: there is no way to orient it wrongly. Add stairs when the convention can be
confirmed in game, not from memory - `_STAIR_NOTE` below says what to check.

WHY THE MATERIAL LIST IS SO SHORT. `blocks.available()` is currently a no-op - the server allowlist
is provisional and `enforce` is false - so it answers True for `pale_oak_slab`, a 1.21 block, on a
1.19 server. Asking it would quietly pick blocks that cannot be placed, which is rule 12's exact
failure. So the trusted set is the partials the ALLOWLIST ACTUALLY CONFIRMS, which means the ones
that appear in a real capture off this server. That is evidence of presence rather than a memory of
a version, and the moment a real 1.19 registry dump lands (`tools/server_blocks.py --reports`) this
widens on its own.
"""
from __future__ import annotations

import functools
import json
import math
import pathlib

from .. import blocks

_STAIR_NOTE = """To add stairs, confirm ONE thing in game: place `oak_stairs[facing=east,half=bottom]`
and look at which side is full height. Then the rule here is 'stair facing the OPEN side', and the
`facing` value follows from that observation - do not infer it from this file."""

# Beyond this RGB distance a partial is not worth having: the geometry gain does not pay for a
# visible colour seam down the animal's back. Such a cell simply stays a full block.
MAX_SHIFT = 30.0


# Suffixes and prefixes that decorate a MATERIAL rather than name one: `stripped_oak_log`,
# `oak_planks` and `oak_slab` are all the oak family.
_STRIP = ("_planks", "_log", "_wood", "_stairs", "_slab", "_block", "_bricks", "_brick")


def family_of(name: str) -> str:
    """The material family a block belongs to - `stripped_dark_oak_wood` -> `dark_oak`."""
    n = name.split(":")[-1].split("[")[0]
    if n.startswith("stripped_"):
        n = n[len("stripped_"):]
    for s in _STRIP:
        if n.endswith(s) and len(n) > len(s):
            n = n[:-len(s)]
            break
    return n


@functools.lru_cache(maxsize=1)
def _confirmed() -> frozenset:
    """Every block the allowlist actually witnessed on this server."""
    try:
        d = json.loads((pathlib.Path(__file__).resolve().parent.parent
                        / "data/server_blocks.json").read_text(encoding="utf-8"))
        return frozenset(d.get("blocks", ()))
    except Exception:
        return frozenset()


def trusted_slabs(witnesses: tuple = ()) -> tuple:
    """Slabs we have positive evidence for, without guessing at Minecraft's version history.

    Three sources, in order of strength:

      1. If the allowlist is AUTHORITATIVE (a real registry dump for the server's version), just
         ask it. Everything below is scaffolding for the fact that it currently is not.
      2. Partials the allowlist actually witnessed in a capture off this server.
      3. Partials whose MATERIAL FAMILY is witnessed. This is the useful one, and it is an
         inference rather than a memory: Minecraft ships a material family COMPLETE - mangrove
         arrived in 1.19 with its planks, slab, stairs, fence and door together - so a server that
         has `mangrove_wood` has `mangrove_slab`. Passing the coat's own blocks as witnesses
         therefore unlocks exactly the materials the animal is already made of, which are also the
         only ones whose colour can match it.

    What this deliberately does NOT do is filter the registry by a remembered list of which blocks
    postdate 1.19. `blocks.available()` is a no-op while `enforce` is false, so it answers True for
    `pale_oak_slab` on a 1.19 server, and correcting that from memory is precisely the mistake rule
    11 is about. An unwitnessed family simply does not get used.
    """
    if blocks.server_authoritative():
        return tuple(sorted(n for n in blocks.search("slab")
                            if n.endswith("_slab") and blocks.available(n)))
    conf = _confirmed()
    fams = {family_of(n) for n in conf} | {family_of(n) for n in witnesses}
    out = {n for n in conf if n.endswith("_slab")}
    for n in blocks.search("slab"):
        if n.endswith("_slab") and family_of(n) in fams:
            out.add(n)
    return tuple(sorted(out))


def slab_for(name: str, max_shift: float = MAX_SHIFT, witnesses: tuple = ()) -> str | None:
    """The trusted slab closest in measured colour to `name`, or None if none is close enough.

    Most coat blocks are logs, wool or bone_block, none of which HAS a slab form - so this is a
    colour match, not a family lookup. `spruce_planks` happens to match `spruce_slab` exactly.

    A PILLAR IS NEVER SLABBED, and this is the whole reason the first attempt looked wrong. The
    colour database samples a block's TOP face, and on a log or a `bone_block` the top is end grain
    while the side - the face a statue actually shows - is bark. Matching `acacia_log`'s orange top
    against `acacia_slab` drew a bright orange line down a grey-brown bear's back, and a white one
    under its belly. `blocks.kind` reports `rotated_pillar` for exactly these blocks, so the game
    settles it rather than a rule of thumb. Planks, stone and wool are uniform on every face, so
    for them the sampled colour is the colour you see and the match holds.

    This is the known-wrong note about top-face sampling turning into a real defect rather than a
    theoretical one. When the colour DB grows side-face colours, this restriction can be lifted.
    """
    if blocks.kind(name) == "rotated_pillar":
        return None
    want = blocks.color(name)
    if not want:
        return None
    best, bd = None, 1e9
    for s in trusted_slabs(tuple(witnesses)):
        c = blocks.color(s)
        if not c or blocks.kind(s) == "rotated_pillar":
            continue
        d = math.dist(want, c)
        if d < bd:
            best, bd = s, d
    return best if bd <= max_shift else None


def slab_shell(cells, skin, base: str, *, max_shift: float = MAX_SHIFT,
               under: bool = False, floor_y: int | None = None) -> dict:
    """{cell: (block name, props)} for the cells worth halving.

    A cell is halved when it sits PROUD of its neighbours - none of them higher, at least one lower.
    That is the definition of a convex step, and it is the only place a half block reads as smoothing
    rather than as damage: halving a cell in a hollow digs a notch, and halving a whole flat plateau
    just lowers it uniformly, which costs blocks and changes nothing.

    `under` does the same to the UNDERSIDE, and is OFF by default. It is geometrically the same
    operation, but a half block taken off an under-surface reads as a gap rather than as smoothing
    wherever the thing being cut is thin - the elephant's ears are flanges a couple of blocks thick
    and slabbing them cut visible slots straight through. The thickness guard below catches a sheet
    lying flat and does NOT catch one standing on edge, which an ear is. On the elephant the
    underside pass was 17 cells against the top surface's 112, so it was never carrying much:
    turning it off loses little and removes the one artifact this pass could produce.

    `floor_y` protects the feet. An underside cell becomes a TOP slab, which sits in the upper half
    of its cell - do that to the course the animal stands on and it hovers half a block off the
    ground. The `grounded` gate would not catch it either, because the cell is still occupied.
    """
    S = cells if isinstance(cells, (set, frozenset)) else set(cells)
    # the coat's own blocks witness their material families, which is what makes their slabs usable
    wit = tuple(sorted({base, *skin.values()}))
    if floor_y is None and S:
        floor_y = min(y for _x, y, _z in S)
    out = {}
    for c in S:
        x, y, z = c
        for sign, kind in ((1, "bottom"), (-1, "top")):
            if sign < 0 and not under:
                continue
            if sign < 0 and floor_y is not None and y <= floor_y + 1:
                continue                                    # never lift a foot off the ground
            if (x, y + sign, z) in S:                       # not the exposed face on this side
                continue
            nb = [(x + dx, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            higher = any((nx, y + sign, nz) in S for nx, nz in nb)
            if higher:
                continue                                    # in a hollow: halving digs a notch
            # A neighbour is LOWER when the column beside this one has no block at this level -
            # which covers both a one-course step down and a sheer rim, the two places a staircase
            # actually shows. The first version also counted "nothing above the neighbour", which
            # is true right across a FLAT plateau, so it halved entire flat surfaces: that costs
            # blocks, lowers the whole plane uniformly and smooths nothing. It drew a half-block
            # crack the length of the bear's belly.
            lower = sum(1 for nx, nz in nb if (nx, y, nz) not in S)
            if not lower:
                continue                                    # flat plateau: nothing to smooth
            # THICKNESS. Halving a cell removes half its volume, which is smoothing on a mass and a
            # HOLE on a sheet. The elephant's ears are two blocks thick, and slabbing their
            # undersides cut white slots straight through them. Require solid behind the face being
            # cut, so only a mass is ever thinned.
            if (x, y - sign, z) not in S or (x, y - 2 * sign, z) not in S:
                continue
            name = skin.get(c, base)
            sl = slab_for(name, max_shift, wit)
            if sl:
                out[c] = (sl, {"type": kind})
            break                                           # a cell gets at most one half
    return out


def volume_fraction(name: str) -> float:
    """How much of its cell a block actually fills - so a measure of shape can count a slab as half.

    Without this, adding slabs changes nothing any metric can see: every rubric dimension works off
    `ids > 0`, where a slab is as solid as a cube, and a surfacing pass would score exactly zero
    improvement while visibly smoothing the model.
    """
    n = name.split(":")[-1].split("[")[0]
    if n.endswith("_slab"):
        return 0.5
    if n.endswith("_stairs"):
        return 0.75
    return 1.0
