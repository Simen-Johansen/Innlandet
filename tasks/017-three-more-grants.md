# Task 017: Three more county grants in the corpus before Run B (B3, widened)

## Goal
Grow the frozen eval corpus from 5 to up to 8 real grants (6 county + Hamar + synthetic), so Run B shows
whether the matcher can tell **overlapping** grants apart, not only that it passes on 5. Every new fact is
human-checked (four eyes), every `eval/` edit is made by a human, and Run B stays the one final run on one
frozen corpus. Coverage moves from `ingested/relevant = 4/24` to up to `7/24`.

## Context
- Decided 26.11 (Simen): Run B moves from Thu 26.11 to **Fri 27.11**. **Hard cut-off Fri 27.11 10:00**: a grant
  that is not through step 6 by then stays `deferred_verification`, and Run B runs on what is ready. No grant is
  added after Run B (the corpus is frozen then; see ROADMAP "Reproducible after submission").
- State at start: corpus refresh C4 committed `96abccc` (26.11): A, D, F, K, H + 2 synthetic files in
  `eval/corpus/grants/`; case 13 added; A in `must_reject` of 11 cases. Free checks PASS. 24 h spend 0 USD.
- Candidates (proposed by Claude from the catalog titles, pages **not yet read**; step 0 confirms or swaps):
  | Code | Catalog page_id | Grant | Why it is a good test |
  |---|---|---|---|
  | N | 37168 | Fondsordning til store nasjonale og internasjonale arrangementer innen idrett | neighbour of A: regional event → A, national/international event → N |
  | R | 62589 | Regionalt kulturfond Innlandet | overlaps K: regional reach, arts for youth vs arts in general |
  | U | 58403 | ULF – Ungdommens livskvalitetsfond | youth grant across sport, culture and outdoor life: invites false matches |
  Backups if a candidate is not open to FLI clubs or cannot be expressed in the frontmatter:
  62588 Tilskudd til utviklingsprosjekt kunst og kultur, 22177 organisasjoner for mennesker med nedsatt
  funksjonsevne. **Not** Spillemidler (18103): applied for through the municipality, rules do not fit the
  frontmatter.
- File format and sources: `innlandet-grants` skill. innlandetfylke.no is `auto` in `context/sources.json`, so
  once a file is in `context/grants/`, the weekly `update_grants.py` keeps it current.
- Two known failures shape the review: the **date gap** (a deadline covers a project period; `deadlines` holds only
  the date) and **HHT/arrangementsutvikling** (affiliation rules such as NIF/DFS/NBF are not a filter field, so
  only the matcher can apply them). Write both kinds of rule down per grant in the review sheet.
- `add_must_reject.py` (C4) re-serialised each `expected.json` with `indent=2`; case 12's diff was +17/−6 for one
  id. The reusable tool must write a minimal diff.
- `python harness/run.py` (also `--dry-run`) clears `out/`. Anything a human must review lives in
  `docs/grant-expansion/`, not `out/`.

## Who does what
- **Claude may:** read live pages (innlandetfylke.no, policy `auto`, our User-Agent), write drafts, tools and
  proposals under `docs/grant-expansion/` and `tools/`, run free checks, run the screening tool.
- **Claude may not:** edit `context/**` or `eval/**` (settings deny it), read existing `eval/cases/*/expected.json`
  contents (the tools read them; Claude reads only their printed summary), commit without a go-ahead.
- **Humans (Simen + Elias):** every frontmatter fact, every decision, every copy into `context/` and `eval/`.

## Steps per grant (in this order)
0. **Confirm the pick (Claude, free).** Read the live page; report in one table per candidate: applicant types,
   region, Frivillighetsregisteret, amount, deadlines and the project period each covers, any rule the filter cannot
   express. Simen confirms or swaps to a backup.
1. **Draft (Claude, free).** `python tools/draft_grant.py <page_id>` writes `docs/grant-expansion/grants/<id>.md`
   (body verbatim under the five headings + `### <page heading>` extras, Kontakt block and author removed, e-mail
   and phone patterns redacted; facts left as `TODO`) and `<id>.checklist.md` (every page heading, every amount
   and date found on the page, the fields a human must fill, and the project period per deadline).
2. **Facts (human, four eyes).** One person fills `applicant_orgforms`, `requires_frivillighetsregisteret`,
   `region_prefix`, `target_group`, `max_amount_nok`, `deadlines`, `title`, `url`; the other checks them against the
   live page, not against the draft (the 11.11 lesson). Set `verified_by`, `checked_at`.
3. **Into the product (human copy).** `cp docs/grant-expansion/grants/<id>.md context/grants/`; set its
   `context/catalog.json` status to `ingested`; `python eval/check_grants.py` and `python eval/check_catalog.py` PASS;
   `python harness/update_grants.py --audit` shows no mismatch for the new file.
4. **Screen every case (Claude runs, free).** `python tools/screen_cases.py --add docs/grant-expansion/grants`
   (see Tools). Output `docs/grant-expansion/decisions.tsv`: one row per (case, new grant), with the filter result,
   the project idea and an empty `decision` / `decided_by`. Claude may add a `proposal` + one-line `why` per row.
5. **Decide (humans).** For each row: `must_reject`, `must_match`, or `leave_out` (genuine grey area, say why),
   initials in `decided_by`. A `must_match` for a new grant in an old case is allowed only if the grant really
   fits; it changes what that case tests, so add a `CASES.md` note.
6. **New cases (Claude proposes, humans own).** Per grant ≥1 `must_match` case and, if possible, 1 near-miss
   `must_reject` case (e.g. a regional event for N, a one-municipality arts project for R). Claude writes the
   proposal to `docs/grant-expansion/cases/<NN>_<name>/` (`input_request.json`, proposed `expected.json` with
   `today`, a README with the reasoning per grant, including A, D, F, K, H). The club's Brreg fixture comes from
   `harness/entity.py` live lookup (allowlisted copy, no roles endpoint). Humans check, then
   `cp -r` into `eval/cases/` and add the `CASES.md` row.
7. **Apply decisions (human eval edit).** Copy the grant into `eval/corpus/grants/`, then
   `python tools/add_expectation.py docs/grant-expansion/decisions.tsv --check`, then without `--check`;
   `git diff eval/cases`: each changed file gains exactly the decided ids.
8. **Free checks.** `python harness/run.py --offline --dry-run`;
   `for c in grants fixtures sources update budget killswitch catalog; do python eval/check_$c.py; done`;
   `python tools/screen_cases.py` once more (now on `eval/corpus/grants/`): every decided `must_reject` with a filter
   reason is filtered as expected.
9. **Log.** One `docs/prompt-log.md` entry (eval edit by humans, which grants, which cases changed and why, any
   grant dropped at the cut-off); `CASES.md` grant-id list gets N/R/U and one sentence each.

## Tools (Claude builds, standard library only, pathlib, `encoding="utf-8"`)
- `tools/draft_grant.py <page_id> [--offline --pages-dir D]`: the minimal task 016. Reuse `extract`, `sanitize`,
  `redact`, `render`, `page_dates`, `checklist_md` from `harness/update_grants.py` (import, do not copy), page URL
  from `context/catalog.json`. Never writes into `context/`. Saves the raw page to `fixtures/pages_raw/` only after
  sanitizing.
- `tools/screen_cases.py [--add DIR] [--grants-dir DIR]`: for every case in `eval/cases/`, run stage 1
  (`harness/entity.py`, offline fixtures) and stage 3 (`harness/filter.py --today <case today>`) as subprocesses
  with `GRANTS_DIR` = a temporary corpus (= `eval/corpus/grants/` + `--add` files, built in a temp dir, deleted after).
  From `expected.json` it reads only `today` and whether the case reached the matcher before; it prints and writes
  per (case, grant): `filtered: <reason>` or `kept: matcher decides`, plus kommunenummer, org form,
  Frivillighetsregisteret, project idea. It never prints the existing `must_match` / `must_reject` lists
  (with `--show-current`, a human may). Restores nothing in `out/` it did not write; leaves `eval/` untouched.
- `tools/add_expectation.py <decisions.tsv> [--check]`: the reusable `add_must_reject.py`. Applies only rows with
  `decided_by` filled and `decision` in {`must_match`, `must_reject`}. Refuses (writes nothing) if: the grant is
  not in `eval/corpus/grants/`; the id is already in the opposite list; the case dir is missing. Minimal diff:
  inserts the id into the existing array text and keeps the file's layout; if it cannot, it refuses that file and
  prints the line to add by hand. Prints `would add` / `added` per row and a count. Humans run it.
- Tests in `tests/` for the three tools on saved fixtures (draft privacy, screen on a temp copy, add_expectation
  refusals and minimal diff); pytest stays green.

## Constraints
- Do not edit `eval/` or `context/` (humans copy). Do not change any check. No personal data: no Kontakt block,
  no caseworker names, e-mails or phones; Brreg via the allowlisted fixture only, never the roles endpoint.
- No model calls in steps 0–8 (all free). Spend stays at 0 until Run B.
- The facts in the frontmatter are human-written; code fills only `id`, `title` (draft), `url`, `provider`,
  `fetched_at`, `source_modified`, body.

## Acceptance (all must hold before Run B)
- Each added grant: `verified_by` set by a human, catalog status `ingested`, file identical in `context/grants/`
  and `eval/corpus/grants/`, ≥1 `must_match` case, decided row for every case that reaches the matcher.
- `check_grants`, `check_fixtures`, `check_sources`, `check_update`, `check_budget`, `check_killswitch`,
  `check_catalog` PASS; dry run OK; pytest green.
- `git diff eval/cases` shows only decided ids, new case dirs and `CASES.md`; prompt-log entry written.
- Any grant not done by Fri 27.11 10:00 is reported as not added, stays `deferred_verification`, and is named in the
  prompt log.

## Then: Run B (task 013), Fri 27.11
Pre-flight: `out/HALTED` absent, `cost_last_24h` < 2 USD. `python eval/run_eval.py` (3 runs per case; with
24 cases today + 3–6 new, and ~8 grants in each matcher prompt, expect ~3.3–4 USD; Run A was 2.49 USD for
23 cases. Under the 5 USD cap, but if the estimate passes 4.5 USD, cut to `--runs 2` and say so). Log to `docs/eval-logs/`; update
`docs/stress/013-stress-dependency.md`; tick task 013. The corpus is frozen from here.

## Out of scope
Spillemidler, municipal grants other than Hamar, a project-date field (future work), changing the matcher prompt.
