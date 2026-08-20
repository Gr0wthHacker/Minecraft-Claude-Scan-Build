"""What a generator must never write over, no matter how plain it looks.

This exists because of a specific mistake. `rootbreak` listed `gray_wool` and `black_wool` as
breakable - they were in the deck's ceiling, they looked like decoration, and they are in fact the
SOUND DAMPENING round the shulker/piston entrance into the tree. The root heaved 57 cells of it.

The lesson generalises past wool: a block that looks like fabric may be a machine's silencer, a
wool block may be a piston's sound baffle, a random stone slab may be a redstone timing floor. A
generator cannot tell by looking, so the safe set is stated once, here, and every generator that
writes into a lived-in world consults it. Anything added to a whitelist elsewhere still has to
clear this.

If a design genuinely must touch one of these, it should say so explicitly and loudly in its
config - never by widening the list.
"""
from __future__ import annotations

# Redstone, storage, and anything a contraption is built from or quietened with.
MECHANISM = (
    # sound dampening and signal-carrying fabric
    "wool", "carpet",
    # redstone proper
    "redstone", "repeater", "comparator", "observer", "piston", "piston_head", "moving_piston",
    "lever", "button", "pressure_plate", "tripwire", "tripwire_hook", "string", "target",
    "note_block", "daylight_detector", "sculk_sensor", "calibrated_sculk_sensor",
    "slime_block", "honey_block", "dispenser", "dropper", "hopper", "hopper_minecart",
    "redstone_lamp", "redstone_torch", "redstone_block", "redstone_wire", "lectern",
    # containers and machines
    "chest", "trapped_chest", "barrel", "shulker_box", "furnace", "blast_furnace", "smoker",
    "brewing_stand", "enchanting_table", "anvil", "grindstone", "smithing_table", "stonecutter",
    "loom", "cartography_table", "fletching_table", "composter", "cauldron", "beacon",
    "crafting_table", "jukebox", "bell", "campfire", "beehive", "bee_nest", "spawner",
    # transport
    "rail", "minecart", "ladder", "scaffolding",
    # doors and anything a mechanism moves
    "_door", "trapdoor", "fence_gate", "iron_bars",
    # signs and banners carry information someone wrote
    "sign", "banner",
    # fluids and the farm blocks a fluid feeds
    "water", "lava", "ice", "farmland", "sugar_cane", "bamboo", "wheat", "carrots", "potatoes",
    "beetroots", "nether_wart", "cocoa", "sweet_berry_bush", "kelp",
    # light a player placed deliberately
    "lantern", "soul_lantern", "torch", "wall_torch", "soul_torch", "end_rod", "glowstone",
    "sea_lantern", "shroomlight", "froglight", "candle", "glow_lichen", "amethyst",
)


def is_protected(name: str) -> bool:
    """`name` may carry a namespace and a state; both are stripped before matching."""
    n = name.split(":")[-1].split("[")[0]
    return any(k in n for k in MECHANISM)


# Things a player stands at and uses. Rule 10: leave working room round them - you need to stand,
# open the thing and walk past. Paving the FLOOR beside a chest is fine; putting a balustrade,
# a cornice or a pier there is not, and the entrance did that to 24 cells before this existed.
USED = ("chest", "trapped_chest", "barrel", "shulker_box", "furnace", "blast_furnace", "smoker",
        "hopper", "dispenser", "dropper", "crafting_table", "anvil", "grindstone", "loom",
        "stonecutter", "smithing_table", "cartography_table", "fletching_table", "brewing_stand",
        "enchanting_table", "composter", "cauldron", "lectern", "beacon", "lever", "button",
        "bed", "jukebox", "note_block")


def is_used(name: str) -> bool:
    n = name.split(":")[-1].split("[")[0]
    return any(k in n for k in USED)

