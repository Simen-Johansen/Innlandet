"""Completeness checks A-D from docs/data-plan.md. Prints PASS or the failed checks; exit 0/1.

Reads only committed files: fixtures/sources.json, fixtures/geonorge_fylke34.json,
fixtures/discovery.json, fixtures/robots/, fixtures/grants/.
"""

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"
USER_AGENT = "innlandet-course-project (github.com/Simen-Johansen/Innlandet)"
MAX_AGE = timedelta(days=7)
EMAIL_ALLOW = {"postmottak", "post"}
PHONE = re.compile(
    r"(?<![\d.,])(?:\+47[\s-]?)?(?:\d{2}[\s-]?\d{2}[\s-]?\d{2}[\s-]?\d{2}|\d{3}[\s-]?\d{2}[\s-]?\d{3})(?![\d.,])"
)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
DOC_LINK = re.compile(
    r"\]\((\S+?(?:\.pdf|\.docx?|\.xlsx?|[Ff]ilnedlasting\.aspx\S*|dokumentnedlasting\.aspx\S*))\)"
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if not ok:
        failures.append(f"{name}: {detail}")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    sources = load(FIX / "sources.json")["sources"]
    geonorge = load(FIX / "geonorge_fylke34.json")
    discovery = load(FIX / "discovery.json")
    manifest = load(FIX / "grants" / "manifest.json")
    included = [s for s in sources if s["status"] == "included"]
    today = date.today()

    # A. Sources
    want = {k["kommunenummer"] for k in geonorge["kommuner"]}
    have = {s["nummer"] for s in sources if s["kind"] == "kommune"}
    check(
        "A1",
        want == have and len(want) == 46,
        f"missing {sorted(want - have)}, extra {sorted(have - want)}",
    )
    check(
        "A1", any(s["kind"] == "fylke" and s["nummer"] == "34" for s in sources), "county missing"
    )
    for s in sources:
        check("A2", s["status"] in {"included", "excluded"}, f"{s['id']} status {s['status']!r}")
        if s["status"] == "excluded":
            check("A2", bool(s.get("reason", "").strip()), f"{s['id']} excluded without reason")
    robots = {}
    for s in included:
        r = discovery["robots"].get(s["id"])
        path = FIX / "robots" / f"{s['id']}.txt"
        check("A3", r is not None and path.exists(), f"{s['id']} has no saved robots.txt")
        if r and path.exists():
            age = today - date.fromisoformat(r["fetched"])
            check("A3", age <= MAX_AGE, f"{s['id']} robots.txt is {age.days} days old")
            rp = RobotFileParser()
            rp.parse(path.read_text(encoding="utf-8").splitlines())
            robots[s["id"]] = rp

    # B. Discovery
    pages = discovery["county"]["index_pages"]
    check(
        "B1",
        len(pages) >= 2 and not pages[-1]["ids"] and all(p["ids"] for p in pages[:-1]),
        "county pagination did not end on exactly one empty page",
    )
    index_ids = {i for p in pages for i in p["ids"]}
    category_ids = {i for ids in discovery["county"]["categories"].values() for i in ids}
    check(
        "B2",
        index_ids == category_ids and index_ids,
        f"index-only {sorted(index_ids - category_ids)}, category-only {sorted(category_ids - index_ids)}",
    )
    grant_urls = {g["url"] for g in discovery["grants"]}
    county_grant_ids = {g["id"] for g in discovery["grants"] if g["source"] == "fylke-34"}
    check("B2", county_grant_ids == index_ids, "county grants in discovery differ from the index")
    for s in included:
        if s["kind"] != "kommune":
            continue
        k = discovery["kommuner"].get(s["id"])
        check("B3", k is not None, f"{s['id']} was not discovered")
        if k:
            excluded = {e["url"]: e["reason"] for e in k["excluded"]}
            for url in k["candidates"]:
                check(
                    "B3",
                    url in grant_urls or bool(excluded.get(url, "").strip()),
                    f"{url} neither collected nor excluded with a reason",
                )

    # C. Fetch
    by_url = {p["url"]: p for p in manifest["pages"]}
    for g in discovery["grants"]:
        p = by_url.get(g["url"])
        check("C1", p is not None, f"{g['url']} not in manifest")
        if p:
            check(
                "C1",
                p["status"] == 200 or bool(p.get("error")),
                f"{g['url']} status {p['status']} without error",
            )
            check("C1", bool(p.get("fetched")), f"{g['url']} has no fetch date")
    for p in manifest["pages"]:
        rp = robots.get(p["source"])
        check(
            "C2",
            rp is not None and rp.can_fetch(USER_AGENT, p["url"]),
            f"{p['url']} disallowed by robots.txt",
        )
    skipped = {d["url"] for d in manifest["skipped_documents"] if d.get("reason", "").strip()}

    # D. Clean
    for p in manifest["pages"]:
        if p["status"] != 200:
            continue
        path = FIX / "grants" / (p.get("file") or "")
        check("D1", bool(p.get("file")) and path.is_file(), f"{p['url']} has no Markdown file")
        if not (p.get("file") and path.is_file()):
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            check("D3", False, f"{p['file']} is not valid UTF-8")
            continue
        check("D1", len(text) > 200, f"{p['file']} is nearly empty")
        check(
            "D1",
            f"Source: {p['url']}" in text and "Fetched: " in text,
            f"{p['file']} lacks Source/Fetched header",
        )
        check(
            "D2", "tel:" not in text and "mailto:" not in text, f"{p['file']} contains tel:/mailto:"
        )
        for m in PHONE.finditer(text):
            check("D2", False, f"{p['file']} phone-like number {m.group(0)!r}")
        for m in EMAIL.finditer(text):
            check(
                "D2", m.group(0).split("@")[0].lower() in EMAIL_ALLOW, f"{p['file']} e-mail address"
            )
        check("D3", "�" not in text and "Ã" not in text, f"{p['file']} has mojibake")
        for m in DOC_LINK.finditer(text):
            check(
                "C3",
                m.group(1) in skipped,
                f"{p['file']} links {urlparse(m.group(1)).path} but it is not listed as skipped",
            )

    if failures:
        print(f"FAIL ({len(failures)})")
        print("\n".join(failures[:50]))
        return 1
    print(
        f"PASS: {len(sources)} sources, {len(discovery['grants'])} grant pages, "
        f"{sum(p['status'] == 200 for p in manifest['pages'])} cleaned"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FileNotFoundError as e:
        print(f"FAIL: missing {Path(e.filename).relative_to(ROOT)}")
        sys.exit(1)
