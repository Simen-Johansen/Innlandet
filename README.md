# Innlandet

Course project, KIUA2003. Agentic workflow, work in progress. See [SPEC.md](SPEC.md).

## Setup

1. Python 3.12 or newer, available as `python`. Harness and checks use the standard library only.
2. Copy `.env.example` to `.env` and fill in values.
3. Run the checks for each stage, e.g. `python harness/entity.py fixtures/input_hamar.json --offline`,
   then `python eval/check_entity.py`. Every check must print PASS. The checks in `eval/` are the source of truth.
4. Optional extra unit tests: `python -m pytest` (needs pytest installed).
