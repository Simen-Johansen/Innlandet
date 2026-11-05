"""Check for task 015: the weekly grant updater follows its rules on human-written cases.

Each case is a folder fixtures/update_cases/<case>/ with
  grants/<id>.md     starting state (copied to a temp dir, never modified in place)
  pages/<id>.html    the page served offline; a missing page simulates a failed request
  sources.json       optional; else fixtures/update_cases/sources.json
  expected.json      written by a human BEFORE the updater exists:
                     {"today": "YYYY-MM-DD", "grants": {"<id>": "<action>"},
                      "forbidden_strings": ["<fictional name used in the page>"]}

The check runs, per case:
  python harness/update_grants.py --offline --pages-dir P --grants-dir G --pending-dir Q
         --sources S --report R --today T
and expects R = {"today", "requests", "grants": [{"id", "action", "reason",
                 "source_modified_before", "source_modified_now"}]}

Actions and the rule each must obey (facts = the human-verified frontmatter keys below):
  unchanged       same "Sist endret": file identical except checked_at = today
  touched         newer "Sist endret", same text: body identical; source_modified, checked_at updated
  updated_text    newer, text changed but no number/date/amount changed and "Hvem kan søke" and
                  "Frister og rapportering" identical: body replaced, every body line found in the page
  needs_review    a fact may have changed: grant file untouched, draft in the pending dir
  failed          request failed or page not parseable: grant file untouched, reason given
  skipped_manual  domain policy is manual: grant file untouched, no request
In every case: facts never change, no personal data in any written file.

Run: python eval/check_update.py
"""
import html as htmlmod
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import EMAIL, FIXTURES, PHONE, ROOT, check, domain, load_json

ACTIONS = {"unchanged", "touched", "updated_text", "needs_review", "failed", "skipped_manual"}
FACTS = ["id", "title", "url", "provider", "applicant_orgforms", "requires_frivillighetsregisteret",
         "region_prefix", "target_group", "max_amount_nok", "deadlines", "verified_by"]
NUMBER = re.compile(r"\d[\d\s.,]*\d|\d")

updater = ROOT / "harness" / "update_grants.py"
check(updater.exists(), "harness/update_grants.py does not exist")
cases_dir = FIXTURES / "update_cases"
cases = sorted(p for p in cases_dir.glob("*") if p.is_dir()) if cases_dir.exists() else []
check(cases, "no cases in fixtures/update_cases/")


def split(text):
    parts = text.split("---", 2)
    meta = {}
    for line in parts[1].strip().splitlines():
        line = re.sub(r"\s+#\s.*$", "", line).strip()
        if line and ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, parts[2]


def section(body, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", body, flags=re.M | re.S)
    return " ".join(m.group(1).split()) if m else None


def numbers(body):
    return sorted(" ".join(n.split()) for n in NUMBER.findall(body))


def page_text(raw):
    raw = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
    return " ".join(htmlmod.unescape(re.sub(r"<[^>]+>", " ", raw)).split())


total = 0
for case in cases:
    name = case.name
    exp = load_json(case / "expected.json")
    sources = case / "sources.json" if (case / "sources.json").exists() else cases_dir / "sources.json"
    policy = {s["domain"]: s["policy"] for s in load_json(sources)["sources"]}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        g_dir, q_dir, report = tmp / "grants", tmp / "pending", tmp / "report.json"
        shutil.copytree(case / "grants", g_dir)
        q_dir.mkdir()
        before = {p.stem: p.read_text(encoding="utf-8") for p in g_dir.glob("*.md")}
        r = subprocess.run([sys.executable, str(updater), "--offline",
                            "--pages-dir", str(case / "pages"), "--grants-dir", str(g_dir),
                            "--pending-dir", str(q_dir), "--sources", str(sources),
                            "--report", str(report), "--today", exp["today"]],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120)
        check(r.returncode == 0, f"[{name}] updater exited {r.returncode}: {r.stderr.strip()[-300:]}")
        rep = load_json(report)
        got = {g["id"]: g for g in rep.get("grants", [])}
        check(set(got) == set(before), f"[{name}] report covers {sorted(got)}, expected {sorted(before)}")

        auto = 0
        for gid, old in before.items():
            g = got[gid]
            action = g.get("action")
            check(action in ACTIONS, f"[{name}] {gid}: unknown action {action!r}")
            check(action == exp["grants"][gid], f"[{name}] {gid}: action {action!r}, expected {exp['grants'][gid]!r}")
            old_meta, old_body = split(old)
            if policy.get(domain(old_meta["url"])) == "auto":
                auto += 1
            new = (g_dir / f"{gid}.md").read_text(encoding="utf-8")
            new_meta, new_body = split(new)
            for k in FACTS:
                check(new_meta.get(k) == old_meta.get(k), f"[{name}] {gid}: fact {k!r} changed by the updater")

            if action in ("needs_review", "failed", "skipped_manual"):
                check(new == old, f"[{name}] {gid}: {action} must leave the grant file untouched")
                if action == "needs_review":
                    check((q_dir / f"{gid}.md").exists(), f"[{name}] {gid}: needs_review must write a draft to the pending dir")
                if action == "failed":
                    check(str(g.get("reason", "")).strip(), f"[{name}] {gid}: failed needs a reason")
                continue

            check(new_meta.get("checked_at") == exp["today"], f"[{name}] {gid}: checked_at must be {exp['today']}")
            if action == "unchanged":
                check(new_body == old_body and new_meta.get("source_modified") == old_meta.get("source_modified"),
                      f"[{name}] {gid}: unchanged must keep body and source_modified")
                continue
            check(new_meta.get("source_modified") == g.get("source_modified_now") != old_meta.get("source_modified"),
                  f"[{name}] {gid}: {action} must store the page's new source_modified")
            if action == "touched":
                check(new_body == old_body, f"[{name}] {gid}: touched must keep the body")
                continue
            # updated_text
            check(new_body != old_body, f"[{name}] {gid}: updated_text but the body did not change")
            check(new_meta.get("fetched_at") == exp["today"], f"[{name}] {gid}: fetched_at must be {exp['today']}")
            for h in ("Formål", "Hvem kan søke", "Hva kan det søkes om", "Vedlegg", "Frister og rapportering"):
                check(section(new_body, h) is not None, f"[{name}] {gid}: heading {h!r} missing after update")
            for h in ("Hvem kan søke", "Frister og rapportering"):
                check(section(new_body, h) == section(old_body, h),
                      f"[{name}] {gid}: {h!r} changed, so this should have been needs_review")
            check(numbers(new_body) == numbers(old_body),
                  f"[{name}] {gid}: numbers changed, so this should have been needs_review")
            page = page_text((case / "pages" / f"{gid}.html").read_text(encoding="utf-8", errors="replace"))
            for line in new_body.splitlines():
                text = " ".join(line.lstrip("-* ").split())
                if text and not line.startswith("#") and not text.startswith("("):
                    check(text in page, f"[{name}] {gid}: body line not found verbatim in the page: {text[:80]!r}")

        check(rep.get("requests") == auto, f"[{name}] requests {rep.get('requests')} != {auto} auto-policy grants")
        for f in list(g_dir.glob("*.md")) + list(q_dir.glob("*")):
            text = f.read_text(encoding="utf-8")
            body = split(text)[1] if text.startswith("---") else text
            for pattern, label in ((EMAIL, "e-mail"), (PHONE, "phone number")):
                m = pattern.search(body)
                check(not m, f"[{name}] {f.name}: {label} written ({m.group(0) if m else ''})")
            for s in exp.get("forbidden_strings", []):
                check(s not in text, f"[{name}] {f.name}: contains forbidden string {s!r} (personal data)")
    total += 1

print(f"{total} update cases")
print("PASS")
