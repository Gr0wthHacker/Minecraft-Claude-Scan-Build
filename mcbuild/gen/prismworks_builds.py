"""PRISMWORKS: the six buildings of the park's machine land, one lot each.

    PF Foundry Gate     53 x 36  at V24, U430    the land's threshold, onto the spine
    PF Prism Array      53 x 51  at V24, U471    the exhibit hall, onto the spine
    PF Resonance Vault  53 x 41  at V82, U471    the closed block, onto the prism walk
    PF Prism Ascent     93 x 72  at V24, U527    the headline - one of three skyline dominants
    PF Forge Deck       24 x 66  at V130, U527   the exit / observation gallery
    PF Service Gallery  13 x 41  at V157, U550   back of house, on the service lane

**THE GROUND IS ALREADY BUILT AND NONE OF IT IS IN HERE.** `Park Ways` draws the lawn, the spine,
the avenues, the back promenade, every spur to every door and every lamp in the land; `Park Rail`
draws the railway. So this module contains BUILDINGS and nothing else - no paving apron, no lamp
post, no bench, no marker. A building that brings its own street furniture is how the previous
park became "chaos"; the street is somebody else's design and it is finished.

Y=0 of every canvas is the first course ABOVE the lawn (world Y203, the lawn being Y202), so a
design stands on ground it does not own and shares no cell with it.

---------------------------------------------------------------------------------------------
THE LAND'S OWN LINE, AND WHY IT IS GEOMETRY

Prismworks is blackstone and deepslate. `blackstone` to `polished_blackstone_bricks` to
`chiseled_polished_blackstone` is 38 -> 45 -> 51 of luminance: a family is one material shown four
ways, and dressing a stone does not change how much light it returns, so **a value ladder searched
inside one family cannot exist by construction.** This repo has drawn the opposite conclusion from
that measurement three separate times. Measured ACROSS families at cheap tier:

    black_wool                  22      the recess - a shadow you can build
    polished_blackstone_bricks  45      the field                            (+23)
    smooth_basalt               73      the pier and the string course       (+28)
    cyan_wool                  104      the signal                           (+31)
    light_blue_wool            145      the high signal                      (+41)
    pearlescent_froglight      229      the emitter                          (+84)

Six stops, every gap >= 23, every one of them CHEAP tier and 1.19. `tests/test_prismworks_builds`
measures that ladder off `blocks.color` rather than trusting this comment.

On top of it the lines are GEOMETRY, because at 23 apart a tone step reads at ten blocks and a
projection reads at a hundred: a proud string course of slabs, a corbelled cornice of upside-down
stairs, a pier rhythm that breaks every wall into bays, a parapet with real merlon gaps. That is
the void tower's rule - **what makes voxels read as architecture is REGULARITY AND OPENINGS, not
damage** - and every one of these six is built on it.

**THE LIGHT IS A SIGNAL, NOT A MOOD.** Every other land here lights itself warm (lantern, ochre
froglight). This one is `soul_lantern` and `pearlescent_froglight` on a `light_blue_wool` band, on
a fixed rhythm, always at a structural position - a pier head, a crown course, a portal reveal -
so the land reads cold and mechanical from the spine at night.

---------------------------------------------------------------------------------------------
WHAT IS DELIBERATELY NOT IN HERE

* **No redstone of any kind.** `PRISMWORKS_GENERATOR.md`: a generator "must not claim that
  obligation is done merely because a litematic contains water, buttons, lamps, or signs", and
  this repo cut two finished casino games rather than ship a machine it could not judge by
  simulation. These six are architecture; the Ascent's timing, the Array's route lights and the
  Vault's completion circuit are separate tickets with their own proof obligations.
* **No lot is filled.** Every one of the six leaves 20-40% of its ground open, because a facade
  field wall to wall reads as a car park with a roof. The Ascent's rear quarter, the Gate's rear
  quarter and the margins of every hall are lawn on purpose.
* **Nothing outside the lot.** `_Lot.put` is bounds-checked against the lot and counts what it
  refuses; a cell outside is cropped at placement and simply lost, and this park has already lost
  a 111-block ride to a single lamp.
* **Nothing in a lamp arm's cell.** The park's avenue lamps stand on the lot boundary lines and
  throw a four-armed `iron_bars` cross at world Y209, one cell of which reaches INTO the lot.
  Fourteen such cells fall inside these six lots; `keep_clear` names them, `put` refuses them, and
  a test re-derives them from `out/Park Complete.litematic` rather than trusting the list.
"""
from __future__ import annotations

from .canvas import Canvas, hash01

SIGN_WIDTH = 15                      # a sign line clips mid-word past this
ANCHOR = (97500, 203, 80300)         # V0 -> X, the course above the lawn, U0 -> Z

#: The land's one palette. Bulk is CHEAP tier throughout: `polished_deepslate` and
#: `deepslate_tiles` are the paving `parkways` gives Prismworks and are both `ok`, so they appear
#: here only as the threshold course and the small trim that ties a building to the street it
#: stands on. A third of a building made of them would put the design over its material policy on
#: its own - the same trade `parkrail` records for its viaduct.
PRISM = {
    "field":   "polished_blackstone_bricks",   # 45 - the wall
    "recess":  "black_wool",                   # 22 - the shadow, and every window reveal
    "pier":    "smooth_basalt",                # 73 - the vertical rhythm, and the string course
    "signal":  "cyan_wool",                    # 104
    "high":    "light_blue_wool",              # 145 - the crown band
    "glow":    "pearlescent_froglight",        # 229
    "floor":   "chiseled_deepslate",           # 54 - interior floors
    "thresh":  "deepslate_tiles",              # 55 (ok) - the doorway course, the land's own kerb
    "worn":    "cracked_polished_blackstone_bricks",   # 40 - the field's own weathering
    "dark":    "blackstone",                   # 38 - cornice and corbel shadow
    # -- trim ------------------------------------------------------------------------------
    "slab":    "polished_blackstone_brick_slab",
    "stair":   "polished_blackstone_brick_stairs",
    "wall":    "polished_blackstone_brick_wall",
    "dslab":   "polished_deepslate_slab",
    "dstair":  "polished_deepslate_stairs",
    "dwall":   "polished_deepslate_wall",
    "kslab":   "blackstone_slab",
    "kstair":  "blackstone_stairs",
    "bars":    "iron_bars",
    # THE LAND'S OWN `arm` IS `dark_oak_trapdoor` AND IT IS NOT USED HERE. `parkways` gives
    # Prismworks that block for its street furniture; on a building it is fifty cells of WARM
    # BROWN roof on a land whose whole identity is cold, and it read as exactly that from every
    # bearing of the first orbit sheet. An inherited palette entry is a suggestion, not an order.
    # AND NOT `iron_trapdoor` EITHER. It is the obvious cold metal shutter and it is a REDSTONE
    # MECHANISM: a door nobody can open in a land that deliberately builds no circuit. The
    # circuit inspection caught it on the first run, which is exactly what it is for.
    "louvre":  "warped_trapdoor",              # roof slats - the one cold timber this economy has
    "shutter": "warped_trapdoor",              # ...and the same panel standing in a window
    "sill":    "gray_wool",                    # 67 - the one course of a reveal that catches light
    "rail":    "warped_fence",
    "lamp":    "soul_lantern",
    "chain":   "iron_chain",
    "rod":     "end_rod",
    "sign":    "warped",                       # -> warped_wall_sign
}

PRISMWORKS_BUILDS = {
    "kind": None,                # gate | array | vault | ascent | deck | gallery
    "at": None,                  # [V, U] - the lot's near corner in park coordinates
    "size": None,                # [depth along V, width along U] - the lot, and the bound
    "height": None,              # canvas height; each kind has its own default
    "title": "",                 # what the building calls itself, on its own sign
    "sub": "",                   # the second line
    "keep_clear": (),            # [[v, u, y]] lot-local cells nothing may occupy (lamp arms)
    "seed": 0,
}

_DEFAULT_H = {"gate": 26, "array": 25, "vault": 29, "ascent": 86, "deck": 15, "gallery": 12}

_WEST, _EAST, _NORTH, _SOUTH = "west", "east", "north", "south"


def _dir(dv: int, du: int) -> str:
    """The compass name of a step in lot coordinates. Canvas x is V (+x east), z is U (+z south)."""
    if dv:
        return _EAST if dv > 0 else _WEST
    return _SOUTH if du > 0 else _NORTH


# ---------------------------------------------------------------------------- the lot


class _Lot:
    """The lot's frame. Every cell in this module is placed through it, so an axis bug is one bug.

    It also owns the two hard boundaries: **the lot** (a cell outside it is cropped at placement
    and lost, so it is refused and counted here instead) and **`keep_clear`** (the park's own lamp
    arms, which reach one cell into five of these six lots at world Y209).
    """

    def __init__(self, c: Canvas, p: dict):
        self.c = c
        self.dv, self.du = int(p["size"][0]), int(p["size"][1])
        self.keep = {(int(a), int(b), int(y)) for a, b, y in (p.get("keep_clear") or ())}
        self.seed = int(p.get("seed", 0))
        self.refused_out = 0
        self.refused_keep = 0
        self._state: dict = {}
        self.lights = 0
        self.signs = 0

    # -- materials --------------------------------------------------------
    def blk(self, name: str) -> int:
        if name not in self._state:
            self._state[name] = self.c.state(name)
        return self._state[name]

    def put(self, v: int, u: int, y: int, name: str, **props) -> bool:
        v, u, y = int(v), int(u), int(y)
        if not (0 <= v < self.dv and 0 <= u < self.du):
            self.refused_out += 1
            return False
        if (v, u, y) in self.keep:
            self.refused_keep += 1
            return False
        if not (0 <= y < self.c.sy):
            self.refused_out += 1
            return False
        blk = self.c.raw_state(name, **props) if props else self.blk(name)
        return self.c.put(v, y, u, blk)

    def has(self, v: int, u: int, y: int) -> bool:
        return self.c.solid(int(v), int(y), int(u))

    def name_at(self, v: int, u: int, y: int) -> str:
        return self.c.get_name(int(v), int(y), int(u)).split(":")[-1]

    def clear(self, v: int, u: int, y: int) -> None:
        self.c.put(int(v), int(y), int(u), 0)

    # -- bulk -------------------------------------------------------------
    def fill(self, v0, u0, y0, v1, u1, y1, name, **props) -> int:
        n = 0
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for v in range(min(v0, v1), max(v0, v1) + 1):
                for u in range(min(u0, u1), max(u0, u1) + 1):
                    n += bool(self.put(v, u, y, name, **props))
        return n

    def hollow(self, v0, u0, y0, v1, u1, y1, name, **props) -> int:
        """A box shell: every cell of the box that touches its own boundary."""
        n = 0
        for y in range(y0, y1 + 1):
            for v in range(v0, v1 + 1):
                for u in range(u0, u1 + 1):
                    if v in (v0, v1) or u in (u0, u1) or y in (y0, y1):
                        n += bool(self.put(v, u, y, name, **props))
        return n

    def ring(self, v0, u0, v1, u1, y, name, **props) -> int:
        n = 0
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if v in (v0, v1) or u in (u0, u1):
                    n += bool(self.put(v, u, y, name, **props))
        return n

    def cut(self, v0, u0, y0, v1, u1, y1) -> None:
        for y in range(y0, y1 + 1):
            for v in range(v0, v1 + 1):
                for u in range(u0, u1 + 1):
                    self.clear(v, u, y)

    # -- fittings ---------------------------------------------------------
    def lamp(self, v, u, y, *, hanging: bool) -> bool:
        """A soul lantern, on a support that is CHECKED rather than assumed.

        A lantern hangs from the block above it or stands on the block below it, and a lantern
        with neither is a placement problem the audit reports and a render draws identically to a
        correct one. `parkrail` learned the same thing about its wall signs.
        """
        if hanging and not self.has(v, u, y + 1):
            return False
        if not hanging and not self.has(v, u, y - 1):
            return False
        if self.put(v, u, y, PRISM["lamp"], hanging="true" if hanging else "false",
                    waterlogged="false"):
            self.lights += 1
            return True
        return False

    def sign(self, v, u, y, facing: str, lines) -> bool:
        """A wall sign in the cell IN FRONT of its wall, its text facing away from its support.

        Four of the earlier park's seven building kinds shipped a sign hung on the one column that
        has an opening in it, and it is invisible in every render: a wall sign floating in air
        draws exactly like one on a wall. So the support is tested and a refusal is returned.
        """
        dv = {_EAST: 1, _WEST: -1}.get(facing, 0)
        du = {_SOUTH: 1, _NORTH: -1}.get(facing, 0)
        if not self.has(v - dv, u - du, y):
            return False
        if self.has(v, u, y):
            return False
        if not self.put(v, u, y, f"{PRISM['sign']}_wall_sign", facing=facing, waterlogged="false"):
            return False
        self.c.sign_text(int(v), int(y), int(u),
                         front=[str(t)[:SIGN_WIDTH] for t in list(lines)[:4]],
                         colour="light_blue", glowing=True)
        self.signs += 1
        return True


# ---------------------------------------------------------------------------- the grammar


def _perimeter(v0, u0, v1, u1):
    """(v, u, dv, du, t) for every cell of a rectangle's boundary, with its OUTWARD normal.

    `t` is the cell's index along its own run, which is what the bay rhythm counts - and the run
    has to be counted along the wall rather than across it. A run scored on the wrong axis comes
    out as 1 everywhere, which is how the deck soffit shipped 184 runs of one or two cells and
    called it a coffer grid.
    """
    for u in range(u0, u1 + 1):
        yield v0, u, -1, 0, u - u0
        yield v1, u, 1, 0, u - u0
    for v in range(v0 + 1, v1):
        yield v, u0, 0, -1, v - v0
        yield v, u1, 0, 1, v - v0


def _corner(v, u, v0, u0, v1, u1) -> bool:
    return v in (v0, v1) and u in (u0, u1)


def _bay_wall(L: _Lot, v0, u0, v1, u1, y0, h, *, bay=6, sill=2, win=3, glaze="bars",
              void=None, band=None, weather=True):
    """One rectangular wall, in the land's grammar. Returns the cells it left open.

    THE RHYTHM IS THE ARCHITECTURE. A pier every `bay` in the lighter stone breaks the run into
    bays; each bay carries a recessed panel with a window in it; the courses between are the
    field. Nothing here is damage and nothing is random - the only variation is a per-CELL
    weathering hash, and it is on the cell rather than on the course because hashed per course a
    wall comes out as horizontal stripes of one material (the deck soffit shipped exactly that).
    """
    opened = 0
    for v, u, dv, du, t in _perimeter(v0, u0, v1, u1):
        pier = _corner(v, u, v0, u0, v1, u1) or (t % bay == 0)
        for y in range(y0, y0 + h):
            if void and void(v, u, y):
                opened += 1
                continue
            if pier:
                L.put(v, u, y, PRISM["pier"])
                continue
            ry = y - y0
            if sill <= ry < sill + win and (t % bay) in (bay // 2, bay // 2 + 1 if bay > 3 else bay // 2):
                # THE WINDOW ITSELF - and a trapdoor screen has to STAND, not lie down. Placed
                # with its default state a trapdoor is a horizontal panel on the floor of its own
                # cell, so a clerestory glazed that way is a row of shelves in an open hole. An
                # OPEN trapdoor is the vertical slab Minecraft never shipped, and `facing` is the
                # face it hangs on: the wall's own outward normal, so the shutter sits in the
                # opening rather than across it.
                mat = PRISM[glaze] if glaze in PRISM else glaze
                if mat.endswith("_trapdoor"):
                    L.put(v, u, y, mat, facing=_dir(dv, du), half="bottom", open="true",
                          powered="false", waterlogged="false")
                else:
                    L.put(v, u, y, mat)
                continue
            if sill - 1 == ry:
                L.put(v, u, y, PRISM["sill"])            # the sill catches light; the head does not
                continue
            if ry == sill + win:
                L.put(v, u, y, PRISM["recess"])          # ...and the head is the shadow over it
                continue
            name = PRISM["field"]
            if weather and hash01(L.seed, v, u, y, 71) < 0.11:
                name = PRISM["worn"]
            L.put(v, u, y, name)
        if band is not None and y0 <= band < y0 + h and not pier:
            L.put(v, u, band, PRISM["signal"])
    return opened


def _string_course(L: _Lot, v0, u0, v1, u1, y, *, out=True, mat=None):
    """A PROUD band: a slab in the cell OUTSIDE the wall face, so the line is a projection.

    This is the whole answer to a land whose stones sit within 12 RGB of each other. A tone step
    of 23 reads at ten blocks; a one-cell projection casts a shadow and reads at a hundred.
    """
    mat = mat or PRISM["dslab"]
    n = 0
    for v, u, dv, du, _t in _perimeter(v0, u0, v1, u1):
        n += bool(L.put(v + (dv if out else 0), u + (du if out else 0), y, mat, type="top",
                        waterlogged="false"))
    return n


def _cornice(L: _Lot, v0, u0, v1, u1, y, *, mat=None):
    """A corbel: an upside-down stair in the cell outside the wall, leaning INTO it.

    A stair's TALL side IS its `facing`, so a corbel under an overhang faces the wall it grows
    from. Our renderer draws a stair the wrong way round identically to a right one, so this is
    asserted in `tests/test_prismworks_builds.py` and never eyeballed.
    """
    mat = mat or PRISM["kstair"]
    n = 0
    for v, u, dv, du, _t in _perimeter(v0, u0, v1, u1):
        n += bool(L.put(v + dv, u + du, y, mat, facing=_dir(-dv, -du), half="top",
                        shape="straight", waterlogged="false"))
    return n


def _skirt(L: _Lot, v0, u0, v1, u1, y, *, mat=None):
    """The plinth's own splay: a bottom-half stair outside the wall, tall side against it."""
    mat = mat or PRISM["kstair"]
    n = 0
    for v, u, dv, du, _t in _perimeter(v0, u0, v1, u1):
        n += bool(L.put(v + dv, u + du, y, mat, facing=_dir(-dv, -du), half="bottom",
                        shape="straight", waterlogged="false"))
    return n


def _parapet(L: _Lot, v0, u0, v1, u1, y, *, every=3, tall=2, lamp_every=0):
    """A parapet with REAL merlon gaps, and the gaps are left empty by the loop that draws it.

    Building a full ring first and alternating merlons over it repaints cells that already exist:
    it alternates perfectly, changes nothing, and the crown ships as a plain drum. The void
    tower shipped that once and nothing about the code looked wrong.
    """
    merlons = 0
    for v, u, dv, du, t in _perimeter(v0, u0, v1, u1):
        corner = _corner(v, u, v0, u0, v1, u1)
        if corner or t % every == 0:
            for k in range(tall):
                L.put(v, u, y + k, PRISM["high"] if k == tall - 1 else PRISM["pier"])
            merlons += 1
            if lamp_every and (corner or t % (every * lamp_every) == 0):
                L.put(v, u, y + tall, PRISM["glow"])
        else:
            L.put(v, u, y, PRISM["wall"], waterlogged="false")
    return merlons


def _roof(L: _Lot, v0, u0, v1, u1, y, *, rib=5, coping=True):
    """A flat roof that is READ FROM ABOVE, because in this park it is.

    Anyone standing on the Prism Ascent's crown or the Forge Deck's gallery looks down on every
    other roof in the land, and a flat plate of one block is the largest blank surface a building
    has. So the plate carries a rib grid of slabs on a WORLD-aligned rhythm - world-aligned so the
    ribs of two neighbouring buildings line up rather than each starting from its own corner - and
    a coping ring one course proud at the edge.
    """
    L.fill(v0, u0, y, v1, u1, y, PRISM["field"])
    ribs = 0
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            if v % rib == 0 or u % rib == 0:
                ribs += bool(L.put(v, u, y + 1, PRISM["dslab"], type="bottom",
                                   waterlogged="false"))
    if coping:
        L.ring(v0, u0, v1, u1, y + 1, PRISM["kslab"], type="bottom", waterlogged="false")
    return ribs


def _pilasters(L: _Lot, v0, u0, v1, u1, y0, h, *, bay=6):
    """A base and a capital on every pier: two projecting stairs, outside the wall face.

    The cheapest real trim there is, and the one that most changes whether a bay rhythm reads as
    a rhythm or as a stripe. It is applied OUTSIDE the wall, so it costs the building nothing
    inside and casts a shadow where the eye is.
    """
    n = 0
    for v, u, dv, du, t in _perimeter(v0, u0, v1, u1):
        if not (_corner(v, u, v0, u0, v1, u1) or t % bay == 0):
            continue
        n += bool(L.put(v + dv, u + du, y0, PRISM["dstair"], facing=_dir(-dv, -du),
                        half="bottom", shape="straight", waterlogged="false"))
        n += bool(L.put(v + dv, u + du, y0 + h - 1, PRISM["dstair"], facing=_dir(-dv, -du),
                        half="top", shape="straight", waterlogged="false"))
    return n


def _floor(L: _Lot, v0, u0, v1, u1, y, *, mat=None, inlay=None, grid=5):
    """An interior floor, patterned on a WORLD-aligned grid so the pattern survives a step."""
    mat, inlay = mat or PRISM["floor"], inlay or PRISM["thresh"]
    n = 0
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            on = (v % grid == 0) or (u % grid == 0)
            n += bool(L.put(v, u, y, inlay if on else mat))
    return n


def _colonnade(L: _Lot, v0, u0, v1, u1, y0, h, *, step, thick=1, beam=True, lamp_every=2,
               rail_at=None):
    """A row of piers with a beam over them: the one form that is open and still architecture.

    Openness is not the absence of a wall, it is a rhythm you can see through. Every pier carries
    the beam, every second bay carries a lamp under it, and the whole row is one connected piece
    with whatever the beam springs from.
    """
    piers = 0
    along_v = (v1 - v0) >= (u1 - u0)
    span = range(v0, v1 + 1, step) if along_v else range(u0, u1 + 1, step)
    for k, a in enumerate(span):
        for t in range(thick):
            if along_v:
                pv, pu = min(a + t, v1), u0
            else:
                pv, pu = v0, min(a + t, u1)
            for y in range(y0, y0 + h):
                L.put(pv, pu, y, PRISM["pier"] if y in (y0, y0 + h - 1) else PRISM["field"])
        piers += 1
    if beam:
        y = y0 + h
        if along_v:
            L.fill(v0, u0, y, v1, u1, y, PRISM["field"])
            L.fill(v0, u0, y + 1, v1, u1, y + 1, PRISM["kslab"], type="bottom",
                   waterlogged="false")
        else:
            L.fill(v0, u0, y, v1, u1, y, PRISM["field"])
            L.fill(v0, u0, y + 1, v1, u1, y + 1, PRISM["kslab"], type="bottom",
                   waterlogged="false")
        for k, a in enumerate(span):
            if lamp_every and k % lamp_every == 0:
                if along_v:
                    L.lamp(min(a, v1), u0, y - 1, hanging=True)
                else:
                    L.lamp(v0, min(a, u1), y - 1, hanging=True)
    if rail_at is not None:
        # a rail between the piers, in the one cold timber this economy has: an arcade you can
        # see through and still not fall off the side of.
        for a in (range(v0, v1 + 1) if along_v else range(u0, u1 + 1)):
            pv, pu = (a, u0) if along_v else (v0, a)
            if not L.has(pv, pu, y0 + rail_at):
                L.put(pv, pu, y0 + rail_at, PRISM["rail"], waterlogged="false")
    return piers


def _portal(L: _Lot, v, u0, u1, y0, h, normal_v: int, *, reveal=True):
    """A doorway: the void, its reveal, its lintel and its head. The void is CUT, never skipped.

    A doorway left out by the wall loop and then punched afterwards repaints cells that already
    exist; a doorway cut afterwards leaves the reveal of whatever the wall happened to put there.
    Both were shipped once here. This cuts the hole and then draws its frame, in that order.
    """
    L.cut(v, u0, y0, v, u1, y0 + h - 1)
    if reveal:
        for y in range(y0, y0 + h):
            L.put(v, u0 - 1, y, PRISM["recess"])
            L.put(v, u1 + 1, y, PRISM["recess"])
        for u in range(u0 - 1, u1 + 2):
            L.put(v, u, y0 + h, PRISM["recess"])
    # a stepped head, which is what a voxel arch actually is
    for k, inset in enumerate((0, 1, 2)):
        for u in range(u0 + inset, u1 - inset + 1):
            L.put(v, u, y0 + h + 1 + k, PRISM["pier"] if k == 2 else PRISM["field"])
    # ...and its own light, in the reveal rather than in the opening
    L.lamp(v - normal_v, u0 - 1, y0 + h - 1, hanging=True)
    L.lamp(v - normal_v, u1 + 1, y0 + h - 1, hanging=True)
    return u1 - u0 + 1


# ---------------------------------------------------------------------------- the six


def _gate(L: _Lot, p: dict) -> dict:
    """PF FOUNDRY GATE - the threshold. You do not look at it, you walk THROUGH it.

    A land's gate is the one building whose job is a hole. So the mass is two pylons, the opening
    between them is seven wide and the whole composition is read from the spine at V18, straight
    down the U448 spur. Behind it a twin arcade carries the axis twenty-six courses into the land
    and then stops, leaving the rear quarter of the lot open lawn.
    """
    dv, du = L.dv, L.du
    door = 18                      # lot-local U of the spur, U448 - U430
    # ---- the portal block, inset ONE CELL FROM THE LOT LINE ON EVERY SIDE. That cell is not
    # politeness: the string course, the corbel and the plinth splay all stand in the cell OUTSIDE
    # the wall face, so a wall on the boundary throws a hundred and three of them past the lot
    # and they are cropped at placement. A trim course with a hundred cells missing is not trim.
    v0, v1, u0, u1 = 1, 21, 1, du - 2
    h = 20
    L.hollow(v0, u0, 0, v1, u1, 0, PRISM["pier"])
    _bay_wall(L, v0, u0, v1, u1, 1, h, bay=6, sill=4, win=4, glaze="bars",
              void=lambda v, u, y: v in (v0, v1) and door - 3 <= u <= door + 3 and 1 <= y <= 8)
    # the passage itself, right through the block
    L.cut(v0, door - 3, 1, v1, door + 3, 8)
    L.fill(v0, door - 3, 0, v1, door + 3, 0, PRISM["thresh"])
    for v in (v0, v1):
        _portal(L, v, door - 3, door + 3, 1, 8, -1 if v == v0 else 1, reveal=True)
    # the passage's own soffit and its line of light
    for v in range(v0, v1 + 1):
        for u in (door - 4, door + 4):
            for y in range(1, 9):
                L.put(v, u, y, PRISM["recess"] if (y % 4) else PRISM["signal"])
        if v % 4 == 2:
            L.lamp(v, door, 8, hanging=True)
    # ---- the overbridge: a chamber over the passage, which is what makes a gate a building
    L.fill(v0, door - 4, 9, v1, door + 4, 9, PRISM["field"])
    _bay_wall(L, v0, door - 4, v1, door + 4, 10, 6, bay=4, sill=1, win=3, glaze="shutter")
    # ---- the crown. THE ROOF IS A PLATE, NOT A RING: the four signal masts stand on it, and a
    # ring leaves them over the hall's own open middle - four six-cell fragments hanging in air,
    # which audits as a clean solid and reports as "needs temporary scaffold".
    _roof(L, v0, u0, v1, u1, h + 1, rib=5, coping=False)
    _string_course(L, v0, u0, v1, u1, 9)
    _pilasters(L, v0, u0, v1, u1, 1, h, bay=6)
    _cornice(L, v0, u0, v1, u1, h + 1)
    L.ring(v0, u0, v1, u1, h + 1, PRISM["dark"])
    merlons = _parapet(L, v0, u0, v1, u1, h + 2, every=3, tall=2, lamp_every=3)
    # the two pylons carry the signal above everything else
    for u in (u0 + 2, u1 - 2):
        for v in (v0 + 2, v1 - 2):
            L.fill(v, u, h + 2, v, u, h + 4, PRISM["pier"])
            L.put(v, u, h + 5, PRISM["high"])
            L.put(v, u, h + 6, PRISM["glow"])
            L.put(v, u, h + 7, PRISM["rod"], facing="up")
    _skirt(L, v0, u0, v1, u1, 0)
    # ---- the arcade: the axis carried into the land, and then stopped
    piers = 0
    for u in (door - 5, door + 5):
        piers += _colonnade(L, 24, u, 44, u, 0, 7, step=5, beam=True, lamp_every=2, rail_at=2)
    # cross beams tie the two rows together, so the arcade is a frame rather than two fences
    for v in range(24, 45, 5):
        L.fill(v, door - 5, 7, v, door + 5, 7, PRISM["field"])
        L.fill(v, door - 5, 8, v, door + 5, 8, PRISM["kslab"], type="bottom", waterlogged="false")
    # ...and it springs from the portal block rather than standing beside it
    for u in (door - 5, door + 5):
        L.fill(v1, u, 0, 24, u, 0, PRISM["thresh"])
        L.fill(v1, u, 7, 24, u, 7, PRISM["field"])
    # louvres between the cross beams: an open roof that is still a roof
    for v in range(25, 44):
        if v % 5:
            for u in range(door - 4, door + 5, 2):
                L.put(v, u, 8, PRISM["louvre"], facing="north", half="top", open="false",
                      powered="false", waterlogged="false")
    # the threshold reaches the lot line, so the passage meets the spur's own last paved cell
    L.fill(0, door - 3, 0, v0, door + 3, 0, PRISM["thresh"])
    L.sign(v0 - 1, door - 4, 6, _WEST, ["PRISMWORKS", "", "FOUNDRY GATE", "keep to the line"])
    L.sign(v1 + 1, door + 4, 6, _EAST, ["FOUNDRY GATE", "", "the works", "beyond"])
    return {"passage_width": 7, "merlons": merlons, "arcade_piers": piers, "portal_height": 20}


def _array(L: _Lot, p: dict) -> dict:
    """PF PRISM ARRAY - the exhibit hall: a lit grid of columns under a clerestory.

    The hall is the OPEN counterpart to the Vault next door: a loggia to the street, tall screened
    bays all round, and a raised clerestory over the middle that is the only part of the land
    other than the Ascent you can see over a wall. Inside it is a five-by-five grid of prism
    columns - the array - and it is a grid rather than a scatter for the reason the thicket's
    drifts are drifts: at this scale a scatter reads as confetti and a rhythm reads as intent.
    """
    dv, du = L.dv, L.du
    door = 25                      # U496 - U471
    v0, v1, u0, u1 = 3, 45, 3, du - 4
    h = 13
    L.hollow(v0, u0, 0, v1, u1, 0, PRISM["pier"])
    _floor(L, v0 + 1, u0 + 1, v1 - 1, u1 - 1, 0, grid=6)
    _bay_wall(L, v0, u0, v1, u1, 1, h, bay=6, sill=3, win=6, glaze="bars",
              void=lambda v, u, y: v == v0 and door - 2 <= u <= door + 2 and 1 <= y <= 6)
    _portal(L, v0, door - 2, door + 2, 1, 6, -1)
    L.fill(v0, door - 2, 0, v0 - 3, door + 2, 0, PRISM["thresh"])
    # ---- the loggia: three courses of colonnade standing in front of the hall's own front
    piers = _colonnade(L, v0 - 3, u0 + 1, v0 - 3, u1 - 1, 0, 8, step=6, beam=True, lamp_every=2,
                       rail_at=2)
    for u in range(u0 + 1, u1, 6):
        L.fill(v0 - 3, u, 0, v0, u, 0, PRISM["thresh"])
        L.fill(v0 - 2, u, 9, v0, u, 9, PRISM["field"])
    # ---- the roof, and the clerestory that lifts its middle
    _roof(L, v0, u0, v1, u1, h + 1, rib=5)
    _string_course(L, v0, u0, v1, u1, 8)
    _pilasters(L, v0, u0, v1, u1, 1, h, bay=6)
    _cornice(L, v0, u0, v1, u1, h + 1)
    _parapet(L, v0, u0, v1, u1, h + 2, every=4, tall=1, lamp_every=4)
    cv0, cu0, cv1, cu1 = v0 + 10, u0 + 12, v1 - 10, u1 - 12
    _bay_wall(L, cv0, cu0, cv1, cu1, h + 2, 6, bay=4, sill=1, win=4, glaze="shutter",
              weather=False, band=h + 7)
    _roof(L, cv0, cu0, cv1, cu1, h + 8, rib=4)
    _cornice(L, cv0, cu0, cv1, cu1, h + 8)
    _parapet(L, cv0, cu0, cv1, cu1, h + 9, every=3, tall=1, lamp_every=2)
    # the lantern's own light, hung from the underside of the clerestory roof over the array
    for v in range(cv0 + 2, cv1, 5):
        for u in range(cu0 + 2, cu1, 5):
            L.put(v, u, h + 7, PRISM["chain"], axis="y")
            L.lamp(v, u, h + 6, hanging=True)
    # ---- the array itself: a grid of prism columns, each one a signal
    cols = 0
    for v in range(v0 + 5, v1 - 3, 8):
        for u in range(u0 + 5, u1 - 3, 8):
            for y in range(1, h - 1):
                L.put(v, u, y, PRISM["field"] if y % 4 else PRISM["signal"])
            L.put(v, u, h - 1, PRISM["high"])
            L.put(v, u, h, PRISM["glow"])
            L.put(v, u, h + 1, PRISM["field"])
            for dv_, du_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                L.put(v + dv_, u + du_, h - 1, PRISM["dslab"], type="bottom", waterlogged="false")
                L.put(v + dv_, u + du_, 1, PRISM["dstair"], facing=_dir(dv_, du_),
                      half="bottom", shape="straight", waterlogged="false")
            cols += 1
    _skirt(L, v0, u0, v1, u1, 0)
    L.sign(v0 - 1, door - 3, 5, _WEST, ["PRISM ARRAY", "", "follow the lit", "columns"])
    return {"columns": cols, "loggia_piers": piers, "clerestory_h": h + 9, "hall_h": h}


def _vault(L: _Lot, p: dict) -> dict:
    """PF RESONANCE VAULT - the closed block, and the deliberate opposite of the Array.

    Four buttressed corners, a battered base, one deep recessed portal and slit windows: the whole
    point of it is that you cannot see in. Its openness is spent on ONE thing - an arcaded
    ambulatory that wraps three sides - so the building is approachable without being transparent.
    Above it a stepped resonator stack narrows in three stages to a signal ring.

    THE FRONT COURSE IS A PLINTH AND NOTHING ELSE. Two of the park's lamp arms reach into this
    lot's front row at world Y209; a plinth is one course tall, so the row is usable at ground
    level and empty where the arm is. The wall starts one course in.
    """
    dv, du = L.dv, L.du
    door = 20                      # U491 - U471
    # THE AMBULATORY IS THREE CELLS OUT FROM THE BLOCK AND HAS TO FIT INSIDE THE LOT. Written
    # against a block on the lot's own margin, all 272 cells of both side arcades landed outside
    # the lot and were cropped: the building audits clean, one connected piece, with two of its
    # three colonnades simply absent. The block is set five in from each side for that colonnade,
    # its tie beams and its own trim.
    v0, v1, u0, u1 = 1, 40, 5, du - 6
    h = 16
    L.ring(v0 - 1, u0 - 1, v1 + 1, u1 + 1, 0, PRISM["thresh"])
    L.hollow(v0, u0, 0, v1, u1, 0, PRISM["pier"])
    _floor(L, v0 + 1, u0 + 1, v1 - 1, u1 - 1, 0, grid=4)
    _bay_wall(L, v0, u0, v1, u1, 1, h, bay=5, sill=8, win=3, glaze="bars", band=h - 1,
              void=lambda v, u, y: v == v0 and door - 2 <= u <= door + 2 and 1 <= y <= 5)
    _portal(L, v0, door - 2, door + 2, 1, 5, -1)
    # ---- the corner buttresses: the mass that says vault, and it steps DOWN away from the block
    for cv, cu, sv, su in ((v0, u0, 1, 1), (v0, u1, 1, -1), (v1, u0, -1, 1), (v1, u1, -1, -1)):
        for a in range(3):
            for b in range(3):
                if a + b > 3:
                    continue
                top = max(3, h - 2 - 3 * max(a, b))
                for y in range(0, top):
                    L.put(cv + sv * a, cu + su * b, y,
                          PRISM["pier"] if y % 5 else PRISM["dark"])
                L.put(cv + sv * a, cu + su * b, top, PRISM["kslab"], type="top",
                      waterlogged="false")
    # ---- the ambulatory: an arcade wrapping the three sides that are not the front
    piers = 0
    piers += _colonnade(L, v0 + 4, u0 - 3, v1 - 4, u0 - 3, 0, 6, step=5, beam=True, lamp_every=2,
                        rail_at=2)
    piers += _colonnade(L, v0 + 4, u1 + 3, v1 - 4, u1 + 3, 0, 6, step=5, beam=True, lamp_every=2,
                        rail_at=2)
    piers += _colonnade(L, v1 + 3, u0 - 3, v1 + 3, u1 + 3, 0, 6, step=5, beam=True, lamp_every=2)
    for u in (u0 - 3, u1 + 3):
        L.fill(v1 + 3, u, 0, v1 + 3, u, 6, PRISM["pier"])
    # tie the arcade back to the block, so the ambulatory has a roof and one component
    for v in range(v0 + 4, v1 - 3, 5):
        for u, s in ((u0 - 3, 1), (u1 + 3, -1)):
            L.fill(v, u, 7, v, u + s * 3, 7, PRISM["field"])
            L.fill(v, u, 8, v, u + s * 3, 8, PRISM["kslab"], type="bottom", waterlogged="false")
    for u in range(u0 - 3, u1 + 4, 5):
        L.fill(v1 + 3, u, 7, v1, u, 7, PRISM["field"])
        L.fill(v1 + 3, u, 8, v1, u, 8, PRISM["kslab"], type="bottom", waterlogged="false")
    # ---- the resonator: three stages, then the ring
    _string_course(L, v0, u0, v1, u1, 7)
    _pilasters(L, v0, u0, v1, u1, 1, h, bay=5)
    _roof(L, v0, u0, v1, u1, h + 1, rib=5)
    _cornice(L, v0, u0, v1, u1, h + 1)
    _parapet(L, v0, u0, v1, u1, h + 2, every=4, tall=1, lamp_every=3)
    sv0, su0, sv1, su1 = v0 + 8, u0 + 8, v1 - 8, u1 - 8
    y = h + 2
    for k, inset in enumerate((0, 3, 6)):
        a, b, cc, d = sv0 + inset, su0 + inset, sv1 - inset, su1 - inset
        L.hollow(a, b, y, cc, d, y + 3, PRISM["field"])
        # THE CAP IS A PLATE, NOT A RING. The next stage is inset three cells all round, so over a
        # ring it stands on nothing - the resonator shipped as two fragments of 788 and 464 cells,
        # one connected solid in the audit and a pair of floating boxes in the world.
        L.fill(a, b, y + 4, cc, d, y + 4, PRISM["pier"])
        _cornice(L, a, b, cc, d, y + 4)
        for v, u, dv_, du_, t in _perimeter(a, b, cc, d):
            if t % 3 == 0:
                L.put(v, u, y + 1, PRISM["signal"])
        y += 5
    # the ring: an open lantern of posts and bars carrying the signal
    a, b, cc, d = sv0 + 6, su0 + 6, sv1 - 6, su1 - 6
    for v, u, dv_, du_, t in _perimeter(a, b, cc, d):
        if _corner(v, u, a, b, cc, d) or t % 2 == 0:
            L.put(v, u, y, PRISM["high"])
            L.put(v, u, y + 1, PRISM["glow"])
        else:
            L.put(v, u, y, PRISM["bars"])
    L.ring(a, b, cc, d, y + 2, PRISM["dslab"], type="bottom", waterlogged="false")
    for v, u in ((a, b), (a, d), (cc, b), (cc, d)):
        L.put(v, u, y + 2, PRISM["rod"], facing="up")
    _skirt(L, v0, u0, v1, u1, 0)
    L.sign(v0 - 1, door - 3, 4, _WEST, ["RESONANCE", "VAULT", "", "three inputs"])
    return {"buttresses": 4, "ambulatory_piers": piers, "resonator_top": y + 2, "block_h": h}


def _ascent(L: _Lot, p: dict) -> dict:
    """PF PRISM ASCENT - the headline, and one of three skyline dominants in the whole park.

    **IT IS COLUMNAR AND PLANAR, WHICH IS WHAT THIS MEDIUM RENDERS NATIVELY.** Everything this
    repo has measured about voxel form says the same thing: a spread wing, a neck, a stilt leg, a
    flat sheet and a straight taper read instantly, and compound volume does not. So the Ascent is
    a square core that TAPERS in four stages, four PLANAR fin blades on its cardinal faces whose
    reach shortens as they rise, and a lit crown - a column with blades, read against the sky.

    Around its foot a ring podium, and from the spine a colonnaded causeway twenty-six courses
    long on the U563 axis, so the approach is the composition: you walk the axis, the podium opens,
    the tower stands in the middle of it.

    The tallest thing in the park today is the Sky Lift at 74 courses over the lawn. This tops out
    at 84, which is a dominant rather than a competitor, and it is the number to move if the park
    ever gains something taller.
    """
    dv, du = L.dv, L.du
    door = 36                      # U563 - U527
    cv, cu = 46, 36                # the tower's own centre: the lot's centre in both axes
    # ---- the causeway: two colonnades and a paved axis, from the lot line to the podium
    piers = 0
    for u in (door - 4, door + 4):
        piers += _colonnade(L, 0, u, 24, u, 0, 8, step=6, beam=True, lamp_every=2, rail_at=2)
    L.fill(0, door - 3, 0, 25, door + 3, 0, PRISM["thresh"])
    for v in range(0, 25, 6):
        L.fill(v, door - 4, 8, v, door + 4, 8, PRISM["field"])
        L.fill(v, door - 4, 9, v, door + 4, 9, PRISM["kslab"], type="bottom", waterlogged="false")
        for u in (door - 4, door + 4):
            L.put(v, u, 10, PRISM["high"])
            L.put(v, u, 11, PRISM["glow"])
    # ---- the podium: a ring building round the tower's foot
    v0, v1, u0, u1 = cv - 20, cv + 20, cu - 20, cu + 19
    h = 11
    L.hollow(v0, u0, 0, v1, u1, 0, PRISM["pier"])
    _bay_wall(L, v0, u0, v1, u1, 1, h, bay=6, sill=3, win=4, glaze="bars",
              void=lambda v, u, y: (v == v0 and door - 3 <= u <= door + 3 and 1 <= y <= 6)
              or (v == v1 and door - 3 <= u <= door + 3 and 1 <= y <= 6))
    for v, n in ((v0, -1), (v1, 1)):
        _portal(L, v, door - 3, door + 3, 1, 6, n)
    L.fill(v0, door - 3, 0, v1, door + 3, 0, PRISM["thresh"])
    _string_course(L, v0, u0, v1, u1, 6)
    _pilasters(L, v0, u0, v1, u1, 1, h, bay=6)
    _roof(L, v0, u0, v1, u1, h + 1, rib=5)
    _cornice(L, v0, u0, v1, u1, h + 1)
    _parapet(L, v0, u0, v1, u1, h + 2, every=4, tall=1, lamp_every=3)
    # the podium is a RING: its middle is the open court the tower stands in
    L.cut(v0 + 6, u0 + 6, h + 1, v1 - 6, u1 - 6, h + 1)
    L.cut(v0 + 6, u0 + 6, h + 2, v1 - 6, u1 - 6, h + 2)
    iv0, iu0, iv1, iu1 = v0 + 5, u0 + 5, v1 - 5, u1 - 5
    _bay_wall(L, iv0, iu0, iv1, iu1, 1, h, bay=6, sill=3, win=4, glaze="shutter", weather=False,
              void=lambda v, u, y: (v == iv0 or v == iv1) and door - 3 <= u <= door + 3
              and 1 <= y <= 6)
    _cornice(L, iv0, iu0, iv1, iu1, h + 1)
    L.fill(v0 + 1, door - 3, 0, v1 - 1, door + 3, 0, PRISM["thresh"])
    _floor(L, iv0 + 1, iu0 + 1, iv1 - 1, iu1 - 1, 0, grid=5)
    _skirt(L, v0, u0, v1, u1, 0)
    # ---- the tower: four stages, each one narrower than the one under it
    stages = [(0, 29, 6), (30, 47, 5), (48, 61, 4), (62, 71, 3)]
    for y0, y1, r in stages:
        a, b, cc, d = cv - r, cu - r, cv + r, cu + r
        for y in range(y0, y1 + 1):
            for v, u, dv_, du_, t in _perimeter(a, b, cc, d):
                corner = _corner(v, u, a, b, cc, d)
                if corner or t % 3 == 0:
                    L.put(v, u, y, PRISM["pier"])
                elif y % 6 == 5:
                    L.put(v, u, y, PRISM["signal"])
                elif (t % 3) == 1 and (y % 6) in (1, 2, 3):
                    L.put(v, u, y, PRISM["bars"])
                else:
                    L.put(v, u, y, PRISM["field"] if hash01(L.seed, v, u, y, 13) > 0.10
                          else PRISM["worn"])
        # A PROUD RING EVERY TWELVE COURSES. A seventy-course shaft with nothing horizontal on it
        # is a chimney; the rings are what give the taper something to be measured against, and
        # they are a projection rather than a tone step for the reason this whole land is - at
        # 23 luminance a step reads at ten blocks and a one-cell shadow reads at a hundred.
        for y in range(y0, y1):
            if y % 12 == 11:
                _string_course(L, a, b, cc, d, y)
        # EVERY SETBACK IS A FLOOR PLATE, AND THAT IS STRUCTURAL RATHER THAN DECORATIVE. The next
        # stage is inset one cell on every side, so its ring stands over the LAST stage's open
        # middle: without a plate at the seam each stage floats above the one under it. Stages 1
        # to 3 got away with it only because the fins happen to bridge them, and stage 4 - which
        # has no fins - shipped as a 573-cell fragment hanging twelve courses up.
        L.fill(a, b, y1, cc, d, y1, PRISM["field"])
        L.ring(a, b, cc, d, y1, PRISM["pier"])
        _cornice(L, a, b, cc, d, y1)
        _string_course(L, a, b, cc, d, y1 - 1)
        for v, u, dv_, du_, t in _perimeter(a, b, cc, d):
            if t % 6 == 0:
                L.put(v, u, y1, PRISM["glow"])
    # ---- the fins: four planar blades, and the reach shortens as they rise
    fins = 0
    for dv_, du_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for y in range(6, 59):
            reach = 2 + int(10 * (58 - y) / 52.0)
            r = 6 if y <= 29 else (5 if y <= 47 else 4)
            base_v, base_u = cv + dv_ * r, cu + du_ * r
            for k in range(1, reach + 1):
                v, u = base_v + dv_ * k, base_u + du_ * k
                for w in (-1, 0, 1):
                    wv, wu = (v, u + w) if dv_ else (v + w, u)
                    edge = (k == reach)
                    if edge:
                        L.put(wv, wu, y, PRISM["high"] if y % 8 == 0 else PRISM["pier"])
                    elif w == 0 and y % 8 == 0:
                        L.put(wv, wu, y, PRISM["signal"])
                    else:
                        L.put(wv, wu, y, PRISM["field"])
                fins += 1
            # THE LEADING LIGHT IS IN THE BLADE'S OWN EDGE, NOT A CELL BEYOND IT. Hung outboard it
            # is a knob on a knife: it puts two cells back on the silhouette every eighth course,
            # so the tower measured as widening after it had begun to taper - the exact belly this
            # form exists to avoid, produced by a lamp.
            if y % 8 == 0:
                L.put(base_v + dv_ * reach, base_u + du_ * reach, y, PRISM["glow"])
    # ---- the crown: an open lantern, and the only place the land goes bright
    a, b, cc, d = cv - 4, cu - 4, cv + 4, cu + 4
    for v, u, dv_, du_, t in _perimeter(a, b, cc, d):
        corner = _corner(v, u, a, b, cc, d)
        for y in range(72, 80):
            if corner or t % 2 == 0:
                L.put(v, u, y, PRISM["high"] if y % 3 == 0 else PRISM["pier"])
            elif y % 3 == 1:
                L.put(v, u, y, PRISM["bars"])
    L.fill(a, b, 71, cc, d, 71, PRISM["field"])
    # the crown's own cap is a plate for the same reason the setbacks are: the two stepped courses
    # over it are inset, and over a ring of posts they are seventy-five cells of nothing.
    L.fill(a, b, 80, cc, d, 80, PRISM["pier"])
    for v, u, dv_, du_, t in _perimeter(a, b, cc, d):
        if _corner(v, u, a, b, cc, d) or t % 4 == 0:
            L.put(v, u, 80, PRISM["glow"])
    _cornice(L, a, b, cc, d, 72)
    _cornice(L, a, b, cc, d, 80)
    L.fill(a + 1, b + 1, 81, cc - 1, d - 1, 81, PRISM["high"])
    L.fill(a + 2, b + 2, 82, cc - 2, d - 2, 82, PRISM["glow"])
    L.put(cv, cu, 83, PRISM["rod"], facing="up")
    for v, u in ((a, b), (a, d), (cc, b), (cc, d)):
        L.put(v, u, 81, PRISM["rod"], facing="up")
    L.sign(v0 - 1, door - 4, 5, _WEST, ["PRISM ASCENT", "", "practice free", "watch from deck"])
    return {"top": 84, "fin_cells": fins, "causeway_piers": piers, "stages": len(stages),
            "podium_h": h}


def _deck(L: _Lot, p: dict) -> dict:
    """PF FORGE DECK - the exit and observation gallery, in the band programmed for exactly that.

    Twenty-four deep and sixty-six long is a HORIZONTAL, so it is built as one: an arcaded
    undercroft carrying a raised deck, a balustrade the whole length, a canopy over the rear half
    on paired posts, and two flights up from the back promenade. It looks back at the Ascent,
    which is the reason the band exists.
    """
    dv, du = L.dv, L.du
    door = 33                      # U560 - U527
    # SIXTEEN OF THE BAND'S TWENTY-FOUR COURSES. Built wall to wall the gallery covered 99% of its
    # own lot, which is the thing the previous park was thrown out for; the rear seven courses are
    # left as lawn, which is also where the Ascent's exit traffic actually spreads out.
    v0, v1, u0, u1 = 1, 16, 1, du - 2
    deck_y = 5
    # ---- the undercroft: piers and arch heads, so the mass is open at the bottom
    piers = 0
    for u in range(u0, u1 + 1, 5):
        for v in (v0, v1):
            L.fill(v, u, 0, v, u, deck_y - 1, PRISM["pier"])
            piers += 1
        L.fill(v0, u, deck_y - 1, v1, u, deck_y - 1, PRISM["field"])
        # a corbelled arch head springing off each pier, both ways along the run
        for v, s in ((v0 + 1, -1), (v1 - 1, 1)):
            L.put(v, u, deck_y - 2, PRISM["kstair"], facing=_dir(s, 0), half="top",
                  shape="straight", waterlogged="false")
    for v in (v0, v1):
        L.fill(v, u0, deck_y - 1, v, u1, deck_y - 1, PRISM["field"])
        L.fill(v, u0, 0, v, u1, 0, PRISM["pier"])
    # the spandrel between the piers is a dark recess with a barred screen in it, so the
    # undercroft is a shaded arcade rather than a row of legs under a shelf
    for u in range(u0, u1 + 1):
        if u % 5 == 0:
            continue
        for v in (v0, v1):
            L.put(v, u, deck_y - 2, PRISM["recess"])
            if u % 5 in (2, 3):
                L.put(v, u, deck_y - 3, PRISM["bars"])
            if u % 10 == 1:
                L.put(v, u, deck_y - 2, PRISM["signal"])
    # ---- the deck
    _floor(L, v0, u0, v1, u1, deck_y, grid=5)
    _string_course(L, v0, u0, v1, u1, deck_y - 1)
    _cornice(L, v0, u0, v1, u1, deck_y)
    # ---- the balustrade, all round, with a gap at the head of each flight
    rails = 0
    for v, u, dv_, du_, t in _perimeter(v0, u0, v1, u1):
        if v == v0 and door - 2 <= u <= door + 2:
            continue
        if _corner(v, u, v0, u0, v1, u1) or t % 5 == 0:
            L.fill(v, u, deck_y + 1, v, u, deck_y + 2, PRISM["pier"])
            L.put(v, u, deck_y + 3, PRISM["high"])
            if t % 15 == 0:
                L.put(v, u, deck_y + 4, PRISM["glow"])
        else:
            L.put(v, u, deck_y + 1, PRISM["wall"], waterlogged="false")
            L.put(v, u, deck_y + 2, PRISM["dslab"], type="bottom", waterlogged="false")
            rails += 1
    # ---- the canopy over the rear half, on paired posts: shelter without a room
    can_y = deck_y + 6
    for u in range(u0 + 2, u1 - 1, 6):
        for v in (v0 + 3, v1 - 1):
            L.fill(v, u, deck_y + 1, v, u, can_y - 1, PRISM["pier"])
        L.fill(v0 + 3, u, can_y, v1 - 1, u, can_y, PRISM["field"])
        L.lamp(v0 + 4, u, can_y - 1, hanging=True)
    L.fill(v0 + 3, u0 + 2, can_y, v1 - 1, u1 - 2, can_y, PRISM["field"])
    L.fill(v0 + 3, u0 + 2, can_y + 1, v1 - 1, u1 - 2, can_y + 1, PRISM["kslab"], type="bottom",
           waterlogged="false")
    for v, u, dv_, du_, t in _perimeter(v0 + 3, u0 + 2, v1 - 1, u1 - 2):
        L.put(v + dv_, u + du_, can_y, PRISM["dstair"], facing=_dir(-dv_, -du_), half="top",
              shape="straight", waterlogged="false")
        if t % 4 == 0:
            L.put(v + dv_, u + du_, can_y - 1, PRISM["louvre"], facing=_dir(dv_, du_),
                  half="top", open="true", powered="false", waterlogged="false")
    # ---- the two flights, cut into the deck's own front
    for su in (door - 1, door + 1):
        for k in range(deck_y + 1):
            v = v0 - 1 + k
            if v > v1:
                break
            L.fill(v, su, 0, v, su, max(0, k - 1), PRISM["field"])
            L.put(v, su, k, PRISM["dstair"], facing=_EAST, half="bottom", shape="straight",
                  waterlogged="false")
    L.fill(v0 - 1, door, 0, v0 + deck_y - 1, door, deck_y - 1, PRISM["field"])
    for k in range(deck_y + 1):
        L.put(v0 - 1 + k, door, k, PRISM["dstair"], facing=_EAST, half="bottom", shape="straight",
              waterlogged="false")
    # THE NAMEPLATE GOES ON A PIER, NOT ON THE NEAREST CELL TO THE DOOR. The undercroft is piers
    # every five with air between them, so a sign three cells from the flight hangs on nothing -
    # and a wall sign floating in air draws exactly like one on a wall in every render we have.
    su = u0 + max(0, (door - 3 - u0) // 5) * 5
    L.sign(v0 - 1, su, 3, _WEST, ["FORGE DECK", "", "watch the", "ascent"])
    return {"deck_y": deck_y, "undercroft_piers": piers, "balustrade": rails, "canopy_y": can_y,
            "nameplate_pier": su}


def _gallery(L: _Lot, p: dict) -> dict:
    """PF SERVICE GALLERY - back of house, and it is supposed to look like it.

    Thirteen deep by forty-one long against the service lane. A monitor roof - a raised clerestory
    ridge with louvres - shutters facing the lane, a vent stack, and no ornament at all beyond the
    one string course that ties it to the rest of the land. It is the only building here that is
    allowed to be plain, and being plain is a decision rather than an omission.
    """
    dv, du = L.dv, L.du
    door = 20                      # U570 - U550
    # NINE OF THE BAND'S THIRTEEN COURSES AND THIRTY-FIVE OF ITS FORTY-ONE. Wall to wall the shed
    # covered every column of its lot and threw fifty-four trim cells past the boundary, where
    # they are cropped; the margin is what the cornice, the plinth splay and the shutter hoods
    # actually stand in.
    v0, v1, u0, u1 = 2, 10, 3, du - 4
    h = 7
    L.hollow(v0, u0, 0, v1, u1, 0, PRISM["pier"])
    _floor(L, v0 + 1, u0 + 1, v1 - 1, u1 - 1, 0, grid=4)
    _bay_wall(L, v0, u0, v1, u1, 1, h, bay=5, sill=4, win=2, glaze="bars",
              void=lambda v, u, y: v == v0 and abs(u - door) <= 1 and 1 <= y <= 3)
    # roller shutters onto the lane, on the bay rhythm
    shutters = 0
    for u in range(u0 + 2, u1 - 1, 10):
        for y in range(1, 4):
            for uu in range(u, min(u + 3, u1)):
                L.put(v0, uu, y, PRISM["field"] if y > 3 else PRISM["recess"])
        for uu in range(u, min(u + 3, u1)):
            # OPEN, so the panel stands against the wall it covers. Closed it is a horizontal
            # shelf at the top of a cell in mid air, which is a canopy, not a roller shutter.
            L.put(v0 - 1, uu, 3, PRISM["shutter"], facing=_EAST, half="bottom", open="true",
                  powered="false", waterlogged="false")
            L.put(v0 - 1, uu, 2, PRISM["shutter"], facing=_EAST, half="bottom", open="true",
                  powered="false", waterlogged="false")
            shutters += 1
        # a hood over each shutter, and the one cold lamp under it: a loading door you can find
        # in the dark is the whole of what a service lane needs at night
        L.fill(v0 - 1, u, 5, v0 - 1, min(u + 2, u1), 5, PRISM["dslab"], type="bottom",
               waterlogged="false")
        L.put(v0 - 1, u + 1, 5, PRISM["field"])
        L.lamp(v0 - 1, u + 1, 4, hanging=True)
    L.cut(v0, door - 1, 1, v0, door + 1, 3)
    _portal(L, v0, door - 1, door + 1, 1, 3, -1)
    _string_course(L, v0, u0, v1, u1, 4)
    _pilasters(L, v0, u0, v1, u1, 1, h, bay=5)
    _roof(L, v0, u0, v1, u1, h + 1, rib=4, coping=False)
    _cornice(L, v0, u0, v1, u1, h + 1)
    L.ring(v0, u0, v1, u1, h + 2, PRISM["kslab"], type="bottom", waterlogged="false")
    # ---- the monitor: a raised ridge with louvres, which is what a plant room actually has
    mv0, mv1 = v0 + 3, v1 - 3
    L.fill(mv0, u0 + 1, h + 2, mv1, u1 - 1, h + 4, PRISM["field"])
    L.cut(mv0 + 1, u0 + 2, h + 2, mv1 - 1, u1 - 2, h + 3)
    for u in range(u0 + 1, u1):
        for v in (mv0, mv1):
            if u % 3:
                L.put(v, u, h + 3, PRISM["bars"])
    L.fill(mv0, u0 + 1, h + 5, mv1, u1 - 1, h + 5, PRISM["kslab"], type="bottom",
           waterlogged="false")
    _cornice(L, mv0, u0 + 1, mv1, u1 - 1, h + 5)
    # ---- the vent stack, the one vertical this shed is allowed
    sv, su = v0 + 5, u1 - 6
    L.fill(sv, su, h + 2, sv + 2, su + 2, h + 8, PRISM["dark"])
    L.cut(sv + 1, su + 1, h + 3, sv + 1, su + 1, h + 8)
    _cornice(L, sv, su, sv + 2, su + 2, h + 9)
    L.ring(sv, su, sv + 2, su + 2, h + 9, PRISM["pier"])
    for v, u, dv_, du_, t in _perimeter(sv, su, sv + 2, su + 2):
        if t % 2 == 0:
            L.put(v, u, h + 10, PRISM["signal"])
    _skirt(L, v0, u0, v1, u1, 0)
    L.sign(v0 - 1, door - 2, 3, _WEST, ["SERVICE", "GALLERY", "", "staff only"])
    return {"shutters": shutters, "monitor_y": h + 5, "stack_top": h + 10, "shed_h": h}


_KINDS = {"gate": _gate, "array": _array, "vault": _vault, "ascent": _ascent,
          "deck": _deck, "gallery": _gallery}

_CONTRACT = {
    "gate": "a walk-through portal on the spine axis with a seven-wide passage, an overbridge "
            "over it and an arcade carrying the axis into the land",
    "array": "an open exhibit hall: a street loggia, screened bays, a raised clerestory and a "
             "grid of lit prism columns under it",
    "vault": "a closed buttressed block with one recessed portal, wrapped on three sides by an "
             "arcaded ambulatory, under a three-stage resonator and a signal ring",
    "ascent": "a columnar spire: a four-stage tapering core with four planar fin blades and a lit "
              "crown, standing in a ring podium reached by a colonnaded causeway",
    "deck": "a raised observation gallery on an arcaded undercroft, balustraded its whole length, "
            "with a canopy over the rear half and two flights from the promenade",
    "gallery": "a plain service shed with a monitor roof, shutters onto the lane and one vent "
               "stack",
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**PRISMWORKS_BUILDS, **(cfg or {})}
    kind = p.get("kind")
    if kind not in _KINDS:
        raise ValueError(f"unknown prismworks build kind {kind!r}; have {sorted(_KINDS)}")
    if not p.get("size") or len(p["size"]) != 2:
        raise ValueError("a prismworks build needs size: [depth along V, width along U]")
    if not p.get("at") or len(p["at"]) != 2:
        raise ValueError("a prismworks build needs at: [V, U] - the lot's near corner")
    dv, du = int(p["size"][0]), int(p["size"][1])
    h = int(p.get("height") or _DEFAULT_H[kind])
    c = Canvas(dv, h, du)
    L = _Lot(c, p)
    detail = _KINDS[kind](L, p)

    v, u = int(p["at"][0]), int(p["at"][1])
    c.world_origin = (ANCHOR[0] + v, ANCHOR[1], ANCHOR[2] + u)
    c.meta = {
        "kind": f"prismworks_{kind}",
        "land": "prismworks",
        "lot": [v, u, v + dv - 1, u + du - 1],
        "size": [dv, du], "height": h,
        "facing": "west",
        "lamp_arms_refused": L.refused_keep,
        "outside_lot_refused": L.refused_out,
        "lights": L.lights, "signs": L.signs,
        **detail,
        "contract": _CONTRACT[kind] + f" - inside V{v}-{v + dv - 1} / U{u}-{u + du - 1} and "
                    f"not one cell outside it",
        "requires_in_game": [
            "colour and the read of the value ladder can only be judged in world",
            "no mechanism is claimed by this geometry: the Ascent's timing, the Array's route "
            "lights and the Vault's completion circuit are separate redstone tickets",
        ],
    }
    return c
