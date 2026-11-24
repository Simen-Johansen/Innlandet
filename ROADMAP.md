# Roadmap: Volunteer Grant Navigator (Tilskudds-los for frivilligheten)

Updated Tue 24.11 (W48). Compulsory 2 (tasks 001–008) is done; the demo ran 12.11; facts fixed and catalog
triaged 24.11. What remains is evidence (judge, Run A, Run B), the corpus refresh and the white paper: see Run-in.

## The chain (architecture figure for the report)

```
input_request.json
  │
  ▼  [1] entity     harness/entity.py      → out/entity.json        check: eval/check_entity.py
  ▼  [2] grants     context/grants/*.md    (curated, sanitized)      check: eval/check_grants.py
  ▼  [3] filter     harness/filter.py      → out/eligible.json      check: eval/check_filter.py
  │                                         + out/match_input.md (context filter for stage 4)
  ▼  [4] match      claude -p (prompts/match.md)  → out/matches.json   check: eval/check_matches.py   (max 3 tries)
  ▼  [5] guide      claude -p (prompts/guide.md)  → out/plan.json      check: eval/check_plan.py      (max 3 tries)
  ▼  [6] render     harness/render.py      → out/grant_action_plan.md  (code, not LLM)
```

Code decides the order. The model only does stages 4 and 5, which are the two steps that need judgment.
Every arrow is a file and a check.

## Milestones (working backwards from the deadlines)

| Date | Milestone | Tasks | Tag |
|---|---|---|---|
| Thu 29.10 | Stages 1–3 run offline, checks green | 001, 002, 003 | – |
| Fri 30.10 | **C2:** full chain runs from one command, offline, with CI | 004–008 | `c2-skeleton` |
| W45 (2–8.11) | Test set and evaluation harness, live grant fetcher | 009, 010 | `w45-eval` |
| W46 (9–15.11) | Safe operation and first stress test, then live demo | 011, 012 | `demo` |
| W47 (16–22.11) | Evidence and correct facts; slipped to 24.11 (see Run-in) | 013, 014 | – |
| W48 (23–29.11) | Facts + triage + judge + Run A 24.11, corpus 25.11, Run B 26.11, writing | 013, 014 | – |
| Thu 03.12 11:59 | White paper on Wiseflow | – | `exam` (never moved) |

## Run-in to the exam (updated Tue 24.11)

35/100 points are evaluation and stress testing, 10 are honest reporting and human-in-the-loop control.
We slipped about 12 days after the demo (nothing was committed 12.11–23.11). The plan stays the same: we cut slack,
not scope. Everything below is still planned; dates that moved are said plainly.
**Spend:** 5 USD per rolling 24 h (kill switch). A 3-run eval is about 2.9 USD, so Run A and Run B need two
different 24 h windows. Pre-flight before any paid run: `out/HALTED` absent, 24 h cost below 2 USD.

### Done (status 24.11)
- [x] A1 350 000 kr and the dropped sections (Avgrensning, Støttenivå, Kriterier, Tildelingsprosess…) restored,
      checked by Simen against the live pages; logged in `docs/prompt-log.md` as an honest failure
- [x] A2 root cause: `update_grants.py` dropped unknown headings; zero-width space in "Hvem kan søke?"
- [x] A3 county files re-checked: `python harness/update_grants.py --audit`, no mismatch left
- [x] A4 drafts get `<id>.checklist.md`; `--audit` writes `out/grant_audit.md` with field provenance
- [x] B1–B2 triage: 54 → 34 `applicant_not_voluntary`, 20 `deferred_verification`, 0 pending (eval edit by Simen,
      logged); signed sheet `docs/triage-2026-11-24.tsv`
- [x] C2 judge calibration: Elias scored plans 1–5 blind; judge plans 2–5 and length probe run 24.11
      (within ±1 on 19/20, exact 13/20; padded plan scored lower, no length bias seen)
- [x] C1 Run A 24.11: 23/23 PASS, every model case 3/3, 2.49 USD (`docs/eval-logs/eval_2026-11-24_110707.log`)
- [x] C3 date gap 24.11: June 2027 event told deadline 01.04.2027 (covers Jul–Dec); the right round closed
      01.11.2026 (`docs/stress/date-gap/`)
- [x] D1 (draft) 8 meeting-report drafts from git history in `docs/meetings/`; Simen and Elias must correct them

### Hard dates
| When | What | Why it is hard |
|---|---|---|
| Tue 24.11 | Run A (3-run eval) starts | Run B needs a separate 24 h window before 03.12 |
| Wed 25.11 | live `update_grants.py` + `catalog.py` | index is stale now; a run on/after 25.11 also holds for `EVAL_TODAY=2026-12-03` |
| Wed 25.11 evening | corpus refreshed, every `expected.json` re-checked | Run B only means something on the refreshed corpus |
| Thu 26.11 | Run B (final 3-run eval), once Run A has left the 24 h window | the raw log for the appendix |
| Sun 29.11 | white-paper full draft | two days left for numbers and appendices |
| Wed 02.12 | freeze steps, `git tag exam`, push (only on explicit go-ahead) | tag never moves |
| Thu 03.12 11:59 | Wiseflow (aim for Wed evening) | deadline |

### Tue 24.11 (today)
1. **C2 judge, task 014** (Claude runs, ~0.31 USD):
   - judge plans 2–5: `python eval/judge.py docs/judge-calibration/plan_N.md --out docs/judge-calibration/judge_plan_N.json`
   - length-bias probe: plan_1 vs a copy padded with polite filler (`docs/judge-calibration/plan_1_padded.md`), judge both
   - fill the Judge column and the agreement table (exact, within ±1, mean abs. diff) in `docs/llm-judge.md`;
     write the probe result under "Known failure modes"; tick `tasks/014-llm-judge.md`
2. **C1 Run A, task 013** (~2.9 USD): `python eval/run_eval.py` (3 runs per case) on the current corpus; report each
   case k/3, total and cost; log kept in `docs/eval-logs/`; fix surprises tomorrow, before Run B.
3. **C3 date-gap known failure** (~0.15 USD): one run with a June 2027 event, keep the plan as evidence
   (`docs/stress/date-gap/`), one line in the white paper's known failures.
4. **D1 meeting reports**: `docs/meetings/` is empty; at least 8 are required. Write them from notes and git history
   (W40–W48 + demo 12.11), one file per meeting: date, present, decided, next. Claude drafts from the git log;
   Simen and Elias correct them.
5. **Hamar hand-check** (freeze step 2, manual domain): every fact against the page, set `checked_at`.

### Wed 25.11
1. `python harness/update_grants.py` and `python harness/catalog.py` live; decide every new catalog entry by hand
   (`harness/triage.py`); `check_grants` and `check_catalog` PASS.
2. **B3 (Should, moved from 22.11):** verify up to 3 of the 20 deferred grants that clubs are most likely to use
   (proposal: Spillemidler, ULF – Ungdommens livskvalitetsfond, Regionalt kulturfond). Per grant: `--audit` on the
   live page, all frontmatter by hand with four eyes, the project period each deadline covers, catalog status
   `ingested`. Cut-off: the corpus refresh in step 3; whatever is not done stays `deferred_verification`.
3. **C4 corpus refresh (human act, eval edit):** copy `context/grants/*.md` to `eval/corpus/grants/`
   (arrangementsutvikling and any B3 grant are new there); ≥1 match case per new grant (+1 no-match if possible);
   Simen and Elias re-check every `eval/cases/*/expected.json` against the new texts (amounts and Avgrensning can
   change matches). Log the edit in `docs/prompt-log.md`. Free check: `python harness/run.py --offline --dry-run`.
4. Fix anything Run A showed.

### Thu 26.11
1. **C5 Run B, task 013** (~2.9 USD, final): pre-flight, `python eval/run_eval.py`; save the raw log for the appendix;
   update `docs/stress/013-stress-dependency.md` (1-run 23/23, 3-run A and B, ~2.9 USD) and tick task 013.
2. The corpus is frozen after this run: `eval/corpus/grants/` is not touched again.
3. White paper: evaluation chapter from the Run A/B logs and the judge table.

### Fri 27.11 – Sun 29.11
- **D2 white paper** 7–8 pages: revised C2 sections, evaluation (Run A, Run B, judge calibration), safe operation,
  stress tests (012, 013, date gap), reflection. Every departure stated: the 12-day slip, Run A on the old corpus,
  the `deferred_verification` eval edit, B3 after the feature freeze, the 11.11 review against the draft.
  Appendices: prompt log, Run B raw log, meeting reports, the field-provenance table from `out/grant_audit.md`.
- W48 meeting report.

### Mon 30.11 – Tue 01.12
- **D3** every number traced to a log, page count, appendices present; README steps followed from a fresh clone.

### Wed 02.12 – Thu 03.12
- **E** exam freeze steps below (step 3 already done on 25.11 unless something changed), tag only on explicit
  go-ahead, submit Wed evening (Elias).

**Reproducible after submission (must hold at the tag)**
- `python eval/run_eval.py` pins `EVAL_TODAY` per case and reads only `eval/corpus/grants/`, so its results do not
  depend on the date they are run. The corpus is frozen at the final eval and not touched again.
- Everything else is reproduced with `EVAL_TODAY=2026-12-03` (README). On that date, `check_grants` needs every
  `checked_at` ≥ 03.11, and `check_catalog` needs `index_checked_at` ≥ 25.11 and no pending entry added before 19.11.
  So the last live `catalog.py` and `update_grants.py` runs happen on or after 25.11, and no entry is left pending.
- Freeze check: on a fresh clone of the tagged commit, with `EVAL_TODAY=2026-12-03`, every check PASSes and
  `python harness/run.py --offline` exits 0. CI (`checks.yml`) does not set `EVAL_TODAY`. That is harmless,
  because it runs only on PRs and on manual dispatch, but say so in the README if someone re-runs it on `exam`.

### Future work (white paper, not built)
- Project date in the request: `project_start`, each deadline stores the project period it covers, "next round not
  announced yet" instead of a computed date. Evidence: C3.
- `run.py` finding `<request>.expected.json` itself: would rewire eval/ checks before the exam, so not now
  (`run_eval.py` already sets `EXPECTED_MATCHES` empty per case).
- Simple web page, remaining county grants, scheduled `catalog.py`, task 016 `draft_grant.py`.

### Exam freeze (W48, before Thu 03.12 11:59), in this order
Section 3.6: the submitted commit is tagged `exam` and the tag never changes after the deadline.
1. Review the drafts in `context/grants_pending/`; copy accepted text into `context/grants/` (humans only).
2. Re-check `hamar_driftstilskudd_frivillige_organisasjoner` by hand (manual domain) and set `checked_at`.
3. Run `python harness/update_grants.py` and `python harness/catalog.py` live once more (on or after 25.11; planned Wed 25.11), so every
   `checked_at` and `index_checked_at` is valid for `EVAL_TODAY=2026-12-03`; decide any new catalog entry by hand.
4. All checks PASS, `python harness/run.py --offline` exits 0, README steps followed once from a fresh clone,
   also with `EVAL_TODAY=2026-12-03` set.
5. `git tag exam` on that commit and push the tag. Never move or delete it. The weekly
   `update-grants.yml` stops by itself once the tag exists; also run `gh workflow disable update-grants`.

If you are behind on Fri 30.10, cut depth, not stages. For example, use 2 grant files instead of 4, or skip the retry loop.

## Every task, the same loop (W40)

1. **Author** commits the check first (red), then writes `tasks/NNN-*.md`
2. **Driver** runs `/plan Implement tasks/NNN-*.md`, reviews the plan, and approves
3. The check decides. On failure, fix the spec or the plan, never the check
4. **Author** reviews the diff and merges. Add one line to `docs/prompt-log.md` whenever agent output was corrected
5. `/clear` before the next task

Swap Author and Driver roles every task. Write one meeting report per week in `docs/meetings/`. The exam requires at least 8.
