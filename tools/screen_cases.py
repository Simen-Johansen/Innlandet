"""Screen every eval case against new grants with the deterministic stages only (task 017, step 4 and 8).

  python tools/screen_cases.py --add docs/grant-expansion/grants   step 4: rows for (case, new grant) into
                                                                   docs/grant-expansion/decisions.tsv
  python tools/screen_cases.py                                     step 8: screen eval/corpus/grants/ and check
                                                                   every decided must_reject row
  options: --grants-dir DIR (base corpus, default eval/corpus/grants), --cases DIR, --tsv FILE,
           --show-current (a human may print each case's current must_match / must_reject)

For each case: stage 1 (harness/entity.py --offline, Brreg fixtures) and stage 3 (harness/filter.py --today
<case today>) as subprocesses, with GRANTS_DIR = a temporary corpus (base + --add files, deleted after). No model
call, no network. Both stages write into out/, so out/ is snapshotted before and restored exactly after.
From expected.json the code reads only today, expected_exit, rejection_reason and fault; it never prints the
must_match / must_reject lists unless --show-current. Writes nothing under eval/ or context/.
Re-running keeps proposal, why, reason, decision and decided_by already in the TSV. Standard library only.
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "eval" / "cases"
CORPUS = ROOT / "eval" / "corpus" / "grants"
TSV = ROOT / "docs" / "grant-expansion" / "decisions.tsv"
OUT = ROOT / "out"
ENTITY = ROOT / "harness" / "entity.py"
FILTER = ROOT / "harness" / "filter.py"
DEFAULT_TODAY = "2026-11-05"  # = eval/run_eval.py
FACT_KEYS = ("applicant_orgforms", "requires_frivillighetsregisteret", "region_prefix", "target_group",
             "max_amount_nok", "deadlines", "verified_by")
COLUMNS = ("case", "grant_id", "filter", "reaches_matcher_now", "reached_matcher_before", "today", "kommunenummer",
           "orgform", "frivillighetsregisteret", "project_idea", "proposal", "why", "reason", "decision",
           "decided_by")
HUMAN_COLUMNS = ("proposal", "why", "reason", "decision", "decided_by")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def front(path):
    """{key: value} of a grant file's frontmatter (comments dropped)."""
    meta = {}
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for line in lines[1:]:
        if line.strip() == "---":
            break
        line = re.sub(r"\s+#\s.*$", "", line).strip()
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def unfinished(path):
    meta = front(path)
    return [k for k in FACT_KEYS if meta.get(k, "TODO") in ("", "TODO")]


def case_meta(case_dir):
    """Only the fields screening needs; the expectation lists are never returned."""
    exp = read_json(case_dir / "expected.json")
    exits = {int(n) for n in re.findall(r"\d+", json.dumps(exp.get("expected_exit", "")))}
    if exp.get("fault") or exp.get("rejection_reason"):
        before = "no"
    elif 3 in exits:
        before = "maybe"
    else:
        before = "yes"
    return {"today": exp.get("today", DEFAULT_TODAY), "before": before, "fault": bool(exp.get("fault"))}


def current_lists(case_dir):
    exp = read_json(case_dir / "expected.json")
    return exp.get("must_match", []), exp.get("must_reject", [])


def snapshot(out_dir, keep):
    if out_dir.exists():
        shutil.copytree(out_dir, keep / "out", copy_function=shutil.copy2)


def restore(out_dir, keep):
    if out_dir.exists():
        shutil.rmtree(out_dir)
    if (keep / "out").exists():
        shutil.copytree(keep / "out", out_dir, copy_function=shutil.copy2)


def run_case(case_dir, today, env, out_dir=OUT):
    """(entity dict or None, {grant_id: 'kept' | reason}, stage-1 rejection reason or '')."""
    req = case_dir / "input_request.json"
    p = subprocess.run([sys.executable, str(ENTITY), str(req), "--offline"], env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        rej = out_dir / "rejection.json"
        reason = read_json(rej).get("reason", "") if rej.exists() else f"exit {p.returncode}"
        return None, {}, reason or f"exit {p.returncode}"
    entity = read_json(out_dir / "entity.json")
    p = subprocess.run([sys.executable, str(FILTER), str(req), "--today", today], env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    eligible = out_dir / "eligible.json"
    if p.returncode not in (0, 3) or not eligible.exists():
        return entity, {}, f"filter exit {p.returncode}: {p.stderr.strip()[-200:]}"
    data = read_json(eligible)
    result = {g: "kept" for g in data.get("kept", [])}
    result.update({r["grant_id"]: r["reason"] for r in data.get("rejected", [])})
    return entity, result, ""


def idea_of(case_dir):
    try:
        idea = read_json(case_dir / "input_request.json").get("project_idea") or ""
    except (OSError, ValueError):
        return ""
    idea = " ".join(str(idea).split())
    return idea if len(idea) <= 160 else idea[:157] + "..."


def screen(cases_dir, base_dir, add_dir=None, out_dir=OUT):
    """[(case, grant_id, row dict)] for every case and grant (only the --add grants when add_dir is given)."""
    add_files = sorted(Path(add_dir).glob("*.md")) if add_dir else []
    add_files = [p for p in add_files if not p.name.endswith(".checklist.md")]
    todo = {p.stem: unfinished(p) for p in add_files}
    todo = {g: k for g, k in todo.items() if k}
    if todo:
        lines = [f"  {g}: {', '.join(k)}" for g, k in todo.items()]
        raise SystemExit("refused: facts still TODO (step 2 first, humans fill them):\n" + "\n".join(lines))
    rows = []
    with tempfile.TemporaryDirectory(prefix="screen_") as tmp:
        tmp = Path(tmp)
        corpus = tmp / "grants"
        corpus.mkdir()
        for p in sorted(Path(base_dir).glob("*.md")):
            shutil.copy2(p, corpus / p.name)
        for p in add_files:
            shutil.copy2(p, corpus / p.name)
        wanted = [p.stem for p in add_files] or sorted(p.stem for p in corpus.glob("*.md"))
        env = {k: v for k, v in os.environ.items() if k not in ("FAULT", "EXPECTED_MATCHES")}
        env.update(PYTHONUTF8="1", GRANTS_DIR=str(corpus))
        keep = tmp / "keep"
        keep.mkdir()
        snapshot(out_dir, keep)
        try:
            for case in sorted(d for d in Path(cases_dir).iterdir() if (d / "expected.json").exists()):
                meta = case_meta(case)
                if meta["fault"]:
                    entity, result, stop = None, {}, "fault case (outage test): never reaches stage 3"
                else:
                    entity, result, stop = run_case(case, meta["today"], env, out_dir)
                now = "yes" if any(v == "kept" for v in result.values()) else "no"
                for gid in wanted:
                    if stop:
                        verdict = f"stage 1: {stop}" if entity is None else stop
                    elif result.get(gid) == "kept":
                        verdict = "kept: matcher decides"
                    else:
                        verdict = f"filtered: {result.get(gid, 'not loaded')}"
                    rows.append({
                        "case": case.name, "grant_id": gid, "filter": verdict, "reaches_matcher_now": now,
                        "reached_matcher_before": meta["before"], "today": meta["today"],
                        "kommunenummer": (entity or {}).get("kommunenummer", ""),
                        "orgform": (entity or {}).get("organisasjonsform", ""),
                        "frivillighetsregisteret": str((entity or {}).get("registrertIFrivillighetsregisteret", "")),
                        "project_idea": idea_of(case)})
        finally:
            restore(out_dir, keep)
    return rows


def read_tsv(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_tsv(path, rows):
    old = {(r["case"], r["grant_id"]): r for r in read_tsv(path)}
    for r in rows:
        prev = old.pop((r["case"], r["grant_id"]), {})
        for c in HUMAN_COLUMNS:
            r[c] = prev.get(c, "")
    kept_old = [r for r in old.values() if any(r.get(c) for c in HUMAN_COLUMNS)]  # never drop a human decision
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in rows + kept_old:
            w.writerow({c: r.get(c, "") for c in COLUMNS})
    return len(kept_old)


def verify(rows, tsv):
    """Step 8: every decided must_reject row with a filter reason must be filtered with that reason."""
    got = {(r["case"], r["grant_id"]): r["filter"] for r in rows}
    bad = 0
    for d in read_tsv(tsv):
        if d.get("decision") != "must_reject" or not d.get("decided_by"):
            continue
        now = got.get((d["case"], d["grant_id"]), "not screened")
        want = d.get("reason", "")
        ok = (now == f"filtered: {want}") if want else True
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {d['case']} {d['grant_id']}: decided must_reject"
              f"{' (' + want + ')' if want else ' (filter or matcher)'}; now {now}")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description="Screen eval cases with stages 1 and 3 (task 017)")
    ap.add_argument("--add", help="folder with new grant files (facts filled)")
    ap.add_argument("--grants-dir", default=str(CORPUS))
    ap.add_argument("--cases", default=str(CASES))
    ap.add_argument("--tsv", default=str(TSV))
    ap.add_argument("--show-current", action="store_true", help="humans only: print current expectations")
    a = ap.parse_args(argv)
    rows = screen(Path(a.cases), Path(a.grants_dir), a.add)
    for r in rows:
        print(f"{r['case']:<36} {r['grant_id']:<48} {r['filter']:<40} kn={r['kommunenummer']} {r['orgform']} "
              f"frivreg={r['frivillighetsregisteret']} | {r['project_idea'][:70]}")
    if a.show_current:
        for case in sorted(d for d in Path(a.cases).iterdir() if (d / "expected.json").exists()):
            mm, mr = current_lists(case)
            print(f"current {case.name}: must_match={mm} must_reject={mr}")
    if a.add:
        kept = write_tsv(Path(a.tsv), rows)
        print(f"{len(rows)} rows -> {a.tsv}" + (f" (+{kept} older decided rows kept)" if kept else ""))
        return 0
    bad = verify(rows, Path(a.tsv))
    print(f"{len(rows)} (case, grant) screened; {bad} decided must_reject row(s) not filtered as decided")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
