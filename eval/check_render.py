"""Check for task 006: out/grant_action_plan.md is rendered faithfully from out/plan.json.

Runs harness/render.py twice itself to test determinism.
Red first: fails before the task (render.py or the .md file missing).
Run: python eval/check_render.py
"""
import re
import subprocess
import sys
from datetime import date

from common import OUT, ROOT, check, load_json

render = ROOT / "harness" / "render.py"
check(render.exists(), "harness/render.py does not exist")
plan = load_json(OUT / "plan.json")
md_path = OUT / "grant_action_plan.md"


def run_render():
    r = subprocess.run([sys.executable, str(render)], cwd=ROOT, capture_output=True, text=True)
    check(r.returncode == 0, f"render.py exited {r.returncode}: {r.stderr.strip()[-300:]}")
    check(md_path.exists(), "out/grant_action_plan.md was not written")
    return md_path.read_bytes()


first = run_render()
second = run_render()
check(first == second, "render.py is not deterministic: two runs gave different bytes")
md = first.decode("utf-8")

check(plan["org_name"] in md and plan["orgnr"] in md, "header must contain club name and orgnr")
check("- [ ]" in md, "attachments must be rendered as a '- [ ]' checklist")


def digits(s):
    return re.sub(r"[\s\u00a0\u202f.]", "", s)


plan_urls, plan_dates = set(), {date.today().strftime("%d.%m.%Y")}
for g in plan["grants"]:
    check(g["title"] in md, f"{g['grant_id']}: title missing from Markdown")
    check(g["url"] in md, f"{g['grant_id']}: url missing from Markdown")
    d = date.fromisoformat(g["application_deadline"]).strftime("%d.%m.%Y")
    check(d in md, f"{g['grant_id']}: deadline {d} (dd.mm.yyyy) missing from Markdown")
    if isinstance(g["max_amount_nok"], int):
        check(str(g["max_amount_nok"]) in digits(md), f"{g['grant_id']}: max amount missing from Markdown")
    plan_urls.add(g["url"])
    plan_dates.add(d)

# Nothing invented by the renderer: every URL and date in the Markdown comes from the plan
for url in re.findall(r"https?://[^\s)>\]]+", md):
    check(url in plan_urls, f"Markdown contains a URL not in plan.json: {url}")
# The fetched_at date in the header line is allowed; collect it from the grant files' dates if you add more
extra_dates = set(re.findall(r"\b\d{2}\.\d{2}\.\d{4}\b", md)) - plan_dates
check(len(extra_dates) <= 1, f"Markdown contains dates not in plan.json: {sorted(extra_dates)} "
                             "(only one extra date, the fetched_at in the header, is allowed)")

print("PASS")
