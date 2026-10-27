---
name: brreg-api
description: Use when looking up an organisation by orgnr, calling data.brreg.no, or reading Brreg fixtures: endpoints, fields we use, privacy rules.
---
# Brønnøysund Enhetsregisteret (open data, no key)
Verified by a live call on 2026-10-27.

- Lookup: `GET https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}`. Unknown orgnr → 404, empty body.
- Search: `GET .../api/enheter?navn=<name>&kommunenummer=<4 digits>&size=5`, results in `_embedded.enheter`.
- Send a User-Agent naming the program: `innlandet-course-project (github.com/Simen-Johansen/Innlandet)`.
- Cache responses; offline runs read `fixtures/brreg/<orgnr>.json`.
- Test orgnr: `871586152` = HAMAR IDRETTSLAG HOVEDLAGET (FLI, kommune 3403, in Frivillighetsregisteret).
  `970169215` (from our rough plan) does NOT exist.

## Fields we keep
`organisasjonsnummer`, `navn`, `organisasjonsform.kode` (e.g. FLI, KOMM), `registrertIFrivillighetsregisteret`,
`forretningsadresse.kommunenummer` (Innlandet starts with `34`), `naeringskode1.beskrivelse`,
`konkurs`, `underAvvikling`.

## Privacy (strip before saving anything)
- Drop `telefon`, `mobil`, `postadresse`, `forretningsadresse.adresse`: they can point to a person.
- Never call `/enheter/{orgnr}/roller`: it lists board members by name.
- Reject organisasjonsform `ENK` (enkeltpersonforetak): its name is a person's name.
