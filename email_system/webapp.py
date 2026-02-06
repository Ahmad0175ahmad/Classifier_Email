from __future__ import annotations

import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .worker import main as worker_main


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path in ("/", "/health", "/healthz"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"not found")

    def log_message(self, format: str, *args) -> None:  # noqa: A003 - match base signature
        return


def _start_worker() -> None:
    try:
        worker_main()
    except Exception as exc:
        print(f"Worker crashed: {exc}")


def main() -> None:
    port = int(os.getenv("PORT", "8000"))

    thread = threading.Thread(target=_start_worker, daemon=True)
    thread.start()

    server = ThreadingHTTPServer(("", port), HealthHandler)
    print(f"Health server listening on :{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
