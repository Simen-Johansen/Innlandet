"""Stage 1: look up the club in Enhetsregisteret (task 001).

Usage: python harness/entity.py input_request.json [--offline]

Writes out/entity.json (exit 0), out/rejection.json (exit 3), or out/rejection.json with reason
upstream_unavailable (exit 1) when Brreg is down or its response fails the schema check (task 013).
Standard library only. Never calls the roles endpoint and keeps no street address.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import faults

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
FIXTURES = ROOT / "fixtures"

API = "https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}"
USER_AGENT = "innlandet-grant-navigator (https://github.com/Simen-Johansen/Innlandet)"
TIMEOUT_S = 10
BACKOFF_S = (1, 2)  # seconds before retry 1 and 2: at most 3 attempts (task 013)
NOT_FOUND_CODES = (404, 410)  # unknown or deleted entity
INNLANDET_PREFIX = "34"
MAX_IDEA_CHARS = 300  # SPEC.md: "one sentence, max 300 chars"
LANGUAGES = ("en", "no")


class Rejection(Exception):
    def __init__(self, reason, detail):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


class UpstreamError(Rejection):
    """Brreg is down or degraded: exit 1 with upstream_unavailable, not a rejection (task 013)."""

    def __init__(self, detail):
        super().__init__("upstream_unavailable", detail)


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


def validate_request(request):
    """Input schema (SPEC.md, task 012), checked before any lookup or model call.

    A bad orgnr stays `invalid_orgnr`; every other problem is `invalid_request`.
    """
    if not isinstance(request, dict):
        raise Rejection("invalid_request", "input_request.json must be a JSON object")
    orgnr = request.get("orgnr")
    if not mod11_ok(orgnr):
        raise Rejection(
            "invalid_orgnr", f"{orgnr!r} is not 9 digits with a valid MOD11 check digit"
        )
    idea = request.get("project_idea")
    if not isinstance(idea, str) or not idea.strip():
        raise Rejection("invalid_request", "project_idea: missing or empty")
    if len(idea) > MAX_IDEA_CHARS:
        raise Rejection(
            "invalid_request", f"project_idea: {len(idea)} characters (max {MAX_IDEA_CHARS})"
        )
    if request.get("output_language") not in LANGUAGES:
        raise Rejection(
            "invalid_request",
            f"output_language: {request.get('output_language')!r} is not one of {list(LANGUAGES)}",
        )
    amount = request.get("requested_amount_nok")
    if amount is not None and (type(amount) is not int or amount < 0):
        raise Rejection(
            "invalid_request", f"requested_amount_nok: {amount!r} is not a whole number >= 0"
        )


def fetch_once(url, orgnr, offline):
    faults.brreg_request(url)
    if offline:
        path = FIXTURES / f"brreg_{orgnr}.json"
        if not path.exists():
            raise Rejection("not_found", f"no offline fixture {path.name}")
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch(orgnr, offline):
    """Return the raw Brreg JSON for orgnr (task 013).

    404/410 (unknown or deleted entity) is a rejection. 429, 5xx, timeouts and network errors
    are retried with backoff; when the retries run out it is an outage, not a rejection.
    """
    url = API.format(orgnr=orgnr)
    for attempt, wait in enumerate((*BACKOFF_S, None), 1):
        try:
            return faults.brreg_response(fetch_once(url, orgnr, offline))
        except urllib.error.HTTPError as e:
            if e.code in NOT_FOUND_CODES:
                raise Rejection("not_found", f"Brreg returned HTTP {e.code} for {orgnr}") from e
            if e.code != 429 and e.code < 500:
                raise UpstreamError(f"Brreg returned HTTP {e.code} for {orgnr}") from e
            problem = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError) as e:
            problem = f"{type(e).__name__}: {getattr(e, 'reason', e)}"
        except json.JSONDecodeError as e:
            raise UpstreamError(f"Brreg response for {orgnr} is not JSON: {e}") from e
        if wait is None:
            raise UpstreamError(f"Brreg unavailable after {attempt} attempts, last: {problem}")
        print(f"Brreg attempt {attempt} failed ({problem}), retrying in {wait} s", file=sys.stderr)
        time.sleep(wait)


def extract(raw, orgnr=None):
    """Flat entity with exactly the fields allowed by the brreg-api skill.

    Schema check first: a response without a boolean registrertIFrivillighetsregisteret is
    degraded, never read as False (that would quietly remove grants, task 013).
    """
    if not isinstance(raw, dict):
        raise UpstreamError(f"Brreg response is {type(raw).__name__}, not an object")
    if orgnr is not None and raw.get("organisasjonsnummer") != orgnr:
        raise UpstreamError(
            f"Brreg response is for {raw.get('organisasjonsnummer')!r}, not {orgnr!r}"
        )
    if not isinstance(raw.get("registrertIFrivillighetsregisteret"), bool):
        raise UpstreamError(
            "Brreg response has no boolean registrertIFrivillighetsregisteret field "
            f"(got {raw.get('registrertIFrivillighetsregisteret', 'nothing')!r})"
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
    entity = extract(raw, orgnr)
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
        validate_request(request)
        entity = lookup(request["orgnr"], offline)
    except UpstreamError as r:
        write_json(OUT / "rejection.json", {"reason": r.reason, "detail": r.detail})
        print(f"upstream unavailable: {r.detail}", file=sys.stderr)
        return 1
    except Rejection as r:
        write_json(OUT / "rejection.json", {"reason": r.reason, "detail": r.detail})
        print(f"rejected: {r.reason}: {r.detail}", file=sys.stderr)
        return 3
    write_json(OUT / "entity.json", entity)
    print(f"ok: {entity['navn']} ({entity['organisasjonsnummer']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
