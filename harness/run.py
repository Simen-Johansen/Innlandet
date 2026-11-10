"""Orchestrator: run stages 1-6 in order with a check after each (task 007).

Usage: python harness/run.py [input_request.json] [--offline] [--dry-run]
       (default request: fixtures/input_hamar.json)

Code decides the order; stages hand off through files in out/. Stages 4 and 5 are headless
`claude -p` calls in an evaluator-optimizer loop: at most 3 attempts, each retry gets the
check's error text. Exit codes (SPEC.md): 0 plan delivered, 1 a check failed, 3 input rejected,
4 halted by the kill switch (task 011).

Safe operation (task 011, docs/safe-operation.md): out/ is wiped at the start of every run except
three state files: out/HALTED (while it exists every run exits 4; a person deletes it),
out/run_history.jsonl (exit code of every run) and out/cost_history.jsonl (every model call).
A run stops with exit 1 once its own cost reaches 1.50 USD. The kill switch writes out/HALTED and
exits 4 after 3 consecutive failed runs, above 3 USD in 24 h, or when a grant file was last
checked more than 30 days ago. Standard library only.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
HARNESS = ROOT / "harness"
EVAL = ROOT / "eval"
COST_LOG = OUT / "cost_log.jsonl"
DEFAULT_REQUEST = ROOT / "fixtures" / "input_hamar.json"

# Kill switch state: survives the wipe of out/ (task 011)
HALTED = OUT / "HALTED"
RUN_HISTORY = OUT / "run_history.jsonl"
COST_HISTORY = OUT / "cost_history.jsonl"
KEEP = {HALTED.name, RUN_HISTORY.name, COST_HISTORY.name}
RUN_BUDGET_USD = 1.50
DAY_BUDGET_USD = 3.00
MAX_FAILED_RUNS = 3
MAX_GRANT_AGE_DAYS = 30
EXIT_HALTED = 4

MAX_ATTEMPTS = 3
CLAUDE_TIMEOUT_S = 600
CLAUDE_ARGS = ["--model", "sonnet",
               "--permission-mode", "dontAsk", "--allowedTools", "Read,Edit(/out/**)",
               "--output-format", "json", "--max-budget-usd", "0.50"]
CHILD_ENV = {**os.environ, "PYTHONUTF8": "1"}

# In script/check args, "<req>" becomes the request path, "<offline>" becomes "--offline"
# (or is dropped) and "<today>" becomes "--today $EVAL_TODAY" (or is dropped) at run time.
# GRANTS_DIR and EVAL_TODAY reach every stage and check through CHILD_ENV (task 009).
STAGES = [
    {"name": "entity", "script": ["entity.py", "<req>", "<offline>"], "prompt": None,
     "input": "<request>", "output": "out/entity.json", "check": ["check_entity.py"]},
    {"name": "grants", "script": ["grants.py"], "prompt": None,
     "input": "context/grants/", "output": "(validated in place)", "check": ["check_grants.py"]},
    {"name": "filter", "script": ["filter.py", "<req>", "<today>"], "prompt": None,
     "input": "out/entity.json + context/grants/", "output": "out/eligible.json, out/match_input.md",
     "check": ["check_filter.py"]},
    {"name": "matcher", "script": None, "prompt": "match.md",
     "input": "out/match_input.md", "output": "out/matches.json", "check": ["check_matches.py"]},
    {"name": "guide", "script": ["guide_input.py", "<req>"], "prompt": "guide.md",
     "input": "out/entity.json, out/matches.json, out/guide_input/", "output": "out/plan.json",
     "check": ["check_plan.py", "<req>"]},
    {"name": "render", "script": ["render.py"], "prompt": None,
     "input": "out/plan.json", "output": "out/grant_action_plan.md", "check": ["check_render.py"]},
]


def fill(args, req, offline=False):
    today = os.environ.get("EVAL_TODAY")
    subs = {"<req>": [str(req)], "<offline>": ["--offline"] if offline else [],
            "<today>": ["--today", today] if today else []}
    return [x for a in args for x in subs.get(a, [a])]


def echo(text, stream=sys.stdout):
    for line in text.strip().splitlines():
        print(f"      {line}", file=stream)


def run_py(path, args):
    """Run a stage script or check with this interpreter, from the repo root."""
    return subprocess.run([sys.executable, str(path), *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", env=CHILD_ENV)


def run_check(stage, req):
    r = run_py(EVAL / stage["check"][0], fill(stage["check"][1:], req))
    passed = r.returncode == 0 and r.stdout.strip().endswith("PASS")
    return passed, (r.stderr.strip() or r.stdout.strip())


def log_cost(stage, attempt, result):
    entry = {
        "stage": stage, "attempt": attempt,
        "total_cost_usd": result.get("total_cost_usd"), "duration_ms": result.get("duration_ms"),
        "num_turns": result.get("num_turns"), "is_error": result.get("is_error"),
        "session_id": result.get("session_id"),
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    for log in (COST_LOG, COST_HISTORY):
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def call_claude(stage, attempt, prompt):
    claude = shutil.which("claude")
    if claude is None:
        print("claude CLI not found on PATH: install Claude Code and log in "
              "(see README, Offline run)", file=sys.stderr)
        sys.exit(1)
    try:
        r = subprocess.run([claude, "-p", prompt, *CLAUDE_ARGS], cwd=ROOT, capture_output=True,
                           text=True, encoding="utf-8", timeout=CLAUDE_TIMEOUT_S)
        out = r.stdout
    except subprocess.TimeoutExpired:
        out = ""
        print(f"      claude timed out after {CLAUDE_TIMEOUT_S} s", file=sys.stderr)
    try:
        result = json.loads(out)
    except json.JSONDecodeError:
        result = {"is_error": True}  # cost unknown; the check decides
    log_cost(stage, attempt, result)
    return result


def total_cost():
    if not COST_LOG.exists():
        return 0.0
    with open(COST_LOG, encoding="utf-8") as f:
        return sum(json.loads(line).get("total_cost_usd") or 0 for line in f if line.strip())


def read_jsonl(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def cost_last_24h():
    """Model cost of all runs in the last 24 h (real clock, also during eval)."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    total = 0.0
    for entry in read_jsonl(COST_HISTORY):
        try:
            logged = datetime.fromisoformat(entry["logged_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if logged >= since:
            total += entry.get("total_cost_usd") or 0
    return total


def stale_grants():
    """Grant files whose checked_at is more than 30 days before EVAL_TODAY (or today).

    Files without a valid checked_at are left to check_grants.py.
    """
    grants = ROOT / (os.environ.get("GRANTS_DIR") or Path("context") / "grants")
    today = date.fromisoformat(os.environ.get("EVAL_TODAY") or date.today().isoformat())
    stale = []
    for path in sorted(grants.glob("*.md")) if grants.exists() else []:
        with open(path, encoding="utf-8") as f:
            m = re.search(r"^checked_at:\s*(\d{4}-\d{2}-\d{2})", f.read(), flags=re.M)
        try:
            checked = date.fromisoformat(m.group(1)) if m else None
        except ValueError:
            checked = None
        if checked and (today - checked).days > MAX_GRANT_AGE_DAYS:
            stale.append(f"{path.name} (checked {checked})")
    return stale


def halt(reason):
    """Kill switch: write out/HALTED and return exit code 4. A person deletes the file."""
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(HALTED, "w", encoding="utf-8") as f:
        f.write(f"halted_at: {stamp}\nreason: {reason}\n"
                "Fix the cause, then delete out/HALTED to allow runs again.\n")
    print(f"HALTED: {reason} (exit {EXIT_HALTED}, see out/HALTED)", file=sys.stderr)
    return EXIT_HALTED


def record_run(code):
    """Append the run's exit code; halt after MAX_FAILED_RUNS failed runs in a row."""
    entry = {"exit": code, "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with open(RUN_HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    last = [e.get("exit") for e in read_jsonl(RUN_HISTORY)[-MAX_FAILED_RUNS:]]
    if len(last) == MAX_FAILED_RUNS and all(c == 1 for c in last):
        return halt(f"{MAX_FAILED_RUNS} consecutive runs failed the verification gate")
    return code


def wipe_out():
    """Delete stale output (it would fake a PASS) but keep the kill switch state."""
    OUT.mkdir(exist_ok=True)
    for path in OUT.iterdir():
        if path.name in KEEP:
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


def reject(n, stage):
    with open(OUT / "rejection.json", encoding="utf-8") as f:
        reason = json.load(f).get("reason", "")
    r = run_py(EVAL / "check_rejection.py", [reason])
    if r.returncode != 0:
        print(f"[{n}] {stage['name']}  rejection check FAIL", file=sys.stderr)
        echo(r.stderr or r.stdout, sys.stderr)
        return 1
    print(f"rejected: {reason} (stage {n}, exit 3)")
    return 3


def run_stage(n, stage, req, offline):
    """Return None to continue, or the exit code to stop with."""
    name = stage["name"]
    if stage["script"]:
        r = run_py(HARNESS / stage["script"][0], fill(stage["script"][1:], req, offline))
        echo(r.stdout)
        if r.returncode == 3:
            return reject(n, stage)
        if r.returncode != 0:
            print(f"[{n}] {name}  {stage['script'][0]} exited {r.returncode}", file=sys.stderr)
            echo(r.stderr, sys.stderr)
            return 1

    if not stage["prompt"]:
        passed, detail = run_check(stage, req)
        print(f"[{n}] {name}  check {'PASS' if passed else 'FAIL'}")
        if not passed:
            echo(detail, sys.stderr)
            return 1
        return None

    with open(HARNESS / "prompts" / stage["prompt"], encoding="utf-8") as f:
        base_prompt = f.read()
    output = ROOT / stage["output"]
    feedback = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        output.unlink(missing_ok=True)  # a stale file must never pass the check
        prompt = base_prompt
        if feedback:
            prompt += f"\n\nPrevious check output (fix this): {feedback}"
        if total_cost() >= RUN_BUDGET_USD:
            print(f"[{n}] {name}  run budget {RUN_BUDGET_USD:.2f} USD reached "
                  f"({total_cost():.2f} USD spent), stopping", file=sys.stderr)
            return 1
        if cost_last_24h() > DAY_BUDGET_USD:
            return halt(f"model cost in the last 24 h is {cost_last_24h():.2f} USD "
                        f"(max {DAY_BUDGET_USD:.2f})")
        result = call_claude(name, attempt, prompt)
        passed, detail = run_check(stage, req)
        cost = result.get("total_cost_usd")
        cost_text = f"{cost:.2f} USD" if isinstance(cost, (int, float)) else "cost unknown"
        print(f"[{n}] {name}  attempt {attempt}/{MAX_ATTEMPTS} ({cost_text})  "
              f"check {'PASS' if passed else 'FAIL'}")
        if passed:
            return None
        echo(detail, sys.stderr)
        feedback = detail
    print(f"[{n}] {name}  failed {MAX_ATTEMPTS} attempts, stopping", file=sys.stderr)
    return 1


def dry_run(req_label):
    name_w = max(len(s["name"]) for s in STAGES)
    grants_label = (os.environ.get("GRANTS_DIR") or "context/grants").rstrip("/\\") + "/"
    flows = [f"{s['input'].replace('<request>', req_label).replace('context/grants/', grants_label)}"
             f" -> {s['output']}" for s in STAGES]
    flow_w = max(len(f) for f in flows)
    for n, (s, flow) in enumerate(zip(STAGES, flows), 1):
        check = " ".join(["eval/" + s["check"][0], *fill(s["check"][1:], req_label)])
        print(f"[{n}] {s['name']:<{name_w}}  {flow:<{flow_w}}   check: {check}")


def main(argv):
    parser = argparse.ArgumentParser(description="Run the whole chain, stages 1-6")
    parser.add_argument("request", nargs="?", default=str(DEFAULT_REQUEST),
                        help="input_request.json (default: fixtures/input_hamar.json)")
    parser.add_argument("--offline", action="store_true", help="use Brreg fixtures, no network")
    parser.add_argument("--dry-run", action="store_true", help="print the wiring, run nothing")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    req = Path(args.request).resolve()
    try:
        req_label = req.relative_to(ROOT).as_posix()
    except ValueError:
        req_label = str(req)
    if args.dry_run:
        if HALTED.exists():
            print("warning: out/HALTED exists, a real run would exit 4", file=sys.stderr)
        dry_run(req_label)
        return 0
    if HALTED.exists():
        with open(HALTED, encoding="utf-8") as f:
            echo(f.read(), sys.stderr)
        print(f"refusing to run while out/HALTED exists (exit {EXIT_HALTED})", file=sys.stderr)
        return EXIT_HALTED
    if not req.exists():
        print(f"request file not found: {args.request}", file=sys.stderr)
        return 1

    wipe_out()
    day_cost = cost_last_24h()
    if day_cost > DAY_BUDGET_USD:
        return halt(f"model cost in the last 24 h is {day_cost:.2f} USD (max {DAY_BUDGET_USD:.2f})")
    stale = stale_grants()
    if stale:
        return halt(f"grant files not checked in {MAX_GRANT_AGE_DAYS} days: {', '.join(stale)}")

    for n, stage in enumerate(STAGES, 1):
        code = run_stage(n, stage, req, args.offline)
        if code is not None:
            return code if code == EXIT_HALTED else record_run(code)
    print(f"ok: out/grant_action_plan.md (model cost {total_cost():.2f} USD, see out/cost_log.jsonl)")
    return record_run(0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
