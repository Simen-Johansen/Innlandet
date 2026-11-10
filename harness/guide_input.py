"""Stage 5 input: copy the matched grants for the guide writer (task 005).

Usage: python harness/guide_input.py input_request.json

Reads out/matches.json, out/eligible.json and out/match_input.md, copies context/grants/<id>.md
(or GRANTS_DIR) for every matched grant to out/guide_input/ with the body wrapped in
<grant_text> tags, and writes out/guide_input/request.json (exit 0), or out/rejection.json when no
grant matched (exit 3). Quote guard (task 012): a match whose evidence_quote is not in that grant's
Formål / Hva kan det søkes om text as the matcher saw it, or quotes an injected instruction,
stops the run (exit 1). Standard library only, no LLM.
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from grants import GRANTS, split_frontmatter, strip_data_tags

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
GUIDE_INPUT = OUT / "guide_input"
GRANT_BLOCK = re.compile(r'<grant_text id="([^"]+)">\n(.*?)\n</grant_text>', flags=re.S)
INSTRUCTION = re.compile(
    r"\b(ignore|disregard|forget)\b.{0,30}\b(instructions?|rules?)\b|mark this grant|as a match"
    r"|\bignorer\b.{0,30}\b(instruksjon|instruksjoner|regler)\b",
    flags=re.I,
)


def norm(text):
    return " ".join(text.split())


def quote_problem(match, blocks):
    """Why this match's evidence_quote does not back it up, or None if it does."""
    gid, quote = match["grant_id"], norm(match.get("evidence_quote") or "")
    block = blocks.get(gid)
    if block is None:
        return f"{gid}: no <grant_text> block in out/match_input.md"
    if not quote or quote not in norm(block):
        return f"{gid}: evidence_quote is not in the Formål / Hva kan det søkes om text the matcher saw"
    lines = [line for line in block.splitlines() if quote in norm(line)] or [quote]
    if any(INSTRUCTION.search(line) for line in lines):
        return f"{gid}: evidence_quote comes from a line holding an injected instruction"
    return None


def copy_wrapped(gid):
    """Copy the grant file; frontmatter as is, body inside <grant_text> tags."""
    path = GRANTS / f"{gid}.md"
    with open(path, encoding="utf-8") as f:
        block, body = split_frontmatter(f.read(), path.name)
    with open(GUIDE_INPUT / f"{gid}.md", "w", encoding="utf-8") as f:
        f.write(f'---\n{block}---\n\n<grant_text id="{gid}">\n{strip_data_tags(body).strip()}\n</grant_text>\n')


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv):
    parser = argparse.ArgumentParser(description="Stage 5 input: copy matched grants")
    parser.add_argument("request", help="input_request.json")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    shutil.rmtree(GUIDE_INPUT, ignore_errors=True)
    (OUT / "plan.json").unlink(missing_ok=True)
    for name, stage in (("matches.json", "stage 4 (matcher)"), ("eligible.json", "stage 3 (harness/filter.py)"),
                        ("match_input.md", "stage 3 (harness/filter.py)")):
        if not (OUT / name).exists():
            print(f"out/{name} missing: run {stage} first", file=sys.stderr)
            return 2
    request = read_json(Path(args.request))
    matches = read_json(OUT / "matches.json")
    eligible = read_json(OUT / "eligible.json")

    matched = [m["grant_id"] for m in matches["matches"] if m["verdict"] == "match"]
    if not matched:
        detail = f"none of the {len(matches['matches'])} kept grants fits the project idea"
        write_json(OUT / "rejection.json", {"reason": "no_matching_grants", "detail": detail})
        print(f"rejected: no_matching_grants: {detail}", file=sys.stderr)
        return 3

    with open(OUT / "match_input.md", encoding="utf-8") as f:
        blocks = dict(GRANT_BLOCK.findall(f.read()))
    problems = [p for m in matches["matches"] if m["verdict"] == "match" and (p := quote_problem(m, blocks))]
    if problems:
        for p in problems:
            print(f"quote guard: {p}", file=sys.stderr)
        return 1

    GUIDE_INPUT.mkdir(parents=True)
    for gid in matched:
        copy_wrapped(gid)
    write_json(GUIDE_INPUT / "request.json", {
        "output_language": request["output_language"],
        "requested_amount_nok": request.get("requested_amount_nok"),
        "project_idea": request.get("project_idea", ""),
        "today": eligible["today"],
    })
    print(f"ok: {len(matched)} matched grant(s) copied to out/guide_input/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
