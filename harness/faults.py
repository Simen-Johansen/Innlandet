"""Fault injection for stress test B, dependency failure (task 013).

A no-op unless the environment variable FAULT is set. FAULT holds one or more values separated
by commas:

  brreg_timeout    every Brreg attempt raises TimeoutError (at once: a hang is simulated, not real)
  brreg_500        every Brreg attempt raises HTTP 500
  brreg_429        every Brreg attempt raises HTTP 429
  brreg_500_once   only the first Brreg attempt raises HTTP 500 (shows the retry recovers)
  brreg_429_once   only the first Brreg attempt raises HTTP 429
  brreg_silent     200 OK, but registrertIFrivillighetsregisteret is missing from the response
  claude_missing   `claude` is not on PATH
  claude_badjson   `claude` exits 1 with non-JSON output; the real CLI is never called

The hooks sit in front of the real call, in offline mode too, so eval cases can use them.
Standard library only.
"""

import io
import os
import urllib.error

FAULTS = {"brreg_timeout", "brreg_500", "brreg_429", "brreg_500_once", "brreg_429_once",
          "brreg_silent", "claude_missing", "claude_badjson"}
_brreg_attempts = 0


def active():
    """The set of injected faults; unknown values stop the run instead of being ignored."""
    faults = {f.strip() for f in os.environ.get("FAULT", "").split(",") if f.strip()}
    unknown = faults - FAULTS
    if unknown:
        raise ValueError(f"unknown FAULT value(s) {sorted(unknown)}, known: {sorted(FAULTS)}")
    return faults


def _http_error(url, code):
    return urllib.error.HTTPError(url, code, f"injected fault (HTTP {code})", {}, io.BytesIO(b""))


def brreg_request(url):
    """Call before every Brreg attempt: raises the injected failure, if any."""
    global _brreg_attempts
    _brreg_attempts += 1
    faults = active()
    if "brreg_timeout" in faults:
        raise TimeoutError("injected fault: Brreg request timed out")
    for code in (500, 429):
        if f"brreg_{code}" in faults or (f"brreg_{code}_once" in faults and _brreg_attempts == 1):
            raise _http_error(url, code)


def brreg_response(raw):
    """Call on every Brreg response: brreg_silent drops the Frivillighetsregisteret field."""
    if "brreg_silent" in active() and isinstance(raw, dict):
        raw = {k: v for k, v in raw.items() if k != "registrertIFrivillighetsregisteret"}
    return raw


def claude_path(path):
    """Wrap shutil.which("claude"): claude_missing hides the CLI."""
    return None if "claude_missing" in active() else path


def claude_badjson():
    """True when the claude call must be replaced by a failing, non-JSON reply."""
    return "claude_badjson" in active()


BADJSON_STDOUT = "Error: injected fault, the claude CLI printed this instead of JSON\n"
