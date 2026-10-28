"""Stage 1: look up the club in Enhetsregisteret (task 001).

Usage: python harness/entity.py input_request.json [--offline]

Writes out/entity.json (exit 0) or out/rejection.json (exit 3).
Standard library only. Never calls the roles endpoint and keeps no street address.
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
FIXTURES = ROOT / "fixtures"

API = "https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}"
USER_AGENT = "innlandet-grant-navigator (https://github.com/Simen-Johansen/Innlandet)"
TIMEOUT_S = 10
INNLANDET_PREFIX = "34"


class Rejection(Exception):
    def __init__(self, reason, detail):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def mod11_ok(orgnr):
    """9 digits with a valid MOD11 check digit (weights 3,2,7,6,5,4,3,2)."""
    if not (isinstance(orgnr, str) and len(orgnr) == 9 and orgnr.isascii() and orgnr.isdigit()):
        return False
    weights = [3, 2, 7, 6, 5, 4, 3, 2]
    rest = sum(int(d) * w for d, w in zip(orgnr, weights)) % 11
    check = 11 - rest
    if check == 11:
        check = 0
    return check != 10 and check == int(orgnr[8])


def fetch(orgnr, offline):
    """Return the raw Brreg JSON for orgnr. One request, no retries (task 013)."""
    if offline:
        path = FIXTURES / f"brreg_{orgnr}.json"
        if not path.exists():
            raise Rejection("not_found", f"no offline fixture {path.name}")
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    req = urllib.request.Request(
        API.format(orgnr=orgnr),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise Rejection("not_found", f"Brreg returned HTTP {e.code} for {orgnr}") from e


def extract(raw):
    """Flat entity with exactly the fields allowed by the brreg-api skill."""
    if "registrertIFrivillighetsregisteret" not in raw:
        # Do not silently default to False.
        raise Rejection(
            "not_found",
            "Brreg response has no registrertIFrivillighetsregisteret field",
        )
    addr = raw.get("forretningsadresse") or raw.get("postadresse") or {}
    return {
        "organisasjonsnummer": raw.get("organisasjonsnummer"),
        "navn": raw.get("navn"),
        "organisasjonsform": (raw.get("organisasjonsform") or {}).get("kode"),
        "kommunenummer": addr.get("kommunenummer"),
        "registrertIFrivillighetsregisteret": raw["registrertIFrivillighetsregisteret"],
        "naeringskode": (raw.get("naeringskode1") or {}).get("kode"),
        "konkurs": bool(raw.get("konkurs")),
        "underAvvikling": bool(raw.get("underAvvikling")),
        "fetched_at": date.today().isoformat(),
    }


def lookup(orgnr, offline):
    if not mod11_ok(orgnr):
        raise Rejection(
            "invalid_orgnr", f"{orgnr!r} is not 9 digits with a valid MOD11 check digit"
        )
    raw = fetch(orgnr, offline)
    entity = extract(raw)
    kommunenummer = str(entity["kommunenummer"] or "")
    if not kommunenummer.startswith(INNLANDET_PREFIX):
        raise Rejection(
            "outside_innlandet",
            f"kommunenummer {kommunenummer or 'missing'} is not in Innlandet (34xx)",
        )
    if (
        entity["konkurs"]
        or entity["underAvvikling"]
        or raw.get("underTvangsavviklingEllerTvangsopplosning")
    ):
        raise Rejection("bankrupt_or_dissolving", "entity is bankrupt or being dissolved")
    return entity


def write_json(path, data):
    OUT.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main(argv):
    args = [a for a in argv if a != "--offline"]
    offline = "--offline" in argv
    if len(args) != 1:
        print("usage: python harness/entity.py input_request.json [--offline]", file=sys.stderr)
        return 2
    for name in ("entity.json", "rejection.json", "plan.json"):
        (OUT / name).unlink(missing_ok=True)
    with open(args[0], encoding="utf-8") as f:
        request = json.load(f)
    try:
        entity = lookup(str(request.get("orgnr", "")), offline)
    except Rejection as r:
        write_json(OUT / "rejection.json", {"reason": r.reason, "detail": r.detail})
        print(f"rejected: {r.reason}: {r.detail}", file=sys.stderr)
        return 3
    write_json(OUT / "entity.json", entity)
    print(f"ok: {entity['navn']} ({entity['organisasjonsnummer']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
