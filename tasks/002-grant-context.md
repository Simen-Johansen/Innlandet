# Task 002: Curate four grant context files (stage 2, manual for the skeleton)

## Goal
`context/grants/` holds 4 grant files in the `innlandet-grants` format, plus `harness/grants.py`
with a `load_grants()` function that parses them (frontmatter + sections) for the later stages.

## Context
- Format and headings: `innlandet-grants` skill
- The 4 files are chosen to exercise every path of the filter and matcher:
  1. an outdoor or activity grant for children/youth that a FLI club can get → expected match
  2. an equipment or inclusion grant for free youth activities → expected match
  3. a culture/arts grant open to FLI → passes filter, rejected by matcher (wrong topic)
  4. a grant open only to municipalities (`applicant_orgforms: KOMM`) → rejected by filter
- **A human finds the real pages** on innlandetfylke.no / the municipality site, copies the text, and
  fills the frontmatter. The grant names and deadlines in our first outline are placeholders until
  checked against the real pages. Put the initials of the checker in `verified_by`.
- Skeleton: copy by hand. Automated fetching comes in task 010.

## Constraints
- Do not edit eval/
- Body text verbatim from the source (evidence quotes are substring-checked later)
- Remove caseworker names, e-mails and phone numbers; keep institutional contact pages as URLs only
- `harness/grants.py`: standard library only, no PyYAML (simple `key: value` parser)

## Acceptance (all must pass)
- `python eval/check_grants.py` prints PASS
- The check failed before this task started (red first)

## What eval/check_grants.py asserts
- every file has all frontmatter keys; `id` equals the file name
- `url` starts with `https://`; `deadlines` parse as ISO dates; `max_amount_nok` is an int or `unknown`
- `fetched_at` is not more than 30 days old (stale context is a failure, not a warning)
- every file has the five body headings
- no match for e-mail (`\S+@\S+\.\w+`) or Norwegian phone (`(\+47\s?)?(\d{2}\s?){4}`) patterns
- `load_grants()` returns 4 grants with the same ids

## Out of scope
Fetching pages automatically, PDF conversion, more than 4 grants
