"""Placement rules learned from real captures make the audit accept what the world accepts — and nothing more."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from mcbuild import audit, learn, nbt, schem


def _model(states, cells):
    """states: list of (name, props); cells: {(x,y,z): palette index}"""
    pal = [nbt.block_state("minecraft:air")] + [nbt.block_state("minecraft:" + n, **p) for n, p in states]
    m = schem.Model(np.zeros((4, 4, 4), np.int32), pal)
    for (x, y, z), i in cells.items():
        m.ids[y, z, x] = i
    return m


def _with_rules(rules):
    audit._OBSERVED = rules


def teardown_function(_):
    audit._OBSERVED = None   # back to whatever is on disk


def test_mine_finds_lantern_on_fence_and_vine_chain():
    m = _model([("oak_fence", {}), ("lantern", {"hanging": "false"}), ("moss_block", {}),
                ("vine", {"north": "true"}), ("vine", {"north": "true"})],
               {(1, 0, 1): 1, (1, 1, 1): 2,                       # lantern on fence
                (3, 3, 2): 3, (3, 3, 3): 4, (3, 2, 3): 5})       # vine on moss (north), vine hanging below it
    mined, anomalies = learn.mine(m)
    assert mined["lantern"]["below"] == {"oak_fence": 1}
    assert mined["vine"]["side"] == {"moss_block": 1} and mined["vine"]["above"] == {"vine": 1}
    assert anomalies == []


def test_mine_reports_air_attachment_as_anomaly_not_rule():
    m = _model([("lantern", {"hanging": "true"})], {(1, 1, 1): 1})
    mined, anomalies = learn.mine(m)
    assert "lantern" not in mined and len(anomalies) == 1


def test_audit_accepts_only_learned_supports():
    m = _model([("iron_bars", {}), ("lantern", {"hanging": "false"}), ("tall_grass", {"half": "lower"}),
                ("tall_grass", {"half": "upper"}), ("moss_block", {})],
               {(1, 0, 1): 1, (1, 1, 1): 2, (3, 0, 3): 5, (3, 1, 3): 3, (3, 2, 3): 4})
    _with_rules({})
    kinds = sorted(p.kind for p in audit.check_supports(m))
    assert kinds == ["lantern", "plant"], kinds                     # bars + upper-half grass rejected cold
    _with_rules({"lantern": {"below": {"iron_bars": 10}}, "plant:tall_grass": {"below": {"tall_grass": 7}}})
    assert audit.check_supports(m) == []                            # accepted once seen for real
    _with_rules({"lantern": {"below": {"glass_pane": 10}}})
    assert [p.kind for p in audit.check_supports(m)] == ["lantern", "plant"]  # exact triples only


def test_iron_chain_holds_lantern():
    m = _model([("moss_block", {}), ("iron_chain", {"axis": "y"}), ("lantern", {"hanging": "true"})],
               {(1, 3, 1): 1, (1, 2, 1): 2, (1, 1, 1): 3})
    _with_rules({})
    assert audit.check_supports(m) == []
