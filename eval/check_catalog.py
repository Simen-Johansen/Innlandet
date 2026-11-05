"""Check for task 010: coverage of the county's grant listing.

Inputs:
  fixtures/fylke_index/side-<N>.html  every page of innlandetfylke.no/tjenester/sok-tilskudd (saved raw)
  context/catalog.json:
    {"index_checked_at": "YYYY-MM-DD",
     "entries": [{"page_id": "36453", "url": "https://innlandetfylke.no/...36453.aspx", "title": "...",
                  "status": "ingested" | "not_relevant" | "pending" | "removed",
                  "reason": <code for not_relevant>, "grant_id": <id if ingested>,
                  "decided_by": <initials, for ingested/not_relevant>, "added_at": "YYYY-MM-DD"}]}

"Covered" means: every grant listed by the county is either a verified grant file or has a
human-recorded reason for being left out. Pending entries may not wait more than 14 days.

Run: python eval/check_catalog.py        Env: GRANTS_DIR, EVAL_TODAY
"""
import re
from datetime import date

from common import CONTEXT, FIXTURES, GRANTS, check, domain, load_json, page_id, parse_grant, today

STATUSES = {"ingested", "not_relevant", "pending", "removed"}
REASONS = {"applicant_not_voluntary", "closed", "expired_no_next_round", "not_a_grant", "duplicate"}
PENDING_MAX_DAYS = 14
INDEX_MAX_DAYS = 8
COUNTY = "innlandetfylke.no"
REF = today()

index_dir = FIXTURES / "fylke_index"
pages = sorted(index_dir.glob("side-*.html")) if index_dir.exists() else []
check(pages, "no saved index pages in fixtures/fylke_index/ (side-1.html ...)")
html = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in pages)

# All pagination pages must be saved, or coverage is silently partial.
last_page = max([int(n) for n in re.findall(r"[?&]Side=(\d+)", html)] or [1])
check(len(pages) == last_page, f"index has {last_page} pages but {len(pages)} are saved")

listed = set(re.findall(r'href="[^"]*/tjenester/sok-tilskudd/[^"]*?\.(\d+)\.aspx"', html))
check(listed, "no grant links found in the saved index pages (template changed?)")

cat = load_json(CONTEXT / "catalog.json")
checked_at = date.fromisoformat(cat.get("index_checked_at", "1900-01-01"))
check((REF - checked_at).days <= INDEX_MAX_DAYS, f"catalog index_checked_at {checked_at} is older than {INDEX_MAX_DAYS} days")

entries = {}
for e in cat.get("entries", []):
    pid = str(e.get("page_id", ""))
    check(pid.isdigit(), f"entry {e.get('title')!r}: page_id must be digits")
    check(pid not in entries, f"duplicate page_id {pid}")
    check(page_id(e.get("url", "")) == pid and domain(e["url"]) == COUNTY, f"{pid}: url must be a {COUNTY} page with id {pid}")
    st = e.get("status")
    check(st in STATUSES, f"{pid}: status {st!r} not in {sorted(STATUSES)}")
    if st == "not_relevant":
        check(e.get("reason") in REASONS, f"{pid}: not_relevant needs a reason in {sorted(REASONS)}")
    if st in ("ingested", "not_relevant"):
        check(str(e.get("decided_by", "")).strip(), f"{pid}: {st} needs decided_by (a human's initials)")
    if st == "pending":
        added = date.fromisoformat(e.get("added_at", "1900-01-01"))
        check((REF - added).days <= PENDING_MAX_DAYS, f"{pid}: pending for more than {PENDING_MAX_DAYS} days, a human must decide")
    entries[pid] = e

missing = listed - set(entries)
check(not missing, f"listed by the county but not in catalog.json: {sorted(missing)}")
for pid, e in entries.items():
    if pid not in listed:
        check(e["status"] == "removed", f"{pid}: no longer listed by the county, status must be 'removed'")
    elif e["status"] == "removed":
        check(False, f"{pid}: marked removed but still listed")

grant_pids = {}
for f in GRANTS.glob("*.md"):
    meta = parse_grant(f)[0]
    if domain(meta["url"]) == COUNTY:
        grant_pids[page_id(meta["url"])] = meta["id"]
for pid, e in entries.items():
    if e["status"] == "ingested":
        check(grant_pids.get(pid) == e.get("grant_id"), f"{pid}: ingested as {e.get('grant_id')!r} but no grant file with that id and page id")
for pid, gid in grant_pids.items():
    check(entries.get(pid, {}).get("status") == "ingested", f"grant file {gid} (page {pid}) is not marked ingested in catalog.json")

count = {s: sum(1 for e in entries.values() if e["status"] == s) for s in sorted(STATUSES)}
relevant = count["ingested"] + count["pending"]
print(f"coverage: {len(listed)} listed | {count['ingested']} ingested | {count['not_relevant']} not relevant | "
      f"{count['pending']} pending | ingested/relevant = {count['ingested']}/{relevant}")
print("PASS")
