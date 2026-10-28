# Task 003: Deterministic eligibility filter (stage 3)

## Goal
`python harness/filter.py` reads `out/entity.json` and `context/grants/`, and writes
`out/eligible.json` (kept and rejected grants, each with a reason) and `out/match_input.md`
(the only context stage 4 will see).

## Context
- Rules, in this order, each one a pure function with its own reason code:
  1. `org_form_not_allowed`: `organisasjonsform` not in `applicant_orgforms`
  2. `outside_region`: `kommunenummer` does not start with `region_prefix`
  3. `not_in_frivillighetsregisteret`: required but `registrertIFrivillighetsregisteret` is false
  4. `no_open_deadline`: every deadline is before today
- `out/eligible.json` = `{"today": "YYYY-MM-DD", "kept": [ids], "rejected": [{"grant_id", "reason"}]}`
- `out/match_input.md` starts with `# Project idea`, then one `## Grant: <id>` section per **kept** grant
  (`harness/filter.py input_request.json` takes the request file to get the idea), containing only `id`, `title`, `## Formål`
  and `## Hva kan det søkes om`. This is our context filter: the model never sees rejected grants,
  URLs, amounts or deadlines, so it cannot invent or mix them up.

## Constraints
- Do not edit eval/
- No LLM. Standard library only. Uses `load_grants()` from task 002
- "Today" comes from a `--today YYYY-MM-DD` argument (default: real date) so tests are repeatable
- If no grant survives: write `out/eligible.json` with `kept: []` and exit 3 with
  `out/rejection.json` reason `no_eligible_grants`

## Acceptance (all must pass)
- `python harness/filter.py fixtures/input_hamar.json --today 2026-10-30 && python eval/check_filter.py` prints PASS
- The check failed before this task started (red first)

## What eval/check_filter.py asserts
- `kept ∪ rejected` = all grant ids, no overlap
- every rejected entry has one of the four reason codes
- re-computes all four rules independently (same order, `today` from the file) and gets the same reasons
- `## Grant:` sections in `out/match_input.md` = kept ids exactly
- `out/match_input.md` contains no rejected grant id, no `http`, no `NOK`/`kr` amounts, no ISO dates

## Out of scope
Topic matching (that is stage 4's judgment)
