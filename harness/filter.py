"""Stage 3: deterministic eligibility filter (task 003).

Usage: python harness/filter.py input_request.json [--today YYYY-MM-DD]

Reads out/entity.json and context/grants/, writes out/eligible.json and
out/match_input.md (exit 0), or out/rejection.json when no grant survives (exit 3).
Standard library only, no LLM.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from grants import load_grants

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"

MATCH_SECTIONS = ("Formål", "Hva kan det søkes om")
# Lines the matcher must never see: URLs, money amounts, ISO dates.
LEAKY_LINE = re.compile(
    r"https?://|www\."
    r"|\d[\d\s.,]*\s?(kr|kroner|NOK)\b|\b(kr|kroner|NOK)\.?\s?\d"
    r"|\d{4}-\d{2}-\d{2}",
    flags=re.I,
)


def org_form_not_allowed(entity, grant, today):
    return entity["organisasjonsform"] not in grant["applicant_orgforms"]


def outside_region(entity, grant, today):
    return not str(entity["kommunenummer"]).startswith(grant["region_prefix"])


def not_in_frivillighetsregisteret(entity, grant, today):
    return grant["requires_frivillighetsregisteret"] and not entity["registrertIFrivillighetsregisteret"]


def no_open_deadline(entity, grant, today):
    """A deadline on today still counts as open; no deadlines at all counts as closed."""
    return all(date.fromisoformat(d) < today for d in grant["deadlines"])


RULES = (org_form_not_allowed, outside_region, not_in_frivillighetsregisteret, no_open_deadline)


def rejection_reason(entity, grant, today):
    """Reason code of the first rule that fails, or None if the grant is kept."""
    for rule in RULES:
        if rule(entity, grant, today):
            return rule.__name__
    return None


def scrub(text):
    """Drop whole lines that leak URLs, amounts or dates; kept lines stay verbatim."""
    lines = [line for line in text.splitlines() if not LEAKY_LINE.search(line)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip("\n")


def match_input(idea, grants):
    parts = ["# Project idea", "", scrub(idea), ""]
    for g in grants:
        parts += [f"## Grant: {g['id']}", "", f"Title: {g['title']}", ""]
        for heading in MATCH_SECTIONS:
            parts += [f"### {heading}", "", scrub(g["sections"].get(heading, "")), ""]
    return "\n".join(parts)


def write_json(path, data):
    OUT.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main(argv):
    parser = argparse.ArgumentParser(description="Stage 3: deterministic eligibility filter")
    parser.add_argument("request", help="input_request.json")
    parser.add_argument("--today", type=date.fromisoformat, default=date.today(),
                        help="YYYY-MM-DD (default: real date)")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    for name in ("eligible.json", "match_input.md", "rejection.json", "plan.json"):
        (OUT / name).unlink(missing_ok=True)
    with open(args.request, encoding="utf-8") as f:
        request = json.load(f)
    entity_path = OUT / "entity.json"
    if not entity_path.exists():
        print("out/entity.json missing: run stage 1 (harness/entity.py) first", file=sys.stderr)
        return 2
    with open(entity_path, encoding="utf-8") as f:
        entity = json.load(f)

    kept, rejected = [], []
    for g in load_grants():
        reason = rejection_reason(entity, g, args.today)
        if reason is None:
            kept.append(g)
        else:
            rejected.append({"grant_id": g["id"], "reason": reason})
    write_json(OUT / "eligible.json", {
        "today": args.today.isoformat(),
        "kept": [g["id"] for g in kept],
        "rejected": rejected,
    })

    if not kept:
        detail = f"all {len(rejected)} grants rejected by the hard filter (today {args.today})"
        write_json(OUT / "rejection.json", {"reason": "no_eligible_grants", "detail": detail})
        print(f"rejected: no_eligible_grants: {detail}", file=sys.stderr)
        return 3
    with open(OUT / "match_input.md", "w", encoding="utf-8") as f:
        f.write(match_input(request.get("project_idea", ""), kept))
    print(f"ok: {len(kept)} kept, {len(rejected)} rejected")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
