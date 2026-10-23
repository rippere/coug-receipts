"""D10: a booked event's time clashes with a teammate's weekly busy block (real Week 10 claims)."""
import json
from datetime import date
from pathlib import Path

import reconcile

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "runs" / "team4@2026-10-28"


def test_clock_time():
    assert reconcile.clock_time({"date_text": "thurs 10/29 at 4:30", "quote": ""}) == "16:30"
    assert reconcile.clock_time({"date_text": "", "quote": "meet at 3pm"}) == "15:00"
    assert reconcile.clock_time({"date_text": "10/29", "quote": "Thursday the 29th"}) is None


def test_week10_demo_clash_names_jordan():
    claims = [json.loads(l) for l in (RUN / "02_claims.jsonl").read_text().splitlines() if l.strip()]
    docs = [json.loads(l) for l in (RUN / "01_docs.jsonl").read_text().splitlines() if l.strip()]
    out = reconcile.reconcile(claims, docs, date(2026, 10, 28))
    d10 = [f for f in out["findings"] if f["detector"] == "D10"]
    assert any(f["facts"]["person"] == "Jordan Ellis" and f["facts"]["event_date"] == "2026-10-29"
               and f["facts"]["event_time"] == "16:30" for f in d10)
    assert all(f["receipts"] for f in d10)
