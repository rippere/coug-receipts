"""Check a stage handoff file against _shared/schema.md.

Usage:
    python _shared/validate.py docs     runs/x/01_docs.jsonl
    python _shared/validate.py claims   runs/x/02_claims.jsonl [runs/x/01_docs.jsonl]
    python _shared/validate.py findings runs/x/03_findings.json
    python _shared/validate.py brief    runs/x/04_brief.json

Exits 0 when the file is a valid handoff, 1 otherwise. Standard library only.
"""
import json
import re
import sys
from pathlib import Path

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DOC_KINDS = {"brief", "notes", "tracker", "availability", "other"}
CLAIM_KINDS = {"task", "deadline", "decision", "status", "availability", "rule",
               "question", "dependency", "requirement", "person"}
STATUSES = {"open", "in_progress", "done", "unknown"}
LEVELS = {"high", "med", "medium", "low"}


def read_jsonl(path):
    rows = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{n}: not valid JSON ({e})")
    return rows


def need(obj, keys, where, errors):
    for k in keys:
        if k not in obj:
            errors.append(f"{where}: missing '{k}'")


def check_docs(path, errors):
    docs = read_jsonl(path)
    ids = set()
    for d in docs:
        where = f"doc {d.get('doc_id', '?')}"
        need(d, ["doc_id", "file", "kind", "doc_date", "author", "lines"], where, errors)
        if d.get("doc_id") in ids:
            errors.append(f"{where}: duplicate doc_id")
        ids.add(d.get("doc_id"))
        if d.get("kind") not in DOC_KINDS:
            errors.append(f"{where}: kind '{d.get('kind')}' not in {sorted(DOC_KINDS)}")
        if d.get("doc_date") is not None and not ISO.match(str(d["doc_date"])):
            errors.append(f"{where}: doc_date must be YYYY-MM-DD or null")
        for line in d.get("lines", []):
            if "loc" not in line or "text" not in line:
                errors.append(f"{where}: every line needs 'loc' and 'text'")
                break
    return f"{len(docs)} docs"


def check_claims(path, errors, docs_path=None):
    claims = read_jsonl(path)
    lines = {}
    if docs_path:
        for d in read_jsonl(docs_path):
            for line in d["lines"]:
                lines[(d["doc_id"], line["loc"])] = line["text"]
    ids = set()
    for c in claims:
        where = f"claim {c.get('id', '?')}"
        need(c, ["id", "doc_id", "loc", "kind", "item_hint", "who", "date_text",
                 "status", "quote", "extract_confidence"], where, errors)
        if c.get("id") in ids:
            errors.append(f"{where}: duplicate id")
        ids.add(c.get("id"))
        if c.get("kind") not in CLAIM_KINDS:
            errors.append(f"{where}: kind '{c.get('kind')}' not allowed")
        if c.get("status") not in STATUSES:
            errors.append(f"{where}: status '{c.get('status')}' not allowed")
        if c.get("extract_confidence") not in LEVELS:
            errors.append(f"{where}: extract_confidence must be high/med/low")
        if not isinstance(c.get("who", []), list):
            errors.append(f"{where}: 'who' must be a list")
        if docs_path:
            text = lines.get((c.get("doc_id"), c.get("loc")))
            if text is None:
                errors.append(f"{where}: no line at {c.get('doc_id')}/{c.get('loc')}")
            elif c.get("quote", "") not in text:
                errors.append(f"{where}: quote is not verbatim at {c.get('doc_id')}/{c.get('loc')}")
    return f"{len(claims)} claims" + (" (quotes checked)" if docs_path else "")


def check_findings(path, errors):
    f = json.loads(Path(path).read_text(encoding="utf-8"))
    need(f, ["project", "today", "next_deadline", "items", "findings"], "findings file", errors)
    if not ISO.match(str(f.get("today", ""))):
        errors.append("today must be YYYY-MM-DD")
    for x in f.get("findings", []):
        where = f"finding {x.get('id', '?')}"
        need(x, ["id", "detector", "facts", "people", "talk_first", "confidence",
                 "receipts", "score"], where, errors)
        if x.get("confidence", {}).get("level") not in LEVELS:
            errors.append(f"{where}: confidence.level must be high/med/low")
        if not x.get("receipts"):
            errors.append(f"{where}: no receipts (every finding needs at least one claim id)")
    return f"{len(f.get('items', []))} items, {len(f.get('findings', []))} findings"


def check_brief(path, errors):
    b = json.loads(Path(path).read_text(encoding="utf-8"))
    need(b, ["project", "today", "today_label", "countdown", "top", "disagreements",
             "missing", "questions", "load", "since_last"], "brief", errors)
    if len(b.get("top", [])) > 3:
        errors.append("top has more than 3 cards")
    for card in b.get("top", []):
        where = f"card #{card.get('rank', '?')}"
        need(card, ["rank", "action", "owner", "date", "date_label", "reason", "stakes",
                    "confidence", "talk_first", "receipts"], where, errors)
        if len(card.get("action", "").split()) > 10:
            errors.append(f"{where}: action is over 10 words")
        if not card.get("receipts"):
            errors.append(f"{where}: no receipts")
        if card.get("date") and not ISO.match(card["date"]):
            errors.append(f"{where}: date must be YYYY-MM-DD")
    return f"{len(b.get('top', []))} cards"


def main(argv):
    if len(argv) < 3 or argv[1] not in {"docs", "claims", "findings", "brief"}:
        print(__doc__)
        return 2
    kind, path = argv[1], argv[2]
    errors = []
    if kind == "docs":
        summary = check_docs(path, errors)
    elif kind == "claims":
        summary = check_claims(path, errors, argv[3] if len(argv) > 3 else None)
    elif kind == "findings":
        summary = check_findings(path, errors)
    else:
        summary = check_brief(path, errors)
    if errors:
        print(f"FAIL {kind} {path}: {summary}")
        for e in errors[:30]:
            print("  -", e)
        if len(errors) > 30:
            print(f"  ... and {len(errors) - 30} more")
        return 1
    print(f"OK {kind} {path}: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
