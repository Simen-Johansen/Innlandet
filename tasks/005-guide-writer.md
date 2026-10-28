# Task 005: Guide writer, headless agent stage (stage 5)

## Goal
A second `claude -p` call with `harness/prompts/guide.md` writes `out/plan.json`: the action plan for the
matched grants, in the requested language.

## Context
- Inputs: `out/entity.json`, `out/matches.json`, and the full grant files of **matched** grants only
  (stage 4 output tells the harness which ones; the harness copies them to `out/guide_input/`)
- Output schema:
  ```json
  {"orgnr": "...", "org_name": "...", "output_language": "en" | "no",
   "grants": [{"grant_id": "...", "title": "...", "url": "...",
               "application_deadline": "YYYY-MM-DD", "max_amount_nok": 50000 | "unknown",
               "amount_note": "...", "why_qualifies": "max 60 words",
               "attachments": ["..."], "steps": ["max 25 words each", "..."]}]}
  ```
- `url`, `application_deadline`, `max_amount_nok` must be copied from the frontmatter.
  `amount_note` says so if `requested_amount_nok` is above the maximum.
- English or klarspråk Norwegian, short sentences

## Constraints
- Do not edit eval/
- Prompt in `harness/prompts/guide.md`; `--allowedTools "Read,Edit(/out/**)"`; budget 0.50 USD
- The model writes JSON only. Markdown is rendered by code (task 006), so formatting can never
  change facts

## Acceptance (all must pass)
- After task 004: run the claude -p command, then `python eval/check_plan.py` prints PASS
- The check failed before this task started (red first)

## What eval/check_plan.py asserts (the verification gate, Section 3.1 of the project description)
- schema valid; `output_language` equals the request
- **entity check:** `orgnr`, `org_name` equal `out/entity.json`
- **grant check:** grant ids ⊆ matched ⊆ kept
- **hallucination check:** `url`, `application_deadline`, `max_amount_nok` equal the frontmatter values
- **privacy check:** no e-mail or phone pattern anywhere in the file
- `why_qualifies` ≤ 60 words, each step ≤ 25 words, at least 1 attachment per grant

## Out of scope
Fluency and helpfulness (LLM-as-judge, task 014)
