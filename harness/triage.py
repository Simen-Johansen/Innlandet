"""Catalog triage worksheet: humans decide pending entries in context/catalog.json (no model).

Usage:
  python harness/triage.py                       write out/triage.tsv, one row per pending entry
  python harness/triage.py --apply out/triage.tsv  (run by a human) record the decided rows in the catalog

Each row has a title-based `proposed_reason` (a suggestion only, never a decision) and an editable `reason`
prefilled with it. A row counts as decided only when a human puts initials in `decided_by`; then --apply sets
status not_relevant, reason and decided_by. Rows without initials, or with an unknown reason, stay pending.
`deferred_verification` means: possibly relevant for a club, but not verified before the exam (time limit,
not a judgment about the grant). Standard library only.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "context" / "catalog.json"
DEFAULT_TSV = ROOT / "out" / "triage.tsv"
REASONS = {"applicant_not_voluntary", "closed", "expired_no_next_round", "not_a_grant", "duplicate",
           "deferred_verification"}
COLUMNS = ["page_id", "title", "url", "proposed_reason", "reason", "decided_by"]

# Page ids whose title suggests a voluntary club might apply. Everything else is proposed as
# applicant_not_voluntary (municipalities, schools, businesses, apprentices, building owners, individuals).
CLUB_PLAUSIBLE = {
    "2659",   # kunstnerresidenser
    "7069",   # Grønn framtid Innlandet
    "17894",  # vilttiltak
    "18103",  # spillemidler
    "18509",  # kulturarenaer
    "22176",  # pensjonistforeninger
    "22177",  # organisasjoner for mennesker med nedsatt funksjonsevne
    "23015",  # fiskesprellaktivitet
    "24601",  # vassdragsmidler
    "35981",  # Interreg Sverige-Norge
    "36451",  # tiltak i statlig sikret friluftslivsområde
    "36673",  # samfunnsnyttige og humanitære organisasjoner
    "37168",  # store arrangementer innen idrett
    "42109",  # etablerte kulturaktører
    "58403",  # ULF - Ungdommens livskvalitetsfond
    "61345",  # privatarkiver
    "62588",  # utviklingsprosjekt kunst og kultur
    "62589",  # regionalt kulturfond
    "66424",  # forebyggende trafikksikkerhetsarbeid
    "81560",  # økt internasjonalt samarbeid
}

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def load():
    with open(CATALOG, encoding="utf-8") as f:
        return json.load(f)


def write_sheet(path):
    pending = [e for e in load()["entries"] if e.get("status") == "pending"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(COLUMNS)
        for e in pending:
            proposal = "deferred_verification" if e["page_id"] in CLUB_PLAUSIBLE else "applicant_not_voluntary"
            w.writerow([e["page_id"], e.get("title", ""), e.get("url", ""), proposal, proposal, ""])
    n_def = sum(e["page_id"] in CLUB_PLAUSIBLE for e in pending)
    print(f"{len(pending)} pending -> {path} ({n_def} proposed deferred_verification, "
          f"{len(pending) - n_def} applicant_not_voluntary). Proposals only: a human fills decided_by.")


def apply_sheet(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    missing = [c for c in ("page_id", "reason", "decided_by") if rows and c not in rows[0]]
    if missing:
        sys.exit(f"FAIL: {path.name} lacks column(s) {', '.join(missing)}")
    cat = load()
    by_id = {e["page_id"]: e for e in cat["entries"]}
    applied, skipped = 0, []
    for r in rows:
        pid, reason, who = r["page_id"].strip(), r["reason"].strip(), r["decided_by"].strip()
        e = by_id.get(pid)
        if not who:
            continue
        if e is None or e.get("status") != "pending":
            skipped.append(f"{pid}: not a pending entry")
        elif reason not in REASONS:
            skipped.append(f"{pid}: unknown reason {reason!r}")
        else:
            e.update(status="not_relevant", reason=reason, decided_by=who)
            applied += 1
    with open(CATALOG, "w", encoding="utf-8") as f:
        f.write(json.dumps(cat, ensure_ascii=False, indent=2) + "\n")
    left = sum(e.get("status") == "pending" for e in cat["entries"])
    for s in skipped:
        print(f"skipped {s}")
    print(f"{applied} decided, {len(skipped)} skipped, {left} still pending")


def main():
    ap = argparse.ArgumentParser(description="Triage worksheet for pending catalog entries.")
    ap.add_argument("--apply", type=Path, metavar="TSV", help="record the rows a human decided")
    ap.add_argument("--out", type=Path, default=DEFAULT_TSV)
    args = ap.parse_args()
    if args.apply:
        apply_sheet(args.apply)
    else:
        write_sheet(args.out)


if __name__ == "__main__":
    main()
