# Interfaces — how the 5 lanes plug together

Each lane **writes only its own paths**, **reads only the files listed**, and **hands off one file in one shape**. A handoff is valid when `python _shared/validate.py <kind> <file>` exits 0. If your output passes the validator, you are done with the interface; whatever the next lane does with it is their problem.

## The chain
```
inputs/<p>@<today>/ ─A─▶ 01_docs.jsonl ─B─▶ 02_claims.jsonl ─C─▶ 03_findings.json ─D─▶ 04_brief.json + 04_board.html
                                                                                    ▲
                                                           E: voice.md rules, golden file, demo
```
All stage outputs go in `runs/<p>@<today>/`. The runner `receipts.py` calls the four CLIs in order and validates each handoff.

## Lane contracts

| Lane | Writes (only) | Reads (only) | CLI it must expose | Hands off | Validate with |
|---|---|---|---|---|---|
| **A · Ingest** + runner | `stages/01_ingest/**`, `receipts.py`, `_shared/validate.py` | `inputs/**` | `python stages/01_ingest/ingest.py <input_dir> -o <runs_dir>/01_docs.jsonl` | `01_docs.jsonl` | `validate.py docs` |
| **B · Extract** | `stages/02_extract/**` | `01_docs.jsonl`, `_shared/schema.md`, `_shared/voice.md` | `python stages/02_extract/extract.py <runs_dir>/01_docs.jsonl -o <runs_dir>/02_claims.jsonl` | `02_claims.jsonl` | `validate.py claims` (also checks every quote verbatim against docs) |
| **C · Reconcile** | `stages/03_reconcile/**` | `02_claims.jsonl`, `01_docs.jsonl`, `_shared/detectors.md` | `python stages/03_reconcile/reconcile.py <claims> <docs> --today YYYY-MM-DD -o <runs_dir>/03_findings.json` | `03_findings.json` | `validate.py findings` |
| **D · Board** | `stages/04_brief/**` | `03_findings.json`, `02_claims.jsonl` (receipt quotes by id), previous run's `03_findings.json`, `_shared/voice.md`, `_shared/design.md` | `python stages/04_brief/brief.py <runs_dir> [--prev <prev_runs_dir>]` → writes `04_brief.json` + `04_board.html` into `<runs_dir>` | the board | `validate.py brief` |
| **E · Story** | `demo/**`, `_shared/voice.md`, `_shared/golden-team4.md` | everything, read-only | none | rules + golden + 5-min script | runs the golden check by eye at 12:15 and 1:00 |

**Nobody edits** `_shared/schema.md` or `_shared/fixtures/**` after 11:05 without telling the whole team in the chat. A schema change means updating the validator and the fixtures in the same commit.

## Working independently
- Every lane starts from a fixture: B ← `fixtures/docs.sample.jsonl`, C ← `fixtures/claims.sample.jsonl`, D ← `fixtures/brief.sample.json` (and C's real output once it lands). A doesn't need one.
- Shared Python deps go in `pyproject.toml`. Ask lane A before adding one.
- The model is set by the env var `RECEIPTS_MODEL`, and the key by `ANTHROPIC_API_KEY`. Never commit keys; `.env` is gitignored.

## Git rules (the sprint version)
- One branch per lane: `lane/a-ingest`, `lane/b-extract`, `lane/c-reconcile`, `lane/d-board`, `lane/e-story`.
- Merge into `main` as soon as your validator passes. Because lanes never touch each other's paths, merges should be conflict-free. If you hit a conflict, you edited outside your lane.
- `main` must always run: `uv run python receipts.py inputs/team4@2026-10-21`.
- Integration checkpoints: **12:15** (first full run), **1:00** (Week 10 run + diff), **1:30** freeze. At freeze, lane A commits the cached `runs/` (`git add -f runs/`) so the demo works offline.

## Definition of done per lane (by 1:30)
- **A**: both input snapshots ingest. Every file has a non-null `kind`, and doc dates are correct for every notes file that has a date.
- **B**: Week 9 claims cover the golden top 3, and no quote fails the verbatim check.
- **C**: the pytest golden facts pass on real B output, not just the fixture.
- **D**: the board renders the three cards, the disagreements, the missing items, and "since last run" for Week 10, and it passes the read-aloud test.
- **E**: the script fits in 5:00 on a timed rehearsal, and the limitations slide is written.
