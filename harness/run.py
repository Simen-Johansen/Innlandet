"""Orchestrator: run stages 1-6 in order with a check after each (task 007).

Usage: python harness/run.py [input_request.json] [--offline] [--dry-run]
       (default request: fixtures/input_hamar.json)

Code decides the order; stages hand off through files in out/. Stages 4 and 5 are headless
`claude -p` calls in an evaluator-optimizer loop: at most 3 attempts, each retry gets the
check's error text. Exit codes (SPEC.md): 0 plan delivered, 1 a check failed, 3 input rejected.
Standard library only.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
HARNESS = ROOT / "harness"
EVAL = ROOT / "eval"
COST_LOG = OUT / "cost_log.jsonl"
DEFAULT_REQUEST = ROOT / "fixtures" / "input_hamar.json"

MAX_ATTEMPTS = 3
CLAUDE_TIMEOUT_S = 600
CLAUDE_ARGS = ["--permission-mode", "dontAsk", "--allowedTools", "Read,Edit(/out/**)",
               "--output-format", "json", "--max-budget-usd", "0.50"]
CHILD_ENV = {**os.environ, "PYTHONUTF8": "1"}

# In script/check args, "<req>" becomes the request path and "<offline>" becomes "--offline"
# (or is dropped) at run time.
STAGES = [
    {"name": "entity", "script": ["entity.py", "<req>", "<offline>"], "prompt": None,
     "input": "<request>", "output": "out/entity.json", "check": ["check_entity.py"]},
    {"name": "grants", "script": ["grants.py"], "prompt": None,
     "input": "context/grants/", "output": "(validated in place)", "check": ["check_grants.py"]},
    {"name": "filter", "script": ["filter.py", "<req>"], "prompt": None,
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
    subs = {"<req>": [str(req)], "<offline>": ["--offline"] if offline else []}
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
    with open(COST_LOG, "a", encoding="utf-8") as f:
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
    flows = [f"{s['input'].replace('<request>', req_label)} -> {s['output']}" for s in STAGES]
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
        dry_run(req_label)
        return 0
    if not req.exists():
        print(f"request file not found: {args.request}", file=sys.stderr)
        return 1

    shutil.rmtree(OUT, ignore_errors=True)  # stale output would fake a PASS
    OUT.mkdir()
    for n, stage in enumerate(STAGES, 1):
        code = run_stage(n, stage, req, args.offline)
        if code is not None:
            return code
    print(f"ok: out/grant_action_plan.md (model cost {total_cost():.2f} USD, see out/cost_log.jsonl)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
