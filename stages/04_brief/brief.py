"""Stage 04: turn ranked findings into the ten-second board.

Usage:
    python stages/04_brief/brief.py runs/team4@2026-10-28 [--prev runs/team4@2026-10-21]

Reads 03_findings.json, 02_claims.jsonl and 01_docs.jsonl from the run folder and writes
04_brief.json and 04_board.html next to them. Every date, count and number comes from stage 03's
facts; sentences are filled from fixed templates (no AI call), and every card cites its claims.
Availability quotes are never printed (they can name reasons); the receipt shows file and line only.
"""
import argparse
import datetime as dt
import difflib
import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = Path(__file__).resolve().parent
TOP_DETECTORS = {"D1", "D2", "D5", "D6", "D7", "D8", "D10"}  # D3/D4/D9 have their own sections
TIER = {"D1": 0, "D2": 0, "D10": 0, "D6": 1, "D7": 1, "D5": 2, "D8": 2}
CONF_DOTS = {"high": "●●●", "med": "●●○", "medium": "●●○", "low": "●○○"}
CONF_WORD = {"high": "High", "med": "Medium", "medium": "Medium", "low": "Low"}


# ---------------------------------------------------------------- small helpers

def d(iso):
    return dt.date.fromisoformat(iso[:10]) if iso else None


def day_label(iso):
    x = d(iso)
    return f"{x:%a} {x:%b} {x.day}" if x else "no date"


def rel_label(iso, today):
    x = d(iso)
    if not x:
        return "no date"
    n = (x - today).days
    when = {0: "today", 1: "tomorrow", -1: "yesterday"}.get(n, f"in {n} days" if n > 0 else f"{-n} days ago")
    return f"{day_label(iso)} · {when}"


def first(name):
    return (name or "").split()[0] if name else ""


def cap(text):
    return text[:1].upper() + text[1:] if text else text


def short(text, words=10):
    parts = (text or "").split()
    return " ".join(parts[:words])


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


# ---------------------------------------------------------------- receipts

def doc_label(doc):
    kind = doc.get("kind")
    if kind == "brief":
        return "Brief"
    if kind == "tracker":
        return "Task list" + (f" ({day_label(doc['doc_date'])})" if doc.get("doc_date") else "")
    if kind == "availability":
        return "Availability"
    if kind == "notes":
        when = day_label(doc["doc_date"]) if doc.get("doc_date") else Path(doc["file"]).stem
        return f"Notes {when}" + (f" · {doc['author']}" if doc.get("author") else "")
    return Path(doc["file"]).name


def receipts_for(claim_ids, claims, docs, limit=4):
    out, seen = [], set()
    for cid in claim_ids:
        c = claims.get(cid)
        if not c or (c["doc_id"], c["loc"]) in seen:
            continue
        seen.add((c["doc_id"], c["loc"]))
        doc = docs.get(c["doc_id"], {"file": c["doc_id"]})
        private = c.get("quote_private") or c.get("kind") == "availability"
        out.append({"label": f"{doc_label(doc)} · {c['loc']}", "file": doc.get("file"), "loc": c["loc"],
                    "quote": None if private else c["quote"], "private": bool(private)})
        if len(out) == limit:
            break
    return out


# ---------------------------------------------------------------- card templates

def card_text(f, today):
    """(action, owner, date, reason, note) for one finding, from its facts only."""
    x, title, who = f["facts"], f.get("item_title") or "this item", f.get("people") or []
    owner = ", ".join(first(p) for p in who) or "Team"
    if f["detector"] == "D1":
        others = []
        for k in x.get("constraints_on_event_day", []):
            if k.get("away_from"):
                others.append(f"{first(k['person'])} away {day_label(k['away_from'])}–{day_label(k['away_to'])}")
            elif k.get("busy_from"):
                others.append(f"{first(k['person'])} busy {k['busy_from']}–{k['busy_to']} that day")
        others = list(dict.fromkeys(others))
        return (cap(title), owner, x["latest_action"],
                f"Needs {x['lead_days']} days' notice and must happen by {day_label(x['event_by'])}; still {x.get('status', 'open')}.",
                "; ".join(others))
    if f["detector"] == "D10":
        event = title.split(" ", 1)[1] if title.split(" ", 1)[0].lower() in {"schedule", "book", "plan", "hold", "run", "submit"} else title
        return (f"Confirm who runs {event}", "Whole team", x["act_by"],
                f"It's {day_label(x['event_date'])} at {x['event_time']}; {first(x['person'])} is busy "
                f"{x['busy_from']}–{x['busy_to']} that day.", "")
    if f["detector"] == "D2" and d(x["finish_by"]) < today:
        return (f"Find a new owner for {title}", "Whole team", today.isoformat(),
                f"{first(x['owner'])} is away {day_label(x['away_from'])}–{day_label(x['away_to'])} "
                f"and the work is still open.", "")
    if f["detector"] == "D2":
        return (f"Finish {title} before {first(x['owner'])} is away", first(x["owner"]), x["finish_by"],
                f"{first(x['owner'])} is away {day_label(x['away_from'])}–{day_label(x['away_to'])}; "
                f"{x.get('slack_days', '?')} working days left.", "")
    if f["detector"] == "D6":
        return (f"Settle {title}", owner, x.get("blocked_due"),
                f"'{x['chain'][-1]}' waits on it and is due {day_label(x.get('blocked_due'))}.", "")
    if f["detector"] == "D7":
        return (f"Decide {title}", "Whole team", x.get("decide_by"),
                f"Raised in {x['meetings_open']} meetings since {day_label(x.get('first_raised'))} without a decision.", "")
    if f["detector"] == "D5":
        missing = " and ".join(x.get("missing", [])) or "owner"
        return (f"Pick an {missing} for {title}" if missing == "owner" else f"Set a {missing} for {title}",
                owner, x.get("due"), f"The task list has no {missing} for it.", "")
    if f["detector"] == "D8":
        return ("Check in on workload this week", "Whole team", None,
                f"{first(x['person'])} holds {x['open_items']} open items; the team median is {x['team_median']}.", "")
    return (cap(title), owner, None, x.get("why", ""), "")


def make_card(rank, group, claims, docs, today):
    lead = group[0]
    action, owner, date, reason, note = card_text(lead, today)
    ids = [cid for f in group for cid in f.get("receipts", [])]
    conf = lead["confidence"]
    return {"rank": rank, "action": short(action), "owner": owner, "date": date,
            "date_label": rel_label(date, today) if date else "this week", "reason": reason, "note": note,
            # 0.5 is stage 03's "weight unknown" default, so only show stakes the brief actually states.
            "stakes": f"{lead['stakes_pct']:g} pts of course grade at stake" if (lead.get("stakes_pct") or 0) > 0.5 else "",
            "confidence": {"level": conf["level"], "word": CONF_WORD.get(conf["level"], conf["level"]),
                           "dots": CONF_DOTS.get(conf["level"], "●○○"), "why": conf.get("why", "")},
            "talk_first": any(f.get("talk_first") for f in group),
            "detectors": sorted({f["detector"] for f in group}), "item_id": lead.get("item_id"),
            "item_title": lead.get("item_title"),
            "receipts": receipts_for(ids, claims, docs)}


# ---------------------------------------------------------------- sections

def disagreement(f, claims, docs):
    x = f["facts"]
    sides = []
    for s in x.get("sides", []):
        says = ", ".join(first(v) for v in s["says"]) if isinstance(s["says"], list) else str(s["says"])
        if len(says) == 10 and says[4] == "-" and says[7] == "-":
            says = day_label(says)
        sides.append({"says": says, "receipts": receipts_for(s.get("claims", []), claims, docs, limit=2)})
    trust = x.get("trust")
    if trust == "decision":
        trust = "The recorded decision"
    elif isinstance(trust, str) and len(trust) >= 10 and trust[4] == "-":
        trust = day_label(trust)
    elif isinstance(trust, list):
        trust = ", ".join(first(t) for t in trust)
    return {"topic": f"{cap(f.get('item_title') or '')}: {x.get('field', 'details')}", "sides": sides,
            "trust": str(trust) if trust else "Ask the team", "why": x.get("why", ""),
            "confidence": CONF_WORD.get(f["confidence"]["level"], "")}


def missing(f, claims, docs):
    x = f["facts"]
    if x.get("penalty_points"):
        impact = f"−{x['penalty_points']:g} points if missing"
    elif x.get("weight_pct"):
        impact = f"{x['weight_pct']:g}% of {(x.get('milestone') or 'the milestone').split()[0]}"
    else:
        impact = "required by the brief"
    return {"item": x.get("component") or f.get("item_title"), "impact": impact,
            "due": day_label(x.get("milestone_due")) if x.get("milestone_due") else "",
            "receipts": receipts_for(f.get("receipts", []), claims, docs, limit=1)}


def answered(f, claims, docs):
    x = f["facts"]
    q = claims.get((x.get("question_claims") or [None])[0], {})
    parts = []
    if x.get("pct_per_day"):
        parts.append(f"{x['pct_per_day']:g}% off per day late" + (f", up to {x['max_days']} days" if x.get("max_days") else ""))
    if x.get("extension_deadline"):
        parts.append(f"extension requests must arrive by {day_label(x['extension_deadline'])}, "
                     f"{x['extension_deadline'][11:16] or '23:59'} ({x.get('extension_notice_hours', 48)}h notice)")
    for k, v in x.items():  # any other dated answer, e.g. the brief's due date for the asked-about item
        if isinstance(v, str) and len(v) >= 10 and v[4:5] == "-" and k != "extension_deadline":
            parts.append(f"the brief says {day_label(v)}")
    receipts = receipts_for([x.get("answer_claim")], claims, docs, limit=1)
    if not parts and receipts and receipts[0]["quote"]:
        parts.append(f"the brief says: “{receipts[0]['quote']}”")
    return {"question": q.get("quote", f.get("item_title")), "answer": cap("; ".join(parts)) + ".",
            "receipts": receipts}


def question_text(f):
    x, title = f["facts"], f.get("item_title") or "this"
    if f["detector"] == "D7":
        return f"{cap(title)} has come up in {x['meetings_open']} meetings. Can we decide it now?"
    if f["detector"] == "D5":
        return f"Who takes {title}?" if "owner" in x.get("missing", []) else f"When is {title} due?"
    if f["detector"] == "D8":
        return f"{first(x['person'])} has {x['open_items']} open items. Can anyone take one?"
    if f["detector"] == "D4":
        return f"Two sources disagree about {title}. Which is right?"
    return f"Talk through {title}."


def current(finding, items_by_id, today):
    """A disagreement about work that was due before today is history; keep the board on this week."""
    due = (items_by_id.get(finding.get("item_id")) or {}).get("due")
    return not due or d(due) >= today


def questions(findings, top_items):
    """One talk-first question per item not already on a top card."""
    out, seen = [], set(top_items)
    for x in findings:
        key = x.get("item_id") or x["id"]
        if x.get("talk_first") and key not in seen and x["detector"] != "D4":
            seen.add(key)
            out.append({"text": question_text(x), "talk_first": True})
    return out[:4]


def since_last(prev_dir, items_now, claims, docs):
    prev_path = prev_dir / "04_brief.json"
    if not prev_path.exists():
        return None
    prev = json.loads(prev_path.read_text())
    # Item ids are per-run, so match last run's cards to this run's items by any name the item goes by.
    by_title = {}
    for i in items_now:
        for name in [i["title"], *(claims[c]["item_hint"] for c in i["claims"] if c in claims)]:
            by_title.setdefault(name.lower(), i)
    flagged = []
    for card in prev.get("top", []):
        name = (card.get("item_title") or card["action"]).lower()
        close = difflib.get_close_matches(name, list(by_title), n=1, cutoff=0.6)
        item = by_title.get(name) or (by_title[close[0]] if close else None)
        status = item["status"] if item else "unknown"
        latest = receipts_for([item["status_from"]], claims, docs, 1) if item and item.get("status_from") else []
        flagged.append({"was": card["action"], "by": day_label(card.get("date")) if card.get("date") else "",
                        "owner": card.get("owner"),
                        "now": {"done": "Done", "in_progress": "In progress", "open": "Still open"}.get(status, cap(status)),
                        "receipts": latest})
    return {"prev_today": prev.get("today"), "prev_label": day_label(prev.get("today")), "flagged": flagged}


# ---------------------------------------------------------------- main

def build(run_dir: Path, prev_dir: Path | None):
    f = json.loads((run_dir / "03_findings.json").read_text())
    claims = {c["id"]: c for c in load_jsonl(run_dir / "02_claims.jsonl")}
    docs = {x["doc_id"]: x for x in load_jsonl(run_dir / "01_docs.jsonl")}
    today = d(f["today"])
    findings = sorted(f["findings"], key=lambda x: -x["score"])

    # Merge findings on the same item into one card, ranked by the item's best finding.
    groups, order = {}, []
    for x in findings:
        if x["detector"] not in TOP_DETECTORS:
            continue
        key = x.get("item_id") or x["id"]
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(x)
    # Hard deadlines first, then blocked decisions, then missing owners/dates; score breaks ties.
    # A card without a receipt never reaches the board (every line must cite its source).
    order = [k for k in order if any(x.get("receipts") for x in groups[k])]
    order.sort(key=lambda k: min(TIER[x["detector"]] for x in groups[k]))
    cards = [make_card(n, groups[k], claims, docs, today) for n, k in enumerate(order, 1)]
    top, also = cards[:3], cards[3:6]
    top_items = {c["item_id"] for c in top}

    items_by_id = {i["item_id"]: i for i in f["items"]}
    nd = f.get("next_deadline") or {}
    return {
        "project": run_dir.name.split("@")[0], "today": f["today"],
        "today_label": f"{today:%A}, {today:%B} {today.day}",
        "countdown": {"label": f"{nd['name']} due {day_label(nd['date'])}", "days": nd["days"]} if nd.get("date") else None,
        "top": top, "also": also,
        "disagreements": [disagreement(x, claims, docs) for x in findings
                          if x["detector"] == "D4" and current(x, items_by_id, today)][:5],
        "missing": [missing(x, claims, docs) for x in findings if x["detector"] == "D3"][:5],
        "answered": [answered(x, claims, docs) for x in findings if x["detector"] == "D9"][:3],
        "questions": questions(findings, top_items),
        "load": {"note": "Counts aren't contribution. Use this to start a conversation, not to judge one.",
                 "people": [{"name": first(n), "open_items": v.get("open_items", 0), "blocks": v.get("blocks_others", 0)}
                            for n, v in sorted((f.get("load") or {}).items())]},
        "since_last": since_last(prev_dir, f["items"], claims, docs) if prev_dir else None,
        "counts": {"docs": len(docs), "claims": len(claims), "findings": len(findings)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--prev", type=Path)
    args = ap.parse_args()

    brief = build(args.run_dir, args.prev)
    (args.run_dir / "04_brief.json").write_text(json.dumps(brief, indent=2))
    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape())
    max_load = max([p["open_items"] for p in brief["load"]["people"]] or [1]) or 1
    html = env.get_template("board.html.j2").render(b=brief, max_load=max_load)
    (args.run_dir / "04_board.html").write_text(html)
    print(f"wrote {args.run_dir / '04_board.html'}: {len(brief['top'])} cards, "
          f"{len(brief['disagreements'])} disagreements, {len(brief['missing'])} missing", file=sys.stderr)


if __name__ == "__main__":
    main()
