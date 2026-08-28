"""The plot: how far out anything is allowed to go, DERIVED from the bedrock.

Jack: *"some go over the edge of our 99x99 boundary, no blocks should go further out than
something we've placed, you can find the 99x99 area by locating the bedrock and moving around
it."*

He is right and the Island Run shipped 120 cells past the edge. The generator's guard was the
CAPTURE box, which is 103x103 - two blocks wider than the plot on every side - so a pad at 50
or 51 out passed a check that was asking the wrong question. The capture is how much of the
world we photographed; the plot is how much of it is ours.

THE BOUNDARY IS FOUND, NOT TYPED. Every skyblock island has one bedrock block at its origin.
Ours is at (-24200, 200, 30000), and measured against it the whole of the island's placed
content spans X -24249..-24151 and Z 29951..30049 - exactly 99 wide, exactly 99 deep, exactly
bedrock +/- 49 on both axes. So the rule and the evidence agree, and neither is hard-coded:
`find()` reads the bedrock out of a capture and `Plot.contains` measures against it.

It is a SQUARE and not a circle, which matters for anything that orbits: a route at radius 52
is legal on the diagonals (49*sqrt2 = 69) and three blocks over the line at the cardinals. A
radius check would either waste the corners or overrun the sides.
"""
from __future__ import annotations

import numpy as np

RADIUS = 49          # measured: the placed content is exactly bedrock +/- 49 on both axes


class Plot:
    """The buildable square, in world coordinates."""

    def __init__(self, cx: int, cz: int, radius: int = RADIUS):
        self.cx, self.cz, self.radius = int(cx), int(cz), int(radius)

    @property
    def bounds(self):
        return (self.cx - self.radius, self.cz - self.radius,
                self.cx + self.radius, self.cz + self.radius)

    def contains(self, x: int, z: int) -> bool:
        return abs(x - self.cx) <= self.radius and abs(z - self.cz) <= self.radius

    def outside(self, cells) -> list:
        """Every (x, y, z, ...) in `cells` that falls off the plot."""
        return [c for c in cells if not self.contains(c[0], c[2])]

    def __repr__(self):
        x0, z0, x1, z1 = self.bounds
        return f"Plot(X {x0}..{x1}, Z {z0}..{z1}, from bedrock at {self.cx},{self.cz})"


def find(capture_path: str, radius: int = RADIUS) -> Plot:
    """Locate the island's bedrock in a capture and return the plot around it.

    Raises if there is no bedrock, deliberately: a silent fallback to a hard-coded centre is
    how a boundary check starts guarding the wrong square.
    """
    from . import schem, scan
    m = schem.load(capture_path)
    sc = scan.load(capture_path.replace(".litematic", ".scan.json"))
    o = sc.meta["origin"]
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    idx = [i for i, n in enumerate(names) if n == "bedrock"]
    if not idx:
        raise ValueError(f"no bedrock in {capture_path}: cannot locate the plot")
    ys, zs, xs = np.nonzero(np.isin(m.ids, idx))
    if not len(xs):
        raise ValueError(f"no bedrock cells in {capture_path}")
    return Plot(int(round(xs.mean())) + o["x"], int(round(zs.mean())) + o["z"], radius)
