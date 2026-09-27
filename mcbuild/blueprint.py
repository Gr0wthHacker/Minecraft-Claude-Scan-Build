"""Program-driven building blueprints for believable Minecraft architecture.

Generators can consume the returned geometry directly, while planners and reviewers can use it
without creating a schematic.  The compiler deliberately owns functional relationships (rooms,
circulation, public/service interfaces and structural rhythm); themed generators retain ownership
of blocks, ornament, and interiors.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

from .grammar import facade_profile


PROGRAMS = {
    "shop": [("sales_floor", "public", 4), ("stockroom", "service", 3)],
    "restaurant": [("host", "public", 3), ("dining", "public", 6), ("kitchen", "service", 5),
                   ("storage", "service", 3)],
    "ride_station": [("queue", "public", 4), ("boarding", "public", 3), ("control", "service", 3),
                      ("exit", "public", 3)],
    "haunted_walkthrough": [("queue", "public", 4), ("pre_show", "public", 4), ("show", "public", 8),
                              ("exit", "public", 3), ("reset_corridor", "service", 3)],
    "hotel_lobby": [("lobby", "public", 7), ("check_in", "public", 3), ("lounge", "public", 4),
                     ("back_office", "service", 3)],
    "workshop": [("showroom", "public", 4), ("work_floor", "service", 7), ("loading", "service", 3)],
    "gallery": [("entry", "public", 3), ("exhibit", "public", 8), ("exit", "public", 3),
                ("collection_store", "service", 3)],
}
STYLES = {"frontier", "hollow", "midway", "civic", "industrial", "natural", "prismworks"}


@dataclass(frozen=True)
class Room:
    name: str
    access: str
    x: int
    z: int
    width: int
    depth: int


def _positive(spec: dict, key: str, minimum: int) -> int:
    value = int(spec.get(key, 0))
    if value < minimum:
        raise ValueError(f"{key} must be at least {minimum}")
    return value


def _program(kind: str, custom) -> list[tuple[str, str, int]]:
    if custom is not None:
        if not isinstance(custom, list) or not custom:
            raise ValueError("rooms must be a non-empty list")
        out = []
        for room in custom:
            if not isinstance(room, dict) or room.get("access") not in {"public", "service"}:
                raise ValueError("each room needs name and public/service access")
            name = room.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("each room needs a name")
            out.append((name, room["access"], int(room.get("min_depth", 3))))
        return out
    if kind not in PROGRAMS:
        raise ValueError(f"unknown building program {kind!r}; have {', '.join(sorted(PROGRAMS))}")
    return PROGRAMS[kind]


def compile(spec: dict) -> dict:
    """Compile a building brief into rooms, interfaces, roof/facade, and structural grid.

    Required brief fields: ``name``, ``program``, ``width``, ``depth``.  The result is deterministic
    and is intentionally block-agnostic so every themed generator can render it faithfully.
    """
    if not isinstance(spec, dict):
        raise ValueError("blueprint must be an object")
    name = spec.get("name")
    kind = spec.get("program")
    if not isinstance(name, str) or not name:
        raise ValueError("blueprint needs a non-empty name")
    if not isinstance(kind, str):
        raise ValueError("blueprint needs a program")
    width, depth = _positive(spec, "width", 7), _positive(spec, "depth", 8)
    floors = _positive(spec | {"floors": spec.get("floors", 1)}, "floors", 1)
    story_height = _positive(spec | {"story_height": spec.get("story_height", 5)}, "story_height", 4)
    style = spec.get("style", "civic")
    if style not in STYLES:
        raise ValueError(f"unknown style {style!r}")
    rooms_spec = _program(kind, spec.get("rooms"))
    # Allocate depth in strips.  This gives every room a true footprint, not a name-only program.
    required = sum(room[2] for room in rooms_spec)
    if required > depth:
        raise ValueError(f"{kind} needs {required} blocks of depth; brief supplies {depth}")
    spare, z, rooms = depth - required, 0, []
    for index, (room_name, access, min_depth) in enumerate(rooms_spec):
        extra = spare if index == 1 else 0  # put useful surplus into the primary room.
        rooms.append(Room(room_name, access, 0, z, width, min_depth + extra))
        z += min_depth + extra

    facade = spec.get("facade", "gable" if style in {"frontier", "hollow"} else "stepped")
    roof = spec.get("roof", "gable" if facade == "gable" else "hip")
    if roof not in {"gable", "hip", "flat", "mansard", "sawtooth", "dome"}:
        raise ValueError(f"unknown roof {roof!r}")
    base_height = floors * story_height
    spacing = min(6, max(3, int(spec.get("support_spacing", 5))))
    xs = sorted(set([0, width - 1] + list(range(0, width, spacing))))
    zs = sorted(set([0, depth - 1] + list(range(0, depth, spacing))))
    anchors = [
        {"name": "public_entry", "kind": "entry", "position": [width // 2, 1, 0], "facing": "north", "width": 3},
        {"name": "public_exit", "kind": "exit", "position": [max(1, width - 2), 1, depth - 1], "facing": "south", "width": 3},
        {"name": "service_access", "kind": "maintenance", "position": [1, 1, depth - 1], "facing": "south", "width": 1},
        {"name": "visual_front", "kind": "visual_front", "position": [width // 2, base_height, 0], "facing": "north", "width": width},
    ]
    if kind in {"ride_station", "haunted_walkthrough"}:
        anchors.extend([
            {"name": "queue_entry", "kind": "queue", "position": [1, 1, 0], "facing": "north", "width": 3},
            {"name": "boarding", "kind": "board", "position": [width // 2, 1, max(1, depth // 2)], "width": 3},
            {"name": "ride_exit", "kind": "ride_exit", "position": [width - 2, 1, depth - 1], "facing": "south", "width": 3},
        ])
    result = {"name": name, "program": kind, "style": style,
              "footprint": {"width": width, "depth": depth, "floors": floors, "story_height": story_height},
              "rooms": [asdict(room) for room in rooms],
              "facade": {"style": facade, "profile": facade_profile(width, facade, base_height)},
              "roof": {"style": roof, "base_y": base_height},
              "structure": {"support_spacing": spacing, "columns": [[x, z] for x in xs for z in zs],
                            "max_clear_span": spacing},
              "anchors": anchors}
    result["quality"] = assess(result)
    return result


def assess(blueprint: dict) -> dict:
    """Return explicit architecture failures; callers decide whether to enforce them."""
    fp, rooms = blueprint["footprint"], blueprint["rooms"]
    failures = []
    if fp["story_height"] < 4: failures.append("insufficient interior headroom")
    if fp["width"] < 7: failures.append("facade too narrow for a primary public door")
    if not any(r["access"] == "public" for r in rooms): failures.append("no public purpose")
    if not any(r["access"] == "service" for r in rooms): failures.append("no service/backstage room")
    if blueprint["structure"]["max_clear_span"] > 6: failures.append("unsupported structural span")
    names = {a["name"] for a in blueprint["anchors"]}
    for required in ("public_entry", "public_exit", "service_access", "visual_front"):
        if required not in names: failures.append(f"missing {required} anchor")
    if blueprint["program"] in {"ride_station", "haunted_walkthrough"}:
        for required in ("queue_entry", "boarding", "ride_exit"):
            if required not in names: failures.append(f"missing ride interface {required}")
    return {"ok": not failures, "failures": failures,
            "room_count": len(rooms), "public_rooms": sum(r["access"] == "public" for r in rooms)}
