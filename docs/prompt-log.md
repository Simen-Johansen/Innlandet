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
