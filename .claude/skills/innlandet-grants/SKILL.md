---
name: innlandet-grants
description: Use when reading, creating, updating or validating files in context/grants/, context/sources.json or context/catalog.json, or when writing prompts that quote grant rules: file format, frontmatter fields, sources, fetch policy.
---
# Grant context files: context/grants/<id>.md

## Frontmatter (between `---` lines, one `key: value` per line, lists comma-separated)
```
id: friluftsliv_example          # = file name without .md
title: <official grant name, Norwegian>            # fact
url: https://...                                    # fact, official page
provider: innlandet_fylkeskommune | hamar_kommune | ...
applicant_orgforms: FLI                             # fact
requires_frivillighetsregisteret: true | false      # fact
region_prefix: 34                                   # fact: prefix or 4-digit kommunenummer
target_group: barn_og_unge | alle | ...             # fact
max_amount_nok: 50000 | unknown                     # fact
deadlines: 2027-05-15, 2027-09-15                   # fact: ISO, next deadlines only
fetched_at: 2026-10-28            # body text last taken from the page
checked_at: 2026-11-05            # last confirmed against the live page (staleness: max 30 days)
source_modified: 2026-10-15T09:37 # the page's "Sist endret", or unknown (manual sources)
verified_by: <initials>           # fact: the human who checked the facts
```
Facts are written by humans only. Code may update `fetched_at`, `checked_at`, `source_modified`
and the body (task 015 rules).

## Body: source text, verbatim, under these headings only
`## Formål`, `## Hvem kan søke`, `## Hva kan det søkes om`, `## Vedlegg`, `## Frister og rapportering`.

## Sources and policy
- `context/sources.json`: per domain `auto` or `manual`; `auto` only if the saved robots.txt allows
  our User-Agent, `*` and AI agents (ClaudeBot, Claude-User, …) for our URLs.
- innlandetfylke.no: automatic (task 015). Municipal sites: manual.
- `context/catalog.json`: every grant the county lists, by numeric page id, with status and,
  for `not_relevant`, a reason code decided by a human.
- Drop the page's "Kontakt" block and `<meta name="author">`: they name a caseworker.
- Drafts live in `context/grants_pending/` and are never loaded by the harness.
