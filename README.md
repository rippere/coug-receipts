# Receipts

Coug AI Build Challenge, Oct 23 2026. You point it at a team's project folder and a "today" date, and it returns the three things that matter this week (task, person, date, reason). Every line links to the file it came from.

**Start here:** open `spec.html` in a browser for the overview. Then read `_shared/interfaces.md` for your lane's contract, and your lane's `stages/0N_*/CONTEXT.md`.

```bash
git clone git@github.com:rippere/coug-receipts.git && cd coug-receipts
git switch -c lane/<your-lane>          # a-ingest | b-extract | c-reconcile | d-board | e-story
uv sync                                  # or: uv run --with <dep> ...
export ANTHROPIC_API_KEY=...             # lane B and D only; never commit it
uv run python receipts.py inputs/team4@2026-10-21     # full run, once all four stage scripts exist
uv run python _shared/validate.py claims _shared/fixtures/claims.sample.jsonl _shared/fixtures/docs.sample.jsonl
```

All team data in `inputs/` is the fictional sample kit from the organizers.
