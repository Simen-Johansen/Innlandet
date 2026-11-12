# Demo runbook: Thu 12.11 13:15

About 10 minutes, about 0.3 USD live. All commands are PowerShell, run from the repo root.
Every command below was tried on 12.11 in the morning, with the exit code shown.

**Important:** a case in `demo/` must run with `EXPECTED_MATCHES` set to its own `.expected.json`.
Otherwise the matcher check grades it against the Hamar expectations and fails 3 times (exit 1).
This is how `eval/check_matches.py` works, not a bug.

## 1. Happy path, live: Gjøvik ski festival (about 20 s, about 0.12 USD, exit 0)
```
$env:EXPECTED_MATCHES="demo/01_gjovik_ski_event.expected.json"; python harness/run.py demo/01_gjovik_ski_event.json; Remove-Item Env:EXPECTED_MATCHES
```
Real Brreg, real Claude. Point at each line:
`[1] entity` → `[2] grants` → `[3] filter` → `[4] matcher` → `[5] guide` → `[6] render`, each with `check PASS`.
Say: code decides the order, the model only does 4 and 5, and nothing moves on until its check passes.
The filter keeps 3 of 5 grants by fixed rules; Claude then matches *Arrangementsutvikling innen idrett*
and rejects the rest. Open `out/grant_action_plan.md`: that is what the club gets.
Backup if Brreg is slow: the same run for Faaberg (`demo/02_faaberg_outdoor.*`).

## 2. An idea from the audience, live (the proof that nothing is scripted, about 0.15 USD)
Ask for an Innlandet club and a project idea. Find the org number on brreg.no. Edit `demo/audience.json`:
`orgnr`, `project_idea` (max 300 characters), `requested_amount_nok`. Then:
```
$env:EXPECTED_MATCHES="demo/audience.expected.json"; python harness/run.py demo/audience.json; Remove-Item Env:EXPECTED_MATCHES
```
`audience.expected.json` is `{}`: no expected answer, the model decides.
- Exit 0: a plan. Open it.
- Exit 3 `no_matching_grants`: correct, too. Only 5 verified grants are in use, and the system says
  "nothing fits" instead of inventing a grant.
Backup org numbers: 983758622 (Gjøvik Skiklubb), 976433416 (Faaberg IL), 970029028 (HHT, Hamar).

## 3. It refuses correctly (free, no model call, exit 3)
```
python harness/run.py demo/03_outside_innlandet.json
```
Prints `rejected: outside_innlandet (stage 1, exit 3)`. A club outside Innlandet stops before any model call.

## 4. Brreg goes down (free, exit 1)
```
$env:FAULT="brreg_500"; python harness/run.py --offline; Remove-Item Env:FAULT
```
Shows two retries with backoff (1 s, 2 s), then `upstream unavailable ... exit 1`. It fails safely and writes no half-finished plan.
(`brreg_500_once` recovers, but the retry line is not printed when it succeeds, so it does not show well.)

## 5. The test set: show the evidence, do not run it live
Open `docs/eval-logs/eval_2026-11-12_082151.log` and scroll to the table: **23/23 PASS, 0.95 USD**
(1 run per case, run the morning of the demo). Explain the groups from `eval/cases/CASES.md`: normal clubs,
boundary cases (deadline passed, amount too high, wrong municipality), bad input, prompt injection
(in grant text and in the idea), and Brreg/Claude being down. Mention the kill switch: a rolling
5 USD/24 h cap writes `out/HALTED` and stops all runs (it fired on 11.11, see `eval_2026-11-11_013508.log`).

## 6. Keeping the grants current (talk, show 1 folder)
The weekly `harness/catalog.py` indexes all 58 county grants. `harness/update_grants.py` checks "Sist endret"
and writes drafts to `context/grants_pending/`. A person verifies every fact before a grant goes into
`context/grants/`. That is why only 5 are live: a deliberate human-in-the-loop gate, not a code limit.

## Before
`Test-Path out/HALTED` must be `False`, and `claude --version` must work.
Model spend on 12.11 before the demo is about 1.4 USD, which leaves about 3.6 USD under the 5 USD cap.

## After (same day, required for the white paper)
Write `docs/meetings/2026-11-12-demo.md`: what ran, any FAIL seen live, and the feedback we got.
A FAIL on stage is not a disaster. It goes into the white paper, as the course asks.
Still owed after the demo: the 3-run full eval for task 013 and the task 014 judge runs (separate 24 h windows).

## If asked
- Only 5 of the 58 county grants are in use, because a person verifies every fact first.
- The test set uses a frozen copy of the grants (`eval/corpus/`), so results do not change when the
  live grant pages change.


Check 24h use:

$cut=(Get-Date).ToUniversalTime().AddHours(-24); (Get-Content out/cost_history.jsonl | ConvertFrom-Json | ? { [datetime]$_.logged_at -gt $cut } | Measure-Object total_cost_usd -Sum).Sum