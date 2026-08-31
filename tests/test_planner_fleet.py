"""The plan gate and the fleet cap — the two places where a mistake is expensive.

Both are mostly REFUSALS, and a refusal is the easiest thing to relax later without noticing.
"""
from __future__ import annotations

import os
import pytest

from mcbuild import fleet, planner


# ---------------------------------------------------------------- the approval gate

def test_a_plan_starts_unapproved():
    """Propose -> approve -> build was Jack's choice, so approval is a state, not a setting."""
    pl = planner.Plan("t", "casino", "x")
    assert pl.approved is False


def test_emit_refuses_an_unapproved_plan(tmp_path, monkeypatch):
    """THE GATE IS IN `emit`, NOT IN THE CLI, so no other caller can route around it."""
    monkeypatch.setattr(planner, "PLANS", tmp_path)
    pl = planner.Plan("gated", "casino", "x")
    pl.modules = [{"name": "M", "gen": "casino", "kind": "slot", "at": [0, 64, 0],
                   "size": [1, 1, 1], "params": {}}]
    pl.save()
    with pytest.raises(PermissionError, match="not approved"):
        planner.emit("gated", out_dir=str(tmp_path))
    planner.approve("gated")
    assert planner.emit("gated", out_dir=str(tmp_path)), "an approved plan must emit"


def test_an_unmatched_brief_raises_rather_than_guessing():
    """A planner that silently defaults to the only theme it has is a planner that builds the
    wrong island confidently."""
    with pytest.raises(ValueError, match="no theme matches"):
        planner._theme_for("a floating library of cats")
    assert planner._theme_for("build me a redstone casino") == "casino"


def test_a_plan_carries_what_it_cannot_promise():
    """The randomiser's distribution is unverifiable offline. A plan that dropped that on the way
    to approval would be asking for a yes it has not earned."""
    pl = planner.Plan("u", "casino", "x")
    pl.unverified.append("randomness ... distribution must be checked in game")
    assert "NOT VERIFIED" in pl.report()


def test_the_report_says_how_to_approve_and_never_pretends_it_is_built():
    pl = planner.Plan("r", "casino", "x")
    assert "NOT APPROVED" in pl.report()
    assert "--approve" in pl.report()


# ---------------------------------------------------------------- the fleet

def test_five_is_a_cap_not_a_default(tmp_path):
    """It is a SERVER RULE, so it is enforced here rather than written in a comment. A tool that
    quietly allowed a sixth is a tool that gets the account banned."""
    assert fleet.MAX_ACCOUNTS == 5
    with pytest.raises(ValueError, match="cap"):
        fleet.assign(["a"], [f"alt{i}" for i in range(6)], schem_dir=str(tmp_path))


def test_two_accounts_never_share_a_design(tmp_path):
    """Two printers placing into the same cells fight: each sees the other's block as already
    built or as a deviation, and the loop's feedback signal becomes noise."""
    d = str(tmp_path)
    fleet.assign(["A", "B", "C"], ["one", "two"], schem_dir=d)
    st = fleet.load(d)
    owners = [c["account"] for c in st["claims"].values()]
    assert len(st["claims"]) == 3
    assert len(set(st["claims"])) == 3, "a design was claimed twice"
    assert set(owners) <= {"one", "two"}


def test_a_claim_is_refused_when_someone_else_holds_it(tmp_path):
    d = str(tmp_path)
    ok, _ = fleet.claim("A", "one", schem_dir=d)
    assert ok
    ok, why = fleet.claim("A", "two", schem_dir=d)
    assert not ok and "one" in why


def test_a_lease_expires_so_a_dead_alt_does_not_strand_the_work(tmp_path):
    """A claim that never expires strands a design for ever; a claim with no expiry lets two
    accounts grab it the moment one is slow. Same reasoning as the chest cooling-off."""
    import datetime as dt
    d = str(tmp_path)
    fleet.claim("A", "one", schem_dir=d)
    st = fleet.load(d)
    old = (dt.datetime.now() - dt.timedelta(minutes=fleet.LEASE_MINUTES + 5)).isoformat()
    st["claims"]["A"]["seen"] = old
    fleet.save(st, d)
    freed = fleet.sweep(fleet.load(d))
    assert freed == ["A"]


def test_a_heartbeat_keeps_a_claim_alive(tmp_path):
    import datetime as dt
    d = str(tmp_path)
    fleet.claim("A", "one", schem_dir=d)
    st = fleet.load(d)
    st["claims"]["A"]["seen"] = (dt.datetime.now() - dt.timedelta(minutes=10)).isoformat()
    fleet.save(st, d)
    assert fleet.heartbeat("one", schem_dir=d) == 1
    assert fleet.sweep(fleet.load(d)) == [], "a heartbeat must reset the lease"


def test_finished_work_is_not_handed_out_again(tmp_path):
    d = str(tmp_path)
    fleet.claim("A", "one", schem_dir=d)
    fleet.finish("A", "one", schem_dir=d)
    fleet.assign(["A", "B"], ["one", "two"], schem_dir=d)
    st = fleet.load(d)
    assert "A" not in st["claims"], "a finished design must not be reassigned"
    assert "B" in st["claims"]


def test_work_is_spread_rather_than_piled_on_one_account(tmp_path):
    d = str(tmp_path)
    fleet.assign([f"D{i}" for i in range(6)], ["a", "b", "c"], schem_dir=d)
    st = fleet.load(d)
    counts = {}
    for c in st["claims"].values():
        counts[c["account"]] = counts.get(c["account"], 0) + 1
    assert max(counts.values()) - min(counts.values()) <= 1, "the split is lopsided"


def test_a_void_plot_sites_nothing_without_a_plane_and_everything_with_one():
    """A FRESH SKYBLOCK ISLAND HAS NO GROUND, and requiring some is how a correct planner refuses
    a perfectly buildable plot.

    The real new island is a 12x12 starter pad in 99x99 of void: every pad search returns nothing
    and all 33 modules report NO SITE, which reads as "the terrain is awkward" when the truth is
    that there is no terrain. `plane` is a DECLARATION rather than a discovery - you say which
    course the floor stands on - and every guard that is about correctness rather than about
    terrain still applies, which is what this asserts.
    """
    from mcbuild import planner, islands as islands_mod
    world = "out/newisle.litematic"
    if not os.path.exists(world):
        import pytest
        pytest.skip("no new-island capture in this checkout")
    plot = islands_mod.plot_of("newisle")
    if plot is None:
        import pytest
        pytest.skip("newisle is not registered in this checkout")

    bare = planner.make("redstone casino", world, name="_t_bare", island="newisle")
    assert not bare.modules, "void ground must not silently site anything"
    assert any("NO SITE" in n for n in bare.notes)

    on = planner.make("redstone casino", world, name="_t_plane", island="newisle", plane=203)
    assert len(on.modules) > 25, "a declared plane must site most of the theme"
    assert any("BUILD PLANE" in n for n in on.notes), "and it must SAY it was declared, not found"
    # THE BOUNDARY IS CHECKED ON THE MEASURED EXTENT, NOT ON THE DECLARED BOX.
    #
    # A casino game is declared 9x8x8 and builds 16x10x10, running from at-6 to at+9 across -
    # the shell, the pit and the payout all extend BACKWARDS from the cell the player stands at.
    # Checking the declared box let a game put its floor over the island's starter chest twice,
    # and would have let one finish past the plot edge.
    for m in on.modules:
        ax, _ay, az = m["at"]
        fx, _fy, fz = m["anchor_offset"]
        w, _h, d = m["size"]
        x0, z0 = ax + fx, az + fz
        assert plot.contains(x0, z0) and plot.contains(x0 + w - 1, z0 + d - 1), (
            f"{m['name']} is off the plot - the boundary guard must use the real footprint")
    assert any(m["size"] != m["declared_size"] for m in on.modules), (
        "the footprint must be MEASURED from the generator, not read from the theme table")
    # the floors are still stacked, and the gaming floor is the plane itself
    assert min(m["at"][1] for m in on.modules) == 203
    assert max(m["at"][1] for m in on.modules) > 203, "the mezzanine must still be lifted"


def test_a_module_is_never_sited_on_something_you_use():
    """RULE 10 AT THE SITING STAGE, which is where it had never been applied.

    `_clear` compares module against module, so on a fresh island a game sited its floor straight
    over the STARTER CHEST - the one holding everything that alt owns - and shipped with a single
    overlap, no placement problem and a clean bill of materials.

    The first fix did not work either, and the reason is worth keeping: the palette holds NBT
    TAGS, and `str(tag)` is a repr that merely CONTAINS the block name, so a careless parse
    matched the bedrock instead and the chest was still invisible.
    """
    from mcbuild import planner, islands as islands_mod, scan as scan_mod
    from mcbuild.gen import protect
    world = "out/newisle.litematic"
    if not os.path.exists(world) or islands_mod.plot_of("newisle") is None:
        pytest.skip("no new-island capture in this checkout")

    sc = scan_mod.load(world)
    used = planner._used_cells(sc)
    assert used, "the capture has a chest in it - the scan must find it"
    names = set()
    m = sc.model
    for tag in m.palette:
        try:
            names.add(tag.value["Name"].value.split(":")[-1])
        except Exception:                                        # noqa: BLE001
            pass
    assert "chest" in names and any(protect.is_used(n) for n in names)

    pl = planner.make("redstone casino", world, name="_t_used", island="newisle", plane=203)
    for (ux, uy, uz) in used:
        for mod in pl.modules:
            ax, ay, az = mod["at"]
            fx, fy, fz = mod["anchor_offset"]
            w, h, d = mod["size"]
            x0, y0, z0 = ax + fx, ay + fy, az + fz
            inside = (x0 <= ux < x0 + w and y0 <= uy < y0 + h and z0 <= uz < z0 + d)
            assert not inside, f"{mod['name']} sits on a used block at {ux},{uy},{uz}"
