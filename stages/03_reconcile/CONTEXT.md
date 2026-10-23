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
