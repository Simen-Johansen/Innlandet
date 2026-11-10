"""County grant catalog (task 010): which grants does innlandetfylke.no list, and what did a human decide?

Usage: python harness/catalog.py [--offline]

Online: fetches every page of the county's listing (/tjenester/sok-tilskudd?Side=N), one request per
page, one at a time, with the User-Agent from context/sources.json, and saves them raw as
fixtures/fylke_index/side-N.html. Offline: reads only the saved pages.
Both then update context/catalog.json, keyed on the numeric page id (".../slug.36453.aspx"), because
the same grant can be listed under two paths:
  new listing -> pending, listing gone -> removed, removed but listed again -> pending.
This script never sets ingested or not_relevant; only a human does. Standard library only.
"""

import argparse
import html
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "context" / "sources.json"
CATALOG = ROOT / "context" / "catalog.json"
INDEX_DIR = ROOT / "fixtures" / "fylke_index"
COUNTY = "innlandetfylke.no"
INDEX_URL = f"https://{COUNTY}/tjenester/sok-tilskudd?Side={{n}}"
TIMEOUT_S = 10
MAX_PAGES = 20  # a guard against a broken pager, not an expected size (~4)

LINK = re.compile(r'<a\b[^>]*?href="([^"]*/tjenester/sok-tilskudd/[^"]*?\.(\d+)\.aspx)"[^>]*>(.*?)</a>', re.S | re.I)
SIDE = re.compile(r"[?&]Side=(\d+)")
AUTHOR_META = re.compile(r'<meta\s+name="author"[^>]*>\s*', re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b")
ORG_EMAILS = {"post@innlandetfylke.no"}  # the county's shared post box in the page footer, not a person

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def get(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return r.read().decode("utf-8", errors="replace")


def last_page(text):
    return max([int(n) for n in SIDE.findall(html.unescape(text))] or [1])


def fetch_index():
    """Fetch side-1..side-N sequentially and save them. Returns the number of pages."""
    cfg = json.loads(SOURCES.read_text(encoding="utf-8"))
    src = next((s for s in cfg["sources"] if s["domain"] == COUNTY), None)
    if not src or src.get("policy") != "auto":
        sys.exit(f"{COUNTY} is not policy 'auto' in context/sources.json; not fetching")
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    n, pages = 1, 1
    while n <= pages:
        text = AUTHOR_META.sub("", get(INDEX_URL.format(n=n), cfg["user_agent"]))
        (INDEX_DIR / f"side-{n}.html").write_text(text, encoding="utf-8")
        pages = min(max(pages, last_page(text)), MAX_PAGES)
        n += 1
    for old in INDEX_DIR.glob("side-*.html"):
        if int(old.stem.split("-")[1]) > pages:
            old.unlink()
    return pages


def listed_grants():
    """{page_id: (url, title)} from the saved index pages; first link per id wins."""
    pages = sorted(INDEX_DIR.glob("side-*.html"), key=lambda p: int(p.stem.split("-")[1]))
    if not pages:
        sys.exit("no saved index pages in fixtures/fylke_index/; run without --offline first")
    found = {}
    for p in pages:
        text = p.read_text(encoding="utf-8")
        if set(EMAIL.findall(text)) - ORG_EMAILS:
            print(f"warning: {p.relative_to(ROOT)} contains an e-mail address; check it before committing")
        for href, pid, inner in LINK.findall(text):
            url = html.unescape(href)
            if url.startswith("/"):
                url = f"https://{COUNTY}{url}"
            title = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", inner)).split())
            if pid not in found or (title and not found[pid][1]):
                found[pid] = (url, title)
    return found, len(pages)


def update_catalog(listed, today, checked_today):
    if CATALOG.exists():
        cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    elif checked_today:
        cat = {"index_checked_at": today, "entries": []}
    else:
        sys.exit("context/catalog.json does not exist; run without --offline first")
    if checked_today:
        cat["index_checked_at"] = today
    entries = {str(e["page_id"]): e for e in cat.get("entries", [])}
    new, removed, relisted = [], [], []
    for pid, (url, title) in listed.items():
        e = entries.get(pid)
        if e is None:
            entries[pid] = {"page_id": pid, "url": url, "title": title, "status": "pending", "added_at": today}
            new.append(pid)
            continue
        e["url"], e["title"] = url, title or e.get("title", "")
        if e["status"] == "removed":
            e["status"], e["added_at"] = "pending", today
            relisted.append(pid)
    for pid, e in entries.items():
        if pid not in listed and e["status"] != "removed":
            e["status"] = "removed"
            removed.append(pid)
    cat["entries"] = [entries[pid] for pid in sorted(entries, key=int)]
    CATALOG.write_text(json.dumps(cat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return cat, new, removed, relisted


def main():
    ap = argparse.ArgumentParser(description="Update context/catalog.json from the county's grant listing.")
    ap.add_argument("--offline", action="store_true", help="use the saved fixtures/fylke_index/ pages only")
    args = ap.parse_args()
    today = date.today().isoformat()
    if not args.offline:
        print(f"fetched {fetch_index()} index pages from {COUNTY}")
    listed, n_pages = listed_grants()
    cat, new, removed, relisted = update_catalog(listed, today, checked_today=not args.offline)
    pending = [e for e in cat["entries"] if e["status"] == "pending"]
    print(f"{n_pages} pages | {len(listed)} listed | {len(new)} new | {len(removed)} removed | "
          f"{len(relisted)} listed again | index checked {cat['index_checked_at']}")
    if pending:
        print(f"\n{len(pending)} pending, a human must decide (ingested or not_relevant + reason):")
        for e in pending:
            print(f"  {e['page_id']:>6}  {e['title']}")


if __name__ == "__main__":
    main()
