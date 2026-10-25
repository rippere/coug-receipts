# 03_reconcile — claims to scored findings (code does dates and counts)

One job: merge claims into items, resolve every date, run the detectors, and rank the results. Deterministic. The only AI call allowed is optional and small: clustering `item_hint`s into items, with the result cached and human-editable.

## Inputs
- Working: `runs/<p>@<today>/02_claims.jsonl`
- Reference: `../../_shared/detectors.md` · `../../_shared/schema.md` §03
- Dev fixture: `../../_shared/fixtures/claims.sample.jsonl` (build against this until lane B delivers)

Do NOT load: raw docs (only claims), `voice.md` (that's wording, which belongs to stage 04).

## Process
1. **Resolve dates** with the rules in `detectors.md` (dateparser + week anchor + doc_date base). Unresolved dates stay `null`.
2. **Cluster into items.** Normalize `item_hint` (lowercase, strip stopwords), then use fuzzy match (rapidfuzz ≥ 85). Optionally, one LLM call returns `{claim_id: item_id}` for leftovers. Write `items_map.json` so a human can fix it.
3. **Per item:** owner (the newest claim with a `who`), due (authority order), status (newest dated source), and `stakes_pct` from the deadline claim's weight × component weight.
4. **Run D1–D9.** Each finding gets its facts, receipts (claim ids), confidence (per the rubric), and `talk_first`.
5. **Rank:** `score = norm(stakes) × 1/(1+max(days_left,0)) × conf`. Keep everything; stage 04 picks the top 3.
6. `load` = open items per person due by the next deadline, plus the `blocks_others` count from dependency claims.

## Outputs
- `03_findings.json` (+ `items_map.json`)

## Human check
Diff the top 5 against `_shared/golden-team4.md`. **If a date is wrong, fix the code, never the output.** Add a pytest per detector using the fixture, e.g. D1 must return `latest_action == 2026-10-22` for `today = 2026-10-21`.

## Real-claims reconciliation (issue #1)
- Run `python -m pytest stages/03_reconcile -q`. Tests cover both the curated
  claims and the unchanged `claims.real-wk9.jsonl` lane B output, plus the CLI
  and findings validator.
- An assignment or scheduling decision does not complete work. Status comes
  from the newest task/status evidence or an explicitly `done` decision. Newer
  task progress supersedes older decisions, including mislabeled assignments.
  Owner selection uses the newest named claim; historical conflicts stay in D4.
- A question marked `unknown` remains unresolved for D9 unless later completion
  evidence answers it. Extension notice uses structured `hours`, falling back to
  a numeric hour duration in `date_text`. If neither is present, the notice stays
  unresolved; no cutoff is invented. Date-only deadlines use the existing
  end-of-day (23:59) convention.
- Lane B sometimes labels product features as `artifact`. D3 requires a
  requirement claim with an artifact/penalty and a weighted-deadline association,
  penalty, or explicit submission obligation (`required`, `requires`,
  `submission`, `submit`, `due`). Unlinked scope stays in the item record for
  review. Missing artifact dates fall back to the next milestone; if no date is
  known, urgency is zero rather than "due today". This conservative heuristic
  cannot infer missing submission semantics from an ambiguous claim.
- Projects without upcoming M-code milestones fall back to dated, weighted
  deadline claims. No project names, people, or calendar dates are hard-coded.
- Findings carry claim IDs and availability constraints, never availability
  quotes. Stage 04 must still honor `quote_private` when displaying receipts.
