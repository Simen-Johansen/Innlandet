"""Check for task 002: context/grants/*.md follow the innlandet-grants format.

Red first: fails with "no grant files" before the task.
Run: python eval/check_grants.py
"""
import sys
from datetime import date

from common import EMAIL, GRANTS, PHONE, ROOT, as_list, check, parse_grant

REQUIRED = ["id", "title", "url", "provider", "applicant_orgforms",
            "requires_frivillighetsregisteret", "region_prefix", "target_group",
            "max_amount_nok", "deadlines", "fetched_at", "verified_by"]
HEADINGS = ["## Formål", "## Hvem kan søke", "## Hva kan det søkes om",
            "## Vedlegg", "## Frister og rapportering"]
MAX_AGE_DAYS = 30

files = sorted(GRANTS.glob("*.md")) if GRANTS.exists() else []
check(len(files) >= 4, f"expected at least 4 grant files in context/grants/, found {len(files)}")

ids = set()
for f in files:
    meta, body = parse_grant(f)
    name = f.name
    missing = [k for k in REQUIRED if not meta.get(k)]
    check(not missing, f"{name}: missing frontmatter keys {missing}")
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
        try:
            date.fromisoformat(d)
        except ValueError:
            check(False, f"{name}: deadline {d!r} is not YYYY-MM-DD")
    try:
        age = (date.today() - date.fromisoformat(meta["fetched_at"])).days
    except ValueError:
        check(False, f"{name}: fetched_at is not YYYY-MM-DD")
    check(age <= MAX_AGE_DAYS, f"{name}: stale context, fetched {age} days ago (max {MAX_AGE_DAYS})")
    for h in HEADINGS:
        check(h in body, f"{name}: body is missing heading {h!r}")
    full = f.read_text(encoding="utf-8")
    m = EMAIL.search(full)
    check(not m, f"{name}: contains an e-mail address ({m.group(0) if m else ''})")
    m = PHONE.search(body)
    check(not m, f"{name}: body contains something like a phone number ({m.group(0) if m else ''})")
    ids.add(meta["id"])

# The harness parser must agree with this independent parser.
sys.path.insert(0, str(ROOT / "harness"))
try:
    from grants import load_grants
except ImportError as e:
    check(False, f"harness/grants.py with load_grants() not found: {e}")
loaded = load_grants()
loaded_ids = {g["id"] if isinstance(g, dict) else g.id for g in loaded}
check(loaded_ids == ids, f"load_grants() ids {sorted(loaded_ids)} != files {sorted(ids)}")

print("PASS")
