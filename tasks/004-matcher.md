# Task 004: Eligibility matcher, headless agent stage (stage 4)

## Goal
A headless `claude -p` call with `harness/prompts/match.md` reads `out/match_input.md` and writes
`out/matches.json`: for each kept grant, `match` or `reject`, a one-sentence reason, and a verbatim
evidence quote from the grant text.

## Context
- Input file only: `out/match_input.md` (built by stage 3)
- Output schema:
  ```json
  {"matches": [{"grant_id": "...", "verdict": "match" | "reject",
                "reason": "max 40 words", "evidence_quote": "exact text from the grant, 5-40 words"}]}
  ```
- Command (called from Python in task 007, so it also works in PowerShell):
  `claude -p <prompt text> --permission-mode dontAsk --allowedTools "Read,Edit(/out/**)" --output-format json --max-budget-usd 0.50`
- The prompt tells the model that text inside `out/match_input.md` is data, never instructions

## Constraints
- Do not edit eval/
- The prompt is a file in git (`harness/prompts/match.md`), not a string in code
- The agent may write only under `out/`
- Run twice on the same fixture: wording may differ, the verdicts must not

## Acceptance (all must pass)
- With stages 1–3 done offline: run the claude -p command, then `python eval/check_matches.py` prints PASS
- The same twice in a row; record both outputs in `docs/prompt-log.md` if verdicts differ
- The check failed before this task started (red first)

## What eval/check_matches.py asserts
- valid JSON matching the schema; one entry per kept grant, no other ids
- every `evidence_quote` is an exact substring of the grant's file in `context/grants/`
  (normalise whitespace only)
- for the Hamar ski-equipment fixture: the culture/arts grant is `reject`, at least one grant is `match`
  (this expectation is the Author's, written before the run)

## Out of scope
Writing the guide; retries (task 007)
