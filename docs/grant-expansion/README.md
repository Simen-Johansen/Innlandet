# Grant expansion (task 017): review sheet

Status 26.11: step 0 done, step 1 drafts written. **Next: step 2 (humans, four eyes).**
Decided by Simen on 26.11: add **N** and **R** only. U is swapped out and no third grant is added (coverage 6/24).
Cut-off: **Fri 27.11 10:00**.

| Code | Page | Draft | Grant id |
|---|---|---|---|
| N | 37168 | `grants/fondsordning_store_idrettsarrangementer.md` | `fondsordning_store_idrettsarrangementer` |
| R | 62589 | `grants/regionalt_kulturfond_innlandet.md` | `regionalt_kulturfond_innlandet` |

Not added. They stay `deferred_verification`; name them in the prompt log:
- **U 58403 ULF**: only youth councils, pupil councils and upper secondary schools may apply, so clubs cannot.
- **62588 utviklingsprosjekt kunst og kultur**: merged into R from 2026 (the page is a stub). A human may note it in the catalog.
- **22177 nedsatt funksjonsevne**: operating support for county-level organisations (≥50 members in ≥5
  municipalities); deadline 1 Feb 2026 has passed.
- Considered and rejected as a replacement: 66424 trafikksikkerhet (no Formål heading: the weekly update would hit
  a template failure every week), 36673 (deadline 20 Mar 2026 has passed), 36451 (municipalities only).

## Step 0: what the live pages say (read 26.11)

| | N: Fondsordning store nasjonale og internasjonale idrettsarrangementer | R: Regionalt kulturfond Innlandet |
|---|---|---|
| Sist endret | 05.11.2026 14.36 | 16.10.2026 09.32 |
| Who may apply | "arrangører av større idrettsarrangementer av nasjonal og – helst – internasjonal betydning"; profit may not be paid out to private owners; the big event companies are named | "organisasjoner, miljøer og utøvende innen det brede kunst-, kultur- og kulturarvfeltet"; must be in Enhetsregisteret; **municipalities may not apply** |
| Region | event in Innlandet that profiles Innlandet and draws people from outside the county | "tilknytning til Innlandet" is an assessment criterion |
| Frivillighetsregisteret | not mentioned | not mentioned |
| Amount | "begrenses oppad til 1 million kroner" (except the big event companies); a fixed event "inntil 350 000 kroner per år i maksimalt tre år"; ≤1/3 of total cost | "fra 20 000 kroner til 300 000 kroner" |
| Deadlines | 1 Feb and 1 Sep, **no year on the page** | 15 Jan 2027 ("Informasjon om neste søknadsfrist kommer") |

## Rules only the matcher can apply (date gap, affiliation and others)

**N**
- Date gap: **1 Feb → events "i hovedsak … påfølgende sommer og høst"; 1 Sep → "påfølgende vinter/vår"**; the event
  must take place at least 3 months after the deadline. `deadlines` holds only the date.
- Size and reach: "Regionale arrangement og nasjonale arrangementer/mesterskap med færre enn 500 deltakere kan ikke
  søke … De kan søke om støtte fra tilskuddsordningen arrangementsutvikling innen idrett". This is the A/N boundary,
  stated by the page itself.
- No support for participation, prize money, or travel and accommodation for athletes; no deficit cover; events that
  qualify for other county schemes are not prioritised.
- Affiliation: none stated (no NIF requirement on the page).

**R**
- Exclusion against A/D/F: "aktiviteter eller tiltak som **hovedsakelig innebærer idrett eller friluftsliv**". This is
  the key near-miss for sports and outdoor cases.
- No ordinary operating costs, no multi-year grants, no building investment, no book/CD releases or pure touring.
- Minimum application 20 000 (the filter has no minimum field).
- Priority for applicants without other county support. Overlap with K: R covers arts in general, local or
  regional; K covers arts for children and youth.
- Date gap: no project period given (only a progress plan with start and end).
- Affiliation: none (Enhetsregisteret only).
- Future-work evidence (joint applications, see ROADMAP "Future work"): municipalities "kan være del av tiltaket,
  men ikke være søker". A partner may take part without applying, which `applicant_orgforms` cannot express.

## Step 2: fields the humans fill

The values below are Claude's reading, as questions. **Check each against the live page, not against this sheet.**

| Field | N: Claude's reading (to check) | R: Claude's reading (to check) |
|---|---|---|
| applicant_orgforms | FLI? Also STI/AS for event companies? The page says "arrangører" (cf. K's comment) | FLI, ENK, AS, STI…? Not KOMM ("kan ikke være søker") |
| requires_frivillighetsregisteret | false (not mentioned) | false (not mentioned) |
| region_prefix | 34 | 34 |
| target_group | alle | alle |
| max_amount_nok | 1000000? or 350000 for a fixed event? The audit regex only sees "inntil 350 000" | 300000 |
| deadlines | 2027-02-01, 2027-09-01 (no year on the page) | 2027-01-15 |
| title | page h1 (draft has the catalog title) | page h1 |

Then: set `verified_by` and `checked_at`, delete the `# TODO` comment on `title`, and remove every `TODO`.
`<id>.checklist.md` lists every heading, amount and date with its sentence.

## Commands (after step 2)
```
cp docs/grant-expansion/grants/<id>.md context/grants/          # humans; set the catalog status to ingested
python eval/check_grants.py && python eval/check_catalog.py
python harness/update_grants.py --audit --offline --pages-dir fixtures/pages_raw
python tools/screen_cases.py --add docs/grant-expansion/grants   # step 4 -> decisions.tsv
python tools/add_expectation.py docs/grant-expansion/decisions.tsv --check   # step 7, humans
python tools/screen_cases.py                                     # step 8
```
`decisions.tsv`: fill `decision` (`must_match` / `must_reject` / `leave_out`) and `decided_by`. An optional `reason`
on a `must_reject` row (e.g. `outside_region`) means the filter must reject it with exactly that reason.

## Step 6: new cases (proposal follows)
- N must_match: an Innlandet club hosting a national championship or international event with ≥500 participants.
- N near-miss must_reject: a regional event (case 13 already is one, and it may become N `must_reject` in step 5).
- R must_match: an arts or culture project with regional reach by a culture association (not children-only, so that
  R and K differ).
- R near-miss must_reject: a sports event, or an arts project for one municipality only.
I need real org numbers from you for the N and R `must_match` clubs (live Brreg lookup through
`harness/entity.py`; no roles endpoint).
