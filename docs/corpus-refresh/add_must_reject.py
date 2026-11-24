"""C4 corpus refresh (25.11): add arrangementsutvikling_innen_idrett to must_reject in the cases that reach the matcher.

A human runs this AFTER copying context/grants/*.md into eval/corpus/grants/ (it refuses otherwise, because a
must_reject for a grant that is not in the corpus fails). Claude wrote this script but never reads expected.json.
Review the result with: git diff eval/cases

Run: python docs/corpus-refresh/add_must_reject.py [--check]   (--check prints what would change, writes nothing)
"""
import json
import sys
from pathlib import Path

GRANT = "arrangementsutvikling_innen_idrett"
CASES = ["01_typical_hht_outdoor", "02_typical_arts_two_municipalities", "03_boundary_ski_equipment",
         "04_boundary_arts_hamar_only", "05_boundary_fli_in_stange", "06_boundary_deadline_passed",
         "07_boundary_amount_over_max", "11_reject_off_topic", "12_norwegian_in_and_out",
         "stress_01_injection_grant_text", "stress_02_injection_project_idea"]
ROOT = Path(__file__).resolve().parents[2]


def listed(items):
    return any((i if isinstance(i, str) else i.get("grant_id")) == GRANT for i in items)


def main():
    check = "--check" in sys.argv
    if not (ROOT / "eval" / "corpus" / "grants" / f"{GRANT}.md").exists():
        print(f"STOP: eval/corpus/grants/{GRANT}.md is missing. Copy context/grants/*.md into the corpus first.")
        return 1
    changed = 0
    for name in CASES:
        path = ROOT / "eval" / "cases" / name / "expected.json"
        with open(path, encoding="utf-8") as f:
            exp = json.load(f)
        items = exp.setdefault("must_reject", [])
        if listed(items):
            print(f"skip    {name} (already listed)")
            continue
        items.append(GRANT)
        changed += 1
        print(f"{'would add' if check else 'added  '} {name}")
        if not check:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(exp, f, ensure_ascii=False, indent=2)
                f.write("\n")
    print(f"{changed} of {len(CASES)} cases {'would change' if check else 'changed'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
