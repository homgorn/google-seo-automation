# Google SEO Automation

Automated Google Analytics 4, Google Tag Manager, Google Search Console,
Google Ads and AI Overviews (AEO) workflows over a **self-updating internal
knowledge base** of Google APIs, built from official machine-readable discovery
documents.

> Status: knowledge base, tooling and 116 regression tests are operational.
> GA4/GTM/GSC/Ads integrations are scaffolded and verified; live API calls
> require credentials (see `project/.env.example`).

---

## What works

- **312 API endpoints** extracted from 7 Google Discovery documents automatically
- **Full-text search** over the wiki (SQLite FTS5, zero external dependencies)
- **Knowledge graph** — 123 subject-predicate-object triples over 12 entities
- **Multi-level indexes** — Markdown, JSON, per-source, plus a machine-readable graph
- **Change detection** via SHA256 + `change_log` audit trail
- **Freshness checks** with a 14-day threshold and cron scheduling
- **116 regression tests** covering 12 defects found during development
- **8 of 11 features** verified (PASS); 3 blocked on external credentials only
- **Mutation guard** — Google Ads budgets and GTM publishing require explicit
  `ALLOW_MUTATIONS=1`

## Quick start

```bash
cd project

# 1. Check environment and install dependencies
./init.sh

# 2. Create / update database schema (idempotent, with migrations)
python scripts/init_db.py

# 3. Fetch fresh documentation from Google
python scripts/sync_wiki.py --full

# 4. Regenerate wiki indexes and the knowledge graph
python scripts/wiki_index.py

# 5. Verify everything is up to date
python scripts/sync_wiki.py --check-freshness
```

> `sync_wiki.py`, `wiki_query.py` and `wiki_index.py` run on the **Python 3.10+
> standard library**. No `pip install` is needed to read or sync the wiki.

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

## Project structure

```
├── README.md               this file (+ 6 locales)
├── LICENSE                 MIT
├── SECURITY.md             reporting, secret handling, known considerations
├── CONTRIBUTING.md         local dev, commit convention, PR flow
├── CODE_OF_CONDUCT.md
├── CHANGELOG.md
├── .github/
│   ├── workflows/ci.yml    tests + coverage + secret scan + weekly refresh
│   ├── ISSUE_TEMPLATE/     bug report, feature request
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── locales.json        locale parity index
└── project/
    ├── wiki/               Markdown knowledge source + generated indexes
    │   ├── index.md        main index
    │   ├── index.json      machine-readable index
    │   ├── _data/          knowledge graph: entities, triples, graph stats
    │   └── <source>/       per-source index
    ├── data/wiki.db        SQLite: docs, endpoints, changelog, FTS5 (not committed)
    ├── scripts/
    │   ├── common.py       shared Verdict, guards, validators, doc routing
    │   ├── init_db.py      schema + idempotent migrations
    │   ├── sync_wiki.py    discovery fetch + markdown ingest + freshness
    │   ├── wiki_index.py   multi-level indexes + knowledge graph
    │   ├── wiki_query.py   CLI search
    │   ├── embed_wiki.py   embeddings (optional)
    │   ├── ga4_automation.py / gtm_automation.py / gsc_automation.py
    │   ├── ads_automation.py / aeo_automation.py
    │   ├── openchamber_sync.py
    │   ├── verify_feature.py   automated feature verification
    │   └── secret_scan.py      secret detection
    ├── tests/              116 regression tests
    ├── docs/
    │   ├── specs/          SPEC-001 platform specification
    │   ├── adr/            4 architecture decision records
    │   ├── runbooks/       credential rotation, disaster recovery, cost
    │   ├── architecture.md measured facts, risks, gaps
    │   ├── progress.md     change log
    │   └── ROADMAP.md      stages, blockers, next chunks
    ├── .opencode/agents/   7 agent roles
    ├── feature_list.json   11 features with acceptance criteria
    ├── AGENTS.md           agent routing
    └── init.sh             environment check
```

## Verification

```bash
# All tests
python -m pytest tests/ -q

# Verify every feature
python scripts/verify_feature.py --all

# Check for secrets
python scripts/secret_scan.py

# Check wiki freshness
python scripts/sync_wiki.py --check-freshness

# Check wiki indexes are current
python scripts/wiki_index.py --verify
```

## Documentation

- [Specification](project/docs/specs/SPEC-001-platform.md) — goals, principles, requirements
- [Architecture](project/docs/architecture.md) — measured facts, risks, gaps
- [ADRs](project/docs/adr/) — 4 architecture decision records
- [Roadmap](project/docs/ROADMAP.md) — stages, blockers, next chunks
- [Progress log](project/docs/progress.md) — change history
- [API reference](project/wiki/api-reference.md) — full Google/Microsoft API reference
- [Runbooks](project/docs/runbooks/) — credential rotation, disaster recovery, cost monitoring

## Security

- `.env` is in `.gitignore`; template is `project/.env.example`
- Secrets come from environment variables only, never hardcoded
- Mutations are dry-run by default (`ALLOW_MUTATIONS=0`)
- Google Ads budgets are validated in micros with a configurable cap
- The database is a cache — regenerated from sources, not committed
- Secret scan runs in CI on every push

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for local development setup, commit
conventions, and the pull-request flow.

## License

[MIT](LICENSE)