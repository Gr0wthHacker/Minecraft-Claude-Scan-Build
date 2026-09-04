"""THE PRISM WELL - a hole cut through the park deck, and the rim you watch it from.

Jack, 2026-09-03: *"prism in its current state is not a theme park, its a collection of
buildings; this is a failure of design."* He was right, and it measured worse than it looked:
56,030 blocks over 36,000 columns, 100% of the plot paved, 13.0% carrying anything three
courses tall and 4.6% carrying an actual building. Half the land was lawn with a path grid
drawn on it, and the land's headline ride was a decorated tower - which its own config said
outright: *"THE PARKOUR COURSE IS NOT IN HERE... This design is the SPIRE the course will be
hung on."*

THE UNUSED DIMENSION IS DOWN. v1 used Y198-286: eighty-eight courses up, four hundred and
forty-eight cells below the build plane, and 261 courses of void underneath it never touched.
Down is the only dimension in this park nobody has spent, no other land competes for it, and a
lit helix falling into darkness is exactly what this medium renders natively. So the land stops
being six boxes on a lawn and becomes ONE HOLE with a rim around it, which is the opposite of a
collection of buildings by construction.

THE DECK IS ONE COURSE OF MOSS AT Y202, measured, and that decided the whole design. A hole cut
in a one-block sheet has a one-block edge, which reads as damage rather than as architecture -
this repo's own rule, learned on the void tower and again on the ruined gateways: *what makes
voxels read as ARCHITECTURE is regularity and openings, not damage.* So the cut is LINED. The
collar hangs fifteen courses below the deck and carries a corbel at its foot, so from underneath
the park has a lit ring in its belly rather than a torn edge, and from the rim you are standing
behind a proper well head.

THE EIGHT BALCONIES ARE THE SPECTATOR STAND, AND THEY ARE GEOMETRY RATHER THAN A RULE. The old
brief asked that observers watch runners without being able to collide with them; a gallery
round the top of a shaft satisfies that by being somewhere else entirely. Each balcony oversails
the void by three cells on its own corbel, so you stand OUT over the hole rather than behind a
fence looking at one.

WHAT THIS DESIGN IS NOT. It is not the course - that is `gen/parkour.py`, hung in the middle of
this void at r30 tapering to r16, which the START PIER is what makes possible: you walk out to
r33 before the first jump, so the run lives twenty blocks clear of the collar on every side
instead of hugging it. It is not the gantry over the course, and it is not the floor. And the lift is built as geometry and NOT claimed as working: a bubble column
is one of the three things the plan lists as uncertifiable offline, and this repo cut two
finished casino games rather than ship a machine it could not judge.

THE CUT IS A DIG, BECAUSE A LITEMATIC CANNOT EXPRESS REMOVAL. Every cell inside the mouth goes
to the sidecar's `dig` list, which `/cscan dig` and `/cscan autodig` read. The hole takes the
park's own dressing - moss, carpet, path tile, the lamp masts standing in it - because that is
what a hole does, and a MACHINE stops the build rather than being worked around: see _NEVER_CUT.
"""
from __future__ import annotations

import math

from . import protect
from .canvas import Canvas, hash01
from .vertical import Ctx, World

WELL = {
    "under": None,
    "centre": [97590, 80815],       # measured: the largest legal mouth clear of rail and line
    "deck_y": 202,                  # the course the park's floor blocks OCCUPY, not the plane
    "r_mouth": 50,                  # the void's radius; the course hangs at 18-24 inside it
    "collar": 3,                    # collar thickness, radially
    "collar_depth": 15,             # how far the lining hangs under the deck
    "gallery": 9,                   # rim terrace, outside the collar
    "bays": 8,                      # viewing balconies, evenly spaced
    "bay_half": 3,                  # balcony half-width, in cells along the rim
    "bay_reach": 3,                 # how far it oversails the void
    "entry_deg": 180,               # the course's start: west, facing the park spine
    "pier_to": 33,                  # the start pier reaches this far in; the run begins here
    # THE CROWN, and it is the answer to a shame Jack named: "its probably a shame that side of
    # the landscape just falls down, should we be building this straight up as well so its a
    # really complete big circuit". The well only ever went DOWN, and 117 courses of clear
    # headroom stood over the mouth doing nothing.
    #
    # NOT A TOWER BESIDE A HOLE - THE SAME COLUMN, CARRIED UP. A spire next to a well is two
    # objects, and two objects is exactly what this land was rebuilt to stop being. The lift is
    # already the spine the helix winds around; run it on to Y300 and the deck stops being the
    # start of the ride and becomes its MIDDLE, with the gallery standing between a course that
    # comes out of the sky and one that disappears into the ground.
    #
    # AND THE CROWN PIER IS WHAT KEEPS EVERY FALL SAFE. The upper course must hang INSIDE the
    # mouth's own cylinder, because a miss outside r50 lands on the lawn at Y203 from ninety-odd
    # courses up. Inside it, a miss at any height on either half falls straight down the well
    # into the pool that is already there - one failure mode for two hundred courses of run, and
    # it is the dramatic one. The pier is how you reach r30 from a platform at r7.
    # AND ABOVE THE DECK IT IS A TOWER, NOT A MAST. Jack, on the first crown: "i think we need
    # to improve the above ground stuff more, i think visually it feels a bit chaotic, not as
    # amazing as when looking down on it, lets upscale this". He is right and it measures: the
    # column was nine wide over ninety-eight courses - ELEVEN TO ONE, which is a stick - and the
    # helix orbited it as loose wire eight blocks out. At distance the whole thing read as thin
    # bits at incompatible scales, with the Wyrm's pale arch out-massing the lot.
    #
    # CHAOS HERE IS AN ABSENCE OF HIERARCHY, not an excess of detail. The plan view works because
    # it flattens everything into concentric rings; the elevation had no mass to organise around.
    # So the shaft becomes a tapering drum with real setbacks and real openings - the void tower's
    # own rule, that what makes voxels read as architecture is regularity and openings rather than
    # damage - and the ring of masts is scaled until it is a colonnade at the base rather than
    # noise. Three scales that belong to each other: tower, pylon, rail.
    #
    # A DRUM ABOVE, A LATTICE BELOW, and the split is deliberate. Above the deck this is the
    # skyline and wants mass. Below it you are looking DOWN the well past it, and a drum there
    # would block the one view the whole land is composed around - so under the deck it stays
    # four lit posts you can see between.
    "tower": True,
    "ribs": 8,                      # the verticals that run the WHOLE shaft, floor to crown
    "base_h": 14,                   # the wider base drum at the deck, before the taper starts
    "tower_r": 12,                  # base radius above the deck
    "tower_top": 6,                 # ...and at the crown
    "tower_wall": 2,
    "tower_stages": 4,              # setbacks: a stepped shaft has a silhouette, a cone does not
    "tower_open": 4,                # openings per stage, on the cardinals
    "y_crown": None,                # None keeps the well exactly as it was: rim to floor only
    "crown_r": 7,
    "crown_pier_to": 33,
    "y_floor": 95,                  # the well's floor - Signal Zero's course
    "lift_post_r": 4,               # the lit corner posts of the return column
    "cut_from": 198, "cut_to": 214,  # the Y band the mouth is cleared through

    # THE LADDER IS MEASURED ACROSS FAMILIES, which is the only place contrast exists on this
    # economy. v1 was six greys between L38 and L73 - a ladder inside ONE family, which this
    # repo has now concluded four separate times cannot draw a line at all.
    "pave": "smooth_stone",                     # L159, pale, so the mouth reads as a hole
    "pave_alt": "stone",                        # L126
    "kerb": "deepslate_bricks",                 # L71
    "collar_hi": "cobbled_deepslate",           # L77, the collar's top band
    "collar_lo": "polished_blackstone_bricks",  # L45, and it gets darker as it falls
    "collar_deep": "black_wool",                # L21, the last band before open void
    "trim": "waxed_copper_block",               # L129, Prismworks' plant metal - the one hue
    "trim_slab": "waxed_cut_copper_slab",
    "rail": "deepslate_brick_wall",
    "cap": "deepslate_brick_slab",
    "light": "ochre_froglight",                 # L230, warm at the mouth; the run cools going down
    "lift_case": "deepslate_bricks",
    "lift_cage": "iron_bars",                   # plain `glass` is EXPENSIVE here; bars are `ok`
    "tie_every": 8,                             # the gantry rings that make the column one piece
    "masts": 8,                                 # the rim signal ring - see section 9
    "practice": 8,                              # free hops on the gallery - see section 10
    "practice_from": 28,                        # degrees off the entry axis
    "mast_h": 18,
    "walk": 3,                                  # the catwalk's half-width, on the entry axis
    "weather": 0.26,
    "seed": 7,

}

AIRY = ("air", "cave_air", "void_air")

# WHAT THE CUT MUST NEVER TAKE - a blacklist, and the first version was a whitelist that shipped
# sixty-one cells hanging over the hole.
#
# The whitelist was the cautious-looking choice and it was wrong for a reason worth keeping. A
# cut has to enumerate every block the park might have placed inside a hundred-wide circle, and
# it cannot: `Park Ways` puts a lamp mast on the verge every twenty-two cells, and the four
# materials those masts are made of were simply not on the list. So the moss under them was dug
# and the masts were left standing on air - a soul lantern, nineteen wall cells and twenty-four
# copper stairs hanging over a void, which is not a cosmetic problem but a trap.
#
# `protect.is_protected` is not the right gate either, and this repo has now written that rule
# down twice: it is the never-OVERWRITE set, not a keep-clear radius, and it holds `wool`,
# `carpet`, `lantern` and `end_rod` because a wool block on the MAIN island may be a sculk
# sensor's silencer. `Island Night` used it as a radius and left 523 cells dark; here it would
# preserve a lamp post in the middle of the hole that replaces it.
#
# MEASURED, NOT ASSUMED: inside this mouth stand 6,972 moss, 455 deepslate tiles, 157 carpet,
# 258 signal-band wool, 73 wall, 60 bars and the copper of the masts - and ZERO machines. So the
# rule is that the hole takes the park's own dressing, which is what a hole does, and a MACHINE
# stops the build rather than being quietly worked around: one inside the mouth means the site
# is wrong, and a site that is wrong should not generate.
_NEVER_CUT = (
    "redstone", "repeater", "comparator", "observer", "piston", "lever", "button",
    "pressure_plate", "tripwire", "target", "note_block", "daylight_detector", "sculk_sensor",
    "dispenser", "dropper", "hopper", "chest", "barrel", "shulker_box", "furnace", "smoker",
    "brewing_stand", "enchanting_table", "anvil", "grindstone", "smithing_table", "stonecutter",
    "loom", "cartography_table", "fletching_table", "composter", "cauldron", "beacon",
    "crafting_table", "jukebox", "bell", "beehive", "bee_nest", "spawner", "lectern",
    "rail", "minecart", "_door", "sign", "banner",
    "lava", "farmland", "sugar_cane", "wheat", "carrots", "potatoes", "beetroots",
    "nether_wart", "cocoa", "sweet_berry_bush", "kelp",
)


def _ring_band(p, y):
    """The collar darkens as it falls: three bands over `collar_depth`, top to bottom."""
    deep = p["deck_y"] - p["collar_depth"]
    t = (y - deep) / max(p["collar_depth"], 1)
    if t > 0.66:
        return p["collar_hi"]
    if t > 0.28:
        return p["collar_lo"]
    return p["collar_deep"]


def build_well(cfg: dict, donors=None) -> Canvas:
    p = {**WELL, **cfg}
    if not p.get("under"):
        raise ValueError("well needs params.under")
    ctx = Ctx(p["under"])
    w = World()
    cx, cz = int(p["centre"][0]), int(p["centre"][1])
    dy = int(p["deck_y"])
    rm, col, gal = int(p["r_mouth"]), int(p["collar"]), int(p["gallery"])
    dig: list[tuple[int, int, int]] = []
    feats = {k: 0 for k in ("cut", "collar", "corbel", "pave", "rail", "balcony",
                            "light", "lift", "post", "steps")}

    def r_of(x, z):
        return math.hypot(x - cx, z - cz)

    def cut(x, y, z):
        """Record a removal. Everything the park dressed this circle with comes out; a MACHINE
        stops the build, because one inside the mouth means the site is wrong."""
        n = ctx.name_at(x, y, z).split("[")[0].split(":")[-1]
        if n in AIRY:
            return False
        if any(k in n for k in _NEVER_CUT):
            raise ValueError(
                f"the cut at {(x, y, z)} would take {n}, which is a machine or somebody's "
                f"storage - move the mouth, do not widen the rule")
        dig.append((x, y, z))
        return True

    # ------------------------------------------------------------------ 1. THE CUT
    # Everything inside the mouth comes out. The collar is built at the edge afterwards, so the
    # band r >= rm is never dug: the lining stands where the deck used to.
    for x in range(cx - rm, cx + rm + 1):
        for z in range(cz - rm, cz + rm + 1):
            if r_of(x, z) >= rm - 0.5:
                continue
            for y in range(int(p["cut_from"]), int(p["cut_to"]) + 1):
                if cut(x, y, z):
                    feats["cut"] += 1

    # ------------------------------------------------------------------ 2. THE COLLAR
    # A hole in a one-course sheet has a one-course edge, which reads as damage. This is the
    # well head: three cells thick, fifteen courses deep, darkening as it falls, with a corbel
    # at its foot so the park's belly gets a cornice rather than a torn edge.
    lo = dy - int(p["collar_depth"])
    for x in range(cx - rm - col - 1, cx + rm + col + 2):
        for z in range(cz - rm - col - 1, cz + rm + col + 2):
            r = r_of(x, z)
            if not (rm - 0.5 <= r < rm + col - 0.5):
                continue
            for y in range(lo, dy + 1):
                mat = _ring_band(p, y)
                if hash01(x, y, z, p["seed"]) < p["weather"]:
                    mat = p["kerb"] if mat == p["collar_hi"] else mat
                w.put(x, y, z, mat)
                feats["collar"] += 1
            # THE STRING COURSE. One band of the plant metal four under the lip, which is what
            # ties this to the rest of Prismworks - v1's one right decision was that
            # `waxed_copper_block` is the only real hue this land can buy at cheap tier.
            w.put(x, dy - 4, z, p["trim"])
            # the corbel: one cell PROUD at the collar's foot, so it reads from below
            if r < rm + 0.6:
                w.put(x, lo - 1, z, p["trim"])
                w.put(x, lo - 2, z, p["collar_deep"])
                feats["corbel"] += 2

    # ------------------------------------------------------------------ 3. THE GALLERY
    # The land's whole public surface. It replaces the lawn locally rather than being drawn on
    # top of it: paving at the deck course, a rail on the collar, lamps on a measured rhythm.
    g0, g1 = rm + col, rm + col + gal
    for x in range(cx - g1 - 1, cx + g1 + 2):
        for z in range(cz - g1 - 1, cz + g1 + 2):
            r = r_of(x, z)
            if not (g0 - 0.5 <= r < g1 + 0.5):
                continue
            band = int(r) - g0
            mat = p["pave"]
            if band in (0, gal - 1):
                mat = p["kerb"]                       # a kerb at both edges: the terrace reads as one ring
            elif hash01(x, dy, z, p["seed"], 3) < p["weather"]:
                mat = p["pave_alt"]
            w.put(x, dy, z, mat)
            feats["pave"] += 1

    # ------------------------------------------------------------------ 4. RAIL AND BALCONIES
    bay_angles = [i * 360.0 / max(int(p["bays"]), 1) for i in range(int(p["bays"]))]
    entry = float(p["entry_deg"])

    def near_bay(x, z):
        """Is this rim cell inside a balcony's opening? Measured by ARC LENGTH, not by angle -
        a fixed angular half-width is a different number of cells at every radius, so the bays
        would be a different size on the collar than on the balcony deck."""
        a = math.degrees(math.atan2(z - cz, x - cx)) % 360.0
        for b in bay_angles:
            d = abs((a - b + 180) % 360 - 180)
            if math.radians(d) * rm <= p["bay_half"] + 0.5:
                return True
        return False

    def near_entry(x, z):
        a = math.degrees(math.atan2(z - cz, x - cx)) % 360.0
        d = abs((a - entry + 180) % 360 - 180)
        return math.radians(d) * rm <= 4.5

    def near_walk(x, z):
        """The catwalk's own gap in the rail, on the axis opposite the start."""
        a = math.degrees(math.atan2(z - cz, x - cx)) % 360.0
        d = abs((a - (entry + 180.0) + 180) % 360 - 180)
        return math.radians(d) * rm <= int(p["walk"]) // 2 + 1.5

    # the rail sits on the collar's middle cell, so you can walk right up to the lip and lean
    rr = rm + col - 2
    for x in range(cx - rm - col, cx + rm + col + 1):
        for z in range(cz - rm - col, cz + rm + col + 1):
            if not (rr - 0.5 <= r_of(x, z) < rr + 0.5):
                continue
            if near_entry(x, z) or near_walk(x, z):
                continue                  # the start and the catwalk: no rail across either
            w.put(x, dy + 1, z, p["rail"])
            feats["rail"] += 1

    # THE BALCONIES OVERSAIL THE VOID. Standing behind a fence looking at a hole is not the same
    # experience as standing out over one, and the difference is three cells.
    reach, half = int(p["bay_reach"]), int(p["bay_half"])
    for b in bay_angles:
        a = math.radians(b)
        ux, uz = math.cos(a), math.sin(a)             # outward
        tx, tz = -uz, ux                              # along the rim
        for s in range(-half, half + 1):
            for q in range(1, reach + 1):
                x = int(round(cx + ux * (rm - q) + tx * s))
                z = int(round(cz + uz * (rm - q) + tz * s))
                w.put(x, dy, z, p["pave"])
                feats["balcony"] += 1
                # THE BRACKET RUNS THE WHOLE REACH, not the first two cells. A balcony carried
                # for two of its three cells is a balcony with a floating lip, and the audit
                # counts the lip. It steps down as it reaches, which is what a corbel does.
                w.put(x, dy - 1, z, p["trim"])
                feats["corbel"] += 1
                if q >= 2:
                    w.put(x, dy - 2, z, p["collar_lo"])
                    feats["corbel"] += 1
            # the rail round the balcony's own lip
            x = int(round(cx + ux * (rm - reach - 1) + tx * s))
            z = int(round(cz + uz * (rm - reach - 1) + tz * s))
            w.put(x, dy, z, p["pave"])
            w.put(x, dy + 1, z, p["rail"])
            feats["rail"] += 1
        # and its two lamps, one each side, on the rim line where they light the lean-over
        for s in (-half - 1, half + 1):
            x = int(round(cx + ux * (rm - 1) + tx * s))
            z = int(round(cz + uz * (rm - 1) + tz * s))
            w.put(x, dy, z, p["light"])
            w.put(x, dy + 1, z, p["rail"])
            feats["light"] += 1

    # ------------------------------------------------------------------ 5. GALLERY LAMPS
    # A LAMP IS A FLUSH FROGLIGHT, WHICH IS THIS ISLAND'S OWN IDIOM AND NEEDS NO SIDE ROOM. Jack
    # scattered thirty-nine of them across the lowland by hand before any tool did it, and a
    # flush light cannot be knocked off a walkway or stand in a cell somebody has to walk through.
    ring_r = g0 + gal // 2
    n_lamp = max(8, int(2 * math.pi * ring_r / 11))
    for i in range(n_lamp):
        a = math.radians(i * 360.0 / n_lamp + 180.0 / n_lamp)
        x = int(round(cx + ring_r * math.cos(a)))
        z = int(round(cz + ring_r * math.sin(a)))
        w.put(x, dy, z, p["light"])
        feats["light"] += 1

    # ------------------------------------------------------------------ 6. THE START PIER
    # THE PIER IS WHAT LETS THE COURSE BE SMALL, and that is a bigger decision than it looks.
    #
    # With the run starting off the rim it had to begin at r45, one jump inside the collar - so
    # its fall zone was the whole hundred-wide disc and the catch at the floor had to be seven
    # thousand cells to cover it. Walking out on a pier to r33 first lets the whole course live
    # inside r30, which cuts the catch to a third, and buys two things it did not pay for:
    # nearly three turns instead of 1.84 at the same move count, because the same jump is a
    # bigger angle at a smaller radius; and a wide band of EMPTY void between the run and the
    # collar, so from the gallery the helix hangs clear in the middle of the mouth instead of
    # hugging the wall.
    #
    # It is also the diving board. You walk out over a hundred courses of nothing, and the first
    # jump is off the end of it.
    a = math.radians(entry)
    ux, uz = math.cos(a), math.sin(a)
    tx, tz = -uz, ux
    for s in range(-4, 5):                        # the apron, on the gallery
        for q in range(0, 6):
            x = int(round(cx + ux * (rm + col - 1 + q) + tx * s))
            z = int(round(cz + uz * (rm + col - 1 + q) + tz * s))
            w.put(x, dy, z, p["trim"] if abs(s) == 4 else p["pave"])
            feats["steps"] += 1
    pier_r = int(p["pier_to"])
    for q in range(pier_r, rm + col):
        for s in (-1, 0, 1):
            x = int(round(cx + ux * q + tx * s))
            z = int(round(cz + uz * q + tz * s))
            if not w.has(x, dy, z):
                w.put(x, dy, z, p["light"] if (s == 0 and q % 8 == 0) else p["pave"])
                feats["steps"] += 1
        for s in (-2, 2):
            x = int(round(cx + ux * q + tx * s))
            z = int(round(cz + uz * q + tz * s))
            if not w.has(x, dy, z):
                w.put(x, dy, z, p["trim"])
                w.put(x, dy + 1, z, p["rail"])
                feats["rail"] += 1
        w.put(int(round(cx + ux * q)), dy - 1, int(round(cz + uz * q)), p["trim"])
        feats["corbel"] += 1
        if q % 6 == 0:                            # the same truss the catwalk carries
            for sgn in (-1, 1):
                for s in range(1, 3):
                    w.put(int(round(cx + ux * q + tx * s * sgn)), dy - 1,
                          int(round(cz + uz * q + tz * s * sgn)), p["collar_lo"])
                    feats["corbel"] += 1
                w.put(int(round(cx + ux * q + tx * 2 * sgn)), dy - 2,
                      int(round(cz + uz * q + tz * 2 * sgn)), p["collar_lo"])
                feats["corbel"] += 1
    # the head: lit, and railed on three sides so the only way off is forward
    for s in (-2, -1, 0, 1, 2):
        x = int(round(cx + ux * (pier_r - 1) + tx * s))
        z = int(round(cz + uz * (pier_r - 1) + tz * s))
        w.put(x, dy, z, p["light"] if abs(s) <= 1 else p["trim"])
        if abs(s) == 2:
            w.put(x, dy + 1, z, p["rail"])
        feats["steps"] += 1

    # ------------------------------------------------------------------ 7. THE RETURN COLUMN
    # A bubble lift in a lit cage, floor to rim: the way back up, the spine the helix winds
    # around, and the best free spectacle on the plot - a player shooting up the middle while
    # others drop around them.
    #
    # NOT CLAIMED AS WORKING. A bubble column is one of the three things this land's plan lists
    # as uncertifiable offline, and this repo cut two finished casino games rather than ship a
    # machine it could not judge. What is built here is the SHAFT; whether the ascent works and
    # whether the exit is dry is `requires_in_game`.
    yf = int(p["y_floor"])
    pr = int(p["lift_post_r"])
    # THE CATWALK CROSSES FROM THE FAR SIDE, opposite the start. The course leaves the rim on
    # the entry axis and a pier landing on the same cells would put the choice of "step off and
    # run" and "walk out to the lift" in one crowded gap; from the far side they are the two
    # ends of one line, which is also how you read the place: arrive west, run down, come back
    # up the middle, walk off east.
    cwd = math.radians(entry + 180.0)
    ex, ez = int(round(math.cos(cwd))), int(round(math.sin(cwd)))

    # THE WATER REACHES THE WALKING LEVEL, NOT THE FLOOR LEVEL. The deck's blocks occupy `dy`
    # and a player stands at `dy + 1`, so a column stopping at `dy` surfaces you inside the
    # floor. It runs one course higher, and the casing on the catwalk's side stops one course
    # short - so you rise to standing height and step straight out onto the head deck.
    #
    # The first build left that cell open and then PAVED IT: the head deck filled every cell of
    # the nine-by-nine that was not already taken, including the exit. A lift sealed on four
    # sides and a working one are the same picture in any render, which is why it is a test.
    crown = int(p["y_crown"]) if p.get("y_crown") else None
    top = (crown + 1) if crown else (dy + 1)
    w.put(cx, yf - 1, cz, "soul_sand")                # the bubble source
    # TWO EXITS WHEN THERE IS A CROWN, and the deck one is the anti-frustration contract. A
    # two-hundred-course run you restart from the very top after every miss is the "long run-back
    # after failure" the old brief forbids by name; getting off at the deck restarts the lower
    # hundred only, which is what makes the two halves separately runnable.
    exits = {(cx + ex, dy + 1, cz + ez)}
    if crown:
        exits.add((cx + ex, crown + 1, cz + ez))
    for y in range(yf, top + 1):
        w.put(cx, y, cz, "water")
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (cx + dx, y, cz + dz) in exits:
                continue
            w.put(cx + dx, y, cz + dz, p["lift_case"])
        feats["lift"] += 5

    # ------------------------------------------------------- 7b. THE SHAFT: ONE FRAME, FLOOR TO CROWN
    # Jack, on the first tower: "i think the tower and the underneath need to feel connected, not
    # completely differently, and needs to be much more visually designed/impressive than just a
    # thinning tower stem". Both true, and the render showed exactly why.
    #
    # IT WAS TWO STRUCTURES STACKED. A dark masonry drum above the deck and a thin lit lattice
    # below it, touching only where they met - two vocabularies, unrelated, one on top of the
    # other. The fix is not to blend them; it is to build ONE THING and let it change what it DOES
    # with height. Eight RIBS and a copper RING BEAM every eight courses run the whole two hundred
    # and five, floor to crown, and they are the same members at the bottom of the pool as at the
    # top of the sky. What changes is the infill: open between the ribs below the deck, where you
    # are looking DOWN the well and a wall would block the one view the land is composed around,
    # and panelled above it, where the land needs mass on the skyline.
    #
    # AND A THINNING STEM IS NOT A DESIGN. The first tower tapered ten to seven over ninety-eight
    # courses - three blocks over four setbacks, so under one block a step, and a silhouette that
    # cannot be seen is not a silhouette. This one steps TWELVE to SIX in four real setbacks, each
    # landing on a projecting bracket course. The ribs stand PROUD of the panel by a cell, which is
    # the one thing that stops a voxel cylinder reading as a smooth grey pipe; the base is a wider
    # drum with its own cornice so the shaft GROWS out of the gallery instead of piercing it; and
    # the windows have real heads and sills, so they read as openings rather than as places the
    # wall ran out.
    ribs = int(p["ribs"])
    tie = max(int(p["tie_every"]), 2)
    tr0, tr1 = float(p["tower_r"]), float(p["tower_top"])
    stages = max(int(p["tower_stages"]), 1)
    wall = int(p["tower_wall"])
    base_h = int(p["base_h"])

    def profile(y):
        """(radius, stage, is_setback) at height `y` - one curve for the whole shaft."""
        if not crown or y <= dy + base_h:
            # THE FLARE RAMPS ONE CELL AT A TIME. Stepping straight from r12 below the deck
            # to r14 above it moved every rib two cells in one course, and two cells apart
            # is not adjacent: the shaft came apart into 21,288 cells below and 13,479
            # above, which is the two-structures problem this rewrite exists to fix,
            # reproduced by the very course that was meant to join them.
            if not crown or y <= dy:
                return tr0, -1, False
            # A BATTER, NOT A LEDGE. The flare rose to +2 and dropped straight back to tr0 at
            # the first setback - two blocks in one course, so the PANEL was not vertically
            # adjacent across the seam and the shaft shed two-by-two islands of wall. The ribs
            # were bridged for exactly this and the panel was not. It rises over two courses
            # and falls over two, which is also what a plinth does.
            return tr0 + min(min(y - dy, 2), max(dy + base_h - y, 0)), -1, False
        span = max(crown - (dy + base_h), 1)
        k = min(int((y - dy - base_h) / span * stages), stages - 1)
        r = tr0 + (tr1 - tr0) * (k / max(stages - 1, 1))
        edge = dy + base_h + int(k * span / stages)
        return r, k, (y == edge and k > 0)

    stage_h = max(int((crown - dy - base_h) / stages), 1) if crown else 1
    # A RIB THAT CHANGES RADIUS CHANGES CELL, AND A DIAGONAL STEP IS NOT A STEP. Every flare
    # and every setback moves each rib to a new column, so the course above is diagonal from
    # the course below and the shaft comes apart there - it shipped as 21,288 cells below the
    # deck and 13,475 above, which is the two-structures problem this rewrite exists to fix,
    # reproduced by the courses meant to join them. Same failure as the ear tips, the
    # ossicones and the Lowland Root's braid, and the same cure: carry the PREVIOUS column
    # one course up so the two are orthogonal neighbours.
    prev_rib: dict[int, tuple[int, int]] = {}
    prev_r = None
    for y in range(yf, top):
        r, k, setback = profile(y)
        panelled = bool(crown) and y > dy + 1
        ring = (y - yf) % tie == 0
        for b in range(ribs):
            a = math.radians(b * 360.0 / ribs)
            # THE RIB, one cell proud of the panel line, and lit every sixteen courses
            rx = int(round(cx + (r + 1) * math.cos(a)))
            rz = int(round(cz + (r + 1) * math.sin(a)))
            w.put(rx, y, rz, p["light"] if (crown and (crown - y) % 16 == 0) else p["lift_case"])
            feats["post"] += 1
            was = prev_rib.get(b)
            if was and was != (rx, rz):
                w.put(was[0], y, was[1], p["lift_case"])   # the bridge over the step
                feats["post"] += 1
            prev_rib[b] = (rx, rz)
            ix = int(round(cx + r * math.cos(a)))
            iz = int(round(cz + r * math.sin(a)))
            if (ix, iz) != (rx, rz):
                w.put(ix, y, iz, p["lift_case"])
                feats["post"] += 1
        if ring or setback:
            # THE RING BEAM: what actually ties two hundred courses into one object
            for x in range(int(cx - r - 2), int(cx + r + 3)):
                for z in range(int(cz - r - 2), int(cz + r + 3)):
                    d = math.hypot(x - cx, z - cz)
                    if r - 0.5 <= d <= r + 1.5 and not w.has(x, y, z):
                        w.put(x, y, z, p["trim"])
                        feats["post"] += 1
            for b in range(ribs):                       # and the spokes in to the lift casing
                a = math.radians(b * 360.0 / ribs)
                # SIX-CONNECTED, AND THE DIAGONAL SPOKES WERE NOT. With eight ribs, four
                # bearings are at 45 degrees, where consecutive q give (2,2), (3,3), (4,4) -
                # a diagonal staircase, and a diagonal neighbour is not a neighbour. Every
                # cell of those four spokes shipped as its own component. Fourth time this
                # exact failure has appeared in this design; bridge the step.
                last = None
                for q in range(2, int(r)):
                    sx = int(round(cx + q * math.cos(a)))
                    sz = int(round(cz + q * math.sin(a)))
                    if last and last != (sx, sz) and abs(sx - last[0]) + abs(sz - last[1]) > 1:
                        if not w.has(sx, y, last[1]):
                            w.put(sx, y, last[1], p["trim"])
                            feats["post"] += 1
                    if not w.has(sx, y, sz):
                        w.put(sx, y, sz, p["trim"])
                        feats["post"] += 1
                    last = (sx, sz)
        if setback:
            # the bracket: a setback PROJECTS, or the step above it reads as a mistake
            for x in range(int(cx - r - 3), int(cx + r + 4)):
                for z in range(int(cz - r - 3), int(cz + r + 4)):
                    d = math.hypot(x - cx, z - cz)
                    if r + 1.5 < d <= r + 2.5 and not w.has(x, y, z):
                        w.put(x, y, z, p["trim"])
                        feats["post"] += 1
        if not panelled:
            prev_r = r
            continue
        # THE PANEL, set BACK from the ribs, with a window in every bay between them.
        #
        # A SETBACK COURSE CARRIES BOTH RADII. Each step is 2.7 blocks at a 12->4 taper, so
        # the panel above a setback is not vertically adjacent to the panel below it and the
        # shaft sheds a ring of two-by-two islands at every stage - the ribs were bridged for
        # exactly this and the panel was not. Filling from the outer band to the inner one on
        # that one course joins them AND is what a setback ledge is: the step you can see.
        lo_r = min(r, prev_r) if (prev_r is not None and prev_r != r) else r
        hi_r = max(r, prev_r) if (prev_r is not None and prev_r != r) else r
        prev_r = r
        for x in range(int(cx - hi_r - 1), int(cx + hi_r + 2)):
            for z in range(int(cz - hi_r - 1), int(cz + hi_r + 2)):
                d = math.hypot(x - cx, z - cz)
                if not (lo_r - wall + 0.5 <= d <= hi_r - 0.5) or w.has(x, y, z):
                    continue
                a = math.degrees(math.atan2(z - cz, x - cx)) % 360.0
                off = min(abs((a - b * 360.0 / ribs + 180) % 360 - 180) for b in range(ribs))
                h = (y - dy - base_h) % stage_h
                win = off > (360.0 / ribs / 2) - 7 and 3 <= h <= stage_h - 4
                if win and not setback and y < crown - 3:
                    continue                            # left open: the window
                mat = p["collar_hi"] if k % 2 == 0 else p["kerb"]
                if hash01(x, y, z, p["seed"], 7) < p["weather"] * 0.5:
                    mat = p["collar_lo"]
                w.put(x, y, z, mat)
                feats["post"] += 1

    if crown:
        # THE BASE CORNICE, so the shaft stands on something at the deck rather than passing through
        for q in (0, 1):
            y = dy + base_h + q
            for x in range(int(cx - tr0 - 4), int(cx + tr0 + 5)):
                for z in range(int(cz - tr0 - 4), int(cz + tr0 + 5)):
                    d = math.hypot(x - cx, z - cz)
                    if tr0 + 1.5 - q <= d <= tr0 + 3.5 - q and not w.has(x, y, z):
                        w.put(x, y, z, p["trim"] if q else p["collar_hi"])
                        feats["post"] += 1
        # AND THE CROWN: a corbelled overhang, a parapet and DARK merlons - the void tower's own
        # recipe, which this repo records as the thing that finally made a voxel tower read, and
        # its own lesson that from directly above a merlon in the parapet's colour is invisible.
        for q, grow in ((0, 2.5), (1, 3.5), (2, 2.5)):
            y = crown - 2 + q
            for x in range(int(cx - tr1 - 5), int(cx + tr1 + 6)):
                for z in range(int(cz - tr1 - 5), int(cz + tr1 + 6)):
                    d = math.hypot(x - cx, z - cz)
                    if tr1 + 1.5 <= d <= tr1 + grow and not w.has(x, y, z):
                        w.put(x, y, z, p["trim"] if q == 1 else p["collar_hi"])
                        feats["post"] += 1
        for b in range(ribs * 2):
            a = math.radians(b * 360.0 / (ribs * 2))
            # ON the parapet, not beyond it: at tr1+3 the merlons stood a cell outside the
            # top cornice course and four of them shipped as two-cell strays.
            mx = int(round(cx + (tr1 + 2) * math.cos(a)))
            mz = int(round(cz + (tr1 + 2) * math.sin(a)))
            w.put(mx, crown + 1, mz, p["collar_deep"])
            w.put(mx, crown + 2, mz, p["collar_deep"] if b % 2 else p["light"])
            feats["post"] += 2

    # THE HEAD DECK, where the lift arrives at the deck course. Everything inside the ribs that
    # is not the water column: you surface at walking height and step straight out onto it.
    for x in range(cx - int(tr0), cx + int(tr0) + 1):
        for z in range(cz - int(tr0), cz + int(tr0) + 1):
            if (x, z) == (cx, cz) or w.has(x, dy, z):
                continue
            if math.hypot(x - cx, z - cz) > tr0 - 0.5:
                continue
            w.put(x, dy, z, p["pave"])
            feats["lift"] += 1

    # ------------------------------------------------------------------ 8. THE CATWALK
    # ONE SPOKE, NOT A CROSS, and it is also the only thing that makes the rim and the shaft one
    # object. A rewrite of the shaft deleted this section by accident and the design immediately
    # came apart into 21,288 cells of collar-and-gallery at r34-62 and 13,483 cells of shaft at
    # r0-23 - two perfectly-built structures with nothing between them. The component count is
    # what caught it; nothing else could, because both halves are correct.
    #
    # Two crossing walkways would quarter the view down the shaft, which is the whole reason the
    # mouth is this wide. A single pier on the entry axis costs one sightline and gives the land
    # its best one: you stand at the middle of the mouth and look straight down two hundred
    # courses. It starts at the shaft's own face and runs out to the collar.
    tx, tz = -ez, ex
    half = int(p["walk"]) // 2
    for q in range(int(tr0), rm + col):
        for s in range(-half, half + 1):
            x = int(round(cx + ex * q + tx * s))
            z = int(round(cz + ez * q + tz * s))
            if w.has(x, dy, z):
                continue
            w.put(x, dy, z, p["light"] if (s == 0 and q % 9 == 0) else p["pave"])
            feats["steps"] += 1
        for s in (-half - 1, half + 1):
            x = int(round(cx + ex * q + tx * s))
            z = int(round(cz + ez * q + tz * s))
            if w.has(x, dy, z):
                continue
            w.put(x, dy, z, p["trim"])
            w.put(x, dy + 1, z, p["rail"])
            feats["rail"] += 1
        # the spine beam, continuous, one course under the walking line
        bx = int(round(cx + ex * q))
        bz = int(round(cz + ez * q))
        if not w.has(bx, dy - 1, bz):
            w.put(bx, dy - 1, bz, p["trim"])
            feats["corbel"] += 1
        if q % 6 == 0:
            # THE STRUT HAS TO REACH THE SPINE OR IT IS NOT A TRUSS, IT IS A LOOSE BLOCK.
            for sgn in (-1, 1):
                for s in range(1, half + 2):
                    x = int(round(cx + ex * q + tx * s * sgn))
                    z = int(round(cz + ez * q + tz * s * sgn))
                    if not w.has(x, dy - 1, z):
                        w.put(x, dy - 1, z, p["collar_lo"])
                        feats["corbel"] += 1
                x = int(round(cx + ex * q + tx * (half + 1) * sgn))
                z = int(round(cz + ez * q + tz * (half + 1) * sgn))
                if not w.has(x, dy - 2, z):
                    w.put(x, dy - 2, z, p["collar_lo"])
                    feats["corbel"] += 1

    # ------------------------------------------------------------------ 8b. THE CROWN
    # A deck on the column head at Y300 and a pier out to r33, which is the deck pier ninety-
    # eight courses higher and in open sky. You ride the lift the whole way, walk out along a
    # board with two hundred courses of nothing under it, and jump.
    if crown:
        cr = int(p["crown_r"])
        for x in range(cx - cr, cx + cr + 1):
            for z in range(cz - cr, cz + cr + 1):
                if math.hypot(x - cx, z - cz) > cr + 0.5 or (x, z) == (cx, cz):
                    continue                     # never over the water: the lift has to arrive
                if w.has(x, crown, z):
                    continue
                edge = math.hypot(x - cx, z - cz) > cr - 1.5
                w.put(x, crown, z, p["trim"] if edge else p["pave"])
                feats["lift"] += 1
                if edge and (x, z) != (cx + ex, cz + ez):
                    w.put(x, crown + 1, z, p["rail"])   # railed, except where you step out
                    feats["rail"] += 1
        # the pier: the same board as the deck's, and the same truss under it
        chalf = 1
        # OUTWARD FROM THE PLATFORM, and the first version had this range backwards:
        # range(33, 8) is EMPTY, so the pier body was never built at all and its five-cell
        # head shipped as a floating component in open sky. The deck pier reads the same way -
        # inner end first, outward - and copying it without re-checking the bounds is how a
        # loop that runs zero times looks exactly like one that works.
        for q in range(cr, int(p["crown_pier_to"]) + 1):
            for t in range(-chalf, chalf + 1):
                x = int(round(cx + ux * q + tx * t))
                z = int(round(cz + uz * q + tz * t))
                if not w.has(x, crown, z):
                    w.put(x, crown, z, p["light"] if (t == 0 and q % 8 == 0) else p["pave"])
                    feats["steps"] += 1
            for t in (-chalf - 1, chalf + 1):
                x = int(round(cx + ux * q + tx * t))
                z = int(round(cz + uz * q + tz * t))
                if not w.has(x, crown, z):
                    w.put(x, crown, z, p["trim"])
                    w.put(x, crown + 1, z, p["rail"])
                    feats["rail"] += 1
            bx = int(round(cx + ux * q))
            bz = int(round(cz + uz * q))
            w.put(bx, crown - 1, bz, p["trim"])          # the spine beam
            feats["corbel"] += 1
            if q % 6 == 0:
                for sgn in (-1, 1):
                    for t in range(1, chalf + 2):
                        w.put(int(round(cx + ux * q + tx * t * sgn)), crown - 1,
                              int(round(cz + uz * q + tz * t * sgn)), p["collar_lo"])
                        feats["corbel"] += 1
                    w.put(int(round(cx + ux * q + tx * (chalf + 1) * sgn)), crown - 2,
                          int(round(cz + uz * q + tz * (chalf + 1) * sgn)), p["collar_lo"])
                    feats["corbel"] += 1
        # the head, lit and railed on three sides so the only way off is forward
        for t in (-2, -1, 0, 1, 2):
            x = int(round(cx + ux * (int(p["crown_pier_to"]) - 1) + tx * t))
            z = int(round(cz + uz * (int(p["crown_pier_to"]) - 1) + tz * t))
            w.put(x, crown, z, p["light"] if abs(t) <= 1 else p["trim"])
            if abs(t) == 2:
                w.put(x, crown + 1, z, p["rail"])
            feats["steps"] += 1

    # ------------------------------------------------------------------ 9. THE MAST RING
    # PRISMWORKS LOST ITS SKYLINE WHEN IT LOST ITS SPIRE, and that had to be answered rather
    # than shrugged at. v1 held one of the park's three skyline dominants at 84 courses; a well
    # is entirely at and below deck level, so from anywhere in the park the land would read as a
    # low grey ring - which is a real loss even though the spire itself was a decorated tower
    # with no ride in it.
    #
    # The answer is NOT another tower. Eight masts on the gallery's outer edge, one over each
    # balcony, is a RING that reads as one object at distance and as a rhythm close up - the
    # relay pylons the land's own frontage already used ("SIGNAL 1" through "SIGNAL 6") turned
    # into the thing they were always pointing at. Eighteen courses each: tall enough to clear
    # the eye and carry from across the land, and nowhere near the Sky Lift's seventy-four, so
    # the park keeps the two dominants it has rather than gaining a third that competes.
    # ON THE GALLERY, NOT BESIDE IT. At g1 + 1 the masts stand one cell OUTSIDE the paving
    # and four of the eight came out as detached 28-cell components - a mast needs a floor
    # under it like anything else, and the gallery's outer band is where it gets one.
    mr = g1 - 2
    for i in range(int(p["masts"])):
        b = math.radians(bay_angles[i % len(bay_angles)])
        mx = int(round(cx + mr * math.cos(b)))
        mz = int(round(cz + mr * math.sin(b)))
        for q in range(int(p["mast_h"])):
            y = dy + 1 + q
            mat = p["trim"] if q % 4 == 3 else p["kerb"]
            if q in (5, 11, 16):
                mat = p["light"]
                feats["light"] += 1
            w.put(mx, y, mz, mat)
            feats["post"] += 1
            if q in (7, 13):                    # the cross arms, so it is an instrument
                for dxx, dzz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    w.put(mx + dxx, y, mz + dzz, p["lift_cage"])
                    feats["post"] += 1
        w.put(mx, dy + int(p["mast_h"]) + 1, mz, "end_rod", facing="up")
        w.put(mx, dy, mz, p["trim"])            # its own footing in the gallery paving
        feats["post"] += 2

    # ------------------------------------------------------------------ 10. THE PRACTICE
    # A FIRST-TIMER HAS TO MEET THE MOVE BEFORE THE HUNDRED-COURSE DROP. The old Prismworks
    # brief made it an acceptance test - "a first-time player finds practice without reading a
    # dense sign" - and v1 never built one, so the only way to learn the jump was to commit to
    # the whole run and fall off it.
    #
    # ON THE GALLERY, WHERE A MISS COSTS ONE BLOCK. Beside the pier was the obvious place and it
    # is wrong: the pier is over the hole, so "practice" there is the real thing with the real
    # consequence. These sit one course above the paving on the gallery's OUTER band, leaving
    # the inner six cells of the promenade clear to walk - a hop you miss drops you onto the
    # floor you were standing on.
    prr = g1 - 1
    step = math.degrees(4.0 / prr)                # 4 blocks of arc: the sprint jump, measured
    for i in range(int(p["practice"]) + 1):
        b = math.radians(entry + float(p["practice_from"]) + i * step)
        px = int(round(cx + prr * math.cos(b)))
        pz = int(round(cz + prr * math.sin(b)))
        w.put(px, dy + 1, pz, p["light"] if i in (0, int(p["practice"])) else p["trim"])
        feats["steps"] += 1
    b0 = math.radians(entry + float(p["practice_from"]) - step)
    sx0 = int(round(cx + prr * math.cos(b0)))
    sz0 = int(round(cz + prr * math.sin(b0)))
    w.put(sx0, dy + 1, sz0, "oak_sign", rotation=0)
    w.sign(sx0, dy + 1, sz0, front=("PRACTICE", "eight jumps", "free", "no drop"))
    feats["steps"] += 1

    return w.canvas({"kind": "well", "profile_view": "top", "facing": [-1, 0],
                     "features_built": feats, "dig": [list(d) for d in dig],
                     "centre": [cx, cz], "r_mouth": rm, "y_floor": yf,
                     "shaft_r": int(p["tower_r"]) + int(p.get("base_h") and 2 or 0)})


# ---------------------------------------------------------------------- THE RIG

RIG = {
    # THE WORLD THE GANTRY HANGS IN, and it had none. The rig was generated from the routes
    # alone and knew nothing about the well it hangs inside, so where the sky run passes the
    # deck its beam landed squarely on the CATWALK - eleven cells at r21-23 on the entry axis,
    # reported as overlap by the pipeline and by nothing in the generator. A design that hangs
    # inside another one has to be told what is already there.
    "under": None,
    # ONE OR MANY: the well has two concentric runs and one gantry serves both, so that the
    # beam is derived from every route it hangs over rather than from a helix re-computed here.
    "route": ["out/PF Crown Descent.scan.json", "out/PF Prism Descent.scan.json"],
    "centre": [97590, 80815],
    "hang": 4,                  # courses above a landing; the parkour's headroom is 3
    "post_at": ("rest",),       # which move kinds get a real post up to the gantry
    "beam": "waxed_copper_block",
    "beam_alt": "polished_blackstone_bricks",
    "web": "iron_bars",
    "light": "ochre_froglight",
    "light_every": 7,
    "seed": 13,
}


def build_rig(cfg: dict, donors=None) -> Canvas:
    """THE GANTRY THE COURSE HANGS UNDER - and the reason it exists is a render.

    `PF Prism Descent` is 167 blocks: 86 one-block landings, nine slime pads and eight rests,
    which is exactly right for a parkour course and, seen in the middle of a hundred-wide mouth,
    reads as CONFETTI. A dusting of single cells at four-block spacing over a hundred courses of
    void is not a helix; it is noise. The Island Run gets away with it because it winds around an
    island and every landing reads against terrain - here there is nothing behind it at all.

    This repo has written the rule down twice and both times about lines rather than cells: the
    deck soffit drew 215 grid runs of which 184 were one or two cells - *"it is not a grid, it is
    confetti"* - and the answer both times was that A BLOCK IS ONLY AS GOOD AS THE LINE IT IS
    PART OF. So the fix is not more landings or brighter ones, it is a continuous line for them
    to belong to.

    A GANTRY OVERHEAD, NOT A RIBBON BESIDE. Three things follow from putting it above:

      it cannot be walked, so it does not trivialise the course it exists to explain - a
      walkable ribbon at the same radius is simply a way to get to the bottom without jumping;
      it clears the jumps by construction, because the parkour's own `headroom` is three and the
      beam sits at four, so nothing it places can be collided with mid-jump;
      and it lights the course from ABOVE, which is where a light belongs when the landing
      itself is the other lamp.

    IT IS DERIVED FROM THE ROUTE, NEVER RE-DERIVED. The course records every move in its own
    sidecar; this reads that list. Two generators computing the same helix from the same
    parameters is exactly the drift `proportions.measure` and `rubric.score` share an entry
    point to avoid - and here the drift would be a gantry hanging over empty air.

    POSTS ONLY AT THE RESTS. A post beside a one-block landing is something to clip on the way
    in, and the landing is meant to be the whole difficulty. A rest is a 3x3 checkpoint you are
    standing still on, so a post there is structure rather than a hazard - eight of them down the
    run, which is what makes the gantry read as CARRIED rather than as a floating ribbon.
    """
    import json
    import os

    p = {**RIG, **cfg}
    ctx = Ctx(p["under"]) if p.get("under") else None
    paths = p["route"] if isinstance(p["route"], (list, tuple)) else [p["route"]]
    routes = []
    for path in paths:
        if not os.path.exists(path):
            raise ValueError(f"the rig needs the course's sidecar: {path} is not there")
        r = [tuple(c) for c in json.load(open(path, encoding="utf-8")).get("route") or ()]
        if len(r) < 8:
            raise ValueError(f"the course at {path} has only {len(r)} moves - regenerate it")
        routes.append(r)
    route = [c for r in routes for c in r]      # for the bars: every landing of every run

    w = World()
    cx, cz = int(p["centre"][0]), int(p["centre"][1])
    hang = int(p["hang"])
    # EVERY LANDING'S OWN COLUMN IS OFF LIMITS, not just the one this cell is over.
    #
    # Hanging the beam four courses over the route clears the move it belongs to, because the
    # parkour's headroom is three. It does NOT clear the others: the run descends, so a beam at
    # move i's y+4 can sit inside move j's headroom where j is four or more courses lower at
    # about the same place, and a post standing two cells outboard of a REST can land squarely
    # in a neighbouring ledge's column. Thirty-five cells did, and every one of them is
    # something to clip on the way into a landing - invisible in any render, because a beam
    # above a landing and a beam in front of one draw identically.
    # AND A REST IS 3x3, NOT ONE CELL. `gen/parkour.py` builds a rest platform with
    # `rest_half` of 1, so eight of its nine cells never appear in the recorded route at all -
    # only the centre does. Barring the centres alone let the gantry put two beam cells inside
    # the corner of a checkpoint you stand on, and neither design could see it: the only thing
    # that reported them was the park assembly's module clash check.
    def blocked(x, y, z):
        """Occupied in the WORLD, so nothing here may claim it."""
        if ctx is None:
            return False
        return ctx.name_at(x, y, z).split("[")[0].split(":")[-1] not in AIRY

    barred = set()
    for c in route:
        h = 1 if (len(c) > 3 and c[3] == "rest") else 0
        for dx in range(-h, h + 1):
            for dz in range(-h, h + 1):
                for q in range(0, 4):
                    barred.add((c[0] + dx, c[1] + q, c[2] + dz))
    feats = {"beam": 0, "web": 0, "post": 0, "light": 0}

    def beam_at(i, x, y, z):
        mat = p["beam"] if hash01(x, y, z, p["seed"]) > 0.34 else p["beam_alt"]
        if i % max(int(p["light_every"]), 1) == 0:
            mat = p["light"]
            feats["light"] += 1
        if not w.has(x, y, z) and (x, y, z) not in barred and not blocked(x, y, z):
            w.put(x, y, z, mat)
            feats["beam"] += 1

    # ------------------------------------------------------------ the beam itself
    # Drawn as a polyline through every move, one cell wide with a second cell OUTWARD, so it
    # reads as a rail rather than as a string of dots - the same reason the collar is three
    # cells thick rather than one.
    #
    # SIX-CONNECTED, AND IT WAS NOT THE FIRST TIME. Sampling the line and rounding each sample
    # gives cells that step DIAGONALLY, and a diagonal neighbour is not a neighbour: the first
    # build came out as 168 separate fragments, which is the confetti this design exists to fix,
    # reproduced in the fix. Same failure as the ear tips, the ossicones and the braided root.
    # So the walk moves one axis at a time and the outward cell takes its DOMINANT axis only.
    def walk(a, b):
        x, y, z = a
        yield (x, y, z)
        while (x, y, z) != b:
            dx, dy, dz = b[0] - x, b[1] - y, b[2] - z
            if abs(dx) >= abs(dy) and abs(dx) >= abs(dz) and dx:
                x += 1 if dx > 0 else -1
            elif abs(dz) >= abs(dy) and dz:
                z += 1 if dz > 0 else -1
            elif dy:
                y += 1 if dy > 0 else -1
            else:
                break
            yield (x, y, z)

    # PER ROUTE, NEVER ACROSS THE JOIN. Zipping the concatenated list pairs the last move of
    # the sky run with the first of the deck run and draws a beam two hundred courses long
    # straight through the middle of the well.
    n = 0
    for one in routes:
        for a, b in zip(one, one[1:]):
            for (x, y, z) in walk((a[0], a[1] + hang, a[2]), (b[0], b[1] + hang, b[2])):
                beam_at(n, x, y, z)
                n += 1
                # the outward cell: a rail has WIDTH, and width is what carries at distance. On the
                # dominant axis only, or it lands diagonally and is its own loose block.
                ddx, ddz = x - cx, z - cz
                ox, oz = (x + (1 if ddx > 0 else -1), z) if abs(ddx) >= abs(ddz) \
                    else (x, z + (1 if ddz > 0 else -1))
                if not w.has(ox, y, oz) and (ox, y, oz) not in barred and not blocked(ox, y, oz):
                    w.put(ox, y, oz, p["web"])
                    feats["web"] += 1

    # ------------------------------------------------------------ the posts, at the rests only
    for (x, y, z, kind) in ((c[0], c[1], c[2], c[3]) for c in route if len(c) > 3):
        if kind not in tuple(p["post_at"]):
            continue
        d = math.hypot(x - cx, z - cz) or 1.0
        px = int(round(x + 2 * (x - cx) / d))
        pz = int(round(z + 2 * (z - cz) / d))
        for q in range(0, hang + 1):
            if (not w.has(px, y + q, pz) and (px, y + q, pz) not in barred
                    and not blocked(px, y + q, pz)):
                w.put(px, y + q, pz, p["beam_alt"] if q < hang else p["beam"])
                feats["post"] += 1
        # and the arm back to the beam, so the post is joined to what it carries
        ax = int(round(x + (x - cx) / d))
        az = int(round(z + (z - cz) / d))
        if (not w.has(ax, y + hang, az) and (ax, y + hang, az) not in barred
                and not blocked(ax, y + hang, az)):
            w.put(ax, y + hang, az, p["beam"])
            feats["post"] += 1

    # ------------------------------------------------------------ STITCH WHAT THE BARS BROKE
    # BARRING IS RIGHT AND IT CUTS THE LINE. Where the helix passes over itself - twice, at about
    # a turn apart - the beam for the lower pass lands inside the headroom of the upper one, so
    # those cells are correctly refused and the beam comes apart into fragments. A gantry in
    # pieces is the confetti this design exists to fix, so the answer is to go AROUND rather than
    # to stop barring: a breadth-first walk through unbarred air from each loose fragment back to
    # the main body, laying beam as it goes.
    def components(scope):
        cells = set(scope)
        out, seen = [], set()
        for c0 in cells:
            if c0 in seen:
                continue
            stack, comp = [c0], []
            seen.add(c0)
            while stack:
                x, y, z = stack.pop()
                comp.append((x, y, z))
                for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                    q = (x + d[0], y + d[1], z + d[2])
                    if q in cells and q not in seen:
                        seen.add(q)
                        stack.append(q)
            out.append(comp)
        return sorted(out, key=len, reverse=True)

    for one in routes:
        # PER ROUTE. Two courses are two helices and their gantries are two LINES - stitching
        # them to each other would draw a beam across ten blocks of open void between r30 and
        # r20, which is a bridge nobody asked for and might sit in a jump path. What has to be
        # one line is each RUN's own gantry, not the design as a whole.
        mine = {c for c in w.cells if any(
            abs(c[0] - m[0]) <= 6 and abs(c[2] - m[2]) <= 6 and 0 <= c[1] - m[1] <= 6
            for m in one)}
        for _ in range(8):
            comps = components(mine)
            if len(comps) <= 1:
                break
            main = set(comps[0])
            joined = False
            for frag in comps[1:]:
                # FROM THE NEAREST CELL, NOT AN ARBITRARY ONE. The sky run's gantry breaks
                # where the CATWALK crosses it at the deck, and the two halves are a
                # hundred courses long each - so a flood started at `frag[0]` begins at
                # whichever end the set happened to yield and exhausts its budget before it
                # reaches the junction. The gap is one cell wide; the search just has to
                # start beside it.
                start = min(frag, key=lambda c: min(
                    abs(c[0] - q[0]) + abs(c[1] - q[1]) + abs(c[2] - q[2]) for q in main))
                prevs, queue, seen = {start: None}, [start], {start}
                hit = None
                for _step in range(4000):
                    if not queue:
                        break
                    cur = queue.pop(0)
                    if cur in main:
                        hit = cur
                        break
                    for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                        q = (cur[0] + d[0], cur[1] + d[1], cur[2] + d[2])
                        if q in seen or q in barred or blocked(*q):
                            continue
                        seen.add(q)
                        prevs[q] = cur
                        queue.append(q)
                if hit is None:
                    continue
                node = hit
                while node is not None:
                    if not w.has(*node):
                        w.put(node[0], node[1], node[2], p['beam_alt'])
                        feats['beam'] += 1
                    mine.add(node)
                    node = prevs[node]
                joined = True
            if not joined:
                break

    # AND DROP WHAT STILL WILL NOT JOIN. A beam stub the walk cannot reach - barred out on every
    # side by the landings it runs between - is five cells hanging in a two-hundred-course void,
    # which is the confetti this whole design exists to remove. A five-cell GAP in an eighteen-
    # hundred-cell line is invisible; five floating blocks are not. Same call `_drop_defer_orphans`
    # makes one file over: if it cannot be carried, it should not be placed.
    for _ in range(4):
        comps = components(set(w.cells))
        loose = [c for c in comps[1:] if len(c) < 12]
        if not loose:
            break
        for frag in loose:
            for cell in frag:
                w.cells.pop(cell, None)
                feats["beam"] -= 1

    return w.canvas({"kind": "prismrig", "profile_view": "top", "facing": [-1, 0],
                     "features_built": feats, "route_from": list(paths)})
