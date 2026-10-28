"""Check for rejections (task 001, 003, later the test set).

Run: python eval/check_rejection.py invalid_orgnr
Passes if out/rejection.json exists with that reason, and no entity/plan was produced.
"""
import sys

from common import OUT, check, load_json

check(len(sys.argv) == 2, "usage: python eval/check_rejection.py <expected_reason>")
expected = sys.argv[1]

rej = load_json(OUT / "rejection.json")
check(rej.get("reason") == expected, f"reason {rej.get('reason')!r} != expected {expected!r}")
check(isinstance(rej.get("detail"), str) and rej["detail"].strip(), "detail must be a non-empty string")
check(not (OUT / "plan.json").exists(), "a rejected input must not produce out/plan.json")
if expected == "invalid_orgnr":
    check(not (OUT / "entity.json").exists(), "invalid orgnr must be rejected before any Brreg lookup")

print("PASS")
