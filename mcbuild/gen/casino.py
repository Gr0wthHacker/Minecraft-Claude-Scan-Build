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

import math

from . import circuits, conceal
from .canvas import Canvas
from .vertical import Ctx, World

# DERIVED, NOT CHOSEN: `palette.affordable_like` run on the reference's own palette, gated on
# cheap + witnessed on this server + not functional. Distance from the reference colour in
# brackets. The board colours needed no substitution at all - they were already cheap.
#
# **`floor` AND `trim` ARE THE ROOM'S FLOOR, NOT A TRIM COURSE - WOOL DOES NOT BELONG THERE.**
# `_room` puts `floor` at the border and `trim` in the field (`_hall` reuses `trim` as its own
# grid line, also in the floor course), so both of these were wool a player stands on rather than
# wool on a wall or a rug. `stone` and `polished_blackstone_bricks` keep the same DEFAULT ladder
# `quartz_block -> white_wool` and `black_stained_glass -> black_wool` were standing in for,
# just off the ground: 126 and 45, both cheap-or-ok, both nowhere near this server's currency.
PALETTE = {
    "floor": "stone",               # was white_wool (quartz_block stand-in) - now the ground
    "trim": "polished_blackstone_bricks",   # was black_wool (black_stained_glass stand-in)
    "accent": "yellow_wool",        # yellow_stained_glass (73 - hue, not distance) - NOT ground;
                                     # see `_button`/`_game_common`/`_wheel` for where it moved off
    "shell": "smooth_stone",
    "board": ["red_wool", "blue_wool", "green_wool", "pink_wool", "cyan_wool",
              "light_blue_wool", "orange_wool", "lime_wool"],
    "carpet": "red_carpet",
    # The relief vocabulary the download corpus says we are seven times short of. Stone brick
    # stairs against smooth stone is a value step of about 30 - visible, and cheap.
    "stair": "stone_brick_stairs",
    "pillar": "deepslate_bricks",   # 71 luminance against smooth stone's 159: the one real line
    "tile": "stone",                # 126 against smooth stone's 159: a quiet checker, not a stripe
    # THE AISLE IS A FLOOR MATERIAL, NOT A CARPET LAID ON ONE (`_hall`'s own docstring) - so it
    # was never a place for wool either. red_nether_bricks reads warm-dark the way red_wool did,
    # in the floor course, cheap tier, no colour left standing on the ground.
    "aisle": "red_nether_bricks",   # was red_wool
    "canopy": ["yellow_wool", "white_wool"],   # the booth awning; a land's skin overrides this
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
    "width": 40,                # hall only: the building's footprint
    "depth": 40,
    "gate": 3,                  # hall only: how wide the way in is
    # ONE COURSE UNDER THE FLOOR, NOT SIX. The reference puts its machines deep, and it can:
    # its displays are driven by decoded booleans. Ours reads the roll's own LEVEL, and a level of
    # 4 reaches four blocks - a six-course pit eats the number before it arrives. Shallow, with the
    # lamps set into the floor, is a lit floor panel and needs no journey at all.
    "pit": 2,
    "sound": True,              # note blocks. Expensive here, so it can be switched off
    "title": None,              # the room's name on the door sign; the plan passes the module's
    "room": True,               # build the enclosing room. Off = the old open bay.
    # BOOTH SWAPS THE SEALED CASINO ROOM FOR AN OPEN FAIRGROUND SHOPFRONT - see `_booth` below.
    # A theme-park sideshow must be watched being played FROM THE STREET; a casino floor must
    # not. Off by default so the casino theme itself never moves.
    "booth": False,
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


# ------------------------------------------------------------------ a game in a THEME PARK
#
# The six verified games are used twice: in the casino, and as MIDWAY SIDESHOWS in the three
# theme-park zones. A Hoopla stall on a bright fairground should not be built out of the casino's
# black-and-white; it should wear the land it stands in, or the zone reads as a casino with a
# ferris wheel parked outside it.
#
# **THE LADDER IS MEASURED ACROSS FAMILIES, AND IT IS THE WHOLE POINT OF THIS TABLE.** This repo
# concluded three separate times that the economy has no value contrast, and every one of those
# measurements was taken INSIDE one material family, where a ladder cannot exist by construction -
# a family is one material shown four ways, and dressing a stone does not change how much light it
# returns. Each skin below is field / shell / pillar with every adjacent pair at least 15 apart in
# luminance, which is about where a trim course stops being a line:
#
#   midway     diorite 188 · stone_bricks 122 · blackstone 38               steps  66,  84
#   frontier   spruce_planks 89 · cobblestone 127 · spruce_log 41           steps  38,  86
#   hollow     tuff 108 · deepslate_bricks 71 · polished_blackstone 45      steps  37,  26
#
# `tests/test_casino.py` measures it rather than trusting this comment.
#
# **`floor` USED TO BE THE ONLY WOOL A PLAYER STOOD ON, AND IT WAS TWICE OVER.** It is the ROOM'S
# OWN FLOOR (`_room`'s border ring, `_wheel`'s felt) - not a wall, not a rug - so `white_wool` and
# `black_wool` here were ground. `diorite` and `tuff` keep the ladder above; the field (`trim`)
# and the corner posts (`pillar`) move with it for midway, where both were ALSO wool doing the
# same job - `_hall` reuses `pillar` as its own floor grid line. `aisle` is the same fix again:
# `_hall`'s own docstring is explicit that it is "a floor material, not a carpet laid on one".
# `carpet` and `accent` are NOT touched here - a rug on top of the floor and a game's own colour
# identity are exactly the "wool for other things" this economy is fine with; see `_game_common`,
# `_button` and `_wheel` for where the accent colour moved OFF the floor and onto the rug alone.
#
# `canopy` is the booth awning's two stripe tones - reused from `gen/park.py::LANDS` for midway
# and frontier so a sideshow's tent matches every other striped canopy in its zone, EXCEPT on
# hollow: park's own hollow canopy is `["black_wool", "deepslate_bricks"]`, and the second of
# those IS this land's `shell` (the booth's own wall block) - a stripe that equals the wall draws
# nothing. Hollow's all-black palette is exactly the one the panel called "nearly featureless", so
# its awning needs the biggest gap of the three: `light_gray_wool`/`white_wool` against
# `deepslate_bricks` (71) measure 70.5 and 164.6 apart - a pale ghost-tent over a dark booth,
# which is also the one place on this island bone-pale wool reads as intentional rather than as a
# quartz substitute.
LAND_SKIN = {
    "midway": {
        "floor": "diorite", "shell": "stone_bricks", "pillar": "blackstone",
        "trim": "blackstone", "accent": "yellow_wool", "stair": "stone_brick_stairs",
        "tile": "stone", "carpet": "red_carpet", "aisle": "red_nether_bricks",
        "canopy": ["red_wool", "white_wool"],
    },
    "frontier": {
        "floor": "spruce_planks", "shell": "cobblestone", "pillar": "spruce_log",
        "trim": "stone_bricks", "accent": "orange_wool", "stair": "spruce_stairs",
        "tile": "stone", "carpet": "brown_carpet", "aisle": "stripped_oak_log",
        "canopy": ["spruce_planks", "stripped_oak_log"],
    },
    "hollow": {
        "floor": "tuff", "shell": "deepslate_bricks",
        "pillar": "polished_blackstone_bricks", "trim": "polished_blackstone_bricks",
        "accent": "purple_wool", "stair": "polished_blackstone_brick_stairs",
        "tile": "cobbled_deepslate", "carpet": "purple_carpet",
        "aisle": "cracked_polished_blackstone_bricks",
        "canopy": ["light_gray_wool", "white_wool"],
    },
}


def _skin(p: dict) -> dict:
    """Apply a land's skin over the casino palette, if one was asked for.

    The BOARD is deliberately left alone. It is the readout a player looks at to see which
    outcome came up, so its colours are doing a job rather than setting a mood, and repainting
    them in a land's own two tones would be repainting the instrument to match the wall.
    """
    land = p.get("land")
    if not land:
        return p
    if land not in LAND_SKIN:
        raise ValueError(f"unknown land {land!r}; have {sorted(LAND_SKIN)}")
    out = dict(p)
    for k, v in LAND_SKIN[land].items():
        # An explicit `pal_x` in the config still wins - the skin is a default, not an override.
        if p.get(f"pal_{k}") == PALETTE.get(k):
            out[f"pal_{k}"] = v
    return out


# WHAT EACH GAME'S SIGN SAYS. Four lines is the whole format, so every word has to earn its place:
# what to do, what you see, what the odds are. THE ODDS ARE ON THE SIGN because this project
# refuses to build a game whose distribution it cannot state - `RNG_MIXES` holds only the two item
# mixes with a measured uniform result, and a house that will not print its odds is a house that
# does not know them.
# FIFTEEN CHARACTERS IS THE LINE. A sign renders about that much before it clips, so a line that
# reads well in a python file - "lamps show your roll" is twenty - is a line cut off mid-word in
# game. `_copy` asserts the limit rather than trusting the eye, because the failure only shows up
# in a screenshot after the build is placed.
SIGN_WIDTH = 15

SIGN_COPY = {
    ("high_roller", 3): ["press to roll", "lamps = roll", "1 . 2 . or 4", "free to play"],
    ("high_roller", 2): ["press to roll", "lamps = roll", "1 or 3", "free to play"],
    ("double_or_none", 3): ["press to roll", "roll 4 to win", "1 in 3", "pays 1 prize"],
    ("double_or_none", 2): ["press to roll", "roll 3 to win", "1 in 2", "pays 1 prize"],
    ("lucky_number", 3): ["press to roll", "hit exactly 2", "not 1, not 4", "1 in 3"],
    ("lucky_number", 2): ["press to roll", "hit exactly 1", "the LOW one", "1 in 2"],
    ("duel", 3): ["you vs house", "high roll wins", "ties go to you", "6 in 9"],
    ("duel", 2): ["you vs house", "high roll wins", "ties go to you", "3 in 4"],
}


# **EACH MECHANIC GETS ITS OWN COLOUR - CARRIED BY THE CARPET, NOT BY THE FLOOR IT SITS ON.** The
# circuits differ and a player cannot see a circuit; what they see from the aisle is a row of
# doorways, and the rug in each one is what says which room this is. `accent` used to ALSO become
# the room's own border course (`_game_common`) and the button's floor pad (`_button`, `_wheel`) -
# wool standing in as ground, twice over. Both now stay the land's own stone; only the carpet, a
# genuine floor COVERING rather than the floor itself, still carries the colour.
KIND_ACCENT = {
    "high_roller":    {"accent": "yellow_wool", "carpet": "yellow_carpet"},
    "double_or_none": {"accent": "red_wool", "carpet": "red_carpet"},
    "lucky_number":   {"accent": "lime_wool", "carpet": "lime_carpet"},
    "duel":           {"accent": "light_blue_wool", "carpet": "light_blue_carpet"},
    "wheel":          {"accent": "purple_wool", "carpet": "purple_carpet"},
}


def _copy(kind, outcomes):
    lines = SIGN_COPY.get((kind, int(outcomes)), ["press to roll", "", "", ""])
    for ln in lines:
        assert len(ln) <= SIGN_WIDTH, f"sign line {ln!r} is {len(ln)} chars, over {SIGN_WIDTH}"
    return lines

_STEP = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
_BACK = {"north": "south", "south": "north", "east": "west", "west": "east"}


def _busy(ctx, x, y, z) -> bool:
    return ctx is not None and ctx.occupied(x, y, z)


def build(cfg: dict, donors=None) -> Canvas:
    p = _skin({**CASINO, **cfg})
    if not p.get("at"):
        raise ValueError("casino needs params.at = [x, y, z] of the play floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown casino kind {p['kind']}; have {sorted(BUILDERS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    # **COVER THE WIRING.** One pass for every kind rather than a lid each: the rule is the same
    # for all of them, and a per-kind lid is a per-kind way to forget one. See `gen/conceal.py`.
    hidden = conceal.conceal(w, p["pal_shell"], protect=[tuple(c) for c in meta.get("stand", ())])

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
        "concealed": hidden["placed"],
        "visible_redstone": len(hidden["left"]),
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
    # **THE PULSE'S DELAY LEG GOES ON THE SIDE THE BUTTON DOES NOT COME DOWN.**
    #
    # `_button` sits at `sx * (width // 2)` - the negative perpendicular - and `pulse`'s default
    # leg is on that same side. On a 5-wide game the button's descent ran ORTHOGONALLY ADJACENT to
    # the leg for three cells, which is one dust network: a held button parked a permanent 15 on
    # the subtract's side input, the monostable never opened, the randomiser's dropper was never
    # triggered, its hopper never received an item, and the comparator read 0 for ever.
    # `double_or_none` and `lucky_number` both shipped that way and could not pay at any odds.
    # `high_roller` is 6 wide, which put its button one cell further out, and it worked - the
    # difference between a machine that runs and one that does not was a single `width` value.
    #
    # Nothing could see it. The states are legal, the run is connected, the audit is clean, no
    # cell is shared, and every test drove the hopper with `Circuit.fill` - which STATES a roll
    # rather than rolling one, so the whole INPUT half of both machines was unexercised.
    # `test_a_press_actually_rolls_the_dice` is the assertion that was missing, and it is
    # entity-free: a dropper firing is an EDGE, which the simulator does model.
    pulse = circuits.pulse((x - dx * 5, y - 1, z - dz * 5), length=2, facing=p["facing"],
                           side=-1)
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
    out = {p["pal_floor"], p["pal_shell"], p["pal_trim"], p["pal_accent"], p["pal_carpet"],
           p["pal_stair"], p["pal_pillar"]}
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


# ---------------------------------------------------------------------- the room
#
# **A GAME IS A ROOM, NOT A PLATFORM.** The first casino built a floor, one back wall and a trim
# line per game and scattered 29 of them across the plot - Jack's verdict was "random platforms of
# shit", and it was the correct one. Nothing told you what a machine was, how to play it, or what
# it paid, and nothing joined one to the next.
#
# What makes voxels read as ARCHITECTURE is regularity and openings - this project settled that on
# the void tower, where a jagged ruin was rejected on sight and a plain regular one with a door and
# window slits worked immediately. So a room here is deliberately ordinary: four walls, one
# doorway, a ceiling, a skirting, a cornice, corner pilasters and a light. The interest comes from
# the ORDER and from the signs, not from novelty.
#
# The palette is the cheap value ladder this project measured across families rather than within
# one: white_wool 236 . smooth_stone 159 . stone 126 . deepslate_bricks 71 . black_wool 21 - 215
# luminance in five cheap stops, against the 51 we spent years calling our only contrast.

ROOM_H = 5              # floor to ceiling: 4 clear courses, which is a room rather than a corridor
# **A GAME ROOM IS A SHOPFRONT, NOT A CELL.** Built with a two-wide door the casino was eighteen
# sealed grey cubes: you could not tell one from another, could not see a game being played, and
# had no reason to walk into any of them. A gaming floor is open bays you look INTO from the
# aisle - the wall survives as a frame and a lintel, which is what carries the sign.
DOOR_W = 4


def _rect(width, depth):
    """The room's footprint as (i, d) pairs, one course of wall thickness outside the bay."""
    return [(i, d) for i in range(-2, width + 2) for d in range(-1, depth + 1)]


def _edge(i, d, width, depth):
    return i in (-2, width + 1) or d in (-1, depth)


def _room(w, p, x, y, z, dx, dz, sx, sz, width, depth, title, lines):
    """Four walls, a door, a ceiling and two signs. Returns the door's centre cell."""
    def at(i, d, h=0):
        return (x + sx * i - dx * d, y + h, z + sz * i - dz * d)

    door_i = max(0, width // 2 - DOOR_W // 2 + 1)
    doors = {door_i + k for k in range(DOOR_W)}

    for (i, d) in _rect(width, depth):
        # FLOOR. A field with a carpet runner down the middle, so the room has a direction: you
        # walk in on the red line and it takes you to the machine.
        #
        # THE CARPET GOES ON TOP OF THE FLOOR, NOT INSTEAD OF IT. Laid in the floor course it had
        # nothing under it and every room shipped six FLOATING carpets - rule 9, and the audit
        # caught it exactly as it is supposed to.
        # **A CASINO IS DARK WITH BRIGHT TRIM, NOT A WHITE BOX.** Built the other way round -
        # white_wool field, smooth stone walls, smooth stone ceiling - the render was a white
        # room with a red line in it, which is a bathroom. The field is the dark end of the
        # cheap ladder (black_wool 21), the border and the cornice are the bright end
        # (white_wool 236), and the walls sit between them at smooth_stone 159. That is the
        # 215-point value range this economy has across families, used as it was measured.
        border = i in (-2, width + 1) or d in (-1, depth)
        w.put(*at(i, d), p["pal_floor"] if border else p["pal_trim"])
        if i in (door_i, door_i + 1) and not border:
            w.put(*at(i, d, 1), p["pal_carpet"])

        if not _edge(i, d, width, depth):
            continue
        corner = i in (-2, width + 1) and d in (-1, depth)
        for h in range(1, ROOM_H):
            # THE DOORWAY IS LEFT EMPTY BY THE WALL LOOP, never punched afterwards. Building the
            # ring first and cutting a hole repaints cells that already exist - the void tower's
            # crenellations shipped as a plain drum for exactly this reason, and the code looked
            # perfectly correct.
            if d == depth and i in doors and h < 4:
                continue
            # CORNER PILASTERS in the dark brick, so the room has four vertical lines and does
            # not read as one continuous drum of stone.
            w.put(*at(i, d, h), p["pal_pillar"] if corner else p["pal_shell"])

    # CEILING, one plane, and DARK - a bright lid over a dark floor reads as a lightwell. A room
    # has a ceiling; a deck does not, which is a distinction the deck soffit's own notes settled
    # after a deck-wide "ceiling" came out as 25 lacy patches at six different heights.
    for (i, d) in _rect(width, depth):
        w.put(*at(i, d, ROOM_H), p["pal_pillar"])

    # SKIRTING and CORNICE: upside-down stairs under the ceiling, plain stairs at the floor. This
    # is the vocabulary the corpus says we are seven times short of, and it is what stops a wall
    # being a flat plane of one block.
    lean = {"east": "west", "west": "east", "north": "south", "south": "north"}
    for (i, d) in _rect(width, depth):
        if not _edge(i, d, width, depth):
            continue
        if d == depth and i in doors:
            continue
        face = _inward(i, d, width, depth, p["facing"])
        if face is None:
            continue
        w.put(*at(i, d, ROOM_H - 1), p["pal_stair"], facing=lean[face], half="top",
              shape="straight", waterlogged="false")

    # LIGHT. **A REDSTONE LAMP IS A DARK BLOCK UNTIL SOMETHING POWERS IT**, and two of them hung
    # in every room's ceiling wired to nothing - the circuit inspection said so on the first run.
    # A lantern hung from the ceiling needs no signal, costs an iron ingot and a torch, and is what
    # a room is lit with. Powering the lamps instead would be a second circuit per room to build,
    # verify and go wrong.
    for i in (0, width - 1):
        w.put(*at(i, depth // 2, ROOM_H - 1), "lantern", hanging="true", waterlogged="false")

    # THE SIGNS, which are the whole point of this pass. One over the door saying what the room
    # is, one inside saying how to play it and what the odds are.
    #
    # **A WALL SIGN GOES ON A WALL, IN THE CELL IN FRONT OF IT.** Written the obvious way these
    # were both wrong and a component count found it: the rules sign sat in the MIDDLE of the room
    # attached to nothing - eighteen single-cell strays, one per room - and the door sign was
    # placed INSIDE the wall plane, overwriting the lintel block it was supposed to hang on.
    #
    # `facing` is the direction the text FACES, which is away from the block it is fixed to.
    back = {"east": "west", "west": "east", "north": "south", "south": "north"}[p["facing"]]

    # Over the door, on the OUTSIDE face, where a shop sign goes - so it reads from the aisle.
    dsx, dsy, dsz = at(door_i, depth + 1, 4)
    w.put(dsx, dsy, dsz, "oak_wall_sign", facing=back, waterlogged="false")
    w.sign(dsx, dsy, dsz, front=[title, "", "", ""], colour="white", glowing=True)

    # The rules, on the BACK wall inside, facing whoever has just walked in. d=-1 is the far wall
    # (d counts toward the front), so the sign hangs in the first interior course, d=0.
    isx, isy, isz = at(door_i, 0, 2)
    w.put(isx, isy, isz, "oak_wall_sign", facing=back, waterlogged="false")
    w.sign(isx, isy, isz, front=list(lines)[:4])
    return (dsx, dsy, dsz)


def _inward(i, d, width, depth, facing):
    """Which way a wall cell's ROOM side faces - so a cornice stair leans into the room."""
    if d == depth:
        return {"east": "west", "west": "east", "north": "south", "south": "north"}[facing]
    if d == -1:
        return facing
    side = {"east": "north", "west": "south", "north": "west", "south": "east"}[facing]
    other = {"east": "south", "west": "north", "north": "east", "south": "west"}[facing]
    if i == -2:
        return other
    if i == width + 1:
        return side
    return None


# ---------------------------------------------------------------------- the fairground booth
#
# **A GAME IS A ROOM, NOT A PLATFORM - AND A SIDESHOW IS A SHOPFRONT, NOT A ROOM.** `_room` boxes
# a player in on purpose: four walls and one doorway is what makes a casino floor read as a
# casino floor. A midway sideshow needs the opposite - the whole point of Hoopla or Tin Can Alley
# is that you watch the game being played FROM THE STREET, the same reason `gen/park.py::_stall`
# gives a shop an open front. A visual review of the finished park found the six sideshow games
# (Hoopla, Lucky Dip, Tin Can Alley, Gold Panning, Fortune Wheel, The Reckoning) "stand bare with
# no booth/wall/sign, unlike the earlier 'casino became a building' work" - correct, because they
# were still built with `room: True`, which is the CASINO's room, not a fairground one.
#
# So this is not `_room` with a hole cut in it - it is `_stall`'s proven shape (a full back wall,
# thin corner POSTS rather than a solid side wall, a slab counter across the open front, a fascia
# board over the opening because an open front has nothing else to hang a sign from) adapted to
# `_room`'s own `at(i, d, h)` convention, so the verified machine underneath - the pit, the wiring,
# the payout - never has to move by one cell.
BOOTH_H = ROOM_H         # counter to awning: the same clearance a casino room gives floor-to-ceiling


def _booth(w, p, x, y, z, dx, dz, sx, sz, width, depth, title, lines):
    """Open front, short corner posts, a back wall carrying the prize shelf and the rules, a
    slab counter, a fascia over the opening, and a striped awning. Returns the fascia sign's
    position, matching `_room`'s return.
    """
    def at(i, d, h=0):
        return (x + sx * i - dx * d, y + h, z + sz * i - dz * d)

    door_i = max(0, width // 2 - DOOR_W // 2 + 1)
    # A LAND WITH NO SKIN STILL GETS TWO TONES: fall back to the casino's own accent/trim rather
    # than crash, so `booth=True` never depends on `land` being set.
    canopy = p.get("pal_canopy") or [p["pal_accent"], p["pal_trim"]]

    # FLOOR: the same field-and-aisle as `_room`, so the pit floor `_game_common` lays afterward
    # still lines up, and the carpet still leads the eye from the counter to the button.
    for (i, d) in _rect(width, depth):
        border = i in (-2, width + 1) or d in (-1, depth)
        w.put(*at(i, d), p["pal_floor"] if border else p["pal_trim"])
        if i in (door_i, door_i + 1) and not border:
            w.put(*at(i, d, 1), p["pal_carpet"])

    # THE BACK WALL, full height and solid - what the prize shelf and the rules sign hang on.
    for i in range(-2, width + 2):
        for h in range(1, BOOTH_H):
            w.put(*at(i, -1, h), p["pal_shell"])

    # CORNER POSTS, NOT A SIDE WALL. A run of `pal_shell` between them would rebuild `_room`'s own
    # sealed box; a single column per side is what lets a passer-by see past it into the booth,
    # exactly the shape `_stall` already proved reads as a shopfront rather than a wall.
    for d in range(-1, depth + 1):
        for h in range(1, BOOTH_H):
            w.put(*at(-2, d, h), p["pal_pillar"])
            w.put(*at(width + 1, d, h), p["pal_pillar"])

    # THE COUNTER: a slab top across the open front, at leaning height, so the opening is a
    # serving hatch rather than a hole in the floor.
    slab = p["pal_stair"].replace("_stairs", "_slab")
    for i in range(-1, width + 1):
        w.put(*at(i, depth, 0), p["pal_trim"])
        w.put(*at(i, depth, 1), slab, type="bottom", waterlogged="false")

    # THE PRIZE SHELF: alternating board colours on the wall face just inside the back wall, the
    # way the reference casino's own display boards are built - a booth reads as "prizes" from
    # thirty blocks before anyone is close enough to read the sign. It is drawn BEFORE the rules
    # sign, deliberately, so the sign wins the one cell they share (the deck soffit's rule: decide
    # order once, and the later placement is the one that survives).
    board = p["pal_board"]
    for k, i in enumerate(range(door_i - 1, door_i + DOOR_W + 1)):
        if not (-1 <= i <= width):
            continue
        w.put(*at(i, 0, 2), board[k % len(board)])
        w.put(*at(i, 0, 3), board[(k + 1) % len(board)])

    # THE FASCIA: a solid board across the whole opening at awning height. An open front has no
    # wall to hang a nameplate from, which is exactly the failure `_stall`'s own docstring warns
    # about - "an open front has no wall to attach one to".
    for i in range(-1, width + 1):
        w.put(*at(i, depth, BOOTH_H - 1), p["pal_trim"])

    # THE AWNING: two tones alternating, one course above the fascia, projecting over the back
    # wall, the posts AND the counter into the aisle - roof over the interior, canopy over the
    # street, one plane doing both. The alternation is what the corpus calls a STRIPE rather than
    # a lid; a single colour here is a roof, not a fairground tent.
    for i in range(-2, width + 2):
        for d in range(-1, depth + 2):
            w.put(*at(i, d, BOOTH_H), canopy[0] if i % 2 == 0 else canopy[1])

    # LIGHT under the awning, near the counter, so the board reads after dark from the street.
    for i in (0, width - 1):
        w.put(*at(i, depth - 1, BOOTH_H - 1), "lantern", hanging="true", waterlogged="false")

    # THE FASCIA SIGN, mounted on the fascia board and facing OUT into the aisle - the game's
    # name, read the way a shop sign is read, from the street rather than from inside the booth.
    back = {"east": "west", "west": "east", "north": "south", "south": "north"}[p["facing"]]
    dsx, dsy, dsz = at(door_i, depth + 1, BOOTH_H - 1)
    w.put(dsx, dsy, dsz, "oak_wall_sign", facing=back, waterlogged="false")
    w.sign(dsx, dsy, dsz, front=[title, "", "", ""], colour="white", glowing=True)

    # THE RULES, on the back wall inside, facing whoever has walked up to the counter.
    isx, isy, isz = at(door_i, 0, 2)
    w.put(isx, isy, isz, "oak_wall_sign", facing=back, waterlogged="false")
    w.sign(isx, isy, isz, front=list(lines)[:4])
    return (dsx, dsy, dsz)


# The old open bay, kept because `marquee`, `prize_wall` and `counter` are FURNITURE rather than
# rooms - they line a corridor and must not each be boxed in.
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
    # THE PAD IS FLOOR, NOT AN ACCENT - it is the same course a player stands on, so it takes the
    # land's own field material rather than the KIND's wool. The button itself is already visibly
    # distinct; the pad does not need to be a coloured tile as well.
    w.put(b[0], b[1] - 1, b[2], p["pal_trim"])
    return b


def _game_common(w, p, ctx, width):
    x, y, z = (int(v) for v in p["at"])
    dx, dz = _STEP[p["facing"]]
    sx, sz = -dz, -dx
    pit = max(4, int(p["pit"]))
    outcomes = int(p["outcomes"])
    if p.get("room", True):
        skin = KIND_ACCENT.get(p["kind"])
        if skin:
            # WOOL OFF THE GROUND: `pal_floor` used to become the KIND's own accent wool here,
            # which is what made every game's border course a coloured wool tile. The carpet
            # alone carries the game's identity now - the floor stays the land's own material.
            p = {**p, "pal_carpet": skin["carpet"]}
        title = p.get("title") or p["kind"].replace("_", " ").upper()
        # BOOTH SWAPS THE SHELL, NOTHING ELSE. `_booth` and `_room` share `at(i, d, h)`, `width`,
        # `depth`, `title` and `lines`, so the button and the machine placed below need not know
        # or care which one built the walls around them.
        shell = _booth if p.get("booth") else _room
        shell(w, p, x, y, z, dx, dz, sx, sz, width, 4,
              str(title).upper()[:15], _copy(p["kind"], outcomes))
    else:
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
    # **THE BAR IS ONE INSTRUMENT, SO IT IS ONE COLOUR.** The caps used to cycle through an
    # eight-colour board list, which on a four-lamp bar means four arbitrary colours - and it is
    # where the stray three pink and three blue wool in the whole casino came from. A reading
    # instrument in four unrelated colours reads as confetti, not as a scale.
    #
    # AND THE CAP IS FLOOR, NOT A DISPLAY COLOUR - it sits directly over the lamp, in the SAME
    # course as the rest of the play floor, so it was wool standing in as ground exactly like the
    # room's own border once did. It takes the land's field material now; the bar still reads by
    # which lamps are LIT, not by what colour is painted over them.
    cap = p["pal_trim"]
    for lamp in display["lamps"]:
        w.put(lamp[0], lamp[1] + 1, lamp[2], cap)
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
    # **THE BARREL IS THE CONNECTOR, SO `payout`'s OWN INPUT DUST IS DEAD WEIGHT.** The boost
    # drives the barrel, the barrel is a solid block behind the dropper, and a strongly powered
    # block fires the dropper beside it - that is the mechanism, and it is why moving the barrel
    # "to avoid a collision" once stopped every payout at every set of odds. The dust cell
    # `payout` lays under its dropper is therefore never reached; left standing it is an orphan,
    # which is what `circuit.inspect` reported on the duel. It becomes the dropper's floor.
    w.put(pay["in"][0], pay["in"][1], pay["in"][2], p["pal_shell"])
    return {"contract": f"press once; pays ONLY on a roll of {win} (1 in {g['outcomes']})",
            "inputs": [list(g["btn"])], "outputs": [list(pay["droppers"][0])],
            "rng_hopper": list(g["rnd"]["hopper"]), "win_level": win,
            "stock": {"dropper": g["rnd"]["stock"]},
            "reads": "threshold", "unverified": [circuits.RANDOM_NOTE]}



def _lucky_number(w: World, p: dict, ctx) -> dict:
    """Hit ONE number exactly. Not "roll high enough" - a different bet with different tension.

    **THE FOUR GAMES WE SHIPPED WERE TWO GAMES.** Measured cell-for-cell, High Roller and Coin Toss
    were 99.2% identical and One In Three and Even Money 97.8%: `threshold` pays on a maximum, and
    a maximum is the same game whatever number you put in it. `circuits.window` is the first
    mechanic here that is not a maximum - an AND-NOT built from a subtract comparator - so the
    middle of the mix can win and the top can lose, which is a bet a player reads differently.
    """
    g = _game_common(w, p, ctx, width=5)
    levels = circuits.RNG_MIXES[g["outcomes"]]["levels"]
    # THE MIDDLE of a three-outcome mix, the low of a two - never the maximum, or this is
    # `double_or_none` with more parts.
    target = levels[len(levels) // 2] if len(levels) > 2 else levels[0]
    cmp_ = g["rnd"]["comparator"]
    foot = (cmp_[0] + g["dx"], cmp_[1], cmp_[2] + g["dz"])
    gate = circuits.window(foot, target, target + 1, facing=p["facing"])
    # **THE BOOST GOES AT `next`, NOT ONE STEP ALONG THE RUN.** One step along is the cell beside
    # the gate's own SIDE input, which carries the HIGH boolean at a full 15 - so a consumer put
    # there reads the signal the gate exists to reject and the exact-value bet silently becomes
    # "roll at least this". `window` names the safe cell so nobody has to re-derive it.
    amp = circuits.boost(gate["next"], facing=gate["face"])
    pay = circuits.payout((amp["out"][0] + g["dx"], amp["out"][1], amp["out"][2] + g["dz"]),
                          count=1, facing=p["facing"])
    _lay(w, p, (gate, amp, pay))
    d0 = pay["droppers"][0]
    bx, bz = d0[0] - g["dx"], d0[2] - g["dz"]
    if not w.has(bx, d0[1], bz):
        w.put(bx, d0[1], bz, "barrel", facing="up", open="false")
    # **THE BARREL IS THE CONNECTOR, SO `payout`'s OWN INPUT DUST IS DEAD WEIGHT.** The boost
    # drives the barrel, the barrel is a solid block behind the dropper, and a strongly powered
    # block fires the dropper beside it - that is the mechanism, and it is why moving the barrel
    # "to avoid a collision" once stopped every payout at every set of odds. The dust cell
    # `payout` lays under its dropper is therefore never reached; left standing it is an orphan,
    # which is what `circuit.inspect` reported on the duel. It becomes the dropper's floor.
    w.put(pay["in"][0], pay["in"][1], pay["in"][2], p["pal_shell"])
    odds = len(levels)
    return {"contract": f"press once; pays ONLY on exactly {target} (1 in {odds})",
            "inputs": [list(g["btn"])], "outputs": [list(pay["droppers"][0])],
            "rng_hopper": list(g["rnd"]["hopper"]), "win_level": target,
            "stock": {"dropper": g["rnd"]["stock"]},
            "reads": "window", "unverified": [circuits.RANDOM_NOTE]}


def _duel(w: World, p: dict, ctx) -> dict:
    """TWO rolls, side by side: yours against the house's. You win ties.

    A comparator in COMPARE mode passes its back signal when back >= side, so the machine needs
    both rolls DECIDED where they are made - which is the analog rule this whole file turns on,
    used as a feature rather than fought. Out of the three-outcome mix there are nine equally
    likely pairs and six have A >= B, so the odds are 2 in 3 and countable, which is this file's
    bar for shipping a game at all.
    """
    g = _game_common(w, p, ctx, width=6)
    levels = circuits.RNG_MIXES[g["outcomes"]]["levels"]
    dx, dz, sx, sz = g["dx"], g["dz"], g["sx"], g["sz"]

    # THE GATE SITS ON THE PLAYER'S OWN COMPARATOR, and the HOUSE'S COMPARATOR SITS ON ITS SIDE.
    #
    # **AN ANALOG VALUE CANNOT TRAVEL** - the rule this whole file turns on - and the first version
    # of this game ignored it for the second roll: the house's randomiser was placed on a lane of
    # its own and `_link`ed to the comparator's side. Dust decays, so the side read 0, and
    # `A >= 0` is true for every A. It paid on all nine combinations and looked like a working
    # machine doing it.
    #
    # A comparator reads its BACK from the cell behind it and its SIDE from the cells beside it,
    # both at whatever level those cells hold. So both rolls have to be produced ADJACENT to the
    # gate, and the geometry is derived from that rather than chosen.
    cmp_ = g["rnd"]["comparator"]
    gate = circuits.duel((cmp_[0] + dx * 2, cmp_[1], cmp_[2] + dz * 2), facing=p["facing"])
    back, side = gate["back"], gate["side"]
    _lay(w, p, (gate,))
    if not w.has(*back):
        w.put(back[0], back[1], back[2], "redstone_wire")   # the player's own output cell

    # A randomiser's comparator sits at pos + (dx, -1) and fires along `facing`, so placing the
    # house two cells back along that line puts its output exactly on the gate's side.
    house = circuits.randomiser((side[0] - dx * 2, side[1] + 1, side[2] - dz * 2),
                                outputs=g["outcomes"], facing=p["facing"])
    _lay(w, p, (house,))
    if not w.has(*side):
        w.put(side[0], side[1], side[2], "redstone_wire")
    # **ONE PULSE FIRES BOTH, AND THE HOUSE'S FEED IS A CORNER RATHER THAN A ROUTE.**
    #
    # It used to be a second `_link` all the way from the pulse, and it did not arrive: the last
    # cell of that run lands on the PLAYER's own randomiser dropper, `_link` correctly refuses to
    # overwrite a component, and what was left sat one diagonal short of the house's input. A
    # diagonal is not a connection, so the house's dropper was never triggered, its hopper stayed
    # empty, the gate's side read 0 - and `A >= 0` is true for every A, which is the machine
    # paying on all nine combinations. That is the fault this game's own docstring says it fixed;
    # it was fixed at the gate and reintroduced at the feed, and nothing could see it because the
    # simulator has no entities and the test STATES both rolls rather than rolling them.
    #
    # The two inputs are one cell apart. Joining them where they already are is two cells of dust
    # in building axes, with no route to go wrong.
    # ...and it ENDS IN A REPEATER, because by the time the pulse reaches the player's own input
    # the level is down to 2 and two more cells of dust is nothing at all. The repeater sits where
    # `house["in"]` names, so its front is the house's dropper: a full 15 straight into it.
    rin = g["rnd"]["in"]
    step = 1 if (house["in"][0] - rin[0]) * sx + (house["in"][2] - rin[2]) * sz > 0 else -1
    corner = (rin[0] + sx * step, rin[1], rin[2] + sz * step)
    if not w.has(*corner):
        w.put(corner[0], corner[1], corner[2], "redstone_wire")
    if not w.has(*house["in"]):
        w.put(house["in"][0], house["in"][1], house["in"][2], "repeater",
              facing=p["facing"], delay="1", locked="false", powered="false")
    for cell in (corner, house["in"]):
        if not w.has(cell[0], cell[1] - 1, cell[2]):
            w.put(cell[0], cell[1] - 1, cell[2], p["pal_shell"])

    amp = circuits.boost((gate["out"][0] + dx, gate["out"][1], gate["out"][2] + dz),
                         facing=p["facing"])
    pay = circuits.payout((amp["out"][0] + dx, amp["out"][1], amp["out"][2] + dz),
                          count=1, facing=p["facing"])
    _lay(w, p, (amp, pay))
    d0 = pay["droppers"][0]
    bx, bz = d0[0] - dx, d0[2] - dz
    if not w.has(bx, d0[1], bz):
        w.put(bx, d0[1], bz, "barrel", facing="up", open="false")
    # **THE BARREL IS THE CONNECTOR, SO `payout`'s OWN INPUT DUST IS DEAD WEIGHT.** The boost
    # drives the barrel, the barrel is a solid block behind the dropper, and a strongly powered
    # block fires the dropper beside it - that is the mechanism, and it is why moving the barrel
    # "to avoid a collision" once stopped every payout at every set of odds. The dust cell
    # `payout` lays under its dropper is therefore never reached; left standing it is an orphan,
    # which is what `circuit.inspect` reported on the duel. It becomes the dropper's floor.
    w.put(pay["in"][0], pay["in"][1], pay["in"][2], p["pal_shell"])
    n = len(levels)
    wins = sum(1 for a in levels for b in levels if a >= b)
    return {"contract": f"press once; you win ties - {wins} in {n * n}",
            "inputs": [list(g["btn"])], "outputs": [list(pay["droppers"][0])],
            "rng_hopper": list(g["rnd"]["hopper"]),
            "house_hopper": list(house["hopper"]),
            "stock": {"dropper": g["rnd"]["stock"], "house dropper": house["stock"]},
            "reads": "duel", "unverified": [circuits.RANDOM_NOTE]}


def _lay(w, mods_p, mods=None, over: bool = False, through=()):
    """Place a module's cells, never over something already standing.

    `over=True` relaxes that to STRUCTURE ONLY - the same rule `_link` runs under. A machine laid
    after the room it sits in has to be allowed through the room's own floor and trim, or its
    cells are dropped one at a time and it ships with holes in it. It is still never allowed over
    a component.

    `through` names extra blocks it may cut, for the case `_structural` cannot cover: the wheel's
    rim RAIL is an `oak_fence`, which is neither structure nor component, and it swallowed exactly
    one cell of the pulse's run - leaving the delay leg beside it orphaned and the machine's own
    monostable broken in the middle. A machine that crosses a railing needs a gap in the railing.
    """
    p, mods = mods_p, mods
    keep = (_structural(p) if over else set()) | set(through)
    for mod in mods:
        for pos, spec in mod["cells"].items():
            if w.has(pos[0], pos[1], pos[2]) and w.name(pos[0], pos[1], pos[2]) not in keep:
                continue
            name, props = _split(spec)
            w.put(pos[0], pos[1], pos[2], name, **props)
        for pos in mod["cells"]:
            if not w.has(pos[0], pos[1] - 1, pos[2]):
                w.put(pos[0], pos[1] - 1, pos[2], p["pal_shell"])



def _wheel(w: World, p: dict, ctx) -> dict:
    """THE COLOUR WHEEL: a SUNKEN bowl you look down into, three pockets, one lights per spin.

    **THIS IS THE FIRST GAME HERE WITH A DIFFERENT SHAPE, and that is the point.** Four verified
    mechanics in four identical booths are four identical rooms - the report was that the games
    "look like theyre identical", and a bar, a payout and a window all read as a button in a grey
    box. This is round, open, sunk into the floor and read from ABOVE, so it resembles none of them
    from the aisle.

    Mechanically it is a DECODER, which none of the others are: one roll, three outputs, exactly
    one live. That needs one comparator per pocket and they all read the SAME hopper -
    **A SPUR OFF THE SOURCE DUST DOES NOT WORK**, because dust adjacent to the comparator's output
    is already a level down and every gate is then off by one. A hopper has four horizontal sides;
    three comparators sit on three of them and each reads the container at full strength.

    **THE POCKET SITS AT ITS OWN GATE'S OUTPUT, AT THE SAME LEVEL.** Two earlier layouts failed for
    the same reason from opposite directions: lamps on a raised tabletop needed the signal routed
    up and over, and the three routes merged - one roll lit two pockets. Sinking the bowl to the
    machine's own course means every pocket is simply the cell next to its gate, there is no
    journey, and nothing can cross.

    **IT IS A COLOUR BET, NOT A NUMBER BET, and that is honest rather than decorative.** Three
    pockets is what three uniform outcomes buys, and `RNG_MIXES` holds only mixes whose
    distribution is measured. Red/green/black is a real roulette bet at odds we can state;
    thirty-seven numbered pockets would be a wheel whose odds we would be inventing.
    """
    x, y, z = (int(v) for v in p["at"])
    dx, dz = _STEP[p["facing"]]
    sx, sz = -dz, -dx
    # THE WHEEL NEVER WENT THROUGH `_room`, so it never picked up its own accent - its canopy
    # fallback used to come out High Roller yellow, a colour that means "this is a bar game" on
    # the one machine that is not one. (The button pad no longer takes this colour at all; see
    # the fix a few lines down - the ground stays stone whichever kind is asking.)
    skin = KIND_ACCENT.get("wheel")
    if skin:
        p = {**p, "pal_accent": skin["accent"]}
    outcomes = 3
    levels = circuits.RNG_MIXES[outcomes]["levels"]
    by = y - 1                                   # the bowl's floor, one course down

    # **THE PULSE IS SITED FROM THE BUTTON, NOT FROM A MAGIC TWELVE.** It used to be built here at
    # `x - dx*12`, before the bowl's radius was known - and the button, which IS derived (`r + 2`
    # off the hub), landed on top of it: the pulse's own first dust cell came out as the button's
    # accent pad and its `in` cell was orphaned in mid-air. The machine still fired, because a
    # floor button strongly powers the block under it and that block happened to be in the middle
    # of the pulse - so it worked by accident, left a stray the inspection reported, and would
    # have moved the moment the bowl changed size. Everything downstream of a derived radius must
    # be measured FROM that radius. The whole approach is built after `r` is known, below.
    rnd = circuits.randomiser((x - dx * 2, by + 1, z - dz * 2), outputs=outcomes,
                              facing=p["facing"])
    _lay(w, p, (rnd,))
    # **`rnd["in"]` IS NOT USED HERE, AND IT CANNOT BE.** It names the cell one step back along
    # `facing` from the dropper - which on this machine is directly ABOVE the west gate's own
    # comparator, and dust does not stand on a comparator. The dropper is fed from the free face
    # instead; see the approach below.

    hop = rnd["hopper"]
    # **THE THREE GATES ARE ARRANGED SO THEY CANNOT TOUCH, and the arrangement is SEARCHED rather
    # than chosen.** Each window occupies a 5x5 quadrant off the hub; with the perpendicular fixed
    # two of them always land in the same one, and the wheel's first build put two pockets in
    # adjacent cells with a third never firing. Opposite faces plus one, all taps outward, is the
    # first assignment with no shared cell - `test_the_wheels_three_gates_never_touch` pins it by
    # rebuilding the search, so a change to `window`'s footprint fails here rather than in game.
    # `south` is in the table because it is the FREE face - the one quadrant no gate reaches - and
    # the whole button approach is built along it. Derived from the same rotation as the gates, so
    # it cannot drift out of step with them at any orientation.
    rot = {"east": {"east": "east", "west": "west", "north": "north", "south": "south"},
           "west": {"east": "west", "west": "east", "north": "south", "south": "north"},
           "north": {"east": "north", "west": "south", "north": "west", "south": "east"},
           "south": {"east": "south", "west": "north", "north": "east", "south": "west"}}[
        p["facing"]]
    faces = [rot["east"], rot["west"], rot["north"]]
    # **CLEARANCE, NOT JUST NO OVERLAP.** The first search demanded only that the three gates share
    # no cell, and found an arrangement where gate 1's output sat ONE BLOCK from gate 4's dust:
    # adjacent dust is one network, so a roll of 4 pushed 15 into the level-1 pocket and lit two.
    # The north gate's taps point the other way, which is the nearest assignment with a real gap.
    tap_sides = [1, 1, -1]
    seg = ["red_wool", "green_wool", "black_wool"]
    # **EVERY GATE FIRST, THEN EVERY POCKET.** Built in one pass the first pocket's colour ring
    # was painted into cells the third gate had not reached yet, `_lay` then skipped them as
    # occupied, and the level-4 gate shipped with its subtract comparator replaced by red wool -
    # so a roll of 4 lit the level-1 pocket. Decoration laid before structure is decoration that
    # eats structure.
    pockets, gate_cells, plan = [], set(), []
    for face, sd, lvl, colour in zip(faces, tap_sides, levels, seg):
        fx, fz = _STEP[face]
        cmp_pos = (hop[0] + fx, hop[1], hop[2] + fz)
        if not w.has(*cmp_pos):
            w.put(cmp_pos[0], cmp_pos[1], cmp_pos[2], "comparator",
                  facing=face, mode="compare", powered="false")
        gate = circuits.window((cmp_pos[0] + fx, cmp_pos[1], cmp_pos[2] + fz),
                               low=lvl, high=lvl + 1, facing=face, side=sd)
        _lay(w, p, (gate,))
        gate_cells |= set(gate["cells"])
        # THE POCKET GOES AT `next`. Placed one step along the run it sat beside the gate's own
        # SIDE cell - the HIGH boolean, a full 15 - and lit on every roll at or above its level,
        # so all three pockets lit in turn and the wheel read as a thermometer, not a bet.
        plan.append((face, colour, gate["next"]))

    for face, colour, lamp in plan:
        fx, fz = _STEP[face]
        w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")
        # THE COLOUR OF THE POCKET, ringed round the lamp so the bet reads when it is dark - and
        # never over a cell another gate owns.
        for ox, oz in ((fx, fz), (-fz, -fx), (fz, fx)):
            c2 = (lamp[0] + ox, lamp[1], lamp[2] + oz)
            if not w.has(*c2) and c2 not in gate_cells:
                w.put(c2[0], c2[1], c2[2], colour)
        pockets.append(list(lamp))

    # THE BOWL, sized to whatever the machine turned out to need rather than guessed at, then a
    # rim and a rail at floor level so it reads as a table and nobody walks into it.
    span = [abs(c[0] - hop[0]) for c in gate_cells] + [abs(c[2] - hop[2]) for c in gate_cells]
    r = max(6, max(span) + 2)
    rim_cells = []
    for i in range(-r - 1, r + 2):
        for d in range(-r - 1, r + 2):
            cx, cz = hop[0] + i, hop[2] + d
            rr = i * i + d * d
            if rr <= r * r:
                if not w.has(cx, by - 1, cz):
                    w.put(cx, by - 1, cz, p["pal_trim"])       # the bowl's own floor
                if not w.has(cx, by, cz):
                    w.put(cx, by, cz, p["pal_floor"])          # the felt
            elif rr <= (r + 1) * (r + 1):
                w.put(cx, by, cz, p["pal_pillar"])             # the rim
                w.put(cx, by + 1, cz, "oak_fence")             # the rail you lean on
                rim_cells.append((i, d))

    # THE ROOF, only when asked for. The wheel is deliberately walless - a sunken bowl read from
    # above, per the docstring above - but a review of the finished park still called every
    # sideshow "bare with no booth/wall/sign", and an open table with nothing over it reads as
    # unfinished furniture even when its shape is doing real work. **NOT ONE GATE CELL MOVES**:
    # everything here is placed AFTER the machine, stands on the rim's own solid `pal_pillar`
    # cells (never floating, never a fifth free-standing post the audit would flag), and starts
    # two courses above the rail so the awning cannot be mistaken for part of the game.
    if p.get("booth") and rim_cells:
        canopy = p.get("pal_canopy") or [p["pal_accent"], p["pal_trim"]]
        step = max(1, len(rim_cells) // 4)
        for (ci, cd) in rim_cells[::step][:4]:
            for cy in range(by + 2, by + 5):
                w.put(hop[0] + ci, cy, hop[2] + cd, p["pal_pillar"])
        for i in range(-r - 1, r + 2):
            for d in range(-r - 1, r + 2):
                w.put(hop[0] + i, by + 5, hop[2] + d, canopy[0] if i % 2 == 0 else canopy[1])

    # **THE APPROACH COMES IN ON THE ONE FACE THAT HAS NO GATE, IN A STRAIGHT LINE, WITH NO
    # `connect` ANYWHERE IN IT.**
    #
    # Three gates radiate from the hub and each of the other three faces carries one, so any run
    # that crosses them merges with the very dust line whose DECAY the gate is measuring - and a
    # measuring line with 15 injected into it reports every roll as the highest. The old approach
    # came in along the machine's own axis, straight over the west gate, and got away with it by a
    # single cell of `climb` step block that happened to sit between the two dust runs. Shifting
    # the button by one exposed it instantly: two pockets lit on one roll.
    #
    # `rot["south"]` is the free face by construction - `faces` above takes east, west and north -
    # so the whole approach is one column in that direction, at the rim's own course, with the
    # felt underneath it as its floor. Nothing here is routed; every cell is an offset.
    ax, az = _STEP[rot["south"]]
    drop = rnd["dropper"]                      # what the pulse has to reach: a rising edge on it

    def out_at(k):
        return (drop[0] + ax * k, drop[1], drop[2] + az * k)

    btn_k = r + 3                              # outside the rim, where a player stands
    btn = out_at(btn_k)
    pad = (btn[0], btn[1] - 1, btn[2])
    # THE PAD IS FLOOR, NOT THE WHEEL'S ACCENT - `_button`'s own fix, restated here because the
    # wheel never goes through `_button` itself (its approach is radial, not the straight column
    # `_button` assumes). `pal_accent` stays wool for the canopy fallback below; the ground does
    # not.
    w.put(pad[0], pad[1], pad[2], p["pal_trim"])
    w.put(btn[0], btn[1], btn[2], "stone_button", face="floor",
          facing=rot["south"], powered="false")
    # A BUTTON EMITS TO ALL SIX NEIGHBOURS, so the cell beside it needs no connector at all.
    feed = out_at(btn_k - 1)
    w.put(feed[0], feed[1], feed[2], "redstone_wire")
    pulse = circuits.pulse(out_at(btn_k - 2), length=2, facing=rot["north"])
    # OVER the bowl's own trim: the approach is laid after the rim, so it has to be allowed to cut
    # through it exactly as `_link` is. Skipping instead would drop the cells the rim happens to
    # cover and leave a machine with a hole in the middle of it.
    _lay(w, p, (pulse,), over=True, through=("oak_fence",))
    keep = _structural(p) | {"oak_fence"}
    # ...and the run stops SHORT OF THE PULSE. `pulse` occupies k = btn_k-2 down to btn_k-5 along
    # this same column, so a loop that ran the whole way would overwrite its comparator with dust
    # and turn the monostable back into the plain repeater this file already deleted once.
    for k in range(1, btn_k - 5):               # the straight run, and the floor it stands on
        c2 = out_at(k)
        if not w.has(*c2) or w.name(*c2) in keep:
            w.put(c2[0], c2[1], c2[2], "redstone_wire")
        if not w.has(c2[0], c2[1] - 1, c2[2]):
            w.put(c2[0], c2[1] - 1, c2[2], p["pal_shell"])
    if not w.has(pad[0], pad[1] - 1, pad[2]):
        w.put(pad[0], pad[1] - 1, pad[2], p["pal_shell"])

    sgn = (btn[0] + ax, btn[1] + 1, btn[2] + az)
    w.put(sgn[0], sgn[1] - 1, sgn[2], p["pal_pillar"])
    # A SIGN FACES THE PLAYER, AND THE PLAYER STANDS OUTSIDE THE BOWL. `p["facing"]` is the
    # machine's axis and has nothing to do with where the approach ended up.
    w.put(sgn[0], sgn[1], sgn[2], "oak_wall_sign", facing=rot["south"], waterlogged="false")
    w.sign(sgn[0], sgn[1], sgn[2],
           front=[str(p.get("title") or "WHEEL")[:15], "red green black", "1 in 3", "spin to win"])
    return {"contract": "press once; exactly one of three pockets lights (1 in 3)",
            "inputs": [list(btn)], "outputs": pockets,
            "rng_hopper": list(hop), "pockets": pockets,
            "stock": {"dropper": rnd["stock"]},
            "reads": "wheel", "unverified": [circuits.RANDOM_NOTE]}


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


def _hall(w: World, p: dict, ctx) -> dict:
    """THE BUILDING. A floor, a perimeter wall, a gateway and a lit colonnade.

    Without this the rooms stand in void, which is both why the casino read as scattered platforms
    and why every design reported free-floating cells: on a fresh skyblock plot there is nothing to
    place a first block against. The floor is the fix for both.

    **NO ROOF, DELIBERATELY.** Each room already has its own ceiling, and a 85x85 lid is seven
    thousand blocks that nobody standing inside a room can see. What makes the place read as built
    from outside is the WALL and the GATEWAY - a regular edge with an opening in it - which is the
    void tower's rule, and it costs a tenth as much. An open sky over a lit plaza is a courtyard,
    not an unfinished room.

    The wall carries a plinth, a string course and a parapet in `deepslate_bricks` - 71 luminance
    against smooth stone's 159, which is the one real value line this economy has at cheap tier.
    Cracked and chiseled variants are within 4 RGB of plain and would draw nothing at all; this
    project has proved that twice and written it down both times.
    """
    x, y, z = (int(v) for v in p["at"])
    wsize, dsize = max(8, int(p["width"])), max(8, int(p["depth"]))
    gate = max(2, int(p["gate"]))
    dx, dz = _STEP[p["facing"]]
    sx, sz = -dz, -dx

    floor, wall, line = p["pal_shell"], p["pal_shell"], p["pal_pillar"]
    lamps = 0
    for i in range(wsize):
        for d in range(dsize):
            cx, cy, cz = x + sx * i - dx * d, y, z + sz * i - dz * d
            if p["check"] and _busy(ctx, cx, cy, cz):
                continue
            edge = i in (0, wsize - 1) or d in (0, dsize - 1)
            if edge:
                # A BORDER COURSE, because a floor plane with no edge reads as a slab someone left.
                w.put(cx, cy, cz, line)
                continue
            # **SEVEN THOUSAND IDENTICAL CELLS IS NOT A FLOOR, IT IS A SLAB.** The hall came out
            # 68% one grey block and read exactly like the platforms it replaced. A floor pattern
            # is the cheapest thing in this build that makes the place look designed: a grid of
            # dark lines every eight, a carpet runner on the entrance axis, and plain stone bays
            # between them. The grid is set in WORLD coordinates, so it stays aligned across
            # everything sited on it - the deck soffit's rule, which it needed after a
            # per-cell grid came out as confetti.
            # THE AISLE IS A FLOOR MATERIAL, NOT A CARPET LAID ON ONE.
            #
            # Drawn as carpet at y+1 it shipped ten FLOATING cells every run, and the reason is
            # about ORDER rather than about carpet: `defer_to` is applied in the finish stage,
            # AFTER the generator has run, so at build time the floor is there, and by the time
            # the design is written the cells it yielded to a room are gone and the carpet on top
            # of them is standing on air. A cell in the floor course cannot outlive its support,
            # because it IS the support.
            aisle = i in (wsize // 2, wsize // 2 + 1)
            gx, gz = cx % 8 == 0, cz % 8 == 0
            if aisle:
                w.put(cx, cy, cz, p["pal_aisle"])
            elif gx or gz:
                w.put(cx, cy, cz, line)
            else:
                w.put(cx, cy, cz, floor if (cx // 8 + cz // 8) % 2 else p["pal_tile"])

    door = {wsize // 2 - k for k in range(gate)}
    for i in range(wsize):
        for d in (0, dsize - 1):
            for h in range(1, 7):
                cx, cy, cz = x + sx * i - dx * d, y + h, z + sz * i - dz * d
                if p["check"] and _busy(ctx, cx, cy, cz):
                    continue
                # THE GATEWAY IS LEFT EMPTY BY THE LOOP, not cut afterwards - the same rule the
                # rooms follow, and the same one the void tower's crenellations shipped without.
                if d == dsize - 1 and i in door and h < 5:
                    continue
                if h in (1, 4):
                    w.put(cx, cy, cz, line)          # plinth and string course
                elif h == 6:
                    w.put(cx, cy, cz, line if i % 2 == 0 else wall)   # parapet
                else:
                    w.put(cx, cy, cz, wall)
    for d in range(dsize):
        for i in (0, wsize - 1):
            for h in range(1, 7):
                cx, cy, cz = x + sx * i - dx * d, y + h, z + sz * i - dz * d
                if p["check"] and _busy(ctx, cx, cy, cz):
                    continue
                if h in (1, 4):
                    w.put(cx, cy, cz, line)
                elif h == 6:
                    w.put(cx, cy, cz, line if d % 2 == 0 else wall)
                else:
                    w.put(cx, cy, cz, wall)

    # A LANTERN EVERY SIX ALONG THE INSIDE OF THE WALL. Cheap (iron and a torch), warm, and it is
    # what stops a walled plaza reading as a pen. Set ON the string course so it has a real block
    # under it - a fixture hanging off nothing is this project's oldest audit failure.
    for i in range(3, wsize - 2, 6):
        for d in (1, dsize - 2):
            cx, cy, cz = x + sx * i - dx * d, y + 5, z + sz * i - dz * d
            if p["check"] and _busy(ctx, cx, cy, cz):
                continue
            w.put(cx, cy - 1, cz, line)
            w.put(cx, cy, cz, "lantern", hanging="false", waterlogged="false")
            lamps += 1

    # THE NAME OVER THE DOOR.
    gi = max(door) + 1
    sx_, sy_, sz_ = x + sx * gi - dx * (dsize - 1), y + 5, z + sz * gi - dz * (dsize - 1)
    if not (p["check"] and _busy(ctx, sx_, sy_, sz_)):
        back = {"east": "west", "west": "east", "north": "south", "south": "north"}[p["facing"]]
        w.put(sx_, sy_, sz_, "oak_wall_sign", facing=back, waterlogged="false")
        w.sign(sx_, sy_, sz_, front=[str(p.get("title") or "CASINO")[:15], "", "", ""],
               colour="white", glowing=True)

    return {"contract": f"{wsize}x{dsize} hall, {gate}-wide gateway, {lamps} lanterns",
            "inputs": [], "outputs": []}


def _prize_wall(w: World, p: dict, ctx) -> dict:
    """One button, one prize. **THE REDSTONE BLOCK WAS THE BUG AND IT MADE THE WHOLE WALL DEAD.**

    Every dispenser had a `redstone_block` stuck permanently to its back, so every one of them was
    LIVE AT REST. A dispenser fires on a RISING EDGE: powered for ever means it dispensed once when
    the chunk loaded and never again, and the buttons - mounted diagonally, not even touching it -
    did nothing at all. Four walls, twenty dispensers, permanently on and permanently useless.

    Nothing caught it because this module had no contract asserted by simulation, which every game
    here has had since the day `chase` and `vault` were cut for exactly this. It has one now.

    The button drives it directly instead: a button on a solid block strongly powers that block,
    and a block above a dispenser powers the dispenser. Press, one item, and the signal falls again
    so the next press works too.
    """
    x, y, z = (int(v) for v in p["at"])
    dx, dz = _STEP[p["facing"]]
    n = max(1, min(12, int(p["lanes"])))
    outs, ins = [], []
    for i in range(n):
        px, pz = x - dz * i * 2, z - dx * i * 2
        for h in range(4):
            w.put(px, y + h, pz, p["pal_shell"])
        w.put(px, y + 1, pz, "dispenser", facing=p["facing"], triggered="false")
        # THE BUTTON IS ON THE BLOCK DIRECTLY ABOVE, which is the only place it can be and still
        # reach: mounted a cell out in front it was diagonal from the dispenser and touching
        # nothing. A barrel behind holds the prizes a human stocks - the machine never reaches
        # past it, which is the same rule the games' payout barrels follow.
        btn = (px + dx, y + 2, pz + dz)
        w.put(btn[0], btn[1], btn[2], "stone_button", face="wall",
              facing=p["facing"], powered="false")
        w.put(px - dx, y + 1, pz - dz, "barrel", facing=p["facing"], open="false")
        w.put(px, y + 3, pz, p["pal_accent"])
        outs.append([px, y + 1, pz])
        ins.append(list(btn))
    return {"contract": f"{n} prizes, one button each, one item per press",
            "inputs": ins, "outputs": outs,
            "stock": {"each dispenser": "the prize it hands out"}}


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
    outs, bars = [], []
    for i in range(n):
        px, pz = x - dz * i, z - dx * i
        w.put(px, y, pz, p["pal_shell"])
        w.put(px, y + 1, pz, "barrel", facing="up", open="false")
        w.put(px + dx, y + 1, pz + dz, "comparator", facing=p["facing"],
              mode="compare", powered="false")
        w.put(px + dx * 2, y + 1, pz + dz * 2, "redstone_lamp", lit="false")
        outs.append([px + dx * 2, y + 1, pz + dz * 2])
        bars.append([px, y + 1, pz])
    # **A BARREL YOU OPEN IS AN INPUT.** Recorded as one - `redstone_audit`'s own census already
    # says so ("a prize counter is a barrel you open") - because a machine that declares no input
    # is a machine nothing can drive, and this one was the only kind in the park that could not be
    # played end to end for want of knowing where to put the prizes.
    return {"contract": f"{n} barrels, each with a fullness lamp",
            "barrels": bars, "inputs": bars, "outputs": outs}


BUILDERS = {"high_roller": _high_roller, "double_or_none": _double_or_none,
            "lucky_number": _lucky_number, "duel": _duel, "wheel": _wheel,
            "prize_wall": _prize_wall, "marquee": _marquee, "counter": _counter,
            "hall": _hall}


def _split(spec: str):
    name = spec.split("[")[0]
    props = {}
    if "[" in spec and spec.endswith("]"):
        for part in spec[spec.index("[") + 1:-1].split(","):
            k, _, v = part.partition("=")
            props[k.strip()] = v.strip()
    return name, props
