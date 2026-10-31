# OpenChamber Session Template — Chunk A: F005 GSC Automation

## Feature
F005 — Google Search Console automation (searchanalytics, sitemap, URL inspection, indexing)

## Context (from wiki)
Документ: `docs/architecture.md` → раздел 4 (GSC)
Источник: `gsc` (searchconsole:v1) — 11 эндпоинтов
DB: `sqlite3 data/wiki.db` — таблицы `api_docs`, `api_endpoints`, `guides`

## Verifier Checklist (MANDATORY before passes=true)

- [ ] S01: `python scripts/gsc_automation.py --step S01 --site-url <url>` → PASS или BLOCKED
- [ ] S02: sitemap guide записан в БД (`SELECT * FROM guides WHERE guide_type='setup'`)
- [ ] S03: пример `searchanalytics` запроса в выводе
- [ ] S04: пример `url:inspect` в выводе
- [ ] S05: `indexing` publish описан
- [ ] S06: batch (до 100 URL) описан
- [ ] `init.sh` прошёл
- [ ] Нет `FAIL` в выводе `verifier`

## Expected Artifacts
- `scripts/gsc_automation.py` — CLI с 6 шагами
- `tests/test_sync_wiki.py` — регрессионный тест для GSC (через FTS5)
- `docs/architecture.md` — раздел 4
- `progress.md` — статус F005
