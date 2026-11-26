"""Build the demo bundles for the GitHub Pages version of the web UI (task 017).

Usage: python web/snapshot.py [--cases gjovik_ski,outside_innlandet]

Runs `python harness/run.py <request> --offline` for each demo case and writes
web/demo/<case>.json (web/bundle.py) and web/demo/index.json. Cases that reach stages 4-5 call
`claude` and cost model money, so a person runs this and commits the result; CI only deploys it.
Existing bundles of cases not selected are kept. Standard library only.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import bundle

WEB = Path(__file__).resolve().parent
ROOT = WEB.parent
DEMO = WEB / "demo"

# id, request file, chip label (no / en)
CASES = [
    ("gjovik_ski", "demo/01_gjovik_ski_event.json",
     "Skifestival for juniorer i Gjøvik", "Junior ski festival in Gjøvik"),
    ("faaberg_outdoor", "demo/02_faaberg_outdoor.json",
     "Turdager for familier i Lillehammer", "Outdoor days for families in Lillehammer"),
    ("climbing_holds", "demo/audience.json",
     "Nye klatretak til buldrerommet", "New climbing holds for the bouldering room"),
    ("outside_innlandet", "demo/03_outside_innlandet.json",
     "Klubb utenfor Innlandet", "Club outside Innlandet"),
    ("bad_checksum", "fixtures/input_bad_checksum.json",
     "Feil i organisasjonsnummeret", "Typo in the organisation number"),
]


def run_case(case_id, req_file):
    req_path = ROOT / req_file
    with open(req_path, encoding="utf-8") as f:
        request = json.load(f)
    # eval/check_matches.py grades against fixtures/expected_matches.json (the Hamar request)
    # unless EXPECTED_MATCHES says otherwise: use the case's own author expectations, if any.
    expected = req_path.with_name(req_path.name.replace(".json", ".expected.json"))
    env = {**os.environ, "PYTHONUTF8": "1",
           "EXPECTED_MATCHES": str(expected) if expected.exists() else ""}
    r = subprocess.run([sys.executable, str(ROOT / "harness" / "run.py"), str(req_path), "--offline"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
    lines = r.stdout.splitlines()
    print(f"{case_id}: exit {r.returncode}")
    for line in lines + r.stderr.splitlines():
        print(f"    {line}")
    result = bundle.build(request, r.returncode, lines, "demo")
    result["case"] = case_id
    return result


def main(argv):
    parser = argparse.ArgumentParser(description="Build web/demo/ bundles (task 017)")
    parser.add_argument("--cases", help="comma-separated case ids (default: all)")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    wanted = set(args.cases.split(",")) if args.cases else {c[0] for c in CASES}
    unknown = wanted - {c[0] for c in CASES}
    if unknown:
        print(f"unknown case ids: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 1
    DEMO.mkdir(exist_ok=True)
    failed = []
    for case_id, req_file, *_ in CASES:
        if case_id not in wanted:
            continue
        result = run_case(case_id, req_file)
        if result["exit"] not in (0, 3):
            failed.append(case_id)  # never publish a failed run as a demo
            continue
        with open(DEMO / f"{case_id}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write("\n")
    index = [{"id": cid, "label": {"no": no, "en": en}}
             for cid, _, no, en in CASES if (DEMO / f"{cid}.json").exists()]
    with open(DEMO / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write("\n")
    if failed:
        print(f"not saved (exit 1 or 4): {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
