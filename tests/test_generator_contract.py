"""Production modules must state their contract and their target server."""
from __future__ import annotations

import numpy as np

from mcbuild import generator_contract, nbt, schem, server_profile


def _model():
    return schem.Model(np.array([[[1]]], dtype=np.int32), [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone")])


def test_contract_makes_missing_world_interfaces_a_hard_visible_failure():
    report = generator_contract.assess({"name": "Ride", "gen": "coaster", "world_contract": True,
                                        "roles": ["ride"], "design": {"purpose": "ride"}}, _model(),
                                      mechanics={"families": {}}, design={"brief": {"purpose": "ride"}})
    assert not report["ok"] and "missing typed anchors" in report["failures"]


def test_skyblock_profile_is_explicitly_1_19_and_has_a_registry_guard():
    assert server_profile.current()["minecraft"] == "1.19"
    violations = server_profile.validate_model(_model())
    assert isinstance(violations, list)
