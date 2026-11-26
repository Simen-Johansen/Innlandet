"""Add decided grant ids to eval/cases/*/expected.json with a minimal diff (task 017 step 7; humans run it).

  python tools/add_expectation.py docs/grant-expansion/decisions.tsv --check   (writes nothing)
  python tools/add_expectation.py docs/grant-expansion/decisions.tsv
  options: --cases DIR (default eval/cases), --corpus DIR (default eval/corpus/grants)

Applies only rows with decided_by filled and decision must_match or must_reject. A must_reject row with a
`reason` is added as {"grant_id": ..., "reason": ...} (filter reason), otherwise as the plain id.
Refuses the whole run (writes nothing) if a row's grant is not in the corpus, the id is already in the opposite
list, or the case dir is missing. Minimal diff: the id is inserted into the existing array text and the file's
layout is kept; the result is re-parsed and must equal the old JSON plus exactly that id. If it cannot, that
file is refused and the line to add by hand is printed. An id already in the same list is skipped.
Replaces tools/add_must_reject.py (C4), which re-serialised whole files. Standard library only.
"""
import argparse
import copy
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "eval" / "cases"
CORPUS = ROOT / "eval" / "corpus" / "grants"
LISTS = ("must_match", "must_reject")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def ids_in(items):
    return {i if isinstance(i, str) else i.get("grant_id") for i in items}


def item_text(gid, reason):
    return json.dumps({"grant_id": gid, "reason": reason} if reason else gid, ensure_ascii=False)


def insert(text, key, new):
    """text with `new` (JSON text) appended to the array of `key`, keeping layout; None if not possible."""
    m = re.search(r'"%s"\s*:\s*\[' % re.escape(key), text)
    if not m:
        return None
    depth, i = 1, m.end()
    in_str = False
    while i < len(text) and depth:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
        i += 1
    if depth:
        return None
    close = i - 1  # index of the array's "]"
    inner = text[m.end():close]
    if not inner.strip():  # empty array: [] -> ["id"]
        return text[:m.end()] + new + text[close:]
    last = len(inner.rstrip())  # end of the last item inside the array
    if "\n" not in inner:  # one line: [..., "a"] -> [..., "a", "id"]
        return text[:m.end() + last] + ", " + new + text[m.end() + last:]
    # multi-line: new item on its own line, indented like the last item
    line_start = inner.rfind("\n", 0, last) + 1
    indent = re.match(r"[ \t]*", inner[line_start:]).group(0)
    nl = "\r\n" if "\r\n" in text else "\n"
    return text[:m.end() + last] + "," + nl + indent + new + text[m.end() + last:]


def plan(rows, cases_dir, corpus_dir):
    """({case path: [(list, gid, reason)]}, refusals, skipped)."""
    todo, refusals, skipped = {}, [], []
    for n, r in enumerate(rows, start=2):
        decision, by = (r.get("decision") or "").strip(), (r.get("decided_by") or "").strip()
        if not by or decision not in LISTS:
            continue
        case, gid, reason = r["case"].strip(), r["grant_id"].strip(), (r.get("reason") or "").strip()
        exp = Path(cases_dir) / case / "expected.json"
        where = f"line {n} ({case}, {gid})"
        if not exp.exists():
            refusals.append(f"{where}: case dir missing")
            continue
        if not (Path(corpus_dir) / f"{gid}.md").exists():
            refusals.append(f"{where}: {gid} is not in {Path(corpus_dir).name}/ (copy the grant first)")
            continue
        if reason and decision != "must_reject":
            refusals.append(f"{where}: a reason is only valid for must_reject")
            continue
        with open(exp, encoding="utf-8") as f:
            data = json.load(f)
        other = "must_reject" if decision == "must_match" else "must_match"
        if gid in ids_in(data.get(other, [])):
            refusals.append(f"{where}: already in {other}")
            continue
        if gid in ids_in(data.get(decision, [])):
            skipped.append(f"{where}: already in {decision}")
            continue
        todo.setdefault(exp, []).append((decision, gid, reason))
    return todo, refusals, skipped


def apply(todo, check):
    added, by_hand = 0, []
    for exp, items in sorted(todo.items()):
        with open(exp, encoding="utf-8", newline="") as f:
            text = f.read()
        data = json.loads(text)
        want = copy.deepcopy(data)
        new_text = text
        for key, gid, reason in items:
            want.setdefault(key, []).append({"grant_id": gid, "reason": reason} if reason else gid)
            new_text = insert(new_text, key, item_text(gid, reason)) if new_text is not None else None
        try:
            ok = new_text is not None and json.loads(new_text) == want
        except ValueError:
            ok = False
        case = exp.parent.name
        if not ok:
            for key, gid, reason in items:
                by_hand.append(f"{case}: add {item_text(gid, reason)} to \"{key}\" by hand")
            continue
        for key, gid, _ in items:
            print(f"{'would add' if check else 'added'}: {case} {key} += {gid}")
        added += len(items)
        if not check:
            with open(exp, "w", encoding="utf-8", newline="") as f:
                f.write(new_text)
    return added, by_hand


def main(argv=None):
    ap = argparse.ArgumentParser(description="Add decided ids to expected.json, minimal diff (task 017)")
    ap.add_argument("tsv")
    ap.add_argument("--check", action="store_true", help="print what would change, write nothing")
    ap.add_argument("--cases", default=str(CASES))
    ap.add_argument("--corpus", default=str(CORPUS))
    a = ap.parse_args(argv)
    with open(a.tsv, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    todo, refusals, skipped = plan(rows, a.cases, a.corpus)
    for s in skipped:
        print(f"skip: {s}")
    if refusals:
        for r in refusals:
            print(f"REFUSED: {r}")
        print(f"refused: {len(refusals)} row(s); nothing written")
        return 2
    added, by_hand = apply(todo, a.check)
    for line in by_hand:
        print(f"REFUSED FILE: {line}")
    print(f"{added} id(s) {'would be added' if a.check else 'added'}"
          f"{f'; {len(by_hand)} to add by hand' if by_hand else ''}")
    return 1 if by_hand else 0


if __name__ == "__main__":
    sys.exit(main())
