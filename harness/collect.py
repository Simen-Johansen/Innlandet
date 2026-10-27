"""Collect grant pages from the pilot sources (docs/data-plan.md steps 1-4).

Stages: robots -> discover -> fetch -> clean. Standard library only.
  uv run python harness/collect.py            live run (cached pages younger than 7 days are reused)
  uv run python harness/collect.py --offline  no network: cache only
  uv run python harness/collect.py --dry-run  print the stages and exit
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"
RAW = ROOT / "out" / "raw"
USER_AGENT = "innlandet-course-project (github.com/Simen-Johansen/Innlandet)"
DELAY_S = 2.0
CACHE_AGE = timedelta(days=7)
TODAY = date.today().isoformat()

COUNTY_INDEX = "https://innlandetfylke.no/tjenester/sok-tilskudd/"
COUNTY_GRANT = re.compile(r"/tjenester/sok-tilskudd/(?:[a-z0-9-]+/)?([a-z0-9-]+)\.(\d+)\.aspx")
COUNTY_CATEGORY = re.compile(
    r"https?://innlandetfylke\.no(?::443)?/tjenester/sok-tilskudd/([a-z0-9-]+)/"
)

# Kommune sitemap URLs: candidate -> grant, unless an exclusion matches (the reason is recorded).
CANDIDATE = re.compile(r"tilskud|tilskot|stotte|støtte|stonad|stønad|fond|midler|frivillig")
GRANT = re.compile(
    r"tilskud|tilskot|kulturmidler|stotteordning|støtteordning|fond(?:et)?\b|-midler"
)
EXCLUDE = [
    (re.compile(r"bostotte|bostøtte|bolig"), "housing allowance for individuals"),
    (
        re.compile(r"landbruk|jordbruk|beite|drenering|produksjonstilskudd"),
        "agriculture, not for clubs",
    ),
    (re.compile(r"barnehage"), "kindergarten funding"),
    (
        re.compile(r"helse|parorende|pårørende|hjelpemid|stottekontakt|omsorg"),
        "care for individuals",
    ),
    (re.compile(r"horing|høring"), "public hearing, not a grant"),
]

EMAIL_ALLOW = {"postmottak", "post"}
PHONE = re.compile(
    r"(?<![\d.,])(?:\+47[\s-]?)?(?:\d{2}[\s-]?\d{2}[\s-]?\d{2}[\s-]?\d{2}|\d{3}[\s-]?\d{2}[\s-]?\d{3})(?![\d.,])"
)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
DOCUMENT = re.compile(
    r"\.(?:pdf|docx?|xlsx?)(?:$|\?)|filnedlasting\.aspx|dokumentnedlasting\.aspx", re.IGNORECASE
)

_last_request = 0.0


# --- network and cache ---------------------------------------------------------------------------


def http_get(url: str, offline: bool) -> tuple[int, bytes, str]:
    """GET with our User-Agent and a pause between requests. Returns (status, body, error)."""
    global _last_request
    if offline:
        return 0, b"", "offline: not in cache"
    wait = DELAY_S - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read(), ""
    except urllib.error.HTTPError as e:
        return e.code, b"", f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, b"", f"network: {e}"


def cache_key(url: str) -> str:
    p = urlparse(url)
    key = re.sub(r"[^a-zA-Z0-9]+", "_", (p.path + "_" + p.query).strip("/")).strip("_")
    return key[:150] or "index"


def cached_get(source: str, url: str, offline: bool) -> dict:
    """Fetch through out/raw/<source>/. Reuses pages younger than CACHE_AGE."""
    folder = RAW / source
    meta_path = folder / f"{cache_key(url)}.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        fresh = date.today() - date.fromisoformat(meta["fetched"]) <= CACHE_AGE
        if (fresh or offline) and meta["status"] == 200:
            meta["body"] = (folder / f"{cache_key(url)}.html").read_bytes()
            return meta
    status, body, error = http_get(url, offline)
    meta = {"url": url, "status": status, "fetched": TODAY, "error": error}
    if status == 200:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{cache_key(url)}.html").write_bytes(body)
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
    meta["body"] = body
    return meta


# --- stage 1: robots -----------------------------------------------------------------------------


def stage_robots(sources: list[dict], discovery: dict, offline: bool) -> dict[str, RobotFileParser]:
    parsers = {}
    for s in sources:
        url = s["base_url"].rstrip("/") + "/robots.txt"
        r = cached_get(s["id"], url, offline)
        text = r["body"].decode("utf-8", errors="replace")
        (FIX / "robots").mkdir(parents=True, exist_ok=True)
        (FIX / "robots" / f"{s['id']}.txt").write_text(text, encoding="utf-8", newline="\n")
        discovery["robots"][s["id"]] = {"url": url, "fetched": r["fetched"], "status": r["status"]}
        rp = RobotFileParser()
        rp.parse(text.splitlines())
        parsers[s["id"]] = rp
        print(f"  robots {s['id']}: {r['status']}")
    return parsers


# --- stage 2: discover ---------------------------------------------------------------------------


def county_ids(html: str) -> dict[str, str]:
    """Grant id -> canonical URL for every grant link on a county list page."""
    return {gid: f"{COUNTY_INDEX}{slug}.{gid}.aspx" for slug, gid in COUNTY_GRANT.findall(html)}


def paginate(source: str, base: str, offline: bool) -> list[dict]:
    """Follow ?Side=1.. until a page lists no grants. Returns [{page, ids, urls}]."""
    pages = []
    for n in range(1, 51):
        html = cached_get(source, f"{base}?Side={n}", offline)["body"].decode("utf-8", "replace")
        found = county_ids(html)
        pages.append({"page": n, "ids": sorted(found), "urls": found})
        if not found:
            break
    return pages


def discover_county(s: dict, discovery: dict, offline: bool) -> list[dict]:
    pages = paginate(s["id"], COUNTY_INDEX, offline)
    first = cached_get(s["id"], f"{COUNTY_INDEX}?Side=1", offline)["body"].decode(
        "utf-8", "replace"
    )
    categories = {}
    for cat in sorted(set(COUNTY_CATEGORY.findall(first))):
        cat_pages = paginate(s["id"], f"{COUNTY_INDEX}{cat}/", offline)
        categories[cat] = sorted({i for p in cat_pages for i in p["ids"]})
    discovery["county"] = {
        "index_pages": [{"page": p["page"], "ids": p["ids"]} for p in pages],
        "categories": categories,
    }
    urls = {gid: url for p in pages for gid, url in p["urls"].items()}
    print(
        f"  {s['id']}: {len(urls)} grants on {len(pages)} index pages, {len(categories)} categories"
    )
    return [{"source": s["id"], "id": gid, "url": urls[gid]} for gid in sorted(urls)]


def sitemap_urls(source: str, url: str, offline: bool, depth: int = 0) -> list[str]:
    xml = cached_get(source, url, offline)["body"].decode("utf-8", "replace")
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    if "<sitemapindex" in xml and depth < 2:
        return [u for child in locs for u in sitemap_urls(source, child, offline, depth + 1)]
    return locs


def classify(url: str, rp: RobotFileParser, seen_slugs: dict[str, str]) -> str:
    """Empty string = collect it; otherwise the reason it is excluded."""
    path = urlparse(url).path.lower()
    if not rp.can_fetch(USER_AGENT, url):
        return "disallowed by robots.txt"
    for pattern, reason in EXCLUDE:
        if pattern.search(path):
            return reason
    if not GRANT.search(path):
        return "no grant keyword in the URL"
    slug = path.rstrip("/").rsplit("/", 1)[-1]
    if slug in seen_slugs:
        return f"duplicate of {seen_slugs[slug]}"
    seen_slugs[slug] = url
    return ""


def discover_kommune(s: dict, discovery: dict, rp: RobotFileParser, offline: bool) -> list[dict]:
    sitemap = s["base_url"].rstrip("/") + "/sitemap.xml"
    candidates = sorted(
        {u for u in sitemap_urls(s["id"], sitemap, offline) if CANDIDATE.search(u.lower())}
    )
    grants, excluded, seen = [], [], {}
    for url in candidates:
        reason = classify(url, rp, seen)
        if reason:
            excluded.append({"url": url, "reason": reason})
        else:
            slug = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
            grants.append({"source": s["id"], "id": slug, "url": url})
    discovery["kommuner"][s["id"]] = {
        "sitemap": sitemap,
        "candidates": candidates,
        "excluded": excluded,
    }
    print(f"  {s['id']}: {len(candidates)} candidates, {len(grants)} collected")
    return grants


# --- stage 4: clean ------------------------------------------------------------------------------

SKIP_TAGS = {
    "script",
    "style",
    "nav",
    "form",
    "button",
    "svg",
    "noscript",
    "iframe",
    "header",
    "footer",
}
SKIP_CLASS = re.compile(r"person|byline|linktoolbar|share|social|breadcrumb|cookie", re.IGNORECASE)
VOID = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "area", "col", "base"}
BLOCK = {"p", "div", "section", "article", "li", "tr", "table", "ul", "ol", "dl", "dt", "dd"}


class MarkdownExtractor(HTMLParser):
    """Text of <main> as simple Markdown, minus navigation, contact-person blocks and contact links."""

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.stack: list[tuple[str, bool]] = []  # (tag, skipped)
        self.in_main = 0
        self.out: list[str] = []
        self.link: tuple[str, list[str]] | None = None
        self.links: list[str] = []
        self.title = ""
        self._in_h1 = False

    @property
    def skipping(self) -> bool:
        return any(skipped for _, skipped in self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in VOID:
            if tag == "br" and self.in_main and not self.skipping:
                self.out.append("\n")
            return
        skip = tag in SKIP_TAGS or bool(SKIP_CLASS.search(a.get("class") or ""))
        self.stack.append((tag, skip))
        if tag == "main":
            self.in_main += 1
        if not self.in_main or self.skipping:
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
            self._in_h1 = tag == "h1"
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in BLOCK:
            self.out.append("\n\n")
        elif tag == "a":
            href = (a.get("href") or "").strip()
            self.link = (href, [])

    def handle_endtag(self, tag):
        if tag in VOID or not any(t == tag for t, _ in self.stack):
            return
        while self.stack:
            t, _ = self.stack.pop()
            if t == "main":
                self.in_main -= 1
            if t == tag:
                break
        if tag == "a" and self.link is not None:
            href, parts = self.link
            self.link = None
            text = " ".join("".join(parts).split())
            if href.lower().startswith(("mailto:", "tel:")) or not text:
                return  # contact links: drop the text too (it often names the person)
            if href and not href.startswith(("#", "javascript:")):
                url = urljoin(self.base_url, href)
                self.links.append(url)
                self.out.append(f"[{text}]({url})")
            else:
                self.out.append(text)
        elif re.fullmatch(r"h[1-6]", tag):
            self._in_h1 = False
            self.out.append("\n")

    def handle_data(self, data):
        if not self.in_main or self.skipping:
            return
        if self._in_h1 and not self.title:
            self.title = " ".join(data.split())
        if self.link is not None:
            self.link[1].append(data)
        else:
            self.out.append(data)


def sanitize(text: str) -> str:
    """Drop every line that holds a phone number or a personal e-mail address."""

    def personal(line: str) -> bool:
        if PHONE.search(line):
            return True
        return any(m.split("@")[0].lower() not in EMAIL_ALLOW for m in EMAIL.findall(line))

    return "\n".join(line for line in text.splitlines() if not personal(line))


def to_markdown(html: str, url: str, fetched: str) -> tuple[str, list[str]]:
    p = MarkdownExtractor(url)
    p.feed(html)
    lines = [" ".join(line.split()) for line in "".join(p.out).splitlines()]
    body, blank = [], True
    for line in lines:
        if line in ("", "-", "#"):
            if not blank:
                body.append("")
            blank = True
        else:
            body.append(line)
            blank = False
    text = sanitize("\n".join(body).strip())
    header = f"# {p.title or url}\n\nSource: {url}\nFetched: {fetched}\n\n"
    return header + text + "\n", p.links


# --- main ----------------------------------------------------------------------------------------

STAGES = [
    ("robots", "base_url/robots.txt", "fixtures/robots/<source>.txt", "eval/check_data.py A3, C2"),
    ("discover", "county index + categories, kommune sitemaps", "fixtures/discovery.json", "B1-B3"),
    ("fetch", "discovered grant URLs", "out/raw/<source>/ (not in git)", "C1"),
    ("clean", "out/raw/", "fixtures/grants/<source>-<id>.md + manifest.json", "C3, D1-D3"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="no network; use out/raw/ only")
    ap.add_argument("--dry-run", action="store_true", help="print the stages and exit")
    args = ap.parse_args()

    sources = [
        s
        for s in json.loads((FIX / "sources.json").read_text(encoding="utf-8"))["sources"]
        if s["status"] == "included"
    ]
    if args.dry_run:
        print(f"sources: {', '.join(s['id'] for s in sources)}")
        for i, (name, src, dst, check) in enumerate(STAGES, 1):
            print(f"[{i}] {name:9} {src} -> {dst}   check: {check}")
        print("then: uv run python eval/check_data.py")
        return 0

    started = datetime.now()
    discovery = {"run_date": TODAY, "robots": {}, "county": {}, "kommuner": {}, "grants": []}
    print("[1] robots")
    robots = stage_robots(sources, discovery, args.offline)
    print("[2] discover")
    for s in sources:
        if s["discovery"] == "county-index":
            discovery["grants"] += discover_county(s, discovery, args.offline)
        else:
            discovery["grants"] += discover_kommune(s, discovery, robots[s["id"]], args.offline)
    FIX.joinpath("discovery.json").write_text(
        json.dumps(discovery, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )

    print(f"[3] fetch + [4] clean: {len(discovery['grants'])} pages")
    grants_dir = FIX / "grants"
    grants_dir.mkdir(parents=True, exist_ok=True)
    for old in grants_dir.glob("*.md"):
        old.unlink()  # a page that disappeared from the source must not linger
    manifest = {"pages": [], "skipped_documents": []}
    skipped = {}
    for g in discovery["grants"]:
        r = cached_get(g["source"], g["url"], args.offline)
        entry = {
            **g,
            "status": r["status"],
            "fetched": r["fetched"],
            "file": None,
            "error": r["error"],
        }
        if r["status"] == 200:
            md, links = to_markdown(r["body"].decode("utf-8", "replace"), g["url"], r["fetched"])
            entry["file"] = f"{g['source']}-{g['id']}.md"
            (grants_dir / entry["file"]).write_text(md, encoding="utf-8", newline="\n")
            for link in links:
                if DOCUMENT.search(link) and link not in skipped:
                    src = next((s["id"] for s in sources if link.startswith(s["base_url"])), None)
                    allowed = src is None or robots[src].can_fetch(USER_AGENT, link)
                    reason = (
                        "documents not fetched yet (later task)"
                        if allowed
                        else "disallowed by robots.txt"
                    )
                    skipped[link] = {"url": link, "found_in": entry["file"], "reason": reason}
        manifest["pages"].append(entry)
    manifest["skipped_documents"] = sorted(skipped.values(), key=lambda d: d["url"])
    (grants_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    ok = sum(p["status"] == 200 for p in manifest["pages"])
    print(
        f"done in {(datetime.now() - started).seconds} s: {ok}/{len(manifest['pages'])} pages cleaned, "
        f"{len(skipped)} linked documents listed"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
