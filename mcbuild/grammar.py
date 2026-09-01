"""Small deterministic grammars shared by sophisticated generators.

They return geometry decisions rather than placing blocks, allowing each themed generator to apply
its own palette and Minecraft state/support rules while sharing the same compositional language.
"""
from __future__ import annotations


def facade_profile(width: int, style: str = "stepped", base: int = 4) -> list[int]:
    """A readable roofline/false-front silhouette with a central hierarchy."""
    if width < 3:
        raise ValueError("a facade needs at least three columns")
    if style not in {"flat", "stepped", "gable", "bracketed"}:
        raise ValueError("unknown facade style")
    mid = (width - 1) / 2
    out = []
    for x in range(width):
        d = abs(x - mid)
        if style == "flat": h = base
        elif style == "stepped": h = base + max(0, int((width / 2 - d) // 2))
        elif style == "gable": h = base + max(0, int(width / 2 - d))
        else: h = base + (2 if x in (0, width - 1) else 0)
        out.append(h)
    return out


def path_route(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """A 4-connected route through declared control points; no diagonal gaps."""
    if len(points) < 2:
        raise ValueError("a route needs an entry and exit")
    out = [tuple(points[0])]
    for end in points[1:]:
        x, z = out[-1]; ex, ez = end
        while x != ex:
            x += 1 if ex > x else -1; out.append((x, z))
        while z != ez:
            z += 1 if ez > z else -1; out.append((x, z))
    return out


def terraced_slope(rise: int, run: int) -> list[int]:
    """One stable height per horizontal course, never changing by more than one block."""
    if run < 1 or rise < 0:
        raise ValueError("rise must be non-negative and run positive")
    return [min(rise, (i + 1) * rise // run) for i in range(run)]


def sculpture_masses(height: int, widths: list[int]) -> list[tuple[int, int]]:
    """Named body-mass bands: a compact scaffold for a silhouette-first sculpture."""
    if height < 3 or not widths or any(w < 1 for w in widths):
        raise ValueError("sculpture masses need positive widths and at least three blocks of height")
    return [(round(i * (height - 1) / max(1, len(widths) - 1)), w) for i, w in enumerate(widths)]
