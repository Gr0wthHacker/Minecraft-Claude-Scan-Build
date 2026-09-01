"""THE SHOW, AND SOMEWHERE TO SIT WHILE IT HAPPENS.

`gen/park.py` builds the attractions and `gen/streetfurniture.py` dresses the ground between
them. Both leave one thing out, and it is the thing that decides whether anybody stays: a park
keeps people because something HAPPENS in it at a stated time, and because there is a pleasant
place to be between rides. Five kinds, and every one of them is somewhere a visitor DOES
something rather than a shape they walk past:

    fireworks         a dispenser battery fired in SEQUENCE by a clock, with a lever to start it
    bandstand_show    a stage with a bell you can ring - the affordable instrument, see below
    foodcourt         counters, barrels, tables with real seats, an awning, bins and light
    viewing           a stepped terrace with a MEASURED sightline to the launch point
    leaderboard       a wall of lecterns: a reason to come back

GEOMETRY is `park`'s exactly, imported rather than restated - two modules each holding a copy of
"which way does a stair lean" is how one facing bug becomes two:

    at       the structure's FRONT-LEFT floor corner, in world coordinates
    facing   the direction the FRONT looks out - a visitor stands in the +facing direction
    i        runs along the frontage; d runs from the front INTO the piece; h counts courses up
    h=-1     the pad the piece stands on. THE PLOT IS VOID, so every kind carries its own.

**NOTHING THAT CARRIES A SIGNAL SHIPS UNVERIFIED.** `tests/test_spectacle.py` builds the firework
battery, wraps it in `mcbuild.circuit` and asserts its contract by simulation - at rest, in
sequence, and that it STOPS. Two finished casino games were deleted from this repo for failing
exactly that bar, and the one thing this project's audit, BOM and renders all pass happily is a
machine that does nothing. Where the mechanism could not be judged, the NON-MECHANICAL version is
built and the gap is recorded in `unverified` rather than smuggled through.

**THE SOUND QUESTION, MEASURED RATHER THAN ASSUMED.** The brief's guess was that a jukebox is the
cheap alternative to note blocks. It is not, on this economy:

    note_block      palette.tier -> EXPENSIVE      (and it needs redstone per block)
    jukebox         palette.tier -> EXPENSIVE      (a diamond)
    bell            palette.tier -> CHEAP          rings on right-click, no wiring at all

So the bandstand's instrument is a **bell**, which is also the block `gen/campanile.py` already
puts on this island. Note blocks and a jukebox are both available as options, both default OFF,
and both are COUNTED INTO `budget` when asked for - the casino's rule, because a plan that says
"a bandstand" rather than "5 note blocks you do not own" is not a plan. A bell needs no circuit,
so there is nothing here to verify and nothing pretending to be verified.

**FIRE.** Checked rather than assumed. In vanilla, fire spreads only from `fire`, `soul_fire` and
lava; a campfire or a candle never ignites its neighbour. This module therefore places NO ignition
source at all - no fire, no lava, no TNT, no flint - and `_IGNITES` is asserted empty over every
kind. The rule that IS load-bearing is the other one: **a firework rocket that cannot leave the
muzzle detonates at the muzzle**, so every dispenser's column is kept open for `clearance` courses
and no flammable block is allowed to touch a dispenser. Both are asserted. The campfire hearth in
the food court keeps a flammable-free ring anyway, belt and braces, because the block a player
eventually brings to a cook fire is flint and steel.

MATERIALS. Everything structural comes from `park.LANDS[land]`; all three lands' `ground` is
non-flammable (stone brick / cobble / polished blackstone), which is what makes them safe launch
pads. The extras were each checked against `blocks.exists`, `blocks.spendable` and `palette.tier`
before being written down:

    dispenser · lever · repeater · redstone_wire · redstone_wall_torch   cheap, and 1.19
    barrel · smoker · composter · cauldron · lectern · bell · campfire   cheap, and 1.19

**AND `item_frame` IS NOT A BLOCK.** `blocks.exists("item_frame")` is False - it is an entity, as
are `armor_stand` and `painting` - so the leaderboard the brief describes as "lecterns and item
frames" is built from lecterns, signs and a painted board. That is recorded in `unverified` rather
than left as a silently missing feature.
"""
from __future__ import annotations

from .canvas import Canvas
from .vertical import Ctx, World
from .park import LANDS, SIGN_WIDTH, _STEP, _Frame, _pad, _cornice, _trim_run
from .streetfurniture import MIN_RUN, _Plaques, _stair, _slab, _i_dir, _fence_props

# ---------------------------------------------------------------------------- safety

# NEVER PLACED. Everything here spreads fire or explodes; `test_spectacle` asserts that not one
# cell of any kind is one of these, so the rule cannot be quietly relaxed by a later pass.
_IGNITES = {"fire", "soul_fire", "lava", "flowing_lava", "tnt", "lit_tnt"}

# Lit blocks that do NOT spread fire in vanilla but that a player brings flint and steel to.
_HOT = {"campfire", "soul_campfire", "candle", "white_candle", "torch", "wall_torch"}

_WOODS = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "bamboo")


def flammable(name: str) -> bool:
    """Would this burn. Kept as one function because three call sites with three lists is how a
    safety rule stops being a rule."""
    n = str(name).split(":")[-1].split("[")[0]
    if n.endswith(("_wool", "_carpet", "_leaves")):
        return True
    if n in ("bookshelf", "hay_block", "vine", "scaffolding", "ladder", "target"):
        return True
    return any(n.startswith(wd + "_") or n == wd for wd in _WOODS)


SPECTACLE = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "fireworks",
    "facing": "east",
    "land": "midway",
    "title": None,
    "lines": None,
    "when": "9pm nightly",      # WHAT TIME THE SHOW IS. A show nobody is told about is a machine.
    "min_run": MIN_RUN,
    "sign": True,

    # --- fireworks
    "battery": 7,               # how many dispensers fire in sequence
    "stagger": 2,               # repeater delay between shots, in redstone ticks (1-4)
    "period": 4,                # each of the clock's two repeaters (2-4); the cycle is ~4*period
    "clearance": 10,            # courses of open sky above every muzzle - see the docstring
    "stand": True,              # a two-row stand in front of the pad, for the casual watcher

    # --- viewing
    "tiers": 4,
    "width": 15,
    "aim": None,                # world (x, y, z) of the launch point; `fireworks` reports it

    # --- bandstand_show
    "notes": 0,                 # note blocks. EXPENSIVE here, so opt-in and budgeted.
    "jukebox": False,           # also EXPENSIVE, and needs discs nobody can craft
    "bells": 1,

    # --- foodcourt / leaderboard
    "stalls": 4,
    "tables": 3,
    "boards": 5,
}
DEFAULTS = SPECTACLE

# Every block a player right-clicks to USE. Rule 10: about three blocks of working room in front
# of one, or you cannot stand, open it and walk past. Recorded on the build so the test can check
# the room actually exists rather than trusting a comment.
_SERVICE = ("barrel", "smoker", "lectern", "composter", "cauldron", "campfire", "jukebox", "bell")

_WORK_ROOM = 3


def _serve(into, f, i, d, h, use, facing=None):
    """Record a block a player uses, and REFUSE a name the work-room rule does not know.

    The rule is only worth anything if every used block goes through it, and the way that stops
    being true is a new fixture recorded under a name nothing checks - which reads as "no
    serving blocks here" rather than as an error. `_SERVICE` is the list, and it is asserted.
    """
    if use not in _SERVICE:
        raise ValueError(f"{use!r} is not in _SERVICE, so nothing would check its working room")
    into.append({"pos": list(f.at(i, d, h)), "facing": facing, "use": use})
    return into[-1]


# ---------------------------------------------------------------------------- small helpers

def _put(w, f, i, d, h, block, **props):
    w.put(*f.at(i, d, h), block, **props)


def _fill(w, f, i0, i1, d0, d1, h, block, **props):
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            _put(w, f, i, d, h, block, **props)
            n += 1
    return n


def _column(w, f, i, d, h0, h1, block):
    for h in range(h0, h1 + 1):
        _put(w, f, i, d, h, block)


def _lamp_under(w, f, pal, i, d, h):
    """A lantern hangs from a FULL block, and the block has to be there ALREADY.

    `park._hang_light` places its own ceiling; under a canopy that would repaint a stripe. This
    one refuses instead of inventing one, because a lantern hanging from air is the lowland's own
    recorded bug and it draws identically to a correct one.
    """
    if not w.has(*f.at(i, d, h + 1)):
        return False
    _put(w, f, i, d, h, pal["light"], hanging="true", waterlogged="false")
    return True


def _hearth(w, f, pal, i, d, h):
    """A cook fire, only where nothing next to it would burn.

    Vanilla campfires do not spread fire, so this is belt and braces - but a lit fire under a wool
    awning is the one place on a fairground somebody eventually applies flint and steel, and the
    check costs six lookups.
    """
    block = "campfire"
    assert block in _HOT, "a lit fixture must be declared, or the ring check means nothing"
    for (di, dd, dh) in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        nb = w.name(*f.at(i + di, d + dd, h + dh))
        if nb and flammable(nb):
            return False
    _put(w, f, i, d, h, block, facing=f.facing, lit="true",
         signal_fire="false", waterlogged="false")
    return True


def _terrace(w, f, pal, i0, i1, d_first, step, tiers, seat_back):
    """Stepped seating: a seat row and a walkway per tier, each one course higher than the last.

    `step` is which way the tiers CLIMB - +1 for a terrace whose show is in front of it, -1 for a
    stand built on the far side of a pad. One helper for both, because a grandstand built twice is
    a grandstand whose two copies disagree the first time one of them is fixed.

    Returns the seat cells so a caller can measure a sightline off the ones a person's eyes are
    actually at, rather than off the bounding box.
    """
    seats = []
    for k in range(tiers):
        d_seat = d_first + step * (2 * k)
        d_walk = d_first + step * (2 * k + 1)
        for i in range(i0, i1 + 1):
            # The riser. Down to the pad course every time, so a tier is solid rather than a
            # shelf: this is what makes the whole terrace one connected piece on a void plot.
            for hh in range(-1, k):
                _put(w, f, i, d_seat, hh, pal["ground"])
                _put(w, f, i, d_walk, hh, pal["ground"])
            _stair(w, f, i, d_seat, k, pal["stair"], seat_back)
            seats.append((i, d_seat, k))
    return seats


def _railing(w, f, pal, cells, h):
    """A fence run whose connections come from its NEIGHBOURS THAT EXIST.

    With every side false a fence renders as a lone post; with every side true a run grows a nub
    off each end into open air. `streetfurniture._fence_props` already answers this, so the run is
    collected first and the props derived from the finished set.
    """
    have = {(i, d) for (i, d) in cells}
    for (i, d) in cells:
        _put(w, f, i, d, h, pal["fence"], **_fence_props(f, have, i, d))
    return len(cells)


# ---------------------------------------------------------------------------- the firework show

def _clock_cells(w, f, pal, i, d, period):
    """`circuits.clock`, ROTATED into the frame and with a LONGER LOOP - a torch whose own output
    comes back, delayed, and switches it off.

    It is copied rather than called for one reason, stated in `circuits.clock` itself: *"built
    along +Z from `pos`; `facing` is accepted for symmetry ... and does not rotate the footprint
    yet."* A world-axis-fixed clock inside a frame-relative building puts the whole machine at a
    different place for each of the four facings, which is exactly the class of bug this module's
    geometry section exists to prevent. The TOPOLOGY is identical, cell for cell, and the whole
    battery's contract is asserted end to end by simulation - which is a stronger check than the
    primitive's own.

    THE LOOP CLOSES ON THE TORCH'S SUPPORT BLOCK, NOT ON THE TORCH. That is `circuits.clock`'s
    first recorded bug: a torch reads the block it is ATTACHED to and nothing else, and pointing
    the return repeater at the torch's own cell emits four tidy blocks that never tick once.

    **THE LOOP CARRIES TWO REPEATERS, NOT ONE, AND THAT IS THE WHOLE DISPLAY.** A repeater's delay
    caps at 4, so a single-repeater loop cycles in about 2*(period+1) = 10 ticks - and a seven-gun
    cascade takes longer than that to run, so shot 0 of the next wave overtakes shot 6 of this one
    and the sky reads as noise rather than as a sweep. Two repeaters roughly double the loop -
    2*(2*period + 3) by the model, 25 ticks MEASURED in simulation at the default - which is room
    for the sequence AND a beat of dark between waves. The extra length is folded into +d rather
    than +i so it cannot collide with the battery, and `test_the_sequence_fits_inside_the_cycle`
    measures the real period off the trace rather than trusting the arithmetic in this paragraph.

    Returns the support cell (which is also the kill switch's target) and the loop's tap.
    """
    # THE TORCH IS ATTACHED TO ITS SUPPORT, and an attachment is `pos + OPPOSITE(facing)` - so a
    # torch reached from the support by stepping +d must itself face +d. Written the other way it
    # attaches to thin air and the clock is six tidy blocks that never tick.
    # THE TWO LANES MUST NOT TOUCH. Folded side by side at i+1 and i+2 they are adjacent down
    # their whole length, which is one wire network rather than a loop: the return short-circuits
    # the outbound, the delay disappears and the clock free-runs at a tick. They are separated by
    # an empty lane at i+2, joined only at the cross and at the turn.
    _put(w, f, i, d, 0, pal["ground"])                                    # S, the support
    _put(w, f, i, d + 1, 0, "redstone_wall_torch", facing=f.back, lit="true")
    for dd in (1, 2):
        _put(w, f, i + 1, d + dd, 0, "redstone_wire")                     # out, lit by the torch
    _put(w, f, i + 1, d + 3, 0, "repeater", facing=f.back, delay=str(period))
    for k in range(3):                                                    # the cross at the far end
        _put(w, f, i + 1 + k, d + 4, 0, "redstone_wire")
    for dd in (3, 2, 1, 0):                                               # ...and back round
        _put(w, f, i + 3, d + dd, 0, "redstone_wire")
    _put(w, f, i + 2, d, 0, "redstone_wire")                              # the turn
    _put(w, f, i + 1, d, 0, "repeater", facing=_i_dir(f, -1), delay=str(period))
    return (i, d), (i + 3, d)


def _fireworks(w: World, p: dict, ctx) -> dict:
    """A FIREWORK BATTERY: dispensers fired one after another so it reads as a display.

    **A BANK OF DISPENSERS ON ONE WIRE IS ONE BANG.** Everything interesting about this is the
    SEQUENCE, and the sequence is a repeater delay line: the clock's square wave enters at the
    first tap and each repeater hands the rising edge on `stagger` ticks later, so shot k leaves
    k*stagger ticks after shot 0 and the whole battery re-fires once per clock cycle.

    A dispenser is EDGE-TRIGGERED, which `mcbuild.circuit` models and which is the difference
    between a display and an empty battery: a held signal dispenses once. That is the same
    property the casino's payout rests on, and it is asserted here rather than assumed.

    **THE KILL SWITCH POWERS THE CLOCK'S OWN SUPPORT, WHICH IS WHY "AT REST" IS REALLY AT REST.**
    Gating the output would leave a clock ticking behind a closed gate; forcing the clock's torch
    off leaves every cell downstream genuinely dark, so "nothing is powered" is a fact about the
    build rather than about where you happen to look. The lever runs through ONE inverting torch:
    lever ON releases the support and the show runs, lever OFF holds it down and everything stops.

    THE MUZZLE COLUMN IS KEPT OPEN. A rocket that cannot leave the dispenser detonates at the
    dispenser, so `clearance` courses above every one of them are empty by construction and the
    test measures it - there is no roof over a launch pad, ever.

    CONTRACT: with the lever off nothing is powered and nothing fires; with it on each dispenser
    fires exactly once per cycle, in order along the battery; the cycle repeats; and throwing the
    lever back stops it dead.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    plaque = _Plaques(p.get("sign", True))
    n = max(2, min(12, int(p["battery"])))
    period = max(2, min(4, int(p["period"])))
    clear = max(4, int(p["clearance"]))

    # THE SEQUENCE MUST FIT INSIDE THE CYCLE, and this is the one number that decides whether the
    # display reads at all. Let the cascade take longer than a cycle and shot 0 of the next wave
    # overtakes shot n-1 of this one: measured on a single-repeater clock at stagger 2 with seven
    # guns, the battery fired 5,4,4,4,4,3,3 in sixty ticks and the order on screen is noise rather
    # than a sweep. So the stagger is CLAMPED to what the clock can carry rather than trusted.
    #
    # Every stage costs its delay PLUS a tick to notice, so a two-repeater loop cycles in about
    # 2*(2*period + 3) - 22 at the default, 25 measured - and a hop down the delay line costs
    # `stagger + 1`. The model is deliberately conservative (it under-states the cycle and
    # over-states the span), and `test_the_sequence_fits_inside_the_cycle` measures both off the
    # trace rather than trusting the arithmetic written here.
    cycle = 2 * (2 * period + 3)
    stagger = max(1, min(4, int(p["stagger"])))
    stagger = max(1, min(stagger, (cycle - 2) // max(1, n - 1) - 1))
    span = (stagger + 1) * (n - 1)

    dwire = 5                 # the delay line
    dgun = dwire - 1          # the dispensers, one step toward the audience
    ic = 2                    # the clock, whose loop folds back into +d behind the line
    i0 = 7                    # the battery starts clear of the clock and its start repeater
    width = 2 * n + 8
    depth = 11

    _pad(w, f, pal, width, depth, margin=1)

    along = _i_dir(f, 1)
    # --- the timebase, and the switch that holds it down
    support, tap = _clock_cells(w, f, pal, ic, dwire, period)

    # --- THE KILL SWITCH, WHICH IS WHY "AT REST" IS REALLY AT REST.
    #
    # One inverting torch, standing where its own emission reaches the clock's SUPPORT. Lever ON
    # holds the inverter down and the clock runs; lever OFF lights it, the support stays powered,
    # the clock's torch can never light and every cell downstream is genuinely dark. Gating the
    # OUTPUT instead would leave a clock ticking behind a shut gate, and "nothing is powered"
    # would be a fact about where you looked rather than about the build.
    #
    # NEITHER THE LEVER NOR ITS SUPPORT MAY TOUCH THE CLOCK'S SUPPORT. A lever strongly powers the
    # block it is attached to and emits to all six of its own neighbours, so one placed a cell
    # nearer would power the support directly - the switch would then stop the clock when ON,
    # which is the same build with the meaning inverted and looks identical in every render.
    _put(w, f, ic, dwire - 1, 0, "redstone_wall_torch", facing=f.back, lit="true")
    _put(w, f, ic, dwire - 2, 0, pal["ground"])                                     # its support
    _put(w, f, ic, dwire - 2, 1, "lever", face="floor", facing=f.facing, powered="false")

    # --- THE START REPEATER, AND IT IS NOT DECORATION.
    #
    # A redstone torch is LIT on chunk load and takes two ticks to notice that the kill switch is
    # holding its support down. Wired straight through, that transient is a real rising edge on
    # every tap: the battery fired ONE SHOT every time the chunk loaded, with the lever off, and
    # the only place that shows is the sky. A repeater whose delay outlasts the transient swallows
    # it - the target flips back before the delay expires, so the edge never leaves - which is why
    # `start` is at least 2 and why `period` is floored at 2 so the clock's high phase can still
    # push it through.
    start = max(2, min(4, period))
    _put(w, f, i0 - 1, dwire, 0, "repeater", facing=along, delay=str(start))

    # --- the delay line and the guns
    guns, taps = [], []
    for k in range(n):
        i = i0 + 2 * k
        _put(w, f, i, dwire, 0, "redstone_wire")
        taps.append((i, dwire))
        _put(w, f, i, dgun, 0, "dispenser", facing="up", triggered="false")
        guns.append(f.at(i, dgun, 0))
        if k < n - 1:
            _put(w, f, i + 1, dwire, 0, "repeater", facing=along, delay=str(stagger))

    # --- the control station: a board you can read before you throw the lever. It stops one
    # cell short of the lever's own support, so the sign wall and the switch cannot repaint
    # each other - the void tower's rule that an opening is LEFT EMPTY rather than punched.
    _fill(w, f, -1, ic - 1, dwire - 2, dwire - 2, 0, pal["trim"])
    _fill(w, f, -1, ic - 1, dwire - 2, dwire - 2, 1, pal["wall"])
    _fill(w, f, -1, ic - 1, dwire - 2, dwire - 2, 2, pal["trim"])
    title = str(p.get("title") or "FIREWORKS").upper()[:SIGN_WIDTH]
    plaque(w, f, pal, 0, dwire - 3, 2, f.facing, [title, "", "", ""])
    plaque(w, f, pal, 0, dwire - 3, 1, f.facing,
           ["SHOW", str(p.get("when") or "")[:SIGN_WIDTH], "pull the lever", "stand back"])

    # --- the safety rail. THE PAD IS NOT A PLACE TO STAND; the stand in front of it is.
    ring = [(i, dd) for i in range(-1, width + 1) for dd in (-1, depth)]
    ring += [(ii, dd) for ii in (-1, width) for dd in range(0, depth)]
    _railing(w, f, pal, ring, 0)

    # --- the stand: two rows in front of the pad, on the far side of the rail
    seats = []
    if p.get("stand", True):
        seats = _terrace(w, f, pal, 1, width - 2, -2, -1, 2, f.facing)

    mid = i0 + 2 * ((n - 1) // 2)
    launch = f.at(mid, dgun, 2)
    return {
        "kind": "fireworks", "width": width, "depth": depth, "height": 3,
        "battery": n, "stagger": stagger, "period": period, "clearance": clear,
        "cycle_ticks": cycle, "span_ticks": span, "start_delay": start,
        "inputs": [list(f.at(ic, dwire - 2, 1))],
        "outputs": [list(g) for g in guns],
        "taps": [list(f.at(i, d, 0)) for (i, d) in taps],
        "clock_support": list(f.at(*support, 0)),
        "clock_tap": list(f.at(*tap, 0)),
        "launch": list(launch),
        "muzzles": [list(g) for g in guns],
        "seats": len(seats),
        "seat_cells": [list(f.at(i, d, h)) for (i, d, h) in seats],
        "signs": plaque.got,
        # THE SIMULATOR HAS NO ENTITIES, so it cannot check that a dispenser was loaded. The one
        # thing it can do is say exactly what to put in - the casino's `stock` rule.
        "stock": {"each dispenser": "firework rockets, up to 9 slots x 64 = 576",
                  "battery total": f"{n * 576} rockets to fill it completely"},
        "contract": (f"lever off: nothing powered, nothing fires. lever on: {n} dispensers fire "
                     f"once each per cycle, in order, {stagger} tick(s) apart, repeating about "
                     f"every {cycle} redstone ticks; lever off again stops it"),
        "unverified": ["how a firework LOOKS is a property of the rocket, not of the circuit: "
                       "load the dispensers with the star pattern you want",
                       "rocket flight time is set on the item and is not modelled here"],
    }


# ---------------------------------------------------------------------------- the bandstand

def _bandstand(w: World, p: dict, ctx) -> dict:
    """A STAGE WITH A BELL YOU CAN RING, and a ring of seats to hear it from.

    **THE INSTRUMENT IS CHOSEN BY MEASUREMENT, NOT BY TASTE.** `palette.tier` says `note_block`
    and `jukebox` are both EXPENSIVE on this economy and `bell` is CHEAP; a bell also rings on
    right-click with no wiring, so there is no circuit here to get wrong and none pretending to
    be right. Note blocks and a jukebox are both offered, both default OFF, and both are counted
    into `budget` when asked for.

    A note block only sounds with AIR ABOVE IT, and its instrument comes from the block BELOW -
    derived by the game, exactly as a stair's shape is, so no `instrument` property is written.
    The first is why the rank keeps off the post line: laid a course in front of it, three of the
    note blocks had a column standing on them and made no sound at all, on a build that audits
    clean and costs exactly the same.

    CONTRACT: a raised stage you can walk up onto, a bell hung from a beam within reach of it,
    seating that faces it, and a sign saying when the band plays. Nothing here carries a signal.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    plaque = _Plaques(p.get("sign", True))
    width = depth = 11
    _pad(w, f, pal, width, depth, margin=1)

    # --- the stage: one course up, so it is a stage rather than a patch of floor
    _fill(w, f, 1, width - 2, 1, depth - 2, 0, pal["ground"])
    for i in range(1, width - 1):        # the moulded lip, a real run rather than four singles
        _stair(w, f, i, 0, 0, pal["stair"], f.facing)
    steps = [i for i in range(width // 2 - 1, width // 2 + 2)]
    for i in steps:                      # ...broken by the steps up, which climb TOWARD the stage
        _stair(w, f, i, 0, 0, pal["stair"], f.back)

    # --- eight posts and a roof
    posts = [(i, d) for i in (1, width // 2, width - 2) for d in (1, depth // 2, depth - 2)
             if not (i == width // 2 and d == depth // 2)]
    for (i, d) in posts:
        _column(w, f, i, d, 1, 4, pal["post"])
    a, b = pal["canopy"]
    for i in range(0, width):
        for d in range(0, depth):
            _put(w, f, i, d, 5, a if (i + d) % 2 == 0 else b)
    # the cornice under the eaves - the vocabulary the corpus says we are seven times short of
    band = [(i, d, f.inward(i, d, width, depth)) for i in range(width) for d in range(depth)
            if (i in (0, width - 1) or d in (0, depth - 1)) and f.inward(i, d, width, depth)]
    _trim_run(w, f, pal, band, 4, int(p["min_run"]))
    # THE NAMEPLATE NEEDS A FULL BLOCK BEHIND IT, AND A CORNICE STAIR IS NOT ONE. `park._sign`
    # only asks whether the cell behind is OCCUPIED, so a sign hung on the eaves stair passed the
    # check and would be refused by the game. Three cells of the cornice are overwritten with a
    # solid fascia first - which is what a name board is anyway.
    _fill(w, f, width // 2 - 1, width // 2 + 1, 0, 0, 4, pal["trim"])

    # --- the cupola, and the BELL under the beam rather than inside the cupola: a bell nobody
    # can reach is an ornament, and the stage floor is at h=1, so h=3 is a comfortable ring.
    _fill(w, f, width // 2 - 1, width // 2 + 1, depth // 2 - 1, depth // 2 + 1, 6, pal["trim"])
    _fill(w, f, width // 2, width // 2, depth // 2, depth // 2, 7, pal["accent"])
    _fill(w, f, width // 2 - 1, width // 2 + 1, depth // 2, depth // 2, 4, pal["post"])   # beam
    bells = max(0, min(3, int(p["bells"])))
    hung = []
    for k in range(bells):
        i = width // 2 + (0, -1, 1)[k]
        _put(w, f, i, depth // 2, 3, "bell",
             attachment="ceiling", facing=f.facing, powered="false")
        hung.append(list(f.at(i, depth // 2, 3)))

    # --- the optional, EXPENSIVE extras. Air above a note block, or it makes no sound.
    # THE RANK KEEPS OFF THE POST LINE. Laid at depth-2 it shared d with the back row of posts,
    # so the note blocks at i=1, 5 and 9 had a column standing on them: they audit clean, they
    # cost the same, and they make no sound whatever, which is the exact shape of failure this
    # module exists to refuse.
    d_rank = depth - 3
    notes = max(0, min(12, int(p["notes"])))
    rank = []
    for k in range(notes):
        i = 2 + k
        if i > width - 4:
            break
        _put(w, f, i, d_rank, 1, "note_block", powered="false")
        rank.append(list(f.at(i, d_rank, 1)))
    box = None
    if p.get("jukebox"):
        _put(w, f, width - 3, d_rank, 1, "jukebox", has_record="false")
        box = list(f.at(width - 3, d_rank, 1))

    # --- seating, facing the stage from outside it
    seats = _terrace(w, f, pal, 0, width - 1, -2, -1, 2, f.facing)

    _lamp_under(w, f, pal, 1, 1, 4)
    _lamp_under(w, f, pal, width - 2, 1, 4)
    title = str(p.get("title") or "BANDSTAND").upper()[:SIGN_WIDTH]
    plaque(w, f, pal, width // 2, -1, 4, f.facing,
           [title, str(p.get("when") or "")[:SIGN_WIDTH], "ring the bell", ""])

    # A BELL IS RUNG FROM BELOW, not from in front, so it is recorded with no facing: the
    # work-room rule then asks about the cell ABOVE it, which is the one that must stay solid for
    # it to hang from - so the bell is deliberately NOT in `service`, and the jukebox, which you
    # do walk up to, is.
    service = []
    if box:
        _serve(service, f, width - 3, depth - 3, 1, "jukebox", f.facing)
    return {
        "kind": "bandstand_show", "width": width, "depth": depth, "height": 8,
        "bells": bells, "notes": len(rank), "jukebox": bool(box), "seats": len(seats),
        "seat_cells": [list(f.at(i, d, h)) for (i, d, h) in seats],
        "signs": plaque.got, "service": service,
        "stock": ({"jukebox": "one music disc per tune; discs are not craftable"} if box else {}),
        "contract": ("a stage with a bell within reach of it and seating that faces it; the "
                     "bell rings on right-click and carries no signal at all"),
        "unverified": ["a note block's PITCH is set by right-clicking it in game and its "
                       "instrument by the block under it - neither is a placed property"],
    }


# ---------------------------------------------------------------------------- the food court

def _foodcourt(w: World, p: dict, ctx) -> dict:
    """THE MOST-USED BUILDING IN A REAL PARK, and the one this park did not have.

    **RULE 10 IS THE PLAN, NOT A CHECK ON IT.** Three blocks of working room in front of anything
    a player opens is what decides the depth of this building: counter at the front of the
    servery, a THREE-WIDE staff aisle behind it, and the barrels and smokers against the back
    wall facing that aisle. Written the other way round - barrels tight behind a counter - the
    building measures the same and cannot be worked in, which is exactly the failure a rule
    written as a comment produces.

    Every serving block is recorded in `service` with the direction it faces, so the test can
    walk out three cells and check they are clear rather than trusting this docstring.

    CONTRACT: a served counter with three blocks of staff room behind it, tables with seats that
    have a back and arms, cover overhead, a bin, and light under the awning.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    plaque = _Plaques(p.get("sign", True))
    width = 17
    depth = 13
    _pad(w, f, pal, width, depth, margin=1)

    d_back, d_serve, d_counter = depth - 1, depth - 2, depth - 6

    # --- the servery: back wall, side returns, and a roof over the working half
    _fill(w, f, 0, width - 1, d_back, d_back, 0, pal["wall"])
    _fill(w, f, 0, width - 1, d_back, d_back, 1, pal["wall"])
    _fill(w, f, 0, width - 1, d_back, d_back, 2, pal["wall"])
    _fill(w, f, 0, width - 1, d_back, d_back, 3, pal["trim"])
    # THE SERVICE DOOR IS LEFT EMPTY BY THE WALL LOOP, never punched afterwards. Building the
    # return first and cutting a hole repaints cells that already exist - the void tower's
    # crenellations shipped as a plain drum for exactly this reason, and nothing about the code
    # looked wrong. Without it the servery is sealed and the staff aisle cannot be reached at all.
    door = (0, d_counter + 1)
    for i in (0, width - 1):
        for d in range(d_counter, d_back):
            for h in range(0, 3):
                if (i, d) == door and h < 2:
                    continue
                _put(w, f, i, d, h, pal["wall"])
            _put(w, f, i, d, 3, pal["trim"])
    a, b = pal["canopy"]
    for i in range(0, width):
        for d in range(d_counter, d_back + 1):
            _put(w, f, i, d, 4, a if (i + d) % 2 == 0 else b)

    # --- the serving line, against the back wall and facing the aisle
    service = []
    stalls = max(1, min(6, int(p["stalls"])))
    slots = [2 + k * ((width - 5) // max(1, stalls - 1) if stalls > 1 else 0)
             for k in range(stalls)]
    for k, i in enumerate(slots):
        i = min(i, width - 3)
        if k % 2 == 0:
            _put(w, f, i, d_serve, 0, "barrel", facing=f.facing, open="false")
            _serve(service, f, i, d_serve, 0, "barrel", f.facing)
        else:
            _put(w, f, i, d_serve, 0, "smoker", facing=f.facing, lit="true")
            _serve(service, f, i, d_serve, 0, "smoker", f.facing)
        # THE MENU GOES OVER THE THING IT DESCRIBES, on the back wall, which is solid there.
        plaque(w, f, pal, i, d_serve, 2, f.facing,
               ["MENU", "hot food", "and a drink", "free refills"])

    # one cook fire, and only where nothing next to it would burn
    hearth = _hearth(w, f, pal, 1, d_serve, 0)
    if hearth:
        _serve(service, f, 1, d_serve, 0, "campfire", f.facing)

    # --- the counter: a full course with a slab lip, so it is chest height from the queue side
    for i in range(1, width - 1):
        _put(w, f, i, d_counter, 0, pal["trim"])
        _slab(w, f, i, d_counter, 1, pal["slab"], "bottom")
    # ...and a PIER at each end rather than a gap: a counter that stops short reads as unfinished,
    # and the staff reach the aisle round the outside of the servery, which is where a service
    # door belongs. The pier is a full column so the fascia over it has something to stand on.
    for i in (1, width - 2):
        _put(w, f, i, d_counter, 0, pal["trim"])
        _put(w, f, i, d_counter, 1, pal["wall"])
        _put(w, f, i, d_counter, 2, pal["trim"])

    # THE FASCIA, and the name on it. An open front has no wall to hang a sign from - the stall's
    # own recorded bug in `park._stall` - so the board it hangs on is built first.
    _fill(w, f, 0, width - 1, d_counter, d_counter, 3, pal["trim"])
    title = str(p.get("title") or "FOOD COURT").upper()[:SIGN_WIDTH]
    plaque(w, f, pal, width // 2, d_counter - 1, 3, f.facing, [title, "", "open all day", ""])

    # --- the covered seating: posts, an awning, tables and real seats
    tables = max(1, min(5, int(p["tables"])))
    step = max(4, (width - 4) // tables)
    table_at = [2 + step * k for k in range(tables) if 2 + step * k <= width - 3]
    for (i) in (1, width - 2):
        for d in (1, d_counter - 2):
            _column(w, f, i, d, 0, 3, pal["post"])
    for i in range(0, width):
        for d in range(0, d_counter):
            _put(w, f, i, d, 4, a if (i + d) % 2 == 0 else b)

    seats = []
    for i in table_at:
        d = 2
        _put(w, f, i, d, 0, pal["post"])
        _slab(w, f, i, d, 1, pal["slab"], "bottom")
        for (di, dd, back) in ((-1, 0, _i_dir(f, -1)), (1, 0, _i_dir(f, 1)),
                               (0, -1, f.facing), (0, 1, f.back)):
            if 0 <= i + di < width and 0 <= d + dd < d_counter:
                _stair(w, f, i + di, d + dd, 0, pal["stair"], back)
                seats.append(list(f.at(i + di, d + dd, 0)))
        _lamp_under(w, f, pal, i, d, 3)

    # --- bins, which are also `_SERVICE`: you use them from ABOVE, so the cell over one stays free
    for i in (0, width - 1):
        _put(w, f, i, 0, 0, "composter", level="0")
        _serve(service, f, i, 0, 0, "composter")

    _cornice(w, f, pal, width, depth, 4, int(p["min_run"]),
             skip=[(i, d) for i in range(width) for d in range(0, d_counter)])

    return {
        "kind": "foodcourt", "width": width, "depth": depth, "height": 5,
        "stalls": len(slots), "tables": len(table_at), "seats": len(seats),
        "seat_cells": seats,
        "hearth": bool(hearth), "signs": plaque.got, "service": service,
        "work_room": _WORK_ROOM,
        "stock": {"barrels": "stock them with whatever the park sells",
                  "smokers": "coal or charcoal for fuel"},
        "contract": (f"a served counter with {_WORK_ROOM} blocks of staff room behind it, "
                     f"{len(table_at)} tables with {len(seats)} seats under cover, a bin at each end, "
                     f"and a lantern over every table"),
        "unverified": [],
    }


# ---------------------------------------------------------------------------- the viewing stand

def _viewing(w: World, p: dict, ctx) -> dict:
    """A TERRACE THAT CAN ACTUALLY SEE THE SHOW - and the sightline is measured, not assumed.

    Every other quality in a grandstand is decoration. If the front row is looking at the back of
    a rail, or at the roof of the food court, the whole building is a shape. `aim` is the launch
    point `fireworks` reports on its own build, and the front row's eye cells are reported here,
    so `tests/test_spectacle.py` walks the segment between them through the COMBINED cells of both
    designs and asserts there is nothing in the way. That is the only form of the check worth
    having: a sightline asserted against one design's own cells proves nothing about the thing it
    is looking at.

    A SEATED EYE IS ONE COURSE ABOVE THE SEAT, and the rail is one course BELOW that - which is
    why the rail can exist at all. Built at seat height it would be a fence across the view.

    CONTRACT: `tiers` rows of seats each a course higher than the last, a rail at the front that
    does not block the front row, light at the back, and a clear line from every seat to `aim`.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    plaque = _Plaques(p.get("sign", True))
    tiers = max(2, min(8, int(p["tiers"])))
    width = max(9, int(p["width"]) | 1)
    depth = 2 * tiers + 2

    _pad(w, f, pal, width, depth, margin=1)
    seats = _terrace(w, f, pal, 0, width - 1, 1, 1, tiers, f.back)

    # --- the rail, ONE COURSE BELOW THE FRONT ROW'S EYES
    _railing(w, f, pal, [(i, 0) for i in range(-1, width + 1)], 0)

    # --- the back wall, which is what a terrace has instead of a fifth tier
    # ...AND IT IS BUILT FROM THE PAD UP, not from the top tier up. Started at the seating's own
    # height it stands on the air over the back walkway, whose floor stops two courses lower - a
    # wall floating a course clear of everything, which the audit passes (nothing is unsupported
    # in Minecraft's sense) and a 6-connectivity count catches as a second component.
    back = depth - 1
    for h in range(0, tiers + 2):
        _fill(w, f, 0, width - 1, back, back, h, pal["wall"] if h < tiers + 1 else pal["trim"])
    for i in (0, width - 1):
        _column(w, f, i, back, 0, tiers + 1, pal["post"])

    # --- light, hung from the back wall's own cornice so nothing hangs from air
    # THE LANTERNS STAND CLEAR OF THE SIGN'S OWN COLUMN. Hung at width//2 they occupied the cell
    # the nameplate wants, `_Plaques` correctly refused to overwrite one, and the terrace shipped
    # with NO SIGN AT ALL - silently, because a refused sign places nothing and looks like a
    # design that never asked for one.
    lit = 0
    for i in (2, width - 3):
        _put(w, f, i, back - 1, tiers + 1, pal["trim"])
        lit += int(_lamp_under(w, f, pal, i, back - 1, tiers))

    title = str(p.get("title") or "GRANDSTAND").upper()[:SIGN_WIDTH]
    plaque(w, f, pal, width // 2, back - 1, tiers, f.facing,
           [title, str(p.get("when") or "")[:SIGN_WIDTH], "best view", "of the show"])

    eyes = [list(f.at(i, d, h + 1)) for (i, d, h) in seats]
    front = [list(f.at(i, d, h + 1)) for (i, d, h) in seats if h == 0]
    aim = [int(v) for v in p["aim"]] if p.get("aim") else None
    return {
        "kind": "viewing", "width": width, "depth": depth, "height": tiers + 2,
        "tiers": tiers, "seats": len(seats), "lit": lit, "signs": plaque.got,
        "seat_cells": [list(f.at(i, d, h)) for (i, d, h) in seats],
        "eyes": eyes, "front_row": front, "sightline_to": aim,
        "contract": (f"{tiers} tiers, {len(seats)} seats, a rail below eye level, and a clear "
                     f"line from every seat to the launch point"),
        "unverified": ([] if aim else
                       ["no `aim` was given, so the sightline is UNCHECKED: pass the "
                        "`launch` point off the fireworks build and it becomes an assertion"]),
    }


# ---------------------------------------------------------------------------- the leaderboard

def _leaderboard(w: World, p: dict, ctx) -> dict:
    """A WALL OF LECTERNS: the reason to come back.

    **`item_frame` IS NOT A BLOCK.** `blocks.exists("item_frame")` is False - it, `painting` and
    `armor_stand` are entities, and nothing in this pipeline places an entity - so the wall the
    brief describes as lecterns and item frames is lecterns, signs and a painted board. Saying so
    is the point: a feature quietly dropped is the failure mode this whole repo keeps recording,
    and it goes in `unverified` rather than into a comment nobody reads.

    A lectern holds a written book, which is a real record a player can leave and another can
    read, so the wall does the job the item frames were for. Rule 10 applies to it exactly as it
    does to a barrel: three blocks of room in front, or you cannot stand and read.

    CONTRACT: `boards` lecterns, each with three clear blocks in front of it, each named by a sign
    on the wall behind, under light, with a header naming the board.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    plaque = _Plaques(p.get("sign", True))
    boards = max(2, min(8, int(p["boards"])))
    width = 2 * boards + 1
    depth = 4
    _pad(w, f, pal, width, depth, margin=1)

    back = depth - 1
    for h in range(0, 5):
        _fill(w, f, 0, width - 1, back, back, h, pal["wall"] if 0 < h < 4 else pal["trim"])
    # THE BOARD: an accent panel, so the wall reads as a notice board rather than as a wall
    for i in range(1, width - 1):
        for h in (2, 3):
            _put(w, f, i, back, h, pal["accent"] if (i + h) % 2 == 0 else pal["wall"])
    for i in (0, width - 1):
        _column(w, f, i, back - 1, 0, 4, pal["post"])

    names = ["COASTER", "THE DROP", "PARKOUR", "BIG WHEEL", "HOOPLA",
             "THE MAZE", "RIFLE RANGE", "SPIN THE WHEEL"]
    stands = []
    for k in range(boards):
        i = 1 + 2 * k
        _put(w, f, i, back - 1, 0, "lectern", facing=f.facing, has_book="false", powered="false")
        _serve(stands, f, i, back - 1, 0, "lectern", f.facing)
        plaque(w, f, pal, i, back - 1, 2, f.facing, [names[k % len(names)][:SIGN_WIDTH],
                                                     "best time", "sign the book", ""])

    # THE LANTERNS KEEP OFF THE HEADER'S COLUMN. Hung at width//2 the header sign found a LANTERN
    # behind it - `park._sign` asks only whether the cell is occupied, so it placed happily and
    # the game would refuse it. A sign needs a full block behind, and that is now asserted.
    lit = 0
    for i in (1, width - 2):
        _put(w, f, i, back - 1, 5, pal["trim"])
        lit += int(_lamp_under(w, f, pal, i, back - 1, 4))

    _put(w, f, width // 2, back - 1, 4, pal["trim"])
    title = str(p.get("title") or "HALL OF FAME").upper()[:SIGN_WIDTH]
    plaque(w, f, pal, width // 2, back - 2, 4, f.facing, [title, "", "beat these", ""])
    _cornice(w, f, pal, width, depth, 5, int(p["min_run"]))

    return {
        "kind": "leaderboard", "width": width, "depth": depth, "height": 6,
        "boards": boards, "lit": lit, "signs": plaque.got, "service": stands,
        "work_room": _WORK_ROOM,
        "stock": {"each lectern": "one book and quill, written up with the record"},
        "contract": (f"{boards} lecterns, each with {_WORK_ROOM} blocks of room in front and a "
                     f"named sign behind, under light"),
        "unverified": ["item frames, paintings and armour stands are ENTITIES, not blocks: "
                       "blocks.exists('item_frame') is False and nothing here can place one"],
    }


BUILDERS = {
    "fireworks": _fireworks,
    "bandstand_show": _bandstand,
    "foodcourt": _foodcourt,
    "viewing": _viewing,
    "leaderboard": _leaderboard,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**SPECTACLE, **cfg}
    if not p.get("at"):
        raise ValueError("spectacle needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown spectacle kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    # THE EXPENSIVE PARTS ARE COUNTED, because they decide whether this can be built at all -
    # `casino.build`'s rule. A bandstand asked for note blocks is a bandstand you have to shop for.
    budget = {}
    for _pos, (name, _pr) in w.cells.items():
        if name in ("note_block", "jukebox", "redstone_lamp", "glowstone", "sea_lantern"):
            budget[name] = budget.get(name, 0) + 1

    # THE MEASURED FOOTPRINT, not the nominal one. `width`/`depth` name the STRUCTURE; what a
    # planner has to reserve is the whole thing including its pad margin and, on the firework
    # pad, the stand out in front of it - which is four cells of ground the nominal numbers do
    # not mention. The planner packs what it is told, so it is told what was actually built.
    xs = [q[0] for q in w.cells]
    zs = [q[2] for q in w.cells]
    span_x = max(xs) - min(xs) + 1
    span_z = max(zs) - min(zs) + 1
    frontage, into = (span_z, span_x) if p["facing"] in ("east", "west") else (span_x, span_z)

    return w.canvas({
        "kind": f"spectacle/{p['kind']}",
        "footprint": [frontage, into],
        "land": p["land"],
        "facing": p["facing"],
        "when": p.get("when"),
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        "budget": budget,
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
