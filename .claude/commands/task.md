---
description: Run one task through the loop (spec, plan, run, verify)
argument-hint: NNN
disable-model-invocation: true
---
Read tasks/$ARGUMENTS-*.md. If there is no such file, stop and say so.

1. Check `git status` is clean and you are on a branch named `task/$ARGUMENTS-...`, not main.
2. Run the Acceptance commands once before changing anything and show that they fail (red first).
3. Propose a plan: files you will touch, assumptions you made, new dependencies, the
   verification commands. Wait for my approval before editing anything.
4. Implement. Stay inside the task's scope; say so if you made any unplanned change.
5. Run every command under "## Acceptance" and paste the output.

Do not touch eval/. If I rejected or corrected anything, add an entry to docs/prompt-log.md.
