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
        runs.append(data)
    runs.sort(key=lambda b: (b["project"], b["today"]))
    payload = json.dumps(runs).replace("</", "<\\/")  # safe inside <script>
    html = (HERE / "templates" / "app.html").read_text().replace("__RUNS_JSON__", payload)
    (runs_dir / "index.html").write_text(html)
    print(f"wrote {runs_dir / 'index.html'} with {len(runs)} runs", file=sys.stderr)


if __name__ == "__main__":
    main()
