# Safe operation (task 011, exam Section 3.2)

Six measures keep the Volunteer Grant Navigator safe to run unattended. Each paragraph says what
is implemented, where, and how we measure that it works.

## Permission scoping
The project settings (`.claude/settings.json`) deny every Claude session in this repo reading
`.env` (`Read(./.env)`, `Read(**/.env)`) and editing the grader and the curated facts
(`Edit(/eval/**)`, `Edit(/context/**)`), plus the expected-answer fixtures and the raw grant pages
that hold personal data. The two model stages (matcher and guide writer) run headless as
`claude -p --permission-mode dontAsk --allowedTools "Read,Edit(/out/**)"` (`CLAUDE_ARGS` in
`harness/run.py`). With `dontAsk`, anything not allowed is refused without asking, so a stage can
only read the repo and write in `out/`. It cannot run shell commands, fetch web pages, or change
code, checks or grant files. The stages start in the repo root, so the deny rules apply to them
too. Measured by: inspection only. The rules are in `.claude/settings.json` and `CLAUDE_ARGS`,
but no automated check tries a forbidden edit yet (a candidate for task 012).

## Secrets
The only possible secret is `ANTHROPIC_API_KEY`. Today there is none: `claude` runs on a Claude Pro
login, there is no `.env`, and CI never calls `claude` (checked 2026-11-10). If a key is added, it
lives in `.env`, which `.gitignore` has ignored since
commit `ad47399` (2026-10-15, the second commit, minutes after the scaffold and before any secret
existed). `git log --all -- .env` is empty, so the file has never been in the history.
`.env.example` holds the variable name only, with no value. Claude Code may not read `.env` (see
above). Measured by: the CI step `git check-ignore .env` in `.github/workflows/checks.yml`, which
fails the build if the ignore rule is ever removed.

## Cost control
On the Pro login used today, `total_cost_usd` is the CLI's estimate of what the call would cost on the
paid API, not money billed; the caps below then limit model usage (the Pro plan has its own usage
limits) rather than spending. They are kept as they are because a deployed service would run with an
API key and pay per token, and because the estimate still stops a runaway loop.
Every `claude -p` call has `--max-budget-usd 0.50`, which the CLI enforces itself. Each call's
`total_cost_usd` is appended to `out/cost_log.jsonl` (this run) and to `out/cost_history.jsonl`
(kept across runs). Before every model call, `run.py` sums this run's log and stops with exit 1
once it has reached 1.50 USD. That is three calls at the cap, not the six calls (3 attempts × 2
stages) the retry loop would allow. Rejected input stops in stages 1–3 and costs nothing. A typical
run costs about 0.08 USD, so 1.50 USD only ever stops a run that has gone wrong. Measured by:
`eval/check_budget.py` (a fake cost history above the 24 h cap stops the run before any claude
call), `check_run.py` and `run_eval.py` (no model call for rejected input), and the cost column
in every eval log in `docs/eval-logs/`. The 1.50 USD per-run cap can't be faked from outside,
because `out/cost_log.jsonl` is emptied at the start of every run. It is a five-line guard in
`run_stage`, and the 0.50 USD cap per call backs it up.

## Human gate
The navigator advises; it never acts. The plan is written to `out/grant_action_plan.md` only.
Nothing is sent to a club, submitted to a grant portal or posted anywhere, and the stages have no
tool that could do it. A person in the club reads the plan and decides whether to apply. Grant
facts (eligibility, deadlines, amounts) are written and checked by a person (`verified_by` in
every grant file). The weekly update (tasks 010, 015, 016) may only refresh dates and the verbatim
body text. New grants become drafts in `context/grants_pending/`, which the harness never loads,
until a person completes them. Why: a missed deadline or a wrong eligibility rule costs a volunteer
club a whole grant round, while a grant that appears a week late costs almost nothing. The gate
trades speed for being right, and for this user that is the right trade.

## Kill switch
`harness/run.py` writes `out/HALTED` (time and reason) and exits 4 when any of these happens:
(1) 3 runs in a row fail the verification gate (exit 1; rejections and delivered plans reset the
count; a run that stopped on `upstream_unavailable` is logged with that reason but neither counts
nor resets, because an outage costs no model money and says nothing about our code, task 013), (2) the model cost in the last 24 h passes 5 USD (raised from 3 USD in task 012, so one
full eval of 17 cases fits with room for a few runs), or (3) a grant file in use was last
checked more than 30 days ago (measured from `EVAL_TODAY` when it is set). While `out/HALTED`
exists every run exits 4 at once, before touching anything. Only a person can resume, by reading
the file, fixing the cause and deleting it. The state the switch needs (`HALTED`,
`run_history.jsonl`, `cost_history.jsonl`) is the only thing in `out/` that survives the wipe at
the start of a run. Eval runs count too: a full eval costs about 2.5 USD, so a second full eval
on the same day halts by design. Measured by: `eval/check_killswitch.py` (3 simulated failed runs →
exit 4 and `out/HALTED`; the next run also exits 4; a stale grant file halts) and
`eval/check_budget.py` (24 h cap).

## Abandonment criterion
We drop stage 5 (the model-written guide) and render the plan from the grant frontmatter only if
the hallucination check (`check_plan.py`, run through `eval/run_eval.py`) fails on more than 20 %
of the eval cases after two prompt revisions of `harness/prompts/guide.md`. We also replace the
model matcher (stage 4) with the rule filter alone if, after two prompt revisions, the mean model
cost per eval run is above 0.50 USD or the matcher misses a `must_match` grant in more than 20 % of
cases. Every revision and its eval result is recorded in `docs/prompt-log.md` and
`docs/eval-logs/`, so the decision is based on logged numbers, not impressions.
