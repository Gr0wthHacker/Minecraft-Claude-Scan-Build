from __future__ import annotations
from mcbuild.spatial import choose


def test_spatial_solver_prefers_route_facing_service_separated_candidate():
    module = {"footprint": [4, 4], "requires_service": True, "near": [[10, 10]]}
    result = choose(module, [{"at": [8, 8], "facing": "south", "service": [8, 12]},
                             {"at": [30, 30], "facing": "north", "service": [30, 29]}],
                    route_cells=[(10, 11), (10, 12)], protected=[])
    assert result["ok"] and result["best"]["at"] == [8, 8]


def test_spatial_solver_explains_bad_placement():
    result = choose({"footprint": [4, 4]}, [{"at": [0, 0], "facing": "north"}], route_cells=[(8, 8)],
                    protected=[(0, 0, 2, 2)])
    assert not result["ok"] and result["repairs"]
