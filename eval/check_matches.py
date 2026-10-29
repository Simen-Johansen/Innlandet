"""Check for task 004: out/matches.json from the matcher agent.

Expected:
  {"matches": [{"grant_id": "...", "verdict": "match" | "reject",
                "reason": "max 40 words", "evidence_quote": "exact text, 5-40 words"}]}

Optional Author expectations (written BEFORE the first run, never by the agent):
  fixtures/expected_matches.json  {"must_match_any": ["id", ...], "must_reject": ["id", ...]}

Red first: fails with "out/matches.json does not exist" before the task.
Run: python eval/check_matches.py
"""
from common import FIXTURES, GRANTS, OUT, check, load_json


def norm(s):
    return " ".join(s.split())


elig = load_json(OUT / "eligible.json")
kept = set(elig["kept"])
data = load_json(OUT / "matches.json")

check(isinstance(data, dict) and isinstance(data.get("matches"), list),
      'matches.json must be {"matches": [...]}')
entries = data["matches"]
ids = [m.get("grant_id") for m in entries]
check(len(ids) == len(set(ids)), f"duplicate grant_id in matches: {ids}")
check(set(ids) == kept, f"matched ids {sorted(set(ids))} != kept ids {sorted(kept)} (one entry per kept grant)")

for m in entries:
    gid = m["grant_id"]
    keys = {"grant_id", "verdict", "reason", "evidence_quote"}
    check(set(m) == keys, f"{gid}: keys must be exactly {sorted(keys)}, got {sorted(m)}")
    check(m["verdict"] in ("match", "reject"), f"{gid}: verdict {m['verdict']!r} must be 'match' or 'reject'")
    check(isinstance(m["reason"], str) and 1 <= len(m["reason"].split()) <= 40,
          f"{gid}: reason must be 1-40 words")
    quote = m["evidence_quote"]
    check(isinstance(quote, str) and 5 <= len(quote.split()) <= 40,
          f"{gid}: evidence_quote must be 5-40 words")
    source = (GRANTS / f"{gid}.md").read_text(encoding="utf-8")
    check(norm(quote) in norm(source),
          f"{gid}: evidence_quote is not a verbatim substring of context/grants/{gid}.md: {quote!r}")

exp_path = FIXTURES / "expected_matches.json"
if exp_path.exists():
    exp = load_json(exp_path)
    verdict = {m["grant_id"]: m["verdict"] for m in entries}
    want_any = exp.get("must_match_any", [])
    if want_any:
        check(any(verdict.get(g) == "match" for g in want_any),
              f"expected at least one of {want_any} to be 'match', got {verdict}")
    for g in exp.get("must_reject", []):
        check(verdict.get(g) == "reject", f"{g}: expected 'reject', got {verdict.get(g)!r}")

print("PASS")
