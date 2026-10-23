# Talking points (5 minutes, 2:00 pm)

Condensed from Evan's script in `CONTEXT.md` and checked against the real boards built at 12:55.
Use the full script for practice. On stage, read only the bold line in each part.
Wording corrections are listed at the bottom.

**Open on screen:** http://benderman:8790/runs/index.html (Ctrl+Shift+R to refresh). Add `#board` to the URL to skip setup.
**Backup:** open `runs/index.html` straight from disk; it needs no server or Wi-Fi.

---

## 1 · Problem (0:00–0:40) · Evan
**Where does this team stand right now? Nobody knows. That's what Receipts answers.**
- Team 4, UNIV 497, Week 9. Milestone 3 (the prototype and sponsor demo) is due Fri Oct 30, nine days out.
- The kit has 12 files: 8 sets of meeting notes from 5 authors, a stale task list, the course brief, and an availability sheet.
- The notes disagree with each other, and the task list only gets updated when someone remembers.

## 2 · Week 9, live (0:40–2:20) · [driver]
**Point it at the folder. In seconds you get three things to do, each with a person, a date, a reason, and a receipt.**
- Setup takes four steps: Project, Week, Files, Ground rules. The build counts up to 12 docs, 196 claims, and 29 findings.
- **Card 1:** *Schedule the demo with Dana. Tyler, by tomorrow, Thu Oct 22.* The brief requires 7 days' notice, and the demo has to happen by Oct 29. The latest notes say it isn't done.
- Click the receipt. It shows the exact quote, the file, and the line. Code did the date math; the AI only reads the notes.
- The confidence shows **High** and says why: a course rule from the brief, plus notes saying it's still open.
- **Card 2:** *Finish the accessibility check before Kwame is away (Tue Oct 27).* The board shows "away Oct 28 – Nov 1" and never says why.
- **Card 3:** *Pick an owner for the privacy plan.* This card carries the **Talk as a team** chip.
- Scroll down to where the documents disagree: Priya's notes say Kwame owns the accessibility check, while the task list says "Mei?". The board marks it **Ask the team** and shows both sides.
- Then the item missing from the task list: the brief requires a **contribution log** with the milestone.

## 3 · A week later (2:20–3:20) · [Ethan]
**Run it again a week later, and it checks its own work.**
- Week 10 has 13 docs and 236 claims. Switch to it with the date dropdown or the runs list.
- Under **Since last run**, three things were flagged last week:
  - **The demo is done.** Tyler emailed Dana on Fri 10/23, one day late. It only went ahead because Dr. Okafor made an exception ("she said ok this time"). The tool flagged it on Wednesday. We talk about outcomes and never blame anyone.
  - **The accessibility check is still open.** Five screens haven't been reviewed, and Kwame leaves today.
  - **The privacy plan is in progress.**
- New top 3, with two days left:
  - **Confirm who runs Thursday's demo.** It's at 4:30 pm, and Jordan is busy from 3 pm. The code caught that time clash.
  - **Find a new owner for the WCAG review**, because Kwame is away.
  - **Set a date for the hours-tracking screens.**
- The missing list now says **contribution log: −5 points if missing.**

## 4 · Responsible AI (3:20–4:15) · [Ben]
**A tool that names people can hurt people, so we wrote the rules before the code.**
- It shows constraints and never the reason behind them: "away Oct 28 – Nov 1", never why.
- It never ranks or scores anyone. The workload view says *"Counts aren't contribution."* It doesn't touch peer evaluations.
- Every line has a receipt, and every quote is checked word for word against the source file. A quote that doesn't match doesn't ship.
- Dates and counts come from code. The AI only turns notes into claims, and a person can edit those claims before they reach the board.
- **It runs on our own GPU, a DGX Spark, so team notes never go to a cloud AI.**
- Nothing is hard-coded to Team 4. The roster, the rules, and today's date all come from the folder.

## 5 · Limits + close (4:15–5:00) · [driver], then Evan
**It's honest about what it can't see.**
- It only knows what's written down. Group chat, email, and Figma are invisible to it.
- Reading messy notes is imperfect, so the claims are editable and confidence is always shown.
- Matching "WCAG review" with "accessibility check" is a judgment call, so that card is marked Medium.
- It can start a conversation about workload, but it can't read how anyone feels.
- **Evan closes:** *"Receipts: what will go wrong before the next deadline, who can stop it this week, and how we know. Thank you."*

---

## Corrections to Evan's script (now matching the real boards)
- **Week 9's disagreement is about an owner** (accessibility: Kwame or Mei?). The peer-evals date conflict (Oct 30 vs Nov 6) only appears in **Week 10**, where the brief wins with Oct 30. Use it there if there's time.
- In Week 9 the contribution log says "required by the brief". The −5 points line only appears in the **Week 10** board.
- **Week 10's top 3:** confirm who runs the demo, a new WCAG owner, and a date for the hours-tracking screens. The privacy plan is no longer in the top 3.
- The chip on talk-first cards reads **"Talk as a team"**, not "Bring to Tuesday's meeting."
- The slide font is **Plus Jakarta Sans**, not Fira.
- **Don't dwell on the Week 10 disagreements panel.** Two rows there are matching errors: "Submit M3" picks up the M4 and M5 dates, and the demo date picks up "Sep 10". If a judge asks, say: *"Matching is the weakest part. That's why confidence is shown and the claims can be edited."*

## Judge Q&A
- **"Couldn't the AI make up a quote?"** Every quote is matched word for word against the file before it ships.
- **"How do you know the dates are right?"** Code computes every date, and we checked the boards against a golden answer file written before the build.
- **"Privacy?"** Inference runs on our own hardware. Reasons for absences are never shown, only the dates.
- **"Does it only work for Team 4?"** Point it at any folder named `project@date`. Nothing in the code names Team 4.
- **"The tracker is right and the notes are wrong?"** The authority order is explicit: brief, then the newest notes, then the task list. The losing side is still shown.
