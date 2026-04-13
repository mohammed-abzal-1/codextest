# Email Validation App (ZeroBounce-style)

This is a lightweight email validation web app inspired by ZeroBounce.

## Features
- Single email validation endpoint/UI
- Batch validation from CSV or newline-separated input
- Risk scoring (0-100)
- Flags for:
  - disposable domains
  - free mail providers
  - role-based mailboxes
  - risky TLDs

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000.

## API

### `POST /api/validate`
```json
{ "email": "name@example.com" }
```

### `POST /api/validate-batch`
```json
{ "emails": "alice@example.com\nbob@mailinator.com" }
```

