# E · Data & Privacy Plan

**Team 4 · UNIV 497 · Milestone 3** &nbsp;|&nbsp; Volunteer Shift Sign-Up for Palouse Harvest Food Share

> **Rubric (10% of M3):** One to two pages covering what personal data the solution would collect, why each item is needed, where it would be stored, who can see it, and how long it is kept.

## 1. Our approach

The system should collect **only what it needs** to fill shifts, send reminders, and track hours. About 140 volunteers will use it, many of them older adults and some high-school students under 18, so we keep forms short and the rules simple. This plan is for the **recommended design**. The Figma prototype itself uses only made-up sample data.

## 2. What we collect and why

| Data | Required? | Why we need it | Who can see it | How long we keep it |
|---|---|---|---|---|
| **First and last name** | Required | Shows who is on each shift's roster | Volunteer (own) · Coordinator | While active + [TODO: e.g., 2 years] after last shift |
| **Mobile phone number** | Required | Sign-in and **text reminders**, which volunteers preferred over email in our interviews | Volunteer (own) · Coordinator · Text service *(sending only)* | Same as name |
| **Email address** | Optional | Backup contact for people who don't text | Volunteer (own) · Coordinator | Same as name |
| **Reminder setting** (on/off) | Required | Volunteers must opt in to texts; replying STOP opts them out | Volunteer (own) · Coordinator | Same as name |
| **Shift sign-ups** (date, role, time) | Required | The schedule and the coordinator roster | Volunteer (own) · Coordinator | [TODO: e.g., 2 years] for staffing planning |
| **Attendance / check-in** | Required | Fixes double-booking and no-shows, and feeds the hours record | Volunteer (own) · Coordinator | Same as hours record |
| **Hours record** | Required *(if hours tracking stays in scope)* | Students need verified hours for school, as Dana raised in Weeks 4, 7 and 10 | Volunteer (own) · Coordinator | [TODO: e.g., 4 years so graduates can get letters] |
| **"Under 18" checkbox** | Required | Flags minors for food-bank rules (e.g., parent consent, adult-supervised shifts). We do **not** store a birth date. | Coordinator only | Same as name |
| **Parent/guardian name and phone** | Only if under 18 | Consent and emergency contact for minors | Coordinator only | Until the volunteer turns 18 or leaves |
| **Emergency contact** | [TODO: ask Dana if needed] | Safety during warehouse shifts | Coordinator only | Same as name |

**We do not collect:** home address, date of birth, SSN or ID numbers, photos, location tracking, or any information about food-bank *clients*.

## 3. Where it's stored

- **One central system:** a hosted volunteer-scheduling platform or web app chosen by Palouse Harvest's developer or vendor. [TODO: name it once chosen]
- **Requirements for that platform:** data stored in the U.S., encrypted in transit (HTTPS) and at rest, daily backups, and the ability to export and delete records.
- **Text reminders:** sent through an SMS service (e.g., Twilio). It receives **only** the phone number and message text, and it may not use the numbers for anything else.
- **Retiring the paper sheet, Google Form, and texts to Dana's phone:** once the new system is live, old sign-up records are copied in and the old copies are shredded or deleted. [TODO: confirm with Dana]

## 4. Who can see what

| Role | Access |
|---|---|
| **Volunteer** | Their own profile, sign-ups, and hours. Can edit their info or ask to be deleted. |
| **Coordinator** (Dana + [TODO: other staff?]) | Full roster and all volunteer records. Logs in with a password plus a second step (2-factor). |
| **Shift lead** *(if used)* | Only their shift's roster: first name, last initial, and phone, on the day of the shift. |
| **Vendor / SMS service** | Technical access only, under a written agreement. No marketing use. |
| **Students, schools, parents** | Nothing directly. Hours letters are produced by the coordinator on request. |

## 5. Retention and deletion

- **Inactive volunteers:** records are deleted or anonymized after [TODO: e.g., 2 years] with no shifts.
- **Hours records:** kept [TODO: e.g., 4 years] so former students can still request verification.
- **Text message logs:** kept 90 days for troubleshooting, then deleted.
- **On request:** a volunteer can ask the coordinator to delete their data at any time. Hours letters should be printed first.
- **Yearly check:** each January the coordinator reviews and clears out old records.

## 6. Open questions for Dana

These will be asked at the Oct 29 demo (see **D · Sponsor Demo & Feedback**, Question 5).

1. Does Palouse Harvest already have a data-retention or volunteer-privacy policy we should match? [TODO]
2. What are the rules for volunteers under 18 (minimum age, parent consent form)? [TODO]
3. Is an emergency contact required for warehouse shifts? [TODO]
4. Besides Dana, who should have coordinator access? [TODO]

---

<sub>Sources: Project Brief §4 and Appendix A; Week 4 notes (Mei, Sep 15: text reminders, older volunteers, hours for students); Week 7 notes (hours tracking important to students and parents); Week 10 notes (Jordan, Oct 27: hours tracking at demo). AI use: drafted with Claude from team notes. No sponsor data was entered into AI tools (Brief §5).</sub>
