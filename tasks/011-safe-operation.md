# Task 011: Safe operation (exam Section 3.2)

## Goal
Every safe-operation measure is implemented, measurable, and documented in `docs/safe-operation.md`.

## Context
| Measure | Implementation |
|---|---|
| Permission scoping | `.claude/settings.json`: deny `Read(./.env)`, `Edit(/eval/**)`, `Edit(/context/**)`; agent stages run with `dontAsk` + `Read,Edit(/out/**)` |
| Secrets | `.env` in `.gitignore` since the first commit; `.env.example` holds names only; `git check-ignore .env` in CI |
| Cost control | `--max-budget-usd 0.50` per claude call; run.py sums `out/cost_log.jsonl` and stops a run above 1.50 USD |
| Human gate | The plan is written to `out/` only; nothing is sent to a club or posted. Grant file updates need human review (task 010). Justify both in the doc |
| Kill switch | run.py writes `out/HALTED` and exits 4 if: 3 consecutive runs fail the verification gate, **or** 24 h cost > 3 USD, **or** a grant file is older than 30 days. It refuses to run while `HALTED` exists; a human deletes it |
| Abandonment criterion | Write it down, e.g. "if the hallucination check fails on more than 20 % of eval cases after two prompt revisions, we drop stage 5 and render the plan from frontmatter only" |

## Constraints
- Do not edit eval/ (except adding new checks, which the Author does)

## Acceptance (all must pass)
- `python eval/check_killswitch.py`: simulates 3 failed runs → exit 4 and `out/HALTED` exists; the next run also exits 4
- `python eval/check_budget.py`: a fake cost log above the cap stops the run before any claude call
- `docs/safe-operation.md` has one paragraph per row above

## Out of scope
Container sandboxing
