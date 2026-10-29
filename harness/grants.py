"""Stage 2: load the curated grant context files (task 002).

Usage: python harness/grants.py

Reads context/grants/*.md (innlandet-grants format) and lists them.
Standard library only, no YAML: a simple `key: value` frontmatter parser.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRANTS = ROOT / "context" / "grants"

LIST_KEYS = ("applicant_orgforms", "deadlines")
BOOL_KEYS = ("requires_frivillighetsregisteret",)
HEADINGS = ("Formål", "Hvem kan søke", "Hva kan det søkes om",
            "Vedlegg", "Frister og rapportering")


class GrantFormatError(ValueError):
    pass


def split_frontmatter(text, name):
    """Return (frontmatter str, body str) for a file that starts with a --- block."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise GrantFormatError(f"{name}: no frontmatter")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[1:i]), "".join(lines[i + 1:])
    raise GrantFormatError(f"{name}: frontmatter not closed with ---")


def parse_meta(block, name):
    meta = {}
    for line in block.splitlines():
        line = re.sub(r"\s+#\s.*$", "", line).strip()  # drop "  # comment"
        if not line:
            continue
        if ":" not in line:
            raise GrantFormatError(f"{name}: bad frontmatter line: {line!r}")
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    for key in LIST_KEYS:
        meta[key] = [v.strip() for v in meta.get(key, "").split(",") if v.strip()]
    for key in BOOL_KEYS:
        if key in meta:
            meta[key] = meta[key] == "true"
    amount = meta.get("max_amount_nok", "unknown")
    meta["max_amount_nok"] = int(amount) if amount.isdigit() else "unknown"
    return meta


def parse_sections(body):
    """Map each `## heading` to its text, verbatim apart from surrounding blank lines."""
    sections = {}
    current = None
    for line in body.splitlines(keepends=True):
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = ""
        elif current is not None:
            sections[current] += line
    return {k: v.strip("\n") for k, v in sections.items()}


def parse_grant(path):
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    block, body = split_frontmatter(text, path.name)
    grant = parse_meta(block, path.name)
    grant["body"] = body
    grant["sections"] = parse_sections(body)
    return grant


def load_grants(directory=GRANTS):
    """All grants in directory, sorted by id."""
    grants = [parse_grant(p) for p in sorted(Path(directory).glob("*.md"))]
    return sorted(grants, key=lambda g: g.get("id", ""))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    for g in load_grants():
        missing = [h for h in HEADINGS if h not in g["sections"]]
        note = f"  (missing {missing})" if missing else ""
        print(f"{g['id']}: {g.get('title', '')}{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
