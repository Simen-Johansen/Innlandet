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
- `--dry-run`: print each stage, its input → output and its check, then exit 0 without running anything
- Find claude with `shutil.which("claude")`; fail clearly if missing
- Log each claude call's cost (from `--output-format json`) to `out/cost_log.jsonl`

## Constraints
- Do not edit eval/
- Stop at the first failing check (like `set -e`); clear `out/` at start (stale output fakes a PASS)
- Exit 3 propagates from stage 1 or 3 rejections without calling the model

## Acceptance (all must pass)
- `python harness/run.py --offline --dry-run` prints 6 stages and exits 0
- `python harness/run.py --offline` exits 0 and `out/grant_action_plan.md` exists
- `python harness/run.py --offline fixtures/input_bad_checksum.json` exits 3 and `out/cost_log.jsonl`
  has no entries (no tokens spent on rejected input)
- README.md has an "Offline run" section your partner follows **without asking you**

## Out of scope
Live grant fetching, the test set (task 009)
