"""Check for task 007: the orchestrator's wiring and rejection path. Model-free, safe for CI.

1. `run.py --offline --dry-run` exits 0, prints 6 stages ("[1]" ... "[6]"), each with "check:",
   and runs nothing (out/ gets no stage outputs).
   NB: deletes stale stage outputs in out/ first, so run it after the other checks.
2. `run.py --offline fixtures/input_bad_checksum.json` exits 3, rejection is correct,
   and out/cost_log.jsonl has no entries (no tokens spent on rejected input).

Red first: fails with "harness/run.py does not exist" before the task.
Run: python eval/check_run.py
"""
import re
import subprocess
import sys

from common import OUT, ROOT, check, load_json

run = ROOT / "harness" / "run.py"
check(run.exists(), "harness/run.py does not exist")


def call(*args):
    return subprocess.run([sys.executable, str(run), *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", timeout=120)


# 1. Dry run. Remove stale stage outputs first (out/ is generated and git-ignored),
#    otherwise an earlier real run would make this test fail.
STAGE_FILES = ("entity.json", "eligible.json", "matches.json", "plan.json")
for f in STAGE_FILES:
    (OUT / f).unlink(missing_ok=True)
r = call("--offline", "--dry-run")
check(r.returncode == 0, f"dry run exited {r.returncode}: {r.stderr.strip()[-300:]}")
stages = re.findall(r"^\s*\[(\d)\].*$", r.stdout, flags=re.M)
check(stages == [str(i) for i in range(1, 7)], f"dry run must print stages [1]..[6] in order, got {stages}")
for line in re.findall(r"^\s*\[\d\].*$", r.stdout, flags=re.M):
    check("check:" in line, f"every stage line must name its check: {line.strip()!r}")
for f in STAGE_FILES:
    check(not (OUT / f).exists(), f"dry run must not produce out/{f}")

# 2. Rejection path
r = call("--offline", "fixtures/input_bad_checksum.json")
check(r.returncode == 3, f"bad checksum must exit 3, got {r.returncode}: {r.stderr.strip()[-300:]}")
rej = load_json(OUT / "rejection.json")
check(rej.get("reason") == "invalid_orgnr", f"reason {rej.get('reason')!r} != 'invalid_orgnr'")
log = OUT / "cost_log.jsonl"
check(not log.exists() or not log.read_text(encoding="utf-8").strip(),
      "cost_log.jsonl has entries: tokens were spent on a rejected input")

print("PASS")
