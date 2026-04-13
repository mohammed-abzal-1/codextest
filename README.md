# Email Validation App (ZeroBounce-style)

A lightweight, dependency-free email validation web app inspired by ZeroBounce.

## Features
- Single email validation endpoint/UI
- Batch validation from CSV or newline-separated input
- Risk scoring (0-100) and status (`valid`, `risky`, `invalid`)
- Flags for disposable domains, free providers, and role-based accounts
- Domain DNS existence check
- Common typo suggestion for popular mail domains
- CSV export of batch results

## Run locally

```bash
python app.py
```

Then open http://127.0.0.1:5000.

## API

### `GET /api/health`
Returns `{"status":"ok"}`.

### `POST /api/validate`
```json
{ "email": "name@example.com" }
```

### `POST /api/validate-batch`
```json
{ "emails": "alice@example.com\nbob@mailinator.com" }
```
Returns summary, detailed results, and a `csv` string for export.
