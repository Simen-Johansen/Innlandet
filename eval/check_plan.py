"""Check for task 005: the verification gate on out/plan.json.

Run: python eval/check_plan.py [request.json]     (default: fixtures/input_hamar.json)
Red first: fails with "out/plan.json does not exist" before the task.

Checks: schema, entity facts, grant chain (plan == matched ⊆ kept),
hallucination (url / deadline / max amount copied from frontmatter), privacy, lengths.
"""
import sys
from datetime import date

from common import EMAIL, FIXTURES, GRANTS, OUT, PHONE, ROOT, as_list, check, load_json, parse_grant

req_path = ROOT / sys.argv[1] if len(sys.argv) > 1 else FIXTURES / "input_hamar.json"
request = load_json(req_path)
entity = load_json(OUT / "entity.json")
elig = load_json(OUT / "eligible.json")
matches = load_json(OUT / "matches.json")
plan = load_json(OUT / "plan.json")
today = date.fromisoformat(elig["today"])

TOP = {"orgnr", "org_name", "output_language", "grants"}
GRANT = {"grant_id", "title", "url", "application_deadline", "max_amount_nok",
         "amount_note", "why_qualifies", "attachments", "steps"}

check(set(plan) == TOP, f"top-level keys must be {sorted(TOP)}, got {sorted(plan)}")
check(plan["output_language"] == request["output_language"],
      f"output_language {plan['output_language']!r} != requested {request['output_language']!r}")

# Entity check
check(plan["orgnr"] == entity["organisasjonsnummer"], "orgnr differs from out/entity.json")
check(plan["org_name"] == entity["navn"], "org_name differs from out/entity.json")

# Grant chain: every matched grant is in the plan, nothing else
matched = {m["grant_id"] for m in matches["matches"] if m["verdict"] == "match"}
check(matched <= set(elig["kept"]), "matches.json has a 'match' for a grant the filter rejected")
plan_ids = [g.get("grant_id") for g in plan["grants"]]
check(len(plan_ids) == len(set(plan_ids)), f"duplicate grants in plan: {plan_ids}")
check(set(plan_ids) == matched, f"plan grants {sorted(plan_ids)} != matched grants {sorted(matched)}")

requested = request.get("requested_amount_nok")
for g in plan["grants"]:
    gid = g["grant_id"]
    check(set(g) == GRANT, f"{gid}: keys must be {sorted(GRANT)}, got {sorted(g)}")
    meta, _ = parse_grant(GRANTS / f"{gid}.md")

    # Hallucination check: facts copied, not generated
    check(g["url"] == meta["url"], f"{gid}: url {g['url']!r} != source {meta['url']!r}")
    check(g["application_deadline"] in as_list(meta["deadlines"]),
          f"{gid}: deadline {g['application_deadline']!r} not in source deadlines {meta['deadlines']!r}")
    check(date.fromisoformat(g["application_deadline"]) >= today,
          f"{gid}: deadline {g['application_deadline']} is already past ({today})")
    src_max = meta["max_amount_nok"]
    want_max = int(src_max) if src_max.isdigit() else "unknown"
    check(g["max_amount_nok"] == want_max, f"{gid}: max_amount_nok {g['max_amount_nok']!r} != source {want_max!r}")
    if isinstance(want_max, int) and isinstance(requested, int) and requested > want_max:
        check(isinstance(g["amount_note"], str) and g["amount_note"].strip(),
              f"{gid}: requested {requested} > max {want_max}, so amount_note must explain it")

    # Lengths and content
    check(isinstance(g["title"], str) and g["title"].strip(), f"{gid}: empty title")
    check(1 <= len(g["why_qualifies"].split()) <= 60, f"{gid}: why_qualifies must be 1-60 words")
    check(isinstance(g["attachments"], list) and len(g["attachments"]) >= 1, f"{gid}: needs at least 1 attachment")
    check(isinstance(g["steps"], list) and len(g["steps"]) >= 1, f"{gid}: needs at least 1 step")
    for s in g["steps"]:
        check(1 <= len(s.split()) <= 25, f"{gid}: step longer than 25 words: {s!r}")

# Privacy check over the whole file
raw = (OUT / "plan.json").read_text(encoding="utf-8")
m = EMAIL.search(raw)
check(not m, f"plan contains an e-mail address ({m.group(0) if m else ''})")
text_values = raw.replace(entity["organisasjonsnummer"], "")  # the orgnr is 9 digits, not a phone
m = PHONE.search(text_values)
check(not m, f"plan contains something like a phone number ({m.group(0) if m else ''})")

print("PASS")
