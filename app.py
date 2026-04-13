from __future__ import annotations

import csv
import io
import json
import re
import socket
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
COMMON_DOMAIN_TYPOS = {
    "gamil.com": "gmail.com",
    "gnail.com": "gmail.com",
    "yaho.com": "yahoo.com",
    "outllok.com": "outlook.com",
    "hotnail.com": "hotmail.com",
}


@dataclass
class ValidationResult:
    email: str
    normalized_email: str
    domain: str
    status: str
    score: int
    reason: str
    suggested_correction: str | None
    has_dns_record: bool
    is_free_provider: bool
    is_disposable: bool
    is_role_account: bool


def normalize_email(email: str) -> str:
    return email.strip().lower()


def has_dns_record(domain: str) -> bool:
    try:
        socket.getaddrinfo(domain, None)
        return True
    except OSError:
        return False


def evaluate_status(score: int, dns_ok: bool) -> str:
    if score < 40:
        return "invalid"
    if not dns_ok:
        return "risky"
    if score < 70:
        return "risky"
    return "valid"


def validate_email(email: str) -> ValidationResult:
    original = email
    email = normalize_email(email)

    if not email:
        return ValidationResult(original, "", "", "invalid", 0, "Email is empty", None, False, False, False, False)

    if not EMAIL_REGEX.match(email):
        return ValidationResult(original, email, "", "invalid", 0, "Invalid email format", None, False, False, False, False)

    local_part, domain = email.split("@", 1)
    is_disposable = domain in DISPOSABLE_DOMAINS
    is_free_provider = domain in FREE_PROVIDERS
    is_role_account = local_part in ROLE_PREFIXES or local_part.startswith("team+")
    suggested = f"{local_part}@{COMMON_DOMAIN_TYPOS[domain]}" if domain in COMMON_DOMAIN_TYPOS else None

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

    if suggested:
        score -= 10
        reasons.append("Domain typo detected")

    score = max(score, 0)
    dns_ok = has_dns_record(domain)
    if not dns_ok:
        reasons.append("Domain has no DNS record")

    status = evaluate_status(score, dns_ok)
    reason = ", ".join(dict.fromkeys(reasons)) if reasons else "Looks good"
    return ValidationResult(
        email=original,
        normalized_email=email,
        domain=domain,
        status=status,
        score=score,
        reason=reason,
        suggested_correction=suggested,
        has_dns_record=dns_ok,
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


def to_csv(results: list[dict]) -> str:
    if not results:
        return "email,status,score,reason\n"

    fieldnames = [
        "email",
        "normalized_email",
        "domain",
        "status",
        "score",
        "reason",
        "suggested_correction",
        "has_dns_record",
        "is_free_provider",
        "is_disposable",
        "is_role_account",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)
    return output.getvalue()


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
        if parsed.path == "/api/health":
            self._send_json({"status": "ok"})
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
            self._send_json({"summary": summary, "results": results, "csv": to_csv(results)})
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
