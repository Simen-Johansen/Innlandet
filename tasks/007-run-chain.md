# Task 007: One command runs the whole chain (walking skeleton complete)

## Goal
`python harness/run.py --offline` runs stages 1–6 in order with a check after each, retries stages 4 and 5
with the check's error text, and exits with the codes in SPEC.md.

## Context
- We use a Python orchestrator instead of `run.sh` (W43) because we develop on Windows, where
  `$(cat ...)` and `python3` do not work. Same design: code decides the order, files are the hand-offs.
- Stages and checks are a list in `run.py`; each check runs with `subprocess.run(["python", "eval/check_x.py"])`
- Evaluator–optimizer loop for stages 4 and 5: at most 3 attempts; on failure, append
  `Previous check output (fix this): <stderr>` to the prompt; after 3 failures, exit 1
- `--dry-run`: print one line per stage, `[N] name  input -> output   check: eval/check_x.py`,
  then exit 0 without running anything (format as in W43)
- Find claude with `shutil.which("claude")`; fail clearly if missing
- Log each claude call's cost (from `--output-format json`) to `out/cost_log.jsonl`

## Constraints
- Do not edit eval/
- Stop at the first failing check (like `set -e`); clear `out/` at start (stale output fakes a PASS)
- Exit 3 propagates from stage 1 or 3 rejections without calling the model

## Acceptance (all must pass)
- `python eval/check_run.py` prints PASS (dry-run wiring + bad-checksum path, model-free)
- `python harness/run.py --offline` exits 0 and `out/grant_action_plan.md` exists
- README.md has an "Offline run" section your partner follows **without asking you**

## Out of scope
Live grant fetching, the test set (task 009)
