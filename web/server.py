"""Local web server for the grant navigator (task 017): live runs of harness/run.py.

Usage: python web/server.py [--port 8017]   then open http://127.0.0.1:8017/

Serves web/ and a small JSON API. Binds to 127.0.0.1 only: every live run spends the owner's
`claude` budget, so the server must not be reachable from other machines.
  GET  /api/health  -> {"ok": true, "running": bool}
  POST /api/run     -> start a run; body = input_request.json + {"offline": bool}; 409 if busy
  GET  /api/status  -> {"running", "stages", "log"} of the current or last run
  GET  /api/result  -> the bundle (web/bundle.py) of the last finished run; 404 before that
One run at a time, because harness/run.py wipes out/ at the start. Standard library only.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import bundle

WEB = Path(__file__).resolve().parent
ROOT = WEB.parent
RUN_PY = ROOT / "harness" / "run.py"
REQUEST_KEYS = ("orgnr", "project_idea", "requested_amount_nok", "output_language")
MAX_BODY = 10_000


class Run:
    """State of the current or last run, shared between request threads."""

    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.log = []
        self.result = None

    def start(self, request, offline):
        with self.lock:
            if self.running:
                return False
            self.running, self.log, self.result = True, [], None
        threading.Thread(target=self._run, args=(request, offline), daemon=True).start()
        return True

    def _run(self, request, offline):
        mode = "offline" if offline else "live"
        code = 1
        try:
            with tempfile.TemporaryDirectory() as tmp:
                req_path = Path(tmp) / "input_request.json"
                with open(req_path, "w", encoding="utf-8") as f:
                    json.dump(request, f, ensure_ascii=False)
                cmd = [sys.executable, str(RUN_PY), str(req_path)] + (["--offline"] if offline else [])
                # A visitor's request has no author expectations: empty EXPECTED_MATCHES turns
                # off the fixed Hamar answer key in eval/check_matches.py (all other checks run).
                env = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1",
                       "EXPECTED_MATCHES": ""}
                proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                        errors="replace", env=env)
                for line in proc.stdout:
                    with self.lock:
                        self.log.append(line.rstrip("\n"))
                code = proc.wait()
            result = bundle.build(request, code, self.log, mode)
        except Exception as e:  # report, never leave the page waiting forever
            with self.lock:
                self.log.append(f"server error: {type(e).__name__}: {e}")
            result = {"mode": mode, "request": request, "exit": 1, "stages": [], "entity": None,
                      "plan": None, "rejection": {"reason": "server_error", "detail": str(e)},
                      "excluded": [], "cost_usd": None}
        with self.lock:
            self.result, self.running = result, False

    def status(self):
        with self.lock:
            return {"running": self.running, "stages": bundle.parse_stages(self.log),
                    "log": list(self.log), "done": self.result is not None}


RUN = Run()


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if not self.path.startswith("/api/status"):
            super().log_message(fmt, *args)

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/health":
            return self.send_json(200, {"ok": True, "running": RUN.running})
        if path == "/api/status":
            return self.send_json(200, RUN.status())
        if path == "/api/result":
            if RUN.result is None:
                return self.send_json(404, {"error": "no finished run yet"})
            return self.send_json(200, RUN.result)
        if path.startswith("/api/"):
            return self.send_json(404, {"error": "unknown endpoint"})
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/run":
            return self.send_json(404, {"error": "unknown endpoint"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self.send_json(400, {"error": "request body missing or too large"})
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self.send_json(400, {"error": "request body is not JSON"})
        if not isinstance(body, dict):
            return self.send_json(400, {"error": "request body must be a JSON object"})
        # Only the request fields reach run.py; harness/entity.py validates them (exit 3).
        request = {k: body[k] for k in REQUEST_KEYS if k in body and body[k] is not None}
        if not RUN.start(request, bool(body.get("offline"))):
            return self.send_json(409, {"error": "a run is already in progress"})
        return self.send_json(202, {"started": True})


def main(argv):
    parser = argparse.ArgumentParser(description="Local web UI with live runs (task 017)")
    parser.add_argument("--port", type=int, default=8017)
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(WEB)))
    print(f"Grant navigator: http://127.0.0.1:{args.port}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
