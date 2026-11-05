# Task 015: Weekly automatic grant update using "Sist endret"

## Goal
`python harness/update_grants.py` keeps `context/grants/` current without a human, as long as no
verified fact changes. Anything that might change a fact goes to a human.

## Context
- Every county grant page ends with `Sist endret dd.mm.yyyy hh.mm`. Each grant file stores it as
  `source_modified: YYYY-MM-DDTHH:MM`, plus `checked_at` (last confirmed against the live page).
- **Compare with the stored value, not with "the last 7 days".** A 7-day window misses a change if
  one weekly run is skipped or fails; comparing with `source_modified` never does.
- We still fetch each page once a week (the date is on the page), so this saves processing, not
  requests: about 20 requests per week for the county.
- Actions per grant (report in `out/update_report.json`):
  | Action | When | Effect on the grant file |
  |---|---|---|
  | `unchanged` | same Sist endret | only `checked_at` = today |
  | `touched` | newer date, same text | `source_modified`, `checked_at` |
  | `updated_text` | newer date, text changed, but no number, date or amount changed and "Hvem kan søke" and "Frister og rapportering" unchanged | body replaced verbatim, `fetched_at`, `source_modified`, `checked_at` |
  | `needs_review` | anything that may change a fact | **untouched**; draft written to `context/grants_pending/<id>.md` |
  | `failed` | request failed, no "Sist endret", a heading missing (template change) | **untouched**, reason given |
  | `skipped_manual` | domain policy is `manual` | untouched, no request |
- Facts (`url`, `applicant_orgforms`, `region_prefix`, `requires_frivillighetsregisteret`,
  `target_group`, `max_amount_nok`, `deadlines`, `title`, `verified_by`) are **never** written by code.
- Expect the **first** automated run on each hand-copied file to give `needs_review`, because the
  updater's extraction will not match the human copy line for line. That is the one-time human check
  the design wants; after it, the file is in the updater's format.
- Sanitizer: drop the page's "Kontakt" block and `<meta name="author">`, then still run the e-mail and
  phone patterns. The live pages name a caseworker in both places.
- A file that keeps failing is not refreshed, so `check_grants.py` turns red after 30 days. That is
  the staleness alarm.
- Scheduling: `.github/workflows/update-grants.yml` (weekly cron). If the report has only
  `unchanged`/`touched`/`updated_text` and `check_grants.py` passes: commit. Otherwise: open a PR with
  the drafts, which is the human gate. Kill switch: if 2 or more grants are `failed` with a template
  reason in one run, write nothing and open an issue.

## Constraints
- Do not edit eval/ or fixtures/update_cases/*/expected.json; standard library only (`html.parser`)
- CLI used by the check:
  `python harness/update_grants.py --offline --pages-dir D --grants-dir G --pending-dir Q --sources S --report R --today YYYY-MM-DD`
  (live mode: same, without `--offline`/`--pages-dir`; defaults to `context/...`)

## Acceptance (all must pass)
- `python eval/check_update.py` prints PASS on all cases in `fixtures/update_cases/`
- `python eval/check_grants.py` still passes after a live run
- The check failed before this task started (red first)

## Fixtures (humans make these, before the task)
Save one real county page with the fetcher, then make variants by hand. In **all** of them, replace
the real caseworker with a fictional one, so no real personal data is committed. Variants: same date;
newer date with the same text; newer date with one reworded sentence; newer date with a changed
deadline; "Sist endret" removed; a missing page; a manual-policy domain.
Write `expected.json` per case before the updater exists.

## Out of scope
New grants (task 016), municipal pages, PDFs
