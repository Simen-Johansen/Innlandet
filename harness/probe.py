"""Probe one public source: fetch the NRK Innlandet RSS feed and write out/probe.json."""

import json
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

SOURCE_URL = "https://www.nrk.no/innlandet/toppsaker.rss"
USER_AGENT = "innlandet-kiua2003/0.1 (+https://github.com/Simen-Johansen/Innlandet)"
OUT_DIR = Path("out")
CACHE_MAX_AGE = 10 * 60  # seconds; reuse the cached feed without any request
TIMEOUT = 15


def fetch(url: str, cache_dir: Path) -> bytes:
    """Return the feed body, making at most one request and honouring the cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    body_path = cache_dir / "feed.xml"
    meta_path = cache_dir / "feed.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    if body_path.exists() and time.time() - body_path.stat().st_mtime < CACHE_MAX_AGE:
        print("cache hit (fresh), no request made", file=sys.stderr)
        return body_path.read_bytes()

    headers = {"User-Agent": USER_AGENT}
    if body_path.exists():
        if meta.get("etag"):
            headers["If-None-Match"] = meta["etag"]
        if meta.get("last_modified"):
            headers["If-Modified-Since"] = meta["last_modified"]

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read()
            meta = {
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            }
    except urllib.error.HTTPError as err:
        if err.code == 304 and body_path.exists():
            print("cache hit (304 Not Modified)", file=sys.stderr)
            body_path.touch()
            return body_path.read_bytes()
        raise

    body_path.write_bytes(body)
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    print(f"fetched {len(body)} bytes", file=sys.stderr)
    return body


def parse(xml_bytes: bytes) -> list[dict]:
    """Extract items with a title and an ISO 8601 date; skip incomplete ones."""
    items = []
    for item in ET.fromstring(xml_bytes).iter("item"):
        title = (item.findtext("title") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if not title or not pub_date:
            continue
        try:
            date = parsedate_to_datetime(pub_date).isoformat()
        except (TypeError, ValueError):
            continue
        items.append({"title": title, "date": date, "link": (item.findtext("link") or "").strip()})
    return items


def main() -> int:
    try:
        items = parse(fetch(SOURCE_URL, OUT_DIR / "cache"))
    except (urllib.error.URLError, ET.ParseError) as err:
        print(f"probe failed: {err}", file=sys.stderr)
        return 1
    if not items:
        print("probe failed: no items in feed", file=sys.stderr)
        return 1

    result = {
        "source_url": SOURCE_URL,
        "fetched_at": datetime.now(UTC).isoformat(),
        "items": items,
    }
    out_path = OUT_DIR / "probe.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(items)} items to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
