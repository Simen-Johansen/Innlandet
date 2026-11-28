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
A full run is 25 cases: 15 reach the model and run 3 times, 10 stop before it and run once. It costs about
3.3 USD (Run A, 23 cases: 2.49 USD), so check the budget first (kill switch: 5 USD per 24 h).
Every case runs on the `today` in its `expected.json` (2026-11-27, case 06 2026-12-02), not on the real date.
Each case's `expected.json` is written by the Author before the case is first run.
Refreshing the corpus is a human act: copy, re-check every `expected.json`, commit.

## Weekly grant update (task 015)
`python harness/update_grants.py` compares each county page's "Sist endret" with the stored
`source_modified` and writes `out/update_report.json`. It only refreshes dates and wording; anything that
may change a fact becomes a draft in `context/grants_pending/` for a human. Offline test:
`python eval/check_update.py`. `.github/workflows/update-grants.yml` ran it weekly in CI until the exam freeze
(26.11). Now it runs only by hand (see below).

## Submitted version and reproducing it later (for the evaluator)

**Set this date first, in the same terminal, before any command: `EVAL_TODAY=2026-11-27`.** That is the frozen
reference date for the final eval (Run B). Run B itself ran on 2026-11-29 with this reference date; the repo was
submitted on 2026-12-03, and the results hold for 2026-11-27 whatever day you run it.
- bash: `export EVAL_TODAY=2026-11-27`
- PowerShell: `$env:EVAL_TODAY = "2026-11-27"`
- cmd: `set EVAL_TODAY=2026-11-27`

Then check out the submitted commit and follow "Setup" and "Offline run" above:
```
git checkout exam
python harness/run.py --offline --dry-run
python harness/run.py --offline
```

| Command | Date it uses | You set |
|---|---|---|
| `python eval/check_*.py`, `python harness/run.py --offline` | `EVAL_TODAY` | `EVAL_TODAY=2026-11-27` |
| `python eval/run_eval.py` | its own fixed dates: **2026-11-27** for every case, except 06 (deadline passed), which uses **2026-12-02**; frozen corpus `eval/corpus/grants/` | nothing (it overrides `EVAL_TODAY`) |
| `python eval/judge.py` | none (scores a plan, advice only) | nothing |

**Why 2026-11-27 and not the submission day.** The running example (`fixtures/input_hamar.json`, an outdoor project)
is expected to match "Tilskudd til friluftslivsaktivitet" (`fixtures/expected_matches.json`). That grant's only
deadline is 2026-12-01. On any later date the filter correctly drops it (`no_open_deadline`), so the
matcher check (`check_matches.py`) fails, and `run.py` exits 1 after it has called the model. That is the right
answer for that date, but it is not the submitted result. On 2026-11-27 every check passes and the eval has the
same dates.

**If you forget `EVAL_TODAY`.** Then the real date is used:
- from 2026-12-02, the running example fails at stage 4 as described above (exit 1, about 0.20 USD spent);
- from **2026-12-25**, the grant files are also more than 30 days past `checked_at`. `check_grants.py` FAILs, and
  `run.py` halts with exit 4 (`out/HALTED`) before any model call.

Delete `out/HALTED` if it exists, set the date and run again. The "generated" date at the top of the plan is
always the real date, and only that line differs.

**What else to know**
- Use `--offline`. It reads the saved Brreg fixtures. Live Brreg data may have changed since submission.
- `run.py --offline` (about 0.30 USD) and `run_eval.py` (about 3.3 USD) call the model, so they need a logged-in
  Claude Code CLI. The dry run, every `check_*.py` and `python -m pytest` are free.
- **The repo is frozen.** The tag `exam` is the submitted commit and the last commit; it is never moved. The weekly
  grant update (`update-grants.yml`) has no schedule and is disabled on GitHub, so nothing commits after the tag.
  It also does nothing if someone starts it by hand while the tag exists. CI (`checks.yml`) runs only on pull
  requests and manual runs, never commits, and sets `EVAL_TODAY=2026-11-27` itself.
