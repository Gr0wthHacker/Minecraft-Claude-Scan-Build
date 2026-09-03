"""THE SEAM - the crystal vein the prism well was cut to reach, breaking the surface.

Jack, on the ground around the finished well: *"we need to find something to actually place in
these areas, they dont fit well especially now with our awesome prism tower."*

**MEASURED FIRST, AND THE HEIGHT HISTOGRAM IS THE WHOLE DIAGNOSIS.** Counted over the shipped
`out/Park Complete.litematic`, every column's height above the build plane:

    band          0-2     3-11    12-24    50+
    frontier     57.7%   19.5%   14.7%    0.9%
    midway       78.1%    8.8%   10.9%    0.5%
    PRISMWORKS   89.1%    3.0%    4.5%    2.5%
    PRISM REACH  96.3%    3.4%    0.0%    0.0%

**There is no middle scale in this land.** Everything is either ankle height or a hundred
courses, so the tower reads as an object dropped on a lawn rather than the thing a place is built
around. The Frontier carries six times the human-scale mass. That - not the emptiness - is why
the tower "doesn't fit".

Two more measurements decided the shape of the answer:

- **The reach's only content is the floor of a building that is not there.** `Wyrm's Crossing` is
  2,839 blocks of which **2,650 are three dark greys of bare paving**, 58 x 43 at V24 U385, and
  the skull it was built to carry moved to the rim gate. It is the slab in Jack's screenshot.
- **Nothing on the surface explains a 110-wide hole.** The well is a DIG and the land around it
  does not acknowledge it in any way.

So: ONE IDEA, THREE SITES. The vein the well was cut to reach, breaking the surface and getting
bigger as you walk toward the mouth.

    fracture   the Prism Reach - the deck cracks, small shards rising to large ones at the
               Prismworks threshold, and a lane through them off the spine to a lookout
    yard       Prismworks column A behind the Foundry Gate - the cutting yard where the seam
               was taken out: benched cut faces, stacked blanks, a gantry line to the mouth
    field      Prismworks column C - the biggest shards, and a raked bank facing the mouth

**IT IS NOT A COLLECTION OF BUILDINGS AND IT MUST NOT BECOME ONE.** `PRISMWORKS_V2_PLAN.md`
retired fourteen of those for exactly that reason. Nothing here is a room; the only enclosed
thing in the whole design is a lookout with a parapet, which is a place to stand.

**AND NOTHING PASSES 30 COURSES.** The v2 plan holds the mast ring to eighteen so *"the park keeps
the two dominants it has rather than gaining a competing third"*, and a field of spikes taller
than the collar would take the mouth's own silhouette. The shards fill the 6-30 band the land has
none of, and stop.

## The palette is a ladder MEASURED ACROSS FAMILIES

This repo has now concluded four separate times that this economy has no value contrast, and
every one of those measurements was taken INSIDE one material family, where a ladder cannot exist
by construction. Measured with `blocks.color(name, "side")`, cheap-or-ok and 1.19:

    polished_blackstone_bricks   45      the deck the seam breaks through
    cyan_wool                   114      the shard's foot
    light_blue_wool             153      its body
    pearlescent_froglight       228      its lit tip

Smallest step 39, biggest 75, against the ~15 at which a tone stops being a tone. And the hue is
the point as much as the value: a blue-cyan against a land of neutral greys and copper orange is
a full hue flip, which is what the turtle proved carries on a floor of one colour.

## Traps this file is written against

- **A LEANING COLUMN DISCONNECTS AT EVERY SIDEWAYS STEP** unless the section is at least one cell
  wide at both courses - the ear tips, the ossicones and the braided root all over again. The
  lean is applied only while the radius is >= 1 and the spike goes straight up.
- **`round()` IS BANKER'S ROUNDING.** Every centre here is integer and every offset is added to
  it, which is the ladybird's own rule.
- **A COLUMN TEST IS NOT A CELL TEST.** `seat` asks about a whole column, which is right for
  deciding where a shard may root and wrong for deciding where a heaved plate may go.
- **THE WORLD IS ASKED, NOT ASSUMED.** Every candidate goes through `_Deck`, which reads the same
  capture `verify_against` audits against - the shop islet's own lesson - and refuses a cell the
  world already fills. The reach's plate is PAVING rather than lawn, so this probe seats on the
  top solid course in a band rather than testing for moss: a design that only knew about lawn
  would have refused the 2,494 columns it exists to work.
"""
from __future__ import annotations

import math

import numpy as np

from .canvas import Canvas, hash01
from .frontier_builds import EAST, NORTH, SOUTH, SIGN_WIDTH, WEST, _Lot
from .frontier_scatter import shipped_cells
from .vertical import Ctx

#: Every entry is checked by `tests/test_seam.py` against `blocks.available` (the 1.19 server),
#: `blocks.spendable` (dirt and grass are CURRENCY here) and `palette.tier`.
#:
#: THE ROCK IS PRISMWORKS' OWN AND NOT THE MINE RIDGE'S. `gen/diggings.py` imports the ridge's
#: geology rather than restating it, and that is right WITHIN a land - two files holding a copy of
#: what rock looks like is how one mountain becomes two different mountains. This is a different
#: land with a different rock: the well's own `deepslate_bricks` / `cobbled_deepslate` /
#: `polished_blackstone_bricks`, so the seam reads as the same hand as the thing it explains.
PAL = {
    "deck": "polished_blackstone_bricks",   # the plate the seam breaks through
    "deck_b": "blackstone",
    "rock": "cobbled_deepslate",
    "rock_b": "deepslate_bricks",
    "rock_c": "tuff",
    "kerb": "polished_blackstone_brick_slab",
    "step": "polished_blackstone_brick_stairs",
    "rock_step": "cobbled_deepslate_stairs",
    "rubble": "cobbled_deepslate_slab",
    "copper": "waxed_copper_block",
    "copper_b": "waxed_exposed_copper",
    "copper_step": "waxed_cut_copper_stairs",
    "copper_slab": "waxed_cut_copper_slab",
    "post": "deepslate_brick_wall",
    "grille": "iron_bars",
    "base": "cyan_wool",                    # the shard, L114
    "mid": "light_blue_wool",               # ...L153
    "tip": "white_wool",                    # ...L236
    "glow": "pearlescent_froglight",        # ...L228, and it is the light
    "crystal": "amethyst_cluster",
    "pane": "light_blue_stained_glass_pane",
    "lamp": "lantern",
    "note": "note_block",
    "sign": "warped_wall_sign",             # the land's own sign, off `PF Front Prismworks`
    "path": "deepslate_tiles",
    "path_b": "polished_deepslate",
    "turf": "moss_carpet",
}

SEAM = {
    "kind": "fracture",            # fracture | yard | field
    "lot": None,                   # [dv, du]
    "at": None,                    # [V, U] in the park lattice
    "anchor": [97500, 203, 80300],
    "sy": 40,
    "under": None,                 # the world this is verified against - ASK THE SAME ONE
    "previous": None,              # this design's own last artifact; see `shipped_cells`
    #: artifacts whose WALKING SURFACE this design may not stand on - see `surface_cells`. It is
    #: named rather than inferred, because the whole point of this design is that it DOES work
    #: one such surface (the crossing's dead plate) and must not work the others.
    "off_limits": (),
    "keep_out": (),                # LOCAL [[v0, v1, u0, u1], ...] - ground another design owns
    "lanes": (),                   # LOCAL [[v0, v1, u0, u1], ...] - ground kept walkable
    "lane_clear": 2,               # ...and how far a shard's foot stays off one
    "clear": 1,                    # columns of margin a shard needs around its own foot

    #: THE SEAM'S OWN LINE, in local coordinates: [v0, u0, v1, u1]. Everything else is derived
    #: from distance to it, so one line moves the whole field and the field cannot come apart
    #: from the story it tells.
    "axis": None,
    "reach": 14.0,                 # how far out from the axis the seam is felt
    "falloff": 0.9,                # how sharply it fades across the axis
    "lobes": 0,                    # outcrops along the axis - see `_lobes`
    "lobe_r": [7.0, 13.0],         # ...their radius, small at the start
    "lobe_wander": 5.0,            # ...and how far off the axis they may sit
    "lobe_floor": 0.30,            # what the seam still does between them
    "grow": [0.35, 1.0],           # intensity along the axis, start -> end
    "pitch": 7,                    # the candidate lattice
    "height": [7, 26],             # shard height, mapped from intensity
    "density": 0.55,               # how many of the lattice's candidates are taken
    "rubble": True,
    "trace": 0,                    # the crack drawn along the whole axis - see `_trace`

    "walk": None,                  # {v, u, dv, du} - a paved lane laid inside a `lanes` box
    "lookout": None,               # fracture: {v, u, dv, du, facing, lines}
    "cuts": (),                    # yard: [[v, u, dv, du, rise], ...]
    "stacks": (),                  # yard: [[v, u], ...]
    "gantry": None,                # yard: {v, u, du, height}
    "spoil": (),                   # yard/field: [[v, u, r, h], ...]
    "bank": None,                  # field: {v, u, dv, du, rise, bench, facing}
    "seed": 0,
    "title": "THE SEAM",
}

_FACE_STEP = {NORTH: (0, -1), SOUTH: (0, 1), EAST: (1, 0), WEST: (-1, 0)}

#: what counts as the park's own untouched ground, for the one question that needs to tell it
#: from paving. `Park Ways` lays moss and nothing else on a lot it has not paved.
_LAWN = ("moss_block", "moss_carpet", "grass_block", "dirt", "coarse_dirt")


def surface_cells(paths, box=None) -> frozenset:
    """The world cells another design owns AS A SURFACE - its paving, kerbs, lamps and furniture.

    **A SEAT IS NOT A PERMISSION.** `_Deck.seat` finds the first free course over a floor, and it
    cannot tell the reach's dead plate - which this design exists to work - from the back
    promenade, which is a guest street with exactly the same shape: a solid course with clear air
    over it. Measured, the cutting yard's lot contains 7 courses of promenade and the field's
    contains the well's own rim gallery, and a probe that only asked "is there a floor" would
    have planted crystal in both.

    Material cannot separate them either: `Park Ways`, the crossing plate and this design are all
    drawn from the same four dark stones, which is the exact case `shipped_cells` exists for. So
    the answer is read off the neighbour's OWN ARTIFACT - the honest one - and a design whose
    surface must stay clear is NAMED in the config rather than inferred, so the choice to work
    the crossing's plate and not the promenade is written down where it can be argued with.

    LAWN IS SKIPPED, or `Park Ways` - which lays every moss block in the park - would make the
    whole park off limits and this design would place nothing at all.
    """
    import os

    from .. import scan as _scan

    out: set = set()
    for path in (paths or ()):
        side = os.path.splitext(str(path))[0] + ".scan.json"
        if not os.path.exists(str(path)) or not os.path.exists(side):
            raise ValueError(f"off_limits names {path!r}, which has no artifact and sidecar here")
        # `scan.load` and not a hand-read of the sidecar: a sidecar's `origin` is a dict in some
        # files and a list in others, and the two disagree silently - `Park Ways` is a dict.
        s = _scan.load(str(path))
        ox, oy, oz = s.origin
        m = s.model
        names = np.array([n.split(":")[-1] for n in m.names])
        drop = np.isin(names, np.array(_LAWN + ("air", "cave_air", "void_air")))
        mask = ~drop[m.ids]                          # [y, z, x]
        ys, zs, xs = np.nonzero(mask)
        wx, wy, wz = xs + ox, ys + oy, zs + oz
        if box:
            keep = ((wx >= box[0]) & (wx <= box[1]) & (wy >= box[2]) & (wy <= box[3])
                    & (wz >= box[4]) & (wz <= box[5]))
            wx, wy, wz = wx[keep], wy[keep], wz[keep]
        out.update(zip(wx.tolist(), wy.tolist(), wz.tolist()))
    return frozenset(out)


# --------------------------------------------------------------------------- the world


class _Deck:
    """What the world says about a column - and the only test that decides where anything goes.

    **IT SEATS, IT DOES NOT LOOK FOR LAWN.** `frontier_scatter._Ground` asks whether the ground
    course is moss, which is exactly right on the Frontier and wrong here: the reach's 2,494
    dead columns are the `Wyrm's Crossing` PLATE, a course of dark paving one above the lawn, and
    a probe that only knew about moss would have refused the ground this design exists to work.
    So it takes the top solid course in a band around the plane and hands back the first free
    course above it.

    A GENERATOR THAT ASKS THE WORLD MUST ASK IT ONCE PER COLUMN, not once per candidate.
    """

    #: what a cell may hold and still count as free. `moss_carpet` is ground cover the design may
    #: replace and the config says so in `verify_replaceable`; everything else standing is
    #: somebody's build.
    SOFT = ("air", "cave_air", "void_air", "moss_carpet")

    def __init__(self, ctx: Ctx, anchor, dv, du, at, clear: int = 1,
                 keep_out=(), mine=None, band: int = 2, head: int = 4, surface=None):
        self.ctx, self.dv, self.du = ctx, dv, du
        self.ax, self.ay, self.az = anchor
        self.at_v, self.at_u = at
        self.clear = int(clear)
        self.band = int(band)
        self.head = int(head)
        self.keep_out = [tuple(int(x) for x in b) for b in (keep_out or ())]
        #: The world cells this design itself shipped last time. **THIS IS THE HONEST ANSWER TO
        #: RULE 15 AND A MATERIAL LIST IS NOT** - in a land where the well, the gate and this
        #: design are all deepslate and blackstone, a material test cannot tell a neighbour's
        #: plinth from our own, and the claim row shipped a post through a marquee proving it.
        self.mine = frozenset(mine or ())
        #: cells another design owns as a walking surface - see `surface_cells`. A column whose
        #: floor is one of these is a STREET, and no seat is ever offered on it.
        self.surface = frozenset(surface or ())
        self._seat: dict = {}
        self._street: dict = {}

    def owned(self, v, u) -> bool:
        return any(a <= v <= b and c <= u <= d for a, b, c, d in self.keep_out)

    def world(self, v, u, y=0):
        return self.ax + self.at_v + v, self.ay + y, self.az + self.at_u + u

    def _soft(self, x, y, z) -> bool:
        n = self.ctx.name_at(x, y, z).split(":")[-1]
        return n in self.SOFT or (x, y, z) in self.mine

    def seat(self, v, u):
        """The first LOCAL course above the world's own floor here, or None.

        None means: off the lot, inside somebody else's ground, over the well's mouth (there is
        no floor at all), or something is standing in the way.
        """
        key = (v, u)
        if key in self._seat:
            return self._seat[key]
        out = None
        if 0 <= v < self.dv and 0 <= u < self.du and not self.owned(v, u):
            x, _, z = self.world(v, u)
            # **TOP DOWN, NOT BOTTOM UP.** The reach is two floors in one lot - the lawn at 202
            # and the crossing's plate at 203 - so the first course with something under it is
            # the LAWN even where a plate stands over it, and a bottom-up scan seats every plate
            # column inside the plate and then refuses it for being occupied. Written that way
            # this design generated exactly nothing, with a clean audit and a correct BOM.
            for y in range(self.band, -1, -1):
                floor = self.ay + y - 1
                if self._soft(x, floor, z):
                    continue
                # A SEAT IS NOT A PERMISSION: a floor somebody else walks on is a street, and a
                # street has the same shape as the ground this design works.
                if (x, floor, z) in self.surface:
                    break
                if all(self._soft(x, self.ay + y + k, z) for k in range(self.head)):
                    out = y
                break
        self._seat[key] = out
        return out

    def on_lawn(self, v, u) -> bool:
        """Is the floor under this column MOSS rather than somebody's paving?

        The reach is two surfaces in one lot - the crossing's dark plate and the lawn around it -
        and the walk must pave one and leave the other alone. `seat` deliberately does not care
        which; this is the one question that does.
        """
        y = self.seat(v, u)
        if y is None:
            return False
        x, _, z = self.world(v, u)
        return self.ctx.name_at(x, self.ay + y - 1, z).split(":")[-1] in _LAWN

    def street(self, v, u) -> bool:
        """Does somebody else's walking surface pass under this column?

        **NOTHING MAY OVERHANG A STREET.** A shard leans up to a fifth of its own height, which at
        26 courses is five cells - enough to put a crystal at head height over the back promenade
        from a foot the seat test quite correctly allowed. A tree one cell off a kerb still crowds
        the walk, and this is the same rule one axis up.
        """
        key = (v, u)
        got = self._street.get(key)
        if got is None:
            x, _, z = self.world(v, u)
            got = any((x, self.ay + k, z) in self.surface for k in range(-1, self.band + 1))
            self._street[key] = got
        return got

    def free(self, v, u, y) -> bool:
        """Is this exact CELL free in the world? A canopy is cells, a trunk is a column."""
        if not (0 <= v < self.dv and 0 <= u < self.du) or self.owned(v, u):
            return False
        if self.surface and self.street(v, u):
            return False
        x, wy, z = self.world(v, u, y)
        return self._soft(x, wy, z)

    def rooted(self, v, u, head: int = 0):
        """A seat with `clear` columns of margin round it, all seated within one course.

        A SHARD ONE CELL OFF A KERB STILL CROWDS THE WALK, and one rooted on a step comes out
        standing on a wall. Both are the same test.
        """
        s = self.seat(v, u)
        if s is None:
            return None
        c = self.clear
        for dv in range(-c, c + 1):
            for du in range(-c, c + 1):
                t = self.seat(v + dv, u + du)
                if t is None or abs(t - s) > 1:
                    return None
        for y in range(s, s + head):
            if not self.free(v, u, y):
                return None
        return s


# --------------------------------------------------------------------------- the field


def _lobes(p: dict) -> list:
    """The seam's OUTCROPS: where along its line it actually breaks the surface.

    **A FIELD WITH NO LOBES IN IT IS CONFETTI.** The first build spread seventeen shards evenly
    down the axis and the plan view read as a dusting of blue dots on a dark floor - which is the
    thicket's own failure ("191 blobs of which 75% were one or two cells") and the deck soffit's
    ("215 runs of which 184 were one or two cells") arriving a third time. A vein does not surface
    evenly; it surfaces in a few places, and the ground between them is what makes those places
    read.

    THE NOISE IS ON THE LOBE'S POSITION AND RADIUS, NEVER ON THE CELL - the thicket's rule, which
    is what puts a solid middle inside a wobbly edge instead of a spray of single cells.
    """
    n = int(p.get("lobes", 0) or 0)
    if n <= 0:
        return []
    v0, u0, v1, u1 = (float(x) for x in p["axis"])
    dv, du = v1 - v0, u1 - u0
    ln = math.hypot(dv, du) or 1.0
    nv, nu = -du / ln, dv / ln                       # the unit normal to the axis
    seed = int(p.get("seed", 0))
    r0, r1 = (float(x) for x in p.get("lobe_r", (7.0, 13.0)))
    out = []
    for k in range(n):
        t = (k + 0.5) / n
        off = (hash01(k, 1, 0, seed) - 0.5) * 2.0 * float(p.get("lobe_wander", 5.0))
        r = r0 + (r1 - r0) * (t * 0.6 + 0.4 * hash01(k, 2, 0, seed))
        out.append((v0 + dv * t + nv * off, u0 + du * t + nu * off, r))
    return out


def _intensity(p: dict, v: float, u: float, lobes=None) -> float:
    """How strongly the seam is felt at a column: 0 nowhere near it, 1 on its axis at full grow.

    ONE LINE DECIDES THE WHOLE FIELD. The alternative - a hand-typed list of shard positions -
    answers the question only where somebody remembered to, which is the same failure that left
    the Welcome Court's two flanks bare when its lot went from 41 wide to 61.
    """
    v0, u0, v1, u1 = (float(x) for x in p["axis"])
    dv, du = v1 - v0, u1 - u0
    n = math.hypot(dv, du) or 1.0
    t = ((v - v0) * dv + (u - u0) * du) / (n * n)      # 0..1 along the axis
    tc = min(1.0, max(0.0, t))
    # perpendicular distance to the SEGMENT, so the field does not run off past its own ends
    pv, pu = v0 + dv * tc, u0 + du * tc
    d = math.hypot(v - pv, u - pu)
    off = max(0.0, 1.0 - d / float(p.get("reach", 14.0)))
    a, b = (float(x) for x in p.get("grow", (0.35, 1.0)))
    s = off ** float(p.get("falloff", 0.9)) * (a + (b - a) * tc)
    lobes = _lobes(p) if lobes is None else lobes
    if lobes:
        best = max(max(0.0, 1.0 - math.hypot(v - lv, u - lu) / lr) for lv, lu, lr in lobes)
        # the floor keeps a thin seam running between the outcrops, so the line still reads
        s *= float(p.get("lobe_floor", 0.30)) + (1.0 - float(p.get("lobe_floor", 0.30))) * best
    return s


# --------------------------------------------------------------------------- the shard


def _radius(r0: int, y: int, h: int) -> int:
    """The section's half-width at course y - a stepped taper, not a smooth one.

    A SMOOTH TAPER AT THIS SCALE IS A CONE AND A CONE IS NOT A CRYSTAL. What reads is a few
    clean shoulders, which is also what a stepped voxel mass does natively.
    """
    t = y / float(max(h - 1, 1))
    # r0 + 0.6 puts the first shoulder at ~30% of the height for a three-wide shard and the spike
    # in the top fifth. At `(r0 + 1) * 1.15` - the first version - a four-wide shard had already
    # lost a course of width by 19% of its height and read as a pole with a cap on it.
    return max(0, r0 - int(t * (r0 + 0.6)))


def base_radius(h: int) -> int:
    """A shard's half-width at its foot. **DIVIDED BY SEVEN AND NOT BY EIGHT**: at /8 everything
    under twelve courses came out as a one-wide plus with a spike on it, which is a bollard."""
    return max(1, min(4, int(h / 7.0 + 0.5)))


def _section(rr: int):
    """A DIAMOND, not a disc. |dv| + |du| <= r gives sharp arrises at the four corners and reads
    as a faceted crystal; a rasterised circle at r<=4 is a blob with a bitten edge."""
    for dv in range(-rr, rr + 1):
        for du in range(-rr, rr + 1):
            if abs(dv) + abs(du) <= rr:
                yield dv, du


def _shard(lot: _Lot, g: _Deck, v: int, u: int, h: int, seed: int) -> dict:
    """One crystal: a leaning, stepped, tapering column with a lit point on it.

    THE LEAN IS APPLIED ONLY WHILE THE SECTION IS AT LEAST ONE CELL WIDE. Two single-cell courses
    offset diagonally are not neighbours, and a spike that steps sideways comes off as a shower
    of loose blocks - the ear tips, the ossicones and the braided root, a fourth time.
    """
    y0 = g.rooted(v, u, head=2)
    if y0 is None:
        return {"at": [v, u], "cells": 0, "why": "no seat"}
    h = int(max(3, h))
    r0 = base_radius(h)
    # the lean: a direction off the cell's own hash, and never more than a third of the height
    ang = hash01(v, u, 3, seed) * math.tau
    lean = (0.09 + 0.13 * hash01(v, u, 5, seed)) * h
    lv, lu = math.cos(ang) * lean, math.sin(ang) * lean

    cells = 0
    top = None
    last_v, last_u = v, u
    for y in range(h):
        rr = _radius(r0, y, h)
        t = y / float(max(h - 1, 1))
        if rr >= 1:
            # int(floor(x + 0.5)) - `round` is banker's and turns a straight taper into a
            # staircase that skips every other course
            cv = v + int(math.floor(lv * t + 0.5))
            cu = u + int(math.floor(lu * t + 0.5))
        else:
            cv, cu = last_v, last_u
        last_v, last_u = cv, cu
        if y >= h - 2:
            key = "glow"
        elif t < 0.30:
            key = "base"
        elif t < 0.70:
            key = "mid"
        else:
            key = "tip"
        for dv, du in _section(rr):
            a, b = cv + dv, cu + du
            if not g.free(a, b, y0 + y):
                continue
            if lot.put(a, y0 + y, b, PAL[key]):
                cells += 1
                if top is None or y0 + y > top[1]:
                    top = (a, y0 + y, b)
    # THE POINT. `amethyst_cluster` is the one block in the game whose texture is a crystal, it
    # is cheap here, and it is the only purple in a design of cyan - so it goes where it can be
    # seen and nowhere else.
    if top and h >= 10 and g.free(top[0], top[2], top[1] + 1):
        if lot.put(top[0], top[1] + 1, top[2], PAL["crystal"], facing="up", waterlogged="false"):
            cells += 1
    return {"at": [v, u], "h": h, "r0": r0, "cells": cells}


def _heave(lot: _Lot, g: _Deck, v: int, u: int, r: int, seed: int) -> int:
    """The deck, lifted and broken where the shard came through.

    A SHARD STANDING ON AN UNBROKEN FLOOR IS AN ORNAMENT ON A TABLE. This is the whole of the
    "cracked plate" idea and it costs a ring: the deck's own stone heaped at the foot, its outer
    edge stepped so the plate reads as tilted rather than as a kerb.

    Every stair leans toward the shard - its tall side is its `facing`, per the convention
    `tests/test_stairhead.py` pins - because our renderer draws both directions identically and
    a plate tilting the wrong way is invisible in every sheet here.
    """
    n = 0
    for dv in range(-r - 1, r + 2):
        for du in range(-r - 1, r + 2):
            d = abs(dv) + abs(du)
            if d == 0 or d > r + 1:
                continue
            a, b = v + dv, u + du
            y = g.seat(a, b)
            if y is None or not g.free(a, b, y):
                continue
            if d <= r:
                key = "deck" if hash01(a, b, 11, seed) < 0.6 else "rock"
                n += int(lot.put(a, y, b, PAL[key]))
            else:
                # the outer course is the tilt: a stair climbing back toward the shard
                if abs(dv) >= abs(du):
                    face = EAST if dv < 0 else WEST
                else:
                    face = SOUTH if du < 0 else NORTH
                n += int(lot.stair(a, y, b, PAL["step"], face))
    # ...and the small crystals at its foot, which is what a real vein looks like
    for k in range(3):
        aa = hash01(v, u, 20 + k, seed) * math.tau
        rr = r + 1
        a = v + int(math.floor(math.cos(aa) * rr + 0.5))
        b = u + int(math.floor(math.sin(aa) * rr + 0.5))
        y = g.seat(a, b)
        if y is None or not lot.has(a, y, b) or not g.free(a, b, y + 1):
            continue
        n += int(lot.put(a, y + 1, b, PAL["crystal"], facing="up", waterlogged="false"))
    return n


def _rubble(lot: _Lot, g: _Deck, v: int, u: int, seed: int) -> int:
    """A splinter: one to three cells of broken crystal lying where it fell. **THE SEAM IS NOT
    ONLY ITS BIG PIECES** - a field of evenly-sized spikes reads as a fence."""
    y = g.rooted(v, u)
    if y is None:
        return 0
    n = 0
    h = 1 + int(hash01(v, u, 31, seed) * 3)
    for k in range(h):
        key = "base" if k == 0 else ("mid" if k == 1 else "glow")
        if g.free(v, u, y + k):
            n += int(lot.put(v, y + k, u, PAL[key]))
    return n


def _trace(lot: _Lot, g: _Deck, p: dict, seed: int) -> dict:
    """The CRACK: the seam's own line drawn across the ground, whether or not it surfaces there.

    **THE OUTCROPS ARE NOT THE SEAM, THEY ARE WHERE IT BREAKS OUT OF THE GROUND.** With lobes
    alone the plate reads as five unrelated clumps of crystal standing on a floor; the trace is
    what makes them five places on ONE line, and it is the only element here that runs the whole
    lot - so the vein visibly enters from the Midway and leaves into Prismworks rather than
    beginning and ending inside its own lot.

    IT IS LAID IN SLABS AND STAIRS, NOT IN FULL BLOCKS. A litematic cannot express removal, so a
    crack in a floor that is already built has to be a HEAVE rather than a cut - and a heave a
    guest can walk over is a line, while one they walk round is a wall. The plan is this design's
    money view and this is what carries it there.
    """
    w = float(p.get("trace", 0) or 0)
    if w <= 0:
        return {"cells": 0}
    v0, u0, v1, u1 = (float(x) for x in p["axis"])
    dv, du = v1 - v0, u1 - u0
    ln = math.hypot(dv, du) or 1.0
    n = 0
    veins = 0
    for v in range(g.dv):
        for u in range(g.du):
            # the perpendicular distance to the axis' INFINITE line, so the trace runs off both
            # ends of the segment and out of the lot
            d = abs((u - u0) * dv - (v - v0) * du) / ln
            if d > w * (0.55 + 0.9 * hash01(v // 2, u // 2, 101, seed)):
                continue
            if any(_in_lane(p, v + a, u + b) for a in (-1, 0, 1) for b in (-1, 0, 1)):
                continue
            y = g.seat(v, u)
            if y is None or not g.free(v, u, y):
                continue
            r = hash01(v, u, 102, seed)
            # **A SOLID MIDDLE INSIDE A WOBBLY EDGE** - the thicket's rule. The first version
            # scattered one material per cell across the whole band and the line vanished in
            # plan: `cobbled_deepslate_slab` is L77 on a plate of L38-73, which is a ladder
            # inside one family, which this file's own docstring says cannot draw a line. The
            # core is the VEIN and it is the only thing here with a hue.
            if d < w * 0.45:
                if r < 0.86:
                    key = "glow" if r < 0.09 else ("base" if r < 0.55 else "mid")
                    if lot.put(v, y, u, PAL[key]):
                        n += 1
                        veins += 1
                continue
            if r < 0.42:
                n += int(lot.slab(v, y, u, PAL["rubble"]))
            elif r < 0.60:
                n += int(lot.put(v, y, u, PAL["rock" if r < 0.52 else "deck_b"]))
            elif r < 0.78:
                if abs(dv) > abs(du):
                    face = EAST if hash01(v, u, 103, seed) < 0.5 else WEST
                else:
                    face = SOUTH if hash01(v, u, 103, seed) < 0.5 else NORTH
                n += int(lot.stair(v, y, u, PAL["step"], face))
    return {"width": w, "veins": veins, "cells": n}


# --------------------------------------------------------------------------- the sweep


def _in_lane(p: dict, v: int, u: int) -> bool:
    for box in (p.get("lanes") or ()):
        a, b, c, d = (int(x) for x in box)
        if a <= v <= b and c <= u <= d:
            return True
    return False


def _sweep(lot: _Lot, g: _Deck, p: dict, seed: int) -> dict:
    """Plant the seam on a coarse lattice, biggest first, with a real gap between neighbours.

    **SPACING IS THE FEATURE.** Three-block spots at three-block spacing merged into one mass and
    the ladybird read as a black beetle with red veins; two shards whose feet touch read as one
    lump with two points. The separation is derived from the pair's own radii, so it cannot go
    stale when the height range moves.

    AND THE LATTICE IS JITTERED, NEVER STRAIGHT. A field on an exact grid is an orchard.
    """
    pitch = max(3, int(p.get("pitch", 7)))
    hmin, hmax = (int(x) for x in p.get("height", (7, 26)))
    dens = float(p.get("density", 0.55))
    lanes = int(p.get("lane_clear", 2))

    # ...computed ONCE. `_intensity` would otherwise rebuild the lobe list per candidate, which
    # is the "ask the world once per cell, not once per candidate" rule one level up.
    lobes = _lobes(p)

    cand = []
    for v in range(1, g.dv - 1, pitch):
        for u in range(1, g.du - 1, pitch):
            a = v + int(hash01(v, u, 1, seed) * pitch) - pitch // 2
            b = u + int(hash01(v, u, 2, seed) * pitch) - pitch // 2
            s = _intensity(p, a, b, lobes)
            if s <= 0.02 or hash01(a, b, 4, seed) > dens * (0.45 + 0.75 * s):
                continue
            cand.append((s, a, b))
    cand.sort(reverse=True)

    taken: list[tuple[int, int, int]] = []
    shards = []
    splinters = 0
    for s, v, u in cand:
        # a shard may not lean over a lane either, so its own foot keeps its distance
        if any(_in_lane(p, v + dv, u + du)
               for dv in range(-lanes, lanes + 1) for du in range(-lanes, lanes + 1)):
            continue
        h = int(hmin + (hmax - hmin) * (s ** 0.9) * (0.66 + 0.46 * hash01(v, u, 6, seed)))
        h = max(3, min(hmax, h))
        r0 = base_radius(h)
        if any(abs(v - a) + abs(u - b) < r0 + rb + 2 for a, b, rb in taken):
            continue
        got = _shard(lot, g, v, u, h, seed)
        if not got["cells"]:
            continue
        taken.append((v, u, r0))
        got["heave"] = _heave(lot, g, v, u, r0, seed)
        shards.append(got)

    if p.get("rubble", True):
        for v in range(2, g.dv - 2, 3):
            for u in range(2, g.du - 2, 3):
                a = v + int(hash01(v, u, 7, seed) * 3) - 1
                b = u + int(hash01(v, u, 8, seed) * 3) - 1
                if any(_in_lane(p, a + dv, b + du)
                       for dv in (-1, 0, 1) for du in (-1, 0, 1)):
                    continue
                s = _intensity(p, a, b, lobes)
                if hash01(a, b, 9, seed) > s * 0.40:
                    continue
                if any(abs(a - cv) + abs(b - cu) < cr + 2 for cv, cu, cr in taken):
                    continue
                n = _rubble(lot, g, a, b, seed)
                if n:
                    splinters += 1
                    taken.append((a, b, 0))
    return {"shards": shards, "splinters": splinters,
            "tallest": max((s.get("h", 0) for s in shards), default=0),
            "cells": sum(s["cells"] + s.get("heave", 0) for s in shards)}


def _sign(lot: _Lot, v: int, y: int, u: int, facing: str, lines) -> bool:
    """A wall sign IN THE LAND'S OWN TIMBER, with its support checked.

    `_Lot.sign` belongs to the Frontier and hard-codes `spruce_wall_sign` through that module's
    own palette - measured, this design shipped one spruce sign into a land whose every other
    sign is warped. The support and the emptiness are checked here exactly as they are there,
    because a wall sign floating in air draws exactly like one on a wall.
    """
    dv = {EAST: 1, WEST: -1}.get(facing, 0)
    du = {SOUTH: 1, NORTH: -1}.get(facing, 0)
    if not lot.has(v - dv, y, u - du) or lot.has(v, y, u):
        return False
    if not lot.put(v, y, u, PAL["sign"], facing=facing, waterlogged="false"):
        return False
    text = [str(t)[:SIGN_WIDTH] for t in list(lines)[:4]]
    lot.c.sign_text(v, y, u, front=text, colour="white", glowing=True)
    lot.signs.append({"at": [v, y, u], "facing": facing, "lines": text})
    return True


# --------------------------------------------------------------------------- the route


def _walk(lot: _Lot, g: _Deck, p: dict, seed: int) -> dict:
    """The lane through the seam, paved - and paved ONLY WHERE THE GROUND IS LAWN.

    The reach's plate is already a dark stone floor; laying a walk over it would be a second
    surface on a finished one, which is the thing this park was rebuilt to stop. So the lane is
    declared over the whole route and only the moss half of it is actually paved, which is what
    makes the walk read as one continuous surface rather than as a strip laid on a slab.
    """
    legs = p.get("walk") or ()
    if isinstance(legs, dict):
        legs = [legs]
    n = 0
    for w in legs:
        v0, u0 = int(w["v"]), int(w["u"])
        dv, du = int(w.get("dv", 3)), int(w.get("du", 3))
        for v in range(v0, v0 + dv):
            for u in range(u0, u0 + du):
                y = g.seat(v, u)
                if y is None or not g.free(v, u, y):
                    continue
                edge = (v in (v0, v0 + dv - 1)) or (u in (u0, u0 + du - 1))
                if not g.on_lawn(v, u):
                    # **THE PLATE IS ALREADY A FLOOR, SO THE LANE IS AN EDGING AND NOT A
                    # SURFACE.** Repaving it would be a second surface on a finished one, which
                    # is the thing this park was rebuilt to stop - and leaving it undrawn makes
                    # the route a gap in a field, which nobody reads as a route. A kerb slab
                    # along the outer cells says where the walk is at the cost of its own line.
                    if edge:
                        n += int(lot.slab(v, y, u, PAL["kerb"]))
                    continue
                key = "path_b" if edge else ("path" if hash01(v, u, 41, seed) > 0.22
                                             else "path_b")
                n += int(lot.put(v, y, u, PAL[key]))
    return {"legs": len(legs), "cells": n}


def _lookout(lot: _Lot, g: _Deck, p: dict, seed: int) -> dict:
    """A place to stand at the end of the lane, and the design's only VERB.

    **A PATH IS REAL WHEN BOTH OF ITS ENDS ARE PLACES** - this repo settled that on the lowland
    quay - so the lane does not simply stop in a field. And Jack's standing complaint about this
    park is *"we don't want empty structures that sit there and are mostly useless"*, so what is
    at the end is not a shelter: it is a rail of NOTE BLOCKS among the biggest shards. A note
    block plays when a guest right-clicks it, with no redstone anywhere in it - so there is
    nothing here that could ship looking like a machine and do nothing, which is the failure that
    cut two finished casino games.

    THE INSTRUMENT COMES FROM THE BLOCK UNDERNEATH, so the rail stands on the shard's own wool
    (guitar) rather than on stone. **The `note` value does not survive placement** - a printer
    places a block's default state and vanilla starts every note block at 0 - so nothing here
    promises a tuning; a guest tunes it by clicking, which is the toy.
    """
    spec = p.get("lookout")
    if not spec:
        return {"cells": 0}
    v0, u0 = int(spec["v"]), int(spec["u"])
    dv, du = int(spec.get("dv", 9)), int(spec.get("du", 11))
    entry = str(spec.get("entry", WEST))
    if entry not in _FACE_STEP:
        raise ValueError(f"a lookout needs a real entry side, not {entry!r}")
    base = g.seat(v0 + dv // 2, u0 + du // 2)
    if base is None:
        return {"cells": 0, "why": "no seat"}

    n = 0
    deck = base + 1                                  # one course up: it is a lookout
    for v in range(v0, v0 + dv):
        for u in range(u0, u0 + du):
            y = g.seat(v, u)
            if y is None:
                continue
            for k in range(y, deck):
                if g.free(v, u, k):
                    n += int(lot.put(v, k, u, PAL["rock_b"]))
            if g.free(v, u, deck):
                key = "path" if hash01(v, u, 51, seed) > 0.25 else "path_b"
                n += int(lot.put(v, deck, u, PAL[key]))

    # THE PARAPET, with a three-cell gate in the middle of the side the lane arrives from - and
    # the gate is left EMPTY by the loop rather than punched afterwards. Building the ring first
    # and cutting a hole repaints cells that already exist, which is how the void tower's
    # crenellations shipped as a plain drum with nothing about the code looking wrong.
    ev, eu = _FACE_STEP[entry]
    mid_v, mid_u = v0 + dv // 2, u0 + du // 2
    for v in range(v0, v0 + dv):
        for u in range(u0, u0 + du):
            if not (v in (v0, v0 + dv - 1) or u in (u0, u0 + du - 1)):
                continue
            on_entry = (ev and v == (v0 if ev < 0 else v0 + dv - 1)) or \
                       (eu and u == (u0 if eu < 0 else u0 + du - 1))
            if on_entry and (abs(u - mid_u) <= 1 if ev else abs(v - mid_v) <= 1):
                continue
            # `free(v, u, y)`, NOT `(v, y, u)` - written the other way round this reads a cell
            # that does not exist, the guard passes, and the parapet ships wherever it likes.
            # `gen/claimrow.py` shipped exactly this transposition once.
            if not g.free(v, u, deck + 1):
                continue
            n += int(lot.put(v, deck + 1, u, PAL["post"], up="true", waterlogged="false",
                             north="none", south="none", east="none", west="none"))

    # THE RAIL, one course inside the parapet OPPOSITE the entry, so a guest arrives facing it
    # and plays it looking out over the seam rather than at their own feet.
    notes = []
    if ev:
        rv = v0 + dv - 2 if ev < 0 else v0 + 1
        line = [(rv, u) for u in range(u0 + 2, u0 + du - 2)]
    else:
        ru = u0 + du - 2 if eu < 0 else u0 + 1
        line = [(v, ru) for v in range(v0 + 2, v0 + dv - 2)]
    for k, (v, u) in enumerate(line):
        if not (g.free(v, u, deck + 1) and g.free(v, u, deck + 2)):
            continue
        if not lot.put(v, deck + 1, u, PAL["mid" if k % 2 else "base"]):
            continue
        n += 1
        # THE INSTRUMENT IS THE BLOCK UNDERNEATH, which is why the rail stands on the shard's own
        # wool (guitar) and not on stone. The `note` VALUE is not promised: a printer places a
        # block's default state and vanilla starts every note block at 0, so the tuning is the
        # guest's - which is the toy.
        if lot.put(v, deck + 2, u, PAL["note"]):
            n += 1
            notes.append([v, deck + 2, u])

    # THE SIGN HANGS ON A PARAPET POST, and the post is CHECKED rather than assumed - four of this
    # park's seven building kinds once shipped a sign on the one column of a wall that has an
    # opening in it, and a wall sign floating in air draws exactly like one on a wall.
    lines = [str(x)[:SIGN_WIDTH] for x in (spec.get("lines")
                                           or ("THE SEAM", "strike it", "it answers"))]
    signed = False
    for sv, su, face in ((v0 + 1, u0 + 1, SOUTH), (v0 + dv - 2, u0 + 1, SOUTH),
                         (v0 + 1, u0 + du - 2, NORTH), (v0 + dv - 2, u0 + du - 2, NORTH)):
        if _sign(lot, sv, deck + 1, su, face, lines):
            signed = True
            break
    return {"at": [v0, u0], "size": [dv, du], "deck": deck, "notes": len(notes),
            "signed": signed, "cells": n}


# --------------------------------------------------------------------------- the workings


def _terrace_height(spec: dict, v: int, u: int) -> int:
    """How high the ground stands at a cell of a benched face, in courses above its own seat."""
    v0, u0 = int(spec["v"]), int(spec["u"])
    dv, du = int(spec["dv"]), int(spec["du"])
    facing = str(spec.get("facing", NORTH))
    fv, fu = _FACE_STEP[facing]
    # distance BACK from the face the bank looks out over
    if fv:
        d = (v - v0) if fv < 0 else (v0 + dv - 1 - v)
    else:
        d = (u - u0) if fu < 0 else (u0 + du - 1 - u)
    run = max(1, int(spec.get("run", 3)))
    return max(0, min(int(spec.get("rise", 6)), d // run))


def _bench(lot: _Lot, g: _Deck, spec: dict, seed: int, crystal: bool = False) -> dict:
    """A benched face of rock: the cut where the seam was taken out, or the bank you watch from.

    ONE FUNCTION FOR BOTH, because they are the same geometry read from opposite sides - a cut is
    a rise you look INTO and a bank is a rise you stand ON. Writing them twice is how one land
    ends up with two different rocks in it.

    **THE TOP OF EVERY BENCH IS WALKABLE.** A terrace whose top course is the same rough rock as
    its face is a heap; a dressed top is a step, and a stack of steps is a stand.
    """
    v0, u0 = int(spec["v"]), int(spec["u"])
    dv, du = int(spec["dv"]), int(spec["du"])
    n = 0
    tops = 0
    for v in range(v0, v0 + dv):
        for u in range(u0, u0 + du):
            y = g.seat(v, u)
            if y is None:
                continue
            h = _terrace_height(spec, v, u)
            for k in range(h):
                if not g.free(v, u, y + k):
                    continue
                if k == h - 1:
                    n += int(lot.put(v, y + k, u, PAL["path" if spec.get("walk") else "rock_b"]))
                    tops += 1
                else:
                    key = "rock" if hash01(v, u, 61 + k, seed) < 0.55 else "rock_b"
                    n += int(lot.put(v, y + k, u, PAL[key]))
            # THE SEAM SHOWS IN THE FACE. A cut face with no crystal in it is a quarry, and this
            # land is not a quarry - it is the one place the vein can be seen in section.
            if crystal and h and hash01(v, u, 71, seed) < 0.16:
                k = max(0, h - 1 - int(hash01(v, u, 72, seed) * max(1, h - 1)))
                if g.free(v, u, y + k):
                    n += int(lot.put(v, y + k, u,
                                     PAL["mid" if hash01(v, u, 73, seed) < 0.5 else "base"]))
    return {"at": [v0, u0], "size": [dv, du], "rise": int(spec.get("rise", 6)),
            "tops": tops, "cells": n}


def _steps(lot: _Lot, g: _Deck, spec: dict) -> int:
    """A flight up the benches, so the bank is climbed rather than looked at.

    THE TREADS FACE THE ASCENT: a flight that climbs toward D has every tread `facing=D`, which
    `tests/test_stairhead.py` pins - and our renderer draws a backwards flight and a correct one
    identically, so this is asserted rather than eyeballed.
    """
    v0, u0 = int(spec["v"]), int(spec["u"])
    dv, du = int(spec["dv"]), int(spec["du"])
    facing = str(spec.get("facing", NORTH))
    fv, fu = _FACE_STEP[facing]
    up = {NORTH: SOUTH, SOUTH: NORTH, EAST: WEST, WEST: EAST}[facing]
    n = 0
    #: the flight runs up the middle of the bank, against its own gradient
    if fv:
        line = [(v, u0 + du // 2) for v in range(v0, v0 + dv)]
    else:
        line = [(v0 + dv // 2, u) for u in range(u0, u0 + du)]
    last = -1
    for v, u in line:
        y = g.seat(v, u)
        if y is None:
            continue
        h = _terrace_height(spec, v, u)
        if h > last and h > 0 and g.free(v, u, y + h - 1):
            n += int(lot.stair(v, y + h - 1, u, PAL["rock_step"], up))
        last = h
    return n


def _stack(lot: _Lot, g: _Deck, v: int, u: int, seed: int) -> int:
    """Cut blanks on a pallet: the seam, squared off and stacked, waiting to go somewhere.

    It is the one prop that says this ground is a WORKS rather than a field - a shard in the
    ground is geology, a shard cut into a cube is somebody's afternoon.
    """
    y = g.rooted(v, u, head=4)
    if y is None:
        return 0
    n = 0
    for dv in range(3):
        for du in range(2):
            a, b = v + dv, u + du
            if g.free(a, b, y):
                n += int(lot.put(a, y, b, PAL["copper_slab"], type="bottom", waterlogged="false"))
            hh = 1 + int(hash01(a, b, 81, seed) * 2.4)
            for k in range(hh):
                if g.free(a, b, y + 1 + k):
                    n += int(lot.put(a, y + 1 + k, b,
                                     PAL["base" if (k + dv) % 2 else "mid"]))
    return n


def _gantry(lot: _Lot, g: _Deck, p: dict, seed: int) -> dict:
    """The line the cut stone leaves by: posts, a beam, and a lamp every other bay.

    IT IS A PROP AND NOT A THIRD RAILWAY. The Frontier's elevated ore line was deleted on sight
    for piercing a building's wall five courses up, and this land already has the park railway on
    its rim. This carries nothing and states so: a beam on posts, running to the collar and
    stopping where the world stops it.
    """
    spec = p.get("gantry")
    if not spec:
        return {"cells": 0}
    v = int(spec["v"])
    u0, du = int(spec["u"]), int(spec["du"])
    hh = int(spec.get("height", 5))
    n, bays, stopped = 0, 0, None
    for k in range(du):
        u = u0 + k
        y = g.seat(v, u)
        if y is None:
            stopped = stopped or u
            continue
        if k % 4 == 0:
            ok = True
            for j in range(hh):
                if not g.free(v, u, y + j):
                    ok = False
                    break
                n += int(lot.put(v, y + j, u, PAL["post" if j else "rock_b"],
                                 **({} if not j else {"up": "true", "waterlogged": "false",
                                                      "north": "none", "south": "none",
                                                      "east": "none", "west": "none"})))
            if ok:
                bays += 1
        if g.free(v, u, y + hh):
            n += int(lot.put(v, y + hh, u, PAL["copper" if k % 4 else "copper_b"]))
        if k % 8 == 4 and g.free(v, u, y + hh - 1) and lot.has(v, y + hh, u):
            n += int(lot.hang(v, y + hh - 1, u))
    return {"at": [v, u0], "du": du, "bays": bays, "stops_at": stopped, "cells": n}


def _spoil(lot: _Lot, g: _Deck, v: int, u: int, r: int, h: int, seed: int) -> int:
    """A heap of what came out of the hole. **GRAVEL IS A CRUST AND NOTHING ELSE (rule 13)** -
    there is none in here, because a falling block over a heap with a soft edge is a hole."""
    n = 0
    for dv in range(-r, r + 1):
        for du in range(-r, r + 1):
            d = math.hypot(dv, du) / max(1.0, float(r))
            hh = int(h * max(0.0, 1.0 - d) ** 0.85 * (0.72 + 0.5 * hash01(v + dv, u + du, 91, seed)))
            if hh <= 0:
                continue
            a, b = v + dv, u + du
            y = g.seat(a, b)
            if y is None:
                continue
            for k in range(hh):
                if not g.free(a, b, y + k):
                    continue
                key = "rock" if hash01(a, b, 92 + k, seed) < 0.62 else "rock_c"
                n += int(lot.put(a, y + k, b, PAL[key]))
    return n


# --------------------------------------------------------------------------- build


def build(cfg: dict, donors=None) -> Canvas:
    p = {**SEAM, **(cfg or {})}
    kind = str(p.get("kind"))
    if kind not in ("fracture", "yard", "field"):
        raise ValueError(f"unknown seam kind {kind!r}; have fracture | yard | field")
    if not p.get("lot"):
        raise ValueError("the seam needs its measured lot: lot: [dv, du]")
    if not p.get("under"):
        raise ValueError("the seam reads the world it is verified against: under: <capture>")
    if not p.get("axis"):
        raise ValueError("the seam needs its own line: axis: [v0, u0, v1, u1]")

    dv, du = int(p["lot"][0]), int(p["lot"][1])
    seed = int(p.get("seed", 0))
    c = Canvas(dv, int(p.get("sy") or 40), du, donors)
    lot = _Lot(c, dv, du, seed=seed)
    anchor = [int(x) for x in p["anchor"]]
    at_v, at_u = (int(x) for x in (p.get("at") or (0, 0)))
    ctx = Ctx(p["under"])
    box = (anchor[0] + at_v - 2, anchor[0] + at_v + dv + 1,
           anchor[1] - 3, anchor[1] + int(p.get("sy") or 40),
           anchor[2] + at_u - 2, anchor[2] + at_u + du + 1)
    g = _Deck(ctx, anchor, dv, du, (at_v, at_u), int(p.get("clear", 1)),
              keep_out=p.get("keep_out") or (), mine=shipped_cells(p.get("previous")),
              surface=surface_cells(p.get("off_limits") or (), box))

    parts: dict = {}
    # ORDER IS LOAD-BEARING. The route and the built ground go in FIRST and the seam is swept
    # over what is left, because every placement here refuses an occupied cell - so "the walk is
    # never taken by a shard" is a property of the order rather than of a check somebody has to
    # remember. It is the claim row's own rule.
    parts["walk"] = _walk(lot, g, p, seed)
    if kind == "yard":
        parts["cuts"] = [_bench(lot, g, spec, seed, crystal=True) for spec in (p.get("cuts") or ())]
        for spec in (p.get("cuts") or ()):
            parts.setdefault("cut_steps", 0)
            parts["cut_steps"] += _steps(lot, g, spec)
        parts["gantry"] = _gantry(lot, g, p, seed)
        parts["stacks"] = sum(_stack(lot, g, int(a), int(b), seed) for a, b in (p.get("stacks") or ()))
    if kind == "field" and p.get("bank"):
        spec = dict(p["bank"])
        spec.setdefault("walk", True)
        parts["bank"] = _bench(lot, g, spec, seed)
        parts["bank_steps"] = _steps(lot, g, spec)
    parts["spoil"] = sum(_spoil(lot, g, int(a), int(b), int(r), int(h), seed)
                         for a, b, r, h in (p.get("spoil") or ()))
    # THE SHARDS FIRST AND THE TRACE AFTER THEM. Every placement here refuses an occupied cell,
    # so laid first the line would win the cells the feet wanted and the outcrops would come out
    # standing in a gap in their own seam. It is the claim row's rule: the order is the check.
    parts["seam"] = _sweep(lot, g, p, seed)
    parts["trace"] = _trace(lot, g, p, seed)
    if kind == "fracture":
        parts["lookout"] = _lookout(lot, g, p, seed)

    c.world_origin = (anchor[0] + at_v, anchor[1], anchor[2] + at_u)
    c.meta = {
        "kind": f"seam_{kind}",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "prismworks",
        "facing": "west",
        "profile_axis": "u",
        "signs": lot.signs,
        "stairs": lot.stairs,
        "refused": lot.refused,
        "parts": parts,
        "contract": _CONTRACT[kind],
    }
    return c


_CONTRACT = {
    "fracture": (
        "the Prism Reach, which was 96.3% ankle height and whose only content was the bare floor "
        "of a building that moved to the rim: the crystal seam breaking through the plate, "
        "growing from splinters at the Midway edge to full shards at the Prismworks threshold, "
        "with a lane off the spine through it to a note-block rail among the biggest of them. "
        "Nothing over 30 courses, so the well's collar keeps the land's silhouette."),
    "yard": (
        "the ground behind the Foundry Gate, which no module ever built: the cutting yard where "
        "the seam was taken out - benched faces with the vein showing in section, stacked blanks "
        "on their pallets, spoil, and a gantry line running to the collar and stopping where the "
        "mouth begins. It is what explains a 110-wide hole."),
    "field": (
        "Prismworks column C, 69% free ground: the seam at full size east of the mouth, and a "
        "raked bank you climb to look down into it over the gallery's own parapet."),
}

