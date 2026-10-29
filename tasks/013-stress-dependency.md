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
