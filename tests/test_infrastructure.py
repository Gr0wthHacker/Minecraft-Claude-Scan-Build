"""Physical routes must remain walkable and structurally explicit."""
from __future__ import annotations

import pytest

from mcbuild.infrastructure import route


def test_bridge_route_has_grade_limited_courses_supports_and_anchors():
    result = route({"kind": "bridge", "width": 3, "points": [[0, 70, 0], [8, 73, 0]], "support_every": 4})
    assert result["grade_ok"] and result["anchors"]["start"] == [0, 70, 0]
    assert result["supports"][-1] == [8, 73, 0] and result["rail_required"]
    assert all(abs(b[1] - a[1]) <= 1 for a, b in zip(result["courses"], result["courses"][1:]))


def test_route_rejects_unwalkable_grades_and_even_widths():
    with pytest.raises(ValueError, match="rises faster"):
        route({"kind": "stairs", "width": 3, "points": [[0, 70, 0], [1, 73, 0]]})
    with pytest.raises(ValueError, match="odd width"):
        route({"kind": "path", "width": 4, "points": [[0, 70, 0], [2, 70, 0]]})
