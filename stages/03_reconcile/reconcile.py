#!/usr/bin/env python3
"""Stage 03 - reconcile: claims -> items -> scored findings.

Code does every date and count in this file. There is no AI here.
Contract: CONTEXT.md (this folder). Rules: ../../_shared/detectors.md.

Usage:
    python reconcile.py <claims.jsonl> <docs.jsonl> --today YYYY-MM-DD -o <findings.json>
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

import dateparser
from rapidfuzz import fuzz

CONF_WEIGHT = {"high": 1.0, "med": 0.7, "low": 0.4}
CONF_RANK = {"high": 0, "med": 1, "low": 2}

# Date words that mean "no real date". These trigger D5 instead of a guess.
VAGUE = {"", "?", "asap", "tbd", "soon", "this week", "before demo", "later"}
MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
MONTH_RE = (r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
            r"aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
            r"\s+(\d{1,2})(?:,?\s+(\d{4}))?\b")
# Only hand a phrase to dateparser when it is clearly relative ("next Tuesday").
RELATIVE_RE = re.compile(r"\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\b|\b(today|tomorrow|tonight|next)\b")

# Item clustering: words that don't identify a task, and words that mean the same thing.
STOPWORDS = {"the", "a", "an", "w", "with", "for", "of", "to", "and", "in", "on", "get", "do", "dr", "our"}
SYNONYMS = {"wcag": "accessibility", "a11y": "accessibility", "check": "review",
            "evaluations": "evals", "evaluation": "evals", "eval": "evals"}
TEAM_WORDS = {"everyone", "all", "team", "whole team", "everybody"}
TASKY = {"task", "status", "dependency"}          # kinds that carry an owner and a status


# ---------------------------------------------------------------- loading

def load_jsonl(path) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def iso(d) -> str | None:
    return d.isoformat() if d else None


# ---------------------------------------------------------------- dates

def resolve_date(text, base=None, year=None, week1=None, milestones=None) -> date | None:
    """Turn a date phrase into a date, or None. Never guesses.

    base: the date of the document the phrase came from (for "next Tuesday").
    year: used when the phrase has no year ("9/19", "Oct 30").
    week1: Monday of week 1, for "wk 10" (resolved to the Friday of that week).
    milestones: {"M3": date} for phrases like "due on the same date as M3".
    """
    if text is None:
        return None
    t = text.strip().lower()
    if t.strip("?!. ") in VAGUE:
        return None
    year = year or (base.year if base else date.today().year)
    try:
        if m := re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t):
            return date(int(m[1]), int(m[2]), int(m[3]))
        if (m := re.search(r"\bm(\d+)\b", t)) and milestones and ("same" in t or "with" in t):
            if f"M{m[1]}" in milestones:
                return milestones[f"M{m[1]}"]
        if (m := re.search(r"\b(?:wk|week)\s*(\d+)\b", t)) and week1:
            return week1 + timedelta(weeks=int(m[1]) - 1, days=4)
        if m := re.search(MONTH_RE, t):
            return date(int(m[3]) if m[3] else year, MONTHS[m[1][:3]], int(m[2]))
        if m := re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t):
            y = int(m[3]) if m[3] else year
            return date(y + 2000 if y < 100 else y, int(m[1]), int(m[2]))
    except ValueError:          # e.g. "13/45" - not a real date
        return None
    if RELATIVE_RE.search(t) and base:
        got = dateparser.parse(text, settings={
            "RELATIVE_BASE": datetime.combine(base, datetime.min.time()),
            "PREFER_DATES_FROM": "future"})
        return got.date() if got else None
    return None


def working_days_between(start: date, end: date) -> int:
    """Mon-Fri days after `start`, up to and including `end`."""
    days, d = 0, start
    while d < end:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


def prepare_claims(claims, docs, today):
    """Attach doc info and a resolved date (`_date`) to every claim. Returns context."""
    doc_by_id = {d["doc_id"]: d for d in docs}
    for c in claims:
        doc = doc_by_id.get(c["doc_id"], {})
        c["_doc_kind"] = doc.get("kind")
        c["_doc_date"] = date.fromisoformat(doc["doc_date"]) if doc.get("doc_date") else None
        c["_file"] = doc.get("file")
        c["_uncertain"] = "?" in (c.get("date_text") or "")

    # Pass 1: week anchor + course year, then milestone dates.
    week1 = next((date.fromisoformat(c["week1_monday"]) for c in claims
                  if c.get("rule") == "week_anchor" and c.get("week1_monday")), None)
    year = week1.year if week1 else today.year
    milestones = {}
    for c in claims:
        if c["kind"] == "deadline" and (m := re.search(r"\bM\d+\b", c.get("deliverable", ""))):
            d = resolve_date(c.get("date_text"), c["_doc_date"], year, week1)
            if d:
                milestones[m[0]] = d

    # Pass 2: every claim.
    for c in claims:
        if c["kind"] in ("availability", "person"):
            c["_date"] = None
            continue
        c["_date"] = resolve_date(c.get("date_text"), c["_doc_date"], year, week1, milestones)
    return {"week1": week1, "year": year, "milestones": milestones, "docs": doc_by_id}


# ---------------------------------------------------------------- items

def norm_hint(hint: str) -> str:
    words = [SYNONYMS.get(w, w) for w in re.findall(r"[a-z0-9]+", (hint or "").lower())]
    return " ".join(w for w in words if w not in STOPWORDS)


def cluster(claims, overrides=None, threshold=88) -> list[dict]:
    """Group claims into items by their item_hint. `overrides` = {claim_id: item_key}."""
    groups: list[dict] = []
    for c in claims:
        if c["kind"] in ("availability", "person"):
            continue
        key = (overrides or {}).get(c["id"]) or norm_hint(c.get("item_hint"))
        best = max(groups, key=lambda g: fuzz.token_sort_ratio(key, g["key"]), default=None)
        if best and fuzz.token_sort_ratio(key, best["key"]) >= threshold:
            best["claims"].append(c)
        else:
            groups.append({"key": key, "claims": [c]})
    return groups


def recency(c):
    """Sort key: newer documents first-class; undated documents count as oldest."""
    return (c["_doc_date"] or date.min, -CONF_RANK.get(c.get("extract_confidence"), 2))


def status_evidence(claims):
    """Deciding an owner/date/scope is not completion of the work.

    An explicitly done decision can compete with task progress, but never
    overrides a newer report. Dependencies describe prerequisites, not progress.
    """
    return [c for c in claims
            if (c["kind"] in ("task", "status")
                and c.get("status") in ("open", "in_progress", "done"))
            or (c["kind"] == "decision" and c.get("status") == "done")]


def newest_status(claims):
    # Prefer direct task evidence over a decision on the same dated source.
    # On a same-day tie, the less-finished status wins: an early warning should never assume "done".
    unfinished = {"open": 1, "in_progress": 1, "done": 0}
    return max(status_evidence(claims),
               key=lambda c: (recency(c)[0], unfinished.get(c.get("status"), 0), recency(c)[1],
                              c["kind"] != "decision"), default=None)


def build_items(groups, ctx, today) -> list[dict]:
    deadlines = [c for g in groups for c in g["claims"] if c["kind"] == "deadline" and c.get("weight_pct")]
    items = []
    for n, g in enumerate(groups, 1):
        cl = g["claims"]
        tasky = [c for c in cl if c["kind"] in TASKY]
        title = (tasky or cl)[0]["item_hint"]

        # Keep the newest named owner; conflicting historical names remain in D4.
        team_owned = any((c.get("who_raw") or "").strip().lower() in TEAM_WORDS for c in cl)
        owner_claim = max((c for c in cl if c["kind"] in TASKY | {"decision"}
                           and c.get("who")), key=recency, default=None)
        owners = list(owner_claim["who"]) if owner_claim else []

        # Due date: the brief wins; otherwise the newest dated source.
        # Only claims that set a due date count; a status report's date ("did it sat") is when work happened.
        dated = [c for c in cl if c["_date"] and c["kind"] in ("task", "deadline", "rule", "decision")]
        brief_dated = [c for c in dated if c["_doc_kind"] == "brief"]
        if brief_dated:
            due_claim, basis = min(brief_dated, key=lambda c: c["_date"]), "brief"
        elif dated:
            due_claim, basis = max(dated, key=recency), "newest source"
        else:
            due_claim, basis = None, None

        # New progress supersedes old decisions, even an old decision labeled done.
        newest = newest_status(cl)
        if newest:
            status, status_from = newest.get("status", "unknown"), newest["id"]
        else:
            status, status_from = ("open" if any(c.get("status") == "open" for c in cl) else "unknown"), None

        # Stakes: course percentage points at risk.
        stakes, milestone, milestone_date = 0.5, None, None
        # The event's authoritative name may be clearer than a tracker alias.
        stake_names = [title, *(c["deliverable"] for c in cl
                               if c.get("deliverable") and not c.get("weight_pct"))]
        for d in deadlines:
            if d in cl:
                stakes, milestone, milestone_date = float(d["weight_pct"]), d["deliverable"], d["_date"]
            for comp in d.get("components", []):
                if any(fuzz.token_set_ratio(norm_hint(name), norm_hint(comp["name"])) >= 70
                       for name in stake_names):
                    stakes = round(d["weight_pct"] * comp["weight_pct"] / 100, 2)
                    milestone, milestone_date = d["deliverable"], d["_date"]
        for c in cl:
            if c.get("penalty_points") and deadlines:
                upcoming = [d for d in deadlines if d["_date"] and d["_date"] >= today]
                if upcoming:
                    d = min(upcoming, key=lambda d: d["_date"])
                    stakes = round(d["weight_pct"] * c["penalty_points"] / 100, 2)
                    milestone, milestone_date = d["deliverable"], d["_date"]

        items.append({
            "item_id": f"i{n:02d}", "title": title, "key": g["key"],
            "owner": owners, "team_owned": team_owned,
            "due": due_claim["_date"] if due_claim else None, "due_basis": basis,
            "due_uncertain": bool(due_claim and due_claim["_uncertain"]),
            "status": status, "status_from": status_from,
            "claims": cl, "stakes_pct": stakes,
            "milestone": milestone, "milestone_date": milestone_date,
            "alias_merged": len({(c.get("item_hint") or "").lower() for c in cl}) > 1,
            "blocks": [], "blocked_by": [],
        })
    link_dependencies(items)
    return items


def find_item(items, hint, threshold=80):
    key = norm_hint(hint)
    best = max(items, key=lambda it: fuzz.token_sort_ratio(key, it["key"]), default=None)
    return best if best and fuzz.token_sort_ratio(key, best["key"]) >= threshold else None


def link_dependencies(items):
    """'X can't finish until Y': Y inherits X's due date and stakes if they are tighter."""
    for it in items:
        for c in it["claims"]:
            if c["kind"] != "dependency":
                continue
            blocked = find_item(items, c.get("blocked")) or it
            blocker = find_item(items, c.get("blocked_by"))
            if not blocker or blocker is blocked:
                continue
            blocked["blocked_by"].append((blocker["item_id"], c["id"]))
            blocker["blocks"].append((blocked["item_id"], c["id"]))
            if blocked["due"] and (not blocker["due"] or blocked["due"] < blocker["due"]):
                blocker["due"], blocker["due_basis"] = blocked["due"], f"blocks {blocked['item_id']}"
            blocker["stakes_pct"] = max(blocker["stakes_pct"], blocked["stakes_pct"])


# ---------------------------------------------------------------- detectors

def finding(detector, item, facts, receipts, conf, why, days_left, people=(), talk_first=False, stakes=None):
    stakes = item["stakes_pct"] if stakes is None else stakes
    norm = stakes / (stakes + 1)                     # saturates: 3 points ~ 0.75
    urgency = 1 / (1 + max(days_left, 0)) if days_left is not None else 0
    return {
        "detector": detector, "item_id": item["item_id"] if item else None,
        "item_title": item["title"] if item else facts.get("component"),
        "facts": facts, "people": list(people), "talk_first": talk_first,
        "confidence": {"level": conf, "why": why},
        "receipts": list(dict.fromkeys(receipts)),
        "days_left": days_left, "stakes_pct": stakes,
        "score": round(norm * urgency * CONF_WEIGHT[conf], 4),
    }


def availability_blocks(claims):
    """Away-ranges and weekly blocks, per person. Reasons were dropped in stage 02."""
    away, weekly = {}, {}
    for c in claims:
        if c["kind"] != "availability":
            continue
        person = c.get("person") or (c.get("who") or [None])[0]
        if c.get("away_from"):
            rng = (date.fromisoformat(c["away_from"]), date.fromisoformat(c.get("away_to") or c["away_from"]))
            away.setdefault(person, {}).setdefault(rng, []).append(c["id"])
        elif c.get("days"):
            weekly.setdefault(person, []).append({**{k: c.get(k) for k in ("days", "from", "to")}, "claim": c["id"]})
    return away, weekly


WEEKDAY_CODES = ["M", "T", "W", "Th", "F", "Sa", "Su"]


def clock_time(c):
    """'HH:MM' if the claim names a time of day ('at 4:30', '3pm'), else None. Bare hours below 8 read as pm."""
    text = f"{c.get('date_text') or ''} {c.get('quote') or ''}".lower()
    m = re.search(r"\b(\d{1,2}):(\d\d)\s*(am|pm)?\b", text) or re.search(r"\b(\d{1,2})()\s*(am|pm)\b", text)
    if not m:
        return None
    hour, minute, ampm = int(m[1]), m[2] or "00", m[3]
    if ampm == "pm" and hour < 12 or (not ampm and hour < 8):
        hour += 12
    return f"{hour % 24:02d}:{minute}"


def d10_event_clash(items, weekly, today):
    """A booked event's time falls inside a teammate's weekly busy block: someone else may need to cover."""
    out = []
    for it in items:
        events = [c for c in it["claims"] if c["_date"] and c["_date"] >= today
                  and c["kind"] in ("task", "decision", "deadline") and clock_time(c)]
        if not events:
            continue
        ev = min(events, key=lambda c: c["_date"])
        at, code = clock_time(ev), WEEKDAY_CODES[ev["_date"].weekday()]
        seen = set()
        for person, blocks in weekly.items():
            for b in blocks:
                if person and person not in seen and code in (b["days"] or []) \
                        and b.get("from") and b.get("to") and b["from"] <= at <= b["to"]:
                    seen.add(person)
                    act_by = max(today, ev["_date"] - timedelta(days=1))
                    out.append(finding("D10", it, {
                        "event_date": iso(ev["_date"]), "event_time": at, "person": person,
                        "busy_from": b["from"], "busy_to": b["to"], "act_by": iso(act_by)},
                        [ev["id"], b["claim"]], "high",
                        "the booked time falls inside a weekly busy block on record",
                        (act_by - today).days, people=[person], talk_first=True))
    return out


def d1_lead_time(items, away, weekly, today):
    out = []
    for it in items:
        rules = [c for c in it["claims"] if c.get("rule") == "lead_time"]
        # Only upcoming events count; a past meeting filed under the same item is history, not a deadline.
        events = [c for c in it["claims"] if c["kind"] in ("rule", "deadline") and c["_date"] and c["_date"] >= today]
        if not rules or not events or it["status"] == "done":
            continue
        rule, event = rules[0], min(events, key=lambda c: c["_date"])
        latest = event["_date"] - timedelta(days=rule["days"])
        if today < latest - timedelta(days=2):
            continue
        # Who else is constrained on the event day (constraints only, never reasons).
        constraints = []
        for person, ranges in away.items():
            for (a, b), ids in ranges.items():
                if a <= event["_date"] <= b:
                    constraints.append({"person": person, "away_from": iso(a), "away_to": iso(b), "claims": ids})
        for person, blocks in weekly.items():
            for blk in blocks:
                if WEEKDAY_CODES[event["_date"].weekday()] in (blk["days"] or []):
                    constraints.append({"person": person, "busy_from": blk["from"], "busy_to": blk["to"],
                                        "claims": [blk["claim"]]})
        status_claims = [c["id"] for c in it["claims"] if c["kind"] in TASKY]
        conf = "high" if rule["_doc_kind"] == "brief" and status_claims else "med"
        facts = {"latest_action": iso(latest), "days_left": (latest - today).days,
                 "lead_days": rule["days"], "event_by": iso(event["_date"]),
                 "earliest_bookable": iso(today + timedelta(days=rule["days"])),
                 "status": it["status"], "constraints_on_event_day": constraints}
        receipts = [rule["id"], event["id"], *status_claims, *[i for k in constraints for i in k["claims"]]]
        out.append(finding("D1", it, facts, receipts, conf,
                           "course rule from the brief, and the latest notes say it is not done"
                           if conf == "high" else "single source",
                           (latest - today).days, people=it["owner"]))
    return out


def merged_ranges(ranges):
    """Join overlapping or touching away-ranges from different sources into one span."""
    out = []
    for (a, b), ids in sorted(ranges.items()):
        if out and a <= out[-1][0][1] + timedelta(days=1):
            (pa, pb), pids = out[-1]
            out[-1] = ((pa, max(pb, b)), [*pids, *ids])
        else:
            out.append(((a, b), list(ids)))
    return out


def d2_owner_unavailable(items, away, today, next_deadline):
    out = []
    for it in items:
        # Only work due by the next deadline; that deadline is when the work is actually needed.
        if it["status"] == "done" or not it["owner"] or not next_deadline:
            continue
        if it["due"] and (it["due"] > next_deadline or it["due"] < today - timedelta(days=7)):
            continue  # due after this milestone, or overdue by over a week (stale record, not this week's work)
        window_end = next_deadline
        for person in it["owner"]:
            for (a, b), ids in merged_ranges(away.get(person, {})):
                if a <= window_end and b >= today:
                    finish_by = a - timedelta(days=1)
                    task_ids = [c["id"] for c in it["claims"] if person in (c.get("who") or [])]
                    conf = "high" if any(c.get("extract_confidence") == "high" for c in it["claims"]
                                         if c["id"] in task_ids) else "med"
                    why = "availability sheet and owner both on record"
                    if it["alias_merged"]:
                        why += "; tracker may list the same work under another name"
                    out.append(finding("D2", it, {
                        "owner": person, "away_from": iso(a), "away_to": iso(b),
                        "finish_by": iso(finish_by), "work_until": iso(window_end),
                        "slack_days": working_days_between(today, finish_by)},
                        [*task_ids, *ids], conf, why, (finish_by - today).days, people=[person]))
    return out


def submission_requirement(claim, item):
    """An extracted 'artifact' may be a product feature, not a submission.

    Require a deadline association, penalty, or explicit submission obligation.
    Ambiguous scope stays in the item record for human review, not a rubric gap.
    """
    if claim["kind"] != "requirement" or not (claim.get("artifact") or claim.get("penalty_points")):
        return False
    return bool(claim.get("penalty_points")
                or any(c["kind"] == "deadline" and c.get("weight_pct") for c in item["claims"])
                or re.search(r"\b(required|requires|submission|submit|due)\b",
                             claim.get("quote", ""), re.I))


def d3_rubric_gaps(items, docs, today, next_deadline=None):
    tracker_rows = []
    for d in docs.values():
        if d.get("kind") == "tracker":
            for line in d["lines"]:
                first = line["text"].split(" | ")[0].strip("- ").strip()
                if first and first.lower() not in ("task",):
                    tracker_rows.append(norm_hint(first))
    covered = lambda name, cut: any(fuzz.token_set_ratio(norm_hint(name), row) >= cut for row in tracker_rows)

    out = []
    claims = [c for it in items for c in it["claims"]]
    for d in (c for c in claims if c["kind"] == "deadline" and c.get("components")):
        if d["_date"] and d["_date"] < today:
            continue
        for comp in d["components"]:
            if covered(comp["name"], 65):
                continue
            stakes = round(d["weight_pct"] * comp["weight_pct"] / 100, 2)
            days = (d["_date"] - today).days if d["_date"] else None
            out.append(finding("D3", None, {
                "component": comp["name"], "weight_pct": comp["weight_pct"], "milestone": d["deliverable"],
                "milestone_due": iso(d["_date"]), "stakes_pct": stakes},
                [d["id"]], "med", "graded in the brief; no matching row in the task list (fuzzy match)",
                days, stakes=stakes, talk_first=False))
    for it in items:
        for c in it["claims"]:
            artifact = c.get("artifact") or c.get("item_hint")
            if submission_requirement(c, it) and not covered(artifact, 80):
                due = it["milestone_date"] or it["due"] or next_deadline
                if due and due < today:
                    continue
                # Unknown dates must not get the maximum urgency of "due today".
                days = (due - today).days if due else None
                out.append(finding("D3", it, {
                    "component": artifact, "penalty_points": c.get("penalty_points"),
                    "milestone": it["milestone"], "milestone_due": iso(due)},
                    [c["id"]], "high", "required by the brief; nowhere in the task list", days))
    return out


def d4_disagree(items, today, next_deadline):
    out = []
    for it in items:
        cl = it["claims"]
        days = ((it["due"] or next_deadline) - today).days if (it["due"] or next_deadline) else 0

        # Dates
        by_date = {}
        for c in cl:
            if c["_date"] and c["kind"] in ("task", "status", "question", "deadline"):
                by_date.setdefault(c["_date"], []).append(c)
        if len(by_date) > 1:
            brief = [d for d, cs in by_date.items() if any(c["_doc_kind"] == "brief" for c in cs)]
            trust = brief[0] if brief else max(by_date, key=lambda d: max(recency(c) for c in by_date[d]))
            out.append(finding("D4", it, {
                "field": "date", "sides": [{"says": iso(d), "claims": [c["id"] for c in cs]} for d, cs in by_date.items()],
                "trust": iso(trust), "why": "the course brief is the authority on course dates" if brief
                else "newest dated source"},
                [c["id"] for cs in by_date.values() for c in cs], "high" if brief else "med",
                "brief settles it" if brief else "newest source wins; check with the team",
                (trust - today).days))

        # Owners
        by_owner = {}
        for c in cl:
            if c["kind"] in TASKY | {"decision"} and c.get("who"):
                by_owner.setdefault(tuple(c["who"]), []).append(c)
        if len(by_owner) > 1:
            out.append(finding("D4", it, {
                "field": "owner", "sides": [{"says": list(o), "claims": [c["id"] for c in cs]} for o, cs in by_owner.items()],
                "trust": None, "why": "same work listed under different owners"},
                [c["id"] for cs in by_owner.values() for c in cs], "med",
                "two names for what looks like the same work", days,
                people=[p for o in by_owner for p in o], talk_first=True))

        # Only an explicit done decision conflicts with ongoing task progress.
        # A tentative date/assignment with status=open is not a disagreement.
        decisions = [c for c in cl if c["kind"] == "decision" and c.get("status") == "done"]
        stale = [c for c in cl if c["kind"] in ("task", "status")
                 and c.get("status") in ("open", "in_progress")]
        if decisions and stale:
            newest = newest_status(cl)
            trust_decision = newest["kind"] == "decision"
            out.append(finding("D4", it, {
                "field": "status", "sides": [{"says": "decided", "claims": [c["id"] for c in decisions]},
                                             {"says": "in progress", "claims": [c["id"] for c in stale]}],
                "trust": "decision" if trust_decision else newest["status"],
                "why": "a recorded decision beats a stale tracker row" if trust_decision
                else "newer task progress supersedes an older decision",
                "status_from": newest["id"]},
                [*(c["id"] for c in decisions + stale), newest["id"]],
                "high", "newest dated status evidence", days))
    return out


def d5_unowned_undated(items, today, next_deadline):
    out = []
    for it in items:
        tasks = [c for c in it["claims"] if c["kind"] in TASKY]
        if not tasks or it["status"] == "done":
            continue
        missing = []
        if not it["owner"] and not it["team_owned"]:
            missing.append("owner")
        if not it["due"]:
            missing.append("date")
        if not missing:
            continue
        ref = it["due"] or next_deadline
        out.append(finding("D5", it, {"missing": missing, "due": iso(it["due"]),
                                      "due_uncertain": it["due_uncertain"]},
                           [c["id"] for c in tasks], "high", "the task list has no " + " or ".join(missing),
                           (ref - today).days if ref else 0, talk_first="owner" in missing))
    return out


def d6_dependency(items, today):
    by_id = {it["item_id"]: it for it in items}
    out = []
    for it in items:
        for blocked_id, cid in it["blocks"]:
            blocked = by_id[blocked_id]
            if it["status"] == "done" or not blocked["due"]:
                continue
            days = (blocked["due"] - today).days
            if 0 <= days <= 7:
                dep = next(c for c in blocked["claims"] + it["claims"] if c["id"] == cid)
                out.append(finding("D6", it, {
                    "chain": [it["title"], blocked["title"]], "blocked_due": iso(blocked["due"]),
                    "slack_days": days},
                    [cid, *(c["id"] for c in it["claims"])], dep.get("extract_confidence", "med"),
                    f"'{blocked['title']}' waits on this", days, people=blocked["owner"]))
    return out


def d7_carried_question(items, today, next_deadline):
    out = []
    for it in items:
        raised = [c for c in it["claims"] if c["kind"] in ("question", "requirement")
                  and c.get("status") == "open" and c["_doc_kind"] == "notes"]
        meetings = {c["doc_id"] for c in raised}
        resolved = any(c["kind"] == "decision" or c.get("status") == "done" for c in it["claims"])
        if len(meetings) < 2 or resolved:
            continue
        ref = it["due"] or next_deadline
        first = min((c["_doc_date"] for c in raised if c["_doc_date"]), default=None)
        out.append(finding("D7", it, {"meetings_open": len(meetings), "first_raised": iso(first),
                                      "decide_by": iso(ref), "decide_by_basis": it["due_basis"]},
                           [c["id"] for c in raised], "med", f"raised in {len(meetings)} meetings, never settled",
                           (ref - today).days if ref else 0, talk_first=True))
    return out


def notice_hours(claim):
    """Use structured hours, or an explicit numeric hour duration in date_text.

    No default policy is invented when extraction omits this field.
    """
    hours = claim.get("hours")
    if isinstance(hours, (int, float)) and not isinstance(hours, bool) and hours > 0:
        return hours
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\s*",
                         claim.get("date_text") or "", re.I)
    return float(match[1]) if match and float(match[1]) > 0 else None


def d9_answered_by_brief(items, all_claims, today, next_deadline):
    ext = next((c for c in all_claims if c.get("rule") == "extension_notice"
                and c["_doc_kind"] == "brief"), None)
    out = []
    for it in items:
        # Unknown question status is unresolved, not answered. A later explicit
        # completion closes it; a bare decision about the item does not.
        resolved = [c for c in it["claims"] if c.get("status") == "done"
                    and c["kind"] in ("question", "task", "status", "decision")]
        questions = [c for c in it["claims"] if c["kind"] == "question"
                     and c.get("status") in ("open", "unknown", None)
                     and not any(recency(r) > recency(c) for r in resolved)]
        answers = [c for c in it["claims"] if c["_doc_kind"] == "brief" and c["kind"] in ("rule", "deadline")]
        if not questions or not answers:
            continue
        a = max(answers, key=recency)
        facts = {"question_claims": [q["id"] for q in questions], "answer_claim": a["id"]}
        receipts = [*facts["question_claims"], a["id"]]
        if a.get("rule") == "late_penalty":
            facts.update(pct_per_day=a.get("pct_per_day"), max_days=a.get("max_days"))
            if ext and next_deadline:
                hours = notice_hours(ext)
                if hours is not None:
                    cutoff = datetime.combine(next_deadline, datetime.min.time()).replace(hour=23, minute=59)
                    facts.update(extension_notice_hours=hours,
                                 extension_deadline=(cutoff - timedelta(hours=hours)).isoformat(timespec="minutes"))
                else:
                    facts["extension_notice_unresolved"] = True
                receipts.append(ext["id"])
        elif a["_date"]:
            facts.update(answer_date=iso(a["_date"]))
        days = (next_deadline - today).days if next_deadline else 0
        out.append(finding("D9", it, facts, receipts, "high", "the course brief answers this", days))
    return out


def compute_load(items, today, next_deadline):
    by_id = {it["item_id"]: it for it in items}
    load = {}
    for it in items:
        if it["status"] == "done":
            continue
        if it["due"] and next_deadline and it["due"] > next_deadline:
            continue
        for p in it["owner"]:
            load.setdefault(p, {"open_items": 0, "blocks_others": 0, "items": []})
            load[p]["open_items"] += 1
            load[p]["items"].append(it["item_id"])
        for blocked_id, _ in it["blocks"]:
            for p in it["owner"]:
                load.setdefault(p, {"open_items": 0, "blocks_others": 0, "items": []})
                load[p]["blocks_others"] += 1
    return load


def d8_load(load, items, today, next_deadline):
    if not load:
        return []
    median = statistics.median(v["open_items"] for v in load.values())
    out = []
    for person, v in load.items():
        if (v["open_items"] >= 3 and v["open_items"] >= 2 * median) or v["blocks_others"] >= 2:
            days = (next_deadline - today).days if next_deadline else 0
            by_id = {it["item_id"]: it for it in items}
            receipts = [c["id"] for i in v["items"] for c in by_id[i]["claims"]
                        if person in (c.get("who") or [])][:6]
            f = finding("D8", None, {"person": person, **v, "team_median": median}, receipts, "med",
                        "counts from the task list; they miss invisible work", days,
                        people=[person], talk_first=True, stakes=1.0)
            out.append(f)
    return out


# ---------------------------------------------------------------- main

def reconcile(claims: list[dict], docs: list[dict], today: date, project: str = "project",
              overrides: dict | None = None) -> dict:
    ctx = prepare_claims(claims, docs, today)
    groups = cluster(claims, overrides)
    items = build_items(groups, ctx, today)

    upcoming = [(name, d) for name, d in ctx["milestones"].items() if d >= today]
    if not upcoming:
        upcoming = [(c.get("deliverable") or c["item_hint"], c["_date"])
                    for c in claims if c["kind"] == "deadline" and c.get("weight_pct")
                    and c["_date"] and c["_date"] >= today]
    next_name, next_deadline = min(upcoming, key=lambda x: x[1]) if upcoming else (None, None)
    away, weekly = availability_blocks(claims)
    load = compute_load(items, today, next_deadline)

    findings = (d1_lead_time(items, away, weekly, today)
                + d10_event_clash(items, weekly, today)
                + d2_owner_unavailable(items, away, today, next_deadline)
                + d3_rubric_gaps(items, ctx["docs"], today, next_deadline)
                + d4_disagree(items, today, next_deadline)
                + d5_unowned_undated(items, today, next_deadline)
                + d6_dependency(items, today)
                + d7_carried_question(items, today, next_deadline)
                + d9_answered_by_brief(items, claims, today, next_deadline)
                + d8_load(load, items, today, next_deadline))
    findings.sort(key=lambda f: f["score"], reverse=True)
    for n, f in enumerate(findings, 1):
        f["id"] = f"f{n:02d}"

    people = sorted({p for c in claims for p in (c.get("who") or [])}
                    | {c["person"] for c in claims if c.get("person")})
    return {
        "project": project, "today": iso(today),
        "next_deadline": {"name": next_name, "date": iso(next_deadline),
                          "days": (next_deadline - today).days if next_deadline else None},
        "people": people,
        "items": [{
            "item_id": it["item_id"], "title": it["title"], "owner": it["owner"],
            "due": iso(it["due"]), "due_basis": it["due_basis"], "status": it["status"],
            "status_from": it["status_from"], "claims": [c["id"] for c in it["claims"]],
            "stakes_pct": it["stakes_pct"], "milestone": it["milestone"],
            "blocks": [b for b, _ in it["blocks"]], "blocked_by": [b for b, _ in it["blocked_by"]],
            "alias_merged": it["alias_merged"]} for it in items],
        "findings": findings,
        "load": load,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stage 03: claims -> scored findings")
    ap.add_argument("claims")
    ap.add_argument("docs")
    ap.add_argument("--today", required=True, type=date.fromisoformat)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--project", default=None)
    ap.add_argument("--items-map", default=None,
                    help="optional JSON {claim_id: item_key} to fix clustering by hand")
    args = ap.parse_args(argv)

    claims, docs = load_jsonl(args.claims), load_jsonl(args.docs)
    parent = Path(args.claims).resolve().parent.name
    project = args.project or (parent.split("@")[0] if "@" in parent else "project")
    overrides = json.loads(Path(args.items_map).read_text()) if args.items_map else None

    result = reconcile(claims, docs, args.today, project, overrides)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    items_map = {it["item_id"]: {"title": it["title"], "claims": it["claims"]} for it in result["items"]}
    (out.parent / "items_map.json").write_text(json.dumps(items_map, indent=2))

    nd = result["next_deadline"]
    print(f"{result['project']} @ {result['today']} · next: {nd['name']} {nd['date']} ({nd['days']} days) · "
          f"{len(result['items'])} items · {len(result['findings'])} findings")
    for f in result["findings"][:5]:
        print(f"  {f['score']:.3f}  {f['detector']}  {f['item_title']:<28}  "
              f"conf={f['confidence']['level']:<4}  days={str(f['days_left']):<3}  {json.dumps(f['facts'])[:110]}")


if __name__ == "__main__":
    main()
