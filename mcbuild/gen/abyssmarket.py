"""THE ABYSS MARKET - the inside of the squid, and the reason to go down there.

Jack: "the squid is so massive and since its hollow we can technically DESIGN the interior ...
make it a place that players want to go to (and maybe buy things from a shop)."

THE CAVITY WAS NOT DESIGNED, IT WAS A SIDE EFFECT, AND IT IS THE BIGGEST INTERIOR ON THE
ISLAND. `configs/abyss_squid.yaml` hollows the animal at `shell: 2` on the argument that mobs
do not spawn here, and records the trade as "66,000 blocks nobody would ever have seen".
Measured off the SHIPPED artifact rather than re-derived from the generator's parameters:

    ONE connected void of 54,994 cells, 250 blocks long   Z80494 -> Z80743
    the floor rises                                       Y104 -> Y145
    the tube runs 11-15 wide at head height, 17-21 higher, 14-20 courses tall
    plus TWO sealed 107-cell pods at Y172-182             one inside each EYE

That is bigger than most of the park's own lands, and every cell of it is already paid for.

THE ACCESS SOLVED ITSELF AND THE KEEP-OUT IS UNTOUCHED. The squid's config exists around one
safety rule - nothing may enter r56 of the Prism Well's fall column, because a surface in a
column a runner falls eighty-six courses down does not save one, it strands one. So the
entrance does not come off the parkour at all. Prismworks' own floor is Y202 over the animal;
a shaft at X97600 Z80665 is r150 from the well, which is nowhere near it.

    park floor Y202 -> 45 courses of open void -> a TWO-CELL shell -> the cavity at Y155

and it lands on X97600, which is the animal's own mirror axis, at the COLLAR where the mantle
meets the head - so the arrival is a junction with somewhere to go in both directions rather
than the end of a corridor.

THE SITE WAS SWEPT AND THE FIRST ANSWER WAS A DRAIN. The best-scoring shaft column by drop
alone is X97600 Z80704, two cells of shell and 42 courses. It is under a POND: 336 water cells
in the 22x22 around it, with the surface at Y202. Cutting a shaft through a pond floor drops
that pond forty-two courses into a sealed animal, and this repo has already drained 199,959
cells to Y-1908 once doing something less obviously dangerous. `_dry` is why the search rejects
any column within five of standing water, and it is not a nicety - it is the difference between
an entrance and flooding the whole design.

THE SECOND ANSWER WAS A CHIMNEY. The next-best column, X97583 Z80739, reports a cavity ceiling
at Y171 under a two-cell shell and looks perfect. That cavity is a TWO-WIDE VERTICAL SLOT - the
inside of an arm base, a hollow tube running up into the crown - and a shaft into it lands a
visitor in a chimney they cannot get out of. A landing cell is checked for ROOM (>=100 cavity
cells in a 7x7x5 box around it), never merely for being cavity, and that check is the whole
difference between the two sites.

THE PALETTE IS PRISMWORKS' SALVAGE CREW, AND IT IS A MEASURED LADDER. The fiction is that the
animal is long dead and a trading post has grown inside it, so the architecture is the copper
and deepslate of the land DIRECTLY OVERHEAD, against the squid's own red flesh and bone ribs.
CLAUDE.md records four separate times that this economy "has no value contrast", and all four
searched INSIDE one material family, where a ladder cannot exist by construction. Across
families, measured with `blocks.color(..., "side")`:

    polished_blackstone_bricks  45   the plinth and the shadow line
    deepslate_bricks            71   the field
    spruce_planks               89   the deck
    cut_copper                 123   THE STRUCTURE - and a hue flip, (191,107,81) against grey
    smooth_stone               159   the pale course
    ochre_froglight            232   the light, and the animal's own

Steps of 26, 18, 34, 36, 73, against the ~15 below which a course stops being a line. And the
important one is copper against the FLESH: `mangrove_planks` is 67 and `red_wool` 65, so
deepslate at 71 would vanish into the walls it is bolted to. Copper is 56 clear of both and the
only warm hue in a cold room.

THE COPPER IS UNWAXED, ON JACK'S WORD, AND IT WILL OXIDISE - WHICH IS THE POINT. A derelict
that goes green inside a dead animal is the story, and the palette survives the journey rather
than merely tolerating it, which was the thing to check before agreeing:

    cut_copper           123  (191,107,81)     fresh: warm, 56 clear of the flesh
    exposed_cut_copper   128  (155,122,101)
    weathered_copper     140  (108,153,110)
    oxidized_cut_copper  136  ( 80,154,126)    green: 71 clear of the flesh

The contrast RISES, 56 -> 71, and green against red flesh is complementary where warm against
warm was not. Oxidation is per-block and random, so it arrives patchy through the two middle
stages, which is what makes it read as age rather than as a repaint. Nothing here is waxed, so
nothing here is pinned to one stage.

This design briefly declared `expensive_allowance: 94` for its `copper_block` posts, because
the economy table had copper filed among the ore blocks and had never measured it. Jack:
"copper is not expensive, we can use it" - and the table said so itself, pricing `copper_block`
above the `cut_copper` that is STONECUT FROM IT one block into four. Corrected in
`palette.EXPENSIVE_NAMES`; the whole family is cheap and there is nothing to declare.

NOT ONE CELL OF THE ANIMAL IS TAKEN. Every placement goes through `_W.put`, which refuses any
cell the squid's own artifact owns and counts the refusal, so `overlap 0` is a property of the
construction rather than a number to hope for - the Wyrm Gate's rule, and the reason a design
that hangs inside another one can be regenerated under it. The dig list is the shaft mouth
only: two courses of Prismworks paving and two courses of the squid's skin, 3x3, thirty-six
cells, and nothing else in the animal is ever broken.

LIGHT IS THE WHOLE PROBLEM AND IT IS PROPAGATED, NOT ASSUMED. The cavity is sealed and there is
no sky light anywhere under the park at any hour, so an unlit deck is not a dim deck, it is an
invisible one. The lamps are `ochre_froglight` set FLUSH INTO the deck - Jack's own idiom, the
one full-block light witnessed in this world, and the one that cannot be knocked off a walkway
- and `tests/test_abyss_market.py` re-runs the propagation over the finished composite rather
than trusting the spacing.
"""
from __future__ import annotations

import collections
from collections import deque

import numpy as np

from .canvas import Canvas

SIGN_W = 15                       # a sign line clips MID-WORD past this and only a screenshot shows it

MARKET = {
    "squid": "out/Abyss Squid.litematic",
    "park": "out/Park Complete.litematic",

    # THE SHAFT. X97600 is the animal's own mirror axis; Z80665 is the collar. Dry paved
    # Prismworks plaza above (smooth_stone / stone_bricks, Y202-203, nothing over Y204),
    # r150 from the Prism Well, two cells of shell, and a roomy landing.
    "shaft": [97600, 80665],
    "surface": 204,               # the course a visitor stands on at the wellhead
    "park_floor": [202, 203],     # the two Prismworks courses the mouth cuts

    "walk_w": 7,                  # the deck's width down the arcade
    "headroom": 3,                # courses a deck must leave over itself
    "lamp_every": 6,              # froglight spacing in the deck
    "mark_every": 22,             # a lay-by and a distance sign down the arcade
    "prow_w": 9,                  # the prow's half-width; the cavity allows ten
    "window_every": 1,            # try every course; the dig budget is the real cap
    "window_budget": 60,          # HARD: cells of the animal a window may cut
    "rib_every": 9,               # copper braces on the animal's own section
    "light_min": 8,               # block light every walkable cell of the deck must reach
    "light_sep": 7,               # how far apart the solver's own lamps may land
}

# ---------------------------------------------------------------------------------------------
# the zones, in WORLD Z. Every boundary is read off the profile in the docstring above rather
# than chosen: the pinch at Z80674 is where the cavity genuinely closes to a 13-wide oval
# floating eight courses over the mantle floor, which is the oesophagus and is a doorway.
TAIL = (80500, 80518)             # the tip: too low to walk under Z80506
SOUND = (80518, 80572)            # the fin band - 45-49 across at floor+5, the widest room
ARCADE = (80572, 80658)           # the long gallery, floor Y110 -> Y136
COLLAR = (80658, 80672)           # the arrival junction, under the shaft
GULLET = (80668, 80684)           # the throat, floor Y142-154 - a stair, not a doorway
BAZAAR = (80684, 80702)           # the head chamber: floor Y144, ceiling Y153-157
PROW = (80702, 80713)             # the front of the head - see `_prow`

XC = 97600                        # the animal's mirror axis, INTEGER, so the fit-out mirrors exactly

# a wall sign hangs on the block OPPOSITE its facing: `facing` is the way the text looks.
_BEHIND = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}


# ---------------------------------------------------------------------------------------------


def _fit(lines):
    """Sign lines, RAISED rather than truncated.

    This park has shipped `MINE CART ESCAP`, `and prize windo` and `ore from the ad`, all four
    from different routes, and every offline check passes a clipped sign: the block is legal,
    supported, affordable and in 1.19, and `render3d` draws it identically to a whole one. The
    damage shows only in a screenshot of the placed build.
    """
    out = []
    for s in lines:
        if len(s) > SIGN_W:
            raise ValueError(f"sign line over {SIGN_W} chars and it would clip mid-word: {s!r}")
        out.append(s)
    return tuple(out)


def _post_sign(w, s, x, y, z, facing, text, back=()):
    """A sign AND the thing it hangs on.

    `_W.sign` refuses a board with nothing behind it, which is right and which turns every
    hopeful sign into silence. Where a design genuinely wants a marker in open floor - the
    tail, the bell - the backing is part of the marker and is built with it.
    """
    dx, dz = _BEHIND[facing]
    if not w.has(x + dx, y, z + dz):
        w.put(x + dx, y, z + dz, s["copper_b"])
    return w.sign(x, y, z, facing, s[f"sign_{facing}"], text, back)


class Cave:
    """The sealed cavity of the SHIPPED squid, measured off the artifact.

    NOT re-derived from `squid.SQUID`. The animal that is placed is the one in `out/`, its
    hollowing was done by the pipeline's `finish.hollow` rather than by the generator, and a
    fit-out computed from the parameters would be a fit-out for a different animal the day
    anybody re-tunes one. The same rule that makes `proportions.measure` and `rubric.score`
    share an entry point: one source, so two tools cannot drift.
    """

    def __init__(self, path: str):
        from .. import scan as scan_mod, schem
        from .. import nbt
        m = schem.load(path)
        s = scan_mod.load(str(path).replace(".litematic", ".scan.json"))
        self.origin = tuple(int(v) for v in s.origin)
        self.solid = m.ids != 0
        self.ids = m.ids
        self.names = [nbt.state_name(q) for q in m.palette]
        ny, nz, nx = self.solid.shape
        self.shape = (ny, nz, nx)

        # exterior air, flooded from every face; what is left is the sealed inside
        air = ~self.solid
        seen = np.zeros_like(air)
        dq: deque = deque()

        def seed(y, z, x):
            if air[y, z, x] and not seen[y, z, x]:
                seen[y, z, x] = True
                dq.append((y, z, x))

        for y in (0, ny - 1):
            for z in range(nz):
                for x in range(nx):
                    seed(y, z, x)
        for z in (0, nz - 1):
            for y in range(ny):
                for x in range(nx):
                    seed(y, z, x)
        for x in (0, nx - 1):
            for y in range(ny):
                for z in range(nz):
                    seed(y, z, x)
        while dq:
            y, z, x = dq.popleft()
            for dy, dz, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                a, b, c = y + dy, z + dz, x + dx
                if 0 <= a < ny and 0 <= b < nz and 0 <= c < nx and air[a, b, c] and not seen[a, b, c]:
                    seen[a, b, c] = True
                    dq.append((a, b, c))
        inside = air & ~seen

        # the biggest sealed component is the body cavity; the rest are the eye pods and
        # a scatter of two- and three-cell voids the shell closed around
        lab = np.zeros(self.solid.shape, np.int32)
        n = 0
        best, bestn = 0, 0
        for y, z, x in zip(*np.nonzero(inside)):
            if lab[y, z, x]:
                continue
            n += 1
            cnt = 0
            dq = deque([(y, z, x)])
            lab[y, z, x] = n
            while dq:
                a, b, c = dq.popleft()
                cnt += 1
                for dy, dz, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                    p, q, r = a + dy, b + dz, c + dx
                    if 0 <= p < ny and 0 <= q < nz and 0 <= r < nx and inside[p, q, r] and not lab[p, q, r]:
                        lab[p, q, r] = n
                        dq.append((p, q, r))
            if cnt > bestn:
                best, bestn = n, cnt
        self.main = lab == best
        self.inside = inside
        self.cells = int(bestn)

    # -- world-coordinate accessors -----------------------------------------------------
    def _ix(self, x, y, z):
        ox, oy, oz = self.origin
        a, b, c = y - oy, z - oz, x - ox
        ny, nz, nx = self.shape
        if 0 <= a < ny and 0 <= b < nz and 0 <= c < nx:
            return a, b, c
        return None

    def rock(self, x, y, z) -> bool:
        """Does the ANIMAL own this cell? Outside its box the answer is no, not OOB.

        `Canvas.get` returns -1 out of bounds and -1 is TRUTHY, which is the bug that painted
        a ladybird's seven spots into thin air with a clean audit behind it. A mask answering
        about an artifact has the same trap and the same fix: say what you mean.
        """
        i = self._ix(x, y, z)
        return bool(self.solid[i]) if i else False

    def cave(self, x, y, z) -> bool:
        i = self._ix(x, y, z)
        return bool(self.main[i]) if i else False

    def band(self, z, half=3):
        """The cavity's floor and ceiling on the MIDLINE band at this Z.

        Measured over X = XC +- half rather than the whole slice, because the fins spread the
        cavity forty-nine cells wide at low Y and a floor taken over the slice is the inside of
        a fin rather than the floor of the room.
        """
        ys = []
        for x in range(XC - half, XC + half + 1):
            col = [y for y in range(self.origin[1], self.origin[1] + self.shape[0]) if self.cave(x, y, z)]
            if col:
                ys.append((min(col), max(col)))
        if not ys:
            return None
        return min(a for a, _ in ys), max(b for _, b in ys)

    def span(self, z, y):
        """The contiguous run of cavity through the midline at this course, as (x0, x1)."""
        if not self.cave(XC, y, z):
            return None
        x0 = x1 = XC
        while self.cave(x0 - 1, y, z):
            x0 -= 1
        while self.cave(x1 + 1, y, z):
            x1 += 1
        return x0, x1


class _W:
    """The canvas in WORLD coordinates, refusing every cell somebody else owns.

    A design that hangs inside another one cannot be checked for overlap after the fact and
    then patched - the refusal has to be structural, or the two fight cell by cell in game and
    the loser is whoever places second. Every count is reported in the sidecar so a refusal
    that fires zero times can be told from a guard that is decorative.
    """

    def __init__(self, c: Canvas, origin, cave: Cave, park, dig: set):
        self.c, self.origin, self.cave, self.park, self.dig = c, origin, cave, park, dig
        self.yielded = 0
        self.clipped = 0
        self.n = 0

    def _l(self, x, y, z):
        ox, oy, oz = self.origin
        return x - ox, y - oy, z - oz

    def free(self, x, y, z) -> bool:
        """May this design write here? The animal and the park both win, except at the mouth."""
        # THE DIG IS CHECKED FIRST, AND THE ORDER IS THE WHOLE POINT. Written with the
        # animal's refusal above it, the exemption reached the park's paving and never the
        # squid's own skin - so the two courses of the hatch, which are the only cells of the
        # animal this design is allowed to touch, refused every rung and the climb had a
        # two-block gap exactly where it passes through the shell.
        if (x, y, z) in self.dig:
            return True
        if self.cave.rock(x, y, z):
            return False
        return not (self.park and self.park.solid_at(x, y, z))

    def put(self, x, y, z, blk) -> bool:
        x, y, z = int(x), int(y), int(z)
        if not self.free(x, y, z):
            self.yielded += 1
            return False
        lx, ly, lz = self._l(x, y, z)
        if not self.c.inb(lx, ly, lz):
            self.clipped += 1
            return False
        if self.c.get(lx, ly, lz) == 0:
            self.n += 1
        self.c.put(lx, ly, lz, blk)
        return True

    def has(self, x, y, z) -> bool:
        """Something SOLID here - ours, the animal's, or the park's."""
        if self.cave.rock(x, y, z):
            return True
        lx, ly, lz = self._l(x, y, z)
        return self.c.solid(lx, ly, lz)

    def sign(self, x, y, z, facing, blk, front, back=()):
        """A wall sign in the cell IN FRONT of its wall, its support CHECKED.

        `park._sign`'s rule, and it has caught four kinds shipping a board hung on a column
        that has an opening in it. Returns False when refused; a caller that ignores that is
        asking for a sign floating in air, which renders identically to one on a wall - and
        which the game simply refuses to place, so the line is lost with nothing to say so.

        THE FIRST VERSION OF THIS METHOD DESCRIBED THE CHECK AND DID NOT MAKE IT. Two signs
        shipped floating on the first build: the tail marker and an arcade lay-by, both in
        open air, both invisible in every render. A docstring is not a guard.
        """
        dx, dz = _BEHIND[facing]
        if not self.has(x + dx, y, z + dz):
            return False
        if not self.put(x, y, z, blk):
            return False
        lx, ly, lz = self._l(x, y, z)
        self.c.sign_text(lx, ly, lz, front=_fit(front), back=_fit(back), colour="white", glowing=True)
        return True


class _Park:
    def __init__(self, path):
        from .. import scan as scan_mod, schem
        m = schem.load(path)
        s = scan_mod.load(str(path).replace(".litematic", ".scan.json"))
        self.origin = tuple(int(v) for v in s.origin)
        self.solid = m.ids != 0
        self.shape = self.solid.shape

    def solid_at(self, x, y, z) -> bool:
        ox, oy, oz = self.origin
        a, b, c = y - oy, z - oz, x - ox
        ny, nz, nx = self.shape
        return bool(self.solid[a, b, c]) if (0 <= a < ny and 0 <= b < nz and 0 <= c < nx) else False


# ---------------------------------------------------------------------------------------------
# the build


def _states(c: Canvas):
    s = {
        "copper": c.state("cut_copper"),
        "copper_b": c.state("copper_block"),
        "deep": c.state("deepslate_bricks"),
        "dark": c.state("polished_blackstone_bricks"),
        "deck": c.state("spruce_planks"),
        "pale": c.state("smooth_stone"),
        "lamp": c.state("ochre_froglight"),
        "lichen_dn": c.raw_state("glow_lichen", down="true", up="false", north="false",
                                 south="false", east="false", west="false", waterlogged="false"),
        "ladder_n": c.raw_state("ladder", facing="north", waterlogged="false"),
        "ladder_s": c.raw_state("ladder", facing="south", waterlogged="false"),
        "fence": c.state("dark_oak_fence"),
        "bell": c.raw_state("bell", facing="north", attachment="ceiling", powered="false"),
        "lantern": c.raw_state("lantern", hanging="true", waterlogged="false"),
        "lant_up": c.raw_state("lantern", hanging="false", waterlogged="false"),
        # A CEILING EIGHTEEN COURSES UP IS NOT A CEILING A LANTERN CAN HANG FROM. The
        # gullet's climb is one cell wide with the animal's rock either side, so the light
        # pass has no floor to set a lamp into and no near roof to hang one from - and a
        # lantern on the crown eighteen above a step arrives at nothing. It is `iron_chain`
        # in 26.x, not `chain`.
        "chain": c.raw_state("iron_chain", axis="y", waterlogged="false"),
    }
    for d in ("north", "south", "east", "west"):
        s[f"stair_{d}"] = c.raw_state("cut_copper_stairs", facing=d, half="bottom",
                                      shape="straight", waterlogged="false")
        s[f"stair_t_{d}"] = c.raw_state("cut_copper_stairs", facing=d, half="top",
                                        shape="straight", waterlogged="false")
        s[f"sign_{d}"] = c.raw_state("spruce_wall_sign", facing=d, waterlogged="false")
    s["slab"] = c.raw_state("cut_copper_slab", type="bottom", waterlogged="false")
    s["slab_t"] = c.raw_state("cut_copper_slab", type="top", waterlogged="false")
    s["deck_slab"] = c.raw_state("spruce_slab", type="bottom", waterlogged="false")
    # a PANE, not a block: `black_stained_glass` is expensive here and the pane is cheap at
    # rgb(24,24,24) against the block's (25,25,25) - and six glass make sixteen panes, so this
    # one really is cheaper per unit rather than being another table error.
    s["pane"] = c.raw_state("black_stained_glass_pane", north="true", south="true",
                            east="false", west="false", waterlogged="false")
    return s


def _profile(cave: Cave, z0: int, z1: int, headroom: int):
    """The deck's height for every Z of the walk, and where it may not go.

    A deck laid on the cavity's own floor is a ramp that steps up AND down - the trough wobbles
    a course either way every few blocks - so the profile is a RUNNING MAXIMUM from the tail
    forward. That makes the whole walk downhill toward the tail by construction, which is what
    puts the payoff at the bottom, and it can never sink below the floor it rests on.
    """
    raw, deck, bad = {}, {}, []
    for z in range(z0, z1 + 1):
        b = cave.band(z)
        if not b:
            continue
        raw[z] = b
    if not raw:
        return {}, bad
    run = None
    for z in sorted(raw):
        fl, ce = raw[z]
        run = fl if run is None else max(run, fl)
        if ce - run < headroom:
            # a deck that would have to duck: leave the walk out rather than build a crawl
            bad.append(z)
            continue
        deck[z] = run
    return deck, bad


def _room_span(cave: Cave, z: int, y: int, need: int, cap: int):
    """The run of floor through the axis a body can actually STAND on, at this course.

    A raw cavity span is the wrong measurement and the fin band proves it: at Z80534 the void
    is forty-five cells across, because the fins are hollow too and their inside is a thin
    wedge that closes to nothing at the wings. Deck laid to that span puts isolated cells out
    where the ceiling is one course over the floor - a floor you cannot stand on, and eight
    free-floating clusters that only a component count can see.

    So the span is the contiguous run through XC where there are `need` clear courses ABOVE
    the deck, capped at `cap` so a room stays a room rather than a plain.
    """
    if not cave.cave(XC, y, z):
        return None

    def ok(x):
        return all(cave.cave(x, y + k, z) for k in range(1, need + 1))

    if not ok(XC):
        return None
    x0 = x1 = XC
    while x0 - 1 >= XC - cap and ok(x0 - 1):
        x0 -= 1
    while x1 + 1 <= XC + cap and ok(x1 + 1):
        x1 += 1
    return x0, x1


def _walkway(w: _W, cave: Cave, s, deck, half: int, mat=None, rail=True, every=0):
    """The deck itself: a flat causeway on the animal's own axis, stepping where the floor does.

    THE STEP IS A STAIR, NEVER A LEDGE. A one-course rise a player walks up is fine; the same
    rise with nothing to read it by is a trip. And a stair leans INTO the rise - its tall side
    is its `facing` - which our renderer draws identically either way, so it is asserted in the
    tests rather than eyeballed.
    """
    mat = mat or s["deck"]
    laid, lamps, ext = 0, 0, {}
    for z in sorted(deck):
        y = deck[z]
        sp = _room_span(cave, z, y, 2, half)
        if not sp:
            continue
        x0, x1 = sp
        for x in range(x0, x1 + 1):
            if w.put(x, y, z, mat):
                laid += 1
        ext[z] = (x0, x1)
        prev = deck.get(z - 1)
        if prev is not None and y - prev == 1:
            # a riser: the tread that carries you up faces +Z, which is `south`
            for x in range(x0, x1 + 1):
                w.put(x, prev, z - 1, s["stair_south"])
        if rail:
            for x in (x0 - 1, x1 + 1):
                if not w.has(x, y + 1, z) and w.free(x, y, z):
                    w.put(x, y, z, mat)
                    w.put(x, y + 1, z, s["fence"])
        if every and z % every == 0 and x1 - x0 >= 2:
            for x in (x0 + 1, x1 - 1):
                if w.put(x, y, z, s["lamp"]):
                    lamps += 1
    return laid, lamps, ext


def _shaft(w: _W, cave: Cave, s, sx: int, sz: int, surface: int, skin: int, cavetop: int):
    """The descent: a wellhead on the Prismworks plaza and a cased shaft down the open void.

    IT IS A LADDER, NOT A WATER COLUMN. A bubble lift is the park's own idiom and it is the one
    thing that must not be built here: the shaft ends INSIDE a sealed animal, so a column that
    leaks does not wet a floor, it fills fifty-five thousand cells. A salvage crew cutting into
    a carcass bolts a ladder to the casing, which is also what the fiction wants.
    """
    n = {"case": 0, "rung": 0, "land": 0}
    # the wellhead: an apron ON TOP of the park's own paving, so it covers nothing
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            if abs(dx) < 2 and abs(dz) < 2:
                continue
            r = max(abs(dx), abs(dz))
            w.put(sx + dx, surface, sz + dz, s["dark"] if r == 3 else s["copper"])
    # A HEADHOUSE, NOT A KERB. Four three-course posts in a Prismworks garden is a hole in the
    # paving with a rim: from anywhere on that plaza it does not announce itself, and a shop
    # nobody can find is not a shop. Five courses and a lintel ring puts it over the hedges,
    # and it is NAMED - this park has now shipped five markers pointing at retired modules and
    # a dozen boards that were silently refused, and an entrance with no board is the same
    # failure before it has even been built.
    top = surface + 6
    for dx, dz in ((-2, -2), (-2, 2), (2, -2), (2, 2)):
        for k in range(1, 6):
            w.put(sx + dx, surface + k, sz + dz, s["copper_b"])
        w.put(sx + dx, top, sz + dz, s["lamp"])
    for dx in range(-2, 3):
        for dz in (-2, 2):
            if abs(dx) < 2:
                w.put(sx + dx, top, sz + dz, s["deep"])
    for dz in range(-1, 2):
        for dx in (-2, 2):
            w.put(sx + dx, top, sz + dz, s["deep"])
    # the name, on both approaches, hung on the lintel's own posts
    for face, dz in (("north", -2), ("south", 2)):
        bx, by, bz = sx, surface + 4, sz + dz
        for k in (3, 4):
            w.put(sx - 1, surface + k, bz, s["copper"])
            w.put(sx + 1, surface + k, bz, s["copper"])
        n["sign"] = n.get("sign", 0) + int(bool(
            _post_sign(w, s, bx, by, bz + (1 if dz < 0 else -1), face,
                       ("THE ABYSS", "MARKET", "down the shaft", "45 blocks"))))

    # the casing: a 5x5 ring round a 3x3 shaft, from just under the park floor to the skin
    top = surface - 3
    for y in range(skin, top + 1):
        # A COURSE LINE, NOT A STRIPE. Four-course bands of copper against deepslate is the
        # largest hue contrast in the palette repeated at the largest pitch, and from any
        # distance the shaft read as a barber pole. One dark course in four is a string
        # course, which is what every other tower in this park draws with.
        band = s["deep"] if y % 4 == 0 else s["copper"]
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if max(abs(dx), abs(dz)) != 2:
                    continue
                if w.put(sx + dx, y, sz + dz, band):
                    n["case"] += 1
        # the ladder, on the north face of the shaft, and a landing every eleven courses
        if w.put(sx, y, sz - 1, s["ladder_s"]):
            n["rung"] += 1
        if (y - skin) % 11 == 0 and y < top - 2:
            for dx in range(-1, 2):
                if w.put(sx + dx, y, sz + 1, s["slab_t"]):
                    n["land"] += 1
            w.put(sx + 1, y + 1, sz + 1, s["lamp"])
    return n


def _rig(w: _W, cave: Cave, s, sx: int, sz: int, top: int, deck_y: int):
    """The shaft carries on INSIDE the animal, because the cavity's ceiling is not its floor.

    The hatch opens at Y155 and the collar's deck is eighteen courses under it. A shaft that
    stops at the skin is a hole a visitor falls out of; what makes it an arrival is that the
    rig hangs on down the body cavity as an open cage, so you climb down INSIDE the animal with
    its ribs either side of you, which is the best thirty seconds in the whole design.
    """
    n = 0
    for y in range(deck_y + 1, top + 1):
        for dx, dz in ((-2, -2), (-2, 2), (2, -2), (2, 2)):
            if w.put(sx + dx, y, sz + dz, s["copper_b"]):
                n += 1
        # THE LADDER NEEDS A WALL AND AN OPEN CAGE HAS NONE. Written as four posts, all
        # forty-four rungs inside the animal hung on air - which the game refuses to place,
        # so the way down would simply not have existed. The north face is closed.
        for dx in range(-1, 2):
            if w.put(sx + dx, y, sz - 2, s["deep"] if y % 4 == 0 else s["copper"]):
                n += 1
        if y % 4 == 0:
            # THE RING MUST NOT REPAINT THE SPINE. Laid over the whole north face it replaced
            # the ladder's own wall with a SLAB every fourth course - four rungs hung on half
            # a block, which the game refuses, in a shaft that is the only way down.
            for dx in range(-2, 3):
                for dz in (-2, 2):
                    if dz == -2 and abs(dx) < 2:
                        continue
                    w.put(sx + dx, y, sz + dz, s["slab"])
            for dz in range(-1, 2):
                for dx in (-2, 2):
                    w.put(sx + dx, y, sz + dz, s["slab"])
        w.put(sx, y, sz - 1, s["ladder_s"])
        if y % 8 == 0:
            w.put(sx + 1, y, sz + 1, s["lamp"])
    return n


def _climb(w: _W, s, sx: int, sz: int, y0: int, y1: int):
    """One ladder run for the WHOLE descent, placed after the two structures that carry it.

    The shaft is built above the animal and the rig below it, and each stops at its own end -
    so the two courses of skin BETWEEN them, which are the dig, had no rung at all. A climb
    with a two-block gap in the middle is not a climb, and nothing about it is visible in a
    render: a ladder that stops looks exactly like a ladder that starts.

    Returns the rungs placed and, separately, the courses it could NOT reach. A gap reported
    is a gap somebody can fix; a gap counted into a total is a gap nobody knows about.
    """
    put, gaps = 0, []
    for y in range(y0, y1 + 1):
        if not w.has(sx, y, sz - 2):
            w.put(sx, y, sz - 2, s["deep"])
        if w.put(sx, y, sz - 1, s["ladder_s"]):
            put += 1
        elif w.c.get(*w._l(sx, y, sz - 1)) == 0:
            gaps.append(y)
    return put, gaps


def _collar(w: _W, cave: Cave, s, sx: int, sz: int, deck):
    """The junction. A visitor lands here and has to be told there are two ways to go."""
    y = deck.get(sz)
    if y is None:
        return 0
    n = 0
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            if w.put(sx + dx, y, sz + dz, s["copper"] if max(abs(dx), abs(dz)) == 3 else s["deck"]):
                n += 1
    for dx, dz in ((-3, -3), (-3, 3), (3, -3), (3, 3)):
        w.put(sx + dx, y + 1, sz + dz, s["copper_b"])
        w.put(sx + dx, y + 2, sz + dz, s["lamp"])
    # the board: a post and two faces, one for each direction of travel
    px, pz = sx + 3, sz
    for k in (1, 2, 3):
        w.put(px, y + k, pz, s["copper_b"])
    w.sign(px - 1, y + 3, pz, "west", s["sign_west"],
           ("THE COLLAR", "-- north --", "the bazaar", "in the head"))
    w.sign(px, y + 3, pz - 1, "north", s["sign_north"],
           ("-- south --", "the long walk", "and the bell", "80 blocks down"))
    return n


def _gullet(w: _W, cave: Cave, s, deck):
    """The throat: a FLIGHT, because the two floors it joins are seven courses apart.

    Jack: *"theres a bunch that ... dont connect to lead to the upper areas as we progress
    towards mouth."* This was the worst of it. The mantle's deck ends at Y137 down in the
    throat's narrow notch and the head's begins at Y144 up in the wide part, and the design
    laid NOTHING between them - a seven-course wall in the middle of the walk, which a visitor
    could only pass by climbing the animal's own raw gullet.

    THE CAUSE WAS ASKING THE WRONG HEIGHT, NOT A MISSING BUILDER. `_gullet` laid its deck at
    `deck[z]` - the running-max profile, Y137 - and `_room_span` correctly refuses that,
    because at Y137 the throat is a ONE-CELL notch with no headroom. It returned None for six
    courses in a row and the builder shrugged. Measured, the cavity above is thirteen wide
    from Y140 up: there was never a wall, only a floor nobody built.

    So the gullet climbs. One course per block, meeting the head's deck exactly, and the
    treads come from `_treads` afterwards like every other step on the walk.
    """
    z0, z1 = GULLET
    n = 0
    lo = deck.get(z0)
    hi = deck.get(z1)
    if lo is None or hi is None:
        return n
    span = max(1, z1 - z0)
    y = lo
    for z in range(z0, z1 + 1):
        # a straight ramp, clamped to one course per block so nothing needs a jump
        want = lo + round((hi - lo) * (z - z0) / span)
        want = max(y, min(y + 1, want)) if hi >= lo else min(y, max(y - 1, want))
        sp = _room_span(cave, z, want, 2, 3)
        if sp is None:
            # the notch: take the first course above that a body actually fits in
            for k in range(1, 6):
                sp = _room_span(cave, z, want + k, 2, 3)
                if sp:
                    want += k
                    break
        if sp is None:
            continue
        y = want
        for x in range(sp[0], sp[1] + 1):
            if w.put(x, y, z, s["deck"]):
                n += 1
        if z % 4 == 0:
            for x in (sp[0], sp[1]):
                w.put(x, y, z, s["lamp"])
    return n


def _runs(cave: Cave, z: int, y: int, reach: int = 16):
    """Every contiguous run of cavity at this course, NOT only the one through the axis.

    `_room_span` asks about the run that contains XC, which is the right question for a tube
    and the wrong one for a RING: at the front of the head the animal's own mouth is open, a
    shaft of void down the axis, and the cavity divides around it into two galleries. Asked
    the axis question the prow reports no room at all, which is exactly what it did - the deck
    stopped at Z80704 and 1,300 reachable cells sat unbuilt behind a measurement that could
    not see them.
    """
    out, run = [], None
    for x in range(XC - reach, XC + reach + 1):
        if cave.cave(x, y, z):
            run = (run[0], x) if run else (x, x)
        elif run:
            out.append(run)
            run = None
    if run:
        out.append(run)
    return out


def _ribs(w: _W, cave: Cave, s, deck, z0: int, z1: int, every: int, cap: int = 14):
    """Copper braces following the animal's OWN cross-section, every few blocks.

    The Sounding Hall came out a flat plank plain with a small bell on it, and the arcade a
    bare corridor - a hundred blocks of floor with a lamp in it, which is the "empty structure
    that sits there" this park has thrown work out for three times. A room this shape cannot
    be given mass by furniture, because the mass is the BODY: what it needs is for the body's
    own section to be drawn.

    So a rib is traced on the cavity's real boundary rather than on an arc somebody chose -
    from the deck up each flank and over the crown - which makes it a rib of THIS animal at
    THIS station, and every one of them different by construction. It also reads as what the
    fiction says happened: a crew shoring a carcass before they built a market in it.
    """
    n = 0
    for z in range(z0, z1 + 1):
        if z % every or z not in deck:
            continue
        y = deck[z]
        top = (cave.band(z) or (y, y))[1]
        for yy in range(y + 1, min(top, y + cap) + 1):
            sp = cave.span(z, yy)
            if not sp:
                continue
            for x in (sp[0], sp[1]):
                if abs(x - XC) > 26:              # the fins run out to nothing; a rib there is a speck
                    continue
                if w.put(x, yy, z, s["copper"]):
                    n += 1
        # and close it over the crown, so it is an arch rather than two posts
        crown = cave.span(z, min(top, y + cap))
        if crown:
            for x in range(max(crown[0], XC - 26), min(crown[1], XC + 26) + 1):
                w.put(x, min(top, y + cap), z, s["copper"])
    return n


def _bazaar(w: _W, cave: Cave, s, deck):
    """The market: stalls down both flanks of the head chamber, facing a centre aisle.

    THE SHOP IS SIGNAGE, ON JACK'S CHOICE. Nothing here holds stock and nothing here is a
    container a stranger can empty - each stall is a counter, a back board and a sign naming
    what the server's own shop command is for that trade. A barrel standing empty in a public
    build reads as a shop somebody has already looted.
    """
    z0, z1 = BAZAAR
    trades = [
        (("STONE & DEEP", "/shops find", "stone_bricks"), ("BLACKSTONE", "/shops find", "blackstone")),
        (("COPPER ROW", "/shops find", "copper_block"), ("GLASS & PANE", "/shops find", "glass")),
        (("WOOL & DYE", "/shops find", "white_wool"), ("TIMBER", "/shops find", "oak_log")),
        (("MOSS & FERN", "/shops find", "moss_block"), ("LIGHT", "/shops find", "froglight")),
    ]
    n, stalls, signed = 0, 0, 0

    # A STALL NEEDS A SPAN, SO THE PICKS ARE FILTERED RATHER THAN COMPUTED. Spaced evenly by
    # index, two of the eight landed where the head chamber pinches and shipped nothing, and a
    # market that advertises eight trades and builds six is a market with two empty bays.
    usable = [z for z in range(z0 + 3, z1 - 2)
              if z in deck and (cave.span(z, deck[z] + 2) or (0, 0))[1]
              - (cave.span(z, deck[z] + 2) or (0, 0))[0] >= 8]
    if len(usable) < len(trades):
        return n, stalls, signed
    gap = len(usable) // (len(trades) + 1)
    picks = [usable[gap * (i + 1)] for i in range(len(trades))]

    for (left, right), z in zip(trades, picks):
        y = deck[z]
        sp = cave.span(z, y + 1)
        if not sp:
            continue
        for side, text in ((-1, left), (+1, right)):
            # THE BACK BOARD IS FOUND PER COURSE, NOT COMPUTED ONCE. Placed one cell in from
            # the span, both boards shipped as seventeen-cell clusters floating a cell clear
            # of the wall they are meant to be bolted to - the span is the last CAVITY cell,
            # so the wall is one further out and the board belongs against it.
            built = 0
            for k in (1, 2, 3):
                row = cave.span(z, y + k)
                if not row:
                    continue
                bx = row[1] if side > 0 else row[0]
                for dz in (-1, 0, 1):
                    if w.put(bx, y + k, z + dz, s["deep"] if k == 2 else s["copper"]):
                        built += 1
            if not built:
                continue
            wx = sp[1] if side > 0 else sp[0]
            cx = wx - 2 * side                      # the counter, two in, facing the aisle
            for dz in (-1, 0, 1):
                w.put(cx, y, z + dz, s["dark"])
                w.put(cx, y + 1, z + dz, s["slab"])
            top = cave.span(z, y + 4)
            if top:
                w.put(top[1] if side > 0 else top[0], y + 4, z, s["lamp"])
            # THE TEXT LOOKS AT THE AISLE, AND THE AISLE IS TOWARD THE AXIS. Written the
            # obvious way round, every board on the high-X flank faced the wall it was
            # bolted to - and a sign whose support is missing is refused in silence.
            face = "west" if side > 0 else "east"
            row = cave.span(z, y + 2)
            bx = (row[1] if side > 0 else row[0]) if row else wx
            if w.sign(bx - side, y + 2, z, face, s[f"sign_{face}"], text):
                signed += 1
            stalls += 1

    # the aisle floor, and a lamp course down the middle
    for z in range(z0, z1 + 1):
        y = deck.get(z)
        if y is None:
            continue
        sp = _room_span(cave, z, y, 2, 5)
        if not sp:
            continue
        for x in range(sp[0], sp[1] + 1):
            if w.put(x, y, z, s["deck"]):
                n += 1
        if z % 5 == 0:
            w.put(XC, y, z, s["lamp"])
    return n, stalls, signed


def _prow(w: _W, cave: Cave, s, deck, dig: set, cap: int, every: int, budget: int):
    """THE PROW - the gallery round the animal's own open mouth.

    Jack, on the placed market: *"theres also some gap left unused towards the mouth of the
    squid from the inside."* He was right, and the reason was mine: `_bazaar` lays its aisle
    through `_room_span`, which asks about the run of cavity containing the AXIS - and from
    Z80705 the axis is not cavity at all. The deck stopped there and about 1,300 reachable
    cells sat behind a measurement that could not see them.

    WHAT IS ACTUALLY THERE, CLASSIFIED CELL BY CELL RATHER THAN COUNTED:

        #  rock        M  the sealed body cavity        .  OPEN VOID
        Y150  .......##MMMMMM###.....###MMMMMM##.......
        Y149  #.......##MMMMM###.....###MMMMM##.......#

    **The squid's mouth is open.** A shaft of outside runs down the axis from Z80706, widening
    forward, and the body cavity forms a RING around it - separated, at the closest, by ONE
    cell of rock. So the front of the market is not a dead end and not a chamber: it is two
    galleries either side of a hole that goes to the sea.

    That is also where the glass finally pays. Measured, a nine-by-seven window in the prow's
    FORWARD wall costs seventy-one cells of the animal and fifty-seven of its sixty-three
    sightlines end on nothing at all - the arm crown's forty lights are off to the sides, not
    in the cone, so it is an expensive black rectangle. A window in the INNER wall is one to
    three cells and looks into the mouth, which is open by construction. The animal supplies
    the view; nothing had to be invented for it.

    THE PROW IS DOWN FROM THE MARKET, AND THAT IS THE PROFILE BEING HONEST. `_profile` is a
    running maximum so the whole walk falls toward the tail, which puts the bazaar's deck two
    to three courses above the ring's own floor. Rather than force the ring up onto a plinth,
    the gallery takes the floor the animal gives it and the market steps DOWN into it - which
    is what a prow is.
    """
    z0, z1 = PROW
    n = {"deck": 0, "steps": 0, "rail": 0, "windows": 0, "dig": 0, "signed": 0}
    if z0 not in deck:
        return n
    head = deck[z0]                                   # the market's own deck, to step down from

    # ---- the floor the ring actually has, per course, and the runs wide enough to walk
    floors: dict[int, tuple[int, list]] = {}
    for z in range(z0, z1 + 1):
        found = None
        for y in range(cave.origin[1], cave.origin[1] + cave.shape[0] - 3):
            rs = [r for r in _runs(cave, z, y)
                  if r[1] - r[0] >= 3
                  and all(cave.cave(x, y + k, z) for x in range(r[0], r[1] + 1) for k in (1, 2))]
            if rs:
                found = (y, rs)
                break
        if found:
            floors[z] = found
    if not floors:
        return n

    # MONOTONE FORWARD, the way the main walk is. Taking each course's own local floor, the
    # ring wobbles - 143, 142, 143, 142 - and every wobble is a step DOWN immediately followed
    # by a step UP, which is two treads and a stumble where the animal only meant one slope.
    # `_profile` is a running maximum toward the head for exactly this reason; the prow falls
    # away from it, so its rule is a running MINIMUM and the walk out to the mouth is downhill
    # the whole way.
    run = None
    for z in sorted(floors):
        y, rs = floors[z]
        want = y if run is None else min(y, run)
        if want != y:
            alt = [r for r in _runs(cave, z, want)
                   if r[1] - r[0] >= 3
                   and all(cave.cave(x, want + k, z) for x in range(r[0], r[1] + 1) for k in (1, 2))]
            if alt:                                   # the animal allows it: take the lower line
                y, rs = want, alt
        floors[z] = (y, rs)
        run = y

    # ---- the descent from the market, so the prow is entered rather than dropped into
    first = min(floors)
    drop = head - floors[first][0]
    for k in range(max(0, drop)):
        z = z0 - 1 - k
        y = head - k
        for x in range(XC - 2, XC + 3):
            if w.put(x, y - 1, z, s["stair_south"]):
                n["steps"] += 1

    # ---- the galleries
    for z in sorted(floors):
        y, rs = floors[z]
        for (x0, x1) in rs:
            for x in range(x0, x1 + 1):
                if w.put(x, y, z, s["deck"]):
                    n["deck"] += 1
            # a rail on the INNER edge only - the outer edge is the animal's own flank, and a
            # rail against a wall is a fence in a corridor
            inner = x1 if x1 < XC else x0
            if abs(inner - XC) <= 3 and not w.has(inner, y + 1, z):
                if w.put(inner, y + 1, z, s["fence"]):
                    n["rail"] += 1

    # ---- THE WINDOWS. Every cell is dug from the animal, so the budget is hard and the count
    # is reported: a hole cut into a sculpture is the one thing in this design with no undo.
    #
    # A WINDOW IS A RUN ON ONE PLANE, NOT A SET OF CELLS. Placed one at a time wherever the
    # rule allowed, forty-six panes came out as a SCATTER of black blobs at three different
    # depths - the mouth's wall is jagged, so glazing each cut where it happened to end put
    # every pane on its own plane. That is the deck soffit's confetti in glass, and it is the
    # sixth time this repo has drawn something per-cell that only reads as a line.
    #
    # So: the cut goes all the way through (you have to see out), the PANE sits only on the
    # gallery's own wall plane (so the window is flat), and a course that cannot make a run of
    # `MIN_RUN` gets nothing at all rather than a speckle.
    MIN_RUN = 3
    for z in sorted(floors):
        if (z - min(floors)) % every:
            continue
        y0 = floors[z][0]
        for sgn in (-1, 1):
            # which courses have an open mouth AND a thin wall, and where does the pane sit?
            rows: dict[int, tuple] = {}
            for yy in range(y0 + 3, y0 + 11):
                axis = cave._ix(XC, yy, z)
                if axis is None or cave.solid[axis] or cave.inside[axis]:
                    continue                          # no mouth at this course
                x, cut = XC, []
                while abs(x - XC) <= 6 and not cave.cave(x, yy, z):
                    if cave.rock(x, yy, z):
                        cut.append((x, yy, z))
                    x += sgn
                if cut and len(cut) <= 3 and cave.cave(x, yy, z):
                    rows[yy] = (cut, x)               # x is the gallery cell beyond the wall
            # keep only CONTIGUOUS runs of at least MIN_RUN courses
            run, keep = [], []
            for yy in sorted(rows) + [None]:
                if run and yy is not None and yy == run[-1] + 1:
                    run.append(yy)
                    continue
                if len(run) >= MIN_RUN:
                    keep.extend(run)
                run = [yy] if yy is not None else []
            # ONE PLANE FOR THE WHOLE RUN, AND THE RUN RE-CHECKED AFTER CHOOSING IT. Taking
            # each course's own innermost cut cell puts the panes at different x, so three
            # qualifying courses can still leave every pane standing alone on its own plane -
            # a run of one, which is the speckle this gate exists to stop. Measured on the
            # first build of this rule: a pane at X97596 Y149 Z80708 with a run of two.
            if not keep:
                continue
            xs = collections.Counter(min(rows[yy][0], key=lambda c: abs(c[0] - rows[yy][1]))[0]
                                     for yy in keep)
            px = xs.most_common(1)[0][0]
            flat = [yy for yy in keep if any(c[0] == px for c in rows[yy][0])]
            run2, keep2 = [], []
            for yy in sorted(flat) + [None]:
                if run2 and yy is not None and yy == run2[-1] + 1:
                    run2.append(yy)
                    continue
                if len(run2) >= MIN_RUN:
                    keep2.extend(run2)
                run2 = [yy] if yy is not None else []
            keep = keep2
            for yy in keep:
                cut, gx = rows[yy]
                if n["dig"] + len(cut) > budget:
                    continue
                for c in cut:
                    dig.add(c)
                    w.dig.add(c)
                    n["dig"] += 1
                # the PANE on ONE plane, the rest of the cut left as air, so the opening is a
                # flat window with a reveal behind it rather than a jagged hole
                if w.put(px, yy, z, s["pane"]):
                    n["windows"] += 1
            # a copper reveal round the opening, so it reads as made rather than as damage
            if keep:
                gx = rows[keep[0]][1]
                for yy in (min(keep) - 1, max(keep) + 1):
                    w.put(gx, yy, z, s["copper"])

    # ---- the name, on the gallery's outer wall where there is something to hang it on
    zs = sorted(floors)
    zm = zs[len(zs) // 2]
    y = floors[zm][0]
    for (x0, x1) in floors[zm][1]:
        # THE WALL IS FOUND AT THE SIGN'S OWN COURSE, NOT TAKEN FROM THE FLOOR'S RUN. The
        # gallery widens as it rises, so the outermost cell two courses up is further out than
        # the floor's edge - and a board hung on the floor's edge has open cavity behind it and
        # is refused in silence. `_bazaar` learned this and its lesson did not travel.
        sgn = -1 if x0 < XC else 1
        yy = y + 2
        x = x0 if sgn < 0 else x1
        while cave.cave(x + sgn, yy, zm):
            x += sgn
        if not cave.cave(x, yy, zm):
            continue
        face = "east" if sgn < 0 else "west"
        if w.sign(x, yy, zm, face, s[f"sign_{face}"],
                  ("THE PROW", "the mouth is", "open - that", "is the void")):
            n["signed"] += 1
    return n


def _sounding(w: _W, cave: Cave, s, deck):
    """THE SOUNDING HALL - the fin band, the widest room in the animal, and the payoff.

    A hall with nothing in it is exactly the thing Jack has thrown out of this park three times
    ("we don't want empty structures that sit there and are mostly useless"), so it gets the one
    verb that costs a single block and cannot break: a BELL, hung over a dais at the far end of
    a two-hundred-block walk. It also names the room, which is the honest test of whether a
    room has a reason - the Lantern Hall, the Prize Office and the Wash House all failed it.
    """
    z0, z1 = SOUND
    n = 0
    zs = [z for z in range(z0, z1 + 1) if z in deck]
    if not zs:
        return n, False
    for z in zs:
        y = deck[z]
        sp = _room_span(cave, z, y, 3, 12)
        if not sp:
            continue
        x0, x1 = sp
        for x in range(x0, x1 + 1):
            if w.put(x, y, z, s["deck"] if abs(x - XC) <= 5 else s["dark"]):
                n += 1
        if z % 6 == 0 and x1 - x0 >= 4:
            for x in (x0 + 1, x1 - 1):
                w.put(x, y, z, s["lamp"])
    # the dais and the bell, on the axis, a third of the way in from the deep end
    dz = zs[len(zs) // 3]
    dy = deck[dz]
    for dx in range(-3, 4):
        for ddz in range(-3, 4):
            if abs(dx) + abs(ddz) <= 4:
                w.put(XC + dx, dy + 1, dz + ddz, s["copper"])
    for dx in range(-2, 3):
        for ddz in range(-2, 3):
            if abs(dx) + abs(ddz) <= 2:
                w.put(XC + dx, dy + 2, dz + ddz, s["dark"])
    # THE BELL HAS TO BE REACHABLE OR IT IS A PICTURE OF A BELL. Hung from the cavity's own
    # ceiling it came out at Y114 over a dais at Y106 - five and a half blocks over a standing
    # player's eye against a reach of about four and a half, so the one verb in the biggest
    # room in the animal could not be used, and every offline check passed it. It hangs from
    # its own FRAME now, which is also what makes it read as a bell rather than as a dot.
    ceil = (cave.band(dz) or (dy, dy + 8))[1]
    top = min(dy + 6, ceil - 1)
    for dx, ddz in ((-3, 0), (3, 0), (0, -3), (0, 3)):
        for y in range(dy + 3, top):
            w.put(XC + dx, y, dz + ddz, s["copper_b"])
    for dx in range(-3, 4):
        w.put(XC + dx, top, dz, s["deep"])
    for ddz in range(-3, 4):
        w.put(XC, top, dz + ddz, s["deep"])
    rung = w.put(XC, top - 1, dz, s["bell"])
    w.put(XC + 3, top - 1, dz + 3, s["lamp"])
    w.put(XC - 3, top - 1, dz - 3, s["lamp"])
    reach = (top - 1) - (dy + 3)          # the bell, over the head of a body on the dais
    if rung and reach > 3:
        raise ValueError(f"the bell is {reach} over the dais and nobody can ring it")
    _post_sign(w, s, XC, dy + 4, dz + 4, "south",
               ("THE SOUNDING", "HALL", "ring the bell", "you got here"))
    return n, rung


def _vault(w: _W, cave: Cave, s, deck):
    """The tail: the deepest cell anybody can stand in, marked and left raw.

    Nothing is built out here but a landing and a lamp. A dead end that has been furnished is a
    room; a dead end that has been REACHED is a distance, and the distance is the point.
    """
    z0, z1 = TAIL
    zs = [z for z in range(z0, z1 + 1) if z in deck]
    if not zs:
        return 0, False
    end = min(zs)
    y = deck[end]
    # THE WHOLE ZONE, NOT FIVE COURSES. Written as a five-course landing at the very tip, the
    # eleven blocks between it and the Sounding Hall's deck belonged to no builder at all and
    # were never floored - so the last stretch of a two-hundred-block walk was a scramble over
    # the animal's raw tail. It passed every check including the walk flood, because
    # scrambling over rock IS walking; only a flood restricted to floor THIS DESIGN BUILT
    # could see it.
    n = 0
    for z in range(end, max(zs) + 1):
        sp = _room_span(cave, z, deck[z], 2, 2) if z in deck else None
        if not sp:
            continue
        for x in range(sp[0], sp[1] + 1):
            if w.put(x, deck[z], z, s["dark"]):
                n += 1
    w.put(XC, y, end + 1, s["lamp"])
    for k in (1, 2):
        w.put(XC, y + k, end, s["copper_b"])
    ok = _post_sign(w, s, XC, y + 2, end + 1, "south",
                    ("THE TAIL", "Y%d" % y, "212 blocks", "from the head"))
    return n, ok


def _marks(w: _W, cave: Cave, s, deck, every: int, sx: int, sz: int):
    """Lay-bys down the arcade, with the distance on them.

    An eighty-six block corridor with a light every six is a corridor. What makes a walk read
    is knowing how far along it you are, and it costs a bench, a lamp and a sign.
    """
    z0, z1 = ARCADE
    n = 0
    for z in range(z0, z1 + 1):
        if z % every or z not in deck:
            continue
        y = deck[z]
        sp = cave.span(z, y + 1)
        if not sp:
            continue
        for side in (-1, 1):
            wx = sp[1] if side > 0 else sp[0]
            if not w.has(wx + side, y + 1, z):
                continue
            for dz in (-1, 0, 1):
                w.put(wx, y, z + dz, s["dark"])
                w.put(wx, y + 1, z + dz, s["slab"])
            w.put(wx, y + 3, z, s["lamp"])
            n += 1
            if side > 0:
                d = abs(sz - z)
                w.sign(wx, y + 2, z, "west", s["sign_west"],
                       ("THE ARCADE", "%d blocks" % d, "to the collar", "bell: south"))
    return n


# ---------------------------------------------------------------------------------------------


def _floors(w: _W, cave: Cave):
    """Every cell this design laid that a body can stand ON, MEASURED off the finished canvas.

    Derived rather than book-kept. Six builders lay floor and each could hand back its own
    list; six lists is six places to forget one, and the question - can somebody stand here -
    is answerable from the model itself with nothing to keep in step.
    """
    ox, oy, oz = w.origin
    out = []
    for y, z, x in zip(*np.nonzero(w.c.ids)):
        wx, wy, wz = x + ox, y + oy, z + oz
        if cave.rock(wx, wy, wz):
            continue
        if not cave.cave(wx, wy + 1, wz):          # the body stands INSIDE the animal
            continue
        if w.c.get(x, y + 1, z) or w.c.get(x, y + 2, z):
            continue
        if cave.rock(wx, wy + 2, wz):
            continue
        out.append((wx, wy, wz))
    return out


def _treads(w: _W, cave: Cave, s, passes: int = 3):
    """Every step on the walk, given its tread, ONCE, over the finished deck.

    Jack, on the placed market: *"the stairs arent aligned, so theres a bunch that are placed
    wrongly or dont connect to lead to the upper areas as we progress towards mouth."* Measured
    over the shipped design, six transitions were wrong and they had three different causes -
    because FOUR builders each rolled their own riser and only one of them was right:

        Z80561/66/70   the Sounding Hall lays deck course by course and placed NO tread at all
        Z80703         a TWO-course drop with nothing in it: you can fall it, not climb it
        Z80705/80710   the prow, which DESCENDS toward the mouth, given south-facing treads

    All 197 stairs in the build faced south. That is right for the arcade, which climbs toward
    the head, and backwards for the prow, which falls away into it - and **our renderer draws a
    backwards flight identically to a correct one**, which is the whole reason this repo asserts
    the stair convention rather than eyeballing it.

    THE RULE, and it is one rule rather than four: a tread sits at the LOWER of the two
    courses, in the column adjacent to the step, with its tall side FACING THE HIGHER DECK.
    `facing` is that direction, `half` is bottom - CLAUDE.md's "a flight that ascends toward D
    has every tread facing=D", which falls out of this rather than being applied by hand.

    It runs to a fixpoint because the cure for a two-course drop is an intermediate landing,
    and that landing is itself a step that wants a tread.
    """
    # THE DECK, NOT EVERYWHERE A BODY CAN STAND. Scoped to `_floors` - which is every standable
    # cell the design placed - the pass read a lay-by BENCH beside the walk, a rib top and the
    # collar's platform as courses of the same route, "found" steps of nine and ten courses
    # between them and started inserting landings in mid-air: six bad transitions became
    # thirty-three. A walk is its own material, and here that is the deck and the treads
    # already in it.
    from .. import nbt as _nbt
    ok = {"minecraft:spruce_planks"}
    walk_ids = {i for i, q in enumerate(w.c.reg.palette)
                if _nbt.state_name(q) in ok or _nbt.state_name(q).endswith("_stairs")}
    ox, oy, oz = w.origin

    fixed = {"tread": 0, "landing": 0, "steep": 0}
    for _ in range(passes):
        top: dict[tuple, int] = {}
        for y, z, x in zip(*np.nonzero(np.isin(w.c.ids, list(walk_ids)))):
            wx, wy, wz = x + ox, y + oy, z + oz
            if w.c.get(x, y + 1, z) or w.c.get(x, y + 2, z):
                continue                              # something stands on it: not the walk
            k = (wx, wz)
            if wy > top.get(k, -9999):
                top[k] = wy
        steep = []
        for (x, z), a in list(top.items()):
            b = top.get((x, z + 1))
            if b is None or a == b:
                continue
            if abs(a - b) == 1:
                # THE TREAD GOES AT THE HIGHER COURSE, AND THE FIRST VERSION PUT IT AT THE
                # LOWER ONE. Jack, walking it: "you walk up stairs, have to jump then walk then
                # jump its very strange." He was describing this exactly. A bottom stair's
                # walkable top is half a block, so a tread laid at the LOW course drops you
                # half a block and then asks for a full one - walk, jump, walk, jump.
                #
                # CLAUDE.md read the convention off Jack's own flight and wrote it down:
                # "four consecutive treads, each ONE COURSE UP AND ONE STEP east". The tread
                # climbs WITH the step. So it sits at the higher of the two courses, in the
                # higher column, facing the direction of ascent - and then the low deck, the
                # tread's front half and the high deck are half a block apart each.
                if b == a + 1:
                    hi_y, hi_z, face = b, z + 1, "south"
                else:
                    hi_y, hi_z, face = a, z, "north"
                if w.put(x, hi_y, hi_z, s[f"stair_{face}"]):
                    fixed["tread"] += 1
            else:
                steep.append((x, a, z, b))
        # A DROP OF TWO IS NOT A STEP. Give it an intermediate course to land on; the next pass
        # then treats the two halves as ordinary steps and treads them.
        for (x, a, z, b) in steep:
            if abs(a - b) > 3:
                continue                              # not one route: two different surfaces
            mid = a + (1 if b > a else -1)
            zz = z if b > a else z + 1
            if w.put(x, mid, zz, s["deck"]):
                fixed["landing"] += 1
        fixed["steep"] = len(steep)
        if not steep and not fixed["tread"]:
            break
    return fixed


def _relight(w: _W, cave: Cave, s, floors, thresh: int, sep: int):
    """Light the walk to a FIXPOINT, propagated, never spaced.

    The first pass laid a lamp every six down the arcade and every five along the aisle, which
    is a rhythm and is not an answer: propagated over the finished composite, 912 of 4,064
    walkable cells came out at block light 3 or under - 622 of them in the bazaar, which is
    the room a visitor is meant to shop in. A sealed cavity under a park that has no sky light
    at any hour does not have dim corners, it has invisible ones.

    So the spacing is a first coat and this is the coat that finishes it: propagate, take every
    walkable cell still under the threshold, set a froglight INTO the floor at a spread of
    them, and propagate again. `Island Night` records why it must be a fixpoint rather than one
    pass - a lamp changes what is dark - and why the lamp goes IN the floor rather than on it:
    a flush emitter is the floor, so it cannot be knocked off a walkway, and it reaches one
    less than it emits because the body stands in the cell above an opaque block.

    THE ANIMAL'S OWN LIGHTS ARE IN THE MODEL. The squid carries 450 froglights in its skin and
    the shell is two thick, so some of that genuinely reaches the inside. Modelling the cavity
    as unlit would put lamps where the animal has already lit itself.
    """
    from .. import nightlight

    if not floors:
        return 0, 0
    xs = [f[0] for f in floors]
    ys = [f[1] for f in floors]
    zs = [f[2] for f in floors]
    # THE WHOLE CANVAS, NOT A PADDED BOX. Cropped, the model is missing the animal's own rock
    # outside the crop, so light behaves differently at the edge than it does in the world -
    # and the solver reported `dark_left: 0` while three treads sat at block light 6. A light
    # solver that is optimistic is the one kind that must not exist: it says a floor is lit
    # when it is not, which is the whole failure this pass was written to prevent.
    #
    # It costs one propagation over the full box, which is what the test does anyway - and the
    # two agreeing is the point. `proportions.measure` and `rubric.score` share an entry point
    # for the same reason; this is the same drift, between a generator and its own test.
    ox_, oy_, oz_ = w.origin
    x0, y0, z0 = ox_, oy_, oz_
    x1 = ox_ + w.c.sx - 1
    y1 = oy_ + w.c.sy - 1
    z1 = oz_ + w.c.sz - 1

    names = list(w.c.reg.palette)
    from .. import nbt
    pal = [nbt.state_name(q) for q in names]
    lookup = {n: i for i, n in enumerate(pal)}
    merged = list(pal)
    remap = {}
    for i, n in enumerate(cave.names):
        if n not in lookup:
            lookup[n] = len(merged)
            merged.append(n)
        remap[i] = lookup[n]

    shape = (y1 - y0 + 1, z1 - z0 + 1, x1 - x0 + 1)
    grid = np.zeros(shape, np.int32)
    ox, oy, oz = w.origin
    # the animal first, then this design over it - and the mouth is air, because it is dug
    for (y, z, x) in zip(*np.nonzero(cave.solid)):
        wy, wz, wx = y + cave.origin[1], z + cave.origin[2], x + cave.origin[0]
        if y0 <= wy <= y1 and z0 <= wz <= z1 and x0 <= wx <= x1:
            grid[wy - y0, wz - z0, wx - x0] = remap[int(cave.ids[y, z, x])]
    sub = w.c.ids[y0 - oy:y1 - oy + 1, z0 - oz:z1 - oz + 1, x0 - ox:x1 - ox + 1]
    grid[sub != 0] = sub[sub != 0]
    for (dx, dy, dz) in w.dig:
        if y0 <= dy <= y1 and z0 <= dz <= z1 and x0 <= dx <= x1:
            if w.c.get(dx - ox, dy - oy, dz - oz) == 0:
                grid[dy - y0, dz - z0, dx - x0] = 0

    opq_p, emit_p, _passy, _spawn, _water = nightlight.classify(merged)
    lamp_id = w.c.state("ochre_froglight")
    lamp_pal = lookup[nbt.state_name(w.c.reg.palette[lamp_id])]

    placed, rounds, dark = 0, 0, []
    used = set()
    for rounds in range(1, 25):
        light = nightlight.propagate(opq_p[grid], emit_p[grid].astype(np.int16))
        dark = [f for f in floors
                if light[f[1] + 1 - y0, f[2] - z0, f[0] - x0] < thresh]
        if not dark:
            break
        # THE SPACING TIGHTENS AS IT CONVERGES. A fixed separation is right for the first
        # rounds - it spreads lamps rather than clustering them - and is what leaves the last
        # handful unlit for ever: three treads sat at block light 6 while the solver spent its
        # whole round budget refusing to put a lamp near them.
        step = sep if rounds <= 5 else max(2, sep // 2)
        dark.sort(key=lambda f: (f[2], f[0]))
        chosen, taken = [], []
        for f in dark:
            if all(abs(f[0] - g[0]) + abs(f[2] - g[2]) >= step for g in taken):
                chosen.append(f)
                taken.append(f)
        got = 0
        for f in chosen:
            # A STAIR IS A STEP, so a lamp may not take it - but the cell still has to be lit,
            # and after `_treads` a whole flight can be stairs end to end. It lights a NEIGHBOUR
            # instead. Refusing and moving on is what left one cell of the gullet at block
            # light 6 with the solver reporting itself finished.
            # NEAREST NON-TREAD, SEARCHED PROPERLY. Four orthogonal neighbours is not enough:
            # on a flight the whole course is stairs, so every candidate is one and the solver
            # gives up. The five cells it left at block light 6-7 were all treads with a run of
            # treads either side of them.
            spot = None
            for r in (0, 1, 2, 3, 4):
                best = None
                for dx in range(-r, r + 1):
                    for dz in range(-r, r + 1):
                        if max(abs(dx), abs(dz)) != r:
                            continue
                        for dy in (0, -1, 1):
                            cand = (f[0] + dx, f[1] + dy, f[2] + dz)
                            here = w.c.get(*w._l(*cand))
                            if not here:
                                continue
                            if "stairs" in nbt.state_name(w.c.reg.palette[here]):
                                continue
                            # A FLUSH LAMP MUST *BE* A FLOOR. The search allows dy=-1 so it
                            # can reach a neighbouring deck one course down - and without
                            # this it took the STRINGER under the tread instead, buried a
                            # froglight beneath an opaque deck block, reported it placed, and
                            # lit nothing. It then chose the same cell every round for the
                            # whole budget, so `got` stayed positive and the "nothing left I
                            # can reach" break never fired: three cells of a diagonal flight
                            # dark for ever, and 24 rounds spent re-placing one lamp.
                            up = w._l(cand[0], cand[1] + 1, cand[2])
                            if w.c.get(*up) or cave.rock(cand[0], cand[1] + 1, cand[2]):
                                continue
                            if cand in used:
                                continue
                            # WHAT STANDS ON IT DOES NOT MATTER FOR A LAMP. `_floors` excludes
                            # a cell carrying a rail, correctly, because nobody stands there -
                            # and the fallback inherited that and so refused the only cells it
                            # could have used. Where the arcade is a full-width flight the ONLY
                            # deck left is the two rail columns, and three treads sat at block
                            # light 6 because a fence was standing on the fix. A froglight is a
                            # full block: the rail stands on it exactly as it stood on the deck.
                            best = cand
                            break
                        if best:
                            break
                    if best:
                        break
                if best:
                    spot = best
                    break
            if spot is not None and abs(spot[0] - f[0]) + abs(spot[2] - f[2]) > 4:
                spot = None                          # too far to light it: hang one instead
            if spot is None:
                # LAST RESORT: HANG IT. Where the cell and all four neighbours are treads -
                # which happens on a flight, and the gullet is one - there is no floor to set
                # a lamp into, and the solver used to give up and report itself finished with
                # the step still dark. A lantern under the animal's own ceiling costs the walk
                # nothing and takes no tread.
                # AND IT IS CHAINED DOWN TO WHERE IT CAN BE SEEN. Hung flush under the
                # crown it is eighteen courses over the gullet's climb, which is four more
                # than a lantern reaches: it was placed, counted as progress, and lit
                # nothing - and because it was re-placed at the same cell every round `got`
                # stayed positive and the solver ran its whole budget re-hanging one lamp.
                # The taproot entrance already owns this idiom, for the same reason: light
                # that falls DOWN a shaft rather than onto its rim.
                for k in range(2, 26):
                    if not cave.rock(f[0], f[1] + k, f[2]):
                        continue
                    hang = min(f[1] + 4, f[1] + k - 1)   # over a head, inside its own reach
                    if (f[0], hang, f[2]) in used:
                        break
                    if not w.put(f[0], hang, f[2], s["lantern"]):
                        break
                    used.add((f[0], hang, f[2]))
                    grid[hang - y0, f[2] - z0, f[0] - x0] =                         lookup[nbt.state_name(w.c.reg.palette[s["lantern"]])]
                    placed += 1
                    got += 1
                    chain_pal = lookup[nbt.state_name(w.c.reg.palette[s["chain"]])]
                    for cy in range(hang + 1, f[1] + k):
                        if w.put(f[0], cy, f[2], s["chain"]):
                            grid[cy - y0, f[2] - z0, f[0] - x0] = chain_pal
                    break
                continue
            if w.put(spot[0], spot[1], spot[2], lamp_id):
                used.add(spot)
                grid[spot[1] - y0, spot[2] - z0, spot[0] - x0] = lamp_pal
                placed += 1
                got += 1
        if not got:                              # nothing left this solver can reach
            break
    # THE REMAINDER IS REPORTED, NOT SWALLOWED. A solver that stops on a round cap and returns
    # only what it placed says a floor is lit when it is not, which is the one thing a light
    # pass must never do. `dark_left` is what a test asserts against.
    return placed, rounds, len(dark)


def build(cfg: dict, donors=None) -> Canvas:
    p = {**MARKET, **(cfg or {})}
    cave = Cave(p["squid"])
    park = _Park(p["park"]) if p.get("park") else None

    ox, oy, oz = cave.origin
    ny, nz, nx = cave.shape
    surface = int(p["surface"])
    SY = surface + 8 - oy                      # room for the wellhead's own crown over the plaza
    c = Canvas(nx, SY, nz, donors)
    c.world_origin = (ox, oy, oz)
    s = _states(c)

    sx, sz = int(p["shaft"][0]), int(p["shaft"][1])

    # ---- the mouth. TWO courses of Prismworks paving and TWO of the animal's skin, 3x3.
    # Nothing else in the animal is ever broken, and the shell thickness is MEASURED rather
    # than assumed to be the hollow's `shell: 2` - a fit-out that trusts a parameter is a
    # fit-out for a different animal the day somebody re-tunes one.
    band = cave.band(sz, half=1)
    if band is None:
        raise ValueError("the shaft column stands over no cavity at all")
    cavetop = band[1]
    skin = cavetop + 1
    while cave.rock(sx, skin, sz):
        skin += 1
    skin -= 1                                   # the last cell of shell
    dig = set()
    floors = [int(v) for v in p["park_floor"]]
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            for y in floors:
                dig.add((sx + dx, y, sz + dz))
            for y in range(cavetop + 1, skin + 1):
                dig.add((sx + dx, y, sz + dz))

    # A DUG CELL THAT IS ALSO BUILT IS NOT A CLASH, and this design has two kinds: the shaft's
    # mouth, where a ladder must have a rung in every course it passes through, and the prow's
    # windows, where the pane IS the cell that was cut. `rimstair` settled the principle on a
    # flight cut into a cliff - "the tread cell is itself a dig" - so the context audit is told
    # to see those cells as what they will be when the printer arrives, which is air.
    #
    # DERIVED FROM THE DIG LIST, ONE BOX PER CELL, rather than two boxes drawn round the shaft
    # by hand. The hand-drawn version was written before the prow existed and silently did not
    # cover it: thirty panes came out as thirty overlaps. A declaration that has to be kept in
    # step with the thing it declares is a declaration that goes stale.
    exclude: list[list[int]] = []

    w = _W(c, (ox, oy, oz), cave, park, dig)

    # ---- the walk. One profile for the whole animal, so the arcade, the gullet and the
    # bazaar cannot disagree about what height the floor is at their shared boundary.
    deck, ducked = _profile(cave, TAIL[0], PROW[1], int(p["headroom"]))
    if not deck:
        raise ValueError("no walkable profile in the cavity")

    half = int(p["walk_w"]) // 2
    walk = {z: y for z, y in deck.items() if ARCADE[0] <= z < COLLAR[1]}
    laid, lamps, _ext = _walkway(w, cave, s, walk, half, s["deck"], every=int(p["lamp_every"]))
    bays = _marks(w, cave, s, deck, int(p["mark_every"]), sx, sz)

    n_shaft = _shaft(w, cave, s, sx, sz, surface, skin + 1, cavetop)
    n_rig = _rig(w, cave, s, sx, sz, cavetop, deck.get(sz, cavetop - 18))
    foot = deck.get(sz, cavetop - 18)
    rungs, gaps = _climb(w, s, sx, sz, foot + 1, surface - 1)
    if gaps:
        raise ValueError(f"the climb has {len(gaps)} course(s) with no rung: {gaps[:8]}")
    n_collar = _collar(w, cave, s, sx, sz, deck)
    n_gullet = _gullet(w, cave, s, deck)
    n_baz, stalls, signed = _bazaar(w, cave, s, deck)
    prow = _prow(w, cave, s, deck, dig, int(p["prow_w"]),
                 int(p["window_every"]), int(p["window_budget"]))
    n_sound, rung = _sounding(w, cave, s, deck)
    ribs = _ribs(w, cave, s, deck, SOUND[0], SOUND[1], int(p["rib_every"]))
    ribs += _ribs(w, cave, s, deck, ARCADE[0], COLLAR[1], int(p["rib_every"]) + 2)
    ribs += _ribs(w, cave, s, deck, GULLET[0], PROW[1], int(p["rib_every"]) - 2)
    n_vault, tailsign = _vault(w, cave, s, deck)

    # THE TREADS BEFORE THE LIGHT, and the light may not eat one: `_relight` sets a froglight
    # INTO a floor cell, and a floor cell that is a stair is a step. Ordered the other way the
    # solver would quietly un-build the flight it was lighting.
    treads = _treads(w, cave, s)
    floors = _floors(w, cave)
    lit, rounds, dark_left = _relight(w, cave, s, floors, int(p["light_min"]), int(p["light_sep"]))

    exclude = [[x, y, z, x, y, z] for (x, y, z) in sorted(dig)]

    c.meta = {
        "kind": "abyssmarket",
        "generated_by": "mcbuild.gen.abyssmarket",
        "facing": "north",
        "dig": [list(d) for d in sorted(dig)],
        "exclude_boxes": exclude,
        "cavity_cells": cave.cells,
        "walk": {"from_z": min(deck), "to_z": max(deck),
                 "from_y": deck[min(deck)], "to_y": deck[max(deck)],
                 "length": max(deck) - min(deck), "ducked": len(ducked)},
        "deck_cells": laid, "deck_lamps": lamps, "lay_bys": bays, "treads": treads,
        "floor_cells": len(floors), "relit": lit, "relight_rounds": rounds,
        "dark_left": dark_left, "light_min": int(p["light_min"]),
        "shaft": {"x": sx, "z": sz, "surface": surface, "skin": skin, "cavity_top": cavetop,
                  "drop": surface - cavetop, **n_shaft, "rig": n_rig,
                  "rungs": rungs, "foot_y": foot},
        "collar": n_collar, "gullet": n_gullet,
        "bazaar": {"cells": n_baz, "stalls": stalls, "signed": signed},
        "prow": prow,
        "sounding": {"cells": n_sound, "bell": bool(rung)}, "ribs": ribs,
        "vault": {"cells": n_vault, "signed": bool(tailsign)},
        "yielded_to_others": w.yielded, "clipped": w.clipped,
    }
    return c
