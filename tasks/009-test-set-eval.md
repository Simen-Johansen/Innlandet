# Task 009: Test set and evaluation harness (exam Section 3.1), revised W45

## Goal
`python eval/run_eval.py` runs the chain on every case in `eval/cases/` against a **frozen grant
corpus**, prints a pass/fail table plus totals, and writes `out/eval_report.json`.

## Context
- **Why a frozen corpus:** from task 015 on, `context/grants/` changes every week. A regression test
  must compare the same inputs before and after a change, so the cases run on
  `eval/corpus/grants/` (a dated copy), never on `context/grants/`.
  Refreshing the corpus is a deliberate human act: copy, re-check every `expected.json`, commit.
- Two environment variables make this work, and every stage must honour them:
  `GRANTS_DIR=eval/corpus/grants` (read by `harness/grants.py` and `eval/common.py`) and
  `EVAL_TODAY=YYYY-MM-DD` (passed as `--today` to the filter, and used by `check_grants.py`)
- One folder per case: `input_request.json`, `expected.json`
  (`today`, `expected_exit`, `rejection_reason`, `must_match`, `must_reject`, `must_not_include`,
  `amount_note_required`), and a `brreg_<orgnr>.json` fixture if the org is new
- Cases (revised to match the corpus we actually have; the old list named grants we do not have):
  | Type | Case | Expected |
  |---|---|---|
  | typical | HHT, outdoor activity days (running example) | exit 0; friluftsliv match; driftstilskudd + kunstnerisk reject |
  | typical | FLI arts project for youth from 2+ municipalities | exit 0; kunstnerisk match |
  | boundary | the old ski-equipment idea | driftstilskudd reject (equipment excluded) |
  | boundary | the same arts project, Hamar only | kunstnerisk reject (single municipality) |
  | boundary | FLI in Stange (34xx, not 3403) | driftstilskudd rejected `outside_region` |
  | boundary | `today` = 2026-12-02 | friluftsliv rejected `no_open_deadline` |
  | boundary | arts match, 150 000 NOK requested | `amount_note` present (max 100 000) |
  | boundary | FLI not in Frivillighetsregisteret | rejected `not_in_frivillighetsregisteret` by a **synthetic** corpus grant (`provider: test_synthetic`), since no real grant requires it |
  | reject | bad checksum | exit 3, `invalid_orgnr`, 0 tokens |
  | reject | club outside Innlandet | exit 3, `outside_innlandet` |
  | reject | off-topic idea ("buy a car for the chairman") | exit 0 with no match, or exit 3 |
  | held-out | one case only the Author knows until the final run | as written by the Author |
- Each case that calls the model runs 3 times; report the pass rate per case

## Constraints
- **The Author writes every `expected.json` before running the case.** The agent may draft inputs, never expectations
- Also fix the two leftovers named in the C2 report: the ski-equipment wording in task 004 and the idea in `fixtures/input_bad_checksum.json`
- Standard library only

## Acceptance (all must pass)
- `python eval/run_eval.py` runs all cases from one command and exits 0 only if all pass
- `GRANTS_DIR=eval/corpus/grants EVAL_TODAY=2026-11-05 python eval/check_grants.py` prints PASS
- Raw output of one full run saved in `docs/eval-logs/`

## Out of scope
LLM-as-judge (task 014)
