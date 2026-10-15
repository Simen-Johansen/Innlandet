# Innlandet
Two-person KIUA2003 course project: an agentic workflow (spec in SPEC.md).

## Layout
- tasks/: task definitions · harness/: agent harness · eval/: evaluations
- fixtures/: test inputs · docs/meetings/: meeting notes · docs/prompt-log.md: prompt log

## Checks
`uv run ruff check . && uv run ruff format --check . && uv run pytest`

## Rules
- Never edit anything in eval/ without asking first.
- No personal data in the repo: not in fixtures, logs, prompts or commits.
- Secrets go in .env (never committed, never read). Copy from .env.example.
- Log significant prompts in docs/prompt-log.md.
