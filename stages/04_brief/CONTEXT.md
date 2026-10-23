# 04_brief — findings to the ten-second board

One job: turn ranked findings into the board. The AI writes sentences; every number and date is copied from stage 03.

## Inputs
- Working: `runs/<p>@<today>/03_findings.json`, plus the previous run's `03_findings.json` for the same project (the latest earlier `@date`), if one exists
- Reference: `../../_shared/voice.md` (hard rules) · `../../_shared/design.md` · `templates/board.html.j2` (lane D writes this)
- Dev fixture: `../../_shared/fixtures/brief.sample.json` (build the HTML against this first)

Do NOT load: `02_claims.jsonl` in full (look up only the receipts' quotes by id), raw docs, the golden file.

## Process
1. Pick the top 3 findings by `score`, after merging findings on the same item into one card. Send the next 2 to `also`, D4 findings to `disagreements`, D3 to `missing`, and D7/D8/talk-first items to `questions`.
2. **One LLM call** writes `action` / `reason` / `confidence.why` / `questions`, given `facts` + `voice.md`. Then check in code: no digit appears in `action`/`reason` that isn't in `facts`; `action` is ≤ 10 words; the text contains none of the banned words (`failed`, `didn't bother`, `behind`, `lazy`, `always`, and any reason words copied from availability text). If a check fails, retry once, then fall back to a template sentence.
3. **Since last run:** match items between runs. A finding that is gone and whose item is now done → `resolved`. A finding id that's new → `new`. A finding in both → `still_open`. For each previous top-3 card, look up what happened (the done date vs the flagged latest date) → `we_flagged`.
4. Fill `receipts[]` with labels (`Wk9 notes · Sofia · p3`), file paths, and quotes.
5. Render `04_board.html` with Jinja2 + the Tailwind CDN + Google Fonts, then open it.

## Outputs
- `04_brief.json`, `04_board.html`

## Human check
Read each card aloud in under ten seconds. Then ask, for each named person: *would they be OK seeing this on a projector?* If not, fix `voice.md` or the check list, not just the sentence.
