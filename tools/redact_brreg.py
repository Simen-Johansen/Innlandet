"""Human tool: remove personal contact data from saved Brreg responses, in place.

  python tools/redact_brreg.py fixtures/brreg_*.json   (or a path outside the repo)

Removes e-mail, phone and mobile numbers, and the street lines of both addresses (often
"c/o <person>" or a home address). Keeps everything the harness and check_entity.py use,
including kommunenummer and _links. Adds "_redacted": true. Standard library only.
"""
import glob
import json
import sys

DROP = ("epostadresse", "mobil", "telefon", "telefaks")

for pattern in sys.argv[1:]:
    for path in glob.glob(pattern):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for key in DROP:
            data.pop(key, None)
        for addr in ("forretningsadresse", "postadresse"):
            if isinstance(data.get(addr), dict):
                data[addr].pop("adresse", None)
        data["_redacted"] = True
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"redacted {path}")
