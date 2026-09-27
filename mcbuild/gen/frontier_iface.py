"""TYPED INTERFACES FOR THE FRONTIER — the anchors a module declares, and what may link to what.

`PARK_OVERHAUL.md` makes the interface schema a promotion gate rather than documentation: *"A plan
cannot be prepared or promoted when a public module has empty anchors."* Every frontier module
therefore declares its own `approach`, `queue_entry`, `boarding`, `ride_exit`, `emergency_exit`,
`service_access` and so on, in the format `design_compiler.anchors()` already parses.

**AN ANCHOR IS LOCAL, AND THAT IS THE ONLY REASON THIS COMPOSES.** `design_compiler.world_anchors`
adds a module's `at` to every anchor position, so a generator that emitted world coordinates would
have them added to `at` a second time and every link in the park would be checked against a point
in the void. Generators here work in world space through `_Frame.at`, so `local()` is the one place
that subtraction happens.

**THE SCHEMA'S NAMES ARE THE BRIEF'S; THE SCHEMA'S KINDS ARE THE COMPILER'S.** `ANCHOR_KINDS` in
`design_compiler.py` is a shared, frozen vocabulary — `entry`, `queue`, `board`, `ride_exit`,
`maintenance`, `visual_front`, `path` — and the brief's names (`service_access`, `frontage`,
`boarding`) are ROLES, not kinds. `ROLE_KIND` below is the mapping, written down once, because a
generator that invents a kind gets a `ValueError` from a shared file it does not own.

WHY THE REQUIREMENTS LIVE HERE RATHER THAN IN A TEST. A test that lists the required anchors is a
second copy of the table in `PARK_OVERHAUL.md`, and the two drift the moment a module type is
added. `REQUIRED` is the single source: the generators build to it and the tests grade against it.
"""
from __future__ import annotations

from ..design_compiler import ANCHOR_KINDS, anchors as parse_anchors, compatible

# The brief's role names -> the compiler's frozen anchor kinds. A role with no mapping is a role
# nobody can link, so `anchor()` refuses it rather than inventing a kind.
ROLE_KIND = {
    # arrival / gate
    "arrival": "path", "public_entry": "entry", "public_exit": "exit", "map_view": "visual_front",
    # rides
    "approach": "path", "queue_entry": "queue", "queue_merge": "queue", "boarding": "board",
    "ride_entry": "entry", "ride_exit": "ride_exit", "emergency_exit": "exit",
    "service_access": "maintenance", "maintenance_access": "maintenance",
    "viewpoint": "visual_front",
    # walkthrough / puzzle
    "entry": "entry", "exit": "exit", "reward": "redstone_output",
    # food / retail / games
    "frontage": "visual_front", "customer_entry": "entry",
    "collection_or_exit": "exit", "collection": "exit",
    # landmark
    "view_approach": "path", "interior_entry": "entry",
    # machinery
    "input": "redstone_input", "output": "redstone_output",
    # paths
    "main_spine": "path", "secondary": "path", "queue": "queue", "service": "maintenance",
    "return_spine": "path", "arrival_spine": "path", "town_square": "path",
    "mine_loop": "path", "canyon_loop": "path",
}

# PARK_OVERHAUL.md's "Required interface schema" table, plus PARK_FRONTIER.md's own additions
# ("All public modules declare public_entry, public_exit, frontage, and service_access. Rides also
# declare queue_entry, queue_merge, boarding, ride_exit, emergency_exit, maintenance_access, and
# viewpoint.")
PUBLIC = ("public_entry", "public_exit", "frontage", "service_access")
REQUIRED = {
    "gate": ("arrival", "public_entry", "public_exit", "map_view"),
    "ride": PUBLIC + ("approach", "queue_entry", "queue_merge", "boarding", "ride_exit",
                      "emergency_exit", "maintenance_access", "viewpoint"),
    "walkthrough": PUBLIC + ("approach", "entry", "exit"),
    "shop": PUBLIC + ("customer_entry", "queue_entry", "collection_or_exit"),
    "landmark": PUBLIC + ("view_approach", "interior_entry"),
    "path": ("main_spine", "return_spine"),
}

# WIDTHS ARE THE CAPACITY RULE, NOT DECORATION. Rule 6: a 5-block main public spine, 3-block
# secondary circulation, 2-3-block queues, distinct exits. `design_compiler.compatible` refuses a
# link whose two ends disagree on width, so declaring these is what makes a 5-wide spine meeting a
# 1-wide door a checkable error rather than a judgement call.
SPINE_W, SECONDARY_W, QUEUE_W, EXIT_W = 5, 3, 3, 3


def local(f, i: int, d: int, h: int) -> tuple[int, int, int]:
    """A building-axis cell as a MODULE-LOCAL offset, which is what an anchor position must be."""
    x, y, z = f.at(i, d, h)
    return (x - f.x, y - f.y, z - f.z)


def anchor(f, name: str, role: str, i: int, d: int, h: int, *, facing=None, width: int = 1) -> dict:
    """One typed anchor, in the format `design_compiler.anchors()` parses.

    `role` is the brief's word; the compiler's `kind` is derived. An unmapped role raises HERE,
    where the caller can see which module asked for it, rather than deep inside a shared parser.
    """
    if role not in ROLE_KIND:
        raise ValueError(f"unknown frontier anchor role {role!r}; have {sorted(ROLE_KIND)}")
    kind = ROLE_KIND[role]
    if kind not in ANCHOR_KINDS:                     # belt and braces: the shared set may move
        raise ValueError(f"role {role!r} maps to {kind!r}, which is not a design_compiler kind")
    return {"name": name, "kind": kind, "role": role, "position": list(local(f, i, d, h)),
            **({"facing": facing} if facing else {}), "width": int(width)}


def missing(kind_type: str, declared) -> list[str]:
    """Which required anchors a module has NOT declared. Empty is the only passing answer."""
    if kind_type not in REQUIRED:
        raise ValueError(f"unknown module type {kind_type!r}; have {sorted(REQUIRED)}")
    have = {a.get("name") for a in (declared or [])} | {a.get("role") for a in (declared or [])}
    return [r for r in REQUIRED[kind_type] if r not in have]


def validate(declared) -> list:
    """Parse through the shared compiler, so a malformed anchor fails here and not at assembly."""
    return parse_anchors([{k: v for k, v in a.items() if k != "role"} for a in declared or []])


def linkable(left: dict, right: dict) -> bool:
    """Would the compiler accept a link between these two declarations?"""
    a, b = validate([left]), validate([right])
    return compatible(a[0], b[0])
