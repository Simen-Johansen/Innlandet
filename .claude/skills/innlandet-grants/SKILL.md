---
name: innlandet-grants
description: Use when reading, creating or validating files in context/grants/, or when writing prompts that quote grant rules: file format, frontmatter fields, sources and their terms.
---
# Grant context files: context/grants/<id>.md

## Frontmatter (between `---` lines, one `key: value` per line, lists comma-separated)
```
id: friluftsliv_example          # = file name without .md
title: <official grant name, Norwegian>
url: https://...                  # official page, verified by a human
provider: innlandet_fylkeskommune | hamar_kommune | ...
applicant_orgforms: FLI           # allowed organisasjonsform codes, e.g. FLI, KOMM
requires_frivillighetsregisteret: true | false
region_prefix: 34                 # kommunenummer prefix, or full 4-digit kommunenummer
target_group: barn_og_unge | alle | ...
max_amount_nok: 50000             # or "unknown"
deadlines: 2027-05-15, 2027-09-15 # ISO dates, next deadlines only
fetched_at: 2026-10-28
verified_by: <initials>           # the human who checked frontmatter against the source
```

## Body: source text, verbatim, under these headings only
`## Formål`, `## Hvem kan søke`, `## Hva kan det søkes om`, `## Vedlegg`, `## Frister og rapportering`.
Copy the text, do not rewrite it: evidence quotes are checked as exact substrings.

## Sources and terms
- innlandetfylke.no (grant pages), the municipalities' grant pages.
- Check robots.txt and terms before any automated fetch; at most one fetch per page per week; cache.
- Strip caseworker names, e-mails and phone numbers before saving (task 002/010).
