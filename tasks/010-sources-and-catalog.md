# Task 010: Source policy and county grant catalog (replaces the old task 010)

## Goal
We know, and can prove by code, (a) which sources we may fetch automatically and (b) that every
grant listed by Innlandet fylkeskommune is either in `context/grants/` or has a human reason for
being left out.

## Context
- **Scope decision (W45):** automatic fetching for innlandetfylke.no only. Municipal grants stay
  manual (like `hamar_driftstilskudd_frivillige_organisasjoner`), because many municipal sites turn
  AI crawlers away in robots.txt and each municipality publishes in its own layout.
- **Human survey first (no code):** for Hamar and 4-5 neighbouring municipalities, record in
  `docs/source-survey.md`: own grant schemes? links to the county's schemes instead? robots.txt
  stance? This answers whether municipal sites duplicate the county (then skip them) or add local
  schemes (then list them as manual sources and name the gap as a limitation).
- `context/sources.json`: one entry per domain, `policy: auto | manual`, a saved copy of robots.txt
  in `fixtures/robots/<domain>.txt`, `robots_checked`, `checked_by` (format: `eval/check_sources.py`)
- **Rule:** a domain is `auto` only if robots.txt allows our User-Agent, `*` and the AI agents
  (ClaudeBot, Claude-User, …) for our grant URLs. Our fetcher is not their crawler, but if a site
  says no to AI agents, we respect the intent.
- `harness/catalog.py`: fetches every page of the county's listing
  (`/tjenester/sok-tilskudd?Side=N`, ~4 pages), saves them as `fixtures/fylke_index/side-N.html`, and
  updates `context/catalog.json`: new listings get `status: pending`, listings that disappear get
  `removed`. Grants are keyed on the numeric page id (`….36453.aspx`), because the same grant can be
  listed under two paths.
- **A human decides relevance** for each pending entry: `ingested` (a grant file exists) or
  `not_relevant` with a reason code (`applicant_not_voluntary`, `closed`, `expired_no_next_round`,
  `not_a_grant`, `duplicate`). Many listings are for municipalities, schools or businesses.

## Constraints
- Do not edit eval/; standard library only
- User-Agent from `sources.json`; one request per index page per run; timeout 10 s; no parallel requests
- `catalog.py` never sets `ingested` or `not_relevant`; only humans do

## Acceptance (all must pass)
- `python eval/check_sources.py` prints PASS
- `python harness/catalog.py --offline && python eval/check_catalog.py` prints PASS and the coverage line
- The checks failed before this task started (red first)

## What the checks assert
- `check_sources.py`: every grant file's domain has a policy; `auto` needs a saved robots.txt that
  allows all listed agents for our URLs; robots checked within 90 days by a named human
- `check_catalog.py`: all pagination pages saved; every listed page id is in the catalog exactly
  once; `ingested` ⇔ a grant file with that page id; `not_relevant` has a reason code and a human;
  nothing `pending` longer than 14 days; the index was checked within 8 days

## Out of scope
Fetching grant pages (task 015), municipal sites, PDF guidelines
