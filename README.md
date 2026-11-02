# Google SEO Automation

Automated Google Analytics 4, Google Tag Manager, Google Search Console,
Google Ads and AI Overviews (AEO) workflows over a **self-updating internal
knowledge base** of Google APIs, built from official machine-readable discovery
documents.

> Status: knowledge-base infrastructure is operational. GA4/GTM/GSC/Ads
> integrations are scaffolded and verified; live API calls require credentials
> (see `.env.example`).

---

## What works

- **312 API endpoints** extracted from 7 Google Discovery documents automatically
- **Full-text search** over the wiki (SQLite FTS5, zero external dependencies)
- **Change detection** via SHA256 + `change_log` audit trail
- **Freshness checks** with a 14-day threshold and cron scheduling
- **16 regression tests** covering 4 bugs found during development
- **7 agent roles** with explicit input/output contracts (explorer, runner,
  verifier, critic, migrator, implementer, orchestrator)
- **8 of 11 features** verified (PASS); 3 blocked on external credentials only

## Quick start

```bash
cd project

# 1. Check environment and install dependencies
./init.sh

# 2. Create / update database schema (idempotent, with migrations)
python scripts/init_db.py

# 3. Fetch fresh documentation from Google
python scripts/sync_wiki.py --full

# 4. Verify everything is up to date
python scripts/sync_wiki.py --check-freshness
```

> `sync_wiki.py` and `wiki_query.py` run on the **Python 3.10+ standard
> library**. No `pip install` is needed to read or sync the wiki. Additional
> dependencies (chromadb, google-api-python-client, etc.) are for future
> integrations and are listed in `requirements.txt`.

## Using the wiki

```bash
python scripts/wiki_query.py stats                      # overview
python scripts/wiki_query.py endpoints --source gtm     # endpoints by source
python scripts/wiki_query.py search "workspace tag"     # full-text search
python scripts/wiki_query.py endpoint workspaces.tags.create
python scripts/wiki_query.py collisions --source ga4_admin  # template collisions
python scripts/wiki_query.py changes --limit 10         # change history
```

## API sources (measured 2026-10-12)

| Source | Discovery document | Endpoints |
|--------|-------------------|-----------|
| Google Analytics Admin API v1alpha | `analyticsadmin.googleapis.com` | 166 |
| Google Tag Manager API v2 | `tagmanager.googleapis.com` | 106 |
| Google Business Profile API v1 | `mybusinessbusinessinformation.googleapis.com` | 15 |
| Google Analytics Data API v1beta | `analyticsdata.googleapis.com` | 11 |
| Google Search Console API v1 | `searchconsole.googleapis.com` | 11 |
| Google Indexing API v3 | `indexing.googleapis.com` | 2 |
| PageSpeed Insights API v5 | `pagespeedonline.googleapis.com` | 1 |
| Google Merchant API v1 | `merchantapi.googleapis.com` | 0 (no methods published) |
| **Total** | | **312** |

Full analysis, including non-working URLs and coverage gaps:
[`docs/architecture.md`](project/docs/architecture.md).

## Project structure

```
project/
├── wiki/                  Markdown knowledge source (committed)
├── data/wiki.db           SQLite: docs, endpoints, changelog, FTS5 (not committed)
├── scripts/
│   ├── init_db.py         Schema + idempotent migrations
│   ├── sync_wiki.py       Discovery fetch + markdown ingest + freshness
│   ├── wiki_query.py      CLI search over the wiki
│   ├── embed_wiki.py      Embeddings (chromadb, optional)
│   ├── gsc_automation.py  Google Search Console automation
│   ├── ads_automation.py  Google Ads automation (GAQL, 4 channels)
│   ├── gtm_automation.py  Google Tag Manager automation
│   ├── aeo_automation.py  Answer Engine Optimization
│   ├── ga4_automation.py  Google Analytics 4 automation
│   ├── openchamber_sync.py OpenChamber session sync
│   └── verify_feature.py  Automated feature verification
├── tests/                 Regression tests (16 tests)
├── docs/
│   ├── architecture.md    Measured facts, risks, gaps
│   ├── progress.md        Progress log
│   └── runbooks/          Credential rotation, DR, cost monitoring
├── .opencode/agents/      7 agent roles
├── feature_list.json      11 features, all pending verifier sign-off
├── AGENTS.md              Agent routing
└── init.sh                Environment check
```

## Agents

| Agent | Role | Model tier |
|-------|------|------------|
| `explorer` | Read-only codebase and API research | Cheap |
| `runner` | Noisy builds and test suites | Cheap |
| `verifier` | **Mandatory** before any `passes: true` | Cheap |
| `critic` | Adversarial review | Strong |
| `migrator` | Bulk mechanical edits | Cheap |
| `implementer` | One feature at a time | Strong |
| `orchestrator` | OpenChamber sessions and scheduling | Cheap |

## Security

- `.env` is in `.gitignore`; template is `.env.example`
- Secrets come from environment variables only, never hardcoded
- Mutations are dry-run by default (`ALLOW_MUTATIONS=0`)
- Google Ads budgets are in micros with a configurable cap
- The database is a cache — it is regenerated from sources, not committed

## Verification

```bash
# Run all tests
python -m pytest tests/ -q

# Verify all features
python scripts/verify_feature.py --all

# Check for secrets
python scripts/secret_scan.py

# Check wiki freshness
python scripts/sync_wiki.py --check-freshness
```

## Documentation

- [Architecture](project/docs/architecture.md) — measured facts, risks, gaps
- [Progress log](project/docs/progress.md) — change history
- [API reference](project/wiki/api-reference.md) — full Google/Microsoft API reference
- [Runbooks](project/docs/runbooks/) — credential rotation, disaster recovery, cost monitoring

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for local development setup, commit
conventions, and the pull-request flow.

## License

[MIT](LICENSE)