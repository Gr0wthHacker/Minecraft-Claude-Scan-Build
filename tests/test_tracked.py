"""Which designs the mod should treat as live work.

`sync.yaml`'s `progress:` list is the only place that knows, and the mod cannot read it — gson and
no YAML parser, and the file lives in the repo rather than beside the schematics. So sync writes it
out as `designs.json`. Without it, bare `/cscan place` placed all 61 designs in the folder, which
includes a shelf of scratch animals parked at the origin lock — `JAG big` is 57,994 cells of jaguar
claiming void it has no right to.
"""
import json
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from mcbuild.coop import write_tracked           # noqa: E402


def _cfg():
    with open(os.path.join(ROOT, "sync.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_the_tracked_list_is_the_progress_list(tmp_path):
    """ACCEPTED 2026-08-23: every design was accepted as complete and `progress:` emptied
    deliberately, so an empty list is now a legal state - the invariant is equality with the
    cfg, not non-emptiness. When new projects are added back, this holds unchanged."""
    names = write_tracked(_cfg(), str(tmp_path))
    assert len(names) == len(_cfg()["progress"])


def test_extensions_are_stripped_because_the_mod_wants_design_NAMES(tmp_path):
    """The mod addresses designs by bare name. Tested on a synthetic cfg so the property
    stays exercised while the live `progress:` list is empty (all designs accepted)."""
    names = write_tracked({"progress": ["out/Rim Hem.litematic", "out/Lowland Glow.litematic"]}, str(tmp_path))
    for n in names:
        assert not n.endswith((".litematic", ".scan.json", ".work.json")), n
        assert "/" not in n and "\\" not in n, n
    assert names == ["Rim Hem", "Lowland Glow"]


def test_it_is_far_smaller_than_the_folder(tmp_path):
    """The entire point. If these ever converge, the fallback is as good as the list."""
    names = write_tracked(_cfg(), str(tmp_path))
    sd = os.path.expandvars(r"%APPDATA%/CCBlueX/LiquidLauncher/data/gameDir/nextgen/schematics")
    if not os.path.isdir(sd):
        pytest.skip("no schematics dir on this machine")
    in_folder = len([f for f in os.listdir(sd) if f.endswith(".scan.json")])
    assert len(names) < in_folder, f"{len(names)} tracked vs {in_folder} in the folder"


def test_the_file_is_json_the_mod_can_read(tmp_path):
    write_tracked(_cfg(), str(tmp_path))
    p = tmp_path / "designs.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(d["tracked"], list)
    assert all(isinstance(x, str) for x in d["tracked"])
    assert d.get("written"), "no timestamp: staleness would be unanswerable"


def test_no_duplicates(tmp_path):
    names = write_tracked(_cfg(), str(tmp_path))
    assert len(names) == len(set(names))


def test_an_empty_progress_list_writes_an_empty_list_not_a_missing_file(tmp_path):
    """`we do not know` and `you track nothing` are different answers, and the mod branches on
    which: a MISSING file falls back to placing everything, an empty list does not."""
    names = write_tracked({"progress": []}, str(tmp_path))
    assert names == []
    assert (tmp_path / "designs.json").exists()
