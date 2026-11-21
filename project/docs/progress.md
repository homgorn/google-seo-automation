# Progress Log — Google SEO Automation

Журнал прогресса. Новая запись сверху.

---

## 2026-11-11 — Аудит качества: 3 ревью, 12 дефектов, 116 тестов, SDD-артефакты

### Проведено

Три независимых code review (параллельные субагенты): ядро скриптов,
automation-скрипты, тесты/CI/безопасность. Каждый дал отчёт с доказательствами
(файл:строка + сценарий поломки + фикс). Ни один дефект не принят на веру —
каждый перепроверен запуском.

### Найдено и исправлено

**CRITICAL**
1. `doc_id` в записях `guides` указывал на **чужие** документы: AEO→gtm,
   GTM→ga4_data, Ads→indexing. Аудит-трейл вёл не туда.
   Фикс: `scripts/common.py::resolve_doc_id(source)` — разрешается по имени
   источника, не «магическим» числом. Миграция v3 перенаправила 28 гайдов,
   удалила 3 дубликата. **Итог: 0 mismatches** (проверено скриптом).

**HIGH**
2. Exit codes: PASS=0, FAIL=1, **BLOCKED=2**. Раньше `gsc_automation` возвращал
   0 при полностью BLOCKED (CI считал бы провалившийся прогон успешным),
   `ads/gtm/aeo/ga4` — 1 вместо 2.
3. `ALLOW_MUTATIONS` и `ADS_MAX_MUTATION_MICROS` были объявлены в `.env.example`,
   но **не читались кодом** — принцип dry-run (SPEC-001 P3) не был enforced.
   Фикс: `common.check_mutation_allowed()`.
4. `PRAGMA foreign_keys = ON` не включался — `ON DELETE CASCADE` в схеме не
   работал, удаление `api_docs` оставляло осиротевшие строки.
5. `sync_run` зависал в статусе `running` при исключении — `finish_run` не
   вызывался. Фикс: try/except + статус `partial`.
6. `errors[]` в `sync_discovery` всегда был пуст — счётчик ошибок всегда 0.
7. `IntegrityError` при конкурентном `sync_wiki.py` ронял весь прогон.
   Фикс: upsert вместо чистого INSERT.
8. `verify_feature.py --all` → pytest → `verify_feature.py --all`:
   **бесконечная рекурсия** (тест таймаутился на 120 с).
   Фикс: guard `VERIFY_FEATURE_NO_PYTEST`.

**MEDIUM**
9. `secret_scan.py`: подстрочная проверка плейсхолдеров (`"your" in value`)
   **маскировала реальные секреты** вида `your_actual_prod_key_abc123`.
   Фикс: точное совпадение. Добавлены паттерны Stripe/Slack/SendGrid/Twilio/
   JWT/Bearer/AWS-secret. Сканер исключает собственный файл.
10. Индекс `api_endpoints.resource` создавался только миграцией, в свежей БД —
    отсутствовал. Фикс: добавлен в SCHEMA.
11. `sync_local_wiki`: один битый файл ронял весь ingest. Фикс: per-file
    try/except.
12. `embed_wiki.py`: docstring обещал семантический поиск, а реальный режим
    был заглушкой. Теперь честно: dry-run + понятное сообщение.

### Рефакторинг

- `scripts/common.py` — единый `Verdict` вместо 6 копий, `log_guide` с
  динамическим `doc_id`, exit codes, валидаторы (property_id, budget, GAQL),
  guard мутаций.
- `gsc/ads/gtm/aeo/ga4_automation.py` переведены на общий модуль.
- Evidence в выводе расширен со 100 до 200 символов — обрезка скрывала
  квоты и форматы, нужные verifier-агенту.

### Тесты: 16 → 116

| Файл | Тестов | Закрывает |
|------|--------|-----------|
| `tests/test_sync_wiki.py` | 16 | регрессии 4 старых багов |
| `tests/test_common.py` | 43 | exit codes, mutation guard, doc_id, валидаторы |
| `tests/test_automation_scripts.py` | 31 | все шаги 5 automation-скриптов |
| `tests/test_tooling.py` | 26 | wiki_query, secret_scan, wiki_index, init_db, verify_feature |

Тест поймал реальный баг: `subprocess.run` не получал `env=env` — окружение
собиралось, но не передавалось в процесс.

### SDD-артефакты (было: только feature_list.json)

| Артефакт | Состояние |
|----------|-----------|
| `docs/specs/SPEC-001-platform.md` | ✅ цели, не-цели, 6 принципов, 12 требований R-01..R-12, DoD |
| `docs/adr/ADR-001-sqlite-and-fts5.md` | ✅ SQLite+FTS5 вместо внешних сервисов |
| `docs/adr/ADR-002-discovery-documents.md` | ✅ Discovery вместо HTML-парсинга |
| `docs/adr/ADR-003-path-templates.md` | ✅ Идентичность = (resource, method_name) |
| `docs/adr/ADR-004-direct-api-client.md` | ✅ Прямой клиент вместо Hyper MCP |
| `docs/ROADMAP.md` | ✅ 7 стадий, блокеры, чанки G-I, пробелы покрытия |
| `feature_list.json` | ✅ обогащён: acceptance_criteria, depends_on, blocked_by, test_refs, script, spec, uncovered_steps |

### Вики: индексы и граф знаний

- `scripts/wiki_index.py` — генератор индексов
- `wiki/index.md` — главный индекс (Markdown)
- `wiki/index.json` — машинно-читаемый индекс
- `wiki/<source>/index.md` — индекс по каждому из 10 источников
- `wiki/_data/entities.json` — 12 сущностей с типами
- `wiki/_data/triples.jsonl` — **123 триплета** (субъект-предикат-объект)
- `wiki/_data/graph.json` — статистика графа, 61 API-ресурс

### CI и безопасность

- `ci.yml`: добавлен `init_db.py` перед verify (без него был бы FAIL),
  покрытие `--cov`, `wiki_index.py --verify`, еженедельный refresh с
  auto-issue, минимальные зависимости для тестов
- `.gitignore` в корне репозитория: `secrets/`, `*.pem`, `*.key`, `*.p12`,
  `*.sqlite*`, `*.bak`, `*.log.*`
- `.env.example`: помечено, какие переменные **реально читает код**

### Проверено

```
pytest tests/ -q                    → 116 passed
python scripts/init_db.py           → idempotent, миграция v3
python scripts/sync_wiki.py --full  → 312 endpoints
python scripts/wiki_index.py        → 123 triples, 61 resources
python scripts/wiki_index.py --verify → актуален
python scripts/secret_scan.py       → 0 находок
python scripts/verify_feature.py --all → 8 PASS, 0 FAIL, 3 BLOCKED
```

### Уверенность

- **9/10** — инфраструктура и tooling (измерено: 312 эндпоинтов, 116 тестов,
  12 закрытых дефектов, 0 mismatches в аудит-трейле)
- **8/10** — готовность к живым интеграциям (код готов и покрыт тестами,
  но без credentials не проверен на реальных API)

### Блокеры (нужны от владельца)

1. `GOOGLE_APPLICATION_CREDENTIALS` **или** `GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN`
2. `GSC_SITE_URL`
3. `GOOGLE_ADS_DEVELOPER_TOKEN` + `GOOGLE_ADS_CUSTOMER_ID`
4. Решение: Merchant — proto или ручной markdown?

### Что дальше

Чанк G (GA4 живые вызовы) → H (GSC живые вызовы) → I (Ads живые вызовы).
Планируется в `docs/ROADMAP.md`.

---

## 2026-10-12 — Чанки A–F: инфраструктура знаний и automation-скрипты

### Сделано

- `feature_list.json` — 11 фич (на тот момент без SDD-полей)
- `AGENTS.md` — 7 агентов с контрактами ввода-вывода
- `init.sh`, `scripts/init_db.py`, `scripts/sync_wiki.py`, `scripts/wiki_query.py`
- `scripts/embed_wiki.py`, `gsc_automation.py`, `ads_automation.py`,
  `gtm_automation.py`, `aeo_automation.py`, `ga4_automation.py`,
  `openchamber_sync.py`, `verify_feature.py`, `secret_scan.py`
- `docs/architecture.md` — измеренные факты, риски, пробелы
- `docs/runbooks/` — 3 runbook-а
- GitHub classic packaging: README (7 языков), LICENSE, SECURITY, CONTRIBUTING,
  CODE_OF_CONDUCT, CHANGELOG, `.github/` templates, CI, 14 topics

### Найденные и исправленные баги (тогдашние)

1. GTM recursion conditional (3 → 106 эндпоинтов)
2. `UNIQUE(method,path)` схлопывал (312 → 162)
3. Naive datetime TypeError в `check_freshness`
4. Windows cp1252 (кириллица в stdout)

## 2026-11-19 — F015 + LLM Wiki + Semantic DB
- F015: `f015_chromex.py` — remote (PSI v5, retry 429/5xx), thresholds LCP<2500/CLS<0.1; tests in `tests/test_f012_f013_f015.py` (140 passed)
- LLM Wiki: `wiki/llm/`, `wiki/llm.md`, `wiki/llm/index.md`, entry in `wiki/index.md`
- Semantic DB: `data/llm_knowledge.db` (entities=27, ontology=26, triples=15, edges=10) + `scripts/build_llm_knowledge.py`, `scripts/query_llm_graph.py`
- F012 structural, auth-blocked (GCP sa needed)

## 2026-11-20 — F010/F011 + F015 fixes + LLM Wiki/semantic DB (F012)
- F015: `f015_chromex.py` — remote (PSI v5, с ретраями), thresholds LCP<2500/CLS<0.1; 140 tests
- F010: `verify_feature.py` + `tests/test_f010_verify.py` + docs/gsc/ — GSC journal (read_csv_journal/write_csv_journal, гарды, ISO validation); verify_feature F010 PASS
- F011: `gsc_automation.py` — gsc_sites_list, gsc_sitemap_list, gsc_urls_inspect, gsc_get_change_log_doc; tests/test_gsc_automation.py; verify_feature F011 PASS
- F012: cloudflare_pages_gsc + cloudflare_deploy_hook (GSC discovery через urls.inspect); googleapiclient imports (pip install)
- LLM Wiki: wiki/llm/, wiki/llm.md, wiki/index.md; research fetches (web.dev CWV)
- Semantic DB: data/llm_knowledge.db (entities=29, ontology=34, triples=15, edges=10)
- docs/gsc/: gsc_declaration.md, README.md, check-in/, gsc_status_reports/
- tests: 155 passed

## 2026-11-20 — Security fixes, F013 (SEO Acceleration), F016 (GSC bucket design)
- SECURITY (audit response): guards on sync_wiki/init_db/wiki_query/embed_wiki/wiki_index/openchamber_sync/verify_feature/gsc_automation (HIGH+MEDIUM mutations)
- F013: `f013_seo_acceleration.py` — actions: robots, crawlers (check_only), claude_blocks, meta_audit, link_audit, image_audit, page_health, deploy_submit; `tests/test_f013_seo.py`; verify_feature F013 PASS
- F016: `docs/gsc/gsc_bucket_design.md` — GSS_PENDING → GSC_READY → DEPLOYING → CLOUDFLARE_WAIT → GSC_FULL_DEPLOY (doc + feature F016)
- Semantic graph: F013, F016 triples (entities=29, ontology=39, triples=15)

## 2026-11-21 — F014 (Astro + Cloudflare 2026) + вики/граф обновлены
- F014: `f014_astro_cloudflare.py` — actions: wrangler (Workers/assets/not_found_handling), cache (cacheCloudflare + _headers immutable), images (imageService + width/height/lazy), redirects, best_practices; `docs/cloudflare-astro-2026.md`; `tests/test_f014_astro.py` (8)
- verify_feature F014 PASS; grounding Astro Docs MCP (deploy/cloudflare, caching)
- Вики: `wiki/llm/f014_astro_cloudflare.md` + index обновлены; граф: F014 triples (ontology=42)
- feature_list: F014 добавлена (16 фич всего)

## 2026-11-21 — F013 sitemap/deploy_submit (steps 5,9,12) + 6 тестов
- F013: action `sitemap` — валидация lastmod/changefreq/hreflang + sitemap-index + interlink report (Cloudflare Crawler Module)
- F013: action `deploy_submit` — реальный submit через F012 (cloudflare_pages_gsc), dry-run BLOCKED по умолчанию
- `_read` helper; tests/test_f013_sitemap.py (6); граф: F013 covers обновлён
