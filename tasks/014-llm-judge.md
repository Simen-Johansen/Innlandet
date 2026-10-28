# Task 014: LLM-as-judge for plain language and helpfulness

## Goal
`python eval/judge.py` scores `out/grant_action_plan.md` on a fixed rubric and writes `out/judge.json`.

## Context
- Rubric (1–5 each, with one sentence of justification): klarspråk / plain English, actionable steps,
  no unexplained jargon, correct tone for a volunteer
- Judge prompt in `eval/prompts/judge.md`, run with `claude -p --permission-mode dontAsk --allowedTools "Read"`
- Calibrate: one human (not the Author of the prompt) scores 5 plans; report agreement with the judge
- Document known failure modes: favours longer answers, favours its own wording, cannot see factual
  errors (that is why facts are checked by code, not by the judge)

## Constraints
- The judge never decides pass/fail for facts; only the code checks do
- `eval/prompts/judge.md` is written by a human and changed only with a prompt-log line

## Acceptance (all must pass)
- `python eval/judge.py` writes valid `out/judge.json` with all four scores
- Calibration table and failure modes are documented in `docs/llm-judge.md`

## Out of scope
Using the judge as a retry signal (it would grade its own homework)
