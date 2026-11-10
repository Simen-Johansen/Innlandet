"""LLM-as-judge for plain language and helpfulness (task 014).

Run: python eval/judge.py [PLAN] [--out PATH]
     (defaults: out/grant_action_plan.md -> out/judge.json)

Scores one plan on four criteria, 1-5 each with one sentence of justification:
plain_language (klarspråk), actionable_steps, no_jargon, tone (for a volunteer).
The prompt is eval/prompts/judge.md, written by a human; {plan_path} in it becomes the plan's
path and the judge reads the file with its Read tool.

The judge advises, it never grades: exit 0 means judge.json is valid, whatever the scores.
Facts are checked by code (check_plan.py, check_render.py), never by the judge, and the scores
are not used as a retry signal. Exit 1 if a guard stops the call or the answer is invalid.

Guards before the call (copied from harness/run.py, the checks do not import harness code):
out/HALTED must be absent and the model cost in the last 24 h must be at most 5.00 USD.
The call's cost is appended to out/cost_history.jsonl (stage "judge"), so it counts toward
the kill switch. CLAUDE_BIN overrides the claude executable (for a free stub test).
Standard library only.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common import OUT, ROOT, check, fail

PROMPT = ROOT / "eval" / "prompts" / "judge.md"
HALTED = OUT / "HALTED"
COST_HISTORY = OUT / "cost_history.jsonl"
DAY_BUDGET_USD = 5.00
TIMEOUT_S = 300
CRITERIA = ("plain_language", "actionable_steps", "no_jargon", "tone")
CLAUDE_ARGS = ["--model", "sonnet", "--permission-mode", "dontAsk", "--allowedTools", "Read",
               "--output-format", "json", "--max-budget-usd", "0.50"]


def rel(path):
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def cost_last_24h():
    if not COST_HISTORY.exists():
        return 0.0
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    total = 0.0
    with open(COST_HISTORY, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            try:
                logged = datetime.fromisoformat(entry["logged_at"])
            except (KeyError, TypeError, ValueError):
                continue
            if logged >= since:
                total += entry.get("total_cost_usd") or 0
    return total


def log_cost(result):
    entry = {
        "stage": "judge", "attempt": 1,
        "total_cost_usd": result.get("total_cost_usd"), "duration_ms": result.get("duration_ms"),
        "num_turns": result.get("num_turns"), "is_error": result.get("is_error"),
        "session_id": result.get("session_id"),
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    OUT.mkdir(exist_ok=True)
    with open(COST_HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def call_claude(prompt):
    claude = shutil.which(os.environ.get("CLAUDE_BIN") or "claude")
    check(claude is not None, "claude CLI not found on PATH")
    try:
        r = subprocess.run([claude, "-p", prompt, *CLAUDE_ARGS], cwd=ROOT, capture_output=True,
                           text=True, encoding="utf-8", timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        log_cost({"is_error": True})
        fail(f"claude timed out after {TIMEOUT_S} s")
    try:
        result = json.loads(r.stdout)
    except json.JSONDecodeError:
        result = {"is_error": True}
    log_cost(result)
    check(isinstance(result.get("result"), str),
          f"claude exited {r.returncode} without a result: {r.stdout.strip()[:200]!r}")
    return result


def parse_scores(text):
    """The judge's answer as {criterion: {score, justification}}; a code fence is allowed."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    check(m is not None, f"judge answer has no JSON object: {text.strip()[:200]!r}")
    try:
        scores = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        fail(f"judge answer is not valid JSON: {e}")
    check(isinstance(scores, dict) and set(scores) == set(CRITERIA),
          f"judge answer must have exactly the keys {', '.join(CRITERIA)}, got {sorted(scores) if isinstance(scores, dict) else scores!r}")
    for name in CRITERIA:
        item = scores[name]
        check(isinstance(item, dict), f"{name}: must be an object with score and justification")
        score = item.get("score")
        check(type(score) is int and 1 <= score <= 5, f"{name}: score must be an integer 1-5, got {score!r}")
        why = item.get("justification")
        check(isinstance(why, str) and why.strip(), f"{name}: justification must be a non-empty string")
    return {name: {"score": scores[name]["score"], "justification": scores[name]["justification"].strip()}
            for name in CRITERIA}


def main():
    ap = argparse.ArgumentParser(description="Score a grant action plan with an LLM judge.")
    ap.add_argument("plan", nargs="?", default="out/grant_action_plan.md")
    ap.add_argument("--out", default="out/judge.json")
    args = ap.parse_args()
    plan = Path(args.plan) if Path(args.plan).is_absolute() else ROOT / args.plan
    out = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    out.unlink(missing_ok=True)  # a failed run must not leave an old judge.json behind

    check(plan.exists(), f"{rel(plan)} does not exist")
    check(plan.read_text(encoding="utf-8").strip(), f"{rel(plan)} is empty")
    check(PROMPT.exists(), f"{rel(PROMPT)} does not exist (a human writes it, task 014)")
    template = PROMPT.read_text(encoding="utf-8")
    check("{plan_path}" in template, f"{rel(PROMPT)} has no {{plan_path}} placeholder")
    check(not HALTED.exists(), "out/HALTED exists: no model calls until a person deletes it")
    day_cost = cost_last_24h()
    check(day_cost <= DAY_BUDGET_USD,
          f"model cost in the last 24 h is {day_cost:.2f} USD (max {DAY_BUDGET_USD:.2f}), not calling the judge")

    result = call_claude(template.replace("{plan_path}", rel(plan)))
    report = {
        "plan": rel(plan),
        "scores": parse_scores(result["result"]),
        "total_cost_usd": result.get("total_cost_usd"),
        "judged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prompt_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"ok: {rel(out)}  " + "  ".join(f"{k} {v['score']}" for k, v in report["scores"].items()))
    cost = report["total_cost_usd"]
    print(f"model cost {cost:.2f} USD" if isinstance(cost, (int, float)) else "model cost unknown")


if __name__ == "__main__":
    main()
