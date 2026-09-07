"""Can a printer actually REACH every cell of this design?

Jack: *"a lot of the schematic has blocks that are diagonal to each other but hollow, meaning
it's impossible to print on them since there's nothing attached to any one side of them ...
they may have a line of things, but the entire line is diagonal so nothing reaches it when
printed below or from above."*

A printer places a block by CLICKING A FACE of something already standing. So a cell is printable
only when a FACE-neighbour - never a corner - is either a world block or another design cell that
has itself been placed. That makes printability a closure over the design's own **6-connectivity**,
seeded by the world, and it is a different question from every check this project already had:
`audit.check_supports` asks whether a block can EXIST, `pipeline._floating` asks whether a cell has
anything under it, and `analyze` asks which material can go in TODAY. None of them asks whether the
chain ever arrives.

**A DIAGONAL JOIN IS NOT A JOIN, AND ONE OF THEM ORPHANS EVERYTHING BEHIND IT.** Measured on the
shipped `Park Complete`: 18,721 cells could never be printed, and **16,062 of those were orphaned by
a diagonal** - 14,393 being the undercrypt, cut off from the rest of the park because every contact
between them is corner-to-corner. A handful of blocks in the right place returns the whole room.
That asymmetry is the reason this is a pass rather than something to eyeball: the fault is tiny and
the damage is not.

    python -m mcbuild printable "Park Complete" --world parkworld
    python -m mcbuild printable "Park Complete" --world parkworld --fix

**A STITCH IS A CORNER FILL, NOT A SCAFFOLD.** It only ever writes into a cell EMPTY in both the
design and the world, between cells the design already has - the same corner fill `squid._core` and
the arc stair's stringers make by hand, applied where nobody remembered to. Its material is taken
from what already touches it, so a stitch cannot introduce a block the design was not already
spending. A cell with nothing within reach is REPORTED instead: that one wants a pillar built out to
it, which is a human with a stack of dirt and not something to invent here.
"""
from __future__ import annotations

import collections
from dataclasses import dataclass, field

from . import blocks, coop, scan
from .analyze import clickable, item_of

FACES = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
STEPS26 = tuple((a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)
                if (a, b, c) != (0, 0, 0))

#: How far a stitch may reach through empty space. A two-axis diagonal needs ONE cell and a
#: three-axis one needs TWO, so 2 closes every corner join there is. More than that is a bridge,
#: which is a scaffold wearing a stitch's clothes and belongs to a person, not to this pass.
REACH = 2

#: Things placed against a FLUID or a plant rather than against a block face - a lily pad goes on
#: water, a sea pickle on a bed the water covers, a vine on a leaf. The closure cannot chain through
#: any of them, and that is right, but calling them "unprintable masses" would bury the one finding
#: that matters under two thousand single cells of pond dressing. Reported apart, never stitched:
#: a solid block filled into a pond is not a repair, it is a filled pond.
DECOR = {"water", "lava", "lily_pad", "seagrass", "tall_seagrass", "kelp", "kelp_plant",
         "sea_pickle", "vine", "glow_lichen", "sculk_vein", "moss_carpet", "cave_vines",
         "cave_vines_plant", "hanging_roots", "big_dripleaf", "small_dripleaf"}


def _at(p, steps=FACES):
    x, y, z = p
    return [(x + a, y + b, z + c) for a, b, c in steps]


@dataclass
class Clump:
    """Cells that cannot be printed, grouped by touching AT ALL - corners included, because a
    diagonal chain is one object to a reader even though it is many to a printer."""
    cells: list
    reason: str = ""

    @property
    def n(self) -> int:
        return len(self.cells)

    @property
    def box(self) -> tuple:
        xs = [p[0] for p in self.cells]
        ys = [p[1] for p in self.cells]
        zs = [p[2] for p in self.cells]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def material(self, cells: dict) -> str:
        return collections.Counter(cells[p] for p in self.cells).most_common(1)[0][0]


@dataclass
class Survey:
    design: str
    world: str | None = None
    total: int = 0
    reachable: int = 0
    seeds: int = 0
    orphans: set = field(default_factory=set)
    by_diagonal: set = field(default_factory=set)   # orphans a corner fill would return
    stitches: dict = field(default_factory=dict)    # (x,y,z) -> block name to add
    unfixable: list = field(default_factory=list)   # list[Clump]: nothing within reach
    in_walkable: int = 0          # stitches that landed where a player could have stood
    visible: int = 0              # stitches with at least one face to open air
    islands: int = 0              # separate printing islands, when there is no world to seed from
    cells: dict = field(default_factory=dict, repr=False)

    @property
    def ok(self) -> bool:
        return not self.orphans

    @property
    def returned(self) -> int:
        """Cells the stitch would make printable."""
        return len(self.orphans) - sum(c.n for c in self.unfixable)

    def report(self, top: int = 8) -> str:
        w = f" vs {self.world}" if self.world else " (design alone)"
        if self.ok:
            return f"{self.design}{w}: all {self.total} cells printable"
        head = (f"{self.seeds} seeded by the world" if self.seeds
                else f"{self.islands} separate printing islands")
        lines = [f"{self.design}{w}: {self.total} cells, {head}",
                 f"  UNPRINTABLE {len(self.orphans)}"
                 f" ({100.0 * len(self.orphans) / max(1, self.total):.1f}%)"
                 f" - {len(self.by_diagonal)} of them orphaned by a DIAGONAL join"]
        if self.stitches:
            mats = collections.Counter(self.stitches.values())
            lines.append(f"  a corner fill of {len(self.stitches)} blocks returns {self.returned}:"
                         + " " + ", ".join(f"{k} x{v}" for k, v in mats.most_common(6)))
            lines.append(f"  {len(self.stitches) - self.visible} of them are buried inside a mass"
                         f" (invisible); {self.visible} show a face")
            if self.in_walkable:
                lines.append(f"  {self.in_walkable} of them land where a player could have stood"
                             f" - check the walk before shipping")
        if self.unfixable:
            hard, soft = self.split_unfixable()
            if hard:
                n = sum(c.n for c in hard)
                lines.append(f"  STILL UNREACHABLE: {n} cells in {len(hard)} masses - nothing"
                             f" within {REACH} of them, so each wants a pillar built out to it")
                for c in hard[:top]:
                    (x0, y0, z0), (x1, y1, z1) = c.box
                    lines.append(f"    {c.n:6d}  X{x0}..{x1} Y{y0}..{y1} Z{z0}..{z1}"
                                 f"  {c.material(self.cells)}")
            if soft:
                n = sum(c.n for c in soft)
                lines.append(f"  plus {n} cells of pond and plant dressing in {len(soft)} pieces -"
                             f" placed against water or a leaf, never against a block face")
        return "\n".join(lines)

    def split_unfixable(self) -> tuple[list, list]:
        """(masses, dressing). A mass is a real hole in the print; dressing is a lily pad, and
        filling a solid block into a pond to reach one is not a repair, it is a filled pond."""
        hard, soft = [], []
        for c in self.unfixable:
            (soft if all(self.cells[p] in DECOR for p in c.cells) else hard).append(c)
        return hard, soft


def clumps(cells) -> list:
    rest, out = set(cells), []
    while rest:
        seed = rest.pop()
        stack, group = [seed], [seed]
        while stack:
            for n in _at(stack.pop(), STEPS26):
                if n in rest:
                    rest.discard(n)
                    group.append(n)
                    stack.append(n)
        out.append(Clump(group))
    out.sort(key=lambda c: -c.n)
    return out


def _grow(standing: set, queue, cells: dict, extra: dict) -> set:
    """Face-closure. A cell may be placed against anything standing; a CLICKABLE cell that has been
    placed is itself standing. A carpet, a vine or water is placeable and carries nothing onward,
    which is the whole reason a line of them cannot reach anywhere."""
    while queue:
        for n in _at(queue.popleft()):
            if n in standing:
                continue
            name = cells.get(n) or extra.get(n)
            if name is None:
                continue
            standing.add(n)
            if clickable(name):
                queue.append(n)
    return standing


def closure(cells: dict, world_click: set, *, steps=FACES, extra: dict | None = None) -> set:
    """Every design cell a printer can arrive at, starting from the world."""
    extra = extra or {}
    everything = {**cells, **extra} if extra else cells
    seeds = [p for p in everything if any(n in world_click for n in _at(p, steps))]
    placed = set(seeds)
    q = collections.deque(p for p in seeds if clickable(everything[p]))
    if steps is FACES:
        return _grow(placed, q, cells, extra)
    while q:                                  # the 26-connected variant, for measuring the cost
        for n in _at(q.popleft(), steps):
            if n in placed or n not in everything:
                continue
            placed.add(n)
            if clickable(everything[n]):
                q.append(n)
    return placed


def fill_material(p, cells: dict, stitches: dict) -> str | None:
    """What a corner fill is made of: the commonest CLICKABLE, non-falling material already touching
    it - face-neighbours first, then corners. Never invented, so a stitch cannot introduce a block
    the design was not already spending, and cannot pour sand into open air (rule 13)."""
    for step in (FACES, STEPS26):
        near = collections.Counter()
        for n in _at(p, step):
            name = cells.get(n) or stitches.get(n)
            if name and clickable(name) and not blocks.falls(name):
                near[name] += 1
        if near:
            return near.most_common(1)[0][0]
    return None


def standable(p, cells: dict, world_occupied: set, stitches: dict) -> bool:
    """Somewhere a player could be standing: something solid under it and two clear courses over.

    A corner fill that lands in one of these is a post in a doorway - the fault this project has
    now shipped three times over (a timber set on a live rail, an adit's post bricking up its own
    corridor, two pines in the one walk a module exists to carry). It is a PREFERENCE and not a
    refusal, because a join that can only be closed through a walkable cell still has to be closed;
    what the count buys is knowing when that happened.
    """
    x, y, z = p
    below = cells.get((x, y - 1, z)) or stitches.get((x, y - 1, z))
    if not ((x, y - 1, z) in world_occupied or (below is not None and clickable(below))):
        return False
    for dy in (1, 2):
        q = (x, y + dy, z)
        if q in cells or q in stitches or q in world_occupied:
            return False
    return True


def exposure(p, cells: dict, world_occupied: set, stitches: dict) -> int:
    """How many of a cell's six faces are open air - which is how much of it anyone can SEE.

    Jack: *"should also pretty much always be invisible to the user, since it's placed on the
    inside of hollow objects."* That is the difference between a repair and a blemish, and it is
    the one thing about a stitch a render CAN judge, so it is scored rather than hoped for: 0 means
    the cell is buried inside a mass and nobody will ever look at it.
    """
    n = 0
    for q in _at(p):
        if q not in cells and q not in world_occupied and q not in stitches:
            n += 1
    return n


def tucked(p, cells: dict, stitches: dict) -> bool:
    """Is there already a block directly overhead? Then this fill is a STRINGER - the course under
    a tread, which every flight in this project builds by hand - rather than a bump laid on top of
    a finished surface. A plan view never sees it and a walker treads on the block above it."""
    x, y, z = p
    q = (x, y + 1, z)
    return q in cells or q in stitches


def _routes(start, cells: dict, world_occupied: set, stitches: dict, reach: int):
    """Routes of EMPTY cells, at most `reach` long, from `start` to something the design has.

    Empty means empty in BOTH the design and the world: a stitch never covers anything, which is
    the one property that makes it safe to add to a build somebody is halfway through."""
    q = collections.deque([(start, ())])
    seen = {start}
    while q:
        here, path = q.popleft()
        for n in _at(here):
            if n in seen:
                continue
            seen.add(n)
            if n in cells or n in stitches:
                if path:
                    yield path, n
                continue
            if n in world_occupied or len(path) >= reach:
                continue
            q.append((n, path + (n,)))


def components(cells: dict) -> list:
    """The design's own printing ISLANDS: sets of cells joined face to face through material a
    printer can build on. Each island past the first costs a block placed by hand, so their number
    is what "can I print this?" actually comes down to when there is no world to start from."""
    out: list = []
    seen: set = set()
    for p in cells:
        if p in seen or not clickable(cells[p]):
            continue
        group, q = {p}, collections.deque([p])
        seen.add(p)
        while q:
            for n in _at(q.popleft()):
                if n in seen or n not in cells:
                    continue
                seen.add(n)
                group.add(n)
                if clickable(cells[n]):
                    q.append(n)
        out.append(group)
    for p in cells:                     # a lone carpet or vine touching nothing is its own island
        if p not in seen:
            out.append({p})
            seen.add(p)
    out.sort(key=len, reverse=True)
    return out


def load_cells(name: str) -> dict:
    """A design or capture as {(x, y, z): item}, in WORLD coordinates."""
    g = coop.Grid(scan.load(name))
    return {p: item_of(s) for p, s in g.cells()}


def survey(design: str, world: str | None = None, *, reach: int = REACH,
           stitch: bool = True, cells: dict | None = None,
           world_cells: dict | None = None) -> Survey:
    """Measure, and unless told otherwise work out the corner fills that would fix it."""
    cells = dict(cells) if cells is not None else load_cells(design)
    wc = world_cells if world_cells is not None else (load_cells(world) if world else {})
    world_occupied = set(wc)
    world_click = {p for p, n in wc.items() if clickable(n)}

    s = Survey(design=design, world=world, total=len(cells), cells=cells)
    s.seeds = sum(1 for p in cells if any(n in world_click for n in _at(p)))
    if world_click:
        placed = closure(cells, world_click)
        diag_placed = closure(cells, world_click, steps=STEPS26)
    else:
        # NO WORLD: you start somewhere, and the sane somewhere is the biggest mass. Everything
        # else is an island needing a block placed by hand, which is the same fault measured
        # without a capture to hand - and the number a generator's own test can assert.
        comps = components(cells)
        placed = set(comps[0]) if comps else set()
        s.islands = len(comps)
        seed_click = {n for p in placed if clickable(cells[p]) for n in _at(p, STEPS26)}
        diag_placed = closure(cells, seed_click, steps=STEPS26)
    s.reachable = len(placed)
    s.orphans = set(cells) - placed
    if not s.orphans or not stitch:
        s.by_diagonal = s.orphans - (set(cells) - diag_placed) if s.orphans else set()
        return s
    s.by_diagonal = s.orphans - (set(cells) - diag_placed)

    # ---- the corner fills ---------------------------------------------------------------------
    # Grow outward from what stands: for every route of empty cells leaving the standing mass and
    # arriving at an orphan the printer could then build on, fill it. Re-grown INCREMENTALLY - a
    # stitch that opens a room lets the room carry itself onward without another full closure, and
    # a full closure per stitch on a park-sized design is minutes rather than seconds.
    stitches: dict = {}
    blocked_walk = [0]
    seen_faces = [0]
    frontier = [p for p in placed if clickable(cells[p])]
    while frontier:
        added: list = []
        for p in frontier:
            # Every route this cell offers, then the CHEAPEST: fewest blocks, and among those the
            # one that blocks the fewest places a player could stand.
            options = [(path, end) for path, end in
                       _routes(p, cells, world_occupied, stitches, reach)
                       if end not in placed and end in cells and clickable(cells[end])]
            if not options:
                continue
            # Cheapest first, then INVISIBLE. Of the two corners that close a diagonal step, one
            # sits UNDER the upper block and one sits ON TOP of the lower one: the first reads as a
            # stringer - the thing the arc stair builds by hand under every slab tread - and the
            # second is a lump on a finished surface. So tucked beats exposed, exposed beats
            # standing room, and a route that fills nobody's floor beats one that does.
            options.sort(key=lambda o: (
                len(o[0]),
                -sum(tucked(c, cells, stitches) for c in o[0]),
                sum(exposure(c, cells, world_occupied, stitches) for c in o[0]),
                sum(standable(c, cells, world_occupied, stitches) for c in o[0])))
            for path, _end in options:
                pending = dict(stitches)          # never half-written: a route fills or it does not
                for c in path:
                    mat = fill_material(c, cells, pending)
                    if mat is None:
                        break
                    pending[c] = mat
                if len(pending) != len(stitches) + len(path):
                    continue
                blocked_walk[0] += sum(standable(c, cells, world_occupied, stitches) for c in path)
                seen_faces[0] += sum(min(1, exposure(c, cells, world_occupied, stitches))
                                     for c in path)
                added.extend(path)
                stitches = pending
                break
        if not added:
            break
        placed |= set(added)
        placed = _grow(placed, collections.deque(added), cells, stitches)
        frontier = [p for p in placed if p in cells and clickable(cells[p])]

    s.stitches = stitches
    s.in_walkable = blocked_walk[0]
    s.visible = seen_faces[0]
    for c in clumps(set(cells) - placed):
        c.reason = "nothing within reach through empty space"
        s.unfixable.append(c)
    return s


def model_cells(model, origin) -> dict:
    """A live `schem.Model` as {(x, y, z): item}, in WORLD coordinates."""
    ox, oy, oz = origin
    names = model.names
    ids = model.ids
    out = {}
    ys, zs, xs = model.solid().nonzero()
    for y, z, x in zip(ys, zs, xs):
        out[(int(x) + ox, int(y) + oy, int(z) + oz)] = item_of(names[ids[y, z, x]])
    return out


def stitch_model(model, origin, *, world_cells: dict | None = None, reach: int = REACH,
                 name: str = "model", rounds: int = 3) -> tuple[Survey, int]:
    """Survey a model in memory and write the corner fills straight into it.

    This is the form a COMPOSITE needs. `Park Complete` is assembled from ~200 module artifacts and
    a diagonal break between two of them belongs to neither, so no generator can see it and no
    per-design pass can fix it - which is also why this runs at the moment the composite is written
    rather than being a command somebody remembers. A step that has to be remembered is a step that
    gets lost, and this project has written that down about `carve_for` already.

    A FILL CAN OPEN A JOIN OF ITS OWN, so this runs to a FIXPOINT rather than once: a corner cell
    written this round is a new face for the round after it, and one pass therefore leaves a short
    tail of breaks that a reader would have to notice and close by hand. `rounds` bounds the work;
    it stops as soon as a round writes nothing. The Survey returned is the FIRST one - the honest
    measurement of the composite AS ASSEMBLED - while the count is every fill across every round.
    """
    ox, oy, oz = origin
    sy, sz, sx = model.ids.shape
    first: Survey | None = None
    written = 0
    for _ in range(max(1, rounds)):
        cells = model_cells(model, origin)
        s = survey(name, None, reach=reach, cells=cells, world_cells=world_cells or {})
        if first is None:
            first = s
        wrote = 0
        for (x, y, z), block in sorted(s.stitches.items()):
            i, j, k = y - oy, z - oz, x - ox
            if not (0 <= i < sy and 0 <= j < sz and 0 <= k < sx):
                continue
            if model.ids[i, j, k] != 0:
                continue
            model.ids[i, j, k] = model.ensure_state(block)
            wrote += 1
        written += wrote
        if not wrote:
            break
    return first, written


def apply(design: str, stitches: dict, *, out: str | None = None) -> tuple[int, int, str]:
    """Write the corner fills into the design's own litematic, at its own origin.

    Returns (written, outside, sidecar path). A stitch outside the model's box is DROPPED and
    COUNTED rather than growing the box: a design padded to `origin_lock` has room for every corner
    between its own cells by construction, so one landing outside is a fault in the survey - not a
    reason to move an origin every placement in the world is already aligned to.
    """
    s = scan.load(design)
    m = s.model
    ox, oy, oz = s.origin
    sy, sz, sx = m.ids.shape
    written = outside = 0
    for (x, y, z), name in sorted(stitches.items()):
        i, j, k = y - oy, z - oz, x - ox
        if not (0 <= i < sy and 0 <= j < sz and 0 <= k < sx):
            outside += 1
            continue
        if m.ids[i, j, k] != 0:                       # never cover: something already claims it
            continue
        m.ids[i, j, k] = m.ensure_state(name)
        written += 1
    lit = out or s.litematic_path
    meta = dict(s.meta)
    meta["stitched"] = int(meta.get("stitched", 0)) + written
    return written, outside, scan.save_pair(lit, m, meta, name=meta.get("name"))
