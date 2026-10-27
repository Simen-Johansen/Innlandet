# Prompt log

One entry per significant prompt, and always when agent output was corrected, challenged
or rejected (the report appendix asks for exactly those). Add entries with `/log`. Format:

## YYYY-MM-DD: short title
- **Who:**
- **Prompt:**
- **Outcome:**
- **Correction:** what the human (or a check) corrected, challenged or rejected, and why

## 2026-10-15: Implement task 001 (probe)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan Implement tasks/001-probe.md`; source chosen: NRK Innlandet RSS
- **Outcome:** `harness/probe.py` (stdlib fetch with User-Agent + cache, RSS parse),
  offline test on a synthetic fixture. Live run pending human check of the feed URL.

## 2026-10-22: Remove the NRK probe
- **Who:** Simen + Claude Code
- **Prompt:** Remove everything from the NRK Innlandet test so we can start on the task in SPEC.md
- **Outcome:** Probe, its test, fixture, task file and eval check deleted in a removal
  commit; history (PR #1) kept.

## 2026-10-27: Claude Code setup from the W40/W43 lectures
- **Who:** Elias + Claude Code (auto mode)
- **Prompt:** Use the W40 and W43 presentations as the Claude setup; edit CLAUDE.md and other
  files to fit our rough plan; use repo files (not private memory) and keep the prompt log.
- **Outcome:** Lean CLAUDE.md; settings.json with deny on Edit/Write in eval/ and a Stop hook
  running the checks; skills `brreg-api` and `grant-sources`; `/task` and `/log` commands;
  read-only `reviewer` subagent; CI `checks.yml`; task and meeting templates.
- **Correction:** The agent asked before building and the human narrowed scope: no skeleton code
  yet. The agent's first question (bash vs Python runner) was too technical; answered with a default.

## 2026-10-27: Example orgnr in the rough plan does not exist
- **Who:** Elias + Claude Code
- **Prompt:** (while writing the brreg-api skill) verify the API against the rough plan's example.
- **Outcome:** `GET /enheter/970169215` returns 404. The real Hamar Idrettslag (hovedlaget) is
  `871586152` (FLI, 3403, in Frivillighetsregisteret). The API also returns `telefon`/`mobil`,
  so the skill now says to strip them.
- **Correction:** The rough plan (AI-drafted) invented an orgnr. Rule added to CLAUDE.md: never
  invent APIs, URLs, orgnrs or deadlines; verify against the source.

## 2026-10-27: Plan for collecting grant rules (RAG or not)
- **Who:** Elias + Claude Code
- **Prompt:** Plan how to retrieve all grant rules from Innlandet websites; should we use RAG?
  Make a binary-verifiable checklist that proves we have all the information.
- **Outcome:** docs/data-plan.md: structured catalogue + code filter + full-text reading instead
  of vector RAG; 6-step pipeline; checklist A1–F2. Based on live recon of innlandetfylke.no
  (58 grants), Geonorge (46 kommuner) and Hamar kommune.
- **Correction:** (1) The agent first said county pages were not UTF-8; the HTTP header said
  utf-8, and the broken æøå came from the Windows terminal. Retracted. (2) Recon showed the rough
  plan's example grant is not open to clubs. (3) "Public, so scraping is allowed" was challenged:
  robots.txt blocks PDF download paths on the county site and ClaudeBot on Hamar's.

## 2026-10-27: PR opened too early
- **Who:** Elias + Claude Code
- **Prompt:** "Okay" to "push and open a pull request?"
- **Outcome:** PR #3 (elias → main) was opened, then closed on request.
- **Correction:** Human rejected it: nothing goes into main yet. CLAUDE.md now says one task =
  one branch, no PRs until both partners decide.

## 2026-10-27: Task 001 first live runs: what the checks caught
- **Who:** Elias + Claude Code
- **Prompt:** "Just get the data" (pilot: county + Hamar, Løten, Stange).
- **Outcome:** 103 pages collected and cleaned; draft check passes; not committed (see last point).
- **Correction:** Each of these was found by the check or by reading the output, not by the agent's
  own confidence:
  1. Check bug: the phone regex matched ISO dates (2026-10-27). Fix proposed in a draft check.
  2. Wrong assumption in the check: "county index and category pages list the same grants". They
     do not (2 index-only, 13 category-only, incl. our test grant 61228). Harness now takes the union.
  3. Harness bug: the cleaner skipped `<form>`, and ASP.NET wraps the whole page in one, so 3 pages
     came out empty. Also skipped `<nav>`, which hid Hamar's list of grants.
  4. Keyword blind spots: "spillemidler", "legat", "stipend" missed; "midler" matched "midlertidig".
  5. Privacy: PASS did not mean clean. Caseworker names in body text slipped through (fixed by
     dropping contact sections and role+name lines), and prize/stipend pages list winners by name,
     which a regex cannot tell apart from place names. Fixtures held back until this is solved.
