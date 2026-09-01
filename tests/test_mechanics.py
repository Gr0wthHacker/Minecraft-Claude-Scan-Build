"""The shared mechanics manifest used by every generator output."""
from __future__ import annotations

import numpy as np

from mcbuild import nbt, schem
from mcbuild.gen import GENERATORS
from mcbuild.mechanics import JAVA_VERSION, manifest


def _model(names):
    palette = [nbt.block_state("minecraft:air")] + [nbt.block_state(f"minecraft:{n}") for n in names]
    ids = np.arange(len(palette), dtype=np.int32).reshape((1, 1, len(palette)))
    return schem.Model(ids, palette)


def test_manifest_groups_real_mechanics_by_registry_kind():
    m = _model(["redstone_wire", "detector_rail", "water", "ladder", "iron_door", "barrel",
                "lantern", "campfire", "oak_wall_sign"])
    got = manifest(m)
    assert got["minecraft"] == f"java-{JAVA_VERSION}"
    assert set(got["families"]) == {"access", "container", "fluid", "hazard", "light", "rail",
                                     "redstone", "signage", "traversal"}
    assert got["families"]["rail"] == ["detector_rail"]
    assert got["families"]["redstone"] == ["detector_rail", "redstone_wire"]
    assert got["verifiers"]["fluid"] == "mcbuild.fluids"
    assert got["roles"] == []


def test_manifest_does_not_claim_a_mechanic_for_plain_architecture():
    got = manifest(_model(["stone_bricks", "spruce_planks", "moss_block"]))
    assert got["families"] == {}
    assert got["verifiers"] == {}


def test_manifest_records_generator_role_contracts_and_name_exceptions():
    got = manifest(_model(["trapped_chest", "redstone_lamp", "oak_sign"]), generator="voidbridge")
    assert got["families"]["redstone"] == ["redstone_lamp", "trapped_chest"]
    assert got["families"]["signage"] == ["oak_sign"]
    assert got["roles"] == ["bridge", "construction"]
    assert "continuous walking deck" in got["role_contracts"]["bridge"]


def test_manifest_accepts_explicit_roles_for_derived_designs():
    got = manifest(_model(["stone"]), roles=["path", "sculpture"])
    assert got["roles"] == ["path", "sculpture"]


def test_every_public_generator_has_the_universal_construction_contract():
    for generator in GENERATORS:
        assert "construction" in manifest(_model(["stone"]), generator=generator)["roles"]
