# Stress test B: dependency failure (task 013)

## Protocol
Six eval cases in `eval/cases/stress_dep_*`, all on the Hamar request (970029028); inputs, faults and
expectations in `eval/cases/CASES.md`. The fault is injected through the `FAULT` environment variable,
read only by `harness/faults.py` (a no-op when unset). `eval/run_eval.py` sets `FAULT` from the case's
`fault` key (empty for every other case, so a `FAULT` left in the shell never leaks into normal cases);
`fault` was added to the allowed keys by the Author. The hooks sit in front of the real call, also with
`--offline`, so the same error path runs as against the live API, without breaking it.

| FAULT | Simulates | Hook |
|---|---|---|
| `brreg_timeout` | the request hangs (raised at once as `TimeoutError`, no real wait) | `entity.fetch_once()` |
| `brreg_500` / `brreg_429` | server error / rate limit on every attempt | `entity.fetch_once()` |
| `brreg_500_once` / `brreg_429_once` | the first attempt fails, the retry succeeds | `entity.fetch_once()` |
| `brreg_silent` | 200 OK, `registrertIFrivillighetsregisteret` missing | `entity.fetch()` on the response |
| `claude_missing` | `claude` not on PATH | `run.call_claude()` |
| `claude_badjson` | `claude` exits 1 with non-JSON (the real CLI is never called) | `run.call_claude()` |

Every case expects exit 1 with `upstream_unavailable` in `out/rejection.json`: an outage is neither a
rejected input (exit 3) nor a delivered plan, and must never produce a partial one.

Order: fault injection added with no behaviour change → six cases run on the old code (all at once, log
`docs/stress/013-before/eval_all.log`, then each alone for a clean `out/` snapshot in
`docs/stress/013-before/<case>/`) → trace → repair → rerun. `out/run_history.jsonl` and
`out/cost_history.jsonl` were backed up before and restored after the runs before repair, and
`out/HALTED` (written by the old code, see stress_dep_06) was deleted.

## Before repair (0.00 USD, no model call)

| Case | Exit | Eval | What happened |
|---|---|---|---|
| stress_dep_01 Brreg timeout | 1 | **FAIL** | `TimeoutError` traceback out of `entity.py`; no `rejection.json`, no reason, no retry. `run.py` only says "entity.py exited 1" |
| stress_dep_02 Brreg 500 | 3 | **FAIL** | `rejected: not_found`: a server error is reported as "the club does not exist" |
| stress_dep_03 Brreg 429 | 3 | **FAIL** | Same: rate limit reported as `not_found`, no retry |
| stress_dep_04 Brreg silent | 3 | **FAIL** | Caught, but as `not_found` (exit 3). The field was **not** silently read as false (see trace) |
| stress_dep_05 claude missing | 1 | **FAIL** | `sys.exit(1)` from inside `call_claude()`: no reason written, and `record_run` skipped, so the run is not even in `run_history.jsonl` |
| stress_dep_06 claude non-JSON | 1, 1, **4** | **FAIL** | Each run used all 3 matcher attempts on a broken CLI ("matches.json does not exist" ×3). The third run in a row **tripped the kill switch** (exit 4, `out/HALTED`: "3 consecutive runs failed the verification gate"), which blocks every later run until a person deletes the file |

## Perturbation trace

| Perturbation | First stage affected | Where it was (or was not) caught | Why the repair interrupts it |
|---|---|---|---|
| 1. Brreg timeout | Stage 1, `fetch()` | Not caught: only `HTTPError` was handled, so the exception crashed the stage | `fetch()` retries `TimeoutError`/`URLError` twice (1 s, 2 s), then raises `UpstreamError` → `rejection.json` `upstream_unavailable`, exit 1 |
| 2. Brreg 500 / 429 | Stage 1, `fetch()` | Caught, wrongly: every `HTTPError` became `not_found` (exit 3), so an outage told the user their org number was unknown, and `run_eval` counts `not_found` as a pre-model rejection | Only 404/410 (unknown or deleted entity, brreg-api skill) stay `not_found`. 429 and 5xx are retried, then `upstream_unavailable`; other 4xx are `upstream_unavailable` at once |
| 3. Brreg silent degradation | Stage 1, `extract()` | Caught already: `extract()` refused a *missing* field (task 001 followed the brreg-api skill: "do not default it to false"). The predicted bug, a missing field read as `false` that quietly removes grants requiring registration (`filter.py` `requires_frivillighetsregisteret and not entity[...]`), was **not present**. Two real gaps remained: the wrong reason (`not_found`), and a field present but `null` (or `"true"`) was copied through. Only `eval/check_entity.py` (requires a bool) stood between that and the filter, where `None` would act as false | Schema check in `extract()`: the field must be a real `bool`, and `organisasjonsnummer` must equal the requested orgnr; otherwise `upstream_unavailable` |
| 4a. `claude` not on PATH | Stage 4 (first model call) | Caught, poorly: bare `sys.exit(1)`, no reason, no run-history entry | `call_claude()` raises `UpstreamUnavailable`; `main()` writes `rejection.json` and records the run with its reason |
| 4b. `claude` exits 1, non-JSON | Stage 4 | Treated as a model mistake: retried with check feedback (useless for a broken CLI); 3 such runs → kill switch | Non-JSON **and** a failed or timed-out CLI stops at once with `upstream_unavailable`. Valid JSON with `is_error` (a real model answer) still goes through the check and retry loop as before |
| 5. Kill switch on outages | `record_run()` | Fired: an outage counted as a code failure, so a 3-run Brreg/claude hiccup needed a person to restart the service | Runs ending in `upstream_unavailable` are logged with that reason but neither count towards nor reset the 3-failure streak |

## Repairs
1. **Retry with backoff** (`harness/entity.py` `fetch()`, `fetch_once()`): at most 3 attempts, waits
   `BACKOFF_S = (1, 2)` s, on 429, 5xx, timeouts and network errors. Each failed attempt is printed
   ("Brreg attempt 1 failed (HTTP 429), retrying in 1 s"). 404/410 stay `not_found` (exit 3).
2. **Schema validation of the Brreg response** (`harness/entity.py` `extract()`): object, matching
   `organisasjonsnummer`, boolean `registrertIFrivillighetsregisteret`. Otherwise `UpstreamError`.
3. **Explicit `upstream_unavailable`, exit 1** (`entity.py` `UpstreamError`, a subclass of `Rejection`;
   `run.py` `UpstreamUnavailable`, `upstream_failure()`): the reason and detail go to `out/rejection.json`,
   `plan.json` is removed. `run.py` reads the reason back for `record_run()`. Not added to
   `PRE_MODEL_REASONS` (the claude faults happen after a logged, unknown-cost call).
4. **claude failures** (`harness/run.py` `call_claude()`): missing CLI and non-JSON-plus-failed CLI raise
   `UpstreamUnavailable` instead of `sys.exit` or three retries.
5. **Kill switch** (`harness/run.py` `record_run()`): outages logged with `"reason": "upstream_unavailable"`
   and left out of the consecutive-failure count.
6. Docs: `README.md` (exit 1 row, fault injection), `SPEC.md` (exit codes), `docs/safe-operation.md`
   (kill switch).

## After repair
Fault cases, `python eval/run_eval.py --case stress_dep_…` (2026-11-10, log
`docs/eval-logs/eval_2026-11-10_230552.log`): **6/6 passed**, 0.00 USD. Eight outage runs in a row
(stress_dep_06 runs 3 times) and no `out/HALTED`.

| Case | Runs | Result |
|---|---|---|
| stress_dep_01 Brreg timeout | 1/1 | PASS: 3 attempts, "Brreg unavailable after 3 attempts, last: TimeoutError" |
| stress_dep_02 Brreg 500 | 1/1 | PASS: 3 attempts, then `upstream_unavailable` (was `not_found`, exit 3) |
| stress_dep_03 Brreg 429 | 1/1 | PASS: same, HTTP 429 |
| stress_dep_04 Brreg silent | 1/1 | PASS: "no boolean registrertIFrivillighetsregisteret field (got 'nothing')" |
| stress_dep_05 claude missing | 1/1 | PASS: reason written, run recorded |
| stress_dep_06 claude non-JSON | 3/3 | PASS: stops on the first attempt, no kill switch (was exit 4 on run 3) |

Other evidence (2026-11-10):
- **Retry recovers:** `FAULT=brreg_429_once` and `FAULT=brreg_500_once` with
  `python harness/entity.py fixtures/input_hamar.json --offline`: one failed attempt, then
  `ok: HAMAR OG HEDEMARKEN TURISTFORENING (970029028)`, exit 0.
- **No-op without FAULT:** all seven Brreg fixtures give the same result as before (six exit 0,
  995378825 `outside_innlandet`); `python harness/run.py --offline` exit 0, plan delivered, 0.15 USD;
  every stage check (`entity`, `grants`, `filter`, `matches`, `plan`, `render`, `run`, `budget`,
  `fixtures`, `catalog`, `sources`, `killswitch`) PASS; `python -m pytest` 5/5.
- **All model-free cases** (09, 10, stress_03a/b/c, six stress_dep), log
  `docs/eval-logs/eval_2026-11-10_230709.log`: 11/11 passed.
- An unknown `FAULT` value (for example a typo) stops with a `ValueError` naming the known values,
  instead of silently testing nothing.

Full test set `python eval/run_eval.py`: **not yet run after the repair.** The 24 h model cost was
2.91 USD when the repair was done and a full eval costs about 2.3 USD, so it would hit the 5 USD
cap (`DAY_BUDGET_USD`) midway and halt by design. To be run once the window allows; result goes here.

`eval/check_update.py` FAILs ("harness/update_grants.py does not exist"): that is the check for task 015,
not built yet, and unrelated to this task.

## Limits
- The timeout is simulated by raising `TimeoutError` at once; a real hang is bounded by `TIMEOUT_S = 10`
  per attempt (so up to about 33 s with backoff), which was not measured live.
- Faults are injected in our own code, in front of the real call; the live Brreg status codes for 429
  and 5xx were not provoked against the real API (by design: the task forbids breaking it).
- A claude timeout (`CLAUDE_TIMEOUT_S = 600`) is handled by the same path as `claude_badjson` but has no
  case of its own: it would take 10 minutes.
- No load testing (out of scope).
- The silent-degradation bug the task expected was already guarded against; the honest finding is the
  wrong reason code and the `null` gap, both closed.
