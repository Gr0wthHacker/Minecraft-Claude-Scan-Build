"""Minecraft Java 1.19 mechanics used by generated schematics.

This is deliberately a capability registry, not a second block database.  The block database says
whether a state is legal; this module says which *game system* a placed block participates in and
which local verifier owns that system.  The manifest is written into every generated sidecar so a
design can be reviewed as a composition of real mechanics rather than a bag of block names.
"""
from __future__ import annotations

from collections import defaultdict

from . import blocks

JAVA_VERSION = "1.19"

# `blocks.kind` comes from Mojang's registry data.  Keeping the mapping in terms of kinds means
# every wood species of door, sign, button, pressure plate, etc. is covered without a growing
# handwritten block-name list.
FAMILIES = {
    "redstone": {
        "redstone_wire", "repeater", "comparator", "observer", "piston_base", "piston_head",
        "redstone_block", "redstone_torch", "lever", "button", "pressure_plate",
        "weighted_pressure_plate", "target", "sculk_sensor", "daylight_detector", "trip_wire_hook",
        "tripwire", "trapped_chest", "detector_rail", "dispenser", "dropper", "note_block", "tnt",
    },
    "rail": {"rail", "powered_rail", "detector_rail", "activator_rail"},
    "fluid": {"liquid", "waterlogged"},
    "traversal": {"ladder", "vine", "scaffolding", "bubble_column"},
    "access": {"door", "trapdoor", "fence_gate"},
    "container": {"chest", "barrel", "hopper", "beehive", "shulker_box", "dispenser", "dropper"},
    "light": {"lantern", "torch", "light", "glowstone", "sea_lantern", "froglight"},
    "hazard": {"liquid", "fire", "soul_fire", "campfire", "tnt", "cactus", "magma_block"},
    "signage": {"standing_sign", "wall_sign", "ceiling_hanging_sign", "wall_hanging_sign"},
}

# A few blocks deliberately use a shared physical kind even though their game behaviour differs.
# Keep those exceptions explicit.  A trapped chest is physically a chest but emits a redstone
# signal; a redstone lamp is physically a light but is also a signal-driven output.
NAME_FAMILIES = {
    "trapped_chest": {"redstone"},
    "redstone_lamp": {"redstone", "light"},
}

VERIFIERS = {
    "redstone": "mcbuild.circuit",
    "rail": "mcbuild.circuit + rail contract tests",
    "fluid": "mcbuild.fluids",
    "traversal": "mcbuild.walk / audit.check_climb",
    "access": "mcbuild.walk + generator route contracts",
    "container": "mcbuild.circuit inputs or operator-stocked metadata",
    "light": "mcbuild.nightlight",
    "hazard": "mcbuild.audit + generator safety contracts",
    "signage": "mcbuild.audit support/state checks",
}

# These are build-purpose contracts, not block claims. A bridge generator has a continuity and
# clearance obligation even when it contains no special mechanics; a sculpture's concerns are
# silhouette, support and palette rather than a fictional redstone system. Configs may add roles
# under top-level ``roles``; generator inference keeps the existing corpus self-describing.
ROLE_GENERATORS = {
    "bridge": {"voidbridge", "isthmus", "ruinway", "rootreach"},
    "path": {"pathkit", "paths", "wayfinding", "arrival", "transit", "streetfurniture"},
    "sculpture": {
        "fox", "sloth", "gecko", "dragonfly", "quadruped", "heron", "bat", "ladybug",
        "axolotl", "turtle", "frog", "monument", "spectacle",
    },
    "ride": {"coaster", "bigwheel", "attractions", "parkour", "railspiral"},
    "building": {
        "tower", "storehall", "atelier", "vestibule", "courthall", "sanctum", "hamlet",
        "campanile", "casino", "civic", "frontiertown", "hollowmanor", "arcade", "ticketing",
        "park_entrance",
    },
    "landscape": {
        "tree", "underside", "garden", "pond", "islet", "lake", "voidisle", "lowland",
        "falls", "thicket", "enrich", "park", "harborlight", "lowglow",
    },
}

ROLE_CONTRACTS = {
    "construction": "legal states, supported placements, stable components, and an auditable bill of materials",
    "bridge": "continuous walking deck, safe edge/clearance, and anchored supports",
    "path": "continuous traversable route with supported furnishings and deliberate access",
    "sculpture": "connected, supported silhouette with deliberate material hierarchy",
    "ride": "route/rail topology plus reachable boarding, exit, and safety paths",
    "building": "legal states, supported attachments, accessible entries, and interior clearance",
    "landscape": "legal fluid/plant placement, stable terrain contacts, and walkable intended routes",
}


def _name(full: str) -> str:
    return full.split(":", 1)[-1].split("[", 1)[0]


def _kind(name: str) -> str:
    try:
        return blocks.kind(name)
    except (KeyError, TypeError):
        return ""


def _roles(generator: str | None, declared) -> list[str]:
    """Return recognised build-purpose roles from the generator and optional config tags."""
    requested = set(declared or ())
    if generator:
        requested.update(role for role, generators in ROLE_GENERATORS.items() if generator in generators)
        # Every public generator is covered by the universal construction contract. More specific
        # roles above add route, silhouette, terrain, or ride requirements where they apply.
        requested.add("construction")
    unknown = requested - set(ROLE_CONTRACTS)
    if unknown:
        raise ValueError(f"unknown mechanics role(s): {', '.join(sorted(unknown))}")
    return sorted(requested)


def manifest(model, *, generator: str | None = None, roles=None) -> dict:
    """Return the mechanics a model actually uses, grouped by capability family.

    A family is included only when it has a placed block.  This keeps a sidecar honest: an
    architectural generator does not claim a redstone contract merely because the toolkit supports
    redstone, while a design with a detector rail cannot hide that it is a rail mechanism.
    """
    names = {_name(n) for n in model.names if _name(n) not in {"air", "cave_air", "void_air"}}
    by_family = defaultdict(list)
    for name in sorted(names):
        kind = _kind(name)
        for family, kinds in FAMILIES.items():
            if kind in kinds:
                by_family[family].append(name)
        for family in NAME_FAMILIES.get(name, ()):
            by_family[family].append(name)
    families = {family: sorted(set(used)) for family, used in sorted(by_family.items())}
    build_roles = _roles(generator, roles)
    return {
        "minecraft": f"java-{JAVA_VERSION}",
        "families": families,
        "verifiers": {family: VERIFIERS[family] for family in families},
        "roles": build_roles,
        "role_contracts": {role: ROLE_CONTRACTS[role] for role in build_roles},
    }
