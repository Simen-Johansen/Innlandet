# Prompt log

One entry per significant prompt. Format:

## YYYY-MM-DD: short title
- **Who:**
- **Prompt:**
- **Outcome:**

## 2026-10-15: Implement task 001 (probe)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan Implement tasks/001-probe.md`; source chosen: NRK Innlandet RSS
- **Outcome:** `harness/probe.py` (stdlib fetch with User-Agent + cache, RSS parse),
  offline test on a synthetic fixture. Live run pending human check of the feed URL.

## 2026-10-22: Remove the NRK probe
- **Who:** Simen + Claude Code
- **Prompt:** Remove everything from the NRK Innlandet test so we can start on the task in SPEC.md
- **Outcome:** Probe, its test, fixture, task file and eval check deleted in a removal
  commit; history (PR #1) kept.

## 2026-10-28: Implement task 001 (Brreg entity)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan implement tasks/001-brreg-entity`
- **Outcome:** `harness/entity.py` (MOD11 before any request, one GET or `--offline` fixture,
  9-key flat entity, rejections exit 3). Real orgnr 942440618 (Hamarkameratene Fotball Elite)
  verified live; the fixture was sanitized (e-mail, mobile and street address removed).
  Corrected: a wrong check-digit-0 example in the agent's own unit test (123456780 → 123456750).

## 2026-10-29: Verify task 002 (grant context)
- **Who:** Simen + Claude Code
- **Prompt:** Verify the four grant files against the live pages and mark them `verified_by: SJ`
- **Outcome:** Claude compared the frontmatter with the pages; Simen confirmed the body text matches.
  All four files have `verified_by: SJ`, and `eval/check_grants.py` prints PASS.
  Corrected: `applicant_orgforms` for kunstnerisk aktivitet (`FLI, KOMM, ENK, AS, STI`) was our own
  reading, not the page's text. The page says only "Arrangører", so a frontmatter comment now says so.
  Friluftsliv keeps `FLI` only (interkommunalt friluftsråd left out on purpose).

## 2026-10-29: Implement task 004 (matcher)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan implement tasks/004-matcher`
- **Outcome:** `harness/prompts/match.md` with a three-condition match rule. The agent asked strict vs lenient;
  we chose strict because a broad purpose (driftstilskudd's "fritidsaktiviteter i Hamar") is open to two
  readings and would make verdicts unstable between runs; strict ties a match to what the grant actually funds.
  Two runs on the Hamar fixture both PASS `eval/check_matches.py` with identical verdicts:
  friluftsliv `match`, driftstilskudd `reject`, kunstnerisk `reject` (~0.13–0.14 USD each).
  Corrected: the first attempt passed the prompt from Windows PowerShell 5.1, which does not escape the
  embedded `"` and truncated the prompt; the agent then guessed the schema (`decision`, no quote) and the
  check FAILed. Calling `claude` from Python `subprocess.run([...])` (as task 007 will) fixes it.

## 2026-10-29: Implement task 005 (guide writer)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan implement tasks/005-guide-writer`
- **Outcome:** `harness/guide_input.py` copies the matched grant files to `out/guide_input/` and writes
  `request.json` (language, requested amount, idea, and `today` from `out/eligible.json`); exit 3
  `no_matching_grants` if nothing matched. `harness/prompts/guide.md` makes the model copy url, deadline
  and max amount from the frontmatter and says what to do if no attachments or no maximum are listed.
  Red first: `check_plan.py` FAILed ("out/plan.json does not exist"). Two runs on the Hamar fixture
  both PASS with the same facts (friluftsliv, 2026-12-01, max `unknown`), costing about 0.15 and 0.08 USD.

## 2026-10-29: Implement task 007 (run chain)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan implement tasks/007-run-chain`
- **Outcome:** `harness/run.py` runs the six stages from a list, with a check after each. It clears `out/`
  first, and a rejection (exit 3) is confirmed with `check_rejection.py` before any model call.
  Stages 4 and 5 retry up to 3 times, with `Previous check output (fix this): <stderr>` appended.
  `claude` is looked up only when stage 4 starts, so `check_run.py` stays model-free for CI.
  `check_run.py` PASS. The full offline run exits 0 (0.14 + 0.15 USD, both first attempt). The retry path was
  tested with a stubbed model call: FAIL, FAIL, PASS goes on; 3 FAILs exit 1.

## 2026-10-29: Implement task 008 (CI)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan implement tasks/008-ci`
- **Outcome:** `.github/workflows/checks.yml` runs stages 1 and 3 offline plus `check_entity`, `check_grants`,
  `check_filter` and `check_run` on every PR, with no model and no secrets. PR #4 went green; changing
  `region_prefix` to `340` in one grant file turned it red at `check_grants` ("region_prefix must be 2 or 4
  digits"); the revert turned it green again. Screenshots of both are in the report.

## 2026-11-10: Implement task 010 (sources and catalog)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan implement tasks/010`; survey of Hamar + 5 neighbours done by fetching robots.txt and one
  grant overview page each
- **Outcome:** `docs/source-survey.md`: municipalities add their own driftstilskudd/kulturmidler, so W45 stands
  (county auto, municipalities manual, named as a limitation). `harness/catalog.py` saved 4 index pages, 58
  listings → `context/catalog.json`. SJ marked 23016, 36453, 2658 ingested; 55 pending (decide by 2026-11-24).
  `check_catalog` red → PASS. `check_sources` was already PASS (sources.json committed in 89af398), so not red first.

## 2026-11-10: Implement task 012 (stress test A, prompt injection)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan implement tasks/012`; Simen wrote the five stress `expected.json` files, added the poisoned
  corpus grant and `invalid_request` to `PRE_MODEL_REASONS`, and raised the 24 h cap test to 5.10 USD
- **Outcome:** Before repair 3/5 stress cases passed (01, 02 absorbed by scrub, filter and the matcher; 03a by
  MOD11); 03b and 03c reached the model and failed. Repairs: `validate_request()` in stage 1, `<grant_text>` /
  `<project_idea>` tags in stages 3 and 5 with updated `match.md` and `guide.md`, quote guard in
  `guide_input.py`; 24 h cap 3 → 5 USD. Full eval 17/17, 2.33 USD. Write-up: `docs/stress/012-stress-injection.md`.

## 2026-11-11: Implement task 014 (LLM-as-judge)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan implement tasks/014`; Simen wrote the judge prompt `eval/prompts/judge.md` (sha256
  `7b057e22…`) and copied Claude's drafted `eval/judge.py` into `eval/` (the `Edit(/eval/**)` deny rule stays)
- **Outcome:** `judge.py` was tested free with a stub `claude` (bad score, missing key, no JSON, HALTED, 24 h cap
  → exit 1, the last two with no call). Real run on the Hamar plan: 4/4/4/4, 0.05 USD (plan run 0.15 USD).
  The judge only advises and is not wired into `run.py` or `run_eval.py`. Calibration (blind human scorer,
  5 plans in `docs/judge-calibration/`) and the length-bias probe are deferred until after the 12 Nov demo.
  Write-up: `docs/llm-judge.md`.

## 2026-11-12: Found in demo prep: live audience org numbers failed at stage 1
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** The audience run from the runbook (`demo/audience.json`, 999220606 Strikkekafeensvenner, never seen
  before) failed at step 1; then `/plan` "you can live enter a brreg number and it works, without an extra step"
- **Found (missed until now):** the live Brreg lookup worked, but `eval/check_entity.py` compares `out/entity.json`
  with `fixtures/brreg_<orgnr>.json`. Every earlier test, eval case and backup org number had a saved fixture, so
  no run had ever checked a club we had not seen. The runbook's "find the org number on brreg.no" step could
  not work for a new club.
- **Outcome:** `harness/entity.py`: a live lookup of an unknown orgnr saves an allowlisted copy of the response
  (only the fields stage 1 and the check read, address cut to kommune + kommunenummer, no contact data or free
  text) as the fixture; never overwrites, nothing saved under `FAULT` or on a bad response. `eval/` unchanged.
  Verified free: new orgnr → saved + `check_entity` PASS, rerun leaves the file unchanged, `check_fixtures` PASS
  (10 clean), `FAULT=brreg_500` → exit 1 with no file, `check_run` and pytest 5/5 green. Limitation: for a new
  club the reference comes from the same live call, so the check verifies field mapping, Innlandet and privacy,
  not Brreg itself. Runbook §2 updated; the full audience run is left to Simen.

## 2026-11-24: Dropped page sections, wrong maximum amount, catalog triage
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan` "do the triage, and get control over which info has to be input or can be gathered from the
  grant pages; the max amount should be linked to some headers being ignored when getting the grants"
- **Found (missed until now):** `harness/update_grants.py` kept only `<h2>` sections in `HEADING_MAP` and dropped
  every other heading without a trace. On the live pages that lost "Tildelingsprosess" (arrangementsutvikling:
  "Maksimal søknadssum er 350 000 kroner", file said `unknown`), "Kriterier", and "Avgrensning", "Støttenivå",
  "Søknadsvurdering" (kunstnerisk aktivitet, folkehelse: the exclusions and the share of costs). The
  arrangementsutvikling heading "Hvem kan søke?" also ends in a zero-width space, so even that core heading did not
  match (the next real update would have failed with a template reason). **Honest failure:** the human gate
  existed, but on 11.11 the review compared the facts against the draft, not against the source page, so a fact
  that the extractor never saw could not be caught.
- **Outcome:** `update_grants.py`: invisible characters stripped; extra fact headings merged under
  `### <page heading>` (EXTRA_MAP); known background headings listed as deliberately left out (IGNORED); unknown
  headings still go to review. New read-only `--audit` writes `out/grant_audit.md`: every page heading, the page's
  amount and deadline dates against the frontmatter, the human-only fields, and the field-provenance table; a
  needs_review draft gets `<id>.checklist.md`. Facts stay human-written: Claude prepared `out/grant_fix/*.md`
  (`max_amount_nok: 350000` plus the re-extracted bodies), **Simen checked them against the live pages** and
  copied them into `context/grants/` himself. Audit after the copy: no mismatch. `check_update` (8 cases),
  `check_grants` PASS.
- **Triage (no model):** new `harness/triage.py` writes a title-based proposal per pending catalog entry;
  `--apply` records only rows a human signed. Simen and Elias reviewed the 54 proposals; Simen signed them (SJ):
  34 `applicant_not_voluntary`, 20 `deferred_verification`, 0 pending. Signed sheet: `docs/triage-2026-11-24.tsv`.
- **Departure from plan (eval edit by a human):** `deferred_verification` = possibly relevant for a club, not
  verified before the exam (our time limit, not a judgment about the grant). Simen added it to `REASONS` in
  `eval/check_catalog.py`; his first version counted `count["deferred_verification"]`, a reason and not a status,
  so the check crashed with `KeyError` (found by Claude by running it). Simen then applied the suggested fix:
  deferred entries count as *relevant* and are printed on their own. Coverage now:
  `58 listed | 4 ingested | 34 not relevant | 20 deferred | 0 pending | ingested/relevant = 4/24`.

## 2026-11-26: Corpus refresh C4 (eval edit by humans), case 13, `must_reject` for arrangementsutvikling
- **Who:** Simen + Claude Code. Humans ran every step that writes to `eval/`; Claude only compared files and
  read diff stats (never `expected.json` contents).
- **Prompt:** `/plan` "redo the diff" (step 2 of `docs/corpus-refresh/README.md`), then the README steps by hand.
- **Departure from plan:** planned for Wed 25.11, done Thu 26.11 morning. The live `update_grants.py` (4 unchanged,
  Hamar manual) and `catalog.py` (58 listed, 0 new, 0 removed) runs and `triage.py` (0 pending) are from 26.11,
  so `checked_at` and `index_checked_at` hold for `EVAL_TODAY=2026-12-03`.
- **Diff (Claude, read-only):** since bd0c3e1 only `checked_at` changed in `context/grants/`. Against the old corpus:
  arrangementsutvikling is new (FLI, Frivillighetsregisteret, region 34, max 350 000, deadline 2027-04-01, NIF/DFS/NBF
  members only, sports events only); H, F and K gained the Støttenivå, Søknadsvurdering and Avgrensning sections (K
  also Krav til søknaden; its one-municipality rule moved from Formål to Støttenivå and Avgrensning); D `checked_at`
  only. No amount, deadline, org-form or region field changed for D, H, F or K, so no filter result changes.
  Left as is: K repeats one Formål sentence (lines 20 and 28); no effect on any match, not yet checked against the live page.
- **Outcome (human eval edit):** `cp context/grants/*.md eval/corpus/grants/`; `add_must_reject.py` added
  `arrangementsutvikling_innen_idrett` to `must_reject` in 11 cases (01–07, 11, 12, stress_01, stress_02; `--check`
  first). Not added: 08 (filter), 09, 10, stress_03a/b/c, stress_dep_01–06 (stop before the matcher). New case 13
  (Gjøvik Skiklubb, regional youth roller-ski sprint, September 2027 → `must_match` A, 01.04.2027 round), written
  by Simen. `CASES.md`: grant id A, the A sentence, row 04 wording, row 13.
- **Re-check:** every `expected.json` re-checked by Simen and Elias against the new texts 
- **Free checks:** `run.py --offline --dry-run` wiring OK; `check_grants`, `check_fixtures` (13 clean), `check_sources`,
  `check_update` (8 cases), `check_budget`, `check_killswitch`, `check_catalog` all PASS
  (`58 listed | 4 ingested | 34 not relevant | 20 deferred | 0 pending`). Stage checks follow in Run B.
- **B3 (optional):**: either verify 1–2 deferred grants (Spillemidler, ULF) before Run B, or skip it;
  if skipped, all 20 stay `deferred_verification` and the white paper says so.

## 2026-11-26: Task 017, two more county grants (N, R) before Run B (eval edit by humans), case 14
- **Who:** Simen + Elias + Claude Code. Humans wrote every frontmatter fact (four eyes: `verified_by: SJ, EB`),
  every decision, and every copy and edit in `context/` and `eval/`. Claude read live pages, built the tools, wrote the drafts
  and proposals under `docs/grant-expansion/`, and ran the free checks and the screening. Settings blocked every Claude write to
  `eval/`, so Simen ran each step that writes there.
- **Prompt:** `/plan implement tasks/017 from step 0`, then the steps in order.
- **Step 0 (live pages, 26.11):** N = 37168 (large national and international sports events) and R = 62589 (Regionalt
  kulturfond) kept. **U = 58403 ULF swapped out:** only youth councils, pupil councils and schools may apply. Both
  backups failed: 62588 has been merged into R from 2026 (the page is a stub); 22177 is operating support for
  county-level organisations, and its 1 Feb 2026 deadline has passed. A third grant was not taken (Simen): 66424
  trafikksikkerhet has no Formål heading, so the weekly update would hit a template failure every week (kill switch).
  **Not added, stay `deferred_verification`:** 58403, 62588, 22177. Coverage `ingested/relevant` 4/24 → **6/24**.
- **Harness change (approved by Simen):** additive heading map in `harness/update_grants.py`. `Formålet med ordningen`
  → Formål (without it N was a template failure); `Tildelingskriterier`, `Avgrensing`, `Vi gir ikke tilskudd til`,
  `Vurdering av søknaden`, `Søknadskategorier`, `Tidligere ordninger fases inn …` merged under Hva kan det søkes om;
  administrative headings ignored. A live `--audit` showed none of the five ingested pages uses them (bodies unchanged).
- **Tools (Claude, stdlib, tests in `tests/`):** `tools/draft_grant.py` (imports the parsing from
  `update_grants.py`; refuses output into `context/`/`eval/`; facts left `TODO`; the checklist lists every amount and
  date with its sentence), `tools/screen_cases.py` (stages 1 and 3 as subprocesses on a temp corpus; `out/` snapshotted
  and restored byte-identical; never prints `must_match`/`must_reject`), `tools/add_expectation.py` (replaces
  `add_must_reject.py`: inserts into the existing array text, then checks that the parsed file equals the old JSON plus
  exactly the new ids). pytest 5 → 21 passed.
- **Facts (step 2, humans):** N: FLI, KOMM, ENK, AS, STI; no Frivillighetsregisteret; 34; alle; max 1 000 000;
  2027-02-01, 2027-09-01 (the page gives no year). R: FLI, ENK, AS, STI (Claude flagged `KOMM`: "kan være del av
  tiltaket, men ikke være søker"; humans removed it); max 300 000; 2027-01-15.
  Claude flagged, humans kept: `ENK` for N, although "overskudd ikke kan bli utbetalt som utbytte til private eiere".
- **Rules only the matcher can apply (review sheet `docs/grant-expansion/README.md`):** N date gap: 1 Feb → events the
  following summer and autumn, 1 Sep → winter and spring, the event ≥3 months after the deadline; N sends regional events
  and national ones with fewer than 500 participants to A. R excludes "hovedsakelig idrett eller friluftsliv", has a
  minimum of 20 000 and no project period. Neither grant has an affiliation rule.
- **Decisions (step 5):** 26 rows proposed by Claude with a one-line why; Simen approved all of them and asked Claude to
  write `SJ` into `decision`/`decided_by`. N `must_reject` in all 13 cases that reach the matcher (13 is the near-miss);
  R `must_match` in 02, 04, 07 (arts; 04 is the K/R overlap test: K rejects one municipality, R allows it) and
  `must_reject` in the other 10.
- **Eval edit (humans, steps 3, 6, 7):** both grants copied to `context/grants/` and `eval/corpus/grants/` (identical);
  catalog 37168 and 62589 `ingested` with `grant_id` (first attempt lacked `grant_id`, so `check_catalog` FAILED; fixed).
  `add_expectation.py` added 24 ids (`--check` first; +3/−1 per file, +4/−2 in 02 and 07); case 04 was refused
  (no `must_match` array to insert into), so Simen added its 2 ids by hand, and a re-run with `--check` gives 0 to add. New case
  **14** (Raufoss IL 976728211, international youth tournament, Aug 2027 → N `must_match`; A and S left out), proposed by
  Claude, confirmed by Simen; Brreg fixture saved through `harness/entity.py` (allowlisted fields, no roles endpoint).
  `CASES.md`: N and R ids and sentence, notes on rows 02, 04, 07, 13, new row 14.
- **Step 8:** dry run OK; `check_grants`, `check_fixtures` (14 clean), `check_sources`, `check_update`,
  `check_budget`, `check_killswitch`, `check_catalog` (`6 ingested | 18 deferred | 6/24`) all PASS; pytest 21 passed;
  `screen_cases.py` on the corpus: 225 (case, grant) pairs, 0 decided `must_reject` rows wrong.
- **Known, not fixed:** `update_grants.py --audit` reports `MISMATCH: page 350000, file 1000000` for N. The audit's amount regex
  misses "1 million kroner" and matches only when there is a single maximum; N's page has two (1 000 000 overall,
  350 000/yr for a recurring event). The human-checked 1 000 000 stands. R: "not on page (check by hand)", because the
  regex misses "fra 20 000 til 300 000"; checked by hand.
- **Effect on Run B:** 25 cases, 9 grants in the corpus. 06 and 11 used to stop at the filter ("0 or 3"); with N and R
  (2027 deadlines) they now reach the matcher, so they run 3 times. Re-estimate the cost before running.
- **Claude slips:** one command opened an `expected.json` (blocked by the permission check, nothing read); a direct
  read of the synthetic corpus grant was also blocked, so S in case 14 was decided by Simen.
- **Future work noted:** joint applications (ROADMAP "Future work"); R lets municipalities take part without applying,
  and N requires binding agreements when one applies on behalf of several.

## 2026-11-26: Reproducible after submission: one reference date 2026-11-27, no automatic commits
- **Who:** Simen + Claude Code (plan mode, plan approved by Simen)
- **Prompt:** "check the usage, so we know whether run B can be done now, and also check if it will work"; then
  `/plan` "ensure everything is either set to december 3rd 2026 or in general works when setting it to december 3rd
  ... shown in the README", and "no automatic update happens in the repo now so the push with exam tag is the absolute
  last commit".
- **Found (free):** 24 h spend 0.00 USD, but Run B would have failed. `run_eval.py` `DEFAULT_TODAY` was 2026-11-05, and
  the C4 corpus has `checked_at` 2026-11-26, so `check_grants` failed at stage 2 in every case (probe: case 08, exit 1,
  0.00 USD, log `docs/eval-logs/eval_2026-11-26_150035.log`). 03.12 can't be the eval date: friluftsliv's only
  deadline is 2026-12-01. `update-grants.yml` committed to `main` on 23.11 (`023dc04`), and its next run would have
  been Mon 30.11.
- **Decision (Simen):** eval pinned to **2026-11-27**. Everything else reproduces with `EVAL_TODAY=2026-12-03`.
- **Proof that no answer changes:** `tools/screen_cases.py --today` (new flag) at 11-05 and 11-27 gave identical
  output for all 225 (case, grant) pairs. At 12-03 the only difference is friluftsliv `no_open_deadline` in 14 cases.
- **Claude changed:** `tools/screen_cases.py` (`--today`, `DEFAULT_TODAY` mirror 2026-11-27);
  `checks.yml` (job `EVAL_TODAY=2026-12-03`, filter step `--today 2026-12-03`); `update-grants.yml` (schedule
  removed); README section for the evaluator; ROADMAP reproduction and freeze step 5. Every CI check, plus
  `check_sources`, `check_catalog` and `check_fixtures`, PASSes with `EVAL_TODAY=2026-12-03` (0.00 USD).
- **Human steps (eval/ and GitHub are not Claude's), done 26.11 by Simen:** `gh workflow disable update-grants`
  (`disabled_manually`; Claude's attempt was blocked by the permission check). `eval/run_eval.py` `DEFAULT_TODAY` and
  docstring, plus the `eval/common.py` comment, changed to 2026-11-27. Every `"today": "2026-11-05"` in
  `eval/cases/*/expected.json` changed to 2026-11-27 (24 cases; case 06 keeps its own 2026-12-02, unchanged).
  Afterwards the corpus `check_grants` PASSes at 11-27 and at 12-02, and `run_eval.py --case 09 --case 10` gives
  2/2 at 0.00 USD.
- **Second decision (Simen): 2026-11-27 everywhere, not 2026-12-03.** On 03.12 the filter keeps 5 grants and drops
  friluftsliv (`no_open_deadline`). Simen read `fixtures/expected_matches.json`: `must_match_any` has
  `tilskudd_til_friluftslivsaktivitet`. So on 03.12 `check_matches` would fail at stage 4, after the model calls.
  Options were 11-27 everywhere, a fixture edit, or documenting the failure. Simen chose 11-27. README, `checks.yml`
  (`EVAL_TODAY` and the filter step `--today 2026-11-27`) and ROADMAP now say 11-27. At 11-27, `check_grants`,
  `check_sources`, `check_catalog` and `check_fixtures` PASS. The earlier 12-03 numbers above are superseded.
