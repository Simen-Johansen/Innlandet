# Task 013: Stress test B, dependency failure (exam Section 3.3, class 2)

## Goal
Show what happens when Brreg (or claude) fails, repair it, and prove the repair holds.

## Context
- Perturbations, injected with an environment variable `FAULT=...` that the harness reads
  (so tests are repeatable without breaking the real API):
  1. `brreg_timeout`: the request hangs
  2. `brreg_500` / `brreg_429`: server error / rate limit
  3. `brreg_silent`: 200 OK but `registrertIFrivillighetsregisteret` missing (silent degradation)
  4. `claude_missing`: `claude` not on PATH or returns non-JSON
- Silent degradation (3) is the interesting one: a missing field must not become `false` and quietly
  remove grants. Expect to find this bug, and report it honestly
- Candidate repairs: retry with backoff (max 2) for 429/5xx; schema validation of the Brreg
  response; explicit reason `upstream_unavailable` with exit 1 instead of a partial plan

## Constraints
- Do not edit eval/ checks to make a perturbation pass
- Fault injection code lives in one place (`harness/faults.py`) and is a no-op unless `FAULT` is set

## Acceptance (all must pass)
- Each fault is a case in `eval/cases/stress_dep_*` with an expected exit code
- Before/after evidence in `docs/stress/013-*`; full test set green after repair

## Out of scope
Load testing

## Remaining (status 12.11): the 3-run full eval
Done: 6 faults injected, 6/6 failed before the repair, trace written, 6/6 after the repair, and 23/23 on
1 run (`docs/eval-logs/eval_2026-11-12_082151.log`). Still open is "full test set green after repair" at
3 runs per case. Plan: `python eval/run_eval.py` (default `--runs 3`, about 2.9 USD). Do it twice, each
time in its own 24 h window. No fixed dates: run whenever the 24 h window has room (pre-flight below).

- [ ] **Run A, current corpus.** Gives time to fix surprises, so the earlier the better.
- [ ] **Run B, after the corpus refresh (the final run, before the exam deadline).** Its log is the raw
      evaluation log for the appendix.
      Only meaningful if someone has copied the new grants into `eval/corpus/` and re-checked every
      `expected.json` (README: a human act). Refreshing `context/grants/` alone does not change the eval.

Each run:
1. Pre-flight: `Test-Path out/HALTED` is `False`; `claude --version` works; the 24 h cost (command in
   `docs/demo-runbook.md`) is **below 2 USD**; the tail of `out/run_history.jsonl` has no exit-1 streak
   (3 failed runs in a row write `out/HALTED`, and the streak carries over from earlier runs).
2. Run it. If `out/HALTED` appears: stop, report it as a FAIL with the log, and let a person delete it.
3. Report each case as k/3, plus the total and the cost. A 2/3 is model variance, which is an honest
   white-paper finding, not something to fix away.
4. In `docs/stress/013-stress-dependency.md`, replace "not yet run after the repair" with the 1-run
   23/23 and the 3-run result. Also correct "about 2.3 USD" there to about 2.9 USD.
5. After Run B: mark the runbook's "still owed" line done and point the appendix at Run B's log.
6. Show the diff and ask before any commit.
