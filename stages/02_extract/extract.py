"""Stage 02: read each document and emit typed claims with verbatim quotes.

Usage:
    uv run python stages/02_extract/extract.py runs/team4@2026-10-21/01_docs.jsonl -o runs/team4@2026-10-21/02_claims.jsonl

One roster call first (who is on the team, and their aliases), then one call per document,
run in parallel. Every quote is checked against its source line in code; claims that fail
are dropped and written to 02_dropped.jsonl next to the output so a human can see them.
Responses are cached in .cache/extract/ by content hash, so reruns are free and work offline.

Env: RECEIPTS_PROVIDER = local (default) | anthropic.
  local:     any OpenAI-compatible server (vLLM, llama.cpp, Ollama) at RECEIPTS_BASE_URL, with
             RECEIPTS_API_KEY if it needs one; RECEIPTS_MODEL defaults to the first model it serves.
  anthropic: ANTHROPIC_API_KEY or an `ant auth login` profile; RECEIPTS_MODEL (default claude-opus-5-5),
             RECEIPTS_EFFORT (default medium).
"""
import argparse
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "extract"

# Load KEY=value lines from the repo's .env (gitignored) without overriding the real environment.
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

PROVIDER = os.environ.get("RECEIPTS_PROVIDER", "local")
MODEL = os.environ.get("RECEIPTS_MODEL", "claude-opus-5-5" if PROVIDER == "anthropic" else "")
EFFORT = os.environ.get("RECEIPTS_EFFORT", "medium")
PROMPT_VERSION = "v1"  # bump to invalidate the cache after a prompt change

KINDS = ["task", "deadline", "decision", "status", "availability", "rule",
         "question", "dependency", "requirement", "person"]
RULES = ["lead_time", "late_penalty", "extension_notice", "week_anchor", "event_by"]
WEEKDAYS = ["M", "T", "W", "Th", "F", "Sa", "Su"]
RULE_HINTS = {"late_penalty": "late policy", "extension_notice": "extension request", "week_anchor": "course calendar"}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
MONTH_DAY = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})"
DAY_CODES = [(r"\bm(?:on)?\b", "M"), (r"\btu(?:e|es|esday)?\b", "T"), (r"\bw(?:ed)?\b", "W"),
             (r"\bth(?:u|ur|urs|ursday)?\b", "Th"), (r"\bf(?:ri)?\b", "F"), (r"\bsat\b", "Sa"), (r"\bsun\b", "Su")]


def derive_availability(c):
    """Fill away dates / weekly busy times from the claim's own text when the model left them empty.
    Years are corrected afterwards by fix_away_years."""
    text = f"{c.get('date_text', '')} {c.get('quote', '')}".lower()
    if not c.get("away_from"):
        dates = re.findall(MONTH_DAY, text)
        if dates:
            import dateparser
            parsed = [dateparser.parse(f"{m} {d}") for m, d in dates[:2]]
            if all(parsed):
                c["away_from"] = parsed[0].date().isoformat()
                c["away_to"] = parsed[-1].date().isoformat()
                return
    if not c.get("days") and not c.get("away_from"):
        after = re.search(r"after (\d{1,2})(?::(\d\d))?\s*(am|pm)?", text)
        span = re.search(r"(\d{1,2})(?::(\d\d))?\s*(am|pm)?\s*-\s*(\d{1,2})(?::(\d\d))?\s*(am|pm)", text)
        days = [code for pat, code in DAY_CODES if re.search(pat, text)]
        spans = re.findall(r"\d{1,2}(?::\d\d)?\s*(?:am|pm)?\s*-\s*\d{1,2}", text)
        if len(spans) > 1:
            return  # several day/time groups on one line ("M + W 4-9pm, Th 3-9pm"): too ambiguous to split
        if days and (after or span):
            def hhmm(h, m, ampm, default_pm=True):
                h = int(h) % 12 + (12 if (ampm == "pm" or (not ampm and default_pm)) else 0)
                return f"{h:02d}:{m or '00'}"
            c["days"] = days
            if after:
                c["from"], c["to"] = hhmm(after[1], after[2], after[3]), "23:59"
            else:
                c["from"], c["to"] = hhmm(span[1], span[2], span[3] or span[6]), hhmm(span[4], span[5], span[6])


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
# Only the core fields are required; kind-specific ones are omitted when they don't apply,
# which keeps the output short (a single local GPU generates ~17-38 tokens/s).
CLAIM_SCHEMA["required"] = ["loc", "kind", "item_hint", "who", "date_text", "status", "quote", "extract_confidence"]
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
- Leave out every optional field that does not apply to the claim's kind.

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


def make_client():
    if PROVIDER == "local":
        from openai import OpenAI
        if "RECEIPTS_BASE_URL" not in os.environ:
            sys.exit("set RECEIPTS_BASE_URL to an OpenAI-compatible server, or RECEIPTS_PROVIDER=anthropic")
        return OpenAI(base_url=os.environ["RECEIPTS_BASE_URL"], api_key=os.environ.get("RECEIPTS_API_KEY", "dummy"),
                      timeout=600, max_retries=1)
    import anthropic
    return anthropic.Anthropic()


def call(client, system, user, schema, cache_key):
    path = CACHE / f"{cache_key}.json"
    if path.exists():
        return json.loads(path.read_text())
    data = call_local(client, system, user, schema) if PROVIDER == "local" else call_claude(client, system, user, schema)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data


def call_local(client, system, user, schema):
    system_text = system if isinstance(system, str) else "\n\n".join(b["text"] for b in system)
    resp = client.chat.completions.create(
        model=MODEL or client.models.list().data[0].id,  # use whatever the server is serving
        messages=[{"role": "system", "content": system_text}, {"role": "user", "content": user}],
        max_tokens=12000,
        response_format={"type": "json_schema", "json_schema": {"name": "extraction", "schema": schema}},
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    choice = resp.choices[0]
    if choice.finish_reason != "stop":
        raise RuntimeError(f"local: finish_reason={choice.finish_reason}; split the document")
    return json.loads(choice.message.content)


def call_claude(client, system, user, schema):
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
    return json.loads(next(b.text for b in response.content if b.type == "text"))


def key(*parts):
    return hashlib.sha256(json.dumps([PROVIDER, MODEL, EFFORT, PROMPT_VERSION, *parts], sort_keys=True).encode()).hexdigest()[:24]


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
    c.setdefault("item_hint", c.get("kind", ""))  # never leave the clustering key out
    c["loc"] = c.get("loc", "").strip("[] ")
    if c.get("rule") == "week_anchor":
        # Stage 03 needs week1_monday as an ISO date. Reading an explicit calendar date is parsing,
        # not date math; anything that isn't a Monday is not a week-1 anchor and is dropped.
        import dateparser
        d = dateparser.parse(c.get("week1_monday") or c.get("date_text") or "")
        if not d or d.weekday() != 0:
            return None
        c["week1_monday"] = d.date().isoformat()
    if c.get("kind") == "deadline":
        # Keep the milestone code as written ("M3") in the deliverable name; stage 03 keys on it.
        code = re.search(r"\b[A-Z]{1,3}\d+\b", c.get("quote", ""))
        if code and code[0] not in c.get("deliverable", ""):
            c["deliverable"] = f"{code[0]} {c.get('deliverable', '')}".strip()
    if c.get("rule") == "late_penalty":
        # A late-penalty rule states a percentage; without one it's mislabeled, so drop the label.
        pct = re.search(r"(\d+(?:\.\d+)?)\s*%", c.get("quote", ""))
        if not pct:
            c.pop("rule")
        else:
            c["pct_per_day"] = float(pct[1])
            if "days" in c and "max_days" not in c:
                c["max_days"] = c.pop("days")
            up_to = re.search(r"up to (\w+) (?:calendar )?days", c["quote"], re.I)
            if up_to and "max_days" not in c:
                word = up_to[1].lower()
                c["max_days"] = int(word) if word.isdigit() else NUMBER_WORDS.get(word)
    if c.get("kind") == "availability":
        derive_availability(c)
    if c.get("rule") in RULE_HINTS:
        c["item_hint"] = RULE_HINTS[c["rule"]]  # course-wide rules aren't about one task
    if c.get("kind") == "availability":
        if not c.get("person") and len(c.get("who") or []) == 1:
            c["person"] = c["who"][0]
        # Constraints, never reasons: the hint is neutral, and the quote (which may name a reason)
        # is marked so the board cites the file and line without printing it.
        c["item_hint"] = "availability"
        c["quote_private"] = True
    return {"doc_id": doc["doc_id"], **c}


def check_quote(claim, doc):
    """Keep the claim if its quote is on its line; repair the loc if the quote is on another line."""
    lines = {l["loc"]: l["text"] for l in doc["lines"]}
    if claim["quote"] and claim["quote"] in lines.get(claim["loc"], ""):
        return claim
    for loc, text in lines.items():
        if claim["quote"] and claim["quote"] in text:
            return {**claim, "loc": loc, "loc_repaired": True}
    # PDF lines wrap, so a quote can run across consecutive lines. Keep the part on the first line;
    # it is still verbatim, and the claim's fields carry the full meaning.
    norm = " ".join(claim["quote"].split())
    locs = list(lines)
    for i, loc in enumerate(locs):
        joined = " ".join(" ".join(lines[l].split()) for l in locs[i:i + 4])
        start = joined.find(norm)
        first = " ".join(lines[loc].split())
        if norm and 0 <= start < len(first) - 15:
            part = first[start:]
            if part in lines[loc]:
                return {**claim, "loc": loc, "quote": part, "quote_trimmed": True}
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
        tidied = tidy(raw, doc)
        claim = check_quote(tidied, doc) if tidied else None
        (kept if claim else dropped).append(claim or {"doc_id": doc["doc_id"], **raw})
    return kept, dropped


def fix_away_years(claims, docs):
    """The model fills away_from/away_to as ISO dates and sometimes guesses the year. When the source
    text names no year, use the project's year (week-1 anchor, else the newest dated doc)."""
    anchor = next((c["week1_monday"] for c in claims if c.get("week1_monday")), None)
    dated = sorted(d["doc_date"] for d in docs if d.get("doc_date"))
    year = (anchor or (dated[-1] if dated else ""))[:4]
    if not year:
        return
    for c in claims:
        if c.get("kind") == "availability" and not re.search(r"\b(19|20)\d\d\b", c.get("quote", "")):
            for k in ("away_from", "away_to"):
                if re.match(r"^\d{4}-\d\d-\d\d$", c.get(k) or ""):
                    c[k] = year + c[k][4:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docs", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    args = ap.parse_args()

    docs = [json.loads(l) for l in args.docs.read_text().splitlines() if l.strip()]
    client = make_client()
    roster = get_roster(client, docs)
    items = known_items(docs)
    print(f"roster: {', '.join(p['name'] for p in roster)}; {len(items)} known items", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=4 if PROVIDER == "local" else 8) as pool:
        results = list(pool.map(lambda d: extract_doc(client, d, roster, items), docs))

    claims, dropped = [], []
    for doc, (kept, lost) in zip(docs, results):
        claims += kept
        dropped += lost
        print(f"  {doc['doc_id']} {doc['file']}: {len(kept)} claims, {len(lost)} dropped", file=sys.stderr)
    fix_away_years(claims, docs)
    for n, c in enumerate(claims, 1):
        c["id"] = f"c{n:03d}"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(c) + "\n" for c in claims))
    (args.out.parent / "02_dropped.jsonl").write_text("".join(json.dumps(c) + "\n" for c in dropped))
    print(f"wrote {len(claims)} claims to {args.out} ({len(dropped)} dropped, see 02_dropped.jsonl)", file=sys.stderr)


if __name__ == "__main__":
    main()
