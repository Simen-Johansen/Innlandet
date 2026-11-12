# Roadmap: Volunteer Grant Navigator (Tilskudds-los for frivilligheten)

Today is W46. Compulsory 2 (tasks 001–008, the walking skeleton) is done; the demo ran 12.11.
What remains is evidence, correct facts and the white paper: see Run-in below.

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
| W47 (16–22.11) | Evidence and correct facts; feature freeze Sun 22.11 (see Run-in) | 013, 014 | – |
| W48 (23–29.11) | Final eval, fixes and writing only (see Run-in) | 013 | – |
| Thu 03.12 11:59 | White paper on Wiseflow | – | `exam` (never moved) |

## Run-in to the exam (12.11 → 03.12)

35/100 points are evaluation and stress testing, 10 are honest reporting and human-in-the-loop control.
So: **evidence and correct facts, not features. No new features after Sun 22.11.**

### Hard dates (everything else may slide within its week)
| When | What | Why it is hard |
|---|---|---|
| by Wed 18.11 | `python harness/catalog.py` live once | stale `index_checked_at` (> 8 days) fails `check_catalog` |
| Sun 22.11 | Feature freeze; last day a new grant may enter | must be in the corpus before the final eval |
| by Tue 24.11 | 0 pending in `context/catalog.json` | 14-day pending limit in `eval/check_catalog.py` |
| Tue 24.11 → Fri 27.11 | Final 3-run eval, on a day of its own (5 USD / 24 h cap) | appendix and task 013 |
| Wed 02.12 | Freeze steps below, `git tag exam`, push (only on explicit go-ahead) | tag never moves |
| Thu 03.12 11:59 | Wiseflow (aim for Wed evening) | deadline |

### Workstreams
**A. Fix the facts (Must, now)**
1. Check the live page, set `max_amount_nok: 350000`; restore the arts grant's exclusion sentence in `context/grants/`.
2. Log both in `docs/prompt-log.md` as corrected agent output; write up as honest failures: the human gate existed,
   but the review compared against the draft, not the source page.
3. Re-check the other county files against their live pages for dropped sections.
4. *(Should, before 22.11)* `update_grants.py` lists unknown page headings (e.g. "Tildelingsprosess") at the top of
   each draft, plus a one-page reviewer fact checklist.

**B. Catalog: 54 pending (Must, before 24.11)**
1. Triage without a model, 27 each: can a volunteer club apply? If not → `not_relevant`, reason code, initials in `decided_by`.
2. **Scope, stated plainly:** we do not have time to verify every relevant county grant before the exam. A relevant
   grant we leave out gets `deferred_verification`, so the catalog shows exactly which grants a person still has to
   verify. That is a limit of our time, not a judgment about the grant. This needs an `eval/` edit made by a human
   (or explicitly delegated), logged in `docs/prompt-log.md` and named in the white paper as a departure from plan:
   add the code to `REASONS`, and count deferred entries as *relevant* in the coverage line. Otherwise
   `ingested/relevant` looks complete when it is not.
3. Verify at most 3–4 high-value grants with four eyes, against the **live page**: every frontmatter fact, the
   project period each deadline covers, every heading mapped or listed as dropped, domain `auto` in `context/sources.json`.
4. Before it counts: copy to `eval/corpus/grants/`, ≥1 match case (+1 no-match if possible), re-check every
   `expected.json`, watch cost per run.

**C. Evidence (Must; judge = Should)**
1. Mon 16.11: 3-run baseline eval on the current corpus (013 Run A).
2. Judge calibration (014): plan_5, blind human scores, judge plans 2–5, length probe, tables (~0.35 USD).
3. Date-gap known failure: one run for a June 2027 event (~0.15 USD); keep the plan as evidence.
4. W48 Mon: refresh `eval/corpus/grants/` from verified files; re-check every `expected.json`.
5. Final 3-run eval (013 Run B); update `tasks/013-stress-dependency.md`; save the raw log.

**D. Writing (Must)**
1. Meeting reports (demo, W47, W48 and earlier ones from notes): at least 8 in the submission, in or outside the repo.
2. White paper 7–8 pages: revised C2 sections + evaluation, safe operation, stress testing, reflection; every
   departure from plan stated. Appendices: prompt logs, one raw eval log, meeting reports.
3. 30.11–01.12: every number traced to a log, page count, appendices present.

**E. Freeze (Wed 02.12):** the exam freeze steps below.

**Reproducible after submission (must hold at the tag)**
- `python eval/run_eval.py` pins `EVAL_TODAY` per case and reads only `eval/corpus/grants/`, so its results do not
  depend on the date they are run. The corpus is frozen at the final eval and not touched again.
- Everything else is reproduced with `EVAL_TODAY=2026-12-03` (README). On that date, `check_grants` needs every
  `checked_at` ≥ 03.11, and `check_catalog` needs `index_checked_at` ≥ 25.11 and no pending entry added before 19.11.
  So the last live `catalog.py` and `update_grants.py` runs happen in freeze step 3, and no entry is left pending.
- Freeze check: on a fresh clone of the tagged commit, with `EVAL_TODAY=2026-12-03`, every check PASSes and
  `python harness/run.py --offline` exits 0. CI (`checks.yml`) does not set `EVAL_TODAY`. That is harmless,
  because it runs only on PRs and on manual dispatch, but say so in the README if someone re-runs it on `exam`.

### Week by week (owners are suggestions)
- **12.11–15.11:** demo report (both) · A1–A2 (Simen) · A3 (Elias) · start B1 (both)
- **W47:** C1 Mon · catalog live by Wed · finish B1–B2 · C2 (Elias scores, Simen runs) · A4 · B3–B4 · C3 ·
  W47 report · **Sun 22.11 feature freeze**
- **W48:** C4 Mon (low spend) · 0 pending by Tue · C5 on its own day · white paper draft (Elias leads, Simen
  numbers) · freeze steps 1–3 · W48 report
- **30.11–03.12:** D3 (both) · E Wed (Simen) · submit Wed evening (Elias)

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
3. Run `python harness/update_grants.py` and `python harness/catalog.py` live once more (on or after 25.11), so every
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
