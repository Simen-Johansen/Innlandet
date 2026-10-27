# Innlandet
Two-person KIUA2003 project: Volunteer Grant Navigator. Orgnr + project idea in,
verified grant checklist out. Problem, users and success: SPEC.md.

## Checks (run before saying "done")
`uv run ruff check . && uv run ruff format --check . && uv run pytest`

## How we work
- One task = one branch = one PR. Every task is `tasks/NNN-name.md` (copy `tasks/_template.md`).
  Run it with `/task NNN`: plan first, wait for approval, then run every Acceptance command.
- Code where you can, model where you must: fetching, filtering and checking are plain Python.
- Each stage writes a file to `out/`; the next stage reads it; a check in `eval/` runs in between.
- Inputs we save from the live world go in `fixtures/`; the harness must also run `--offline` on them.

## Rules
- Never edit eval/ or weaken a test to make it pass; ask first. A failing check means fix the spec or code.
- No personal data anywhere: no names, phone numbers or e-mails in fixtures, out/, logs, prompts, commits.
- Secrets go in .env (never committed, never read). Copy from .env.example.
- Never invent APIs, URLs, orgnrs or deadlines: verify against the source or say it is unverified.
- Project knowledge lives in this repo, not in your private memory: decisions → docs/meetings/,
  scope → SPEC.md or a task file, rules → this file. Do not write to ~/.claude memory for this project.
- When the user corrects, challenges or rejects your output, add an entry to docs/prompt-log.md
  in the same session (use `/log`).

## Context on demand
- Brønnøysund API (orgnr lookup, fields, privacy): the `brreg-api` skill.
- Grant sources (innlandetfylke.no, kommune pages, caching, sanitizing): the `grant-sources` skill.
