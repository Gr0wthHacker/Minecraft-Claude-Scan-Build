"""Brief in, PLAN out — and nothing is built until a human says yes.

    python -m mcbuild plan "redstone casino" --world out/island_now.litematic
    python -m mcbuild plan --show casino
    python -m mcbuild plan --approve casino          # the gate. Nothing builds before this.
    python -m mcbuild plan --emit casino             # writes the configs

Jack's choice was **propose -> approve -> build**, and that is the whole architecture here rather
than a setting. The planner proposes; the deterministic pipeline verifies; a human approves; only
then does anything reach the world.

**THE PLANNER DOES NOT UNDERSTAND ENGLISH AND DOES NOT PRETEND TO.** A brief selects a THEME out
of a catalogue and sets its parameters. That is an honest split: the open-ended half (what should a
casino contain, how big, in what style) is a judgement, and the closed half (does it fit, does it
collide, can it be afforded, do the circuits work) is measurement. Wiring an LLM to the first half
is a one-line change - it emits a theme name and a parameter dict - and it still cannot skip the
second half, which is the point. A model that could approve its own plan would be a model that
could build a spotted table at island scale.

What a plan carries, and every one of these is a refusal waiting to happen:

    sited        every module on real ground, inside the plot, not overlapping each other
    costed       through `recipes` against your actual containers, so "can I afford it" is answered
    verified     circuits inspected; a module whose contract cannot be met is REPORTED, not placed
    ordered      dependencies first, using the same `after` the build order already understands
    unverified   what the plan knows it cannot promise, carried forward in writing
"""
from __future__ import annotations

import collections
import datetime as _dt
import json
import os
import pathlib

import numpy as np

from . import plot as plot_mod, scan as scan_mod

PLANS = pathlib.Path("out/plans")

# ---------------------------------------------------------------------- the catalogue
#
# A THEME is a list of modules with a footprint and a generator. Deliberately data rather than
# code: adding "arcade" or "market" should not require touching the planner, and the thing an LLM
# would emit is exactly one of these dicts.
# THE REFERENCE CASINO DOES NOT FIT ON A SKYBLOCK PLOT. It is 135 x 105 and a plot is 99 x 99 -
# 36 over on X and 6 over on Z. Jack: *"it cant be bigger than 99x99 ... but we can go vertically
# higher and much lower"*, and that is the whole shape of the answer: the same volume is 1.45
# floors when it is STACKED, and Y-64 to Y320 is 384 courses of room. So a theme carries a
# `floors` plan rather than sprawling, and every module's footprint is checked against the plot
# before anything is generated.
MAX_FOOTPRINT = 99

#: The furthest an interface anchor stands off its own face (`interfaces._LAYOUT`'s deepest
#: standoff - a landmark's view approach). A module clear of a reserved band whose APPROACH is
#: not is still a module the streets cannot reach.
MAX_STANDOFF = 4

THEMES = {
    "casino": {
        "blurb": "a redstone casino: four verified games over two floors, inside a 99x99 plot",
        # **ONE FLOOR, BECAUSE A SECOND ONE IS A STRUCTURE AND NOT A NUMBER.**
        #
        # This said two floors and lifted eleven modules to +12 - and nothing ever BUILT a
        # mezzanine: no deck, no railing, no stairs. All eleven hung in open air eleven blocks
        # over the gaming floor, and a component count of the finished casino found exactly that:
        # one building of 15,710 cells and 45 floating fragments.
        #
        # A floor entry is a lift, and a lift is only legitimate when something carries the thing
        # being lifted. Adding a real gallery - deck, balustrade and a flight down - is a fine
        # thing to build and it is a BUILD, so until it exists everything stands on the ground.
        "floors": [
            {"name": "Gaming Floor", "y": 0},
        ],
        # **FOUR DISTINCT MECHANICS, NOT FOUR NAMES FOR TWO.**
        #
        # The previous lineup was measured cell-for-cell and it was two games wearing four names:
        # High Roller vs Coin Toss were 99.2% the same cells and One In Three vs Even Money 97.8%,
        # because `threshold` pays on a MAXIMUM and a maximum is the same game whatever number you
        # put in it. Changing the odds is not changing the game.
        #
        # What separates these four is the QUESTION the player is answering:
        #
        #   High Roller    what did I roll?          bar        reads a level
        #   One In Three   did I roll high enough?   threshold  a maximum
        #   Lucky Two      did I hit the number?     window     an AND-NOT, middle wins, top loses
        #   Duel           did I beat the house?     compare    two rolls, ties to the player
        #   Colour Wheel   where did it land?        decoder    one roll, three pockets, one lit
        #
        # The Wheel is the first with a different SHAPE as well as a different circuit - a sunken
        # round bowl with a rail, read from above - because four verified mechanics in four
        # identical booths are still four identical rooms.
        #
        # **THE ODDS VARIANTS ARE GONE.** "Coin Toss" was High Roller at 2 outcomes and measured
        # 98.7% the same machine; "Even Money" was One In Three and measured 94.6%. Changing a
        # number is not changing a game, and shipping it under a different name over a different
        # door is the thing that made this read as the same room eighteen times.
        #
        # Each is a different circuit asserted by its own simulation, and each states its odds -
        # a house that cannot state its odds does not know them.
        "modules": [
            # **THE BIGGEST MODULE IS SITED FIRST.** `bays` packs in list order, so the booths
            # filled the grid and the 23x21 wheel reported NO SITE three times - a module is not
            # unsiteable because it is late, it is unsiteable because everything smaller got there
            # first. Largest footprint first is the only order that does not starve it.
            {"name": "Colour Wheel", "gen": "casino", "kind": "wheel",
             "size": [24, 4, 24], "params": {"pit": 2}, "count": 2, "floor": 0},
            {"name": "High Roller", "gen": "casino", "kind": "high_roller",
             "size": [9, 8, 8], "params": {"outcomes": 3, "pit": 2}, "count": 3, "floor": 0},
            {"name": "One In Three", "gen": "casino", "kind": "double_or_none",
             "size": [9, 8, 8], "params": {"outcomes": 3, "pit": 2}, "count": 3, "floor": 0},
            {"name": "Lucky Two", "gen": "casino", "kind": "lucky_number",
             "size": [9, 8, 8], "params": {"outcomes": 3, "pit": 2}, "count": 3, "floor": 0},
            {"name": "Duel", "gen": "casino", "kind": "duel",
             "size": [9, 8, 8], "params": {"outcomes": 3, "pit": 2}, "count": 3, "floor": 0},
            {"name": "Casino Marquee", "gen": "casino", "kind": "marquee",
             "size": [18, 5, 4], "params": {"length": 16}, "count": 4, "floor": 0},
            {"name": "Prize Wall", "gen": "casino", "kind": "prize_wall",
             "size": [4, 5, 12], "params": {"lanes": 5}, "count": 4, "floor": 0},
            {"name": "House Bank", "gen": "casino", "kind": "counter",
             "size": [4, 4, 8], "params": {"lanes": 6}, "count": 3, "floor": 0},
            # THE BUILDING GOES LAST, AND THAT ORDER IS LOAD-BEARING.
            #
            # `emit` chains `defer_to` down the list, so a later module yields any cell an earlier
            # one already claimed. Built first, the hall's floor would take every room's floor and
            # the rooms would lose the thing that makes them rooms. Built last it lays only the
            # ground BETWEEN them - which is exactly what a hall is.
            #
            # It is also the fix for "nothing to place against": the plot is void, and every design
            # reported free-floating cells because there is no ground on a fresh skyblock island.
            {"name": "Casino Hall", "gen": "casino", "kind": "hall", "anchor": "cover",
             "size": [88, 7, 88], "params": {"width": 88, "depth": 88, "gate": 3},
             "count": 1, "floor": 0},
        ],
    },

    # ------------------------------------------------------------------ the theme park
    #
    # THREE ZONES THAT ARE NOT THE SAME ZONE. The first attempt gave all three an identical module
    # list and three palettes, and Jack named it exactly: *"all 3 areas are the same with different
    # materials... nothing actually exists outside of some infrastructure and some huts"*. He was
    # right - it was 9,544 blocks a zone, nothing over 29 tall, eleven 9x7 huts and NO RIDES, in a
    # thing whose entire point is rides.
    #
    # The zones now differ in KIND, not in paint:
    #
    #   midway     THE ENTRANCE. Not a themed land at all - arrival, shops, a fountain, a statue,
    #              a carousel and a ferris wheel. Lighthearted, bright, and the place you come in.
    #   frontier   A WESTERN MINING TOWN, with a mine coaster as its headline ride.
    #   hollow     A HAUNTED GOTHIC QUARTER, with a three-storey manor and a drop tower.
    #
    # ONE HEADLINE RIDE PER ZONE, and that is measured rather than chosen: a 57x57 coaster has
    # exactly ONE viable bay in a 99x99 plot, so two of them cannot coexist. Which is also how
    # real parks are laid out.
    "midway": {
        "blurb": "the entrance: a shopping street, a fountain, a carousel and the big wheel",
        "keywords": ["theme park", "midway", "entrance", "fairground", "carnival", "park centre"],
        "greenfield": True,
        "orient": True,
        "paths": True,
        "paths_name": "Midway Paths",
        "furniture": ["bench", "planter", "lamppost", "topiary", "bin", "signpost"],
        "spacing": 0,
        "reserve": [[97640, 80551, 97649, 80649]],
        "floors": [{"name": "Ground", "y": 0}],
        "modules": [
            {
                "name": "The Big Top",
                "gen": "setpiece",
                "kind": "bigtop",
                "size": [29, 19, 29],
                "orient": False,
                "district": "Fairground",
                "params": {"land": "midway", "facing": "east", "radius": 11},
            },
            # **THE ARRIVAL COURT IS PINNED TO THE BEDROCK AND SITED FIRST.** `at` is the
            # arrival cell itself, not a corner: the court is built radially around the one
            # coordinate that cannot be negotiated. Its own dig list clears the starter pad and
            # the tree; the starter chest is deliberately left standing and reported.
            # ------------------------------------------------- things to DO, and a reason to stay
            # The user: *"we want this to be a unique real experience that people want to stay
            # around for"*. A park keeps people because things HAPPEN in it and because there is
            # somewhere pleasant to be between rides - so: a show on a timer, a terrace to watch
            # it from, somewhere to eat, and games where what the PLAYER does decides the outcome
            # rather than a randomiser they stand and watch.
            {"name": "Midway Map", "gen": "wayfinding", "kind": "mapboard",
             "size": [3, 9, 11], "orient": False,
             "params": {"land": "midway", "zone": "midway", "title": "MIDWAY",
                        "facing": "east"}},
            {"name": "Park Notices", "gen": "wayfinding", "kind": "noticeboard",
             "size": [3, 7, 7], "orient": False,
             "params": {"land": "midway", "title": "PARK RULES", "facing": "east"}},
            {"name": "Midway Post", "gen": "wayfinding", "kind": "fingerpost",
             "size": [9, 9, 9], "orient": False, "anchor": "junction",
             "params": {"land": "midway", "facing": "east",
                        "arms": [{"direction": "north", "dest": "Frontier"},
                                 {"direction": "south", "dest": "Hollow"},
                                 {"direction": "west", "dest": "Park Gate"}]}},
            {"name": "The Big Wheel", "gen": "bigwheel", "kind": "wheel",
             "size": [19, 85, 77], "orient": False,
             "anchor": "edge", "side": "east",
             "params": {"land": "midway", "diameter": 65, "spokes": 16, "cars": 16,
                        "facing": "west"}},
            # **D=25, NOT 31, AND THE PLOT DECIDED IT.** A monument 34 wide pinned to the centre
            # of a 99-wide plot leaves exactly 32 either side of it, so NO 40x40 exists on the
            # midway at all - the carousel at its full diameter could not be sited anywhere, at
            # any packing. It keeps its real 80-cell circuit and its two rings of mounts; what it
            # loses is six blocks of radius. `orient: False` because a round ride gains nothing
            # from a square reservation.
            {"name": "Carousel", "gen": "bigwheel", "kind": "carousel",
             "size": [32, 27, 27], "orient": False,
             "params": {"land": "midway", "diameter": 25, "mounts": 12, "facing": "east"}},
            {"name": "Park Gate", "gen": "park", "kind": "gate", "size": [15, 9, 7],
             "anchor": "edge", "side": "west",
             "params": {"land": "midway", "lanes": 3, "depth": 6, "facing": "west"}},
            # The islands run along Z: left is NORTH, right is SOUTH.
            {"name": "Frontier Arch", "gen": "park", "kind": "arch", "size": [9, 9, 5],
             "anchor": "edge", "side": "north",
             "params": {"land": "frontier", "width": 7, "height": 6, "facing": "north"}},
            {"name": "Hollow Arch", "gen": "park", "kind": "arch", "size": [9, 9, 5],
             "anchor": "edge", "side": "south",
             "params": {"land": "hollow", "width": 7, "height": 6, "facing": "south"}},
            {"name": "Grand Plaza", "gen": "park", "kind": "plaza", "anchor": "cover",
             # **`width` IS THE FRONTAGE AND ON AN EAST-FACING MODULE THAT IS Z.** Written 88x96 the
            # plaza came out 96 wide across X and paved ten columns of the transit corridor, while
            # the carousel in the south-west corner stood on bare void because Z was three short.
            # 99 along Z covers the plot end to end; 89 across X runs from the western boundary
            # to X 97639, which is the last column the theme owns and the one the transit
            # station's landing pad sits against. At 88 it stopped one short and left a
            # ONE-BLOCK UNMARKED GAP OVER OPEN VOID between the zone's paving and the pad -
            # present in the frontier and the hollow, absent in the midway, which is the worst
            # combination: jumpable, unsigned, and inconsistent between zones.
            "size": [88, 5, 99],
             "params": {"land": "midway", "width": 99, "depth": 89, "facing": "east"}},
        ],
    },

    "frontier": {
        "blurb": "a western mining town: a mine coaster, a log flume, a headframe and a saloon",
        "keywords": ["frontier", "mine", "western", "wild west", "prospect"],
        "greenfield": True,
        "orient": True,
        "paths": True,
        "paths_name": "Frontier Paths",
        "furniture": ["bench", "planter", "lamppost", "signpost", "bin", "flagpole"],
        "spacing": 0,
        "reserve": [[97640, 80351, 97649, 80449]],
        # **THE FRONTIER'S PROGRAM DOES NOT FIT ITS PLOT, AND THE ANSWER IS DOWN.**
        #
        # Measured: 6,709 cells of module footprint against 8,811 of owned land - 76% before a
        # single street is drawn - and a land with a 5-wide spine, 3-wide frontage walks and a
        # service road cannot pack much past 60%. Every reordering simply changed WHICH module
        # was squeezed out; the Saloon and the Gold Sluice took turns reporting NO SITE.
        #
        # PARK_VERTICAL_MASTERPLAN.md section 6 already answers it: the mine journey belongs
        # under the town, and the hidden core band (B-48..B-8) is what it is for. A module on
        # the Undermine floor stands 24 courses down, and `_clear` has always compared boxes in
        # three dimensions - so it costs the surface nothing. This is the difference between a
        # flat fairground with tunnels and a park whose mine is actually beneath it.
        # **AND A THIRD FLOOR, BECAUSE THE MINE IS NOT THE MINE WORKS.** The Undermine at -24
        # is the hidden core - the station a guest boards at, which section 3 puts at B-48..B-8.
        # The JOURNEY belongs in the deep adventure band beneath it, and the difference is the
        # whole point of having bands: a station under a town and a cavern under a station are
        # not the same kind of place, and stacking both at one depth would say they were.
        "floors": [{"name": "Ground", "y": 0}],
        "modules": [
            {
                "name": "The Water Tower",
                "gen": "setpiece",
                "kind": "watertower",
                "size": [15, 25, 11],
                "orient": False,
                "district": "Mining Square",
                "params": {"land": "frontier", "facing": "east"},
            },
            # **A LEVER TO ARM AND A BUTTON TO FIRE.** A two-block SUBTRACT interlock rather
            # than a machine pit - every pit in this repo has cost a floating floor - then a
            # five-piston fuse thumps the length of the drift, seven charges go at the face and a
            # bell rings. `drift` is a NEW key on purpose: the shared FRONTIER["depth"] is the
            # saloon's 12, and reading that built a drift with room for two fuse stages of five.
            # ------------------------------------------------------- Prospecting Row
            #
            # PARK_FRONTIER.md asks for "Gold Sluice, Shooting Range, Nugget Chute under one
            # covered porch, then Assay/Prize redemption" - one row of things you do with your
            # hands, with the place you spend a win at the end of it. They were four separate
            # machines scattered across the plot; naming the district is what puts them on one
            # street, in the order a guest uses them.
            #
            # Reuse, not new code: a plinko board is a gravel-washing chute in a mining town, and
            # DROP is a fourth verb beside press, shoot and weigh.
            # A shooting range and an assay scale: both are things you do with your hands, and
            # both belong to a mining town.
            # **THE ASSAY OFFICE AND THE PAY WINDOW ARE ONE COUNTER, ON MAIN STREET.**
            # PARK_FRONTIER.md: "Pay Window + Assay Office: Merge into Assay & Prize Office
            # between games and Main Street", and its Main Street holds "Saloon, Assay & Prize
            # Office, service/rest frontage". Two separate buildings - one weighing your find,
            # one paying for it - is two queues for one transaction, and the pair sat at
            # opposite ends of the land. They keep their own mechanisms and stand shoulder to
            # shoulder, which is what a merge means for two things that each still have to work.
            #
            # They share Main Street's district rather than owning one of their own: a
            # two-building district competes with the Saloon for the same street and leaves it
            # NO SITE, which is what happened when they had their own.
            # **A GAME YOU PLAY WITH YOUR HANDS.** Drop items into the head box; flowing
            # water carries them thirteen cells down a stepped launder into a hopper row feeding
            # a barrel, and a comparator on that barrel raises a gold block into a window and
            # rings a bell. Both simulators agree, in both directions - it is dark when empty.
            # It replaces the Riverboat, which was a hull you could walk onto and nothing else.
            {"name": "Frontier Map", "gen": "wayfinding", "kind": "mapboard",
             "size": [3, 9, 11], "orient": False,
             "params": {"land": "frontier", "zone": "frontier", "title": "FRONTIER",
                        "facing": "east"}},
            {"name": "Frontier Post", "gen": "wayfinding", "kind": "fingerpost",
             "size": [9, 9, 9], "orient": False, "anchor": "junction",
             "params": {"land": "frontier", "facing": "east",
                        "arms": [{"direction": "south", "dest": "Midway"},
                                 {"direction": "west", "dest": "Mine Coaster"}]}},
            # **"MINE CART ESCAPE", NOT "RUNAWAY MINE".** PARK_FRONTIER.md asks for a family
            # ride "mechanically and visually distinct from coaster", and the two names were a
            # promise that they were the same thing twice. The mechanism is already the distinct
            # one; the name was the part still claiming otherwise.
            # ...and it is the ride that goes down there. A mine cart escape whose whole story
            # is getting OUT of a mine belongs in one; on the surface it was a shed with track
            # in it, taking 598 cells of the town's own street frontage to be so.
            # **THE JOURNEY SECTION 6 ASKS FOR, AND IT IS A WALK RATHER THAN A RIDE.** Worked ore
            # near the surface, a broken trestle over a cavern, the flooded lower works, and one
            # crystal reveal at the deepest point - four rooms that each do exactly one thing,
            # threaded on a corridor that reaches every one of them by construction.
            {"name": "Mine Coaster", "gen": "coaster", "kind": "coaster",
             "size": [47, 38, 47], "orient": False, "anchor": "edge", "side": "north",
             "district": "Mining Square",
             "params": {"land": "frontier", "span": 44, "top": 34, "facing": "south"}},
            # **THE LOG FLUME IS BACK - `fluids.carries` returns True for it now.**
            #
            # It was withdrawn once already for the reason Jack gave: *"the water slide etc are a
            # good idea but functionally dont actually work"*. The second attempt (spaced sources,
            # none on the lift) still failed - 161 cells reached, 0 flowing - and the cause was
            # `_seal`, the leak backstop: it filled every empty cell horizontally adjacent to a
            # water block, which is exactly the gap the NEXT source needs open to spread through.
            # It walled every source into its own sealed pocket.
            #
            # Fixing that exposed two more of the same shape, both from a corner's own doubled
            # wall/floor offset landing on a real cell of one of its two legs (two indices away,
            # not one) - once in the wall loop, once in the floor's own bed. `_wall_offs` is the
            # one fix for all three: it drops the two offsets that point back along either leg,
            # leaving only the corner's genuine outer perimeter. `_seal` is now bed-only (below,
            # never sideways) and finds nothing left to do - the geometry is correct by
            # construction, not patched after the fact. `tests/test_flume.py` pins all of it,
            # including every facing and three sizes, so the corner bug cannot come back quietly.
            # **A FLUME IS A LIFT HILL AND VANILLA HAS NO CHAIN LIFT.** Nothing carries a
            # player UP a water channel, and the flume's own crest source sat at the top of a
            # staircase descending BOTH ways - twenty courses of water running back down the lift
            # at the rider. The headroom fault the user found (7 of 137 cells with under two clear
            # courses) was the smaller half and a two-line fix; fixing it would have shipped a
            # ride nobody can start. A real water slide's lift is a STAIRCASE, so this one has
            # one: forecourt, quay, splash pool, slipway, a helical stair tower, a bridge, a start
            # box, and sixty cells of descent back into the same pool. One source in the channel
            # rather than 193, because every step down restarts water's seven-block budget.
            # The headframe is the mine district's own entrance and its vertical landmark, so
            # it belongs to Mining Square rather than standing wherever a bay was free.
            # A saloon is a FRONTAGE with a bar behind it, so the square reservation books
            # its own depth again in air. The frontier had four free 17x17 slots and no 19x19.
            # orient False: a windmill's sails read from every side, so it does not need the
            # square reservation - and at 13x21 booking 23x23 was the difference between it
            # fitting and being refused.
            {"name": "Frontier Gate", "gen": "park", "kind": "arch", "size": [9, 9, 5],
             "anchor": "edge", "side": "south",
             "params": {"land": "frontier", "width": 7, "height": 6, "facing": "south"}},
            {"name": "Frontier Plaza", "gen": "park", "kind": "plaza", "anchor": "cover",
             # **`width` IS THE FRONTAGE AND ON AN EAST-FACING MODULE THAT IS Z.** Written 88x96 the
            # plaza came out 96 wide across X and paved ten columns of the transit corridor, while
            # the carousel in the south-west corner stood on bare void because Z was three short.
            # 99 along Z covers the plot end to end; 89 across X runs from the western boundary
            # to X 97639, which is the last column the theme owns and the one the transit
            # station's landing pad sits against. At 88 it stopped one short and left a
            # ONE-BLOCK UNMARKED GAP OVER OPEN VOID between the zone's paving and the pad -
            # present in the frontier and the hollow, absent in the midway, which is the worst
            # combination: jumpable, unsigned, and inconsistent between zones.
            "size": [88, 5, 99],
             "params": {"land": "frontier", "width": 99, "depth": 89, "facing": "east"}},
        ],
    },

    "hollow": {
        "blurb": "a haunted quarter: a three-storey manor, a drop tower, a clock tower and a graveyard",
        "keywords": ["hollow", "haunted", "gothic", "crypt", "manor", "spooky"],
        "greenfield": True,
        "orient": True,
        "paths": True,
        "paths_name": "Hollow Paths",
        "furniture": ["bench", "lamppost", "topiary", "signpost", "bin", "planter"],
        "spacing": 0,
        "reserve": [[97640, 80751, 97649, 80849]],
        # **AND THE HOLLOW GOES DOWN TOO, for the same measured reason as the Frontier.** Its
        # program needs 5,744 cells of the 8,811 it owns before a street is drawn, and the
        # Plummet - a 20x17 drop tower, the smallest of its five flagships - was the module that
        # kept losing. PARK_VERTICAL_MASTERPLAN.md section 7 already says where the room is:
        # "public streets lead to a much older world below: crypts, forgotten rail tunnels, and
        # a final founder's vault."
        "floors": [{"name": "Ground", "y": 0}],
        "modules": [
            {
                "name": "The Mausoleum",
                "gen": "setpiece",
                "kind": "mausoleum",
                "size": [18, 17, 29],
                "orient": False,
                "district": "Crypt Market",
                "params": {"land": "hollow", "facing": "east"},
            },
            # ---------------------------------------------------------- the Crypt Market
            #
            # **ELEVEN SMALL MODULES ARE NOT ELEVEN ATTRACTIONS.** PARK_HOLLOW.md: "Keep five
            # major experiences; stop treating eleven small modules as equal attractions. Mirror
            # Maze, Ossuary, Vault, Reliquary, and rest/service functions become one purposeful
            # Crypt Market."
            #
            # Nothing here is deleted and nothing new is invented: what changes is that they now
            # name a DISTRICT, and the packer sites a district together instead of hugging
            # whichever neighbour happens to be nearest. That one word is the difference between
            # a market and five machines standing on paving at opposite corners of the plot.
            #
            # **A TOMB YOU WALK INTO AND A PUZZLE YOU SOLVE.** Three shroud-levers, each lighting
            # its own lamp; the vault's doors open onto the prize alcove only while all three are
            # up, and shut the moment one drops.
            # ...and the Ossuary is the piece that belongs down there. A tomb you walk INTO,
            # on the surface, is a shed with levers in it; twenty courses under the market it is
            # the crypt the market is named after, and it hands the Plummet back its site.
            # **THE UNDERCRYPT SECTION 7 ASKS FOR.** Catacombs, the ossuary branch, the train's
            # own show chamber, a drowned crypt and the founder's vault - and it surfaces
            # somewhere else, which is what makes it a journey rather than a cul-de-sac.
            # ...and this is where an Ossuary or Vault win gets spent. A game with no payout is a
            # machine, not a game.
            # A 4x4 grid rather than 7x6: measured, 13x13 against 17x19. It keeps its
            # spanning-tree branches and its single solved route, so it is a shorter walk rather
            # than a simpler one.
            {"name": "Mirror Maze", "gen": "attractions", "kind": "mirrormaze",
             "size": [13, 10, 13], "orient": False, "district": "Crypt Market",
             "params": {"land": "hollow", "facing": "east", "maze_w": 4, "maze_d": 4}},
            # The two games that need a dark room: a combination vault, and a corridor of sculk
            # sensors you have to cross without making a sound.
            # **THE MARKET NEEDS SOMEWHERE TO SIT DOWN.** Section 7 of the vertical masterplan
            # asks the Crypt Market to be "discovery/recovery" and names a Mourning Parlour for
            # the recovery half. Every other land already had a recovery node and the Hollow had
            # none, so a guest who had walked the manor, dropped the tower and solved the crypt
            # had nowhere in the land to stop.

            # ---------------------------------------------------------- the Manor Quarter

            # ---------------------------------------------------------- wayfinding
            #
            # **NINE NAMEPLATES FOR ELEVEN DESTINATIONS IS NOT WAYFINDING, IT IS NOISE**, and it
            # is the one thing PARK_HOLLOW.md is explicit about: signage belongs "at Gate/Arrival
            # Court, Manor/Tower split, Ghost Train/Market split, and return loop - not at every
            # facade." A label on every building answers "which building is this", which a
            # visitor standing in front of one already knows; what they do not know is which way
            # to turn. So the nine markers are gone and the two real forks each get a post.
            {"name": "Hollow Map", "gen": "wayfinding", "kind": "mapboard",
             "size": [3, 9, 11], "orient": False,
             "params": {"land": "hollow", "zone": "hollow", "title": "HOLLOW",
                        "legend": ["MANOR west", "TOWER east", "MARKET south"],
                        "facing": "east"}},
            {"name": "Hollow Post", "gen": "wayfinding", "kind": "fingerpost",
             "size": [9, 9, 9], "orient": False, "anchor": "junction",
             "params": {"land": "hollow", "facing": "east",
                        "arms": [{"direction": "north", "dest": "Midway"},
                                 {"direction": "west", "dest": "Haunted Manor"},
                                 {"direction": "east", "dest": "Clock Tower"},
                                 {"direction": "south", "dest": "The Plummet"}]}},
            # The Manor/Tower split and the Train/Market split: the two places a visitor has to
            # choose and cannot see both answers from.
            {"name": "Manor Turn Post", "gen": "wayfinding", "kind": "fingerpost",
             "size": [9, 9, 9], "orient": False,
             "params": {"land": "hollow", "facing": "east",
                        "arms": [{"direction": "west", "dest": "Haunted Manor"},
                                 {"direction": "east", "dest": "The Plummet"}]}},
            {"name": "Market Turn Post", "gen": "wayfinding", "kind": "fingerpost",
             "size": [9, 9, 9], "orient": False,
             "params": {"land": "hollow", "facing": "east",
                        "arms": [{"direction": "north", "dest": "Ghost Train"},
                                 {"direction": "south", "dest": "The Reliquary"}]}},
            # It grew SEVEN COURSES DOWNWARD, not outward: every set piece hides its wiring
            # under the floorboard it fires through, so the footprint is unchanged and the height
            # is not.
            {"name": "Hollow Gate", "gen": "park", "kind": "arch", "size": [9, 9, 5],
             "anchor": "edge", "side": "north",
             "params": {"land": "hollow", "width": 7, "height": 6, "facing": "north"}},
            {"name": "Hollow Court", "gen": "park", "kind": "plaza", "anchor": "cover",
             # **`width` IS THE FRONTAGE AND ON AN EAST-FACING MODULE THAT IS Z.** Written 88x96 the
            # plaza came out 96 wide across X and paved ten columns of the transit corridor, while
            # the carousel in the south-west corner stood on bare void because Z was three short.
            # 99 along Z covers the plot end to end; 89 across X runs from the western boundary
            # to X 97639, which is the last column the theme owns and the one the transit
            # station's landing pad sits against. At 88 it stopped one short and left a
            # ONE-BLOCK UNMARKED GAP OVER OPEN VOID between the zone's paving and the pad -
            # present in the frontier and the hollow, absent in the midway, which is the worst
            # combination: jumpable, unsigned, and inconsistent between zones.
            "size": [88, 5, 99],
             "params": {"land": "hollow", "width": 99, "depth": 89, "facing": "east"}},
        ],
    },
}


class Plan:
    def __init__(self, name: str, theme: str, brief: str = ""):
        self.name = name
        self.theme = theme
        self.brief = brief
        self.created = _dt.datetime.now().isoformat(timespec="seconds")
        self.approved = False
        self.approved_at = ""
        self.island = ""
        self.modules: list = []
        # The land's own circulation, role-typed. Carried on the plan rather than only
        # inside the paths module so a gate can read the network without re-deriving it -
        # two derivations of one network is how a check and the thing it checks drift.
        self.routes: list = []
        # Gate evidence supplied from outside the planner: mechanics, safety, night, visual.
        # Absent means "not measured", which those gates report as a failure rather than
        # passing quietly.
        self.evidence: dict = {}
        self.notes: list = []
        self.unverified: list = []

    # ------------------------------------------------------------------ io

    def path(self) -> pathlib.Path:
        return PLANS / f"{self.name}.json"

    def save(self) -> str:
        PLANS.mkdir(parents=True, exist_ok=True)
        self.path().write_text(json.dumps(self.__dict__, indent=1), encoding="utf-8")
        return str(self.path())

    @classmethod
    def load(cls, name: str) -> "Plan":
        p = PLANS / f"{name}.json"
        if not p.exists():
            raise FileNotFoundError(f"no plan called {name} (looked in {PLANS})")
        d = json.loads(p.read_text(encoding="utf-8"))
        pl = cls(d["name"], d["theme"], d.get("brief", ""))
        pl.__dict__.update(d)
        return pl

    # ------------------------------------------------------------------ report

    def report(self) -> str:
        out = [f"PLAN {self.name}  ({self.theme})  {'APPROVED' if self.approved else 'NOT APPROVED'}",
               f"  brief: {self.brief or '-'}"]
        if not self.modules:
            out.append("  nothing sited - the ground could not take it")
        for m in self.modules:
            at = m["at"]
            out.append(f"  {m['name']:22s} {m['kind']:11s} at {at[0]} {at[1]} {at[2]}  "
                       f"{m['size'][0]}x{m['size'][1]}x{m['size'][2]}"
                       + (f"  {m['blocks']} blocks" if m.get("blocks") else ""))
            if m.get("contract"):
                out.append(f"      contract: {m['contract']}")
            for f in m.get("circuit", [])[:3]:
                out.append(f"      CIRCUIT: {f}")
        if self.modules:
            # THE SPREAD IS READ OFF THE ANCHOR OFFSET, NOT OFF `at`.
            #
            # A module's anchor is not its minimum corner - a game runs from at-6 to at+9 and the
            # hall runs from at-87 to at - so treating `at` as the corner reported the casino
            # spilling 80 blocks past the plot and using 113% of it, when every module was in fact
            # inside. A boundary report that cries wolf is one nobody reads.
            xs, zs, area = [], [], 0
            for m in self.modules:
                fx, _fy, fz = m.get("anchor_offset", (0, 0, 0))
                x0, z0 = m["at"][0] + fx, m["at"][2] + fz
                xs += [x0, x0 + m["size"][0] - 1]
                zs += [z0, z0 + m["size"][2] - 1]
                if not m.get("covers"):          # the hall IS the floor; it is not "used up"
                    area += m["size"][0] * m["size"][2]
            out.append(f"  spread: X {min(xs)}..{max(xs)}  Z {min(zs)}..{max(zs)}  "
                       f"({area} of {99 * 99} plot cells used by module footprints, "
                       f"{100 * area / (99 * 99):.0f}%)")
        for n in self.notes:
            out.append(f"  note: {n}")
        for u in self.unverified:
            out.append(f"  NOT VERIFIED: {u}")
        out.append("  " + ("build it: python -m mcbuild plan --emit " + self.name
                           if self.approved else
                           "approve with: python -m mcbuild plan --approve " + self.name))
        return "\n".join(out)


# ---------------------------------------------------------------------- siting

def _surface(sc) -> tuple:
    """(height map, name grid) of the capture's topmost solid cell per column, in world coords."""
    m = sc.model
    names = np.array([n.split(":")[-1] for n in m.names])
    solid = m.solid()
    sy, sz, sx = solid.shape
    ox, oy, oz = sc.origin
    # topmost solid per column
    idx = np.where(solid.any(axis=0), solid.shape[0] - 1 - np.argmax(solid[::-1], axis=0), -1)
    return idx, oy, (ox, oz), names, m.ids


def ground_band(sc, tolerance: int = 6) -> tuple:
    """The island's actual GROUND level, measured as the modal surface height.

    THE TOPMOST SOLID CELL IS NOT THE GROUND. On this island the highest block in most columns is
    the sky bird at Y268, so a naive height map sites a casino on a sculpture eighty blocks up -
    which is exactly what the first run of this planner did. That is the night pass's own lesson
    ("the lowest-standable classifier struck a THIRD time") arriving from the opposite direction.

    The mode is the honest statistic here: a plate 2,000 columns wide dominates any number of
    towers, sculptures and floating rocks, and it needs no hand-written Y.
    """
    idx, oy, _, _, _ = _surface(sc)
    vals = idx[idx >= 0]
    if not len(vals):
        return None
    counts = np.bincount(vals.astype(int))
    top = int(counts.argmax()) + oy
    return (top - tolerance, top + tolerance)


def pads(sc, size, plot=None, roll: int = 1, limit: int = 200, y_range=None) -> list:
    """Every flat-enough patch of ground the given footprint fits on.

    FLAT ENOUGH IS MEASURED, NOT ASSUMED. `roll` is how many courses the ground may vary across
    the footprint; this project has learned twice that a build sited on rolling terrain either
    floats on the low side or buries its feet on the high one.

    Returns [(x, y, z, roll)] with y the course the module stands ON.
    """
    idx, oy, (ox, oz), names, ids = _surface(sc)
    w, h, d = (int(v) for v in size)
    out = []
    H, W = idx.shape                    # (z, x)
    for zi in range(0, H - d):
        for xi in range(0, W - w):
            win = idx[zi:zi + d, xi:xi + w]
            if (win < 0).any():
                continue
            spread = int(win.max() - win.min())
            if spread > roll:
                continue
            top = int(win.max()) + oy + 1
            if y_range is not None and not (y_range[0] <= top <= y_range[1]):
                continue
            x, z = xi + ox, zi + oz
            # BOTH CORNERS, because a footprint is a box: checking only its origin sites a
            # module that starts inside the plot and finishes over the line, which is exactly how
            # the Island Run put 120 cells past the edge.
            if plot is not None and not (plot.contains(x, z) and plot.contains(x + w, z + d)):
                continue
            out.append((x, int(win.max()) + oy + 1, z, spread))
            if len(out) >= limit:
                return out
    return out


def turn_extent(gen: str, kind: str, params: dict, declared, facings=None) -> int:
    """The largest extent this module reaches at ANY facing - what a rotatable module must book.

    **A FOOTPRINT IS NOT NECESSARILY THE SAME AT EVERY FACING**, and assuming it was put the
    Fortune Wheel two cells inside a dead tree. Its booth grew a roof on one side, so it measures
    21 wide facing east and 23 facing west; siting reserved max(21, 19) and `_orient_to_streets`
    then turned it west, straight out of its own bay and into its neighbour. Every check upstream
    was correct - the reservation was simply measured at one facing out of four.

    So the square is booked against the WORST facing, which is the only one that can be safely
    assumed. Four builds a module, cached like everything else here.

    **AND `orient: False` IS NOT EXEMPT.** Its own note said a 180 flip "leaves the footprint
    identical", which is true of a symmetric module and false of this one - the wheel is the case
    that proved it, flipping east to west and growing two cells into a dead tree while its bay
    still read 21. A module that opts out of the 90-degree turn can still be flipped, so it books
    the worst of the two facings on its own axis; `facings` is how the caller says which.
    """
    best = 0
    for facing in (facings or ("east", "south", "west", "north")):
        _ox, _oy, _oz, w, _h, d = measured_footprint(
            gen, kind, {**params, "facing": facing}, declared)
        best = max(best, w, d)
    return best


def bays(plot, size, spacing: int = 3, margin: int = 4) -> list:
    """Lay the plot out as a GRID of bays, the way a floor is actually planned.

    **FIRST FIT DOES NOT USE A PLOT, IT FILLS A STRIP.** `pads` returns the first 200 flat spots it
    finds, which on a 99x99 plot is one row along the near edge - so the first few modules took
    them all and every module after that reported NO SITE beside 94% empty ground. The plan used
    **6%** of the plot and looked like a queue rather than a casino.

    A grid is also simply what the thing IS: bays of equal size, aisles between them, a margin off
    the boundary so nothing is built against the void. Returned in a spiral from the centre, so a
    half-full plan is a cluster around the middle rather than a line down one side.
    """
    x0, z0, x1, z1 = plot.bounds
    w, _h, d = (int(v) for v in size)
    stride_x, stride_z = w + spacing, d + spacing
    cols = max(1, ((x1 - x0 + 1) - 2 * margin) // stride_x)
    rows = max(1, ((z1 - z0 + 1) - 2 * margin) // stride_z)
    # centre the grid in the plot rather than pinning it to a corner
    used_x, used_z = cols * stride_x - spacing, rows * stride_z - spacing
    ox = x0 + ((x1 - x0 + 1) - used_x) // 2
    oz = z0 + ((z1 - z0 + 1) - used_z) // 2
    out = []
    for r in range(rows):
        for c in range(cols):
            out.append((ox + c * stride_x, oz + r * stride_z))
    mid_c, mid_r = (cols - 1) / 2, (rows - 1) / 2
    out.sort(key=lambda t: ((t[0] - (ox + mid_c * stride_x)) ** 2
                            + (t[1] - (oz + mid_r * stride_z)) ** 2))
    return out


def _sitable(sited, candidate, own=None) -> bool:
    """Both siting contracts at once: rule 4, and every public interface on the land.

    One predicate rather than two calls at three call sites, because the third call site
    is the one that gets forgotten - the alternate-facing branch has already been the
    last to learn a rule twice.
    """
    return _rule_four_clear(sited, candidate) and _anchors_on_land(candidate, own)


def _anchors_on_land(candidate, own) -> bool:
    """Do all this module's public interfaces land on the land the theme owns?

    The repair pass already turns a module whose FRONT opens onto land the theme does not
    own. It knows nothing about the other seven anchors, so a ride sited hard against the
    eastern boundary put its emergency exit two cells into the transit corridor - a fire
    exit onto a railway, correctly unreachable, and there is no facing that fixes it. The
    answer is not to turn it, it is not to put it there.

    A handoff is exempt: an arch's connector side is off the land BY DEFINITION.
    """
    if own is None:
        return True
    from . import interfaces as _interfaces
    trial = dict(candidate)
    _interfaces.annotate([trial], owned=own)
    for anchor in trial.get("interface", {}).get("anchors", []):
        if not anchor.get("public") or anchor["name"] in _interfaces.HANDOFF:
            continue
        x, _y, z = anchor["at"]
        if not (own[0] <= x <= own[1] and own[2] <= z <= own[3]):
            return False
    return True


def _rule_four_clear(sited, candidate) -> bool:
    """May this module stand here without discharging into a neighbour's queue?

    PARK_OVERHAUL.md rule 4. Within one module the interface layout already keeps a queue mouth
    and a discharge apart; what no module can see about itself is the ARRANGEMENT - a prize
    counter sited shoulder to shoulder with a vault, its collection point exactly on the vault's
    queue mouth. That is not a hypothetical: it is what the Hollow shipped, and grouping the two
    into one market made it worse rather than better, because a district is precisely a set of
    buildings standing close together.

    So it is a SITING constraint, checked before a spot is taken rather than reported afterwards.
    Reported, the only available fix is to move a module, which is this function running late.

    **THE SITED MODULES HAVE NO ANCHORS YET, AND THE FIRST VERSION FORGOT IT.** Interfaces are
    annotated after siting, so comparing a freshly-annotated candidate against the plan's own
    module dicts compared it against nothing: nineteen checks, zero refusals, and the Reliquary
    still discharging into the Vault. Both sides are annotated here, on copies, so the check is
    of the arrangement rather than of one half of it.
    """
    from . import interfaces as _interfaces
    trial = dict(candidate)
    others = [dict(m) for m in sited if m.get("kind") not in {"paths", "plaza"}]
    _interfaces.annotate(others + [trial])
    if not trial.get("interface", {}).get("anchors"):
        return True
    return not _interfaces.exit_queue_collisions(others + [trial])


#: How far a district's members may span before it stops reading as one street. A frontage of
#: three or four buildings is about 60 cells on this plot; past that a guest sees separate
#: buildings, whatever the theme calls them. Invented, like every other threshold in this file,
#: and stated so the next person suspects the number before the code.
DISTRICT_SPREAD = 60


def _districts_of(modules) -> dict:
    out = {}
    for module in modules:
        if module.get("district"):
            out.setdefault(module["district"], []).append(module)
    return {name: members for name, members in out.items() if len(members) > 1}


def _district_spread(members) -> int:
    """The longer side of the box a district's modules occupy."""
    boxes = [_box_of(m) for m in members]
    return max(max(b[2] for b in boxes) - min(b[0] for b in boxes),
               max(b[3] for b in boxes) - min(b[1] for b in boxes)) + 1


def _centre_box(pl_plot, spec):
    """The single cell where a land's two spines cross - its own crossroads.

    **A FINGERPOST BELONGS AT THE CROSSROADS AND MUST NOT COST A RIDE TO GET THERE.** Rule 7 makes
    wayfinding part of the path graph and the land specs put it at the decision points rather
    than on every facade; sited by `bays` it lands wherever a slot was free, which is a signpost
    in a field, and both side lands had every decision point unserved while carrying a post each.

    `anchor: centre` was tried and is the wrong tool: it claims its box in the FIRST siting group,
    so a 9x9 post took the middle of the Hollow before its rides were placed and cost it the
    Ghost Train and the Plummet. This is a PREFERENCE instead - the module keeps its ordinary
    place in the size order and simply takes the free bay nearest the crossing, which for a
    signpost is exactly the right answer and for a full plot degrades to where it used to be.
    """
    if pl_plot is None:
        return None
    x0, x1, z0, z1 = _owned_bounds(pl_plot, spec)
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    return (cx, cz, cx, cz)


def _district_box(modules, district):
    """The bounding box of everything already sited in a named district, or None.

    Read off the SITED modules rather than kept as a running variable: a module can be refused a
    site, and a ledger that assumed it landed would pull the whole district toward a building
    that does not exist.
    """
    if not district:
        return None
    boxes = [_box_of(m) for m in modules if m.get("district") == district]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def _box_gap(bx, bz, size, box) -> int:
    """How far a candidate bay sits from a district's own footprint, 0 when they touch."""
    x0, z0, x1, z1 = box
    cx1, cz1 = bx + size[0] - 1, bz + size[2] - 1
    return max(0, max(x0 - cx1, bx - x1)) + max(0, max(z0 - cz1, bz - z1))


def _contact(bx, bz, size, taken, bounds) -> int:
    """How much of this candidate box's edge touches something already there, or the boundary.

    **THIS IS WHAT STOPS A PLOT FRAGMENTING.** Ordered by distance from the centre, every module
    packs inward and the free space is left as a RING - wide, thin, and never square - so the
    hollow reported NO SITE for its clock tower and its crypt with the plot 51% used and a
    brute-force sweep finding no 18x18 anywhere on it. Preferring a spot that HUGS a neighbour's
    wall or the boundary keeps the leftover in one piece.

    It is also what a street looks like. Buildings stand shoulder to shoulder along a frontage;
    scattered evenly over a field is a business park.
    """
    px0, px1, pz0, pz1 = bounds
    w, _h, d = (int(v) for v in size)
    x1, z1 = bx + w - 1, bz + d - 1
    touch = 0
    if bx <= px0 + 1:
        touch += d
    if x1 >= px1 - 1:
        touch += d
    if bz <= pz0 + 1:
        touch += w
    if z1 >= pz1 - 1:
        touch += w
    for (ax, _ay, az, aw, _ah, ad) in taken:
        ox = min(x1, ax + aw - 1) - max(bx, ax) + 1
        oz = min(z1, az + ad - 1) - max(bz, az) + 1
        if oz > 0 and (abs(bx - (ax + aw)) <= 1 or abs(ax - (bx + w)) <= 1):
            touch += oz
        if ox > 0 and (abs(bz - (az + ad)) <= 1 or abs(az - (bz + d)) <= 1):
            touch += ox
    return touch


def _clear(taken: list, x, y, z, size) -> bool:
    """Does this footprint miss everything already placed. Boxes, because a module is a box."""
    w, h, d = (int(v) for v in size)
    for (ax, ay, az, aw, ah, ad) in taken:
        if (x < ax + aw and ax < x + w and z < az + ad and az < z + d
                and y < ay + ah and ay < y + h):
            return False
    return True


# ---------------------------------------------------------------------- planning



_FOOTPRINT_CACHE: dict = {}


def measured_footprint(gen: str, kind: str, params: dict, declared):
    """The module's REAL extent relative to its anchor, measured by building one.

    **THE DECLARED SIZE WAS A HAND-TYPED GUESS AND IT WAS WRONG.** A casino game is declared 9x8x8
    and builds 16x10x10 - and not centred on its anchor either: it runs from at-6 to at+9 across
    and at-7 to at+2 along, because the shell, the pit and the payout all extend BACKWARDS from
    the cell the player stands at. So every clearance test, every module-against-module check and
    the plot boundary guard were all measuring a box the build does not occupy, and a game sited
    its floor straight over the island's starter chest twice running.

    This is rule 11 pointed at ourselves: ask the generator, not your memory. Building one module
    costs milliseconds and is cached per (kind, params).

    Returns (ox, oy, oz, w, h, d) - the offsets from `at` and the true size.
    """
    key = (gen, kind, tuple(sorted((k, str(v)) for k, v in params.items())))
    if key in _FOOTPRINT_CACHE:
        return _FOOTPRINT_CACHE[key]
    out = None
    try:
        import numpy as np
        from .gen import GENERATORS
        probe = {**params, "at": [0, 64, 0], "kind": kind, "check": False}
        probe.setdefault("facing", "east")
        c = GENERATORS[gen].build(probe, [])
        m = c.to_model()
        ox, oy, oz = c.world_origin
        names = []
        for tag in m.palette:
            try:
                names.append(tag.value["Name"].value.split(":")[-1])
            except Exception:                                    # noqa: BLE001
                names.append("air")
        solid = ~np.isin(m.ids, [i for i, n in enumerate(names) if n == "air"])
        ys, zs, xs = np.where(solid)
        if len(xs):
            out = (int(xs.min()) + ox, int(ys.min()) + oy - 64, int(zs.min()) + oz,
                   int(xs.max() - xs.min()) + 1, int(ys.max() - ys.min()) + 1,
                   int(zs.max() - zs.min()) + 1)
    except Exception:                                            # noqa: BLE001
        out = None
    if out is None:
        # A MEASUREMENT THAT FAILED IS NOT A MEASUREMENT OF ZERO. Fall back to the declared box
        # and say nothing clever about it.
        out = (0, 0, 0, int(declared[0]), int(declared[1]), int(declared[2]))
    _FOOTPRINT_CACHE[key] = out
    return out



def _plot_bounds(pp):
    b = getattr(pp, "bounds", None)
    if callable(b):
        return b()
    return (pp.cx - pp.radius, pp.cx + pp.radius, pp.cz - pp.radius, pp.cz + pp.radius)


USE_CLEAR = 3          # rule 10: room to stand at a chest, open it and walk past


def _used_cells(sc) -> list:
    """Every cell in the capture holding something a player STANDS AT AND USES.

    Deliberately `protect.is_used` rather than `protect.is_protected`: the protected set is the
    never-OVERWRITE list and holds `wool`, which on this project's own islands is most of the
    sculpture material - used as a keep-clear radius it swallows whole builds. This project has
    made that exact substitution once already, in the night pass, and written it down.
    """
    from .gen import protect
    out = []
    # THE PALETTE HOLDS NBT TAGS, NOT STRINGS, and `str(tag)` is the tag's repr - which contains
    # the block name as a substring, so a careless parse SILENTLY MATCHES THE WRONG THING. The
    # first version of this found one "used" cell on the island and it was the BEDROCK; the chest
    # it was written to protect was never seen, and a module sited straight over it again.
    m = sc.model if hasattr(sc, "model") else sc
    ids = m.ids
    names = []
    for tag in m.palette:
        try:
            names.append(tag.value["Name"].value.split(":")[-1])
        except Exception:                                        # noqa: BLE001
            names.append("air")
    keep = {i for i, n in enumerate(names) if protect.is_used(n)}
    if not keep:
        return out
    import numpy as np
    ox, oy, oz = sc.origin
    for i in keep:
        for (y, z, x) in zip(*np.where(ids == i)):
            out.append((int(x) + ox, int(y) + oy, int(z) + oz))
    return out


def _owned_bounds(pl_plot, spec) -> tuple:
    """The plot MINUS the strips a theme has declared it does not own.

    A reserved strip is infrastructure - the transit corridor down the east of every park plot -
    and it has to shrink the land in three different places or it only half works. Seeding
    `taken` stops the PACKER using it; it does nothing for the two branches that compute a
    position from the plot's own bounds. The edge branch parked the Big Wheel and the Clock Tower
    on the railway; the cover branch then centred an 88-wide plaza across it, which claims nothing
    and so passed every collision check while paving the track.
    """
    x0, x1, z0, z1 = _plot_bounds(pl_plot)
    for (rx0, rz0, rx1, rz1) in spec.get("reserve", ()):
        if rz0 <= z0 and rz1 >= z1:                  # a full-height strip moves X
            if rx1 >= x1:
                x1 = min(x1, rx0 - 1)
            if rx0 <= x0:
                x0 = max(x0, rx1 + 1)
        if rx0 <= x0 and rx1 >= x1:                  # a full-width strip moves Z
            if rz1 >= z1:
                z1 = min(z1, rz0 - 1)
            if rz0 <= z0:
                z0 = max(z0, rz1 + 1)
    return x0, x1, z0, z1


def _site_order(spec: dict) -> list:
    """The order modules are SITED in, which is not the order they are written in.

    `bays` packs in list order, so a module listed late finds the grid full of kiosks and reports
    NO SITE - the Colour Wheel did exactly that three times before anyone noticed. The rule is
    "biggest first", and for a while it was kept BY HAND in the theme lists. That went wrong the
    first time it was actually checked: ordered by the hand-typed `size`, a tower DECLARING 15x15
    but MEASURING 13x13 led every zone while being the smaller module. **A step that has to be
    remembered is a step that gets lost** - the same finding that turned the shop islet's hand-cut
    well into `finish.carve_for` - so the order is DERIVED here, from `measured_footprint`, which
    is what the packer actually consumes.

    Three groups, and the order between them is load-bearing:

      EDGE/CENTRE  first. A gate's position IS its meaning, it is not negotiable, and it claims
                   its box. Sited late, a ride has already taken the edge and the gate slides
                   somewhere it does not belong - which is how Park Gate once landed on Guest
                   Services.
      FREE         next, by DESCENDING MEASURED AREA. The rule this function exists for.
      COVER        last. A covering module is not competing for space, it IS the space, so it
                   must see every room already placed. Listed first it lays its floor under
                   nothing.
    """
    edge, free, cover = [], [], []
    for m in spec["modules"]:
        a = m.get("anchor")
        # `junction` is a PREFERENCE, not a pin, so it stays in the free group and keeps its
        # place in the size order - which is the whole reason it cannot starve anything.
        grp = (cover if a == "cover"
               else edge if a in ("edge", "centre", "origin") else free)
        grp.append(m)

    def area(m):
        _fx, _fy, _fz, fw, _fh, fd = measured_footprint(
            m["gen"], m["kind"], dict(m.get("params", {})), m["size"])
        return fw * fd

    free.sort(key=area, reverse=True)

    # **A DISTRICT IS SITED CONSECUTIVELY, OR NAMING IT BUYS ALMOST NOTHING.** Sorted purely by
    # area, a district's members are placed at wildly different moments - the Assay Office is the
    # third module of the Frontier and the Prize Office the fourteenth - and by the time the
    # second one is looking for a spot, every bay near the first has been taken by something
    # else. Measured: the pair came out 78 cells apart on a 99-cell plot, which is two ends of
    # the land rather than one counter.
    #
    # So the biggest member still decides WHERE a district starts - the rule this function exists
    # for is untouched, and a large module still gets the pick of the plot - and the rest of the
    # district follows immediately behind it, largest first. A module with no district keeps its
    # place in the ordinary queue.
    ordered, seen = [], set()
    by_district = {}
    for m in free:
        if m.get("district"):
            by_district.setdefault(m["district"], []).append(m)
    for m in free:
        if id(m) in seen:
            continue
        group = by_district.get(m.get("district")) or [m]
        for member in group:
            if id(member) not in seen:
                seen.add(id(member))
                ordered.append(member)
    return edge + ordered + cover


def make(brief: str, world: str, name: str | None = None, theme: str | None = None,
         plot_from: str | None = None, spacing: int = 2, island: str | None = None,
         plane: int | None = None) -> Plan:
    """Site a theme's modules on real ground and cost them. Nothing is generated yet.

    `island` names an entry in the island registry, so a plan can target a DIFFERENT island from
    the one this tooling grew up on - which is the whole point of a fresh plot for the casino. The
    plot then comes from that registry entry rather than from the capture's own bedrock, so a
    capture that happens to include two islands cannot pick the wrong square.
    """
    theme = theme or _theme_for(brief)
    if theme not in THEMES:
        raise ValueError(f"no theme {theme!r}; have {sorted(THEMES)}")
    spec = THEMES[theme]
    pl = Plan(name or theme, theme, brief)

    sc = scan_mod.load(world)
    try:
        if island:
            from . import islands as islands_mod
            pl_plot = islands_mod.plot_of(island)
            if pl_plot is None:
                raise ValueError(f"no island called {island!r} - "
                                 f"python -m mcbuild islands --add {island} --from {world}")
            pl.island = island
            pl.notes.append(f"island {island} (owner {islands_mod.owner(island) or '-'}): {pl_plot}")
        else:
            pl_plot = plot_mod.find(plot_from or world)
            pl.notes.append(f"plot {pl_plot}")
    except Exception as e:                                       # noqa: BLE001
        pl_plot = None
        # NOT FOUND IS NOT INSIDE. A boundary guard that silently passes everything is the failure
        # it exists to prevent, so the plan says so rather than quietly siting off the island.
        pl.notes.append(f"PLOT UNKNOWN ({e}) - nothing is boundary-checked")

    # A SKYBLOCK PLOT HAS NO GROUND, and requiring some is how a correct planner refuses a
    # perfectly buildable island. A fresh island is a 12x12 starter pad in 99x99 of void: every
    # pad search returns nothing and every module reports NO SITE, which reads as "the terrain is
    # awkward" when the truth is that there is no terrain at all.
    #
    # `plane` is the answer, and it is a DECLARATION rather than a discovery: you say which course
    # the gaming floor stands on and the modules are laid out on the grid at that height. Every
    # other guard still applies - the plot boundary, the overlap between modules, the vertical
    # stacking - because those are the ones that are about correctness rather than about terrain.
    #
    # Each module carries its own floor and its own pit floor, so nothing hangs unsupported once
    # it is built; what a plane cannot promise is something to place the FIRST block against, and
    # the plan says so rather than letting the printer discover it.
    band = None if plane is not None else ground_band(sc)
    if plane is not None:
        pl.notes.append(f"sited on a DECLARED BUILD PLANE at Y{plane} - this plot has no ground, "
                        f"so the layout is the grid and each module carries its own floor")
        pl.notes.append("the first module has nothing to place against: stand a starter platform "
                        "under the gaming floor, or build outward from the island's own pad")
    if band:
        pl.notes.append(f"ground band Y{band[0]}..{band[1]} (modal surface) - "
                        f"nothing is sited on a rooftop or a sculpture")
    # A MODULE BIGGER THAN THE PLOT CAN NEVER BE SITED, and finding that out as "NO SITE" after a
    # full pad search reads like the ground being awkward rather than the design being impossible.
    for mspec in spec["modules"]:
        w_, _h, d_ = mspec["size"]
        if w_ > MAX_FOOTPRINT or d_ > MAX_FOOTPRINT:
            pl.notes.append(f"{mspec['name']}: {w_}x{d_} is larger than the {MAX_FOOTPRINT}x"
                            f"{MAX_FOOTPRINT} plot - it cannot fit at any position")
    floors = spec.get("floors") or [{"name": "Ground", "y": 0}]
    if len(floors) > 1:
        pl.notes.append(f"stacked over {len(floors)} floor(s): "
                        + ", ".join(f"{f['name']} at +{f['y']}" for f in floors)
                        + " - the plot is 99x99 but the vertical is free")
    # WHAT IS ALREADY THERE AND USED IS NOT SITE, and the planner only ever checked itself.
    #
    # `_clear` compares module against module, so on a fresh island `High Roller 6` sited straight
    # over the STARTER CHEST - the one holding everything the alt owns - and shipped with a single
    # overlap and no placement problem. Rule 10 has been in this project for a year (leave about
    # three blocks of working room around anything you stand at and use); nothing had ever applied
    # it at the SITING stage, because on the main island the ground search happened to avoid them.
    #
    # A used block is seeded into `taken` as a box, so it costs nothing new: the same clearance
    # test that keeps two modules apart keeps a module off a chest.
    #
    # **AND ON A GREENFIELD PLOT THAT RULE DENIES THE WHOLE BUILD.** A fresh skyblock island has
    # exactly one chest, and it sits AT THE CENTRE. A 44-wide module gets two bay columns out of a
    # 99-wide plot and the chest's 7x7 clearance box straddles both, so a single starter chest
    # reported NO SITE for the Haunted Manor, the Mine Coaster AND the Log Flume - the three
    # headline pieces of the park, each silently refused by a box nobody would keep.
    #
    # Rule 10 is right and stays on by default: it exists because a module once sited its floor
    # over the starter chest holding everything an alt owned. What is wrong is applying it
    # unconditionally to a plot that is BEING CLEARED to build on. So a theme may declare
    # `greenfield`, and when it does the containers are not treated as fixtures - but every one is
    # NAMED IN THE PLAN and listed for removal, because a container silently built over is the
    # exact loss this rule was written after.
    # **A THEME MAY SET ITS OWN SPACING, and a park wants NONE of it.** The gap between two
    # casino games is circulation; the gap between two fairground buildings is the AVENUE, which
    # the path pass draws separately and which is five cells wide, plus a three-wide spur to every
    # door. Paying for circulation twice cost the frontier its shooting gallery and the hollow its
    # clock tower and its crypt, and at one cell it was still refusing a prize counter and a high
    # striker at 64% used. Buildings on a fairground street stand shoulder to shoulder; the
    # measured footprint already includes each module's own apron, so zero here is a party wall,
    # not two buildings sharing a cell - which `_clear` still forbids.
    spacing = int(spec.get("spacing", spacing))
    _own_for_siting = _owned_bounds(pl_plot, spec) if pl_plot is not None else None
    taken: list = []
    # **INFRASTRUCTURE IS RESERVED BEFORE THE BUILDINGS ARE PACKED, or it has nowhere to land.**
    # The transit line runs a fixed corridor down the east of all three plots and its stations
    # reach into each zone at platform level. As soon as the packer learned to hug the boundary
    # the parks filled that corridor - 270 cells of collision, and the railway had been sited
    # against a layout two packing changes old. A theme declares the strips it does not own.
    for (rx0, rz0, rx1, rz1) in spec.get("reserve", ()):
        taken.append((rx0, (plane or 0) - 8, rz0, rx1 - rx0 + 1, 64, rz1 - rz0 + 1))
    used = list(_used_cells(sc))
    if spec.get("greenfield") and used:
        pl.notes.append(
            f"GREENFIELD: {len(used)} container/fixture cell(s) are NOT treated as fixtures "
            f"here - {', '.join(f'{x} {y} {z}' for (x, y, z) in used[:4])}"
            + (" ..." if len(used) > 4 else "")
            + ". Empty and break them before printing; on a fresh plot this is the starter chest, "
              "and its keep-clear box otherwise refuses every module wider than about 40.")
    else:
        for (ux, uy, uz) in used:
            taken.append((ux - USE_CLEAR, uy - USE_CLEAR, uz - USE_CLEAR,
                          USE_CLEAR * 2 + 1, USE_CLEAR * 2 + 1, USE_CLEAR * 2 + 1))
    for mspec in _site_order(spec):
        fx, fy, fz, fw, fh, fd = measured_footprint(
            mspec["gen"], mspec["kind"], dict(mspec.get("params", {})), mspec["size"])
        # **A MODULE THAT WILL BE TURNED MUST RESERVE A SQUARE.** Orientation is decided after
        # siting - it depends on where the module landed relative to the hub - and turning a 9x7
        # building through 90 degrees makes it 7x9, which no longer fits the slot that was
        # reserved for it. Booking the larger dimension on both axes means any of the four
        # facings fits the same slot, so the turn can never push a building into its neighbour.
        # It costs a little packing efficiency and the plots are 13% used.
        # A module may opt OUT of the square reservation. It matters at ride scale: a 16x55
        # shop street would book 55x55 - a third of the plot - to hold a rotation it does not
        # need, because its frontage IS its design. Such a module can still be FLIPPED 180
        # degrees, which leaves the footprint identical, so it can still choose which side of
        # its own axis to address; only the 90-degree turn is denied it.
        orient = (bool(spec.get("orient")) and mspec.get("anchor") != "cover"
                  and mspec.get("orient", True))
        bw = bd = (turn_extent(mspec["gen"], mspec["kind"], dict(mspec.get("params", {})),
                               mspec["size"]) if orient else 0)
        for i in range(int(mspec.get("count", 1))):
            size = ([bw + spacing, fh, bd + spacing] if orient
                    else [fw + spacing, fh, fd + spacing])
            # **THE FLOOR'S LIFT HAS TO REACH THE COLLISION TEST, NOT ONLY THE MODULE
            # DICT.** `_clear` has always compared boxes in three dimensions, and the lift
            # was applied afterwards - so a ride on an Undermine floor 24 courses down still
            # claimed its surface footprint against everything else, and moving the mine
            # underground bought the town exactly nothing. The three free-siting branches
            # site at `level`, which is the plane plus the floor's own offset; the edge,
            # centre, origin and cover branches stay on the plane, because a gate on a
            # different storey is not a gate.
            lift = floors[min(int(mspec.get('floor', 0)), len(floors) - 1)]['y']
            level = plane if plane is None else plane + lift
            spot = None
            taken_box = None
            bay = None
            turned_params = None
            # A COVERING MODULE IS NOT COMPETING FOR SPACE, IT IS THE SPACE.
            #
            # The hall's whole job is to lay the ground under and between the rooms, so the
            # overlap test that keeps two games apart is exactly wrong for it: asked to find a
            # free bay it correctly reported NO SITE, because by then the plane is full of rooms.
            # It is centred on the plot instead, and it claims nothing, so nothing sited after it
            # is pushed out.
            if mspec.get("anchor") == "cover" and pl_plot is not None and plane is not None:
                x0, x1, z0, z1 = _owned_bounds(pl_plot, spec)
                cw, cd = size[0] - spacing, size[2] - spacing
                bx = x0 + max(0, ((x1 - x0 + 1) - cw) // 2)
                bz = z0 + max(0, ((z1 - z0 + 1) - cd) // 2)
                pl.modules.append({
                    "name": mspec["name"], "gen": mspec["gen"], "kind": mspec["kind"],
                    "at": [bx - fx, plane, bz - fz], "size": [fw, fh, fd], "roll": 0,
                    "declared_size": list(mspec["size"]), "anchor_offset": [fx, fy, fz],
                    "floor": floors[0]["name"], "covers": True,
                    "params": dict(mspec.get("params", {})), "world": world,
                })
                continue
            # A CENTREPIECE BELONGS AT THE CENTRE, and that is not a thing the packer can know.
            #
            # `cover` centres a module and claims NOTHING, because it is the ground. A hero object
            # is the opposite: it must be at the middle AND own its box, so the avenues cross at
            # it and everything else keeps clear. Left to the bay packer a monument lands wherever
            # there happened to be a slot, which for the one thing the whole zone is arranged
            # around is the same mistake as siting the gate in the middle of a field.
            # **THE ONE COORDINATE THAT CANNOT BE NEGOTIATED IS THE ONE THE SERVER CHOOSES.**
            # A player is put down at the island's bedrock, and on this plot the Monument was
            # built straight across it: 2,105 of its blocks stood inside the volume an arrival
            # needs, with zero standable cells within three blocks at street level. Every check
            # passed - legal, supported, cheap, one connected piece, every door on the street -
            # because nothing ever asked whether the cell a player ARRIVES in is a cell a player
            # can STAND in. `origin` pins a module to the bedrock and claims its box, so the
            # arrival court is sited first and everything else keeps out of it.
            if mspec.get("anchor") == "origin" and pl_plot is not None and plane is not None:
                bcx, bcz = pl_plot.cx, pl_plot.cz
                bx, bz = bcx - fw // 2, bcz - fd // 2
                taken.append((bx, plane + fy, bz, fw, fh, fd))
                pl.modules.append({
                    "name": mspec["name"], "gen": mspec["gen"], "kind": mspec["kind"],
                    "at": [bcx, plane, bcz], "size": [fw, fh, fd], "roll": 0,
                    "declared_size": list(mspec["size"]), "anchor_offset": [fx, fy, fz],
                    "floor": floors[0]["name"], "arrival": True,
                    "params": dict(mspec.get("params", {})), "world": world,
                })
                continue
            if mspec.get("anchor") == "centre" and pl_plot is not None and plane is not None:
                x0, x1, z0, z1 = _owned_bounds(pl_plot, spec)
                bx = x0 + ((x1 - x0 + 1) - fw) // 2
                bz = z0 + ((z1 - z0 + 1) - fd) // 2
                taken.append((bx, plane + fy, bz, fw, fh, fd))
                pl.modules.append({
                    "name": mspec["name"], "gen": mspec["gen"], "kind": mspec["kind"],
                    "at": [bx - fx, plane, bz - fz], "size": [fw, fh, fd], "roll": 0,
                    "declared_size": list(mspec["size"]), "anchor_offset": [fx, fy, fz],
                    "floor": floors[0]["name"], "centrepiece": True,
                    "params": dict(mspec.get("params", {})), "world": world,
                })
                continue
            # AN EDGE MODULE IS A THRESHOLD, AND A THRESHOLD IS ONLY A THRESHOLD ON THE BOUNDARY.
            #
            # A gate sited by `bays` lands wherever there happens to be a free bay, which is a
            # gatehouse in the middle of a field: you walk round it. Same for the arches that lead
            # to the neighbouring zones - an arch to the west that is not ON the western edge does
            # not point anywhere. So `anchor: edge` pins the module against the named side and
            # centres it along that side, and unlike `cover` it DOES claim its box, because
            # everything else must keep out of the doorway.
            if mspec.get("anchor") == "edge" and pl_plot is not None and plane is not None:
                x0, x1, z0, z1 = _owned_bounds(pl_plot, spec)
                side = mspec.get("side", "south")
                if side in ("west", "east"):
                    bx = x0 if side == "west" else x1 - fw + 1
                    bz = z0 + max(0, ((z1 - z0 + 1) - fd) // 2)
                else:
                    bz = z0 if side == "north" else z1 - fd + 1
                    bx = x0 + max(0, ((x1 - x0 + 1) - fw) // 2)
                # **AN EDGE MODULE MUST STAY ON ITS EDGE, BUT IT CAN SLIDE ALONG IT.** This branch
                # pinned and claimed without ever asking `_clear`, so the Park Gate was dropped
                # straight onto Guest Services - the only module-against-module collision in the
                # whole park, and one no amount of care in the bay packer could have prevented,
                # because the edge branch never consulted it. Centred first, then outward along
                # the edge in both directions; if the whole edge is full it is REPORTED rather
                # than silently overlapping, since a gate you cannot reach is not a gate.
                esize = [fw + spacing, fh, fd + spacing]
                along_z = side in ("west", "east")
                lo, hi = (z0, z1 - fd + 1) if along_z else (x0, x1 - fw + 1)
                start = bz if along_z else bx
                # **AND WHEN THE WHOLE EDGE IS FULL IT STEPS INWARD RATHER THAN OVERLAPPING.**
                # Reserving the backstage band pushed the Big Wheel eight cells in, onto the
                # Arrival Court, which is pinned to bedrock and cannot move - and the branch
                # shipped the collision with a note. A landmark a few cells off its edge is
                # a landmark; one built through the arrival court is a bug in the world.
                inward = {"west": (1, 0), "east": (-1, 0),
                          "north": (0, 1), "south": (0, -1)}[side]
                placed, moved = False, 0
                for step in range(0, 13):
                    sx, sz = bx + inward[0] * step, bz + inward[1] * step
                    for off in range(0, (hi - lo) + 1, 2):
                        for cand in ({start + off, start - off} if off else {start}):
                            if not (lo <= cand <= hi):
                                continue
                            tx, tz = (sx, cand) if along_z else (cand, sz)
                            if _clear(taken, tx, plane + fy, tz, esize):
                                bx, bz, placed, moved = tx, tz, True, step
                                break
                        if placed:
                            break
                    if placed:
                        break
                if placed and moved:
                    pl.notes.append(f"{mspec['name']}: its {side} edge was full - stepped "
                                    f"{moved} cells inward to clear what was already sited")
                if not placed:
                    pl.notes.append(f"{mspec['name']}: its {side} edge is full - placed at the "
                                    f"centred position and OVERLAPPING something already sited")
                taken.append((bx, plane + fy, bz, fw, fh, fd))
                pl.modules.append({
                    "name": mspec["name"], "gen": mspec["gen"], "kind": mspec["kind"],
                    "at": [bx - fx, plane, bz - fz], "size": [fw, fh, fd], "roll": 0,
                    "declared_size": list(mspec["size"]), "anchor_offset": [fx, fy, fz],
                    "floor": floors[0]["name"], "edge": side,
                    "params": dict(mspec.get("params", {})), "world": world,
                })
                continue
            # THE GRID FIRST, so the plot is used rather than a strip of it. Each bay still has to
            # pass the SAME ground test a free-form pad would - flat enough, in the band, free -
            # because a tidy grid over rolling terrain is still a build on rolling terrain.
            if plane is not None and pl_plot is not None:
                _gb = _plot_bounds(pl_plot)
                # **A DISTRICT IS SITED TOGETHER, OR IT IS NOT A DISTRICT.** PARK_HOLLOW.md:
                # "stop treating eleven small modules as equal attractions" - and the reason the
                # Hollow reads as eleven machines on paving is that the packer sorts by CONTACT
                # with anything already there, which hugs whichever neighbour happens to be
                # nearest and scatters a market across the plot. A module that names a district
                # prefers the bays nearest what its own district has already claimed; when the
                # district has nothing yet, or nothing near enough is free, it falls back to the
                # ordinary rule rather than reporting NO SITE. Grouping is a preference, and a
                # sited module beats a tidy one.
                _here = _district_box(pl.modules, mspec.get("district"))
                if mspec.get("anchor") == "junction":
                    _here = _centre_box(pl_plot, spec)
                if _here is not None:
                    _bays = sorted(bays(pl_plot, size, spacing=1),
                                   key=lambda t: (_box_gap(t[0], t[1], size, _here),
                                                  -_contact(t[0], t[1], size, taken, _gb)))
                else:
                    _bays = sorted(bays(pl_plot, size, spacing=1),
                                   key=lambda t: -_contact(t[0], t[1], size, taken, _gb))
                for (bx, bz) in _bays:
                    # bays() hands back where the BUILD goes; the anchor is offset from it
                    ax, az = bx - fx, bz - fz
                    if not (pl_plot.contains(bx, bz)
                            and pl_plot.contains(bx + size[0], bz + size[2])):
                        continue
                    if _clear(taken, bx, level + fy, bz, size) and _sitable(
                            pl.modules, {"name": mspec["name"], "gen": mspec["gen"],
                                         "kind": mspec["kind"], "at": [ax, plane, az],
                                         "size": [fw, fh, fd], "anchor_offset": [fx, fy, fz],
                                         "params": dict(mspec.get("params", {}))}, _own_for_siting):
                        spot = (ax, plane, az, 0)
                        taken_box = (bx, level + fy, bz, bw or fw, fh, bd or fd)
                        # the RESERVED corner, kept so the module can be re-placed inside its own
                        # slot once its facing is chosen from where it landed
                        bay = (bx, bz, bw or fw, bd or fd)
                        break
            elif pl_plot is not None:
                for (bx, bz) in bays(pl_plot, size, spacing=1):
                    hits = [q for q in pads(sc, size, pl_plot, y_range=band, limit=4000)
                            if q[0] == bx and q[2] == bz]
                    if hits and _clear(taken, hits[0][0], hits[0][1], hits[0][2], size):
                        spot = hits[0]
                        break
            # **THE GRID IS COMPUTED PER MODULE SIZE AND KNOWS NOTHING ABOUT WHAT IS ALREADY
            # THERE, so one big module can deny every bay of every later one.** The 51x51 mine
            # coaster landed dead centre of a 99-wide plot; a 15x15 water tower's grid is five
            # columns at stride 16, and because the coaster spans 53 of the 99 EVERY column
            # clipped it - 25 bays, 25 refusals, against a `taken` list holding exactly one box.
            # Six of the Frontier's eight buildings were refused by one ride, with 23 blocks of
            # clear margin down each side that the grid simply had no position for.
            #
            # So when the grid is exhausted, scan on a fine step instead - the leftover margins
            # around a large neighbour are real site, and a grid is a layout convenience rather
            # than a constraint. Sorted by distance from the plot centre, so a park still packs
            # inward rather than scattering to the rim.
            if spot is None and plane is not None and pl_plot is not None:
                px0, px1, pz0, pz1 = _plot_bounds(pl_plot)
                cx0, cz0 = (px0 + px1) // 2, (pz0 + pz1) // 2
                # **THE STEP IS 2, NOT 4, AND THE DIFFERENCE IS WHOLE RIDES.** At a stride of 4
                # the midway sited its ferris wheel and its monument and then reported NO SITE
                # for the carousel, the swings AND the teacups - every ride in a fairground -
                # with the plot only 51% used. The leftover margins around two big neighbours
                # are real site and they are not on a 4-grid. Halving the stride is four times
                # the candidates for a search that is already bounded by the plot.
                # **AND THE MARGIN IS 1, WHICH IS THE OTHER HALF OF THE SAME BUG.** A monument
                # pinned to the plot centre leaves exactly two bands of 33 either side of it, and
                # a scan that starts three cells in can only ever offer a 33 a position that
                # overhangs the monument. Every ride in the midway was refused by three cells of
                # politeness. The box must simply END inside the plot: `bx + size - 1 <= px1`.
                # ...and it steps by ONE, because a stride of two has a PARITY. The band left by
                # a centred monument began at pz0 and the scan started at pz0+1, so every
                # candidate it offered overhung the monument by a single cell and the whole band
                # was invisible. A stride is an optimisation; on a 99x99 plot it was buying a few
                # milliseconds and costing three rides.
                cands = [(bx, bz)
                         for bz in range(pz0, pz1 - size[2] + 2)
                         for bx in range(px0, px1 - size[0] + 2)]
                # **BEST FIT, NOT NEAREST THE CENTRE.** Sorted by distance from the middle, every
                # module packs inward and the leftovers are a RING - wide, thin, and never square,
                # so the hollow reported NO SITE for its clock tower and its crypt with the plot
                # 51% used and a brute-force sweep finding no 18x18 anywhere. Preferring a spot
                # that HUGS what is already there - a neighbour's wall or the plot boundary -
                # leaves the free space in one piece instead of a dozen slots too narrow to use.
                # It is also what a street looks like: buildings shoulder to shoulder, not
                # scattered evenly over a field.
                _b = (px0, px1, pz0, pz1)
                # **AND THE DISTRICT PREFERENCE HAS TO BE HERE TOO, or it only half works.** The
                # grid branch learned it first and the Crypt Market still came out spread over
                # 79x91 - almost the whole plot - because the market's big modules never reach
                # the grid: a 42x27 vault exhausts every bay and lands in this fallback, which
                # sorted purely by contact and cheerfully hugged whichever wall was nearest.
                # Proximity to the district comes first, then contact, then the centre.
                _here = _district_box(pl.modules, mspec.get("district"))
                if mspec.get("anchor") == "junction":
                    _here = _centre_box(pl_plot, spec)
                if _here is not None:
                    cands.sort(key=lambda t: (_box_gap(t[0], t[1], size, _here),
                                              -_contact(t[0], t[1], size, taken, _b),
                                              (t[0] + size[0] // 2 - cx0) ** 2
                                              + (t[1] + size[2] // 2 - cz0) ** 2))
                else:
                    cands.sort(key=lambda t: (-_contact(t[0], t[1], size, taken, _b),
                                              (t[0] + size[0] // 2 - cx0) ** 2
                                              + (t[1] + size[2] // 2 - cz0) ** 2))
                for (bx, bz) in cands:
                    if _clear(taken, bx, level + fy, bz, size) and _sitable(
                            pl.modules, {"name": mspec["name"], "gen": mspec["gen"],
                                         "kind": mspec["kind"],
                                         "at": [bx - fx, plane, bz - fz],
                                         "size": [fw, fh, fd], "anchor_offset": [fx, fy, fz],
                                         "params": dict(mspec.get("params", {}))}, _own_for_siting):
                        spot = (bx - fx, plane, bz - fz, 0)
                        taken_box = (bx, level + fy, bz, bw or fw, fh, bd or fd)
                        bay = (bx, bz, bw or fw, bd or fd)
                        break
            # **AND IF IT WILL NOT FIT ONE WAY ROUND, TURN IT.** A module that opts out of the
            # square reservation keeps its rectangle - which is right, a 16x55 street should not
            # book 55x55 - but it also meant a 17x19 maze was refused outright by a plot holding
            # plenty of 19x17. `orient: False` says "do not book a square", not "never turn"; the
            # square exists so a turn decided AFTER siting is safe, and a turn decided DURING
            # siting needs no reservation at all because the footprint is measured at the facing
            # it will actually be built with.
            if spot is None and not orient and plane is not None and pl_plot is not None:
                _f = dict(mspec.get("params", {})).get("facing", "east")
                _alt = {"east": "north", "west": "north",
                        "north": "east", "south": "east"}[_f]
                _p2 = {**dict(mspec.get("params", {})), "facing": _alt}
                afx, afy, afz, afw, afh, afd = measured_footprint(
                    mspec["gen"], mspec["kind"], _p2, mspec["size"])
                asize = [afw + spacing, afh, afd + spacing]
                px0, px1, pz0, pz1 = _plot_bounds(pl_plot)
                _b = (px0, px1, pz0, pz1)
                acands = [(bx, bz)
                          for bz in range(pz0, pz1 - asize[2] + 2)
                          for bx in range(px0, px1 - asize[0] + 2)]
                # The district preference and rule 4 apply here too. This is the THIRD siting
                # path in this function and the last one to learn them: a module that only fits
                # turned is still a module of its district, and turning it does not exempt its
                # discharge from landing on somebody's queue. Prospecting Row came out spread
                # over 86x89 - the whole plot - because its turned member was placed by contact
                # alone.
                _ahere = _district_box(pl.modules, mspec.get("district"))
                if _ahere is not None:
                    acands.sort(key=lambda t: (_box_gap(t[0], t[1], asize, _ahere),
                                               -_contact(t[0], t[1], asize, taken, _b)))
                else:
                    acands.sort(key=lambda t: -_contact(t[0], t[1], asize, taken, _b))
                for (bx, bz) in acands:
                    if _clear(taken, bx, level + afy, bz, asize) and _sitable(
                            pl.modules, {"name": mspec["name"], "gen": mspec["gen"],
                                         "kind": mspec["kind"],
                                         "at": [bx - afx, plane, bz - afz],
                                         "size": [afw, afh, afd],
                                         "anchor_offset": [afx, afy, afz], "params": _p2}, _own_for_siting):
                        spot = (bx - afx, plane, bz - afz, 0)
                        taken_box = (bx, level + afy, bz, afw, afh, afd)
                        bay = (bx, bz, afw, afd)
                        turned_params, fx, fy, fz = _p2, afx, afy, afz
                        fw, fh, fd = afw, afh, afd
                        break

            if spot is None and plane is None:
                for (x, y, z, roll) in pads(sc, size, pl_plot, y_range=band, limit=4000):
                    if _clear(taken, x, y, z, size):
                        spot = (x, y, z, roll)
                        break
            label = mspec["name"] + (f" {i + 1}" if int(mspec.get("count", 1)) > 1 else "")
            if spot is None:
                why = ("no free bay left on the plane" if plane is not None
                       else "nothing flat enough and free")
                pl.notes.append(f"{label}: NO SITE - {why} at {size[0]}x{size[2]}")
                continue
            x, y, z, roll = spot
            # **A RESERVED BOX HOLDS THE BUILD, NOT THE BUILD PLUS ITS SPACING.** Stored
            # padded, every candidate then added its own padding on top and two modules ended up
            # FOUR cells apart where two was asked for. What it DOES hold is the square a
            # rotatable module reserved - drop that and a later module packs inside the space the
            # turn needs, which is how Runaway Mine ended up inside The Saloon - which sounds harmless and is not: the
            # hollow reported NO SITE for its maze, its crypt, its clock tower and its ride gate
            # with the plot 52% used, and a brute-force sweep found seventeen positions that fit.
            # The spacing belongs to the CANDIDATE, once.
            taken.append(taken_box or (x + fx, y + fy, z + fz, bw or fw, fh, bd or fd))
            pl.modules.append({
                "name": label, "gen": mspec["gen"], "kind": mspec["kind"],
                "district": mspec.get("district"),
                "at": [x, y + lift, z], "size": [fw, fh, fd], "roll": roll,
                "declared_size": list(mspec["size"]), "anchor_offset": [fx, fy, fz],
                "floor": floors[min(int(mspec.get("floor", 0)), len(floors) - 1)]["name"],
                "params": dict(turned_params or mspec.get("params", {})),
                "bay": list(bay) if bay else None,
                "square": bool(orient),
                "world": world,
            })
    # **A DISTRICT THAT COULD NOT BE LAID OUT TOGETHER SAYS SO.** The preference is exactly that
    # - a preference - and on a plot already holding a 47x47 coaster there is sometimes no
    # contiguous land left for a three-module row. Sited apart and reported, a reviewer can move
    # a ride or drop a module; sited apart and silent, the theme claims a street it does not have.
    for _name, _members in _districts_of(pl.modules).items():
        _gap = _district_spread(_members)
        if _gap > DISTRICT_SPREAD:
            pl.notes.append(
                f"district {_name!r}: its {len(_members)} modules span {_gap} cells - the plot "
                f"had no room to lay them out together, so it reads as separate buildings "
                f"rather than as one street")

    if spec.get("orient") and plane is not None:
        _orient_to_streets(pl, plane, _owned_bounds(pl_plot, spec)
                           if pl_plot is not None else None)
    # **THE INTERFACES ARE NAMED BEFORE THE STREETS ARE DRAWN, and that order is the whole
    # reform.** The path pass used to run one spur to one front-of-building point, which is
    # why 61 public anchors across the three lands stood on nothing: a building has more
    # than one way in and the pass only ever knew about one of them. The anchors exist
    # first now, and the streets are built to serve them.
    if theme in {"midway", "frontier", "hollow"} and plane is not None:
        from . import interfaces as _interfaces
        _interfaces.annotate(pl.modules, plane,
                             _owned_bounds(pl_plot, spec) if pl_plot is not None else None)
    if spec.get("paths") and plane is not None:
        _add_paths(pl, spec, plane, world, pl_plot)
    if spec.get("furniture") and plane is not None:
        _add_furniture(pl, spec, plane, world, pl_plot)
    # The path pass has always inferred public approaches. Make purpose and access an explicit
    # contract for every park module before it is emitted to agents or sidecars.
    if theme in {"midway", "frontier", "hollow"}:
        from .park_contracts import annotate as _annotate_park_contracts
        _annotate_park_contracts(pl.modules, _front_of, _inside_of)
    return pl


def _front_of(m):
    """The cell a visitor stands in to face this module's door, in world coordinates.

    `at` is the module's FRONT-LEFT corner and `d` runs from the front INTO the building, so the
    front face is the box edge in the +facing direction - not the minimum corner, and not the
    anchor. Getting this from the box rather than from `at` is the same lesson
    `measured_footprint` records: the declared anchor is not where the build actually is.
    """
    from .gen.park import _STEP
    ax, _ay, az = m["at"]
    ox, _oy, oz = m.get("anchor_offset", (0, 0, 0))
    w, _h, d = m["size"]
    x0, z0 = ax + ox, az + oz
    x1, z1 = x0 + w - 1, z0 + d - 1
    dx, dz = _STEP[m.get("params", {}).get("facing", "east")]
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    if dx:
        return ((x1 + 2) if dx > 0 else (x0 - 2), cz)
    return (cx, (z1 + 2) if dz > 0 else (z0 - 2))


_BACK_FACING = {"north": "south", "south": "north", "east": "west", "west": "east"}


def _street_axis(m, cx, cz):
    """Which avenue this module belongs to, and which way it must face to address it.

    Decided from the module's CENTRE rather than from its front, because the front is a function
    of the facing and this is what chooses the facing - reading it off the front would be circular
    and would let the orientation and the spur disagree about which avenue a building is on.
    Returns (facing, along_z) where along_z means it spurs perpendicular to the east-west avenue.
    """
    # **MEASURED FROM THE RESERVED SQUARE, NOT FROM THE BUILT BOX.** Turning a building moves
    # its box, which moves its centre, which can flip the very decision that turned it - one
    # module per zone came out facing one avenue while the recomputed answer named the other, so
    # its shopfront addressed one street and its spur ran to another. The reserved bay does not
    # move when the module turns, so deciding from it is stable by construction.
    bay = m.get("bay")
    if bay and len(bay) == 4:
        bx, bz, bw, bd = bay
        mx, mz = bx + bw // 2, bz + bd // 2
    else:
        x0, z0, x1, z1 = _box_of(m)
        mx, mz = (x0 + x1) // 2, (z0 + z1) // 2
    dx, dz = mx - cx, mz - cz
    if abs(dz) <= abs(dx):
        return ("north" if dz > 0 else "south"), True
    return ("west" if dx > 0 else "east"), False


def _orient_to_streets(pl, plane, own=None):
    """Turn every building to address the street it is joined to.

    **HALF OF THEM PRESENTED THEIR BACKS.** `facing` was a theme constant, so a booth sited north
    of the avenue faced exactly the same way as one sited south of it, and about half the park
    showed a blank rear wall to the street its own spur ran to. A shopfront that cannot be seen
    into is a shed.

    This runs AFTER siting because the answer depends on where the module landed, and it is only
    safe because siting reserved a SQUARE: turning a 9x7 building makes it 7x9, and re-measuring
    inside its own slot is what keeps it out of its neighbour. The edge modules are left alone -
    a gate faces out of the park by definition, which is the whole reason it is on the edge.
    """
    hub = next((m for m in pl.modules if m.get("covers")), None)
    if hub is None:
        return
    hx0, hz0, hx1, hz1 = _box_of(hub)
    cx, cz = (hx0 + hx1) // 2, (hz0 + hz1) // 2
    for m in pl.modules:
        # **AN EDGE MODULE IS LEFT ALONE ONLY WHEN IT IS A THRESHOLD.** A gate faces out of
        # the park by definition, which is the whole reason it is on the edge - but a
        # LANDMARK on the edge is not a threshold, and left facing outward its frontage
        # lands off the land the theme owns, where no street may go. The Hollow's Clock
        # Tower - the thing its own spec calls "the forward visual pull" - was presenting
        # its face to the reserved transit corridor for exactly this reason.
        threshold = m["kind"] in ("arch", "gate")
        if m is hub or (m.get("edge") and threshold) or m["kind"] == "paths" or not m.get("bay"):
            continue
        facing, _along_z = _street_axis(m, cx, cz)
        now = m["params"].get("facing")
        if facing == now:
            continue
        # A module that did not reserve a square may only be FLIPPED, never turned: a 180-degree
        # flip keeps the footprint identical, where a 90-degree turn swaps width for depth and
        # would overrun the slot booked for it.
        if not m.get("square") and facing != _BACK_FACING[now]:
            continue
        params = {**m.get("params", {}), "facing": facing}
        fx, fy, fz, fw, fh, fd = measured_footprint(
            m["gen"], m["kind"], params, m.get("declared_size", m["size"]))
        bx, bz = m["bay"][0], m["bay"][1]
        # **THE TURN CHECKS ITSELF, because a footprint is not necessarily the same at every
        # facing.** The reservation assumes a turn swaps width for depth and nothing else; the
        # Fortune Wheel's booth grew a roof on one side, so it measures 21 wide facing east and
        # 23 facing west, and flipping it walked two cells into a dead tree with every check
        # upstream correct. Predicting that per generator is whack-a-mole - three separate
        # reservation rules each fixed one zone and broke another. Trying the turn and DECLINING
        # it when it collides is local, general, and cannot be broken by a generator nobody has
        # written yet. A building that keeps its back to the street is a much smaller fault than
        # one built through its neighbour.
        turned = (bx, bz, bx + fw - 1, bz + fd - 1)
        # **A DOOR MAY NOT OPEN ONTO LAND THE THEME DOES NOT OWN.** Turned to address the nearer
        # avenue, a booth on the eastern edge of the owned strip ended up with its front on the
        # transit corridor's first column - a shopfront facing a railway, and a spur that could
        # never legally reach it. The turn is declined for the same reason it is declined for a
        # collision: keeping its back to the street is the smaller fault.
        clash = False
        # **AND THE TURNED BOX MUST STAY ON THE OWNED LAND.** Siting checks the reserve; the turn
        # pass re-places the module with a freshly measured footprint and was only checking its
        # NEIGHBOURS, so a module that had been sited clear of the transit corridor could be
        # turned into it - which is how the Mine Head ended up two cells over the railway with
        # every siting check correct.
        if own is not None and not (own[0] <= turned[0] and turned[2] <= own[1]
                                    and own[2] <= turned[1] and turned[3] <= own[3]):
            m["turn_declined"] = "the turned box leaves the land the theme owns"
            continue
        if own is not None:
            _saved = m["params"]
            m["params"] = params
            _fx, _fz = _front_of(m)
            m["params"] = _saved
            if not (own[0] <= _fx <= own[1] and own[2] <= _fz <= own[3]):
                m["turn_declined"] = "the turned front opens onto land the theme does not own"
                continue
        turned_y = (m["at"][1] + fy, m["at"][1] + fy + fh - 1)
        for other in pl.modules:
            if other is m or other is hub or other["kind"] == "paths":
                continue
            if _boxes_clash(turned, turned_y, other):
                clash = True
                break
        if clash:
            m["turn_declined"] = "the turned box walks into a neighbour"
            continue
        # **AND A TURN MAY NOT CREATE THE COLLISION SITING REFUSED.** Rule 4 is checked when a
        # spot is taken, and then this pass flips the building and moves every anchor with it -
        # so the Reliquary was sited clear of the Vault, turned to address the street it was
        # joined to, and came to rest with its collection point one cell off the Vault's queue
        # mouth. Every check upstream was correct. Declining the turn keeps its back to the
        # street, which is the smaller fault - the same trade this pass already makes for a
        # collision and for a door onto land the theme does not own.
        _probe = {**m, "params": params, "at": [bx - fx, m["at"][1], bz - fz],
                  "anchor_offset": [fx, fy, fz], "size": [fw, fh, fd]}
        # **THE SAME PREDICATE SITING USES.** A turn re-places a module, so it owes the same
        # two contracts a placement does - rule 4, and every public interface on the owned
        # land. The front-on-owned-land test above is ONE of eight interfaces; turned, a
        # ride at the eastern boundary put its emergency exit two cells into the transit
        # corridor, a fire exit onto a railway that no facing fixes and that siting had
        # already refused.
        if not _sitable([o for o in pl.modules if o is not m], _probe, own):
            m["turn_declined"] = "the turn breaks rule 4 or puts an interface off the land"
            continue
        m.pop("turn_declined", None)
        m["params"] = params
        # **A TURN MAY NOT FLATTEN A MODULE ONTO THE BUILD PLANE.** Both passes re-placed
        # a module at `plane`, which is right for everything standing on the ground and
        # silently undid the floor lift for anything that is not: the Frontier's mine ride
        # was sited 24 courses down, turned to address its street, and came back up into
        # the town it had just been moved out of - overlapping the headframe that is its
        # own entrance. A turn changes which way a module faces, and nothing else.
        m["at"] = [bx - fx, m["at"][1], bz - fz]
        m["anchor_offset"] = [fx, fy, fz]
        m["size"] = [fw, fh, fd]

    # **AND A SECOND PASS FOR THE DOORS THAT STILL POINT NOWHERE.** Declining a turn keeps a
    # module's ORIGINAL facing, which on the eastern edge of the owned strip is the theme's
    # default `east` - straight at the transit corridor. A booth whose door opens onto a railway
    # has no path to it and never will, so this is a repair rather than a preference: try every
    # facing and take the first whose front lands on owned land without walking into a neighbour.
    if own is not None:
        for m in pl.modules:
            # **THE SAME THRESHOLD RULE AS THE FIRST PASS.** Skipping every edge module
            # left the Clock Tower - a landmark, not a threshold - presenting its face to
            # the reserved transit corridor, which is the one direction no street may
            # reach. A gate faces out by definition; a tower on the edge does not.
            threshold = m["kind"] in ("arch", "gate")
            if m is hub or (m.get("edge") and threshold) or m["kind"] == "paths":
                continue
            if not m.get("bay") and not m.get("edge"):
                continue
            fx0, fz0 = _front_of(m)
            if own[0] <= fx0 <= own[1] and own[2] <= fz0 <= own[3]:
                continue
            bx, bz = (m["bay"][0], m["bay"][1]) if m.get("bay") else _box_of(m)[:2]
            for cand in ("east", "north", "west", "south"):
                if cand == m["params"].get("facing"):
                    continue
                params = {**m.get("params", {}), "facing": cand}
                cfx, cfy, cfz, cfw, cfh, cfd = measured_footprint(
                    m["gen"], m["kind"], params, m.get("declared_size", m["size"]))
                box = (bx, bz, bx + cfw - 1, bz + cfd - 1)
                box_y = (m["at"][1] + cfy, m["at"][1] + cfy + cfh - 1)
                if any(_boxes_clash(box, box_y, x) for x in pl.modules
                       if x is not m and x is not hub and x["kind"] != "paths"):
                    continue
                if not (own[0] <= bx and bx + cfw - 1 <= own[1]
                        and own[2] <= bz and bz + cfd - 1 <= own[3]):
                    continue
                probe = {**m, "params": params,
                         "at": [bx - cfx, m["at"][1], bz - cfz], "size": [cfw, cfh, cfd],
                         "anchor_offset": [cfx, cfy, cfz]}
                pfx, pfz = _front_of(probe)
                if not (own[0] <= pfx <= own[1] and own[2] <= pfz <= own[3]):
                    continue
                        # Rule 4 and the on-land rule again. This pass turns a module for a
                # different reason from the one above it and would otherwise re-create
                # exactly the placements that one declines - which is what it did: the
                # Reliquary was refused its flip by the first pass and given the same
                # flip by this one, two functions later.
                if not _sitable([o for o in pl.modules if o is not m], probe, own):
                    continue
                m.update(probe)
                break


def _y_span(m):
    """The courses a module occupies. Two modules on different bands may share a plan
    view and should: the Mine Head stands directly over the Mine Cart Escape, which is
    what a headframe IS, and a plan-view collision test called that a clash and refused
    to turn the headframe away from the railway."""
    y0 = m["at"][1] + m.get("anchor_offset", (0, 0, 0))[1]
    return y0, y0 + m["size"][1] - 1


def _boxes_clash(a_box, a_y, b) -> bool:
    b_box, b_y = _box_of(b), _y_span(b)
    if not (a_y[0] <= b_y[1] and b_y[0] <= a_y[1]):
        return False
    return (a_box[0] <= b_box[2] and b_box[0] <= a_box[2]
            and a_box[1] <= b_box[3] and b_box[1] <= a_box[3])


def _inside_of(m):
    """The cell a visitor stands in on the PARK side of a threshold - the opposite of `_front_of`.

    An edge module faces outward by definition, so its front approach lies beyond the plot; the
    street has to meet it where the park is.
    """
    from .gen.park import _STEP
    x0, z0, x1, z1 = _box_of(m)
    dx, dz = _STEP[m.get("params", {}).get("facing", "east")]
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    if dx:
        return ((x0 - 2) if dx > 0 else (x1 + 2), cz)
    return (cx, (z0 - 2) if dz > 0 else (z1 + 2))


def _box_of(m):
    ax, _ay, az = m["at"]
    ox, _oy, oz = m.get("anchor_offset", (0, 0, 0))
    w, _h, d = m["size"]
    return (ax + ox, az + oz, ax + ox + w - 1, az + oz + d - 1)


def _add_paths(pl, spec, plane, world, pl_plot=None):
    """Build the land's circulation from its declared interfaces, and record it on the plan.

    **THE STREETS SERVE THE ANCHORS, NOT THE FRONT DOORS.** This used to run one 3-wide spur from
    one front-of-building point per module, and measured against the interface schema that left
    61 public anchors across the three lands standing on nothing - every ride exit, every
    emergency exit, every flank queue mouth, every view approach. A building has more than one way
    in; a pass that knows about one of them cannot satisfy rule 2.

    `circulation.build` owns the geometry and `pathgraph` owns the rules over it. What stays here
    is the bookkeeping only the planner can do: the obstacle list the plaza plants around, and
    inserting the paths module ahead of the plaza so the streets are not painted over.
    """
    from . import circulation

    hub = next((m for m in pl.modules if m.get("covers")), None)
    if hub is None:
        return
    hx0, hz0, hx1, hz1 = _box_of(hub)
    cx, cz = (hx0 + hx1) // 2, (hz0 + hz1) // 2

    # **AGAINST THE LAND THE THEME OWNS, NOT THE PLOT.** Clamped to the plot the avenues ran
    # straight into the reserved transit corridor and the railway and the park fought over 57
    # cells while every building sat correctly clear. The reserve has to shrink everything that
    # reads the plot's bounds.
    own = _owned_bounds(pl_plot, spec) if pl_plot is not None else (hx0, hx1, hz0, hz1)

    others = [m for m in pl.modules if m is not hub and m["kind"] != "paths"]
    obstacles = [list(_box_of(m)) for m in others]
    # **THE PLAZA IS HANDED THE SAME OBSTACLE LIST.** Its planting beds, trees, terrace and pool
    # are laid over the whole footprint and it has no other way of knowing where anything stands -
    # without this it plants a tree in a doorway and lays a bed across a spur. Measured over the
    # three real zones: 0 collisions with it, 20-53 without.
    # **A COPY, NOT THE SAME LIST.** The route boxes are appended to the plaza's obstacles so
    # it does not plant a tree in a spur - and handed the SAME list object, the paths module
    # got them too, which made every route an obstacle to itself. Not one lamp post was ever
    # placed in any zone: the lamp loop ran, found its own kerb "blocked", and skipped, and
    # the night pass then measured 2,943 route cells at block light 0.
    hub.setdefault("params", {})["obstacles"] = list(obstacles)

    routes = circulation.build(pl.modules, (cx, cz), own, plane)
    if not routes:
        return

    # **AND THE STREETS THEMSELVES ARE OBSTACLES TO THE PLANTING.** The plaza was handed the
    # buildings and told to keep clear of them, which it did - and then put a tree in the middle
    # of a spur. A route is a box like anything else.
    from . import pathgraph
    for route in routes:
        # A shaft carries a Y, so its endpoints are three-element; `pathgraph.cells`
        # already knows how to read either shape, and taking the box from the cells it
        # actually claims is both correct for an L and correct for a vertical run.
        claimed = pathgraph.cells(route)
        if not claimed:
            continue
        xs = [c[0] for c in claimed]
        zs = [c[1] for c in claimed]
        hub["params"]["obstacles"].append(
            [min(xs) - 1, min(zs) - 1, max(xs) + 1, max(zs) + 1])

    # The plan carries its own circulation so the gates can read it without re-deriving the
    # geometry - two derivations of one network is how a check and the thing it checks drift.
    pl.routes = routes
    _add_stairwells(pl, spec, plane, world)

    land = spec["modules"][0]["params"]["land"]
    # **INSERTED BEFORE THE PLAZA, NOT APPENDED AFTER IT.** `layers.slice_plan` resolves a
    # contested cell first-writer-wins in plan order, and the paving and the plaza occupy the same
    # course - appended last, every avenue would be overwritten by the plaza it crosses and the
    # park would have invisible streets. Buildings still come first and still win, which is the
    # order actually wanted: building over path over plaza.
    pl.modules.insert(pl.modules.index(hub), {
        "name": spec.get("paths_name", "Park Paths"), "gen": "park", "kind": "paths",
        "at": [cx, plane, cz], "size": [1, 5, 1], "roll": 0,
        "declared_size": [1, 5, 1], "anchor_offset": [0, 0, 0],
        "floor": pl.modules[0]["floor"], "covers": True,
        "params": {"land": land, "facing": "east", "routes": routes, "obstacles": obstacles},
        "world": world,
    })


def _add_stairwells(pl, spec, plane, world) -> None:
    """Build the stair that every declared shaft promises.

    **A SHAFT IS A CONTRACT AND SOMETHING HAS TO HONOUR IT.** `circulation` declares a vertical
    connection wherever a module stands off the build plane, and for a while nothing built one:
    the safety pass walked the Frontier's shaft course by course and found twelve cells of solid
    rock between the town and the mine landing it was supposed to reach. A route nobody digs is
    the decorative doorway rule 2 forbids, pointing downwards.

    `gen/stairwell.py` already does exactly this job - a cased shaft with a slab spiral in it,
    punched through the floor, kerbed and railed at the head so the hole reads as a stair rather
    than as a place to fall down - so this is a siting, not a new generator.
    """
    land = spec["modules"][0]["params"]["land"]
    for route in pl.routes:
        if route.get("role") != "shaft":
            continue
        (x, top, z), (_bx, bottom, _bz) = route["a"], route["b"]
        name = (route.get("name") or "Shaft").replace(" shaft", " Stair")
        pl.modules.append({
            "name": name, "gen": "stairwell", "kind": "stairwell",
            # `at` is the shaft's own column and the module is measured from it, so the module
            # box is the hole - which is what keeps anything else out of it.
            "at": [x, int(min(top, bottom)), z],
            "size": [7, int(abs(top - bottom)) + 1, 7],
            "declared_size": [7, int(abs(top - bottom)) + 1, 7],
            "anchor_offset": [-3, 0, -3],
            "floor": pl.modules[0]["floor"], "shaft": True,
            "params": {"land": land, "facing": "east",
                       "center": [int(x), int(z)], "radius": 1,
                       "y_bottom": int(min(top, bottom)), "y_top": int(max(top, bottom)),
                       "shaft_lamp_every": 5,
                       "under": world},
            "world": world,
        })


def _add_furniture(pl, spec, plane, world, pl_plot=None):
    """Dress the avenues with benches, planters, lamps and bins.

    **FURNITURE BELONGS TO THE STREET, NOT TO THE BAY GRID.** Listed as ordinary modules these
    would be handed to `bays`, which packs a 99x99 plot into a grid of slots and would scatter
    twenty benches evenly across the whole zone - including the middle of open ground nobody
    walks over. A bench in a field is not furniture, it is litter. So they are placed the way the
    lamp posts already are: ALONG the avenues the path pass has just drawn, at a fixed interval,
    set back to the kerb.

    Three rules, each of which produced a wrong-looking street first:

    - **THE INTERVAL MUST CLEAR THE WIDEST PIECE.** Every kind here carries its own paved pad -
      a bench measures 8x11, not 2x1 - so an interval shorter than the pad's own depth puts two
      pads through each other. It is derived from the measured footprints rather than typed.
    - **ALTERNATE KERBS.** Everything on one side reads as a fence; alternating gives a street.
    - **NOTHING IN THE CROSSING.** The two avenues meet at the hub and that square is the one
      place people gather, so a band around it is left clear.

    A piece that would land inside a building's box, off the plot, or on top of another piece is
    simply skipped - the street is dressed with what fits, and a missing bench costs nothing.
    """
    hub = next((m for m in pl.modules if m.get("covers") and m["kind"] != "paths"), None)
    paths = next((m for m in pl.modules if m["kind"] == "paths"), None)
    if hub is None or paths is None:
        return
    hx0, hz0, hx1, hz1 = _box_of(hub)
    cx, cz = (hx0 + hx1) // 2, (hz0 + hz1) // 2

    land = spec["modules"][0]["params"]["land"]
    wanted = list(spec["furniture"])
    if not wanted:
        return

    # measure once: the interval and the kerb offset both come off the real footprints
    sized = []
    for kind in wanted:
        # The declared size is only ever a FALLBACK for a kind that fails to build; every one of
        # these measures, so what is used is the real extent, pad included.
        fx, fy, fz, fw, fh, fd = measured_footprint(
            "streetfurniture", kind, {"land": land, "facing": "east"}, [9, 9, 9])
        sized.append((kind, fx, fy, fz, fw, fh, fd))
    step = max(max(fw, fd) for (_k, _x, _y, _z, fw, _h, fd) in sized) + 4
    kerb = max(max(fw, fd) for (_k, _x, _y, _z, fw, _h, fd) in sized) // 2 + 4

    obstacles = [list(_box_of(m)) for m in pl.modules
                 if not m.get("covers") and m["kind"] != "paths"]
    placed: list = []
    px0, px1, pz0, pz1 = (_owned_bounds(pl_plot, spec) if pl_plot is not None
                          else (cx - 40, cx + 40, cz - 40, cz + 40))

    def _free(x0, z0, x1, z1):
        if pl_plot is not None and not (px0 <= x0 and x1 <= px1
                                        and pz0 <= z0 and z1 <= pz1):
            return False
        for (bx0, bz0, bx1, bz1) in obstacles + placed:
            if x0 <= bx1 and x1 >= bx0 and z0 <= bz1 and z1 >= bz0:
                return False
        return True

    # **WALK THE AVENUES THAT WERE ACTUALLY DRAWN, not the plot they sit in.** An avenue is
    # clamped to the spread of the doors it serves, so it is routinely shorter than the plot -
    # and furniture stepped from `px0+6` to `px1-6` walked off both ends of it, leaving a bench
    # twenty blocks from the nearest paving in a zone whose whole street network is five wide.
    # The routes are already computed and sitting on the paths module; read them.
    lanes = {}
    for r in (paths["params"].get("routes") or []):
        # **THE AVENUES, NOT EVERY LIT ROUTE.** `lamps` used to mean "one of the two full-
        # length avenues" and now means "carries lighting", which is every public route -
        # so a bench-dressing pass keyed on it started walking frontage walks and shafts.
        # The role is what a spine IS; the lamp is a consequence of being one.
        if r.get("role") != "main_spine":
            continue
        a, b = r["a"], r["b"]
        (ax, az) = (a[0], a[2]) if len(a) > 2 else (a[0], a[1])
        (bx, bz) = (b[0], b[2]) if len(b) > 2 else (b[0], b[1])
        if az == bz:
            lanes["x"] = (min(ax, bx), max(ax, bx), az)
        elif ax == bx:
            lanes["z"] = (min(az, bz), max(az, bz), ax)

    n = 0
    # Both avenues, walked from one end to the other, dressing alternate kerbs.
    runs = [(axis, lo + 4, hi - 4, fixed)
            for axis, (lo, hi, fixed) in lanes.items() if hi - lo > 16]
    # **THE KERB IS A SEARCH, NOT A CONSTANT, AND THAT IS THE WHOLE DIFFERENCE.** Written with a
    # single fixed offset every piece landed either on the avenue or inside a building, and the
    # first run of this pass placed EXACTLY ZERO in a plot that is only half full: at 48% used,
    # the two strips either side of the two avenues happen to be where most of the frontages are.
    # Each piece carries its own paved pad - a bench measures 8x11, not 2x1 - so it needs real
    # room. Trying a ladder of setbacks and taking the first that fits puts a bench in the gap
    # BETWEEN two shopfronts instead of refusing to place one at all.
    # The ladder is short ON PURPOSE. Its job is to find room BETWEEN two frontages, not to
    # rehouse a bench in the middle of a field: past about three blocks of extra setback the
    # piece stops belonging to the street, which is the only reason it exists.
    setbacks = [kerb + k for k in (0, 2, 4, 6)]
    for (axis, lo, hi, fixed) in runs:
        t = lo
        while t <= hi:
            kind, fx, fy, fz, fw, fh, fd = sized[n % len(sized)]
            got = None
            # ALTERNATE SIDES, nearest setback first: everything on one kerb reads as a fence.
            first = 1 if (n % 2 == 0) else -1
            for off in setbacks:
                for side in (first, -first):
                    if axis == "x":
                        ax, az = t, fixed + side * off
                        facing = "north" if side > 0 else "south"
                    else:
                        ax, az = fixed + side * off, t
                        facing = "west" if side > 0 else "east"
                    # SKIP THE CROSSING: where the two avenues meet is where people gather,
                    # which is the one square that must not have a bin in the middle of it.
                    if abs(ax - cx) < step and abs(az - cz) < step:
                        continue
                    x0, z0 = ax - fw // 2, az - fd // 2
                    x1, z1 = x0 + fw - 1, z0 + fd - 1
                    if _free(x0, z0, x1, z1):
                        got = (x0, z0, x1, z1, facing)
                        break
                if got:
                    break
            if got:
                x0, z0, x1, z1, facing = got
                placed.append((x0, z0, x1, z1))
                pl.modules.append({
                    "name": f"{kind.title()} {len(placed)}",
                    "gen": "streetfurniture", "kind": kind,
                    "at": [x0 - fx, plane, z0 - fz], "size": [fw, fh, fd], "roll": 0,
                    "declared_size": [fw, fh, fd], "anchor_offset": [fx, fy, fz],
                    "floor": pl.modules[0]["floor"],
                    "params": {"land": land, "facing": facing},
                    "world": world,
                })
                n += 1
            t += step
    if placed:
        pl.notes.append(f"street furniture: {len(placed)} piece(s) along the avenues")


def _theme_for(brief: str) -> str:
    """Pick a theme from a brief, by keyword.

    DELIBERATELY DUMB, AND SAYS SO. This is the open-ended half of the problem and a keyword match
    is an honest placeholder for a judgement; what it must never do is guess silently, so an
    unmatched brief raises rather than defaulting to the only theme in the catalogue.
    """
    b = (brief or "").lower()
    # **A NAME BEATS A KEYWORD, AND THE TWO PASSES ARE THE WHOLE FIX.** Checked together, the
    # first theme whose EITHER test passes wins - so `midway`'s generic "theme park" keyword
    # swallowed "theme park frontier" and "theme park hollow" alike, and all three zones planned
    # as the centre. Both dry runs came back byte-identical, which is the only reason it was
    # caught: two different briefs producing the same 10,403-block plan is not a coincidence.
    #
    # An explicit name is the strongest possible signal a brief can carry, so it is resolved
    # first, across ALL themes, before any keyword is considered.
    for theme in THEMES:
        if theme in b:
            return theme
    for theme, spec in THEMES.items():
        if any(word in b for word in spec.get("keywords", [])):
            return theme
    raise ValueError(f"no theme matches {brief!r}; have {sorted(THEMES)}. "
                     f"Pass --theme explicitly, or add one to planner.THEMES")


def verify(pl: Plan, quiet: bool = True) -> Plan:
    """Generate every module in memory, inspect its circuits, and cost it.

    THIS RUNS BEFORE APPROVAL, WHICH IS THE ENTIRE POINT. A plan you approve should already know
    whether its machines work, what they cost and whether they fit - approving a list of names is
    approving nothing.
    """
    from . import circuit as circuit_mod, recipes as recipes_mod, coop
    from .gen import GENERATORS

    have = coop.load_storage()
    total = collections.Counter()
    for m in pl.modules:
        gen = GENERATORS.get(m["gen"])
        if gen is None:
            m["circuit"] = [f"unknown generator {m['gen']}"]
            continue
        params = {**m.get("params", {}), "at": m["at"], "kind": m["kind"],
                  "under": m.get("world"), "check": True}
        try:
            canvas = gen.build(params, [])
        except Exception as e:                                   # noqa: BLE001
            m["circuit"] = [f"BUILD FAILED: {e}"]
            continue
        model = canvas.to_model() if hasattr(canvas, "to_model") else canvas
        m["blocks"] = int((model.ids > 0).sum())
        meta = getattr(canvas, "meta", {}) or {}
        m["contract"] = meta.get("contract", "")
        for u in meta.get("unverified", []) or []:
            if u not in pl.unverified:
                pl.unverified.append(u)
        origin = getattr(canvas, "world_origin", None) or (0, 0, 0)
        if circuit_mod.has_redstone(model):
            m["circuit"] = [f"{k} at {p}: {d}"
                            for k, p, d in circuit_mod.inspect(model, origin)][:8]
        else:
            m["circuit"] = []
        for i, n in zip(*np.unique(model.ids[model.ids > 0], return_counts=True)):
            total[model.names[i].split(":")[-1]] += int(n)

    if total:
        plan_r = recipes_mod.plan(total, have) if recipes_mod.available() else None
        pl.cost = {"blocks": int(sum(total.values())),
                   "materials": len(total),
                   "short": dict(plan_r.short) if plan_r else {},
                   "from_stock": dict(plan_r.used) if plan_r else {}}
    return pl


def approve(name: str) -> Plan:
    pl = Plan.load(name)
    pl.approved = True
    pl.approved_at = _dt.datetime.now().isoformat(timespec="seconds")
    pl.save()
    return pl



def measured_expensive(gen: str, kind: str, params: dict) -> dict:
    """How many CURRENCY-tier blocks one of these modules really places.

    A marquee is sixteen redstone lamps and a lamp cannot be substituted by colour - the nearest
    cheap match is `acacia_planks`, which is a lamp that does not light. So the cost is real and
    the honest thing is to DECLARE it, exactly as the Island Run declares its thirteen slime
    blocks: the repo-wide eight-block ceiling stays meaningful for everything else, and the
    exception sits in the config where a reader meets it.
    """
    from .gen import GENERATORS
    from . import palette
    out: dict = {}
    try:
        probe = {**params, "at": [0, 64, 0], "kind": kind, "check": False}
        probe.setdefault("facing", "east")
        c = GENERATORS[gen].build(probe, [])
        m = c.to_model()
        import numpy as np
        for i, tag in enumerate(m.palette):
            try:
                name = tag.value["Name"].value.split(":")[-1]
            except Exception:                                    # noqa: BLE001
                continue
            n = int((m.ids == i).sum())
            if n and palette.tier(name) == "expensive":
                out[name] = out.get(name, 0) + n
    except Exception:                                            # noqa: BLE001
        return {}
    return out


def emit(name: str, out_dir: str = "configs") -> list:
    """Write one config per module — and REFUSE if the plan is not approved.

    The gate is here rather than in the CLI so that no other caller can route around it.
    """
    import yaml
    pl = Plan.load(name)
    if not pl.approved:
        raise PermissionError(
            f"plan {name} is not approved. Nothing is emitted until a human says yes: "
            f"python -m mcbuild plan --approve {name}")
    # THE ORIGIN LOCK IS OFF FOR A PLAN, AND BOTH HALVES OF THAT ARE DELIBERATE.
    #
    # The default lock is the MAIN island's corner, so a casino at 97588/80595 would pad from
    # -24251/29949 - a schematic the size of the world, which passes the pipeline's own
    # "lock <= natural origin" check because it really is below and west of everything.
    #
    # Deriving the lock from THIS island's plot corner fixes the size and is still wrong. The lock
    # exists so a design that regenerates cannot drift, and it pays for that with padding: each
    # module then shipped as a 47x13x40 box holding 224 blocks - 99% AIR - and all 29 placements
    # sat on one corner, overlapping, most of them looking empty from wherever you stand.
    #
    # A PLANNED MODULE DOES NOT NEED THE LOCK, because its `at` is pinned in the config by an
    # approved plan. The origin is already deterministic; the lock only adds air. So each design
    # hugs its own content and its placement sits where the module actually is.
    written = []
    prev: list = []
    for m in pl.modules:
        slug = m["name"].lower().replace(" ", "_")
        cfg = {
            "name": m["name"],
            "gen": m["gen"],
            # THE MODULE'S NAME REACHES THE BUILD, so the door sign says which room this is.
            # Without it every door in the casino reads "HIGH ROLLER" and a player cannot tell
            # one room from the next - which is most of what "it is not clear what any of the
            # games are" meant.
            "params": {**m.get("params", {}), "at": m["at"], "kind": m["kind"],
                       "title": m["name"], "under": m.get("world")},
            "finish": {"verify_against": m.get("world")},
        }
        contract = m.get("park_contract")
        if contract:
            cfg["park_contract"] = contract
            cfg["design"] = {
                "purpose": contract["purpose"], "hierarchy": contract["hierarchy"],
                "style": contract.get("land"),
                "narrative": f"{m['name']} serves the {contract.get('land', 'park')} visitor journey.",
            }
        cfg["origin_lock"] = False
        exp = measured_expensive(m["gen"], m["kind"], dict(m.get("params", {})))
        if exp:
            total = sum(exp.values())
            cfg["expensive_allowance"] = total
            cfg["expensive_reason"] = (
                "; ".join(f"{v}x {k}" for k, v in sorted(exp.items()))
                + " - a light cannot be substituted by colour (the nearest cheap match is a lamp "
                  "that does not light), so this cost is declared rather than hidden")
        # **NOTHING DEFERS ANY MORE, AND THAT IS THE POINT.**
        #
        # `defer_to` settles which design owns a shared cell, and it does that by DELETING the
        # cell from the loser - so every module became a fragment with holes in it, and looking at
        # the casino meant loading a pile of overlapping designs each missing pieces. Three rounds
        # of confusion came out of that, and none of it was ever about the casino.
        #
        # The modules are INTERMEDIATE artifacts now. Each is generated whole, overlaps and all;
        # the conflicts are resolved once, explicitly, in `layers.slice_plan`, which is also the
        # only place that knows the right precedence. What gets placed is the slice.
        p = os.path.join(out_dir, f"{slug}.yaml")
        with open(p, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
        written.append(p)
        prev.append(m["name"])
    return written


def upgrade_interfaces(name: str) -> Plan:
    """Give an existing park plan its typed interfaces and its role-typed circulation.

    **NOTHING IS RE-SITED.** An approved plan is a set of decisions about where things stand, and
    re-running `make` would quietly move them; what a plan written before the interface schema is
    missing is the CONTRACT, not the layout. So the anchors are derived from the boxes that are
    already there and the streets are rebuilt to serve them.

    A plan whose modules then fail a gate fails it honestly - that is the defect the schema exists
    to surface, and hiding it behind a re-site would be answering a different question.
    """
    from . import circulation, interfaces as _interfaces, islands
    plan = Plan.load(name)
    if plan.theme not in {"midway", "frontier", "hollow"}:
        raise ValueError(f"{name} is not a centre/left/right park plan")
    spec = THEMES[plan.theme]
    hub = next((m for m in plan.modules if m.get("covers") and m["kind"] == "plaza"), None)
    if hub is None:
        raise ValueError(f"{name} has no plaza to centre its streets on")
    hx0, hz0, hx1, hz1 = _box_of(hub)
    # The plan records the ISLAND it was sited on; the plot comes from that, not from a
    # coordinate. `plot_of` takes a name.
    plot = islands.plot_of(plan.island) if plan.island else None
    if plot is None:
        first = plan.modules[0]["at"]
        plot = islands.plot_of(islands.at(first[0], first[2]) or "")
    own = _owned_bounds(plot, spec) if plot is not None else (hx0, hx1, hz0, hz1)
    plane = int(hub["at"][1])

    _interfaces.annotate(plan.modules, plane, own)
    plan.routes = circulation.build(plan.modules, ((hx0 + hx1) // 2, (hz0 + hz1) // 2),
                                    own, plane)
    for module in plan.modules:
        if module["kind"] == "paths":
            module.setdefault("params", {})["routes"] = plan.routes
    plan.save()
    return plan


def upgrade_park_contracts(name: str) -> Plan:
    """Add public-purpose/access metadata to an existing park plan without re-siting anything."""
    plan = Plan.load(name)
    if plan.theme not in {"midway", "frontier", "hollow"}:
        raise ValueError(f"{name} is not a center/left/right park plan")
    from .park_contracts import annotate
    annotate(plan.modules, _front_of, _inside_of)
    plan.save()
    return plan
