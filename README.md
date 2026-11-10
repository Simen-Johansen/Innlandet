# Innlandet

Course project, KIUA2003. Agentic workflow, work in progress. See [SPEC.md](SPEC.md).

## Setup

1. Python 3.12 or newer, available as `python`. Harness and checks use the standard library only.
2. Copy `.env.example` to `.env` and fill in values.
3. Run the checks for each stage, e.g. `python harness/entity.py fixtures/input_hamar.json --offline`,
   then `python eval/check_entity.py`. Every check must print PASS. The checks in `eval/` are the source of truth.
4. Optional extra unit tests: `python -m pytest` (needs pytest installed).

## Offline run

One command runs the whole chain (stages 1–6) on the saved Brreg fixtures, with a check after each stage.

**You need**
- Python 3.12 or newer, started as `python` (check: `python --version`).
- Claude Code CLI, logged in (check: `claude --version`; log in once with `claude`). Stages 4 and 5 call it.
- A terminal opened in the repo folder. PowerShell, cmd or bash all work.

**1. Check the wiring (free, no model calls)**
```
python harness/run.py --offline --dry-run
```
This prints six lines, `[1] entity` to `[6] render`, each showing its input, output and check.
It runs nothing.

**2. Run the chain** (about 0.30 USD)
```
python harness/run.py --offline
```
It uses `fixtures/input_hamar.json` by default. To use another request, give its path first:
`python harness/run.py fixtures/input_bad_checksum.json --offline`.
Each stage prints a line such as `[4] matcher  attempt 1/3 (0.14 USD)  check PASS`. The last line starts
with `ok:` when everything has passed.

**3. Read the result** in `out/grant_action_plan.md`. Other files in `out/`:
`plan.json` (the same plan as JSON), `cost_log.jsonl` (one line per model call), and the files each
stage hands to the next.

**Exit codes**

| Code | Meaning | What to do |
|------|---------|------------|
| 0 | Plan delivered | Open `out/grant_action_plan.md` |
| 1 | A check failed | Read the `FAIL:` line printed above it. The model stages (4, 5) were already tried 3 times |
| 1 | Brreg or `claude` is down (`upstream_unavailable` in `out/rejection.json`) | Not your input: try again later. Brreg was already retried twice |
| 3 | Input rejected (expected for bad input) | Read `out/rejection.json` for the reason |
| 4 | Halted by the kill switch | Read `out/HALTED`, fix the cause, then delete the file. Every run exits 4 until you do |

See the exit code in PowerShell with `$LASTEXITCODE`, in bash with `echo $?`.

**Good to know**
- `out/` is emptied at the start of every run, so copy anything you want to keep first. Only the
  kill switch state survives: `out/HALTED`, `out/run_history.jsonl` and `out/cost_history.jsonl`.
- Each model call has a 0.50 USD budget cap, a run stops (exit 1) once it has spent 1.50 USD, and
  the kill switch halts (exit 4) above 5 USD in 24 h, after 3 failed runs in a row, or when a grant
  file was last checked more than 30 days ago. See `docs/safe-operation.md`.
- Rejected input (for example a bad orgnr) stops before any model call and costs nothing.
- `claude CLI not found on PATH`: install Claude Code, open a new terminal, and try `claude --version`.
- Fault injection (task 013): set `FAULT` to `brreg_timeout`, `brreg_500`, `brreg_429`,
  `brreg_500_once`, `brreg_429_once`, `brreg_silent`, `claude_missing` or `claude_badjson`
  (comma-separated for several) to simulate a broken dependency, also with `--offline`. Unset, it
  does nothing. See `harness/faults.py` and `docs/stress/013-stress-dependency.md`.
- Leave out `--offline` to look the club up live in Brreg. Grants are read from `context/grants/`,
  unless `GRANTS_DIR` is set; `EVAL_TODAY=YYYY-MM-DD` fixes the date the filter uses.

## Evaluation (task 009)
`python eval/run_eval.py` runs every case in `eval/cases/` against the frozen corpus
`eval/corpus/grants/` (never `context/grants/`), 3 runs per case that calls the model.
It prints a pass/fail table, writes `out/eval_report.json` and a raw log in `docs/eval-logs/`, and
exits 0 only if all cases pass. `--case NAME` runs one case, `--runs 1` is a cheap smoke test.
A full run costs up to about 3 USD per model run, roughly 27 runs, so check the budget first.
Each case's `expected.json` is written by the Author before the case is first run.
Refreshing the corpus is a human act: copy, re-check every `expected.json`, commit.
