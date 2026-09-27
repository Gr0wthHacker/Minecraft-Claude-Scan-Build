from __future__ import annotations
from mcbuild import critic, district_solver


def test_district_solver_offers_named_layout_alternatives():
    module = {"name": "Shop", "footprint": [4, 4]}
    got = district_solver.alternatives([module], {"Shop": [{"at": [8, 8], "facing": "south"}]}, route_cells=[(10, 12)])
    assert got["ok"] and set(got["alternatives"]) == {"flow", "skyline", "cost", "balanced"}


def test_critic_prioritizes_player_flow_over_visual_and_cost():
    findings = critic.review(navigation={"ok": False, "failures": ["unreachable exit"]},
                             visual={"ok": False, "failures": ["too dark"]},
                             efficiency={"ok": False, "failures": ["block budget exceeded"]})
    assert [item["area"] for item in findings] == ["player-flow", "visual", "efficiency"]
