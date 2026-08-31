"""Ticketing: the park's entrance, and the one mechanism in it that has to WORK.

A park you walk straight into is not a park. This is the arrival sequence -- queue, box office,
barrier, lockers -- and exactly one part of it carries a signal:

    boxoffice    the vending hall. Chests of tickets on a counter, a price board naming GRASS.
                 NO MECHANISM AT ALL, and that is a decision, not an omission - see below.
    queue        a switchback line with a canopy. Architecture; one connected walk, two ends.
    ticketgate   THE BARRIER. Drop the ticket in the slot; the iron door opens for ~1.5s and
                 closes by itself. The ticket falls through to a collection barrel behind.
    turnstile    the same barrier driven by a BUTTON - the exit/staff lane, where no ticket is
                 owed. Same verified mechanism, different trigger.
    ridegate     a one-lane version for a ride's own entrance, with a lamp that lights when open.
    lockers      barrels in a shelter, numbered, with room to stand and open them.

**THE HOUSE RULE OF THIS REPO IS THAT AN UNVERIFIED MECHANISM DOES NOT SHIP.** Two finished casino
games were deleted for being unassertable. So every cell here that carries a signal is part of a
chain whose contract `tests/test_ticketing.py` asserts by SIMULATION through `mcbuild.circuit`:
closed at rest, open on the stated trigger, closed again afterwards, and never latched on.

WHY THE TICKET IS INSERTED RATHER THAN THE CHEST BEING WATCHED
--------------------------------------------------------------
The obvious design is to watch the vending chest and fire the gate when a ticket leaves it. It
cannot be built at one-item resolution, and the arithmetic says so before any block is placed.

A comparator reads a container as `floor(1 + 14 * fullness)`, where fullness is the mean of
`count / maxStackSize` over ALL slots. A chest has 27 slots, so removing one stackable item moves
fullness by `1 / (64 * 27)` = 0.00058, against the `1/14` = 0.071 needed to move the signal by
one. **The signal does not change at all**, and a gate built on it would look perfect, audit
clean, cost what it should, and never once open. That is this project's oldest failure mode.

Small containers do work - a hopper is 5 slots, so one non-stackable ticket is 0.2 of fullness and
a clean step of ~3 - and a falling-edge detector for one is buildable: a comparator chain carries
an analog level EXACTLY and adds two ticks a stage (measured, in this repo's own simulator), so a
delayed copy subtracted from the live reading gives a pulse on any drop. **It is not shipped**, for
one honest reason: the detector was not built and asserted, only its two building blocks were, and
a mechanism whose contract has not been asserted end to end does not go in. It is recorded in
`unverified` on the box office so nobody re-derives the arithmetic from scratch.

What ships instead loses nothing the player cares about and gains a closed loop: the box office
hands out a ticket, the barrier EATS it, and the collection barrel behind the barrier is where the
box office is restocked from. A rising edge from an empty hopper needs no edge-detection trickery
at all and works with any item at any stack size.

THE MECHANISM, END TO END
-------------------------
Everything mechanical lives in a crawlspace one course under the paving, so a visitor sees a wall,
a door, a slot and a hatch.

    insert hopper (h=1, in the wall face)      the ticket goes in here
      v  hoppers, straight down through the wall's own footprint
    read hopper (crawlspace)  --> collection barrel, under a trapdoor hatch in the paving
      |
    comparator (reads the read hopper: empty 0, one item >= 1)
      v
    HOLD  --  a direct repeater OR'd with a delay lane tapped at every stage
      v
    torch pair (two inversions, because a torch inverts and we need the door OPEN on a HIGH)
      v
    the paving block under the door, strongly powered -> the iron door opens

Four things about it are load-bearing and each was measured rather than assumed:

* **A HOPPER PASSES ITS ITEM ON IN 8 GAME TICKS.** So the comparator's pulse is about four
  redstone ticks and the door would be open for half a second - not long enough to walk through.
  The hold is what turns that into ~1.5s.
* **A DELAY CHAIN DELAYS BOTH EDGES; IT DOES NOT EXTEND A PULSE.** A repeater chain moves a
  4-tick pulse later and leaves it 4 ticks long. What extends it is a chain TAPPED AT EVERY
  STAGE into a shared output line: the taps overlap, so the output is high continuously from the
  first tap to the last. Built as one tap at the end it comes out as two separate pulses with a
  dark gap between them - the door would flicker shut and open again. `_hold` does the taps, and
  `test_the_hold_has_no_gap_in_it` is what keeps them.
* **THE TAPS MUST BE ONE-WAY.** Wired as plain dust the output line feeds back into the delay
  lane, the loop closes, and the whole thing latches ON for ever - a barrier stuck open. Every
  tap is a repeater. That failure was produced twice while prototyping this and both times the
  build looked correct.
* **A TORCH INVERTS, SO THERE ARE TWO OF THEM.** One torch would give a door that stands open at
  rest and shuts when a ticket arrives.

`circuits.pulse` IS NOT USED, and that is deliberate: measured against the simulator it does not
pulse, it delays - a held input produces a held output - so the hold here is built out of
repeaters whose behaviour was measured rather than assumed. See the note in the report.

GEOMETRY - the same convention as `gen/park.py`, stated once because it is invisible in a render:

    at       the barrier's FRONT-LEFT floor corner, in world coordinates
    facing   the direction the front looks out; a visitor arrives from the +facing side
    i        along the frontage      d      into the park (d=0 is the front wall)
    h        courses up from the paving; h=-1 is the paving, h=-2 the crawlspace

Per lane the crawlspace uses three columns and one spare, so lanes sit four apart:

    L = i_lane      the torch pair (d 0 to -3), then the OUT line, running FORWARD
    P = i_lane+1    the direct repeater and the taps - nothing else, see below
    Q = i_lane+2    the ticket hopper column and the collection barrel (d >= 0), the feed run
                    and the delay lane (d < 0)
    i_lane+3        the button's staircase, and otherwise solid ON PURPOSE: at spacing three one
                    lane's delay lane sits next to the next lane's OUT line and they short.

**THE MACHINE RUNS FORWARD, UNDER THE FORECOURT, AND THE TICKET RUNS BACK INTO THE HALL.** That
looks like a stylistic choice and it is not - it is the only arrangement that keeps every hopper
away from every torch. **A HOPPER BESIDE A LIT REDSTONE TORCH IS DISABLED**, so a hopper next to
this circuit's own output torch would stop passing its ticket on the moment the door opened; the
comparator would go on reading it, the door would go on being open, and the barrier would be
latched wide open by a mechanism that simulates perfectly. `mcbuild.circuit` has no model of a
hopper's enabled flag, so nothing in this repo could have caught it - it is designed out instead,
and `test_no_hopper_touches_a_torch_or_powered_dust` is what keeps it that way.

For the same reason column P carries repeaters and NOTHING ELSE: it is adjacent to column L along
its whole length, and L holds two torches (one of them lit at rest), the paving block under the
door (strongly powered whenever the door is open) and the OUT dust line. Dust in P would be
powered by any of them, feed the hold, and latch the lane open.
"""
from __future__ import annotations

from . import park
from .canvas import Canvas
from .vertical import Ctx, World

_STEP = park._STEP
_BACK = park._BACK
# The direction of increasing `i` - the same map `park._Frame` derives its side axis from.
_SIDE = {"east": "north", "west": "south", "north": "west", "south": "east"}

SIGN_WIDTH = park.SIGN_WIDTH        # 15. One source, so the two files cannot disagree.

# The crawlspace, in courses below the paving.
PAVE_H = -1         # the block you walk on
MACH_H = -2         # where the redstone lives
FLOOR_H = -3        # what the redstone stands on

TICKETING = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "ticketgate",
    "facing": "east",
    "land": "midway",
    "title": None,
    "lanes": 2,
    # HOW LONG THE DOOR STAYS OPEN, in delay-lane stages. Each stage is two redstone ticks of
    # hold and two cells of crawlspace, so this is a real trade against the module's footprint.
    # 4 stages measures as ~13 ticks (1.3s) on a hopper's own 4-tick pulse.
    "hold": 4,
    "width": 11,                # boxoffice / queue / lockers
    "depth": 9,
    "windows": 3,               # boxoffice: serving hatches
    "bays": 6,                  # lockers: how many barrels
    "price": "8 grass",         # what a ticket costs, printed on the board
    "lamp": True,               # ridegate: the GO lamp (redstone_lamp is EXPENSIVE - budgeted)
    "min_run": 3,
    "sign": True,
}

# `redstone_lamp` is the only block in the game that lights on a signal, and it is EXPENSIVE on
# this economy. There is no cheap substitute: the nearest cheap colour match is a plank, which is
# a lamp that does not light, and A LIGHT CANNOT BE SUBSTITUTED BY COLOUR. So it is COUNTED into
# the build's `budget` exactly as `gen/casino.py` counts its own, and used two at a time.
BUDGETED = ("redstone_lamp",)


def _split(spec: str):
    name = spec.split("[")[0]
    props = {}
    if "[" in spec and spec.endswith("]"):
        for part in spec[spec.index("[") + 1:-1].split(","):
            k, _, v = part.partition("=")
            props[k.strip()] = v.strip()
    return name, props


# ---------------------------------------------------------------------------- the machine

def _hold(w, f, pal, p, L, P, Q, stages):
    """A pulse EXTENDER: a direct branch OR'd with a delay lane tapped at every stage.

    `IN` is the dust at (Q, d=-4); `OUT` is the dust line in column L from d=-4 forward, which the
    torch pair reads. Everything runs toward the forecourt, i.e. toward decreasing d.

    THE THREE RULES, each of which produced a build that looked right and did not work:

    * the direct branch and the delay lane both START at IN and both END on OUT, and every join
      is a REPEATER - so nothing on OUT can feed back into the lane. Wired with plain dust the
      ring closes and the barrier latches open. That was produced twice while prototyping this;
    * every stage is tapped, not just the last, or the output is two pulses with a dark gap
      between them and the door flickers shut and open again;
    * the direct repeater is delay 2. At delay 1 its pulse ends one tick before the first tap
      arrives, and an input shorter than four ticks opens the door twice instead of once.
    """
    fwd = f.facing
    minus_i = _BACK[_SIDE[f.facing]]
    span = 4 + 2 * stages

    # the OUT line: dust in column L, from the torch pair's block A forward past the last tap
    for d in range(-span, -3):
        w.put(*f.at(L, d, MACH_H), "redstone_wire")

    # IN, and the two one-way branches off it
    w.put(*f.at(Q, -4, MACH_H), "redstone_wire")
    w.put(*f.at(P, -4, MACH_H), "repeater", facing=minus_i, delay="2",
          locked="false", powered="false")                      # direct -> OUT
    w.put(*f.at(Q, -5, MACH_H), "repeater", facing=fwd, delay="1",
          locked="false", powered="false")                      # IN -> the delay lane

    taps = []
    for s in range(stages):
        d = -(6 + 2 * s)
        w.put(*f.at(Q, d, MACH_H), "redstone_wire")              # the stage's dust
        if s + 1 < stages:
            w.put(*f.at(Q, d - 1, MACH_H), "repeater", facing=fwd, delay="1",
                  locked="false", powered="false")
        w.put(*f.at(P, d, MACH_H), "repeater", facing=minus_i, delay="1",
              locked="false", powered="false")                   # the TAP, one-way onto OUT
        taps.append(d)
    return taps


def _torch_pair(w, f, pal, L):
    """Two inversions, ending on the paving block the door stands on.

    A torch is OFF when its support is powered, so ONE of them gives a door that stands open at
    rest and shuts when a ticket arrives. Two give a door that opens on a HIGH. The last torch
    drives the block ABOVE it strongly, and that block is the paving under the door - which is why
    none of this is visible from the lane, and why no dust ever has to climb out of the
    crawlspace. A dust staircase up to the door would need a hole in the paving to climb through.
    """
    back = f.back
    w.put(*f.at(L, -1, MACH_H), pal["trim"])                     # B: T1's support
    w.put(*f.at(L, -3, MACH_H), pal["trim"])                     # A: T0's support
    w.put(*f.at(L, -2, MACH_H), "redstone_wall_torch", facing=back, lit="true")   # T0, on A
    w.put(*f.at(L, 0, MACH_H), "redstone_wall_torch", facing=back, lit="true")    # T1, on B


def _hopper_slot(w, f, pal, Q, R):
    """The ticket slot: a hopper you can reach, a drop through the wall, a barrel and a hatch.

    THE TICKET GOES BACKWARD INTO THE HALL AND THE SIGNAL GOES FORWARD UNDER THE FORECOURT, so
    the hopper chain never comes near the torch pair. See the module docstring: a hopper beside a
    lit torch is a DISABLED hopper, and a disabled read hopper is a barrier latched open.

    The comparator reads the bottom hopper. Empty is 0 and one ticket of any kind is at least 1 -
    which is the whole reason the insert side needs no edge detector and works with any item at
    any stack size.
    """
    fwd, back = f.facing, f.back
    for h in (1, 0, PAVE_H):
        w.put(*f.at(Q, 0, h), "hopper", facing="down", enabled="true")
    w.put(*f.at(Q, 0, MACH_H), "hopper", facing=back, enabled="true")     # the READ hopper
    w.put(*f.at(Q, 1, MACH_H), "hopper", facing=back, enabled="true")
    w.put(*f.at(Q, 2, MACH_H), "barrel", facing="up", open="false")       # collection
    # THE HATCH. A barrel that cannot be emptied fills after 27 tickets and the lane jams, so the
    # paving over it is a trapdoor - walkable shut, and open it to reach the barrel below.
    w.put(*f.at(Q, 2, PAVE_H), f"{pal['wood']}_trapdoor", facing=fwd, half="bottom",
          open="false", powered="false", waterlogged="false")
    # the comparator, and the short feed run to IN
    w.put(*f.at(Q, -1, MACH_H), "comparator", facing=fwd, mode="compare", powered="false")
    for d in (-2, -3):
        w.put(*f.at(Q, d, MACH_H), "redstone_wire")
    return f.at(Q, 0, MACH_H)


def _button_slot(w, f, pal, Q, R):
    """The other trigger: a button on the wall, and a dust staircase down inside it.

    A BUTTON, NOT A PRESSURE PLATE, and the reason is the descent. A plate only weakly powers the
    block under it, and weak power cannot drive dust - so a plate needs dust beside it in the
    paving, out in the open where people walk. A button STRONGLY powers the block it is fixed to,
    and a strongly powered block passes 15 to dust on the far side of it, inside the wall.

    Each step down needs an AIR cell over the lower dust or the signal simply does not descend,
    and every one of those cells is inside the wall's own two-deep footprint where nobody sees it.

    THE STAIRCASE AVOIDS TWO COLUMNS AND ONE COURSE, and the second was found by simulation after
    the build looked finished. Column P is adjacent to the torch pair. And the step at (R, d=0)
    in the PAVING course sat directly beside the NEXT lane's door paving - the one block in a lane
    that is strongly powered whenever that door is open - so opening lane two opened lane one as
    well. Every lane checked out on its own; nothing but running two of them together showed it.
    """
    fwd = f.facing
    w.put(*f.at(Q, -1, 1), "stone_button", face="wall", facing=fwd, powered="false")
    steps = [(Q, 1, 1), (R, 1, 0), (Q, 1, PAVE_H), (Q, 0, MACH_H)]
    for (i, d, h) in steps:
        w.put(*f.at(i, d, h), "redstone_wire")
    for (i, d, h) in steps[1:]:
        w.put(*f.at(i, d, h + 1), "air")            # the headroom the descent needs
    for d in (-1, -2, -3):
        w.put(*f.at(Q, d, MACH_H), "redstone_wire")
    return f.at(Q, -1, 1)


def _barrier(w: World, p: dict, ctx, trigger: str, lamp: bool = False) -> dict:
    """The gated lanes, the machine under them, and the wall they are cut into.

    One machine per lane and no bus between them: two lanes must open independently, and a shared
    line would also put one lane's delay lane next to the next lane's output. Independent lanes
    cost a spare column each and remove a whole class of coupling.
    """
    f = park._Frame(p)
    pal = park.LANDS[p["land"]]
    lanes = max(1, int(p["lanes"]))
    stages = max(2, min(6, int(p["hold"])))
    width = 4 * lanes + 1
    lane_i = [1 + 4 * k for k in range(lanes)]
    span = 4 + 2 * stages                    # the last tap sits at d = -span
    fore = span + 2                          # how far FORWARD the forecourt and machine reach
    height = 5

    # PAVING AND CRAWLSPACE. A skyblock plot is void, so the module brings its own ground - and
    # the machine needs a floor under every cell of dust as well as a lid over it. The forecourt
    # is the machine's roof, which is why it is as deep as it is.
    for i in range(-1, width + 1):
        for d in range(-fore, 5):
            w.put(*f.at(i, d, FLOOR_H), pal["ground"])
            w.put(*f.at(i, d, PAVE_H), pal["ground"] if 0 <= d <= 1 else pal["path"])

    # THE WALL IS TWO DEEP, so you pass THROUGH the barrier rather than past a facade - and so the
    # button's staircase has masonry to hide in. The lane openings are LEFT EMPTY by the loop and
    # never punched afterwards: repainting cells that already exist is how the void tower's
    # crenellations shipped as a plain drum with nothing about the code looking wrong.
    doors = set(lane_i)
    for i in range(width):
        for d in (0, 1):
            for h in range(height):
                if i in doors and h < 2:
                    continue
                pier = i in doors or (i - 1) in doors or (i + 1) in doors
                w.put(*f.at(i, d, h), pal["trim"] if h in (0, height - 1) else
                      (pal["post"] if pier and h == 2 else pal["wall"]))

    # THE DOORS. Two halves, because a door is two blocks and the game will not load half of one.
    for i in lane_i:
        for (h, half) in ((0, "lower"), (1, "upper")):
            w.put(*f.at(i, 0, h), "iron_door", facing=f.facing, half=half, hinge="left",
                  open="false", powered="false")

    # the machine, per lane
    slots = []
    for i in lane_i:
        L, P, Q, R = i, i + 1, i + 2, i + 3
        _torch_pair(w, f, pal, L)
        if trigger == "hopper":
            slots.append(_hopper_slot(w, f, pal, Q, R))
        else:
            slots.append(_button_slot(w, f, pal, Q, R))
        _hold(w, f, pal, p, L, P, Q, stages)

    # A ROOF over the wall, and a lintel band so the openings read as an arcade.
    for i in range(width):
        for d in (0, 1):
            w.put(*f.at(i, d, height), pal["trim"])
    park._cornice(w, f, pal, width, 2, height, int(p["min_run"]))
    for i in (0, width - 1):
        park._hang_light(w, f, pal, i, -1, height - 2)

    # THE LAMP, on the ridegate only. It is the ONE expensive block here and it is budgeted, not
    # smuggled: there is no cheap block that lights on a signal.
    lamps = []
    if lamp:
        for i in lane_i:
            # **SET INTO THE FORECOURT PAVING, OVER THE OUT LINE.** Two placements were tried and
            # simulated before this one, and both were wrong in ways only simulation shows:
            #   - over the doorway at h=2 it touches nothing that is ever powered. The only
            #     strongly powered block in a lane is the paving UNDER the door, and a lamp two
            #     courses above it is not adjacent to anything. It could never have lit;
            #   - beside the door at d=-1 it is LIT AT REST, because T0 - the torch that is lit
            #     when the barrier is CLOSED - strongly powers the paving block above itself, and
            #     that block is next door. A GO lamp that says GO at rest is worse than none.
            # Over the OUT dust it is dark at rest and lit for exactly the hold, which is what a
            # lane being open means.
            w.put(*f.at(i, -4, PAVE_H), "redstone_lamp", lit="false")
            lamps.append(list(f.at(i, -4, PAVE_H)))

    return {"width": width, "depth": 2, "height": height, "lanes": lanes, "stages": stages,
            "lane_i": lane_i, "span": span, "fore": fore,
            "doors": [list(f.at(i, 0, 0)) for i in lane_i],
            "slots": [list(s) for s in slots],
            "lamps": lamps}


# ---------------------------------------------------------------------------- the kinds

def _ticketgate(w: World, p: dict, ctx) -> dict:
    """The barrier that eats a ticket.

    CONTRACT, asserted by simulation in `tests/test_ticketing.py`:
      * at rest, with every hopper empty, the door is UNPOWERED and nothing else is driven;
      * an item in a lane's read hopper powers that lane's door within a few ticks;
      * the door stays powered continuously - no gap - for about `2*hold + 5` redstone ticks
        after the hopper passes the item on, and then CLOSES;
      * a second ticket opens it again; nothing latches.
    """
    f = park._Frame(p)
    pal = park.LANDS[p["land"]]
    meta = _barrier(w, p, ctx, trigger="hopper")
    title = str(p.get("title") or "PARK ENTRY").upper()[:SIGN_WIDTH]
    park._sign(w, f, pal, meta["lane_i"][0] - 1, -1, 3, f.facing,
               [title, "INSERT TICKET", "in the slot", "one per person"])
    park._sign(w, f, pal, meta["lane_i"][-1] + 1, -1, 3, f.facing,
               ["TICKET BARRIER", "slot beside you", "door opens", "keep left"])
    return {**meta, "kind": "ticketing/ticketgate",
            "inputs": [list(s) for s in meta["slots"]],
            "outputs": meta["doors"],
            "contract": ("a ticket in the slot opens that lane's door for about "
                         f"{2 * meta['stages'] + 5} redstone ticks and it closes by itself; "
                         "the ticket falls through to the collection barrel behind"),
            "hazards": ["an item LEFT in a read hopper holds that lane open until it is removed - "
                        "the comparator reads the hopper continuously. The hopper drains into the "
                        "barrel by itself, so this only happens if the barrel is full."],
            "unverified": [
                "the hopper's own 8-game-tick transfer is an ENTITY behaviour and this simulator "
                "has none: the length of the comparator's pulse is the game's number, not ours. "
                "The circuit is asserted for input pulses of 2 to 8 redstone ticks, which brackets "
                "it."]}


def _turnstile(w: World, p: dict, ctx) -> dict:
    """The same barrier, opened by a button. The exit and staff lanes, where no ticket is owed.

    CONTRACT: identical to `ticketgate` with the button as the trigger - closed at rest, open on
    a press, closed again afterwards, never latched.
    """
    f = park._Frame(p)
    pal = park.LANDS[p["land"]]
    meta = _barrier(w, p, ctx, trigger="button")
    title = str(p.get("title") or "WAY OUT").upper()[:SIGN_WIDTH]
    park._sign(w, f, pal, meta["lane_i"][0] - 1, -1, 3, f.facing,
               [title, "PRESS TO OPEN", "no ticket", "needed"])
    return {**meta, "kind": "ticketing/turnstile",
            "inputs": [list(s) for s in meta["slots"]],
            "outputs": meta["doors"],
            "contract": ("a press opens that lane's door for about "
                         f"{2 * meta['stages'] + 5} redstone ticks and it closes by itself"),
            "unverified": []}


def _ridegate(w: World, p: dict, ctx) -> dict:
    """A ride's own entrance: one or two lanes, a button, and a lamp that says GO.

    THE LAMP IS DRIVEN BY THE DOOR'S OWN POWER, not by a second circuit. A GO lamp on its own
    wiring is a lamp that can disagree with the door, which is worse than no lamp at all.
    """
    f = park._Frame(p)
    pal = park.LANDS[p["land"]]
    p = {**p, "lanes": max(1, min(2, int(p["lanes"])))}
    meta = _barrier(w, p, ctx, trigger="button", lamp=bool(p.get("lamp", True)))
    title = str(p.get("title") or "RIDE ENTRY").upper()[:SIGN_WIDTH]
    park._sign(w, f, pal, meta["lane_i"][0] - 1, -1, 3, f.facing,
               [title, "PRESS TO ENTER", "lamp = open", "mind the step"])
    return {**meta, "kind": "ticketing/ridegate",
            "inputs": [list(s) for s in meta["slots"]],
            "outputs": meta["doors"],
            "budget": {"redstone_lamp": len(meta["lamps"])},
            "contract": ("a press opens the lane for about "
                         f"{2 * meta['stages'] + 5} redstone ticks; the lamp over the lane is "
                         "lit exactly while the door is open, because it reads the same block"),
            "unverified": []}


def _boxoffice(w: World, p: dict, ctx) -> dict:
    """The vending hall: a counter, serving hatches, ticket chests, and the price in GRASS.

    NO MECHANISM. The module docstring has the arithmetic: a 27-slot chest cannot be read at
    one-item resolution, so a gate driven off the withdrawal would never fire. The chests here
    are stock, the barrier is what reads the ticket, and the loop closes because the barrier's
    collection barrels are what this counter is restocked from.
    """
    f = park._Frame(p)
    pal = park.LANDS[p["land"]]
    width = max(9, int(p["width"]))
    depth = max(7, int(p["depth"]))
    height = 6
    windows = max(1, min((width - 3) // 2, int(p["windows"])))

    park._pad(w, f, pal, width, depth, margin=1)

    # THE FRONT IS A COUNTER, NOT A WALL. A hall you cannot see into is a shed; the casino's
    # eighteen sealed grey cubes are the failure being avoided.
    win_i = [width // 2 + (k - windows // 2) * 2 for k in range(windows)]
    for i in range(width):
        for d in range(depth):
            edge = i in (0, width - 1) or d in (0, depth - 1)
            if not edge:
                continue
            for h in range(height):
                if d == 0 and i in win_i and h in (2, 3):
                    continue                       # the serving hatch, left empty by the loop
                corner = i in (0, width - 1) and d in (0, depth - 1)
                w.put(*f.at(i, d, h), pal["post"] if corner else
                      (pal["trim"] if h in (0, height - 1) else pal["wall"]))

    # the counter: a top slab along the inside of the front wall, and the chests behind it
    chests = []
    for i in range(1, width - 1):
        w.put(*f.at(i, 1, 0), pal["trim"])
        w.put(*f.at(i, 1, 1), pal["slab"], type="top", waterlogged="false")
    for i in win_i:
        # A CHEST NEEDS A CLEAR CELL ABOVE IT OR IT CANNOT BE OPENED. The counter slab is one
        # column forward of the chests for exactly that reason.
        w.put(*f.at(i, 2, 0), "chest", facing=f.facing, type="single", waterlogged="false")
        chests.append(list(f.at(i, 2, 0)))

    # roof: a flat lid with a trim edge, because a hall has a ceiling
    for i in range(-1, width + 1):
        for d in range(-1, depth + 1):
            w.put(*f.at(i, d, height), pal["canopy"][0] if (i + d) % 2 == 0 else pal["canopy"][1])
    park._cornice(w, f, pal, width, depth, height, int(p["min_run"]))
    for i in (1, width - 2):
        park._hang_light(w, f, pal, i, 2, height - 2)

    # THE PRICE BOARD, and it names the currency. Fifteen characters is the line.
    title = str(p.get("title") or "BOX OFFICE").upper()[:SIGN_WIDTH]
    price = str(p.get("price") or "8 grass")[:SIGN_WIDTH]
    signed = park._sign(w, f, pal, width // 2, -1, height - 1, f.facing,
                        [title, "TICKETS", price, "one per person"])
    for i in win_i:
        park._sign(w, f, pal, i, -1, 4, f.facing, ["TICKETS", price, "", ""])

    # A DOOR AT THE BACK, so the staff side is a room somebody can get into.
    for h in range(2):
        w.put(*f.at(width // 2, depth - 1, h), "air")
    return {"kind": "ticketing/boxoffice", "width": width, "depth": depth, "height": height,
            "windows": windows, "chests": chests, "signed": signed,
            "contract": "a hall you buy a ticket in: a counter you can see over, a chest of "
                        "tickets at every hatch, and the price in grass on the board",
            "unverified": [
                "NOTHING HERE CARRIES A SIGNAL, so there is nothing to verify - which is the "
                "decision. Watching the chest itself cannot work: a comparator reads "
                "floor(1 + 14 * fullness) and a 27-slot chest moves 1/(64*27) per stackable "
                "item against the 1/14 needed, so the signal never changes. A 5-slot hopper of "
                "non-stackable tickets does step (~3 a ticket) and a delayed-copy detector for "
                "one is buildable - a comparator chain carries an analog level exactly and adds "
                "two ticks a stage, both measured here - but it was not built and asserted end "
                "to end, so it does not ship."]}


def _queue(w: World, p: dict, ctx) -> dict:
    """A switchback queue: rails folded back on themselves, a canopy, and two ends.

    Architecture only, so there is no circuit contract - but there IS a contract, and it is the
    one a queue can fail: ONE CONNECTED WALK, an entrance at one end and an exit at the other,
    and no dead end. A switchback whose last leg is closed is a pen.
    """
    f = park._Frame(p)
    pal = park.LANDS[p["land"]]
    width = max(9, int(p["width"]))
    depth = max(7, int(p["depth"]))

    park._pad(w, f, pal, width, depth, margin=1, block=pal["path"])

    # THE RAILS. Each leg leaves a gap at the opposite end, so the walk folds instead of stopping.
    legs = 0
    for k, d in enumerate(range(1, depth - 1, 2)):
        near = k % 2 == 0
        for i in range(width):
            # the gap: the end the walk turns at
            if near and i >= width - 1:
                continue
            if not near and i <= 0:
                continue
            w.put(*f.at(i, d, 0), pal["fence"], north="false", south="false",
                  east="false", west="false", waterlogged="false")
        legs += 1

    # THE CANOPY over the back half - shade is what makes a queue read as a queue rather than as
    # a fenced field, and it is two colours alternating for the same reason a stall's is.
    a, b = pal["canopy"]
    for i in range(-1, width + 1):
        for d in range(depth // 2, depth + 1):
            w.put(*f.at(i, d, 4), a if i % 2 == 0 else b)
    for i in (-1, width):
        for d in (depth // 2, depth):
            for h in range(4):
                w.put(*f.at(i, d, h), pal["post"])
    for i in (-1, width):
        for d in (depth // 2, depth):
            park._hang_light(w, f, pal, i, d, 3)

    title = str(p.get("title") or "QUEUE HERE").upper()[:SIGN_WIDTH]
    # THE SIGN HANGS ON A POST THAT EXISTS. `_sign` refuses one that does not, and a refused sign
    # is a sign that silently is not there - this project's most-repeated failure shape.
    park._sign(w, f, pal, -1, depth // 2 - 1, 2, f.facing,
               [title, "wait from here", "", "keep left"])
    park._sign(w, f, pal, width, depth - 1, 2, f.facing, ["THIS WAY", "to the gate", "", ""])
    return {"kind": "ticketing/queue", "width": width, "depth": depth, "legs": legs,
            "contract": "a switchback line: one entrance, one exit at the far end, every leg "
                        "open at the end it turns at, and a canopy over the back half",
            "unverified": []}


def _lockers(w: World, p: dict, ctx) -> dict:
    """A bank of barrels in a shelter, numbered.

    RULE 10 IS THE WHOLE DESIGN CONSTRAINT: leave about three blocks of working room around
    anything you use. A locker wall you cannot stand in front of is a wall of decoration, so the
    shelter is deep enough to open a barrel and walk past somebody doing the same.
    """
    f = park._Frame(p)
    pal = park.LANDS[p["land"]]
    bays = max(2, min(12, int(p["bays"])))
    width = bays + 2
    depth = max(4, int(p["depth"]))          # >= 4: barrel, standing room, room to pass
    height = 5

    park._pad(w, f, pal, width, depth, margin=1)

    # the back wall carries the barrels; the sides are posts, so the shelter is open-fronted
    for i in range(width):
        for h in range(height):
            w.put(*f.at(i, depth - 1, h), pal["wall"] if h < height - 1 else pal["trim"])
    for d in range(depth):
        for h in range(height):
            w.put(*f.at(0, d, h), pal["post"])
            w.put(*f.at(width - 1, d, h), pal["post"])
    for i in range(-1, width + 1):
        for d in range(-1, depth + 1):
            w.put(*f.at(i, d, height), pal["canopy"][0] if (i + d) % 2 == 0 else pal["canopy"][1])

    # A BARREL OPENS WITH A BLOCK OVER IT, WHICH IS WHY IT IS A BARREL AND NOT A CHEST. The whole
    # point of a locker bank is two courses of them, and a chest wall would need a clear cell over
    # every upper chest.
    lockers = []
    for k in range(bays):
        i = k + 1
        for h in (1, 2):
            w.put(*f.at(i, depth - 2, h), "barrel", facing=f.facing, open="false")
            lockers.append(list(f.at(i, depth - 2, h)))
        w.put(*f.at(i, depth - 2, 0), pal["trim"])
        w.put(*f.at(i, depth - 2, 3), pal["trim"])

    # numbers, one sign per pair - a locker bank with no numbers is a wall of barrels
    for k in range(bays):
        park._sign(w, f, pal, k + 1, depth - 3, 3, f.facing,
                   [f"LOCKER {k + 1}", "", "", ""])
    park._hang_light(w, f, pal, width // 2, 1, height - 2)
    # THE FASCIA. An open-fronted shelter has no wall to hang a name board on, and `_sign` REFUSES
    # a sign with nothing behind it - which is silent, and is this project's most-repeated failure
    # shape. The stall in `gen/park.py` grew a fascia for exactly this reason.
    for i in range(width):
        w.put(*f.at(i, 0, height - 1), pal["trim"])
    title = str(p.get("title") or "LOCKERS").upper()[:SIGN_WIDTH]
    park._sign(w, f, pal, width // 2, -1, height - 1, f.facing,
               [title, "leave bags here", "", "not staffed"])
    return {"kind": "ticketing/lockers", "width": width, "depth": depth, "bays": bays,
            "lockers": lockers,
            "contract": f"{bays} numbered locker bays, two barrels each, with {depth - 2} "
                        f"clear courses of standing room in front of them",
            "unverified": []}


BUILDERS = {
    "boxoffice": _boxoffice,
    "queue": _queue,
    "ticketgate": _ticketgate,
    "turnstile": _turnstile,
    "ridegate": _ridegate,
    "lockers": _lockers,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**TICKETING, **cfg}
    if not p.get("at"):
        raise ValueError("ticketing needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown ticketing kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in park.LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(park.LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    # `_button_slot` carves headroom for its staircase by writing "air", which a World has no
    # concept of - it is a sparse buffer, so an air cell is a cell that is NOT THERE.
    for pos, (name, _pr) in list(w.cells.items()):
        if name == "air":
            del w.cells[pos]

    budget = {}
    for pos, (name, _pr) in w.cells.items():
        if name in BUDGETED:
            budget[name] = budget.get(name, 0) + 1
    return w.canvas({
        "kind": meta.get("kind", f"ticketing/{p['kind']}"),
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        "budget": budget,
        **{k: v for k, v in meta.items()
           if k not in ("contract", "unverified", "kind", "budget")},
    })
