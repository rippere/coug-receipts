# Evan: your lane (E · the pitch)

You own our 5-minute demo: what we say, the order, who says it, and how the slides look. The rest of the team owns the code. Copy everything below the line into Claude or ChatGPT and work through it with the AI. It will interview you first, and every final decision is yours.

Save your work in the `demo/` folder on GitHub (open the folder → **Add file** → **Upload files** or **Create new file** → **Commit changes**). Don't edit files anywhere else in the repo.

---

You're my coach for a 5-minute hackathon pitch. I'm Evan, I'm not technical, and I own this part of our team's project. Interview me, give me options, and let me choose. Don't decide for me, and don't write anything I can't say out loud comfortably.

## The event
Coug AI Build Challenge, Friday Oct 23, 2026, judged by the WSU MIS Advisory Board. Building stops at 1:30 pm, and demos start at 2:00 pm: 5 minutes each, then questions. The judges score:
- working demo 30%
- specific guidance a team would act on 25%
- works for any project 15%
- responsible AI 15%
- presentation 15%, which includes stating our honest limitations

## Our product: "Receipts"
It reads a student team's own project files (meeting notes, task list, schedule, the instructor's brief) and shows the three things most likely to go wrong this week. Each one names the task, the person, the date, and the reason. Every line links to the exact sentence it came from (the "receipt").

The test data is Team 4, a fictional team of 6 students building a volunteer sign-up app for a food bank. Their status is spread across 12 files written by 5 different note-takers, and some of those files disagree with each other.

## The one story to tell
On Wednesday of Week 9, our tool found this:
- The course requires 7 days' notice to book a sponsor demo, and the demo has to happen by Thursday, October 29.
- So the last day to ask was Thursday, October 22.
- The Week 9 meeting notes say nobody had asked yet.

One week later, the Week 10 notes show the request went out on October 23, one day late. The instructor had to make an exception. Our tool flagged it the day before the deadline.

## How it works (pick at most two for the pitch)
- The AI reads the documents, and ordinary code does all the date math, so dates are never guessed.
- It runs on Ben's own private AI hardware, so team documents never go to a cloud AI.
- Every quote is checked word for word against the source file. Anything that doesn't match is thrown out.
- People stay in charge: everything the AI extracts is a plain file a teammate can read and correct.

## Responsible AI (say one or two)
- It flags the work, not the person.
- It says when someone is away ("Kwame is away Oct 28 to Nov 1") but never why.
- It never ranks teammates. Workload issues become a question for the team, not a verdict.

## Honest limits (say two)
- It only knows what's written down. The group chat, email, and Figma are invisible to it.
- Pulling facts out of messy notes isn't perfect, which is why it shows a confidence level and lets people correct it.
- The ranking of the top three still needs tuning, and the dashboard is a first version.

## Facts I may use (and nothing else)
- The facts above, as written.
- Numbers Ben confirms at 1:00 pm, such as how many claims the tool pulled out. Until then, write [BEN TO CONFIRM].

If I want a number, quote, or feature that isn't on this list, tell me to ask Ben. Don't fill it in.

## Guardrails
1. **Brevity.** The script is 450–550 words. That leaves time for clicking through the live demo. Short sentences, one idea each.
2. **Demo only what runs.** Ben will tell me at 1:00 what works live. Never promise a feature as if it exists. Say "next we'd add…" instead.
3. **Dignity.** Team 4's people are fictional, but we talk about them the way we'd want to be talked about. No blame words ("dropped the ball," "lazy," "failed").
4. **No real student data,** grades, or personal information anywhere.
5. **Plain words.** No jargon (pipeline, LLM, schema, inference) unless I ask for it. "The AI reads; code does the math" is the level.

## What I need from you, in this order
1. **Ask me 3 questions first:** who on our team presents which part, whether I want a confident or a conversational tone, and which slide tool I'll use (Google Slides, PowerPoint, or Canva).
2. **Offer two different openings** (two sentences each) and let me pick one.
3. **Draft the script** in this shape, with a time on each part:
   - 0:00–0:30 the problem, in one picture a judge has lived
   - 0:30–2:30 live demo (Ben drives the screen and I narrate): the Oct 22 card, one click to show its receipt, then the Week 10 "we flagged it, then this happened" moment
   - 2:30–3:30 how it works and responsible AI (three sentences total)
   - 3:30–4:30 two honest limits and what we'd build next
   - 4:30–5:00 thank you, and a buffer
4. **Have me read it aloud with a timer.** Cut anything that runs long, and tell me what you cut.
5. **Slides: 4 at most,** and the live demo replaces any slide about features:
   1. Title: "Receipts" plus one line
   2. The problem: 12 files, 5 writers, one missed deadline
   3. How it works and responsible AI: 3 short lines
   4. Limits and what's next
6. **A Q&A card:** the 5 likeliest judge questions, with answers of 2 sentences or fewer that use only the allowed facts.

## Slide design rules (our team's design system)
- Fonts: Fira Sans for text and Fira Code for dates and numbers (both free on Google Fonts). Use one font size for titles and one for body. Body text is at least 24 pt.
- Colors: off-white background `#FAFAF7`, dark ink text `#0F172A`, blue `#1E40AF` for highlights, amber `#B45309` for the one thing that needs attention. **No red anywhere**, because on a team tool it reads as blame.
- One idea per slide and no more than 15 words. Left-align the text.
- Use simple line icons (for example from lucide.dev), never emoji.
- Check that text is readable from the back of the room: dark text on a light background, never gray-on-gray.
- Use a screenshot of our real board, never a made-up mockup.

When we finish, give me the final script, the slide text, and the Q&A card as one clean document I can paste into `demo/pitch.md`.
