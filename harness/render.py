"""Stage 6: render the plan as Markdown (task 006).

Usage: python harness/render.py

Reads out/plan.json and the fetched_at date from out/guide_input/<grant_id>.md, and writes
out/grant_action_plan.md. Standard library only, no LLM; same input gives the same bytes.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
GUIDE_INPUT = OUT / "guide_input"

LABELS = {
    "en": {
        "title": "Grant action plan",
        "orgnr": "Organisation number",
        "generated": "Generated",
        "disclaimer": "Checked automatically against the official sources fetched on {fetched_at}. "
                      "Always confirm the deadline on the grant page before applying.",
        "deadline": "Deadline",
        "max_amount": "Max amount",
        "unknown_amount": "Not stated on the grant page",
        "why": "Why your club qualifies",
        "attachments": "Attachments",
        "steps": "Steps",
    },
    "no": {
        "title": "Søknadsplan for tilskudd",
        "orgnr": "Organisasjonsnummer",
        "generated": "Generert",
        "disclaimer": "Automatisk kontrollert mot de offisielle kildene hentet {fetched_at}. "
                      "Bekreft alltid fristen på tilskuddssiden før dere søker.",
        "deadline": "Søknadsfrist",
        "max_amount": "Maksbeløp",
        "unknown_amount": "Ikke oppgitt på tilskuddssiden",
        "why": "Hvorfor dere kvalifiserer",
        "attachments": "Vedlegg",
        "steps": "Steg",
    },
}


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_fetched_at(path):
    """The fetched_at value from a grant file's `key: value` frontmatter, or None."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        line = re.sub(r"\s+#\s.*$", "", line).strip()  # drop "  # comment"
        key, _, value = line.partition(":")
        if key.strip() == "fetched_at" and value.strip():
            return date.fromisoformat(value.strip())
    return None


def fmt_date(d):
    return d.strftime("%d.%m.%Y")


def fmt_amount(amount, labels):
    if isinstance(amount, int):
        return f"{amount:,} NOK".replace(",", " ")
    return labels["unknown_amount"]


def render_markdown(plan, fetched_at, today):
    labels = LABELS[plan["output_language"]]
    lines = [
        f"# {labels['title']}: {plan['org_name']}",
        "",
        f"{labels['orgnr']}: {plan['orgnr']}  ",
        f"{labels['generated']}: {fmt_date(today)}",
        "",
        labels["disclaimer"].format(fetched_at=fmt_date(fetched_at)),
    ]
    for g in plan["grants"]:
        deadline = date.fromisoformat(g["application_deadline"])
        lines += [
            "",
            f"## [{g['title']}]({g['url']})",
            "",
            f"- **{labels['deadline']}:** {fmt_date(deadline)}",
            f"- **{labels['max_amount']}:** {fmt_amount(g['max_amount_nok'], labels)}",
        ]
        if isinstance(g.get("amount_note"), str) and g["amount_note"].strip():
            lines.append(f"  {g['amount_note'].strip()}")
        lines += ["", f"### {labels['why']}", "", g["why_qualifies"].strip(),
                  "", f"### {labels['attachments']}", ""]
        lines += [f"- [ ] {a}" for a in g["attachments"]]
        lines += ["", f"### {labels['steps']}", ""]
        lines += [f"{i}. {s}" for i, s in enumerate(g["steps"], 1)]
    return "\n".join(lines) + "\n"


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    if not (OUT / "plan.json").exists():
        print("out/plan.json missing: run stage 5 (guide writer) first", file=sys.stderr)
        return 2
    plan = read_json(OUT / "plan.json")

    fetched = []
    for g in plan["grants"]:
        path = GUIDE_INPUT / f"{g['grant_id']}.md"
        d = read_fetched_at(path) if path.exists() else None
        if d is None:
            print(f"no fetched_at for {g['grant_id']} in out/guide_input/: run stage 5 input first",
                  file=sys.stderr)
            return 2
        fetched.append(d)
    if not fetched:
        print("out/plan.json has no grants: nothing to render", file=sys.stderr)
        return 2

    # The oldest fetch date is the honest claim when sources were fetched on different days
    md = render_markdown(plan, min(fetched), date.today())
    with open(OUT / "grant_action_plan.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    print(f"ok: {len(plan['grants'])} grant(s) rendered to out/grant_action_plan.md")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
