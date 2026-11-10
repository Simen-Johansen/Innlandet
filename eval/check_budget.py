"""Check for task 011: the 24 h cost cap in harness/run.py. Model-free, safe for CI.

1. A fake out/cost_history.jsonl with 3.10 USD logged now (cap: 3 USD per 24 h) stops the run
   before any claude call: exit 4, out/HALTED exists, out/cost_log.jsonl stays empty.
2. Cost older than 24 h does not count: 5.00 USD logged 2 days ago, a bad orgnr still gets the
   normal rejection (exit 3) and no model call.

The 1.50 USD per-run cap cannot be faked here (out/cost_log.jsonl is emptied at the start of every
run); docs/safe-operation.md explains how it is enforced.
Restores the kill switch state it found (out/run_history.jsonl, cost_history.jsonl).
Red first: fails before task 011 (the run ignores the cost history).
Run: python eval/check_budget.py
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from common import OUT, ROOT, check

run = ROOT / "harness" / "run.py"
STATE = [OUT / "HALTED", OUT / "run_history.jsonl", OUT / "cost_history.jsonl"]


def reset():
    for f in STATE:
        f.unlink(missing_ok=True)


# A real halt must be resolved by a person, never cleared by a check.
check(not STATE[0].exists(), "out/HALTED exists: read it, fix the cause, delete it, then rerun")
saved = {f: f.read_bytes() for f in STATE[1:] if f.exists()}


def seed(cost, age):
    OUT.mkdir(exist_ok=True)
    stamp = (datetime.now(timezone.utc) - age).isoformat(timespec="seconds")
    entry = {"stage": "matcher", "attempt": 1, "total_cost_usd": cost, "logged_at": stamp}
    with open(OUT / "cost_history.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def call(*args):
    env = {**os.environ, "PYTHONUTF8": "1"}
    env.pop("GRANTS_DIR", None)
    return subprocess.run([sys.executable, str(run), "--offline", *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=120)


def no_model_calls():
    log = OUT / "cost_log.jsonl"
    check(not log.exists() or not log.read_text(encoding="utf-8").strip(),
          "cost_log.jsonl has entries: the run reached the model above the cost cap")


reset()
try:
    # 1. Above the 24 h cap
    seed(3.10, timedelta(minutes=5))
    r = call()
    check(r.returncode == 4, f"3.10 USD in 24 h: exit {r.returncode}, expected 4: {r.stderr.strip()[-300:]}")
    check((OUT / "HALTED").exists(), "out/HALTED missing after the 24 h cost cap")
    no_model_calls()

    # 2. Old cost is ignored
    reset()
    seed(5.00, timedelta(days=2))
    r = call("fixtures/input_bad_checksum.json")
    check(r.returncode == 3, f"cost from 2 days ago must not halt: exit {r.returncode}, expected 3")
    check(not (OUT / "HALTED").exists(), "out/HALTED written for cost older than 24 h")
    no_model_calls()
finally:
    reset()
    for f, data in saved.items():
        f.write_bytes(data)

print("PASS")
