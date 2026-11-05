"""Check for task 010: every grant source has a recorded, human-checked fetch policy.

context/sources.json:
  {"user_agent": "<name our fetcher sends>",
   "sources": [{"domain": "innlandetfylke.no", "policy": "auto" | "manual",
                "robots_file": "fixtures/robots/innlandetfylke.no.txt" | null,
                "robots_checked": "YYYY-MM-DD", "checked_by": "<initials>", "note": "..."}]}

Rule enforced by code: a domain may be "auto" only if its saved robots.txt allows our user agent,
"*", and the AI agents below, for every grant URL we hold on that domain. If a site turns AI
crawlers away, we do not fetch it automatically either, even though our fetcher is not their crawler.

Run: python eval/check_sources.py        Env: GRANTS_DIR, EVAL_TODAY
"""
from datetime import date
from urllib.robotparser import RobotFileParser

from common import CONTEXT, GRANTS, ROOT, check, domain, load_json, parse_grant, today

AI_AGENTS = ["ClaudeBot", "Claude-User", "Claude-SearchBot", "anthropic-ai", "GPTBot"]
MAX_AGE_DAYS = 90

data = load_json(CONTEXT / "sources.json")
ua = data.get("user_agent", "")
check(isinstance(ua, str) and ua.strip(), "sources.json needs a non-empty user_agent")
sources = {}
for s in data.get("sources", []):
    d = s.get("domain", "")
    check(d and d == d.lower() and not d.startswith("www."), f"bad domain {d!r} (lowercase, no www.)")
    check(d not in sources, f"duplicate domain {d}")
    check(s.get("policy") in ("auto", "manual"), f"{d}: policy must be 'auto' or 'manual'")
    check(str(s.get("checked_by", "")).strip(), f"{d}: checked_by (a human's initials) is required")
    try:
        checked = date.fromisoformat(s.get("robots_checked", ""))
    except ValueError:
        check(False, f"{d}: robots_checked must be YYYY-MM-DD")
    check((today() - checked).days <= MAX_AGE_DAYS, f"{d}: robots.txt last checked over {MAX_AGE_DAYS} days ago")
    if s["policy"] == "auto":
        check(s.get("robots_file"), f"{d}: policy 'auto' requires a saved robots_file")
    sources[d] = s

urls_by_domain = {}
for f in sorted(GRANTS.glob("*.md")):
    url = parse_grant(f)[0]["url"]
    d = domain(url)
    check(d in sources, f"{f.name}: domain {d} has no entry in context/sources.json")
    urls_by_domain.setdefault(d, []).append(url)

for d, s in sources.items():
    if not s.get("robots_file"):
        continue
    path = ROOT / s["robots_file"]
    check(path.exists(), f"{d}: robots_file {s['robots_file']} does not exist")
    rp = RobotFileParser()
    rp.parse(path.read_text(encoding="utf-8", errors="replace").splitlines())
    blocked = [(a, u) for u in urls_by_domain.get(d, []) for a in [ua, "*"] + AI_AGENTS
               if not rp.can_fetch(a, u)]
    if blocked and s["policy"] == "auto":
        check(False, f"{d}: policy is 'auto' but robots.txt disallows {blocked[0][0]} for {blocked[0][1]}")
    if blocked:
        print(f"note: {d} is manual; robots.txt disallows e.g. {blocked[0][0]}")

print("PASS")
