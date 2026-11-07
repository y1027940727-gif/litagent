"""Minimal HTTP wrapper for Cloud Run (stdlib only). POST /ask {"question": "..."}"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from .agent import Agent
from .llm import Gemini

_agent = None


def agent():
    global _agent
    if _agent is None:
        _agent = Agent(Gemini())
    return _agent


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send(200, {"status": "ok"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            q = json.loads(self.rfile.read(n))["question"]
        except Exception:
            return self._send(400, {"error": 'send {"question": "..."}'})
        try:
            r = agent().run(q)
            self._send(200, {"answer": r.answer, "check": r.check, "retrieved": r.retrieved_ids})
        except Exception as e:
            self._send(500, {"error": str(e)})


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), H).serve_forever()
