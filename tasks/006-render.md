# Task 006: Render the plan as Markdown (stage 6)

## Goal
`python harness/render.py` turns `out/plan.json` into `out/grant_action_plan.md` without any LLM.

## Context
- One section per grant: title + link, deadline (`dd.mm.yyyy`), max amount, why the club qualifies,
  attachment checklist (`- [ ]`), numbered steps
- Header: club name, orgnr, generated date, and the line
  "Checked automatically against the official sources fetched on <fetched_at>. Always confirm the
  deadline on the grant page before applying."
- Labels in the output language (`en`/`no`)

## Constraints
- Do not edit eval/
- Standard library only; deterministic: same JSON in, same bytes out

## Acceptance (all must pass)
- `python eval/check_render.py` prints PASS (it runs render.py twice itself)
- The check failed before this task started (red first)

## What eval/check_render.py asserts
- every grant title, URL and deadline in `plan.json` appears in the Markdown
- running render twice gives byte-identical files
- every URL in the Markdown is in `plan.json`; no dates except plan deadlines, today, and one `fetched_at`

## Out of scope
HTML, PDF, sending the plan anywhere (that is a human gate, task 011)
