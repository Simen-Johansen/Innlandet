"""Check for task 003: the hard filter is correct and match_input.md leaks nothing.

Expected out/eligible.json:
  {"today": "YYYY-MM-DD", "kept": ["id", ...],
   "rejected": [{"grant_id": "id", "reason": "<code>"}, ...]}
Expected out/match_input.md: "# Project idea" section, then one "## Grant: <id>" section per kept grant.

Red first: fails with "out/eligible.json does not exist" before the task.
Run: python eval/check_filter.py
"""
import re
from datetime import date

from common import GRANTS, OUT, ROOT, as_list, check, load_json, parse_grant

REASONS = ["org_form_not_allowed", "outside_region",
           "not_in_frivillighetsregisteret", "no_open_deadline"]

entity = load_json(OUT / "entity.json")
elig = load_json(OUT / "eligible.json")
check({"today", "kept", "rejected"} <= set(elig), "eligible.json needs keys today, kept, rejected")
today = date.fromisoformat(elig["today"])

grants = {f.stem: parse_grant(f)[0] for f in GRANTS.glob("*.md")}
kept = set(elig["kept"])
rejected = {r["grant_id"]: r["reason"] for r in elig["rejected"]}

check(not kept & set(rejected), f"grants both kept and rejected: {sorted(kept & set(rejected))}")
check(kept | set(rejected) == set(grants),
      f"kept+rejected {sorted(kept | set(rejected))} != all grants {sorted(grants)}")
for gid, reason in rejected.items():
    check(reason in REASONS, f"{gid}: unknown reason {reason!r}")


def expected_reason(meta):
    """Recompute the rules independently, in the order given in task 003."""
    if entity["organisasjonsform"] not in as_list(meta["applicant_orgforms"]):
        return "org_form_not_allowed"
    if not str(entity["kommunenummer"]).startswith(meta["region_prefix"]):
        return "outside_region"
    if meta["requires_frivillighetsregisteret"] == "true" and not entity["registrertIFrivillighetsregisteret"]:
        return "not_in_frivillighetsregisteret"
    if all(date.fromisoformat(d) < today for d in as_list(meta["deadlines"])):
        return "no_open_deadline"
    return None


for gid, meta in grants.items():
    exp = expected_reason(meta)
    got = rejected.get(gid)
    check(exp == got, f"{gid}: expected {'kept' if exp is None else exp!r}, harness says {'kept' if got is None else got!r}")

# Context filter: stage 4 must see only what it needs.
mi_path = OUT / "match_input.md"
check(mi_path.exists(), "out/match_input.md does not exist")
mi = mi_path.read_text(encoding="utf-8")
check(mi.lstrip().startswith("# Project idea"), "match_input.md must start with '# Project idea'")
sections = set(re.findall(r"^## Grant: (\S+)\s*$", mi, flags=re.M))
check(sections == kept, f"grant sections {sorted(sections)} != kept {sorted(kept)}")
for gid in rejected:
    check(gid not in mi, f"rejected grant {gid!r} leaks into match_input.md")
check("http" not in mi, "match_input.md must not contain URLs")
check(not re.search(r"\d[\d\s.]*\s?(kr|NOK)\b|\b(kr|NOK)\.?\s?\d", mi, flags=re.I),
      "match_input.md must not contain NOK amounts")
check(not re.search(r"\d{4}-\d{2}-\d{2}", mi), "match_input.md must not contain deadlines")

print("PASS")
