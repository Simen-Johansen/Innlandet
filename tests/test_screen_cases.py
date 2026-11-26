"""tools/screen_cases.py on a temporary synthetic case (task 017): out/ restored, TODO refused, TSV merge."""
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import screen_cases  # noqa: E402

GJOVIK = "983758622"  # club fixture already in fixtures/ (case 13)
GRANT = """---
id: syn_new
title: Syntetisk ny ordning
url: https://innlandetfylke.no/x.1.aspx
provider: innlandet_fylkeskommune
applicant_orgforms: FLI
requires_frivillighetsregisteret: false
region_prefix: {prefix}
target_group: alle
max_amount_nok: 50000
deadlines: 2027-02-01
fetched_at: 2026-11-26
checked_at: 2026-11-26
source_modified: 2026-11-05T14:36
verified_by: XX
---

## Formål

Syntetisk.

## Hvem kan søke

Lag.

## Hva kan det søkes om

Arrangementer.

## Vedlegg

Ingen.

## Frister og rapportering

1. februar 2027.
"""


def tree_hash(d):
    h = hashlib.sha1()
    if d.exists():
        for p in sorted(d.rglob("*")):
            if p.is_file():
                h.update(str(p.relative_to(d)).encode() + p.read_bytes())
    return h.hexdigest()


@pytest.fixture
def world(tmp_path):
    cases = tmp_path / "cases"
    case = cases / "90_syn"
    case.mkdir(parents=True)
    (case / "input_request.json").write_text(json.dumps(
        {"orgnr": GJOVIK, "project_idea": "Syntetisk idé", "requested_amount_nok": 10000, "output_language": "no"}), encoding="utf-8")
    (case / "expected.json").write_text(json.dumps(
        {"today": "2026-11-05", "expected_exit": 0, "must_match": ["secret_a"], "must_reject": ["secret_b"]}),
        encoding="utf-8")
    base = tmp_path / "base"
    base.mkdir()
    shutil.copy2(ROOT / "eval" / "corpus" / "grants" / "arrangementsutvikling_innen_idrett.md", base)
    add = tmp_path / "add"
    add.mkdir()
    return tmp_path, cases, base, add


def test_screen_keeps_and_filters_and_restores_out(world):
    tmp, cases, base, add = world
    (add / "syn_new.md").write_text(GRANT.format(prefix="34"), encoding="utf-8")
    before = tree_hash(screen_cases.OUT)
    rows = screen_cases.screen(cases, base, add)
    assert tree_hash(screen_cases.OUT) == before
    assert [(r["case"], r["grant_id"], r["filter"]) for r in rows] == [("90_syn", "syn_new", "kept: matcher decides")]
    assert rows[0]["orgform"] == "FLI" and rows[0]["kommunenummer"].startswith("34")
    (add / "syn_new.md").write_text(GRANT.format(prefix="3403"), encoding="utf-8")  # Hamar only
    rows = screen_cases.screen(cases, base, add)
    assert rows[0]["filter"] == "filtered: outside_region"
    assert tree_hash(screen_cases.OUT) == before


def test_never_prints_current_lists(world, capsys):
    tmp, cases, base, add = world
    (add / "syn_new.md").write_text(GRANT.format(prefix="34"), encoding="utf-8")
    screen_cases.main(["--add", str(add), "--grants-dir", str(base), "--cases", str(cases),
                       "--tsv", str(tmp / "d.tsv")])
    out = capsys.readouterr().out + (tmp / "d.tsv").read_text(encoding="utf-8")
    assert "secret_a" not in out and "secret_b" not in out


def test_refuses_todo_facts(world):
    tmp, cases, base, add = world
    (add / "syn_new.md").write_text(GRANT.format(prefix="34").replace("deadlines: 2027-02-01", "deadlines: TODO"),
                                    encoding="utf-8")
    with pytest.raises(SystemExit, match="TODO"):
        screen_cases.screen(cases, base, add)


def test_tsv_keeps_human_columns(tmp_path):
    tsv = tmp_path / "d.tsv"
    row = {"case": "c", "grant_id": "g", "filter": "kept: matcher decides"}
    screen_cases.write_tsv(tsv, [dict(row)])
    (first,) = screen_cases.read_tsv(tsv)
    first.update(proposal="must_reject", why="why", decision="must_reject", decided_by="SJ")
    with open(tsv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=screen_cases.COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerow(first)
    screen_cases.write_tsv(tsv, [dict(row, filter="filtered: outside_region")])
    (got,) = screen_cases.read_tsv(tsv)
    assert got["filter"] == "filtered: outside_region"
    assert (got["proposal"], got["decision"], got["decided_by"]) == ("must_reject", "must_reject", "SJ")
