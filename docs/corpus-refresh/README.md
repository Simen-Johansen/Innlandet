# Corpus refresh C4: checklist for Wed 25.11

Prepared by Claude on 24.11. Humans run every step. Claude cannot edit `eval/` and never reads `expected.json`.
Run B is **Thu 26.11 after about 13:00 UTC**, not on 25.11 (rolling 24 h spend window).

## Decisions (made 24.11)
- The new grant `arrangementsutvikling_innen_idrett` needs a **sports event** and an applicant affiliated with
  **NIF, DFS or NBF**. None of the existing cases is an event, so it goes into `must_reject` in the 11 cases that
  reach the matcher: 01, 02, 03, 04, 05, 06, 07, 11, 12, stress_01, stress_02 (`add_must_reject.py` does this).
- Not added: 08 (filter removes it: not in Frivillighetsregisteret), and 09, 10, stress_03a/b/c and stress_dep_01–06
  (they stop before the matcher; adding it there would make them fail).
- New case **13**: Gjøvik Skiklubb (fixture 983758622), regional youth roller-ski sprint in **September 2027**
  (the 01.04.2027 round covers Jul–Dec 2027), so the expectation is `must_match`. Already copied into `eval/cases/` by Simen on 24.11 (Claude's proposal stays in `cases/` for reference).
- No case 14. HHT is **not** affiliated (DNT member, under Norsk Friluftsliv, checked by Simen 24.11), and the 24.11
  date-gap run already matched it. Recorded as a known failure in `docs/stress/date-gap/README.md`.
- The corpus copy and the `must_reject` edit happen **together**. A `must_reject` for a grant missing from the
  corpus fails, so the script refuses to run before the copy.

## Steps (bash, via `!`, in this order)
```bash
# 1. Live grant update and catalog
python harness/update_grants.py
python harness/catalog.py
python harness/triage.py            # decide any new catalog entry by hand; 0 pending afterwards
```
**2. Tell Claude "redo the diff".** Claude compares `context/grants/` with `eval/corpus/grants/` again and tells
you if an amount, deadline or rule changed in a way that breaks the decisions above. Wait for an OK.
```bash
# 3. Corpus refresh + case edits in ONE step (the human eval edit)
cp context/grants/*.md eval/corpus/grants/
python docs/corpus-refresh/add_must_reject.py --check     # shows the 11 cases, writes nothing
python docs/corpus-refresh/add_must_reject.py
git diff --stat eval/               # expect: corpus .md files, 11 expected.json (+ case 13 and CASES.md if not committed yet)
git diff eval/cases                 # each expected.json gains one line; formatting may also be normalised

# 4. Free checks (no model calls)
python harness/run.py --offline --dry-run
for c in grants fixtures sources update budget killswitch catalog; do python eval/check_$c.py; done
```
The stage checks (entity, filter, matches, plan, render, rejection) need a real run. They are covered by Run B.

**5. `eval/cases/CASES.md`:** the case 13 row and the row 04 wording were already done by Simen on 24.11, and
case 13 is already in `eval/cases/` (Simen's own expected.json, not overwritten). Still to do: add
`A = arrangementsutvikling_innen_idrett` to the grant-id list at the top, and this sentence under it:
`A is in must_reject of every case that reaches the matcher (none is a sports event).`

**6. Add an entry to `docs/prompt-log.md`** in the same style as the last entries: the corpus refresh on 25.11
(arrangementsutvikling is new; H, F and K gained the Støttenivå, Søknadsvurdering and Avgrensning sections), case 13
added, `arrangementsutvikling` in `must_reject` of 11 cases, every expected.json re-checked by Simen and Elias,
an eval edit by humans.

**7. Optional B3**, only if steps 1–6 are done by early afternoon: verify 1–2 deferred grants (Spillemidler or ULF),
four eyes, copy them into the corpus, and add one `must_match` case each. Otherwise skip B3 and say so in the white paper.

**8. Commit** (on go-ahead). The corpus is then frozen for Run B on 26.11.

## What changed in the grant texts (state 24.11, redo in step 2)
| Grant | Change |
|---|---|
| arrangementsutvikling_innen_idrett | NEW: FLI, Frivillighetsregisteret, region 34, max 350 000, deadline 2027-04-01 |
| hamar_driftstilskudd (D) | `checked_at` only |
| folkehelse (H) | new Støttenivå / Søknadsvurdering / Avgrensning sections; still "Kommunen må stå som søker" |
| friluftsliv (F) | form URL text only; deadline still 2026-12-01 |
| kunstnerisk (K) | new Krav til søknaden / Søknadsvurdering / Avgrensning; one-municipality rule moved out of Formål; one Formål sentence now appears twice (check against the live page) |

No amount, deadline, org-form or region field changed for D, H, F or K, so the existing filter results stay the same.
