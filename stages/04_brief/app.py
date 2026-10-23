"""Build the tabbed app: one local HTML page holding every run's board.

Usage:
    python stages/04_brief/app.py [runs_dir]        # default: runs/  ->  runs/index.html

Reads runs/<project>@<date>/04_brief.json for every run (sample fixtures skipped) and embeds them
as JSON in templates/app.html. Open runs/index.html in a browser; no server needed.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    runs_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[1] / "runs"
    runs = []
    for brief in sorted(runs_dir.glob("*@*/04_brief.json")):
        name = brief.parent.name
        if name.startswith("fixture"):
            continue
        data = json.loads(brief.read_text())
        data["run"] = name
        docs = brief.parent / "01_docs.jsonl"  # file list for the setup wizard (metadata only, no text)
        data["docs"] = [{k: d.get(k) for k in ("file", "kind", "doc_date", "author")} | {"lines": len(d["lines"])}
                        for d in map(json.loads, docs.read_text().splitlines())] if docs.exists() else []
        claims = brief.parent / "02_claims.jsonl"  # claims per file, for the Sources view
        per_doc = {}
        if claims.exists() and docs.exists():
            ids = {d["doc_id"]: d["file"] for d in map(json.loads, docs.read_text().splitlines())}
            for c in map(json.loads, claims.read_text().splitlines()):
                f = ids.get(c["doc_id"])
                per_doc[f] = per_doc.get(f, 0) + 1
        for d in data["docs"]:
            d["claims"] = per_doc.get(d["file"], 0)
        findings = brief.parent / "03_findings.json"  # item record for the Project record view
        data["items"] = [{"title": i["title"], "owner": i["owner"], "due": i["due"], "status": i["status"],
                          "receipts": len(i["claims"])}
                         for i in json.loads(findings.read_text())["items"]] if findings.exists() else []
        runs.append(data)
    runs.sort(key=lambda b: (b["project"], b["today"]))
    payload = json.dumps(runs).replace("</", "<\\/")  # safe inside <script>
    html = (HERE / "templates" / "app.html").read_text().replace("__RUNS_JSON__", payload)
    (runs_dir / "index.html").write_text(html)
    print(f"wrote {runs_dir / 'index.html'} with {len(runs)} runs", file=sys.stderr)


if __name__ == "__main__":
    main()
