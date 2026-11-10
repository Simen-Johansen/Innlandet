"""Human tool: build fixtures/update_cases/ for task 015 (never touches expected.json).

  python tools/save_sources.py page tilskudd_til_friluftslivsaktivitet      (first, saves the live page)
  python tools/make_update_cases.py --real-name "First Last" [--real-name "Other Name" ...]

--real-name: every person named on the saved page (the contact block and the page author). Read the
page and pass each name; they are replaced by the fictional "Kari Testesen" and the script stops if
any is left. E-mail addresses and phone links are replaced too. Only the anonymised copy is written
into fixtures/update_cases/; the raw page in fixtures/pages_raw/ must not be committed.

Builds 8 cases (see fixtures/update_cases/FORMAT.md). Standard library only.
"""
import argparse
import html
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "fixtures" / "update_cases"
GRANTS = ROOT / "context" / "grants"
REAL_ID = "tilskudd_til_friluftslivsaktivitet"
MANUAL_ID = "hamar_driftstilskudd_frivillige_organisasjoner"
SYN_ID = "syn_friluftsaktivitet"
FAKE_NAME, FAKE_MAIL, FAKE_TEL, FAKE_TEL_TEXT = "Kari Testesen", "kari.testesen@example.no", "+4791234567", "91 23 45 67"
OLD = "2020-01-01T00:00"  # older than any real "Sist endret"
SIST = re.compile(r"Sist endret\s+(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2})[.:](\d{2})")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def text_of(raw):
    raw = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())


def anonymise(raw, names):
    for n in names:
        raw = raw.replace(n, FAKE_NAME).replace(html.escape(n), FAKE_NAME)
    raw = re.sub(r'(<meta[^>]+name="author"[^>]+content=")[^"]*(")', rf"\g<1>{FAKE_NAME}\g<2>", raw, flags=re.I)
    raw = re.sub(r'(<a[^>]*href=")tel:[^"]*("[^>]*>).*?(</a>)', rf"\g<1>tel:{FAKE_TEL}\g<2>{FAKE_TEL_TEXT}\g<3>", raw, flags=re.S | re.I)
    raw = re.sub(r"mailto:[^\"'>\s]+", f"mailto:{FAKE_MAIL}", raw)
    raw = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", FAKE_MAIL, raw)
    left = [n for n in names if n.lower() in raw.lower() or n.lower() in text_of(raw).lower()]
    if left:
        sys.exit(f"STOP: still on the page after anonymising: {left}. Edit by hand.")
    return raw


def set_key(text, key, value):
    new, n = re.subn(rf"^{key}:.*$", f"{key}: {value}", text, count=1, flags=re.M)
    if not n:
        sys.exit(f"STOP: no '{key}:' line in a grant file. Add checked_at and source_modified first.")
    return new


def write_case(name, grants, pages):
    d = CASES / name
    for sub in ("grants", "pages"):
        shutil.rmtree(d / sub, ignore_errors=True)
        (d / sub).mkdir(parents=True)
    for gid, text in grants.items():
        (d / "grants" / f"{gid}.md").write_text(text, encoding="utf-8")
    for gid, raw in pages.items():
        (d / "pages" / f"{gid}.html").write_text(raw, encoding="utf-8")
    note = "" if (d / "expected.json").exists() else "   <- expected.json MISSING, write it"
    print(f"  {name}{note}")


SYN_GRANT = """---
id: syn_friluftsaktivitet
title: Testtilskudd til friluftsaktivitet
url: https://innlandetfylke.no/tjenester/sok-tilskudd/test/testtilskudd-til-friluftsaktivitet.99001.aspx
provider: test_synthetic
applicant_orgforms: FLI
requires_frivillighetsregisteret: false
region_prefix: 34
target_group: alle
max_amount_nok: unknown
deadlines: 2026-12-01
fetched_at: 2026-10-20
checked_at: 2026-10-29
source_modified: 2026-10-15T09:37
verified_by: TEST
---

## Formål

{formal}

## Hvem kan søke

En frivillig medlemsorganisasjon som er registrert i Enhetsregisteret.

## Hva kan det søkes om

Organiserte friluftslivsaktiviteter for barn og unge.

## Vedlegg

Du søker via elektronisk skjema.

## Frister og rapportering

{frist}
"""

SYN_PAGE = """<!DOCTYPE html>
<html lang="nb"><head><meta charset="utf-8"><meta name="author" content="Kari Testesen">
<title>Testtilskudd til friluftsaktivitet - Innlandet fylkeskommune</title></head>
<body><main>
<h1>Testtilskudd til friluftsaktivitet</h1>
<h2>Formål</h2>
<p>{formal}</p>
<h2>Hvem kan søke</h2>
<p>En frivillig medlemsorganisasjon som er registrert i Enhetsregisteret.</p>
<h2>Hva kan det søkes om</h2>
<p>Organiserte friluftslivsaktiviteter for barn og unge.</p>
<h2>Vedlegg</h2>
<p>Du søker via elektronisk skjema.</p>
<h2>Frister og rapportering</h2>
<p>{frist}</p>
<p>Sist endret {sist}</p>
<h2>Kontakt</h2>
<p>Kari Testesen</p><p>Seniorrådgiver</p>
<p>E-post <a href="mailto:kari.testesen@example.no">Send e-post til Kari Testesen</a></p>
<p>Mobil <a href="tel:+4791234567">91 23 45 67</a></p>
</main></body></html>
"""
F1 = "Tilskuddsordningen skal bidra til økt deltakelse i friluftsliv for alle grupper i befolkningen."
F2 = "Tilskuddsordningen skal bidra til at flere grupper i befolkningen deltar i friluftsliv."
D1 = "Søknadsfrist: 1. desember."
D2 = "Søknadsfrist: 15. november."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real-name", action="append", default=[], help="a person named on the saved page")
    args = ap.parse_args()
    raw_path = ROOT / "fixtures" / "pages_raw" / f"{REAL_ID}.html"
    if not raw_path.exists():
        sys.exit(f"STOP: {raw_path.relative_to(ROOT)} missing. Run: python tools/save_sources.py page {REAL_ID}")
    if not args.real_name:
        sys.exit("STOP: pass --real-name for every person named on the page (read the page first)")
    raw = anonymise(raw_path.read_text(encoding="utf-8", errors="replace"), args.real_name)
    m = SIST.search(text_of(raw))
    if not m:
        sys.exit("STOP: no 'Sist endret dd.mm.yyyy hh.mm' found on the saved page")
    sist = f"{m[3]}-{m[2]}-{m[1]}T{m[4]}:{m[5]}"
    broken = re.sub(r"Sist endret(?:\s|&nbsp;|<[^>]+>)*\d{2}\.\d{2}\.\d{4}(?:\s|&nbsp;|<[^>]+>)*\d{2}[.:]\d{2}", "", raw)
    if SIST.search(text_of(broken)):
        sys.exit("STOP: could not remove 'Sist endret' automatically; make the template_changed page by hand")

    real = (GRANTS / f"{REAL_ID}.md").read_text(encoding="utf-8")
    manual = (GRANTS / f"{MANUAL_ID}.md").read_text(encoding="utf-8")
    print(f"page 'Sist endret' = {sist}; writing cases:")
    write_case("real_unchanged", {REAL_ID: set_key(real, "source_modified", sist)}, {REAL_ID: raw})
    write_case("real_first_run", {REAL_ID: set_key(real, "source_modified", OLD)}, {REAL_ID: raw})
    write_case("real_template_changed", {REAL_ID: set_key(real, "source_modified", OLD)}, {REAL_ID: broken})
    write_case("page_unreachable", {REAL_ID: set_key(real, "source_modified", OLD)}, {})
    write_case("manual_domain", {MANUAL_ID: manual}, {})
    g = SYN_GRANT.format(formal=F1, frist=D1)
    write_case("syn_touched", {SYN_ID: g}, {SYN_ID: SYN_PAGE.format(formal=F1, frist=D1, sist="01.11.2026 10.00")})
    write_case("syn_wording", {SYN_ID: g}, {SYN_ID: SYN_PAGE.format(formal=F2, frist=D1, sist="02.11.2026 08.15")})
    write_case("syn_deadline", {SYN_ID: g}, {SYN_ID: SYN_PAGE.format(formal=F1, frist=D2, sist="03.11.2026 12.00")})
    print("Done. Read each expected.json, then commit fixtures/update_cases/ (not fixtures/pages_raw/).")


if __name__ == "__main__":
    main()
