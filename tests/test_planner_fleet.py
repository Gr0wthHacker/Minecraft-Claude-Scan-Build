"""The plan gate and the fleet cap — the two places where a mistake is expensive.

Both are mostly REFUSALS, and a refusal is the easiest thing to relax later without noticing.
"""
from __future__ import annotations

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
