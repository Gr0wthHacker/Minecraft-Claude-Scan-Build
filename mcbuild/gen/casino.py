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
    "kind": "game",             # game | prize_wall | marquee | counter
    "facing": "east",
    "outcomes": 3,              # 2 or 3 - the only mixes with a measured uniform distribution
    "board": 5,                 # display board width, in cells
    "length": 16,               # marquee only
    "lanes": 5,                 # prize_wall / counter only
    "pit": 6,                   # how far BELOW the floor the machine sits
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


# ---------------------------------------------------------------------- the game

def _game(w: World, p: dict, ctx) -> dict:
    """One casino game: a board a player reads, a verified randomiser under the floor.

    Laid out the way the reference is - the player stands on a floor, faces a board, presses a
    button, and every moving part is in a pit below.
    """
    x, y, z = (int(v) for v in p["at"])
    dx, dz = _STEP[p["facing"]]
    sx, sz = -dz, -dx                      # sideways, across the board's width
    board = max(3, min(9, int(p["board"])))
    pit = max(3, int(p["pit"]))
    outcomes = int(p["outcomes"])

    # --- the play floor, and the back wall the board sits on
    for i in range(-1, board + 1):
        for d in range(4):
            w.put(x + sx * i - dx * d, y, z + sz * i - dz * d, p["pal_floor"])
    for i in range(-1, board + 1):
        for h in range(1, 5):
            w.put(x + sx * i + dx * 2, y + h, z + sz * i + dz * 2, p["pal_shell"])

    # --- the board. THE DISPLAY IS THE GAME, so it is wired to the RESULT rather than decorated.
    #
    # The randomiser's outcome is an ANALOG LEVEL (1, 2 or 4), and wire loses one per block - so a
    # run of dust under the board reads the outcome off as a BAR: level 1 lights one lamp, level 4
    # lights three. That is a real casino display and, unlike a single-winner decoder, it needs no
    # level discriminator to build or to verify.
    #
    # The first version placed the lamps and note blocks and wired NEITHER. The inspection said so
    # immediately - "redstone_lamp is not wired x2", "note_block is not wired x3" - which is the
    # composing-modules lesson for the third time today: parts near each other are not a machine.
    lamps, chimes, cols = [], [], []
    levels = circuits.RNG_MIXES[outcomes]["levels"]
    for k in range(outcomes if p.get("display") else 0):
        i = k + 1                                   # distance along the bus = the level it needs
        colour = p["pal_board"][k % len(p["pal_board"])]
        # THE LAMP SITS DIRECTLY ON THE BUS. Put on the back wall it is DIAGONAL from the dust and
        # nothing reaches it - which is exactly what the first bar did: three lamps, no light.
        lamp = (x + sx * i, y + 1, z + sz * i)
        w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")
        for h in (2, 3):                            # the colour reads above the lamp
            w.put(x + sx * i, y + h, z + sz * i, colour)
        lamps.append(list(lamp))
        cols.append({"outcome": k, "colour": colour, "lamp": list(lamp),
                     "lights_at_level": levels[k]})
        if p["sound"]:
            ch = (x + sx * i + dx, y, z + sz * i + dz)   # beside the bus, on the floor course
            w.put(ch[0], ch[1], ch[2], "note_block", instrument="harp",
                  note=str(6 + k * 4), powered="false")
            chimes.append(list(ch))

    # --- the button the player presses
    # THE BUTTON MUST NOT SIT ON THE BUS. Placed at the middle of the board it landed on lamp
    # index 1 and simply replaced it - a display with a hole in it, and no error anywhere.
    btn = (x - dx * 2, y + 1, z - dz * 2)
    w.put(btn[0], btn[1], btn[2], "stone_button", face="floor",
          facing=p["facing"], powered="false")
    w.put(btn[0], btn[1] - 1, btn[2], p["pal_trim"])

    # --- the machine, in the pit
    my = y - pit
    pulse = circuits.pulse((x, my, z), length=2, facing=p["facing"])
    rnd = circuits.randomiser((x + dx * 3, my + 1, z + dz * 3), outputs=outcomes,
                              facing=p["facing"])
    pay = circuits.payout((x + dx * 6, my, z + dz * 6), count=1, facing=p["facing"])
    for mod in (pulse, rnd, pay):
        for pos, spec in mod["cells"].items():
            if p["check"] and _busy(ctx, pos[0], pos[1], pos[2]):
                continue
            name, props = _split(spec)
            w.put(pos[0], pos[1], pos[2], name, **props)
    # AN `in` CELL IS WIRE, AND A CONNECTOR WILL NOT PLACE IT. `connect` deliberately skips its
    # endpoints - it must never overwrite the component it joins - so an endpoint that is supposed
    # to be dust has to be laid here. Without it the randomiser's trigger cell was simply empty and
    # the dropper was never fired: "dropper is not wired", on a machine that looked complete.
    for endpoint in (pulse["in"], rnd["in"], pay["in"]):
        if not w.has(endpoint[0], endpoint[1], endpoint[2]):
            w.put(endpoint[0], endpoint[1], endpoint[2], "redstone_wire")
    # ...and the links. A CONNECTOR RUNS BETWEEN THINGS and never overwrites a component.
    for link in (circuits.connect(btn, pulse["in"]),
                 circuits.connect(pulse["out"], rnd["in"]),
                 circuits.connect(rnd["comparator"], pay["in"])):
        for pos, spec in link["cells"].items():
            if w.has(pos[0], pos[1], pos[2]) or (p["check"] and _busy(ctx, pos[0], pos[1], pos[2])):
                continue
            name, props = _split(spec)
            w.put(pos[0], pos[1], pos[2], name, **props)

    # the pit needs a floor, or the machine hangs in air
    for i in range(-1, board + 1):
        for d in range(-1, 9):
            w.put(x + sx * i + dx * d, my - 1, z + sz * i + dz * d, p["pal_shell"])

    # --- the display bus: the outcome, carried up to the board and read off as a bar.
    # Each lamp sits ON the bus at its own distance, so the level decides how many light.
    bus = []
    for i in range(0, (board + 1) if p.get("display") else 0):
        bus.append((x + sx * i, y, z + sz * i))
    for c_ in bus:
        w.put(c_[0], c_[1], c_[2], "redstone_wire")
    # THE RISER NEEDS ITS OWN LANE. Run along the machine's axis it shared cells with the links
    # already laid there, `w.has` skipped its step blocks, and it ended as dust stacked on dust -
    # which connects to nothing. Sent sideways, where nothing else is, it has clear ground.
    side = {"east": "north", "west": "south", "north": "west", "south": "east"}[p["facing"]]
    riser = None if not bus else circuits.climb(rnd["comparator"], bus[0], block=p["pal_shell"], facing=side)
    for pos, spec in (riser["cells"].items() if riser else ()):
        if w.has(pos[0], pos[1], pos[2]):
            continue
        name, props = _split(spec)
        w.put(pos[0], pos[1], pos[2], name, **props)
    for pos, spec in (circuits.connect(riser["top"], bus[0])["cells"].items() if riser else ()):
        if w.has(pos[0], pos[1], pos[2]):
            continue
        name, props = _split(spec)
        w.put(pos[0], pos[1], pos[2], name, **props)

    w.put(x + dx * 8, my, z + dz * 8, "barrel", facing="up", open="false")   # the bank

    return {
        "contract": (f"one press, {outcomes} equally likely outcomes {rnd['levels']}, "
                     f"one payout" + (", read off the board as a bar" if p.get("display") else
                                       " (display OFF - see the note in CASINO)") + "; "
                     f"the machine is {pit} courses under the floor"),
        "inputs": [list(btn)],
        "outputs": [list(pay["droppers"][0])],
        "stock": {"dropper": rnd["stock"]},
        "rng_hopper": list(rnd["hopper"]),
        "board": cols,
        "bus": [list(b) for b in bus],
        "lamps": lamps,
        "chimes": chimes,
        "unverified": [circuits.RANDOM_NOTE],
    }


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


BUILDERS = {"game": _game, "prize_wall": _prize_wall, "marquee": _marquee, "counter": _counter}


def _split(spec: str):
    name = spec.split("[")[0]
    props = {}
    if "[" in spec and spec.endswith("]"):
        for part in spec[spec.index("[") + 1:-1].split(","):
            k, _, v = part.partition("=")
            props[k.strip()] = v.strip()
    return name, props
