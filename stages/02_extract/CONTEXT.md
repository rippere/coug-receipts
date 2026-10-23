# 02_extract — lines to typed claims (the only AI-reads stage)

One job: read each doc and emit typed claims, each carrying a verbatim quote and its location. No reconciling across docs, and no date math.

## Inputs
- Working: `runs/<p>@<today>/01_docs.jsonl`
- Reference: `../../_shared/schema.md` §02 · `../../_shared/voice.md` (the "constraints, never reasons" rule applies here first) · `prompts/extract.md` (lane B writes this)

Do NOT load: other docs while extracting one (one call per doc keeps quotes honest), the golden file, `03`/`04`.

## Process
1. **Roster pass first** (one call over the README/brief/notes that introduce people). Emit `person` claims holding the canonical name, role, and aliases ("Ty", "Tyler B.", "PR" → Priya, initials in filenames). Pass this roster into every later call.
2. **Per-doc call** with structured output (JSON schema = the claim schema). The prompt rules:
   - `quote` must be a **verbatim substring** of the doc's line at `loc`. Code checks this and drops any claim that fails, logging it.
   - `date_text` is copied as written. Never convert it.
   - For the brief: emit `rule` claims (lead_time, late_penalty, extension_notice, week_anchor, demo_by) and `deadline` claims with weights and rubric components.
   - For availability: emit blocks and drop reasons. "OCT 28 – NOV 1 sisters wedding" becomes `away_from/away_to` only.
   - Emit `dependency` claims for "can't do X until Y" and `question` claims for "is that in or out?", "TBD", "double check".
3. Model: `RECEIPTS_MODEL` env var, default `claude-sonnet-5-5`, temperature 0. Cache each doc's response by content hash so reruns are free and the demo can work offline.
4. Assign ids `c001…`, then write `02_claims.jsonl`.

## Outputs
- `02_claims.jsonl`

## Human check (the main gate)
Skim every claim. Fix wrong ones in place and delete hallucinated ones. Add `"edited_by":"human"` to anything you change. Stage 03 reads whatever is in this file. In the demo, *say* that this gate exists. It is the "humans in charge" story.
