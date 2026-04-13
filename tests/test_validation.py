from app import validate_email


def test_valid_email():
    result = validate_email("hello@company.com")
    assert result.status == "valid"
    assert result.score >= 70


def test_disposable_email():
    result = validate_email("test@mailinator.com")
    assert result.is_disposable is True
    assert result.status in {"invalid", "risky"}


def test_bad_format():
    result = validate_email("bad-email")
    assert result.status == "invalid"
    assert result.score == 0
