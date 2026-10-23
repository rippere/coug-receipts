"""Run the whole pipeline on one project snapshot.

Usage:
    uv run python receipts.py inputs/team4@2026-10-21
    uv run python receipts.py inputs/team4@2026-10-28 --from 03   # rerun from a stage, e.g. after hand-editing claims

The folder name after '@' is "today". Output goes to runs/<same name>/.
Each stage's output is validated before the next stage runs.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VALIDATE = ROOT / "_shared" / "validate.py"


def run(cmd):
    print("$", " ".join(str(c) for c in cmd))
    result = subprocess.run([str(c) for c in cmd])
    if result.returncode != 0:
        sys.exit(f"stopped: '{cmd[1]}' exited {result.returncode}")


def previous_run(runs_dir):
    """The latest earlier run of the same project, for the 'since last run' section."""
    project, today = runs_dir.name.split("@")
    earlier = sorted(p for p in runs_dir.parent.glob(f"{project}@*")
                     if p.name.split("@")[1] < today and (p / "03_findings.json").exists())
    return earlier[-1] if earlier else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("--from", dest="start", default="01", choices=["01", "02", "03", "04"])
    args = ap.parse_args()

    name = args.input_dir.resolve().name
    if "@" not in name:
        sys.exit("input folder must be named <project>@YYYY-MM-DD")
    today = name.split("@")[1]
    out = ROOT / "runs" / name
    out.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    docs, claims, findings = out / "01_docs.jsonl", out / "02_claims.jsonl", out / "03_findings.json"

    if args.start <= "01":
        run([py, ROOT / "stages/01_ingest/ingest.py", args.input_dir, "-o", docs])
        run([py, VALIDATE, "docs", docs])
    if args.start <= "02":
        run([py, ROOT / "stages/02_extract/extract.py", docs, "-o", claims])
        run([py, VALIDATE, "claims", claims, docs])
    if args.start <= "03":
        run([py, ROOT / "stages/03_reconcile/reconcile.py", claims, docs, "--today", today, "-o", findings])
        run([py, VALIDATE, "findings", findings])
    prev = previous_run(out)
    run([py, ROOT / "stages/04_brief/brief.py", out] + (["--prev", prev] if prev else []))
    run([py, VALIDATE, "brief", out / "04_brief.json"])
    run([py, ROOT / "stages/04_brief/app.py", ROOT / "runs"])
    print(f"\nApp: {ROOT / 'runs' / 'index.html'}   (single board: {out / '04_board.html'})")


if __name__ == "__main__":
    main()
