"""tools/add_expectation.py on synthetic expected.json files (task 017): refusals and a one-line diff."""
import difflib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import add_expectation as ae  # noqa: E402

HEADER = "case\tgrant_id\treason\tdecision\tdecided_by\n"
MULTI = '{\n  "today": "2026-11-05",\n  "must_match": [\n    "f"\n  ],\n  "must_reject": [\n    "a",\n' \
        '    {"grant_id": "h", "reason": "org_form_not_allowed"}\n  ]\n}\n'
ONELINE = '{"today": "2026-11-05", "must_match": ["f"], "must_reject": ["a", "d"]}\n'
EMPTY = '{\n    "must_match": [],\n    "must_reject": ["a"]\n}\n'
NOKEY = '{"today": "2026-11-05", "must_match": ["f"]}\n'


@pytest.fixture
def world(tmp_path):
    cases, corpus = tmp_path / "cases", tmp_path / "corpus"
    corpus.mkdir()
    for gid in ("n", "r", "a", "f"):
        (corpus / f"{gid}.md").write_text("---\n---\n", encoding="utf-8")
    for name, text in (("01_multi", MULTI), ("02_oneline", ONELINE), ("03_empty", EMPTY), ("04_nokey", NOKEY)):
        (cases / name).mkdir(parents=True)
        (cases / name / "expected.json").write_bytes(text.encode("utf-8"))
    return tmp_path, cases, corpus


def run(tmp, cases, corpus, rows, *flags):
    tsv = tmp / "d.tsv"
    tsv.write_text(HEADER + "".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")
    return ae.main([str(tsv), "--cases", str(cases), "--corpus", str(corpus), *flags])


def diff(old, new):
    return [line for line in difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0)
            if line[:1] in "+-" and not line.startswith(("+++", "---"))]


def test_minimal_diff_in_every_layout(world):
    tmp, cases, corpus = world
    rows = [("01_multi", "n", "", "must_reject", "SJ"), ("02_oneline", "n", "", "must_reject", "EH"),
            ("03_empty", "r", "", "must_match", "SJ"), ("01_multi", "r", "outside_region", "must_reject", "SJ")]
    assert run(tmp, cases, corpus, rows, "--check") == 0
    assert (cases / "01_multi" / "expected.json").read_text(encoding="utf-8") == MULTI  # --check writes nothing
    assert run(tmp, cases, corpus, rows) == 0
    multi = (cases / "01_multi" / "expected.json").read_text(encoding="utf-8")
    assert diff(MULTI, multi) == [
        '-    {"grant_id": "h", "reason": "org_form_not_allowed"}',
        '+    {"grant_id": "h", "reason": "org_form_not_allowed"},', '+    "n",',
        '+    {"grant_id": "r", "reason": "outside_region"}']
    one = (cases / "02_oneline" / "expected.json").read_text(encoding="utf-8")
    assert one == ONELINE.replace('"d"]', '"d", "n"]')
    empty = (cases / "03_empty" / "expected.json").read_text(encoding="utf-8")
    assert empty == EMPTY.replace('"must_match": []', '"must_match": ["r"]')


def test_crlf_file_stays_crlf(world):
    tmp, cases, corpus = world
    p = cases / "01_multi" / "expected.json"
    p.write_bytes(MULTI.replace("\n", "\r\n").encode("utf-8"))
    assert run(tmp, cases, corpus, [("01_multi", "n", "", "must_reject", "SJ")]) == 0
    raw = p.read_bytes().decode("utf-8")
    assert "\n" not in raw.replace("\r\n", "") and '    "n"' in raw


def test_undecided_rows_ignored(world):
    tmp, cases, corpus = world
    assert run(tmp, cases, corpus, [("01_multi", "n", "", "must_reject", ""),
                                     ("01_multi", "n", "", "leave_out", "SJ")]) == 0
    assert (cases / "01_multi" / "expected.json").read_text(encoding="utf-8") == MULTI


@pytest.mark.parametrize("row, why", [
    (("01_multi", "zzz", "", "must_reject", "SJ"), "not in"),
    (("01_multi", "f", "", "must_reject", "SJ"), "already in must_match"),
    (("99_gone", "n", "", "must_reject", "SJ"), "case dir missing"),
])
def test_refusals_write_nothing(world, capsys, row, why):
    tmp, cases, corpus = world
    good = ("02_oneline", "n", "", "must_reject", "SJ")
    assert run(tmp, cases, corpus, [good, row]) == 2
    assert why in capsys.readouterr().out
    assert (cases / "02_oneline" / "expected.json").read_text(encoding="utf-8") == ONELINE


def test_missing_key_is_refused_with_line_to_add(world, capsys):
    tmp, cases, corpus = world
    assert run(tmp, cases, corpus, [("04_nokey", "n", "", "must_reject", "SJ")]) == 1
    assert 'add "n" to "must_reject" by hand' in capsys.readouterr().out
    assert (cases / "04_nokey" / "expected.json").read_text(encoding="utf-8") == NOKEY


def test_same_list_is_skipped(world, capsys):
    tmp, cases, corpus = world
    assert run(tmp, cases, corpus, [("02_oneline", "a", "", "must_reject", "SJ")]) == 0
    assert "skip" in capsys.readouterr().out
