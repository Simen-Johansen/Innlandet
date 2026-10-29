# Prompt log

One entry per significant prompt. Format:

## YYYY-MM-DD: short title
- **Who:**
- **Prompt:**
- **Outcome:**

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

## 2026-10-28: Implement task 001 (Brreg entity)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan implement tasks/001-brreg-entity`
- **Outcome:** `harness/entity.py` (MOD11 before any request, one GET or `--offline` fixture,
  9-key flat entity, rejections exit 3). Real orgnr 942440618 (Hamarkameratene Fotball Elite)
  verified live; the fixture was sanitized (e-mail, mobile and street address removed).
  Corrected: a wrong check-digit-0 example in the agent's own unit test (123456780 → 123456750).

## 2026-10-29: Verify task 002 (grant context)
- **Who:** Simen + Claude Code
- **Prompt:** Verify the four grant files against the live pages and mark them `verified_by: SJ`
- **Outcome:** Claude compared the frontmatter with the pages; Simen confirmed the body text matches.
  All four files have `verified_by: SJ`, and `eval/check_grants.py` prints PASS.
  Corrected: `applicant_orgforms` for kunstnerisk aktivitet (`FLI, KOMM, ENK, AS, STI`) was our own
  reading, not the page's text. The page says only "Arrangører", so a frontmatter comment now says so.
  Friluftsliv keeps `FLI` only (interkommunalt friluftsråd left out on purpose).

## 2026-10-29: Implement task 004 (matcher)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan implement tasks/004-matcher`
- **Outcome:** `harness/prompts/match.md` with a three-condition match rule. The agent asked strict vs lenient;
  we chose strict because a broad purpose (driftstilskudd's "fritidsaktiviteter i Hamar") is open to two
  readings and would make verdicts unstable between runs; strict ties a match to what the grant actually funds.
  Two runs on the Hamar fixture both PASS `eval/check_matches.py` with identical verdicts:
  friluftsliv `match`, driftstilskudd `reject`, kunstnerisk `reject` (~0.13–0.14 USD each).
  Corrected: the first attempt passed the prompt from Windows PowerShell 5.1, which does not escape the
  embedded `"` and truncated the prompt; the agent then guessed the schema (`decision`, no quote) and the
  check FAILed. Calling `claude` from Python `subprocess.run([...])` (as task 007 will) fixes it.

## 2026-10-29: Implement task 005 (guide writer)
- **Who:** Simen + Claude Code (plan mode)
- **Prompt:** `/plan implement tasks/005-guide-writer`
- **Outcome:** `harness/guide_input.py` copies the matched grant files to `out/guide_input/` and writes
  `request.json` (language, requested amount, idea, and `today` from `out/eligible.json`); exit 3
  `no_matching_grants` if nothing matched. `harness/prompts/guide.md` makes the model copy url, deadline
  and max amount from the frontmatter and says what to do if no attachments or no maximum are listed.
  Red first: `check_plan.py` FAILed ("out/plan.json does not exist"). Two runs on the Hamar fixture
  both PASS with the same facts (friluftsliv, 2026-12-01, max `unknown`), costing about 0.15 and 0.08 USD.
