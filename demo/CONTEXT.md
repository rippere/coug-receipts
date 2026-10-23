# Demo — five minutes, whole team, rehearsed twice after 1:30

Reads: `../_shared/golden-team4.md`, `../_shared/voice.md`, the two boards in `../runs/`. Writes: this script and one slide (Google Slides, link below).

## Cast
Everyone speaks once. Lane A drives the laptop the whole time, so nobody else touches it. Fill in names at kickoff.

| Part | Time | Speaker | On screen |
|---|---|---|---|
| 1 · Problem | 0:00–0:40 | **E** · Evan | the kit folder |
| 2 · Live run, Week 9 | 0:40–2:20 | **D** · [Lane D name] | `runs/team4@2026-10-21/04_board.html` |
| 3 · A week later | 2:20–3:20 | **C** · [Lane C name] | `runs/team4@2026-10-28/04_board.html` |
| 4 · Responsible AI | 3:20–4:15 | **B** · [Lane B name] | `_shared/voice.md` |
| 5 · Honest limits + close | 4:15–5:00 | **A** · [Lane A name], then **E** | limitations slide |

**Driver (Lane A):** before we start, open both boards in browser tabs, keep a terminal ready in the repo with the Week 9 command typed, and open the slide in a third tab.

Each part has **cues** (talk in your own words) and **say** lines (the full version if you blank). At about 140 words a minute the say lines total about 4:10, which leaves roughly 50 seconds for clicks, pauses, and the two runs. **The runs must be fast:** do them once beforehand so the extraction cache is warm. If a live run takes more than about 10 seconds, A opens the cached board instead (see fallback ladder).

---

## 1 · Problem (0:00–0:40) · E

**Cues**
- Team 4, Week 9, prototype due in 9 days
- 8 sets of notes, 5 authors, a stale task list, the brief
- Ask the room: where do they stand? Pause.
- Hand off to D

**Say**
> This is Team 4: six students, one capstone, Week 9. Their prototype milestone is due in nine days. Here's everything they've written down: eight sets of meeting notes from five different people, a task list, the course brief, and an availability sheet. The notes don't agree, and the task list gets updated whenever someone remembers.
>
> So, quick question for the room: where does this team stand right now? *(pause two seconds)* Nobody knows. That's the problem Receipts solves. [Lane D name], show them.

---

## 2 · Live run, Week 9 (0:40–2:20) · D

**Cues**
- One command, folder + today's date (Wed Oct 21)
- Read card #1 aloud in ten seconds
- Click the receipt: quote + Brief §5. Code did the date, AI wrote the sentence.
- Confidence line: High, and why
- Scroll: documents disagree (peer evals Nov 6 vs **Oct 30**, the brief wins)
- Scroll: not on your task list (contribution log, −5)
- Hand off to C

**Say**
> *(A runs `uv run python receipts.py inputs/team4@2026-10-21`)*
> One command. We point it at the team's folder, and the folder name tells it today's date: Wednesday, October 21st.
>
> *(board opens)* This is the board. Three cards: the three things that matter this week. Card one, in ten seconds: "Request the sponsor demo. Tyler, by tomorrow, Thursday October 22nd. The brief needs seven days' notice, and the demo has to happen by the 29th."
>
> *(A clicks the receipt stub)* Every line has a receipt. Click it and you get the exact quote: the Week 9 notes say the request hasn't gone out yet, and section five of the brief sets the seven-day rule. Code did the date math. The AI only wrote the sentence.
>
> *(point at the confidence badge)* It also says how sure it is: High, because the brief, the notes, and the task list all agree.
>
> *(A scrolls)* Down here, the documents disagree. The task list and the Week 9 notes say peer evaluations are due November 6th. The brief says October 30th. The brief wins, and you can see both sides.
>
> *(A scrolls)* And this one isn't on their task list at all: the contribution log. It's required, and missing it costs five points. [Lane C name], what happens a week later?

---

## 3 · A week later (2:20–3:20) · C

**Cues**
- Drop in the Week 10 update, rerun
- Since last run: we flagged Oct 22 → request went out Oct 23, went ahead on an instructor exception
- Outcome only, no blame
- New top 3: who runs the demo, finish the accessibility review, privacy plan
- Hand off to B

**Say**
> A week later, the team adds its Week 10 notes and runs it again. *(A runs `uv run python receipts.py inputs/team4@2026-10-28`)*
>
> *(A scrolls to "Since last run")* Now the board checks its own work. Last week we flagged: request the demo by October 22nd. What happened: the request went out on the 23rd, and the demo only went ahead because the instructor made an exception. The tool would have caught it on Wednesday. No blame, just the outcome.
>
> *(A scrolls up to the cards)* Two days left, and the new top three: confirm who runs Thursday's demo, get the last screens accessibility-reviewed, and draft the privacy plan. Each one has an owner and a date. [Lane B name], how do we keep this fair to people?

---

## 4 · Responsible AI (3:20–4:15) · B

**Cues**
- A tool that names people can hurt people, so rules came first
- Constraints, never reasons ("away Oct 28–Nov 1", never why)
- Never ranks or scores anyone
- Talk-first tag = a conversation, not a verdict
- Receipts, dates in code, a human edits the claims
- Nothing hard-coded to Team 4
- Hand off to A

**Say**
> *(A opens `_shared/voice.md`)* A tool that names people can hurt people, so we wrote the rules first. It shows constraints, never reasons. The board says "away October 28th to November 1st", and never why. It never ranks or scores anyone. When a card is about someone's workload, it's tagged "Bring to Tuesday's meeting": a conversation, not a verdict.
>
> Every sentence has a receipt, every date is computed in code, and a person reads and can fix the AI's claims before anything reaches the board. And nothing is hard-coded to Team 4. The roster, the course rules, and today's date all come from the folder. [Lane A name], what can't it do?

---

## 5 · Honest limits + close (4:15–5:00) · A, then E

**Cues (A)**
- Only knows what's written down (not chat, email, Figma)
- Messy notes → editable claims, confidence shown
- "WCAG review" = "accessibility check" is a judgment call → Medium
- Can start a workload conversation, can't read feelings

**Say (A)**
> *(A switches to the slide)* Four honest limits. One: it only knows what's written down. It can't see group chat, email, or Figma, and that's where half of a real team's state lives. Two: reading messy notes is imperfect, so claims are editable and confidence is always shown. Three: matching two names for the same task is a judgment call, so it's labeled Medium. Four: it can open a conversation about workload, but it can't tell how anyone feels, so it never pretends to.

**Say (E)**
> Receipts: what will go wrong before the next deadline, who can stop it this week, and how we know. Thank you.

---

## Limitations slide
[Receipts — Honest limits](https://docs.google.com/presentation/d/1NpJp7aiYXKKM7Tp9NuLqrWq99-0ytEuNav2T8lLHlpI/edit) (Google Slides; share it with the team before the demo). One slide, the four limits above, styled like the board (Fira, paper background, amber accent, no red). Download a PDF copy as the offline backup.

## If something breaks (fallback ladder)
- **Live run hangs or errors** → A opens the cached board in `runs/` and says "Here's the run from this morning." Keep going.
- **Extraction looks wrong** → say so: "A person fixes the claims file by hand. That's the human check working."
- **Wi-Fi dies** → everything opens from local files, including the cached runs. Open the slide from a downloaded PDF copy.

## Judge Q&A (who answers)
- *"What if the tracker is right and the notes are wrong?"* (**C**) The authority order is explicit, and the losing side is still shown.
- *"Privacy?"* (**B**) Team data stays in the folder. Reasons for absence never leave stage 02. Runs on someone's own project can use a local model.
- *"Why not a full PM platform?"* (**E**) One team, one moment, one insight. That's the brief.
- *"How do you know the dates are right?"* (**A**) Code computes every date, and we check the board against a golden answer file written before we built anything.
- *"Couldn't the AI just make up a quote?"* (**D**) Every quote is checked word-for-word against the source file. If it doesn't match, it doesn't ship.

## Rehearsal log (done = under 5:00 on a timed run)
| Run | Time | Over/under | What to cut or fix |
|---|---|---|---|
| 1 (after 1:30) | [TODO] | [TODO] | [TODO] |
| 2 | [TODO] | [TODO] | [TODO] |

If you're over time, cut in this order: the confidence-badge line (Part 2), then the "nothing hard-coded" line (Part 4).
