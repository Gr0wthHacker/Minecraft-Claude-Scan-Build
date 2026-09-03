"""Generator registry. Each module exposes DEFAULTS and build(cfg, donors)->Canvas."""
from . import asset, parkways, parkrail, tree, fox, tower, underside, garden, pond, casing, farm, pathkit, sloth, gecko, dragonfly, belly, vertical, dressing, interior, courtyard, redstone, islet, spiral, stairwell, storehall, atelier, lake, voidisle, vestibule, quadruped, lowland, heron, bat, ladybug, stairhead, deckfloor, gallery, rootbreak, rimstair, courthall, ruinring, axolotl, ruinway, sanctum, voidbridge, hamlet, campanile, harborlight, turtle, rootreach, lowglow, falls, thicket, enrich, parkour, frog, railspiral, casino, park, coaster, bigwheel, civic, frontiertown, hollowmanor, monument, streetfurniture, attractions, transit, ticketing, wayfinding, isthmus, spectacle, arcade, arrival, balloon, wyrm, undercroft, setpiece, prismworks, prismwell, prismfloor
from .canvas import Canvas, hash01

class _Compose:
    """Lazy adapter: mcbuild.compose imports the registry, so bind it at call time."""
    DEFAULTS = {"parts": None}

    def build(self, cfg, donors=None):
        from ..compose import build as compose_build
        return compose_build(cfg, donors)


class _Wrap:
    """Adapt a plain build function to the generator-module protocol."""
    def __init__(self, fn, defaults):
        self.build = fn; self.DEFAULTS = defaults


from . import frontier_builds, midway_builds, prismworks_builds  # noqa: E402
from . import minestation  # noqa: E402
from . import park_entrance, park_frontage, park_vantage, park_water  # noqa: E402
from . import claimrow, diggings, fossils, frontier_scatter, mineridge  # noqa: E402
from . import mineworks, park_games, plateau, pterosaur, sauropod, seam  # noqa: E402
from . import wyrmgate  # noqa: E402
from . import menagerie  # noqa: E402


GENERATORS = {
    "asset": asset,
    "parkways": parkways,
    "parkrail": parkrail,
    # the park's three lands, one generator module each - written by a stream
    # per land, on lots that are geometrically disjoint.
    "frontier_builds": frontier_builds,
    "midwaybuild": midway_builds,
    "prismworks_builds": prismworks_builds,
    # the lake and the water garden - see mcbuild/gen/park_water.py
    "park_water": park_water,
    # the three climbable high points - see mcbuild/gen/park_vantage.py
    "park_vantage": park_vantage,
    # marquees, portals, queues, props - mcbuild/gen/park_frontage.py
    # the Mine Coaster's own artifact, adopted and edited - mcbuild/gen/minestation.py
    "minestation": minestation,
    "park_frontage": park_frontage,
    "park_entrance": park_entrance,
    # the mountain the Mine Coaster is cut into, and the works that feed it -
    # mcbuild/gen/mineridge.py and mcbuild/gen/mineworks.py
    "mineridge": mineridge,
    "mineworks": mineworks,
    # the land dressing: pines, snags, boulders and mine debris on the open lawn -
    # mcbuild/gen/frontier_scatter.py. NOT ONE BUILDING in it, deliberately.
    "frontier_scatter": frontier_scatter,
    # the bone skull straddling the rim railway, mouth open around the track -
    # mcbuild/gen/wyrmgate.py. It touches NOTHING the railway made and is carried
    # from the rim, because the jaw is exactly as deep as the corridor is wide.
    "wyrmgate": wyrmgate,
    # the worked-out landscape that replaced Boomtown's seven false fronts, with two
    # shops cut INTO its banks - mcbuild/gen/diggings.py
    "diggings": diggings,
    # THE GROUND THE MODULES NEVER BUILT. Frontier column A is 54% bare moss and the two biggest
    # holes are INSIDE its lots: the Trailhead Gate's walled court has an empty middle and the
    # Prospecting Porch is a strip on one flank with twenty columns of unbuilt back. The scatter
    # keeps out of module lots (rightly - a material test cannot tell its pine from the
    # Diggings'), so that ground belonged to nobody. `kind: claims` works it; `kind: yard` gives
    # the gate the paved route through it that a threshold has to have -
    # mcbuild/gen/claimrow.py
    "claimrow": claimrow,
    # THE SEAM. Measured over the shipped park, Prismworks carries 3.0% of its columns in the
    # 3-11 course band against the Frontier's 19.5%, and the Prism Reach 3.4% with NOTHING at
    # all above 12 - so the well's tower reads as an object dropped on a lawn rather than the
    # thing a place is built around. This is the crystal vein the well was cut to reach,
    # breaking the surface: `fracture` in the reach, `yard` behind the Foundry Gate, `field`
    # east of the mouth. mcbuild/gen/seam.py
    "seam": seam,
    # THE LOST PLATEAU. Measured, the Frontier used show material at 1.3% against 21-32% for every
    # other land in the park - the biggest land, the most verbs, and no identity at all, because a
    # gold-rush mining camp IS timber and stone and cannot be fixed by adding colour. This dresses
    # the Mine Ridge - 8,804 columns, 5,776 of them standing at Y206+ and the biggest grey object
    # in the park - as jungle, ADDITIVELY, so the coaster and the mountain are untouched.
    # mcbuild/gen/plateau.py
    "plateau": plateau,
    # THE LOST PLATEAU'S LANDMARK, and the one big animal this system is good at: a brachiosaur is
    # a neck on columnar legs, which is the giraffe - the only quadruped in this repo that works -
    # rather than the compound volumetric muscle that retired eight mammals.
    # mcbuild/gen/sauropod.py
    "sauropod": sauropod,
    # ...and the other half of the same rule: the sauropod is COLUMNS and this is the PLANE. A
    # pterosaur's identity is one membrane hung from one elongated finger, which is the shape this
    # medium renders best of anything - the sky bird and the bat are the two recorded successes.
    # mcbuild/gen/pterosaur.py
    "pterosaur": pterosaur,
    # **THE GAMES INSIDE THE PARK'S BUILDINGS, AND THIS ENTRY WAS MISSING.**
    # `mcbuild/gen/park_games.py`, `tests/test_park_games.py` and ten
    # `configs/pf_game_*.yaml` all existed and the generator was not registered, so
    # not one of those configs could be regenerated - `mcbuild gen` answered "unknown
    # generator park_games". Three of the built artifacts were also never placed. A
    # generator nobody can reach is indistinguishable from one nobody wrote.
    "park_games": park_games,
    "compose": _Compose(),
    "setpiece": setpiece,
    "prismworks": _Wrap(prismworks.build, prismworks.PRISMWORKS),
    "undercroft": undercroft,
    "arcade": arcade,
    "menagerie": menagerie,
    "balloon": balloon,
    "wyrm": wyrm,
    "arrival": arrival,
    "attractions": attractions,
    "ticketing": ticketing,
    "transit": transit,
    "isthmus": isthmus,
    "spectacle": spectacle,
    "casino": casino,
    "park": park,
    "wayfinding": wayfinding,
    "monument": monument,
    "streetfurniture": streetfurniture,
    "hollowmanor": hollowmanor,
    "frontiertown": frontiertown,
    "civic": civic,
    "bigwheel": bigwheel,
    "coaster": coaster,
    "tree": tree,
    "fox": fox,
    "tower": tower,
    "underside": underside,
    "belly": belly,
    "pond": pond,
    "casing": casing,
    "farm": farm,
    "pathkit": pathkit,
    "sloth": sloth,
    "gecko": gecko,
    "dragonfly": dragonfly,
    "bench": _Wrap(garden.build_bench, {}),
    "planter": _Wrap(garden.build_planter, {}),
    "well": _Wrap(garden.build_well, {}),
    "lamp": _Wrap(garden.build_lamp, {}),
    "scatter": _Wrap(garden.build_scatter, {}),
    "taproot": _Wrap(vertical.build_taproot, vertical.TAPROOT),
    "shard": _Wrap(vertical.build_shard, vertical.SHARD),
    "chimney": _Wrap(dressing.build_chimney, dressing.CHIMNEY),
    "footing": _Wrap(dressing.build_footing, dressing.FOOTING),
    "hem": _Wrap(dressing.build_hem, dressing.HEM),
    "paths": _Wrap(dressing.build_paths, dressing.PATHS),
    "lightposts": _Wrap(dressing.build_lightposts, dressing.LIGHTPOSTS),
    "entrance": _Wrap(dressing.build_entrance, dressing.ENTRANCE),
    "ridelights": _Wrap(dressing.build_ridelights, dressing.RIDELIGHTS),
    "apiary": _Wrap(dressing.build_apiary, dressing.APIARY),
    "birdlanterns": _Wrap(dressing.build_birdlanterns, dressing.BIRDLANTERNS),
    "altar": _Wrap(dressing.build_altar, dressing.ALTAR),
    "vault": _Wrap(interior.build_vault, interior.VAULT),
    "court": _Wrap(courtyard.build_court, courtyard.COURT),
    "sorter": _Wrap(redstone.build_sorter, redstone.SORTER),
    "islet": _Wrap(islet.build_islet, islet.ISLET),
    "spiral": _Wrap(spiral.build_spiral, spiral.SPIRAL),
    "stairwell": _Wrap(stairwell.build_stairwell, stairwell.STAIRWELL),
    "rimstair": _Wrap(rimstair.build_rimstair, rimstair.RIMSTAIR),
    "courthall": _Wrap(courthall.build_courthall, courthall.COURTHALL),
    "storehall": _Wrap(storehall.build_storehall, storehall.STOREHALL),
    "atelier": _Wrap(atelier.build_atelier, atelier.ATELIER),
    "lake": _Wrap(lake.build_lake, lake.LAKE),
    "voidisle": _Wrap(voidisle.build_voidisle, voidisle.VOIDISLE),
    "vestibule": _Wrap(vestibule.build_vestibule, vestibule.VESTIBULE),
    "quadruped": _Wrap(quadruped.build_quadruped, quadruped.QUADRUPED),
    "lowland": _Wrap(lowland.build_lowland, lowland.LOWLAND),
    "heron": _Wrap(heron.build_heron, heron.HERON),
    "bat": _Wrap(bat.build_bat, bat.BAT),
    "ladybug": _Wrap(ladybug.build_ladybug, ladybug.LADYBUG),
    "stairhead": _Wrap(stairhead.build_stairhead, stairhead.STAIRHEAD),
    "deckfloor": _Wrap(deckfloor.build_deckfloor, deckfloor.DECKFLOOR),
    "gallery": _Wrap(gallery.build_gallery, gallery.GALLERY),
    "rootbreak": _Wrap(rootbreak.build_rootbreak, rootbreak.ROOTBREAK),
    "ruinring": _Wrap(ruinring.build_ruinring, ruinring.RUINRING),
    "axolotl": _Wrap(axolotl.build_axolotl, axolotl.AXOLOTL),
    "ruinway": _Wrap(ruinway.build_ruinway, ruinway.RUINWAY),
    "sanctum": _Wrap(sanctum.build_sanctum, sanctum.SANCTUM),
    "voidbridge": _Wrap(voidbridge.build_voidbridge, voidbridge.RUINBRIDGE),
    "hamlet": _Wrap(hamlet.build_hamlet, hamlet.HAMLET),
    "campanile": _Wrap(campanile.build_campanile, campanile.CAMPANILE),
    "harborlight": _Wrap(harborlight.build_harborlight, harborlight.HARBORLIGHT),
    "turtle": _Wrap(turtle.build_turtle, turtle.TURTLE),
    "rootreach": _Wrap(rootreach.build_rootreach, rootreach.ROOTREACH),
    "lowglow": _Wrap(lowglow.build_lowglow, lowglow.LOWGLOW),
    "falls": _Wrap(falls.build_falls, falls.FALLS),
    "frog": _Wrap(frog.build_frog, frog.FROG),
    "thicket": _Wrap(thicket.build_thicket, thicket.THICKET),
    "enrich": _Wrap(enrich.build_enrich, enrich.ENRICH),
    "parkour": _Wrap(parkour.build_parkour, parkour.PARKOUR),
    "prismwell": _Wrap(prismwell.build_well, prismwell.WELL),
    "prismrig": _Wrap(prismwell.build_rig, prismwell.RIG),
    "prismfloor": _Wrap(prismfloor.build_floor, prismfloor.FLOOR),
    "railspiral": _Wrap(railspiral.build_railspiral, railspiral.RAILSPIRAL),
}

__all__ = ["GENERATORS", "Canvas", "hash01"]
