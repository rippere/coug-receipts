# Receipts — the pipeline on one screen

## The one insight (choose it in the first 15 minutes; this is it)
> **"What will go wrong before the next deadline, who can stop it this week, and how we know."**

Direction: the **early warning system**, with the **check-in coach** as its output format. The "tracker that builds itself" sits underneath as plumbing. The "fair share view" appears only as a respectful, secondary panel.

The demo moment: run it on **Wed Oct 21 (Week 9)**. Card #1 says *"Request the sponsor demo by Thu Oct 22. The brief needs 7 days' notice, and the demo has to happen by Oct 29."* Then run it on **Week 10**: the request went out Oct 23, one day late, and only went ahead because the instructor made an exception. **The tool would have caught it on Wednesday.**

## Design stance (liberties we're taking, and where they come from)
| Liberty | Source |
|---|---|
| Show **three** cards above the fold. Everything else sits below. | The kickoff's "ten seconds": *the few things that matter today, why, and the exact action.* Win on concept and design, not breadth. |
| **Receipts are the content.** Every claim opens to its quote, file, author, and date. | Receipts-as-content: credibility comes from showing the evidence. It also covers the 15% "shows its sources" score. |
| Tag cards with **talk first** whenever a person is the subject | Name the tasks that need a human decision. Kickoff: *"knows when to defer to people"* |
| **Since last week**: what we flagged, and what actually happened | Score last week's warnings kept/broken against evidence in the newer files |
| Show **constraints, never reasons** ("away Oct 28–Nov 1", not why) | Share the signal, not the private detail. The brief's accommodations policy. |
| Use a golden file as the acceptance test; code does dates | "Done = observed" doctrine; kickoff: *"A demo that gets a due date wrong is over."* |

## Pipeline
| # | Stage | Kind | Reads | Writes (`runs/<p>@<today>/`) | Human gate |
|---|---|---|---|---|---|
| 01 | ingest | code | `inputs/<p>@<today>/**` | `01_docs.jsonl`: every file as located lines plus its doc date and author | Spot-check that each file appears once with a sane date |
| 02 | extract | **AI** | `01_docs.jsonl` | `02_claims.jsonl`: typed claims, each with a verbatim quote | **Main gate.** Read the claims. Fix wrong ones by hand. |
| 03 | reconcile | code | `02_claims.jsonl` | `03_findings.json`: items, conflicts, gaps, risks, all scored | Compare to `_shared/golden-team4.md` |
| 04 | brief | AI words over code facts | `03_findings.json` (+ previous run) | `04_brief.json`, `04_board.html` | Read it aloud. Would each named teammate be OK seeing it? |

Status = which `0N_*` files exist in `runs/`. Week 10 = a new input folder → a new run → stage 04 diffs it against the previous run of that project.

## Generality (15%): nothing about Team 4 is hard-coded
The roster comes from the documents. Course rules (lead times, late penalty, rubric weights) come out of the brief as `rule` claims. "Today" comes from the folder name. The detectors are generic: lead-time, availability clash, rubric gap, source conflict. Bonus: run it on one of our own group projects, with the teammates' permission.

## Lanes (one owner per folder; write names at kickoff)
| Lane | Owns | Builds against | First milestone |
|---|---|---|---|
| A — Ingest | `stages/01_ingest/` | the raw kit | 11:30 `01_docs.jsonl` for both snapshots |
| B — Extract | `stages/02_extract/` | `_shared/fixtures/docs.sample.jsonl` | 11:45 claims for the brief + 2 notes files |
| C — Reconcile | `stages/03_reconcile/` | `_shared/fixtures/claims.sample.jsonl` | 12:00 D1 + D2 + D3 firing on the fixture |
| D — Board | `stages/04_brief/` | `_shared/fixtures/brief.sample.json` | 12:00 static board renders the fixture |
| E — Story | `demo/` + `_shared/voice.md` | the golden file | 12:30 script draft; own-project data with permission |

The interface is `_shared/schema.md`. Freeze it by 11:05. Changing it after that is a whole-team decision.

## Timeline (build ends 1:30, demos at 2:00)
- **10:45–11:05** Everyone skims the kit and assigns lanes. Freeze the schema.
- **11:05–12:15** Lanes build in parallel against the fixtures.
- **12:15** Integration #1: run end to end on `team4@2026-10-21`. Ugly output is fine.
- **12:15–1:00** Tune the ranking and wording against the golden file. Run Week 10 and check the diff.
- **1:00–1:30** Bonus run on our own project. Polish. Write the limitations slide.
- **1:30 STOP.** Rehearse `demo/CONTEXT.md` twice.

## Fallback ladder (never demo nothing)
Extraction flaky → hand-fix `02_claims.jsonl`, and say so in the demo (that is the human gate working). UI late → render `04_brief.json` as markdown. API down → replay the cached `runs/`.
