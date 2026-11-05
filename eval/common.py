"""Small helpers shared by the checks. Standard library only.

The checks deliberately do NOT import harness/ code (except check_grants' last
assertion): a check that reuses the code under test cannot catch its bugs.
"""
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
FIXTURES = ROOT / "fixtures"
# Overridable so the evaluation harness can run against a frozen corpus (task 009):
#   GRANTS_DIR=eval/corpus/grants  EVAL_TODAY=2026-11-05
GRANTS = Path(os.environ.get("GRANTS_DIR") or ROOT / "context" / "grants")
if not GRANTS.is_absolute():
    GRANTS = ROOT / GRANTS
CONTEXT = ROOT / "context"

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# +47 numbers, 8 digits as 2-2-2-2 or 3-2-3, or plain 8 digits. May give false
# positives on 8-digit amounts; that is a known, documented trade-off.
PHONE = re.compile(r"\+47[\s\d]{8,11}|\b\d{2}\s\d{2}\s\d{2}\s\d{2}\b|\b\d{3}\s\d{2}\s\d{3}\b|\b\d{8}\b")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def load_json(path):
    path = Path(path)
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    check(path.exists(), f"{shown} does not exist")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"{shown} is not valid JSON: {e}")


def mod11_ok(orgnr):
    if not re.fullmatch(r"\d{9}", str(orgnr)):
        return False
    weights = [3, 2, 7, 6, 5, 4, 3, 2]
    s = sum(int(d) * w for d, w in zip(orgnr[:8], weights))
    c = 11 - s % 11
    c = 0 if c == 11 else c
    return c != 10 and c == int(orgnr[8])


def parse_grant(path):
    """Return (frontmatter dict, body str). Independent of harness/grants.py."""
    text = Path(path).read_text(encoding="utf-8")
    check(text.startswith("---"), f"{Path(path).name}: no frontmatter")
    parts = text.split("---", 2)
    check(len(parts) == 3, f"{Path(path).name}: frontmatter not closed with ---")
    meta = {}
    for line in parts[1].strip().splitlines():
        line = re.sub(r"\s+#\s.*$", "", line).strip()  # drop "  # comment"
        if not line:
            continue
        check(":" in line, f"{Path(path).name}: bad frontmatter line: {line!r}")
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, parts[2]


def as_list(value):
    return [v.strip() for v in value.split(",") if v.strip()]


def today():
    """The reference date for staleness checks: EVAL_TODAY if set, else the real date."""
    value = os.environ.get("EVAL_TODAY")
    return date.fromisoformat(value) if value else date.today()


def domain(url):
    """Host of an https URL without a leading www."""
    host = re.sub(r"^https?://", "", url).split("/", 1)[0].split(":", 1)[0].lower()
    return host[4:] if host.startswith("www.") else host


def page_id(url):
    """Numeric page id in innlandetfylke.no URLs (".../slug.36453.aspx" -> "36453"), else None.
    The same grant can be listed under two paths; the id is stable."""
    m = re.search(r"\.(\d+)\.aspx", url)
    return m.group(1) if m else None
