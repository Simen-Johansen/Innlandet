"""Stop hook: the agent may not say "done" while the checks fail.

Exit 0 lets the agent stop. Exit 2 sends stderr back to the agent so it keeps working.
Only runs when Python files have uncommitted changes, so chat-only sessions stay fast.
"""

import json
import subprocess
import sys

CHECKS = [
    ["uv", "run", "ruff", "check", "."],
    ["uv", "run", "ruff", "format", "--check", "."],
    ["uv", "run", "pytest", "-q"],
]


def main() -> int:
    event = json.load(sys.stdin)
    if event.get("stop_hook_active"):
        return 0  # already sent back once: let it stop, or it could loop forever

    changed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        check=False,
        capture_output=True,
        text=True,
    ).stdout
    if not any(line.rstrip().endswith(".py") for line in changed.splitlines()):
        return 0

    for cmd in CHECKS:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Check failed: {' '.join(cmd)}\n{result.stdout}{result.stderr}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
