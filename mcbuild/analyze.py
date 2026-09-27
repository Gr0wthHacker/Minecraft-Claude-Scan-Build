"""Which materials a build can actually USE right now, and where.

Jack: *"analyze schematics automatically, identify most used materials, and most placeable based
on no air blocks around it based on currently placed, so we can efficiently spread resources in
large builds."*

A bill of materials says what a design is MADE of. On a build the size of the park that is the
wrong question for a trip: a pack of the commonest block is a pack of blocks with nothing to place
them against, if the commonest block is the roof. The question a trip should ask is which material
has the most cells that can go in TODAY - a remaining cell with at least one solid face-neighbour
standing in the world - and, one step further, which material's placement UNLOCKS the most cells
that cannot go in yet. Ranked that way the pack fills with what the build can take, and the walls
go up before anyone fetches a roof.

    python -m mcbuild analyze "Park Complete" --world newisle          # the table
    python -m mcbuild analyze "Park Complete" --world newisle --have   # ...against your chests

`placeable` counts a remaining cell with a CLICKABLE face-neighbour in the CAPTURE; the in-game
`/cscan analyze` asks the live world the same question through `Work.placeableNow`, whose rule
is the printer's own (`Printer.support`: not air, not replaceable, blocks motion). Clickable is
that rule by name: a slab, a stair, a wall or a chest is a face to place against; a vine, a
tuft of grass, a torch, a carpet, a rail or water is not. The friend island's platform is all
top slabs, and a rule that only counted full cubes called every one of its stairs unplaceable.
"""
from __future__ import annotations
import collections
from dataclasses import dataclass, field
from . import coop, scan
from .audit import GROUND_PLANTS
from .blocks import AIRY

FACES = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


_NOT_CLICKABLE = {"vine", "water", "lava", "snow", "redstone_wire", "tripwire", "ladder", "repeater",
                  "comparator", "lever", "scaffolding", "moss_carpet", "lily_pad", "sea_pickle", "kelp",
                  "seagrass", "tall_seagrass", "glow_lichen", "sculk_vein", "cave_vines", "cave_vines_plant",
                  # ...and `torch` itself, which `endswith("_torch")` does not catch - the commonest
                  # light in the game read as a face to build on.
                  "torch"}
_NOT_CLICKABLE_SUFFIX = ("_torch", "_button", "_pressure_plate", "rail", "_sign", "_carpet", "_banner",
                         "_sapling", "_propagule", "_bush", "_fungus", "_roots", "_flower", "_tulip")

#: `Storage.CONTAINERS`, matched as a SUBSTRING exactly as the mod matches it - so `white_shulker_box`
#: and `trapped_chest` are covered by `shulker_box` and `chest`. A right-click on one of these OPENS
#: it; nothing is placed.
_CONTAINERS = ("chest", "barrel", "shulker_box", "hopper", "dispenser", "dropper", "furnace",
               "blast_furnace", "smoker", "brewing_stand", "chiseled_bookshelf", "decorated_pot",
               "crafter", "campfire", "lectern", "beacon", "cartography_table", "loom",
               "smithing_table", "grindstone", "stonecutter", "enchanting_table", "anvil",
               "crafting_table")

#: `Printer.toggles` - blocks whose own `use()` runs FIRST, so a right-click cycles a repeater,
#: feeds a composter or rings a bell and places nothing.
_TOGGLES = {"repeater", "comparator", "daylight_detector", "composter", "bell", "flower_pot",
            "target", "lectern", "dragon_egg", "respawn_anchor", "beehive", "bee_nest", "tnt",
            "chiseled_bookshelf", "decorated_pot", "note_block", "jukebox"}
_TOGGLE_SUFFIX = ("cake", "cauldron", "candle", "redstone_ore", "sign")
#: ...and the families `Printer.support` names outright.
_USE_SUFFIX = ("_door", "_trapdoor", "_fence_gate", "_button", "_bed")


def clickable(name: str) -> bool:
    """A face to place against: `Printer.support`, ported rather than paraphrased.

    THE TWO WERE A HAND-WRITTEN LIST EACH AND HAD DRIFTED. This said yes to every chest, barrel,
    furnace, hopper, door, trapdoor, fence gate, bed, note block, jukebox, cauldron, lectern, bell
    and flower pot in the game - all of which the printer refuses, because a right-click USES them.
    That is not a reporting nicety: `printable.closure` chains print-reachability through this, and
    `printable.stitch_model` WRITES THE RESULT into the shipped composite, so every false yes is an
    orphan mass reported as reachable and left unstitched. Rule 11, across a language boundary, in
    the one pass that edits an artifact.
    """
    if name in AIRY or name == "OOB" or name in GROUND_PLANTS or name in _NOT_CLICKABLE:
        return False
    if name in _TOGGLES or name.endswith(_TOGGLE_SUFFIX) or name.endswith(_USE_SUFFIX):
        return False
    if name == "lever" or any(c in name for c in _CONTAINERS):
        return False
    return not name.endswith(_NOT_CLICKABLE_SUFFIX)


def item_of(state: str) -> str:
    """`stone_brick_stairs[facing=east,half=top]` -> `stone_brick_stairs`; namespaced or not."""
    n = state.split("[", 1)[0]
    return n.split(":")[-1]


@dataclass
class Material:
    item: str
    total: int = 0          # cells of it in the design
    built: int = 0
    remaining: int = 0
    placeable: int = 0      # remaining cells with a solid neighbour standing in the world
    unlocks: int = 0        # remaining cells of ANY material that a placeable cell of this one would give a face
    where: tuple | None = None   # the (x, z) 16-region holding the most placeable cells
    where_n: int = 0

    @property
    def stacks(self) -> int:
        return (self.remaining + 63) // 64


@dataclass
class Analysis:
    design: str
    total: int = 0
    built: int = 0
    remaining: int = 0
    placeable: int = 0
    materials: dict = field(default_factory=dict)

    def ranked(self) -> list[Material]:
        """Most PLACEABLE first, then most unlocking, then most remaining - the order a trip wants."""
        return sorted(self.materials.values(), key=lambda m: (-m.placeable, -m.unlocks, -m.remaining, m.item))


def analyze(design: str, world: str, *, loose_rock: bool = True) -> Analysis:
    d = coop.Grid(scan.load(design))
    w = coop.Grid(scan.load(world))
    p = coop.progress(design, world, loose_rock=loose_rock)
    a = Analysis(design=p.design, total=p.total, built=p.built)
    mats: dict[str, Material] = {}
    for _pos, want in d.cells():
        m = mats.setdefault(item_of(want), Material(item_of(want)))
        m.total += 1
    remaining = {pos: item_of(want) for pos, want in p.remaining_cells}
    placeable_at: dict[tuple, str] = {}
    region_counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for (x, y, z), item in remaining.items():
        m = mats[item]
        m.remaining += 1
        if any(clickable(w.name(x + dx, y + dy, z + dz)) for dx, dy, dz in FACES):
            m.placeable += 1
            placeable_at[(x, y, z)] = item
            region_counts[item][(x // 16 * 16, z // 16 * 16)] += 1
    # ONE STEP OF UNLOCKING: a cell that cannot go in yet, next to a cell that can. Credited to the
    # material of the cell that would give it a face; a cell touching two counts for both, because
    # either trip would open it.
    for (x, y, z), item in remaining.items():
        if (x, y, z) in placeable_at:
            continue
        credited = set()
        for dx, dy, dz in FACES:
            n = placeable_at.get((x + dx, y + dy, z + dz))
            if n is not None:
                credited.add(n)
        for n in credited:
            mats[n].unlocks += 1
    for m in mats.values():
        m.built = m.total - m.remaining
        if region_counts.get(m.item):
            m.where, m.where_n = region_counts[m.item].most_common(1)[0]
    a.remaining = sum(m.remaining for m in mats.values())
    a.placeable = sum(m.placeable for m in mats.values())
    a.materials = mats
    return a


def render(a: Analysis, have: collections.Counter | None = None, top: int = 15) -> str:
    lines = [f"{a.design}: {a.built}/{a.total} built, {a.remaining} left, "
             f"{a.placeable} of those placeable against what stands today"]
    head = f"{'material':26s} {'placeable':>9s} {'unlocks':>7s} {'left':>7s} {'stacks':>6s}"
    if have is not None:
        head += f" {'have':>7s} {'short':>7s}"
    head += "   where (x,z region)"
    lines.append(head)
    for m in a.ranked()[:top]:
        row = f"{m.item:26s} {m.placeable:9d} {m.unlocks:7d} {m.remaining:7d} {m.stacks:6d}"
        if have is not None:
            got = have.get(m.item, 0)
            row += f" {got:7d} {max(0, m.remaining - got):7d}"
        if m.where is not None:
            row += f"   ({m.where[0]},{m.where[1]}) x{m.where_n}"
        lines.append(row)
    blocked = [m for m in a.materials.values() if m.remaining and not m.placeable]
    if blocked:
        lines.append("nothing to place against yet: " + ", ".join(
            f"{m.item}:{m.remaining}" for m in sorted(blocked, key=lambda m: -m.remaining)[:8]))
    lines.append("fill the pack top-down: a trip for the first row places the most and opens the most.")
    return "\n".join(lines)
