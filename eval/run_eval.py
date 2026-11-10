"""Evaluation harness for task 009: run the chain on every case in eval/cases/ against the frozen corpus.

Run: python eval/run_eval.py [--case NAME ...] [--runs N]

Each case folder holds input_request.json and expected.json. The Author writes expected.json
BEFORE the case is run; a case without it is reported as FAIL and not run (no tokens spent).
expected.json keys (all optional except expected_exit):
  today                 YYYY-MM-DD, passed as EVAL_TODAY (default 2026-11-05)
  expected_exit         int, or a list of allowed ints (e.g. [0, 3])
  rejection_reason      reason in out/rejection.json
  must_match            grant ids the matcher must mark "match"
  must_reject           grant ids, or {"grant_id": ..., "reason": ...}: rejected by the filter
                        (with that reason, if given) or marked "reject" by the matcher
  must_not_include      grant ids that must not be in out/plan.json
  amount_note_required  true (every planned grant with max < requested has an amount_note)
                        or a list of grant ids that must have a non-empty amount_note

Every run uses GRANTS_DIR=eval/corpus/grants, EVAL_TODAY=<today> and EXPECTED_MATCHES="" (so
check_matches.py does not grade the case against the running example). A case runs --runs
times (default 3) if it reached the model, once if it was rejected before. A case passes only
if every run passes. Rejections before the model must leave out/cost_log.jsonl empty.

Prints a table plus totals, writes out/eval_report.json and a raw log in docs/eval-logs/.
Exit 0 only if every case passes. Standard library only.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from common import OUT, ROOT

CASES = ROOT / "eval" / "cases"
CORPUS = Path("eval") / "corpus" / "grants"
LOGS = ROOT / "docs" / "eval-logs"
RUN = ROOT / "harness" / "run.py"
DEFAULT_TODAY = "2026-11-05"
KEYS = {"today", "expected_exit", "rejection_reason", "must_match", "must_reject",
        "must_not_include", "amount_note_required"}
# Rejections made by stages 1-3, before any model call.
PRE_MODEL_REASONS = {"invalid_orgnr", "invalid_request", "not_found", "outside_innlandet", "bankrupt_or_dissolving",
                     "no_eligible_grants"}


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def snapshot():
    """Everything a run left in out/, read before the next run wipes it."""
    log = OUT / "cost_log.jsonl"
    costs = []
    if log.exists():
        with open(log, encoding="utf-8") as f:
            costs = [json.loads(line) for line in f if line.strip()]
    return {name: read_json(OUT / f"{name}.json")
            for name in ("rejection", "eligible", "matches", "plan")} | {"costs": costs}


def grade(exp, code, out, requested):
    """List of failure messages; empty means the run passed."""
    errors = []
    allowed = exp["expected_exit"] if isinstance(exp["expected_exit"], list) else [exp["expected_exit"]]
    if code not in allowed:
        errors.append(f"exit {code}, expected {allowed}")
    rej = out["rejection"] or {}
    if exp.get("rejection_reason") and rej.get("reason") != exp["rejection_reason"]:
        errors.append(f"rejection {rej.get('reason')!r}, expected {exp['rejection_reason']!r}")
    if rej.get("reason") in PRE_MODEL_REASONS and out["costs"]:
        errors.append(f"rejected as {rej['reason']} but {len(out['costs'])} model call(s) were logged")

    verdict = {m.get("grant_id"): m.get("verdict") for m in (out["matches"] or {}).get("matches", [])}
    filtered = {r["grant_id"]: r["reason"] for r in (out["eligible"] or {}).get("rejected", [])}
    for gid in exp.get("must_match", []):
        if verdict.get(gid) != "match":
            errors.append(f"{gid}: expected match, got {verdict.get(gid) or filtered.get(gid) or 'nothing'}")
    for item in exp.get("must_reject", []):
        gid, reason = (item, None) if isinstance(item, str) else (item["grant_id"], item.get("reason"))
        if reason:
            if filtered.get(gid) != reason:
                errors.append(f"{gid}: expected filter reason {reason}, got {filtered.get(gid) or verdict.get(gid)}")
        elif gid not in filtered and verdict.get(gid) != "reject":
            errors.append(f"{gid}: expected reject, got {verdict.get(gid) or 'nothing'}")

    planned = {g.get("grant_id"): g for g in (out["plan"] or {}).get("grants", [])}
    for gid in exp.get("must_not_include", []):
        if gid in planned:
            errors.append(f"{gid}: must not be in plan.json")
    need = exp.get("amount_note_required")
    if need is True:
        need = [gid for gid, g in planned.items()
                if isinstance(g.get("max_amount_nok"), int) and isinstance(requested, int)
                and requested > g["max_amount_nok"]]
        if not need:
            errors.append("amount_note_required, but no planned grant has a max below the requested amount")
    for gid in need or []:
        note = (planned.get(gid) or {}).get("amount_note")
        if not (isinstance(note, str) and note.strip()):
            errors.append(f"{gid}: amount_note missing")
    return errors


def run_case(case, runs, log):
    req = case / "input_request.json"
    exp = read_json(case / "expected.json")
    if exp is None:
        return {"case": case.name, "runs": [], "passed": False,
                "error": "no valid expected.json (the Author writes it before the first run)"}
    unknown = set(exp) - KEYS
    if unknown or "expected_exit" not in exp:
        return {"case": case.name, "runs": [], "passed": False,
                "error": f"expected.json: unknown keys {sorted(unknown)} or no expected_exit"}
    requested = (read_json(req) or {}).get("requested_amount_nok")
    env = {**os.environ, "PYTHONUTF8": "1", "GRANTS_DIR": str(CORPUS),
           "EVAL_TODAY": exp.get("today", DEFAULT_TODAY), "EXPECTED_MATCHES": ""}
    results = []
    for k in range(1, runs + 1):
        r = subprocess.run([sys.executable, str(RUN), str(req), "--offline"], cwd=ROOT, env=env,
                           capture_output=True, text=True, encoding="utf-8")
        out = snapshot()
        errors = grade(exp, r.returncode, out, requested)
        cost = sum(c.get("total_cost_usd") or 0 for c in out["costs"])
        results.append({"run": k, "exit": r.returncode, "passed": not errors, "errors": errors,
                        "model_calls": len(out["costs"]), "cost_usd": round(cost, 4)})
        log.write(f"\n===== {case.name} run {k}/{runs}: exit {r.returncode}, "
                  f"{'PASS' if not errors else 'FAIL'} =====\n{r.stdout}{r.stderr}")
        for e in errors:
            log.write(f"  FAIL: {e}\n")
        log.flush()
        print(f"  {case.name} run {k}: {'PASS' if not errors else 'FAIL'} (exit {r.returncode})", flush=True)
        if not out["costs"]:
            break  # never reached the model: deterministic, one run is enough
    return {"case": case.name, "today": env["EVAL_TODAY"], "runs": results,
            "pass_rate": f"{sum(x['passed'] for x in results)}/{len(results)}",
            "passed": all(x["passed"] for x in results)}


def main(argv):
    parser = argparse.ArgumentParser(description="Run every eval case against the frozen corpus")
    parser.add_argument("--case", action="append", help="run only this case folder (repeatable)")
    parser.add_argument("--runs", type=int, default=3, help="runs per case that calls the model (default 3)")
    args = parser.parse_args(argv)

    cases = sorted(p for p in CASES.iterdir() if p.is_dir()) if CASES.exists() else []
    if args.case:
        cases = [c for c in cases if c.name in args.case]
    if not cases:
        print("FAIL: no cases found in eval/cases/", file=sys.stderr)
        return 1

    LOGS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_path = LOGS / f"eval_{stamp}.log"
    with open(log_path, "w", encoding="utf-8") as log:
        log.write(f"python eval/run_eval.py {' '.join(argv)}\nstarted {stamp}, GRANTS_DIR={CORPUS.as_posix()}\n")
        report = [run_case(c, args.runs, log) for c in cases]

        width = max(len(r["case"]) for r in report)
        lines = [f"{'case':<{width}}  {'pass':>5}  result  detail"]
        for r in report:
            first = r.get("error") or next((e for x in r["runs"] for e in x["errors"]), "")
            lines.append(f"{r['case']:<{width}}  {r.get('pass_rate', '0/0'):>5}  "
                         f"{'PASS' if r['passed'] else 'FAIL':<6}  {first}")
        n_pass = sum(r["passed"] for r in report)
        cost = sum(x["cost_usd"] for r in report for x in r["runs"])
        lines.append(f"total: {n_pass}/{len(report)} cases passed, model cost {cost:.2f} USD")
        table = "\n".join(lines)
        print(table)
        log.write(f"\n{table}\n")

    OUT.mkdir(exist_ok=True)
    with open(OUT / "eval_report.json", "w", encoding="utf-8") as f:
        json.dump({"generated": stamp, "grants_dir": CORPUS.as_posix(), "cases": report,
                   "passed": n_pass, "total": len(report), "cost_usd": round(cost, 4)},
                  f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"report: out/eval_report.json, log: {log_path.relative_to(ROOT).as_posix()}")
    return 0 if n_pass == len(report) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
