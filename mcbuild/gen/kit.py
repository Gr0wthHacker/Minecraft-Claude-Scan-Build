"""The building kit: symmetric BY CONSTRUCTION, with a detail vocabulary that reads.

Two measurements decided everything in this file.

**THE PARK'S BUILDINGS HAVE NO MIRROR PLANE AT ALL.** Measured as the share of blocks with no
counterpart across the frontage axis: Shooting Range 122%, Carousel 126%, Plinko 112%, Assay
Office 102% - over 100% because every mismatch counts on both sides. The one piece that came out
genuinely symmetric, the Clock Tower at 3.8%, is also one of the few a player can name. A facade
built cell by cell drifts, and no amount of care in the caller stops it: the guarantee has to be
structural.

So a building is drawn ONCE, on one side of its own centre line, and the other side is a mirror
that the kit writes for you. Symmetry is then not something a test catches afterwards; it is
something the caller cannot break.

**AND A MIRROR FLIPS, IT DOES NOT COPY.** This project already paid for that lesson on the frog:
written the obvious way, 60 of 134 stairs came out facing the same way on both flanks - a chamfer
leaning into the wall on one side and out of it on the other. Only the ACROSS axis flips; a stair
leaning fore or aft leans the same way on both sides. `render3d` draws a wrong facing and a right
one identically, so this is asserted rather than eyeballed.

**THE SECOND MEASUREMENT IS THE DETAIL VOCABULARY.** Against 31 outside builds, per thousand cells:

    stairs    0.64 vs 4.51     seven times under
    fences    0.07 vs 2.22     thirty times under
    trapdoors 0.00 vs 1.07     we have never placed one

An open trapdoor is the vertical slab Minecraft never shipped; an upside-down stair is an eave; a
fence is a railing. Those three are what make a surface read as BUILT rather than as a box, and
this kit uses all of them - so a caller gets them by using the kit at all, rather than by
remembering to.
"""
from __future__ import annotations

from .canvas import hash01

# ------------------------------------------------------------------ mirroring

#: Flipping across the X axis swaps east and west and leaves north/south alone; across Z, the
#: reverse. A block whose facing lies ALONG the mirror keeps it - that is the frog's rule, and
#: getting it wrong is invisible in every render this project has.
_FLIP_X = {"east": "west", "west": "east"}
_FLIP_Z = {"north": "south", "south": "north"}

#: A stair's `shape` names an inner/outer corner by LEFT or RIGHT, so a mirror swaps them too.
_FLIP_SHAPE = {"inner_left": "inner_right", "inner_right": "inner_left",
               "outer_left": "outer_right", "outer_right": "outer_left"}

#: Properties that name a direction and therefore have to be flipped. `axis` is not one of them:
#: a log lying along X still lies along X in the mirror.
_DIRECTIONAL = ("facing", "shape", "hinge")


def flip(props: dict, axis: str) -> dict:
    """One block's state, mirrored across `axis` ("x" or "z")."""
    table = _FLIP_X if axis == "x" else _FLIP_Z
    out = dict(props)
    if "facing" in out:
        out["facing"] = table.get(out["facing"], out["facing"])
    if "shape" in out:
        out["shape"] = _FLIP_SHAPE.get(out["shape"], out["shape"])
    if out.get("hinge") in ("left", "right"):
        out["hinge"] = "right" if out["hinge"] == "left" else "left"
    # A multiface block (vine, glow lichen) names the faces it clings to, and two of them swap.
    if axis == "x" and ("east" in out or "west" in out):
        out["east"], out["west"] = out.get("west", "false"), out.get("east", "false")
    if axis == "z" and ("north" in out or "south" in out):
        out["north"], out["south"] = out.get("south", "false"), out.get("north", "false")
    return out


class Sym:
    """A drawing surface that writes every block twice - once as given, once mirrored.

    The caller works in LOCAL coordinates: `u` runs across the building from its centre line, `v`
    runs into it from the front, `h` is the course above its floor. A cell at u=0 is ON the mirror
    and is written once; everything else is written on both sides with its state flipped.

    Because the caller never names a world coordinate, a building cannot be lopsided by accident -
    which is the entire point, and is why every attraction in the park was.
    """

    def __init__(self, world, origin, facing: str = "east"):
        self.w = world
        self.ox, self.oy, self.oz = (int(v) for v in origin)
        self.facing = facing
        # `across` is the axis the mirror flips; `into` runs from the front into the building.
        self.axis = "z" if facing in ("east", "west") else "x"
        self.placed = 0

    # -------------------------------------------------------------- geometry

    def world(self, u: int, v: int, h: int) -> tuple:
        """The world cell for a local (across, into, up) coordinate."""
        if self.facing == "east":
            return (self.ox + v, self.oy + h, self.oz + u)
        if self.facing == "west":
            return (self.ox - v, self.oy + h, self.oz - u)
        if self.facing == "south":
            return (self.ox - u, self.oy + h, self.oz + v)
        return (self.ox + u, self.oy + h, self.oz - v)

    def put(self, u: int, v: int, h: int, name: str, **props) -> None:
        """Place a block and its mirror. `u` may be negative; the mirror is written for you."""
        x, y, z = self.world(u, v, h)
        self.w.put(x, y, z, name, **props)
        self.placed += 1
        if u == 0:
            return
        mx, my, mz = self.world(-u, v, h)
        self.w.put(mx, my, mz, name, **flip(props, self.axis))
        self.placed += 1

    def one(self, u: int, v: int, h: int, name: str, **props) -> None:
        """Place a block WITHOUT its mirror - for something genuinely one-sided.

        Deliberately awkward to reach and deliberately named. A door on the left of a facade and
        nothing on the right is a decision somebody should have to make on purpose; every
        building in this park made it by accident.
        """
        x, y, z = self.world(u, v, h)
        self.w.put(x, y, z, name, **props)
        self.placed += 1

    def sign(self, u: int, v: int, h: int, lines, back=()) -> None:
        x, y, z = self.world(u, v, h)
        self.w.sign(x, y, z, front=list(lines), back=list(back))

    def has(self, u: int, v: int, h: int) -> bool:
        return self.w.has(*self.world(u, v, h))


# ------------------------------------------------------------------ the pieces

def plinth(s: Sym, half: int, depth: int, pal, courses: int = 1) -> None:
    """A base course a cell proud of the wall, so the building meets the ground on a line.

    A wall that runs straight into the paving has no bottom edge, which is most of why a box
    reads as a box. One course of trim, one cell out, is the cheapest thing that fixes it.
    """
    for course in range(courses):
        for u in range(-half - 1, half + 2):
            for v in range(-1, depth + 1):
                if abs(u) <= half and 0 <= v < depth and course:
                    continue
                s.put(u, v, course, pal["trim"])


def walls(s: Sym, half: int, depth: int, height: int, pal, *, door: int = 3,
          windows=(), seed: float = 0.0) -> None:
    """The shell: four walls, a doorway in the middle of the front, windows where asked.

    **THE DOORWAY IS LEFT EMPTY BY THE WALL LOOP, NEVER PUNCHED AFTERWARDS.** Building the ring
    and then cutting a hole repaints cells that already exist - the void tower's crenellations
    shipped as a plain drum for exactly this reason and nothing about the code looked wrong.
    """
    door_half = max(0, door // 2)
    window_rows = set(windows)
    for h in range(height):
        for u in range(-half, half + 1):
            for v in range(depth):
                edge = abs(u) == half or v in (0, depth - 1)
                if not edge:
                    continue
                if v == 0 and abs(u) <= door_half and h < 3:
                    continue                                   # the doorway
                if h in window_rows and abs(u) != half and 0 < v < depth - 1:
                    continue
                block = pal["wall"]
                if hash01(u, v, h, seed) < 0.12:
                    block = pal.get("wall_alt", pal["wall"])
                s.put(u, v, h, block)


def openings(s: Sym, half: int, depth: int, pal, rows=(), width: int = 1) -> int:
    """Glazed openings in the front wall, with a sill under each and a lintel over it.

    A hole in a wall is a hole; a hole with a sill and a lintel is a window. The pane's own
    connection state is set ALONG the wall - with every side false it renders as a lone post
    rather than as glazing, which this project has shipped once already.
    """
    made = 0
    along = ("north", "south") if s.axis == "z" else ("east", "west")
    for h in rows:
        for u in range(1, half, 3):
            for k in range(width):
                s.put(u + k, 0, h, "glass_pane",
                      **{along[0]: "true", along[1]: "true",
                         "east": "false" if along[0] != "east" else "true",
                         "waterlogged": "false"})
                made += 2
            s.put(u, 0, h - 1, pal["slab"], type="top", waterlogged="false")     # sill
            s.put(u, 0, h + width, pal["trim"])                                  # lintel
    return made


def eaves(s: Sym, half: int, depth: int, height: int, pal) -> None:
    """An upside-down stair course under the roof line, all the way round.

    **AN UPSIDE-DOWN STAIR IS AN EAVE**, and it is one of the three details this project uses at a
    fraction of the rate outside builders do. It is the difference between a roof sitting on a
    box and a roof that overhangs it.
    """
    lean = {"east": "west", "west": "east", "north": "south", "south": "north"}
    for u in range(-half - 1, half + 2):
        for v in (-1, depth):
            face = "east" if v == depth else "west"
            if s.facing in ("north", "south"):
                face = "south" if v == depth else "north"
            s.put(u, v, height, pal["stair"], facing=lean[face], half="top",
                  shape="straight", waterlogged="false")
    for v in range(0, depth):
        s.put(half + 1, v, height, pal["stair"],
              facing="south" if s.axis == "z" else "east",
              half="top", shape="straight", waterlogged="false")


def gable(s: Sym, half: int, depth: int, height: int, pal, pitch: int = 1) -> int:
    """A pitched roof that steps in from both sides to a ridge - symmetric by construction.

    Stepped in stairs rather than in full blocks, because a stepped roof of cubes is a ziggurat
    and a stepped roof of stairs is a roof. The ridge is one course of slab, which is what stops
    the two slopes meeting in a jagged seam.
    """
    lean = "west" if s.facing == "east" else "east"
    if s.axis == "x":
        lean = "north" if s.facing == "south" else "south"
    #
    # **A ROOF THAT STEPS IN AND UP AT THE SAME TIME IS DIAGONAL-ONLY.** Each course sits one cell
    # nearer the ridge AND one course higher than the last, so the two touch at a corner and
    # nowhere else: every gable this kit made came apart into one loose ring per course, and the
    # mausoleum that first used it shipped in thirteen pieces. Each step lays a RISER in the
    # previous course's own column, which is also what a real rafter does where it meets the
    # course below. Same rule as the water tower's splayed leg.
    rows = 0
    for step in range(half + 1):
        h = height + step * pitch
        u = half - step
        if u < 0:
            break
        for v in range(-1, depth + 1):
            if step:
                for lift in range(pitch):
                    s.put(u + 1, v, h - pitch + 1 + lift, pal["roof_stair"],
                          facing=_toward_centre(s, u + 1), half="bottom",
                          shape="straight", waterlogged="false")
            s.put(u, v, h, pal["roof_stair"], facing=_toward_centre(s, u), half="bottom",
                  shape="straight", waterlogged="false")
            if u == 0:
                s.put(0, v, h + 1, pal["roof_slab"], type="bottom", waterlogged="false")
        rows += 1
    return rows


def _toward_centre(s: Sym, u: int) -> str:
    """Which way a roof stair leans so both slopes fall AWAY from the ridge."""
    if s.axis == "z":
        return "north" if u > 0 else "south"
    return "west" if u > 0 else "east"


def canopy(s: Sym, half: int, pal, reach: int = 2, height: int = 3) -> int:
    """An awning over the frontage on fence posts - what makes a shopfront a shopfront.

    Fences are the detail this project is thirty times under the outside rate on, and this is
    where they belong: holding up the thing that tells you the counter is open.
    """
    made = 0
    for u in range(-half, half + 1):
        for v in range(-reach, 0):
            s.put(u, v, height, pal["canopy"][(abs(u) + abs(v)) % len(pal["canopy"])])
            made += 1
    for u in (half, half - 3):
        if u < 0:
            continue
        for h in range(height):
            s.put(u, -reach, h, pal["fence"], waterlogged="false")
            made += 1
    return made


def fascia(s: Sym, half: int, pal, height: int, name: str) -> None:
    """The board a building's name goes on, over the door and under the eave.

    **AN OPEN SHOPFRONT HAS NO WALL TO HANG A SIGN ON**, which is why this is a board rather than
    a wall sign: the fascia is placed first and the sign hangs on the fascia.
    """
    for u in range(-half, half + 1):
        s.put(u, -1, height, pal["beam"], axis="x" if s.axis == "x" else "z")
    s.one(0, -2, height, f"{pal['wood']}_wall_sign", facing=s.facing, waterlogged="false")
    s.sign(0, -2, height, [name[:15]])


def rail(s: Sym, half: int, depth: int, pal, height: int = 0) -> int:
    """A fence railing round a deck or a drop - the second under-used detail, in its own place."""
    made = 0
    for u in range(-half, half + 1):
        for v in (-1, depth):
            s.put(u, v, height, pal["fence"], waterlogged="false")
            made += 1
    return made
