"""Stage 02: read each document and emit typed claims with verbatim quotes.

Usage:
    uv run python stages/02_extract/extract.py runs/team4@2026-10-21/01_docs.jsonl -o runs/team4@2026-10-21/02_claims.jsonl

One roster call first (who is on the team, and their aliases), then one call per document,
run in parallel. Every quote is checked against its source line in code; claims that fail
are dropped and written to 02_dropped.jsonl next to the output so a human can see them.
Responses are cached in .cache/extract/ by content hash, so reruns are free and work offline.

Env: RECEIPTS_MODEL (default claude-opus-5-5), RECEIPTS_EFFORT (default medium).
"""
import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "extract"

# Load KEY=value lines from the repo's .env (gitignored) without overriding the real environment.
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))
MODEL = os.environ.get("RECEIPTS_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("RECEIPTS_EFFORT", "medium")
PROMPT_VERSION = "v1"  # bump to invalidate the cache after a prompt change

KINDS = ["task", "deadline", "decision", "status", "availability", "rule",
         "question", "dependency", "requirement", "person"]
RULES = ["lead_time", "late_penalty", "extension_notice", "week_anchor", "event_by"]
WEEKDAYS = ["M", "T", "W", "Th", "F", "Sa", "Su"]


def nullable(t):
    return {"type": [t, "null"]}


CLAIM_SCHEMA = {
    "type": "object",
    "properties": {
        "loc": {"type": "string"},
        "kind": {"type": "string", "enum": KINDS},
        "item_hint": {"type": "string"},
        "who_raw": nullable("string"),
        "who": {"type": "array", "items": {"type": "string"}},
        "date_text": {"type": "string"},
        "status": {"type": "string", "enum": ["open", "in_progress", "done", "unknown"]},
        "quote": {"type": "string"},
        "extract_confidence": {"type": "string", "enum": ["high", "med", "low"]},
        # kind-specific fields; null when they don't apply
        "rule": {"type": ["string", "null"], "enum": RULES + [None]},
        "rule_days": nullable("integer"),
        "hours": nullable("integer"),
        "pct_per_day": nullable("number"),
        "max_days": nullable("integer"),
        "week1_monday": nullable("string"),
        "applies_to": nullable("string"),
        "event": nullable("string"),
        "deliverable": nullable("string"),
        "weight_pct": nullable("number"),
        "components": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "weight_pct": {"type": "number"}},
            "required": ["name", "weight_pct"], "additionalProperties": False}},
        "artifact": nullable("string"),
        "penalty_points": nullable("number"),
        "person": nullable("string"),
        "away_from": nullable("string"),
        "away_to": nullable("string"),
        "weekly_days": {"type": "array", "items": {"type": "string", "enum": WEEKDAYS}},
        "busy_from": nullable("string"),
        "busy_to": nullable("string"),
        "blocked": nullable("string"),
        "blocked_by": nullable("string"),
    },
}
CLAIM_SCHEMA["required"] = list(CLAIM_SCHEMA["properties"])
CLAIM_SCHEMA["additionalProperties"] = False
CLAIMS_SCHEMA = {"type": "object", "properties": {"claims": {"type": "array", "items": CLAIM_SCHEMA}},
                 "required": ["claims"], "additionalProperties": False}

ROSTER_SCHEMA = {"type": "object", "properties": {"people": {"type": "array", "items": {
    "type": "object",
    "properties": {"name": {"type": "string"}, "role": {"type": "string"},
                   "aliases": {"type": "array", "items": {"type": "string"}}},
    "required": ["name", "role", "aliases"], "additionalProperties": False}}},
    "required": ["people"], "additionalProperties": False}

EXTRACT_RULES = """You extract claims from ONE document belonging to a student project team. Another program
reconciles claims across documents and does all date math, so your only job is faithful extraction.

Each line of the document is shown as `[loc] text`. For every claim:
- `loc` is the bracketed location of the line the claim comes from.
- `quote` MUST be copied character-for-character from that one line: a short exact substring, never
  paraphrased, never spanning two lines. Claims whose quote is not an exact substring are discarded.
- `date_text` is the date or timing exactly as written ("9/19", "ASAP", "wk 10", "Thursday the 29th",
  "this week"); empty string if none. Never convert or compute dates.
- `who` holds canonical full names from the roster; map nicknames, initials and first names. Use []
  when nobody owns it ("?", blank, "everyone" is []). `who_raw` is the name as written, or null.
- `item_hint` is a short noun phrase naming the piece of work. When the claim is about an item in the
  KNOWN ITEMS list, reuse that exact phrase so claims from different documents line up. That applies
  to rules too: a rule about requesting sponsor meetings belongs to the item for scheduling the demo.
- Set every field that does not apply to null (or [] for lists).

Kinds:
- task: work someone does (owner, due date, status). status: done | in_progress | open | unknown.
- status: a report on progress of an existing item ("hasn't emailed yet" = open; "finished" = done).
- decision: something the team decided ("DECISION: ...", "we agreed").
- question: an open question, TBD, "need to ask", "double check", "not decided".
- dependency: "can't do X until Y" -> blocked = X, blocked_by = Y.
- requirement: something the work must include or a required artifact (`artifact`, `penalty_points`).
- deadline: a graded or dated deliverable from a course or client brief: `deliverable`, `weight_pct`,
  and rubric `components` with their weights.
- rule: a policy with numbers. rule = lead_time (rule_days = notice days, applies_to), late_penalty
  (pct_per_day, max_days), extension_notice (hours), week_anchor (week1_monday as YYYY-MM-DD),
  event_by (event = what must happen, date_text = by when).
- availability: when someone is away (away_from/away_to as YYYY-MM-DD) or busy weekly
  (weekly_days using M T W Th F Sa Su, busy_from/busy_to as 24h HH:MM). Record ONLY the constraint.
  Never record the reason (trips, family, health, jobs, commutes) in any field, including item_hint.
  Keep the quote to the dates or times themselves.
- person: someone joining or leaving the team, or a role change.

Extract every claim a teammate would need to know where the project stands. Skip pleasantries.
`extract_confidence` is low when you had to guess what the writer meant."""


def doc_text(doc, limit=None):
    lines = doc["lines"][:limit] if limit else doc["lines"]
    return "\n".join(f"[{l['loc']}] {l['text']}" for l in lines)


def call(client, system, user, schema, cache_key):
    path = CACHE / f"{cache_key}.json"
    if path.exists():
        return json.loads(path.read_text())
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        cache_control={"type": "ephemeral"},
        system=system,
        output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": user}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"model declined ({response.stop_details}); request id {response._request_id}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("hit max_tokens; split the document")
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data


def key(*parts):
    return hashlib.sha256(json.dumps([MODEL, EFFORT, PROMPT_VERSION, *parts], sort_keys=True).encode()).hexdigest()[:24]


def get_roster(client, docs):
    # The first lines of every document are enough to find who is on the team.
    sample = "\n\n".join(f"=== {d['file']} ===\n{doc_text(d, 40)}" for d in docs)
    system = ("List the members of this project team: canonical full name, role, and every alias "
              "used in the documents (first names, nicknames, initials, 'Ty', 'PR', 'KA', 'Tyler B.'). "
              "Include only team members, not clients or instructors.")
    return call(client, system, sample, ROSTER_SCHEMA, key("roster", sample))["people"]


def known_items(docs):
    """First column of every tracker row, so claims from notes can reuse the tracker's names."""
    items = []
    for d in docs:
        if d["kind"] == "tracker":
            for line in d["lines"]:
                cells = [c.strip() for c in line["text"].split(" | ")]
                first = cells[0]
                if sum(1 for c in cells if c) < 2 or first.lower() in {"task", "tasks", "item", "to do", "todo"}:
                    continue  # title row or header row
                if first and not first.startswith("---"):
                    items.append(first)
    return items


def tidy(raw, doc):
    """Drop nulls/empties and map schema-only field names onto the shared schema names."""
    c = {k: v for k, v in raw.items() if v not in (None, [], "") or k in ("who", "date_text", "who_raw")}
    if "rule_days" in c:
        c["days"] = c.pop("rule_days")
    if "weekly_days" in c:
        c["days"] = c.pop("weekly_days")
        c["from"], c["to"] = c.pop("busy_from", None), c.pop("busy_to", None)
    c.setdefault("who_raw", None)
    return {"doc_id": doc["doc_id"], **c}


def check_quote(claim, doc):
    """Keep the claim if its quote is on its line; repair the loc if the quote is on another line."""
    lines = {l["loc"]: l["text"] for l in doc["lines"]}
    if claim["quote"] and claim["quote"] in lines.get(claim["loc"], ""):
        return claim
    for loc, text in lines.items():
        if claim["quote"] and claim["quote"] in text:
            return {**claim, "loc": loc, "loc_repaired": True}
    return None


def extract_doc(client, doc, roster, items):
    system = [
        {"type": "text", "text": EXTRACT_RULES},
        {"type": "text", "text": "ROSTER:\n" + json.dumps(roster) + "\n\nKNOWN ITEMS:\n" + "\n".join(items)},
    ]
    user = (f"Document: {doc['file']} (kind: {doc['kind']}, dated {doc['doc_date'] or 'unknown'}, "
            f"author {doc['author'] or 'unknown'})\n\n{doc_text(doc)}")
    data = call(client, system, user, CLAIMS_SCHEMA, key("doc", system, user))
    kept, dropped = [], []
    for raw in data["claims"]:
        claim = check_quote(tidy(raw, doc), doc)
        (kept if claim else dropped).append(claim or tidy(raw, doc))
    return kept, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docs", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    args = ap.parse_args()

    docs = [json.loads(l) for l in args.docs.read_text().splitlines() if l.strip()]
    client = anthropic.Anthropic()
    roster = get_roster(client, docs)
    items = known_items(docs)
    print(f"roster: {', '.join(p['name'] for p in roster)}; {len(items)} known items", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda d: extract_doc(client, d, roster, items), docs))

    claims, dropped = [], []
    for doc, (kept, lost) in zip(docs, results):
        claims += kept
        dropped += lost
        print(f"  {doc['doc_id']} {doc['file']}: {len(kept)} claims, {len(lost)} dropped", file=sys.stderr)
    for n, c in enumerate(claims, 1):
        c["id"] = f"c{n:03d}"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(c) + "\n" for c in claims))
    (args.out.parent / "02_dropped.jsonl").write_text("".join(json.dumps(c) + "\n" for c in dropped))
    print(f"wrote {len(claims)} claims to {args.out} ({len(dropped)} dropped, see 02_dropped.jsonl)", file=sys.stderr)


if __name__ == "__main__":
    main()
