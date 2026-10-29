# SPEC: Volunteer Grant Navigator

## Problem
Volunteer clubs in Innlandet (sports clubs, school bands, outdoor groups) are run by unpaid volunteers.
Grant rules from Innlandet fylkeskommune and the municipalities are spread over many pages and PDFs
in formal Norwegian. Clubs miss deadlines or apply for grants they are not eligible for.
The same reading work is repeated by every club, every season.

## Users
A volunteer treasurer or board member of a club registered in Enhetsregisteret, located in Innlandet.

## Input
`input_request.json`:
```json
{ "orgnr": "9 digits", "project_idea": "one sentence, max 300 chars",
  "requested_amount_nok": 60000, "output_language": "en" | "no" }
```

## Output
- `out/plan.json`: a machine-checkable action plan (schema in task 005)
- `out/grant_action_plan.md`: the same content rendered for humans by code
- or `out/rejection.json` when the input must be rejected

## Definition of success (all checked by code unless marked)
1. **Entity facts are true.** `orgnr`, `navn`, `organisasjonsform`, `kommunenummer` and the
   Frivillighetsregisteret status in the output equal the Brreg response saved in `out/entity.json`.
2. **No invented grants.** Every grant in the plan exists in `context/grants/`, passed the hard filter
   (stage 3), and was matched in stage 4.
3. **No invented facts.** Every URL, deadline and NOK maximum in the plan is copied exactly from that
   grant's file. Every evidence quote is a verbatim substring of the grant file.
4. **No ineligible grants.** No grant whose hard rules exclude the applicant appears in the plan
   (wrong organisation form, outside the region, missing required registration).
5. **No personal data.** The plan contains no e-mail addresses, phone numbers or personal names.
6. **Correct rejection.** Invalid orgnr (checksum), unknown or deleted entity, an entity outside
   Innlandet, or an empty or off-topic project idea gives `out/rejection.json` with a reason code,
   and the run exits with code 3.
7. *(Judgment, LLM-as-judge, documented in task 014.)* The guide is plain language (klarspråk) and
   actually helpful to a volunteer.

## Exit codes of `python harness/run.py`
`0` plan delivered · `1` a check failed after retries · `3` input rejected (expected) · `4` halted by kill switch

## Out of scope
Writing the application itself, submitting it, any login-protected portal, and any data about persons
(including the Brreg roles endpoint).
