"""Collect the output files of one run into a single JSON bundle for the web page (task 017).

Reads out/ (stage output files) and the frontmatter of context/grants/ (grant titles), never
stage code. Used by web/server.py (live) and web/snapshot.py (demo files for GitHub Pages).
Standard library only.
"""

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
GRANTS = ROOT / "context" / "grants"

# Only these entity fields reach the browser (out/entity.json has no address, keep it that way).
ENTITY_FIELDS = ("organisasjonsnummer", "navn", "organisasjonsform", "kommunenummer",
                 "registrertIFrivillighetsregisteret", "fetched_at")

# One line of harness/run.py stdout per finished stage, e.g.
# "[4] matcher  attempt 1/3 (0.12 USD)  check PASS" or "[1] entity  check PASS".
STAGE_LINE = re.compile(r"^\[(\d)\]\s+(\w+)\s+(?:attempt (\d)/(\d) \(([^)]*)\)\s+)?check (PASS|FAIL)")


def read_json(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_text(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def frontmatter(path):
    """The `key: value` frontmatter of a grant file as a dict."""
    text = read_text(path) or ""
    m = re.match(r"---\n(.*?)\n---", text.replace("\r\n", "\n"), flags=re.S)
    fields = {}
    for line in (m.group(1).splitlines() if m else []):
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def grant_index():
    """grant_id -> {title, url} from context/grants/*.md."""
    index = {}
    for path in sorted(GRANTS.glob("*.md")) if GRANTS.exists() else []:
        fm = frontmatter(path)
        gid = fm.get("id") or path.stem
        index[gid] = {"title": fm.get("title") or gid, "url": fm.get("url"),
                      "fetched_at": fm.get("fetched_at")}
    return index


def parse_stages(lines):
    """Stage progress from run.py stdout: [{n, name, status, attempt, attempts, cost}]."""
    stages = {}
    for line in lines:
        m = STAGE_LINE.match(line.strip())
        if not m:
            continue
        n, name, attempt, attempts, cost, verdict = m.groups()
        stages[int(n)] = {"n": int(n), "name": name, "status": verdict.lower(),
                          "attempt": int(attempt) if attempt else None,
                          "attempts": int(attempts) if attempts else None, "cost": cost}
    return [stages[k] for k in sorted(stages)]


def total_cost():
    path = OUT / "cost_log.jsonl"
    if not path.exists():
        return 0.0
    with open(path, encoding="utf-8") as f:
        return round(sum(json.loads(l).get("total_cost_usd") or 0 for l in f if l.strip()), 4)


def excluded_grants(titles):
    """Grants the club does not qualify for: filter rule (stage 3) or matcher reason (stage 4)."""
    excluded = []
    eligible = read_json(OUT / "eligible.json") or {}
    for r in eligible.get("rejected", []):
        g = titles.get(r["grant_id"], {})
        excluded.append({"grant_id": r["grant_id"], "title": g.get("title", r["grant_id"]),
                         "url": g.get("url"), "stage": "filter", "reason": r["reason"]})
    matches = read_json(OUT / "matches.json") or {}
    for m in matches.get("matches", []):
        if m.get("verdict") != "reject":
            continue
        g = titles.get(m["grant_id"], {})
        excluded.append({"grant_id": m["grant_id"], "title": g.get("title", m["grant_id"]),
                         "url": g.get("url"), "stage": "matcher", "reason": m.get("reason", "")})
    return excluded


def halted_reason(text):
    """The `reason:` line of out/HALTED, or None."""
    for line in (text or "").splitlines():
        if line.startswith("reason:"):
            return line.partition(":")[2].strip()
    return None


def build(request, exit_code, log_lines, mode):
    """The bundle for the run that just wrote out/."""
    entity = read_json(OUT / "entity.json")
    plan = read_json(OUT / "plan.json") if exit_code == 0 else None
    titles = grant_index()
    halted = read_text(OUT / "HALTED") if exit_code == 4 else None
    return {
        "mode": mode,
        "generated": date.today().isoformat(),
        "request": request,
        "exit": exit_code,
        "stages": parse_stages(log_lines),
        "entity": {k: entity.get(k) for k in ENTITY_FIELDS} if entity else None,
        "plan": plan,
        "fetched_at": max((titles.get(g["grant_id"], {}).get("fetched_at") or ""
                           for g in plan["grants"]), default="") or None if plan else None,
        "markdown": read_text(OUT / "grant_action_plan.md") if plan else None,
        "rejection": read_json(OUT / "rejection.json"),
        "halted": halted_reason(halted),
        "excluded": excluded_grants(titles),
        "cost_usd": total_cost(),
    }
