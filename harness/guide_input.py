"""Stage 5 input: copy the matched grants for the guide writer (task 005).

Usage: python harness/guide_input.py input_request.json

Reads out/matches.json and out/eligible.json, copies context/grants/<id>.md for every
matched grant to out/guide_input/, and writes out/guide_input/request.json (exit 0),
or out/rejection.json when no grant matched (exit 3). Standard library only, no LLM.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
GRANTS = ROOT / "context" / "grants"
GUIDE_INPUT = OUT / "guide_input"


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
    for name, stage in (("matches.json", "stage 4 (matcher)"), ("eligible.json", "stage 3 (harness/filter.py)")):
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

    GUIDE_INPUT.mkdir(parents=True)
    for gid in matched:
        shutil.copyfile(GRANTS / f"{gid}.md", GUIDE_INPUT / f"{gid}.md")
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
