# 01_ingest — any file to located lines

One job: turn every file in a project folder into plain text lines, each with a stable location, plus a doc date and author. Code only, no AI.

## Inputs
- Working: `inputs/<project>@<today>/**` (recurse; skip `_*` and zips)
- Reference: `../../_shared/schema.md` §01

Do NOT load: the golden file, other stages, previous runs.

## Process
1. Dispatch on extension: `.docx` (python-docx paragraphs + tables), `.txt`/`.md` (lines), `.xlsx` (openpyxl, one line per non-empty row, cells joined with ` | `, datetimes as ISO), `.pdf` (pdfplumber/pypdf, one entry per page, then split into lines).
2. `doc_date`: regex the filename first (`2026-10-20`, `oct 27`, `Sep 15`), then the first 5 lines ("Date: Tue Oct 13, 2026", "sept 8"). Year-less dates take the year of the brief. If neither works, use `null`. Do not guess.
3. `author`: regex "Notes by: X", "Writer: X", "- Sofia", or a trailing "_Priya"/"KA" in the filename. Otherwise `null`.
4. `kind`: heuristics first ("rubric"/"grading" → brief; ≥3 rows with a who/due header → tracker; "classes|work|away" header → availability; "meeting|notes|wk" → notes). Fall back to `other`.
5. Write `runs/<project>@<today>/01_docs.jsonl`. "Today" is parsed from the folder name after `@`.

## Outputs
- `01_docs.jsonl`: one object per file, with exactly the schema fields.

## Human check
Run `jq -r '[.file,.kind,.doc_date,.author]|@tsv'` on the output. Every file should appear once, and the dates should look right. Known traps in Team 4: `wk 7.txt` has no date in it, so the code should fall back to the week anchor (Tue Oct 6) or leave it `null`. `wk3 notes.txt` says "sep 8". The updated tracker's date comes from its filename ("updated oct 27").
