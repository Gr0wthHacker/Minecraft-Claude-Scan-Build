"""Reusable, elevation-aware geometry contracts for Skyblock paths and bridges."""
from __future__ import annotations

from .grammar import path_route, terraced_slope


def route(spec: dict) -> dict:
    """Compile a walkable path/bridge centreline into placed-course geometry decisions.

    Points are ``[x, y, z]``. Grade is bounded to one rise per horizontal cell; steeper movement
    is explicitly a staircase. This is a geometry plan consumed by themed generators, not a flat
    paving paint operation.
    """
    points = spec.get("points")
    width = int(spec.get("width", 3))
    kind = spec.get("kind", "path")
    if kind not in {"path", "bridge", "ramp", "stairs"} or width < 1 or width % 2 == 0:
        raise ValueError("infrastructure needs path/bridge/ramp/stairs and positive odd width")
    if not isinstance(points, list) or len(points) < 2 or any(not isinstance(p, list) or len(p) != 3 for p in points):
        raise ValueError("infrastructure points must be two or more [x,y,z] positions")
    courses = []
    for a, b in zip(points, points[1:]):
        (x0, y0, z0), (x1, y1, z1) = map(lambda p: tuple(map(int, p)), (a, b))
        flat = path_route([(x0, z0), (x1, z1)])
        rise = y1 - y0
        if abs(rise) > len(flat) - 1:
            raise ValueError("route rises faster than one block per horizontal course")
        heights = terraced_slope(abs(rise), len(flat) - 1) if len(flat) > 1 else [0]
        if rise < 0: heights = [-value for value in heights]
        courses.extend([[x, y0 + heights[index], z] for index, (x, z) in enumerate(flat[:-1])])
    courses.append(list(map(int, points[-1])))
    half = width // 2
    deck = set()
    for x, y, z in courses:
        for dx in range(-half, half + 1):
            for dz in range(-half, half + 1):
                # Square corners are avoided on straight runs by only widening perpendicular to
                # the direction in the themed renderer; this conservative deck remains connected.
                deck.add((x + dx, y, z + dz))
    supports = []
    if kind == "bridge":
        every = max(3, int(spec.get("support_every", 6)))
        supports = [courses[index] for index in range(0, len(courses), every)] + [courses[-1]]
    return {"kind": kind, "width": width, "courses": courses, "deck_cells": [list(p) for p in sorted(deck)],
            "supports": supports, "anchors": {"start": courses[0], "end": courses[-1]},
            "grade_ok": True, "rail_required": bool(spec.get("rails", kind == "bridge"))}
