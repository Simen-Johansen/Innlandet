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
