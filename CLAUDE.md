# Volunteer Grant Navigator: org number + project idea → verified grant checklist for Innlandet clubs.

## Commands (use `python`, never `python3`: python3 does not exist on our machines)
- Full offline run: `python harness/run.py --offline`
- Wiring only: `python harness/run.py --offline --dry-run`
- Checks: each stage has `python eval/check_<stage>.py`; all must print PASS
- Eval (from task 009): `python eval/run_eval.py`

## Rules
- Never edit `eval/` without asking. The checks grade you; if a check fails, report it, do not change it.
- No personal data: never call the Brreg roles endpoint, never store addresses beyond kommunenummer,
  never keep names, e-mails or phone numbers from grant pages.
- Python standard library only in `harness/` and `eval/`. Always `open(..., encoding="utf-8")` (æ ø å).
- Paths with pathlib, not hard-coded `/` or `\` (we develop on Windows; CI is Linux).
- Stages hand off through files in `out/`. A stage never reads another stage's code, only its output file.
- Brreg details: use the `brreg-api` skill. Grant file format and sources: use the `innlandet-grants` skill.
