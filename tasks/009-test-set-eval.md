# Task 009: Test set and evaluation harness (exam Section 3.1)

## Goal
`python eval/run_eval.py` runs the chain on every case in `eval/cases/` and prints a pass/fail table
plus totals, and writes `out/eval_report.json`.

## Context
- One folder per case: `eval/cases/<name>/input_request.json` + `expected.json`
  (`expected_exit`, `must_match` ids, `must_not_include` ids, `rejection_reason`)
- Minimum cases:
  | Type | Case | Expected |
  |---|---|---|
  | typical | Hamar sports club, ski equipment for kids | exit 0, outdoor + equipment grants |
  | typical | a youth band (FLI) asking for instruments | exit 0, culture grant, not the outdoor grant |
  | boundary | club registered in a kommune outside Innlandet | exit 3, `outside_innlandet` |
  | boundary | requested amount above every maximum | exit 0, `amount_note` present |
  | boundary | grant whose only deadline is yesterday (`--today`) | grant rejected `no_open_deadline` |
  | boundary | FLI not in Frivillighetsregisteret | grants requiring it are excluded |
  | reject | orgnr with bad checksum | exit 3, `invalid_orgnr`, 0 tokens |
  | reject | empty or off-topic project idea ("buy a car for the chairman") | exit 3 or no matches |
  | held-out | one case the agent never sees during development | kept out of tasks and prompts |
- Each case runs offline (fixtures), so results depend on our code and the model, not the internet
- Run each LLM case 3 times; report pass rate per case (model variance is data, not noise)

## Constraints
- **Author writes all cases and expected outcomes before running them.** The agent may draft input
  files, never `expected.json`
- Standard library only

## Acceptance (all must pass)
- `python eval/run_eval.py` runs all cases from one command and exits 0 only if all pass
- Raw output of one full run saved for the white paper appendix (`docs/eval-logs/`)

## Out of scope
LLM-as-judge (task 014)
