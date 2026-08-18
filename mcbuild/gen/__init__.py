"""Generator registry. Each module exposes DEFAULTS and build(cfg, donors)->Canvas."""
from . import tree, fox, tower, underside, garden, pond, casing, farm, pathkit, sloth, gecko, dragonfly, belly, vertical, dressing, interior, courtyard, redstone, islet, spiral, stairwell, storehall, atelier
from .canvas import Canvas, hash01

class _Wrap:
    """Adapt a plain build function to the generator-module protocol."""
    def __init__(self, fn, defaults):
        self.build = fn; self.DEFAULTS = defaults


GENERATORS = {
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
    "storehall": _Wrap(storehall.build_storehall, storehall.STOREHALL),
    "atelier": _Wrap(atelier.build_atelier, atelier.ATELIER),
}

__all__ = ["GENERATORS", "Canvas", "hash01"]
