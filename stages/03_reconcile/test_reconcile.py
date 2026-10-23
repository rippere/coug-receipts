"""Golden Week-9 checks for stage 03 (see _shared/golden-team4.md).

Run:  uv run --with dateparser --with rapidfuzz --with pytest python -I -m pytest stages/03_reconcile -q
"""
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reconcile as rc  # noqa: E402

FIX = HERE.parents[1] / "_shared" / "fixtures"
TODAY = date(2026, 10, 21)


def run():
    claims = rc.load_jsonl(FIX / "claims.sample.jsonl")
    docs = rc.load_jsonl(FIX / "docs.sample.jsonl")
    return rc.reconcile(claims, docs, TODAY, "team4")


RESULT = run()
F = RESULT["findings"]


def pick(detector, title_word):
    hits = [f for f in F if f["detector"] == detector and title_word in (f["item_title"] or "").lower()]
    assert hits, f"no {detector} finding about '{title_word}'"
    return hits[0]


def test_fixture_quotes_are_verbatim():
    docs = {d["doc_id"]: d for d in rc.load_jsonl(FIX / "docs.sample.jsonl")}
    for c in rc.load_jsonl(FIX / "claims.sample.jsonl"):
        line = next(l["text"] for l in docs[c["doc_id"]]["lines"] if l["loc"] == c["loc"])
        assert c["quote"] in line, c["id"]


def test_date_resolution():
    week1, ms = date(2026, 8, 24), {"M3": date(2026, 10, 30)}
    r = lambda t, base=None: rc.resolve_date(t, base, 2026, week1, ms)
    assert r("Fri, Oct 30") == date(2026, 10, 30)
    assert r("no later than Thursday, October 29") == date(2026, 10, 29)
    assert r("nov 6?") == date(2026, 11, 6)
    assert r("10/27") == date(2026, 10, 27)
    assert r("2026-10-23") == date(2026, 10, 23)
    assert r("wk 10") == date(2026, 10, 30)          # Friday of week 10
    assert r("due on the same date as M3") == date(2026, 10, 30)
    assert r("ASAP") is None and r("?") is None and r("") is None
    assert r("at least seven calendar days before") is None


def test_next_deadline():
    assert RESULT["next_deadline"] == {"name": "M3", "date": "2026-10-30", "days": 9}


def test_d1_demo_request_by_oct_22():
    f = pick("D1", "demo")
    assert f["facts"]["latest_action"] == "2026-10-22"
    assert f["facts"]["event_by"] == "2026-10-29"
    assert f["facts"]["days_left"] == 1
    assert f["confidence"]["level"] == "high"
    people = {c["person"] for c in f["facts"]["constraints_on_event_day"]}
    assert {"Kwame Asante", "Jordan Ellis"} <= people


def test_d2_kwame_away_before_accessibility_done():
    f = pick("D2", "accessibility")
    assert f["facts"]["owner"] == "Kwame Asante"
    assert f["facts"]["away_from"] == "2026-10-28"
    assert f["facts"]["finish_by"] == "2026-10-27"


def test_d4_peer_evals_trust_brief():
    f = next(f for f in F if f["detector"] == "D4" and "peer" in f["item_title"] and f["facts"]["field"] == "date")
    assert f["facts"]["trust"] == "2026-10-30"
    assert "2026-11-06" in [s["says"] for s in f["facts"]["sides"]]
    assert f["confidence"]["level"] == "high"


def test_d4_react_decision_beats_tracker():
    f = next(f for f in F if f["detector"] == "D4" and f["facts"]["field"] == "status")
    assert f["facts"]["trust"] == "decision"


def test_d9_late_policy_answered():
    f = pick("D9", "late policy")
    assert f["facts"]["pct_per_day"] == 10 and f["facts"]["max_days"] == 3
    assert f["facts"]["extension_deadline"] == "2026-10-28T23:59"


def test_d3_contribution_log_missing():
    f = next(f for f in F if f["detector"] == "D3" and f["facts"]["component"] == "contribution log")
    assert f["facts"]["penalty_points"] == 5
    assert f["confidence"]["level"] == "high"


def test_d5_privacy_plan_unowned():
    f = pick("D5", "privacy")
    assert "owner" in f["facts"]["missing"] and f["talk_first"]


def test_d7_hours_tracking_carried_over():
    f = pick("D7", "hours")
    assert f["facts"]["meetings_open"] >= 2 and f["talk_first"]


def test_no_reasons_leak():
    blob = json.dumps(RESULT).lower()
    for word in ("wedding", "interview in seattle", "sick", "commute"):
        assert word not in blob
