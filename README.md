# Innlandet

Course project, KIUA2003. Agentic workflow, work in progress. See [SPEC.md](SPEC.md).

## Setup

1. Install [uv](https://docs.astral.sh/uv/): `winget install astral-sh.uv` (or `pip install uv`).
2. `uv sync`
3. Copy `.env.example` to `.env` and fill in values.
4. Run checks: `uv run ruff check . && uv run ruff format --check . && uv run pytest`
