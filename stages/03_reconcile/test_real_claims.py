"""Issue #1: real lane B output must work without editing the shared fixture."""
import copy
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reconcile as rc

ROOT = HERE.parents[1]
FIX = ROOT / "_shared" / "fixtures"
TODAY = date(2026, 10, 21)


def real_claims():
    return rc.load_jsonl(FIX / "claims.spark-wk9.jsonl")


def run(claims=None, docs=None):
    return rc.reconcile(copy.deepcopy(real_claims() if claims is None else claims),
                        rc.load_jsonl(FIX / "docs.sample.jsonl") if docs is None else docs,
                        TODAY, "team4")


def pick(result, detector, title):
    return next(f for f in result["findings"]
                if f["detector"] == detector and title in (f["item_title"] or "").lower())


@pytest.fixture(scope="module")
def real_result():
    return run()


def test_real_demo_stays_open_and_is_top_warning(real_result):
    item = next(i for i in real_result["items"] if "c042" in i["claims"])
    assert item["status"] == "open"
    assert item["status_from"] == "c040"
    assert item["owner"] == ["Tyler Brandt"]
    warning = pick(real_result, "D1", "demo")
    assert warning == real_result["findings"][0]
    assert warning["facts"]["latest_action"] == "2026-10-22"
    assert warning["facts"]["event_by"] == "2026-10-29"
    assert warning["facts"]["days_left"] == 1
    assert warning["confidence"]["level"] == "high"
    assert warning["stakes_pct"] == 3
    assert {"c014", "c040"} <= set(warning["receipts"])
    # A tentative scheduling decision is not a completion conflict either.
    assert not any(f["detector"] == "D4" and f["facts"].get("field") == "status"
                   and f["item_id"] == item["item_id"] for f in real_result["findings"])


def test_real_accessibility_uses_newer_progress_over_done_assignment(real_result):
    assert next(c for c in real_claims() if c["id"] == "c063")["status"] == "done"
    item = next(i for i in real_result["items"] if "c063" in i["claims"])
    assert item["status"] == "open" and item["status_from"] == "c037"
    assert item["owner"] == ["Kwame Asante"]
    warning = pick(real_result, "D2", "accessibility")
    assert warning["facts"]["away_from"] == "2026-10-28"
    assert warning["facts"]["away_to"] == "2026-11-01"
    assert warning["facts"]["finish_by"] == "2026-10-27"
    assert warning["facts"]["slack_days"] == 4
    assert {"c037", "c108"} <= set(warning["receipts"])
    disagreement = next(f for f in real_result["findings"] if f["detector"] == "D4"
                        and f["item_id"] == item["item_id"] and f["facts"]["field"] == "owner")
    assert disagreement["talk_first"]


def test_real_late_policy_answers_unknown_question_and_parses_hours(real_result):
    warning = pick(real_result, "D9", "late policy")
    assert warning["facts"]["pct_per_day"] == 10
    assert warning["facts"]["max_days"] == 3
    assert warning["facts"]["extension_notice_hours"] == 48
    assert warning["facts"]["extension_deadline"] == "2026-10-28T23:59"
    assert {"c104", "c012", "c013"} <= set(warning["receipts"])


def test_real_scope_is_not_reported_as_missing_submission(real_result):
    gaps = [f for f in real_result["findings"] if f["detector"] == "D3"]
    components = {f["facts"]["component"] for f in gaps}
    assert not components & {"AI usage constraint", "Volunteer shift signup",
                             "Shift reminder", "Coordinator schedule view", "Team charter", "Scope"}
    assert "Contribution log" in components
    assert "Updated project plan" in components
    log = next(f for f in gaps if f["facts"]["component"] == "Contribution log"
               and f["facts"].get("penalty_points") == 5)
    assert log["facts"]["milestone_due"] == "2026-10-30"
    assert log["days_left"] == 9
    assert log["stakes_pct"] == 1


def claim(cid, kind="task", status="open", doc="new", **extra):
    return {"id": cid, "kind": kind, "status": status, "doc_id": doc,
            "item_hint": "Review", "who": [], "date_text": "", "quote": "",
            "extract_confidence": "high", **extra}


DOCS = [{"doc_id": "new", "doc_date": "2026-10-20", "kind": "notes", "lines": []},
        {"doc_id": "old", "doc_date": "2026-10-13", "kind": "notes", "lines": []},
        {"doc_id": "brief", "doc_date": None, "kind": "brief", "lines": []}]


@pytest.mark.parametrize("decision_status", ["open", "unknown"])
def test_new_assignment_or_date_decision_does_not_complete_work(decision_status):
    result = run([claim("task", doc="old", status="in_progress", who=["Alex"]),
                  claim("decision", "decision", decision_status, who=["Sam"])], DOCS)
    assert result["items"][0]["status"] == "in_progress"
    assert result["items"][0]["status_from"] == "task"
    assert result["items"][0]["owner"] == ["Sam"]


def test_explicit_done_decision_can_close_work_but_newer_progress_reopens_it():
    claims = [claim("task", doc="old"), claim("decision", "decision", "done")]
    assert run(claims, DOCS)["items"][0]["status"] == "done"
    claims[0]["doc_id"], claims[1]["doc_id"] = "new", "old"
    result = run(claims, DOCS)
    assert result["items"][0]["status"] == "open"
    assert pick(result, "D4", "review")["facts"]["trust"] == "open"


def test_dependency_does_not_override_progress():
    result = run([claim("task", doc="old"), claim("dep", "dependency", "done")], DOCS)
    assert result["items"][0]["status"] == "open"


def test_done_question_does_not_trigger_d9():
    claims = real_claims()
    next(c for c in claims if c["id"] == "c104")["status"] = "done"
    assert not any(f["detector"] == "D9" for f in run(claims)["findings"])


def test_newer_answer_does_not_resurrect_old_question():
    claims = [claim("q", "question", "unknown", doc="old"),
              claim("answer", "status", "done"),
              claim("rule", "rule", doc="brief", rule="policy")]
    assert not any(f["detector"] == "D9" for f in run(claims, DOCS)["findings"])


def test_missing_notice_hours_does_not_crash_or_invent_a_cutoff():
    claims = real_claims()
    next(c for c in claims if c["id"] == "c013")["date_text"] = "before the deadline"
    warning = pick(run(claims), "D9", "late policy")
    assert warning["facts"]["extension_notice_unresolved"]
    assert "extension_deadline" not in warning["facts"]
    assert "c013" in warning["receipts"]


def test_next_deadline_without_milestone_codes():
    claims = [claim("deadline", "deadline", doc="brief", date_text="Oct 30",
                    deliverable="Prototype delivery", weight_pct=20)]
    assert run(claims, DOCS)["next_deadline"] == {
        "name": "Prototype delivery", "date": "2026-10-30", "days": 9}


def test_undated_submission_is_not_maximally_urgent():
    claims = [claim("required", "requirement", doc="brief", artifact="Evidence log",
                    quote="An evidence log is required.")]
    warning = pick(run(claims, DOCS), "D3", "review")
    assert warning["days_left"] is None
    assert warning["score"] == 0


def test_real_output_has_receipts_and_omits_private_quotes(real_result):
    valid_ids = {c["id"] for c in real_claims()}
    for finding in real_result["findings"]:
        assert finding["receipts"] and set(finding["receipts"]) <= valid_ids
    output = json.dumps(real_result)
    for c in real_claims():
        if c.get("quote_private"):
            assert c["quote"] not in output


def test_real_cli_handoff_passes_validator(tmp_path):
    output = tmp_path / "03_findings.json"
    subprocess.run([sys.executable, str(HERE / "reconcile.py"),
                    str(FIX / "claims.spark-wk9.jsonl"), str(FIX / "docs.sample.jsonl"),
                    "--today", TODAY.isoformat(), "-o", str(output)], check=True, capture_output=True)
    subprocess.run([sys.executable, str(ROOT / "_shared" / "validate.py"),
                    "findings", str(output)], check=True, capture_output=True)
