# Task 010: Automated, polite grant fetcher with privacy sanitizer

## Goal
`python harness/fetch_grants.py` refreshes the body text of the grant files from their official URLs,
strips personal data, and reports any change instead of silently overwriting.

## Context
- Before writing code, a human reads robots.txt and the terms of each source and records them in the
  `innlandet-grants` skill. If a source disallows automated access, it stays manual
- Cache: `fixtures/grants_raw/<id>.html` + `<id>.meta.json` (ETag / Last-Modified); conditional
  requests; at most once per 7 days per page
- Sanitizer: `harness/sanitize.py` removes e-mails, phone numbers and the contact block
- If the extracted text differs from the current body: write `out/grant_changes/<id>.diff` and
  **do not** update the file. A human reviews and updates frontmatter (deadlines may have changed)

## Constraints
- Do not edit eval/; standard library only (`html.parser`)
- User-Agent with app name + repo URL; timeout 10 s; no parallel requests

## Acceptance (all must pass)
- `python harness/fetch_grants.py --offline` (reads cached HTML) followed by `python eval/check_grants.py` → PASS
- `python eval/check_sanitize.py`: a fixture page with a fake name, e-mail and phone comes out clean
- A second live run within 7 days makes 0 requests (logged)

## Out of scope
PDF guidelines (document as a limitation, or a later task)
