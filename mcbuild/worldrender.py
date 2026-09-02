"""Render compiled Skyblock infrastructure contracts into sparse placeable chunks.

This is WorldSpec layer 1 and 2 - platform and infrastructure - and it is the largest single
line in PARK_VISUAL_AND_BUDGET_SPEC.md's programme (42,000 blocks: "shared paths, retaining
edges, service, lighting, safety ... makes the island feel intentionally built and safe rather
than objects on void").

Paving a route deck alone does not do that job. A deck one course thick over open void is a
floating ribbon: it has no edge you can see, nothing under it, and nothing to stop a player
walking off it in the dark. So this renders, in order:

    platform   a course of structure under every public deck, so paving stands on something
    deck       the walking surface itself
    kerb       a visible edge course either side, which is what makes a path read as built
    rail       a guard where a route is a bridge or carries a declared rail requirement
    rim        the protected outer band: retaining edge and void-safety, not decoration
    light      warm reliable lighting on the public network at a stated interval

**PALETTE CHANGES ARE PART OF THE INFRASTRUCTURE, NOT OF THE BUILDINGS.** PARK_FULL_BUILD_SPEC
requires the public spine to "visibly change palette" at each land edge, and a spine that reads
the same for 600 blocks tells a player nothing about where they are. The palette is chosen per
REGION from the plan's own region bounds, so a land edge cannot drift away from where the
WorldSpec says it is.

Every block here is checked cheap-and-1.19 by ``tests/test_worldrender.py``: the dirt/grass
family is CURRENCY on this server and appears nowhere.
"""
from __future__ import annotations

from .world import SparseWorld

#: Per-land infrastructure palette. Cheap tier only, and each land's own stone/timber - the
#: transition a walker sees at U 170, 215, 385 and 430 is these tables changing, nothing more.
PALETTES = {
    # NO COBBLESTONE ANYWHERE. It was the single most-used block in the park (44,027 cells, 17.7%)
    # and 9,002 of those were this table - a raw quarry block used as the finished walking surface
    # and edge of a theme park. Jack's call: deepslate, smooth stone, brick.
    #
    # PLATFORM IS UNDER THE DECK AND NOBODY SEES IT, so it is cheap `stone_bricks` in every land
    # and the ok-tier budget is spent on the surfaces that are actually looked at.
    "frontier": {"deck": "minecraft:stone_brick_slab", "kerb": "minecraft:polished_blackstone_bricks",
                 "platform": "minecraft:stone_bricks", "rim": "minecraft:deepslate_bricks",
                 "batter": "minecraft:cracked_stone_bricks", "post": "minecraft:spruce_fence",
                 "light": "minecraft:lantern"},
    "frontier_reach": {"deck": "minecraft:stone_brick_slab", "kerb": "minecraft:polished_blackstone_bricks",
                       "platform": "minecraft:stone_bricks", "rim": "minecraft:deepslate_bricks",
                       "batter": "minecraft:cracked_stone_bricks", "post": "minecraft:spruce_fence",
                       "light": "minecraft:lantern"},
    "midway": {"deck": "minecraft:smooth_stone_slab", "kerb": "minecraft:polished_blackstone_bricks",
               "platform": "minecraft:stone_bricks", "rim": "minecraft:smooth_stone",
               "batter": "minecraft:stone_bricks", "post": "minecraft:oak_fence",
               "light": "minecraft:lantern"},
    "prism_reach": {"deck": "minecraft:polished_deepslate_slab", "kerb": "minecraft:stone_bricks",
                    "platform": "minecraft:stone_bricks", "rim": "minecraft:deepslate_tiles",
                    "batter": "minecraft:polished_blackstone_bricks",
                    "post": "minecraft:polished_blackstone_brick_wall", "light": "minecraft:soul_lantern"},
    "prismworks": {"deck": "minecraft:polished_deepslate_slab", "kerb": "minecraft:stone_bricks",
                   "platform": "minecraft:stone_bricks", "rim": "minecraft:deepslate_tiles",
                   "batter": "minecraft:polished_blackstone_bricks",
                   "post": "minecraft:polished_blackstone_brick_wall", "light": "minecraft:soul_lantern"},
}
DEFAULT = PALETTES["midway"]

#: A guest path is lit at a spacing a lantern can actually cover. A lantern is light 15 and a
#: mob spawns at 0, so 9 leaves real margin at the midpoint after the falloff over a walked
#: surface - the same interval `transit.py` and the lowland's own posts already use.
LIGHT_EVERY = 9
#: The protected rim band, from PARK_FULL_BUILD_SPEC: "V 170-199 is support, terrain, void
#: safety, sightline protection". Only its inner face is built; the rest is reserve.
RIM_FROM = 170
RIM_EVERY = 4
#: how far the batter falls away toward the void, and how often it steps down
RIM_BAND, RIM_STEP, RIM_BUTTRESS = 29, 4, 12
#: A REACH IS A CAUSEWAY, so its shoulder starts far further in than a land's does. A land uses
#: its depth for programme and only its last thirty for edge; a reach carries one way through and
#: one identity beat, and everything outboard of those is structure falling away to the void -
#: which is what `isthmus.py` already builds on the island. Measured before this: the two reaches
#: were 35% and 20% covered with eighty blocks of dead depth between the setpiece and the rim.
REACH_RIM_FROM = 96
REACHES = {"frontier_reach", "prism_reach"}
#: the park's own outer public edge, inboard of the V12 spine
EDGE_FROM, EDGE_TO = 4, 9


def _region_of(plan: dict, z: int) -> str:
    for region in plan.get("regions", []):
        x0, z0, x1, z1 = region["bounds"]
        if z0 <= z <= z1:
            return region["name"]
    return "midway"


def _perpendicular(courses, index) -> list[tuple[int, int]]:
    """The unit normal(s) to a route's own direction of travel at one course cell.

    At a corner the two segments disagree, so BOTH normals are returned and the corner gets its
    edge on both - which is what a real turn in a path looks like, and what stops a kerb ending
    a block short every time a route bends.
    """
    out = []
    for a, b in ((index - 1, index), (index, index + 1)):
        if a < 0 or b >= len(courses):
            continue
        dx, dz = courses[b][0] - courses[a][0], courses[b][2] - courses[a][2]
        normal = (0, 1) if dx else (1, 0) if dz else None
        if normal and normal not in out:
            out.append(normal)
    return out or [(0, 1)]


def infrastructure(plan: dict) -> SparseWorld:
    """Render platform, decks, kerbs, rails, rim and lighting from a compiled WorldSpec."""
    world = SparseWorld(chunk_size=int(plan.get("world_rules", {}).get("chunk_size", 16)))
    plane = int(plan["site"]["build_plane"])
    palette = {name: PALETTES.get(name, DEFAULT) for name in
               [r["name"] for r in plan.get("regions", [])] or ["midway"]}
    deck_cells: set[tuple[int, int]] = set()

    for route in plan.get("routes", []):
        service = route.get("kind") == "service"
        geometry = route.get("geometry")
        if geometry:
            deck, courses, supports = geometry["deck_cells"], geometry["courses"], geometry["supports"]
        else:
            deck = [[x, plane, z] for x, z in route["footprint"]]
            courses = [[x, plane, z] for x, z in route["cells"]]
            supports = []
        bridge = route["kind"] == "bridge"
        for x, y, z in deck:
            pal = palette.get(_region_of(plan, z), DEFAULT)
            world.put(x, y, z, pal["kerb"] if bridge else pal["deck"])
            # PLATFORM: paving over open void is a floating ribbon. One course of structure
            # under every public deck is what makes the park stand on something.
            world.put(x, y - 1, z, pal["platform"])
            if not service:
                deck_cells.add((x, z))
        for x, y, z in supports:
            pal = palette.get(_region_of(plan, z), DEFAULT)
            for yy in range(plane, y):
                world.put(x, yy, z, pal["rim"])
        if service:
            continue

        half = int(route["width"]) // 2
        railed = bool(geometry and geometry.get("rail_required")) or bridge
        for index, (x, y, z) in enumerate(courses):
            pal = palette.get(_region_of(plan, z), DEFAULT)
            # THE KERB GOES ON THE ROUTE'S OWN PERPENDICULAR, not on a fixed axis. The park
            # spine runs along z, so its width is in x; every access spur runs along x, so its
            # width is in z. Offsetting always in z put this park's main spine's "edges" ahead
            # of and behind a walker, on the deck - and `deck_cells` then swallowed them, so the
            # spine simply had no edge and nothing said so.
            for dx, dz in _perpendicular(courses, index):
                for side in (-1, 1):
                    ex, ez = x + side * dx * (half + 1), z + side * dz * (half + 1)
                    # the edge course is what makes a route read as a built path rather than as
                    # a strip of floor - and it is where the furniture goes, so nothing else
                    # may stand in it.
                    if (ex, ez) not in deck_cells:
                        world.put(ex, y, ez, pal["kerb"])
                        # a kerb over open void is the same floating ribbon as a deck over one
                        world.put(ex, y - 1, ez, pal["platform"])
                    if railed:
                        world.put(ex, y + 1, ez, "minecraft:iron_bars")
                    if index % LIGHT_EVERY == 0 and (ex, ez) not in deck_cells:
                        world.put(ex, y + 1, ez, pal["post"])
                        world.put(ex, y + 2, ez, pal["light"])

    # THE PROTECTED RIM IS A BAND, NOT A LINE. V170-199 is "support, terrain, void safety,
    # sightline protection" - thirty of every land's two hundred depth, and it was a single course
    # at V170, so fifteen percent of the park was measured as empty in every land. What belongs
    # there is not buildings: it is the edge the park stands on. A stepped batter falls away from
    # the inner face toward the void, buttressed at an interval, with a coping and a rail on the
    # face a guest can actually see. That is terrain and structure, and it leaves the void view.
    x0, z0, x1, z1 = plan["site"]["bounds"]
    for z in range(z0, z1 + 1):
        region = _region_of(plan, z)
        pal = palette.get(region, DEFAULT)
        rim_from = REACH_RIM_FROM if region in REACHES else RIM_FROM
        world.put(rim_from, plane, z, pal["rim"])
        world.put(rim_from, plane - 1, z, pal["platform"])
        if z % RIM_EVERY == 0:
            world.put(rim_from, plane + 1, z, pal["post"])
        # the batter: each step out toward the void drops a course, so the rim reads as the edge
        # of something built rather than as a wall standing on nothing.
        for step in range(1, x1 - rim_from + 1):
            x = rim_from + step
            if x > x1:
                break
            drop = step // RIM_STEP
            world.put(x, plane - drop, z, pal["batter"])
            # buttresses at an interval, carried down far enough to read as support from below
            if z % RIM_BUTTRESS == 0 and step % 3 == 0:
                for y in range(plane - drop - 1, plane - drop - 4, -1):
                    world.put(x, y, z, pal["rim"])

    # AND THE OUTER THRESHOLD EDGE. V0-9 was empty in every land too: the spine runs at V12 and
    # nothing lay between it and the park's own public boundary, so the park had no front edge at
    # all. A coping course and a rail is what a threshold looks like from outside it.
    for z in range(z0, z1 + 1):
        pal = palette.get(_region_of(plan, z), DEFAULT)
        for x in range(EDGE_FROM, EDGE_TO + 1):
            world.put(x, plane - 1, z, pal["platform"])
            world.put(x, plane, z, pal["deck"] if x >= EDGE_TO - 2 else pal["batter"])
        world.put(EDGE_FROM, plane + 1, z, pal["kerb"])
        if z % RIM_EVERY == 0:
            world.put(EDGE_FROM, plane + 2, z, pal["post"])

    return world
