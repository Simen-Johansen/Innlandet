"""Check for task 001: out/entity.json is true to the saved Brreg response.

Red first: fails with "out/entity.json does not exist" before the task.
Run: python eval/check_entity.py
"""
import re
from datetime import date

from common import FIXTURES, OUT, check, load_json, mod11_ok

ALLOWED_KEYS = {
    "organisasjonsnummer", "navn", "organisasjonsform", "kommunenummer",
    "registrertIFrivillighetsregisteret", "naeringskode", "konkurs",
    "underAvvikling", "fetched_at",
}

entity = load_json(OUT / "entity.json")

check(set(entity) == ALLOWED_KEYS,
      f"keys differ. extra: {sorted(set(entity) - ALLOWED_KEYS)}, missing: {sorted(ALLOWED_KEYS - set(entity))}")

orgnr = entity["organisasjonsnummer"]
check(mod11_ok(orgnr), f"organisasjonsnummer {orgnr!r} is not 9 digits with a valid MOD11 check digit")

raw = load_json(FIXTURES / f"brreg_{orgnr}.json")
addr = raw.get("forretningsadresse") or raw.get("postadresse") or {}
expected = {
    "organisasjonsnummer": raw.get("organisasjonsnummer"),
    "navn": raw.get("navn"),
    "organisasjonsform": (raw.get("organisasjonsform") or {}).get("kode"),
    "kommunenummer": addr.get("kommunenummer"),
    # Missing in raw -> None. The harness must not silently turn a missing field into False.
    "registrertIFrivillighetsregisteret": raw.get("registrertIFrivillighetsregisteret"),
}
for key, value in expected.items():
    check(entity[key] == value, f"{key}: output {entity[key]!r} != Brreg fixture {value!r}")

check(re.fullmatch(r"34\d\d", str(entity["kommunenummer"])),
      f"kommunenummer {entity['kommunenummer']!r} is not in Innlandet (34xx)")
check(isinstance(entity["registrertIFrivillighetsregisteret"], bool),
      "registrertIFrivillighetsregisteret must be true/false")
try:
    date.fromisoformat(str(entity["fetched_at"])[:10])
except ValueError:
    check(False, f"fetched_at {entity['fetched_at']!r} is not an ISO date")

check(not any("adresse" in k for k in entity), "address fields must not be kept")
check(not any("@" in str(v) for v in entity.values()), "a value contains '@'")

print("PASS")
