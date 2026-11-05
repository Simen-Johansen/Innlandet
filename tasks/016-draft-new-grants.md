# Task 016 (optional): Draft new county grants for human review

## Goal
For each catalog entry that a human has marked relevant but that has no grant file yet,
`python harness/draft_grant.py <page_id>` writes `context/grants_pending/<id>.md`. A human completes
the facts, sets `verified_by`, and moves the file into `context/grants/`.

## Context
- Reuses the extraction and sanitizer from task 015
- Code fills only what it can copy: `id`, `title`, `url`, `provider`, `source_modified`, `fetched_at`,
  and the body under the five headings. Facts are left as `TODO`.
- `check_grants.py` never reads `context/grants_pending/`, so a draft cannot reach the matcher

## Acceptance
- A draft for a saved fixture page passes `python eval/check_update.py`'s privacy and verbatim rules
  (add it as a case), and fails `check_grants.py` until a human replaces every `TODO`

## Out of scope
Letting a model fill in facts
