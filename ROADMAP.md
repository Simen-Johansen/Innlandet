# Roadmap: Volunteer Grant Navigator (Tilskudds-los for frivilligheten)

Today is W44. Compulsory 2 is due **Fri 30.10**, so tasks 001–008 are the walking skeleton.
Every stage should exist, even if it is crude, before any stage is made good (W40: "thin, end to end, runs").

## The chain (architecture figure for the report)

```
input_request.json
  │
  ▼  [1] entity     harness/entity.py      → out/entity.json        check: eval/check_entity.py
  ▼  [2] grants     context/grants/*.md    (curated, sanitized)      check: eval/check_grants.py
  ▼  [3] filter     harness/filter.py      → out/eligible.json      check: eval/check_filter.py
  │                                         + out/match_input.md (context filter for stage 4)
  ▼  [4] match      claude -p (prompts/match.md)  → out/matches.json   check: eval/check_matches.py   (max 3 tries)
  ▼  [5] guide      claude -p (prompts/guide.md)  → out/plan.json      check: eval/check_plan.py      (max 3 tries)
  ▼  [6] render     harness/render.py      → out/grant_action_plan.md  (code, not LLM)
```

Code decides the order. The model only does stages 4 and 5, which are the two steps that need judgment.
Every arrow is a file and a check.

## Milestones (working backwards from the deadlines)

| Date | Milestone | Tasks | Tag |
|---|---|---|---|
| Thu 29.10 | Stages 1–3 run offline, checks green | 001, 002, 003 | – |
| Fri 30.10 | **C2:** full chain runs from one command, offline, with CI | 004–008 | `c2-skeleton` |
| W45 (2–8.11) | Test set and evaluation harness, live grant fetcher | 009, 010 | `w45-eval` |
| W46 (9–15.11) | Safe operation and first stress test, then live demo | 011, 012 | `demo` |
| W47 (16–22.11) | Second stress test, LLM-as-judge, demo feedback fixed | 013, 014 | – |
| W48 (23–29.11) | Freeze features; write the white paper; full eval run for the appendix | – | – |
| Thu 03.12 11:59 | White paper on Wiseflow | – | `exam` (never moved) |

If you are behind on Fri 30.10, cut depth, not stages. For example, use 2 grant files instead of 4, or skip the retry loop.

## Every task, the same loop (W40)

1. **Author** commits the check first (red), then writes `tasks/NNN-*.md`
2. **Driver** runs `/plan Implement tasks/NNN-*.md`, reviews the plan, and approves
3. The check decides. On failure, fix the spec or the plan, never the check
4. **Author** reviews the diff and merges. Add one line to `docs/prompt-log.md` whenever agent output was corrected
5. `/clear` before the next task

Swap Author and Driver roles every task. Write one meeting report per week in `docs/meetings/`. The exam requires at least 8.
