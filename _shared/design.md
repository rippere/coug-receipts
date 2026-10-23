# Design — the board (from /ui-ux-pro-max, with deliberate overrides)

## Base system (ui-ux-pro-max output for "Receipts")
- Type: **Fira Sans** (body, actions) + **Fira Code** (receipts, dates, numbers). Load both from Google Fonts.
- Palette: primary `#1E40AF` (links, receipts), amber `#B45309` (act this week; amber-700 so text passes 4.5:1 on paper), ink `#0F172A`, muted `#475569`, background "paper" `#FAFAF7`, cards `#FFFFFF`, borders `#E2E8F0`.
- Rules: SVG icons only (inline Lucide paths), `cursor-pointer` + a 200ms color transition on anything clickable, visible focus rings, `prefers-reduced-motion` respected, color never the only signal.

## Overrides (and why)
| ui-ux-pro-max suggested | We do | Why |
|---|---|---|
| Data-dense dashboard, KPI grid | **3 cards** above the fold. The dense panels go below. | The kickoff's 10-second rule. Judges read the first screen only. |
| Red/amber/green status | **No red anywhere.** Amber = act this week; slate = info. | Red reads as blame on a team-facing tool. |
| Charts | One horizontal bar strip (fair share), with a text table beside it | Accessibility; the data is counts, not trends |

## Signature element: the receipt
Each card ends in a row of **receipt stubs**: small Fira Code chips with a dashed (perforated) top border, labelled like `Wk9 notes · Sofia · p3` or `Brief §5`. Clicking one expands the verbatim quote, file path, and doc date in place. Use `<details>` so it works without JavaScript.

## Confidence badge
`●●● High`, `●●○ Medium`, `●○○ Low`, always with the word, plus a `title` tooltip holding the one-line why. Never color alone.

## Page order
1. **Header strip**: project · `Wed Oct 21 · Week 9` · countdown `M3 due Fri Oct 30 — 9 days` (computed by code).
2. **This week: three things.** Cards: rank · verb-first action (24px) · owner chip · date (`Thu Oct 22 · tomorrow`) · reason · stakes · confidence · receipts · `Bring to the meeting` tag if `talk_first`.
3. **The documents disagree.** Rows: topic | side A (receipt) | side B (receipt) | which we trust and why.
4. **Not on your task list yet.** Rubric gaps (D3) with their weight or penalty.
5. **Questions for the next meeting.** Includes D7, D8, and talk-first items.
6. **Who's carrying what.** Bars of open items with invisible work listed beside them, and the caution line "Counts aren't contribution. Use this to start a conversation."
7. **Since last run** (Week 10 only): ✓ resolved · new · still open · *we flagged → what happened*.

## Projector constraints
Body text is at least 18px. Content is centered with `max-w-6xl` and 16px side gutters. Cards stack below 768px. Light theme only. It runs offline from a static file (inline the fonts if the venue Wi-Fi dies).
