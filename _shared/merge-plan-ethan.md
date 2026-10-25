# Merge plan: Ethan's Figma Make app → our app (decided 2026-10-23, ~12:55)

Ethan's app (reference, read-only): https://latch-glide-00920386.figma.site
Our app: `stages/04_brief/templates/app.html` → built by `stages/04_brief/app.py` → `runs/index.html`.
Freeze 1:30 pm, demos 2:00 pm. Keep the setup wizard (Project → Week → Files → Ground rules → build) unchanged.

## Decisions (grilled with Ben)
1. **Base = ours.** Port his ideas in; don't rebuild his React app.
2. **His navigation.** Sidebar = sections: This week · Since last run · Project record · Fair share · Check-in coach · Sources.
   Run switcher = date dropdown in the header ("Wed, Oct 21, 2026 ⌄"). Disagreements + Gaps fold into This week as two
   side-by-side panels under the cards (plus "Already answered by the brief"). Tour's last step points at the date dropdown.
3. **New sections, in build order:** (1) Check-in coach: drafted agenda (where we are · three priorities · questions),
   Copy/Export button, side note "A guide, not a verdict." (2) Project record: searchable table task · owner · due · status ·
   receipts, filter All/Open/Done. (3) Sources: stat row (files · claims · items · findings) + file list with claims per file.
   (4) Fair share: person cards (open commitments, documented contributions, away notice) + "Counts aren't contribution" banner;
   fallback = restyled Team view.
4. **Visual adopts:** hero "This week, with receipts." + subtitle; milestone card with progress bar; initials avatars;
   breadcrumb top bar (no fake search/import buttons); "receipts." wordmark. **Keep** our ink/amber palette (blue only for
   links/receipts) and Plus Jakarta Sans (no Fira).
5. **Copy:** sidebar tagline "Every warning has a reason. Every reason has a receipt."; This week "This week, with receipts." /
   "Three things to focus on" + "A starting point for your next team conversation."; Project record "One shared record.";
   Fair share "Make the work visible."; Check-in "A better check-in."; Sources "The evidence behind it."; Since last run
   "What we flagged, and what happened."; chip stays "Talk as a team"; card titles/reasons stay ours (pipeline).

## Data the new sections need
- `brief.py` → add `items` to 04_brief.json: title, owner (first names), due, status, n receipts (claim ids), + per-person done
  items for Fair share. Source: `03_findings.json` items. Validator ignores extra keys.
- `app.py` → per-doc claim counts (count claims by doc_id from 02_claims.jsonl) alongside the docs list it already embeds.
- Milestone progress = elapsed share of the window from the previous milestone date to the next deadline (or from week-1 anchor).

## Verify before calling done
Rebuild both runs (`uv run python receipts.py inputs/team4@2026-10-2X --from 04`), then in Playwright (served locally at
`runs/index.html?v=N`): wizard → build → tour (all steps resolve) → every sidebar section renders →
date dropdown switches runs → receipt drawer opens → no console errors. Commit + push to main.

## Other workstream
Evan (lane E) is writing the 5-minute narrative/slides from `demo/EVAN_PROMPT.md`; his branch is `lane/e-story`.
