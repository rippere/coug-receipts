"""Stage 01: turn every file in a project folder into located lines, plus a doc date and author.

Usage:
    python stages/01_ingest/ingest.py inputs/team4@2026-10-21 -o runs/team4@2026-10-21/01_docs.jsonl

Code only, no AI. Reads .docx, .txt/.md, .xlsx and .pdf. Skips files and folders starting with
"_" or ".", and zip files. "Today" comes from the folder name after "@" and is used only to pick
the year for dates written without one.

Locations: p<N> paragraph (.docx), L<N> line (.txt), r<N> spreadsheet row, pg<N>L<M> PDF page/line.
"""
import argparse
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

MONTHS = {m: i for i, names in enumerate(
    [("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"), ("may",),
     ("jun", "june"), ("jul", "july"), ("aug", "august"), ("sep", "sept", "september"),
     ("oct", "october"), ("nov", "november"), ("dec", "december")], 1) for m in names}
MONTH_RE = r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
NOT_NAMES = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
             "meeting", "notes", "week", "team", "update", "updated"} | set(MONTHS)


# ---------------------------------------------------------------- readers

def read_docx(path):
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    lines, n = [], 0
    for para in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        text = html.unescape("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", para)))
        if text.strip():
            n += 1
            lines.append({"loc": f"p{n}", "text": text})
    return lines


def read_txt(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    return [{"loc": f"L{n}", "text": t} for n, t in enumerate(text.splitlines(), 1) if t.strip()]


def read_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    lines = []
    for i, ws in enumerate(wb.worksheets):
        prefix = "" if i == 0 else f"{ws.title}!"
        for n, row in enumerate(ws.iter_rows(values_only=True), 1):
            if any(c is not None for c in row):
                cells = ["" if c is None else (c.date().isoformat() if isinstance(c, dt.datetime) else str(c))
                         for c in row]
                lines.append({"loc": f"{prefix}r{n}", "text": " | ".join(cells)})
    return lines


def read_pdf(path):
    if shutil.which("pdftotext"):
        text = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
        pages = text.split("\f")
    else:  # e.g. Windows without poppler; locations will differ from pdftotext runs
        from pypdf import PdfReader
        pages = [p.extract_text() or "" for p in PdfReader(path).pages]
    lines = []
    for g, page in enumerate(pages, 1):
        for n, t in enumerate(page.splitlines(), 1):
            if t.strip():
                lines.append({"loc": f"pg{g}L{n}", "text": re.sub(r"\s+", " ", t.strip())})
    return lines


READERS = {".docx": read_docx, ".txt": read_txt, ".md": read_txt, ".xlsx": read_xlsx, ".pdf": read_pdf}


# ---------------------------------------------------------------- metadata

def make_date(year, month, day, today):
    """Build a date; a missing year is today's year, or last year if that lands >60 days ahead."""
    try:
        if year:
            return dt.date(int(year) + (2000 if int(year) < 100 else 0), month, day)
        d = dt.date(today.year, month, day)
        return d.replace(year=today.year - 1) if (d - today).days > 60 else d
    except ValueError:
        return None


def find_date(text, today):
    s = text.lower()
    if m := re.search(r"\b(20\d\d)-(\d\d)-(\d\d)\b", s):
        return make_date(m[1], int(m[2]), int(m[3]), today)
    if m := re.search(MONTH_RE + r"\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s*(20\d\d))?", s):
        return make_date(m[3], MONTHS[m[1]], int(m[2]), today)
    if m := re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", s):
        return make_date(m[3], int(m[1]), int(m[2]), today)
    return None


def doc_date(path, lines, today):
    """Filename first, then the first lines (a spreadsheet's title row only; data rows hold due
    dates, not the document's date). Notes can't be dated after today. None when nothing fits."""
    found = find_date(path.stem.replace("_", " "), today)
    head = lines[:1] if path.suffix.lower() == ".xlsx" else lines[:3]
    for line in head:
        if found:
            break
        found = find_date(line["text"], today)
    if found and found > today:
        return None
    return found.isoformat() if found else None


def clean_name(name):
    return name.capitalize() if name and name.lower() not in NOT_NAMES else None


def doc_author(path, lines):
    head = "\n".join(l["text"] for l in lines[:6])
    if m := re.search(r"(?:notes by|notes|writer|written by|note taker|minutes by)\s*:\s*([A-Za-z]+)", head, re.I):
        return clean_name(m[1])
    for pattern in (r"notes\s*-\s*([A-Za-z]+)", r"\s-\s([A-Za-z]+)$", r"_([A-Za-z]+)$"):
        if m := re.search(pattern, path.stem, re.I):
            if name := clean_name(m[1]):
                return name if len(name) > 2 else name.upper()  # keep initials like "KA" as written
    if m := re.search(r"notes\s*-\s*([A-Za-z]+)", lines[0]["text"] if lines else "", re.I):
        return clean_name(m[1])
    return None


def doc_kind(path, lines):
    name = path.name.lower()
    head = " ".join(l["text"] for l in lines[:40]).lower()
    if "readme" in name:
        return "other"
    # A brief by name, or a long document that reads like one (notes that mention "the rubric" don't count).
    brief_terms = sum(1 for t in ("rubric", "grading", "deliverable", "weight", "due date", "policies")
                      if t in " ".join(l["text"] for l in lines).lower())
    if re.search(r"brief|syllabus|rubric|assignment", name) or (len(lines) > 60 and brief_terms >= 3):
        return "brief"
    if path.suffix.lower() == ".xlsx":
        header = " ".join(l["text"] for l in lines[:3]).lower()
        if re.search(r"\b(class|classes|work|away|availability|schedule)\b", header) and "due" not in header:
            return "availability"
        if re.search(r"\b(who|owner|assigned|assignee)\b", header) and re.search(r"\b(due|deadline|status)\b", header):
            return "tracker"
    if re.search(r"meeting|notes|minutes|\bwk\s?\d|\bweek\s?\d", name + " " + head[:200]):
        return "notes"
    return "other"


# ---------------------------------------------------------------- main

def ingest(input_dir: Path, today: dt.date) -> list[dict]:
    files = sorted(p for p in input_dir.rglob("*")
                   if p.is_file() and p.suffix.lower() in READERS
                   and not any(part.startswith(("_", ".")) for part in p.relative_to(input_dir).parts))
    docs = []
    for n, path in enumerate(files, 1):
        try:
            lines = READERS[path.suffix.lower()](path)
        except Exception as e:  # one unreadable file shouldn't stop the run
            print(f"  skipped {path.name}: {e}", file=sys.stderr)
            continue
        kind = doc_kind(path, lines)
        docs.append({"doc_id": f"d{n:02d}", "file": path.relative_to(input_dir).as_posix(),
                     "kind": kind, "doc_date": doc_date(path, lines, today),
                     "author": doc_author(path, lines) if kind == "notes" else None, "lines": lines})
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    args = ap.parse_args()
    name = args.input_dir.resolve().name
    today = dt.date.fromisoformat(name.split("@")[1]) if "@" in name else dt.date.today()

    docs = ingest(args.input_dir, today)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(d) + "\n" for d in docs))
    for d in docs:
        print(f"  {d['doc_id']} {d['kind']:12} {d['doc_date'] or '-':10} {d['author'] or '-':8} "
              f"{len(d['lines']):4} lines  {d['file']}", file=sys.stderr)
    print(f"wrote {len(docs)} docs to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
