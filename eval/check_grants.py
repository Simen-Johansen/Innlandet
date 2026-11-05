"""Check for task 002 (updated for tasks 010/015): grant files follow the innlandet-grants format.

Run: python eval/check_grants.py
Env: GRANTS_DIR (default context/grants), EVAL_TODAY (default: real date).

New in W45: `checked_at` (last confirmed against the live page) and `source_modified`
(the page's "Sist endret", or "unknown"). Staleness is measured on checked_at.
"""
import re
import sys
from datetime import date

from common import EMAIL, GRANTS, PHONE, ROOT, as_list, check, parse_grant, today

REQUIRED = ["id", "title", "url", "provider", "applicant_orgforms",
            "requires_frivillighetsregisteret", "region_prefix", "target_group",
            "max_amount_nok", "deadlines", "fetched_at", "checked_at", "source_modified",
            "verified_by"]
HEADINGS = ["## Formål", "## Hvem kan søke", "## Hva kan det søkes om",
            "## Vedlegg", "## Frister og rapportering"]
MAX_AGE_DAYS = 30
REF = today()


def iso(name, key, value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        check(False, f"{name}: {key} {value!r} is not YYYY-MM-DD")


files = sorted(GRANTS.glob("*.md")) if GRANTS.exists() else []
check(len(files) >= 4, f"expected at least 4 grant files in {GRANTS}, found {len(files)}")

ids = set()
for f in files:
    meta, body = parse_grant(f)
    name = f.name
    missing = [k for k in REQUIRED if not meta.get(k)]
    check(not missing, f"{name}: missing frontmatter keys {missing}")
    todo = [k for k, v in meta.items() if "TODO" in v]
    check(not todo, f"{name}: unfinished draft, TODO in {todo} (task 016: a human completes it)")
    check(meta["id"] == f.stem, f"{name}: id {meta['id']!r} != file name")
    check(meta["url"].startswith("https://"), f"{name}: url must start with https://")
    check(meta["requires_frivillighetsregisteret"] in ("true", "false"),
          f"{name}: requires_frivillighetsregisteret must be true or false")
    check(meta["region_prefix"].isdigit() and len(meta["region_prefix"]) in (2, 4),
          f"{name}: region_prefix must be 2 or 4 digits")
    check(meta["max_amount_nok"] == "unknown" or meta["max_amount_nok"].isdigit(),
          f"{name}: max_amount_nok must be an integer or 'unknown'")
    check(as_list(meta["applicant_orgforms"]), f"{name}: applicant_orgforms is empty")
    for d in as_list(meta["deadlines"]):
        iso(name, "deadline", d)
    fetched = iso(name, "fetched_at", meta["fetched_at"])
    checked = iso(name, "checked_at", meta["checked_at"])
    check(fetched <= checked <= REF, f"{name}: need fetched_at <= checked_at <= today ({fetched}, {checked}, {REF})")
    age = (REF - checked).days
    check(age <= MAX_AGE_DAYS, f"{name}: stale context, last checked {age} days ago (max {MAX_AGE_DAYS})")
    sm = meta["source_modified"]
    check(sm == "unknown" or re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", sm),
          f"{name}: source_modified {sm!r} must be YYYY-MM-DDTHH:MM or 'unknown'")
    for h in HEADINGS:
        check(h in body, f"{name}: body is missing heading {h!r}")
    full = f.read_text(encoding="utf-8")
    m = EMAIL.search(full)
    check(not m, f"{name}: contains an e-mail address ({m.group(0) if m else ''})")
    m = PHONE.search(body)
    check(not m, f"{name}: body contains something like a phone number ({m.group(0) if m else ''})")
    ids.add(meta["id"])

# The harness parser must agree with this independent parser (and honour GRANTS_DIR).
sys.path.insert(0, str(ROOT / "harness"))
try:
    from grants import load_grants
except ImportError as e:
    check(False, f"harness/grants.py with load_grants() not found: {e}")
loaded = load_grants()
loaded_ids = {g["id"] if isinstance(g, dict) else g.id for g in loaded}
check(loaded_ids == ids, f"load_grants() ids {sorted(loaded_ids)} != files in {GRANTS} {sorted(ids)}")

print("PASS")
