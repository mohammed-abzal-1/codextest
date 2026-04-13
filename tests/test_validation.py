import app
from app import to_csv, validate_email


def test_valid_email(monkeypatch):
    monkeypatch.setattr(app, "has_dns_record", lambda domain: True)
    result = validate_email("hello@company.com")
    assert result.status == "valid"
    assert result.score >= 70
    assert result.normalized_email == "hello@company.com"


def test_disposable_email(monkeypatch):
    monkeypatch.setattr(app, "has_dns_record", lambda domain: True)
    result = validate_email("test@mailinator.com")
    assert result.is_disposable is True
    assert result.status in {"invalid", "risky"}


def test_bad_format():
    result = validate_email("bad-email")
    assert result.status == "invalid"
    assert result.score == 0


def test_typo_suggestion(monkeypatch):
    monkeypatch.setattr(app, "has_dns_record", lambda domain: True)
    result = validate_email("user@gamil.com")
    assert result.suggested_correction == "user@gmail.com"


def test_csv_export_headers():
    csv_text = to_csv([
        {
            "email": "a@example.com",
            "normalized_email": "a@example.com",
            "domain": "example.com",
            "status": "valid",
            "score": 95,
            "reason": "Looks good",
            "suggested_correction": None,
            "has_dns_record": True,
            "is_free_provider": False,
            "is_disposable": False,
            "is_role_account": False,
        }
    ])
    assert "normalized_email" in csv_text
    assert "a@example.com" in csv_text
