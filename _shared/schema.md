# Schema — the interface between lanes

Freeze this at 11:05. Each stage writes exactly this shape. Fields not listed here are fine, but nobody downstream may depend on them.

## 01 → `01_docs.jsonl` (one line per source file)
```json
{"doc_id":"d05","file":"02_Meeting_Notes/2026-10-20_Wk9 meeting - Sofia.docx",
 "kind":"notes",            // brief | notes | tracker | availability | other
 "doc_date":"2026-10-20",   // from filename/header, by code; null if unknown
 "author":"Sofia",          // null if unknown
 "lines":[{"loc":"p3","text":"Tyler said he hasn't emailed Dana about the demo yet..."}]}
```
`loc` is `p<N>` for paragraphs, `L<N>` for lines in .txt files, `r<N>` for spreadsheet rows (the text is the row cells joined with ` | `), and `pg<N>L<M>` for PDF page N, line M (whitespace collapsed).

## 02 → `02_claims.jsonl` (one line per claim)
```json
{"id":"c031","doc_id":"d05","loc":"p3",
 "kind":"task",             // task | deadline | decision | status | availability | rule | question | dependency | requirement | person
 "item_hint":"schedule sponsor demo",   // short noun phrase; 03 clusters on this
 "who_raw":"Tyler", "who":["Tyler Brandt"],   // canonical names from roster claims; [] if unowned
 "date_text":"this week", "status":"open",    // open | in_progress | done | unknown
 "quote":"Tyler said he hasn't emailed Dana about the demo yet but will do it this week.",
 "extract_confidence":"high"}            // high | med | low
```
Extra fields by kind:
- `rule`: `{"rule":"lead_time","days":7,"applies_to":"sponsor meeting or demo"}` · `{"rule":"late_penalty","pct_per_day":10,"max_days":3}` · `{"rule":"extension_notice","hours":48}` · `{"rule":"week_anchor","week1_monday":"2026-08-24"}`
- `deadline`: `{"deliverable":"M3 prototype + sponsor demo","weight_pct":20,"components":[{"name":"Sponsor demo and feedback","weight_pct":15}]}`
- `availability`: `{"person":"Kwame Asante","away_from":"2026-10-28","away_to":"2026-11-01"}`, or recurring: `{"days":["Th"],"from":"15:00","to":"21:00"}`. **No reasons.** Stage 02 drops the "why".
- `dependency`: `{"blocked":"coordinator roster flow","blocked_by":"coordinator screens"}`

**Stage 02 never resolves dates.** It copies `date_text` verbatim. Stage 03 resolves it against the doc's `doc_date`, the `week_anchor` rule, and today.

## 03 → `03_findings.json`
```json
{"project":"team4","today":"2026-10-21","next_deadline":{"name":"M3","date":"2026-10-30","days":9},
 "people":["Priya Raman", "..."],
 "items":[{"item_id":"i07","title":"Schedule sponsor demo","owner":["Tyler Brandt"],
           "due":"2026-10-29","due_basis":"rule:demo_by", "status":"open","status_from":"c031",
           "claims":["c031","c044"],"stakes_pct":3.0}],
 "findings":[{"id":"f01","detector":"D1","item_id":"i07",
   "facts":{"latest_action":"2026-10-22","days_left":1,"lead_days":7,"event_by":"2026-10-29"},
   "people":["Tyler Brandt"],"talk_first":false,
   "confidence":{"level":"high","why":"brief rule + Week 9 notes agree it is not sent"},
   "receipts":["c031","c012","c014"],"score":0.91}],
 "load":{"Mei Lin Zhou":{"open_items":2,"blocks_others":2}}}
```
`stakes_pct` = milestone weight × component weight, i.e. course percentage points at risk. Ranking: `score = norm(stakes) × urgency(days_left) × conf`, where high = 1, med = 0.7, low = 0.4.

## 04 → `04_brief.json` (what the board renders; see `fixtures/brief.sample.json`)
```json
{"project":"...","today":"...","today_label":"Wed Oct 21 · Week 9","countdown":{"label":"M3 due Fri Oct 30","days":9},
 "top":[{"rank":1,"action":"Request the sponsor demo","owner":"Tyler","date":"2026-10-22","date_label":"Thu Oct 22 · tomorrow",
         "reason":"...","stakes":"Demo = 15% of M3","confidence":{"level":"high","why":"..."},"talk_first":false,
         "receipts":[{"label":"Brief §5","file":"...","quote":"..."}]}],
 "also":[], "disagreements":[{"topic":"","sides":[{"says":"","receipt":{}}],"trust":"","why":""}],
 "missing":[], "questions":[], "load":{"note":"","people":[{"name":"","items":[],"invisible":[]}]},
 "since_last":null}
```
The **AI writes only** `action`, `reason`, `why` and `questions` text, and always from `facts`. Every date, count, and day number is copied straight from stage 03.
