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

## Status
- [x] `eval/judge.py` with guards, judge prompt (logged in `docs/prompt-log.md`), rubric, failure modes
- [x] plan_1 judged: 4 / 4 / 4 / 4, 0.055 USD
- [x] plan_5 made from eval case 12 (Norwegian in and out), 0.16 USD
- [x] Elias scores plans 1–5 blind (Human column in `docs/llm-judge.md`), 2026-11-12
- [x] Judge plans 2–5 (2026-11-24, 0.24 USD; saved in `docs/judge-calibration/`)
- [x] Length-bias probe: plan_1 4/4/3/4 vs padded 3/3/4/3, no length bias seen (0.12 USD)
- [x] Judge column and agreement table: exact 13/20, within ±1 19/20, mean abs. diff 0.40
- [ ] White paper: say plainly that 5 plans is a small sample, so the table shows how the judge was checked, not that it is reliable

## Out of scope
Using the judge as a retry signal (it would grade its own homework)
