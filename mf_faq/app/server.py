"""Zero-dependency HTTP front end.

    python3 -m app.server            # http://127.0.0.1:8000
    python3 -m app.server --port 9000

Binds to loopback by default. Questions are answered in-process and are never
written to disk or to a log line - the PII gate in guardrails.py depends on the
raw question not outliving the request.
"""

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .assistant import Assistant

UI_PATH = os.path.join(os.path.dirname(__file__), "ui.html")
MAX_BODY = 8 * 1024  # a question is never this long; anything bigger is refused

ASSISTANT = Assistant()


class Handler(BaseHTTPRequestHandler):
    server_version = "MFFaq/1.0"

    # Silence the default access log: it would echo request paths, and we do not
    # want any user input landing in a log.
    def log_message(self, fmt, *args):
        pass

    def _send(self, status, payload, content_type="application/json; charset=utf-8"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            with open(UI_PATH, "rb") as handle:
                self._send(200, handle.read(), "text/html; charset=utf-8")
        elif path == "/api/scope":
            self._send(200, {
                "amc": ASSISTANT.meta["amc"],
                "schemes": ASSISTANT.scheme_names(),
                "sources": len(ASSISTANT.sources),
                "last_updated_from_sources": ASSISTANT.meta["last_updated_from_sources"],
            })
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/ask":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._send(400, {"error": "bad content-length"})
            return
        if length > MAX_BODY:
            self._send(413, {"error": "question too long"})
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            question = payload.get("question", "")
        except (ValueError, UnicodeDecodeError):
            self._send(400, {"error": "bad json"})
            return
        self._send(200, ASSISTANT.ask(question if isinstance(question, str) else ""))


def main():
    parser = argparse.ArgumentParser(description="Groww Mutual Fund FAQ assistant")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("Groww Mutual Fund FAQ - facts-only, no investment advice.")
    print("Serving on http://%s:%d  (Ctrl-C to stop)" % (args.host, args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
