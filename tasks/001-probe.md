# Task 001: Probe one public source
## Goal
`harness/probe.py` fetches the NRK
Innlandet RSS feed and writes its items
to `out/probe.json`.
## Context
- Source: https://www.nrk.no/innlandet/toppsaker.rss
(RSS 2.0; `<item>` has `title`, `link`,
`pubDate`). Verified by a human: 2026-10-15
- Output contract: `eval/check_probe.py`
- Offline test input: `fixtures/nrk_sample.rss`
(synthetic, no real content)
## Constraints
- Do not edit eval/
- No personal data; public sources only;
follow the source's terms (User-Agent,
caching, rate limits)
- Python 3 standard library only
## Acceptance (all must pass)
- `python3 harness/probe.py &&
python3 eval/check_probe.py` prints
PASS
- The check failed before this task
started (red first)
## Out of scope
Summarisation, scheduling, anything
with an LLM (later tasks)
