from urllib.robotparser import RobotFileParser

from harness.collect import classify, county_ids, to_markdown

PAGE = """<html><body><nav>Meny</nav><main>
<h1>Tilskudd til friluftsliv</h1>
<p>Lag og foreninger kan s&oslash;ke. S&oslash;knadsfrist er 15. mai 2026.</p>
<p>Les <a href="/kunde/filer/retningslinjer.pdf">retningslinjene</a> og
<a href="https://www.regionalforvaltning.no/x">s&oslash;k her</a>.</p>
<p>Ring saksbehandler på 99 88 77 66 for spørsmål.</p>
<p>Skriv til postmottak@innlandetfylke.no.</p>
<div class="emnekart-webpart--person type-person"><h2>Kontakt</h2>
<div class="person-name">Kari Eksempel</div>
<a href="mailto:kari@innlandetfylke.no">Send e-post til Kari Eksempel</a></div>
<a href="tel:+4799887766">Ring oss</a>
</main><footer>Bunntekst</footer></body></html>"""


def test_markdown_keeps_rules_and_links():
    md, links = to_markdown(PAGE, "https://innlandetfylke.no/a/b.1.aspx", "2026-10-27")
    assert md.startswith("# Tilskudd til friluftsliv\n")
    assert "Source: https://innlandetfylke.no/a/b.1.aspx\nFetched: 2026-10-27" in md
    assert "Søknadsfrist er 15. mai 2026." in md
    assert "[søk her](https://www.regionalforvaltning.no/x)" in md
    assert "https://innlandetfylke.no/kunde/filer/retningslinjer.pdf" in links
    assert "postmottak@innlandetfylke.no" in md
    assert "Meny" not in md and "Bunntekst" not in md


def test_markdown_removes_personal_data():
    md, _ = to_markdown(PAGE, "https://innlandetfylke.no/a/b.1.aspx", "2026-10-27")
    assert "Kari" not in md
    assert "99 88 77 66" not in md and "tel:" not in md and "mailto:" not in md
    assert "Ring oss" not in md


def test_markdown_removes_names_in_body_text():
    page = (
        "<main><h1>Tilskudd</h1><p>Lag kan søke innen 1. mars.</p>"
        "<h2>Kontaktperson</h2><p>Kari Nordmann, seniorrådgiver</p><p>Ring oss gjerne.</p>"
        "<h2>Hvem kan søke?</h2><p>Kontakt rådgiver Ola Nordmann for hjelp.</p>"
        "<p>Søknaden sendes til fylkeskommunens saksbehandler.</p></main>"
    )
    md, _ = to_markdown(page, "https://innlandetfylke.no/t.1.aspx", "2026-10-27")
    assert "Nordmann" not in md and "Ring oss gjerne" not in md
    assert "## Hvem kan søke?" in md and "Lag kan søke innen 1. mars." in md
    assert "fylkeskommunens saksbehandler" in md  # a role without a name stays


def test_markdown_reads_main_inside_form_and_header():
    page = (
        "<html><body><form><main><article><header><h1>Spillemidler</h1></header>"
        "<p>Frist 2026-10-27 og 15. oktober.</p></article></main></form></body></html>"
    )
    md, _ = to_markdown(page, "https://innlandetfylke.no/s.18103.aspx", "2026-10-27")
    assert md.startswith("# Spillemidler\n")
    assert "Frist 2026-10-27 og 15. oktober." in md  # a date is not a phone number


def test_county_ids_dedupes_category_paths():
    html = (
        '<a href="/tjenester/sok-tilskudd/spillemidler.18103.aspx">'
        '<a href="/tjenester/sok-tilskudd/frivilligheten/spillemidler.18103.aspx">'
    )
    assert county_ids(html) == {
        "18103": "https://innlandetfylke.no/tjenester/sok-tilskudd/spillemidler.18103.aspx"
    }


def test_classify_kommune_urls():
    rp = RobotFileParser()
    rp.parse(["User-agent: *", "Disallow: /sok/"])
    seen: dict[str, str] = {}
    base = "https://www.hamar.kommune.no"
    assert classify(f"{base}/nyhetsarkiv/tilskudd-til-inkludering", rp, seen) == ""
    assert classify(f"{base}/politikk/tilskudd-til-inkludering", rp, seen).startswith("duplicate")
    assert (
        classify(f"{base}/landbruk/tilskudd-og-erstatninger/", rp, seen)
        == "agriculture, not for clubs"
    )
    assert classify(f"{base}/kultur-og-frivillighet/", rp, seen) == "no grant keyword in the URL"
    assert classify(f"{base}/sok/tilskudd", rp, seen) == "disallowed by robots.txt"
    assert classify(f"{base}/nyheter/midlertidig-skole", rp, seen) == "no grant keyword in the URL"
    assert classify(f"{base}/tilskudd-og-priser/spillemidler/", rp, seen) == ""
    assert classify(f"{base}/tilskudd-og-priser/kulturpris/", rp, seen, from_hub=True) == ""
