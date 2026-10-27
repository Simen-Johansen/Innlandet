# Task 001: Collect grant rules from the pilot sources

## Goal
After this task, `fixtures/grants/` holds one cleaned, sanitised Markdown file per grant page from
the pilot sources, with a manifest and discovery record that prove nothing listed was skipped.

## Context
- Plan and checklist: `docs/data-plan.md` (steps 0–4, checks A–D). Skill: `grant-sources`.
- Registry: `fixtures/sources.json`. Kommune list: `fixtures/geonorge_fylke34.json`
  (`https://ws.geonorge.no/kommuneinfo/v1/fylker/34`, saved 2026-10-27).
- Pilot (decision 2026-10-27): Innlandet fylkeskommune (`https://innlandetfylke.no/tjenester/sok-tilskudd/`),
  Hamar (3403), Løten (3412), Stange (3413). Ringsaker (3411) excluded: no sitemap.xml.
  The other 42 kommuner are excluded as outside the pilot.
- Hamar, Løten and Stange block `ClaudeBot` in robots.txt; `User-agent: *` is allowed. Our harness
  sends its own User-Agent, not ClaudeBot. Open question for the lecturer (see docs/data-plan.md).

## Constraints
- Do not edit eval/
- Python standard library only in harness/
- Respect robots.txt for our User-Agent; 2 s between requests; reuse cached raw pages younger than 7 days
- Raw HTML stays in `out/raw/` (not in git); only cleaned Markdown is committed
- Remove contact-person blocks, `tel:`/`mailto:` links, phone numbers and personal e-mails before saving

## Acceptance (all must pass)
- `uv run python harness/collect.py --dry-run` prints every stage with its input, output and check, then exits 0
- `uv run python harness/collect.py` (live) then `uv run python eval/check_data.py` prints PASS
- `uv run python eval/check_data.py` failed before this task started (red first)
- `uv run ruff check . && uv run ruff format --check . && uv run pytest` passes

## Out of scope
Extracting the grant schema (step 5, checks E–F), PDF attachments (listed, not fetched),
national schemes (Frifond, momskompensasjon), the 43 kommuner outside the pilot.
