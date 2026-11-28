# Known failure (fix pending verification): Regionalt kulturfond rejected about 1 run in 4 (2026-11-28)

**Symptom.** Full eval 28.11 (`docs/eval-logs/eval_2026-11-28_103011.log`, 3.84 USD): **23/25 cases**.
`02_typical_arts_two_municipalities` (run 1) and `04_boundary_arts_hamar_only` (run 2) each failed 1 of 3 runs with
`regionalt_kulturfond_innlandet: expected match, got reject`. Stages 1-3 were identical in every run (7 kept, 2
rejected, kulturfond kept), so the stage 4 matcher (model) is the source. A probe that same day (6 runs, about
0.70 USD) gave 1 more reject, and 2 extra runs of case 02 gave 1 more (`eval_2026-11-28_110302.log`,
`eval_2026-11-28_110333.log`). In total **4 rejects in 14 runs**.

**What the matcher said** (`matches_reject_before_fix.json`):
"Condition 1 fails: the 'Hva kan det søkes om' section gives only a broad purpose and does not name youth
workshops or an open field." Condition 1 in `harness/prompts/match.md` requires that "Hva kan det søkes om" names
the project's activity.

**First hypothesis, wrong.** We thought the scope sentence "Ordningen er åpen for alle kultur- og kunstuttrykk"
(under `## Hvem kan søke`) was missing from the matcher's view, and widened condition 1 in `match.md`. Case 02 then
failed again (1 of 2 runs). The reason it could not work: `harness/filter.py` gives the matcher only "Formål" and
"Hva kan det søkes om" (`MATCH_SECTIONS`). "Hvem kan søke" never reaches the model. The prompt change was reverted.

**Real cause: heading levels in `out/match_input.md`.** `filter.py` wrote each section under a `###` heading, but
the kulturfond grant's own sub-headings inside "Hva kan det søkes om" are also `###` (`### Tidligere ordninger…`,
`### Krav til søknaden`, `### Vi gir ikke tilskudd til`, `### Vurdering av søknaden`, `### Søknadskategorier`;
see `match_input_before_fix.md`, lines 140-188). To the model the section ends after one line ("Formål: Bidra til
gode lokalsamfunn …"). The sentence that satisfies condition 1 sits under Søknadskategorier: "Det kan søkes om
tilskudd til å utvikle og gjennomføre mindre kunst- og kulturaktiviteter". It looks like a separate section,
so the model sometimes ignores it.

**Fix (in this commit, `harness/filter.py`).** Headings inside a section text go one level down (`###` → `####`),
so they read as part of their section. Prompt, grant files and `eval/` are unchanged. Checked without model cost:
`check_filter.py` PASS, `check_grants.py` PASS, kulturfond sub-headings now `####` under `### Hva kan det søkes om`.
**Side effect to watch:** other grants with sub-headings (for example fondsordning's `Avgrensing`) now show
their exclusions as part of "Hva kan det søkes om". That is more correct, but it can change reject verdicts.

## To do on 2026-11-29 (not verified yet)

1. **Wait until after 11:15 local time (10:15 UTC).** The last model call on 28.11 was at 10:04 UTC. The kill switch
   halts above 5 USD in 24 h (`harness/run.py`, `DAY_BUDGET_USD`), and the 24-hour total was 4.91 USD on 28.11.
   Before starting, check that `out/HALTED` does not exist and that the last-24h cost is below 1.10 USD.
2. **Run the full eval once:** `python eval/run_eval.py` (about 3.84 USD, about 30 min). Do not run anything else
   that calls the model the same day before it finishes.
3. **Read the result:**
   - Pass condition: 25/25, and kulturfond `match` in all 6 runs of cases 02 and 04.
   - Check that every case with `must_reject` in `expected.json` still passes, plus 11_reject_off_topic and the
     stress_01/02 injection cases. These cases test the side effect.
   - If kulturfond still fails: the fix is not enough. Keep `filter.py`, report it, and document 02/04 as known flaky.
   - If a case that passed before now fails: revert the `filter.py` change and keep this note as a known failure.
4. **Record the result** here (before 23/25, after x/25, cost), in the white paper evaluation section, and in
   `docs/prompt-log.md` if needed. Commit only after Simen approves.
