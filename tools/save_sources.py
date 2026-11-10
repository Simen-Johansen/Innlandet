"""Human tool (not part of the harness): save robots.txt files and raw grant pages.

  python tools/save_sources.py robots
      Downloads robots.txt for every domain in context/sources.json to fixtures/robots/<domain>.txt
      and prints, for each domain, which agents may fetch our grant URLs.
  python tools/save_sources.py page <grant_id>
      Downloads the live page of context/grants/<grant_id>.md to fixtures/pages_raw/<grant_id>.html.

One request per file, our User-Agent, 10 s timeout. Standard library only.
After running "robots", a human reads the output, sets policy, robots_checked and checked_by.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "context" / "sources.json"
GRANTS = ROOT / "context" / "grants"
AGENTS = ["*", "ClaudeBot", "Claude-User", "Claude-SearchBot", "anthropic-ai", "GPTBot"]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def get(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read()


def grant_urls():
    out = {}
    for f in sorted(GRANTS.glob("*.md")):
        m = re.search(r"^url:\s*(\S+)", f.read_text(encoding="utf-8"), flags=re.M)
        if m:
            out[f.stem] = m.group(1)
    return out


def host(url):
    h = re.sub(r"^https?://", "", url).split("/", 1)[0].lower()
    return h[4:] if h.startswith("www.") else h


def robots(cfg):
    urls = grant_urls()
    for s in cfg["sources"]:
        d = s["domain"]
        hosts = {re.sub(r"^https?://", "", u).split("/", 1)[0] for u in urls.values() if host(u) == d} or {d}
        h = sorted(hosts)[0]
        dest = ROOT / s["robots_file"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            body = get(f"https://{h}/robots.txt", cfg["user_agent"]).decode("utf-8", errors="replace")
        except Exception as e:
            print(f"{d}: could not fetch robots.txt ({e}); treat as manual and check by hand")
            continue
        dest.write_text(body, encoding="utf-8")
        rp = RobotFileParser()
        rp.parse(body.splitlines())
        print(f"\n{d}  (saved {s['robots_file']})")
        for gid, u in urls.items():
            if host(u) != d:
                continue
            blocked = [a for a in [cfg["user_agent"]] + AGENTS if not rp.can_fetch(a, u)]
            print(f"  {gid}: {'BLOCKED for ' + ', '.join(blocked) if blocked else 'allowed for all agents'}")
    print("\nNow set policy (auto only if nothing is blocked), robots_checked (today) and checked_by in context/sources.json.")


def page(cfg, gid):
    url = grant_urls().get(gid)
    if not url:
        sys.exit(f"no context/grants/{gid}.md with a url")
    dest = ROOT / "fixtures" / "pages_raw" / f"{gid}.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(get(url, cfg["user_agent"]))
    print(f"saved {dest.relative_to(ROOT)} ({dest.stat().st_size} bytes)")
    print("It contains a caseworker's name, e-mail and phone. Do NOT commit it: run tools/make_update_cases.py, "
          "which writes an anonymised copy, then delete fixtures/pages_raw/ or keep it git-ignored.")


if __name__ == "__main__":
    cfg = json.loads(SOURCES.read_text(encoding="utf-8"))
    if len(sys.argv) >= 2 and sys.argv[1] == "robots":
        robots(cfg)
    elif len(sys.argv) == 3 and sys.argv[1] == "page":
        page(cfg, sys.argv[2])
    else:
        sys.exit(__doc__)
