# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue.
2. Email the maintainer or open a private security advisory on GitHub.
3. Include: description, reproduction steps, impact assessment.

We aim to respond within 48 hours and provide a fix within 14 days.

## Secret Handling

This project handles Google Cloud credentials, OAuth tokens, and API keys.

- **Never commit** `.env`, `service-account*.json`, or any credential files.
- All secrets come from environment variables (see `.env.example`).
- Run `python scripts/secret_scan.py` before every commit.
- The database (`data/wiki.db`) is a cache and is not committed.

## Known Security Considerations

- The `init.sh` script creates `.env` from template — fill it manually.
- Google Ads budgets are validated in micros to prevent accidental overspend.
- Mutations are dry-run by default (`ALLOW_MUTATIONS=0`).
- The Indexing API has a 200 requests/day default quota — do not abuse.