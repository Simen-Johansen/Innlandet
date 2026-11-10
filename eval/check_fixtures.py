"""Check: no personal contact data in committed Brreg fixtures (project constraint: no personal data).

Run: python eval/check_fixtures.py
Fails on any fixtures/brreg_*.json with an e-mail, phone/mobile field, a street address line,
or text that looks like an e-mail or Norwegian phone number. Fix: python tools/redact_brreg.py <file>
"""
import json

from common import EMAIL, FIXTURES, PHONE, check

files = sorted(FIXTURES.glob("brreg_*.json"))
check(files, "no fixtures/brreg_*.json found")
for f in files:
    data = json.loads(f.read_text(encoding="utf-8"))
    for key in ("epostadresse", "mobil", "telefon", "telefaks"):
        check(key not in data, f"{f.name}: contains '{key}' (run tools/redact_brreg.py)")
    for addr in ("forretningsadresse", "postadresse"):
        check("adresse" not in (data.get(addr) or {}), f"{f.name}: {addr} has street lines (run tools/redact_brreg.py)")
    text = json.dumps(data, ensure_ascii=False)
    for pattern, label in ((EMAIL, "e-mail"), (PHONE, "phone number")):
        m = pattern.search(text.replace(data.get("organisasjonsnummer", "#"), ""))
        check(not m, f"{f.name}: something like a {label}: {m.group(0) if m else ''}")
print(f"{len(files)} fixtures clean")
print("PASS")
