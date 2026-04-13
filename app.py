from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

BASE_DIR = Path(__file__).parent

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

DISPOSABLE_DOMAINS = {
    "mailinator.com",
    "10minutemail.com",
    "guerrillamail.com",
    "tempmail.com",
    "yopmail.com",
}

FREE_PROVIDERS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "aol.com",
}

ROLE_PREFIXES = {
    "admin",
    "billing",
    "contact",
    "hello",
    "hr",
    "info",
    "marketing",
    "no-reply",
    "noreply",
    "ops",
    "sales",
    "support",
    "team",
}

RISKY_TLDS = {"zip", "xyz", "click", "work", "loan", "top"}


@dataclass
class ValidationResult:
    email: str
    status: str
    score: int
    reason: str
    is_free_provider: bool
    is_disposable: bool
    is_role_account: bool


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> ValidationResult:
    original = email
    email = normalize_email(email)

    if not email:
        return ValidationResult(original, "invalid", 0, "Email is empty", False, False, False)

    if not EMAIL_REGEX.match(email):
        return ValidationResult(original, "invalid", 0, "Invalid email format", False, False, False)

    local_part, domain = email.split("@", 1)
    is_disposable = domain in DISPOSABLE_DOMAINS
    is_free_provider = domain in FREE_PROVIDERS
    is_role_account = local_part in ROLE_PREFIXES or local_part.startswith("team+")

    tld = domain.rsplit(".", 1)[-1]
    score = 100
    reasons: list[str] = []

    if is_disposable:
        score -= 65
        reasons.append("Disposable domain")

    if is_role_account:
        score -= 20
        reasons.append("Role-based mailbox")

    if tld in RISKY_TLDS:
        score -= 15
        reasons.append("Risky TLD")

    if len(local_part) <= 2:
        score -= 10
        reasons.append("Short local part")

    if ".." in email:
        score -= 10
        reasons.append("Consecutive dots")

    score = max(score, 0)

    if score < 40:
        status = "invalid"
    elif score < 70:
        status = "risky"
    else:
        status = "valid"

    reason = ", ".join(reasons) if reasons else "Looks good"
    return ValidationResult(
        email=original,
        status=status,
        score=score,
        reason=reason,
        is_free_provider=is_free_provider,
        is_disposable=is_disposable,
        is_role_account=is_role_account,
    )


def parse_batch_input(raw_input: str) -> Iterable[str]:
    buffer = io.StringIO(raw_input.strip())
    reader = csv.reader(buffer)
    for row in reader:
        for value in row:
            email = value.strip()
            if email:
                yield email


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_file(BASE_DIR / "templates" / "index.html", "text/html")
            return
        if parsed.path == "/static/styles.css":
            self._serve_file(BASE_DIR / "static" / "styles.css", "text/css")
            return
        if parsed.path == "/static/app.js":
            self._serve_file(BASE_DIR / "static" / "app.js", "application/javascript")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/validate":
            email = str(payload.get("email", ""))
            result = asdict(validate_email(email))
            self._send_json(result)
            return

        if parsed.path == "/api/validate-batch":
            raw = str(payload.get("emails", ""))
            results = [asdict(validate_email(email)) for email in parse_batch_input(raw)]
            summary = {
                "total": len(results),
                "valid": sum(1 for r in results if r["status"] == "valid"),
                "risky": sum(1 for r in results if r["status"] == "risky"),
                "invalid": sum(1 for r in results if r["status"] == "invalid"),
            }
            self._send_json({"summary": summary, "results": results})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def run(port: int = 5000):
    server = ThreadingHTTPServer(("127.0.0.1", port), AppHandler)
    print(f"Listening on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
