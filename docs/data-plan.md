# Data plan: collecting and organising grant rules

Status: draft 2026-10-27, needs both partners' sign-off. Based on a live look at the sources
on 2026-10-27 (see "What we found").

## Decision: a structured grant catalogue, not vector RAG

The corpus is small (about 58 county grants plus municipal ones: hundreds, not millions of pages)
and the question is eligibility, not similarity. Vector RAG chunks the text, so "who can apply" and
"deadline" end up in different chunks than the purpose, and a similar-sounding grant the club cannot
apply for still gets retrieved. That is also hard to verify.

Instead:
1. **Catalogue:** one JSON record per grant with the hard facts (applicant types, deadlines, amount,
   region), each with a quote copied from the source page.
2. **Code filters** on those fields (Stage 3 in the rough plan).
3. **The model reads the full text** of only the few grants that survive (Stage 4). With 3–10
   grants the whole text fits in the context, so nothing needs chunking.

This is retrieval by metadata and a tool, not by embeddings. It is cheaper, deterministic and every
step can be checked. Revisit embeddings only if the surviving set is ever too large to read in full.

## Pipeline (each step writes a file, a check runs after it)

| Step | Does | Code/model | Output |
|---|---|---|---|
| 0 Registry | List every source: county + 46 kommuner (Geonorge) + national schemes; include/exclude with reason | code + human | `fixtures/sources.json` |
| 1 Robots | Fetch and save robots.txt per source; record allowed paths | code | `out/robots/<source>.txt` |
| 2 Discover | Enumerate grant URLs: county index `?Side=1..N` until empty + all category pages; kommuner via sitemap.xml + keyword filter | code | `out/discovered.json` |
| 3 Fetch | Download each URL (our User-Agent, 2 s between requests, weekly at most, If-Modified-Since) | code | `out/raw/<source>/<id>.html` (not in git) |
| 4 Clean | Main content → Markdown, keep links; strip `tel:`, personal e-mails, phone numbers, names | code | `fixtures/grants/<source>-<id>.md` |
| 5 Extract | Fill the grant schema with a verbatim quote per field | model (`claude -p`, `--json-schema`) | `fixtures/catalog/<source>-<id>.json` |
| 6 Index | Merge into one catalogue | code | `fixtures/catalog.json` |

Raw HTML stays out of git ("do not republish beyond what the workflow requires"); only cleaned,
sanitised Markdown and the catalogue are committed, so offline runs work.

### Grant schema (draft)
`id`, `source`, `title`, `url`, `applicant_types` (enum: forening, idrettslag, kommune, friluftsråd,
bedrift, privatperson, annet), `requires_frivillighetsregisteret` (bool/null), `region`,
`deadlines` (ISO dates, or "løpende"), `max_amount_nok` (or null), `purpose`, `status` (open/closed),
`fetched` (date), and `evidence`: field → verbatim quote from the Markdown file.

## Completeness checklist (each item: a program exits 0 or 1)

Completeness can only be proven relative to sources we have enumerated. Not "everything that exists",
but "everything in the registry, cross-checked two independent ways".

**A. Sources**
- [ ] A1 The registry's kommunenummer set equals Geonorge's list for fylke 34 (46 kommuner), plus the county.
- [ ] A2 Every registry entry is `included` or `excluded`; every exclusion has a non-empty reason.
- [ ] A3 Every included source has a robots.txt saved at most 7 days ago.

**B. Discovery**
- [ ] B1 County pagination was followed until a page with 0 grants (proves we reached the end).
- [ ] B2 The grant IDs from the index pages equal the IDs from the union of all category pages (two independent lists agree).
- [ ] B3 Every kommune sitemap URL matching the keyword list (tilskudd, støtte, stønad, fond, midler) is either in `discovered.json` or in an exclusion list with a reason (e.g. landbruk, bostøtte).

**C. Fetch**
- [ ] C1 Every discovered URL has a snapshot with status 200 and a fetch date, or a recorded error.
- [ ] C2 No fetched URL matches a Disallow rule in that source's robots.txt.
- [ ] C3 Linked documents we could not fetch (robots, 404) are listed with the reason, not silently skipped.

**D. Clean**
- [ ] D1 Every snapshot has a non-empty `.md` with a source URL and fetch date header.
- [ ] D2 No `.md` contains a phone number, `tel:`, or e-mail address outside an allowlist (e.g. `postmottak@`).
- [ ] D3 Every `.md` is valid UTF-8 with no mojibake (`Ã¸`, `Ã¥`) or U+FFFD.

**E. Catalogue**
- [ ] E1 `.md` files and catalogue records match 1:1.
- [ ] E2 Every record validates against the schema.
- [ ] E3 Every field value has a quote, and that quote appears verbatim in its `.md` (no invented facts).
- [ ] E4 No record has empty `applicant_types` (unclear cases are flagged for a human instead).

**F. Ground truth (held out, written by a human, never shown to the agent)**
- [ ] F1 For 10 hand-labelled grants, `applicant_types` and `deadlines` in the catalogue match the labels 100 %.
- [ ] F2 "Friluftsliv – enkelt og nært" (61228) has applicant types kommune + friluftsråd only, so
      a club query (orgnr 871586152) never returns it.

## What we found (2026-10-27)

- County index: 58 unique grant IDs on `?Side=1..4` (`?Side=5` is empty), 11 categories; the same
  grant appears under several paths.
- County robots.txt disallows `/Filnedlasting.aspx`, `/dokumentnedlasting.aspx`, `/Innsyn*` among
  others. PDF attachments served there are off limits (C3).
- Grant pages are UTF-8; applications go via regionalforvaltning.no (`Ordning_Id`).
- Grant pages contain caseworker phone numbers (`tel:`), so sanitising (D2) is needed.
- The rough plan's example grant "friluftsliv enkelt og nært" is open to kommuner and friluftsråd,
  not clubs.
- Hamar kommune: grant info is spread across `/landbruk/tilskudd-og-erstatninger/` and the news
  archive; robots.txt blocks `ClaudeBot` by name (`User-agent: *` is allowed).

## Open decisions
1. Scope: all 46 kommuner, or the county + a pilot region (Hamar, Stange, Løten, Ringsaker)?
2. Sites that block AI crawlers by name (Hamar): exclude, or ask the lecturer?
3. National schemes clubs use (e.g. Frifond, momskompensasjon): in scope?
