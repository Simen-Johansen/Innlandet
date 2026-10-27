# Innlandet

Course project, KIUA2003. Agentic workflow, work in progress. See [SPEC.md](SPEC.md).

## Setup

1. Install [uv](https://docs.astral.sh/uv/): `winget install astral-sh.uv` (or `pip install uv`).
2. `uv sync`
3. Copy `.env.example` to `.env` and fill in values.
4. Run checks: `uv run ruff check . && uv run ruff format --check . && uv run pytest`

## Working with Claude Code

The rules for the agent live in files in this repo, so both partners get the same agent:

| File | Loaded | What it holds |
|---|---|---|
| `CLAUDE.md` | every session | how to run checks, the rules |
| `tasks/NNN-*.md` | per task (`/task NNN`) | one unit of work + its acceptance check |
| `.claude/skills/*/SKILL.md` | when the topic comes up | Brreg API and grant-source details |
| `.claude/settings.json` | always (enforced) | permissions: never read `.env`, never edit `eval/`; Stop hook |
| `.claude/agents/reviewer.md` | on request | read-only reviewer of a diff vs. a task |
| `docs/prompt-log.md` | `/log` | where the agent was corrected or rejected |
| `docs/meetings/` | by us | weekly meeting reports (copy `_template.md`) |
