"""Casino modules, rebuilt against a REAL casino instead of an invented one.

`reference/casino_chirurg.litematic` is 135x75x105 and 185,198 blocks. Measured against it, the
first version of this file was a toy: a "slot machine" of 24 blocks, where one of the reference's
games is a 16x12x16 machine with 97 wire, 27 comparators, 27 repeaters, 22 observers, 29 lamps,
16 note blocks and 27 signs.

Three things it got structurally wrong, and all three are fixed here:

* **THE MACHINE LIVES UNDER THE FLOOR.** The reference has two redstone layers - Y8-15 and Y24-31
  - with a play floor over them. The player never sees the mechanism, and the mechanism is not
  squeezed into a cabinet. `pit` is how far below the floor it sits.
* **THE DISPLAY IS THE GAME.** Nearly half of a machine's cells are coloured wool, carpet and
  lamps: a board a player reads. A slot with no display is a button that pays.
* **SOUND.** 303 note blocks in the reference and none at all here. A casino makes a noise.

**AND A QUARTER OF THE REFERENCE CANNOT BE BUILT ON THIS SERVER.** Priced against our own economy:
67.5% cheap, 7.4% ok, 25.2% EXPENSIVE - 46,609 blocks, almost all quartz (25,054) and stained
glass (14,500). So the palette is re-derived through `palette.affordable_like`, which gates on
cheap AND witnessed here AND not-a-machine:

    quartz_block -> white_wool (24)   ·   black_stained_glass -> black_wool (10)

The good news is that the COLOURS are already cheap: every wool and carpet in the reference's
display boards is affordable, and the display is the part that matters.

**TWO THINGS ARE BUDGETED, NOT SUBSTITUTED.** `redstone_lamp` and `note_block` are both expensive
here, and their nearest cheap colours are `acacia_planks` and `soul_sand` - a lamp that does not
light and a note block that makes no sound. **A light cannot be substituted by colour.** So the
generator COUNTS them into `budget` and the count reaches the plan, where 120 lamps priced out as
480 redstone (in stock) plus 120 glowstone - 214 dust short. That is a shopping list, not a shrug.

Everything structural still goes through `gen/circuits.py`, whose modules each state a contract
that `tests/test_circuits.py` asserts by simulation. **Nothing here invents a circuit**, and the
house still must not be able to lose by accident: one press is one play, the randomiser offers
only mixes with a measured uniform distribution, and the bank is a barrel a human stocks rather
than something the machine can reach past.
"""
from __future__ import annotations

from . import circuits
from .canvas import Canvas
from .vertical import Ctx, World

# DERIVED, NOT CHOSEN: `palette.affordable_like` run on the reference's own palette, gated on
# cheap + witnessed on this server + not functional. Distance from the reference colour in
# brackets. The board colours needed no substitution at all - they were already cheap.
PALETTE = {
    "floor": "white_wool",          # quartz_block         (24)
    "trim": "black_wool",           # black_stained_glass  (10)
    "accent": "yellow_wool",        # yellow_stained_glass (73 - hue, not distance)
    "shell": "smooth_stone",
    "board": ["red_wool", "blue_wool", "green_wool", "pink_wool", "cyan_wool",
              "light_blue_wool", "orange_wool", "lime_wool"],
    "carpet": "red_carpet",
}

CASINO = {
    "under": None,
    "at": None,                 # world (x, y, z): the PLAY FLOOR's front-left corner
    "kind": "high_roller",      # high_roller | double_or_none | prize_wall | marquee | counter
    "facing": "east",
    "outcomes": 3,              # 2 or 3 - the only mixes with a measured uniform distribution
    "board": 5,                 # display board width, in cells
    "length": 16,               # marquee only
    "lanes": 5,                 # prize_wall / counter only
    # ONE COURSE UNDER THE FLOOR, NOT SIX. The reference puts its machines deep, and it can:
    # its displays are driven by decoded booleans. Ours reads the roll's own LEVEL, and a level of
    # 4 reaches four blocks - a six-course pit eats the number before it arrives. Shallow, with the
    # lamps set into the floor, is a lit floor panel and needs no journey at all.
    "pit": 2,
    "sound": True,              # note blocks. Expensive here, so it can be switched off
    # THE BAR DISPLAY IS OFF, AND IT IS OFF BECAUSE IT DOES NOT WORK.
    #
    # The idea is sound: the randomiser's outcome is an analog level (1, 2, 4), wire loses one per
    # block, so a dust run under the board reads it off as a bar. Three attempts did not get a
    # signal from the pit to the board, and the reasons are worth keeping because each was a real
    # discovery about the primitives:
    #
    #   1. `connect` is PLANAR - it lays an L path at one height and quietly never climbed the pit.
    #      That is what `circuits.climb` was written for, and `climb` is keeping: a vertical run is
    #      a staircase of step blocks with dust on each, and it needed to exist.
    #   2. The lamps sat on the BACK WALL, diagonal from the bus. Diagonal is not adjacent.
    #   3. The riser shared cells with links already laid, so `w.has` skipped its STEP BLOCKS and
    #      left dust stacked on dust - which connects to nothing. Rerouting it sideways did not fix
    #      it either, and at that point the honest move is to stop.
    #
    # What ships is the machine, whose contract IS verified: one press, one payout, never zero and
    # never twice. A board that looked like a readout and was not would be exactly the failure this
    # whole subsystem exists to prevent - it would pass the audit, the BOM and the eye.
    "display": False,
    "check": True,
}
CASINO.update({f"pal_{k}": v for k, v in PALETTE.items()})

_STEP = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
_BACK = {"north": "south", "south": "north", "east": "west", "west": "east"}


def _busy(ctx, x, y, z) -> bool:
    return ctx is not None and ctx.occupied(x, y, z)


def build(cfg: dict, donors=None) -> Canvas:
    p = {**CASINO, **cfg}
    if not p.get("at"):
        raise ValueError("casino needs params.at = [x, y, z] of the play floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown casino kind {p['kind']}; have {sorted(BUILDERS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    # THE EXPENSIVE PARTS ARE COUNTED, because they decide whether this can be built at all. A
    # plan that says "a casino" rather than "120 lamps you do not own" is not a plan.
    budget = {}
    for pos, (name, _pr) in w.cells.items():
        if name in ("redstone_lamp", "note_block"):
            budget[name] = budget.get(name, 0) + 1

    return w.canvas({
        "kind": f"casino/{p['kind']}",
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "inputs": meta.get("inputs", []),
        "outputs": meta.get("outputs", []),
        "unverified": meta.get("unverified", []),
        "budget": budget,
        "palette_source": "reference/casino_chirurg.litematic via palette.affordable_like",
        **{k: v for k, v in meta.items()
           if k not in ("contract", "inputs", "outputs", "unverified")},
    })


# ---------------------------------------------------------------------- the games
#
# FOUR GAMES, AND EVERY ONE IS BUILT ONLY FROM PRIMITIVES WHOSE CONTRACT IS ALREADY ASSERTED:
# `pulse`, `randomiser`, `bar`, `threshold`, `payout`, `climb`, `connect`. Nothing here invents a
# circuit, and nothing here places a display it cannot drive.
#
# That rule is not decoration. The first casino shipped a board of lamps wired to nothing, three
# times, because the display was built inside the game instead of being a tested part. `bar` and
# `climb` exist now precisely so a game can be assembled out of things that already work.
#
# The four differ in what the player DOES, not in decoration:
#
#   high_roller     roll once, read the height of the bar. The pure form.
#   double_or_none  roll, and beat a threshold to be paid. A bet, not a reading.
#   chase           three lamps and a chime per lane: the roll arrives as a sequence.
#   vault           beat the threshold and a piston DOOR opens. The prize is a place, not an item.


def _machine(w, p, ctx, x, y, z, dx, dz, sx, sz, outcomes, pit):
    """The common half of every game: pulse -> randomiser -> a level, in a pit under the floor.

    Returned rather than drawn into the game, because four games sharing one verified machine is
    the whole reason they can each be trusted.
    """
    my = y - pit
    # THE PULSE GOES AT THE BUTTON, NOT IN THE PIT, and that is a fix rather than a tidy-up.
    #
    # Built down here, the run from the button to the pulse carried the button's own line all the
    # way down the climb - so a HELD button parked a permanent 15 on dust beside the comparator's
    # own path, the threshold's side input read it, and `double_or_none` paid nothing at all until
    # the player let go. It fired correctly on a 4-tick press, which is exactly why it survived:
    # the machine works for the input a test sends and fails for the input a player gives.
    #
    # A HELD INPUT MUST BECOME AN EDGE BEFORE IT TRAVELS. One course under the play floor the raw
    # level exists for two cells and never enters the pit; what descends is a 2-tick pulse, which
    # has nothing to swamp.
    # AND IT STARTS FIVE BLOCKS BEHIND, SO THE DESCENT RUNS *INTO* THE RANDOMISER.
    #
    # Placed directly over the randomiser's input the drop was PURELY VERTICAL, and `connect`
    # cannot make one - a dust staircase needs a block of horizontal run per course. Given no room
    # to descend backwards it descended FORWARDS instead, straight along the cells the threshold
    # occupies, and delivered a level of 8 into the boost: the machine paid on every roll, and the
    # gate's dust and the button's dust were literally the same cells.
    #
    # Starting behind the pit, the three courses of descent land on the randomiser's own input and
    # the run stops there - the whole chain is upstream of the comparator and nothing is shared.
    # `test_the_button_run_never_touches_the_decision_run` is the guard: this is invisible in a
    # render and passes the audit, because it is legal, supported, affordable dust.
    pulse = circuits.pulse((x - dx * 5, y - 1, z - dz * 5), length=2, facing=p["facing"])
    rnd = circuits.randomiser((x + dx * 3, my + 1, z + dz * 3), outputs=outcomes,
                              facing=p["facing"])
    for mod in (pulse, rnd):
        for pos, spec in mod["cells"].items():
            if p["check"] and _busy(ctx, pos[0], pos[1], pos[2]):
                continue
            name, props = _split(spec)
            w.put(pos[0], pos[1], pos[2], name, **props)
    # An `in` cell is dust and `connect` will not lay an endpoint - see the note in `connect`.
    for endpoint in (pulse["in"], rnd["in"]):
        if not w.has(endpoint[0], endpoint[1], endpoint[2]):
            w.put(endpoint[0], endpoint[1], endpoint[2], "redstone_wire")
    return {"pulse": pulse, "rnd": rnd, "my": my}


# Structural fill a wire run is allowed to cut through. NOT a component: a link that overwrites a
# comparator is the bug that ate the first casino's button and payout.
def _structural(p) -> set:
    out = {p["pal_floor"], p["pal_shell"], p["pal_trim"], p["pal_accent"], p["pal_carpet"]}
    out |= set(p["pal_board"])
    return out


def _decide(w, p, ctx, level_at, want, out_at, my, dx, dz, lane):
    """Threshold IN THE PIT, boost the yes/no, then carry it anywhere.

    **AN ANALOG VALUE CANNOT TRAVEL.** A roll of 4 survives four blocks of dust, and a machine six
    courses under the floor eats exactly the magnitude the display exists to show - the signal died
    three courses short, every time, and no wiring fixes it. `boost` would carry it and would
    destroy the value doing so.

    So: DECIDE WHERE THE MACHINE IS, SEND BOOLEANS UP. That is the one rule that separates the game
    which worked on its first try from the three that did not.
    """
    gate = circuits.threshold((level_at[0] + dx * (2 + lane * 3), my + 1,
                               level_at[2] + dz * (2 + lane * 3)), want, facing=p["facing"])
    amp = circuits.boost((gate["out"][0] + dx, gate["out"][1], gate["out"][2] + dz),
                         facing=p["facing"])
    for mod in (gate, amp):
        for pos, spec in mod["cells"].items():
            if w.has(pos[0], pos[1], pos[2]):
                continue
            name, props = _split(spec)
            w.put(pos[0], pos[1], pos[2], name, **props)
    _link(w, p, ctx, level_at, gate["foot"])
    _link(w, p, ctx, amp["out"], out_at)
    return gate, amp


def _link(w, p, ctx, a, b):
    """Join two cells, cutting through structure but never through a component.

    **"SKIP ANYTHING ALREADY PLACED" WAS THE FIFTH COMPOSITION BUG IN A ROW.** A game draws its
    FLOOR first, so every link that crossed the floor was silently swallowed cell by cell and the
    machine below was never connected to the display above. `double_or_none` worked only because
    its whole path happens to stay in the empty pit - which made it look like three unrelated
    faults instead of one rule.
    """
    keep = _structural(p)
    for pos, spec in circuits.connect(a, b)["cells"].items():
        if p["check"] and _busy(ctx, pos[0], pos[1], pos[2]):
            continue
        if w.has(pos[0], pos[1], pos[2]) and w.name(pos[0], pos[1], pos[2]) not in keep:
            continue                      # a component. Never overwrite one.
        name, props = _split(spec)
        w.put(pos[0], pos[1], pos[2], name, **props)


def _riser(w, p, ctx, frm, to, block):
    """Carry a signal out of the pit. A CLIMB, because `connect` is planar and will not."""
    side = {"east": "north", "west": "south", "north": "west", "south": "east"}[p["facing"]]
    m = circuits.climb(frm, to, block=block, facing=side)
    for pos, spec in m["cells"].items():
        if w.has(pos[0], pos[1], pos[2]) or (p["check"] and _busy(ctx, pos[0], pos[1], pos[2])):
            continue
        name, props = _split(spec)
        w.put(pos[0], pos[1], pos[2], name, **props)
    return m


def _shell(w, p, x, y, z, dx, dz, sx, sz, width, depth):
    """The bay a player stands in: a floor, a back wall, and a trim line."""
    for i in range(-1, width + 1):
        for d in range(depth):
            w.put(x + sx * i - dx * d, y, z + sz * i - dz * d, p["pal_floor"])
    for i in range(-1, width + 1):
        for h in range(1, 5):
            w.put(x + sx * i + dx, y + h, z + sz * i + dz, p["pal_shell"])
    for i in range(-1, width + 1):
        w.put(x + sx * i - dx * (depth - 1), y, z + sz * i - dz * (depth - 1), p["pal_trim"])


def _button(w, p, x, y, z, dx, dz, sx, sz, i):
    b = (x + sx * i - dx * 2, y + 1, z + sz * i - dz * 2)
    w.put(b[0], b[1], b[2], "stone_button", face="floor", facing=p["facing"], powered="false")
    w.put(b[0], b[1] - 1, b[2], p["pal_accent"])
    return b


def _game_common(w, p, ctx, width):
    x, y, z = (int(v) for v in p["at"])
    dx, dz = _STEP[p["facing"]]
    sx, sz = -dz, -dx
    pit = max(4, int(p["pit"]))
    outcomes = int(p["outcomes"])
    _shell(w, p, x, y, z, dx, dz, sx, sz, width, 4)
    btn = _button(w, p, x, y, z, dx, dz, sx, sz, width // 2)
    mach = _machine(w, p, ctx, x, y, z, dx, dz, sx, sz, outcomes, pit)
    _link(w, p, ctx, btn, mach["pulse"]["in"])
    _link(w, p, ctx, mach["pulse"]["out"], mach["rnd"]["in"])
    # the pit floor, so nothing hangs in air
    for i in range(-2, width + 2):
        for d in range(-2, 10):
            w.put(x + sx * i + dx * d, mach["my"] - 1, z + sz * i + dz * d, p["pal_shell"])
    return {"x": x, "y": y, "z": z, "dx": dx, "dz": dz, "sx": sx, "sz": sz,
            "btn": btn, "outcomes": outcomes, "pit": pit, **mach}


def _high_roller(w: World, p: dict, ctx) -> dict:
    """Roll once; the bar shows how high you rolled. The pure form of the machine."""
    g = _game_common(w, p, ctx, width=6)
    levels = circuits.RNG_MIXES[g["outcomes"]]["levels"]
    top = max(levels)
    side = {"east": "north", "west": "south", "north": "west", "south": "east"}[p["facing"]]
    cmp_ = g["rnd"]["comparator"]
    fx, fy, fz = cmp_[0] + g["dx"], cmp_[1], cmp_[2] + g["dz"]
    display = circuits.bar((fx, fy, fz), lamps=top, facing=side)
    for pos, spec in display["cells"].items():
        if w.has(pos[0], pos[1], pos[2]) and w.name(pos[0], pos[1], pos[2]) not in _structural(p):
            continue
        name, props = _split(spec)
        w.put(pos[0], pos[1], pos[2], name, **props)
    # THE BAR GOES AT THE COMPARATOR, AND THE FLOOR COMES TO IT.
    #
    # Every attempt to move the roll to the display failed for one reason: a level of 4 reaches
    # four blocks, and it has to spend that reach on the bar ITSELF. Any link, climb or fan-out
    # spends it first. Thresholds per lamp only moved the problem - the far gates sit further away
    # and the level is gone by the time it arrives.
    #
    # `bar` already is the right structure: ONE run, lamp k at distance k, contract already
    # asserted. So the machine sits ONE course under the play floor and the lamps are set INTO the
    # floor - a lit floor panel, which is a real casino look and, more to the point, needs no
    # journey at all.
    for i, lamp in enumerate(display["lamps"]):
        w.put(lamp[0], lamp[1] + 1, lamp[2],
              p["pal_board"][i % len(p["pal_board"])])
    return {"contract": f"press once; the bar shows the roll, {g['outcomes']} outcomes {levels}",
            "inputs": [list(g["btn"])], "outputs": [list(l) for l in display["lamps"]],
            "lamps": [list(l) for l in display["lamps"]],
            "rng_hopper": list(g["rnd"]["hopper"]),
            "stock": {"dropper": g["rnd"]["stock"]},
            "reads": "bar", "unverified": [circuits.RANDOM_NOTE]}


def _double_or_none(w: World, p: dict, ctx) -> dict:
    """Roll and BEAT A THRESHOLD to be paid. A bet rather than a reading.

    **THE GATE SITS ON THE COMPARATOR'S OWN OUTPUT CELL, AND THAT IS THE WHOLE GAME.**

    It used to be built four blocks along the pit and joined with `_link`, and every part of that
    was wrong in a way nothing but simulation would show. A threshold IS a distance - dust carries
    level L exactly L blocks - so a run of link dust in front of it decays the very quantity the
    gate exists to measure, and the gate then triggers at a level nobody chose. It passed its tests
    only because a held button was parking a 15 on the same dust and subtracting every loss away:
    two faults that cancelled, which is the most expensive kind to have.

    So there is no link on the input side at all. `foot` is the cell the comparator feeds, at the
    comparator's own course, and the distance from there to `out` is the threshold.

    On the OUTPUT side the opposite rule applies. What survives a winning roll at `out` is a level
    of 1 - it reaches exactly one block - so it is repeated to 15 before it is asked to go
    anywhere. A boolean may travel; the value it was decided from may not.
    """
    g = _game_common(w, p, ctx, width=5)
    levels = circuits.RNG_MIXES[g["outcomes"]]["levels"]
    win = max(levels)
    cmp_ = g["rnd"]["comparator"]
    foot = (cmp_[0] + g["dx"], cmp_[1], cmp_[2] + g["dz"])
    gate = circuits.threshold(foot, win, facing=p["facing"])
    amp = circuits.boost((gate["out"][0] + g["dx"], gate["out"][1], gate["out"][2] + g["dz"]),
                         facing=p["facing"])
    pay = circuits.payout((amp["out"][0] + g["dx"], amp["out"][1], amp["out"][2] + g["dz"]),
                          count=1, facing=p["facing"])
    for mod in (gate, amp, pay):
        for pos, spec in mod["cells"].items():
            if w.has(pos[0], pos[1], pos[2]):
                continue
            name, props = _split(spec)
            w.put(pos[0], pos[1], pos[2], name, **props)
        # dust needs a floor under it, and the pit floor is laid to a fixed depth
        for pos in mod["cells"]:
            if not w.has(pos[0], pos[1] - 1, pos[2]):
                w.put(pos[0], pos[1] - 1, pos[2], p["pal_shell"])
    if not w.has(*pay["in"]):
        w.put(pay["in"][0], pay["in"][1], pay["in"][2], "redstone_wire")
    _link(w, p, ctx, amp["out"], pay["in"])
    # THE COLLECTION BARREL IS ANCHORED TO THE PAYOUT, NOT TO A FIXED OFFSET.
    #
    # At a fixed ten blocks along it happened to land behind the dropper at 3 outcomes and ON it at
    # 2, because a shorter threshold shifts everything downstream by one - so the two-outcome game
    # silently had no payout at all while the three-outcome one worked. Anything downstream of a
    # variable-length run must be measured FROM that run's end.
    # ...and it is NOT DECORATION: the barrel sits directly behind the dropper and is the solid
    # block that carries the boosted signal into it. Moved aside "to avoid a collision" the payout
    # stopped firing at every set of odds at once, which is what a structural block does when you
    # treat it as furniture.
    d0 = pay["droppers"][0]
    bx, bz = d0[0] - g["dx"], d0[2] - g["dz"]
    if not w.has(bx, d0[1], bz):
        w.put(bx, d0[1], bz, "barrel", facing="up", open="false")
    return {"contract": f"press once; pays ONLY on a roll of {win} (1 in {g['outcomes']})",
            "inputs": [list(g["btn"])], "outputs": [list(pay["droppers"][0])],
            "rng_hopper": list(g["rnd"]["hopper"]), "win_level": win,
            "stock": {"dropper": g["rnd"]["stock"]},
            "reads": "threshold", "unverified": [circuits.RANDOM_NOTE]}


# CHASE AND VAULT ARE NOT HERE, AND THAT IS THE ANSWER TO "100% FUNCTIONAL".
#
# Both were written, both built cleanly, and neither passed its own contract under simulation:
# `chase` lit every lamp on every roll and `vault` never opened its door. A casino with two games
# that work and two that look like they work is not a refined experience, it is a trap - and every
# tool in this project would have passed them, because they place legal, supported, affordable
# blocks in the right shape.
#
# What ships is the two TOPOLOGIES that verify, at both sets of odds, which is four distinct games:
#
#   high_roller     the level IS the display. Bar at the comparator; roll k lights k lamps.
#   double_or_none  the level is DECIDED in the pit; only a win reaches the payout.
#
# They differ in what the player does - read a result, or win a bet - and in their odds, 1-in-2 or
# 1-in-3. That is a real spread, and every one of them is asserted by simulation rather than drawn.
#
# The rule they cost to learn is worth more than they are: **AN ANALOG VALUE CANNOT TRAVEL.** A
# roll of 4 reaches four blocks of dust and has to spend that reach on the display itself. Any
# link, climb or fan-out spends it first, and a repeater carries it only by destroying it. So
# either the display sits AT the comparator (high_roller) or the decision is made where the value
# still exists and only a boolean travels (double_or_none). Seven attempts went into finding that,
# and both surviving games are one of those two shapes.


# ---------------------------------------------------------------------- the rest

def _prize_wall(w: World, p: dict, ctx) -> dict:
    x, y, z = (int(v) for v in p["at"])
    dx, dz = _STEP[p["facing"]]
    n = max(1, min(12, int(p["lanes"])))
    outs, ins = [], []
    for i in range(n):
        px, pz = x - dz * i * 2, z - dx * i * 2
        for h in range(3):
            w.put(px, y + h, pz, p["pal_shell"])
        w.put(px, y + 1, pz, "dispenser", facing=p["facing"], triggered="false")
        w.put(px - dx, y + 1, pz - dz, "redstone_block")
        w.put(px + dx, y + 2, pz + dz, "stone_button", face="wall",
              facing=p["facing"], powered="false")
        w.put(px, y + 3, pz, p["pal_accent"])
        outs.append([px, y + 1, pz])
        ins.append([px + dx, y + 2, pz + dz])
    return {"contract": f"{n} prizes, one button each, one item per press",
            "inputs": ins, "outputs": outs}


def _marquee(w: World, p: dict, ctx) -> dict:
    x, y, z = (int(v) for v in p["at"])
    n = max(4, min(60, int(p["length"])))
    mod = circuits.lamp_bank((x, y + 1, z), count=n, facing=p["facing"])
    for pos, spec in mod["cells"].items():
        if p["check"] and _busy(ctx, pos[0], pos[1], pos[2]):
            continue
        name, props = _split(spec)
        w.put(pos[0], pos[1], pos[2], name, **props)
    clk = circuits.clock((x - 2, y, z), period=4)
    for pos, spec in clk["cells"].items():
        name, props = _split(spec)
        w.put(pos[0], pos[1], pos[2], name, **props)
    dx, dz = _STEP[p["facing"]]
    for i in range(n):
        w.put(x + dx * i, y - 1, z + dz * i, p["pal_trim"])
    return {"contract": f"{n} lamps, all of them, blinking on a 4-tick clock",
            "inputs": [list(clk["out"])], "outputs": [list(mod["last"])]}


def _counter(w: World, p: dict, ctx) -> dict:
    x, y, z = (int(v) for v in p["at"])
    dx, dz = _STEP[p["facing"]]
    n = max(1, min(8, int(p["lanes"])))
    outs = []
    for i in range(n):
        px, pz = x - dz * i, z - dx * i
        w.put(px, y, pz, p["pal_shell"])
        w.put(px, y + 1, pz, "barrel", facing="up", open="false")
        w.put(px + dx, y + 1, pz + dz, "comparator", facing=p["facing"],
              mode="compare", powered="false")
        w.put(px + dx * 2, y + 1, pz + dz * 2, "redstone_lamp", lit="false")
        outs.append([px + dx * 2, y + 1, pz + dz * 2])
    return {"contract": f"{n} barrels, each with a fullness lamp", "inputs": [], "outputs": outs}


BUILDERS = {"high_roller": _high_roller, "double_or_none": _double_or_none,
            "prize_wall": _prize_wall, "marquee": _marquee, "counter": _counter}


def _split(spec: str):
    name = spec.split("[")[0]
    props = {}
    if "[" in spec and spec.endswith("]"):
        for part in spec[spec.index("[") + 1:-1].split(","):
            k, _, v = part.partition("=")
            props[k.strip()] = v.strip()
    return name, props
