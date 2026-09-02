from __future__ import annotations

from mcbuild import tickets, worldschema


def test_strict_worldschema_and_ticket_output(tmp_path):
    plan = {"format": 1, "server_profile": "skyblock-1.19", "style_packs": ["midway"],
            "site": {"anchor": [0, 70, 0], "bounds": [0, 0, 20, 20], "build_plane": 70,
                     "entry_points": [[1, 1]], "protected": []},
            "modules": [{"name": "Station", "plot": "a", "generator": "coaster", "role": "ride",
                         "footprint": [12, 18], "at": [2, 2], "access_points": [[2, 1]], "anchors": [],
                         "depends_on": [], "budget": {"blocks": 1000}, "scenarios": ["public_visit"],
                         "review_views": ["arrival", "facade", "skyline", "interior", "night"]}]}
    assert worldschema.validate(plan) == []
    paths = tickets.write(plan, tmp_path)
    assert "Scenarios" in __import__("pathlib").Path(paths[0]).read_text(encoding="utf-8")
