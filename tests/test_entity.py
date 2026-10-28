import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))

from entity import Rejection, extract, lookup, mod11_ok  # noqa: E402


def test_mod11():
    assert mod11_ok("942440618")
    assert not mod11_ok("970169215")
    assert mod11_ok("123456750")  # weighted sum 132 = 12 * 11 -> check digit 0
    assert not mod11_ok("12345678")
    assert not mod11_ok("94244061x")


def test_extract_falls_back_to_postadresse():
    raw = {
        "organisasjonsnummer": "942440618",
        "navn": "X",
        "organisasjonsform": {"kode": "FLI"},
        "postadresse": {"adresse": ["street 1"], "kommunenummer": "3403"},
        "registrertIFrivillighetsregisteret": True,
    }
    entity = extract(raw)
    assert entity["kommunenummer"] == "3403"
    assert not any("adresse" in k for k in entity)


def test_missing_frivillighetsregisteret_is_not_false():
    with pytest.raises(Rejection):
        extract({"organisasjonsnummer": "942440618", "postadresse": {"kommunenummer": "3403"}})


def test_invalid_orgnr_rejected_before_fetch():
    with pytest.raises(Rejection) as e:
        lookup("970169215", offline=False)
    assert e.value.reason == "invalid_orgnr"
