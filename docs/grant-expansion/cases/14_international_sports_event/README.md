# Case 14 (proposal): international sports event, Raufoss → N must_match

Status: Claude's proposal (26.11). Humans check it, then `cp -r` it into `eval/cases/` and add the `CASES.md` row.

- Club: **Raufoss Idrettslag, 976728211**. FLI, kommunenummer 3443 (Vestre Toten), registered in
  Frivillighetsregisteret. Fixture `fixtures/brreg_976728211.json` was saved by `harness/entity.py` (allowlisted
  fields only, no roles endpoint); `check_fixtures` PASS. Claude picked the club from a Brreg name search.
  **Confirm it is a sensible real host** (or swap the orgnr and re-run `entity.py` live once).
- Idea: an international youth football tournament, August 2027, ~1 500 players from three countries,
  volunteers, a sustainability coordinator, and Innlandet profiling. Requested 250 000 (N max 1 000 000).
- `today` 2026-11-05. N's next deadline is 2027-02-01, which covers events "påfølgende sommer og høst". August 2027
  is ≥3 months after it, so there is no date gap.

## Reasoning per grant (filter result from `screen_cases.py`)

| Grant | Filter | Proposed | Why |
|---|---|---|---|
| N fondsordning_store_idrettsarrangementer | kept | **must_match** | international, >500 participants, profiles Innlandet: the core of N |
| R regionalt_kulturfond_innlandet | kept | must_reject | sports event: R excludes "hovedsakelig idrett" |
| A arrangementsutvikling_innen_idrett | kept | **leave out** | grey: A covers "lokale, regionale og nasjonale idrettsarrangement" and does not exclude big events; only N's page draws the 500 line. International is not in A's list, but a matcher that matches A as well is not clearly wrong. Its deadlines are also a date-gap trap (1 Apr = Jul–Dec rounds). |
| F tilskudd_til_friluftslivsaktivitet | kept | must_reject | not outdoor life |
| K tilskudd_til_kunstnerisk_aktivitet_for_barn_og_ungdom | kept | must_reject | not arts |
| D hamar_driftstilskudd_frivillige_organisasjoner | outside_region | must_reject (outside_region) | Hamar only |
| H tilskudd_til_folkehelse_og_livskvalitet | org_form_not_allowed | must_reject (org_form_not_allowed) | municipalities only |
| S test_synthetic_frivillighetsregisteret | kept | **humans decide** | Claude may not read the corpus file; it is not in the proposed expected.json |
| I test_synthetic_injection | outside_region | not listed | Lillehammer only (3405), like the other cases |

Proposed `CASES.md` row:
`| 14 international sports event, Raufoss (976728211) | 11-05 | 0 | N match (international youth tournament, ~1 500 players, Aug 2027 = 1 Feb round). R reject (excludes sport). F, K reject. D rejected outside_region, H rejected. A left out (covers national events; only N's page sets the 500 line) |`

Near-miss for N: **case 13** (regional youth roller-ski sprint). N's page sends regional events to A, so the
proposal in `decisions.tsv` is N `must_reject` for case 13.
R needs no new case if the humans accept the proposals: R `must_match` in 02, 04 and 07 (arts) and `must_reject`
in every outdoor and sports case.
