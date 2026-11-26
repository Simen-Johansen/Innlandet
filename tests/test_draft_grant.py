"""tools/draft_grant.py on a synthetic saved page (task 017): privacy and the no-context/ rule."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import draft_grant  # noqa: E402

FAKE_NAME, FAKE_MAIL, FAKE_TEL = "Kari Testesen", "kari.testesen@example.no", "91 23 45 67"
PAGE = f"""<html><head><meta name="author" content="{FAKE_NAME}"><title>t</title></head><body><main><article>
<h1>Syntetisk tilskudd</h1>
<h2>Formålet med ordningen</h2><p>Stimulere til arrangementer i Innlandet.</p>
<h2>Hvem kan søke?</h2><p>Frivillige lag og foreninger.</p>
<h2>Avgrensing</h2><ul><li>Maksimal bevilgning er 1 million kroner.</li><li>Inntil 50 000 kroner per år.</li></ul>
<h2>Søknadsfrist</h2><p>Søknadsfristen er 1. februar 2027 for arrangementer påfølgende sommer.</p>
<p>Ring {FAKE_TEL} eller skriv til {FAKE_MAIL}.</p>
<div class="byline"><span>Sist endret</span> <span>05.11.2026 14.36</span></div>
</article></main><aside><h2>Kontakt</h2><p>{FAKE_NAME}</p><a href="tel:{FAKE_TEL}">{FAKE_TEL}</a>
<a href="mailto:{FAKE_MAIL}">{FAKE_MAIL}</a></aside></body></html>"""


@pytest.fixture
def setup(tmp_path):
    cat = tmp_path / "catalog.json"
    cat.write_text(json.dumps({"grants": [{"page_id": "99999", "title": "Syntetisk tilskudd",
                                           "url": "https://innlandetfylke.no/x.99999.aspx"}]}), encoding="utf-8")
    src = tmp_path / "sources.json"
    src.write_text(json.dumps({"user_agent": "test", "sources": [
        {"domain": "innlandetfylke.no", "policy": "auto"}]}), encoding="utf-8")
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "syn.html").write_text(PAGE, encoding="utf-8")
    return tmp_path, cat, src, pages


def test_draft_has_no_personal_data_and_facts_are_todo(setup):
    tmp, cat, src, pages = setup
    out = tmp / "drafts"
    gid, problem, hits = draft_grant.draft("99999", "syn", offline=True, pages_dir=pages, out_dir=out,
                                           today="2026-11-26", catalog_path=cat, sources_path=src,
                                           save_raw_dir=None)
    assert gid == "syn" and not problem[0]  # only "no page section for: Vedlegg", not a template failure
    text = (out / "syn.md").read_text(encoding="utf-8")
    check = (out / "syn.checklist.md").read_text(encoding="utf-8")
    for leak in (FAKE_NAME, FAKE_MAIL, FAKE_TEL, "Kontakt"):
        assert leak not in text and leak not in check
    assert f"Ring {draft_grant.REDACTED} eller skriv til {draft_grant.REDACTED}" in text  # redacted in the page
    for key in draft_grant.HUMAN_FACTS + ("verified_by", "checked_at"):
        assert f"\n{key}: TODO" in text
    assert "source_modified: 2026-11-05T14:36" in text
    assert "## Formål\n\nStimulere til arrangementer i Innlandet." in text
    assert "### Avgrensing" in text
    assert '"1 million kroner"' in check and '"50 000 kroner"' in check
    assert "1. februar 2027 (2027-02-01): Søknadsfristen er 1. februar 2027 for arrangementer" in check


def test_safe_page_drops_aside_author_mail_and_phone():
    page = draft_grant.safe_page(PAGE)
    for leak in (FAKE_NAME, FAKE_MAIL, FAKE_TEL, "tel:"):
        assert leak not in page
    assert "Sist endret" in page


def test_refuses_output_into_context_or_eval(setup):
    tmp, cat, src, pages = setup
    for bad in (draft_grant.ROOT / "context" / "grants", draft_grant.ROOT / "eval" / "corpus" / "grants"):
        with pytest.raises(SystemExit, match="refused"):
            draft_grant.draft("99999", "syn", offline=True, pages_dir=pages, out_dir=bad, catalog_path=cat,
                              sources_path=src, save_raw_dir=None)


def test_slug():
    assert draft_grant.slug("Regionalt kulturfond Innlandet") == "regionalt_kulturfond_innlandet"
    assert draft_grant.slug("Tilskudd til ærlige små øyer") == "tilskudd_til_aerlige_sma_oyer"
