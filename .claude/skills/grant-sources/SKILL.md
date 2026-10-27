---
name: grant-sources
description: Use when fetching, caching, sanitizing or reading grant rules from innlandetfylke.no or kommune websites, or files in fixtures/grants/.
---
# Grant sources

- Main source: Innlandet fylkeskommune's grant pages (innlandetfylke.no, "Søk tilskudd"). A human
  verifies every grant URL before it goes in a task file or fixture.
- Respect robots.txt. It disallows, among others, `/Filnedlasting.aspx`, `/dokumentnedlasting.aspx`,
  `/Innsyn*`, `/Kontakt.aspx`, `/kunde/filer`. Fetch only allowed pages, at most once a week, with our User-Agent.
- Save each grant as `fixtures/grants/<slug>.md` with a header: source URL, fetched date, deadline(s),
  applicant types, max amount (NOK). Keep the Norwegian rule text; quote, do not paraphrase.
- Sanitize before saving: remove caseworker names, personal e-mails and phone numbers. Keep only
  institutional contact points (e.g. a postmottak address).
- Do not republish more of the source than the workflow needs.
- Every deadline, URL and amount in our output must appear word-for-word in one of these files.
