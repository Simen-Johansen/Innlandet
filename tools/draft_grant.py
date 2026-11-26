"""Draft one county grant file for human review (task 017, the minimal task 016).

  python tools/draft_grant.py <page_id> [--id GRANT_ID] [--offline --pages-dir D] [--out-dir O] [--today YYYY-MM-DD]

Reads the page URL from context/catalog.json and the User-Agent from context/sources.json, fetches the page
(policy must be auto) or reads <pages-dir>/<grant id>.html offline, and writes
  <out-dir>/<id>.md            frontmatter (code fills id, title, url, provider, fetched_at, source_modified;
                               every fact is TODO) + the body under the five headings, verbatim
  <out-dir>/<id>.checklist.md  every page heading, every amount and date on the page, the fields a human fills,
                               and the sentence around each deadline (which project period it covers)
Default out-dir: docs/grant-expansion/grants/. A live fetch also saves the sanitized, redacted page as
fixtures/pages_raw/<id>.html (gitignored), so `update_grants.py --audit --offline` can re-read it.
Never writes into context/ or eval/. Reuses the parsing of harness/update_grants.py (import, not copy).
Standard library only.
"""
import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

from update_grants import (  # noqa: E402
    EMAIL, HEADINGS, PHONE, REDACTED, SIST_ENDRET, checklist_md, domain, extract, fact_audit, fetch, norm,
    page_dates, page_text, redact, render, sanitize,
)

CATALOG = ROOT / "context" / "catalog.json"
SOURCES = ROOT / "context" / "sources.json"
OUT_DIR = ROOT / "docs" / "grant-expansion" / "grants"
PAGES_RAW = ROOT / "fixtures" / "pages_raw"
FORBIDDEN = (ROOT / "context", ROOT / "eval")
PROVIDER = {"innlandetfylke.no": "innlandet_fylkeskommune"}
HUMAN_FACTS = ("applicant_orgforms", "requires_frivillighetsregisteret", "region_prefix", "target_group",
               "max_amount_nok", "deadlines")
# Any amount, with or without "inntil"/"maks" in front (the audit's AMOUNT_MAX misses "fra 20 000 til 300 000").
AMOUNT_ANY = re.compile(r"\d{1,3}(?:[\s.]\d{3})+\s*(?:kr\b|kroner|,-)|\d+\s*(?:kr\b|kroner|,-)"
                        r"|\d+(?:,\d+)?\s*million(?:er)?(?:\s*kroner)?", re.I)
TEL_HREF = re.compile(r'href="tel:[^"]*"', re.I)
MAIL_HREF = re.compile(r'href="mailto:[^"?][^"]*"', re.I)  # keeps the share link "mailto:?subject=..."

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def slug(title):
    t = title.lower().replace("æ", "ae").replace("ø", "o").replace("å", "a")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def catalog_entry(page_id, catalog_path=CATALOG):
    data = load_json(catalog_path)
    items = data if isinstance(data, list) else next(v for v in data.values() if isinstance(v, list))
    for e in items:
        if str(e.get("page_id")) == str(page_id):
            return e
    raise SystemExit(f"page_id {page_id} not in {catalog_path.name}")


def inside(path, dirs):
    p = Path(path).resolve()
    return any(p == d.resolve() or d.resolve() in p.parents for d in dirs)


def safe_page(raw):
    """Sanitized page for fixtures/pages_raw: no author meta, no aside (the Kontakt block), no e-mail, no phone."""
    page = TEL_HREF.sub('href="#"', MAIL_HREF.sub('href="#"', sanitize(raw)))
    return PHONE.sub(REDACTED, EMAIL.sub(REDACTED, page))


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[^\d\s][.!?])\s+(?=[A-ZÆØÅ])", text) if s.strip()]


def frontmatter(gid, title, url, provider, today, source_modified):
    lines = ["---", f"id: {gid}", f"title: {title}  # TODO human: confirm against the page h1", f"url: {url}",
             f"provider: {provider}"]
    lines += [f"{k}: TODO" for k in HUMAN_FACTS]
    lines += [f"fetched_at: {today}", "checked_at: TODO", f"source_modified: {source_modified}",
              "verified_by: TODO", "---"]
    return "\n".join(lines) + "\n"


def extra_checklist(found, problem, all_text):
    """all_text: the page's sentences, one paragraph or list item at a time."""
    L = ["", "## Draft status"]
    if problem:
        kind = "TEMPLATE FAILURE (weekly update would fail: fix the heading map first)" if problem[0] else "note"
        L.append(f"- [ ] {kind}: {problem[1]}")
    else:
        L.append("- every page heading is mapped, merged or deliberately ignored")
    L += ["", "## Every amount on the page (code found, a human picks max_amount_nok)"]
    hits = list(dict.fromkeys((m.group(0), s) for s in all_text for m in AMOUNT_ANY.finditer(s)))
    L += [f"- [ ] \"{norm(a)}\" in: {s}" for a, s in hits] or ["- (no amount found)"]
    L += ["", "## Every date on the page, with its sentence (deadline -> which project period?)"]
    rows = list(dict.fromkeys((w, iso, s) for s in all_text for w, iso in page_dates(s)))
    L += [f"- [ ] {w} ({iso}): {s}" for w, iso, s in rows] or ["- (no date found)"]
    L += ["", "## Rules the filter cannot express (fill by hand; only the matcher can apply them)",
          "- [ ] date gap: does a deadline cover a project/event period? which?",
          "- [ ] affiliation / membership rules (NIF, umbrella body, county level, ...):",
          "- [ ] size / reach rules (participants, national, regional, local):",
          "- [ ] exclusions that hit another grant's field (e.g. 'not mainly sport'):",
          "- [ ] minimum amount, co-funding share, multi-year rules:",
          "", "Text merged from extra headings (read these first for the rules above):"]
    for h in HEADINGS:
        L += [f"- {h}: ### {t}" for k, t in found.get(h, []) if k == "h3"]
    return "\n".join(L) + "\n"


def draft(page_id, gid=None, offline=False, pages_dir=None, out_dir=OUT_DIR, today=None,
          catalog_path=CATALOG, sources_path=SOURCES, save_raw_dir=PAGES_RAW):
    out_dir = Path(out_dir)
    if inside(out_dir, FORBIDDEN) or (save_raw_dir and inside(save_raw_dir, FORBIDDEN)):
        raise SystemExit("refused: drafts never go into context/ or eval/ (humans copy them)")
    entry = catalog_entry(page_id, Path(catalog_path))
    url, title = entry["url"], entry["title"]
    gid = gid or slug(title)
    src = load_json(sources_path)
    policy = {s["domain"]: s["policy"] for s in src["sources"]}.get(domain(url), "manual")
    if not offline and policy != "auto":
        raise SystemExit(f"refused: {domain(url)} is {policy}; read the page by hand")
    raw = fetch(url, src["user_agent"], gid, pages_dir if offline else None)
    page = safe_page(raw)
    found, problem, heads = extract(page)
    body, hits = redact(render(found))
    m = SIST_ENDRET.search(page_text(page))
    sist = f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}:{m.group(5)}" if m else "unknown"
    today = today or date.today().isoformat()
    meta_text = frontmatter(gid, title, url, PROVIDER.get(domain(url), "TODO"), today, sist)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"{gid}.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(meta_text + body)
    meta = {"url": url, "max_amount_nok": "TODO", "deadlines": "", **{k: "TODO" for k in HUMAN_FACTS[:4]},
            "provider": PROVIDER.get(domain(url), "TODO"), "verified_by": "TODO"}
    all_text = [s for h in HEADINGS for k, t in found.get(h, []) if k != "h3" for s in sentences(t)]
    check = checklist_md(gid, meta, heads, fact_audit(meta, found), m.group(0) if m else None)
    check += extra_checklist(found, problem, all_text)
    if hits:
        check += f"\n{hits} e-mail/phone pattern(s) redacted as {REDACTED}: check they were not amounts.\n"
    with open(out_dir / f"{gid}.checklist.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(check)
    if not offline and save_raw_dir:
        Path(save_raw_dir).mkdir(parents=True, exist_ok=True)
        with open(Path(save_raw_dir) / f"{gid}.html", "w", encoding="utf-8", newline="\n") as f:
            f.write(page)
    return gid, problem, hits


def main(argv=None):
    ap = argparse.ArgumentParser(description="Draft one county grant file for human review (task 017)")
    ap.add_argument("page_id")
    ap.add_argument("--id", dest="gid", help="grant id (default: slug of the catalog title)")
    ap.add_argument("--offline", action="store_true", help="read <pages-dir>/<id>.html, no request")
    ap.add_argument("--pages-dir", default=str(PAGES_RAW))
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--today")
    a = ap.parse_args(argv)
    gid, problem, hits = draft(a.page_id, a.gid, a.offline, Path(a.pages_dir), Path(a.out_dir), a.today)
    rel = Path(a.out_dir).resolve()
    rel = rel.relative_to(ROOT) if ROOT in rel.parents else rel
    print(f"wrote {rel / (gid + '.md')} and {gid}.checklist.md"
          f"{'; ' + problem[1] if problem else ''}{f'; {hits} redacted' if hits else ''}")
    return 2 if problem and problem[0] else 0


if __name__ == "__main__":
    sys.exit(main())
