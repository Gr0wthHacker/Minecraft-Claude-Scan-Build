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
    pair       THE DOUBLE           two buttons, two people, one prize - press together
    mark       THE MARK             load the scale to EXACTLY the number on the sign
    striker    THE STRIKER          hit it; the column climbs; a maximum rings the bell
    counter    THE PRIZE COUNTER    prize windows that show what is actually in stock
    pattern    THE ARRAY            three levers; exactly one of eight patterns aligns it
    sequence   THE VAULT            three keys, IN ORDER, and the strongroom opens
    starter    THE SIGNAL           a countdown that runs down the board and rings you away

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
  redeem at. `counter` is that counter, and its droppers are not wired to anything a player can
  reach - the stock lamps are.
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
  ticket does not own. It is written up in the report instead. Until it is closed, the Midway's
  games are games of SKILL and no sign in this park states odds it cannot keep.
* **THE PRISM ASCENT'S SPIRE CARRIES NO SIGNAL.** Its shaft is 79 courses of hollow core divided by
  solid diaphragms at Y232, Y250, Y264 and Y274, and its outer face is broken by four fin blades.
  A dust staircase needs one block of horizontal run per course and there is nowhere to spend 79 of
  them; a torch ladder alternates on and off by construction, so half the tower is lit at rest. The
  launch chamber at its foot gets a real countdown; what the spire itself would need is openings in
  its own shell, which is a change to `prismworks_builds.py`.

GEOMETRY is `gen/park.py`'s `_Frame`, unchanged, so a console sits in a room exactly as a stall
sits on a street:

    at       the console's FRONT-LEFT cell on the course a player STANDS on (y = floor + 1)
    facing   the direction the front looks out - a visitor stands in the +facing direction
    i        along the frontage      d   from the front INTO the console      h   courses up
"""
from __future__ import annotations

from . import circuits
from .arcade import _SIDE, _dirs, _ij, _lay, _line, _run, and_gate, ladder, read_out
from .canvas import Canvas
from .park import LANDS, SIGN_WIDTH, _BACK, _STEP, _Frame, _sign
from .vertical import Ctx, World

# ---------------------------------------------------------------------------- palettes
#
# **NOT `LANDS` VERBATIM, AND FOR TWO MEASURED REASONS.** The frontier's `ground` there is
# `cobblestone`, which this ticket bars outright; and there is no `prismworks` entry at all,
# because the land was written after `park.py` and keeps its palette in `prismworks_builds.PRISM`.
# The keys are exactly the ones `arcade._structural`, `_line`, `_button`, `_sign` and `_hang_light`
# read, so a console can be handed to any of those helpers whatever land it stands in.

_PRISM = {
    "ground": "chiseled_deepslate",             # 54 - the land's own interior floor
    "path": "polished_deepslate",
    "wall": "polished_blackstone_bricks",       # 45 - the field
    "trim": "smooth_basalt",                    # 73 - the string course, +28 on the field
    "post": "blackstone",
    "beam": "polished_blackstone_bricks",
    "slab": "polished_blackstone_brick_slab",
    "stair": "polished_blackstone_brick_stairs",
    "fence": "warped_fence",
    "gate": "warped_fence_gate",
    "light": "soul_lantern",
    "canopy": ["black_wool", "deepslate_bricks"],
    "accent": "cyan_wool",                      # 104 - the land's signal colour
    "wood": "warped",
}

_FRONTIER = {
    **LANDS["frontier"],
    # COBBLESTONE IS BARRED BY THIS TICKET, and the land's own buildings do not use it either:
    # `frontier_builds.PAL` puts `stone_bricks` under everything and a blackstone plinth below that.
    "ground": "stone_bricks",
    "trim": "polished_blackstone_bricks",
    "path": "smooth_stone",
}

PALETTES = {"midway": LANDS["midway"], "frontier": _FRONTIER, "prismworks": _PRISM}

GAME = {
    "under": None,              # capture(s) the console is fitted into - see `Ctx`
    "at": None,                 # world (x, y, z): FRONT-LEFT cell of the STANDING course
    "facing": "east",
    "land": "midway",
    "kind": "aim",
    "title": None,
    "building": "",             # which module this fits out, for the sidecar
    "deck": 1,                  # how many courses of plinth under the machine course
    "score": 6,                 # aim/striker: how many lamps, and the level that rings the bell
    "mark": 4,                  # mark: the exact reading that wins
    "band": 1,                  # mark: how wide the winning window is
    "lanes": 4,                 # counter: how many prize windows
    "stages": 5,                # starter: how many countdown lamps
    "pattern": (True, False, True),   # pattern: the one lever setting that aligns the array
    "sign": True,
}
DEFAULTS = GAME


# ---------------------------------------------------------------------------- the console
#
# One shape, eight games. A console is furniture: a player cannot walk through it, which is exactly
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


def _ring(w: World, f, pal: dict, width: int, depth: int, h: int) -> None:
    """The machine course's own wall, and the reason it is a RING rather than a fill.

    Filling every unused cell of the machine course would put a solid block against every component
    in it - and a repeater or comparator aimed at a solid block STRONGLY powers it, which then
    passes 15 to any dust touching its far side. That is a short across the machine, invisible in
    every render. A hollow box has no far side to short to.
    """
    for i in range(width):
        for d in range(depth):
            if i in (0, width - 1) or d in (0, depth - 1):
                w.put(*f.at(i, d, h), pal["wall"])


def _lid(w: World, f, pal: dict, width: int, depth: int, h: int, open_at=()) -> None:
    """The counter top, laid LAST so it never covers a lamp or a prize hatch already placed.

    `open_at` is what a caller has to say out loud: a scale you cannot drop anything on is a scale
    with a lid over it, and `w.has` cannot see that because the cell it would fill is genuinely
    empty - the plate is a course BELOW.
    """
    skip = {tuple(c) for c in open_at}
    for i in range(width):
        for d in range(depth):
            if (i, d) in skip or w.has(*f.at(i, d, h)):
                continue
            w.put(*f.at(i, d, h), pal["trim"])


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
    """A lamp in FRONT of every cell of a dust run, standing on the console's own top.

    **THE LAMP GOES BESIDE THE DUST, NEVER ON TOP OF IT.** Above it, it is a full block resting on
    redstone - a placement the game refuses and a display that pops the first time the chunk loads.
    Beside it, on the same course, it is simply adjacent and it is what the player is looking at.
    """
    out = []
    for (i, d) in run:
        pos = f.at(i, side_d, h)
        w.put(pos[0], pos[1], pos[2], "redstone_lamp", lit="false")
        out.append(pos)
    return out


def _bell(w: World, f, pal: dict, i: int, d: int, h: int, facing: str) -> tuple:
    """A bell on its own block, beside the cell that rings it.

    A `bell` with `attachment=floor` needs a real floor: hung in the cell directly over the wire
    that rings it, three arcade games shipped a bell the game will not place at all.
    """
    pos = f.at(i, d, h)
    if not w.has(*f.at(i, d, h - 1)):
        w.put(*f.at(i, d, h - 1), pal["wall"])
    w.put(pos[0], pos[1], pos[2], "bell", attachment="floor", facing=facing, powered="false")
    return pos


def _press(w: World, f, pal: dict, i: int, d: int, h: int, facing: str, block: str = "") -> tuple:
    """A button on the counter top, on a pad of the land's accent so it reads as the thing to press.

    A FLOOR BUTTON STRONGLY POWERS THE BLOCK BENEATH IT, and dust in the cell under that block is
    adjacent to it, so a press on the lid arrives in the machine course with no routing at all.
    That one fact is what lets every control here sit where a hand can reach it while the machine
    stays sealed a course below.
    """
    pad = f.at(i, d, h - 1)
    w.put(pad[0], pad[1], pad[2], block or pal["accent"])
    pos = f.at(i, d, h)
    w.put(pos[0], pos[1], pos[2], "stone_button", face="floor", facing=facing, powered="false")
    return pos


def _lever(w: World, f, pal: dict, i: int, d: int, h: int, facing: str) -> tuple:
    """A lever on the counter top. Same route as a button and it HOLDS, which is what a lock needs."""
    pad = f.at(i, d, h - 1)
    w.put(pad[0], pad[1], pad[2], pal["accent"])
    pos = f.at(i, d, h)
    w.put(pos[0], pos[1], pos[2], "lever", face="floor", facing=facing, powered="false")
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

    That number never leaves the cell it is made in: the comparator behind the disc opens straight
    onto the bar, and the bar IS the decay. Dust loses one per block, so a hit of L lights L lamps,
    and the LAST lamp lights only when L reached the end of the run - which is the threshold, for
    free, with no gate to build and nothing to tune. The bell hangs beside that last cell.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    deck = max(1, int(p["deck"]))
    my = deck                                     # the machine course
    score = max(3, min(12, int(p["score"])))
    width = score + 6
    depth = 3
    height = my + 5

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    # THE DISC, set into the board at the machine course so the reading, the bar and the bell are
    # all on one plane. Two courses up it would be a better shot and the analog value would have to
    # climb to reach its own display, which is the one thing it cannot do.
    tgt = f.at(1, depth, my)
    w.put(tgt[0], tgt[1], tgt[2], "target", power="0")
    rd = read_out(f.at(2, depth, my), D["i+"])
    _lay(w, pal, (rd,), floor=pal["wall"])

    run = []
    for k in range(score):
        i = 3 + k
        cell = f.at(i, depth, my)
        w.put(cell[0], cell[1], cell[2], "redstone_wire")
        run.append((i, depth))
    lamps = _lamp_row(w, f, run, depth - 1, my)

    last_i = 3 + score - 1
    bell = _bell(w, f, pal, last_i + 1, depth, my, p["facing"])

    _ring(w, f, pal, width, depth, my)
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "TARGET WALL").upper()
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["SHOOT THE DISC", "centre scores", f"all {score} lamps", "rings the bell"])

    return {"kind": "aim", "width": width, "depth": depth + 1, "height": height + 1,
            "score": score, "target": list(tgt), "bell": list(bell),
            "lamps": [list(x) for x in lamps], "comparator": list(rd["cells"] and next(iter(rd["cells"]))),
            "signed": signed,
            "inputs": [list(tgt)], "outputs": [list(bell)] + [list(x) for x in lamps],
            "stock": {},
            "contract": (f"a hit of strength L lights the first min(L, {score}) lamps; only "
                         f"L >= {score} lights the last one and rings the bell"),
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
    height = my + 3

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

    _ring(w, f, pal, width, depth, my)
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "THE STRIKER").upper()
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["HIT THE DISC", "harder climbs", f"light all {rungs}", "to ring the bell"])

    return {"kind": "striker", "width": width, "depth": depth + 1,
            "height": height + rungs + 1, "rungs": rungs,
            "target": list(tgt), "bell": list(bell),
            "lamps": [list(x) for x in lad["lamps"]], "top": list(top), "signed": signed,
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
    height = my + 4

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    plate = f.at(1, 1, my)
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

    _ring(w, f, pal, width, depth, my)
    bell = _bell(w, f, pal, ni + 1, nd, nh, p["facing"])
    _lid(w, f, pal, width, depth, my + 1, open_at=[(1, 1)])
    title = str(p.get("title") or "THE MARK").upper()
    high = mark + band - 1
    rule = f"exactly {mark}" if band == 1 else f"{mark} to {high}"
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["LOAD THE SCALE", f"stop at {rule}", "over is a loss", "lamp = you won"])

    return {"kind": "mark", "width": width, "depth": depth + 1, "height": height + 1,
            "mark": mark, "band": band, "plate": list(plate), "lamp": list(lamp),
            "bell": list(bell), "signed": signed,
            "inputs": [list(plate)], "outputs": [list(lamp), list(bell)], "stock": {},
            "contract": (f"the lamp and the bell come on only while the scale reads {mark} to "
                         f"{high}; below is dark and OVER is dark again"),
            "unverified": ["A PLATE'S LEVEL IS AN INPUT YOU STATE. The simulator has no entities "
                           "and cannot put an item on a scale; that N items really read N is the "
                           "game's own behaviour."]}


def _pair(w: World, p: dict, ctx) -> dict:
    """THE DOUBLE. Two buttons a room apart, and the prize only lights when both are down at once.

    **THE ONLY GAME IN THE PARK THAT NEEDS TWO PEOPLE**, and it is the cheapest one here: an
    `arcade.and_gate` is one torch per input and one more to invert the merge, because redstone has
    no AND and a comparator cannot be one - COMPARE passes the back when back >= side, which is a
    threshold, and SUBTRACT is a difference. De Morgan does the rest.

    Each button is stretched by `circuits.pulse` so a press is a fixed window rather than however
    long a finger stayed down; miss the window and the gate sees one input and does nothing.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    deck = max(1, int(p["deck"]))
    my = deck
    width = 15
    depth = 5
    height = my + 5

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    # THE GATE, on its own lane at the back of the console, its two feeds two apart - which is what
    # `and_gate`'s geometry is for, and why the odd rows between them must stay empty: a cell
    # powered there powers BOTH inverters and the gate silently becomes an OR.
    gate = and_gate(f.at(6, 1, my), D["i+"], D["in"])
    _lay(w, pal, (gate,), floor=pal["wall"])

    presses, pulses = [], []
    for k, i in enumerate((1, width - 2)):
        btn = _press(w, f, pal, i, 2, my + 2, p["facing"])
        presses.append(btn)
        # The button's block is at my+1; the dust it powers is the cell under it, at the machine
        # course, which is where the pulse takes its input from.
        seat = f.at(i, 2, my)
        w.put(seat[0], seat[1], seat[2], "redstone_wire")
        pul = circuits.pulse(f.at(i, 3, my), length=3,
                             facing=D["in"] if k == 0 else D["in"], side=1 if k == 0 else -1)
        _lay(w, pal, (pul,), floor=pal["wall"])
        pulses.append(pul)
        pi, pd, _ = _ij(f, pul["out"])
        feed = gate["feeds"][k]
        fi, fd, _ = _ij(f, feed)
        _run(w, pal, f, [(pi, pd), (pi, fd), (fi, fd)], my)

    oi, od, _ = _ij(f, gate["out"])
    lamp = f.at(oi, od, my + 1)
    w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")
    bell = _bell(w, f, pal, oi + 1, od, my, p["facing"])

    _ring(w, f, pal, width, depth, my)
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "THE DOUBLE").upper()
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["TWO PLAYERS", "one at each end", "press TOGETHER", "one alone: no"])

    return {"kind": "pair", "width": width, "depth": depth + 1, "height": height + 1,
            "buttons": [list(b) for b in presses], "lamp": list(lamp), "bell": list(bell),
            "signed": signed,
            "inputs": [list(b) for b in presses], "outputs": [list(lamp), list(bell)], "stock": {},
            "contract": "the lamp and the bell come on only when BOTH buttons are pressed together; "
                        "either one alone does nothing at all",
            "unverified": []}


def _pattern(w: World, p: dict, ctx) -> dict:
    """THE ARRAY. Three levers, eight settings, and exactly one of them aligns it.

    **A COMBINATION, WHICH IS A DIFFERENT PUZZLE FROM A SEQUENCE.** Nothing is remembered here: the
    array is aligned while the levers are right and falls out of alignment the moment one moves, so
    it can be worked out by trying, it can be left set for the next visitor, and it cannot deadlock.
    That is the free route-choice contract the park's own mechanics note asks for - a wrong choice
    returns you safely to a previous branch.

    A lever that must be DOWN is inverted by a torch before it reaches the gate, so the pattern is
    not "all three on" - which would be a machine you cannot get wrong.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    deck = max(1, int(p["deck"]))
    my = deck
    want = tuple(bool(v) for v in p["pattern"])[:3]
    want = want + (True,) * (3 - len(want))
    width = 21
    depth = 7
    height = my + 5

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    gate = and_gate(f.at(2, 1, my), D["i+"], D["in"], inputs=3)
    _lay(w, pal, (gate,), floor=pal["wall"])

    levers = []
    for k in range(3):
        i = 4 + k * 5
        lev = _lever(w, f, pal, i, 5, my + 2, p["facing"])
        levers.append(lev)
        seat = f.at(i, 5, my)
        w.put(seat[0], seat[1], seat[2], "redstone_wire")
        src = (i, 5)
        if not want[k]:
            # AN INVERTED INPUT IS A TORCH, and the torch must stand on a block the lever's own
            # line powers - never on the line itself. Dust one step along, then a support, then the
            # torch on top of it, and the torch's output is the cell above.
            sup = f.at(i, 4, my)
            w.put(sup[0], sup[1], sup[2], pal["wall"])
            tor = f.at(i, 4, my + 1)
            w.put(tor[0], tor[1], tor[2], "redstone_torch", lit="true")
            # the torch drives the block above it; a dust cell beside the torch reads it directly.
            out = f.at(i, 3, my + 1)
            w.put(out[0], out[1], out[2], "redstone_wire")
            w.put(*f.at(i, 3, my), pal["wall"])
            _run(w, pal, f, [(i, 3)], my + 1)
            src = None
            # drop back to the machine course beside the torch, clear of the lever's own dust
            step = f.at(i, 2, my + 1)
            w.put(step[0], step[1], step[2], "redstone_wire")
            w.put(*f.at(i, 2, my), pal["wall"])
            src = (i, 2)
            fi, fd, _ = _ij(f, gate["feeds"][k])
            _run(w, pal, f, [(i, 3), (i, 2)], my + 1)
            _line(w, pal, f, (i, 2), (i, 2), my + 1)
            # ...and across to the gate, one course up, then down onto the feed.
            _run(w, pal, f, [(i, 2), (fi + 1, 2), (fi + 1, fd)], my + 1)
            _line(w, pal, f, (fi + 1, fd), (fi, fd), my + 1)
            continue
        fi, fd, _ = _ij(f, gate["feeds"][k])
        _run(w, pal, f, [src, (i, fd), (fi, fd)], my)

    oi, od, _ = _ij(f, gate["out"])
    lamps = []
    for k in range(3):
        cell = f.at(oi, od, my + 1) if k == 0 else f.at(oi - k, od, my + 1)
        w.put(cell[0], cell[1], cell[2], "redstone_lamp", lit="false")
        lamps.append(cell)
        if k:
            _line(w, pal, f, (oi, od), (oi - k, od), my)
    bell = _bell(w, f, pal, oi + 1, od, my, p["facing"])

    _ring(w, f, pal, width, depth, my)
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "THE ARRAY").upper()
    setting = " ".join("UP" if v else "DOWN" for v in want)
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["THREE LEVERS", "one setting only", "aligns the array", "lamps = aligned"])

    return {"kind": "pattern", "width": width, "depth": depth + 1, "height": height + 1,
            "levers": [list(x) for x in levers], "want": list(want),
            "lamps": [list(x) for x in lamps], "bell": list(bell), "signed": signed,
            "inputs": [list(x) for x in levers],
            "outputs": [list(x) for x in lamps] + [list(bell)], "stock": {},
            "answer": setting,
            "contract": (f"exactly one of the eight lever settings ({setting}) lights the array and "
                         f"rings the bell; the other seven do nothing"),
            "unverified": []}


def _sequence(w: World, p: dict, ctx) -> dict:
    """THE VAULT. Three keys, and they only count IN ORDER.

    **THE ONE MECHANIC IN THIS REPO THAT REMEMBERS ANYTHING.** Every other game is combinational -
    it answers about the instant it is asked. A lock has to hold what you have already done, which
    is what `circuits.latch` is: two repeaters locking each other, the mechanism every memory cell
    in the game is built from.

    Key 1 sets the first latch on its own. Key 2 is an AND of its own button and latch 1, key 3 an
    AND of its own button and latch 2, so pressing three before one does nothing at all - the order
    is enforced by the machine and not by a sign. The third latch drives the strongroom door and a
    lever on the counter resets all three, which is the bounded reset the park's mechanics contract
    asks of every tier-3 system: no state a visitor can get stuck in.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    deck = max(1, int(p["deck"]))
    my = deck
    width = 27
    depth = 9
    height = my + 5

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    latches, gates, buttons = [], [], []
    for k in range(3):
        i = 3 + k * 8
        btn = _press(w, f, pal, i, 7, my + 2, p["facing"])
        buttons.append(btn)
        seat = f.at(i, 7, my)
        w.put(seat[0], seat[1], seat[2], "redstone_wire")
        pul = circuits.pulse(f.at(i, 6, my), length=3, facing=D["in"], side=1)
        _lay(w, pal, (pul,), floor=pal["wall"])
        pi, pd, _ = _ij(f, pul["out"])

        lat = circuits.latch(f.at(i, 2, my), facing=D["in"])
        _lay(w, pal, (lat,), floor=pal["wall"])
        latches.append(lat)
        si, sd, _ = _ij(f, lat["set"])

        if k == 0:
            _run(w, pal, f, [(pi, pd), (pi, sd), (si, sd)], my)
        else:
            # KEY k COUNTS ONLY WHILE KEY k-1 IS ALREADY HELD, which is the whole of the order rule.
            ag = and_gate(f.at(i + 3, 4, my), D["in"], D["i+"])
            _lay(w, pal, (ag,), floor=pal["wall"])
            gates.append(ag)
            ai, ad, _ = _ij(f, ag["feeds"][0])
            bi2, bd2, _ = _ij(f, ag["feeds"][1])
            _run(w, pal, f, [(pi, pd), (ai, pd), (ai, ad)], my)
            oi_prev, od_prev, _ = _ij(f, latches[k - 1]["out"])
            _run(w, pal, f, [(oi_prev, od_prev), (oi_prev, bd2), (bi2, bd2)], my)
            gi, gd, _ = _ij(f, ag["out"])
            _run(w, pal, f, [(gi, gd), (gi, sd), (si, sd)], my)

    # THE RESET, and it is not decoration: a lock with no way back is a lock that strands the next
    # visitor with a door that will not open and no way to make it.
    reset = _lever(w, f, pal, width - 2, 7, my + 2, p["facing"])
    rseat = f.at(width - 2, 7, my)
    w.put(rseat[0], rseat[1], rseat[2], "redstone_wire")
    for k, lat in enumerate(latches):
        ri, rd, _ = _ij(f, lat["reset"])
        _run(w, pal, f, [(width - 2, 7), (width - 2, rd), (ri, rd)], my)

    oi, od, _ = _ij(f, latches[-1]["out"])
    lamps = []
    for k in range(2):
        cell = f.at(oi - k, od, my + 1)
        w.put(cell[0], cell[1], cell[2], "redstone_lamp", lit="false")
        lamps.append(cell)
        if k:
            _line(w, pal, f, (oi, od), (oi - k, od), my)
    bell = _bell(w, f, pal, oi + 1, od, my, p["facing"])

    # THE DOOR. An iron door is two blocks and it is the one output in this file a player walks
    # THROUGH rather than looks at, which is what makes a strongroom a strongroom.
    door_i = oi - 3
    door = []
    for h in (0, 1):
        cell = f.at(door_i, od, my + h)
        w.put(cell[0], cell[1], cell[2], "iron_door", facing=D["out"],
              half="lower" if h == 0 else "upper", hinge="left", open="false", powered="false")
        door.append(cell)
    _line(w, pal, f, (oi, od), (door_i + 1, od), my)

    _ring(w, f, pal, width, depth, my)
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "THE VAULT").upper()
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["THREE KEYS", "left to right", "wrong order: no", "lever = reset"])

    return {"kind": "sequence", "width": width, "depth": depth + 1, "height": height + 1,
            "buttons": [list(b) for b in buttons], "reset": list(reset),
            "lamps": [list(x) for x in lamps], "bell": list(bell),
            "door": [list(x) for x in door], "signed": signed,
            "inputs": [list(b) for b in buttons] + [list(reset)],
            "outputs": [list(x) for x in door] + [list(x) for x in lamps] + [list(bell)],
            "stock": {},
            "contract": "the door opens only after all three keys are pressed IN ORDER; a key "
                        "pressed out of turn does nothing, the state HOLDS between presses, and "
                        "the lever puts every latch back",
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
    height = my + 5

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    btn = _press(w, f, pal, 1, 2, my + 2, p["facing"])
    seat = f.at(1, 2, my)
    w.put(seat[0], seat[1], seat[2], "redstone_wire")
    pul = circuits.pulse(f.at(1, 1, my), length=4, facing=D["i+"], side=1)
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

    last = (4 + (stages - 1) * 2, 1)
    bell = _bell(w, f, pal, last[0] + 1, last[1], my, p["facing"])

    _ring(w, f, pal, width, depth, my)
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "THE SIGNAL").upper()
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["PRESS TO START", "the light runs", "the board, then", "the bell: go"])

    return {"kind": "starter", "width": width, "depth": depth + 1, "height": height + 1,
            "stages": stages, "button": list(btn), "bell": list(bell),
            "lamps": [list(x) for x in lamps], "signed": signed,
            "inputs": [list(btn)], "outputs": [list(x) for x in lamps] + [list(bell)], "stock": {},
            "contract": (f"one press walks a light along {stages} lamps in order and rings the bell "
                         f"at the end; the bell does not ring before the last lamp has lit"),
            "unverified": []}


def _counter(w: World, p: dict, ctx) -> dict:
    """THE PRIZE COUNTER. Where what you won is redeemed, and where you can see what is left.

    **NOT A GAME, AND THAT IS THE POINT.** Nothing in this file dispenses a prize, because a
    machine that pays on a held reading is how a house loses money by accident - the casino pins
    that hazard and does not fix it. The prizes live in barrels a person hands out, and the one
    thing the redstone does is tell the truth about them: a comparator reads each barrel and lights
    that window's lamp exactly when there is something in it.

    An EMPTY window is dark. That is the whole contract, and it is worth having: a counter with
    nothing behind it is the thing every fairground prize wall in the game actually is.
    """
    f = _Frame(p)
    pal = PALETTES[p["land"]]
    D = _dirs(p["facing"])
    deck = max(1, int(p["deck"]))
    my = deck
    lanes = max(2, min(6, int(p["lanes"])))
    width = lanes * 3 + 3
    depth = 3
    height = my + 5

    _plinth(w, f, pal, width, depth, deck)
    _board(w, f, pal, width, depth, height)

    barrels, lamps = [], []
    for k in range(lanes):
        i = 2 + k * 3
        bar = f.at(i, depth, my)
        w.put(bar[0], bar[1], bar[2], "barrel", facing="up", open="false")
        rd = read_out(f.at(i, depth, my + 1), D["i+"])
        # A COMPARATOR READS WHAT IS BEHIND IT, and a barrel's fullness is read from any side. Set
        # it directly over the barrel and aim it along the frontage, so the reading never travels.
        w.put(*f.at(i, depth, my + 1), "comparator", facing=D["i+"], mode="compare",
              powered="false")
        dust = f.at(i + 1, depth, my + 1)
        w.put(dust[0], dust[1], dust[2], "redstone_wire")
        w.put(*f.at(i + 1, depth, my), pal["wall"])
        lamp = f.at(i + 1, depth - 1, my + 1)
        w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")
        barrels.append(bar)
        lamps.append(lamp)

    bell = _bell(w, f, pal, width - 2, 1, my + 1, p["facing"])
    call = _press(w, f, pal, width - 2, 2, my + 2, p["facing"])
    seat = f.at(width - 2, 2, my + 1)
    w.put(seat[0], seat[1], seat[2], "redstone_wire")
    w.put(*f.at(width - 2, 2, my), pal["wall"])

    _ring(w, f, pal, width, depth, my)
    _lid(w, f, pal, width, depth, my + 1)
    title = str(p.get("title") or "PRIZE COUNTER").upper()
    signed = _signs(w, f, pal, p, width, depth, height, title,
                    ["REDEEM HERE", "a lit window", "is in stock", "button = ring"])

    return {"kind": "counter", "width": width, "depth": depth + 1, "height": height + 1,
            "lanes": lanes, "barrels": [list(x) for x in barrels],
            "lamps": [list(x) for x in lamps], "bell": list(bell), "button": list(call),
            "signed": signed,
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
    "sequence": _sequence,
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
