import json
from datetime import datetime
data = json.load(open("out/probe.json", encoding="utf-8"))
assert data["source_url"].startswith("https://")
assert len(data["items"]) >= 1, "no items"
for it in data["items"]:
   assert it["title"].strip(), "empty title"
   d = it["date"].replace("Z", "+00:00")
   datetime.fromisoformat(d)
print("PASS")
