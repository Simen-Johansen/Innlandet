# Demo runbook: Thu 12.11 13:15

Two commands. Both are short enough to type live.

## 1. One live run: the workflow (about 20 s, ~0.15 USD)
```
python harness/run.py
```
Real Brreg, real Claude, the Hamar club. While it prints, point at each line:
`[1] entity` → `[2] grants` → `[3] filter` → `[4] matcher` → `[5] guide` → `[6] render`, each with `check PASS`.
Say: code decides the order, the model only does 4 and 5, and nothing moves on until its check passes.
Then open `out/grant_action_plan.md`: that is what the club gets.

## 2. The test set: does the workflow hold up? (a few minutes, under 1 USD)
```
python eval/run_eval.py --runs 1
```
Runs all 23 cases from `eval/cases/` and prints one PASS/FAIL line per case:
normal clubs, boundary cases (deadline passed, amount too high, wrong municipality), bad input
(wrong org number, outside Innlandet), prompt injection, and Brreg/Claude being down.
Start it, explain the case groups while it runs (`eval/cases/CASES.md`), and read the total at the end.
The log is saved in `docs/eval-logs/` automatically.

## Before
`Test-Path out/HALTED` must be `False`, and `claude --version` must work.

## After (same day, required for the white paper)
Write `docs/meetings/2026-11-12-demo.md`: what ran, any FAIL seen live, and the feedback we got.
A FAIL on stage is not a disaster. It goes into the white paper, as the course asks.

## If asked
- Only 5 of the 58 county grants are in use, because a human verifies every fact first.
- The test set uses a frozen copy of the grants (`eval/corpus/`), so results do not change when the
  live grant pages change.
