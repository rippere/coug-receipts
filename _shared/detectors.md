# Detectors (stage 03, all deterministic code)

The AI never decides whether a detector fires. It only phrases the result in stage 04.

| ID | Name | Fires when | Facts emitted |
|---|---|---|---|
| D1 | Lead-time squeeze | a `lead_time` rule applies to an event that must happen by date E, the action isn't done, and `today ≥ E − lead_days − 2` | `latest_action = E − lead_days`, `days_left` |
| D2 | Owner unavailable | an item's owner has an `availability` block that overlaps the window between today and the item's due date or event time | `owner`, `away_from/to`, `slack_days` (working days left before they leave) |
| D3 | Rubric gap | a `deadline.components[]` entry, or a required artifact (e.g. contribution log), has no matching item in the tracker | `component`, `weight_pct`, `penalty` |
| D4 | Sources disagree | ≥2 claims on the same item differ on date, owner, status, or scope | `sides[]`, `trust` (picked by the authority order below), `why` |
| D5 | Unowned / undated | an open item has no `who`, or its date is vague (`?`, `ASAP`, `before demo`, `wk 10`) | `missing: owner\|date` |
| D6 | Dependency squeeze | B is `blocked_by` A, and A's expected date + B's lead time runs past B's due date or B's owner's availability | `chain[]`, `slack_days` |
| D7 | Carried-over question | a `question` raised in ≥2 meetings with no later resolving claim | `meetings_open`, `first_raised` |
| D8 | Load concentration | see `voice.md`, Fair share panel | per-person counts, `blocks_others` |
| D9 | Answered by the brief | an open `question` matches a `rule` / `deadline` the brief already states | the answer and its receipt. This is the "defer to the source" move. |

## Authority order (D4)
For dates of course deliverables and rules: **the brief wins**. For status: **the newest dated source wins**. A `DECISION:` line in notes beats the tracker. Whatever loses still appears on the board as "the documents disagree". It is never silently dropped.

## Confidence
- **High**: an authoritative source (the brief), or ≥2 independent sources that agree.
- **Medium**: a single source, or an identity/alias match the AI inferred ("PR" → Priya, "WCAG review" = "accessibility check").
- **Low**: the sources conflict and no authority rule settles it, or the date is vague.

## Date resolution (code only)
Resolve `date_text` against the claim's `doc_date` (`dateparser`, `PREFER_DATES_FROM=future`, `RELATIVE_BASE=doc_date`). `"wk N"` uses the `week_anchor` rule. Spreadsheet cells may already be datetimes. Year-less dates ("9/19") take the brief's year. Anything that still doesn't resolve stays `null` and triggers D5. **Never let the model fill in a date.**
