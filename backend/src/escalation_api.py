"""Escalation Support API & Web Dashboard Server.

Provides REST endpoints to view and manage open human escalation requests,
plus serves the live web dashboard UI.
"""

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from db import (
    get_escalation,
    init_db,
    list_escalations,
    update_escalation_status,
)

logger = logging.getLogger("escalation_api")
logging.basicConfig(level=logging.INFO)

DASHBOARD_HTML_PATH = Path(__file__).parent / "escalation_dashboard.html"


class EscalationRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict | list, status_code: int = 200):
        body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_content: str, status_code: int = 200):
        body = html_content.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Serve Dashboard HTML on / or /dashboard
        if path in ("/", "/dashboard"):
            if DASHBOARD_HTML_PATH.exists():
                html = DASHBOARD_HTML_PATH.read_text(encoding="utf-8")
                self._send_html(html)
            else:
                self._send_json({"error": "Dashboard HTML file not found"}, 404)
            return

        # GET /api/escalations — list tickets
        if path == "/api/escalations":
            status_param = query.get("status", ["open"])[0]
            filter_status = None if status_param == "all" else status_param
            tickets = list_escalations(status=filter_status)
            self._send_json(tickets)
            return

        # GET /api/escalations/<id> — get single ticket
        if path.startswith("/api/escalations/"):
            esc_id = path.replace("/api/escalations/", "").strip()
            ticket = get_escalation(esc_id)
            if ticket:
                self._send_json(ticket)
            else:
                self._send_json({"error": f"Escalation {esc_id} not found"}, 404)
            return

        self._send_json({"error": "Not Found"}, 404)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/escalations/"):
            esc_id = path.replace("/api/escalations/", "").strip()
            content_length = int(self.headers.get("Content-Length", 0))
            body_data = self.rfile.read(content_length)

            try:
                payload = json.loads(body_data)
                new_status = payload.get("status")
                if not new_status:
                    self._send_json({"error": "Missing 'status' field"}, 400)
                    return

                updated = update_escalation_status(esc_id, new_status)
                if updated:
                    self._send_json(updated)
                else:
                    self._send_json({"error": f"Escalation {esc_id} not found"}, 404)
            except ValueError as e:
                self._send_json({"error": str(e)}, 400)
            except Exception as exc:
                self._send_json({"error": f"Internal error: {exc}"}, 500)
            return

        self._send_json({"error": "Not Found"}, 404)


def run_server(port: int = 8000):
    init_db()
    server_address = ("", port)
    httpd = HTTPServer(server_address, EscalationRequestHandler)
    logger.info("Escalation Dashboard API running at http://localhost:%d/", port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped.")


if __name__ == "__main__":
    run_server()
