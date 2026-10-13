"""Put the modules that ARE BUILT onto the ground layer, at their measured lots.

Jack: "unless we need size adjustments... use existing modules for major things like ferris wheel,
and only use new agents to build new things for the gaps of areas that we dont have things for."

**TWENTY-NINE MODULES WERE ALREADY BUILT** in `out/park_final/artifacts/` - 250,000 blocks
including the Sky Lift, the Mine Coaster and the Prism Ascent - and nothing was placing them,
because the assembly step still used `park_final.world.json`'s own `at` values. Those predate the
grid rework and the audit found them incompatible with any street plan: eight modules sat inside
the arrival spine band. `tools/park_lots.PLACEMENT` is the measured table that supersedes them.

    python tools/park_place.py            place every built module, report clashes
    python tools/park_place.py --ship     ...and merge to `Park Buildings` and ship it

THE FIVE `* Line` MODULES ARE SUPERSEDED AND SKIPPED. They are the old per-land path strips;
`Park Ways` is the ground layer now and draws all of it, so placing them would put two designs on
one surface - the exact thing `finish.defer_to` exists to stop, and the reason the casino was
sliced into layers rather than shipped as thirty overlapping fragments.

A MODULE'S OWN y=0 IS NOT ITS FLOOR. `parkbuild` records which course of each canvas is the build
plane in `planes.json` - a lot with a basement starts below it - so the vertical offset is
`plane - planes[name]`, never zero. Placed without it every below-plane reservation ends up in
the air, which is how the coaster once floated thirteen courses over its own ridge.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcbuild import nbt, printable, profile as mcprofile, scan, schem  # noqa: E402
from mcbuild.ops import declutter as declutter_op  # noqa: E402
from mcbuild.ops.declutter import report as declutter_report  # noqa: E402
from mcbuild.ops.unseen import hollow_unseen  # noqa: E402
from tools.park_lots import PLACEMENT  # noqa: E402

ARTIFACTS = ROOT / "out" / "park_final" / "artifacts"
#: superseded by `Park Ways` - see the module docstring
#: JACK KEPT THREE. "the ferris wheel itself, the merry go round itself, and the roller coaster
#: are worthy saves from that buildings bunch, everything else should be rebuilt to properly fit
#: themes, available spaces, etc, without the chaos that exists currently."
#:
#: So this is a KEEP list rather than a skip list, and the difference matters: a skip list grows
#: quietly wrong as modules are added, while a keep list can only ever place what somebody named.
#: `Carousel Court` and `Sky Lift` are now their ride and nothing else - part 0 of a compose of
#: seventeen and twenty-seven - because the courts around them were the chaos.
KEEP = {"Sky Lift", "Carousel Court", "Mine Coaster",
        #: AND THE WYRM, which is a SET PIECE rather than one of the "hollow buildings" Jack
        #: threw away - a pale hooded serpent on dark masonry, `gen/wyrm.py`'s own shape, and the
        #: only thing programmed for the Prism Reach. It was being dropped because the keep list
        #: named rides and nothing else, and that alone is why U377-429 measures as FIFTY-THREE
        #: COLUMNS OF NOTHING. A void that size is not restraint, it is a module nobody placed.
        "Wyrm's Crossing",
        #: AND THE WELCOME COURT, which was built and never placed because the keep list named
        #: rides. It is the stone court with trees and a water feature that the park's centre
        #: needed - Jack: "that center area where the ferris wheel should have a stone walk up,
        #: maybe a small fountain... a welcoming area that cleanly paths and directs them."
        "Welcome Court"}

#: V0 -> X, U0 -> Z, and the floor course. Derived by tools/park_anchor.py from the island
#: registry; stated here only so a shipped sidecar can carry it.
ANCHOR = (97500, 202, 80300)


def plane_of(model, role: str = "") -> int:
    """Which course of a module's own canvas is its GROUND, DERIVED rather than looked up.

    `parkbuild` writes this to `planes.json` - and a FILTERED rebuild REPLACES that file with only
    the modules it built, so rebuilding four of twenty-one reduced it to a single entry and every
    other module's plane silently became 0. The Mine Coaster's is 13: at 0 it hangs thirteen
    courses over its own ridge with 4,650 of its 4,662 columns touching nothing, which is exactly
    what "the rollercoaster is still floating in mid air" was. Nothing this cheap to measure
    should depend on a side file that a partial run can truncate.

    The rule is `parkbuild`'s own: the lowest course covering most of the module's own columns.
    A bare hanging creature is exempt - the Sloth's densest course is 23 up and lowering it by
    that would bury it in the deck - but a sculpture COMPOSED on its own apron does have ground.
    """
    sol = model.solid()
    if role == "sculpture":
        return 0
    cols = len({(int(x), int(z)) for _y, z, x in zip(*sol.nonzero())})
    per = sol.sum(axis=(1, 2))
    return next((int(y) for y, n in enumerate(per) if n >= 0.60 * cols), 0)


#: DESIGNS THAT ARE NOT LOT MODULES. A lake, a water garden, a set of frontage pieces or a summit
#: is not something `PLACEMENT` has a lot for - it sits in the space BETWEEN lots, or hangs off a
#: module that already stands. Each carries its own world origin in its own sidecar, so it is
#: placed from that rather than from a table, and the only thing this list decides is whether it
#: is placed at all.
#: ...and only the ones whose STREAM HAS LANDED. Four generators are written in parallel and a
#: half-finished design on disk is indistinguishable from a finished one - it loads, it audits, it
#: has an origin. Placing one would put a stream's working state into the shipped park and, worse,
#: make the next `--ship` look like a regression when it changed. A name goes in here when its
#: agent reports, not when its file appears.
EXTRAS_READY = {"PF Water Claim Lake", "PF Water Wyrm Garden",
                # THE EMPTY-GROUND CLEANUP. `extras()` places in filename order and every lot
                # module goes in before any of them, so a shrub can never take a cell a
                # BUILDING wanted; and it plants only where the composite it reads is already
                # open lawn, so it cannot take a cell from the extras placed after it either.
                # First writer wins, and a flower is worth less than anything else here.
                #
                # `PF Park Rim Green` is the protected V187-199 reserve, separately, at a
                # third of the density and capped at three courses. Drop it from this set to
                # leave the reserve as bare moss - see its own config for the trade.
                "PF Park Green", "PF Park Rim Green",
                # THE PLAQUES GO IN LAST OF THE FRONTIER'S DRESSING, so a plaque can never
                # take a cell the ground, the overgrowth or the rim wanted - first writer
                # wins, and a board a guest reads is worth less than the walk it stands on.
                "PF Plateau Plaques",
                # THE TWO SKIES (2026-09-13). Jack: *"add more sky elements that are
                # disconnected"*, then *"this applies to carnival area as well"*. Measured over
                # the park as placed, the Lost Plateau carried 0.88% of its mass above Y250 -
                # ONE object, the pterosaur, and it is perched on a crag - and the Midway had
                # 165 cells above Y270 and nothing at all over Y280.
                #
                # They are placed LAST of all the extras and it costs nothing to do so: both
                # hang in open air, so they contend for no cell with anything in the park and
                # the cross-design check reports zero against all 44 modules.
                "PF Plateau Skies", "PF Midway Skies",

                # **THE VANTAGE LOOKOUT IS RETIRED (2026-09-12).** Jack, looking north at the
                # land's far end: *"i think the tower is a cop out and feels lazy."* Measured off
                # the shipped composite it was exactly that - 4,154 blocks, 17 x 17, 56 courses,
                # and **100% of its own footprint standing at full height**, with one interactive
                # block in the whole of it. A shaft is the most height a lot can be given for the
                # least idea, and this one stood at the LAND'S CLIMAX: guests enter the Lost
                # Plateau from the Midway at U169 and walk north, so it was the last thing they
                # saw. Against the 2026-09-11 plot capture it was **345 of 4,943 built - 7%** - so
                # retiring it costs about three hundred placed blocks.
                #
                # `PF Broken Plateau`'s belvedere replaces it and keeps the skyline it was holding:
                # a timber deck that leaves the west lip at the rim and cantilevers out over the
                # gorge mouth, with a mast on it. The height is the same order and it is EARNED -
                # the drop is under your feet rather than something you climbed above.
                # `configs/pf_vantage_frontier_lookout.yaml`, its generator and its artifact all
                # stand as the record; this set is the one thing that decides what is placed.
                #     "PF Vantage Frontier Lookout",
                # THE BELVEDERE IS WITHDRAWN. Jack, standing on its crown: "there is a large
                # building/tower right next to the air balloon design... its squished between
                # the balloon and the railway" - and he was right to pull it rather than nudge
                # it. Its own docstring already recorded the squeeze it was built into: the door
                # opens straight onto the Circus ring at V138 because there was nowhere else on
                # this lot to put it, eighteen columns from the railway on the other side. A
                # vantage that has to touch both landmarks to fit is not sited, it is wedged.
                # Archived in archive/pf_vantage_midway_belvedere/.
                #     "PF Vantage Midway Belvedere",
                #
                # A SHOOTING RANGE WAS TRIED IN ITS PLACE AND WITHDRAWN TOO. `arcade._range`'s
                # concealed award floor runs 12 courses behind its visible booth - a 24-26 deep
                # footprint that left a bare service slab trailing off the back of the build,
                # correct by every offline check and visibly wrong the moment it was placed.
                # Jack: "this looks terrible in current state, the blocks are sticking out the
                # back etc." Archived in archive/claim_lake_range_v1/.
                #     "PF Claim Lake Range",
                #
                # A SMALL PETTING ZOO TAKES THE SQUARE INSTEAD. Jack: "maybe a small zoo where
                # we put actual MC animals" - `gen/menagerie.py` is fence, posts, four small
                # shelters and signs, nothing concealed and nothing behind its own back wall, so
                # there is nothing left to trail off it. The pens ship empty; stocking them with
                # real animals is Jack's own job in world. See configs/claim_lake_menagerie.yaml.
                "PF Claim Lake Menagerie",
                # THE SUMMIT IS WITHDRAWN AGAIN, and this time by measurement rather than by
                # caution: 2,709 of its 4,522 cells stand INSIDE the Prism Well's mouth. It
                # was a viewpoint over the Prism Ascent, and the Ascent is gone - the well
                # IS the viewpoint now, and its rim gallery is nine wide with eight balconies
                # oversailing the void. Archived in archive/prismworks_v1/.
                #     "PF Vantage Prism Summit",
                #
                # PRISMWORKS v2 - THE PRISM WELL. Four designs, and the ORDER MATTERS: the
                # rig is derived from the descent's recorded route and the floor is sited
                # against both. `tools/prismchain.py` builds them in sequence; this list only
                # places what that produced. See PRISMWORKS_V2_PLAN.md.
                "PF Prism Well", "PF Prism Descent", "PF Prism Rig", "PF Signal Zero",
                # ...and the SKY RUN, which carries the column on to Y300 and makes
                # Prismworks the park's tallest thing. Jack: "should we be building this
                # straight up as well so its a really complete big circuit".
                "PF Crown Descent",
                "PF Front Frontier", "PF Front Midway", "PF Front Prismworks",
                "PF Entry Gate",
                # THE FRONTIER'S MOUNTAIN AND ITS WORKS. `PF Mine Ridge` wraps the Mine Coaster
                # without taking one cell of it; `PF Mine Works` is the ore line, the stamp mill
                # and the dock. See configs/pf_mine_ridge.yaml and configs/pf_mine_works.yaml.
                #: `PF Prep Works` was `PF Mine Works` until 2026-09-12. Jack: "not sure theres
                #: a use for all them ... retheme it." It was the last MINING building in a land
                #: re-themed to palaeontology - and it was re-themed rather than retired because
                #: the plot capture says it is 37% built (2,806 placed blocks) and it carries the
                #: land's only moving mechanism. The rebuild is bit-identical: the name changed,
                #: the prose changed, three boards changed, and not one block moved.
                "PF Mine Ridge", "PF Prep Works",
                # **THREE GAMES WERE BUILT FOR THE FRONTIER AND NEVER PLACED.** Measured over the
                # shipped `Park Complete`, the whole land's interactive inventory was 646 rails,
                # 2 buttons, 2 bells and 2 detector rails - every verb in it belonging to the
                # coaster - while `out/PF Game Pan Line`, `Powder Striker` and `Prize Office` sat
                # on disk, generated, simulated and absent from the park. A design that is built
                # and unplaced is indistinguishable from one that was never written.
                "PF Game Pan Line", "PF Game Powder Striker", "PF Game Prize Office",
                # ...and the fourth, written for the Prospecting Porch's second bay,
                # which shipped as a shell with no circuit behind it.
                "PF Game The Riffle",
                # THE LAND DRESSING, and not one building in it. Measured, the Frontier's whole
                # flora was 29,488 moss blocks and ZERO LEAVES - not one tree in a land that is
                # 66% bare lawn. Jack: "i dont want a bunch of buildings to go into, this is just
                # a village then ... find other small things to add in the area."
                "PF Frontier Scatter",
                # **THE WEST HALF IS TERRAIN AND ONE EXCAVATION NOW.** Jack, on the re-themed land:
                # "its just buildings, the dig zone is crappy ... i really dont like this splatter
                # of buildings that dont look amazing and dont really do anything." Measured, its
                # columns A and B carried six buildings, 17,857 blocks and ONE interactive block.
                #
                # `PF Plateau Vale` is column A - jungle downland, four trial trenches and a single
                # arch where the Trailhead Gate's 45x39 of towers, court and stockade stood - and
                # `PF Plateau Bone Bed` is column B, ONE excavation across the Diggings' lot, Mining
                # Square's lot and the park's own cross walk between them, which it uses as the
                # causeway into the bottom of the pit rather than fighting.
                #
                # ORDER MATTERS: the vale carries the arch that straddles the U41-45 avenue and the
                # bone bed reserves the ground the three re-sited games stand on, so both go in
                # before the land dressing that keeps out of module lots.
                # **AND THE VALE IS REPLACED BY `PF Broken Plateau` (2026-09-12)**, on the same
                # lot, with the same responsibilities including the arch. Jack: *"this area of the
                # map feels very weak, the buildings have unclear purposes ... we need to redo this
                # area so it matches the wow factors of the other 2 sides."* Both of those wow
                # factors are terrain-scale geology with a route driven through it - the Mine Ridge
                # with a coaster bored through it, the Prism Well with a descent down it - and the
                # axis neither uses is OUT. The north end is the park's own rim with open void past
                # it, so the mass now runs to that boundary at full height and BREAKS, and a gorge
                # is cut back from the edge with the fossil bed in its walls.
                #
                # The Vale is kept whole on disk. Of its 4,542 built cells on this ground 4,046 are
                # the Y202 moss lawn, which is `Park Ways`' and stays.
                #     "PF Plateau Vale",
                "PF Broken Plateau", "PF Plateau Bone Bed",
                #: **AND THE FIELD SHOP ON THE LOT THE TOWER LEFT (2026-09-12).** Jack: "the lot
                #: where the tower was is empty ... maybe we keep 1 building and put another shop
                #: there", and on where: "tower lot". 17 x 17 at the land's climax, on the east
                #: verge of the V123-127 avenue looking across at the gorge mouth - so it is a
                #: shop AND the terrace the belvedere is seen from. Open-fronted, and it holds not
                #: one container: the board names the server's own `/shops`.
                #:
                #: It goes in AFTER the terrain and BEFORE the land dressing, like every other
                #: building here - the dressing keeps out of module lots and cannot do that for a
                #: lot that is not occupied yet.
                "PF Plateau Shop",
                #: **THE WORM IN THE LAST PLAZA (2026-10-13).** Jack: "at the very end circle ...
                #: a big scary worm thing in the circle coming out of the ground (breaking the
                #: ground)". It stands on the spine's r11 plaza at V12/U43, so it goes in AFTER
                #: `Park Ways` has laid that paving - the foot replaces 113 cells of it on purpose.
                "PF Sandworm",
                #
                # RETIRED WITH THEM, and each was measured before it was cut:
                #   PF Frontier Diggings  5,577 - a 30x16 trench with a 25-block spine in a 53x46
                #                                 lot, plus two more timber shops. This IS the dig
                #                                 zone Jack called crappy; the bone bed is 99 x 46.
                #   PF Frontier Claim Row 1,168 } ground dressing written to fill the holes the
                #   PF Frontier Muster Yard 905 } gate and the porch left inside their own lots.
                # Their configs, generators and artifacts all stand as the record.
                #     "PF Frontier Diggings",
                #     "PF Frontier Claim Row", "PF Frontier Muster Yard",
                #
                # ...and the SECOND RIDE, in the emptiest lot in the land. Mining Square
                # measured 1.4 blocks per column with 10% of it standing three courses tall -
                # 39 x 44 of flat paving - and the Frontier had exactly one ride.
                # `PARK_FRONTIER.md` asks for this one by name.
                "PF Mine Cart Escape",
                # THE GROUND THE MODULES NEVER BUILT. Jack, looking down Frontier column A:
                # "basically everything on this row from the orange flag to the tower is
                # useless/waste of usage of space." Measured, V24-146 x U0-39 was 5,840 columns
                # and 54% bare moss - and the two biggest holes were INSIDE the lots: the
                # Trailhead Gate's walled court has an empty middle and no paved route through it
                # at all, and the Prospecting Porch is built as a strip on one flank with twenty
                # columns of unbuilt back. `frontier_scatter` keeps out of module lots (rightly -
                # a material test cannot tell its pine from the Diggings'), so that ground
                # belonged to nobody.
                #     (see the retirement note above - both are out with the two lots they
                #      were written to dress)
                # THE LOST PLATEAU. Jack: "I just think this theme is boring and dull and doesnt
                # represent well - its confusing to the end user ... 'frontier' needs to change."
                # Measured, the Frontier used show material at 1.3% against 21-32% for every other
                # land - the biggest land in the park, the most verbs, and no identity, because a
                # gold-rush mining camp IS timber and stone. This dresses the Mine Ridge as jungle,
                # ADDITIVELY, so the coaster and the mountain are untouched: 72% of the land's mass
                # is those two designs and neither is regenerated.
                "PF Lost Plateau",
                # THE LANDMARK. Jack: "we can put it somewhere on the far left side; against the
                # void where the tower and other frontier objects currently are." Measured, that
                # is the ONLY place it fits: the largest clear rectangle anywhere else in the land
                # is 6 x 49, and this animal is 48 x 11 x 36. The outer rim past the railway rolls
                # two courses in its whole length.
                "PF Sauropod",
                # ...and the other half of the rule the sauropod is built on: the sauropod is
                # COLUMNS and this is the PLANE. It stands on the plateau's own summit at Y257 -
                # the highest ground anywhere in the Frontier - on a crag it brings with it,
                # because a wing is a silhouette and the only thing that reads behind one is sky.
                "PF Pterosaur",
                # THE JUNGLE TAKES THE CAMP BACK, and the rim gets a reason to walk to. Measured
                # after the re-theme: leaves were 7.0% of the plateau and 3.0% of the town, ~35,000
                # exposed building cells carried nothing green, and the rim was 2,249 columns at
                # 3.8 blocks per column carrying one animal and no route to it.
                "PF Frontier Overgrowth", "PF Frontier Rim",
                # THE WYRM'S SKULL, OFF THE CAUSEWAY AND ONTO THE LINE. Jack: "are we able to
                # place the skull so that the mouth 'opens' around the railway, the back of the
                # skeleton is towards the void and the mouth gap is where the railway passes
                # through sideways". `Wyrm's Crossing` keeps the paved crossing and loses the set
                # piece, so the skull is in ONE place: see configs/pf_wyrm_gate.yaml for why his
                # orientation is the only one that fits and why the design takes no cell the
                # railway made.
                "PF Wyrm Gate",
                # THE SEAM, in three places. Jack, looking at the ground round the finished well:
                # "we need to find something to actually place in these areas, they dont fit well
                # especially now with our awesome prism tower." Measured over the shipped park,
                # Prismworks carries 3.0% of its columns in the 3-11 course band against the
                # Frontier's 19.5% and the Prism Reach 3.4% with NOTHING above twelve - so the
                # tower reads as an object dropped on a lawn rather than the thing a place is
                # built around, and the reach's only content is `Wyrm's Crossing`'s bare plate,
                # 2,650 of whose 2,839 blocks are three dark greys of paving.
                #
                # One idea in three sites: the crystal vein the well was cut to reach, breaking
                # the surface. `fracture` crosses the reach and its dead plate; `yard` is the
                # cutting yard behind the Foundry Gate, which is the only thing in the land that
                # accounts for the well being a DIG; `field` is the vein at full size east of the
                # mouth with a raked bank you watch the descent from. See mcbuild/gen/seam.py.
                # ...AND ALL THREE ARE WITHDRAWN FROM PLACEMENT, THE DAY THEY WERE BUILT. Jack,
                # on the placed result: "this looks terrible" and "these random spires and stuff
                # all look terrible ... this is crappy and not good."
                #
                # HE IS RIGHT AND THE FAILURE IS THE PRIMITIVE, NOT THE TUNING. Forty tapering
                # columns on a flat plate read as a picket fence: `base_radius` narrows every one
                # of them to a single cell within a third of its height, they all end in a white
                # cap, and the trace scattered single wool cells across the paving - which is the
                # confetti failure this repo has already recorded on the deck soffit, the lowland
                # thicket and the frontier scatter, re-created a fourth time.
                #
                # AND THE DEEPER ONE: SCATTERED OBJECTS ON A FLAT PLANE ARE CLUTTER, WHATEVER
                # THEIR SHAPE. Every part of this park that reads is TERRAIN or a single mass -
                # the Mine Ridge, the Lost Plateau, the Diggings - and the Frontier's 19.5%
                # mid-band that this design was chasing comes from a MOUNTAIN, not from props. A
                # height histogram can be moved by either and only one of them looks like
                # anything.
                #
                # The configs, `mcbuild/gen/seam.py` and the three artifacts all stand as the
                # record; this table is the one thing that decides whether a module is placed.
                #     "PF Prism Fracture", "PF Prism Cutting Yard", "PF Prism Seam Field"
                #
                # WHAT REPLACES THEM IS GROUND. Jack: "build sophisticated impressive terrain that
                # fits the area appropriately ... it cant be impassable terrain, it should still
                # feel like a park, gradual hills, small areas ... really terrain the entire area,
                # from the building you removed all the way to the railway edge, and all the way
                # to our parkour area so it feels even that more dramatic of a fall."
                #
                # `PF Prism Downs` is the whole land and its reach - 154 x 212 - as downland
                # swelling to a crest against the well's collar, so the shaft is a hole in a HILL.
                # No step anywhere exceeds one course, measured on the shipped artifact rather
                # than on the field, because the world's own floor is not one plane and two
                # neighbours at the same height above it can still be two courses apart.
                "PF Prism Downs",
                # THE MIDWAY'S THIRD RIDE, in the emptiest lot in the park. Jack, standing in it:
                # "theres a strip here before the prism area that has these buildings and this
                # empty plot, i think we can do more with this area thats more impactful to the
                # player, and cooler." Measured before anything was drawn, Midway column C's rear
                # - V100-153 x U345-384, 2,160 columns with streets on all four sides - was
                # **0.09 blocks per column**, 0.9% of it standing three courses tall, 13 lanterns
                # in the whole thing and a top of Y208 against Y223 for the Skill Arcade beside it.
                # Mining Square, the lot he had replaced in the Frontier for being a car park, was
                # 1.4; this was fifteen times emptier, and a hole in the skyline as well.
                #
                # It carries its own origin, so it is placed from here rather than from
                # `PLACEMENT` - see configs/pf_helter_skelter.yaml and mcbuild/gen/helter.py.
                "PF Helter Skelter",
                # **AND THE FOUR MACHINES THAT BELONG TO THE TWO BUILDINGS IN FRONT OF IT.** This
                # is the Frontier's own failure, in the Midway: `out/PF Game Target Wall`,
                # `The Double`, `The Mark` and `Prize Point` were built, circuit-simulated and
                # absent from the shipped park, so the Skill Arcade and the Prize Point stood as
                # empty shells while the whole land carried FOUR buttons across 170 columns. A
                # design that is built and unplaced is indistinguishable from one nobody wrote.
                # THE STREET THAT REPLACED THE SKILL ARCADE AND THE PRIZE POINT. Jack: "i dont
                # like these and they feel out of place/useless unclear." `PF Games Row` is the
                # frontage `PARK_MIDWAY.md` asks for by name - a walk from the east avenue to the
                # helter skelter's forecourt, a continuous awning down each verge, and six
                # self-contained consoles standing on it. There is no building in it.
                #
                # IT GOES IN BEFORE THE CONSOLES, so a bay's own cell can never be won by the
                # street: the row reserves all six boxes and raises on a hit, and the consoles
                # count their own refusals from the other side.
                # **AND THE ROW IS RETIRED IN ITS TURN, WITH ALL SIX CONSOLES.** Jack, on it as
                # built: "the games arent playable as they are facing, theyre ugly, and just not
                # working, these have been a consistent issue, either identify and make them
                # really look good, or trash the idea and lets put something else there."
                #
                # THE FAULT IS IN `park_games`, NOT IN THE SITING, and it is worth stating exactly
                # because four more consoles stand in the Frontier with it. Dumped block for block
                # off `out/PF Game Target Wall.litematic`:
                #
                #     Y206   ############   the lid
                #     Y205   ##B#######T#   the BELL and the TARGET - the game's own INPUT
                #            ###LLLLLL###   the six score lamps
                #     Y204   ############   the plinth
                #            front face U357: solid at Y204, Y205 and Y206
                #
                # A console is a THREE-COURSE SEALED CABINET. Its score lamps - the thing that
                # tells a player what happened - are buried in the lid course in EVERY kind; the
                # `aim` and `striker` targets are entirely enclosed, so they cannot be shot; and
                # `pair`'s two buttons sit on top of a three-course lid, above a standing player's
                # head, with their lamp buried eleven cells away at the far end. Only `counter`'s
                # barrels are on a face a player can touch.
                #
                # **AND EVERY ONE OF THEM SIMULATES CORRECTLY.** The circuits are right. That is
                # this repo's own cardinal sin - a machine that looks like it works - in the one
                # subsystem written to prevent it, and it is why the games have been "a consistent
                # issue" for as long as they have existed. Its own docstring says what it assumes:
                # "a console is furniture ... it needs no ceiling because the building already has
                # one." The Skill Arcade was that building, and it was hiding them.
                #
                # STILL OPEN AND NOT THIS PASS'S: `PF Game Pan Line`, `PF Game Powder Striker`,
                # `PF Game The Riffle` and `PF Game Prize Office` are PLACED in the Frontier with
                # the same fault. Fixing it is a rewrite of `park_games` across six kinds and
                # eleven configs - lamps on the front face, inputs reachable, the counter a course
                # lower - with every simulated contract to re-verify. It is its own job.
                #
                # `PF Midway Garden` takes the lot and keeps the one thing worth keeping: the walk.
                "PF Midway Garden",
                #     "PF Games Row",
                # ...AND THE SIX MACHINES THAT STAND IN IT. Three re-sited out of the retired
                # hall, one out of the retired kiosk, and TWO THE MARQUEE HAD ALREADY PROMISED -
                # the board over the Arcade said "five games" over three. `PARK_MIDWAY.md` names
                # the high striker by name and `park_games` already had the kind.
                #     "PF Game Target Wall", "PF Game The Mark", "PF Game The Striker",
                #     "PF Game The Double", "PF Game The Signal", "PF Game Prize Point",
                }


def extras() -> list:
    """(name, V, U, model, y offset) for every landed design that carries its own origin."""
    out = []
    for f in sorted((ROOT / "out").glob("PF *.litematic")):
        side = f.with_suffix(".scan.json")
        if not side.exists():
            continue
        meta = json.loads(side.read_text(encoding="utf-8"))
        o = meta.get("origin") or {}
        if not o or meta.get("kind") in (None, "park"):
            continue
        # a lot module is placed from PLACEMENT and must not also be placed from here
        if f.stem[3:] in PLACEMENT or f.stem not in EXTRAS_READY:
            continue
        out.append((f.stem, int(o["x"]) - ANCHOR[0], int(o["z"]) - ANCHOR[2],
                    schem.load(str(f)), -(int(o["y"]) - ANCHOR[1] - 1)))
    return out


def lots() -> dict:
    spec = json.loads((ROOT / "park_final.world.json").read_text(encoding="utf-8"))
    return ({m["name"]: m.get("footprint") for m in spec["modules"]},
            {m["name"]: m.get("role", "") for m in spec["modules"]})


def modules(report=False) -> list:
    """(name, V, U, model, plane) for every built module that has a measured lot.

    CROPPED TO ITS LOT, and the crop is REPORTED rather than silent. One cell outside a lot costs
    the neighbour behind it a course - this park has already lost a 111-block ride to a single
    lamp - so the boundary is enforced at placement whatever a generator emitted.
    """
    out = []
    box, roles = lots()
    for name, (v, u) in sorted(PLACEMENT.items()):
        if name not in KEEP and not (ROOT / "out" / f"PF {name}.litematic").exists():
            continue
        # A `PF ` BUILD SUPERSEDES THE RETIRED ARTIFACT OF THE SAME NAME. The three lands were
        # rebuilt from scratch into `out/PF <name>.litematic`; `out/park_final/artifacts` still
        # holds the previous attempt, and only the three rides Jack kept are taken from there.
        pf = ROOT / "out" / f"PF {name}.litematic"
        # THE CAROUSEL IS BUILT FROM `configs/carousel.yaml`, NOT FROM THE ARTIFACT. The artifact is
        # diameter 45 - 52 x 47 - which is why it could only ever live in column B. `out/Carousel`
        # is the same generator at the diameter its lot actually holds, and the lot is column A now.
        own_carousel = ROOT / "out" / "Carousel.litematic"
        if name == "Carousel Court" and own_carousel.exists():
            f = own_carousel
        else:
            f = pf if pf.exists() else ARTIFACTS / f"{name}.litematic"
        if not f.exists():
            continue
        m = schem.load(str(f))
        fp = box.get(name)
        if fp:
            deep, wide = int(fp[0]), int(fp[1])
            _sy, sz, sx = m.ids.shape
            if sx > deep or sz > wide:
                before = int(m.solid().sum())
                m = schem.Model(m.ids[:, :min(sz, wide), :min(sx, deep)].copy(), m.palette)
                if report:
                    print(f"  cropped {name}: {before - int(m.solid().sum())} cells "
                          f"outside its {deep}x{wide} lot")
        out.append((name, int(v), int(u), m, plane_of(m, roles.get(name, ""))))
    out.extend(extras())
    from tools.park_dressing_repairs import apply as repair_dressing
    return repair_dressing(out)


#: A TILE ENTITY BELONGS TO A BLOCK THAT CAN HOLD ONE. Carried on position alone, two of them
#: landed on an `oak_log` and a `stone_bricks` - a source design whose sign block had since moved
#: while its text stayed behind, which a litematic stores perfectly happily and a game reads as a
#: corrupt region. The block at the destination is the authority, not the coordinate.
TEXTED = ("sign", "lectern", "chest", "banner", "barrel", "furnace", "hopper", "dispenser",
          "dropper", "beehive", "bee_nest", "jukebox", "campfire", "skull", "head", "shulker_box")


def _holds_text(name: str) -> bool:
    n = str(name).split(":")[-1]
    return any(k in n for k in TEXTED)


def merge(items) -> schem.Model:
    """One model, module by module, first writer winning a contested cell.

    **A SIGN'S TEXT FOLLOWS ITS BLOCK, AND FOR A YEAR IT DID NOT.** A sign is two things in two
    halves of a litematic - a palette entry and a tile entity - and this merge built a bare
    `Model(ids, pal)`, so every sign in the park came out BLANK in the one artifact anybody
    actually places. Measured before the fix: `PF Front Frontier` 16 tile entities, `PF Claim Lake
    Menagerie` 19, `PF Trailhead Gate` 6 ... and `Park Complete` **0**. Nothing could see it: the
    blocks are all correct, the audit passes, the BOM is right, and `render3d` draws a sign the
    same whether or not it says anything. The only symptom is a guest walking a park where nothing
    is named, which is exactly the complaint that found it.

    `layers.slice_plan` has always carried them and states the rule it is keeping: a tile entity
    whose block was won by another module is a tile entity with no block, which is a corrupt region
    rather than a lost line. So a sign travels only when ITS OWN cell survived the contest.
    """
    import numpy as np
    cells, pal, index = {}, [nbt.block_state("minecraft:air")], {}
    owner, tiles = {}, []
    for name, v, u, m, plane in items:
        names = {i: e.value["Name"].value for i, e in enumerate(m.palette)}
        props = {i: e.value.get("Properties") for i, e in enumerate(m.palette)}
        for y, z, x in zip(*m.solid().nonzero()):
            # the module's own build plane is the ground layer's floor course
            pos = (int(x) + v, int(y) - plane + 1, int(z) + u)
            if pos in cells:
                continue
            key = int(m.ids[y, z, x])
            state = (names[key], str(props[key]))
            slot = index.get(state)
            if slot is None:
                slot = index[state] = len(pal)
                pal.append(m.palette[key])
            cells[pos] = slot
            owner[pos] = name
        for t in (getattr(m, "tile_entities", None) or []):
            try:
                tv = t.value
                pos = (int(tv["x"].value) + v,
                       int(tv["y"].value) - plane + 1,
                       int(tv["z"].value) + u)
            except Exception:                                    # noqa: BLE001
                continue
            # a tile entity whose block lost the contest has no block to belong to
            if owner.get(pos) != name:
                continue
            if not _holds_text(names[int(m.ids[tv["y"].value, tv["z"].value, tv["x"].value])]):
                continue
            tiles.append((pos, t))
    xs = [p[0] for p in cells]; ys = [p[1] for p in cells]; zs = [p[2] for p in cells]
    ox, oy, oz = min(xs), min(ys), min(zs)
    ids = np.zeros((max(ys) - oy + 1, max(zs) - oz + 1, max(xs) - ox + 1), np.int32)
    for (x, y, z), slot in cells.items():
        ids[y - oy, z - oz, x - ox] = slot
    out = schem.Model(ids, pal)
    out.tile_entities = [_shift_tile(t, x - ox, y - oy, z - oz) for (x, y, z), t in tiles]
    return out, (ox, oy, oz)


def _shift_tile(tag, x: int, y: int, z: int):
    """The same tile entity, re-addressed into the merged frame.

    Rewritten rather than mutated: the source model is another design's artifact and may be merged
    again into a second composite in the same run, and a tile entity moved in place would carry the
    first merge's coordinates into the second.
    """
    from mcbuild.nbt import Tag, TAG_COMPOUND, TAG_INT
    v = dict(tag.value)
    v["x"], v["y"], v["z"] = Tag(TAG_INT, int(x)), Tag(TAG_INT, int(y)), Tag(TAG_INT, int(z))
    return Tag(TAG_COMPOUND, v)


def clashes(items) -> list:
    """Which two modules contend for which cells - a work problem, so reported per PAIR."""
    owner, pairs = {}, Counter()
    for name, v, u, m, plane in items:
        for y, z, x in zip(*m.solid().nonzero()):
            pos = (int(x) + v, int(y) - plane + 1, int(z) + u)
            prior = owner.get(pos)
            if prior is None:
                owner[pos] = name
            elif prior != name:
                pairs[tuple(sorted((prior, name)))] += 1
    return [(a, b, n) for (a, b), n in pairs.most_common()]


def against_ground(model, origin) -> int:
    """Cells the buildings and the ground layer both claim. The ground's own floor is y0."""
    ways = ROOT / "out" / "Park Ways.litematic"
    if not ways.exists():
        return -1
    w = schem.load(str(ways)).solid()
    ox, oy, oz = origin
    hit = 0
    for y, z, x in zip(*model.solid().nonzero()):
        gx, gy, gz = int(x) + ox, int(y) + oy, int(z) + oz
        if 0 <= gy < w.shape[0] and 0 <= gz < w.shape[1] and 0 <= gx < w.shape[2] and w[gy, gz, gx]:
            hit += 1
    return hit



def _dig_of(names) -> list:
    """Every dig cell declared by any part, in world coordinates, de-duplicated."""
    seen, out = set(), []
    for name in names:
        side = ROOT / "out" / f"{name}.scan.json"
        if not side.exists():
            continue
        for cell in (json.loads(side.read_text(encoding="utf-8")).get("dig") or []):
            key = tuple(cell)
            if key not in seen:
                seen.add(key); out.append(list(cell))
    return out


def complete(items):
    """GROUND + RAILWAY + BUILDINGS AS ONE DESIGN, because three placements hide each other.

    Jack: "the land disappears when i try to place the buildings, i need to be able to see all."
    Three schematics whose bounding boxes overlap are three placements Litematica draws on top of
    one another, and the one you are looking at is whichever won - which is the same complaint the
    casino produced ("stop with the defer crap so i can actually see everything in totality") and
    the same answer: ship the whole thing as one artifact and keep the pieces for building in
    stages.

    PRECEDENCE IS BUILDINGS > RAILWAY > GROUND, and it is REPORTED rather than applied quietly.
    The ground is laid under a building on purpose - a floor that stops at the wall leaves a hole
    the moment anything moves - so the building has to win the cells they share or the picture
    shows paving drawn through a wall.

    AND A CELL YOU ARE TOLD TO BREAK IS NOT A CELL YOU ARE TOLD TO PLACE. The Prism Well is a
    hundred-wide mouth cut through the deck, so it declares 8,233 dig cells - and 8,037 of them
    are cells `Park Ways` lays moss in. Shipped without this the composite instructs you to place
    eight thousand blocks and then break them, and anyone printing it fills in the hole the
    design exists to open. The dig list wins over the GROUND and the RAILWAY; it is not applied
    to buildings, because a design that digs its own footing and rebuilds it is doing exactly
    what a dig is for.
    """
    import numpy as np
    from collections import Counter
    ways = schem.load(str(ROOT / "out" / "Park Ways.litematic"))
    rail = schem.load(str(ROOT / "out" / "Park Rail.litematic"))
    model, origin = merge(items)
    # world -> plan, the same frame `merge` places into: plan + ANCHOR == world
    dug = {(c[0] - ANCHOR[0], c[1] - ANCHOR[1], c[2] - ANCHOR[2])
           for c in _dig_of(["Park Rail"] + [i[0] for i in items])}

    height = 220
    sz, sx = ways.ids.shape[1], ways.ids.shape[2]
    ids = np.zeros((height, sz, sx), np.int32)
    pal, index = [nbt.block_state("minecraft:air")], {}
    contested = Counter()

    tiles = []

    def lay(m, ov, oy, ou, tag, honour_dig=False):
        names = {i: e.value["Name"].value for i, e in enumerate(m.palette)}
        props = {i: e.value.get("Properties") for i, e in enumerate(m.palette)}
        won = set()
        for y, z, x in zip(*m.solid().nonzero()):
            Y, Z, X = int(y) + oy, int(z) + ou, int(x) + ov
            if not (0 <= Y < height and 0 <= Z < sz and 0 <= X < sx):
                continue
            if honour_dig and (X, Y + min(0, origin[1]), Z) in dug:
                contested[tag + " (dug)"] += 1
                continue
            if ids[Y, Z, X]:
                contested[tag] += 1
                continue
            key = int(m.ids[y, z, x])
            state = (names[key], str(props[key]))
            slot = index.get(state)
            if slot is None:
                slot = index[state] = len(pal); pal.append(m.palette[key])
            ids[Y, Z, X] = slot
            won.add((int(x), int(y), int(z)))
        # ...and its signs with it. This composite is the one Jack places, so a sign whose text
        # is dropped here is a blank sign in the world however correct the module was.
        for t in (getattr(m, "tile_entities", None) or []):
            try:
                tv = t.value
                lx, ly, lz = int(tv["x"].value), int(tv["y"].value), int(tv["z"].value)
            except Exception:                                    # noqa: BLE001
                continue
            if (lx, ly, lz) not in won:          # its block lost the cell, or was never laid
                continue
            if not _holds_text(names[int(m.ids[ly, lz, lx])]):
                continue
            tiles.append(_shift_tile(t, lx + ov, ly + oy, lz + ou))

    lay(model, origin[0], origin[1] - min(0, origin[1]), origin[2], "buildings")
    # THE RAIL'S OWN CORRIDOR START, read from its config rather than typed - it moved from
    # V172-179 to V172-186 the day the line went to two tracks, and a hard-coded offset here
    # would have laid the whole railway seven columns out with nothing to say so.
    import yaml as _yaml
    _rv = _yaml.safe_load((ROOT / "configs" / "park_rail.yaml").read_text(encoding="utf-8"))
    lay(rail, int(_rv["params"]["bounds"][0]), 0 - min(0, origin[1]), 0, "railway", True)
    lay(ways, 0, 0 - min(0, origin[1]), 0, "ground", True)
    out = schem.Model(ids, pal)
    out.tile_entities = tiles
    return out, (0, min(0, origin[1]), 0), contested



#: Keys that record a HUMAN's decision about this design rather than anything the merge computed.
#: They are read back off the shipped sidecar and re-stated, because a rebuild of the blocks is not
#: a withdrawal of approval - and because no other code in this repo can put them back.
APPROVAL_KEYS = ("anchor_status", "automation_approved")


#: THE LANDSCAPE, AND NOTHING ELSE. Jack, after the first run went wide: *"nope you screwed up, you
#: hollowed things like the train station etc, i said landscape terraforming etc only"*. He is
#: right, and "etc" was mine to read narrowly. These are the five modules that ARE ground - a
#: mountain, two stretches of downland, an excavation and the canopy over the ridge. A ride, a
#: station, a building, a sculpture and the railway are all somebody's structure and are context:
#: they still decide what is hidden, they are never themselves touched.
TERRAIN_MODULES = frozenset({
    "PF Mine Ridge",            # the mountain the coaster is cut into
    "PF Prism Downs",           # the Prismworks terrain
    "PF Broken Plateau",        # the mesa, the gorge and its spoil
    "PF Plateau Bone Bed",      # the excavation and its spoil
    "PF Lost Plateau",          # the moss cap and canopy over the ridge

})

#: ...and inside those, only what a terraforming pass actually lays. A module's footprint holds
#: lanterns, signs, timber sets and rails as well as rock, and a mask drawn round the module alone
#: would offer all of it. Natural rock and ground only - no brick, no plank, no wool, no
#: `smooth_stone`, which is masonry however grey it looks.
TERRAIN_BLOCKS = frozenset({
    "stone", "cobblestone", "mossy_cobblestone", "cobbled_deepslate", "deepslate",
    "smooth_basalt", "basalt", "blackstone", "granite", "diorite", "andesite", "calcite",
    "dripstone_block", "moss_block", "gravel", "tuff", "clay", "obsidian",
    "coal_ore", "gold_ore", "iron_ore", "copper_ore", "redstone_ore", "lapis_ore",
    "sand", "red_sand", "sandstone", "red_sandstone", "soul_sand", "soul_soil",
})


def terrain_mask(items, whole, worigin):
    """Cells the hollow pass may touch: laid by a landscape module AND made of ground.

    Both halves are needed. The module list alone would offer a terrain pass's own lanterns and
    timber; the material list alone would offer a building's cobblestone core, and a station is
    exactly what this is not allowed to touch.
    """
    import numpy as np
    h, sz, sx = whole.ids.shape
    mask = np.zeros((h, sz, sx), bool)
    oy = worigin[1]
    for name, v, u, m, plane in items:
        if name not in TERRAIN_MODULES:
            continue
        ys, zs, xs = m.solid().nonzero()
        Y, Z, X = ys - plane + 1 - oy, zs + u, xs + v
        ok = (Y >= 0) & (Y < h) & (Z >= 0) & (Z < sz) & (X >= 0) & (X < sx)
        mask[Y[ok], Z[ok], X[ok]] = True
    ground = np.array([n.split(":")[-1] in TERRAIN_BLOCKS for n in whole.names])[whole.ids]
    return mask & ground


def _carry_approval(out_path) -> dict:
    """The approval keys already on disk, or the cautious default for a design nobody has approved."""
    side = str(out_path)[: -len(".litematic")] + ".scan.json"
    keep = {"anchor_status": "PREVIEW placement; rebase before building"}
    try:
        with open(side, encoding="utf-8") as f:
            prev = json.load(f)
    except (OSError, ValueError):
        return keep
    for k in APPROVAL_KEYS:
        if k in prev:
            keep[k] = prev[k]
    return keep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ship", action="store_true")
    args = ap.parse_args()

    items = modules(report=True)
    print(f"{len(items)} built modules with a measured lot\n")
    for name, v, u, m, plane in items:
        sy, sz, sx = m.ids.shape
        print(f"  {name:<24}{int(m.solid().sum()):>7} at V{v:<4}U{u:<4} {sx:>3}x{sy:>3}x{sz:<3}"
              f"  plane {plane}")
    found = clashes(items)
    print("\nmodule clashes:", "none" if not found else "")
    for a, b, n in found:
        print(f"  {a} x {b}: {n} cells")

    model, origin = merge(items)
    sy, sz, sx = model.ids.shape
    print(f"\nPark Buildings  {sx}x{sy}x{sz}  {int(model.solid().sum()):,} blocks"
          f"  origin V{origin[0]} y{origin[1]} U{origin[2]}")
    print(f"cells also claimed by the ground layer: {against_ground(model, origin)}")

    if args.ship:
        # The buildings-only composite is SHIPPED too, so it gets the same clutter pass as the
        # whole park - a design that lands in the schematics folder must not behave differently
        # from the one beside it. The full report is printed once, under Park Complete.
        b_removed, b_swapped = declutter_op(model)
        # NO HOLLOW PASS HERE. This composite is the BUILDINGS, and the pass is scoped to
        # the landscape - there is nothing in it the pass is allowed to touch.
        print("")
        print(f"Park Buildings: {sum(b_removed.values()):,} clutter cells hidden, "
              f"{sum(b_swapped.values()):,} swapped")
        out = ROOT / "out" / "Park Buildings.litematic"
        meta = {"origin": {"x": ANCHOR[0] + origin[0], "y": ANCHOR[1] + origin[1],
                           "z": ANCHOR[2] + origin[2]},
                "kind": "park", "name": "Park Buildings",
                "generated_by": "tools/park_place.py",
                "anchor_status": "PREVIEW placement; rebase before building",
                "contains": [i[0] for i in items]}
        scan.save_pair(str(out), model, meta, name="Park Buildings")
        dest = Path(mcprofile.load()["schem_dir"])
        shutil.copy2(out, dest / out.name)
        (dest / "Park Buildings.scan.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"\nshipped -> {dest / out.name}")

        whole, worigin, contested = complete(items)
        # GROUND CLUTTER IS HIDDEN AT THE COMPOSITE, not turned off a config at a time. A dozen
        # passes plant it (`parkgreen`, `frontier_scatter`, `thicket`, `plateau`, every `_Ground`
        # helper), so switching it off upstream is one decision taken twelve times and remembered
        # twelve - and the module artifacts stay as they were designed, which is what makes this
        # reversible. A litematic cannot express removal, so a fern already standing in the world
        # is untouched: it is simply no longer the printer's to place, or `/cscan check`'s to
        # report. Moss BLOCK stays - it is the ground - and so do the leaves, the vines and every
        # plant that emits light; see `mcbuild/ops/declutter.py` for why each.
        removed, swapped = declutter_op(whole)
        print("")
        print(declutter_report(removed, swapped))
        # AND THEN THE INSIDE OF THE LANDSCAPE. The Mine Ridge, the Downs, the Vale, the Bone
        # Bed and the Plateau's cap are solid masses, and a solid mass costs the same to print as
        # a hollow one and looks the same from every angle a guest has. `unseen` removes a block
        # only when all six of its neighbours are opaque full cubes, so anything with a face onto
        # air - INCLUDING air the outside cannot reach, which is what a station room and a tunnel
        # bore are - stays. `terrain_mask` is the scope: the five modules that ARE ground, and
        # inside them only the rock and soil a terraforming pass lays. Everything else in the park
        # is context, deciding what is hidden and never touched.
        #
        # It runs BEFORE the stitch below on purpose: hollowing is what turns a sloped skin into a
        # staircase of edge diagonals, `_connect` closes those with the design's OWN blocks, and
        # the stitch is the backstop for what is left rather than the thing doing the work.
        unseen = hollow_unseen(whole, carve_only=terrain_mask(items, whole, worigin))
        print("")
        print(unseen.report())
        # A DIAGONAL JOIN IS NOT A JOIN. A printer clicks a FACE, so two cells that meet only at a
        # corner leave everything behind them unreachable - and a break BETWEEN two modules belongs
        # to neither of them, so nothing upstream of this merge can see it. Measured before this
        # ran: 18,721 cells of the shipped composite could never have been printed, 16,062 of them
        # orphaned by a corner. Closed here, where the composite exists.
        stitch, stitched = printable.stitch_model(
            whole, (ANCHOR[0] + worigin[0], ANCHOR[1] + worigin[1], ANCHOR[2] + worigin[2]),
            name="Park Complete")
        wout = ROOT / "out" / "Park Complete.litematic"
        wmeta = {"origin": {"x": ANCHOR[0] + worigin[0], "y": ANCHOR[1] + worigin[1],
                            "z": ANCHOR[2] + worigin[2]},
                 "kind": "park", "name": "Park Complete",
                 "generated_by": "tools/park_place.py",
                 # ---- APPROVAL SURVIVES A RE-SHIP. `Designs.requireAutonomousApproval` refuses
                 # any design whose `anchor_status` says "preview"/"provisional"/"rebase", and
                 # demands `automation_approved: true`. NOTHING IN PYTHON EVER WROTE EITHER - they
                 # were set by hand - and `save_pair` replaces the sidecar rather than merging, so
                 # every `--ship` silently reverted them and the mod then refused to build the park
                 # with a message about a status string nobody had set. Carried forward from the
                 # sidecar on disk: a ship re-states the geometry, it does not withdraw consent.
                 **_carry_approval(wout),
                 "contains": ["Park Ways", "Park Rail"] + [i[0] for i in items],
                 # A LITEMATIC CANNOT EXPRESS REMOVAL, so every "break this first" cell lives in
                 # a sidecar - and this file writes a FRESH sidecar on every ship, which silently
                 # dropped the lake's 2,963 buried lawn cells and the viaduct's 52 the first time
                 # I re-placed after adding them by hand. Gathered from the parts, so it cannot
                 # be forgotten again: leave them and the lake is a lawn with water drawn on it.
                 "dig": _dig_of(["Park Rail"] + [i[0] for i in items]),
                 "dig_note": "cells to BREAK before printing - see `contains` for their designs"}
        # Furnishings are checked against the finished surface, after clutter and hollowing.
        from tools.park_refinement import apply as apply_refinement
        whole = apply_refinement(whole, tuple(wmeta["origin"][k] for k in ("x", "y", "z")))
        wmeta["contains"].append("PF Premium Refinement")
        scan.save_pair(str(wout), whole, wmeta, name="Park Complete")
        shutil.copy2(wout, dest / wout.name)
        (dest / "Park Complete.scan.json").write_text(json.dumps(wmeta, indent=2), encoding="utf-8")
        wy, wz, wx = whole.ids.shape
        print("")
        print(f"Park Complete   {wx}x{wy}x{wz}  {int(whole.solid().sum()):,} blocks")
        print(f"   printable: {stitched} corner fills close diagonal joins and return "
              f"{stitch.returned} cells the printer could not have reached; "
              f"{sum(c.n for c in stitch.unfixable)} left in {len(stitch.unfixable)} clumps "
              f"(see `python -m mcbuild printable \"Park Complete\"`)")
        print(f"   contested cells yielded to the winner: {dict(contested)}")
        print(f"shipped -> {dest / wout.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
