# Contributing

## Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/homgorn/google-seo-automation.git
   cd google-seo-automation
   ```

2. Initialize the environment:
   ```bash
   cd project
   ./init.sh
   ```

3. Run tests:
   ```bash
   python -m pytest tests/ -q
   ```

4. Verify features:
   ```bash
   python scripts/verify_feature.py --all
   ```

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): subject
fix(scope): subject
docs(scope): subject
refactor(scope): subject
test(scope): subject
chore(scope): subject
```

The subject says what changed, not that work happened.

## Pull Request Flow

1. Create a feature branch: `git checkout -b feature/<name>`
2. Make changes, run tests
3. Run `python scripts/secret_scan.py` (must pass)
4. Open a PR with a clear description
5. Wait for CI to pass

## Code Style

- Python: PEP 8, type hints where helpful
- All scripts must handle UTF-8 output (Windows cp1252 issue)
- All mutations must be dry-run by default
- All API calls must handle auth failure, quota exhaustion, timeout, malformed response

## Adding a New API Source

1. Add discovery URL to `DISCOVERY_SOURCES` in `sync_wiki.py`
2. Run `python scripts/sync_wiki.py --full`
3. Verify with `python scripts/wiki_query.py stats`
4. Add tests to `tests/test_sync_wiki.py`
5. Update `docs/architecture.md` with measured endpoint counts