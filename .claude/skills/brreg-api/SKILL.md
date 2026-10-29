---
name: brreg-api
description: Use when calling data.brreg.no, reading fixtures/brreg_*.json, or writing out/entity.json: endpoint, fields to keep, error handling, privacy rules.
---
# Enhetsregisteret open API (Brønnøysundregistrene)

- Endpoint: `GET https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}`. Open, no key.
  Send a User-Agent naming the app and repo URL, never a personal e-mail.
- Validate the orgnr **before** calling: 9 digits, MOD11 with weights 3,2,7,6,5,4,3,2.
  Check digit = 11 − (sum mod 11); 11 → 0; 10 → invalid. An invalid orgnr is rejected without a request.
- `out/entity.json` is flat, with exactly these keys (eval/check_entity.py enforces it):
  `organisasjonsnummer`, `navn`, `organisasjonsform` (= raw `organisasjonsform.kode`), `kommunenummer`,
  `registrertIFrivillighetsregisteret`, `naeringskode` (= raw `naeringskode1.kode`), `konkurs`,
  `underAvvikling`, `fetched_at` (ISO date).
- If `registrertIFrivillighetsregisteret` is missing in the response, do not default it to false:
  reject with a clear reason instead (silent degradation, task 013).
- `kommunenummer`: take `forretningsadresse.kommunenummer`; if missing (common for FLI), use
  `postadresse.kommunenummer`. Drop the street address: for small clubs it is often someone's home.
- Innlandet: `kommunenummer` starts with `34` (Hamar = 3403).
- Non-200 responses (unknown or deleted entities): record the status code in a rejection;
  do not guess. Verify the real status codes once by hand and save each response as a fixture.
- Never call `/roller` (it returns personal names).
