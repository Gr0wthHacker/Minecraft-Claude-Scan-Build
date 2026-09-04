"""Games INSIDE the park's buildings - the half that was never built.

Sixteen buildings, 77,845 blocks, and TEN interactive blocks in the whole park: seven rails and
three target blocks wired to nothing. Five of the eight modules declared `ride` are sheds. Jack,
looking at it: *"really nice to look at - but serve no purpose ... this is still supposed to be a
theme park so there has to be games, or something engaging to do here."*

Every kind here is a machine a visitor OPERATES, standing in a room that already exists. It states
a CONTRACT and `tests/test_park_games.py` asserts that contract by SIMULATION through
`mcbuild.circuit`. A kind whose contract is not asserted does not belong in this file - that rule
deleted two finished casino games and it is the only reason anything here can be believed, because
a redstone build is the one thing in this project whose wrongness is invisible in every render,
every audit and every bill of materials.

    aim        THE TARGET WALL      shoot the disc; the counter lights by how central you were
                                    (`discs: 3` makes it an ARRAY of independent lanes)
    striker    THE STRIKER          hit it; the column climbs; a maximum rings the bell
    mark       THE MARK             load the scale to EXACTLY the number on the sign
    pair       THE DOUBLE           two buttons, two people, one prize - press together
    pattern    THE VAULT            n levers; exactly one of 2^n settings opens it (`door: true`)
    starter    THE SIGNAL           a countdown that runs down the board and rings you away
    counter    THE PRIZE COUNTER    prize windows that show what is actually in stock

**A CABINET, NOT A PIT.** Everything in `gen/arcade.py` hides its machine in a pit `pit` courses
under its own pad, because a fairground booth brings its own ground and can dig as deep as it
likes. A game going INSIDE a finished building cannot: the floor it stands on is somebody else's
design, digging under it is a dig list rather than a placement, and every cell taken from it is an
overlap. So every machine here lives in a CONSOLE - a plinth, a machine course inside a wall ring,
a lid over it, and controls on top - standing on the room's own floor and writing only into air.
That is what makes `overlap 0` a property of the construction rather than something to hope for.

**AND THE MACHINE COURSE IS h=1, NOT h=0.** `arcade._lay` gives every wire cell a floor when there
is nothing under it, and under h=0 is the BUILDING's floor - a cell the world already owns. One
course up, the plinth is always there, the helper never reaches past it, and the world is never
written to at all.

THE RULES THIS RUNS UNDER, each of which has already cost this project a rebuild:

* **AN ANALOG VALUE CANNOT TRAVEL.** A level of 4 reaches four blocks of dust and a repeater
  carries it only by destroying it. So every analog reading here is displayed and decided where it
  is made - the comparator's own output cell is the foot of the bar - and only booleans move.
* **THE DECAY IS THE MEASUREMENT, AND IT IS ALSO THE THRESHOLD.** A run of `n` dust cells lights
  its last lamp exactly when the reading was at least `n`. `aim` and `striker` therefore contain no
  gate at all: the bell hangs beside the last cell, so it rings on a maximum and on nothing else.
* **NOTHING HERE DISPENSES A PRIZE.** The casino pins a hazard where a stuck item reads a winning
  level against an edge that never falls and the house pays until the bank is empty. A game whose
  output is a lamp and a bell cannot lose money by accident, and the park already has a counter to
  redeem at. `counter` is that counter, and what its redstone does is tell the truth about stock.
* **A GAME NOBODY CAN WORK OUT HOW TO PLAY IS AN EMPTY STRUCTURE**, which is the complaint this
  file answers. Every kind signs itself with what to do and what happens, fifteen characters a
  line, and `_sign` REFUSES a cell with no block behind it - so the sign is checked, never hoped
  for.

**WHAT IS NOT BUILT, and why, rather than silently dropped.**

* **NO DROPPER RANDOMISER, SO NO GAME OF CHANCE.** `circuits.randomiser` puts a `dropper[facing=
  down]` over a `hopper[facing=down]`: the dropper inserts its item into the hopper, and the hopper
  has nowhere to push it back to. The mix therefore migrates out of the dropper one trigger at a
  time and accumulates in the hopper, so the second roll reads two items rather than one and the
  fourth reads nothing at all. minecraft.wiki's own randomizer closes that loop - the container the
  comparator reads feeds back into the dropper - and closing it here would be editing a module this
  ticket does not own. It is written up in the report instead. Until it is closed, these games are
  games of SKILL and no sign in this park states odds it cannot keep.
* **NO LOCK THAT COUNTS THE ORDER**, which is what a "resonance vault" wants to be. It needs one
  memory cell per key, and `circuits.latch` DOES NOT HOLD: driven with the repo's own harness, its
  output drops the tick the set pulse ends, against a contract that says the opposite. Its own test
  asserts only that the latch "has state at all" - a bound looser than the bug, exactly the failure
  this project already records about `circuits.pulse`. A cross-coupled pair of torches does hold
  and was verified while writing this; wiring three of them plus two AND gates through one console
  then needs five signals routed past each other, and every arrangement tried put two of them in
  one cell, which is one signal, which is a vault that opens on the wrong key. The Vault ships as a
  COMBINATION instead - a lock with no state, which cannot deadlock either - and the working latch
  topology is in the report.
* **THE PRISM ASCENT'S SPIRE CARRIES NO SIGNAL.** Its shaft is 79 courses of hollow core divided by
  solid diaphragms at Y232, Y250, Y264 and Y274, and its outer face is broken by four fin blades.
  A dust staircase needs one block of horizontal run per course and there is nowhere to spend 79 of
  them; a torch ladder alternates on and off by construction, so half the tower would be lit at
  rest. The calibration court at its foot gets a real countdown; what the spire itself would need
  is openings in its own shell, which is a change to `prismworks_builds.py`.

GEOMETRY is `gen/park.py`'s `_Frame`, unchanged, so a console sits in a room exactly as a stall
sits on a street:

    at       the console's FRONT-LEFT cell on the course a player STANDS on (y = floor + 1)
    facing   the direction the front looks out - a visitor stands in the +facing direction
    i        along the frontage      d   from the front INTO the console      h   courses up
"""
from __future__ import annotations

from . import circuits
from .arcade import _dirs, _ij, _lay, _line, _run, and_gate, ladder, read_out
from .canvas import Canvas
from .park import LANDS, SIGN_WIDTH, _STEP, _Frame, _sign
from .vertical import Ctx, World

# ---------------------------------------------------------------------------- palettes
#
# **`LANDS` VERBATIM WHEREVER IT CAN BE.** The one departure is the frontier, whose `ground`
# there is `cobblestone` - barred outright by this ticket, and not what the land's own buildings
# stand on either: `frontier_builds.PAL` puts `stone_bricks` under everything with a blackstone
# plinth below that. The keys used are exactly the ones `arcade._structural`, `_line`, `_run` and
# `park._sign` read, so a console can be handed to any of those helpers whatever land it is in.

# **PRISMWORKS IS `LANDS`' OWN NOW, AND THIS FILE'S COPY IS DELETED.** It was written here only
# because `park.LANDS` had no prismworks entry at all - which, as `park.py` now records, meant a
# land that does not exist in the table "silently becomes another land", and is very likely what
# Jack meant by *"I thought this area was now prism - which had a different purpose/feel"*. Keeping
# a second table beside the real one is the drift `proportions.measure` and `rubric.score` share an
# entry point to avoid: two answers to one question, and no way to tell which a console used.

_FRONTIER = {
    **LANDS["frontier"],
    # COBBLESTONE IS BARRED BY THIS TICKET, and the land's own buildings do not use it either:
    # `frontier_builds.PAL` puts `stone_bricks` under everything and a blackstone plinth below that.
    "ground": "stone_bricks",
    "trim": "polished_blackstone_bricks",
    "path": "smooth_stone",
}

PALETTES = {"midway": LANDS["midway"], "frontier": _FRONTIER,
            "prismworks": LANDS["prismworks"]}

GAME = {
    "under": None,              # capture(s) the console is fitted into - see `Ctx`
    "at": None,                 # world (x, y, z): FRONT-LEFT cell of the STANDING course
    "facing": "east",
    "land": "midway",
    "kind": "aim",
    "title": None,
    "building": "",             # which module this fits out, for the sidecar
    "deck": 1,                  # how many courses of plinth under the machine course
    "height": None,             # board height; a low room needs a low console
    "score": 6,                 # aim/striker: how many lamps, and the level that rings the bell
    "discs": 1,                 # aim: how many independent target lanes
    "mark": 4,                  # mark: the exact reading that wins
    "band": 1,                  # mark: how wide the winning window is
    "lanes": 4,                 # counter: how many prize windows
    "stages": 5,                # starter: how many countdown lamps
    "pattern": (True, False, True),   # pattern: the one lever setting that opens it
    "door": False,              # pattern: an iron door in the console's face, not just a lamp
    "sign": True,
}
DEFAULTS = GAME

# What must never show on the outside of a cabinet. A lamp, a barrel, a button, a bell and a door
# are things the game exists to SHOW; a wire is a thing a player can break by accident.
MACHINE = ("redstone_wire", "repeater", "comparator", "redstone_torch", "redstone_wall_torch")


# ---------------------------------------------------------------------------- the console
#
# One shape, seven games. A console is furniture: a player cannot walk through it, which is exactly
# why the machine inside it is safe, and it needs no ceiling because the building already has one.


def _plinth(w: World, f, pal: dict, width: int, depth: int, deck: int) -> None:
    """The solid base the machine course stands on, `deck` courses of it.

    **THIS IS WHAT KEEPS THE HELPERS OFF THE BUILDING'S FLOOR.** `arcade._lay` and `_line` both put
    a floor under any wire cell that has nothing beneath it, and beneath h=0 is the room's own
    paving - a cell the capture already owns, so writing it is an overlap on a design whose whole
    claim is that it has none. Built first and built solid, there is never a cell for them to fill.
    """
    for i in range(width):
        for d in range(depth):
            for h in range(deck):
                w.put(*f.at(i, d, h), pal["ground"])


def _ring(w: World, f, pal: dict, width: int, depth: int, h: int,
          window: bool = True, keep=()) -> list:
    """The machine course's own wall, and the reason it is a RING rather than a fill.

    Filling every unused cell of the machine course would put a solid block against every component
    in it - and a repeater or comparator aimed at a solid block STRONGLY powers it, which then
    passes 15 to any dust touching its far side. That is a short across the machine, invisible in
    every render. A hollow box has no far side to short to.

    **IT SKIPS WHAT IS ALREADY THERE, AND THAT IS NOT POLITENESS.** Written to `put`
    unconditionally it walled straight over the target wall's own lamp row, which sits on the
    console's back edge because that is the face a player is looking at: the game shipped with a
    disc, a bar of dust, a bell and NOT ONE LAMP, at 172 blocks, zero placement problems, one
    connected piece and a clean circuit inspection. Nothing but reading the bill of materials
    would have caught it.

    Returns the perimeter cells holding a live component - a wire showing on the outside of the
    cabinet is a leak, and the tests assert there are none.
    """
    leaks = []
    for i in range(width):
        for d in range(depth):
            if not (i in (0, width - 1) or d in (0, depth - 1)):
                continue
            pos = f.at(i, d, h)
            if w.has(*pos):
                if w.name(*pos) in MACHINE:
                    leaks.append(list(pos))
                continue
            # **THE FRONT ROW IS A WINDOW, AND THAT IS THE WHOLE POINT OF THE COURSE.** Walled, the
            # machine course is sealed: its score lamps - the thing that tells a player what
            # happened - are invisible from the only side anybody stands on, and the aim and
            # striker discs cannot be shot at all. Jack: "the games arent playable as they are
            # facing, theyre ugly, and just not working." A player's eye stands at 1.62 above the
            # floor, so this course IS their eye line; open, they look straight into the works.
            #
            # It stays SOLID at the two end posts, which carry the cabinet, and at every column
            # `keep` names - those are where a control is bolted to the outside and must have
            # something to bolt to.
            if window and d == 0 and 0 < i < width - 1 and i not in set(keep):
                # **GLAZED, NOT OPEN.** Left as air the window is a hole a hand reaches through:
                # measured, nine of eleven consoles then had a wire, a repeater or a comparator
                # with a clear line to the outside, which is the leak `_ring` is a wall to prevent.
                # A pane stops the hand and not the eye, which is exactly what a shopfront is - and
                # `_daylight` cuts it back to air in the few columns an ARROW has to pass through,
                # because glass stops one of those too.
                w.put(pos[0], pos[1], pos[2], "glass_pane")
                continue
            w.put(pos[0], pos[1], pos[2], pal["wall"])
    return leaks


def _lid(w: World, f, pal: dict, width: int, depth: int, h: int, open_at=()) -> None:
    """The counter top, laid LAST so it never covers a lamp, a control or a door already placed.

    `open_at` is what a caller has to say out loud: a scale you cannot drop anything on is a scale
    with a lid over it, and `w.has` cannot see that, because the cell it would fill is genuinely
    empty - the plate is a course BELOW.
    """
    skip = {tuple(c) for c in open_at}
    for i in range(width):
        for d in range(depth):
            if (i, d) in skip or w.has(*f.at(i, d, h)):
                continue
            w.put(*f.at(i, d, h), pal["trim"])


def _daylight(w: World, f, cells, depth: int, pane: str | None = "glass_pane",
              fabric=()) -> int:
    """Carve a clear line from every readout and every control to the FRONT of the cabinet.

    Opening the machine course's front row is not enough on its own, and the reason is that the
    kinds do not all put their parts on one plane: `pair`, `counter`, `mark` and `striker` carry
    lamps in or above the LID course, where the lid walls them in, and `aim` and `striker` set
    their disc into the BOARD, where the ring's own back row stands in front of it. Measured, six
    of seven kinds still had an invisible readout and three had an unreachable input after the
    window went in.

    So this walks out from each cell one at a time and removes whatever this design put in the way
    - never a component, so it cannot carve through the works.

    **A READOUT IS GLAZED AND AN INPUT IS OPEN, and that distinction is the whole of it.** A score
    lamp must be SEEN and must not be reachable, so its channel is filled back with a pane: a hand
    cannot get through and a wire behind it cannot be broken. A disc has to be SHOT and a button
    pressed, so those channels are air - glass stops an arrow.
    """
    n = 0
    for pos in cells:
        i, d, h = _ij(f, pos)
        for dd in range(d - 1, -2, -1):
            q = f.at(i, dd, h)
            if not w.has(*q):
                continue
            # **IT MAY ONLY REMOVE FABRIC.** A blocklist of "the works" was not enough: written
            # that way it ate the counter's own call button and the striker's rules sign, both of
            # which are neither wire nor lamp, and the circuit tests caught it. So this carves the
            # cabinet's own wall, trim, floor and glazing and NOTHING else - a whitelist, because
            # the next part somebody adds will not be on anybody's blocklist either.
            if w.name(*q) not in set(fabric):
                break
            del w.cells[q]
            w.signs.pop(q, None)
            if pane and 0 <= dd < depth:
                w.put(q[0], q[1], q[2], pane)
            n += 1
    return n


def _reattach(w: World, f, pal: dict, cells) -> int:
    """Put back the block every wall control is bolted to, after the carving has been through.

    **A BUTTON CANNOT HANG ON A PANE.** The counter's call button ended up attached to glass,
    because the bell it rings is an OUTPUT and the sightline carved for that bell ran straight
    through the button's own backing - the two passes are correct on their own and wrong together.
    A control is placed before the sightlines and read after them, so this is the last word.
    """
    n = 0
    for pos in cells:
        if w.name(*pos) not in ("stone_button", "lever"):
            continue
        i, d, h = _ij(f, pos)
        back = f.at(i, d + 1, h)
        if w.has(*back) and w.name(*back) not in ("glass_pane", "iron_bars"):
            continue
        w.put(back[0], back[1], back[2], pal["wall"])
        n += 1
    return n


def _seal(w: World, f, depth: int) -> int:
    """Glaze anything the carving left within a hand's reach, and GUARANTEE it rather than hope.

    `_daylight` cuts an INPUT's channel to air, because glass stops an arrow and a disc has to be
    shot - and a channel cut past a disc can leave the wire behind it open to the outside. Rather
    than reason about which kind does that (three of eleven did, and each for its own reason), this
    walks every machine cell afterwards and puts a pane in the first free cell of any line that is
    air all the way out. **A PROPERTY WORTH HAVING IS WORTH GUARANTEEING**: the ring is a wall so a
    player cannot break the works, and a window that undoes that quietly is worse than no window.
    """
    n = 0
    for pos in [q for q, (name, _pr) in w.cells.items() if name in MACHINE]:
        i, d, h = _ij(f, pos)
        # **A WIRE IS NOT A BARRIER, AND READING IT AS ONE IS WHY THIS DID NOTHING AT FIRST.** A
        # long dust run points at the front, so every cell in front of the cell behind it is more
        # dust - and a first version that bailed on any occupied cell therefore bailed on every
        # wire in the design and placed not one pane, while the front-most cell of each run was
        # still open to the world. Only something a hand cannot pass counts as cover.
        cover, free = False, None
        for dd in range(d - 1, -2, -1):
            q = f.at(i, dd, h)
            if w.has(*q):
                if w.name(*q) in MACHINE:
                    continue
                cover = True
                break
            if dd >= 0:
                free = q                               # the cell nearest the front, so one pane
        if cover or free is None:
            continue
        w.put(free[0], free[1], free[2], "glass_pane")
        n += 1
    return n


def _board(w: World, f, pal: dict, width: int, depth: int, height: int) -> None:
    """The board behind the console: what the game is played against, and what its signs hang on.

    A sign is refused outright when there is no block behind it, so a console with an open back
    ships its name and its rules SILENTLY missing on a build that audits perfectly clean. Five
    arcade kinds did exactly that once.
    """
    for i in range(width):
        for h in range(height):
            w.put(*f.at(i, depth, h), pal["wall"])
    for i in range(width):
        w.put(*f.at(i, depth, height), pal["trim"])


def _lamp_row(w: World, f, run, side_d: int, h: int) -> list:
    """A lamp in FRONT of every cell of a dust run, on the same course.

    **THE LAMP GOES BESIDE THE DUST, NEVER ON TOP OF IT.** Above it, it is a full block resting on
    redstone - a placement the game refuses and a display that pops the first time the chunk loads.
    Beside it, it is simply adjacent, and it is what the player is looking at.
    """
    out = []
    for (i, _d) in run:
        pos = f.at(i, side_d, h)
        w.put(pos[0], pos[1], pos[2], "redstone_lamp", lit="false")
        out.append(pos)
    return out


def _bell(w: World, f, pal: dict, i: int, d: int, h: int, facing: str) -> tuple:
    """A bell on its own block, beside the cell that rings it.

    A `bell` with `attachment=floor` needs a real floor: hung in the cell directly over the wire
    that rings it, three arcade games shipped a bell the game will not place at all.
    """
    if not w.has(*f.at(i, d, h - 1)):
        w.put(*f.at(i, d, h - 1), pal["wall"])
    pos = f.at(i, d, h)
    w.put(pos[0], pos[1], pos[2], "bell", attachment="floor", facing=facing, powered="false")
    return pos


def _press(w: World, f, pal: dict, i: int, d: int, h: int, facing: str) -> tuple:
    """A button on the counter top, on a pad of the land's accent so it reads as the thing to press.

    A FLOOR BUTTON STRONGLY POWERS THE BLOCK BENEATH IT, and dust in the cell under that block is
    adjacent to it, so a press on the lid arrives in the machine course with no routing at all.
    That one fact is what lets every control here sit where a hand can reach it while the machine
    stays sealed a course below.
    """
    pad = f.at(i, d, h - 1)
    w.put(pad[0], pad[1], pad[2], pal["accent"])
    pos = f.at(i, d, h)
    w.put(pos[0], pos[1], pos[2], "stone_button", face="floor", facing=facing, powered="false")
    return pos


def _face_control(w: World, f, pal: dict, i: int, h: int, facing: str,
                  kind: str = "stone_button") -> tuple:
    """A control on the FRONT of the cabinet, at the machine course - which is eye level.

    **THE CONTROLS USED TO SIT ON THE LID**, two courses over the machine, and `_press`'s docstring
    calls that "where a hand can reach it". Measured against a standing player it is not: the lid's
    top face is 1.4 blocks ABOVE their eye, so they press a button they cannot see on a counter
    they cannot see over. That is half of "not playable"; the sealed machine course was the other
    half.

    This is the same mechanic turned through ninety degrees. `_press` relies on a floor button
    strongly powering the block BENEATH it, with dust under that block; a wall button strongly
    powers the block BEHIND it, and dust in the cell behind THAT reads it with no routing at all.
    So the control is on the outside of the cabinet where a hand and an eye both find it, the
    machine stays sealed behind its own front, and the wire never leaves the box.
    """
    back = f.at(i, 0, h)                       # the front-row cell it is bolted to
    if not w.has(*back):
        w.put(back[0], back[1], back[2], pal["wall"])
    pad = f.at(i, -1, h - 1)                   # a step of the land's accent under it, so it reads
    if not w.has(*pad):
        w.put(pad[0], pad[1], pad[2], pal["accent"])
    pos = f.at(i, -1, h)
    w.put(pos[0], pos[1], pos[2], kind, face="wall", facing=facing, powered="false")
    drive = f.at(i, 1, h)                      # the cell the press arrives in
    if not w.has(*drive):
        w.put(drive[0], drive[1], drive[2], "redstone_wire")
    return pos


def _lever(w: World, f, pal: dict, i: int, d: int, h: int, facing: str) -> tuple:
    """A lever on the counter top. Same route as a button, and it HOLDS - which is what a lock
    needs and what nothing else in this file has."""
    pad = f.at(i, d, h - 1)
    w.put(pad[0], pad[1], pad[2], pal["accent"])
    pos = f.at(i, d, h)
    w.put(pos[0], pos[1], pos[2], "lever", face="floor", facing=facing, powered="false")
    return pos


def _and(w: World, f, pal: dict, D: dict, gi: int, gd: int, h: int, n: int) -> dict:
    """`arcade.and_gate`, laid so its inputs arrive down PARALLEL LANES two cells apart.

    **THE ORIENTATION IS THE WHOLE DIFFICULTY, AND GETTING IT WRONG COST FOUR LAYOUTS.** The gate's
    feeds all sit one step BEHIND it along its own `facing`, so with `facing` pointing along the
    frontage every input has to be routed in from the same side, past the gate's own body - and two
    L-routes into a strip that narrow cannot be laid without sharing a cell, which is one signal,
    which is a gate that fires on one input. Turned so that `facing` runs INTO the console and
    `side` runs along the frontage, the feeds come out as `n` lanes at i = gi, gi+2, gi+4 ... on one
    d, each fed by a straight run down its own lane, with the odd lanes between them left empty
    exactly as `and_gate` requires. There is no routing left to get wrong.
    """
    gate = and_gate(f.at(gi, gd, h), D["in"], D["i+"], inputs=n)
    _lay(w, pal, (gate,), floor=pal["wall"])
    lanes = [_ij(f, feed)[0] for feed in gate["feeds"]]
    return {**gate, "lanes": lanes, "feed_d": _ij(f, gate["feeds"][0])[1]}


def _guard(w: World, f, pal: dict, D: dict, i: int, d: int, h: int) -> tuple:
    """A delay-2 repeater on a torch gate's output, and it is not decoration.

    **A TORCH GATE IS TRUE FOR TWO TICKS THE MOMENT IT IS BUILT.** Every torch in it starts LIT, so
    before the inverters settle the output is high - measured at exactly two ticks - and it happens
    again on every chunk load. A delay-2 repeater needs three consecutive ticks to switch, so it
    swallows the startup glitch whole and passes a real win untouched. Without it every gate game
    in this file rings its own bell as the chunk loads, with nobody in the room.
    """
    pos = f.at(i, d, h)
    w.put(pos[0], pos[1], pos[2], "repeater", facing=D["in"], delay="2",
          locked="false", powered="false")
    if not w.has(*f.at(i, d, h - 1)):
        w.put(*f.at(i, d, h - 1), pal["wall"])
    return pos


def _signs(w: World, f, pal: dict, p: dict, width: int, depth: int, height: int,
           title: str, rules) -> bool:
    """The name and the rules, on the board, checked rather than assumed."""
    if not p.get("sign", True):
        return True
    ok = _sign(w, f, pal, max(0, width // 2 - 2), depth - 1, height,
               f.facing, [title[:SIGN_WIDTH]])
    ok &= _sign(w, f, pal, min(width - 1, width // 2 + 2), depth - 1, height,
                f.facing, [str(s)[:SIGN_WIDTH] for s in rules])
    return ok


# ---------------------------------------------------------------------------- the games


def _aim(w: World, p: dict, ctx) -> dict:
    """THE TARGET WALL. Shoot the disc; the counter lights by how central the hit was.

    **A `target` BLOCK IS THE ONLY GENUINELY ANALOG INPUT A PLAYER HAS.** It emits 1 to 15 by how
    near the centre a projectile landed, so aim arrives as a NUMBER. Everything the park had before
    this was a button.

    That number never leaves the cell it is made in: the comparator beside the disc opens straight
    onto the bar, and the bar IS the decay. Dust loses one per block, so a hit of L lights L lamps,
    and the LAST lamp lights only when L reached the end of the run - which is the threshold, for
    free, with no gate to build and nothing to tune. The bell hangs beside that last cell.

    `discs` makes it an ARRAY: several discs on one board, each with its own bar and its own bell,
    and each answering only for itself.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    deck = max(1, int(p["deck"]))
    my = deck                                     # the machine course
    score = max(3, min(12, int(p["score"])))
    # **NOT `lanes`.** That key already means "how many prize windows" to `counter`, and the shared
    # DEFAULTS table gives it a value - so a single-disc target wall silently built itself four
    # discs wide the moment the two kinds shared a name.
    discs = max(1, min(4, int(p.get("discs", 1))))
    stride = score + 4
    width = discs * stride + 2
    depth = 3
    height = int(p.get("height") or my + 4)

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    targets, lamps, bells = [], [], []
    for lane in range(discs):
        base = 1 + lane * stride
        # THE DISC, set into the board at the machine course so the reading, the bar and the bell
        # are all on one plane. Two courses up it would be a better shot and the analog value would
        # have to climb to reach its own display, which is the one thing it cannot do.
        tgt = f.at(base, depth, my)
        w.put(tgt[0], tgt[1], tgt[2], "target", power="0")
        rd = read_out(f.at(base + 1, depth, my), D["i+"])
        _lay(w, pal, (rd,), floor=pal["wall"])

        run = []
        for k in range(score):
            i = base + 2 + k
            cell = f.at(i, depth, my)
            w.put(cell[0], cell[1], cell[2], "redstone_wire")
            run.append((i, depth))
        lamps.append(_lamp_row(w, f, run, depth - 1, my))
        # **A LANE HAS TO END IN A DEAD COLUMN.** Two bars laid `score + 2` apart put one lane's
        # last dust cell next to the next lane's disc, and adjacent dust is ONE network: every disc
        # would have answered for every bar - the plinko board's own recorded failure, and it
        # audits perfectly clean. `stride` leaves the bell's cell and one clear column between.
        bells.append(_bell(w, f, pal, base + 2 + score, depth, my, p["facing"]))
        targets.append(tgt)

    leaks = _ring(w, f, pal, width, depth, my)
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "TARGET WALL").upper()
    what = "SHOOT THE DISC" if discs == 1 else f"SHOOT ALL {discs}"
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    [what, "centre scores", f"all {score} lamps", "rings the bell"])

    return {"kind": "aim", "width": width, "depth": depth + 1, "height": height + 1,
            "score": score, "discs": discs,
            "targets": [list(t) for t in targets], "target": list(targets[0]),
            "bells": [list(b) for b in bells], "bell": list(bells[0]),
            "lamps": [[list(x) for x in row] for row in lamps],
            "signed": signed, "leaks": leaks,
            "inputs": [list(t) for t in targets],
            "outputs": [list(b) for b in bells] + [list(x) for row in lamps for x in row],
            "stock": {},
            "contract": (f"{discs} disc(s); a hit of strength L on a disc lights the first "
                         f"min(L, {score}) lamps of THAT disc's bar and no other's, and only "
                         f"L >= {score} lights its last lamp and rings its bell"),
            "unverified": ["A TARGET'S OUTPUT IS AN INPUT YOU STATE. The simulator has no entities "
                           "and cannot fire an arrow at it; that a bullseye really reads 15 and a "
                           "rim hit really reads 1 is the game's own behaviour."]}


def _striker(w: World, p: dict, ctx) -> dict:
    """THE STRIKER. Hit the pad; the column climbs by how hard; a maximum rings the bell at the top.

    Same physics as the target wall and a completely different machine, because the drama is
    HEIGHT: `arcade.ladder` is a dust staircase with a lamp beside every step, and a hit of L dies L
    steps up. There is no repeater anywhere in it - one would restore the signal to 15 and light the
    whole tower on any hit at all, which is a lamp rather than an instrument.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    deck = max(1, int(p["deck"]))
    my = deck
    rungs = max(4, min(12, int(p["score"])))
    # A DUST STAIRCASE CLIMBS DIAGONALLY, SO THE TOWER LEANS, and the footprint has to admit it:
    # one cell of run per course is what a redstone staircase IS.
    width = rungs + 6
    depth = 3
    height = int(p.get("height") or my + 3)

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    tgt = f.at(1, depth, my)
    w.put(tgt[0], tgt[1], tgt[2], "target", power="0")
    rd = read_out(f.at(2, depth, my), D["i+"])
    _lay(w, pal, (rd,), floor=pal["wall"])
    lad = ladder(rd["out"], rungs, D["i+"], D["out"], block=pal["trim"])
    _lay(w, pal, (lad,), floor=pal["wall"])
    # THE BELL BESIDE THE TOP RUNG. The top of a `rungs`-step ladder carries a signal only when the
    # hit was at least `rungs`, so the threshold is the ladder itself and there is no gate.
    top = lad["top"]
    bi, bd, bh = _ij(f, top)
    bell = _bell(w, f, pal, bi + 1, bd, bh, p["facing"])

    leaks = _ring(w, f, pal, width, depth, my)
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "THE STRIKER").upper()
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["HIT THE DISC", "harder climbs", f"all {rungs} = bell", "nothing less"])

    return {"kind": "striker", "width": width, "depth": depth + 1,
            "height": height + rungs + 1, "rungs": rungs,
            "target": list(tgt), "bell": list(bell),
            "lamps": [list(x) for x in lad["lamps"]], "top": list(top),
            "signed": signed, "leaks": leaks,
            "inputs": [list(tgt)], "outputs": [list(bell)] + [list(x) for x in lad["lamps"]],
            "stock": {},
            "contract": (f"a hit of strength L lights the bottom min(L, {rungs}) lamps of the "
                         f"column; only L >= {rungs} reaches the top and rings the bell"),
            "unverified": ["A TARGET'S OUTPUT IS AN INPUT YOU STATE - the simulator has no "
                           "entities and cannot swing at it."]}


def _mark(w: World, p: dict, ctx) -> dict:
    """THE MARK. Load the scale until it reads EXACTLY the number on the sign - no more, no less.

    **THE ONLY BET IN THIS FILE THAT IS NOT A MAXIMUM.** Every other analog game pays for going
    high enough, which is the same game whatever number is written on it; this one pays for
    stopping in the right place, and going one over loses. `circuits.window` is the gate - an
    AND-NOT built from two perpendicular taps on one decaying run and a comparator in SUBTRACT mode
    - and the losing case is what makes it a game: overshoot and the lamp goes out again.

    The scale is a `light_weighted_pressure_plate`, which reads one level per item standing on it,
    so the player's own COUNT is the input.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    # **THE SCALE STANDS ON THE MACHINE COURSE, NOT ON THE LID**, and that is not a detail. A
    # WEIGHTED plate is an ANALOG source: it EMITS its level to its six neighbours and, unlike a
    # button or an ordinary plate, it does not strongly power the block under it - `circuit`'s
    # `SIGNAL_INPUTS` branch is taken before the plate branch and sets no `into` at all. So the
    # trick every other control here uses, reading a press out of the cell under its support, gives
    # exactly nothing: the first build of this game was silent at every level, with every block
    # legal, supported and correctly wired. The run has to touch the PLATE.
    deck = max(2, int(p["deck"]))
    my = deck
    mark = max(2, min(12, int(p["mark"])))
    band = max(1, min(4, int(p["band"])))
    # **A `window` IS FOUR CELLS DEEP ACROSS ITS OWN RUN, AND A THREE-DEEP CONSOLE ATE IT.** Its
    # lanes are the run, the taps, the gate and the output, and with the run laid along the frontage
    # those four lanes are four cells of DEPTH. Built in a console three deep, the gate landed in
    # the back board (which `arcade._lay` overwrites, because a board is structural) and the output
    # landed BEHIND it, outside the console entirely - a machine in two halves with a wall between
    # them, and zero placement problems reported.
    depth = 8
    width = mark + band + 6
    height = int(p.get("height") or my + 4)

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    plate = f.at(1, 1, my)
    # A WEIGHTED PLATE HAS `power`, NOT `powered` - it is analog, and the state audit says so.
    w.put(plate[0], plate[1], plate[2], "light_weighted_pressure_plate", power="0")

    win = circuits.window(f.at(2, 1, my), mark, mark + band, facing=D["i+"], side=-1)
    _lay(w, pal, (win,), floor=pal["wall"])

    # THE ANSWER, one lamp and one bell, because the window is a yes or a no. A bar here would be a
    # second instrument saying the same thing. **THE OUTPUT IS CONSUMED AT `next`, NEVER ONE STEP
    # BACK TOWARD THE FRONT** - the cell between the gate and the front IS the gate, and a run laid
    # through it is a run `_line` silently skips.
    nxt = win["next"]
    ni, nd, nh = _ij(f, nxt)
    w.put(nxt[0], nxt[1], nxt[2], "redstone_wire")
    lamp = f.at(ni, nd, nh + 1)
    w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")

    leaks = _ring(w, f, pal, width, depth, my)
    bell = _bell(w, f, pal, ni + 1, nd, nh, p["facing"])
    _lid(w, f, pal, width, depth, my + 1, open_at=[(1, 1)])
    title = str(p.get("title") or "THE MARK").upper()
    high = mark + band - 1
    # **THE NUMBER IS THE GAME, SO IT MUST SURVIVE THE FIFTEEN-CHARACTER CUT.** "stop at exactly
    # 4" is sixteen characters and clips to "stop at exactly" - a precision game whose sign does not
    # say what to stop at, and it only shows up in a screenshot after the build has been placed.
    rule = f"the mark is {mark}" if band == 1 else f"{mark} to {high} wins"
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["LOAD THE SCALE", rule, "over is a loss", "lamp = you won"])

    return {"kind": "mark", "width": width, "depth": depth + 1, "height": height + 1,
            "mark": mark, "band": band, "plate": list(plate), "lamp": list(lamp),
            "bell": list(bell), "signed": signed, "leaks": leaks,
            "inputs": [list(plate)], "outputs": [list(lamp), list(bell)], "stock": {},
            "contract": ("the lamp and the bell come on only while the scale reads "
                         + (f"exactly {mark}" if band == 1 else f"{mark} to {high}")
                         + "; below is dark and OVER is dark again"),
            "unverified": ["A PLATE'S LEVEL IS AN INPUT YOU STATE. The simulator has no entities "
                           "and cannot put an item on a scale; that N items really read N is the "
                           "game's own behaviour."]}


def _pair(w: World, p: dict, ctx) -> dict:
    """THE DOUBLE. Two buttons, one at each end of the counter, and the prize needs BOTH at once.

    **THE ONLY GAME IN THE PARK THAT NEEDS TWO PEOPLE.** Redstone has no AND and a comparator cannot
    be one - COMPARE passes the back when back >= side, which is a threshold, and SUBTRACT is a
    difference - so it is `arcade.and_gate`: one torch per input to invert it, one merged line, and
    one more torch to invert the merge. De Morgan, in nine blocks.

    A stone button holds for about a second, so "together" means within a second - a window a pair
    of hands can hit and one pair cannot, because the far button is eight cells away.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    deck = max(1, int(p["deck"]))
    my = deck
    spread = 8
    width = 15
    depth = 13
    height = int(p.get("height") or my + 4)

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    gate = _and(w, f, pal, D, 3, 3, my, 2)
    near, far = gate["lanes"]                     # i = 3 and i = 5
    fd = gate["feed_d"]                           # d = 2

    # THE NEAR BUTTON sits over its own lane and drops straight onto the feed.
    b0 = _face_control(w, f, pal, near, my, p["facing"])
    _line(w, pal, f, (near, 1), (near, fd), my)
    # THE FAR ONE is eight cells away and comes home along the FRONT lane, which is the one lane
    # nothing else uses. It stops on its own feed lane, so the empty column between the two feeds -
    # the column `and_gate` needs kept clear or it becomes an OR - is never written.
    b1 = _face_control(w, f, pal, near + spread, my, p["facing"])
    _line(w, pal, f, (near + spread, 1), (far, 1), my)
    _line(w, pal, f, (far, 1), (far, fd), my)

    oi, od, _ = _ij(f, gate["out"])
    guard = _guard(w, f, pal, D, oi, od + 1, my)
    lit = f.at(oi, od + 2, my)
    w.put(lit[0], lit[1], lit[2], "redstone_wire")
    lamp = f.at(oi, od + 2, my + 1)
    w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")

    leaks = _ring(w, f, pal, width, depth, my, keep=(near, near + spread))
    bell = _bell(w, f, pal, oi + 1, od + 2, my, p["facing"])
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "THE DOUBLE").upper()
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["TWO PLAYERS", "one at each end", "press TOGETHER", "one alone: no"])

    return {"kind": "pair", "width": width, "depth": depth + 1, "height": height + 1,
            "buttons": [list(b0), list(b1)], "spread": spread,
            "lamp": list(lamp), "bell": list(bell), "guard": list(guard),
            "signed": signed, "leaks": leaks,
            "inputs": [list(b0), list(b1)], "outputs": [list(lamp), list(bell)], "stock": {},
            "contract": "the lamp and the bell come on only while BOTH buttons are down together; "
                        "either one alone does nothing, and nothing fires when the machine is "
                        "first built",
            "unverified": []}


def _pattern(w: World, p: dict, ctx) -> dict:
    """THE COMBINATION. `n` levers, one setting out of two-to-the-`n`, and only that one opens it.

    **A COMBINATION IS A DIFFERENT PUZZLE FROM A SEQUENCE, and it is the one that cannot deadlock.**
    Nothing is remembered: the lock is open while the levers are right and shut the instant one
    moves, so it can be worked out by trying, left set for the next visitor, and never stranded in a
    state nobody can clear. That is the bounded-reset contract the park's own mechanics note asks of
    every puzzle, satisfied by having no state at all.

    A lever that must be DOWN is inverted by a torch on the way in, so the answer is never "all of
    them up" - which is a lock with one obvious key. The inverter is three cells of the lane it
    already owns: dust, a support the dust weakly powers, and a torch attached to that support whose
    own cell is the feed's neighbour. Every lane is two apart from its neighbour, which is what
    `and_gate` requires and what makes each one a straight run with nothing to cross.

    `door` turns the result into an iron door in the console's own face.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    deck = max(1, int(p["deck"]))
    my = deck
    want = [bool(v) for v in p["pattern"]]
    want = (want + [True, True])[:max(2, min(4, len(want) or 3))]
    n = len(want)
    # THE LANE IS SIX DEEP: seat, dust, support, torch, feed, and the gate behind it. A straight
    # lever skips the middle three and runs dust the whole way, so both cases fit one geometry.
    gd = 7
    gi = 3
    width = gi + 2 * n + 6
    # **THE CONSOLE HAS TO BE DEEPER THAN THE GATE'S TAIL, PLUS THE GUARD, PLUS THE OUTPUT, PLUS THE
    # RING.** Cut two cells short, `_ring` put a wall block straight over the guard repeater and the
    # output dust landed in the back board: the lock was silent at every one of the eight settings,
    # with zero placement problems and one connected piece. The gate's own out sits at gd+6.
    depth = gd + 10
    height = int(p.get("height") or my + 4)

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    gate = _and(w, f, pal, D, gi, gd, my, n)
    fd = gate["feed_d"]                                # gd - 1

    levers, gate_cols = [], [gate["lanes"][k] for k in range(len(want))]
    for k, up in enumerate(want):
        i = gate["lanes"][k]
        levers.append(_face_control(w, f, pal, i, my, p["facing"], "lever"))
        if up:
            _line(w, pal, f, (i, 1), (i, fd), my)
        else:
            # DUST, THEN A SUPPORT, THEN A TORCH ON IT. The torch is off while the lever's own line
            # powers the support and on when it does not, so the feed reads the lever INVERTED, and
            # the torch's own cell is already the feed's neighbour - no run at all.
            _line(w, pal, f, (i, 1), (i, fd - 3), my)
            w.put(*f.at(i, fd - 2, my), pal["wall"])
            tor = f.at(i, fd - 1, my)
            w.put(tor[0], tor[1], tor[2], "redstone_wall_torch", facing=D["in"], lit="true")

    oi, od, _ = _ij(f, gate["out"])
    guard = _guard(w, f, pal, D, oi, od + 1, my)
    lit = f.at(oi, od + 2, my)
    w.put(lit[0], lit[1], lit[2], "redstone_wire")

    # THE ANSWER RUNS TO THE FRONT. Nothing analog is being carried - the gate has already decided -
    # so a boolean may travel as far as it likes, and it has to: the gate's output is at the BACK
    # of the console and the door is the thing a customer looks at.
    di = width - 5                       # the door's own lane, clear of every lever and the gate
    _run(w, pal, f, [(oi, od + 2), (di, od + 2), (di, 1)], my)

    lamps = []
    for k in (2, 3):
        cell = f.at(oi + k, od + 2, my + 1)
        w.put(cell[0], cell[1], cell[2], "redstone_lamp", lit="false")
        lamps.append(cell)

    leaks = _ring(w, f, pal, width, depth, my, keep=tuple(gate_cols))

    door = []
    if p.get("door"):
        # **AN IRON DOOR IN THE VAULT'S OWN FACE, AND IT IS A HATCH RATHER THAN A WALK-THROUGH.**
        # The first version put it two cells from the back board, which is INSIDE the cabinet: an
        # iron door opening onto a redstone machine, described in its own contract as the one output
        # a player walks through. What a console can honestly offer is its FRONT - the door stands
        # in the ring the customer is looking at and swings when the combination is right. A
        # strongroom you can walk INTO is a room, and a room is a change to the building.
        # Placed AFTER `_ring`, or the ring walls it up again.
        for h in (0, 1):
            cell = f.at(di, 0, my + h)
            w.put(cell[0], cell[1], cell[2], "iron_door", facing=f.facing,
                  half="lower" if h == 0 else "upper", hinge="left",
                  open="false", powered="false")
            door.append(cell)

    # **THE BELL GOES ON THE FAR SIDE OF THE OUTPUT, NEVER ON THE RUN.** Placed one step ALONG the
    # frontage it landed on the first cell of the route to the door - and a bell conducts nothing,
    # so the gate read 15, the two cells either side of the bell read 15 and 0, and the lock was
    # dead at every setting on a build with zero placement problems and one connected piece. It is
    # the same cell the lamps and the door are fed through; there is only one of it.
    bell = _bell(w, f, pal, oi - 1, od + 2, my, p["facing"])
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "THE COMBINATION").upper()
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    [f"{n} LEVERS", "ONE setting", "opens it", "any other: no"])

    setting = " ".join("UP" if v else "DOWN" for v in want)
    return {"kind": "pattern", "width": width, "depth": depth + 1, "height": height + 1,
            "levers": [list(x) for x in levers], "want": list(want), "n": n,
            "lamps": [list(x) for x in lamps], "bell": list(bell), "guard": list(guard),
            "door": [list(x) for x in door], "signed": signed, "leaks": leaks,
            "inputs": [list(x) for x in levers],
            "outputs": [list(x) for x in lamps] + [list(bell)] + [list(x) for x in door],
            "stock": {}, "answer": setting,
            "contract": (f"exactly one of the {2 ** n} lever settings ({setting}) lights the lock"
                         + (" and opens the door" if door else "")
                         + f"; the other {2 ** n - 1} do nothing, and nothing opens when the "
                           f"machine is first built"),
            "unverified": []}


def _starter(w: World, p: dict, ctx) -> dict:
    """THE SIGNAL. Press READY and the countdown walks the board, then the bell sends you away.

    A chain of delay-2 repeaters, each driving its own lamp, so a single press becomes a light that
    moves - and the bell hangs on the LAST stage, so it cannot ring early. **A ONE-TICK PULSE IS
    SWALLOWED BY A DELAY-ONE REPEATER**, in this model and in the game's scheduler alike, so the
    press is stretched to four ticks before it enters the chain.

    There is nothing random in it and nothing to win: it is the launch signal at the foot of the
    spire, and what it is for is that a queue can see when it is their turn.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    deck = max(1, int(p["deck"]))
    my = deck
    stages = max(3, min(8, int(p["stages"])))
    width = stages * 2 + 6
    depth = 4
    height = int(p.get("height") or my + 4)

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    btn = _face_control(w, f, pal, 1, my, p["facing"])
    seat = f.at(1, 2, my)
    w.put(seat[0], seat[1], seat[2], "redstone_wire")
    # **THE PULSE'S DELAY LEG IS PERPENDICULAR AND IT HAS A SIDE.** On `side=1` it landed on the
    # console's own front ring - three cells of live dust showing on the outside of the cabinet,
    # which `_ring` reports as a leak. It runs inward instead.
    pul = circuits.pulse(f.at(1, 1, my), length=4, facing=D["i+"], side=-1)
    _lay(w, pal, (pul,), floor=pal["wall"])
    pi, pd, _ = _ij(f, pul["out"])
    _run(w, pal, f, [(pi, pd), (2, pd), (2, 1)], my)

    lamps = []
    for k in range(stages):
        rep = f.at(3 + k * 2, 1, my)
        dust = f.at(4 + k * 2, 1, my)
        w.put(rep[0], rep[1], rep[2], "repeater", facing=D["i+"], delay="2",
              locked="false", powered="false")
        w.put(dust[0], dust[1], dust[2], "redstone_wire")
        lamp = f.at(4 + k * 2, 2, my)
        w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")
        lamps.append(lamp)

    last_i = 4 + (stages - 1) * 2
    leaks = _ring(w, f, pal, width, depth, my, keep=(1,))
    bell = _bell(w, f, pal, last_i + 1, 1, my, p["facing"])
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "THE SIGNAL").upper()
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["PRESS TO START", "the light runs", "the board, then", "the bell: go"])

    return {"kind": "starter", "width": width, "depth": depth + 1, "height": height + 1,
            "stages": stages, "button": list(btn), "bell": list(bell),
            "lamps": [list(x) for x in lamps], "signed": signed, "leaks": leaks,
            "inputs": [list(btn)], "outputs": [list(x) for x in lamps] + [list(bell)], "stock": {},
            "contract": (f"one press walks a light along {stages} lamps in order and rings the bell "
                         f"at the end; the bell does not ring before the last lamp has lit"),
            "unverified": []}


def _counter(w: World, p: dict, ctx) -> dict:
    """THE PRIZE COUNTER. Where what you won is redeemed, and where you can see what is left.

    **NOT A GAME, AND THAT IS THE POINT.** Nothing in this file dispenses a prize, because a machine
    that pays on a held reading is how a house loses money by accident - the casino pins that hazard
    and does not fix it. The prizes live in barrels a person hands out, and the one thing the
    redstone does is tell the truth about them: a comparator reads each barrel and lights that
    window's lamp exactly when there is something in it.

    An EMPTY window is dark. That is the whole contract, and it is worth having: a counter with
    nothing behind it is what every fairground prize wall in the game actually is.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    deck = max(1, int(p["deck"]))
    my = deck
    lanes = max(2, min(6, int(p["lanes"])))
    width = lanes * 3 + 4
    depth = 4
    height = int(p.get("height") or my + 4)

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    barrels, lamps = [], []
    for k in range(lanes):
        i = 1 + k * 3
        # **A COMPARATOR READS WHAT IS BEHIND IT, WHICH MEANS BESIDE IT, NOT ABOVE IT.** The first
        # build put each comparator directly over its barrel, which reads whatever is BEHIND the
        # comparator on its own course - air - so every window was dark however the barrel was
        # stocked, and every block in it was legal, supported and correctly wired. The barrel is set
        # into the counter's FRONT face where a customer can see it opened, and the comparator sits
        # directly behind it on the same course.
        bar = f.at(i, 0, my)
        w.put(bar[0], bar[1], bar[2], "barrel", facing=f.facing, open="false")
        barrels.append(bar)
        w.put(*f.at(i, 1, my), "comparator", facing=D["in"], mode="compare", powered="false")
        dust = f.at(i, 2, my)
        w.put(dust[0], dust[1], dust[2], "redstone_wire")
        # THE LAMP IS IN THE COUNTER TOP OVER ITS OWN DUST, so a lit window is read from where a
        # customer stands rather than from behind the counter.
        lamp = f.at(i, 2, my + 1)
        w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")
        lamps.append(lamp)

    call = _face_control(w, f, pal, width - 2, my, p["facing"])
    seat = f.at(width - 2, 2, my)
    w.put(seat[0], seat[1], seat[2], "redstone_wire")

    leaks = _ring(w, f, pal, width, depth, my, keep=(width - 2,))
    bell = _bell(w, f, pal, width - 2, 1, my, p["facing"])
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "PRIZE COUNTER").upper()
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["REDEEM HERE", "a lit window", "is in stock", "button = ring"])

    return {"kind": "counter", "width": width, "depth": depth + 1, "height": height + 1,
            "lanes": lanes, "barrels": [list(x) for x in barrels],
            "lamps": [list(x) for x in lamps], "bell": list(bell), "button": list(call),
            "signed": signed, "leaks": leaks,
            "inputs": [list(x) for x in barrels] + [list(call)],
            "outputs": [list(x) for x in lamps] + [list(bell)],
            "stock": {"each barrel": "the prize that window redeems"},
            "contract": "each window's lamp is lit exactly while its own barrel holds something "
                        "and dark when that barrel is empty, and no window answers for another; "
                        "the call button rings the counter bell",
            "unverified": ["WHAT IS IN A BARREL IS AN INPUT YOU STATE. The simulator has no "
                           "entities and cannot stock or empty one."]}


BUILDERS = {
    "aim": _aim,
    "striker": _striker,
    "mark": _mark,
    "pair": _pair,
    "pattern": _pattern,
    "starter": _starter,
    "counter": _counter,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**GAME, **cfg}
    if not p.get("at"):
        raise ValueError("park_games needs params.at = [x, y, z] of the front-left standing cell")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown park_games kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in PALETTES:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(PALETTES)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    # **THE SIGHTLINES, CARVED ONCE FOR EVERY KIND.** Each builder states its own `inputs` and
    # `outputs`, so this is the one place that knows what a player has to see and touch without
    # knowing anything about how the game works - and doing it here rather than seven times is
    # what stops the next kind shipping sealed. A readout is GLAZED and a control is OPEN: a lamp
    # must be seen and must not be reachable, a disc must be shot and glass stops an arrow.
    f0 = _Frame(p)
    deep = int(meta.get("depth") or 4)
    fabric = {PALETTES[p["land"]][k] for k in ("wall", "trim", "ground", "accent")
              if k in PALETTES[p["land"]]} | {"glass_pane"}
    _daylight(w, f0, [tuple(q) for q in meta.get("outputs") or []], deep,
              pane="glass_pane", fabric=fabric)
    _daylight(w, f0, [tuple(q) for q in meta.get("inputs") or []], deep,
              pane=None, fabric=fabric)
    _reattach(w, f0, PALETTES[p["land"]], [tuple(q) for q in meta.get("inputs") or []])
    _seal(w, f0, deep)

    # **NOTHING MAY BE WRITTEN WHERE THE BUILDING ALREADY STANDS.** A console is fitted into a room
    # that exists, so a cell the capture owns is not a cell to compose with - it is an overlap, and
    # `overlap 0` is the one property that makes this design safe to place beside sixteen finished
    # buildings. Refused cells are COUNTED rather than silently dropped: a machine missing a cell is
    # a machine that does nothing, so a non-zero count is a siting error and the tests fail on it.
    refused = []
    if ctx is not None:
        for pos in list(w.cells):
            if ctx.occupied(*pos):
                refused.append(list(pos))
                del w.cells[pos]
                w.signs.pop(pos, None)

    budget = {}
    for _pos, (name, _pr) in w.cells.items():
        if name in ("redstone_lamp", "note_block"):
            budget[name] = budget.get(name, 0) + 1

    f = _Frame(p)
    ijs = [_ij(f, c) for c in w.cells]
    lo_i, hi_i = min(v[0] for v in ijs), max(v[0] for v in ijs)
    lo_d, hi_d = min(v[1] for v in ijs), max(v[1] for v in ijs)
    lo_h, hi_h = min(v[2] for v in ijs), max(v[2] for v in ijs)

    return w.canvas({
        "kind": f"park_games/{p['kind']}",
        "building": p.get("building", ""),
        "land": p["land"],
        "facing": p["facing"],
        "footprint": [hi_i - lo_i + 1, hi_d - lo_d + 1],
        "courses": [lo_h, hi_h],
        "budget": budget,
        "refused": refused,
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
