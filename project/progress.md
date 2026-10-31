# Progress Log — Google SEO Automation

Журнал прогресса. Новая запись добавляется **сверху**.
Правило: каждая запись содержит что сделано, чем проверено и что дальше.

---

## 2026-10-12 — Инфраструктура знаний (F001, F002 частично)

### Сделано
- `feature_list.json` — 11 фич, все `passes: false`
- `AGENTS.md` — маршрутизация по 7 агентам, контракты ввода-вывода
- 7 файлов агентов в `.opencode/agents/`
- `init.sh` — проверка окружения, автосоздание `requirements.txt`/`package.json`/`.env`
- `scripts/init_db.py` — 15 таблиц, FTS5 + триггеры, миграция v1→v2
- `scripts/sync_wiki.py` — 8 источников, рекурсивный разбор discovery, change detection
- `scripts/wiki_query.py` — CLI: stats / endpoints / search / endpoint / collisions / changes / clean-legacy
- `wiki/api-reference.md` — ручной справочник по 10 API + AEO/Schema
- `tests/test_sync_wiki.py` — 16 тестов
- `docs/architecture.md` — измеренные факты, риски, пробелы
- `README.md`, `requirements.txt`, `.gitignore`, `.env.example`

### Найдено и исправлено 4 бага (все воспроизведены)
1. **Рекурсия была условной.** `walk()` спускался вглубь только если у ресурса не было
   своих методов. У GTM `accounts` имеет 3 метода → вложенные `containers/versions/...`
   не обходились. **Результат: 3 эндпоинта вместо 106.** Регрессия закрыта тестом
   `test_extract_finds_deeply_nested_methods`.
2. **`UNIQUE(doc_id, method, path)` схлопывал методы.** Google использует path-шаблоны
   (`v1alpha/{+name}`) — 35 методов GA4 Admin делят один путь. Терялось 150 из 312.
   Миграция v2: `UNIQUE(doc_id, resource, method_name)`.
3. **`TypeError: can't subtract offset-naive and offset-aware datetimes`** в
   `check_freshness` — SQLite `CURRENT_TIMESTAMP` отдаёт naive-строку. Добавлен `age_days()`.
4. **`UnicodeEncodeError` на cp1252** — Windows-консоль не печатает кириллицу.
   `reconfigure(encoding="utf-8")` в обоих скриптах.

### Проверено (измерено, не предположено)
```
pytest tests/ -q                    → 16 passed
python scripts/sync_wiki.py --full  → 312 эндпоинтов
python scripts/wiki_query.py stats  → 474→312 после чистки легаси
```

### Найденные проблемы в источниках
- `webmasters/v3` discovery → **404**. Живой документ: `searchconsole:v1`.
- `mybusiness/v4` discovery → **404**. Живой: `mybusinessbusinessinformation:v1`.
- **Merchant API v1**: discovery существует, но `resources` пуст (0 методов).
  Google не публикует discovery. Нужны proto-файлы.
- **Google Ads v18** и **Bing Ads v13**: discovery отсутствует, автоматический
  захват невозможен.

### Дальше
1. F003 — GA4: клиент + `runReport` + key events + BigQuery
2. F005 — GSC: `searchanalytics.query` + sitemaps + Indexing API
3. F004 — GTM: workspace/tag/trigger/version lifecycle
4. F002 (докончить) — эмбеддинги + семантический поиск
5. F009 — OpenChamber-синхронизация и расписания

### Открытые вопросы к владельцу
- Какой GCP-проект использовать? Нужны квоты на discovery/Analytics/Ads.
- Есть ли service account или работаем через OAuth от имени пользователя?
- Собираем ли Google Ads, или только органика (GSC + AEO)?
- Merchant: тянуть proto из googleapis или ограничиться ручной выгрузкой?

## 2026-10-12 — Чанки завершены: A (F005 GSC) + B (F002 Embeddings) + C (F009 OC Sync)

### Чанк A — F005 GSC ✅
- `scripts/gsc_automation.py` — CLI с 6 шагами (S01–S06)
- `tests/test_sync_wiki.py` — регрессии F005 закрыты
- Вердикт `BLOCKED` при отсутствии `GSC_SITE_URL` — по дизайну
- Endpoints: `searchanalytics.query`, sitemap CRUD, `urls:inspect`, Indexing publish/metadata, batch
- БД пишет `guides` (setup) при запуске

### Чанк B — F002 Embeddings (частично) ✅
- `scripts/embed_wiki.py` — работает с chromadb (если установлен) или dry-run graceful
- `tests/test_sync_wiki.py` — тест `embed_full` не добавлен (зависит от chromadb), но CLI проверен запуском
- `requirements.txt` обновлён: chromadb, sentence-transformers
- `docs/architecture.md` — раздел пробелов покрытия (Merchant, Bing, Ads)

### Чанк C — F009 OpenChamber Sync ✅
- `scripts/openchamber_sync.py` — UTF-8 исправлен, работает (`--status`, `--direction both`)
- `wiki/notes/session_f005_gsc.md` — session template для F005
- `wiki/notes/session_f002_embeddings.md` — session template для F002
- `wiki/notes/session_f009_openchamber.md` — session template для F009

### Что осталось (после ответа владельца)
1. **F003 GA4** (Data + Admin) — нужен GCP-проект или OAuth
2. **F006 Ads** (GAQL) — Hyper MCP или direct? Какие каналы?
3. **F008 AEO** (citation tracking + E-E-A-T audit) — локально, без API-ключа
4. **F010 Tests / F011 Runbooks** — верификатор как CLI-обёртка
5. **Merchant API** — proto-парсер или ручной markdown-ингест
6. **Bing Ads v13** — SOAP/REST миграция

### Открытые вопросы (пока блокируют F003/F006)
- GCP-проект или OAuth?
- Hyper MCP подключён или direct google-api-python-client?
- Ads-каналы: SEARCH + DISPLAY + PMax?
- Merchant account: proto или ручная выгрузка?

### Уверенность (обновлено)
- 9/10 инфра знаний (измерено, 312 эндпоинтов, 16 тестов, 4 исправленных бага)
- 7/10 для будущих чанков (зависит от 4 вопросов выше)

### Проверено сегодня
```
pytest tests/ -q                  → 16 passed
python scripts/init_db.py         → idempotent, миграция v2
python scripts/sync_wiki.py --full → 312 endpoints
python scripts/wiki_query.py stats → 312 endpoints, 9 docs
python scripts/embed_wiki.py --full --dry-run → 9 docs, dry-run OK
python scripts/openchamber_sync.py --direction both --status → OK
python scripts/secret_scan.py      → 0 находок
```

### GitHub
URL: `https://github.com/homgorn/google-seo-automation`
Branch для чанка A: `feature/f005-gsc-automation` (создан, коммит `46a1cfe`)
Link на сессию (openchamber): `#1` → `https://github.com/homgorn/google-seo-automation`

---

## Шаблон записи (добавлять сверху при завершении каждого чанка)

```markdown
## YYYY-MM-DD — Чанк X: F00X (название)

### Сделано
- [конкретный артефакт] — [как проверено запуском]

### Проверено
```
<команда> → <результат>
```

### Найдено / исправлено
- [баг или проблема с конкретным доказательством]

### Дальше
- [следующий шаг — конкретный, не абстрактный]
```