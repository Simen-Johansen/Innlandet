"""Check for task 011: the kill switch in harness/run.py. Model-free, safe for CI.

1. Three runs that fail the verification gate (empty GRANTS_DIR, so check_grants fails at stage 2,
   before any model call): runs 1 and 2 exit 1, run 3 exits 4 and writes out/HALTED.
2. The next run, with valid input, also exits 4 while out/HALTED exists.
3. A grant file last checked more than 30 days before EVAL_TODAY halts the run (exit 4).
4. No model call was made (out/cost_log.jsonl stays empty).

Restores the kill switch state it found (out/run_history.jsonl, cost_history.jsonl).
Red first: fails before task 011 (run 3 exits 1 and no out/HALTED).
Run: python eval/check_killswitch.py
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from common import OUT, ROOT, check

run = ROOT / "harness" / "run.py"
STATE = [OUT / "HALTED", OUT / "run_history.jsonl", OUT / "cost_history.jsonl"]
TODAY = "2026-11-05"


def reset():
    for f in STATE:
        f.unlink(missing_ok=True)


# A real halt must be resolved by a person, never cleared by a check.
check(not STATE[0].exists(), "out/HALTED exists: read it, fix the cause, delete it, then rerun")
saved = {f: f.read_bytes() for f in STATE[1:] if f.exists()}


def call(grants_dir=None, *args):
    env = {**os.environ, "PYTHONUTF8": "1", "EVAL_TODAY": TODAY}
    if grants_dir:
        env["GRANTS_DIR"] = str(grants_dir)
    else:
        env.pop("GRANTS_DIR", None)
    return subprocess.run([sys.executable, str(run), "--offline", *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=120)


def no_model_calls():
    log = OUT / "cost_log.jsonl"
    check(not log.exists() or not log.read_text(encoding="utf-8").strip(),
          "cost_log.jsonl has entries: the kill switch test must not reach the model")


reset()
try:
    # 1. Three failed runs in a row
    with tempfile.TemporaryDirectory() as empty:
        for i, expected in enumerate([1, 1, 4], 1):
            r = call(empty)
            check(r.returncode == expected,
                  f"failed run {i} exited {r.returncode}, expected {expected}: {r.stderr.strip()[-300:]}")
            no_model_calls()
    check((OUT / "HALTED").exists(), "out/HALTED missing after 3 consecutive failed runs")

    # 2. The next run refuses to start
    r = call()
    check(r.returncode == 4, f"run while out/HALTED exists exited {r.returncode}, expected 4")
    check((OUT / "HALTED").exists(), "out/HALTED must stay until a person deletes it")
    no_model_calls()

    # 3. Stale grant file: checked_at 31 days before EVAL_TODAY
    reset()
    src = sorted((ROOT / "eval" / "corpus" / "grants").glob("*.md"))[0]
    with tempfile.TemporaryDirectory() as tmp:
        text = src.read_text(encoding="utf-8")
        text = re.sub(r"^(fetched_at|checked_at):.*$", r"\1: 2026-10-05", text, flags=re.M)
        (Path(tmp) / src.name).write_text(text, encoding="utf-8")
        r = call(tmp)
    check(r.returncode == 4, f"stale grant file: exit {r.returncode}, expected 4: {r.stderr.strip()[-300:]}")
    check((OUT / "HALTED").exists(), "out/HALTED missing after a stale grant file")
    no_model_calls()
finally:
    reset()
    for f, data in saved.items():
        f.write_bytes(data)

print("PASS")
