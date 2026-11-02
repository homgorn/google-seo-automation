# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-31

### Added
- Knowledge base infrastructure: SQLite + FTS5, 312 API endpoints from 7 Google Discovery documents
- `sync_wiki.py` — automated discovery document sync with SHA256 change detection
- `wiki_query.py` — CLI search (stats, endpoints, search, endpoint, collisions, changes)
- `embed_wiki.py` — embedding pipeline (chromadb, graceful fallback)
- `gsc_automation.py` — Google Search Console automation (6 steps)
- `ads_automation.py` — Google Ads automation (GAQL, 4 channels: SEARCH, DISPLAY, PMax, VIDEO)
- `gtm_automation.py` — Google Tag Manager automation (workspace lifecycle, tags, triggers, vars, versions, audit)
- `aeo_automation.py` — Answer Engine Optimization (citation tracking, E-E-A-T, schema, competitor, content)
- `ga4_automation.py` — Google Analytics 4 automation (8 steps, service account + OAuth)
- `openchamber_sync.py` — OpenChamber session synchronization
- `verify_feature.py` — automated feature verification (11 features)
- 7 automation roles with explicit I/O contracts
- 16 regression tests covering 4 bugs found during development
- 3 runbooks (credential rotation, disaster recovery, cost monitoring)
- `.env.example` — environment variable template
- `init.sh` — environment check and setup

### Fixed
- GTM discovery recursion was conditional (3 → 106 endpoints)
- UNIQUE(method, path) collapsed path templates (312 → 162 endpoints, 150 lost)
- Naive datetime TypeError in freshness check
- Windows cp1252 encoding crash on Cyrillic output

### Known Issues
- Merchant API v1 publishes no discovery methods (0 endpoints)
- Bing Ads v13 has no discovery document
- Google Ads v18 has no discovery document (GAQL from docs only)