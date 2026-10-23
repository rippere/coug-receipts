# Receipts — Coug AI Build Challenge (Oct 23, 2026)

Point it at a team's project folder and a "today" date. It hands back the three things that matter this week (task, person, date, reason), and every line links to the file it came from.

Built on ICM: folders carry sequencing, files carry state. Each stage folder has one owner and one contract (`CONTEXT.md`). If something needs explaining, put the explanation in that folder's contract.

## Where things live

| Folder | What it holds |
|---|---|
| `CONTEXT.md` | the whole pipeline on one screen: the stance, the lanes, the timeline. **Read this first.** |
| `stages/01..04_*` | the pipeline in order. Each folder holds its contract and code. |
| `_shared/interfaces.md` | **lane contracts**: who writes what, the CLI each stage exposes, the validator, git rules |
| `_shared/` | factory: `schema.md` (the data shapes), `voice.md` (dignity rules), `detectors.md`, `design.md` |
| `_shared/fixtures/` | hand-made stage outputs, so every lane can build against them before the lane upstream works |
| `_shared/golden-team4.md` | the acceptance test: what a correct board says for Week 9 and Week 10 |
| `inputs/<project>@<today>/` | one folder per project snapshot. The folder name sets "today". |
| `runs/<project>@<today>/` | product: one folder per run, holding `01_docs.jsonl` … `04_board.html` |
| `demo/` | the 5-minute script, the limitations, the kickoff guide |

## Route by what just happened

| If | Go to | Then stop at |
|---|---|---|
| new teammate joining | `CONTEXT.md` → your lane's `stages/0N_*/CONTEXT.md` | your lane's fixture |
| starting a run | `uv run python receipts.py inputs/team4@2026-10-21` | a human reads `runs/…/02_claims.jsonl` |
| claims look wrong | edit `runs/…/02_claims.jsonl` by hand, then rerun from stage 03 | — |
| board looks wrong | compare it to `_shared/golden-team4.md` | fix the detector, not the wording |
| asked for status | scan `runs/*/` for which `0N_*` files exist | report |
| rehearsing | `demo/CONTEXT.md` | — |

## The rules

1. Code computes dates and counts. The AI reads, connects, and explains (kickoff guide). A wrong date ends the demo.
2. If a sentence on the board has no receipt, it doesn't go on the board.
3. Nothing moves to the next stage until a person has read the output of the last one.
