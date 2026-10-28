# Task 001: Look up the club in Enhetsregisteret (stage 1)

## Goal
`python harness/entity.py input_request.json` writes `out/entity.json` with the verified public facts
about the club, or `out/rejection.json` if the orgnr cannot be used.

## Context
- Input: `input_request.json` (format in SPEC.md)
- API: https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr} (verified by a human to exist)
- Field list, MOD11 rule and privacy rules: `brreg-api` skill
- Fixtures for C2: `fixtures/brreg_<orgnr>.json`, one live call by hand for one real Innlandet club.
  **Look up the orgnr on Brreg yourself**; the 970169215 in our first outline fails MOD11 and is not a
  real orgnr (prompt-log line). Put the real one in `fixtures/input_hamar.json`.
- `fixtures/input_bad_checksum.json` (orgnr 970169215) is synthetic and needs no API call.
- Non-Innlandet and unknown-orgnr fixtures come later, in task 009

## Constraints
- Do not edit eval/
- Python standard library only (`urllib.request`, `json`)
- User-Agent header with app name + repo URL; one request per run; timeout 10 s
- `--offline` reads `fixtures/brreg_<orgnr>.json` instead of calling the API; output is identical
- Keep only the fields listed in the skill; no street address, no roles endpoint
- Rejections: `{"reason": "invalid_orgnr" | "not_found" | "outside_innlandet" | "bankrupt_or_dissolving", "detail": "..."}`, exit code 3

## Acceptance (all must pass)
- `python harness/entity.py fixtures/input_hamar.json --offline && python eval/check_entity.py` prints PASS
- `python harness/entity.py fixtures/input_bad_checksum.json --offline` exits 3, then
  `python eval/check_rejection.py invalid_orgnr` prints PASS (no network call, no entity.json)
- The check failed before this task started (red first)

## What eval/check_entity.py asserts (Author writes this first)
- `out/entity.json` exists, valid UTF-8 JSON, exactly the 9 flat keys in the `brreg-api` skill
- `organisasjonsnummer` is 9 digits and passes MOD11
- `organisasjonsnummer`, `navn`, `organisasjonsform`, `kommunenummer`, `registrertIFrivillighetsregisteret`
  equal the values in the raw fixture (no invented or altered facts)
- `kommunenummer` matches `^34\d\d$`
- no key contains `adresse`, no value contains `@`

## Out of scope
Grants, any LLM call, retries on API failure (task 013)
