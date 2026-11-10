# Why each expected.json says what it says (written by the Authors; read before the first run)

Grant ids: F = tilskudd_til_friluftslivsaktivitet, D = hamar_driftstilskudd_frivillige_organisasjoner,
K = tilskudd_til_kunstnerisk_aktivitet_for_barn_og_ungdom, H = tilskudd_til_folkehelse_og_livskvalitet,
S = test_synthetic_frivillighetsregisteret (frozen corpus only).
H is rejected by the filter for every FLI (`org_form_not_allowed`, the first rule), so it is in every
case that reaches stage 3. `must_reject` with a plain id passes on a filter rejection *or* a matcher
"reject"; with a reason it must be that filter reason.

| Case | today | exit | Expectation and why |
|---|---|---|---|
| 01 HHT outdoor | 11-05 | 0 | F match (organised outdoor activity). D reject (strict rule: pays operating support, not projects). K reject (arts, one municipality) |
| 02 arts, 2+ municipalities | 11-05 | 0 | K match (arts for youth, regional reach). F reject (not outdoor). D reject (filter if not in Hamar, else strict rule) |
| 03 ski equipment | 11-05 | 0 or 3 | D reject (equipment purchase is explicitly excluded). K reject. F left out: equipment for outdoor days is a genuine grey area |
| 04 arts, Hamar only | 11-05 | 0 or 3 | K reject: its Formål excludes projects for one municipality only |
| 05 FLI in Stange (934424638) | 11-05 | 0 | F match (same outdoor idea, F is open to all of Innlandet). D rejected `outside_region` (Hamar only). K reject |
| 06 deadline passed | 12-02 | 0 or 3 | F rejected `no_open_deadline` (only deadline 2026-12-01). D and K reject: nothing left fits the outdoor idea |
| 07 amount over max | 11-05 | 0 | K match and K has an amount_note (150 000 requested, max 100 000) |
| 08 not in Frivillighetsregisteret (123456785, synthetic) | 11-05 | 0 | S rejected `not_in_frivillighetsregisteret`, but F still matches: the rule removes only grants that require registration |
| 09 bad checksum | 11-05 | 3 | `invalid_orgnr`, before any model call |
| 10 outside Innlandet | 11-05 | 3 | `outside_innlandet`, before any model call |
| 11 off-topic | 11-05 | 0 or 3 | every real grant rejected, nothing in the plan |

"0 or 3" means the matcher may reject every grant. Tighten it to one value once you have decided
what run.py does when nothing matches (SPEC.md says an off-topic idea gives exit 3).
