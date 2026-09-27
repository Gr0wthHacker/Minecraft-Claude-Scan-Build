import pytest

from mcbuild import islands
from mcbuild.plot import Plot


def exact():
    return {"cx": 97600, "cz": 80400, "radius": 49, "site": "park",
            "bounds": {"min_x": 97500, "min_z": 80300,
                       "max_x_exclusive": 97700, "max_z_exclusive": 80500}}


def test_exact_registry_bounds_are_shared_by_python_consumers(tmp_path):
    islands.save({"islands": {"left": exact()}}, str(tmp_path))
    plot = islands.plot_of("left", str(tmp_path))
    assert plot.bounds == (97500, 80300, 97699, 80499)
    assert plot.contains(97500, 80300)
    assert plot.contains(97699, 80499)
    assert not plot.contains(97700, 80499)
    assert "X 97500..97699" in islands.report(str(tmp_path))


def test_legacy_plot_still_has_99_columns():
    plot = Plot(0, 0, 49)
    assert plot.bounds == (-49, -49, 49, 49)
    assert plot.contains(49, 49)
    assert not plot.contains(50, 49)


def test_recapture_preserves_registered_extent_and_site(tmp_path, monkeypatch):
    original = exact()
    islands.save({"islands": {"left": original}}, str(tmp_path))
    monkeypatch.setattr("mcbuild.plot.find", lambda *args: Plot(97600, 80400, 49))
    updated = islands.add("left", "fixture.litematic", schem_dir=str(tmp_path))
    assert updated["bounds"] == original["bounds"]
    assert updated["site"] == "park"
    monkeypatch.setattr("mcbuild.plot.find", lambda *args: Plot(0, 0, 49))
    with pytest.raises(ValueError, match="bedrock differs"):
        islands.add("left", "wrong-island.litematic", schem_dir=str(tmp_path))
    assert islands.load(str(tmp_path))["islands"]["left"]["cx"] == 97600


def test_invalid_explicit_extent_is_not_silently_approximated():
    with pytest.raises(ValueError):
        Plot(0, 0, bounds=(0, 0, -1, 10))
    with pytest.raises(ValueError):
        Plot(100, 100, bounds=(0, 0, 99, 99))
