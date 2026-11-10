# LLM-as-judge (task 014)

`python eval/judge.py` scores a grant action plan for plain language and helpfulness and writes
`out/judge.json`. It answers a question the code checks cannot: is the plan easy for a volunteer
to read and act on? It never answers whether the plan is *right*.

## Rubric
Each criterion gets a score of 1–5 and one sentence of justification.

| Key | Criterion |
|---|---|
| `plain_language` | Klarspråk / plain English: short sentences, everyday words |
| `actionable_steps` | The steps say who does what, in an order a club can follow |
| `no_jargon` | No unexplained jargon (grant, legal or bureaucratic terms are explained) |
| `tone` | Correct tone for a volunteer: friendly, direct, not formal or patronising |

The prompt is `eval/prompts/judge.md`. A human writes it. It is changed only with a line in
`docs/prompt-log.md`, and `judge.json` stores `prompt_sha256` so every score can be traced to
the prompt version that gave it.

## How to run
```
python eval/judge.py                                   # out/grant_action_plan.md -> out/judge.json
python eval/judge.py docs/judge-calibration/plan_2.md --out out/judge_plan_2.json
```
The judge runs as `claude -p --model sonnet --permission-mode dontAsk --allowedTools "Read"
--output-format json --max-budget-usd 0.50`. It can read the repo but cannot write, run commands
or fetch pages. The prompt tells it to treat the plan as data, because plans quote grant text
(see task 012).

Guards before the call. Each one stops with exit 1 and makes no model call:
- the plan is missing or empty;
- the prompt is missing or has no `{plan_path}` placeholder;
- `out/HALTED` exists;
- the model cost in the last 24 h is over 5.00 USD.

These are the same rules as `harness/run.py`, copied here because the checks do not import
harness code. The cost of every call goes to `out/cost_history.jsonl` with `stage: "judge"`,
so judge runs count toward the kill switch.

`judge.py` exits 0 when `judge.json` is valid, whatever the scores are. It exits 1 if the
answer does not have exactly the four keys, each with an integer score from 1 to 5 and a
non-empty justification. There is no retry.

## What the judge does not do
- **It never decides pass or fail.** Facts are checked by code, never by the judge: grant
  ids, deadlines, amounts and URLs by `check_plan.py`, and the rendered Markdown by
  `check_render.py`. The judge cannot see factual errors (see below), so making it a gate would
  let a fluent but wrong plan through.
- **It is not a retry signal.** It is not called from `run.py` or `run_eval.py`. A model
  rewriting the plan until a model judge likes it would be grading its own homework, and it
  would make plans longer and more like the judge's taste, not better for the club.

## Calibration
**Method.** One human who did not write the judge prompt scores the 5 plans in
`docs/judge-calibration/` with the rubric above. They score blind, before seeing the judge's
scores. Then the judge scores the same 5 plans with the committed prompt.

**Agreement measures.** For each criterion and overall:
- exact agreement (% of plans with the same score);
- agreement within ±1 (%);
- mean absolute difference.

| Plan | Source | Human P / A / J / T | Judge P / A / J / T |
|---|---|---|---|
| plan_1 | Hamar running example (offline run, 2026-11-11) | – | 4 / 4 / 4 / 4 |
| plan_2 | `012-before/stress_01_injection_grant_text` | – | – |
| plan_3 | `012-before/stress_02_injection_project_idea` | – | – |
| plan_4 | `012-before/stress_03c_long_idea` | – | – |
| plan_5 | eval case 02 or 12 (made after the demo) | – | – |

P = plain_language, A = actionable_steps, J = no_jargon, T = tone.

| Criterion | Exact | Within ±1 | Mean abs. diff |
|---|---|---|---|
| plain_language | – | – | – |
| actionable_steps | – | – | – |
| no_jargon | – | – | – |
| tone | – | – | – |

Human scorer: _to be named_. The table is filled after the 12 Nov demo, to keep model spend
low before it (5 USD per 24 h cap).

## Known failure modes
- **It favours longer answers.** LLM judges tend to score a longer, more complete-looking plan
  higher, even when a volunteer would rather have a short one. Probe (after the demo): judge
  plan_1 and a copy padded with polite filler and repeated advice, then compare the scores.
- **It favours its own wording.** The plans are written by Claude (stage 5) and judged by
  Claude, so the judge may reward the phrasing and structure it would use itself. A human
  scorer is the only real check on this, which is why calibration uses one.
- **It cannot see factual errors.** The judge reads only the plan. It cannot know that a
  deadline, amount or eligibility rule is wrong, or that a step was planted by injected text.
  Plans 2–4 were written before the task 012 repair: they read fluently and may still score
  well, which shows why facts are checked by code (`check_plan.py`, `check_render.py`) and never
  by the judge.
